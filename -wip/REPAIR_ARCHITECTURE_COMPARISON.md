# Riff Repair Architecture: Comparative Analysis
## Missing vs Duplicate tool_results - Design Patterns

**Analysis Date**: 2025-11-07
**Status**: Architecture Review
**Scope**: Riff repair system design patterns

---

## High-Level Architecture

```
Riff Repair System (340K LOC codebase)
│
├── Classic Path (Your Current Location)
│   ├── src/riff/classic/commands/scan.py (102 lines)
│   │   └─ Detects MISSING tool_results (cross-message)
│   │
│   ├── src/riff/classic/commands/fix.py (95 lines)
│   │   └─ Adds synthetic tool_results to user messages
│   │
│   └── src/riff/classic/utils.py
│       └─ Shared utilities (get_message_role, normalize_structure)
│
└── Graph Path (Different Purpose)
    ├── src/riff/graph/repair.py (624 lines)
    │   ├─ ConversationRepairEngine
    │   ├─ RepairOperation
    │   └─ Semantic analysis + DAG validation
    │
    └── Used for: Orphaned message graph reconstruction
        Not used for: tool_result issues
```

---

## Problem Spectrum

### Tier 1: Missing Relationships (Current Implementation ✅)

**Problem**: No response to tool_use

```json
{
  "role": "assistant",
  "content": [{"type": "tool_use", "id": "call_123"}]
}
[MISSING: tool_result for call_123]
{
  "role": "user",
  "content": [...]  // No tool_result block!
}
```

**Detection**: Cross-message boundary check
```python
pending_tool_uses = [call_123]
seen_tool_results = []
missing = pending_tool_uses - seen_tool_results = [call_123]
```

**Repair**: Add synthetic result block
```python
# Prepend to user message
{"type": "tool_result", "tool_use_id": "call_123", "is_error": True}
```

**Why This Works**:
- Straightforward math (set difference)
- Adds data (safe operation)
- Error-flagged (indicates synthetic)

---

### Tier 2: Duplicate Within Message (Missing Implementation ❌)

**Problem**: Multiple responses to same tool_use

```json
{
  "role": "user",
  "content": [
    {"type": "tool_result", "tool_use_id": "call_123", "content": "First"},
    {"type": "tool_result", "tool_use_id": "call_123", "content": "Second"}
    // ^^^ DUPLICATE! Claude will reject or ignore second
  ]
}
```

**Detection**: Within-message occurrence count
```python
id_counts = {"call_123": 2}
duplicates = [id for id, count in id_counts.items() if count > 1]
```

**Repair**: Remove duplicate entries (keep first)
```python
content = [
    {"type": "tool_result", "tool_use_id": "call_123", "content": "First"},
    # Second one removed
]
```

**Why This Isn't Implemented**:
- Not a blocking issue (missing is worse)
- Set-based tracking naturally hides duplicates
- Low priority (duplicates are rare)

---

### Tier 3: Orphaned Result (Not Implemented, Harder Problem ❓)

**Problem**: Result without matching tool_use

```json
{
  "role": "user",
  "content": [
    {"type": "tool_result", "tool_use_id": "call_UNKNOWN"}
    // ^^^ No assistant message has tool_use with this ID!
  ]
}
```

**Detection**: Requires full conversation scan
```python
all_tool_uses = {call_123, call_456}
all_tool_results = {call_123, call_UNKNOWN}
orphaned = all_tool_results - all_tool_uses
```

**Repair**: ???
- Can't guess the matching tool_use
- Could move to different message
- Could mark as error
- Probably delete

**Why This Isn't Implemented**:
- Requires complex semantic matching
- No safe "default" behavior
- Rare in practice

---

## Design Pattern Comparison

### Pattern 1: Missing Detection (Tier 1) - What Exists

```
┌─────────────────────────────────────────────────────────┐
│         MISSING TOOL_RESULT PATTERN                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Scope:      Cross-Message (boundary)                  │
│  State:      pending=[list of IDs]                     │
│  Algorithm:  Set difference                            │
│  Trigger:    User message after assistant with tool   │
│  Action:     Prepend synthetic result                  │
│                                                         │
│  Data Flow:                                            │
│  ┌─ Assistant msg → pending=[call_123]               │
│  ├─ User msg    → seen={} → missing=[call_123]        │
│  └─ Generate    → prepend tool_result(call_123)       │
│                                                         │
│  Safety: HIGH (adds error-marked data)                │
│  Code Size: ~50 lines                                  │
│  Complexity: Medium (state tracking)                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Implementation Location**: `scan.py` + `fix.py`

```python
# scan.py: Detect
for msg in messages:
    if assistant: pending.extend(tool_use_ids)
    if user: seen.update(tool_result_ids)
            missing = pending - seen

