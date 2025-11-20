# SurrealDB Consolidation: Quick Reference
**Single Instance (8284) | Three Namespaces | Riff Phase 6B Ready**

---

## 🚀 At a Glance

```
Port 8284 (localhost)
└─ Single SurrealDB Instance
   ├─ MEMORY namespace
   │  ├─ agent:*          (Federation agent state)
   │  ├─ task:*           (Task coordination)
   │  ├─ event:*          (Federation events)
   │  └─ repairs_events   (Riff repair audit log) ⭐ READY
   │
   ├─ VIGIL namespace
   │  ├─ item             (TimeSliced knowledge atoms)
   │  ├─ timeslice        (Temporal boundaries)
   │  ├─ relation         (Dendrite-like edges)
   │  └─ schema_ver       (Schema evolution tracking)
   │
   └─ FEDERATION namespace
      ├─ service:*        (Service registry)
      ├─ event:*          (Cross-machine events)
      └─ agent:*          (Agent discovery)
```

---

## 📋 Essential Locations

| Component | Location | Size | Status |
|-----------|----------|------|--------|
| **Data** | `~/.local/share/nabi/surrealdb/data/` | 16GB | ✅ Active |
| **Config** | `~/.config/nabi/surreal/surreal.toml` | 1.2KB | ✅ Configured |
| **Vigil Schema** | `~/.config/nabi/vigil/surrealdb/schema.surql` | 103 lines | ✅ Deployed |
| **Riff Phase 6B** | `~/nabia/tools/riff-cli/src/riff/surrealdb/` | 30KB+ | ✅ Built (disabled) |
| **Tests** | `~/nabia/tools/riff-cli/tests/surrealdb/` | 5 test files | ✅ Ready |
| **Federation Registry** | `~/.config/nabi/federation-registry.toml` | 11KB | ✅ Active |

---

## 🔌 Connection Details

```bash
# Direct Connection
URL: ws://localhost:8284/rpc           # WebSocket
URL: http://localhost:8284/            # HTTP REST

# Configuration
User: root
Pass: (environment variable or config)

# Default Namespace
namespace = "memory"
database = "nabi"
```

---

## 🔄 Riff-CLI Phase 6B: Ready to Activate

### Current Status
- ✅ **Implementation**: Complete (storage.py, 30KB+)
- ✅ **Tests**: Written and ready (5 test files)
- ✅ **Schema**: Can be deployed to memory namespace
- ❌ **Enabled**: Currently disabled (`surrealdb_enabled = false`)

### What It Does
1. **Logs repairs** as immutable events to `repairs_events` table
2. **Materializes sessions** by replaying events
3. **Provides audit trail** - every repair timestamped and immutable
4. **Enables rollback** - reconstruct pre-repair state anytime

### Activation Steps (5 minutes)
```bash
# 1. Update config
echo "surrealdb_enabled = true" >> ~/.config/nabi/tools/riff.toml

# 2. Create schema
surreal import --conn ws://localhost:8284/rpc \
  --user root --pass $SURREAL_PASS \
  ~/nabia/tools/riff-cli/src/riff/surrealdb/schema_repairs.surql

# 3. Run tests
cd ~/nabia/tools/riff-cli
pytest tests/surrealdb/ -v

# 4. Enable in code
# src/riff/config.py: surrealdb_enabled = True
```

---

## 🧠 Vigil Namespace: Strategic Oversight

### Design Pattern: TimeSliced Items

```
Item (note|log|span|artifact|metric)
  │
  ├─ content: { What happened }
  ├─ vec: [0.1, 0.2, ...] (optional embedding)
  ├─ source: cli|tmux|riff|vigil|agent|fs
  └─ created_at: 2025-11-12T04:45:00Z
      │
      └─► relation[weight:0.8] ──► Relation (MENTIONS, DERIVED_FROM, CAUSES)
              │
              └──► TimeSlice
                    ├─ session_id: "riff-session-123"
                    ├─ device: mac|wsl|rpi
                    ├─ t_start: 2025-11-12T04:45:00Z
                    └─ t_end: null (ongoing) or timestamp
```

### Query Patterns

```sql
-- Find all items in a time window
SELECT * FROM item
WHERE ->relation->timeslice
  AND timeslice.t_start >= $start
  AND (timeslice.t_end <= $end OR timeslice.t_end IS NULL)

-- Get all items from a specific session
SELECT * FROM item
WHERE ->relation->timeslice
  AND timeslice.session_id = 'session-123'

-- Trace item lineage (what caused this item?)
SELECT * FROM item:123->relation WHERE kind = 'DERIVED_FROM'
```

