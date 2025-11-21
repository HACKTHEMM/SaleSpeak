from fastapi import status
from loguru import logger
from app import http_exception
from app.database import supabase
from app.database.models.roles import Roles, RolesDB
from app.database.repositories.crud.base_supabase_crud import BaseSupabaseCrud

class RolesRepository(BaseSupabaseCrud[RolesDB]):
    def __init__(self):
        super().__init__(
            client=supabase.client,
            table_name="roles",
            id_field="id"
        )

    async def new(self, data: Roles):
        data = RolesDB(**data.model_dump())
        try:
            res = await self.save(data)
            return res
        except Exception as e:
            logger.error(f"Error creating role: {e}")
            if "duplicate" in str(e).lower():
                raise await http_exception.conflict_exception("Role already exists")
            raise await http_exception.internal_server_error_exception("Error saving role")

roles_repo = RolesRepository()
