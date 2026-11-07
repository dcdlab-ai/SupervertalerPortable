# -*- coding: utf-8 -*-
r"""BATCH P2.4 helper for make_portable_zip.bat (runs on the bundled dev
runtime as the ORCHESTRATOR only - stdlib just for unzip/zip/subprocess).
The dev runtime E:\Dev\python-embed is never a CONTENT source any more:
the shipped runtime is built from the official embeddable zip + requirements.lock.

Four subcommands:

  runtime <stage> <embedzip> <getpip> <wheelhouse> <lockfile>
      Build <stage>\python-embed from scratch:
        1. unpack the official embeddable zip (CPython 3.13.15);
        2. write python313._pth (same content as RUNTIME_REBUILD.md);
        3. ensure the wheelhouse has a wheel for every lock pin + pip;
           missing wheels -> `pip download -r <lockfile> -d <wheelhouse>`
           (run by the orchestrating interpreter, read-only w.r.t. runtimes);
           no network and cache still incomplete -> clear error, stage KEPT;
        4. bootstrap pip offline: python.exe get-pip.py --no-index
           --find-links <wheelhouse>;
        5. install exactly the lock: python.exe -m pip install --no-index
           --find-links <wheelhouse> -r <lockfile>;
        6. delete get-pip.py from the stage (pip itself STAYS - coordinator
           decision);
        7. verify dist-info set == lock pins + pip (FAIL on any mismatch);
        8. forbidden check: the old prune list (pygments, pytest stack,
           pyflakes, chardet, get-pip.py + dist-infos) must NOT be present
           (FAIL if found) - P2.4 replaces pruning with a gate.
      Stage is kept on failure for inspection.

  importsmoke
      Run by the STAGED python-embed AFTER the _pth patch: import the product
      monolith and the key third-party modules; exit 1 on any failure.

  zip <stage-root> <zip-file>
      Pack the stage root into a REAL zip (deflate), then verify: testzip()
      clean, entry count == file count of the tree, no absolute/drive/..
      paths, forward slashes only, and ZERO __pycache__ / .pyc / .pyo
      entries. Exit 1 on any failure.

Usage from the bat (paths are bat variables):
  "%RUNTIME%\python.exe" "%HELPER%" runtime "%STAGE%" "%EMBED_ZIP%" "%GETPIP%" "%WHEELHOUSE%" "%REPO%\requirements.lock"
  pushd "%STAGE%"
  "python-embed\python.exe" "%HELPER%" importsmoke
  "python-embed\python.exe" "%HELPER%" zip "%STAGE%" "%ZIPFILE%"
"""
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

# ---------------------------------------------------------------- gates
# Packages that must NEVER appear in the built runtime (old prune list,
# P2.0 verdict item 4 - now a presence gate, not a cleanup).
FORBIDDEN_DIRS = [
    "pygments",   # pytest dependency, never imported by the product
    "_pytest",    # pytest stack
    "pytest",
    "iniconfig",
    "pluggy",
    "colorama",
    "pyflakes",   # one-time deviation 2026-10-23 (AGENTS), product never imports
    "chardet",    # requests uses charset_normalizer
]
FORBIDDEN_FILES = [
    "get-pip.py",  # pip bootstrap; deleted by `runtime` after install
]
FORBIDDEN_SCRIPTS = [
    "pytest.exe", "py.test.exe",    # pytest
    "chardetect.exe",               # chardet
    "pyflakes.exe",                 # pyflakes
    "pygmentize.exe",               # pygments
]

PTH_CONTENT = "python313.zip\n.\n..\\SupervertalerPortable\nLib\\site-packages\nimport site\n"

_wheels_norm = lambda s: re.sub(r"[-_.]+", "_", s.lower())


def _run(cmd, **kw):
    print(f"[runtime] $ {' '.join(cmd)}", flush=True)
    env = dict(os.environ)
    # pip compiles the packages it installs -> __pycache__/.pyc would end up
    # in the zip; the distributive must ship zero bytecode.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(cmd, env=env, **kw)


def _strip_bytecode(root: str) -> int:
    """Remove every __pycache__ dir and .pyc/.pyo file; returns removed count."""
    removed = 0
    for r, dirs, files in os.walk(root, topdown=True):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(r, d))
                dirs.remove(d)
                removed += 1
        for f in files:
            if f.lower().endswith((".pyc", ".pyo")):
                os.remove(os.path.join(r, f))
                removed += 1
    return removed


