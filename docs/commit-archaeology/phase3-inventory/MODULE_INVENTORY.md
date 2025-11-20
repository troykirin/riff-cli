# Riff CLI Module Inventory

## Core Infrastructure Modules

### Configuration & Management

#### Module: config.py
- **Path**: `src/riff/config.py`
- **Purpose**: XDG Base Directory Specification configuration loading from ~/.config/nabi/riff.toml
- **Scope**: Medium (core infrastructure)
- **Key Components**: 
  - `get_config()`: Get global config instance
  - `RiffConfig`: Configuration dataclass
  - Default config template with educational comments
- **Dependencies**: toml, pathlib, os, typing
- **Related Docs**: ARCHITECTURE.md, docs/START_HERE.md
- **Status**: Enhanced (v2.0 - XDG architecture)

#### Module: manifest_adapter.py
- **Path**: `src/riff/manifest_adapter.py`
- **Purpose**: Pluggable interface for checking if reindex is needed via SHA256 manifest hashing
- **Scope**: Medium (infrastructure for index validation)
- **Key Components**:
  - `ManifestAdapter`: Abstract base class
  - `LocalManifestAdapter`: SHA256-based manifest implementation
  - `get_manifest_adapter()`: Factory function
- **Key Methods**:
  - `needs_reindex()`: Check if projects directory changed
  - `validate_index_integrity()`: Detect stale Qdrant entries
  - `save_manifest()`: Store manifest for comparison
- **Dependencies**: hashlib, json, datetime, pathlib
- **Related Docs**: PHASE_6B_QUICKSTART.md, docs/ARCHITECTURE.md
- **Status**: New (v2.0 - index validation integration)

#### Module: backup.py
- **Path**: `src/riff/backup.py`
- **Purpose**: Safe backup system using XDG directories for conversation file protection
- **Scope**: Medium (data protection)
- **Key Components**:
  - `get_backup_metadata_path()`: Get backup index location
  - `load_backup_index()`: Load backup metadata
  - Backup storage in ~/.local/share/nabi/riff/backups/
- **Dependencies**: pathlib, datetime, json, shutil, os
- **Related Docs**: BINARY_RELEASE_CHECKLIST.md
- **Status**: New (v2.0 - XDG backup system)

#### Module: memory_producer.py
- **Path**: `src/riff/memory_producer.py`
- **Purpose**: SurrealDB Memory Substrate integration producing memory:item records
- **Scope**: Medium (federation memory coordination)
- **Key Components**:
  - `RiffMemoryProducer`: Producer for TimeSliced MemoryItems
  - `get_memory_producer()`: Singleton accessor
  - Event/span/state/metric logging methods
- **Key Methods**:
  - `log_event()`, `log_span()`, `log_state()`, `log_metric()`: Core logging
  - `log_reindex_started/completed()`: Reindex lifecycle
  - `log_validation_failed()`: Index validation events
  - `log_search_performed()`: Search telemetry
- **Dependencies**: json, datetime, uuid, pathlib, typing
- **Related Docs**: IMMUTABLE_STORE_ARCHITECTURE.md, PHASE_6B_QUICKSTART.md
- **Status**: New (Phase 3A memory integration)

### CLI & Commands

#### Module: cli.py
- **Path**: `src/riff/cli.py`
- **Purpose**: Unified riff CLI dispatcher (search conversations + repair JSONL)
- **Scope**: Large (main entry point)
- **Key Commands**:
  - `cmd_scan()`: Analyze conversation structure
  - `cmd_fix()`: Repair JSONL corruption
  - `cmd_tui()`: Interactive TUI navigation
  - `cmd_graph()`: Graph visualization
  - `cmd_visualize()`: DAG viewer (riff-dag-tui)
  - `cmd_sync_surrealdb()`: Sync to SurrealDB
  - `cmd_search()`: Search with Qdrant + intent enhancement
  - `cmd_repair()`: Repair individual sessions
- **Dependencies**: argparse, pathlib, rich, all submodules
- **Related Docs**: docs/usage.md, ARCHITECTURE.md
- **Status**: Enhanced (v2.0 - comprehensive CLI)

---

## Graph & Analysis Modules

### Data Models

