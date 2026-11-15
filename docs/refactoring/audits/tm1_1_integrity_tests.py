r"""
BATCH TM1.1 test suite (commit 3) — целостность таблицы Browse All и удаления
(modules/tm_manager_qt.py, TMManagerDialog.refresh_browser / delete_selected_entry).

Сценарии (offscreen, изолированный SUPERVERTALER_DATA_ROOT, временная TM-база,
N = 30 записей с уникальными source/target):
  a. После refresh каждая строка: ID == id из БД для её (source,target);
     дублей ID нет; число строк == числу записей в БД.
  b. То же после сортировки кликом по заголовку КАЖДОЙ колонки (asc/desc) и
     после повторного refresh; попутно: сортировка по ID — числовая (1..30),
     а не лексикографическая (1, 10, 11, ..., 2).
  c. То же с активным фильтром (подстрока) и после очистки фильтра + refresh
     (без пустых строк).
  d. Удаление на таблице, отсортированной по Source: диапазон (Shift) +
     Ctrl+клик; из БД исчезают РОВНО записи с выделенными source/target,
     остальные на месте, их ID не изменились.
  e. Удаление при активном фильтре — то же.
  f. Повторный refresh после удаления: таблица совпадает с БД.

Дополнительно: окно подтверждения содержит список ID удаляемых записей.

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen SUPERVERTALER_DATA_ROOT=<изолированный профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm1_1_integrity_tests.py

На «до»-коде (BATCH TM1, коммит 2) падают сценарии b/c/d/e/f (рассинхрон
строк при включённой сортировке во время заполнения); сценарий a на свежем
окне проходит и там (индикатор сортировки ещё невалиден).
"""

import os
import sys

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM1_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(os.environ.get("TM1_STAGE_DIR", STAGE_ROOT), "tm1_1-suite-profile")

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

from PyQt6.QtCore import QItemSelectionModel, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidgetSelectionRange

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog

N_ENTRIES = 30
DB_PATH = os.path.join(PROFILE, "tm1_1_suite.db")

CAPTURED_CONFIRM = []  # текст последнего окна подтверждения


# --- инфраструктура -------------------------------------------------------------


def make_db():
    for suffix in ("", "-wal", "-shm"):
        p = DB_PATH + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=DB_PATH, log_callback=lambda *a, **k: None)
    db.connect()
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM1.1 suite TM', 'tm11suite', 'en', 'nl')"
    )
    db.connection.commit()
    for i in range(1, N_ENTRIES + 1):
        db.add_translation_unit(
            source=f"unique-src-{i:03d} payload",
            target=f"unique-tgt-{i:03d} payload",
            source_lang="en",
            target_lang="nl",
            tm_id="tm11suite",
        )
    db.connection.commit()
    return db


def db_id_source_map(db):
    db.cursor.execute("SELECT id, source_text, target_text FROM translation_units")
    return {
        r["id"]: (r["source_text"], r["target_text"]) for r in db.cursor.fetchall()
    }


def db_row_count(db):
    db.cursor.execute("SELECT COUNT(*) AS n FROM translation_units")
    return db.cursor.fetchone()["n"]


def close_db(db):
    try:
        db.connection.close()
    except Exception:
        pass


def monkeypatch_boxes(question_answer=QMessageBox.StandardButton.Yes):
    def fake_question(parent, title, text, *a, **k):
        CAPTURED_CONFIRM.append(text)
        return question_answer

    QMessageBox.question = staticmethod(fake_question)
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)


def make_dialog(db):
    return TMManagerDialog(None, db, log_callback=lambda msg: None)


