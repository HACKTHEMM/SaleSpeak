import time
from fastapi import FastAPI, status, HTTPException
from fastapi.responses import ORJSONResponse
from starlette.requests import Request
from starlette.responses import Response
from app.Config import ENV_SETTINGS
from app.http_exception import http_error_handler
from app.schema.health import Health_Schema
from app.utils.uptime import getUptime
from app.routes.api.routers import routers
from app.routes.api.v1.voice_assistant import set_assistant
from app.database import supabase
from app.core.app_configure import configure_database, configure_logging, configure_middleware
import os
import sys

start_time = time.time()

app = FastAPI(
    title = ENV_SETTINGS.APP_TITLE,
    description= ENV_SETTINGS.APP_DESCRIPTION,
    version= "v" + ENV_SETTINGS.APP_VERSION
)

configs = [
    configure_database,
    configure_logging,
    configure_middleware,
]

GROQ_API_KEY = ENV_SETTINGS.GROQ_API_KEY

@app.on_event("startup")
async def startup_event():
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not found!")

    try:
        from app.core.assistant.voice_assistant import IntegratedVoiceAssistant
        integrated_assistant = IntegratedVoiceAssistant()
        assistant_instance = integrated_assistant.get_voice_assistant()
        set_assistant(assistant_instance)
    except ImportError as e:
        sys.exit(1)
    except Exception as e:
        sys.exit(1)

@app.get("/health",response_class=ORJSONResponse, response_model=Health_Schema, tags=["Health Route"])
async def health_check(request: Request, response: Response):
    database_connected = False
    if supabase.admin_client:
        try:
            supabase.admin_client.auth.admin.list_users()
            database_connected = True
        except Exception as e:
            print(f"Database connection check failed: {e}")
            database_connected = False
    return Health_Schema(
        success=True,
        status=status.HTTP_200_OK,
        app=ENV_SETTINGS.APP_TITLE,
        version=ENV_SETTINGS.APP_VERSION,
        ip_address=request.client.host,
        uptime=getUptime(start_time),
        database_connected=database_connected
    )

for app_configure in configs:
    app_configure(app)

app.include_router(routers)
app.add_exception_handler(HTTPException, http_error_handler)