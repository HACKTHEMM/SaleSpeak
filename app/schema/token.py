from typing import Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseToken(BaseModel):
    access_token: str
    refresh_token: str
    scope: str


class TokenData(BaseModel):
    user_id: Union[UUID, str]
    user_type: Literal["admin","user"] = "admin"
    scope: Literal["login", "forgot_password", "create_account"] = "login"
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )
    
class RefreshTokenPost(BaseModel):
    refresh_token: str


class OnlyRefreshToken(BaseModel):
    refresh_token: str