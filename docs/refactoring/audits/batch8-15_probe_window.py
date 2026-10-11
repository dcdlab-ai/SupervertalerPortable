# -*- coding: utf-8 -*-
"""Offscreen-пробник Batch #8.11: чипы Chat + счётчики фоновых объектов.

Запуск: python probe_window_811.py <isodir> <tag> <scenario: clean|upgrade> [datadir]
Профиль изолируется перенаправлением USERPROFILE/APPDATA/HOME/TEMP в <isodir>.

Фиксирует: окно строится; main_tabs 6; Settings 14; список чипов Chat
(ключ, подпись, видимость, checked) в порядке раскладки для каждого ChatViewWidget;
число QTimer/QThread/QThreadPool-объектов Chat и Prompt Manager; дерево данных
S-clean; hash-diff S-upgrade.
"""
import faulthandler
import hashlib
import os
import pathlib
import sys
import time

iso = pathlib.Path(sys.argv[1]).resolve()
tag = sys.argv[2]
scenario = sys.argv[3] if len(sys.argv) > 3 else "clean"
data_dir = pathlib.Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else iso / "Supervertaler"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)

sys.path.insert(0, os.getcwd())
t0 = time.time()


def snapshot_dir(root: pathlib.Path):
    out = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            except OSError:
                h = "<unreadable>"
            out[str(p.relative_to(root)).replace("\\", "/")] = h
    return out


before = snapshot_dir(data_dir) if data_dir.exists() else {}
print(f"[{tag}] scenario={scenario} data_dir={data_dir} pre-start snapshot: {len(before)} files", flush=True)

import Supervertaler  # noqa: E402
for k in sorted(before):
    print(f"[{tag}] PRE-FILE {k} {before[k]}", flush=True)

from PyQt6.QtCore import QTimer, QThread, QThreadPool  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

app = QApplication(sys.argv)
print(f"[{tag}] QApplication ok ({time.time()-t0:.1f}s)", flush=True)

import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

_real_exec = QDialog.exec


def _logging_exec(self, *a, **k):
    print(f"[{tag}] MODAL-ATTEMPT QDialog.exec: {type(self).__name__} "
          f"title={self.windowTitle()!r}", flush=True)
    return QDialog.DialogCode.Rejected


QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
print(f"[{tag}] modal dialogs neutralized (logging)", flush=True)

try:
    window = Supervertaler.SupervertalerQt()
    print(f"[{tag}] SupervertalerQt constructed ({time.time()-t0:.1f}s)", flush=True)
except Exception as e:
    import traceback
    print(f"[{tag}] CONSTRUCT FAILED: {e!r}", flush=True)
    traceback.print_exc()
    os._exit(2)

try:
    udp = pathlib.Path(Supervertaler.get_user_data_path())
    print(f"[{tag}] user_data_path: {udp}", flush=True)
except Exception as e:
    udp = None
    print(f"[{tag}] get_user_data_path FAILED: {e!r}", flush=True)

try:
    window._warm_up_top_tabs()
    print(f"[{tag}] _warm_up_top_tabs() ok", flush=True)
except Exception as e:
    print(f"[{tag}] _warm_up_top_tabs() FAILED: {e!r}", flush=True)

main_tabs = getattr(window, "main_tabs", None)
labels = [main_tabs.tabText(i) for i in range(main_tabs.count())] if main_tabs else []
print(f"[{tag}] main_tabs ({len(labels)}): {labels}", flush=True)

st = getattr(window, "settings_tabs", None)
if st is not None:
    st_labels = [st.tabText(i) for i in range(st.count())]
    print(f"[{tag}] settings pages ({len(st_labels)}): {st_labels}", flush=True)
else:
    print(f"[{tag}] settings_tabs attr absent", flush=True)

# --- Чипы Chat: все ChatViewWidget, порядок раскладки ---
from modules.chat_view_widget import ChatViewWidget  # noqa: E402

