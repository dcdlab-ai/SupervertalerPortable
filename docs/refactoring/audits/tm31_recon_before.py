# -*- coding: utf-8 -*-
r"""
BATCH TM3.1 recon-скрипт «до» — воспроизводит регрессии S1–S4, найденные
ручным тестом BATCH TM3 (Browse All, modules/tm_manager_qt.py).

Ключевое отличие от tm3_recon_before.py: проверки ОТРИСОВКИ и ПРОВОДКИ,
а не только расчётов:
  R1 (S1) отрисовка без фильтра: делегат рисует ОДНУ строку (painter.drawText
          без TextWordWrap), хотя sizeHint считает высоту многострочного
          переноса (QTextDocument). Проверка по реальным пикселям grab()
          на платформе «windows» (реальные шрифты): протяжённость чернил
          в ячейке vs расчётное число строк переноса (QTextLayout).
          С фильтром путь другой (QTextDocument) — перенос работает.
  R2 (S2) контраст текста в Source/Target в состояниях: обычная,
          чередующаяся, выделенная строка, текущая ячейка выделенной
          строки; светлая и тёмная тема. Путь с подсветкой берёт
          palette.highlightedText() (белый), путь без подсветки —
          palette.text() (тёмный) — инверсия непоследовательна.
          Метрика: WCAG-контраст «цвет ядра текста vs фон ячейки» по
          пикселям grab().
  R3 (S3) смена «Search in»/«Whole words» при активном фильтре не
          переприменяет фильтр (строки и подсветка не меняются):
          currentIndexChanged/toggled не подключены к refresh_browser.
  R4 (S4) проводка свежести: реальный путь главного окна (подпроцесс,
          полный запуск SupervertalerQt): tm_tab_refresh_callback —
          сырое замыкание refresh_tm_list (обёртка TM3 не устанавливается:
          getattr на Supervertaler.py читает атрибут ДО его присвоения),
          on_tm_list_changed не вызывается ни разу, после реального
          _delete_tm записи висят в Browse All, новая TM отсутствует
          в списке «TM:».

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  TM31_PROFILE_DIR=<изолированный профиль> TM31_STAGE_DIR=<stage>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm31_recon_before.py

Результат: «CONFIRMED» = регрессия воспроизведена (на ПОСЛЕ-коде должна
исчезнуть), «NOT-REPRODUCED» = не воспроизведена. Код выхода всегда 0
(это не gate, а измерение). PNG-доказательства пишутся в TM31_STAGE_DIR.
"""

import json
import os
import pathlib
import subprocess
import sys

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM31_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(
        os.environ.get("TM31_STAGE_DIR", STAGE_ROOT), "tm31-recon-profile")

EVIDENCE_DIR = os.path.join(
    os.environ.get("TM31_STAGE_DIR", STAGE_ROOT), "evidence")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO)


