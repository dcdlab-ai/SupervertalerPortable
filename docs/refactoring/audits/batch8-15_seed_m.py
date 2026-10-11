import json, pathlib, sys

iso = pathlib.Path(sys.argv[1])
val = sys.argv[2]  # "none" | "true" | "false"

for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
sd = iso / "Supervertaler" / "workbench" / "settings"
sd.mkdir(parents=True, exist_ok=True)
p = sd / "settings.json"

if val == "none":
    p.write_text(json.dumps({"ui": {}}, indent=2), encoding="utf-8")
else:
    p.write_text(json.dumps(
        {"ui": {"provider_enabled_states": {"mt_mymemory": val == "true"}}},
        indent=2), encoding="utf-8")
print("seeded", p, "with mt_mymemory:", val)
