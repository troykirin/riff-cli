from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table
from ..utils import iter_jsonl_safe, get_message_role, get_message_content


console = Console()


@dataclass
class ScanIssue:
    file: Path
    missing_ids: list[str]
    assistant_index: int | None
    duplicate_ids: dict[str, dict[str, int | list]] | None = None


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


def detect_duplicate_tool_results(lines: list[dict]) -> dict[str, dict[str, int | list]]:
    """Detect duplicate tool_result blocks with the same ID."""
    duplicates: dict[str, dict] = {}

    for msg_idx, msg in enumerate(lines):
        role = get_message_role(msg)
        if role != "user":
            continue

        content = get_message_content(msg)
        if not isinstance(content, list):
            continue

        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_result":
                tool_id = c.get("tool_use_id")
                if tool_id:
                    if tool_id not in duplicates:
                        duplicates[tool_id] = {"count": 0, "message_indices": set()}
                    duplicates[tool_id]["count"] += 1
                    duplicates[tool_id]["message_indices"].add(msg_idx)

    # Return only IDs with count > 1
    result = {}
    for tool_id, info in duplicates.items():
        if info["count"] > 1:
            result[tool_id] = {
                "count": info["count"],
                "message_indices": sorted(list(info["message_indices"]))
            }
    return result


def scan_one(path: Path) -> list[ScanIssue]:
    lines = list(iter_jsonl_safe(path))
    if not lines:
        return []
    issues = detect_missing_tool_results(lines)
    duplicates = detect_duplicate_tool_results(lines)

    for i in issues:
        i.file = path
        if duplicates:
            i.duplicate_ids = duplicates

    # If only duplicates found but no missing, create an issue for them
    if not issues and duplicates:
        issue = ScanIssue(
            file=path,
            missing_ids=[],
            assistant_index=None,
            duplicate_ids=duplicates
        )
        issues.append(issue)

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
        console.print("[green]No issues found (no missing or duplicate tool_results).[/green]")
        return 0

    # Show missing tool_results table if any
    has_missing = any(issue.missing_ids for issue in all_issues)
    if has_missing:
        table = Table(title="Missing tool_result after tool_use")
        table.add_column("File")
        table.add_column("Assistant idx")
        table.add_column("Missing IDs")

        for issue in all_issues:
            if issue.missing_ids:
                table.add_row(str(issue.file), str(issue.assistant_index or -1), ", ".join(issue.missing_ids))

        console.print(table)

    # Show duplicate tool_results table if any
    has_duplicates = any(issue.duplicate_ids for issue in all_issues)
    if has_duplicates:
        dup_table = Table(title="Duplicate tool_result blocks (same ID appears multiple times)")
        dup_table.add_column("File")
        dup_table.add_column("Tool ID")
        dup_table.add_column("Total Count")
        dup_table.add_column("Message Indices")

        for issue in all_issues:
            if issue.duplicate_ids:
                for tool_id, info in issue.duplicate_ids.items():
                    msg_indices = ", ".join(str(i) for i in info["message_indices"])
                    dup_table.add_row(
                        str(issue.file),
                        tool_id[:20] + "..." if len(tool_id) > 20 else tool_id,
                        str(info["count"]),
                        msg_indices
                    )

        console.print(dup_table)

    if args.show:
        if has_missing:
            console.print("\n[bold cyan]Missing tool_results:[/bold cyan]")
            for issue in all_issues:
                if issue.missing_ids:
                    console.print(f"[yellow]{issue.file}[/yellow]")
                    for tid in issue.missing_ids:
                        console.print(f"  - {tid}")

        if has_duplicates:
            console.print("\n[bold cyan]Duplicate tool_results:[/bold cyan]")
            for issue in all_issues:
                if issue.duplicate_ids:
                    console.print(f"[yellow]{issue.file}[/yellow]")
                    for tool_id, info in issue.duplicate_ids.items():
                        console.print(f"  - {tool_id}: appears {info['count']} times")
                        for msg_idx in info["message_indices"]:
                            console.print(f"      in message[{msg_idx}]")

    return 1


