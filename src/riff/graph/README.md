# Conversation DAG Visualization

ASCII tree visualization for Claude conversation graphs, inspired by `git log --graph`.

## Overview

The `visualizer` module provides tools to render conversation DAG structures as ASCII trees, making it easy to understand conversation flow, branches, and structural issues like orphaned messages.

## Features

- **Main Thread Visualization**: Primary conversation flow with `*` markers
- **Side Discussions**: Branch and rejoin patterns with `|\` graphics
- **Orphan Detection**: Highlight disconnected messages with `!` markers
- **Navigation Support**: Flatten tree into navigable list for TUI integration
- **Corruption Metrics**: Display corruption scores and inferred causes

## Quick Start

```python
from riff.graph import Session, visualize_session

# Load or create a session
session = load_session_from_jsonl("session.jsonl")

# Visualize as ASCII tree
tree = visualize_session(session, max_preview_length=80)
print(tree)
```

## Output Format

The visualizer produces output similar to `git log --graph`:

```
* 2025-10-20 User: "message preview"
* 2025-10-20 Assistant: "response preview"
|\
| * [Side] User: "tangent question"
| * [Side] Assistant: "answer"
|/
* 2025-10-20 User: "back to main"
|
| ! [ORPHAN] User: "Resume attempt"
| ! [ORPHAN] Assistant: "Continuing..."
| ! (corruption_score: 0.92, null parent, resume failure)
```

### Markers

- `*` - Main thread message
- `|\` - Side discussion branch start
- `|/` - Side discussion branch rejoin
- `|` - Continuation/separator
- `!` - Orphaned message (disconnected)

## API Reference

### ConversationTreeVisualizer

Main class for generating ASCII tree visualizations.

```python
from riff.graph.visualizer import ConversationTreeVisualizer

visualizer = ConversationTreeVisualizer(max_preview_length=80)
tree_str = visualizer.visualize(session)
```

**Methods:**

- `visualize(session: Session) -> str`: Generate full ASCII tree
- `flatten_for_navigation(session: Session) -> List[LineItem]`: Flatten for TUI navigation

**Parameters:**

- `max_preview_length`: Maximum characters for message preview (default: 80)

### LineItem

Represents a single line in the flattened visualization.

```python
@dataclass
class LineItem:
    text: str                      # Formatted line text
    message_uuid: Optional[str]    # Message UUID (for navigation)
    thread_id: Optional[str]       # Thread identifier
    is_orphan: bool                # True if orphaned
    corruption_score: float        # Corruption score (0.0-1.0)
    indent_level: int              # Indentation depth
```

### Convenience Functions

```python
from riff.graph.visualizer import (
    visualize_session,
    flatten_session_for_navigation
)

# Quick visualization
tree = visualize_session(session, max_preview_length=80)

# Quick flattening for navigation
nav_items = flatten_session_for_navigation(session)
```

## Integration with TUI

The visualizer is designed for seamless TUI integration:

```python
from riff.graph.visualizer import flatten_session_for_navigation

# Get navigable line items
nav_items = flatten_session_for_navigation(session)

# Each LineItem contains:
# - text: Formatted display text
# - message_uuid: For jumping to full message
# - thread_id: For thread-based filtering
# - is_orphan: For visual highlighting
# - corruption_score: For warnings
```

### TUI Navigation Pattern

```python
class ConversationGraphTUI:
    def __init__(self, session):
        self.nav_items = flatten_session_for_navigation(session)
        self.current_index = 0

    def navigate_up(self):
        if self.current_index > 0:
            self.current_index -= 1

    def navigate_down(self):
        if self.current_index < len(self.nav_items) - 1:
            self.current_index += 1

    def get_current_message(self):
        item = self.nav_items[self.current_index]
        if item.message_uuid:
            return session.get_message_by_uuid(item.message_uuid)
        return None
```

## Corruption Detection

The visualizer displays corruption information for orphaned threads:

```
| ! (corruption_score: 0.92, null parent, resume failure)
```

**Corruption Signals:**

- `null parent`: Message has no parent UUID (broken chain)
- `resume failure`: Message marked as sidechain but disconnected
- `high corruption score`: Aggregate score > 0.8

## Testing

Run the test suite to see the visualizer in action:

```bash
PYTHONPATH=/path/to/riff-cli/src python3 -m riff.graph.test_visualizer
```

This demonstrates:
- Main thread rendering
- Side discussion branches
- Orphaned message detection
- Navigation flattening

## Implementation Details

### Thread Processing Order

1. **Main Thread**: Rendered first with `*` markers
2. **Side Discussions**: Rendered with branch graphics (`|\`, `|/`)
3. **Orphaned Threads**: Rendered last with `!` markers and warnings

### Message Preview

- First line of message content only
- Truncated to `max_preview_length` with "..." suffix
- Strips whitespace for clean display

### Timestamp Formatting

- ISO8601 input converted to `YYYY-MM-DD HH:MM` format
- Graceful fallback if parsing fails

## Future Enhancements

- [ ] Color support for TUI rendering
- [ ] Configurable indent width
- [ ] Semantic topic labels
- [ ] Interactive repair suggestions
- [ ] Export to other formats (DOT, Mermaid)

## See Also

- `/Users/tryk/nabia/tools/riff-cli/docs/SEMANTIC_DAG_DESIGN.md` - Overall architecture
- `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/models.py` - Data models
- `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/dag.py` - DAG construction
