# -*- coding: utf-8 -*-
"""Headless-тесты Batch I2 (+ I2.1): окно «роль → имя стиля» + хендлер
export_tagged_txt.

Offscreen, модалки подменены (по образцу batch-p1b_batch8-15_regress_common.py):
QDialog.exec → Accepted, QMessageBox.* → запись в журнал, QFileDialog → очередь
путей. Полный хендлер проверяется на двух реальных md (docling и PyMuPDF4LLM):
проект из md → export_tagged_txt → побайтовое сравнение с CLI-выходом
python -m modules.tagged_text того же исходника (при пустом переводе
используется правило шага 0а: цели = источникам в тесте; фолбэк «исходник»
даёт те же строки).

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u i2_export_tests.py > i2.out 2>&1

Финальные прогоны: run-003 (I2, 32/0, 2026-11-07), run-005 (I2.1, 39/0,
2026-11-08 — +A18–A23 статусная строка Save/Load; run-002 задокументирован
в BATCH_I2_REPORT.md s4: B9 переведён на CLI с той же картой серии).
"""
import faulthandler
import hashlib
import json
import os
import pathlib
import subprocess
import sys

faulthandler.dump_traceback_later(90, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-i2\tests\run-005')
ISO = STAGE / 'iso'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)

MD_DOCLING = (r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out\docling'
              r'\4164e8d8a0ef6c4df4142b7d9dc49a7f\Input.md')
MD_PYMUPDF = (r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out'
              r'\PyMuPDF4LLM\pymupdf4llm_gui_x0bf0ve2\Input.md')

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'AppData' / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)  # seam: data root = <iso>/Supervertaler
for d in ('Desktop', 'Documents', 'Downloads'):
    (ISO / d).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, REPO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import PyQt6.QtWidgets as QW  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog,  # noqa: E402
                             QMessageBox, QTableWidgetItem)

# --- нейтрализация модалок с журналом ---
modal_log = []
_real_exec = QDialog.exec


def _logging_exec(self, *a, **k):
    modal_log.append(f"QDialog.exec {type(self).__name__} '{self.windowTitle()}'")
    return QDialog.DialogCode.Accepted


QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(
    lambda *a, **k: (modal_log.append(f"info '{a[1] if len(a) > 1 else k.get('title', '')}'"),
                     QMessageBox.StandardButton.Ok)[1])
QMessageBox.warning = staticmethod(
    lambda *a, **k: (modal_log.append(f"warning '{a[1] if len(a) > 1 else k.get('title', '')}'"),
                     QMessageBox.StandardButton.Ok)[1])
QMessageBox.critical = staticmethod(
    lambda *a, **k: (modal_log.append(f"critical '{a[1] if len(a) > 1 else k.get('title', '')}'"),
                     QMessageBox.StandardButton.Ok)[1])

save_queue = []
open_queue = []
QFileDialog.getSaveFileName = staticmethod(
    lambda *a, **k: (save_queue.pop(0) if save_queue else '', ''))
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (open_queue.pop(0) if open_queue else '', ''))
QFileDialog.getExistingDirectory = staticmethod(
    lambda *a, **k: (save_queue.pop(0) if save_queue else ''))

PASSED = 0
FAILED = 0


def check(name, cond, detail=''):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f'PASS {name}', flush=True)
    else:
        FAILED += 1
        print(f'FAIL {name} {detail}', flush=True)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


app = QApplication(sys.argv)

# ═══ Часть A: диалог (без полного приложения) ═══════════════════════════
from modules.tagged_text.stylemap import StyleMap, load as load_stylemap, save as save_stylemap  # noqa: E402
from modules.tagged_text_export_dialog import (  # noqa: E402
    TaggedTextExportDialog, list_series, series_path)

MAPS = str(ISO / 'Supervertaler' / 'mapping')

dlg = TaggedTextExportDialog(StyleMap(), images_dir='', series_name='',
                             series_names=(), maps_dir=MAPS)
