# -*- coding: utf-8 -*-
r"""
BATCH TM3.1 suite — тесты ОТРИСОВКИ, КОНТРАСТА, ПРОВОДКИ и read-only
поведения Browse All (modules/tm_manager_qt.py) поверх батчей TM2/TM3.

Ключевое отличие от tm3_browse_all_tests.py: проверяется фактическая
отрисовка (grab() по пикселям на платформе с реальными шрифтами) и
проводка свежести, а не только расчёты высот.

Секции:
  S1 отрисовка (задача 1): без фильтра/с фильтром/после resize — число
     реально отрисованных строк текста в ячейке == числу строк переноса
     (QTextLayout); высота строки == высоте документа + PAD.
  S2 контраст (задача 2): WCAG >= 4.5:1 по реальным пикселям в состояниях
     обычная / чередующаяся / выделенная строка / текущая ячейка
     выделенной строки, светлая и тёмная тема; подсвеченный фрагмент —
     тёмный текст на #FFD54F.
  S3 немедленное применение «Search in»/«Whole words» (задача 3),
     включая заглавные: «Пехотная», «ПЕХОТНАЯ» при запросе «пехот».
  S4 проводка свежести (задача 4): показ всегда перезагружает (по логу
     "reloaded on show"), refresh_browser пересобирает «TM:», выбор TM
     сохраняется / несуществующая -> All TMs; монолит — AST-проверки
     единой точки (реальный полный путь — recon R4, см. отчёт).
  S5 read-only (задача 5): флаги без ItemIsEditable, NoEditTriggers,
     двойной клик не открывает редактор; сортировка кликом работает.

Запуск (из репозитория E:\Dev\SupervertalerPortable) — платформа
«windows» с реальными шрифтами, окна за пределами экрана:
  TM31_PROFILE_DIR=<изолированный профиль> TM31_STAGE_DIR=<stage>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm31_browse_all_tests.py

Код выхода 1 при любом FAIL.
"""

import ast
import os
import re
import sys

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM31_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(
        os.environ.get("TM31_STAGE_DIR", STAGE_ROOT), "tm31-suite-profile")
EVIDENCE_DIR = os.path.join(
    os.environ.get("TM31_STAGE_DIR", STAGE_ROOT), "evidence")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO)

# Одноразовый изолированный профиль (тема прошлых прогонов не должна
# попадать в текущий: ThemeManager хранит выбранную тему в themes.json).
import shutil
if os.path.isdir(PROFILE):
    shutil.rmtree(PROFILE)
os.makedirs(PROFILE, exist_ok=True)
os.makedirs(os.path.join(PROFILE, "home"), exist_ok=True)
os.makedirs(os.path.join(PROFILE, "temp"), exist_ok=True)
os.makedirs(os.path.join(PROFILE, "workbench", "settings"), exist_ok=True)
os.environ["SUPERVERTALER_DATA_ROOT"] = PROFILE
_home = os.path.join(PROFILE, "home")
os.environ["USERPROFILE"] = _home
os.environ["HOME"] = _home
os.environ["APPDATA"] = _home
os.environ["LOCALAPPDATA"] = _home
os.environ["TEMP"] = os.path.join(PROFILE, "temp")
os.environ["TMP"] = os.environ["TEMP"]
# Платформа с РЕАЛЬНЫМИ шрифтами (требование задачи 0a/тестов отрисовки):
# окна двигаются за пределы экрана, отрисовка снимается grab().
os.environ.pop("QT_QPA_PLATFORM", None)

import faulthandler

faulthandler.dump_traceback_later(300, repeat=True, file=sys.stderr)

from pathlib import Path

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QImage, QTextDocument
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (QApplication, QAbstractItemView, QGroupBox,
                             QStyleOptionViewItem, QTabWidget, QVBoxLayout,
                             QWidget)

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog, _BrowserCellDelegate
from modules.theme_manager import ThemeManager

