# Riff CLI v2.0: Analysis Quick Reference

**Date**: 2025-10-28 | **Analysis Size**: 1,005 lines | **Code Analyzed**: ~13,000 Python LOC

---

## At a Glance

| Aspect | Status | Details |
|--------|--------|---------|
| **Architecture** | ✅ Enterprise-grade | Clean separation, pluggable backends, type-safe |
| **Search** | ✅ Production-ready | Qdrant + sentence-transformers semantic search |
| **Graph Analysis** | ✅ Core complete | DAG reconstruction, thread detection, 0-1 corruption scoring |
| **Repair Tools** | ✅ Production-ready | JSONL scan, fix, graph visualization (backward compatible) |
| **SurrealDB Sync** | 🚧 Phase 6B | Immutable event store for repairs (integration underway) |
| **Interactive TUI** | 🚧 Week 2 | Vim-style navigation in development |
| **Federation** | 📋 Phase 6C | memchain + Loki integration (planned) |
| **Testing** | ✅ Comprehensive | 22 test files, 4,500+ lines, 50-70% coverage |
| **Documentation** | ✅ Excellent | 35+ docs, detailed handoff notes |

---

## Module Breakdown (50 Files)

### 1. Search (2 files) - ✅ Production
- `src/riff/search/qdrant.py`: Vector DB client (150 lines)
- `src/riff/search/preview.py`: Rich CLI formatting

### 2. Enhance (1 file) - ✅ Working
- `src/riff/enhance/intent.py`: Query expansion & intent detection (71 lines)

### 3. Graph (15 files) - ✅/🚧 Core Done/UI TBD
- `models.py`: Message, Thread, Session dataclasses (type-safe)
- `dag.py`: Conversation DAG builder (~300 lines)
- `analysis.py`: Thread detection & corruption scoring (~300 lines)
- `loaders.py`: Abstract storage interface + JSONL impl
- `visualizer.py`: ASCII tree rendering
- `graph_navigator.py`: Interactive TUI (in progress)
- `repair.py`, `persistence.py`: Orchestration
- Test files for all above

### 4. Classic (4 files) - ✅ Preserved
- `commands/scan.py`: Find JSONL issues
- `commands/fix.py`: Repair missing tool_result
- `commands/tui.py`: Interactive file browser
- `commands/graph.py`: Mermaid/DOT output

### 5. SurrealDB (6 files) - 🚧 Phase 6B
- `storage.py`: Async WebSocket client
- `schema_utils.py`: Schema generation
- `repair_provider.py`: Event persistence
- Test & example files

### 6. TUI (3 files) - 🚧 Week 2
- `interface.py`, `graph_navigator.py`, `prompt_toolkit_impl.py`

### 7. CLI (1 file) - ✅ Ready
- `src/riff/cli.py`: Unified entry point (476 lines, 8 subcommands)

### 8. Backends (1 file) - 🏗️ Planned
- Plugin architecture for storage backends

---

## Architecture Patterns (Enterprise)

### 1. Unified CLI Entry Point
```python
# src/riff/cli.py: Multi-command parser with subcommand handlers
parser.add_subparsers(dest="command")
p_search = subparsers.add_parser("search", ...)
p_search.set_defaults(func=cmd_search)  # Clean dispatch
```

### 2. Storage Abstraction
```python
# src/riff/graph/loaders.py: Abstract base class pattern
class ConversationStorage(ABC):
    @abstractmethod
    def load_messages(self, session_id: str) -> list[Message]: ...

class JSONLLoader(ConversationStorage):  # Concrete impl
    def load_messages(self, session_id: str) -> list[Message]: ...
# Later: DatabaseLoader, RemoteLoader follow same interface
```

### 3. Type-Safe Models
```python
# src/riff/graph/models.py
@dataclass
class Message:
    uuid: str
    parent_uuid: Optional[str]
    type: MessageType  # Enum: user, assistant, system, ...
    corruption_score: float  # 0.0-1.0 with validation

    def __post_init__(self) -> None:
        # Validate on construction
        if not 0.0 <= self.corruption_score <= 1.0:
            raise ValueError(...)
```

