# Phase 6C: Federation Integration - Connect riff-cli to memchain SurrealDB via MCP

## Executive Summary

**Objective**: Integrate riff-cli repair workflows into the federation infrastructure, leveraging memchain's SurrealDB instance through MCP coordination servers instead of direct HTTP/WebSocket connections.

**Alignment**:
- ✅ Architectural continuity (no silos)
- ✅ Leverages existing infrastructure (memchain, SurrealDB, MCP)
- ✅ Uses federation authentication (OAuth/Hydra)
- ✅ WebSocket coordination via federation message bus
- ✅ Low latency, low maintenance, high reliability
- ✅ Fits NABI protocol governance model
- ✅ Cross-platform: iOS bridge, Nuxt, React, etc.

---

## Architecture Diagram: Federation Integration

```
┌────────────────────────────────────────────────────────────────────┐
│                        riff-cli (macOS/WSL/RPi)                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  ConversationGraphNavigator (TUI)                            │ │
│  │  ┌──────────────────────────────────────────────────────────┤ │
│  │  │  RepairManager (Backend-Agnostic)                        │ │
│  │  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │  │  FederationRepairProvider (NEW Phase 6C)          │ │ │
│  │  │  │  ├─ Coordination: mcp__memchain__store()         │ │ │
│  │  │  │  ├─ Query: mcp__memchain__retrieve()             │ │ │
│  │  │  │  └─ Events: Loki via federation              │ │ │
│  │  │  └────────────────────────────────────────────────────┘ │ │
│  │  └──────────────────────────────────────────────────────────┘ │
│  └────────────────┬───────────────────────────────────────────────┘ │
└───────────────────┼──────────────────────────────────────────────────┘
                    │
        ┌───────────┴──────────────┐
        │  Federation Message Bus  │
        │  (MCP Coordination)      │
        │  ┌──────────────────────┐│
        │  │ memchain_mcp server  ││
        │  │ (federation hub)     ││
        │  └──────┬───────────────┘│
        └─────────┼────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐  ┌────▼────┐  ┌────▼────┐
│ Loki  │  │SurrealDB│  │ Hydra   │
│Logs   │  │repairs_ │  │(OAuth)  │
│Events │  │events   │  │         │
└───────┘  └─────────┘  └────────┘
           ws://100.97.105.80:8000/rpc
           (Raspberry Pi Coordination Server)

Cross-Platform Access:
┌──────────────────────────────────────────────────────┐
│  iOS Bridge ◄──┐                          ┌─► React  │
│  Nuxt App  ◄───┼─ Federation Auth (Hydra)┤          │
│  Web UI    ◄───┼─ WebSocket Gateway      ├─► Vue    │
│  CLI       ◄───┘                          └─► REST   │
└──────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap: Phase 6C

### Phase 6C.1: Foundation - FederationRepairProvider (Week 1)

**Goal**: Create FederationRepairProvider that coordinates with memchain via MCP

**Tasks**:

1. **Create FederationRepairProvider class** (NEW file)
   ```
   src/riff/surrealdb/federation_provider.py
   ```

   Extends PersistenceProvider:
   ```python
   class FederationRepairProvider(PersistenceProvider):
       """
       Repair persistence via federation MCP coordination.

       Coordinates with memchain SurrealDB through:
       - mcp__memchain__store(): Write repair events
       - mcp__memchain__retrieve(): Query repair history
       - Loki: Event logging via federation
       """

       def __init__(self, federation_client=None, operator="riff-cli"):
           self.mcp_client = federation_client or create_federation_client()
           self.operator = operator

       def create_backup(self, session_id: str, source_path: Path) -> Path:
           """Store session snapshot in federation."""
           event = {
               "type": "repair:backup",
               "session_id": session_id,
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "operator": self.operator,
           }
           event_id = self.mcp_client.store(key=f"backup:{session_id}:{event['timestamp']}", value=event)
           return Path(f"federation://backup/{event_id}")

       def apply_repair(self, target_path: Path, repair_op: EngineRepairOperation) -> bool:
           """Log immutable repair event in federation SurrealDB."""
           event = {
               "type": "repair:event",
               "message_id": repair_op.message_id,
               "old_parent_uuid": repair_op.original_parent_uuid,
               "new_parent_uuid": repair_op.suggested_parent_uuid,
               "reason": repair_op.reason,
               "similarity_score": repair_op.similarity_score,
               "operator": self.operator,
               "timestamp": datetime.now(timezone.utc).isoformat(),
           }

           # Store in federation (transactional via MCP)
           event_id = self.mcp_client.store(
               key=f"repair:{repair_op.message_id}:{event['timestamp']}",
               value=event
           )

           # Log to Loki
           self._log_to_loki(event)

           return event_id is not None

       def show_undo_history(self, session_id: str) -> List[RepairSnapshot]:
           """Query repair history from federation."""
           # Query memchain for all repairs for this session
           repairs = self.mcp_client.retrieve(
               query=f"repair:*:{session_id}",  # Pattern match
               limit=100
           )

           # Convert to RepairSnapshot objects
           return [self._to_snapshot(r) for r in repairs]
   ```

2. **Create federation_client module** (NEW file)
   ```
   src/riff/federation/client.py
   ```

   Wrapper around MCP coordination:
   ```python
   class FederationClient:
       """MCP coordination client for federation operations."""

       def __init__(self, namespace="riff", database="repairs"):
           self.namespace = namespace
           self.database = database
           self._setup_mcp_connection()

       def store(self, key: str, value: dict) -> Optional[str]:
           """Store repair event in federation."""
           # Use memchain_mcp server via federation message bus
           response = mcp__memchain__store(
               namespace=self.namespace,
               database=self.database,
               key=key,
               value=value,
               immutable=True  # Append-only
           )
           return response.get("event_id")

       def retrieve(self, query: str, limit: int = 100) -> List[dict]:
           """Query repair history from federation."""
           response = mcp__memchain__retrieve(
               namespace=self.namespace,
               database=self.database,
               query=query,
               limit=limit
           )
           return response.get("results", [])
   ```

3. **Update TUI to use FederationRepairProvider**
   ```
   src/riff/tui/graph_navigator.py

   Modify _create_persistence_provider():
   - Check for FEDERATION_MODE env var
   - If true, create FederationRepairProvider
   - Otherwise fallback to SurrealDB/JSONL chain
   ```

4. **Add federation authentication**
   ```
   src/riff/federation/auth.py

   - Detect OAuth/Hydra credentials
   - Use federation auth context
   - Share auth token with memchain_mcp
   ```

**Deliverables**:
- FederationRepairProvider class (200 lines)
- federation_client module (150 lines)
- TUI integration (30 lines modified)
- Authentication handler (100 lines)
- Total: ~480 lines new code

**Testing**:
```
tests/test_federation_provider.py (250 lines)
- Mock MCP coordination
- Repair event storage
- History retrieval
- Authentication tests
```

---

### Phase 6C.2: Event Coordination (Week 2)

**Goal**: Set up bi-directional event coordination between riff-cli and memchain

**Tasks**:

1. **Define repair event schema in federation**
   ```
   src/riff/federation/schemas.py

   RepairEventSchema:
   - event_id: UUID
   - session_id: str
   - message_id: str
   - old_parent_uuid: Optional[str]
   - new_parent_uuid: str
   - reason: str
   - operator: str (source: "riff-cli", "chat", "agent")
   - timestamp: ISO8601
   - similarity_score: float
   - validation_passed: bool
   - federation_node_id: str (which riff instance)
   - correlation_id: str (for request tracing)
   ```

2. **Create federation message publishers**
   ```
   src/riff/federation/events.py

   - publish_repair_event(event) -> bool
   - publish_undo_event(event_id) -> bool
   - subscribe_to_repairs(session_id, callback) -> listener

   Uses Loki for persistence:
   - job: "riff-cli"
   - labels: {session_id, operator, node_id}
   ```

3. **Add Loki integration**
   ```
   src/riff/federation/loki_client.py

   - log_repair_event(event) -> str (log_id)
   - query_repair_history(session_id) -> List[LogEntry]
   - set_labels(correlation_id, session_id, operator)
   ```

4. **Implement event callbacks**
   ```
   TUI repair workflow:
   1. User presses 'r' → create_repair_preview()
   2. Publish: repair:preview event (correlation_id)
   3. User confirms → apply_repair()
   4. Publish: repair:applied event (immutable)
   5. Loki logs both (with correlation_id for tracing)
   6. Other riff instances notified via message bus
   ```

**Deliverables**:
- Event schemas (80 lines)
- Message publishers (120 lines)
- Loki integration (150 lines)
- Event callbacks (100 lines)
- Total: ~450 lines

**Testing**:
```
tests/federation/test_event_coordination.py
- Event schema validation
- Publisher callbacks
- Loki logging verification
- Cross-node event propagation (mock)
```

---

### Phase 6C.3: Cross-Node Synchronization (Week 3)

**Goal**: Enable repair coordination across multiple riff instances

**Tasks**:

1. **Implement repair conflict detection**
   ```
   src/riff/federation/conflict_detection.py

   Detect when:
   - Same message repaired by multiple operators simultaneously
   - Conflicting parent assignments
   - Cascading repairs across instances

   Resolution strategies:
   - Last-write-wins (with operator audit)
   - Consensus voting (for federation)
   - Merge repair events
   ```

2. **Add distributed repair coordination**
   ```
   src/riff/federation/distributed_repair.py

   CoordinatedRepair:
   - Claim repair operation (federation-wide lock)
   - Perform repair locally
   - Publish immutable event to federation
   - Release lock
   - Notify other instances
   ```

3. **Implement repair deduplication**
   ```
   - Hash-based deduplication
   - Content-addressable storage
   - Detect idempotent repairs
   - Prevent duplicate events
   ```

**Deliverables**:
- Conflict detection (180 lines)
- Distributed coordination (200 lines)
- Deduplication logic (120 lines)
- Total: ~500 lines

**Testing**:
```
tests/federation/test_distributed_repair.py
- Concurrent repair scenarios
- Conflict detection
- Resolution strategies
- Idempotency verification
```

---

### Phase 6C.4: CLI & Configuration (Week 4)

**Goal**: Integrate federation mode into riff-cli

**Tasks**:

1. **Add CLI flags**
   ```
   riff graph <session> \
     --federation-mode \
     --federation-url ws://100.97.105.80:8000/rpc \
     --federation-auth-token $FEDERATION_TOKEN \
     --federation-namespace riff \
     --federation-database repairs
   ```

2. **Create federation configuration**
   ```
   ~/.config/nabi/riff-federation.yaml

   federation:
     enabled: true
     mode: "memchain"  # memchain | surrealdb | hybrid
     url: "ws://100.97.105.80:8000/rpc"
     auth:
       type: "oauth"  # oauth | token | mcp
       hydra_url: "https://hydra.nabi"
       client_id: "${HYDRA_CLIENT_ID}"
       client_secret: "${HYDRA_CLIENT_SECRET}"
     coordination:
       namespace: "riff"
       database: "repairs"
       immutable: true
     loki:
       enabled: true
       url: "http://100.97.105.80:3100"
       job: "riff-cli"
   ```

3. **Add configuration loader**
   ```
   src/riff/federation/config.py

   - Load from ~/.config/nabi/riff-federation.yaml
   - Environment variable overrides
   - Validate federation connectivity
   - Auth token refresh
   ```

4. **Update cmd_graph to support federation**
   ```
   src/riff/cli.py

   Added args:
   - --federation-mode
   - --federation-url
   - --federation-auth-token
   ```

**Deliverables**:
- CLI integration (60 lines)
- Configuration loader (150 lines)
- Config schema validation (80 lines)
- Total: ~290 lines

---

### Phase 6C.5: Integration Testing & Documentation (Week 5)

**Goal**: Comprehensive testing and documentation

**Tasks**:

1. **End-to-end integration tests**
   ```
   tests/federation/test_e2e_repair_workflow.py

   Scenarios:
   - Repair workflow via federation
   - Multi-instance coordination
   - Conflict resolution
   - Event persistence to SurrealDB
   - Loki log verification
   ```

2. **Performance & resilience tests**
   ```
   tests/federation/test_federation_resilience.py

   - MCP connection failure → fallback
   - Loki unavailable → queue events
   - SurrealDB connection issues → retry
   - Partial network partitions
   ```

3. **Documentation**
   ```
   docs/PHASE_6C_FEDERATION_INTEGRATION.md
   - Architecture overview
   - Configuration guide
   - Operation procedures
   - Troubleshooting guide

   docs/FEDERATION_REPAIR_WORKFLOW.md
   - User guide for federation mode
   - Multi-instance coordination examples
   - Conflict resolution scenarios
   ```

**Deliverables**:
- Integration tests (400 lines)
- Resilience tests (300 lines)
- Documentation (1500 lines)
- Total: ~2,200 lines

---

## Implementation Timeline

```
Week 1: Foundation
  ├─ FederationRepairProvider (200 lines)
  ├─ Federation client module (150 lines)
  ├─ Auth handler (100 lines)
  └─ Unit tests (250 lines)
  Total: 700 lines

