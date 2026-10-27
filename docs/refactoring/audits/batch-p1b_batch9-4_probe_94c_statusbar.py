# -*- coding: utf-8 -*-
"""Batch 9.4c probe: status-bar LLM indicator, 3 states.

Scenarios (fresh iso profile, self-seeded):
  prof   — 2 profiles, active 'Profile B'  -> '🔌 Profile B: model-b'
  none   — no profiles, no legacy endpoint  -> '🔌 Custom profile not configured'
  legacy — legacy single-field endpoint     -> '🔌 Custom Endpoint: <model>'
Запуск: python probe_94c_statusbar.py <tree-root> <iso-dir> <scenario>
"""
import faulthandler, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
scenario = sys.argv[3]

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam: data root -> <iso>/Supervertaler
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"

sd = data_dir / "workbench" / "settings"
sd.mkdir(parents=True, exist_ok=True)
A = {"name": "Profile A", "endpoint": "http://127.0.0.1:1111/v1", "model": "model-a", "api_key": ""}
B = {"name": "Profile B", "endpoint": "http://127.0.0.1:2222/v1", "model": "model-b", "api_key": ""}
llm = {"provider": "custom_openai", "custom_openai_profiles": [], "custom_openai_active_profile": ""}
if scenario == "prof":
    llm.update({"custom_openai_profiles": [A, B], "custom_openai_active_profile": "Profile B",
                "custom_openai_model": "model-b", "custom_openai_endpoint": "http://127.0.0.1:2222/v1"})
elif scenario == "none":
    pass
elif scenario == "legacy":
    llm.update({"custom_openai_endpoint": "http://127.0.0.1:3333/v1", "custom_openai_model": "legacy-model"})
(sd / "settings.json").write_text(json.dumps({"ui": {"llm_settings": llm}}, indent=2), encoding="utf-8")

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

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
ind = getattr(win, "llm_indicator_label", None)
text = ind.text() if ind else "<absent>"
tip = ind.toolTip() if ind else ""
say("STATE:", scenario, "TEXT:", repr(text))
say("TIP:", repr(tip))

expect = {"prof": "🔌 Profile B: model-b",
          "none": "🔌 Custom profile not configured",
          "legacy": "🔌 Custom Endpoint: legacy-model"}[scenario]
say("EXPECTED:", repr(expect), "->", "OK" if text == expect else "MISMATCH")

# Local LLM read-only note present in AI Settings tab?
tab = win._create_ai_settings_tab()
from PyQt6.QtWidgets import QLabel  # noqa: E402
labels = [l.text() for l in tab.findChildren(QLabel)]
note = [t for t in labels if "Local server management is coming later" in t]
say("LOCAL-LLM NOTE:", "OK" if note else "MISSING", note[:1])
say("PROBE DONE")
os._exit(0)