check('A1 таблица: 11 строк (8 ролей + 3 символьных)',
      dlg.table.rowCount() == 11, dlg.table.rowCount())
check('A2 дефолт h1 -> h1',
      dlg.table.item(0, dlg.COL_STYLE).text() == 'h1')
check('A3 дефолт table_row -> table_row',
      dlg.table.item(7, dlg.COL_STYLE).text() == 'table_row')
check('A4 дефолт char Bold/Italic/BoldItalic',
      [dlg.table.item(r, dlg.COL_STYLE).text() for r in (8, 9, 10)]
      == ['Bold', 'Italic', 'BoldItalic'])

dlg.table.setItem(0, dlg.COL_STYLE, QTableWidgetItem('Заголовок 1'))
dlg.table.setItem(8, dlg.COL_STYLE, QTableWidgetItem('Группа:Жирный'))
sm = dlg.style_map()
check('A5 style_map(): правки читаются',
      sm.para_name('h1') == 'Заголовок 1' and sm.char_name('bold') == 'Группа:Жирный')
check('A6 style_map(): остальные роли по умолчанию',
      sm.para_name('p') == 'p' and sm.char_name('italic') == 'Italic')

dlg._reset_defaults()
check('A7 Сбросить -> дефолты',
      dlg.style_map().para_name('h1') == 'h1'
      and dlg.style_map().char_name('bold') == 'Bold')

dlg.table.setItem(0, dlg.COL_STYLE, QTableWidgetItem('   '))
n_modals = len(modal_log)
dlg._validate_and_accept()
check('A8 пустое имя стиля -> не принято, предупреждение',
      dlg.result() != QDialog.DialogCode.Accepted
      and any("warning 'Export InDesign Tagged Text'" in m
              for m in modal_log[n_modals:]), modal_log[n_modals:])

dlg.table.setItem(0, dlg.COL_STYLE, QTableWidgetItem('H1'))
dlg._validate_and_accept()
check('A9 все имена заполнены -> принято', dlg.result() == QDialog.DialogCode.Accepted)

check('A10 имя серии с \\ / : -> ошибка валидации',
      all(TaggedTextExportDialog._series_error(s) for s in
          ('a\\b', 'a/b', 'a:b', 'a*b', 'a?b', 'a"b', 'a<b', 'a>b', 'a|b'))
      and TaggedTextExportDialog._series_error('') is not None
      and TaggedTextExportDialog._series_error('.hidden') is not None
      and TaggedTextExportDialog._series_error('Моя серия 2') is None)

dlg2 = TaggedTextExportDialog(StyleMap(), images_dir='', series_name='Test2',
                              series_names=(), maps_dir=MAPS)
dlg2._save_series()
check('A11 сохранение серии: файл <data_root>\\mapping\\Test2.tagmap.json',
      os.path.isfile(series_path(MAPS, 'Test2')))
loaded, load_warnings = load_stylemap(series_path(MAPS, 'Test2'))
check('A12 кругосветка: сохранённые имена читаются',
      loaded.para_name('h1') == 'h1' and not load_warnings)

save_stylemap(series_path(MAPS, 'Custom'), StyleMap(
    paragraph_styles={'h1': 'Заголовок 1', 'h2': 'Заголовок 2'},
    char_styles={'bold': 'Сильный'}))
dlg3 = TaggedTextExportDialog(StyleMap(), images_dir='', series_name='',
                              series_names=list_series(MAPS), maps_dir=MAPS)
check('A13 выбор серии из комбобокса',
      dlg3.series_combo.count() == 1 + len(list_series(MAPS)),
      dlg3.series_combo.count())
