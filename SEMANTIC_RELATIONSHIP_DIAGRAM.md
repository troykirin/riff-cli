# Semantic Relationship Diagram: Riff-CLI Integration with Federation Architecture

**Purpose**: Visual mapping of how riff-cli Phase 6A/6B/6C integrates with SurrealDB, nabi-mcp, and federation coordination
**Format**: Multiple perspectives on the same semantic relationships

---

## 1. Component Stack Visualization

### Horizontal (Data Flow) View

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        FEDERATION KNOWLEDGE LAYER                           │
│                         (nabi-mcp / SurrealDB)                              │
└────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │
                    WebSocket Query Interface (search_nodes)
                                      │
        ┌─────────────┬──────────────┴──────────────┬──────────────┐
        │             │                              │              │
        ▼             ▼                              ▼              ▼
   ┌────────┐    ┌─────────┐                  ┌──────────┐    ┌────────┐
   │ riff   │    │  Other  │                  │ Vigil   │    │ Eternal│
   │ CLI    │    │  Agents │                  │ Monitor │    │Agents  │
   └────────┘    └─────────┘                  └──────────┘    └────────┘
        │
        │ (Creates Immutable Repair Events)
        │
        ▼
   ┌──────────────────┐
   │  memchain_mcp    │
   │  (Coordination)  │
   └──────────────────┘
```

### Vertical (Architecture) View

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: APPLICATION (Tools & Services)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐              ┌───────────────────┐      │
│  │   Riff-CLI     │              │  Other Tools      │      │
│  │  Phase 6A/B/C  │──────────────│  (future)         │      │
│  │  + Week 1 TUI  │              │                   │      │
│  └────────────────┘              └───────────────────┘      │
│         │                                                     │
│         │ Query / Create / Update                            │
│         ▼                                                     │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: KNOWLEDGE (Query Interface)                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│              ┌──────────────────┐                            │
│              │   nabi-mcp       │                            │
│              │  (MCP Server)    │                            │
│              │  WebSocket       │                            │
│              │  Interface       │                            │
│              └────────┬─────────┘                            │
│                       │ RPC Calls                            │
│                       ▼                                      │
│         ┌──────────────────────────┐                        │
│         │  memory.json (Fallback)  │                        │
│         │  (Syncthing-synced)      │                        │
│         └──────────────────────────┘                        │
│                       │                                      │
│                       │ JSON Operations                      │
│                       ▼                                      │
├─────────────────────────────────────────────────────────────┤
│ LAYER 1: STORAGE (Immutable Event Store)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│           ┌──────────────────────────┐                      │
│           │     SurrealDB            │                      │
│           │   (Canonical Store)      │                      │
│           │                          │                      │
│           │  namespace: memory       │                      │
│           │  database: nabi          │                      │
│           │  498 entities (✅)       │                      │
│           │  308 blocked (⏳)        │                      │
│           └──────────────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Riff-CLI Phase Architecture with Federation Integration

### Phase 6A: Repair Engine (Orphan Detection)

```
Session Input
    │
    ▼
┌─────────────────────────────────┐
│ Orphan Detection (Phase 6A)      │
│                                  │
│ 1. Query nabi-mcp:              │
│    - Find conversation records  │
│    - Check parent references    │
│    - Identify orphans           │
│                                  │
│ 2. Query SurrealDB:             │
│    - Immutable event log        │
│    - Conversation history       │
│    - Semantic relationships     │
│                                  │
│ 3. Suggest Parents:             │
│    - Rank by similarity         │
│    - Return top candidates      │
└─────────────────────────────────┘
    │
    ├─→ User Selection (TUI)
    │
    ▼
Parent Candidate List
```

### Phase 6B: Persistence Layer (Pluggable Backend)

```
Repair Operation
    │
    ▼
┌──────────────────────────────────┐
│ Abstracted Persistence Provider   │
│                                   │
│ Interface:                        │
│ - write_repair(event)            │
│ - read_repair(id)                │
│ - query_repairs(parent_id)       │
│                                   │
│ Implementations:                  │
│ 1. JSONL Backend                 │
│    ├─ Fast append-only           │
│    └─ Local file-based           │
│                                   │
│ 2. SurrealDB Backend             │
│    ├─ Immutable event log        │
│    └─ Relational queries         │
└──────────────────────────────────┘
    │
    ├─→ [Backend Selection]
    │   (environment var or config)
    │
    ├─→ JSONL: Fast local writes
    │
    └─→ SurrealDB: Federation sync
