from typing import Callable

from fastapi import FastAPI
from loguru import logger

from app.database import supabase


def create_start_app_handler(app: FastAPI) -> Callable:

    @logger.catch
    async def start_app() -> None:
        try:
            if supabase.client is not None:
                _ = supabase.auth()
                logger.info("Supabase Connected.")
            else:
                raise Exception("Supabase client not initialized")
        except Exception as e:
            raise e

    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:

    @logger.catch
    async def stop_app() -> None:
        try:
            if supabase.client is not None:
                supabase.client = None
                logger.info("Closed Supabase Connection")
        except Exception as e:
            raise e

    return stop_app
