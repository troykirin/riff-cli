# Riff Repair Implementation Analysis
## Why Multiple tool_result Blocks Aren't Being Fixed

**Analysis Date**: 2025-11-07
**Status**: Complete diagnosis with architectural root cause
**Scope**: Riff repair engine for Claude conversation JSONL files

---

## Executive Summary

The Riff repair implementation **successfully handles MISSING tool_result blocks** (the problem it was designed to solve), but **does NOT detect or fix DUPLICATE/MULTIPLE tool_result blocks for the SAME tool_use ID**. This is a gap in coverage, not a bug in the existing logic.

---

## Part A: What the Repair Code Actually Does

### Current Repair Logic (Location: `/Users/tryk/nabia/tools/riff-cli/src/riff/classic/commands/fix.py`)

**Algorithm**: Track-and-Fill Pattern

```python
def repair_stream(lines: list[dict]) -> list[dict]:
    fixed: list[dict] = []
    pending: list[str] = []  # <-- Track pending tool_use IDs

    for msg in lines:
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "assistant":
            # COLLECT all tool_use IDs from assistant messages
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "tool_use" and c.get("id"):
                        pending.append(c["id"])
            fixed.append(msg)

        elif role == "user":
            if pending:
                seen = set()
                # SCAN for existing tool_results
                if isinstance(content, list):
                    for c in content:
                        if c.get("type") == "tool_result" and c.get("tool_use_id"):
                            seen.add(c["tool_use_id"])

                # FIND MISSING: IDs in pending but NOT in seen
                missing = [tid for tid in pending if tid not in seen]

                if missing:
                    # CREATE tool_results for missing IDs
                    tr = [{
                        "type": "tool_result",
                        "tool_use_id": tid,
                        "content": "Tool run cancelled by user before completion.",
                        "is_error": True,
                    } for tid in missing]

                    # PREPEND to user message content
                    msg = normalize_message_structure(msg)
                    msg["message"]["content"] = tr + (msg["message"].get("content") or [])

                pending = []
            fixed.append(msg)
```

**Key Operations**:
1. ✅ Collects tool_use IDs from assistant messages
2. ✅ Detects which tool_use IDs are MISSING from the next user message
3. ✅ Generates synthetic tool_result blocks for missing IDs
4. ✅ Prepends them to user message content
5. ✅ Resets tracking at next user message

---

## Part B: Why It Doesn't Handle Duplicate tool_results

### The Root Cause: Tracking Model Gap

The repair engine uses a **set-based uniqueness check**:

```python
seen = set()  # <-- One-dimensional: only tracks "was it mentioned?"
for c in content:
    if c.get("type") == "tool_result" and c.get("tool_use_id"):
        seen.add(c["tool_use_id"])  # <-- Adds ID to set

# Problem: set only cares about presence, not frequency
# seen.add("abc123")  # First occurrence
# seen.add("abc123")  # Second occurrence - SET IGNORES THIS!
```

**Why This Design**:
- The code was optimized for the "missing tool_result" problem
- A set automatically de-duplicates during iteration
- The logic says: "If ID is in the set, skip it" (don't add another)
- But it never checks: "Are there multiple entries in the original content for the same ID?"

### What Happens with Duplicates

**Input JSONL** (user message with duplicate tool_results):
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {"type": "tool_result", "tool_use_id": "abc123", "content": "Result 1"},
      {"type": "tool_result", "tool_use_id": "abc123", "content": "Result 2"}
    ]
  }
}
```

**What the scanner sees**:
```python
for c in content:
    if c.get("tool_use_id"):
        seen.add(c["tool_use_id"])

# Iteration 1: seen.add("abc123")  -> seen = {"abc123"}
# Iteration 2: seen.add("abc123")  -> seen = {"abc123"}  (no change!)

