"""
Unit tests for QdrantSearcher core functionality
Tests isolated components with all dependencies mocked
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from tests.fixtures.sessions import FIXTURE_SESSIONS
from tests.fixtures.builders import MockPoint, MockResponseBuilder


@pytest.mark.unit
class TestQdrantSearcherInitialization:
    """Test searcher initialization and configuration"""

    def test_initialization_success(self, mock_searcher):
        """Verify successful searcher initialization"""
        assert mock_searcher is not None
        assert mock_searcher.collection_name == "claude_sessions"
        assert mock_searcher.client is not None
        assert mock_searcher.model is not None

    def test_initialization_without_qdrant_deps(self, monkeypatch):
        """Test initialization when Qdrant deps are missing"""
        monkeypatch.setattr("riff.search.qdrant.QDRANT_AVAILABLE", False)

        from riff.search.qdrant import QdrantSearcher

        with pytest.raises(ImportError) as exc_info:
            searcher = QdrantSearcher()

        assert "Qdrant dependencies not installed" in str(exc_info.value)

    def test_custom_qdrant_url(self, mock_qdrant_client, mock_sentence_transformer, monkeypatch):
        """Test initialization with custom Qdrant URL"""
        monkeypatch.setattr("riff.search.qdrant.QDRANT_AVAILABLE", True)

        custom_url = "http://custom-qdrant:6333"
        mock_client_class = Mock(return_value=mock_qdrant_client)

        monkeypatch.setattr("riff.search.qdrant.QdrantClient", mock_client_class)
        monkeypatch.setattr("riff.search.qdrant.SentenceTransformer", lambda m: mock_sentence_transformer)

        from riff.search.qdrant import QdrantSearcher
        searcher = QdrantSearcher(qdrant_url=custom_url)

        mock_client_class.assert_called_once_with(url=custom_url)


@pytest.mark.unit
class TestSearchFunctionality:
    """Test search operations"""

    def test_basic_search_success(self, mock_searcher, test_sessions):
        """Test successful search with results"""
        # Setup mock response
        mock_results = [
            MockPoint(
                id=test_sessions["typical_todowrite"]["session_id"],
                payload=test_sessions["typical_todowrite"],
                score=0.85
            ),
            MockPoint(
                id=test_sessions["typical_hooks"]["session_id"],
                payload=test_sessions["typical_hooks"],
                score=0.72
            )
        ]

        mock_searcher.client.search.return_value = mock_results

        # Perform search
        results = mock_searcher.search("TodoWrite", limit=5)

        # Verify results
        assert len(results) == 2
        assert results[0].session_id == test_sessions["typical_todowrite"]["session_id"]
        assert results[0].score == 0.85
        assert results[1].score == 0.72

        # Verify search was called correctly
        mock_searcher.client.search.assert_called_once()
        call_args = mock_searcher.client.search.call_args
        assert call_args[1]['collection_name'] == 'claude_sessions'
        assert call_args[1]['limit'] == 5

    def test_search_with_no_results(self, mock_searcher):
        """Test search that returns no results"""
        mock_searcher.client.search.return_value = []

        results = mock_searcher.search("nonexistent-query-xyz")

        assert len(results) == 0
        assert results == []

    def test_search_with_empty_query(self, mock_searcher):
        """Test search with empty query string"""
        mock_searcher.client.search.return_value = []

        results = mock_searcher.search("")

        assert len(results) == 0

    def test_search_with_score_threshold(self, mock_searcher, test_sessions):
        """Test search with custom score threshold"""
        mock_results = [
            MockPoint(
                id=test_sessions["typical_todowrite"]["session_id"],
                payload=test_sessions["typical_todowrite"],
                score=0.95
            )
        ]

        mock_searcher.client.search.return_value = mock_results

        results = mock_searcher.search("test", min_score=0.8)

        # Verify threshold was passed
        call_args = mock_searcher.client.search.call_args
        assert call_args[1]['score_threshold'] == 0.8

    def test_search_exception_handling(self, mock_searcher):
        """Test search error handling"""
        mock_searcher.client.search.side_effect = Exception("Connection failed")

        with pytest.raises(RuntimeError) as exc_info:
            mock_searcher.search("test")

        assert "Search failed" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.parametrize("limit", [1, 5, 10, 100])
    def test_search_with_different_limits(self, mock_searcher, limit):
        """Test search with various limit values"""
        mock_searcher.client.search.return_value = []

        mock_searcher.search("test", limit=limit)

        call_args = mock_searcher.client.search.call_args
        assert call_args[1]['limit'] == limit


@pytest.mark.unit
class TestUUIDSearch:
    """Test UUID-based search functionality"""

    def test_uuid_search_found(self, mock_searcher, test_sessions):
        """Test successful UUID lookup"""
        target_session = test_sessions["typical_todowrite"]
        mock_point = MockPoint(
            id=target_session["session_id"],
            payload=target_session
        )

        mock_searcher.client.scroll.return_value = ([mock_point], None)

        result = mock_searcher.search_by_uuid(target_session["session_id"])

        assert result is not None
        assert result.session_id == target_session["session_id"]
        assert result.working_directory == target_session["working_directory"]
        assert result.score == 1.0  # Direct match

    def test_uuid_search_not_found(self, mock_searcher):
        """Test UUID lookup when session doesn't exist"""
        mock_searcher.client.scroll.return_value = ([], None)

        result = mock_searcher.search_by_uuid("nonexistent-uuid")

        assert result is None

    def test_uuid_search_exception(self, mock_searcher):
        """Test UUID search error handling"""
        mock_searcher.client.scroll.side_effect = Exception("Database error")

        with pytest.raises(RuntimeError) as exc_info:
            mock_searcher.search_by_uuid("test-uuid")

        assert "UUID search failed" in str(exc_info.value)

    def test_uuid_search_filter_structure(self, mock_searcher):
        """Test that UUID search uses correct filter structure"""
        mock_searcher.client.scroll.return_value = ([], None)

        test_uuid = "test-session-id-123"
        mock_searcher.search_by_uuid(test_uuid)

        call_args = mock_searcher.client.scroll.call_args
        filter_arg = call_args[1]['scroll_filter']

        assert 'must' in filter_arg
        assert len(filter_arg['must']) == 1
        assert filter_arg['must'][0]['key'] == 'session_id'
        assert filter_arg['must'][0]['match']['value'] == test_uuid


