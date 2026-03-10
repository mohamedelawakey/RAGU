from dotenv import load_dotenv
import os

load_dotenv()

# postgres config
DB_NAME = os.getenv("DB_NAME", "edu_rag")
DB_USER = os.getenv("DB_USER", "edu_rag")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))

# redis config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_RETRIES = int(os.getenv("REDIS_RETRIES", 3))
REDIS_RETRY_DELAY = float(os.getenv("REDIS_RETRY_DELAY", 1.0))

# milvus config
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_ALIAS = os.getenv("MILVUS_ALIAS", "default")
MILVUS_TIMEOUT = float(os.getenv("MILVUS_TIMEOUT", 5.0)) 

class Config:
    # postgres config
    DB_NAME = DB_NAME
    DB_USER = DB_USER
    DB_PASSWORD = DB_PASSWORD
    DB_HOST = DB_HOST
    DB_PORT = DB_PORT

    # redis config
    REDIS_HOST = REDIS_HOST
    REDIS_PORT = REDIS_PORT
    REDIS_PASSWORD = REDIS_PASSWORD
    REDIS_DB = REDIS_DB
    REDIS_RETRIES = REDIS_RETRIES
    REDIS_RETRY_DELAY = REDIS_RETRY_DELAY

    # connection pool config
    MIN_CONNECTIONS = 1
    MAX_CONNECTIONS = 20

    # milvus config
    MILVUS_HOST = MILVUS_HOST
    MILVUS_PORT = MILVUS_PORT
    MILVUS_ALIAS = MILVUS_ALIAS
    MILVUS_TIMEOUT = MILVUS_TIMEOUT
