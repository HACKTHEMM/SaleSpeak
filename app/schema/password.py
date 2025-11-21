from pydantic import BaseModel


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str


class SetPassword(BaseModel):
    new_password: str
