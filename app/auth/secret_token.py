from fastapi import HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader
from app.Config import ENV_PROJECT
from app.oauth import verify_access_token
import app.http_exception as http_exception

api_key_header = APIKeyHeader(name="X-API-Key")

async def check_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == ENV_PROJECT.API_ACCESS_SECRET_TOKEN:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
    )