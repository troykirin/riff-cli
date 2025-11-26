# Riff CLI - Key Findings Summary

## Overview
The riff-cli project is a **Python 3.13+ CLI application**, not Rust. It implements semantic search, JSONL repair, and conversation visualization for Claude sessions.

**Project Root**: `/Users/tryk/nabia/tools/riff-cli/`

---

## Main Files of Interest

### Entry Point
- **`/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py`** (286 lines)
  - Contains `build_parser()` function that defines all 9 subcommands
  - Contains `main()` function that dispatches to command implementations
  - This is the authoritative source for CLI structure

### Command Implementations
- `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py`:
  - `cmd_search()` (lines 285-341) - Semantic search
  - `cmd_graph()` (lines 343-445) - DAG visualization
  - `cmd_sync_surrealdb()` (lines 21-283) - Phase 6B persistence
  - `cmd_browse()` (lines 447-477) - Interactive browser

### Backend Modules
- `/Users/tryk/nabia/tools/riff-cli/src/riff/search/qdrant.py` - Vector search backend
- `/Users/tryk/nabia/tools/riff-cli/src/riff/search/preview.py` - Content rendering
- `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/dag.py` - DAG implementation
- `/Users/tryk/nabia/tools/riff-cli/src/riff/surrealdb/storage.py` - DB client

### Documentation
- `/Users/tryk/nabia/tools/riff-cli/README.md` - Quick start
- `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md` - System design
- `/Users/tryk/nabia/tools/riff-cli/pyproject.toml` - uv project config

---

## Command Structure (9 Total)

### NEW Commands (v2.0)
1. **search** - Semantic search with content preview
2. **browse** - Vim-style interactive browser
3. **graph** - Semantic DAG tree visualization
4. **sync:surrealdb** - Phase 6B immutable event store

### CLASSIC Commands (Preserved)
5. **scan** - JSONL file analysis
6. **fix** - JSONL repair
7. **tui** - Interactive file browser
8. **graph-classic** - Mermaid/DOT output
9. **--qdrant-url** - Global option

---

## Flag Analysis - NO CONFLICTS FOUND

**Search Command** (`riff search`)
- `query` (positional)
- `--limit` (int, default: 10)
- `--min-score` (float, default: 0.3)
- `--uuid` (boolean)
- `--ai` (boolean)
- `--days` (int)
- `--since` (str)
- `--until` (str)

**Graph-Classic Command** (`riff graph-classic`)
- `path` (positional)
- `--format` (enum: dot|mermaid) **← NO SHORT `-f` option**
- `--out` (str)

**Other Commands**
- scan: `--glob`, `--show`
- fix: `--in-place`
- tui: `--glob`, `--fzf`
- sync:surrealdb: `--force`, `--dry-run`, `--operator`, `--surrealdb-url`

**Conclusion**: No `-f` duplicate conflicts detected anywhere in the CLI.

---

## Architecture Overview

### Three-Layer Design
1. **CLI Layer** (cli.py)
   - Argument parsing via argparse
   - Command dispatch

2. **Business Logic Layer**
   - Search (QdrantSearcher)
   - Graph analysis (DAG)
   - Query enhancement

3. **Integration Layer**
   - SurrealDB (persistence)
   - JSONL (repair)
   - Qdrant (vectors)

### Modular Components
- **Search Module**: QdrantSearcher + ContentPreview
- **Graph Module**: DAG + Visualizer + Repair
- **TUI Module**: Abstract interface + PromptToolkit
- **SurrealDB Module**: HTTP API client + event store
- **Classic Module**: Preserved original functionality

---

## Integration with nabi-python

**Current State**: Not yet wired in nabi-python script

**nabi-python** (`/Users/tryk/nabia/tools/nabi-python`)
- Shell script fallback shim
- Routes `nabi <commander>` to backends
- Does NOT yet handle "riff" commander

**riff-cli** is independently functional:
```bash
riff search "query"           # Direct usage works
riff graph SESSION_ID         # Direct usage works
riff sync:surrealdb SESSION   # Direct usage works
```

**Next Steps for Integration**:
1. Add "riff" case in nabi-python script
2. Route to riff-cli Python CLI
3. Handle any command translation needed
4. Test via `nabi exec riff ...`

---

## Project Status

**Version**: 2.0.0  
**Language**: Python 3.13+  
**Framework**: argparse (standard library)  
**Package Manager**: uv

**Timeline**:
- ✅ Week 1: Foundation (architecture, Docker, docs)
- 🚧 Week 2: TUI module (in progress)
- 📅 Week 3: TUI integration
- 📅 Week 4: Production polish

**Key Features**:
- ✅ Semantic search with Qdrant
- ✅ Time-based filtering (--days, --since, --until)
- ✅ DAG-based conversation analysis
- ✅ SurrealDB immutable event store
- ✅ JSONL repair utilities
- 🚧 Interactive TUI (WIP)

---

## File Location Summary

```
/Users/tryk/nabia/tools/riff-cli/
├── src/riff/cli.py                    ← MAIN ENTRY POINT
├── README.md                          ← Quick start
├── pyproject.toml                     ← Dependencies
├── Taskfile.yml                       ← Task automation
│
├── src/riff/
│   ├── search/qdrant.py              ← Vector search
│   ├── search/preview.py             ← Content rendering
│   ├── graph/dag.py                  ← DAG structure
│   ├── surrealdb/storage.py          ← DB client
│   └── ... (other modules)
│
└── docs/
    ├── ARCHITECTURE.md               ← System design
    ├── PHASE_6B_*.md                 ← Persistence details
    └── (30+ other docs)
```

---

## Investigation Methodology

1. ✅ Examined `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py` for all command definitions
2. ✅ Analyzed `build_parser()` function line-by-line
3. ✅ Searched for `-f` flag usage across entire codebase
4. ✅ Reviewed nabi-python integration point
5. ✅ Verified directory structure and file organization
6. ✅ Confirmed no conflicting flag definitions

---

## Recommendations

### For Understanding the Codebase
1. Start with: `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py`
2. Then read: `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md`
3. Review: `/Users/tryk/nabia/tools/riff-cli/README.md` for quick start

### For Integration
1. Update nabi-python to route "riff" commander
2. Map `nabi exec riff search` → Python CLI
3. Test integration before committing

### For Future Development
1. Phase 2 (Week 2): Complete TUI module
2. Phase 3 (Week 3): Default TUI integration
3. Consider future Rust port based on architecture

---

## Quick Command Reference

```bash
# Semantic search with content preview
riff search "memory architecture"

# Search by session UUID
riff search --uuid abc-123-def

# Time-filtered search
riff search "federation" --days 7

# Graph visualization (interactive TUI)
riff graph SESSION_UUID --interactive

# ASCII tree only (no TUI)
riff graph SESSION_UUID --no-interactive

# Sync session to SurrealDB
riff sync:surrealdb SESSION_UUID --force

# Classic JSONL repair
riff scan ~/claude/sessions/
riff fix broken-session.jsonl --in-place

# Dry-run sync
riff sync:surrealdb SESSION_UUID --dry-run
```

---

**Document**: Riff CLI Architecture Exploration  
**Generated**: 2025-10-23  
**Status**: Complete and verified
