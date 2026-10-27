# -*- coding: utf-8 -*-
"""Batch P1-B negative probe (acceptance probe 4).

Proves: with NO pointer file and NO seam env var, the app's default branch
(build root) keeps data in <build_root>/Supervertaler and NEVER creates
%APPDATA%/Supervertaler (config.json pointer) or ~/Supervertaler.

To keep the default-branch build root inside the stage (and away from the
real E:\\Dev), the app runs from a git WORKTREE placed at
<stage>/negroot/SupervertalerPortable  ->  build root = <stage>/negroot.

Assertions (snapshot diff of the whole isolated profile, pre vs post):
  - <profile>/AppData/Roaming/Supervertaler  NOT created (no config.json);
  - <profile>/Supervertaler (the old ~ default) NOT created;
  - the only data dir that appears is <stage>/negroot/Supervertaler.

Run: python batch-p1b_probe_negative.py <worktree-root> <stage-dir> <tag>
Prints P1B-NEG-OK / P1B-NEG-FAILED.
"""
import faulthandler
import hashlib
import json
import os
import pathlib
import sys
import time

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]

iso = stage / "neg-iso"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
os.environ.pop("SUPERVERTALER_DATA_ROOT", None)  # negative: NO seam
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)

# the profile MUST NOT contain a pointer file for this run
assert not (iso / "AppData" / "Roaming" / "Supervertaler").exists(), "pre: APPDATA pointer dir exists"
assert not (iso / "Supervertaler").exists(), "pre: ~/Supervertaler exists"


def tree_state(root: pathlib.Path):
    state = {}
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        if p.is_file():
            state[rel] = "F:" + hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        else:
            state[rel] = "D"
    return state


failures = []


def check(name, cond, detail=""):
    print(f"[{tag}] {name}: {'ok' if cond else 'FAIL'} {detail}", flush=True)
    if not cond:
        failures.append(name)


faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))
t0 = time.time()
state0 = tree_state(iso)

import Supervertaler as SV  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
print(f"[{tag}] window built ({time.time()-t0:.1f}s)", flush=True)

expected_root = tree.parent / "Supervertaler"
check("default data root = <build_root>/Supervertaler",
      pathlib.Path(win.user_data_path).resolve() == expected_root,
      f"{win.user_data_path} (expected {expected_root})")

for _ in range(120):
    app.processEvents()
    time.sleep(0.05)

win._really_quit = True
win.close()
for _ in range(5):
    app.processEvents()
    time.sleep(0.1)

state1 = tree_state(iso)
created = sorted(set(state1) - set(state0))
check("APPDATA/.../Supervertaler not created",
      not (iso / "AppData" / "Roaming" / "Supervertaler").exists())
check("no config.json anywhere in profile",
      not [p for p in state1 if p.endswith("config.json")])
check("~/Supervertaler not created", not (iso / "Supervertaler").exists())
check("profile write-free",
      not [p for p in created if not p.startswith(("tmp", "Desktop", "Documents", "Downloads"))],
      f"created in profile: {created}")

out = {
    "tag": tag,
    "user_data_path": str(win.user_data_path),
    "expected_root": str(expected_root),
    "created_in_profile": created,
    "data_root_listing": sorted(p.name for p in expected_root.iterdir())
    if expected_root.exists() else [],
}
(stage / f"p1b_neg_{tag}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                           encoding="utf-8")

if failures:
    print(f"P1B-NEG-FAILED: {failures}", flush=True)
    sys.stdout.flush()
    os._exit(1)
print("P1B-NEG-OK", flush=True)
os._exit(0)
