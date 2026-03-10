from sentence_transformers import SentenceTransformer
from ..config import Config
from .. import get_logger

import threading
logger = get_logger("model_loading.module")


class LoadModel:
    _model = None
    _lock = threading.Lock()

    @classmethod
    def get_model(cls):
        if cls._model is not None:
            return cls._model

        with cls._lock:
            if cls._model is None:
                try:
                    logger.info(f"Loading embedding model: {Config.EMBEDDING_MODEL}...")
                    cls._model = SentenceTransformer(Config.EMBEDDING_MODEL)
                    logger.info("Model loaded successfully!")
                except Exception as e:
                    logger.exception(f"Failed to load model: {e}")
                    return None
        return cls._model
