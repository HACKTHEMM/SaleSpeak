from fastapi import status
from loguru import logger
from app import http_exception
from app.database import supabase
from app.database.models.token import RefreshTokenCreate, RefreshTokenDB
from app.database.repositories.crud.base_supabase_crud import BaseSupabaseCrud

class RefreshTokenRepository(BaseSupabaseCrud[RefreshTokenDB]):
    def __init__(self):
        super().__init__(
            client=supabase.client,
            table_name="tokens",
            id_field="id"
        )

    async def new(self, data: RefreshTokenCreate):
        data = RefreshTokenDB(**data.model_dump())
        try:
            res = await self.save(data)
            return res
        except Exception as e:
            logger.error(f"Error creating token: {e}")
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                raise await http_exception.conflict_exception("Token already exists")
            raise await http_exception.internal_server_error_exception("Error saving token")

refresh_token_repo = RefreshTokenRepository()
