"""BATCH P2.4 probe of the UNPACKED distributive (built from requirements.lock).

Stages (each prints STAGE-OK / STAGE-FAIL):
  1. headless imports of <unpacked>\\SupervertalerPortable (setup + modules.*)
  2. offscreen full app start (SupervertalerQt instantiation, iso data root)
  3. real translation round-trip via LLMClient custom_openai -> mock server
  4. Help -> About dialog shows v1.10.371 (QDialog.exec monkeypatched)
  5. optional/dev packages ABSENT inventory (pyyaml, markdown, packaging,
     markitdown, onnxruntime, vosk, faster_whisper, sounddevice, ahk, chardet,
     pytest, pygments, pyflakes)

Usage (unpacked-runtime python - the build's own interpreter):
  <unpacked>\\python-embed\\python.exe -u p2-4_probe_unpacked.py <unpacked-root> <stage-dir>
"""
import os
import sys
import time
import traceback
import pathlib

unpacked = pathlib.Path(sys.argv[1]).resolve()
STAGE = pathlib.Path(sys.argv[2]).resolve()
CODE = unpacked / "SupervertalerPortable"
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(STAGE / "mock"))
sys.path.insert(0, r"E:\Dev\SupervertalerPortable\docs\refactoring\audits")

ISO = STAGE / "iso_probe"
os.makedirs(ISO / "Supervertaler", exist_ok=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SUPERVERTALER_DATA_ROOT"] = str(ISO)
for var in ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA"):
    os.environ[var] = str(ISO / "_profile")
os.makedirs(os.environ["USERPROFILE"], exist_ok=True)
os.environ["TEMP"] = str(ISO / "_tmp")
os.environ["TMP"] = os.environ["TEMP"]
os.makedirs(os.environ["TEMP"], exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(ISO / "_pycache")

import faulthandler
faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)

results = {}

# --- Stage 1: headless imports -------------------------------------------
try:
    import importlib
    mods = ["setup"] + [
        "modules." + str(m.relative_to(CODE / "modules")).replace("\\", "/")[:-3]
        .replace("/", ".")
        for m in sorted((CODE / "modules").rglob("*.py"))
    ]
    ok, failed = 0, []
    for name in mods:
        try:
            importlib.import_module(name)
            ok += 1
        except Exception as e:
            failed.append((name, f"{type(e).__name__}: {e}"))
    results["headless"] = ("OK" if (ok, len(failed)) == (89, 1) else "FAIL",
                           f"{ok} ok / {len(failed)} fail / {len(mods)} total; "
                           f"fails={failed}")
except Exception as e:
    results["headless"] = ("FAIL", f"{type(e).__name__}: {e}")
    traceback.print_exc()

# --- Stage 2: offscreen app start -----------------------------------------
app = None
mw = None
try:
    t0 = time.time()
    import Supervertaler as sv  # noqa
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    mw = sv.SupervertalerQt()
    results["offscreen_start"] = ("OK", f"{time.time()-t0:.1f}s, "
                                  f"title={mw.windowTitle()!r}")
except Exception as e:
    results["offscreen_start"] = ("FAIL", f"{type(e).__name__}: {e}")
    traceback.print_exc()

# --- Stage 3: translation via mock server ---------------------------------
if mw is not None:
    try:
        import threading
        from mock_openai_server import Handler
        from http.server import HTTPServer
        srv = HTTPServer(("127.0.0.1", 0), Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        from modules.llm_clients import LLMClient
        client = LLMClient(api_key="mock-key", provider="custom_openai",
                           model="mock-model", base_url=f"http://127.0.0.1:{port}/v1",
                           timeout_seconds=20)
        t0 = time.time()
        out = client.translate("Hello world, this is a test.",
                               source_lang="English", target_lang="Russian")
        results["translate_mock"] = ("OK", f"{time.time()-t0:.1f}s, output={out!r}")
        srv.shutdown()
    except Exception as e:
        results["translate_mock"] = ("FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
else:
    results["translate_mock"] = ("SKIP", "no app instance")

# --- Stage 4: Help -> About version ---------------------------------------
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
        good = expected in title and sv.__version__ == "1.10.371"
        results["about_version"] = ("OK" if good else "FAIL",
                                    f"title={title!r}, expected {expected!r}")
    except Exception as e:
        results["about_version"] = ("FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
else:
    results["about_version"] = ("SKIP", "no app instance")

# --- Stage 5: absent-package inventory ------------------------------------
try:
    import importlib
    absent_must = {}
    for modname in ("yaml", "markdown", "packaging", "markitdown", "onnxruntime",
                    "vosk", "faster_whisper", "sounddevice", "ahk", "chardet",
                    "pytest", "pygments", "pyflakes", "anthropic",
                    "google.generativeai", "fitz", "PyQt6.QtWebEngineWidgets"):
        try:
            importlib.import_module(modname)
            absent_must[modname] = "PRESENT(!)"
        except Exception as e:
            absent_must[modname] = f"ABSENT ({type(e).__name__})"
    bad = [k for k, v in absent_must.items() if v == "PRESENT(!)"]
    results["absent_inventory"] = ("OK" if not bad else "FAIL",
                                   f"unexpectedly present: {bad}" if bad
                                   else "all optional/dev packages absent")
except Exception as e:
    results["absent_inventory"] = ("FAIL", str(e))

# --- negative profile control ----------------------------------------------
profile = ISO / "_profile"
strays = [str(p) for p in profile.rglob("*")
          if p.name not in (".supervertaler_config.json",)]
results["profile_negative"] = ("OK" if not strays else "FAIL",
                               f"strays in profile: {strays[:5]}" if strays
                               else "profile dir clean")

# --- cleanup ---------------------------------------------------------------
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

print("\n===== P2.4 UNPACKED-DISTRIBUTIVE PROBE RESULTS =====")
for k, (status, detail) in results.items():
    print(f"[{status}] {k}: {detail}")
sys.stdout.flush()
os._exit(0)
