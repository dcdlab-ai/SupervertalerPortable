# -*- coding: utf-8 -*-
"""Batch 9.4g probe: Custom MT endpoint scheme normalization (Dmitry's note #1).

Checks:
  save  — QuickTrans tab Save normalizes schemeless Custom MT endpoint
          (192.168.1.5:8080/v1 -> http://192.168.1.5:8080/v1) in settings.json
          and shows it in the field (pattern of AI Settings 9.1b).
  read  — call_custom_mt normalizes schemeless endpoint on read (LLMClient
          base_url gets the scheme).
  keep  — endpoint with scheme passes through unchanged.
Запуск: python probe_94g_mtfix.py <tree-root> <iso-dir>
"""
import faulthandler, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()

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
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8")

sd = data_dir / "workbench" / "settings"
sd.mkdir(parents=True, exist_ok=True)
data = {
    "ui": {"llm_settings": {"provider": "custom_openai",
                            "custom_mt_profiles": [
                                {"name": "MT1", "endpoint": "192.168.1.5:8080/v1",
                                 "model": "mt-model", "api_key": "", "enabled": True},
                                {"name": "MT2", "endpoint": "http://192.168.1.9:1234/v1",
                                 "model": "mt2", "api_key": "", "enabled": True}],
                            "custom_mt_active_profile": "MT1"}},
    "general": {"mt_quick_lookup": {"mtql_custom_mt": True}},
    "api_keys": {},
}
(sd / "settings.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
settings_file = sd / "settings.json"

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
Supervertaler.SuperlookupTab.register_global_hotkey = lambda self: None

RESULTS = iso / "results.txt"
_rfh = open(RESULTS, "w", encoding="utf-8", buffering=1)
def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True); _rfh.write(msg + "\n"); _rfh.flush()

win = Supervertaler.SupervertalerQt()
say("WINDOW OK")

# ---- save: schemeless endpoint in tab -> normalized in file + field ----
tab = win._create_mt_quick_lookup_settings_tab()
win._custom_mt_endpoint_input.setText("192.168.1.5:8080/v1")
save_btn = next((b for b in tab.findChildren(QPushButton) if "Save QuickTrans" in b.text()), None)
save_btn.click()
mt1 = next(p for p in json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]["custom_mt_profiles"] if p["name"] == "MT1")
mt2 = next(p for p in json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]["custom_mt_profiles"] if p["name"] == "MT2")
say("SAVED MT1 endpoint:", repr(mt1["endpoint"]))
say("SAVED MT2 endpoint:", repr(mt2["endpoint"]))
say("FIELD SHOWS:", repr(win._custom_mt_endpoint_input.text()))
say("SAVE OK:", mt1["endpoint"] == "http://192.168.1.5:8080/v1"
    and mt2["endpoint"] == "http://192.168.1.9:1234/v1"
    and win._custom_mt_endpoint_input.text() == "http://192.168.1.5:8080/v1")

# ---- read: call_custom_mt normalizes schemeless endpoint (capture LLMClient) ----
import modules.llm_clients as _lc  # noqa: E402
_captured = {}
_Real = _lc.LLMClient
class _Spy(_Real):
    def __init__(self, *a, **k):
        _captured.update(k)
        raise RuntimeError("stop-before-network")
_lc.LLMClient = _Spy
out = win.call_custom_mt("text", "en", "nl", {"name": "MTX", "endpoint": "192.168.1.5:8080/v1", "model": "m", "api_key": ""})
_lc.LLMClient = _Real
say("READ base_url:", repr(_captured.get("base_url")))
say("READ OK:", _captured.get("base_url") == "http://192.168.1.5:8080/v1")

# ---- read: active profile from disk (schemeless MT1) ----
_captured.clear()
_lc.LLMClient = _Spy
out2 = win.call_custom_mt("text", "en", "nl")
_lc.LLMClient = _Real
say("ACTIVE base_url:", repr(_captured.get("base_url")))
say("ACTIVE OK:", _captured.get("base_url") == "http://192.168.1.5:8080/v1")

say("PROBE DONE")
os._exit(0)
