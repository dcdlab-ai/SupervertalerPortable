# -*- coding: utf-8 -*-
"""Batch P1-A step 0: baseline snapshots of the to-be-removed blocks.

Extracts byte-exact line ranges from the worktree Supervertaler.py into
snapshot files with sha256, plus whole-file hashes, plus AST method
boundaries (to confirm the ranges are exactly whole methods / blocks).
"""
import ast, hashlib, pathlib, sys

TREE = pathlib.Path(r"E:\Dev\SupervertalerPortable")
STAGE = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1a")
SNAP = STAGE / "snapshots"
SNAP.mkdir(parents=True, exist_ok=True)

src = (TREE / "Supervertaler.py").read_bytes()
text = src.decode("utf-8")
# split preserving line endings: use splitlines(keepends=True)
lines = text.splitlines(keepends=True)
print(f"Supervertaler.py: {len(lines)} lines, {len(src)} bytes")

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

# (name, start, end) 1-based inclusive
BLOCKS = [
    ("p11a_call",        6436,  6438),
    ("p11a_privacy",    20814, 20839),
    ("p11a_initmethod", 37093, 37116),
    ("p11b_trayblock",  26501, 26517),
    ("p11b_trayhandler",26623, 26648),
    ("p12_import",        429,   429),
    ("p12_menuitem",     8536,  8540),
    ("p12_updatecluster",48286, 48827),
    ("p12_aboutbtn",    48998, 49002),
]

manifest = []
for name, a, b in BLOCKS:
    blob = "".join(lines[a-1:b]).encode("utf-8")
    (SNAP / f"{name}.txt").write_bytes(blob)
    manifest.append(f"{sha(blob)}  {name}  lines {a}-{b}  {len(blob)} bytes")

for rel in ("Supervertaler.py", "modules/usage_statistics.py", "modules/autostart.py"):
    b = (TREE / rel).read_bytes()
    n = b.count(b"\n")
    cr = b.count(b"\r")
    manifest.append(f"{sha(b)}  FILE {rel}  {n} lines  CR={cr}")

# --- AST method boundaries -------------------------------------------------
tree = ast.parse(text)
want = {
    "_init_usage_statistics", "_on_toggle_autostart", "check_for_updates",
    "_fetch_latest_release_info_from_github", "_normalize_version_tuple",
    "_format_version_for_display", "copy_version_info_to_clipboard",
    "show_about", "_tray_quit", "restore_last_project_if_enabled",
    "_setup_tray_icon", "_on_toggle_start_minimized", "_on_toggle_close_to_tray",
}
ast_lines = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in want:
        ast_lines.append(f"{node.name}: def@{node.lineno} end@{node.end_lineno}")
manifest.append("--- AST method boundaries ---")
manifest.extend(sorted(ast_lines))

(SNAP / "baseline_manifest.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")
print("\n".join(manifest))
