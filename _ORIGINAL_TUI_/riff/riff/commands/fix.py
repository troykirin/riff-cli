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


console = Console()


def repair_stream(lines: list[dict]) -> list[dict]:
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

    fixed = repair_stream(lines)

    out_path = path if args.in_place else path.with_suffix(path.suffix + ".repaired")
    with out_path.open("w", encoding="utf-8") as f:
        for m in fixed:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    console.print(f"[green]Wrote {out_path}[/green]")
    return 0


