# -*- coding: utf-8 -*-
"""Batch P1-A: verify each git diff removal is byte-identical to its snapshot block.

Compares the '-' lines of the current `git diff` against the stage snapshots.
Each snapshot block must appear exactly once as a contiguous run of removed
lines (plus blank-line context accounting: snapshots include the trailing
blank line, git diff renders it as a removed line too).
"""
import hashlib, pathlib, subprocess, sys

TREE = pathlib.Path(r"E:\Dev\SupervertalerPortable")
SNAP = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1a\snapshots")

def run_diff():
    p = subprocess.run(["git", "diff", "--", "Supervertaler.py"],
                       cwd=str(TREE), capture_output=True)
    return p.stdout.decode("utf-8", errors="replace")

diff = run_diff()
# collect contiguous runs of removed lines per hunk
runs = []
cur = []
for ln in diff.splitlines(keepends=True):
    if ln.startswith("---") or ln.startswith("+++") or ln.startswith("@@"):
        if cur:
            runs.append("".join(cur)); cur = []
    elif ln.startswith("-"):
        cur.append(ln[1:])
    else:
        if cur:
            runs.append("".join(cur)); cur = []
if cur:
    runs.append("".join(cur))

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

targets = {f.name[:-4]: (SNAP / f.name).read_bytes() for f in SNAP.glob("*.txt")}
# normalize runs: git diff strips '\n' at line end? No — splitlines(keepends=True) on text
# keeps \r\n when present. Snapshots were taken with keepends -> identical byte shape.
ok, bad = [], []
for name, blob in targets.items():
    found = [r for r in runs if r == blob]
    if len(found) == 1:
        ok.append(name)
    elif len(found) == 0:
        # try LF-normalized comparison (git diff may have normalized CRLF);
        # also accept one extra trailing blank line (separators between methods
        # deleted together with whole-method blocks)
        n1 = blob.replace(b"\r\n", b"\n").decode("utf-8")
        found = [r for r in runs if r.replace("\r\n", "\n") == n1]
        tag = " (LF-normalized hunk)"
        if not found:
            found = [r for r in runs if r.replace("\r\n", "\n") == n1 + "\n"]
            tag = " (LF-normalized hunk + 1 trailing blank)"
        if len(found) == 1:
            ok.append(name + tag)
        else:
            bad.append(name)
    else:
        bad.append(name + f" (x{len(found)})")

# extra removed lines beyond expected blocks?
total_removed = sum(len(r.splitlines()) for r in runs)
expected_lines = sum(len(b.splitlines()) for b in targets.values())
print("removed runs lines:", total_removed, " expected (snapshots):", expected_lines)
for n in sorted(ok):
    print("OK  ", n)
for n in sorted(bad):
    print("BAD ", n)
sys.exit(1 if bad else 0)
