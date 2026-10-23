# -*- coding: utf-8 -*-
"""Batch #9.3 спецификация: «не настроено» без сети + ловушка сети + Save AI Settings.

Сценарии (один соло-прогон):
  A. legacy-trap: settings.json с provider=ollama, llm_*/mt_* ключами, облачными
     ключами api_keys, БЕЗ custom-профилей -> старт чистый, provider мигрирует,
     диск не переписан, ловушка сети не сработала.
  B. «не настроено»: translate_current_segment / translate_batch / _run_proofreading /
     Match Panel / QuickTrans-чип / chat-клиент — вежливые сообщения/тихий выход,
     НОЛЬ сетевых попыток (ловушка requests+socket на не-loopback).
  C. Save AI Settings: страница открывается; Save кликается при КАЖДОМ радио
     (openai/claude/gemini/mistral/deepseek/openrouter/ollama/custom) — не падает;
     после Save+load provider == custom_openai.
Вердикт в JSON.
"""
import json, os, pathlib, socket, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]
OUT = pathlib.Path(rf"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-3\spec_verdict_{tag}.json")

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
sys.path.insert(0, str(tree))

# ---------- ЛОВУСКА СЕТИ: любой не-loopback connect -> AssertionError ----------
_real_connect = socket.socket.connect
TRAP = {"hits": []}

def trapped_connect(self, address):
    host = address[0] if isinstance(address, tuple) else str(address)
    if host not in ("127.0.0.1", "localhost", "::1"):
        TRAP["hits"].append(str(address))
        raise AssertionError(f"NETWORK TRAP: connect to {address}")
    return _real_connect(self, address)

socket.socket.connect = trapped_connect

import requests  # noqa: E402
_real_request = requests.Session.request

def trapped_request(self, *a, **k):
    url = a[1] if len(a) > 1 else k.get("url", "") or ""
    host = ""
    m = url.split("//", 1)
    if len(m) == 2:
        host = m[1].split("/", 1)[0].split(":", 1)[0].lower()
    if host in ("127.0.0.1", "localhost", "::1"):
        return _real_request(self, *a, **k)  # loopback разрешён (UI-виджет Ollama статуса до 9.4)
    TRAP["hits"].append(f"requests: {url}")
    raise AssertionError(f"NETWORK TRAP: requests {url}")

requests.Session.request = trapped_request

from PyQt6.QtWidgets import QRadioButton, QPushButton  # noqa: E402
import Supervertaler as SV  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Accepted
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

open_queue = [r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-3\inputs\test.txt"]
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (open_queue.pop(0) if open_queue else "", ""))

# ---------- A. сид: legacy ollama-настройки, БЕЗ custom-профилей ----------
sf = data_dir / "workbench" / "settings" / "settings.json"
sf.parent.mkdir(parents=True, exist_ok=True)
SEED = {
    "ui": {
        "llm_settings": {
            "provider": "ollama", "ollama_model": "qwen3:8b", "ollama_timeout_minutes": 7,
            "openai_model": "gpt-5.5", "claude_model": "claude-sonnet-5-5",
            "custom_openai_endpoint": "", "custom_openai_profiles": [],
            "custom_openai_active_profile": ""},
        "provider_enabled_states": {"llm_openai": False, "llm_claude": True,
                                    "mt_deepl": True, "llm_custom_openai": True},
        "mt_quick_lookup": {"mtql_claude": True, "mtql_openai": True, "mtql_custom_mt": False},
    },
    "api_keys": {"openai": "sk-legacy-openai", "claude": "sk-legacy-claude",
                 "google": "AIza-legacy", "deepl": "legacy-dl"},
}
sf.write_text(json.dumps(SEED, indent=1, ensure_ascii=False), encoding="utf-8")
DISK_BEFORE = json.loads(sf.read_text(encoding="utf-8"))["ui"]["llm_settings"]["provider"]

