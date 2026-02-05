from __future__ import annotations

from pathlib import Path
from rich.console import Console
from ..utils import load_jsonl_safe, get_message_role


console = Console()


def build_mermaid(lines: list[dict]) -> str:
    out = ["graph TD"]
    prev_id = None
    for i, msg in enumerate(lines):
        node_id = f"n{i}"
        role = get_message_role(msg) or "unknown"
        label = role
        if role == "assistant":
            label = "assistant"
        elif role == "user":
            label = "user"
        out.append(f"    {node_id}[\"{i}: {label}\"]")
        if prev_id is not None:
            out.append(f"    {prev_id} --> {node_id}")
        prev_id = node_id
    return "\n".join(out)


def build_dot(lines: list[dict]) -> str:
    out = ["digraph G {"]
    prev_id = None
    for i, msg in enumerate(lines):
        node_id = f"n{i}"
        role = get_message_role(msg) or "unknown"
        color = "lightblue" if role == "assistant" else "lightgreen" if role == "user" else "white"
        out.append(f"  {node_id} [label=\"{i}: {role}\", style=filled, fillcolor=\"{color}\"];")
        if prev_id is not None:
            out.append(f"  {prev_id} -> {node_id};")
        prev_id = node_id
    out.append("}")
    return "\n".join(out)


def cmd_graph(args) -> int:
    # Import resolver functions
    try:
        from ...resolver import resolve_session_path, is_uuid, is_partial_uuid
    except ImportError:
        # Fallback if resolver not available
        def resolve_session_path(s):
            p = Path(s)
            return p if p.exists() else None
        def is_uuid(s):
            return False
        def is_partial_uuid(s):
            return False

    # Try to resolve UUID or path
    path_input = args.path
    resolved_path = resolve_session_path(path_input)

    if not resolved_path:
        console.print(f"[red]Error: Session not found: {path_input}[/red]")
        if is_uuid(path_input) or is_partial_uuid(path_input):
            console.print("[dim]UUID could not be resolved to a session file.[/dim]")
            console.print("[dim]Tip: Use 'riff search' to find available sessions.[/dim]")
        else:
            console.print(f"[dim]File not found: {Path(path_input)}[/dim]")
        return 1

    path = resolved_path
    if is_uuid(path_input) or is_partial_uuid(path_input):
        console.print(f"[dim]Resolved UUID to: {path}[/dim]")

    lines = load_jsonl_safe(path)
    if not lines:
        console.print(f"[yellow]Warning: No valid JSON lines found in {path}[/yellow]")
        return 1

    if args.format == "dot":
        graph = build_dot(lines)
    else:
        graph = build_mermaid(lines)

    if args.out:
        Path(args.out).write_text(graph, encoding="utf-8")
        console.print(f"[green]Wrote {args.out}[/green]")
    else:
        console.print(graph)
    return 0


