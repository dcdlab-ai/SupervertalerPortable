# BATCH Q-A / Q.2 probe — link-only gate in QuickTrans (panel + popup, MT + LLM).
# argv[1] = tree root, argv[2] = results JSON.
# Real call chain: QuickTransPanel/MTQuickPopup -> MTFetchWorker -> parent_app
# stub whose call_custom_mt / create_llm_client are the REAL SupervertalerQt
# methods aimed at a fake loopback OpenAI endpoint (request trap).
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


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n)
        REQUESTS.append({"path": self.path, "body": body.decode('utf-8', 'replace')[:300]})
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
    """Real methods where the fetch chain is real; nothing else."""

    def __init__(self):
        self.source_language = 'English'
        self.target_language = 'Dutch'

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


def wait_panel_idle(panel, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)
        if panel.suggestions and not any(w.isRunning() for w in panel._workers):
            pump(0.3)
            return True
    return False


def wait_popup_rows(popup, n, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)
        if len(popup.suggestion_items) >= n and not (
                popup.worker and popup.worker.isRunning()) and not getattr(popup, '_fetch_workers', []):
            pump(0.3)
            return True
    return False


def find_fetch_buttons(layout):
    from PyQt6.QtWidgets import QPushButton
    btns = []
    for i in range(layout.count()):
        w = layout.itemAt(i).widget()
        if w is not None:
            btns += [b for b in w.findChildren(QPushButton) if b.text() == 'Fetch']
    return btns


LINK1 = "![Image](y.png)"
LINK2 = "![Image](y.png)."
MIXED = "![Image](y.png) see figure two"

# ── PANEL ─────────────────────────────────────────────────────────────
try:
    stub = ParentStub()
    stub._mtql = {'mtql_custom_mt': True, 'mtql_popup_ai_autofetch': True,
                  'mtql_llm_profiles': None}
    panel = QT.QuickTransPanel(stub)
    panel.show()

    # P1: bare link
    REQUESTS.clear()
    panel.request_update(LINK1, 'English', 'Dutch')
    pump(0.6)  # debounce 300 ms
    ok = wait_panel_idle(panel)
    rows = [(s.translation, s.is_error, getattr(s, 'link_only', None)) for s in panel.suggestions]
    check("panel_link1_no_requests", len(REQUESTS) == 0, REQUESTS)
    check("panel_link1_rows", ok and len(rows) == 1
          and rows[0] == (LINK1, False, True), rows)

    # P2: link + trailing period
    REQUESTS.clear()
    panel.request_update(LINK2, 'English', 'Dutch')
    pump(0.6)
    ok = wait_panel_idle(panel)
    rows = [(s.translation, s.is_error, getattr(s, 'link_only', None)) for s in panel.suggestions]
    check("panel_link2_no_requests", len(REQUESTS) == 0, REQUESTS)
    check("panel_link2_rows", ok and len(rows) == 1
          and rows[0] == (LINK2, False, True), rows)

    # P3: mixed segment still goes to the network
    REQUESTS.clear()
    panel.request_update(MIXED, 'English', 'Dutch')
    pump(0.6)
    ok = wait_panel_idle(panel)
    rows = [(s.translation, s.is_error, getattr(s, 'link_only', None)) for s in panel.suggestions]
    check("panel_mixed_requests", len(REQUESTS) == 1, REQUESTS)
    check("panel_mixed_rows_normal", ok and len(rows) == 1 and not rows[0][2], rows)

    # P4: panel LLM Fetch button on a link-only segment
    REQUESTS.clear()
    stub._mtql = {'mtql_custom_mt': True, 'mtql_popup_ai_autofetch': True,
                  'mtql_llm_profiles': None}
    panel.request_update(LINK1, 'English', 'Dutch')
    pump(0.6)
    wait_panel_idle(panel)
    # re-fetch with LLM buttons: force refresh to rebuild rows incl. buttons
    panel._pending = (LINK1, 'English', 'Dutch')
    REQUESTS.clear()
    panel._force_refresh()
    pump(0.5)
    btns = find_fetch_buttons(panel.results_layout)
    check("panel_llm_button_present", len(btns) >= 1, len(btns))
    if btns:
        btns[0].click()
        idle = wait_panel_idle(panel)
        rows = [(s.translation, getattr(s, 'link_only', None)) for s in panel.suggestions]
        check("panel_llm_button_no_requests", len(REQUESTS) == 0, REQUESTS)
        check("panel_llm_button_row_source", idle and any(
            t == LINK1 and lo for (t, lo) in rows), rows)
    panel.close()
    panel.deleteLater()
