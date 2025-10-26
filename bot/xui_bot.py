import asyncio
import json
import os
import time
import sqlite3
import logging
import psutil
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db_handler import toggle_user
from config_loader import load_config
from utils import parse_duration
from scheduler import scheduler  
from x_ui_menu import main_menu  

# ===========================
# INITIALIZATION
# ===========================

cfg = load_config()
bot = Bot(cfg["telegram_token"])
dp = Dispatcher()

# ✅ use shared scheduler only (do NOT reinitialize)
logging.basicConfig(
    filename=cfg["log_path"],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ===========================
# COMMAND HANDLERS
# ===========================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if message.from_user.id not in cfg["admin_ids"]:
        await message.reply(
            "👋 Hello! I’m your X-UI bot.\n\n"
            "🚫 You are *not authorized* to use admin functions.\n"
            "Please contact your server administrator for access.",
            parse_mode="Markdown"
        )
        return

    await message.reply(
        "👋 **Welcome, Admin!**\n\n"
        "✅ Your bot is *online* and connected to Telegram.\n\n"
        "Here’s what I can do for you:\n"
        "• `/account <email>` — Check users\n"
        "• `/stop <email> <time>` — Temporarily stop user (e.g., 30m, 2h, 1d)\n"
        "• `/system` — Check server performance & XUI info\n"
        "• `/whoami` — Show your Telegram ID\n"
        "• `/help` — Show all available commands\n\n"
        "💡 *Example:*\n"
        "`/account alice@example.com`\n\n"
        "🛠 Use the menu below or type any command to begin.",
        parse_mode="Markdown"
    )


@dp.message(Command("account"))
async def handle_user(message: types.Message):
    """
    Show all temporarily stopped users and their re-enable times.
    """
    if message.from_user.id not in cfg["admin_ids"]:
        return await message.reply("❌ Unauthorized")

    jobs = scheduler.get_jobs()
    if not jobs:
        return await message.reply("✅ No users are currently stopped.")

    msg = "🚫 **Temporarily Stopped Users:**\n\n"
    for job in jobs:
        if job.id.startswith("reenable_"):
            email = job.id.replace("reenable_", "")
            run_time = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
            msg += f"• `{email}` → restores at `{run_time}`\n"

    await message.reply(msg, parse_mode="Markdown")



# ===========================
# CUSTOM STOP (BAN) COMMAND
# ===========================

@dp.message(Command("stop"))
async def stop_user(message: types.Message):
    """
    Temporarily disable a user (with custom duration)
    Usage: /stop <email> <duration> (e.g. /stop alice@example.com 2h)
    """
    if message.from_user.id not in cfg["admin_ids"]:
        return await message.reply("❌ Unauthorized")

    try:
        _, email, duration_str = message.text.split(maxsplit=2)
    except ValueError:
        return await message.reply("⚠️ Usage: /stop <email> <duration> (e.g. 30m, 2h, 1d)")

    delta = parse_duration(duration_str)

    result = toggle_user(email, False)
    if not result:
        logging.warning(f"[STOP] Account {email} not found.")
        return await message.reply(f"⚠️ `{email}` not found in database.", parse_mode="Markdown")

    run_time = datetime.now() + delta
    scheduler.add_job(
        toggle_user,
        trigger="date",
        id=f"reenable_{email}",
        run_date=run_time,
        args=[email, True],
        replace_existing=True,
        misfire_grace_time=3600,
        name=f"AutoReEnable_{email}"
    )

    logging.info(f"[STOP] {email} disabled for {duration_str}, will re-enable at {run_time}")
    await message.reply(
        f"🚫 `{email}` stopped for *{duration_str}*.\n\n"
        f"🕒 Access will restore automatically at *{run_time.strftime('%Y-%m-%d %H:%M:%S')}*.",
        parse_mode="Markdown"
    )


# ===========================
# STATUS COMMAND HANDLER
# ===========================

@dp.message(Command("system"))
async def status_handler(message: types.Message):
    """Show XUI and system system summary"""
    if message.from_user.id not in cfg["admin_ids"]:
        return await message.reply("❌ Unauthorized")

    uptime_seconds = time.time() - psutil.boot_time()
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    cpu_usage = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    mem_usage = f"{mem.percent}% ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)"

    db_path = cfg.get("db_path", "/etc/x-ui/x-ui.db")
    total_inbounds = total_clients = 0
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM inbounds")
            total_inbounds = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM clients")
            total_clients = cur.fetchone()[0] or 0
            conn.close()
        except Exception as e:
            total_inbounds, total_clients = 0, 0
            logging.error(f"DB check failed: {e}")

    process_uptime = "N/A"
    try:
        proc = psutil.Process(os.getpid())
        process_uptime = str(datetime.now() - datetime.fromtimestamp(proc.create_time())).split('.')[0]
    except Exception:
        pass

    status_msg = (
        f"📊 **XUI Server Status**\n\n"
        f"🟢 *Bot Status:* Online\n"
        f"⏱ *Bot Uptime:* `{process_uptime}`\n"
        f"💻 *System Uptime:* `{uptime_str}`\n\n"
        f"🧠 *Memory:* {mem_usage}\n"
        f"⚙️ *CPU Usage:* {cpu_usage}%\n\n"
        f"🌐 *Inbounds:* {total_inbounds}\n"
        f"👥 *Clients:* {total_clients}\n\n"
        f"✅ Use `/account <email>` to see."
    )

    await message.reply(status_msg, parse_mode="Markdown")


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    """Show help text and usage examples"""
    await message.reply(
        "📘 **Available Commands:**\n\n"
        "/start - Show the main menu\n"
        "/system - Check bot/server status\n"
        "/whoami - Show your Telegram ID\n"
        "/account <email> - Check a user (admin only)\n"
        "/stop <email> <time> - Temporarily stop a user (e.g., 30m, 2h, 1d)\n\n"
        "Example:\n`/account alice@example.com`",
        parse_mode="Markdown"
    )


@dp.message(Command("whoami"))
async def id_handler(message: types.Message):
    """Show your Telegram ID"""
    await message.reply(f"🆔 Your Telegram ID: `{message.from_user.id}`", parse_mode="Markdown")

# =========================== 
# BUTTON HANDLERS (Enable/Disable)
# ===========================

@dp.callback_query()
async def actions(query: types.CallbackQuery):
    """Handle inline buttons (ON/OFF)"""
    action, email = query.data.split("|")
    admin_id = query.from_user.id

    # Check existing job
    for job in scheduler.get_jobs():
        if job.id == f"reenable_{email}":
            scheduler.remove_job(job.id)
            logging.info(f"[SCHEDULER] Removed old job for {email}")

    if action == "enable":
        result = toggle_user(email, True)
        if not result:
            return await query.message.edit_text(f"⚠️ `{email}` not found.", parse_mode="Markdown")
        logging.info(f"[MANUAL ENABLE] {email} restored by admin {admin_id}")
        await query.message.edit_text(f"🔓 `{email}` manually restored ✅", parse_mode="Markdown")
        return

    elif action == "disable":
        result = toggle_user(email, False)
        if not result:
            return await query.message.edit_text(f"⚠️ `{email}` not found.", parse_mode="Markdown")

        logging.info(f"[TEMP DISABLE] {email} disabled by admin {admin_id}")
        run_time = datetime.now() + timedelta(hours=24)
        scheduler.add_job(
            toggle_user,
            trigger="date",
            id=f"reenable_{email}",
            run_date=run_time,
            args=[email, True],
            replace_existing=True,
            misfire_grace_time=3600,
            name=f"AutoReEnable_{email}"
        )
        await query.message.edit_text(
            f"🚫 `{email}` disabled for 24h.\n"
            f"🕒 Access restores at `{run_time.strftime('%Y-%m-%d %H:%M:%S')}`.",
            parse_mode="Markdown"
        )


async def set_bot_commands(bot: Bot):
    """Register visible commands for Telegram's sidebar menu"""
    commands = [
        types.BotCommand(command="start", description="Show the main menu"),
        types.BotCommand(command="help", description="Help and usage guide"),
        types.BotCommand(command="system", description="Check system status"),
        types.BotCommand(command="whoami", description="Show your Telegram ID"),
        types.BotCommand(command="account", description="Manage a user (admin only)"),
        types.BotCommand(command="stop", description="Temporarily stop a user"),
    ]
    await bot.set_my_commands(commands)


# ===========================
# MAIN ENTRY POINT
# ===========================

async def main():
    logging.info("🚀 XUI Telegram Bot starting...")
    scheduler.start()
    logging.info("Scheduler started")

    for job in scheduler.get_jobs():
        logging.info(f"[JOB RESTORE] Loaded {job.id} scheduled for {job.next_run_time}")

    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot stopped manually.")
