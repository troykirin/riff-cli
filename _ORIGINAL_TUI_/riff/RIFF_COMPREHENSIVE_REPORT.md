# RIFF: Comprehensive Report on Claude Session Management & Memory Interface Vision

## Executive Summary

Through deep investigation of Claude Code's session management system, we've uncovered the architecture of how AI conversations are stored, the problems that arise, and the opportunity to build a comprehensive memory interface system. The riff tool, initially conceived as a JSONL repair utility, has the potential to evolve into a "git for memories" - a version control system for cognitive processes.

## Part 1: How Claude Session Management Actually Works

### File System Structure
```
~/.claude/
├── projects/
│   └── [project-name]/
│       ├── [uuid].jsonl          # Session conversation files
│       └── backups/               # Session backups
├── todos/
│   └── [session-uuid]-agent-[uuid].json  # Task state per session
├── settings.json                  # Global settings
└── statsig/                      # Analytics/metrics
```

### JSONL Message Structure
Each line in a `.jsonl` file is a complete JSON object representing a message:

```json
{
  "sessionId": "49d6aef0-62d7-437f-92e8-760a747dda2e",
  "parentUuid": "6a225509-...",  // Links to previous message
  "uuid": "c962fe8a-...",        // This message's ID
  "type": "user",                // or "assistant"
  "message": {
    "role": "user",
    "content": [
      {"type": "text", "text": "..."},
      {"type": "tool_use", "id": "toolu_...", "name": "Bash", ...},
      {"type": "tool_result", "tool_use_id": "toolu_...", ...}
    ]
  },
  "timestamp": "2025-08-24T23:11:53.999Z",
  "cwd": "/home/user/project",
  "userType": "external",
  "gitBranch": "",
  "version": "1.0.90"
}
```

### Key Discoveries

1. **UUID Chain Structure**: Messages form a linked list via `parentUuid`, creating conversation threads
2. **Session Branching**: When conversations continue after errors, new sessions can reference old `sessionId`s
3. **Tool Use/Result Pairing**: Every `tool_use` must have a corresponding `tool_result`, but they don't need to be adjacent
4. **Todo State Persistence**: Stuck "in_progress" todos in `~/.claude/todos/` cause persistent errors
5. **Parallel Sessions**: Multiple Claude sessions CAN run simultaneously if they have clean, non-branched histories
6. **Compression Success**: Session `49d6aef0` compressed to 4 lines through `/compact` - shows potential for optimization

## Part 2: Problems Identified & Fixed

### Critical Issues Found
1. **Duplicate tool_results**: Riff tool bug creating multiple results for single tool_use
2. **Session branching**: Chain discovered: `40c2fb9f` → `45910070` → `f8e3b4d2` → `5efb2072` → `93ea02fa`
3. **Corrupt commands**: `/status` and `/compact` can corrupt sessions
4. **No native management**: Claude lacks built-in features for searching/managing historical sessions

### Repairs Implemented
- Removed duplicate tool_results from corrupted sessions
- Fixed stuck todos by changing "in_progress" to "completed"
- Backed up and removed branched sessions to eliminate noise
- Truncated corrupted sessions at clean breakpoints

## Part 3: The Riff Memory Interface Vision

### Core Architecture

```
riff/
├── core/          # JSONL parsing, validation, structure analysis
├── repair/        # Fix tool pairs, handle branching, merge sessions
├── index/         # SQLite database, incremental updates
├── search/        # Ripgrep, FTS, semantic search
├── tui/           # Rich/Textual terminal interface
├── export/        # Markdown, HTML, compressed formats
└── graph/         # NetworkX visualization
```

### TUI Design: Three-Pane Layout

```
┌─────────────────┬──────────────────┬────────────────┐
│ SESSION BROWSER │  MESSAGE LIST    │ CONTENT VIEWER │
├─────────────────┼──────────────────┼────────────────┤
│ ✓ 49d6aef0 (4)  │ 1. user: Start   │ Role: user     │
│ ✓ 40c2fb9f (62) │ 2. asst: I'll..  │ Time: 17:30    │
│ ✓ 5821e735 (34) │ > 3. user: Run.. │ ──────────────  │
│ ⚠ 93ea02fa (93) │ 4. asst: Run... │ Let me run the │
│                 │ 5. tool: Bash    │ test suite...  │
└─────────────────┴──────────────────┴────────────────┘
[/search] [g:graph] [r:repair] [e:export] [q:quit]
```