except Exception:
    check("panel_link1_no_requests", False, traceback.format_exc())

# ── POPUP (auto-fetch MT + LLM) ───────────────────────────────────────
try:
    stub2 = ParentStub()
    stub2._mtql = {'mtql_custom_mt': True, 'mtql_popup_ai_autofetch': True,
                   'mtql_llm_profiles': None}
    REQUESTS.clear()
    popup = QT.MTQuickPopup(stub2, LINK1, 'English', 'Dutch', parent=None,
                            external_mode=True)
    ok = wait_popup_rows(popup, 2)
    rows = [(s.translation, s.is_error, getattr(s, 'link_only', None)) for s in popup.suggestions]
    check("popup_link1_no_requests", len(REQUESTS) == 0, REQUESTS)
    check("popup_link1_rows", ok and len(rows) == 2
          and all(t == LINK1 and not e and lo for (t, e, lo) in rows), rows)
    # insert path: number/Enter insert emits the SOURCE verbatim (draft)
    got = []
    popup.translation_selected.connect(got.append)
    popup._insert_selected()
    check("popup_insert_source", got == [LINK1], got)
    popup.close()
    popup.deleteLater()
    pump(0.2)
except Exception:
    check("popup_link1_no_requests", False, traceback.format_exc())

# ── POPUP (Fetch-button mode for AI) ──────────────────────────────────
try:
    stub3 = ParentStub()
    stub3._mtql = {'mtql_custom_mt': True, 'mtql_popup_ai_autofetch': False,
                   'mtql_llm_profiles': None}
    REQUESTS.clear()
    popup2 = QT.MTQuickPopup(stub3, LINK2, 'English', 'Dutch', parent=None,
                             external_mode=True)
    ok = wait_popup_rows(popup2, 1)   # only the MT row auto-fetches
    rows = [(s.translation, getattr(s, 'link_only', None)) for s in popup2.suggestions]
    check("popup_fetchmode_mt_row", ok and rows and rows[0] == (LINK2, True), rows)
    btns = find_fetch_buttons(popup2.suggestions_layout)
    check("popup_fetchmode_button_present", len(btns) == 1, len(btns))
    if btns:
        btns[0].click()
        ok2 = wait_popup_rows(popup2, 2)
        rows2 = [(s.translation, getattr(s, 'link_only', None)) for s in popup2.suggestions]
        check("popup_fetchmode_click_no_requests", len(REQUESTS) == 0, REQUESTS)
        check("popup_fetchmode_click_row", ok2 and any(
            t == LINK2 and lo for (t, lo) in rows2), rows2)
    # mixed segment in the popup still fetches
    REQUESTS.clear()
    popup2.source_text = MIXED
    popup2._reset_and_refetch()
    pump(0.5)
    ok3 = wait_popup_rows(popup2, 1)
    check("popup_mixed_requests", len(REQUESTS) == 1, REQUESTS)
    check("popup_mixed_rows_normal", ok3 and all(
        not getattr(s, 'link_only', False) for s in popup2.suggestions),
        [(s.translation, getattr(s, 'link_only', None)) for s in popup2.suggestions])
    popup2.close()
    popup2.deleteLater()
    pump(0.2)
except Exception:
    check("popup_fetchmode_mt_row", False, traceback.format_exc())

RESULTS["_meta"] = {"tree": TREE, "port": PORT, "total_requests": len(REQUESTS)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
srv.shutdown()
os._exit(0)
