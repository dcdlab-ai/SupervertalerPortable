r"""
BATCH TM2 recon-test «до» — воспроизведение проблем Browse All
(modules/tm_manager_qt.py, TMManagerDialog.refresh_browser и окрестности).

Проблемы, которые сценарии обязаны воспроизвести на ДО-коде:
  R1. Порядок по умолчанию: строки показываются по modified_date DESC, а не
      по ID по возрастанию; индикатор сортировки невалиден до первого клика.
  R2. Фильтр (0a): refresh_browser с непустым полем Filter идёт через
      concordance_search → FTS5-фраза (целые слова, не подстрока):
        - «the» НЕ находит строку, где есть только «There …» (токен there != the);
        - «пехот» не находит «Пехотная дивизия» (токен != подстрока), при этом
          «пехотная» находит её же (целое слово, кириллица складывается) —
          это подтверждает, что дело НЕ в регистре кириллицы на FTS-пути;
        - «юнит» находит «юнит стреляет» (наблюдение Дмитрия).
      Дополнительно демонстрируется LIKE-fallback путь (повреждённый FTS):
        - «the» находит «There …» как подстроку (ASCII-регистр складывается);
        - «пехот» НЕ находит «Пехотная дивизия» с заглавной (LIKE складывает
          регистр только для ASCII) — гипотеза из ТЗ проверена.
  R3. Фильтр игнорирует лимит Show: у concordance_search жёсткий LIMIT 100
      (120 записей в БД, Show: 500 → показывается 100).
  R4. Фильтр всегда ищет в обеих колонках, режима «Search in» нет (структурно:
      проверяется отсутствие комбобокса search-in).
  R5. Обрезка текста (0c): Source/Target обрезаны до 100 символов
      (entry['source_text'][:100]), tooltip пустой.
  R6. Клавиша Delete (0d): QTest.keyClick(table, Key_Delete) при выделенной
      строке и замоканном подтверждении ничего не удаляет (обработчика нет).
  R7. Layout: в верхней строке лежат Filter/Show/Refresh, внизу только
      Delete Selected + статус — раскладка задач 2 не соответствует.

Свежесть данных (0b) — по коду, без скрипта: см. отчёт, п. 0b.

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen SUPERVERTALER_DATA_ROOT/TM2_PROFILE_DIR=<профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm2_recon_before.py

Все находки печатаются как [FOUND]/[NOT-FOUND] с цифрами; на ДО-коде
ожидается: R1..R7 = FOUND (кроме помеченных частичных).
"""

import os
import sys
import time

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM2_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(os.environ.get("TM2_STAGE_DIR", STAGE_ROOT), "tm2-recon-profile")

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

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog

DB_PATH = os.path.join(PROFILE, "tm2_recon.db")
app = QApplication.instance() or QApplication(sys.argv)

FINDINGS = []


def record(name, expected_on_before, found, detail):
    verdict = "FOUND" if found else "NOT-FOUND"
    FINDINGS.append((name, expected_on_before, found))
    print(f"[{verdict}] {name}: {detail}")


_DB_SEQ = [0]


def close_db(db):
    try:
        db.connection.close()
    except Exception:
        pass


def make_db():
    # У каждой сценарной БД свой файл: соединения SQLite не переживают
    # удаление файла, а диалог держит своё подключение открытым.
    _DB_SEQ[0] += 1
    db_path = DB_PATH.replace(".db", f"_s{_DB_SEQ[0]}.db")
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=lambda *a, **k: None)
    db.connect()
    # TM записи нужно регистрировать в translation_memories: phantom-TM
    # write guard отвергает add_translation_unit для незарегистрированных tm_id.
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM2 recon TM', 'tm2recon', 'en', 'nl')"
    )
    db.connection.commit()
    return db


def add(db, source, target, tm_id="tm2recon"):
    db.add_translation_unit(
        source=source, target=target, source_lang="en", target_lang="nl",
        tm_id=tm_id,
    )


