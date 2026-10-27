#!/usr/bin/env python3
"""
CI Quality Ratchet Gate
Enforces that Ruff lint and MyPy static typing errors never exceed the committed baseline.
Converts report-only lint checks into hard blocking CI gates without requiring unrealistic all-at-once cleanup.
"""

import sys
import os
import json
import subprocess
import re

BASELINE_PATH = os.path.join(os.path.dirname(__file__), "..", ".github", "ci_baseline.json")

def load_baseline():
    if not os.path.exists(BASELINE_PATH):
        print(f"::error::Baseline file not found at {BASELINE_PATH}")
        sys.exit(1)
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def check_ruff(baseline_limit: int):
    print("=======================================================")
    print(f"RUNNING RUFF QUALITY RATCHET GATE (Baseline max: {baseline_limit})")
    print("=======================================================")
    cmd = [sys.executable, "-m", "ruff", "check", "backend/", "--output-format=json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        errors = json.loads(res.stdout) if res.stdout.strip() else []
        count = len(errors)
    except Exception as e:
        # Fallback to counting text lines if json parsing fails
        lines = [l for l in res.stdout.splitlines() if ":" in l and ("error" in l or "warning" in l)]
        count = len(lines)
    
    print(f"Current Ruff error count: {count}")
    if count <= baseline_limit:
        print(f"PASS: Ruff errors ({count}) are at or below baseline limit ({baseline_limit}). Ratchet held.")
        sys.exit(0)
    else:
        diff = count - baseline_limit
        print(f"::error::Ruff quality ratchet FAILED! Current errors ({count}) exceed baseline ({baseline_limit}) by +{diff}.")
        print("Please resolve the new linting errors before merging.")
        sys.exit(1)

def check_mypy(baseline_limit: int):
    print("=======================================================")
    print(f"RUNNING MYPY QUALITY RATCHET GATE (Baseline max: {baseline_limit})")
    print("=======================================================")
    cmd = [sys.executable, "-m", "mypy", "backend/app", "--explicit-package-bases", "--ignore-missing-imports"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    output = res.stdout + "\n" + res.stderr
    print(output)
    
    match = re.search(r"Found (\d+) errors in \d+ files", output)
    if match:
        count = int(match.group(1))
    elif "Success: no issues found" in output:
        count = 0
    else:
        # Fallback to counting error lines
        error_lines = [l for l in output.splitlines() if ": error:" in l]
        count = len(error_lines)
        
    print(f"Current MyPy error count: {count}")
    if count <= baseline_limit:
        print(f"PASS: MyPy errors ({count}) are at or below baseline limit ({baseline_limit}). Ratchet held.")
        sys.exit(0)
    else:
        diff = count - baseline_limit
        print(f"::error::MyPy quality ratchet FAILED! Current errors ({count}) exceed baseline ({baseline_limit}) by +{diff}.")
        print("Please resolve the newly introduced type errors before merging.")
        sys.exit(1)

if __name__ == "__main__":
    tool = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    baseline = load_baseline()
    
    if tool == "ruff":
        check_ruff(baseline.get("ruff_max_errors", 932))
    elif tool == "mypy":
        check_mypy(baseline.get("mypy_max_errors", 279))
    else:
        print(f"Usage: {sys.argv[0]} [ruff|mypy]")
        sys.exit(1)
