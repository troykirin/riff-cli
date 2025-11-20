# Riff CLI Module Relationships & Dependencies

## High-Level Dependency Graph

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                             │
│          Command dispatcher, argument parsing, routing           │
└──────────────────┬──────────────────┬──────────────────┬─────────┘
                   │                  │                  │
        ┌──────────▼────┐  ┌─────────▼────┐  ┌────────▼──────┐
        │  Classic Cmds │  │  Subcommands │  │  New Features │
        │ (scan, fix)   │  │ (search, viz)│  │ (surrealdb)   │
        └────────┬──────┘  └──────┬───────┘  └────────┬──────┘
                 │                │                   │
        ┌────────▼────────────────▼───────────────────▼──────┐
        │          Graph Analysis & Repair Core              │
        │ ┌──────────────────────────────────────────────┐   │
        │ │  models.py (Message, Thread, Session)       │   │
        │ │  loaders.py (JSONLLoader, abstract I/O)     │   │
        │ │  dag.py (ConversationDAG)                   │   │
        │ │  analysis.py (ThreadDetector, Scorer)       │   │
        │ │  repair.py (RepairEngine, Suggestions)      │   │
        │ │  persistence.py (JSONLRepairWriter, undo)   │   │
        │ └──────────────────────────────────────────────┘   │
        └──────────────┬───────────────────────┬──────────────┘
                       │                       │
        ┌──────────────▼─┐          ┌─────────▼──────────┐
        │   Search Layer │          │  Persistence Layer │
        │ (Qdrant, intent│          │  (SurrealDB, Event)│
        │   enhancement) │          │  (Backup, Manifest)│
        └────────────────┘          └────────────────────┘
