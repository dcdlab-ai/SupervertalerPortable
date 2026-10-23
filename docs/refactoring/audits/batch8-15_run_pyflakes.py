import os, pathlib, sys

OUT = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-15")
sys.path.insert(0, str(pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-9") / "pyflakes_lib"))
# Q-A Q7 (координатор 2026-10-23): dev-рантайм агент не меняет — pyflakes
# ставится ВНЕ рантайма (pip install --target). Встраиваемый Python (._pth)
# игнорирует PYTHONPATH, поэтому внешний каталог добавляется прямо здесь.
# Исторический b8-9/pyflakes_lib повреждён 2026-10-22 (у пакета удалены .py,
# остались только __pycache__ — см. env-baseline_q-a.txt); новый эталон —
# qa/env/pyflakes-ext (4.0.3; счётчики совпадают с базой 4.0.1: 548/126/4).
sys.path.insert(0, r"D:\Temp\SupervertalerPortable\qa\env\pyflakes-ext")
os.chdir(r"E:\Dev\SupervertalerPortable")

from pyflakes.api import checkPath
from pyflakes.reporter import Reporter

files = ["Supervertaler.py"] + sorted(str(p) for p in pathlib.Path("modules").rglob("*.py"))
warning_count = 0
with open(OUT / f"undefined_names_{sys.argv[1]}.txt", "w", encoding="utf-8") as fh:
    reporter = Reporter(fh, fh)
    for f in files:
        warning_count += checkPath(f, reporter=reporter)
print("pyflakes warnings (repo):", warning_count)

undef = [l for l in (OUT / f"undefined_names_{sys.argv[1]}.txt").read_text(encoding="utf-8").splitlines()
         if "undefined name" in l]
print("undefined-name lines:", len(undef))

import re, collections
names = collections.Counter()
for l in undef:
    m = re.search(r"undefined name '([^']+)'", l)
    if m:
        names[m.group(1)] += 1
print("unique undefined names:", len(names))
for n, c in sorted(names.items()):
    print(f"  {n}: {c}")
