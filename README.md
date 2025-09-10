# Riff CLI

A comprehensive toolkit for JSONL file analysis offering both fast UUID extraction and rich interactive fuzzy search capabilities.

## Features

### Nushell Variants (Fast & Lightweight)
- **UUID Extraction**: Lightning-fast UUID extraction from Claude conversation logs
- **Fuzzy Search**: Interactive search using `fzf` for quick UUID selection
- **Multiple Formats**: Support for interactive, JSON, and UUID-only outputs
- **Content Search**: Filter entries by search terms within the content
- **Performance Optimized**: Configurable limits and streaming for large datasets

### Python Interactive (Rich & Visual)
- **Rich Interface**: Syntax-highlighted JSON with smooth scrolling navigation
- **Advanced Fuzzy Search**: Powered by RapidFuzz with context-aware snippets
- **Keyboard Navigation**: Vim-style controls and interactive browsing
- **Full JSON Expansion**: Complete record viewing with proper formatting
- **Modern Python Stack**: Built with Rich, prompt_toolkit, and uv

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd riff-cli

# Install Nushell variants
./install/install.sh

# Install Python interactive (using uv)
cd python && uv sync
```

### Basic Usage

**Nushell Variants (Fast UUID extraction):**
```bash
# Interactive mode with fuzzy search
riff data.jsonl

# Extract UUIDs only
riff-uuid data.jsonl

# JSON output format
riff-json data.jsonl

# Search within content
riff data.jsonl --search "error"
```

**Python Interactive (Rich browsing):**
```bash
# Rich interactive fuzzy search
cd python
uv run python jsonl_tool.py data.jsonl --query "search phrase"

# Navigate with [n]ext, [p]revious, [v]iew full, [q]uit
```

## Requirements

### Nushell Variants
- [Nushell](https://www.nushell.sh/) - Modern shell with structured data support
- [fzf](https://github.com/junegunn/fzf) - Fuzzy finder for interactive selection

### Python Interactive
- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Tool Variants

### Nushell Tools
- **riff**: Main implementation optimized for Claude conversation logs
- **riff-enhanced**: Enhanced version with progress indicators
- **riff-simple**: Minimal version for testing and debugging

### Python Tools
- **riff-interactive**: Rich fuzzy search with visual interface and keyboard navigation

## Documentation

- [Usage Guide](docs/usage.md) - Comprehensive usage examples
- [Development](docs/development.md) - Development setup and contributing

## Project Structure

```
riff-cli/
├── README.md              # This file
├── src/                   # Nushell source code
│   ├── riff.nu           # Main CLI implementation
│   ├── riff-enhanced.nu  # Enhanced version with progress
│   └── riff-simple.nu    # Simple test version
├── python/                # Python interactive tool
│   ├── jsonl_tool.py     # Rich interactive fuzzy search
│   ├── pyproject.toml    # uv project configuration
│   ├── requirements.txt  # pip dependencies
│   ├── README.md         # Python tool documentation
│   └── context.md        # Vision and development context
├── install/               # Installation scripts
│   ├── install.sh        # Nushell tools installation
│   ├── zsh-aliases.sh    # Shell integration aliases
│   └── uninstall.sh      # Clean removal script
├── docs/                  # Documentation
│   ├── usage.md          # Comprehensive usage guide
│   └── development.md    # Development and contributing
└── tests/                 # Test files and examples
    └── sample-data/       # Sample JSONL files
```

## License

This project is part of the Nabia ecosystem and follows its licensing terms.