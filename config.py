import os
from dotenv import load_dotenv

load_dotenv()
HOUSE_INVITE_LINK = os.getenv("HOUSE_INVITE_LINK", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "1623991112"))
# Необязательно: ID группы, куда бот должен приглашать одобренных пользователей.
HOUSE_CHAT_ID_RAW = os.getenv("HOUSE_CHAT_ID", "").strip()
HOUSE_CHAT_ID = int(HOUSE_CHAT_ID_RAW) if HOUSE_CHAT_ID_RAW else None
# Для создания пригласительных ссылок бот должен быть администратором группы
# с правом приглашать пользователей.
