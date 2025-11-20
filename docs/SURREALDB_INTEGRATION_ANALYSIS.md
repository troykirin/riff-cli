# SurrealDB Integration Analysis

**Analysis Date**: 2025-10-20
**Context**: Designing ConversationDAG integration with existing SurrealDB infrastructure

---

## 🔍 **What Currently Exists**

### Location: `/Users/tryk/nabia/memchain/surreal/knowledge-graph/`

### 1. **SurrealDB Schema (Generic Knowledge Graph)**

```sql
-- Current model (entity-relation-observation pattern)
DEFINE TABLE entity SCHEMAFULL;
DEFINE FIELD name ON entity TYPE string;
DEFINE FIELD entityType ON entity TYPE string;
DEFINE FIELD observations ON entity TYPE array<string>;
DEFINE FIELD slug ON entity TYPE string;
DEFINE FIELD search_terms ON entity TYPE string;

-- Indexes
DEFINE INDEX entity_name_idx ON entity COLUMNS name;
DEFINE INDEX entity_type_idx ON entity COLUMNS entityType;
DEFINE INDEX entity_slug_idx ON entity COLUMNS slug;

-- Full-text search
DEFINE ANALYZER search_analyzer TOKENIZERS blank,class FILTERS snowball(english),lowercase;
DEFINE INDEX entity_search_idx ON entity COLUMNS search_terms SEARCH ANALYZER search_analyzer BM25(1.2,0.75);

-- Relations
RELATE entity:from->relation->entity:to SET relationType = 'type';
```

**Data Model:**
- Entities: Generic knowledge nodes (people, concepts, etc.)
- Relations: Typed edges between entities
- Observations: Array of strings describing entities

### 2. **Pipeline Infrastructure**

```
knowledge-graph/pipeline/
├── core.py              # Pipeline engine (ETL/ELT)
├── loaders/             # Data source loaders
├── processors/          # Transform processors
└── validators/          # Validation stages
```

**Features:**
- Staged processing (Extract → Validate → Transform → Load)
- Plugin-based processors
- Configuration-driven
- Stream processing support
- Comprehensive error handling

### 3. **Import/Export Scripts**

```python
# scripts/surrealdb_importer.py
class SurrealDBImporter:
    def setup_schema()           # Creates entity/relation schema
    def import_jsonl()           # JSONL → SurrealDB
    def search_entities()        # Full-text search
    def query_relations()        # Graph traversal
```

**Capabilities:**
- JSONL → SurrealQL conversion
- Direct HTTP API access
- Full-text search
- Relation queries

### 4. **Database Configuration**

```
Namespace: knowledge
Database: graph
URL: http://localhost:8000
Auth: root/root (default)
```

---

## ❌ **What's Missing (For Conversations)**

### No Conversation-Specific Models

The existing schema is for **generic entities**, not **conversations**:

| Current (Entity Model) | Needed (Conversation Model) |
|------------------------|------------------------------|
| Entity (generic node) | Message (conversation node) |
| entityType (string) | type (user/assistant/system) |
| observations (array) | content (message text) |
| relation (generic) | parentUuid (explicit parent link) |
| - | timestamp (temporal ordering) |
| - | threadId (semantic grouping) |
| - | isSidechain (branch marker) |
| - | corruption_score (integrity) |

### No Conversation Operations

Missing:
- ❌ Message parent-child tracking
- ❌ Thread detection/grouping
- ❌ Temporal ordering
- ❌ Sidechain/orphan detection
- ❌ Semantic thread analysis
- ❌ DAG traversal for conversations

---

## 🏗️ **Integration Architecture**

### **Design Decision: Layered Approach**

```
┌─────────────────────────────────────────────────────────────┐
│  User Interface Layer                                       │
│  ├─ riff-cli TUI (visualization, curation)                  │
│  └─ claude-manager CLI (repair, validation)                 │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│  Application Layer - ConversationDAG                        │
│  ├─ Parse conversations into DAG                            │
│  ├─ Semantic thread detection                               │
│  ├─ Corruption detection                                    │
│  └─ Storage-agnostic interface                              │
└──────────┬──────────────────────────────────┬───────────────┘
           ↓                                   ↓
┌──────────────────────┐           ┌──────────────────────────┐
│  JSONL Storage       │           │  SurrealDB Storage       │
│  (Source of Truth)   │           │  (Cached Graph)          │
│                      │           │                          │
│  - Claude sessions   │───parse──→│  - Parsed conversations  │
│  - Read-only         │           │  - Fast graph queries    │
│  - Authoritative     │           │  - User curation         │
└──────────────────────┘           └──────────────────────────┘
           ↓                                   ↓
┌──────────────────────┐           ┌──────────────────────────┐
│  Qdrant              │           │  Search Index            │
│  - Semantic search   │←──index───│  - Embeddings            │
│  - Vector queries    │           │  - Time filtering        │
└──────────────────────┘           └──────────────────────────┘
```

