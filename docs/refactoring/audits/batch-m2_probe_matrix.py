# -*- coding: utf-8 -*-
"""BATCH M2 matrix probe: M2.1 link-only paths, M2.2 visible errors, M2.3 NBSP.

Precedent: docs/refactoring/audits/batch-m1e_probe_head_nbsp.py (full app,
isolated profile, fake OpenAI-compatible loopback endpoint, network trap,
stubbed modals). Sections selectable via argv[3] (default: all).

Sections:
  S0  Qt mechanism proof: setPlainText NBSP round-trip, textChanged firing
      with / without blockSignals (the M2.3 mechanism).
  S1  batch (LLM) NBSP matrix: normal / link-only / mixed / link-only+NBSP;
      response carries NBSP -> segment.target must keep NBSP (M2.3 gate);
      link-only rows: target == source, draft, console line; ids gate.
  S2  whole-batch endpoint failure: link-only slot filled with source (M2.1e),
      others BATCH ERROR; console lines.
  S3  FuzzyFixer bulk: link-only 0 requests, source copy (M2.1a).
  S4  AutoTagger bulk: link-only filtered (caller gate, 0 requests, M2.1b);
      S4b failing endpoint -> translation_error console line (M2.2b).
  S5  MT batch: link-only 0 MT requests, source copy (M2.1c).
  S6  Proofreading: link-only excluded from the segment set (M2.1d), log line.
  S7  Match-panel chip: truncated answer -> error text in LLM chip, no modal
      (M2.2a); S7b success chip.
  S8  network trap (must be empty).

Run: python probe_m2_matrix.py <tree-root> <run-dir> [sections-csv]
"""
import faulthandler, json, os, pathlib, re, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
SECTIONS = set((sys.argv[3] if len(sys.argv) > 3 else
               "S0,S1,S2,S3,S4,S4b,S5,S6,S7,S8").split(","))
iso = stage / "iso"
OUT = stage / "probe_m2.json"

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

faulthandler.dump_traceback_later(240, repeat=True, file=sys.stderr)
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
MODE = {"mode": "ok"}
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
            "mode": MODE["mode"],
            "path": self.path,
            "model": body.get("model", ""),
            "n_messages": len(messages),
            "user_len": len(user_content),
            "ids_in_prompt": ids,
            "head": user_content[:160].replace("\n", "\\n"),
        })
        mode = MODE["mode"]
        finish = "stop"
        if mode == "fail":
            data = json.dumps({"error": {"message": "Simulated endpoint failure"}}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if mode == "mt":
            content = "MT-translated"
        elif mode == "truncate":
            content = "Partial answer"
            finish = "length"
        elif "[SEGMENT " in user_content:
            content = "[SEGMENT 0001] ✓ No issues"
        elif "Hello <1>world</1>" in user_content:
            content = "Hallo <1>wereld</1>"
        elif ids:
            content = "\n".join(f"{i}. Trans lated{i}" for i in ids)
        else:
            content = "Goedemorgen"
        resp = {
            "id": "chatcmpl-fake", "object": "chat.completion", "created": 1,
            "model": body.get("model", ""),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": finish}],
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

# ---------- section input files ----------
inputs = stage / "inputs"
inputs.mkdir(parents=True, exist_ok=True)
FILES = {
    "S1": ("m2_s1_nb4.txt", "Text alpha\n![Image](fig.png)\n![Image](x.png) Figure shows\n![Image](y.png) \n"),
    "S2": ("m2_s2_fail3.txt", "Text one\n![Image](fig.png)\nText two\n"),
    "S3": ("m2_s3_fuzzy3.txt", "Text one\n![Image](fig.png)\nText two\n"),
    "S4": ("m2_s4_tag2.txt", "Hello <1>world</1>\n![Image](fig.png)\n"),
    "S4b": ("m2_s4b_tag1.txt", "Hello <1>world</1>\n"),
    "S5": ("m2_s5_mt2.txt", "Text one\n![Image](fig.png)\n"),
    "S6": ("m2_s6_pr2.txt", "Text for proofread\n![Image](fig.png)\n"),
    "S7": ("m2_s7_fetch1.txt", "Fetch me text\n"),
}
for name, (fn, content) in FILES.items():
    (inputs / fn).write_text(content, encoding="utf-8")

open_queue = [str(inputs / FILES[k][0]) for k in
              ("S1", "S2", "S3", "S4", "S4b", "S5", "S6", "S7") if k in SECTIONS]


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
        "custom_openai_active_profile": "Fake Custom",
        "custom_mt_profiles": [{
            "name": "Fake MT", "endpoint": f"http://127.0.0.1:{PORT}/v1",
            "model": "fake-mt", "api_key": "mt-key", "raw_mode": True, "enabled": True}],
        "custom_mt_active_profile": "Fake MT"}},
    "api_keys": {"custom_openai": "file-key-456"},
}
sf.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")

