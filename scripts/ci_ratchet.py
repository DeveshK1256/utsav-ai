#!/usr/bin/env python3
"""
CI Quality Ratchet Gate
Enforces that Ruff lint and MyPy static typing errors never exceed the committed baseline.
Crucially, when the current error count is LOWER than the baseline, the ratchet automatically
tightens: it rewrites the baseline file with the new lower number. The baseline only ever
moves down, never up.
"""

import sys
import os
import json
import subprocess
import re
import argparse

DEFAULT_BASELINE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".github", "ci_baseline.json")
)


def load_baseline(baseline_path: str = DEFAULT_BASELINE_PATH) -> dict:
    if not os.path.exists(baseline_path):
        print(f"::error::Baseline file not found at {baseline_path}")
        sys.exit(1)
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_baseline(data: dict, baseline_path: str = DEFAULT_BASELINE_PATH) -> None:
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def get_ruff_error_count(target_dir: str = "backend/") -> int:
    cmd = [sys.executable, "-m", "ruff", "check", target_dir, "--output-format=json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        errors = json.loads(res.stdout) if res.stdout.strip() else []
        return len(errors)
    except Exception:
        # Fallback to counting text lines if json parsing fails
        lines = [l for l in res.stdout.splitlines() if ":" in l and ("error" in l or "warning" in l)]
        return len(lines)


def get_mypy_error_count(target_dir: str = "backend/app") -> int:
    cmd = [sys.executable, "-m", "mypy", target_dir, "--explicit-package-bases", "--ignore-missing-imports"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    output = res.stdout + "\n" + res.stderr
    print(output.strip())

    match = re.search(r"Found (\d+) errors in \d+ files", output)
    if match:
        return int(match.group(1))
    elif "Success: no issues found" in output:
        return 0
    else:
        error_lines = [l for l in output.splitlines() if ": error:" in l]
        return len(error_lines)


def commit_baseline_update(baseline_path: str, tool: str, old_count: int, new_count: int) -> None:
    try:
        status_res = subprocess.run(["git", "status", "--porcelain", baseline_path], capture_output=True, text=True)
        if not status_res.stdout.strip():
            return

        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=False, capture_output=True)
        subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False, capture_output=True)
        subprocess.run(["git", "add", baseline_path], check=True, capture_output=True)
        msg = f"chore(ci): ratchet {tool} baseline down from {old_count} to {new_count} (-{old_count - new_count})"
        commit_res = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
        if commit_res.returncode == 0:
            print(f"Auto-committed updated baseline: {msg}")
    except Exception as e:
        print(f"Notice: Auto-commit skipped ({e})")


def run_ratchet(
    tool: str,
    baseline_path: str = DEFAULT_BASELINE_PATH,
    auto_commit: bool = False,
    custom_target: str = None
) -> int:
    baseline_data = load_baseline(baseline_path)
    tool_lower = tool.lower()

    if tool_lower == "ruff":
        key = "ruff_max_errors"
        target = custom_target or "backend/"
        count = get_ruff_error_count(target)
    elif tool_lower == "mypy":
        key = "mypy_max_errors"
        target = custom_target or "backend/app"
        count = get_mypy_error_count(target)
    else:
        print(f"::error::Unknown ratchet tool '{tool}'. Expected 'ruff' or 'mypy'.")
        return 1

    baseline_limit = baseline_data.get(key, 0)
    print("=======================================================")
    print(f"RUNNING {tool.upper()} QUALITY RATCHET GATE")
    print(f"Committed Baseline Limit: {baseline_limit}")
    print(f"Current Measured Errors: {count}")
    print("=======================================================")

    if count > baseline_limit:
        diff = count - baseline_limit
        print(f"::error::{tool.upper()} quality ratchet FAILED! Current errors ({count}) exceed baseline ({baseline_limit}) by +{diff}.")
        print(f"::error::Ratchet rule: Baseline ({baseline_limit}) will NEVER be raised. Please resolve the regression before merging.")
        return 1
    elif count < baseline_limit:
        diff = baseline_limit - count
        print(f"[RATCHET TIGHTENED] {tool.upper()} errors improved from {baseline_limit} down to {count} (-{diff} errors).")
        print(f"Rewriting {baseline_path} with new tightened baseline {count}...")
        baseline_data[key] = count
        save_baseline(baseline_data, baseline_path)
        print(f"PASS: Baseline updated to {count}. The bar has been permanently raised.")

        if auto_commit:
            commit_baseline_update(baseline_path, tool, baseline_limit, count)
        return 0
    else:
        print(f"PASS: {tool.upper()} errors ({count}) match baseline limit ({baseline_limit}). Ratchet held.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="CI Quality Ratchet Gate")
    parser.add_argument("tool", choices=["ruff", "mypy"], help="Linter/typechecker tool to run ratchet check on")
    parser.add_argument("--baseline-file", default=DEFAULT_BASELINE_PATH, help="Path to ci_baseline.json")
    parser.add_argument("--auto-commit", action="store_true", help="Auto-commit updated baseline if tightened")
    parser.add_argument("--target", default=None, help="Custom target directory for the tool")

    args = parser.parse_args()
    code = run_ratchet(
        tool=args.tool,
        baseline_path=args.baseline_file,
        auto_commit=args.auto_commit,
        custom_target=args.target
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
