class Config:
    # embeddings
    EMBEDDING_MODEL = 'BAAI/bge-m3'  # 1024 dim
    BATCH_SIZE = 32

    # cleaning
    STRIP_KASHIDA = True
    KEEP_TASHKEEL = True
    
    # chunking
    CHUNK_SIZE = 1000
    MAX_CHUNK_SIZE = 8000
    CHUNK_OVERLAP = 200
    SEPARATORS = ["\n\n", "\n", ". ", "؟ ", "! ", "، ", "؛ ", " "]