def shown_ids(table):
    out = []
    for r in range(table.rowCount()):
        it = table.item(r, 0)
        out.append(int(it.text()) if it is not None and it.text().strip() else None)
    return out


def run_filter(dlg, text):
    dlg.browser_filter.setText(text)
    dlg.refresh_browser()


# ---------------------------------------------------------------------------
# R1: порядок по умолчанию + индикатор
# ---------------------------------------------------------------------------
def r1_default_order():
    db = make_db()
    for i in range(1, 7):
        add(db, f"order source {i:02d}", f"order target {i:02d}")
    # Разводим modified_date по часам: запись с БОЛЬШИМ id — самая свежая,
    # поэтому modified_date DESC показывает [6, 5, 4, 3, 2, 1] — не id-asc.
    db.cursor.execute("UPDATE translation_units SET modified_date = datetime('now', '-50 minutes') WHERE id = 1")
    db.cursor.execute("UPDATE translation_units SET modified_date = datetime('now', '-40 minutes') WHERE id = 2")
    db.cursor.execute("UPDATE translation_units SET modified_date = datetime('now', '-30 minutes') WHERE id = 3")
    db.cursor.execute("UPDATE translation_units SET modified_date = datetime('now', '-20 minutes') WHERE id = 4")
    db.cursor.execute("UPDATE translation_units SET modified_date = datetime('now', '-10 minutes') WHERE id = 5")
    db.cursor.execute("UPDATE translation_units SET modified_date = datetime('now', '-0 minutes') WHERE id = 6")
    db.connection.commit()

    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    ids = shown_ids(dlg.browser_table)
    order_bad = ids and ids[0] != min(x for x in ids if x is not None)
    header = dlg.browser_table.horizontalHeader()
    sec = header.sortIndicatorSection()
    order = header.sortIndicatorOrder()
    indicator_valid = (sec == 0 and order == Qt.SortOrder.AscendingOrder)
    record("R1a default order is NOT id-asc", True, order_bad,
           f"shown ids={ids} (newest-first: id 1 first)")
    record("R1b sort indicator invalid on first show", True, not indicator_valid,
           f"section={sec}, order={order}")
    dlg.close()
    close_db(db)
    return db