RESULTS = {"passed": 0, "failed": 0, "failures": []}


def check(name, ok, detail=""):
    if ok:
        RESULTS["passed"] += 1
        print(f"[PASS] {name}" + (f" | {detail}" if detail else ""))
    else:
        RESULTS["failed"] += 1
        RESULTS["failures"].append(name)
        print(f"[FAIL] {name}" + (f" | {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Помощники (общие с recon: метрики по пикселям + QTextLayout)
# ---------------------------------------------------------------------------

def _chan(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def wcag_luminance(color):
    return (0.2126 * _chan(color.red())
            + 0.7152 * _chan(color.green())
            + 0.0722 * _chan(color.blue()))


def wcag_contrast(c1, c2):
    l1, l2 = sorted((wcag_luminance(c1), wcag_luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def grab_viewport(widget):
    img = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    return img


def cell_ink_metrics(img, rect, tol=70):
    """Фон ячейки = доминирующий цвет; текст = цвет «ядра» чернил."""
    x0 = max(rect.left(), 0)
    x1 = min(rect.right(), img.width() - 1)
    y0 = max(rect.top(), 0)
    y1 = min(rect.bottom(), img.height() - 1)
    if x1 < x0 or y1 < y0:
        return None
    counts = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            name = img.pixelColor(x, y).name()
            counts[name] = counts.get(name, 0) + 1
    bg = QColor(max(counts, key=counts.get))
    ink_rows = []
    dists = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = img.pixelColor(x, y)
            d = (abs(c.red() - bg.red()) + abs(c.green() - bg.green())
                 + abs(c.blue() - bg.blue()))
            if d > tol:
                ink_rows.append(y)
                dists.setdefault(d, []).append(c)
    if not ink_rows:
        return {"bg": bg, "text": None, "contrast": None, "extent": 0}
    max_d = max(dists)
    core = dists[max_d]
    text = QColor(sum(c.red() for c in core) // len(core),
                  sum(c.green() for c in core) // len(core),
                  sum(c.blue() for c in core) // len(core))
    extent = max(ink_rows) - min(ink_rows) + 1
    return {"bg": bg, "text": text, "contrast": wcag_contrast(text, bg),
            "extent": extent}


def qtextlayout_line_count(text, font, width):
    """Число строк переноса по словам (QTextLayout, требование задачи 0a)."""
    from PyQt6.QtGui import QTextLayout, QTextOption
    if not text:
        return 1
    layout = QTextLayout(text, font)
    opt = QTextOption()
    opt.setWrapMode(QTextOption.WrapMode.WordWrap)
    layout.setTextOption(opt)
    layout.beginLayout()
    lines = 0
    line = layout.createLine()
    while line.isValid():
        line.setLineWidth(max(10.0, width))
        if line.textLength() == 0:
            break
        lines += 1
        line = layout.createLine()
    layout.endLayout()
    return max(lines, 1)


def two_line_text(font, width):
    n = 1
    text = "translation"
    while qtextlayout_line_count(text, font, width) < 2 and n < 60:
        n += 1
        text = " ".join(["translation"] * (n + 1))
    return text


def _actual_lines(extent, glyph_h, spacing):
    if extent <= glyph_h or spacing <= 0:
        return 1
    return round((extent - glyph_h) / spacing) + 1


def expected_row_height(text, column_width, font):
    """Эталон высоты: тот же алгоритм, что у делегата (_make_doc:
    setHtml при подсветке с повторным setDefaultFont, setPlainText без)."""
    doc = QTextDocument()
    doc.setDefaultFont(font)
    doc.setDocumentMargin(0)
    doc.setPlainText(text)  # без фильтра — ветка setPlainText
    doc.setTextWidth(max(10, column_width - _BrowserCellDelegate.PAD_X))
    return int(doc.size().height()) + _BrowserCellDelegate.PAD_Y


DB_SEQ = [0]


def make_db(log=lambda m: None):
    DB_SEQ[0] += 1
    db_path = os.path.join(PROFILE, f"tm31_suite_s{DB_SEQ[0]}.db")
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=log)
    db.connect()
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM31 suite TM', 'tma', 'en', 'nl')")
    db.connection.commit()
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


def pump(app, times=5):
    for _ in range(times):
        app.processEvents()


def show_dialog_offscreen(dlg, size=(1200, 700)):
    dlg.resize(*size)
    dlg.move(-3000, -3000)
    dlg.show()
    QTest.qWait(150)
    app = QApplication.instance()
    pump(app, 10)


def long_text(lines, chars_per_line=110):
    # Слова РАЗНОЙ длины: равномерные 11-символьные слова ложатся на
    # «ножевой край» переноса QTextLayout (ширина 351 → 10 строк, 350 → 12 —
    # замер doc_probe.py), из-за чего ±1 px ширины колонки меняет число
    # строк на 2. Разнобой длин делает перенос устойчивым к ±1 px.
    words = ["translation", "infantry", "division", "orders", "move"]
    unit, n = [], 0
    while n < chars_per_line:
        w = words[len(unit) % len(words)]
        unit.append(w)
        n += len(w) + 1
    return (" ".join(unit) + " ") * lines


# ---------------------------------------------------------------------------
# S1: отрисовка (задача 1) — windows-платформа, реальные шрифты
# ---------------------------------------------------------------------------

def s1_rendering(app):
    print("--- S1 отрисовка: единый путь без/с фильтром, resize ---")
    db = make_db()
    add(db, long_text(6), long_text(6))
    add(db, "short pair", "короткая пара")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table
    show_dialog_offscreen(dlg)
    QTest.qWait(300)  # дебаунс высот

    def measure(table, item):
        img = grab_viewport(table.viewport())
        return img, cell_ink_metrics(img, table.visualItemRect(item))

    item_font = table.font()  # как в tm3-сьюте: шрифт вида, а не item'а
    # Ширина переноса = ШИРИНА ЯЧЕЙКИ (visualItemRect), не columnWidth:
    # у stretch-колонок они расходятся на 1 px, а делегат получает именно
    # option.rect ячейки (замер doc_probe.py: ширина 351 → 10 строк, 350 → 12).
    colw = table.visualItemRect(table.item(0, 1)).width()
    wrap_width = colw - _BrowserCellDelegate.PAD_X
    exp_lines = qtextlayout_line_count(table.item(0, 1).text(),
                                       item_font, wrap_width)

    # межстрочный шаг и высота глифа — по документу и короткой ячейке
    doc1 = QTextDocument()
    doc1.setDefaultFont(item_font)
    doc1.setPlainText("translation")
    doc1.setTextWidth(wrap_width)
    doc2 = QTextDocument()
    doc2.setDefaultFont(item_font)
    doc2.setPlainText(two_line_text(item_font, wrap_width))
    doc2.setTextWidth(wrap_width)
    spacing = doc2.size().height() - doc1.size().height()
    _, m_short = measure(table, table.item(1, 1))
    glyph_h = m_short["extent"]

    img0, m0 = measure(table, table.item(0, 1))
    img0.save(os.path.join(EVIDENCE_DIR, "s1_nofilter.png"))
    lines0 = _actual_lines(m0["extent"], glyph_h, spacing)
    check("T1 без фильтра отрисовано столько же строк, сколько рассчитано "
          "переносом (±1)",
          abs(lines0 - exp_lines) <= 1,
          f"ожидается {exp_lines}, отрисовано {lines0} "
          f"(чернила {m0['extent']}px, шаг {spacing:.1f}px, "
          f"высота строки {table.rowHeight(0)}px)")

    exp_h = expected_row_height(table.item(0, 1).text(), colw, item_font)
    check("T2 без фильтра высота строки == высоте переноса + PAD (±2)",
          abs(table.rowHeight(0) - exp_h) <= 2,
          f"{table.rowHeight(0)}px vs {exp_h}px (colw={colw})")

    dlg.browser_filter.setText("translation")
    dlg.refresh_browser()
    pump(app)
    img1, m1 = measure(table, table.item(0, 1))
    img1.save(os.path.join(EVIDENCE_DIR, "s1_filter.png"))
    lines1 = _actual_lines(m1["extent"], glyph_h, spacing)
    check("T3 с фильтром отрисовано столько же строк, сколько рассчитано (±1)",
          abs(lines1 - exp_lines) <= 1,
          f"ожидается {exp_lines}, отрисовано {lines1}")

    dlg.resize(1700, 700)
    pump(app)
    QTest.qWait(300)  # дебаунс высот
    pump(app)
    item = table.item(0, 1)
    colw2 = table.visualItemRect(item).width()
    exp2 = qtextlayout_line_count(item.text(), item_font,
                                  colw2 - _BrowserCellDelegate.PAD_X)
    img2, m2 = measure(table, item)
    lines2 = _actual_lines(m2["extent"], glyph_h, spacing)
    check("T4 после resize окна (без Refresh) отрисованные строки == "
          "пересчитанному переносу (±1)",
          abs(lines2 - exp2) <= 1,
          f"ожидается {exp2}, отрисовано {lines2}, "
          f"высота строки {table.rowHeight(0)}px")
    dlg.hide()
    close_db(db)


# ---------------------------------------------------------------------------
# S2: контраст (задача 2) — светлая и тёмная тема, все состояния
# ---------------------------------------------------------------------------

def s2_contrast(app, theme):
    tag = "light" if "Light" in theme.current_theme.name else "dark"
    print(f"--- S2 контраст ({tag}, тема {theme.current_theme.name!r}) ---")
    db = make_db()
    add(db, "translation unit with words here", "перевод блока перевода здесь")
    add(db, long_text(3), long_text(3))
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table
    show_dialog_offscreen(dlg)
    QTest.qWait(300)
    pump(app)

    def grab_states():
        """(без выделения) → (выделенная строка) → (выделенная + фильтр)."""
        out = []
        img = grab_viewport(table.viewport())
        out.append(("plain", img))
        table.setCurrentCell(0, 1)
        pump(app)
        out.append(("selected", grab_viewport(table.viewport())))
        dlg.browser_filter.setText("translation")
        dlg.refresh_browser()
        table.setCurrentCell(0, 1)
        pump(app)
        out.append(("filter-sel", grab_viewport(table.viewport())))
        dlg.browser_filter.clear()
        dlg.refresh_browser()
        table.setCurrentCell(-1, -1)
        pump(app)
        return out

    bad = []
    measured = []
    for state, img in grab_states():
        for label, col in (("Source", 1), ("Target", 2), ("ID", 3)):
            item = table.item(0, col)
            if item is None:
                continue
            m = cell_ink_metrics(img, table.visualItemRect(item))
            if m is None or m["contrast"] is None:
                continue
            measured.append(f"{state}/{label}: bg={m['bg'].name()} "
                            f"text={m['text'].name()} c={m['contrast']:.2f}")
            if label != "ID" and m["contrast"] < 4.5:
                bad.append(f"{state}/{label}={m['contrast']:.2f}")

    # чередующаяся строка (row 1 = odd → alternate при включённой опции)
    img = grab_viewport(table.viewport())
    alt_item = table.item(1, 2)
    m_alt = cell_ink_metrics(img, table.visualItemRect(alt_item))
    if m_alt and m_alt["contrast"] is not None:
        measured.append(f"plain/alt-row-Target: bg={m_alt['bg'].name()} "
                        f"text={m_alt['text'].name()} c={m_alt['contrast']:.2f}")
        if m_alt["contrast"] < 4.5:
            bad.append(f"alt-row={m_alt['contrast']:.2f}")

    for line in measured:
        print(f"  {line}")
    check(f"T-S2-{tag}: контраст Source/Target >= 4.5:1 во всех состояниях",
          not bad, "; ".join(bad) or "все состояния в норме")

    # Подсвеченный фрагмент: тёмный текст на #FFD54F
    table.setCurrentCell(0, 1)
    dlg.browser_filter.setText("translation")
    dlg.refresh_browser()
    table.setCurrentCell(0, 1)
    pump(app)
    img = grab_viewport(table.viewport())
    img.save(os.path.join(EVIDENCE_DIR, f"s2_{tag}_filter_selected.png"))
    rect = table.visualItemRect(table.item(0, 1))
    yellow = QColor("#FFD54F")
    yellow_px = 0
    dark_px = 0
    x0 = max(rect.left(), 0)
    x1 = min(rect.right(), img.width() - 1)
    y0 = max(rect.top(), 0)
    y1 = min(rect.bottom(), img.height() - 1)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = img.pixelColor(x, y)
            d = (abs(c.red() - yellow.red()) + abs(c.green() - yellow.green())
                 + abs(c.blue() - yellow.blue()))
            if d <= 60:
                yellow_px += 1
            elif wcag_luminance(c) < 0.2:
                dark_px += 1
    check(f"T-S2-{tag}-hl: подсветка нарисована (#FFD54F найден), рядом "
          f"тёмный текст",
          yellow_px > 20 and dark_px > 20,
          f"жёлтых пикселей {yellow_px}, тёмных {dark_px}")
    dlg.hide()
    close_db(db)
    return not bad


# ---------------------------------------------------------------------------
# S3: немедленное применение «Search in»/«Whole words» (задача 3)
# ---------------------------------------------------------------------------

def s3_immediate_filter(app):
    print("--- S3 Search in / Whole words применяются сразу ---")
    db = make_db()
    add(db, "english source 1", "пехотная дивизия номер 1")
    add(db, "english source 2", "ПЕХОТНАЯ дивизия номер 2")
    add(db, "Пехотная школа", "english target 3")
    add(db, "plain source", "обычный перевод")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table
    show_dialog_offscreen(dlg)
    pump(app)

    dlg.browser_filter.setText("пехот")
    dlg.refresh_browser()
    pump(app)
    rows_both = table.rowCount()
    check("T-S3-1 «пехот» находит «Пехотная» и «ПЕХОТНАЯ» (3 строки)",
          rows_both == 3, f"rows={rows_both}")

    # Source only: сразу 1 строка («Пехотная школа» — единственный Source-хит;
    # «пехотная дивизия»/«ПЕХОТНАЯ дивизия» живут в Target)
    dlg.browser_search_in.setCurrentIndex(1)
    pump(app)
    rows_source_only = table.rowCount()
    tgt_enabled = dlg._target_delegate._enabled
    check("T-S3-2 смена «Search in» применяется сразу (Source only → 1)",
          rows_source_only == 1 and not tgt_enabled,
          f"rows={rows_source_only}, target highlight enabled={tgt_enabled}")

    # Target only: сразу 2 строки, подсветка только в Target
    dlg.browser_search_in.setCurrentIndex(2)
    pump(app)
    rows_target_only = table.rowCount()
    src_enabled = dlg._source_delegate._enabled
    tgt_enabled = dlg._target_delegate._enabled
    check("T-S3-3 «Target only» применяется сразу (2 строки, Source без "
          "подсветки)",
          rows_target_only == 2 and not src_enabled and tgt_enabled,
          f"rows={rows_target_only}, source={src_enabled}, target={tgt_enabled}")

    # Whole words применяется сразу: «пехот» как подстрока даёт 3 строки
    # («пехотная», «ПЕХОТНАЯ», «Пехотная школа»), как ЦЕЛОЕ СЛОВО — 0
    # («пехот» — только префикс «пехотная», \bпехот\b внутри не матчится).
    dlg.browser_search_in.setCurrentIndex(0)  # both
    pump(app)
    rows_ww_off = table.rowCount()
    dlg.browser_whole_words.setChecked(True)
    pump(app)
    rows_ww_on = table.rowCount()
    dlg.browser_whole_words.setChecked(False)
    pump(app)
    rows_ww_back = table.rowCount()
    check("T-S3-4 Whole words применяется сразу («пехот»: 3 → 0 → 3)",
          rows_ww_off == 3 and rows_ww_on == 0 and rows_ww_back == 3,
          f"rows off={rows_ww_off}, on={rows_ww_on}, back={rows_ww_back}")

    # Пустой Filter: состояние запоминается, перезагрузки нет
    log_lines = []
    dlg2 = TMManagerDialog(None, db, log_callback=log_lines.append)
    show_dialog_offscreen(dlg2)
    pump(app)
    loaded_before = sum("TM Browser: Loaded" in m for m in log_lines)
    dlg2.browser_search_in.setCurrentIndex(1)  # Source only, Filter пуст
    pump(app)
    loaded_after = sum("TM Browser: Loaded" in m for m in log_lines)
    check("T-S3-5 при пустом Filter смена режима не перезагружает таблицу",
          loaded_before == loaded_after,
          f"Loaded до={loaded_before}, после={loaded_after}")
    dlg2.hide()

    dlg.hide()
    close_db(db)


# ---------------------------------------------------------------------------
# S4: проводка свежести (задача 4) — модульная часть + AST монолита
# ---------------------------------------------------------------------------

def s4_freshness(app):
    print("--- S4 проводка свежести: показ всегда, «TM:» при refresh ---")
    db = make_db()
    add_tm(db, "TM Alpha", "alpha")
    add(db, "alpha entry 1", "alpha перевод 1", tm_id="alpha")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table
    show_dialog_offscreen(dlg)
    pump(app)

    # Показ всегда перезагружает (даже без dirty-флага): правим БД в обход
    # диалога, прячем и показываем подвкладку.
    db.cursor.execute("DELETE FROM translation_units WHERE tm_id = 'alpha'")
    db.connection.commit()
    table.clearSelection()
    dlg.browser_tab.hide()
    pump(app)
    log_lines = []
    dlg.log = log_lines.append
    dlg.browser_tab.show()
    QTest.qWait(200)
    pump(app)
    reloaded = table.rowCount() == 0
    log_ok = any("TM Browser: reloaded on show (0 entries)" in m
                 for m in log_lines)
    no_selection = len(table.selectedIndexes()) == 0
    check("T-S4-1 показ перезагружает всегда (записи удалены в БД → 0 строк)",
          reloaded, f"rows={table.rowCount()}")
    check("T-S4-2 лог «TM Browser: reloaded on show (N entries)» есть",
          log_ok, "; ".join(m for m in log_lines if "reloaded on show" in m))
    check("T-S4-3 выделение сбрасывается при показе",
          no_selection, f"selected={len(table.selectedIndexes())}")

    # refresh_browser пересобирает «TM:» (новая TM появляется)
    add_tm(db, "TM Beta", "beta")
    dlg.refresh_browser()
    pump(app)
    combo_ids = [dlg.browser_tm_combo.itemData(i)
                 for i in range(dlg.browser_tm_combo.count())]
    check("T-S4-4 refresh_browser пересобирает «TM:» (новая TM в списке)",
          "beta" in combo_ids, f"combo={combo_ids}")

    # Выбор TM сохраняется; выбор несуществующей → All TMs
    idx = dlg.browser_tm_combo.findData("beta")
    dlg.browser_tm_combo.setCurrentIndex(idx)
    dlg.refresh_browser()
    pump(app)
    kept = dlg.browser_tm_combo.currentData() == "beta"
    add_tm(db, "TM Gamma", "gamma")  # не помечаем deleted: просто пересборка
    db.cursor.execute("DELETE FROM translation_memories WHERE tm_id='beta'")
    db.connection.commit()
    dlg.refresh_browser()
    pump(app)
    fell_back = (dlg.browser_tm_combo.currentData() is None
                 and dlg.browser_tm_combo.currentText() == "All TMs")
    check("T-S4-5 выбор сохраняется, удалённая TM → «All TMs»",
          kept and fell_back,
          f"kept={kept}, after-delete current="
          f"{dlg.browser_tm_combo.currentText()!r}")

    # Показ ПОДВКЛАДКИ (вложенный QTabWidget, как в монолите): _BrowserTable
    # получает showEvent при переключении страницы → перезагрузка всегда.
    add(db, "nested entry", "nested перевод", tm_id="alpha")
    db.connection.commit()
    dlg.refresh_browser()
    pump(app)
    rows_before_switch = dlg.browser_table.rowCount()

    inner = QTabWidget()
    page = QWidget()
    page_lay = QVBoxLayout(page)
    page_lay.addWidget(dlg.browser_tab)  # реальная подвкладка монолита
    # browser_tab унёс из скрытого диалога ЯВНЫЙ hidden-флаг (не-текущая
    # страница QTabWidget); в реальном приложении переключение страницы
    # делает setVisible(True) явно — эмулируем этот шаг, иначе страница не
    # покажется вовсе (проверено mini-probe show_event_probe.py).
    dlg.browser_tab.setVisible(True)
    inner.addTab(page, "📖 Browse All")
    inner.addTab(QWidget(), "📋 TM List")
    outer = QTabWidget()
    holder = QGroupBox()
    holder_lay = QVBoxLayout(holder)
    holder_lay.addWidget(inner)
    outer.addTab(holder, "TMs")
    outer.move(-3000, -3000)
    outer.resize(1200, 700)
    outer.show()
    pump(app)
    inner.setCurrentIndex(1)  # TM List: Browse All скрыт
    pump(app)
    db.cursor.execute("DELETE FROM translation_units WHERE tm_id='alpha'")
    db.connection.commit()
    rows_hidden = dlg.browser_table.rowCount()
    log_lines2 = []
    dlg.log = log_lines2.append
    inner.setCurrentIndex(0)  # обратно к Browse All (showEvent)
    QTest.qWait(200)
    pump(app)
    check("T-S4-6 переключение подвкладки перезагружает данные (showEvent → "
          "reload, записи удалённые в БД исчезают)",
          rows_before_switch == 1 and rows_hidden == 1
          and dlg.browser_table.rowCount() == 0,
          f"rows до скрытия={rows_before_switch}, скрыт={rows_hidden}, "
          f"после показа={dlg.browser_table.rowCount()}")
    log_ok2 = any("TM Browser: reloaded on show (0 entries)" in m
                  for m in log_lines2)
    check("T-S4-7 лог «reloaded on show» и при показе подвкладки",
          log_ok2)
    outer.hide()
    dlg.hide()
    close_db(db)

    # --- AST-проверки монолита (единая точка проводки) ---
    print("--- S4 AST монолита (единая точка; реальный путь — recon R4) ---")
    sv_src = open(os.path.join(REPO, "Supervertaler.py"),
                  encoding="utf-8").read()
    tree = ast.parse(sv_src)
    found = {"browse_mgr_set": False, "notify_in_closure": False,
             "wrapper_gone": True, "editor_hook": False, "panel_hook": False}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Attribute)
                        and t.attr == "_tm_browse_manager"):
                    found["browse_mgr_set"] = True
        if isinstance(node, ast.Call):
            fn = node.func
            if (isinstance(fn, ast.Attribute)
                    and fn.attr == "on_tm_list_changed"):
                found["notify_in_closure"] = True
            if (isinstance(fn, ast.Attribute)
                    and fn.attr == "tm_tab_refresh_callback"
                    and isinstance(fn.value, ast.Name)
                    and fn.value.id == "self"):
                found["editor_hook"] = True
        if isinstance(node, ast.Attribute) and node.attr == "_prev_tm_list_refresh":
            found["wrapper_gone"] = False
    check("T-S4-6 AST: create_translation_memories_tab хранит "
          "_tm_browse_manager",
          found["browse_mgr_set"])
    check("T-S4-7 AST: в теле refresh_tm_list есть вызов on_tm_list_changed "
          "(единая точка)",
          found["notify_in_closure"])
    check("T-S4-8 AST: обёртка TM3 (_prev_tm_list_refresh) удалена",
          found["wrapper_gone"])
    check("T-S4-9 AST: TMEditorDialog/Match Panel вызывают "
          "tm_tab_refresh_callback (проводка через общую точку сохранена)",
          found["editor_hook"])


# ---------------------------------------------------------------------------
# S5: read-only (задача 5)
# ---------------------------------------------------------------------------

def s5_readonly(app):
    print("--- S5 ячейки только для чтения ---")
    db = make_db()
    add(db, "readonly source", "readonly перевод")
    dlg = TMManagerDialog(None, db, log_callback=lambda m: None)
    table = dlg.browser_table
    show_dialog_offscreen(dlg)
    pump(app)

    all_ro = all(
        not bool(table.item(r, c).flags() & Qt.ItemFlag.ItemIsEditable)
        for r in range(table.rowCount()) for c in range(table.columnCount()))
    check("T-S5-1 ни одна ячейка не имеет ItemIsEditable", all_ro)

    triggers_ok = table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    check("T-S5-2 editTriggers == NoEditTriggers", triggers_ok,
          str(table.editTriggers()))

    # Двойной клик не открывает редактор
    rect = table.visualItemRect(table.item(0, 1))
    QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.NoModifier, rect.center())
    pump(app)
    editing_state = QAbstractItemView.State.EditingState.value
    editor_absent = (table.state().value & editing_state) == 0
    check("T-S5-3 двойной клик не открывает редактор", editor_absent,
          f"state editing={bool(table.state().value & editing_state)}")

    # Сортировка по клику работает (read-only не ломает сортировку)
    table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
    first_before = table.item(0, 0).data(Qt.ItemDataRole.DisplayRole)
    table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    pump(app)
    order_desc = (table.item(0, 0).data(Qt.ItemDataRole.DisplayRole)
                  >= first_before)
    sorting_enabled = table.isSortingEnabled()
    check("T-S5-4 сортировка кликом по заголовку работает",
          order_desc and sorting_enabled,
          f"first={first_before}, sortingEnabled={sorting_enabled}")
    dlg.hide()
    close_db(db)


# ---------------------------------------------------------------------------

def main():
    app = QApplication.instance() or QApplication(sys.argv)

    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    # Тема приложения, как в реальном запуске (светлая по умолчанию).
    theme = ThemeManager(user_data_path=Path(PROFILE))
    theme.apply_theme(app)
    pump(app, 10)

    s1_rendering(app)
    s2_contrast(app, theme)
    s3_immediate_filter(app)
    s4_freshness(app)
    s5_readonly(app)

    # Тёмная тема: тот же набор контрастных состояний.
    theme.set_theme("Dark")
    theme.apply_theme(app)
    pump(app, 10)
    s2_contrast(app, theme)

    faulthandler.cancel_dump_traceback_later()
    total = RESULTS["passed"] + RESULTS["failed"]
    print(f"\nTOTAL: {total} checks, passed={RESULTS['passed']}, "
          f"failed={RESULTS['failed']}")
    if RESULTS["failures"]:
        print("FAILED:", "; ".join(RESULTS["failures"]))
    return 1 if RESULTS["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
