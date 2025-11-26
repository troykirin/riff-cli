# Riff CLI: Complete Python Backend Architecture Exploration

**Exploration Date**: 2025-10-23  
**Repository**: /Users/tryk/nabia/tools/riff-cli  
**Focus**: Python backend structure, CLI entry points, and integration mechanisms

---

## Executive Summary

**Riff CLI v2.0** is a unified Python tool (no Rust component yet) that provides:
- **Semantic search** through Claude conversations via Qdrant
- **JSONL repair and analysis** for conversation data
- **Interactive TUI** for browsing and visualization
- **SurrealDB integration** for persistent event-based storage (Phase 6B)

The architecture follows an **XDG-compliant federation** pattern where the Python tool is registered with the Nabi ecosystem and called via `nabi exec riff <command>`.

---

## 1. Main CLI Entry Point & Module Structure

### Entry Point Hierarchy

```
pyproject.toml: riff = "riff.cli:main"
    ↓
src/riff/__main__.py (Python -m riff entry)
    ↓
src/riff/cli.py (Main entry point - 600 lines)
    ├── build_parser() → argparse.ArgumentParser
    ├── main(argv) → int (exit code)
    └── Command functions:
        ├── cmd_search() - Qdrant semantic search
        ├── cmd_sync_surrealdb() - JSONL → SurrealDB sync
        ├── cmd_graph() - Visualize conversation DAG
        ├── cmd_browse() - Interactive navigator
        └── Classic commands preserved
```

### Version & Package Info

- **Version**: 2.0.0
- **Python Target**: 3.13+
- **Entry Script**: `riff = "riff.cli:main"` (pyproject.toml)
- **Build System**: uv_build (uv-managed package)

---

## 2. Available Commands & Tools

### Command Categories

#### NEW: Search & Discovery Commands

```bash
riff search <query>           # Semantic search with content preview
  --limit N                   # Max results (default: 10)
  --min-score FLOAT          # Similarity threshold (default: 0.3)
  --uuid                     # Treat query as UUID
  --ai                       # Enable AI intent enhancement
  --days N                   # Filter past N days
  --since DATE               # ISO 8601 filter
  --until DATE               # ISO 8601 filter

riff browse [query]          # Interactive vim-style navigator
  --limit N                  # Results to load
```

#### Phase 6B: SurrealDB Integration

```bash
riff sync:surrealdb <session_id>  # Sync JSONL to SurrealDB immutable store
  --force                    # Re-sync even if unchanged
  --dry-run                  # Preview without writing
  --operator NAME            # Operator name for audit trail
  --surrealdb-url URL       # Custom SurrealDB endpoint
```

#### Graph Visualization

```bash
riff graph <session_id>      # Visualize as semantic DAG tree
  --interactive             # Launch TUI navigator (default: True)
  --no-interactive          # ASCII tree only
  --surrealdb-url URL      # Repair backend URL

riff graph-classic <path>    # Legacy mermaid/dot output
  --format {dot,mermaid}
  --out FILE
```

#### Classic JSONL Commands

```bash
riff scan [target]          # Find JSONL issues
  --glob PATTERN            # File glob (default: **/*.jsonl)
  --show                    # Show details

riff fix <path>             # Repair JSONL
  --in-place               # Write back to same file

riff tui [target]           # Interactive JSONL browser
  --glob PATTERN
  --fzf                    # Use fzf for picking
```

### Command Implementation Pattern

Each command follows this pattern:
```python
def cmd_<name>(args) -> int:
    """Command implementation"""
    try:
        # Perform operation
        return 0  # Success
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1  # Failure
```

---

## 3. Module Structure & Key Components

### Directory Layout

```
src/riff/
├── __init__.py           # Package metadata (__version__ = "2.0.0")
├── __main__.py          # Entry for python -m riff
├── cli.py               # Command routing & entry point
│
├── search/              # Semantic search backend
│   ├── __init__.py
│   ├── qdrant.py       # QdrantSearcher - vector DB interface
│   └── preview.py      # ContentPreview - rich text rendering
│
├── enhance/             # AI-powered query enhancement
│   ├── __init__.py
│   └── intent.py       # IntentEnhancer - Grok-based expansion
│
├── graph/               # DAG analysis & persistence
│   ├── models.py        # Message, Thread, Session dataclasses
│   ├── dag.py          # ConversationDAG - tree analysis
│   ├── loaders.py      # JSONLLoader - session loading
│   ├── repair.py       # Repair operations & detection
│   ├── persistence.py  # Serialization & storage
│   ├── analysis.py     # Semantic analysis
│   └── visualizer.py   # ASCII tree rendering
│
├── surrealdb/           # Phase 6B: Event-sourced storage
│   ├── storage.py       # SurrealDBStorage - HTTP API integration
│   ├── schema_utils.py  # Schema preparation & validation
│   ├── repair_provider.py  # Repair events & materialization
│   ├── schema.sql       # SurrealDB table definitions
│   └── materialized_views.sql
│
├── classic/             # Original TUI commands (preserved)
│   ├── __init__.py
│   ├── utils.py
│   └── commands/
│       ├── tui.py      # TUI mode (prompt_toolkit)
│       ├── scan.py     # JSONL scanning
│       ├── fix.py      # JSONL repair
│       └── graph.py    # Graph generation
│
└── tui/                 # Interactive TUI (Week 2, modular)
    ├── interface.py     # Abstract TUI base class
    ├── prompt_toolkit_impl.py  # MVP implementation
    ├── graph_navigator.py  # Conversation navigator
    └── __init__.py
```

