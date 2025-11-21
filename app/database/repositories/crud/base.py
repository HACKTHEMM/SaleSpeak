from enum import Enum
from typing import Any, Generic, List, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, field_validator

T = TypeVar("T")

ID = Union[str, int, UUID]


class SortingOrder(int, Enum):
    ASC = 1
    DESC = -1


class Sort(BaseModel):
    sort_field: str
    sort_order: SortingOrder


class Page(BaseModel):
    page: int = 1
    limit: int = 10

    @field_validator("page", "limit", mode="before")
    @classmethod
    def validate_positive_values(cls, value):
        if value < 1:
            raise ValueError("Values for page and limit must be positive integers")
        return value

    @field_validator("limit", mode="before")
    @classmethod
    def validate_max_limit(cls, value):
        if value > 100:
            raise ValueError("Limit cannot exceed 100")
        return value


class PageRequest(BaseModel):
    paging: Page
    sorting: Sort = None


class Meta(Page):
    total: int


class PaginatedResponse(BaseModel):
    docs: List[Any]
    meta: Meta


class AsyncCrudRepository(Generic[T]):
    async def findOne(self, filter: dict, projection: dict = None) -> T: ...

    async def findOneById(self, id: ID) -> T: ...

    async def findAll(self, filter: dict, projection: dict = None) -> List[T]: ...

    async def findAllById(self, ids: List[ID]) -> List[T]: ...

    async def exists(self, entity: T) -> bool: ...

    async def existsById(self, id: ID) -> bool: ...

    async def count(self, filter: Union[dict, None]) -> int: ...

    async def delete(self, entity: T) -> bool: ...

    async def deleteById(self, id: ID) -> bool: ...

    async def deleteAll(self, entities: List[T]) -> bool: ...

    async def deleteAllById(self, ids: List[ID]) -> bool: ...

    async def save(self, entity: T) -> T: ...

    async def replace(self, entity: T) -> T: ...


class AsyncPagingAndSortingRepository(AsyncCrudRepository[T]):
    async def findAll(
        self, filter: dict, pagination: PageRequest = None, projection: dict = None
    ) -> Union[PaginatedResponse, List[T]]: ...

    async def findAllById(self, ids: List[ID], pagination: PageRequest = None) -> List[T]: ...
