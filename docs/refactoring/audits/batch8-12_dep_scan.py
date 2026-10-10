"""Section B: for each requirement, find importers in code (live vs orphan).

Top-level import names per distribution (from installed metadata where available,
else a curated map). For each package: list importing files, split by live/orphan
using reach.py's live set (recomputed here).
"""
import ast
import os
import sys
import importlib.metadata as md

REPO = r"E:\Dev\SupervertalerPortable"

# live set from reach.py output (it lists ORPHANS; live = targets - orphans)
targets = set()
for root, dirs, files in os.walk(os.path.join(REPO, "modules")):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py"):
            rel = os.path.relpath(os.path.join(root, f), REPO)
            targets.add(rel[:-3].replace(os.sep, "."))
targets.add("Supervertaler")
targets.add("setup")
orphans = set()
mode = False
for line in open(r"D:\Temp\SupervertalerPortable\refactoring\batch8-12\reach_v3.txt", encoding="utf-8"):
    line = line.strip()
    if line.startswith("=== ORPHANS"):
        mode = True
        continue
    if mode and line:
        orphans.add(line)
live = targets - orphans

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
    p = list(parts)
    if level > 0:
        p = p[: len(p) - (level - 1)]
    if module:
        p = p + module.split(".")
    return ".".join(p)

# collect all top-level import roots per file
imports = {}  # file -> set of top-level module names
for p in py_files():
    rel = os.path.relpath(p, REPO)
    src = open(p, "r", encoding="utf-8").read()
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
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
                names.add(node.args[0].value.split(".")[0])
    imports[rel] = names

# distribution -> top-level import names
DIST = {
    "setuptools": ["setuptools", "pkg_resources"],
    "wheel": [],
    "PyQt6": ["PyQt6"],
    "PyQt6-WebEngine": ["PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets"],
    "python-docx": ["docx"],
    "openpyxl": ["openpyxl"],
    "Pillow": ["PIL"],
    "lxml": ["lxml"],
    "openai": ["openai"],
    "anthropic": ["anthropic"],
    "google-generativeai": ["google.generativeai", "google"],
    "requests": ["requests"],
    "markitdown": ["markitdown"],
    "sacrebleu": ["sacrebleu"],
    "pyperclip": ["pyperclip"],
    "chardet": ["chardet"],
    "pyyaml": ["yaml"],
    "markdown": ["markdown"],
    "pyspellchecker": ["spellchecker"],
    "spylls": ["spylls"],
    "numpy": ["numpy"],
    "PyMuPDF": ["fitz", "pymupdf"],
    "boto3": ["boto3"],
    "deepl": ["deepl"],
    "psutil": ["psutil"],
    "pynput": ["pynput"],
    "pyobjc-framework-Cocoa": ["objc", "Foundation", "AppKit"],
    "sounddevice": ["sounddevice"],
    "ahk": ["ahk"],
    "vosk": ["vosk"],
    "faster-whisper": ["faster_whisper"],
}

def classify(f):
    if f == "Supervertaler.py":
        return "LIVE"
    d = dotted(f)
    if d.startswith("tools.") or d.startswith("tests."):
        return "TOOL"
    return "LIVE" if d in live else "ORPHAN"

for dist, tops in DIST.items():
    hits = []
    for f, names in imports.items():
        for t in tops:
            if t in names:
                hits.append((f, classify(f)))
                break
    print(f"\n=== {dist} (top-level: {', '.join(tops) if tops else '-'}) ===")
    from collections import Counter
    c = Counter(h[1] for h in hits)
    print(f"  importers: {len(hits)}  {dict(c)}")
    for f, k in sorted(hits):
        print(f"   {k:7s} {f}")

# transitive: check installed metadata for requirements of key packages
print("\n=== TRANSITIVE (installed metadata Requires-Dist) ===")
for dist in ["python-docx", "openpyxl", "Pillow", "markitdown", "sacrebleu", "spylls",
             "faster-whisper", "vosk", "openai", "anthropic", "google-generativeai",
             "requests", "pyspellchecker", "deepl", "boto3", "pynput", "psutil",
             "numpy", "PyMuPDF", "pyyaml", "markdown", "chardet", "pyperclip"]:
    try:
        meta = md.metadata(dist)
        reqs = [r for r in meta.get_all("Requires-Dist") or []]
        print(f"{dist}: {reqs}")
    except md.PackageNotFoundError:
        print(f"{dist}: NOT INSTALLED in bundled runtime")
