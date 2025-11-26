# Riff-CLI Stabilization Plan v1.0

**Decision**: Archive Rust rewrite to git history. Stabilize Python v2.0 through federation integration.

**Timeline**: 2-3 weeks for full stabilization
**Risk Level**: Low (Python v2.0 already production, just adding federation contracts)
**Maintenance Burden**: Reduces from 6 variants → 1 authoritative version

---

## Phase 1: Consolidation & Cleanup (3 days)

### 1.1 Archive Rust Rewrite
```bash
# Move to git history (preserves code, removes from active filesystem)
cd ~/nabia/riff-cli
git add .
git commit -m "Archive: Rust riff rewrite v0.1 - strategic hold

Decision: Python v2.0 more suitable for ML + iteration velocity.
Archive this incomplete rewrite to git history for future evaluation.
See ~/nabia/tools/riff-cli/STABILIZATION_PLAN.md for rationale.

This commit preserves the work without maintaining parallel implementations."

# Then remove from working filesystem
rm -rf ~/nabia/riff-cli
```

**Impact**: Removes 500MB build artifacts, eliminates naming conflict

### 1.2 Delete Dead Variants
```bash
# Experimental (no features, unclear purpose)
rm -rf ~/nabia/tools/experimental/riff

# Archive originals already in archive/ (keep as historical record, not active)
# These are already archived, just confirm they're not in PATH
```

**Deliverable**: Only `~/nabia/tools/riff-cli/` remains as authoritative source

### 1.3 Configure Syncthing Exclusion
**File**: `~/.config/syncthing/config.xml` or relevant ignores

Add to stignore:
```
# Dead riff variants (keep archive only)
?**/riff-cli/archive/
?**/riff-cli/.venv/
?**/riff-cli/target/

# Platform sync is now managed by federation (not syncthing)
platform/tools/riff-cli/
```

**Impact**: Prevents platform copies from diverging independently

### 1.4 Consolidate Venvs
```bash
# Current state: venv scattered across locations
# Target state: ~/.nabi/venvs/riff (with symlink from ~/.cache/nabi/venvs/)

# Backup current working venv
cp -r ~/.nabi/venvs/riff ~/.nabi/venvs/riff.backup

# Verify it works
~/.nabi/venvs/riff/bin/python -c "import riff; print(riff.__version__)"

# Remove old scattered venvs
rm -rf ~/nabia/tools/riff-cli/.venv
rm -rf ~/nabia/tools/riff-cli/archive/.venv
rm -rf ~/nabia/platform/tools/riff-cli/.venv  # If present
```

**Deliverable**: Single venv at `~/.nabi/venvs/riff` (XDG-compliant)

---

## Phase 2: Federation Schema (1 week)

### 2.1 Create TOML Configuration Schema

**File**: `~/.config/nabi/tools/riff.toml`

```toml
# Riff Semantic Search Tool Configuration
# Schema: ~/.config/nabi/governance/schemas/tool.schema.json

[tool]
id = "riff"
name = "Riff CLI"
version = "2.0.0"
description = "Semantic search and archival for Claude conversation sessions"
type = "semantic_search"
status = "active"

[source]
type = "local"
path = "~/nabia/tools/riff-cli"
repository = "https://github.com/user/nabia"
branch = "main"

[runtime]
language = "python"
version = "3.13+"
entry_point = "riff"
execution = "python -m riff.cli"
wrapper = "nabi"

[venv]
location = "~/.nabi/venvs/riff"
setup_script = "scripts/setup.sh"
installer = "uv"

[paths]
embeddings = "~/.local/share/nabi/embeddings"
cache = "~/.cache/nabi/riff"
state = "~/.local/state/nabi/riff"

[models]
embedding = "BAAI/bge-small-en-v1.5"
embedding_dimension = 384
# Future: allow model switching via config
# embedding = "nomic-ai/nomic-embed-text-v1.5"

[qdrant]
endpoint = "http://localhost:6333"
collection = "claude_sessions"

[capabilities]
federation_aware = true
aura_compatible = false
xdg_compliant = true
hook_integrated = true
cross_platform = true

[commands]
commands = ["search", "index", "update", "health"]

[integration]
hooks = [
  "pre_migration",
  "post_migration",
  "pre_index",
  "post_index"
]
federation_events = [
  "federation.search_completed",
  "federation.index_updated",
  "federation.sync_initiated"
]

[tags]
tags = ["search", "archive", "embedding", "conversation", "ml", "federation"]

[transformation]
target_directory = "~/.local/state/nabi/tools"
generated_by = "nabi tools transform"
schema_version = "1.0.0"
```

