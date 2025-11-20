"""
Riff Memory Producer - SurrealDB Memory Substrate Integration
==============================================================

Produces memory:item records compatible with Phase 3A SurrealDB schema.

Schema Alignment:
- memory:item (events, spans, states, metrics)
- memory:timeslice (temporal bounds)
- memory:schema_ver (versioning)
- link:relation (dendrite edges)

Integration: Phase 3A ingestion pipeline reads from memory_stream.jsonl
Timeline: Ready for substrate landing in 1.5-2 hours
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4


class RiffMemoryProducer:
    """
    Produces TimeSliced MemoryItems for SurrealDB substrate.

    Each item has:
    - Unique ID (memory:riff_{uuid})
    - Timestamp (ISO 8601 UTC)
    - Source identifier (riff-cli)
    - Schema version (riff.v1.0.0)
    - Kind (event|span|state|metric)
    - Payload (arbitrary JSON)

    Memory items are written to ~/.local/state/nabi/riff/memory_stream.jsonl
    Phase 3A ingestion pipeline consumes this stream.
    """

    def __init__(
        self,
        stream_path: Optional[Path] = None,
        schema_version: str = "riff.v1.0.0",
        enable_logging: bool = True
    ):
        """
        Initialize memory producer.

        Args:
            stream_path: Path to memory stream JSONL file
            schema_version: Schema version for memory items
            enable_logging: Whether to write memory items (disable for testing)
        """
        self.schema_version = schema_version
        self.enable_logging = enable_logging

        # Default stream path: ~/.local/state/nabi/riff/memory_stream.jsonl
        if stream_path is None:
            stream_path = Path("~/.local/state/nabi/riff/memory_stream.jsonl").expanduser()

        self.stream_path = stream_path

        # Ensure parent directory exists
        if self.enable_logging:
            self.stream_path.parent.mkdir(parents=True, exist_ok=True)

    def _generate_id(self, event_type: str) -> str:
        """
        Generate unique memory item ID.

        Format: memory:riff_{event_type}_{uuid}
        Example: memory:riff_reindex_abc123
        """
        short_uuid = str(uuid4())[:8]
        return f"memory:riff_{event_type}_{short_uuid}"

    def _write_item(self, item: Dict[str, Any]) -> None:
        """
        Write memory item to stream.

        Appends JSONL (JSON lines) to memory_stream.jsonl.
        Phase 3A ingestion reads this file periodically.
        """
        if not self.enable_logging:
            return

        try:
            with self.stream_path.open("a") as f:
                f.write(json.dumps(item) + "\n")
        except Exception as e:
            # Graceful degradation: If we can't write memory items,
            # riff still works (just no memory substrate integration)
            pass

    def log_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """
        Log a discrete event (reindex, validation, etc.)

        Args:
            event_type: Type of event (e.g., 'reindex_completed')
            payload: Event-specific data
            session_id: Optional Claude session ID for BELONGS_TO_SESSION edge

        Returns:
            Memory item ID
        """
        item_id = self._generate_id(event_type)

        item = {
            "id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "riff-cli",
            "kind": "event",
            "schema_ver": self.schema_version,
            "event_type": event_type,
            "payload": payload
        }

        if session_id:
            item["session_id"] = session_id

        self._write_item(item)
        return item_id

    def log_span(
        self,
        span_type: str,
        duration_ms: float,
        payload: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """
        Log a time-bounded operation (search, resume, etc.)

        Args:
            span_type: Type of span (e.g., 'search_performed')
            duration_ms: Duration in milliseconds
            payload: Span-specific data
            session_id: Optional Claude session ID

        Returns:
            Memory item ID
        """
        item_id = self._generate_id(span_type)

        item = {
            "id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "riff-cli",
            "kind": "span",
            "schema_ver": self.schema_version,
            "span_type": span_type,
            "duration_ms": duration_ms,
            "payload": payload
        }

        if session_id:
            item["session_id"] = session_id

        self._write_item(item)
        return item_id

    def log_state(
        self,
        state_type: str,
        payload: Dict[str, Any]
    ) -> str:
        """
        Log a state change (manifest update, config change, etc.)

        Args:
            state_type: Type of state (e.g., 'manifest_updated')
            payload: State-specific data

        Returns:
            Memory item ID
        """
        item_id = self._generate_id(state_type)

        item = {
            "id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "riff-cli",
            "kind": "state",
            "schema_ver": self.schema_version,
            "state_type": state_type,
            "payload": payload
        }

        self._write_item(item)
        return item_id

    def log_metric(
        self,
        metric_name: str,
        metric_value: float,
        payload: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a metric observation (latency, staleness, etc.)

        Args:
            metric_name: Name of metric (e.g., 'search_latency')
            metric_value: Numeric value
            payload: Optional additional context

        Returns:
            Memory item ID
        """
        item_id = self._generate_id(metric_name)

        item = {
            "id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "riff-cli",
            "kind": "metric",
            "schema_ver": self.schema_version,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "payload": payload or {}
        }

        self._write_item(item)
        return item_id

    # Convenience methods for common riff operations

    def log_reindex_started(
        self,
        reason: str,
        manifest_hash: str,
        file_count: int
    ) -> str:
        """Log reindex start event"""
        return self.log_event("reindex_started", {
            "reason": reason,
            "manifest_hash_before": manifest_hash,
            "file_count": file_count
        })

    def log_reindex_completed(
        self,
        duration_seconds: int,
        sessions_indexed: int,
        manifest_hash: str,
        success: bool = True
    ) -> str:
        """Log reindex completion event"""
        return self.log_event("reindex_completed", {
            "duration_seconds": duration_seconds,
            "sessions_indexed": sessions_indexed,
            "manifest_hash_after": manifest_hash,
            "success": success
        })

    def log_validation_failed(
        self,
        missing_count: int,
        total_indexed: int,
        stale_percentage: float
    ) -> str:
        """Log index validation failure"""
        return self.log_event("validation_failed", {
            "missing_count": missing_count,
            "total_indexed": total_indexed,
            "stale_percentage": stale_percentage
        })

    def log_search_performed(
        self,
        query: str,
        results_count: int,
        latency_ms: float,
        top_score: Optional[float] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Log search operation"""
        return self.log_span("search_performed", latency_ms, {
            "query": query,
            "results_count": results_count,
            "top_score": top_score
        }, session_id=session_id)

    def log_session_resumed(
        self,
        session_id: str,
        working_directory: str,
        latency_ms: float
    ) -> str:
        """Log session resumption"""
        return self.log_span("session_resumed", latency_ms, {
            "session_id": session_id,
            "working_directory": working_directory
        }, session_id=session_id)

    def log_manifest_changed(
        self,
        manifest_hash: str,
        change_summary: str,
        files_added: int,
        files_removed: int,
        files_modified: int
    ) -> str:
        """Log manifest state change"""
        return self.log_state("manifest_updated", {
            "manifest_hash": manifest_hash,
            "change_summary": change_summary,
            "files_added": files_added,
            "files_removed": files_removed,
            "files_modified": files_modified
        })

    def log_search_latency_metric(self, latency_ms: float) -> str:
        """Log search latency metric"""
        return self.log_metric("search_latency_ms", latency_ms)

    def log_index_staleness_metric(self, stale_percentage: float) -> str:
        """Log index staleness metric"""
        return self.log_metric("index_staleness_pct", stale_percentage)


# Global instance (singleton pattern)
_memory_producer: Optional[RiffMemoryProducer] = None


def get_memory_producer() -> RiffMemoryProducer:
    """
    Get global memory producer instance.

    Lazily initialized on first access.
    Can be disabled via environment variable: RIFF_DISABLE_MEMORY_LOGGING=1
    """
    global _memory_producer

    if _memory_producer is None:
        import os
        enable_logging = os.environ.get("RIFF_DISABLE_MEMORY_LOGGING", "0") != "1"
        _memory_producer = RiffMemoryProducer(enable_logging=enable_logging)

    return _memory_producer
