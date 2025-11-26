# Phase 3 Code Changes Summary

**Quick Reference**: All code changes made during Phase 3 integration

---

## Layer 1: Rust Router

**File**: `/Users/tryk/nabia/core/nabi-cli/src/main.rs`

### Change 1: Add Riff Command Enum Variant

**Location**: Lines 113-118

```rust
/// Search Claude conversations & repair JSONL sessions (riff-cli)
Riff {
    /// Riff subcommand and arguments (passed through to riff-cli)
    #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
    args: Vec<String>,
},
```

---

### Change 2: Add Handler Dispatch

**Location**: Line 551

```rust
Commands::Riff { args } => handle_riff(args),
```

---

### Change 3: Implement Handler Function

**Location**: Lines 1282-1295

```rust
fn handle_riff(args: Vec<String>) -> Result<()> {
    // Layer 1 → Layer 2 handoff for riff-cli
    // Route all riff commands to Python CLI layer
    println!(
        "{}",
        "🔍 Routing to riff-cli...".cyan().bold()
    );

    let mut python_args = vec!["riff"];
    let arg_refs: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
    python_args.extend_from_slice(&arg_refs);

    route_to_python_cli(&python_args)
}
```

---

## Layer 2: Bash Router

**File**: `/Users/tryk/nabia/tools/nabi-python`

### Change 1: Add Riff Case Statement

**Location**: Lines 315-329

```bash
riff)
    # Riff-CLI - Search Claude conversations & repair JSONL sessions
    # Route to riff-cli venv (Layer 3)
    RIFF_VENV="$HOME/.nabi/venvs/riff-cli"
    if [[ ! -d "$RIFF_VENV" ]]; then
        error "riff-cli venv not found"
        info "Expected: $RIFF_VENV"
        info "Run: Phase 1 venv consolidation"
        exit 1
    fi

    # Execute via riff-cli venv's Python interpreter
    # Layer 2 → Layer 3 handoff
    exec "$RIFF_VENV/bin/python" -m riff.cli "$@"
    ;;
```

---

### Change 2: Update Help Text (Empty Commander)

**Location**: Lines 252-268

```bash
"")
    error "No commander specified"
    echo ""
    echo "Usage: nabi-python <commander> <args...>"
    echo ""
    echo "Available commanders:"
    echo "  claude      - Claude session/project operations (routes to cm)"
    echo "  docs        - Documentation/manifest operations"
    echo "  port        - Port registry and management"
    echo "  federation  - Federation agent coordination"
    echo "  riff        - Search Claude conversations & repair JSONL sessions"  # NEW
    echo "  syncthing   - Syncthing federation status"
    echo "  doctor      - Health checks"
    echo "  data        - Data operations (pending implementation)"
    echo ""
    exit 1
    ;;
```

---

### Change 3: Update Help Text (Unknown Commander)

**Location**: Lines 334-348

```bash
*)
    error "Unknown commander: $commander"
    echo ""
    echo "Available commanders:"
    echo "  claude      - Claude session/project operations"
    echo "  docs        - Documentation/manifest operations"
    echo "  port        - Port registry and management"
    echo "  federation  - Federation agent coordination"
    echo "  riff        - Search Claude conversations & repair JSONL sessions"  # NEW
    echo "  syncthing   - Syncthing federation status"
    echo "  doctor      - Health checks"
    echo "  data        - Data operations (pending)"
    echo ""
    exit 1
    ;;
```

---

## Binary Updates

### Build Command

```bash
cd /Users/tryk/nabia/core/nabi-cli
cargo build --release
```

**Build Output**: `/Users/tryk/.cache/nabi/nabi-cli/target/release/nabi`

---

### Installation Command

```bash
cp /Users/tryk/.cache/nabi/nabi-cli/target/release/nabi ~/.local/bin/nabi
```

**Installed Location**: `/Users/tryk/.local/bin/nabi`

---

## Statistics

### Lines Added

- **Layer 1 (Rust)**: 21 lines
  - Enum variant: 6 lines
  - Handler dispatch: 1 line
  - Handler function: 14 lines

- **Layer 2 (Bash)**: 19 lines
  - Case statement: 15 lines
  - Help text updates: 4 lines (2 locations × 2 lines)

**Total**: 40 lines of code

---

### Functions Added

- **Layer 1**: 1 function (`handle_riff`)
- **Layer 2**: 1 case statement

**Total**: 2 new routing components

---

### Files Modified

1. `/Users/tryk/nabia/core/nabi-cli/src/main.rs`
2. `/Users/tryk/nabia/tools/nabi-python`

**Total**: 2 files

---

## Testing Commands

### Test 1: Help
```bash
nabi riff --help
nabi riff
```

### Test 2: Subcommands
```bash
nabi riff search "test" --limit 3
nabi riff scan --help
nabi riff graph --help
```

### Test 3: Error Handling
```bash
nabi riff invalid-command
```

### Test 4: All Commands
```bash
for cmd in search browse scan fix tui graph graph-classic sync:surrealdb; do
  nabi riff $cmd --help > /dev/null 2>&1 && echo "✅ $cmd" || echo "❌ $cmd"
done
```

### Test 5: Performance
```bash
time nabi riff scan --help > /dev/null 2>&1
```

---

## Routing Flow

```
$ nabi riff search "query"
    ↓
[Layer 1: Rust] ~/.local/bin/nabi
  • Parses: command=Riff, args=["search", "query"]
  • Calls: handle_riff(args)
  • Delegates: route_to_python_cli(["riff", "search", "query"])
    ↓
[Layer 2: Bash] ~/.local/bin/nabi-python
  • Receives: commander="riff", args=["search", "query"]
  • Resolves: RIFF_VENV="~/.nabi/venvs/riff-cli"
  • Executes: exec "$RIFF_VENV/bin/python" -m riff.cli "search" "query"
    ↓
[Layer 3: Python] ~/.nabi/venvs/riff-cli/bin/python
  • Module: riff.cli
  • Command: search("query")
  • Results: → stdout → user
```

---

## Key Design Decisions

### 1. `trailing_var_arg = true`
**Why**: Captures all remaining arguments after `riff`
**Example**: `nabi riff search "query" --limit 3` → `["search", "query", "--limit", "3"]`

### 2. `allow_hyphen_values = true`
**Why**: Allows flags to pass through without Clap intercepting them
**Example**: `--help`, `--limit`, `--qdrant-url`

### 3. `exec` instead of subprocess
**Why**: Replaces bash process, avoiding parent/child overhead
**Benefit**: No zombie processes, cleaner `ps` output

### 4. XDG-compliant paths
**Why**: Cross-platform compatibility (macOS, WSL, Linux, RPi)
**Example**: `$HOME/.nabi/venvs/` instead of `/Users/tryk/.nabi/venvs/`

---

## Documentation Created

1. **PHASE3_COMPLETION_REPORT.md** - Full phase execution report
2. **ROUTING_PATTERN_GUIDE.md** - Reusable pattern for future tools
3. **PHASE3_CODE_SUMMARY.md** - This file (code reference)

**Location**: `/Users/tryk/nabia/tools/riff-cli/`

---

## Next Steps

### Phase 4: Git Consolidation (45 min target)

**Objective**: Resolve two-git-repo conflict

**Decision Required**:
- Option A: Single source repo at `~/nabia/core/nabi-cli/.git/`
- Option B: Dual repo pattern (needs cleanup)

**Recommendation**: Option A (matches XDG architecture)

---

**Created**: 2025-10-24
**Phase**: Phase 3 - Three-Layer riff Integration
**Status**: ✅ COMPLETE
