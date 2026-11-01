"""BATCH P2.4: site-packages name==version comparison,
P2.1 distributive (dev-runtime copy) vs P2.4 distributive (built from lock).
Prints the was/became table for the report.
"""
import email
import os
import re

SP21 = (r"E:\Dev\Work_temp\SupervertalerPortable\refactoring"
        r"\batch-p21\unpacked\python-embed\Lib\site-packages")
SP24 = sys_arg = None
import sys
SP24 = sys.argv[1]

norm = lambda s: re.sub(r"[-_.]+", "-", s.lower())


def inventory(sp):
    inv = {}
    for entry in os.listdir(sp):
        if not entry.endswith(".dist-info"):
            continue
        with open(os.path.join(sp, entry, "METADATA"),
                  encoding="utf-8", errors="replace") as f:
            msg = email.message_from_file(f)
        inv[norm(msg.get("Name", entry))] = msg.get("Version", "?")
    return inv


inv21 = inventory(SP21)
inv24 = inventory(SP24)
allnames = sorted(set(inv21) | set(inv24))
print(f"P2.1: {len(inv21)} dist-infos; P2.4: {len(inv24)} dist-infos\n")
print(f"{'package':24} | P2.1 (was) | P2.4 (became)")
removed, added, changed = [], [], []
for n in allnames:
    a, b = inv21.get(n), inv24.get(n)
    if a and b:
        mark = "" if a == b else f"  <-- VERSION MISMATCH"
        if a != b:
            changed.append(n)
        print(f"{n:24} | {a:10} | {b:10}{mark}")
    elif a:
        print(f"{n:24} | {a:10} | REMOVED")
        removed.append(n)
    else:
        print(f"{n:24} | -          | {b} (ADDED)")
        added.append(n)
print(f"\nremoved: {removed}")
print(f"added: {added}")
print(f"version mismatches: {changed}")
