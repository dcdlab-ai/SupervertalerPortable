# -*- coding: utf-8 -*-
"""BATCH Q-C / Q.5 probe — profile picker in Proofreading + Batch dialogs.

Setup: two fake loopback endpoints (A, B) with distinct models and request
params; settings seed: LLM profiles 'LLM A' (ACTIVE) -> A, 'LLM B' -> B
(model llm-b, max_tokens 777, extra_body {"foo":"bar"}); MT profiles
'MT A' (ACTIVE) -> A, 'MT B' -> B (model mt-b).

Sections:
  P1 proofread, picker untouched (default = active A): requests -> A, llm-a.
  P2 proofread, picker set to B: requests -> B, llm-b, max_tokens 777,
     extra_body foo=bar, 0 to A; global active stays A; llm_settings untouched.
  P3 batch LLM, picker untouched: requests -> A, llm-a (identical to before).
  P4 batch LLM, picker set to B: requests -> B, llm-b, 777, foo=bar, 0 to A.
  P5 batch MT, MT picker set to B: MT requests -> B (mt-b), 0 to A.
  P6 empty profile list: proofread gate message, 0 requests.

Run: python probe_q5.py <tree-root> <stage-dir>
"""
import faulthandler, json, os, pathlib, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
iso = stage / "iso"
OUT = stage / "probe_q5.json"

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

# ---------- two fake endpoints ----------
SERVERS = {"A": {"requests": [], "port": None}, "B": {"requests": [], "port": None}}


def make_handler(tag):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8", "replace")) if n else {}
            user_content = ""
            for m in reversed(body.get("messages", [])):
                if m.get("role") == "user":
                    c = m.get("content")
                    user_content = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                    break
            SERVERS[tag]["requests"].append({
                "model": body.get("model", ""),
                "max_tokens": body.get("max_tokens"),
                "max_completion_tokens": body.get("max_completion_tokens"),
                "foo": (body.get("foo") or (body.get("extra_body", {}) or {}).get("foo")),
                "user_head": user_content[:100].replace("\n", "\\n")})
            if "translation proofreader" in user_content:
                # Proofreading batch prompt — answer with ISSUE markers so the
                # worker emits segment_issue and proofreading_notes get keyed
                # by the model name (OK markers create no notes).
                import re as _re
                ids = [int(m) for m in _re.findall(r"\[SEGMENT (\d+)\]", user_content)]
                content = "\n".join(f"[SEGMENT {i:04d}] \u26a0\n  Issue: probe issue {i}"
                                    for i in ids) or "[SEGMENT 0001] \u26a0\n  Issue: probe"
            else:
                content = f"ANSWER-{tag}"
            resp = {"id": f"chatcmpl-{tag}", "object": "chat.completion", "created": 1,
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
    return H


for tag in ("A", "B"):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(tag))
    SERVERS[tag]["port"] = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

# ---------- modal/file-dialog neutralization + scripted profile picker ------
import PyQt6.QtWidgets as QW  # noqa: E402
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog, QComboBox, QCheckBox  # noqa: E402

modal_log = []
MODE = {"action": "default"}  # default | llm_b | mt_b


def _scripted_exec(self, *a, **k):
    modal_log.append(f"QDialog.exec {type(self).__name__} '{self.windowTitle()}'")
    if MODE["action"] != "default":
        combos = self.findChildren(QComboBox)
        for cb in combos:
            names = [cb.itemData(i) for i in range(cb.count())]
            if MODE["action"] == "llm_b" and "LLM B" in names:
                cb.setCurrentIndex(names.index("LLM B"))
            if MODE["action"] == "mt_b" and "MT B" in names:
                cb.setCurrentIndex(names.index("MT B"))
        if MODE["action"] == "mt_b":
            for ch in self.findChildren(QCheckBox):
                if ch.text().startswith("\U0001F310 MT"):
                    ch.setChecked(True)
    return QDialog.DialogCode.Accepted


QDialog.exec = _scripted_exec
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: (modal_log.append(f"warn '{a[1] if len(a) > 1 else ''}'"), QMessageBox.StandardButton.Ok)[1])
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

inputs = stage / "inputs"
inputs.mkdir(parents=True, exist_ok=True)
(inputs / "q5_doc.txt").write_text("First segment text\nSecond segment text\n", encoding="utf-8")
open_queue = [str(inputs / "q5_doc.txt")] * 4
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (open_queue.pop(0) if open_queue else "", ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(stage / "out.txt"), ""))

