# -*- coding: utf-8 -*-
"""Headless-тесты Batch C2: защита от «перелива контекста».

Части:
  A — modules/prompt_markers.py: детектор looks_like_context_overflow.
      Таблица пар (source, response, ожидание), 34 строки: фикстуры
      FIXTURE_OVERFLOW_31 / FIXTURE_OK_32 / FIXTURE_OK_33 (эталонные ответы
      той же сессии nailong-9b), границы +1/+2/+3 абзацев, многоабзацные
      source (порог от числа абзацев source), правило длины (только в
      сочетании с превышением строк), русские/английские/пустые/пробельные.
  B — полное приложение: translate_current_segment (перелив -> повтор без
      блока контекста -> успех; оба ответа переливают -> пропуск,
      target/TM/undo/статус не тронуты; запрос уже без контекста -> сразу
      пропуск; эхо в повторе после перелива -> пропуск; ячейка таблицы
      (is_table=True) ведёт себя так же; undo в успехе = baseline обычного
      успеха). Заглушка LLM-клиента — как в c1.
  C — writer Tagged Text: перелившийся target (уже сохранённый до батча)
      даёт предупреждение «возможный перелив контекста (строка N)»;
      обычные targets — нет; без source_lines — нет (контракт CLI).

Регрессы c1 (33/0) и c11 (15/0) — отдельными прогонами (файлы сьютов),
результаты фиксируются в отчёте BATCH_C2_REPORT.md.

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/c2_context_overflow_tests.py
"""
import faulthandler
import os
import pathlib
import sys

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-c2\tests\run-001')
ISO = STAGE / 'iso'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'AppData' / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
for d in ('Desktop', 'Documents', 'Downloads', 'tmp'):
    (ISO / d).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, REPO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

# ═══ Фикстуры (эталонные ответы Дмитрия, промпт C2) ═══════════════════════
SRC_31 = 'Bridge Guards'
FIXTURE_OVERFLOW_31 = (
    'Охранники моста\n\n'
    'Союзные лучники на мосту считаются находящимися в плотном укрытии при '
    'защите подходов к мосту до тех пор, пока они не начнут движение или не '
    'подвергнутся атаке.\n\n'
    'Исторически шотландские лучники были размещены для охраны моста и вели '
    'огонь по англичанам, когда те пытались пересечь его.\n\n'
    'Убежище в церкви\n\n'
    'В первый раз, когда английская юнит пересекает мост, одна '
    'франко-шотландская пехотная юнит в пределах 6″ от церкви может совершить '
    'бесплатный ход прямо во внутреннее пространство церкви (если она там еще '
    'не находится).\n\n'
    'Это отсылает к короткому историческому эпизоду, когда защитники отступили '
    'вокруг церкви до того, как бой переместился дальше.')
SRC_32 = ('The allied bridge archers count as being in hard<br>cover while '
          'defending the bridge approaches<br>until they move or are charged.')
SRC_32_LF = SRC_32.replace('<br>', '\n')
FIXTURE_OK_32 = ('Союзные лучники на мосту считаются находящимися в плотном '
                 'укрытии при защите подходов к мосту до тех пор, пока они не '
                 'начнут движение или не подвергнутся атаке.')
SRC_33 = ('Historically, Scots archers<br>were posted to guard the<br>bridge '
          'and fired on the<br>English as they forced the<br>crossing.')
FIXTURE_OK_33 = ('Исторически шотландские лучники были размещены для охраны '
                 'моста и вели огонь по англичанам, когда те пытались '
                 'пересечь его.')

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


# ═══ Часть A: детектор — таблица пар ══════════════════════════════════════
from modules.prompt_markers import (  # noqa: E402
    count_paragraphs,
    looks_like_context_overflow,
)

_LONG_RU = 'Очень длинный абзац перевода этой короткой строки заголовка, ' * 5
_LONG_EN = 'A long legitimate translation paragraph for the short header ' * 5

