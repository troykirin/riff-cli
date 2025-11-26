# Three-Layer Routing Pattern Guide

**Purpose**: Step-by-step guide for integrating any tool into the unified `nabi` namespace

**Reference Implementation**: `riff-cli` integration (Phase 3)

**Time to Integrate**: ~45 minutes per tool

---

## Architecture Overview

```
Layer 1 (Rust)    → Fast routing decisions (<1ms)
    ↓
Layer 2 (Bash)    → Venv resolution, subprocess isolation
    ↓
Layer 3 (Python)  → Actual functionality
```

**Benefits**:
- Unified namespace (`nabi <tool>`)
- Language-agnostic (Python, Node.js, Rust, Go, etc.)
- Clean subprocess isolation
- Zero shared state between tools
- XDG-compliant storage

---

## Prerequisites

Before integrating a tool, ensure:

1. **Venv exists** at `~/.nabi/venvs/<tool-name>/`
2. **Module entry point** is defined (e.g., `tool.cli`)
3. **Tool is installable** via pip/npm/cargo/etc.

---

## Step 1: Add to Layer 1 (Rust)

**File**: `/Users/tryk/nabia/core/nabi-cli/src/main.rs`

### 1.1: Add Command Variant to Enum

**Location**: Find `enum Commands` (around line 26)

**Pattern**:
```rust
/// Brief description of tool
ToolName {
    /// Tool subcommand and arguments (passed through)
    #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
    args: Vec<String>,
},
```

**Example (riff)**:
```rust
/// Search Claude conversations & repair JSONL sessions (riff-cli)
Riff {
    /// Riff subcommand and arguments (passed through to riff-cli)
    #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
    args: Vec<String>,
},
```

**Key Attributes**:
- `trailing_var_arg = true`: Captures all remaining CLI arguments
- `allow_hyphen_values = true`: Allows flags like `--help` to pass through

---

### 1.2: Add Handler Dispatch

**Location**: Find `fn main() -> Result<()>` match statement (around line 529)

**Pattern**:
```rust
Commands::ToolName { args } => handle_toolname(args),
```

**Example (riff)**:
```rust
Commands::Riff { args } => handle_riff(args),
```

---

### 1.3: Implement Handler Function

**Location**: End of file (before `route_to_python_cli()` function)

**Pattern**:
```rust
fn handle_toolname(args: Vec<String>) -> Result<()> {
    // Layer 1 → Layer 2 handoff
    println!(
        "{}",
        "🔍 Routing to <tool-name>...".cyan().bold()
    );

    let mut python_args = vec!["toolname"];
    let arg_refs: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
    python_args.extend_from_slice(&arg_refs);

    route_to_python_cli(&python_args)
}
```

**Example (riff)**:
```rust
fn handle_riff(args: Vec<String>) -> Result<()> {
    // Layer 1 → Layer 2 handoff for riff-cli
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

### 1.4: Rebuild and Install

```bash
cd ~/nabia/core/nabi-cli
cargo build --release
cp ~/.cache/nabi/nabi-cli/target/release/nabi ~/.local/bin/nabi
```

**Expected Build Time**: 10-15 seconds

---

## Step 2: Add to Layer 2 (Bash)

**File**: `/Users/tryk/nabia/tools/nabi-python`

### 2.1: Add Case Statement

**Location**: Find the main `case "$commander" in` block (around line 40)

**Pattern**:
```bash
toolname)
    # Tool description - Brief summary
    # Route to <tool-name> venv (Layer 3)
    TOOL_VENV="$HOME/.nabi/venvs/toolname-cli"
    if [[ ! -d "$TOOL_VENV" ]]; then
        error "toolname venv not found"
        info "Expected: $TOOL_VENV"
        info "Run: Phase 1 venv consolidation OR create venv"
        exit 1
    fi

    # Execute via venv's Python interpreter
    # Layer 2 → Layer 3 handoff
    exec "$TOOL_VENV/bin/python" -m toolname.cli "$@"
    ;;
```

**Example (riff)**:
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

**Key Design**:
- Use `exec` for clean subprocess handoff (no parent process overhead)
- Error handling with helpful messages
- XDG-compliant paths (no hardcoded `/Users/tryk`)

---

### 2.2: Update Help Text (2 locations)

**Location 1**: Empty commander handler (around line 252)

```bash
"")
    error "No commander specified"
    echo ""
    echo "Available commanders:"
    echo "  toolname    - Brief description"
    ...
```

**Location 2**: Unknown commander handler (around line 334)

```bash
*)
    error "Unknown commander: $commander"
    echo ""
    echo "Available commanders:"
    echo "  toolname    - Brief description"
    ...
