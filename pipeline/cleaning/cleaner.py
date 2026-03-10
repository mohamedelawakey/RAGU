from . import get_logger, Config
import re
import unicodedata

logger = get_logger("cleaner.module")


class Cleaner:
    @staticmethod
    def clean(text: str) -> str:
        """
        Clean and normalize a text string for downstream processing.
        
        Performs Unicode NFKC normalization, conditionally removes the Kashida character (U+0640) and Arabic diacritics (U+064B–U+0652) according to Config flags, collapses three or more consecutive newlines to two, replaces runs of spaces or tabs with a single space, and trims leading/trailing whitespace. If `text` is falsy (e.g., None or empty), returns an empty string.
        
        Parameters:
            text (str): Input text to clean.
        
        Returns:
            str: The cleaned and normalized text, or an empty string if the input was falsy.
        """
        if not text:
            return ""

        text = unicodedata.normalize('NFKC', text)

        if Config.STRIP_KASHIDA:
            text = re.sub(r'\u0640', '', text)

        if not Config.KEEP_TASHKEEL:
            text = re.sub(r'[\u064b-\u0652]', '', text)

        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)

        return text.strip()
