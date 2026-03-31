from backend.db.connections.milvus import MilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from backend.mq.consumers import IngestionConsumer
from utils.logger import get_logger
from dotenv import load_dotenv
import asyncio

logger = get_logger("worker.main")


async def init_services():
    logger.info("Initializing Worker Database Connections...")

    await PostgresDBConnection.init_db()

    MilvusDBConnection.get_instance().connect()

    logger.info("Databases connected successfully.")


async def main():
    load_dotenv()

    try:
        await init_services()
        await IngestionConsumer.start_consuming()

        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user, shutting down.")
    except Exception as e:
        logger.exception(f"Fatal worker error: {e}")
    finally:
        await PostgresDBConnection.close_all()
        logger.info("Worker shutdown gracefully.")

if __name__ == "__main__":
    asyncio.run(main())
