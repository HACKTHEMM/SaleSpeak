from typing import List, Optional
from app.database.repositories.crud.base import ID, AsyncCrudRepository, T


class AsyncListCrudRepository(AsyncCrudRepository[T]):
    async def findAll(
        self, 
        filter: dict = None, 
        projection: dict = None,
        order_by: str = None,
        limit: int = None
    ) -> List[T]:
        ...

    async def findAllByID(
        self, 
        ids: List[ID],
        projection: dict = None
    ) -> List[T]:
        ...
