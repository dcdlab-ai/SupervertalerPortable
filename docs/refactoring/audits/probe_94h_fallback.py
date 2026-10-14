# -*- coding: utf-8 -*-
"""Batch 9.4h probe: popup fallback to GLOBAL ACTIVE profile when all QuickTrans
profiles are disabled (Dmitry's clarification 2026-10-13).

Scenarios (single app, settings rewritten between them):
  S1 enabled=[] (all unchecked)  -> chip = global active profile name, translation works
  S2 enabled=['Profile B']       -> chips = [Profile B] only (regression)
  S3 enabled absent              -> chips = both profiles (regression)
  S4 profiles=[] (all deleted)   -> legacy 'Custom' chip (regression)
Запуск: python probe_94h_fallback.py <tree-root> <iso-dir>
"""
import faulthandler, json, os, pathlib, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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

REQUESTS = []


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8", "replace")) if length else {}
        model = body.get("model", "")
        REQUESTS.append({"path": self.path, "auth": self.headers.get("Authorization", ""),
                         "model": model})
        resp = {
            "id": "chatcmpl-fake", "object": "chat.completion", "created": 1, "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Goedemorgen"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15},
        }
        data = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
PORT = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QLabel  # noqa: E402
from modules.quicktrans import MTQuickPopup  # noqa: E402

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

A = {"name": "Profile A", "endpoint": f"http://127.0.0.1:{PORT}/v1", "model": "fake-llm", "api_key": "prof-key-A"}
B = {"name": "Profile B", "endpoint": f"http://127.0.0.1:{PORT}/v1", "model": "fake-llm", "api_key": "prof-key-B"}

def write_settings(profiles, enabled, active="Profile A"):
    mtql = {"mtql_custom_openai": True, "mtql_popup_ai_autofetch": True}
    if enabled is not None:
        mtql["mtql_llm_profiles"] = enabled
    data = {
        "ui": {"llm_settings": {"provider": "custom_openai", "custom_openai_profiles": profiles,
                                "custom_openai_active_profile": active,
                                "custom_openai_model": "fake-llm",
                                "custom_openai_endpoint": f"http://127.0.0.1:{PORT}/v1"}},
        "general": {"mt_quick_lookup": mtql},
        "api_keys": {},
    }
    (sd / "settings.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

win = Supervertaler.SupervertalerQt()
say("WINDOW OK")
qt = win.quicktrans_panel

def chips():
    return [(n, c) for n, c, _ in qt._get_enabled_providers() if c == "CUS"]

def popup_row():
    REQUESTS.clear()
    popup = MTQuickPopup(parent_app=win, source_text="Good morning",
                         source_lang="English", target_lang="Dutch", parent=None)
    done = {"n": 0}
    popup.worker.all_complete.connect(lambda: done.__setitem__("n", 1))
    t0 = time.time()
    while done["n"] == 0 and time.time() - t0 < 60:
        app.processEvents()
        time.sleep(0.05)
    rows = [w.text()[:80] for w in popup.findChildren(QLabel)
            if w.text().startswith("[") or "Goedemorgen" in w.text()]
    return rows, list(REQUESTS)

# S1: all profiles unchecked -> fallback chip = global active 'Profile A', translation works
write_settings([A, B], [])
say("S1 chips:", chips())
rows, reqs = popup_row()
say("S1 rows:", rows)
say("S1 auth:", [r["auth"] for r in reqs])
say("S1 OK:", chips() == [("Profile A", "CUS")] and any("Goedemorgen" in r for r in rows)
    and any(r["auth"] == "Bearer prof-key-A" for r in reqs))

# S2: subset -> only Profile B chip (regression)
write_settings([A, B], ["Profile B"])
say("S2 chips:", chips())
say("S2 OK:", chips() == [("Profile B", "CUS")])

# S3: enabled absent -> all profiles with endpoint (regression)
write_settings([A, B], None)
say("S3 chips:", chips())
say("S3 OK:", chips() == [("Profile A", "CUS"), ("Profile B", "CUS")])

# S4: profiles list empty -> SettingsService auto-migrates the flat endpoint into
# a legacy profile 'Custom Endpoint' (pre-9.4h behavior); chip present, translation works
write_settings([], [])
say("S4 chips:", chips())
rows, reqs = popup_row()
say("S4 rows:", rows)
say("S4 OK:", len(chips()) == 1 and chips()[0][1] == "CUS"
    and chips()[0][0] in ("Custom", "Custom Endpoint") and any("Goedemorgen" in r for r in rows))

# S5: all unchecked + NO active profile name (active='Ghost') -> fallback resolves first profile
write_settings([A, B], [], active="Ghost")
say("S5 chips:", chips())
say("S5 OK:", chips() == [("Profile A", "CUS")])

say("PROBE DONE")
os._exit(0)
