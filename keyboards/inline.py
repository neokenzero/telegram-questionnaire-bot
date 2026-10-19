from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def review_keyboard(application_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"app:accept:{application_id}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data=f"app:reject:{application_id}"),
        ],
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"app:reply:{application_id}")],
    ])