```

---

## Step 3: Ensure Layer 3 (Tool Implementation)

### 3.1: Create Venv (if needed)

```bash
python3 -m venv ~/.nabi/venvs/toolname-cli
source ~/.nabi/venvs/toolname-cli/bin/activate
pip install <package-name>
```

### 3.2: Verify Module Entry Point

The tool must be invokable as a Python module:

```bash
~/.nabi/venvs/toolname-cli/bin/python -m toolname.cli --help
```

**Common Patterns**:
- CLI tools: `python -m <package>.cli`
- Scripts: `python -m <package>.__main__`
- Custom: Define in `setup.py` or `pyproject.toml`

---

## Step 4: Test Integration

### Test 1: Help System
```bash
nabi toolname --help
```

**Expected**: Tool's help text appears

---

### Test 2: Command Execution
```bash
nabi toolname <subcommand> <args>
```

**Expected**: Tool executes and returns results

---

### Test 3: Error Handling
```bash
nabi toolname invalid-command
```

**Expected**: Clean error message from tool

---

### Test 4: Subprocess Isolation
```bash
nabi toolname <command> &
ps aux | grep toolname
```

**Expected**: Process completes cleanly, no zombies

---

### Test 5: Performance
```bash
time nabi toolname --help > /dev/null 2>&1
```

**Expected**:
- Rust + Bash overhead: <20ms
- Total time: Depends on tool (Python ~3s cold start)

---

## Non-Python Tools

The pattern works for ANY language:

### Node.js Example

**Layer 2 (Bash)**:
```bash
mytool)
    TOOL_DIR="$HOME/.nabi/tools/mytool"
    if [[ ! -d "$TOOL_DIR" ]]; then
        error "mytool not found"
        exit 1
    fi
    exec node "$TOOL_DIR/index.js" "$@"
    ;;
```

### Rust Example

**Layer 2 (Bash)**:
```bash
rusttool)
    TOOL_BIN="$HOME/.nabi/bin/rusttool"
    if [[ ! -f "$TOOL_BIN" ]]; then
        error "rusttool binary not found"
        exit 1
    fi
    exec "$TOOL_BIN" "$@"
    ;;
```

### Go Example

**Layer 2 (Bash)**:
```bash
gotool)
    TOOL_BIN="$HOME/.nabi/bin/gotool"
    if [[ ! -f "$TOOL_BIN" ]]; then
        error "gotool binary not found"
        exit 1
    fi
    exec "$TOOL_BIN" "$@"
    ;;
```

---

## Troubleshooting

### Issue: "Commander not found"

**Symptom**: `❌ Commander 'toolname' not found`

**Solution**:
1. Verify Layer 2 case statement exists
2. Check spelling (case-sensitive)
3. Ensure bash script is executable: `chmod +x ~/nabia/tools/nabi-python`

---

### Issue: "Venv not found"

**Symptom**: `❌ toolname venv not found`

**Solution**:
1. Create venv: `python3 -m venv ~/.nabi/venvs/toolname-cli`
2. Install package: `pip install <package-name>`
3. Verify path in Layer 2 matches actual location

---

### Issue: "Module not found"

**Symptom**: `ModuleNotFoundError: No module named 'toolname'`

**Solution**:
1. Activate venv: `source ~/.nabi/venvs/toolname-cli/bin/activate`
2. Install package: `pip install <package-name>`
3. Verify module entry point: `python -m toolname.cli --help`

---

### Issue: Arguments not passing through

**Symptom**: Tool doesn't receive arguments

**Solution**:
1. Check Layer 1: Ensure `trailing_var_arg = true`
2. Check Layer 1: Ensure `allow_hyphen_values = true`
3. Check Layer 2: Ensure `"$@"` is quoted

---

## Best Practices

### 1. Use XDG-Compliant Paths

❌ **Don't**:
```bash
TOOL_VENV="/Users/tryk/.nabi/venvs/tool"
```

✅ **Do**:
```bash
TOOL_VENV="$HOME/.nabi/venvs/tool"
```

---

### 2. Add Helpful Error Messages

❌ **Don't**:
```bash
if [[ ! -d "$TOOL_VENV" ]]; then
    exit 1
fi
```

✅ **Do**:
```bash
if [[ ! -d "$TOOL_VENV" ]]; then
    error "toolname venv not found"
    info "Expected: $TOOL_VENV"
    info "Run: python3 -m venv $TOOL_VENV"
    exit 1
fi
```

---

### 3. Use `exec` for Clean Handoff

❌ **Don't**:
```bash
"$TOOL_VENV/bin/python" -m toolname.cli "$@"
```

✅ **Do**:
```bash
exec "$TOOL_VENV/bin/python" -m toolname.cli "$@"
```

**Reason**: `exec` replaces the bash process, avoiding subprocess overhead

---

### 4. Document Routing in Comments

```bash
toolname)
    # Tool description - Brief summary
    # Route to <tool-name> venv (Layer 3)
    ...
    # Layer 2 → Layer 3 handoff
    exec ...
```

---

## Reference Implementation

See Phase 3 completion for full working example:
- **Report**: `/Users/tryk/nabia/tools/riff-cli/PHASE3_COMPLETION_REPORT.md`
- **Layer 1**: `/Users/tryk/nabia/core/nabi-cli/src/main.rs` lines 113-118, 1282-1295
- **Layer 2**: `/Users/tryk/nabia/tools/nabi-python` lines 315-329

---

## Timeline

**Estimated Time per Tool**: 45 minutes

- Layer 1 (Rust): 20 min
  - Add enum variant: 5 min
  - Add handler: 10 min
  - Build + install: 5 min
- Layer 2 (Bash): 10 min
  - Add case statement: 5 min
  - Update help text: 5 min
- Testing: 10 min
  - Help system: 2 min
  - Command execution: 3 min
  - Error handling: 2 min
  - Subprocess isolation: 3 min
- Documentation: 5 min

**With Practice**: Can be reduced to 20-30 minutes per tool

---

## Conclusion

The three-layer routing pattern is **proven, performant, and repeatable**. Any tool, in any language, can be integrated into the unified `nabi` namespace following this guide.

**Pattern Proven**: `riff-cli` integration (Phase 3)
**Architecture**: ORIGIN_ALPHA_MANIFEST
**Next**: Apply this pattern to other tools as needed

---

**Created**: 2025-10-24
**Reference**: Phase 3 - Three-Layer riff Integration
