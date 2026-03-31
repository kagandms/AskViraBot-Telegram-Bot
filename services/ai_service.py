import logging

from config import supabase

logger = logging.getLogger(__name__)


def get_ai_daily_usage(user_id: int | str, today_str: str) -> int:
    if not supabase:
        return 0
    try:
        response = (
            supabase.table("ai_usage")
            .select("usage_count")
            .eq("user_id", str(user_id))
            .eq("usage_date", today_str)
            .execute()
        )
        if response.data:
            return response.data[0]["usage_count"]
        return 0
    except Exception as e:
        logger.error(f"AI kullanım getirme hatası (User: {user_id}): {e}")
        return 0


def set_ai_daily_usage(user_id: int | str, today_str: str, count: int) -> None:
    if not supabase:
        return
    try:
        data = {"user_id": str(user_id), "usage_date": today_str, "usage_count": count}
        supabase.table("ai_usage").upsert(data, on_conflict="user_id,usage_date").execute()
    except Exception as e:
        logger.error(f"AI kullanım kaydetme hatası (User: {user_id}): {e}")


def increment_ai_usage(user_id: int | str, today_str: str) -> int:
    if not supabase:
        return 0
    try:
        current = get_ai_daily_usage(user_id, today_str)
        new_count = current + 1
        set_ai_daily_usage(user_id, today_str, new_count)
        return new_count
    except Exception as e:
        logger.error(f"AI kullanım artırma hatası (User: {user_id}): {e}")
        return 0


def get_ai_total_stats(today_str: str) -> dict:
    if not supabase:
        return {"total_messages": 0, "unique_users": 0}
    try:
        response = supabase.table("ai_usage").select("usage_count").eq("usage_date", today_str).execute()
        if response.data:
            total = sum(row["usage_count"] for row in response.data)
            unique = len(response.data)
            return {"total_messages": total, "unique_users": unique}
        return {"total_messages": 0, "unique_users": 0}
    except Exception as e:
        logger.error(f"AI istatistik hatası: {e}")
        return {"total_messages": 0, "unique_users": 0}
