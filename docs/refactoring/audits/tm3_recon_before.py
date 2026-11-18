r"""
BATCH TM3 recon-скрипт «до» — воспроизводит находки 0a–0d ручного теста
Browse All (modules/tm_manager_qt.py, TMManagerDialog.browser_tab).

Проверки (offscreen, изолированный SUPERVERTALER_DATA_ROOT, временная TM-база):
  R1 (0a) высота строк: (а) первый показ вкладки — высоты строк посчитаны
          до того, как колонки получили финальную ширину (строки выше,
          чем нужно: «лишние пустые поля»); (б) изменение ширины окна
          НЕ пересчитывает высоты (после расширения строки всё ещё выше,
          чем нужно). Сравнение с эталоном resizeRowsToContents() при
          финальной ширине. Ручной тест: после Refresh нормализуется.
  R2 (0b) галка «Whole words» (обычный QCheckBox под темой приложения):
          включённое состояние НЕ содержит отметки ✓ в индикаторе —
          только заливка фона. Контрольный образец: CheckmarkCheckBox
          (modules/styled_widgets.py) в включённом состоянии ✓ рисует.
          Причина: modules/theme_manager.py:479-486 задаёт
          QCheckBox::indicator:checked { background-color: ... } БЕЗ
          изображения отметки — Qt рисует индикатор по stylesheet,
          родная галка не отрисовывается вовсе.
  R3 (0c) редактирование ячейки: все 6 колонок редактируемы по умолчанию
          (ItemIsEditable в флагах item), делегат редактора не установлен
          (дефолтный однострочный QLineEdit), изменённый текст ячейки
          НЕ пишется в БД (никакой itemChanged-обработчик не подключён —
          статически: grep 'itemChanged' modules/tm_manager_qt.py пуст).
          Побочный эффект: при включённой сортировке правка по
          отсортированной колонке перетасовывает строки.
  R4 (0d) tooltip: Source и Target ячейки несут полный текст в
          setToolTip (подтверждение места установки).

Запуск (из репозитория E:\Dev\SupervertalerPortable):
  QT_QPA_PLATFORM=offscreen TM3_PROFILE_DIR=<изолированный профиль>
  E:\Dev\python-embed\python.exe docs/refactoring/audits/tm3_recon_before.py

Результат: «CONFIRMED» = находка воспроизведена (на ПОСЛЕ-коде должна
исчезнуть), «NOT-REPRODUCED» = не воспроизведена. Код выхода всегда 0
(это не gate, а измерение).
"""

import os
import sys

STAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("TM3_PROFILE_DIR")
if not PROFILE:
    PROFILE = os.path.join(os.environ.get("TM3_STAGE_DIR", STAGE_ROOT), "tm3-recon-profile")

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

faulthandler.dump_traceback_later(180, repeat=True)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication, QCheckBox

from modules.database_manager import DatabaseManager
from modules.tm_manager_qt import TMManagerDialog
from modules.theme_manager import ThemeManager
from modules.styled_widgets import CheckmarkCheckBox

DB_SEQ = [0]


def confirmed(name, ok, detail=""):
    """CONFIRMED = находка 0a-0d воспроизведена на ДО-коде."""
    print(f"[{'CONFIRMED' if ok else 'NOT-REPRODUCED'}] {name}" + (f" | {detail}" if detail else ""))


def make_db():
    DB_SEQ[0] += 1
    db_path = os.path.join(PROFILE, f"tm3_recon_s{DB_SEQ[0]}.db")
    for suffix in ("", "-wal", "-shm"):
        p = db_path + suffix
        if os.path.exists(p):
            os.remove(p)
    db = DatabaseManager(db_path=db_path, log_callback=lambda *a, **k: None)
    db.connect()
    db.cursor.execute(
        "INSERT INTO translation_memories (name, tm_id, source_lang, target_lang) "
        "VALUES ('TM3 recon TM', 'tm3recon', 'en', 'nl')"
    )
    db.connection.commit()
    return db


def add(db, source, target):
    db.add_translation_unit(
        source=source, target=target, source_lang="en", target_lang="nl",
        tm_id="tm3recon",
    )


