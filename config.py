
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", ""))
HOUSE_INVITE_LINK = os.getenv("HOUSE_INVITE_LINK", "").strip()
