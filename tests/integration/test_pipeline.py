import pytest
import os
import asyncio
from pipeline.ingestion.ingestor import DocumentIngestor
from pipeline.retrieval.retriever import Retriever
from pipeline.orchestrator.orchestrator import RAGPipeline
from backend.db.connections.postgres import PostgresDBConnection
from pymilvus import utility
import uuid

# These tests require a running Postgres and Milvus instance.
# They also require the API keys (Cohere) to be correctly set in the environment.


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
class TestEndToEndPipeline:
    async def test_full_ingestion_and_retrieval(self):
        # 1. Setup a dummy document
        test_file_path = "tests/integration/dummy_doc.txt"
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        # Ensure dir exists
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

        # Write some recognizable content
        unique_fact = f"The secret password for {test_user_id} is XYZ123987."
        with open(test_file_path, "w") as f:
            f.write(f"This is a dummy test document.\n{unique_fact}\nIt contains very specific testing information.")

        try:
            # 2. Ingest the document
            # Note: This will actually extract, clean, chunk, embed, and store in DBs
            # If Milvus collection doesn't exist, this will fail. Run setup.py first.
            from pipeline.config import Config
            
            # Since Ingestor no longer registers the file, register it manually for testing.
            filename = os.path.basename(test_file_path)
            async with PostgresDBConnection.get_db_connection() as conn:
                document_id = await conn.fetchval(
                    Config.INSERT_DOCUMENT_NODE, filename, test_file_path, test_user_id
                )
                
            success = await DocumentIngestor.ingest_document(test_file_path, test_user_id, document_id)
            assert success is True

            # 3. Test Retrieval
            retriever = Retriever(top_k=2)
            results = await retriever.retrieve("What is the secret password?", test_user_id)

            assert results is not None
            assert len(results) > 0

            # The result should contain our unique fact
            found_fact = any("XYZ123987" in res["text_content"] for res in results)
            assert found_fact is True

            # 4. Test Full RAG Orchestrator
            pipeline = RAGPipeline()
            response_generator = await pipeline.query("What is the secret password?", test_user_id)

            assert response_generator is not None

            final_answer = ""
            for chunk in response_generator:
                final_answer += chunk

            assert "XYZ123987" in final_answer

        finally:
            # Cleanup dummy file
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

            # Note: Database cleanup of this specific user_id is recommended but omitted
            # here to keep tests simple. Real integration tests often run against isolated DBs.
