# -*- coding: utf-8 -*-
"""Batch #9.2a: проба диспетчера _fetch_mt_translation_async (custom MT only).

Фейк OpenAI-совместимый endpoint на 127.0.0.1; диспетчер вызывается напрямую,
QTimer.singleShot(150) срабатывает при накачке processEvents. Проверки:
  - фейк-сервер получил POST /v1/chat/completions (диспетчер пошёл в custom MT);
  - в логе появилась строка '✓ MT translation (custom MT: ...)' или тихий сбой
    без исключений; результат — в JSON-файл.
Запуск: python batch9-2_probe_dispatcher.py <tree-root> <iso-dir> <tag>
"""
import faulthandler, json, os, pathlib, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]
OUT = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-2\dispatcher_verdict.json")

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

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

FAKE_TRANSLATION = "Goedemorgen"


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.server.hits += 1
        self.server.last_body = body.decode("utf-8", "replace")
        resp = {
            "id": "chatcmpl-fake", "object": "chat.completion", "created": 1, "model": "fake-mt",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": FAKE_TRANSLATION},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
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
server.hits = 0
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected

sf = data_dir / "workbench" / "settings" / "settings.json"
sf.parent.mkdir(parents=True, exist_ok=True)
sf.write_text(json.dumps({"ui": {"llm_settings": {
    "provider": "custom_openai",
    "custom_mt_profiles": [{"name": "MT Fake", "endpoint": f"http://127.0.0.1:{port}/v1",
                            "model": "fake-mt", "api_key": "", "raw_mode": True, "enabled": True}],
    "custom_mt_active_profile": "MT Fake"}}}, indent=2, ensure_ascii=False), encoding="utf-8")

result = {"tag": tag, "port": port, "logs": []}
try:
    win = Supervertaler.SupervertalerQt()
    # перехват лога диспетчера
    base_log = win.log
    win.log = lambda msg: (result["logs"].append(str(msg)), base_log(msg))

    class _Seg:  # диспетчер сегмент не использует
        pass

    win._fetch_mt_translation_async("Good morning", _Seg(), 0)
    for _ in range(60):
        app.processEvents()
        time.sleep(0.05)

    result["server_hits"] = server.hits
    result["fake_body_seen"] = bool(getattr(server, "last_body", None))
    result["verdict"] = server.hits >= 1  # диспетчер дошёл до custom MT (панельная ветка требует assistance_widget, как в baseline)
except BaseException as e:
    import traceback
    result["exception"] = f"{type(e).__name__}: {e}"
    traceback.print_exc()

OUT.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
os._exit(0)
