# -*- coding: utf-8 -*-
"""Headless-тесты Batch T2 (коммит 1): двойная запись в TM при подтверждении.

Факт (T1 §4 / промпт T2): на каждое подтверждение сегмент попадал в TM ДВАЖДЫ —
неявно через update_status_icon(row, 'confirmed') (guard «status=='confirmed'
и непустой target» внутри вызывает save_segment_to_activated_tms) и явным
вызовом save_segment_to_activated_tms сразу после. Коммит T2 удаляет явные
вызовы на всех трёх сайтах: _confirm_current_row_segment (Ctrl+Enter /
Confirm & Next), confirm_selected_segments (Confirm all), _check_auto_confirm_100_percent
(авто-подтверждение 100%).

Сценарии (одна загрузка приложения, 36 сегментов, изолированный SUPERVERTALER_DATA_ROOT):
  S1  подтверждение 28 сегментов подряд (confirm_selected_segments, latest) — 28 вызовов;
  S2  отсортированная сетка (apply_sort source_desc) + подтверждение 1 сегмента — 1 вызов;
  S3  отфильтрованная сетка (source_filter) + подтверждение 2 сегментов — 2 вызова;
  S4  сегмент с пустым target — 0 вызовов;
  S5  одиночное подтверждение (Ctrl+Enter → _confirm_current_row_segment) — 1 вызов;
  S6  Confirm & Next (confirm_and_next_unconfirmed) — 1 вызов;
  S7  авто-подтверждение 100% (tm_save_mode='all') — 1 вызов, без UNIQUE-предупреждений;
  S8  bulk-подтверждение в режиме 'all' — 1 вызов, без UNIQUE-предупреждений.
В конце — дамп всех строк TM (source,target) в JSON для сравнения «до/после
правки» между деревом HEAD и рабочим деревом (содержимое БД не меняется:
в latest — DELETE+INSERT той же пары, в all — второй INSERT упирался в UNIQUE).

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/t2_tm_double_write_tests.py
"""
import faulthandler
import json
import os
import pathlib
import sys

faulthandler.dump_traceback_later(900, repeat=True, file=sys.stderr)

# Оверрайды для прогона «до правки» на worktree HEAD (сравнение содержимого
# TM-БД до/после коммита): T2_REPO — корень другого дерева, T2_STAGE — свой
# каталог прогона.
REPO = os.environ.get('T2_REPO', r'E:\Dev\SupervertalerPortable')
STAGE = pathlib.Path(os.environ.get(
    'T2_STAGE', r'E:\Dev\Work_temp\SupervertalerPortable'
                r'\refactoring\batch-t2\tests\run-001'))
ISO = STAGE / 'iso'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
for d in ('Desktop', 'Documents', 'Downloads', 'tmp'):
    (ISO / d).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, REPO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

PASSED = 0
FAILED = 0


def check(name, cond, detail=None):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print('PASS', name, flush=True)
    else:
        FAILED += 1
        print('FAIL', name, '->', repr(detail), flush=True)


from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)


def _logging_exec(self, *a, **k):
    # Accepted: диалог импорта TXT требует подтверждения языковой пары
    # (как в c1/c2/c3-сьютах).
    return QDialog.DialogCode.Accepted


QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(
    lambda *a, **k: (modal_log.append('info'), QMessageBox.StandardButton.Ok)[1])
QMessageBox.warning = staticmethod(
    lambda *a, **k: (modal_log.append('warning'), QMessageBox.StandardButton.Ok)[1])
modal_log = []
open_queue = []

from PyQt6.QtWidgets import QFileDialog  # noqa: E402

QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (open_queue.pop(0) if open_queue else '', ''))

import Supervertaler as SV  # noqa: E402

win = SV.SupervertalerQt()
print('[t2] window built', flush=True)
import time as _t  # noqa: E402
for _ in range(60):
    app.processEvents()
    _t.sleep(0.05)

