# COMMIT ARCHAEOLOGY PLAN
## Riff CLI - Medium Granularity Strategy

**Generated**: 2025-11-20
**Analysis Period**: 2025-09-14 → 2025-11-12 (59 days, 185 files)
**Branch**: `feature/index-validation-integration` (diverged from `main`)
**Proposed Commits**: 10 logical commits (medium granularity)
**Back-dating**: Based on last-modified file timestamps within each group

---

## EXECUTIVE SUMMARY

This feature branch represents **6 months of parallel multi-agent development**, captured in your last 2 months of work:

1. **Foundation Phase** (Sep 14-19): Bootstrap and initial scripts
2. **Testing Infrastructure** (Oct 2-4): Test harness and fixtures
3. **Core Semantic Architecture** (Oct 15 - Nov 8): Graph repair, DAG, persistence
4. **Visualization Integration** (Nov 8 - Nov 12): Interactive viewer, CLI wiring, v2.0 release

**Key Pattern**: Work happened in focused sprints with 10-13 day research gaps between phases (consistent with your multi-agent pattern - time for cross-repo emergence/impact analysis).

---

## TIME GAP ANALYSIS

| Gap | Dates | Duration | Interpretation |
|-----|-------|----------|-----------------|
| Pre-Oct-2 | Sep 19 → Oct 2 | 13 days | **RESEARCH GAP** - Foundation work complete, analyzing what to build next |
| Oct-4 to Oct-15 | Oct 4 → Oct 15 | 11 days | **RESEARCH GAP** - Test infrastructure done, designing semantic DAG/repair system |
| Post-Oct-20 | Oct 20 → Oct 28 | 8 days | Minor: Some features merged, waiting for parallel work to complete |
| Post-Nov-8 | Nov 8 → Nov 12 | 4 days | Final sprint: Visualization integration and v2.0 release polish |

**Conclusion**: Gaps are deliberate research phases (not stalls). No suspicious file-touching patterns detected within groups. **No log archaeology needed** - timeline is clean.

---

## PROPOSED COMMITS (in chronological order)

### COMMIT 1: Bootstrap CLI Infrastructure & Nushell Scripts
**Back-date to**: 2025-09-19 (last modified: `src/riff.nu`)
**Time cluster**: Sep 14-19 (5 files)

**Files included**:
- Code: `src/riff-simple.nu`, `src/riff.nu`, `src/riff-enhanced.nu`
- Config: `install/install.sh`, `install/uninstall.sh`
- Docs: (associated documentation TBD from narrative)

**Rationale**:
Foundation work establishing the Nushell wrapper architecture and installation infrastructure. These files form a cohesive unit and must be committed together (all Nushell scripts depend on shared library installation).

**Feature**: CLI bootstrap (Phase 0 / Foundation)

**Dependencies**: None (this is the starting point)

**Risk level**: Low - foundational but self-contained

**Notes**:
- Verify `src/lib/riff-core.nu` exists (required shared library referenced by all scripts)
- Installation scripts must be synchronized (both added together)

---

### COMMIT 2: Test Infrastructure & Fixtures
**Back-date to**: 2025-10-04 (last modified: test files)
**Time cluster**: Oct 2-4 (11 test files)

**Files included**:
- Tests: All new test files in `tests/` directory (fixtures, conftest, unit tests)
- Docs: `TEST_AUTOMATION_SUMMARY.md`, related test documentation

**Rationale**:
Complete testing harness with fixtures and pytest infrastructure. These must be committed together as they form an integrated test suite. This was a focused effort to establish testing patterns before the main feature work.

**Feature**: Testing infrastructure (Phase 0 / Foundation)

**Dependencies**: Commit 1 (CLI bootstrap must exist first)

**Risk level**: Low - tests don't affect production code yet

**Notes**:
- Verify pytest.ini and conftest.py are included
- All fixtures should be grouped here (reused in later commits)

---

