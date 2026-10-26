# -*- coding: utf-8 -*-
"""Batch P1-A: make runnable copies of suite probes that imported the removed
modules/usage_statistics.py.

Each copy is byte-identical to its original EXCEPT the exact two stub lines
  import modules.usage_statistics as _us  # noqa: E402
  _us.show_opt_in_dialog = lambda parent=None: False
which are deleted (the app no longer has the opt-in dialog at startup).
Copies are written to docs/refactoring/audits/ as batch-p1a_<orig>.py.
"""
import hashlib, pathlib, sys

AUD = pathlib.Path(r"E:\Dev\SupervertalerPortable\docs\refactoring\audits")
NAMES = [
    "batch9-4_probe_94h_fallback.py",
    "batch9-4_probe_94f_profiles.py",
    "batch9-4_probe_94d_qtchat.py",
    "batch9-4_probe_94c_statusbar.py",
    "batch9-3_probe_llm_e2e.py",
    "batch8-15_probe_window.py",
    "batch8-13_code_tools_smoke.py",
    "batch8-15_regress_termbase.py",
    "batch8-15_probe_about.py",
    "batch9-4_probe_94a_save.py",
    "r9_probe_profiles.py",
]
STUB1 = "import modules.usage_statistics as _us  # noqa: E402\n"
STUB2 = "_us.show_opt_in_dialog = lambda parent=None: False\n"

out = []
for name in NAMES:
    data = (AUD / name).read_bytes().decode("utf-8")
    lines = data.splitlines(keepends=True)
    idx1 = [i for i, l in enumerate(lines) if l.rstrip("\r\n") == STUB1.rstrip("\r\n")]
    assert len(idx1) == 1, (name, idx1)
    i1 = idx1[0]
    assert lines[i1 + 1].rstrip("\r\n") == STUB2.rstrip("\r\n"), (name, i1 + 1)
    new = lines[:i1] + lines[i1 + 2:]
    if name == "batch8-13_code_tools_smoke.py":
        # P1.2 removed check_for_updates: drop the Tools-smoke item
        # ("Help/Check-for-Updates", lambda: win.check_for_updates()),
        # baseline 42 items -> 41. The canonical 8.13 script itself stays
        # untouched as the historical baseline table.
        item = '    ("Help/Check-for-Updates", lambda: win.check_for_updates()),\n'
        idx2 = [i for i, l in enumerate(new) if l.rstrip("\r\n") == item.rstrip("\r\n")]
        assert len(idx2) == 1, (name, idx2)
        new = new[:idx2[0]] + new[idx2[0] + 1:]
        print(f"{name}: removed smoke item at line {idx2[0]+1}")
    copy = AUD / f"batch-p1a_{name}"
    copy.write_bytes("".join(new).encode("utf-8"))
    assert "usage_statistics" not in "".join(new) and "_us." not in "".join(new), name
    out.append(f"{hashlib.sha256(copy.read_bytes()).hexdigest()}  {copy.name}  removed lines {i1+1},{i1+2} of {name}")

print("\n".join(out))
print("COPIES:", len(out))
