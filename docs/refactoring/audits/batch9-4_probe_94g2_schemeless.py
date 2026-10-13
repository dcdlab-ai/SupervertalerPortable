# -*- coding: utf-8 -*-
"""Batch 9.4g probe: QuickTrans POPUP path with Custom (OpenAI-Compatible) chip.

Reproduces Dmitry's T9.4.6 observation: popup shows CUS chip but no translation.
Builds MTQuickPopup(parent_app=win) with a seeded Custom profile pointing at a
loopback fake server, autofetch ON, and captures the CUS row result text.

Checks:
  chips  — popup provider list contains CUS chip(s)
  result — CUS row shows translation (not [Error: ...])
  server — fake endpoint received the request (path/auth/model)
Запуск: python probe_94g_popup.py <tree-root> <iso-dir>
"""
import faulthandler, json, os, pathlib, sys, threading, re
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

# ---------- fake server ----------
REQUESTS = []


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8", "replace")) if length else {}
        model = body.get("model", "")
        messages = body.get("messages", [])
        user_content = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                user_content = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                break
        REQUESTS.append({
            "path": self.path,
            "auth": self.headers.get("Authorization", ""),
            "model": model,
            "n_messages": len(messages),
            "head": user_content[:80].replace("\n", "\\n"),
        })
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

A = {"name": "Profile A", "endpoint": f"127.0.0.1:{PORT}/v1", "model": "fake-llm", "api_key": "prof-key-123"}
data = {
    "ui": {
        "llm_settings": {"provider": "custom_openai", "custom_openai_profiles": [A],
                         "custom_openai_active_profile": "Profile A",
                         "custom_openai_model": "fake-llm",
                         "custom_openai_endpoint": f"http://127.0.0.1:{PORT}/v1"},
    },
    "general": {"mt_quick_lookup": {"mtql_custom_openai": True, "mtql_popup_ai_autofetch": True}},
    "api_keys": {},
}
(sd / "settings.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402
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

win = Supervertaler.SupervertalerQt()
say("WINDOW OK")

# 1) mixin chain directly (same code the popup uses)
qt = getattr(win, "quicktrans_panel", None)
provs = qt._get_enabled_providers()
say("MIXIN PROVIDERS:", [(n, c) for n, c, _ in provs])

# 2) direct call through the popup's call function
cus = [p for p in provs if p[1] == "CUS"]
if cus:
    out = cus[0][2]("Goedemorgen", "English", "Dutch")
    say("DIRECT CUS CALL:", repr(out[:120]))
    say("SERVER SEEN:", len(REQUESTS), json.dumps(REQUESTS[-1] if REQUESTS else {}, ensure_ascii=False))

# 3) full popup: MTQuickPopup(parent_app=win) with autofetch
popup = MTQuickPopup(parent_app=win, source_text="Good morning",
                     source_lang="English", target_lang="Dutch", parent=None)
say("POPUP CREATED")

done = {"n": 0}
def on_all():
    done["n"] += 1
popup.worker.all_complete.connect(on_all)
import time
t0 = time.time()
while done["n"] == 0 and time.time() - t0 < 60:
    app.processEvents()
    time.sleep(0.05)
say("POPUP WORKER DONE:", done["n"] > 0)

rows = []
from PyQt6.QtWidgets import QLabel, QFrame  # noqa: E402
for w in popup.findChildren(QLabel):
    t = w.text()
    if t.startswith("[") or "Goedemorgen" in t:
        rows.append(t[:120])
say("POPUP RESULT ROWS:", rows)
say("SERVER TOTAL:", len(REQUESTS))
say("PROBE DONE")
os._exit(0)
