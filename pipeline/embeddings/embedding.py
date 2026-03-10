from typing import List, Optional
from .load_models import LoadModel
from ..config import Config
from .. import get_logger

logger = get_logger("embedding.module")


class Embedding:
    @staticmethod
    def embed(chunks: List[str]) -> Optional[List[List[float]]]:
        """
        Generate vector embeddings for the given text chunks.
        
        Parameters:
            chunks (List[str]): Sequence of text segments to convert into embedding vectors.
        
        Returns:
            Optional[List[List[float]]]: A list of embedding vectors (one list of floats per chunk).
            Returns an empty list if `chunks` is empty. Returns `None` if the embedding model could not
            be initialized or if a critical error occurs during embedding.
        """
        if not chunks:
            logger.warning("No chunks provided for embedding.")
            return []

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
            logger.error(f"Critical error during embedding process: {e}")
            return None
