# ConversationGraphNavigator Usage Guide

## Overview

The `ConversationGraphNavigator` provides a vim-style interactive TUI for navigating conversation DAGs (Directed Acyclic Graphs). It allows you to explore conversation structure, view message details, and identify orphaned messages.

## Quick Start

```python
from pathlib import Path
from riff.graph import JSONLLoader, ConversationDAG, ConversationGraphNavigator

# Load conversation from JSONL
conversations_dir = Path("~/.claude/projects/your-project").expanduser()
loader = JSONLLoader(conversations_dir)

# Build DAG
session_id = "your-session-id"
dag = ConversationDAG(loader, session_id)

# Launch interactive navigator
navigator = ConversationGraphNavigator(dag)
result = navigator.navigate()

# Handle navigation result
if result.action == "open":
    line = navigator.lines[result.selected_index]
    message = navigator._get_message_from_line(line)
    if message:
        navigator.show_message_details(message)
elif result.action == "repair":
    line = navigator.lines[result.selected_index]
    message = navigator._get_message_from_line(line)
    if message:
        navigator.show_repair_suggestions(message)
```

## Key Bindings

The navigator uses vim-style keybindings:

| Key | Action | Description |
|-----|--------|-------------|
| `j` | Move down | Navigate to next line |
| `k` | Move up | Navigate to previous line |
| `g` | Go to top | Jump to first line |
| `G` | Go to bottom | Jump to last line (Shift+G) |
| `Enter` | Show details | Display full message details |
| `r` | Repair | Show repair suggestions (for orphans) |
| `q` | Quit | Exit navigator |
| `Ctrl+C` | Force quit | Emergency exit |

## Display Format

The navigator shows conversations in a git-log-like tree format:

```
* 2025-10-20 12:34 User: "analyze riff-cli"
* 2025-10-20 12:35 Assistant: "I'll examine the architecture..."
|\
| * [Side] 2025-10-20 12:40 User: "quick question about search"
| * [Side] 2025-10-20 12:41 Assistant: "That's handled by Qdrant..."
|/
* 2025-10-20 12:45 User: "back to the main question..."
|
| ! [ORPHAN] 2025-10-20 13:00 User: "Resume attempt"
| ! [ORPHAN] 2025-10-20 13:01 Assistant: "Continuing conversation..."
| ! (corruption_score: 0.92, resume failure)
```

### Visual Markers

- `*` = Main thread or side discussion message
- `|` = Branch connector
- `!\` = Branch start
- `|/` = Branch end (rejoin)
- `!` = Orphaned message (corruption detected)

### Color Coding

- **White/Normal**: Regular messages
- **Red**: Orphaned messages (corruption detected)
- **Dim**: Branch markers and separators

## Message Details View

Pressing `Enter` on a message shows:

- Full UUID
- Message type (USER, ASSISTANT, SYSTEM, etc)
- Timestamp
- Parent/child relationships
- Thread membership
- Corruption score
- Full message content (up to 2000 chars)
- Ancestry path from root

## Repair Suggestions (for Orphans)

Pressing `r` on an orphaned message shows:

1. **Candidate parent messages** ranked by confidence score
2. **Scoring factors**:
   - Timestamp proximity
   - Message type patterns (user → assistant alternation)
   - Thread membership
   - Content similarity (future enhancement)

3. **Repair instructions**:
   ```bash
   riff repair --session <session-id> \
               --orphan <orphan-uuid> \
               --parent <candidate-uuid>
   ```

## Viewport Pagination

The navigator intelligently handles large conversations:

- Shows 20 lines at a time (configurable via `viewport_height`)
- Centered on current cursor position
- Smooth scrolling with j/k navigation
- Position indicator: `Line 42/142`

## Integration Examples

### CLI Integration

```python
# Add to riff CLI
@click.command()
@click.argument('session_id')
def graph(session_id: str):
    """Navigate conversation graph interactively."""
    from riff.graph import JSONLLoader, ConversationDAG, ConversationGraphNavigator
    from pathlib import Path

    conversations_dir = Path("~/.claude/projects/").expanduser()
    loader = JSONLLoader(conversations_dir)

    dag = ConversationDAG(loader, session_id)
    navigator = ConversationGraphNavigator(dag)

    while navigator.is_active():
        result = navigator.navigate()

        if result.action == "open":
            line = navigator.lines[result.selected_index]
            message = navigator._get_message_from_line(line)
            if message:
                navigator.show_message_details(message)

        elif result.action == "repair":
            line = navigator.lines[result.selected_index]
            message = navigator._get_message_from_line(line)
            if message:
                navigator.show_repair_suggestions(message)

        elif result.action == "quit":
            break
```

### Programmatic Analysis

```python
# Analyze session structure before navigation
from riff.graph import JSONLLoader, ConversationDAG
from pathlib import Path

loader = JSONLLoader(Path("~/.claude/projects/your-project").expanduser())
dag = ConversationDAG(loader, "session-id")
session = dag.to_session()

print(f"Total messages: {session.message_count}")
print(f"Threads: {session.thread_count}")
print(f"Orphans: {session.orphan_count}")
print(f"Corruption score: {session.corruption_score:.2f}")

# Launch navigator only if needed
if session.orphan_count > 0:
    from riff.graph import ConversationGraphNavigator
    navigator = ConversationGraphNavigator(dag)
    navigator.navigate()
```

## Architecture

### Component Relationship

```
ConversationDAG (dag.py)
    ↓ builds session
Session (models.py)
    ↓ contains threads
Thread (models.py)
    ↓ contains messages
Message (models.py)

ConversationTreeVisualizer (visualizer.py)
    ↓ flattens session
List[LineItem] (visualizer.py)
    ↓ displayed by
ConversationGraphNavigator (tui.py)
```

### Data Flow

1. **Load**: `JSONLLoader` reads JSONL conversation files
2. **Parse**: Creates `Message` objects with metadata
3. **Build**: `ConversationDAG` constructs graph structure
4. **Analyze**: Identifies threads, orphans, corruption scores
5. **Flatten**: `ConversationTreeVisualizer` creates `LineItem` list
6. **Navigate**: `ConversationGraphNavigator` provides TUI
7. **Interact**: User navigates with vim keys, views details

## Performance

The navigator handles large conversations efficiently:

- **1000+ messages**: Smooth navigation, viewport pagination
- **Memory**: O(n) where n = message count
- **Rendering**: Only visible viewport lines rendered
- **Indexing**: O(1) message lookup by UUID

## Future Enhancements

Planned features:

1. **Search within conversation**: `/pattern` vim-style search
2. **Jump to thread**: `t` key to switch threads
3. **Expand/collapse**: Fold side discussions
4. **Export selected**: Save viewport or thread to file
5. **Semantic highlighting**: Color-code by topic
6. **Content similarity**: Better repair suggestions
7. **Diff mode**: Compare two sessions
8. **Undo/redo**: For repair operations

## Troubleshooting

### "No messages in conversation"

- Check that session_id is correct
- Verify JSONL file exists in conversations_dir
- Ensure JSONL is valid (use `riff validate`)

### Navigation feels sluggish

- Reduce `viewport_height` (default: 20)
- Consider session corruption (high overhead)

### Orphans not showing repair suggestions

- Orphan may be severely corrupted
- Main thread may be empty
- Try manual inspection with `show_message_details`

## See Also

- `SEMANTIC_DAG_DESIGN.md` - Architecture overview
- `docs/TIME_FILTERING.md` - Time-based search integration
- `docs/ARCHITECTURE.md` - Overall riff-cli design
