"""P2.3 probe: runtime built ONLY from requirements.lock (clean Python 3.13.15).

Stages (each prints STAGE-OK / STAGE-FAIL):
  1. import Supervertaler (headless module import) + __version__
  2. offscreen full app start (SupervertalerQt instantiation, iso data root)
  3. real translation round-trip via LLMClient custom_openai -> mock server
  4. Help -> About dialog title shows v{__version__} (QDialog.exec monkeypatched)
  5. extras absent/present inventory in the lock runtime
"""
import os, sys, traceback

REPO = r"E:\Dev\SupervertalerPortable"
sys.path.insert(0, REPO)
sys.path.insert(0, r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p23\mock")
ISO = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p23\iso"
os.makedirs(os.path.join(ISO, "Supervertaler"), exist_ok=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SUPERVERTALER_DATA_ROOT"] = ISO
for var in ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA"):
    os.environ[var] = os.path.join(ISO, "_profile")
os.makedirs(os.environ["USERPROFILE"], exist_ok=True)
os.environ["TEMP"] = os.path.join(ISO, "_tmp")
os.environ["TMP"] = os.environ["TEMP"]
os.makedirs(os.environ["TEMP"], exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = os.path.join(ISO, "_pycache")

import faulthandler, time
faulthandler.dump_traceback_later(150, repeat=True, file=sys.stderr)

results = {}

# --- Stage 1: headless import -------------------------------------------
try:
    t0 = time.time()
    import Supervertaler as sv  # noqa
    results["import_supervertaler"] = ("OK", f"{time.time()-t0:.1f}s, version={getattr(sv, '__version__', '?')}")
except Exception as e:
    results["import_supervertaler"] = ("FAIL", f"{type(e).__name__}: {e}")
    traceback.print_exc()

# --- Stage 2: offscreen app start ---------------------------------------
app = None
mw = None
if results["import_supervertaler"][0] == "OK":
    try:
        t0 = time.time()
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        SupervertalerQt = sv.SupervertalerQt
        mw = SupervertalerQt()
        results["offscreen_start"] = ("OK", f"{time.time()-t0:.1f}s to instantiate, title={mw.windowTitle()!r}")
    except Exception as e:
        results["offscreen_start"] = ("FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
else:
    results["offscreen_start"] = ("SKIP", "stage 1 failed")

# --- Stage 3: translation via mock server --------------------------------
if mw is not None:
    try:
        import threading, time as _t
        from mock_openai_server import Handler  # reuse handler def
        from http.server import HTTPServer
        srv = HTTPServer(("127.0.0.1", 0), Handler)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        from modules.llm_clients import LLMClient
        client = LLMClient(api_key="mock-key", provider="custom_openai",
                           model="mock-model", base_url=f"http://127.0.0.1:{port}/v1",
                           timeout_seconds=20)
        t0 = _t.time()
        out = client.translate("Hello world, this is a test.", source_lang="English", target_lang="Russian")
        results["translate_mock"] = ("OK", f"{_t.time()-t0:.1f}s, output={out!r}" if isinstance(out, str) else f"output={out!r}")
        srv.shutdown()
    except Exception as e:
        results["translate_mock"] = ("FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
else:
    results["translate_mock"] = ("SKIP", "no app instance")

# --- Stage 4: Help -> About version --------------------------------------
if mw is not None:
    try:
        from PyQt6.QtWidgets import QDialog, QLabel
        captured = {}
        orig_exec = QDialog.exec
        def fake_exec(self, *a, **k):
            for lbl in self.findChildren(QLabel):
                t = lbl.text()
                if "Supervertaler Workbench v" in t:
                    captured["title"] = t
            return QDialog.DialogCode.Rejected
        QDialog.exec = fake_exec
        mw.show_about()
        QDialog.exec = orig_exec
        title = captured.get("title", "")
        expected = f"Supervertaler Workbench v{sv.__version__}"
        ok = expected in title and sv.__version__ == "1.10.371"
        results["about_version"] = ("OK" if ok else "FAIL", f"title={title!r}, expected {expected!r}")
    except Exception as e:
        results["about_version"] = ("FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
else:
    results["about_version"] = ("SKIP", "no app instance")

# --- Stage 5: extras inventory in the lock runtime ------------------------
try:
    import importlib
    extras = {}
    for modname in ("markitdown", "anthropic", "google.generativeai", "fitz", "numpy",
                    "sacrebleu", "boto3", "deepl", "psutil", "chardet", "pynput",
                    "vosk", "faster_whisper", "sounddevice", "ahk", "PyQt6.QtWebEngineWidgets",
                    "setuptools"):
        try:
            importlib.import_module(modname)
            extras[modname] = "present"
        except Exception as e:
            extras[modname] = f"ABSENT ({type(e).__name__})"
    results["extras"] = ("INFO", extras)
except Exception as e:
    results["extras"] = ("FAIL", str(e))

# --- cleanup --------------------------------------------------------------
if mw is not None:
    try:
        mw.close()
    except Exception:
        pass
if app is not None:
    try:
        app.quit()
    except Exception:
        pass

print("\n===== P2.3 LOCK-RUNTIME PROBE RESULTS =====")
for k, (status, detail) in results.items():
    print(f"[{status}] {k}: {detail}")
sys.stdout.flush()
os._exit(0)
