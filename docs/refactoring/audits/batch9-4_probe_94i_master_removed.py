# -*- coding: utf-8 -*-
"""Batch 9.4i probe: QuickTrans master checkbox 'Custom (OpenAI-Compatible)' removed.

Dmitry's decision 2026-10-14: no master checkbox in the QuickTrans tab; LLM chips
are always present; profile checkboxes select chips; empty selection -> global
active profile chip (9.4h); nothing configured -> no chips, no errors; the legacy
key mtql_custom_openai in settings.json is inert (not read, not written, not erased).

Scenarios (single app, settings rewritten between them; fake endpoint on 127.0.0.1):
  T1 tab   — master checkbox absent; Auto-fetch + profile checkboxes present;
             read-only model field absent; _mtql_checkboxes has no mtql_custom_openai;
             Save does NOT write mtql_custom_openai and does NOT erase it from file;
             foreign mt_quick_lookup keys intact.
  T2 chips — A,B on -> two chips; B only -> one; all off -> active-profile chip +
             translation with THAT profile's Bearer key; profiles deleted + flat
             endpoint -> 'Custom Endpoint' chip; nothing configured -> no chips,
             no errors; dangling active name -> first profile with endpoint.
  T3 old   — mtql_custom_openai false / true / absent give IDENTICAL results.
  T4 trap  — network trap (requests/anthropic/google.generativeai/ollama imports +
             non-loopback socket) never fires.
  T5 shot  — Dmitry's screenshot scenario: old settings.json with the master key
             present and false, profile 'strata' unchecked -> popup shows the global
             active profile chip and translates.
Запуск: python probe_94i_master_removed.py <tree-root> <iso-dir>
"""
import faulthandler, importlib.abc, importlib.machinery, json, os, pathlib, socket, sys, threading, time
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
settings_file = sd / "settings.json"

# ---------------- network trap ----------------
TRAP_MODULES = ("requests", "anthropic", "google.generativeai", "ollama")
TRAP_HITS = []


class TrapFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in TRAP_MODULES:
            TRAP_HITS.append(fullname)
        return None


sys.meta_path.insert(0, TrapFinder())

_real_connect = socket.socket.connect


def _guarded_connect(self, address, *a, **k):
    try:
        host = address[0] if isinstance(address, tuple) and address else ""
        if isinstance(host, str) and host not in ("127.0.0.1", "localhost", "::1", ""):
            TRAP_HITS.append("socket:" + host)
    except Exception:
        pass
    return _real_connect(self, address, *a, **k)


socket.socket.connect = _guarded_connect

# ---------------- fake LLM server ----------------
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

faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import (QApplication, QDialog, QMessageBox, QGroupBox, QCheckBox,  # noqa: E402
                             QPushButton, QLineEdit)

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
Supervertaler.SuperlookupTab.register_global_hotkey = lambda self: None

RESULTS = iso / "results.txt"
_rfh = open(RESULTS, "w", encoding="utf-8", buffering=1)


def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    _rfh.write(msg + "\n")
    _rfh.flush()


EP = f"http://127.0.0.1:{PORT}/v1"
A = {"name": "Profile A", "endpoint": EP, "model": "model-a", "api_key": "prof-key-A"}
B = {"name": "Profile B", "endpoint": EP, "model": "model-b", "api_key": "prof-key-B"}
C = {"name": "Profile C", "endpoint": "", "model": "model-c", "api_key": ""}


def write_settings(profiles, enabled, active="Profile A", mtql_extra=None, flat=True):
    mtql = {"mtql_popup_ai_autofetch": True, "mtql_custom_mt": False,
            "mtql_google": True, "mtql_bing": False}
    if enabled is not None:
        mtql["mtql_llm_profiles"] = enabled
    if mtql_extra:
        mtql.update(mtql_extra)
    llm = {"provider": "custom_openai", "custom_openai_profiles": profiles,
           "custom_openai_active_profile": active}
    if flat:
        llm["custom_openai_model"] = "model-a"
        llm["custom_openai_endpoint"] = EP
    data = {"ui": {"llm_settings": llm}, "general": {"mt_quick_lookup": mtql}, "api_keys": {}}
    settings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


