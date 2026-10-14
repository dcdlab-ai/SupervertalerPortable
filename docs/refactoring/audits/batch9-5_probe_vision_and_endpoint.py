# -*- coding: utf-8 -*-
"""Batch 9.5 special probe: vision as a profile property + empty-endpoint guard.

Scenarios (single app; fake OpenAI-compatible endpoint on 127.0.0.1; network trap):
  V1  profile supports_vision=True + image -> request body contains image_url
      with data:image/png;base64 (client-level and figure-context level).
  V2  supports_vision=False/absent -> every gate (translate_current_segment,
      Image Extractor, figure-context, prompt manager) refuses with 0 image
      requests; messages intelligible.
  V3  two profiles with different flags: gates follow the profile actually
      used for the request (active and profile_name).
  V4  old settings.json without the key: load -> False, file not rewritten
      (hash before/after).
  V5  UI round-trip: tick, switch profile, back, Save, re-read -> flags
      persisted; 9.1 regression (add/remove/switch/dangling active) survives.
  V6  empty endpoint: empty and whitespace -> Save blocked, warning with the
      profile name (QMessageBox captured), settings.json unchanged (hash),
      dialog stays open, problem profile selected; valid profile saves;
      pre-existing empty profile loads and is NOT deleted; Custom MT save
      unchanged.
  V7  QuickTrans chips + 9.4i fallback (run probe_94i separately).
  V8  network trap never fired.
Запуск: python batch9-5_probe_vision_and_endpoint.py <tree-root> <iso-dir>
"""
import faulthandler, hashlib, importlib.abc, json, os, pathlib, socket, sys, threading
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

# ---------------- fake LLM server (records full bodies) ----------------
REQUESTS = []


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        try:
            body = json.loads(raw)
        except Exception:
            body = {"_raw": raw}
        model = body.get("model", "")
        REQUESTS.append({"path": self.path, "model": model, "body": body})
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

