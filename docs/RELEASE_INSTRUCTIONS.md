# Riff v2.0.0 Release Instructions

Complete checklist and procedures for releasing Riff CLI as a single-binary distribution.

---

## Pre-Release Checklist (In Progress ✓)

- [x] XDG system implementation complete
- [x] Backup system integration complete
- [x] Duplicate tool_result detection/removal implemented
- [x] Documentation complete (XDG_ONBOARDING_GUIDE.md, QUICK_START.md)
- [x] Version bumped to 2.0.0
- [x] CHANGELOG.md created
- [x] Python syntax validated
- [x] All imports verified
- [ ] **NEXT STEP**: Create PyInstaller spec file

---

## Phase 1: Build Infrastructure (Week 1)

### Step 1.1: Create PyInstaller Spec File

Location: `.release/riff.spec` (build artifacts directory)

```python
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Riff CLI single-binary release"""

import sys
from PyInstaller.utils.hooks import get_module_file_path

block_cipher = None

# Core dependencies
hiddenimports = [
    'riff',
    'riff.config',
    'riff.backup',
    'riff.classic',
    'riff.classic.commands.scan',
    'riff.classic.commands.fix',
    'riff.classic.commands.tui',
    'riff.classic.commands.graph',
    'riff.search',
    'riff.enhance',
    'riff.graph',
    'riff.visualization',
    'toml',
    'rich',
    'click',
]

# Optional dependencies that should be excluded by default
excludedimports = [
    'sentence-transformers',  # Heavy, optional for search
    'qdrant-client',          # Optional for search
    'surrealdb',              # Optional for db sync
]

a = Analysis(
    ['src/riff/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    excludes=excludedimports,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
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
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

**Build with:**
```bash
pyinstaller .release/riff.spec
```

**Output:** `dist/riff` (executable binary, ~30-50 MB)

### Step 1.2: Test Binary Locally

```bash
# Build the binary
pyinstaller riff.spec

# Test basic commands
./dist/riff --version
./dist/riff --help
./dist/riff scan ~/.claude
./dist/riff scan ~/.claude --show

# Verify XDG directories created
ls -la ~/.config/nabi/
ls -la ~/.local/share/nabi/riff/

# Test fix command with backup
./dist/riff fix --in-place /path/to/conversation.jsonl

# Verify backup was created
ls -la ~/.local/share/nabi/riff/backups/
```

### Step 1.3: Create GitHub Actions Workflow

Location: `.github/workflows/release.yml`

```yaml
name: Build & Release Riff

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11']

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pyinstaller

      - name: Build binary
        run: |
          pyinstaller .release/riff.spec

      - name: Test binary (Linux/macOS)
        if: runner.os != 'Windows'
        run: |
          ./dist/riff --version
          ./dist/riff --help

      - name: Test binary (Windows)
        if: runner.os == 'Windows'
        run: |
          dist\riff.exe --version
          dist\riff.exe --help

      - name: Create release artifact
        run: |
          cd dist
          if [ "$RUNNER_OS" == "Windows" ]; then
            7z a riff-${{ runner.os }}-${{ matrix.python-version }}.zip riff.exe
          else
            tar czf riff-${{ runner.os }}-${{ matrix.python-version }}.tar.gz riff
          fi

      - name: Upload to release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/riff-*.{zip,tar.gz}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Phase 2: Distribution Setup (Week 2)

### Step 2.1: Create Homebrew Formula

Location: `.release/homebrew-formula.rb` (already exists)

```ruby
class RiffCli < Formula
  desc "Conversation repair and semantic search CLI"
  homepage "https://github.com/NabiaTech/riff-cli"
  url "https://github.com/NabiaTech/riff-cli/releases/download/v2.0.0/riff-macos-latest.tar.gz"
  sha256 "CALCULATE_AND_INSERT_SHA256_HERE"
  license "MIT"

  depends_on "python@3.11"

  def install
    bin.install "riff"
  end

  test do
    system "#{bin}/riff", "--version"
  end
end
```

**Install locally:**
```bash
brew install --build-from-source .release/homebrew-formula.rb
```

### Step 2.2: Setup Homebrew Tap

Create repository: `NabiaTech/homebrew-riff-cli`

**Contents:**
- `Formula/riff-cli.rb` - Formula file
- `README.md` - Instructions
- `.github/workflows/tests.yml` - CI/CD

**Usage:**
```bash
brew tap nabitech/riff-cli
brew install riff-cli
```

### Step 2.3: GitHub Release

1. **Create tag:**
   ```bash
   git tag -a v2.0.0 -m "Release v2.0.0: XDG Architecture + Single Binary"
   git push origin v2.0.0
   ```

