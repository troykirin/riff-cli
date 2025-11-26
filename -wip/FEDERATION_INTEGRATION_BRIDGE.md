# Riff-CLI Federation Integration Bridge

**Purpose**: Practical guide for integrating riff-cli Week 1 + recovery work into federation documentation
**Status**: Implementation-ready (ALIGN validated)
**Timeline**: ~2 hours for Phases 1-2, pending SurrealDB for Phase 3

---

## Quick Start: What Changed?

Your Week 1 + recovery work is **complete and functionally integrated** but **not yet indexed in federation documentation**. This bridge document provides a step-by-step path to make it visible to the federation.

### Before Integration
```
riff-cli (local)
├─ Phase 6A/B/C code ✅
├─ Week 1 TUI ✅
├─ Recovery entities (6) ⚠️ orphaned from knowledge graph
├─ Phase documentation (in git commits) ✓
└─ NOT in federation indices ❌
```

### After Integration
```
riff-cli (federated)
├─ Phase 6A/B/C code ✅
├─ Week 1 TUI ✅
├─ Recovery entities (6) ✅ in nabi-mcp
├─ Phase documentation ✅ in ~/Sync/docs/
├─ Cross-linked to CLAUDE.md ✅
├─ Indexed in FEDERATED_MASTER_INDEX.md ✅
├─ Validation rules in place ✅
└─ Visible to federation agents ✅
```

---

## Phase 1: Documentation Export (30 minutes)

### Step 1.1: Extract Phase 6A Documentation
**File to Create**: `~/Sync/docs/architecture/RIFF_CLI_PHASE_6A_REPAIR_ENGINE.md`

**Source**: Commits `2e8ee71` (Phase 6A complete) and git log entries
**Content Checklist**:
- [ ] What is Phase 6A? (Orphan detection + parent suggestion)
- [ ] How does it query nabi-mcp?
- [ ] How does it read from SurrealDB?
- [ ] Parent suggestion algorithm (semantic similarity)
- [ ] TUI integration (Week 1)
- [ ] Configuration options
- [ ] Example repair workflow

**Template Structure**:
```markdown
# Phase 6A: Repair Engine - Orphan Detection & Parent Suggestion

## Overview
Phase 6A implements the core recovery engine...

## Architecture
### Orphan Detection
- Query nabi-mcp for conversations without parent_id
- Check SurrealDB immutable event log
- Return orphan candidates to TUI

### Parent Suggestion
- Semantic similarity ranking algorithm
- Score calculation: (semantic_match % metadata_match %)
- Return top-5 candidates

## Integration Points
- nabi-mcp: search_nodes(query)
- SurrealDB: immutable event log queries
- Week 1 TUI: display results and manage user selection

## Code References
- Entry point: src/riff_cli/recovery/orphan_detector.py
- Ranking algorithm: src/riff_cli/recovery/parent_suggester.py
- TUI integration: src/riff_cli/tui/recovery_view.nu

## Usage Example
```bash
riff repair --session UUID-X --suggest
# Returns ranked parent candidates
```

## Validation Rules
- No false positives in orphan detection
- Parent suggestion accuracy >= 85%
- Response time < 500ms
```

**Time**: 15 minutes

### Step 1.2: Extract Phase 6B Documentation
**File to Create**: `~/Sync/docs/architecture/RIFF_CLI_PHASE_6B_PERSISTENCE.md`

**Source**: Commits `c26ed8a` (immutable event store) and `1c96cc6` (persistence provider)
**Content Checklist**:
- [ ] Abstracted persistence provider design
- [ ] JSONL backend implementation
- [ ] SurrealDB backend implementation
- [ ] Configuration (backend selection)
- [ ] Data model (Repair schema)
- [ ] Fallback handling

**Template Structure**:
```markdown
# Phase 6B: Persistence Layer - Pluggable Backend Architecture

## Overview
Phase 6B abstracts the persistence layer to support multiple backends...

## Architecture

### Abstracted Interface
```python
class PersistenceProvider:
    def write_repair(event: RepairEvent) -> str: ...
    def read_repair(id: str) -> RepairEvent: ...
    def query_repairs(parent_id: str) -> List[RepairEvent]: ...
```

### JSONL Backend
- Fast local writes (append-only)
- Syncthing synchronization
- Use case: Development, rapid prototyping

### SurrealDB Backend
- Immutable event log
- Relational queries
- Use case: Production, federation coordination

## Configuration
```bash
export RIFF_PERSISTENCE_BACKEND=surrealdb  # or jsonl
export SURREALDB_URL=ws://localhost:8284/rpc
```

## Data Model
```sql
CREATE TABLE repairs (
  id: string,
  session_id: string,
  parent_id: string,
  reason: string,
  timestamp: datetime,
  metadata: object
);
```

## Integration with Phase 6C
- Phase 6C reads repair events from this layer
- Events logged immutably to federation
```