PAIRS = [
    # (id, source, response, expected, note)
    ('A01', SRC_31, FIXTURE_OVERFLOW_31, True,
     'живой случай #31: 1 абзац против 6 (~700 знаков)'),
    ('A02', SRC_32, FIXTURE_OK_32, False,
     'FIXTURE_OK_32 (source с <br>) — нормальный ответ'),
    ('A03', SRC_32_LF, FIXTURE_OK_32, False,
     'FIXTURE_OK_32: source с LF (бывший <br>), ответ одной строкой'),
    ('A04', SRC_33, FIXTURE_OK_33, False,
     'FIXTURE_OK_33 — нормальный ответ'),
    ('A05', 'Single header line', _LONG_EN.strip(), False,
     'одна строка -> одна строка любой длины (en)'),
    ('A06', 'Короткий заголовок', _LONG_RU.strip(), False,
     'одна строка -> одна строка любой длины (ru)'),
    ('A07', 'Стр1\nСтр2\nСтр3', 'Пер1\nПер2\nПер3', False,
     'многострочный source, столько же абзацев'),
    ('A08', 'Стр1\nСтр2', 'Пер1\nПер2\nПер3', False,
     '+1 абзац (допуск: перевод разбил абзац)'),
    ('A09', 'Стр1\nСтр2\nСтр3', 'Пер1\nПер2', False,
     '-1 абзац (перевод склеил) — не перелив'),
    ('A10', 'Single line source here', 'а б в\nа б в\nа б в', False,
     '+2 абзаца — граница, ещё не перелив'),
    ('A11', 'Single line source here', 'а б в\nа б в\nа б в\nа б в', True,
     '+3 абзаца — перелив'),
    ('A12', SRC_31, '', False, 'пустой ответ — обрабатывает существующая логика'),
    ('A13', SRC_31, '   \n \n  ', False, 'пробельный ответ'),
    ('A14', '', 'Перевод', False, 'пустой source'),
    ('A15', '   ', '   ', False, 'оба пробельные'),
    ('A16', 'Стр1\nСтр2', 'Пер1\nПер2', False,
     'source с LF и ответ с тем же числом LF'),
    ('A17', SRC_31, 'Короткий.\n\nДлинный второй абзац перевода с большим '
     'количеством текста чтобы гарантированно набрать объём выше '
     'десятикратной длины короткого источника.', True,
     'правило длины: 13 знаков, 2 абзаца, 150 знаков >10x (130)'),
    ('A18', SRC_31, 'Короткий.\n\nВторой абзац покороче.', False,
     'правило длины не дотянуто (<10x) — не перелив'),
    ('A19', SRC_31, _LONG_RU.strip(), False,
     'правило длины БЕЗ превышения строк — не перелив (задача 1в)'),
    ('A20', 'S1\n\nS2\n\nS3', 'П1\n\nП2\n\nП3', False,
     'многоабзацный source (3), ответ 3 — совпадает'),
    ('A21', 'S1\n\nS2\n\nS3', 'П1\n\nП2\n\nП3\n\nП4', False,
     'многоабзацный source (3), +1'),
    ('A22', 'S1\n\nS2\n\nS3', 'П1\n\nП2\n\nП3\n\nП4\n\nП5', False,
     'многоабзацный source (3), +2 — не перелив'),
    ('A23', 'S1\n\nS2\n\nS3', 'П1\n\nП2\n\nП3\n\nП4\n\nП5\n\nП6', True,
     'многоабзацный source (3), +3 >= max(3, 3) — перелив'),
    ('A24', 'S1\n\nS2\n\nS3\n\nS4\n\nS5\n\nS6',
     '\n\n'.join('П%d' % k for k in range(1, 13)), True,
     'многоабзацный source (6), +6 >= max(3, 6) — перелив'),
    ('A25', 'S1\n\nS2\n\nS3\n\nS4\n\nS5\n\nS6',
     '\n\n'.join('П%d' % k for k in range(1, 11)), False,
     'многоабзацный source (6), +4 < 6 — не перелив'),
    ('A26', SRC_31, 'Охранники моста\n\n\n\nСоюзные лучники на мосту считаются '
     'находящимися в плотном укрытии при защите подходов к мосту до тех пор, '
     'пока они не начнут движение или не подвергнутся атаке, и далее ещё '
     'довольно много текста перевода соседних сегментов.', True,
     'пробельные строки между абзацами не считаются абзацами'),
    ('A27', 'Заголовок', 'Перевод заголовка.', False,
     'короткий source (9 знаков), ответ 19 знаков <10x, одна строка'),
    ('A28', 'Заголовок', 'Перевод.\n\nВторой абзац достаточно длинный чтобы '
     'точно пройти правило длины десять раз умноженное на короткий источник.',
     True, 'короткий source, 2 абзаца, 118 знаков >= 10x9'),
    ('A29', SRC_31, SRC_31, False, 'ответ = source (не перелив)'),
    ('A30', SRC_31, None, False, 'None-ответ'),
    ('A31', SRC_31, FIXTURE_OVERFLOW_31.strip(), True,
     'фикстура с обрезкой краёв — тот же вердикт'),
    ('A32', SRC_31, 'Охранники моста\n\n' + 'т' * 300, True,
     '2 абзаца, второй очень длинный (>10x) — правило длины'),
    ('A33', 'Товар\n\nПозиция\n\nКоличество', 'Позиция заказа', False,
     'многоабзацный source, ответ короче — не перелив'),
    ('A34', SRC_31, 'Охранники\nмоста', False,
     'перенос строки внутри одной строки-абзаца'),
]

