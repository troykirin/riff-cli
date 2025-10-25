# Persistence Layer

Complete JSONL repair writer with undo/rollback capabilities for riff-cli conversation graph repairs.

## Overview

The persistence layer provides safe, atomic operations for modifying Claude conversation JSONL files with full undo/rollback support.

**Key Features:**
- Atomic JSONL updates (write-to-temp, then rename)
- Timestamped backups before each repair
- Session-scoped undo stack (last 10 operations)
- Persistent undo history to disk
- JSONL validation after each write
- Safe rollback to any backup point

## Architecture

```
~/.riff/
├── backups/
│   └── {session-id}/
│       ├── 20250120_100000_123456.jsonl  # Timestamped backups
│       ├── 20250120_100130_789012.jsonl
│       └── ...
└── undo/
    └── {session-id}.json  # Persistent undo stack
```

## Core Components

### RepairOperation

Represents a single repair operation on a message.

```python
@dataclass
class RepairOperation:
    message_uuid: str          # UUID of message being repaired
    field: str                 # Field to modify (e.g., "parentUuid")
    old_value: any            # Original value
    new_value: any            # New value
    timestamp: str            # ISO8601 timestamp
    reason: str               # Optional explanation
```

### RepairSnapshot

Snapshot of repairs applied to a session.

```python
@dataclass
class RepairSnapshot:
    session_id: str                    # Session identifier
    timestamp: datetime                # Snapshot creation time
    original_jsonl_path: Path          # Path to session JSONL
    backup_path: Path                  # Path to backup
    repairs_applied: List[RepairOperation]
    can_rollback: bool                 # Backup exists
```

### JSONLRepairWriter

Main writer class for persisting repairs with undo support.

## Usage

### Basic Repair

```python
from riff.graph.persistence import RepairOperation, create_repair_writer

# Create writer
writer = create_repair_writer()

# Define repair
repair = RepairOperation(
    message_uuid="orphaned-msg-uuid",
    field="parentUuid",
    old_value="missing-parent",
    new_value="valid-parent-uuid",
    reason="Reattach orphan to main thread",
)

# Apply repair with automatic backup
success, backup_path = writer.repair_with_backup(
    session_id="your-session-id",
    jsonl_path=Path("/path/to/session.jsonl"),
    repairs=[repair],
)
```

### Batch Repairs

```python
repairs = [
    RepairOperation(
        message_uuid="orphan-1",
        field="parentUuid",
        old_value="missing-1",
        new_value="main-parent",
        reason="Reattach orphan 1",
    ),
    RepairOperation(
        message_uuid="orphan-2",
        field="parentUuid",
        old_value="missing-2",
        new_value="main-parent",
        reason="Reattach orphan 2",
    ),
]

success, backup_path = writer.repair_with_backup(
    session_id="your-session-id",
    jsonl_path=jsonl_path,
    repairs=repairs,
)
```

### Undo Last Repair

```python
# Show undo history
history = writer.show_undo_history("your-session-id")

for snapshot in history:
    print(f"Timestamp: {snapshot.timestamp}")
    print(f"Repairs: {len(snapshot.repairs_applied)}")

# Undo last repair
success = writer.undo_last_repair(jsonl_path, "your-session-id")
```

### Rollback to Specific Backup

```python
# List backups
backups = writer.list_backups("your-session-id")

# Roll back to specific backup
target_backup = backups[1]  # Second-most-recent
success = writer.rollback_to_backup(jsonl_path, target_backup)
```

## API Reference

### JSONLRepairWriter

#### Backup Management

```python
create_backup(session_id: str, jsonl_path: Path) -> Path
    """Create timestamped backup of JSONL file."""

list_backups(session_id: str) -> List[Path]
    """List all backups for a session (newest first)."""

delete_backup(backup_path: Path) -> bool
    """Delete a specific backup file."""
```

#### Repair Operations

```python
apply_repair(jsonl_path: Path, repair_op: RepairOperation) -> bool
    """Apply a single repair operation atomically."""

apply_batch_repairs(jsonl_path: Path, repairs: List[RepairOperation])
    -> Tuple[bool, List[RepairOperation]]
    """Apply multiple repairs in order. Stops on first failure."""
```

#### Rollback Operations

```python
rollback_to_backup(jsonl_path: Path, backup_path: Path) -> bool
    """Restore JSONL from backup."""
```

#### Undo System

```python
push_repair_snapshot(
    session_id: str,
    jsonl_path: Path,
    backup_path: Path,
    repairs: List[RepairOperation],
) -> None
    """Push a new repair snapshot onto the undo stack."""

show_undo_history(session_id: str) -> List[RepairSnapshot]
    """List all available undo points (newest first)."""

undo_last_repair(jsonl_path: Path, session_id: str) -> bool
    """Undo the last repair operation."""
```

#### Workflow Helpers

```python
repair_with_backup(
    session_id: str,
    jsonl_path: Path,
    repairs: List[RepairOperation],
) -> Tuple[bool, Optional[Path]]
    """Complete workflow: backup, apply repairs, push snapshot."""
```

## Integration with DAG Analysis

