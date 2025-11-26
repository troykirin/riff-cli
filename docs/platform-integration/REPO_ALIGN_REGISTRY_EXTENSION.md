# nabi repo align - Registry Integration & Duplicate Detection

**Extends**: REPO_ALIGN_IMPLEMENTATION_PLAN.md

**Purpose**: Solve repository lifecycle tracking and duplicate detection across POC → prototype → production evolution cycles

---

## Problem Statement

**Current Pain Point** (from user feedback):

> "I've lost awareness of how the paths have changed and which one is the latest. POCs turned into prototypes, prototypes evolved into other forms, and now there was a remake last night to make the production version."

**Example**: `riff-cli` has existed in multiple locations:
- `~/dev/riff-cli` (initial POC)
- `~/projects/riff-tui-prototype` (prototype)
- `~/nabia/tools/riff-cli` (previous version)
- `~/nabia/platform/tools/riff-cli` (current production version)

**Impact**:
- Path confusion across sessions
- Duplicated effort (editing wrong version)
- Manifest drift (multiple manifests for same logical repo)
- Documentation staleness (references to old paths)

---

## Solution: Repository Registry with Lifecycle Tracking

### New Commands

```rust
// Add to RepoCommands enum

#[derive(Subcommand)]
enum RepoCommands {
    // ... existing commands (check, report, fix, validate) ...

    /// List all registered repositories
    Registry {
        /// Show only active repos
        #[arg(short, long)]
        active: bool,

        /// Filter by lifecycle stage
        #[arg(short, long)]
        lifecycle: Option<LifecycleStage>,

        /// Output format
        #[arg(short = 'f', long, default_value = "table")]
        format: OutputFormat,
    },

    /// Detect duplicate repositories
    Duplicates {
        /// Similarity threshold (0.0-1.0)
        #[arg(short, long, default_value = "0.7")]
        threshold: f32,

        /// Auto-mark duplicates as archived
        #[arg(long)]
        auto_archive: bool,
    },

    /// Mark repository lifecycle stage
    Mark {
        /// Repository path or name
        #[arg(value_name = "REPO")]
        repo: String,

        /// Lifecycle stage
        #[arg(value_enum)]
        stage: LifecycleStage,

        /// Reason/notes
        #[arg(short, long)]
        reason: Option<String>,
    },

    /// Show repository status and evolution history
    Status {
        /// Repository path or name (defaults to current directory)
        repo: Option<String>,

        /// Show evolution history
        #[arg(short = 'H', long)]
        history: bool,
    },

    /// Link repositories in evolution chain
    Link {
        /// Previous version repository
        #[arg(value_name = "FROM")]
        from: String,

        /// Next version repository
        #[arg(value_name = "TO")]
        to: String,

        /// Relationship type
        #[arg(short, long, default_value = "evolution")]
        relation: RelationType,
    },
}

#[derive(Clone, ValueEnum)]
enum LifecycleStage {
    /// Proof of concept (exploratory)
    Poc,
    /// Working prototype (validation)
    Prototype,
    /// Development version (active work)
    Development,
    /// Production version (canonical)
    Production,
    /// Archived (superseded/deprecated)
    Archived,
    /// Unknown/unclassified
    Unknown,
}

#[derive(Clone, ValueEnum)]
enum RelationType {
    /// Direct evolution (POC → Prototype → Production)
    Evolution,
    /// Fork for experimentation
    Fork,
    /// Parallel implementation (different approach)
    Parallel,
    /// Merge/consolidation
    Consolidation,
}
```

---

## Enhanced Manifest Schema

### Registry Metadata Extension

Add to existing manifest schema (`~/.local/state/nabi/manifests/{repo}.manifest.json`):