**Time**: 15 minutes

### Step 1.3: Extract Phase 6C Documentation
**File to Create**: `~/Sync/docs/architecture/RIFF_CLI_PHASE_6C_FEDERATION.md`

**Source**: Commits `ec605c4` and `6849d49` (Phase 6C design)
**Content Checklist**:
- [ ] Immutable event store pattern
- [ ] Federation integration architecture
- [ ] memchain_mcp event logging
- [ ] Loki monitoring integration
- [ ] STOP protocol compliance
- [ ] Implementation status (design stage)

**Template Structure**:
```markdown
# Phase 6C: Federation Integration - Immutable Event Store

## Overview
Phase 6C integrates riff-cli recovery workflows into the broader federation...

## Architecture

### Immutable Event Store
- All repairs logged to SurrealDB as append-only events
- Provides complete audit trail
- Enables federation-wide repair visibility

### Federation Integration
```python
# After repair completion:
mcp__memchain__store(
    key=f"event:session-repair:{session_id}",
    value={
        "type": "session:repaired",
        "session_id": session_id,
        "parent_id": parent_id,
        "phase": "6C",
        "timestamp": datetime.now(),
        "federation": true
    }
)
```

### Loki Monitoring
- Repair events logged with structured fields
- Query: {job="riff-cli"} session_repaired=true
- Metrics: repair success rate, orphan detection accuracy

### STOP Protocol Compliance
- S (Semantic): Phase 6A orphan detection
- T (Threading): Parent-child relationship repair
- O (Over): nabi-mcp + SurrealDB
- P (Persistence): Immutable event log

## Status: Design Complete (Implementation Pending)
- Architecture documented
- Integration points identified
- Ready for implementation in Week 2
```

**Time**: 10 minutes

### After Step 1.3
Commit the three phase docs:
```bash
cd ~/nabia/tools/riff-cli
git add FEDERATION_INTEGRATION_BRIDGE.md \
        ALIGN_COHERENCE_VALIDATION_REPORT.md \
        SEMANTIC_RELATIONSHIP_DIAGRAM.md
git commit -m "docs: Add federation integration analysis and bridge"
```

---

## Phase 2: Federation Documentation Updates (45 minutes)

### Step 2.1: Update CLAUDE.md Memory Architecture Section
**File**: `/Users/tryk/.claude/CLAUDE.md`
**Location**: Lines 25-48 (Knowledge section)
**Action**: Add subsection for recovery workflows

**Original** (lines 25-48):
```yaml
Knowledge (task-scoped, graph-based):
  MCP: nabi-mcp
  Purpose: Cross-agent collaboration context, knowledge graph queries
  Backend: SurrealDB (✅ Active since 2025-10-27)
    - URL: ws://localhost:8284/rpc
    - Entities: 498 (migrated from memory.json)
```

**Updated** (lines 25-60):
```yaml
Knowledge (task-scoped, graph-based):
  MCP: nabi-mcp
  Purpose: Cross-agent collaboration context, knowledge graph queries
  Backend: SurrealDB (✅ Active since 2025-10-27)
    - URL: ws://localhost:8284/rpc
    - Entities: 498 (migrated from memory.json)
    - Schema: ~/Sync/docs/architecture/SURREALDB_MEMORY_SCHEMA.surql

  Recovery Workflows (riff-cli):
    Purpose: Session orphan detection and repair via SurrealDB + nabi-mcp
    Components:
      - Phase 6A: Orphan detection + parent suggestion (semantic ranking)
      - Phase 6B: Pluggable persistence (JSONL/SurrealDB abstraction)
      - Phase 6C: Immutable event store + federation logging (design stage)
    Integration: Logs repairs via memchain_mcp coordination layer
    Status: ✅ Phase 6A/6B complete, ⏳ Phase 6C in design
    Entry Points:
      - TUI: ~/.nabi/venvs/riff-cli/bin/riff (interactive session search)
      - Command: riff repair --session UUID --suggest (parent suggestions)
      - History: riff history --filters (repair audit trail)
    Documentation:
      - ~/Sync/docs/architecture/RIFF_CLI_PHASE_6A_REPAIR_ENGINE.md
      - ~/Sync/docs/architecture/RIFF_CLI_PHASE_6B_PERSISTENCE.md
      - ~/Sync/docs/architecture/RIFF_CLI_PHASE_6C_FEDERATION.md
```