def confirmed(name, ok, detail=""):
    """CONFIRMED = регрессия S1-S4 воспроизведена на ДО-коде."""
    print(f"[{'CONFIRMED' if ok else 'NOT-REPRODUCED'}] {name}" + (f" | {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Общие помощники (используются и в основном процессе, и в подпроцессе R4)
# ---------------------------------------------------------------------------

def setup_profile_env(profile):
    """Одноразовый профиль: прошлая тема/состояние приложения не должны
    попадать в следующий прогон (темы.json с Dark, проект и т.п.)."""
    import shutil
    if os.path.isdir(profile):
        shutil.rmtree(profile)
    os.makedirs(profile, exist_ok=True)
    os.makedirs(os.path.join(profile, "home"), exist_ok=True)
    os.makedirs(os.path.join(profile, "temp"), exist_ok=True)
    os.makedirs(os.path.join(profile, "workbench", "settings"), exist_ok=True)
    os.environ["SUPERVERTALER_DATA_ROOT"] = profile
    home = os.path.join(profile, "home")
    os.environ["USERPROFILE"] = home
    os.environ["HOME"] = home
    os.environ["APPDATA"] = home
    os.environ["LOCALAPPDATA"] = home
    os.environ["TEMP"] = os.path.join(profile, "temp")
    os.environ["TMP"] = os.environ["TEMP"]


# --- пиксельные метрики -----------------------------------------------------

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
    from PyQt6.QtGui import QImage
    img = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    return img


def cell_ink_metrics(img, rect, tol=70):
    """Фон ячейки = доминирующий цвет; текст = цвет «ядра» чернил
    (пиксели на >=90 % максимального удаления от фона, т.е. без
    антиалиасинговой каймы). Возвращает фон, текст, контраст и
    протяжённость чернил по вертикали."""
    from PyQt6.QtGui import QColor
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
    dominant_name = max(counts, key=counts.get)
    bg = QColor(dominant_name)
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
        return {"bg": bg, "text": None, "contrast": None,
                "extent": 0, "ink_px": 0}
    max_d = max(dists)
    core = dists[max_d]
    r = sum(c.red() for c in core) // len(core)
    g = sum(c.green() for c in core) // len(core)
    b = sum(c.blue() for c in core) // len(core)
    text = QColor(r, g, b)
    extent = (max(ink_rows) - min(ink_rows) + 1) if ink_rows else 0
    return {"bg": bg, "text": text,
            "contrast": wcag_contrast(text, bg),
            "extent": extent, "ink_px": len(ink_rows)}


def qtextlayout_line_count(text, font, width):
    """Число строк переноса по словам (QTextLayout, как требует задача 0a)."""
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
    """Текст ровно на 2 строки переноса при данной ширине."""
    n = 1
    text = "translation"
    while qtextlayout_line_count(text, font, width) < 2 and n < 60:
        n += 1
        text = " ".join(["translation"] * (n + 1))
    return text


def save_png(img, name):
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    path = os.path.join(EVIDENCE_DIR, name)
    img.save(path)
    return path


# --- фикстуры TM ------------------------------------------------------------

DB_SEQ = [0]


def make_db(log=lambda msg: None):
    from modules.database_manager import DatabaseManager
    DB_SEQ[0] += 1
    db_path = os.path.join(PROFILE, f"tm31_recon_s{DB_SEQ[0]}.db")
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=log)
    db.connect()
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM31 recon TM', 'tm31recon', 'en', 'nl')"
    )
    db.connection.commit()
    return db


def add(db, source, target):
    db.add_translation_unit(
        source=source, target=target, source_lang="en", target_lang="nl",
        tm_id="tm31recon",
    )


def long_text(lines, chars_per_line=110):
    """Текст, который в узкой колонке оборачивается в много строк.

    Слова РАЗНОЙ длины: равномерные 11-символьные слова ложатся на
    «ножевой край» переноса QTextLayout (351 px → 10 строк, 350 px → 12 —
    замер doc_probe.py), из-за чего ±1 px ширины колонки меняет число строк
    на 2 и ломает дискриминацию «до/после»."""
    words = ["translation", "infantry", "division", "orders", "move"]
    unit, n = [], 0
    while n < chars_per_line:
        w = words[len(unit) % len(words)]
        unit.append(w)
        n += len(w) + 1
    return (" ".join(unit) + " ") * lines


def _actual_lines(extent, glyph_h, spacing):
    """Число реально отрисованных строк по протяжённости чернил."""
    if extent <= glyph_h or spacing <= 0:
        return 1
    return round((extent - glyph_h) / spacing) + 1


# ---------------------------------------------------------------------------
# Основной процесс: R1/R2/R3 на платформе windows (реальные шрифты)
# ---------------------------------------------------------------------------

