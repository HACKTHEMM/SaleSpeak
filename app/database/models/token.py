import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.schema.enums import UserType

class RefreshTokenCreate(BaseModel):
    refresh_token: str
    user_id: UUID
    user_type: UserType

class RefreshTokenDB(RefreshTokenCreate):
    id: UUID | None = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
