r"""
BATCH TM1 recon test (commit 1) — «до»-воспроизведение бага
«Delete selected» в TM-браузере (modules/tm_manager_qt.py, TMManagerDialog.delete_selected_entry).

Баг от Дмитрия (2026-11-12): вкладка TMs -> Browse All, выделение нескольких
записей (Shift+клик по диапазону), «Delete Selected» удаляет только ПОСЛЕДНЮЮ
выбранную запись (currentRow), следующий клик — предпоследнюю и т.д.

Ожидаемое (после исправления): все выделенные записи удаляются за один клик.

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen SUPERVERTALER_DATA_ROOT=<изолированный профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm1_recon_delete_selected_before.py

Тест не трогает реальные TM-базы: БД создаётся в изолированном каталоге.
На «до»-коде тест ФИКСИРУЕТ баг (удалена 1 запись из 5 выделенных);
после исправления тот же тест должен показать удаление всех 5.
"""

import os
import sys
import sqlite3

# --- изолированная среда (до импортов PyQt) ---------------------------------
STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))  # docs/refactoring/audits
PROFILE = os.environ.get("TM1_PROFILE_DIR")
if not PROFILE:
    # по умолчанию — каталог рядом со снютом; при штатном запуске задаётся извне
    PROFILE = os.path.join(os.environ.get("TM1_STAGE_DIR", STAGE_ROOT), "tm1-before-profile")

os.makedirs(PROFILE, exist_ok=True)
os.makedirs(os.path.join(PROFILE, "home"), exist_ok=True)
os.makedirs(os.path.join(PROFILE, "temp"), exist_ok=True)
os.environ["SUPERVERTALER_DATA_ROOT"] = PROFILE
os.environ["USERPROFILE"] = os.path.join(PROFILE, "home")
os.environ["HOME"] = os.environ["USERPROFILE"]
os.environ["APPDATA"] = os.environ["USERPROFILE"]
os.environ["LOCALAPPDATA"] = os.environ["USERPROFILE"]
os.environ["TEMP"] = os.path.join(PROFILE, "temp")
os.environ["TMP"] = os.environ["TEMP"]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO)

import faulthandler

faulthandler.dump_traceback_later(60, repeat=True)

from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
    QTableWidgetSelectionRange,
)

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog

DB_PATH = os.path.join(PROFILE, "tm1_before.db")

# --- стадии -----------------------------------------------------------------


def build_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db = DatabaseManager(db_path=DB_PATH, log_callback=lambda *a, **k: None)
    db.connect()
    # TM-строка (phantom-guard add_translation_unit требует её наличия)
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM1 recon TM', 'tm1recon', 'en', 'nl')"
    )
    db.connection.commit()
    # 10 записей штатным путём (add_translation_unit сам считает хэши)
    for i in range(1, 11):
        db.add_translation_unit(
            source=f"source {i:02d}",
            target=f"target {i:02d}",
            source_lang="en",
            target_lang="nl",
            tm_id="tm1recon",
        )
    db.connection.commit()
    return db


def db_ids(db):
    db.cursor.execute("SELECT id FROM translation_units ORDER BY id")
    return [r["id"] for r in db.cursor.fetchall()]


def monkeypatch_boxes():
    """QDialog-модалки никогда не закрываются offscreen — подменяем."""
    QMessageBox.question = staticmethod(
        lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)


def main():
    db = build_db()
    ids_before = db_ids(db)
    app = QApplication.instance() or QApplication(sys.argv)
    monkeypatch_boxes()

    dlg = TMManagerDialog(
        None, db, log_callback=lambda msg: print(f"[dlg-log] {msg}")
    )
    table = dlg.browser_table

    # выделение 5 подряд (имитация Shift+клик по диапазону): строки 0..4.
    # В реальном UI Shift+клик ставит текущую строку на кликнутую (якорную),
    # затем расширяет диапазон — воспроизводим именно так.
    table.clearSelection()
    table.setCurrentCell(4, 0)
    table.setRangeSelected(QTableWidgetSelectionRange(0, 0, 4, table.columnCount() - 1), True)

    selected_ids = []
    for it in table.selectedItems():
        if it.column() == 0:
            selected_ids.append(int(it.text()))
    selected_ids = sorted(set(selected_ids))
    current_row = table.currentRow()
    current_id = int(table.item(current_row, 0).text()) if current_row >= 0 else None

    print(f"rows in db before: {len(ids_before)} (ids {ids_before})")
    print(f"table rows: {table.rowCount()}")
    print(f"selected ids (shift-range rows 0..4): {selected_ids}")
    print(f"currentRow -> id {current_id}")

    dlg.delete_selected_entry()

    ids_after = db_ids(db)
    deleted = sorted(set(ids_before) - set(ids_after))
    remaining_in_table = [
        int(table.item(r, 0).text())
        for r in range(table.rowCount())
        if table.item(r, 0)
    ]
    print(f"ids after delete: {ids_after}")
    print(f"deleted ids: {deleted}")
    print(f"table rows after: {table.rowCount()} (ids {remaining_in_table})")

    ok = len(deleted) == 5 and deleted == selected_ids and table.rowCount() == 5
    print()
    if ok:
        print("RESULT: OK — удалены все 5 выделенных записи за один клик")
    else:
        print(
            f"RESULT: BUG REPRODUCED — выделено 5, удалено {len(deleted)} "
            f"(id {deleted}); expected 5 ({selected_ids})"
        )
    dlg.close()
    db.close() if hasattr(db, "close") else None
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
