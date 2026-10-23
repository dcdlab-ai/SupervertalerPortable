# BATCH Q-A / Q.1 probe — MT-profile request fields + error surfacing.
# Runs against a tree root passed as argv[1]; writes JSON results to argv[2].
# Fake loopback OpenAI endpoint captures raw request bodies (byte-identical
# pre/post comparison), plus typed-error and save-handler scenarios.
import os, sys, json, hashlib, threading, time, base64, traceback

TREE = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
os.chdir(TREE)
sys.path.insert(0, TREE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
STAGE_TMP = os.path.dirname(OUT)
os.environ['TEMP'] = STAGE_TMP
os.environ['TMP'] = STAGE_TMP

RESULTS = {}
LOG = []


def check(name, cond, detail=""):
    RESULTS[name] = {"status": "PASS" if cond else "FAIL", "detail": str(detail)[:600]}


def skip(name, why):
    RESULTS[name] = {"status": "SKIP", "detail": str(why)[:300]}


# ── fake OpenAI endpoint ─────────────────────────────────────────────
from http.server import BaseHTTPRequestHandler, HTTPServer

CAPTURED = []


class FakeHandler(BaseHTTPRequestHandler):
    mode = "ok"        # ok | length | sleep
    sleep_s = 2.0

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n)
        CAPTURED.append({"path": self.path, "body": body})
        if FakeHandler.mode == "sleep":
            time.sleep(FakeHandler.sleep_s)
            self.send_response(500)
            self.send_header('Content-Length', '2')
            self.end_headers()
            self.wfile.write(b'{}')
            return
        if FakeHandler.mode == "length":
            content, finish = "Trans lated partial", "length"
        else:
            content, finish = "TRANSLATED-OK", "stop"
        resp = {"id": "chatcmpl-1", "object": "chat.completion", "created": 0,
                "model": "m", "choices": [{"index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish}]}
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

# ── import app class, build stub ─────────────────────────────────────
import Supervertaler as SV
SQ = SV.SupervertalerQt


class Stub:
    load_api_keys = lambda self: {}

    def log(self, msg):
        LOG.append(str(msg))

    _custom_profile_request_kwargs = SQ._custom_profile_request_kwargs
    _validate_custom_profiles = SQ._validate_custom_profiles
    _normalize_custom_endpoint = staticmethod(SQ._normalize_custom_endpoint)
    tr = lambda self, s, *a, **k: s


stub = Stub()


def mt_call(profile):
    return SQ.call_custom_mt(stub, "Hello world", "English", "Dutch", profile)


def body_of(idx):
    return CAPTURED[idx]["body"]


def profile_with(**extra):
    p = {"name": "Local proxy", "endpoint": BASE, "model": "m",
         "api_key": "", "raw_mode": True, "enabled": True}
    p.update(extra)
    return p


# ── 1. old-format profile (no new fields): call + captured body ──────
try:
    old = profile_with()
    res = mt_call(old)
    b = body_of(-1)
    check("old_profile_result", res == "TRANSLATED-OK", res)
    check("old_profile_request_count_1", len(CAPTURED) == 1, len(CAPTURED))
    RESULTS["old_profile_body"] = {
        "status": "INFO",
        "sha256": hashlib.sha256(b).hexdigest(),
        "length": len(b),
        "body": b.decode('utf-8', 'replace'),
    }
except Exception as e:
    check("old_profile_result", False, traceback.format_exc())

# ── 2. max_tokens field appears in the body ───────────────────────────
try:
    before = len(CAPTURED)
    res = mt_call(profile_with(max_tokens="20000"))
    body = json.loads(body_of(-1))
    check("max_tokens_in_body", body.get("max_tokens") == 20000,
          body.get("max_tokens"))
    check("max_tokens_result", res == "TRANSLATED-OK", res)
    check("max_tokens_one_request", len(CAPTURED) == before + 1, len(CAPTURED))
except Exception:
    check("max_tokens_in_body", False, traceback.format_exc())

# ── 3. extra_body key merged into the body ────────────────────────────
try:
    res = mt_call(profile_with(extra_body='{"chat_template_kwargs": {"enable_thinking": false}}'))
    body = json.loads(body_of(-1))
    check("extra_body_in_body",
          body.get("chat_template_kwargs") == {"enable_thinking": False},
          body.get("chat_template_kwargs"))
except Exception:
    check("extra_body_in_body", False, traceback.format_exc())

# ── 4. timeout → readable one-line error with the profile name ────────
try:
    FakeHandler.mode = "sleep"
    t0 = time.time()
    res = mt_call(profile_with(timeout_min="0.005"))   # 0.3 s
    dt = time.time() - t0
    ok = (res.startswith("[Error:") and "timed out" in res
          and "profile 'Local proxy'" in res and "\n" not in res)
    # Q1 verdict (coordinator 2026-10-23): neutral hint, no menu path
    ok = ok and "the profile's 'Request timeout' field" in res
    ok = ok and "Settings" not in res
    check("timeout_error_text", ok, res)
    check("timeout_no_misleading_proxy_text", "proxy not running" not in res, res)
except Exception:
    check("timeout_error_text", False, traceback.format_exc())
finally:
    FakeHandler.mode = "ok"

# ── 5. truncation → readable one-line error ───────────────────────────
try:
    FakeHandler.mode = "length"
    res = mt_call(profile_with())
    ok = (res.startswith("[Error:") and "max_tokens" in res and "\n" not in res)
    check("truncated_error_text", ok, res)
    check("truncated_not_generic", "Custom MT error" not in res, res)
except Exception:
    check("truncated_error_text", False, traceback.format_exc())
finally:
    FakeHandler.mode = "ok"

# ── 6. parse_profile_request_fields: old-format + comma rules ─────────
try:
    from modules.llm_clients import parse_profile_request_fields as P
    mt, ts, eb, errs = P(profile_with())
    check("parse_old_format_clean", (mt, ts, eb, errs) == (None, None, None, []), (mt, ts, eb, errs))
    mt, ts, eb, errs = P(profile_with(timeout_min="1,5"))
    check("parse_comma_timeout", abs((ts or 0) - 90.0) < 1e-9 and not errs, (ts, errs))
    mt, ts, eb, errs = P(profile_with(timeout_min="1,5,5"))
    check("parse_multi_separator_rejected", bool(errs), errs)
    mt, ts, eb, errs = P(profile_with(max_tokens="abc"))
    check("parse_abc_rejected", bool(errs), errs)
    mt, ts, eb, errs = P(profile_with(extra_body='{"model": "x"}'))
    check("parse_forbidden_key_rejected", any("model" in e for e in errs), errs)
except Exception:
    check("parse_old_format_clean", False, traceback.format_exc())

# ── 7. save handler: validation blocks Save, "1,5" → "1.5" ────────────
try:
    from PyQt6.QtWidgets import QApplication, QComboBox, QLineEdit, QCheckBox
    app = QApplication.instance() or QApplication([])
    warns = []
    infos = []
    _w, _i = SV.QMessageBox.warning, SV.QMessageBox.information

    def _fake_warning(*a, **k):
        warns.append(a)
        return SV.QMessageBox.StandardButton.Ok

    def _fake_information(*a, **k):
        infos.append(a)
        return SV.QMessageBox.StandardButton.Ok

    SV.QMessageBox.warning = staticmethod(_fake_warning)
    SV.QMessageBox.information = staticmethod(_fake_information)

    class SaveStub(Stub):
        def __init__(self):
            self._mtql_checkboxes = {}
            self._mtql_llm_combos = {}
            self._mtql_llm_profile_cbs = None
            self.general_saved = None
            self.llm_saved = None

        def load_general_settings(self):
            return {}

        def save_general_settings(self, s):
            self.general_saved = s

        def load_llm_settings(self):
            return {"custom_mt_profiles": [], "custom_mt_active_profile": ""}

        def save_llm_settings(self, s):
            self.llm_saved = s

    def make_save_stub(profiles):
        s = SaveStub()
        s._custom_mt_profiles = [dict(p) for p in profiles]
        s._custom_mt_profile_combo = QComboBox()
        for p in s._custom_mt_profiles:
            s._custom_mt_profile_combo.addItem(p["name"])
        s._custom_mt_profile_combo.setCurrentIndex(0)
        s._custom_mt_endpoint_input = QLineEdit()
        s._custom_mt_model_input = QLineEdit()
        s._custom_mt_key_input = QLineEdit()
        s._custom_mt_raw_cb = QCheckBox()
        s._custom_mt_show_cb = QCheckBox()
        s._custom_mt_raw_cb.setChecked(True)
        s._custom_mt_show_cb.setChecked(True)
        s._custom_mt_endpoint_input.setText(BASE)
        s._custom_mt_model_input.setText("m")
        if not hasattr(s, "_custom_mt_max_tokens_input"):
            s._custom_mt_max_tokens_input = QLineEdit()
            s._custom_mt_timeout_input = QLineEdit()
            s._custom_mt_extra_input = QLineEdit()
        return s

    # S1: invalid max_tokens blocks Save
    s = make_save_stub([profile_with()])
    s._custom_mt_max_tokens_input.setText("abc")
    warns.clear()
    SQ._save_mt_quick_lookup_settings(s)
    check("save_blocked_abc",
          s.general_saved is None and s.llm_saved is None
          and any('Profile "Local proxy"' in str(a) and "Max tokens" in str(a) for a in warns),
          [str(a)[:200] for a in warns] or "no warning")

    # S2: timeout "1,5,5" blocks Save
    s = make_save_stub([profile_with()])
    s._custom_mt_max_tokens_input.clear()
    s._custom_mt_timeout_input.setText("1,5,5")
    warns.clear()
    SQ._save_mt_quick_lookup_settings(s)
    check("save_blocked_1555",
          s.general_saved is None and s.llm_saved is None
          and any("Request timeout" in str(a) for a in warns),
          [str(a)[:200] for a in warns] or "no warning")

    # S3: forbidden extra_body key blocks Save
    s = make_save_stub([profile_with()])
    s._custom_mt_timeout_input.clear()
    s._custom_mt_extra_input.setText('{"model": "x"}')
    warns.clear()
    SQ._save_mt_quick_lookup_settings(s)
    check("save_blocked_forbidden_key",
          s.general_saved is None and s.llm_saved is None
          and any("must not contain the key(s): model" in str(a) for a in warns),
          [str(a)[:200] for a in warns] or "no warning")

    # S4: valid "1,5" saved as "1.5"
    s = make_save_stub([profile_with()])
    s._custom_mt_extra_input.clear()
    s._custom_mt_timeout_input.setText("1,5")
    warns.clear()
    SQ._save_mt_quick_lookup_settings(s)
    prof = (s.llm_saved or {}).get("custom_mt_profiles", [{}])[0]
    check("save_comma_to_dot",
          s.llm_saved is not None and prof.get("timeout_min") == "1.5"
          and not warns, (prof.get("timeout_min"), [str(a)[:150] for a in warns]))

    # S5: old-format profile saves clean, no new keys added
    s = make_save_stub([{"name": "Old", "endpoint": BASE, "model": "m",
                         "api_key": "", "raw_mode": True, "enabled": True}])
    warns.clear()
    SQ._save_mt_quick_lookup_settings(s)
    prof = (s.llm_saved or {}).get("custom_mt_profiles", [{}])[0]
    check("save_old_format_no_new_keys",
          s.llm_saved is not None and not warns
          and not any(k in prof for k in ("max_tokens", "timeout_min", "extra_body")),
          (prof, [str(a)[:150] for a in warns]))

    SV.QMessageBox.warning = _w
    SV.QMessageBox.information = _i
except AttributeError as e:
    skip("save_handler_probe", f"pre tree (no new fields): {e}")
except Exception:
    try:
        SV.QMessageBox.warning = _w
        SV.QMessageBox.information = _i
    except Exception:
        pass
    check("save_blocked_abc", False, traceback.format_exc())

RESULTS["_meta"] = {
    "tree": TREE,
    "port": PORT,
    "captured_requests": len(CAPTURED),
    "stub_log_tail": LOG[-8:],
}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
srv.shutdown()
os._exit(0)