faulthandler.dump_traceback_later(240, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import (QApplication, QDialog, QMessageBox, QCheckBox,  # noqa: E402
                             QPushButton, QComboBox, QLineEdit, QFileDialog)
from PyQt6.QtCore import QTimer

app = QApplication(sys.argv)
# Accepted: import options dialog proceeds only on Accepted (as in regress_common)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Accepted
QDialog.exec_ = lambda self, *a, **k: QDialog.DialogCode.Accepted
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

MODAL_LOG = []  # (kind, title, text)


def _q(parent, title, text, *a, **k):
    MODAL_LOG.append(("question", str(title), str(text)))
    # Yes: remove-profile handler checks reply == Yes; Image Extractor gate
    # treats anything != Cancel as "proceed text-only".
    return QMessageBox.StandardButton.Yes


def _w(parent, title, text, *a, **k):
    MODAL_LOG.append(("warning", str(title), str(text)))
    return QMessageBox.StandardButton.Ok


def _i(parent, title, text, *a, **k):
    MODAL_LOG.append(("information", str(title), str(text)))
    return QMessageBox.StandardButton.Ok


QMessageBox.question = staticmethod(_q)
QMessageBox.warning = staticmethod(_w)
QMessageBox.information = staticmethod(_i)
Supervertaler.SuperlookupTab.register_global_hotkey = lambda self: None

RESULTS = iso / "results.txt"
_rfh = open(RESULTS, "w", encoding="utf-8", buffering=1)
PASS = []


def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    _rfh.write(msg + "\n")
    _rfh.flush()


def check(name, ok, detail=""):
    PASS.append((name, bool(ok)))
    say(("PASS" if ok else "FAIL"), name, detail)


EP = f"http://127.0.0.1:{PORT}/v1"


def prof(name, ep=EP, model="model-x", key="", vision=None):
    p = {"name": name, "endpoint": ep, "model": model, "api_key": key}
    if vision is not None:
        p["supports_vision"] = vision
    return p


def write_settings(profiles, active="Profile A", mtql=None, mt_profiles=None):
    llm = {"provider": "custom_openai", "custom_openai_profiles": profiles,
           "custom_openai_active_profile": active,
           "custom_openai_model": profiles[0].get("model", "") if profiles else "",
           "custom_openai_endpoint": profiles[0].get("endpoint", "") if profiles else ""}
    if mt_profiles is not None:
        llm["custom_mt_profiles"] = mt_profiles
        llm["custom_mt_active_profile"] = mt_profiles[0]["name"] if mt_profiles else ""
    data = {"ui": {"llm_settings": llm},
            "general": {"mt_quick_lookup": mtql or {"mtql_custom_openai": True},
                        # TM pre-check off: the first translate adds the segment
                        # to TM; the second call must still hit the API, not
                        # auto-insert the TM match.
                        "check_tm_before_api": False},
            "api_keys": {}}
    settings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sha_settings():
    return hashlib.sha256(settings_file.read_bytes()).hexdigest()[:16]


def image_requests():
    n = 0
    for r in REQUESTS:
        for msg in r["body"].get("messages", []):
            c = msg.get("content")
            if isinstance(c, list):
                for part in c:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        n += 1
    return n


def has_png_base64():
    for r in REQUESTS:
        for msg in r["body"].get("messages", []):
            c = msg.get("content")
            if isinstance(c, list):
                for part in c:
                    if (isinstance(part, dict) and part.get("type") == "image_url"
                            and str(part.get("image_url", {}).get("url", "")).startswith("data:image/png;base64,")):
                        return True
    return False


# Profiles: A vision=True, B vision=False, C no-key (absent), D empty endpoint
A = prof("Profile A", vision=True)
B = prof("Profile B", model="model-b", vision=False)
C = prof("Profile C", model="model-c")
D = prof("Profile D", ep="", model="model-d", vision=True)
write_settings([A, B, C, D], active="Profile B")

# Okapi sidecar imports `requests` for its 127.0.0.1 Java sidecar; the probe
# pumps the event loop (translate_current_segment), which would fire the
# sidecar's QTimer.singleShot(1500) and pollute the network trap. The sidecar
# is irrelevant to vision/endpoint scenarios -> disable it. Patch the CLASS
# method before construction: singleShot captures the bound method at
# scheduling time, so an instance-attribute patch after construction is too
# late (it only looked safe while pumping stayed under 1.5 s).
Supervertaler.SupervertalerQt._start_okapi_sidecar = lambda self: None
win = Supervertaler.SupervertalerQt()
say("WINDOW OK")

# ============ V3/V1 client-level: flag follows profile ============
llm = win.load_llm_settings()
cA = win.create_llm_client("custom_openai", None, {}, settings=llm, profile_name="Profile A")
cB = win.create_llm_client("custom_openai", None, {}, settings=llm)  # active = B
cC = win.create_llm_client("custom_openai", None, {}, settings=llm, profile_name="Profile C")
check("V3 flag follows profile_name (A=True)", cA.supports_vision is True, f"A={cA.supports_vision}")
check("V3 flag follows active (B=False)", cB.supports_vision is False, f"B={cB.supports_vision}")
check("V3 absent key -> False (C)", cC.supports_vision is False, f"C={cC.supports_vision}")

import base64
from modules.figure_context_manager import pil_image_to_base64_png
from PIL import Image

img = Image.new("RGB", (8, 6), (200, 30, 30))
b64 = pil_image_to_base64_png(img)

REQUESTS.clear()
cA.translate_with_usage("Good morning", images=[("Figure 1A", b64)])
check("V1 client vision=True -> image_url in body", image_requests() == 1 and has_png_base64(),
      f"img_req={image_requests()}")
check("V8 trap silent after V1", not TRAP_HITS, str(TRAP_HITS))

REQUESTS.clear()
cB.translate_with_usage("Good morning", images=[("Figure 1A", b64)])
check("V2 client vision=False -> 0 image requests", image_requests() == 0 and len(REQUESTS) == 1,
      f"img_req={image_requests()} reqs={len(REQUESTS)}")

# ============ V2 figure-context gate (translate_current_segment) ============
inputs = iso / "inputs"
inputs.mkdir(exist_ok=True)
(inputs / "fig.txt").write_text("See Figure 1A for details.\nPlain segment.\n", encoding="utf-8")
open_queue = [str(inputs / "fig.txt")]
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(open_queue), ""))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (open_queue.pop(0) if open_queue else "", ""))
win.import_simple_txt()
check("V2 project loaded", win.current_project is not None and len(win.current_project.segments) >= 2,
      f"segs={len(win.current_project.segments) if win.current_project else 0}")
