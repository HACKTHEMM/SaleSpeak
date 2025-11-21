from supabase import create_client, Client
from app.database.connections.db_abs import Database


class Supabase(Database):
    client: Client = None
    admin_client: Client = None

    def init_connection(self, url: str, key: str, service_key: str = None):
        self.client = create_client(url, key)
        if service_key:
            self.admin_client = create_client(url, service_key)
        return self.client

    async def execute_query(self, query):
        try:
            response = await query.execute()
            return response
        except Exception as e:
            print(f"Query execution failed: {e}")
            raise e

    def table(self, table_name: str):
        if self.client is None:
            raise Exception("Database not connected")
        return self.client.table(table_name)

    def storage(self):
        if self.client is None:
            raise Exception("Database not connected")
        return self.client.storage

    def auth(self):
        if self.client is None:
            raise Exception("Database not connected")
        return self.client.auth

    async def rpc(self, function_name: str, params: dict = None):
        try:
            if params:
                response = await self.client.rpc(function_name, params).execute()
            else:
                response = await self.client.rpc(function_name).execute()
            return response
        except Exception as e:
            print(f"RPC call failed: {e}")
            raise e
