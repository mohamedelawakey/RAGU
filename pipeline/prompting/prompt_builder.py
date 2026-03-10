from . import get_logger
from .prompts import Prompts

logger = get_logger("prompt_builder.module")


class PromptBuilder:
    @staticmethod
    def build(user_question: str, context: str) -> str:
        """
        Builds a structured retrieval-augmented generation (RAG) prompt from a user question and context.
        
        Wraps the user question and context with explicit delimiters and combines them into a single prompt suitable for RAG prompt construction.
        
        Parameters:
            user_question (str): The user's question text to include in the prompt.
            context (str): Contextual data or user information to include alongside the question.
        
        Returns:
            str: The combined prompt string ready for RAG consumption.
        
        Raises:
            ValueError: If `user_question` or `context` is empty.
        """
        logger.info("Building secure prompt for the user question...")

        if not user_question or not context:
            logger.error("User question and context must not be empty")
            raise ValueError("User question and context must not be empty")

        wrapped_user_question = f">>>START_QUESTION<<<\n{user_question}\n<<<END_QUESTION>>>"
        wrapped_context = f">>>USER_DATA<<<\n{context}\n<<<END_DATA>>>"

        return Prompts.construct_rag_prompt(wrapped_user_question, wrapped_context)