```json
{
  "schema_version": "1.1.0",
  "repo": {
    "name": "riff-cli",
    "path": "/Users/tryk/nabia/platform/tools/riff-cli",
    "git_branch": "main",
    "lifecycle": {
      "stage": "production",
      "marked_at": "2025-10-26T00:00:00Z",
      "marked_by": "user",
      "reason": "Production version after consolidation"
    },
    "evolution": {
      "previous": [
        {
          "path": "/Users/tryk/nabia/tools/riff-cli",
          "stage": "archived",
          "relation": "evolution",
          "archived_at": "2025-10-25T23:00:00Z"
        }
      ],
      "aliases": [
        "riff",
        "riff-search",
        "claude-search"
      ]
    }
  },
  // ... existing fields (generated_at, files, metadata) ...
}
```

### Registry Index File

Create central registry at `~/.local/state/nabi/manifests/registry.json`:

```json
{
  "schema_version": "1.0.0",
  "updated_at": "2025-10-26T00:00:00Z",
  "repos": [
    {
      "name": "riff-cli",
      "canonical_path": "~/nabia/platform/tools/riff-cli",
      "lifecycle": "production",
      "last_updated": "2025-10-26T00:00:00Z",
      "manifest_file": "riff-cli.manifest.json",
      "duplicates": [
        {
          "path": "~/nabia/tools/riff-cli",
          "similarity": 0.95,
          "status": "archived"
        },
        {
          "path": "~/dev/riff-tui",
          "similarity": 0.72,
          "status": "archived"
        }
      ]
    }
  ],
  "statistics": {
    "total_repos": 15,
    "active": 12,
    "archived": 3,
    "duplicates_detected": 7
  }
}
```

---

## Duplicate Detection Algorithm

### Similarity Scoring

```rust
pub struct DuplicateDetector {
    threshold: f32,  // 0.0-1.0
}

impl DuplicateDetector {
    /// Calculate similarity score between two repositories
    pub fn calculate_similarity(&self, repo_a: &Manifest, repo_b: &Manifest) -> f32 {
        let name_score = self.name_similarity(&repo_a.repo.name, &repo_b.repo.name);
        let path_score = self.path_similarity(&repo_a.repo.path, &repo_b.repo.path);
        let content_score = self.content_similarity(&repo_a.files, &repo_b.files);

        // Weighted average
        (name_score * 0.4) + (path_score * 0.3) + (content_score * 0.3)
    }

    /// Name similarity using Levenshtein distance
    fn name_similarity(&self, name_a: &str, name_b: &str) -> f32 {
        let distance = levenshtein(name_a, name_b);
        let max_len = name_a.len().max(name_b.len()) as f32;
        1.0 - (distance as f32 / max_len)
    }

    /// Path similarity (common prefixes and suffixes)
    fn path_similarity(&self, path_a: &Path, path_b: &Path) -> f32 {
        let components_a: Vec<_> = path_a.components().collect();
        let components_b: Vec<_> = path_b.components().collect();

        let common_count = components_a.iter()
            .zip(&components_b)
            .take_while(|(a, b)| a == b)
            .count();

        let max_len = components_a.len().max(components_b.len()) as f32;
        common_count as f32 / max_len
    }

    /// Content similarity (file structure overlap)
    fn content_similarity(&self, files_a: &[FileEntry], files_b: &[FileEntry]) -> f32 {
        let paths_a: HashSet<_> = files_a.iter().map(|f| &f.path).collect();
        let paths_b: HashSet<_> = files_b.iter().map(|f| &f.path).collect();

        let intersection = paths_a.intersection(&paths_b).count();
        let union = paths_a.union(&paths_b).count();

        if union == 0 {
            return 0.0;
        }

        intersection as f32 / union as f32
    }

    /// Detect all duplicates above threshold
    pub fn detect_duplicates(&self, manifests: &[Manifest]) -> Vec<DuplicateGroup> {
        let mut groups = Vec::new();
        let mut processed = HashSet::new();

        for (i, manifest_a) in manifests.iter().enumerate() {
            if processed.contains(&i) {
                continue;
            }

            let mut group = DuplicateGroup {
                canonical: manifest_a.clone(),
                duplicates: Vec::new(),
            };

            for (j, manifest_b) in manifests.iter().enumerate().skip(i + 1) {
                if processed.contains(&j) {
                    continue;
                }

                let similarity = self.calculate_similarity(manifest_a, manifest_b);

                if similarity >= self.threshold {
                    group.duplicates.push(DuplicateEntry {
                        manifest: manifest_b.clone(),
                        similarity,
                    });
                    processed.insert(j);
                }
            }

            if !group.duplicates.is_empty() {
                groups.push(group);
            }
            processed.insert(i);
        }

        groups
    }
}

pub struct DuplicateGroup {
    pub canonical: Manifest,
    pub duplicates: Vec<DuplicateEntry>,
}

pub struct DuplicateEntry {
    pub manifest: Manifest,
    pub similarity: f32,
}
```