**Time**: 10 minutes

### Step 2.2: Add Riff-CLI to COHERENCE_VALIDATION_FRAMEWORK.md
**File**: `~/Sync/docs/architecture/COHERENCE_VALIDATION_FRAMEWORK.md`
**Action**: Add riff-cli validation rules section

**Insert After** (existing "Architectural Coherence" section):
```markdown
## Riff-CLI Recovery Workflow Validation

### Orphan Detection Validation
- **Rule**: No orphaned sessions without detected parent candidates
  - Verification: riff repair --session UUID --suggest (must return candidates)
  - Threshold: 100% orphan detection accuracy
  - Consequence: CRITICAL drift if orphans go undetected

- **Rule**: Parent suggestion accuracy >= 85%
  - Verification: Compare suggested parent with actual parent in audit trail
  - Threshold: 85% match rate across all repairs
  - Consequence: HIGH drift if accuracy degrades below threshold

### Persistence Layer Validation
- **Rule**: JSONL and SurrealDB backends stay synchronized
  - Verification: Repair count(JSONL) == Repair count(SurrealDB)
  - Threshold: 100% consistency
  - Consequence: CRITICAL if backends diverge

- **Rule**: All repairs logged immutably
  - Verification: SELECT COUNT(*) FROM repairs; (no deletes)
  - Threshold: Append-only operations only
  - Consequence: CRITICAL if repairs are modified/deleted

### Federation Integration Validation
- **Rule**: Completed repairs emit memchain events
  - Verification: memchain list --prefix="event:session-repair"
  - Threshold: 100% event emission
  - Consequence: HIGH if federation notifications fail

- **Rule**: Loki monitoring captures repair events
  - Verification: curl -s 'http://localhost:3100/loki/api/v1/query' \
    --data-urlencode 'query={job="riff-cli"}'
  - Threshold: All repair events logged
  - Consequence: MEDIUM if monitoring gaps exist

### Integration Point Validation
- **Rule**: riff-cli commands work via `nabi exec riff`
  - Verification: nabi exec riff --help (no errors)
  - Threshold: All commands functional
  - Consequence: HIGH if nabi-cli integration breaks

- **Rule**: Recovery entities visible in nabi-mcp
  - Verification: mcp__nabi-mcp__search_nodes(query="recovery session")
  - Threshold: >= 6 recovery entities found
  - Consequence: MEDIUM if knowledge graph incomplete
```

**Time**: 15 minutes

### Step 2.3: Add Riff-CLI Section to FEDERATED_MASTER_INDEX.md
**File**: `~/Sync/docs/FEDERATED_MASTER_INDEX.md`
**Action**: Insert riff-cli section in appropriate category

**Insert Under** (new "Tools & Utilities" section or appropriate location):
```markdown
### 🔧 Riff-CLI: Session Recovery & Repair Workflows

Riff-CLI provides federation-native session recovery using SurrealDB, nabi-mcp, and memchain coordination.

#### Quick Navigation
- **[Phase 6A: Repair Engine](architecture/RIFF_CLI_PHASE_6A_REPAIR_ENGINE.md)** - Orphan detection + parent suggestion
- **[Phase 6B: Persistence](architecture/RIFF_CLI_PHASE_6B_PERSISTENCE.md)** - Pluggable JSONL/SurrealDB backends
- **[Phase 6C: Federation](architecture/RIFF_CLI_PHASE_6C_FEDERATION.md)** - Immutable event store + federation logging
- **[Integration Bridge](setup-guides/riff-cli-federation-integration-bridge.md)** - Integration implementation guide
- **[Setup Guide](setup-guides/riff-claude-manager-setup.md)** - Installation and configuration

#### Quick Start
```bash
# Launch interactive session search
riff

# Search for specific sessions
riff search "conversation about X"

# Detect and repair orphaned sessions
riff repair --session UUID-X --suggest
```

#### Architecture
- **Knowledge Layer**: nabi-mcp queries SurrealDB for orphaned sessions
- **Application Layer**: Phase 6A/B/C orchestrates detection → persistence → federation
- **Coordination Layer**: memchain_mcp logs repairs as immutable federation events
- **Monitoring**: Loki tracks session recovery metrics

#### Status
- ✅ Phase 6A: Orphan detection + parent suggestion (complete)
- ✅ Phase 6B: Pluggable persistence layer (complete)
- ⏳ Phase 6C: Federation integration (design phase)
- ✅ Week 1: TUI-first architecture (complete)

#### Integration with Memory Architecture
Riff-CLI recovery workflows integrate with the three-tier memory system:
1. **Storage Tier (SurrealDB)**: Immutable event log of repairs
2. **Query Tier (nabi-mcp)**: Orphan detection via search_nodes()
3. **Application Tier (riff-cli)**: User-facing recovery UX
```

