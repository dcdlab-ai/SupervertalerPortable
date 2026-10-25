# -*- coding: utf-8 -*-
"""BATCH Q-C / Q.7r probe — NBSP survives every target-write path.

Paths (prompt list):
  A QuickTrans panel Fetch + Ctrl+N insert (real panel, real handler chain)
  B TM inserts: search_and_display_tm_matches 100% autofill + _auto_insert_tm_match
  C batch LLM translation (PreTranslationWorker, fake endpoint NBSP answers)
  D manual edit of a NEIGHBOUR char in a cell that already holds NBSP
  E Ctrl+T single-segment LLM translation
  F idempotency: repeat programmatic insert of the same text -> no extra undo
  G export: simple txt keeps \xa0
Regressions per path: status, undo args, TM debounce no-crash, preview no-crash.

Run: python probe_q7r.py <tree-root> <stage-dir>
"""
import faulthandler, json, os, pathlib, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
iso = stage / "iso"
OUT = stage / "probe_q7r.json"

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

faulthandler.dump_traceback_later(300, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

NB = '\xa0'

# ---------- network trap ----------
NET_TRAPS = []
_real_connect = socket.socket.connect


def _trapped_connect(self, address, *a, **k):
    if isinstance(address, tuple) and len(address) >= 2:
        host = address[0]
        if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost"):
            NET_TRAPS.append(str(address))
    return _real_connect(self, address, *a, **k)


socket.socket.connect = _trapped_connect

# ---------- fake OpenAI-compatible endpoint ----------
REQUESTS = []


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n).decode("utf-8", "replace")) if n else {}
        user_content = ""
        for m in reversed(body.get("messages", [])):
            if m.get("role") == "user":
                c = m.get("content")
                user_content = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                break
        REQUESTS.append({"path": self.path, "model": body.get("model", ""),
                         "head": user_content[:120].replace("\n", "\\n")})
        import re as _re
        ids = []
        if "**SEGMENTS TO TRANSLATE" in user_content:
            seg_part = user_content.split("**SEGMENTS TO TRANSLATE:")[-1].split("**YOUR TRANSLATIONS")[0]
            ids = [int(m) for m in _re.findall(r"(?m)^(\d+)\.\s", seg_part)]
        if ids:
            content = "\n".join(f"{i}. Batch{NB}antwoord{NB}{i}" for i in ids)
        elif "QuickTrans" in user_content:
            content = f"Paneel{NB}vertaling{NB}NBSP"
        elif "CtrlT" in user_content:
            content = f"CtrlT{NB}antwoord"
        else:
            content = f"Vraag{NB}antwoord"
        resp = {"id": "chatcmpl-q7r", "object": "chat.completion", "created": 1,
                "model": body.get("model", ""),
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}}
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


def _logging_exec(self, *a, **k):
    modal_log.append(f"QDialog.exec {type(self).__name__} '{self.windowTitle()}'")
    return QDialog.DialogCode.Accepted


QDialog.exec = _logging_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: (modal_log.append(f"warn '{a[1] if len(a) > 1 else ''}'"), QMessageBox.StandardButton.Ok)[1])
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

inputs = stage / "inputs"
inputs.mkdir(parents=True, exist_ok=True)
(inputs / "q7r_a.txt").write_text("QuickTrans segment one\nQuickTrans segment two\n", encoding="utf-8")
(inputs / "q7r_c.txt").write_text("Batch alpha\nBatch beta\n", encoding="utf-8")
(inputs / "q7r_e.txt").write_text("CtrlT segment two\n", encoding="utf-8")

open_queue = [str(inputs / "q7r_a.txt"), str(inputs / "q7r_c.txt"), str(inputs / "q7r_e.txt")]
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (open_queue.pop(0) if open_queue else "", ""))
export_path = str(stage / "export_out.txt")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (export_path, ""))

import Supervertaler as SV  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from modules.dialogs import live_progress as _lp  # noqa: E402
CONSOLE = []
_lp.LiveProgressDialog.add_console_line = lambda self, message, is_success=True: CONSOLE.append((str(message), bool(is_success)))

from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402

app = QApplication(sys.argv)

sf = data_dir / "workbench" / "settings" / "settings.json"
sf.parent.mkdir(parents=True, exist_ok=True)
sf.write_text(json.dumps({
    "ui": {"llm_settings": {
        "provider": "custom_openai",
        "custom_openai_profiles": [{
            "name": "Fake Custom", "endpoint": f"http://127.0.0.1:{PORT}/v1",
            "model": "fake-llm", "api_key": "prof-key-123", "enabled": True}],
        "custom_openai_active_profile": "Fake Custom",
        "custom_mt_profiles": []}},
    "api_keys": {"custom_openai": "file-key-456"},
}, indent=2, ensure_ascii=False), encoding="utf-8")