### **Data Flow Phases**

**Phase 1: Foundation (Current - JSONL only)**
```
JSONL files → ConversationDAG → Qdrant (semantic search)
                              → In-memory graph visualization
```

**Phase 2: SurrealDB Caching (Next)**
```
JSONL files → ConversationDAG → SurrealDB (cached graph)
                              → Qdrant (semantic search)
                              → TUI (reads from SurrealDB cache)
```

**Phase 3: Full Integration (Future)**
```
JSONL files → ConversationDAG → SurrealDB (primary storage)
                              → Qdrant (semantic search index)
                              → User curation (bookmarks, tags, notes)
                              → JSONL export (backup/compatibility)
```

---

## 📐 **Proposed Conversation Schema**

### **New Tables for SurrealDB**

```sql
-- Conversation Session
DEFINE TABLE session SCHEMAFULL;
DEFINE FIELD session_id ON session TYPE string;
DEFINE FIELD file_path ON session TYPE string;
DEFINE FIELD working_directory ON session TYPE string;
DEFINE FIELD first_message_timestamp ON session TYPE datetime;
DEFINE FIELD last_message_timestamp ON session TYPE datetime;
DEFINE FIELD message_count ON session TYPE int;
DEFINE FIELD thread_count ON session TYPE int;
DEFINE FIELD has_orphans ON session TYPE bool;

DEFINE INDEX session_id_idx ON session COLUMNS session_id UNIQUE;
DEFINE INDEX session_timestamp_idx ON session COLUMNS first_message_timestamp;

-- Message Node
DEFINE TABLE message SCHEMAFULL;
DEFINE FIELD uuid ON message TYPE string;
DEFINE FIELD session_id ON message TYPE string;
DEFINE FIELD parent_uuid ON message TYPE option<string>;
DEFINE FIELD type ON message TYPE string;  -- "user" | "assistant" | "system"
DEFINE FIELD content ON message TYPE string;
DEFINE FIELD timestamp ON message TYPE datetime;
DEFINE FIELD is_sidechain ON message TYPE bool;
DEFINE FIELD thread_id ON message TYPE option<string>;
DEFINE FIELD semantic_topic ON message TYPE option<string>;
DEFINE FIELD corruption_score ON message TYPE float DEFAULT 0.0;

DEFINE INDEX message_uuid_idx ON message COLUMNS uuid UNIQUE;
DEFINE INDEX message_session_idx ON message COLUMNS session_id;
DEFINE INDEX message_timestamp_idx ON message COLUMNS timestamp;
DEFINE INDEX message_thread_idx ON message COLUMNS thread_id;

-- Full-text search on message content
DEFINE ANALYZER message_analyzer TOKENIZERS blank,class FILTERS snowball(english),lowercase;
DEFINE INDEX message_content_idx ON message COLUMNS content SEARCH ANALYZER message_analyzer BM25(1.2,0.75);

-- Thread (Semantic Grouping)
DEFINE TABLE thread SCHEMAFULL;
DEFINE FIELD thread_id ON thread TYPE string;
DEFINE FIELD session_id ON thread TYPE string;
DEFINE FIELD thread_type ON thread TYPE string;  -- "main" | "side_discussion" | "orphaned"
DEFINE FIELD semantic_topic ON thread TYPE option<string>;
DEFINE FIELD message_count ON thread TYPE int;
DEFINE FIELD first_timestamp ON thread TYPE datetime;
DEFINE FIELD last_timestamp ON thread TYPE datetime;
DEFINE FIELD corruption_score ON thread TYPE float DEFAULT 0.0;

DEFINE INDEX thread_id_idx ON thread COLUMNS thread_id UNIQUE;
DEFINE INDEX thread_session_idx ON thread COLUMNS session_id;
DEFINE INDEX thread_type_idx ON thread COLUMNS thread_type;

-- Relations (Parent-Child Links)
RELATE message->child_of->message SET
    created_at = time::now();

-- Thread membership
RELATE message->belongs_to->thread SET
    join_timestamp = time::now();

-- Session membership
RELATE message->part_of->session SET
    message_index = 0;
```

### **Key Design Decisions**

1. **Separate message, thread, session tables** - Allows independent querying
2. **Explicit parent_uuid field** - Plus `child_of` relation for graph queries
3. **Corruption scoring** - Stored at message and thread levels
4. **Semantic metadata** - Thread topic, type classification
5. **Temporal indexing** - Fast time-range queries
6. **Full-text search** - BM25 on message content

---

## 🔌 **ConversationDAG Storage Interface**

