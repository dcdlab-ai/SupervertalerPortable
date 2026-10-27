# -*- coding: utf-8 -*-
"""Batch P1-B Settings-groups snapshot probe (acceptance probe 5).

Run against TWO trees with the SAME script: a git worktree at HEAD (before)
and the working tree (after); the diff of the printed SETTINGS GROUPS list
must be exactly one removed group: "Data Folder Location".

The seam env var is set in both runs (HEAD code ignores it and resolves
~/Supervertaler = <iso>/Supervertaler anyway, so both runs use the same data
dir); no pointer is seeded (the before-run's auto-recovery would write one
into the isolated APPDATA only if <iso>/Supervertaler has content — seeding
nothing keeps the before-run write-free too).

Run: python batch-p1b_probe_groups.py <tree-root> <iso-dir> <tag>
Writes <iso>/p1b_groups_<tag>.json.
"""
import faulthandler
import json
import os
import pathlib
import sys
import time

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam (ignored by HEAD)
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)

faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))
t0 = time.time()

import Supervertaler as SV  # noqa: E402
from PyQt6.QtWidgets import QApplication, QGroupBox  # noqa: E402

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
print(f"[{tag}] window built ({time.time()-t0:.1f}s)", flush=True)

settings_groups = []
idx = getattr(win, "settings_tab_index", None)
if idx is not None and hasattr(win, "main_tabs"):
    w = win.main_tabs.widget(idx)
    if w is not None:
        settings_groups = [g.title() for g in w.findChildren(QGroupBox)]
print(f"[{tag}] SETTINGS GROUPS: {settings_groups}", flush=True)

out = {
    "tag": tag,
    "settings_groups": settings_groups,
    "user_data_path": str(win.user_data_path),
}
(iso / f"p1b_groups_{tag}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
win._really_quit = True
win.close()
for _ in range(5):
    app.processEvents()
    time.sleep(0.1)
os._exit(0)