# Map key = normalized figure ref (detect_figure_references returns '1a' for 'Figure 1A')
win.figure_context.figure_context_map["1a"] = img
win.table.selectRow(0); win.table.setCurrentCell(0, 0)
say("GRID DEBUG: rowCount=", win.table.rowCount(), "currentRow=", win.table.currentRow(),
    "segs=", len(win.current_project.segments))

# active = Profile B (vision False)
MODAL_LOG.clear()
REQUESTS.clear()
win.table.selectRow(0); win.table.setCurrentCell(0, 0)
win.translate_current_segment()
say("MODALS after translate(B):", MODAL_LOG)
fig_log = [m for m in MODAL_LOG if "vision" in m[2].lower() or "vision" in m[1].lower()]
check("V2 figure gate: 0 image requests", image_requests() == 0, f"img_req={image_requests()}")
check("V2 figure gate: text-only translation sent", len(REQUESTS) == 1, f"reqs={len(REQUESTS)}")

# active = Profile A (vision True) -> images ship
write_settings([A, B, C, D], active="Profile A")
win.table.selectRow(0); win.table.setCurrentCell(0, 0)
REQUESTS.clear()
win.translate_current_segment()
check("V1 figure gate vision=True -> image_url ships", image_requests() >= 1 and has_png_base64(),
      f"img_req={image_requests()}")

# ============ V2 Image Extractor gate ============
win.image_extractor_ai_label.setChecked(True)
# chat backend client follows active profile (A=True) -> refresh to B (False)
write_settings([A, B, C, D], active="Profile B")
pm = getattr(win, "prompt_manager_qt", None)
cb = getattr(pm, "chat_backend", None) if pm else None
if cb:
    cb.refresh_llm_client()
MODAL_LOG.clear()
REQUESTS.clear()
res = win._build_image_extract_ai_callback([])
ie_log = [m for m in MODAL_LOG if "vision" in m[2].lower() or "Settings" in m[2]]
check("V2 Image Extractor: refuses, 0 requests", res in (None, False) and image_requests() == 0,
      f"res={res} img_req={image_requests()}")
check("V2 Image Extractor: intelligible message mentions Settings/profile",
      any(("Settings" in m[2] and ("profile" in m[2].lower() or "vision" in m[2].lower())) for m in ie_log),
      str(ie_log[:1]))

# ============ V2 prompt manager gate ============
cb2 = getattr(pm, "chat_backend", None)
if cb2:
    cb2.refresh_llm_client()
pm._autoprompt_include_images.setChecked(True)
MODAL_LOG.clear()
REQUESTS.clear()
res2 = pm._collect_autoprompt_images("prompt")
pm_log = [m for m in MODAL_LOG if "vision" in m[2].lower()]
check("V2 prompt manager: refuses (None/sentinel), 0 requests",
      (res2 is None or res2 == {"images": [], "refs": []}) and image_requests() == 0,
      f"res={res2} img_req={image_requests()}")
check("V2 prompt manager: intelligible message mentions Settings/profile",
      any(("Settings" in m[2] and ("profile" in m[2].lower() or "vision" in m[2].lower())) for m in pm_log),
      str(pm_log[:1]))
pm._autoprompt_include_images.setChecked(False)

# ============ V4 old settings.json without key ============
old = [prof("Legacy", vision=None)]
write_settings(old, active="Legacy")
h_before = sha_settings()
llm4 = win.load_llm_settings()
c4 = win.create_llm_client("custom_openai", None, {}, settings=llm4)
h_after = sha_settings()
check("V4 load -> supports_vision False", c4.supports_vision is False, f"{c4.supports_vision}")
check("V4 file not rewritten on load", h_before == h_after, f"{h_before}=={h_after}")

# ============ V5 UI round-trip ============
write_settings([prof("Profile A", vision=False), prof("Profile B", model="model-b", vision=True)],
               active="Profile A")