# ---------------------------------------------------------------------------
# R2: семантика фильтра (FTS-путь и LIKE-fallback путь)
# ---------------------------------------------------------------------------
def r2_filter_semantics():
    db = make_db()
    add(db, "There he goes.", "Вот он идёт.")            # только «There», слова «the» нет
    add(db, "The unit advances on the hill.", "Английские юниты идут.")  # есть токен «the»; «юниты» != «юнит»
    add(db, "Infantry squad", "Пехотная дивизия")         # заглавная П
    add(db, "Scout reports", "юнит стреляет")             # точный токен «юнит»
    add(db, "пехотный отряд", "small squad")              # строчная строка для LIKE-пути
    add(db, "50% done with _under_score_", "50% и _подчёркивание_")
    db.connection.commit()

    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)

    def srcs():
        return [dlg.browser_table.item(r, 1).text() for r in range(dlg.browser_table.rowCount())]

    run_filter(dlg, "the")
    the_rows = srcs()
    the_found_there = any("There he goes" in s for s in the_rows)
    # FTS: токен the != There → «There he goes.» НЕ найден как подстрока
    record("R2a 'the' does NOT find 'There he goes.' (FTS whole-word)",
           True, not the_found_there,
           f"rows for 'the': {the_rows}")

    run_filter(dlg, "пехот")
    pekhot_rows = srcs()
    record("R2b 'пехот' does NOT find 'Пехотная дивизия' (substring broken)",
           True, len(pekhot_rows) == 0, f"rows: {pekhot_rows}")

    run_filter(dlg, "пехотная")
    pek_word = srcs()
    record("R2c 'пехотная' (whole word) DOES find the 'Пехотная дивизия' row",
           True, len(pek_word) == 1, f"rows: {pek_word}")

    run_filter(dlg, "юнит")
    unit_rows = srcs()
    # «юнит стреляет» лежит в TARGET строки Scout reports; важно, что найдена
    # ровно она, а строка с «юниты» (Английские юниты идут) не попала.
    record("R2d 'юнит' finds exactly the 'юнит стреляет' row and NOT the 'юниты' row "
           "(whole-word: token 'юниты' != 'юнит')",
           True, len(unit_rows) == 1, f"rows: {unit_rows}")

    run_filter(dlg, "английск")
    angl_rows = srcs()
    record("R2e 'английск' finds NOTHING although target contains 'английские…' (Dmitry's case)",
           True, len(angl_rows) == 0, f"rows: {angl_rows}")

    # LIKE-fallback путь: имитируем повреждённый FTS (переименованием таблицы
    # MATCH выбрасывает исключение → в коде fallback на LIKE).
    db.cursor.execute("ALTER TABLE translation_units_fts RENAME TO translation_units_fts_bak")
    db.connection.commit()
    try:
        run_filter(dlg, "the")
        like_rows = srcs()
        record("R2f LIKE-fallback: 'the' DOES find 'There he goes.' (ASCII case folding)",
               True, any("There he goes" in s for s in like_rows), f"rows: {like_rows}")

        run_filter(dlg, "пехот")
        like_pek = srcs()
        like_cap = any("Пехотная" in s for s in like_pek)
        like_low = any("пехотный" in s for s in like_pek)
        record("R2g LIKE-fallback: 'пехот' does NOT find capital 'Пехотная дивизия' "
               "(SQLite LIKE folds ASCII only)", True, not like_cap, f"rows: {like_pek}")
        record("R2h LIKE-fallback: 'пехот' DOES find lowercase 'пехотный отряд' "
               "(case, not substring, is the blocker)", True, like_low, f"rows: {like_pek}")

        run_filter(dlg, "50%")
        pct_rows = srcs()
        record("R2i LIKE-fallback: '%' in query is a wildcard (matches rows containing '50…')",
               True, any("50%" in s for s in pct_rows), f"rows for '50%': {pct_rows}")
    finally:
        db.cursor.execute("ALTER TABLE translation_units_fts_bak RENAME TO translation_units_fts")
        db.connection.commit()

    dlg.close()
    close_db(db)
    return db


# ---------------------------------------------------------------------------
# R3: фильтр игнорирует Show (жёсткий LIMIT 100 у concordance_search)
# ---------------------------------------------------------------------------
def r3_filter_ignores_limit():
    db = make_db()
    for i in range(1, 121):
        add(db, f"payload source {i:03d}", f"payload target {i:03d}")
    db.connection.commit()
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    dlg.browser_limit.setValue(500)  # Show: 500 — все 120 должны быть доступны
    run_filter(dlg, "payload")
    n = dlg.browser_table.rowCount()
    record("R3 filter ignores Show limit (hard FTS LIMIT 100)",
           True, n == 100, f"db has 120 matching entries, Show: 500, shown={n}")
    run_filter(dlg, "")
    n_plain = dlg.browser_table.rowCount()
    record("R3b unfiltered path obeys Show (120 <= 500 → all)",
           True, n_plain == 120, f"shown={n_plain}")
    dlg.close()
    close_db(db)
    return db


# ---------------------------------------------------------------------------
# R4/R5/R6/R7
# ---------------------------------------------------------------------------
def r4_search_in_absent():
    db = make_db()
    add(db, "alpha only in source", "beta only in target")
    db.connection.commit()
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    has_combo = hasattr(dlg, "browser_search_in")
    record("R4 no 'Search in' selector (filter always searches both columns)",
           True, not has_combo, "attribute browser_search_in missing on before-code")
    dlg.close()
    close_db(db)
    return db


