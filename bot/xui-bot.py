import asyncio, json, sqlite3, logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.db_handler import toggle_user
from bot.config_loader import load_config
from bot.menu import main_menu

cfg = load_config()
bot, dp = Bot(cfg["telegram_token"]), Dispatcher()
scheduler = AsyncIOScheduler()
logging.basicConfig(filename=cfg["log_path"], level=logging.INFO, format="%(asctime)s - %(message)s")

@dp.message(Command("user"))
async def handle_user(message: types.Message):
    if message.from_user.id not in cfg["admin_ids"]:
        return await message.reply("❌ Unauthorized")
    try:
        email = message.text.split(maxsplit=1)[1]
    except IndexError:
        return await message.reply("⚠️ Usage: /user <email>")
    await message.reply(f"🔍 Managing user `{email}`", parse_mode="Markdown", reply_markup=main_menu(email))

@dp.callback_query()
async def actions(query: types.CallbackQuery):
    action, email = query.data.split("|")
    if action == "enable":
        toggle_user(email, True)
        await query.message.edit_text(f"✅ `{email}` enabled", parse_mode="Markdown")
    elif action == "disable":
        toggle_user(email, False)
        scheduler.add_job(lambda: toggle_user(email, True), "interval", hours=24, max_instances=1)
        await query.message.edit_text(f"🚫 `{email}` disabled for 24h (auto re-enable scheduled)", parse_mode="Markdown")

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