# Harness: deferred Okapi sidecar timer (QTimer.singleShot(1500), scheduled in
# _init_okapi_sidecar_deferred) imports modules.okapi_sidecar -> `import
# requests` (loopback-only, for the Java sidecar). If event pumping crosses
# 1.5 s the import fires and the network trap records it. Patch the CLASS
# method before construction: singleShot captures the bound method at
# scheduling time, so an instance-attribute patch after construction is too
# late.
Supervertaler.SupervertalerQt._start_okapi_sidecar = lambda self: None
win = Supervertaler.SupervertalerQt()
say("WINDOW OK")
qt = win.quicktrans_panel
from modules.quicktrans import MTQuickPopup  # noqa: E402


def chips():
    return [(n, c) for n, c, _ in qt._get_enabled_providers() if c == "CUS"]


def popup_row():
    REQUESTS.clear()
    popup = MTQuickPopup(parent_app=win, source_text="Good morning",
                         source_lang="English", target_lang="Dutch", parent=None)
    if getattr(popup, "worker", None) is None:
        # No providers configured: popup shows politely, no worker, no requests.
        return [], []
    done = {"n": 0}
    popup.worker.all_complete.connect(lambda: done.__setitem__("n", 1))
    t0 = time.time()
    while done["n"] == 0 and time.time() - t0 < 60:
        app.processEvents()
        time.sleep(0.05)
    rows = [w.text()[:80] for w in popup.findChildren(QLabel)
            if w.text().startswith("[") or "Goedemorgen" in w.text()]
    return rows, list(REQUESTS)


from PyQt6.QtWidgets import QLabel  # noqa: E402

# ---------------- T1: tab ----------------
write_settings([A, B, C], None)
tab = win._create_mt_quick_lookup_settings_tab()
groups = {g.title(): g for g in tab.findChildren(QGroupBox)}
llm_g = next((g for t, g in groups.items() if "AI/LLM Providers" in t), None)
cb_texts = [c.text() for c in llm_g.findChildren(QCheckBox)]
say("T1 CHECKBOXES:", cb_texts)
say("T1 MASTER ABSENT:", not any("Custom (OpenAI-Compatible)" in t for t in cb_texts))
say("T1 AUTOFETCH PRESENT:", any("Auto-fetch" in t for t in cb_texts))
say("T1 PROFILE CBS:", sorted(win._mtql_llm_profile_cbs))
say("T1 KEYS:", sorted(k for k in win._mtql_checkboxes))
say("T1 NO MASTER KEY:", "mtql_custom_openai" not in win._mtql_checkboxes)
say("T1 COMBOS:", sorted(win._mtql_llm_combos))
edits = [w for w in llm_g.findChildren(QLineEdit)]
say("T1 NO READONLY FIELD:", all(not w.isReadOnly() for w in edits), "edits=", len(edits))

# Save: master key present in file, false -> must stay false, not written anew
write_settings([A, B, C], None, mtql_extra={"mtql_custom_openai": False,
                                            "mtql_custom_openai_model": "legacy-model"})
before = json.loads(settings_file.read_text(encoding="utf-8"))
win._mtql_llm_profile_cbs["Profile C"].setChecked(False)
save_btn = next((b for b in tab.findChildren(QPushButton) if "Save QuickTrans" in b.text()), None)
save_btn.click()
after = json.loads(settings_file.read_text(encoding="utf-8"))
st_a = after["general"]["mt_quick_lookup"]
st_b = before["general"]["mt_quick_lookup"]
say("T1 SAVED:", st_a.get("mtql_llm_profiles"))
say("T1 MASTER UNCHANGED:", st_a.get("mtql_custom_openai") is False,
    "MODEL UNCHANGED:", st_a.get("mtql_custom_openai_model") == "legacy-model")
