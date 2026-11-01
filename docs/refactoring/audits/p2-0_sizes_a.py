import os, sys, json

ROOT = r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\unpacked"

def dir_size(path, skip_names=()):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in skip_names]
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total

def tree_sizes(path):
    """size of each immediate child (file or dir, recursive)"""
    out = []
    for name in sorted(os.listdir(path)):
        p = os.path.join(path, name)
        if os.path.isdir(p):
            out.append((name, dir_size(p), "dir"))
        else:
            out.append((name, os.path.getsize(p), "file"))
    return out

def mb(n): return round(n / 1024 / 1024, 1)

report = {}

# 1. Build-root top-level
print("=== BUILD ROOT (unpacked, top-level) ===")
rows = tree_sizes(ROOT)
tot = 0
for name, size, kind in sorted(rows, key=lambda r: -r[1]):
    print(f"{mb(size):>9} MB  {kind:4}  {name}")
    tot += size
print(f"{mb(tot):>9} MB  TOTAL")

# 2. python-embed top level
PE = os.path.join(ROOT, "python-embed")
print("\n=== python-embed (top-level) ===")
for name, size, kind in sorted(tree_sizes(PE), key=lambda r: -r[1]):
    print(f"{mb(size):>9} MB  {kind:4}  {name}")

SP = os.path.join(PE, "Lib", "site-packages")

# 3. site-packages: every package dir, top-40
print("\n=== site-packages: ALL entries sorted by size (top 45) ===")
rows = tree_sizes(SP)
grand = 0
for name, size, kind in sorted(rows, key=lambda r: -r[1])[:45]:
    print(f"{mb(size):>9} MB  {kind:4}  {name}")
grand = sum(s for _, s, _ in rows)
print(f"{mb(grand):>9} MB  site-packages TOTAL")

# 4. PyQt6 subpackage breakdown
QT = os.path.join(SP, "PyQt6")
if os.path.isdir(QT):
    print("\n=== PyQt6 subpackages ===")
    for name, size, kind in sorted(tree_sizes(QT), key=lambda r: -r[1]):
        print(f"{mb(size):>9} MB  {kind:4}  {name}")

# 5. Junk inside site-packages: __pycache__, tests, docs, dist-info
print("\n=== Junk inside site-packages ===")
junk_pycache = 0; junk_tests = 0; junk_docs = 0
n_pycache = n_tests = n_docs = 0
for dirpath, dirnames, filenames in os.walk(SP):
    for d in list(dirnames):
        p = os.path.join(dirpath, d)
        if d == "__pycache__":
            s = dir_size(p); junk_pycache += s; n_pycache += 1
        elif d.lower() in ("tests", "test"):
            s = dir_size(p); junk_tests += s; n_tests += 1
        elif d.lower() in ("docs", "doc", "docsource", "examples", "demos"):
            s = dir_size(p); junk_docs += s; n_docs += 1
print(f"__pycache__ dirs: {n_pycache} dirs, {mb(junk_pycache)} MB")
print(f"tests dirs      : {n_tests} dirs, {mb(junk_tests)} MB")
print(f"docs/examples   : {n_docs} dirs, {mb(junk_docs)} MB")

# dist-info count
dis = [d for d in os.listdir(SP) if d.endswith(".dist-info")]
print(f"dist-info entries: {len(dis)}")
print("INSTALLED PACKAGES:")
for d in sorted(dis):
    print("  ", d)

# 6. Code folder (SupervertalerPortable) breakdown
CODE = os.path.join(ROOT, "SupervertalerPortable")
print("\n=== SupervertalerPortable (code folder) ===")
for name, size, kind in sorted(tree_sizes(CODE), key=lambda r: -r[1]):
    print(f"{mb(size):>9} MB  {kind:4}  {name}")

# zip compressed per top-level
print("\n=== ZIP: compressed sizes ===")
import zipfile
zf = zipfile.ZipFile(r"E:\Dev\Work_temp\SupervertalerPortable\build\supervertaler-portable_20261031_1843.zip")
comp = {}; unc = {}
for i in zf.infolist():
    top = i.filename.split("/")[0]
    comp[top] = comp.get(top, 0) + i.compress_size
    unc[top] = unc.get(top, 0) + i.file_size
for top in sorted(comp):
    print(f"{mb(comp[top]):>9} MB compressed / {mb(unc[top]):>9} MB raw  {top}")
print(f"{mb(sum(comp.values())):>9} MB compressed TOTAL (zip file: 334,878,720)")
