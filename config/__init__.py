import logging
import os
from typing import Optional

from supabase import Client, create_client

from .settings import settings

logger = logging.getLogger(__name__)

# --- EXPORTS (Compatibility with old config.py) ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(BASE_DIR, "DejaVuSans.ttf")
NOTES_PER_PAGE = settings.NOTES_PER_PAGE
TIMEZONE = settings.TIMEZONE
BOT_NAME = settings.BOT_NAME
AI_DAILY_LIMIT = settings.AI_DAILY_LIMIT
WEB_APP_BASE_URL = settings.WEB_APP_BASE_URL
ALLOW_LOCAL_WEBAPP_BYPASS = settings.ALLOW_LOCAL_WEBAPP_BYPASS

# API KEYS (Validated by Pydantic on import)
BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
OPENWEATHERMAP_API_KEY = settings.OPENWEATHERMAP_API_KEY
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY.get_secret_value()

ADMIN_IDS = settings.get_admin_ids


# --- LAZY SINGLETON ---
_supabase_client: Client | None = None


def get_supabase() -> Client | None:
    """Lazy-initialized Supabase client with error handling."""
    global _supabase_client
    if _supabase_client is None:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("✅ Supabase bağlantısı başarılı")
        except Exception as e:
            logger.error(f"❌ Supabase bağlantı hatası: {e}")
    return _supabase_client


# Backward compatibility — eager init on import
supabase: Client | None = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    _supabase_client = supabase  # Share with lazy getter
    logger.info("✅ Supabase (PostgreSQL) Bağlantısı Başarılı! (via Pydantic Settings)")
except Exception as e:
    logger.error(f"❌ Supabase Bağlantı Hatası: {e}")
