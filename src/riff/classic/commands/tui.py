from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import radiolist_dialog

from .fix import repair_stream
from ..utils import load_jsonl_safe


console = Console()


def list_jsonl_files(root: Path, glob: str) -> list[Path]:
    return [p for p in root.rglob(glob) if p.is_file()]


def pick_with_fzf(candidates: list[str]) -> str | None:
    try:
        import subprocess
        proc = subprocess.run(["fzf"], input="\n".join(candidates).encode(), stdout=subprocess.PIPE)
        if proc.returncode == 0:
            return proc.stdout.decode().strip()
    except Exception:
        return None
    return None


def cmd_tui(args) -> int:
    root = Path(args.target)
    files = list_jsonl_files(root, args.glob)
    if not files:
        console.print("[yellow]No JSONL files found.[/yellow]")
        return 1

    choices = [str(p) for p in files]

    selected: str | None = None
    if getattr(args, "fzf", False):
        selected = pick_with_fzf(choices)

    if not selected:
        # Warn if truncating file list
        if len(choices) > 5000:
            console.print(f"[yellow]Warning: Showing first 5000 of {len(choices)} files[/yellow]")
        
        result = radiolist_dialog(
            title="Select JSONL",
            text="Pick a file to inspect/repair",
            values=[(c, c) for c in choices[:5000]],
        ).run()
        selected = result

    if not selected:
        return 0

    path = Path(selected)
    lines = load_jsonl_safe(path)
    
    if not lines:
        console.print(f"[yellow]Warning: No valid JSON lines found in {path}[/yellow]")
        return 1

    from .scan import detect_missing_tool_results
    issues = detect_missing_tool_results(lines)

    table = Table(title=f"Issues in {path.name}")
    table.add_column("Assistant idx")
    table.add_column("Missing IDs")
    for issue in issues:
        table.add_row(str(issue.assistant_index or -1), ", ".join(issue.missing_ids))
    console.print(table)

    if issues:
        do_fix = prompt("Repair now? [y/N]: ")
        if do_fix.lower().startswith("y"):
            fixed = repair_stream(lines)
            out_path = path.with_suffix(path.suffix + ".repaired")
            with out_path.open("w", encoding="utf-8") as f:
                for m in fixed:
                    f.write(json.dumps(m, ensure_ascii=False) + "\n")
            console.print(f"[green]Wrote {out_path}[/green]")

    if lines:
        console.print("\n[bold]Preview:[/bold]")
        for _, msg in zip(range(10), lines):
            text = json.dumps(msg, indent=2, ensure_ascii=False)
            console.print(Syntax(text, "json", theme="monokai", line_numbers=False))
    return 0


