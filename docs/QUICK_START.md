# Riff CLI - Quick Start Guide

Get up and running with Riff in 5 minutes.

## Installation

### From Source
```bash
git clone https://github.com/NabiaTech/riff-cli.git
cd riff-cli
pip install -e .
```

### From Homebrew (Coming Soon)
```bash
brew install riff-cli
```

### From Binary (Coming Soon)
Download from [GitHub Releases](https://github.com/NabiaTech/riff-cli/releases)

---

## First Run: Automatic Setup

```bash
riff scan ~/.claude
```

**First time?** Riff automatically creates XDG directories and configuration:

```
[✓] Created XDG configuration at ~/.config/nabi/riff.toml
[✓] Created XDG directories:
    - ~/.local/share/nabi/riff
    - ~/.local/state/nabi/riff
    - ~/.cache/nabi/riff

[💡] Open ~/.config/nabi/riff.toml to understand the XDG architecture
```

---

## Basic Commands

### Scan for Issues
```bash
# Scan a specific file
riff scan ~/.claude/projects/conversation.jsonl

# Scan an entire directory
riff scan ~/.claude/projects/

# Show details of issues found
riff scan ~/.claude/projects/ --show
```

**What it checks:**
- ✓ Missing tool_result blocks (conversation corruption)
- ✓ Duplicate tool_result IDs (session resume bugs)
- ✓ Malformed JSONL entries

### Fix Conversations
```bash
# Create a repaired copy (non-destructive)
riff fix ~/.claude/projects/conversation.jsonl

# Repair in-place with backup
# (creates timestamped backup automatically)
riff fix --in-place ~/.claude/projects/conversation.jsonl

# Check the backup
cat ~/.local/share/nabi/riff/backups/20251110T143022-*.jsonl
```

### Visualize Conversation DAG
```bash
riff visualize ~/.claude/projects/conversation.jsonl

# This opens an interactive DAG viewer showing message flow
```

---

## Understanding Your Configuration

After first run, read your auto-created config:

```bash
cat ~/.config/nabi/riff.toml
```

Key sections:

```toml
[paths]
# Where Riff finds your conversations
conversations = "~/.claude/projects"

# Where Riff stores semantic indexes
embeddings = "~/.local/share/nabi/riff/embeddings"

# Where backups are stored
backups = "~/.local/share/nabi/riff/backups"

# Where temporary files go
cache = "~/.cache/nabi/riff"

# Where runtime state is stored
state = "~/.local/state/nabi/riff"
```

**Want to customize?** Edit the TOML file:

```bash
vim ~/.config/nabi/riff.toml
```

---

## Common Tasks

### Fix a Broken Conversation
```bash
# Identify issues
riff scan conversation.jsonl --show

# Back up and fix
riff fix --in-place conversation.jsonl

# Verify it's fixed
riff scan conversation.jsonl
```

### Restore from Backup
```bash
# List available backups
ls ~/.local/share/nabi/riff/backups/

# Restore manually (they're just JSONL files)
cp ~/.local/share/nabi/riff/backups/20251110T143022-*.jsonl \
   ~/.claude/projects/conversation.jsonl
```

### Check Your Directory Structure
```bash
# Show XDG directories
ls -la ~/.config/nabi/               # Configuration
ls -la ~/.local/share/nabi/riff/    # Data
ls -la ~/.local/state/nabi/riff/    # State
ls -la ~/.cache/nabi/riff/          # Cache
```

---

## Environment Variables

Override config file settings with environment variables:

```bash
# Use a different conversation directory
RIFF_CONVERSATIONS_DIR=~/my-conversations riff scan .

# Store embeddings elsewhere
RIFF_EMBEDDINGS_DIR=/fast-ssd/embeddings riff search "topic"

# Use custom config file
RIFF_CONFIG=~/my-riff-config.toml riff scan .
```

**Available variables:**
- `RIFF_CONFIG` - Custom config file path
- `RIFF_CONVERSATIONS_DIR` - Where to find conversations
- `RIFF_EMBEDDINGS_DIR` - Where to store embeddings
- `RIFF_BACKUPS_DIR` - Where to store backups
- `RIFF_CACHE_DIR` - Where to store temporary files
- `RIFF_STATE_DIR` - Where to store runtime state

---

## Semantic Search (Optional)

Requires Qdrant vector database.

### Setup Qdrant
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Search Conversations
```bash
# Search by semantic meaning
riff search "how to configure authentication?"

# Visualize results in DAG format
riff search "oauth implementation" --visualize
```

---

## Troubleshooting

### Permission Error: `Cannot create config`
```bash
# Ensure XDG directories are writable
mkdir -p ~/.config/nabi ~/.local/share/nabi ~/.local/state/nabi ~/.cache/nabi
chmod 755 ~/.config/nabi ~/.local/share/nabi ~/.local/state/nabi ~/.cache/nabi
```

### "File not found" for conversations
```bash
# Verify your conversations path in config
cat ~/.config/nabi/riff.toml | grep conversations

# Check if path exists
ls -la ~/.claude/projects/
```

### Duplicate tool_results error
```bash
# Riff handles this automatically
# But you can inspect what it found
riff scan conversation.jsonl --show
```

### Search returns no results
```bash
# Embeddings not indexed yet
# Run search to trigger indexing (may take time)
riff search "your query"

# Check if Qdrant is running
curl http://localhost:6333/health
```

---

## Learning More

### Understand XDG Architecture
```bash
cat docs/XDG_ONBOARDING_GUIDE.md
```

This comprehensive guide explains:
- What XDG is and why it matters
- How Riff uses all 4 directory types
- Why this prepares you for NabiOS

### Explore Command Help
```bash
riff --help              # Main help
riff scan --help         # Scan command options
riff fix --help          # Fix command options
riff search --help       # Search command options
```

### Check GitHub
[github.com/NabiaTech/riff-cli](https://github.com/NabiaTech/riff-cli)
- Issues and discussions
- Documentation
- Examples

---

## Next Steps

1. **Run your first scan**: `riff scan ~/.claude`
2. **Read the config**: `cat ~/.config/nabi/riff.toml`
3. **Fix a conversation**: `riff fix --in-place conversation.jsonl`
4. **Learn XDG**: `cat docs/XDG_ONBOARDING_GUIDE.md`
5. **Explore NabiOS**: Ready to learn about the broader federation!

---

## Get Help

- **Questions?** Check: GitHub Discussions
- **Bug Report?** Open: GitHub Issue
- **Want to Contribute?** See: CONTRIBUTING.md

---

**Happy conversation analyzing! 🚀**
