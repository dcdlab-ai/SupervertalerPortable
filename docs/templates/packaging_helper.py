# -*- coding: utf-8 -*-
r"""BATCH P2.1 helper for make_portable_zip.bat (runs on the bundled runtime,
stdlib only). Three subcommands:

  prune <runtime-copy-dir>
      Remove the dev-junk exclusion list from a STAGED COPY of the embedded
      runtime (never from E:\Dev\python-embed itself). The list is the
      coordinator decision of 2026-10-31 (P2.0 verdict, item 4): pip stays,
      Qt is not trimmed, opengl32sw.dll stays.

  importsmoke
      Run by the STAGED python-embed AFTER the _pth patch: import the product
      monolith and the key third-party modules; exit 1 on any failure.

  zip <stage-root> <zip-file>
      Pack the stage root into a REAL zip (deflate), then verify: testzip()
      clean, entry count == file count of the tree, no absolute/drive/..
      paths, forward slashes only. Exit 1 on any failure.

Usage from the bat (REPO = repo root, RUNTIME = E:\Dev\python-embed):
  "%RUNTIME%\python.exe" "%REPO%\docs\templates\packaging_helper.py" prune "%STAGE%\python-embed"
  pushd "%STAGE%" && "%RUNTIME%"... actually the staged interpreter:
  "python-embed\python.exe" "%REPO%\docs\templates\packaging_helper.py" importsmoke
  "%RUNTIME%\python.exe" "%REPO%\docs\templates\packaging_helper.py" zip "%STAGE%" "%ZIPFILE%"
"""
import fnmatch
import os
import shutil
import sys
import time
import zipfile

# ---------------------------------------------------------------- exclusion
# Coordinator decision (P2.0 verdict 2026-10-31, item 4): remove from the
# DISTRIBUTIVE COPY only, dev runtime untouched. pip and pip-*.dist-info
# deliberately KEPT; PyQt6 .pyi kept; opengl32sw.dll kept; Qt not trimmed.
RUNTIME_EXCLUDE_DIRS = [
    "pygments",   # pytest dependency, never imported by the product
    "_pytest",    # pytest stack
    "pytest",
    "iniconfig",
    "pluggy",
    "colorama",
    "pyflakes",   # one-time deviation 2026-10-23 (AGENTS), product never imports
    "chardet",    # requests uses charset_normalizer
]
RUNTIME_EXCLUDE_FILES = [
    "get-pip.py",  # pip bootstrap; pip itself stays
]
# Dead entry-point shims of the excluded packages (runtime Scripts\ dir):
# each targets a module that prune removes, so the exe would be broken.
RUNTIME_EXCLUDE_SCRIPTS = [
    "pytest.exe", "py.test.exe",    # pytest
    "chardetect.exe",               # chardet
    "pyflakes.exe",                 # pyflakes
    "pygmentize.exe",               # pygments
]
# The matching <name>-<version>.dist-info directories are derived from
# RUNTIME_EXCLUDE_DIRS automatically ("pygments-2.21.0.dist-info" etc.).


def cmd_prune(runtime_copy: str) -> int:
    rt = os.path.abspath(runtime_copy)
    if not os.path.isdir(rt):
        print(f"[prune] FAIL: not a directory: {rt}")
        return 1
    sp = os.path.join(rt, "Lib", "site-packages")
    removed, missing = [], []
    total = 0
    for name in RUNTIME_EXCLUDE_DIRS:
        for root_dirs_dir in (sp, rt):
            p = os.path.join(root_dirs_dir, name)
            if os.path.isdir(p):
                sz = _tree_size(p)
                shutil.rmtree(p)
                removed.append((os.path.relpath(p, rt), sz))
                total += sz
            for entry in os.listdir(root_dirs_dir):
                if fnmatch.fnmatch(entry.lower(), f"{name}-*.dist-info"):
                    p = os.path.join(root_dirs_dir, entry)
                    if os.path.isdir(p):
                        sz = _tree_size(p)
                        shutil.rmtree(p)
                        removed.append((os.path.relpath(p, rt), sz))
                        total += sz
    for name in RUNTIME_EXCLUDE_FILES:
        p = os.path.join(rt, name)
        if os.path.isfile(p):
            sz = os.path.getsize(p)
            os.remove(p)
            removed.append((name, sz))
            total += sz
    scripts = os.path.join(rt, "Scripts")
    for name in RUNTIME_EXCLUDE_SCRIPTS:
        p = os.path.join(scripts, name)
        if os.path.isfile(p):
            sz = os.path.getsize(p)
            os.remove(p)
            removed.append((os.path.join("Scripts", name), sz))
            total += sz
    # drift report: every expected item must have been found
    for name in (RUNTIME_EXCLUDE_DIRS + RUNTIME_EXCLUDE_FILES
                 + RUNTIME_EXCLUDE_SCRIPTS):
        if not any(r.split(os.sep)[-1] == name or
                   r.split(os.sep)[-1].startswith(name + "-") for r, _ in removed):
            missing.append(name)
    for rel, sz in removed:
        print(f"[prune] removed {rel} ({sz/1024/1024:.1f} MB)")
    print(f"[prune] total removed: {total/1024/1024:.1f} MB, {len(removed)} items")
    if missing:
        # expected-but-absent: suspicious drift of the dev runtime, report it
        print(f"[prune] WARN not found (runtime drift?): {missing}")
    if not removed:
        print("[prune] FAIL: nothing removed - exclusion list matched nothing")
        return 1
    print("[prune] OK")
    return 0