# Result: seen = {"abc123"} with ONE entry
# Code thinks: "abc123 is covered"
# Reality: abc123 appears TWICE in the content list
```

**Output**: The scanner reports NO ISSUE because:
- pending = ["abc123"]
- seen = {"abc123"}
- missing = [] (empty!)
- No repair is attempted

---

## Part C: Why Truncation is Needed, Not Patching

### The Type of Problem

This is a **data quality issue**, not a missing-link issue:

| Problem Type | Current Fix | Needed Fix |
|---|---|---|
| Missing tool_result (tool_use has no response) | ✅ Adds synthetic result | N/A |
| Duplicate tool_result (tool_use has 2+ responses) | ❌ Doesn't detect | ⚠️ Truncate or merge |
| Wrong tool_use_id in tool_result | ❌ Doesn't detect | ❌ No fix (data corruption) |

### Why Simple Patching Won't Work

**Option 1: Patch (modify parent_uuid)**
- Doesn't apply here - tool_results don't have parent relationships
- Tool results are CONTENT ITEMS within a user message, not separate messages

**Option 2: Deduplicate/Truncate**
- Keep FIRST tool_result for each ID, remove duplicates
- This is safe because Claude processes results sequentially
- Duplicates are typically caused by:
  - Export/import tool fumbling
  - JSONL editing mistakes
  - Malformed conversation reconstructions

### Recommended Truncation Strategy

```python
def deduplicate_tool_results(content: list) -> list:
    """Remove duplicate tool_results, keeping first occurrence."""
    seen_ids = set()
    deduplicated = []

    for item in content:
        if item.get("type") == "tool_result":
            tool_use_id = item.get("tool_use_id")
            if tool_use_id in seen_ids:
                # Skip duplicate
                continue
            seen_ids.add(tool_use_id)

        deduplicated.append(item)

    return deduplicated
```

**Why This Works**:
- Claude processes tool_results sequentially
- Only the FIRST result for each tool_use ID matters
- Duplicates are noise/corruption
- Keeps original order and content structure

---

## Part D: Implementation Comparison

### Missing tool_result Fix (What Currently Works)

**Location**: `src/riff/classic/commands/fix.py:17-71`
**Complexity**: Medium (track pending, match at user boundary)
**Scope**: Cross-message coordination

```
Assistant message:
  └─ tool_use(id="abc123")

User message:
  └─ [missing tool_result for "abc123"]

Fix: Prepend synthetic tool_result(id="abc123")
```

### Duplicate tool_result Fix (What's Missing)

**Needed Location**: New function in `fix.py` or `scan.py`
**Complexity**: Low (single-pass dedupe within one message)
**Scope**: Within-message deduplication

```
User message content:
  ├─ tool_result(id="abc123")  ← Keep
  ├─ tool_result(id="abc123")  ← Remove (duplicate)
  └─ [other content]

Fix: Filter to single occurrence per ID
```

---

## Part E: Scanner vs Fixer Gap

### What the Scanner Detects (`scan.py:24-55`)

```python
def detect_missing_tool_results(lines: list[dict]) -> list[ScanIssue]:
    pending: list[str] = []

    for idx, msg in enumerate(lines):
        if role == "assistant":
            # Collect tool_use IDs
            for c in content:
                if c.get("type") == "tool_use" and c.get("id"):
                    pending.append(c["id"])

        elif role == "user":
            if pending:
                seen = set()
                for c in content:
                    if c.get("type") == "tool_result":
                        seen.add(c["tool_use_id"])

                missing = [tid for tid in pending if tid not in seen]

                if missing:  # <-- Only reports MISSING
                    issues.append(ScanIssue(...))
                pending = []
```

**Issues Detected**:
- ✅ Missing tool_result (ID in pending, not in seen)
- ❌ Duplicate tool_result (Multiple items with same ID in content)
- ❌ Orphaned tool_result (result ID doesn't match any tool_use)

### What Needs to Be Added

**Enhanced Scanner Function**:
```python
def detect_duplicate_tool_results(lines: list[dict]) -> list[ScanIssue]:
    """Detect duplicate tool_results within messages."""
    issues: list[ScanIssue] = []

    for idx, msg in enumerate(lines):
        role = get_message_role(msg)
        content = get_message_content(msg)

        if role == "user" and isinstance(content, list):
            id_count = {}
            for c in content:
                if c.get("type") == "tool_result":
                    tid = c.get("tool_use_id")
                    id_count[tid] = id_count.get(tid, 0) + 1

            # Report duplicates
            duplicates = [tid for tid, count in id_count.items() if count > 1]
            if duplicates:
                issues.append(ScanIssue(
                    file=...,
                    duplicate_ids=duplicates,  # <-- NEW
                    message_index=idx
                ))

    return issues
