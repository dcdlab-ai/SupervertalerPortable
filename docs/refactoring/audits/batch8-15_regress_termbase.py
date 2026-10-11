# -*- coding: utf-8 -*-
"""Termbase-регрессия Batch #8.12 (Этап 3 п.9, закрывает U-2).

Программно: создать термбазу, добавить/изменить/удалить термин, импорт/экспорт,
открыть вкладку Termbases и right-panel. Сравнивает до/после по JSON-снапшоту
(состояние БД термбаз + терминов + результаты операций + классы виджетов).

Запуск: python regress_termbase.py <tree-root> <stage-dir> <tag>
Профиль изолируется (USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP -> stage/iso).
"""
import faulthandler
import json
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

import PyQt6.QtGui as QtGui
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog

calls = []
QtGui.QDesktopServices.openUrl = staticmethod(lambda url: calls.append(f"openUrl {url.toString()}"))


def _logging_exec(self, *a, **k):
    calls.append(f"QDialog.exec {type(self).__name__} '{self.windowTitle()}'")
    return QDialog.DialogCode.Rejected


QDialog.exec = _logging_exec
QDialog.exec_ = _logging_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
import modules.file_dialog_helper as fdh  # noqa: E402
fdh.get_save_file_name = lambda *a, **k: ("", "")
fdh.get_open_file_name = lambda *a, **k: ("", "")

import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

import Supervertaler as SV  # noqa: E402

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
print(f"[{tag}] window built ({time.time()-t0:.1f}s)", flush=True)
for _ in range(120):
    app.processEvents()
    time.sleep(0.05)

snap = {}
mgr = win.termbase_mgr

# --- 1. создать термбазу ---
try:
    tb_id = mgr.create_termbase("probe_tb812", "en", "ru")
    snap["create_termbase"] = f"id={tb_id}" if tb_id is not None else "None"
except Exception as e:
    snap["create_termbase"] = f"EXC {type(e).__name__}: {e}"
    tb_id = None

# --- 2. добавить термин ---
if tb_id:
    try:
        r = mgr.add_term(tb_id, "house", "дом", domain="general", notes="probe")
        snap["add_term"] = f"ok={bool(r)}"
    except Exception as e:
        snap["add_term"] = f"EXC {type(e).__name__}: {e}"

    # --- 3. изменить термин ---
    try:
        terms = mgr.get_terms(tb_id)
        tid = terms[0]["id"] if terms else None
        snap["terms_after_add"] = len(terms)
        if tid is not None:
            r = mgr.update_term(tid, source_term="house", target_term="домик",
                                domain="general", notes="probe2")
            snap["update_term"] = f"ok={bool(r)}"
            terms2 = mgr.get_terms(tb_id)
            snap["target_after_update"] = terms2[0]["target_term"] if terms2 else "?"
    except Exception as e:
        snap["update_term"] = f"EXC {type(e).__name__}: {e}"

    # --- 4. экспорт/импорт TSV термбазы (термин ещё в базе) ---
    try:
        from modules.termbase_import_export import TermbaseExporter, TermbaseImporter  # noqa: E402
        out = stage / f"tb_export_{tag}.tsv"
        exp = TermbaseExporter(win.db_manager, mgr)
        ok, msg = exp.export_tsv(tb_id, str(out))
        snap["export_tsv"] = f"ok={ok} msg={msg} exists={out.exists()}"
        if out.exists():
            import hashlib
            snap["export_tsv_sha"] = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
            imp = TermbaseImporter(win.db_manager, mgr)
            r2 = imp.import_tsv(str(out), tb_id)
            snap["import_tsv"] = f"ok={bool(r2[0]) if isinstance(r2, tuple) else bool(r2)}"
            snap["terms_after_import"] = len(mgr.get_terms(tb_id))
    except Exception as e:
        snap["export_tsv"] = f"EXC {type(e).__name__}: {e}"

    # --- 5. удалить термин ---
    try:
        terms = mgr.get_terms(tb_id)
        tid = terms[0]["id"] if terms else None
        if tid is not None:
            r = mgr.delete_term(tid)
            snap["delete_term"] = f"ok={bool(r)}"
        snap["terms_after_delete"] = len(mgr.get_terms(tb_id))
    except Exception as e:
        snap["delete_term"] = f"EXC {type(e).__name__}: {e}"

# --- 6. вкладка Termbases + right-panel ---
try:
    tab = win.create_termbases_tab()
    snap["termbases_tab"] = type(tab).__name__
    app.processEvents()
    from PyQt6.QtWidgets import QTableWidget  # noqa: E402
    tables = tab.findChildren(QTableWidget)
    snap["termbases_tables"] = len(tables)
    cols = []
    for t in tables:
        cols.append([t.horizontalHeaderItem(i).text() if t.horizontalHeaderItem(i) else "?"
                     for i in range(t.columnCount())])
    snap["termbases_columns"] = cols
    # right-panel: список терминов выбранной термбазы
    rp = getattr(win, "termbase_right_panel", None)
    snap["right_panel"] = type(rp).__name__ if rp is not None else "None"
except Exception as e:
    snap["termbases_tab"] = f"EXC {type(e).__name__}: {e}"

# --- 7. список термбаз ---
try:
    tbs = mgr.get_all_termbases()
    snap["termbases_list"] = [(t.get("name"), t.get("source_lang"), t.get("target_lang"))
                              for t in tbs]
except Exception as e:
    snap["termbases_list"] = f"EXC {type(e).__name__}: {e}"

print(f"[{tag}] SNAP {json.dumps(snap, ensure_ascii=False, sort_keys=True)}", flush=True)
print(f"[{tag}] MODAL-ATTEMPTS {calls}", flush=True)
print(f"[{tag}] REGRESS-TB OK ({time.time()-t0:.1f}s)", flush=True)
os._exit(0)
