import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pipeline.search.bm25_search import BM25Search
from pipeline.search.semantic_search import SemanticSearch
from pipeline.search.hybrid_search import HybridSearch


class TestBM25Search:
    async def test_empty_query(self):
        searcher = BM25Search()
        result = await searcher.search("", "user1")
        assert result == []

    @patch('pipeline.search.bm25_search.PostgresDBConnection.get_db_connection')
    async def test_successful_search(self, mock_get_conn):
        mock_conn = AsyncMock()
        mock_row1 = {'chunk_id': 'c1', 'rank_score': 0.8}
        mock_row2 = {'chunk_id': 'c2', 'rank_score': 0.6}
        mock_conn.fetch.return_value = [mock_row1, mock_row2]

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn_ctx

        searcher = BM25Search()
        results = await searcher.search("test query", "user1")

        assert len(results) == 2
        assert results[0]['chunk_id'] == 'c1'
        assert results[0]['score'] == 0.8
        assert results[1]['chunk_id'] == 'c2'

    @patch('pipeline.search.bm25_search.PostgresDBConnection.get_db_connection')
    async def test_no_results(self, mock_get_conn):
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn_ctx

        searcher = BM25Search()
        results = await searcher.search("nonexistent", "user1")

        assert results == []


class TestSemanticSearch:
    async def test_empty_query(self):
        searcher = SemanticSearch()
        result = await searcher.search("", "user1")
        assert result == []

    @patch('pipeline.search.semantic_search.AsyncMilvusDBConnection.get_connection')
    @patch('pipeline.search.semantic_search.utility.has_collection')
    @patch('pipeline.search.semantic_search.Collection')
    @patch('pipeline.search.semantic_search.QueryEmbedding.embed_query')
    async def test_successful_search(self, mock_embed, mock_coll_cls, mock_has_coll, mock_conn):
        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_has_coll.return_value = True

        mock_collection = MagicMock()
        mock_coll_cls.return_value = mock_collection

        # Mock search results structure (list of lists of hits)
        mock_hit1 = MagicMock()
        mock_hit1.entity.get.return_value = "c1"
        mock_hit1.distance = 0.95

        mock_search_results = [[mock_hit1]]
        mock_collection.search.return_value = mock_search_results

        searcher = SemanticSearch()

        # Override executor to run synchronously in tests
        searcher._run_in_executor = AsyncMock()
        searcher._run_in_executor.side_effect = lambda f, *args, **kwargs: f(*args, **kwargs)

        # But utility.has_collection and Collection.search must be mocked carefully
        # since we are bypassing the executor in the test
        async def fake_executor(func, *args, **kwargs):
            if func == mock_embed:
                return [0.1, 0.2, 0.3]
            elif func == mock_has_coll:
                return True
            elif func == mock_coll_cls:
                return mock_collection
            elif func == mock_collection.load:
                return None
            elif func == mock_collection.search:
                return mock_search_results
            return None

        searcher._run_in_executor = fake_executor

        results = await searcher.search("test query", "user1")
        assert len(results) == 1
        assert results[0]["chunk_id"] == "c1"
        assert results[0]["score"] == 0.95


class TestHybridSearch:
    async def test_empty_query(self):
        searcher = HybridSearch()
        result = await searcher.search("", "user1")
        assert result == []

    @patch('pipeline.search.hybrid_search.SemanticSearch.search')
    @patch('pipeline.search.hybrid_search.BM25Search.search')
    async def test_rrf_fusion(self, mock_bm25, mock_semantic):
        # Semantic search gives c1, c2
        mock_semantic.return_value = [
            {"chunk_id": "c1", "score": 0.9},
            {"chunk_id": "c2", "score": 0.8}
        ]

        # BM25 gives c2, c3
        mock_bm25.return_value = [
            {"chunk_id": "c2", "score": 10.5},
            {"chunk_id": "c3", "score": 5.2}
        ]

        searcher = HybridSearch(top_k=3, rrf_k=60)
        results = await searcher.search("test", "user1")

        # c2 should win because it appears in both (rank 2 in sem, rank 1 in bm25)
        assert len(results) == 3
        assert results[0]["chunk_id"] == "c2"

        # Extract chunk IDs list
        ids = [r["chunk_id"] for r in results]
        assert "c1" in ids
        assert "c3" in ids

    @patch('pipeline.search.hybrid_search.SemanticSearch.search')
    @patch('pipeline.search.hybrid_search.BM25Search.search')
    async def test_fallback_on_one_failure(self, mock_bm25, mock_semantic):
        # Semantic search fails
        mock_semantic.return_value = None

        # BM25 succeeds
        mock_bm25.return_value = [
            {"chunk_id": "c2", "score": 10.5}
        ]

        searcher = HybridSearch(top_k=3, rrf_k=60)
        results = await searcher.search("test", "user1")

        assert len(results) == 1
        assert results[0]["chunk_id"] == "c2"

    @patch('pipeline.search.hybrid_search.SemanticSearch.search')
    @patch('pipeline.search.hybrid_search.BM25Search.search')
    async def test_both_failures(self, mock_bm25, mock_semantic):
        mock_semantic.return_value = None
        mock_bm25.return_value = None

        searcher = HybridSearch(top_k=3, rrf_k=60)
        results = await searcher.search("test", "user1")

        assert results is None
