from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from pipeline import get_logger
from typing import Optional
import threading
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
                    logger.info("Initializing Universal Docling (OCR + Tables)...")

                    options = PdfPipelineOptions()
                    options.do_ocr = True
                    options.do_table_structure = True

                    cls._converter = DocumentConverter(
                        format_options={
                            InputFormat.PDF: PdfFormatOption(pipeline_options=options)
                        }
                    )
        return cls._converter

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

            if ext in DocumentExtractor.DOCLING_EXTENSIONS:
                converter = DocumentExtractor.get_converter()
                result = converter.convert(file_path)

                if result and result.document:
                    return result.document.export_to_markdown().strip()

                logger.warning(f"Docling failed to parse content for: {file_path}")
                return ""

            logger.warning(f"Unsupported extension: {ext}")
            return None

        except Exception:
            logger.exception(f"Critical error extracting {file_path}")
            return None
