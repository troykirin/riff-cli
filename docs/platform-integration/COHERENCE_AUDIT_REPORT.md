# Riff-CLI Federation Alignment Audit Report

**Status**: DRIFT_DETECTED (HIGH SEVERITY)
**Scope**: Virtual Environment Architecture & Path Coherence
**Timestamp**: 2025-10-26
**Auditor**: Semantic Custodian (ALIGN)

---

## Executive Summary

The riff-cli repository contains **mixed architectural signals** regarding virtual environment location and Python tool invocation. While `.hookrc` correctly implements the federation standard (`~/.nabi/venvs/riff-cli/`), several documentation files and configuration references still contain the **legacy `.venv/` pattern** and **hardcoded paths**.

**Impact**: Moderate - The actual runtime is correctly configured, but documentation could mislead developers and violate XDG compliance principles across the federation.

---

## Findings

### 1. Virtual Environment Location - MIXED STATE

**Status**: PARTIAL ALIGNMENT

#### ✅ Correct (Federation-Compliant)
- **`.hookrc`** (lines 9-22): Correctly references `~/.nabi/venvs/riff-cli/`
- **`phase3_verification.sh`** (line 22): Correctly checks for `~/.nabi/venvs/riff-cli`
- **`docs/development.md`** (line 82): Documents correct location as `~/.nabi/venvs/riff-cli/`

#### ❌ Incorrect (Legacy Pattern)
- **`.venv/`**: Directory exists at project root (legacy artifact)
- **`PLATFORM_INTEGRATION.md`** (lines 62-63):
  - Line 62: `python3.13 -m venv .venv` (uses local venv)
  - Line 63: `source .venv/bin/activate` (references local activation)
- **`docs/RIFF_UNIFIED.md`** (lines 73-76):
  - Line 73: `uv venv` (creates local venv)
  - Line 76: `source .venv/bin/activate` (references local activation)

### 2. Hardcoded Paths - VIOLATIONS DETECTED

**Status**: DRIFT CONFIRMED

#### Hardcoded `/Users/tryk` Paths
1. **`docs/development.md`** (line 14):
   - Current: `cd /Users/tryk/nabia/tools/riff-cli`
   - Should: `cd ~/nabia/platform/tools/riff-cli` OR use relative navigation

2. **`START_HERE_NABI_EXPLORATION.md`** (multiple instances):
   - `/Users/tryk/nabia/tools/riff-cli/` appears multiple times
   - Context: These are exploration/documentation files, should still follow XDG

3. **`ROUTING_PATTERN_GUIDE.md`** (multiple instances):
   - `/Users/tryk/nabia/core/nabi-cli/src/main.rs`
   - `/Users/tryk/nabia/tools/nabi-python`
   - `/Users/tryk/nabia/tools/riff-cli/PHASE3_COMPLETION_REPORT.md`
   - `/Users/tryk/nabia/core/nabi-cli/src/main.rs`
   - Context: Pattern guide, should use relative or `~` expansion

### 3. Python Invocation Pattern - VIOLATIONS DETECTED

**Status**: DRIFT CONFIRMED

#### Direct Python/Python3 Usage (Should Use `uv`)
1. **`PLATFORM_INTEGRATION.md`**:
   - Line 62: `python3.13 -m venv .venv`
   - Line 309: `python -m riff --version`
   - Line 314: `python -m riff search "test"`
   - Line 318: `alias riff="python -m riff"`
   - Line 333: `python --version`

2. **`docs/RIFF_UNIFIED.md`**:
   - Line 73: `uv venv` (correct use of uv)
   - Line 76: `source .venv/bin/activate` (but still targets .venv)

3. **`manifest.toml`**:
   - Line 35: `invocation = "python -m riff"` (should not hardcode python)

4. **`.hookrc`**:
   - Line 19: `python3 -m venv` (should use `uv`, but this is acceptable as bootstrap)
   - Line 60: `python --version` (informational, acceptable)

### 4. Documentation Coherence - ISSUES FOUND

**Status**: MODERATE

#### Issues
1. Multiple documents reference outdated project location:
   - Old: `~/nabia/tools/riff-cli`
   - New: `~/nabia/platform/tools/riff-cli`
   - Files affected:
     - `docs/development.md` (line 14)
     - `PLATFORM_INTEGRATION.md` (line 47, 378, 381)

2. Inconsistent virtual environment guidance:
   - Some docs say use `.venv/`
   - Some docs say use `~/.nabi/venvs/riff-cli/`
   - Some docs provide "Option 1, 2, 3" with mixed approaches

3. Missing XDG compliance rationale in some newer docs

#### Affected Files
- `PLATFORM_INTEGRATION.md` - Options 1-2 contradict Option 3
- `docs/RIFF_UNIFIED.md` - Setup section uses `.venv/`
- `manifest.toml` - Invocation pattern hardcodes `python`

### 5. Path Coherence Violations - ARCHITECTURE DRIFT

**Status**: CRITICAL (Principle Violation)