idx = dlg3.series_combo.findText('Custom')
dlg3.series_combo.setCurrentIndex(idx)
check('A14 выбор серии загружает карту в таблицу',
      dlg3.table.item(0, dlg3.COL_STYLE).text() == 'Заголовок 1'
      and dlg3.table.item(1, dlg3.COL_STYLE).text() == 'Заголовок 2'
      and dlg3.table.item(8, dlg3.COL_STYLE).text() == 'Сильный')

dlg4 = TaggedTextExportDialog(StyleMap(), images_dir='', series_name='',
                              series_names=(), maps_dir=str(ISO / 'no-such-maps'))
check('A15 чистая установка: диалог открывается без ошибок',
      dlg4.series_combo.count() == 1 and list_series(str(ISO / 'no-such-maps')) == [])

dlg5 = TaggedTextExportDialog(StyleMap(), images_dir='E:\\some\\images',
                              series_name='', series_names=(), maps_dir=MAPS)
check('A16 доступ images_dir/series_name/use_source_fallback',
      dlg5.images_dir() == 'E:\\some\\images'
      and dlg5.series_name() == ''
      and dlg5.use_source_fallback() is True)
dlg5.use_empty_radio.setChecked(True)
dlg5.use_source_radio.setChecked(False)
check('A17 переключатель непереведённых: пусто',
      dlg5.use_source_fallback() is False)

# A18–A23: немодальная статусная строка (Batch I2.1, T-I2c)
dlg6 = TaggedTextExportDialog(StyleMap(), images_dir='', series_name='',
                              series_names=(), maps_dir=MAPS)
n_modals = len(modal_log)
dlg6._save_series()
check('A18 Save с пустым именем -> статус-ошибка «Введите имя серии», без модалок',
      dlg6.status_label.text() == 'Enter a mapping set name first.'
      and dlg6.status_is_error()
      and len(modal_log) == n_modals, dlg6.status_label.text())

dlg6.series_edit.setText('StatusSeries')
check('A19 статус сброшен при смене имени серии',
      dlg6.status_label.text() == '' and not dlg6.status_is_error())

n_modals = len(modal_log)
dlg6._save_series()
check('A20 Save ok -> «Saved: <полный путь>», без модалок',
      dlg6.status_label.text() == 'Saved: ' + series_path(MAPS, 'StatusSeries')
      and not dlg6.status_is_error()
      and len(modal_log) == n_modals, dlg6.status_label.text())
check('A20b файл серии создан', os.path.isfile(series_path(MAPS, 'StatusSeries')))

dlg6._load_series()
check('A21 Load существующей -> «Loaded: <серия>»',
      dlg6.status_label.text() == 'Loaded: StatusSeries'
      and not dlg6.status_is_error(), dlg6.status_label.text())

dlg6.series_edit.setText('NoSuchSeries')
dlg6._load_series()
check('A22 Load отсутствующей -> статус-ошибка, без модалок',
      dlg6.status_label.text().startswith('Mapping set not found:')
      and dlg6.status_is_error(), dlg6.status_label.text())

n_modals = len(modal_log)
dlg6.series_edit.setText('')
dlg6._load_series()
check('A23 Load с пустым именем -> статус-ошибка, без NameError/модалок (фикс I2)',
      dlg6.status_label.text() == 'Enter a mapping set name.'
      and dlg6.status_is_error()
      and len(modal_log) == n_modals, dlg6.status_label.text())

# ═══ Часть B: полное приложение и хендлер ═══════════════════════════════
import Supervertaler as SV  # noqa: E402

win = SV.SupervertalerQt()
print('[i2] window built', flush=True)
import time as _t  # noqa: E402
for _ in range(60):
    app.processEvents()
    _t.sleep(0.05)

# B0 пункт меню: существует, подписан, подключён к export_tagged_txt
from PyQt6.QtGui import QAction  # noqa: E402
actions = [a for a in win.findChildren(QAction)
           if a.text() == 'InDesign &Tagged Text (TXT)...']
check('B0 пункт меню InDesign Tagged Text существует',
      len(actions) == 1, [a.text() for a in win.findChildren(QAction)
                          if 'Tagged' in a.text()])

