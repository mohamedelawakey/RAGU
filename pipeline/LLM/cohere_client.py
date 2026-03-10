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
            min=Config.MIN,
            max=Config.MAX
        ),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def cohereChat(prompt: str):
        """
        Stream text content from a Cohere chat response for the given prompt.
        
        Yields successive text chunks produced by the model's streaming chat response as they arrive.
        
        Parameters:
            prompt (str): The user message sent to the Cohere chat model.
        
        Returns:
            str: Successive pieces of text from the streaming response, yielded as they are received.
        """
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

        except Exception as e:
            logger.error(f"Critical error in CohereClient.cohereChat after retries: {str(e)}")
            return