#### Violation: Relative vs Absolute Path Strategies
The federation standard states:
- **Config**: Use `~/.config/nabi/...` (XDG_CONFIG_HOME)
- **Runtime**: Use `~/.nabi/...` (XDG_DATA_HOME / XDG_STATE_HOME)
- **Virtual Environments**: Use `~/.nabi/venvs/<tool-name>/`
- **Never**: Hardcoded `/Users/tryk/...` paths

#### Evidence of Violation
```toml
# manifest.toml - Line 35
invocation = "python -m riff"  # ❌ Hardcodes python executable

# ✅ Should be:
invocation = "~/.nabi/venvs/riff-cli/bin/python -m riff"
# OR rely on PATH with proper shim registration
```

### 6. .gitignore Configuration - PARTIAL ALIGNMENT

**Status**: ACCEPTABLE

The `.gitignore` correctly ignores `.venv/` on line 9, which is good. However, it doesn't explicitly ignore the project-root `.venv` which should ideally be removed entirely.

---

## Impact Assessment

### Severity: HIGH

**Why**:
1. **Principle Violation**: Hardcoded paths violate XDG Base Directory Specification (NORTH STAR)
2. **Federation Inconsistency**: Documentation contradicts actual runtime setup
3. **Developer Confusion**: Multiple setup guides with conflicting recommendations
4. **Portability Risk**: Hardcoded `/Users/tryk` paths won't work on other machines

### Affected Areas
- ✅ **Runtime**: Correctly configured via `.hookrc`
- ❌ **Documentation**: Contains legacy patterns and hardcoded paths
- ❌ **Configuration**: `manifest.toml` invocation string non-portable
- ⚠️ **Legacy Artifacts**: `.venv/` directory still exists at project root

### Downstream Impact
- Developers following `PLATFORM_INTEGRATION.md` will create `.venv/` instead of using federation standard
- Hardcoded paths in ROUTING_PATTERN_GUIDE.md break on non-tryk machines
- Federation tools relying on manifest.toml invocation will fail

---

## Validation Against Federation Standards

### XDG Compliance Checklist

| Principle | Status | Evidence |
|-----------|--------|----------|
| Config in `~/.config/nabi/` | ✅ | `.hookrc` uses `$NABI_RUNTIME_DIR` |
| Runtime in `~/.nabi/` | ✅ | `RIFF_VENV="$NABI_VENV_ROOT/riff-cli"` |
| No hardcoded `/Users/tryk` paths | ❌ | Found in PLATFORM_INTEGRATION.md, ROUTING_PATTERN_GUIDE.md |
| Virtual envs at `~/.nabi/venvs/` | ✅ | `.hookrc` line 11 correct |
| Use `uv` not `python3`/`python` | ⚠️ | Mixed: some docs use `uv`, others use `python` |
| Portable across platforms | ❌ | Hardcoded paths break on macOS/WSL/Linux/RPi |

### Schema-Driven Transformation (Universal Pattern)

The aura system expects:
```
Schema (Config): ~/.config/nabi/auras/architect.toml
       ↓ transformation
Derived State: ~/.nabi/venvs/riff-cli/
       ↓
Manifest: manifest.toml (should reference derived state, not schema)
```

**Finding**: `manifest.toml` invocation pattern should reference the derived state location, not assume `python` in PATH.

---

## Detailed Findings by File

### File 1: `PLATFORM_INTEGRATION.md`

**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/PLATFORM_INTEGRATION.md`

**Issues**:
1. **Line 14**: Hardcoded path `/Users/tryk/nabia/tools/riff-cli`
   - Should be: `~/nabia/platform/tools/riff-cli` or `.` (relative)

2. **Lines 62-63**: Uses `.venv/` instead of `~/.nabi/venvs/riff-cli/`
   ```bash
   # Current (WRONG)
   python3.13 -m venv .venv
   source .venv/bin/activate

   # Should be (CORRECT)
   python3 -m venv ~/.nabi/venvs/riff-cli
   source ~/.nabi/venvs/riff-cli/bin/activate
   ```

3. **Lines 309, 314, 318, 333**: Use `python -m` instead of venv-aware invocation
   - Currently assumes `python` in PATH
   - Should verify venv location first

4. **Line 378, 381**: Outdated path references to `~/nabia/tools/riff-cli`
   - Should reference `~/nabia/platform/tools/riff-cli`

**Severity**: HIGH - Setup guide is authoritative for new developers

---

### File 2: `docs/RIFF_UNIFIED.md`

**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/docs/RIFF_UNIFIED.md`

**Issues**:
1. **Lines 73-76**: Outdated setup using `.venv/`
   ```bash
   # Current (WRONG)
   uv venv
   source .venv/bin/activate

   # Should be (CORRECT)
   uv venv ~/.nabi/venvs/riff-cli
   source ~/.nabi/venvs/riff-cli/bin/activate
   ```

**Severity**: MEDIUM - This is newer unified doc, easily corrected

---

### File 3: `docs/development.md`