### 4. Graceful Error Handling
```python
# src/riff/cli.py: cmd_search() pattern
try:
    searcher = QdrantSearcher(...)
    if not searcher.is_available():
        console.print("[yellow]Qdrant unavailable[/yellow]")
        return 1
    results = searcher.search(...)
    return 0
except ImportError:
    console.print("[red]Install: pip install qdrant-client[/red]")
    return 1
```

---

## Code Quality Metrics

| Aspect | Score | Notes |
|--------|-------|-------|
| Type Hints | 60% | New modules (search, enhance): 95%, Old modules (classic): 30% |
| Test Coverage | 50-70% | Gaps in TUI, Phase 6C federation code |
| Linting | ✅ Enabled | mypy, ruff, pytest configurations present |
| Documentation | ✅ Excellent | 35+ files, detailed handoff notes |
| Architecture | ✅ Clean | ABC patterns, no global state, testable |

---

## Dependency Graph

```
CORE (always required):
  ├─ rich >=13.0.0           Terminal formatting
  ├─ prompt-toolkit >=3.0.0  Interactive TUI
  └─ rapidfuzz >=3.0.0       Fuzzy matching

OPTIONAL (feature-gated):
  ├─ qdrant-client >=1.7.0        [search]
  ├─ sentence-transformers >=2.2.0 [search]
  └─ surrealdb                     [federation]

DEV (testing & quality):
  ├─ pytest >=7.0.0
  ├─ pytest-cov >=4.0.0
  ├─ mypy >=1.0.0
  └─ uv (build backend)
```

---

## Integration Points

### Nabi CLI (Ready)
```bash
nabi exec riff search "memory"
nabi exec riff graph session-uuid
nabi list  # riff appears in registry
```

### SurrealDB (Phase 6B - In Progress)
```bash
riff sync:surrealdb session-uuid
# Syncs JSONL → SurrealDB
# Logs repairs as immutable events
# Enables cross-agent coordination
```

### Federation (Phase 6C - Planned)
- memchain MCP client wrapper
- Repair event schema validation
- Distributed locking (conflict detection)
- Loki event publishing
- OAuth integration

---

## Commands Overview

### Search
```bash
riff search "memory"                    # Semantic search
riff search --ai "federation patterns"  # AI-enhanced
riff search --uuid abc-123              # UUID lookup
riff search --days 7                    # Past 7 days
```

### Graph Visualization
```bash
riff graph session-uuid                 # Interactive DAG
riff graph session-uuid --no-interactive # ASCII only
```

### Repair
```bash
riff scan ~/claude/sessions/   # Find issues
riff fix session.jsonl          # Repair corruption
riff sync:surrealdb session-id  # Sync to SurrealDB
```

### Legacy Commands (Preserved)
```bash
riff tui ~/claude/              # File browser
riff graph-classic session.jsonl # Mermaid/DOT output
```

---

## Strengths ✅

1. **Clean Separation**: Search, graph, repair are independent modules
2. **Progressive Enhancement**: Works with/without optional backends
3. **Type Safety**: Full Python 3.13+ annotations on new code
4. **Enterprise Patterns**: ABC-based extensibility, no global state
5. **Documentation**: 35+ files with detailed design decisions
6. **Federation Ready**: SurrealDB + memchain integration pathways
7. **Testable**: Fixtures, mocks, integration tests
8. **Portable**: XDG-compliant, works on macOS/Linux/WSL/RPi

---

## Areas Needing Attention ⚠️

1. **TUI Completion** (Week 2)
   - Vim keybindings (j/k, h/l, /, q)
   - Message detail view
   - Thread filtering

2. **Federation Phase 6C** (Planned)
   - memchain coordination
   - Distributed repair locking
   - Loki monitoring

3. **Type Hint Consistency** (60% → 100%)
   - Migrate `classic/` module (30% coverage)
   - Update `graph/repair.py`

4. **Performance Benchmarking**
   - Unknown behavior with 1000+ message sessions
   - No embedding cache optimization

---