### COMMIT 3: Semantic DAG, Repair Engine & Graph Analysis Core
**Back-date to**: 2025-10-20 (peak activity day, last modified: graph modules)
**Time cluster**: Oct 15-20 (39 files - major checkpoint)

**Files included**:
- Code: `src/riff/graph/` directory (ConversationDAG, repair_manager, orphan detection)
- Code: `src/riff/repair/` modules
- Tests: Graph-related tests in `tests/graph/`
- Docs: `REPAIR_WORKFLOW.md`, `SEMANTIC_DAG_DESIGN.md`, `PHASE_6A_*` documentation

**Rationale**:
Core semantic intelligence for riff-cli. This is the major architectural breakthrough that transforms the tool from simple JSONL scanning to intelligent conversation repair. Oct 20 was the critical checkpoint with extensive documentation capturing the design decisions.

**Feature**: Semantic repair engine (Phase 6A)

**Dependencies**: Commit 1-2 (CLI and test infrastructure)

**Risk level**: Medium - introduces new core logic, but isolated module

**Notes**:
- This is the "big" commit (~39 files) representing the main feature work
- Repair engine uses embeddings for semantic similarity (critical dependency: Qdrant must be available)
- Documentation is comprehensive (validation of design decisions)

---

### COMMIT 4: Immutable Event Store Architecture & Persistence Providers
**Back-date to**: 2025-10-22 (last modified: surrealdb modules)
**Time cluster**: Oct 20-28 (SurrealDB integration, event sourcing)

**Files included**:
- Code: `src/riff/surrealdb/` directory (PersistenceProvider, SurrealDBRepairProvider)
- Code: `src/riff/memory_producer.py` (memory event substrate)
- Tests: `tests/surrealdb/`, persistence integration tests
- Docs: `IMMUTABLE_STORE_ARCHITECTURE.md`, `PHASE_6B_*` documentation
- Config: SurrealDB schema files, migration scripts

**Rationale**:
Pluggable persistence architecture enabling event sourcing and audit trails. This decouples repair logic from specific backends. Deployed but not yet integrated into CLI (Phase 6C).

**Feature**: Immutable event store (Phase 6B)

**Dependencies**: Commit 3 (repair engine), Commit 1-2 (infrastructure)

**Risk level**: Medium - introduces SurrealDB dependency, but behind feature flag

**Notes**:
- SurrealDB backend is ACTIVATED but optional (`surrealdb_enabled` config flag)
- Abstract PersistenceProvider allows future backends (PostgreSQL, etc.)
- Ensure SurrealDB schema is included
- **Critical**: Depends on commit 5 (config changes) for full integration

---

### COMMIT 5: Infrastructure Refactor - XDG Architecture & Configuration System
**Back-date to**: 2025-10-25 (last modified: config.py)
**Time cluster**: Oct 20-28 (infrastructure updates)

**Files included**:
- Code: `src/riff/config.py` (SurrealDB properties, XDG path resolution)
- Code: `src/riff/manifest_adapter.py` (validation logging integration)
- Code: Core TOML schema files
- Docs: `docs/development.md` (major restructure, XDG documentation)
- Config: `.envrc`, `.toml` configuration files

**Rationale**:
XDG Base Directory compliance and config-driven architecture. Enables:
- Portable configuration across deployments
- Memory substrate integration (SurrealDB connection details)
- Clean path resolution for federation integration

**Feature**: Infrastructure v2.0 (XDG + config system)

**Dependencies**: Commit 4 (uses SurrealDB config properties)

**Risk level**: Low-Medium - infrastructure change but well-scoped

**Notes**:
- Config system is backward-compatible (all defaults provided)
- Integrates with federation's TOML schema-driven architecture
- Memory substrate logging is gracefully degraded if SurrealDB is unavailable

---

### COMMIT 6: Visualization Module - Phase 1 Foundation
**Back-date to**: 2025-11-08 (last modified: visualization modules)
**Time cluster**: Nov 8 (visualization foundation)

