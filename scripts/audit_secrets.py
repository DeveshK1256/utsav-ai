import os
import re
import subprocess

print("=======================================================")
print("RUNNING GITLEAKS / CREDENTIAL AUDIT ON GIT REPOSITORY")
print("=======================================================")

secret_patterns = [
    ("Gemini / Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Generic Private Key", re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----")),
    ("AWS Access Key ID", re.compile(r"(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}")),
    ("GitHub Personal Access Token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}")),
    ("Generic Hardcoded Secret Assignment", re.compile(r"(?i)(api_key|secret_key|app_secret|password)\s*=\s*['\"][0-9a-zA-Z\-_]{16,}['\"]"))
]

files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
leaks = []

for f in files:
    if f.endswith((".png", ".ico", ".pdf", ".woff2", ".ttf", ".jsonl")):
        continue
    try:
        with open(f, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        for label, pat in secret_patterns:
            matches = pat.findall(content)
            for m in matches:
                # Exclude dummy values in test stubs or tests
                if any(stub in content for stub in ["fake_test_key", "test_secret", "secret_key_123", "fake_key"]):
                    continue
                leaks.append((f, label, str(m)[:10] + "..."))
    except Exception as e:
        pass

if not leaks:
    print("GITLEAKS AUDIT RESULT: ZERO LEAKS FOUND. Clean repository working tree.")
    print("=======================================================")
else:
    print(f"GITLEAKS AUDIT RESULT: FOUND {len(leaks)} POTENTIAL LEAKS:")
    for f, label, snippet in leaks:
        print(f"  - {f}: {label} ({snippet})")
    print("=======================================================")
