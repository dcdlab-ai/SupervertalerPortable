"""Independent reachability: parse every .py in the repo with AST, build
import edges (import / from-import incl. relative, importlib.import_module,
__import__ with literal strings), then BFS from roots.
Roots: Supervertaler.py, setup.py, tools/**, tests/** (consumers).
Prints live/orphan sets. Independent of importer_scan.py (AST-direct)."""
import ast
import os
import sys

REPO = r"E:\Dev\SupervertalerPortable"

def py_files():
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "python-embed", "node_modules")]
        for f in files:
            if f.endswith(".py"):
                out.append(os.path.join(root, f))
    return out

def dotted(rel):
    return rel[:-3].replace(os.sep, ".")

def pkg_parts(rel):
    parts = dotted(rel).split(".")
    return parts[:-1] if parts[-1] == "__init__" else parts[:-1]

def resolve_rel(parts, level, module):
    if level == 0:
        return module or ""
    p = list(parts)
    p = p[: len(p) - (level - 1)]
    if module:
        p = p + module.split(".")
    return ".".join(p)

# module inventory (targets)
targets = set()
for p in py_files():
    rel = os.path.relpath(p, REPO)
    if rel.startswith("modules" + os.sep) or (os.sep not in rel):
        targets.add(dotted(rel))

edges = {t: set() for t in targets}  # target -> set of importer dotted names

def add_edge(target, importer):
    parts = target.split(".")
    for i in range(1, len(parts) + 1):
        prefix = ".".join(parts[:i])
        edges.setdefault(prefix, set()).add(importer)
        init = prefix + ".__init__"
        if init in targets:
            edges.setdefault(init, set()).add(importer)

for p in py_files():
    rel = os.path.relpath(p, REPO)
    importer = dotted(rel)
    src = open(p, "r", encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                add_edge(a.name, importer)
        elif isinstance(node, ast.ImportFrom):
            mod = resolve_rel(pkg_parts(rel), node.level, node.module)
            if mod:
                add_edge(mod, importer)
            for a in node.names:
                cand = f"{mod}.{a.name}" if mod else a.name
                if cand in targets:
                    edges.setdefault(cand, set()).add(importer)
        elif isinstance(node, ast.Call):
            f = node.func
            fname = None
            if isinstance(f, ast.Attribute) and f.attr == "import_module":
                base = f.value
                if isinstance(base, ast.Name) and base.id == "importlib":
                    fname = "import_module"
            elif isinstance(f, ast.Name) and f.id == "__import__":
                fname = "__import__"
            if fname and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                add_edge(node.args[0].value, importer)

roots = {"Supervertaler", "setup"}
for t in targets:
    if t.startswith("tools.") or t.startswith("tests."):
        roots.add(t)

live = set(roots)
reverse = {}
for t, imps in edges.items():
    for i in imps:
        reverse.setdefault(i, set()).add(t)
stack = list(roots)
while stack:
    x = stack.pop()
    for child in reverse.get(x, ()):
        if child in targets and child not in live:
            live.add(child)
            stack.append(child)

orphans = sorted(t for t in targets if t not in live)
print(f"targets={len(targets)} live={len(live & targets)} orphan={len(orphans)}")
print("\n=== ORPHANS (AST-direct, roots incl. tools/tests) ===")
for t in orphans:
    print(t)
