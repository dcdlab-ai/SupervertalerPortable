# -*- coding: utf-8 -*-
"""Batch P1-B unit probe for modules/portable_paths.py (STEP 1 acceptance).

Covers:
  1. default branch      -- no env, no dev flag: data_root = <build_root>/Supervertaler,
                            build_root = parents[2] of the module file;
  2. dev-flag branch     -- .supervertaler.local next to the code:
                            data_root = <repo>/user_data_private (env absent);
  3. env branch          -- SUPERVERTALER_DATA_ROOT (absolute) wins over the
                            dev flag: data_root = <env>/Supervertaler;
  4. relative env        -- ValueError with a clear message, for both
                            build_root() and data_root();
  5. purity              -- a full snapshot of the fake tree before/after all
                            calls is byte-identical: the functions never
                            create or write anything;
  6. real module         -- build_root() of the repo copy resolves to the
                            repo's parent; data_root() matches the repo's
                            actual dev-flag state.

Run: python batch-p1b_unit_portable_paths.py <stage-dir>
Prints UNIT-OK on success; exits non-zero otherwise.
"""
import hashlib
import importlib.util
import os
import pathlib
import shutil
import sys

stage = pathlib.Path(sys.argv[1]).resolve()
stage.mkdir(parents=True, exist_ok=True)
AUD = pathlib.Path(__file__).resolve().parent
SRC = AUD.parent.parent.parent / "modules" / "portable_paths.py"
REAL_REPO = SRC.resolve().parents[1]
REAL_ROOT = REAL_REPO.parent

failures = []


def check(name, cond, detail=""):
    status = "ok" if cond else "FAIL"
    print(f"[unit] {name}: {status} {detail}", flush=True)
    if not cond:
        failures.append(name)


def load_copy(build: pathlib.Path):
    """Copy the module into a fake <build>/modules/ tree and import it."""
    mods = build / "modules"
    mods.mkdir(parents=True, exist_ok=True)
    dst = mods / "portable_paths.py"
    shutil.copyfile(SRC, dst)
    spec = importlib.util.spec_from_file_location("pp_fake", dst)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tree_state(root: pathlib.Path):
    state = {}
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        state[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "DIR"
    return state


env_key = "SUPERVERTALER_DATA_ROOT"
old_env = os.environ.pop(env_key, None)
try:
    # --- fake tree, default branch ---
    # layout mirrors the real one: <root>/<code_dir>/modules/portable_paths.py
    base = stage / "faketree"
    shutil.rmtree(base, ignore_errors=True)
    root = base / "root"
    build = root / "SupervertalerPortable"  # code dir, like the repo
    pp = load_copy(build)
    check("default build_root", pp.build_root() == root, str(pp.build_root()))
    check("default data_root", pp.data_root() == root / "Supervertaler", str(pp.data_root()))
    check("state_root == build_root", pp.state_root() == root)

    # --- env branch (absolute, wins over dev flag) ---
    envdir = base / "elsewhere"
    envdir.mkdir()
    (build / ".supervertaler.local").write_text("", encoding="utf-8")
    os.environ[env_key] = str(envdir)
    check("env build_root", pp.build_root() == envdir, str(pp.build_root()))
    check("env data_root", pp.data_root() == envdir / "Supervertaler", str(pp.data_root()))

    # --- dev-flag branch (env cleared) ---
    del os.environ[env_key]
    check("dev-flag data_root",
          pp.data_root() == build / "user_data_private", str(pp.data_root()))
    check("dev-flag build_root unchanged", pp.build_root() == root)

    # --- relative env -> error ---
    os.environ[env_key] = "relative/path"
    for fn in ("build_root", "data_root"):
        try:
            getattr(pp, fn)()
            check(f"relative env {fn} raises", False, "no exception")
        except ValueError as e:
            check(f"relative env {fn} raises", "ABSOLUTE" in str(e), str(e)[:80])

    # --- purity: snapshot before/after all the calls above ---
    os.environ.pop(env_key, None)
    snap = tree_state(base)
    for _ in range(3):
        pp.build_root(); pp.data_root(); pp.state_root()
    check("no disk writes", tree_state(base) == snap,
          "tree changed during calls" if tree_state(base) != snap else "")

    # --- empty/whitespace env falls through to the flag/build-root logic ---
    os.environ[env_key] = "   "
    check("blank env ignored", pp.data_root() == build / "user_data_private")
    os.environ.pop(env_key, None)

    # --- real module ---
    spec = importlib.util.spec_from_file_location("pp_real", SRC)
    real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real)
    check("real build_root", real.build_root() == REAL_ROOT, str(real.build_root()))
    expect = (REAL_REPO / "user_data_private" if (REAL_REPO / ".supervertaler.local").exists()
              else REAL_ROOT / "Supervertaler")
    check("real data_root matches flag state", real.data_root() == expect, str(real.data_root()))
finally:
    if old_env is not None:
        os.environ[env_key] = old_env
    else:
        os.environ.pop(env_key, None)

if failures:
    print(f"UNIT-FAILED: {failures}", flush=True)
    sys.exit(1)
print("UNIT-OK", flush=True)
