import pytest
from pipeline.prompting.prompt_builder import PromptBuilder


class TestPromptBuilder:
    def test_successful_build(self):
        question = "What is gravity?"
        context = "Gravity is a fundamental interaction."

        messages = PromptBuilder.build(question, context)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        system_content = messages[0]["content"]
        user_content = messages[1]["content"]

        assert "What is gravity?" in user_content
        assert "Gravity is a fundamental interaction." in user_content

        import re
        match = re.search(r'\[(BOUNDARY_[a-f0-9]{32}_BOUNDARY)\]', user_content)
        assert match is not None
        boundary = match.group(1)

        assert f"[{boundary}]" in system_content

    def test_empty_question(self):
        with pytest.raises(ValueError, match="User question and context must not be empty"):
            PromptBuilder.build("", "context")

    def test_whitespace_question(self):
        with pytest.raises(ValueError, match="User question and context must not be empty"):
            PromptBuilder.build("   ", "context")

    def test_empty_context(self):
        with pytest.raises(ValueError, match="User question and context must not be empty"):
            PromptBuilder.build("question", "")

    def test_whitespace_context(self):
        with pytest.raises(ValueError, match="User question and context must not be empty"):
            PromptBuilder.build("question", "   ")

    def test_none_values(self):
        with pytest.raises(ValueError, match="User question and context must not be empty"):
            PromptBuilder.build(None, "context")

        with pytest.raises(ValueError, match="User question and context must not be empty"):
            PromptBuilder.build("question", None)
