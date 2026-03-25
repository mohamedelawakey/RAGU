class Config:
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

    # Update Document Node status to completed
    UPDATE_DOCUMENT_STATUS = """
        UPDATE documents
        SET status = $1
        WHERE id = $2
    """

    # insert chunks into Postgres
    INSERT_CHUNKS = """
        INSERT INTO document_chunks (id, document_id, page_number, text_content)
        VALUES ($1, $2, $3, $4)
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
    SEARCH_PARAMS_NPROBE = 10
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
