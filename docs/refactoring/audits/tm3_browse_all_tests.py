r"""
BATCH TM3 test suite — Browse All полировка (modules/tm_manager_qt.py).

Проверки (offscreen, изолированный SUPERVERTALER_DATA_ROOT, временная TM-база;
у каждого сценария своя БД):
  S1 высоты строк (T1–T4, задача 1): по тексту после первого show() и после
     resize окна БЕЗ Refresh (допуск ±2 px, эталон = тот же алгоритм, что у
     делегата: быстрый путь QFontMetrics для однострочного текста, иначе
     QTextDocument по ширине колонки минус PAD_X, плюс PAD_Y); замер
     заполнения 500 длинных строк < 1 c (порог TM2).
  S2 tooltip (T5–T7, задача 2): у Source/Target пуст; «Search in» сохранён.
  S3 подсветка (T8–T14, задача 3): match_ranges — подстрока, регистр,
     кириллица («пехот» → «Пехотная»), Whole words, режимы Search in;
     подсветки нет после Clear; делегат реально рисует (grab() с подсветкой
     отличается от без неё; в выделенной строке тоже); текст item не менялся.
  S4 галка Whole words (T15–T17, задача 4): grab() включённой отличается от
     выключенной в области индикатора; во включённом состоянии есть отметка
     (пиксели, отличные от заливки); и в светлой, и в тёмной теме.
  S5 Clear (T18–T20, задача 5): текст, Whole words (выкл.), Search in
     (Source and Target); «TM:» НЕ сбрасывается.
  S6 редактор ячейки (T21–T23, задача 6 — ОСТАНОВЛЕНО по промпту):
     состояние «до» не менялось — ячейки редактируемы, делегат НЕ создаёт
     QPlainTextEdit, правка не пишется в БД (= recon R3a/R3b).
  S7 текущая ячейка + Ctrl+C (T24–T28, задача 7): фон текущей ячейки темнее
     остальных ячеек выделенной строки; Ctrl+C копирует полный текст
     текущей ячейки (Source/Target/прочая колонка), на длинном тексте и на
     ячейке с подсветкой — без разметки.
  S8 свежесть (T29–T35, задача 8): удаление/импорт TM при видимой подвкладке
     — таблица совпадает с БД по (id, source, target) БЕЗ Refresh; при
     скрытой — dirty-флаг и перезагрузка при показе; фильтр и сортировка
     сохраняются; выделение сбрасывается; удалённая TM в «TM:» → All TMs.
  S9 список «TM:» (T36–T42, задача 9): пункты = All TMs + TM из БД (имя в
     подписи, tm_id в data); выбор сразу перезагружает таблицу (без Enter);
     записи = ровно выбранной TM по БД; лимит Show действует ПОСЛЕ
     TM-ограничения; удаление выбранной TM → All TMs; порядок строки фильтра
     TM: → Filter:; в scoped-режиме (tm_ids=) список скрыт.

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen TM3_PROFILE_DIR=<изолированный профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm3_browse_all_tests.py

Задача 6 ОСТАНОВЛЕНА (recon R3a/R3b: правка ячейки не пишется в БД) — S6
фиксирует это состояние, редактор не менялся.
"""

import os
import sys
import time

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM3_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(os.environ.get("TM3_STAGE_DIR", STAGE_ROOT), "tm3-suite-profile")

os.makedirs(PROFILE, exist_ok=True)
os.makedirs(os.path.join(PROFILE, "home"), exist_ok=True)
os.makedirs(os.path.join(PROFILE, "temp"), exist_ok=True)
os.makedirs(os.path.join(PROFILE, "workbench", "settings"), exist_ok=True)
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

faulthandler.dump_traceback_later(300, repeat=True)

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QTextDocument, QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox, QStyleOptionViewItem

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog, _BrowserCellDelegate
from modules.theme_manager import ThemeManager

app = QApplication.instance() or QApplication(sys.argv)

RESULTS = []
DB_SEQ = [0]


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))


def make_db():
    DB_SEQ[0] += 1
    db_path = os.path.join(PROFILE, f"tm3_suite_s{DB_SEQ[0]}.db")
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=lambda *a, **k: None)
    db.connect()
    return db


