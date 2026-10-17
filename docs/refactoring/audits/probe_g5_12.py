# -*- coding: utf-8 -*-
"""Batch G5.1+G5.2 special probe (P1-P11).

Fake OpenAI-compatible endpoint on 127.0.0.1 + network trap (same harness as
g5_prompt_capture.py). Verifies:
  P1  vision=True + figure ref + loaded image -> image_url present AND
      FIGURE CONTEXT block in text, labels in sent order, final delimiter
      stays the last line.
  P2  vision=False + same segment -> 0 image parts, NO block in text.
  P3  segment without figure ref + vision=True + images loaded -> 0 image
      parts, no block.
  P4  two refs with images -> block lists both in order, 2 image parts.
  P5  user-saved layer1.json containing the OLD static line -> old line kept
      (saved copy untouched), block inserted exactly once, delimiter last.
  P6  Image Extractor AI-label prompt -> no FIGURE CONTEXT block.
  P7  Combined Prompt Preview -> figure info line present, block NOT in
      preview (expected divergence documented in report).
  P8  5 refs with 5 images -> only first 4 sent, log 'Figure context: 5
      images found, only first 4 sent', labels Image 1..4.
  P9  batch worker (PreTranslationWorker._translate_with_llm) -> 0 image
      parts, no block.
  P10 md-insertion '![Image](..\\Figure 2.jpg)' -> ref '2' sent (indirect
      path preserved).
  P11 network trap silent + emoji/non-ASCII arrive as correct UTF-8 bytes.
Run: python probe_g5_12.py <tree-root> <iso-dir>
"""
import faulthandler, importlib.abc, json, os, pathlib, socket, sys, threading
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

faulthandler.dump_traceback_later(300, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import (  # noqa: E402
    QApplication, QDialog, QMessageBox, QFileDialog, QCheckBox, QLabel,
    QPlainTextEdit, QTextEdit)

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


BLOCK = "FIGURE CONTEXT:"
OLD_LINE = ("If the text refers to figures (e.g., 'Figure 1A'), relevant "
            "images may be provided for visual context.")

# ---------------- segments ----------------
SEG0 = "See Figure 1A — café ☕ «привет» 🖼️ gear engages"
SEG1 = "Plain segment without references"
SEG2 = "See Figure 1A and Figure 2 for details"
SEG3 = "See Figures 1A, 2, 3, 4 and 5"
SEG4 = "![Image](..\\Figure 2.jpg)"
inputs = iso / "inputs"
inputs.mkdir(exist_ok=True)
(inputs / "fig.txt").write_text("\n".join([SEG0, SEG1, SEG2, SEG3, SEG4]) + "\n",
                                encoding="utf-8")
open_queue = [str(inputs / "fig.txt")]
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(open_queue), ""))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (open_queue.pop(0) if open_queue else "", ""))

A = prof("Profile A", vision=True)
B = prof("Profile B", model="model-b", vision=False)
write_settings([A, B], active="Profile A")

win = Supervertaler.SupervertalerQt()
say("WINDOW OK")

LOGS = []
_orig_log = win.log


def log_cap(msg, *a, **k):
    LOGS.append(str(msg))
    _orig_log(msg, *a, **k)


win.log = log_cap

win.import_simple_txt()
say("segs=", len(win.current_project.segments) if win.current_project else 0)

# Load fixture images as refs 1a,2,3,4,5
from PIL import Image
fixture = tree / "docs" / "refactoring" / "samples" / "Figure 1A.png"
fixture2 = tree / "docs" / "refactoring" / "samples" / "Figure 2.jpg"
img = Image.open(str(fixture)).convert("RGB")
img2 = Image.open(str(fixture2)).convert("RGB")
for ref in ("1a", "3", "4", "5"):
    win.figure_context.figure_context_map[ref] = img
win.figure_context.figure_context_map["2"] = img2
say("fixtures loaded:", list(win.figure_context.figure_context_map.keys()))


def translate_row(row, active):
    write_settings([A, B], active=active)
    win.table.selectRow(row)
    win.table.setCurrentCell(row, 0)
    REQUESTS.clear()
    win.translate_current_segment()
    body = REQUESTS[0]["body"] if REQUESTS else {}
    text = "\n".join(text_parts(body))
    return body, text


def last_line(text):
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


# ---- P1: vision=True, ref+image -> image + block, delimiter last ----
body, text = translate_row(0, "Profile A")
check("P1 vision=True -> 1 image part", image_parts(body) == 1, f"img={image_parts(body)}")
check("P1 block present with label 'Image 1 = Figure 1A'",
      BLOCK in text and "Image 1 = Figure 1A" in text)
