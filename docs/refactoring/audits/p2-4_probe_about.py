"""BATCH P2.4, Part A.2: dev-runtime offscreen probe - Help -> About shows
v1.10.371 after the P2.4 pyproject/lock state (version string untouched).
Run: E:\\Dev\\python-embed\\python.exe -u p2-4_probe_about.py
"""
import os
import sys
import time
import traceback

REPO = r"E:\Dev\SupervertalerPortable"
STAGE = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p24"
sys.path.insert(0, REPO)
ISO = os.path.join(STAGE, "iso_about")
os.makedirs(os.path.join(ISO, "Supervertaler"), exist_ok=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SUPERVERTALER_DATA_ROOT"] = ISO
for var in ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA"):
    os.environ[var] = os.path.join(ISO, "_profile")
os.makedirs(os.environ["USERPROFILE"], exist_ok=True)
os.environ["TEMP"] = os.path.join(ISO, "_tmp")
os.environ["TMP"] = os.environ["TEMP"]
os.makedirs(os.environ["TEMP"], exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = os.path.join(ISO, "_pycache")

import faulthandler
faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)

ok = True
try:
    t0 = time.time()
    import Supervertaler as sv  # noqa
    print(f"[1] import OK {time.time()-t0:.1f}s version={sv.__version__}")
    from PyQt6.QtWidgets import QApplication, QDialog, QLabel
    app = QApplication.instance() or QApplication(sys.argv)
    t0 = time.time()
    mw = sv.SupervertalerQt()
    print(f"[2] offscreen start OK {time.time()-t0:.1f}s title={mw.windowTitle()!r}")

    captured = {}
    orig_exec = QDialog.exec
    def fake_exec(self, *a, **k):
        for lbl in self.findChildren(QLabel):
            t = lbl.text()
            if "Supervertaler Workbench v" in t:
                captured["title"] = t
        return QDialog.DialogCode.Rejected
    QDialog.exec = fake_exec
    mw.show_about()
    QDialog.exec = orig_exec
    title = captured.get("title", "")
    expected = f"Supervertaler Workbench v{sv.__version__}"
    good = expected in title and sv.__version__ == "1.10.371"
    ok = ok and good
    print(f"[3] about {'OK' if good else 'FAIL'} title={title!r}")

    mw.close()
    app.quit()
except Exception:
    ok = False
    traceback.print_exc()

print("P2.4 ABOUT PROBE:", "OK" if ok else "FAIL")
sys.stdout.flush()
os._exit(0 if ok else 1)