### Core Data Models (graph/models.py)

```python
class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    SUMMARY = "summary"
    FILE_HISTORY_SNAPSHOT = "file-history-snapshot"

@dataclass
class Message:
    uuid: str
    parent_uuid: Optional[str]
    type: MessageType
    content: str
    timestamp: str
    session_id: str
    is_sidechain: bool = False
    semantic_topic: Optional[str] = None
    thread_id: Optional[str] = None
    is_orphaned: bool = False
    corruption_score: float = 0.0
    metadata: dict[str, any]

@dataclass
class Thread:
    thread_id: str
    messages: list[Message]
    thread_type: ThreadType  # MAIN, SIDE_DISCUSSION, ORPHANED
    semantic_topic: Optional[str]
    corruption_score: float
    parent_thread_id: Optional[str]

@dataclass
class Session:
    session_id: str
    main_thread: Optional[Thread]
    side_threads: list[Thread]
    orphan_threads: list[Thread]
    message_count: int
    thread_count: int
    orphan_count: int
    corruption_score: float
```

---

## 4. IPC/Handoff & Communication Protocols

### Federation Integration (No Direct Rust Call)

**Important**: Riff does NOT have a Rust CLI calling Python. Instead:

```
nabi-python (bash shim)
    ↓
Routes to registered tools via symlinks
    ↓
~/.nabi/bin/riff → ../venvs/riff-cli/bin/riff
    ↓
Activates Python venv → calls riff Python CLI
```

### No IPC Currently Implemented

- **Current State**: CLI is a single Python entry point
- **Future Extensibility**: `backends/` module reserved for:
  - Nushell integration
  - CMP (Cognitive Memory Protocol)
  - Direct SurrealDB operations

### Communication Points

1. **Standard Input/Output**: Arguments parsed by argparse
2. **HTTP API**: SurrealDB storage.py uses `httpx` for HTTP calls
3. **Environment Variables**: Configuration via .hookrc

---

## 5. Environment Variables & Configuration

### XDG-Compliant Federation Setup (.hookrc)

```bash
# Runtime paths (from federation)
export NABI_RUNTIME_DIR="${NABI_RUNTIME_DIR:-$HOME/.nabi}"
export NABI_VENV_ROOT="${NABI_VENV_ROOT:-$NABI_RUNTIME_DIR/venvs}"
export RIFF_VENV="$NABI_VENV_ROOT/riff-cli"

# Python path setup
export PYTHONPATH="$RIFF_ROOT/src:$PYTHONPATH"

# Search backend
export RIFF_QDRANT_URL="${RIFF_QDRANT_URL:-http://localhost:6333}"
export RIFF_QDRANT_COLLECTION="${RIFF_QDRANT_COLLECTION:-claude_sessions}"
export RIFF_SEARCH_ENABLED=true
export RIFF_EMBEDDING_MODEL="${RIFF_EMBEDDING_MODEL:-all-MiniLM-L6-v2}"

# Preview settings
export RIFF_PREVIEW_MAX_LENGTH=200
export RIFF_PREVIEW_LINES=3

# Environment
export RIFF_ENV=development
```

### direnv Integration (.envrc)

```bash
#!/usr/bin/env bash
if [ -f .hookrc ]; then
  source .hookrc
fi
```

### Python Version

- **Lockfile**: `.python-version` → 3.13
- **Package Manager**: uv (fast, XDG-aware)
- **Virtual Env**: `~/.nabi/venvs/riff-cli/`

---

## 6. How Rust CLI Should Call Python Backend

### Current State (No Rust Yet)

```
User → nabi CLI (bash) → riff-python (registered tool) → Python subprocess
```

### If Rust CLI Were to Call Python

**Option A: Subprocess Pattern** (Recommended for federation)
```rust
use std::process::Command;

let output = Command::new("riff")
    .args(&["search", "query"])
    .output()?;
```

**Option B: Type-Stub Pattern** (Current federation design)
```rust
// Rust layer parses Nabi DSL commands
// Routes to Python via subprocess with structured args
// Receives JSON output for further processing
```