check("P1 final delimiter is last line", last_line(text).startswith("**YOUR TRANSLATION"),
      repr(last_line(text)[:40]))
check("P1 block placed before delimiter",
      BLOCK in text and text.find(BLOCK) < text.find("**YOUR TRANSLATION"))

# ---- P2: vision=False -> 0 images, no block ----
body, text = translate_row(0, "Profile B")
check("P2 vision=False -> 0 image parts", image_parts(body) == 0, f"img={image_parts(body)}")
check("P2 no block in text", BLOCK not in text)

# ---- P3: no figure ref -> 0 images, no block ----
body, text = translate_row(1, "Profile A")
check("P3 no-ref segment -> 0 image parts", image_parts(body) == 0, f"img={image_parts(body)}")
check("P3 no block in text", BLOCK not in text)

# ---- P4: two refs -> 2 images, labels in order ----
body, text = translate_row(2, "Profile A")
check("P4 two refs -> 2 image parts", image_parts(body) == 2, f"img={image_parts(body)}")
check("P4 labels in sent order",
      "Image 1 = Figure 1A; Image 2 = Figure 2" in text,
      repr([ln for ln in text.splitlines() if BLOCK in ln][:1]))

# ---- P5: user-saved layer1.json with OLD line -> kept, block once ----
pm = win.prompt_manager_qt
lib_dir = pathlib.Path(pm.prompt_library_dir)
layer1 = lib_dir / "system_prompts_layer1.json"
default_tpl = pm._get_default_system_template("single")
saved_tpl = default_tpl.replace(
    "{{SOURCE_LANGUAGE}} text:", OLD_LINE + "\n\n{{SOURCE_LANGUAGE}} text:")
layer1.write_text(json.dumps({"single": saved_tpl}, ensure_ascii=False), encoding="utf-8")
pm._load_system_templates()
body, text = translate_row(0, "Profile A")
check("P5 saved copy keeps OLD static line (kept verbatim)", text.count(OLD_LINE) == 1)
check("P5 block inserted exactly once", text.count(BLOCK) == 1, f"count={text.count(BLOCK)}")
check("P5 delimiter last line", last_line(text).startswith("**YOUR TRANSLATION"))
check("P5 layer1.json untouched by translation",
      json.loads(layer1.read_text(encoding="utf-8"))["single"] == saved_tpl)
layer1.unlink()
pm._load_system_templates()

# ---- P6: Image Extractor AI-label prompt has no block ----
cb = getattr(pm, "chat_backend", None)


class StubLLM:
    provider = "custom_openai"
    model = "model-x"
    supports_vision = True


CAPTURED = []


class StubChat:
    llm_client = StubLLM()

    def send_ai_request(self, prompt, system_prompt, is_analysis=False, images=None, **k):
        CAPTURED.append({"prompt": prompt, "system": system_prompt,
                         "images": len(images) if images else 0})
        return "Figure 1A", {}


win.prompt_manager_qt.chat_backend = StubChat()
if not hasattr(win, "image_extractor_ai_label"):
    win.image_extractor_ai_label = QCheckBox()
win.image_extractor_ai_label.setChecked(True)
# Gate 4 stub: one unlabelled image in the peek (empty docx list would make
# the builder silently return None — that is the builder's own design).
_orig_peek = win.image_extractor.peek_labels_multiple
win.image_extractor.peek_labels_multiple = lambda paths: [
    ("stub.docx", [("media1", None, "See Figure 1A")])]
# Gate 5 confirmation compares against Ok specifically.
_orig_question = QMessageBox.question
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
fn = win._build_image_extract_ai_callback(["stub.docx"])
QMessageBox.question = _orig_question
win.image_extractor.peek_labels_multiple = _orig_peek
if callable(fn):
    with open(str(fixture), "rb") as fh:
        fn(fh.read(), "See Figure 1A", "Figure 1A.png")
    p6 = CAPTURED[0] if CAPTURED else {}
    check("P6 extractor callback invoked with 1 image", p6.get("images") == 1, str(p6.get("images")))
    check("P6 extractor prompt has NO figure-context block",
          BLOCK not in p6.get("prompt", "") and "label" in p6.get("prompt", "").lower())
else:
    check("P6 extractor callback invoked with 1 image", False, f"fn={fn!r}")
win.prompt_manager_qt.chat_backend = cb

# ---- P7: preview shows figure info AND the block, byte-identical to
# the request block (verdict answer 1, G5.1d: shared builder function) ----
preview_texts = []
_orig_exec = QDialog.exec


