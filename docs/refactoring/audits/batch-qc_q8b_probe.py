# -*- coding: utf-8 -*-
"""BATCH Q-C / Q.8b probe — connect timeout 15 s + LLMConnectionError + SDK
retry split. Runs identically on the pre-Q.8b and post-Q.8b trees; the JSON
records behaviour so the two runs can be diffed.

S1 fake-200 endpoint: one translate call; sha256 of the request BODY
   (byte-identity across trees) + model/params.
S2 network matrix: TEST-NET default timeout / closed port / silent server
   (3 s profile): wall time, exception class, cause, message.
S3 QuickTrans rows (real panel + stub parent): MT row dead localhost
   (legacy '[MT proxy not running. Start it.]'), LLM row dead REMOTE host
   (new one-line message, single brackets — Q.8a probe requirement).
S4 5xx retries preserved: fake endpoint answers 500,500,200 -> success on
   the 3rd attempt (3 requests total).
"""
import hashlib, json, os, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TREE = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
os.chdir(TREE)
sys.path.insert(0, TREE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['TEMP'] = os.path.dirname(OUT)
os.environ['TMP'] = os.path.dirname(OUT)

NET_TRAPS = []
_real_connect = socket.socket.connect


def _trapped_connect(self, address, *a, **k):
    if isinstance(address, tuple) and len(address) >= 2:
        host = address[0]
        # 192.0.2.1 (TEST-NET-1) is this probe's deliberate target, not a leak
        if (isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost")
                and host != "192.0.2.1"):
            NET_TRAPS.append(str(address))
    return _real_connect(self, address, *a, **k)


socket.socket.connect = _trapped_connect

MODE = {"n": 0}
BODIES = []


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        MODE["n"] += 1
        BODIES.append(raw)
        if MODE["n"] <= 2:
            data = json.dumps({"error": {"message": "simulated 500"}}).encode()
            self.send_response(500)
        else:
            content = "Goedemorgen"
            resp = {"id": "x", "object": "chat.completion", "created": 1, "model": "m",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
            data = json.dumps(resp).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

from modules.llm_clients import LLMClient  # noqa: E402

R = {"tag": "q8b", "port": PORT, "checks": {}, "evidence": {}}
C = R["checks"]
EV = R["evidence"]


def check(name, cond, detail=""):
    C[name] = {"status": "PASS" if cond else "FAIL", "detail": str(detail)[:400]}
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")


def call(endpoint, timeout_minutes=None):
    timeout_s = None if timeout_minutes is None else timeout_minutes * 60.0
    client = LLMClient(api_key="probe", provider="custom_openai", model="probe-model",
                       base_url=endpoint, timeout_seconds=timeout_s,
                       profile_name="Probe profile")
    t0 = time.perf_counter()
    try:
        res = client.translate(text="hi", source_lang="en", target_lang="nl")
        return {"outcome": "returned", "result": res, "wall": round(time.perf_counter() - t0, 1)}
    except Exception as e:
        cause = getattr(e, "__cause__", None)
        return {"outcome": "raised", "exc": type(e).__name__,
                "exc_module": type(e).__module__,
                "cause": (type(cause).__name__ if cause else None),
                "msg": str(e)[:300], "wall": round(time.perf_counter() - t0, 1)}


# ---- S1 + S4: fake endpoint; 500,500,200 -> 3rd attempt succeeds ----------
ok = call(f"http://127.0.0.1:{PORT}/v1")
EV["s1"] = ok
EV["s1_body_sha256"] = hashlib.sha256(BODIES[0]).hexdigest() if BODIES else None
check("s4_5xx_retried_to_success", ok["outcome"] == "returned" and len(BODIES) == 3,
      f"outcome={ok.get('outcome')} requests={len(BODIES)}")

# ---- S2: network matrix ----------------------------------------------------
EV["s2_testnet_default"] = call("http://192.0.2.1:65500/v1", None)
time.sleep(0.2)
EV["s2_refused"] = call("http://127.0.0.1:1/v1", 0.05)

silent = socket.socket()
silent.bind(("127.0.0.1", 0))
silent.listen(8)
SILENT_PORT = silent.getsockname()[1]
_conns = []


def _hold():
    while True:
        try:
            c, _ = silent.accept()
            _conns.append(c)
        except OSError:
            return


threading.Thread(target=_hold, daemon=True).start()
EV["s2_silent_read"] = call(f"http://127.0.0.1:{SILENT_PORT}/v1", 0.05)

# ---- S2 checks (new Q.8b expectations) --------------------------------------
_td = EV["s2_testnet_default"]
check("s2_testnet_default_conn_error",
      _td.get("exc") == "LLMConnectionError" and _td.get("wall", 999) <= 20,
      f"exc={_td.get('exc')} wall={_td.get('wall')}")
check("s2_testnet_default_message",
      "Cannot connect to 192.0.2.1:65500 within 15 s" in _td.get("msg", "")
      and "host unreachable or server stopped" in _td.get("msg", "")
      and "profile 'Probe profile'" in _td.get("msg", ""),
      repr(_td.get("msg", ""))[:200])
_rf = EV["s2_refused"]
check("s2_refused_fast_conn_error",
      _rf.get("exc") == "LLMConnectionError" and _rf.get("wall", 999) <= 5,
      f"exc={_rf.get('exc')} wall={_rf.get('wall')}")
_sr = EV["s2_silent_read"]
check("s2_silent_read_timeout_preserved",
      _sr.get("exc") == "LLMTimeoutError"
      and "timed out after 0.05 minutes (3 s)" in _sr.get("msg", "")
      and 8 <= _sr.get("wall", 0) <= 15,
      f"exc={_sr.get('exc')} wall={_sr.get('wall')} msg={_sr.get('msg','')[:80]}")

# ---- S3: QuickTrans rows (panel + stub) -------------------------------------
from PyQt6.QtWidgets import QApplication  # noqa: E402
app = QApplication.instance() or QApplication([])
import Supervertaler as SV  # noqa: E402
SQ = SV.SupervertalerQt


class ParentStub:
    def __init__(self, llm_endpoint, mt_endpoint):
        self._llm_ep = llm_endpoint
        self._mt_ep = mt_endpoint

    load_api_keys = lambda self: {}
    load_provider_enabled_states = lambda self: {}
    call_custom_mt = SQ.call_custom_mt
    create_llm_client = SQ.create_llm_client
    _custom_llm_ready = SQ._custom_llm_ready
    _get_active_custom_profile = SQ._get_active_custom_profile
    _custom_profile_request_kwargs = SQ._custom_profile_request_kwargs
    _normalize_custom_endpoint = staticmethod(SQ._normalize_custom_endpoint)
    _get_proxy_url = lambda self: None

    def log(self, msg):
        pass

    def load_general_settings(self):
        return {'mt_quick_lookup': {'mtql_custom_mt': True, 'mtql_llm_profiles': None}}

    def load_llm_settings(self):
        return {
            'custom_mt_profiles': [
                {'name': 'MT dead', 'endpoint': self._mt_ep, 'model': 'm',
                 'api_key': '', 'raw_mode': True, 'enabled': True}],
            'custom_openai_profiles': [
                {'name': 'LLM dead', 'endpoint': self._llm_ep, 'model': 'm',
                 'api_key': '', 'supports_vision': False}],
            'custom_openai_active_profile': 'LLM dead',
        }


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


# MT row: dead LOCALHOST port -> legacy text must stay
stub = ParentStub("http://127.0.0.1:1/v1", "http://127.0.0.1:1/v1")
from modules.quicktrans import QuickTransPanel  # noqa: E402
panel = QuickTransPanel(stub)
panel.show()
panel.request_update('hello world', 'English', 'Dutch')
pump(0.4)
panel._force_refresh()
pump(0.4)
EV["s3_mt_rows"] = len(panel._mt_fetch_rows)
if panel._mt_fetch_rows:
    panel._mt_fetch_rows[0][1].click()
    pump(3.0)
    texts = [r.current_text() for r in panel._rows]
    EV["s3_mt_row_text"] = texts
    check("s3_mt_localhost_legacy_text", any("[MT proxy not running. Start it.]" == t for t in texts),
          repr(texts))

# LLM row: dead REMOTE host (TEST-NET) -> new one-line message, single brackets
panel2 = QuickTransPanel(ParentStub("http://192.0.2.1:65500/v1", "http://127.0.0.1:1/v1"))
panel2.show()
panel2.request_update('hello world', 'English', 'Dutch')
pump(0.4)
panel2._force_refresh()
pump(0.4)
EV["s3_llm_rows"] = len(panel2._ai_fetch_rows)
if panel2._ai_fetch_rows:
    t0 = time.perf_counter()
    panel2._ai_fetch_rows[0][1].click()
    pump(25.0)
    texts = [r.current_text() for r in panel2._rows]
    EV["s3_llm_row_text"] = texts
    EV["s3_llm_wall"] = round(time.perf_counter() - t0, 1)
    one = texts[0] if texts else ""
    check("s3_llm_remote_single_brackets",
          one.startswith("[Error:") and one.endswith("]") and not one.startswith("[["),
          repr(one))
    check("s3_llm_remote_new_message", "Cannot connect to 192.0.2.1:65500 within 15 s" in one
          and "host unreachable or server stopped" in one and "profile 'LLM dead'" in one,
          repr(one))

check("trap_network_empty", not NET_TRAPS, repr(NET_TRAPS[:3]))

R["ok"] = all(v["status"] == "PASS" for v in C.values())
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=1)
print("Q8B-PROBE", "GREEN" if R["ok"] else "RED",
      f"{sum(1 for v in C.values() if v['status']=='PASS')}/{len(C)}")
sys.stdout.flush()
os._exit(0 if R["ok"] else 1)
