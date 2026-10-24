# BATCH Q-B / Q.3 probe — panel QuickTrans: no auto-request, per-profile MT
# Fetch rows, block "Fetch all", result bound to segment, link-only rows.
# argv[1] = tree root, argv[2] = results JSON.
# Real call chain: QuickTransPanel -> _get_enabled_providers -> MTFetchWorker
# -> parent_app stub whose call_custom_mt / create_llm_client are the REAL
# SupervertalerQt methods aimed at fake loopback OpenAI endpoints (two
# servers with distinct responses so the endpoint routing is observable).
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

# Two fake endpoints; each answers with its own marker and records requests.
SERVERS = {}   # 'A' | 'B' -> {"requests": [...], "delay": float}


def make_handler(tag):
    class FakeHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(n)
            srv = SERVERS[tag]
            srv["requests"].append({"path": self.path, "body": body.decode('utf-8', 'replace')[:200]})
            if srv["delay"] > 0:
                time.sleep(srv["delay"])
            resp = {"id": f"chatcmpl-{tag}", "object": "chat.completion", "created": 0,
                    "model": "m", "choices": [{"index": 0,
                    "message": {"role": "assistant", "content": f"TRANSLATED-{tag}"},
                    "finish_reason": "stop"}]}
            data = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass
    return FakeHandler


BASES = {}
for tag in ('A', 'B'):
    SERVERS[tag] = {"requests": [], "delay": 0.0}
    srv = HTTPServer(('127.0.0.1', 0), make_handler(tag))
    BASES[tag] = f"http://127.0.0.1:{srv.server_address[1]}/v1"
    threading.Thread(target=srv.serve_forever, daemon=True).start()


def total_requests():
    return len(SERVERS['A']["requests"]) + len(SERVERS['B']["requests"])


import Supervertaler as SV
SQ = SV.SupervertalerQt


class ParentStub:
    """Real methods where the fetch chain is real; nothing else."""

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
                {'name': 'MT prof A', 'endpoint': BASES['A'], 'model': 'm',
                 'api_key': '', 'raw_mode': True, 'enabled': True},
                {'name': 'MT prof B', 'endpoint': BASES['B'], 'model': 'm',
                 'api_key': '', 'raw_mode': True, 'enabled': True},
                # enabled but no endpoint -> must NOT become a row
                {'name': 'MT no endpoint', 'endpoint': '', 'model': 'm',
                 'api_key': '', 'raw_mode': True, 'enabled': True},
                # endpoint but disabled -> must NOT become a row
                {'name': 'MT disabled', 'endpoint': BASES['A'], 'model': 'm',
                 'api_key': '', 'raw_mode': True, 'enabled': False},
            ],
            'custom_openai_profiles': [
                {'name': 'LLM prof', 'endpoint': BASES['A'], 'model': 'm',
                 'api_key': '', 'supports_vision': False}],
        }


from PyQt6.QtWidgets import QApplication, QPushButton, QLabel, QFrame
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


def fetch_buttons():
    """(chip_name, btn) for every live Fetch row, in visual order."""
    out = []
    panel = PANEL[0]
    for i in range(panel.results_layout.count()):
        w = panel.results_layout.itemAt(i).widget()
        if w is None:
            continue
        btns = [b for b in w.findChildren(QPushButton) if b.text() in ('Fetch', '…')]
        if btns:
            chips = [l.text() for l in w.findChildren(QLabel)
                     if l.text() in ('MT prof A', 'MT prof B', 'MT no endpoint',
                                     'MT disabled', 'LLM prof')]
            out.append((chips[0] if chips else '?', btns[0]))
    return out


def fetch_all_buttons():
    panel = PANEL[0]
    return [b for b in panel.findChildren(QPushButton) if b.text() == 'Fetch all']


def row_texts():
    panel = PANEL[0]
    return [(s.provider_name, s.translation, s.is_error, s.link_only)
            for s in panel.suggestions]


PANEL = []
LINK = "![Image](y.png)"

