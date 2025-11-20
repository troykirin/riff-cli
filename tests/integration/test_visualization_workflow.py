"""Integration tests for complete visualization workflow."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from riff.visualization import (
    RiffDagTUIHandler,
    convert_to_dag_format,
    write_temp_jsonl,
)
from riff.visualization.formatter import validate_jsonl_format


class TestSearchToVisualizationWorkflow:
    """Test complete workflow from search results to visualization."""

    @pytest.fixture
    def search_results(self):
        """Sample search results from riff-cli search."""
        return [
            {
                "id": "mem_001",
                "title": "Authentication Implementation",
                "session_id": "session_001",
                "tags": ["auth", "implementation"],
                "timestamp": "2025-11-08T10:00:00Z",
                "related_nodes": ["mem_002", "mem_003"],
            },
            {
                "id": "mem_002",
                "title": "OAuth2 Integration",
                "session_id": "session_001",
                "tags": ["oauth", "security"],
                "timestamp": "2025-11-08T10:15:00Z",
                "related_nodes": ["mem_001"],
            },
            {
                "id": "mem_003",
                "title": "JWT Token Validation",
                "session_id": "session_001",
                "tags": ["jwt", "security"],
                "timestamp": "2025-11-08T10:30:00Z",
                "related_nodes": ["mem_001"],
            },
        ]

    def test_search_to_jsonl_export(self, search_results, tmp_path):
        """Test converting search results to JSONL file."""
        import os

        os.environ["HOME"] = str(tmp_path)

        # Convert and write
        output_path = write_temp_jsonl(search_results)

        assert output_path.exists()
        assert output_path.suffix == ".jsonl"

        # Validate format
        is_valid, message = validate_jsonl_format(output_path)
        assert is_valid is True

    def test_search_to_visualization_complete(self, search_results, tmp_path):
        """Test complete search → export → visualize workflow."""
        import os

        os.environ["HOME"] = str(tmp_path)

        # Step 1: Export search results to JSONL
        jsonl_path = write_temp_jsonl(search_results)
        assert jsonl_path.exists()

        # Step 2: Validate JSONL
        is_valid, message = validate_jsonl_format(jsonl_path)
        assert is_valid is True

        # Step 3: Create handler and verify binary
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()

            # Verify binary is available
            assert handler.verify_installed() is True

            # Step 4: Launch visualization (mocked)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                exit_code = handler.launch(jsonl_path)
                assert exit_code == 0

    def test_jsonl_format_compatibility(self, search_results, tmp_path):
        """Test that exported JSONL is compatible with riff-dag-tui format."""
        import os

        os.environ["HOME"] = str(tmp_path)

        jsonl_path = write_temp_jsonl(search_results)

        # Parse and verify structure
        with open(jsonl_path) as f:
            records = [json.loads(line) for line in f]

        # Separate nodes and edges
        nodes = [r for r in records if r["type"] == "node"]
        edges = [r for r in records if r["type"] == "edge"]

        # Verify nodes have required fields
        required_node_fields = {"type", "id", "label"}
        for node in nodes:
            assert all(field in node for field in required_node_fields)

        # Verify edges have required fields
        required_edge_fields = {"type", "from", "to"}
        for edge in edges:
            assert all(field in edge for field in required_edge_fields)

        # Verify relationships exist
        assert len(edges) > 0

    def test_large_result_set_export(self, tmp_path):
        """Test exporting large number of search results."""
        import os

        os.environ["HOME"] = str(tmp_path)

        # Generate large result set
        large_results = [
            {
                "id": f"mem_{i:06d}",
                "title": f"Memory Entry {i}",
                "session_id": f"session_{i // 100}",
                "tags": [f"tag_{i % 10}"],
                "timestamp": "2025-11-08T10:00:00Z",
                "related_nodes": (
                    [f"mem_{(i-1):06d}"] if i > 0 else []
                ),  # Create chain
            }
            for i in range(1000)
        ]

        # Export
        jsonl_path = write_temp_jsonl(large_results)

        # Validate
        is_valid, message = validate_jsonl_format(jsonl_path)
        assert is_valid is True
        assert "1000 nodes" in message


class TestErrorHandlingInWorkflow:
    """Test error handling in visualization workflow."""

    def test_workflow_with_invalid_results(self, tmp_path):
        """Test workflow handles invalid search results gracefully."""
        import os

        os.environ["HOME"] = str(tmp_path)

        # Invalid results (missing required fields)
        invalid_results = [
            {"id": "1"},  # Missing title and session_id
            {"title": "Test"},  # Missing id
        ]

        # Should still create JSONL (formatter is permissive)
        jsonl_path = write_temp_jsonl(invalid_results)
        assert jsonl_path.exists()

        # Validate (should still have nodes)
        is_valid, message = validate_jsonl_format(jsonl_path)
        assert is_valid is True

    def test_workflow_with_special_characters(self, tmp_path):
        """Test workflow handles special characters in results."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [
            {
                "id": "mem_001",
                "title": 'Test with "quotes" and \\backslashes\\',
                "session_id": "session_001",
                "tags": ["emoji_🔍", "unicode_中文"],
            }
        ]

        jsonl_path = write_temp_jsonl(results)

        # Validate and read back
        is_valid, message = validate_jsonl_format(jsonl_path)
        assert is_valid is True

        with open(jsonl_path) as f:
            record = json.loads(f.readline())
            assert "quotes" in record["label"]

    def test_missing_binary_error_recovery(self, tmp_path):
        """Test graceful error when binary is not available."""
        import os

        os.environ["HOME"] = str(tmp_path)

        with patch("shutil.which", return_value=None):
            with patch.object(Path, "home", return_value=tmp_path):
                with patch.object(Path, "exists", return_value=False):
                    with pytest.raises(FileNotFoundError):
                        handler = RiffDagTUIHandler()