# fix.py: Repair
if missing:
    prepend(synthetic_tool_results)
```

---

### Pattern 2: Duplicate Detection (Tier 2) - What's Missing

```
┌─────────────────────────────────────────────────────────┐
│         DUPLICATE TOOL_RESULT PATTERN                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Scope:      Within-Message (content)                  │
│  State:      id_count={id: count}                      │
│  Algorithm:  Frequency counting                        │
│  Trigger:    User message content scan                 │
│  Action:     Remove excess occurrences                 │
│                                                         │
│  Data Flow:                                            │
│  ┌─ User msg → content=[tool_result, tool_result]    │
│  ├─ Count     → id_count={call_123: 2}                │
│  └─ Filter    → keep only first of each               │
│                                                         │
│  Safety: VERY HIGH (removes only redundant data)       │
│  Code Size: ~20 lines                                  │
│  Complexity: Low (single-pass filter)                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Implementation Location**: `scan.py` + `fix.py`

```python
# scan.py: Detect
for msg in messages:
    if user:
        id_count = {}
        for content_item in content:
            if tool_result: id_count[id] += 1
        duplicates = [id for id, count if count > 1]

# fix.py: Repair
seen_ids = set()
filtered = []
for item in content:
    if tool_result and item.id in seen_ids: continue
    filtered.append(item)
```

---

## Side-by-Side Comparison

| Aspect | Missing (Tier 1) | Duplicate (Tier 2) |
|--------|------------------|-------------------|
| **Problem** | No response to tool_use | Multiple responses to tool_use |
| **Location** | Between messages | Within message content |
| **Scope** | Cross-message state | Local content |
| **Detection** | Set difference | Frequency count |
| **Repair** | Add synthetic data | Remove redundant data |
| **Safety** | High (synthetic, error-flagged) | Very high (remove only dupes) |
| **Complexity** | Medium (state tracking) | Low (single pass) |
| **Code Size** | ~50 lines | ~20 lines |
| **Status** | ✅ Implemented | ❌ Not implemented |
| **Priority** | High (blocks Claude) | Medium (confusing, but works) |
| **Test Coverage** | Yes (`test_repair.py`) | No |
| **Error Cases** | Multiple | Few |
| **Users Affected** | Conversations ending mid-tool | Export/import roundtrips |

---

## Why Missing Is Implemented But Duplicate Isn't

### Blocking Power (Why Missing Matters)

```
Missing tool_result:
┌─────────────────────────┐
│  User tries to resume   │  ← Can't continue conversation
│  Claude API says:       │    "tool_use abc123 has no result"
│  "ERROR: incomplete"    │
└─────────────────────────┘

Duplicate tool_result:
┌─────────────────────────┐
│  User tries to resume   │  ← CAN continue
│  Claude API says:       │    (processes first result)
│  "OK, using first one"  │
└─────────────────────────┘
```

**Result**: Missing is a BLOCKER, duplicate is an ANNOYANCE

### Implementation Difficulty

**Missing**:
- Requires maintaining cross-message state
- Must handle message boundaries
- Need to identify sync points (when to check)
- More complex logic: `pending - seen`

**Duplicate**:
- Single message context
- Simple frequency counting
- No state needed
- Straightforward logic: `if count > 1: remove`

### Priority Reasoning

1. **Fix blockers first** (missing) → Done ✅
2. **Then fix annoyances** (duplicate) → To do ❌
3. **Then fix edge cases** (orphaned) → Future

---

## Code Complexity Proof

### Missing Pattern (Established, 102 + 95 = 197 lines total)

```python
# scan.py: Detect missing
def detect_missing_tool_results(lines):
    issues = []
    pending = []                           # <-- State
    last_assistant_index = None            # <-- Context

    for idx, msg in enumerate(lines):
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "assistant":
            # Track pending
            last_assistant_index = idx
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "tool_use":
                        pending.append(c["id"])
            continue

        if role == "user":
            # Cross-message sync point
            if pending:
                seen = set()
                if isinstance(content, list):
                    for c in content:
                        if c.get("type") == "tool_result":
                            seen.add(c["tool_use_id"])

                # Set difference!
                missing = [tid for tid in pending if tid not in seen]

                if missing:
                    issues.append(ScanIssue(...))
                pending = []

    return issues
```

**Complexity Markers**: 🔴 Multiple state variables, 🔴 Multi-message coordination, 🔴 Complex control flow

### Duplicate Pattern (Proposed, ~30 lines total)