def r5_truncation():
    db = make_db()
    long_source = ("The quick brown fox jumps over the lazy dog. " * 8).strip()  # 360+ символов
    long_target = "Целевой текст: " + ("быстрая бурая лиса прыгает через ленивого пса. " * 8)
    add(db, long_source, long_target)
    db.connection.commit()
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    it1 = dlg.browser_table.item(0, 1)
    it2 = dlg.browser_table.item(0, 2)
    src_len = len(it1.text())
    tgt_len = len(it2.text())
    truncated = src_len == 100 and tgt_len == 100 and src_len < len(long_source)
    tooltip_empty = not it1.toolTip()
    record("R5a Source/Target cells truncated to 100 chars", True, truncated,
           f"source cell len={src_len} (full={len(long_source)}), target cell len={tgt_len}")
    record("R5b no tooltip with full text", True, tooltip_empty,
           f"tooltip='{it1.toolTip()[:40]}'")
    dlg.close()
    close_db(db)
    return db


def r6_delete_key_dead():
    db = make_db()
    for i in range(1, 6):
        add(db, f"delkey source {i}", f"delkey target {i}")
    db.connection.commit()
    calls = []

    orig_question = QMessageBox.question
    orig_information = QMessageBox.information
    orig_warning = QMessageBox.warning
    orig_critical = QMessageBox.critical

    def fake_question(parent, title, text, *a, **k):
        calls.append(text)
        return QMessageBox.StandardButton.Yes

    QMessageBox.question = staticmethod(fake_question)
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)
    try:
        dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
        dlg.browser_table.selectRow(0)
        QTest.keyClick(dlg.browser_table, Qt.Key.Key_Delete)
        n_after = dlg.browser_table.rowCount()
        db.cursor.execute("SELECT COUNT(*) AS n FROM translation_units")
        n_db = db.cursor.fetchone()["n"]
        record("R6 Delete key does nothing (no handler, confirm never shown)",
               True, n_after == 5 and n_db == 5 and not calls,
               f"rows after={n_after}, db count={n_db}, confirm dialogs shown={len(calls)}")
        dlg.close()
    finally:
        QMessageBox.question = staticmethod(orig_question)
        QMessageBox.information = staticmethod(orig_information)
        QMessageBox.warning = staticmethod(orig_warning)
        QMessageBox.critical = staticmethod(orig_critical)
    close_db(db)
    return db


def r7_layout():
    db = make_db()
    add(db, "layout probe", "layout probe target")
    db.connection.commit()
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    # В ДО-коде в верхней строке: Filter, Show (spinbox), Refresh — определяем
    # по составу родительского layout спинбокса.
    spin_parent_is_filter_row = dlg.browser_limit.parentWidget() is dlg.browser_filter.parentWidget()
    record("R7 Show/Refresh sit in the SAME top row as Filter (target layout: they move to bottom panel)",
           True, spin_parent_is_filter_row,
           "before-code: browser_limit.parentWidget() == browser_filter.parentWidget()")
    dlg.close()
    close_db(db)
    return db


def main():
    print("=== BATCH TM2 recon «before» ===")
    r1_default_order()
    r2_filter_semantics()
    r3_filter_ignores_limit()
    r4_search_in_absent()
    r5_truncation()
    r6_delete_key_dead()
    r7_layout()
    print("\n=== summary ===")
    for name, expected, found in FINDINGS:
        mark = "OK" if found == expected else "UNEXPECTED"
        print(f"  [{mark}] {name} (expected_on_before={expected}, found={found})")
    unexpected = [n for n, e, f in FINDINGS if f != e]
    print(f"\ntotal findings: {len(FINDINGS)}, unexpected: {len(unexpected)}")
    if unexpected:
        for n in unexpected:
            print(f"  !! {n} did not reproduce — investigate before implementation")


if __name__ == "__main__":
    main()
