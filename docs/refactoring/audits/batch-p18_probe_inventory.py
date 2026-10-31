# -*- coding: utf-8 -*-
r"""BATCH P1.8 Part A probe: inventory of everything the product + runtime
write OUTSIDE the build tree when run WITHOUT a profile redirect.

The isolated dir (iso) simulates the real user environment: USERPROFILE /
APPDATA / LOCALAPPDATA / HOME point into iso, TEMP/TMP into iso\tmp.
After the run, everything found under iso\AppData, iso\tmp, iso\Desktop...
= what WOULD have landed in the real %APPDATA% / %TEMP% etc. Everything
directly under iso root = what WOULD have landed in the real ~ (or, for
state_root() service files, in the build root = inside the tree).
The seam SUPERVERTALER_DATA_ROOT=iso maps data root to <iso>\Supervertaler
(in the real build: <build_root>\Supervertaler — inside the tree).

Modes (argv[4]):
  clean  — empty iso, NO settings seed: start, QuickTrans popup, close
           (the "clean start" checklist source).
  full   — settings seeded for the fake OpenAI endpoint, then: start, popup,
           import sample txt, translate via fake server, save project,
           close (the full working cycle).

Both modes also run M4 (read-only): `reg query HKCU\Software\Supervertaler /s`
and the HKCU Run value before/after — diff must be empty.

Optional argv[5] "tripwire": replace sys.modules['winreg'] with a blocking
object BEFORE product imports (P1.6 M3 method) — used by the P1.8 battery.

Verdicts: P18-INV-OK / P18-INV-FAIL <reasons>.
Run: python batch-p18_probe_inventory.py <tree-root> <iso-dir> <tag> <mode> [tripwire]
"""
import faulthandler
import json
import os
import pathlib
import subprocess
import sys
import time

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]
mode = sys.argv[4] if len(sys.argv) > 4 else "clean"
tripwire = "tripwire" in sys.argv[5:]

STAGE = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p18")
STAGE.mkdir(parents=True, exist_ok=True)
OUT = STAGE / f"inventory_{tag}.json"

# --- capture the REAL environment sentinels before overriding ---
REAL = {
    "APPDATA": os.environ.get("APPDATA", ""),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
    "USERPROFILE": os.environ.get("USERPROFILE", ""),
}

# --- M3 tripwire (optional): python-level registry WRITE access records+raises.
# Reads by the stdlib proxy auto-detection (urllib getproxies_registry ->
# HKCU\Internet Settings, executed before EVERY outbound HTTP request) are
# PASSED THROUGH to the real winreg and logged: read-only, machine-global,
# unavoidable without patching the stdlib; the no-write guarantee itself is
# enforced machine-wide by M4 (reg query diff).
ACCESS_LOG = []
import winreg as _REAL_WINREG  # noqa: E402  (captured BEFORE the block)


class _WinregBlock:
    __spec__ = None
    __name__ = "winreg"
    __loader__ = None
    __package__ = "winreg"
    __path__ = None
    __file__ = None
    __doc__ = "P1.8 M3 tripwire (not the real winreg)"

    def __getattr__(self, name):
        import traceback as _tb
        stack = "".join(_tb.format_stack()[:-1])
        if "getproxies" in stack or "proxy_bypass" in stack:
            # stdlib proxy detection: restore the real module and proceed
            sys.modules["winreg"] = _REAL_WINREG
            sys.modules["_winreg"] = _REAL_WINREG
            ACCESS_LOG.append(f"PASSTHROUGH (stdlib proxy read, read-only): {name}")
            return getattr(_REAL_WINREG, name)
        ACCESS_LOG.append(f"{name} :: " +
                          " <- ".join(_tb.format_stack()[:-1][-4:]))
        raise RuntimeError(f"P18-M3 winreg access blocked: {name}")


if tripwire:
    sys.modules["winreg"] = _WinregBlock()
    sys.modules["_winreg"] = _WinregBlock()

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)

faulthandler.dump_traceback_later(240, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))


def reg_snapshot():
    """M4 helper: read-only reg query -> (stdout or <absent>) for both keys.

    reg.exe speaks the OEM codepage on this machine (utf-8 decode of CP866
    output crashed the reader thread in the first run) — decode accordingly.
    """
    out = {}
    for label, cmd in (
        ("Software\\Supervertaler",
         ["reg", "query", r"HKCU\Software\Supervertaler", "/s"]),
        ("Run\\Supervertaler",
         ["reg", "query",
          r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
          "/v", "Supervertaler"]),
    ):
        p = subprocess.run(cmd, capture_output=True, timeout=30)
        body = (p.stdout + p.stderr).decode("oem", errors="replace").strip()
        out[label] = body if p.returncode == 0 else "<absent>"
    return out