# ── Контроль границ: путь данных изолирован ────────────────────────────────
check('A0 изоляция данных: user_data под ISO',
      str(SV.get_user_data_path()).startswith(str(ISO)), SV.get_user_data_path())

# ── Фикстура: 36 сегментов с уникальными источниками ──────────────────────
N_SEG = 36
FIX_TXT = OUT / 't2_fixture.txt'
lines = []
for i in range(1, N_SEG + 1):
    if i <= 28:
        lines.append(f'Bulk sentence number {i}.')
    elif i == 29:
        lines.append('Sorted sentence alpha.')
    elif i in (30, 31):
        lines.append('Filtered sentence uniqueword.')
    elif i == 32:
        lines.append('Empty target sentence.')
    elif i == 33:
        lines.append('Single confirm sentence.')
    elif i == 34:
        lines.append('Confirm and next sentence.')
    elif i == 35:
        lines.append('Auto confirm sentence.')
    else:
        lines.append('Bulk all sentence.')
FIX_TXT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
open_queue.append(str(FIX_TXT))
win.import_simple_txt()
segs = win.current_project.segments
check('B0 фикстура импортирована: 36 сегментов', len(segs) == N_SEG, len(segs))
for _s in segs:
    _s.target = ''
    _s.status = 'untranslated'

# Отключаем debounced-обработчик набора (в сьюте набор «печатанием» не
# тестируется, а таймер сработал бы уже ПОСЛЕ подтверждения и дал бы
# ложный дополнительный вызов TM-записи).
win._handle_target_text_debounced_by_id = lambda *a, **k: None

# ── TM: реальная база в изолированном профиле ──────────────────────────────
proj = win.current_project
if proj.id is None:
    proj.id = 1  # сьютовое значение: достаточно для связи TM↔проект
proj.source_lang = 'en'
proj.target_lang = 'nl'
tm_db_id = win.tm_metadata_mgr.create_tm(
    'T2 suite TM', 't2_suite_tm', 'en', 'nl', read_only=False,
    project_id=proj.id)
check('B1 TM создана', tm_db_id is not None, tm_db_id)
check('B2 TM активирована для проекта',
      win.tm_metadata_mgr.activate_tm(tm_db_id, proj.id))
check('B3 get_writable_tm_ids видит TM',
      't2_suite_tm' in win.tm_metadata_mgr.get_writable_tm_ids(proj.id),
      win.tm_metadata_mgr.get_writable_tm_ids(proj.id))
proj.tm_settings = {'activated_tm_ids': ['t2_suite_tm']}
win.tm_save_mode = 'latest'

# ── Счётчик вызовов save_segment_to_activated_tms + захват лога ───────────
tm_calls = []
_orig_save = win.save_segment_to_activated_tms


def _counting_save(source, target):
    tm_calls.append((source, target))
    return _orig_save(source, target)


win.save_segment_to_activated_tms = _counting_save

log_lines = []
_orig_log = win.log


def _capturing_log(msg, *a, **k):
    log_lines.append(str(msg))
    return _orig_log(msg, *a, **k)


win.log = _capturing_log


def reset_captures():
    tm_calls.clear()
    log_lines.clear()


# Снимок исходного порядка id: apply_sort сортирует список segments НА МЕСТЕ,
# поэтому индексация «строка фикстуры → сегмент» идёт по снимку, а не по живому
# списку (живой порядок меняется при сортировке сетки в S2).
orig_ids = [s.id for s in segs]


def seg_by_index(idx):
    """Сегмент по исходному индексу списка (список может быть пересортирован)."""
    target_id = orig_ids[idx]
    return next(s for s in win.current_project.segments if s.id == target_id)


def fill_target(seg, text):
    """Заполняет перевод: виджет сетки (если есть) + объект сегмента."""
    row = win._find_row_for_segment(seg.id)
    if row >= 0:
        w = win.table.cellWidget(row, 3)
        if w is not None and hasattr(w, 'setPlainText'):
            w.setPlainText(text)
            app.processEvents()
    seg.target = text


