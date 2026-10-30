# -*- coding: utf-8 -*-
r"""BATCH P1.6b unit probe: QSettings insurance (setDefaultFormat + setPath).

Replays exactly what main() does: QSettings.setDefaultFormat(IniFormat) and
QSettings.setPath(IniFormat, UserScope, <data_root()>/qsettings) BEFORE any
QApplication exists (PyQt6 6.11 — must work in this order), then:

  * the no-arg QSettings() honours defaultFormat: its write lands in
    <iso>/Supervertaler/qsettings/Supervertaler.ini (the seam's data root),
    NOT in the registry; the qsettings/ directory appears only on the first
    real write (a bare startup with read-only QSettings creates nothing);
  * an explicit IniFormat ctor writes via setPath into the same directory;
  * Qt-design observation (documented, not worked around): the 2-arg
    QSettings(org, app) ctor resolves to NativeFormat — Qt 6.11 hardcodes it,
    defaultFormat is NOT honoured by this ctor. The probe only READS such an
    object (no registry write happens anywhere in this probe);
  * HKCU\Software\Supervertaler (read-only reg query, method M4) byte-identical
    before/after; no ZZOrg2 key created;
  * nothing in the isolated profile (AppData clean).

Also AST-checks the monolith: the three main() calls
(setDefaultFormat, setPath, setAttribute(AA_DontUseNativeDialogs)) exist and
all precede `app = QApplication(sys.argv)`.

Prints P16-QS-OK / P16-QS-FAIL; exit 0/1.
Run: python batch-p16_unit_qsettings.py <iso-dir>
"""
import ast
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ISO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(
    r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p16\iso-qs")
PROFILE = ISO / "profile"

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SUPERVERTALER_DATA_ROOT"] = str(ISO)
os.environ["USERPROFILE"] = str(PROFILE)
os.environ["HOME"] = str(PROFILE)
os.environ["APPDATA"] = str(PROFILE / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(PROFILE / "AppData" / "Local")
os.environ["TEMP"] = str(ISO / "tmp")
os.environ["TMP"] = str(ISO / "tmp")

sys.path.insert(0, str(REPO))

from PyQt6.QtCore import QSettings, PYQT_VERSION_STR   # noqa: E402
from modules.portable_paths import data_root           # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def reg_query(key):
    r = subprocess.run(["reg", "query", key], capture_output=True, text=True)
    return (r.returncode, (r.stdout + r.stderr).strip())


KEY = "HKCU\\Software\\Supervertaler"


def ast_order_check():
    """main() must call setDefaultFormat/setPath/setAttribute BEFORE QApplication."""
    tree = ast.parse((REPO / "Supervertaler.py").read_text(encoding="utf-8"))
    main_fn = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    lines = {"setDefaultFormat": None, "setPath": None, "setAttribute": None,
             "QApplication": None}

    def attr_name(node):
        return node.attr if isinstance(node, ast.Attribute) else None

    for n in ast.walk(main_fn):
        if isinstance(n, ast.Call):
            f = n.func
            fn = attr_name(f)
            if fn == "setDefaultFormat":
                lines["setDefaultFormat"] = n.lineno
            elif fn == "setPath":
                lines["setPath"] = n.lineno
            elif fn == "setAttribute":
                lines["setAttribute"] = n.lineno
            elif (isinstance(f, ast.Name) and f.id == "QApplication") or \
                 (isinstance(f, ast.Attribute) and attr_name(f) == "QApplication"):
                if lines["QApplication"] is None:
                    lines["QApplication"] = n.lineno
    return lines


def main():
    reg_before = reg_query(KEY)
    qs_dir = data_root() / "qsettings"

    # --- the main() insurance, replayed verbatim BEFORE QApplication ---
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      str(qs_dir))
    print(f"  PyQt6 {PYQT_VERSION_STR}: setDefaultFormat/setPath accepted "
          f"before QApplication creation")
    check("no qsettings/ directory before any QApplication/write",
          not qs_dir.exists(), str(qs_dir))

    from PyQt6.QtWidgets import QApplication  # noqa: E402
    app = QApplication([])
    app.setApplicationName("Supervertaler")
    app.setOrganizationName("Supervertaler")
    check("QApplication created after the insurance calls",
          app is not None and QApplication.instance() is not None)

    # --- bare startup: read-only QSettings must create nothing ---
    read_only = QSettings("Supervertaler", "PlainAppNoWrite")
    read_only.value("width", 1)
    check("read-only QSettings creates no directory",
          not qs_dir.exists(), str(qs_dir))

    # --- insurance target A: defaultFormat-honouring ctor (no-arg) ---
    s_def = QSettings()
    check("no-arg QSettings honours defaultFormat (IniFormat)",
          s_def.format() == QSettings.Format.IniFormat, str(s_def.format()))
    s_def.setValue("width", 42)
    s_def.sync()
    check("qsettings/ directory created by the write", qs_dir.exists(), str(qs_dir))
    # Qt nests ini files as <setPath-path>/<organization>/<app>.ini
    ini_def = qs_dir / "Supervertaler" / "Supervertaler.ini"
    check("no-arg QSettings write lands in <data_root>/qsettings/Supervertaler/Supervertaler.ini",
          ini_def.exists(), str(ini_def))
    text_def = ini_def.read_text(encoding="utf-8") if ini_def.exists() else ""
    check("ini carries the written value", "width=42" in text_def,
          repr(text_def[:200]))

    # --- insurance target B: explicit IniFormat ctor (setPath honoured) ---
    s_exp = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      "ZZOrg", "ZZApp")
    s_exp.setValue("mark", "p16")
    s_exp.sync()
    ini_exp = qs_dir / "ZZOrg" / "ZZApp.ini"
    check("explicit IniFormat ctor writes via setPath into qsettings/ZZOrg/ZZApp.ini",
          ini_exp.exists(), str(ini_exp))

    # --- Qt-design observation: 2-arg ctor is NativeFormat (registry path).
    # Documented, NOT written (read-only: this probe never touches the registry;
    # the limitation is a coordinator question, see report section 8).
    s2 = QSettings("ZZOrg2", "ZZApp2")
    check("Qt 6.11 observation: 2-arg QSettings(org,app) resolves to NativeFormat "
          "(defaultFormat NOT honoured by this ctor)",
          s2.format() == QSettings.Format.NativeFormat, str(s2.format()))
    s2.value("nothing")  # read-only, no write

    check("read-only QSettings created no file (bare startup)",
          not any("PlainAppNoWrite" in str(p) for p in qs_dir.rglob("*")))
    created_files = sorted(str(p.relative_to(qs_dir)).replace("\\", "/")
                           for p in qs_dir.rglob("*.ini"))
    check("qsettings/ contains only the two written files",
          created_files == sorted(["Supervertaler/Supervertaler.ini",
                                   "ZZOrg/ZZApp.ini"]),
          str(created_files))

    # --- registry untouched (M4, read-only) ---
    reg_after = reg_query(KEY)
    check("HKCU\\Software\\Supervertaler unchanged", reg_before == reg_after,
          f"before rc={reg_before[0]}, after rc={reg_after[0]}")

    # --- negative control: profile (AppData) clean ---
    noise = [p for p in (PROFILE / "AppData").rglob("*")
             if p.name == "Supervertaler"] if (PROFILE / "AppData").exists() else []
    check("no Supervertaler entry in the isolated AppData", not noise, str(noise))

    # --- AST: main() call order (the real app's behaviour contract) ---
    order = ast_order_check()
    print(f"  main() AST lines: {order}")
    qa = order["QApplication"]
    for k in ("setDefaultFormat", "setPath", "setAttribute"):
        check(f"main(): {k} present and before QApplication(sys.argv)",
              order[k] is not None and qa is not None and order[k] < qa,
              f"{k}@{order[k]} vs QApplication@{qa}")

    print("P16-QS-OK" if not FAILURES else f"P16-QS-FAIL {FAILURES}")
    sys.exit(0 if not FAILURES else 1)


main()
