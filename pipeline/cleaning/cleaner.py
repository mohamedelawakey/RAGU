from . import get_logger, Config
import re
import unicodedata
from typing import Optional

logger = get_logger("cleaner.module")


class Cleaner:
    @staticmethod
    def clean(text: Optional[str]) -> str:
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
