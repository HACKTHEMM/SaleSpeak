from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: str
    SERP_API_KEY:str
    BASE_API_V1: Optional[str] = "/api/v1"
    APP_VERSION: Optional[str] = "1.0.0"
    APP_TITLE: Optional[str] = "Backend Service"
    APP_DESCRIPTION: Optional[str] = "This is a backend service application."
    SUPABASE_DB_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    LOGIN_ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int
    RESET_PASSWORD_TOKEN_EXPIRE_MINUTES: str
    EMAIL_CONFIRMATION_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_SECRET: str
    ACCESS_TOKEN_SECRET: str
    SIGNUP_TOKEN_SECRET: str
    FORGOT_PASSWORD_TOKEN_SECRET: str
    PORT: int
    DEBUG: Optional[bool] = False
    LOG_DIR: Optional[str] = "logs"
    MODEL_ID: Optional[str] = None
    COMPANY_NAME: str = "LenDen Club"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

ENV_SETTINGS = Settings()