def dir_snapshot(root: str):
    """Shallow content snapshot (rel path + size) of a real-env sentinel dir
    that pre-exists the run — so the post-check flags only NEW/changed files,
    not the machine's historical leftovers."""
    rows = {}
    base = pathlib.Path(root)
    if not base.is_dir():
        return None
    for p in base.rglob("*"):
        try:
            if p.is_file():
                rows[str(p.relative_to(base))] = p.stat().st_size
        except OSError:
            rows[str(p.relative_to(base))] = "<oserror>"
    return rows


def walk_dir(root: pathlib.Path):
    """Relative-path inventory (files + dirs) of a tree."""
    rows = []
    if not root.exists():
        return rows
    for p in sorted(root.rglob("*")):
        try:
            rel = str(p.relative_to(root))
            kind = "dir" if p.is_dir() else f"file:{p.stat().st_size}"
            rows.append(f"{rel} [{kind}]")
        except OSError as e:
            rows.append(f"{p.name} [oserror:{e}]")
    return rows


RESULT = {"tag": tag, "mode": mode, "tripwire": tripwire}
FAIL = []

reg_before = reg_snapshot()

# ---------- fake server (full mode only) ----------
if mode == "full":
    import re as _re
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class FakeHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8", "replace")) if length else {}
            model = body.get("model", "")
            messages = body.get("messages", [])
            user_content = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    c = m.get("content")
                    user_content = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                    break
            if "[SEGMENT " in user_content:
                nums = _re.findall(r"\[SEGMENT (\d{4})\]", user_content)
                content = "\n".join(f"[SEGMENT {n}] ✓" for n in nums) or "[SEGMENT 0001] ✓"
            else:
                content = "Goedemorgen"
            resp = {
                "id": "chatcmpl-fake", "object": "chat.completion", "created": 1,
                "model": model,
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
    RESULT["fake_port"] = PORT

# ---------- modal / file-dialog neutralization ----------
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
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)

import Supervertaler as SV  # noqa: E402

if mode == "full":
    # seed AFTER import, BEFORE app construction (same order as e2e probe)
    data_dir = iso / "Supervertaler"
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
        "general": {"restore_last_project": False},
    }
    sf.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
t0 = time.time()
win = SV.SupervertalerQt()
print(f"[{tag}] full app built ({time.time()-t0:.1f}s)", flush=True)
RESULT["app_built_s"] = round(time.time() - t0, 1)

for _ in range(100):
    app.processEvents()
    time.sleep(0.05)

# --- QuickTrans popup open/close (geometry write path, no network) ---
from modules.quicktrans import MTQuickPopup  # noqa: E402
MTQuickPopup.start_fetching = lambda self: None
popup = MTQuickPopup(win, "hello world")
popup.show()
for _ in range(10):
    app.processEvents()
popup.resize(640, 420)
popup.move(60, 40)
popup.close()
for _ in range(10):
    app.processEvents()
RESULT["popup_done"] = True

if mode == "full":
    # --- import sample txt -> project ---
    sample = str(tree / "user_data" / "samples" / "sample_en_nl.txt")
    if not pathlib.Path(sample).exists():
        sample = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-3\inputs\test.txt"
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (sample, ""))
    QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([sample], ""))
    import modules.file_dialog_helper as fdh  # noqa: E402
    save_target = iso / "Documents" / "test_proj.svproj"
    save_target.parent.mkdir(parents=True, exist_ok=True)
    fdh.get_save_file_name = staticmethod(
        lambda *a, **k: (str(save_target), ""))

    win.import_simple_txt()
    for _ in range(40):
        app.processEvents()
        time.sleep(0.05)
    n_seg = len(win.current_project.segments) if win.current_project else 0
    RESULT["imported_segments"] = n_seg
    if not n_seg:
        FAIL.append("full: no segments imported")

    # --- single-segment translation via fake server ---
    win.table.setCurrentCell(1, 2)
    if win.table.currentRow() < 0:
        win.table.selectRow(1)
    app.processEvents()
    win.translate_current_segment()
    for _ in range(20):
        app.processEvents()
    if win.current_project:
        tgt = win.current_project.segments[1].target
        RESULT["translated_target"] = tgt[:60]
        if not tgt:
            FAIL.append("full: segment 1 target empty after translate")

    # --- save project (nest_in_own_folder may nest it: Documents\test_proj\test_proj.svproj) ---
    win.save_project_as()
    for _ in range(20):
        app.processEvents()
    svproj_hits = [p for p in (iso / "Documents").rglob("*.svproj")]
    RESULT["svproj_saved"] = [str(p.relative_to(iso)) for p in svproj_hits]
    if not svproj_hits:
        FAIL.append("full: .svproj not saved")

# --- graceful close ---
win._really_quit = True
win.close()
for _ in range(5):
    app.processEvents()
    time.sleep(0.1)

faulthandler.cancel_dump_traceback_later()

# ---------- post-state inventory ----------
reg_after = reg_snapshot()
RESULT["reg_diff_empty"] = (reg_before == reg_after)
if not RESULT["reg_diff_empty"]:
    FAIL.append("M4: registry diff non-empty")
    RESULT["reg_before"] = reg_before
    RESULT["reg_after"] = reg_after

