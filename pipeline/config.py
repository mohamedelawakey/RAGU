import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # extraction
    EXTRACTION_TIMEOUT = float(os.getenv('EXTRACTION_TIMEOUT', 300.0))

    # embeddings
    EMBEDDING_MODEL = 'BAAI/bge-m3'
    EMBEDDING_DIM = 1024
    BATCH_SIZE = 32

    # cleaning
    STRIP_KASHIDA = True
    KEEP_TASHKEEL = True

    # chunking
    CHUNK_SIZE = 1000
    MAX_CHUNK_SIZE = 8000
    CHUNK_OVERLAP = 200
    SEPARATORS = ("\n\n", "\n", ". ", "؟ ", "! ", "، ", "؛ ", " ")

    # cohere client
    COHERE_MODEL_NAME = "command-a-03-2025"

    # retry configurations
    STOP_RETRY = 3
    MULTIPLIER = 1
    RETRY_MIN_WAIT = 2
    RETRY_MAX_WAIT = 10

    # Insert Document Node into Postgres (Initial state: processing)
    INSERT_DOCUMENT_NODE = """
        INSERT INTO documents (filename, file_path, status, user_id)
        VALUES ($1, $2, 'processing', $3)
        RETURNING id
    """

    # Update Document Node status and optional error message
    UPDATE_DOCUMENT_STATUS = """
        UPDATE documents
        SET status = $1, error_message = $2
        WHERE id = $3
    """

    # insert chunks into Postgres
    INSERT_CHUNKS = """
        INSERT INTO document_chunks (
            id, document_id, page_number, text_content
        )
        VALUES ($1, $2, $3, $4)
    """

    # delete chunks from Postgres
    DELETE_CHUNKS = """
        DELETE FROM document_chunks WHERE document_id = $1
    """

    # BM25 Search Configurations (Advanced Multilingual & Fuzzy Search)
    BM25_TOP_K = 20
    BM25_QUERY = """
        WITH search_query AS (
            SELECT websearch_to_tsquery('simple', $1) AS q
        )
        SELECT
            c.id as chunk_id,
            (
                ts_rank_cd(to_tsvector('simple', c.text_content), sq.q) * 0.7 +
                similarity(c.text_content, $1) * 0.3
            ) as rank_score
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        CROSS JOIN search_query sq
        WHERE
            d.user_id = $3
            AND (
                to_tsvector('simple', c.text_content) @@ sq.q
                OR c.text_content % $1
            )
        ORDER BY rank_score DESC
        LIMIT $2
    """

    # Semantic Search Configurations
    SEMANTIC_SEARCH_TOP_K = 20
    COLLECTION_NAME = "edu_chunks"
    SEARCH_PARAMS_METRIC_TYPE = "COSINE"
    MILVUS_INDEX_TYPE = os.getenv("MILVUS_INDEX_TYPE", "HNSW")
    SEARCH_PARAMS_EF = int(os.getenv("MILVUS_HNSW_EF", "64"))
    MILVUS_ALIAS = "default"

    # Hybrid Search Configurations
    HYBRID_SEARCH_TOP_K = 20
    RRF_K = 60

    # Retriever Configurations
    FETCH_CHUNKS_BY_IDS = """
        SELECT id, text_content
        FROM document_chunks
        WHERE id = ANY($1::text[])
    """

    # Reranker Configurations
    RERANKER_MODEL = "rerank-v3.5"
    RERANKER_TOP_N = 20

    # Ingestion Configurations
    INGESTION_BATCH_MULTIPLIER = 2
    EMBEDDING_SLEEP_TIME = 0.1
    MILVUS_BATCH_SIZE = 500

    # Chat Retriever Configurations
    CHAT_RETRIEVER_TOP_K = 5
    CHAT_RETRIEVER_METRIC_TYPE = "COSINE"
    CHAT_RETRIEVER_EF = 64
    FETCH_CHAT_MESSAGES_QUERY = """
        SELECT id, role, content, session_id 
        FROM chat_messages WHERE id = ANY($1)
    """