def long_text(lines, chars_per_line=90):
    """Текст, который в узкой колонке оборачивается в много строк."""
    word = "translation "
    return (" ".join(word for _ in range(chars_per_line // len(word) + 1)) + " ") * lines


def pump(app, times=5):
    for _ in range(times):
        app.processEvents()


# Константы высоты, совпадающие с планом BATCH TM3 (делегат задачи 3/1):
# ширина переноса = columnWidth - PAD_X, высота строки = doc height + PAD_Y.
PAD_X = 8
PAD_Y = 6


def expected_row_height(text, column_width, font):
    """Независимый расчёт высоты строки: перенос по QTextDocument с той же
    ширина и шрифтом, что у делегата."""
    from PyQt6.QtGui import QTextDocument
    doc = QTextDocument()
    doc.setDefaultFont(font)
    doc.setPlainText(text)
    doc.setTextWidth(max(10, column_width - PAD_X))
    return int(doc.size().height()) + PAD_Y


def count_glyph_pixels(image: QImage, rect, tol=60, shrink=3):
    """Число пикселей ВО ВНУТРЕННЕЙ области индикатора (рамка отрезана
    ``shrink`` пикселями с каждой стороны), чей цвет заметно отличается от
    ДОМИНИРУЮЩЕГО цвета внутренней области (заливки). Отметка ✓ = меньшинство
    пикселей другого цвета; чистая заливка = 0."""
    x0 = max(rect.left() + shrink, 0)
    x1 = min(rect.right() - shrink, image.width() - 1)
    y0 = max(rect.top() + shrink, 0)
    y1 = min(rect.bottom() - shrink, image.height() - 1)
    if x1 < x0 or y1 < y0:
        return -1
    counts = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = image.pixelColor(x, y).name()
            counts[c] = counts.get(c, 0) + 1
    dominant = max(counts, key=counts.get)
    dr, dg, db = (
        int(dominant[1:3], 16), int(dominant[3:5], 16), int(dominant[5:7], 16))
    total = sum(counts.values())
    dominant_share = counts[dominant]
    differing = total - dominant_share
    return differing, dominant, total


def indicator_rect(widget):
    from PyQt6.QtWidgets import QStyleOptionButton
    opt = QStyleOptionButton()
    widget.initStyleOption(opt)
    return widget.style().subElementRect(
        widget.style().SubElement.SE_CheckBoxIndicator, opt, widget)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # Прикладываем тему приложения, как это делает реальный запуск
    # (именно её stylesheet с QCheckBox::indicator:checked без отметки —
    # рабочая гипотеза 0b).
    from pathlib import Path as _Path
    theme = ThemeManager(user_data_path=_Path(PROFILE))
    theme.apply_theme(app)

    print("== R1 (0a) высота строк ==")
    db1 = make_db()
    add(db1, long_text(6), long_text(6))
    add(db1, long_text(3), long_text(4))
    add(db1, "short pair", "короткая пара")
    dialog = TMManagerDialog(None, db1, log_callback=lambda msg: None)
    table = dialog.browser_table
    hidden_colw = table.columnWidth(1)
    hidden_h0, hidden_h1 = table.rowHeight(0), table.rowHeight(1)

    # Воссоздаём «первое открытие вкладки»: таблица заполнялась в
    # конструкторе, пока всё скрыто; теперь показываем диалог (в приложении
    # подвкладка Browse All внутри вкладки TMs) — колонки Stretch получают
    # финальную ширину, а высоты строк остаются от скрытого состояния.
    dialog.show()
    dialog.resize(1000, 600)
    pump(app)
    # Ждём дебаунс высот (если он есть в проверяемом коде): на ДО-коде
    # таймера нет и заморозка остаётся, на ПОСЛЕ-коде высоты пересчитаются.
    from PyQt6.QtTest import QTest
    QTest.qWait(300)
    pump(app)
    colw = table.columnWidth(1)
    shown_h0, shown_h1 = table.rowHeight(0), table.rowHeight(1)
    src_item = table.item(0, 1)
    exp_h0 = expected_row_height(src_item.text(), colw, src_item.font())
    tgt_item = table.item(0, 2)
    exp_h1 = expected_row_height(tgt_item.text(), table.columnWidth(2), tgt_item.font())
    confirmed(
        "R1a первый показ: высоты НЕ пересчитаны (заморожены со скрытого "
        "состояния, ширины колонок изменились)",
        shown_h0 == hidden_h0 and shown_h1 == hidden_h1
        and colw != hidden_colw,
        f"row0: hidden {hidden_h0}px -> shown {shown_h0}px (без изменений), "
        f"row1: hidden {hidden_h1}px -> shown {shown_h1}px; "
        f"colWidth(Source): {hidden_colw}px -> {colw}px; "
        f"эталон (QTextDocument по финальной ширине): {exp_h0}px/{exp_h1}px",
    )

    # (б) изменение ширины окна: колонки Stretch расширяются, текст
    # занимает меньше строк, но высоты строк НЕ пересчитываются.
    dialog.resize(1700, 600)
    pump(app)
    QTest.qWait(300)
    pump(app)
    colw2 = table.columnWidth(1)
    stale_h0 = table.rowHeight(0)
    exp_h0b = expected_row_height(src_item.text(), colw2, src_item.font())
    confirmed(
        "R1b resize окна не пересчитывает высоты",
        stale_h0 > exp_h0b + 10,
        f"после расширения (colWidth={colw2}px) row0 остался {stale_h0}px, "
        f"эталон при новой ширине {exp_h0b}px",
    )
    dialog.hide()
    db1.connection.close()

    print("== R2 (0b) галка Whole words без отметки ==")
    plain = QCheckBox("Whole words")
    plain.show()
    pump(app)

    plain.setChecked(True)
    pump(app)
    img_checked = plain.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    rect = indicator_rect(plain)
    glyph_checked, fill_color, total_px = count_glyph_pixels(img_checked, rect)

    confirmed(
        "R2a обычный QCheckBox под темой: во включённом состоянии нет отметки ✓",
        glyph_checked <= 2,
        f"индикатор {rect.width()}x{rect.height()}, заливка {fill_color}, "
        f"пикселей-«меньшинства» (отметка): {glyph_checked} из {total_px}",
    )

    checkmark = CheckmarkCheckBox("Whole words")
    checkmark.show()
    pump(app)
    checkmark.setChecked(True)
    pump(app)
    img_cm = checkmark.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    rect_cm = indicator_rect(checkmark)
    cm_differing, cm_fill, cm_total = count_glyph_pixels(img_cm, rect_cm)
    confirmed(
        "R2b контроль: CheckmarkCheckBox рисует видимую отметку",
        cm_differing >= 5,
        f"заливка {cm_fill}, пикселей-«меньшинства» (белая галка): "
        f"{cm_differing} из {cm_total}",
    )
    plain.hide()
    checkmark.hide()

    print("== R3 (0c) правка ячейки не пишется в БД ==")
    db2 = make_db()
    add(db2, "editable source text", "редактируемый текст")
    dialog2 = TMManagerDialog(None, db2, log_callback=lambda msg: None)
    t2 = dialog2.browser_table
    flags_ok = all(
        bool(t2.item(r, c).flags() & Qt.ItemFlag.ItemIsEditable)
        for r in range(t2.rowCount()) for c in range(t2.columnCount())
    )
    delegate = t2.itemDelegateForColumn(1)
    confirmed(
        "R3a все ячейки редактируемы (включая ID/Usage/Modified), "
        "кастомного делегата нет",
        flags_ok and delegate is None,
        f"ItemIsEditable на всех ячейках: {flags_ok}; "
        f"itemDelegateForColumn(1): {delegate}",
    )

    item = t2.item(0, 1)
    edited = "EDITED-BY-RECON не сохраняется"
    item.setText(edited)
    pump(app)
    db2.cursor.execute("SELECT source_text FROM translation_units WHERE id = ?", (1,))
    db_text = db2.cursor.fetchone()[0]
    confirmed(
        "R3b правка текста ячейки НЕ пишется в БД",
        item.text() == edited and db_text == "editable source text",
        f"в item: {item.text()[:40]!r}; в БД: {db_text!r}",
    )
    dialog2.browser_tab.hide()
    db2.connection.close()

    print("== R4 (0d) tooltip на Source/Target ==")
    db3 = make_db()
    add(db3, "tooltip source " * 10, "tooltip target " * 10)
    dialog3 = TMManagerDialog(None, db3, log_callback=lambda msg: None)
    t3 = dialog3.browser_table
    tt_s = t3.item(0, 1).toolTip()
    tt_t = t3.item(0, 2).toolTip()
    confirmed(
        "R4 Source/Target несут полный текст в tooltip",
        bool(tt_s) and bool(tt_t),
        f"len(source tooltip)={len(tt_s)}, len(target tooltip)={len(tt_t)}",
    )
    dialog3.browser_tab.hide()
    db3.connection.close()

    print("== R5 (0e) встроение Browse All — статические факты (в отчёт) ==")
    print("  Supervertaler.py:10883-10904: tm_tabs (QTabWidget) внутри вкладки TMs;")
    print("  '📖 Browse All' = temp_manager.browser_tab из TMManagerDialog(self, db, log);")
    print("  экземпляр держится через tab._tm_manager; dialog.exec() НЕ вызывается.")
    print("  Операции со списком TM завершаются refresh_callback() (= refresh_tm_list):")
    print("   - create: Supervertaler.py:18197 (_show_create_tm_dialog)")
    print("   - import: Supervertaler.py:18639 (_import_tmx_as_tm)")
    print("   - delete: Supervertaler.py:18748 (_delete_tm -> tm_metadata_manager.delete_tm")
    print("     -> лог '✓ Deleted TM (ID: ...)' tm_metadata_manager.py:294)")
    print("   - контекстное меню (project TM / readonly): 11379/11388/11398")
    print("  refresh_tm_list сохранён как self.tm_tab_refresh_callback (11254).")
    print("  TMEditorDialog (_show_tm_editor_dialog, 18755) правит записи одной TM и")
    print("  по закрытию НЕ вызывает refresh_callback — ни TM List, ни Browse All.")
    print("  Match Panel: _match_panel_delete_tm_entry (33956) удаляет запись TM —")
    print("  тоже без refresh.")

    print("\nRecon done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