try:
    stub = ParentStub()
    panel = QT.QuickTransPanel(stub)
    PANEL.append(panel)
    panel.show()

    # ── 1. three selections in a row — zero network requests ──────────
    for text in ("First segment", "Second segment", "Third segment"):
        panel.request_update(text, 'English', 'Dutch')
        pump(0.6)  # panel debounce is 300 ms
    pump(0.5)
    check("q3_sel3_no_requests", total_requests() == 0,
          {"A": len(SERVERS['A']["requests"]), "B": len(SERVERS['B']["requests"])})

    # ── 2. initial rows: one Fetch row per enabled provider ───────────
    fb = fetch_buttons()
    names = [n for n, _b in fb]
    check("q3_rows_initial", names == ['MT prof A', 'MT prof B', 'LLM prof'],
          {"names": names, "workers": len(panel._workers)})
    check("q3_no_endpoint_or_disabled_hidden",
          'MT no endpoint' not in names and 'MT disabled' not in names, names)
    check("q3_no_result_rows_yet", len(panel.suggestions) == 0, row_texts())

    # ── 3. both block headers carry a Fetch all button ────────────────
    fa = fetch_all_buttons()
    check("q3_fetch_all_buttons", len(fa) == 2, [b.text() for b in fa])

    # ── 4. Fetch on ONE MT row: exactly 1 request, to that profile ────
    btn_a = next(b for n, b in fb if n == 'MT prof A')
    btn_a.click()
    ok = wait_until(lambda: len(panel.suggestions) == 1 and not panel._workers)
    rows = row_texts()
    check("q3_fetch_one_result", ok and rows == [('MT prof A', 'TRANSLATED-A', False, False)], rows)
    check("q3_fetch_one_request_routed",
          len(SERVERS['A']["requests"]) == 1 and len(SERVERS['B']["requests"]) == 0,
          {"A": len(SERVERS['A']["requests"]), "B": len(SERVERS['B']["requests"])})

    # ── 5. Fetch all (MT block): remaining enabled MT rows fire ────────
    SERVERS['A']["requests"].clear()
    SERVERS['B']["requests"].clear()
    mt_fetch_all = fa[0]
    mt_fetch_all.click()
    ok = wait_until(lambda: len(panel.suggestions) == 2 and not panel._workers)
    rows = row_texts()
    check("q3_fetch_all_mt_rows",
          ok and sorted(r[0] for r in rows) == ['MT prof A', 'MT prof B']
          and any(r[1] == 'TRANSLATED-B' for r in rows), rows)
    check("q3_fetch_all_mt_requests",
          len(SERVERS['A']["requests"]) == 0 and len(SERVERS['B']["requests"]) == 1,
          {"A": len(SERVERS['A']["requests"]), "B": len(SERVERS['B']["requests"]),
           "llm_row_still_unfetched": [n for n, b in fetch_buttons()]})

    # ── 6. AI block Fetch all: the LLM row fires once ──────────────────
    SERVERS['A']["requests"].clear()
    ai_fetch_all = fa[1]
    ai_fetch_all.click()
    ok = wait_until(lambda: len(panel.suggestions) == 3 and not panel._workers)
    rows = row_texts()
    check("q3_fetch_all_ai_rows", ok and any(
        r[0] == 'LLM prof' and r[1] == 'TRANSLATED-A' for r in rows), rows)
    check("q3_fetch_all_ai_requests", len(SERVERS['A']["requests"]) == 1,
          len(SERVERS['A']["requests"]))

    # ── 7. selection change after Fetch: old results discarded, rows
    #      reset to "press Fetch" state; an in-flight answer is dropped ─
    SERVERS['A']["requests"].clear()
    SERVERS['B']["requests"].clear()
    # move to a fresh segment so the rows reset to their initial state
    panel.request_update("Segment for the stale test", 'English', 'Dutch')
    pump(0.6)
    SERVERS['B']["delay"] = 1.5
    fb = fetch_buttons()
    btn_b = next(b for n, b in fb if n == 'MT prof B')
    btn_b.click()
    in_flight = wait_until(lambda: any(w.isRunning() for w in panel._workers), 3.0)
    panel.request_update("Another segment entirely", 'English', 'Dutch')
    pump(0.6)  # debounce + rebuild
    check("q3_stale_inflight_dropped",
          in_flight and total_requests() == 1 and len(panel.suggestions) == 0,
          {"in_flight": in_flight, "requests": total_requests(), "rows": row_texts()})
    fb = fetch_buttons()
    names = [n for n, _b in fb]
    check("q3_rows_reset_after_change", names == ['MT prof A', 'MT prof B', 'LLM prof'], names)
    ok = wait_until(lambda: not panel._workers, 5.0)
    pump(0.4)
    check("q3_late_answer_not_shown",
          ok and len(panel.suggestions) == 0 and total_requests() == 1,
          {"workers_left": len(panel._workers), "rows": row_texts(),
           "requests": total_requests()})

    # ── 8. link-only segment: rows with source + marker, no network ───
    SERVERS['A']["requests"].clear()
    SERVERS['B']["requests"].clear()
    panel.request_update(LINK, 'English', 'Dutch')
    pump(0.6)
    rows = row_texts()
    check("q3_linkonly_rows",
          len(rows) == 3 and all(t == LINK and not e and lo
                                 for (_n, t, e, lo) in rows), rows)
    check("q3_linkonly_no_requests", total_requests() == 0,
          {"A": len(SERVERS['A']["requests"]), "B": len(SERVERS['B']["requests"])})
    check("q3_linkonly_no_fetchall", len(fetch_all_buttons()) == 0,
          len(fetch_all_buttons()))

    panel.close()
    panel.deleteLater()
    pump(0.2)
except Exception:
    check("q3_probe_crashed", False, traceback.format_exc())

RESULTS["_meta"] = {"tree": TREE,
                    "bases": dict(BASES),
                    "requests": {k: len(v["requests"]) for k, v in SERVERS.items()}}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
os._exit(0)
