# Riff CLI Codebase Catalog - Complete Index

## Quick Navigation

This catalog provides a complete understanding of the Riff CLI v2.0 codebase structure, features, and dependencies.

### Start Here

1. **RIFF_CLI_BUILD_SUMMARY.md** - Executive overview and architecture
   - High-level system design
   - Feature group breakdown
   - Technology stack
   - Workflow examples
   - Key statistics

2. **MODULE_INVENTORY.md** - Detailed module catalog
   - 56 modules organized by purpose
   - Key components and functions for each
   - Dependencies and related documentation
   - Test coverage summary
   - Status (new/enhanced/maintained/core)

3. **FEATURE_GROUPS.json** - Structured feature organization
   - 8 feature groups with descriptions
   - Module mappings
   - Key features per group
   - Dependency layer hierarchy
   - Machine-readable format for integration

4. **MODULE_RELATIONSHIPS.md** - Technical dependency analysis
   - Dependency graphs and flows
   - Command execution flows
   - Import dependencies by layer
   - No circular import detection
   - XDG configuration paths

---

## What Was Built: Feature Summary

### Search & Retrieval (Mature)
- **Modules**: `search/`, `enhance/`, `manifest_adapter.py`
- **Capabilities**: Qdrant vector search, intent enhancement, index validation
- **Status**: Production-ready

### Graph Analysis & Repair (Mature)
- **Modules**: `graph/` (9 modules for DAG, analysis, repair, persistence)
- **Capabilities**: Orphan detection, thread classification, heuristic repair suggestions
- **Status**: Core functionality, stable

### Deduplication (New)
- **Modules**: `classic/duplicate_handler.py`, dedup commands
- **Capabilities**: Production-grade duplicate tool_result removal, graceful error handling
- **Status**: New feature in v2.0

### Data Persistence (New - Phase 6B)
- **Modules**: `surrealdb/` (4 modules), `memory_producer.py`, `backup.py`
- **Capabilities**: Immutable event sourcing, materialization, federation integration
- **Status**: New in v2.0

### UI & Visualization (Mature)
- **Modules**: `visualization/`, `tui/`, `graph/visualizer.py`, `graph/tui.py`
- **Capabilities**: Vim-style navigation, ASCII trees, riff-dag-tui integration
- **Status**: Mature with v2.0 enhancements

### Infrastructure (Mature)
- **Modules**: `config.py`, `manifest_adapter.py`, `memory_producer.py`, `backup.py`
- **Capabilities**: XDG compliance, telemetry, validation, backups
- **Status**: v2.0 enhanced with single binary support

### Classic Commands (Maintained)
- **Modules**: `classic/` (7 modules)
- **Commands**: scan, fix, tui, graph, fix-with-dedup, scan-with-dupes
- **Status**: Backward compatible, actively maintained

### CLI & Dispatch (Mature)
- **Module**: `cli.py` (main entry point)
- **Commands**: 8+ subcommands dispatched
- **Status**: v2.0 comprehensive command set

---

## Module Organization

### By Layer (Dependency Order)

1. **Core** (0 external dependencies)
   - `graph/models.py` - Foundational dataclasses

2. **I/O Abstractions**
   - `graph/loaders.py` - Storage interface
   - `surrealdb/schema_utils.py` - Schema definitions

3. **Analysis Engines**
   - `graph/dag.py` - Graph construction
   - `graph/analysis.py` - Semantic analysis
   - `graph/repair.py` - Repair suggestions

4. **Search Layer**
   - `search/qdrant.py` - Vector search
   - `enhance/intent.py` - Query enhancement

5. **Persistence**
   - `graph/persistence.py` - JSONL repair writer
   - `surrealdb/storage.py` - Event sourcing

6. **UI/Visualization**
   - `visualization/` (2 modules) - DAG viewer integration
   - `tui/` (3 modules) - Interactive navigation
   - `graph/visualizer.py` - ASCII rendering

7. **Infrastructure**
   - `config.py` - Configuration management
   - `manifest_adapter.py` - Index validation
   - `memory_producer.py` - Telemetry
   - `backup.py` - Backup management

8. **Dispatcher**
   - `cli.py` - Command routing

### By Subdirectory

