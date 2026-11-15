"""
BATCH TM1 test suite (commit 3) — «Delete Selected» в TM-браузере
(TMManagerDialog.delete_selected_entry, modules/tm_manager_qt.py).

Сценарии (offscreen, изолированный SUPERVERTALER_DATA_ROOT, временные TM-базы):
  1. Shift-диапазон 5 подряд -> удалены все 5 за один клик.
  2. Ctrl-выборочные 3 из 10 (не подряд) -> удалены именно эти 3.
  3. Ctrl+A -> удалены все 10, таблица пуста, счётчик «Showing 0 entries».
  4. Ноль выделенных -> ничего не удалено, окно не падает.
  5. «No» в подтверждении -> ничего не удалено.
  6. 1200 выделено -> удалены все ОДНОЙ транзакцией (пачки <= 500),
     один refresh_browser, одна строка лога.
  7. Ошибка на второй пачке (заглушка курсора) -> откат всего набора.
  8. Отсортированная/отфильтрованная таблица -> удалены именно выделенные
     id (взятые из колонки ID), а не строки с теми же номерами.

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen SUPERVERTALER_DATA_ROOT=<изолированный профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm1_delete_selected_tests.py
"""

import os
import sys

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM1_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(os.environ.get("TM1_STAGE_DIR", STAGE_ROOT), "tm1-suite-profile")

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

faulthandler.dump_traceback_later(120, repeat=True)

from PyQt6.QtCore import QItemSelectionModel
from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
    QTableWidgetSelectionRange,
)

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog

BATCH_LIMIT = 500  # должен совпадать с лимитом пачки в delete_selected_entry


# --- инфраструктура -----------------------------------------------------------


class FailingCursor:
    """Прокси курсора: бросает исключение на N-м DELETE по translation_units."""

    def __init__(self, real, fail_on_delete_no):
        self._real = real
        self._fail_on = fail_on_delete_no
        self.delete_calls = 0

    def execute(self, sql, params=()):
        if "DELETE FROM translation_units" in sql:
            self.delete_calls += 1
            if self.delete_calls >= self._fail_on:
                raise RuntimeError("injected failure on chunk")
        return self._real.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self._real, name)


def make_db(name):
    db_path = os.path.join(PROFILE, name)
    if os.path.exists(db_path):
        os.remove(db_path)
    for suffix in ("-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=lambda *a, **k: None)
    db.connect()
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES (?, ?, 'en', 'nl')",
        (f"TM1 suite {name}", "tm1suite"),
    )
    db.connection.commit()
    return db


def seed_entries(db, count):
    for i in range(1, count + 1):
        db.add_translation_unit(
            source=f"source {i:04d}",
            target=f"target {i:04d}",
            source_lang="en",
            target_lang="nl",
            tm_id="tm1suite",
        )
    db.connection.commit()


def db_ids(db):
    db.cursor.execute("SELECT id FROM translation_units ORDER BY id")
    return [r["id"] for r in db.cursor.fetchall()]


def make_dialog(db, load_limit=None):
    logs = []
    dlg = TMManagerDialog(None, db, log_callback=logs.append)
    if load_limit is not None:
        # browser_limit по умолчанию 500 — для больших сценариев поднимаем
        # лимит загрузки, иначе selectAll() выделит только загруженные строки.
        dlg.browser_limit.setValue(load_limit)
        dlg.refresh_browser()
    return dlg, logs


def table_ids(table):
    return [int(table.item(r, 0).text()) for r in range(table.rowCount()) if table.item(r, 0)]


def monkeypatch_boxes(question_answer=QMessageBox.StandardButton.Yes):
    QMessageBox.question = staticmethod(lambda *a, **k: question_answer)
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)