#### Module: models.py
- **Path**: `src/riff/graph/models.py`
- **Purpose**: Type-safe dataclasses for DAG representation
- **Scope**: Small (data structures)
- **Key Components**:
  - `MessageType`: Enum (user, assistant, system, summary, file-history-snapshot)
  - `ThreadType`: Enum (main, side_discussion, orphaned)
  - `Message`: Message dataclass with uuid, parent_uuid, type, content, etc.
  - `Thread`: Thread grouping
  - `Session`: Session container
- **Dependencies**: dataclasses, typing, enum
- **Related Docs**: GRAPH_MODULE.md
- **Status**: Core (stable, extended types)

### Storage & Loading

#### Module: loaders.py
- **Path**: `src/riff/graph/loaders.py`
- **Purpose**: Abstract storage interface + JSONL loader for Claude conversations
- **Scope**: Medium (I/O abstraction)
- **Key Components**:
  - `ConversationStorage`: Abstract base class
  - `JSONLLoader`: Concrete JSONL implementation
- **Key Methods**:
  - `load_messages()`: Load session from JSONL
  - `save_session()`: Persist session
  - `update_message()`: Update single message
- **Dependencies**: json, abc, pathlib, models
- **Related Docs**: ARCHITECTURE.md
- **Status**: Core (stable)

### Graph Construction & Analysis

#### Module: dag.py
- **Path**: `src/riff/graph/dag.py`
- **Purpose**: Build directed acyclic graph from messages, identify threads and orphans
- **Scope**: Medium (core graph ops)
- **Key Components**:
  - `ConversationDAG`: Main DAG builder
  - Adjacency list construction
  - Thread detection integration
- **Key Methods**:
  - `_build_graph()`: Construct parent-child relationships
  - `identify_threads()`: Find all threads
  - `detect_orphans()`: Find disconnected messages
  - `compute_corruption_metrics()`: Health scoring
- **Dependencies**: typing, collections, models, loaders, analysis
- **Related Docs**: GRAPH_MODULE.md, REPAIR_WORKFLOW.md
- **Status**: Core (stable)

#### Module: analysis.py
- **Path**: `src/riff/graph/analysis.py`
- **Purpose**: Semantic analysis without ML (thread detection, corruption scoring)
- **Scope**: Medium (semantic heuristics)
- **Key Components**:
  - `ThreadDetector`: Identify main/side/orphaned threads
  - `CorruptionScorer`: Compute message health metrics
  - `SemanticAnalyzer`: Keyword/temporal pattern analysis
  - Helper functions: `analyze_session_semantics()`, `detect_orphans_with_scoring()`
- **Key Methods**:
  - `identify_threads()`: Thread classification
  - `score_message()`: Corruption measurement
  - `extract_semantic_topic()`: Topic classification
- **Dependencies**: logging, re, collections, typing, models
- **Related Docs**: REPAIR_WORKFLOW.md, SEMANTIC_RELATIONSHIP_DIAGRAM.md
- **Status**: Core (stable with enhancements)

#### Module: repair.py
- **Path**: `src/riff/graph/repair.py`
- **Purpose**: Repair engine for detecting/fixing orphaned messages
- **Scope**: Medium (repair heuristics)
- **Key Components**:
  - `RepairDiff`: Before/after state display
  - `ParentCandidate`: Potential parent for orphan
  - `RepairOperation`: Repair suggestion with similarity score
  - `RepairEngine`: Main repair coordinator
- **Key Methods**:
  - `suggest_repairs()`: Generate repair operations
  - `validate_repair()`: Circular dependency checks
  - `generate_repair_diff()`: Display changes
  - `_compute_similarity()`: Heuristic scoring (keyword, temporal, thread)
- **Dependencies**: logging, dataclasses, datetime, typing, models, analysis
- **Related Docs**: REPAIR_WORKFLOW.md, DUPLICATE_HANDLER_ARCHITECTURE.md
- **Status**: Core (stable)

#### Module: repair_manager.py
- **Path**: `src/riff/graph/repair_manager.py`
- **Purpose**: High-level repair coordination with operator feedback
- **Scope**: Medium (repair workflow)
- **Key Components**:
  - `RepairManager`: Orchestrates repair operations
- **Key Methods**:
  - `interactive_repair()`: User-guided repair flow
  - `batch_repair()`: Programmatic repair
- **Dependencies**: models, repair, loaders, persistence
- **Related Docs**: REPAIR_WORKFLOW.md
- **Status**: Core (stable)

### Visualization

