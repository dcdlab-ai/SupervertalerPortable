# -*- coding: utf-8 -*-
r"""BATCH P1.6a probe: QuickTrans popup geometry lives in quicktrans.ini.

Runs the MTQuickPopup popup offscreen with the P1-B seam
(SUPERVERTALER_DATA_ROOT=iso) and an isolated profile (negative control).
Verifies:
  * with no ini: the popup opens with built-in defaults (650x400);
  * closeEvent writes <state_root()>/quicktrans.ini (i.e. <iso>/quicktrans.ini)
    with exactly the keys width/height/x/y and the geometry set before close;
  * a FRESH popup ("app restart") reads the same geometry back;
  * HKCU\Software\Supervertaler (read-only reg query, method M4) is byte-
    identical before and after the run — the popup creates/updates no registry key;
  * the isolated profile stays empty (no AppData writes, no .supervertaler_config).

Prints P16-POPUP-OK / P16-POPUP-FAIL; exit 0/1.
Run: python batch-p16_probe_popup.py <iso-dir>
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]       # E:\Dev\SupervertalerPortable
ISO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(
    r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p16\iso-popup")
PROFILE = ISO / "profile"

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SUPERVERTALER_DATA_ROOT"] = str(ISO)
os.environ["USERPROFILE"] = str(PROFILE)
os.environ["HOME"] = str(PROFILE)
os.environ["APPDATA"] = str(PROFILE / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(PROFILE / "AppData" / "Local")
os.environ["TEMP"] = str(ISO / "tmp")
os.environ["TMP"] = str(ISO / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (PROFILE / d).mkdir(parents=True, exist_ok=True)
(PROFILE / "AppData" / "Roaming").mkdir(parents=True, exist_ok=True)
(PROFILE / "AppData" / "Local").mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO))

from PyQt6.QtWidgets import QApplication                      # noqa: E402
from modules.portable_paths import state_root, data_root      # noqa: E402
from modules.quicktrans import MTQuickPopup                   # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def reg_query(key):
    """Method M4: read-only observation of the user registry (never a write)."""
    r = subprocess.run(["reg", "query", key], capture_output=True, text=True)
    return (r.returncode, (r.stdout + r.stderr).strip())


KEY = "HKCU\\Software\\Supervertaler"


def parse_ini(path: Path):
    """Minimal QSettings-INIT parser: returns {key: value} of the General section."""
    keys = {}
    section = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        m = re.fullmatch(r"\[(.*)\]", line)
        if m:
            section = m.group(1)
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            keys[f"{section}/{k.strip()}"] = v.strip()
    return keys


def main():
    app = QApplication.instance() or QApplication([])

    # The popup auto-fetches translations on open; geometry is the subject of
    # this probe, so no network is needed (and none must happen here).
    MTQuickPopup.start_fetching = lambda self: None

    reg_before = reg_query(KEY)
    profile_before = sorted(str(p.relative_to(ISO)) for p in ISO.rglob("*"))

    check("state_root == iso (seam works)", state_root() == ISO, str(state_root()))
    check("data_root == iso/Supervertaler", data_root() == ISO / "Supervertaler",
          str(data_root()))
    ini = state_root() / "quicktrans.ini"
    check("no quicktrans.ini before the popup", not ini.exists(), str(ini))

    # --- first open: built-in defaults, nothing written on open ---
    p1 = MTQuickPopup(None, "hello world", "en", "nl")
    p1.show()
    for _ in range(5):
        app.processEvents()
    check("defaults applied when no ini (650x400)",
          p1.width() == 650 and p1.height() == 400,
          f"{p1.width()}x{p1.height()}")

    # --- move/resize, close -> geometry lands in the ini ---
    p1.resize(611, 317)
    p1.move(73, 41)
    p1.close()
    for _ in range(5):
        app.processEvents()
    check("quicktrans.ini created at <iso>/quicktrans.ini", ini.exists(), str(ini))
    vals = parse_ini(ini) if ini.exists() else {}
    want = {"General/width": "611", "General/height": "317",
            "General/x": "73", "General/y": "41"}
    check("ini contains exactly the geometry keys", vals == want, repr(vals))

    # --- "app restart": a fresh popup reads the same geometry back ---
    p2 = MTQuickPopup(None, "again", "en", "nl")
    p2.show()
    for _ in range(5):
        app.processEvents()
    check("fresh popup restores width/height",
          p2.width() == 611 and p2.height() == 317,
          f"{p2.width()}x{p2.height()}")
    check("fresh popup restores x/y", (p2.x(), p2.y()) == (73, 41), str(p2.pos()))
    p2.close()
    for _ in range(5):
        app.processEvents()

    # --- registry untouched (read-only observation, method M4) ---
    reg_after = reg_query(KEY)
    check("HKCU\\Software\\Supervertaler unchanged by the run",
          reg_before == reg_after,
          f"before rc={reg_before[0]}, after rc={reg_after[0]}")

    # --- negative control: isolated profile stayed a skeleton ---
    profile_after = sorted(str(p.relative_to(ISO)) for p in ISO.rglob("*"))
    new = [p for p in profile_after
           if p.startswith("profile\\AppData") and "Supervertaler" in p]
    check("no AppData/Supervertaler in the isolated profile", not new, str(new))
    check("no .supervertaler_config.json in the profile",
          not (PROFILE / ".supervertaler_config.json").exists())
    check("no qsettings/ directory (nothing writes QSettings here)",
          not (data_root() / "qsettings").exists())

    print("P16-POPUP-OK" if not FAILURES else f"P16-POPUP-FAIL {FAILURES}")
    sys.exit(0 if not FAILURES else 1)


main()
