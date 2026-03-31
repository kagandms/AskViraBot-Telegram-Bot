from datetime import datetime

from pydantic import BaseModel


class NoteModel(BaseModel):
    id: int
    user_id: int | str
    title: str | None = None
    content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
