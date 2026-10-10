# -*- coding: utf-8 -*-
"""Спец-baseline меню/фильтров Batch #8.13 (Этап 0 п.5).

1) Полный список QAction меню File/Project/Tools/Help (текст, вложенность,
   разделители) из QMenuBar построенного окна.
2) Список фильтров ВСЕХ файловых диалогов открытия/импорта/экспорта:
   перехват аргументов QFileDialog.get* и file_dialog_helper.get_* при
   программном вызове обработчиков (таблица пунктов как в tools_smoke 8.12).

Запуск: python menu_probe.py <tree-root> <stage-dir> <tag>
"""
import faulthandler
import os
import pathlib
import sys
import time

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]
iso = stage / "iso"

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
(cfg_dir / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8"
)

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))
t0 = time.time()

import webbrowser
import PyQt6.QtGui as QtGui
from PyQt6.QtWidgets import (QApplication, QDialog, QMessageBox, QFileDialog,
                             QInputDialog, QMenuBar, QTableWidget)

dialog_calls = []

def _log_open(parent, title, directory, filters, *a, **k):
    dialog_calls.append(("getOpenFileName", title, filters))
    return ("", "")
def _log_opens(parent, title, directory, filters, *a, **k):
    dialog_calls.append(("getOpenFileNames", title, filters))
    return ([], "")
def _log_save(parent, title, directory, filters, *a, **k):
    dialog_calls.append(("getSaveFileName", title, filters))
    return ("", "")
def _log_dir(parent, title, directory, *a, **k):
    dialog_calls.append(("getExistingDirectory", title, ""))
    return ""

QFileDialog.getOpenFileName = staticmethod(_log_open)
QFileDialog.getOpenFileNames = staticmethod(_log_opens)
QFileDialog.getSaveFileName = staticmethod(_log_save)
QFileDialog.getExistingDirectory = staticmethod(_log_dir)

import modules.file_dialog_helper as fdh
fdh.get_open_file_name = lambda *a, **k: (dialog_calls.append(("fdh.get_open_file_name", str(a[1] if len(a) > 1 else ""), str(a[2] if len(a) > 2 else ""))), ("", ""))[1]
fdh.get_open_file_names = lambda *a, **k: (dialog_calls.append(("fdh.get_open_file_names", str(a[1] if len(a) > 1 else ""), str(a[2] if len(a) > 2 else ""))), ([], ""))[1]
fdh.get_save_file_name = lambda *a, **k: (dialog_calls.append(("fdh.get_save_file_name", str(a[1] if len(a) > 1 else ""), str(a[2] if len(a) > 2 else ""))), ("", ""))[1]
fdh.get_existing_directory = lambda *a, **k: (dialog_calls.append(("fdh.get_existing_directory", str(a[1] if len(a) > 1 else ""), "")), "")[1]

def _logging_exec(self, *a, **k):
    return QDialog.DialogCode.Rejected
QDialog.exec = _logging_exec
QDialog.exec_ = _logging_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
webbrowser.open = lambda url, *a, **k: True
QtGui.QDesktopServices.openUrl = staticmethod(lambda url: None)
import modules.usage_statistics as _us
_us.show_opt_in_dialog = lambda parent=None: False

import Supervertaler as SV
from modules.help_system import open_help, Topics as HelpTopics

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
for _ in range(120):
    app.processEvents()
    time.sleep(0.05)
print(f"[{tag}] window built ({time.time()-t0:.1f}s)", flush=True)

# --- 1) меню ---
def dump_menu(menu, depth):
    for act in menu.actions():
        if act.isSeparator():
            print(f"[{tag}] MENU {'  '*depth}| separator", flush=True)
        else:
            sub = act.menu()
            print(f"[{tag}] MENU {'  '*depth}{act.text()!r}{' [submenu]' if sub else ''}", flush=True)
            if sub:
                dump_menu(sub, depth + 1)

mb = win.findChildren(QMenuBar)
if not mb:
    print(f"[{tag}] NO MENUBAR", flush=True)
    os._exit(2)
for m in mb[0].actions():
    sub = m.menu()
    if sub:
        print(f"[{tag}] TOP {m.text()!r}", flush=True)
        dump_menu(sub, 1)

# --- 2) фильтры диалогов ---
ITEMS = [
    ("Project/Open Project", lambda: win.open_project()),
    ("Project/Save As", lambda: win.save_project_as()),
    ("Project/Import/Document", lambda: win.import_document()),
    ("Project/Import/Text-Markdown", lambda: win.import_simple_txt()),
    ("Project/Import/Folder", lambda: win.import_folder_multifile()),
    ("Project/Import/GNU-gettext", lambda: win.import_po_file()),
    ("Project/Import/Reimport/Bilingual-Table", lambda: win.import_review_table()),
    ("Project/Import/Reimport/Bilingual-Text", lambda: win.import_bilingual_markdown()),
    ("Project/Export/Translated-Document", lambda: win.export_document()),
    ("Project/Export/Simple-Text", lambda: win.export_simple_txt()),
    ("Project/Export/GNU-gettext", lambda: win.export_po_file()),
    ("Project/Export/Folder", lambda: win.export_folder_multifile()),
    ("Project/Export/Relocate-Source", lambda: win.relocate_source_folder()),
    ("Project/Export/TMX-from-Grid", lambda: win.export_tmx_from_grid()),
    ("Project/Export/TMX-from-Selected", lambda: win.export_tmx_from_selected()),
    ("Project/Export/TMX-from-TM", lambda: win.export_tmx_from_tm_database()),
    ("Tools/Quick-Count", lambda: win.show_quick_statistics_dialog()),
    ("Tools/Statistics", lambda: win.show_statistics_dialog()),
]

tm_table = None
for t in win.findChildren(QTableWidget):
    hdrs = [t.horizontalHeaderItem(i).text() if t.horizontalHeaderItem(i) else None
            for i in range(t.columnCount())]
    if hdrs and "TM Name" in hdrs:
        tm_table = t
        break
ITEMS += [
    ("TM/Import TMX", lambda: win._import_tmx_as_tm(win.tm_metadata_mgr, tm_table, lambda: None)),
    ("TM/Export TM", lambda: win._export_tm_to_tmx(win.tm_metadata_mgr, tm_table)),
]
for name, fn in ITEMS:
    before_n = len(dialog_calls)
    try:
        fn()
        res = "ok"
    except Exception as e:
        res = f"EXC {type(e).__name__}"
    app.processEvents()
    new = dialog_calls[before_n:]
    print(f"[{tag}] ITEM {name}: {res} dialogs={len(new)}", flush=True)
    for kind, title, filt in new:
        print(f"[{tag}]   DIALOG {kind} title={title!r} filter={filt!r}", flush=True)

print(f"[{tag}] MENU PROBE OK ({time.time()-t0:.1f}s)", flush=True)
os._exit(0)