def _lock_pins(lockfile: str):
    pins = []
    with open(lockfile, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                name, _, ver = line.partition("==")
                pins.append((name.strip(), ver.strip()))
    return pins


def _wheelhouse_missing(wheelhouse: str, pins):
    """Lock pins (+ pip) that have no wheel file in the wheelhouse."""
    wheels = {}
    for fn in os.listdir(wheelhouse):
        if fn.endswith(".whl"):
            stem = fn[:-4]
            parts = stem.split("-")
            if len(parts) >= 2:
                wheels.setdefault(_wheels_norm(parts[0]), set()).add(parts[1])
    missing = []
    for name, ver in pins + [("pip", None)]:
        vers = wheels.get(_wheels_norm(name), set())
        if not vers or (ver is not None and ver not in vers):
            missing.append(f"{name}=={ver}" if ver else name)
    return missing


def cmd_runtime(stage: str, embedzip: str, getpip: str, wheelhouse: str,
                lockfile: str) -> int:
    stage = os.path.abspath(stage)
    rt = os.path.join(stage, "python-embed")
    if not os.path.isfile(embedzip):
        print(f"[runtime] FAIL: embeddable zip not found: {embedzip}")
        return 1
    if not os.path.isfile(getpip):
        print(f"[runtime] FAIL: get-pip.py not found: {getpip}")
        return 1
    if not os.path.isfile(lockfile):
        print(f"[runtime] FAIL: lock file not found: {lockfile}")
        return 1
    pins = _lock_pins(lockfile)
    print(f"[runtime] lock pins: {len(pins)}")

    # --- 0. wheelhouse completeness (download only if needed) -----------
    if not os.path.isdir(wheelhouse):
        os.makedirs(wheelhouse, exist_ok=True)
    missing = _wheelhouse_missing(wheelhouse, pins)
    if missing:
        print(f"[runtime] wheelhouse incomplete, {len(missing)} missing "
              f"(first: {missing[:3]}...)" if len(missing) > 3 else
              f"[runtime] wheelhouse incomplete: {missing}")
        rc = _run([sys.executable, "-m", "pip", "download", "-r", lockfile,
                   "-d", wheelhouse]).returncode
        rc2 = _run([sys.executable, "-m", "pip", "download", "pip",
                    "-d", wheelhouse]).returncode
        still = _wheelhouse_missing(wheelhouse, pins)
        if still:
            print(f"[runtime] FAIL: wheelhouse still incomplete after "
                  f"download (rc={rc}, pip-rc={rc2}): {still}\n"
                  f"  Instructions: provide network access OR fill the "
                  f"wheelhouse manually:\n"
                  f"    <python> -m pip download -r {lockfile} -d {wheelhouse}\n"
                  f"    <python> -m pip download pip -d {wheelhouse}\n"
                  f"  Stage kept for inspection: {stage}")
            return 1
    else:
        print(f"[runtime] wheelhouse complete (all {len(pins)} pins + pip)")

    # --- 1. unpack embeddable zip ---------------------------------------
    if os.path.isdir(rt):
        print(f"[runtime] FAIL: {rt} already exists (fresh stage expected); "
              f"stage kept for inspection")
        return 1
    t0 = time.time()
    tmp = rt + "_unpack"
    with zipfile.ZipFile(embedzip) as zf:
        for n in zf.namelist():
            if "\\" in n or n.startswith("/") or ":" in n or ".." in n.split("/"):
                print(f"[runtime] FAIL: unsafe entry in embed zip: {n!r}")
                return 1
        zf.extractall(tmp)
    # Some embeddable zips carry a single top-level folder - lift its
    # contents up so that python.exe lands directly in rt.
    entries = os.listdir(tmp)
    inner = tmp
    if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])):
        inner = os.path.join(tmp, entries[0])
    os.rename(inner, rt)
    if inner != tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    if not os.path.isfile(os.path.join(rt, "python.exe")):
        print(f"[runtime] FAIL: unpacked zip has no python.exe")
        return 1
    print(f"[runtime] unpacked {embedzip} -> {rt} ({time.time()-t0:.0f}s)")

    # --- 2. python313._pth ------------------------------------------------
    with open(os.path.join(rt, "python313._pth"), "w",
              encoding="ascii", newline="\n") as f:
        f.write(PTH_CONTENT)
    print(f"[runtime] python313._pth written")

    stage_py = os.path.join(rt, "python.exe")

    # --- 3. bootstrap pip (offline from the wheelhouse) ------------------
    if _run([stage_py, getpip, "--no-index", "--find-links", wheelhouse,
             "--no-warn-script-location"]).returncode != 0:
        print("[runtime] FAIL: pip bootstrap failed")
        return 1

    # --- 4. install exactly the lock --------------------------------------
    if _run([stage_py, "-m", "pip", "install", "--no-index",
             "--find-links", wheelhouse, "-r", lockfile]).returncode != 0:
        print("[runtime] FAIL: pip install from lock failed")
        return 1

    # --- 5. get-pip.py out of the stage (pip itself stays) ----------------
    gp = os.path.join(rt, "get-pip.py")
    if os.path.isfile(gp):
        os.remove(gp)
        print("[runtime] get-pip.py removed from stage")

    # --- 6. dist-info set == lock pins + pip ------------------------------
    sp = os.path.join(rt, "Lib", "site-packages")
    norm = lambda s: re.sub(r"[-_.]+", "-", s.lower())
    want = {norm(n): v for n, v in pins}
    got = {}
    for entry in os.listdir(sp):
        if not entry.endswith(".dist-info"):
            continue
        base = entry[:-len(".dist-info")]
        # name part = everything before the LAST dash that precedes version:
        # dir name is <name>-<version>; version never contains a dash here
        # (all lock versions are plain x.y.z), but name may (PyQt6-Qt6).
        # Take METADATA Name/Version instead - unambiguous.
        with open(os.path.join(sp, entry, "METADATA"),
                  encoding="utf-8", errors="replace") as f:
            nm = vv = None
            for line in f:
                low = line.lower()
                if low.startswith("name:"):
                    nm = line.split(":", 1)[1].strip()
                elif low.startswith("version:"):
                    vv = line.split(":", 1)[1].strip()
                if nm and vv:
                    break
        got[norm(nm)] = vv
    extra_pip = [k for k in got if k == "pip"]
    unexpected = sorted(k for k in got if k not in want and k != "pip")
    wrong = sorted(f"{k}: lock {want[k]} != dist {got[k]}"
                   for k in want if k in got and want[k] != got[k])
    absent = sorted(k for k in want if k not in got)
    ok = (not unexpected and not wrong and not absent and len(extra_pip) == 1)
    print(f"[runtime] dist-info: {len(got)} entries "
          f"(lock {len(want)} + pip {len(extra_pip)})")
    for label, lst in (("UNEXPECTED", unexpected), ("VERSION-MISMATCH", wrong),
                       ("MISSING", absent)):
        if lst:
            print(f"[runtime] FAIL {label}: {lst}")
    if not ok:
        return 1

    # --- 7. bytecode strip + forbidden check ------------------------------
    n = _strip_bytecode(rt)
    leftover = 0
    for r, dirs, files in os.walk(rt):
        leftover += sum(1 for d in dirs if d == "__pycache__")
        leftover += sum(1 for f in files if f.lower().endswith((".pyc", ".pyo")))
    if leftover:
        print(f"[runtime] FAIL: {leftover} __pycache__/.pyc/.pyo remain after strip")
        return 1
    print(f"[runtime] bytecode strip: {n} items removed, 0 remain")
    hits = []
    for name in FORBIDDEN_DIRS:
        for root_dir in (sp, rt):
            p = os.path.join(root_dir, name)
            if os.path.isdir(p):
                hits.append(os.path.relpath(p, rt))
            for entry in os.listdir(root_dir):
                if entry.lower().startswith(name.lower() + "-") \
                        and entry.lower().endswith(".dist-info"):
                    hits.append(os.path.relpath(os.path.join(root_dir, entry), rt))
    for name in FORBIDDEN_FILES:
        if os.path.isfile(os.path.join(rt, name)):
            hits.append(name)
    scripts = os.path.join(rt, "Scripts")
    if os.path.isdir(scripts):
        for name in FORBIDDEN_SCRIPTS:
            if os.path.isfile(os.path.join(scripts, name)):
                hits.append(os.path.join("Scripts", name))
    if hits:
        print(f"[runtime] FAIL: forbidden items present in the runtime: {hits}")
        return 1
    print("[runtime] forbidden check CLEAN")

    print(f"[runtime] OK ({time.time()-t0:.0f}s total)")
    return 0


