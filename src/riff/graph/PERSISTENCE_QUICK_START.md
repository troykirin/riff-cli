# Persistence Layer - Quick Start

Fast-track guide to using the riff-cli persistence layer for JSONL repairs.

## Installation

The persistence layer is part of the `riff.graph` module:

```python
from riff.graph.persistence import (
    RepairOperation,
    RepairSnapshot,
    JSONLRepairWriter,
    create_repair_writer,
)
```

## 5-Minute Quick Start

### 1. Create a Repair Writer

```python
from riff.graph.persistence import create_repair_writer

writer = create_repair_writer()
```

### 2. Define a Repair

```python
from riff.graph.persistence import RepairOperation

repair = RepairOperation(
    message_uuid="msg-uuid-to-fix",
    field="parentUuid",
    old_value="missing-parent-uuid",
    new_value="correct-parent-uuid",
    reason="Fix orphaned message",
)
```

### 3. Apply Repair

```python
from pathlib import Path

session_id = "your-session-id"
jsonl_path = Path("/path/to/session.jsonl")

success, backup_path = writer.repair_with_backup(
    session_id=session_id,
    jsonl_path=jsonl_path,
    repairs=[repair],
)

if success:
    print(f"✓ Repair applied! Backup at: {backup_path}")
else:
    print("✗ Repair failed")
```

### 4. Undo if Needed

```python
# Show undo history
history = writer.show_undo_history(session_id)
print(f"Available undo points: {len(history)}")

# Undo last repair
writer.undo_last_repair(jsonl_path, session_id)
```

## Common Use Cases

### Fix Orphaned Messages

```python
from riff.graph import ConversationDAG, JSONLLoader
from riff.graph.persistence import RepairOperation, create_repair_writer

# Load conversation
loader = JSONLLoader(conversations_dir)
dag = ConversationDAG(loader, session_id)
session = dag.to_session()

# Find orphans
orphans = [msg for msg in session.messages if msg.is_orphaned]

# Create repairs
repairs = []
main_parent = session.main_thread.messages[0].uuid

for orphan in orphans:
    repairs.append(RepairOperation(
        message_uuid=orphan.uuid,
        field="parentUuid",
        old_value=orphan.parent_uuid,
        new_value=main_parent,
        reason="Reattach orphan to main thread",
    ))

# Apply
writer = create_repair_writer()
writer.repair_with_backup(session_id, jsonl_path, repairs)
```

### Batch Repairs

```python
repairs = [
    RepairOperation(
        message_uuid="msg-1",
        field="parentUuid",
        old_value="old-parent-1",
        new_value="new-parent-1",
    ),
    RepairOperation(
        message_uuid="msg-2",
        field="parentUuid",
        old_value="old-parent-2",
        new_value="new-parent-2",
    ),
]

writer.repair_with_backup(session_id, jsonl_path, repairs)
```

### Manual Rollback

```python
# List backups
backups = writer.list_backups(session_id)

# Choose a backup
target_backup = backups[0]  # Most recent

# Rollback
writer.rollback_to_backup(jsonl_path, target_backup)
```

## Key Concepts

### Atomic Updates

All writes are atomic:
1. Write to `.jsonl.tmp`
2. Validate integrity
3. Rename (atomic operation)

### Automatic Backups

Every repair creates a timestamped backup in `~/.riff/backups/{session-id}/`

### Undo Stack

- Last 10 operations per session
- Persisted to disk
- Survives restarts

### Safety First

- Never modifies original without backup
- Validates JSONL after every write
- Returns success/failure status

## Directory Structure

```
~/.riff/
├── backups/
│   └── {session-id}/
│       ├── 20250120_100000_123456.jsonl
│       ├── 20250120_100130_789012.jsonl
│       └── ...
└── undo/
    └── {session-id}.json
```

## Testing Your Changes

```python
# Before applying to production
import tempfile
import shutil

# Create test copy
test_path = Path(tempfile.mktemp(suffix=".jsonl"))
shutil.copy(jsonl_path, test_path)

# Test repairs on copy
writer.repair_with_backup(session_id, test_path, repairs)

# Verify results
loader = JSONLLoader(test_path.parent)
dag = ConversationDAG(loader, session_id)
session = dag.to_session()

print(f"Orphans after repair: {session.orphan_count}")
```

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
    print(f"Invalid repair: {e}")
```

## Next Steps

1. Read full documentation: `PERSISTENCE.md`
2. Run examples: `python example_persistence.py`
3. Run tests: `pytest test_persistence.py -v`

## Common Pitfalls

### Wrong UUID Format

```python
# ✗ Wrong
repair = RepairOperation(
    message_uuid="msg-orphan",  # Must match actual UUID in JSONL
    ...
)

# ✓ Correct - use actual UUIDs from JSONL
repair = RepairOperation(
    message_uuid="01234567-89ab-cdef-0123-456789abcdef",
    ...
)
```

### Missing Validation

```python
# ✗ Wrong - no validation
writer.repair_with_backup(session_id, jsonl_path, repairs)

# ✓ Correct - check success
success, backup = writer.repair_with_backup(session_id, jsonl_path, repairs)
if not success:
    print("Repair failed")
```

### Modifying Original File

```python
# ✗ Wrong - modifying without backup
with open(jsonl_path, "w") as f:
    # Direct modification
    ...

# ✓ Correct - use repair writer
writer.repair_with_backup(session_id, jsonl_path, repairs)
```

## FAQ

**Q: Can I undo multiple repairs at once?**

A: Currently, `undo_last_repair()` undoes one snapshot at a time. Call it multiple times to undo multiple repairs.

**Q: What happens if a repair fails mid-batch?**

A: Batch repairs stop at the first failure. Partial repairs are tracked in the returned list.

**Q: Can I roll back to any point in time?**

A: Yes! Use `list_backups()` to see all backups, then `rollback_to_backup()` to restore any specific backup.

**Q: Are repairs reversible?**

A: Yes, if a backup exists. The undo system tracks all repairs and maintains backups for rollback.

**Q: What fields can be repaired?**

A: Any field in the JSONL message. The `field` parameter in `RepairOperation` can be `"parentUuid"`, `"timestamp"`, or any other JSONL field.

## Support

For issues or questions:
- See full docs: `PERSISTENCE.md`
- Check examples: `example_persistence.py`
- Run tests: `test_persistence.py`