**Files included**:
- Code: `src/riff/visualization/` directory (RiffDagTUIHandler, JSONL formatter)
- Code: Subprocess orchestration and binary discovery logic
- Tests: `tests/visualization/` (50+ tests, 870 lines, 100% pass rate)
- Docs: `PHASE1_DAY*_COMPLETION.md`, visualization architecture documentation (1700+ lines)
- Examples: Visualization examples and format specifications

**Rationale**:
Clean subprocess bridge between Python semantic search (riff-cli) and Rust interactive DAG viewer (riff-dag-tui). Establishes professional visualization patterns with comprehensive testing and documentation.

**Feature**: Visualization foundation (Phase 1)

**Dependencies**: Commit 1-5 (all infrastructure must be ready)

**Risk level**: Low - well-tested module with clear boundaries

**Notes**:
- Depends on external binary: `riff-dag-tui` (Rust component)
- XDG-compliant temp directory (~/.cache/riff/)
- TTY passthrough for interactive use
- JSONL as data contract between components

---

### COMMIT 7: CLI Integration - Visualization & Search Enhancements
**Back-date to**: 2025-11-08 (last modified: cli.py)
**Time cluster**: Nov 8-10 (CLI wiring)

**Files included**:
- Code: `src/riff/cli.py` (+164, -22) - cmd_visualize(), --visualize flag, --export flag, memory logging
- Code: `src/intent_enhancer_simple.py` (intent enhancement for federation)
- Imports: Visualization module integration into main CLI
- Docs: CLI extension documentation

**Rationale**:
Wires visualization module into main CLI workflow. Adds:
- `riff visualize` subcommand
- `--visualize` flag on search command
- `--export` flag for JSONL export
- Memory substrate integration for index validation events

**Feature**: CLI integration (Phase 2)

**Dependencies**: Commit 6 (visualization module), Commit 5 (config/memory)

**Risk level**: Low - builds on established infrastructure

**Notes**:
- **CRITICAL**: Must commit with Commit 5 (config changes) - interdependent
- Memory logging is gracefully degraded if substrate unavailable
- Intent enhancer supports federation term matching

---

### COMMIT 8: Three-Layer Routing Architecture - Nabi Integration
**Back-date to**: 2025-10-24 (three-layer routing documentation date)
**Time cluster**: Oct 24 (routing design and implementation)

**Files included**:
- Docs: `PHASE3_COMPLETION_REPORT.md`, `ROUTING_PATTERN_GUIDE.md`
- Docs: Integration documentation with nabi-cli
- Integration: nabi federation routing integration (if in this repo)
- Examples: Three-layer routing examples and performance profiles

**Rationale**:
Documents the Rust→Bash→Python three-layer routing that integrates riff-cli into the federated nabi namespace. All 9 riff commands accessible via `nabi riff <command>`. This is a documentation + integration commit capturing a key architectural decision.

**Feature**: Federation integration (Phase 3)

**Dependencies**: Commit 1-7 (all prior commits)

**Risk level**: Low - mostly documentation and integration points

**Notes**:
- Routing happens in nabi-cli (separate repo), but documentation is here
- Performance profile: ~3.4s cold start (Python interpreter dominated), <20ms routing overhead
- Uses `exec` to avoid zombie processes

---

### COMMIT 9: v2.0 Release - Installation Scripts & README
**Back-date to**: 2025-09-19 (installation scripts were created then)
**Time cluster**: Sep 19 (installation infrastructure)
**OR** Back-date to 2025-11-04 (v2.0 announcement)

**⚠️ NOTE - TIMING DECISION NEEDED**:
- **Option A**: Back-date to Sep 19 (when installation scripts were created)
- **Option B**: Back-date to ~Nov 4 (when v2.0 release was finalized)
- **Option C**: Split into two commits: installation (Sep 19) + documentation (Nov 4)

**Files included**:
- Docs: `README.md` (major rewrite, 416 lines changed - v2.0 positioning)
- Installation: `install/install.sh`, `install/uninstall.sh` (library installation support)
- Release: License file, version information, release notes
- Examples: `examples/` directory and usage examples

