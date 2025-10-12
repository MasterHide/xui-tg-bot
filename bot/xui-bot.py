import asyncio
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db_handler import toggle_user
from config_loader import load_config
from utils import *  # (optional, if used anywhere)
from scheduler import scheduler  # if referenced
from x_ui_menu import main_menu  # fix name to match your file


# ===========================
# INITIALIZATION
# ===========================

cfg = load_config()
bot = Bot(cfg["telegram_token"])
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Logging configuration
logging.basicConfig(
    filename=cfg["log_path"],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ===========================
# COMMAND HANDLERS
# ===========================

@dp.message(Command("user"))
async def handle_user(message: types.Message):
    """Handle /user <email> command from admin"""
    if message.from_user.id not in cfg["admin_ids"]:
        return await message.reply("❌ Unauthorized")

    try:
        email = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        return await message.reply("⚠️ Usage: /user <email>")

    await message.reply(
        f"🔍 Managing user `{email}`",
        parse_mode="Markdown",
        reply_markup=main_menu(email)
    )


# ===========================
# BUTTON HANDLERS (Enable/Disable)
# ===========================

@dp.callback_query()
async def actions(query: types.CallbackQuery):
    """Handle inline buttons (enable/disable)"""
    action, email = query.data.split("|")

    # Remove any existing scheduled re-enable job for this user
    for job in scheduler.get_jobs():
        if job.id == f"reenable_{email}":
            scheduler.remove_job(job.id)
            logging.info(f"[SCHEDULER] Removed old job for {email}")

    if action == "enable":
        # Manual re-enable
        toggle_user(email, True)
        logging.info(f"[MANUAL ENABLE] {email} re-enabled by admin {query.from_user.id}")

        await query.message.edit_text(
            f"✅ `{email}` has been manually re-enabled.",
            parse_mode="Markdown"
        )

    elif action == "disable":
        # Disable user immediately
        toggle_user(email, False)
        logging.info(f"[TEMP DISABLE] {email} disabled by admin {query.from_user.id}")

        # Schedule automatic re-enable after 24 hours
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

        logging.info(f"[SCHEDULER] Auto re-enable for {email} scheduled at {run_time}")

        await query.message.edit_text(
            f"🚫 `{email}` disabled for 24 hours.\n\n"
            f"🕒 Auto re-enable scheduled for *{run_time.strftime('%Y-%m-%d %H:%M:%S')}*.",
            parse_mode="Markdown"
        )


# ===========================
# MAIN ENTRY POINT
# ===========================

async def main():
    logging.info("🚀 XUI Telegram Bot starting...")
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot stopped manually.")
