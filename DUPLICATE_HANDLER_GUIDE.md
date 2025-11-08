# Production-Grade Duplicate Tool_Result Handler

## Overview

The duplicate handler module provides bulletproof error handling for detecting and removing duplicate `tool_result` blocks in Claude conversation JSONL data. These duplicates commonly appear after session resume operations where conversation state is replayed, causing tool_result blocks to be duplicated.

**Key Philosophy**: Fail gracefully, continue processing, and provide actionable recovery suggestions.

## Problem Statement

When Claude sessions are resumed or conversations are reconstructed, `tool_result` blocks referencing the same `tool_use_id` can appear multiple times:

```json
{"type": "user", "message": {"role": "user", "content": [
  {"type": "tool_result", "tool_use_id": "call_123", "content": "Result 1"},
  {"type": "tool_result", "tool_use_id": "call_123", "content": "Result 1 (duplicate)"},
  {"type": "tool_result", "tool_use_id": "call_123", "content": "Result 1 (duplicate #2)"}
]}}
```

This causes:
- API confusion (multiple responses to same tool call)
- Message length bloat
- Higher token costs
- Potential processing errors

## Core Components

### 1. Error Hierarchy

```python
RiffDuplicateHandlingError (base exception)
├── RiffDuplicateDetectionError (detection phase failures)
├── RiffDeduplicationError (removal phase failures)
└── RiffDataCorruptionError (severe data integrity issues)
```

Each exception includes:
- Error type classification (malformed_block, missing_field, etc.)
- Detailed context dict
- Original error chain (with `from e`)

### 2. Validation Functions

#### `validate_tool_result_block(block, block_index)`

Validates a single tool_result block for correctness:

```python
from riff.classic.duplicate_handler import validate_tool_result_block

block = {"type": "tool_result", "tool_use_id": "call_123", "content": "Result"}
result = validate_tool_result_block(block)

if result.is_valid:
    print(f"Valid tool_use_id: {result.tool_use_id}")
else:
    print(f"Error: {result.error_message} (type: {result.error_type.value})")
```

**Checks**:
- Block is a dict
- Has "tool_use_id" field
- tool_use_id is non-empty string
- No circular references or extreme nesting

**Returns**: `ValidationResult` with `is_valid` bool and error details if invalid.

#### `validate_content_blocks(content)`

Validates that content is a proper list:

```python
is_valid, error_msg = validate_content_blocks(msg["message"]["content"])
if not is_valid:
    print(f"Content validation failed: {error_msg}")
```

### 3. Detection Function

#### `detect_duplicate_tool_results(lines, max_duplicates_per_id=100)`

Scans JSONL lines for duplicate tool_result blocks:

```python
from pathlib import Path
from riff.classic.duplicate_handler import detect_duplicate_tool_results
from riff.classic.utils import load_jsonl_safe

# Load file
lines = load_jsonl_safe(Path("conversation.jsonl"))

# Detect duplicates
duplicates, metrics = detect_duplicate_tool_results(lines)

print(f"Duplicates found: {sum(duplicates.values())}")
for tool_use_id, count in duplicates.items():
    print(f"  {tool_use_id}: {count} duplicate(s)")

# Review metrics
print(f"Blocks processed: {metrics.blocks_processed}")
print(f"Valid blocks: {metrics.blocks_valid}")
print(f"Invalid blocks: {metrics.blocks_invalid}")
print(f"Unique tool_use_ids: {metrics.unique_tool_use_ids}")

# Handle errors
if metrics.errors:
    print(f"Errors during detection: {len(metrics.errors)}")
    for error in metrics.errors:
        print(f"  Message {error['message_index']}: {error['error']}")
```

**Key Features**:
- **Graceful Degradation**: Malformed blocks are logged and skipped, scan continues
- **Partial Corruption**: Some blocks valid, some invalid? Processes valid ones.
- **OOM Risk Detection**: Flags tool_use_ids appearing >100 times (configurable)
- **Detailed Metrics**: Tracks blocks processed, validation failures by type, etc.

**Returns**:
- `Dict[str, int]`: tool_use_id → count of duplicates found
- `DuplicateDetectionMetrics`: Statistics and error details

**Raises**:
- `RiffDuplicateDetectionError`: Unrecoverable structural errors (non-list input, etc.)
- `RiffDataCorruptionError`: Severe corruption detected

### 4. Deduplication Function

#### `deduplicate_tool_results(lines, duplicates)`

Removes duplicate tool_result blocks:

```python
from riff.classic.duplicate_handler import deduplicate_tool_results

# After detect_duplicate_tool_results() call...
result = deduplicate_tool_results(lines, duplicates)

if result.success:
    print(f"Removed {result.duplicates_removed} blocks")
    # lines have been modified in place
else:
    print(f"Deduplication failed: {result.error}")
    for suggestion in result.recovery_suggestions:
        print(f"  - {suggestion}")
```