for pid, src, resp, expected, note in PAIRS:
    got = looks_like_context_overflow(resp, src)
    check(f'{pid} {note}',
          got == expected,
          (got, expected,
           count_paragraphs(resp or ''), count_paragraphs(src)))

check('A-count таблица пар >= 25 строк', len(PAIRS) >= 25, len(PAIRS))
check('A-counts count_paragraphs(фикстура 31) == 6 и source == 1',
      count_paragraphs(FIXTURE_OVERFLOW_31) == 6
      and count_paragraphs(SRC_31) == 1,
      (count_paragraphs(FIXTURE_OVERFLOW_31), count_paragraphs(SRC_31)))

# ═══ Часть B: полное приложение ═══════════════════════════════════════════
import PyQt6.QtWidgets as QW  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog,  # noqa: E402
                             QMessageBox)

app = QApplication.instance() or QApplication(sys.argv)

modal_log = []


def _logging_exec(self, *a, **k):
    modal_log.append(f"QDialog.exec {type(self).__name__}")
    return QDialog.DialogCode.Accepted


QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(
    lambda *a, **k: (modal_log.append('info'), QMessageBox.StandardButton.Ok)[1])
QMessageBox.warning = staticmethod(
    lambda *a, **k: (modal_log.append('warning'), QMessageBox.StandardButton.Ok)[1])
QMessageBox.critical = staticmethod(
    lambda *a, **k: (modal_log.append('critical'), QMessageBox.StandardButton.Ok)[1])
save_queue = []
open_queue = []
QFileDialog.getSaveFileName = staticmethod(
    lambda *a, **k: (save_queue.pop(0) if save_queue else '', ''))
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (open_queue.pop(0) if open_queue else '', ''))

import Supervertaler as SV  # noqa: E402
from modules.llm_clients import LLMPromptEchoError  # noqa: E402

win = SV.SupervertalerQt()
print('[c2] window built', flush=True)
import time as _t  # noqa: E402
for _ in range(60):
    app.processEvents()
    _t.sleep(0.05)

# Фикстура проекта: 3 ОБЫЧНЫХ (не табличных) сегмента.
FIX_TXT = OUT / 'c2_fixture.txt'
FIX_TXT.write_text('Bridge Guards.\n'
                   'Goals and victory conditions.\n'
                   'Retreat to the camp at dusk.\n', encoding='utf-8')
