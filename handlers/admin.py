from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, HOUSE_CHAT_ID
from database.db import (
    get_application, review_application, set_admin_session,
    clear_admin_session,
)
from keyboards.inline import review_keyboard

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("pending"))
async def pending(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Новые заявки приходят сюда автоматически. Для диалога с пользователем "
        "используй кнопку «Ответить» под его заявкой или /reply ID."
    )


@router.callback_query(F.data.startswith("app:"))
async def review_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    try:
        _, action, raw_id = callback.data.split(":")
        application_id = int(raw_id)
    except (ValueError, AttributeError):
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    app = await get_application(application_id)
    if not app:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    if app["status"] != "pending":
        await callback.answer("Эта заявка уже рассмотрена.", show_alert=True)
        return

    if action == "reject":
        await set_admin_session(ADMIN_ID, application_id, "reject_reason")
        await callback.message.answer(
            f"Напиши причину отказа для заявки #{application_id} одним сообщением. "
            "Чтобы отказать без причины, отправь «-»."
        )
        await callback.answer()
        return

    if action == "reply":
        await set_admin_session(ADMIN_ID, application_id, "reply")
        await callback.message.answer(
            f"Напиши сообщение пользователю по заявке #{application_id}. "
            "Следующее текстовое сообщение будет отправлено ему."
        )
        await callback.answer()
        return

    if action == "accept":
        invite_link = None
        if HOUSE_CHAT_ID is not None:
            try:
                invite = await callback.bot.create_chat_invite_link(
                    chat_id=HOUSE_CHAT_ID,
                    member_limit=1,
                    creates_join_request=False,
                    name=f"application-{application_id}",
                )
                invite_link = invite.invite_link
            except Exception:
                await callback.message.answer(
                    "Не удалось создать приглашение. Проверь HOUSE_CHAT_ID и права бота "
                    "администратора группы. Заявка пока не одобрена."
                )
                await callback.answer("Ошибка создания приглашения.", show_alert=True)
                return

        if action == "accept":
            from config import HOUSE_INVITE_LINK

            if not HOUSE_INVITE_LINK:
                await callback.answer(
                    "Ссылка на вступление не настроена.",
                    show_alert=True,
                )
                return

            await review_application(
                application_id,
                "accepted",
                ADMIN_ID,
                invite_link=HOUSE_INVITE_LINK,
            )

            text = (
                "✅ Твоя заявка в Minecraft House одобрена!\n\n"
                f"🔗 Ссылка для вступления: {HOUSE_INVITE_LINK}"
            )

            try:
                await callback.bot.send_message(app["tg_id"], text)
            except Exception:
                await callback.message.answer(
                    f"Заявка #{application_id} одобрена, "
                    "но не удалось написать пользователю."
                )

            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                f"Заявка #{application_id} одобрена."
            )
            await callback.answer("Одобрено.")
            return

    await callback.answer("Неизвестное действие.", show_alert=True)