**Key Design Principle**: **Process Isolation**
- Each tool is a separate subprocess
- Communication via stdout/structured formats (JSON, JSONL)
- No shared memory or direct function calls
- Federation registry maps tool names to executables

### Current Federation Registration

```bash
# Tasks register riff with Nabi CLI
task nabi:register

# Creates symlink
~/.nabi/bin/riff → ~/.nabi/venvs/riff-cli/bin/riff

# Usage
nabi exec riff search "query"
```

---

## 7. Database & Persistence Layer

### Three-Tier Persistence Architecture

#### Tier 1: JSONL Files (Reference)
- Source format from Claude sessions
- Location: `~/.claude/projects/**/*.jsonl`
- Status: Read-only after sync to SurrealDB
- Format: Newline-delimited JSON

#### Tier 2: SurrealDB (Canonical - Phase 6B)
- **URL**: `ws://localhost:8000/rpc` (WebSocket) or HTTP API
- **Schema**:
  ```sql
  TABLE sessions
  TABLE messages
  TABLE repairs_events  # Immutable append-only log
  TABLE sessions_materialized  # Cached rebuild
  ```
- **Features**:
  - Immutable event sourcing for repairs
  - Full audit trail
  - Point-in-time reconstruction
  - HTTP API for Python integration

#### Tier 3: Qdrant (Search Index)
- **URL**: `http://localhost:6333`
- **Collection**: `claude_sessions`
- **Dimensions**: 384 (all-MiniLM-L6-v2)
- **Features**:
  - Semantic vector search
  - Metadata filtering (dates, topics)
  - <2s search latency
  - ~50MB index

### Storage Interface (graph/persistence.py)

```python
class ConversationStorage(Protocol):
    """Abstract storage interface"""
    
    def load_messages(self, session_id: str) -> list[Message]:
        """Load messages for session"""
    
    def save_messages(self, session_id: str, messages: list[Message]) -> None:
        """Persist messages"""
    
    def log_repair(self, event: RepairEvent) -> None:
        """Log repair operation"""
    
    def get_session(self, session_id: str) -> Session:
        """Get complete session state"""
```

---

## 8. Key Integration Points with Federation

### Nabi CLI Registration Pattern

```bash
# In riff-cli/Taskfile.yml
task nabi:register:
  cmds:
    - mkdir -p ~/.nabi/bin
    - ln -sf ~/.nabi/venvs/riff-cli/bin/riff ~/.nabi/bin/riff
```

### From Other Tools

```bash
# Any tool can call riff
nabi exec riff search "query"
nabi exec riff sync:surrealdb <session_id>
nabi exec riff graph <session_id>
```

### Port Registry Integration

- **Qdrant Port**: 6333 (see `~/docs/federation/PORT_REGISTRY.md`)
- **SurrealDB Port**: 8000
- **Configuration**: Via environment variables

---

## 9. Documentation & Knowledge Resources

### In-Repository Docs

| Document | Purpose |
|----------|---------|
| `README.md` | Quick start & overview |
| `docs/ARCHITECTURE.md` | System design decisions |
| `docs/RIFF_UNIFIED.md` | Unified command architecture |
| `docs/PHASE_6B_STRATEGIC_HANDOFF.md` | SurrealDB integration |
| `docs/SURREALDB_INTEGRATION_ANALYSIS.md` | Storage architecture |
| `src/riff/surrealdb/INTEGRATION_GUIDE.md` | Phase 6B usage |
| `src/riff/graph/PERSISTENCE.md` | Persistence layer |

### External Reference

- **Nabi CLI Docs**: `~/docs/tools/nabi-cli.md`
- **Federation Protocols**: `~/docs/federation/STOP_PROTOCOL.md`
- **Port Registry**: `~/docs/federation/PORT_REGISTRY.md`

---

## 10. Technology Stack & Dependencies

### Core Dependencies

```toml
rich = ">=13.0.0"           # Terminal UI
prompt-toolkit = ">=3.0.0"  # TUI interactions
rapidfuzz = ">=3.0.0"       # Fuzzy matching
```

### Optional (Search Backend)

```toml
qdrant-client = ">=1.7.0"           # Vector DB client
sentence-transformers = ">=2.2.0"   # Embeddings
```

### Development

```toml
pytest = ">=7.0.0"           # Testing
pytest-cov = ">=4.0.0"       # Coverage
mypy = ">=1.0.0"             # Type checking
```

### Package Management

