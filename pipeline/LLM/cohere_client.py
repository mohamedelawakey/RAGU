from pipeline.prompting.prompts import Prompts
from utils.logger import get_logger
from pipeline.config import Config
from dotenv import load_dotenv
import cohere
import time
import os

logger = get_logger("cohere_llm.module")


class CohereClient:
    @staticmethod
    def reformulate_query(query: str, history: list) -> str:
        if not history or len(history) == 0:
            return query

        load_dotenv()
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            return query

        client = cohere.ClientV2(api_key=api_key)

        sys_prompt = Prompts.get_reformulation_system_prompt()
        history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
        user_prompt = Prompts.get_reformulation_user_prompt(query, history_text)

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            logger.info("CohereClient: Reformulating query based on history...")
            response = client.chat(
                model=Config.COHERE_MODEL_NAME,
                messages=messages,
                temperature=0.1
            )

            rewritten = response.message.content[0].text.strip()
            rewritten = rewritten.replace('"', '').replace("'", "")

            logger.info(f"CohereClient: Query reformulated -> {rewritten}")
            return rewritten
        except Exception as e:
            logger.error(f"CohereClient failed to reformulate query: {e}")
            return query

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