```

### Phase 6C: Federation Integration (Immutable Events)

```
Completed Repair
    │
    ▼
┌────────────────────────────────┐
│ Immutable Event Store          │
│                                 │
│ 1. Log to SurrealDB            │
│    event_type: "repair"        │
│    session_id: UUID            │
│    parent_id: UUID             │
│    timestamp: ISO8601          │
│    metadata: {...}             │
│                                 │
│ 2. Emit to memchain_mcp        │
│    event: "session:repaired"   │
│    tags: ["recovery",          │
│           "federation"]        │
│                                 │
│ 3. Federation Coordination     │
│    - Loki logging              │
│    - STOP protocol compliance  │
│    - Cross-agent notification  │
└────────────────────────────────┘
    │
    ├─→ SurrealDB (Storage)
    ├─→ memchain_mcp (Coordination)
    └─→ Loki (Monitoring)
```

### Week 1: TUI-First Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────┐
│ Interactive TUI (riff CLI)       │
│                                  │
│ Features:                        │
│ 1. Session search               │
│ 2. Interactive filtering        │
│ 3. Parent suggestion review     │
│ 4. One-click repair             │
│ 5. Repair history view          │
│                                  │
│ Backend Integration:            │
│ - Queries via nabi-mcp          │
│ - Repairs via Phase 6B          │
│ - Events logged via Phase 6C    │
└─────────────────────────────────┘
    │
    ├─→ Search Results
    ├─→ Suggestion Review
    ├─→ Repair Execution
    └─→ History Display
```

---

## 3. Information Flow: Session Recovery Workflow

### Complete End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER INITIATES RECOVERY                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  $ riff search "session query"                                      │
│         └──→ TUI launches (Week 1)                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. SEARCH & DISCOVER ORPHANS                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  riff-cli calls:                                                    │
│    mcp__nabi-mcp__search_nodes(query="user input")                 │
│         └──→ nabi-mcp queries SurrealDB                            │
│             - Returns matching conversations                       │
│             - Identifies orphans (no parent)                       │
│             - Formats for TUI display                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. DISPLAY RESULTS & DETECT ORPHANS (Phase 6A)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  TUI shows:                                                         │
│    [x] Session 1 (has parent) ✓                                    │
│    [ ] Orphan Session 2 (no parent) ⚠️                            │
│    [ ] Orphan Session 3 (no parent) ⚠️                            │
│                                                                      │
│  For orphans, Phase 6A suggests parents:                           │
│    "Session 2 might belong to: Parent A (95%), Parent B (87%)"    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. USER SELECTS & CONFIRMS REPAIR                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User clicks: "Repair orphan → Parent A"                           │
│         └──→ Repair operation created                              │
│             {                                                       │
│              "session_id": "UUID-2",                               │
│              "parent_id": "UUID-A",                                │
│              "reason": "user_selected",                            │
│              "timestamp": "ISO8601"                                │
│             }                                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. PERSIST REPAIR (Phase 6B)                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Abstracted Persistence Provider:                                   │
│                                                                      │
│  if BACKEND == "JSONL":                                             │
│    → Fast append to local .jsonl file                              │
│    → Synced via Syncthing                                          │
│                                                                      │
│  if BACKEND == "SURREALDB":                                        │
│    → INSERT into repairs table                                     │
│    → Immutable event log                                           │
│    → Queryable via nabi-mcp                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. LOG IMMUTABLE EVENT (Phase 6C)                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  riff-cli emits to memchain_mcp:                                    │
│                                                                      │
│  mcp__memchain__store(                                              │
│    key="event:session-repair:UUID-2",                              │
│    value={                                                          │
│      "type": "session:repaired",                                   │
│      "session_id": "UUID-2",                                       │
│      "parent_id": "UUID-A",                                        │
│      "phase": "6C",                                                │
│      "timestamp": "ISO8601",                                       │
│      "federation": true                                            │
│    }                                                                │
│  )                                                                  │
│                                                                      │
│  Federation effects:                                                │
│  - Loki event logged (monitoring)                                   │
│  - F-STOP protocol validated                                        │
│  - Cross-agent notification queued                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. FEDERATION PROPAGATION                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Syncthing updates:                                                 │
│  - JSONL repairs synced to other nodes                              │
│  - SurrealDB replicated to federation                               │
│                                                                      │
│  Loki monitoring:                                                   │
│  - Session recovery metrics recorded                                │
│  - Agent coordination logged                                        │
│                                                                      │
│  Other agents notified:                                             │
│  - igris (strategic oversight)                                      │
│  - beru (tactical coordination)                                     │
│  - synthesis agents (context aware)                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. COMPLETION & HISTORY                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  riff CLI shows:                                                    │
│  "✓ Session 2 repaired: linked to Parent A"                        │
│  "Repair logged: event:session-repair:UUID-2"                      │
│  "Federation notified: 3 agents updated"                            │
│                                                                      │
│  User can view:                                                     │
│  - Repair history (Week 1 TUI feature)                              │
│  - Orphan detection trends                                          │
│  - Parent suggestion accuracy metrics                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Federation Integration Matrix