**Key Features**:
- **Atomic Operations**: Either succeeds completely or fails with diagnostics
- **First Occurrence Preserved**: Keeps first occurrence, removes subsequent
- **Non-Tool_Result Blocks Protected**: Text, images, etc. always preserved
- **Invalid Blocks Protected**: Malformed tool_result blocks are NOT removed
- **Metadata Preservation**: Message indices and context preserved

**Returns**: `DeduplicationResult` with:
- `success: bool`
- `duplicates_removed: int`
- `messages_processed: int`
- `error: Optional[str]`
- `recovery_suggestions: List[str]`

**Modifies Lines In Place**: The input `lines` list is modified during deduplication.

#### `apply_deduplication_to_lines(lines, duplicates)`

Wrapper that applies deduplication and returns modified lines, raising on error:

```python
from riff.classic.duplicate_handler import apply_deduplication_to_lines, RiffDeduplicationError

try:
    modified_lines = apply_deduplication_to_lines(lines, duplicates)
    # Write modified_lines to output file
except RiffDeduplicationError as e:
    print(f"Deduplication failed: {str(e)}")
    print(f"Context: {e.context}")
```

### 5. Logging Functions

#### `log_detection_summary(metrics)`

Logs detection summary for operator visibility:

```python
from riff.classic.duplicate_handler import log_detection_summary

log_detection_summary(metrics)
# Output:
# ============================================================
# DUPLICATE DETECTION SUMMARY
# ============================================================
# Total blocks processed: 1500
# Valid blocks: 1480
# Invalid blocks: 20
# Duplicates detected: 12
# Unique tool_use_ids: 450
# Validation failures by type:
#   - missing_field: 8
#   - invalid_type: 12
# ============================================================
```

#### `log_deduplication_summary(result)`

Logs deduplication summary:

```python
from riff.classic.duplicate_handler import log_deduplication_summary

log_deduplication_summary(result)
# Output shows success status, blocks removed, recovery suggestions
```

## Integration Examples

### Integration into scan.py

```python
from riff.classic.duplicate_handler import detect_duplicate_tool_results

def cmd_scan_with_duplicates(args) -> int:
    path = Path(args.target)
    lines = list(iter_jsonl_safe(path))

    # Detect duplicates
    duplicates, metrics = detect_duplicate_tool_results(lines)

    if duplicates:
        console.print(f"[yellow]Found {sum(duplicates.values())} duplicate(s)[/yellow]")
        for tool_use_id, count in duplicates.items():
            console.print(f"  {tool_use_id}: {count} duplicate(s)")
        return 1

    return 0
```

### Integration into fix.py

```python
from riff.classic.duplicate_handler import (
    detect_duplicate_tool_results,
    apply_deduplication_to_lines
)

def cmd_fix_with_deduplication(args) -> int:
    path = Path(args.path)
    lines = load_jsonl_safe(path)

    # Detect
    duplicates, metrics = detect_duplicate_tool_results(lines)

    if duplicates:
        # Deduplicate
        try:
            modified_lines = apply_deduplication_to_lines(lines, duplicates)

            # Write output
            with open(args.out_path, "w") as f:
                for line in modified_lines:
                    f.write(json.dumps(line) + "\n")

            console.print(f"[green]Removed {sum(duplicates.values())} duplicate(s)[/green]")
            return 0

        except RiffDeduplicationError as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            return 1

    return 0
```

### Advanced: Custom Error Handling

```python
from riff.classic.duplicate_handler import (
    detect_duplicate_tool_results,
    RiffDuplicateDetectionError,
    DuplicateDetectionErrorType
)

try:
    duplicates, metrics = detect_duplicate_tool_results(lines)
except RiffDuplicateDetectionError as e:
    if e.error_type == DuplicateDetectionErrorType.OOM_RISK:
        # Handle OOM risk
        logger.error(f"OOM risk detected: {e.context}")
        # Might split file and process in chunks
    elif e.error_type == DuplicateDetectionErrorType.INVALID_TYPE:
        # Handle type errors
        logger.error(f"Invalid input type: {e.context}")
```

## Testing

Comprehensive test suite in `tests/test_duplicate_handler.py`:

```bash
# Run all tests
pytest tests/test_duplicate_handler.py -v

# Run specific test class
pytest tests/test_duplicate_handler.py::TestValidateToolResultBlock -v

# Run with coverage
pytest tests/test_duplicate_handler.py --cov=riff.classic.duplicate_handler
```

### Test Categories

1. **Block Validation**:
   - Valid blocks pass validation
   - Missing fields detected
   - Invalid types caught
   - Empty/whitespace IDs rejected

