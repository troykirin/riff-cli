"""
Enhanced scan command with duplicate tool_result detection.

This module extends the original scan functionality with production-grade
error handling for detecting duplicate tool_result blocks that indicate
data corruption from session resume operations.

Usage:
    python -m riff scan --path <file> --detect-duplicates --show-duplicates
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..utils import iter_jsonl_safe, get_message_role, get_message_content
from ..duplicate_handler import (
    detect_duplicate_tool_results,
    log_detection_summary,
    RiffDuplicateDetectionError,
    DuplicateDetectionMetrics,
)

# Setup logging
logger = logging.getLogger(__name__)
console = Console()


@dataclass
class ScanIssue:
    """Issue found during scan."""
    file: Path
    missing_ids: list[str]
    assistant_index: int | None


@dataclass
class DuplicateScanResult:
    """Result of scanning for duplicates."""
    file: Path
    duplicates: Dict[str, int]
    metrics: DuplicateDetectionMetrics
    error: Optional[str] = None


def detect_missing_tool_results(lines: list[dict]) -> list[ScanIssue]:
    """
    Original missing tool_results detection.

    Args:
        lines: List of message dicts

    Returns:
        List of ScanIssue objects for missing tool_results
    """
    issues: list[ScanIssue] = []
    pending: list[str] = []
    last_assistant_index: int | None = None

    for idx, msg in enumerate(lines):
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "assistant":
            last_assistant_index = idx
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id"):
                        pending.append(c["id"])
        elif role == "user":
            if pending:
                seen = set()
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


def scan_for_duplicates(path: Path) -> DuplicateScanResult:
    """
    Scan a JSONL file for duplicate tool_result blocks.

    This function safely loads a JSONL file and detects duplicate tool_result
    blocks that indicate data corruption from session resume issues.

    Args:
        path: Path to JSONL file to scan

    Returns:
        DuplicateScanResult with findings or error details

    Example:
        result = scan_for_duplicates(Path("conversation.jsonl"))
        if result.duplicates:
            print(f"Found {len(result.duplicates)} duplicated tool_use_ids")
        if result.error:
            print(f"Error during scan: {result.error}")
    """
    logger.info(f"Starting duplicate scan on {path}")

    try:
        # Load all lines safely
        lines = list(iter_jsonl_safe(path))

        if not lines:
            logger.warning(f"No valid JSON lines found in {path}")
            return DuplicateScanResult(
                file=path,
                duplicates={},
                metrics=DuplicateDetectionMetrics(),
                error="No valid JSON lines found"
            )

        logger.debug(f"Loaded {len(lines)} valid JSON lines")

        # Detect duplicates with full error handling
        duplicates, metrics = detect_duplicate_tool_results(lines)

        logger.info(
            f"Duplicate detection complete: {metrics.duplicates_detected} duplicates "
            f"in {metrics.unique_tool_use_ids} unique tool_use_ids"
        )

        return DuplicateScanResult(
            file=path,
            duplicates=duplicates,
            metrics=metrics,
            error=None
        )

    except RiffDuplicateDetectionError as e:
        logger.error(f"Error during duplicate detection: {str(e)}", exc_info=True)
        return DuplicateScanResult(
            file=path,
            duplicates={},
            metrics=DuplicateDetectionMetrics(),
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during duplicate scan: {str(e)}", exc_info=True)
        return DuplicateScanResult(
            file=path,
            duplicates={},
            metrics=DuplicateDetectionMetrics(),
            error=f"Unexpected error: {str(e)}"
        )


def display_duplicate_results(result: DuplicateScanResult) -> int:
    """
    Display duplicate scan results to user with rich formatting.

    Args:
        result: DuplicateScanResult from scan_for_duplicates

    Returns:
        0 if no duplicates found, 1 if duplicates found, 2 if error occurred
    """
    if result.error:
        console.print(
            Panel(
                f"[red]Error during duplicate scan:[/red]\n{result.error}",
                title="Duplicate Scan Error",
                style="red"
            )
        )
        return 2

    if not result.duplicates:
        console.print("[green]No duplicate tool_result blocks found.[/green]")
        return 0

    # Display summary
    console.print(f"\n[yellow]File:[/yellow] {result.file}")
    console.print(f"[yellow]Total duplicates detected:[/yellow] {result.metrics.duplicates_detected}")
    console.print(f"[yellow]Unique tool_use_ids with duplicates:[/yellow] {len(result.duplicates)}")

    # Display details table
    table = Table(title="Duplicate tool_result Blocks")
    table.add_column("tool_use_id", style="cyan")
    table.add_column("Duplicate Count", style="magenta")
    table.add_column("Total Occurrences", style="magenta")

    for tool_use_id, dup_count in sorted(result.duplicates.items(), key=lambda x: x[1], reverse=True):
        total_occurrences = dup_count + 1
        table.add_row(tool_use_id, str(dup_count), str(total_occurrences))

    console.print(table)

    # Display metrics summary
    if result.metrics.blocks_invalid > 0:
        console.print(f"\n[yellow]Warning:[/yellow] {result.metrics.blocks_invalid} invalid blocks found")
        if result.metrics.validation_failures:
            console.print("Validation failures by type:")
            for error_type, count in result.metrics.validation_failures.items():
                console.print(f"  - {error_type.value}: {count}")

    # Display recovery suggestions
    if result.metrics.duplicates_detected > 50:
        console.print(
            Panel(
                "[yellow]High duplicate count detected.[/yellow]\n"
                "This usually indicates:\n"
                "1. Session resume operations that duplicated tool_results\n"
                "2. Multiple resume cycles stacking duplicates\n\n"
                "Recommendation: Use the fix command to deduplicate:\n"
                "[green]riff fix --path <file> --deduplicate --in-place[/green]",
                title="Recovery Suggestion",
                style="yellow"
            )
        )

    return 1


def cmd_scan_with_duplicates(args) -> int:
    """
    Enhanced scan command entry point with duplicate detection.

    Args:
        args: Parsed command arguments with:
            - target: Path to file or directory
            - glob: Glob pattern for directory scan (default: "*.jsonl")
            - show: Whether to show detailed results
            - detect-duplicates: Whether to detect duplicates (default: True)

    Returns:
        0 if no issues found, 1 if issues found, 2 if error occurred
    """
    target = Path(args.target)
    files: list[Path]

    if target.is_dir():
        files = [p for p in target.rglob(args.glob or "*.jsonl") if p.is_file()]
    else:
        files = [target]

    if not files:
        console.print(f"[yellow]No files matching pattern found in {target}[/yellow]")
        return 0

    logger.info(f"Scanning {len(files)} file(s) for duplicate tool_result blocks")

    all_missing_issues: list[ScanIssue] = []
    all_duplicate_results: list[DuplicateScanResult] = []
    error_count = 0

    for f in files:
        # Original missing tool_results scan
        try:
            lines = list(iter_jsonl_safe(f))
            if lines:
                issues = detect_missing_tool_results(lines)
                for issue in issues:
                    issue.file = f
                all_missing_issues.extend(issues)
        except Exception as e:
            logger.error(f"Error scanning {f} for missing tool_results: {str(e)}")
            error_count += 1

        # New duplicate detection scan
        if hasattr(args, 'detect_duplicates') and args.detect_duplicates:
            result = scan_for_duplicates(f)
            all_duplicate_results.append(result)
            if result.error:
                error_count += 1

    # Display results
    console.print("\n" + "=" * 60)
    console.print("[bold]SCAN RESULTS[/bold]")
    console.print("=" * 60)

    # Missing tool_results
    if all_missing_issues:
        console.print("\n[red]Missing tool_result issues found[/red]")
        table = Table(title="Missing tool_result after tool_use")
        table.add_column("File")
        table.add_column("Assistant idx")
        table.add_column("Missing IDs")

        for issue in all_missing_issues:
            table.add_row(str(issue.file), str(issue.assistant_index or -1), ", ".join(issue.missing_ids))

        console.print(table)
    else:
        console.print("[green]No missing tool_result issues found.[/green]")

    # Duplicates
    if hasattr(args, 'detect_duplicates') and args.detect_duplicates:
        console.print("\n")
        for result in all_duplicate_results:
            display_duplicate_results(result)

    if error_count > 0:
        console.print(f"\n[yellow]Warning: {error_count} error(s) encountered during scan[/yellow]")
        return 2

    if all_missing_issues or any(r.duplicates for r in all_duplicate_results):
        return 1

    return 0


if __name__ == "__main__":
    # Example usage
    import sys

    class Args:
        target = sys.argv[1] if len(sys.argv) > 1 else "."
        glob = "*.jsonl"
        show = True
        detect_duplicates = True

    exit_code = cmd_scan_with_duplicates(Args())
    sys.exit(exit_code)