@pytest.mark.unit
class TestAvailabilityCheck:
    """Test Qdrant availability checking"""

    def test_is_available_when_connected(self, mock_searcher):
        """Test availability check when Qdrant is accessible"""
        mock_searcher.client.get_collections.return_value = {"collections": []}

        is_available = mock_searcher.is_available()

        assert is_available is True
        mock_searcher.client.get_collections.assert_called_once()

    def test_is_available_when_disconnected(self, mock_searcher):
        """Test availability check when Qdrant is not accessible"""
        mock_searcher.client.get_collections.side_effect = Exception("Connection refused")

        is_available = mock_searcher.is_available()

        assert is_available is False


@pytest.mark.unit
class TestVectorEmbedding:
    """Test vector embedding generation"""

    def test_query_embedding_generation(self, mock_searcher):
        """Test that queries are properly embedded"""
        test_query = "test query"
        expected_vector = [0.1] * 384  # Mock 384-dim vector

        mock_searcher.model.encode.return_value = expected_vector
        mock_searcher.client.search.return_value = []

        mock_searcher.search(test_query)

        # Verify encoding was called
        mock_searcher.model.encode.assert_called_once_with(test_query)

        # Verify vector was passed to search
        call_args = mock_searcher.client.search.call_args
        assert call_args[1]['query_vector'] == expected_vector

    def test_embedding_dimension_consistency(self, mock_searcher):
        """Test that embeddings have correct dimensions"""
        mock_searcher.client.search.return_value = []

        # Model should return 384-dimensional vectors
        mock_searcher.search("test")

        call_args = mock_searcher.client.search.call_args
        query_vector = call_args[1]['query_vector']

        # Should be a list (after .tolist() conversion)
        assert isinstance(query_vector, list)


@pytest.mark.unit
class TestSearchResultMapping:
    """Test mapping from Qdrant responses to SearchResult objects"""

    def test_complete_payload_mapping(self, mock_searcher, test_sessions):
        """Test that all payload fields are correctly mapped"""
        session = test_sessions["federation_context"]
        mock_point = MockPoint(
            id=session["session_id"],
            payload=session,
            score=0.88
        )

        mock_searcher.client.search.return_value = [mock_point]

        results = mock_searcher.search("federation")

        assert len(results) == 1
        result = results[0]

        # Verify all fields mapped correctly
        assert result.session_id == session["session_id"]
        assert result.file_path == session["file_path"]
        assert result.working_directory == session["working_directory"]
        assert result.content_preview == session["content_preview"]
        assert result.score == 0.88

    def test_missing_field_handling(self, mock_searcher):
        """Test handling of missing payload fields"""
        incomplete_payload = {
            "session_id": "test-id",
            "file_path": "/test/path",
            # Missing: working_directory, content_preview
        }

        mock_point = MockPoint(
            id="test-id",
            payload=incomplete_payload,
            score=0.5
        )

        mock_searcher.client.search.return_value = [mock_point]

        # Should raise KeyError for missing fields
        with pytest.raises(KeyError):
            mock_searcher.search("test")


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_unicode_query_handling(self, mock_searcher):
        """Test search with Unicode characters"""
        unicode_query = "测试 テスト тест 🚀"
        mock_searcher.client.search.return_value = []

        # Should not raise any encoding errors
        results = mock_searcher.search(unicode_query)

        assert results == []
        mock_searcher.model.encode.assert_called_once_with(unicode_query)

    def test_very_long_query(self, mock_searcher):
        """Test search with very long query string"""
        long_query = "test " * 1000  # 5000 characters
        mock_searcher.client.search.return_value = []

        results = mock_searcher.search(long_query)

        assert results == []

    def test_special_characters_in_query(self, mock_searcher):
        """Test search with special characters"""
        special_query = "test & <html> $var 'quotes' \"double\""
        mock_searcher.client.search.return_value = []

        results = mock_searcher.search(special_query)

        assert results == []

    def test_negative_score_threshold(self, mock_searcher):
        """Test search with negative score threshold"""
        # Negative threshold should work (though unusual)
        mock_searcher.client.search.return_value = []

        results = mock_searcher.search("test", min_score=-1.0)

        call_args = mock_searcher.client.search.call_args
        assert call_args[1]['score_threshold'] == -1.0

    def test_zero_limit(self, mock_searcher):
        """Test search with zero limit"""
        mock_searcher.client.search.return_value = []

        results = mock_searcher.search("test", limit=0)

        call_args = mock_searcher.client.search.call_args
        assert call_args[1]['limit'] == 0
        assert results == []