views = window.findChildren(ChatViewWidget)
print(f"[{tag}] ChatViewWidget instances: {len(views)}", flush=True)
for vi, view in enumerate(views):
    row = view._context_chips_row
    chips = []
    for i in range(row.count()):
        item = row.itemAt(i)
        w = item.widget()
        if w is None:
            chips.append(("stretch", "", None, None))
        elif isinstance(w, __import__("PyQt6.QtWidgets", fromlist=["QPushButton"]).QPushButton):
            key = next((k for k, b in view._context_toggles.items() if b is w), "?")
            chips.append((key, w.text(), w.isVisible(), w.isChecked()))
        else:
            chips.append(("label", w.text(), w.isVisible(), None))
    print(f"[{tag}] CHIPS view#{vi} ({type(view).__name__}): {chips}", flush=True)
    print(f"[{tag}] CHIPSTATE view#{vi}: {view.get_context_state()}", flush=True)

# --- Счётчики фоновых объектов ---
def counters(obj, name):
    if not hasattr(obj, "findChildren"):
        print(f"[{tag}] COUNTERS {name}: (not a QObject)", flush=True)
        return
    qt = len(obj.findChildren(QTimer))
    qth = len(obj.findChildren(QThread))
    print(f"[{tag}] COUNTERS {name}: QTimer={qt} QThread={qth}", flush=True)

for vi, view in enumerate(views):
    counters(view, f"chatview#{vi}")
pm = getattr(window, "prompt_manager_qt", None)
if pm is not None:
    counters(pm, "prompt_manager_qt")
    counters(pm.chat_backend, "pm.chat_backend")
    for attr in ("_ai_tab_chat_view", "_grid_chat_view"):
        v = getattr(pm, attr, None)
        if v is not None:
            counters(v, f"pm.{attr}")
else:
    print(f"[{tag}] prompt_manager_qt absent", flush=True)

# Singleton poller/client (после 8.11 модуля нет)
try:
    import modules.trados_bridge_client as _tbc  # noqa: E402
    _pol = _tbc.TradosBridgePoller._shared_instance
    _cli = _tbc.TradosBridgeClient._shared_instance
    print(f"[{tag}] POLLER singleton: {'present' if _pol is not None else 'None'}"
          f"{'' if _pol is None else ' QTimer=' + str(len(_pol.findChildren(QTimer))) + ' avail=' + str(_pol.current_state())}", flush=True)
    print(f"[{tag}] CLIENT singleton: {'present' if _cli is not None else 'None'}", flush=True)
except ModuleNotFoundError:
    print(f"[{tag}] POLLER/CLIENT: module modules.trados_bridge_client absent", flush=True)

pool = QThreadPool.globalInstance()
print(f"[{tag}] QThreadPool.globalInstance: active={pool.activeThreadCount()} max={pool.maxThreadCount()}", flush=True)
app_threads = len(app.findChildren(QThread))
print(f"[{tag}] QApplication.findChildren(QThread): {app_threads}", flush=True)

# --- Закрытие и дерево данных ---
try:
    window.close()
    app.processEvents()
    print(f"[{tag}] window.close() ok", flush=True)
except Exception as e:
    print(f"[{tag}] window.close() FAILED: {e!r}", flush=True)

if udp is not None and udp.exists():
    tree = sorted(str(p.relative_to(udp)).replace("\\", "/") for p in udp.rglob("*"))
    print(f"[{tag}] DATA-TREE ({len(tree)} entries under {udp}):", flush=True)
    for t in tree:
        print(f"[{tag}] TREE {t}", flush=True)
if scenario == "upgrade" and data_dir.exists():
    after = snapshot_dir(data_dir)
    transient = lambda k: k.endswith((".db-shm", ".db-wal"))
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in (set(after) & set(before)) if after[k] != before[k])
    changed_core = [k for k in changed if not transient(k)]
    changed_transient = [k for k in changed if transient(k)]
    print(f"[{tag}] HASH-DIFF (of {data_dir}) added={added} removed={removed} "
          f"changed={changed_core} transient={changed_transient}", flush=True)

print(f"[{tag}] PROBE OK ({time.time()-t0:.1f}s)", flush=True)
QTimer.singleShot(0, app.quit)
app.exec()
os._exit(0)