import Supervertaler as SV  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False
from modules.dialogs import live_progress as _lp  # noqa: E402
_lp.LiveProgressDialog.add_console_line = lambda self, message, is_success=True: None

from PyQt6.QtWidgets import QApplication  # noqa: E402
app = QApplication(sys.argv)

SEED_LLM = {
    "provider": "custom_openai",
    "custom_openai_profiles": [
        {"name": "LLM A", "endpoint": f"http://127.0.0.1:{SERVERS['A']['port']}/v1",
         "model": "llm-a", "api_key": "key-a", "enabled": True},
        {"name": "LLM B", "endpoint": f"http://127.0.0.1:{SERVERS['B']['port']}/v1",
         "model": "llm-b", "api_key": "key-b", "enabled": True,
         "max_tokens": "777", "extra_body": '{"foo": "bar"}'},
    ],
    "custom_openai_active_profile": "LLM A",
    "custom_mt_profiles": [
        {"name": "MT A", "endpoint": f"http://127.0.0.1:{SERVERS['A']['port']}/v1",
         "model": "mt-a", "api_key": "", "raw_mode": True, "enabled": True},
        {"name": "MT B", "endpoint": f"http://127.0.0.1:{SERVERS['B']['port']}/v1",
         "model": "mt-b", "api_key": "", "raw_mode": True, "enabled": True},
    ],
    "custom_mt_active_profile": "MT A",
}
sf = data_dir / "workbench" / "settings" / "settings.json"
sf.parent.mkdir(parents=True, exist_ok=True)
sf.write_text(json.dumps({"ui": {"llm_settings": SEED_LLM},
                          "api_keys": {"custom_openai": "file-key"}},
                         indent=2, ensure_ascii=False), encoding="utf-8")
SEED_LLM_JSON = json.dumps(SEED_LLM, sort_keys=True, ensure_ascii=False)

result = {"tag": "q5", "servers": {k: v["port"] for k, v in SERVERS.items()},
          "checks": {}, "evidence": {}}
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


def llm_settings_now(win):
    return win.load_llm_settings()