def close_db(db):
    try:
        db.connection.close()
    except Exception:
        pass


def add_tm(db, name, tm_id, source_lang="en", target_lang="nl"):
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES (?, ?, ?, ?)", (name, tm_id, source_lang, target_lang))
    db.connection.commit()


def add(db, source, target, tm_id="tma"):
    db.add_translation_unit(source=source, target=target,
                            source_lang="en", target_lang="nl", tm_id=tm_id)


def db_entries(db):
    db.cursor.execute(
        "SELECT id, source_text, target_text FROM translation_units ORDER BY id")
    return [(r["id"], r["source_text"], r["target_text"])
            for r in db.cursor.fetchall()]


def table_entries(table):
    out = []
    for r in range(table.rowCount()):
        id_item = table.item(r, 0)
        s_item = table.item(r, 1)
        t_item = table.item(r, 2)
        if id_item is None or s_item is None or t_item is None:
            continue
        out.append((int(id_item.data(Qt.ItemDataRole.UserRole) or id_item.text()),
                    s_item.text(), t_item.text()))
    return sorted(out, key=lambda e: e[0])


def pump(times=10):
    for _ in range(times):
        app.processEvents()


def wait_height_sync(dlg):
    """Дождаться дебаунса высот (100 мс) и его выполнения."""
    pump(3)
    deadline = time.time() + 2.0
    while dlg._height_timer.isActive() and time.time() < deadline:
        QTest.qWait(20)
    QTest.qWait(30)
    pump(3)


def expected_row_height(text, column_width, font):
    """Независимый эталон высоты: QTextDocument по ширине колонки минус
    PAD_X, плюс PAD_Y — тот же детерминированный алгоритм, что у
    _BrowserCellDelegate (QFontMetrics на безшрифтовой offscreen-платформе
    даёт отличную метрику строки, поэтому не используется)."""
    if not text:
        return 0
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setDefaultFont(font)
    doc.setPlainText(text)
    doc.setTextWidth(max(10, column_width - _BrowserCellDelegate.PAD_X))
    return int(doc.size().height()) + _BrowserCellDelegate.PAD_Y


def display_ids(table):
    """ID записей в ПОРЯДКЕ ОТОБРАЖЕНИЯ (не отсортированные)."""
    return [int(table.item(r, 0).data(Qt.ItemDataRole.UserRole))
            for r in range(table.rowCount())]


def indicator_region(widget):
    opt = QStyleOptionButton_stub = QStyleOptionViewItem()
    from PyQt6.QtWidgets import QStyleOptionButton
    opt = QStyleOptionButton()
    widget.initStyleOption(opt)
    return widget.style().subElementRect(
        widget.style().SubElement.SE_CheckBoxIndicator, opt, widget)


def minority_pixels(image, rect, shrink=3):
    """Число пикселей внутренней области индикатора, отличных от
    доминирующего цвета (заливки). Отметка ✓ = меньшинство."""
    x0, x1 = rect.left() + shrink, rect.right() - shrink
    y0, y1 = rect.top() + shrink, rect.bottom() - shrink
    counts = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = image.pixelColor(x, y).name()
            counts[c] = counts.get(c, 0) + 1
    dominant = max(counts, key=counts.get)
    return sum(v for k, v in counts.items() if k != dominant), dominant


def differing_pixel_count(img1, img2):
    if img1.size() != img2.size():
        return -1
    diff = 0
    for y in range(img1.height()):
        for x in range(img1.width()):
            if img1.pixel(x, y) != img2.pixel(x, y):
                diff += 1
    return diff


# ============================================================
# S1 высоты строк (задача 1)
# ============================================================

