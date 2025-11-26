# Riff CLI Exploration: Complete Index

**Date**: 2025-10-23  
**Repository**: /Users/tryk/nabia/tools/riff-cli  
**Scope**: Python backend architecture, CLI structure, and integration mechanisms

---

## 📋 What This Exploration Covers

This is a **complete technical deep-dive** into the Riff CLI Python backend, covering:

1. **CLI Entry Point & Command Structure** - Where commands come in, how they're routed
2. **Module Architecture** - All Python packages and their purposes
3. **Available Commands** - Every command riff supports with examples
4. **Communication & IPC** - How tools interact (No Rust integration yet)
5. **Configuration & Environment** - Environment variables, venv setup, XDG compliance
6. **Database Layer** - Three-tier architecture (JSONL → SurrealDB → Qdrant)
7. **Federation Integration** - How riff integrates with Nabi ecosystem
8. **Data Models** - Core Python dataclasses (Message, Thread, Session)
9. **Future Extensibility** - Planned backends and integration points

---

## 📄 Documentation Files

### New Files Created

#### 1. **EXPLORATION_REPORT.md** (636 lines, 17KB)
**Comprehensive technical reference covering:**
- CLI entry points and command routing
- Complete module structure with directory tree
- All 12 available commands with examples
- Data models and core types
- IPC/handoff mechanisms (federation pattern)
- Environment variables and XDG compliance
- How Rust CLI would call Python (pattern recommendation)
- Three-tier persistence architecture
- Integration points with federation
- Technology stack and dependencies
- Architecture diagrams and data flows
- Future extensibility points

**Best for**: Developers who need complete technical understanding

#### 2. **QUICK_REFERENCE.md** (180 lines, 4.2KB)
**One-page cheat sheet with:**
- Copy-paste ready commands
- Module organization quick table
- Configuration summary
- Database tiers overview
- Federation integration quick steps
- File paths (absolute, ready to copy)
- Health check commands
- Common patterns and examples

**Best for**: Quick lookups during development

---

## 🗂️ Key File Locations (Absolute Paths)

### Entry Points
```
/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py              [600 lines - main command router]
/Users/tryk/nabia/tools/riff-cli/src/riff/__main__.py         [Python -m riff entry]
/Users/tryk/nabia/tools/riff-cli/pyproject.toml               [riff = "riff.cli:main"]
```

### Configuration
```
/Users/tryk/nabia/tools/riff-cli/.hookrc                      [Environment setup, venv activation]
/Users/tryk/nabia/tools/riff-cli/.envrc                       [direnv integration]
/Users/tryk/nabia/tools/riff-cli/.python-version              [3.13 target]
```

### Core Modules
```
/Users/tryk/nabia/tools/riff-cli/src/riff/search/qdrant.py     [QdrantSearcher - vector search]
/Users/tryk/nabia/tools/riff-cli/src/riff/enhance/intent.py    [IntentEnhancer - AI enhancement]
/Users/tryk/nabia/tools/riff-cli/src/riff/graph/models.py      [Message, Thread, Session dataclasses]
/Users/tryk/nabia/tools/riff-cli/src/riff/surrealdb/storage.py [SurrealDB integration, HTTP API]
```

### Documentation
```
/Users/tryk/nabia/tools/riff-cli/README.md                     [Quick start]
/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md          [System design decisions]
/Users/tryk/nabia/tools/riff-cli/docs/PHASE_6B_STRATEGIC_HANDOFF.md [SurrealDB integration]
```

---

## 🎯 Quick Navigation

### I want to understand...

**Command routing**
→ See EXPLORATION_REPORT.md § 1 & § 2  
→ Read cli.py:build_parser() & cli.py:main()

**Data structures**
→ See EXPLORATION_REPORT.md § 3  
→ Read graph/models.py (Message, Thread, Session)

**Search implementation**
→ See EXPLORATION_REPORT.md § 11 (Data Flow: Search)  
→ Read search/qdrant.py (QdrantSearcher class)

**SurrealDB integration**
→ See EXPLORATION_REPORT.md § 7  
→ Read surrealdb/storage.py & docs/PHASE_6B_STRATEGIC_HANDOFF.md

**How to call from Rust**
→ See EXPLORATION_REPORT.md § 6  
→ Pattern: subprocess isolation via federation registry

**Configuration & environment**
→ See EXPLORATION_REPORT.md § 5  
→ Read .hookrc file (comprehensive setup)

**Federation integration**
→ See EXPLORATION_REPORT.md § 8  
→ Command: `nabi exec riff <cmd>` via `~/.nabi/bin/riff` symlink

**Available commands**
→ See EXPLORATION_REPORT.md § 2  
→ Or QUICK_REFERENCE.md § Key Commands
→ Or run: `riff --help`

**Module purposes**
→ See EXPLORATION_REPORT.md § 3 (Module Layout)  
→ Or QUICK_REFERENCE.md § Module Organization

---

## 🔍 The 5-Minute Summary

**Riff v2.0** is a **Python CLI** (not Rust yet) that:

1. **Searches conversations** semantically via Qdrant (384-dim vectors)
2. **Repairs JSONL** files (detects/fixes corruption)
3. **Visualizes as DAGs** (ASCII trees with optional TUI)
4. **Syncs to SurrealDB** with immutable event logging (Phase 6B)
5. **Integrates with Nabi** via federation symlinks

**No direct Rust integration yet** - communicates via subprocess isolation pattern.

**Architecture**: CLI command dispatcher → modular backends (search, repair, graph, etc.)

**Key Components**:
- `cli.py` - Command routing (argparse)
- `search/` - Qdrant vector search
- `graph/` - DAG analysis & persistence
- `surrealdb/` - Event-sourced storage
- `classic/` - Original JSONL commands