---

## 🎯 Consolidation Benefits

| Before | After |
|--------|-------|
| Multiple databases | Single SurrealDB |
| Scattered schemas | Unified namespaces |
| Manual backups | Automated snapshots |
| No audit trail | Immutable event logs |
| Vector-only search | Vector + relational + temporal |
| Single-machine | Federation-ready |

---

## 💾 Backup Strategy

**Automatic Backup**:
- Location: `~/.local/share/nabi/surrealdb/data.backup.TIMESTAMP/`
- Frequency: On consolidation completion
- Method: Full RocksDB snapshot

**Recovery**:
```bash
# Restore from backup
cp -r ~/.local/share/nabi/surrealdb/data.backup.20251102-141425/* \
      ~/.local/share/nabi/surrealdb/data/

# Verify integrity
surreal query ws://localhost:8284/rpc "INFO FOR DB"
```

---

## 🔍 Diagnostic Commands

```bash
# Check if running
curl -s http://localhost:8284/health

# Query namespaces
surreal query ws://localhost:8284/rpc --user root "LIST NAMESPACES"

# Check memory namespace
surreal query ws://localhost:8284/rpc --user root --ns memory "LIST TABLES"

# Check Vigil namespace
surreal query ws://localhost:8284/rpc --user root --ns vigil "LIST TABLES"

# Count repair events
surreal query ws://localhost:8284/rpc --user root --ns memory "SELECT COUNT() FROM repairs_events GROUP ALL"

# View recent repairs
surreal query ws://localhost:8284/rpc --user root --ns memory \
  "SELECT * FROM repairs_events ORDER BY created_at DESC LIMIT 10"
```

---

## 📊 Architecture Decision: Why Three Namespaces?

### MEMORY Namespace
- **Purpose**: Federation coordination hub
- **Scope**: Agent state, task tracking, federation events
- **Consistency**: ACID, real-time
- **Sharing**: All federation tools access here
- **Riff Integration**: repairs_events table for audit trail

### VIGIL Namespace
- **Purpose**: Strategic oversight + temporal memory
- **Scope**: TimeSliced items, dendrite relations, schema evolution
- **Consistency**: Append-only (never destructive)
- **Sharing**: Vigil reads/writes, other tools can query
- **Strength**: Temporal analysis, session isolation, cross-device context

### FEDERATION Namespace
- **Purpose**: Service coordination (TBD, partially defined)
- **Scope**: Service registry, agent discovery, event publishing
- **Consistency**: Eventually consistent (distributed)
- **Sharing**: All federation nodes
- **Status**: Schema in-progress

---

## ⚡ Performance Notes

- **Block Cache**: 33GB (optimized for 16GB data)
- **Background Threads**: 10 (database) + 10 (merging) = 20 total
- **Write Buffer**: 128MB per memtable, 32 max
- **Compaction**: Level-based with delete optimization
- **Latency**: <100ms typical queries, <500ms complex traversals

---

## 🚀 Next Steps

### This Week
- [ ] Verify 8284 connectivity
- [ ] Review Vigil temporal schema
- [ ] Activate Riff Phase 6B (flag flip + schema)
- [ ] Run test suite

### Next Week
- [ ] Wire TUI repair logging to SurrealDB
- [ ] Implement materialization caching
- [ ] Test rollback scenarios

### Strategic (Q4)
- [ ] Complete Federation namespace schema
- [ ] Enable federation-wide repair sync
- [ ] Unified query API across namespaces
- [ ] Temporal analysis dashboards

---

## 📚 Deep Dive Documentation

- **Architecture**: `SURREALDB_CONSOLIDATION_DISCOVERY.md` (this directory)
- **Vigil Schema**: `~/.config/nabi/vigil/surrealdb/schema.surql`
- **Phase 6B Details**: `src/riff/surrealdb/PHASE6B_README.md`
- **Integration Guide**: `src/riff/surrealdb/INTEGRATION_GUIDE.md`
- **Configuration**: `~/.config/nabi/surreal/surreal.toml`

---

**Status**: ✅ Consolidated + Ready to Activate Riff Phase 6B
**Last Updated**: 2025-11-12
