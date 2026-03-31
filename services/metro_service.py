import logging
from typing import Any

from config import supabase

logger = logging.getLogger(__name__)


def get_metro_favorites(user_id: int | str) -> list[dict[str, Any]]:
    if not supabase:
        return []
    try:
        response = supabase.table("metro_favorites").select("*").eq("user_id", str(user_id)).execute()
        if not response.data:
            return []

        return [
            favorite
            for favorite in response.data
            if favorite.get("station_id") is not None and favorite.get("direction_id") is not None
        ]
    except Exception as e:
        logger.error(f"Metro favorileri getirme hatası (User: {user_id}): {e}")
        return []


def add_metro_favorite(
    user_id: int | str,
    line_id: str,
    line_name: str,
    station_id: str,
    station_name: str,
    direction_id: str,
    direction_name: str,
) -> bool:
    if not supabase:
        return False
    try:
        existing = (
            supabase.table("metro_favorites")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("station_id", station_id)
            .eq("direction_id", direction_id)
            .execute()
        )
        if existing.data:
            return False

        data = {
            "user_id": str(user_id),
            "line_id": line_id,
            "line_name": line_name,
            "station_id": station_id,
            "station_name": station_name,
            "direction_id": direction_id,
            "direction_name": direction_name,
        }
        supabase.table("metro_favorites").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Metro favori ekleme hatası (User: {user_id}): {e}")
        return False


def remove_metro_favorite(user_id: int, station_id: str, direction_id: str) -> bool:
    if not supabase:
        return False
    try:
        supabase.table("metro_favorites").delete().eq("user_id", str(user_id)).eq("station_id", station_id).eq(
            "direction_id", direction_id
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Metro favori silme hatası (User: {user_id}, Station: {station_id}): {e}")
        return False
