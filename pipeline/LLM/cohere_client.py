from utils.logger import get_logger
from pipeline.config import Config
from dotenv import load_dotenv
import cohere
import os
import time

logger = get_logger("cohere_llm.module")


class CohereClient:
    @staticmethod
    def cohere_chat(messages: list):
        load_dotenv()
        api_key = os.getenv("COHERE_API_KEY")

        if not api_key:
            logger.error("Cohere API KEY not found in environment variables.")
            raise ValueError("COHERE_API_KEY is not set.")

        client = cohere.ClientV2(api_key=api_key)
        
        for attempt in range(1, Config.STOP_RETRY + 1):
            events_yielded = 0
            try:
                logger.info(f"Starting Cohere stream (Attempt {attempt})...")
                response = client.chat_stream(
                    model=Config.COHERE_MODEL_NAME,
                    messages=messages
                )

                for event in response:
                    if event.type == "content-delta":
                        yield event.delta.message.content.text
                        events_yielded += 1

                logger.info("Stream completed successfully.")
                return

            except Exception as e:
                if events_yielded > 0:
                    logger.error(f"Stream broke mid-generation: {e}")
                    raise
                else:
                    logger.warning(f"Cohere stream attempt {attempt} failed: {e}")
                    if attempt == Config.STOP_RETRY:
                        logger.error("Final failure in CohereClient.cohere_chat after retries.")
                        raise
                    
                    wait_time = min(
                        Config.RETRY_MAX_WAIT,
                        (Config.MULTIPLIER ** attempt) * Config.RETRY_MIN_WAIT
                    )
                    time.sleep(wait_time)
