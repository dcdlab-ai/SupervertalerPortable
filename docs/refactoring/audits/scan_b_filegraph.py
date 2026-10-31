import ast, os, sys, json
from collections import deque

REPO = r"E:\Dev\SupervertalerPortable"
sys.path.insert(0, REPO)

# local module names resolvable via modules/ on sys.path
MODDIR = os.path.join(REPO, "modules")
local_top = set()
for name in os.listdir(MODDIR):
    if name.endswith(".py"):
        local_top.add(name[:-3])
    elif os.path.isdir(os.path.join(MODDIR, name)) and os.path.exists(os.path.join(MODDIR, name, "__init__.py")):
        local_top.add(name)
local_top |= {"Supervertaler"}
for sub in ("dialogs", "grid", "workers"):
    pass  # subpackages via modules.dialogs.X

# also modules.dialogs.X etc are package-qualified (modules.*) so handled by prefix

all_files = {"Supervertaler": os.path.join(REPO, "Supervertaler.py")}
for dirpath, dirnames, filenames in os.walk(MODDIR):
    for f in filenames:
        if f.endswith(".py"):
            rel = os.path.relpath(os.path.join(dirpath, f), REPO)
            mod = rel[:-3].replace("\\", ".").replace("/", ".")
            all_files[mod] = os.path.join(dirpath, f)

def parents_map(tree):
    p = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            p[ch] = node
    return p

def stack_of(p, node):
    s = []
    cur = node
    while cur in p:
        cur = p[cur]
        s.append(cur)
    return s

def kind_of(p, node):
    s = stack_of(p, node)
    in_func = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) for n in s)
    in_try = any(isinstance(n, (ast.Try, getattr(ast, "TryStar", ast.Try))) for n in s)
    if in_func: return "lazy"
    if in_try: return "guarded"
    return "mandatory"

def resolve(rootname, dotted):
    """given import target 'a.b.c', find matching internal file key"""
    if dotted in all_files:
        return dotted
    if dotted.startswith("modules."):
        parts = dotted.split(".")[1:]
        if os.path.exists(os.path.join(MODDIR, *parts) + ".py"):
            return dotted
        pkgdir = os.path.join(MODDIR, *parts)
        if os.path.isdir(pkgdir) and os.path.exists(os.path.join(pkgdir, "__init__.py")):
            return dotted + ".__init__"
        return None
    if dotted in local_top:
        if os.path.exists(os.path.join(MODDIR, dotted + ".py")):
            return "modules." + dotted
        pkgdir = os.path.join(MODDIR, dotted)
        if os.path.isdir(pkgdir) and os.path.exists(os.path.join(pkgdir, "__init__.py")):
            return "modules." + dotted + ".__init__"
    # plain 'import tag_manager' from a modules file -> modules.tag_manager
    if rootname in local_top and not dotted.startswith("modules.") and "." not in dotted:
        cand = "modules." + dotted
        if cand in all_files:
            return cand
    return None

edges = {}  # file -> list of (target_file, kind)
for mod, fname in all_files.items():
    src = open(fname, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src, filename=fname)
    except SyntaxError as e:
        print("SYNTAXERR", mod, e); continue
    p = parents_map(tree)
    lst = []
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Import):
            targets = [(a.name, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                base = mod.split(".")
                base = base[:-node.level]
                full = ".".join(base + ([node.module] if node.module else []))
                if node.module:
                    targets.append((full, full))
                    for a in node.names:  # imported name may itself be a submodule
                        targets.append((full + "." + a.name, full + "." + a.name))
                else:
                    for a in node.names:  # 'from . import X'
                        targets.append((full + "." + a.name, full + "." + a.name))
            else:
                if node.module:
                    targets.append((node.module, node.module))
                    # from X import Y may import a SUBMODULE Y of package X
                    if node.module in ("modules",) or node.module.startswith("modules."):
                        for a in node.names:
                            targets.append((node.module + "." + a.name, node.module + "." + a.name))
        for orig, dotted in targets:
            root = dotted.split(".")[0]
            if root in ("modules", "Supervertaler") or root in local_top:
                t = resolve(root, dotted)
                if t and t != mod:
                    lst.append((t, kind_of(p, node)))
    edges[mod] = lst

# BFS from Supervertaler over mandatory edges only
mandatory_files = set()
q = deque(["Supervertaler"])
mandatory_files.add("Supervertaler")
while q:
    cur = q.popleft()
    for t, k in edges.get(cur, []):
        if k == "mandatory" and t not in mandatory_files:
            mandatory_files.add(t)
            q.append(t)

# files referenced at all
all_referenced = set()
for f, lst in edges.items():
    for t, k in lst:
        all_referenced.add(t)

never = sorted(set(all_files) - all_referenced - {"Supervertaler"})
lazy_only = sorted(all_referenced - mandatory_files - {"Supervertaler"})

print("=== MANDATORY FILES (loaded at startup via unguarded top-level imports) ===")
for f in sorted(mandatory_files):
    print("  ", f)
print(f"\nTOTAL mandatory: {len(mandatory_files)} / {len(all_files)} files")
print("\n=== LAZY/GUARDED-ONLY FILES (referenced but not startup) ===")
for f in lazy_only:
    print("  ", f)
print("\n=== NEVER IMPORTED (dead files?) ===")
for f in never:
    print("  ", f)

# who imports pdf_rescue_Qt?
print("\n=== Importers of pdf_rescue_Qt ===")
for f, lst in edges.items():
    for t, k in lst:
        if "pdf_rescue" in t:
            print(f"  {f} ({k}) -> {t}")
print("\n=== Importers of llm_clients ===")
for f, lst in edges.items():
    for t, k in lst:
        if t.endswith("llm_clients"):
            print(f"  {f} ({k}) -> {t}")

json.dump({"mandatory_files": sorted(mandatory_files), "lazy_only": lazy_only, "never": never,
           "edges": {k: v for k, v in edges.items()}},
          open(r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\filegraph.json", "w"), indent=1)
