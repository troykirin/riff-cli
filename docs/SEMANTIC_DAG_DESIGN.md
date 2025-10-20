# Semantic Conversation DAG Architecture

**Vision**: Visualize Claude conversations like git trees, but semantically intelligent

**Model**: Conversations as hierarchical semantic structures, not just linear parent-child chains

---

## 1. Core Data Model

### ConversationDAG
```python
class ConversationDAG:
    """Semantic DAG of a conversation session"""

    def __init__(self, session_id: str, messages: List[Message]):
        self.session_id = session_id
        self.messages = {msg.uuid: msg for msg in messages}
        self.graph = self._build_semantic_graph()
        self.threads = self._identify_semantic_threads()
        self.orphans = self._detect_orphaned_branches()

    def _build_semantic_graph(self) -> Dict:
        """Build parent-child relationships with semantic clustering"""
        # Structural: parentUuid → children
        # Semantic: topic/intent clustering → related messages
        pass

    def _identify_semantic_threads(self) -> List[SemanticThread]:
        """Identify primary thread + side discussions"""
        pass

    def _detect_orphaned_branches(self) -> List[OrphanedBranch]:
        """Find disconnected branches"""
        pass
```

### Message Enrichment
```python
@dataclass
class Message:
    uuid: str
    parent_uuid: Optional[str]
    type: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str

    # NEW: Semantic enrichment
    semantic_topic: Optional[str]      # e.g., "architecture", "debugging", "question"
    semantic_confidence: float         # 0.0-1.0 how confident we are
    thread_id: Optional[str]           # which thread this belongs to
    is_orphaned: bool = False
    corruption_score: float = 0.0      # likelihood this is corrupted/orphaned
```

---

## 2. Semantic Thread Detection

### What is a "Thread"?

```
Main Thread: Continuous conversation from root
├─ Messages with valid parentUuid chain to root
├─ Primary topic (semantic)
└─ Longest continuous path

Side Discussion: Topical detour
├─ User asks tangential question
├─ Claude responds
├─ User says "back to..." or similar intent marker
└─ Rejoins main thread

Orphaned Branch: Disconnected by bug
├─ parentUuid points to non-existent message
├─ OR parentUuid is null but not root
├─ Indicates resume/branch failure
└─ No valid path to root
```

### Detection Algorithm

```python
def identify_semantic_threads(self) -> List[SemanticThread]:
    """
    1. Build structural graph (parentUuid relationships)
    2. Identify connected components
    3. Find main thread (longest path from roots)
    4. Cluster remaining by semantic similarity
    5. Detect re-entry points (where branches rejoin)
    """

    # Phase 1: Structural Analysis
    main_thread = self._find_longest_path_from_roots()
    disconnected_components = self._find_connected_components()

    # Phase 2: Semantic Analysis
    for component in disconnected_components:
        if is_likely_side_discussion(component, main_thread):
            # Has re-entry point back to main
            yield SemanticThread(
                type="side_discussion",
                messages=component,
                main_thread_connection=re_entry_point
            )
        else:
            # Orphaned (no re-entry)
            yield OrphanedBranch(
                type="orphaned",
                messages=component,
                corruption_likelihood=score_corruption(component)
            )
```

---

## 3. Corruption Detection

### Orphan Scoring Algorithm

```python
def score_corruption(messages: List[Message]) -> float:
    """
    Estimate likelihood this branch is corruption vs intentional

    Factors:
    - parentUuid=null for non-root (high corruption signal)
    - Timestamp immediately after previous message (indicates resume failure)
    - isSidechain=true without valid parent (indicates failed resume)
    - Content doesn't match conversation flow
    - No semantic connection to main thread
    """

    score = 0.0

    # Signal 1: Invalid parent
    if messages[0].parent_uuid is None and not is_root(messages[0]):
        score += 0.4

    # Signal 2: Timestamp pattern
    if timestamp_immediately_after_previous(messages[0]):
        score += 0.2

    # Signal 3: Sidechain flag without valid parent
    if messages[0].is_sidechain and not has_valid_parent(messages[0]):
        score += 0.3

    # Signal 4: Semantic disconnection
    semantic_distance = distance_to_main_thread(messages[0])
    if semantic_distance > 0.7:  # Very different topic
        score += 0.1

    return min(score, 1.0)
```

---

## 4. ASCII Tree Visualization

### Output Format (like `git log --graph`)

