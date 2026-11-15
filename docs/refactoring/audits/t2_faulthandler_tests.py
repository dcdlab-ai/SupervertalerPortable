# -*- coding: utf-8 -*-
"""Headless-тесты Batch T2 (коммит 4): faulthandler в main().

До коммита faulthandler в Supervertaler.py НЕ был включён (grep по main()/
_setup_diagnostic_log — пусто; единственные вхождения faulthandler — в
тестовых сьютах docs/refactoring/audits/*). Коммит добавляет
_enable_faulthandler(): файл <user_data_path>/workbench/logs/
supervertaler-fatal.log (рядом с supervertaler.log, тот же механизм путей
P1), ротация «один предыдущий» (supervertaler-fatal-previous.log), файл
открыт через модульную переменную всю жизнь процесса, ошибка открытия не
мешает запуску.

Сценарии:
  F1  дочерний процесс включает faulthandler реальной функцией
      Supervertaler._enable_faulthandler() и падает (ctypes.string_at(0) —
      access violation); в supervertaler-fatal.log есть маркер
      «Windows fatal exception»/«Fatal Python error» и трассировка;
  F2  ротация: перед падением в лог кладут строку-маркер прошлого сеанса —
      после прогона маркер уехал в -previous.log (или удалён), новый
      supervertaler-fatal.log начинается свежим сеансом;
  F3  файл журнала лежит внутри изолированного SUPERVERTALER_DATA_ROOT
      (не в профиле пользователя), ручка удержана модульной переменной;
  F4  ошибка открытия файла (недоступный каталог) не мешает запуску:
      _enable_faulthandler() возвращает None без исключения.

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/t2_faulthandler_tests.py
"""
import faulthandler
import json
import os
import pathlib
import subprocess
import sys

faulthandler.dump_traceback_later(300, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-t2\tests\run-004')
ISO = STAGE / 'iso'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
(ISO / 'tmp').mkdir(parents=True, exist_ok=True)

LOG_DIR = ISO / 'Supervertaler' / 'workbench' / 'logs'
FATAL_LOG = LOG_DIR / 'supervertaler-fatal.log'
FATAL_PREV = LOG_DIR / 'supervertaler-fatal-previous.log'

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


# ── F0: grep-факт — до коммита faulthandler в монолите не включался ───────
mono_src = (pathlib.Path(REPO) / 'Supervertaler.py').read_text(encoding='utf-8')
check('F0 в монолите есть _enable_faulthandler',
      '_enable_faulthandler' in mono_src)
check('F0 enable вызывается из main()',
      '_enable_faulthandler()' in mono_src)

# ── Дочерний скрипт: включить faulthandler и упасть ───────────────────────
CHILD = r'''
import os, pathlib, sys
os.environ['SUPERVERTALER_DATA_ROOT'] = r'%ISO%'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, r'%REPO%')
import Supervertaler as SV

out = {'phase': 'enable'}
try:
    path = SV._enable_faulthandler()
    out['path'] = str(path)
    out['handle_open'] = getattr(SV, '_fault_log_file', None) is not None
except Exception as e:
    out['enable_exception'] = repr(e)
    pathlib.Path(r'%RESULT%').write_text(__import__('json').dumps(out), encoding='utf-8')
    sys.exit(0)

# ВАЖНО: файл держит модульная переменная; где-то ещё раз проверить, что
# открыта (F3), и упасть access violation'ом. SEM_NOGPFAULTERRORBOX гасит
# диалог WER, чтобы прогон не завис на окне отчёта о сбое.
out['phase'] = 'crash'
pathlib.Path(r'%RESULT%').write_text(__import__('json').dumps(out), encoding='utf-8')
import ctypes
if sys.platform == 'win32':
    SEM_FAILCRITICALERRORS = 0x0001
    SEM_NOGPFAULTERRORBOX = 0x0002
    ctypes.windll.kernel32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
ctypes.string_at(0)
'''
child = (CHILD.replace('%ISO%', str(ISO)).replace('%REPO%', REPO)
              .replace('%RESULT%', str(OUT / 't2_fatal_child.json')))
child_path = OUT / 't2_fatal_child.py'
child_path.write_text(child, encoding='utf-8')

# ── Подготовка: сеем «прошлый сеанс» для проверки ротации (F2) ────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
for p in (FATAL_LOG, FATAL_PREV):
    if p.exists():
        p.unlink()
FATAL_LOG.write_text('PREVIOUS-SESSION-MARKER\n', encoding='utf-8')

if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

env = dict(os.environ)
env['TEMP'] = str(ISO / 'tmp')
env['TMP'] = str(ISO / 'tmp')
env['PYTHONDONTWRITEBYTECODE'] = '1'
proc = subprocess.run(
    [sys.executable, '-I', str(child_path)],
    creationflags=CREATE_NO_WINDOW, env=env, timeout=300, cwd=str(OUT))
check('F1 дочерний процесс упал (exit != 0)', proc.returncode != 0, proc.returncode)

result = json.loads((OUT / 't2_fatal_child.json').read_text(encoding='utf-8'))
check('F1 _enable_faulthandler вернул путь', result.get('path') is not None, result)
check('F1 путь внутри изолированного data root (F3)',
      str(LOG_DIR) in result.get('path', ''), result.get('path'))
check('F3 ручка файла удержана модульной переменной', result.get('handle_open') is True)

check('F1 fatal-лог создан', FATAL_LOG.exists(), str(FATAL_LOG))
if FATAL_LOG.exists():
    text = FATAL_LOG.read_text(encoding='utf-8', errors='replace')
    has_marker = ('Windows fatal exception' in text
                  or 'Fatal Python error' in text
                  or 'access violation' in text.lower())
    check('F1 маркер фатального сбоя в логе', has_marker, text[:400])
    has_trace = ('File "' in text and ('line ' in text)) or 'Current thread' in text
    check('F1 трассировка в логе', has_trace, text[:400])
    check('F2 маркер прошлого сеанса не в новом логе',
          'PREVIOUS-SESSION-MARKER' not in text, text[:200])
check('F2 ротация: предыдущий лог уехал в -previous',
      FATAL_PREV.exists() and 'PREVIOUS-SESSION-MARKER'
      in FATAL_PREV.read_text(encoding='utf-8', errors='replace'),
      str(FATAL_PREV))

# ── F4: невоспроизводимый каталог → None без исключения ───────────────────
# mkdir(parents=True) сам создаёт дерево каталогов, поэтому «сломать» открытие
# можно только упором в существующий ФАЙЛ: log_dir — путь ПОД файлом.
sys.path.insert(0, REPO)
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import Supervertaler as SV  # noqa: E402

blocker_file = STAGE / 'blocked' / 'blocker.dat'
blocker_file.parent.mkdir(parents=True, exist_ok=True)
blocker_file.write_text('not a dir', encoding='utf-8')

_saved = SV.get_user_data_path
SV.get_user_data_path = lambda: blocker_file  # путь, который существует как ФАЙЛ
try:
    rc = SV._enable_faulthandler()
    check('F4 ошибка открытия файла не мешает (None без исключения)', rc is None, rc)
except Exception as e:
    check('F4 ошибка открытия файла не мешает (None без исключения)', False, repr(e))
finally:
    SV.get_user_data_path = _saved

print(flush=True)
print(f'RESULT t2_faulthandler: PASSED={PASSED} FAILED={FAILED}', flush=True)
sys.stdout.flush()
os._exit(0 if FAILED == 0 else 1)