def check_table_integrity(dlg, id_map):
    """a/b/c-проверка: каждая строка ID == id её (source,target); без дублей;
    число строк == числу записей в БД; нет пустых ячеек ID/Source/Target."""
    table = dlg.browser_table
    n_rows = table.rowCount()
    problems = []
    ids_seen = []
    for row in range(n_rows):
        it0 = table.item(row, 0)
        it1 = table.item(row, 1)
        it2 = table.item(row, 2)
        if it0 is None or it1 is None or it2 is None:
            problems.append(f"row {row}: missing cell")
            continue
        if not it0.text().strip():
            problems.append(f"row {row}: empty ID cell")
            continue
        entry_id = int(it0.text())
        ids_seen.append(entry_id)
        want = id_map.get(entry_id)
        if want is None:
            problems.append(f"row {row}: id {entry_id} not in db")
        elif it1.text() != want[0][:100] or it2.text() != want[1][:100]:
            problems.append(f"row {row}: id {entry_id} shows foreign text")
    dup = len(ids_seen) - len(set(ids_seen))
    if dup:
        problems.append(f"duplicate IDs: {dup}")
    if n_rows != len(id_map):
        problems.append(f"row count {n_rows} != db count {len(id_map)}")
    return problems


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


def shown_pairs(table, rows):
    """(id, source, target) того, что ПОКАЗАНО в данных строках."""
    pairs = []
    for r in rows:
        it0, it1, it2 = table.item(r, 0), table.item(r, 1), table.item(r, 2)
        pairs.append(
            (
                int(it0.text()) if it0 is not None and it0.text().strip() else None,
                it1.text() if it1 is not None else None,
                it2.text() if it2 is not None else None,
            )
        )
    return pairs


# --- сценарии ---------------------------------------------------------------------


def scenario_a_after_refresh():
    db = make_db()
    dlg = make_dialog(db)
    id_map = db_id_source_map(db)
    problems = check_table_integrity(dlg, id_map)
    ok = not problems and dlg.browser_status.text() == "Showing 30 entries"
    dlg.close()
    close_db(db)
    return ok, f"problems={problems[:5]}"


def scenario_b_sort_every_column():
    db = make_db()
    dlg = make_dialog(db)
    id_map = db_id_source_map(db)
    table = dlg.browser_table
    problems = []
    for col in range(table.columnCount()):
        for order in (Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder):
            table.sortByColumn(col, order)  # клик по заголовку
            dlg.refresh_browser()
            p = check_table_integrity(dlg, id_map)
            if p:
                problems.append(f"col {col} {order}: {p[:3]}")
    # повторный refresh на отсортированной таблице
    table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    dlg.refresh_browser()
    dlg.refresh_browser()
    p = check_table_integrity(dlg, id_map)
    if p:
        problems.append(f"double refresh: {p[:3]}")
    # числовая сортировка по ID: asc должен дать 1..30 (не 1, 10, 11, ...)
    table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    dlg.refresh_browser()
    ids = [int(table.item(r, 0).text()) for r in range(table.rowCount())]
    numeric_ok = ids == sorted(ids) and ids[0] == 1 and ids[-1] == N_ENTRIES
    ok = not problems and numeric_ok
    dlg.close()
    close_db(db)
    return ok, f"problems={problems[:5]} numeric_id_sort={numeric_ok}"


def scenario_c_filter_on_off():
    db = make_db()
    dlg = make_dialog(db)
    id_map = db_id_source_map(db)
    table = dlg.browser_table
    problems = []
    # пользователь отсортировал, затем включил фильтр
    table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
    dlg.browser_filter.setText("payload")  # FTS-токен: находят все 30 записей
    dlg.refresh_browser()
    p = check_table_integrity(dlg, id_map)
    if p:
        problems.append(f"filter on: {p[:3]}")
    # узкий фильтр
    dlg.browser_filter.setText("unique-tgt-007")
    dlg.refresh_browser()
    if table.rowCount() != 1:
        problems.append(f"narrow filter: rows={table.rowCount()} expected 1")
    # очистка фильтра + refresh: полная таблица, без пустых строк
    dlg.browser_filter.setText("")
    dlg.refresh_browser()
    p = check_table_integrity(dlg, id_map)
    if p:
        problems.append(f"filter cleared: {p[:3]}")
    empty_rows = [
        r for r in range(table.rowCount())
        if table.item(r, 0) is None or not table.item(r, 0).text().strip()
    ]
    if empty_rows:
        problems.append(f"empty rows after filter cleared: {empty_rows[:5]}")
    ok = not problems
    dlg.close()
    close_db(db)
    return ok, f"problems={problems[:5]}"