def run_render_recon():
    from modules.tm_manager_qt import TMManagerDialog, _BrowserCellDelegate
    from modules.theme_manager import ThemeManager

    from PyQt6.QtGui import QTextDocument
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    theme = ThemeManager(user_data_path=pathlib.Path(PROFILE))
    theme.apply_theme(app)

    print(f"platform: {os.environ.get('QT_QPA_PLATFORM', 'windows(default)')}")

    # ---------------- R1 (S1): отрисовка без фильтра ----------------
    print("== R1 (S1) отрисовка без фильтра vs с фильтром ==")
    db1 = make_db()
    add(db1, long_text(6), long_text(6))
    add(db1, "short pair", "короткая пара")
    dlg = TMManagerDialog(None, db1, log_callback=lambda msg: None)
    table = dlg.browser_table
    dlg.resize(1200, 700)
    dlg.move(-3000, -3000)  # окно за пределами экрана (требование 0a)
    dlg.show()
    QTest.qWait(300)  # дебаунс высот (на ПОСЛЕ-коде успевает сработать)
    app.processEvents()

    def measure(table, item):
        img = grab_viewport(table.viewport())
        return img, cell_ink_metrics(img, table.visualItemRect(item))

    src_item = table.item(0, 1)
    # Ширина переноса = ШИРИНА ЯЧЕЙКИ (visualItemRect), не columnWidth:
    # делегат получает option.rect ячейки (у stretch-колонок они расходятся
    # на 1 px, а на «ножевом крае» переноса это меняет число строк).
    colw = table.visualItemRect(src_item).width()
    wrap_width = colw - _BrowserCellDelegate.PAD_X
    # Шрифт ВИДА (как у делегата через option.font), а не item'а: item
    # создаётся с шрифтом приложения (Segoe UI 10), делегат рендерит шрифтом
    # таблицы (Segoe UI 9) — на 9pt перенос даёт другое число строк.
    font = table.font()
    exp_lines = qtextlayout_line_count(src_item.text(), font, wrap_width)

    img0, m0 = measure(table, src_item)
    _, m_short = measure(table, table.item(1, 1))
    glyph_h = m_short["extent"]

    doc1 = QTextDocument()
    doc1.setDefaultFont(font)
    doc1.setPlainText("translation")
    doc1.setTextWidth(wrap_width)
    text2 = two_line_text(font, wrap_width)
    doc2 = QTextDocument()
    doc2.setDefaultFont(font)
    doc2.setPlainText(text2)
    doc2.setTextWidth(wrap_width)
    spacing = doc2.size().height() - doc1.size().height()

    actual_lines = _actual_lines(m0["extent"], glyph_h, spacing)
    save_png(img0, "r1_nofilter_row0.png")
    confirmed(
        "R1a без фильтра текст рисуется МЕНЬШИМ числом строк, чем рассчитана высота",
        actual_lines < exp_lines - 1,
        f"ожидается строк переноса: {exp_lines}; реально отрисовано: "
        f"{actual_lines} (чернила {m0['extent']}px, одиночная строка "
        f"{glyph_h}px, межстрочный шаг {spacing:.1f}px, высота строки "
        f"{table.rowHeight(0)}px)",
    )

    # с фильтром: другой путь отрисовки (QTextDocument с подсветкой)
    dlg.browser_filter.setText("translation")
    dlg.refresh_browser()
    app.processEvents()
    src_item = table.item(0, 1)
    img1, m1 = measure(table, src_item)
    actual_lines_f = _actual_lines(m1["extent"], glyph_h, spacing)
    save_png(img1, "r1_filter_row0.png")
    confirmed(
        "R1b с фильтром тот же текст рисуется по-другому (второй путь отрисовки)",
        abs(actual_lines_f - exp_lines) <= 1 and actual_lines != actual_lines_f,
        f"без фильтра: {actual_lines} строк; с фильтром: {actual_lines_f} строк "
        f"(ожидается {exp_lines}); чернила {m1['extent']}px",
    )
    dlg.hide()
    db1.connection.close()

    # ---------------- R2 (S2): контраст по темам и состояниям ----------------
    print("== R2 (S2) контраст текста по состояниям и темам ==")
    db2 = make_db()
    add(db2, "translation unit with words here", "перевод блока перевода здесь")
    add(db2, long_text(3), long_text(3))
    dlg2 = TMManagerDialog(None, db2, log_callback=lambda msg: None)
    table2 = dlg2.browser_table
    dlg2.resize(1200, 700)
    dlg2.move(-3000, -3000)
    dlg2.show()
    QTest.qWait(300)
    app.processEvents()

    def snap_states(tag, theme_name):
        """(без фильтра) → (выделенная строка) → (выделенная + фильтр)."""
        rows = []
        img = grab_viewport(table2.viewport())
        save_png(img, f"r2_{tag}_nofilter.png")
        for label, item in (("Source", table2.item(0, 1)),
                            ("Target", table2.item(0, 2)),
                            ("ID", table2.item(0, 3)),
                            ("Target-alt-row", table2.item(1, 2))):
            rows.append((f"{theme_name}/nofilter/{label}",
                         cell_ink_metrics(img, table2.visualItemRect(item))))
        # выделенная строка: Source = текущая ячейка, Target = выбранная
        table2.setCurrentCell(0, 1)
        app.processEvents()
        img = grab_viewport(table2.viewport())
        save_png(img, f"r2_{tag}_selected_nofilter.png")
        for label, item in (("Source", table2.item(0, 1)),
                            ("Target", table2.item(0, 2)),
                            ("ID", table2.item(0, 3))):
            rows.append((f"{theme_name}/nofilter-sel/{label}",
                         cell_ink_metrics(img, table2.visualItemRect(item))))
        # с фильтром (подсветка активна в обеих колонках)
        dlg2.browser_filter.setText("translation")
        dlg2.refresh_browser()
        table2.setCurrentCell(0, 1)
        app.processEvents()
        img = grab_viewport(table2.viewport())
        save_png(img, f"r2_{tag}_filter_selected.png")
        for label, item in (("Source", table2.item(0, 1)),
                            ("Target", table2.item(0, 2)),
                            ("ID", table2.item(0, 3))):
            rows.append((f"{theme_name}/filter-sel/{label}",
                         cell_ink_metrics(img, table2.visualItemRect(item))))
        dlg2.browser_filter.clear()
        dlg2.refresh_browser()
        table2.setCurrentCell(-1, -1)
        app.processEvents()
        return rows

    all_rows = snap_states("light", "Light")
    print(f"  palette under theme Light: highlight="
          f"{table2.palette().highlight().color().name()} highlightedText="
          f"{table2.palette().highlightedText().color().name()} base="
          f"{table2.palette().base().color().name()} text="
          f"{table2.palette().text().color().name()}")

    st_contrast = {}
    for state, m in all_rows:
        if m["contrast"] is None:
            it = table2.item(0, 2) if "Target" in state else table2.item(0, 1)
            rect = table2.visualItemRect(it)
            print(f"  {state:32s} БЕЗ ЧЕРНИЛ (text={it.text()[:25]!r}, "
                  f"rect={rect.width()}x{rect.height()})")
            continue
        print(f"  {state:32s} bg={m['bg'].name()} text={m['text'].name()} "
              f"contrast={m['contrast']:.2f}")
        st_contrast[state] = m["contrast"]
    light_bad = {}
    for s, c in st_contrast.items():
        th, grp, col = s.split("/", 2)
        if col.startswith(("Source", "Target")) and c < 4.5:
            id_c = st_contrast.get(f"{th}/{grp}/ID")
            if id_c is None or id_c >= 4.5:
                light_bad[s] = c
    confirmed(
        "R2a светлая тема: Source/Target < 4.5:1, при этом ID в тех же "
        "состояниях >= 4.5:1 — инверсия непоследовательна между колонками",
        bool(light_bad),
        "; ".join(f"{s}={c:.2f}" for s, c in sorted(light_bad.items()))
        or "все состояния Source/Target >= 4.5:1",
    )

    # тёмная тема
    theme.set_theme("Dark")
    theme.apply_theme(app)
    app.processEvents()
    dark_rows = snap_states("dark", "Dark")
    print(f"  palette under theme Dark: highlight="
          f"{table2.palette().highlight().color().name()} highlightedText="
          f"{table2.palette().highlightedText().color().name()} base="
          f"{table2.palette().base().color().name()} text="
          f"{table2.palette().text().color().name()}")
    dark_st = {}
    for state, m in dark_rows:
        if m["contrast"] is None:
            continue
        print(f"  {state:32s} bg={m['bg'].name()} text={m['text'].name()} "
              f"contrast={m['contrast']:.2f}")
        dark_st[state] = m["contrast"]
    dark_bad = {s: c for s, c in dark_st.items()
                if s.split("/", 2)[2].startswith(("Source", "Target"))
                and c < 4.5}
    confirmed(
        "R2b тёмная тема: Source/Target < 4.5:1 в каком-то состоянии",
        bool(dark_bad),
        "; ".join(f"{s}={c:.2f}" for s, c in sorted(dark_bad.items()))
        or "все состояния >= 4.5:1",
    )
    dlg2.hide()
    db2.connection.close()

    # ---------------- R3 (S3): проводка Search in / Whole words ----------------
    print("== R3 (S3) смена Search in / Whole words при активном фильтре ==")
    db3 = make_db()
    for i in range(4):
        add(db3, f"english source {i}", f"пехотная дивизия номер {i}")
    add(db3, "Пехотная школа", "english target")
    dlg3 = TMManagerDialog(None, db3, log_callback=lambda msg: None)
    table3 = dlg3.browser_table
    dlg3.resize(1200, 700)
    dlg3.move(-3000, -3000)
    dlg3.show()
    QTest.qWait(300)
    app.processEvents()

    dlg3.browser_filter.setText("пехот")
    dlg3.refresh_browser()
    app.processEvents()
    rows_before = table3.rowCount()

    import re as _re
    src = open(os.path.join(REPO, "modules", "tm_manager_qt.py"),
               encoding="utf-8").read()
    search_in_connected = _re.search(
        r"browser_search_in\.currentIndexChanged\.connect", src) is not None
    ww_connected = _re.search(
        r"browser_whole_words\.toggled\.connect", src) is not None
    print(f"  browser_search_in.currentIndexChanged подключён: {search_in_connected}")
    print(f"  browser_whole_words.toggled подключён: {ww_connected}")

    # динамика: смена режима при активном фильтре
    dlg3.browser_search_in.setCurrentIndex(1)  # Source only
    app.processEvents()
    rows_after_mode = table3.rowCount()
    tgt_enabled_after = dlg3._target_delegate._enabled
    dlg3.browser_whole_words.setChecked(True)
    app.processEvents()
    rows_after_ww = table3.rowCount()
    confirmed(
        "R3a смена «Search in» при активном фильтре не переприменяет фильтр",
        rows_after_mode == rows_before and tgt_enabled_after,
        f"строк до: {rows_before}, после смены режима: {rows_after_mode} "
        f"(ожидалось 1: «Пехотная школа» в Source); подсветка Target всё ещё "
        f"включена: {tgt_enabled_after}; currentIndexChanged подключён: "
        f"{search_in_connected}",
    )
    confirmed(
        "R3b смена «Whole words» при активном фильтре не переприменяет фильтр",
        rows_after_ww == rows_before,
        f"строк после включения Whole words: {rows_after_ww} "
        f"(Whole words+«пехот» в Source only должен давать 0 строк); "
        f"toggled подключён: {ww_connected}",
    )
    dlg3.hide()
    db3.connection.close()

    print("== R5 статические факты проводки (0d, в отчёт) ==")
    sv_lines = open(os.path.join(REPO, "Supervertaler.py"),
                    encoding="utf-8").read().splitlines()
    for i, line in enumerate(sv_lines, 1):
        if "_prev_tm_list_refresh = getattr" in line:
            print(f"  Supervertaler.py:{i}: обёртка TM3 читает атрибут "
                  f"tm_tab_refresh_callback (на этот момент он ещё НЕ задан)")
        if "self.tm_tab_refresh_callback = refresh_tm_list" in line:
            print(f"  Supervertaler.py:{i}: атрибут присваивается ЗДЕСЬ — "
                  f"позже чтения в обёртке")
        if line.strip().startswith("def refresh_tm_list():"):
            print(f"  Supervertaler.py:{i}: замыкание refresh_tm_list "
                  f"(единая точка: create/import/delete получают его как "
                  f"параметр, TMEditorDialog/Match Panel вызывают через "
                  f"атрибут)")
        if "self.refresh_tm_list()" in line:
            print(f"  Supervertaler.py:{i}: вызов метода-заглушки "
                  f"refresh_tm_list (no-op, не замыкание)")

    print("\nMain-process recon done — запуск подпроцесса R4 (полное приложение)...")


