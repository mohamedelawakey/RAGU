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
REDIS_BLACKLIST_PREFIX = os.getenv("REDIS_BLACKLIST_PREFIX", "blacklist:")

# milvus config
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))
MILVUS_ALIAS = os.getenv("MILVUS_ALIAS", "default")
MILVUS_TIMEOUT = float(os.getenv("MILVUS_TIMEOUT", 5.0))
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", 1024))

# connection pool config
MIN_CONNECTIONS = int(os.getenv("MIN_CONNECTIONS", 1))
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", 20))

# rabbitmq config
RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost/"
)
RABBITMQ_QUEUE_NAME = os.getenv(
    "RABBITMQ_QUEUE_NAME",
    "document_ingestion_queue"
)

# documents config
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/edu_rag_uploads")
MAX_FILES_PER_USER = int(os.getenv("MAX_FILES_PER_USER", 2))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# postgres queries
UPDATE_DOCUMENT_STATUS = """
    UPDATE documents
    SET status = $1
    WHERE id = $2
"""
CHECK_USER_EXISTS_QUERY = """
    SELECT id FROM users WHERE email = $1 OR username = $2
"""
INSERT_USER_QUERY = """
    INSERT INTO users (id, username, email, hashed_password) VALUES ($1, $2, $3, $4)
"""
GET_USER_AUTH_QUERY = """
    SELECT id, hashed_password FROM users WHERE email = $1 OR username = $1
"""
CHECK_USER_DOCUMENT_QUOTA_QUERY = """
    SELECT COUNT(*) FROM documents WHERE user_id = $1
"""
INSERT_DOCUMENT_QUERY = """
    INSERT INTO documents (user_id, filename, file_path, status)
    VALUES ($1, $2, $3, 'pending')
    RETURNING id
"""

# auth config
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    raise ValueError("FATAL: SECRET_KEY environment variable is not set. Refusing insecure initialization.")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
)
REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30)
)

# security config (middleware)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", 31536000))

extra_masked_keys = os.getenv("EXTRA_SENSITIVE_KEYS", "").split(",")
SENSITIVE_KEYS = {"password", "token", "email", "access_token", "refresh_token"}
SENSITIVE_KEYS.update([k.strip().lower() for k in extra_masked_keys if k.strip()])

# compression config (middleware)
GZIP_MIN_SIZE = int(os.getenv("GZIP_MIN_SIZE", 1000))


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
    REDIS_BLACKLIST_PREFIX = REDIS_BLACKLIST_PREFIX

    # connection pool config
    MIN_CONNECTIONS = MIN_CONNECTIONS
    MAX_CONNECTIONS = MAX_CONNECTIONS

    # milvus config
    MILVUS_HOST = MILVUS_HOST
    MILVUS_PORT = MILVUS_PORT
    MILVUS_ALIAS = MILVUS_ALIAS
    MILVUS_TIMEOUT = MILVUS_TIMEOUT
    EMBEDDING_DIM = EMBEDDING_DIM

    # rabbitmq config
    RABBITMQ_URL = RABBITMQ_URL
    RABBITMQ_QUEUE_NAME = RABBITMQ_QUEUE_NAME

    # postgres queries
    UPDATE_DOCUMENT_STATUS = UPDATE_DOCUMENT_STATUS
    CHECK_USER_EXISTS_QUERY = CHECK_USER_EXISTS_QUERY
    INSERT_USER_QUERY = INSERT_USER_QUERY
    GET_USER_AUTH_QUERY = GET_USER_AUTH_QUERY
    CHECK_USER_DOCUMENT_QUOTA_QUERY = CHECK_USER_DOCUMENT_QUOTA_QUERY
    INSERT_DOCUMENT_QUERY = INSERT_DOCUMENT_QUERY

    # documents config
    UPLOAD_DIR = UPLOAD_DIR
    MAX_FILES_PER_USER = MAX_FILES_PER_USER
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_BYTES

    # auth config
    SECRET_KEY = SECRET_KEY
    ALGORITHM = ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS = REFRESH_TOKEN_EXPIRE_DAYS

    # security config (middleware)
    ALLOWED_ORIGINS = ALLOWED_ORIGINS
    HSTS_MAX_AGE = HSTS_MAX_AGE

    # compression config (middleware)
    GZIP_MIN_SIZE = GZIP_MIN_SIZE
