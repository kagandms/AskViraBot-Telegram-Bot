import asyncio
import functools
import logging
import time

from config import supabase

logger = logging.getLogger(__name__)

# --- RETRY DECORATOR ---
MAX_RETRIES = 2
RETRY_DELAY = 0.5  # seconds (exponential backoff)


def _db_retry(func):
    """Decorator that retries sync DB operations on transient failures."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY * (2**attempt)
                    logger.warning(f"DB retry {attempt + 1}/{MAX_RETRIES} for {func.__name__}: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"DB operation {func.__name__} failed after {MAX_RETRIES + 1} attempts: {e}")
        raise last_error

    return wrapper


# --- LANGUAGE ---

from models.user_model import UserModel


# --- USER MODEL ACCESS ---
@_db_retry
def get_user_model(user_id: int | str) -> UserModel:
    """Fetch full user object as Pydantic model."""
    user_id = str(user_id)
    if not supabase:
        return UserModel(user_id=user_id)
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if response.data:
            return UserModel(**response.data[0])
        return UserModel(user_id=user_id)
    except Exception as e:
        logger.error(f"User model fetch error: {e}")
        return UserModel(user_id=user_id)


# --- LANGUAGE ---
from services.cache_service import get_cache, set_cache

# --- LANGUAGE ---
# _user_lang_cache removed in favor of Redis


async def get_user_lang(user_id: int | str) -> str:
    user_id = str(user_id)
    cache_key = f"lang:{user_id}"

    # 1. Try Cache
    cached = await get_cache(cache_key)
    if cached:
        # logger.debug(f"DEBUG: Lang from cache for {user_id}: {cached}")
        return cached

    # 2. Fallback to DB (Sync call wrapped in thread)
    def _fetch_db():
        if not supabase:
            return "en"
        try:
            response = supabase.table("users").select("lang").eq("user_id", user_id).execute()
            # logger.debug(f"DEBUG: DB Fetch Response for {user_id}: {response.data}")
            if response.data and response.data[0].get("lang"):
                return response.data[0]["lang"]
            return "en"
        except Exception as e:
            logger.error(f"Dil getirme hatası (User: {user_id}): {e}")
            return "en"

    lang = await asyncio.to_thread(_fetch_db)
    logger.debug(f"Lang fetched from DB for {user_id}: {lang}")

    # 3. Set Cache
    await set_cache(cache_key, lang, ttl=86400)  # 24 hours
    return lang


async def set_user_lang_db(user_id: int | str, lang: str) -> None:
    user_id = str(user_id)
    cache_key = f"lang:{user_id}"

    logger.debug(f"Setting language for {user_id} to {lang}")

    # 1. Update Cache FIRST - this is the primary storage now
    await set_cache(cache_key, lang, ttl=604800)  # 7 days cache
    logger.debug(f"Cache updated for {user_id} -> {lang}")

    # 2. Update DB (Await this to prevent race conditions)
    def _update_db():
        if not supabase:
            logger.error("No supabase client while updating language")
            return
        try:
            # Use UPSERT to ensure user exists if not already present
            data = {"user_id": user_id, "lang": lang}
            # upsert handles both insert and update based on primary key / unique constraint
            result = supabase.table("users").upsert(data, on_conflict="user_id").execute()
            logger.debug(f"Language upsert result for {user_id}: {result.data}")
        except Exception as e:
            # Log but don't fail - cache has the data
            logger.error(f"DB lang update error: {e}")

    # Wait for DB update to finish ensuring next read sees changes
    await asyncio.to_thread(_update_db)


# --- STATE MANAGEMENT ---
@_db_retry
def set_user_state(user_id: int | str, state_name: str, state_data: dict | None = None) -> None:
    if not supabase:
        return
    if state_data is None:
        state_data = {}

    try:
        data = {"user_id": str(user_id), "state_name": state_name, "state_data": state_data}
        supabase.table("user_states").upsert(data, on_conflict="user_id").execute()
    except Exception as e:
        logger.error(f"Error setting state for {user_id}: {e}")


@_db_retry
def get_user_state(user_id: int | str) -> dict | None:
    if not supabase:
        return None
    try:
        response = supabase.table("user_states").select("*").eq("user_id", str(user_id)).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting state for {user_id}: {e}")
        return None


@_db_retry
def clear_user_state(user_id: int | str) -> None:
    if not supabase:
        return
    try:
        supabase.table("user_states").delete().eq("user_id", str(user_id)).execute()
    except Exception as e:
        logger.error(f"Error clearing state for {user_id}: {e}")


# --- ADMIN ---
@_db_retry
def get_all_users_count() -> int:
    if not supabase:
        return 0
    try:
        response = supabase.table("users").select("user_id", count="exact").execute()
        return response.count if response.count else 0
    except Exception as e:
        logger.error(f"Kullanıcı sayısı hatası: {e}")
        return 0


def get_all_user_ids() -> list[int]:
    if not supabase:
        return []
    try:
        response = supabase.table("users").select("user_id").execute()
        return [int(u["user_id"]) for u in response.data] if response.data else []
    except Exception as e:
        logger.error(f"Kullanıcı listesi hatası: {e}")
        return []


def get_recent_users(limit: int = 10) -> list[UserModel]:
    if not supabase:
        return []
    try:
        response = supabase.table("users").select("*").order("created_at", desc=True).limit(limit).execute()
        # Return list of UserModels
        return [UserModel(**u) for u in response.data] if response.data else []
    except Exception as e:
        logger.error(f"Son kullanıcılar hatası: {e}")
        return []