#### Module: visualizer.py
- **Path**: `src/riff/graph/visualizer.py`
- **Purpose**: ASCII tree visualization of conversation DAG
- **Scope**: Small (display formatting)
- **Key Components**:
  - `LineItem`: Single visual line
  - `ConversationTreeVisualizer`: ASCII renderer
  - Helper: `visualize_session()`, `flatten_session_for_navigation()`
- **Key Methods**:
  - `visualize()`: Render tree
  - `flatten()`: Convert to linear list
- **Dependencies**: models, dag, typing
- **Related Docs**: VISUALIZER_IMPLEMENTATION.md
- **Status**: Core (stable)

#### Module: tui.py
- **Path**: `src/riff/graph/tui.py`
- **Purpose**: Interactive terminal UI for navigating conversation DAG
- **Scope**: Medium (TUI interaction)
- **Key Components**:
  - `ConversationGraphNavigator`: Vim-style navigation (j/k/g/G)
- **Key Methods**:
  - `navigate()`: Main interaction loop
  - `show_session()`: Display selected session
  - `apply_filter()`: Time-based filtering
- **Dependencies**: models, visualizer, loaders, typing, prompt_toolkit (optional)
- **Related Docs**: GRAPH_NAVIGATOR_USAGE.md, TIME_FILTERING.md
- **Status**: Enhanced (v2.0)

### Persistence & Repair Writing

#### Module: persistence.py
- **Path**: `src/riff/graph/persistence.py`
- **Purpose**: JSONL repair writer with undo/rollback capabilities
- **Scope**: Medium (repair I/O)
- **Key Components**:
  - `RepairOperation`: Operation record (message_uuid, field, old/new value)
  - `RepairSnapshot`: Session repair state
  - `JSONLRepairWriter`: Atomic JSONL updates
  - `create_repair_writer()`: Factory
- **Key Methods**:
  - `write_repair()`: Apply single repair
  - `write_repairs()`: Batch repairs
  - `undo()`, `redo()`: Repair history
  - `create_backup()`: Pre-repair backup
- **Dependencies**: json, logging, os, shutil, dataclasses, datetime, pathlib, loaders
- **Related Docs**: REPAIR_WORKFLOW.md
- **Status**: Core (stable)

#### Module: persistence_provider.py / persistence_providers.py
- **Path**: `src/riff/graph/persistence_provider.py`, `persistence_providers.py`
- **Purpose**: Abstract providers for different storage backends
- **Scope**: Small (abstraction layer)
- **Key Components**:
  - `PersistenceProvider`: Abstract interface
  - Concrete implementations (JSONL, SurrealDB-ready)
- **Dependencies**: abc, typing, models
- **Related Docs**: ARCHITECTURE.md
- **Status**: Core (abstraction)

---

## Search & Retrieval Modules

### Semantic Search

#### Module: search/qdrant.py
- **Path**: `src/riff/search/qdrant.py`
- **Purpose**: Vector semantic search using Qdrant + sentence-transformers
- **Scope**: Medium (search backend)
- **Key Components**:
  - `SearchResult`: Search hit dataclass
  - `QdrantSearcher`: Main search interface
- **Key Methods**:
  - `search()`: Semantic vector search
  - `index_session()`: Add session to index
  - `reindex_all()`: Bulk indexing
  - `delete_session()`: Remove from index
- **Dependencies**: qdrant_client, sentence_transformers, dataclasses, datetime, pathlib, config
- **Related Docs**: SEMANTIC_ANALYSIS_COMPLETE.md
- **Status**: Core (stable)

#### Module: search/preview.py
- **Path**: `src/riff/search/preview.py`
- **Purpose**: Content preview extraction from search results
- **Scope**: Small (display formatting)
- **Key Components**:
  - `ContentPreview`: Preview dataclass
- **Key Methods**:
  - `extract_preview()`: Get text snippet
  - `highlight_matches()`: Keyword emphasis
- **Dependencies**: pathlib, loaders
- **Related Docs**: docs/usage.md
- **Status**: Core (stable)

### Intent Enhancement

#### Module: enhance/intent.py
- **Path**: `src/riff/enhance/intent.py`
- **Purpose**: Query enhancement with keyword expansion and intent detection
- **Scope**: Small (search enhancement)
- **Key Components**:
  - `IntentEnhancer`: Query processor
  - Pattern mapping (memory, federation, search, bug, riff, performance)
