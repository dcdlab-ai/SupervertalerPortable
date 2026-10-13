# -*- coding: utf-8 -*-
"""Batch 9.4d probe: QuickTrans tab LLM part, CUS chips, chat model menu.

Checks:
  tab    — AI/LLM Providers group: only Custom checkbox + popup-autofetch;
           no Claude/OpenAI/Gemini/Mistral/DeepSeek/OpenRouter/Ollama rows;
           _mtql_checkboxes has no mtql_claude/.../mtql_ollama keys.
  chips  — _add_llm_providers: mtql_custom_openai=True -> CUS chip;
           legacy mtql_claude/mtql_ollama=True -> no chips.
  menu   — chat model menu: active profile header + 'AI Settings…' action;
           no provider submenus.
Запуск: python probe_94d_qtchat.py <tree-root> <iso-dir>
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
A = {"name": "Profile A", "endpoint": "http://127.0.0.1:1111/v1", "model": "model-a", "api_key": ""}
B = {"name": "Profile B", "endpoint": "http://127.0.0.1:2222/v1", "model": "model-b", "api_key": ""}
data = {
    "ui": {
        "llm_settings": {"provider": "custom_openai", "custom_openai_profiles": [A, B],
                         "custom_openai_active_profile": "Profile B",
                         "custom_openai_model": "model-b",
                         "custom_openai_endpoint": "http://127.0.0.1:2222/v1"},
        "general_settings": {"mt_quick_lookup": {"mtql_custom_openai": True,
                                                 "mtql_claude": True, "mtql_ollama": True}},
    },
    "api_keys": {"openai": "sk-x", "claude": "sk-x"},
}
(sd / "settings.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QGroupBox, QCheckBox, QLineEdit  # noqa: E402
from PyQt6.QtWidgets import QMenu  # noqa: E402

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
say("LLM GROUP:", llm_g is not None)
cbs = [c.text() for c in llm_g.findChildren(QCheckBox)]
say("LLM CHECKBOXES:", cbs)
bad = [t for t in cbs if any(k in t for k in ("Claude", "OpenAI", "Gemini", "Mistral", "DeepSeek", "OpenRouter", "Ollama")) and "Custom" not in t]
say("BAD CHECKBOXES:", bad)
keys = sorted(k for k in win._mtql_checkboxes if k.startswith("mtql_"))
say("MTQL KEYS:", keys)
bad_keys = [k for k in keys if k in ("mtql_claude", "mtql_openai", "mtql_gemini", "mtql_mistral",
                                     "mtql_deepseek", "mtql_openrouter", "mtql_ollama")]
say("BAD MTQL KEYS:", bad_keys)
combos = sorted(k for k in win._mtql_llm_combos)
say("MTQL LLM COMBOS:", combos)
custom_edit = win._mtql_llm_combos.get("mtql_custom_openai_model")
say("CUSTOM MODEL FIELD:", repr(custom_edit.text()) if isinstance(custom_edit, QLineEdit) else "<absent>",
    "readonly=", custom_edit.isReadOnly() if isinstance(custom_edit, QLineEdit) else None)

# ---- chips ----
from modules.quicktrans import QuickTransPanel  # noqa: E402
qt = getattr(win, "quicktrans_panel", None)
if qt is None:
    qt = QuickTransPanel(win)
say("PANEL:", type(qt).__name__)
if qt is not None:
    provs = []
    qt._add_llm_providers(provs, {"openai": "sk-x", "claude": "sk-x"},
                          {"mtql_custom_openai": True, "mtql_claude": True, "mtql_ollama": True})
    say("CHIPS (custom+legacy on):", [(n, c) for n, c, _ in provs])
    provs2 = []
    qt._add_llm_providers(provs2, {}, {"mtql_claude": True, "mtql_ollama": True})
    say("CHIPS (legacy only):", [(n, c) for n, c, _ in provs2])

# ---- chat menu ----
from modules.chat_view_widget import ChatViewWidget  # noqa: E402
import gc  # noqa: E402
pm = getattr(win, "prompt_manager_qt", None)
cw = getattr(pm, "_ai_tab_chat_view", None) if pm else None
if cw is None and pm is not None:
    cw = getattr(pm, "_grid_chat_view", None)
if cw is None:
    cw = next((o for o in gc.get_objects() if isinstance(o, ChatViewWidget)), None)
say("CHAT WIDGET:", cw is not None)
if cw is not None:
    captured = {}
    def fake_exec(self, pos=None):
        acts = []
        for a in self.actions():
            acts.append((a.text(), a.isEnabled()))
        captured["actions"] = acts
        return None
    QMenu.exec = fake_exec
    cw._show_model_menu()
    say("MENU ACTIONS:", captured.get("actions"))

say("PROBE DONE")
os._exit(0)
