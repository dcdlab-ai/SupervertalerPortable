# -*- coding: utf-8 -*-
"""Batch P1-B full-app probe: paths enumeration + settings/api_keys e2e + save
byte-stability (acceptance probes 1, 3, 6).

Runs the real app offscreen with the P1-B seam (SUPERVERTALER_DATA_ROOT=iso)
and USERPROFILE/APPDATA/... pointed at the isolated profile (negative control).

Checks:
  1. win.user_data_path == <iso>/Supervertaler;
  2. after build + save cycle + graceful close: EVERY created/changed path in
     the profile is under <iso>/Supervertaler (plus tmp/ noise); nothing in
     APPDATA/LOCALAPPDATA (no Supervertaler dir, no config.json);
  3. e2e: general settings and api_keys saved through the app's own save
     delegates are readable back and land in <iso>/Supervertaler/workbench/
     settings/settings.json;
  4. byte stability of the api_keys values across a save cycle.

Run: python batch-p1b_probe_app.py <tree-root> <iso-dir> <tag>
Writes <iso>/p1b_app_<tag>.json; prints P1B-APP-OK / P1B-APP-FAILED.
"""
import faulthandler
import hashlib
import json
import os
import pathlib
import sys
import time

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)

data_dir = iso / "Supervertaler"
settings_file = data_dir / "workbench" / "settings" / "settings.json"
SEED = {
    "api_keys": {"custom_openai": "sk-seed-1234567890"},
    "general": {"restore_last_project": False, "global_ui_font_scale": 125},
    "ui": {}, "features": {},
}
settings_file.parent.mkdir(parents=True, exist_ok=True)
if settings_file.exists():
    settings_file.unlink()
settings_file.write_text(json.dumps(SEED, indent=2, ensure_ascii=False), encoding="utf-8")


def tree_state(root: pathlib.Path):
    state = {}
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        if p.is_file():
            state[rel] = "F:" + hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        else:
            state[rel] = "D"
    return state


failures = []


def check(name, cond, detail=""):
    print(f"[{tag}] {name}: {'ok' if cond else 'FAIL'} {detail}", flush=True)
    if not cond:
        failures.append(name)


faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))
t0 = time.time()
state0 = tree_state(iso)
sha_seed = hashlib.sha256(settings_file.read_bytes()).hexdigest()

import Supervertaler as SV  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
print(f"[{tag}] window built ({time.time()-t0:.1f}s)", flush=True)

check("user_data_path == <iso>/Supervertaler",
      pathlib.Path(win.user_data_path).resolve() == data_dir, str(win.user_data_path))

for _ in range(120):
    app.processEvents()
    time.sleep(0.05)
print(f"[{tag}] event loop pumped 6s", flush=True)

# --- e2e: read back through the app's own loaders ---
gen = win.load_general_settings()
check("general read-back", gen.get("global_ui_font_scale") == 125, repr(gen.get("global_ui_font_scale")))

# --- emulate Settings -> Save through the same delegates the UI handlers use ---
gen_saved = dict(gen)
gen_saved["p1b_marker"] = "saved-by-probe"
win.save_general_settings(gen_saved)
win.save_api_keys({"custom_openai": "sk-seed-1234567890"})

on_disk = json.loads(settings_file.read_text(encoding="utf-8"))
check("general marker on disk",
      on_disk.get("general", {}).get("p1b_marker") == "saved-by-probe")
check("api key value byte-stable",
      on_disk.get("api_keys", {}).get("custom_openai") == "sk-seed-1234567890",
      repr(on_disk.get("api_keys")))
check("settings.json under data root",
      str(settings_file).startswith(str(data_dir)))

# --- graceful close ---
win._really_quit = True
win.close()
for _ in range(5):
    app.processEvents()
    time.sleep(0.1)

state1 = tree_state(iso)
created = sorted(set(state1) - set(state0))
changed = sorted(k for k in set(state1) & set(state0) if state1[k] != state0[k])

allowed_prefix = ("Supervertaler\\", "Supervertaler/", "tmp\\", "tmp/",
                  "Desktop\\", "Desktop/", "Documents\\", "Documents/", "Downloads\\", "Downloads/")
outside = [p for p in created + changed if not p.startswith(allowed_prefix)]
check("all new paths under <iso>/Supervertaler (or tmp/skeleton)",
      not outside, f"outside={outside}")
appdata_noise = [p for p in state1 if p.startswith("AppData")
                 and ("Supervertaler" in p or p.endswith("config.json"))]
check("APPDATA clean (no Supervertaler, no config.json)", not appdata_noise, str(appdata_noise))

out = {
    "tag": tag,
    "user_data_path": str(win.user_data_path),
    "created": created,
    "changed": changed,
    "sha_seed": sha_seed,
    "sha_final": hashlib.sha256(settings_file.read_bytes()).hexdigest(),
    "outside": outside,
    "appdata_noise": appdata_noise,
}
(iso / f"p1b_app_{tag}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

if failures:
    print(f"P1B-APP-FAILED: {failures}", flush=True)
    sys.stdout.flush()
    os._exit(1)
print("P1B-APP-OK", flush=True)
os._exit(0)