- **Key Methods**:
  - `enhance_query()`: Keyword expansion
  - `detect_intent()`: Intent classification (question, search, debug, optimization, general)
  - `suggest_filters()`: Intent-based filter recommendations
- **Dependencies**: re
- **Related Docs**: SEMANTIC_ANALYSIS_COMPLETE.md
- **Status**: New (v2.0 - recursive intent-driven search)

---

## Database & Persistence Modules

### SurrealDB Integration

#### Module: surrealdb/schema_utils.py
- **Path**: `src/riff/surrealdb/schema_utils.py`
- **Purpose**: SurrealDB schema definition and validation utilities
- **Scope**: Medium (schema management)
- **Key Components**:
  - `SCHEMA_DICT`: Complete schema definition
  - `get_schema_sql()`: Generate SQL for table creation
  - Validation: `validate_session_data()`, `validate_message_data()`, `validate_thread_data()`
  - Preparation: `prepare_session_record()`, `prepare_message_record()`, `prepare_thread_record()`
  - Query builders: `build_orphaned_messages_query()`, `build_session_stats_query()`, etc.
- **Dependencies**: typing, json, dataclasses
- **Related Docs**: IMMUTABLE_STORE_ARCHITECTURE.md, SURREALDB_INTEGRATION_ANALYSIS.md
- **Status**: New (Phase 6B - immutable event store)

#### Module: surrealdb/storage.py
- **Path**: `src/riff/surrealdb/storage.py`
- **Purpose**: SurrealDB storage with immutable repair event logging
- **Scope**: Large (core persistence)
- **Key Components**:
  - `SurrealDBStorage`: Main storage interface
  - `RepairEvent`: Immutable repair event dataclass
  - Custom Exceptions: `SurrealDBConnectionError`, `RepairEventValidationError`, `SessionNotFoundError`, `MaterializationError`
  - `create_surrealdb_storage()`: Factory
- **Key Methods**:
  - `store_session()`: Save conversation
  - `log_repair_event()`: Immutable event append
  - `materialize_session()`: Rebuild from events
  - `get_session_timeline()`: Replay history
  - HTTP API integration (no WebSocket)
- **Dependencies**: json, logging, uuid, dataclasses, datetime, pathlib, typing, urllib, httpx, models, loaders, schema_utils
- **Related Docs**: IMMUTABLE_STORE_ARCHITECTURE.md, IMMUTABLE_STORE_VISUAL_SUMMARY.md, PHASE_6B_QUICKSTART.md
- **Status**: New (Phase 6B - immutable event sourcing)

#### Module: surrealdb/repair_provider.py
- **Path**: `src/riff/surrealdb/repair_provider.py`
- **Purpose**: SurrealDB repair provider for Phase 6B integration
- **Scope**: Medium (repair interface)
- **Key Components**:
  - `SurrealDBRepairProvider`: Repair backend implementation
- **Key Methods**:
  - `suggest_repairs()`: Query repair candidates
  - `apply_repair()`: Log repair event
- **Dependencies**: surrealdb modules, graph modules, typing
- **Related Docs**: PHASE_6B_QUICKSTART.md
- **Status**: New (Phase 6B)

#### Module: surrealdb/repair_events_utils.py
- **Path**: `src/riff/surrealdb/repair_events_utils.py`
- **Purpose**: Utilities for repair event handling
- **Scope**: Small (helper functions)
- **Dependencies**: json, typing, models
- **Related Docs**: IMMUTABLE_STORE_ARCHITECTURE.md
- **Status**: New (Phase 6B)

---

## Visualization & UI Modules

### Interactive Visualization

#### Module: visualization/handler.py
- **Path**: `src/riff/visualization/handler.py`
- **Purpose**: Subprocess lifecycle manager for riff-dag-tui (Rust DAG viewer)
- **Scope**: Small (subprocess management)
- **Key Components**:
  - `RiffDagTUIHandler`: Binary discovery and subprocess launcher
- **Key Methods**:
  - `_discover_binary()`: Find riff-dag-tui in standard locations
  - `verify_installed()`: Check binary availability
  - `launch()`: Spawn subprocess with JSONL
  - `get_installation_hint()`: Help message
- **Dependencies**: subprocess, shutil, pathlib, typing, rich
- **Related Docs**: VISUALIZER_IMPLEMENTATION.md
- **Status**: New (v2.0 - unified visualization)

