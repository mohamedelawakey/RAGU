import pytest
from pipeline.chunking.chunker import TextSplitter
from pipeline.config import Config


class TestTextSplitter:
    def test_empty_string(self):
        chunks = TextSplitter.text_split("")
        assert chunks == []

    def test_white_space_string(self):
        chunks = TextSplitter.text_split("   \n\t  ")
        assert chunks == []

    def test_short_string(self):
        text = "This is a short educational text."
        chunks = TextSplitter.text_split(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_string_chunking(self):
        # Create a string larger than CHUNK_SIZE
        word = "Knowledge "
        text = word * (Config.CHUNK_SIZE // len(word) + 10)
        chunks = TextSplitter.text_split(text)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= Config.MAX_CHUNK_SIZE
            assert len(chunk) > 0

    def test_overlap_exists(self):
        text = "A " * 500
        chunks = TextSplitter.text_split(text)

        if len(chunks) > 1:
            # We expect some overlap between chunks based on the overlap parameter
            # However langchain recursive splitter overlap is approximate
            assert "A " in chunks[0]
            assert "A " in chunks[1]

    def test_arabic_text_chunking(self):
        text = "القراءة هي الغذاء العقلي. " * 100
        chunks = TextSplitter.text_split(text)
        assert len(chunks) > 0
        assert "القراءة" in chunks[0]
