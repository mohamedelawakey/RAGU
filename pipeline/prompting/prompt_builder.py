from utils.logger import get_logger
from .prompts import Prompts
import uuid

logger = get_logger("prompt_builder.module")


class PromptBuilder:
    @staticmethod
    def build(user_question: str, context: str) -> list[dict]:
        logger.info("Building secure prompt for the user question...")

        if not user_question or not user_question.strip():
            logger.error("User question must not be empty")
            raise ValueError("User question must not be empty")

        boundary_token = f"BOUNDARY_{uuid.uuid4().hex}_BOUNDARY"
        has_context = bool(context and context.strip())

        system_message = Prompts.get_system_prompt(
            boundary_token,
            has_context=has_context
        )

        user_message = Prompts.get_user_prompt(
            user_question,
            context,
            boundary_token
        )

        messages = [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        logger.info("Secure messages assembled with dynamic boundaries.")
        return messages
