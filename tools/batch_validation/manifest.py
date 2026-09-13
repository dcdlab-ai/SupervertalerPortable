# -*- coding: utf-8 -*-
"""SHA256 manifest of all .py files under a repo root (recursive, skips
__pycache__/.git and this toolkit's own directory, so batch baselines stay
comparable). Usage: python manifest.py <repo_root> <out_path>"""
import hashlib, os, sys

repo, out_path = sys.argv[1], sys.argv[2]

entries = []
for dirpath, dirnames, filenames in os.walk(repo):
    dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", "batch_validation")]
    for fn in filenames:
        if fn.endswith(".py"):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, repo).replace("\\", "/")
            with open(full, "rb") as f:
                data = f.read()
            entries.append((rel, hashlib.sha256(data).hexdigest()))

entries.sort()
with open(out_path, "w", encoding="utf-8", newline="\n") as out:
    for rel, h in entries:
        out.write(f"{h}  {rel}\n")
print(f"{len(entries)} files -> {out_path}")
