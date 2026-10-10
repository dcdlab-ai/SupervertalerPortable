# -*- coding: utf-8 -*-
"""Batch #8.12 Этап 1.2: публичные классы/функции 17 сирот и их имена в остальном коде.

Для каждого модуля: AST-список top-level class/function. Затем grep по
Supervertaler.py, modules/**, tools/**, tests/** (без __pycache__, без самих
сирот) на каждое имя как идентификатор (\bname\b). Вывод: имя -> файлы:строки.
"""
import ast
import pathlib
import re
import sys

REPO = pathlib.Path(r"E:\Dev\SupervertalerPortable")
ORPHANS = [
    "extract_tm", "feature_manager", "find_replace", "glossary_manager",
    "identifier_conventions", "pdf_rescue_tkinter", "project_home_panel",
    "project_tm", "prompt_assistant", "prompt_library", "quick_access_sidebar",
    "ribbon_widget", "style_guide_manager", "superdocs", "superdocs_viewer_qt",
    "tracked_changes", "translation_services",
]

names = {}
for m in ORPHANS:
    p = REPO / "modules" / f"{m}.py"
    tree = ast.parse(p.read_text(encoding="utf-8"))
    top = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            top.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            top.append(node.name)
    names[m] = top

# consumer files: everything py except the 17 orphans themselves
consumers = []
for p in REPO.rglob("*.py"):
    rel = p.relative_to(REPO).as_posix()
    if "__pycache__" in rel:
        continue
    if rel in [f"modules/{m}.py" for m in ORPHANS]:
        continue
    consumers.append((rel, p.read_text(encoding="utf-8", errors="replace")))

print("=== public names per orphan ===")
for m in ORPHANS:
    print(f"{m}: {', '.join(names[m]) if names[m] else '(none)'}")

print("\n=== name hits in consumer code ===")
all_names = sorted({n for m in ORPHANS for n in names[m]})
hits = {n: [] for n in all_names}
for rel, text in consumers:
    for i, line in enumerate(text.splitlines(), 1):
        for n in all_names:
            if re.search(rf"\b{n}\b", line):
                hits[n].append(f"{rel}:{i}: {line.strip()[:120]}")
for n in all_names:
    if hits[n]:
        print(f"--- {n} ({len(hits[n])} hits)")
        for h in hits[n][:12]:
            print(f"    {h}")
        if len(hits[n]) > 12:
            print(f"    ... +{len(hits[n])-12} more")
clean = [n for n in all_names if not hits[n]]
print(f"\n=== names with 0 hits in consumer code ({len(clean)}/{len(all_names)}) ===")
print(", ".join(clean))