open_queue.append(str(FIX_TXT))
win.import_simple_txt()
n_segs = len(win.current_project.segments)
check('B0 фикстура импортирована: 3 сегмента', n_segs == 3, n_segs)
for _s in win.current_project.segments:
    _s.target = ''
    _s.status = 'untranslated'

OK_31 = 'Охрана моста.'


class StubClient:
    """Заглушка LLM-клиента: сценарий ответов + журнал вызовов (стиль c1)."""
    supports_vision = False

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def translate(self, text, source_lang='en', target_lang='nl',
                  context=None, custom_prompt=None, max_tokens=None,
                  images=None, system_prompt=None, skip_cleaning=False,
                  enable_prompt_caching=False, detect_prompt_echo=False, **k):
        self.calls.append({'text': text, 'custom_prompt': custom_prompt,
                           'echo_flag': detect_prompt_echo})
        action = self.script.pop(0)
        if isinstance(action, Exception):
            raise action
        return action


def _select_row(win, row):
    win.table.clearSelection()
    idx = win.table.model().index(row, 0)
    win.table.selectionModel().setCurrentIndex(
        idx, win.table.selectionModel().SelectionFlag.ClearAndSelect)
    app.processEvents()


_logs = []
_orig_log = win.log
win.log = lambda msg: (_logs.append(msg), _orig_log(msg))[1]
undo_log = []
_orig_undo = win.record_undo_state
win.record_undo_state = lambda *a, **k: (undo_log.append(a),
                                         _orig_undo(*a, **k))[1]
tm_log = []
_orig_tm_save = win.save_segment_to_activated_tms
win.save_segment_to_activated_tms = lambda *a, **k: tm_log.append(a)
win._custom_llm_ready = lambda settings=None: True


def _run_translate(win, row):
    modal_log.clear()
    _logs.clear()
    undo_log.clear()
    tm_log.clear()
    _select_row(win, row)
    win.translate_current_segment()
    return win.current_project.segments[row]


# --- B1: перелив -> повтор без контекста -> успех (обычный сегмент) --------
seg1 = win.current_project.segments[0]
stub1 = StubClient([FIXTURE_OVERFLOW_31, OK_31])
win.create_llm_client = lambda *a, **k: stub1
seg1 = _run_translate(win, 0)
check('B1a два вызова', len(stub1.calls) == 2, len(stub1.calls))
check('B1b промт 1-го вызова С блоком SURROUNDING',
      'SURROUNDING SEGMENTS FOR CONTEXT' in stub1.calls[0]['custom_prompt'])
check('B1c промт 2-го вызова БЕЗ блока SURROUNDING',
      'SURROUNDING SEGMENTS FOR CONTEXT'
      not in stub1.calls[1]['custom_prompt'])
check('B1d оба вызова detect_prompt_echo=True',
      stub1.calls[0]['echo_flag'] and stub1.calls[1]['echo_flag'])
check('B1e в target второй ответ, статус draft',
      seg1.target == OK_31 and seg1.status == 'draft',
      (seg1.target[:30], seg1.status))
check('B1f в TM не пишется до подтверждения (save_segment_to_activated_tms'
      ' не вызван)', len(tm_log) == 0, len(tm_log))
check('B1g лог перелива: "context overflow ... retrying without context"',
      any('context overflow' in m and 'retrying without context' in m
          for m in _logs), _logs[-4:])

# Baseline обычного успеха: сколько undo-вызовов пишет путь перевода.
seg_b = win.current_project.segments[0]
seg_b.target = ''
seg_b.status = 'untranslated'
stub_plain = StubClient([OK_31])
win.create_llm_client = lambda *a, **k: stub_plain
seg_b = _run_translate(win, 0)
UNDO_BASELINE = len(undo_log)
check('B1h baseline обычного успеха: undo-вызовов > 0', UNDO_BASELINE > 0,
      UNDO_BASELINE)

