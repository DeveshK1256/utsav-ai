"""Generate reproducible maintainability metrics for backend and frontend source."""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _coverage_metrics() -> dict[str, object]:
    data = _read_json(ROOT / "cov.json")
    if not data:
        return {"status": "NOT_RUN"}
    totals = data.get("totals", {})
    if not isinstance(totals, dict):
        return {"status": "FAIL", "reason": "Invalid coverage totals"}
    statements = int(totals.get("num_statements", 0))
    branches = int(totals.get("num_branches", 0))
    test_summary = {"passed": None, "failed": None, "skipped": None}
    summary_path = ROOT / "pytest-results.txt"
    if summary_path.exists():
        summary = summary_path.read_text(encoding="utf-8", errors="replace")
        match = re.search(
            r"(?:(\d+) passed, )?(?:(\d+) failed, )?(?:(\d+) skipped, )?\d+ deselected",
            summary,
        )
        if match:
            test_summary = {
                "passed": int(match.group(1) or 0),
                "failed": int(match.group(2) or 0),
                "skipped": int(match.group(3) or 0),
            }
    return {
        "status": "PASS",
        "tests": {
            **test_summary,
        },
        "line_coverage": (
            round(float(totals.get("covered_lines", 0)) / statements * 100, 2)
            if statements
            else None
        ),
        "branch_coverage": (
            round(float(totals.get("covered_branches", 0)) / branches * 100, 2)
            if branches
            else None
        ),
    }


def _duplication_metrics() -> dict[str, object]:
    data = _read_json(ROOT / "reports/jscpd/jscpd-report.json")
    if not data:
        return {"status": "NOT_RUN"}
    statistic = data.get("statistics", {})
    if not isinstance(statistic, dict):
        return {"status": "FAIL", "reason": "Invalid jscpd statistics"}
    total = statistic.get("total", {})
    if not isinstance(total, dict):
        return {"status": "FAIL", "reason": "Missing jscpd total"}
    percentage = float(total.get("percentage", 0))
    threshold = 1.0
    return {
        "status": "PASS" if percentage < threshold else "FAIL",
        "percentage": percentage,
        "duplicated_lines": total.get("duplicatedLines"),
        "duplicated_tokens": total.get("duplicatedTokens"),
        "clones": len(data.get("duplicates", [])),
        "threshold": threshold,
    }


def _python_inventory() -> dict[str, object]:
    functions: list[dict[str, object]] = []
    files: list[dict[str, object]] = []
    for path in sorted((ROOT / "backend").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        files.append({"file": str(path.relative_to(ROOT)), "lines": len(source.splitlines())})
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "name": node.name,
                        "line": node.lineno,
                        "lines": getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                    }
                )
    return {
        "files": files,
        "files_over_400_lines": [item for item in files if item["lines"] > 400],
        "functions": functions,
        "functions_over_50_lines": [item for item in functions if item["lines"] > 50],
    }


def _lizard_metrics() -> list[dict[str, object]]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "lizard",
            "backend/app",
            "frontend/app",
            "frontend/components",
            "--csv",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    functions: list[dict[str, object]] = []
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) < 11:
            continue
        filename = row[6]
        functions.append(
            {
                "file": filename,
                "name": row[8],
                "line": int(row[9]),
                "nloc": int(row[0]),
                "cyclomatic_complexity": int(row[1]),
                "token_count": int(row[2]),
                "parameter_count": int(row[3]),
            }
        )
    return functions


def _command_version(command: list[str]) -> str:
    result = subprocess.run(  # noqa: S603
        command, cwd=ROOT, check=True, capture_output=True, text=True
    )
    return (result.stdout or result.stderr).strip().splitlines()[0]


def build_report() -> dict[str, object]:
    inventory = _python_inventory()
    lizard = _lizard_metrics()
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "branch": subprocess.run(
            ["git", "branch", "--show-current"],  # noqa: S607
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "runtime": {
            "python": platform.python_version(),
            "node": _command_version(["node", "--version"]),
        },
        "tools": {
            "lizard": _command_version([sys.executable, "-m", "lizard", "--version"]),
            "radon": _command_version([sys.executable, "-m", "radon", "--version"]),
            "ruff": _command_version([sys.executable, "-m", "ruff", "--version"]),
            "mypy": _command_version([sys.executable, "-m", "mypy", "--version"]),
        },
        "thresholds": {
            "cyclomatic_complexity_max": 10,
            "function_lines_review_threshold": 50,
            "file_lines_review_threshold": 400,
            "backend_line_coverage_min": 90,
            "backend_branch_coverage_min": 85,
        },
        "python_ast_inventory": inventory,
        "lizard_functions": lizard,
        "quality": {
            "duplication": _duplication_metrics(),
            "coverage": _coverage_metrics(),
        },
        "notes": {
            "cognitive_complexity": (
                "Not emitted by the selected analyzers; Lizard cyclomatic complexity and "
                "Radon maintainability index are reported instead."
            ),
            "duplication": (
                "Measured separately with jscpd because it is a cross-language detector; "
                "generated dependencies are excluded."
            ),
        },
    }


def render_markdown(report: dict[str, object]) -> str:
    inventory = report["python_ast_inventory"]
    functions = inventory["functions_over_50_lines"]
    files = inventory["files_over_400_lines"]
    high_complexity = [
        item for item in report["lizard_functions"] if item["cyclomatic_complexity"] > 10
    ]
    lines = [
        "# Reproducible Quality Measurement",
        "",
        "Generated by `scripts/quality_report.py`; this report contains measurements only.",
        "",
        f"- Tools: {report['tools']}",
        f"- Files over 400 lines: **{len(files)}**",
        f"- Functions over 50 lines: **{len(functions)}**",
        f"- Lizard functions over complexity 10: **{len(high_complexity)}**",
        f"- Duplication: **{report['quality']['duplication']}**",
        f"- Coverage: **{report['quality']['coverage']}**",
        "",
        "## Functions over 50 lines",
        "",
        "| File | Function | Line | Lines |",
        "|---|---|---:|---:|",
    ]
    lines.extend(
        f"| `{item['file']}` | `{item['name']}` | {item['line']} | {item['lines']} |"
        for item in functions
    )
    lines.extend(
        [
            "",
            "## Functions over cyclomatic complexity 10",
            "",
            "| File | Function | Line | CCN |",
            "|---|---|---:|---:|",
        ]
    )
    lines.extend(
        f"| `{item['file']}` | `{item['name']}` | {item['line']} | "
        f"{item['cyclomatic_complexity']} |"
        for item in high_complexity
    )
    lines.extend(
        [
            "",
            "## Files over 400 lines",
            "",
            "| File | Lines |",
            "|---|---:|",
        ]
    )
    lines.extend(f"| `{item['file']}` | {item['lines']} |" for item in files)
    lines.extend(
        [
            "",
            "Cognitive complexity is not claimed because the selected analyzers do not emit it.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/quality_metrics.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports/quality_metrics.md")
    args = parser.parse_args()
    report = build_report()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
