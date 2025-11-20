# XDG Base Directory Specification - Onboarding Guide

## Welcome to Riff: Your First Step Toward NabiOS Architecture

When you first run `riff`, if the configuration file doesn't exist, Riff automatically creates one with an educational TOML template. This guide explains why Riff is designed this way and what you're learning by using it.

---

## Table of Contents

1. [The Problem Riff Solves](#the-problem-riff-solves)
2. [XDG Base Directory Specification Explained](#xdg-base-directory-specification-explained)
3. [How Riff Uses XDG](#how-riff-uses-xdg)
4. [Directory Structure Tour](#directory-structure-tour)
5. [Configuration and Customization](#configuration-and-customization)
6. [Backups and Data Safety](#backups-and-data-safety)
7. [Why This Matters for NabiOS](#why-this-matters-for-nabitech)
8. [Common Questions](#common-questions)

---

## The Problem Riff Solves

Before XDG, applications scattered files everywhere:

```
~/.claude/                    # Tool 1
~/.riff/                      # Tool 2
~/.searcher/                  # Tool 3
~/.embeddings/                # Tool 4
~/.cache/riff/                # Temp files, but where?
~/.local/share/claude-manager/ # Long-term data (but inconsistent naming)
```

**The chaos:**
- Where do I backup?
- Where can I safely delete temporary files?
- How do I sync configurations across machines?
- Which directories are permanent vs. temporary?

**The solution:** XDG Base Directory Specification - a Linux/macOS/Unix standard that says:

> "There SHALL be a single base directory relative to which user-specific configuration files should be stored. If [$XDG_CONFIG_HOME](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) is either not set or empty, a default equal to [$HOME](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap08.html#tag_08_21)/.config should be used."

---

## XDG Base Directory Specification Explained

XDG defines **four directory types**, each with a specific purpose:

### 1. `~/.config/` - Configuration Files

**Purpose:** Application settings, preferences, credentials (non-secrets)

**Characteristics:**
- Human-readable (TOML, JSON, YAML, INI)
- Portable across machines (safe to sync)
- Never contains large binary data
- User should be able to edit files here directly

**Example Riff files:**
- `~/.config/nabi/riff.toml` - Your Riff configuration

### 2. `~/.local/share/` - Application Data

**Purpose:** Long-term data created or modified by the application

**Characteristics:**
- Includes: databases, embeddings, indexes, conversation backups
- Can be binary or text
- Safe to backup (these are your valuable files)
- Should survive application updates
- Part of your regular backup strategy

**Example Riff files:**
- `~/.local/share/nabi/riff/embeddings/` - Semantic search indexes
- `~/.local/share/nabi/riff/backups/` - Conversation backups before fixes

### 3. `~/.local/state/` - Runtime State

**Purpose:** Ephemeral state that survives reboots but can be deleted

**Characteristics:**
- Not backed up regularly (can be regenerated)
- Can be cleared without data loss
- Includes: logs, temporary indexes, runtime caches
- Enables hot-reload coordination between tools

**Example Riff files:**
- `~/.local/state/nabi/riff/backups-index.json` - Hot-reloadable backup manifest
- `~/.local/state/nabi/riff/search-index/` - Temporary search indexes

### 4. `~/.cache/` - Temporary Cache

**Purpose:** Temporary files that can be deleted without harm

**Characteristics:**
- Never contains irreplaceable data
- Deleted when space is needed
- Can be on fast SSD or ramdisk
- Safe to exclude from backups

**Example Riff files:**
- `~/.cache/nabi/riff/` - Temporary working files, search results

---

## How Riff Uses XDG

Riff demonstrates the XDG pattern by using all four directory types:

```
~/.config/nabi/riff.toml           # Configuration: where to find things
    ├─ [paths]
    │  ├─ conversations = "~/.claude/projects"    # Where your data lives
    │  ├─ embeddings = "~/.local/share/nabi/riff/embeddings"
    │  ├─ backups = "~/.local/share/nabi/riff/backups"
    │  ├─ cache = "~/.cache/nabi/riff"
    │  └─ state = "~/.local/state/nabi/riff"
    └─ [features], [models], etc.

~/.local/share/nabi/riff/          # Data: what you create
    ├─ embeddings/                   # Semantic indexes (important!)
    ├─ backups/                      # Backed-up conversations
    │  ├─ 20251110T143022-d58b28a9-fix.jsonl
    │  ├─ 20251110T152015-7b332eb8-fix.jsonl
    │  └─ ...
    └─ ...

~/.local/state/nabi/riff/          # State: runtime coordination
    ├─ backups-index.json            # Hot-reloadable metadata
    ├─ search-index/                 # Temporary indexes
    └─ logs/

~/.cache/nabi/riff/                # Cache: temporary only
    ├─ search_xyz123.jsonl           # Temp file
    └─ ...
```

---

## Directory Structure Tour

When Riff runs for the first time, it:

1. **Detects** that `~/.config/nabi/riff.toml` doesn't exist
2. **Creates** the configuration file with educational comments
3. **Ensures** all XDG directories exist:
   - `~/.config/nabi/` (config)
   - `~/.local/share/nabi/riff/` (data)
   - `~/.local/state/nabi/riff/` (state)
   - `~/.cache/nabi/riff/` (cache)

Example output:
```
[✓] Created XDG configuration at ~/.config/nabi/riff.toml
[✓] Created XDG directories:
    - ~/.local/share/nabi/riff
    - ~/.local/state/nabi/riff
    - ~/.cache/nabi/riff

[💡] Open ~/.config/nabi/riff.toml to understand the XDG architecture
```

---

## Configuration and Customization

Your configuration file is `~/.config/nabi/riff.toml`. It's a TOML file with extensive inline comments explaining each section.

### Why TOML?

- **Human-readable**: Designed for configuration files
- **Comments**: Can explain why each setting exists
- **Structure**: Hierarchical sections like `[paths]`, `[models]`, `[features]`
- **Portable**: Same format on Linux, macOS, Windows

### Customizing Paths

Edit `~/.config/nabi/riff.toml` to customize where Riff stores data:

```toml
[paths]
# Change where Riff looks for conversations
conversations = "~/Documents/my-conversations"

# Store embeddings on a fast SSD
embeddings = "/Volumes/fast-ssd/riff-embeddings"

# Use cloud backup for backups
backups = "~/Dropbox/riff-backups"

# Use tmpfs (RAM) for faster caching (risky on low-memory systems)
cache = "/tmp/riff-cache"
```

### Environment Variable Overrides

For temporary overrides without editing the config file:

```bash
# Use a custom conversation directory for one command
RIFF_CONVERSATIONS_DIR=~/temp-convos riff scan .

# Store embeddings elsewhere this time
RIFF_EMBEDDINGS_DIR=/tmp/test-embeddings riff search "topic"

# Available environment variables:
#  - RIFF_CONFIG
#  - RIFF_CONVERSATIONS_DIR
#  - RIFF_EMBEDDINGS_DIR
#  - RIFF_BACKUPS_DIR
#  - RIFF_CACHE_DIR
#  - RIFF_STATE_DIR
```

---

## Backups and Data Safety

Riff automatically creates backups when you use `riff fix --in-place`:

```bash
riff fix --in-place ~/.claude/projects/d58b28a9.jsonl
```

**What happens:**
1. Riff loads your conversation
2. Creates a timestamped backup in `~/.local/share/nabi/riff/backups/`
3. Repairs the conversation in-place
4. Records the backup in `~/.local/state/nabi/riff/backups-index.json`

**Backup filename format:**
```
YYYYMMDDTHHMMSS-{uuid}-{reason}.jsonl
20251110T143022-d58b28a9-5b9f-490b-fix.jsonl
│        │      │       │
│        │      │       └─ reason (fix, scan, manual)
│        │      └─ session UUID (first part of filename)
│        └─ timestamp (YearMonthDayTHourMinuteSecond)
└─ ISO 8601 format for easy sorting
```

**The backup index** (`~/.local/state/nabi/riff/backups-index.json`) is:
- **Hot-reloadable**: Updated immediately after each backup
- **Portable**: JSON format, human-readable
- **Erasable**: Can delete this file, backups remain (just index is lost)

**Restore a backup** (via your own tools or future Riff commands):
```bash
# Backups are just JSONL files, you can copy them manually
cp ~/.local/share/nabi/riff/backups/20251110T143022-d58b28a9-fix.jsonl \
   ~/.claude/projects/d58b28a9.jsonl
```

---

## Why This Matters for NabiOS

Riff is designed as the **first tool** you interact with when learning NabiOS. Here's why XDG matters:

### 1. **Unified Ecosystem**

All NabiOS tools use the same pattern:

```
~/.config/nabi/
├─ riff.toml
├─ claude-manager.toml
├─ memchain.toml
├─ searcher.toml
└─ ... (50+ tools)

~/.local/share/nabi/
├─ riff/
├─ claude-manager/
├─ memchain/
└─ ... (all tool data)
```

Once you understand Riff's structure, you understand **all NabiOS tools**.

### 2. **Portable Configurations**

Move your config directory between machines:

```bash
# Backup only config
tar czf nabi-config.tar.gz ~/.config/nabi/

# Transfer to new machine
scp nabi-config.tar.gz newmachine:
tar xzf nabi-config.tar.gz -C ~/

# All tools are configured!
```

### 3. **Smart Backup Strategy**

You know exactly what to backup:

```bash
# Backup only application data (not temp files)
rsync -av ~/.local/share/nabi/ /backup/nabi-data/

# Ignore caches safely
rsync -av --exclude=".cache" ~/.local/share/nabi/ /backup/nabi-data/

# Backup configs for portability
rsync -av ~/.config/nabi/ /backup/nabi-config/

# Skip state (regenerated easily)
rsync -av --exclude=".local/state" ~/.local/share/nabi/ /backup/
```

### 4. **Federation Coordination**

The `~/.local/state/` directory enables multiple tools to coordinate without restarting:

```
~/.local/state/nabi/
├─ riff/
│  └─ backups-index.json      # Riff publishes backup events
├─ memchain/
│  └─ coordination/           # Memchain reads/writes coordination
├─ message-bus.sock           # Tools coordinate via sockets
└─ ...
```

Tools can:
- Read fresh state without restarting
- Publish events others subscribe to
- Coordinate work across the federation

### 5. **Educational Progression**

As you master Riff, you're ready for:

**Stage 1 (Now):** Riff CLI - single tool, XDG pattern
```bash
riff scan ~/.claude
riff fix --in-place conversation.jsonl
```

**Stage 2:** NabiOS Federation - multiple tools
```bash
nabi list                    # See all available tools
nabi exec {tool-name}        # Run any tool with unified config
```

**Stage 3:** Advanced Coordination
```bash
nabi watch --federation      # Monitor federation state
nabi analyze repo            # Cross-project dependency analysis
```

Each stage builds on the previous one, and **Riff teaches the foundation**.

---

## Common Questions

### Q: Why not just use `~/.riff/` like my other tools?

**A:** XDG enables:
- **Consistency**: All tools follow same pattern → easier to manage
- **Backup strategy**: Know what to backup (`~/.local/share/nabi/`)
- **Portability**: Move configs to new machines easily
- **Federation**: Tools coordinate via `~/.local/state/`

### Q: Can I use different paths?

**A:** Yes! Edit `~/.config/nabi/riff.toml` to customize. Riff is portable within your customization:

```toml
[paths]
conversations = "/external/drive/conversations"  # Use external drive
embeddings = "/fast-ssd/embeddings"             # Fast SSD for indexes
backups = "~/Dropbox/backups"                   # Cloud sync for safety
```

Or use environment variables:

```bash
RIFF_CONVERSATIONS_DIR=~/temp riff scan .
```

### Q: What if I delete ~/.cache/nabi/riff?

**A:** Safe to delete. Riff will recreate as needed:
- Temporary files will be regenerated
- Long-term data is in `~/.local/share/nabi/riff/`
- You might need to re-index embeddings (slow)

### Q: What if I delete ~/.local/state/nabi/riff?

**A:** Safe to delete. State will be regenerated:
- Backup index will be rebuilt from files
- Search indexes will be recreated
- No permanent data loss
- Riff will run slower until re-indexed

### Q: How do I share backups with others?

**A:** They're just JSONL files:

```bash
# Copy a backup
cp ~/.local/share/nabi/riff/backups/20251110T143022-d58b28a9-fix.jsonl \
   ~/Downloads/d58b28a9-FIXED.jsonl

# Share via email, git, etc.
# Others can import and analyze
```

### Q: Can I version control my config?

**A:** Yes!

```bash
cd ~/.config/nabi
git init
git add riff.toml
git commit -m "Initial Riff configuration"

# Now track changes
vim riff.toml   # Make changes
git diff        # See what changed
git commit -am "Updated embeddings location"
```

### Q: How is this different from just using ~/.claude/projects?

**A:** Let's compare workflows:

**Old approach (monolithic):**
```
~/.claude/projects/           # Conversations live here
~/.cache/riff/                # But where are temp files?
/somewhere/embeddings/        # Where are embeddings?
~/.claude/backups/            # Is this being backed up?
~/.riff/config.toml          # Where's the config?

Backup strategy: "Hope it's in the right place"
Portability: "How do I move this to a new machine?"
```

**Riff approach (XDG-compliant):**
```
~/.claude/projects/           # Conversations (external, unchanged)
~/.config/nabi/riff.toml      # Configuration (portable!)
~/.local/share/nabi/riff/     # Data (backup this directory)
~/.local/state/nabi/riff/     # State (can be regenerated)
~/.cache/nabi/riff/           # Cache (safe to delete)

Backup strategy: "Back up ~/.local/share/nabi/"
Portability: "Sync ~/.config/nabi/ to new machine"
Federation: "Multiple tools coordinate via ~/.local/state/"
```

---

## Next Steps

1. **Explore your configuration:**
   ```bash
   cat ~/.config/nabi/riff.toml
   ```

2. **Understand your directory structure:**
   ```bash
   ls -la ~/.config/nabi/
   ls -la ~/.local/share/nabi/riff/
   ls -la ~/.cache/nabi/riff/
   ```

3. **Try backing up a conversation:**
   ```bash
   riff fix --in-place ~/.claude/projects/some-conversation.jsonl
   ls -la ~/.local/share/nabi/riff/backups/
   ```

4. **Learn about the backup index:**
   ```bash
   cat ~/.local/state/nabi/riff/backups-index.json
   ```

5. **Customize your paths** (optional):
   ```bash
   vim ~/.config/nabi/riff.toml
   # Change [paths] section as desired
   ```

6. **Prepare for NabiOS:**
   - Now that you understand XDG via Riff, explore other tools
   - They all use the same pattern
   - You're learning the foundation of the entire ecosystem

---

## Related Documentation

- [Riff README](../README.md) - Tool usage guide
- [Riff Architecture](./ARCHITECTURE.md) - Internal design
- [NabiOS Federation Docs](https://docs.nabia.dev/) - Full ecosystem

---

**Remember:** Riff isn't just a tool. It's your gateway to understanding why NabiOS is architected the way it is. Every time you use it, you're learning a pattern that scales to dozens of coordinated tools.

Welcome to the future of portable, coordinated software. 🚀
