# -*- coding: utf-8 -*-
"""Grep constructor/name call sites across all .py files of a repo root.
Usage: python callsites.py <repo_root> <regex> <out_path>"""
import os, re, sys

repo, pattern, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
rx = re.compile(pattern)

with open(out_path, "w", encoding="utf-8", newline="\n") as out:
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", "batch_validation")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dirpath, fn)
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                for i, ln in enumerate(f, 1):
                    if rx.search(ln):
                        out.write(f"{os.path.relpath(fp, repo).replace(os.sep, '/')}:{i}: {ln.rstrip()}\n")
print(f"-> {out_path}")