# B1 пустой проект -> предупреждение, без диалогов
win.current_project = None
n_modals = len(modal_log)
win.export_tagged_txt()
check('B1 нет проекта -> предупреждение "No Project"',
      any("warning 'No Project'" in m for m in modal_log[n_modals:]))

# B2 документ из md docling -> экспорт -> байт-в-байт с CLI
open_queue.append(MD_DOCLING)
win.import_simple_txt()
n_docling = len(win.current_project.segments)
check('B2 импорт docling: сегменты есть, путь исходника сохранён',
      n_docling > 0
      and win.current_project.original_txt_path == MD_DOCLING, n_docling)
for seg in win.current_project.segments:
    seg.target = seg.source  # правило пустого перевода шага 0а (тест)

out_docling = str(OUT / 'docling_gui.tagged.txt')
save_queue.append(out_docling)
n_modals = len(modal_log)
win.export_tagged_txt()
check('B3 хендлер: окно соответствий и окно отчёта открыты',
      any("'Export InDesign Tagged Text'" in m for m in modal_log[n_modals:])
      and any("'InDesign Tagged Text Export Report" in m
              for m in modal_log[n_modals:]), modal_log[n_modals:])
check('B4 файл записан (UTF-16LE+BOM)',
      os.path.isfile(out_docling)
      and pathlib.Path(out_docling).read_bytes()[:2] == b'\xff\xfe')

cli_docling = str(OUT / 'docling_cli.tagged.txt')
r = subprocess.run([sys.executable, '-m', 'modules.tagged_text',
                    MD_DOCLING, cli_docling], cwd=REPO, capture_output=True)
check('B5 docling: GUI-экспорт == CLI-выход (байт-в-байт)',
      r.returncode == 0 and sha(out_docling) == sha(cli_docling),
      (r.returncode, sha(out_docling)[:16], sha(cli_docling)[:16]))

# B6 последние серия/папка попали в settings.json (seam data root)
settings = win.load_general_settings()
check('B6 settings.json: ключи tagged_text_last_*',
      'tagged_text_last_series' in settings
      and 'tagged_text_last_images_dir' in settings,
      sorted(k for k in settings if 'tagged' in k))
mapping_dir = pathlib.Path(MAPS)
check('B6b папка mapping создана только внутри data root',
      mapping_dir.is_dir() and str(mapping_dir).startswith(str(ISO / 'Supervertaler')))

# B7 несохранённые серии: pre-save карта -> settings -> экспорт применяет имена
save_stylemap(series_path(MAPS, 'MyMap'), StyleMap(
    paragraph_styles={'h1': 'Глава'})
)
settings = win.load_general_settings()
settings['tagged_text_last_series'] = 'MyMap'
settings['tagged_text_last_images_dir'] = ''
win.save_general_settings(settings)

open_queue.append(MD_PYMUPDF)
win.import_simple_txt()
n_pymupdf = len(win.current_project.segments)
check('B7 импорт pymupdf4llm: сегменты есть', n_pymupdf > 0, n_pymupdf)
for seg in win.current_project.segments:
    seg.target = seg.source

out_pymupdf = str(OUT / 'pymupdf_gui.tagged.txt')
save_queue.append(out_pymupdf)
win.export_tagged_txt()
check('B8 pymupdf: файл записан', os.path.isfile(out_pymupdf))

# --- Batch T1 (коммит 1): нормализация таблиц входа CLI для B9 ---
# GUI-экспорт собирает таблицы канонически (build_table_row/
# build_table_separator — решение TBL1.0 п.4), поэтому CLI-выход сравнивается
# с GUI на входе с ТАК ЖЕ нормализованными таблицами (строки данных
# пересобраны build_table_row(ячейки), после строки заголовка вставлен
# build_table_separator(число ячеек заголовка); все остальные строки —
# байт-в-байт, EOL исходника сохранён). Само сравнение — строгое байт-в-байт.
from modules.md_table_cells import (find_table_blocks, is_table_separator,  # noqa: E402
                                    split_table_row, build_table_row,
                                    build_table_separator)


