# Conversation Repair Workflow Guide

## Overview

The riff repair workflow enables you to:
- **Detect** orphaned messages in Claude conversation sessions
- **Suggest** optimal parent messages using semantic similarity
- **Preview** repairs with detailed diffs before applying
- **Apply** repairs atomically with automatic backups
- **Undo** repairs with one-command rollback

## Phase 6A Completion

**Status**: ✅ Production Ready

All components integrated and tested:
- ✅ Repair Engine (orphan detection, parent suggestions)
- ✅ Persistence Layer (atomic writes, undo stack, rollback)
- ✅ TUI Integration (m/r/u keybindings with modals)
- ✅ RepairManager coordinator
- ✅ CLI integration with full workflow support

## Quick Start

### 1. Open a Session for Repair

```bash
riff graph 794650a6-84a5-446b-879c-639ee85fbde4
```

Shows:
- Session statistics (orphaned threads, corruption score)
- ASCII tree visualization with orphaned messages marked `[!]`
- Interactive vim-style TUI

### 2. Mark Messages for Repair

Navigate to a message and press **`m`** to mark/unmark:

```
[*] Message is marked for repair
[!] Message is orphaned (no valid parent)
```

Marked messages persist during your session for batch processing.

### 3. Repair a Single Message

Position cursor on orphaned message (marked `[!]`) and press **`r`**:

```
┌─ REPAIR PREVIEW ───────────────────────┐
│ Message: "What's the best way to...    │
│ Current Parent: null                   │
│                                        │
│ ━━━ SUGGESTED REPAIR (1/3) ━━━        │
│ Parent: "Let me help you understand"   │
│ Similarity: 87.5%                      │
│ Reason: semantic similarity            │
│                                        │
│ Diff:                                  │
│ - parentUuid: null                     │
│ + parentUuid: abc-def-123              │
│                                        │
│        [Y]es / [N]o                    │
└────────────────────────────────────────┘
```

Press **`Y`** to:
1. ✓ Validate repair (no cycles, timestamp ordering)
2. ✓ Create backup at `~/.riff/backups/{session-id}/{timestamp}.jsonl`
3. ✓ Apply repair to JSONL (atomic write)
4. ✓ Reload DAG automatically

Press **`N`** to cancel or **`>`** for next candidate.

### 4. View Repair History

Press **`u`** to show undo stack:

```
┌─ UNDO STACK ───────────────────────────┐
│ Available Undo Points (Most Recent):   │
│                                        │
│ 1. Repairs: 3                          │
│    Time: 2025-01-20T15:30:45           │
│    Backup: 2025-01-20T15_30_45.jsonl   │
│                                        │
│ 2. Repairs: 1                          │
│    Time: 2025-01-20T15:28:12           │
│    Backup: 2025-01-20T15_28_12.jsonl   │
│                                        │
│ Undo will restore JSONL and reload.    │
│        [Y]es / [N]o                    │
└────────────────────────────────────────┘
```

Press **`Y`** to undo last repair (rollback to previous backup).

## Repair Engine Details

### Orphan Detection

Messages are identified as orphaned if:
- `parentUuid` is `null` AND not a root message
- Parent UUID points to non-existent message
- Timestamp anomalies (created before parent, etc.)

Corruption score (0.0-1.0) combines:
- Missing parent UUID (+0.4 weight)
- Timestamp violations (+0.2 weight)
- Sidechain flag (+0.3 weight)
- Content markers (+0.1 weight)

### Parent Suggestion Algorithm

For each orphaned message, the system ranks candidates by:

**50% - Semantic Similarity**
- Keyword overlap analysis
- Topic clustering
- Content matching

**30% - Temporal Continuity**
- Created within 5 minutes = max score
- Score decays with time distance
- Prevents illogical ordering

**20% - Message Type Compatibility**
- User → Assistant flow natural
- Assistant → User flow natural
- System messages considered

Example scoring:
```
Candidate A: Semantic 0.85 × 0.5 = 0.425
             Time 0.80 × 0.3 = 0.240
             Type 1.0 × 0.2 = 0.200
             Total = 0.865 (87%)

Candidate B: Semantic 0.60 × 0.5 = 0.300
             Time 0.90 × 0.3 = 0.270
             Type 0.5 × 0.2 = 0.100
             Total = 0.670 (67%)
```

### Repair Validation

Before applying, the system validates:

1. **Parent Exists**: UUID must be in current session
2. **No Cycles**: Repairing can't create circular dependency
3. **Timestamp Logic**: Parent must be created before child
4. **Referential Integrity**: All references remain valid

If validation fails:
```
┌─ REPAIR VALIDATION FAILED ─────────────┐
│ Error: Timestamp violation             │
│ Parent created after child             │
│ (Parent: Jan 20 15:30, Child: 15:25)  │
└────────────────────────────────────────┘
```

## Persistence & Undo

### Backup Strategy

When repair applied:
```
~/.riff/backups/
└── {session-id}/
    ├── 2025-01-20T15_30_45.jsonl  ← Before repair #1
    ├── 2025-01-20T15_31_12.jsonl  ← Before repair #2
    └── 2025-01-20T15_32_00.jsonl  ← Before repair #3
```