win = None
try:
    win = SV.SupervertalerQt()
    for _ in range(120):
        app.processEvents()
        time.sleep(0.05)

    # ============ P1: proofread with default picker (active A) ================
    win.import_simple_txt()
    pump(2.0)
    # Proofreading's default scope is "Confirmed only"; a fresh import is
    # 'untranslated' — confirm both segments so the worker has work to do.
    for _s in win.current_project.segments:
        _s.status = 'confirmed'
    win.load_segments_to_grid()
    pump(1.5)
    MODE["action"] = "default"
    SERVERS["A"]["requests"].clear(); SERVERS["B"]["requests"].clear()
    win.show_proofread_dialog()
    pump(6.0)
    ra, rb = len(SERVERS["A"]["requests"]), len(SERVERS["B"]["requests"])
    check("p1_default_requests_to_A", ra >= 1 and rb == 0, f"A={ra} B={rb}")
    if ra:
        r = SERVERS["A"]["requests"][0]
        check("p1_default_model_llm_a", r["model"] == "llm-a", repr(r))
    notes_models = set()
    for s in win.current_project.segments:
        notes_models |= set((s.proofreading_notes or {}).keys())
    check("p1_notes_keyed_llm_a", notes_models == {"llm-a"}, repr(notes_models))

    # ============ P2: proofread with picker set to B ==========================
    for _s in win.current_project.segments:
        _s.status = 'confirmed'
    MODE["action"] = "llm_b"
    SERVERS["A"]["requests"].clear(); SERVERS["B"]["requests"].clear()
    win.show_proofread_dialog()
    pump(6.0)
    ra, rb = len(SERVERS["A"]["requests"]), len(SERVERS["B"]["requests"])
    check("p2_selB_requests_to_B", rb >= 1 and ra == 0, f"A={ra} B={rb}")
    if rb:
        r = SERVERS["B"]["requests"][0]
        check("p2_selB_model_llm_b", r["model"] == "llm-b", repr(r))
        check("p2_selB_max_tokens_777", r["max_tokens"] == 777, repr(r))
        check("p2_selB_extra_body_foo", r["foo"] == "bar", repr(r))
    st = llm_settings_now(win)
    check("p2_active_profile_still_A",
          st.get("custom_openai_active_profile") == "LLM A"
          and st.get("custom_mt_active_profile") == "MT A",
          repr(st.get("custom_openai_active_profile")))
    on_disk = json.dumps(json.loads(sf.read_text(encoding="utf-8"))["ui"]["llm_settings"],
                         sort_keys=True, ensure_ascii=False)
    check("p2_settings_json_untouched", on_disk == SEED_LLM_JSON,
          "changed" if on_disk != SEED_LLM_JSON else "identical")

    # ============ P3: batch LLM with default picker ===========================
    win.import_simple_txt()
    pump(2.0)
    MODE["action"] = "default"
    SERVERS["A"]["requests"].clear(); SERVERS["B"]["requests"].clear()
    rows = [(i, s) for i, s in enumerate(win.current_project.segments)]
    win.translate_batch(segments_with_rows=rows, scope_description="q5 P3 default")
    pump(8.0)
    ra, rb = len(SERVERS["A"]["requests"]), len(SERVERS["B"]["requests"])
    check("p3_default_requests_to_A", ra >= 1 and rb == 0, f"A={ra} B={rb}")
    if ra:
        check("p3_default_model_llm_a", SERVERS["A"]["requests"][0]["model"] == "llm-a",
              repr(SERVERS["A"]["requests"][0]))

    # ============ P4: batch LLM with picker set to B ==========================
    win.import_simple_txt()
    pump(2.0)
    MODE["action"] = "llm_b"
    SERVERS["A"]["requests"].clear(); SERVERS["B"]["requests"].clear()
    rows = [(i, s) for i, s in enumerate(win.current_project.segments)]
    win.translate_batch(segments_with_rows=rows, scope_description="q5 P4 llm B")
    pump(8.0)
    ra, rb = len(SERVERS["A"]["requests"]), len(SERVERS["B"]["requests"])
    check("p4_selB_requests_to_B", rb >= 1 and ra == 0, f"A={ra} B={rb}")
    if rb:
        r = SERVERS["B"]["requests"][0]
        check("p4_selB_model_llm_b", r["model"] == "llm-b", repr(r))
        check("p4_selB_max_tokens_777", r["max_tokens"] == 777, repr(r))
        check("p4_selB_extra_body_foo", r["foo"] == "bar", repr(r))
    st = llm_settings_now(win)
    check("p4_active_profile_still_A", st.get("custom_openai_active_profile") == "LLM A",
          repr(st.get("custom_openai_active_profile")))

    # ============ P5: batch MT with MT picker set to B ========================
    win.import_simple_txt()
    pump(2.0)
    MODE["action"] = "mt_b"
    SERVERS["A"]["requests"].clear(); SERVERS["B"]["requests"].clear()
    rows = [(i, s) for i, s in enumerate(win.current_project.segments)]
    win.translate_batch(segments_with_rows=rows, scope_description="q5 P5 mt B")
    pump(8.0)
    ra, rb = len(SERVERS["A"]["requests"]), len(SERVERS["B"]["requests"])
    check("p5_mt_selB_requests_to_B", rb >= 1 and ra == 0, f"A={ra} B={rb}")
    if rb:
        r = SERVERS["B"]["requests"][0]
        check("p5_mt_selB_model_mt_b", r["model"] == "mt-b", repr(r))
        EV["p5_request_user_head"] = r["user_head"]

    # ============ P6: empty profile list keeps the gate =======================
    MODE["action"] = "default"
    n_warn = len([m for m in modal_log if "not configured" in m])
    try:
        win._run_proofreading([(0, win.current_project.segments[0])], "custom_openai",
                              "m", "", settings={"custom_openai_profiles": []})
    except Exception as ex:
        check("p6_gate_no_crash", False, repr(ex))
    pump(1.0)
    warns = [m for m in modal_log if "not configured" in m]
    check("p6_gate_message_shown", len(warns) == n_warn + 1, repr(warns[-1:]))

    check("trap_network_empty", not NET_TRAPS, repr(NET_TRAPS[:3]))
    EV["modal_log_head"] = modal_log[:12]
finally:
    result["checks_summary"] = {k: v["status"] for k, v in CHECKS.items()}
    result["ok"] = all(v["status"] == "PASS" for v in CHECKS.values())
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Q5-PROBE", "GREEN" if result["ok"] else "RED",
          f"{sum(1 for v in CHECKS.values() if v['status']=='PASS')}/{len(CHECKS)}")
    try:
        if win is not None:
            win.close()
    except Exception:
        pass
    sys.stdout.flush()
    os._exit(0 if result["ok"] else 1)
