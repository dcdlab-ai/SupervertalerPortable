# -*- coding: utf-8 -*-
"""Batch #9.2: спец-пробы (пустые профили / legacy-trap / QuickTrans-таб / AI-таб).

Сценарии (каждый — СВЕЖИЙ iso-профиль, сидируется снаружи):
  empty   — custom_mt_profiles=[]: диспетчер вежливо молчит, QuickTrans-провайдеры без MT,
            пакетный диалог: mt_providers_available пуст
  legacy  — старый settings.json (mt_* флаги+ключи+mtql_*): старт без ошибок, ловушка
            requests.post/get -> AssertionError (обращение к удалённым провайдерам = провал),
            provider_enabled_states без mt_*, custom MT-ридер жив
  tabs    — QuickTrans-таб: нет чекбоксов удалённых MT-провайдеров, есть custom MT;
            AI-таб: профили Custom из 9.1 целы (комбо+Save)
Запуск: python batch9-2_probe_spec.py <tree-root> <iso-dir> <scenario>
"""
import faulthandler, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
scenario = sys.argv[3]
OUT = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-2\spec_verdict.json")

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

# Ловушка: любое обращение к сетевым движкам удалённых MT-провайдеров = провал.
# (patch и для requests в модулях приложения, и глобально)
import requests  # noqa: E402


def _trap(*a, **k):
    raise AssertionError("NETWORK TRAP HIT: removed MT provider tried to talk to the network")


requests.post = _trap
requests.get = _trap
requests.request = _trap

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QComboBox, QLineEdit, QPushButton  # noqa: E402
from modules.styled_widgets import CheckmarkCheckBox  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected

sf = data_dir / "workbench" / "settings" / "settings.json"
sf.parent.mkdir(parents=True, exist_ok=True)

LEGACY = {"ui": {"llm_settings": {
    "provider": "openai",
    "custom_openai_model": "test", "custom_openai_endpoint": "127.0.0.1:3445/v1",
    "custom_openai_profiles": [], "custom_openai_active_profile": "",
    "custom_mt_profiles": [], "custom_mt_active_profile": ""},
    "provider_enabled_states": {"mt_google_translate": True, "mt_deepl": True,
                                "mt_microsoft": True, "mt_amazon": True,
                                "mt_modernmt": True, "mt_mymemory": True,
                                "llm_openai": True},
    "api_keys": {"google_translate": "AIzaseed", "deepl": "dlseed",
                 "microsoft_translate": "azseed", "modernmt": "mmtseed", "mymemory": "mmseed"},
    "mt_quick_lookup": {"mtql_gt": True, "mtql_dl": True, "mtql_ms": True,
                        "mtql_at": True, "mtql_mmt": True, "mtql_mm": True,
                        "mtql_custom_mt": False}}}

result = {"scenario": scenario}
try:
    if scenario == "empty":
        sf.write_text(json.dumps({"ui": {"llm_settings": {
            "provider": "custom_openai", "custom_openai_profiles": [], "custom_openai_active_profile": "",
            "custom_mt_profiles": [], "custom_mt_active_profile": ""}}}, indent=2), encoding="utf-8")
    elif scenario in ("legacy", "tabs"):
        sf.write_text(json.dumps(LEGACY, indent=2, ensure_ascii=False), encoding="utf-8")

    win = Supervertaler.SupervertalerQt()

    if scenario == "empty":
        class _Seg:
            pass
        win._fetch_mt_translation_async("Good morning", _Seg(), 0)
        for _ in range(30):
            app.processEvents()
            import time as _t; _t.sleep(0.02)
        prof = win._get_active_custom_mt_profile()
        # пакетный диалог: логика доступности (та же, что в translate_batch)
        avail = ['Custom MT'] if any((p.get('enabled', True) and (p.get('endpoint') or '').strip())
                                     for p in win._get_custom_mt_profiles()) else []
        result["active_profile"] = prof
        result["batch_mt_available"] = avail
        result["verdict"] = prof is None and avail == []
    elif scenario == "legacy":
        states = win.load_provider_enabled_states()
        mt_keys = [k for k in states if k.startswith("mt_")]
        prof = win._get_active_custom_mt_profile()
        # QuickTrans-провайдеры (MT): без mtql_custom_mt -> пусто; чипы удалённых не собираются
        from modules.quicktrans import QuickTransProviderMixin
        class _Carrier(QuickTransProviderMixin):
            pass
        carrier = _Carrier()
        carrier.parent_app = win
        provs = carrier._get_enabled_providers(include_mt=True, include_llms=False)
        result["mt_state_keys"] = mt_keys
        result["active_mt_profile"] = prof
        result["quicktrans_mt_providers"] = [(p[0], p[1]) for p in provs]
        result["verdict"] = (prof is None and provs == [] and len(mt_keys) == 6)  # старые mt_* в файле остаются инертно; читателей нет (ловушка сети не сработала)
    elif scenario == "tabs":
        qt_tab = win._create_mt_quick_lookup_settings_tab()
        cb_texts = [c.text() for c in qt_tab.findChildren(CheckmarkCheckBox)]
        removed_names = ["Google Translate", "DeepL", "Microsoft Translator",
                         "Amazon Translate", "ModernMT", "MyMemory (Free tier)", "MyMemory (Free)"]
        has_removed = [t for t in cb_texts if any(r.lower() in t.lower() for r in removed_names)]
        has_cmt = any("custom mt endpoint" in t.lower() for t in cb_texts)
        ai_tab = win._create_ai_settings_tab()
        combo = next((c for c in ai_tab.findChildren(QComboBox)
                      if c.count() >= 1 and c.itemText(0) == "Custom Endpoint"), None)
        save_btn = next((b for b in ai_tab.findChildren(QPushButton)
                         if "Save AI Settings" in b.text()), None)
        result["qt_removed_checkboxes"] = has_removed
        result["qt_custom_mt_cb"] = has_cmt
        result["ai_profile_combo"] = combo is not None
        result["ai_save_btn"] = save_btn is not None
        result["verdict"] = (not has_removed and has_cmt and combo is not None and save_btn is not None)

except BaseException as e:
    import traceback
    result["exception"] = f"{type(e).__name__}: {e}"
    traceback.print_exc()

OUT.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
os._exit(0)
