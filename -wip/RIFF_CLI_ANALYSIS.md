# Riff-CLI Comprehensive Analysis

**Date**: 2025-10-27  
**Status**: Production-ready search, TUI in Week 2 development  
**Version**: 2.0.0  
**Repository**: `/Users/tryk/nabia/tools/riff-cli`  

---

## Executive Summary

**Riff-CLI** is a production-grade Python tool for searching Claude conversation sessions with semantic search and repairing malformed JSONL exports. It's part of the Nabia federation but **currently not indexed in federation documentation** (noted as integration gap).

### Key Facts
- **13K lines** of Python code (12,973 LOC)
- **9 major modules** (search, repair, TUI, graph, SurrealDB integration, etc.)
- **Development Stage**: Search fully operational | TUI in progress (Week 2)
- **Deployment**: XDG-compliant venv at `~/.nabi/venvs/riff-cli/`
- **Federation Status**: Code complete ✅ | Documentation gap ⚠️ | Not indexed ❌

---

## 1. Project Structure & Organization

### Directory Layout
```
/Users/tryk/nabia/tools/riff-cli/
├── src/riff/                    # Python package (1.4M)
│   ├── cli.py                   # Entry point (command routing)
│   ├── __main__.py              # Module invocation
│   ├── search/                  # Qdrant semantic search
│   │   ├── qdrant.py            # Vector database client
│   │   └── preview.py           # Rich text content rendering
│   ├── classic/                 # Original commands (scan, fix, tui, graph)
│   │   ├── commands/
│   │   │   ├── scan.py          # JSONL issue detection
│   │   │   ├── fix.py           # JSONL repair
│   │   │   ├── tui.py           # Interactive file browser
│   │   │   └── graph.py         # Conversation visualization
│   │   └── utils.py             # Shared utilities
│   ├── enhance/                 # AI query enhancement
│   │   └── intent.py            # Intent classification
│   ├── graph/                   # Conversation DAG analysis (24 files)
│   │   ├── models.py            # Data structures
│   │   ├── loaders.py           # JSONL parsing
│   │   ├── analysis.py          # Semantic DAG construction
│   │   ├── visualizer.py        # Tree/graph rendering
│   │   ├── persistence.py       # Event logging
│   │   ├── repair.py            # Repair workflow
│   │   └── ... (+ test files, docs)
│   ├── surrealdb/               # SurrealDB integration (Phase 6B) (23 files)
│   │   ├── storage.py           # Immutable event store
│   │   ├── repair_provider.py   # Repair persistence
│   │   ├── schema.sql           # Database schema
│   │   ├── schema_events.sql    # Event log schema
│   │   └── ... (+ utilities, tests, examples)
│   ├── tui/                     # Interactive TUI (Week 2) (4 files)
│   │   ├── interface.py         # Abstract TUI base
│   │   ├── prompt_toolkit_impl.py # MVP implementation
│   │   └── graph_navigator.py   # Navigation logic
│   └── backends/                # Plugin architecture
├── tests/                       # Test suite
├── infrastructure/              # Docker & Qdrant config
│   ├── docker-compose.yml       # Qdrant orchestration
│   └── qdrant/                  # Qdrant config
├── docs/                        # Documentation (35+ files)
├── .venv/                       # Python 3.13 venv (742M)
├── archive/                     # Legacy files (organized)
├── Taskfile.yml                 # Task automation
├── pyproject.toml               # uv configuration
└── README.md                    # Main documentation

```

### Code Organization Characteristics
- **Clean root**: Only essential files (README, config, build files)
- **Enterprise structure**: docs/, infrastructure/, tests/, src/ separated
- **Legacy management**: Old TUI in _ORIGINAL_TUI/, legacy code in archive/
- **Self-documenting**: README explains project purpose and structure clearly

---

## 2. Purpose & Capabilities

### Primary Purpose
Riff-CLI is a **unified search and repair tool for Claude conversation sessions**. It bridges:
- Semantic search across 800+ conversation JSONL files
- JSONL validation and repair (fixing broken exports)
- Interactive browsing and visualization
- Recovery workflows (orphan detection, parent suggestion)
- SurrealDB immutable event logging (Phase 6B)

### Key Capabilities

#### 2.1 Semantic Search with Content Preview
- **Qdrant Vector Database**: Searches ~800 indexed Claude sessions
- **Semantic Matching**: Finds conversations by meaning, not just keywords
- **Content Preview**: Actual text snippets in search results (not just paths)
- **Time-based Filtering**: `--days N`, `--since DATE`, `--until DATE`
- **UUID Lookup**: Direct access by session ID
- **AI Enhancement**: Optional intent-driven keyword expansion via Grok