# --- B2: оба ответа переливают -> пропуск ----------------------------------
seg2 = win.current_project.segments[1]
stub2 = StubClient([FIXTURE_OVERFLOW_31, FIXTURE_OVERFLOW_31])
win.create_llm_client = lambda *a, **k: stub2
seg2 = _run_translate(win, 1)
check('B2a ровно два вызова (один повтор без контекста)',
      len(stub2.calls) == 2, len(stub2.calls))
check('B2b повтор БЕЗ блока SURROUNDING',
      'SURROUNDING SEGMENTS FOR CONTEXT'
      not in stub2.calls[1]['custom_prompt'])
check('B2c target пуст', seg2.target == '', seg2.target[:40])
check('B2d статус прежний (untranslated)', seg2.status == 'untranslated',
      seg2.status)
check('B2e undo не писался', len(undo_log) == 0, len(undo_log))
check('B2f в TM не пишется', len(tm_log) == 0, len(tm_log))
check('B2g лог skip: "translation skipped (context overflow persists)"',
      any('translation skipped (context overflow persists)' in m
          for m in _logs), _logs[-4:])
check('B2h без модалок',
      not any('warning' in m or 'critical' in m for m in modal_log), modal_log)

# --- B3: запрос уже БЕЗ контекста -> сразу пропуск -------------------------
settings = win.load_general_settings()
settings['surrounding_segments'] = 0
win.save_general_settings(settings)
seg3 = win.current_project.segments[2]
stub3 = StubClient([FIXTURE_OVERFLOW_31])
win.create_llm_client = lambda *a, **k: stub3
seg3 = _run_translate(win, 2)
check('B3a ровно один вызов — повтора нет', len(stub3.calls) == 1,
      len(stub3.calls))
check('B3b target пуст', seg3.target == '', seg3.target[:40])
check('B3c статус прежний', seg3.status == 'untranslated', seg3.status)
check('B3d undo/TM не тронуты', len(undo_log) == 0 and len(tm_log) == 0,
      (len(undo_log), len(tm_log)))
check('B3e лог skip (context overflow)', any('translation skipped' in m
      for m in _logs), _logs[-3:])
check('B3f без модалок',
      not any('warning' in m or 'critical' in m for m in modal_log), modal_log)

# вернём контекст для остальных сценариев
settings['surrounding_segments'] = 5
win.save_general_settings(settings)

# --- B4: эхо в ПОВТОРЕ после перелива -> пропуск ---------------------------
seg3 = win.current_project.segments[2]
seg3.target = ''
seg3.status = 'untranslated'
stub4 = StubClient([FIXTURE_OVERFLOW_31, LLMPromptEchoError('echo')])
win.create_llm_client = lambda *a, **k: stub4
seg3 = _run_translate(win, 2)
check('B4a два вызова (перелив -> повтор -> эхо)',
      len(stub4.calls) == 2, len(stub4.calls))
check('B4b target пуст / статус прежний',
      seg3.target == '' and seg3.status == 'untranslated',
      (seg3.target[:30], seg3.status))
check('B4c undo/TM не тронуты', len(undo_log) == 0 and len(tm_log) == 0,
      (len(undo_log), len(tm_log)))
check('B4d лог skip', any('translation skipped' in m for m in _logs),
      _logs[-3:])
check('B4e без модалок',
      not any('warning' in m or 'critical' in m for m in modal_log), modal_log)

# --- B5: успех после перелива -> undo как у обычного успеха ----------------
seg3 = win.current_project.segments[2]
seg3.target = ''
seg3.status = 'untranslated'
stub5 = StubClient([FIXTURE_OVERFLOW_31, OK_31])
win.create_llm_client = lambda *a, **k: stub5
seg3 = _run_translate(win, 2)
check('B5a успех после перелива: undo-вызовов как в baseline обычного успеха',
      len(undo_log) == UNDO_BASELINE, (len(undo_log), UNDO_BASELINE))
