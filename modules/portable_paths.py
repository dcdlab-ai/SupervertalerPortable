"""
portable_paths.py – the single source of data-path resolution for Supervertaler.

P1-B: the root of the build is the only source of paths. The old system
(a pointer file in %APPDATA%/Supervertaler/config.json choosing an arbitrary
data folder, defaulting to ~/Supervertaler) is gone; the app always keeps its
data next to the build:

    <build_root>/Supervertaler/          <- data_root() default
    <build_root>/                        <- build_root() / state_root()

Layout handled by build_root(): the code lives one level below the build root
(`<build_root>/SupervertalerPortable/modules/portable_paths.py`), so the build
root is parents[2] of this file. The same layout works for the dev repo
(E:/Dev/SupervertalerPortable inside E:/Dev) and for the frozen test build
(D:/SupervertalerPortable_test/SupervertalerPortable inside
D:/SupervertalerPortable_test).

Resolution priority for data_root() (fixed, do not reorder):
    1. env SUPERVERTALER_DATA_ROOT          -> <env>/Supervertaler
       (test seam; must be an ABSOLUTE path, relative values are an error)
    2. dev flag .supervertaler.local next to the code
                                            -> <repo>/user_data_private
       (same convention as ConfigManager / the private-features flag; keeps the
       developer's git-ignored data inside the repo)
    3. build root                           -> <build_root>/Supervertaler

These functions are pure path math: they never create directories and never
write anything to disk. stdlib only -- this module is imported by mirrors
(ui_scale, llm_clients, llm_pricing) that must not pull in the monolith or Qt.
"""

import os
import sys
from pathlib import Path

DEV_FLAG = ".supervertaler.local"
ENV_VAR = "SUPERVERTALER_DATA_ROOT"


def build_root() -> Path:
    """Root of the build: the directory one level above the code directory.

    With the code at ``<root>/SupervertalerPortable/modules/portable_paths.py``
    this is ``<root>`` (parents[2] of this file). The environment variable
    SUPERVERTALER_DATA_ROOT overrides it for isolated test runs; a relative
    value is rejected with a clear message instead of silently resolving
    against the process CWD.
    """
    env = os.environ.get(ENV_VAR, "").strip()
    if env:
        p = Path(env)
        if not p.is_absolute():
            raise ValueError(
                f"{ENV_VAR} must be an ABSOLUTE path, got relative: {env!r}"
            )
        return p
    return Path(__file__).resolve().parents[2]


def data_root() -> Path:
    """Catalog of user data (settings, databases, profiles, api keys).

    Priority: env SUPERVERTALER_DATA_ROOT > dev flag .supervertaler.local >
    <build_root>/Supervertaler. Never creates anything on disk.
    """
    env = os.environ.get(ENV_VAR, "").strip()
    if env:
        return build_root() / "Supervertaler"
    repo = Path(__file__).resolve().parents[1]
    if (repo / DEV_FLAG).exists():
        return repo / "user_data_private"
    return build_root() / "Supervertaler"


def state_root() -> Path:
    """Catalog for service state files written directly into the build root
    (P1-C/P1.6: last_directory.json, quicktrans.ini, qsettings/)."""
    return build_root()
