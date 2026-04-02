from pymilvus import connections, utility, Collection
from pymilvus.exceptions import MilvusException
from utils.logger import get_logger
from backend.config import Config
from typing import Optional
import threading
import asyncio

logger = get_logger("milvus.module")


class AsyncMilvusDBConnection:
    _lock: Optional[asyncio.Lock] = None
    _init_lock = threading.Lock()
    _connected: bool = False

    @staticmethod
    async def get_connection(
        alias: str = Config.MILVUS_ALIAS,
        timeout: float = Config.MILVUS_TIMEOUT
    ) -> bool:
        with AsyncMilvusDBConnection._init_lock:
            if AsyncMilvusDBConnection._lock is None:
                AsyncMilvusDBConnection._lock = asyncio.Lock()

        if (
            AsyncMilvusDBConnection._connected or
            connections.has_connection(alias)
        ):
            return True

        async with AsyncMilvusDBConnection._lock:
            if (
                AsyncMilvusDBConnection._connected or
                connections.has_connection(alias)
            ):
                AsyncMilvusDBConnection._connected = True
                return True

            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: connections.connect(
                        alias=alias,
                        host=Config.MILVUS_HOST,
                        port=Config.MILVUS_PORT,
                        timeout=timeout
                    )
                )

                AsyncMilvusDBConnection._connected = True
                logger.info(
                    f"Connected to Milvus successfully on "
                    f"{Config.MILVUS_HOST}:{Config.MILVUS_PORT}"
                )

                return True

            except MilvusException as e:
                logger.exception("MilvusException during connection")
                raise ConnectionError(
                    f"Failed to connect to Milvus: {e}"
                ) from e

            except Exception as e:
                logger.exception("Unexpected error connecting to Milvus")
                raise ConnectionError(f"Unexpected error connecting to Milvus: {e}") from e

    @staticmethod
    async def initialize_collection(collection_name: str, schema) -> None:
        await AsyncMilvusDBConnection.get_connection()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: AsyncMilvusDBConnection._init_collection_sync(collection_name, schema)
        )

    @staticmethod
    def _init_collection_sync(collection_name: str, schema) -> None:
        from pymilvus import utility, Collection
        if not utility.has_collection(collection_name, using=Config.MILVUS_ALIAS):
            collection = Collection(
                name=collection_name,
                schema=schema,
                using=Config.MILVUS_ALIAS,
            )
            index_params = {
                "metric_type": Config.MILVUS_METRIC_TYPE,
                "index_type": Config.MILVUS_INDEX_TYPE,
                "params": {"M": Config.MILVUS_HNSW_M, "efConstruction": Config.MILVUS_HNSW_EF_CONSTRUCTION}
            }
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            collection.load()
            logger.info(f"Initialized collection: {collection_name}")
        else:
            logger.info(f"Collection {collection_name} already exists.")