---

## Command Examples

### List All Registered Repositories

```bash
# Show all registered repos in table format
nabi repo align registry

# Output:
# ┌────────────────┬───────────────────────────────────────┬─────────────┬──────────────┐
# │ Name           │ Path                                   │ Lifecycle   │ Last Updated │
# ├────────────────┼───────────────────────────────────────┼─────────────┼──────────────┤
# │ riff-cli       │ ~/nabia/platform/tools/riff-cli       │ production  │ 2025-10-26   │
# │ nabi-cli       │ ~/nabia/core/nabi-cli                 │ production  │ 2025-10-24   │
# │ memchain       │ ~/nabia/memchain                      │ development │ 2025-10-23   │
# │ riff-cli-old   │ ~/nabia/tools/riff-cli                │ archived    │ 2025-10-20   │
# └────────────────┴───────────────────────────────────────┴─────────────┴──────────────┘

# Show only active/production repos
nabi repo align registry --active

# JSON output for scripting
nabi repo align registry --format json > repos.json

# Filter by lifecycle stage
nabi repo align registry --lifecycle production
nabi repo align registry --lifecycle archived
```

### Detect Duplicates

```bash
# Detect potential duplicates (similarity >= 0.7)
nabi repo align duplicates

# Output:
# 🔍 Duplicate repositories detected:
#
# Group 1: riff-cli
# ├─ Canonical: ~/nabia/platform/tools/riff-cli (production)
# ├─ Duplicate: ~/nabia/tools/riff-cli (archived) - 95% similar
# └─ Duplicate: ~/dev/riff-tui (unknown) - 72% similar
#
# Group 2: voice-whisper
# ├─ Canonical: ~/nabia/voice-whisper (production)
# └─ Duplicate: ~/projects/whisper-poc (archived) - 81% similar
#
# 💡 Suggestion: Run 'nabi repo align mark <path> archived' for old versions

# Lower threshold for more aggressive detection
nabi repo align duplicates --threshold 0.5

# Auto-archive detected duplicates
nabi repo align duplicates --auto-archive --threshold 0.8
```

### Mark Repository Lifecycle

```bash
# Mark old version as archived
nabi repo align mark ~/nabia/tools/riff-cli archived \
  --reason "Superseded by platform/tools/riff-cli production version"

# Mark new repo as production
nabi repo align mark ~/nabia/platform/tools/riff-cli production \
  --reason "Consolidated version after Phase 3 completion"

# Mark POC for future cleanup
nabi repo align mark ~/dev/experimental-poc poc \
  --reason "Experimental TUI prototype"

# Output:
# ✓ Marked ~/nabia/tools/riff-cli as 'archived'
#   Reason: Superseded by platform/tools/riff-cli production version
#   Updated manifest: riff-cli-old.manifest.json
```

### Link Repositories in Evolution Chain

```bash
# Link POC → Prototype → Production evolution
nabi repo align link ~/dev/riff-tui ~/nabia/tools/riff-cli --relation evolution
nabi repo align link ~/nabia/tools/riff-cli ~/nabia/platform/tools/riff-cli --relation evolution

# Create fork relationship
nabi repo align link ~/nabia/memchain ~/nabia/memchain-experimental --relation fork

# Output:
# ✓ Linked evolution chain:
#   ~/dev/riff-tui (poc)
#     → ~/nabia/tools/riff-cli (archived)
#       → ~/nabia/platform/tools/riff-cli (production)
```