# ---------------------------------------------------------------------------
# Подпроцесс R4: полный запуск SupervertalerQt (offscreen), реальная проводка
# ---------------------------------------------------------------------------

def run_fullapp_recon():
    import faulthandler
    setup_profile_env(os.environ["TM31_FULLAPP_PROFILE"])
    # Платформа windows (реальные шрифты): offscreen без каталога шрифтов
    # флакует access violation'ом при построении приложения ("Cannot find
    # font directory"); окно всё равно не показывается до фазы показа,
    # а там оно двигается за пределы экрана.
    os.environ["QT_QPA_PLATFORM"] = "windows"
    faulthandler.enable(file=sys.stderr)  # SIGSEGV → стек-дамп (probe флакует)
    faulthandler.dump_traceback_later(15, repeat=True, file=sys.stderr)

    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import (QApplication, QDialog, QMessageBox,
                                 QPushButton, QTableWidget, QTabWidget)

    app = QApplication.instance() or QApplication(sys.argv)

    import Supervertaler as _sv
    from Supervertaler import SupervertalerQt
    from modules.tm_manager_qt import TMManagerDialog

    # Отключаем ГЛОБАЛЬНЫЕ хоткеи целиком: их фоновый message-pump
    # флакует access violation'ом в probe-процессе (faulthandler: main
    # thread при живом pump-потоке); в реальном приложении это не
    # воспроизводится, для проводки свежести хоткеи не нужны.
    _sv.SuperlookupTab.register_global_hotkey = lambda self: None
    from modules.platform_helpers import GlobalHotkeyManager
    GlobalHotkeyManager.register = lambda self, *a, **k: None
    GlobalHotkeyManager.start = lambda self: False

    # Все модальные диалоги обезврежены; подтверждение удаления = Yes.
    QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected
    QMessageBox.question = staticmethod(
        lambda *a, **k: QMessageBox.StandardButton.Yes)
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    QMessageBox.critical = staticmethod(lambda *a, **k: None)

    logs = []
    w = SupervertalerQt()
    w.log = logs.append

    mgrs = w.findChildren(TMManagerDialog)
    if not mgrs:
        print("R4_ERROR: TMManagerDialog not found")
        return 2
    mgr = mgrs[0]

    # Инструментация: счётчики реальных вызовов (не прямых).
    calls = {"changed": 0, "shown": 0}
    _orig_changed = mgr.on_tm_list_changed
    _orig_shown = mgr._on_browser_shown
    mgr.on_tm_list_changed = lambda: (
        calls.__setitem__("changed", calls["changed"] + 1),
        _orig_changed())[1]
    mgr._on_browser_shown = lambda: (
        calls.__setitem__("shown", calls["shown"] + 1),
        _orig_shown())[1]

    cb_name = getattr(w.tm_tab_refresh_callback, "__name__", "?")

    # Подвкладка «📖 Browse All» (вложенный QTabWidget внутри вкладки TMs)
    nested = None
    browse_idx = -1
    for t in w.findChildren(QTabWidget):
        for i in range(t.count()):
            if "Browse All" in t.tabText(i):
                nested = t
                browse_idx = i
    if nested is None:
        print("R4_ERROR: Browse All sub-tab not found")
        return 2

    def combo_ids():
        return [mgr.browser_tm_combo.itemData(i)
                for i in range(mgr.browser_tm_combo.count())]

    def browse_rows():
        return mgr.browser_table.rowCount()

    def switch_to_browse():
        """Действие пользователя: клик по вкладке «💾 TMs», затем по
        подвкладке «📖 Browse All»."""
        if not w.isVisible():
            w.move(-3000, -3000)  # за пределами экрана
            w.show()
            app.processEvents()
        for i in range(w.main_tabs.count()):
            if "TMs" in w.main_tabs.tabText(i):
                w.main_tabs.setCurrentIndex(i)
                break
        nested.setCurrentIndex(browse_idx)
        QTest.qWait(150)
        app.processEvents()

    def find_button(fragment):
        # Окно ещё скрыто на фазе кликов — видимость не требуется: click()
        # работает и на скрытых виджетах (в реальном приложении окно видно).
        for b in w.findChildren(QPushButton):
            if fragment in b.text():
                return b
        return None

    from PyQt6.QtWidgets import QLineEdit as _QLineEdit
    _rejected_stub = (lambda self, *a, **k: QDialog.DialogCode.Rejected)

    def _create_exec_stub(dialog_self, *a, **k):
        # Заполняем поля РЕАЛЬНОГО диалога создания TM и «нажимаем» Create:
        # порядок полей — name, tm_id, source_lang, target_lang.
        for f, val in zip(dialog_self.findChildren(_QLineEdit),
                          ["TM31 Recon B", "tm31reconb", "en", "nl"]):
            f.setText(val)
        return QDialog.DialogCode.Accepted

    # --- Фаза 1: TM A с записями, Browse All смотрят (как у Дмитрия) ---
    w.tm_metadata_mgr.create_tm("TM31 Recon A", "tm31recona", "en", "nl")
    for i in range(3):
        w.db_manager.add_translation_unit(
            source=f"recon source {i}", target=f"recon target {i}",
            source_lang="en", target_lang="nl", tm_id="tm31recona")
    w.tm_tab_refresh_callback()
    mgr.refresh_browser()
    rows_initial = browse_rows()
    # Фаза 1 — ТОЛЬКО подготовка: сбрасываем dirty-флаг (если есть), чтобы
    # фазы 2–5 отражали РЕАЛЬНЫЕ кнопочные пути, а не остаток setup'а.
    if hasattr(mgr, "_data_dirty"):
        mgr._data_dirty = False

    # --- Фаза 2: создание TM B РЕАЛЬНОЙ кнопкой «+ Create New TM» ---
    # (кнопка вызывает _show_create_tm_dialog(tm_metadata_mgr,
    # refresh_tm_list-ЗАМЫКАНИЕ, ...) — тот же путь, что у пользователя).
    create_btn = find_button("Create New TM")
    if create_btn is None:
        print("R4_ERROR: create button not found")
        return 2
    QDialog.exec = _create_exec_stub
    try:
        create_btn.click()
        app.processEvents()
    finally:
        QDialog.exec = _rejected_stub
    f2 = {
        "combo": combo_ids(),
        "rows": browse_rows(),
        "dirty": getattr(mgr, "_data_dirty", None),
        "shown_calls": calls["shown"],
    }
    print(f"R4 фаза2 (создание TM B кнопкой, Browse All скрыт): "
          f"combo={f2['combo']}, rows={f2['rows']}, dirty={f2['dirty']}, "
          f"shown={f2['shown_calls']}")

    # --- Фаза 3: пользователь кликает «📖 Browse All» (showEvent) ---
    switch_to_browse()
    f3 = {
        "combo": combo_ids(),
        "rows": browse_rows(),
        "dirty": getattr(mgr, "_data_dirty", None),
        "shown_calls": calls["shown"],
        "visible": mgr.browser_table.isVisible(),
    }
    print(f"R4 фаза3 (показ Browse All): combo={f3['combo']}, rows={f3['rows']}, "
          f"dirty={f3['dirty']}, shown={f3['shown_calls']}, "
          f"visible={f3['visible']}")

    # --- Фаза 4: удаление TM A РЕАЛЬНОЙ кнопкой «🗑️ Delete TM» ---
    tm_table = None
    for t in w.findChildren(QTableWidget):
        hdr = t.horizontalHeaderItem(0)
        if hdr is not None and hdr.text() == "TM Name":
            tm_table = t
            break
    if tm_table is None:
        print("R4_ERROR: tm_table not found")
        return 2
    # вернуться на TM List (Browse All снова скрыт)
    nested.setCurrentIndex(0)
    app.processEvents()
    row = None
    for r in range(tm_table.rowCount()):
        it = tm_table.item(r, 0)
        if it is not None and it.text() == "TM31 Recon A":
            row = r
            break
    if row is None:
        print("R4_ERROR: TM row not found in TM list")
        return 2
    tm_table.selectRow(row)
    app.processEvents()
    delete_btn = find_button("Delete TM")
    if delete_btn is None:
        print("R4_ERROR: delete button not found")
        return 2
    delete_btn.click()  # QMessageBox.question уже обезврежен → Yes
    app.processEvents()
    f4 = {
        "combo": combo_ids(),
        "rows": browse_rows(),
        "dirty": getattr(mgr, "_data_dirty", None),
        "changed_calls": calls["changed"],
    }
    print(f"R4 фаза4 (удаление TM A кнопкой, Browse All скрыт): "
          f"combo={f4['combo']}, rows={f4['rows']} "
          f"(до удаления {rows_initial}), dirty={f4['dirty']}, "
          f"changed={f4['changed_calls']}")

    # --- Фаза 5: пользователь снова открывает Browse All ---
    switch_to_browse()
    f5 = {
        "combo": combo_ids(),
        "rows": browse_rows(),
        "shown_calls": calls["shown"],
    }
    print(f"R4 фаза5 (повторный показ): combo={f5['combo']}, "
          f"rows={f5['rows']}, shown={f5['shown_calls']}")

    verdict = {
        "callback_name": cb_name,
        "calls": dict(calls),
        "f2_created_in_combo": "tm31reconb" in f2["combo"],
        "f3_created_in_combo_after_show": "tm31reconb" in f3["combo"],
        "f3_rows_after_show": f3["rows"],
        "f3_shown_fired": f3["shown_calls"] > 0,
        "f4_rows_after_delete_hidden": f4["rows"],
        "f4_dirty": f4["dirty"],
        "f5_deleted_in_combo_after_show": "tm31recona" in f5["combo"],
        "f5_rows_after_show": f5["rows"],
        "rows_initial": rows_initial,
    }
    print("R4_JSON " + json.dumps(verdict))
    faulthandler.cancel_dump_traceback_later()
    return 0


