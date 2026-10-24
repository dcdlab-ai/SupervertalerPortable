# BATCH Q-B regression probe — ADAPTED panel equivalents of the Q-A probe
# checks whose panel behavior Q.3/Q.4 changed by design (the popup halves of
# the Q-A probes pass unchanged; see batch-qb_qa_*_after_qb.json).
# argv[1] = tree root, argv[2] = results JSON.
#
# Original check -> adapted equivalent:
#   q2.panel_link1_rows / panel_link2_rows
#       old: 1 auto MT link-only row.   new: link-only rows for EVERY enabled
#       profile (MT + LLM), source verbatim + marker, 0 requests.
#   q2.panel_mixed_requests / panel_mixed_rows_normal
#       old: 1 auto request, 1 normal row.  new: 0 auto requests, 0 result
#       rows, fetch rows shown; pressing Fetch on the mixed segment DOES hit
#       the network and produces a normal (non-link-only) row.
#   q2.panel_llm_button_present (+ the two button checks that never ran)
#       old: LLM Fetch button on a link-only segment.  new: no Fetch buttons
#       at all — the LLM link-only row is already there (with the source).
#   q6.panel_close_while_inflight (S2)
#       old: close during the AUTO MT fetch.  new: no auto fetch exists; the
#       same scenario runs through a Fetch button (close mid-request).
import os, sys, json, time, threading, traceback

TREE = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
os.chdir(TREE)
sys.path.insert(0, TREE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
STAGE_TMP = os.path.dirname(OUT)
os.environ['TEMP'] = STAGE_TMP
os.environ['TMP'] = STAGE_TMP

RESULTS = {}


def check(name, cond, detail=""):
    RESULTS[name] = {"status": "PASS" if cond else "FAIL", "detail": str(detail)[:500]}


from http.server import BaseHTTPRequestHandler, HTTPServer

REQUESTS = []
DELAY = [0.0]


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n)
        REQUESTS.append({"path": self.path, "body": body.decode('utf-8', 'replace')[:200]})
        if DELAY[0] > 0:
            time.sleep(DELAY[0])
        resp = {"id": "chatcmpl-1", "object": "chat.completion", "created": 0,
                "model": "m", "choices": [{"index": 0,
                "message": {"role": "assistant", "content": "TRANSLATED-OK"},
                "finish_reason": "stop"}]}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