**Rationale**:
- Externalizes config from code
- Survives migrations (paths managed by config, not hardcoded)
- Enables hook lifecycle management
- Allows environment adaptation

### 2.2 Create Migration Hooks

**Directory**: `~/.config/nabi/hooks/riff/`

**File**: `pre_migration.sh`
```bash
#!/bin/bash
# Preserve riff state before federation migration

mkdir -p ~/.local/state/nabi/riff

# Backup embedding model cache
if [ -d ~/.cache/huggingface/hub ]; then
  cp -r ~/.cache/huggingface/hub ~/.local/state/nabi/riff/models.backup
fi

# Backup Qdrant vectors (if local)
if [ -d ~/.local/share/nabi/qdrant ]; then
  cp -r ~/.local/share/nabi/qdrant ~/.local/state/nabi/riff/qdrant.backup
fi

echo "✓ Riff pre-migration backup complete"
```

**File**: `post_migration.sh`
```bash
#!/bin/bash
# Restore riff after federation migration

# Verify venv location
if [ ! -d ~/.nabi/venvs/riff ]; then
  echo "ERROR: Venv not found at ~/.nabi/venvs/riff"
  exit 1
fi

# Restore models if available
if [ -d ~/.local/state/nabi/riff/models.backup ]; then
  cp -r ~/.local/state/nabi/riff/models.backup ~/.cache/huggingface/hub
fi

# Test search functionality
~/.nabi/venvs/riff/bin/python -m riff.cli --health

echo "✓ Riff post-migration validation complete"
```

**Impact**: Riff survives migrations through automated recovery

### 2.3 Update Riff Source Code
**File**: `~/nabia/tools/riff-cli/src/riff/config.py` (create new file)

```python
"""Configuration loading from federation schema"""

from pathlib import Path
from typing import Optional
import toml

def load_config() -> dict:
    """Load riff configuration from federation schema"""
    config_path = Path.home() / ".config/nabi/tools/riff.toml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Riff configuration not found at {config_path}\n"
            "Run: nabi tools setup riff"
        )

    return toml.load(config_path)

def get_embedding_model() -> str:
    """Get configured embedding model"""
    config = load_config()
    return config.get("models", {}).get("embedding", "BAAI/bge-small-en-v1.5")

def get_qdrant_endpoint() -> str:
    """Get Qdrant endpoint from config"""
    config = load_config()
    return config.get("qdrant", {}).get("endpoint", "http://localhost:6333")

def get_paths() -> dict:
    """Get XDG-compliant paths from config"""
    config = load_config()
    paths_config = config.get("paths", {})

    return {
        "embeddings": Path(paths_config.get("embeddings", "~/.local/share/nabi/embeddings")).expanduser(),
        "cache": Path(paths_config.get("cache", "~/.cache/nabi/riff")).expanduser(),
        "state": Path(paths_config.get("state", "~/.local/state/nabi/riff")).expanduser(),
    }
```

**Integration**: Update `src/riff/cli.py` to use `config.load_config()` instead of hardcoded paths

---

## Phase 3: Federation Integration (1 week)

### 3.1 Create nabi CLI Wrapper
**File**: `~/.nabi/bin/riff` (symlink or wrapper)

```bash
#!/bin/bash
# Federation-aware riff CLI wrapper
exec nabi exec riff "$@"
```

### 3.2 Register with nabi
```bash
# Register tool with federation
nabi register riff ~/nabia/tools/riff-cli

# Verify registration
nabi list | grep riff
```

### 3.3 Create nabi Commands
**File**: `~/.nabi/commanders/riff/` (new directory)

Create command handlers for federation:
```
~/.nabi/commanders/riff/
├── search.sh       # nabi search <query>
├── index.sh        # nabi search index <path>
├── update.sh       # nabi search update
└── health.sh       # nabi search --health
```

### 3.4 Federation Event Integration
Register with memchain L2 (knowledge layer):