RESULT["modal_log"] = modal_log
RESULT["winreg_accesses"] = ACCESS_LOG
blocked = [a for a in ACCESS_LOG if not a.startswith("PASSTHROUGH")]
if blocked:
    FAIL.append(f"M3: {len(blocked)} blocked winreg accesses: "
                f"{[b.split(' ::')[0] for b in blocked]}")

iso_files = walk_dir(iso)
RESULT["iso_inventory"] = iso_files

# real-environment sentinels: flag only what is NEW or CHANGED by this run —
# the machine may carry pre-existing historical leftovers (APPDATA\Supervertaler,
# LOCALAPPDATA\Supervertaler\okapi-sidecar from pre-portable versions).
SENTINEL_NAMES = ("Supervertaler", ".supervertaler_config.json",
                  "Supervertaler-Workbench", "quicktrans.ini", "last_directory.json")
sentinels = {}
for label, base in (("APPDATA", REAL["APPDATA"]), ("LOCALAPPDATA", REAL["LOCALAPPDATA"]),
                    ("USERPROFILE", REAL["USERPROFILE"])):
    if not base:
        continue
    for name in SENTINEL_NAMES:
        pre_file = pathlib.Path(base) / name
        pre_dir_snap = dir_snapshot(str(pre_file)) if pre_file.is_dir() else None
        key = f"{label}\\{name}"
        if pre_file.is_dir():
            post_snap = dir_snapshot(str(pre_file))
            added = {k: v for k, v in (post_snap or {}).items()
                     if pre_dir_snap.get(k) != v}
            sentinels[key] = {"pre_existing_dir": True,
                              "new_or_changed_entries": added}
            if added:
                FAIL.append(f"real-env sentinel dir gained entries: {key}: {list(added)[:10]}")
        else:
            sentinels[key] = {"appeared_after_run": pre_file.exists()}
            if pre_file.exists():
                FAIL.append(f"real-env sentinel appeared after run: {key}")
if REAL["USERPROFILE"]:
    key = "USERPROFILE\\.config/autostart/supervertaler.desktop"
    sentinels[key] = {"appeared_after_run":
                      (pathlib.Path(REAL["USERPROFILE"]) / ".config" / "autostart"
                       / "supervertaler.desktop").exists()}
RESULT["real_sentinels"] = sentinels

# classification of iso findings
DATA_ROOT = "Supervertaler\\"
HARNESS_OWN = ("Documents\\test_proj.svproj", "Documents\\test_proj")
HARNESS_SKELETON = ("Desktop", "Documents", "Downloads", "tmp")
STATE_ROOT_FILES = {"quicktrans.ini", "last_directory.json"}
offenses = {"appdata": [], "userprofile_other": [], "tmp": [], "desktop_dl": []}
for row in iso_files:
    rel = row.split(" [")[0]
    if rel.startswith("AppData\\"):
        offenses["appdata"].append(rel)
    elif rel.startswith("tmp\\"):
        offenses["tmp"].append(rel)
    elif rel.startswith(("Desktop\\", "Downloads\\")):
        offenses["desktop_dl"].append(rel)
    elif rel.startswith("Documents\\"):
        if not any(rel == h or rel.startswith(h) for h in HARNESS_OWN):
            offenses["userprofile_other"].append(rel)
    elif rel == DATA_ROOT.rstrip("\\") or rel.startswith(DATA_ROOT):
        pass  # data root: expected
    elif rel in HARNESS_SKELETON:
        pass  # empty skeleton dirs created by the harness itself
    elif rel in STATE_ROOT_FILES:
        pass  # state_root service files: inside build root in the real build
    else:
        offenses["userprofile_other"].append(rel)
RESULT["iso_classification"] = {k: v for k, v in offenses.items()}
if offenses["appdata"]:
    FAIL.append(f"iso\\AppData non-empty ({len(offenses['appdata'])} entries)")
if offenses["userprofile_other"]:
    FAIL.append(f"iso root unexpected entries: {offenses['userprofile_other'][:10]}")
if offenses["desktop_dl"]:
    FAIL.append(f"iso Desktop/Downloads entries: {offenses['desktop_dl'][:10]}")
# tmp entries are REPORTED, not failed: %TEMP% transit files are the known
# T1-T3 class; Part B's start.bat redirects TEMP into the build root.
RESULT["tmp_entries"] = offenses["tmp"]

print(f"[{tag}] iso entries: {len(iso_files)}", flush=True)
print(f"[{tag}] AppData: {len(offenses['appdata'])}  tmp: {len(offenses['tmp'])}  "
      f"other: {len(offenses['userprofile_other'])}", flush=True)

RESULT["fail"] = FAIL
OUT.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False), encoding="utf-8")
if FAIL:
    print(f"P18-INV-FAIL {FAIL}", flush=True)
    sys.stdout.flush()
    os._exit(1)
print("P18-INV-OK", flush=True)
sys.stdout.flush()
os._exit(0)
