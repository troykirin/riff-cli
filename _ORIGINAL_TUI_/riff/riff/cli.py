import argparse
import sys
from pathlib import Path

from .commands.scan import cmd_scan
from .commands.fix import cmd_fix
from .commands.tui import cmd_tui
from .commands.graph import cmd_graph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="riff", description="Riff JSONL sessions: scan, fix, TUI, graph")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Scan directory or file(s) for JSONL sessions and detect issues")
    p_scan.add_argument("target", nargs="?", default=".", help="Directory or file to scan")
    p_scan.add_argument("--glob", dest="glob", default="**/*.jsonl", help="Glob when target is a directory")
    p_scan.add_argument("--show", dest="show", action="store_true", help="Show offending message indices/ids")
    p_scan.set_defaults(func=cmd_scan)

    p_fix = sub.add_parser("fix", help="Repair missing tool_result after tool_use in JSONL")
    p_fix.add_argument("path", help="JSONL file to repair in-place or write .repaired")
    p_fix.add_argument("--in-place", dest="in_place", action="store_true", help="Write changes back to the same file")
    p_fix.set_defaults(func=cmd_fix)

    p_tui = sub.add_parser("tui", help="Interactive TUI to browse, search, and fix sessions")
    p_tui.add_argument("target", nargs="?", default=".", help="Directory to browse for JSONL files")
    p_tui.add_argument("--glob", dest="glob", default="**/*.jsonl", help="File glob")
    p_tui.add_argument("--fzf", dest="fzf", action="store_true", help="Use fzf for quick pick when available")
    p_tui.set_defaults(func=cmd_tui)

    p_graph = sub.add_parser("graph", help="Generate a conversation graph (DOT/Mermaid)")
    p_graph.add_argument("path", help="JSONL file path")
    p_graph.add_argument("--format", choices=["dot", "mermaid"], default="mermaid")
    p_graph.add_argument("--out", dest="out", help="Output file path (writes to stdout if omitted)")
    p_graph.set_defaults(func=cmd_graph)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())