### **Abstract Storage Interface**

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class ConversationStorage(ABC):
    """Abstract storage interface for ConversationDAG"""

    @abstractmethod
    def load_session(self, session_id: str) -> Dict:
        """Load session metadata"""
        pass

    @abstractmethod
    def load_messages(self, session_id: str) -> List[Message]:
        """Load all messages for a session"""
        pass

    @abstractmethod
    def save_session(self, session: Session) -> bool:
        """Save session and all messages"""
        pass

    @abstractmethod
    def update_message(self, message: Message) -> bool:
        """Update single message (e.g., relink parent)"""
        pass

    @abstractmethod
    def search_messages(self, query: str, **filters) -> List[Message]:
        """Search messages with filters"""
        pass

    @abstractmethod
    def query_graph(self, session_id: str, query: Dict) -> List[Message]:
        """Graph traversal queries"""
        pass
```

### **JSONL Implementation**

```python
class JSONLStorage(ConversationStorage):
    """Storage backed by Claude Code JSONL files"""

    def load_messages(self, session_id: str) -> List[Message]:
        # Parse JSONL file
        file_path = self._resolve_session_file(session_id)
        messages = []

        with open(file_path) as f:
            for line in f:
                data = json.loads(line)
                if data.get('type') in ['user', 'assistant']:
                    messages.append(self._parse_message(data))

        return messages

    def save_session(self, session: Session) -> bool:
        # JSONL is read-only, return False
        return False
```

### **SurrealDB Implementation**

```python
class SurrealDBStorage(ConversationStorage):
    """Storage backed by SurrealDB graph database"""

    def __init__(self, url: str = "http://localhost:8000"):
        self.client = Surreal(url)
        self.client.signin({"user": "root", "pass": "root"})
        self.client.use("knowledge", "conversations")

    def load_messages(self, session_id: str) -> List[Message]:
        # Query SurrealDB
        query = """
        SELECT * FROM message
        WHERE session_id = $session_id
        ORDER BY timestamp ASC
        """
        results = self.client.query(query, {"session_id": session_id})
        return [self._parse_message(r) for r in results]

    def save_session(self, session: Session) -> bool:
        # Atomic transaction
        try:
            # Create session
            self.client.create("session", session.to_dict())

            # Create all messages
            for message in session.messages:
                self.client.create("message", message.to_dict())

            # Create parent-child relations
            for message in session.messages:
                if message.parent_uuid:
                    self.client.query("""
                        RELATE message:$uuid->child_of->message:$parent_uuid
                    """, {
                        "uuid": message.uuid,
                        "parent_uuid": message.parent_uuid
                    })

            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def query_graph(self, session_id: str, query: Dict) -> List[Message]:
        # Example: Find all orphaned messages
        if query.get("type") == "orphans":
            results = self.client.query("""
                SELECT * FROM message
                WHERE session_id = $session_id
                  AND parent_uuid = NONE
                  AND (SELECT COUNT() FROM message->child_of)[0] = 0
            """, {"session_id": session_id})
            return [self._parse_message(r) for r in results]
```

---

## 🎯 **Integration Strategy**

### **Phase 1: Foundation (This Week)**

**Goal**: Get ConversationDAG working with JSONL

```python
# riff-cli uses JSONL storage
storage = JSONLStorage()
dag = ConversationDAG(storage, session_id)

# Visualize in TUI
navigator = ConversationGraphNavigator(dag)
navigator.navigate()
```

**Deliverables:**
- ConversationDAG class with JSONL loader
- ASCII tree visualization
- TUI navigator with vim keys
- Corruption detection

**No SurrealDB required yet** - Build foundation first.

---

### **Phase 2: SurrealDB Caching (Next Week)**

**Goal**: Add SurrealDB as materialized view cache

```python
# Parse once, cache in SurrealDB
jsonl_storage = JSONLStorage()
dag = ConversationDAG(jsonl_storage, session_id)

# Cache to SurrealDB
surreal_storage = SurrealDBStorage()
surreal_storage.save_session(dag.to_session())

# Future loads read from cache
cached_dag = ConversationDAG(surreal_storage, session_id)  # Fast!
```

**Deliverables:**
- SurrealDB conversation schema (SQL above)
- SurrealDBStorage implementation
- Sync command: `riff sync:surrealdb <session-id>`
- Verify cached data matches JSONL

**Benefits:**
- Fast graph queries
- No re-parsing JSONL
- Foundation for curation

---

### **Phase 3: Memory Curation (Week 3)**

**Goal**: User curation in TUI, saved to SurrealDB

```python
# TUI operations modify SurrealDB
navigator.bookmark_message(message_uuid)    # Adds tag in SurrealDB
navigator.delete_thread(thread_id)          # Marks for deletion
navigator.add_note(message_uuid, "note")    # Saves annotation

