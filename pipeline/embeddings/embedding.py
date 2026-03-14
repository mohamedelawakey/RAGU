from .load_models import LoadModel
from typing import List, Optional
from utils.logger import get_logger
from pipeline.config import Config

logger = get_logger("embedding.module")


class Embedding:
    @staticmethod
    def embed(chunks: List[str]) -> Optional[List[List[float]]]:
        if not chunks:
            logger.warning("No chunks provided for embedding.")
            return None

        _model = LoadModel.get_model()
        if _model is None:
            logger.error("Embedding model could not be initialized.")
            return None

        try:
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")

            embeddings = _model.encode(
                chunks,
                batch_size=Config.BATCH_SIZE,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            logger.info("Embeddings generated successfully.")
            return embeddings.tolist()

        except Exception as e:
            logger.exception(f"Critical error during embedding process: {e}")
            return None
