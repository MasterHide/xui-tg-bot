from aiogram import types

def main_menu(email: str):
    buttons = [
        [types.InlineKeyboardButton(text="✅ Turn On", callback_data=f"enable|{email}"),
         types.InlineKeyboardButton(text="🚫 Turn Off", callback_data=f"disable|{email}")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)
