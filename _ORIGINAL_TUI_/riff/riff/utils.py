"""Shared utilities for riff commands."""

import json
from typing import Any, Dict, Iterator, List, Optional
from pathlib import Path
from rich.console import Console

console = Console()


def parse_jsonl_line(line: str, line_number: int) -> Optional[Dict[str, Any]]:
    """
    Parse a single JSONL line with error handling.
    
    Args:
        line: The line to parse
        line_number: Line number for error reporting
        
    Returns:
        Parsed JSON dict or None if invalid
    """
    line = line.strip()
    if not line:
        return None
    
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        console.print(f"[yellow]Warning: Line {line_number} - Invalid JSON: {e}[/yellow]")
        return None


def iter_jsonl_safe(path: Path) -> Iterator[Dict[str, Any]]:
    """
    Safely iterate over JSONL file, skipping invalid lines.
    
    Args:
        path: Path to JSONL file
        
    Yields:
        Valid JSON dicts from the file
    """
    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            parsed = parse_jsonl_line(line, line_num)
            if parsed is not None:
                yield parsed


def load_jsonl_safe(path: Path) -> List[Dict[str, Any]]:
    """
    Load all valid lines from a JSONL file.
    
    Args:
        path: Path to JSONL file
        
    Returns:
        List of valid JSON dicts
    """
    return list(iter_jsonl_safe(path))


def get_message_role(msg: Dict[str, Any]) -> Optional[str]:
    """
    Extract role from a message dict, handling various formats.
    
    Args:
        msg: Message dict
        
    Returns:
        Role string or None
    """
    # Try message.role first, then type field
    return (msg.get("message") or {}).get("role") or msg.get("type")


def get_message_content(msg: Dict[str, Any]) -> List[Any]:
    """
    Extract content from a message dict, handling various formats.
    
    Args:
        msg: Message dict
        
    Returns:
        Content list (empty list if no content)
    """
    # Try message.content first, then content field, default to empty list
    return (msg.get("message") or {}).get("content") or msg.get("content") or []


def normalize_message_structure(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize message to have consistent structure.
    
    Args:
        msg: Message dict
        
    Returns:
        Normalized message dict with 'message' key
    """
    if "message" not in msg:
        role = msg.get("type", "unknown")
        content = msg.get("content", [])
        msg["message"] = {"role": role, "content": content}
    return msg