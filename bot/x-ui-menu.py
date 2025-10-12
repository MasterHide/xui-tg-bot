from aiogram import types

def main_menu(email: str):
    buttons = [
        [types.InlineKeyboardButton(text="✅ Enable", callback_data=f"enable|{email}"),
         types.InlineKeyboardButton(text="🚫 Disable 24h", callback_data=f"disable|{email}")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)
