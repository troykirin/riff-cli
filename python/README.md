# Riff Interactive - Python JSONL Fuzzy Search Tool

A powerful interactive CLI tool for fuzzy searching `.jsonl` files with rich formatting, syntax highlighting, and keyboard-driven navigation.

## Features

- **Rich Interactive Interface**: Syntax-highlighted JSON with smooth scrolling
- **Fuzzy Search**: Powered by RapidFuzz for intelligent content matching
- **Keyboard Navigation**: Arrow keys, vim-style navigation, and shortcuts
- **Context-Aware Snippets**: Smart content extraction around search terms
- **Full JSON Expansion**: View complete records with proper formatting
- **Modern Python Stack**: Built with Rich, prompt_toolkit, and uv

## Installation

Using `uv` (recommended):
```bash
cd python
uv sync
uv run python jsonl_tool.py data.jsonl --query "search phrase"
```

Using pip:
```bash
cd python
pip install -r requirements.txt
python jsonl_tool.py data.jsonl --query "search phrase"
```

## Usage

```bash
# Basic fuzzy search
python jsonl_tool.py data.jsonl --query "search phrase"

# Adjust search sensitivity
python jsonl_tool.py data.jsonl --query "error" --threshold 60

# Interactive browsing with keyboard controls
# [n]ext, [p]revious, [v]iew full, [↑/↓] scroll, [q]uit
```

## Interactive Features

Once you run the tool, you'll enter an interactive browser with these controls:

- **n** - Next match
- **p** - Previous match  
- **v** - View full JSON record with syntax highlighting
- **↑/u** - Scroll up in current snippet
- **↓/d** - Scroll down in current snippet
- **q** - Quit browser
- **Ctrl+C** - Emergency exit

## Development

This tool is part of the larger Riff CLI project that provides multiple approaches to JSONL file analysis:

- **Nushell variants** (`../src/`): Fast UUID extraction for Claude conversation logs
- **Python interactive** (`./`): Rich fuzzy search with visual interface

## Vision: DAW for Dialogue

This tool represents a step toward building a "Digital Audio Workstation for Dialogue" - an interface that doesn't just show your memory but lets you conduct it. The vision includes:

- **Live Interactive Semantic Canvas**: Real-time interaction with conversation flows
- **Advanced Semantic Transformations**: Topic clustering, intent threading, dynamic summarization
- **REPL-like Terminal Interface**: Command palette for memory manipulation
- **Recursive Interpretive Frames**: Layered conversation analysis like instruments in a DAW

Think: Vim meets Ableton meets Claude - where memory traces become musical, interactive, and compositional.

## Future Enhancements

- [ ] Visual wireframe for semantic canvas
- [ ] Structured spec for CLI commands + data flow  
- [ ] Prototype using Tauri or Ink
- [ ] Canvas document mapping memory → interaction primitives