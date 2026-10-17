"""Batch G5.2b (coordinator verdict 2026-10-17, answer 2): comma rule matrix.

Complements g5_2_regex_matrix_after.py (that file and its log are NOT
touched). Rule under test:
  - after and/&/or any 1-3-digit token is accepted;
  - after a comma only a token with a letter suffix (1A, 1B) is accepted,
    unless the keyword is plural (Figures 1, 2 and 3);
  - token boundary: no partial year match (201 must not come out of 2018).
Run: E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/g5_2b_comma_matrix.py
"""
import os, sys
sys.path.insert(0, os.getcwd())
from modules.figure_context_manager import FigureContextManager


class _App:
    def log(self, *a, **k):
        pass


fc = FigureContextManager(_App())

# (segment, expected refs) — coordinator's cases first, then the
# regression set proving the old matrix cases are unchanged.
CASES = [
    # --- coordinator's cases (verdict answer 2) ---
    ("Figure 3, 12 soldiers advance", ['3']),
    ("see Figure 3, 12 soldiers advance", ['3']),
    ("Figure 1A, 1B", ['1a', '1b']),
    ("Figures 1, 2 and 3", ['1', '2', '3']),
    ("Figure 1, 2018", ['1']),
    ("Figure 1 and 2018", ['1']),
    ("Figure 1, 201", ['1']),
    # --- boundary: 3-digit token limit must not partial-match a year ---
    ("Figure 1, 2018 and 2019", ['1']),
    ("Figures 1, 2018", ['1']),  # 2018 is 4 digits -> never a token, plural keyword included
    # --- singular keyword + comma: bare numbers rejected ---
    ("Figure 1, 2", ['1']),
    ("Figure 1, 2, 3", ['1']),
    ("Рисунок 1, 2 показан", ['1']),
    # --- plural keyword + comma: bare numbers accepted ---
    ("Figures 1, 2", ['1', '2']),
    ("Figures 1, 2, 3", ['1', '2', '3']),
    ("Figures 1, 2, and 3", ['1', '2', '3']),
    ("Figures 1, 201", ['1', '201']),
    ("Рисунки 1, 2 показаны", ['1', '2']),
    # --- letter-suffix chains after comma (singular keyword legal) ---
    ("Figure 1A, 1B, 2C", ['1a', '1b', '2c']),
    ("Fig. 1A, 2B", ['1a', '2b']),
    ("See figure 1A, figure 2B", ['1a', '2b']),
    # --- and/&/or keep accepting any number (unchanged) ---
    ("Figure 1 & 2", ['1', '2']),
    ("Figure 1 or 2", ['1', '2']),
    ("Figure 1A and 1B", ['1a', '1b']),
    ("See Figures 1 and 2 for details", ['1', '2']),
    # --- unchanged from matrix after (regression) ---
    ("As shown in Figure 1A, the gear engages.", ['1a']),
    ("See Fig.1-3 for the diagrams", ['1']),
    ("Figure 1A/B", ['1a']),
    ("Fig. 1A-B", ['1a']),
    ("Figure 1A and 1B (Figures 2A and 2B)", ['1a', '1b', '2a', '2b']),
    ("Figure 1A, Figure 2B and Figure 3C", ['1a', '2b', '3c']),
    ("Figure", []),
    ("figures of speech", []),
    ("configuration", []),
    ("Config. 3", []),
    ("Table 1", []),
    ("prefigure 2", []),
    ("Fig", []),
    ("рис. 3 показан", ['3']),
    ("нарисуй 2", []),
    ("![Image](..\\Figure 2.jpg)", ['2']),
]

fails = 0
print("=== SEGMENT -> detected refs (comma rule, G5.2b) ===")
for seg, expected in CASES:
    got = fc.detect_figure_references(seg)
    ok = got == expected
    if not ok:
        fails += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {seg!r:45} -> {got}  (expected {expected})")

print(f"\nTOTAL {len(CASES) - fails}/{len(CASES)} PASS")
sys.exit(1 if fails else 0)