```

## Detailed Module Interaction Map

### Input Layer (I/O)

```
graph/loaders.py (Abstract interface)
  ├── JSONLLoader (Concrete implementation)
  │   ├── reads from: ~/.claude/projects/*.jsonl
  │   └── outputs: List[Message]
  │
  └── SurrealDB connections
      ├── surrealdb/storage.py
      └── surrealdb/schema_utils.py
```

### Analysis Layer

```
graph/dag.py (Graph construction)
  ├── depends on: models.py, loaders.py
  ├── inputs: List[Message]
  ├── outputs: ConversationDAG (adjacency lists)
  │
  └── graph/analysis.py (Semantic analysis)
      ├── ThreadDetector: Identify main/side/orphaned
      ├── CorruptionScorer: 0.0-1.0 health metric
      └── SemanticAnalyzer: Topic extraction
          │
          └── graph/repair.py (Repair suggestions)
              ├── RepairEngine: Heuristic similarity
              ├── ParentCandidate: Scored suggestions
              └── RepairDiff: Before/after display
```

### Search Layer

```
search/qdrant.py
  ├── QdrantSearcher: Vector database interface
  ├── SearchResult: Hit dataclass
  └── Index management (create, delete, reindex)
      │
      └── enhance/intent.py
          ├── IntentEnhancer: Query processing
          ├── Intent detection: question/search/debug/optimization
          └── Keyword expansion: memory, federation, etc.
```

### Persistence Layer

```
graph/persistence.py
  ├── RepairOperation: Single repair record
  ├── RepairSnapshot: Session state
  ├── JSONLRepairWriter: Atomic JSONL updates
  └── Undo/redo history
      │
      └── surrealdb/storage.py
          ├── SurrealDBStorage: Event logging
          ├── RepairEvent: Immutable append
          └── materialize_session(): Replay events
              │
              └── surrealdb/schema_utils.py
                  ├── SCHEMA_DICT: Table definitions
                  ├── Validation functions
                  └── Query builders
```

### Deduplication Pipeline

```
classic/duplicate_handler.py (Detection engine)
  ├── detect_duplicate_tool_results()
  ├── remove_duplicate_tool_results()
  └── Graceful error handling
      │
      ├── classic/commands/fix_with_deduplication.py
      │   └── cmd_fix() with dedup
      │
      └── classic/commands/scan_with_duplicates.py
          └── cmd_scan() with dedup reporting
```

### UI/Visualization Pipeline

```
Conversation Session (JSONL file)
  │
  ├─→ graph/loaders.py (JSONLLoader)
  │       │
  │       └─→ List[Message]
  │
  ├─→ graph/dag.py (ConversationDAG)
  │       │
  │       └─→ Adjacency lists, children, parents
  │
  ├─→ graph/analysis.py (ThreadDetector)
  │       │
  │       └─→ List[Thread]
  │
  ├─→ graph/visualizer.py (ASCII render)
  │       │
  │       └─→ ConversationTreeVisualizer
  │           │
  │           ├─→ Terminal output (tui.py navigation)
  │           │
  │           └─→ visualization/formatter.py
  │               │
  │               └─→ convert_to_dag_format()
  │                   │
  │                   └─→ visualization/handler.py
  │                       │
  │                       └─→ RiffDagTUIHandler
  │                           │
  │                           └─→ riff-dag-tui subprocess
```

### Infrastructure Coordination

```
config.py
  ├── get_config(): RiffConfig
  ├── XDG paths expansion
  └── TOML configuration loading
      │
      ├─→ manifest_adapter.py
      │   ├── ManifestAdapter (abstract)
      │   ├── LocalManifestAdapter (SHA256)
      │   └── needs_reindex(), validate_index_integrity()
      │
      ├─→ memory_producer.py
      │   ├── RiffMemoryProducer (singleton)
      │   ├── log_event/span/state/metric()
      │   └── memory:item JSONL stream
      │
      └─→ backup.py
          ├── get_backup_metadata_path()
          └── load_backup_index()
```

## Command Flow Examples

### Scan Command Flow

```
cli.py:cmd_scan()
  │
  ├─→ get_config()
  ├─→ get_manifest_adapter() → validate_index_integrity()
  ├─→ JSONLLoader → load_messages()
  ├─→ ConversationDAG → build graph
  ├─→ ThreadDetector → identify_threads()
  ├─→ CorruptionScorer → score_session()
  └─→ print_report()
```

### Search Command Flow

```
cli.py:cmd_search(query)
  │
  ├─→ IntentEnhancer → enhance_query()
  ├─→ detect_intent() → suggest_filters()
  ├─→ QdrantSearcher → search(enhanced_query)
  ├─→ memory_producer → log_search_performed()
  ├─→ ContentPreview → extract_preview()
  └─→ display_results()
```

### Repair Command Flow

```
cli.py:cmd_repair(session_id)
  │
  ├─→ JSONLLoader → load_messages()
  ├─→ ConversationDAG → build graph
  ├─→ RepairEngine → suggest_repairs()
  ├─→ RepairManager → interactive_repair()
  │   ├─→ operator reviews suggestions
  │   └─→ selects repairs to apply
  ├─→ JSONLRepairWriter → write_repair()
  ├─→ SurrealDBStorage → log_repair_event()
  ├─→ memory_producer → log_reindex_completed()
  ├─→ backup.py → create_backup()
  └─→ display_summary()
```

### SurrealDB Sync Command Flow

```
cli.py:cmd_sync_surrealdb(session_id)
  │
  ├─→ JSONLLoader → load_messages()
  ├─→ ConversationDAG → build graph
  ├─→ ThreadDetector → identify_threads()
  ├─→ SurrealDBStorage → store_session()
  ├─→ prepare_session_record() [schema_utils]
  ├─→ prepare_message_record() [schema_utils]
  ├─→ SurrealDBStorage → log_repair_event()
  ├─→ memory_producer → log_event()
  └─→ display_sync_status()
```

## Module Import Dependencies

### Core Layer (Fundamental)

```
graph/models.py
  ├── imports: dataclasses, typing, enum
  └── imported_by: All other graph modules
```

### Storage Layer

```
graph/loaders.py
  ├── imports: json, abc, pathlib, models
  └── imported_by: dag, persistence, cli
  
surrealdb/schema_utils.py
  ├── imports: typing, json, dataclasses
  └── imported_by: surrealdb/storage, loaders
```

### Analysis Layer

```
graph/dag.py
  ├── imports: typing, collections, models, loaders, analysis
  └── imported_by: repair, cli, tui
  
graph/analysis.py
  ├── imports: logging, re, collections, typing, models
  └── imported_by: dag, repair, repair_manager
  
graph/repair.py
  ├── imports: logging, dataclasses, datetime, typing, models, analysis
  └── imported_by: repair_manager, cli
```

### Search Layer

```
search/qdrant.py
  ├── imports: dataclasses, typing, datetime, pathlib, qdrant_client, sentence_transformers, config
  └── imported_by: cli, search commands
  
enhance/intent.py
  ├── imports: re
  └── imported_by: cli, search layer
```

### Persistence Layer

```
graph/persistence.py
  ├── imports: json, logging, os, shutil, dataclasses, datetime, pathlib, loaders
  └── imported_by: cli, classic commands
  
surrealdb/storage.py
  ├── imports: json, logging, uuid, dataclasses, datetime, pathlib, typing, urllib, httpx, models, loaders, schema_utils
  └── imported_by: cli, sync commands, repair provider
```

### UI Layer

```
visualization/handler.py
  ├── imports: subprocess, shutil, pathlib, typing, rich
  └── imported_by: cli
  
tui/graph_navigator.py
  ├── imports: models, visualizer, loaders, typing, interface
  └── imported_by: cli, classic commands
  
graph/visualizer.py
  ├── imports: models, dag, typing
  └── imported_by: tui, cli
```

### Infrastructure Layer

```
config.py
  ├── imports: pathlib, typing, toml, os
  └── imported_by: All layers (global configuration)
  
manifest_adapter.py
  ├── imports: abc, pathlib, typing, hashlib, json, datetime
  └── imported_by: search commands, cli
  
memory_producer.py
  ├── imports: json, datetime, pathlib, typing, uuid
  └── imported_by: cli, analysis, persistence
  
backup.py
  ├── imports: pathlib, datetime, typing, json, shutil, os
  └── imported_by: persistence, repair commands
```

### Dispatcher Layer

```
cli.py
  ├── imports: argparse, pathlib, rich, all major modules
  └── entry_point: main()
```

## Circular Dependency Prevention

**No circular imports detected**. Dependency flow is strictly layered:

1. Core models (no external deps)
2. Storage abstractions (depend on 1)
3. Analysis engines (depend on 1, 2)
4. Search engines (depend on 1)
5. Persistence systems (depend on 1, 2, 3)
6. UI/Visualization (depend on 1, 2, 3)
7. Infrastructure (depend on all layers)
8. CLI dispatcher (depends on all)

## Configuration Paths (XDG)

All paths are configured via `~/.config/nabi/riff.toml` and expandable:

```
~/.config/nabi/riff.toml         (main config)
  │
  ├─ conversations: ~/.claude/projects/
  │  └── read by: loaders.py, cli.py
  │
  ├─ embeddings: ~/.local/share/nabi/riff/embeddings
  │  └── used by: search/qdrant.py
  │
  ├─ backups: ~/.local/share/nabi/riff/backups/
  │  └── managed by: backup.py, persistence.py
  │
  ├─ state: ~/.local/state/nabi/riff/
  │  └── contains: manifest.json, memory_stream.jsonl
  │
  └─ cache: ~/.cache/nabi/riff/
     └── temporary: indexes, temp files
```

---

**Generated**: 2025-11-20  
**Version**: 2.0.0 (XDG Architecture)  
**Total Connections**: 50+ module-to-module dependencies  