tab = win._create_ai_settings_tab()
vcb = next((c for c in tab.findChildren(QCheckBox) if "supports vision" in c.text()), None)
combo = next((c for c in tab.findChildren(QComboBox) if c.count() >= 2), None)
ep_edit = next((e for e in tab.findChildren(QLineEdit) if "api.example.com" in (e.placeholderText() or "")), None)
check("V5 vision checkbox exists", vcb is not None)
check("V5 combo exists", combo is not None and ep_edit is not None)
if vcb and combo and ep_edit:
    combo.setCurrentIndex(0)
    check("V5 populate: A unchecked", vcb.isChecked() is False)
    vcb.setChecked(True)
    combo.setCurrentIndex(1)
    check("V5 populate: B checked (from file)", vcb.isChecked() is True)
    combo.setCurrentIndex(0)
    check("V5 populate: back to A checked (live)", vcb.isChecked() is True)
    h5 = sha_settings()
    save_btn = next((b for b in tab.findChildren(QPushButton) if "Save AI Settings" in b.text()), None)
    save_btn.click()
    st5 = json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]
    flags = {p["name"]: p.get("supports_vision") for p in st5["custom_openai_profiles"]}
    check("V5 Save persists flags (A=True,B=True)", flags == {"Profile A": True, "Profile B": True}, str(flags))
    # add profile -> unchecked by default
    add_btn = next((b for b in tab.findChildren(QPushButton) if b.text() == "+"), None)
    from PyQt6.QtWidgets import QInputDialog
    QInputDialog.getText = staticmethod(lambda *a, **k: ("Profile New", True))
    add_btn.click()
    idx_new = combo.findText("Profile New")
    combo.setCurrentIndex(idx_new)
    check("V5 new profile unchecked by default", vcb.isChecked() is False)
    # remove it
    rm_btn = next((b for b in tab.findChildren(QPushButton) if b.text() == "−"), None)
    rm_btn.click()
    check("V5 remove profile (dialog Yes via monkeypatch)", combo.findText("Profile New") == -1)
    # dangling active name survives save
    st5b = json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]
    check("V5 9.1-regression: profiles survive save",
          {p["name"] for p in st5b["custom_openai_profiles"]} == {"Profile A", "Profile B"},
          str([p["name"] for p in st5b["custom_openai_profiles"]]))

# ============ V6 empty endpoint guard ============
write_settings([prof("Profile A", vision=True), prof("Profile B", model="model-b", vision=False)],
               active="Profile A")
tab6 = win._create_ai_settings_tab()
combo6 = next((c for c in tab6.findChildren(QComboBox) if c.count() >= 2), None)
ep6 = next((e for e in tab6.findChildren(QLineEdit) if "api.example.com" in (e.placeholderText() or "")), None)
save6 = next((b for b in tab6.findChildren(QPushButton) if "Save AI Settings" in b.text()), None)

# empty endpoint on active profile
combo6.setCurrentIndex(0)
ep6.setText("")
ep6.editingFinished.emit()
h6 = sha_settings()
MODAL_LOG.clear()
save6.click()
st6 = json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]
check("V6 empty endpoint: Save blocked (file unchanged)", sha_settings() == h6,
      f"{sha_settings()} vs {h6}")
check("V6 empty endpoint: warning names the profile",
      any(m[0] == "warning" and "Profile A" in m[1] + m[2] for m in MODAL_LOG), str(MODAL_LOG[:2]))
check("V6 empty endpoint: problem profile selected", combo6.currentIndex() == 0)
check("V6 empty endpoint: profiles intact on disk",
      {p["name"] for p in st6["custom_openai_profiles"]} == {"Profile A", "Profile B"})

# whitespace-only endpoint
ep6.setText("   ")
ep6.editingFinished.emit()
h6w = sha_settings()
MODAL_LOG.clear()
save6.click()
check("V6 whitespace endpoint: Save blocked", sha_settings() == h6w)
check("V6 whitespace endpoint: warning names the profile",
      any(m[0] == "warning" and "Profile A" in m[1] + m[2] for m in MODAL_LOG), str(MODAL_LOG[:2]))

# non-active profile with empty endpoint (D) -> blocked too
write_settings([prof("Profile A", vision=True), prof("Profile D", ep="", vision=True)], active="Profile A")
tab6b = win._create_ai_settings_tab()
combo6b = next((c for c in tab6b.findChildren(QComboBox) if c.count() >= 2), None)
save6b = next((b for b in tab6b.findChildren(QPushButton) if "Save AI Settings" in b.text()), None)
combo6b.setCurrentIndex(0)
h6b = sha_settings()
MODAL_LOG.clear()
save6b.click()
check("V6 non-active empty profile: Save blocked", sha_settings() == h6b)
check("V6 non-active empty profile: warning names Profile D",
      any(m[0] == "warning" and "Profile D" in m[1] + m[2] for m in MODAL_LOG), str(MODAL_LOG[:2]))
check("V6 non-active empty profile: selected in combo", combo6b.currentIndex() == 1)

