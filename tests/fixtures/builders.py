"""
Mock response builders for Qdrant testing
Creates realistic mock responses matching actual Qdrant API structure
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import uuid


@dataclass
class MockPoint:
    """Mock Qdrant point matching actual API structure"""
    id: str
    payload: Dict[str, Any]
    score: Optional[float] = None
    vector: Optional[List[float]] = None

    def to_dict(self):
        """Convert to dict format for JSON serialization"""
        result = {
            "id": self.id,
            "payload": self.payload
        }
        if self.score is not None:
            result["score"] = self.score
        if self.vector is not None:
            result["vector"] = self.vector
        return result


class MockQdrantResponse:
    """Mock response matching Qdrant client response structure"""

    def __init__(self, points: List[MockPoint]):
        self.points = points

    def __iter__(self):
        """Make response iterable like actual Qdrant response"""
        return iter(self.points)

    def __len__(self):
        return len(self.points)

    def __getitem__(self, index):
        return self.points[index]


class MockResponseBuilder:
    """Build realistic Qdrant API responses for testing"""

    @staticmethod
    def search_response(
        sessions: List[Dict[str, Any]],
        scores: List[float]
    ) -> List[MockPoint]:
        """
        Build mock search response with scores

        Args:
            sessions: List of session payloads
            scores: Corresponding similarity scores

        Returns:
            List of MockPoint objects with scores
        """
        if len(sessions) != len(scores):
            raise ValueError("Sessions and scores must have same length")

        return [
            MockPoint(
                id=session.get('session_id', str(uuid.uuid4())),
                payload=session,
                score=score
            )
            for session, score in zip(sessions, scores)
        ]

    @staticmethod
    def scroll_response(
        sessions: List[Dict[str, Any]],
        offset: Optional[str] = None
    ) -> Tuple[List[MockPoint], Optional[str]]:
        """
        Build mock scroll response for pagination

        Args:
            sessions: List of session payloads
            offset: Next page offset (None if last page)

        Returns:
            Tuple of (points, next_offset)
        """
        points = [
            MockPoint(
                id=session.get('session_id', str(uuid.uuid4())),
                payload=session
            )
            for session in sessions
        ]
        return (points, offset)

    @staticmethod
    def collection_info_response(
        points_count: int = 804,
        vectors_count: int = 804,
        status: str = "ok"
    ) -> Dict[str, Any]:
        """
        Build mock collection info response

        Args:
            points_count: Number of points in collection
            vectors_count: Number of vectors
            status: Collection status

        Returns:
            Collection info dict
        """
        return {
            "status": status,
            "result": {
                "status": "green",
                "points_count": points_count,
                "vectors_count": vectors_count,
                "config": {
                    "params": {
                        "vectors": {
                            "size": 384,
                            "distance": "Cosine"
                        }
                    },
                    "hnsw_config": {
                        "m": 16,
                        "ef_construct": 100,
                        "full_scan_threshold": 10000
                    }
                }
            }
        }

    @staticmethod
    def error_response(
        error_message: str,
        status_code: int = 500
    ) -> Dict[str, Any]:
        """
        Build mock error response

        Args:
            error_message: Error description
            status_code: HTTP status code

        Returns:
            Error response dict
        """
        return {
            "status": "error",
            "error": error_message,
            "status_code": status_code
        }

    @staticmethod
    def build_search_results_with_relevance(
        query: str,
        sessions: List[Dict[str, Any]],
        min_score: float = 0.3
    ) -> List[MockPoint]:
        """
        Build search results with realistic relevance scores

        Args:
            query: Search query
            sessions: Available sessions
            min_score: Minimum score threshold

        Returns:
            Filtered and scored search results
        """
        results = []
        query_lower = query.lower()

        for session in sessions:
            # Calculate mock relevance score
            preview = session.get('content_preview', '').lower()
            working_dir = session.get('working_directory', '').lower()

            score = 0.0

            # Exact match in preview
            if query_lower in preview:
                score += 0.5

            # Partial match in preview
            elif any(word in preview for word in query_lower.split()):
                score += 0.3

            # Match in working directory
            if query_lower in working_dir:
                score += 0.2

            # Apply some variation for realism
            import random
            score += random.uniform(-0.1, 0.1)
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

            if score >= min_score:
                results.append(MockPoint(
                    id=session['session_id'],
                    payload=session,
                    score=score
                ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results


class MockQdrantClient:
    """
    Complete mock Qdrant client for testing
    Implements the same interface as the real QdrantClient
    """

    def __init__(self, sessions: List[Dict[str, Any]] = None):
        """
        Initialize mock client with test data

        Args:
            sessions: Initial session data
        """
        self.sessions = sessions or []
        self.builder = MockResponseBuilder()
        self.connected = True

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[MockPoint]:
        """Mock search implementation"""
        if not self.connected:
            raise ConnectionError("Qdrant not available")

        # For testing, return predefined results based on vector similarity
        # In real tests, you'd compute actual cosine similarity
        all_results = self.builder.build_search_results_with_relevance(
            query="test",  # Would extract from vector in real implementation
            sessions=self.sessions[:limit * 2],  # Get more than limit
            min_score=score_threshold or 0.0
        )

        return all_results[:limit]

    def scroll(
        self,
        collection_name: str,
        scroll_filter: Optional[Dict] = None,
        limit: int = 10,
        offset: Optional[str] = None
    ) -> Tuple[List[MockPoint], Optional[str]]:
        """Mock scroll implementation"""
        if not self.connected:
            raise ConnectionError("Qdrant not available")

        # Filter sessions if filter provided
        filtered_sessions = self.sessions

        if scroll_filter and 'must' in scroll_filter:
            for condition in scroll_filter['must']:
                if condition['key'] == 'session_id':
                    target_id = condition['match']['value']
                    filtered_sessions = [
                        s for s in self.sessions
                        if s['session_id'] == target_id
                    ]

        # Return paginated results
        start = int(offset) if offset else 0
        end = start + limit
        page = filtered_sessions[start:end]

        next_offset = str(end) if end < len(filtered_sessions) else None

        return self.builder.scroll_response(page, next_offset)

    def get_collections(self) -> Dict[str, Any]:
        """Mock get collections"""
        if not self.connected:
            raise ConnectionError("Qdrant not available")

        return {
            "collections": [
                {
                    "name": "claude_sessions",
                    "status": "green"
                }
            ]
        }

    def set_connected(self, connected: bool):
        """Helper to simulate connection issues"""
        self.connected = connected