**Performance**: Sub-2s latency, 384-dim vectors, 0.2 similarity threshold

#### 2.2 JSONL Repair & Validation
- **Scan**: Detect issues in Claude conversation exports
  - Missing tool_result fields
  - Malformed JSON
  - Orphaned messages
- **Fix**: Repair broken JSONL files
  - Auto-completion of missing fields
  - Writes `.repaired` backup
  - Original file unchanged
- **Validation**: Comprehensive error reporting

#### 2.3 Interactive TUI (Week 2)
- **Browse Mode**: Vim-style navigation (j/k/g/G)
- **Search Integration**: 'f' key to filter results
- **Session Viewer**: Display full conversation content
- **Modular Architecture**: Abstract interface for library swaps

#### 2.4 Conversation Visualization
- **Semantic DAG**: Directed acyclic graph of conversation flow
- **Tree Rendering**: Human-readable conversation structure
- **Mermaid/DOT Export**: Graph visualization formats
- **Analysis**: Identify patterns, branching points, anomalies

#### 2.5 Recovery Workflows (Phase 6A/B)
- **Orphan Detection**: Find conversations with missing parents
- **Parent Suggestion**: Rank candidate parent sessions by semantic similarity
- **Repair Events**: Immutable audit log of all repairs
- **SurrealDB Backend**: Persistent event store for federation coordination

#### 2.6 Federation Integration (Phase 6B/C)
- **Pluggable Persistence**: JSONL or SurrealDB backends
- **Immutable Event Log**: Audit trail of all operations
- **nabi-mcp Integration**: Search recovery entities in knowledge graph
- **Cross-machine Sync**: Syncthing + federation coordination

---

## 3. Entry Points & Main Modules

### CLI Entry Point
**File**: `src/riff/cli.py` (25K lines)

**Command Structure**:
```
riff [global-options] <command> [command-options]

Commands:
  search              Search Claude sessions with content preview
  browse              Interactive vim-style conversation browser
  scan                Scan for JSONL issues
  fix                 Repair missing tool_result in JSONL
  tui                 Interactive TUI for JSONL browsing
  graph               Visualize conversation as semantic DAG tree
  graph-classic       Generate conversation graph (mermaid/dot format)
  sync:surrealdb      Sync JSONL session to SurrealDB immutable event store
```

### Module Hierarchy

#### search/
- **QdrantSearcher** (qdrant.py): Vector DB client
  - `search()` - Execute semantic search with filters
  - `_build_time_filter()` - Handle --days/--since/--until
  - `_calculate_relevance()` - Score results
- **ContentPreview** (preview.py): Rich text rendering
  - `format_snippet()` - Syntax highlighting
  - `filter_hooks()` - Remove internal hook messages

#### classic/
- **cmd_scan** (scan.py): JSONL validation
- **cmd_fix** (fix.py): JSONL repair with auto-completion
- **cmd_tui** (tui.py): File browser interface
- **cmd_graph** (graph.py): Conversation visualization

#### graph/
- **JSONLLoader** (loaders.py): Parse JSONL files
- **ConversationDAG** (dag.py): Build conversation graph
- **ConversationAnalyzer** (analysis.py): Analyze structure
- **ConversationTreeVisualizer** (visualizer.py): Render tree output
- **RepairManager** (repair_manager.py): Coordinate repairs

#### surrealdb/
- **SurrealDBStorage** (storage.py): Immutable event store
- **RepairProvider** (repair_provider.py): Repair persistence
- **schema_utils.py**: Database schema management
- **repair_events_utils.py**: Event logging

#### tui/
- **InteractiveTUI** (interface.py): Abstract base class
- **PromptToolkitTUI** (prompt_toolkit_impl.py): MVP implementation
- **GraphNavigator** (graph_navigator.py): Navigation logic

#### enhance/
- **IntentEnhancer** (intent.py): AI query expansion

### Main Function
```python
def main():
    """Unified CLI entry point"""
    parser = argparse.ArgumentParser(description="Riff: search Claude conversations & repair JSONL sessions")
    subparsers = parser.add_subparsers(dest='command')
    
    # Register subcommands
    add_search_args(subparsers.add_parser('search'))
    add_browse_args(subparsers.add_parser('browse'))
    add_scan_args(subparsers.add_parser('scan'))
    # ... etc
    
    args = parser.parse_args()
    return execute_command(args)
```

