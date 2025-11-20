# Commit Strategy Based on File Timeline Analysis

## Quick Reference: What to Commit & When

Based on modification timestamp analysis of 185 files across 59 days, here's the recommended commit strategy:

---

## Session 1: Foundation (Sep 14-19)

### Commit 1: "Initial riff-cli foundation and documentation"

**Date**: `2025-09-19 16:13:00`  
**Files**: 9 total

```
docs/RIFF-CLAUDE-EXTENSION.md
CLAUDE-DATA-SCHEMA.yaml
2025-09-12-nos-400.txt
AGENTS.md
src/riff-simple.nu
install/install.sh
install/uninstall.sh
src/riff.nu
src/riff-enhanced.nu
```

**Reasoning**: These 9 files form the natural foundation. The Nushell scripts all cluster Sep 19 afternoon (tight 2-hour window), suggesting they were created together.

---

## Session 2: Test Infrastructure (Oct 2-4)

### Commit 2: "Add test framework and library scaffolding"

**Date**: `2025-10-04 19:48:05`  
**Files**: 11 total

```
src/lib/
src/types/
src/integration/
tests/test_intent_enhancer.py
tests/test_jsonl_tool.py
tests/conftest.py
pytest.ini
docs/PATTERNS.md
requirements-dev.txt
src/intent_enhancer_simple.py
tmp.J1U41IBYgx (temp artifact - may skip)
```

**Reasoning**: Clean test infrastructure checkpoint. All pytest/library files form a coherent unit.

---

## Session 3: Core Development (Oct 15 - Nov 12)

### Strategy: 7 Feature-Focused Commits

This session is complex (165 files) and should be split by architectural feature rather than time.

---

### Commit 3: "Add graph navigation and search infrastructure"

**Date**: `2025-10-20 15:01:24`  
**Files**: ~17 files

**Core Code**:
```
src/riff/search/__init__.py
src/riff/backends/
src/riff/enhance/
src/riff/tui/__init__.py
src/riff/tui/interface.py
src/riff/__main__.py
```

**Supporting Docs** (checkpoint documents from Oct 17-20):
```
docs/ARCHITECTURE.md
docs/TIME_FILTERING.md
docs/SEMANTIC_DAG_DESIGN.md
docs/SURREALDB_INTEGRATION_ANALYSIS.md
docs/VISUALIZER_IMPLEMENTATION.md
docs/GRAPH_MODULE.md
docs/GRAPH_NAVIGATOR_USAGE.md
RIFF_UNIFIED.md
.python-version
.hookrc
riff (executable)
Taskfile.yml
examples/
scripts/
tests/explore_qdrant.py
```

**Commit Message**:
```
feat: Add graph navigation and search infrastructure (phase 1)

- Implement recursive intent-driven search system (fixes NOS-444)
- Add semantic DAG visualization foundation  
- Integrate Qdrant index for entity search
- Add time-based filtering and session recovery
- Comprehensive architecture documentation
```

---

### Commit 4: "Implement SurrealDB integration and persistence"

**Date**: `2025-10-28 20:16:54`  
**Files**: ~15 files

**Core Code**:
```
src/riff/surrealdb/
src/riff/graph/
src/claude_schema.py
src/intent_enhancer.py
```

**Supporting Docs**:
```
ENTERPRISE_ARCHITECTURE_ASSESSMENT.md
REPOSITORY_ASSESSMENT_2025-10-28.md
QUICK_REFERENCE_2025-10-28.md
docs/COMPREHENSIVE_ARCHITECTURE_ANALYSIS_2025-10-28.md
docs/ANALYSIS_QUICK_REFERENCE.md
docs/_ANALYSIS_INDEX.md
docs/WEEK1_COMPLETION.md
docs/RECOVERY_SESSION_INTEGRATION.md
docs/RECOVERY_ENTITIES_ALIGNMENT.md
ALIGN_COHERENCE_VALIDATION_REPORT.md
SEMANTIC_RELATIONSHIP_DIAGRAM.md
FEDERATION_INTEGRATION_BRIDGE.md
tests/
```

**Commit Message**:
```
feat: Integrate SurrealDB persistence and graph module

- Add SurrealDB schema and persistence provider
- Implement semantic graph module for entity relationships
- Add federation integration bridge
- Support session recovery and entity alignment
- Comprehensive architecture analysis and validation
```

---

### Commit 5: "Add manifest adapter and index validation"

**Date**: `2025-11-04 14:02:50`  
**Files**: ~7 files

**Core Code**:
```
src/riff/manifest_adapter.py
src/riff/memory_producer.py
```

**Docs**:
```
MANIFEST_AUTO_REINDEX_GUIDE.md
MANIFEST_ADAPTER_ARCHITECTURE.md
COMPLETION_SUMMARY_2025-11-04.md
TESTING_RESULTS_2025-11-04.md
FINAL_DELIVERY_SUMMARY.md
```

**Commit Message**:
```
feat: Add manifest adapter and automatic index validation

- Implement manifest-based index integrity checking
- Add automatic reindex on file changes
- Add memory producer for session context
- Complete Phase 1 delivery
```

---

### Commit 6: "Implement duplicate tool result handler"

**Date**: `2025-11-08 11:28:13`  
**Files**: ~24 files

**Core Code**:
```
src/riff/classic/
src/riff/visualization/
```

**Test Code**:
```
tests/test_duplicate_handler.py
tests/test_duplicate_tool_results.py
tests/unit/
tests/integration/
tests/TEST_DUPLICATE_TOOL_RESULTS_README.md
tests/DUPLICATE_TESTS_QUICK_START.md
```