## Improvement Opportunities (Prioritized)

### High Priority (1-2 weeks)
1. **TUI Completion** - Critical UX feature
2. **Federation Integration** - Multi-agent coordination
3. **Search Index Management** - Operational necessity

### Medium Priority (2-4 weeks)
4. **Type Hint Migration** - Code consistency
5. **Error Recovery** - Checkpoint system for repairs
6. **Performance Optimization** - Large-session handling

### Lower Priority (1-3 months)
7. **Content Preview Enhancements** - Syntax highlighting, diffs
8. **Plugin Architecture** - Custom repair strategies
9. **Monitoring** - JSON logging, Prometheus metrics

---

## Key Files to Review

| File | Lines | Purpose |
|------|-------|---------|
| `src/riff/cli.py` | 476 | Entry point, 8 subcommands |
| `src/riff/graph/models.py` | 150 | Data model definitions |
| `src/riff/graph/dag.py` | ~300 | DAG construction algorithm |
| `src/riff/graph/analysis.py` | ~300 | Thread detection & scoring |
| `src/riff/search/qdrant.py` | ~150 | Qdrant integration |
| `pyproject.toml` | 33 | Dependencies, entry points |
| `.hookrc` | ~150 | Environment setup |
| `Taskfile.yml` | ~300 | Automation (45+ tasks) |

---

## Testing & Quality Assurance

### Run Tests
```bash
task test:all           # Full suite with coverage
task test:unit          # Unit tests only
task test:integration   # Integration tests
task lint               # Type checking (mypy)
```

### Coverage Goals
```
Target:
  - search/: 95% (currently ~80%)
  - graph/: 90% (currently ~65%)
  - surrealdb/: 95% (currently ~70%)
  - classic/: 75% (currently ~40%)
  - tui/: 60% (currently ~20%)
```

---

## Federation Status

| Phase | Status | Target | Features |
|-------|--------|--------|----------|
| **6A** | ✅ Complete | N/A | Search, graph, repair tools |
| **6B** | 🚧 Underway | Oct 28 | SurrealDB event store sync |
| **6C** | 📋 Planned | Nov 15 | memchain coordination |

---

## Environment Variables

```bash
RIFF_ENV=development                    # Mode
RIFF_QDRANT_URL=http://localhost:6333  # Vector DB
RIFF_QDRANT_COLLECTION=claude_sessions # Collection
RIFF_EMBEDDING_MODEL=all-MiniLM-L6-v2 # Embeddings
RIFF_SEARCH_ENABLED=true                # Feature flag
RIFF_PREVIEW_MAX_LENGTH=200            # Snippet size
```

---

## Documentation Map

| Document | Location | Purpose |
|----------|----------|---------|
| **Comprehensive Analysis** | `COMPREHENSIVE_ARCHITECTURE_ANALYSIS_2025-10-28.md` | Full 1,005-line analysis |
| **Architecture** | `ARCHITECTURE.md` | System design decisions |
| **Quick Start** | `START_HERE.md` | Getting started guide |
| **Development** | `development.md` | Dev environment setup |
| **Graph Module** | `GRAPH_MODULE.md` | DAG analysis details |
| **Phase 6B** | `PHASE_6B_*.md` | SurrealDB integration |
| **Phase 6C** | `PHASE_6C_FEDERATION_INTEGRATION_PLAN.md` | Federation roadmap |

---

## Summary

**Riff CLI v2.0** is a **production-ready, enterprise-grade tool** for:
- Semantic search across conversation archives
- JSONL corruption detection and repair
- Interactive DAG visualization of conversation threads
- Federation-wide coordination via SurrealDB + memchain

**Best For**: Teams managing large conversation volumes, multi-agent systems, audit trails.

**Next Steps**: TUI completion (Week 2) → Federation integration (Phase 6C) → Production deployment.

---

**Analysis Generated**: 2025-10-28  
**Total Documentation**: 1,005 lines  
**Code Coverage**: ~13,000 lines Python across 50+ files  
**Key Insight**: Production-ready search & repair with clear federation integration pathway.