```python
from riff.graph import ConversationDAG, JSONLLoader
from riff.graph.persistence import RepairOperation, create_repair_writer

# Load conversation
loader = JSONLLoader(conversations_dir)
dag = ConversationDAG(loader, session_id)
session = dag.to_session()

# Find orphaned messages
orphans = [msg for msg in session.messages if msg.is_orphaned]

# Create repair operations
repairs = []
main_parent = session.main_thread.messages[0].uuid

for orphan in orphans:
    repair = RepairOperation(
        message_uuid=orphan.uuid,
        field="parentUuid",
        old_value=orphan.parent_uuid,
        new_value=main_parent,
        reason=f"Auto-repair orphan (corruption={orphan.corruption_score:.2f})",
    )
    repairs.append(repair)

# Apply repairs
writer = create_repair_writer()
success, backup_path = writer.repair_with_backup(
    session_id=session_id,
    jsonl_path=jsonl_path,
    repairs=repairs,
)
```

## Safety Features

### Atomic Writes

All JSONL modifications use atomic write pattern:
1. Write to temporary file (`.jsonl.tmp`)
2. Validate integrity
3. Atomic rename (overwrites original)

### Automatic Backups

Every repair operation creates a timestamped backup before making changes.

### Validation

JSONL files are validated after each write using `JSONLLoader` to ensure structural integrity.

### Undo Stack

- In-memory undo stack (last 10 operations per session)
- Persisted to disk for cross-session recovery
- Automatic cleanup of old snapshots

### Rollback Protection

- `can_rollback` flag indicates if backup exists
- Validation before rollback
- Error handling for missing backups

## Error Handling

```python
try:
    success, backup = writer.repair_with_backup(
        session_id=session_id,
        jsonl_path=jsonl_path,
        repairs=repairs,
    )

    if not success:
        print("Repair failed - check logs")

except FileNotFoundError:
    print("JSONL file not found")

except ValueError as e:
    print(f"Invalid repair operation: {e}")

except IOError as e:
    print(f"I/O error: {e}")
```

## Testing

Comprehensive test suite in `test_persistence.py`:

```bash
# Run tests
pytest src/riff/graph/test_persistence.py -v

# Run specific test
pytest src/riff/graph/test_persistence.py::test_apply_repair -v
```

Test coverage includes:
- RepairOperation serialization
- Backup creation and management
- Single and batch repairs
- Atomic writes
- Rollback operations
- Undo system
- Undo stack size limits
- Full workflow integration

## Examples

See `example_persistence.py` for complete usage examples:

```bash
python src/riff/graph/example_persistence.py
```

Examples include:
1. Basic repair workflow
2. Batch repair workflow
3. Undo workflow
4. Integrated DAG analysis workflow
5. Backup management
6. Rollback to specific backup

## Best Practices

### 1. Always Use repair_with_backup()

Prefer the complete workflow helper over manual steps:

```python
# ✓ Good
success, backup = writer.repair_with_backup(session_id, path, repairs)

# ✗ Avoid
backup = writer.create_backup(session_id, path)
writer.apply_batch_repairs(path, repairs)
writer.push_repair_snapshot(session_id, path, backup, repairs)
```

### 2. Validate Before Repair

Check that repairs are valid before applying:

```python
# Load session to verify message exists
loader = JSONLLoader(conversations_dir)
dag = ConversationDAG(loader, session_id)
session = dag.to_session()

# Verify message exists
target_message = session.get_message_by_uuid(repair.message_uuid)
if target_message is None:
    raise ValueError(f"Message not found: {repair.message_uuid}")
```

### 3. Use Descriptive Reasons

Always provide clear reasons for repairs:

```python
RepairOperation(
    message_uuid=orphan.uuid,
    field="parentUuid",
    old_value=orphan.parent_uuid,
    new_value=suggested_parent,
    reason=f"Auto-repair: reattach orphan (corruption={orphan.corruption_score:.2f})",
)
```

### 4. Test Repairs on Copies First

Test repair strategies on backup copies before applying to production data:

```bash
cp ~/.claude/projects/-Users-tryk--nabi/{session-id}.jsonl /tmp/test-session.jsonl
# Test repairs on /tmp/test-session.jsonl
```

### 5. Keep Backups

Don't delete backups unless storage is critical. They provide insurance against unexpected issues.

## Limitations

### Undo Stack Size

- In-memory: Last 10 operations per session
- Disk persistence ensures recovery across sessions
- Oldest snapshots are automatically removed

### Backup Storage

- Backups accumulate over time
- Manual cleanup required for long-term storage management
- Consider implementing backup retention policy

### Concurrent Access

- Not designed for concurrent writes
- Use file locking if multiple processes need access

## Future Enhancements

Potential improvements:

1. **Compression**: Compress old backups to save space
2. **Retention Policy**: Automatic backup cleanup (keep last N days)
3. **Diff-based Undo**: Store diffs instead of full backups
4. **Repair Validation**: Pre-flight checks before applying repairs
5. **Repair Templates**: Pre-defined repair patterns for common issues
6. **Batch Optimization**: Optimize batch repairs with single file read
7. **Conflict Resolution**: Handle concurrent modifications
8. **Audit Trail**: Comprehensive logging of all repair operations

## Contributing

When adding new features to the persistence layer:

1. Add comprehensive docstrings
2. Include type hints
3. Write tests in `test_persistence.py`
4. Update this README
5. Add usage examples to `example_persistence.py`

## License

Part of riff-cli project.