result = {"tag": tag, "trap_hits": TRAP["hits"]}
try:
    win = SV.SupervertalerQt()
    import time as _time
    for _ in range(60):
        app.processEvents()
        _time.sleep(0.05)

    llm = win.load_llm_settings()
    result["A_provider_migrated"] = llm["provider"] == "custom_openai"
    _disk_after = json.loads(sf.read_text(encoding="utf-8"))["ui"]["llm_settings"]["provider"]
    result["A_disk_provider_untouched"] = _disk_after == DISK_BEFORE
    result["A_ready_is_None"] = win._custom_llm_ready(llm) is None

    # --- B. «не настроено» на всех путях ---
    win.import_simple_txt()
    for _ in range(40):
        app.processEvents()
        _time.sleep(0.05)

    n0 = len(TRAP["hits"])
    win.table.selectRow(1)
    win.translate_current_segment()
    result["B_single_no_network"] = len(TRAP["hits"]) == n0
    result["B_single_target_empty"] = not win.current_project.segments[1].target

    n0 = len(TRAP["hits"])
    rows = [(i, win.current_project.segments[i]) for i in (1, 2)]
    win.translate_batch(segments_with_rows=rows, scope_description="spec")
    result["B_batch_no_network"] = len(TRAP["hits"]) == n0
    result["B_batch_no_targets"] = all(not win.current_project.segments[i].target for i in (1, 2))

    n0 = len(TRAP["hits"])
    win._run_proofreading([(0, win.current_project.segments[0])], "custom_openai", "m", "", win.load_llm_settings())
    result["B_proofread_no_network"] = len(TRAP["hits"]) == n0

    n0 = len(TRAP["hits"])
    win.enable_llm_matching = True
    win.enable_mt_matching = False
    matches = {"LLM": [], "MT": [], "TM": []}
    win._add_mt_and_llm_matches(win.current_project.segments[4], matches, "en", "nl", "en", "nl")
    result["B_matchpanel_silent"] = (len(TRAP["hits"]) == n0 and matches["LLM"] == [])

    n0 = len(TRAP["hits"])
    win.enable_llm_matching = False

    n0 = len(TRAP["hits"])
    backend = win.prompt_manager_qt.chat_backend
    backend.refresh_llm_client()
    result["B_chat_client_None"] = backend.llm_client is None
    result["B_chat_no_network"] = len(TRAP["hits"]) == n0

    # QuickTrans-чип напрямую (родительский метод mixin)
    n0 = len(TRAP["hits"])
    class _Carrier:
        pass
    from modules.quicktrans import QuickTransProviderMixin
    carrier = _Carrier()
    carrier.parent_app = win
    chip_result = QuickTransProviderMixin._call_llm_translation(
        carrier, "custom_openai", "Hello", "English", "Dutch", None)
    result["B_quicktrans_message"] = "not configured" in chip_result.lower()
    result["B_quicktrans_no_network"] = len(TRAP["hits"]) == n0

    # --- C. страница AI Settings: Save на каждом радио ---
    tabs = win.settings_tabs if hasattr(win, "settings_tabs") else None
    # находим страницу по заголовку через sidebar-навигацию (label-based)
    result["C_page_list"] = None
    try:
        win._go_to_settings_tab("AI Settings")
        for _ in range(30):
            app.processEvents()
        save_btn = None
        radios = {}
        for rb in win.findChildren(QRadioButton):
            t = rb.text()
            for key in ("OpenAI", "Anthropic Claude", "Google Gemini", "Mistral AI", "DeepSeek",
                        "OpenRouter", "Local LLM", "Custom (OpenAI-Compatible API)"):
                if key in t:
                    radios[key] = rb
        result["C_radios_found"] = sorted(radios.keys())
        # кнопка Save: на странице AI Settings её text() == 'Save AI Settings' (или похожее)
        for btn in win.findChildren(QPushButton):
            if "Save" in btn.text() and "AI" in btn.text():
                save_btn = btn
                break
        result["C_save_btn"] = save_btn.text() if save_btn else None
        if save_btn:
            saves_ok = 0
            for key, rb in radios.items():
                rb.setChecked(True)
                app.processEvents()
                save_btn.click()
                for _ in range(20):
                    app.processEvents()
                saves_ok += 1
                after = win.load_llm_settings()["provider"]
                if after != "custom_openai":
                    result[f"C_after_save_{key}"] = after
            result["C_saves_ok"] = saves_ok
            result["C_provider_still_custom"] = win.load_llm_settings()["provider"] == "custom_openai"
    except Exception as e:
        import traceback
        result["C_exception"] = f"{type(e).__name__}: {e}"
        result["C_tb"] = traceback.format_exc()[-800:]

    result["trap_hits_total"] = TRAP["hits"]
    result["verdict"] = "OK" if not TRAP["hits"] else "TRAP-HIT"
except BaseException as e:
    import traceback
    result["exception"] = f"{type(e).__name__}: {e}"
    result["traceback"] = traceback.format_exc()[-1500:]
    result["verdict"] = "EXCEPTION"

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
os._exit(0)
