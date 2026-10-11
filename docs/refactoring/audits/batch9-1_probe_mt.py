# -*- coding: utf-8 -*-
"""9.1b(iii): _get_active_custom_mt_profile возвращает нормализованную копию, диск не меняется.
Вердикт пишется в файл mt_verdict.json (stdout приложения нестабилен после старта).
Запуск: python batch9-1_probe_mt.py <tree-root> <iso-dir>
"""
import faulthandler, hashlib, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
OUT = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b9-1\mt_verdict.json")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg = iso / "AppData" / "Roaming" / "Supervertaler"
cfg.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8")

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected

sf = data_dir / "workbench" / "settings" / "settings.json"
sf.parent.mkdir(parents=True, exist_ok=True)
sf.write_text(json.dumps({"ui": {"llm_settings": {
    "provider": "custom_openai",
    "custom_mt_profiles": [{"name": "MT Local", "endpoint": "127.0.0.1:5000/v1",
                            "model": "mt", "api_key": ""}],
    "custom_mt_active_profile": "MT Local"}}}, indent=2, ensure_ascii=False), encoding="utf-8")

result = {}
try:
    win = Supervertaler.SupervertalerQt()
    h0 = hashlib.sha256(sf.read_bytes()).hexdigest()
    ls = win.load_llm_settings()
    prof = win._get_active_custom_mt_profile(ls)
    h1 = hashlib.sha256(sf.read_bytes()).hexdigest()
    result = {"endpoint": prof.get("endpoint"), "unchanged": h0 == h1,
              "verdict": prof.get("endpoint") == "http://127.0.0.1:5000/v1" and h0 == h1}
except BaseException as e:
    import traceback
    result = {"exception": f"{type(e).__name__}: {e}"}
    traceback.print_exc()

OUT.write_text(json.dumps(result), encoding="utf-8")
os._exit(0)
