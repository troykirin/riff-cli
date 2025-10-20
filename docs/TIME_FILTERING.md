# Time-Based Search Filtering

**Status**: ✅ Implemented (Week 1)
**Feature**: Filter search results by date ranges
**Library**: Qdrant metadata queries

---

## Quick Start

### Filter past 3 days
```bash
riff search "memory" --days 3
```

### Filter since specific date
```bash
riff search "federation" --since 2025-10-15
```

### Filter until specific date
```bash
riff search "deployment" --until 2025-10-20
```

### Combine filters (after Oct 15, before Oct 20)
```bash
riff search "oauth" --since 2025-10-15 --until 2025-10-20
```

---

## Usage Modes

### 1. CLI Flags (Direct)

**Most common usage** - specify date range in command:

```bash
# Past N days
riff search <query> --days 1      # Last 24 hours
riff search <query> --days 7      # Last week
riff search <query> --days 30     # Last month

# ISO 8601 dates
riff search <query> --since 2025-10-01
riff search <query> --until 2025-10-31
```

### 2. Interactive Mode (Coming Week 2)

Press `f` during TUI navigation to toggle filter:

```
Commands: j/k=navigate | g/G=top/bottom | Enter=open | f=filter | q=quit
> Press 'f' to set filter
? Time filter options:
  1d = Past 1 day
  3d = Past 3 days  (default)
  1w = Past 1 week
  1m = Past 1 month
  all = All time
```

---

## Implementation Details

### How It Works

1. **Indexing**: Session timestamps extracted from JSONL and stored in Qdrant
   - Field: `session_timestamp`
   - Format: ISO 8601 (from Claude JSONL files)
   - Example: `2025-10-20T07:30:00.123456+00:00`

2. **Filtering**: Build Qdrant query filter based on parameters
   - `--days N`: `session_timestamp >= now - N days`
   - `--since DATE`: `session_timestamp >= DATE`
   - `--until DATE`: `session_timestamp <= DATE`

3. **Results**: Only matching sessions returned

### Code Location

**CLI Arguments**: `src/riff/cli.py:123-125`
```python
p_search.add_argument("--days", type=int, help="Filter to sessions from past N days")
p_search.add_argument("--since", help="Filter sessions since date (ISO 8601: YYYY-MM-DD)")
p_search.add_argument("--until", help="Filter sessions until date (ISO 8601: YYYY-MM-DD)")
```

**Search Implementation**: `src/riff/search/qdrant.py:42-86`
```python
def _build_time_filter(self, days, since, until):
    """Build Qdrant filter for time-based queries"""
    # Handles conversion to ISO format and Qdrant filter syntax
```

**Indexing**: `scripts/improved_indexer.py:50-61`
```python
metadata = {
    'session_id': session_file.stem,
    'file_path': str(session_file),
    'working_directory': '',
    'session_timestamp': None  # Populated from JSONL
}
```

---

## Examples

### Find recent work on OAuth
```bash
riff search "oauth implementation" --days 3
```

### Find all federation discussions from specific week
```bash
riff search "federation protocol" --since 2025-10-13 --until 2025-10-20
```

### Find old memory-related sessions
```bash
riff search "memory" --until 2025-09-01
```

### Find nothing (query before any sessions)
```bash
riff search "anything" --since 2030-01-01
# Returns 0 results (all sessions are older)
```

---

## Timestamp Format

### Input Formats

CLI accepts both:
- **Flexible**: `2025-10-20` → auto-converts to ISO 8601
- **ISO 8601**: `2025-10-20T15:30:00Z` (fully qualified)

### Storage

Sessions store full ISO 8601 with timezone:
```
2025-10-20T07:30:00.123456+00:00
```

### Calculation

For `--days N`, calculates:
```python
cutoff = datetime.now() - timedelta(days=N)
# Filters: session_timestamp >= cutoff
```

---

## Notes

### Combining Filters

Multiple filters are **AND-ed** together:
```bash
riff search "query" --days 7 --until 2025-10-20
# Returns: sessions in last 7 days AND before Oct 20
```

### Performance

- Filter applied **server-side** in Qdrant (efficient)
- No client-side filtering
- Same <2s search latency

### Time Zones

All timestamps stored in UTC (Qdrant metadata).
CLI dates are interpreted relative to local timezone.

---

## Future Extensions (Week 2-3)

1. **Interactive Filter Toggle**: Press 'f' in TUI
2. **Quick Presets**: 1d, 3d, 1w, 1m shortcuts
3. **Filter Combination UI**: Pick start/end dates interactively
4. **Saved Filters**: Remember user preferences

---

For more info, see: `/docs/ARCHITECTURE.md`
