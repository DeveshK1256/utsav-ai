"""
Deterministic CI Test Runner
Executes pytest and outputs clear annotations for GitHub Actions on any failure.
"""
import sys
import subprocess

def run_suite(suite_dir: str):
    print(f"\n=======================================================")
    print(f"RUNNING TEST SUITE: {suite_dir}")
    print(f"=======================================================\n")
    cmd = [sys.executable, "-m", "pytest", suite_dir, "-v", "--tb=short"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    print(res.stdout)
    if res.stderr:
        print("STDERR:\n", res.stderr)
        
    if res.returncode != 0:
        print(f"\n::error::Test suite {suite_dir} FAILED with exit code {res.returncode}")
        # Print failed lines specifically as GitHub Actions errors
        for line in res.stdout.splitlines():
            if line.startswith("FAILED ") or line.startswith("ERROR "):
                print(f"::error file={suite_dir}::{line}")
        sys.exit(res.returncode)

if __name__ == "__main__":
    suite = sys.argv[1] if len(sys.argv) > 1 else "tests/unit/"
    run_suite(suite)