def _eol_of(line):
    for e in ('\r\n', '\n', '\r'):
        if line.endswith(e):
            return e
    return ''


def normalize_md_tables(lines):
    """Канонизация md-таблиц (Batch T1): блоки find_table_blocks, строки
    данных -> build_table_row, разделитель после заголовка ->
    build_table_separator(n_cols_header); не-табличные строки без изменений."""
    out = []
    blocks = iter(find_table_blocks(lines))
    cur = next(blocks, None)
    i, n = 0, len(lines)
    while i < n:
        if cur is not None and i == cur.start:
            row_idx = 0
            for j in range(cur.start, cur.end + 1):
                eol = _eol_of(lines[j])
                if is_table_separator(lines[j]):
                    continue  # исходный разделитель заменяется каноническим
                cells = split_table_row(lines[j])
                out.append(build_table_row(cells) + eol)
                if cur.header and row_idx == 0:
                    out.append(build_table_separator(cur.n_cols_header) + eol)
                row_idx += 1
            i = cur.end + 1
            cur = next(blocks, None)
            continue
        out.append(lines[i])
        i += 1
    return out


# CLI идёт с ТОЙ ЖЕ картой серии MyMap (GUI применил её из settings),
# поэтому сравнение байт-в-байт корректно.
cli_pymupdf = str(OUT / 'pymupdf_cli.tagged.txt')
norm_pymupdf = OUT / 'pymupdf_cli_input_norm.md'
norm_pymupdf.write_text(
    ''.join(normalize_md_tables(
        pathlib.Path(MD_PYMUPDF).read_text(encoding='utf-8')
        .splitlines(keepends=True))),
    encoding='utf-8', newline='')
r = subprocess.run([sys.executable, '-m', 'modules.tagged_text',
                    str(norm_pymupdf), cli_pymupdf,
                    '--map', series_path(MAPS, 'MyMap')],
                   cwd=REPO, capture_output=True)
check('B9 pymupdf: GUI-экспорт == CLI-выход с картой MyMap (байт-в-байт)',
      r.returncode == 0 and sha(out_pymupdf) == sha(cli_pymupdf),
      (r.returncode,))

text = pathlib.Path(out_pymupdf).read_bytes().decode('utf-16')
check('B10 карта серии применена: <ParaStyle:Глава> у h1',
      '<ParaStyle:Глава>' in text and '<DefineParaStyle:Глава=' in text)

# B11 правило пустого перевода: 0 переводов -> предупреждение, файл не пишется
for seg in win.current_project.segments:
    seg.target = ''
no_out = str(OUT / 'must_not_exist.tagged.txt')
save_queue.append(no_out)
n_modals = len(modal_log)
win.export_tagged_txt()
check('B11 ноль переводов -> "No Translations", файл не создан',
      any("warning 'No Translations'" in m for m in modal_log[n_modals:])
      and not os.path.isfile(no_out), modal_log[n_modals:])

# B12 серия сохранена из диалога хендлера и видна в списке
check('B12 список серий содержит Test2 и MyMap',
      set(list_series(MAPS)) >= {'Test2', 'MyMap'}, list_series(MAPS))

# B13 settings после экспорта: последняя серия и папка обновлены
settings = win.load_general_settings()
check('B13 last_series сохранился (из диалога, авто-accept)',
      settings.get('tagged_text_last_series') == 'MyMap',
      settings.get('tagged_text_last_series'))

print(f'I2-TESTS: {PASSED} passed / {FAILED} failed', flush=True)
print(f'I2-MODALS: {len(modal_log)}', flush=True)
if FAILED:
    print('FAILED ITEMS:', flush=True)
os._exit(1 if FAILED else 0)