Week 2: Event Coordination
  ├─ Event schemas (80 lines)
  ├─ Message publishers (120 lines)
  ├─ Loki integration (150 lines)
  ├─ Event callbacks (100 lines)
  └─ Tests (300 lines)
  Total: 750 lines

Week 3: Cross-Node Sync
  ├─ Conflict detection (180 lines)
  ├─ Distributed coordination (200 lines)
  ├─ Deduplication (120 lines)
  └─ Tests (400 lines)
  Total: 900 lines

Week 4: CLI & Config
  ├─ CLI integration (60 lines)
  ├─ Config loader (150 lines)
  ├─ Schema validation (80 lines)
  └─ Tests (200 lines)
  Total: 490 lines

Week 5: Testing & Docs
  ├─ Integration tests (400 lines)
  ├─ Resilience tests (300 lines)
  ├─ Documentation (1,500 lines)
  └─ Final integration (200 lines)
  Total: 2,400 lines

TOTAL: ~5,240 lines
```

---

## Success Criteria

### Functional Requirements ✅

- [ ] FederationRepairProvider successfully stores repairs in memchain SurrealDB
- [ ] Cross-node repair coordination works without conflicts
- [ ] Fallback to JSONL works when federation unavailable
- [ ] Multi-instance TUI repairs visible across all instances
- [ ] Repair history fully queryable from federation
- [ ] Loki event logging captures all repairs with correlation IDs
- [ ] OAuth/Hydra authentication integrated

### Non-Functional Requirements ✅

- [ ] Latency: <100ms for repair coordination (federation-local)
- [ ] Throughput: >100 repairs/second per instance
- [ ] Availability: 99.9% (graceful degradation via fallback)
- [ ] Memory: <50MB overhead for federation client
- [ ] Maintainability: <20 lines of operational config
- [ ] Test Coverage: >90% (integration + unit tests)

### Architectural Alignment ✅

- [ ] Follows NABI protocol governance
- [ ] Leverages existing memchain infrastructure
- [ ] Uses federation authentication (Hydra/OAuth)
- [ ] Integrates with Loki monitoring
- [ ] WebSocket coordination via message bus
- [ ] Cross-platform compatible (iOS, Web, CLI)
- [ ] No new external dependencies

---

## Key Architectural Principles

### 1. Architectural Continuity
```
Phase 6B: Pluggable persistence (abstraction)
       ↓
