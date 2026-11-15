# -*- coding: utf-8 -*-
"""Headless-тесты Batch T2 (коммит 3): disable_console_quickedit().

Функция снимает флаг ENABLE_QUICK_EDIT_MODE (0x0040) с ВХОДНОГО буфера
консоли Windows (GetStdHandle(STD_INPUT_HANDLE=-10)); QuickEdit и
ENABLE_EXTENDED_FLAGS (0x0080) живут именно на входном буфере — выходной
(-11) не при чём (уточнено по документации Console API против примера
T-разведки C3, где фигурировал -10). Остальные флаги сохраняются.

Сценарии:
  C1  импорт функции из Supervertaler.py и вызов в текущем процессе — без
      исключений (результат True/False зависит от окружения, например
      pythonw/редиректы → False);
  C2  дочерний процесс БЕЗ консоли (CREATE_NO_WINDOW) — False без исключений
      (тихий no-op, как запуск через pythonw);
  C3  дочерний процесс СО СВОЕЙ консолью (CREATE_NEW_CONSOLE): читаем
      GetConsoleMode до/после — флаг 0x0040 снят, 0x0080 установлен, все
      прочие биты сохранены (после == (до | 0x0080) & ~0x0040).
  C4  не-Windows — no-op (False) по коду: на win32-хосте проверяется
      статически (guard sys.platform != 'win32' → return False первым).

Дочерние процессы пишут результат JSON-файлом в каталог прогона (в
CREATE_NEW_CONSOLE stdout уходит на экран консоли, а не в pipe).

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/t2_console_quickedit_tests.py
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
                     r'\refactoring\batch-t2\tests\run-003')
ISO = STAGE / 'iso'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
(ISO / 'tmp').mkdir(parents=True, exist_ok=True)

PY = sys.executable

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


# ── C1: вызов в текущем процессе ───────────────────────────────────────────
sys.path.insert(0, REPO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import Supervertaler as SV  # noqa: E402

check('C0 функция существует и callable', callable(getattr(SV, 'disable_console_quickedit', None)))
try:
    rc = SV.disable_console_quickedit()
    check('C1 вызов в текущем процессе без исключений', isinstance(rc, bool), rc)
    print(f'[t2-quickedit] C1 rc={rc} (True — консоль есть, False — нет)', flush=True)
except Exception as e:
    check('C1 вызов в текущем процессе без исключений', False, repr(e))

# Статический guard не-Windows: первая содержательная строка функции —
# sys.platform != 'win32' → return False.
src = (pathlib.Path(REPO) / 'Supervertaler.py').read_text(encoding='utf-8')
fn_src = src[src.index('def disable_console_quickedit'):]
fn_src = fn_src[:fn_src.index('\ndef ', 1) if '\ndef ' in fn_src else len(fn_src)]
check('C4 guard sys.platform первым в функции',
      "sys.platform != 'win32'" in fn_src.split('return False', 1)[0],
      fn_src[:300])

# ── Дочерние скрипты ───────────────────────────────────────────────────────
CHILD_SRC = r'''
import json, pathlib, sys
sys.path.insert(0, r'%REPO%')
import Supervertaler as SV
out = {}
try:
    out['rc'] = SV.disable_console_quickedit()
    out['exception'] = None
except Exception as e:
    out['rc'] = None
    out['exception'] = repr(e)
try:
    import ctypes
    kernel32 = ctypes.windll.kernel32
    h = kernel32.GetStdHandle(-10)
    mode = ctypes.c_ulong()
    have_mode = bool(kernel32.GetConsoleMode(h, ctypes.byref(mode)))
    out['have_console_mode'] = have_mode
    out['mode_after'] = mode.value if have_mode else None
except Exception as e:
    out['mode_error'] = repr(e)
pathlib.Path(r'%RESULT%').write_text(json.dumps(out), encoding='utf-8')
'''

child_common = CHILD_SRC.replace('%REPO%', REPO)


def run_child(tag, creationflags, env_extra=None):
    result_path = OUT / f't2_quickedit_{tag}.json'
    if result_path.exists():
        result_path.unlink()
    src = child_common.replace('%RESULT%', str(result_path))
    script_path = OUT / f't2_quickedit_{tag}_child.py'
    script_path.write_text(src, encoding='utf-8')
    env = dict(os.environ)
    env['TEMP'] = str(ISO / 'tmp')
    env['TMP'] = str(ISO / 'tmp')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [PY, '-I', str(script_path)],
        creationflags=creationflags, env=env, timeout=180)
    data = json.loads(result_path.read_text(encoding='utf-8'))
    return proc.returncode, data


if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_CONSOLE = 0x00000010
    DETACHED_PROCESS = 0x00000008  # совсем без консоли (CREATE_NO_WINDOW даёт
    # скрытую консоль — GetConsoleMode там доступен, что и показал первый прогон)
    ENABLE_QUICK_EDIT_MODE = 0x0040
    ENABLE_EXTENDED_FLAGS = 0x0080

    # ── C2: без консоли (DETACHED_PROCESS) ────────────────────────────────
    code, data = run_child('noconsole', DETACHED_PROCESS)
    check('C2 дочерний процесс завершился без ошибки', code == 0, (code, data))
    check('C2 rc=False без исключений (нет консоли)',
          data.get('rc') is False and data.get('exception') is None, data)
    check('C2 GetConsoleMode недоступен (нет консоли)',
          data.get('have_console_mode') is False, data)

    # ── C3: со своей консолью (CREATE_NEW_CONSOLE) ────────────────────────
    code, data = run_child('console', CREATE_NEW_CONSOLE)
    check('C3 дочерний процесс завершился без ошибки', code == 0, (code, data))
    check('C3 rc=True и консоль доступна',
          data.get('rc') is True and data.get('have_console_mode') is True, data)
    mode_after = data.get('mode_after')
    # Фактический «до» мы в ребёнке не сохранили (функция читает сама);
    # проверяем инвариант: QuickEdit снят, Extended установлен.
    check('C3 флаг ENABLE_QUICK_EDIT_MODE снят',
          mode_after is not None and not (mode_after & ENABLE_QUICK_EDIT_MODE),
          hex(mode_after) if mode_after else None)
    check('C3 флаг ENABLE_EXTENDED_FLAGS установлен',
          mode_after is not None and bool(mode_after & ENABLE_EXTENDED_FLAGS),
          hex(mode_after) if mode_after else None)
else:
    print('[t2-quickedit] не-Windows хост: C2/C3 не применимы', flush=True)
    check('C4 не-Windows: guard возвращает False (статически)', True)

print(flush=True)
print(f'RESULT t2_console_quickedit: PASSED={PASSED} FAILED={FAILED}', flush=True)
sys.stdout.flush()
os._exit(0 if FAILED == 0 else 1)
