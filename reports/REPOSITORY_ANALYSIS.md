# Riff CLI Repository Analysis

**Analysis Date**: 2025-01-27  
**Repository**: `/Users/tryk/nabia/tools/riff-cli`  
**Version**: 2.0.0  
**Status**: Production Ready (Search), In Development (TUI)

---

## Executive Summary

**Riff CLI** is a Python-based command-line tool for searching Claude conversation sessions using semantic search (Qdrant) and repairing JSONL files. It's part of the **NabiOS ecosystem** and serves as a gateway tool that teaches XDG Base Directory Specification compliance while providing enterprise-grade conversation management.

### Key Highlights
- ✅ **v2.0 Released**: XDG-compliant architecture with educational onboarding
- ✅ **Semantic Search**: Qdrant vector search with 384-dim embeddings
- ✅ **Three-Tier Persistence**: JSONL → SurrealDB → Qdrant
- ✅ **Comprehensive Testing**: Unit, integration, and live tests
- ✅ **Well-Documented**: Extensive docs with quick-start guides
- 🚧 **TUI Module**: In development (Week 2)

---

## 1. Project Overview

### Purpose
Riff CLI enables users to:
1. **Search conversations semantically** - Find Claude sessions by meaning, not just keywords
2. **Repair JSONL files** - Fix malformed conversation exports with duplicate detection
3. **Visualize conversation graphs** - Generate DAG visualizations (Mermaid/DOT)
4. **Sync to SurrealDB** - Event-sourced storage for immutable conversation history
5. **Interactive browsing** - TUI for navigating conversations

### Target Users
- Developers working with Claude conversations
- Users needing to search through conversation history
- NabiOS ecosystem participants learning XDG patterns

### Ecosystem Position
```
NabiOS Federation
├── Riff CLI (this repo) - Semantic search + JSONL repair
├── Riff DAG TUI - Visualization companion
└── NabiOS Core - Federation coordination
```

---

## 2. Architecture & Design

### 2.1 System Architecture

**Three-Layer Design:**
```
CLI Entry Point (cli.py)
    ├── Search Mode (Qdrant semantic search)
    ├── Repair Mode (JSONL fix/scan)
    └── TUI Mode (Interactive navigation)
```

### 2.2 Module Organization

**Core Modules** (13 modules, ~277 classes/functions):

| Module | Purpose | Status |
|--------|---------|--------|
| `cli.py` | Command routing & argument parsing | ✅ Complete |
| `search/` | Qdrant vector search + content preview | ✅ Complete |
| `graph/` | DAG analysis, models, loaders | ✅ Complete |
| `surrealdb/` | Event-sourced storage integration | ✅ Complete |
| `classic/` | Original TUI commands (scan/fix/tui/graph) | ✅ Complete |
| `enhance/` | AI query enhancement (Grok) | ✅ Complete |
| `tui/` | Interactive navigator (modular) | 🚧 In Progress |
| `backup.py` | Automatic backup system | ✅ Complete |
| `config.py` | XDG-compliant configuration | ✅ Complete |
| `visualization/` | DAG visualization handlers | ✅ Complete |

### 2.3 Data Flow

**Three-Tier Persistence Architecture:**
```
1. JSONL (Source)
   ↓ Index/Sync
2. SurrealDB (Canonical Store - Immutable Events)
   ↓ Vectorize
3. Qdrant (Search Index - 384-dim vectors)
```

**Search Flow:**
```
User Query → Intent Enhancement (optional) → Embedding → Qdrant Search → Content Preview
```

### 2.4 Design Patterns

1. **Modular TUI Architecture**: Abstract `InteractiveTUI` interface allows swapping implementations
2. **Process Isolation**: Federation uses subprocess isolation for tool communication
3. **XDG Compliance**: All paths follow XDG Base Directory Specification
4. **Event Sourcing**: SurrealDB stores immutable events, not state
5. **Graceful Degradation**: Works without optional dependencies

---

## 3. Key Components Deep Dive

### 3.1 Search Module (`src/riff/search/`)

**Components:**
- `qdrant.py`: QdrantSearcher with time-based filtering
- `preview.py`: ContentPreview with rich text rendering
- `router.py`: Search routing logic

