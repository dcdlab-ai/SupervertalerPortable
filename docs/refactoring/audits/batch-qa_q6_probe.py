# BATCH Q-A / Q.6 probe — cooperative cancel on QuickTrans close.
# argv[1] = tree root, argv[2] = results JSON.
# Fake endpoint with a configurable delay; close the popup/panel WHILE a
# request is in flight; assert: close is fast, no late result lands in the UI,
# no Python exceptions, detached QThreads finish and get cleaned up.
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
DELAY = [1.5]   # mutable: seconds the endpoint holds each request


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


from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

import modules.quicktrans as QT


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def running_workers(panel_or_popup):
    ws = []
    w = getattr(panel_or_popup, 'worker', None)
    if w is not None:
        ws.append(w)
    ws += list(getattr(panel_or_popup, '_fetch_workers', []) or [])
    ws += list(getattr(panel_or_popup, '_workers', []) or [])
    return ws


# ── S1: popup closed while the auto-fetch (MT + LLM) is in flight ─────
try:
    DELAY[0] = 1.5
    stub = ParentStub()
    popup = QT.MTQuickPopup(stub, "Hello world", 'English', 'Dutch',
                            parent=None, external_mode=True)
    # wait until at least one request is in flight on a running worker
    deadline = time.time() + 5
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if any(w.isRunning() for w in running_workers(popup)) and REQUESTS:
            break
    in_flight = any(w.isRunning() for w in running_workers(popup))
    wref = popup.worker
    wrefs = list(running_workers(popup))
    emitted = []
    popup.translation_selected.connect(emitted.append)
    t0 = time.time()
    popup.close()
    close_dt = time.time() - t0
    pump(4.0)   # let the delayed requests complete
    check("popup_close_while_inflight", in_flight, {"requests": len(REQUESTS)})
    check("popup_close_fast", close_dt < 0.5, f"{close_dt:.3f}s")
    check("popup_closed_flag", bool(getattr(popup, '_closed', None)),
          getattr(popup, '_closed', 'attr missing (pre)'))
    check("popup_no_late_result", len(popup.suggestions) == 0,
          [(s.translation, s.is_error) for s in popup.suggestions])
    check("popup_no_insert_after_close", emitted == [], emitted)
    finished = all(not w.isRunning() for w in wrefs)
    check("popup_threads_finished", finished,
          [(id(w), w.isRunning()) for w in wrefs])
    det = getattr(QT, '_DETACHED_WORKERS', None)
    check("popup_detached_registry_empty",
          det is not None and len(det) == 0, det is not None and len(det) or 'attr missing (pre)')
    popup.deleteLater()
    pump(0.2)
except Exception:
    check("popup_close_while_inflight", False, traceback.format_exc())

# ── S2: docked panel closed while the MT auto-fetch is in flight ──────
try:
    DELAY[0] = 1.5
    stub2 = ParentStub()
    panel = QT.QuickTransPanel(stub2)
    panel.show()
    panel.request_update("Hello world", 'English', 'Dutch')
    deadline = time.time() + 5
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if panel._workers and any(w.isRunning() for w in panel._workers) and REQUESTS:
            break
    in_flight = panel._workers and any(w.isRunning() for w in panel._workers)
    wrefs = list(panel._workers)
    t0 = time.time()
    panel.close()
    close_dt = time.time() - t0
    pump(4.0)
    check("panel_close_while_inflight", bool(in_flight), {"requests": len(REQUESTS)})
    check("panel_close_fast", close_dt < 0.5, f"{close_dt:.3f}s")
    check("panel_closed_flag", bool(getattr(panel, '_closed', None)),
          getattr(panel, '_closed', 'attr missing (pre)'))
    check("panel_no_late_result", len(panel.suggestions) == 0,
          [(s.translation, s.is_error) for s in panel.suggestions])
    finished = all(not w.isRunning() for w in wrefs)
    check("panel_threads_finished", finished,
          [(id(w), w.isRunning()) for w in wrefs])
    det = getattr(QT, '_DETACHED_WORKERS', None)
    check("panel_detached_registry_empty",
          det is not None and len(det) == 0, det is not None and len(det) or 'attr missing (pre)')
    panel.deleteLater()
    pump(0.2)
except Exception:
    check("panel_close_while_inflight", False, traceback.format_exc())

# ── S3: popup LLM Fetch-button worker closed mid-request ──────────────
try:
    DELAY[0] = 0.0   # the initial MT auto row settles immediately
    stub3 = ParentStub()
    stub3._mtql['mtql_popup_ai_autofetch'] = False
    REQUESTS.clear()
    popup2 = QT.MTQuickPopup(stub3, "Another text", 'English', 'Dutch',
                             parent=None, external_mode=True)
    deadline = time.time() + 5
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
        if len(popup2.suggestion_items) >= 1 and not running_workers(popup2):
            break
    pump(0.3)
    from PyQt6.QtWidgets import QPushButton
    btns = []
    for i in range(popup2.suggestions_layout.count()):
        w = popup2.suggestions_layout.itemAt(i).widget()
        if w is not None:
            btns += [b for b in w.findChildren(QPushButton) if b.text() == 'Fetch']
    check("s3_button_present", len(btns) == 1, len(btns))
    if btns:
        DELAY[0] = 1.5
        btns[0].click()
        deadline = time.time() + 5
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.02)
            if getattr(popup2, '_fetch_workers', []) and any(
                    w.isRunning() for w in popup2._fetch_workers):
                break
        in_flight = bool(getattr(popup2, '_fetch_workers', [])) and any(
            w.isRunning() for w in popup2._fetch_workers)
        wrefs = list(popup2._fetch_workers)
        t0 = time.time()
        popup2.close()
        close_dt = time.time() - t0
        pump(4.0)
        check("s3_close_while_inflight", in_flight, {"requests": len(REQUESTS)})
        check("s3_close_fast", close_dt < 0.5, f"{close_dt:.3f}s")
        check("s3_no_late_result", len(popup2.suggestions) == 1,
              [(s.translation, s.is_error) for s in popup2.suggestions])
        finished = all(not w.isRunning() for w in wrefs)
        check("s3_threads_finished", finished,
              [(id(w), w.isRunning()) for w in wrefs])
        det = getattr(QT, '_DETACHED_WORKERS', None)
        check("s3_detached_registry_empty",
              det is not None and len(det) == 0, det is not None and len(det) or 'attr missing (pre)')
    popup2.deleteLater()
    pump(0.2)
except Exception:
    check("s3_button_present", False, traceback.format_exc())

RESULTS["_meta"] = {"tree": TREE, "port": PORT, "total_requests": len(REQUESTS)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
srv.shutdown()
os._exit(0)
