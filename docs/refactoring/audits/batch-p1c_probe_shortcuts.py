"""
BATCH P1-C probe 2: keyboard shortcuts widget with CWD != build root (P1.4b).

Constructs KeyboardShortcutsWidget offscreen with the process CWD set to the
stage directory and the data root pointed at an isolated dir via the
SUPERVERTALER_DATA_ROOT seam. Verifies:
  * the fallback ShortcutManager (no main window) resolves the SAME absolute
    file the monolith passes: <data_root>/workbench/settings/shortcuts.json;
  * constructing the widget creates NO user_data/ tree under CWD
    (snapshot diff of CWD is empty);
  * a changed shortcut is persisted under <data_root> and survives a fresh
    widget construction ("restart").

Prints P1C-SH-OK / P1C-SH-FAIL. Exit code 0/1.
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# iso dir: argv[1] (the runner passes the stage dir) or the documented stage
ISO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else \
    Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1c\iso-sh")
CWD = ISO / "cwd"
CWD.mkdir(parents=True, exist_ok=True)

os.environ["SUPERVERTALER_DATA_ROOT"] = str(ISO)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# CWD must differ from the repo: chdir into the stage dir.
os.chdir(CWD)
sys.path.insert(0, str(REPO))

from PyQt6.QtWidgets import QApplication  # noqa: E402
from modules.shortcut_manager import ShortcutManager        # noqa: E402
from modules.keyboard_shortcuts_widget import (             # noqa: E402
    KeyboardShortcutsWidget)
from modules.portable_paths import data_root                # noqa: E402

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

    expected_file = data_root() / "workbench" / "settings" / "shortcuts.json"
    check("expected shortcuts file is under data_root (seam)",
          expected_file == ISO / "Supervertaler" / "workbench" / "settings"
          / "shortcuts.json", str(expected_file))

    # The same expression the monolith uses (Supervertaler.py:6249):
    monolith_expr = data_root() / "workbench" / "settings" / "shortcuts.json"

    cwd_before = snapshot(CWD)

    # Standalone construction (parent=None) — exercises the fallback branch.
    w1 = KeyboardShortcutsWidget(parent=None)
    check("fallback manager file == monolith path (absolute)",
          w1.manager.settings_file == monolith_expr
          and Path(w1.manager.settings_file).is_absolute(),
          str(w1.manager.settings_file))

    cwd_after = snapshot(CWD)
    check("no user_data tree appeared under CWD",
          cwd_before == cwd_after,
          "new: " + "; ".join(set(cwd_after) - set(cwd_before))
          if cwd_before != cwd_after else "")

    # Change one shortcut, persist.
    sid = "file_open"
    w1.manager.set_shortcut(sid, "Ctrl+Shift+O")
    w1.manager.save_shortcuts()
    check("shortcuts.json written under <data_root>",
          expected_file.exists(), str(expected_file))

    # "Restart": a fresh widget loads the custom value back.
    w2 = KeyboardShortcutsWidget(parent=None)
    got = w2.manager.get_shortcut(sid)
    check("custom shortcut survives fresh construction",
          got == "Ctrl+Shift+O", repr(got))
    all_s = w2.manager.get_all_shortcuts()
    check("widget table reports the shortcut as custom",
          all_s[sid]["is_custom"] is True)

    # Cleanup for re-runs: remove the persisted custom value.
    w2.manager.reset_shortcut(sid)
    w2.manager.save_shortcuts()

    print()
    if FAILURES:
        print("P1C-SH-FAIL:", len(FAILURES), "failed —", "; ".join(FAILURES))
        return 1
    print("P1C-SH-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
