# nabi repo align - Implementation Summary

**Linear Issue**: [NOS-671](https://linear.app/nabia/issue/NOS-671/implement-nabi-repo-align-for-automated-repository-compliance)

**Created**: 2025-10-26

---

## What We Accomplished

### 1. ✅ Created Linear Issue (NOS-671)
- Comprehensive feature description
- Integration points documented
- Clear acceptance criteria
- Priority: High (1)
- Estimate: 8 points

### 2. ✅ Designed Complete Command Structure
- Main commands: `check`, `report`, `fix`, `validate`
- Registry commands: `registry`, `duplicates`, `mark`, `status`, `link`
- Output formats: text, JSON, markdown
- Exit codes for CI/CD integration

### 3. ✅ Identified Validation Rules
From Link Mapper (`~/Sync/docs/.ops/validation/validation_rules.yaml`):
- **XDG Compliance**: 4 rules (CONFIG, CACHE, STATE, DATA)
- **Path Validation**: 2 rules (no hardcoded users, home expansion)
- **Federation Standards**: 3 rules (namespacing, integration, CLI documentation)
- **Exception Handling**: Code blocks, example comments

### 4. ✅ Created Implementation Plan
**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/REPO_ALIGN_IMPLEMENTATION_PLAN.md`

**Contents**:
- Command structure with Rust code examples
- Module architecture (`src/repo/` with validators)
- Data structures (ComplianceReport, Violation, Severity)
- 4-phase implementation roadmap
- Testing strategy with fixtures
- Auto-fix templates
- Dependencies and cargo.toml updates

### 5. ✅ Designed Registry Extension
**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/REPO_ALIGN_REGISTRY_EXTENSION.md`

**Solves**:
- Repository lifecycle tracking (POC → Prototype → Production)
- Duplicate detection with similarity scoring
- Evolution chain visualization
- Path awareness across repo migrations

**New Commands**:
- `nabi repo align registry` - List all registered repos
- `nabi repo align duplicates` - Find similar repos
- `nabi repo align mark <repo> <stage>` - Set lifecycle stage
- `nabi repo align status` - Show repo evolution history
- `nabi repo align link <from> <to>` - Connect evolution chain

---

## Key Features

### Automated Compliance Validation

**Before** (Manual Align Agent Work):
```bash
# Agent deployed to riff-cli
# Scanned 842 files
# Found 6 hardcoded paths, mixed venv patterns
# Generated 5 reports manually
# Time: ~30 minutes of agent work
```

**After** (Automated with nabi repo align):
```bash
nabi repo align check
# Scans repository in <1 second
# Exit code: 2 (errors found)
# Output: Grouped violations by severity

nabi repo align fix --interactive
# Previews fixes
# User confirms
# Auto-applies safe fixes
# Time: <10 seconds
```

### Duplicate Detection & Lifecycle Tracking

**Problem Solved**: "Lost awareness of which version is latest"

```bash
# Detect duplicates across your workspace
nabi repo align duplicates

# Output:
# Group 1: riff-cli
# ├─ Canonical: ~/nabia/platform/tools/riff-cli (production)
# ├─ Duplicate: ~/nabia/tools/riff-cli (archived) - 95% similar
# └─ Duplicate: ~/dev/riff-tui (unknown) - 72% similar

# Mark lifecycle stages
nabi repo align mark ~/nabia/tools/riff-cli archived
nabi repo align mark ~/nabia/platform/tools/riff-cli production

# Show evolution history
nabi repo align status --history

# Evolution Chain:
#   1. ~/dev/riff-tui (poc, archived 2025-08-15)
#   2. ~/nabia/tools/riff-cli (prototype, archived 2025-10-25)
#   3. ~/nabia/platform/tools/riff-cli (production) ← YOU ARE HERE
```

### CI/CD Integration

```yaml
# .github/workflows/compliance.yml
- name: Validate Repository Compliance
  run: nabi repo align check --strict --format json
  # Exit 0 = pass, 2 = fail → blocks merge
```

```bash
# .git/hooks/pre-commit
#!/bin/bash
nabi repo align check --strict || {
    echo "❌ Compliance check failed"
    exit 1
}
```

---

## Implementation Phases

### Phase 1: Foundation (1-2 weeks)
**Goal**: Read-only validation with exit codes

**Deliverables**:
- Command structure in `~/nabia/core/nabi-cli/src/main.rs`
- `src/repo/check.rs` implementation
- XDG and hardcoded path validators
- Text output format
- Exit code compliance for CI/CD

**Testing**:
```bash
nabi repo align check ~/nabia/core/nabi-cli
# Should pass (exit 0)

nabi repo align check ~/nabia/tools/legacy-tool
# Should fail with violations (exit 2)
```

### Phase 2: Reporting (1-2 weeks)
**Goal**: Comprehensive reports (human + machine readable)

**Deliverables**:
- `src/repo/report.rs` implementation
- Markdown report generation
- JSON output for tooling
- Grouped violations by file/severity
- Registry listing command

**Testing**:
```bash
nabi repo align report --output COMPLIANCE_REPORT.md
nabi repo align registry --format table
nabi repo align validate --standard xdg
```

### Phase 3: Auto-Remediation (1-2 weeks)
**Goal**: Safe automated fixes

**Deliverables**:
- `src/repo/fix.rs` implementation
- Dry-run preview mode
- Interactive confirmation
- Automatic backup creation
- Common fix templates (path expansion, XDG injection)

**Testing**:
```bash
nabi repo align fix --dry-run
# Preview changes

nabi repo align fix --interactive
# Confirm each fix

nabi repo align fix --yes
# Auto-apply safe fixes
```

### Phase 4: Registry & Duplicates (1-2 weeks)
**Goal**: Repository lifecycle tracking

**Deliverables**:
- Duplicate detection algorithm (Levenshtein + content similarity)
- Registry index (`~/.local/state/nabi/manifests/registry.json`)
- Lifecycle marking (POC, Prototype, Production, Archived)
- Evolution chain linking
- Migration suggestions for archived repo references

**Testing**:
```bash
nabi repo align duplicates --threshold 0.7
nabi repo align mark ~/old/repo archived
nabi repo align link ~/poc ~/prototype --relation evolution
nabi repo align status --history
```

---

## Architecture

### Module Structure
```
~/nabia/core/nabi-cli/src/
├── main.rs                      # Command definitions
├── repo/
│   ├── mod.rs                   # Public API
│   ├── check.rs                 # Compliance checking
│   ├── report.rs                # Report generation
│   ├── fix.rs                   # Auto-remediation
│   ├── validate.rs              # Standard validation
│   ├── registry.rs              # Registry management
│   ├── duplicates.rs            # Duplicate detection
│   └── validators/
│       ├── xdg.rs               # XDG compliance
│       ├── venv.rs              # Venv location
│       ├── paths.rs             # Hardcoded paths
│       ├── federation.rs        # Federation patterns
│       └── docs.rs              # Documentation structure
```

### Reusable Components

**From Existing Codebase**:
- `src/paths.rs` - XDG path utilities (NabiPaths struct)
- Manifest system - SHA256 validation, drift detection
- Link mapper rules - `~/Sync/docs/.ops/validation/validation_rules.yaml`

**New Dependencies**:
```toml
[dependencies]
regex = "1.10"           # Pattern matching
walkdir = "2.4"          # File tree walking
serde_yaml = "0.9"       # YAML parsing (validation rules)
toml = "0.8"             # TOML parsing (config)
```

---

## Documentation Created

1. **REPO_ALIGN_IMPLEMENTATION_PLAN.md** (450+ lines)
   - Complete command structure
   - Validation rules reference
   - Implementation architecture
   - Testing strategy
   - Dependencies and cargo.toml

2. **REPO_ALIGN_REGISTRY_EXTENSION.md** (550+ lines)
   - Registry integration design
   - Duplicate detection algorithm
   - Lifecycle tracking commands
   - Evolution chain linking
   - Enhanced manifest schema

3. **NABI_REPO_ALIGN_SUMMARY.md** (this document)
   - Executive summary
   - Key features overview
   - Implementation roadmap
   - Quick reference

---

## Benefits

### For Users
✅ **Speed**: Instant validation (<1s) vs agent deployment (minutes)
✅ **Consistency**: Same standards across all repos
✅ **Proactive**: Catch drift before commits
✅ **Clarity**: Know which repo version is current
✅ **Automation**: CI/CD integration out of box

### For Agents
✅ **Focus**: align agent does semantic work, not mechanical validation
✅ **Efficiency**: No need to deploy agents for compliance checks
✅ **Reliability**: Consistent validation results
✅ **Context**: Clear lifecycle stage for each repo

### For Federation
✅ **Standards Enforcement**: Automated XDG compliance
✅ **Drift Prevention**: Proactive validation at hook boundaries
✅ **Registry Awareness**: Central index of all repos
✅ **Evolution Tracking**: Historical context for repo migrations

---

## Validation Rules Reference

### XDG Compliance
| Rule | Pattern | Description |
|------|---------|-------------|
| xdg_config | `$XDG_CONFIG_HOME` | Config paths must use XDG variable |
| xdg_cache | `$XDG_CACHE_HOME` | Cache paths must use XDG variable |
| xdg_state | `$XDG_STATE_HOME` | State paths must use XDG variable |
| xdg_data | `$XDG_DATA_HOME` | Data paths must use XDG variable |

### Path Validation
| Rule | Pattern | Description |
|------|---------|-------------|
| no_hardcoded_users | `/Users/tryk\|/home/[a-z]+` | No hardcoded user paths |
| home_expansion | `$HOME\|~/` | Use $HOME or ~/ for home directory |

### Virtual Environment
| Rule | Pattern | Description |
|------|---------|-------------|
| venv_location | `~/.nabi/venvs/{tool}/` | Venv must be in runtime location |
| no_project_venv | `.venv/` | No project-local .venv/ |

### Federation Standards
| Rule | Pattern | Description |
|------|---------|-------------|
| tool_namespace | `/nabi/{tool}/` | Tool-specific paths namespaced |
| federation_integration | `federation\|Federation` | Must mention federation |
| nabi_cli_documented | `nabi (exec\|list\|resolve)` | nabi-cli integration documented |

---

## Example Workflows

### Daily Development
```bash
# Morning: Check compliance before starting work
nabi repo align check

# During: Fix issues as you go
nabi repo align fix --interactive

# Before commit: Validate (via pre-commit hook)
git commit -m "feat: new feature"
# → nabi repo align check --strict runs automatically
```

### New Repository Setup
```bash
# Initialize repository with production standards
nabi repo align mark . production

# Validate compliance
nabi repo align check --strict

# Generate manifest
nabi docs manifest generate .

# Add to registry
# (automatic on first check)
```

### Repository Evolution
```bash
# Starting new version
nabi repo align mark ~/old/repo archived \
  --reason "Superseded by new implementation"

nabi repo align mark ~/new/repo production \
  --reason "Consolidated production version"

nabi repo align link ~/old/repo ~/new/repo --relation evolution

# Check for references to old paths
nabi repo align check --archived-refs
```

### CI/CD Pipeline
```yaml
name: Compliance Check
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install nabi CLI
        run: |
          curl -fsSL https://get.nabia.ai | sh
      - name: Validate Compliance
        run: nabi repo align check --strict --format json
```

---

## Next Steps

### Immediate (Week 1)
1. ✅ Linear issue created (NOS-671)
2. ✅ Design documents complete
3. ⏭️ Begin Phase 1 implementation
   - Add command structure to `~/nabia/core/nabi-cli/src/main.rs`
   - Create `src/repo/` module
   - Implement XDG validator (reuse paths.rs)

### Short-term (Weeks 2-4)
4. Phase 2: Reporting implementation
5. Phase 3: Auto-remediation
6. Testing with riff-cli and nabi-cli repos

### Medium-term (Weeks 5-8)
7. Phase 4: Registry and duplicate detection
8. Git hook integration
9. GitHub Actions workflow examples
10. Documentation updates

---

## Success Metrics

### Phase 1
- [ ] Command structure compiles
- [ ] XDG validator detects hardcoded paths
- [ ] Exit codes correct for CI/CD
- [ ] <1s scan time for typical repo
- [ ] 80%+ test coverage

### Phase 2
- [ ] Markdown reports generated
- [ ] JSON output parseable by tools
- [ ] Grouped violations readable
- [ ] Registry lists all manifests

### Phase 3
- [ ] Dry-run previews accurate
- [ ] Interactive mode UX smooth
- [ ] Safe fixes auto-applied correctly
- [ ] Backup creation reliable

### Phase 4
- [ ] Duplicate detection <5% false positives
- [ ] Evolution chains visualized
- [ ] Lifecycle marking persistent
- [ ] Migration suggestions accurate

---

## References

- **Linear Issue**: https://linear.app/nabia/issue/NOS-671
- **Implementation Plan**: `./REPO_ALIGN_IMPLEMENTATION_PLAN.md`
- **Registry Extension**: `./REPO_ALIGN_REGISTRY_EXTENSION.md`
- **Validation Rules**: `~/Sync/docs/.ops/validation/validation_rules.yaml`
- **Manifest Schema**: `~/.local/state/nabi/manifests/SCHEMA.md`
- **nabi-cli Source**: `~/nabia/core/nabi-cli/`

---

## Questions & Answers

**Q: Why not just use the align agent for all validation?**
A: The align agent should focus on **semantic resonance** (architecture, documentation quality) rather than mechanical validation that scripts can handle. This frees agent capacity for higher-value work.

**Q: How does this integrate with the existing manifest system?**
A: `nabi repo align` builds on top of the manifest system (`~/.local/state/nabi/manifests/`), adding compliance rules and duplicate detection. It reuses SHA256 validation logic and extends manifests with lifecycle metadata.

**Q: What about repos that don't have manifests yet?**
A: First run of `nabi repo align check` will auto-generate a manifest using `nabi docs manifest generate`. The registry is populated automatically.

**Q: How does duplicate detection handle false positives?**
A: The similarity threshold (default 0.7) is tunable via `--threshold`. Users can manually mark repos as distinct using `nabi repo align mark`. Evolution chains help distinguish intentional forks from duplicates.

**Q: Can I use this in pre-commit hooks without blocking fast commits?**
A: Yes! The check runs in <1s for typical repos. For large repos, use `--quick` mode (scans only staged files) or run in CI/CD instead of pre-commit.

---

**Status**: Design Complete ✅
**Next Action**: Begin Phase 1 implementation in nabi-cli
**Time Estimate**: 6-8 weeks total (4 phases)
**Priority**: High (prevents federation drift proactively)
