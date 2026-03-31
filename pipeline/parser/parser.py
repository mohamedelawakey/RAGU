from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from utils.logger import get_logger
from typing import Optional
import threading
import fitz
import os

logger = get_logger("universal_extractor.module")


class DocumentExtractor:
    _converter = None
    _lock = threading.Lock()
    DOCLING_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.html'}

    @classmethod
    def get_converter(cls):
        if cls._converter is None:
            with cls._lock:
                if cls._converter is None:
                    logger.info(
                        "Initializing Docling Fallback (OCR Disabled)..."
                    )

                    options = PdfPipelineOptions()
                    options.do_ocr = False
                    options.do_table_structure = False

                    cls._converter = DocumentConverter(
                        format_options={
                            InputFormat.PDF: PdfFormatOption(
                                pipeline_options=options
                            )
                        }
                    )
        return cls._converter

    @staticmethod
    def _extract_with_fitz(file_path: str) -> Optional[str]:
        try:
            logger.info(f"Attempting Fast Extraction (PyMuPDF) for {file_path}")
            text_parts = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())

            full_text = "\n".join(text_parts).strip()

            if len(full_text) > 100:
                logger.info(f"Fast Extraction successful ({len(full_text)} chars)")
                return full_text
            return None
        except Exception as e:
            logger.warning(f"PyMuPDF failed/skipped for {file_path}: {e}")
            return None

    @staticmethod
    def extract(file_path: str) -> Optional[str]:
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()

            if ext == '.pdf':
                fast_text = DocumentExtractor._extract_with_fitz(file_path)
                if fast_text:
                    return fast_text

                logger.info(
                    f"Falling back to Deep Extraction (Docling) for {file_path}"
                )

            if ext in DocumentExtractor.DOCLING_EXTENSIONS:
                converter = DocumentExtractor.get_converter()
                result = converter.convert(file_path)

                if result and result.document:
                    return result.document.export_to_markdown().strip()

                logger.warning(
                    f"Docling failed to parse content for: {file_path}"
                )
                return ""

            logger.warning(f"Unsupported extension: {ext}")
            return None

        except Exception:
            logger.exception(f"Critical error extracting {file_path}")
            return None
