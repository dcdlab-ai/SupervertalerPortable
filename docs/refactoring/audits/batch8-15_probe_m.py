# -*- coding: utf-8 -*-
"""Спец-проба M: MyMemory по умолчанию OFF только для новых установок.

Сценарии (iso-профиль готовится снаружи):
  clean         — settings.json без ui.provider_enabled_states -> False/unchecked
  upgrade-true  — ui.provider_enabled_states = {"mt_mymemory": true}  -> True/checked
  upgrade-false — ui.provider_enabled_states = {"mt_mymemory": false} -> False/unchecked
После старта: settings.json НЕ перезаписывается (хеш до == хеш после).

Запуск: python batch8-15_probe_m.py <tree-root> <iso-dir> <tag>
"""
import faulthandler, hashlib, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg_dir = iso / "AppData" / "Roaming" / "Supervertaler"
cfg_dir.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg_dir / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8"
)

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QCheckBox  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected

settings_file = data_dir / "workbench" / "settings" / "settings.json"

def _pes():
    """ui.provider_enabled_states из settings.json (или None)."""
    if not settings_file.exists():
        return None
    try:
        return json.loads(settings_file.read_text(encoding="utf-8")).get("ui", {}).get("provider_enabled_states")
    except Exception as e:
        return f"<err {e}>"

before_pes = _pes()
existed_before = settings_file.exists()
before_hash = hashlib.sha256(settings_file.read_bytes()).hexdigest() if existed_before else "<absent>"

win = Supervertaler.SupervertalerQt()
print(f"[{tag}] window built", flush=True)

logic_val = win.load_provider_enabled_states().get("mt_mymemory")
cb = next((c for c in win.findChildren(QCheckBox)
           if c.text() == "Enable MyMemory (Free tier)"), None)
ui_val = cb.isChecked() if cb else None

raw_pes = None
if settings_file.exists():
    try:
        raw_pes = json.loads(settings_file.read_text(encoding="utf-8")).get("ui", {}).get("provider_enabled_states")
    except Exception as e:
        raw_pes = f"<err {e}>"

after_hash = hashlib.sha256(settings_file.read_bytes()).hexdigest() if settings_file.exists() else "<absent>"
after_pes = _pes()
report = {
    "logic_mt_mymemory": logic_val,
    "ui_checkbox_checked": ui_val,
    "pes_before": before_pes,
    "pes_after": after_pes,
    "pes_unchanged": (before_pes == after_pes) if existed_before else None,
    "settings_json_unchanged": (before_hash == after_hash) if existed_before else None,
}
print(f"[{tag}] REPORT {json.dumps(report)}", flush=True)
ok = report["logic_mt_mymemory"] == report["ui_checkbox_checked"] is not None \
     and (not existed_before or report["pes_unchanged"])
print(f"[{tag}] RESULT {'OK' if ok else 'FAIL'}", flush=True)
os._exit(0 if ok else 1)
