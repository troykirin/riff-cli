"""
Enhanced fix command with duplicate tool_result deduplication.

This module extends the original fix functionality with production-grade
error handling for removing duplicate tool_result blocks from corrupted
conversation data.

Usage:
    python -m riff fix --path <file> --deduplicate --in-place --backup
    python -m riff fix --path <file> --deduplicate --detect-first
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils import (
    load_jsonl_safe,
    get_message_role,
    get_message_content,
    normalize_message_structure,
)
from ..duplicate_handler import (
    detect_duplicate_tool_results,
    apply_deduplication_to_lines,
    log_detection_summary,
    log_deduplication_summary,
    RiffDuplicateDetectionError,
    RiffDeduplicationError,
    DeduplicationResult,
)

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class FixResult:
    """Result of a fix operation."""
    success: bool
    output_path: Path
    missing_tool_results_added: int = 0
    duplicate_tool_results_removed: int = 0
    messages_processed: int = 0
    error: Optional[str] = None
    recovery_suggestions: List[str] = None


def repair_missing_tool_results(lines: list[dict]) -> list[dict]:
    """
    Original repair function for missing tool_results.

    Args:
        lines: List of message dicts

    Returns:
        Repaired list with missing tool_results added
    """
    fixed: list[dict] = []
    pending: list[str] = []

    for msg in lines:
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "assistant":
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id"):
                        pending.append(c["id"])
            fixed.append(msg)
            continue

        if role == "user":
            if pending:
                seen = set()
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


def create_backup(path: Path) -> Optional[Path]:
    """
    Create a backup of the input file.

    Args:
        path: Path to file to backup

    Returns:
        Path to backup file, or None if backup failed
    """
    backup_path = path.with_suffix(path.suffix + ".backup")

    try:
        shutil.copy2(path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        console.print(f"[green]Backup created:[/green] {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {str(e)}")
        console.print(f"[yellow]Warning: Failed to create backup: {str(e)}[/yellow]")
        return None


def cmd_fix_with_deduplication(args) -> int:
    """
    Enhanced fix command entry point with deduplication support.

    Args:
        args: Parsed command arguments with:
            - path: Path to JSONL file to fix
            - in_place: Whether to overwrite original file
            - backup: Whether to create backup before fixing
            - deduplicate: Whether to remove duplicates
            - detect_first: Whether to detect duplicates first
            - repair_missing: Whether to repair missing tool_results (default: True)

    Returns:
        0 on success, 1 on error
    """
    path = Path(args.path)

    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        logger.error(f"File not found: {path}")
        return 1

    logger.info(f"Starting fix operation on {path}")

    try:
        # Load file
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading JSONL file...", total=None)
            lines = load_jsonl_safe(path)
            progress.update(task, completed=True)

        if not lines:
            console.print(f"[yellow]Warning: No valid JSON lines found in {path}[/yellow]")
            logger.warning(f"No valid JSON lines in {path}")
            return 1

        console.print(f"[cyan]Loaded {len(lines)} message(s)[/cyan]")
        logger.info(f"Loaded {len(lines)} lines")

        # Optional: Create backup
        backup_path = None
        if hasattr(args, 'backup') and args.backup:
            backup_path = create_backup(path)

        # Stage 1: Detect duplicates if requested
        duplicates_to_remove = {}
        if hasattr(args, 'deduplicate') and args.deduplicate:
            if hasattr(args, 'detect_first') and args.detect_first:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Detecting duplicate tool_results...", total=None)

                    try:
                        duplicates_to_remove, metrics = detect_duplicate_tool_results(lines)
                        progress.update(task, completed=True)

                        log_detection_summary(metrics)

                        if duplicates_to_remove:
                            console.print(
                                f"\n[yellow]Found {sum(duplicates_to_remove.values())} duplicate "
                                f"tool_result block(s) in {len(duplicates_to_remove)} tool_use_id(s)[/yellow]"
                            )
                        else:
                            console.print("[green]No duplicate tool_results found.[/green]")

                    except RiffDuplicateDetectionError as e:
                        console.print(f"[red]Error detecting duplicates: {str(e)}[/red]")
                        logger.error(f"Duplicate detection error: {str(e)}", exc_info=True)
                        if backup_path:
                            console.print(f"[yellow]Backup preserved at: {backup_path}[/yellow]")
                        return 1

        # Stage 2: Repair missing tool_results if requested
        if hasattr(args, 'repair_missing') and args.repair_missing:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Repairing missing tool_results...", total=None)
                lines = repair_missing_tool_results(lines)
                progress.update(task, completed=True)
            console.print("[green]Missing tool_results repaired[/green]")

        # Stage 3: Deduplicate if requested
        duplicates_removed = 0
        if hasattr(args, 'deduplicate') and args.deduplicate and duplicates_to_remove:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Removing duplicate tool_results...", total=None)

                try:
                    lines = apply_deduplication_to_lines(lines, duplicates_to_remove)
                    duplicates_removed = sum(duplicates_to_remove.values())
                    progress.update(task, completed=True)
                    console.print(f"[green]Removed {duplicates_removed} duplicate block(s)[/green]")

                except RiffDeduplicationError as e:
                    console.print(f"[red]Error during deduplication: {str(e)}[/red]")
                    logger.error(f"Deduplication error: {str(e)}", exc_info=True)

                    # Offer recovery options
                    if backup_path:
                        console.print(f"[yellow]Backup preserved at: {backup_path}[/yellow]")

                    recovery_suggestions = [
                        "Check file integrity with 'jq .' command",
                        f"Review backup at {backup_path}" if backup_path else "Create a backup before retry",
                        "Contact support with file details"
                    ]

                    console.print("[yellow]Recovery suggestions:[/yellow]")
                    for suggestion in recovery_suggestions:
                        console.print(f"  - {suggestion}")

                    return 1

        # Stage 4: Write output
        out_path = path if (hasattr(args, 'in_place') and args.in_place) else path.with_suffix(path.suffix + ".repaired")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Writing output file...", total=None)

            try:
                with out_path.open("w", encoding="utf-8") as f:
                    for m in lines:
                        f.write(json.dumps(m, ensure_ascii=False) + "\n")
                progress.update(task, completed=True)

                console.print(f"[green]Output written to:[/green] {out_path}")
                logger.info(f"Output written to {out_path}")

            except Exception as e:
                console.print(f"[red]Error writing output: {str(e)}[/red]")
                logger.error(f"Error writing output: {str(e)}", exc_info=True)
                return 1

        # Summary
        console.print("\n" + "=" * 60)
        console.print("[bold]FIX SUMMARY[/bold]")
        console.print("=" * 60)
        console.print(f"Messages processed: {len(lines)}")
        if hasattr(args, 'repair_missing') and args.repair_missing:
            console.print(f"Duplicate tool_results removed: {duplicates_removed}")
        console.print(f"Output: {out_path}")

        if backup_path:
            console.print(f"Backup: {backup_path}")

        console.print("=" * 60)

        logger.info(
            f"Fix operation complete: "
            f"{duplicates_removed} duplicates removed, "
            f"output to {out_path}"
        )

        return 0

    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        logger.error(f"Unexpected error during fix: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Example usage
    import sys

    class Args:
        path = sys.argv[1] if len(sys.argv) > 1 else "test.jsonl"
        in_place = False
        backup = True
        deduplicate = True
        detect_first = True
        repair_missing = True

    exit_code = cmd_fix_with_deduplication(Args())
    sys.exit(exit_code)
