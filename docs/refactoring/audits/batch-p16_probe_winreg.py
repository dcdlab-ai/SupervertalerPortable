# -*- coding: utf-8 -*-
r"""BATCH P1.6 probe M3: winreg tripwire during offscreen app start + popup.

sys.modules['winreg'] is replaced with a blocking object BEFORE any product
import: every attribute access (winreg.OpenKey, ...) records the name and
raises. Then the full app starts offscreen (P1-B seam, isolated profile) and
the QuickTrans popup is opened and closed (closeEvent writes quicktrans.ini).

Zero accesses = P16-WINREG-OK. Note (RECON P1.0 section 3): this catches the
PYTHON level only — C++-level QSettings NativeFormat writes bypass the winreg
module; they are covered by M2 (the main() insurance) and M4 (reg-query diff).

Run: python batch-p16_probe_winreg.py <tree-root> <iso-dir> <tag>
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

# --- M3 tripwire: ANY python-level registry access records + raises ---
ACCESS_LOG = []


class _WinregBlock:
    """Registry-call tripwire. Module-machinery attributes are inert on
    purpose: importlib.metadata & friends scan sys.modules and touch
    __spec__/__name__ on every entry — that is not a registry access.
    Every real registry function (OpenKey, QueryValue, ...) raises."""
    __spec__ = None
    __name__ = "winreg"
    __loader__ = None
    __package__ = "winreg"
    __path__ = None
    __file__ = None
    __doc__ = "P1.6 M3 tripwire (not the real winreg)"

    def __getattr__(self, name):
        ACCESS_LOG.append(name)
        raise RuntimeError(f"P16-M3 winreg access blocked: {name}")


sys.modules["winreg"] = _WinregBlock()
sys.modules["_winreg"] = _WinregBlock()

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)

data_dir = iso / "Supervertaler"
settings_file = data_dir / "workbench" / "settings" / "settings.json"
SEED = {
    "api_keys": {"custom_openai": "sk-seed-1234567890"},
    "general": {"restore_last_project": False, "global_ui_font_scale": 125},
    "ui": {}, "features": {},
}
settings_file.parent.mkdir(parents=True, exist_ok=True)
if settings_file.exists():
    settings_file.unlink()
settings_file.write_text(json.dumps(SEED, indent=2, ensure_ascii=False), encoding="utf-8")

faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))
t0 = time.time()

import Supervertaler as SV  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from modules.quicktrans import MTQuickPopup  # noqa: E402

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
print(f"[{tag}] full app built ({time.time()-t0:.1f}s)", flush=True)

for _ in range(40):
    app.processEvents()
    time.sleep(0.05)

# --- open the QuickTrans popup, close it (closeEvent saves the geometry) ---
MTQuickPopup.start_fetching = lambda self: None  # geometry probe, no network
popup = MTQuickPopup(win, "hello world")
popup.show()
for _ in range(10):
    app.processEvents()
popup.resize(640, 420)
popup.move(60, 40)
popup.close()
for _ in range(10):
    app.processEvents()
ini = iso / "quicktrans.ini"
print(f"[{tag}] popup closed, quicktrans.ini at seam root: {ini.exists()}", flush=True)

# graceful close (same discipline as batch-p1b_probe_app)
win._really_quit = True
win.close()
for _ in range(5):
    app.processEvents()
    time.sleep(0.1)

faulthandler.cancel_dump_traceback_later()
print(f"[{tag}] winreg accesses: {len(ACCESS_LOG)} {ACCESS_LOG}", flush=True)
if ACCESS_LOG:
    print("P16-WINREG-FAIL", flush=True)
    sys.stdout.flush()
    os._exit(1)
print("P16-WINREG-OK", flush=True)
sys.stdout.flush()
os._exit(0)
