import datetime
from typing import Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schema.enums import PermissionType
from app.utils.helper import strip_whitespace

class Roles(BaseModel):
    role_name: str
    permissions: Dict[str, bool] = {perm.value: False for perm in PermissionType}
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        use_enum_values=True,
    )
    
    @field_validator("*", mode="before")
    def apply_strip_whitespace(cls, value):
        return strip_whitespace(value)

class RolesDB(Roles):
    id: UUID | None = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
