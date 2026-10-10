# -*- coding: utf-8 -*-
"""Регрессия общих путей Batch #8.9 (Этап 3 п.6).

Один и тот же скрипт запускается в worktree HEAD («before») и в рабочей копии
(«after») с одинаковыми входными файлами; печатает число сегментов и sha256
выходных файлов (TMX — с нормализацией creationdate; DOCX — по содержимому zip).

Запуск: python regress_common.py <tree-root> <stage-dir> <tag>
  stage-dir содержит: inputs/ (test.txt, test.md, test.docx) и iso/ (профиль).
"""
import faulthandler
import hashlib
import os
import pathlib
import re
import sys
import zipfile

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]
iso = stage / "iso"
inputs = stage / "inputs"
outdir = stage / f"out-{tag}"
outdir.mkdir(parents=True, exist_ok=True)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
(iso / "Desktop").mkdir(exist_ok=True)
(iso / "Documents").mkdir(exist_ok=True)
(iso / "Downloads").mkdir(exist_ok=True)
cfg_dir = iso / "AppData" / "Roaming" / "Supervertaler"
cfg_dir.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg_dir / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8"
)

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import PyQt6.QtWidgets as QW  # noqa: E402
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog  # noqa: E402

# --- нейтрализация модалок: авто-accept с логом ---
modal_log = []
_real_exec = QDialog.exec


def _logging_exec(self, *a, **k):
    modal_log.append(f"QDialog.exec {type(self).__name__} '{self.windowTitle()}'")
    return QDialog.DialogCode.Accepted


QDialog.exec = _logging_exec
QDialog.exec_ = _logging_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

# --- файловые диалоги: очередь путей ---
open_queue = []
save_queue = []


def fake_open(*a, **k):
    return (open_queue.pop(0) if open_queue else "", "")


def fake_save(*a, **k):
    return (save_queue.pop(0) if save_queue else "", "")


QFileDialog.getOpenFileName = staticmethod(fake_open)
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(open_queue), "") if open_queue else ([], ""))
QFileDialog.getSaveFileName = staticmethod(fake_save)
import modules.file_dialog_helper as fdh  # noqa: E402

fdh.get_save_file_name = lambda *a, **k: (save_queue.pop(0) if save_queue else "", "")
fdh.get_open_file_name = lambda *a, **k: (open_queue.pop(0) if open_queue else "", "")

import Supervertaler as SV  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
print(f"[{tag}] window built", flush=True)

# Прокачка event loop: отложенный QTimer(1500ms) создаёт okapi_sidecar только
# при работающем event loop (в before-прогоне его крутил вложенный цикл диалога
# скачивания сайдкара).
import time as _time
for _ in range(120):
    app.processEvents()
    _time.sleep(0.05)
print(f"[{tag}] event loop pumped 6s; okapi_sidecar={win.okapi_sidecar is not None}", flush=True)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def sha_docx(p):
    """Хэш DOCX по содержимому zip (имя+байты записей, отсортировано) — без zip-таймстемпов."""
    with zipfile.ZipFile(p) as z:
        h = hashlib.sha256()
        for name in sorted(z.namelist()):
            h.update(name.encode())
            h.update(z.read(name))
        return h.hexdigest()[:16]


def sha_tmx(p):
    data = pathlib.Path(p).read_bytes()
    data = re.sub(rb"creationdate=\"[^\"]*\"", b"creationdate=\"NORMALIZED\"", data)
    return hashlib.sha256(data).hexdigest()[:16]


def fill_targets(win, prefix):
    for i, seg in enumerate(win.current_project.segments):
        seg.target = f"{prefix}{i+1}: {seg.source}"


results = {}

# --- 1. импорт TXT ---
open_queue.append(str(inputs / "test.txt"))
win.import_simple_txt()
n_txt = len(win.current_project.segments) if win.current_project else 0
results["import_txt_segments"] = n_txt
fill_targets(win, "T")
save_queue.append(str(outdir / "out_simple.txt"))
win.export_simple_txt()
results["export_simple_txt"] = sha(outdir / "out_simple.txt") if (outdir / "out_simple.txt").exists() else "MISSING"

# --- 2. импорт MD ---
open_queue.append(str(inputs / "test.md"))
win.import_simple_txt()
results["import_md_segments"] = len(win.current_project.segments) if win.current_project else 0

# --- 3. импорт DOCX + экспорт translated docx ---
open_queue.append(str(inputs / "test.docx"))
win.import_docx_from_path(str(inputs / "test.docx"))
results["import_docx_segments"] = len(win.current_project.segments) if win.current_project else 0
fill_targets(win, "D")
save_queue.append(str(outdir / "out_translated.docx"))
win.export_target_only_docx()
results["export_docx"] = sha_docx(outdir / "out_translated.docx") if (outdir / "out_translated.docx").exists() else "MISSING"

# --- 4. экспорт TMX из грида ---
save_queue.append(str(outdir / "out_grid.tmx"))
win.export_tmx_from_grid()
results["export_tmx"] = sha_tmx(outdir / "out_grid.tmx") if (outdir / "out_grid.tmx").exists() else "MISSING"

print(f"[{tag}] RESULTS {results}", flush=True)
print(f"[{tag}] MODAL-ATTEMPTS {len(modal_log)}: {modal_log}", flush=True)
os._exit(0)
