# -*- coding: utf-8 -*-
"""Headless-тесты Batch C3: остатки каркаса промта в переводе.

Части:
  A — modules/prompt_markers.py: strip_prompt_leaks. Таблица пар
      (source, response, segment_number, ожидание), 39 строк: эталоны
      F1–F4 промпта BATCH C3 (живые случаи nailong-9b), границы правил
      (в)/(б)/(а), FP-заслоны (десятичная дробь, source с числом, строчные/
      цифры/точки в скобках, вложенные скобки, заголовок >40, скобки <10
      знаков, каркас без двоеточия и без **), русские и английские.
  B — полное приложение: translate_current_segment (F1-цепочка «эхо-каркас
      -> повтор -> F1»; F2/F3; ответ целиком каркас -> повтор без контекста;
      каркас и в повторе -> пропуск; обычный ответ не меняется; без контекста
      -> сразу пропуск; F2 в ответе эхо-повтора C1; F2 в ответе
      перелив-повтора C2). Заглушка LLM-клиента — как в c1/c2.
  C — экспорт Tagged Text: предпроход по сегментам (коммит 3): ячейка-перелив
      -> «возможный перелив контекста (ячейка, сегмент #N)»; ячейка-эхо ->
      «похоже на эхо промта (ячейка, сегмент #N)»; остатки разметки ->
      «остатки разметки промта в переводе (сегмент #N)»; обычный перелив —
      писателем, без дубля; чистый проект — без новых предупреждений; файл
      записан (UTF-16LE BOM), target предпроходом не меняется.

Регрессы c1 (33/0), c2 (75/0), c11 (15/0), i2 (39/0) — отдельными прогонами
(файлы сьютов), результаты фиксируются в отчёте BATCH_C3_REPORT.md.

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/c3_prompt_leaks_tests.py
"""
import faulthandler
import os
import pathlib
import sys