# All operations stored in SurrealDB
# JSONL remains read-only
```

**New Schema Additions:**
```sql
-- User Curation
DEFINE TABLE bookmark SCHEMAFULL;
DEFINE FIELD message_uuid ON bookmark TYPE string;
DEFINE FIELD user_note ON bookmark TYPE option<string>;
DEFINE FIELD created_at ON bookmark TYPE datetime;

RELATE message->bookmarked_by->user;
```

**Deliverables:**
- TUI keybindings: `b` (bookmark), `n` (note), `d` (delete)
- Curation saved to SurrealDB
- Export curated view to JSONL

---

## 📊 **Data Sync Strategy**

### **Option 1: Cache-Aside (Recommended)**

```
JSONL (authoritative)
  ↓ parse on-demand
ConversationDAG (in-memory)
  ↓ cache
SurrealDB (materialized view)
  ↑ read cached
TUI (queries SurrealDB if exists, else JSONL)
```

**Workflow:**
1. First access: Parse JSONL → Cache to SurrealDB
2. Subsequent: Read from SurrealDB (fast)
3. JSONL changes: Invalidate cache, re-parse
4. User edits: Update SurrealDB only

### **Option 2: Write-Through (Future)**

```
New conversations → SurrealDB (primary)
                 → JSONL export (backup)
```

**When to migrate**: When you want conversations authored in your tools, not Claude Code.

---

## 🔍 **Query Examples**

### **Find All Orphaned Branches**

```sql
-- SurrealDB query
SELECT
    m.uuid,
    m.content,
    m.timestamp,
    m.corruption_score
FROM message m
WHERE m.session_id = $session_id
  AND m.parent_uuid = NONE
  AND (SELECT COUNT() FROM (SELECT * FROM message WHERE parent_uuid = m.uuid))[0] > 0
ORDER BY m.timestamp DESC;
```

### **Get Thread Timeline**

```sql
-- Get all messages in a thread, ordered
SELECT
    m.uuid,
    m.type,
    m.content,
    m.timestamp
FROM message m
WHERE m.thread_id = $thread_id
ORDER BY m.timestamp ASC;
```

### **Find Related Discussions**

```sql
-- Semantic search with BM25
SELECT
    m.uuid,
    m.content,
    search::score(1) AS relevance
FROM message m
WHERE m.session_id = $session_id
  AND m.content @1@ $search_query
ORDER BY relevance DESC
LIMIT 10;
```

### **Repair Operation: Relink Orphan**

```sql
-- Update parent UUID
UPDATE message:$orphan_uuid SET parent_uuid = $new_parent_uuid;

-- Create relation
RELATE message:$orphan_uuid->child_of->message:$new_parent_uuid;

-- Update corruption score
UPDATE message:$orphan_uuid SET corruption_score = 0.0;
```

---

## ✅ **Implementation Checklist**

### Phase 1: Foundation (JSONL only)
- [ ] ConversationDAG class
- [ ] JSONLStorage implementation
- [ ] Message/Thread data classes
- [ ] ASCII tree visualizer
- [ ] TUI navigator
- [ ] Corruption detection

### Phase 2: SurrealDB Caching
- [ ] Create conversation schema in SurrealDB
- [ ] SurrealDBStorage implementation
- [ ] Sync command (`riff sync:surrealdb`)
- [ ] Cache validation tests
- [ ] Query performance benchmarks

### Phase 3: Memory Curation
- [ ] Bookmark/tag schema
- [ ] TUI curation keybindings
- [ ] Note/annotation support
- [ ] Export curated sessions
- [ ] Cross-session linking

---

## 📝 **Next Steps**

1. **Implement ConversationDAG with JSONL** (Phase 1)
   - Get foundation working
   - Prove out the abstraction
   - Validate with real sessions

2. **Design conversation schema** (Phase 2 prep)
   - Finalize SQL definitions
   - Create migration scripts
   - Document query patterns

3. **Build SurrealDBStorage** (Phase 2)
   - Implement save/load operations
   - Sync command
   - Performance testing

4. **Integrate with TUI** (Phase 3)
   - Curation features
   - Real-time updates
   - Export workflows

---

## 🎯 **Success Criteria**

✅ **Phase 1 Complete When:**
- ConversationDAG parses JSONL sessions
- ASCII tree shows semantic structure
- TUI navigates with vim keys
- Orphans detected correctly

✅ **Phase 2 Complete When:**
- Sessions cached in SurrealDB
- Cache matches JSONL exactly
- Graph queries <100ms
- Sync command works reliably

✅ **Phase 3 Complete When:**
- Bookmarks saved to SurrealDB
- Notes/tags persist across sessions
- Curated view exportable
- "Live graph as you riff" vision achieved

