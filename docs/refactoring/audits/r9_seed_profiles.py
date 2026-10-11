# -*- coding: utf-8 -*-
"""Сидирование settings.json для сценариев R9 (iso-профиль)."""
import json, pathlib, sys

iso = pathlib.Path(sys.argv[1])
scenario = sys.argv[2]

sd = iso / "Supervertaler" / "workbench" / "settings"
sd.mkdir(parents=True, exist_ok=True)

CE = {"name": "Custom Endpoint", "endpoint": "http://127.0.0.1:8888/v1",
      "model": "Qwen3.8-27B-GGUF:UD-IQ2_XXS", "api_key": "sk-seed-TEST"}
A = {"name": "Profile A", "endpoint": "http://127.0.0.1:1111/v1", "model": "model-a", "api_key": ""}
B = {"name": "Profile B", "endpoint": "http://127.0.0.1:2222/v1", "model": "model-b", "api_key": ""}

base = {"provider": "custom_openai", "custom_openai_model": "test",
        "custom_openai_endpoint": "127.0.0.1:3445/v1",
        "custom_mt_profiles": [], "custom_mt_active_profile": ""}

if scenario == "a":
    base.update({"custom_openai_profiles": [CE], "custom_openai_active_profile": ""})
elif scenario == "ctrl":
    base.update({"custom_openai_profiles": [A, B], "custom_openai_active_profile": "Profile A"})
elif scenario == "rm":
    base.update({"custom_openai_profiles": [A, B], "custom_openai_active_profile": "Profile A"})

(sd / "settings.json").write_text(
    json.dumps({"ui": {"llm_settings": base}}, indent=2, ensure_ascii=False), encoding="utf-8")
print("seeded", sd / "settings.json", "scenario", scenario)
