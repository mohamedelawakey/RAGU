from utils.logger import get_logger
from backend.config import Config
import aio_pika

logger = get_logger("mq.connection")


class RabbitMQConnection:
    _connection: aio_pika.RobustConnection = None

    @classmethod
    async def get_connection(cls) -> aio_pika.RobustConnection:
        try:
            if cls._connection is None or cls._connection.is_closed:
                logger.info("Connecting to RabbitMQ...")
                cls._connection = await aio_pika.connect_robust(Config.RABBITMQ_URL)
                logger.info("RabbitMQ robust connection established.")
            return cls._connection

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    @classmethod
    async def get_channel(cls) -> aio_pika.RobustChannel:
        try:
            connection = await cls.get_connection()
            logger.info("Getting channel...")
            channel = await connection.channel()
            logger.info("Channel obtained.")
            return channel
        except Exception as e:
            logger.error(f"Failed to get channel: {e}")
            raise

    @classmethod
    async def close(cls):
        try:
            if cls._connection and not cls._connection.is_closed:
                await cls._connection.close()
                logger.info("RabbitMQ connection closed.")
        except Exception as e:
            logger.error(f"Failed to close RabbitMQ connection: {e}")
            raise
