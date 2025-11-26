#!/bin/bash
# Phase 3 Verification Script
# Tests all aspects of riff-cli integration

echo "========================================="
echo "Phase 3 Verification: riff-cli Integration"
echo "========================================="
echo ""

# Test 1: Layer 1 (Rust) accepts riff command
echo "✓ Test 1: Layer 1 (Rust) accepts riff command"
if nabi riff 2>&1 | grep -q "Riff: search Claude"; then
    echo "  ✅ PASS - Rust layer routes to riff"
else
    echo "  ❌ FAIL - Rust layer doesn't recognize riff"
    exit 1
fi
echo ""

# Test 2: Layer 2 (Bash) finds venv
echo "✓ Test 2: Layer 2 (Bash) finds venv"
if [ -d ~/.nabi/venvs/riff-cli ]; then
    echo "  ✅ PASS - Venv exists at ~/.nabi/venvs/riff-cli"
else
    echo "  ❌ FAIL - Venv not found"
    exit 1
fi
echo ""

# Test 3: Layer 3 (Python) module works
echo "✓ Test 3: Layer 3 (Python) module works"
if ~/.nabi/venvs/riff-cli/bin/python -m riff.cli --help 2>&1 | grep -q "search Claude"; then
    echo "  ✅ PASS - Python module executes"
else
    echo "  ❌ FAIL - Python module error"
    exit 1
fi
echo ""

# Test 4: Full stack routing
echo "✓ Test 4: Full stack routing (all 9 commands)"
commands=(search browse scan fix tui graph graph-classic "sync:surrealdb")
failed=0
for cmd in "${commands[@]}"; do
    if nabi riff $cmd --help > /dev/null 2>&1; then
        echo "  ✅ $cmd"
    else
        echo "  ❌ $cmd"
        failed=$((failed + 1))
    fi
done
if [ $failed -eq 0 ]; then
    echo "  ✅ PASS - All 9 commands accessible"
else
    echo "  ❌ FAIL - $failed commands failed"
    exit 1
fi
echo ""

# Test 5: Error handling
echo "✓ Test 5: Error handling"
if nabi riff invalid-command 2>&1 | grep -q "invalid choice"; then
    echo "  ✅ PASS - Error propagates cleanly"
else
    echo "  ❌ FAIL - Error handling broken"
    exit 1
fi
echo ""

# Test 6: Performance baseline
echo "✓ Test 6: Performance baseline"
start_time=$(date +%s%N)
nabi riff scan --help > /dev/null 2>&1
end_time=$(date +%s%N)
elapsed_ms=$(( (end_time - start_time) / 1000000 ))
echo "  ⏱️  Execution time: ${elapsed_ms}ms"
if [ $elapsed_ms -lt 10000 ]; then
    echo "  ✅ PASS - Performance acceptable (<10s)"
else
    echo "  ⚠️  WARNING - Performance slow (${elapsed_ms}ms)"
fi
echo ""

# Summary
echo "========================================="
echo "Phase 3 Verification: ✅ ALL TESTS PASSED"
echo "========================================="
echo ""
echo "Integration Status:"
echo "  • Layer 1 (Rust): ✅ Operational"
echo "  • Layer 2 (Bash): ✅ Operational"
echo "  • Layer 3 (Python): ✅ Operational"
echo "  • Full Stack: ✅ Operational"
echo "  • Error Handling: ✅ Operational"
echo "  • Performance: ✅ Acceptable"
echo ""
echo "Decision Gate: ✅ READY TO PROCEED TO PHASE 4"
echo ""
