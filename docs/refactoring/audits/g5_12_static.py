# -*- coding: utf-8 -*-
"""Batch G5.1+G5.2 static protection suite (format of batch9-5_static_after_*.log).

Запуск: python docs/refactoring/audits/g5_12_static.py <tag>
Метрики: AST chain, pyflakes (warnings + undefined), py_compile канон/справ,
headless imports, grep-гейт 9 файлов.
"""
import ast
import compileall
import importlib
import io
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b8-9") / "pyflakes_lib"))
tag = sys.argv[1] if len(sys.argv) > 1 else "after"
OUT = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-g5-12")
OUT.mkdir(parents=True, exist_ok=True)

# --- chain ---
print(f"=== chain {tag} ===", flush=True)
r = subprocess.run(
    [sys.executable, str(ROOT / "docs/refactoring/audits/batch8-12_code_startup_chain_resolve.py"),
     str(ROOT / "Supervertaler.py"), f"g512_{tag}"],
    capture_output=True, text=True, cwd=str(ROOT))
print(r.stdout.strip())
print(r.stderr.strip())

# --- pyflakes ---
print(f"=== pyflakes {tag} ===", flush=True)
from pyflakes.api import checkPath
from pyflakes.reporter import Reporter

buf = io.StringIO()
rep = Reporter(buf, buf)
files = ["Supervertaler.py"] + sorted(str(p) for p in ROOT.glob("modules/**/*.py") if "__pycache__" not in str(p))
n_warn = 0
for f in files:
    n_warn += checkPath(f, reporter=rep)
text = buf.getvalue()
undef_lines = [l for l in text.splitlines() if "undefined name" in l]
names = {}
for l in undef_lines:
    nm = l.split("undefined name")[1].strip().strip("'\"")
    names[nm] = names.get(nm, 0) + 1
print(f"pyflakes warnings (repo): {n_warn}")
print(f"undefined-name lines: {len(undef_lines)}")
print(f"unique undefined names: {len(names)}")
for k in sorted(names):
    print(f"  {k}: {names[k]}")

# --- py_compile ---
print("=== py_compile ===", flush=True)
import py_compile

PYC = OUT / "pyc"
PYC.mkdir(exist_ok=True)

def compile_set(files):
    ok = fail = 0
    for f in files:
        try:
            py_compile.compile(str(f), cfile=str(PYC / (f.name + "c")), doraise=True)
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  FAIL {f}: {e}")
    return ok, fail, len(files)

tracked = subprocess.run(["git", "ls-files", "*.py"], capture_output=True, text=True, cwd=str(ROOT)).stdout.split()
canon = [ROOT / p for p in tracked if not p.replace("\\", "/").startswith("docs/")]
o, fa, t = compile_set(canon)
print(f"py_compile CANONICAL (outside docs/): {o} ok / {fa} fail / {t} total")
o2, fa2, t2 = compile_set([ROOT / p for p in tracked])
print(f"py_compile REFERENCE (all tracked .py):         {o2} ok / {fa2} fail / {t2} total")

# --- headless ---
print("=== headless ===", flush=True)
ok, fail = 0, []
try:
    importlib.import_module("setup")
    ok += 1
except Exception as e:
    fail.append(("setup", f"{type(e).__name__}: {e}"))
mods = sorted(ROOT.glob("modules/**/*.py"))
for m in mods:
    if "__pycache__" in str(m):
        continue
    name = "modules." + str(m.relative_to(ROOT / "modules")).replace("\\", "/")[:-3].replace("/", ".")
    try:
        importlib.import_module(name)
        ok += 1
    except Exception as e:
        fail.append((name, f"{type(e).__name__}: {e}"))
print(f"headless imports (with setup.py): {ok} ok / {len(fail)} fail / {ok + len(fail)} total")
for n, e in fail:
    print(f"FAIL {n}: {e}")

# --- grep gate (канонический скрипт 9.3) ---
print("=== grep gate ===", flush=True)
r = subprocess.run([sys.executable, str(ROOT / "docs/refactoring/audits/batch9-3_grep_gate.py")],
                   capture_output=True, text=True, cwd=str(ROOT))
print(r.stdout.strip())
print(r.stderr.strip())

print("=== DONE static ===", flush=True)
