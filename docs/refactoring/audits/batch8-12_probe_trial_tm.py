# -*- coding: utf-8 -*-
"""Offscreen probe of the TRIAL worktree (Stage 2 p.2): app starts, TM tab
builds, Bridge column gone, remaining columns intact. Isolated profile
(arg1), tag arg2. Read-only. Run with CWD = wt-trial."""
import faulthandler
import os
import pathlib
import sys
import time

iso = pathlib.Path(sys.argv[1]).resolve()
tag = sys.argv[2]
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
for sub in ("Desktop", "Documents", "Downloads"):
    (iso / sub).mkdir(parents=True, exist_ok=True)
(iso / "tmp").mkdir(parents=True, exist_ok=True)

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, os.getcwd())
t0 = time.time()

from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
print(f"[{tag}] QApplication ok ({time.time()-t0:.1f}s)", flush=True)

import Supervertaler  # noqa: E402
print(f"[{tag}] import ok ({time.time()-t0:.1f}s)", flush=True)

import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog, QColorDialog, QInputDialog  # noqa: E402
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected
QDialog.open = lambda self, *a, **k: None
for cls in (QMessageBox, QFileDialog, QColorDialog, QInputDialog):
    for m in ("information", "warning", "critical", "question", "about",
              "getOpenFileName", "getSaveFileName", "getExistingDirectory",
              "getColor", "getText", "getInt"):
        if hasattr(cls, m):
            setattr(cls, m, staticmethod(lambda *a, **k: None))
print(f"[{tag}] modals neutralized", flush=True)

window = Supervertaler.SupervertalerQt()
print(f"[{tag}] SupervertalerQt constructed ({time.time()-t0:.1f}s)", flush=True)

tabs = window.main_tabs
labels = [tabs.tabText(i) for i in range(tabs.count())]
print(f"[{tag}] MAIN_TABS: {len(labels)} {labels}", flush=True)

for i, t in enumerate(labels):
    if "TMs" in t:
        tabs.setCurrentIndex(i)
        app.processEvents()
        break

from PyQt6.QtWidgets import QTableWidget  # noqa: E402
tm_table = None
for tb in window.findChildren(QTableWidget):
    hdr = [tb.horizontalHeaderItem(c).text() if tb.horizontalHeaderItem(c) else "" for c in range(tb.columnCount())]
    if any("TM Name" in h for h in hdr):
        tm_table = tb
        break
if tm_table is None:
    print(f"[{tag}] TM_TABLE: MISSING", flush=True)
else:
    hdr = [tm_table.horizontalHeaderItem(c).text() if tm_table.horizontalHeaderItem(c) else "" for c in range(tm_table.columnCount())]
    print(f"[{tag}] TM columns: {tm_table.columnCount()} headers: {hdr}", flush=True)
    print(f"[{tag}] BRIDGE_COL present: {any('Bridge' in h for h in hdr)}", flush=True)
    for r in range(min(tm_table.rowCount(), 3)):
        w3 = tm_table.cellWidget(r, 3); w4 = tm_table.cellWidget(r, 4); w5 = tm_table.cellWidget(r, 5)
        it6 = tm_table.item(r, 6)
        print(f"[{tag}] row {r}: w3={type(w3).__name__ if w3 else None} w4={type(w4).__name__ if w4 else None} w5={type(w5).__name__ if w5 else None} item6={it6.text() if it6 else None}", flush=True)
print(f"[{tag}] PROBE_DONE", flush=True)
os._exit(0)
