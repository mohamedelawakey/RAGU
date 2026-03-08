import os
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from . import get_logger

logger = get_logger("universal_extractor.module")


class DocumentExtractor:
    _converter = None
    DOCLING_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.html'}

    @classmethod
    def get_converter(cls):
        if cls._converter is None:
            logger.info("Initializing Universal Docling (OCR + Tables)...")

            options = PdfPipelineOptions()
            options.do_ocr = True
            options.do_table_structure = True

            cls._converter = DocumentConverter(
                pipeline_options=options
            )
        return cls._converter

    @staticmethod
    def extract(filePath: str):
        try:
            if not os.path.exists(filePath):
                logger.error(f"File not found: {filePath}")
                return None

            _, ext = os.path.splitext(filePath)
            ext = ext.lower()

            if ext == '.txt':
                with open(filePath, 'r', encoding='utf-8') as f:
                    return f.read().strip()

            if ext in DocumentExtractor.DOCLING_EXTENSIONS:
                converter = DocumentExtractor.get_converter()
                result = converter.convert(filePath)

                if result and result.document:
                    return result.document.export_to_markdown().strip()

                logger.warning(f"Docling failed to parse content for: {filePath}")
                return ""

            logger.warning(f"Unsupported extension: {ext}")
            return None

        except Exception as e:
            logger.error(f"Critical error extracting {filePath}: {str(e)}")
            return None