def _tree_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def cmd_importsmoke() -> int:
    # Run by the STAGED interpreter: sys.path comes from the patched ._pth
    # (..\SupervertalerPortable + Lib\site-packages), not from cwd.
    modules = [
        "PyQt6.QtWidgets", "openai", "docx", "openpyxl", "PIL", "lxml",
        "yaml", "requests", "spellchecker", "Supervertaler",
    ]
    import importlib
    failed = []
    for name in modules:
        try:
            mod = importlib.import_module(name)
            ver = getattr(mod, "__version__", "?")
            # flush=True is mandatory: importing Supervertaler re-wraps
            # sys.stdout (Supervertaler.py:173) and discards the buffer.
            print(f"[importsmoke] OK {name} ({ver})", flush=True)
        except Exception as e:
            failed.append(name)
            print(f"[importsmoke] FAIL {name}: {type(e).__name__}: {e}", flush=True)
    if failed:
        print(f"[importsmoke] FAIL: {failed}", flush=True)
        return 1
    print("[importsmoke] OK all", len(modules), "modules", flush=True)
    return 0


def cmd_zip(stage_root: str, zip_path: str) -> int:
    stage = os.path.abspath(stage_root)
    zip_path = os.path.abspath(zip_path)
    if not os.path.isdir(stage):
        print(f"[zip] FAIL: not a directory: {stage}")
        return 1
    t0 = time.time()
    tree_files = 0
    tree_dirs = 0
    for root, dirs, files in os.walk(stage):
        tree_dirs += len(dirs)
        tree_files += len(files)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as zf:
        # deterministic walk order: top-level entries sorted
        for root, dirs, files in os.walk(stage):
            dirs.sort()
            rel_root = os.path.relpath(root, stage)
            if rel_root != ".":
                arc_dir = rel_root.replace(os.sep, "/") + "/"
                zf.writestr(zipfile.ZipInfo(arc_dir), b"")
            for f in sorted(files):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, stage).replace(os.sep, "/")
                zf.write(full, rel)
    size = os.path.getsize(zip_path)
    # --- post-write verification -------------------------------------------
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()  # reads every entry back, CRC check
        if bad is not None:
            print(f"[zip] FAIL: testzip() reports corrupt entry: {bad}")
            return 1
        names = zf.namelist()
        z_files = [n for n in names if not n.endswith("/")]
        z_dirs = [n for n in names if n.endswith("/")]
        if len(z_files) != tree_files:
            print(f"[zip] FAIL: zip has {len(z_files)} file entries, tree has {tree_files}")
            return 1
        if len(z_dirs) != tree_dirs:
            print(f"[zip] FAIL: zip has {len(z_dirs)} dir entries, tree has {tree_dirs}")
            return 1
        for n in names:
            if "\\" in n or n.startswith("/") or ":" in n or ".." in n.split("/"):
                print(f"[zip] FAIL: unsafe entry name: {n!r}")
                return 1
    print(f"[zip] OK: {zip_path}")
    print(f"[zip] entries: {len(z_files)} files + {len(z_dirs)} dirs = tree "
          f"({tree_files}+{tree_dirs}); size {size} bytes "
          f"({size/1024/1024:.1f} MB); {time.time()-t0:.0f}s")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "prune" and len(sys.argv) == 3:
        return cmd_prune(sys.argv[2])
    if cmd == "importsmoke":
        return cmd_importsmoke()
    if cmd == "zip" and len(sys.argv) == 4:
        return cmd_zip(sys.argv[2], sys.argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