### What Each Component Provides

| Component | Provides | Consumes | Integration Point |
|-----------|----------|----------|-------------------|
| **SurrealDB** | Immutable event store, relational queries | write_repair events | Phase 6C → memchain |
| **nabi-mcp** | search_nodes, open_nodes, create_entities | queries from riff-cli | Phase 6A → discovery |
| **riff-cli Phase 6A** | Orphan detection, parent suggestions | nabi-mcp queries, SurrealDB reads | Application → Knowledge |
| **riff-cli Phase 6B** | Persistence abstraction, backend choice | repair operations | Phase 6A → Phase 6C |
| **riff-cli Phase 6C** | Federation logging, immutable events | persistence layer writes | Phase 6B → coordination |
| **riff-cli Week 1** | Interactive TUI, user experience | all phases 6A/B/C | Application UI |
| **memchain_mcp** | Coordination events, federation logging | Phase 6C events | Federation notifications |

### Semantic Relationship Types

```
Phase 6A (Orphan Detection)
    ├─ QUERIES → nabi-mcp (search for orphans)
    ├─ READS → SurrealDB (conversation history)
    └─ SUGGESTS → Repair candidates

Phase 6B (Persistence)
    ├─ ABSTRACTS → JSONL backend (fast local)
    ├─ ABSTRACTS → SurrealDB backend (federation)
    └─ IMPLEMENTS → write_repair(), read_repair()

Phase 6C (Federation)
    ├─ LOGS → SurrealDB (immutable events)
    ├─ EMITS → memchain_mcp (coordination)
    ├─ PUBLISHES → Loki (monitoring)
    └─ NOTIFIES → Federation agents

Week 1 (TUI)
    ├─ CALLS → Phase 6A (orphan detection)
    ├─ CALLS → Phase 6B (persistence)
    ├─ DISPLAYS → Phase 6C (event history)
    └─ INTERACTS → User (feedback loop)
```

---

## 5. Integration with Broader Federation Architecture

### Position in AIO Pattern (Aura → Inference → Ops)

```
AURA (Schema-Driven):
  ~/.config/nabi/auras/architect.toml
      └─→ riff-cli configuration
          - venv location: ~/.nabi/venvs/riff-cli/
          - persistence backend: SurrealDB (default)
          - federation enabled: true

         ↓ Transform

INFERENCE (Semantic Layer):
  Phase 6A: Orphan detection + parent suggestions
      - Semantic similarity ranking
      - Conversation context analysis
      - Pattern recognition

         ↓ Activate

OPERATIONS (Execution Layer):
  Phase 6B/6C: Repair execution + federation logging
      - Immutable event store
      - Syncthing synchronization
      - Loki monitoring
      - Agent notification
```

### Position in STOP Protocol (Federation-aware Context Validation)

```
STOP = Semantic Threading Over Persistence

Riff-CLI Implementation:
├─ S (Semantic): Phase 6A orphan detection
├─ T (Threading): Parent-child relationship repair
├─ O (Over): nabi-mcp + SurrealDB
└─ P (Persistence): Phase 6B/6C immutable logging

F-STOP = Federation STOP
├─ Repair events → memchain_mcp coordination
├─ Validation → CLAUDE.md coherence checks
└─ Propagation → Syncthing + Loki
```

