# ConversationDAG Visualizer Implementation

**Status**: ✅ Complete
**Date**: 2025-10-20
**Location**: `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/visualizer.py`

---

## Overview

Implemented ASCII tree visualization for ConversationDAG structures, providing git-log style output for conversation analysis and navigation.

## Deliverables

### 1. Core Implementation

**File**: `src/riff/graph/visualizer.py`

**Classes**:

- `LineItem`: Dataclass representing a single line in the flattened tree
  - `text`: Formatted display text
  - `message_uuid`: Reference for navigation
  - `thread_id`: Thread identifier
  - `is_orphan`: Orphan flag
  - `corruption_score`: Corruption metric (0.0-1.0)
  - `indent_level`: Tree indentation depth

- `ConversationTreeVisualizer`: Main visualization engine
  - `visualize(session)`: Generate full ASCII tree output
  - `flatten_for_navigation(session)`: Convert to flat list for TUI

**Features**:
- Main thread rendering with `*` markers
- Side discussion branches with `|\` and `|/` graphics
- Orphaned thread detection with `!` markers
- Corruption score display with inferred causes
- Message preview truncation (configurable, default 80 chars)
- Timestamp formatting (ISO8601 → `YYYY-MM-DD HH:MM`)

### 2. Output Format

The visualizer produces git-log style ASCII trees:

```
* 2025-10-20 12:34 User: "main thread message"
* 2025-10-20 12:35 Assistant: "response on main thread"
|\
| * [Side] 2025-10-20 12:40 User: "side question"
| * [Side] 2025-10-20 12:41 Assistant: "side answer"
|/
* 2025-10-20 12:45 User: "back to main topic"
|
| ! [ORPHAN] 2025-10-20 13:00 User: "disconnected message"
| ! [ORPHAN] 2025-10-20 13:01 Assistant: "orphaned response"
| ! (corruption_score: 0.92, null parent, resume failure)
```

**Markers**:
- `*` = Main thread message
- `|\` = Side discussion branch start
- `|/` = Side discussion branch end (rejoin)
- `|` = Continuation line / separator
- `!` = Orphaned message (corrupted)

### 3. Navigation Support

The `flatten_for_navigation()` method converts the tree structure into a flat list suitable for TUI cursor navigation:

```python
nav_items = flatten_for_navigation(session)

for item in nav_items:
    print(item.text)  # Display formatted line
    if item.message_uuid:
        # Can jump to full message
        msg = session.get_message_by_uuid(item.message_uuid)