#### Module: visualization/formatter.py
- **Path**: `src/riff/visualization/formatter.py`
- **Purpose**: Convert graph data to riff-dag-tui input format
- **Scope**: Small (data transformation)
- **Key Components**:
  - `convert_to_dag_format()`: Transform to DAG format
  - `write_temp_jsonl()`: Write formatted JSONL
- **Dependencies**: pathlib, json, typing, tempfile, models
- **Related Docs**: VISUALIZER_IMPLEMENTATION.md
- **Status**: New (v2.0)

### Terminal UI

#### Module: tui/interface.py
- **Path**: `src/riff/tui/interface.py`
- **Purpose**: Abstract TUI interface for modular implementations
- **Scope**: Small (abstraction)
- **Key Components**:
  - `InteractiveTUI`: Abstract base class
  - `NavigationResult`: Navigation result dataclass
  - `TUIConfig`: Configuration
- **Key Methods**: `navigate()`, `update_results()`, `show_filter_prompt()`, `display_session()`, `is_active()`
- **Dependencies**: abc, dataclasses, typing
- **Related Docs**: GRAPH_NAVIGATOR_USAGE.md
- **Status**: Core (stable abstraction)

#### Module: tui/graph_navigator.py
- **Path**: `src/riff/tui/graph_navigator.py`
- **Purpose**: Vim-style graph navigation UI
- **Scope**: Medium (interactive navigation)
- **Key Components**:
  - `ConversationGraphNavigator`: Main navigator
- **Key Methods**:
  - `navigate()`: Interactive loop
  - Vim keys: j (down), k (up), g (top), G (bottom), f (filter), Enter (open)
- **Dependencies**: interface, models, visualizer, loaders, typing
- **Related Docs**: GRAPH_NAVIGATOR_USAGE.md, TIME_FILTERING.md
- **Status**: Core (stable)

#### Module: tui/prompt_toolkit_impl.py
- **Path**: `src/riff/tui/prompt_toolkit_impl.py`
- **Purpose**: Optional prompt_toolkit-based TUI implementation
- **Scope**: Small (alternative backend)
- **Dependencies**: prompt_toolkit (optional)
- **Related Docs**: GRAPH_NAVIGATOR_USAGE.md
- **Status**: Optional

---

## Classic Commands (Legacy Support)

### Repair & Analysis Commands

#### Module: classic/commands/fix.py
- **Path**: `src/riff/classic/commands/fix.py`
- **Purpose**: Repair JSONL files fixing parent references and structure
- **Scope**: Medium (legacy repair)
- **Key Methods**: `cmd_fix()` entry point
- **Dependencies**: graph, persistence, models, loaders
- **Related Docs**: REPAIR_WORKFLOW.md
- **Status**: Maintained (backward compatibility)

#### Module: classic/commands/scan.py
- **Path**: `src/riff/classic/commands/scan.py`
- **Purpose**: Analyze conversation structure without modifications
- **Scope**: Medium (analysis)
- **Key Methods**: `cmd_scan()` entry point
- **Dependencies**: graph, models, loaders
- **Related Docs**: docs/usage.md
- **Status**: Maintained

#### Module: classic/commands/tui.py
- **Path**: `src/riff/classic/commands/tui.py`
- **Purpose**: Launch interactive TUI navigator
- **Scope**: Small (UI dispatcher)
- **Key Methods**: `cmd_tui()` entry point
- **Dependencies**: tui, loaders
- **Related Docs**: GRAPH_NAVIGATOR_USAGE.md
- **Status**: Maintained

#### Module: classic/commands/graph.py
- **Path**: `src/riff/classic/commands/graph.py`
- **Purpose**: Generate graph visualization
- **Scope**: Small (visualization)
- **Key Methods**: `cmd_graph()` entry point
- **Dependencies**: graph, visualizer
- **Related Docs**: VISUALIZER_IMPLEMENTATION.md
- **Status**: Maintained

### Deduplication Commands

#### Module: classic/commands/fix_with_deduplication.py
- **Path**: `src/riff/classic/commands/fix_with_deduplication.py`
- **Purpose**: Fix JSONL with duplicate tool_result removal
- **Scope**: Medium (deduplication)
- **Key Methods**: Integration with duplicate_handler
- **Dependencies**: duplicate_handler, fix
- **Related Docs**: DUPLICATE_TOOL_RESULT_IMPLEMENTATION_GUIDE.md
- **Status**: New (deduplication feature)

