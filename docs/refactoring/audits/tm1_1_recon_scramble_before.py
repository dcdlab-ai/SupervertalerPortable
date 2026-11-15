r"""
BATCH TM1.1 recon test (commit 1) — «до»-воспроизведение бага рассинхрона
таблицы Browse All (modules/tm_manager_qt.py, TMManagerDialog.refresh_browser).

Симптом от ручного теста TM1 (Дмитрий, 2026-11-15): в TM Browser -> Browse All
ID в таблице не соответствует тексту строки (дубли ID, ID одной записи меняется
между обновлениями), а после «Delete Selected» исчезают не те записи, что
выделены. Причина: setSortingEnabled(True) включён ВО ВРЕМЯ заполнения таблицы.
Пока индикатор сортировки невалиден (свежее окно), пересортировки при заполнении
нет и таблица целостна; но после клика пользователя по заголовку (валидный
индикатор) КАЖДЫЙ setItem() во время refresh_browser() вызывает пересортировку,
строки уезжают на лету, ячейки одной записи расходятся по разным строкам.

Тест (N = 30 записей с уникальными source/target):
  A0. Свежее окно без пользовательской сортировки: базовая целостность
      (контроль — здесь всё должно быть хорошо и на «до»-коде).
  A1. Пользователь отсортировал по колонке ID (клик по заголовку) и нажал
      Refresh: для каждой строки ID из колонки 0 должен соответствовать
      source/target записи в БД; дублей ID и пустых ячеек быть не должно.
      (Сортировка по ID — худший случай: 24 из 30 строк получают чужой текст,
      удаление по колонке ID забирает не те записи, что показаны.)
  B.  Удаление на отсортированной таблице: выделяем конкретные строки (как
      Ctrl+клик), запоминаем ИМЕННО то, что показано в выделенных строках
      (source), удаляем, сверяем с БД: исчезнуть должны записи с показанными
      source и только они.

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen SUPERVERTALER_DATA_ROOT=<изолированный профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm1_1_recon_scramble_before.py

Тест не трогает реальные TM-базы: БД создаётся в изолированном каталоге.
На «до»-коде тест ПАДАЕТ (фиксирует рассинхрон); после исправления — проходит.
"""

import os
import sys

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM1_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(os.environ.get("TM1_STAGE_DIR", STAGE_ROOT), "tm1_1-recon-profile")

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

from PyQt6.QtCore import QItemSelectionModel, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog

N_ENTRIES = 30
DB_A = os.path.join(PROFILE, "tm1_1_recon_a.db")
DB_B = os.path.join(PROFILE, "tm1_1_recon_b.db")


def build_db(db_path):
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=lambda *a, **k: None)
    db.connect()
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM1.1 recon TM', 'tm11recon', 'en', 'nl')"
    )
    db.connection.commit()
    for i in range(1, N_ENTRIES + 1):
        db.add_translation_unit(
            source=f"unique-src-{i:03d} payload",
            target=f"unique-tgt-{i:03d} payload",
            source_lang="en",
            target_lang="nl",
            tm_id="tm11recon",
        )
    db.connection.commit()
    return db


def db_sources(db):
    db.cursor.execute("SELECT id, source_text FROM translation_units")
    return {r["source_text"]: r["id"] for r in db.cursor.fetchall()}


def monkeypatch_boxes():
    """QDialog-модалки никогда не закрываются offscreen — подменяем."""
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)


def check_population(dlg, source_to_id):
    """Для каждой показанной строки ID из колонки 0 должен соответствовать
    source/target записи в БД (source -> id)."""
    table = dlg.browser_table
    n_rows = table.rowCount()
    mismatch = []
    empty_cells = 0
    ids_seen = []
    for row in range(n_rows):
        it_id = table.item(row, 0)
        it_src = table.item(row, 1)
        it_tgt = table.item(row, 2)
        for it in (it_id, it_src, it_tgt):
            if it is None or not it.text().strip():
                empty_cells += 1
        if it_id is None or not it_id.text().strip():
            mismatch.append((row, "<no id>", it_src.text() if it_src else "<none>"))
            continue
        entry_id = int(it_id.text())
        ids_seen.append(entry_id)
        want_src = it_src.text() if it_src else ""
        if source_to_id.get(want_src) != entry_id:
            mismatch.append(
                (row, entry_id, f"src='{want_src}' -> id {source_to_id.get(want_src)} in db")
            )
        if it_tgt is None or not it_tgt.text().strip():
            mismatch.append((row, entry_id, "empty Target cell"))
    dup = len(ids_seen) - len(set(ids_seen))
    return n_rows, mismatch, dup, empty_cells


