"""Unit tests for JSONL formatter - conversion to riff-dag-tui format."""

import json
import pytest
from pathlib import Path
from datetime import datetime
from riff.visualization.formatter import (
    convert_to_dag_format,
    write_temp_jsonl,
    validate_jsonl_format,
)


class TestConvertToDagFormat:
    """Test conversion of search results to riff-dag-tui JSONL format."""

    def test_convert_empty_results(self):
        """Test conversion of empty results list."""
        results = []
        output = list(convert_to_dag_format(results))
        assert output == []

    def test_convert_single_node(self):
        """Test conversion of single search result to node record."""
        results = [
            {
                "id": "mem_001",
                "title": "Test Memory",
                "session_id": "session_123",
                "tags": ["test", "memory"],
                "timestamp": "2025-11-08T10:00:00Z",
            }
        ]

        output = list(convert_to_dag_format(results))
        assert len(output) == 1

        node = output[0]
        assert node["type"] == "node"
        assert node["id"] == "mem_001"
        assert node["label"] == "Test Memory"
        assert node["span"] == "session_123"
        assert node["tags"] == ["test", "memory"]
        assert node["ts"] == "2025-11-08T10:00:00Z"

    def test_convert_multiple_nodes(self):
        """Test conversion of multiple search results."""
        results = [
            {"id": "node_1", "title": "First", "session_id": "sess_1", "tags": []},
            {"id": "node_2", "title": "Second", "session_id": "sess_1", "tags": []},
            {"id": "node_3", "title": "Third", "session_id": "sess_2", "tags": []},
        ]

        output = list(convert_to_dag_format(results))
        assert len(output) == 3

        for i, node in enumerate(output):
            assert node["type"] == "node"
            assert "id" in node
            assert "label" in node

    def test_convert_nodes_with_edges(self):
        """Test conversion with node relationships (edges)."""
        results = [
            {
                "id": "node_1",
                "title": "Parent",
                "session_id": "sess_1",
                "tags": [],
                "related_nodes": ["node_2", "node_3"],
            },
            {
                "id": "node_2",
                "title": "Child 1",
                "session_id": "sess_1",
                "tags": [],
                "related_nodes": [],
            },
        ]

        output = list(convert_to_dag_format(results, include_edges=True))

        # Should have 2 nodes + 2 edges
        nodes = [r for r in output if r["type"] == "node"]
        edges = [r for r in output if r["type"] == "edge"]

        assert len(nodes) == 2
        assert len(edges) == 2

        # Check edge structure
        assert edges[0]["from"] == "node_1"
        assert edges[0]["to"] == "node_2"

    def test_convert_nodes_without_edges(self):
        """Test conversion without edges when flag is False."""
        results = [
            {
                "id": "node_1",
                "title": "Parent",
                "session_id": "sess_1",
                "tags": [],
                "related_nodes": ["node_2"],
            }
        ]

        output = list(convert_to_dag_format(results, include_edges=False))
        assert len(output) == 1
        assert output[0]["type"] == "node"

    def test_convert_missing_fields(self):
        """Test conversion handles missing optional fields."""
        results = [
            {
                "title": "Test",
                # Missing id, session_id, tags, timestamp
            }
        ]

        output = list(convert_to_dag_format(results))
        assert len(output) == 1

        node = output[0]
        assert node["type"] == "node"
        assert "id" in node  # Should have generated id
        assert node["label"] == "Test"
        assert "span" in node  # Should have default span
        assert "ts" in node  # Should have timestamp

    def test_convert_label_truncation(self):
        """Test label truncation to 100 characters."""
        long_title = "x" * 200
        results = [{"title": long_title}]

        output = list(convert_to_dag_format(results))
        assert len(output[0]["label"]) == 100

    def test_convert_string_conversion(self):
        """Test that all values are converted to strings."""
        results = [
            {
                "id": 123,  # numeric id
                "title": "Test",
                "session_id": 456,  # numeric session_id
            }
        ]

        output = list(convert_to_dag_format(results))
        node = output[0]

        assert isinstance(node["id"], str)
        assert isinstance(node["span"], str)


class TestWriteTempJsonl:
    """Test temporary JSONL file writing."""

    def test_write_temp_jsonl_creates_file(self, tmp_path):
        """Test that write_temp_jsonl creates a file."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [
            {"id": "1", "title": "Test", "session_id": "sess_1", "tags": []}
        ]

        output_path = write_temp_jsonl(results)

        assert output_path.exists()
        assert output_path.suffix == ".jsonl"

    def test_write_temp_jsonl_xdg_directory(self, tmp_path):
        """Test that file is written to ~/.cache/riff/"""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [{"id": "1", "title": "Test", "session_id": "sess_1", "tags": []}]

        output_path = write_temp_jsonl(results)

        expected_dir = tmp_path / ".cache" / "riff"
        assert expected_dir.exists()
        assert output_path.parent == expected_dir

    def test_write_temp_jsonl_custom_prefix(self, tmp_path):
        """Test custom filename prefix."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [{"id": "1", "title": "Test", "session_id": "sess_1", "tags": []}]

        output_path = write_temp_jsonl(results, prefix="custom-prefix")

        assert "custom-prefix" in output_path.name

    def test_write_temp_jsonl_valid_jsonl_format(self, tmp_path):
        """Test that output is valid JSONL."""
        import os

        os.environ["HOME"] = str(tmp_path)

        results = [
            {"id": "1", "title": "First", "session_id": "sess_1", "tags": ["test"]},
            {"id": "2", "title": "Second", "session_id": "sess_1", "tags": []},
        ]

        output_path = write_temp_jsonl(results)

        # Read and parse JSONL
        with open(output_path) as f:
            lines = f.readlines()

        assert len(lines) == 2

        for line in lines:
            obj = json.loads(line)
            assert "type" in obj
            assert "id" in obj

    def test_write_temp_jsonl_handles_error(self, tmp_path):
        """Test error handling during write."""
        import os

        os.environ["HOME"] = str(tmp_path)

        # Create read-only directory to trigger error
        cache_dir = tmp_path / ".cache" / "riff"
        cache_dir.mkdir(parents=True)
        cache_dir.chmod(0o444)

        results = [{"id": "1", "title": "Test", "session_id": "sess_1", "tags": []}]

        try:
            with pytest.raises(Exception):
                write_temp_jsonl(results)
        finally:
            # Restore permissions for cleanup
            cache_dir.chmod(0o755)


