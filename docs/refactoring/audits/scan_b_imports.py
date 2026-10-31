import ast, os, sys, json

REPO = r"E:\Dev\SupervertalerPortable"
sys.path.insert(0, REPO)
STDLIB = set(sys.stdlib_module_names)
PROJECT = {"Supervertaler", "modules"}  # top-level project roots

files = [os.path.join(REPO, "Supervertaler.py")]
for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, "modules")):
    for f in filenames:
        if f.endswith(".py"):
            files.append(os.path.join(dirpath, f))

MANDATORY = {}
GUARDED = {}
LAZY = {}
ATTR = {}

BUCKETS = {"mandatory": MANDATORY, "guarded": GUARDED, "lazy": LAZY}

def stack_of(parents, node):
    s = []
    cur = node
    while cur in parents:
        cur = parents[cur]
        s.append(cur)
    return s

def enclosing_kind(node_stack):
    in_func = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) for n in node_stack)
    in_try = False
    if not in_func:
        for n in node_stack:
            if isinstance(n, ast.Try) or (hasattr(ast, "TryStar") and isinstance(n, ast.TryStar)):
                in_try = True
    if in_func:
        return "lazy"
    if in_try:
        return "guarded"
    return "mandatory"

def add(kind, name, fname, line):
    BUCKETS[kind].setdefault(name, []).append(f"{os.path.relpath(fname, REPO)}:{line}")

for fname in files:
    src = open(fname, encoding="utf-8", errors="replace").read()
    tree = ast.parse(src, filename=fname)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in PROJECT or root in STDLIB or root == "__future__":
                    continue
                add(enclosing_kind(stack_of(parents, node)), root, fname, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            mod = node.module or ""
            root = mod.split(".")[0]
            if not root or root in PROJECT or root in STDLIB or root == "__future__":
                continue
            add(enclosing_kind(stack_of(parents, node)), root, fname, node.lineno)
        elif isinstance(node, ast.Call):
            f = node.func
            dyn = False
            if isinstance(f, ast.Attribute) and f.attr == "import_module" and isinstance(f.value, ast.Name) and f.value.id == "importlib":
                dyn = True
            if isinstance(f, ast.Name) and f.id in ("__import__", "import_module"):
                dyn = True
            if dyn:
                ATTR.setdefault("DYNAMIC_IMPORT", []).append(f"{os.path.relpath(fname, REPO)}:{node.lineno}")

print("=== MANDATORY (top-level, unguarded) ===")
for name in sorted(MANDATORY):
    print(f"  {name}: {', '.join(MANDATORY[name])}")
print("\n=== GUARDED (top-level inside try/except) ===")
for name in sorted(GUARDED):
    print(f"  {name}: {', '.join(GUARDED[name])}")
print("\n=== LAZY (inside functions/classes) ===")
for name in sorted(LAZY):
    print(f"  {name}: {len(LAZY[name])} sites: {', '.join(LAZY[name][:8])}{' ...' if len(LAZY[name])>8 else ''}")
print("\n=== DYNAMIC IMPORT SITES ===")
for s in ATTR.get("DYNAMIC_IMPORT", []):
    print("  ", s)

json.dump({"mandatory": MANDATORY, "guarded": GUARDED, "lazy": LAZY, "dynamic": ATTR.get("DYNAMIC_IMPORT", [])},
          open(r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\imports_raw.json", "w"), indent=1)