```

---

## Part F: Architectural Design Pattern

### Current System (Orphan Messages)

The `/graph/repair.py` (21.8 KB) handles a DIFFERENT problem:
- **What**: Orphaned conversation messages (messages with missing parent_uuid)
- **How**: Semantic similarity + timestamp analysis + validation
- **Output**: Suggested parent assignments for tree reconstruction

```
Message Graph Repair
├─ Find orphaned messages (no parent)
├─ Suggest candidates by similarity
├─ Validate (no circular deps, timestamp logic)
└─ Apply repair (update parent_uuid)
```

### Needed System (Content Deduplication)

The classic `fix.py` (95 lines) handles a DIFFERENT problem:
- **What**: Missing tool_result blocks in the message stream
- **How**: Track pending tool_uses across message boundaries
- **Output**: Synthetic tool_results prepended to user messages

```
Content Stream Repair
├─ Track tool_use IDs from assistant
├─ Find missing responses at user message
├─ Generate synthetic tool_results
└─ Prepend to user message content
```

### Missing System (Duplicate Deduplication)

**Needed**: Content-level deduplication within messages:
- **What**: Duplicate tool_result blocks within same message
- **How**: Count occurrences per ID, keep first, remove rest
- **Output**: Cleaned content with one result per tool_use ID

```
Content Deduplication
├─ Scan user message content
├─ Count tool_result IDs
├─ Identify duplicates (count > 1)
└─ Filter to first occurrence per ID
```

**Key Insight**: This is **not** a message graph problem (no parent_uuid changes needed), it's a **content cleaning** problem.

---

## Summary Table

| Aspect | Missing tool_result | Duplicate tool_result |
|--------|-------------------|----------------------|
| **Current Status** | ✅ Implemented | ❌ Not implemented |
| **Detection** | Via scan.py (missing IDs) | Needs new scan logic |
| **Fix Type** | Add synthetic blocks | Truncate/deduplicate |
| **Scope** | Cross-message (boundary) | Within-message (content) |
| **Complexity** | Medium | Low |
| **Lines of Code** | ~50 | ~20 |
| **Safety Level** | High (synthetic + error flag) | Very High (keeps original data) |
| **Root Cause** | Design gap | Not prioritized |

---

## Recommendations

### Short Term
1. **Add duplicate detection** to `scan.py:detect_missing_tool_results()`
   - Add `duplicate_ids` field to `ScanIssue`
   - Report duplicates separately from missing

2. **Add deduplication filter** to `fix.py:repair_stream()`
   - New function: `deduplicate_tool_results(content)`
   - Call after normalizing structure, before returning

### Medium Term
3. **Unify scanning** into one comprehensive function
   - `detect_content_issues()` that reports:
     - Missing tool_results
     - Duplicate tool_results
     - Orphaned tool_results (result ID with no tool_use)

4. **Enhance ScanIssue dataclass**
   ```python
   @dataclass
   class ScanIssue:
       file: Path
       message_index: int | None
       missing_ids: list[str] = field(default_factory=list)
       duplicate_ids: list[str] = field(default_factory=list)
       orphaned_ids: list[str] = field(default_factory=list)
   ```

### Long Term
5. **Consider a ValidationEngine** separate from RepairEngine
   - Repair engine handles message graph (orphan fixing)
   - Validation engine handles content integrity
   - Both pluggable into persistence layers (JSONL, SurrealDB)

---

## Files Involved

### Core Repair Logic
- **`src/riff/classic/commands/fix.py`** (95 lines)
  - `repair_stream()` - Main repair loop
  - `cmd_fix()` - CLI entry point
  - Status: ✅ Works for missing tool_results

- **`src/riff/classic/commands/scan.py`** (102 lines)
  - `detect_missing_tool_results()` - Missing detection
  - `cmd_scan()` - CLI reporting
  - Status: ✅ Detects missing, ❌ Doesn't detect duplicates

### Graph-Based Repair (Different Purpose)
- **`src/riff/graph/repair.py`** (624 lines)
  - `ConversationRepairEngine` - Orphan message fixing
  - Uses semantic analysis + DAG validation
  - Status: ✅ Works for orphaned messages (not tool_results)

### Integration Points
- **`src/riff/cli.py`** - CLI main entry
- **`src/riff/classic/utils.py`** - Helper functions
- **`tests/graph/test_repair.py`** - Tests for repair.py

---

## Conclusion

**The Riff repair system is well-designed for its primary purpose** (fixing missing tool_result blocks), but has a clear architectural gap: **it doesn't detect or remove duplicate/multiple tool_result blocks for the same tool_use ID**.

This is **not a bug in the existing code** — the existing code works perfectly for what it was designed to do. Instead, it's a **missing feature** that should be added alongside the existing missing-detection logic.

The fix is straightforward (deduplication is a simple single-pass filter), and the codebase is well-structured to accept it (just add new logic in `scan.py` and `fix.py`).