### Key Features

#### 1. Search & Navigation
- **FZF Integration**: `riff search [pattern]` with preview
- **Keybindings**: j/k (move), / (search), n/p (next/prev)
- **Search modes**: --code, --tools, --errors, --user, --assistant
- **Memory rotation**: 1-9 (jump to slots), Space (slideshow)

#### 2. Indexing System (SQLite/DuckDB)
```sql
-- Core tables
sessions (id, path, line_count, created_at, last_modified)
messages (session_id, line_num, uuid, parent_uuid, role, timestamp)
content_fts (message_id, content)  -- Full text search
tool_uses (message_id, tool_name, tool_id)
branches (from_session, to_session, branch_point)
```

#### 3. Intelligent Compression
**Knowledge Cards** for mobile viewing:
- Problem Statement (what was being solved)
- Approach (strategy and tools)  
- Challenges (errors encountered)
- Resolution (final solution)
- Insights (patterns discovered)

Each card links to relevant message ranges, creating Wikipedia-like summaries.

#### 4. Session Operations
- **Merge**: Untangle branched conversations into linear history
- **Diff**: Show what changed between sessions
- **Blame**: Identify when concepts were first understood
- **Cherry-pick**: Extract solutions between sessions
- **Rebase**: Reorganize messy histories

### Advanced Capabilities

#### Integration Layer
- Git correlation (commits during session)
- File system watcher (track all touched files)
- Browser history (link research with coding)
- Calendar context (meeting → coding session)
- Loki/Grafana (agent activity patterns)
- Obsidian/Logseq export

#### Security & Privacy
- Automatic secret detection/redaction
- Encryption at rest for archives
- Access control for shared environments
- Audit logging
- Sensitive data purging
- Filtered exports

#### Machine Learning Opportunities
- Predict next actions from context
- Detect anomalous patterns
- Suggest optimizations from history
- Auto-generate summaries
- Cluster by problem type
- Learn personal patterns

## Part 4: Implementation Roadmap

### Phase 1: Foundation (Current)
- [x] Basic JSONL repair functionality
- [x] Session validation
- [x] Duplicate detection
- [ ] Basic TUI with file browser

### Phase 2: Search & Index
- [ ] SQLite schema implementation
- [ ] Ripgrep integration
- [ ] FZF search interface
- [ ] Incremental indexing

### Phase 3: Advanced TUI
- [ ] Three-pane layout
- [ ] Message navigation
- [ ] Syntax highlighting
- [ ] Graph visualization

### Phase 4: Intelligence
- [ ] Session merging/untangling
- [ ] Semantic compression
- [ ] Knowledge cards
- [ ] ML-based insights

### Phase 5: Ecosystem
- [ ] Plugin system
- [ ] External integrations
- [ ] Mobile interface
- [ ] Distributed storage

## Conclusion

The riff tool represents a fundamental shift in how we interact with AI conversation history. By treating these interactions as valuable memory artifacts that need proper version control, search, and management tools, we're building infrastructure for the AI-augmented knowledge worker.

This isn't just about fixing corrupted Claude sessions - it's about recognizing that our conversations with AI assistants are becoming an extension of our cognitive processes and deserve the same sophistication in tooling that we've developed for code with git.

The vision: **Riff as the "git for memories"** - making our interactions with AI searchable, versionable, and most importantly, *learnable* from. Every session becomes a teachable moment, every error a learning opportunity, and every solution a reusable pattern.

## Next Steps

1. **Immediate**: Fix the riff repair bug (scan ahead for tool_results)
2. **Short-term**: Build basic TUI with search functionality  
3. **Medium-term**: Implement SQLite indexing and FZF integration
4. **Long-term**: Develop semantic compression and mobile interface

The journey from "JSONL repair tool" to "cognitive version control system" begins with understanding that our memories with AI are not just logs to be fixed, but knowledge to be cultivated.