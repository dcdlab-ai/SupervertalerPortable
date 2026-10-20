# -*- coding: utf-8 -*-
"""M1e matrix probe: broadened link-only criterion (leftover without letters/digits).

Precedent: docs/refactoring/audits/batch-m1_probe_m1_e2e.py (full app, isolated
profile, fake OpenAI-compatible loopback endpoint, network trap, stubbed modals).

Scenarios:
  S1 single-matrix — 14 segments (Dmitry's M1e matrix); for each row, Ctrl+T
     (translate_current_segment): requests to the fake endpoint, target, status,
     TM log lines, delta of rows in translation_units.
  S2 batch — fresh import of the same 14 rows, one batch run: ids in the prompt
     must be exactly the LLM rows; link-only targets == source byte-wise; TM delta.
  S3 net-trap — socket.connect to any non-loopback address must be zero.

Run: python probe_m1e_matrix.py <tree-root> <run-dir>   (offscreen, isolated profile)
"""
import faulthandler, hashlib, json, os, pathlib, re, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
iso = stage / "iso"
OUT = stage / "probe_m1e_verdict.json"

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(stage / "tmp")
os.environ["TMP"] = str(stage / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg = iso / "AppData" / "Roaming" / "Supervertaler"
cfg.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8")

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

# ---------- network trap ----------
NET_TRAPS = []
_real_connect = socket.socket.connect


def _traced_connect(self, address, *a, **k):
    if isinstance(address, tuple) and len(address) >= 2:
        host = address[0]
        if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost"):
            NET_TRAPS.append(str(address))
    return _real_connect(self, address, *a, **k)


socket.socket.connect = _traced_connect

# ---------- fake OpenAI-compatible endpoint (loopback only) ----------
REQUESTS = []
PAYLOADS_DIR = stage / "payloads"
PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8", "replace")) if length else {}
        messages = body.get("messages", [])
        user_content = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                user_content = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                break
        n = len(REQUESTS)
        (PAYLOADS_DIR / f"req-{n:02d}.json").write_text(
            json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
        ids = []
        if "**SEGMENTS TO TRANSLATE" in user_content:
            seg_part = user_content.split("**SEGMENTS TO TRANSLATE:")[-1]
            seg_part = seg_part.split("**YOUR TRANSLATIONS")[0]
            ids = [int(m) for m in re.findall(r"(?m)^(\d+)\.\s", seg_part)]
        REQUESTS.append({
            "path": self.path,
            "model": body.get("model", ""),
            "n_messages": len(messages),
            "user_len": len(user_content),
            "ids_in_prompt": ids,
            "head": user_content[:120].replace("\n", "\\n"),
        })
        if ids:
            content = "\n".join(f"{i}. Translated{i}" for i in ids)
        else:
            content = "Goedemorgen"
        resp = {
            "id": "chatcmpl-fake", "object": "chat.completion", "created": 1,
            "model": body.get("model", ""),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
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

# ---------- modal/file-dialog neutralization ----------
import PyQt6.QtWidgets as QW  # noqa: E402
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog  # noqa: E402

modal_log = []
_real_exec = QDialog.exec


def _logging_exec(self, *a, **k):
    modal_log.append(f"QDialog.exec {type(self).__name__} '{self.windowTitle()}'")
    return QDialog.DialogCode.Accepted


QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda self_t, *a, **k: (modal_log.append(f"QMessageBox '{a[1] if len(a) > 1 else ''}'"), QMessageBox.StandardButton.Ok)[1])
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

# ---------- M1e matrix input (Dmitry's cases, one per line; line 12 empty) ----------
CASES = [
    ("link_nbsp_period", "![Image](x) ."),
    ("clean_period", "![Image](x)."),
    ("plain_text", "Text one"),
]
EXPECT_LINK_ONLY = {name: val for name, txt in CASES
                    for val in [bool(re.search(r"!\[[^\]]*\]\([^)]*\)", txt)
                                    and not re.search(r"[^\W_]",
                                                      re.sub(r"!\[[^\]]*\]\([^)]*\)", "", txt)))]}

inputs = stage / "inputs"
inputs.mkdir(parents=True, exist_ok=True)
matrix = inputs / "m1e_matrix_en_nl.txt"
matrix.write_text("\n".join(txt for _, txt in CASES) + "\n", encoding="utf-8")

open_queue = [str(matrix), str(matrix)]


def fake_open(*a, **k):
    return (open_queue.pop(0) if open_queue else "", "")


QFileDialog.getOpenFileName = staticmethod(fake_open)
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(open_queue), "") if open_queue else ([], ""))

import Supervertaler as SV  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from modules.dialogs import live_progress as _lp  # noqa: E402
CONSOLE = []
_lp.LiveProgressDialog.add_console_line = lambda self, message, is_success=True: CONSOLE.append((str(message), bool(is_success)))

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

sf = data_dir / "workbench" / "settings" / "settings.json"
sf.parent.mkdir(parents=True, exist_ok=True)
seed = {
    "ui": {"llm_settings": {
        "provider": "custom_openai",
        "custom_openai_profiles": [{
            "name": "Fake Custom", "endpoint": f"http://127.0.0.1:{PORT}/v1",
            "model": "fake-llm", "api_key": "prof-key-123", "enabled": True}],
        "custom_openai_active_profile": "Fake Custom"}},
    "api_keys": {"custom_openai": "file-key-456"},
}
sf.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")

