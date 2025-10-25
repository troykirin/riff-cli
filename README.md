# Riff CLI

> 🎶 Search Claude conversations like a pro

Riff CLI is a powerful command-line tool for searching through Claude conversation exports and JSONL files. Built with Nushell for speed and structured data handling.

## Features

- **Auto-Detection**: Automatically detects Claude export format vs JSONL files
- **Intent-Driven Search**: Optional AI-enhanced keyword expansion for better results
- **Interactive Selection**: Built-in fuzzy finder (fzf) for quick navigation
- **Multiple Output Formats**: JSON, UUID-only, or formatted text
- **Fast & Efficient**: Leverages Nushell's structured data processing
- **Flexible**: Search conversations, projects, users, or raw JSONL files

## Quick Start

```bash
# Install
make install

# Basic search
riff "search term"

# Intent-driven search with keyword expansion
riff "find discussions about AI" --intent

# Search specific path
riff "error" --path ~/claude-exports

# Get UUIDs only
riff "project" --uuid-only
```

## Installation

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for detailed installation instructions.

**Quick install:**
```bash
git clone https://github.com/yourusername/riff-cli.git
cd riff-cli
make install
```

## Usage

See [docs/USAGE.md](docs/USAGE.md) for comprehensive usage examples.

**Basic syntax:**
```bash
riff [SEARCH_TERM] [OPTIONS]

Options:
  -p, --path PATH        Search path (default: ~/.claude/projects)
  -f, --format FORMAT    Format: jsonl, claude, auto (default: auto)
  -i, --intent          Enable intent-driven search
  -r, --recursive NUM   Recursive enhancement depth (1-5, default: 3)
  -n, --no-fzf         Skip fzf and output directly
  -u, --uuid-only      Output only UUIDs
  -j, --json           Output as JSON
  -v, --verbose        Verbose output with debug info
  -l, --limit NUM      Limit results (default: 1000)
  --progress           Show progress indicators
```

## Requirements

**Core:**
- [Nushell](https://www.nushell.sh/) - Modern shell with structured data support

**Optional (recommended):**
- [fzf](https://github.com/junegunn/fzf) - For interactive selection
- Python 3 - For intent-driven search enhancement

## Examples

```bash
# Search conversations about a specific topic
riff "authentication" --intent

# Find all mentions of a project
riff "project-name" --format claude

# Get raw UUIDs for scripting
riff "error" --uuid-only --no-fzf

# Verbose search with progress
riff "debug" --verbose --progress

# Search custom directory
riff "keyword" --path ~/my-exports
```

## Environment Variables

```bash
export RIFF_SEARCH_PATH="$HOME/.claude/projects"  # Default search path
export RIFF_INTENT_SCRIPT="$HOME/.local/lib/riff/intent_enhancer_simple.py"
export RIFF_DEBUG=false  # Enable debug output
```

## Project Structure

```
riff-cli/
├── src/
│   ├── riff.nu                      # Main CLI script
│   ├── lib/                         # Library modules
│   │   └── riff-core.nu            # Core utilities
│   └── intent_enhancer_simple.py   # Optional intent enhancement
├── docs/
│   ├── INSTALLATION.md             # Installation guide
│   └── USAGE.md                    # Usage guide
├── examples/
│   ├── basic-search.sh             # Basic search examples
│   ├── batch-search.sh             # Batch processing
│   └── json-output.sh              # JSON output examples
├── install.sh                      # Installation script
├── Makefile                        # Make targets
└── README.md                       # This file
```

## Advanced Features

### Intent-Driven Search

When enabled with `--intent`, Riff CLI expands your search terms using pattern matching and domain knowledge:

```bash
# Expands "claude" to include: assistant, conversation, chat, ai, llm, dialogue
riff "claude discussions" --intent

# Expands "project" to include: implementation, feature, module, component
riff "project work" --intent
```

### NabiOS Integration (Optional)

Riff CLI can integrate with the [NabiOS](docs/integration/NABIÓS.md) federation ecosystem for advanced features like:
- Cross-agent search coordination
- Persistent memory integration
- Federated knowledge graphs

See [docs/integration/NABIÓS.md](docs/integration/NABIÓS.md) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [Nushell](https://www.nushell.sh/) - Modern shell with structured data
- [fzf](https://github.com/junegunn/fzf) - Command-line fuzzy finder

---

**Note**: This is the standalone open-source version of Riff CLI. For federation features and NabiOS integration, see the integration documentation.
