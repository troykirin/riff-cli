# RIFF-CLI Quick Reference

**Assessment Date**: 2025-10-28  
**Status**: ACTIVE DEVELOPMENT - Ready for production (search), TUI in Week 2

---

## Key Facts

| Aspect | Status |
|--------|--------|
| **Active** | ✅ Yes - last commit today |
| **Maintained** | ✅ Full-time development |
| **Version** | 2.0.0 (Python 3.13+) |
| **Location** | /Users/tryk/nabia/tools/riff-cli |
| **Federation** | ✅ Integrated (~/.nabi/venvs/riff-cli) |
| **Production-Ready** | ✅ Search, Fix, Scan modules |
| **TUI Ready** | 🚧 Week 2 in progress |

---

## Core Capabilities

```
✅ Semantic Search     - Find conversations by meaning (Qdrant)
✅ Content Preview    - See actual text snippets in results
✅ Time Filtering     - --days, --since, --until options
✅ JSONL Repair       - Scan/fix broken conversation exports
✅ Graph Analysis     - Visualize conversation structure
✅ UUID Lookup        - Direct session ID search
🚧 Interactive TUI    - vim-style navigation (Week 2)
```

---

## Development Stage

**Phase Timeline**:
- Week 1: Foundation ✅ COMPLETE
  - Clean architecture
  - Docker/Taskfile
  - Semantic search live
  - Documentation complete

- Week 2: TUI Module 🚧 IN PROGRESS
  - Interactive search interface
  - vim navigation
  - Graph navigator

- Week 3-4: Polish & Production

---

## File Organization

```
riff-cli/
├── src/riff/
│   ├── cli.py              # Entry point
│   ├── search/             # Qdrant search
│   ├── enhance/            # AI enhancement
│   ├── classic/            # Original commands
│   ├── tui/                # New interactive UI
│   ├── graph/              # DAG analysis
│   └── surrealdb/          # DB integration
├── tests/                  # 22 test files
├── docs/                   # 36+ documentation files
└── infrastructure/         # Docker, Qdrant config
```

---

## Configuration

| Component | Location | Status |
|-----------|----------|--------|
| Python | 3.13 | ✅ Cutting-edge |
| Virtual Env | ~/.nabi/venvs/riff-cli | ✅ Present |
| Build System | uv + uv_build | ✅ Modern |
| direnv | .envrc | ✅ Auto-loads |
| Hooks | .hookrc | ✅ XDG-compliant |
| Database | SurrealDB (nabi ns) | ✅ Configured |

---

## Uncommitted Work

**42 files with pending changes**:
- 5 deleted (doc reorganization)
- 39 modified (refinement)
- Pattern: Week 1 cleanup tasks in final stages

---

## Known Issues

1. **Remote Sync Needed**
   - Local 6 commits ahead, 4 behind origin
   - Requires: `git pull` decision

2. **Path Hardcoding**
   - Some paths use `-Users-tryk--nabi` format
   - Needs: XDG-compliant refactoring

3. **Nabi Integration**
   - Registration workflow defined but not verified
   - Needs: `task nabi:register` validation

---

## Quick Start

```bash
# Navigate to project
cd /Users/tryk/nabia/tools/riff-cli

# Activate environment (auto via direnv)
direnv allow

# List available tasks
task --list

# Search conversations
uv run riff search "query here"

# Repair JSONL
task scan -- ~/path/to/sessions/

# View help
uv run riff --help
```

---

## Documentation Highlights

**Must Read**:
1. ARCHITECTURE.md - System design (production-grade)
2. WEEK1_COMPLETION.md - Phase status
3. REPAIR_WORKFLOW.md - JSONL repair guide

**Reference**:
- PHASE_6C_FEDERATION_INTEGRATION_PLAN.md - Current roadmap
- FEDERATION_INTEGRATION_BRIDGE.md - Alignment with nabi
- SYNC_SURREALDB.md - Database procedures

---

## Full Assessment

See detailed report:
```
/Users/tryk/nabia/tools/riff-cli/REPOSITORY_ASSESSMENT_2025-10-28.md
```

---

## Next Steps (Priority)

1. [ ] Sync remote: `git pull`
2. [ ] Commit cleanup: 42 pending files
3. [ ] Refactor paths: Replace hardcoded user paths
4. [ ] Verify nabi: `task nabi:register`
5. [ ] Complete Week 2: TUI milestone

---

**Bottom Line**: riff-cli is ACTIVE, MAINTAINED, and PRODUCTION-READY for search. TUI enhancements coming Week 2.
