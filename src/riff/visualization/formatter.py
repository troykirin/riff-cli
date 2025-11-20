"""JSONL formatting for riff-dag-tui compatibility.

Converts search results to riff-dag-tui input format:
- type: "node" or "edge"
- id: unique identifier
- label: display text
- span: session/span grouping
- tags: array of tags
- ts: ISO 8601 timestamp
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Generator, Optional, List
from datetime import datetime
from rich.console import Console

console = Console()


def convert_to_dag_format(
    results: List[Any],
    include_edges: bool = True,
) -> Generator[dict, None, None]:
    """Convert search results to riff-dag-tui JSONL format.

    Args:
        results: List of search result dicts
        include_edges: Whether to generate edge records

    Yields:
        JSONL-compatible dict objects (node and edge records)
    """
    if not results:
        return

    # Yield node records
    for i, result in enumerate(results):
        node_id = result.get("id") or result.get("session_id") or f"node_{i}"

        yield {
            "type": "node",
            "id": str(node_id),
            "label": str(result.get("title", "Untitled"))[:100],
            "span": str(result.get("session_id", "unknown")),
            "tags": result.get("tags", []),
            "ts": result.get("timestamp", datetime.now().isoformat()),
        }

    # Yield edge records if relationships exist
    if include_edges:
        for result in results:
            node_id = result.get("id") or result.get("session_id")
            if not node_id:
                continue

            # Add edges from relationships
            for related_id in result.get("related_nodes", []):
                yield {
                    "type": "edge",
                    "from": str(node_id),
                    "to": str(related_id),
                }


def write_temp_jsonl(
    data: List[Any],
    prefix: str = "riff-search",
    include_edges: bool = True,
) -> Path:
    """Write search results to temporary JSONL file.

    Uses XDG-compliant temp directory: ~/.cache/riff/

    Args:
        data: List of search results
        prefix: Prefix for filename
        include_edges: Whether to include edge records

    Returns:
        Path to created JSONL file

    Raises:
        IOError: If unable to write file
    """
    # Create XDG-compliant cache directory
    cache_dir = Path.home() / ".cache" / "riff"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary file in cache directory
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=cache_dir,
        prefix=prefix + "_",
        suffix=".jsonl",
        delete=False,
    ) as f:
        temp_path = Path(f.name)

        # Write JSONL data
        try:
            converted = convert_to_dag_format(data, include_edges=include_edges)
            for record in converted:
                f.write(json.dumps(record) + "\n")

            console.print(
                f"[green]✓[/green] Exported {len(data)} results to [cyan]{temp_path}[/cyan]"
            )
            return temp_path

        except Exception as e:
            console.print(f"[red]Error writing JSONL:[/red] {e}")
            temp_path.unlink(missing_ok=True)
            raise


def validate_jsonl_format(jsonl_path: Path) -> tuple[bool, str]:
    """Validate JSONL file format for riff-dag-tui compatibility.

    Args:
        jsonl_path: Path to JSONL file

    Returns:
        Tuple of (is_valid, message)
    """
    if not jsonl_path.exists():
        return False, f"File not found: {jsonl_path}"

    try:
        node_count = 0
        edge_count = 0

        with open(jsonl_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue

                record = json.loads(line)
                record_type = record.get("type")

                if record_type == "node":
                    # Validate required fields
                    if not record.get("id"):
                        return False, "Node missing required field: id"
                    if not record.get("label"):
                        return False, "Node missing required field: label"
                    node_count += 1

                elif record_type == "edge":
                    # Validate required fields
                    if not record.get("from"):
                        return False, "Edge missing required field: from"
                    if not record.get("to"):
                        return False, "Edge missing required field: to"
                    edge_count += 1

        if node_count == 0:
            return False, "No nodes found in JSONL file"

        return True, f"Valid: {node_count} nodes, {edge_count} edges"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error validating JSONL: {e}"
