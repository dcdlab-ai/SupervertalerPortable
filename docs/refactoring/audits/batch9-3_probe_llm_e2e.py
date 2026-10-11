# -*- coding: utf-8 -*-
"""Batch #9.3 «ДО»/«ПОСЛЕ»-проба: 5 LLM-сценариев через фейк OpenAI-совместимый endpoint (loopback).

Сценарии (все на provider=custom_openai, активный профиль -> фейк-сервер):
  single      — win.translate_current_segment() (Ctrl+T-путь)
  batch3      — win.translate_batch() (диалог провайдера: QDialog.exec -> Accepted, LLM по умолчанию)
  matchpanel  — win._add_mt_and_llm_matches(...) с enable_llm_matching=True
  proofread2  — win._run_proofreading([...2 сегмента...], ...)
  chat        — prompt_manager_qt.chat_backend.send_ai_request(...)

Фейк-сервер логирует каждый запрос (path, Authorization, model, roles, user_len, head)
и отвечает по содержимому промпта: proofread-маркеры -> '[SEGMENT N] ✓',
пакетный промпт -> 'нумерованный список', иначе -> 'Goedemorgen'.
Вердикт пишется в JSON (stdout ненадёжен у idle-процессов).

Запуск: python batch9-3_probe_llm_e2e.py <tree-root> <iso-dir> <tag>
"""
import faulthandler, json, os, pathlib, re, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]
OUT = pathlib.Path(rf"D:\Temp\SupervertalerPortable\refactoring\b9-3\llm_e2e_verdict_{tag}.json")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg = iso / "AppData" / "Roaming" / "Supervertaler"
cfg.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8")

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

# ---------- fake server ----------
REQUESTS = []


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8", "replace")) if length else {}
        model = body.get("model", "")
        messages = body.get("messages", [])
        roles = [m.get("role") for m in messages]
        user_content = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                user_content = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                break
        REQUESTS.append({
            "path": self.path,
            "auth": self.headers.get("Authorization", ""),
            "model": model,
            "roles": roles,
            "n_messages": len(messages),
            "user_len": len(user_content),
            "head": user_content[:80].replace("\n", "\\n"),
        })

        if "[SEGMENT " in user_content:
            nums = re.findall(r"\[SEGMENT (\d{4})\]", user_content)
            content = "\n".join(f"[SEGMENT {n}] \u2713" for n in nums) or "[SEGMENT 0001] \u2713"
        elif "**SEGMENTS TO TRANSLATE" in user_content:
            ids = re.findall(r"(?m)^(\d+)\.\s", user_content)
            content = "\n".join(f"{i}. Goedemorgen{i}" for i in ids) or "1. Goedemorgen"
        else:
            content = "Goedemorgen"

        resp = {
            "id": "chatcmpl-fake", "object": "chat.completion", "created": 1, "model": model,
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
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

open_queue = [str(tree / "user_data" / "samples" / "sample_en_nl.txt")]
if not pathlib.Path(open_queue[0]).exists():
    open_queue = [str(inputs) for inputs in [
        r"D:\Temp\SupervertalerPortable\refactoring\b9-3\inputs\test.txt"]]


def fake_open(*a, **k):
    return (open_queue.pop(0) if open_queue else "", "")


QFileDialog.getOpenFileName = staticmethod(fake_open)
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(open_queue), "") if open_queue else ([], ""))

import Supervertaler as SV  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

# ---------- settings seed: provider=custom_openai -> fake endpoint ----------
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

result = {"tag": tag, "port": PORT, "requests": REQUESTS, "modal_log": modal_log}
try:
    win = SV.SupervertalerQt()
    result["current_provider"] = getattr(win, "current_provider", None)
    result["current_model"] = getattr(win, "current_model", None)
    APP_LOG = []
    _orig_log = win.log
    win.log = lambda msg, *a, **k: (APP_LOG.append(str(msg)), _orig_log(msg, *a, **k))
    import time as _time
    for _ in range(100):
        app.processEvents()
        _time.sleep(0.05)

    # --- import sample txt -> project + grid ---
    win.import_simple_txt()
    for _ in range(40):
        app.processEvents()
        _time.sleep(0.05)
    n_seg = len(win.current_project.segments) if win.current_project else 0
    result["imported_segments"] = n_seg
    if not n_seg:
        raise RuntimeError("no segments imported")

    # --- scenario 1: single (row 1: непустой источник) ---
    n0 = len(REQUESTS)
    win.table.setCurrentCell(1, 2)
    result["row_immediate"] = win.table.currentRow()
    if win.table.currentRow() < 0:
        win.table.selectRow(1)
    result["row_after_select"] = win.table.currentRow()
    app.processEvents()
    result["row_final"] = win.table.currentRow()
    win.translate_current_segment()
    for _ in range(20):
        app.processEvents()
    seg1 = win.current_project.segments[1]
    result["single"] = {
        "target": seg1.target, "status": seg1.status,
        "requests": REQUESTS[n0:], "n_requests": len(REQUESTS) - n0,
        "log": APP_LOG[-8:], "row": win.table.currentRow(),
        "src_head": seg1.source[:50]}

    # --- scenario 2: batch 3 ---
    rows = [(i, win.current_project.segments[i]) for i in (1, 2, 3)]
    for _, s in rows:
        s.target = ""
    n0 = len(REQUESTS)
    win.translate_batch(segments_with_rows=rows, scope_description="probe 3")
    for _ in range(20):
        app.processEvents()
    result["batch3"] = {
        "targets": [win.current_project.segments[i].target for i in (1, 2, 3)],
        "requests": REQUESTS[n0:], "n_requests": len(REQUESTS) - n0}

    # --- scenario 3: Match Panel LLM ---
    n0 = len(REQUESTS)
    win.enable_mt_matching = False
    win.enable_llm_matching = True
    matches = {"LLM": [], "MT": [], "TM": []}
    seg = win.current_project.segments[4]
    win._add_mt_and_llm_matches(seg, matches, "English", "Dutch", "en", "nl")
    for _ in range(20):
        app.processEvents()
    result["matchpanel"] = {
        "llm_matches": [m.provider_code for m in matches["LLM"]],
        "requests": REQUESTS[n0:], "n_requests": len(REQUESTS) - n0}

    # --- scenario 4: proofread 2 ---
    n0 = len(REQUESTS)
    pr_rows = [(0, win.current_project.segments[0]), (1, win.current_project.segments[1])]
    win._run_proofreading(pr_rows, "custom_openai", "fake-llm",
                          "", win.load_llm_settings())
    if getattr(win, "_proofread_worker", None) is not None:
        win._proofread_worker.wait()
    for _ in range(20):
        app.processEvents()
    result["proofread2"] = {
        "notes": {str(k): v for k, v in (win.current_project.segments[0].proofreading_notes or {}).items()},
        "requests": REQUESTS[n0:], "n_requests": len(REQUESTS) - n0}

    # --- scenario 5: chat ---
    n0 = len(REQUESTS)
    backend = win.prompt_manager_qt.chat_backend
    text, meta = backend.send_ai_request("Say hello", "You are helpful.")
    for _ in range(20):
        app.processEvents()
    result["chat"] = {
        "response": text, "meta_provider": meta.get("provider"), "meta_model": meta.get("model"),
        "requests": REQUESTS[n0:], "n_requests": len(REQUESTS) - n0}

    result["verdict"] = "OK"
except BaseException as e:
    import traceback
    result["exception"] = f"{type(e).__name__}: {e}"
    result["traceback"] = traceback.format_exc()
    result["verdict"] = "EXCEPTION"

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
os._exit(0)
