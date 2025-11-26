# Riff-CLI: Consolidation Companion Document

**Purpose**: Context for riff-cli developers on the consolidation with riff-dag-tui
**Status**: Reference & Planning Document
**Date**: 2025-11-08
**Primary Document**: See ~/nabia/tui/production/riff-dag-tui/PURPOSE_DISCOVERY_REPORT.md

---

## 🎯 Quick Context

riff-cli is being **consolidated with riff-dag-tui** to create a unified conversation intelligence toolkit for MemRiff.

**What this means for riff-cli**:
- Stay Python-based (no migration needed)
- Add visualization capabilities (via subprocess)
- Become the primary entry point for unified `riff` command
- Deepen federation integration

**Timeline**: Implementation in 4-5 days (Week of Nov 11)

---

## 📋 The Consolidation Plan

### Option A: Python-First Subprocess Integration (APPROVED)

**How riff-cli changes**:

1. **Add subprocess handler module**
   ```python
   src/riff/visualization/handler.py
   ├── RiffDagTUIHandler class
   ├── Binary discovery logic
   └── Process lifecycle management
   ```

2. **Add visualize command**
   ```python
   @app.command()
   def visualize(input_file: str):
       """Explore conversation DAG interactively."""
       handler.launch(Path(input_file))
   ```

3. **Enhance search command**
   ```python
   @app.command()
   def search(
       query: str,
       visualize: bool = typer.Option(False, "--visualize"),
       ...
   ):
       """Search conversations."""
       results = semantic_search(query, ...)

       if visualize:
           export_and_visualize(results)
   ```

4. **Add visualization module**
   ```python
   src/riff/visualization/
   ├── handler.py        # Subprocess lifecycle
   ├── formatter.py      # JSONL conversion
   └── config.py         # Configuration
   ```

### What Stays the Same

✓ Search functionality (Qdrant integration)
✓ JSONL repair operations
✓ TUI module (separate development)
✓ Graph generation
✓ Configuration and federation setup

### What's New

+ Visualization integration
+ Subprocess handler
+ JSONL export to standard format
+ `--visualize` flag for search
+ `visualize` subcommand
+ Temp file management

---

## 🏗️ Implementation Tasks

### Phase 1: Subprocess Handler (Day 1)

**Task**: Create reusable subprocess management

```python
# File: src/riff/visualization/handler.py

class RiffDagTUIHandler:
    """Manages riff-dag-tui subprocess lifecycle."""

    def __init__(self):
        self.binary_path = self._discover_binary()

    def _discover_binary(self) -> Path:
        """Find riff-dag-tui binary in standard locations."""
        # Check ~/.cargo/bin/riff-dag-tui
        # Check ./target/release/riff-dag-tui
        # Check PATH
        # Raise helpful error if not found

    def launch(self, jsonl_path: Path) -> int:
        """Spawn riff-dag-tui with JSONL file."""
        result = subprocess.run(
            [str(self.binary_path), "--input", str(jsonl_path)],
            capture_output=False
        )
        return result.returncode

    def verify_installed(self) -> bool:
        """Check if riff-dag-tui is available."""
        try:
            self._discover_binary()
            return True
        except FileNotFoundError:
            return False
```

**Tests**:
- Binary discovery works on macOS and Linux
- Subprocess spawns and returns exit code
- Error messages are helpful
- No hanging processes

---

### Phase 2: CLI Integration (Day 2)

**Task**: Wire visualization into CLI commands

```python
# File: src/riff/cli.py

@app.command()
def visualize(
    input_file: str = typer.Argument(..., help="JSONL file to visualize"),
):
    """Explore conversation DAG interactively (opens riff-dag-tui)."""
    handler = RiffDagTUIHandler()

    if not handler.verify_installed():
        typer.echo(
            "❌ riff-dag-tui not found. Install with:\n"
            "  cargo install --path ../riff-dag-tui",
            err=True
        )
        raise typer.Exit(1)

    typer.echo(f"🚀 Opening {input_file} in interactive viewer...")
    exit_code = handler.launch(Path(input_file))

    if exit_code != 0:
        typer.echo(f"❌ Visualization exited with code {exit_code}", err=True)
        raise typer.Exit(exit_code)

@app.command()
def search(
    query: str,
    visualize: bool = typer.Option(False, "--visualize", help="Open results in interactive viewer"),
    export: str = typer.Option(None, "--export", help="Export results to JSONL"),
    days: int = typer.Option(None, "--days", help="Filter results from past N days"),
    ai: bool = typer.Option(False, "--ai", help="Use AI-enhanced query"),
):
    """Search conversations semantically."""
    results = semantic_search(query, days=days, ai_enhance=ai)

    if export:
        export_to_jsonl(results, export)
        typer.echo(f"✅ Exported {len(results)} results to {export}")

    if visualize:
        jsonl_data = _convert_to_dag_format(results)
        temp_file = _write_temp_jsonl(jsonl_data)
        try:
            handler = RiffDagTUIHandler()
            handler.launch(temp_file)
        finally:
            temp_file.unlink()  # Cleanup

    return results
```

