# G5.2 (after): regex matrix for figure-reference detection — re-run of
# g5_regex_matrix.py against the EDITED modules/figure_context_manager.py,
# with the input table extended by Dmitry's negatives (batch G5.1+G5.2 prompt).
# Imports the REAL functions; no product code is modified; no network.
import os, sys
sys.path.insert(0, os.getcwd())
from modules.figure_context_manager import normalize_figure_ref, FigureContextManager

class App:
    def log(self, *a, **k): pass
fc = FigureContextManager(App())

# File-name normalization: what ref does a filename map to?
FILENAMES = [
    "Figure 1A.png", "figure_1a.PNG", "Fig 1A.jpg", "1A.png",
    "Figure 1.png", "fig3b.png", "Fig. 3-B.png", "figure1.png",
    "Figure 10.png", "Fig.1.png", "figure_10c.tiff", "IMG_001.png",
    "Figure 1A and 1B.png", "Рисунок 1.png",
    # G5.2 additions:
    "figure_1a_and_1b.png", "Figure 1A-B.png", "fig_2.jpg",
    "Рис. 3.png", "рисунки 2.png", "Figure1.png",
]

# Segment-text inputs (the prompt's required table + negatives from G5.2f)
SEGMENTS = [
    "As shown in Figure 1A, the gear engages.",
    "see figure 2b for details",
    "FIGURE 3 shows the assembly",
    "See Fig. 1 for the diagram",
    "See Fig.1-3 for the diagrams",
    "See Figures 1 and 2 for details",
    "See Figure 1A and 1B together",
    "(Figure 4) is referenced here",
    "Refer to Figure 10 below",
    "Table 1 lists the values",
    "Рисунок 1 показывает узел",
    "Figure1 is glued",
    "See Figure 1A here",
    "See Figure 1A",
    "See Figure 1A and 1B",
    "Figures 1 and 2 are shown",
    "see fig. 4",
    "see fig 4",
    "figuur 5 in the manual",
    "Figure 1A, Figure 2B and Figure 3C",
    "See Fig 1A",
    "See Fig.1A",
    "figure 1a",
    "Figure 1A (see Fig. 2B)",
    "no figure reference here",
    "Fig. 1A and Fig. 2B",
    "Figures 1, 2 and 3",
    "Figures 1, 2, and 3",
    "See figure 1A, figure 2B",
    "Figure 1A/B",
    "Fig. 1A-B",
    "Figure 1A-B",
    "Figures 1A-1B",
    "Fig.1A",
    "Fig.1A-B",
    "See Figure 1A and Figure 1B",
    "Figures 1A and 1B",
    "Figure 1A and 1B",
    "see figure 1a and 1b",
    "Figure 1A and 1B (Figures 2A and 2B)",
    "See Fig. 1A",
    "See Fig.1A and 1B",
    "Fig. 1A and 1B",
    "Figure 1A and 1B and 2C",
    "Figures 1A and 1B and 2C",
    "See Figure 1A and 1B and 2C and 3D",
    "Figure 1A and 1B and 2C and 3D and 4E",
    "Fig. 1A and 1B and 2C and 3D",
    # G5.2f negatives (Dmitry's list):
    "Figure",
    "Figure.",
    "figures of speech",
    "configuration",
    "Config. 3",
    "Table 1",
    "prefigure 2",
    "Fig",
    "Figure 1 and 2018",
    "Fig.1A and 1B",          # glued
    "See\u00a0Figure\u00a01A",   # nbsp variants
    "Figure\u00a01A\u00a0and\u00a01B",
    "рис. 3 показан",
    "нарисуй 2",
    "![Image](..\\Figure 2.jpg)",   # md indirect path (P10 regression)
]

print("=== FILENAME -> normalized ref (normalize_figure_ref) ===")
for fn in FILENAMES:
    print(f"  {fn!r:30} -> {normalize_figure_ref(fn)!r}")

print()
print("=== SEGMENT -> detected refs (detect_figure_references) ===")
for seg in SEGMENTS:
    refs = fc.detect_figure_references(seg)
    print(f"  {seg!r:55} -> {refs}")

print()
print("=== CROSS: for each segment, which filenames match the detected refs? ===")
file_map = {normalize_figure_ref(fn): fn for fn in FILENAMES if normalize_figure_ref(fn)}
for seg in SEGMENTS:
    refs = fc.detect_figure_references(seg)
    matched = [file_map[r] for r in refs if r in file_map]
    print(f"  {seg!r:55} refs={refs} files={matched}")
