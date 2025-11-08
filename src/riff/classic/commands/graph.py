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
    path = Path(args.path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {path}[/red]")
        return 1
    
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