---

## 6. Data Model: Session Recovery Entity Relationships

### SurrealDB Schema (Implicit)

```
Session {
  id: UUID,
  parent_id: Optional[UUID],  // NULL = orphan
  created_at: DateTime,
  metadata: JSON,
  status: "active" | "orphaned" | "repaired"
}

Repair {
  id: UUID,
  session_id: UUID,           // Which session repaired
  parent_id: UUID,            // Which parent suggested
  reason: String,             // user_selected | auto_suggested
  timestamp: DateTime,
  confidence: Float,          // 0.0 to 1.0
  status: "pending" | "completed" | "failed"
}

ConversationDAG {
  id: UUID,
  parent_id: Optional[UUID],
  semantic_hash: String,
  created_at: DateTime,
  relationships: Relation[]
}
```

### nabi-mcp Entity Types (Knowledge Graph)

```
Entity Types:
├─ Conversation (root entity)
│   ├─ id: UUID
│   ├─ parent: Optional[Entity]
│   └─ observations: [recovery_metadata]
│
├─ Session (contains conversations)
│   ├─ id: UUID
│   ├─ status: orphaned | active | repaired
│   └─ repair_history: Repair[]
│
└─ Recovery Pattern (generic)
    ├─ name: "orphan_detection"
    ├─ phase: "6A"
    └─ observations: [pattern_details]
```

---

## 7. Success Indicators: How to Validate Integration

### Technical Validation

```bash
# 1. Can riff-cli find orphaned sessions?
riff search --filter="orphaned:true"
→ Should return list of sessions without parents

# 2. Can riff-cli suggest parents?
riff repair --session UUID-X --suggest
→ Should return ranked list of parent candidates

# 3. Are repairs logged immutably?
nabi docs manifest validate
→ Should find riff-cli repairs in SurrealDB audit trail

# 4. Are federation events emitted?
curl -s 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={job="riff-cli"}'
→ Should show repair event logs

# 5. Is Syncthing syncing repairs?
ls -la ~/.nabi/venvs/riff-cli/repairs/
→ Should show JSONL files synced to other nodes
```

### Semantic Validation

```bash
# 1. Are 6 recovery entities in knowledge graph?
mcp__nabi-mcp__search_nodes(query="recovery session orphan")
→ Should return 6+ entities

# 2. Are entities linked correctly?
mcp__nabi-mcp__open_nodes(names=["Claude Manager"])
→ Should show relationships to nabi-mcp, SurrealDB, memchain

# 3. Is documentation linked?
cat ~/Sync/docs/FEDERATED_MASTER_INDEX.md | grep -i "riff"
→ Should find riff-cli section

# 4. Are validation rules in place?
grep -r "riff-cli" ~/Sync/docs/architecture/COHERENCE_VALIDATION_FRAMEWORK.md
→ Should find repair validation rules
```

### Federation Validation

```bash
# 1. Can other agents discover recovery patterns?
riff | grep -E "federation|agent|coordination"
→ Should show federation integration

# 2. Is riff-cli in nabi-cli registry?
nabi exec riff
→ Should launch riff TUI

# 3. Are repair events visible to Vigil monitoring?
ssh rpi "curl -s http://localhost:3100/loki/api/v1/labels"
→ Should include job="riff-cli"
```

---

## Summary: Semantic Coherence Checklist

- [ ] Phase 6A/B/C docs exported to ~/Sync/docs/architecture/
- [ ] Recovery workflows documented in CLAUDE.md
- [ ] Integration bridge document created (~200 lines)
- [ ] Riff-cli section added to FEDERATED_MASTER_INDEX.md
- [ ] Recovery patterns added to COHERENCE_VALIDATION_FRAMEWORK.md
- [ ] 6 recovery entities created in nabi-mcp (post-SurrealDB fix)
- [ ] All cross-links validated (no broken references)
- [ ] Federation coordination tested (memchain events)
- [ ] Syncthing synchronization verified
- [ ] Agent discoverability confirmed (via riff command)

---

**Diagram Generated**: 2025-10-26 23:52 UTC
**For**: ALIGN Semantic Custodian validation report
**Next Action**: Implement Phase 1 (Documentation Export)

