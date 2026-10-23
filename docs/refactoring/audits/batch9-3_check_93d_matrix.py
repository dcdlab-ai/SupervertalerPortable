# -*- coding: utf-8 -*-
"""Batch 9.3 матрица совместимости (рекон п.8) + поведение llm_clients.

provider ∈ {openai, claude, gemini, mistral, deepseek, openrouter, ollama,
custom_openai, '', неизвестная строка, отсутствует ключ} × профили
{есть / нет / только legacy-плоские / active не найден в списке}."""
import json, os, pathlib, sys, tempfile

sys.path.insert(0, r"E:\Dev\SupervertalerPortable")
tmp = pathlib.Path(tempfile.mkdtemp(dir=r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-3"))
work = tmp / "workbench" / "settings"; work.mkdir(parents=True)
ptr = tmp / "_cfg"; (ptr / "Supervertaler").mkdir(parents=True)
os.environ["APPDATA"] = str(ptr)
(ptr / "Supervertaler" / "config.json").write_text(
    '{"user_data_path": "' + str(tmp).replace("\\", "\\\\") + '"}', encoding="utf-8")

import modules.settings_service as ss_mod
import modules.llm_clients as llm

svc = ss_mod.SettingsService(settings_dir=work, log=lambda m: None)

def set_llm(d):
    (work / "settings.json").write_text(
        json.dumps({"ui": {"llm_settings": d}}, ensure_ascii=False), encoding="utf-8")

def get_llm():
    return json.loads((work / "settings.json").read_text(encoding="utf-8"))["ui"]["llm_settings"]

PROVIDERS = ["openai", "claude", "gemini", "mistral", "deepseek", "openrouter",
             "ollama", "custom_openai", "", "mystery-llm"]
PROFILES = {
    "есть": [{"name": "P1", "endpoint": "http://127.0.0.1:9/v1", "model": "m1", "api_key": "k1"}],
    "нет": [],
    "legacy-flat": None,   # специальный случай: плоские поля, профилей нет
    "active-не-найден": [{"name": "P1", "endpoint": "http://127.0.0.1:9/v1", "model": "m1", "api_key": "k1"}],
}
ok = fail = 0
for prov in PROVIDERS:
    for pname, profs in PROFILES.items():
        d = {"provider": prov}
        if pname == "legacy-flat":
            d.update({"custom_openai_endpoint": "127.0.0.1:3445/v1", "custom_openai_model": "flat-m"})
        elif pname == "active-не-найден":
            d.update({"custom_openai_profiles": profs, "custom_openai_active_profile": "GHOST"})
        else:
            d.update({"custom_openai_profiles": profs, "custom_openai_active_profile": (profs[0]["name"] if profs else "")})
        set_llm(d)
        got = svc.load_llm_settings()
        on_disk = get_llm()
        try:
            assert got["provider"] == "custom_openai", got["provider"]
            assert on_disk.get("provider") == prov, "disk rewritten!"
            if pname == "есть":
                assert got["custom_openai_profiles"] and got["custom_openai_profiles"][0]["name"] == "P1"
            elif pname == "нет":
                assert got["custom_openai_profiles"] == []
            elif pname == "legacy-flat":
                assert got["custom_openai_profiles"][0]["endpoint"] == "http://127.0.0.1:3445/v1"
            elif pname == "active-не-найден":
                # миграция не лечит ghost-active (это работа _get_active_custom_profile -> первый профиль)
                assert got["custom_openai_active_profile"] == "GHOST"
        except AssertionError as e:
            fail += 1
            print(f"  FAIL {prov!r} × {pname}: {e}")
        else:
            ok += 1
print(f"matrix load_llm_settings: {ok} ok / {fail} fail (disk never rewritten)")

# --- LLMClient: только custom_openai исполняется; остальные — ValueError ---
c = llm.LLMClient(api_key="not-needed", provider="custom_openai", model="m",
                  base_url="http://127.0.0.1:9/v1")
assert c.model == "m"
c2 = llm.LLMClient(api_key="x", provider="custom_openai")   # модель не задана -> дефолт
assert c2.model == "custom-model", c2.model
try:
    llm.LLMClient(api_key="", provider="custom_openai", model="m")  # ключ пуст — допустимо
    keyless = True
except ValueError:
    keyless = False
assert keyless, "custom_openai must be keyless"

for prov in ["openai", "claude", "gemini", "mistral", "deepseek", "openrouter", "ollama", "weird"]:
    try:
        cc = llm.LLMClient(api_key="k", provider=prov, model="mm")
        try:
            cc.translate_with_usage(text="x", source_lang="en", target_lang="nl")
            print(f"  FAIL {prov}: request EXECUTED (must ValueError)")
            fail += 1
        except ValueError as e:
            assert "has been removed" in str(e), e
            ok += 1
    except ValueError as e:
        # __init__ может отклонить раньше (нет модели в DEFAULT_MODELS) — тоже валидно
        ok += 1
print("LLMClient: чужой provider -> ValueError ('has been removed'), custom_openai исполняется")

# --- vision: всегда False до 9.5 ---
for prov, model in [("custom_openai", "any-vision-model"), ("claude", "claude-sonnet-5-5"), ("openai", "gpt-5.5")]:
    assert llm.LLMClient.model_supports_vision(prov, model) is False
print("model_supports_vision: False для всех (VISION_MODELS = {}, галка — 9.5)")

# --- keep-alive имена 9.4 существуют ---
assert callable(llm.set_ollama_timeout)          # _apply_ollama_timeout_setting (9.4)
assert "MISTRAL_MODELS" in dir(llm.LLMClient)    # меню чата (9.4)
assert "CLAUDE_MODELS" in dir(llm.LLMClient)
assert "OLLAMA_MODELS" in dir(llm.LLMClient)
assert "OPENROUTER_MODELS" in dir(llm.LLMClient)
assert not hasattr(llm.LLMClient, "check_ollama_status")
assert not hasattr(llm.LLMClient, "get_ollama_model_info")
assert not hasattr(llm, "get_google_translation")
assert not hasattr(llm, "get_openai_translation")
assert not hasattr(llm, "get_claude_translation")
assert llm.LLMConfig is not None and llm.load_api_keys is not None
print("имена 9.4 живы (set_ollama_timeout, *_MODELS для меню чата); удалённые отсутствуют")
print("ALL MATRIX CHECKS PASSED" if fail == 0 else f"FAILURES: {fail}")
