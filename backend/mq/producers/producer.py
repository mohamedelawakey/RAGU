from backend.mq import RabbitMQConnection
from utils.logger import get_logger
from backend.config import Config
import aio_pika
import json

logger = get_logger("mq.producer")


class IngestionProducer:
    @staticmethod
    async def publish_ingestion_job(file_path: str, user_id: str, document_id: int):
        try:
            channel = await RabbitMQConnection.get_channel()

            await channel.declare_queue(
                Config.RABBITMQ_QUEUE_NAME,
                durable=True
            )

            payload = {
                "file_path": file_path,
                "user_id": user_id,
                "document_id": document_id
            }

            message = aio_pika.Message(
                body=json.dumps(payload).encode("utf-8"),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await channel.default_exchange.publish(
                message,
                routing_key=Config.RABBITMQ_QUEUE_NAME
            )

            logger.info(f"Successfully published ingestion job for doc_id: {document_id}")

        except Exception as e:
            logger.error(f"Failed to publish ingestion job to RabbitMQ: {e}")
            raise
