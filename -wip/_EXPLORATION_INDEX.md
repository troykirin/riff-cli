# Riff CLI - Exploration Documentation Index

This index documents the thorough exploration of the riff-cli project structure, architecture, and CLI implementation.

## Generated Documents

This exploration created three comprehensive documents in the project root:

### 1. `/Users/tryk/nabia/tools/riff-cli/_KEY_FINDINGS_SUMMARY.md`
**Purpose**: Executive summary of findings  
**Audience**: Anyone needing quick overview  
**Contains**:
- Project overview and status
- Main files of interest with absolute paths
- Command structure (all 9 commands)
- Flag analysis (no conflicts found)
- Integration status with nabi-python
- Quick command reference

**Read this first** for a quick understanding.

---

### 2. `/Users/tryk/nabia/tools/riff-cli/_RIFF_CLI_ARCHITECTURE_EXPLORATION.md`
**Purpose**: Detailed technical exploration  
**Audience**: Developers implementing integrations  
**Contains**:
- Complete directory structure with file descriptions
- Detailed CLI command definitions
- Integration architecture (riff-cli vs nabi-python)
- Command routing flow diagram
- Core command implementations
- Architectural patterns and extension points
- Phase 6B (SurrealDB) integration details
- Implementation files cross-reference

**Read this** for deep technical understanding.

---

### 3. `/Users/tryk/nabia/tools/riff-cli/_CLI_ARCHITECTURE_DIAGRAM.txt`
**Purpose**: Visual reference and quick lookup  
**Audience**: Anyone wanting visual representation  
**Contains**:
- Source code organization (ASCII tree)
- Command execution flow (ASCII diagram)
- Flag analysis reference table
- Key design decisions
- nabi integration status
- Project timeline
- Key files at-a-glance

**Reference this** for visual understanding and CLI lookup.

---

## Key Findings

### Project Type
- **Not Rust**: Python 3.13+ CLI application
- **Framework**: argparse (standard library)
- **Package Manager**: uv

### Main Entry Point
```
/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py
  ├── build_parser()  - Defines 9 subcommands
  ├── main()         - Entry point dispatcher
  └── cmd_*()        - Implementation functions
```

### CLI Commands (9 Total)
- `search` - Semantic search
- `browse` - Interactive browser
- `graph` - DAG visualization
- `sync:surrealdb` - Phase 6B persistence
- `scan`, `fix`, `tui`, `graph-classic` - Classic commands
- Global: `--qdrant-url`

### Flag Conflict Status
**No `-f` duplicate conflicts found** - all flags are unique per command

### Integration with nabi
- **Current**: Independent, fully functional
- **Status**: Not yet wired in nabi-python script
- **Next Step**: Add "riff" case in nabi-python router

---

## File Locations (Absolute Paths)

### Critical Files
1. `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py` - MAIN ENTRY POINT
2. `/Users/tryk/nabia/tools/riff-cli/README.md` - Quick start guide
3. `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md` - System design

### Backend Modules
- `/Users/tryk/nabia/tools/riff-cli/src/riff/search/qdrant.py`
- `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/dag.py`
- `/Users/tryk/nabia/tools/riff-cli/src/riff/surrealdb/storage.py`

### Configuration
- `/Users/tryk/nabia/tools/riff-cli/pyproject.toml` - Dependencies
- `/Users/tryk/nabia/tools/riff-cli/Taskfile.yml` - Task automation

### Documentation
- `/Users/tryk/nabia/tools/riff-cli/docs/` - 31 markdown files
- `/Users/tryk/nabia/tools/riff-cli/docs/PHASE_6B_*.md` - Persistence details
- `/Users/tryk/nabia/tools/riff-cli/docs/PHASE_6C_*.md` - Federation planning

---

## Exploration Methodology

The exploration followed a systematic approach:

1. ✅ **Initial Discovery**
   - Located project root
   - Identified Python, not Rust implementation
   - Found entry point (cli.py)

2. ✅ **CLI Structure Analysis**
   - Read build_parser() function (lines 479-575)
   - Documented all 9 subcommands
   - Analyzed argument definitions

3. ✅ **Flag Conflict Investigation**
   - Searched entire codebase for `-f` usage
   - Analyzed each command's flags
   - Verified no duplicate conflicts

4. ✅ **Integration Review**
   - Examined nabi-python script
   - Identified current routing
   - Documented integration points

5. ✅ **Architecture Documentation**
   - Created directory maps
   - Documented data flow
   - Identified modules and relationships

---

## For Different Audiences

### If you want to...

**Understand the overall architecture**
→ Read: `_RIFF_CLI_ARCHITECTURE_EXPLORATION.md`

**Quick reference on commands and flags**
→ Read: `_KEY_FINDINGS_SUMMARY.md`

**Visual representation of structure**
→ Read: `_CLI_ARCHITECTURE_DIAGRAM.txt`

**Deep implementation details**
→ Read: `/Users/tryk/nabia/tools/riff-cli/docs/ARCHITECTURE.md`

**Integration with nabi-cli**
→ Read: `_KEY_FINDINGS_SUMMARY.md` (Integration section)

**Quick start with examples**
→ Read: `/Users/tryk/nabia/tools/riff-cli/README.md`

---

## Verification Checklist

All findings have been verified through:

- [x] Direct code inspection (cli.py)
- [x] Grep searches across entire codebase
- [x] File system exploration
- [x] nabi-python integration review
- [x] Cross-reference with documentation
- [x] Verification of absolute file paths

---

## Next Steps for Integration

1. **Review** this exploration documentation
2. **Study** `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py`
3. **Understand** the three-layer architecture
4. **Plan** nabi-python integration
5. **Implement** routing in nabi-python script
6. **Test** via `nabi exec riff ...`

---

## Quick Command Examples

```bash
# Direct usage (works now)
riff search "memory architecture"
riff graph SESSION_UUID
riff sync:surrealdb SESSION_UUID

# Future nabi integration
nabi exec riff search "memory architecture"
nabi exec riff graph SESSION_UUID
```

---

**Exploration Date**: 2025-10-23  
**Status**: Complete and verified  
**Next Review**: When riff-cli architecture changes

