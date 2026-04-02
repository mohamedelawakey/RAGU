from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from backend.db.models.milvus_collections import get_chunk_schema
from pipeline.parser.parser import DocumentExtractor
from pipeline.embeddings.embedding import Embedding
from pipeline.chunking.chunker import TextSplitter
from pipeline.cleaning.cleaner import Cleaner
from utils.logger import get_logger
from pipeline.config import Config
from pymilvus import Collection
import asyncio
import uuid

logger = get_logger("ingestion.module")


class DocumentIngestor:
    @staticmethod
    async def ingest_document(
        filePath: str, user_id: str, document_id: int
    ) -> tuple[bool, str]:
        logger.info(
            f"Starting ingestion pipeline for document: {filePath} "
            f"[user_id={user_id}, doc_id={document_id}]"
        )

        try:
            collection_name = (Config.COLLECTION_NAME or "").strip()
            if not collection_name:
                raise ValueError("Config.COLLECTION_NAME is missing or empty.")

            logger.info("Verifying Milvus collection availability...")
            await AsyncMilvusDBConnection.initialize_collection(
                collection_name=collection_name,
                schema=get_chunk_schema()
            )

            # 1. Extraction
            logger.info("Extracting text from document...")
            try:
                text = await asyncio.wait_for(
                    asyncio.to_thread(DocumentExtractor.extract, filePath),
                    timeout=Config.EXTRACTION_TIMEOUT
                )
            except asyncio.TimeoutError:
                return (
                    False,
                    f"Extraction timeout ({Config.EXTRACTION_TIMEOUT}s)"
                )
            except Exception as e:
                return False, f"Extraction error: {str(e)}"

            if not text:
                return False, "No text extracted from document."

            # 2. Cleaning & Chunking
            logger.info("Cleaning and chunking text...")
            try:
                text = await asyncio.to_thread(Cleaner.clean, text)
                if not text:
                    return False, "Text became empty after cleaning."

                chunks = await asyncio.to_thread(TextSplitter.text_split, text)
                if not chunks:
                    return False, "Document chunking failed."
            except Exception as e:
                return False, f"Text processing error: {str(e)}"

            # 3. Embedding (Batched to prevent memory/heartbeat issues)
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            all_embeddings = []
            batch_size = Config.BATCH_SIZE * Config.INGESTION_BATCH_MULTIPLIER

            try:
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    num_batches = (len(chunks) - 1) // batch_size + 1
                    logger.info(
                        f"Processing embedding batch {i//batch_size + 1}/"
                        f"{num_batches}..."
                    )

                    batch_embeddings = await asyncio.to_thread(
                        Embedding.embed, batch
                    )
                    if not batch_embeddings:
                        return (
                            False,
                            f"Embedding failed at batch {i//batch_size + 1}"
                        )

                    all_embeddings.extend(batch_embeddings)

                    await asyncio.sleep(Config.EMBEDDING_SLEEP_TIME)
            except Exception as e:
                return False, f"Embedding engine error: {str(e)}"

            if len(all_embeddings) != len(chunks):
                return False, "Mismatch between chunk count and embedding count."

            # 4. Storage (Postgres)
            logger.info("Saving chunks to PostgreSQL...")
            try:
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
                    await conn.executemany(Config.INSERT_CHUNKS, chunk_records)
            except Exception as e:
                return False, f"Postgres storage error: {str(e)}"

            # 5. Indexing (Milvus)
            logger.info("Inserting embeddings into Milvus...")
            try:
                collection = Collection(collection_name)

                milvus_batch_size = Config.MILVUS_BATCH_SIZE
                for i in range(0, len(chunks), milvus_batch_size):
                    end = i + milvus_batch_size
                    collection.insert([
                        chunk_ids[i:end],
                        [user_id] * len(chunks[i:end]),
                        [document_id] * len(chunks[i:end]),
                        all_embeddings[i:end]
                    ])

                # Hangs too long. Let Milvus flush in BG.
                # collection.flush()

                logger.info(
                    f"Successfully indexed document {document_id} in Milvus."
                )
            except Exception as e:
                logger.error(f"Milvus indexing failed for document {document_id}. Rolling back chunks in Postgres...")
                try:
                    async with PostgresDBConnection.get_db_connection() as conn:
                        await conn.execute(Config.DELETE_CHUNKS, document_id)
                except Exception as rollback_err:
                    logger.critical(f"Failed to rollback chunks for document {document_id}: {str(rollback_err)}")

                return False, f"Milvus indexing error: {str(e)}"

            return True, ""

        except Exception as e:
            logger.exception(
                f"Unexpected ingestion failure for document {document_id}"
            )
            return False, f"Unexpected error: {str(e)}"
