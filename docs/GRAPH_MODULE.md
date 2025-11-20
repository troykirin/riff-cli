# Conversation Graph Module

## Overview

The `riff.graph` module provides semantic DAG (Directed Acyclic Graph) construction and analysis for Claude conversation JSONL files. It enables deep analysis of conversation structure, thread detection, orphan identification, and corruption metrics.

## Architecture

### Core Components

1. **models.py** - Type-safe dataclasses
   - `Message`: Individual conversation messages with metadata
   - `Thread`: Coherent sequences of messages
   - `Session`: Complete conversation sessions with threads
   - Enums: `MessageType`, `ThreadType`

2. **loaders.py** - Storage abstraction
   - `ConversationStorage`: Abstract interface for storage backends
   - `JSONLLoader`: Claude JSONL file parser

3. **dag.py** - Graph construction and analysis
   - `ConversationDAG`: DAG builder with thread detection
   - Graph traversal methods
   - Structural validation

## Type Safety

Built with Python 3.13+ type hints:
- Full type annotations on all functions and methods
- Type-safe enums for message and thread types
- Proper use of Optional, List, Dict type hints
- TypeAlias for complex types (AdjacencyList)

## Key Features

### 1. Message Parsing

Handles all Claude message types:
- User messages
- Assistant messages (including tool use)
- System messages
- Summary messages
- File history snapshots

```python
from riff.graph import JSONLLoader

loader = JSONLLoader("~/.claude/projects/my-project")
messages = loader.load_messages("session-uuid")
```

### 2. DAG Construction

Builds parent-child relationships:
- Adjacency list representation
- Fast UUID-based lookup
- Handles missing parents gracefully
- Detects orphaned messages

```python
from riff.graph import ConversationDAG

dag = ConversationDAG(loader, "session-uuid")

# Get message relationships
parent = dag.get_parent(msg.uuid)
children = dag.get_children(msg.uuid)
ancestry = dag.get_ancestry_path(msg.uuid)
subtree = dag.get_subtree(msg.uuid)
```

### 3. Thread Detection

Identifies conversation threads:
- **Main thread**: Primary conversation flow
- **Side discussions**: Sidechain/subagent conversations
- **Orphaned threads**: Disconnected message sequences

```python
session = dag.to_session()

# Access threads
main = session.main_thread
sides = session.side_threads
orphans = session.orphans

for thread in session.threads:
    print(f"{thread.thread_type}: {thread.message_count} messages")
```

### 4. Corruption Analysis

Computes corruption scores (0.0 = perfect, 1.0 = broken):
- Message-level: missing fields, invalid references
- Thread-level: fragmentation, disconnection
- Session-level: overall structural health

```python
# Message corruption
for msg in session.messages:
    if msg.corruption_score > 0.3:
        print(f"Corrupted: {msg.uuid}")

# Thread corruption
for thread in session.threads:
    print(f"{thread.thread_id}: {thread.corruption_score:.2f}")

# Session corruption
print(f"Session health: {session.corruption_score:.2f}")
```

### 5. Structural Validation

Validates DAG properties:
- Cycle detection (ensures DAG property)
- Missing parent warnings
- Component analysis
- Statistics generation

```python
validation = dag.validate_structure()

if not validation['is_valid']:
    print("Errors:", validation['errors'])

print("Stats:", validation['stats'])
```

## Usage Examples

### Basic Analysis

```python
from pathlib import Path
from riff.graph import JSONLLoader, ConversationDAG

# Load session
conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
loader = JSONLLoader(conversations_dir)
dag = ConversationDAG(loader, "794650a6-84a5-446b-879c-639ee85fbde4")

# Convert to session
session = dag.to_session()

# Print statistics
print(f"Messages: {session.message_count}")
print(f"Threads: {session.thread_count}")
print(f"Orphans: {session.orphan_count}")
print(f"Corruption: {session.corruption_score:.2f}")
```

### Thread Analysis

```python
# Analyze main thread
if session.main_thread:
    thread = session.main_thread
    print(f"Main thread: {thread.message_count} messages")

    first = thread.first_message
    last = thread.last_message

    print(f"Started: {first.timestamp}")
    print(f"Ended: {last.timestamp}")

# Analyze side discussions
for thread in session.side_threads:
    print(f"Side: {thread.thread_id} ({thread.message_count} msgs)")
```

### Finding Orphans

```python
# Find orphaned messages
orphaned_messages = [m for m in session.messages if m.is_orphaned]

print(f"Found {len(orphaned_messages)} orphaned messages")

for msg in orphaned_messages:
    print(f"  {msg.uuid}: parent={msg.parent_uuid}")
```

### Path Analysis

