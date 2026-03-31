from backend.db.connections.postgres import PostgresDBConnection
from pipeline.ingestion.ingestor import DocumentIngestor
from backend.mq import RabbitMQConnection
from utils.logger import get_logger
from backend.config import Config
import json

logger = get_logger("mq.consumer")


class IngestionConsumer:
    @staticmethod
    async def update_document_status(
        document_id: int,
        new_status: str,
        error_message: str = None
    ):
        try:
            async with PostgresDBConnection.get_db_connection() as conn:
                await conn.execute(
                    Config.UPDATE_DOCUMENT_STATUS,
                    new_status,
                    error_message,
                    document_id
                )
                logger.info(
                    f"Document ID {document_id} status updated to {new_status}"
                )

        except Exception as e:
            logger.critical(
                f"CRITICAL: Failed to update document {document_id} status "
                f"to {new_status}. Error: {e}"
            )

    @staticmethod
    async def start_consuming():
        try:
            channel = await RabbitMQConnection.get_channel()

            await channel.set_qos(prefetch_count=1)

            queue = await channel.declare_queue(
                Config.RABBITMQ_QUEUE_NAME,
                durable=True
            )

            logger.info("Ingestion Consumer started. Waiting for messages...")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            payload = json.loads(message.body.decode("utf-8"))
                            file_path = payload["file_path"]
                            user_id = payload["user_id"]
                            document_id = payload["document_id"]

                            logger.info(
                                f"Received ingestion job for document ID "
                                f"{document_id}..."
                            )

                            success, error_msg = await DocumentIngestor.ingest_document(
                                file_path, user_id, document_id
                            )

                            if success:
                                await IngestionConsumer.update_document_status(
                                    document_id, "completed"
                                )
                                logger.info(
                                    f"Successfully processed document ID: "
                                    f"{document_id}"
                                )
                            else:
                                await IngestionConsumer.update_document_status(
                                    document_id, "failed", error_msg
                                )
                                logger.error(
                                    f"Ingestion failed for document ID: "
                                    f"{document_id}. Error: {error_msg}"
                                )

                        except Exception as e:
                            logger.exception(
                                f"Critical error while consuming message: {e}"
                            )

                            if 'document_id' in locals():
                                await IngestionConsumer.update_document_status(
                                    document_id, "failed", str(e)
                                )

        except Exception as e:
            logger.error(f"Consumer connection failure: {e}")
            raise


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(IngestionConsumer.start_consuming())
    except KeyboardInterrupt:
        logger.info("Ingestion Consumer stopped gracefully.")
