# Riff Unified: Conversation Search + JSONL Repair

## 🎯 What You Get

A **single `riff` command** that does everything:

1. **Search Claude Conversations** with actual content snippets visible
2. **Vim-style Navigation** through results
3. **Repair JSONL** files (original functionality preserved)
4. **Interactive Browsing** with rich preview

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│     riff (unified CLI)          │
│    Single entry point, smart    │
│      command routing            │
└──────────────┬──────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌────────┐
│ NEW:   │ │OLD:  │ │OLD:    │
│Search  │ │TUI   │ │Repair  │
│Browse  │ │Scan  │ │Graph   │
└───┬────┘ └──┬───┘ └───┬────┘
    │         │         │
    ▼         ▼         ▼
┌─────────────────────────────────┐
│   Backend Strategy Layer         │
├──────────┬──────────┬────────────┤
│ Qdrant   │ Rich TUI │  Intent AI │
│ Semantic │ Classic  │ Enhancer   │
└──────────┴──────────┴────────────┘
```

## 📋 Directory Structure

```
src/riff/
├── __init__.py              # Package init
├── cli.py                   # Unified entry point
│
├── classic/                 # Original TUI preserved
│   ├── __init__.py
│   ├── utils.py
│   └── commands/
│       ├── tui.py          # Interactive JSONL browser
│       ├── scan.py         # Scan for issues
│       ├── fix.py          # Repair JSONL
│       └── graph.py        # Generate graphs
│
├── search/                  # NEW: Search with snippets
│   ├── __init__.py
│   ├── qdrant.py           # Vector search backend
│   └── preview.py          # Rich content preview
│
├── enhance/                 # NEW: AI enhancements
│   ├── __init__.py
│   └── intent.py           # Intent detection & expansion
│
└── backends/                # Future: Nushell, CMP
    └── __init__.py
```

## 🚀 Quick Start

### Setup

```bash
# Create environment
uv venv

# Activate
source .venv/bin/activate

# Install core dependencies
uv pip install -r python/requirements.txt

# Optional: Install search dependencies
uv pip install qdrant-client sentence-transformers
```

### Run

```bash
# Show help
./riff --help

# Search conversations (NEW!)
./riff search "memory architecture"

# Search with AI enhancement (NEW!)
./riff search --ai "federation patterns"

# Search by UUID
./riff search --uuid abc-123-def

# Original commands (preserved)
./riff scan ~/claude/
./riff fix session.jsonl
./riff tui
./riff graph session.jsonl
```

## ✨ New Capabilities

### Search with Content Preview

```bash
$ ./riff search "memory layers"

🔍 Search Results (3 found)
Query: memory layers

┌──────────────────────────────────────────┐
│ Idx │ Session ID      │ Score │ Directory│
├─────┼─────────────────┼───────┼──────────┤
│  1  │ abc-123-def...  │ 0.92  │ ~/claude/│
│  2  │ xyz-456-ghi...  │ 0.87  │ ~/claude/│
│  3  │ pqr-789-stu...  │ 0.81  │ ~/sync/  │
└──────────────────────────────────────────┘

Content Previews:

[1] abc-123-def-456
"...discussing memory layers
 and how coordination differs
 from knowledge storage..."

[2] xyz-456-ghi-789
"...the three-tier memory
 architecture enables..."
```

### Direct UUID Search

```bash
$ ./riff search --uuid abc-123-def-456

✅ Found session: abc-123-def-456
📁 Directory: ~/claude/sessions
📊 Score: 1.000
📝 Preview: "...the conversation about memory systems..."
```

### AI-Enhanced Search

```bash
$ ./riff search --ai "how did we solve that memory leak?"

🔍 Enhanced query: memory leak solve architecture debugging optimization
Found 5 sessions for: ...
```

## 🔧 Restored Functionality

All original commands work exactly as before:

```bash
# Scan JSONL files
./riff scan ~/claude/ --glob "**/*.jsonl" --show

# Repair JSONL issues
./riff fix session.jsonl --in-place

# Interactive TUI (vim-style)
./riff tui ~/claude/ --fzf

# Generate conversation graphs
./riff graph session.jsonl --format mermaid --out graph.md
```

## 📂 Use Case: Searching Your Conversation Snippets

The key difference from before: **you can actually see the text you're searching for**.

Before unification:
```
❌ File path only
❌ No content preview
❌ Can't see what you're searching for
```

After unification:
```
✅ Semantic search ("memory architecture")
✅ Content previews in results
✅ Direct UUID lookup
✅ AI-enhanced queries
✅ Vim-style navigation
```

## 🔌 Integration with CMP

The unified riff can leverage CMP (Cognitive Memory Protocol) for:
- Cognitive search across sessions
- Memory-aware result ranking
- Cross-session context awareness

Future enhancement: `./riff search --cognitive "..."`

## 📝 Implementation Notes

- **Zero Breaking Changes**: All original commands preserved
- **Modular Design**: Each backend is independent
- **Type Safe**: Python 3.13+ with full typing
- **Rich UI**: Terminal-friendly with color and formatting

## 🔮 Future Enhancements

1. Full interactive vim navigator with j/k/g/G navigation
2. CMP integration for cognitive search
3. Nushell backend for fast UUID extraction
4. Full-text search with highlighting
5. Search history and saved queries
6. Integration with nabi CLI registry

## 🎯 Success Metrics

✅ Single `riff` command for all operations
✅ See actual content snippets, not just paths
✅ Vim-style interface preserved
✅ Original repair functionality intact
✅ Search with multiple backends (Qdrant, Intent)
✅ AI enhancement available
✅ Type-safe Python 3.13+ code

---

**Now you can actually "riff" through your conversations!**
