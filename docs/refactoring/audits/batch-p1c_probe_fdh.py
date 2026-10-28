"""
BATCH P1-C probe 1: last_directory state file in the build root (P1.4a).

Runs the file_dialog_helper functions with QFileDialog monkeypatched,
SUPERVERTALER_DATA_ROOT (the test seam) pointed at an isolated dir, and the
user profile env vars isolated as the negative control. Verifies:
  * the state file is <state_root()>/last_directory.json (i.e. <iso>/...),
  * the saved value round-trips through a FRESH ConfigManager instance
    ("service restart"),
  * no .supervertaler_config.json appears in the (isolated) profile.

Prints P1C-FDH-OK on success, P1C-FDH-FAIL otherwise. Exit code 0/1.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]       # E:\Dev\SupervertalerPortable
# iso dir: argv[1] (the runner passes the stage dir) or the documented stage
ISO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else \
    Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1c\iso-fdh")
PROFILE = ISO / "profile"                        # isolated USERPROFILE etc.
DATA = ISO / "Supervertaler"                     # data root via the seam

# --- test seam: data root -> ISO; profile dirs isolated (negative control) ---
os.environ["SUPERVERTALER_DATA_ROOT"] = str(ISO)
os.environ["USERPROFILE"] = str(PROFILE)
os.environ["HOME"] = str(PROFILE)
os.environ["APPDATA"] = str(PROFILE / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(PROFILE / "AppData" / "Local")

sys.path.insert(0, str(REPO))

from PyQt6.QtWidgets import QApplication  # noqa: E402
from modules import file_dialog_helper as fdh            # noqa: E402
from modules.config_manager import ConfigManager          # noqa: E402
from modules.portable_paths import state_root, data_root  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    tag = "OK " if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def main():
    app = QApplication.instance() or QApplication([])

    # Snapshot the isolated profile (must stay empty at the end).
    profile_before = sorted(str(p.relative_to(ISO)) for p in ISO.rglob("*")) \
        if ISO.exists() else []

    # --- open-file dialog: state must be written next to the state root ---
    proj = ISO / "projects" / "demo"
    proj.mkdir(parents=True, exist_ok=True)
    picked = proj / "file.txt"
    picked.write_text("x", encoding="utf-8")

    state_file = state_root() / "last_directory.json"
    check("state_root == iso (seam works)", state_root() == ISO, str(state_root()))
    check("data_root == iso/Supervertaler", data_root() == DATA, str(data_root()))
    check("no state file before the dialog", not state_file.exists())

    fdh.QFileDialog.getOpenFileName = staticmethod(
        lambda *a, **k: (str(picked), "Any Files (*)"))
    out, filt = fdh.get_open_file_name()
    check("dialog returned the picked file", out == str(picked))
    check("state file created at <iso>/last_directory.json",
          state_file.exists(), str(state_file))
    data = json.loads(state_file.read_text(encoding="utf-8")) \
        if state_file.exists() else {}
    check('format {"last_directory": "<dir>"}',
          data.get("last_directory") == os.path.normpath(str(proj)),
          repr(data))

    # --- "service restart": a fresh ConfigManager reads the same value ---
    fresh = ConfigManager()
    check("fresh ConfigManager reads persisted value",
          fresh.get_last_directory() == os.path.normpath(str(proj)))

    # --- save dialog: last_directory updated from the file path ---
    target = ISO / "exports"
    target.mkdir(parents=True, exist_ok=True)
    save_target = target / "out.docx"
    fdh.QFileDialog.getSaveFileName = staticmethod(
        lambda *a, **k: (str(save_target), "DOCX (*.docx)"))
    fdh.get_save_file_name()
    fresh2 = ConfigManager()
    check("save dialog updates last_directory",
          fresh2.get_last_directory() == os.path.normpath(str(target)))

    # --- directory dialog: set_last_directory path ---
    pick_dir = ISO / "projects2"
    pick_dir.mkdir(parents=True, exist_ok=True)
    fdh.QFileDialog.getExistingDirectory = staticmethod(
        lambda *a, **k: str(pick_dir))
    fdh.get_existing_directory()
    fresh3 = ConfigManager()
    check("directory dialog sets last_directory",
          fresh3.get_last_directory() == os.path.normpath(str(pick_dir)))

    # --- multi-open dialog: first file's dir wins ---
    m1 = ISO / "multi" / "a.txt"
    m2 = ISO / "multi" / "b.txt"
    m1.parent.mkdir(parents=True, exist_ok=True)
    m1.write_text("1", encoding="utf-8")
    m2.write_text("2", encoding="utf-8")
    fdh.QFileDialog.getOpenFileNames = staticmethod(
        lambda *a, **k: ([str(m1), str(m2)], "Any Files (*)"))
    fdh.get_open_file_names()
    fresh4 = ConfigManager()
    check("multi-open dialog uses first file's dir",
          fresh4.get_last_directory() == os.path.normpath(str(m1.parent)))

    # --- negative control: nothing appeared in the isolated profile ---
    profile_after = sorted(str(p.relative_to(ISO)) for p in ISO.rglob("*"))
    new_in_profile = [p for p in profile_after
                      if p not in profile_before
                      and p.replace("/", "\\").startswith("profile\\")]
    check("isolated profile stayed empty (no .supervertaler_config.json)",
          not new_in_profile, "; ".join(new_in_profile))

    print()
    if FAILURES:
        print("P1C-FDH-FAIL:", len(FAILURES), "failed —", "; ".join(FAILURES))
        return 1
    print("P1C-FDH-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