# Registry-backed keys (owned by tab widgets) must survive Save unchanged.
# mtql_google/mtql_bing have no widget in the tab — Save rebuilds the section
# from widgets only (pre-9.4i design), they are not 9.4i's concern.
foreign = {k: st_b[k] for k in ("mtql_custom_mt", "mtql_popup_ai_autofetch")}
say("T1 FOREIGN INTACT:", all(st_a.get(k) == v for k, v in foreign.items()))
say("T1 OK:", (not any("Custom (OpenAI-Compatible)" in t for t in cb_texts))
    and "mtql_custom_openai" not in win._mtql_checkboxes
    and st_a.get("mtql_llm_profiles") == ["Profile A", "Profile B"]
    and st_a.get("mtql_custom_openai") is False
    and st_a.get("mtql_custom_openai_model") == "legacy-model"
    and all(st_a.get(k) == v for k, v in foreign.items()))

# ---------------- T2: chips ----------------
write_settings([A, B], ["Profile A", "Profile B"])
say("T2 both:", chips())
say("T2 OK both:", chips() == [("Profile A", "CUS"), ("Profile B", "CUS")])

write_settings([A, B], ["Profile B"])
say("T2 subset:", chips())
say("T2 OK subset:", chips() == [("Profile B", "CUS")])

write_settings([A, B], [])
say("T2 all-off:", chips())
rows, reqs = popup_row()
say("T2 all-off rows:", rows, "auth:", [r["auth"] for r in reqs])
say("T2 OK all-off:", chips() == [("Profile A", "CUS")] and any("Goedemorgen" in r for r in rows)
    and any(r["auth"] == "Bearer prof-key-A" for r in reqs))

write_settings([A, B], ["Ghost"])
say("T2 stale-list:", chips())
say("T2 OK stale:", chips() == [("Profile A", "CUS")])

write_settings([A, B], [], active="Ghost")
say("T2 dangling-active:", chips())
say("T2 OK dangling:", chips() == [("Profile A", "CUS")])

write_settings([C, B], None)
say("T2 empty-endpoint-skipped:", chips())
say("T2 OK empty-endpoint:", chips() == [("Profile B", "CUS")])

# profiles deleted, flat endpoint present -> SettingsService migrates to 'Custom Endpoint'
write_settings([], [])
say("T2 legacy-flat:", chips())
rows, reqs = popup_row()
say("T2 legacy-flat rows:", rows)
say("T2 OK legacy-flat:", len(chips()) == 1 and chips()[0][1] == "CUS"
    and chips()[0][0] in ("Custom", "Custom Endpoint") and any("Goedemorgen" in r for r in rows))

# nothing configured at all -> no chips, no errors
write_settings([], [], flat=False)
say("T2 nothing:", chips())
rows, reqs = popup_row()
say("T2 nothing rows:", rows)
say("T2 OK nothing:", chips() == [] and not any("Traceback" in r for r in rows))

# ---------------- T3: old master key values identical ----------------
results = []
for val in (False, True, None):
    extra = {} if val is None else {"mtql_custom_openai": val}
    write_settings([A, B], ["Profile A"], mtql_extra=extra)
    results.append(chips())
say("T3 chips per master value:", results)
say("T3 OK:", results[0] == results[1] == results[2] == [("Profile A", "CUS")])

# ---------------- T5: Dmitry's screenshot scenario ----------------
# Old settings.json: master key present + false, profile 'strata' unchecked,
# global active profile 'strata' configured in AI Settings.
S = {"name": "strata", "endpoint": EP, "model": "swift-1.5-iq3_xxs", "api_key": "prof-key-strata"}
write_settings([S], [], active="strata", mtql_extra={"mtql_custom_openai": False})
say("T5 chips:", chips())
rows, reqs = popup_row()
say("T5 rows:", rows, "auth:", [r["auth"] for r in reqs])
say("T5 OK:", chips() == [("strata", "CUS")] and any("Goedemorgen" in r for r in rows)
    and any(r["auth"] == "Bearer prof-key-strata" for r in reqs))

# ---------------- T4: trap ----------------
say("T4 TRAP HITS:", TRAP_HITS)
say("T4 OK:", TRAP_HITS == [])

say("PROBE DONE")
os._exit(0)
