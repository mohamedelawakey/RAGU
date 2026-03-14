from pymilvus import CollectionSchema, FieldSchema, DataType
from pipeline.config import Config


def get_chunk_schema() -> CollectionSchema:
    chunk_id = FieldSchema(
        name="chunk_id",
        dtype=DataType.VARCHAR,
        max_length=100,
        is_primary=True,
        auto_id=False
    )

    user_id = FieldSchema(
        name="user_id",
        dtype=DataType.VARCHAR,
        max_length=255
    )

    document_id = FieldSchema(
        name="document_id",
        dtype=DataType.INT64
    )

    embedding = FieldSchema(
        name="embedding",
        dtype=DataType.FLOAT_VECTOR,
        dim=Config.EMBEDDING_DIM
    )

    schema = CollectionSchema(
        fields=[chunk_id, user_id, document_id, embedding],
        description="Educational Document Embeddings for RAG (Text stored in PG)"
    )

    return schema
