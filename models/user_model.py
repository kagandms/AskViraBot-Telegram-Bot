from datetime import datetime

from pydantic import BaseModel


class UserModel(BaseModel):
    user_id: int | str
    lang: str = "en"
    coins: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    state_name: str | None = None
    state_data: dict | None = None

    # Optional: Methods for business logic if needed,
    # but initially just data structure.