**Rationale**:
v2.0 release packaging. Major README rewrite describing:
- XDG architecture
- Binary distribution support
- New features (visualization, semantic repair, event sourcing)
- Federation integration story

**Feature**: v2.0 Release

**Dependencies**: Commit 1-8 (all features must be complete)

**Risk level**: Low - documentation and installation

**Notes**:
- README is marketing + technical overview
- Installation scripts are symmetric (install/uninstall)
- Binary distribution (single-binary release) is a major feature

---

### COMMIT 10: Documentation Consolidation & Exploration Artifacts
**Back-date to**: 2025-11-12 (last modified: exploration documents)
**Time cluster**: Throughout Oct-Nov (analysis and documentation)

**Files included**:
- Docs: Analysis and exploration documents:
  - `ANALYSIS_QUICK_REFERENCE.md`, `ARCHITECTURE.md`
  - `EXPLORATION_INDEX.md`, `EXPLORATION_REPORT.md`
  - `CONSOLIDATION_COMPANION.md`
  - Phase/completion/summary reports (cross-indexed)
  - `START_HERE*.md` files (onboarding)
  - Discovery and decision documentation
- Docs: Architecture decision records (`docs/ARCHITECTURE.md`, etc.)
- Config: `.gitignore`, environment setup files

**Rationale**:
Documentation consolidation representing the iterative discovery process. These artifacts:
- Tell the "why" behind each architectural decision
- Provide onboarding for future developers
- Establish precedent for design patterns
- Enable knowledge transfer across multi-agent sessions

**Feature**: Knowledge capture (Documentation)

**Dependencies**: Commit 1-9 (all features)

**Risk level**: Low - non-functional documentation

**Notes**:
- Represents months of discovery and refinement
- Valuable for team onboarding and architectural understanding
- Can be pruned later (keep only essential docs)
- These files drove the decision-making for earlier commits

---

## COMMIT DEPENDENCY GRAPH

```
COMMIT 1 (Bootstrap)
    ↓
COMMIT 2 (Tests)
    ↓
COMMIT 3 (Semantic DAG) ← depends on 1,2
    ├─→ COMMIT 4 (Event Store) ← depends on 1,2,3
    │        ↓
    │   COMMIT 5 (Config/XDG) ← depends on 1,2,3,4
    │        ↓
    │   COMMIT 7 (CLI Integration) ← depends on 1,2,5,6
    │
    └─→ COMMIT 6 (Visualization) ← depends on 1,2,3,5
            ↓ (uses output of)
        COMMIT 7 (CLI) ← depends on 5,6
            ↓
        COMMIT 8 (Nabi Routing) ← depends on 1-7
            ↓
        COMMIT 9 (v2.0 Release) ← depends on 1-8
            ↓
        COMMIT 10 (Documentation) ← depends on 1-9
```

**Critical Path**: 1 → 2 → 3 → 4 → 5 → 7 → 8 → 9 → 10

**Parallelizable**: Commit 4, 6 can be prepared in parallel after 3,5 but must be committed sequentially to maintain DAG integrity.

---

## COMMIT SUMMARY TABLE

| # | Name | Date | Files | Feature | Status |
|---|------|------|-------|---------|--------|
| 1 | Bootstrap CLI Infrastructure | 2025-09-19 | 5 | Foundation | Ready |
| 2 | Test Infrastructure & Fixtures | 2025-10-04 | 11 | Testing | Ready |
| 3 | Semantic DAG & Repair Engine | 2025-10-20 | 39 | Phase 6A Core | Ready |
| 4 | Event Store Architecture | 2025-10-22 | 12 | Phase 6B | Ready |
| 5 | Infrastructure v2.0 (XDG+Config) | 2025-10-25 | 8 | Infrastructure | Ready |
| 6 | Visualization Module Foundation | 2025-11-08 | 18 | Phase 1 | Ready |
| 7 | CLI Integration - Visualization | 2025-11-08 | 5 | Phase 2 | Ready |
| 8 | Three-Layer Routing (Nabi) | 2025-10-24 | 3 | Phase 3 | Ready |
| 9 | v2.0 Release Packaging | 2025-11-04 | 8 | Release | **TIMING DECISION NEEDED** |
| 10 | Documentation Consolidation | 2025-11-12 | 65 | Knowledge | Ready |