2. **GitHub Actions automatically:**
   - Builds binaries for macOS, Linux, Windows
   - Creates GitHub Release with artifacts
   - Uploads to releases page

3. **Manual verification:**
   - Download binary from releases page
   - Test on clean system (no nabi, no config)
   - Verify XDG auto-creation works

---

## Phase 3: Installation Documentation (Week 2)

### Step 3.1: Update README.md

Add installation section at top:

```markdown
## Installation

### Quick Start (Homebrew - macOS)
```bash
brew tap nabitech/riff-cli
brew install riff-cli
riff scan ~/.claude
```

### Download Binary
Latest release: [GitHub Releases](https://github.com/NabiaTech/riff-cli/releases)

### From Source
```bash
git clone https://github.com/NabiaTech/riff-cli.git
cd riff-cli
pip install -e .
```
```

### Step 3.2: Create Installation Guide

Location: `docs/INSTALLATION.md`

Covers:
- Homebrew installation
- Binary download
- Source installation
- Verification
- Troubleshooting

---

## Phase 4: Announcement (End of Week 2)

### Step 4.1: Prepare Release Notes

File: `docs/RELEASE_NOTES_v2.0.0.md`

Include:
- What changed (XDG, backups, teaching-first)
- How to upgrade
- Known limitations
- Future roadmap

### Step 4.2: Announce Release

- GitHub Release announcement
- Documentation update
- Social channels (if applicable)
- NabiOS community notification

---

## Testing Checklist

### Binary Functionality Tests
- [ ] Binary downloads and executes
- [ ] `riff --version` shows 2.0.0
- [ ] `riff --help` displays correctly
- [ ] `riff scan ~/.claude` works without config
- [ ] XDG directories created on first run
- [ ] Config file auto-created with TOML
- [ ] `riff fix --in-place` creates backup
- [ ] Backup index updated in state dir
- [ ] All 9 subcommands functional

### Platform Tests
- [ ] macOS x86_64
- [ ] macOS ARM64 (Apple Silicon)
- [ ] Linux x86_64
- [ ] Windows 10/11

### XDG Tests
- [ ] Config created at `~/.config/nabi/riff.toml`
- [ ] Data stored in `~/.local/share/nabi/riff/`
- [ ] State in `~/.local/state/nabi/riff/`
- [ ] Cache in `~/.cache/nabi/riff/`
- [ ] Config readable and editable
- [ ] Paths customizable in TOML
- [ ] Environment variables override config

### Backup Tests
- [ ] Backup created before fix
- [ ] Backup location correct
- [ ] Timestamp format ISO 8601
- [ ] Backup index created and readable
- [ ] Old backups can be cleaned up
- [ ] Restore works manually

### Educational Tests
- [ ] TOML comments are clear
- [ ] XDG_ONBOARDING_GUIDE is helpful
- [ ] User understands XDG after reading docs
- [ ] Config serves as learning tool

---

## Rollback Plan

If critical issues discovered:

```bash
# Delete release tag
git tag -d v2.0.0
git push origin --delete v2.0.0

# Create hotfix branch
git checkout -b hotfix/v2.0.1

# Fix issues
# ... make changes ...

# Test thoroughly
# Create new release
git tag -a v2.0.1 -m "Hotfix: ..."
git push origin v2.0.1
```

---

## Post-Release Tasks

### Week 3+
- [ ] Monitor GitHub issues for bugs
- [ ] Update documentation based on feedback
- [ ] Plan v2.1.0 enhancements
- [ ] Consider Conda package
- [ ] Consider Docker image
- [ ] Plan Windows .exe code signing

---

## Success Metrics

✅ **Release is successful when:**
- Binary works on macOS, Linux, Windows
- XDG system creates directories correctly
- Config auto-creation works (teaching value)
- Backup system prevents data loss
- Users understand XDG through Riff
- No critical bugs reported in first week
- Documentation is clear and helpful

✅ **Binary is distribution-ready when:**
- 30-50 MB single executable
- No external venv required
- Works on clean systems
- XDG auto-setup on first run
- All commands functional
- Comprehensive error messages

---

## Questions?

Refer to:
- `CHANGELOG.md` - What changed
- `docs/XDG_ONBOARDING_GUIDE.md` - Architecture
- `docs/QUICK_START.md` - Usage
- `src/riff/config.py` - Implementation details

---

**Status**: Ready for Phase 1 (PyInstaller)
**Target Release Date**: End of Week 2, November 17, 2025
**Last Updated**: November 10, 2025
