# G3.2e Q8 inventory: all product call sites of send_ai_request /
# translate / translate_with_usage with their skip_cleaning/is_analysis kwargs.
import ast, pathlib, sys
ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
TARGETS = {"send_ai_request", "translate", "translate_with_usage"}

def kwrepr(call):
    out = {}
    for kw in call.keywords:
        v = kw.value
        if isinstance(v, ast.Constant):
            out[kw.arg] = repr(v.value)
        elif isinstance(v, ast.Name):
            out[kw.arg] = v.id
        else:
            out[kw.arg] = ast.dump(v)[:60]
    return out

rows = []
files = [ROOT / "Supervertaler.py"] + sorted(ROOT.glob("modules/**/*.py"))
for f in files:
    if "__pycache__" in str(f):
        continue
    tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else None)
            if name in TARGETS and name != "def":
                recv = ast.unparse(fn)[:50] if isinstance(fn, ast.Attribute) else ast.unparse(fn)
                rows.append((str(f.relative_to(ROOT)), node.lineno, name, recv, kwrepr(node)))
for r in rows:
    print(f"{r[0]}:{r[1]} {r[2]} recv={r[3]} kwargs={r[4]}")
print(f"TOTAL {len(rows)} call sites")
