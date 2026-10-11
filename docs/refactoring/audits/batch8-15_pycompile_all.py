"""py_compile для Batch #8.15 — два счётчика (правило Дмитрия, 8.13 §9.3):
  канонический — только код вне docs/ (не растёт от аудит-скриптов);
  справочный   — общий (git ls-files *.py).
Сравнение до/после всегда на одном и том же наборе файлов; критерий 0 ошибок.
"""
import py_compile, subprocess, sys, pathlib

ROOT = r"E:\Dev\SupervertalerPortable"
PYC = r"D:\Temp\SupervertalerPortable\refactoring\b8-15\_pyc.pyc"
files = subprocess.run(["git", "ls-files", "*.py"], capture_output=True, text=True,
                       cwd=ROOT).stdout.split()
app_files = [f for f in files if not f.startswith("docs/")]
ok = fail = cok = cfail = 0
fails = []
for f in files:
    try:
        py_compile.compile(f, doraise=True, cfile=PYC)
        ok += 1
    except Exception as e:
        fail += 1
        fails.append((f, str(e)))
for f in app_files:
    try:
        py_compile.compile(f, doraise=True, cfile=PYC)
        cok += 1
    except Exception as e:
        cfail += 1
        fails.append((f, "CANON " + str(e)))
print(f"py_compile CANONICAL (outside docs/): {cok} ok / {cfail} fail / {len(app_files)} total")
print(f"py_compile REFERENCE (all tracked .py):         {ok} ok / {fail} fail / {len(files)} total")
for f, e in fails:
    print(f"FAIL {f}: {e}")
