from utils.logger import get_logger
from .prompts import Prompts

logger = get_logger("prompt_builder.module")


class PromptBuilder:
    @staticmethod
    def build(user_question: str, context: str, history: list = None) -> list[dict]:
        logger.info("Building secure prompt for the user question...")

        if not user_question or not user_question.strip():
            logger.error("User question must not be empty")
            raise ValueError("User question must not be empty")

        boundary_token = "|#|CONTEXT_START|#|"
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
            }
        ]

        if history:
            for msg in history:
                messages.append({
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"]
                })

        messages.append({
            "role": "user",
            "content": user_message
        })

        logger.info("Secure messages assembled with dynamic boundaries.")
        return messages