### Show Repository Status

```bash
# Show current repo status
cd ~/nabia/platform/tools/riff-cli
nabi repo align status

# Output:
# Repository: riff-cli
# Path: ~/nabia/platform/tools/riff-cli
# Lifecycle: production
# Git Branch: main
# Last Manifest Update: 2025-10-26 18:30:00
#
# Evolution Chain:
#   1. ~/dev/riff-tui (poc, archived 2025-08-15)
#   2. ~/nabia/tools/riff-cli (prototype, archived 2025-10-25)
#   3. ~/nabia/platform/tools/riff-cli (production, current) ← YOU ARE HERE
#
# Duplicates Detected: 2 archived versions
# Compliance: 100% (last checked: 2025-10-26 18:29:00)

# Show evolution history
nabi repo align status --history

# Check specific repo
nabi repo align status ~/nabia/tools/riff-cli

# Output:
# ⚠️  Warning: This repository is marked as 'archived'
# Superseded by: ~/nabia/platform/tools/riff-cli (production)
# Reason: Superseded by platform/tools/riff-cli production version
# Archived: 2025-10-25 23:00:00
#
# 💡 Suggestion: Use production version at ~/nabia/platform/tools/riff-cli
```

---

## Auto-Remediation Actions

### Duplicate Resolution Workflow

```bash
# Interactive duplicate resolution
nabi repo align duplicates --interactive

# Output:
# 🔍 Found 3 duplicate groups
#
# Group 1: riff-cli
# ├─ [A] ~/nabia/platform/tools/riff-cli (production, last updated: 2025-10-26)
# ├─ [B] ~/nabia/tools/riff-cli (unknown, last updated: 2025-10-20)
# └─ [C] ~/dev/riff-tui (unknown, last updated: 2025-08-15)
#
# Which is the canonical version? [A/B/C/skip]: A
# Mark others as archived? [Y/n]: Y
#
# ✓ Marked ~/nabia/tools/riff-cli as 'archived'
# ✓ Marked ~/dev/riff-tui as 'archived'
# ✓ Created evolution chain: C → B → A
```

### Path Migration Suggestions

When detecting archived repos with references in active code:

```bash
nabi repo align check ~/nabia/platform/tools/some-project

# Output:
# ❌ Hardcoded path references to archived repositories:
#
# File: README.md:15
#   Reference: ~/nabia/tools/riff-cli
#   Status: archived (superseded)
#   Suggestion: Replace with ~/nabia/platform/tools/riff-cli
#
# File: scripts/build.sh:8
#   Reference: /Users/tryk/dev/riff-tui
#   Status: archived (POC)
#   Suggestion: Remove or update to production version
#
# 💡 Run 'nabi repo align fix --archived-refs' to auto-update
```

---

## Registry Maintenance Commands

```bash
# Rebuild registry index from manifests
nabi repo align registry --rebuild

# Clean up orphaned manifests (repos that no longer exist)
nabi repo align registry --clean-orphans

# Validate all manifests for consistency
nabi repo align registry --validate-all

# Export registry to Markdown for documentation
nabi repo align registry --format markdown > REPOSITORY_REGISTRY.md
```

---

## Integration with Existing Workflow

### Session Start Hook Enhancement

Add duplicate detection warning to session start:

```python
# ~/.config/nabi/governance/hooks/session_start.py (enhancement)

def check_repo_duplicates(repo_path: str) -> Optional[str]:
    """Warn if current repo has known duplicates"""
    result = subprocess.run(
        ["nabi", "repo", "align", "status", repo_path, "--format", "json"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        data = json.loads(result.stdout)
        if data.get("duplicates"):
            canonical = data["duplicates"]["canonical_path"]
            if repo_path != canonical:
                return f"⚠️  Working in archived repository. Production version: {canonical}"

    return None
```

---

## Database Schema (Future: SurrealDB)

For advanced querying and analytics:

