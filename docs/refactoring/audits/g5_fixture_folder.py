# G5 follow-up (READ-ONLY): full figure-context path on Dmitry's shortened fixture.
# Simulates .md import segmentation (one line per segment) + load_from_folder(samples/).
import os, sys, pathlib
sys.path.insert(0, os.getcwd())
from modules.figure_context_manager import FigureContextManager

class App:
    def log(self, *a, **k): print("   ", *a)
fc = FigureContextManager(App())

samples = pathlib.Path("docs/refactoring/samples").resolve()
n = fc.load_from_folder(str(samples))
print(f"load_from_folder -> {n} images, map keys = {sorted(fc.figure_context_map)}")

lines = (samples / "Miniature Wargames #520.translation.md").read_text(encoding="utf-8").splitlines()
print()
print("=== per-segment get_images_for_text (md import = one line per segment) ===")
for i, ln in enumerate(lines, 1):
    imgs = fc.get_images_for_text(ln)
    print(f"  segment {i} (len={len(ln)}): refs={fc.detect_figure_references(ln)} images={[r for r,_ in imgs]}")