result = {"tag": "m2-matrix", "port": PORT, "sections": sorted(SECTIONS),
          "requests": REQUESTS, "modal_log": modal_log, "checks": {}}
CHECKS = result["checks"]


def pump(n=30):
    for _ in range(n):
        app.processEvents()
        time.sleep(0.03)


def tu_count(win):
    cur = win.db_manager.connection.execute(
        "SELECT COUNT(*) AS c FROM translation_units")
    return cur.fetchone()["c"]


def payload_user_text(req_idx):
    body = json.loads((PAYLOADS_DIR / f"req-{req_idx:02d}.json").read_text(encoding="utf-8"))
    for m in reversed(body.get("messages", [])):
        if m.get("role") == "user":
            c = m.get("content")
            return c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
    return ""


TM_MARKERS = ("Added to TM", "Refusing to add TU", "Saved segment", "Saved to TM")

try:
    win = SV.SupervertalerQt()
    APP_LOG = []
    _orig_log = win.log
    win.log = lambda msg, *a, **k: (APP_LOG.append(str(msg)), _orig_log(msg, *a, **k))
    for _ in range(100):
        app.processEvents()
        time.sleep(0.05)

    CHIP = []
    if not getattr(win, "results_panels", None):
        win.create_assistance_panel()  # Match Panel is created lazily
    for _p in getattr(win, "results_panels", []):
        _o = _p.set_matches

        def cap(matches_dict, _o=_o):
            CHIP.append(matches_dict)
            return _o(matches_dict)

        _p.set_matches = cap

    # ================= S0: Qt widget mechanism (M2.3 proof basis) =================
    if "S0" in SECTIONS:
        s0 = {}
        ed = QW.QTextEdit()
        ed.setPlainText("a b")
        s0["roundtrip_repr"] = repr(ed.toPlainText())
        s0["nbsp_normalized_by_qt"] = ed.toPlainText() == "a b"
        w1 = QW.QTextEdit()
        fires1 = []
        w1.textChanged.connect(lambda: fires1.append(repr(w1.toPlainText())))
        w1.setPlainText("a b")
        s0["fires_without_block_synchronously"] = len(fires1)
        w2 = QW.QTextEdit()
        fires2 = []
        w2.textChanged.connect(lambda: fires2.append(repr(w2.toPlainText())))
        w2.blockSignals(True)
        w2.setPlainText("a b")
        w2.blockSignals(False)
        pump(15)
        s0["fires_with_block_after_pump"] = len(fires2)
        result["s0"] = s0
        CHECKS["s0_qt_normalizes_nbsp"] = s0["nbsp_normalized_by_qt"]
        CHECKS["s0_handler_fires_without_block"] = s0["fires_without_block_synchronously"] == 1
        CHECKS["s0_handler_quiet_with_block"] = s0["fires_with_block_after_pump"] == 0

    # ================= S1: batch NBSP matrix =================
    if "S1" in SECTIONS:
        win.import_simple_txt()
        pump(40)
        segs = win.current_project.segments
        rows = [(i, s) for i, s in enumerate(segs) if s.source.strip()]
        n0 = len(REQUESTS)
        log_n = len(APP_LOG)
        CONSOLE.clear()
        tu0 = tu_count(win)
        win.translate_batch(segments_with_rows=rows, scope_description="m2 S1 nbsp matrix")
        pump(35)
        req = REQUESTS[n0] if len(REQUESTS) > n0 else None
        result["s1"] = {
            "imported": [(s.id, repr(s.source)) for s in segs],
            "n_requests": len(REQUESTS) - n0,
            "ids_in_prompt": req["ids_in_prompt"] if req else None,
            "targets": [(s.id, repr(s.target), s.status) for s in segs],
            "widget_plain": [repr(win.table.cellWidget(i, 3).toPlainText())
                             for i in range(len(segs))
                             if win.table.cellWidget(i, 3)],
            "console_link": sum(1 for m, _ in CONSOLE if "⤳ link-only (LLM skipped)" in m),
            "tu_delta": tu_count(win) - tu0,
            "tm_log_lines": [l for l in APP_LOG[log_n:] if any(mk in l for mk in TM_MARKERS)],
        }
        t = {sid: tg for sid, tg, _ in result["s1"]["targets"]}
        CHECKS["s1_one_request"] = result["s1"]["n_requests"] == 1
        CHECKS["s1_ids_gate"] = result["s1"]["ids_in_prompt"] == [1, 3]
        CHECKS["s1_nbsp_preserved_normal"] = (
            t.get(1) == repr("Trans\xa0lated1") and t.get(3) == repr("Trans\xa0lated3"))
        CHECKS["s1_linkonly_copy"] = (
            t.get(2) == repr("![Image](fig.png)") and t.get(4) == repr("![Image](y.png)\xa0"))
        CHECKS["s1_all_draft"] = all(st == "draft" for _, _, st in result["s1"]["targets"])
        CHECKS["s1_console_2_lines"] = result["s1"]["console_link"] == 2
        CHECKS["s1_no_tu_written"] = result["s1"]["tu_delta"] == 0

    # ================= S2: whole-batch endpoint failure =================
    if "S2" in SECTIONS:
        win._batch_retry_pass = 1
        win._batch_provider_type = "LLM"
        win._batch_provider_name = "custom_openai"
        win._batch_model = "fake-llm"
        win._batch_retry_enabled = False
        MODE["mode"] = "fail"
        win.import_simple_txt()
        pump(40)
        segs = win.current_project.segments
        rows = [(i, s) for i, s in enumerate(segs) if s.source.strip()]
        n0 = len(REQUESTS)
        CONSOLE.clear()
        tu0 = tu_count(win)
        win.translate_batch(segments_with_rows=rows, scope_description="m2 S2 batch failure")
        pump(35)
        MODE["mode"] = "ok"
        for attr in ("_batch_retry_pass", "_batch_provider_type",
                     "_batch_provider_name", "_batch_model", "_batch_retry_enabled"):
            if hasattr(win, attr):
                delattr(win, attr)
        t = {s.id: (repr(s.target), s.status) for s in segs}
        reqs = REQUESTS[n0:]
        result["s2"] = {
            "n_requests": len(REQUESTS) - n0,
            "targets": [(s.id, repr(s.target), s.status) for s in segs],
            "console_link": sum(1 for m, _ in CONSOLE if "⤳ link-only (LLM skipped)" in m),
            "console_batch_error": sum(1 for m, _ in CONSOLE if "BATCH ERROR" in m),
            "tu_delta": tu_count(win) - tu0,
        }
        CHECKS["s2_requests_all_fail"] = len(reqs) >= 1 and all(q["mode"] == "fail" for q in reqs)
        CHECKS["s2_linkonly_copied_draft"] = (
            t.get(2) == (repr("![Image](fig.png)"), "draft"))
        CHECKS["s2_normal_failed_empty"] = (
            t.get(1)[0] == repr("") and t.get(3)[0] == repr(""))
        CHECKS["s2_console_link_1_error_2"] = (
            result["s2"]["console_link"] == 1 and result["s2"]["console_batch_error"] == 2)
        CHECKS["s2_no_tu_written"] = result["s2"]["tu_delta"] == 0

    # ================= S3: FuzzyFixer bulk =================
    if "S3" in SECTIONS:
        win.import_simple_txt()
        pump(40)
        # import resets fuzzy_fixer_enabled from general settings — set AFTER import
        win.fuzzy_fixer_enabled = True
        segs = win.current_project.segments
        rows = [(i, s) for i, s in enumerate(segs) if s.source.strip()]
        n0 = len(REQUESTS)
        CONSOLE.clear()
        tu0 = tu_count(win)
        win.translate_batch(segments_with_rows=rows, scope_description="m2 S3 fuzzy")
        pump(45)
        win.fuzzy_fixer_enabled = False
        t = {s.id: (repr(s.target), s.status) for s in segs}
        result["s3"] = {
            "n_requests": len(REQUESTS) - n0,
            "targets": [(s.id, repr(s.target), s.status) for s in segs],
            "console_link": sum(1 for m, _ in CONSOLE if "⤳ link-only (LLM skipped)" in m),
            "tu_delta": tu_count(win) - tu0,
        }
        CHECKS["s3_two_requests_only"] = result["s3"]["n_requests"] == 2
        CHECKS["s3_linkonly_copy_draft"] = t.get(2) == (repr("![Image](fig.png)"), "draft")
        CHECKS["s3_normal_translated"] = (
            t.get(1)[0] == repr("Goedemorgen") and t.get(3)[0] == repr("Goedemorgen"))
        CHECKS["s3_console_1_line"] = result["s3"]["console_link"] == 1
        CHECKS["s3_no_tu_written"] = result["s3"]["tu_delta"] == 0

    # ================= S4 / S4b: AutoTagger bulk =================
    if "S4" in SECTIONS:
        win.import_simple_txt()
        pump(40)
        segs = win.current_project.segments
        segs[0].target = "Hallo wereld"
        segs[1].target = "![Image](fig.png)"
        n0 = len(REQUESTS)
        CONSOLE.clear()
        tu0 = tu_count(win)
        win.autotag_segments_bulk()
        pump(35)
        result["s4"] = {
            "n_requests": len(REQUESTS) - n0,
            "targets": [(s.id, repr(s.target), s.status) for s in segs],
            "console_no_tags": sum(1 for m, _ in CONSOLE if "⊘ no tags" in m),
            "tu_delta": tu_count(win) - tu0,
        }
        CHECKS["s4_only_tagged_request"] = result["s4"]["n_requests"] == 1
        CHECKS["s4_linkonly_untouched"] = result["s4"]["targets"][1][1] == repr("![Image](fig.png)")
        CHECKS["s4_no_tu_written"] = result["s4"]["tu_delta"] == 0
    if "S4b" in SECTIONS:
        MODE["mode"] = "fail"
        win.import_simple_txt()
        pump(40)
        segs = win.current_project.segments
        segs[0].target = "Hallo wereld"
        n0 = len(REQUESTS)
        log_n = len(APP_LOG)
        CONSOLE.clear()
        win.autotag_segments_bulk()
        pump(35)
        MODE["mode"] = "ok"
        result["s4b"] = {
            "n_requests": len(REQUESTS) - n0,
            "console_fail_lines": [m for m, _ in CONSOLE if "❌ AutoTagger:" in m],
            "app_fail_lines": [l for l in APP_LOG[log_n:] if "❌ AutoTagger batch failed" in l],
        }
        CHECKS["s4b_console_error_line"] = any("AutoTagger on #" in m for m in result["s4b"]["console_fail_lines"])
        CHECKS["s4b_app_log_line"] = len(result["s4b"]["app_fail_lines"]) >= 1

    # ================= S5: MT batch =================
    if "S5" in SECTIONS:
        win._batch_retry_pass = 1
        win._batch_provider_type = "MT"
        win._batch_provider_name = "Custom MT"
        win._batch_retry_enabled = False
        MODE["mode"] = "mt"
        win.import_simple_txt()
        pump(40)
        segs = win.current_project.segments
        rows = [(i, s) for i, s in enumerate(segs) if s.source.strip()]
        n0 = len(REQUESTS)
        CONSOLE.clear()
        tu0 = tu_count(win)
        win.translate_batch(segments_with_rows=rows, scope_description="m2 S5 MT")
        pump(35)
        MODE["mode"] = "ok"
        for attr in ("_batch_retry_pass", "_batch_provider_type",
                     "_batch_provider_name", "_batch_retry_enabled"):
            if hasattr(win, attr):
                delattr(win, attr)
        t = {s.id: (repr(s.target), s.status) for s in segs}
        result["s5"] = {
            "n_requests": len(REQUESTS) - n0,
            "targets": [(s.id, repr(s.target), s.status) for s in segs],
            "console_link": sum(1 for m, _ in CONSOLE if "⤳ link-only (MT skipped)" in m),
            "tu_delta": tu_count(win) - tu0,
        }
        CHECKS["s5_one_request"] = result["s5"]["n_requests"] == 1
        CHECKS["s5_linkonly_copy_draft"] = t.get(2) == (repr("![Image](fig.png)"), "draft")
        CHECKS["s5_normal_mt_done"] = t.get(1)[0] == repr("MT-translated")
        CHECKS["s5_console_1_line"] = result["s5"]["console_link"] == 1
        CHECKS["s5_no_tu_written"] = result["s5"]["tu_delta"] == 0

    # ================= S6: Proofreading entry =================
    if "S6" in SECTIONS:
        win.import_simple_txt()
        pump(40)
        segs = win.current_project.segments
        rows_pr = [(i, s) for i, s in enumerate(segs) if s.source.strip()]
        n0 = len(REQUESTS)
        log_n = len(APP_LOG)
        CONSOLE.clear()
        win._run_proofreading(rows_pr, "custom_openai", "fake-llm", "", win.load_llm_settings())
        pump(45)
        payload = payload_user_text(n0) if len(REQUESTS) > n0 else ""
        result["s6"] = {
            "n_requests": len(REQUESTS) - n0,
            "payload_has_normal": "Text for proofread" in payload,
            "payload_has_linkonly": "fig.png" in payload,
            "log_exclusion": [l for l in APP_LOG[log_n:] if "excluded from proofreading" in l],
            "notes": [(s.id, repr(getattr(s, "proofreading_notes", ""))) for s in segs],
        }
        CHECKS["s6_one_request"] = result["s6"]["n_requests"] == 1
        CHECKS["s6_payload_excludes_linkonly"] = (
            result["s6"]["payload_has_normal"] and not result["s6"]["payload_has_linkonly"])
        CHECKS["s6_log_line"] = len(result["s6"]["log_exclusion"]) >= 1

    # ================= S7: chip visible errors =================
    if "S7" in SECTIONS:
        win.import_simple_txt()
        pump(40)
        segs = win.current_project.segments
        win.table.selectRow(0)
        pump(3)
        win.table.setCurrentCell(0, 2)
        pump(3)
        MODE["mode"] = "truncate"
        CHIP.clear()
        modal_n = len(modal_log)
        n0 = len(REQUESTS)
        log_n = len(APP_LOG)
        # re-wrap AFTER import: the panel objects are recreated on project load
        _panels = getattr(win, "results_panels", None)
        if not _panels:
            win.create_assistance_panel()
            _panels = win.results_panels
        for _p in _panels:
            if getattr(_p, "_m2cap", False):
                continue
            _o2 = _p.set_matches

            def cap2(matches_dict, _o2=_o2):
                CHIP.append(matches_dict)
                return _o2(matches_dict)

            _p.set_matches = cap2
            _p._m2cap = True
        win._fetch_llm_translation_async("Fetch me text", segs[0], 0)
        pump(30)
        last = CHIP[-1] if CHIP else None
        llm_m = (last or {}).get("LLM") or []
        chip = llm_m[0] if llm_m else None
        result["s7"] = {
            "n_requests": len(REQUESTS) - n0,
            "chip_present": chip is not None,
            "chip_target": repr(getattr(chip, "target", None)) if chip else None,
            "chip_metadata": getattr(chip, "metadata", None) if chip else None,
            "log_lines": [l for l in APP_LOG[log_n:] if "LLM translation failed" in l],
            "modal_delta": len(modal_log) - modal_n,
        }
        meta = getattr(chip, "metadata", {}) if chip else {}
        CHECKS["s7_one_request"] = result["s7"]["n_requests"] == 1
        CHECKS["s7_chip_error"] = (
            result["s7"]["chip_present"] and meta.get("llm_error") == "LLMTruncatedError")
        CHECKS["s7_chip_hint_max_tokens"] = "Max tokens" in (getattr(chip, "target", "") if chip else "")
        CHECKS["s7_no_modal"] = result["s7"]["modal_delta"] == 0
        CHECKS["s7_log_line"] = any("shown in LLM chip" in l for l in result["s7"]["log_lines"])
        # S7b: success chip on the same row — INFORMATIONAL ONLY: the success
        # path is gated on self.assistance_widget, which is never assigned in
        # the current codebase (dead gate, predates M2) — no check.
        CHIP.clear()
        win._fetch_llm_translation_async("Fetch me text", segs[0], 0)
        pump(30)
        last = CHIP[-1] if CHIP else None
        llm_m = (last or {}).get("LLM") or []
        chip2 = llm_m[0] if llm_m else None
        result["s7b"] = {"chip_target": repr(getattr(chip2, "target", None)) if chip2 else None}
        MODE["mode"] = "ok"

    # ================= S8: network trap =================
    result["net_traps"] = NET_TRAPS
    CHECKS["s8_no_net_traps"] = not NET_TRAPS

    result["verdict"] = "PASS" if all(CHECKS.values()) else "FAIL"
except BaseException as e:
    import traceback
    result["exception"] = f"{type(e).__name__}: {e}"
    result["traceback"] = traceback.format_exc()
    result["verdict"] = "EXCEPTION"

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
os._exit(0)
