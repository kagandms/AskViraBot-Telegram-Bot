from datetime import datetime

from pydantic import BaseModel


class ReminderModel(BaseModel):
    id: int
    user_id: int | str
    chat_id: int | str | None = None
    message: str | None = None
    time: str | datetime | None = None
    is_completed: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