result = {"tag": "m1e-matrix", "port": PORT, "requests": REQUESTS, "modal_log": modal_log}


def pump(n=30):
    for _ in range(n):
        app.processEvents()
        time.sleep(0.03)


def tu_count(win):
    cur = win.db_manager.connection.execute(
        "SELECT COUNT(*) AS c FROM translation_units")
    return cur.fetchone()["c"]


TM_MARKERS = ("Added to TM", "Refusing to add TU", "Saved segment", "Saved to TM")

try:
    win = SV.SupervertalerQt()
    APP_LOG = []
    _orig_log = win.log
    win.log = lambda msg, *a, **k: (APP_LOG.append(str(msg)), _orig_log(msg, *a, **k))
    for _ in range(100):
        app.processEvents()
        time.sleep(0.05)

    # ================= S1: single Ctrl+T over the 14-case matrix =================
    win.import_simple_txt()
    pump(40)
    segs = win.current_project.segments
    result["s1_imported"] = [(s.id, repr(s.source)) for s in segs]
    if len(segs) < len(CASES):
        raise RuntimeError(f"matrix import produced {len(segs)} segments, expected >=14")
    # normalize: cases follow the first 14 rows in file order
    result["s1"] = {}
    for i, (name, txt) in enumerate(CASES):
        s = segs[i]
        win.table.selectRow(i)
        pump(3)
        win.table.setCurrentCell(i, 2)
        pump(3)
        n0 = len(REQUESTS)
        log_n = len(APP_LOG)
        tu0 = tu_count(win)
        win.translate_current_segment()
        pump(15)
        new_log = APP_LOG[log_n:]
        result["s1"][name] = {
            "src_repr": repr(s.source),
            "n_requests": len(REQUESTS) - n0,
            "tgt_repr": repr(s.target),
            "target_eq_source": s.target == s.source,
            "status": s.status,
            "tu_delta": tu_count(win) - tu0,
            "tm_log_lines": [l for l in new_log if any(mk in l for mk in TM_MARKERS)],
            "gate_line": [l for l in new_log if "link-only segment" in l],
        }

    # ================= S2: batch over fresh import =================
    win.import_simple_txt()
    pump(40)
    segs2 = win.current_project.segments
    rows2 = [(i, s) for i, s in enumerate(segs2) if s.source.strip()]
    n0 = len(REQUESTS)
    log_n = len(APP_LOG)
    CONSOLE.clear()
    tu0 = tu_count(win)
    win.translate_batch(segments_with_rows=rows2, scope_description="m1e batch")
    pump(25)
    result["s2_targets_repr"] = [(s.id, repr(s.source), repr(s.target)) for s in segs2]
    result["s2_app_log"] = APP_LOG[log_n:]
    req = REQUESTS[n0] if len(REQUESTS) > n0 else None
    llm_ids = [segs2[i].id for i, (nm, tx) in zip(range(len(segs2)), CASES)
               if not EXPECT_LINK_ONLY[nm] and tx.strip()]
    result["s2"] = {
        "n_requests": len(REQUESTS) - n0,
        "ids_in_prompt": req["ids_in_prompt"] if req else None,
        "expected_sent_ids": llm_ids,
        "targets_eq_source": [segs2[i].target == segs2[i].source
                              for i in range(min(len(segs2), len(CASES)))
                              if EXPECT_LINK_ONLY[CASES[i][0]]],
        "statuses": [s.status for s in segs2],
        "console_link_only_lines": sum(1 for m, _ in CONSOLE if "⤳ link-only (LLM skipped)" in m),
        "tu_delta": tu_count(win) - tu0,
    }

    # ================= S3: net trap =================
    result["net_traps"] = NET_TRAPS

    # ---- verdict ----
    checks = {}
    checks["s1_imported_14"] = len(segs) >= 14
    for name, txt in CASES:
        r = result["s1"][name]
        exp_link_only = EXPECT_LINK_ONLY[name]
        if exp_link_only:
            checks[f"s1_{name}"] = (
                r["n_requests"] == 0 and r["target_eq_source"]
                and r["status"] == "draft" and r["tu_delta"] == 0
                and not r["tm_log_lines"] and len(r["gate_line"]) == 1)
        elif not txt.strip():
            checks[f"s1_{name}"] = (
                r["n_requests"] == 0 and r["tgt_repr"] == "''"
                and r["status"] == "untranslated" and r["tu_delta"] == 0)
        else:
            checks[f"s1_{name}"] = (
                r["n_requests"] == 1 and r["tgt_repr"] == "'Goedemorgen'"
                and r["status"] == "draft" and r["tu_delta"] == 0)
    checks["s2_n_requests_1"] = result["s2"]["n_requests"] == 1
    checks["s2_sent_ids_exact"] = result["s2"]["ids_in_prompt"] == result["s2"]["expected_sent_ids"]
    checks["s2_all_link_targets_eq_source"] = all(result["s2"]["targets_eq_source"])
    checks["s2_console_8_copy_lines"] = result["s2"]["console_link_only_lines"] == 8
    checks["s2_no_tu_written"] = result["s2"]["tu_delta"] == 0
    checks["s3_no_net_traps"] = not result["net_traps"]
    result["checks"] = checks
    result["verdict"] = "PASS" if all(checks.values()) else "FAIL"
except BaseException as e:
    import traceback
    result["exception"] = f"{type(e).__name__}: {e}"
    result["traceback"] = traceback.format_exc()
    result["verdict"] = "EXCEPTION"

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
os._exit(0)
