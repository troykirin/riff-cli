# Riff CLI: Quick Reference Guide

## One-Page Summary

**Riff v2.0** = Python CLI for searching Claude conversations + JSONL repair

### What It Does

```
Search conversations by meaning + repair JSONL + visualize as trees
```

### Quick Setup

```bash
cd /Users/tryk/nabia/tools/riff-cli
direnv allow          # Loads .envrc → .hookrc
riff --help          # Shows all commands
```

---

## Key Commands (Copy-Paste Ready)

### Search
```bash
riff search "memory architecture"              # Semantic search
riff search "query" --ai                       # With AI enhancement
riff search "query" --days 7                   # Past week only
riff search --uuid abc-123-def                 # Find by UUID
```

### SurrealDB Sync (Phase 6B)
```bash
riff sync:surrealdb abc-123-session-id         # Sync to DB
riff sync:surrealdb path/to/session.jsonl      # Full path works too
riff sync:surrealdb abc-123 --dry-run          # Preview only
riff sync:surrealdb abc-123 --force            # Force re-sync
```

### Graph Visualization
```bash
riff graph abc-123                             # ASCII tree + TUI
riff graph abc-123 --no-interactive            # ASCII only
riff graph path/to/session.jsonl               # Full path works
```

### Original Commands (Preserved)
```bash
riff scan ~/claude/                            # Find issues
riff fix broken.jsonl --in-place               # Repair file
riff tui ~/claude/                             # Browse interactively
riff graph-classic session.jsonl --format mermaid  # Legacy format
```

---

## Module Organization

| Path | Purpose |
|------|---------|
| `cli.py` | Command router (entry point) |
| `search/` | Qdrant vector search |
| `enhance/` | AI query enhancement |
| `graph/` | DAG analysis, models, loaders |
| `surrealdb/` | Event-sourced storage |
| `classic/` | Original TUI commands |
| `tui/` | Interactive navigator |

---

## Key Data Structures

```python
Message(uuid, parent_uuid, type, content, ...)
Thread(thread_id, messages, thread_type, ...)
Session(session_id, main_thread, side_threads, ...)
```

---

## Configuration

### Environment Variables (.hookrc auto-loads)

```bash
RIFF_QDRANT_URL           # Search backend (default: http://localhost:6333)
RIFF_QDRANT_COLLECTION    # Qdrant collection (default: claude_sessions)
RIFF_SEARCH_ENABLED       # Enable search (default: true)
RIFF_EMBEDDING_MODEL      # Embeddings (default: all-MiniLM-L6-v2)
RIFF_ENV                  # Environment (development/production)
```

### Venv Location

```
~/.nabi/venvs/riff-cli/    # Managed by federation
```

---

## Database Tiers

1. **JSONL** - Source (read-only after sync)
2. **SurrealDB** - Canonical store (immutable events)
3. **Qdrant** - Search index (384-dim vectors)

---

## Federation Integration

```bash
task nabi:register                    # Register with Nabi CLI
nabi exec riff search "query"        # Use from anywhere
```

---

## Important URLs

```
SurrealDB: ws://localhost:8000/rpc   (WebSocket)
Qdrant:    http://localhost:6333     (HTTP)
```

See `~/docs/federation/PORT_REGISTRY.md` for status

---

## Common Patterns

### Search with Multiple Filters
```bash
riff search "federation" --ai --days 14 --min-score 0.5
```

### Sync with Custom Operator
```bash
riff sync:surrealdb abc-123 --operator "my-script"
```

### Check Health
```bash
source .hookrc    # Load env
python -c "from riff.search import QdrantSearcher; print('OK' if QdrantSearcher().is_available() else 'FAIL')"
```

---

## File Paths (Absolute - Copy These)

- Entry Point: `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py`
- Config: `/Users/tryk/nabia/tools/riff-cli/.hookrc`
- Docs: `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md`
- Tests: `/Users/tryk/nabia/tools/riff-cli/tests/`

---

## Next Steps for Development

1. **Search**: Already works (Qdrant backend)
2. **SurrealDB Sync**: Phase 6B complete ✅
3. **TUI**: In development (Week 2)
4. **Rust Integration**: Planned (Phase 7+)

---

## Quick Health Check

```bash
cd /Users/tryk/nabia/tools/riff-cli
direnv allow
riff --help                    # Should show all commands
riff search "test"            # Should connect to Qdrant
echo $RIFF_QDRANT_URL         # Should print URL
```

---

For detailed docs: See `EXPLORATION_REPORT.md` or `/docs/` folder
