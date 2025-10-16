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
from utils import *  # optional
from scheduler import scheduler  
from x_ui_menu import main_menu  


# ===========================
# INITIALIZATION
# ===========================

cfg = load_config()
bot = Bot(cfg["telegram_token"])
dp = Dispatcher()
scheduler = AsyncIOScheduler()

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
            "👋 Hello! I’m your X-UI  bot.\n\n"
            "🚫 You are *not authorized* to use admin functions.\n"
            "Please contact your server administrator for access.",
            parse_mode="Markdown"
        )
        return

    await message.reply(
        "👋 **Welcome, Admin!**\n\n"
        "✅ Your bot is *online* and connected to Telegram.\n\n"
        "Here’s what I can do for you:\n"
        "• `/account <email>` — check users\n"
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
    """Handle /account <email> command from admin"""
    if message.from_user.id not in cfg["admin_ids"]:
        return await message.reply("❌ Unauthorized")

    try:
        email = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        return await message.reply("⚠️ Usage: /account <email>")

    await message.reply(
        f"🔍 Checking account `{email}`",
        parse_mode="Markdown",
        reply_markup=main_menu(email)
    )


# ===========================
# STATUS COMMAND HANDLER
# ===========================

import os, time, psutil, sqlite3
from datetime import datetime, timedelta

@dp.message(Command("system"))
async def status_handler(message: types.Message):
    """Show XUI and system system summary"""
    if message.from_user.id not in cfg["admin_ids"]:
        return await message.reply("❌ Unauthorized")

    # --- 1️⃣ Get system stats ---
    uptime_seconds = time.time() - psutil.boot_time()
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    cpu_usage = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    mem_usage = f"{mem.percent}% ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)"

    # --- 2️⃣ Get X-UI DB info ---
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

    # --- 3️⃣ Get uptime of bot process ---
    process_uptime = "N/A"
    try:
        proc = psutil.Process(os.getpid())
        process_uptime = str(datetime.now() - datetime.fromtimestamp(proc.create_time())).split('.')[0]
    except Exception:
        pass

    # --- 4️⃣ Build status message ---
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
        "/account <email> - check a user (admin only)\n\n"
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

    # --- ACTION: ENABLE USER ---
    if action == "enable":
        result = toggle_user(email, True)

        if not result:
            logging.warning(f"account {email} not found.")
            await query.message.edit_text(
                f"⚠️ `{email}` not found in database — cannot On.",
                parse_mode="Markdown"
            )
            return

        logging.info(f"[MANUAL ENABLE] {email} access restored by admin {admin_id}")
        await query.message.edit_text(
            f"🔓 `{email}` has been *manually access restored* ✅",
            parse_mode="Markdown"
        )
        return

    # --- ACTION: DISABLE USER ---
    elif action == "disable":
        result = toggle_user(email, False)

        if not result:
            logging.warning(f"account {email} not found.")
            await query.message.edit_text(
                f"⚠️ `{email}` not found in database — cannot Off.",
                parse_mode="Markdown"
            )
            return

        logging.info(f"[TEMP DISABLE] {email} Off by admin {admin_id}")

        # Schedule re-enable job (24h)
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
        logging.info(f"[SCHEDULER] A access restored for {email}  at {run_time}")

        await query.message.edit_text(
            f"🚫 `{email}` Off for 24 .\n\n"
            f"🕒 A access for *{run_time.strftime('%Y-%m-%d %H:%M:%S')}*.",
            parse_mode="Markdown"
        )


async def set_bot_commands(bot: Bot):
    """Register visible commands for Telegram's sidebar menu"""
    commands = [
        types.BotCommand(command="start", description="Show the main menu"),
        types.BotCommand(command="help", description="Bot help and usage guide"),
        types.BotCommand(command="system", description="Check bot/server status"),
        types.BotCommand(command="whoami", description="Show your Telegram ID"),
        types.BotCommand(command="account", description="M-U (admin only)"),
    ]
    await bot.set_my_commands(commands)


# ===========================
# MAIN ENTRY POINT
# ===========================

async def main():
    logging.info("🚀 XUI Telegram Bot starting...")
    scheduler.start()
    logging.info("Scheduler started")
    await set_bot_commands(bot)  # 👈 This line registers the command list
    logging.info("Bot commands registered")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot stopped manually.")
