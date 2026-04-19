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

        try:
            prefix = ""
            if "e5" in Config.EMBEDDING_MODEL.lower():
                prefix = "passage: "

            p_chunks = [prefix + c for c in chunks] if prefix else chunks

            logger.info(f"Generating embeddings for {len(chunks)} chunks...")

            _model = LoadModel.get_model()
            if _model is None:
                logger.error("Embedding model could not be initialized.")
                return None

            if Config.USE_MULTI_PROCESS_EMBEDDING and len(chunks) > 1:
                pool = LoadModel.get_pool()
                if pool:
                    logger.info("Using multi-process pool for encoding...")
                    embeddings = _model.encode_multi_process(
                        p_chunks,
                        pool,
                        batch_size=Config.BATCH_SIZE
                    )
                    logger.info("Multi-process embeddings generated successfully.")
                    return embeddings.tolist()
                else:
                    logger.warning("Falling back to single-process encoding (pool failed).")

            embeddings = _model.encode(
                p_chunks,
                batch_size=Config.BATCH_SIZE,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            logger.info("Embeddings generated successfully.")
            return embeddings.tolist()

        except Exception as e:
            logger.exception(f"Critical error during embedding process: {e}")
            return None