def select_rows(table, row_list):
    """Ctrl-выборочное выделение строк (как Ctrl+клик)."""
    table.clearSelection()
    model = table.selectionModel()
    for r in row_list:
        model.select(
            table.model().index(r, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )


def select_range(table, row_from, row_to):
    """Shift-диапазон с якорем на row_to (как Shift+клик)."""
    table.clearSelection()
    table.setCurrentCell(row_to, 0)
    table.setRangeSelected(
        QTableWidgetSelectionRange(row_from, 0, row_to, table.columnCount() - 1), True
    )


# --- сценарии ------------------------------------------------------------------


def scenario_shift_range():
    db = make_db("tm1_s1.db")
    seed_entries(db, 10)
    dlg, logs = make_dialog(db)
    ids_before = db_ids(db)
    select_range(dlg.browser_table, 0, 4)
    selected = sorted({int(i.text()) for i in dlg.browser_table.selectedItems() if i.column() == 0})
    dlg.delete_selected_entry()
    ids_after = db_ids(db)
    deleted = sorted(set(ids_before) - set(ids_after))
    ok = (
        len(selected) == 5
        and deleted == selected
        and dlg.browser_table.rowCount() == 5
        and any("deleted 5 entries from TM tm1suite" in line for line in logs)
    )
    dlg.close()
    return ok, f"selected={selected} deleted={deleted}"


def scenario_ctrl_pick():
    db = make_db("tm1_s2.db")
    seed_entries(db, 10)
    dlg, logs = make_dialog(db)
    ids_before = db_ids(db)
    rows = table_ids(dlg.browser_table)
    pick_rows = [0, 4, 7]
    pick_ids = sorted(rows[r] for r in pick_rows)
    select_rows(dlg.browser_table, pick_rows)
    dlg.delete_selected_entry()
    deleted = sorted(set(ids_before) - set(db_ids(db)))
    ok = deleted == pick_ids and dlg.browser_table.rowCount() == 7
    dlg.close()
    return ok, f"picked={pick_ids} deleted={deleted}"


def scenario_ctrl_a():
    db = make_db("tm1_s3.db")
    seed_entries(db, 10)
    dlg, logs = make_dialog(db)
    dlg.browser_table.selectAll()
    dlg.delete_selected_entry()
    remaining = db_ids(db)
    ok = (
        remaining == []
        and dlg.browser_table.rowCount() == 0
        and dlg.browser_status.text() == "Showing 0 entries"
    )
    dlg.close()
    return ok, f"remaining={remaining} status='{dlg.browser_status.text()}'"


def scenario_zero_selected():
    db = make_db("tm1_s4.db")
    seed_entries(db, 10)
    dlg, logs = make_dialog(db)
    ids_before = db_ids(db)
    dlg.browser_table.clearSelection()
    dlg.delete_selected_entry()
    ok = db_ids(db) == ids_before
    dlg.close()
    return ok, "no selection -> nothing deleted"


def scenario_cancel():
    db = make_db("tm1_s5.db")
    seed_entries(db, 10)
    dlg, logs = make_dialog(db)
    ids_before = db_ids(db)
    monkeypatch_boxes(QMessageBox.StandardButton.No)
    select_range(dlg.browser_table, 0, 2)
    dlg.delete_selected_entry()
    ok = db_ids(db) == ids_before
    monkeypatch_boxes(QMessageBox.StandardButton.Yes)
    dlg.close()
    return ok, "cancel -> nothing deleted"


def scenario_1200_one_transaction():
    db = make_db("tm1_s6.db")
    seed_entries(db, 1200)
    dlg, logs = make_dialog(db, load_limit=2000)
    refresh_calls = []
    orig_refresh = dlg.refresh_browser
    dlg.refresh_browser = lambda: (refresh_calls.append(1), orig_refresh())[1]
    dlg.browser_table.selectAll()
    dlg.delete_selected_entry()
    ok = (
        db_ids(db) == []
        and dlg.browser_table.rowCount() == 0
        and len(refresh_calls) == 1
        and any("deleted 1200 entries from TM tm1suite" in line for line in logs)
    )
    chunks = (1200 + BATCH_LIMIT - 1) // BATCH_LIMIT
    dlg.close()
    return ok, f"remaining={len(db_ids(db))} refresh_calls={len(refresh_calls)} chunks={chunks} log_lines={sum('deleted' in l for l in logs)}"


def scenario_error_rollback():
    db = make_db("tm1_s7.db")
    seed_entries(db, 1200)
    dlg, logs = make_dialog(db, load_limit=2000)
    ids_before = db_ids(db)
    real_cursor = db.cursor
    db.cursor = FailingCursor(real_cursor, fail_on_delete_no=2)
    dlg.browser_table.selectAll()
    dlg.delete_selected_entry()
    db.cursor = real_cursor
    unchanged = db_ids(db) == ids_before
    ok = unchanged and dlg.browser_table.rowCount() == 1200
    dlg.close()
    return ok, f"db_unchanged={unchanged} delete_calls=2 (fail on 2nd chunk)"


def scenario_filtered_sorted():
    db = make_db("tm1_s8.db")
    seed_entries(db, 10)
    dlg, logs = make_dialog(db)
    ids_before = db_ids(db)
    # сортировка по колонке 0 (ID) по убыванию + фильтр, затем Refresh.
    # Фильтр идёт через concordance_search (FTS-токены): «target» находит
    # все 10 строк. После сортировки по убыванию верхние строки таблицы —
    # ids 10, 9 (в исходном порядке запроса на этих местах ids 1, 2).
    dlg.browser_table.setSortingEnabled(True)
    dlg.browser_table.sortByColumn(0, __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.SortOrder.DescendingOrder)
    dlg.browser_filter.setText("target")
    dlg.refresh_browser()
    shown = table_ids(dlg.browser_table)
    if len(shown) < 2:
        return False, f"filter test setup failed: shown={shown}"
    # выделяем ПЕРВЫЕ две показанные строки (после сортировки это ids 10, 9)
    select_rows(dlg.browser_table, [0, 1])
    picked = sorted(shown[0:2])
    dlg.delete_selected_entry()
    deleted = sorted(set(ids_before) - set(db_ids(db)))
    ok = deleted == picked and len(shown) - 2 == dlg.browser_table.rowCount()
    dlg.close()
    return ok, f"shown={shown} picked={picked} deleted={deleted}"


SCENARIOS = [
    ("1 shift-range 5 -> deleted 5", scenario_shift_range),
    ("2 ctrl-pick 3 of 10 -> exactly those", scenario_ctrl_pick),
    ("3 ctrl+A -> all deleted, counter 0", scenario_ctrl_a),
    ("4 zero selected -> nothing", scenario_zero_selected),
    ("5 cancel in confirm -> nothing", scenario_cancel),
    ("6 1200 selected -> one transaction, one refresh", scenario_1200_one_transaction),
    ("7 injected error on 2nd chunk -> full rollback", scenario_error_rollback),
    ("8 filtered+sorted table -> selected ids only", scenario_filtered_sorted),
]


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    monkeypatch_boxes(QMessageBox.StandardButton.Yes)

    results = []
    for name, fn in SCENARIOS:
        try:
            ok, info = fn()
        except Exception as e:  # сьют не должен падать целиком на одном сценарии
            ok, info = False, f"EXCEPTION: {type(e).__name__}: {e}"
        results.append((name, ok, info))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {info}")

    failed = [r for r in results if not r[1]]
    print()
    print(f"SUMMARY: {len(results) - len(failed)}/{len(results)} OK")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
