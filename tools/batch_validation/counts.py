# -*- coding: utf-8 -*-
"""The 8 mandatory batch metrics, counted identically before/after.
Excludes this toolkit's own directory so the scripts do not match their own
pattern literals (e.g. `singleShot` in PATTERNS below) and baselines stay
comparable with batches #1–#3c.
Usage: python counts.py <repo_root> <out_path>"""
import os, re, sys

repo, out_path = sys.argv[1], sys.argv[2]

PATTERNS = [
    r"\.connect\(",
    r"QShortcut\(",
    r"create_shortcut\(",
    r"QTimer\(",
    r"timeout\.connect",
    r"QTimer\.timeout",
    r"singleShot",
    r"QMetaObject\.invokeMethod",
]

files = []
for dirpath, dirnames, filenames in os.walk(repo):
    dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", "batch_validation")]
    for fn in filenames:
        if fn.endswith(".py"):
            files.append(os.path.join(dirpath, fn))

lines = []
for pat in PATTERNS:
    rx = re.compile(pat)
    n = 0
    for fp in files:
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            for _ln in f:
                if rx.search(_ln):
                    n += 1
    lines.append(f"{pat}: {n}")

with open(out_path, "w", encoding="utf-8", newline="\n") as out:
    out.write("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"-> {out_path} ({len(files)} py files)")