```
* 2025-10-20 User: "analyze riff-cli"
* 2025-10-20 Assistant: "I'll examine the architecture..."
* 2025-10-20 User: "what about the TUI?"
* 2025-10-20 Assistant: "The TUI uses prompt_toolkit..."
|\
| * 2025-10-20 [Side] User: "what's semantic search?"
| * 2025-10-20 [Side] Assistant: "It uses embeddings..."
|/
* 2025-10-20 User: "back to the main question..."
* 2025-10-20 Assistant: "Right, so for the architecture..."
|
| ! 2025-10-20 [ORPHANED] User: "Resume attempt"
| ! 2025-10-20 [ORPHANED] Assistant: "Continuing conversation..."
| ! 2025-10-20 [ORPHANED] User: "more work on this"
| ! (parentUuid=null, likely resume failure)
|
* 2025-10-20 User: "final thoughts"
* 2025-10-20 Assistant: "Summary of work..."
```

### Visualization Class

```python
class ConversationTreeVisualizer:
    """Generate ASCII tree output for semantic DAG"""

    def visualize(self, dag: ConversationDAG) -> str:
        """
        Build ASCII tree showing:
        - Main thread as * markers
        - Side discussions as | branches
        - Orphaned branches as ! markers
        - Topic labels and timestamps
        """
        output = []

        # Render main thread
        for msg in dag.threads[0].messages:
            output.append(self._format_main_thread_message(msg))

        # Render side discussions with branch markers
        for thread in dag.threads[1:]:
            output.append(f"|")
            for msg in thread.messages:
                output.append(self._format_side_discussion_message(msg))
            output.append(f"|/")

        # Render orphaned branches with warning
        for orphan in dag.orphans:
            output.append(f"|")
            for msg in orphan.messages:
                output.append(self._format_orphaned_message(msg))

        return "\n".join(output)
```

---

## 5. Repair Strategy

### Atomic Relink Operations

```python
class ConversationRepair:
    """Atomic repair operations for broken conversation chains"""

    def relink_orphan_to_main_thread(
        self,
        orphan: OrphanedBranch,
        main_thread: SemanticThread,
        insertion_point: Message
    ) -> RepairOperation:
        """
        Relink orphan branch to main thread

        Steps:
        1. Validate: orphan.messages[0].parent_uuid = insertion_point.uuid
        2. Backup: save original state
        3. Update: modify JSONL parent references
        4. Validate: rebuild DAG and verify connectivity
        5. Commit: atomic write with audit trail
        6. Rollback: restore from backup if verification fails
        """

        operation = RepairOperation(
            type="relink",
            from_branch=orphan,
            to_point=insertion_point,
            backup_file=self._create_backup(),
            changes=[]
        )

        # Update parent UUID
        orphan.messages[0].parent_uuid = insertion_point.uuid
        operation.changes.append({
            "message_uuid": orphan.messages[0].uuid,
            "field": "parentUuid",
            "old_value": None,
            "new_value": insertion_point.uuid
        })

        # Validate result
        new_dag = ConversationDAG(self.session_id, all_messages)
        if not self._is_valid_dag(new_dag):
            operation.rollback()
            raise RepairError("Repair would create invalid DAG")

        return operation

    def interactive_repair(self, dag: ConversationDAG):
        """
        Present user with repair options for detected corruption

        Show:
        - Orphaned branches with corruption scores
        - Suggested reconnection points
        - Preview of changes
        - Confirmation before commit
        """
        pass
```

---

## 6. Integration with riff-cli TUI

### New TUI Mode: "Graph View"

```python
class ConversationGraphNavigator(InteractiveTUI):
    """Navigate conversation structure as semantic DAG"""

    def __init__(self, dag: ConversationDAG, console: Console):
        self.dag = dag
        self.console = console
        self.current_thread_idx = 0
        self.current_msg_idx = 0

    def navigate(self) -> NavigationResult:
        """
        Vim keys:
        - j/k: Move down/up within thread
        - l/h: Move right/left between threads
        - g: Go to main thread start
        - G: Go to end
        - o: Open message details
        - r: Show repair suggestions for orphans
        - Enter: Accept repair
        - q: Quit
        """
        pass

    def display_tree(self):
        """Show ASCII tree visualization"""
        self.console.print(self.dag.visualize())

    def highlight_orphans(self):
        """Highlight orphaned branches in red"""
        pass

    def show_repair_suggestions(self):
        """Interactive repair assistant"""
        pass
```

---

## 7. CLI Integration

### claude-manager Commands

