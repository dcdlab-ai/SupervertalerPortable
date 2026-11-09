# -*- coding: utf-8 -*-
"""Headless-тесты Batch C1: защита от эха промта.

Части:
  A — modules/prompt_markers.py: константы байт-в-байт равны прежним
      литералам; детектор looks_like_prompt_echo (фикстуры — строки из
      выходов I2 / T-I2b; по уточнению координатора эхо в T-I2b находится
      в TARGET — выходе экспорта, а не в source).
  B — modules/llm_clients.py: флаг detect_prompt_echo (по умолчанию ВЫКЛЮЧЕН;
      с флагом эхо -> LLMPromptEchoError, чистый ответ проходит).
  C — полное приложение: translate_current_segment (эхо -> повтор без блока
      контекста -> успех; эхо дважды -> target/TM/undo не тронуты, статус
      прежний, лог без модалок); байт-в-байт равенство собранного промта;
      writer-предупреждение об эхе с номерами строк и выравнивание
      source_lines.

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/c1_prompt_echo_tests.py
"""
import faulthandler
import os
import pathlib
import sys

faulthandler.dump_traceback_later(90, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-c1\tests\run-001')
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
for d in ('Desktop', 'Documents', 'Downloads'):
    (ISO / d).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, REPO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import PyQt6.QtWidgets as QW  # noqa: E402,F401 (QApplication владельцем окна)
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog,  # noqa: E402
                             QMessageBox)

modal_log = []


def _logging_exec(self, *a, **k):
    modal_log.append(f"QDialog.exec {type(self).__name__} '{self.windowTitle()}'")
    return QDialog.DialogCode.Accepted


QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(
    lambda *a, **k: (modal_log.append(f"info '{a[1] if len(a) > 1 else ''}'"),
                     QMessageBox.StandardButton.Ok)[1])
QMessageBox.warning = staticmethod(
    lambda *a, **k: (modal_log.append(f"warning '{a[1] if len(a) > 1 else ''}'"),
                     QMessageBox.StandardButton.Ok)[1])
