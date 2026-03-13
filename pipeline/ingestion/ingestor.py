from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from pipeline.parser.parser import DocumentExtractor
from pipeline.embeddings.embedding import Embedding
from pipeline.chunking.chunker import TextSplitter
from pipeline.cleaning.cleaner import Cleaner
from pymilvus import Collection, utility
from pipeline import get_logger
from pipeline import Config
import uuid
import os

logger = get_logger("ingestion.module")


class DocumentIngestor:
    @staticmethod
    async def ingest_document(filePath: str) -> bool:
        logger.info(f"Starting ingestion pipeline for document: {filePath}")

        collection_name = (Config.COLLECTION_NAME or "").strip()
        if not collection_name:
            logger.error("Config.COLLECTION_NAME is missing or empty. Please set a valid Milvus collection name.")
            return False

        logger.info("Extracting text from document...")
        text = DocumentExtractor.extract(filePath)
        if not text:
            logger.error(f"Failed to extract text from {filePath}")
            return False

        logger.info("Cleaning extracted text...")
        text = Cleaner.clean(text)
        if not text:
            logger.error(f"Text became empty after cleaning {filePath}")
            return False

        logger.info("Chunking extracted text...")
        chunks = TextSplitter.text_split(text)
        if not chunks:
            logger.error(f"Failed to generate chunks for {filePath}")
            return False

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = Embedding.embed(chunks)
        if not embeddings or len(embeddings) != len(chunks):
            logger.error("Failed to generate embeddings or mismatch in chunk/embedding count.")
            return False

        filename = os.path.basename(filePath)
        chunk_ids = [str(uuid.uuid4()) for _ in range(len(chunks))]

        try:
            logger.info("Saving document metadata and text chunks to PostgreSQL...")
            async with PostgresDBConnection.get_db_connection() as conn:
                document_id = await conn.fetchval(
                    Config.INSERT_DOCUMENT_NODE, filename, filePath
                )

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

            logger.info("Connecting to Milvus to store embeddings...")
            await AsyncMilvusDBConnection.get_connection()

            if not utility.has_collection(collection_name):
                logger.error(f"Milvus collection '{collection_name}' does not exist. Please run setup.")
                return False

            collection = Collection(collection_name)

            document_ids_for_milvus = [document_id] * len(chunks)
            milvus_data = [
                chunk_ids,
                document_ids_for_milvus,
                embeddings
            ]

            insert_result = collection.insert(milvus_data)
            collection.flush()
            logger.info(f"Successfully inserted {insert_result.insert_count} vectors into Milvus (Collection: {collection_name}).")

            return True

        except Exception:
            logger.exception(f"Critical error during database ingestion for '{filePath}'")
            return False
