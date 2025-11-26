# Riff CLI: Binary Release - Action Checklist

**Overall Status**: 7.2/10 - Close to Ready  
**Time to Production**: 20-30 hours (~1 week)  
**Recommended Path**: PyInstaller + GitHub Releases + Homebrew

---

## PRIORITY 1: CRITICAL FIXES (Must Do Before Release)

### [ ] Fix 1: Config Optional + Env Vars (30 mins)
**File**: `src/riff/config.py`
**What**: Make config file optional, add environment variable overrides

**Checklist**:
- [ ] Config file no longer throws error if missing
- [ ] Sensible defaults for all settings exist
- [ ] Environment variables work: `RIFF_QDRANT_URL`, `RIFF_SURREALDB_URL`
- [ ] Test: `riff scan ~/.claude --show` works without config file

**Code Change**:
```python
# Before: Throws FileNotFoundError
# After: Returns empty config dict, uses all defaults
if config_path.exists():
    self._config = toml.load(config_path)
else:
    self._config = {}  # Use defaults only
```

---

### [ ] Fix 2: Lazy-Import Optional Dependencies (2-3 hours)
**Files**: `src/riff/cli.py`, `src/riff/search/__init__.py`
**What**: Only import qdrant/sentence-transformers when needed

**Checklist**:
- [ ] `cmd_search()` imports `QdrantSearcher` internally, not at module load
- [ ] `cmd_browse()` imports `QdrantSearcher` internally
- [ ] Both have try/except that suggests installation if import fails
- [ ] Test: `riff scan` works without `qdrant-client` installed
- [ ] Test: `riff search "query"` shows helpful error message if search module missing

**Code Change**:
```python
# Before: Import at top of module
from riff.search import QdrantSearcher

# After: Import inside function
def cmd_search(args) -> int:
    try:
        from riff.search import QdrantSearcher
    except ImportError:
        console.print("[red]Search module not available[/red]")
        console.print("[yellow]Install: pip install riff[search][/yellow]")
        return 1
```

---

### [ ] Fix 3: XDG Compliance - Hardcoded Paths (1-2 hours)
**File**: `src/riff/cli.py`
**What**: Replace hardcoded paths with config-aware versions

**Checklist**:
- [ ] Line 632: `conversations_dir` uses config.paths or sensible default
- [ ] Line 545: `cache_dir` uses `~/.cache/nabi/riff` (not `~/.cache/riff`)
- [ ] Config supports path overrides: `[paths]` section
- [ ] Test: `riff graph <uuid>` works when ~/.claude doesn't exist
- [ ] Test: `riff search` uses proper cache directory

**Code Change**:
```python
# Before (line 632):
conversations_dir = Path.home() / ".claude" / "projects"

# After:
from riff.config import get_config
config = get_config()
conversations_dir = config.paths.get('conversations', Path.home() / ".claude" / "projects")

# Before (line 545):
cache_dir = Path.home() / ".cache" / "riff"

# After:
cache_dir = config.paths['cache']
```

---

## PRIORITY 2: BUILD INFRASTRUCTURE (Must Do for Release)

### [ ] Create PyInstaller Spec (2-3 hours)
**File**: `riff.spec` (new)
**What**: Configure PyInstaller to build binary correctly

**Checklist**:
- [ ] File exists: `riff.spec`
- [ ] hiddenimports includes: `riff.classic`, `riff.graph`, `riff.enhance`, `riff.surrealdb`
- [ ] hiddenimports excludes: `riff.search` (optional module)
- [ ] Binary builds successfully: `pyinstaller riff.spec`
- [ ] Binary is ~30 MB (core only, no sentence-transformers)
- [ ] Binary works: `./dist/riff/riff --version`

**Template**:
```python
# riff.spec
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/riff/__main__.py'],
    pathex=[str(Path.cwd())],
    binaries=[],
    datas=[],
    hiddenimports=[
        'riff.classic',
        'riff.graph',
        'riff.enhance',
        'riff.surrealdb',
    ],
    excludedimports=['riff.search'],  # Make search optional
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='riff',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
```