**Tests**:
- `riff visualize file.jsonl` works
- `riff search "query" --visualize` spawns TUI
- Temp files are cleaned up
- Error messages are helpful

---

### Phase 3: JSONL Conversion (Day 2)

**Task**: Ensure search results convert to DAG format

```python
# File: src/riff/visualization/formatter.py

def convert_to_dag_format(results):
    """Convert search results to riff-dag-tui JSONL format."""
    for i, result in enumerate(results):
        yield {
            "type": "node",
            "id": result.get('id', f"node_{i}"),
            "label": result.get('title', 'Untitled')[:100],
            "span": result.get('session_id', 'unknown'),
            "tags": result.get('tags', []),
            "ts": result.get('timestamp', '')
        }

        # Optional: Add edges based on relationships
        for related_id in result.get('related_nodes', []):
            yield {
                "type": "edge",
                "from": result['id'],
                "to": related_id
            }

def write_temp_jsonl(data: list, prefix: str = "riff-search") -> Path:
    """Write data to temporary JSONL file."""
    # Use ~/.cache/riff/ directory (XDG-compliant)
    # Create directory if needed
    # Generate unique filename with timestamp
    # Write JSONL data
    # Return Path
```

**Tests**:
- JSONL format matches riff-dag-tui expectations
- Nodes have required fields (type, id, label)
- Edges reference existing nodes
- Temp files in correct location

---

### Phase 4: Testing & Documentation (Days 3-5)

**Task**: Comprehensive testing and documentation

**Unit Tests**:
```python
def test_subprocess_handler_discovers_binary():
    handler = RiffDagTUIHandler()
    assert handler.binary_path.exists()

def test_visualize_command_with_missing_binary(monkeypatch):
    # Mock binary not found
    # Verify helpful error message
    pass

def test_search_visualize_creates_temp_jsonl():
    # Search with --visualize
    # Verify temp file created
    # Verify format is correct
    # Verify cleanup happens
    pass

def test_cross_platform_binary_discovery():
    # Test on macOS and Linux
    # Verify PATH search works
    # Verify standard locations checked
    pass
```

**Integration Tests**:
```python
def test_search_to_visualize_workflow():
    # Execute: riff search "test" --visualize
    # Verify subprocess spawned
    # Verify JSONL created
    # Verify cleanup
    pass

def test_large_result_set_handling():
    # Test with 1000+ results
    # Verify performance acceptable
    # Verify no memory issues
    pass
```

**Documentation**:
- Update README.md with new `visualize` command
- Add usage examples
- Document JSONL format
- Update feature list

---

## 📊 Implementation Checklist

### Phase 1 Checklist (Day 1)
- [ ] Create `src/riff/visualization/` directory
- [ ] Implement `handler.py` with RiffDagTUIHandler
- [ ] Binary discovery logic for multiple platforms
- [ ] Error handling and helpful messages
- [ ] Unit tests for handler module

### Phase 2 Checklist (Day 2)
- [ ] Add `visualize` subcommand to CLI
- [ ] Add `--visualize` flag to search
- [ ] Implement JSONL formatter
- [ ] Temp file management
- [ ] Subprocess error handling
- [ ] Unit tests for CLI integration

### Phase 3 Checklist (Day 3)
- [ ] Integration tests (end-to-end)
- [ ] Cross-platform testing (macOS, Linux)
- [ ] Error scenario testing
- [ ] Performance testing (subprocess spawn)
- [ ] Temp file cleanup verification

### Phase 4 Checklist (Days 4-5)
- [ ] Update README.md with examples
- [ ] Document JSONL format specification
- [ ] Add visualization to feature list
- [ ] Federation integration (Nabi CLI)
- [ ] Release notes preparation
- [ ] Code review and approval

---

## 🔗 Related Projects

**riff-dag-tui** (Rust visualization)
- Location: ~/nabia/tui/production/riff-dag-tui/
- Input format: JSONL (nodes + edges)
- Data contract: Defined and stable
- Status: Production-ready

**Integration Protocol**:
- File format: JSONL (standard, text-based, future-proof)
- Process communication: stdout/stderr + exit codes
- Lifecycle: Parent process manages subprocess
- Cleanup: Parent responsible for temp files

---

## 🧪 Testing Strategy

