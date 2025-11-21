import json
import logging
import time
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from loguru import logger
from starlette.requests import Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.Config import ENV_SETTINGS
from app.core.events import create_start_app_handler, create_stop_app_handler
from app.utils.logging import loguru_sink_serializer

def configure_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        try:
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
        except Exception as e:
            return ORJSONResponse(
                json.dumps(
                    {
                        "loc":[],
                        "msg": f"Internal Server Error: {str(e)}",
                        "type":"unexpected_error",
                    }
                ),
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            )

def configure_logging(app:FastAPI):
    logger.remove()
    level_name = "DEBUG" if ENV_SETTINGS.DEBUG else "INFO"
    logger.add(
        loguru_sink_serializer,
        level=level_name,
        enqueue=True,
        serialize=True,
    )
    logging.getLogger("passlib").setLevel(logging.ERROR)
    app.logger = logger

def configure_database(app: FastAPI):
    app.add_event_handler("startup", create_start_app_handler(app))
    app.add_event_handler("shutdown", create_stop_app_handler(app))