---

## 4. Dependencies & Environment Setup

### Python Version
- **Minimum**: Python 3.13+
- **Current venv**: CPython 3.13.7 (macOS aarch64)
- **Package Manager**: uv (Astral - modern Python packaging)

### Core Dependencies

#### Required (base)
```toml
rich>=13.0.0              # Terminal UI rendering
prompt-toolkit>=3.0.0     # Interactive prompts
rapidfuzz>=3.0.0          # Fuzzy string matching
```

#### Optional: Search Features
```toml
qdrant-client>=1.7.0      # Vector database client
sentence-transformers>=2.2.0  # Embeddings (all-MiniLM-L6-v2)
```

#### Optional: Development
```toml
pytest>=7.0.0             # Test runner
pytest-cov>=4.0.0         # Coverage reporting
mypy>=1.0.0               # Type checking
```

### System Requirements
- **Docker**: For Qdrant service (optional but recommended)
- **Task**: Task automation (`brew install go-task`)
- **Qdrant**: Vector database (Docker container recommended)

### Environment Variables
```bash
QDRANT_URL              # Qdrant service URL (default: http://localhost:6333)
SURREALDB_URL          # SurrealDB connection (default: ws://localhost:8284/rpc)
RIFF_PERSISTENCE_BACKEND  # "jsonl" or "surrealdb" (default: jsonl)
XDG_CONFIG_HOME        # Configuration home (~/.config)
XDG_STATE_HOME         # State home (~/.local/state)
```

### Setup Instructions

**1. Quick Setup (30 seconds)**
```bash
cd /Users/tryk/nabia/tools/riff-cli
task dev:setup           # Install dependencies
task docker:up           # Start Qdrant
```

**2. Development Environment**
```bash
source .hookrc           # Load direnv setup
uv sync                  # Install in venv
uv run riff search "test"  # Verify installation
```

**3. Federation Integration** (XDG-compliant)
```bash
task nabi:register       # Register with nabi CLI
# Symlink created: ~/.nabi/bin/riff → ~/.nabi/venvs/riff-cli/bin/riff
```

### Current Status
- ✅ **venv created**: `~/.nabi/venvs/riff-cli/` (if setup completed)
- ✅ **Module importable**: `import riff` works
- ✅ **CLI functional**: `uv run riff --help` displays all commands
- ⚠️ **Qdrant not running**: Need `task docker:up` for search functionality
- ⚠️ **SurrealDB not configured**: Phase 6B requires separate setup

---

## 5. Documentation

### In-Repository Documentation (35+ files)
Located in `/Users/tryk/nabia/tools/riff-cli/docs/`

**Architecture & Design**:
- `ARCHITECTURE.md` - System design, three-layer architecture
- `PATTERNS.md` - Design patterns used
- `ROUTING_PATTERN_GUIDE.md` - CLI routing patterns

**Phases**:
- `PHASE_6B_IMPLEMENTATION.md` - Persistence layer
- `PHASE_6C_FEDERATION_INTEGRATION_PLAN.md` - Federation integration roadmap
- `PHASE_6B_QUICKSTART.md` - Quick start for Phase 6B
- `WEEK1_COMPLETION.md` - Week 1 TUI completion

**Graph Module**:
- `GRAPH_MODULE.md` - Conversation DAG analysis
- `GRAPH_NAVIGATOR_USAGE.md` - TUI navigation guide
- `SEMANTIC_DAG_DESIGN.md` - DAG construction algorithm
- `ANALYSIS_SUMMARY.md` - Analysis features

**SurrealDB Integration**:
- `SURREALDB_INTEGRATION_ANALYSIS.md` - Integration analysis
- `IMMUTABLE_STORE_ARCHITECTURE.md` - Event store design
- `IMMUTABLE_STORE_VISUAL_SUMMARY.md` - Visual overview

**Recovery Workflows**:
- `RECOVERY_SESSION_INTEGRATION.md` - Session recovery design
- `RECOVERY_ENTITIES_ALIGNMENT.md` - Entity alignment
- `REPAIR_WORKFLOW.md` - Repair process documentation

**Handoff & Status**:
- `HANDOFF_2025-10-20.md` - 25K line comprehensive handoff
- `CURRENT_STATE_ASSESSMENT_2025-10-22.md` - Status as of Oct 22
- `WEEK1_COMPLETION.md` - Week 1 milestones

