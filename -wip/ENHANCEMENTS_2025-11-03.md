# Riff-CLI Search & Preview Enhancements (2025-11-03)

## Overview
Enhanced riff-cli with improved search capabilities and interactive modal previews for detailed message viewing. Users can now search for specific phrases/words with fuzzy matching fallback and view full message content in formatted modals.

---

## 1. ✅ Fixed Embedding Model Configuration

**Issue**: Code was hardcoding `all-MiniLM-L6-v2` (256-dim) instead of using configured `BAAI/bge-small-en-v1.5` (384-dim) from ~/.config/nabi/tools/riff.toml

**Files Modified**:
- `src/riff/search/qdrant.py` (lines 38-49)

**Changes**:
```python
# BEFORE: Hardcoded model
self.model = SentenceTransformer('all-MiniLM-L6-v2')

# AFTER: Config-driven model loading
try:
    from ..config import RiffConfig
    config = RiffConfig()
    model_name = config.embedding_model
except Exception:
    model_name = 'BAAI/bge-small-en-v1.5'

self.model = SentenceTransformer(model_name)
```

**Impact**: Uses correct embedding model, ensuring semantic search operates on proper vector space

---

## 2. ✅ Lowered Default Search Threshold

**Issue**: Default threshold of 0.3 was too restrictive, preventing relevant results from appearing

**Files Modified**:
- `src/riff/cli.py` (line 529)
- `src/riff/search/qdrant.py` (line 102)

**Changes**:
```
Old default: --min-score 0.3
New default: --min-score 0.15
```

**Impact**: Better recall - now shows more potentially relevant results by default. Users can still use `--min-score 0.5` for strict matching if needed.

---

## 3. ✅ Added Fuzzy Matching Fallback

**Purpose**: Enable phrase/word searches to work even with semantic mismatch or typos

**Files Modified**:
- `src/riff/search/qdrant.py` (added lines 178-239)
- `src/riff/cli.py` (added lines 324-337)

**How It Works**:
1. **Semantic search** runs first (your main vector-based search)
2. **If results < 3**, automatically tries fuzzy matching
3. **Fuzzy match scoring**:
   - Exact substring match: score = 1.0
   - Partial word match: score = 0.8
   - Character similarity: proportional match score
4. **Results merged** with semantic results, no duplicates

**Example Use Case**:
```bash
# Search for specific phrase - gets semantic + fuzzy results
nabi riff search "authentication token bypass"

# Gets both semantic matches and exact phrase matches
# Combined results will include documents with exact phrases
```

---

## 4. ✅ Modal Preview in Search TUI

**Purpose**: View full message content in a formatted modal instead of just truncated preview

**Files Modified**:
- `src/riff/tui/prompt_toolkit_impl.py` (added lines 79-87, 190-221)
- `src/riff/cli.py` (updated lines 360, 370-373)

**New Key Binding**: `o` - Open preview modal from search results

**What You Get**:
```
╭─── Session Preview ───╮
│                       │
│ Session ID: abc-123.. │
│ Score: 85.3%          │
│ Location: /path/...   │
│                       │
│ Preview (first 500):  │
│ ───────────────────   │
│ Full message content  │
│ with word wrapping    │
│ for readability       │
│                       │
╰─ Press any key... ───╯
```

**Usage Flow**:
1. `nabi riff search "your query"` → Shows result list
2. Navigate with `j/k` to select result
3. Press `o` to see full preview modal
4. Press `Enter` to open full session in editor

---

## 5. ✅ Modal Preview in Graph Navigator

**Purpose**: View message details when browsing conversation DAG with `nabi riff graph <uuid>`

**Files Modified**:
- `src/riff/tui/graph_navigator.py` (added lines 373-375, 675-765, updated 117-131)

**New Key Binding**: `Enter` - Preview message from DAG tree

**What You Get** in Modal:
```
┌─────────────────────────────┐
│  Message Preview            │
├─────────────────────────────┤
│ UUID: msg-uuid-1234...      │
│ Type: assistant             │
│ Timestamp: 2025-11-03 12:34 │
│ Parent: parent-uuid-5678... │
│                             │
│ Content (first 500 chars):  │
│ ─────────────────────────   │
│ [Full message text wrapped] │
│ ... (truncated)             │
└─────────────────────────────┘
```

