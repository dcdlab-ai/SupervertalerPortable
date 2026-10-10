"""Section A: full importer scan for every project module.

Forms covered:
  - import X / import X.Y (AST Import)
  - from X import ... incl. relative imports resolved to absolute (AST ImportFrom)
  - importlib.import_module("X") / __import__("X") with literal strings
  - getattr/hasattr/setattr(obj, "X") with literal strings
  - string constants containing the module dotted name or path form
    (modules.foo, modules/foo, modules\\foo)
  - non-Python files: .bat .spec .toml .cfg .json .md .txt .iss (grep)
Outputs JSON: module -> list of (file, line, form, snippet).
"""
import ast
import json
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

def nonpy_files():
    exts = (".bat", ".spec", ".toml", ".cfg", ".json", ".md", ".txt", ".iss", ".ini")
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "python-embed", "node_modules")]
        for f in files:
            if f.endswith(exts):
                out.append(os.path.join(root, f))
    return out

# module inventory: dotted name -> base name
modules = {}
for p in py_files():
    rel = os.path.relpath(p, REPO)
    if rel.startswith("modules" + os.sep):
        dotted = rel[:-3].replace(os.sep, ".")
    elif os.sep not in rel and rel != "Supervertaler.py":
        dotted = rel[:-3]
    elif rel == "Supervertaler.py":
        dotted = "Supervertaler"
    else:
        continue  # tools/**, tests/** are consumers, not inventory targets
    modules[dotted] = os.path.basename(rel)[:-3]

# resolve relative imports to absolute, from the file's PACKAGE (directory parts)
def resolve_rel(pkg_parts, level, module):
    if level == 0:
        return module or ""
    parts = list(pkg_parts)
    parts = parts[: len(parts) - (level - 1)]
    if module:
        parts = parts + module.split(".")
    return ".".join(parts)

class Collector(ast.NodeVisitor):
    def __init__(self, path, pkg_parts):
        self.path = path
        self.pkg_parts = pkg_parts
        self.hits = []  # (line, form, snippet)

    def visit_Import(self, node):
        for a in node.names:
            self.hits.append((node.lineno, "import", a.name))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        mod = resolve_rel(self.pkg_parts, node.level, node.module)
        names = ",".join(a.name for a in node.names)
        self.hits.append((node.lineno, "from", f"{mod} import {names}"))
        self.generic_visit(node)

    def visit_Call(self, node):
        f = node.func
        fname = None
        if isinstance(f, ast.Attribute):
            fname = f.attr
            base = f.value
            base_name = base.id if isinstance(base, ast.Name) else ""
            if fname == "import_module" and base_name in ("importlib", "importlib2"):
                fname = "importlib.import_module"
            elif fname == "__import__":
                fname = "__import__"
            else:
                fname = None
        elif isinstance(f, ast.Name):
            fname = f.id if f.id in ("__import__", "getattr", "hasattr", "setattr") else None
        if fname in ("importlib.import_module", "__import__", "getattr", "hasattr", "setattr"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                self.hits.append((node.lineno, fname, node.args[0].value))
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and len(node.value) > 3:
            self_name = ".".join(self.pkg_parts + [os.path.basename(self.path)[:-3]])
            for mname, base in modules.items():
                if mname == self_name:
                    continue
                forms = [mname, mname.replace(".", "/"), mname.replace(".", "\\")]
                for form in forms:
                    if form in node.value:
                        self.hits.append((node.lineno, "string", f"{form} in {node.value[:120]!r}"))
                        break
        self.generic_visit(node)

result = {m: [] for m in modules}
for p in py_files():
    rel = os.path.relpath(p, REPO)
    dotted_of_file = rel[:-3].replace(os.sep, ".")
    parts = dotted_of_file.split(".")
    if parts[-1] == "__init__":
        pkg_parts = parts[:-1]
    else:
        pkg_parts = parts[:-1]
    try:
        src = open(p, "r", encoding="utf-8").read()
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR {rel}: {e}", file=sys.stderr)
        continue
    c = Collector(rel, pkg_parts)
    c.visit(tree)
    def add_edge(target, form, snippet):
        parts = target.split(".")
        for i in range(1, len(parts) + 1):
            prefix = ".".join(parts[:i])
            if prefix in modules:
                result[prefix].append((rel, line, form, snippet))
            init = prefix + ".__init__"
            if init in modules:
                result[init].append((rel, line, form, snippet))
    for line, form, snippet in c.hits:
        # normalize import forms to dotted module
        if form == "import":
            add_edge(snippet, form, snippet)
        elif form == "from":
            target = snippet.split(" import ")[0]
            names = snippet.split(" import ")[-1]
            if target:
                add_edge(target, form, snippet)
            for n in names.split(","):
                n = n.strip()
                cand = f"{target}.{n}" if target else n
                if cand in modules:
                    result[cand].append((rel, line, form, snippet))
        else:
            # string forms: match against dotted/path/base forms
            for m, base in modules.items():
                if m == dotted_of_file:
                    continue
                forms = [m, m.replace(".", "/"), m.replace(".", "\\"),
                         m.replace(".", "/") + ".py", base + ".py"]
                hay = snippet
                if any(f in hay for f in forms):
                    result[m].append((rel, line, form, snippet))

# non-Python grep
nonpy_hits = {m: [] for m in modules}
for p in nonpy_files():
    rel = os.path.relpath(p, REPO)
    try:
        text = open(p, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        for m, base in modules.items():
            forms = [m, m.replace(".", "/"), m.replace(".", "\\"), base + ".py"]
            if any(f in line for f in forms):
                nonpy_hits[m].append((rel, i, "nonpy", line.strip()[:140]))

out = {"py_importers": result, "nonpy_hits": nonpy_hits}
with open(r"D:\Temp\SupervertalerPortable\refactoring\batch8-12\importers.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)

# summary
print(f"{'module':45s} py-hits nonpy-hits  importers(files)")
for m in sorted(modules):
    hits = result[m]
    files = sorted({h[0] for h in hits if h[2] in ("import", "from", "importlib.import_module", "__import__", "getattr", "hasattr", "setattr")})
    nph = nonpy_hits[m]
    print(f"{m:45s} {len(hits):7d} {len(nph):9d}  {','.join(files) if files else '-'}")