```sql
-- Repository table
DEFINE TABLE repository SCHEMAFULL;
DEFINE FIELD name ON repository TYPE string;
DEFINE FIELD path ON repository TYPE string;
DEFINE FIELD lifecycle ON repository TYPE string;
DEFINE FIELD created_at ON repository TYPE datetime;
DEFINE FIELD archived_at ON repository TYPE option<datetime>;

-- Evolution relationship
DEFINE TABLE evolves_to SCHEMAFULL TYPE RELATION FROM repository TO repository;
DEFINE FIELD relation_type ON evolves_to TYPE string;
DEFINE FIELD created_at ON evolves_to TYPE datetime;

-- Example queries
SELECT * FROM repository WHERE lifecycle = 'production';
SELECT ->evolves_to->repository FROM repository:riff_cli;
```

---

## Metrics and Analytics

### Registry Health Dashboard

```bash
nabi repo align registry --stats

# Output:
# Repository Registry Health
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Total Repositories:        23
# Active (Production):       12  (52%)
# Development:               8   (35%)
# Archived:                  3   (13%)
#
# Duplicate Detection:
#   Duplicate Groups:        5
#   Similarity Avg:          0.81
#   Auto-archived:           7
#
# Evolution Chains:
#   Tracked Chains:          4
#   Avg Chain Length:        2.5
#   Orphaned POCs:           2
#
# Last Registry Scan:        2025-10-26 18:30:00
# Registry Compliance:       95%
```

---

## Testing Strategy

### Unit Tests

```rust
#[test]
fn test_duplicate_detection_high_similarity() {
    let manifest_a = create_test_manifest("riff-cli", "~/nabia/platform/tools/riff-cli");
    let manifest_b = create_test_manifest("riff-cli-old", "~/nabia/tools/riff-cli");

    let detector = DuplicateDetector { threshold: 0.7 };
    let similarity = detector.calculate_similarity(&manifest_a, &manifest_b);

    assert!(similarity >= 0.7);
}

#[test]
fn test_lifecycle_marking() {
    let mut manifest = load_manifest("test_fixtures/riff-cli.manifest.json");

    mark_lifecycle(&mut manifest, LifecycleStage::Archived, Some("Superseded"));

    assert_eq!(manifest.repo.lifecycle.stage, "archived");
    assert!(manifest.repo.lifecycle.reason.is_some());
}
```

### Integration Tests

```bash
# Test duplicate detection workflow
./tests/test_duplicate_detection.sh

# Test registry rebuild
./tests/test_registry_rebuild.sh

# Test lifecycle marking and evolution chains
./tests/test_lifecycle_tracking.sh
```

---

## Documentation Updates

1. **User Guide**: Add "Repository Lifecycle Management" section
2. **Best Practices**: Document POC → Prototype → Production workflow
3. **Migration Guide**: How to consolidate duplicate repos
4. **Troubleshooting**: Common registry issues and solutions

---

## Success Criteria

### Phase 1 (Registry Foundation)
- [x] Registry index created
- [ ] List command working
- [ ] Status command shows lifecycle
- [ ] Lifecycle marking functional

### Phase 2 (Duplicate Detection)
- [ ] Similarity algorithm implemented
- [ ] Duplicates command working
- [ ] Auto-archive feature tested
- [ ] False positive rate < 5%

### Phase 3 (Evolution Tracking)
- [ ] Link command functional
- [ ] Evolution chains visualized
- [ ] History tracking working
- [ ] Migration suggestions accurate

---

## Future Enhancements

1. **Visual Evolution Graph**: Mermaid diagram of repo relationships
2. **Auto-Migration Tool**: Automated path updates across codebase
3. **Workspace Awareness**: Detect cross-repo references
4. **Time-Travel**: Show repo state at any point in history
5. **Smart Archival**: ML-based suggestions for archival candidates

---

**Status**: Ready for Phase 1 implementation (extends main implementation plan)
**Solves**: Repository lifecycle tracking, duplicate detection, path awareness loss
**Next Step**: Implement registry indexing and duplicate detection algorithm
