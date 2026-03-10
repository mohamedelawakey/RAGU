from . import get_logger
from .prompts import Prompts

logger = get_logger("prompt_builder.module")


class PromptBuilder:
    @staticmethod
    def build(user_question: str, context: str) -> str:
        logger.info("Building secure prompt for the user question...")

        if not user_question or not context:
            logger.error("User question and context must not be empty")
            raise ValueError("User question and context must not be empty")

        wrapped_user_question = f">>>START_QUESTION<<<\n{user_question}\n<<<END_QUESTION>>>"
        wrapped_context = f">>>USER_DATA<<<\n{context}\n<<<END_DATA>>>"

        return Prompts.construct_rag_prompt(wrapped_user_question, wrapped_context)