**Features:**
- Semantic search with 384-dim vectors (all-MiniLM-L6-v2)
- Time filtering: `--days`, `--since`, `--until`
- Content snippets in results (not just metadata)
- UUID lookup support
- AI-enhanced queries (optional)

### 3.2 Graph Module (`src/riff/graph/`)

**Components:**
- `models.py`: Message, Thread, Session data models
- `loaders.py`: JSONL loading and parsing
- `dag.py`: DAG analysis and traversal
- `visualizer.py`: Conversation tree visualization
- `persistence.py`: Multi-provider persistence (SurrealDB, JSONL)

**Capabilities:**
- DAG structure analysis
- Thread relationship mapping
- Multiple output formats (Mermaid, DOT, ASCII)
- Interactive TUI visualization

### 3.3 SurrealDB Integration (`src/riff/surrealdb/`)

**Components:**
- `storage.py`: Event-sourced storage implementation
- `schema.sql`: Database schema definitions
- `repair_provider.py`: Repair event handling
- `schema_utils.py`: Schema management utilities

**Architecture:**
- Immutable event store
- Materialized views for queries
- Repair event tracking
- Session synchronization

### 3.4 Classic Commands (`src/riff/classic/`)

**Commands:**
- `scan`: Find issues in JSONL files (includes duplicate detection)
- `fix`: Repair conversations with automatic backup
- `tui`: Interactive file browser
- `graph`: Generate conversation graphs

**Features:**
- Duplicate tool_result detection
- Safe backup system before modifications
- Rich output tables

### 3.5 Configuration System (`src/riff/config.py`)

**XDG-Compliant Paths:**
- `~/.config/nabi/riff.toml` - Configuration (portable)
- `~/.local/share/nabi/riff/` - Application data (backup this)
- `~/.local/state/nabi/riff/` - Runtime state (ephemeral)
- `~/.cache/nabi/riff/` - Temporary cache (deletable)

**Features:**
- Auto-creation with educational TOML (200 lines)
- Environment variable overrides
- Lazy loading with singleton pattern
- Hot-reload support

### 3.6 Backup System (`src/riff/backup.py`)

**Features:**
- Automatic timestamped backups before modifications
- Hot-reload index in state directory
- Restore capability with safety backups
- Cleanup tools for old backups

---

## 4. Technology Stack

### 4.1 Core Dependencies

**Python**: 3.13+ (requires modern Python features)

**Core Libraries:**
- `rich>=13.0.0` - Terminal formatting and UI
- `prompt-toolkit>=3.0.0` - Interactive TUI
- `rapidfuzz>=3.0.0` - Fuzzy string matching
- `toml>=0.10.2` - Configuration parsing
- `surrealdb>=1.0.6` - Database client

**Optional Dependencies:**
- `qdrant-client>=1.7.0` - Vector search (search mode)
- `sentence-transformers>=2.2.0` - Embeddings (search mode)

### 4.2 Infrastructure

**Docker Services:**
- Qdrant (vector database) - `localhost:6333` (HTTP), `6334` (gRPC)
- SurrealDB (event store) - `ws://localhost:8000/rpc`

**Build System:**
- `uv` - Fast Python package manager
- `pyproject.toml` - Modern Python project configuration
- `Taskfile.yml` - Task automation (Task runner)

### 4.3 Development Tools

**Testing:**
- `pytest>=7.0.0` - Test framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `pytest-mock>=3.10.0` - Mocking utilities

**Code Quality:**
- `mypy>=1.0.0` - Type checking
- `black>=23.0.0` - Code formatting
- `ruff>=0.1.0` - Fast linting

---

## 5. Development Status

### 5.1 Completed Features (v2.0.0)

✅ **Core Functionality:**
- Semantic search with Qdrant
- JSONL repair with duplicate detection
- SurrealDB synchronization
- Graph visualization
- XDG-compliant configuration
- Automatic backup system
- AI query enhancement

✅ **Infrastructure:**
- Docker Compose setup
- Task automation
- Federation integration
- Comprehensive documentation

### 5.2 In Progress

🚧 **TUI Module** (Week 2):
- Modular TUI architecture (abstract interface)
- PromptToolkit implementation (MVP)
- Graph navigator
- Vim-style controls

### 5.3 Planned (v2.1.0+)

