# Riff CLI

A Nushell-based command-line tool for extracting and searching UUIDs from JSONL files with fuzzy search integration.

## Features

- **UUID Extraction**: Extract UUIDs from JSONL files efficiently
- **Fuzzy Search**: Interactive search using `fzf` for quick UUID selection
- **Multiple Formats**: Support for interactive, JSON, and UUID-only outputs
- **Content Search**: Filter entries by search terms within the content
- **Progress Indicators**: Visual progress for large file processing
- **Performance Optimized**: Configurable limits and streaming for large datasets

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd riff-cli

# Run the installation script
./install/install.sh
```

### Basic Usage

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

## Requirements

- [Nushell](https://www.nushell.sh/) - Modern shell with structured data support
- [fzf](https://github.com/junegunn/fzf) - Fuzzy finder for interactive selection

## Variants

- **riff**: Main implementation with full features
- **riff-enhanced**: Enhanced version with progress indicators
- **riff-simple**: Minimal version for testing and debugging

## Documentation

- [Usage Guide](docs/usage.md) - Comprehensive usage examples
- [Development](docs/development.md) - Development setup and contributing

## Project Structure

```
riff-cli/
├── README.md              # This file
├── src/                   # Source code
│   ├── riff.nu           # Main CLI implementation
│   ├── riff-enhanced.nu  # Enhanced version with progress
│   └── riff-simple.nu    # Simple test version
├── install/               # Installation scripts
│   ├── install.sh        # Main installation script
│   ├── zsh-aliases.sh    # Shell integration aliases
│   └── uninstall.sh      # Clean removal script
├── docs/                  # Documentation
└── tests/                 # Test files and examples
    └── sample-data/       # Sample JSONL files
```

## License

This project is part of the Nabia ecosystem and follows its licensing terms.