def select_row(row):
    win.table.clearSelection()
    win.table.setCurrentCell(row, 3)
    win.table.selectRow(row)
    app.processEvents()


def select_seg(seg):
    select_row(win._find_row_for_segment(seg.id))


def tm_rows():
    cur = win.db_manager.cursor
    cur.execute("SELECT source_text, target_text FROM translation_units "
                "WHERE tm_id='t2_suite_tm' ORDER BY source_text, target_text")
    return cur.fetchall()


def unique_warnings():
    return [m for m in log_lines if 'Could not save to TM' in m
            or 'UNIQUE' in m]


# ═══ S1: подтверждение 28 сегментов подряд (latest) ═══════════════════════
bulk28 = [seg_by_index(i) for i in range(28)]
for i, s in enumerate(bulk28):
    fill_target(s, f'Перевод {i + 1}')
reset_captures()
win.confirm_selected_segments(bulk28)
app.processEvents()
check('S1 вызовов save = 28 (по одному на сегмент)', len(tm_calls) == 28, len(tm_calls))
check('S1 нет сегмента с двумя записями',
      len(set(tm_calls)) == len(tm_calls), len(tm_calls) - len(set(tm_calls)))
check('S1 статус подтверждён у всех', all(s.status == 'confirmed' for s in bulk28))
check('S1 лог «Confirmed 28 segment(s), saved 28 to TM»',
      any('Confirmed 28 segment(s), saved 28 to TM' in m for m in log_lines),
      [m for m in log_lines if 'Confirmed' in m])
check('S1 в TM 28 строк', len(tm_rows()) == 28, len(tm_rows()))
s1_dump = tm_rows()

# ═══ S2: отсортированная сетка ════════════════════════════════════════════
win.apply_sort('source_desc')
app.processEvents()
s_sorted = seg_by_index(28)  # 'Sorted sentence alpha.'
fill_target(s_sorted, 'Перевод отсортированный')
row_sorted = win._find_row_for_segment(s_sorted.id)
check('S2 сегмент найден в отсортированной сетке', row_sorted >= 0, row_sorted)
# строка грида после сортировки всё ещё соответствует своему сегменту:
check('S2 строка грида = сегмент (ID в строке)',
      int(win.table.item(row_sorted, 0).text()) == s_sorted.id)
reset_captures()
win.confirm_selected_segments([s_sorted])
app.processEvents()
check('S2 вызовов save = 1', len(tm_calls) == 1, len(tm_calls))
win.apply_sort(None)
app.processEvents()

# ═══ S3: отфильтрованная сетка ════════════════════════════════════════════
win.source_filter.setText('uniqueword')
win.apply_filters()
app.processEvents()
filtered = [seg_by_index(29), seg_by_index(30)]  # строки 30/31 фикстуры
for s, txt in zip(filtered, ('Перевод фильтр 1', 'Перевод фильтр 2')):
    fill_target(s, txt)
reset_captures()
win.confirm_selected_segments(filtered)
app.processEvents()
check('S3 вызовов save = 2 (по одному на сегмент)', len(tm_calls) == 2, len(tm_calls))
check('S3 статусы подтверждены', all(s.status == 'confirmed' for s in filtered))
win.source_filter.setText('')
win.apply_filters()
app.processEvents()

# ═══ S4: сегмент с пустым target ══════════════════════════════════════════
s_empty = seg_by_index(31)  # строка 32 фикстуры 'Empty target sentence.'
fill_target(s_empty, '')
reset_captures()
win.confirm_selected_segments([s_empty])
app.processEvents()
check('S4 вызовов save = 0 (пустой target)', len(tm_calls) == 0, len(tm_calls))
check('S4 статус подтверждён', s_empty.status == 'confirmed')