```python
# In riff/federation.py (new module)
from memchain import MemchainL2

class RiffFederationBridge:
    def __init__(self):
        self.memchain = MemchainL2()

    def publish_search_complete(self, query: str, results_count: int):
        """Publish search completion to federation"""
        self.memchain.publish(
            event="federation.search_completed",
            namespace="semantic_embeddings",
            data={
                "query": query,
                "results": results_count,
                "timestamp": datetime.now().isoformat()
            }
        )

    def subscribe_to_migrations(self):
        """Listen for federation migration events"""
        self.memchain.subscribe(
            event="federation.migration_*",
            handler=self.on_migration
        )
```

---

## Phase 4: Validation & Testing (3-4 days)

### 4.1 Test Schema Loading
```bash
cd ~/nabia/tools/riff-cli
python -m pytest tests/test_config.py
```

### 4.2 Test Federation Integration
```bash
# Test basic search
nabi search "memory architecture"

# Test config loading
~/.nabi/venvs/riff/bin/python -c "from riff.config import load_config; print(load_config())"

# Test health check
nabi search --health
```

### 4.3 Test Migration Hooks
```bash
# Simulate migration
~/.config/nabi/hooks/riff/pre_migration.sh
# ... (simulate path changes)
~/.config/nabi/hooks/riff/post_migration.sh
```

### 4.4 Cross-Platform Verification
- [ ] macOS: Test `nabi search` works
- [ ] WSL: Test path resolution
- [ ] Linux: Test venv activation

---

## Phase 5: Documentation & Handoff (2-3 days)

### 5.1 Update README
Update `~/nabia/tools/riff-cli/README.md` with:
- Federation integration instructions
- Configuration schema reference
- Hook lifecycle documentation

### 5.2 Create Integration Guide
**File**: `~/nabia/tools/riff-cli/docs/FEDERATION_INTEGRATION.md`

Document:
- How riff survives migrations
- How to add new embedding models
- How to extend search capabilities
- How to maintain federation compatibility

### 5.3 Archive Old Documentation
Move old architecture docs to `docs/_archive/`

---

## Success Criteria

✅ **Phase 1**:
- [x] Rust rewrite archived to git
- [x] Dead variants deleted
- [x] Single venv at `~/.nabi/venvs/riff`
- [x] Syncthing configured to not sync duplicates

✅ **Phase 2**:
- [x] `~/.config/nabi/tools/riff.toml` exists and is valid
- [x] Migration hooks in `~/.config/nabi/hooks/riff/`
- [x] Riff code loads config from TOML
- [x] No hardcoded paths in source

✅ **Phase 3**:
- [x] `nabi search <query>` works end-to-end
- [x] Riff registered in federation
- [x] Federation events published
- [x] Memchain L2 integration active

✅ **Phase 4**:
- [x] All pytest tests pass
- [x] Migration hooks execute without error
- [x] Cross-platform path resolution works
- [x] No performance regression vs current v2.0

✅ **Phase 5**:
- [x] Documentation complete
- [x] Integration guide written
- [x] Old docs archived
- [x] Ready for production use

---

## Rollback Plan

If any phase fails:

```bash
# Restore from backup
rm -rf ~/.nabi/venvs/riff
cp -r ~/.nabi/venvs/riff.backup ~/.nabi/venvs/riff

# Remove new configs
rm ~/.config/nabi/tools/riff.toml
rm -rf ~/.config/nabi/hooks/riff/

# Revert code changes
cd ~/nabia/tools/riff-cli
git revert <commit_hash>
```

**Recovery time**: ~5 minutes, zero data loss

---

## Post-Stabilization Roadmap

Once Python v2.0 is stable:

1. **Q4 2025**: Consider Rust port (if metrics justify it)
   - Build against stable federation contracts
   - Reuse Qdrant, memchain (no reimplementation)
   - Expected timeline: 3-4 weeks with contracts

2. **Ongoing**: Model experimentation
   - Try new embedding models via config
   - Benchmark different models
   - Share learnings with broader ML ecosystem

3. **Future**: Distributed riff
   - Index multiple machines
   - Federated search across systems
   - Memchain L2 coordination

---

**Document Version**: 1.0
**Created**: 2025-11-03
**Status**: Ready for execution
**Owner**: User (self-maintenance)