```python
# Find path from root to message
msg = session.messages[50]
path = dag.get_ancestry_path(msg.uuid)

print(f"Path to message {msg.uuid}:")
for i, ancestor in enumerate(path):
    indent = "  " * i
    print(f"{indent}{ancestor.type.value}: {ancestor.content[:50]}")
```

## Testing

Comprehensive pytest suite with 39 tests:

```bash
# Run all graph tests
pytest tests/graph/ -v

# Run specific test file
pytest tests/graph/test_dag.py -v

# Run with coverage
pytest tests/graph/ --cov=riff.graph --cov-report=html
```

Test coverage:
- **models.py**: Dataclass validation, enum conversion, properties
- **loaders.py**: JSONL parsing, content extraction, metadata preservation
- **dag.py**: Graph construction, traversal, thread detection, validation

## Performance

Designed for efficiency:
- O(1) message lookup via UUID index
- O(n) DAG construction (single pass)
- O(n) thread detection (connected components)
- Handles sessions with 100+ messages efficiently

Tested with real Claude sessions:
- 159 messages processed in <0.1s
- 5 threads detected correctly
- Full validation in <0.1s

## Future Enhancements

Planned features:
1. Semantic topic detection (NLP-based)
2. Time-based filtering and slicing
3. Cross-session thread linking
4. Interactive visualization
5. Repair suggestions for corrupted sessions

## Integration Points

The graph module serves as foundation for:
- **riff search**: Content search within conversation structure
- **riff repair**: Session corruption detection and repair
- **riff viz**: Interactive conversation visualization
- **Memory systems**: Integration with memory-kb and Anytype

## API Reference

### Core Classes

#### Message
```python
@dataclass
class Message:
    uuid: str
    parent_uuid: Optional[str]
    type: MessageType
    content: str
    timestamp: str
    session_id: str
    is_sidechain: bool = False
    semantic_topic: Optional[str] = None
    thread_id: Optional[str] = None
    is_orphaned: bool = False
    corruption_score: float = 0.0
    metadata: dict[str, any] = field(default_factory=dict)
```

#### Thread
```python
@dataclass
class Thread:
    thread_id: str
    messages: list[Message]
    thread_type: ThreadType
    semantic_topic: Optional[str] = None
    corruption_score: float = 0.0
    parent_thread_id: Optional[str] = None

    @property
    def message_count(self) -> int
    @property
    def first_message(self) -> Message
    @property
    def last_message(self) -> Message
```

#### Session
```python
@dataclass
class Session:
    session_id: str
    messages: list[Message]
    threads: list[Thread]
    orphans: list[Thread]
    corruption_score: float = 0.0
    metadata: dict[str, any] = field(default_factory=dict)

    @property
    def message_count(self) -> int
    @property
    def thread_count(self) -> int
    @property
    def orphan_count(self) -> int
    @property
    def main_thread(self) -> Optional[Thread]
    @property
    def side_threads(self) -> list[Thread]

    def get_thread_by_id(self, thread_id: str) -> Optional[Thread]
    def get_message_by_uuid(self, uuid: str) -> Optional[Message]
```

#### ConversationDAG
```python
class ConversationDAG:
    def __init__(self, loader: ConversationStorage, session_id: str)

    def get_message(self, uuid: str) -> Optional[Message]
    def get_children(self, uuid: str) -> list[Message]
    def get_parent(self, uuid: str) -> Optional[Message]
    def get_ancestry_path(self, uuid: str) -> list[Message]
    def get_subtree(self, uuid: str) -> list[Message]
    def to_session(self) -> Session
    def validate_structure(self) -> dict[str, any]
```

#### JSONLLoader
```python
class JSONLLoader(ConversationStorage):
    def __init__(self, conversations_dir: Path | str)

    def load_messages(self, session_id: str) -> list[Message]
    def save_session(self, session: Session) -> None
    def update_message(self, message: Message) -> None
    def list_sessions(self) -> list[str]
    def session_exists(self, session_id: str) -> bool
```

## File Locations

```
/Users/tryk/nabia/tools/riff-cli/
├── src/riff/graph/
│   ├── __init__.py          # Module exports
│   ├── models.py            # Data classes (377 lines)
│   ├── loaders.py           # Storage abstraction (327 lines)
│   └── dag.py               # DAG construction (502 lines)
├── tests/graph/
│   ├── __init__.py
│   ├── test_models.py       # Model tests (255 lines)
│   ├── test_loaders.py      # Loader tests (112 lines)
│   └── test_dag.py          # DAG tests (180 lines)
└── docs/
    └── GRAPH_MODULE.md      # This file
```

## Dependencies

Core dependencies (from pyproject.toml):
- Python 3.13+
- No external dependencies beyond stdlib

Development dependencies:
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- mypy >= 1.0.0

## License

Part of riff-cli, built for NabiOS federation.