srv = HTTPServer(('127.0.0.1', 0), FakeHandler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{PORT}/v1"

import Supervertaler as SV
SQ = SV.SupervertalerQt


class ParentStub:
    def __init__(self):
        self.source_language = 'English'
        self.target_language = 'Dutch'
        self._mtql = {'mtql_custom_mt': True, 'mtql_popup_ai_autofetch': True,
                      'mtql_llm_profiles': None}

    load_api_keys = lambda self: {}
    load_provider_enabled_states = lambda self: {}
    call_custom_mt = SQ.call_custom_mt
    create_llm_client = SQ.create_llm_client
    _get_active_custom_profile = SQ._get_active_custom_profile
    _custom_profile_request_kwargs = SQ._custom_profile_request_kwargs
    _normalize_custom_endpoint = staticmethod(SQ._normalize_custom_endpoint)
    _get_proxy_url = lambda self: None

    def log(self, msg):
        pass

    def load_general_settings(self):
        return {'mt_quick_lookup': dict(self._mtql)}

    def load_llm_settings(self):
        return {
            'custom_mt_profiles': [
                {'name': 'Local proxy', 'endpoint': BASE, 'model': 'm',
                 'api_key': '', 'raw_mode': True, 'enabled': True}],
            'custom_openai_profiles': [
                {'name': 'LLM prof', 'endpoint': BASE, 'model': 'm',
                 'api_key': '', 'supports_vision': False}],
        }


from PyQt6.QtWidgets import QApplication, QPushButton
app = QApplication.instance() or QApplication([])

import modules.quicktrans as QT


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def wait_until(pred, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)
        if pred():
            pump(0.2)
            return True
    return False


def fetch_buttons(panel):
    out = []
    for i in range(panel.results_layout.count()):
        w = panel.results_layout.itemAt(i).widget()
        if w is None:
            continue
        out += [b for b in w.findChildren(QPushButton) if b.text() in ('Fetch', '…')]
    return out


LINK1 = "![Image](y.png)"
LINK2 = "![Image](y.png)."
MIXED = "![Image](y.png) see figure two"

# ── A1/A2: link-only rows for every enabled profile, no network ────────
try:
    stub = ParentStub()
    panel = QT.QuickTransPanel(stub)
    panel.show()

    for tag, text in (("link1", LINK1), ("link2", LINK2)):
        REQUESTS.clear()
        panel.request_update(text, 'English', 'Dutch')
        pump(0.6)
        rows = [(s.provider_name, s.translation, s.is_error, getattr(s, 'link_only', None))
                for s in panel.suggestions]
        check(f"adapt_panel_{tag}_no_requests", len(REQUESTS) == 0, REQUESTS)
        check(f"adapt_panel_{tag}_rows",
              len(rows) == 2 and all(t == text and not e and lo for (_n, t, e, lo) in rows)
              and {r[0] for r in rows} == {'Local proxy', 'LLM prof'}, rows)
        # no Fetch buttons: the rows are already results
        check(f"adapt_panel_{tag}_no_buttons",
              len(fetch_buttons(panel)) == 0, len(fetch_buttons(panel)))
    panel.close()
    panel.deleteLater()
    pump(0.2)
except Exception:
    check("adapt_panel_link1_rows", False, traceback.format_exc())

# ── A3: mixed segment — no AUTO request; Fetch works and is a normal row ─
try:
    stub2 = ParentStub()
    panel2 = QT.QuickTransPanel(stub2)
    panel2.show()
    REQUESTS.clear()
    panel2.request_update(MIXED, 'English', 'Dutch')
    pump(0.6)
    pump(0.5)
    check("adapt_panel_mixed_no_auto_requests", len(REQUESTS) == 0, REQUESTS)
    check("adapt_panel_mixed_rows_empty", len(panel2.suggestions) == 0,
          [(s.translation, s.link_only) for s in panel2.suggestions])
    btns = fetch_buttons(panel2)
    check("adapt_panel_mixed_fetch_rows", len(btns) == 2, len(btns))
    if btns:
        btns[0].click()
        ok = wait_until(lambda: len(panel2.suggestions) == 1 and not panel2._workers)
        rows = [(s.translation, s.is_error, getattr(s, 'link_only', None))
                for s in panel2.suggestions]
        check("adapt_panel_mixed_fetch_requests", len(REQUESTS) == 1, REQUESTS)
        check("adapt_panel_mixed_fetch_row_normal",
              ok and rows == [("TRANSLATED-OK", False, False)], rows)
    panel2.close()
    panel2.deleteLater()
    pump(0.2)
except Exception:
    check("adapt_panel_mixed_no_auto_requests", False, traceback.format_exc())

# ── A4 (q6 S2 adapted): close mid-request started via a Fetch button ────
try:
    DELAY[0] = 1.5
    stub3 = ParentStub()
    panel3 = QT.QuickTransPanel(stub3)
    panel3.show()
    panel3.request_update("Hello world", 'English', 'Dutch')
    pump(0.6)
    btns = fetch_buttons(panel3)
    check("adapt_q6_fetch_row_present", len(btns) >= 1, len(btns))
    if btns:
        btns[0].click()
        in_flight = wait_until(lambda: any(w.isRunning() for w in panel3._workers), 3.0)
        wrefs = list(panel3._workers)
        t0 = time.time()
        panel3.close()
        close_dt = time.time() - t0
        pump(4.0)
        check("adapt_q6_close_while_inflight", in_flight, {"requests": len(REQUESTS)})
        check("adapt_q6_close_fast", close_dt < 0.5, f"{close_dt:.3f}s")
        check("adapt_q6_closed_flag", bool(getattr(panel3, '_closed', None)),
              getattr(panel3, '_closed', 'attr missing'))
        check("adapt_q6_no_late_result", len(panel3.suggestions) == 0,
              [(s.translation, s.is_error) for s in panel3.suggestions])
        finished = all(not w.isRunning() for w in wrefs)
        check("adapt_q6_threads_finished", finished,
              [(id(w), w.isRunning()) for w in wrefs])
        det = getattr(QT, '_DETACHED_WORKERS', None)
        check("adapt_q6_detached_registry_empty",
              det is not None and len(det) == 0,
              det is not None and len(det) or 'attr missing')
    panel3.deleteLater()
    pump(0.2)
except Exception:
    check("adapt_q6_close_while_inflight", False, traceback.format_exc())

RESULTS["_meta"] = {"tree": TREE, "port": PORT, "total_requests": len(REQUESTS)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
srv.shutdown()
os._exit(0)
