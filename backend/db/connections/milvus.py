from pymilvus.exceptions import MilvusException
from backend.config import Config
from pymilvus import connections
from typing import Optional
from . import get_logger
import asyncio

logger = get_logger("milvus.module")


class AsyncMilvusDBConnection:
    _lock: Optional[asyncio.Lock] = None
    _connected: bool = False

    @staticmethod
    async def get_connection(
        alias: str = Config.MILVUS_ALIAS,
        timeout: float = Config.MILVUS_TIMEOUT
    ) -> bool:
        """
        Ensure a Milvus connection exists for the given alias, establishing one if necessary.
        
        Parameters:
            alias (str): Connection alias to use or check for in the Milvus connection registry.
            timeout (float): Connection timeout in seconds for the attempt.
        
        Returns:
            bool: `true` if a connection for the alias is present (or was successfully established), `false` otherwise.
        
        Raises:
            ConnectionError: If establishing a new connection fails.
        """
        if AsyncMilvusDBConnection._lock is None:
            AsyncMilvusDBConnection._lock = asyncio.Lock()

        if AsyncMilvusDBConnection._connected or connections.has_connection(alias):
            return True

        async with AsyncMilvusDBConnection._lock:
            if AsyncMilvusDBConnection._connected or connections.has_connection(alias):
                AsyncMilvusDBConnection._connected = True
                return True

            try:
                connections.connect(
                    alias=alias,
                    host=Config.MILVUS_HOST,
                    port=Config.MILVUS_PORT,
                    timeout=timeout
                )

                AsyncMilvusDBConnection._connected = True
                logger.info(f"Connected to Milvus successfully on {Config.MILVUS_HOST}:{Config.MILVUS_PORT}")

                return True

            except MilvusException as e:
                logger.error(f"MilvusException during connection: {e}")
                raise ConnectionError(f"Failed to connect to Milvus: {e}")

            except Exception as e:
                logger.error(f"Unexpected error connecting to Milvus: {e}", exc_info=True)
                raise ConnectionError(f"Unexpected error connecting to Milvus: {e}")
