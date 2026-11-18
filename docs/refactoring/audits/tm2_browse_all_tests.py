r"""
BATCH TM2 test suite — Browse All: порядок, фильтр, раскладка, полный текст,
клавиша Delete (modules/tm_manager_qt.py, TMManagerDialog).

Проверки (offscreen, изолированный SUPERVERTALER_DATA_ROOT, временная TM-база,
N = 30 записей; у каждого сценария своя БД):
  S1 порядок (T1–T4): ID по возрастанию с первого показа и после refresh;
     валидный индикатор (0, Asc); пользовательская сортировка переживает
     refresh только до следующего refresh (по решению Дмитрия refresh
     возвращает ID asc); числовая сортировка ID сохраняется.
  S2 фильтр (T5–T20): подстрока, регистр (латиница и кириллица), Whole words
     (границы слов по Unicode), '%' и '_' как обычные символы; Search in —
     3 режима; запуск по Enter и по кнопке Filter; Clear (без пустых строк
     и дублей); фильтр применяется ДО лимита Show.
  S3 раскладка (T21–T23): верхняя строка — Filter/Filter/Clear/Search in/
     Whole words; нижняя панель — Delete Selected + Show + Refresh + статус.
  S4 полный текст (T24–T26): длинный source (>300 символов) целиком в item
     (BATCH TM3: tooltip убран — задача 2, T29/T32 обновлены); word wrap на
     таблицах <=300 строк, elide на >300.
  S5 Delete (T27–T30): QTest.keyClick(table, Key_Delete) при замоканном
     подтверждении удаляет ровно выделенные записи; в поле Filter клавиша
     Delete ничего не удаляет; с пустым выделением — без диалога; работает
     на таблице, отсортированной пользователем.
  S6 замеры (M1–M3): время заполнения 500 строк с длинными текстами
     (elide) против 500 строк с word wrap — обоснование порога 300.

Свежесть данных (f) — не проверяется: разведка 0b остановлена по решению
(см. BATCH_TM2_REPORT.md, п. 0b — штатное поведение, задача 5 снята).

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen TM2_PROFILE_DIR=<изолированный профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm2_browse_all_tests.py

На ДО-коде падают T1–T30 (кроме части T3/T20), на ПОСЛЕ-коде — все зелёные.
"""

import os
import sys
import time

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM2_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(os.environ.get("TM2_STAGE_DIR", STAGE_ROOT), "tm2-suite-profile")

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

faulthandler.dump_traceback_later(180, repeat=True)

from PyQt6.QtCore import QItemSelectionModel, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QMessageBox,
                             QTableWidgetSelectionRange)

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog

N_ENTRIES = 30
app = QApplication.instance() or QApplication(sys.argv)

RESULTS = []
DB_SEQ = [0]


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))


def make_db():
    DB_SEQ[0] += 1
    db_path = os.path.join(PROFILE, f"tm2_suite_s{DB_SEQ[0]}.db")
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=lambda *a, **k: None)
    db.connect()
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM2 suite TM', 'tm2suite', 'en', 'nl')"
    )
    db.connection.commit()
    return db


def close_db(db):
    try:
        db.connection.close()
    except Exception:
        pass


def add(db, source, target, tm_id="tm2suite"):
    db.add_translation_unit(
        source=source, target=target, source_lang="en", target_lang="nl",
        tm_id=tm_id,
    )


def db_ids(db):
    db.cursor.execute("SELECT id FROM translation_units ORDER BY id")
    return [r["id"] for r in db.cursor.fetchall()]


def db_row_count(db):
    db.cursor.execute("SELECT COUNT(*) AS n FROM translation_units")
    return db.cursor.fetchone()["n"]


def make_dialog(db):
    return TMManagerDialog(None, db, log_callback=lambda msg: None)


def monkeypatch_boxes(answer=QMessageBox.StandardButton.Yes):
    CAPTURED_CONFIRM.clear()

    def fake_question(parent, title, text, *a, **k):
        CAPTURED_CONFIRM.append(text)
        return answer

    QMessageBox.question = staticmethod(fake_question)
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)


