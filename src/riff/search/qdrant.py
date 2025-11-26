"""Qdrant semantic search backend for Claude sessions"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


@dataclass
class SearchResult:
    """Result from semantic search"""
    session_id: str
    file_path: str
    working_directory: str
    content_preview: str
    score: float


class QdrantSearcher:
    """Search Claude sessions using Qdrant vector database

    Uses lazy loading for the embedding model to avoid slow initialization
    when only checking Qdrant availability or performing non-search operations.
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "Qdrant dependencies not installed. "
                "Install with: pip install qdrant-client sentence-transformers"
            )

        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = "claude_sessions"

        # Lazy-load embedding model (expensive operation)
        self._model = None
        self._model_name = None

    @property
    def model(self) -> "SentenceTransformer":
        """Lazy-load embedding model on first access"""
        if self._model is None:
            # Load model name from config
            try:
                from ..config import RiffConfig
                config = RiffConfig()
                self._model_name = config.embedding_model
            except Exception:
                # Fallback if config not available
                self._model_name = 'BAAI/bge-small-en-v1.5'

            # Load the model (this is the expensive operation)
            self._model = SentenceTransformer(self._model_name)

        return self._model

    def _build_time_filter(self, days: Optional[int] = None, since: Optional[str] = None,
                          until: Optional[str] = None) -> Optional[dict]:
        """Build Qdrant filter for time-based queries"""
        if not any([days, since, until]):
            return None

        must_conditions = []

        # Handle --days (past N days from now)
        if days and days > 0:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            must_conditions.append({
                "key": "session_timestamp",
                "range": {
                    "gte": cutoff
                }
            })

        # Handle --since (after specific date)
        if since:
            try:
                since_date = datetime.fromisoformat(since).isoformat()
                must_conditions.append({
                    "key": "session_timestamp",
                    "range": {
                        "gte": since_date
                    }
                })
            except ValueError:
                raise ValueError("Invalid --since date format. Use ISO 8601: YYYY-MM-DD")

        # Handle --until (before specific date)
        if until:
            try:
                until_date = datetime.fromisoformat(until).isoformat()
                must_conditions.append({
                    "key": "session_timestamp",
                    "range": {
                        "lte": until_date
                    }
                })
            except ValueError:
                raise ValueError("Invalid --until date format. Use ISO 8601: YYYY-MM-DD")

        return {"must": must_conditions} if must_conditions else None

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.15,
        days: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> list[SearchResult]:
        """Search for sessions using semantic similarity with optional time filtering"""
        try:
            query_embedding = self.model.encode(query).tolist()

            # Build time-based filter if requested
            query_filter = self._build_time_filter(days, since, until)

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score,
                query_filter=query_filter
            )

            return [
                SearchResult(
                    session_id=r.payload['session_id'] if r.payload else '',
                    file_path=r.payload['file_path'] if r.payload else '',
                    working_directory=r.payload['working_directory'] if r.payload else '',
                    content_preview=r.payload['content_preview'] if r.payload else '',
                    score=r.score if r.score is not None else 0.0
                )
                for r in results
                if r.payload is not None
            ]
        except Exception as e:
            raise RuntimeError(f"Search failed: {e}")

    def search_by_uuid(self, session_id: str) -> Optional[SearchResult]:
        """Search for a specific session by UUID"""
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "session_id",
                            "match": {"value": session_id}
                        }
                    ]
                },
                limit=1
            )

            points = results[0] if results else []
            if not points:
                return None

            p = points[0]
            if not p.payload:
                return None

            return SearchResult(
                session_id=p.payload['session_id'],
                file_path=p.payload['file_path'],
                working_directory=p.payload['working_directory'],
                content_preview=p.payload['content_preview'],
                score=1.0  # Direct match
            )
        except Exception as e:
            raise RuntimeError(f"UUID search failed: {e}")

    def is_available(self) -> bool:
        """Check if Qdrant is available and accessible"""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def get_all_indexed_file_paths(self) -> list[str]:
        """
        Get list of all file paths indexed in Qdrant.
        Used by manifest adapter to validate index integrity.
        """
        try:
            # Use scroll to get ALL indexed sessions (no limit)
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000  # High limit to get all in most cases
            )

            points = results[0] if results else []
            file_paths = []

            for p in points:
                if p.payload and 'file_path' in p.payload:
                    file_paths.append(p.payload['file_path'])

            return file_paths
        except Exception as e:
            # If we can't get indexed paths, return empty list
            # (manifest adapter will handle this gracefully)
            return []

    def search_fuzzy(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.6
    ) -> list[SearchResult]:
        """
        Fallback fuzzy matching search for exact phrases and typo tolerance.
        Uses simple substring and character similarity for word-level queries.
        """
        try:
            # Get all points from collection (with pagination if needed)
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit * 3  # Fetch more to filter
            )

            points = results[0] if results else []
            fuzzy_results = []

            query_lower = query.lower()

            for p in points:
                if not p.payload:
                    continue

                content = p.payload.get('content_preview', '').lower()
                session_id = p.payload.get('session_id', '')

                # Exact substring match gets highest score
                if query_lower in content:
                    score = 1.0
                # Partial word match gets medium-high score
                elif any(word in content for word in query_lower.split()):
                    score = 0.8
                # Character-level similarity as fallback
                else:
                    # Count matching characters (basic Jaro-like similarity)
                    matching_chars = sum(1 for c in query_lower if c in content)
                    score = matching_chars / max(len(query_lower), 1)

                if score >= min_score:
                    fuzzy_results.append({
                        'payload': p.payload,
                        'score': score
                    })

            # Sort by score descending
            fuzzy_results.sort(key=lambda x: x['score'], reverse=True)

            return [
                SearchResult(
                    session_id=r['payload']['session_id'],
                    file_path=r['payload']['file_path'],
                    working_directory=r['payload']['working_directory'],
                    content_preview=r['payload']['content_preview'],
                    score=r['score']
                )
                for r in fuzzy_results[:limit]
            ]
        except Exception as e:
            raise RuntimeError(f"Fuzzy search failed: {e}")