**Root Documentation**:
- `README.md` - Main README with quick start
- `START_HERE_ALIGN_VALIDATION.md` - Entry point for ALIGN analysis
- `FEDERATION_INTEGRATION_BRIDGE.md` - Federation integration guide (1000+ lines)
- `ALIGN_COHERENCE_VALIDATION_REPORT.md` - Detailed coherence analysis (2800+ lines)
- `SEMANTIC_RELATIONSHIP_DIAGRAM.md` - Architecture diagrams (1200+ lines)

### Handoff Documents
**Location**: `/private/tmp/docs/riff-cli/` (temporary, not synced)

These are analysis/decision documents created during development.

### Main README
Located at `/Users/tryk/nabia/tools/riff-cli/README.md`

**Covers**:
- Feature overview
- Quick start (30 seconds)
- Usage examples
- Project structure
- Requirements
- Roadmap
- Federation integration

### Inline Documentation
- **Type hints**: Type-annotated Python throughout
- **Docstrings**: Module and function documentation
- **Code comments**: Complex algorithms documented inline

---

## 6. Integration with Nabi CLI

### Current Status: **Partially Integrated** ⚠️

#### What Works ✅
1. **XDG-Compliant Venv**
   - Riff installed in: `~/.nabi/venvs/riff-cli/`
   - Entry point: `~/.nabi/venvs/riff-cli/bin/riff`
   - Can be symlinked to `~/.nabi/bin/riff`

2. **Task Automation**
   - `task nabi:register` - Symlinks riff to federation
   - `task nabi:status` - Checks registration status
   - Taskfile integrates with nabi CLI pattern

3. **Module Structure**
   - Proper package layout (`src/riff/`)
   - Entry point defined: `riff = "riff.cli:main"`
   - Can be invoked via: `uv run riff <command>`

#### What's Missing ⚠️
1. **Federation Indices** ❌
   - Not listed in `FEDERATED_MASTER_INDEX.md`
   - Not in `MASTER_INDEX.md`
   - Not discoverable via federation agent search

2. **CLAUDE.md Integration** ❌
   - No mention in `/Users/tryk/.claude/CLAUDE.md`
   - Not documented in Memory Architecture section
   - Recovery workflows not documented for agents

3. **Documentation Promotion** ❌
   - Docs in git history (commits) not promoted to `~/Sync/docs/`
   - Phase 6A/B/C documentation not in federation knowledge base
   - 6 recovery entities orphaned from nabi-mcp

4. **SurrealDB Integration** ⚠️ Pending
   - Schema defined but not deployed
   - Repair events can't be logged until SurrealDB operational
   - Migration of recovery entities awaits SurrealDB fix

### Nabi CLI Integration Points
```bash
# If fully integrated, these would work:
nabi exec riff search "query"
nabi resolve riff
nabi list                    # Would show riff in available tools

# Currently requires:
uv run riff search "query"   # From project directory
~/.nabi/venvs/riff-cli/bin/riff search "query"  # Full path
```

### Federation Architecture (Planned - Phase 6C)
- **Memory Layer**: Recovery entities in nabi-mcp
- **Coordination**: Repair events logged to SurrealDB
- **Knowledge Graph**: Repair workflows discoverable
- **STOP Protocol**: Repair operations tracked
- **Federation Events**: Loki integration for monitoring

---

## 7. Current State Assessment

### What's Working ✅

**Search Module**
- Semantic search fully operational
- Content preview rendering works
- Time-based filtering implemented
- Performance: <2s latency

**Classic Commands**
- Scan, fix, tui, graph all functional
- JSONL repair process works
- Visualization generates correctly

**Code Quality**
- 13K lines well-organized Python
- Type hints throughout
- Comprehensive test coverage
- Enterprise repository structure

**Development Workflow**
- Taskfile automation integrated
- Easy setup: `task dev:setup`
- Docker/Qdrant easily managed
- Testing framework ready

### What Needs Attention ⚠️

**Federation Integration**
1. **Documentation Gaps**
   - Phase 6A/B/C docs in git history, not in federation
   - Handoff documents in /private/tmp/, not synced
   - ALIGN validation docs need federation promotion

2. **Knowledge Graph**
   - 6 recovery entities not in nabi-mcp
   - SurrealDB migration blocked by schema issues
   - No repair event logging happening

3. **Agent Discoverability**
   - Agents can't discover riff-cli workflows
   - Recovery patterns not in federation KB
   - No STOP protocol tracking for repairs

