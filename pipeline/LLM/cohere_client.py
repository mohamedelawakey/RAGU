from dotenv import load_dotenv
from ..config import Config
from .. import get_logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import cohere
import os

logger = get_logger("cohere_llm.module")
load_dotenv()


class CohereClient:
    @staticmethod
    @retry(
        stop=stop_after_attempt(Config.STOP_RETRY),
        wait=wait_exponential(
            multiplier=Config.MULTIPLIER,
            min=Config.RETRY_MIN_WAIT,
            max=Config.RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def cohere_chat(prompt: str):
        try:
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                logger.error("Cohere API KEY not found in environment variables.")
                return

            client = cohere.ClientV2(api_key=api_key)

            logger.info("Starting streaming request to Cohere (with retry policy)...")

            response = client.chat_stream(
                model=Config.COHERE_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            for event in response:
                if event.type == "content-delta":
                    yield event.delta.message.content.text

            logger.info("Stream completed successfully.")

        except Exception:
            logger.exception("Critical error in CohereClient.cohere_chat")
            raise
