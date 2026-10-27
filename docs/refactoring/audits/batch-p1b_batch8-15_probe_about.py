# -*- coding: utf-8 -*-
"""Спец-проба E-01: About открывается через меню (QAction.triggered), диалог
создаётся без исключений; снимаем заголовок/версию/лейблы.

Запуск: python batch8-15_probe_about.py <tree-root> <iso-dir> <tag>
QDialog.exec нейтрализован: захват диалога + QDialog.DialogCode.Rejected.
"""
import faulthandler, os, pathlib, sys, time

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
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam: data root -> <iso>/Supervertaler
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

app = QApplication(sys.argv)

captured = []
_real_exec = QDialog.exec

def _capture_exec(self, *a, **k):
    labels = []
    for lab in self.findChildren(type(self)) :  # placeholder, replaced below
        pass
    from PyQt6.QtWidgets import QLabel
    texts = [l.text() for l in self.findChildren(QLabel)]
    captured.append({
        "class": type(self).__name__,
        "title": self.windowTitle(),
        "labels": texts,
    })
    return _real_exec.__wrapped__ if hasattr(_real_exec, "__wrapped__") else QDialog.DialogCode.Rejected

QDialog.exec = lambda self, *a, **k: _capture_exec(self, *a, **k)

from PyQt6.QtWidgets import QMainWindow  # noqa: E402
win = Supervertaler.SupervertalerQt()
print(f"[{tag}] window built", flush=True)

# найти About-экшен в меню Help
from PyQt6.QtGui import QAction  # noqa: E402
about_actions = [a for a in win.findChildren(QAction) if a.text() and "about" in a.text().lower()]
print(f"[{tag}] about actions: {[a.text() for a in about_actions]}", flush=True)

ok = False
for a in about_actions:
    before_len = len(captured)
    try:
        a.trigger()  # полный сигнальный путь: triggered -> self.show_about
        QTimer.singleShot(0, lambda: None)
        app.processEvents()
        if len(captured) > before_len:
            ok = True
            print(f"[{tag}] ABOUT-DIALOG {captured[-1]}", flush=True)
            break
    except SystemExit:
        raise
    except BaseException as e:
        print(f"[{tag}] EXC on {a.text()}: {type(e).__name__}: {e}", flush=True)

print(f"[{tag}] RESULT {'OK' if ok else 'FAIL'}", flush=True)
win.close()
app.processEvents()
os._exit(0 if ok else 1)