QMessageBox.critical = staticmethod(
    lambda *a, **k: (modal_log.append(f"critical '{a[1] if len(a) > 1 else ''}'"),
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


app = QApplication(sys.argv)

# ═══ Часть A: маркеры и детектор ════════════════════════════════════════
from modules.prompt_markers import (  # noqa: E402
    SURROUNDING_CONTEXT_EXPLAINER, SURROUNDING_CONTEXT_HEADER,
    TRANSLATE_THIS_MARK, looks_like_prompt_echo)

# Фикстуры — строки из выхода I2 (T-I2b; эхо в TARGET, уточнение координатора).
RU_ECHO_BLOCK = (
    'ОКРУЖАЮЩИЕ СЕГМЕНТЫ ДЛЯ КОНТЕКСТА:\n'
    '(Сегмент, отмеченный >>> <<<, подлежит переводу)\n'
    '13. ## ОСОБЫЕ ПРАВИЛА\n'
    '25. |Основная линия союзников|В первый раз...\n'
    '27.\n'
    '28.\n'
    '29.\n'
    '>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<  [ПЕРЕВЕСТИ ЭТО]\n'
    '31.\n'
)
EN_ECHO_BLOCK = (
    '**SURROUNDING SEGMENTS FOR CONTEXT:**\n'
    '(The segment marked with >>> <<< is the one to translate)\n'
    '13. ## SPECIAL RULES\n'
    '27.\n'
    '28.\n'
    '>>> 30. ### GOALS AND VICTORY <<<  [TRANSLATE THIS]\n'
)

check('A1 константы байт-в-байт равны прежним литералам',
      SURROUNDING_CONTEXT_HEADER == '**SURROUNDING SEGMENTS FOR CONTEXT:**'
      and SURROUNDING_CONTEXT_EXPLAINER
      == '(The segment marked with >>> <<< is the one to translate)'
      and TRANSLATE_THIS_MARK == '[TRANSLATE THIS]')
check('A2 эхо по-русски (полный блок) -> детект',
      looks_like_prompt_echo(RU_ECHO_BLOCK, 'Простой текст'))
check('A3 эхо по-английски (полный блок) -> детект',
      looks_like_prompt_echo(EN_ECHO_BLOCK, 'Plain text'))
check('A4 маркированная строка (рус.) -> детект (парные >>>/<<<)',
      looks_like_prompt_echo('>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<  [ПЕРЕВЕСТИ ЭТО]',
                             'Простой текст'))
check('A5 ">>> 5. Начало" -> детект (нумерованный сигнал)',
      looks_like_prompt_echo('>>> 5. Начало работы', 'Введение'))
check('A6 литерал заголовка в ответе -> детект',
      looks_like_prompt_echo('SURROUNDING SEGMENTS FOR CONTEXT: ...', 'текст'))
check('A7 source сам содержит ">>> 30. ... <<< [ПЕРЕВЕСТИ ЭТО]" -> НЕТ детекта',
      not looks_like_prompt_echo(
          '>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<  [ПЕРЕВЕСТИ ЭТО]',
          '>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<  [ПЕРЕВЕСТИ ЭТО]'))
check('A8 markdown-нумерованный список -> НЕТ детекта',
      not looks_like_prompt_echo('1. Пункт один\n2. Пункт два\n3. Пункт три',
                                 '1. Item one\n2. Item two'))
check('A9 голая строка "27." -> НЕТ детекта (контракт координатора)',
      not looks_like_prompt_echo('27.', 'Обычный текст'))
check('A10 обычный перевод -> НЕТ детекта',
      not looks_like_prompt_echo('Мост охраняется — «цитаты», 3 юнита. ✅',
                                 'The bridge is guarded — "quotes", 3 units.'))
check('A11 ">>>" без парного "<<<" -> НЕТ детекта (парное правило)',
      not looks_like_prompt_echo('Стрелка >>> в тексте', 'Plain text'))
check('A12 пустой/None ответ -> False',
      not looks_like_prompt_echo('', 'текст')
      and not looks_like_prompt_echo(None, 'текст'))

# ═══ Часть B: флаг detect_prompt_echo в LLMClient ═══════════════════════
from modules.llm_clients import (LLMClient, LLMPromptEchoError,  # noqa: E402
                                 LLMResponseError)

_real_call = LLMClient._call_openai_with_usage
LLMClient._call_openai_with_usage = lambda self, prompt, **k: (RU_ECHO_BLOCK, {})

cl = LLMClient(api_key='not-needed', provider='custom_openai', model='stub-model')
try:
    cl.translate(text='Простой текст', source_lang='ru', target_lang='en',
                 detect_prompt_echo=True)
    check('B1 флаг True + эхо -> LLMPromptEchoError', False, 'no raise')
except LLMPromptEchoError as e:
    check('B1 флаг True + эхо -> LLMPromptEchoError', True)
except Exception as e:  # noqa: BLE001
    check('B1 флаг True + эхо -> LLMPromptEchoError', False, repr(e))

res = cl.translate(text='Простой текст', source_lang='ru', target_lang='en')
check('B2 флаг по умолчанию ВЫКЛЮЧЕН: эхо-ответ проходит без исключения',
      res == RU_ECHO_BLOCK)

LLMClient._call_openai_with_usage = (
    lambda self, prompt, **k: ('Чистый перевод моста.', {}))
res = cl.translate(text='текст', source_lang='ru', target_lang='en',
                   detect_prompt_echo=True)
check('B3 флаг True + чистый ответ -> проходит',
      res == 'Чистый перевод моста.')

LLMClient._call_openai_with_usage = (
    lambda self, prompt, **k: ('>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<', {}))
res = cl.translate(text='>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<',
                   source_lang='ru', target_lang='en', detect_prompt_echo=True)
check('B4 source сам содержит маркеры -> проходит (нет ложного срабатывания)',
      '>>>' in res)
check('B5 LLMPromptEchoError — типизированный наследник LLMResponseError '
      '(как LLMTruncatedError, G3.2)',
      issubclass(LLMPromptEchoError, LLMResponseError)
      and issubclass(LLMPromptEchoError, ValueError))

LLMClient._call_openai_with_usage = _real_call

# ═══ Часть C: полное приложение ═════════════════════════════════════════
import Supervertaler as SV  # noqa: E402

win = SV.SupervertalerQt()
print('[c1] window built', flush=True)
import time as _t  # noqa: E402
for _ in range(60):
    app.processEvents()
    _t.sleep(0.05)

# Фикстура проекта: 3 строки -> 3 сегмента.
FIX_TXT = OUT / 'c1_fixture.txt'
FIX_TXT.write_text('The bridge is guarded by archers.\n'
                   'Goals and victory conditions.\n'
                   'Retreat to the camp at dusk.\n', encoding='utf-8')
open_queue.append(str(FIX_TXT))
win.import_simple_txt()
n_segs = len(win.current_project.segments)
check('C0 фикстура импортирована: 3 сегмента', n_segs == 3, n_segs)
for _s in win.current_project.segments:
    _s.target = ''  # без переводов — target_text="" в промте


class StubClient:
    """Заглушка LLM-клиента: сценарий ответов + журнал вызовов."""
    supports_vision = False

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def translate(self, text, source_lang='en', target_lang='nl',
                  context=None, custom_prompt=None, max_tokens=None,
                  images=None, system_prompt=None, skip_cleaning=False,
                  enable_prompt_caching=False, detect_prompt_echo=False, **k):
        self.calls.append({
            'text': text, 'custom_prompt': custom_prompt, 'images': images,
            'echo_flag': detect_prompt_echo})
        action = self.script.pop(0)
        if isinstance(action, Exception):
            raise action
        return action


def _expected_prompt(win, seg, current_row, n_segs):
    """Ожидаемый промт: сборка ДО батча (прежние литералы)."""
    base = win.prompt_manager_qt.build_final_prompt(
        source_text=seg.source,
        source_lang=win.current_project.source_lang,
        target_lang=win.current_project.target_lang,
        mode='single',
        glossary_terms=win.get_ai_inject_glossary_terms(),
        target_text=seg.target or '',
        fuzzy_match=None,
    )
    surrounding = 5
    start_idx = max(0, current_row - surrounding)
    end_idx = min(n_segs, current_row + surrounding + 1)
    parts = []
    for i in range(start_idx, end_idx):
        s = win.current_project.segments[i]
        if i == current_row:
            parts.append(f'>>> {s.id}. {s.source} <<<  [TRANSLATE THIS]')
        else:
            parts.append(f'{s.id}. {s.source}')
            if s.target:
                parts.append(f'    → {s.target}')
    ctx = ('\n\n**SURROUNDING SEGMENTS FOR CONTEXT:**\n'
           '(The segment marked with >>> <<< is the one to translate)\n\n'
           + '\n'.join(parts))
    return base.replace('**YOUR TRANSLATION', ctx + '\n\n**YOUR TRANSLATION')


def _select_row(win, row):
    win.table.clearSelection()
    idx = win.table.model().index(row, 0)
    win.table.selectionModel().setCurrentIndex(
        idx, win.table.selectionModel().SelectionFlag.ClearAndSelect)
    app.processEvents()


seg2 = win.current_project.segments[1]
_logs = []
_orig_log = win.log
win.log = lambda msg: (_logs.append(msg), _orig_log(msg))[1]

# C1–C4: эхо -> повтор без контекста -> успех.
stub = StubClient([
    LLMPromptEchoError('echo'),
    'The victory conditions are listed below.',
])
win.create_llm_client = lambda *a, **k: stub
# Изолированный профиль без Custom endpoint: гвардия «not configured»
# заглушается — клиент и так подменён (перевод не ходит в сеть).
win._custom_llm_ready = lambda settings=None: True
_select_row(win, 1)
n_modals = len(modal_log)
win.translate_current_segment()
seg2 = win.current_project.segments[1]
check('C1 оба вызова с detect_prompt_echo=True',
      len(stub.calls) == 2 and stub.calls[0]['echo_flag']
      and stub.calls[1]['echo_flag'], [c['echo_flag'] for c in stub.calls])
base_expected = None
check('C2 промт 1-го вызова байт-в-байт равен прежней сборке',
      stub.calls[0]['custom_prompt']
      == _expected_prompt(win, seg2, 1, n_segs))
check('C3 повтор БЕЗ блока окружающих сегментов (промт = базовый)',
      stub.calls[1]['custom_prompt']
      == win.prompt_manager_qt.build_final_prompt(
          source_text=seg2.source,
          source_lang=win.current_project.source_lang,
          target_lang=win.current_project.target_lang,
          mode='single',
          glossary_terms=win.get_ai_inject_glossary_terms(),
          target_text='',
          fuzzy_match=None))
check('C4 успех: target записан, статус draft',
      seg2.target == 'The victory conditions are listed below.'
      and seg2.status == 'draft',
      (seg2.target[:40], seg2.status))
check('C5 лог повтора: "Retry without surrounding context"',
      any('Retry without surrounding context' in m for m in _logs))
check('C6 без модальных окон при повторе',
      not any("warning 'Translation Failed'" in m for m in modal_log[n_modals:]))

# C7–C11: эхо дважды -> ничего не тронуто.
seg3 = win.current_project.segments[2]
seg3.target = ''
seg3.status = 'untranslated'
stub2 = StubClient([LLMPromptEchoError('echo'), LLMPromptEchoError('echo')])
win.create_llm_client = lambda *a, **k: stub2
win._custom_llm_ready = lambda settings=None: True
_select_row(win, 2)
n_modals = len(modal_log)
_logs.clear()
win.translate_current_segment()
seg3 = win.current_project.segments[2]
check('C7 двойное эхо: два вызова, target НЕ записан',
      len(stub2.calls) == 2 and seg3.target == '', seg3.target[:40])
check('C8 статус прежний', seg3.status == 'untranslated', seg3.status)
check('C9 лог: "Prompt echo in the model response — segment #%s left untranslated"'
      % seg3.id,
      any('left untranslated' in m and f'#{seg3.id}' in m for m in _logs),
      list(_logs)[-3:])
check('C10 без модалок (в т.ч. без "Translation Failed")',
      not any("warning 'Translation Failed'" in m for m in modal_log[n_modals:]))
check('C11 повтор тоже с detect_prompt_echo=True',
      stub2.calls[1]['echo_flag'] is True)

# C12–C14: writer-предупреждение об эхе (Batch C1, координатор Q4).
from modules.tagged_text.stylemap import StyleMap  # noqa: E402
from modules.tagged_text.writer import write_tagged_text  # noqa: E402

segments = list(win.current_project.segments)
segments[0].target = RU_ECHO_BLOCK  # эхо в target (уточнение координатора)
translated_lines = win._collect_translated_lines(segments, False)
md_text = '\n'.join(translated_lines)
# Выравнивание до физических строк — та же схема, что в export_tagged_txt:
# логический source дублируется по числу физических строк target.
source_lines = []
for _src, _out in zip(win._collect_source_lines(segments), translated_lines):
    source_lines.extend([_src] * (_out.count('\n') + 1))
check('C12 source_lines выровнены 1:1 с физическими строками md',
      len(source_lines) == len(md_text.split('\n')),
      (len(source_lines), len(md_text.split('\n'))))
data, report = write_tagged_text(
    md_text, style_map=StyleMap(), source_lines=source_lines)
check('C13 эхо в target -> предупреждение с номером строки (строка 2: парные >>>/<<<)',
      any('похоже на эхо промта (строка 2)' in w for w in report.warnings),
      report.warnings[:3])
data2, report2 = write_tagged_text(md_text, style_map=StyleMap())
check('C14 без source_lines предупреждения нет (контракт CLI/регресс)',
      not any('эхо промта' in w for w in report2.warnings))
# «>>>» из source легитимен: source строки содержит маркеры -> нет предупреждения
segments[0].source = '>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<  [ПЕРЕВЕСТИ ЭТО]'
segments[0].target = '>>> 30. ### ЦЕЛИ И ПОБЕДА  <<<  [ПЕРЕВЕСТИ ЭТО]'
md_text2 = '\n'.join(win._collect_translated_lines(segments, False))
data3, report3 = write_tagged_text(
    md_text2, style_map=StyleMap(), source_lines=win._collect_source_lines(segments))
check('C15 target с ">>>" из source -> БЕЗ предупреждения',
      not any('эхо промта' in w for w in report3.warnings),
      report3.warnings[:3])

win.log = _orig_log
print(f'[c1] done: {PASSED} passed / {FAILED} failed', flush=True)
sys.exit(1 if FAILED else 0)