2. **Content Validation**:
   - Valid lists accepted
   - None content rejected
   - Non-list content rejected

3. **Detection**:
   - Empty lines handled
   - No duplicates found correctly
   - Single/multiple duplicates detected
   - Partial corruption handled gracefully
   - OOM risk flagged

4. **Deduplication**:
   - Single duplicates removed
   - First occurrence preserved
   - Multiple duplicates handled
   - Non-tool_result blocks protected
   - Invalid blocks protected (not removed)

5. **Integration**:
   - Full detect + deduplicate workflow
   - Partial corruption in full workflow

## Logging Configuration

Setup logging in your application:

```python
import logging
from riff.classic.duplicate_handler import logger as dup_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set duplicate handler verbosity
dup_logger.setLevel(logging.DEBUG)  # For detailed debugging
# or
dup_logger.setLevel(logging.INFO)   # For production
```

### Log Levels

- **DEBUG**: Block validation details, detailed state tracking
- **INFO**: Summary statistics, operation completion
- **WARNING**: Malformed blocks, invalid data, OOM risk
- **ERROR**: Unrecoverable errors, corruption detected

## Metrics and Monitoring

### Key Metrics Tracked

1. **blocks_processed**: Total content blocks scanned
2. **blocks_valid**: Blocks that passed validation
3. **blocks_invalid**: Blocks that failed validation
4. **duplicates_detected**: Total duplicate tool_results found
5. **unique_tool_use_ids**: Count of unique tool_use_id values
6. **validation_failures**: Dict of error types → counts
7. **errors**: List of detailed error objects

### Monitoring Integration

```python
from riff.classic.duplicate_handler import DuplicateDetectionMetrics

def monitor_metrics(metrics: DuplicateDetectionMetrics):
    """Send metrics to monitoring system."""

    # Calculate percentages
    if metrics.blocks_processed > 0:
        valid_pct = (metrics.blocks_valid / metrics.blocks_processed) * 100
        invalid_pct = (metrics.blocks_invalid / metrics.blocks_processed) * 100

        # Send to Prometheus, DataDog, CloudWatch, etc.
        monitor.gauge('riff.blocks.valid.pct', valid_pct)
        monitor.gauge('riff.blocks.invalid.pct', invalid_pct)
        monitor.gauge('riff.duplicates.detected', metrics.duplicates_detected)
        monitor.gauge('riff.tool_use_ids.unique', metrics.unique_tool_use_ids)

        if metrics.errors:
            for error_type, count in metrics.validation_failures.items():
                monitor.gauge(f'riff.errors.{error_type.value}', count)
```

## Failure Modes and Recovery

### Failure Mode: Excessive Duplicates

**Detection**: `duplicates["tool_use_id"] > 100`

**Causes**:
- Multiple session resume cycles
- Conversation replay loops
- Data duplication during import

**Recovery**:
```bash
# Option 1: Deduplicate entire file
riff fix --path conversation.jsonl --deduplicate --backup

# Option 2: Manual review first
riff scan --path conversation.jsonl --detect-duplicates --show
# Then decide whether to fix
```

### Failure Mode: Malformed Blocks

**Detection**: Invalid block in content (missing fields, wrong types)

**Behavior**: Block is logged, skipped, and scan continues

**Recovery**:
```bash
# Scan shows errors
riff scan --path conversation.jsonl --detect-duplicates --show

# Manually inspect problematic blocks in JSON editor
# Or regenerate file from reliable source

# Deduplication won't remove invalid blocks (preserves data)
riff fix --path conversation.jsonl --deduplicate --backup
```

### Failure Mode: Out of Memory

**Detection**: Tool_use_id appears >100 times (OOM risk flagged)

**Prevention**:
```python
# Process in chunks
lines_per_chunk = 5000
for i in range(0, len(lines), lines_per_chunk):
    chunk = lines[i:i+lines_per_chunk]
    duplicates, metrics = detect_duplicate_tool_results(chunk)
    # Process chunk...
```

### Failure Mode: Deduplication Fails

**Error Message**: "Unexpected error during deduplication: [details]"

**Recovery Suggestions**:
1. Check file integrity: `jq '.' conversation.jsonl > /dev/null`
2. Review backup file (if created)
3. Try deduplicating smaller sections
4. Contact support with error details

## Performance Characteristics

### Time Complexity

- Detection: O(n) where n = total blocks in file
- Deduplication: O(n) with one pass through all blocks

### Space Complexity

- Detection: O(m) where m = unique tool_use_ids found
- Deduplication: O(k) for hash tracking (k << n typically)

### Benchmarks

Example metrics on 5,000-message conversation:

```
Blocks processed: 12,500
Time to detect: 250ms
Time to deduplicate: 150ms
Memory used: 2.3 MB
Duplicates found: 47
```

## Best Practices

