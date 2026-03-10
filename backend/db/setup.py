from backend.db.models.milvus_collections import get_chunk_schema
from backend.db.connections.milvus import AsyncMilvusDBConnection
from pymilvus import Collection, utility
import asyncio
import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


async def init_milvus_collections():
    print("Connecting to Milvus...")
    await AsyncMilvusDBConnection.get_connection()

    collection_name = "edu_chunks"

    if utility.has_collection(collection_name):
        print(f"Collection '{collection_name}' already exists.")
    else:
        print(f"Creating Collection '{collection_name}'...")
        schema = get_chunk_schema()
        collection = Collection(name=collection_name, schema=schema)

        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 8, "efConstruction": 64}
        }

        print(f"Creating index for '{collection_name}'...")
        collection.create_index(field_name="embedding", index_params=index_params)

        print(f"Loading '{collection_name}' into memory...")
        collection.load()
        print("Milvus setup completed successfully!")


if __name__ == "__main__":
    asyncio.run(init_milvus_collections())
