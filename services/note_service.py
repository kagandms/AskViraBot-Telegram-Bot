import logging

from config import supabase
from models.note_model import NoteModel

logger = logging.getLogger(__name__)


def get_user_notes(user_id: int | str) -> list[NoteModel]:
    if not supabase:
        return []
    try:
        response = supabase.table("notes").select("*").eq("user_id", str(user_id)).order("id").execute()
        return [NoteModel(**note) for note in response.data]
    except Exception as e:
        logger.error(f"Notları getirme hatası (User: {user_id}): {e}")
        return []


def add_user_note(user_id: int | str, note_content: str) -> bool:
    if not supabase:
        return False
    try:
        data = {"user_id": str(user_id), "content": note_content, "title": None}
        supabase.table("notes").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Not ekleme hatası (User: {user_id}): {e}")
        return False


def update_user_note(note_id: int, new_content: str) -> bool:
    if not supabase:
        return False
    try:
        try:
            supabase.table("notes").update({"content": new_content}).eq("id", note_id).execute()
            return True
        except Exception as e:
            if "updated_at" not in str(e):
                raise e

            # Database Trigger Fallback
            res = supabase.table("notes").select("*").eq("id", note_id).execute()
            if not res.data:
                return False
            note = res.data[0]

            supabase.table("notes").delete().eq("id", note_id).execute()

            try:
                supabase.table("notes").insert(
                    {
                        "id": note_id,
                        "user_id": note["user_id"],
                        "title": note.get("title"),
                        "content": new_content,
                        "created_at": note.get("created_at"),
                    }
                ).execute()
            except Exception:
                supabase.table("notes").insert(
                    {"user_id": note["user_id"], "title": note.get("title"), "content": new_content}
                ).execute()
            return True

    except Exception as e:
        logger.error(f"Not güncelleme hatası (ID: {note_id}): {e}")
        return False


def delete_user_note_by_id(note_id: int) -> bool:
    if not supabase:
        return False
    try:
        supabase.table("notes").delete().eq("id", note_id).execute()
        return True
    except Exception as e:
        logger.error(f"Not silme hatası (ID: {note_id}): {e}")
        return False


def get_all_notes_count() -> int:
    if not supabase:
        return 0
    try:
        response = supabase.table("notes").select("id", count="exact").execute()
        return response.count if response.count else 0
    except Exception as e:
        logger.error(f"Not sayısı hatası: {e}")
        return 0


# --- HELPERS / WRAPPERS ---
def get_notes(user_id: int | str) -> list[str]:
    """Sadece not içeriklerini string listesi olarak döndürür."""
    raw_notes = get_user_notes(user_id)
    return [note.content for note in raw_notes]


def add_note(user_id: int | str, content: str) -> bool:
    """add_user_note fonksiyonuna yönlendirir."""
    return add_user_note(user_id, content)


def delete_note(user_id: int | str, note_number: int) -> bool:
    """Sıra numarasına (1, 2, 3...) göre not siler."""
    raw_notes = get_user_notes(user_id)
    index = note_number - 1
    if 0 <= index < len(raw_notes):
        note_id = raw_notes[index].id
        return delete_user_note_by_id(note_id)
    return False


def update_note(user_id: int | str, note_index: int, new_content: str) -> bool:
    """Liste indeksine (1, 2, 3...) göre not günceller."""
    raw_notes = get_user_notes(user_id)
    index = note_index - 1
    if 0 <= index < len(raw_notes):
        note_id = raw_notes[index].id
        return update_user_note(note_id, new_content)
    return False
