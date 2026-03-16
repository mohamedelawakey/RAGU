from utils.logger import get_logger
from pipeline.config import Config
from dotenv import load_dotenv
from tenacity import (
    Retrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import cohere
import os

logger = get_logger("cohere_llm.module")


class CohereClient:
    @staticmethod
    def cohere_chat(messages: list):
        load_dotenv()
        api_key = os.getenv("COHERE_API_KEY")

        if not api_key:
            logger.error("Cohere API KEY not found in environment variables.")
            raise ValueError("COHERE_API_KEY is not set.")

        retryer = Retrying(
            stop=stop_after_attempt(Config.STOP_RETRY),
            wait=wait_exponential(
                multiplier=Config.MULTIPLIER,
                min=Config.RETRY_MIN_WAIT,
                max=Config.RETRY_MAX_WAIT
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True
        )

        def _run_stream():
            for attempt in retryer:
                with attempt:
                    logger.info(f"Starting Cohere stream (Attempt {attempt.retry_state.attempt_number})...")
                    client = cohere.ClientV2(api_key=api_key)

                    response = client.chat_stream(
                        model=Config.COHERE_MODEL_NAME,
                        messages=messages
                    )

                    for event in response:
                        if event.type == "content-delta":
                            yield event.delta.message.content.text

                    logger.info("Stream completed successfully.")

        try:
            return _run_stream()
        except Exception:
            logger.exception("Final failure in CohereClient.cohere_chat after retries.")
            raise
