from sentence_transformers import SentenceTransformer
from .config import Config
from . import get_logger


logger = get_logger("model_loading.module")


class LoadModel:
    _model = None

    @classmethod
    def get_model(cls):
        try:
            if cls._model is None:
                logger.info(f"Loading embedding model: {Config.EMBEDDING_MODEL}...")
                cls._model = SentenceTransformer(Config.EMBEDDING_MODEL)
                logger.info("Model loaded successfully!")

            return cls._model

        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return None