def cap_exec(self, *a, **k):
    for lbl in self.findChildren(QLabel):
        preview_texts.append(lbl.text())
    for ed in self.findChildren(QPlainTextEdit):
        preview_texts.append(ed.toPlainText())
    for ed in self.findChildren(QTextEdit):
        preview_texts.append(ed.toPlainText())
    return QDialog.DialogCode.Accepted


QDialog.exec = cap_exec
win.table.selectRow(0)
win.table.setCurrentCell(0, 0)
try:
    win._preview_combined_prompt_from_grid()
except Exception as e:
    say("P7 preview call note:", e)
QDialog.exec = _orig_exec
pv = "\n".join(preview_texts)
check("P7 preview mentions image(s) will be sent", "image(s) will be sent" in pv)
check("P7 preview HAS the figure-context block", BLOCK in pv)
# Byte-identity: extract the block line from the request (P1 text) and
# from the preview and compare exactly.
_req_block = next((ln for ln in text.splitlines() if ln.startswith(BLOCK)), "")
_pv_block = next((ln for ln in pv.splitlines() if ln.startswith(BLOCK)), "")
check("P7 preview block byte-identical to request block",
      _req_block == _pv_block and bool(_req_block),
      f"req={len(_req_block)}B pv={len(_pv_block)}B")
check("P7 preview delimiter stays last line", last_line(pv).startswith("**YOUR TRANSLATION"),
      repr(last_line(pv)[:40]))

# ---- P8: 5 refs, 5 images -> first 4 sent + log ----
LOGS.clear()
body, text = translate_row(3, "Profile A")
check("P8 5 refs -> only 4 image parts", image_parts(body) == 4, f"img={image_parts(body)}")
check("P8 overflow logged",
      any("Figure context: 5 images found, only first 4 sent" in ln for ln in LOGS),
      str([ln for ln in LOGS if "Figure context" in ln]))
check("P8 labels Image 1..4 in appearance order",
      all(f"Image {i} = Figure {r}" in text for i, r in ((1, "1A"), (2, "2"), (3, "3"), (4, "4"))))

# ---- P9: batch worker -> 0 images, no block ----
seg = win.current_project.segments[0]
worker = Supervertaler.PreTranslationWorker(
    parent_app=win, segments=[seg], provider_type="custom_openai",
    provider_name="custom_openai", model="model-x",
    prompt_manager=win.prompt_manager_qt, base_url=EP, custom_api_key="")
REQUESTS.clear()
worker._translate_with_llm(seg)
body = REQUESTS[0]["body"] if REQUESTS else {}
text = "\n".join(text_parts(body))
check("P9 batch worker -> 1 request, 0 image parts",
      len(REQUESTS) == 1 and image_parts(body) == 0,
      f"reqs={len(REQUESTS)} img={image_parts(body)}")
check("P9 batch worker text has NO block", BLOCK not in text)

# ---- P10: md-insertion indirect path preserved ----
body, text = translate_row(4, "Profile A")
check("P10 md-insertion ref '2' -> 1 image part", image_parts(body) == 1, f"img={image_parts(body)}")
check("P10 block labels Figure 2", "Image 1 = Figure 2" in text)

# ---- P11: trap silent + UTF-8 bytes ----
body, text = translate_row(0, "Profile A")
raw = REQUESTS[0]["raw"] if REQUESTS else b""
seqs = {"café é": b"\xc3\xa9", "☕": b"\xe2\x98\x95", "«": b"\xc2\xab",
        "»": b"\xc2\xbb", "привет п": b"\xd0\xbf", "🖼": b"\xf0\x9f\x96\xbc"}
check("P11 emoji/non-ASCII arrive as UTF-8 bytes",
      all(s in raw for s in seqs.values()),
      str({k: (s in raw) for k, s in seqs.items()}))
check("P11 no '?' substitution in text part", text.count("?") == 0, f"q={text.count('?')}")
check("P11 network trap silent", not TRAP_HITS, str(TRAP_HITS))

# ---- static: block text lives ONLY in the shared builder (G5.1d) ----
mp = (tree / "modules" / "unified_prompt_manager_qt.py").read_text(encoding="utf-8")
fp = (tree / "modules" / "figure_context_manager.py").read_text(encoding="utf-8")
mono = (tree / "Supervertaler.py").read_text(encoding="utf-8")
check("static: block text in figure module (shared builder)", BLOCK in fp)
check("static: no block text in prompt manager", BLOCK not in mp)
check("static: no block text copy in monolith (calls builder only)",
      BLOCK not in mono and "build_figure_context_block" in mono)

say("DONE")
os._exit(0)
