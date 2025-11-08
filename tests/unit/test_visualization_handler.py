"""Unit tests for RiffDagTUIHandler - subprocess lifecycle management."""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from riff.visualization.handler import RiffDagTUIHandler


class TestRiffDagTUIHandlerBinaryDiscovery:
    """Test binary discovery mechanism with multiple fallback locations."""

    def test_discover_binary_cargo_install(self, tmp_path):
        """Test discovery of binary from ~/.cargo/bin/riff-dag-tui"""
        # Create mock binary
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()
            assert handler.binary_path == binary_path
            assert handler.binary_path.exists()

    def test_discover_binary_from_path(self, tmp_path):
        """Test discovery of binary from system PATH via shutil.which()"""
        binary_path = tmp_path / "riff-dag-tui"
        binary_path.touch()

        with patch("shutil.which") as mock_which:
            mock_which.return_value = str(binary_path)
            with patch.object(Path, "home", return_value=tmp_path):
                handler = RiffDagTUIHandler()
                # Binary was found via PATH
                assert handler.binary_path is not None

    def test_discover_binary_not_found(self, tmp_path):
        """Test error when binary not found in any location."""
        with patch("shutil.which", return_value=None):
            with patch.object(Path, "home", return_value=tmp_path):
                with patch.object(Path, "exists", return_value=False):
                    with pytest.raises(FileNotFoundError) as exc_info:
                        RiffDagTUIHandler()
                    assert "riff-dag-tui binary not found" in str(exc_info.value)

    def test_verify_installed_true(self, tmp_path):
        """Test verify_installed returns True when binary exists."""
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()
            assert handler.verify_installed() is True

    def test_verify_installed_false(self, tmp_path):
        """Test verify_installed returns False when binary not found."""
        # Create a mock handler that simulates binary not found
        handler = Mock(spec=RiffDagTUIHandler)
        handler.binary_path = None
        handler.verify_installed.return_value = False

        assert handler.verify_installed() is False
        assert handler.binary_path is None


class TestRiffDagTUIHandlerLaunch:
    """Test subprocess launching and lifecycle management."""

    @pytest.fixture
    def handler_with_binary(self, tmp_path):
        """Create handler with mock binary."""
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()
            return handler, binary_path

    def test_launch_success(self, handler_with_binary, tmp_path):
        """Test successful subprocess launch."""
        handler, binary_path = handler_with_binary
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text('{"type": "node", "id": "1", "label": "test"}\n')

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            exit_code = handler.launch(jsonl_file)

            assert exit_code == 0
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert str(binary_path) in args[0]
            assert "--input" in args
            assert str(jsonl_file) in args

    def test_launch_missing_input_file(self, handler_with_binary):
        """Test launch with missing input file."""
        handler, _ = handler_with_binary
        missing_file = Path("/nonexistent/file.jsonl")

        exit_code = handler.launch(missing_file)
        assert exit_code == 1

    def test_launch_process_failure(self, handler_with_binary, tmp_path):
        """Test handling of subprocess failure."""
        handler, _ = handler_with_binary
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text('{"type": "node", "id": "1"}\n')

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            exit_code = handler.launch(jsonl_file)
            assert exit_code == 1

    def test_launch_subprocess_exception(self, handler_with_binary, tmp_path):
        """Test handling of subprocess OSError."""
        handler, _ = handler_with_binary
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text('{"type": "node", "id": "1"}\n')

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Process failed")
            exit_code = handler.launch(jsonl_file)
            assert exit_code == 1

    def test_launch_tty_passthrough(self, handler_with_binary, tmp_path):
        """Test that launch allows riff-dag-tui to control TTY."""
        handler, _ = handler_with_binary
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text('{"type": "node", "id": "1"}\n')

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            handler.launch(jsonl_file)

            # Verify capture_output=False to allow TTY passthrough
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("capture_output") is False


class TestRiffDagTUIHandlerErrorMessages:
    """Test error handling and helpful error messages."""

    def test_get_installation_hint(self, tmp_path):
        """Test installation hint message."""
        # Create handler with cargo bin binary
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()
            hint = handler.get_installation_hint()
            assert "riff-dag-tui not found" in hint
            assert "cargo install" in hint

    def test_error_message_missing_binary(self, tmp_path):
        """Test error message when binary not found."""
        with patch("shutil.which", return_value=None):
            with patch.object(Path, "home", return_value=tmp_path):
                with patch.object(Path, "exists", return_value=False):
                    with pytest.raises(FileNotFoundError) as exc_info:
                        RiffDagTUIHandler()

                    error_msg = str(exc_info.value)
                    assert "cargo install" in error_msg
                    assert "cargo build --release" in error_msg


class TestRiffDagTUIHandlerIntegration:
    """Integration tests for complete handler workflow."""

    def test_handler_initialization_flow(self, tmp_path):
        """Test complete handler initialization flow."""
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()
            assert handler.binary_path is not None
            assert handler.verify_installed() is True

    def test_handler_lifecycle(self, tmp_path):
        """Test complete handler lifecycle: init -> verify -> launch."""
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text('{"type": "node", "id": "1", "label": "test"}\n')

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()

            # Verify binary is installed
            assert handler.verify_installed() is True

            # Launch with mock subprocess
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                exit_code = handler.launch(jsonl_file)
                assert exit_code == 0
