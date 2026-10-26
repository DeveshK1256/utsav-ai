import os
import re

frontend_dir = r"d:\Utsav\frontend"

def check_case_exact(path):
    parts = os.path.relpath(path, frontend_dir).replace("\\", "/").split("/")
    cur = frontend_dir
    for part in parts:
        if part in (".", ""):
            continue
        try:
            actual_entries = os.listdir(cur)
        except Exception:
            return False, f"Directory does not exist: {cur}"
        if part not in actual_entries:
            # Check if case mismatch
            matching = [e for e in actual_entries if e.lower() == part.lower()]
            if matching:
                return False, f"Case mismatch: '{part}' vs actual '{matching[0]}' in {cur}"
            else:
                return False, f"Entry '{part}' not found in {cur}"
        cur = os.path.join(cur, part)
    return True, "OK"

for root, dirs, files in os.walk(frontend_dir):
    if any(x in root for x in ['node_modules', '.next', 'out']):
        continue
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", content)
            for imp in imports:
                if imp.startswith(('.', '@/')):
                    if imp.startswith('@/'):
                        target = os.path.join(frontend_dir, imp[2:])
                    else:
                        target = os.path.normpath(os.path.join(root, imp))
                    
                    found_ext = None
                    for ext in ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx']:
                        cand = target + ext
                        if os.path.exists(cand):
                            ok, msg = check_case_exact(cand)
                            if not ok:
                                print(f"CASE ERROR in {os.path.relpath(filepath, frontend_dir)}: {imp} -> {msg}")
                            found_ext = ext
                            break
                    if found_ext is None:
                        print(f"NOT FOUND in {os.path.relpath(filepath, frontend_dir)}: {imp}")
print("Case check done.")