# fill valid endpoint -> Save passes
ep6b = next((e for e in tab6b.findChildren(QLineEdit) if "api.example.com" in (e.placeholderText() or "")), None)
combo6b.setCurrentIndex(1)
ep6b.setText("127.0.0.1:3445/v1")
ep6b.editingFinished.emit()
MODAL_LOG.clear()
save6b.click()
st6b = json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]
saved_d = next(p for p in st6b["custom_openai_profiles"] if p["name"] == "Profile D")
check("V6 valid endpoint: Save passes", saved_d["endpoint"] == "http://127.0.0.1:3445/v1",
      saved_d["endpoint"])
check("V6 valid endpoint: no warning", not any(m[0] == "warning" for m in MODAL_LOG), str(MODAL_LOG[:2]))

# pre-existing empty profile on disk loads and is NOT deleted
write_settings([prof("Profile A", vision=True), prof("Profile E", ep="", vision=False)], active="Profile A")
llm6 = win.load_llm_settings()
check("V6 pre-existing empty profile loads, not deleted",
      any(p["name"] == "Profile E" for p in llm6["custom_openai_profiles"]))

# ============ V6 (Q3): delete ALL profiles -> Save succeeds ============
# Zero profiles is a legal state: the guard validates only profiles that are
# in the list. Save must succeed, mirrors clear, status bar says
# "Custom profile not configured", and a fresh window (restart) reads the
# file without errors.
write_settings([prof("Profile A", vision=True), prof("Profile B", model="model-b")], active="Profile A")
tab6c = win._create_ai_settings_tab()
combo6c = next((c for c in tab6c.findChildren(QComboBox) if c.count() >= 2), None)
save6c = next((b for b in tab6c.findChildren(QPushButton) if "Save AI Settings" in b.text()), None)
rm6c = next((b for b in tab6c.findChildren(QPushButton) if b.text() == "−"), None)
MODAL_LOG.clear()
combo6c.setCurrentIndex(0); rm6c.click()
combo6c.setCurrentIndex(0); rm6c.click()
check("V6 Q3: all profiles removed from combo", combo6c.count() == 0, str(combo6c.count()))
save6c.click()
st6c = json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]
check("V6 Q3: Save with zero profiles succeeds (no warning)",
      st6c["custom_openai_profiles"] == [] and not any(m[0] == "warning" for m in MODAL_LOG),
      str(MODAL_LOG[:2]))
check("V6 Q3: mirrors cleared",
      st6c.get("custom_openai_endpoint", "") == "" and st6c.get("custom_openai_active_profile", "") == "",
      str(st6c.get("custom_openai_endpoint")))
check("V6 Q3: status bar shows not configured",
      "not configured" in win.llm_indicator_label.text(), win.llm_indicator_label.text())
win2 = Supervertaler.SupervertalerQt()
llm2 = win2.load_llm_settings()
check("V6 Q3: restart builds and reads zero profiles", llm2["custom_openai_profiles"] == [],
      str(llm2["custom_openai_profiles"]))
check("V6 Q3: restart status bar not configured",
      "not configured" in win2.llm_indicator_label.text(), win2.llm_indicator_label.text())
win2.close()

# Custom MT save unchanged (no endpoint validation there)
mt = [{"name": "MT1", "endpoint": "", "model": "mt-m", "api_key": "", "raw_mode": False, "enabled": True}]
write_settings([prof("Profile A", vision=True)], active="Profile A", mt_profiles=mt)
tab_mt = win._create_mt_quick_lookup_settings_tab()
save_mt = next((b for b in tab_mt.findChildren(QPushButton) if "Save QuickTrans" in b.text()), None)
MODAL_LOG.clear()
save_mt.click()
st_mt = json.loads(settings_file.read_text(encoding="utf-8"))["ui"]["llm_settings"]
check("V6 Custom MT save unchanged (empty MT endpoint allowed)",
      any(p["name"] == "MT1" for p in st_mt.get("custom_mt_profiles", []))
      and not any(m[0] == "warning" and "MT1" in m[1] + m[2] for m in MODAL_LOG),
      str(st_mt.get("custom_mt_profiles")))

# ============ V8 trap ============
check("V8 network trap never fired", not TRAP_HITS, str(TRAP_HITS))

fails = [n for n, ok in PASS if not ok]
say("TOTAL", len(PASS), "FAILS", len(fails), fails)
say("PROBE DONE")
os._exit(0)
