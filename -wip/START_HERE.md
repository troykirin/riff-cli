# Riff CLI Exploration: START HERE

Welcome! You've just received a complete technical exploration of the Riff CLI Python backend.

---

## 🎯 What You Have

Three comprehensive documents have been created to help you understand Riff:

### 1. **EXPLORATION_INDEX.md** ← START HERE FIRST
**Your navigation guide (10KB)**

- What this exploration covers
- Quick 5-minute summary
- Navigation guide ("I want to understand X...")
- Reading order recommendations
- Key file locations (all absolute paths)
- Important insights and lessons learned

**Time commitment**: 5-10 minutes

---

### 2. **EXPLORATION_REPORT.md** ← FOR DEEP UNDERSTANDING
**Comprehensive technical reference (17KB, 636 lines)**

Everything you need to know about Riff's architecture:

- CLI entry point hierarchy
- All 12+ available commands with examples
- Complete module structure (13 core modules)
- Data models (Message, Thread, Session)
- IPC/handoff mechanisms (federation pattern)
- Environment variables & configuration
- Three-tier persistence architecture (JSONL → SurrealDB → Qdrant)
- Federation integration pattern
- How Rust CLI would call Python (recommended pattern)
- Technology stack
- Architecture diagrams
- Future extensibility points

**Time commitment**: 30-60 minutes

---

### 3. **QUICK_REFERENCE.md** ← FOR QUICK LOOKUPS
**One-page cheat sheet (4.2KB)**

Copy-paste ready:

- Quick commands
- Module organization table
- Configuration summary
- Database tiers
- File paths (absolute)
- Health check commands
- Common patterns

**Time commitment**: Quick reference (keep open while coding)

---

## 🚀 Quick Start (5 Minutes)

```bash
# Go to riff-cli directory
cd /Users/tryk/nabia/tools/riff-cli

# Set up environment (loads all configs)
direnv allow

# See what riff can do
riff --help

# Test search
riff search "test"

# Check health
source .hookrc
python -c "from riff.search import QdrantSearcher; print('OK' if QdrantSearcher().is_available() else 'FAIL')"
```

---

## 📚 Recommended Reading Path

### Level 1: Quick Overview (10 min)
1. This file (START_HERE.md)
2. EXPLORATION_INDEX.md § "The 5-Minute Summary"
3. QUICK_REFERENCE.md

### Level 2: Understand Architecture (30 min)
1. EXPLORATION_REPORT.md § 1-3 (Entry points, commands, modules)
2. EXPLORATION_REPORT.md § 11 (Architecture diagrams)
3. View: `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py` (actual code)

### Level 3: Deep Dive (1 hour)
1. EXPLORATION_REPORT.md § 4-8 (IPC, config, databases)
2. Read: `src/riff/search/qdrant.py` (search backend)
3. Read: `src/riff/surrealdb/storage.py` (database integration)
4. Read: `docs/ARCHITECTURE.md` (design decisions)

### Level 4: Extend Riff (2+ hours)
1. EXPLORATION_REPORT.md § 12 (Extensibility)
2. EXPLORATION_REPORT.md § 6 (Rust integration pattern)
3. Explore: `backends/` module (future hooks)
4. Review: `tests/` directory (how to test)

---

## 🎯 Key Takeaways

### What Is Riff?

A **Python CLI** (v2.0) that searches Claude conversations and repairs JSONL files:

```
Semantic Search → DAG Visualization → SurrealDB Sync → Qdrant Index
```

### How It Works

```
User Input (CLI) → argparse → Command Router (cli.py)
                                    ↓
         ┌──────────────┬──────────────┬──────────────┐
         ↓              ↓              ↓              ↓
      search        sync:surrealdb   graph        classic
      (Qdrant)    (SurrealDB+Events) (DAG+TUI)   (scan/fix/tui)
```

### Key Components

| Component | What It Does | Location |
|-----------|-------------|----------|
| `cli.py` | Command routing | `src/riff/cli.py` |
| `search/` | Qdrant vector search | `src/riff/search/` |
| `graph/` | DAG analysis & models | `src/riff/graph/` |
| `surrealdb/` | Event-sourced storage | `src/riff/surrealdb/` |
| `classic/` | Original JSONL commands | `src/riff/classic/` |
| `enhance/` | AI query enhancement | `src/riff/enhance/` |
| `tui/` | Interactive navigator | `src/riff/tui/` |

### Databases

