from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID
from database.db import (
    upsert_user, get_application_by_user,
    get_application, get_admin_session, clear_admin_session,
    set_admin_session, save_message, review_application,
)

router = Router()


def name_of(message: Message) -> str:
    parts = [message.from_user.first_name, message.from_user.last_name]
    return " ".join(x for x in parts if x) or "Без имени"


async def admin_has_session(message: Message) -> bool:
    if message.from_user.id != ADMIN_ID:
        return False
    return await get_admin_session(ADMIN_ID) is not None


async def user_has_application(message: Message) -> bool:
    if message.from_user.id == ADMIN_ID:
        return False
    return await get_application_by_user(message.from_user.id) is not None


@router.message(Command("reply"))
async def reply_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /reply ID_ЗАЯВКИ")
        return
    application_id = int(parts[1])
    app = await get_application(application_id)
    if not app:
        await message.answer("Заявка не найдена.")
        return
    await set_admin_session(ADMIN_ID, application_id, "reply")
    await message.answer(
        f"Выбран диалог по заявке #{application_id}. "
        "Отправь следующим сообщением текст для пользователя."
    )


@router.message(F.text, admin_has_session)
async def handle_admin_session(message: Message):
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    session = await get_admin_session(ADMIN_ID)
    if not session:
        return
    app = await get_application(session["application_id"])
    if not app:
        await clear_admin_session(ADMIN_ID)
        await message.answer("Заявка не найдена; режим диалога сброшен.")
        return

    if session["mode"] == "reject_reason":
        reason = None if text == "-" else text
        await review_application(app["id"], "rejected", ADMIN_ID, reason=reason)
        await message.bot.send_message(
            app["tg_id"],
            "❌ Твоя заявка в Minecraft House отклонена."
            + (f"\nПричина: {reason}" if reason else ""),
        )
        await clear_admin_session(ADMIN_ID)
        await message.answer(f"Заявка #{app['id']} отклонена.")
        return

    if session["mode"] == "reply":
        await message.bot.send_message(
            app["tg_id"], f"✉️ Сообщение от администратора:\n\n{text}"
        )
        await save_message(app["id"], ADMIN_ID, app["tg_id"], text)
        await clear_admin_session(ADMIN_ID)
        await message.answer("Сообщение отправлено. Для следующего ответа используй /reply ID.")


@router.message(F.text, user_has_application)
async def relay_user_message(message: Message):
    user = message.from_user
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    app = await get_application_by_user(user.id)
    if not app:
        return
    await upsert_user(user.id, user.username, name_of(message))
    await save_message(app["id"], user.id, ADMIN_ID, text)
    username = f"@{user.username}" if user.username else "нет username"
    await message.bot.send_message(
        ADMIN_ID,
        f"✉️ <b>Сообщение по заявке #{app['id']}</b>\n"
        f"От: {name_of(message)} ({username})\n"
        f"ID: <code>{user.id}</code>\n\n{text}\n\n"
        f"Ответить: /reply {app['id']}",
    )
    await message.answer("Сообщение передано администратору.")
