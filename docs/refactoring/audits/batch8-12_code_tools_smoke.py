# -*- coding: utf-8 -*-
"""Tools-smoke Batch #8.12 (Этап 0 п.9 / Этап 3 п.8).

Прямой программный вызов обработчика КАЖДОГО пункта меню Project/Tools/Help
(таблица имён построена из create_menus: Project 7891-8110, Tools 8495-8573,
Help 8575-8641) с нейтрализованными модалками. Для каждого пункта:
«исключение/нет» + классы новых top-level виджетов + побочные вызовы.
Exit пропускается.

Прямые вызовы вместо action.trigger(): PyQt6 при исключении в слоте,
достигнутом через сигнал, вызывает qFatal и прерывает процесс (PDF Rescue
без fitz) — прямой Python-вызов обработчика ловится try/except.

Запуск: python tools_smoke.py <tree-root> <stage-dir> <tag>
Профиль изолируется (USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP -> stage/iso).
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
                             QInputDialog, QColorDialog)

# --- нейтрализация: логируем, не открываем ---
calls = []
webbrowser.open = lambda url, *a, **k: (calls.append(f"webbrowser.open {url}"), True)[1]
QtGui.QDesktopServices.openUrl = staticmethod(
    lambda url: calls.append(f"openUrl {url.toString()}"))


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
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
import modules.file_dialog_helper as fdh  # noqa: E402
fdh.get_save_file_name = lambda *a, **k: ("", "")
fdh.get_open_file_name = lambda *a, **k: ("", "")
fdh.get_existing_directory = lambda *a, **k: ""

import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

import Supervertaler as SV  # noqa: E402
from modules.help_system import open_help, Topics as HelpTopics  # noqa: E402

app = QApplication(sys.argv)
print(f"[{tag}] QApplication ok ({time.time()-t0:.1f}s)", flush=True)

try:
    win = SV.SupervertalerQt()
    print(f"[{tag}] window built ({time.time()-t0:.1f}s)", flush=True)
except Exception as e:
    import traceback
    print(f"[{tag}] CONSTRUCT FAILED: {e!r}", flush=True)
    traceback.print_exc()
    os._exit(2)

for _ in range(120):
    app.processEvents()
    time.sleep(0.05)
print(f"[{tag}] event loop pumped 6s", flush=True)

# --- таблица: путь меню -> обработчик (имена из create_menus) ---
ITEMS = [
    # Project (&Project, 7891-8110)
    ("Project/New Project", lambda: win.new_project()),
    ("Project/Open Project", lambda: win.open_project()),
    ("Project/Save", lambda: win.save_project()),
    ("Project/Save As", lambda: win.save_project_as()),
    ("Project/Close Project", lambda: win.close_project()),
    ("Project/Import/Document", lambda: win.import_document()),
    ("Project/Import/Text-Markdown", lambda: win.import_simple_txt()),
    ("Project/Import/Folder", lambda: win.import_folder_multifile()),
    ("Project/Import/GNU-gettext", lambda: win.import_po_file()),
    ("Project/Import/Reimport/Bilingual-Table", lambda: win.import_review_table()),
    ("Project/Import/Reimport/Bilingual-Text", lambda: win.import_bilingual_markdown()),
    ("Project/Import/Help-Formats", lambda: open_help(HelpTopics.IMPORT_FORMATS)),
    ("Project/Export/Translated-Document", lambda: win.export_document()),
    ("Project/Export/Simple-Text", lambda: win.export_simple_txt()),
    ("Project/Export/GNU-gettext", lambda: win.export_po_file()),
    ("Project/Export/Folder", lambda: win.export_folder_multifile()),
    ("Project/Export/Relocate-Source", lambda: win.relocate_source_folder()),
    ("Project/Export/Reimport/Bilingual-Table", lambda: win.export_review_table_with_tags()),
    ("Project/Export/Reimport/Bilingual-Text", lambda: win.export_bilingual_markdown()),
    ("Project/Export/TMX-from-Grid", lambda: win.export_tmx_from_grid()),
    ("Project/Export/TMX-from-Selected", lambda: win.export_tmx_from_selected()),
    ("Project/Export/TMX-from-TM", lambda: win.export_tmx_from_tm_database()),
    ("Project/Export/Help-Formats", lambda: open_help(HelpTopics.IMPORT_FORMATS)),
    ("Project/Project-Info", lambda: win.show_project_info_dialog()),
    # Tools (8495-8573)
    ("Tools/PDF-Rescue", lambda: win.open_pdf_rescue_window()),
    ("Tools/Superlookup", lambda: win.show_concordance_search()),
    ("Tools/TMX-Editor", lambda: win.open_tmx_editor_window()),
    ("Tools/Statistics", lambda: win.show_statistics_dialog()),
    ("Tools/Quick-Count", lambda: win.show_quick_statistics_dialog()),
    ("Tools/Image-Extractor", lambda: win.show_image_extractor_from_tools()),
    ("Tools/Scratchpad", lambda: win.show_scratchpad()),
    ("Tools/Log-Window", lambda: win.detach_log_window()),
    ("Tools/Token-Usage-Costs", lambda: _open_usage_report(win)),
    ("Tools/Settings", lambda: win._go_to_settings_tab()),
    # Help (8575-8641)
    ("Help/Workbench-Help", lambda: win._open_url("https://docs.supervertaler.com/workbench/")),
    ("Help/Keyboard-Shortcuts", lambda: open_help(HelpTopics.KEYBOARD_SHORTCUTS)),
    ("Help/Changelog", lambda: win._open_url("https://github.com/Supervertaler/Supervertaler-Workbench/blob/main/CHANGELOG.md")),
    ("Help/Check-for-Updates", lambda: win.check_for_updates()),
    ("Help/Copy-Version-Info", lambda: win.copy_version_info_to_clipboard()),
    ("Help/Open-Diagnostic-Log", lambda: win.open_diagnostic_log()),
    ("Help/Open-Log-Folder", lambda: win.open_diagnostic_log_folder()),
    ("Help/Community-Discussions", lambda: win._open_url("https://github.com/orgs/Supervertaler/discussions")),
    ("Help/GitHub-Repository", lambda: win._open_url("https://github.com/Supervertaler/Supervertaler-Workbench")),
    ("Help/About", lambda: win.show_about()),
]


def _open_usage_report(win):
    from modules.usage_report_dialog import UsageReportDialog
    budget = float(getattr(win, "monthly_budget_usd", 0.0) or 0.0)
    UsageReportDialog(win, budget=budget).exec()


print(f"[{tag}] menu items: {len(ITEMS)}", flush=True)
for path, fn in ITEMS:
    calls.clear()
    before = {id(w) for w in app.topLevelWidgets()}
    exc = "no-exception"
    try:
        fn()
    except Exception as e:
        exc = f"EXC {type(e).__name__}: {e}"
    app.processEvents()
    new = sorted({type(w).__name__ for w in app.topLevelWidgets() if id(w) not in before})
    print(f"[{tag}] ITEM {path}: {exc} | new-widgets={new} | side-effects={calls}", flush=True)

print(f"[{tag}] SMOKE OK ({time.time()-t0:.1f}s)", flush=True)
os._exit(0)