check('B5b target записан', seg3.target == OK_31, seg3.target[:30])
check('B5c в TM не пишется', len(tm_log) == 0, len(tm_log))

# --- B6: ячейка таблицы (is_table=True) ведёт себя так же ------------------
seg1 = win.current_project.segments[0]
seg1.target = ''
seg1.status = 'untranslated'
seg1.is_table = True          # TABLE_CELL-сегмент (docling/docx-импорт)
seg1.table_info = (0, 0, 1)
stub6 = StubClient([FIXTURE_OVERFLOW_31, OK_31])
win.create_llm_client = lambda *a, **k: stub6
seg1 = _run_translate(win, 0)
check('B6a TABLE_CELL: два вызова, повтор без контекста',
      len(stub6.calls) == 2
      and 'SURROUNDING SEGMENTS FOR CONTEXT'
      not in stub6.calls[1]['custom_prompt'],
      len(stub6.calls))
check('B6b TABLE_CELL: target = чистый перевод',
      seg1.target == OK_31 and seg1.status == 'draft',
      (seg1.target[:30], seg1.status))
check('B6c TABLE_CELL: в TM не пишется', len(tm_log) == 0, len(tm_log))
seg1.is_table = False
seg1.table_info = None

# ═══ Часть C: writer Tagged Text ══════════════════════════════════════════
from modules.tagged_text.stylemap import StyleMap  # noqa: E402
from modules.tagged_text.writer import write_tagged_text  # noqa: E402


def _expand_source_lines(sources, outs):
    sl = []
    for s, o in zip(sources, outs):
        sl.extend([s] * (o.count('\n') + 1))
    return sl


segments = list(win.current_project.segments)
sources = [s.source for s in segments]
# C1: перелившийся target (6 абзацев при source в одну строку) в строке 1.
outs = [FIXTURE_OVERFLOW_31, 'Условия победы перечислены ниже.',
        'Отступление в лагерь в сумерках.']
md_text = '\n'.join(outs)
source_lines = _expand_source_lines(sources, outs)
check('C1 source_lines выровнены 1:1 с физическими строками md',
      len(source_lines) == len(md_text.split('\n')),
      (len(source_lines), len(md_text.split('\n'))))
data, report = write_tagged_text(
    md_text, style_map=StyleMap(), source_lines=source_lines)
check('C2 перелившийся target -> "возможный перелив контекста (строка 1)"',
      any('возможный перелив контекста (строка 1)' in w
          for w in report.warnings), report.warnings[:4])
# C3: обычные targets — предупреждений о переливе нет.
outs2 = ['Охрана моста.', 'Условия победы перечислены ниже.',
         'Отступление в лагерь в сумерках.']
md2 = '\n'.join(outs2)
sl2 = _expand_source_lines(sources, outs2)
data2, report2 = write_tagged_text(
    md2, style_map=StyleMap(), source_lines=sl2)
check('C3 обычные targets — предупреждений о переливе нет',
      not any('перелив' in w for w in report2.warnings), report2.warnings)
# C4: без source_lines — контракт CLI (предупреждений о переливе нет).
data3, report3 = write_tagged_text(md_text, style_map=StyleMap())
check('C4 без source_lines предупреждений о переливе нет',
      not any('перелив' in w for w in report3.warnings))
# C5: source с LF (бывший <br>) + легитимный перевод — предупреждений нет.
srcs_lf = [SRC_32_LF] + sources[1:]
outs5 = [FIXTURE_OK_32] + outs2[1:]
md5 = '\n'.join(outs5)
sl5 = _expand_source_lines(srcs_lf, outs5)
data5, report5 = write_tagged_text(
    md5, style_map=StyleMap(), source_lines=sl5)
check('C5 source с LF + легитимный перевод — предупреждений нет',
      not any('перелив' in w for w in report5.warnings), report5.warnings)

print(f'[c2] done: {PASSED} passed / {FAILED} failed', flush=True)
os._exit(0 if FAILED == 0 else 1)
