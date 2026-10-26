# -*- coding: utf-8 -*-
"""P1.2: delete the update-check cluster (snapshot p12_updatecluster.txt,
lines 48286-48827 as captured at baseline) plus the single following blank
line, byte-exact. Refuses to touch the file if the snapshot occurs any
number of times other than exactly once."""
import pathlib, sys

TREE = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py")
SNAP = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1a\snapshots\p12_updatecluster.txt")

data = TREE.read_bytes()
snap = SNAP.read_bytes()
n = data.count(snap)
if n != 1:
    print(f"ABORT: snapshot occurrences = {n}")
    sys.exit(2)
idx = data.find(snap)
after = data[idx + len(snap): idx + len(snap) + 2]
if after != b"\r\n":
    print("ABORT: expected a CRLF blank line right after the block, got", after)
    sys.exit(2)
end = idx + len(snap) + 2
new = data[:idx] + data[end:]
TREE.write_bytes(new)
print(f"removed {end-idx} bytes at offset {idx}; file {len(data)} -> {len(new)} bytes")
print("lines:", data.count(b"\n"), "->", new.count(b"\n"))
