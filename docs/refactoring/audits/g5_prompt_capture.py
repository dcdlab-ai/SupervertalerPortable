# -*- coding: utf-8 -*-
"""G5 audit (READ-ONLY): capture the EXACT request body for a figure-context
segment, with-image vs without-image, via a fake OpenAI-compatible endpoint on
127.0.0.1 + network trap. Records raw UTF-8 bytes + parsed JSON (base64
truncated). Verifies emoji/non-ASCII arrive as correct UTF-8 bytes.

Scenarios:
  G1  supports_vision=True + figure ref + loaded image -> body has image_url;
      text part captured verbatim; figure-context block in text shown.
  G2  supports_vision=False + same segment -> 0 image parts; text part captured.
  G3  text part with-image vs without-image: identical? (figure role NOT in text)
  G4  emoji + non-ASCII in segment arrive as correct UTF-8 bytes (no '?').
  G5  network trap silent.
Run: python g5_prompt_capture.py <tree-root> <iso-dir>
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

# ---------------- fake LLM server (records raw bytes + parsed body) ----------------
REQUESTS = []  # each: {"raw": bytes, "body": dict, "path": str}


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {"_raw": raw.decode("utf-8", "replace")}
        REQUESTS.append({"raw": raw, "body": body, "path": self.path})
        model = body.get("model", "") if isinstance(body, dict) else ""
        resp = {
            "id": "chatcmpl-fake", "object": "chat.completion", "created": 1, "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Vertaling"},
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

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Accepted
QDialog.exec_ = lambda self, *a, **k: QDialog.DialogCode.Accepted
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
Supervertaler.SupervertalerQt._start_okapi_sidecar = lambda self: None
Supervertaler.SuperlookupTab.register_global_hotkey = lambda self: None

RESULTS = iso / "results.txt"
_rfh = open(RESULTS, "w", encoding="utf-8", buffering=1)


def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    _rfh.write(msg + "\n")
    _rfh.flush()


def check(name, ok, detail=""):
    say(("PASS" if ok else "FAIL"), name, detail)


EP = f"http://127.0.0.1:{PORT}/v1"


def prof(name, ep=EP, model="model-x", key="", vision=None):
    p = {"name": name, "endpoint": ep, "model": model, "api_key": key}
    if vision is not None:
        p["supports_vision"] = vision
    return p


def write_settings(profiles, active="Profile A"):
    llm = {"provider": "custom_openai", "custom_openai_profiles": profiles,
           "custom_openai_active_profile": active,
           "custom_openai_model": profiles[0].get("model", "") if profiles else "",
           "custom_openai_endpoint": profiles[0].get("endpoint", "") if profiles else ""}
    data = {"ui": {"llm_settings": llm},
            "general": {"mt_quick_lookup": {"mtql_custom_openai": True},
                        "check_tm_before_api": False},
            "api_keys": {}}
    settings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def text_parts(body):
    out = []
    for msg in body.get("messages", []):
        c = msg.get("content")
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "text":
                    out.append(part.get("text", ""))
        elif isinstance(c, str):
            out.append(c)
    return out


def image_parts(body):
    n = 0
    for msg in body.get("messages", []):
        c = msg.get("content")
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    n += 1
    return n


def truncate_b64(body):
    """Return a copy of body with base64 payloads shortened for logging."""
    b = json.loads(json.dumps(body))
    for msg in b.get("messages", []):
        c = msg.get("content")
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    u = part.get("image_url", {}).get("url", "")
                    if len(u) > 80:
                        part["image_url"]["url"] = u[:60] + f"...<+{len(u)-60} chars>"
    return b


# Segment with figure ref + emoji + non-ASCII (UTF-8 probe)
SEG = "See Figure 1A — café ☕ «привет» 🖼️ gear engages"
inputs = iso / "inputs"
inputs.mkdir(exist_ok=True)
(inputs / "fig.txt").write_text(SEG + "\nPlain segment.\n", encoding="utf-8")
open_queue = [str(inputs / "fig.txt")]
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(open_queue), ""))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (open_queue.pop(0) if open_queue else "", ""))

A = prof("Profile A", vision=True)
B = prof("Profile B", model="model-b", vision=False)
write_settings([A, B], active="Profile A")

win = Supervertaler.SupervertalerQt()
say("WINDOW OK")

win.import_simple_txt()
say("segs=", len(win.current_project.segments) if win.current_project else 0)

# Load the REAL fixture image as figure ref '1a'
from PIL import Image
from modules.figure_context_manager import pil_image_to_base64_png
fixture = tree / "docs" / "refactoring" / "samples" / "Figure 1A.png"
img = Image.open(str(fixture))
win.figure_context.figure_context_map["1a"] = img
say("fixture loaded:", fixture.name, img.size)

# ---- G1: vision=True, with image ----
write_settings([A, B], active="Profile A")
win.table.selectRow(0); win.table.setCurrentCell(0, 0)
REQUESTS.clear()
win.translate_current_segment()
say("G1 requests:", len(REQUESTS), "image_parts:", image_parts(REQUESTS[0]["body"]) if REQUESTS else 0)
check("G1 vision=True -> 1 request with image_url",
      len(REQUESTS) == 1 and image_parts(REQUESTS[0]["body"]) == 1,
      f"reqs={len(REQUESTS)} img={image_parts(REQUESTS[0]['body']) if REQUESTS else 0}")
with_img_text = "\n".join(text_parts(REQUESTS[0]["body"])) if REQUESTS else ""
with_img_body = truncate_b64(REQUESTS[0]["body"]) if REQUESTS else {}
with_img_raw = REQUESTS[0]["raw"] if REQUESTS else b""

# ---- G2: vision=False, same segment ----
write_settings([A, B], active="Profile B")
win.table.selectRow(0); win.table.setCurrentCell(0, 0)
REQUESTS.clear()
win.translate_current_segment()
say("G2 requests:", len(REQUESTS), "image_parts:", image_parts(REQUESTS[0]["body"]) if REQUESTS else 0)
check("G2 vision=False -> 1 request, 0 image parts",
      len(REQUESTS) == 1 and image_parts(REQUESTS[0]["body"]) == 0,
      f"reqs={len(REQUESTS)} img={image_parts(REQUESTS[0]['body']) if REQUESTS else 0}")
without_text = "\n".join(text_parts(REQUESTS[0]["body"])) if REQUESTS else ""
without_body = truncate_b64(REQUESTS[0]["body"]) if REQUESTS else {}

# ---- G3: text part identical? ----
check("G3 text part identical with/without image (figure role NOT in text)",
      with_img_text == without_text,
      f"len_with={len(with_img_text)} len_without={len(without_text)}")

# ---- G4: emoji/non-ASCII arrive as correct UTF-8 bytes ----
say("=== G4 raw-bytes UTF-8 check (with-image request) ===")
say("raw bytes len:", len(with_img_raw))
# emoji/non-ASCII expected byte sequences
checks = {
    "café (é U+00E9)": b"\xc3\xa9",
    "☕ U+2615": b"\xe2\x98\x95",
    "« U+00AB": b"\xc2\xab",
    "» U+00BB": b"\xc2\xbb",
    "привет (U+043F)": b"\xd0\xbf",
    "🖼 U+1F5BC": b"\xf0\x9f\x96\xbc",
}
for label, seq in checks.items():
    present = seq in with_img_raw
    say(f"  {'OK ' if present else 'MISS'} {label}: {seq.hex()} in raw = {present}")
# count '?' in the text part (loss indicator)
q_in_text = with_img_text.count("?")
say("  '?' count in text part:", q_in_text, "(0 = no loss)")
check("G4 all emoji/non-ASCII present as UTF-8 bytes",
      all(seq in with_img_raw for seq in checks.values()),
      "see per-seq lines")
check("G4 no '?' substitution in text part", q_in_text == 0, f"q={q_in_text}")

# ---- G5: trap silent ----
check("G5 network trap silent", not TRAP_HITS, str(TRAP_HITS))

# ---- dump bodies for the report ----
say("=== G1 body (with image, base64 truncated) ===")
say(json.dumps(with_img_body, ensure_ascii=False, indent=2))
say("=== G2 body (without image) ===")
say(json.dumps(without_body, ensure_ascii=False, indent=2))
say("=== G1 text part (verbatim) ===")
say(with_img_text)
say("=== figure-context keywords in text part ===")
for kw in ("figure", "Figure", "image", "context", "изображ", "картин"):
    say(f"  '{kw}' in text part: {kw in with_img_text}")

say("DONE")
os._exit(0)
