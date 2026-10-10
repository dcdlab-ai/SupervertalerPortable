import os, pathlib, sys

OUT = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-12")
sys.path.insert(0, str(pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-9") / "pyflakes_lib"))
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

# undefined-name subset only
undef = [l for l in (OUT / f"undefined_names_{sys.argv[1]}.txt").read_text(encoding="utf-8").splitlines()
         if "undefined name" in l]
print("undefined-name lines:", len(undef))

# per-module check for the two edited files
for mod in ["modules/statuses.py", "modules/help_system.py", "modules/termbase_manager.py", "modules/styled_widgets.py"]:
    import io
    buf = io.StringIO()
    rep = Reporter(buf, buf)
    n = checkPath(mod, reporter=rep)
    print(f"{mod}: {n} warnings")
    print(buf.getvalue())