**Docs**:
```
CONSOLIDATION_COMPANION.md
DUPLICATE_HANDLER_GUIDE.md
DUPLICATE_HANDLER_IMPLEMENTATION.md
DUPLICATE_HANDLER_ARCHITECTURE.md
DUPLICATE_HANDLER_SUMMARY.md
DUPLICATE_HANDLER_README.md
docs/visualization-module-quickstart.mdx
docs/jsonl-specification.mdx
docs/api-reference.mdx
docs/examples.mdx
docs/INDEX.md
PHASE1_DAY1_COMPLETION.md
PHASE1_DAY3_COMPLETION.md
PHASE1_DAY4_COMPLETION.md
PHASE1_PROGRESS_SUMMARY.md
```

**Commit Message**:
```
feat: Add duplicate tool result handler and visualization

- Implement duplicate detection and resolution strategy
- Add visualization module for semantic insights
- Comprehensive test suite for handler system
- Complete API reference and examples documentation
- Track Phase 1 progress through multiple completion stages
```

---

### Commit 7: "Prepare v2.0.0 binary release and SurrealDB activation"

**Date**: `2025-11-12 13:21:36`  
**Files**: ~13 files

**Code**:
```
src/riff/cli.py (updated)
src/riff/config.py (updated)
src/riff/tui/graph_navigator.py
```

**Binary Release Docs**:
```
BINARY_RELEASE_READINESS.md
BINARY_RELEASE_CHECKLIST.md
BINARY_RELEASE_SUMMARY.txt
BINARY_RELEASE_INDEX.md
```

**SurrealDB Activation**:
```
CURRENT_STATE_SUMMARY.md
SURREALDB_CONSOLIDATION_DISCOVERY.md
SURREALDB_QUICK_REFERENCE.md
PHASE1_SURREALDB_ACTIVATION_COMPLETE.md
PHASE2_TUI_INTEGRATION_COMPLETE.md
SURREALDB_ACTIVATION_SUMMARY.md
uv.lock
```

**Commit Message**:
```
chore: Release v2.0.0 - XDG Architecture + Single Binary Distribution

- Finalize XDG-compliant directory structure
- Complete SurrealDB integration and activation
- Prepare binary distribution for macOS/Linux
- Update graph navigator and CLI entry point
- Mark Phase 1 & 2 completion with SurrealDB live
```

---

## Supplementary Commits (Optional)

For more granular history, consider these additional commits:

### Optional Commit A: "Add stabilization plan and TUI enhancements" 
**Date**: `2025-11-03 23:56:00`
```
STABILIZATION_PLAN.md
TUI_ENHANCEMENT_COMPLETE.md
ENHANCEMENTS_2025-11-03.md
src/riff/search/preview.py
src/riff/__init__.py
src/riff/config.pyi
```

### Optional Commit B: "Document architecture analysis and repair strategies"
**Date**: `2025-11-07 22:17:08`
```
RIFF_REPAIR_THEORY_ANALYSIS.md
DUPLICATE_TOOL_RESULT_IMPLEMENTATION_GUIDE.md
REPAIR_ARCHITECTURE_COMPARISON.md
THEORY_ANALYSIS_SUMMARY.md
RIFF_ANALYSIS_INDEX.md
```

---

## Timeline Verification Checklist

Use these dates to verify commit ordering:

- [ ] Session 1: Sep 14 ≤ timestamps ≤ Sep 19 16:13
- [ ] Session 2: Oct 2 ≤ timestamps ≤ Oct 4 19:48
- [ ] Commit 3: Oct 17 ≤ timestamps ≤ Oct 20 15:01
- [ ] Commit 4: Oct 22 ≤ timestamps ≤ Oct 28 20:16
- [ ] Commit 5: Oct 28 ≤ timestamps ≤ Nov 4 14:02
- [ ] Commit 6: Nov 7 ≤ timestamps ≤ Nov 8 11:28
- [ ] Commit 7: Nov 10 ≤ timestamps ≤ Nov 12 13:21

---

## Important Notes

1. **All 185 files are currently untracked** - They should be added to git first
2. **Use the JSON timeline** (`FILE_TIMELINE.json`) for precise file→timestamp mapping
3. **Author dates should match the latest timestamp in each commit** for historical accuracy
4. **Consider squashing related work** within each session if the granularity gets unwieldy
5. **The 13-day and 11-day gaps** likely represent research/review phases that won't appear in commits

---

## Git Commands to Execute

```bash
# After staging files, use these for accurate back-dating:

# Session 1
git commit --date="2025-09-19T16:13:00" -m "Initial riff-cli foundation and documentation"

# Session 2  
git commit --date="2025-10-04T19:48:05" -m "Add test framework and library scaffolding"

# Session 3 commits
git commit --date="2025-10-20T15:01:24" -m "feat: Add graph navigation and search infrastructure (phase 1)"
git commit --date="2025-10-28T20:16:54" -m "feat: Integrate SurrealDB persistence and graph module"
git commit --date="2025-11-04T14:02:50" -m "feat: Add manifest adapter and automatic index validation"
git commit --date="2025-11-08T11:28:13" -m "feat: Add duplicate tool result handler and visualization"
git commit --date="2025-11-12T13:21:36" -m "chore: Release v2.0.0 - XDG Architecture + Single Binary Distribution"
```

Use `--date=<date>` format: `"YYYY-MM-DDTHH:MM:SS"`

