from sentence_transformers import SentenceTransformer
from utils.logger import get_logger
from pipeline.config import Config
import threading
import torch

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
                    has_cuda = torch.cuda.is_available()
                    device = "cuda" if has_cuda else "cpu"

                    logger.info(
                        f"Loading {Config.EMBEDDING_MODEL} on {device}..."
                    )

                    cls._model = SentenceTransformer(
                        Config.EMBEDDING_MODEL, device=device
                    )

                    logger.info("Model loaded successfully!")

                except Exception as e:
                    logger.exception(f"Failed to load model: {e}")
                    return None

        return cls._model
