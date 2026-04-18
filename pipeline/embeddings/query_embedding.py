from .load_models import LoadModel
from typing import List, Optional
from utils.logger import get_logger
from pipeline.config import Config

logger = get_logger("query_embedding.module")


class QueryEmbedding:
    @staticmethod
    def embed_query(query: str) -> Optional[List[float]]:
        if not query or not query.strip():
            logger.warning("No query provided for embedding.")
            return None

        _model = LoadModel.get_model()
        if _model is None:
            logger.error("Embedding model could not be initialized.")
            return None

        try:
            prefix = ""
            if "e5" in Config.EMBEDDING_MODEL.lower():
                prefix = "query: "

            prefixed_query = prefix + query if prefix else query

            logger.info(f"Generating embedding for query [length={len(query)}]")

            embedding = _model.encode(
                prefixed_query,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            logger.info("Query embedding generated successfully.")
            return embedding.tolist()

        except Exception as e:
            logger.exception(f"Critical error during query embedding process: {e}")
            return None