```bash
# Diagnose session structure
cm diagnose:graph <session-id>
# Output:
# ├─ Main thread: 45 messages, 2025-10-15 to 2025-10-20
# ├─ Side discussions: 12 messages (3 re-entries)
# └─ Orphaned branches: 2 (41 messages, corruption score 0.9+)
#
# Detailed view: cm diagnose:graph <session-id> --verbose

# Interactive repair
cm repair:graph <session-id> [--dry-run] [--interactive]
# Presents options, shows preview, asks for confirmation

# Visualize tree
cm view:tree <session-id> [--highlight-orphans] [--ascii]
```

### riff-cli Integration

```bash
# Launch graph navigator on a session
riff graph <session-id>
# Shows semantic tree, allows vim navigation
# 'r' key shows repair suggestions

# Search + graph
riff search "topic" --days 3 --graph
# Show search results as graph view instead of list
```

---

## 8. Data Flow

```
JSONL File
  ↓
Parse Messages (extract uuid, parentUuid, content, timestamp)
  ↓
ConversationDAG
  ├─ Build structural graph (parentUuid relationships)
  ├─ Identify connected components
  ├─ Semantic clustering (topic detection)
  └─ Orphan detection (corruption scoring)
  ↓
Semantic Threads
  ├─ Main thread (longest path from roots)
  ├─ Side discussions (branches with re-entries)
  └─ Orphaned branches (no connection to main)
  ↓
Visualization Options
  ├─ ASCII tree (git log --graph style)
  ├─ TUI navigator (interactive)
  └─ Repair suggestions (interactive repair)
  ↓
Repair Operations (if needed)
  ├─ Validate candidate repairs
  ├─ Preview changes
  ├─ Atomic commit with audit trail
  └─ Rollback on failure
```

---

## 9. Success Criteria

✅ **Graph Building**
- Parse JSONL and correctly identify all parent-child relationships
- Handle null parentUuids
- Build connected components

✅ **Semantic Detection**
- Distinguish main thread from side discussions
- Score likelihood of corruption
- Detect re-entry points

✅ **Visualization**
- ASCII tree output matching git log format
- TUI navigation with vim keys
- Clear marking of orphaned branches

✅ **Repair**
- Atomic relink operations
- Validation before/after
- Audit trail of changes
- Rollback capability

✅ **Integration**
- claude-manager `cm diagnose:graph` and `cm repair:graph`
- riff-cli graph view mode
- Seamless with existing tools

---

## 10. Example Session

```bash
# User diagnoses a session that feels broken
$ cm diagnose:graph 794650a6-84a5-446b-879c-639ee85fbde4

Main Thread: 3 messages (2025-10-15)
├─ User: "analyze riff-cli"
├─ Assistant: "I'll examine the architecture..."
└─ User: "what about the TUI?"

Side Discussion: 12 messages (2025-10-15 to 2025-10-20, reconnected)
├─ User: "quick question about search"
├─ Assistant: "That's handled by Qdrant..."
└─ [Rejoins main] User: "back to architecture..."

⚠️ ORPHANED BRANCH: 99 messages (corruption score: 0.92)
├─ User: "Resume attempt" (parentUuid=null, isSidechain=true)
├─ Assistant: "Continuing..."
└─ ... (further conversation)

# User wants to repair
$ cm repair:graph 794650a6-84a5-446b-879c-639ee85fbde4 --interactive

Found 1 orphaned branch with high corruption probability (0.92)

Suggested repair: Relink orphan to main thread at message 3
├─ Set orphan[0].parentUuid = message[3].uuid
├─ Result: 108 messages in single continuous thread
└─ Backup: saved to ~/.claude/backups/[session-id].backup

Proceed with repair? [y/n] y

✅ Repair complete
├─ Modified: 1 message (orphan[0].parentUuid)
├─ Backup: ~/.claude/backups/[session-id].backup
└─ Audit: Repair logged in session metadata

# Now user can navigate
$ riff graph 794650a6-84a5-446b-879c-639ee85fbde4

(Interactive TUI shows semantic tree with vim navigation)
```

---

## Implementation Roadmap

**Phase 1: Core DAG (Week 1)**
- ConversationDAG class
- Graph building from JSONL
- Basic orphan detection

**Phase 2: Visualization (Week 1-2)**
- ASCII tree generator
- TUI navigator
- Semantic thread identification

**Phase 3: Repair (Week 2)**
- Atomic relink operations
- Repair validation
- Audit trails

**Phase 4: Integration (Week 3)**
- claude-manager commands
- riff-cli graph mode
- End-to-end testing

