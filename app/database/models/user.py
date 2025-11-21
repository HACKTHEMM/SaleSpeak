import datetime
from typing import Dict, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.database.models.entity import username, phoneNumber
from app.schema.enums import PermissionType
from app.utils.helper import normalize_email, strip_whitespace

class User(BaseModel):
    role_id: UUID
    username: username
    email: Optional[str] = None
    phone_number: Optional[phoneNumber] = None
    password: Optional[str] = None
    onboarded: Optional[bool] = False
    deactivated: Optional[bool] = False
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        use_enum_values=True,
    )
    
    @field_validator("*", mode="before")
    def apply_strip_whitespace(cls, value):
        return strip_whitespace(value)

    @field_validator("email", mode="after")
    def apply_normalize_email(cls, value):
        return normalize_email(value)

class UserDB(User):
    id: UUID | None = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    password: str = None
    onboarded: bool = False
    deactivated: bool = False
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        use_enum_values=True,
    )