def main():
    if "--fullapp" in sys.argv:
        return run_fullapp_recon()

    setup_profile_env(PROFILE)
    run_render_recon()

    # R4: полный запуск приложения в подпроцессе (отдельный изолированный
    # профиль, offscreen — отрисовка там не нужна, нужна РЕАЛЬНАЯ проводка).
    fullapp_profile = os.path.join(
        os.environ.get("TM31_STAGE_DIR", STAGE_ROOT),
        "tm31-recon-fullapp-profile")
    env = dict(os.environ)
    env["TM31_FULLAPP_PROFILE"] = fullapp_profile
    script = os.path.abspath(__file__)
    cmd = [sys.executable, "-u", script, "--fullapp"]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900,
                          cwd=REPO)
    out = (proc.stdout or "") + (proc.stderr or "")
    print("--- R4 subprocess output ---")
    print(out[-4000:] if len(out) > 4000 else out)
    json_line = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("R4_JSON "):
            json_line = json.loads(line[len("R4_JSON "):])
    if json_line:
        j = json_line
        # Симптомы S4 у Дмитрия: созданная TM отсутствует в «TM:» даже
        # после показа Browse All; записи/список TM обновляются только
        # вручную. Проверяем РЕАЛЬНЫЙ поток: операция при скрытой подвкладке
        # → показ подвкладки (showEvent).
        c1 = (not j["f2_created_in_combo"]
              and not j["f3_created_in_combo_after_show"])
        confirmed("R4a созданная TM не появляется в «TM:» даже после показа "
                  "подвкладки (реальный путь create → show)",
                  c1,
                  f"после create (скрыт): {j['f2_created_in_combo']}; после "
                  f"показа: {j['f3_created_in_combo_after_show']}; "
                  f"showEvent сработал: {j['f3_shown_fired']}")
        c2 = (j["f5_deleted_in_combo_after_show"]
              or j["f5_rows_after_show"] >= j["rows_initial"])
        confirmed("R4b удалённая TM остаётся в «TM:» / записи висят в Browse "
                  "All даже после показа подвкладки (реальный путь delete → "
                  "show)",
                  c2,
                  f"после удаления (скрыт): rows={j['f4_rows_after_delete_hidden']}, "
                  f"dirty={j['f4_dirty']}; после показа: rows="
                  f"{j['f5_rows_after_show']}, TM в списке: "
                  f"{j['f5_deleted_in_combo_after_show']}")
        print(f"  callback={j['callback_name']}; on_tm_list_changed="
              f"{j['calls']['changed']}, _on_browser_shown={j['calls']['shown']}")
    else:
        confirmed("R4 подпроцесс вернул результат", False,
                  "нет R4_JSON в выводе — см. вывод подпроцесса выше")

    print("\nRecon done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
