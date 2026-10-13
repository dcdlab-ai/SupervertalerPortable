# -*- coding: utf-8 -*-
"""Seed settings.json for the 9.4a save probe (foreign keys + 2 profiles)."""
import json, pathlib, sys

iso = pathlib.Path(sys.argv[1])
sd = iso / "Supervertaler" / "workbench" / "settings"
sd.mkdir(parents=True, exist_ok=True)

A = {"name": "Profile A", "endpoint": "http://127.0.0.1:1111/v1", "model": "model-a", "api_key": ""}
B = {"name": "Profile B", "endpoint": "http://127.0.0.1:2222/v1", "model": "model-b", "api_key": "sk-B"}
MT = {"name": "Local proxy", "endpoint": "http://127.0.0.1:1234/v1", "model": "google", "api_key": "", "raw_mode": True, "enabled": True}

data = {
    "ui": {
        "llm_settings": {
            "provider": "custom_openai",
            "custom_openai_profiles": [A, B],
            "custom_openai_active_profile": "Profile B",
            "custom_openai_model": "model-b",
            "custom_openai_endpoint": "http://127.0.0.1:2222/v1",
            "custom_mt_profiles": [MT],
            "custom_mt_active_profile": "Local proxy",
            "openai_model": "gpt-5.5",
            "claude_model": "claude-sonnet-5-5",
            "ollama_model": "translategemma:12b",
            "ollama_timeout_minutes": 7,
        },
        "provider_enabled_states": {
            "llm_openai": False, "llm_claude": True, "llm_ollama": False,
            "llm_custom_openai": False,
            "mt_google": True, "mt_deepl": False,
        },
        "general_settings": {
            "batch_size": 21,
            "enable_llm_matching": True,
            "ollama_keepwarm": True,
            "mt_quick_lookup": {"mtql_custom_openai": True, "mtql_google": True},
            "match_limits": {"LLM": 3, "MT": 3, "TM": 5, "Termbases": 10},
        },
    },
    "api_keys": {"openai": "sk-old-openai", "gemini": "AIza-old"},
}
(sd / "settings.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print("seeded", sd / "settings.json")
