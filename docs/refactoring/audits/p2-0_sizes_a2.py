import os

ROOT = r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\unpacked"
SP = os.path.join(ROOT, "python-embed", "Lib", "site-packages")

def mb(n): return round(n / 1024 / 1024, 1)

def dir_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            try: total += os.path.getsize(os.path.join(dirpath, f))
            except OSError: pass
    return total

def tree(path):
    out = []
    for name in sorted(os.listdir(path)):
        p = os.path.join(path, name)
        if os.path.isdir(p): out.append((name, dir_size(p)))
        else: out.append((name, os.path.getsize(p)))
    return out

QT6 = os.path.join(SP, "PyQt6", "Qt6")
print("=== PyQt6/Qt6 subdirs ===")
for name, size in sorted(tree(QT6), key=lambda r: -r[1]):
    print(f"{mb(size):>9} MB  {name}")

BIN = os.path.join(QT6, "bin")
print("\n=== PyQt6/Qt6/bin top 25 DLLs ===")
for name, size in sorted(tree(BIN), key=lambda r: -r[1])[:25]:
    print(f"{mb(size):>9} MB  {name}")

print("\n=== PyQt6/Qt6/plugins ===")
for name, size in sorted(tree(os.path.join(QT6, "plugins")), key=lambda r: -r[1]):
    print(f"{mb(size):>9} MB  {name}")

for sub in ("translations", "qml", "metatypes", "libexec"):
    p = os.path.join(QT6, sub)
    if os.path.isdir(p):
        print(f"\n=== PyQt6/Qt6/{sub} === TOTAL {mb(dir_size(p))} MB")

print("\n=== TOP-40 biggest files in whole build root ===")
allfiles = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        p = os.path.join(dirpath, f)
        try: allfiles.append((os.path.getsize(p), os.path.relpath(p, ROOT)))
        except OSError: pass
for size, rel in sorted(allfiles, reverse=True)[:40]:
    print(f"{mb(size):>9} MB  {rel}")

# bindings / .pyi inside PyQt6 root (type stubs shipped?)
print("\n=== PyQt6 .pyi stubs total ===")
pyi = [f for f in allfiles if f[1].startswith("python-embed\\Lib\\site-packages\\PyQt6") and f[1].endswith(".pyi")]
print(f"{len(pyi)} files, {mb(sum(s for s,_ in pyi))} MB")