def s1_heights():
    print("--- S1 высоты строк (задача 1) ---")
    db = make_db()
    add_tm(db, "TM3 suite TM", "tma")
    add(db, " ".join(["infantry"] * 40), " ".join(["пехотная"] * 40))
    add(db, "short source", "короткий перевод")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table

    dlg.show()
    dlg.resize(1000, 600)
    # Ждём дебаунс высот (100 мс): пересчёт при показе идёт через
    # single-shot QTimer, tight processEvents его не запускает.
    wait_height_sync(dlg)

    ok = True
    details = []
    view_font = table.font()
    for r in range(table.rowCount()):
        for col, item in ((1, table.item(r, 1)), (2, table.item(r, 2))):
            colw = table.columnWidth(col)
            exp = expected_row_height(item.text(), colw, view_font)
            diff = abs(table.rowHeight(r) - exp)
            ok = ok and diff <= 2
            if diff > 2:
                details.append(f"r{r}c{col}: {table.rowHeight(r)} vs {exp}")
    check("T1 после первого show() высоты строк по тексту (±2 px), без Refresh",
          ok, "; ".join(details) or "все строки в допуске")

    dlg.resize(1700, 600)
    pump()
    wait_height_sync(dlg)
    ok = True
    details = []
    for r in range(table.rowCount()):
        for col, item in ((1, table.item(r, 1)), (2, table.item(r, 2))):
            colw = table.columnWidth(col)
            exp = expected_row_height(item.text(), colw, view_font)
            diff = abs(table.rowHeight(r) - exp)
            ok = ok and diff <= 2
            if diff > 2:
                details.append(f"r{r}c{col}: {table.rowHeight(r)} vs {exp}")
    check("T2 после resize окна высоты пересчитаны (±2 px), без Refresh",
          ok, "; ".join(details) or "все строки в допуске")

    # Скрытая вкладка + refresh → показ: высоты пересчитываются при показе
    # (recon R1a: до батча оставались замороженными).
    dlg.hide()
    dlg.browser_filter.setText("short")
    dlg.refresh_browser()
    dlg.show()
    wait_height_sync(dlg)
    item = table.item(0, 1)
    exp = expected_row_height(item.text(), table.columnWidth(1), view_font)
    check("T3 refresh на скрытой вкладке → при показе высота по тексту",
          abs(table.rowHeight(0) - exp) <= 2,
          f"row0 {table.rowHeight(0)}px vs эталон {exp}px")
    dlg.browser_filter.clear()
    dlg.refresh_browser()

    # BATCH TM3.1, задача 1: отрисовка согласована с расчётом — протяжённость
    # чернил в ячейке без фильтра совпадает с фильтром (единый путь
    # QTextDocument; до TM3.1 без фильтра рисовалась ОДНА строка drawText'ом,
    # а высота считалась многострочной — recon S1/R1a).
    from PyQt6.QtGui import QColor, QImage

    def _ink_extent(tbl, it):
        img = tbl.viewport().grab().toImage().convertToFormat(
            QImage.Format.Format_RGB32)
        rect = tbl.visualItemRect(it)
        x0, x1 = max(rect.left(), 0), min(rect.right(), img.width() - 1)
        y0, y1 = max(rect.top(), 0), min(rect.bottom(), img.height() - 1)
        counts = {}
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                nm = img.pixelColor(xx, yy).name()
                counts[nm] = counts.get(nm, 0) + 1
        bg = QColor(max(counts, key=counts.get))
        rows = []
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                c = img.pixelColor(xx, yy)
                if (abs(c.red() - bg.red()) + abs(c.green() - bg.green())
                        + abs(c.blue() - bg.blue())) > 70:
                    rows.append(yy)
                    break
        return (max(rows) - min(rows) + 1) if rows else 0

    ext_nofilter = _ink_extent(table, table.item(0, 1))
    dlg.browser_filter.setText("infantry")
    dlg.refresh_browser()
    pump()
    ext_filter = _ink_extent(table, table.item(0, 1))
    dlg.browser_filter.clear()
    dlg.refresh_browser()
    check("T3.1 (TM3.1) отрисовка без фильтра занимает столько же строк "
          "по вертикали, сколько с фильтром (единый путь)",
          ext_nofilter > 0 and abs(ext_nofilter - ext_filter) <= max(4, ext_filter // 4),
          f"чернила без фильтра {ext_nofilter}px, с фильтром {ext_filter}px")

    # T4 (M): заполнение 500 длинных строк < 1 c (порог BATCH TM2).
    for i in range(500):
        add(db, f"entry {i} " + "translation " * 150,
            f"перевод {i} " + "перевод " * 150)
    t0 = time.perf_counter()
    dlg.refresh_browser()
    elapsed = time.perf_counter() - t0
    check("T4 (M) заполнение 500 длинных строк < 1 c", elapsed < 1.0,
          f"{elapsed:.3f} c, rows={table.rowCount()}")
    dlg.hide()
    close_db(db)


# ============================================================
# S2 tooltip (задача 2)
# ============================================================

def s2_tooltips():
    print("--- S2 tooltip (задача 2) ---")
    db = make_db()
    add_tm(db, "TM3 suite TM", "tma")
    add(db, "tooltip source " * 20, "tooltip target " * 20)
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table
    check("T5 tooltip у Source пуст", table.item(0, 1).toolTip() == "",
          repr(table.item(0, 1).toolTip()[:30]))
    check("T6 tooltip у Target пуст", table.item(0, 2).toolTip() == "",
          repr(table.item(0, 2).toolTip()[:30]))
    check("T7 tooltip «Search in» сохранён",
          dlg.browser_search_in.toolTip() != "")
    dlg.hide()
    close_db(db)


# ============================================================
# S3 подсветка (задача 3)
# ============================================================

def s3_highlight():
    print("--- S3 подсветка (задача 3) ---")
    mr = _BrowserCellDelegate.match_ranges

    check("T8 match_ranges: подстрока по оригиналу, регистр игнорируется",
          mr("Infantry division", "infantry", False) == [(0, 8)]
          and mr("Infantry division", "INFANTRY", False) == [(0, 8)])
    check("T9 match_ranges: кириллица («пехот» → «Пехотная»)",
          mr("Пехотная дивизия", "пехот", False) == [(0, 5)])
    check("T10 match_ranges: несколько совпадений",
          mr("аб аб аб", "аб", False) == [(0, 2), (3, 5), (6, 8)])
    check("T11 match_ranges: Whole words — не внутри слова",
          mr("division infantry div", "div", True) == [(18, 21)]
          and mr("division infantry div", "div", False) == [(0, 3), (18, 21)])
    check("T12 match_ranges: пустые входы",
          mr("", "x", False) == [] and mr("text", "", False) == [])

    db = make_db()
    add_tm(db, "TM3 suite TM", "tma")
    add(db, "Пехотная дивизия перешла реку", "infantry division crossed")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    dlg.show()
    dlg.resize(1000, 500)
    pump()

    # Search in: Source only → Target-колонка не подсвечивается
    dlg.browser_search_in.setCurrentIndex(1)  # Source only
    dlg.browser_filter.setText("division")
    dlg.refresh_browser()
    check("T13 режим Search in: вне режима подсветки нет",
          dlg._source_delegate._term == "division"
          and dlg._target_delegate._term == "division"
          and dlg._target_delegate._enabled is False
          and dlg._source_delegate._enabled is True)

    dlg.browser_search_in.setCurrentIndex(0)  # Source and Target
    dlg.refresh_browser()
    item_before = table_text = dlg.browser_table.item(0, 1).text()

    table = dlg.browser_table
    rect = table.visualItemRect(table.item(0, 1))
    vp = table.viewport().grab().toImage()
    # убрать подсветку без изменения данных
    dlg._source_delegate.set_highlight("")
    dlg._target_delegate.set_highlight("")
    table.viewport().update()
    pump()
    vp2 = table.viewport().grab().toImage()
    diff = differing_pixel_count(vp, vp2)
    check("T14 делегат реально рисует подсветку (grab отличается, item не менялся)",
          diff > 20 and table_text == "Пехотная дивизия перешла реку",
          f"{diff} пикселей различий; item.text() без изменений")

    # Clear → подсветки нет
    dlg.browser_filter.setText("division")
    dlg.refresh_browser()
    dlg.clear_browser_filter()
    check("T15 после Clear подсветки нет",
          dlg._source_delegate._term == "" and dlg._target_delegate._term == "")
    dlg.hide()
    close_db(db)


# ============================================================
# S4 галка Whole words (задача 4)
# ============================================================

def s4_checkbox():
    print("--- S4 галка Whole words (задача 4) ---")
    from modules.styled_widgets import CheckmarkCheckBox
    box = CheckmarkCheckBox("Whole words")
    box.show()
    pump()
    box.setChecked(False)
    pump()
    img_off = box.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    rect = indicator_region(box)
    box.setChecked(True)
    pump()
    img_on = box.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    on_minority, fill = minority_pixels(img_on, rect)
    off_minority, _ = minority_pixels(img_off, rect)
    diff = differing_pixel_count(
        img_on.copy(rect), img_off.copy(rect))
    check("T15 grab() включённой отличается от выключенной в области индикатора",
          diff > 10, f"{diff} пикселей различий, заливка {fill}")
    check("T16 во включённом состоянии есть отметка ✓",
          on_minority >= 5 and off_minority <= 2,
          f"checked: {on_minority} пикселей-«меньшинства», unchecked: {off_minority}")

    # Тёмная тема
    theme = ThemeManager(user_data_path=__import__("pathlib").Path(PROFILE))
    theme.current_theme = theme.get_theme("Dark")
    theme.apply_theme(app)
    box.setChecked(False)
    pump()
    dark_off = box.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    box.setChecked(True)
    pump()
    dark_on = box.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    dark_minority, dark_fill = minority_pixels(dark_on, rect)
    dark_diff = differing_pixel_count(dark_on.copy(rect), dark_off.copy(rect))
    check("T17 тёмная тема: включённая отличается и содержит отметку",
          dark_diff > 10 and dark_minority >= 5,
          f"{dark_diff} пикселей различий, {dark_minority} пикселей отметки, "
          f"заливка {dark_fill}")
    # вернуть светлую тему остальным сценариям
    theme.current_theme = theme.get_theme("Light (Default)")
    theme.apply_theme(app)
    box.hide()


# ============================================================
# S5 Clear (задача 5)
# ============================================================

def s5_clear():
    print("--- S5 Clear (задача 5) ---")
    db = make_db()
    add_tm(db, "TM A", "tma")
    add_tm(db, "TM B", "tmb")
    add(db, "alpha source", "alpha target", tm_id="tma")
    add(db, "beta source", "beta target", tm_id="tmb")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    dlg.show()
    pump()
    dlg.browser_tm_combo.setCurrentIndex(1)  # TM A
    dlg.browser_filter.setText("alpha")
    dlg.browser_whole_words.setChecked(True)
    dlg.browser_search_in.setCurrentIndex(2)  # Target only
    dlg.refresh_browser()
    check("T18 предусловие: фильтр сужает до 1 записи",
          dlg.browser_table.rowCount() == 1,
          f"rows={dlg.browser_table.rowCount()}")
    dlg.clear_browser_filter()
    check("T19 Clear сбрасывает текст, Whole words, Search in",
          dlg.browser_filter.text() == ""
          and dlg.browser_whole_words.isChecked() is False
          and dlg.browser_search_in.currentIndex() == 0)
    check("T20 Clear НЕ сбрасывает список «TM:» и перезагружает без фильтра",
          dlg.browser_tm_combo.currentData() == "tma"
          and dlg.browser_table.rowCount() == 1)
    dlg.hide()
    close_db(db)


# ============================================================
# S6 редактор ячейки (задача 6 — ОСТАНОВЛЕНО)
# ============================================================

def s6_editor_stop():
    print("--- S6 редактор (задача 6 ОСТАНОВЛЕНО; BATCH TM3.1 задача 5: "
          "ячейки read-only) ---")
    db = make_db()
    add_tm(db, "TM3 suite TM", "tma")
    add(db, "editable source text", "editable target text")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table
    # BATCH TM3.1, задача 5 (намеренное изменение): ячейки только для
    # чтения — правки остаются в Edit/Maintain TM, записи в БД из таблицы
    # не делаются.
    check("T21 BATCH TM3.1: ячейки без ItemIsEditable (read-only)",
          not bool(table.item(0, 1).flags() & Qt.ItemFlag.ItemIsEditable))
    editor = table.itemDelegateForColumn(1).createEditor(
        table, QStyleOptionViewItem(), table.model().index(0, 1))
    check("T22 делегат НЕ создаёт QPlainTextEdit (задача 6 снята)",
          editor is not None and editor.__class__.__name__ != "QPlainTextEdit",
          f"editor class: {editor.__class__.__name__}")
    editor.deleteLater()

    item = table.item(0, 1)
    item.setText("EDITED-NOT-SAVED")
    db.cursor.execute("SELECT source_text FROM translation_units WHERE id=1")
    db_text = db.cursor.fetchone()[0]
    check("T23 правка НЕ пишется в БД (= recon R3b)",
          item.text() == "EDITED-NOT-SAVED" and db_text == "editable source text",
          f"БД: {db_text!r}")
    dlg.hide()
    close_db(db)


# ============================================================
# S7 текущая ячейка + Ctrl+C (задача 7)
# ============================================================

def s7_current_cell():
    print("--- S7 текущая ячейка + Ctrl+C (задача 7) ---")
    db = make_db()
    add_tm(db, "TM3 suite TM", "tma")
    long_src = "long source text " * 40
    add(db, long_src, "target A")
    add(db, "row B source", "target B")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    dlg.show()
    dlg.resize(1000, 500)
    pump()
    table = dlg.browser_table

    table.selectRow(0)
    table.setCurrentCell(0, 1)
    pump()
    vp = table.viewport().grab().toImage()
    r1 = table.visualItemRect(table.item(0, 1))
    r2 = table.visualItemRect(table.item(0, 2))
    # угол ячейки без текста (padding-зона)
    c1 = vp.pixelColor(r1.right() - 3, r1.top() + 2)
    c2 = vp.pixelColor(r2.right() - 3, r2.top() + 2)
    lum1 = 0.299 * c1.red() + 0.587 * c1.green() + 0.114 * c1.blue()
    lum2 = 0.299 * c2.red() + 0.587 * c2.green() + 0.114 * c2.blue()
    check("T24 текущая ячейка темнее остальных в выделенной строке",
          c1 != c2 and lum1 < lum2,
          f"current rgb {c1.name()} (lum {lum1:.0f}) vs сосед {c2.name()} "
          f"(lum {lum2:.0f})")

    clip = QApplication.clipboard()
    clip.clear()
    QTest.keyClick(table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    pump()
    check("T25 клик Source + Ctrl+C = полный текст Source",
          clip.text() == long_src,
          f"clipboard len={len(clip.text())}, expected {len(long_src)}")

    table.setCurrentCell(0, 2)
    clip.clear()
    QTest.keyClick(table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    pump()
    check("T26 клик Target + Ctrl+C = текст Target",
          clip.text() == "target A", repr(clip.text()[:40]))

    table.setCurrentCell(0, 3)  # колонка TM
    clip.clear()
    QTest.keyClick(table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    pump()
    check("T27 прочая колонка: Ctrl+C = её текст",
          clip.text() == "tma", repr(clip.text()[:40]))

    # Ctrl+C на ячейке с подсветкой — буфер без разметки
    dlg.browser_filter.setText("target")
    dlg.refresh_browser()
    table.selectRow(0)
    table.setCurrentCell(0, 2)
    clip.clear()
    QTest.keyClick(table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    pump()
    check("T28 Ctrl+C на подсвеченной ячейке — без разметки",
          clip.text() == "target A" and "<span" not in clip.text(),
          repr(clip.text()[:60]))
    dlg.browser_filter.clear()
    dlg.refresh_browser()
    dlg.hide()
    close_db(db)


# ============================================================
# S8 свежесть (задача 8)
# ============================================================

def s8_freshness():
    print("--- S8 свежесть (задача 8) ---")
    # (а) видима: удаление TM → таблица совпадает с БД без Refresh
    db = make_db()
    add_tm(db, "TM A", "tma")
    add_tm(db, "TM B", "tmb")
    add(db, "keep A1", "держать A1", tm_id="tma")
    add(db, "gone B1", "удалить B1", tm_id="tmb")
    add(db, "gone B2", "удалить B2", tm_id="tmb")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    dlg.show()
    dlg.resize(1000, 500)
    pump()
    check("T29 предусловие: 3 записи до удаления TM",
          table_entries(dlg.browser_table) ==
          sorted(db_entries(db), key=lambda e: e[0]))
    db.cursor.execute("DELETE FROM translation_units WHERE tm_id='tmb'")
    db.cursor.execute("DELETE FROM translation_memories WHERE tm_id='tmb'")
    db.connection.commit()
    dlg.on_tm_list_changed()
    pump()
    ok_rows = (table_entries(dlg.browser_table) ==
               sorted(db_entries(db), key=lambda e: e[0])
               and dlg.browser_table.rowCount() == 1)
    ok_combo = all(
        dlg.browser_tm_combo.itemData(i) != "tmb"
        for i in range(dlg.browser_tm_combo.count()))
    check("T30 видимая: удаление TM → таблица = БД и «TM:» без tmb (без Refresh)",
          ok_rows and ok_combo,
          f"rows={dlg.browser_table.rowCount()}, texts={table_entries(dlg.browser_table)}")

    # (а) видима: импорт TM → записи появляются
    add_tm(db, "TM C", "tmc")
    add(db, "new C1", "новый C1", tm_id="tmc")
    add(db, "new C2", "новый C2", tm_id="tmc")
    db.connection.commit()
    dlg.on_tm_list_changed()
    pump()
    check("T31 видимая: импорт TM → записи и «TM:» обновились без Refresh",
          table_entries(dlg.browser_table) ==
          sorted(db_entries(db), key=lambda e: e[0])
          and dlg.browser_tm_combo.findData("tmc") >= 0)

    # (б) скрыта: dirty-флаг и перезагрузка при показе, фильтр/сортировка
    dlg.browser_filter.setText("new C")
    dlg.refresh_browser()
    check("T32 предусловие: фильтр показывает 2 записи",
          dlg.browser_table.rowCount() == 2,
          f"rows={dlg.browser_table.rowCount()}")
    dlg.browser_table.horizontalHeader().setSortIndicator(
        0, Qt.SortOrder.DescendingOrder)
    pump()
    dlg.hide()
    add(db, "new C3", "новый C3", tm_id="tmc")
    db.connection.commit()
    dlg.on_tm_list_changed()  # BATCH TM3.1: скрытая — перезагрузка при показе
    check("T33 скрытая: перезагрузки нет (данные до показа не изменились)",
          dlg.browser_table.rowCount() == 2,
          f"rows={dlg.browser_table.rowCount()}")
    dlg.show()
    pump()
    ids = display_ids(dlg.browser_table)
    check("T34 показ: перезагрузка (всегда — TM3.1 задача 4), фильтр "
          "сохранён, сортировка ID desc",
          dlg.browser_table.rowCount() == 3 and ids == sorted(ids, reverse=True),
          f"ids (порядок отображения)={ids}")
    dlg.browser_filter.clear()
    dlg.refresh_browser()

    # выделение сбрасывается
    dlg.browser_table.selectRow(0)
    check("T35 предусловие: есть выделение",
          bool(dlg.browser_table.selectedIndexes()))
    add(db, "new C4", "новый C4", tm_id="tmc")
    db.connection.commit()
    dlg.on_tm_list_changed()
    pump()
    check("T35 перезагрузка сбрасывает выделение",
          not dlg.browser_table.selectedIndexes()
          and dlg.browser_table.rowCount() == 5,
          f"selected={len(dlg.browser_table.selectedIndexes())}, "
          f"rows={dlg.browser_table.rowCount()}")
    dlg.hide()
    close_db(db)


# ============================================================
# S9 список «TM:» (задача 9)
# ============================================================

def s9_tm_combo():
    print("--- S9 список «TM:» (задача 9) ---")
    db = make_db()
    add_tm(db, "TM B", "tmb")
    add_tm(db, "TM A", "tma")
    for i in range(10):
        add(db, f"alpha {i}", f"альфа {i}", tm_id="tma")
    for i in range(150):
        add(db, f"beta {i}", f"бета {i}", tm_id="tmb")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    dlg.show()
    dlg.resize(1000, 500)
    pump()
    combo = dlg.browser_tm_combo
    check("T36 пункты = All TMs + TM из БД (подпись — имя, ключ — tm_id)",
          combo.count() == 3
          and [combo.itemText(i) for i in range(combo.count())]
          == ["All TMs", "TM A", "TM B"]
          and [combo.itemData(i) for i in range(combo.count())]
          == [None, "tma", "tmb"])
    check("T37 по умолчанию All TMs — все записи",
          combo.currentData() is None
          and dlg.browser_table.rowCount() == 160)

    # Выбор TM: без Enter, записи = ровно выбранной TM
    combo.setCurrentIndex(1)  # tma
    pump()
    rows = table_entries(dlg.browser_table)
    db_tma = [(i, s, t) for (i, s, t) in db_entries(db) if s.startswith("alpha")]
    check("T38 выбор TM сразу перезагружает (без Enter): ровно записи этой TM",
          len(rows) == 10 and all(s.startswith("alpha") for _, s, _ in rows)
          and rows == sorted(db_tma, key=lambda e: e[0]),
          f"rows={len(rows)}")

    # Лимит Show действует ПОСЛЕ TM-ограничения
    dlg.browser_limit.setValue(100)
    combo.setCurrentIndex(2)  # tmb (150 записей)
    pump()
    rows = table_entries(dlg.browser_table)
    tm_col_ok = all(
        dlg.browser_table.item(r, 3).text() == "tmb"
        for r in range(dlg.browser_table.rowCount()))
    check("T39 лимит Show после TM-ограничения: 100 записей TM B",
          dlg.browser_table.rowCount() == 100
          and tm_col_ok
          and all(row[1].startswith("beta") for row in rows),
          f"rows={dlg.browser_table.rowCount()}")
    dlg.browser_limit.setValue(500)

    # Порядок верхней строки: TM: → Filter:
    lay = dlg.browser_tab.layout().itemAt(0).layout()
    texts = []
    for i in range(lay.count()):
        w = lay.itemAt(i).widget()
        if w is not None:
            texts.append(w.text() if hasattr(w, "text") else "")
    check("T40 строка фильтра: «TM:» перед «Filter:»",
          "TM:" in texts and "Filter:" in texts
          and texts.index("TM:") < texts.index("Filter:"), f"{texts}")

    # Удаление выбранной TM → All TMs
    combo.setCurrentIndex(1)  # tma выбрана
    pump()
    db.cursor.execute("DELETE FROM translation_units WHERE tm_id='tma'")
    db.cursor.execute("DELETE FROM translation_memories WHERE tm_id='tma'")
    db.connection.commit()
    dlg.on_tm_list_changed()
    pump()
    rows = table_entries(dlg.browser_table)
    check("T41 удаление выбранной TM → All TMs и все записи",
          combo.currentData() is None and combo.itemText(0) == "All TMs"
          and len(rows) == 150,
          f"current={combo.currentData()}, rows={len(rows)}")

    # Scoped-режим (TMEditorDialog): список скрыт, ограничение tm_ids работает
    dlg2 = TMManagerDialog(None, db, log_callback=lambda m: None, tm_ids=["tmb"])
    check("T42 scoped-режим: «TM:» скрыт, ограничение tm_ids",
          dlg2.browser_tm_combo.isHidden()
          and dlg2._browser_tm_constraint() == ["tmb"]
          and dlg2.browser_table.rowCount() == 150,
          f"hidden={dlg2.browser_tm_combo.isHidden()}, "
          f"rows={dlg2.browser_table.rowCount()}")
    dlg2.hide()
    dlg.hide()
    close_db(db)


def main():
    s1_heights()
    s2_tooltips()
    s3_highlight()
    s4_checkbox()
    s5_clear()
    s6_editor_stop()
    s7_current_cell()
    s8_freshness()
    s9_tm_combo()

    passed = sum(1 for _, ok in RESULTS if ok)
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\nTOTAL: {passed}/{len(RESULTS)} PASS")
    if failed:
        print("FAILED:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