**Time**: 15 minutes

### Step 2.4: Update MASTER_INDEX.md (Local Index)
**File**: `~/Sync/docs/MASTER_INDEX.md`
**Action**: Add reference to riff-cli documentation

**Insert Under** (appropriate tools/setup section):
```markdown
- **[Riff CLI & Claude Manager Setup](setup-guides/riff-claude-manager-setup.md)** - Installation, configuration, and aliases
```

**Time**: 5 minutes

---

## Phase 3: Knowledge Graph Migration (30 minutes, BLOCKED)

### Current Status
**Blocker**: SurrealDB migration has 308 entity constraint violations
**Prerequisite**: Resolve SurrealDB unique constraints (separate task)
**Action**: Cannot proceed until SurrealDB is fixed

### What Happens in Phase 3
Once SurrealDB is fixed:

**Step 3.1: Create Recovery Entities in nabi-mcp**
```python
mcp__nabi-mcp__create_entities([
  {
    name: "Claude Manager",
    entityType: "Tool",
    observations: [
      "Session management tool for Claude Desktop",
      "Handles UUID-based session context preservation",
      "Integrates with riff-cli for session recovery workflows",
      "Reverse-engineered UUID decoupling mechanism"
    ]
  },
  {
    name: "NabiOS Substrate",
    entityType: "Architecture",
    observations: [
      "Cognitive substrate enabling federation-wide session recovery",
      "Foundation for session portability across platforms",
      "Supports both JSONL and SurrealDB persistence backends"
    ]
  },
  {
    name: "Session Recovery Path",
    entityType: "Pattern",
    observations: [
      "UUID-based recovery pathway for orphaned conversations",
      "Enables session discovery via nabi-mcp semantic search",
      "Parent suggestion via semantic similarity ranking"
    ]
  },
  {
    name: "Repair Workflow Engine",
    entityType: "Component",
    observations: [
      "Orchestrates Phase 6A/6B/6C repair process",
      "Integrates SurrealDB queries with user-facing TUI",
      "Logs immutable repair events for federation"
    ]
  },
  {
    name: "Federation Coordination Protocol",
    entityType: "Protocol",
    observations: [
      "memchain_mcp integration for repair event logging",
      "STOP protocol compliance for recovery workflows",
      "Cross-agent notification on session repairs"
    ]
  },
  {
    name: "Session Portability Pattern",
    entityType: "Pattern",
    observations: [
      "Refactoring-safe design for session recovery",
      "Emergent systems engineering principles",
      "Enables seamless session transfer across platforms"
    ]
  }
])
```

**Time**: 30 minutes (pending SurrealDB)

**Step 3.2: Create Entity Relationships**
```python
mcp__nabi-mcp__create_relations([
  {"from": "Repair Workflow Engine", "to": "SurrealDB", "relationType": "queries_immutable_log"},
  {"from": "Repair Workflow Engine", "to": "nabi-mcp", "relationType": "discovers_orphans_via"},
  {"from": "Session Recovery Path", "to": "Claude Manager", "relationType": "uses_context_from"},
  {"from": "Federation Coordination Protocol", "to": "memchain_mcp", "relationType": "emits_events_to"},
  # ... (establish full relationship graph)
])
```

**Time**: 15 minutes (pending SurrealDB)

---

## Phase 4: Validation & Hardening (30 minutes)

### Step 4.1: Validate Documentation Links
```bash
# Check all cross-references work
cd ~/Sync/docs
for file in architecture/RIFF_CLI_*.md; do
  echo "Checking $file..."
  grep -o '\[.*\](.*\.md)' "$file" | while read link; do
    target=$(echo "$link" | sed 's/.*(\(.*\)).*/\1/')
    if [ ! -f "$target" ]; then
      echo "  ❌ Broken link: $target"
    fi
  done
done
```

**Expected Output**: No broken links

**Time**: 10 minutes

### Step 4.2: Verify Coherence Framework Integration
```bash
# Check riff-cli validation rules are in place
grep -i "riff-cli" ~/Sync/docs/architecture/COHERENCE_VALIDATION_FRAMEWORK.md
# Should return multiple validation rules

# Verify entities are searchable
mcp__nabi-mcp__search_nodes(query="riff-cli recovery")
# Should return >= 6 entities
```

