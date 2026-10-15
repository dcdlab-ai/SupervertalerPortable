# G5 audit follow-up (READ-ONLY): re-check figure-context behavior on Dmitry's
# shortened fixture (2 variants: text "(Figure 1A)" + md-embed ![Image](path)).
import os, sys, pathlib
sys.path.insert(0, os.getcwd())
from modules.figure_context_manager import normalize_figure_ref, FigureContextManager

class App:
    def log(self, *a, **k): pass
fc = FigureContextManager(App())

samples = pathlib.Path("docs/refactoring/samples")
lines = (samples / "Miniature Wargames #520.translation.md").read_text(encoding="utf-8").splitlines()

print("=== fixture lines ===")
for i, ln in enumerate(lines, 1):
    print(f"  line {i}: len={len(ln)}  tail={ln[-80:]!r}")

print()
print("=== variant 1: text '(Figure 1A)' in line 1 ===")
refs1 = fc.detect_figure_references(lines[0])
print(f"  detect refs = {refs1}")
fn1 = "Figure 1A.png"
print(f"  normalize_figure_ref({fn1!r}) = {normalize_figure_ref(fn1)!r}")
print(f"  match: {normalize_figure_ref(fn1) in refs1}")

print()
print("=== variant 2: md-embed line 3 ===")
md = lines[2]
print(f"  line = {md!r}")
refs2 = fc.detect_figure_references(md)
print(f"  detect refs on md line = {refs2}")
import re
m = re.search(r'!\[[^\]]*\]\(([^)]*)\)', md)
path = m.group(1) if m else None
print(f"  md path = {path!r}")
if path:
    p = pathlib.Path(path)
    print(f"  exists = {p.exists()}")
    print(f"  basename = {p.name!r}")
    print(f"  normalize_figure_ref(basename) = {normalize_figure_ref(p.name)!r}")
    print(f"  detect refs on basename = {fc.detect_figure_references(p.name)}")

print()
print("=== figure folder scan: which files in samples/ get a ref? ===")
for f in sorted(samples.iterdir()):
    if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'):
        print(f"  {f.name!r:20} -> {normalize_figure_ref(f.name)!r}")