def scenario_d_delete_sorted_by_source():
    db = make_db()
    dlg = make_dialog(db)
    table = dlg.browser_table
    before = db_id_source_map(db)
    # сортировка по Source asc + refresh, как в ручном сценарии
    table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
    dlg.refresh_browser()
    # Shift-диапазон строк 0..1 + Ctrl+клик по строке 5
    select_range(table, 0, 1)
    table.selectionModel().select(
        table.model().index(5, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    picked = shown_pairs(table, [0, 1, 5])
    picked_sources = [p[1] for p in picked]
    picked_ids = sorted(p[0] for p in picked)
    dlg.delete_selected_entry()
    after = db_id_source_map(db)
    deleted = sorted(set(before) - set(after))
    # из БД исчезли ровно записи с показанными source/target
    expected = sorted(i for i, (s, t) in before.items() if s[:100] in picked_sources)
    # остальные на месте, их ID не изменились
    others_intact = all(
        before[i] == after.get(i) for i in before if i not in deleted
    )
    # окно подтверждения содержало список ID
    confirm_ok = bool(CAPTURED_CONFIRM) and "IDs:" in CAPTURED_CONFIRM[-1] and all(
        str(i) in CAPTURED_CONFIRM[-1] for i in picked_ids
    )
    ok = deleted == expected == picked_ids and others_intact and confirm_ok
    dlg.close()
    close_db(db)
    return ok, (
        f"picked_ids={picked_ids} deleted={deleted} others_intact={others_intact} "
        f"confirm_shows_ids={confirm_ok}"
    )


def scenario_e_delete_with_filter():
    db = make_db()
    dlg = make_dialog(db)
    table = dlg.browser_table
    before = db_id_source_map(db)
    dlg.browser_filter.setText("payload")
    table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    dlg.refresh_browser()
    rows = [0, 2, 4]
    select_rows(table, rows)
    picked = shown_pairs(table, rows)
    picked_sources = [p[1] for p in picked]
    dlg.delete_selected_entry()
    after = db_id_source_map(db)
    deleted = sorted(set(before) - set(after))
    expected = sorted(i for i, (s, t) in before.items() if s[:100] in picked_sources)
    ok = deleted == expected and db_row_count(db) == N_ENTRIES - len(expected)
    dlg.close()
    close_db(db)
    return ok, f"picked={picked_sources} deleted={deleted}"


def scenario_f_refresh_after_delete():
    db = make_db()
    dlg = make_dialog(db)
    table = dlg.browser_table
    before = db_id_source_map(db)
    table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    dlg.refresh_browser()
    select_range(table, 0, 4)
    dlg.delete_selected_entry()
    # повторный refresh после удаления: таблица совпадает с БД
    dlg.refresh_browser()
    after = db_id_source_map(db)
    problems = check_table_integrity(dlg, after)
    shown = sorted(
        int(table.item(r, 0).text()) for r in range(table.rowCount()) if table.item(r, 0)
    )
    ok = (
        not problems
        and shown == sorted(after)
        and len(after) == len(before) - 5
        and dlg.browser_status.text() == f"Showing {len(after)} entries"
    )
    dlg.close()
    close_db(db)
    return ok, f"problems={problems[:5]} remaining={len(after)}"


SCENARIOS = [
    ("a refresh -> rows match db", scenario_a_after_refresh),
    ("b sort by each column + double refresh -> rows match db", scenario_b_sort_every_column),
    ("c filter on/narrow/cleared -> rows match db, no empty rows", scenario_c_filter_on_off),
    ("d delete on Source-sorted table -> exactly shown entries", scenario_d_delete_sorted_by_source),
    ("e delete with active filter -> exactly selected entries", scenario_e_delete_with_filter),
    ("f refresh after delete -> table matches db", scenario_f_refresh_after_delete),
]


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    monkeypatch_boxes(QMessageBox.StandardButton.Yes)

    results = []
    for name, fn in SCENARIOS:
        CAPTURED_CONFIRM.clear()
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
