from __future__ import annotations

import json
from pathlib import Path
from rich.console import Console
from ..utils import (
    load_jsonl_safe,
    get_message_role,
    get_message_content,
    normalize_message_structure,
)
from .scan import detect_duplicate_tool_results
from ...backup import create_backup
from ...config import get_config


console = Console()


def deduplicate_tool_results(lines: list[dict]) -> list[dict]:
    """Remove duplicate tool_result blocks, keeping only the first occurrence of each ID."""
    seen_tool_results: set[str] = set()
    deduplicated: list[dict] = []

    for msg in lines:
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "user" and isinstance(content, list):
            filtered_content: list[dict] = []

            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    tool_id = c.get("tool_use_id")
                    if tool_id:
                        # Keep this tool_result only if we haven't seen this ID before
                        if tool_id not in seen_tool_results:
                            seen_tool_results.add(tool_id)
                            filtered_content.append(c)
                        # Skip duplicates
                    else:
                        # No ID, include anyway (safety measure)
                        filtered_content.append(c)
                else:
                    # Not a tool_result, always include
                    filtered_content.append(c)

            # Update the message with filtered content
            msg_copy = msg.copy()
            if "message" in msg_copy:
                msg_copy["message"] = msg_copy["message"].copy()
                msg_copy["message"]["content"] = filtered_content
            else:
                msg_copy["content"] = filtered_content

            deduplicated.append(msg_copy)
        else:
            # Not a user message or content not a list, keep as-is
            deduplicated.append(msg)

    return deduplicated


def repair_stream(lines: list[dict]) -> list[dict]:
    # Step 1: Deduplicate any existing tool_results
    lines = deduplicate_tool_results(lines)

    fixed: list[dict] = []
    pending: list[str] = []
    for msg in lines:
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "assistant":
            # Safe iteration even if content is not iterable
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id"):
                        pending.append(c["id"])
            fixed.append(msg)
            continue

        if role == "user":
            if pending:
                seen = set()
                # Safe iteration even if content is not iterable
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id"):
                            seen.add(c["tool_use_id"])
                missing = [tid for tid in pending if tid not in seen]
                if missing:
                    tr = [{
                        "type": "tool_result",
                        "tool_use_id": tid,
                        "content": "Tool run cancelled by user before completion.",
                        "is_error": True,
                    } for tid in missing]
                    msg = normalize_message_structure(msg)
                    msg["message"]["content"] = tr + (msg["message"].get("content") or [])
                pending = []
            fixed.append(msg)
            continue

        fixed.append(msg)

    if pending:
        fixed.append({
            "type": "user",
            "message": {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tid,
                    "content": "Tool run cancelled by user before completion.",
                    "is_error": True,
                } for tid in pending]
            }
        })

    return fixed


def cmd_fix(args) -> int:
    path = Path(args.path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        return 1

    lines = load_jsonl_safe(path)
    if not lines:
        console.print(f"[yellow]Warning: No valid JSON lines found in {path}[/yellow]")
        return 1

    # Create backup before any modifications if fixing in-place
    if args.in_place:
        config = get_config()
        backup_path = create_backup(path, config, reason="fix")
        if backup_path:
            console.print(f"[dim]Backup created: {backup_path.name}[/dim]")
        else:
            console.print("[yellow]Warning: Could not create backup, proceeding anyway[/yellow]")

    # Check for duplicates before fixing
    duplicates = detect_duplicate_tool_results(lines)
    if duplicates:
        console.print("[cyan]Removing duplicate tool_results...[/cyan]")
        for tool_id, info in duplicates.items():
            console.print(f"  - {tool_id}: removing {info['count'] - 1} duplicate(s) "
                         f"(found in messages: {info['message_indices']})")

    fixed = repair_stream(lines)

    out_path = path if args.in_place else path.with_suffix(path.suffix + ".repaired")
    with out_path.open("w", encoding="utf-8") as f:
        for m in fixed:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    console.print(f"[green]✓ Wrote {out_path}[/green]")
    return 0