### Unit Testing
- Test subprocess handler in isolation
- Mock riff-dag-tui binary
- Test JSONL conversion logic
- Test error handling

### Integration Testing
- Full workflow: search → export → visualize
- Cross-platform validation
- Large result sets
- Error scenarios (missing binary, corrupt JSONL)

### Manual Testing
- Test on macOS
- Test on Linux
- Verify temp file cleanup
- Test error messages are helpful

---

## 📈 Success Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| **Binary Discovery** | Works on macOS + Linux | Path search + standard locations |
| **Subprocess Spawn Time** | < 2 seconds | Measured from Python startup |
| **JSONL Conversion** | < 100ms for 1000 results | In-memory formatting |
| **Temp File Cleanup** | 100% successful | Even on error paths |
| **Test Coverage** | > 90% | Focus on integration paths |
| **Documentation** | Clear examples | Real-world use cases |

---

## 🚀 Deployment Strategy

### For This Sprint
1. Implement in `riff-cli` (this repo)
2. Test integration with riff-dag-tui
3. Create v2.1 release

### For Federation Registration
1. Register `riff` entry point with Nabi CLI
2. Add to Memchain service inventory
3. Update MemRiff documentation
4. Add Loki event streaming

### For User Communication
1. Update README with new capabilities
2. Document workflow examples
3. Add to federation knowledge base
4. Plan operator training

---

## ❓ Questions for Implementation

1. **Subprocess TTY**: Should visualization spawn in new terminal or take over TTY?
   - *Recommendation*: Take over TTY (better UX)

2. **Result Limits**: Maximum nodes to visualize?
   - *Recommendation*: 500 default, warn at 1000

3. **Temp Directory**: Location for JSONL files?
   - *Recommendation*: ~/.cache/riff/ (XDG-compliant)

4. **Auto-Spawn**: Should --visualize be default?
   - *Recommendation*: Opt-in (explicit flag)

5. **Fallback Mode**: If riff-dag-tui unavailable?
   - *Recommendation*: Show JSON results, suggest installation

---

## 📚 Reference Documents

**Primary Analysis**:
- `~/nabia/tui/production/riff-dag-tui/PURPOSE_DISCOVERY_REPORT.md` (START HERE)

**Implementation Guides**:
- `~/nabia/tui/production/riff-dag-tui/CONSOLIDATION_QUICK_START.md`
- `~/nabia/tui/production/riff-dag-tui/CONSOLIDATION_ANALYSIS.md`

**Architecture Design**:
- `~/nabia/tui/production/riff-dag-tui/UNIFIED_ENTRY_POINT.md`

**Navigation Hub**:
- `~/nabia/tui/production/riff-dag-tui/CONSOLIDATION_INDEX.md`

---

## 🎓 Key Architectural Principles

### 1. Subprocess as Integration Glue
- Clean separation of concerns
- Language freedom (Python + Rust)
- Process isolation (stability)
- Easy to debug and replace

### 2. JSONL as Contract
- Standard, text-based format
- Future-proof (easy to extend)
- Self-documenting (type field)
- Works across language boundaries

### 3. XDG Compliance
- Portable paths (~/.cache/, ~/.config/)
- Federation-aligned
- Enables Syncthing sync
- Cross-platform compatible

### 4. Backward Compatibility
- Old commands still work
- New features are opt-in
- No breaking changes
- User can ignore new features

---

## 📅 Timeline

| Date | Phase | Deliverable |
|------|-------|-------------|
| Nov 11 (Day 1) | Phase 1 | Subprocess handler module |
| Nov 12 (Day 2) | Phase 2 | CLI integration + JSONL formatter |
| Nov 13 (Day 3) | Phase 3 | Integration testing |
| Nov 14 (Day 4) | Phase 4 | Documentation + federation |
| Nov 15 (Day 5) | Release | v2.1 ready for deployment |

---

## ✅ Definition of Done

- [ ] Code complete (all 4 phases)
- [ ] Unit tests (90%+ coverage)
- [ ] Integration tests (end-to-end)
- [ ] Cross-platform testing (macOS, Linux)
- [ ] Documentation updated
- [ ] Code review approved
- [ ] Federation integration complete
- [ ] Ready for production deployment

---

## 📞 Points of Contact

**Questions about consolidation strategy?**
→ See PURPOSE_DISCOVERY_REPORT.md

**Questions about implementation?**
→ See CONSOLIDATION_QUICK_START.md

**Questions about architecture?**
→ See UNIFIED_ENTRY_POINT.md or CONSOLIDATION_ANALYSIS.md

---

*Companion document to the main consolidation analysis*
*Ready for implementation sprint (Week of Nov 11)*
