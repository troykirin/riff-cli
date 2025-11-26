# nabi repo align - Quick Start Card

**Linear Issue**: [NOS-671](https://linear.app/nabia/issue/NOS-671) | **Status**: Design Complete ✅

---

## What is it?

Automated repository compliance validation that:
- Detects XDG violations, hardcoded paths, wrong venv locations
- Finds duplicate repos across POC → Prototype → Production cycles
- Tracks repository lifecycle and evolution chains
- Prevents federation drift **before commits**

---

## Quick Commands

```bash
# Check current repo compliance
nabi repo align check

# Generate detailed report
nabi repo align report --output COMPLIANCE_REPORT.md

# Fix issues interactively
nabi repo align fix --interactive

# List all registered repos
nabi repo align registry

# Find duplicate repos
nabi repo align duplicates

# Show repo evolution history
nabi repo align status --history

# Mark repo lifecycle stage
nabi repo align mark . production
```

---

## The Problem We're Solving

**Before** (Manual with align agent):
- align agent deployed for 30+ minutes
- Scans files manually
- Generates reports one at a time
- Agent capacity wasted on mechanical validation

**After** (Automated with nabi repo align):
- Instant validation (<1 second)
- Automated reports
- CI/CD integration
- align agent focuses on **semantic work**

**User Pain Point**:
> "I've lost awareness of which repo version is latest. POCs became prototypes, prototypes evolved, and now I don't know which path is production."

**Solution**: Lifecycle tracking + duplicate detection + evolution chains

---

## Documentation

| Document | Purpose | Lines |
|----------|---------|-------|
| **NABI_REPO_ALIGN_SUMMARY.md** | Executive summary, overview | 450+ |
| **REPO_ALIGN_IMPLEMENTATION_PLAN.md** | Technical implementation details | 450+ |
| **REPO_ALIGN_REGISTRY_EXTENSION.md** | Duplicate detection, lifecycle tracking | 550+ |
| **REPO_ALIGN_QUICK_START.md** | This document | Quick reference |

**All located in**: `/Users/tryk/nabia/platform/tools/riff-cli/`

---

## Implementation Status

### ✅ Completed
- [x] Linear issue created (NOS-671)
- [x] Command structure designed
- [x] Validation rules identified
- [x] Implementation plan documented
- [x] Registry extension designed
- [x] Testing strategy defined

### ⏭️ Next Steps
1. Create `src/repo/` module in `~/nabia/core/nabi-cli/`
2. Add command definitions to `main.rs`
3. Implement XDG validator (Phase 1)
4. Write unit tests
5. Test with riff-cli repository

---

## Key Features

### 1. Compliance Validation
```bash
nabi repo align check
# ❌ Hardcoded path: /Users/tryk/nabia (line 42)
# ❌ Project .venv detected (use ~/.nabi/venvs/)
# ❌ Missing XDG variables in config
# Exit code: 2 (errors detected)
```

### 2. Duplicate Detection
```bash
nabi repo align duplicates
# Group 1: riff-cli
# ├─ Canonical: ~/nabia/platform/tools/riff-cli (production)
# ├─ Duplicate: ~/nabia/tools/riff-cli (archived) - 95% similar
# └─ Duplicate: ~/dev/riff-tui (unknown) - 72% similar
```

### 3. Lifecycle Tracking
```bash
nabi repo align status --history
# Evolution Chain:
#   1. ~/dev/riff-tui (poc, archived 2025-08-15)
#   2. ~/nabia/tools/riff-cli (prototype, archived 2025-10-25)
#   3. ~/nabia/platform/tools/riff-cli (production) ← YOU ARE HERE
```

### 4. Auto-Remediation
```bash
nabi repo align fix --interactive
# File: README.md:42
#   Before: /Users/tryk/nabia
#   After:  ~/nabia
# Apply fix? [y/N]: y
# ✓ Fixed (backed up to README.md.bak)
```

---

## Validation Rules

### XDG Compliance
- ✅ Use `$XDG_CONFIG_HOME`, not `~/.config`
- ✅ Use `$XDG_STATE_HOME`, not `~/.local/state`
- ✅ Use `$XDG_CACHE_HOME`, not `~/.cache`
- ✅ Use `$XDG_DATA_HOME`, not `~/.local/share`

### Path Standards
- ✅ Use `~/` not `/Users/tryk/`
- ✅ Use `$HOME` not hardcoded user paths
- ✅ Venv at `~/.nabi/venvs/{tool}/` not `.venv/`

### Federation Standards
- ✅ Tool paths under `/nabi/{tool}/` namespace
- ✅ Mention federation integration in docs
- ✅ Document nabi-cli usage patterns

---

## CI/CD Integration

### GitHub Actions
```yaml
- name: Validate Compliance
  run: nabi repo align check --strict --format json
```

### Pre-commit Hook
```bash
nabi repo align check --strict || exit 1
```

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1** | 1-2 weeks | `check` command, XDG validator, exit codes |
| **Phase 2** | 1-2 weeks | `report` command, JSON/Markdown output, registry list |
| **Phase 3** | 1-2 weeks | `fix` command, interactive mode, backups |
| **Phase 4** | 1-2 weeks | Duplicate detection, lifecycle tracking, evolution chains |

**Total**: 6-8 weeks

---

## Example Workflow

```bash
# 1. Check compliance
cd ~/nabia/platform/tools/riff-cli
nabi repo align check
# ❌ 6 violations found

# 2. Generate report
nabi repo align report --output COMPLIANCE.md
# Review violations in markdown

# 3. Fix issues
nabi repo align fix --interactive
# Confirm each fix, apply changes

# 4. Verify fix
nabi repo align check
# ✓ All checks passed!

# 5. Check for duplicates
nabi repo align duplicates
# Found archived version at ~/nabia/tools/riff-cli

# 6. Mark lifecycle
nabi repo align mark ~/nabia/tools/riff-cli archived
nabi repo align mark . production

# 7. Link evolution
nabi repo align link ~/nabia/tools/riff-cli . --relation evolution

# 8. View history
nabi repo align status --history
# Shows full evolution chain
```

---

## When to Use

### Use `nabi repo align` when:
- ✅ Starting a new repository (ensure standards from day 1)
- ✅ Before committing (pre-commit hook validation)
- ✅ In CI/CD pipeline (block merges on violations)
- ✅ After repo migration (validate new paths)
- ✅ Confused about repo versions (find duplicates, check evolution)
- ✅ Preparing for production (final compliance check)

### Use `align agent` when:
- ✅ Analyzing semantic coherence (documentation quality)
- ✅ Architectural decision validation
- ✅ Cross-system integration analysis
- ✅ Complex refactoring guidance

**Key Insight**: Let machines do mechanical validation, let agents do semantic analysis.

---

## Current Status

**Design**: ✅ Complete
**Linear Issue**: ✅ Created (NOS-671)
**Documentation**: ✅ Complete (1,450+ lines)
**Implementation**: ⏭️ Ready to start (Phase 1)

**Next Action**: Begin implementation in `~/nabia/core/nabi-cli/`

---

## Contact & References

- **Linear**: [NOS-671](https://linear.app/nabia/issue/NOS-671)
- **Docs**: `/Users/tryk/nabia/platform/tools/riff-cli/REPO_ALIGN_*.md`
- **Implementation**: `~/nabia/core/nabi-cli/src/repo/`
- **Validation Rules**: `~/Sync/docs/.ops/validation/validation_rules.yaml`

---

**Version**: 1.0.0 | **Date**: 2025-10-26 | **Status**: Design Complete ✅
