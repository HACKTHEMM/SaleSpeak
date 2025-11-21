import datetime
from typing import Any, Dict, Optional, Union
import re
from pydantic import BaseModel, field_validator, validator, model_validator
from app.utils.helper import strip_whitespace

class Name(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator("first_name", "middle_name", "last_name", pre=True, always=True)
    def capitalize_name(cls, value: str) -> str:
        if value:
            return value.capitalize()
        return value
    
    @field_validator("*", mode="before")
    def apply_strip_whitespace(cls, value):
        return strip_whitespace(value)

class phoneNumber(BaseModel):
    country_code: Optional[str] = "+1"
    phone_number: Optional[str]
    
    @field_validator("*", mode="before")
    def apply_strip_whitespace(cls, value):
        return strip_whitespace(value)

    @model_validator(mode="after")
    def validate_full_number(self):
        if not self.phone_number:
            raise ValueError("phone_number is required")
        
        if not self.country_code.startswith("+"):
            raise ValueError("country_code must start with '+'")

        full_number = f"{self.country_code}{self.phone_number}"

        pattern = r"^\+[1-9]\d{1,14}$"
        if not re.match(pattern, full_number):
            raise ValueError(f"Invalid phone number format: {full_number}")

        return self

class Address(BaseModel):
    street_address: Optional[str] = None
    street_address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    
    @field_validator("*", mode="before")
    def apply_strip_whitespace(cls, value):
        return strip_whitespace(value)

class username(BaseModel):
    first_name: str
    last_name: str
    
    @validator("first_name", "last_name", pre=True, always=True)
    def capitalize_name(cls, value: str) -> str:
        if value:
            return value.capitalize()
        return value
    
    @field_validator("*", mode="before")
    def apply_strip_whitespace(cls, value):
        return strip_whitespace(value)
