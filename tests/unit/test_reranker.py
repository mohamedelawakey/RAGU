import pytest
from unittest.mock import patch, MagicMock
from pipeline.reranker.reranker import Reranker


class TestReranker:
    def test_empty_query(self):
        chunks = [{"chunk_id": "1", "text_content": "test", "score": 1.0}]
        result = Reranker.rerank("", chunks)
        assert result is None

    def test_whitespace_query(self):
        chunks = [{"chunk_id": "1", "text_content": "test", "score": 1.0}]
        result = Reranker.rerank("   ", chunks)
        assert result is None

    def test_empty_chunks(self):
        result = Reranker.rerank("query", [])
        assert result == []

    @patch('pipeline.reranker.reranker.api_key', None)
    def test_missing_api_key(self):
        chunks = [{"chunk_id": "1", "text_content": "test", "score": 1.0}]
        result = Reranker.rerank("query", chunks)
        assert result is None

    @patch('pipeline.reranker.reranker.api_key', 'fake_key')
    @patch('pipeline.reranker.reranker.cohere.ClientV2')
    def test_successful_rerank(self, mock_cohere):
        # Setup mock chunks
        chunks = [
            {"chunk_id": "c1", "text_content": "Doc A", "score": 0.5},
            {"chunk_id": "c2", "text_content": "Doc B", "score": 0.8}
        ]

        # Setup mock client
        mock_client = MagicMock()
        mock_cohere.return_value = mock_client

        # Setup mock response
        mock_response = MagicMock()
        res1 = MagicMock()
        res1.index = 1  # Reranker decided "Doc B" (index 1) is best
        res1.relevance_score = 0.99

        res2 = MagicMock()
        res2.index = 0  # "Doc A" is second
        res2.relevance_score = 0.11

        mock_response.results = [res1, res2]
        mock_client.rerank.return_value = mock_response

        # Execute
        result = Reranker.rerank("Find best doc", chunks, top_n=2)

        # Asserts
        assert len(result) == 2
        # First result should be c2
        assert result[0]["chunk_id"] == "c2"
        assert result[0]["rrf_score"] == 0.8
        assert result[0]["rerank_score"] == 0.99
        assert result[0]["text_content"] == "Doc B"

        # Second result should be c1
        assert result[1]["chunk_id"] == "c1"
        assert result[1]["rrf_score"] == 0.5
        assert result[1]["rerank_score"] == 0.11
        assert result[1]["text_content"] == "Doc A"

    @patch('pipeline.reranker.reranker.api_key', 'fake_key')
    @patch('pipeline.reranker.reranker.cohere.ClientV2')
    def test_api_failure(self, mock_cohere):
        chunks = [{"chunk_id": "1", "text_content": "test", "score": 1.0}]

        mock_client = MagicMock()
        mock_client.rerank.side_effect = Exception("API Offline")
        mock_cohere.return_value = mock_client

        # The function catches exceptions and returns None to trigger fallback mechanism
        result = Reranker.rerank("query", chunks)
        assert result is None