faulthandler.dump_traceback_later(240, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-c3\tests\run-002')
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


# ═══ Часть A: strip_prompt_leaks — таблица пар ════════════════════════════
from modules.prompt_markers import strip_prompt_leaks  # noqa: E402

F1_SRC = '## ANTIDOTE TO THE ENGLISH'
F1_RESP = ('## ПРОТИВОЯД ДЛЯ АНГЛИЙСКОГО\n\n'
           '**ВАШ ПЕРЕВОД (укажите ТОЛЬКО переведённый текст, '
           'без нумерации или меток):**')
F1_EXPECT = '## ПРОТИВОЯД ДЛЯ АНГЛИЙСКОГО'
F1_EN_RESP = ('## ANTIDOTE TO THE ENGLISH\n\n'
              '**YOUR TRANSLATION (provide ONLY the translated text, '
              'no numbering or labels):**')
F1_EN_EXPECT = '## ANTIDOTE TO THE ENGLISH'

PAIRS = [
    # (id, source, response, segment_number, ожидание-text, note)
    ('P01', F1_SRC, F1_RESP, 1, F1_EXPECT,
     'F1: метка-инструкция срезана, заголовок остался'),
    ('P02', F1_SRC, F1_EN_RESP, 1, F1_EN_EXPECT,
     'F1-EN: английская каркас-строка'),
    ('P03', 'ENGLISH', '8. АНГЛИЧАНЕ', 8, 'АНГЛИЧАНЕ',
     'F2: префикс номера «8.» срезан'),
    ('P04', 'ENGLISH', '8. АНГЛИЙЦЫ', 8, 'АНГЛИЙЦЫ',
     'F2-вариант: «АНГЛИЙЦЫ»'),
    ('P05', '**ENGLISH**', '8. **АНГЛИЧАНЕ** [ПЕРЕВЕСТИ ЭТО]', 8,
     '**АНГЛИЧАНЕ**', 'F3: номер + метка «[ПЕРЕВЕСТИ ЭТО]»'),
    ('P06', '8. First item', '8. Первый пункт', 8, '8. Первый пункт',
     'F4а: source сам с «8.» — не трогать'),
    ('P07', '3. Chapter', '3. Глава', 8, '3. Глава',
     'F4б: source с другим номером «3.» — не трогать'),
    ('P08', 'Hello [sic]', 'Привет [sic]', 1, 'Привет [sic]',
     'F4в: строчные буквы в скобках — не метка'),
    ('P09', 'Заключение:', 'Итог перевода.', 5, 'Итог перевода.',
     'обычный ответ без утечек — без изменений'),
    ('P10', 'Table of contents', '8. Оглавление', 3, '8. Оглавление',
     'номер в ответе != номеру сегмента — не трогать'),
    ('P11', 'ENGLISH', '8.АНГЛИЧАНЕ', 8, 'АНГЛИЧАНЕ',
     '«8.» без пробела — срезается'),
    ('P12', 'ENGLISH', '8.5 см в ширину', 8, '8.5 см в ширину',
     'десятичная дробь «8.5» — не срезается'),
    ('P13', 'ENGLISH', '8. АНГЛИЧАНЕ [ПЕРЕВЕСТИ]', 8, 'АНГЛИЧАНЕ',
     'метка [ПЕРЕВЕСТИ] одним словом'),
    ('P14', 'ENGLISH', '8. АНГЛИЧАНЕ [TRANSLATE THIS]', 8, 'АНГЛИЧАНЕ',
     'метка [TRANSLATE THIS]'),
    ('P15', 'ENGLISH', '8. АНГЛИЧАНЕ [ПЕРЕВЕСТИ-ЭТО]', 8, 'АНГЛИЧАНЕ',
     'метка с дефисом внутри слова'),
    ('P16', 'ENGLISH', '8. АНГЛИЧАНЕ [ПЕРЕВЕДИ 2]', 8,
     'АНГЛИЧАНЕ [ПЕРЕВЕДИ 2]',
     'цифры внутри скобок — метка не срезается, номер срезается'),
    ('P17', 'ENGLISH', '8. АНГЛИЧАНЕ [см. приложение]', 8,
     'АНГЛИЧАНЕ [см. приложение]',
     'точка/строчные внутри — метка не срезается, номер срезается'),
    ('P18', 'См. [приложение 1]', 'Смотрите [приложение 1]', 1,
     'Смотрите [приложение 1]',
     'source оканчивается «]» — правило (б) выключено'),
    ('P19', 'Список', 'А. Первый\nБ. Второй\nВ. Третий', 2,
     'А. Первый\nБ. Второй\nВ. Третий',
     'нумерованный список A/B/C — не трогать'),
    ('P20', 'Chapter title', 'Название главы\n\nВАШ ОТВЕТ (дайте только '
     'перевод, без пояснений):', 4, 'Название главы',
     'каркас-строка без ** — срезается'),
    ('P21', 'Chapter title', 'Название главы (см. примечания ниже)', 4,
     'Название главы (см. примечания ниже)',
     'подстрочная скобка внутри текста — не срезается'),
    ('P22', 'Bridge Guards', 'Охрана моста.\n\n'
     '**ВАШ ПЕРЕВОД (укажите ТОЛЬКО переведённый текст, '
     'без нумерации или меток):**\n\n', 2, 'Охрана моста.',
     'метка в конце с хвостовыми пустыми строками'),
    ('P23', 'Bridge Guards', '**ВАШ ПЕРЕВОД (укажите ТОЛЬКО переведённый '
     'текст, без нумерации или меток):**', 2, '',
     'ответ целиком каркас -> пусто (эхо)'),
    ('P24', 'Bridge Guards', '8.', 8, '', 'ответ целиком номер -> пусто'),
    ('P25', 'ENGLISH', '8. АНГЛИЧАНЕ\n\n**ВАШ ПЕРЕВОД (укажите ТОЛЬКО '
     'переведённый текст, без нумерации или меток):**', 8, 'АНГЛИЧАНЕ',
     'два правила: номер + каркас-строка'),
    ('P26', 'ENGLISH', '8. АНГЛИЧАНЕ [ПЕРЕВЕСТИ ЭТО]\n\n**ВАШ ПЕРЕВОД '
     '(укажите ТОЛЬКО переведённый текст, без нумерации или меток):**', 8,
     'АНГЛИЧАНЕ', 'три правила: каркас-строка + метка + номер'),
    ('P27', 'Вложенные [скобки [внутри]]', 'Перевод [скобки [внутри]]', 1,
     'Перевод [скобки [внутри]]', 'вложенные скобки — не трогать'),
    ('P28', 'Very long header section', 'ПЕРЕВЕСТИ\n\nПеревод этой '
     'строки полностью.', 9, 'ПЕРЕВЕСТИ\n\nПеревод этой строки полностью.',
     '«ПЕРЕВЕСТИ» не последняя строка целиком-инструкцией (нет скобок) — не трогать'),
    ('P29', 'Header', 'Перевод.\n\n**ВАШ ПЕРЕВОД (кратко):**', 7,
     'Перевод.\n\n**ВАШ ПЕРЕВОД (кратко):**',
     'скобки короче 10 знаков — каркас-строка не срезается'),
    ('P30', 'Header', 'Огромный заголовок главы, превышающий сорок символов '
     'сам по себе (см. примечание):', 7,
     'Огромный заголовок главы, превышающий сорок символов '
     'сам по себе (см. примечание):',
     'заголовок длиннее 40 знаков — не срезается'),
    ('P31', '', '', 1, '', 'всё пусто'),
    ('P32', 'Src', '   \n \n ', 1, '', 'пробельный ответ -> пусто'),
    ('P33', None, None, 1, '', 'None-ответ'),
    ('P34', 'Chapter 3', '8. АНГЛИЧАНЕ [ПЕРЕВЕСТИ ЭТО]', 8, 'АНГЛИЧАНЕ',
     'source с числом без точки («Chapter 3») — правила работают'),
    ('P35', 'ENGLISH', '  8. АНГЛИЧАНЕ', 8, 'АНГЛИЧАНЕ',
     'ведущие пробелы перед номером'),
    ('P36', 'ENGLISH', '80. АНГЛИЧАНЕ', 8, '80. АНГЛИЧАНЕ',
     'двузначный номер != сегменту — не трогать'),
    ('P37', 'ENGLISH', '8. Перевод [ПЕРЕВЕСТИ ЭТО] ', 8,
     'Перевод', 'метка + хвостовой пробел'),
    ('P38', 'Chapter title', '**ВАШ ПЕРЕВОД (укажите ТОЛЬКО переведённый '
     'текст, без нумерации или меток)**', 4, '',
     'болд без двоеточия — каркас (признак **)'),
    ('P39', 'Chapter title', 'ВАШ ПЕРЕВОД (укажите только перевод)', 4,
     'ВАШ ПЕРЕВОД (укажите только перевод)',
     'без двоеточия и без ** — не каркас (FP-заслон)'),
]

for pid, src, resp, seg_no, expect, note in PAIRS:
    got_text, got_removed = strip_prompt_leaks(resp, src, seg_no)
    check(f'{pid} {note}', got_text == expect,
          (got_text, expect, got_removed))

check('A-count таблица пар >= 25 строк', len(PAIRS) >= 25, len(PAIRS))
_txt1, _rem1 = strip_prompt_leaks(F1_RESP, F1_SRC, 1)
check('A-removed F1: срезанный фрагмент — каркас-строка',
      _txt1 == F1_EXPECT and len(_rem1) == 1
      and _rem1[0] == '**ВАШ ПЕРЕВОД (укажите ТОЛЬКО переведённый текст, '
                      'без нумерации или меток):**', _rem1)
_txt3, _rem3 = strip_prompt_leaks('8. **АНГЛИЧАНЕ** [ПЕРЕВЕСТИ ЭТО]',
                                  '**ENGLISH**', 8)
check('A-removed F3: номер + метка', _txt3 == '**АНГЛИЧАНЕ**'
      and sorted(_rem3) == ['8.', '[ПЕРЕВЕСТИ ЭТО]'], _rem3)

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
print('[c3] window built', flush=True)
import time as _t  # noqa: E402
for _ in range(60):
    app.processEvents()
    _t.sleep(0.05)

FIX_TXT = OUT / 'c3_fixture.txt'
FIX_TXT.write_text('## ANTIDOTE TO THE ENGLISH\n'
                   'ENGLISH\n'
                   'Bridge Guards.\n'
                   'Chapter title.\n'
                   'Goals and victory conditions.\n'
                   'Retreat to the camp at dusk.\n', encoding='utf-8')
open_queue.append(str(FIX_TXT))
win.import_simple_txt()
segs = win.current_project.segments
check('B0 фикстура импортирована: 6 сегментов', len(segs) == 6, len(segs))
for _s in segs:
    _s.target = ''
    _s.status = 'untranslated'

F1 = F1_RESP
# Ответы F2/F3 строятся от РЕАЛЬНОГО id сегмента (правило (а) срезает
# префикс только при совпадении с seg.id — нумерацией блока контекста).
F2_RU = f'{segs[1].id}. АНГЛИЧАНЕ'
F2_EXPECT = 'АНГЛИЧАНЕ'
F2_ID = segs[1].id
F5_ID = segs[5].id
SCAFFOLD_ONLY = ('**ВАШ ПЕРЕВОД (укажите ТОЛЬКО переведённый текст, '
                 'без нумерации или меток):**')
ECHO_FRAME = '>>> 2. Переведено соседнее <<<\n\n>>> 3. Ещё соседнее <<<'
OK_PLAIN = 'Обычный перевод без утечек.'


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
win.record_undo_state = lambda *a, **k: undo_log.append(a)
tm_log = []
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


def _reset(row):
    segs[row].target = ''
    segs[row].status = 'untranslated'


# --- B1: F1-цепочка: первый ответ эхо-каркас -> повтор -> F1 ---------------
# (эхо моделируется ИСКЛЮЧЕНИЕМ из клиента — C1-детектор живёт внутри
# client.translate, строка-ответ заглушка детектировать не умеет; как в c1/c2)
_reset(0)
stub1 = StubClient([LLMPromptEchoError('echo'), F1])
win.create_llm_client = lambda *a, **k: stub1
seg1 = _run_translate(win, 0)
check('B1a два вызова (эхо -> повтор)', len(stub1.calls) == 2, len(stub1.calls))
check('B1b промт 1-го вызова С блоком SURROUNDING',
      'SURROUNDING SEGMENTS FOR CONTEXT' in stub1.calls[0]['custom_prompt'])
check('B1c промт 2-го вызова БЕЗ блока SURROUNDING',
      'SURROUNDING SEGMENTS FOR CONTEXT' not in stub1.calls[1]['custom_prompt'])
check('B1d в target F1 без каркас-строки',
      seg1.target == F1_EXPECT, seg1.target[:60])
check('B1e статус draft', seg1.status == 'draft', seg1.status)
check('B1f лог про срезание (removed prompt artefact)',
      any('removed prompt artefact(s)' in m and 'ВАШ ПЕРЕВОД' in m
          for m in _logs), _logs[-4:])
check('B1g в TM не пишется до подтверждения', len(tm_log) == 0, len(tm_log))

# --- B2: F2 — префикс номера срезается -------------------------------------
_reset(1)
stub2 = StubClient([F2_RU])
win.create_llm_client = lambda *a, **k: stub2
seg2 = _run_translate(win, 1)
check('B2a один вызов (утечек-эха нет)', len(stub2.calls) == 1, len(stub2.calls))
check('B2b target = «АНГЛИЧАНЕ»', seg2.target == F2_EXPECT, seg2.target[:40])
check('B2c лог про срезание номера',
      any('removed prompt artefact(s)' in m and f'{F2_ID}.' in m
          for m in _logs), _logs[-3:])
check('B2d статус draft', seg2.status == 'draft', seg2.status)

# --- B3: F3 — номер + метка «[ПЕРЕВЕСТИ ЭТО]» -------------------------------
_reset(2)
stub3 = StubClient([f'{segs[2].id}. **АНГЛИЧАНЕ** [ПЕРЕВЕСТИ ЭТО]'])
win.create_llm_client = lambda *a, **k: stub3
seg3 = _run_translate(win, 2)
check('B3a target = «**АНГЛИЧАНЕ**»', seg3.target == '**АНГЛИЧАНЕ**',
      seg3.target[:40])
check('B3b лог про два срезания',
      any('removed prompt artefact(s)' in m and '[ПЕРЕВЕСТИ ЭТО]' in m
          for m in _logs), _logs[-3:])

# --- B4: ответ целиком каркас -> повтор без контекста -> успех --------------
_reset(3)
stub4 = StubClient([SCAFFOLD_ONLY, OK_PLAIN])
win.create_llm_client = lambda *a, **k: stub4
seg4 = _run_translate(win, 3)
check('B4a два вызова (каркас -> повтор)', len(stub4.calls) == 2,
      len(stub4.calls))
check('B4b промт 2-го вызова БЕЗ блока SURROUNDING',
      'SURROUNDING SEGMENTS FOR CONTEXT' not in stub4.calls[1]['custom_prompt'])
check('B4c в target чистый повтор', seg4.target == OK_PLAIN,
      seg4.target[:40])
check('B4d лог «only prompt scaffolding»',
      any('only prompt scaffolding' in m for m in _logs), _logs[-4:])

# --- B5: каркас и в повторе -> пропуск (без модалок) ------------------------
_reset(4)
stub5 = StubClient([SCAFFOLD_ONLY, SCAFFOLD_ONLY])
win.create_llm_client = lambda *a, **k: stub5
seg5 = _run_translate(win, 4)
check('B5a ровно два вызова', len(stub5.calls) == 2, len(stub5.calls))
check('B5b target пуст', seg5.target == '', seg5.target[:40])
check('B5c статус прежний (untranslated)', seg5.status == 'untranslated',
      seg5.status)
check('B5d undo/TM не тронуты', len(undo_log) == 0 and len(tm_log) == 0,
      (len(undo_log), len(tm_log)))
check('B5e без модалок',
      not any('warning' in m or 'critical' in m for m in modal_log), modal_log)

# --- B6: обычный ответ не меняется и не логируется --------------------------
_reset(5)
stub6 = StubClient([OK_PLAIN])
win.create_llm_client = lambda *a, **k: stub6
seg6 = _run_translate(win, 5)
check('B6a target = обычный перевод', seg6.target == OK_PLAIN,
      seg6.target[:40])
check('B6b без лога срезания',
      not any('removed prompt artefact' in m for m in _logs), _logs[-3:])
check('B6c без логов каркаса/эха/перелива',
      not any('scaffolding' in m or 'echo' in m.lower() or 'overflow' in m
              for m in _logs), _logs[-3:])

# --- B7: каркас при запросе БЕЗ контекста -> сразу пропуск ------------------
settings = win.load_general_settings()
settings['surrounding_segments'] = 0
win.save_general_settings(settings)
_reset(5)
stub7 = StubClient([SCAFFOLD_ONLY])
win.create_llm_client = lambda *a, **k: stub7
seg7 = _run_translate(win, 5)
check('B7a ровно один вызов — повтора нет', len(stub7.calls) == 1,
      len(stub7.calls))
check('B7b target пуст / статус прежний',
      seg7.target == '' and seg7.status == 'untranslated',
      (seg7.target[:30], seg7.status))
check('B7c без модалок',
      not any('warning' in m or 'critical' in m for m in modal_log), modal_log)
settings['surrounding_segments'] = 5
win.save_general_settings(settings)

# --- B8: F2 в ответе ЭХО-повтора C1 -----------------------------------------
_reset(5)
stub8 = StubClient([LLMPromptEchoError('echo'), f'{F5_ID}. АНГЛИЧАНЕ'])
win.create_llm_client = lambda *a, **k: stub8
seg8 = _run_translate(win, 5)
check('B8a два вызова', len(stub8.calls) == 2, len(stub8.calls))
check('B8b в target F2 без номера (эхо-повтор тоже срезается)',
      seg8.target == F2_EXPECT, seg8.target[:40])
check('B8c лог про срезание в повторе',
      any('removed prompt artefact(s)' in m for m in _logs), _logs[-3:])

# --- B9: F2 в ответе ПЕРЕЛИВ-повтора C2 -------------------------------------
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
_reset(5)
stub9 = StubClient([FIXTURE_OVERFLOW_31, f'{F5_ID}. АНГЛИЧАНЕ'])
win.create_llm_client = lambda *a, **k: stub9
seg9 = _run_translate(win, 5)
check('B9a два вызова (перелив -> повтор)', len(stub9.calls) == 2,
      len(stub9.calls))
check('B9b в target F2 без номера (перелив-повтор тоже срезается)',
      seg9.target == F2_EXPECT, seg9.target[:40])
check('B9c статус draft', seg9.status == 'draft', seg9.status)

# ═══ Часть C: предпроход по сегментам в экспорте Tagged Text ═══════════════
from modules.tagged_text.stylemap import StyleMap  # noqa: E402

report_holder = {}
win._show_tagged_text_report = lambda report, path: report_holder.update(
    report=report, path=path)

# C1–C6: ячейка-перелив + ячейка-эхо + обычный перелив + сегмент с метками.
segs[0].table_info = (0, 0, 0, True)
segs[0].file_id = 0
segs[0].target = FIXTURE_OVERFLOW_31       # ячейка-перелив
segs[1].table_info = (0, 0, 1, False)
segs[1].file_id = 0
segs[1].target = '>>> 8. Переведено соседнее <<< [ПЕРЕВЕСТИ ЭТО]'  # эхо
segs[2].target = FIXTURE_OVERFLOW_31       # ОБЫЧНЫЙ сегмент-перелив
segs[2].table_info = None
segs[3].target = 'Отступление в лагерь в сумерках. [ПЕРЕВЕСТИ ЭТО]'
segs[3].table_info = None
segs[4].target = 'Обычный перевод.'
segs[4].table_info = None
segs[5].target = 'Тоже обычный.'
segs[5].table_info = None

OUTFILE = OUT / 'c3_export.txt'
save_queue.append(str(OUTFILE))
win.export_tagged_txt()
report = report_holder.get('report')
check('C1 отчёт собран', report is not None, report_holder)
if report:
    warns = report.warnings
    check('C2 ячейка-перелив -> «возможный перелив контекста '
          '(ячейка, сегмент #1)»',
          any('возможный перелив контекста (ячейка, сегмент #1)' in w
              for w in warns), warns[:5])
    check('C3 ячейка-эхо -> «похоже на эхо промта (ячейка, сегмент #2)»',
          any('похоже на эхо промта (ячейка, сегмент #2)' in w
              for w in warns), warns[:5])
    check('C4 сегмент с метками -> «остатки разметки промта в переводе '
          '(сегмент #4)»',
          any('остатки разметки промта в переводе (сегмент #4)' in w
              and '[ПЕРЕВЕСТИ ЭТО]' in w for w in warns), warns[:5])
    check('C5 обычный перелив — писателем «(строка N)», без дубля '
          '«(ячейка…)»',
          any('возможный перелив контекста (строка' in w for w in warns)
          and not any('(ячейка, сегмент #3' in w or '(ячейка, сегмент #4' in w
                      for w in warns), [w for w in warns if 'перелив' in w])
    check('C6 предупреждения предпрохода наверху списка',
          warns and '(ячейка' in warns[0], warns[:3])
    _data = OUTFILE.read_bytes()
    check('C7 файл записан (UTF-16LE BOM + <UNICODE-WIN>)',
          _data[:2] == b'\xff\xfe'
          and _data[2:28].decode('utf-16-le') == '<UNICODE-WIN>', _data[:28])
    check('C8 target не изменён предпроходом',
          segs[3].target.endswith('[ПЕРЕВЕСТИ ЭТО]')
          and segs[0].target == FIXTURE_OVERFLOW_31,
          (segs[3].target[-20:], segs[0].target[:20]))

# C9: чистый проект — без новых предупреждений.
for _s in segs:
    _s.target = 'Обычный перевод.' if _s.source.strip() else ''
    _s.table_info = None
report_holder.clear()
OUTFILE2 = OUT / 'c3_export_clean.txt'
save_queue.append(str(OUTFILE2))
win.export_tagged_txt()
report2 = report_holder.get('report')
check('C9 чистый проект — без предупреждений',
      report2 is not None and not report2.warnings,
      report2.warnings if report2 else 'нет отчёта')

print(f'[c3] done: {PASSED} passed / {FAILED} failed', flush=True)
os._exit(0 if FAILED == 0 else 1)