📅 **Future Releases:**
- Single-binary distribution (PyInstaller)
- GitHub Actions CI/CD
- Homebrew formula
- Windows .exe support
- Auto-update mechanism

---

## 6. Code Quality & Organization

### 6.1 Codebase Metrics

- **Total Classes/Functions**: ~277 across 54 files
- **Main Entry Point**: `src/riff/cli.py` (945 lines)
- **Test Coverage**: Comprehensive (unit + integration + live)
- **Documentation**: Extensive (docs/ directory with multiple guides)

### 6.2 Code Organization

**Strengths:**
- ✅ Clean module separation
- ✅ XDG-compliant paths (no hardcoded `~/.claude`)
- ✅ Type hints throughout
- ✅ Comprehensive error handling
- ✅ Graceful degradation for optional features

**Structure:**
```
src/riff/
├── cli.py              # Entry point
├── config.py           # XDG configuration
├── backup.py           # Backup system
├── search/             # Semantic search
├── graph/              # DAG analysis
├── surrealdb/          # Database integration
├── classic/            # Original commands
├── enhance/            # AI enhancement
├── tui/                # Interactive UI
└── visualization/      # DAG visualization
```

### 6.3 Best Practices

- ✅ Follows PEP 8 conventions
- ✅ Uses `uv` for modern Python dependency management
- ✅ Task automation with Taskfile
- ✅ Comprehensive test suite
- ✅ Documentation-first approach
- ✅ Educational onboarding (XDG guide)

---

## 7. Testing Infrastructure

### 7.1 Test Organization

**Test Structure:**
```
tests/
├── unit/               # Fast, isolated unit tests
├── integration/        # Integration tests
├── surrealdb/          # Database tests
├── graph/              # DAG module tests
├── fixtures/           # Test data builders
└── sample-data/        # Sample JSONL files
```

### 7.2 Test Types

**Unit Tests:**
- Core search functionality
- Visualization formatters
- Handler logic

**Integration Tests:**
- Search workflow
- Visualization pipeline
- SurrealDB sync

**Live Tests:**
- Qdrant connectivity
- Real search queries
- End-to-end workflows

**Test Markers:**
- `@pytest.mark.unit` - Fast, isolated
- `@pytest.mark.integration` - External services
- `@pytest.mark.live` - Read-only live Qdrant
- `@pytest.mark.require_qdrant` - Requires Qdrant
- `@pytest.mark.slow` - Tests >5s

### 7.3 Test Execution

**Commands:**
```bash
task test:all           # Full suite
task test:unit         # Unit tests only
task test:integration  # Integration tests
task test:coverage     # With coverage report
```

---

## 8. Documentation

### 8.1 Documentation Structure

**Getting Started:**
- `README.md` - Project overview
- `QUICK_REFERENCE.md` - One-page cheat sheet
- `docs/QUICK_START.md` - 5-minute setup
- `docs/START_HERE.md` - Exploration guide

**Architecture:**
- `docs/ARCHITECTURE.md` - System design
- `docs/XDG_ONBOARDING_GUIDE.md` - 4,500-word XDG guide
- `docs/development.md` - Development setup

**Reference:**
- `docs/api-reference.mdx` - API documentation
- `docs/jsonl-specification.mdx` - Data format spec
- `docs/examples.mdx` - Usage examples

**Module-Specific:**
- `src/riff/graph/README.md` - Graph module
- `src/riff/surrealdb/README.md` - SurrealDB integration
- Multiple quick-start guides per module

### 8.2 Documentation Quality

**Strengths:**
- ✅ Comprehensive coverage
- ✅ Multiple entry points (quick-start, deep-dive)
- ✅ Code examples throughout
- ✅ Architecture diagrams
- ✅ Educational content (XDG guide)

**Areas for Improvement:**
- Could benefit from API documentation generation (Sphinx/MkDocs)
- Some older docs in `_archive/` could be cleaned up

---

## 9. Strengths

### 9.1 Architecture

1. **XDG Compliance**: Teaching-first design with educational onboarding
2. **Modular Design**: Clean separation of concerns
3. **Three-Tier Persistence**: JSONL → SurrealDB → Qdrant
4. **Graceful Degradation**: Works without optional dependencies
5. **Federation Ready**: Process isolation pattern

### 9.2 Code Quality

