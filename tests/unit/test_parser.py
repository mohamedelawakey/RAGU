import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
from pipeline.parser.parser import DocumentExtractor


class TestParser:
    @patch('os.path.exists')
    def test_extract_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        result = DocumentExtractor.extract("non_existent.pdf")
        assert result is None

    @patch('os.path.exists')
    def test_extract_unsupported_extension(self, mock_exists):
        mock_exists.return_value = True
        result = DocumentExtractor.extract("image.png")
        assert result is None

    @patch('os.path.exists')
    def test_extract_txt_file(self, mock_exists):
        mock_exists.return_value = True
        fake_content = "This is a dummy text file."

        with patch('builtins.open', mock_open(read_data=fake_content)):
            result = DocumentExtractor.extract("document.txt")
            assert result == fake_content

    @patch('os.path.exists')
    @patch('pipeline.parser.parser.DocumentExtractor.get_converter')
    def test_extract_supported_docling_file(self, mock_get_converter, mock_exists):
        mock_exists.return_value = True

        mock_converter = MagicMock()
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Markdown Content"
        mock_converter.convert.return_value = mock_result
        mock_get_converter.return_value = mock_converter

        # Test PDF
        result = DocumentExtractor.extract("document.pdf")
        assert result == "Markdown Content"
        mock_converter.convert.assert_called_with("document.pdf")

    @patch('os.path.exists')
    @patch('pipeline.parser.parser.DocumentExtractor.get_converter')
    def test_docling_failure_fallback(self, mock_get_converter, mock_exists):
        mock_exists.return_value = True

        mock_converter = MagicMock()
        mock_converter.convert.return_value = None # Simulating a failure returning None
        mock_get_converter.return_value = mock_converter

        result = DocumentExtractor.extract("corrupted.pdf")
        assert result == "" # Configured to return empty string on parse failure

    @patch('os.path.exists')
    def test_extract_exception_handling(self, mock_exists):
        mock_exists.return_value = True

        # Open throwing an exception
        with patch('builtins.open', side_effect=PermissionError("Access Denied")):
            result = DocumentExtractor.extract("locked_doc.txt")
            assert result is None