def close_db(db):
    try:
        db.connection.close()
    except Exception:
        pass


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    monkeypatch_boxes()

    # --- A0/A1. целостность заполнения ---------------------------------------
    db = build_db(DB_A)
    sources_before = db_sources(db)
    dlg = TMManagerDialog(None, db, log_callback=lambda msg: None)
    table = dlg.browser_table
    hdr = table.horizontalHeader()
    print(f"entries in db: {len(sources_before)}")
    print(
        f"default sort indicator: section={hdr.sortIndicatorSection()} "
        f"order={hdr.sortIndicatorOrder()}"
    )

    n0, mis0, dup0, empty0 = check_population(dlg, sources_before)
    print(f"[A0 fresh window] rows={n0} mismatches={len(mis0)} dup_ids={dup0} empty_cells={empty0}")

    # пользователь кликает по заголовку ID (asc), затем Refresh
    table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    dlg.refresh_browser()
    n1, mis1, dup1, empty1 = check_population(dlg, sources_before)
    print(f"[A1 after header-sort + Refresh] rows={n1} mismatches={len(mis1)} dup_ids={dup1} empty_cells={empty1}")
    for row, eid, info in mis1[:8]:
        print(f"    row {row}: id={eid} {info}")
    if len(mis1) > 8:
        print(f"    ... and {len(mis1) - 8} more")
    print(f"[A1] status label: '{dlg.browser_status.text()}'")

    # повторный Refresh — «ID одной и той же записи меняется между обновлениями»
    dlg.refresh_browser()
    n2, mis2, dup2, empty2 = check_population(dlg, sources_before)
    print(f"[A1 second Refresh] rows={n2} mismatches={len(mis2)} dup_ids={dup2} empty_cells={empty2}")
    dlg.close()
    close_db(db)

    # --- B. удаление выделенных строк на отсортированной таблице --------------
    db2 = build_db(DB_B)
    dlg2 = TMManagerDialog(None, db2, log_callback=lambda msg: None)
    table2 = dlg2.browser_table
    # как в ручном тесте: пользователь отсортировал по ID и обновил
    table2.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    dlg2.refresh_browser()
    pick_rows = [0, 3, 7]
    model = table2.model()
    table2.clearSelection()
    for r in pick_rows:
        table2.selectionModel().select(
            model.index(r, 0),
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
    shown_sources = []
    for r in pick_rows:
        it = table2.item(r, 1)
        shown_sources.append(it.text() if it else "<no cell>")
    before = db_sources(db2)
    dlg2.delete_selected_entry()
    after = db_sources(db2)
    deleted = set(before) - set(after)
    expected = set(s for s in shown_sources if s in before)
    ok_b = deleted == expected and len(after) == N_ENTRIES - len(expected)
    print(f"[B] selected display rows: {pick_rows}")
    print(f"[B] sources shown in selected rows: {shown_sources}")
    print(f"[B] deleted from db: {len(deleted)} entries: {sorted(deleted)}")
    print(f"[B] expected from shown rows: {len(expected)} entries: {sorted(expected)}")
    print(f"[B] remaining entries in db: {len(after)} (expected {N_ENTRIES - len(expected)})")
    dlg2.close()
    close_db(db2)

    ok_a = (
        n0 == N_ENTRIES and not mis0 and dup0 == 0 and empty0 == 0
        and n1 == N_ENTRIES and not mis1 and dup1 == 0 and empty1 == 0
        and n2 == N_ENTRIES and not mis2 and dup2 == 0 and empty2 == 0
    )
    ok = ok_a and ok_b
    print()
    if ok:
        print("RESULT: OK — таблица целостна после сортировки+Refresh, удаляются именно выделенные записи")
    else:
        print(
            f"RESULT: BUG REPRODUCED — рассинхрон строк: A0 mismatches={len(mis0)}, "
            f"A1 mismatches={len(mis1)} (dup_ids={dup1}, empty={empty1}); "
            f"удаление по выделенным строкам корректно: {ok_b}"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
