import logging
from typing import Any

from config import supabase
from models.reminder_model import ReminderModel

logger = logging.getLogger(__name__)


def get_all_reminders_db() -> list[ReminderModel]:
    if not supabase:
        return []
    try:
        response = supabase.table("reminders").select("*").execute()
        return [ReminderModel(**rem) for rem in response.data]
    except Exception as e:
        logger.error(f"Hatırlatıcıları çekme hatası: {e}")
        return []


def add_reminder_db(reminder_data: dict[str, Any]) -> int | None:
    if not supabase:
        return None
    try:
        data_to_insert = {
            "user_id": str(reminder_data["user_id"]),
            "chat_id": str(reminder_data["chat_id"]),
            "message": reminder_data["message"],
            "time": reminder_data["time"],
            "is_completed": False,
        }
        response = supabase.table("reminders").insert(data_to_insert).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("id")
        return None
    except Exception as e:
        logger.error(f"Hatırlatıcı ekleme hatası: {e}")
        return None


def remove_reminder_db(reminder_id: int) -> None:
    if not supabase:
        return
    try:
        supabase.table("reminders").delete().eq("id", reminder_id).execute()
    except Exception as e:
        logger.error(f"Hatırlatıcı silme hatası: {e}")


def get_all_reminders_count() -> int:
    if not supabase:
        return 0
    try:
        response = supabase.table("reminders").select("id", count="exact").execute()
        return response.count if response.count else 0
    except Exception as e:
        logger.error(f"Hatırlatıcı sayısı hatası: {e}")
        return 0
