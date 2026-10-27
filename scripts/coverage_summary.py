import json

with open("cov.json", "r", encoding="utf-8") as f:
    data = json.load(f)

totals = data["totals"]
cl = totals["covered_lines"]
sl = totals["num_statements"]
cb = totals["covered_branches"]
nb = totals["num_branches"]

line_pct = (cl / sl) * 100 if sl else 0
branch_pct = (cb / nb) * 100 if nb else 0
combined_pct = ((cl + cb) / (sl + nb)) * 100 if (sl + nb) else 0

print(f"Statement / Line Coverage: {cl} / {sl} ({line_pct:.2f}%)")
print(f"Branch Coverage (branch-only): {cb} / {nb} ({branch_pct:.2f}%)")
print(f"Combined Coverage: {cl + cb} / {sl + nb} ({combined_pct:.2f}%)")

print("\nFiles with missing branches:")
missing_branches_by_file = []
for filepath, fileinfo in data.get("files", {}).items():
    summary = fileinfo.get("summary", {})
    f_cb = summary.get("covered_branches", 0)
    f_nb = summary.get("num_branches", 0)
    missing = f_nb - f_cb
    if missing > 0:
        missing_branches_by_file.append((missing, f_cb, f_nb, filepath))

missing_branches_by_file.sort(reverse=True, key=lambda x: x[0])
for missing, f_cb, f_nb, filepath in missing_branches_by_file[:20]:
    pct = (f_cb / f_nb) * 100 if f_nb else 0
    print(f"  {missing:2d} missing branches ({f_cb}/{f_nb}, {pct:.1f}%): {filepath}")
