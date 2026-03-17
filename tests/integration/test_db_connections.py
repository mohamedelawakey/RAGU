import pytest
import os
import asyncio
from backend.db.connections.postgres import PostgresDBConnection
from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.redis import AsyncRedisDBConnection
from pymilvus import utility


@pytest.mark.asyncio
class TestDatabaseConnections:
    async def test_postgres_connection(self):
        # Simply trying to execute a simple query
        async with PostgresDBConnection.get_db_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    async def test_milvus_connection(self):
        # Just getting connection verifies authentication
        await AsyncMilvusDBConnection.get_connection()
        # Verify utility can ping essentially
        collections = utility.list_collections()
        assert isinstance(collections, list)

    async def test_redis_connection(self):
        pool = await AsyncRedisDBConnection.get_pool()
        assert pool is not None