```python
# scan.py: Detect duplicates
def detect_duplicate_tool_results(lines):
    issues = []

    for idx, msg in enumerate(lines):
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "user" and isinstance(content, list):
            # Count occurrences
            id_count = {}
            for c in content:
                if c.get("type") == "tool_result":
                    tid = c.get("tool_use_id")
                    if tid:
                        id_count[tid] = id_count.get(tid, 0) + 1

            # Find counts > 1
            duplicates = [tid for tid, count in id_count.items() if count > 1]

            if duplicates:
                issues.append(ScanIssue(...))

    return issues
```

**Complexity Markers**: 🟢 No state tracking, 🟢 Single-message scope, 🟢 Linear control flow

---

## Test Coverage Gap

### Existing Tests (for Missing Detection)

File: `tests/graph/test_repair.py`

```python
def test_missing_tool_result():
    """Should detect missing tool_result after tool_use"""

def test_suggest_parent_candidates():
    """Should suggest parents using semantic similarity"""

def test_validate_repair():
    """Should validate repair operations"""
```

### Missing Tests (for Duplicate Detection)

```python
# These DON'T EXIST yet:

def test_duplicate_tool_results():
    """Should detect duplicate tool_result blocks"""

def test_deduplicate_preserves_order():
    """Should remove duplicates while maintaining order"""

def test_no_false_positives_on_different_ids():
    """Should not report different IDs as duplicates"""
```

---

## Integration Points

### Current Integration (scan → fix → persist)

```
CLI Entry
  ↓
riff scan → detect_missing_tool_results()
  ↓ (if issues found)
riff fix → repair_stream() → add synthetic results
  ↓
Write to disk / SurrealDB
```

### Proposed Integration (enhanced)

```
CLI Entry
  ↓
riff scan → detect_missing_tool_results() + detect_duplicate_tool_results()
  ↓ (if either issue found)
riff fix → repair_stream() → (add synthetic + deduplicate)
  ↓
Write to disk / SurrealDB
```

**Key Insight**: Deduplication fits NATURALLY into the existing repair_stream flow, right after adding missing results.

---

## Why Not Use graph/repair.py?

The orphan message repair engine (`src/riff/graph/repair.py`, 624 lines) might seem applicable, but it's **not**:

| Aspect | graph/repair.py | Needed for tool_results |
|--------|-----------------|------------------------|
| **Input** | Message with null parentUuid | Duplicate tool_result blocks |
| **Algorithm** | Semantic similarity + DAG analysis | Frequency counting |
| **Output** | New parentUuid assignment | Filtered content list |
| **Scope** | Message graph structure | Message content |
| **Complexity** | Very high (ML-like) | Very low (deterministic) |

**Result**: graph/repair.py is **massive overkill** for duplicate detection. The tool_result problem is fundamentally simpler.

---

## Architectural Lessons

### Lesson 1: Tier-Based Problem Solving
Address problems by severity:
1. **Blockers** (missing) → Must fix → Complex if needed
2. **Annoyances** (duplicates) → Should fix → Simple solutions preferred
3. **Edge cases** (orphaned) → Nice to have → Only if resources allow

### Lesson 2: Scope Determines Complexity
- **Cross-message problems** → Need state machines, context, sync points
- **Within-message problems** → Single-pass filters, no state
- Choose the simplest approach that matches the scope

### Lesson 3: Reuse Existing Patterns
Don't reinvent the wheel:
- Use existing `ScanIssue` dataclass (extend, don't replace)
- Use existing `repair_stream()` pattern (add new function, integrate)
- Follow existing utility patterns (get_message_role, etc.)

### Lesson 4: Test-Driven Discovery
The fact that **no duplicate detection tests exist** is a clue that it's a gap. Tests drive implementation, not the other way around.

---

## Decision Framework

**Should we implement duplicate detection?**

| Factor | Score | Evidence |
|--------|-------|----------|
| **Blocking severity** | Low | Works despite duplicates |
| **User impact** | Medium | Confusing but functional |
| **Implementation difficulty** | Very Low | ~30 lines, ~1 day |
| **Code maintainability** | High | Follows existing patterns |
| **Test coverage** | High | Easy to test |
| **Business value** | Medium | Cleanup, validation |

**Recommendation**: YES - High ROI (simple + valuable + low risk)

---

## Next Steps

1. Read `DUPLICATE_TOOL_RESULT_IMPLEMENTATION_GUIDE.md` for detailed implementation
2. Run proposed tests (they will fail)
3. Implement Phase 1 (duplicate detection)
4. Implement Phase 2 (repair integration)
5. Run full test suite
6. Manual testing with real JSONL files

---

## References

- **Current Missing Detection**: `src/riff/classic/commands/scan.py:24-55`
- **Current Repair Logic**: `src/riff/classic/commands/fix.py:17-71`
- **Graph Repair (Different Problem)**: `src/riff/graph/repair.py`
- **Shared Utilities**: `src/riff/classic/utils.py`
- **Test Patterns**: `tests/graph/test_repair.py`