**src/riff/**
- `__init__.py`, `__main__.py` - Package initialization
- `cli.py` - Main CLI dispatcher
- `config.py` - Configuration loading
- `backup.py` - Backup management
- `manifest_adapter.py` - Index validation
- `memory_producer.py` - Federation telemetry

**src/riff/graph/** (9 modules)
- Core DAG analysis: `models.py`, `loaders.py`, `dag.py`
- Semantic analysis: `analysis.py`
- Repair engine: `repair.py`, `repair_manager.py`
- Persistence: `persistence.py`, `persistence_provider.py`, `persistence_providers.py`
- Visualization: `visualizer.py`, `tui.py`
- Examples/tests: `test_*.py`, `example_*.py`

**src/riff/search/** (3 modules)
- `qdrant.py` - Vector search backend
- `preview.py` - Content preview extraction

**src/riff/enhance/** (2 modules)
- `intent.py` - Intent detection and query enhancement

**src/riff/surrealdb/** (9 modules)
- Core: `storage.py`, `schema_utils.py`
- Utilities: `repair_events_utils.py`, `repair_provider.py`
- Examples: `example_usage.py`, `phase6b_example.py`
- Tests: `test_*.py`

**src/riff/visualization/** (3 modules)
- `handler.py` - riff-dag-tui subprocess management
- `formatter.py` - DAG format conversion

**src/riff/tui/** (4 modules)
- `interface.py` - Abstract TUI interface
- `graph_navigator.py` - Vim-style navigation
- `prompt_toolkit_impl.py` - Optional backend

**src/riff/classic/** (7 modules)
- `__init__.py` - Command exports
- `duplicate_handler.py` - Deduplication engine
- `utils.py` - Shared utilities
- **commands/** (6 modules)
  - `scan.py`, `fix.py`, `tui.py`, `graph.py` - Classic commands
  - `scan_with_duplicates.py`, `fix_with_deduplication.py` - New v2.0 variants

**tests/** (35+ test files)
- Organized by component: graph/, surrealdb/, unit/, integration/
- Feature tests: deduplication, search, persistence, etc.

---

## Key Statistics

| Aspect | Count |
|--------|-------|
| Total Python Files | 56 |
| Core Analysis Modules | 25 |
| Infrastructure Modules | 4 |
| Classic Commands | 7 |
| TUI/Visualization | 6 |
| Test Files | 35+ |
| Test Fixtures | 2 |
| Configuration Files | ~20 docs |
| Lines of Code | ~15,000+ |
| Feature Groups | 8 |

---

## Technology Stack

### Required
- Python 3.13+ (type annotations, modern stdlib)
- Qdrant (vector database)
- sentence-transformers (embeddings)
- Rich (CLI formatting)
- TOML (configuration)
- httpx (HTTP client)
- SurrealDB (immutable event store)

### Optional
- prompt_toolkit (advanced TUI)
- pytest (testing)

---

## How to Use This Catalog

### Understanding the Architecture
1. Start with **RIFF_CLI_BUILD_SUMMARY.md** for the big picture
2. Review **MODULE_RELATIONSHIPS.md** for dependency flows
3. Check **FEATURE_GROUPS.json** for feature mapping

### Finding a Specific Module
1. Use **MODULE_INVENTORY.md** index
2. Search for module name or purpose
3. Check "Related Docs" for detailed documentation

### Understanding Data Flows
1. Reference **MODULE_RELATIONSHIPS.md** command flow sections
2. Trace dependencies from CLI to backend layers
3. Review test files for usage examples

### Extending the System
1. Identify feature group in **FEATURE_GROUPS.json**
2. Find abstract base classes in **MODULE_INVENTORY.md**
3. Check existing implementations for patterns

---

## Notable Design Patterns

### Abstraction Layers
- `ConversationStorage` - Pluggable storage backends
- `ManifestAdapter` - Swappable validation strategies
- `InteractiveTUI` - Multiple TUI implementations
- `PersistenceProvider` - Multiple repair backends

### Error Handling
- `RiffDuplicateHandlingError` - Categorized exceptions
- Graceful degradation in all I/O operations
- Detailed logging for debugging

### Configuration
- XDG Base Directory Specification compliance
- TOML-based with environment variable overrides
- Path expansion and centralized management

### Memory Integration
- `RiffMemoryProducer` - Federation substrate ready
- Event/span/state/metric abstractions
- Structured JSONL logging for Phase 3A

### Testing
- Comprehensive test fixtures
- Unit, integration, and feature tests
- SurrealDB test harness
- Graph algorithm validation

---

## Version History

### v2.0.0 (Current)
- XDG architecture implementation
- Single binary distribution support
- Production-grade deduplication
- Phase 6B event sourcing
- Intent enhancement for search
- Index validation via SHA256 manifest
- Memory substrate integration

### v1.x (Legacy)
- Classic JSONL repair
- Basic semantic search
- ASCII visualization
- TUI navigation

---

## Documentation Cross-Reference

### Core Architecture
- `docs/ARCHITECTURE.md` - System design
- `docs/START_HERE.md` - Getting started
- `docs/PHASE_6B_QUICKSTART.md` - Event sourcing

### Component Documentation
- `docs/GRAPH_MODULE.md` - DAG analysis
- `docs/REPAIR_WORKFLOW.md` - Repair system
- `docs/IMMUTABLE_STORE_ARCHITECTURE.md` - SurrealDB
- `docs/DUPLICATE_HANDLER_ARCHITECTURE.md` - Deduplication
- `docs/VISUALIZER_IMPLEMENTATION.md` - Visualization
- `docs/GRAPH_NAVIGATOR_USAGE.md` - TUI navigation
- `docs/TIME_FILTERING.md` - Filtering features
- `docs/SEMANTIC_ANALYSIS_COMPLETE.md` - Search features

### Integration Guides
- `docs/ROUTING_PATTERN_GUIDE.md` - CLI routing
- `docs/CONSOLIDATED_INDEX_AND_LINK_MAPPER.md` - System mapping
- `docs/PHASE_6C_FEDERATION_INTEGRATION_PLAN.md` - Federation

---

## Support & Maintenance

### Test Coverage
- Graph: DAG construction, repair, thread detection
- SurrealDB: Event sourcing, materialization, sync
- Search: Semantic search, intent detection
- Visualization: Format conversion, TUI handlers
- Deduplication: Detection, validation, error handling

### CI/CD Ready
- 35+ test files
- pytest.ini configuration
- Comprehensive fixtures
- Integration test workflows

### Production Deployment
- XDG-compliant paths
- Error handling and logging
- Backup and recovery systems
- Memory substrate integration

---

**Catalog Generated**: 2025-11-20  
**Riff CLI Version**: 2.0.0  
**Status**: Production-Ready  
**Last Updated**: Latest commit (feature/index-validation-integration)  

For questions about specific modules, see MODULE_INVENTORY.md.  
For architectural questions, see RIFF_CLI_BUILD_SUMMARY.md.  
For dependency analysis, see MODULE_RELATIONSHIPS.md.  
For feature organization, see FEATURE_GROUPS.json.

