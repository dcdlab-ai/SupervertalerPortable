# -*- coding: utf-8 -*-
r"""BATCH P1.6c probe: AA_DontUseNativeDialogs — file dialogs open as Qt dialogs.

Runs offscreen with the P1-B seam and an isolated profile. Verifies:
  * QApplication.setAttribute(AA_DontUseNativeDialogs, True) before creating
    the app makes QApplication.testAttribute True (the main() behaviour);
  * a real QFileDialog (open / save / directory modes) opens as a WIDGET-BASED
    Qt dialog: visible, non-native (Qt widget dialogs contain a QListView —
    native dialogs are childless native windows), renders to a non-empty image;
  * file_dialog_helper passes the explicit start directory (last_directory)
    into QFileDialog in all four wrappers (the AA flag does not remove the
    explicit start dir);
  * the isolated profile stays clean (no AppData writes).

Prints P16-FD-OK / P16-FD-FAIL; exit 0/1.
Run: python batch-p16_probe_dialogs.py <iso-dir>
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ISO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(
    r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p16\iso-fd")
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

sys.path.insert(0, str(REPO))

from PyQt6.QtCore import Qt                    # noqa: E402
from PyQt6.QtWidgets import (QAbstractItemView, QFileDialog,  # noqa: E402
                             QApplication)

FAILURES = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def main():
    # Replicate main()'s P1.6c placement: attribute set BEFORE the app exists.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
    app = QApplication([])
    check("AA_DontUseNativeDialogs active on the application",
          app.testAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs))

    # --- explicit start directory: fdh passes last_directory in all 4 wrappers
    from modules.config_manager import get_config_manager
    start = ISO / "projects"
    start.mkdir(parents=True, exist_ok=True)
    cfg = get_config_manager()
    cfg.set_last_directory(str(start))

    captured = []

    def fake_get(parent=None, caption="", directory="", *a, **k):
        captured.append(directory)
        return "", ""

    def fake_get_multi(parent=None, caption="", directory="", *a, **k):
        captured.append(directory)
        return [], ""

    def fake_get_dir(parent=None, caption="", directory="", *a, **k):
        captured.append(directory)
        return ""

    from modules import file_dialog_helper as fdh
    fdh.QFileDialog.getOpenFileName = staticmethod(fake_get)
    fdh.QFileDialog.getOpenFileNames = staticmethod(fake_get_multi)
    fdh.QFileDialog.getSaveFileName = staticmethod(fake_get)
    fdh.QFileDialog.getExistingDirectory = staticmethod(fake_get_dir)
    fdh.get_open_file_name()
    fdh.get_open_file_names()
    fdh.get_save_file_name()
    fdh.get_existing_directory()
    want = os.path.normpath(str(start))
    check("fdh passes last_directory as start dir in all 4 wrappers",
          len(captured) == 4 and all(os.path.normpath(d) == want for d in captured),
          repr(captured))

    # --- real QFileDialog opens as a widget-based Qt dialog (offscreen-safe) ---
    def widget_dialog_checks(dlg, label):
        dlg.show()
        for _ in range(6):
            app.processEvents()
        check(f"{label}: dialog visible", dlg.isVisible())
        # Qt widget dialogs embed child views (file list etc.); native dialogs
        # are childless native windows. With AA_DontUseNativeDialogs set, a
        # plain QFileDialog must be the widget variant.
        check(f"{label}: widget-based (contains item views)",
              bool(dlg.findChildren(QAbstractItemView)),
              f"{len(dlg.findChildren(QAbstractItemView))} views")
        pix = dlg.grab()
        check(f"{label}: renders a non-empty image",
              not pix.isNull() and pix.width() > 100 and pix.height() > 100,
              f"{pix.width()}x{pix.height()}")
        check(f"{label}: starts in the requested directory",
              os.path.normpath(dlg.directory().path()) == want,
              dlg.directory().path())
        dlg.close()
        for _ in range(4):
            app.processEvents()

    d_open = QFileDialog(None, "Open Project", str(start), "Projects (*.svproj)")
    widget_dialog_checks(d_open, "open dialog")
    d_save = QFileDialog(None, "Save As", str(start), "Text (*.txt)")
    d_save.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    widget_dialog_checks(d_save, "save dialog")
    d_dir = QFileDialog(None, "Choose Folder", str(start))
    d_dir.setFileMode(QFileDialog.FileMode.Directory)
    widget_dialog_checks(d_dir, "directory dialog")

    # --- negative control: profile untouched ---
    # (the ISO path itself contains "SupervertalerPortable", so match names,
    # not substrings; Microsoft\Windows\Caches is the OS's own folder-cache)
    noise = ([p for p in (PROFILE / "AppData").rglob("*")
              if p.name == "Supervertaler"
              or (p.name == "config.json" and p.parent.name == "Supervertaler")]
             if (PROFILE / "AppData").exists() else [])
    check("no Supervertaler entry in the isolated AppData", not noise, str(noise))

    print("P16-FD-OK" if not FAILURES else f"P16-FD-FAIL {FAILURES}")
    sys.exit(0 if not FAILURES else 1)


main()