Each backup is a full JSONL snapshot before repair applied.

### Undo Stack

```
~/.riff/undo/
└── {session-id}.json

{
  "repairs": [
    {
      "message_id": "msg-123",
      "old_parent": null,
      "new_parent": "msg-456",
      "timestamp": "2025-01-20T15:30:45",
      "backup": ".../2025-01-20T15_30_45.jsonl"
    }
  ]
}
```

Undo stack persists between sessions for safe recovery.

### Atomic Operations

Repair write flow:
```
1. Create backup
   └─ cp JSONL BACKUP.jsonl

2. Write to temp file
   └─ echo updated messages > TEMP.jsonl

3. Validate temp file
   └─ Parse JSONL, count messages

4. Atomic rename
   └─ mv TEMP.jsonl JSONL

5. Reload DAG
   └─ Re-parse from disk
```

On any error, original JSONL untouched and backup preserved.

## Examples

### Example 1: Single Orphan Repair

**Session**: 794650a6 (from user's initial report)
**Corruption**: 24.1% (98/406 messages orphaned)

Steps:
```bash
$ riff graph 794650a6
# TUI opens, shows [!] on lines 156, 203, 245, etc.

# Navigate to line 156 (orphaned message)
# Press 'r' → see repair preview with 87% similarity
# Press 'Y' → repair applied
# View updated corruption score: 23.8%
# Press 'u' → undo history shows 1 repair
```

### Example 2: Batch Mark & Review

Scenario: Multiple orphans need repair

```bash
# Navigate through session
j/k      # Move to orphaned messages
m        # Mark several messages (shown with [*])
r        # Show repair preview
Y        # Apply
r        # Next message
Y        # Apply
u        # View undo history (now shows 2 repairs)
```

### Example 3: Undo & Retry

Scenario: Repair didn't work as expected

```bash
# Applied repairs, but corruption score didn't improve
u        # Show undo stack
Y        # Undo last repair
# DAG reloads, back to previous state
# Try different candidates or manual repairs
```

## Files & Architecture

### Core Modules

**`src/riff/graph/repair_manager.py`** (407 lines)
- Coordinates repair engine, persistence, DAG
- Handles orphan detection and parent suggestions
- Manages undo/rollback

**`src/riff/graph/repair.py`** (550 lines)
- ConversationRepairEngine class
- Orphan detection algorithm
- Parent suggestion with semantic analysis
- Repair validation logic

**`src/riff/graph/persistence.py`** (656 lines)
- JSONLRepairWriter class
- Atomic backup + write + reload
- Undo stack management
- Rollback capabilities

**`src/riff/tui/graph_navigator.py`** (enhanced)
- ConversationGraphNavigator with repair support
- m/r/u keybinding handlers
- Repair confirmation modals with Y/N
- Marked messages UI

### CLI Integration

**`src/riff/cli.py`**
- Passes session_id, jsonl_path, loader to navigator
- Initializes RepairManager in TUI
- Error handling for missing repair components

## Testing

### Unit Tests

**`tests/graph/test_repair.py`** (13 tests)
- Orphan detection
- Parent suggestion algorithm
- Repair validation (cycles, timestamps)
- Similarity scoring

**`tests/graph/test_persistence.py`** (20 tests)
- Backup creation
- Atomic repairs
- Batch operations
- Undo/rollback
- Persistence recovery

### Manual Testing

Test with orphaned session:
```bash
# This session has 24.1% corruption rate
riff graph 794650a6

# In TUI:
# 1. Navigate to orphaned message
# 2. Press 'r' to see repair preview
# 3. Press 'Y' to apply
# 4. Corruption score should improve
# 5. Press 'u' to see backup history
# 6. Press 'Y' to undo and verify rollback
```

## Limitations & Future Work

### Current Limitations

- Similarity scoring is heuristic-based (keyword overlap, not ML embeddings)
- Only CLI-based repair (no UI batch export yet)
- No cross-session linking (Phase 7)
- SurrealDB caching not yet implemented (Phase 6B)

### Phase 6B: SurrealDB Integration

Planned features:
- Persistent caching of repaired sessions
- Fast queries without JSONL re-parsing
- Materialized views for corrupted sessions
- Time-range queries for session fragments

### Phase 7: Memory Curation

Planned features:
- Bookmark / tag / annotate messages
- Export curated sessions
- Cross-conversation linking
- Memory DAW (Digital Audio Workstation style interface)

## Troubleshooting

### "Repair Engine Not Initialized"

Cause: JSONL path or loader not found
Fix: Ensure session is opened with full path or UUID

### "No Repair Candidates Found"

Cause: All messages incompatible (temporal, type, content)
Fix: Check message content; may need manual review

### Backup Not Created

Cause: Permissions or disk space
Fix: Ensure `~/.riff/backups/` writable

### DAG Reload Failed

Cause: JSONL corrupted during write
Fix: Undo repair with 'u', check disk/permissions

## References

- SEMANTIC_DAG_DESIGN.md - Full architecture
- PERSISTENCE.md - Persistence API reference
- REPAIR_ENGINE.md - Repair algorithm details
- SURREALDB_INTEGRATION_ANALYSIS.md - Phase 6B planning