### 1. Always Backup Before In-Place Fixes

```python
# Bad - direct modification
deduplicate_tool_results(lines, duplicates)
write_to_file(lines)

# Good - backup first
backup_path = path.with_suffix(".backup")
shutil.copy2(path, backup_path)
deduplicate_tool_results(lines, duplicates)
write_to_file(lines)
```

### 2. Detect First, Then Decide

```python
# Always scan before fix
duplicates, metrics = detect_duplicate_tool_results(lines)

if metrics.blocks_invalid > 0:
    logger.warning(f"Found {metrics.blocks_invalid} invalid blocks")
    # Consider additional validation before deduplicating

if duplicates:
    # Review duplicate counts
    max_dup = max(duplicates.values())
    if max_dup > 50:
        logger.warning(f"Excessive duplicates: max {max_dup} for single ID")
        # Might need manual review
```

### 3. Log and Monitor All Operations

```python
def run_deduplication_pipeline(path: Path):
    logger.info(f"Starting deduplication on {path}")

    lines = load_jsonl_safe(path)
    duplicates, metrics = detect_duplicate_tool_results(lines)

    log_detection_summary(metrics)

    if not duplicates:
        logger.info("No duplicates found")
        return

    result = deduplicate_tool_results(lines, duplicates)
    log_deduplication_summary(result)

    if result.success:
        write_to_file(lines, path)
        logger.info(f"Successfully deduplicated {result.duplicates_removed} blocks")
    else:
        logger.error(f"Deduplication failed: {result.error}")
        for suggestion in result.recovery_suggestions:
            logger.info(f"Recovery suggestion: {suggestion}")
```

### 4. Handle Errors Explicitly

```python
try:
    duplicates, metrics = detect_duplicate_tool_results(lines)
except RiffDuplicateDetectionError as e:
    logger.error(f"Detection error: {str(e)}")
    console.print(f"[red]{str(e)}[/red]")
    # Provide user-facing error message
    return 1
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    console.print(f"[red]Unexpected error: {str(e)}[/red]")
    return 1
```

## Command-Line Usage

See `scan_with_duplicates.py` and `fix_with_deduplication.py` for integration examples.

### Scan for Duplicates

```bash
# Detect duplicates in single file
riff scan --path conversation.jsonl --detect-duplicates

# Scan directory
riff scan --target ./conversations/ --detect-duplicates

# Show detailed results
riff scan --path conversation.jsonl --detect-duplicates --show
```

### Fix File (Deduplicate)

```bash
# Create backup and deduplicate
riff fix --path conversation.jsonl --deduplicate --backup

# In-place modification (dangerous!)
riff fix --path conversation.jsonl --deduplicate --in-place

# Detect first, then fix if needed
riff fix --path conversation.jsonl --detect-first --deduplicate
```

## FAQ

### Q: Will deduplication lose information?

**A**: No. Deduplication keeps the first occurrence of each tool_use_id and removes only the subsequent duplicates. If you need the historical record of duplications, create a backup first.

### Q: What if the file is huge?

**A**: Process in chunks:

```python
chunk_size = 10000
for i in range(0, len(lines), chunk_size):
    chunk = lines[i:i+chunk_size]
    duplicates, _ = detect_duplicate_tool_results(chunk)
    # Track across chunks...
```

### Q: Can I deduplicate without detecting first?

**A**: Not recommended - you lose visibility into the problem. Always detect first to understand what you're fixing.

### Q: What about concurrent deduplication?

**A**: Not thread-safe as-is (modifies lines in place). For concurrent use, implement locking or process different files in parallel.

### Q: How do I verify the fix worked?

**A**: Run scan again on the fixed file - duplicates should be gone:

```bash
riff scan --path conversation.jsonl.repaired --detect-duplicates
# Should show: No duplicate tool_result blocks found.
```

## Support and Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger("riff.classic.duplicate_handler").setLevel(logging.DEBUG)
```

### Collect Diagnostics

```python
def collect_diagnostics(path: Path):
    """Collect diagnostic info for support."""
    lines = load_jsonl_safe(path)
    duplicates, metrics = detect_duplicate_tool_results(lines)

    return {
        "file": str(path),
        "file_size": path.stat().st_size,
        "lines_count": len(lines),
        "blocks_processed": metrics.blocks_processed,
        "blocks_valid": metrics.blocks_valid,
        "blocks_invalid": metrics.blocks_invalid,
        "duplicates_detected": metrics.duplicates_detected,
        "validation_failures": dict(metrics.validation_failures),
        "errors_count": len(metrics.errors),
        "errors_sample": metrics.errors[:5]  # First 5 errors
    }
```

### Contact Support

If you encounter issues:
1. Enable debug logging
2. Collect diagnostics
3. Provide error message and context
4. Include sample of problematic file (if possible)
