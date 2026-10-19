import json
import re

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import ADMIN_ID
from database.db import (
    upsert_user, get_user, get_application_by_user, update_draft,
    create_application,
)
from keyboards.inline import review_keyboard

router = Router()

QUESTIONS = [
    ("minecraft_nick", "1/6. Напиши свой Minecraft-ник (3–16 символов)."),
    ("age", "2/6. Сколько тебе лет?"),
    ("timezone", "3/6. Какой у тебя часовой пояс? Например, UTC+3."),
    ("motivation", "4/6. Почему хочешь вступить?"),
    ("experience", "5/6. Какой у тебя опыт игры и специализация?"),
    ("availability", "6/6. Сколько времени в неделю готов уделять серверу?"),
]


def display_name(message: Message) -> str:
    parts = [message.from_user.first_name, message.from_user.last_name]
    return " ".join(part for part in parts if part) or "Без имени"


@router.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    await upsert_user(user.id, user.username, display_name(message))
    existing = await get_application_by_user(user.id)
    if existing:
        labels = {
            "pending": "Твоя заявка уже ожидает рассмотрения.",
            "accepted": "Твоя заявка уже одобрена.",
            "rejected": "Твоя заявка была отклонена. Повторная подача пока не предусмотрена.",
        }
        await message.answer(labels.get(existing["status"], "Заявка уже существует."))
        if existing["status"] == "rejected" and existing.get("reject_reason"):
            await message.answer(f"Причина: {existing['reject_reason']}")
        return
    await update_draft(user.id, 0, {})
    await message.answer(
        "Привет! Заполним заявку на вступление.\n\n"
        + QUESTIONS[0][1]
    )


@router.message(F.text)
async def answer_question(message: Message):
    user_obj = message.from_user
    text = (message.text or "").strip()
    if text.startswith("/"):
        return
    await upsert_user(user_obj.id, user_obj.username, display_name(message))
    user = await get_user(user_obj.id)
    if not user or user["step"] is None:
        return
    existing = await get_application_by_user(user_obj.id)
    if existing:
        return

    index = int(user["step"])
    if not 0 <= index < len(QUESTIONS):
        await update_draft(user_obj.id, None, {})
        await message.answer("Состояние анкеты сброшено. Напиши /start.")
        return
    if not text:
        await message.answer("Ответ не должен быть пустым. Попробуй ещё раз.")
        return
    if index == 0 and not re.fullmatch(r"[A-Za-z0-9_]{3,16}", text):
        await message.answer("Ник должен содержать 3–16 символов: латиницу, цифры или _.")
        return
    if index == 1 and (not text.isdigit() or not 10 <= int(text) <= 99):
        await message.answer("Укажи возраст числом от 10 до 99.")
        return

    draft = json.loads(user["draft"] or "{}")
    draft[QUESTIONS[index][0]] = text
    if index < len(QUESTIONS) - 1:
        await update_draft(user_obj.id, index + 1, draft)
        await message.answer(QUESTIONS[index + 1][1])
        return

    application_id = await create_application(user_obj.id, draft)
    await update_draft(user_obj.id, None, {})
    summary = "\n\n".join(
        f"<b>{label}</b>\n{draft[key]}"
        for key, label in [
            ("minecraft_nick", "Minecraft-ник"),
            ("age", "Возраст"),
            ("timezone", "Часовой пояс"),
            ("motivation", "Почему хочет вступить"),
            ("experience", "Опыт и специализация"),
            ("availability", "Время в неделю"),
        ]
    )
    username = f"@{user_obj.username}" if user_obj.username else "не указан"
    await message.answer("✅ Заявка отправлена! Ожидай решения администратора.")
    try:
        await message.bot.send_message(
            ADMIN_ID,
            f"📩 <b>Новая заявка #{application_id}</b>\n"
            f"Имя: {display_name(message)}\n"
            f"Telegram ID: <code>{user_obj.id}</code>\n"
            f"Username: {username}\n\n{summary}",
            reply_markup=review_keyboard(application_id),
        )
    except Exception:
        await message.answer(
            "Заявка сохранена, но не удалось уведомить администратора. "
            "Попробуй позже или свяжись с администратором."
        )
        raise
