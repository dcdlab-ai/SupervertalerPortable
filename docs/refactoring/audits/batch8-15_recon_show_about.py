"""Recon E-01: все определения show_about в Supervertaler.py + вызовы."""
import ast, pathlib, re

src = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py").read_text(encoding="utf-8")
lines = src.splitlines()
tree = ast.parse(src)

print("=== def show_about / def *about* (all classes/top-level) ===")
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and "about" in sub.name.lower():
                print(f"class {node.name}: def {sub.name} @ {sub.lineno}-{sub.end_lineno} ({sub.end_lineno-sub.lineno+1} lines)")
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "about" in node.name.lower():
        print(f"top-level: def {node.name} @ {node.lineno}-{node.end_lineno}")

print("\n=== textual references to show_about ===")
for i, l in enumerate(lines, 1):
    if re.search(r"show_about", l):
        print(f"{i}: {l.rstrip()[:150]}")

print("\n=== body head of each show_about def ===")
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef) and sub.name == "show_about":
                seg = lines[sub.lineno-1:sub.lineno+7]
                print(f"--- class {node.name} @ {sub.lineno}-{sub.end_lineno} ---")
                for j, l in enumerate(seg, sub.lineno):
                    print(f"{j}: {l.rstrip()[:140]}")
