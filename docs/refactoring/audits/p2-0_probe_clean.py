"""P2.0 probe: clean runtime built only from requirements.txt.

Stages (each prints STAGE-OK / STAGE-FAIL):
  1. import Supervertaler (headless module import)
  2. offscreen full app start (SupervertalerQt instantiation, iso data root)
  3. real translation round-trip via LLMClient custom_openai -> mock server
  4. missing-but-imported extras: pdf_rescue_Qt (fitz), markitdown, anthropic
"""
import os, sys, traceback

REPO = r"E:\Dev\SupervertalerPortable"
sys.path.insert(0, r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\mock")
ISO = r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\iso"
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
        import threading, urllib.request, time as _t
        from mock_openai_server import Handler  # reuse handler def
        from http.server import HTTPServer
        # run mock server in-process on an ephemeral port
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

# --- Stage 4: known-broken extras in this runtime ------------------------
try:
    import importlib
    extras = {}
    for modname in ("fitz", "markitdown", "anthropic", "numpy", "sacrebleu", "boto3", "deepl", "psutil", "pynput", "setuptools"):
        try:
            importlib.import_module(modname)
            extras[modname] = "present"
        except Exception as e:
            extras[modname] = f"ABSENT ({type(e).__name__})"
    results["extras"] = ("INFO", extras)
    # pdf_rescue_Qt import attempt (fitz unguarded at its top level)
    try:
        importlib.import_module("modules.pdf_rescue_Qt")
        results["pdf_rescue_import"] = ("OK", "module imported")
    except Exception as e:
        results["pdf_rescue_import"] = ("FAIL", f"{type(e).__name__}: {e}")
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

print("\n===== P2.0 CLEAN-RUNTIME PROBE RESULTS =====")
for k, (status, detail) in results.items():
    print(f"[{status}] {k}: {detail}")
sys.stdout.flush()
os._exit(0)