**Configuration**: XDG-compliant federation with `~/.nabi/venvs/riff-cli/`

**Databases**:
1. JSONL (source, read-only after sync)
2. SurrealDB (canonical, immutable events)
3. Qdrant (search index, 384-dim)

---

## 📚 Reading Order (Recommended)

**Quick Overview (5 min)**
1. This file (EXPLORATION_INDEX.md)
2. QUICK_REFERENCE.md

**Detailed Understanding (30 min)**
1. EXPLORATION_REPORT.md § 1-3 (Entry points, commands, modules)
2. EXPLORATION_REPORT.md § 11 (Architecture diagrams)
3. Look at: `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py` (actual code)

**Implementation Deep-Dive (1 hour)**
1. EXPLORATION_REPORT.md § 4-8 (IPC, config, databases, integration)
2. Read: `/Users/tryk/nabia/tools/riff-cli/src/riff/search/qdrant.py`
3. Read: `/Users/tryk/nabia/tools/riff-cli/src/riff/surrealdb/storage.py`
4. Read: `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md`

**Extending Riff (2 hours)**
1. EXPLORATION_REPORT.md § 12 (Extensibility points)
2. EXPLORATION_REPORT.md § 6 (How Rust would call Python)
3. Check `backends/` module (reserved for future integration)
4. Review test files: `/Users/tryk/nabia/tools/riff-cli/tests/`

---

## 🔧 Quick Commands

```bash
# Setup
cd /Users/tryk/nabia/tools/riff-cli
direnv allow
source .hookrc

# Verify setup
echo $RIFF_QDRANT_URL
python -c "from riff.search import QdrantSearcher; print(QdrantSearcher().is_available())"

# Run commands
riff --help
riff search "test"
riff sync:surrealdb <session-id>
riff graph <session-id>

# Register with federation
task nabi:register
nabi exec riff search "query"
```

---

## 🎓 Key Learnings

### Important Insights

1. **No Rust CLI Yet** - Riff is pure Python. Rust integration planned for Phase 7+.

2. **Process Isolation Pattern** - Federation uses subprocess isolation:
   - Each tool is independent process
   - Communication via stdout/JSON
   - Registry maps tool names to executables
   - No shared memory or direct calls

3. **XDG Compliance** - Venv at `~/.nabi/venvs/riff-cli/`:
   - Managed by federation
   - Auto-activated via `.hookrc`
   - Cross-platform compatible

4. **Three-Tier Persistence** - Reflects federation design:
   - JSONL (source, legacy)
   - SurrealDB (canonical, immutable events)
   - Qdrant (search index)

5. **Pluggable Architecture** - All backends (search, storage, TUI) follow Protocol patterns:
   - Can be swapped without changing CLI
   - Extensibility points in `backends/` module
   - Future Rust integration via subprocess

6. **Type Safety** - Python 3.13+ with full annotations:
   - Dataclasses for core models
   - Protocol types for interfaces
   - mypy type checking in CI

---

## 📊 Statistics

| Metric | Value |
|--------|-------|
| CLI Entry Point | `src/riff/cli.py` (600 lines) |
| Total Python Modules | 13 core modules |
| Commands Supported | 12+ (search, sync, graph, scan, fix, tui, etc.) |
| Data Model Classes | Message, Thread, Session, MessageType, ThreadType |
| Search Backend | Qdrant (384-dim vectors) |
| Event Store | SurrealDB (immutable append-only) |
| Python Target | 3.13+ |
| Documentation Files | 3 (README, ARCHITECTURE, Phase 6B guide) |
| Test Coverage | Tests in `tests/` directory |

---

## 🚀 Next Steps

**For Understanding**:
1. Read EXPLORATION_REPORT.md (detailed reference)
2. Read QUICK_REFERENCE.md (quick lookups)
3. Review `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md`

**For Implementation**:
1. Review `src/riff/cli.py` (command routing)
2. Study `search/qdrant.py` (backend pattern)
3. Look at `surrealdb/storage.py` (integration pattern)
4. Check `backends/` module (future expansion)

**For Extension**:
1. Create new backend in `backends/` or new module
2. Implement `ConversationStorage` protocol
3. Register in `cli.py` with new command
4. Add tests in `tests/` directory

---

## 📞 Cross-References

**Related Projects**:
- Nabi CLI: `~/docs/tools/nabi-cli.md`
- Federation: `~/docs/federation/STOP_PROTOCOL.md`
- Port Registry: `~/docs/federation/PORT_REGISTRY.md`

**In-Repo Documentation**:
- Architecture: `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md`
- Phase 6B: `/Users/tryk/nabia/tools/riff-cli/docs/PHASE_6B_STRATEGIC_HANDOFF.md`
- Development: `/Users/tryk/nabia/tools/riff-cli/docs/development.md`

---

## ✅ Exploration Complete

**Created Documents**:
- ✅ EXPLORATION_REPORT.md (636 lines, comprehensive reference)
- ✅ QUICK_REFERENCE.md (180 lines, quick guide)
- ✅ EXPLORATION_INDEX.md (this file, navigation guide)

**Coverage**:
- ✅ CLI entry points and command structure
- ✅ Module organization and purposes
- ✅ All 12+ available commands with examples
- ✅ Data models and core types
- ✅ Communication patterns (federation subprocess model)
- ✅ Configuration and environment setup
- ✅ Three-tier persistence architecture
- ✅ Federation integration pattern
- ✅ How Rust would integrate (recommended pattern)
- ✅ Future extensibility points

---

**Last Updated**: 2025-10-23  
**Explorer**: Claude Code Analysis  
**Status**: Complete & Documented