4. **Cross-Platform Validation**
   - Tested on macOS (dev machine)
   - WSL/Linux/RPi compatibility not verified
   - Hardcoded paths need audit

### Known Limitations ⚠️

**TUI Module (Week 2)**
- Interactive browser still in development
- PromptToolkitTUI is MVP implementation
- Future swap to Rust backend (tui-types) planned

**SurrealDB Integration**
- Schema defined but not tested end-to-end
- Repair event logging prepared but not active
- Immutable store architecture ready for validation

**Performance**
- Qdrant requires Docker (not ideal for minimal setups)
- Vector embeddings require sentence-transformers (~500MB)
- Full system footprint: 1.5GB (mostly venv)

### Issues to Resolve

**1. Federation Promotion**
- Extract Phase 6A/B/C docs from git history
- Create promotion PR to ~/Sync/docs/
- Update FEDERATED_MASTER_INDEX.md
- Add to CLAUDE.md Memory Architecture section

**2. SurrealDB Validation**
- Test schema deployment
- Verify repair event logging
- Migrate recovery entities
- Validate end-to-end workflow

**3. Cross-Platform Testing**
- Verify paths work on Linux/WSL/RPi
- Test Docker setup on different platforms
- Validate federation communication

---

## 8. Recommendations for Onboarding

### For Fresh Agents

**Priority 1: Understand the Architecture** (30 min)
1. Read: `README.md` - Overview and quick start
2. Read: `docs/ARCHITECTURE.md` - System design
3. Skim: `SEMANTIC_RELATIONSHIP_DIAGRAM.md` - Visual architecture

**Priority 2: Get It Running** (30 min)
```bash
cd /Users/tryk/nabia/tools/riff-cli
task dev:setup           # Install dependencies
task docker:up           # Start Qdrant
uv run riff search "test"  # Verify search works
```

**Priority 3: Understand Current State** (1 hour)
1. Read: `START_HERE_ALIGN_VALIDATION.md` - Current gaps
2. Read: `FEDERATION_INTEGRATION_BRIDGE.md` - What needs doing
3. Review: Git log to see recent work

### For Federation Integration Work

**Recommended Path**:
1. Read FEDERATION_INTEGRATION_BRIDGE.md (20 min)
2. Execute Phase 1: Documentation export (30 min)
3. Execute Phase 2: Federation integration (45 min)
4. Execute Phase 4: Validation (30 min)
5. Await SurrealDB fix for Phase 3

**Expected Timeline**: 2-3 hours for Phases 1-2-4

### For Development Work

**Module Knowledge Required** (1-2 hours):
1. `search/` - Know Qdrant client API
2. `graph/` - Understand conversation DAG model
3. `surrealdb/` - Know immutable event store patterns
4. `classic/` - Original command implementations
5. `tui/` - Abstract interface pattern

**Testing**:
```bash
task test:all              # Full test suite
task test:coverage         # Coverage report
task test:graph           # Graph module tests
```

### Critical Files to Know

| File | Purpose | Knowledge Required |
|------|---------|-------------------|
| `src/riff/cli.py` | Command routing | 30 min |
| `src/riff/search/qdrant.py` | Vector search | 20 min |
| `src/riff/graph/analysis.py` | DAG construction | 30 min |
| `src/riff/surrealdb/storage.py` | Immutable events | 20 min |
| `docs/ARCHITECTURE.md` | System design | 20 min |

---

## 9. Quick Health Check

```bash
# Current status verification
cd /Users/tryk/nabia/tools/riff-cli

# ✅ Module importable?
uv run python -c "import riff; print('✅ Module works')"

# ✅ CLI entry point?
uv run riff --help | head -5

# ✅ Search functional? (requires Qdrant)
task docker:status   # Check Qdrant (should fail if not running)

# ✅ Tests passing?
task test:all        # Run test suite

# ✅ Nabi registration?
task nabi:status     # Check federation symlink
```

---

