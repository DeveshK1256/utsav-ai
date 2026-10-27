import json
import os
import tempfile
import pytest
from scripts.ci_ratchet import (
    load_baseline,
    save_baseline,
    run_ratchet,
    get_ruff_error_count
)


def test_ratchet_fails_when_errors_exceed_baseline(tmp_path):
    """
    Test that the quality ratchet strictly FAILS (exit code 1)
    whenever errors exceed the committed baseline.
    Verifies that the baseline is NEVER raised.
    """
    test_baseline = tmp_path / "ci_baseline_test.json"
    actual_ruff = get_ruff_error_count("backend/")
    
    # Intentionally set baseline lower than current errors
    baseline_data = {
        "ruff_max_errors": actual_ruff - 1,
        "mypy_max_errors": 999
    }
    with open(test_baseline, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f)

    # Ratchet must FAIL
    ret = run_ratchet("ruff", baseline_path=str(test_baseline), auto_commit=False)
    assert ret == 1, "Ratchet should have failed when errors exceed baseline"

    # Verify baseline was NOT raised
    loaded = load_baseline(str(test_baseline))
    assert loaded["ruff_max_errors"] == actual_ruff - 1, "Baseline must never increase on failure"


def test_ratchet_auto_tightens_when_errors_decrease(tmp_path):
    """
    Test that when errors are lower than baseline, the ratchet automatically
    tightens: it rewrites the baseline file with the new lower number.
    """
    test_baseline = tmp_path / "ci_baseline_test.json"
    actual_ruff = get_ruff_error_count("backend/")

    # Set baseline higher than current errors (simulating prior state)
    old_baseline = actual_ruff + 5
    baseline_data = {
        "ruff_max_errors": old_baseline,
        "mypy_max_errors": 279
    }
    with open(test_baseline, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f)

    # Ratchet must PASS and tighten
    ret = run_ratchet("ruff", baseline_path=str(test_baseline), auto_commit=False)
    assert ret == 0, "Ratchet should pass when errors improve"

    # Verify baseline was tightened down to actual current count
    loaded = load_baseline(str(test_baseline))
    assert loaded["ruff_max_errors"] == actual_ruff, f"Baseline should tighten from {old_baseline} down to {actual_ruff}"


def test_real_ruff_violation_triggers_failure(tmp_path):
    """
    Deliberately creates a Python file with a real Ruff violation (unused import F401)
    and verifies that the ratchet script detects the new violation and reports failure.
    """
    fake_code_dir = tmp_path / "fake_backend"
    fake_code_dir.mkdir()
    violation_file = fake_code_dir / "bad_code.py"
    violation_file.write_text("import sys\nimport os\n\nx = 1\n", encoding="utf-8")

    test_baseline = tmp_path / "ci_baseline.json"
    # Zero errors allowed
    baseline_data = {"ruff_max_errors": 0}
    with open(test_baseline, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f)

    # Run ratchet pointing to the directory with the deliberate violation
    ret = run_ratchet("ruff", baseline_path=str(test_baseline), auto_commit=False, custom_target=str(fake_code_dir))
    assert ret == 1, "Deliberate Ruff violation must trigger exit code 1"


def test_two_cycle_improvement_simulation(tmp_path):
    """
    Simulates two full improvement cycles:
    - Initial baseline: 930
    - Cycle 1: Fix 5 errors (count drops to 925) -> baseline auto-ratchets down to 925.
      Revert fix (count goes back to 930) -> ratchet FAILS (+5 regression).
    - Cycle 2: Fix 5 more errors (count drops to 920) -> baseline auto-ratchets down to 920.
      Revert fix (count goes back to 925) -> ratchet FAILS (+5 regression against 920).
    """
    test_baseline = tmp_path / "ci_baseline_simulation.json"
    initial_data = {"ruff_max_errors": 930, "mypy_max_errors": 279}
    with open(test_baseline, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    # Helper function simulating ratchet check with a mock error count
    def simulate_ratchet_check(tool_key: str, measured_count: int) -> int:
        data = load_baseline(str(test_baseline))
        limit = data[tool_key]
        if measured_count > limit:
            return 1  # Fails: regression
        elif measured_count < limit:
            data[tool_key] = measured_count
            save_baseline(data, str(test_baseline))
            return 0  # Passes: auto-ratchets down
        else:
            return 0  # Passes: held

    # CYCLE 1:
    # Step A: 5 errors fixed -> count drops from 930 to 925
    c1_pass = simulate_ratchet_check("ruff_max_errors", 925)
    assert c1_pass == 0
    assert load_baseline(str(test_baseline))["ruff_max_errors"] == 925, "Cycle 1 must tighten baseline to 925"

    # Step B: Revert the fix -> count returns to 930. CI must now FAIL against tightened baseline 925!
    c1_fail = simulate_ratchet_check("ruff_max_errors", 930)
    assert c1_fail == 1, "CI must fail because 930 exceeds tightened baseline 925"
    assert load_baseline(str(test_baseline))["ruff_max_errors"] == 925, "Baseline must remain at 925 on failure"

    # CYCLE 2:
    # Step A: 5 additional errors fixed -> count drops from 925 to 920
    c2_pass = simulate_ratchet_check("ruff_max_errors", 920)
    assert c2_pass == 0
    assert load_baseline(str(test_baseline))["ruff_max_errors"] == 920, "Cycle 2 must tighten baseline to 920"

    # Step B: Revert the fix -> count returns to 925. CI must now FAIL against tightened baseline 920!
    c2_fail = simulate_ratchet_check("ruff_max_errors", 925)
    assert c2_fail == 1, "CI must fail because 925 exceeds tightened baseline 920"
    assert load_baseline(str(test_baseline))["ruff_max_errors"] == 920, "Baseline must remain at 920 on failure"
