# -*- coding: utf-8 -*-
"""9.3a юнит: миграция load_llm_settings (молча, диск не переписывается), нормализация legacy,
делегат монолита == реализация сервиса (15 кейсов 9.1b)."""
import json, os, pathlib, sys, tempfile
sys.path.insert(0, r"E:\Dev\SupervertalerPortable")
tmp = tempfile.mkdtemp(dir=r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-3")
work = pathlib.Path(tmp) / "workbench" / "settings"
work.mkdir(parents=True)
ptr = pathlib.Path(tmp) / "_cfg"
ptr.mkdir()
os.environ["APPDATA"] = str(ptr)
(ptr / "Supervertaler").mkdir()
(ptr / "Supervertaler" / "config.json").write_text(
    '{"user_data_path": "' + str(pathlib.Path(tmp)).replace("\\", "\\\\") + '"}', encoding="utf-8")

import importlib
ss_mod = importlib.import_module("modules.settings_service")

svc = ss_mod.SettingsService(settings_dir=pathlib.Path(tmp) / "workbench" / "settings", log=lambda m: None)

def write_settings(d):
    (work / "settings.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")

def load_case(name, llm, expect_provider="custom_openai"):
    write_settings({"ui": {"llm_settings": llm}})
    before = (work / "settings.json").read_text(encoding="utf-8")
    got = svc.load_llm_settings()
    after = (work / "settings.json").read_text(encoding="utf-8")
    assert got["provider"] == expect_provider, f"{name}: provider={got['provider']}"
    assert before == after, f"{name}: settings.json was rewritten on load!"
    return got

# 1) provider=openai -> custom_openai, ключи файла целы
g = load_case("openai", {"provider": "openai", "openai_model": "gpt-5.5"})
assert g["openai_model"] == "gpt-5.5", "old key lost"
# 2) provider=ollama
g = load_case("ollama", {"provider": "ollama", "ollama_model": "qwen3:8b", "ollama_timeout_minutes": 5})
assert g["ollama_model"] == "qwen3:8b"
# 3) provider отсутствует
load_case("absent", {"custom_openai_profiles": []})
# 4) provider=неизвестная строка
load_case("unknown", {"provider": "mystery-llm"})
# 5) provider=пустая строка
load_case("empty", {"provider": ""})
# 6) legacy-плоский конфиг без схем -> профиль с http:// (loopback)
g = load_case("legacy-flat", {"provider": "openai", "custom_openai_endpoint": "127.0.0.1:3445/v1",
                              "custom_openai_model": "llama-local"})
prof = g["custom_openai_profiles"][0]
assert prof["endpoint"] == "http://127.0.0.1:3445/v1", prof
assert prof["model"] == "llama-local"
assert g["custom_openai_active_profile"] == "Custom Endpoint"
# 7) legacy-плоский с https://host — схема сохраняется
g = load_case("legacy-https", {"custom_openai_endpoint": "api.example.com/v1"})
assert g["custom_openai_profiles"][0]["endpoint"] == "https://api.example.com/v1", g["custom_openai_profiles"]
# 8) существующие профили не тронуты миграцией плоского
g = load_case("profiles-exist", {"provider": "claude",
    "custom_openai_profiles": [{"name": "P1", "endpoint": "http://x", "model": "m", "api_key": "k"}],
    "custom_openai_active_profile": "P1", "custom_openai_endpoint": "old-flat:1"})
assert len(g["custom_openai_profiles"]) == 1 and g["custom_openai_profiles"][0]["name"] == "P1"
assert g["custom_openai_endpoint"] == "old-flat:1", "flat key rewritten"

# 9) делегат монолита == сервис: таблица 15 кейсов 9.1b
cases = ["", "://", "//host/v1", "localhost:1234/v1", "127.0.0.1:3445/v1", "10.0.0.5/api",
         "192.168.1.10:8080", "172.16.0.9", "172.32.0.9", "[::1]:8080/v1", "::1",
         "mybox.local/v1", "api.example.com/v1", "HTTPS://API.EXAMPLE.COM/v1", "https://x.y/v1/"]
svc_norm = ss_mod.SettingsService.normalize_custom_endpoint
for c in cases:
    a = svc_norm(c)
    # монолит-делегат: тот же вызов через класс
    import Supervertaler
    b = Supervertaler.SupervertalerQt._normalize_custom_endpoint(c)
    assert a == b, f"{c!r}: {a!r} != {b!r}"
print("15/15 normalize cases agree (service == monolith delegate)")

# 10) provider_enabled_states: дефолты редуцированы, старые файлы читаются инертно
write_settings({"ui": {"provider_enabled_states": {"llm_openai": False, "mt_deepl": True}}})
st = svc.load_provider_enabled_states()
assert st["llm_custom_openai"] is True
assert st["llm_openai"] is False, "old key must stay inert-readable"
assert st["mt_deepl"] is True
write_settings({"ui": {}})
st2 = svc.load_provider_enabled_states()
assert set(st2.keys()) == {"llm_custom_openai"}, st2
print("provider_enabled_states OK (default = llm_custom_openai only; legacy keys inert)")
print("ALL 9.3a UNIT CHECKS PASSED")
