# -*- coding: utf-8 -*-
"""Batch #9.4a probe: AI Settings page after provider removal.

Scenarios (fresh iso profile, seeded externally):
  build  — window builds; AI Settings tab builds; NO remote provider widgets
           (radios/combos/enable cbs/API-key fields/Ollama group absent);
           Custom profiles section present; status-bar indicator text.
  save   — click "Save AI Settings" with 2 seeded profiles; verify:
           * profiles + active preserved, provider=custom_openai;
           * foreign llm_settings keys (custom_mt_profiles, legacy *_model,
             ollama_*) NOT erased;
           * provider_enabled_states: mt_* + legacy llm_* preserved,
             llm_custom_openai updated;
           * general_settings: enable_llm_matching + ollama_keepwarm keys
             preserved (inert), batch_size updated.
Запуск: python probe_94a_save.py <tree-root> <iso-dir> <scenario: build|save>
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
# Harness: winapi hotkey pump thread races with offscreen teardown (native AV
# in platform_helpers._message_pump, unrelated to 9.4a) — neutralize hotkeys.
Supervertaler.SuperlookupTab.register_global_hotkey = lambda self: None

RESULTS = iso / "results.txt"
_rfh = open(RESULTS, "w", encoding="utf-8", buffering=1)
def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True); _rfh.write(msg + "\n"); _rfh.flush()

settings_file = data_dir / "workbench" / "settings" / "settings.json"

def read_all():
    return json.loads(settings_file.read_text(encoding="utf-8"))

win = Supervertaler.SupervertalerQt()
say("WINDOW OK")

# Build the AI Settings tab (via the settings dialog builder path)
tab = win._create_ai_settings_tab()
say("AI TAB OK")

# 1) No remote provider widgets anywhere in the tab
from PyQt6.QtWidgets import QRadioButton, QComboBox, QGroupBox  # noqa: E402
radios = tab.findChildren(QRadioButton)
radio_texts = [r.text() for r in radios]
remote = [t for t in radio_texts if any(k in t for k in ("OpenAI", "Claude", "Gemini", "Mistral", "DeepSeek", "OpenRouter", "Ollama", "Local LLM")) and "Custom" not in t]
say("RADIOS:", radio_texts)
say("REMOTE RADIOS PRESENT:", remote)

combos = tab.findChildren(QComboBox)
combo_names = []
for c in combos:
    items = [c.itemText(i) for i in range(c.count())]
    combo_names.append((c.objectName() or "combo", items[:3]))
say("COMBOS:", combo_names)
modelish = [c for c in combos if any(any(k in it.lower() for k in ("gpt", "claude", "gemini", "mistral", "deepseek", "openrouter", "translategemma")) for it in [c.itemText(i) for i in range(c.count())])]
say("MODEL COMBOS PRESENT:", len(modelish))

group_titles = [g.title() for g in tab.findChildren(QGroupBox)]
say("GROUPS:", group_titles)
bad_groups = [t for t in group_titles if any(k in t for k in ("Ollama", "API Keys", "Enable/Disable"))]
say("BAD GROUPS:", bad_groups)

# Custom profiles section present?
from PyQt6.QtWidgets import QLabel  # noqa: E402
labels = [l.text() for l in tab.findChildren(QLabel)]
say("PROFILES SECTION:", any("Profile:" in t for t in labels),
      any("Custom (OpenAI-Compatible) Settings" in t for t in labels))

# 2) Status bar indicator
ind = getattr(win, "llm_indicator_label", None)
say("INDICATOR:", repr(ind.text()) if ind else "<absent>")

if scenario in ("save", "legacy"):
    before = read_all()
    # Record the Custom-enable checkbox state as it appears in the UI
    from PyQt6.QtWidgets import QCheckBox  # noqa: E402
    cbs = tab.findChildren(QCheckBox)
    custom_cb = [c for c in cbs if "Enable Custom" in c.text()]
    assert len(custom_cb) == 1, custom_cb
    cb_state = custom_cb[0].isChecked()
    # Click the Save button on the tab
    save_btns = [b for b in tab.findChildren(QPushButton) if "Save AI Settings" in b.text()]
    assert len(save_btns) == 1, save_btns
    save_btns[0].click()
    after = read_all()

    llm_b = before.get("ui", {}).get("llm_settings", {})
    llm_a = after.get("ui", {}).get("llm_settings", {})
    checks = []
    checks.append(("provider==custom_openai", llm_a.get("provider") == "custom_openai"))
    if scenario == "legacy":
        # Файл написан ДО 9.5 (ни у одного профиля нет supports_vision).
        # Save дописывает ключ только активному профилю (из чекбокса вкладки,
        # unchecked -> False); неактивный профиль остаётся без ключа.
        # «profiles preserved» = после снятия нового ключа словари равны.
        def _strip_vision(plist):
            return [{k: v for k, v in p.items() if k != "supports_vision"} for p in plist]
        checks.append(("profiles preserved (ignoring new supports_vision)",
                       _strip_vision(llm_a.get("custom_openai_profiles", []))
                       == llm_b.get("custom_openai_profiles", [])))
        _pa = next((p for p in llm_a.get("custom_openai_profiles", [])
                    if p.get("name") == llm_b.get("custom_openai_active_profile")), {})
        _na = next((p for p in llm_a.get("custom_openai_profiles", [])
                    if p.get("name") != llm_b.get("custom_openai_active_profile")), {})
        checks.append(("legacy: active profile gained supports_vision=False",
                       _pa.get("supports_vision") is False))
        checks.append(("legacy: non-active profile has no supports_vision key",
                       "supports_vision" not in _na))
    else:
        checks.append(("profiles preserved", llm_a.get("custom_openai_profiles") == llm_b.get("custom_openai_profiles")))
    checks.append(("active preserved", llm_a.get("custom_openai_active_profile") == llm_b.get("custom_openai_active_profile")))
    checks.append(("custom_mt_profiles intact", llm_a.get("custom_mt_profiles") == llm_b.get("custom_mt_profiles")))
    checks.append(("legacy openai_model intact", llm_a.get("openai_model") == llm_b.get("openai_model")))
    checks.append(("legacy ollama_model intact", llm_a.get("ollama_model") == llm_b.get("ollama_model")))
    checks.append(("legacy ollama_timeout intact", llm_a.get("ollama_timeout_minutes") == llm_b.get("ollama_timeout_minutes")))

    st_b = before.get("ui", {}).get("provider_enabled_states", {})
    st_a = after.get("ui", {}).get("provider_enabled_states", {})
    mt_ok = all(st_a.get(k) == v for k, v in st_b.items() if k.startswith("mt_"))
    legacy_ok = all(st_a.get(k) == v for k, v in st_b.items() if k.startswith("llm_") and k != "llm_custom_openai")
    checks.append(("mt_* states intact", mt_ok))
    checks.append(("legacy llm_* states intact", legacy_ok))
    checks.append(("llm_custom_openai == checkbox", st_a.get("llm_custom_openai") == cb_state))

    g_b = before.get("ui", {}).get("general_settings", {})
    g_a = after.get("ui", {}).get("general_settings", {})
    checks.append(("enable_llm_matching key intact", g_a.get("enable_llm_matching") == g_b.get("enable_llm_matching")))
    checks.append(("ollama_keepwarm key intact", g_a.get("ollama_keepwarm") == g_b.get("ollama_keepwarm")))
    checks.append(("batch_size updated", g_a.get("batch_size") == 21))
    checks.append(("mt_quick_lookup intact", g_a.get("mt_quick_lookup") == g_b.get("mt_quick_lookup")))

    ak_b = before.get("api_keys", {})
    ak_a = after.get("api_keys", {})
    checks.append(("api_keys intact", ak_a == ak_b))

    fails = [n for n, ok in checks if not ok]
    say("SAVE CHECKS:", "ALL OK" if not fails else f"FAIL {fails}")
    for n, ok in checks:
        say(("OK  " if ok else "FAIL") + " " + n)

say("PROBE DONE")
os._exit(0)
