# Riff CLI v2.0 - Teaching-First NabiOS Onboarding Tool

**Your gateway to the XDG Base Directory Specification + Unified Claude conversation search + JSONL repair toolkit**

Riff is more than a tool—it's your **first step into NabiOS architecture**. Run it on any clean system, and it automatically teaches you why portable software requires the XDG Base Directory Specification. Search through your Claude conversations and **see the actual text snippets** you're looking for—not just file paths. Built with Python 3.13+, powered by Qdrant semantic search, with enterprise-grade architecture.

> **Status**: ✅ v2.0 Release Ready | XDG Architecture Complete | Single-Binary Ready | Teaching-First Design
>
> **New in v2.0**: Automatic XDG configuration + Backup system + Duplicate detection + Educational TOML + Ready for binary distribution

## 🏗️ v2.0 Architectural Innovations

### XDG Base Directory Specification (Teaching-First Design)
- **Auto-Configuration**: Config file automatically created on first run with 200-line educational TOML
- **Portable Paths**: Separates configuration, data, state, and cache into standard XDG directories
  - `~/.config/nabi/riff.toml` - Configuration (portable)
  - `~/.local/share/nabi/riff/` - Application data (backup this)
  - `~/.local/state/nabi/riff/` - Runtime state (ephemeral)
  - `~/.cache/nabi/riff/` - Temporary cache (deletable)
- **Educational Comments**: TOML explains why XDG matters and prepares you for NabiOS
- **No Pre-Configuration Required**: Works on clean systems immediately

### Safe Backup System
- **Automatic Backups**: Creates timestamped backups before modifying conversations
- **Hot-Reload Index**: Backup manifest in state directory updates immediately
- **Data Safety**: Prevents accidental data loss during repairs
- **Easy Restore**: Backups are standard JSONL files, restoreable manually

### Duplicate Detection & Removal (NEW)
- **Session Resume Corruption Fix**: Identifies and removes duplicate tool_result blocks
- **Safe Deduplication**: Keeps first occurrence, removes duplicates
- **Rich Output**: Visual tables showing issues and fixes

## ✨ Core Features

### Semantic Search with Content Preview
- **See What You Search For**: Actual conversation snippets in results (not just paths)
- **Semantic Search**: Find conversations by meaning, not just keywords
- **AI Enhancement**: Optional intent-driven query expansion
- **Direct UUID Lookup**: Quick access by session ID
- **Rich Preview**: Color-formatted content in terminal

### Original TUI Commands
- **Scan**: Find issues in JSONL files (now includes duplicate detection)
- **Fix**: Repair conversations with automatic backup
- **TUI**: Interactive file browser with vim-style navigation
- **Graph**: Generate conversation graphs (Mermaid/DOT format)

## 🚀 Quick Start

### 1. Setup (30 seconds)

```bash
cd /Users/tryk/nabia/tools/riff-cli

# Setup development environment
task dev:setup

# Start Qdrant (for search)
task docker:up
```

### 2. Search Your Conversations

```bash
# Semantic search with content snippets
task search -- "memory architecture"

# Or use directly
uv run riff search "federation patterns"

# UUID lookup
uv run riff search --uuid abc-123

# AI-enhanced search
uv run riff search --ai "your query"
```

### 3. Repair JSONL Files

```bash
# Scan for issues
task scan -- ~/claude/sessions/

# Fix broken JSONL
task fix -- session.jsonl

# Interactive TUI
uv run riff tui ~/claude/
```

### All Available Commands

```bash
task --list
```

### Federation Integration

```bash
# Register with Nabi CLI
task nabi:register

# Then use from anywhere
nabi exec riff search "query"
```

## 📋 Requirements

