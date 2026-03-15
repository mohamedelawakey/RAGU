from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from pipeline.parser.parser import DocumentExtractor
from pipeline.embeddings.embedding import Embedding
from pipeline.chunking.chunker import TextSplitter
from pipeline.cleaning.cleaner import Cleaner
from pymilvus import Collection, utility
from utils.logger import get_logger
from pipeline.config import Config
import uuid
import os

logger = get_logger("ingestion.module")


class DocumentIngestor:
    @staticmethod
    async def ingest_document(filePath: str, user_id: str) -> bool:
        logger.info(f"Starting ingestion pipeline for document: {filePath} [user_id={user_id}]")

        collection_name = (Config.COLLECTION_NAME or "").strip()
        if not collection_name:
            logger.error("Config.COLLECTION_NAME is missing or empty. Please set a valid Milvus collection name.")
            raise ValueError("Config.COLLECTION_NAME is missing or empty.")

        filename = os.path.basename(filePath)

        try:
            logger.info(f"Registering document in Postgres as 'processing' for user {user_id}...")
            async with PostgresDBConnection.get_db_connection() as conn:
                document_id = await conn.fetchval(
                    Config.INSERT_DOCUMENT_NODE, filename, filePath, user_id
                )
        except Exception as e:
            logger.exception(f"Failed to register document '{filename}' in Postgres.")
            raise RuntimeError(f"Database error while registering document: {e}")

        logger.info("Verifying Milvus collection availability...")
        await AsyncMilvusDBConnection.get_connection()
        if not utility.has_collection(collection_name):
            logger.error(f"Milvus collection '{collection_name}' does not exist. Please run setup first.")
            raise RuntimeError(f"Milvus collection '{collection_name}' does not exist.")

        logger.info("Extracting text from document...")
        text = DocumentExtractor.extract(filePath)
        if not text:
            logger.error(f"Failed to extract text from {filePath}")
            raise ValueError(f"No text extracted from document '{filePath}'")

        logger.info("Cleaning extracted text...")
        text = Cleaner.clean(text)
        if not text:
            logger.error(f"Text became empty after cleaning {filePath}")
            raise ValueError("Text became empty after cleaning")

        logger.info("Chunking extracted text...")
        chunks = TextSplitter.text_split(text)
        if not chunks:
            logger.error(f"Failed to generate chunks for {filePath}")
            raise RuntimeError("Document chunking failed")

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = Embedding.embed(chunks)
        if not embeddings or len(embeddings) != len(chunks):
            logger.error("Failed to generate embeddings or mismatch in chunk/embedding count.")
            raise RuntimeError("Document embedding failed")

        try:
            logger.info("Saving text chunks to PostgreSQL...")
            chunk_ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
            async with PostgresDBConnection.get_db_connection() as conn:

                chunk_records = []
                for i in range(len(chunks)):
                    chunk_records.append((
                        chunk_ids[i],
                        document_id,
                        None,
                        chunks[i]
                    ))

                await conn.executemany(
                    Config.INSERT_CHUNKS, chunk_records
                )
                logger.info(f"Successfully saved {len(chunks)} chunks to Postgres under Document ID: {document_id}")

            logger.info("Inserting embeddings into Milvus...")
            collection = Collection(collection_name)

            document_ids_for_milvus = [document_id] * len(chunks)
            user_ids_for_milvus = [user_id] * len(chunks)

            milvus_data = [
                chunk_ids,
                user_ids_for_milvus,
                document_ids_for_milvus,
                embeddings
            ]

            insert_result = collection.insert(milvus_data)
            collection.flush()
            logger.info(f"Successfully inserted {insert_result.insert_count} vectors into Milvus (Collection: {collection_name}).")

            async with PostgresDBConnection.get_db_connection() as conn:
                await conn.execute(
                    Config.UPDATE_DOCUMENT_STATUS,
                    "completed",
                    document_id
                )
                logger.info(f"Document ID {document_id} marked as 'completed'.")

            return True

        except Exception as e:
            logger.exception(f"Critical error during database ingestion for '{filePath}'")
            try:
                async with PostgresDBConnection.get_db_connection() as conn:
                    await conn.execute(
                        Config.UPDATE_DOCUMENT_STATUS,
                        "failed",
                        document_id
                    )
            except Exception:
                logger.error(f"Failed to update document {document_id} status to 'failed'.")
            raise RuntimeError(f"Critical ingestion error: {e}")