class TestTemporaryFileManagement:
    """Test temporary file creation and cleanup."""

    def test_temp_file_location(self, tmp_path):
        """Test that temp files are created in XDG-compliant location."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [{"id": "1", "title": "Test", "session_id": "sess_1", "tags": []}]

        jsonl_path = write_temp_jsonl(results)

        # Verify location
        expected_cache_dir = tmp_path / ".cache" / "riff"
        assert expected_cache_dir in jsonl_path.parents

    def test_temp_file_naming(self, tmp_path):
        """Test that temp files have correct naming convention."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [{"id": "1", "title": "Test", "session_id": "sess_1", "tags": []}]

        # Default prefix
        path1 = write_temp_jsonl(results)
        assert "riff-search" in path1.name

        # Custom prefix
        path2 = write_temp_jsonl(results, prefix="custom")
        assert "custom" in path2.name

        # All should end with .jsonl
        assert path1.suffix == ".jsonl"
        assert path2.suffix == ".jsonl"

    def test_multiple_temp_files(self, tmp_path):
        """Test creating multiple temporary files."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [{"id": "1", "title": "Test", "session_id": "sess_1", "tags": []}]

        # Create multiple files
        paths = [write_temp_jsonl(results) for _ in range(5)]

        # All should exist
        for path in paths:
            assert path.exists()

        # All should have unique names
        filenames = [p.name for p in paths]
        assert len(set(filenames)) == len(filenames)


class TestCLIIntegration:
    """Test integration with CLI commands."""

    def test_visualize_command_integration(self, tmp_path):
        """Test the visualize command with sample JSONL file."""
        # Create sample JSONL
        jsonl_path = tmp_path / "test.jsonl"
        jsonl_path.write_text(
            '{"type": "node", "id": "1", "label": "Test"}\n'
            '{"type": "edge", "from": "1", "to": "2"}\n'
            '{"type": "node", "id": "2", "label": "Test2"}\n'
        )

        # Validate it
        is_valid, message = validate_jsonl_format(jsonl_path)
        assert is_valid is True

    def test_search_with_visualize_flag(self, tmp_path):
        """Test search command with --visualize flag."""
        import os

        os.environ["HOME"] = str(tmp_path)

        # Simulate search results
        search_results = [
            {
                "id": "1",
                "title": "Result 1",
                "session_id": "sess_1",
                "tags": [],
            }
        ]

        # Export would be done by CLI
        jsonl_path = write_temp_jsonl(search_results)

        # Create handler
        cargo_bin = tmp_path / ".cargo" / "bin"
        cargo_bin.mkdir(parents=True)
        binary_path = cargo_bin / "riff-dag-tui"
        binary_path.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            handler = RiffDagTUIHandler()

            # Simulate visualize
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                exit_code = handler.launch(jsonl_path)
                assert exit_code == 0


class TestDataRoundtrip:
    """Test data integrity through complete workflow."""

    def test_data_preservation_roundtrip(self, tmp_path):
        """Test that data is preserved through export and read-back."""
        import os

        os.environ["HOME"] = str(tmp_path)

        original_data = {
            "id": "mem_001",
            "title": "Test Memory",
            "session_id": "session_001",
            "tags": ["tag1", "tag2"],
            "timestamp": "2025-11-08T10:00:00Z",
        }

        results = [original_data]

        # Export
        jsonl_path = write_temp_jsonl(results)

        # Read back
        with open(jsonl_path) as f:
            lines = f.readlines()

        node = json.loads(lines[0])

        # Verify data preservation
        assert node["id"] == original_data["id"]
        assert node["label"] == original_data["title"]
        assert node["span"] == original_data["session_id"]
        assert node["tags"] == original_data["tags"]
        assert node["ts"] == original_data["timestamp"]

    def test_edge_relationships_preserved(self, tmp_path):
        """Test that edge relationships are correctly preserved."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [
            {
                "id": "node_1",
                "title": "Parent",
                "session_id": "sess_1",
                "tags": [],
                "related_nodes": ["node_2", "node_3"],
            }
        ]

        jsonl_path = write_temp_jsonl(results)

        with open(jsonl_path) as f:
            records = [json.loads(line) for line in f]

        edges = [r for r in records if r["type"] == "edge"]

        # Should have 2 edges
        assert len(edges) == 2
        assert edges[0]["from"] == "node_1"
        assert edges[1]["from"] == "node_1"
        assert set(e["to"] for e in edges) == {"node_2", "node_3"}
