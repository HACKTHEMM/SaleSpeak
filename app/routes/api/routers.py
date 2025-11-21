from fastapi import APIRouter
from app.Config import ENV_SETTINGS
from app.routes.api.v1.user import user as user_endpoints
from app.routes.api.v1.auth import auth as auth_endpoints
from app.routes.api.v1.roles import roles as roles_endpoints
from app.routes.api.v1.voice_assistant import voice_assistant_router

routers = APIRouter()

routers.include_router(
    user_endpoints, prefix=ENV_SETTINGS.BASE_API_V1 + "/user", tags=["User"]
)

routers.include_router(
    auth_endpoints, prefix=ENV_SETTINGS.BASE_API_V1 + "/auth", tags=["Auth"]
)

routers.include_router(
    roles_endpoints, prefix=ENV_SETTINGS.BASE_API_V1 + "/roles", tags=["Roles"]
)

routers.include_router(
    voice_assistant_router, prefix=ENV_SETTINGS.BASE_API_V1 + "/voice-assistant", tags=["Voice Assistant"]
)