- **Manager**: `uv` (Astral's fast Python package manager)
- **Lock File**: `uv.lock` (226.6MB - large due to sentence-transformers)
- **Python Version**: 3.13+

---

## 11. Architecture Diagrams

### Command Routing Flow

```
User Input (CLI args)
    ↓
argparse.ArgumentParser (cli.py:build_parser)
    ↓
Command Dispatcher (cli.py:main)
    ├─ search → cmd_search()
    │   ├─ QdrantSearcher (search/qdrant.py)
    │   ├─ IntentEnhancer (enhance/intent.py)
    │   └─ ContentPreview (search/preview.py)
    │
    ├─ sync:surrealdb → cmd_sync_surrealdb()
    │   ├─ JSONLLoader (graph/loaders.py)
    │   ├─ ConversationDAG (graph/dag.py)
    │   └─ SurrealDB HTTP API (surrealdb/storage.py)
    │
    ├─ graph → cmd_graph()
    │   ├─ JSONLLoader
    │   ├─ ConversationDAG
    │   ├─ ConversationTreeVisualizer
    │   └─ [Optional] ConversationGraphNavigator (TUI)
    │
    └─ [Classic] scan/fix/tui
        └─ classic.commands.*
```

### Data Flow (Search)

```
Query (text)
    ↓
IntentEnhancer (optional --ai flag)
    ↓
QdrantSearcher.search()
    ├─ sentence-transformers (query → 384-dim vector)
    ├─ Qdrant (vector similarity search)
    └─ Metadata filtering (--days/--since/--until)
    ↓
Results [Session] list
    ↓
ContentPreview.display_search_results()
    └─ Rich formatted output
```

### Data Flow (SurrealDB Sync)

```
JSONL File (~/.claude/projects/**/*.jsonl)
    ↓
JSONLLoader.load_messages()
    └─ Returns: list[Message]
    ↓
ConversationDAG(loader, session_id)
    └─ Builds tree from parent_uuid links
    ↓
dag.to_session()
    └─ Returns: Session (main + side threads)
    ↓
Change Detection (compare with existing)
    └─ Generates: list[RepairEvent]
    ↓
SurrealDB.create("session", {...})
SurrealDB.create("repairs_events", [...])
SurrealDB.create("sessions_materialized", {...})
    ↓
Immutable Event Store
```

---

## 12. Future Extensibility Points

### Pluggable Backend Architecture

1. **Search Backends** (search/)
   - Current: Qdrant (vector)
   - Future: Full-text search, fuzzy matching

2. **Persistence Backends** (graph/persistence.py)
   - Current: JSONL → SurrealDB
   - Future: Direct graph DB, GraphQL

3. **TUI Implementations** (tui/)
   - Current: prompt_toolkit (MVP)
   - Future: Rust tui-types backend (Phase 7)

4. **External Backends** (backends/)
   - Nushell integration (fast UUID extraction)
   - CMP (Cognitive Memory Protocol)
   - External graph databases

### Module Expansion Pattern

```python
# New backend example:
class MyBackend(ConversationStorage):
    def load_messages(self, session_id: str) -> list[Message]:
        # Custom implementation
    
    def save_messages(self, session_id: str, messages: list[Message]):
        # Custom implementation

# Register in cli.py
if args.backend == 'mybackend':
    storage = MyBackend()
```

---

## Summary Table: What's What

| Component | Type | Purpose | Status |
|-----------|------|---------|--------|
| `cli.py` | Python | Command routing | Production |
| `search/qdrant.py` | Python | Vector search | Production |
| `enhance/intent.py` | Python | AI query enhancement | Production |
| `graph/` | Python | DAG analysis | Production |
| `surrealdb/` | Python | Event-sourced storage | Phase 6B ✅ |
| `classic/` | Python | Original TUI commands | Preserved |
| `tui/` | Python | Interactive navigator | Development (Week 2) |
| `backends/` | Python | Extensibility hooks | Future |
| Rust CLI | N/A | Not implemented yet | Planned (Phase 7+) |

---

## Key Files Reference

### Entry Points
- `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py` (600 lines - command dispatcher)
- `/Users/tryk/nabia/tools/riff-cli/src/riff/__main__.py` (Python -m entry)
- `/Users/tryk/nabia/tools/riff-cli/pyproject.toml` (riff = "riff.cli:main")

### Configuration
- `/Users/tryk/nabia/tools/riff-cli/.hookrc` (environment setup, venv activation)
- `/Users/tryk/nabia/tools/riff-cli/.envrc` (direnv integration)
- `/Users/tryk/nabia/tools/riff-cli/.python-version` (3.13)

### Key Modules
- `/Users/tryk/nabia/tools/riff-cli/src/riff/search/qdrant.py` (QdrantSearcher)
- `/Users/tryk/nabia/tools/riff-cli/src/riff/surrealdb/storage.py` (SurrealDB integration)
- `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/models.py` (Data structures)

### Documentation
- `/Users/tryk/nabia/tools/riff-cli/README.md` (Quick start)
- `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md` (System design)
- `/Users/tryk/nabia/tools/riff-cli/docs/PHASE_6B_STRATEGIC_HANDOFF.md` (SurrealDB)