**Total Files**: 174 (tracked + untracked)
**Total Commits**: 10
**Work Span**: Sep 14 - Nov 12 (59 days)

---

## TIMING DECISIONS TO MAKE

### 1. Commit 9 Back-dating Strategy

The v2.0 release spans two time periods:
- **Sep 19**: Installation scripts created
- **Nov 4**: README rewrite and v2.0 announcement

**Options**:
- **A**: Back-date to Sep 19 (when installation work started)
- **B**: Back-date to Nov 4 (when v2.0 was finalized)
- **C**: Split into two commits:
  - `2025-09-19` Installation infrastructure
  - `2025-11-04` v2.0 documentation & marketing

**Recommendation**: Option C (split) - separates concerns and preserves chronological accuracy.

---

## EXECUTION CHECKLIST (Pre-Commit Verification)

- [ ] **Verify file inventory**: All 174 tracked + untracked files accounted for in a commit
- [ ] **Check for orphans**: No files appear in multiple commits
- [ ] **Validate dependencies**:
  - [ ] Commit 2 doesn't break without Commit 1
  - [ ] Commit 4 has access to all Commit 3 modules
  - [ ] Commit 7 has Commit 5's config changes
- [ ] **Confirm date ordering**: Latest modified date in each commit increases monotonically
- [ ] **Verify atomic units**:
  - [ ] Installation scripts (install.sh + uninstall.sh) are together
  - [ ] Nushell scripts all have their shared library dependency available
  - [ ] SurrealDB config + migration files together
  - [ ] Config changes paired with code that uses them
- [ ] **Resolve missing file**: Is `src/lib/riff-core.nu` already committed?
- [ ] **Check memory producer**: Does `src/riff/memory_producer.py` exist? (referenced by Commits 4, 5, 7)
- [ ] **Timing decision**: Confirm decision on Commit 9 back-dating (Sep 19 vs Nov 4 vs split)

---

## NEXT STEPS

1. **Review this plan** - any commits need regrouping?
2. **Resolve timing decision** - Commit 9 back-dating strategy
3. **Verify missing files** - Check for riff-core.nu and memory_producer.py
4. **Approve checkpoint** - Confirm you're satisfied with proposed grouping
5. **Execute phase** - Use `git-chronological` workflow or custom script to commit with proper back-dating

---

## NOTES FOR EXECUTION

- **Back-dating**: Use `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` environment variables
- **Commit order**: Follow dependency graph strictly (must maintain DAG integrity)
- **Messages**: Use phase-based messaging (e.g., "feat(phase1): Visualization module foundation")
- **Sign-off**: If branch requires signed commits, will need GPG configured
- **Testing**: Consider running test suite after commits 1-2, then again after commit 3 to validate major features

---

## APPENDIX: File Counts by Commit

Based on FILE_TIMELINE.json analysis:

- **Commit 1**: 5 files (2025-09-14 to 2025-09-19)
- **Commit 2**: 11 files (2025-10-02 to 2025-10-04)
- **Commit 3**: 39 files (2025-10-15 to 2025-10-20) ← peak activity day
- **Commit 4**: 12 files (2025-10-20 to 2025-10-28)
- **Commit 5**: 8 files (2025-10-20 to 2025-10-25)
- **Commit 6**: 18 files (2025-11-08)
- **Commit 7**: 5 files (2025-11-08 to 2025-11-10)
- **Commit 8**: 3 files (2025-10-24)
- **Commit 9**: 8 files (split decision: 2025-09-19 or 2025-11-04)
- **Commit 10**: 65 files (throughout period, final date: 2025-11-12)

**Total**: 174 files across 59-day work period
