# -*- coding: utf-8 -*-
"""Batch P1-A UI snapshot probe (runs pre and post on the same code path).

Snapshots: tray context-menu items, Settings-tab QGroupBox titles, Help menu
items, About dialog buttons (QDialog.exec monkeypatched), settings.json
sha256 seeded/after-build/after-close.

Run: python batch-p1a_probe_ui.py <tree-root> <iso-dir> <pre|post>
Offscreen, isolated profile. Instance takes ~1-2 min.
"""
import faulthandler, hashlib, json, os, pathlib, sys, time

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
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg_dir = iso / "AppData" / "Roaming" / "Supervertaler"
cfg_dir.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
data_dir.mkdir(parents=True, exist_ok=True)
(cfg_dir / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8")

# Seed unified settings with the inert usage_statistics_* keys so the byte
# check has content to compare (pre-run code reads them, must not rewrite).
seed = {
    "api_keys": {}, "general": {"restore_last_project": False},
    "ui": {}, "features": {},
    "usage_statistics_enabled": False,
    "usage_statistics_asked": True,
    "usage_statistics_id": "seed-00000000-0000-0000-0000-000000000000",
}
settings_file = data_dir / "workbench" / "settings" / "settings.json"
settings_file.parent.mkdir(parents=True, exist_ok=True)
if settings_file.exists():
    settings_file.unlink()
settings_file.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")

faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))
t0 = time.time()

def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

sha_seeded = sha(settings_file)

import Supervertaler as SV  # noqa: E402
from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtGui import QAction  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication, QDialog, QGroupBox, QLabel, QPushButton, QSystemTrayIcon)

app = QApplication(sys.argv)
print(f"[{tag}] QApplication ok ({time.time()-t0:.1f}s)", flush=True)

dialogs = []
_real_exec = QDialog.exec

def _capture_exec(self, *a, **k):
    dialogs.append({
        "title": self.windowTitle(),
        "buttons": [b.text() for b in self.findChildren(QPushButton)],
        "labels": [l.text() for l in self.findChildren(QLabel)][:12],
    })
    return QDialog.DialogCode.Rejected

QDialog.exec = lambda self, *a, **k: _capture_exec(self, *a, **k)
QSystemTrayIcon.isSystemTrayAvailable = staticmethod(lambda: True)

try:
    win = SV.SupervertalerQt()
    print(f"[{tag}] window built ({time.time()-t0:.1f}s)", flush=True)
except Exception as e:
    import traceback
    print(f"[{tag}] CONSTRUCT FAILED: {e!r}", flush=True)
    traceback.print_exc()
    os._exit(2)

sha_after_build = sha(settings_file)

# tray menu (main() normally calls this after __init__)
win._setup_tray_icon()
tray_menu = win._tray_icon.contextMenu() if win._tray_icon is not None else None
tray_items = []
if tray_menu is not None:
    for a in tray_menu.actions():
        tray_items.append(a.text() if a.text() else "---")
print(f"[{tag}] TRAY MENU: {tray_items}", flush=True)

# Settings tab group boxes
settings_groups = []
idx = getattr(win, "settings_tab_index", None)
if idx is not None and hasattr(win, "main_tabs"):
    w = win.main_tabs.widget(idx)
    if w is not None:
        settings_groups = [g.title() for g in w.findChildren(QGroupBox)]
print(f"[{tag}] SETTINGS GROUPS: {settings_groups}", flush=True)

# Help menu items
help_items = []
bar = win.menuBar()
from PyQt6.QtWidgets import QMenu  # noqa: E402
for act in bar.actions():
    m = act.menu()
    title = (act.text() or (m.title() if m is not None else ""))
    if title and ("help" in title.lower() or "справ" in title.lower()):
        help_items = [a.text() if a.text() else "---" for a in m.actions()]
        break
print(f"[{tag}] HELP MENU: {help_items}", flush=True)

# About dialog buttons
about = {}
for a in win.findChildren(QAction):
    if a.text() and "about" in a.text().lower():
        n0 = len(dialogs)
        try:
            a.trigger()
            app.processEvents()
        except SystemExit:
            raise
        except BaseException as e:
            print(f"[{tag}] EXC on {a.text()}: {type(e).__name__}: {e}", flush=True)
        if len(dialogs) > n0:
            about = dialogs[-1]
            break
print(f"[{tag}] ABOUT DIALOG: {about}", flush=True)

# graceful close, then final settings.json sha
win._really_quit = True
win.close()
for _ in range(5):
    app.processEvents()
    time.sleep(0.1)
sha_after_close = sha(settings_file)

out = {
    "tag": tag,
    "tray_available": win._tray_icon is not None,
    "tray_items": tray_items,
    "settings_groups": settings_groups,
    "help_items": help_items,
    "about": about,
    "settings_json_path": str(settings_file),
    "sha_seeded": sha_seeded,
    "sha_after_build": sha_after_build,
    "sha_after_close": sha_after_close,
    "bytes_stable": sha_seeded == sha_after_close,
}
(iso / f"snapshot_{tag}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[{tag}] SNAPSHOT WRITTEN bytes_stable={out['bytes_stable']}", flush=True)
os._exit(0)