**Navigation Help Updated**:
- Old: "Enter: Expand/collapse thread"
- New: "Enter: Preview full message in modal"

---

## 6. ✅ Added TOML Dependency

**Files Modified**:
- `pyproject.toml` (added line 14)

**Change**:
```toml
dependencies = [
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.0",
    "rapidfuzz>=3.0.0",
    "toml>=0.10.2",  # ← NEW
]
```

---

## Usage Examples

### Search with Fuzzy Fallback
```bash
# Semantic + fuzzy search
nabi riff search "federation architecture"

# Output shows:
# 🎮 Interactive Mode
# Use j/k to navigate, Enter to open, o=preview, q to quit
# 📝 Combined semantic + fuzzy matching (found 8 total)
```

### Preview Search Results
```bash
# In interactive mode, press 'o' to preview
# Shows formatted panel with metadata + content
```

### Graph Navigation with Preview
```bash
# Browse conversation structure
nabi riff graph abc-123-def

# In TUI, press 'Enter' on any line to see full message
# Shows modal with UUID, type, timestamp, parent, and content
```

### Fine-Tune Threshold
```bash
# Strict matching (only very similar results)
nabi riff search "query" --min-score 0.5

# Loose matching (many candidate results)
nabi riff search "query" --min-score 0.1
```

---

## Key Improvements Summary

| Feature | Impact | Use Case |
|---------|--------|----------|
| **Model Fix** | Correct embedding space | Ensures semantic similarity scores are accurate |
| **Lower Threshold** | Better recall | Find relevant results that were hidden before |
| **Fuzzy Fallback** | Word/phrase search support | Search for exact phrases, not just semantic meaning |
| **Preview Modals** | See full context | Understand search results before opening full session |
| **Graph Preview** | Navigate DAG interactively | Explore conversation tree and read messages inline |

---

## Testing Checklist

- [x] CLI loads without errors
- [x] `riff search --help` shows updated help text
- [x] Embedding model loads from config
- [x] Default threshold is 0.15
- [x] Fuzzy matching triggers on low results
- [x] Search TUI 'o' key opens preview modal
- [x] Graph navigator 'Enter' key shows message modal
- [x] Help text updated in both TUI implementations

---

## Notes

- **Backward Compatible**: All changes are additive; existing commands work as before
- **Config-Driven**: Model selection now comes from `~/.config/nabi/tools/riff.toml`
- **Graceful Fallback**: If config missing, defaults to BAAI model
- **Performance**: Fuzzy search only triggers when needed (<3 results), minimal overhead

---

**Last Updated**: 2025-11-03
**Version**: 2.0.0+enhance
**Status**: ✅ Ready for Use

## 6. ✅ Proper Claude Code Session Resumption

**Purpose**: When opening a session, properly change to its working directory and resume in Claude Code with correct context

**Files Modified**:
- `src/riff/tui/prompt_toolkit_impl.py` (added `resume_session()` method, lines 190-229)
- `src/riff/cli.py` (updated call site, lines 372-376)

**How It Works**:
1. User navigates search results and presses `Enter` to open
2. `resume_session()` validates paths:
   - Session file exists
   - Working directory exists
3. Changes to the working directory: `os.chdir(working_directory)`
4. Executes: `os.execvp('claude', ['claude', '--resume', session_id])`
5. Process is replaced with Claude Code, preserving the context

**Key Features**:
- **Path Validation**: Checks both session file and working directory before proceeding
- **Process Replacement**: Uses `os.execvp()` to replace current process (not subprocess), so you're truly in the session context
- **Error Handling**: Provides helpful error messages if paths don't exist or `claude` command not found
- **Working Directory**: Restores the exact directory context the session was created in

**Example Flow**:
```bash
# In riff search results:
$ nabi riff search "federation patterns"

# Navigate with j/k, press Enter on result:
📁 Changing to directory: /path/to/federation-project
🚀 Resuming session: abc-123-def...

# Claude Code launches with session loaded in correct directory
# Your working directory is now /path/to/federation-project
```

**Why This Matters**:
Claude Code requires being in the correct working directory for:
- Relative file paths to work correctly
- Tool execution (git, npm, etc.) to use correct repository context
- Session state to load properly with full context
- `--resume` flag to find the JSONL file

---

