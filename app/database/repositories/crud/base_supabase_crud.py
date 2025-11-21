from enum import Enum
from typing import List, Optional, Union
from uuid import UUID
from supabase import Client
from app.database.repositories.crud.base import (
    ID,
    AsyncPagingAndSortingRepository,
    Meta,
    PageRequest,
    PaginatedResponse,
    SortingOrder,
    T,
)

def model_serializer(entity, id_field="_id"):
    if hasattr(entity, "model_dump"):
        result = entity.model_dump(by_alias=True)
    elif hasattr(entity, "dict"):
        result = entity.dict(by_alias=True)
    else:
        result = entity
    return result


class BaseSupabaseCrud(AsyncPagingAndSortingRepository[T]):
    def __init__(
        self,
        client: Client,
        table_name: str,
        id_field: str = "id",
        default_filter: dict = None,
    ):
        self.client = client
        self.table_name = table_name
        self.id_field = id_field
        self.default_filter = default_filter or {}
        self.serializer = lambda x: model_serializer(x, self.id_field)

    def _apply_filters(self, query, filters: dict):
        for key, value in filters.items():
            if isinstance(value, dict):
                for op, val in value.items():
                    if op == "$gt":
                        query = query.gt(key, val)
                    elif op == "$gte":
                        query = query.gte(key, val)
                    elif op == "$lt":
                        query = query.lt(key, val)
                    elif op == "$lte":
                        query = query.lte(key, val)
                    elif op == "$ne":
                        query = query.neq(key, val)
                    elif op == "$in":
                        query = query.in_(key, val)
                    elif op == "$regex":
                        query = query.ilike(key, f"%{val}%")
            else:
                query = query.eq(key, value)
        return query

    async def findOne(
        self, filter: dict, projection: dict = None, sort: list = None
    ) -> Optional[T]:
        query = self.client.table(self.table_name).select(
            ",".join(projection.keys()) if projection else "*"
        )
        
        combined_filter = {**filter, **self.default_filter}
        query = self._apply_filters(query, combined_filter)

        if sort:
            for field, order in sort:
                query = query.order(field, desc=(order == -1))

        query = query.limit(1)
        response = query.execute()
        
        return response.data[0] if response.data else None

    async def findOneById(self, id: ID) -> Optional[T]:
        query = self.client.table(self.table_name).select("*")
        query = query.eq(self.id_field, id)
        query = self._apply_filters(query, self.default_filter)
        
        response = query.execute()
        return response.data[0] if response.data else None

    async def findAllById(self, ids: List[ID]) -> List[T]:
        query = self.client.table(self.table_name).select("*")
        query = query.in_(self.id_field, ids)
        query = self._apply_filters(query, self.default_filter)
        
        response = query.execute()
        return response.data

    async def exists(self, entity: T) -> bool:
        entity_dict = self.serializer(entity)
        query = self.client.table(self.table_name).select(self.id_field)
        
        combined_filter = {**entity_dict, **self.default_filter}
        query = self._apply_filters(query, combined_filter)
        query = query.limit(1)
        
        response = query.execute()
        return len(response.data) > 0

    async def existsByQuery(self, query_filter: dict) -> bool:
        query = self.client.table(self.table_name).select(self.id_field)
        
        combined_filter = {**query_filter, **self.default_filter}
        query = self._apply_filters(query, combined_filter)
        query = query.limit(1)
        
        response = query.execute()
        return len(response.data) > 0

    async def existsById(self, id: ID) -> bool:
        query = self.client.table(self.table_name).select(self.id_field)
        query = query.eq(self.id_field, id)
        query = self._apply_filters(query, self.default_filter)
        query = query.limit(1)
        
        response = query.execute()
        return len(response.data) > 0

    async def count(self, filter: dict = None) -> int:
        query = self.client.table(self.table_name).select(
            self.id_field, count="exact"
        )
        
        if filter:
            combined_filter = {**filter, **self.default_filter}
        else:
            combined_filter = self.default_filter
            
        query = self._apply_filters(query, combined_filter)
        
        response = query.execute()
        return response.count

    async def delete(self, entity: T) -> bool:
        entity_dict = self.serializer(entity)
        entity_id = entity_dict.get(self.id_field)
        
        query = self.client.table(self.table_name).delete()
        query = query.eq(self.id_field, entity_id)
        query = self._apply_filters(query, self.default_filter)
        
        response = query.execute()
        return len(response.data) > 0

    async def deleteOne(self, filter: dict) -> bool:
        query = self.client.table(self.table_name).delete()
        
        combined_filter = {**filter, **self.default_filter}
        query = self._apply_filters(query, combined_filter)
        
        response = query.execute()
        return len(response.data) > 0

    async def deleteById(self, id: ID) -> bool:
        query = self.client.table(self.table_name).delete()
        query = query.eq(self.id_field, id)
        query = self._apply_filters(query, self.default_filter)
        
        response = query.execute()
        return len(response.data) > 0

    async def deleteAll(self, filter: dict) -> int:

        query = self.client.table(self.table_name).delete()
        
        combined_filter = {**filter, **self.default_filter}
        query = self._apply_filters(query, combined_filter)
        
        response = query.execute()
        return len(response.data)

    async def deleteAllById(self, ids: List[ID]) -> bool:

        query = self.client.table(self.table_name).delete()
        query = query.in_(self.id_field, ids)
        query = self._apply_filters(query, self.default_filter)
        
        response = query.execute()
        return len(response.data) == len(ids)

    async def replace(self, entity: T) -> T:
        entity_dict = self.serializer(entity)
        entity_id = entity_dict.get(self.id_field)
        
        if not entity_id:
            raise ValueError("Entity must have an ID to be replaced")
        
        query = self.client.table(self.table_name).update(entity_dict)
        query = query.eq(self.id_field, entity_id)
        
        response = query.execute()
        
        if not response.data:
            raise ValueError("No document found to replace")
        
        return response.data[0]

    async def save(self, entity: T) -> T:
        import datetime
        from uuid import UUID

        def serialize(value):
            if isinstance(value, UUID):
                return str(value)
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, (datetime.datetime, datetime.date)):
                return value.isoformat()
            if isinstance(value, dict):
                return {k: serialize(v) for k, v in value.items()}
            if isinstance(value, list):
                return [serialize(v) for v in value]
            return value

        if hasattr(entity, "model_dump"):
            item = serialize(entity.model_dump())
        elif hasattr(entity, "dict"):
            item = serialize(entity.dict())
        else:
            item = entity

        if self.id_field in item and item[self.id_field] is None:
            del item[self.id_field]

        query = self.client.table(self.table_name).insert(item)
        response = query.execute()
        
        return response.data[0] if response.data else None

    async def findAll(
        self,
        filter: dict = None,
        pagination: Optional[PageRequest] = None,
        projection: dict = None,
    ) -> Union[PaginatedResponse, List[dict]]:
        select_fields = ",".join(projection.keys()) if projection else "*"
        query = self.client.table(self.table_name).select(select_fields, count="exact")

        if filter:
            combined_filter = {**filter, **self.default_filter}
        else:
            combined_filter = self.default_filter
            
        query = self._apply_filters(query, combined_filter)

        if pagination:
            if pagination.sorting:
                ascending = pagination.sorting.sort_order == SortingOrder.ASC
                query = query.order(pagination.sorting.sort_field, desc=not ascending)

            offset = (pagination.paging.page - 1) * pagination.paging.limit
            query = query.range(offset, offset + pagination.paging.limit - 1)

            response = query.execute()

            return PaginatedResponse(
                docs=response.data,
                meta=Meta(
                    page=pagination.paging.page,
                    limit=pagination.paging.limit,
                    total=response.count or 0,
                ),
            )
        else:
            response = query.execute()
            return response.data

    async def update_one(self, filter: dict, update: dict, **kwargs) -> bool:
        query = self.client.table(self.table_name).update(update)
        
        combined_filter = {**filter, **self.default_filter}
        query = self._apply_filters(query, combined_filter)
        
        response = query.execute()
        return len(response.data) > 0

    async def update(self, filter: dict, update: dict, **kwargs):
        query = self.client.table(self.table_name).update(update)
        
        combined_filter = {**filter, **self.default_filter}
        query = self._apply_filters(query, combined_filter)
        
        response = query.execute()
        return response.data[0] if response.data else None

    async def update_many(self, filter: dict, update: dict, **kwargs) -> int:
        query = self.client.table(self.table_name).update(update)
        
        combined_filter = {**filter, **self.default_filter}
        query = self._apply_filters(query, combined_filter)
        
        response = query.execute()
        return len(response.data)

    async def filterByName(self, name: str) -> Optional[T]:
        query = self.client.table(self.table_name).select("*")
        query = query.ilike("name", f"%{name}%")
        query = self._apply_filters(query, self.default_filter)
        
        response = query.execute()
        return response.data[0] if response.data else None
