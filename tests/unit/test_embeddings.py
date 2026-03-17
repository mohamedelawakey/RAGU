import pytest
from unittest.mock import patch, MagicMock
from pipeline.embeddings.embedding import Embedding
from pipeline.embeddings.query_embedding import QueryEmbedding


class TestEmbeddings:
    @patch('pipeline.embeddings.embedding.LoadModel.get_model')
    def test_bulk_embedding_success(self, mock_get_model):
        # Setup mock model
        mock_model = MagicMock()
        mock_encode = MagicMock()
        # Mock numpy array output which tolist() converts to list
        mock_encode.return_value.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_model.encode = mock_encode
        mock_get_model.return_value = mock_model

        chunks = ["Chunk 1", "Chunk 2"]
        result = Embedding.embed(chunks)

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_encode.assert_called_once()
        args, kwargs = mock_encode.call_args
        assert args[0] == chunks
        assert kwargs["convert_to_numpy"] is True

    def test_bulk_embedding_empty_chunks(self):
        result = Embedding.embed([])
        assert result is None

    @patch('pipeline.embeddings.embedding.LoadModel.get_model')
    def test_bulk_embedding_no_model(self, mock_get_model):
        mock_get_model.return_value = None
        result = Embedding.embed(["test"])
        assert result is None

    @patch('pipeline.embeddings.query_embedding.LoadModel.get_model')
    def test_query_embedding_success(self, mock_get_model):
        mock_model = MagicMock()
        mock_encode = MagicMock()
        mock_encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode = mock_encode
        mock_get_model.return_value = mock_model

        result = QueryEmbedding.embed_query("test query")

        assert result == [0.1, 0.2, 0.3]
        mock_encode.assert_called_once()
        args, kwargs = mock_encode.call_args
        assert args[0] == "test query"
        assert kwargs["convert_to_numpy"] is True

    def test_query_embedding_empty_query(self):
        result = QueryEmbedding.embed_query("")
        assert result is None

    def test_query_embedding_whitespace(self):
        result = QueryEmbedding.embed_query("   ")
        assert result is None

    @patch('pipeline.embeddings.query_embedding.LoadModel.get_model')
    def test_query_embedding_no_model(self, mock_get_model):
        mock_get_model.return_value = None
        result = QueryEmbedding.embed_query("test")
        assert result is None
