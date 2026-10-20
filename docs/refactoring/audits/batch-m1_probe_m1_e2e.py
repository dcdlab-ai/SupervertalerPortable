# -*- coding: utf-8 -*-
"""M1 e2e probe: link-only segments must not reach the LLM endpoint.

Precedent: docs/refactoring/audits/batch9-3_probe_llm_e2e.py (full app, isolated
profile, fake OpenAI-compatible loopback endpoint, stubbed modals).

Scenarios:
  S1 matrix-batch  — 11-segment synthetic project (link-only + link+text + plain
                     + plain md link + empty alt); one batch call: the payload
                     must contain ONLY the ids that are not link-only; link-only
                     targets == source byte-wise; statuses draft; counters.
                     M1e (2026-10-20, broadened criterion): the trailing-period row
                     "![Image](x.png)." (id 7) is now link-only too -> expected ids
                     [1, 6, 8, 10, 11] (was [1, 6, 7, 8, 10, 11] under M1), 6 copy
                     lines (was 5). Expectations updated per coordinator verdict
                     (M1e Q8); the historical run logs are NOT regenerated.
  S2 all-links     — a batch of ONLY link-only segments: ZERO endpoint requests.
  S3 single-link   — translate_current_segment on a link-only segment: zero new
                     requests, target == source, status draft, log line.
  S4 single-mixed  — translate_current_segment on "![Image](x.png) Figure 1
                     shows": exactly one request, LLM target used.
  S5 fixture       — real docs/refactoring/samples/Miniature Wargames #520.
                     translation.md: import, batch, export; the image-link
                     target must be byte-identical in the exported md.
  S6 net-trap      — socket.connect to any non-loopback address must be zero.

Run: python probe_m1_e2e.py <tree-root> <run-dir>   (offscreen, isolated profile)
"""
import faulthandler, hashlib, json, os, pathlib, re, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

tree = pathlib.Path(sys.argv[1]).resolve()
stage = pathlib.Path(sys.argv[2]).resolve()
iso = stage / "iso"
OUT = stage / "probe_m1_e2e_verdict.json"

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

faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

# ---------- network trap: every non-loopback connect attempt is recorded ----------
NET_TRAPS = []
_real_connect = socket.socket.connect


def _traced_connect(self, address, *a, **k):
    if isinstance(address, tuple) and len(address) >= 2:
        host = address[0]
        if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost"):
            NET_TRAPS.append(str(address))
    return _real_connect(self, address, *a, **k)


socket.socket.connect = _traced_connect