## 10. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Riff-CLI v2.0                           │
│                    (13K Python LOC)                         │
├─────────────────────────────────────────────────────────────┤
│
│  ┌─ CLI Layer (cli.py)
│  │  └─ Argument parsing, command routing
│  │
│  ├─ Search Module (search/)
│  │  ├─ QdrantSearcher (vector DB client)
│  │  └─ ContentPreview (rich rendering)
│  │
│  ├─ Graph Module (graph/)
│  │  ├─ JSONLLoader (JSONL parsing)
│  │  ├─ ConversationDAG (semantic DAG)
│  │  ├─ Analysis (conversation structure)
│  │  ├─ Visualizer (tree rendering)
│  │  └─ RepairManager (repair coordination)
│  │
│  ├─ Classic Module (classic/)
│  │  ├─ cmd_scan (JSONL validation)
│  │  ├─ cmd_fix (JSONL repair)
│  │  ├─ cmd_tui (file browser)
│  │  └─ cmd_graph (visualization)
│  │
│  ├─ SurrealDB Module (surrealdb/)
│  │  ├─ SurrealDBStorage (immutable events)
│  │  ├─ RepairProvider (repair persistence)
│  │  └─ Schema management
│  │
│  ├─ TUI Module (tui/) [Week 2]
│  │  ├─ InteractiveTUI (abstract)
│  │  ├─ PromptToolkitTUI (MVP)
│  │  └─ GraphNavigator (vim-style)
│  │
│  └─ Enhance Module (enhance/)
│     └─ IntentEnhancer (AI query expansion)
│
├─────────────────────────────────────────────────────────────┤
│  Infrastructure:
│  - Qdrant (Docker container) - vector search
│  - SurrealDB (separate service) - immutable events
│  - Syncthing (federation sync) - cross-machine coordination
└─────────────────────────────────────────────────────────────┘
```

---

## Summary Table

| Aspect | Status | Notes |
|--------|--------|-------|
| **Code** | ✅ Production | 13K LOC, well-structured, type-safe |
| **Search** | ✅ Operational | Semantic + time filtering, <2s latency |
| **Repair** | ✅ Operational | JSONL validation and fixing working |
| **TUI** | 🚧 In Progress | Week 2 development, abstract interface ready |
| **Graph Analysis** | ✅ Complete | DAG construction and visualization working |
| **SurrealDB Integration** | ⚠️ Ready | Schema defined, awaiting validation |
| **Federation Integration** | ⚠️ Gaps | Docs not promoted, not indexed, entities orphaned |
| **Tests** | ✅ Complete | Unit + integration tests present |
| **Documentation** | ⚠️ Scattered | Comprehensive but not federated |
| **Setup** | ✅ Easy | `task dev:setup` gets you running |
| **nabi Integration** | ⚠️ Partial | Can be registered, not indexed yet |

---

## Next Steps

### Immediate (This Week)
1. **Federation Promotion** (Phase 1-2, FEDERATION_INTEGRATION_BRIDGE.md)
   - Export Phase 6A/B/C documentation
   - Create PRs to ~/Sync/docs/
   - Update federation indices
   - Time: ~2 hours

2. **Documentation Audit** 
   - Verify all paths use XDG compliance
   - Check no hardcoded /Users/tryk paths
   - Validate cross-platform portability

### Short Term (Next 2 Weeks)
1. **SurrealDB Validation** (Phase 3, pending SurrealDB fix)
   - Test schema deployment
   - Verify repair event logging
   - Migrate 6 orphaned entities

2. **Cross-Platform Testing**
   - Validate on Linux/WSL/RPi
   - Verify Docker setup works everywhere
   - Test federation communication

### Medium Term (Weeks 3-4)
1. **TUI Completion** (Week 2 continues)
   - Finish vim-style navigation
   - Integrate with graph display
   - Polish user experience

2. **Federation Service Spec**
   - Define repair event schema
   - Create coordination protocol
   - Document agent workflows

---

## References

### Key Documents
- **Main Entry**: `README.md` - Start here
- **Architecture**: `docs/ARCHITECTURE.md`
- **Federation**: `FEDERATION_INTEGRATION_BRIDGE.md`, `ALIGN_COHERENCE_VALIDATION_REPORT.md`
- **Semantics**: `SEMANTIC_RELATIONSHIP_DIAGRAM.md`
- **Validation**: `START_HERE_ALIGN_VALIDATION.md`

### Code Locations
- **Entry point**: `src/riff/cli.py`
- **Search**: `src/riff/search/`
- **Graph**: `src/riff/graph/`
- **SurrealDB**: `src/riff/surrealdb/`
- **Tests**: `tests/`

### External Dependencies
- Qdrant: http://localhost:6333
- SurrealDB: ws://localhost:8284/rpc
- Federation: ~/Sync/docs, nabi-mcp, SurrealDB

---

**Status**: Ready for federation integration and cross-platform validation  
**Last Updated**: 2025-10-27 13:00 UTC