class TestValidateJsonlFormat:
    """Test JSONL format validation."""

    def test_validate_valid_jsonl(self, tmp_path):
        """Test validation of valid JSONL file."""
        jsonl_file = tmp_path / "valid.jsonl"
        jsonl_file.write_text(
            '{"type": "node", "id": "1", "label": "Test"}\n'
            '{"type": "edge", "from": "1", "to": "2"}\n'
        )

        is_valid, message = validate_jsonl_format(jsonl_file)
        assert is_valid is True
        assert "Valid" in message
        assert "1 nodes" in message
        assert "1 edges" in message

    def test_validate_missing_file(self, tmp_path):
        """Test validation of non-existent file."""
        missing_file = tmp_path / "missing.jsonl"

        is_valid, message = validate_jsonl_format(missing_file)
        assert is_valid is False
        assert "File not found" in message

    def test_validate_invalid_json(self, tmp_path):
        """Test validation with invalid JSON."""
        jsonl_file = tmp_path / "invalid.jsonl"
        jsonl_file.write_text('{"type": "node", "id": "1" INVALID}\n')

        is_valid, message = validate_jsonl_format(jsonl_file)
        assert is_valid is False
        assert "Invalid JSON" in message

    def test_validate_missing_required_fields_node(self, tmp_path):
        """Test validation detects missing required node fields."""
        jsonl_file = tmp_path / "incomplete.jsonl"
        jsonl_file.write_text('{"type": "node", "id": "1"}\n')  # Missing label

        is_valid, message = validate_jsonl_format(jsonl_file)
        assert is_valid is False
        assert "label" in message

    def test_validate_missing_required_fields_edge(self, tmp_path):
        """Test validation detects missing required edge fields."""
        jsonl_file = tmp_path / "incomplete_edge.jsonl"
        jsonl_file.write_text(
            '{"type": "node", "id": "1", "label": "Test"}\n'
            '{"type": "edge", "from": "1"}\n'  # Missing to
        )

        is_valid, message = validate_jsonl_format(jsonl_file)
        assert is_valid is False
        assert "to" in message

    def test_validate_no_nodes(self, tmp_path):
        """Test validation with no node records."""
        jsonl_file = tmp_path / "no_nodes.jsonl"
        jsonl_file.write_text('{"type": "unknown"}\n')

        is_valid, message = validate_jsonl_format(jsonl_file)
        assert is_valid is False
        assert "No nodes found" in message

    def test_validate_empty_lines(self, tmp_path):
        """Test validation handles empty lines."""
        jsonl_file = tmp_path / "with_empty.jsonl"
        jsonl_file.write_text(
            '{"type": "node", "id": "1", "label": "Test"}\n'
            "\n"
            '{"type": "node", "id": "2", "label": "Test2"}\n'
        )

        is_valid, message = validate_jsonl_format(jsonl_file)
        assert is_valid is True
        assert "2 nodes" in message

    def test_validate_large_dataset(self, tmp_path):
        """Test validation with large number of records."""
        jsonl_file = tmp_path / "large.jsonl"

        with open(jsonl_file, "w") as f:
            for i in range(1000):
                f.write(
                    json.dumps({"type": "node", "id": str(i), "label": f"Node {i}"})
                    + "\n"
                )
            for i in range(999):
                f.write(
                    json.dumps({"type": "edge", "from": str(i), "to": str(i + 1)})
                    + "\n"
                )

        is_valid, message = validate_jsonl_format(jsonl_file)
        assert is_valid is True
        assert "1000 nodes" in message
        assert "999 edges" in message


class TestFormatterIntegration:
    """Integration tests combining multiple formatter functions."""

    def test_convert_and_write_workflow(self, tmp_path):
        """Test complete workflow: convert -> write -> validate."""
        import os

        os.environ["HOME"] = str(tmp_path)

        # Sample search results
        results = [
            {
                "id": "mem_001",
                "title": "Search Result 1",
                "session_id": "session_abc",
                "tags": ["search", "test"],
                "related_nodes": ["mem_002"],
            },
            {
                "id": "mem_002",
                "title": "Related Result",
                "session_id": "session_abc",
                "tags": ["related"],
            },
        ]

        # Write JSONL
        output_path = write_temp_jsonl(results)

        # Validate JSONL
        is_valid, message = validate_jsonl_format(output_path)
        assert is_valid is True

        # Verify contents
        with open(output_path) as f:
            lines = f.readlines()

        objects = [json.loads(line) for line in lines]

        # Should have 2 nodes + 1 edge
        nodes = [o for o in objects if o["type"] == "node"]
        edges = [o for o in objects if o["type"] == "edge"]

        assert len(nodes) == 2
        assert len(edges) == 1
