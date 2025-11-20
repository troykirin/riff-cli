# Commit Archaeology - Directory Structure

```
docs/commit-archaeology/
├── _INDEX.md                                [ENTRY POINT - Read this first]
├── COMMIT_ARCHAEOLOGY_PLAN.md               [MAIN DELIVERABLE]
│
├── phase1-file-timeline/                    [WHEN files were modified]
│   ├── 00_START_HERE_TIMELINE.md
│   ├── TIMELINE_ANALYSIS_README.md
│   ├── FILE_TIMELINE.json
│   ├── FILE_TIMELINE_SUMMARY.md
│   ├── COMMIT_ARCHAEOLOGY_INSIGHTS.md
│   └── COMMIT_STRATEGY.md
│
├── phase2-narrative/                        [WHAT was built and WHY]
│   ├── NARRATIVE_SUMMARY.md
│   ├── PHASE_TO_FEATURES_MAPPING.json
│   ├── NARRATIVE_QUICKSTART.md
│   ├── EXTRACTION_SUMMARY.md
│   └── NARRATIVE_INDEX.md
│
├── phase3-inventory/                        [WHAT CODE was built]
│   ├── CATALOG_INDEX.md
│   ├── MODULE_INVENTORY.md
│   ├── RIFF_CLI_BUILD_SUMMARY.md
│   ├── MODULE_RELATIONSHIPS.md
│   └── FEATURE_GROUPS.json
│
└── phase4-modified-files/                   [WHAT CHANGED in tracked files]
    └── MODIFIED_FILES_ANALYSIS.md
```

## File Count by Phase

| Phase | Purpose | Files | Total Size |
|-------|---------|-------|-----------|
| **Index** | Navigation & entry point | 2 | ~20 KB |
| **Phase 1** | File timeline analysis | 6 | ~71 KB |
| **Phase 2** | Narrative extraction | 5 | ~40 KB |
| **Phase 3** | Module inventory | 5 | ~45 KB |
| **Phase 4** | Modified files analysis | 1 | ~15 KB |
| **TOTAL** | Complete archaeology | 19 | ~191 KB |

## Quick Navigation

**Start here**: `_INDEX.md` (this guides you through everything)
**For execution**: `COMMIT_ARCHAEOLOGY_PLAN.md` (the actual plan to implement)
**For understanding**: `phase2-narrative/NARRATIVE_SUMMARY.md` (the story)
**For architecture**: `phase3-inventory/RIFF_CLI_BUILD_SUMMARY.md` (design overview)
**For verification**: `phase1-file-timeline/FILE_TIMELINE.json` (source data)

## Machine-Readable Data

- `phase1-file-timeline/FILE_TIMELINE.json` - All file timestamps
- `phase2-narrative/PHASE_TO_FEATURES_MAPPING.json` - Feature groupings
- `phase3-inventory/FEATURE_GROUPS.json` - Organized features

These can be parsed by tools/scripts for automation.
