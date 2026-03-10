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
