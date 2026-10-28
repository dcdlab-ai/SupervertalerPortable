"""
BATCH P1-C probe 4 (negative): isolated profile stays empty, all new state
lands inside the build root — WITHOUT the SUPERVERTALER_DATA_ROOT seam.

The code under test is a worktree copy at <stage>/negroot/SupervertalerPortable
(passed as argv[1]); its build root is <stage>/negroot — inside the stage, so
nothing can leak into E:\\Dev. USERPROFILE/HOME/APPDATA/LOCALAPPDATA/TEMP/TMP
point at empty isolated dirs (argv[2]) as the negative control.

Exercises the full P1-C surface in one process:
  * file_dialog_helper write cycle  -> <negroot>\\last_directory.json,
  * KeyboardShortcutsWidget (CWD = a stage dir, NOT the build root)
    -> shortcuts under <negroot>\\Supervertaler\\workbench\\settings\\,
  * OkapiSidecar construction (lazy target resolves inside the build root).

Verifies the profile snapshot diff is EMPTY afterwards.

Prints P1C-NEG-OK / P1C-NEG-FAIL. Exit code 0/1.
"""
import os
import sys
from pathlib import Path

WORKTREE = Path(sys.argv[1]).resolve()
ISO = Path(sys.argv[2]).resolve()          # holds the isolated profile dirs

PROFILE = ISO / "profile"
CWD = ISO / "cwd-neg"
CWD.mkdir(parents=True, exist_ok=True)

# NO SUPERVERTALER_DATA_ROOT — the build root must win on its own.
os.environ.pop("SUPERVERTALER_DATA_ROOT", None)
os.environ["USERPROFILE"] = str(PROFILE)
os.environ["HOME"] = str(PROFILE)
os.environ["APPDATA"] = str(PROFILE / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(PROFILE / "AppData" / "Local")
os.environ["TEMP"] = str(ISO / "tmp")
os.environ["TMP"] = str(ISO / "tmp")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

os.chdir(CWD)
sys.path.insert(0, str(WORKTREE))

from PyQt6.QtWidgets import QApplication  # noqa: E402
from modules import file_dialog_helper as fdh              # noqa: E402
from modules.config_manager import ConfigManager            # noqa: E402
from modules.keyboard_shortcuts_widget import (             # noqa: E402
    KeyboardShortcutsWidget)
from modules.okapi_sidecar import OkapiSidecar              # noqa: E402
from modules.portable_paths import build_root, data_root    # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    tag = "OK " if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def snapshot(root: Path):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def main():
    app = QApplication.instance() or QApplication([])

    build = build_root()
    check("build_root == negroot (worktree layout)",
          build == WORKTREE.parent, str(build))
    check("data_root == <negroot>/Supervertaler",
          data_root() == build / "Supervertaler", str(data_root()))

    profile_before = snapshot(ISO)

    # --- fdh cycle: state file must land in the build root ---
    picked_dir = WORKTREE / "docs"
    fake_file = str(picked_dir / "demo.txt")
    fdh.QFileDialog.getOpenFileName = staticmethod(
        lambda *a, **k: (fake_file, "Any Files (*)"))
    fdh.get_open_file_name()
    state_file = build / "last_directory.json"
    check("last_directory.json in the build root", state_file.exists(),
          str(state_file))
    check("fresh ConfigManager reads it",
          ConfigManager().get_last_directory()
          == os.path.normpath(str(picked_dir)))

    # --- shortcuts widget with CWD != build root ---
    cwd_before = snapshot(CWD)
    w = KeyboardShortcutsWidget(parent=None)
    sh_file = data_root() / "workbench" / "settings" / "shortcuts.json"
    check("widget manager file inside build root (absolute)",
          w.manager.settings_file == sh_file, str(w.manager.settings_file))
    w.manager.set_shortcut("file_save", "Ctrl+Alt+S")
    w.manager.save_shortcuts()
    check("shortcuts.json under <build_root>/Supervertaler", sh_file.exists())
    w2 = KeyboardShortcutsWidget(parent=None)
    check("custom shortcut survives fresh construction",
          w2.manager.get_shortcut("file_save") == "Ctrl+Alt+S")
    w2.manager.reset_shortcut("file_save")
    w2.manager.save_shortcuts()
    cwd_after = snapshot(CWD)
    check("no user_data tree under CWD", cwd_before == cwd_after,
          "; ".join(set(cwd_after) - set(cwd_before)))

    # --- okapi: lazy target inside the build root ---
    oc = OkapiSidecar()
    check("okapi lazy target == <build_root>/Supervertaler/okapi-sidecar",
          oc._user_data_sidecar_dir()
          == build / "Supervertaler" / "okapi-sidecar",
          str(oc._user_data_sidecar_dir()))

    # --- negative control: the isolated profile gained NOTHING ---
    profile_after = snapshot(ISO)
    gained = [p for p in profile_after if p not in profile_before]
    check("isolated profile diff is EMPTY", not gained,
          "; ".join(gained[:10]))
    check("no ~/Supervertaler appeared",
          not (PROFILE / "Supervertaler").exists())

    print()
    if FAILURES:
        print("P1C-NEG-FAIL:", len(FAILURES), "failed —", "; ".join(FAILURES))
        return 1
    print("P1C-NEG-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