result = {"tag": "q7r", "port": PORT, "requests": REQUESTS, "checks": {}, "evidence": {}}
CHECKS = result["checks"]
EV = result["evidence"]


def check(name, cond, detail=""):
    CHECKS[name] = {"status": "PASS" if cond else "FAIL", "detail": str(detail)[:400]}
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")


def pump(seconds=1.0):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def seg(win, i):
    return win.current_project.segments[i]


win = None
try:
    win = SV.SupervertalerQt()
    for _ in range(120):
        app.processEvents()
        time.sleep(0.05)

    # ---- undo spy (counts REAL record_undo_state calls incl. guard skips) ----
    import traceback
    UNDO = []
    UNDO_TRACES = []
    _orig_record = win.record_undo_state

    def spy_record(sid, old_t, new_t, old_s, new_s):
        UNDO.append((sid, old_t, new_t, old_s, new_s))
        UNDO_TRACES.append("".join(traceback.format_stack()[-6:-1]))
        return _orig_record(sid, old_t, new_t, old_s, new_s)

    win.record_undo_state = spy_record

    # ================= A: QuickTrans panel Fetch + Ctrl+N =====================
    win.import_simple_txt()
    pump(2.0)
    win.table.selectRow(0)
    pump(0.5)
    panel = win.quicktrans_panel
    check("a_panel_exists", panel is not None, type(panel).__name__)
    panel.show()  # request_update only rebuilds rows while the panel is visible
    pump(0.3)
    panel.request_update(seg(win, 0).source, "English", "Dutch")
    pump(0.5)
    # isVisible() stays False inside an inactive tab even after show();
    # _force_refresh is the app's own ↻ path and rebuilds rows regardless.
    panel._force_refresh()
    pump(1.0)
    ai_rows = getattr(panel, '_ai_fetch_rows', [])
    check("a_ai_fetch_row_present", len(ai_rows) == 1, f"{len(ai_rows)} AI rows")
    if ai_rows:
        ai_rows[0][1].click()
        pump(2.0)
        texts = [r.current_text() for r in panel._rows]
        check("a_result_has_nbsp", any(NB in t for t in texts), repr(texts))
        _n_undo_pre_insert = len(UNDO)
        ok_ins = panel.insert_match_by_number(1)
        pump(1.0)
        t = seg(win, 0).target
        check("a_model_keeps_nbsp", NB in t, repr(t))
        # The handler only flips confirmed->draft; an 'untranslated' segment
        # keeps its status on a programmatic insert (same as before Q.7r).
        check("a_status_unchanged_by_insert", seg(win, 0).status == "untranslated",
              seg(win, 0).status)
        check("a_undo_single_raw_entry",
              sum(1 for u in UNDO if u[2] == f"Paneel{NB}vertaling{NB}NBSP") == 1
              and len(UNDO) == _n_undo_pre_insert + 1,
              repr([u[2] for u in UNDO]))
        w = win.table.cellWidget(0, 3)
        check("a_widget_shows_text", len(w.toPlainText()) > 3, repr(w.toPlainText()))

    # ================= F: idempotency (repeat the SAME insert twice) ==========
    n_undo_before = len(UNDO)
    win._insert_quicktrans_translation(f"Paneel{NB}vertaling{NB}NBSP")
    pump(0.3)
    n_after_first = len(UNDO)
    win._insert_quicktrans_translation(f"Paneel{NB}vertaling{NB}NBSP")
    pump(0.3)
    n_after_second = len(UNDO)
    t = seg(win, 0).target
    check("f_repeat_insert_no_extra_undo",
          n_after_first == n_undo_before and n_after_second == n_undo_before,
          f"{n_undo_before}->{n_after_first}->{n_after_second}")
    check("f_repeat_insert_keeps_nbsp", NB in t, repr(t))
    EV["undo_log_a_f"] = [list(u) for u in UNDO]

    # ================= B: TM inserts ==========================================
    class FakeTMDB:
        def search_all(self, source_text, tm_ids=None, max_matches=5):
            return [{"source": source_text, "target": f"TM{NB}vol{NB}zin", "match_pct": 100,
                     "tm_name": "fake", "tm_id": "fake"}]

    win.tm_database = FakeTMDB()
    win.auto_fill_100_matches = True
    UNDO.clear()
    win.table.selectRow(0)
    pump(0.2)
    # segment 0 now non-empty -> use row 0 reset: clear target first (manual clear path)
    win.table.cellWidget(0, 3).setPlainText("")
    pump(0.8)
    win.table.selectRow(0)
    pump(0.3)
    win.search_and_display_tm_matches(seg(win, 0).source)
    pump(0.8)
    t = seg(win, 0).target
    check("b_autofill_model_keeps_nbsp", NB in t, repr(t))
    EV["undo_b_autofill"] = [list(u) for u in UNDO]
    check("b_autofill_undo_once_raw", len([u for u in UNDO if u[2] == f"TM{NB}vol{NB}zin"]) == 1,
          repr([u[2] for u in UNDO]))
    check("b_autofill_status", seg(win, 0).status in ("draft", "confirmed"), seg(win, 0).status)

    UNDO.clear()
    win._auto_insert_tm_match(seg(win, 1), f"TMauto{NB}target", row=1)
    pump(0.8)
    t1 = seg(win, 1).target
    check("b_autoinsert_model_keeps_nbsp", NB in t1, repr(t1))
    EV["undo_b_autoinsert"] = [list(u) for u in UNDO]
    EV["undo_b_autoinsert_traces"] = UNDO_TRACES
    # Exactly one entry may rewrite the target (the site's own raw write);
    # every other entry must be status-only (old_target == new_target), i.e.
    # the textChanged handler must NOT re-write the model (Q.7r guard).
    rewrites = [u for u in UNDO if u[1] != u[2]]
    check("b_autoinsert_single_text_rewrite",
          len(rewrites) == 1 and rewrites[0][2] == f"TMauto{NB}target",
          repr([[u[1], u[2]] for u in UNDO]))

    # ================= C: batch LLM translation ===============================
    win.import_simple_txt()
    pump(2.0)
    rows = [(i, s) for i, s in enumerate(win.current_project.segments) if s.source.strip()]
    UNDO.clear()
    CONSOLE.clear()
    n_req0 = len(REQUESTS)
    win.translate_batch(segments_with_rows=rows, scope_description="q7r batch nbsp")
    pump(10.0)
    targets = [s.target for s in win.current_project.segments]
    check("c_batch_models_keep_nbsp", all(NB in t for t in targets), repr(targets))
    check("c_batch_statuses_draft", all(s.status == "draft" for s in win.current_project.segments),
          [s.status for s in win.current_project.segments])
    check("c_batch_requests_went_to_fake", len(REQUESTS) > n_req0, f"{len(REQUESTS) - n_req0} requests")
    EV["c_targets"] = [repr(t) for t in targets]
    EV["c_undo_n"] = len(UNDO)

    # ================= D: manual edit of neighbour char =======================
    ed = win.table.cellWidget(0, 3)
    raw_before = ed.document().toRawText()
    check("d_cell_holds_nbsp_before_edit", NB in raw_before, repr(raw_before))
    ed.setFocus()
    cur = ed.textCursor(); cur.setPosition(5); ed.setTextCursor(cur)
    UNDO.clear()
    QTest.keyClicks(ed, "X")
    pump(1.2)
    t = seg(win, 0).target
    check("d_manual_edit_keeps_nbsp", NB in t and "X" in t, repr(t))
    check("d_manual_undo_recorded", len(UNDO) >= 1, f"{len(UNDO)} undo entries")
    check("d_status_stays_draft", seg(win, 0).status == "draft", seg(win, 0).status)

    # ================= E: Ctrl+T ===============================================
    win.import_simple_txt()
    pump(2.0)
    win.table.selectRow(0)
    pump(0.5)
    UNDO.clear()
    n_req0 = len(REQUESTS)
    win.translate_current_segment()
    pump(6.0)
    t = seg(win, 0).target
    check("e_ctrlt_model_keeps_nbsp", NB in t, repr(t))
    check("e_ctrlt_status_draft", seg(win, 0).status == "draft", seg(win, 0).status)
    check("e_ctrlt_request_sent", len(REQUESTS) > n_req0, f"{len(REQUESTS) - n_req0} requests")
    EV["e_target"] = repr(t)
    EV["e_undo"] = [list(u) for u in UNDO]

    # ================= G: export keeps NBSP ===================================
    win.export_simple_txt()
    pump(1.0)
    try:
        exported = pathlib.Path(export_path).read_bytes().decode("utf-8", "replace")
    except Exception as ex:
        exported = f"<read error {ex}>"
    check("g_export_txt_keeps_nbsp", NB in exported, repr(exported[:120]))

    check("trap_network_empty", not NET_TRAPS, repr(NET_TRAPS[:3]))
    EV["modal_log_head"] = modal_log[:10]
finally:
    result["checks_summary"] = {k: v["status"] for k, v in CHECKS.items()}
    result["ok"] = all(v["status"] == "PASS" for v in CHECKS.values())
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Q7R-PROBE", "GREEN" if result["ok"] else "RED",
          f"{sum(1 for v in CHECKS.values() if v['status']=='PASS')}/{len(CHECKS)}")
    try:
        if win is not None:
            win.close()
    except Exception:
        pass
    pump(1.0)
    sys.stdout.flush()
    os._exit(0 if result["ok"] else 1)
