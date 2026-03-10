from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from . import get_logger
import os

logger = get_logger("universal_extractor.module")


class DocumentExtractor:
    _converter = None
    DOCLING_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.html'}

    @classmethod
    def get_converter(cls):
        """
        Return a cached DocumentConverter configured for PDF OCR and table extraction.
        
        Initializes a singleton DocumentConverter on first call with PDF format options that enable OCR and table-structure extraction, then returns the cached instance.
        
        Returns:
            DocumentConverter: A DocumentConverter instance configured for PDFs (OCR and table structure enabled).
        """
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
    def extract(filePath: str):
        """
        Extracts textual content from the file at the given path.
        
        For plain `.txt` files returns the file text with surrounding whitespace removed. For supported document types (DocumentExtractor.DOCLING_EXTENSIONS) returns the document exported to Markdown with surrounding whitespace removed. If a supported document is parsed but contains no extractable document, returns an empty string. Returns `None` when the file does not exist, the extension is unsupported, or an unexpected error occurs.
        
        Parameters:
        	filePath (str): Path to the file to extract.
        
        Returns:
        	str: Extracted text or Markdown content, or an empty string if parsing produced no document; `None` for missing/unsupported files or on error.
        """
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