1. **Type Safety**: Type hints throughout
2. **Error Handling**: Comprehensive exception handling
3. **Testing**: Multi-level test coverage
4. **Documentation**: Extensive and well-organized
5. **Modern Tooling**: `uv`, `ruff`, `pytest`

### 9.3 User Experience

1. **Educational**: XDG guide teaches best practices
2. **Safe Operations**: Automatic backups before modifications
3. **Rich Output**: Color-formatted terminal output
4. **Flexible**: Multiple search modes and filters
5. **Integration**: Works with NabiOS federation

---

## 10. Areas for Improvement

### 10.1 Code Organization

1. **Archive Cleanup**: `_archive/` and `archive/` contain old docs that could be consolidated
2. **Documentation Consolidation**: Some duplicate documentation across multiple files
3. **Test Organization**: Could benefit from clearer test categorization

### 10.2 Features

1. **TUI Completion**: TUI module still in development
2. **Binary Distribution**: v2.1.0 planned but not yet implemented
3. **CI/CD**: No automated testing/CI pipeline visible
4. **Windows Support**: Limited Windows testing/optimization

### 10.3 Technical Debt

1. **Legacy Code**: Some older implementations in `_ORIGINAL_TUI_/`
2. **Path Hardcoding**: Some remaining hardcoded paths (mostly fixed in v2.0)
3. **Dependency Management**: Could benefit from dependency pinning

---

## 11. Recommendations

### 11.1 Immediate (High Priority)

1. **Complete TUI Module**: Finish Week 2 TUI implementation
2. **CI/CD Pipeline**: Set up GitHub Actions for automated testing
3. **Archive Cleanup**: Consolidate or remove old documentation
4. **Test Coverage**: Aim for >80% coverage (add coverage reporting)

### 11.2 Short-Term (v2.1.0)

1. **Binary Distribution**: Implement PyInstaller single-binary
2. **Homebrew Formula**: Package for easy installation
3. **API Documentation**: Generate from docstrings (Sphinx/MkDocs)
4. **Performance Testing**: Add benchmarks for search operations

### 11.3 Long-Term (v2.2.0+)

1. **Rust Integration**: Plan for Phase 7+ Rust CLI integration
2. **Windows Optimization**: Full Windows support with .exe
3. **Auto-Update**: Implement update mechanism
4. **Plugin System**: Extensibility for custom backends

---

## 12. Key Metrics Summary

| Metric | Value |
|--------|-------|
| **Version** | 2.0.0 |
| **Python Version** | 3.13+ |
| **Total Modules** | 13 core modules |
| **Classes/Functions** | ~277 |
| **Test Files** | 29+ test files |
| **Documentation Files** | 50+ markdown files |
| **Dependencies** | 6 core + 2 optional |
| **Docker Services** | 1 (Qdrant) |
| **Status** | Production (Search), Dev (TUI) |

---

## 13. Conclusion

**Riff CLI** is a **well-architected, production-ready tool** with:

- ✅ **Strong Foundation**: XDG-compliant, modular architecture
- ✅ **Comprehensive Features**: Search, repair, visualization, sync
- ✅ **Excellent Documentation**: Multiple entry points, educational content
- ✅ **Quality Code**: Type hints, tests, modern tooling
- ✅ **Ecosystem Integration**: NabiOS federation ready

**Primary Strengths:**
1. Educational design (XDG onboarding)
2. Three-tier persistence architecture
3. Comprehensive testing infrastructure
4. Well-documented codebase

**Primary Opportunities:**
1. Complete TUI module
2. Add CI/CD pipeline
3. Binary distribution (v2.1.0)
4. Archive cleanup

**Overall Assessment**: **Production-ready** for search and repair functionality, with clear roadmap for TUI completion and binary distribution.

---

## 14. Next Steps

1. **Review TUI Implementation**: Check progress on Week 2 TUI module
2. **Set Up CI/CD**: Configure GitHub Actions for automated testing
3. **Plan v2.1.0**: Prepare for binary distribution release
4. **Archive Cleanup**: Consolidate old documentation
5. **Performance Testing**: Add benchmarks for search operations

---

**Analysis Complete** ✅

For questions or deeper dives into specific modules, refer to:
- `docs/ARCHITECTURE.md` - System design
- `docs/START_HERE.md` - Exploration guide
- `QUICK_REFERENCE.md` - Quick lookup



