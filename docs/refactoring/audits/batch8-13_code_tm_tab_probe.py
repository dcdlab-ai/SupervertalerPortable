# -*- coding: utf-8 -*-
"""Спец-baseline/регрессия TM-вкладки Batch #8.13 (Этап 0 п.4 / Этап 3 п.7).

Программно, offscreen, изолированный профиль. Колонки определяются динамически
по классу виджета (Read=CheckmarkCheckBox col3, Write=BlueCheckmarkCheckBox
col4, SuperLookup=TealCheckmarkCheckBox — col6 «до», col5 «после»), поэтому
лог флагов Read/Write/SuperLookup идентичен в «до» и «после». Bridge-колонка
(«до») не переключается: её флаги логируются как есть.

Фиксирует:
  1) число колонок, заголовки, ширины, класс виджета в каждой ячейке строки 0,
     начальные состояния чекбоксов;
  2) создать 2 TM -> переключить Read/Write/SuperLookup каждой кликом ->
     флаги из БД/метаданных -> переименовать -> удалить;
  3) Select All / Unselect All Read/Write/SuperLookup: состояния строк + флаги;
  4) сортировка по Entries; refresh; бридж-флаг в БД до/после (код приложения
     менять не должен).

Запуск: python tm_tab_probe.py <tree-root> <stage-dir> <tag>
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

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QTableWidget, QCheckBox  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

def _logging_exec(self, *a, **k):
    print(f"[{tag}] MODAL-ATTEMPT QDialog.exec: {type(self).__name__} title={self.windowTitle()!r}", flush=True)
    return QDialog.DialogCode.Rejected
QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)

import Supervertaler  # noqa: E402
from modules.styled_widgets import CheckmarkCheckBox, BlueCheckmarkCheckBox, TealCheckmarkCheckBox  # noqa: E402

app = QApplication(sys.argv)
window = Supervertaler.SupervertalerQt()
print(f"[{tag}] window constructed ({time.time()-t0:.1f}s)", flush=True)

mgr = window.tm_metadata_mgr
tm_table = None
for t in window.findChildren(QTableWidget):
    hdrs = [t.horizontalHeaderItem(i).text() if t.horizontalHeaderItem(i) else None
            for i in range(t.columnCount())]
    if hdrs and "TM Name" in hdrs:
        tm_table = t
        break
if tm_table is None:
    print(f"[{tag}] TM TABLE NOT FOUND", flush=True)
    os._exit(2)

def table_state():
    st = {"columns": tm_table.columnCount(),
          "headers": [tm_table.horizontalHeaderItem(i).text() if tm_table.horizontalHeaderItem(i) else None
                      for i in range(tm_table.columnCount())],
          "widths": [tm_table.columnWidth(i) for i in range(tm_table.columnCount())],
          "rows": tm_table.rowCount(),
          "cells": []}
    for row in range(tm_table.rowCount()):
        rowdesc = []
        for col in range(tm_table.columnCount()):
            w = tm_table.cellWidget(row, col)
            it = tm_table.item(row, col)
            if w is not None:
                rowdesc.append(f"col{col}:{type(w).__name__}:checked={w.isChecked()}")
            elif it is not None:
                rowdesc.append(f"col{col}:item:{it.text()}")
            else:
                rowdesc.append(f"col{col}:empty")
        st["cells"].append(rowdesc)
    return st

def col_of(row, cls):
    # Exact type match: Read and Bridge are both plain CheckmarkCheckBox,
    # so isinstance would be ambiguous. Read is the first plain column.
    for col in range(tm_table.columnCount()):
        w = tm_table.cellWidget(row, col)
        if type(w) is cls:
            return col
    return None

def flags_for(name):
    tm = next((t for t in mgr.get_all_tms() if t["name"] == name), None)
    if tm is None:
        return None
    return {"id": tm["id"],
            "read": mgr.is_tm_active(tm["id"], 0),
            "read_only": tm.get("read_only"),
            "superlookup": tm.get("superlookup_enabled"),
            "bridged": tm.get("bridged_to_trados")}

def click(w):
    w.click()
    app.processEvents()

def header_checkbox(label):
    # Search only inside the TM tab widget (tm_table's parent): the Termbases
    # tab has identically-labelled "Select All Read/Write" checkboxes.
    tab = tm_table.parentWidget()
    for cb in tab.findChildren(QCheckBox):
        if cb.text() == label:
            return cb
    return None

print(f"[{tag}] INITIAL TABLE: {json.dumps(table_state(), ensure_ascii=False)}", flush=True)

id1 = mgr.create_tm("Probe TM One", "probe_tm_one", "en", "ru", "desc1")
id2 = mgr.create_tm("Probe TM Two", "probe_tm_two", "nl", "ru", "desc2")
window.tm_tab_refresh_callback()
app.processEvents()
print(f"[{tag}] CREATED ids={id1},{id2}", flush=True)
st = table_state()
print(f"[{tag}] AFTER CREATE: {json.dumps(st, ensure_ascii=False)}", flush=True)
print(f"[{tag}] FLAGS after create: one={flags_for('Probe TM One')} two={flags_for('Probe TM Two')}", flush=True)

names = [tm_table.item(r, 0).text() for r in range(tm_table.rowCount())]
r1, r2 = names.index("Probe TM One"), names.index("Probe TM Two")
for r, name in ((r1, "Probe TM One"), (r2, "Probe TM Two")):
    read_col = col_of(r, CheckmarkCheckBox)
    write_col = col_of(r, BlueCheckmarkCheckBox)
    sl_col = col_of(r, TealCheckmarkCheckBox)
    for col, label in ((read_col, "Read"), (write_col, "Write"), (sl_col, "SuperLookup")):
        w = tm_table.cellWidget(r, col)
        before = w.isChecked()
        click(w)
        after = w.isChecked()
        print(f"[{tag}] TOGGLE {name} {label} col{col} ({type(w).__name__}) {before}->{after} flags={flags_for(name)}", flush=True)

for label, cls in (("Select All Read", __import__("modules.styled_widgets", fromlist=["CheckmarkCheckBox"]).CheckmarkCheckBox),
                   ("Select All Write", BlueCheckmarkCheckBox),
                   ("Select All SuperLookup", TealCheckmarkCheckBox)):
    cb = header_checkbox(label)
    if cb is None:
        print(f"[{tag}] HEADER CHECKBOX MISSING: {label}", flush=True)
        continue
    col = col_of(0, cls)
    print(f"[{tag}] HEADER {label}: before-click checked={cb.isChecked()}", flush=True)
    cb.setChecked(not cb.isChecked()); app.processEvents()
    states = [tm_table.cellWidget(r, col).isChecked() for r in range(tm_table.rowCount())]
    print(f"[{tag}] SELECT-ALL {label} col{col}: header-checked={cb.isChecked()} rows-checked={states} flags one={flags_for('Probe TM One')} two={flags_for('Probe TM Two')}", flush=True)
    cb.setChecked(not cb.isChecked()); app.processEvents()
    states = [tm_table.cellWidget(r, col).isChecked() for r in range(tm_table.rowCount())]
    print(f"[{tag}] UNSELECT-ALL {label} col{col}: header-checked={cb.isChecked()} rows-checked={states}", flush=True)

window.tm_tab_refresh_callback(); app.processEvents()
print(f"[{tag}] AFTER REFRESH: {json.dumps(table_state(), ensure_ascii=False)}", flush=True)

tm_table.sortItems(2, Qt.SortOrder.AscendingOrder); app.processEvents()
print(f"[{tag}] SORT col2 asc: names={[tm_table.item(r,0).text() for r in range(tm_table.rowCount())]} indicator={tm_table.horizontalHeader().sortIndicatorSection()}/{tm_table.horizontalHeader().sortIndicatorOrder()}", flush=True)
tm_table.sortItems(2, Qt.SortOrder.DescendingOrder); app.processEvents()
print(f"[{tag}] SORT col2 desc: names={[tm_table.item(r,0).text() for r in range(tm_table.rowCount())]} indicator={tm_table.horizontalHeader().sortIndicatorSection()}/{tm_table.horizontalHeader().sortIndicatorOrder()}", flush=True)

mgr.update_tm(id1, name="Probe TM Renamed")
window.tm_tab_refresh_callback(); app.processEvents()
print(f"[{tag}] AFTER RENAME: names={[tm_table.item(r,0).text() for r in range(tm_table.rowCount())]}", flush=True)
mgr.delete_tm(id2, delete_entries=True)
window.tm_tab_refresh_callback(); app.processEvents()
print(f"[{tag}] AFTER DELETE: names={[tm_table.item(r,0).text() for r in range(tm_table.rowCount())]}", flush=True)

print(f"[{tag}] BRIDGE FLAG final: one={flags_for('Probe TM Renamed')}", flush=True)
print(f"[{tag}] TM PROBE OK ({time.time()-t0:.1f}s)", flush=True)
os._exit(0)