**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/docs/development.md`

**Status**: CORRECT except one issue

**Issue**:
1. **Line 14**: Hardcoded path in Quick Start example
   ```bash
   # Current (WRONG)
   cd /Users/tryk/nabia/tools/riff-cli

   # Should be (CORRECT)
   cd ~/nabia/platform/tools/riff-cli
   ```

**Notes**:
- Line 82 correctly documents `~/.nabi/venvs/riff-cli/` location
- Overall development guide is well-aligned

**Severity**: LOW - Single path fix needed

---

### File 4: `manifest.toml`

**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/manifest.toml`

**Issues**:
1. **Line 35**: Invocation assumes `python` in PATH
   ```toml
   # Current (FRAGILE)
   invocation = "python -m riff"

   # Should reference federation venv
   invocation = "~/.nabi/venvs/riff-cli/bin/python -m riff"
   # OR use nabi CLI shim:
   invocation = "nabi exec riff"
   ```

**Severity**: HIGH - Manifest is the contract between tool and federation

---

### File 5: `.hookrc`

**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/.hookrc`

**Status**: ✅ CORRECT

Lines 9-22 properly implement federation venv pattern. This is the gold standard.

---

### File 6: `Taskfile.yml`

**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/Taskfile.yml`

**Status**: ✅ CORRECT

Uses `uv run` throughout, which properly respects the venv. Line 171 correctly symlinks to venv binary.

---

### File 7: `phase3_verification.sh`

**Location**: `/Users/tryk/nabia/platform/tools/riff-cli/phase3_verification.sh`

**Status**: ✅ CORRECT

Line 22 correctly checks for `~/.nabi/venvs/riff-cli` location.

---

### File 8: `ROUTING_PATTERN_GUIDE.md`, `START_HERE_*` files

**Status**: DOCUMENTATION/EXPLORATION FILES

These contain hardcoded paths for historical/reference purposes. Should be migrated to standard paths but are lower priority than active documentation.

---

## Remediation Plan

### Phase 1: Critical Path Fixes (IMMEDIATE)

**Target**: Align with federation standard, unblock new developers

1. **Update `PLATFORM_INTEGRATION.md`**:
   - Change all `.venv/` references to `~/.nabi/venvs/riff-cli/`
   - Update hardcoded `/Users/tryk` paths to use `~` expansion
   - Update Option 2 to show correct venv location
   - Update example commands to use venv-aware paths

2. **Update `manifest.toml`**:
   - Change invocation to use venv-aware path or nabi CLI
   - Reference `~/.nabi/venvs/riff-cli/bin/python` directly

3. **Update `docs/RIFF_UNIFIED.md`**:
   - Correct setup section to use `~/.nabi/venvs/riff-cli/`

4. **Update `docs/development.md`**:
   - Fix hardcoded path on line 14

### Phase 2: Documentation Cleanup (FOLLOW-UP)

**Target**: Consistency and clarity across all documentation

1. Add XDG compliance note to all setup sections
2. Consolidate multiple setup options into single clear path
3. Update all references to `/Users/tryk` paths to `~` expansion
4. Add federation compliance badge to updated docs

### Phase 3: Artifact Cleanup (OPTIONAL)

**Target**: Remove legacy artifacts

1. Remove `.venv/` directory from project root (once verified not needed)
2. Update `.gitignore` to document XDG compliance rationale

---

## Expected Outcomes

After remediation:

- ✅ All documentation references `~/.nabi/venvs/riff-cli/`
- ✅ No hardcoded `/Users/tryk` paths in active documentation
- ✅ `manifest.toml` invocation portable across machines
- ✅ All developers follow same setup pattern
- ✅ Full XDG compliance achieved
- ✅ Federation integration unambiguous

---

## Success Criteria

| Criterion | Current | Target | Status |
|-----------|---------|--------|--------|
| Zero hardcoded paths in docs | ❌ | ✅ | TBD |
| All venvs point to `~/.nabi/` | ⚠️ | ✅ | TBD |
| Manifest invocation portable | ❌ | ✅ | TBD |
| Single setup guide | ❌ | ✅ | TBD |
| XDG compliance badge | ❌ | ✅ | TBD |

---

## References

- **Federation Standard**: `~/.claude/CLAUDE.md` (Aura System Architecture section)
- **XDG Spec**: `~/.config/nabi/governance/xdg-compliance.md`
- **Nabi CLI Docs**: `~/docs/tools/nabi-cli.md`
- **Manifest System**: `~/docs/tools/manifest-system.md`

---

## Recommendation

**Action Required**: HIGH PRIORITY

The runtime is correctly configured, but documentation drift could mislead developers and cause XDG violations. Recommend immediate fixes to critical files in Phase 1, followed by comprehensive documentation cleanup in Phase 2.

**Estimated Effort**: 45 minutes for Phase 1, 20 minutes for Phase 2

**Risk of Inaction**: Continued violation of federation standards, developer confusion, portability issues on non-tryk machines

---

*Report prepared by Semantic Custodian (ALIGN)*
*Validation pattern: Federation-aware, XDG-compliant, portable*
*Coherence status: DRIFT_DETECTED → REMEDIATION_REQUIRED*
