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

    _pool = None
    _pool_lock = threading.Lock()

    @classmethod
    def get_pool(cls):
        if cls._pool is not None:
            return cls._pool

        with cls._pool_lock:
            if cls._pool is None:
                model = cls.get_model()
                if model:
                    try:
                        logger.info(f"Starting multi-process pool with {Config.EMBEDDING_NUM_PROCESSES} processes...")
                        devices = ["cpu"] * Config.EMBEDDING_NUM_PROCESSES
                        if torch.cuda.is_available():
                            devices = [f"cuda:{i}" for i in range(torch.cuda.device_count())]

                        cls._pool = model.start_multi_process_pool(target_devices=devices)
                    except Exception as e:
                        logger.error(f"Failed to start multi-process pool: {e}")
                        return None
        return cls._pool

    @classmethod
    def stop_pool(cls):
        with cls._pool_lock:
            if cls._pool is not None:
                model = cls.get_model()
                if model:
                    logger.info("Stopping multi-process pool...")
                    model.stop_multi_process_pool(cls._pool)
                    cls._pool = None