---

### [ ] Create GitHub Actions Release Workflow (2-3 hours)
**File**: `.github/workflows/release.yml` (new)
**What**: Automate binary builds on version tags

**Checklist**:
- [ ] File exists: `.github/workflows/release.yml`
- [ ] Triggers on: `push` to tags matching `v*`
- [ ] Builds on: macOS-latest, ubuntu-latest
- [ ] Creates: Signed binaries with checksums
- [ ] Uploads: To GitHub Releases
- [ ] Tested: Run workflow on test tag, verify artifacts

**Template**:
```yaml
# .github/workflows/release.yml
name: Release Binary

on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        os: [macos-latest, ubuntu-latest]
        include:
          - os: macos-latest
            artifact: riff-macos-arm64
          - os: ubuntu-latest
            artifact: riff-linux-x86_64
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install pyinstaller uv
          uv sync
      
      - name: Build binary
        run: |
          pyinstaller riff.spec
          tar czf dist/${{ matrix.artifact }}.tar.gz -C dist riff
      
      - name: Upload release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/${{ matrix.artifact }}.tar.gz
```

---

### [ ] Create Homebrew Formula (1-2 hours)
**File**: `.release/homebrew-formula.rb` (new)
**What**: Template for macOS installation via brew

**Checklist**:
- [ ] File exists: `.release/homebrew-formula.rb`
- [ ] URLs point to GitHub releases
- [ ] SHA256 checksums present (auto-filled at release)
- [ ] Installation instructions documented
- [ ] Tested: Create separate homebrew-tools repo, test formula

**Template**:
```ruby
# .release/homebrew-formula.rb
class Riff < Formula
  desc "Search Claude conversations & repair JSONL sessions"
  homepage "https://github.com/nabia/riff-cli"
  
  on_macos do
    url "https://github.com/nabia/riff-cli/releases/download/v2.0.0/riff-macos-arm64.tar.gz"
    sha256 "WILL_BE_AUTO_FILLED_AT_RELEASE"
  end
  
  on_linux do
    url "https://github.com/nabia/riff-cli/releases/download/v2.0.0/riff-linux-x86_64.tar.gz"
    sha256 "WILL_BE_AUTO_FILLED_AT_RELEASE"
  end
  
  def install
    bin.install "riff"
  end
end
```

---

## PRIORITY 3: TESTING & DOCUMENTATION

### [ ] Write Binary Release Tests (1-2 hours)
**File**: `tests/unit/test_binary_build.py` (new)
**What**: Verify binary builds correctly and works as expected

**Checklist**:
- [ ] Test: PyInstaller spec is valid
- [ ] Test: Binary builds without errors
- [ ] Test: Binary is <35 MB (core) or <200 MB (with search)
- [ ] Test: `./riff --version` returns version
- [ ] Test: `./riff --help` shows all commands
- [ ] Test: `./riff scan` works without config
- [ ] Test: `./riff search` fails gracefully without [search]
- [ ] Test: Startup time < 1 second

---

### [ ] Create Installation Documentation (1-2 hours)
**File**: `docs/BINARY_INSTALLATION.md` (new)
**What**: User-facing install guide

**Checklist**:
- [ ] macOS installation: `brew install nabia/tools/riff`
- [ ] Linux installation: Download + extract from releases
- [ ] Windows installation: TODO (Phase 2)
- [ ] From source: `pip install riff`
- [ ] Verify installation: `riff --version`
- [ ] Quick start example

---

### [ ] Update README (1 hour)
**File**: `README.md`
**What**: Add binary installation section

**Checklist**:
- [ ] Installation section updated with binary instructions
- [ ] Quick start example uses `riff` command
- [ ] Links to BINARY_INSTALLATION.md for detailed setup
- [ ] Mentions both `pip install` and `brew install` options

---

## PRIORITY 4: RELEASE EXECUTION