#### Module: classic/commands/scan_with_duplicates.py
- **Path**: `src/riff/classic/commands/scan_with_duplicates.py`
- **Purpose**: Scan and report duplicate tool_result blocks
- **Scope**: Medium (analysis)
- **Key Methods**: `cmd_scan()` variant
- **Dependencies**: duplicate_handler, scan
- **Related Docs**: DUPLICATE_TOOL_RESULT_IMPLEMENTATION_GUIDE.md
- **Status**: New (deduplication feature)

### Deduplication Utilities

#### Module: classic/duplicate_handler.py
- **Path**: `src/riff/classic/duplicate_handler.py`
- **Purpose**: Production-grade duplicate tool_result detection and removal
- **Scope**: Medium (error handling)
- **Key Components**:
  - `DuplicateDetectionErrorType`: Error categorization enum
  - `ValidationResult`: Block validation result
  - `DuplicateDetectionMetrics`: Metrics tracking
  - `DeduplicationResult`: Operation result
  - `RiffDuplicateHandlingError`: Base exception
  - Helper functions: `detect_duplicate_tool_results()`, `remove_duplicate_tool_results()`, etc.
- **Key Methods**:
  - `detect_duplicates()`: Identify duplicate blocks
  - `remove_duplicates()`: Safe removal with recovery
  - `_validate_block()`: Malformation detection
- **Features**: Graceful error handling, partial corruption support, OOM protection, detailed logging
- **Dependencies**: logging, json, dataclasses, typing, collections, enum
- **Related Docs**: DUPLICATE_HANDLER_ARCHITECTURE.md, DUPLICATE_TOOL_RESULT_IMPLEMENTATION_GUIDE.md
- **Status**: New (production deduplication)

#### Module: classic/utils.py
- **Path**: `src/riff/classic/utils.py`
- **Purpose**: Shared utility functions for classic commands
- **Scope**: Small (helpers)
- **Dependencies**: pathlib, json
- **Status**: Core

---

## Test Modules

### Graph Tests
- **Path**: `tests/graph/`
- **Test Files**:
  - `test_dag.py`: ConversationDAG construction
  - `test_loaders.py`: JSONL loading
  - `test_models.py`: Data model validation
  - `test_persistence.py`: Repair writing and undo
  - `test_repair.py`: Repair engine logic
- **Coverage**: DAG construction, orphan detection, thread identification, repair operations

### SurrealDB Tests
- **Path**: `tests/surrealdb/`
- **Test Files**:
  - `test_storage.py`: Storage operations
  - `test_materialization.py`: Event replay
  - `test_events.py`: Repair event logging
  - `test_sync_command.py`: Sync command workflow
- **Coverage**: Event sourcing, immutable store, materialization

### Integration Tests
- **Path**: `tests/integration/`
- **Test Files**:
  - `test_visualization_workflow.py`: End-to-end visualization
- **Coverage**: Cross-module workflows

### Unit Tests
- **Path**: `tests/unit/`
- **Test Files**:
  - `test_search_core.py`: Search functionality
  - `test_visualization_handler.py`: TUI handler
  - `test_visualization_formatter.py`: Format conversion
- **Coverage**: Individual components

### Feature Tests
- **Path**: `tests/`
- **Test Files**:
  - `test_duplicate_handler.py`: Deduplication logic
  - `test_duplicate_tool_results.py`: Integration tests
  - `test_intent_enhancer.py`: Query enhancement
  - `test_jsonl_tool.py`: JSONL utilities
  - `test_persistence_provider_integration.py`: Provider abstraction
  - `test_search_live.py`: Live search testing
  - `conftest.py`: Pytest fixtures and configuration

---

## Summary Statistics

- **Total Python Modules**: 56 files
- **Core Modules**: 25 (graph, search, database)
- **Infrastructure**: 4 (config, backup, manifest, memory)
- **Classic Commands**: 7 (legacy support)
- **TUI & Visualization**: 6
- **Tests**: 35+ test files
- **Major Components**: 
  - Graph Analysis (DAG, repair, analysis)
  - Semantic Search (Qdrant + intent)
  - SurrealDB Persistence (event sourcing)
  - Interactive TUI (vim-style navigation)
  - Data Visualization (ASCII + riff-dag-tui)