def cmd_importsmoke() -> int:
    # Run by the STAGED interpreter: sys.path comes from the patched ._pth
    # (..\SupervertalerPortable + Lib\site-packages), not from cwd.
    modules = [
        "PyQt6.QtWidgets", "openai", "docx", "openpyxl", "PIL", "lxml",
        "requests", "spellchecker", "spylls", "pydantic", "Supervertaler",
        # Batch I1: новый пакет писателя InDesign Tagged Text (только stdlib)
        "modules.tagged_text",
        # Batch I2: окно экспорта «роль → имя стиля InDesign» (PyQt6)
        "modules.tagged_text_export_dialog",
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
        pycache = [n for n in names if "__pycache__" in n
                   or n.lower().endswith((".pyc", ".pyo"))]
        if pycache:
            print(f"[zip] FAIL: {len(pycache)} __pycache__/.pyc/.pyo entries in zip, "
                  f"first: {pycache[:5]}")
            return 1
    print(f"[zip] OK: {zip_path}")
    print(f"[zip] entries: {len(z_files)} files + {len(z_dirs)} dirs = tree "
          f"({tree_files}+{tree_dirs}); size {size} bytes "
          f"({size/1024/1024:.1f} MB); __pycache__/.pyc: 0; {time.time()-t0:.0f}s")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "runtime" and len(sys.argv) == 7:
        return cmd_runtime(*sys.argv[2:7])
    if cmd == "importsmoke":
        return cmd_importsmoke()
    if cmd == "zip" and len(sys.argv) == 4:
        return cmd_zip(sys.argv[2], sys.argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