# ---------- fake OpenAI-compatible endpoint (loopback only) ----------
REQUESTS = []
PAYLOADS_DIR = stage / "payloads"
PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8", "replace")) if length else {}
        messages = body.get("messages", [])
        user_content = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                user_content = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                break
        n = len(REQUESTS)
        (PAYLOADS_DIR / f"req-{n:02d}.json").write_text(
            json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
        ids = []
        if "**SEGMENTS TO TRANSLATE" in user_content:
            # ids as they appear in the segment list of the prompt
            seg_part = user_content.split("**SEGMENTS TO TRANSLATE:**")[-1]
            seg_part = seg_part.split("**YOUR TRANSLATIONS")[0]
            ids = [int(m) for m in re.findall(r"(?m)^(\d+)\.\s", seg_part)]
        REQUESTS.append({
            "path": self.path,
            "model": body.get("model", ""),
            "n_messages": len(messages),
            "user_len": len(user_content),
            "ids_in_prompt": ids,
            "head": user_content[:120].replace("\n", "\\n"),
        })
        if ids:
            content = "\n".join(f"{i}. Translated{i}" for i in ids)
        else:
            content = "Goedemorgen"
        resp = {
            "id": "chatcmpl-fake", "object": "chat.completion", "created": 1,
            "model": body.get("model", ""),
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

# input files: matrix txt, all-links txt, fixture md (copied into stage/inputs)
inputs = stage / "inputs"
inputs.mkdir(parents=True, exist_ok=True)
matrix = inputs / "m1_matrix_en_nl.txt"
matrix.write_text("\n".join([
    "The quick brown fox jumps over the lazy dog.",
    "![Image](/path/file.png)",
    "![Image](a.png) ![Image](b.png)",
    "![Figure 1](x.png)",
    "![Рисунок 1](рисунки/рисунок 1.png)",
    "![Image](x.png) Figure 1 shows",
    "![Image](x.png).",
    "[t](u)",
    "![](x.png)",
    "![Image](x.png) some text after",
    "The troops advanced at dawn.",
    "",
]) + "\n", encoding="utf-8")
alllinks = inputs / "m1_all_links_en_nl.txt"
alllinks.write_text("![Image](x1.png)\n![Figure 3](fig/рис 3.png)\n", encoding="utf-8")
fixture_src = tree / "docs" / "refactoring" / "samples" / "Miniature Wargames #520.translation.md"
fixture = inputs / "m1_fixture_en_nl.md"
fixture.write_bytes(fixture_src.read_bytes())

open_queue = [str(matrix), str(alllinks), str(fixture)]


def fake_open(*a, **k):
    return (open_queue.pop(0) if open_queue else "", "")


QFileDialog.getOpenFileName = staticmethod(fake_open)
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: (list(open_queue), "") if open_queue else ([], ""))

import Supervertaler as SV  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

# capture the batch console lines (progress_update messages)
from modules.dialogs import live_progress as _lp  # noqa: E402
CONSOLE = []
_lp.LiveProgressDialog.add_console_line = lambda self, message, is_success=True: CONSOLE.append((str(message), bool(is_success)))

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

result = {"tag": "m1-e2e", "port": PORT, "requests": REQUESTS, "modal_log": modal_log}


def pump(n=30):
    for _ in range(n):
        app.processEvents()
        time.sleep(0.03)


try:
    win = SV.SupervertalerQt()
    APP_LOG = []
    _orig_log = win.log
    win.log = lambda msg, *a, **k: (APP_LOG.append(str(msg)), _orig_log(msg, *a, **k))
    for _ in range(100):
        app.processEvents()
        time.sleep(0.05)

    # ================= S1: matrix batch =================
    win.import_simple_txt()
    pump(40)
    segs = win.current_project.segments
    result["s1_segments"] = [(s.id, s.source[:60]) for s in segs]
    if len(segs) < 11:
        raise RuntimeError(f"matrix import produced {len(segs)} segments, expected 11")
    rows = [(i, segs[i]) for i in range(11)]
    for _, s in rows:
        s.target = ""
    n0 = len(REQUESTS)
    CONSOLE.clear()
    win.translate_batch(segments_with_rows=rows, scope_description="m1 matrix")
    pump(20)
    req = REQUESTS[n0] if len(REQUESTS) > n0 else None
    result["s1"] = {
        "n_requests": len(REQUESTS) - n0,
        "ids_in_prompt": req["ids_in_prompt"] if req else None,
        "targets": [segs[i].target for i in range(11)],
        "statuses": [segs[i].status for i in range(11)],
        "console_link_only_lines": sum(1 for m, _ in CONSOLE if "⤳ link-only (LLM skipped)" in m),
        "console_lines_n": len(CONSOLE),
    }
    link_idx = {1, 2, 3, 4, 6, 8}  # 0-based link-only rows: ids 2..5, 7 ("![Image](x.png)."
    # trailing period — link-only since M1e), 9
    link_only_sources = [segs[i].source for i in link_idx]
    result["s1"]["link_only_targets_byte_eq_source"] = all(
        segs[i].target == segs[i].source for i in link_idx)
    result["s1"]["translated_ids_byte_eq_expected"] = all(
        segs[i].target == f"Translated{segs[i].id}" for i in range(11) if i not in link_idx)

    # ================= S3: single on link-only (row 1 = id 2) =================
    win.table.selectRow(1)
    pump(5)
    win.table.setCurrentCell(1, 2)
    pump(5)
    n0 = len(REQUESTS)
    log_n = len(APP_LOG)
    win.translate_current_segment()
    pump(20)
    s = segs[1]
    result["s3"] = {
        "row": win.table.currentRow(),
        "n_requests": len(REQUESTS) - n0,
        "target_eq_source": s.target == s.source,
        "status": s.status,
        "log_lines": APP_LOG[log_n:],
    }

    # ================= S4: single on link+text (row 5 = id 6) =================
    win.table.selectRow(5)
    pump(5)
    win.table.setCurrentCell(5, 2)
    pump(5)
    n0 = len(REQUESTS)
    log_n = len(APP_LOG)
    win.translate_current_segment()
    pump(30)
    s6 = segs[5]
    result["s4"] = {
        "n_requests": len(REQUESTS) - n0,
        "target": s6.target,
        "status": s6.status,
        "log_tail": APP_LOG[log_n:],
    }

    # ================= S2: batch of ONLY link-only segments =================
    win.import_simple_txt()
    pump(40)
    segs2 = win.current_project.segments
    rows2 = [(i, segs2[i]) for i in range(len(segs2))]
    n0 = len(REQUESTS)
    CONSOLE.clear()
    win.translate_batch(segments_with_rows=rows2, scope_description="m1 all-links")
    pump(20)
    result["s2"] = {
        "n_requests": len(REQUESTS) - n0,
        "targets_eq_source": all(s.target == s.source for s in segs2),
        "statuses": [s.status for s in segs2],
        "console_link_only_lines": sum(1 for m, _ in CONSOLE if "⤳ link-only (LLM skipped)" in m),
    }

    # ================= S5: real fixture import -> batch -> export =================
    win.import_simple_txt()
    pump(40)
    segs5 = win.current_project.segments
    fixture_sources = [s.source for s in segs5]
    link_rows = [i for i, s in enumerate(segs5)
                 if s.source.strip().startswith("![")]
    rows5 = [(i, segs5[i]) for i in range(len(segs5)) if segs5[i].source.strip()]
    n0 = len(REQUESTS)
    CONSOLE.clear()
    win.translate_batch(segments_with_rows=rows5, scope_description="m1 fixture")
    pump(20)
    req = REQUESTS[n0] if len(REQUESTS) > n0 else None
    link_ids = {segs5[i].id for i in link_rows}
    sent_ids = set(req["ids_in_prompt"]) if req else set()
    result["s5"] = {
        "n_segments": len(segs5),
        "link_rows": link_rows,
        "link_ids": sorted(link_ids),
        "n_requests": len(REQUESTS) - n0,
        "ids_in_prompt": req["ids_in_prompt"] if req else None,
        "link_ids_leaked_to_endpoint": sorted(link_ids & sent_ids),
        "link_targets_eq_source": all(segs5[i].target == segs5[i].source for i in link_rows),
        "link_statuses": [segs5[i].status for i in link_rows],
        "console_link_only_lines": sum(1 for m, _ in CONSOLE if "⤳ link-only (LLM skipped)" in m),
    }
    # export via the module's builder (same code path as export_bilingual_markdown)
    from modules.bilingual_markdown_handler import MdExportSegment, build_markdown, build_sidecar, write_export
    mdsegs = [MdExportSegment(number=i + 1, segment_id=s.id, source=s.source, target=s.target)
              for i, s in enumerate(segs5)]
    md_text = build_markdown(
        mdsegs, project_name="m1", source_file_name="m1_fixture_en_nl.md",
        source_lang_display="English", target_lang_display="Dutch", tool_version="probe")
    out_md = stage / "export" / "m1_fixture_export.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    sidecar = build_sidecar(
        mdsegs, project_name="m1", source_file_name="m1_fixture_en_nl.md",
        source_language="en", target_language="nl", tool_version="m1-probe",
        export_file_path=str(out_md), timestamp_utc="2026-10-19T00:00:00Z")
    write_export(str(out_md), md_text, sidecar)
    exp_text = out_md.read_text(encoding="utf-8")
    # every source link string must appear in the export exactly twice (source +
    # target lines) and byte-identical (count of exact matches == 2)
    link_strs = [segs5[i].source.strip() for i in link_rows]
    result["s5"]["export_link_byte_identity"] = {ls: exp_text.count(ls) for ls in link_strs}

    # ================= S6: network trap verdict =================
    result["net_traps"] = NET_TRAPS

    # ---- verdict ----
    s1 = result["s1"]
    ok = (
        s1["n_requests"] == 1
        and s1["ids_in_prompt"] == [1, 6, 8, 10, 11]
        and s1["link_only_targets_byte_eq_source"]
        and s1["translated_ids_byte_eq_expected"]
        and all(st == "draft" for st in s1["statuses"])
        and s1["console_link_only_lines"] == 6
        and result["s3"]["n_requests"] == 0
        and result["s3"]["target_eq_source"]
        and result["s3"]["status"] == "draft"
        and any("link-only segment" in l for l in result["s3"]["log_lines"])
        and result["s4"]["n_requests"] == 1
        # single-prompt responses from the fake endpoint are the fixed string
        # "Goedemorgen" (no numbered list in a single-segment prompt)
        and result["s4"]["target"] == "Goedemorgen"
        and result["s4"]["status"] == "draft"
        and result["s2"]["n_requests"] == 0
        and result["s2"]["targets_eq_source"]
        and result["s2"]["console_link_only_lines"] == 2
        and result["s5"]["n_requests"] == 1
        and not result["s5"]["link_ids_leaked_to_endpoint"]
        and result["s5"]["link_targets_eq_source"]
        and result["s5"]["console_link_only_lines"] == 1
        and all(v == 2 for v in result["s5"]["export_link_byte_identity"].values())
        and not result["net_traps"]
    )
    result["verdict"] = "PASS" if ok else "FAIL"
except BaseException as e:
    import traceback
    result["exception"] = f"{type(e).__name__}: {e}"
    result["traceback"] = traceback.format_exc()
    result["verdict"] = "EXCEPTION"

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
os._exit(0)
