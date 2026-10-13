# -*- coding: utf-8 -*-
"""Batch 9.4f probe: per-profile Custom chips in QuickTrans.

Checks:
  tab    — per-profile enable checkboxes under the Custom row (checked by
           default when mtql_llm_profiles absent); master checkbox intact.
  save   — Save persists mtql_llm_profiles = checked names; foreign keys intact.
  chips  — _add_llm_providers: master off -> no chips; enabled list -> chips
           for listed profiles only; absent list -> chip per profile w/ endpoint.
  exec   — create_llm_client(profile_name='Profile A') resolves Profile A's
           endpoint/model/key (global active profile unchanged).
Запуск: python probe_94f_profiles.py <tree-root> <iso-dir>
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
A = {"name": "Profile A", "endpoint": "http://127.0.0.1:1111/v1", "model": "model-a", "api_key": "sk-A"}
B = {"name": "Profile B", "endpoint": "http://127.0.0.1:2222/v1", "model": "model-b", "api_key": ""}
C = {"name": "Profile C", "endpoint": "", "model": "model-c", "api_key": ""}
data = {
    "ui": {
        "llm_settings": {"provider": "custom_openai", "custom_openai_profiles": [A, B, C],
                         "custom_openai_active_profile": "Profile B",
                         "custom_openai_model": "model-b",
                         "custom_openai_endpoint": "http://127.0.0.1:2222/v1"},
    },
    "general": {"mt_quick_lookup": {"mtql_custom_openai": True}},
    "api_keys": {},
}
(sd / "settings.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
settings_file = sd / "settings.json"

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QGroupBox, QCheckBox, QPushButton  # noqa: E402

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

# ---- tab ----
tab = win._create_mt_quick_lookup_settings_tab()
say("TAB OK")
groups = {g.title(): g for g in tab.findChildren(QGroupBox)}
llm_g = next((g for t, g in groups.items() if "AI/LLM Providers" in t), None)
cbs = [c.text() for c in llm_g.findChildren(QCheckBox)]
say("LLM CHECKBOXES:", cbs)
prof_cbs = {n: cb.isChecked() for n, cb in win._mtql_llm_profile_cbs.items()}
say("PROFILE CBS:", prof_cbs)
say("DEFAULT ALL ON:", all(prof_cbs.values()) and set(prof_cbs) == {"Profile A", "Profile B", "Profile C"})

# ---- save ----
# Uncheck Profile C, keep A+B; then Save.
win._mtql_llm_profile_cbs["Profile C"].setChecked(False)
save_btn = next((b for b in tab.findChildren(QPushButton) if "Save QuickTrans" in b.text()), None)
save_btn.click()
st = json.loads(settings_file.read_text(encoding="utf-8"))["general"]["mt_quick_lookup"]
say("SAVED mtql_llm_profiles:", st.get("mtql_llm_profiles"))
say("SAVE OK:", st.get("mtql_llm_profiles") == ["Profile A", "Profile B"] and st.get("mtql_custom_openai") is True)

# ---- chips ----
from modules.quicktrans import QuickTransPanel  # noqa: E402
qt = getattr(win, "quicktrans_panel", None) or QuickTransPanel(win)
llm = json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]

def chips(mq):
    provs = []
    qt._add_llm_providers(provs, {}, mq)
    return [(n, c) for n, c, _ in provs]

say("CHIPS master-off:", chips({"mtql_custom_openai": False}))
say("CHIPS enabled A,B:", chips({"mtql_custom_openai": True, "mtql_llm_profiles": ["Profile A", "Profile B"]}))
say("CHIPS enabled C-only:", chips({"mtql_custom_openai": True, "mtql_llm_profiles": ["Profile C"]}))
say("CHIPS list-absent:", chips({"mtql_custom_openai": True}))
say("CHIPS master-on-empty-list:", chips({"mtql_custom_openai": True, "mtql_llm_profiles": []}))

# ---- exec: profile_name plumbing ----
cA = win.create_llm_client("custom_openai", None, {}, settings=llm, profile_name="Profile A")
cB = win.create_llm_client("custom_openai", None, {}, settings=llm)  # active = Profile B
say("CLIENT A:", cA.base_url, cA.model, cA.api_key)
say("CLIENT ACTIVE:", cB.base_url, cB.model)
say("EXEC OK:", "1111" in str(cA.base_url) and cA.model == "model-a" and cA.api_key == "sk-A"
    and "2222" in str(cB.base_url) and cB.model == "model-b")
# global active profile unchanged
say("ACTIVE UNCHANGED:", llm.get("custom_openai_active_profile") == "Profile B")

say("PROBE DONE")
os._exit(0)