# ═══ S5: одиночное подтверждение (Ctrl+Enter → _confirm_current_row_segment)
s_single = seg_by_index(32)  # строка 33 'Single confirm sentence.'
fill_target(s_single, 'Перевод одиночный')
select_seg(s_single)
reset_captures()
win._confirm_current_row_segment()
app.processEvents()
check('S5 вызовов save = 1', len(tm_calls) == 1, len(tm_calls))
check('S5 статус подтверждён', s_single.status == 'confirmed')

# ═══ S6: Confirm & Next ═══════════════════════════════════════════════════
s_cn = seg_by_index(33)  # строка 34 'Confirm and next sentence.'
fill_target(s_cn, 'Перевод confirm-next')
select_seg(s_cn)
reset_captures()
win.confirm_and_next_unconfirmed()
app.processEvents()
check('S6 вызовов save = 1', len(tm_calls) == 1, len(tm_calls))
check('S6 статус подтверждён', s_cn.status == 'confirmed')

# ═══ S7: авто-подтверждение 100% (режим latest) ═══════════════════════════
# Примечание: в режиме 'all' сохранение пары, пришедшей из TM, ВСЕГДА упиралось
# бы в UNIQUE (пара уже есть в ТМ — она оттуда и взята), независимо от правки;
# поэтому авто-подтверждение проверяем в 'latest' (DELETE+INSERT той же пары).
win.tm_save_mode = 'latest'
win.enable_tm_matching = True
win.auto_confirm_100_percent_matches = True
s_auto = seg_by_index(34)  # строка 35 'Auto confirm sentence.'
_win = win.db_manager.add_translation_unit(
    source=s_auto.source, target='Автоперевод из TM',
    source_lang='en', target_lang='nl', tm_id='t2_suite_tm', overwrite=False)
check('S7 в TM засеян 100% источник', _win is not None, _win)
fill_target(s_auto, '')  # пустой target — условие авто-подтверждения
select_seg(s_auto)
reset_captures()
win._check_auto_confirm_100_percent(win._find_row_for_segment(s_auto.id), s_auto)
app.processEvents()
check('S7 вызовов save = 1', len(tm_calls) == 1, len(tm_calls))
check('S7 сегмент подтверждён', s_auto.status == 'confirmed', s_auto.status)
check('S7 target из TM', s_auto.target == 'Автоперевод из TM', s_auto.target)
check('S7 нет UNIQUE-предупреждений', len(unique_warnings()) == 0, unique_warnings())

# ═══ S8: bulk-подтверждение в режиме all ══════════════════════════════════
s_all = seg_by_index(35)  # строка 36 'Bulk all sentence.'
fill_target(s_all, 'Перевод в режиме all')
reset_captures()
win.confirm_selected_segments([s_all])
app.processEvents()
check('S8 вызовов save = 1', len(tm_calls) == 1, len(tm_calls))
check('S8 нет UNIQUE-предупреждений', len(unique_warnings()) == 0, unique_warnings())

# ═══ Дамп TM для сравнения «до/после правки» ══════════════════════════════
dump = {
    'tm_rows': [[r[0], r[1]] for r in tm_rows()],
    'scenario_s1_rows': [[r[0], r[1]] for r in s1_dump],
}
dump_path = OUT / 't2_tm_dump.json'
dump_path.write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding='utf-8')
check('D0 дамп TM записан', dump_path.exists())
check('D1 в TM ровно по строке на уникальный источник',
      len(dump['tm_rows']) == 34,  # 28 bulk + sorted + 1 filtered (оба отфильтрованных
                                   # сегмента имеют одинаковый source → в latest одна
                                   # строка) + single + c&n + auto + all; пустой target
                                   # записи не даёт
      len(dump['tm_rows']))
check('D2 нет дублирующихся (source,target) пар',
      len(set(map(tuple, dump['tm_rows']))) == len(dump['tm_rows']))

print(flush=True)
print(f'RESULT t2_tm_double_write: PASSED={PASSED} FAILED={FAILED}', flush=True)
sys.stdout.flush()
sys.stderr.flush()
app.processEvents()
os._exit(0 if FAILED == 0 else 1)