```

Each `LineItem` includes:
- Visual formatting preserved from tree
- Message UUID for detail view jumps
- Thread ID for filtering/grouping
- Orphan status for visual highlighting
- Corruption score for warnings
- Indent level for structure preservation

### 4. Corruption Detection

The visualizer displays corruption information for orphaned threads:

```
| ! (corruption_score: 0.92, null parent, resume failure, high corruption score)
```

**Detected Signals**:
- `null parent`: parentUuid is None (broken chain)
- `resume failure`: isSidechain=true but disconnected
- `high corruption score`: Aggregate score > 0.8

### 5. Test Suite

**File**: `src/riff/graph/test_visualizer.py`

Synthetic test session demonstrating:
- Main thread with 6 messages
- Side discussion with 4 messages (branching and rejoining)
- Orphaned thread with 3 messages (corruption_score: 0.92)

Run test:
```bash
PYTHONPATH=/path/to/riff-cli/src python3 -m riff.graph.test_visualizer
```

### 6. Real Data Example

**File**: `src/riff/graph/example_usage.py`

Demonstrates loading real Claude JSONL files and visualizing them:

```bash
PYTHONPATH=/path/to/riff-cli/src python3 -m riff.graph.example_usage ~/.claude/projects/*/session.jsonl
```

Features:
- JSONL parsing with error handling
- Message content extraction (handles multiple formats)
- Type conversion (user/assistant/system)
- Simple session construction

### 7. Documentation

**File**: `src/riff/graph/README.md`

Comprehensive documentation including:
- Quick start guide
- API reference
- Integration patterns for TUI
- Corruption detection details
- Testing instructions
- Future enhancement ideas

---

## Integration Points

### With TUI

The visualizer is designed for seamless TUI integration:

```python
from riff.graph.visualizer import flatten_session_for_navigation

class ConversationGraphTUI:
    def __init__(self, session):
        self.nav_items = flatten_session_for_navigation(session)
        self.current_index = 0

    def render(self):
        # Display current view with highlight
        for i, item in enumerate(self.nav_items):
            if i == self.current_index:
                print(f"> {item.text}")  # Highlighted
            else:
                print(f"  {item.text}")

    def on_enter(self):
        # Jump to message detail view
        item = self.nav_items[self.current_index]
        if item.message_uuid:
            return self.show_message_detail(item.message_uuid)
```

### With ConversationDAG

Once the full DAG implementation is complete:

```python
from riff.graph import ConversationDAG, visualize_session

# Build DAG with thread detection
dag = ConversationDAG.from_jsonl("session.jsonl")

# Visualize the analyzed structure
tree = visualize_session(dag.to_session())
print(tree)
```

---

## Testing Results

### Synthetic Test

```
Session: test-session-001
Total messages: 13
Threads: 2 (main + 1 side)
Orphaned threads: 1
Corruption score: 0.25

Output: 17 navigation items (6 main + 4 branch markers + 4 side + 3 orphan)
```

### Real JSONL Test

```
Session: 106589a6-8430-44ea-9ad9-507bd64f24b0
Total messages: 439
Threads: 1 (main only, no DAG analysis yet)

Successfully rendered full conversation tree with proper timestamps and previews
```

---

## Architecture Alignment

This implementation aligns with the design in `docs/SEMANTIC_DAG_DESIGN.md`:

✅ **Section 4: ASCII Tree Visualization**
- Git-log style output format
- Main thread with `*` markers
- Side discussions with branch graphics
- Orphan detection with `!` markers

✅ **Section 6: Integration with riff-cli TUI**
- Flattened navigation list
- LineItem metadata for cursor tracking
- Message UUID references for detail views

✅ **Data Flow**
- Session → Threads → LineItems → Visualization

---

## Future Enhancements

As noted in the design document and README:

1. **Color Support**: Add ANSI color codes for TUI rendering
   - Main thread: default color
   - Side discussions: cyan/blue
   - Orphans: red/yellow warning colors

2. **Interactive Repair**: Integration with repair operations
   - Show repair suggestions in visualization
   - Highlight relink candidates
   - Preview repair outcomes

3. **Semantic Labels**: Display topic clusters
   - `* [Architecture] User: "question about design"`
   - Semantic thread names from DAG analysis

4. **Export Formats**: Additional output formats
   - DOT format for GraphViz
   - Mermaid diagram syntax
   - JSON tree structure

5. **Navigation Enhancements**:
   - Thread-based filtering (show only main, only side, only orphans)
   - Time-range filtering
   - Search within visualization

---

## Files Created

1. `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/visualizer.py` (358 lines)
2. `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/test_visualizer.py` (261 lines)
3. `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/example_usage.py` (201 lines)
4. `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/README.md` (documentation)

**Modified**:
1. `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/__init__.py` (added exports)

---

## Success Criteria Met

✅ **ConversationTreeVisualizer class**
- `visualize()` method generates git-log style output
- `flatten_for_navigation()` provides flat list for TUI
- Configurable message preview length

✅ **LineItem dataclass**
- All required fields present
- Metadata for navigation and display
- Type-safe with proper annotations

✅ **Output Format**
- Main thread with `*` markers
- Side discussions with `|\` and `|/` branch graphics
- Orphans with `!` markers and corruption scores
- Timestamps and message types
- Preview truncation with "..."

✅ **Navigation Support**
- Flat list preserves tree structure via indentation
- Each message gets one LineItem
- Breadth-first ordering through threads

✅ **Testing**
- Synthetic test session with all thread types
- Real JSONL data loading and visualization
- Documented test execution

---

## Next Steps

1. **DAG Integration**: Once `ConversationDAG` class is complete, integrate with visualizer
2. **TUI Integration**: Implement graph view mode in riff-cli TUI
3. **CLI Commands**: Add `riff graph <session-id>` command
4. **Color Support**: Add ANSI color codes for enhanced TUI rendering
5. **Repair Integration**: Show repair suggestions inline with orphans

---

## References

- Design Document: `/Users/tryk/nabia/tools/riff-cli/docs/SEMANTIC_DAG_DESIGN.md`
- Models: `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/models.py`
- Implementation: `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/visualizer.py`
- Documentation: `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/README.md`