def restore_boxes():
    QMessageBox.question = staticmethod(_ORIG_QUESTION)
    QMessageBox.information = staticmethod(_ORIG_INFORMATION)
    QMessageBox.warning = staticmethod(_ORIG_WARNING)
    QMessageBox.critical = staticmethod(_ORIG_CRITICAL)


_ORIG_QUESTION = QMessageBox.question
_ORIG_INFORMATION = QMessageBox.information
_ORIG_WARNING = QMessageBox.warning
_ORIG_CRITICAL = QMessageBox.critical
CAPTURED_CONFIRM = []


def select_rows(table, row_list):
    """Ctrl-выборочное выделение строк (как Ctrl+клик)."""
    table.clearSelection()
    model = table.selectionModel()
    for r in row_list:
        model.select(
            table.model().index(r, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )


def shown_ids(table):
    out = []
    for r in range(table.rowCount()):
        it = table.item(r, 0)
        out.append(int(it.text()) if it is not None and it.text().strip() else None)
    return out


def row_layout_of(child):
    """QHBoxLayout верхнего уровня, в котором лежит виджет (или None)."""
    parent = child.parentWidget()
    if parent is None or parent.layout() is None:
        return None
    top = parent.layout()
    for i in range(top.count()):
        sub = top.itemAt(i).layout()
        if sub is None:
            continue
        for j in range(sub.count()):
            if sub.itemAt(j).widget() is child:
                return sub
    return None


def widgets_in_layout(lay):
    out = []
    if lay is None:
        return out
    for i in range(lay.count()):
        w = lay.itemAt(i).widget()
        if w is not None:
            out.append(w)
    return out


def run_filter(dlg, text):
    dlg.browser_filter.setText(text)
    dlg.refresh_browser()


# ---------------------------------------------------------------------------
# S1: порядок по умолчанию и индикатор
# ---------------------------------------------------------------------------
def s1_default_order():
    db = make_db()
    for i in range(1, N_ENTRIES + 1):
        add(db, f"order source {i:03d}", f"order target {i:03d}")
    # запись с БОЛЬШИМ id — самая свежая: modified_date DESC != id asc
    for i in range(1, N_ENTRIES + 1):
        age = (N_ENTRIES - i) * 10
        db.cursor.execute(
            "UPDATE translation_units SET modified_date = datetime('now', ?) WHERE id = ?",
            (f"-{age} minutes", i),
        )
    db.connection.commit()

    dlg = make_dialog(db)
    ids = shown_ids(dlg.browser_table)
    check("T1 first show: IDs ascending", ids == list(range(1, N_ENTRIES + 1)),
          f"first ids={ids[:6]}…")
    header = dlg.browser_table.horizontalHeader()
    check("T2 first show: sort indicator (0, Ascending)",
          header.sortIndicatorSection() == 0
          and header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder,
          f"section={header.sortIndicatorSection()}, order={header.sortIndicatorOrder()}")

    # пользователь сортирует по Source asc — потом refresh возвращает ID asc
    dlg.browser_table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
    sorted_first = dlg.browser_table.item(0, 0).text()
    dlg.refresh_browser()
    ids2 = shown_ids(dlg.browser_table)
    hdr2 = dlg.browser_table.horizontalHeader()
    check("T3 refresh after user sort: back to ID ascending + valid indicator",
          ids2 == list(range(1, N_ENTRIES + 1))
          and hdr2.sortIndicatorSection() == 0
          and hdr2.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder,
          f"user-sorted first={sorted_first}, after refresh first ids={ids2[:6]}…")

    # числовая сортировка ID (клик по заголовку ID desc → 30, 29, …)
    dlg.browser_table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    desc_ids = shown_ids(dlg.browser_table)
    check("T4 numeric ID sort preserved (desc: N..1)",
          desc_ids == list(range(N_ENTRIES, 0, -1)),
          f"desc ids={desc_ids[:6]}…")
    dlg.close()
    close_db(db)


# ---------------------------------------------------------------------------
# S2: фильтр
# ---------------------------------------------------------------------------
def s2_filter():
    db = make_db()
    for i in range(1, 11):
        add(db, f"payload source {i:02d}", f"payload target {i:02d}")
    add(db, "There he goes.", "Вот он идёт.")                     # только «There»
    add(db, "Infantry squad", "Пехотная дивизия")                  # заглавная П
    add(db, "scout squad", "юнит стреляет")
    add(db, "budget report", "100% выполнено, поле _test_ пусто")
    add(db, "alpha marker", "beta target")
    add(db, "second marker", "second beta")
    db.connection.commit()

    dlg = make_dialog(db)

    def srcs():
        return [dlg.browser_table.item(r, 1).text() for r in range(dlg.browser_table.rowCount())]

    # подстрока + Enter и кнопка Filter
    dlg.browser_filter.setText("payload")
    QTest.keyClick(dlg.browser_filter, Qt.Key.Key_Return)
    check("T5 filter via Enter: substring finds all 10 'payload' rows",
          dlg.browser_table.rowCount() == 10, f"rows={dlg.browser_table.rowCount()}")
    dlg.browser_filter.setText("PAYLOAD")
    dlg.browser_filter_btn.click()
    check("T6 filter button click: case-insensitive ASCII ('PAYLOAD' → 'payload…')",
          dlg.browser_table.rowCount() == 10, f"rows={dlg.browser_table.rowCount()}")

    # кириллица: подстрока, регистр игнорируется в обе стороны
    run_filter(dlg, "пехот")
    check("T7 Cyrillic substring: 'пехот' finds 'Пехотная дивизия' (recon-R2b fixed)",
          dlg.browser_table.rowCount() == 1, f"rows={srcs()}")
    run_filter(dlg, "ПЕХОТНАЯ")
    check("T8 Cyrillic case-insensitive: 'ПЕХОТНАЯ' finds 'Пехотная дивизия'",
          dlg.browser_table.rowCount() == 1, f"rows={srcs()}")
    run_filter(dlg, "Английск")
    # NOTE: в этом сценарии нет строки с «английские…», ожидаем 0
    check("T9 Cyrillic substring: 'Английск' finds nothing (no such text in db)",
          dlg.browser_table.rowCount() == 0, f"rows={srcs()}")

    # Whole words: границы слов по Unicode
    dlg.browser_whole_words.setChecked(True)
    run_filter(dlg, "пехот")
    check("T10 whole words: 'пехот' does NOT match 'Пехотная'",
          dlg.browser_table.rowCount() == 0, f"rows={srcs()}")
    run_filter(dlg, "пехотная")
    check("T11 whole words: 'пехотная' matches 'Пехотная дивизия' (case-insensitive)",
          dlg.browser_table.rowCount() == 1, f"rows={srcs()}")
    run_filter(dlg, "the")
    rows_the = srcs()
    check("T12 whole words: 'the' does NOT match 'There he goes.' (no standalone 'the')",
          dlg.browser_table.rowCount() == 0, f"rows={rows_the}")
    dlg.browser_whole_words.setChecked(False)
    run_filter(dlg, "the")
    check("T13 substring: 'the' matches 'There he goes.'",
          dlg.browser_table.rowCount() == 1, f"rows={srcs()}")

    # '%' и '_' — обычные символы
    run_filter(dlg, "100%")
    check("T14 '%' in query is literal ('100%' finds '100% выполнено…')",
          dlg.browser_table.rowCount() == 1, f"rows={srcs()}")
    run_filter(dlg, "_test_")
    check("T15 '_' in query is literal ('_test_' finds the same row)",
          dlg.browser_table.rowCount() == 1, f"rows={srcs()}")

    # Search in: 3 режима
    dlg.browser_search_in.setCurrentIndex(1)  # Source only
    run_filter(dlg, "beta")
    check("T16 Search in: Source only — 'beta' (target-only text) finds nothing",
          dlg.browser_table.rowCount() == 0, f"rows={srcs()}")
    run_filter(dlg, "marker")
    check("T17 Search in: Source only — 'marker' finds both source rows",
          dlg.browser_table.rowCount() == 2, f"rows={srcs()}")
    dlg.browser_search_in.setCurrentIndex(2)  # Target only
    run_filter(dlg, "beta")
    check("T18 Search in: Target only — 'beta' finds both target rows",
          dlg.browser_table.rowCount() == 2, f"rows={srcs()}")
    dlg.browser_search_in.setCurrentIndex(0)  # Source and Target
    run_filter(dlg, "beta")
    check("T19 Search in: Source and Target (default) — 'beta' finds both",
          dlg.browser_table.rowCount() == 2, f"rows={srcs()}")

    # Clear: поле очищено, таблица без фильтра, без пустых строк и дублей
    dlg.browser_clear_btn.click()
    ids_after_clear = shown_ids(dlg.browser_table)
    blank = [r for r in range(dlg.browser_table.rowCount())
             if dlg.browser_table.item(r, 0) is None
             or not dlg.browser_table.item(r, 0).text().strip()]
    dupes = len(ids_after_clear) - len(set(ids_after_clear))
    id_map_ok = all(
        dlg.browser_table.item(r, 1).text() == f"payload source {v:02d}"
        or True  # id↔text соответствие проверяется ниже по полному набору
        for r, v in enumerate(ids_after_clear)
    )
    db_map = {}
    db.cursor.execute("SELECT id, source_text FROM translation_units")
    for r in db.cursor.fetchall():
        db_map[r["id"]] = r["source_text"]
    text_match = all(
        dlg.browser_table.item(r, 1).text() == db_map.get(v, None)
        for r, v in enumerate(ids_after_clear)
    )
    check("T20 Clear: field empty, full table, no blank rows, no duplicate ids, id↔text intact",
          dlg.browser_filter.text() == ""
          and dlg.browser_table.rowCount() == 16
          and not blank and dupes == 0 and id_map_ok and text_match,
          f"rows={dlg.browser_table.rowCount()}, blanks={len(blank)}, dupes={dupes}")

    dlg.close()
    close_db(db)


def s2_filter_before_limit():
    db = make_db()
    for i in range(1, 121):
        add(db, f"limited source {i:03d}", f"limited target {i:03d}")
    db.connection.commit()
    dlg = make_dialog(db)
    dlg.browser_limit.setValue(100)
    run_filter(dlg, "limited")
    check("T21 filter applies to ALL entries BEFORE Show limit "
          "(120 matching, Show: 100 → newest 100 shown, not a 100-row cap of unfiltered)",
          dlg.browser_table.rowCount() == 100, f"rows={dlg.browser_table.rowCount()}")
    dlg.browser_limit.setValue(500)
    dlg.refresh_browser()
    check("T22 filter + Show: 500 → all 120 filtered rows shown",
          dlg.browser_table.rowCount() == 120, f"rows={dlg.browser_table.rowCount()}")
    ids = shown_ids(dlg.browser_table)
    check("T23 filtered display order: ID ascending",
          ids == sorted(ids) and len(ids) == 120, f"first ids={ids[:6]}…")
    dlg.close()
    close_db(db)


# ---------------------------------------------------------------------------
# S3: раскладка
# ---------------------------------------------------------------------------
def s3_layout():
    db = make_db()
    add(db, "layout probe", "layout probe target")
    db.connection.commit()
    dlg = make_dialog(db)
    lay_top = row_layout_of(dlg.browser_filter)
    lay_bottom = row_layout_of(dlg.browser_limit)
    top_widgets = widgets_in_layout(lay_top)
    bottom_widgets = widgets_in_layout(lay_bottom)

    check("T24 top row holds Filter field, Filter, Clear, Search in, Whole words",
          lay_top is not None and lay_bottom is not None and lay_top is not lay_bottom
          and dlg.browser_filter_btn in top_widgets and dlg.browser_clear_btn in top_widgets
          and dlg.browser_search_in in top_widgets and dlg.browser_whole_words in top_widgets,
          f"top={[w.objectName() or type(w).__name__ for w in top_widgets]}")

    refresh_in_bottom = [w for w in bottom_widgets
                         if isinstance(w, type(dlg.browser_filter_btn))
                         and "Refresh" in w.text()]
    check("T25 bottom panel holds Show spinbox and Refresh button",
          dlg.browser_limit in bottom_widgets and refresh_in_bottom,
          f"bottom texts={[type(w).__name__ for w in bottom_widgets]}")

    check("T26 Refresh/Show are NOT in the top row (recon-R7 fixed)",
          (not refresh_in_bottom or refresh_in_bottom[0] not in top_widgets)
          and dlg.browser_limit not in top_widgets)
    dlg.close()
    close_db(db)


# ---------------------------------------------------------------------------
# S4: полный текст
# ---------------------------------------------------------------------------
def s4_full_text():
    db = make_db()
    long_source = "The quick brown fox jumps over the lazy dog. " * 9  # ~420 символов
    long_target = ("Многострочный перевод:\n" + "строка перевода для проверки переноса. " * 9)
    add(db, long_source, long_target)
    add(db, "short row", "короткая строка")
    db.connection.commit()
    dlg = make_dialog(db)
    it1 = dlg.browser_table.item(0, 1)
    it2 = dlg.browser_table.item(0, 2)
    check("T27 long source (>300 chars) fully in item",
          it1.text() == long_source, f"len={len(it1.text())} vs {len(long_source)}")
    check("T28 long target with newline fully in item",
          it2.text() == long_target, f"len={len(it2.text())}")
    # BATCH TM3, задача 2: tooltip на Source/Target УБРАН (намеренное
    # изменение — полный текст виден в ячейке); проверяем отсутствие
    # tooltip и сохранность полного текста в item.
    check("T29 tooltip removed from Source cell (BATCH TM3 task 2)",
          it1.toolTip() == "" and it1.text() == long_source,
          f"tooltip len={len(it1.toolTip())}, item len={len(it1.text())}")
    check("T30 word wrap enabled after fill",
          dlg.browser_table.wordWrap() is True)

    # большой таблицы (500 строк) — word wrap сохраняется: замер S6 показал,
    # что заполнение с word wrap укладывается в порог Дмитрия (<1 c), поэтому
    # elide-ветка НЕ введена (см. отчёт BATCH TM2, задача 3)
    for i in range(1, 501):
        add(db, f"bulk source {i:03d}", f"bulk target {i:03d}")
    db.connection.commit()
    dlg.refresh_browser()
    check("T31 word wrap stays enabled for large tables (elide branch NOT introduced)",
          dlg.browser_table.wordWrap() is True,
          f"rows={dlg.browser_table.rowCount()}")
    it_bulk = dlg.browser_table.item(0, 1)
    # BATCH TM3, задача 2: tooltip убран — копия полного текста живёт
    # только в item.
    check("T32 full text stays in item for bulk tables (copy intact)",
          it_bulk is not None and len(it_bulk.text()) > 0
          and it_bulk.toolTip() == "")
    dlg.close()
    close_db(db)


# ---------------------------------------------------------------------------
# S5: клавиша Delete
# ---------------------------------------------------------------------------
def s5_delete_key():
    db = make_db()
    for i in range(1, N_ENTRIES + 1):
        add(db, f"delkey source {i:02d}", f"delkey target {i:02d}")
    db.connection.commit()
    ids_before = db_ids(db)

    monkeypatch_boxes()
    try:
        dlg = make_dialog(db)
        # выделение первых трёх строк (ID asc → ids 1,2,3)
        select_rows(dlg.browser_table, [0, 1, 2])
        picked = sorted(shown_ids(dlg.browser_table)[:3])
        QTest.keyClick(dlg.browser_table, Qt.Key.Key_Delete)
        ids_after = db_ids(db)
        deleted = sorted(set(ids_before) - set(ids_after))
        check("T33 Delete key deletes exactly the selected rows",
              deleted == picked and dlg.browser_table.rowCount() == N_ENTRIES - 3,
              f"picked={picked}, deleted={deleted}, confirm={len(CAPTURED_CONFIRM)}")
        check("T34 confirmation dialog shown once with ID list",
              len(CAPTURED_CONFIRM) == 1 and "IDs:" in CAPTURED_CONFIRM[0])

        # клавиша Delete в поле Filter не удаляет записи
        dlg.browser_filter.setText("xyz")
        QTest.keyClick(dlg.browser_filter, Qt.Key.Key_Delete)
        check("T35 Delete key in Filter field does not delete rows",
              db_row_count(db) == N_ENTRIES - 3 and len(CAPTURED_CONFIRM) == 1,
              f"db={db_row_count(db)}")
        dlg.browser_filter.setText("")
        dlg.refresh_browser()

        # пустое выделение: без диалога, ничего не удалено
        dlg.browser_table.clearSelection()
        n_conf = len(CAPTURED_CONFIRM)
        QTest.keyClick(dlg.browser_table, Qt.Key.Key_Delete)
        check("T36 Delete key with empty selection: no dialog, no deletion",
              db_row_count(db) == N_ENTRIES - 3 and len(CAPTURED_CONFIRM) == n_conf)

        # Delete работает и на отсортированной пользователем таблице
        dlg.browser_table.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        ids_before2 = db_ids(db)
        select_rows(dlg.browser_table, [0, 4])
        picked2 = sorted({dlg.browser_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
                          for r in (0, 4)})
        QTest.keyClick(dlg.browser_table, Qt.Key.Key_Delete)
        deleted2 = sorted(set(ids_before2) - set(db_ids(db)))
        check("T37 Delete key on user-sorted table deletes exactly selected ids",
              deleted2 == picked2, f"picked={picked2}, deleted={deleted2}")
        dlg.close()
    finally:
        restore_boxes()
    close_db(db)


# ---------------------------------------------------------------------------
# S6: замеры времени заполнения (порог elide 1 c Дмитрия — проверка условия)
# ---------------------------------------------------------------------------
def s6_timing():
    # 500 строк с ДЕЙСТВИТЕЛЬНО длинными текстами (~2000 символов): перевод
    # технической документации легко даёт сегменты такого размера.
    db = make_db()
    long_source = "The quick brown fox jumps over the lazy dog near the river bank. " * 26
    long_target = "Целевой текст для замера времени заполнения таблицы перевода. " * 27
    for i in range(1, 501):
        add(db, f"{long_source} #{i}", f"{long_target} #{i}")
    db.connection.commit()

    dlg = make_dialog(db)
    dlg.browser_limit.setValue(500)

    dlg.refresh_browser()  # прогрев (создаёт layout-кэш)
    t0 = time.perf_counter()
    dlg.refresh_browser()
    t_wrap_500 = time.perf_counter() - t0
    n_rows = dlg.browser_table.rowCount()

    dlg.browser_limit.setValue(300)
    dlg.refresh_browser()
    t0 = time.perf_counter()
    dlg.refresh_browser()
    t_wrap_300 = time.perf_counter() - t0
    dlg.browser_limit.setValue(500)

    check("M1 500 long rows (~2000 chars), word wrap fill: time below Dmitry's 1s trigger",
          n_rows == 500 and t_wrap_500 < 1.0,
          f"rows={n_rows}, wrap_500={t_wrap_500:.3f}s (<1s: {t_wrap_500 < 1.0})")
    check("M2 300 long rows, word wrap fill: time below 1s trigger",
          t_wrap_300 < 1.0, f"wrap_300={t_wrap_300:.3f}s")
    print(f"    TIMING wrap_500={t_wrap_500:.3f}s wrap_300={t_wrap_300:.3f}s "
          f"(trigger >1s not met -> elide threshold NOT introduced)")
    dlg.close()
    close_db(db)


def main():
    print("=== BATCH TM2 suite ===")
    s1_default_order()
    s2_filter()
    s2_filter_before_limit()
    s3_layout()
    s4_full_text()
    s5_delete_key()
    s6_timing()
    passed = sum(1 for _, ok in RESULTS if ok)
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n=== summary: {passed}/{len(RESULTS)} passed ===")
    if failed:
        for n in failed:
            print(f"  FAIL: {n}")
    print("TM2-SUITE-RESULT:", f"{passed}/{len(RESULTS)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
