# -*- coding: utf-8 -*-
"""Full-app read-only snapshot probe (Batch #3c practice).

Instantiates SupervertalerQt offscreen and records every instance of the
requested widget classes found in the live UI (count, text, checked, enabled,
size, sha256 of styleSheet(), class_module). Widgets that only exist inside
modal dialogs are captured by monkeypatching QDialog.exec: the stub snapshots
the dialog's children and returns Rejected, so nothing is persisted.

User data does NOT follow cwd — it resolves from the global
~/.supervertaler_config.json. This probe is read-only and safe to run from a
git worktree for before/after comparison.

Usage:
    python probe_app.py <repo_root> <out.json> [--classes A,B,C] [--dialog MethodName]
Defaults: --classes PinkCheckmarkCheckBox,BlueCheckmarkCheckBox,OrangeCheckmarkCheckBox,CustomRadioButton
          --dialog _show_create_termbase_dialog (pass empty string to skip)
"""
import faulthandler, hashlib, json, os, sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

root, out_json = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
def _opt(name, default):
    return args[args.index(name) + 1] if name in args else default
class_names = _opt("--classes",
                   "PinkCheckmarkCheckBox,BlueCheckmarkCheckBox,OrangeCheckmarkCheckBox,CustomRadioButton").split(",")
dialog_method = _opt("--dialog", "_show_create_termbase_dialog")

sys.path.insert(0, root)
faulthandler.dump_traceback_later(90, repeat=True, file=sys.stderr)

from PyQt6.QtWidgets import QApplication, QDialog
app = QApplication(sys.argv)

import Supervertaler as sv
from Supervertaler import SupervertalerQt

dialog_snapshot = {}
if dialog_method:
    _orig_exec = QDialog.exec
    def _exec_stub(self, *a, **k):
        for name in class_names:
            cls = getattr(sv, name)
            dialog_snapshot.setdefault(name, []).extend(wd.text() for wd in self.findChildren(cls))
        return QDialog.DialogCode.Rejected
    QDialog.exec = _exec_stub

w = SupervertalerQt()
if dialog_method:
    try:
        getattr(w, dialog_method)(None, None, 0)
    except Exception as e:
        print("dialog probe error:", e)
    finally:
        QDialog.exec = _orig_exec
faulthandler.cancel_dump_traceback_later()

report = {"root": root, "window_title": w.windowTitle()}
for name in class_names:
    cls = getattr(sv, name)
    items = []
    for wd in w.findChildren(cls):
        items.append({
            "text": wd.text(),
            "checked": wd.isChecked(),
            "enabled": wd.isEnabled(),
            "size": [wd.width(), wd.height()],
            "stylesheet_sha256": hashlib.sha256(wd.styleSheet().encode("utf-8")).hexdigest(),
            "class_module": type(wd).__module__,
        })
    report[name] = {"count": len(items), "instances": items}
report["dialog_snapshot"] = dialog_snapshot

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print("PROBE_OK", json.dumps({k: (v["count"] if isinstance(v, dict) and "count" in v else v)
                              for k, v in report.items() if k not in ("root", "dialog_snapshot")}))