- **Python 3.13+**
- **uv** - Package manager ([install](https://docs.astral.sh/uv/))
- **task** - Task automation ([install](https://taskfile.dev/))
- **Docker** - For Qdrant (optional, but recommended)

All Python dependencies are managed via `pyproject.toml`

## 🏗️ Project Structure

```
riff-cli/
├── src/riff/              # Python package
│   ├── cli.py            # Entry point
│   ├── search/           # Qdrant semantic search
│   ├── enhance/          # AI query enhancement
│   ├── classic/          # Original commands (scan, fix, tui, graph)
│   └── tui/              # Interactive TUI (Week 2)
├── tests/                # Test suite
├── infrastructure/       # Docker & Qdrant config
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # System design
│   └── DEVELOPMENT.md    # Dev guide
├── Taskfile.yml          # Task automation
└── pyproject.toml        # uv project config
```

**Clean root directory** (enterprise standard):
- Only essential configs and documentation at root
- Legacy files moved to `archive/`
- Infrastructure organized in `infrastructure/`

## 🚀 Installation & Setup

### Tab Completion (Bash & Zsh)

Tab completion provides context-aware suggestions for commands, flags, and files.

#### Bash Setup

Add this line to your `~/.bashrc`:

```bash
source /path/to/riff-cli/src/riff/completion.sh
```

Then reload your shell:

```bash
source ~/.bashrc
```

Or start a new terminal session.

#### Zsh Setup

Add this line to your `~/.zshrc`:

```bash
source /path/to/riff-cli/src/riff/completion.sh
```

Then reload your shell:

```bash
source ~/.zshrc
```

Or start a new terminal session.

#### Homebrew / System-Wide Installation

If installing riff-cli via Homebrew or system package manager, the completion script will be automatically placed in the correct directory:

**Bash (macOS/Linux):**
```bash
cp src/riff/completion.sh /usr/local/etc/bash_completion.d/riff
# Or for Homebrew-managed completion:
cp src/riff/completion.sh $(brew --prefix)/etc/bash_completion.d/riff
```

**Zsh (macOS/Linux):**
```bash
cp src/riff/completion.sh /usr/local/share/zsh/site-functions/_riff
# Or for Homebrew-managed completion:
cp src/riff/completion.sh $(brew --prefix)/share/zsh/site-functions/_riff
```

### Usage Examples

After sourcing the completion script, you'll have tab completion for:

**Commands:**
```bash
riff [TAB][TAB]              # Shows all commands
riff sca[TAB]                # Completes to "scan"
riff sear[TAB]               # Completes to "search"
riff gra[TAB]                # Completes to "graph"
```

**Flags:**
```bash
riff search --[TAB]          # Shows: --limit, --min-score, --uuid, --ai, etc.
riff scan --[TAB]            # Shows: --glob, --show
riff fix --[TAB]             # Shows: --in-place
riff graph --[TAB]           # Shows: --interactive, --surrealdb-url
```

**File Paths:**
```bash
riff scan ~/claude/[TAB]     # Auto-completes directory paths
riff fix /path/to/[TAB]      # Auto-completes .jsonl files
riff visualize session.[TAB] # Auto-completes .jsonl files
```

**Format Options:**
```bash
riff graph-classic file.jsonl --format [TAB]  # Shows: dot, mermaid
```

## 📚 Documentation

### Getting Started
- **[QUICK_START.md](docs/QUICK_START.md)** - 5-minute setup guide
- **[XDG_ONBOARDING_GUIDE.md](docs/XDG_ONBOARDING_GUIDE.md)** - Understanding XDG architecture (4,500 words)
- **[INSTALLATION.md](docs/INSTALLATION.md)** - Installation methods and troubleshooting (Coming v2.1)

### Development & Architecture
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and decisions
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Setup and contribution guide
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[RELEASE_INSTRUCTIONS.md](RELEASE_INSTRUCTIONS.md)** - Binary release guide

### Reference
- **Backup System**: Implementation in `src/riff/backup.py`
- **Configuration System**: XDG-compliant in `src/riff/config.py`
- **Duplicate Detection**: Detection/removal in `src/riff/classic/commands/scan.py` and `fix.py`

## 🗓️ Release Roadmap

### ✅ v2.0.0 - Released Now
- ✅ XDG Base Directory Specification implementation
- ✅ Automatic configuration with educational TOML
- ✅ Safe backup system with hot-reload index
- ✅ Duplicate tool_result detection and removal
- ✅ Production-ready for single-binary distribution
- ✅ Comprehensive documentation

### 🚀 v2.1.0 (Next - Week 2)
- Single-binary distribution (PyInstaller)
- GitHub Actions CI/CD for multi-platform builds
- Homebrew formula and tap
- Pre-built binaries on GitHub Releases

### 📅 v2.2.0+ (Future)
- Windows .exe support with code signing
- Docker image distribution
- Conda package
- Auto-update mechanism
- Windows terminal optimization

## License

This project is part of the Nabia ecosystem and follows its licensing terms.