Phase 6C: Federation integration (concrete realization)
       ↓
Result: riff-cli becomes federation-native, not siloed
```

### 2. Low Operational Overhead
```
Before: HTTP proxy + separate SurrealDB instance
After: Single MCP coordination message
       ↓
Complexity: Reduced
Maintenance: Delegated to federation
```

### 3. NABI Protocol Alignment
```
Governance: ✅ Federation coordination
Authentication: ✅ OAuth/Hydra
Transport: ✅ WebSocket via message bus
Observability: ✅ Loki event logging
Resilience: ✅ Graceful degradation
```

### 4. Zero-Friction Integration
```
Users don't need to:
  ❌ Configure new databases
  ❌ Manage credentials separately
  ❌ Set up proxies
  ✅ Just run riff with --federation-mode
```

---

## Phase 6C Dependencies

**Must Be Complete Before Phase 6C**:
- ✅ Phase 6B (Persistence Provider Abstraction) - DONE
- ✅ memchain MCP servers running
- ✅ SurrealDB on federation (ws://100.97.105.80:8000)
- ✅ Loki monitoring available
- ✅ Hydra OAuth configured

**Can Proceed in Parallel**:
- Phase 7 (Memory Curation) - independent
- Other federation feature work

---

## Next Steps

1. **Stakeholder Review**: Confirm architecture with federation leads
2. **Spike Investigation**: Verify MCP coordination patterns work as designed
3. **Prototype Week 1**: Build FederationRepairProvider POC
4. **Feedback Loop**: Validate coordination with memchain team
5. **Full Implementation**: Execute 5-week timeline

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| MCP coordination overhead | High latency | Cache frequently accessed repairs |
| Federation unavailability | Service interruption | Fallback to JSONL (automatic) |
| SurrealDB schema mismatch | Data corruption | Automated schema validation |
| Concurrent repairs conflicts | Data inconsistency | Distributed locking via MCP |
| Auth token expiration | Repair failures | Automatic token refresh |
| Loki log volume | Storage bloat | Retention policies, aggregation |

---

## Post-Implementation: Phase 6D & 6E

**Phase 6D: Background Jobs**
- Materialized view sync across federation
- Drift detection from Loki
- Cleanup of stale repair events

**Phase 6E: Advanced Features**
- Real-time repair dashboard (Grafana)
- Repair analytics by operator
- Cross-conversation repair patterns
- Predictive repair suggestions

