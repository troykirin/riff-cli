"""
Integration tests for persistence provider backends.

Tests the pluggable persistence provider system for repairs, including:
- JSONLRepairProvider (JSONL backend)
- SurrealDBRepairProvider (SurrealDB backend)
- Backend switching and auto-detection
- RepairManager with different backends
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
import tempfile
import json

from riff.graph.persistence_provider import PersistenceProvider, RepairSnapshot
from riff.graph.persistence_providers import JSONLRepairProvider
from riff.graph.repair_manager import RepairManager, create_repair_manager
from riff.graph.repair import RepairOperation as EngineRepairOperation
from riff.graph.models import Session, Message, Thread, ThreadType, MessageType
from riff.graph.dag import ConversationDAG
from riff.graph.loaders import JSONLLoader
from riff.surrealdb.repair_provider import SurrealDBRepairProvider
from riff.surrealdb.storage import SurrealDBStorage, RepairEvent


class TestJSONLRepairProvider:
    """Test JSONLRepairProvider backend."""

    @pytest.fixture
    def provider(self):
        """Create JSONL repair provider with temp backup directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield JSONLRepairProvider(backup_root=Path(tmpdir))

    def test_backend_name(self, provider):
        """Test backend name identification."""
        assert provider.get_backend_name() == "JSONL"

    def test_create_backup(self, provider):
        """Test backup creation."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            source_path = Path(f.name)
            f.write(b'{"id": "msg-1", "content": "test"}\n')

        try:
            backup_path = provider.create_backup("session-123", source_path)
            assert backup_path.exists()
            assert backup_path.stat().st_size > 0
        finally:
            source_path.unlink()
            backup_path.unlink()

    def test_apply_repair_creates_repair_operation(self, provider):
        """Test that apply_repair accepts EngineRepairOperation."""
        repair_op = EngineRepairOperation(
            message_id="msg-123",
            original_parent_uuid="parent-old",
            suggested_parent_uuid="parent-new",
            similarity_score=0.95,
            reason="Test repair",
            timestamp="2025-01-20T15:30:00Z",
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            source_path = Path(f.name)
            f.write(b'{"id": "msg-123", "parentUuid": "parent-old"}\n')

        try:
            # Even if it fails, it should accept the operation
            provider.apply_repair(source_path, repair_op)
        finally:
            source_path.unlink()

    def test_show_undo_history_returns_empty_for_new_session(self, provider):
        """Test that undo history is empty for new session."""
        history = provider.show_undo_history("nonexistent-session")
        assert history == []

    def test_backend_fallback(self):
        """Test fallback to JSONL when creation fails."""
        provider = JSONLRepairProvider()
        assert provider is not None
        assert provider.get_backend_name() == "JSONL"


class TestSurrealDBRepairProvider:
    """Test SurrealDBRepairProvider backend."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock SurrealDBStorage."""
        storage = Mock(spec=SurrealDBStorage)
        storage.log_repair_event.return_value = True
        storage.get_session_history.return_value = []
        return storage

    @pytest.fixture
    def provider(self, mock_storage):
        """Create SurrealDB repair provider with mocked storage."""
        return SurrealDBRepairProvider(storage=mock_storage, operator="test")

    def test_backend_name(self, provider):
        """Test backend name identification."""
        assert provider.get_backend_name() == "SurrealDB"

    def test_create_backup_returns_virtual_path(self, provider):
        """Test that backup creates virtual SurrealDB path."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            source_path = Path(f.name)

        try:
            backup_path = provider.create_backup("session-123", source_path)

            # Should return a virtual path
            backup_str = str(backup_path)
            assert "surrealdb:" in backup_str  # Can be surrealdb:// or surrealdb:/
            assert "session-123" in backup_str
        finally:
            source_path.unlink()

    def test_apply_repair_logs_event(self, provider, mock_storage):
        """Test that apply_repair logs to SurrealDB."""
        repair_op = EngineRepairOperation(
            message_id="msg-123",
            original_parent_uuid="parent-old",
            suggested_parent_uuid="parent-new",
            similarity_score=0.95,
            reason="Test repair",
            timestamp="2025-01-20T15:30:00Z",
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            source_path = Path(f.name)

        try:
            success = provider.apply_repair(source_path, repair_op)
            assert success
            mock_storage.log_repair_event.assert_called_once()
        finally:
            source_path.unlink()

    def test_apply_repair_handles_failure(self, provider, mock_storage):
        """Test that apply_repair handles SurrealDB failures gracefully."""
        mock_storage.log_repair_event.return_value = False

        repair_op = EngineRepairOperation(
            message_id="msg-123",
            original_parent_uuid=None,
            suggested_parent_uuid="parent-new",
            similarity_score=0.95,
            reason="Test repair",
            timestamp=None,
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            source_path = Path(f.name)

        try:
            success = provider.apply_repair(source_path, repair_op)
            assert not success
        finally:
            source_path.unlink()

    def test_rollback_creates_revert_event(self, provider, mock_storage):
        """Test that rollback creates a revert event."""
        # First, apply a repair
        repair_op = EngineRepairOperation(
            message_id="msg-123",
            original_parent_uuid=None,
            suggested_parent_uuid="parent-new",
            similarity_score=0.95,
            reason="Test repair",
            timestamp=None,
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            source_path = Path(f.name)

        try:
            # Apply repair first
            provider.apply_repair(source_path, repair_op)

            # Reset mock for rollback
            mock_storage.log_repair_event.reset_mock()

            # Rollback should log a revert event
            backup_path = Path("surrealdb://event/test")
            success = provider.rollback_to_backup(source_path, backup_path)
            assert success
            mock_storage.log_repair_event.assert_called_once()
        finally:
            source_path.unlink()

    def test_show_undo_history_queries_storage(self, provider, mock_storage):
        """Test that undo history queries SurrealDB."""
        test_event = RepairEvent(
            session_id="session-123",
            timestamp=datetime.now(timezone.utc),
            operator="test",
            message_id="msg-123",
            old_parent_uuid="old-parent",
            new_parent_uuid="new-parent",
            reason="Test repair",
            validation_passed=True,
        )
        mock_storage.get_session_history.return_value = [test_event]

        history = provider.show_undo_history("session-123")

        assert len(history) == 1
        assert history[0].timestamp == test_event.timestamp.isoformat()
        mock_storage.get_session_history.assert_called_once_with("session-123")


class TestRepairManagerWithProviders:
    """Test RepairManager with different persistence providers."""

    @pytest.fixture
    def session(self):
        """Create a test session."""
        now_iso = datetime.now(timezone.utc).isoformat()
        msg1 = Message(
            uuid="msg-1",
            type=MessageType.USER,
            content="Hello",
            parent_uuid=None,
            timestamp=now_iso,
            session_id="session-123",
        )
        msg2 = Message(
            uuid="msg-2",
            type=MessageType.ASSISTANT,
            content="Hi there",
            parent_uuid="msg-1",
            timestamp=now_iso,
            session_id="session-123",
        )
        thread = Thread(
            thread_id="thread-1",
            thread_type=ThreadType.MAIN,
            messages=[msg1, msg2],
        )
        session = Session(
            session_id="session-123",
            messages=[msg1, msg2],
            threads=[thread],
            orphans=[],
        )
        return session

    @pytest.fixture
    def dag_and_loader(self):
        """Create mock DAG and loader."""
        dag = Mock(spec=ConversationDAG)
        loader = Mock(spec=JSONLLoader)

        # Mock to_session
        now_iso = datetime.now(timezone.utc).isoformat()
        msg1 = Message(
            uuid="msg-1",
            type=MessageType.USER,
            content="Hello",
            parent_uuid=None,
            timestamp=now_iso,
            session_id="session-123",
        )
        thread = Thread(
            thread_id="thread-1",
            thread_type=ThreadType.MAIN,
            messages=[msg1],
        )
        session = Session(
            session_id="session-123",
            messages=[msg1],
            threads=[thread],
            orphans=[],
        )
        dag.to_session.return_value = session
        loader.load_messages.return_value = [msg1]

        return dag, loader

    def test_repair_manager_with_jsonl_provider(self, session, dag_and_loader):
        """Test RepairManager with JSONL backend."""
        dag, loader = dag_and_loader

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            jsonl_path = Path(f.name)

        try:
            provider = JSONLRepairProvider()

            manager = create_repair_manager(
                session_id="session-123",
                jsonl_path=jsonl_path,
                session=session,
                dag=dag,
                loader=loader,
                persistence_provider=provider,
            )

            # create_repair_manager returns RepairManager directly
            assert isinstance(manager, RepairManager)
            assert manager.persistence_provider is not None
        finally:
            jsonl_path.unlink()

    def test_repair_manager_with_surrealdb_provider(self, session, dag_and_loader):
        """Test RepairManager with SurrealDB backend."""
        dag, loader = dag_and_loader
        mock_storage = Mock(spec=SurrealDBStorage)

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            jsonl_path = Path(f.name)

        try:
            provider = SurrealDBRepairProvider(storage=mock_storage, operator="test")

            manager = create_repair_manager(
                session_id="session-123",
                jsonl_path=jsonl_path,
                session=session,
                dag=dag,
                loader=loader,
                persistence_provider=provider,
            )

            assert isinstance(manager, RepairManager)
            assert manager.persistence_provider.get_backend_name() == "SurrealDB"
        finally:
            jsonl_path.unlink()

    def test_repair_manager_defaults_to_jsonl(self, session, dag_and_loader):
        """Test RepairManager defaults to JSONL provider."""
        dag, loader = dag_and_loader

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            jsonl_path = Path(f.name)

        try:
            # No provider specified - should default to JSONL
            manager = create_repair_manager(
                session_id="session-123",
                jsonl_path=jsonl_path,
                session=session,
                dag=dag,
                loader=loader,
            )

            assert isinstance(manager, RepairManager)
            # Check that JSONL provider was created
            assert manager.persistence_provider.get_backend_name() == "JSONL"
        finally:
            jsonl_path.unlink()


class TestProviderSwitching:
    """Test switching between different persistence providers."""

    def test_provider_can_be_switched_at_runtime(self):
        """Test that providers can be switched without code changes."""
        # Create two different providers
        jsonl_provider = JSONLRepairProvider()

        with patch('riff.surrealdb.storage.SurrealDBStorage') as mock_storage_class:
            mock_storage = Mock(spec=SurrealDBStorage)
            surrealdb_provider = SurrealDBRepairProvider(
                storage=mock_storage,
                operator="test"
            )

        # Both should work with RepairManager interface
        assert jsonl_provider.get_backend_name() == "JSONL"
        assert surrealdb_provider.get_backend_name() == "SurrealDB"

    def test_abstract_provider_interface(self):
        """Test that PersistenceProvider is properly abstract."""
        # Try to instantiate abstract class directly
        with pytest.raises(TypeError):
            PersistenceProvider()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
