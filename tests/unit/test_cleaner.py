import pytest
from pipeline.cleaning.cleaner import Cleaner
from pipeline.config import Config
import unicodedata


class TestCleaner:
    def test_empty_string(self):
        result = Cleaner.clean("")
        assert result == ""

    def test_whitespace_removal(self):
        text = "   This   has  too   much   whitespace.   \n\n\n\n\n "
        result = Cleaner.clean(text)
        assert result == "This has too much whitespace."

    def test_unicode_normalization(self):
        # Fullwidth Latin Small Letter A (U+FF41) should normalize to 'a'
        text = "Hello ａ"
        result = Cleaner.clean(text)
        assert result == "Hello a"

    def test_special_characters_handling(self):
        text = "Hello!! This is a test??? Yes..."
        result = Cleaner.clean(text)
        # Should keep meaningful punctuation but remove extras if the cleaner does that
        # By default cleaner keeps standard punctuation
        assert "Hello" in result
        assert "Yes" in result

    @pytest.mark.skipif(not Config.KEEP_TASHKEEL, reason="Tashkeel keeping is disabled")
    def test_tashkeel_preservation(self):
        text = "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ"
        result = Cleaner.clean(text)
        expected = unicodedata.normalize('NFKC', text)
        assert result == expected

    @pytest.mark.skipif(not Config.STRIP_KASHIDA, reason="Kashida stripping is disabled")
    def test_arabic_kashida_removal(self):
        # 'م' + kashida + 'ر' + 'ح' + 'ب' + 'ا'
        text = "مـرحـبـا بك"
        result = Cleaner.clean(text)
        assert result == "مرحبا بك"