**Expected Output**: Validation rules found, entities discoverable

**Time**: 10 minutes

### Step 4.3: Test Federation Integration
```bash
# Verify riff-cli available via nabi-cli
nabi exec riff --help
# Should launch interactive help

# Test memchain event logging (post-Phase 6C)
mcp__memchain__list(prefix="event:session-repair")
# Should list repair events
```

**Expected Output**: riff-cli accessible, events logged

**Time**: 10 minutes

---

## Implementation Checklist

### Phase 1: Documentation Export
- [ ] Extract Phase 6A documentation
- [ ] Extract Phase 6B documentation
- [ ] Extract Phase 6C documentation
- [ ] Create FEDERATION_INTEGRATION_BRIDGE.md (this file)
- [ ] Commit with message: "docs: Add riff-cli phase documentation and federation bridge"

### Phase 2: Federation Integration
- [ ] Update CLAUDE.md (Memory Architecture section)
- [ ] Update COHERENCE_VALIDATION_FRAMEWORK.md (add riff-cli rules)
- [ ] Update FEDERATED_MASTER_INDEX.md (add riff-cli section)
- [ ] Update MASTER_INDEX.md (add setup guide reference)
- [ ] Verify all files committed

### Phase 3: Knowledge Graph Migration (PENDING SurrealDB)
- [ ] Resolve SurrealDB unique constraints
- [ ] Create 6 recovery entities in nabi-mcp
- [ ] Establish entity relationships
- [ ] Verify entities are searchable

### Phase 4: Validation
- [ ] Run link validation checks
- [ ] Verify coherence framework integration
- [ ] Test federation integration (nabi exec riff)
- [ ] Confirm documentation passes `nabi docs manifest validate`
- [ ] Document completion in COMPLETION_REPORT.md

---

## Success Criteria

**Documentation Integration Complete When**:
1. ✅ All cross-links working (no broken references)
2. ✅ Riff-cli indexed in FEDERATED_MASTER_INDEX.md
3. ✅ Recovery workflows documented in CLAUDE.md
4. ✅ Validation rules in COHERENCE_VALIDATION_FRAMEWORK.md
5. ✅ Phase 6A/B/C documentation exported to ~/Sync/docs/
6. ✅ 6 recovery entities in nabi-mcp (post-SurrealDB fix)
7. ✅ All files committed with descriptive messages
8. ✅ No drift detected in manifest validation

**Federation Visibility Complete When**:
1. ✅ Federation agents can discover riff-cli via indices
2. ✅ Recovery workflows visible to Vigil monitoring
3. ✅ memchain events logged for all repairs
4. ✅ Loki metrics tracking session recovery
5. ✅ Syncthing syncing repair events to other nodes

---

## Next Steps After Integration

1. **Implement Phase 6C**: Federation integration (event logging, memchain coordination)
2. **Enhanced Monitoring**: Add Vigil dashboard for session recovery metrics
3. **Repair Suggestions**: Improve semantic similarity algorithm for parent ranking
4. **Cleanup Pipeline**: Implement automated orphan session cleanup workflow
5. **Cross-Platform Testing**: Validate recovery across macOS, WSL, RPi

---

## Troubleshooting

### Issue: SurrealDB Migration Blocked
**Symptom**: Cannot migrate recovery entities to nabi-mcp
**Cause**: 308 entity unique constraint violations in SurrealDB
**Resolution**:
1. Backup current state: `cp ~/Sync/memory/memory.json ~/backups/memory-$(date +%s).json`
2. Debug constraints: Query SurrealDB for duplicate entity names
3. Resolve conflicts: Merge/rename duplicates
4. Re-run migration: `nabi init --aura architect --reset-memory`

### Issue: Broken Links in Documentation
**Symptom**: `nabi docs manifest validate` fails
**Cause**: File references outdated after moving to ~/Sync/docs/
**Resolution**: Run link checker, update all references

### Issue: Recovery Entities Not Searchable
**Symptom**: `mcp__nabi-mcp__search_nodes()` returns empty
**Cause**: SurrealDB fallback not finding entities in memory.json
**Resolution**: Verify SurrealDB is running: `curl ws://localhost:8284/rpc`

---

**Bridge Document Generated**: 2025-10-26 23:55 UTC
**Purpose**: Practical implementation guide for federation integration
**Next Action**: Start Phase 1 (Documentation Export)

