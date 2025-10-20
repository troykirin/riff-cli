# Riff CLI v2.0 - Architecture

**Version**: 2.0  
**Status**: Production (Search), In Development (TUI)  
**Last Updated**: 2025-10-18

---

## Overview

Riff CLI is a unified tool for searching Claude conversation sessions and repairing JSONL files. Version 2.0 introduces semantic search with Qdrant and establishes enterprise-grade repository structure.

**Core Capabilities:**
- 🔍 **Semantic Search**: Find conversations by meaning, not just keywords
- 📅 **Time-based Filtering**: Filter by --days, --since, or --until (NEW)
- 🛠️ **JSONL Repair**: Scan and fix malformed conversation exports
- 🎯 **Content Preview**: See actual text snippets, not just metadata
- 🤖 **AI Enhancement**: Intent-driven keyword expansion with Grok
- 📊 **Interactive TUI**: Modular vim-style navigation (Week 2 - in progress)

---

## System Architecture

### Three-Layer Design

```
┌─────────────────────────────────────┐
│     CLI Entry Point (cli.py)        │
│  - Command routing                  │
│  - Argument parsing                 │
│  - Mode selection                   │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ Search │ │ Repair │ │  TUI   │
│  Mode  │ │  Mode  │ │  Mode  │
└───┬────┘ └───┬────┘ └───┬────┘
    │          │           │
    └──────────┴───────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌─────────┐
│ Qdrant  │ │Classic │ │ Intent  │
│ Search  │ │  Fix   │ │   AI    │
└─────────┘ └────────┘ └─────────┘
```

See full architecture documentation at:
/private/tmp/docs/riff-cli/DECISIONS_AND_RATIONALE.md

---

## Key Components

### 1. Search Module (src/riff/search/)
- **QdrantSearcher**: Semantic search with 384-dim vectors + time-based filtering
- **ContentPreview**: Rich text rendering with improved hook filtering
- Time filtering methods: `_build_time_filter()` supports --days, --since, --until

### 2. TUI Module (src/riff/tui/) - MODULAR ARCHITECTURE
**Design Pattern: Abstract Interface + Implementations**
- **InteractiveTUI**: Abstract base class (not tied to any library)
- **PromptToolkitTUI**: MVP implementation with vim-style controls
- **TUIConfig**: Behavior configuration
- Allows future swaps (e.g., to tui-types Rust backend) without code changes

### 3. Enhancement Module (src/riff/enhance/)
- AI-powered keyword expansion with Grok
- Intent classification and routing

### 4. Classic Module (src/riff/classic/)
- Original TUI, scan, fix, graph commands preserved

---

## Design Decisions

### Time-based Filtering (NEW)
- Session timestamps stored in Qdrant metadata
- Extracted from JSONL timestamp field during indexing
- Three filter modes:
  - `--days N`: Sessions from past N days
  - `--since DATE`: Sessions after ISO 8601 date
  - `--until DATE`: Sessions before ISO 8601 date
- Example: `riff search "memory" --days 3`

### Modular TUI Architecture (NEW)
- Abstract `InteractiveTUI` interface (library-agnostic)
- Current implementation: `PromptToolkitTUI` (MVP)
- Future-proof for swaps (e.g., Rust tui-types integration)
- No tight coupling to any TUI library

### XDG-Compliant Federation
- Venv at: ~/.nabi/venvs/riff-cli/
- Cross-platform compatible
- No hardcoded paths

### Semantic Search
- Qdrant vector database
- Threshold: 0.2 (optimized for recall)
- Sub-2s latency

### Enterprise Repository Structure
- Clean root (<10 essential files)
- Infrastructure in infrastructure/
- Documentation in docs/
- Archive for legacy files

---

## Technology Stack

- **Python 3.13**: Modern type system
- **uv**: Package management
- **Qdrant**: Vector database
- **sentence-transformers**: Embeddings (all-MiniLM-L6-v2)
- **rich**: Terminal UI
- **Task**: Automation (Taskfile.yml)

---

## Data Flow

### Search with Filtering:
```
User Query → Intent Enhancement → Time Filter (--days/--since/--until)
  → Qdrant Query → Results → Rich Preview (no hook messages)
```

### Interactive Navigation:
```
Search Results → PromptToolkitTUI → Vim Controls (j/k/g/G)
  → 'f' key → Filter Prompt → Re-search with new filter
  → Enter → Open Session → Display full content
```

### Repair: JSONL → Scan → Detect Issues → Fix → Write .repaired

---

## Performance

- **Search Latency**: <2s
- **Indexed Sessions**: 804 (verified intact)
- **Vector Dimensions**: 384
- **Storage**: ~50MB index

---

## Federation Integration

```bash
# Nabi CLI registration
~/.nabi/bin/riff → ../venvs/riff-cli/bin/riff

# Usage
task nabi:register
nabi exec riff search "query"
```

---

## Roadmap

- **Week 1**: Foundation ✅
  - Content extraction + improved indexing
  - Time-based filtering architecture
  - Modular TUI interface design

- **Week 2**: TUI module development (in progress)
  - PromptToolkitTUI implementation
  - Vim-style navigation with prompt_toolkit
  - Filter toggling with 'f' keybinding
  - Session viewing with Enter

- **Week 3**: Default TUI integration
  - Integration with search command
  - 'riff browse' interactive mode
  - End-to-end testing

- **Week 4**: Production polish
  - Performance optimization
  - Future backend swap support (tui-types)

---

For complete architectural decisions and rationale, see:
- /private/tmp/docs/riff-cli/DECISIONS_AND_RATIONALE.md
- /private/tmp/docs/riff-cli/RIFF_CLI_HANDOFF.md
