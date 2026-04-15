from sentence_transformers import CrossEncoder
from utils.logger import get_logger
from pipeline.config import Config
import torch

logger = get_logger("reranker.loader")


class LocalRerankerLoader:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            model_path = Config.LOCAL_RERANKER_MODEL
            device = "cuda" if torch.cuda.is_available() else "cpu"

            logger.info(f"Loading local reranker model: {model_path} on {device}...")
            try:
                cls._model = CrossEncoder(model_path, device=device)
                logger.info("Local reranker model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load local reranker model: {e}")
                raise
        return cls._model