### [ ] Test Locally (2-3 hours)
**What**: Verify everything works before public release

**Checklist**:
- [ ] Clone fresh repo to separate directory
- [ ] Build binary locally: `pyinstaller riff.spec`
- [ ] Test all basic commands:
  - [ ] `./dist/riff/riff --version`
  - [ ] `./dist/riff/riff scan ~/.claude --show`
  - [ ] `./dist/riff/riff fix test-file.jsonl`
  - [ ] `./dist/riff/riff tui ~/.claude`
  - [ ] `./dist/riff/riff graph <uuid>`
- [ ] Test without config: `rm ~/.config/nabi/tools/riff.toml && ./dist/riff/riff scan`
- [ ] Test without search module: `./dist/riff/riff search "test"` (should show helpful error)
- [ ] Binary size acceptable: `du -h dist/riff`
- [ ] Startup time acceptable: `time ./dist/riff/riff --version` (< 1 sec)

---

### [ ] Create Release (1-2 hours)
**What**: Tag, push, and publish release

**Checklist**:
- [ ] All code changes committed
- [ ] Version number updated: `pyproject.toml` and `__init__.py`
- [ ] CHANGELOG.md updated with release notes
- [ ] Git tag created: `git tag -a v2.0.0 -m "Release message"`
- [ ] Tag pushed: `git push origin v2.0.0` (triggers GitHub Actions)
- [ ] GitHub Actions completes successfully
- [ ] Artifacts uploaded to Releases page
- [ ] Release notes posted with download links

---

### [ ] Publish Homebrew Formula (1 hour)
**What**: Make package available via `brew install`

**Checklist**:
- [ ] Create separate `homebrew-tools` repository (or PR to existing tap)
- [ ] Copy formula to tap: `riff.rb`
- [ ] Test locally: `brew tap nabia/tools <repo-url>`
- [ ] Test locally: `brew install nabia/tools/riff`
- [ ] Verify: `which riff` and `riff --version`
- [ ] Push tap repo

---

## OPTIONAL: NICE-TO-HAVE IMPROVEMENTS (Phase 2)

### [ ] Windows Binary (.exe)
- Build on `windows-latest` in GitHub Actions
- Test with MinGW or MSVC
- Upload to releases

### [ ] Docker Image
- Create Dockerfile with `riff[search]`
- Push to Docker Hub: `nabia/riff:2.0.0`

### [ ] Conda Package
- Create `conda-forge` recipe
- Test installation via conda

### [ ] Auto-Update Feature
- Implement `riff update` command
- Check GitHub releases for newer versions

---

## SUMMARY: FASTEST PATH TO RELEASE

**Week 1 (20-30 hours)**:
1. Fix config (30 mins)
2. Lazy imports (2-3 hrs)
3. Fix paths (1-2 hrs)
4. PyInstaller spec (2-3 hrs)
5. GitHub Actions (2-3 hrs)
6. Homebrew formula (1-2 hrs)
7. Testing (3-4 hrs)
8. Local build + release (2 hrs)

**Result**: `riff` binary available on GitHub releases + Homebrew

---

## SUCCESS CRITERIA

Release is ready when:
- ✅ Binary builds without errors
- ✅ All 9 commands work in binary (except optional search)
- ✅ Binary is <35 MB (core) or <200 MB (with search)
- ✅ Works without config file
- ✅ macOS: `brew install nabia/tools/riff` works
- ✅ Linux: Download, extract, run works
- ✅ Installation docs are clear
- ✅ Startup time < 1 second

---

## ROLLBACK PLAN

If release has critical issue:
1. Delete GitHub release (don't delete tag)
2. Revert problematic commits
3. Push new commits
4. Recreate tag: `git tag -d v2.0.0 && git push origin :v2.0.0`
5. Test locally again
6. Re-create tag and push (triggers Actions again)

---

**Last Updated**: November 10, 2025  
**Next Review**: After Phase 1 completion

