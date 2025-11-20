from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.table import Table
from ..utils import iter_jsonl_safe, get_message_role, get_message_content


console = Console()


@dataclass
class ScanIssue:
    file: Path
    missing_ids: list[str]
    assistant_index: int | None


# Use iter_jsonl_safe from utils instead


def detect_missing_tool_results(lines: list[dict]) -> list[ScanIssue]:
    issues: list[ScanIssue] = []
    pending: list[str] = []
    last_assistant_index: int | None = None

    for idx, msg in enumerate(lines):
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "assistant":
            last_assistant_index = idx
            # Safe iteration even if content is not a list
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id"):
                        pending.append(c["id"])
        elif role == "user":
            if pending:
                seen = set()
                # Safe iteration even if content is not a list
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id"):
                            seen.add(c["tool_use_id"])
                missing = [tid for tid in pending if tid not in seen]
                if missing:
                    issues.append(ScanIssue(file=Path(), missing_ids=missing, assistant_index=last_assistant_index))
                pending = []

    if pending:
        issues.append(ScanIssue(file=Path(), missing_ids=list(pending), assistant_index=last_assistant_index))
    return issues


def scan_one(path: Path) -> list[ScanIssue]:
    lines = list(iter_jsonl_safe(path))
    if not lines:
        return []
    issues = detect_missing_tool_results(lines)
    for i in issues:
        i.file = path
    return issues


def cmd_scan(args) -> int:
    target = Path(args.target)
    files: list[Path]
    if target.is_dir():
        files = [p for p in target.rglob(args.glob) if p.is_file()]
    else:
        files = [target]

    all_issues: list[ScanIssue] = []
    for f in files:
        all_issues.extend(scan_one(f))

    if not all_issues:
        console.print("[green]No missing tool_result issues found.[/green]")
        return 0

    table = Table(title="Missing tool_result after tool_use")
    table.add_column("File")
    table.add_column("Assistant idx")
    table.add_column("Missing IDs")

    for issue in all_issues:
        table.add_row(str(issue.file), str(issue.assistant_index or -1), ", ".join(issue.missing_ids))

    console.print(table)

    if args.show:
        for issue in all_issues:
            console.print(f"[yellow]{issue.file} assistant_index={issue.assistant_index}[/yellow]")
            for tid in issue.missing_ids:
                console.print(f"  - {tid}")
    return 1