1. **JSONL** - Source format (Claude exports)
2. **SurrealDB** - Canonical store (immutable events)
3. **Qdrant** - Search index (384-dim vectors)

### Configuration

- **Venv**: `~/.nabi/venvs/riff-cli/`
- **Setup**: `.hookrc` (auto-activated by direnv)
- **XDG Compliant**: Federation-managed paths

---

## 💡 Most Important Things to Know

### 1. No Rust CLI Yet
Riff is **pure Python**. Rust integration planned for Phase 7+.

### 2. Process Isolation Pattern
Federation uses subprocess isolation:
- Tools are independent processes
- Communication via stdout/structured formats
- Registry maps tool names to executables
- Pattern recommendation for any Rust integration

### 3. Command Entry Point
```bash
pyproject.toml: riff = "riff.cli:main"
         ↓
src/riff/cli.py:main()
         ↓
build_parser() → argparse.ArgumentParser
```

### 4. Federation Integration
```bash
~/.nabi/bin/riff → ~/.nabi/venvs/riff-cli/bin/riff
                        ↓
                    Activates venv
                        ↓
                    Calls Python CLI
```

### 5. Three Commands You'll Use
```bash
riff search "query"                    # Find conversations
riff sync:surrealdb <session-id>      # Sync to database
riff graph <session-id>               # Visualize as tree
```

---

## 🔍 Finding Specific Information

**I want to know about...**

- **Commands**: See QUICK_REFERENCE.md or run `riff --help`
- **Module structure**: See EXPLORATION_REPORT.md § 3
- **Search implementation**: See EXPLORATION_REPORT.md § 11 + `search/qdrant.py`
- **SurrealDB integration**: See EXPLORATION_REPORT.md § 7 + `surrealdb/storage.py`
- **Configuration**: See EXPLORATION_REPORT.md § 5 + `.hookrc`
- **How to extend Riff**: See EXPLORATION_REPORT.md § 12
- **How Rust would call it**: See EXPLORATION_REPORT.md § 6
- **File locations**: See EXPLORATION_INDEX.md § "Key File Locations"

---

## 📁 Important File Paths (Absolute)

All absolute paths - copy directly:

```
Entry Point:    /Users/tryk/nabia/tools/riff-cli/src/riff/cli.py
Configuration:  /Users/tryk/nabia/tools/riff-cli/.hookrc
Search Backend: /Users/tryk/nabia/tools/riff-cli/src/riff/search/qdrant.py
Database:       /Users/tryk/nabia/tools/riff-cli/src/riff/surrealdb/storage.py
Models:         /Users/tryk/nabia/tools/riff-cli/src/riff/graph/models.py
Docs:           /Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md
```

---

## ✅ What This Exploration Covers

- ✅ CLI entry points and command structure
- ✅ Module organization (13 core modules)
- ✅ All 12+ available commands
- ✅ Data models (Message, Thread, Session)
- ✅ Communication patterns (federation model)
- ✅ Configuration and environment
- ✅ Three-tier persistence (JSONL → SurrealDB → Qdrant)
- ✅ Federation integration
- ✅ Rust integration pattern (recommended)
- ✅ Future extensibility

---

## 🎓 Next Steps

**Pick your path**:

1. **Quick Learner**: Read EXPLORATION_INDEX.md (5 min)
2. **Full Understanding**: Read EXPLORATION_REPORT.md (30-60 min)
3. **Implementation Ready**: Study EXPLORATION_REPORT.md § 12 + code review (1-2 hours)
4. **Want to Extend**: EXPLORATION_REPORT.md § 6 + § 12 + review tests (2+ hours)

---

## 📞 Document Navigation

| Document | Best For | Time |
|----------|----------|------|
| **START_HERE.md** | Overview & orientation | 5 min |
| **EXPLORATION_INDEX.md** | Navigation & quick reference | 10 min |
| **QUICK_REFERENCE.md** | Cheat sheet during development | 2 min |
| **EXPLORATION_REPORT.md** | Complete technical understanding | 30-60 min |
| **Source Code** | Real implementation details | 1+ hours |

---

## 🚀 You're Ready!

Everything you need to understand Riff is here. Start with **EXPLORATION_INDEX.md**, then dive deeper with **EXPLORATION_REPORT.md** as needed.

Questions? Check the cross-references section in **EXPLORATION_INDEX.md** for related documentation.

---

**Date Created**: 2025-10-23  
**Coverage**: Complete Python backend exploration  
**Status**: Ready to use

Happy exploring!
