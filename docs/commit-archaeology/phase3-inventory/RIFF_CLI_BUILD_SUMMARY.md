# Riff CLI Build Summary

## Overview

Riff CLI is a comprehensive conversation analysis and repair system built in Python with 56 modules across 8 major feature groups. The system handles semantic search, DAG-based conversation repair, deduplication, and immutable event sourcing via SurrealDB.

**Version**: 2.0.0 (XDG Architecture + Single Binary Distribution)  
**Key Technologies**: Python 3.13+, Qdrant, SurrealDB, sentence-transformers, Rich CLI

---

## Architecture Stack (Layered)

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Dispatcher (cli.py)              │
├─────────────────────────────────────────────────────────┤
│  Commands: scan, fix, tui, search, repair, visualize   │
├─────────────────────────────────────────────────────────┤
│            UI Layer (visualization, tui)                │
│     ASCII trees, vim-style nav, DAG viewer              │
├─────────────────────────────────────────────────────────┤
│         Analysis Layer (graph, enhance, search)         │
│  DAG construction, thread detection, intent detection   │
├─────────────────────────────────────────────────────────┤
│    Persistence Layer (surrealdb, graph/persistence)     │
│  Event sourcing, JSONL repair, undo/redo                │
├─────────────────────────────────────────────────────────┤
│   Storage Layer (loaders, models, surrealdb/schema)     │
│  Abstract interfaces, JSONL I/O, type-safe models       │
├─────────────────────────────────────────────────────────┤
│         Infrastructure (config, manifest, memory)       │
│  XDG compliance, index validation, federation bridge    │
└─────────────────────────────────────────────────────────┘
```

---

## Feature Groups Breakdown

### 1. Search & Retrieval (Mature)
Semantic vector search with intelligent query enhancement.

**Key Modules**:
- `search/qdrant.py` - Vector search via Qdrant
- `enhance/intent.py` - Query expansion and intent detection
- `manifest_adapter.py` - Index validation via SHA256 manifest

**Capabilities**:
- Sentence-transformer embeddings
- Intent classification (question, search, debug, optimization, general)
- Keyword expansion patterns
- Index integrity validation with stale entry detection

### 2. Graph Analysis & Repair (Mature)
Core conversation analysis with orphan detection and repair suggestions.

**Key Modules**:
- `graph/models.py` - Type-safe message/thread/session dataclasses
- `graph/dag.py` - DAG construction and graph traversal
- `graph/analysis.py` - Thread detection, corruption scoring (heuristic-based, no ML)
- `graph/repair.py` - Orphan detection and similarity scoring
- `graph/persistence.py` - JSONL repair writing with undo/redo

**Capabilities**:
- Thread classification (main, side discussions, orphaned)
- Corruption metrics (0.0-1.0 scores)
- Similarity heuristics (keyword overlap, temporal proximity, thread context)
- Atomic repair operations with rollback
- Session-scoped undo history

### 3. Deduplication (New - v2.0)
Production-grade duplicate tool_result detection and removal.

**Key Modules**:
- `classic/duplicate_handler.py` - Detection engine with error categorization
- `classic/commands/fix_with_deduplication.py` - Repair command
- `classic/commands/scan_with_duplicates.py` - Analysis command

**Capabilities**:
- Malformation detection
- Partial corruption support (separate valid/invalid blocks)
- OOM protection
- Error categorization with recovery suggestions
- Graceful degradation

### 4. Data Persistence (New - Phase 6B)
Immutable event sourcing with SurrealDB backend.

**Key Modules**:
- `surrealdb/storage.py` - Immutable event logging and session materialization
- `surrealdb/schema_utils.py` - Schema definition and validation
- `memory_producer.py` - Federation memory substrate integration
- `backup.py` - XDG-compliant backup management

**Capabilities**:
- Event replay for point-in-time reconstruction
- Full audit trails of all repairs
- HTTP API integration (no WebSocket overhead)
- Phase 3A memory item production
- Hot-reloadable backup metadata

### 5. UI & Visualization (Mature)
Interactive terminal navigation and DAG visualization.

**Key Modules**:
- `visualization/handler.py` - riff-dag-tui subprocess management
- `tui/graph_navigator.py` - Vim-style navigation
- `graph/visualizer.py` - ASCII tree rendering

**Capabilities**:
- Vim keys: j/k (nav), g/G (ends), f (filter), Enter (open)
- Time-based filtering (1/3/7/30+ days)
- Modular TUI interface design
- DAG format conversion for external viewers

### 6. Infrastructure & Configuration (Mature)
XDG compliance and federation coordination.

**Key Modules**:
- `config.py` - TOML configuration with educational comments
- `manifest_adapter.py` - SHA256 validation
- `memory_producer.py` - Telemetry and lifecycle logging
- `backup.py` - Safe backup with metadata tracking

**Capabilities**:
- XDG Base Directory Specification compliance
- Path expansion and environment variables
- Reindex lifecycle tracking
- Search/validation telemetry

### 7. Classic Commands (Maintained)
Backward-compatible command set.

**Commands**:
- `scan` - Non-destructive analysis
- `fix` - JSONL repair
- `tui` - Interactive navigation
- `graph` - Visualization
- `fix-with-dedup` - Repair + deduplication
- `scan-with-dupes` - Analysis + duplication reporting

### 8. CLI & Dispatching (Mature)
Unified command orchestration.

**Key Module**: `cli.py`

**Commands**:
- `scan` - Analyze structure
- `fix` - Repair JSONL
- `tui` - Navigate interactively
- `search` - Semantic search
- `repair` - Guided repair
- `visualize` - DAG viewer
- `sync-surrealdb` - Sync to database
- `graph` - Generate visualization

---

## Core Module Dependencies

### Dependency Layers

**Layer 1 (Core)**: Models
- `graph/models.py` - Foundational dataclasses

**Layer 2 (I/O)**: Storage abstraction
- `graph/loaders.py` - Abstract storage interface
- `graph/persistence.py` - Repair writing

**Layer 3 (Analysis)**: Semantic processing
- `graph/dag.py` - Graph construction
- `graph/analysis.py` - Semantic analysis
- `graph/repair.py` - Repair engine

**Layer 4 (Search)**: Discovery
- `search/qdrant.py` - Vector search
- `enhance/intent.py` - Query enhancement

**Layer 5 (Persistence)**: Database
- `surrealdb/storage.py` - Event store
- `surrealdb/schema_utils.py` - Schema management

**Layer 6 (UI)**: Presentation
- `visualization/handler.py` - External viewer
- `tui/graph_navigator.py` - Interactive UI

**Layer 7 (Infrastructure)**: System integration
- `config.py` - Configuration
- `manifest_adapter.py` - Validation
- `memory_producer.py` - Telemetry

**Layer 8 (Dispatch)**: CLI orchestration
- `cli.py` - Command routing

### Cross-Cutting Concerns

**Error Handling**:
- `classic/duplicate_handler.py` - Graceful corruption handling
- All modules use logging for structured output

**Backup & Recovery**:
- `graph/persistence.py` - Undo/redo
- `backup.py` - XDG-compliant backups

**Testing**:
- 35+ test files covering all major components
- Graph, SurrealDB, search, visualization, deduplication

---

## New Features in v2.0

### Infrastructure Enhancements
1. **XDG Architecture**: Unified configuration at `~/.config/nabi/riff.toml`
2. **Index Validation**: SHA256 manifest checking for Qdrant integrity
3. **Backup System**: Hot-reloadable metadata at `~/.local/state/nabi/riff/`
4. **Memory Integration**: Federation-ready telemetry via SurrealDB substrate

### Feature Additions
1. **Deduplication**: Production-grade duplicate tool_result removal
2. **Intent Enhancement**: Query keyword expansion and intent classification
3. **Event Sourcing**: Full immutable repair event logging
4. **Binary Distribution**: Single executable with XDG paths

### Visualization Improvements
1. **riff-dag-tui Integration**: Subprocess lifecycle management
2. **DAG Format Converter**: JSONL transformation for external viewers
3. **Unified CLI**: Integrated search, repair, and visualization

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Python Modules | 56 |
| Core Analysis Modules | 25 |
| Infrastructure Modules | 4 |
| Classic Commands | 7 |
| TUI/Visualization | 6 |
| Test Files | 35+ |
| Lines of Code | ~15,000+ |
| Documentation Files | 20+ |

---

## Technology Stack

### Core Dependencies
- **Python 3.13+**: Type annotations, modern stdlib
- **Qdrant**: Vector database (semantic search)
- **SurrealDB**: Document/graph database (immutable events)
- **sentence-transformers**: Embedding models
- **Rich**: Terminal formatting
- **TOML**: Configuration files
- **httpx**: HTTP API client

### Optional Dependencies
- **prompt_toolkit**: Advanced TUI features
- **pytest**: Testing framework

---

## How Features Work Together

### Search Workflow
1. **User Query** → CLI dispatcher
2. **Intent Enhancement** → Keyword expansion
3. **Qdrant Search** → Vector similarity
4. **Content Preview** → Snippet extraction
5. **Memory Producer** → Telemetry logging

### Repair Workflow
1. **Session Load** → JSONLLoader
2. **DAG Construction** → ConversationDAG
3. **Thread Detection** → ThreadDetector
4. **Orphan Identification** → CorruptionScorer
5. **Repair Suggestion** → RepairEngine (heuristic similarity)
6. **Operator Review** → Interactive repair manager
7. **Atomic Write** → JSONLRepairWriter
8. **Event Log** → SurrealDBStorage (immutable)
9. **Backup** → XDG backup system
10. **Undo Ready** → RepairSnapshot history

### Visualization Workflow
1. **Session Load** → JSONLLoader
2. **DAG Build** → ConversationDAG
3. **ASCII Render** → ConversationTreeVisualizer (optional)
4. **Format Convert** → convert_to_dag_format
5. **Launch Viewer** → riff-dag-tui subprocess
6. **Interactive Explore** → vim-style navigation

---

## Extensibility Points

### Abstract Base Classes
- `ConversationStorage` → Pluggable storage backends
- `ManifestAdapter` → Custom validation strategies
- `InteractiveTUI` → Alternative TUI implementations
- `PersistenceProvider` → Multiple repair backends

### Configuration
- XDG paths fully customizable in `riff.toml`
- Embedding models selectable
- Environment variable overrides supported

### Integration Hooks
- Memory substrate integration (Phase 3A ready)
- SurrealDB sync via `cmd_sync_surrealdb()`
- Plugin-ready command structure in `cli.py`

---

## Known Limitations & Future Work

### Current Scope
- No ML-based repair suggestions (heuristics only)
- SurrealDB integration in Phase 6B (not yet canonical)
- Manual operator review required for repairs

### Planned Enhancements
- System-wide manifest integration (when available)
- Multi-model embedding support
- Advanced repair batching
- Real-time sync with federation

---

## Documentation Resources

**Core Architecture**: `docs/ARCHITECTURE.md`  
**Quick Start**: `docs/START_HERE.md`, `docs/PHASE_6B_QUICKSTART.md`  
**Repair Workflow**: `docs/REPAIR_WORKFLOW.md`  
**Graph Analysis**: `docs/GRAPH_MODULE.md`  
**Visualization**: `docs/VISUALIZER_IMPLEMENTATION.md`, `docs/GRAPH_NAVIGATOR_USAGE.md`  
**SurrealDB**: `docs/IMMUTABLE_STORE_ARCHITECTURE.md`  
**Deduplication**: `docs/DUPLICATE_HANDLER_ARCHITECTURE.md`  

---

## Summary

Riff CLI v2.0 is a mature, production-ready system for analyzing Claude conversations and repairing JSONL corruption. It combines semantic search, graph-based repair suggestions, immutable event logging, and interactive visualization into a cohesive tool. The XDG architecture enables portable configuration, and the federation integration points prepare it for broader system coordination.

**Status**: Production-ready for conversation analysis and repair  
**Maturity**: Core features stable; new features (Phase 6B, deduplication) comprehensive  
**Integration**: Ready for federation memory substrate and system-wide manifest  

