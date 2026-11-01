# -*- coding: utf-8 -*-
r"""BATCH P2.1 probe: verify the UNPACKED zip built by the new packager.

Run BY the unpacked runtime's own interpreter, e.g.:
  <unpacked>\python-embed\python.exe -u p2-1_probe_unpacked.py <unpacked-root> <iso-dir>

Stages (each prints [OK]/[FAIL]/[INFO]):
  1. headless import of every modules/**/*.py + setup.py  (P1.8 baseline: 89/2,
     known fails = setup.py[setuptools], modules.pdf_rescue_Qt[fitz])
  2. offscreen app start (SupervertalerQt instantiation, iso data root)
  3. real translation round-trip via LLMClient custom_openai -> mock server
     (docs/refactoring/audits/p2-0_mock_openai_server.py, in-process)
  4. exclusions: dev junk ABSENT from the unpacked runtime, pip PRESENT
"""
import faulthandler
import importlib
import os
import pathlib
import sys
import time
import traceback

unpacked = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
code = unpacked / "SupervertalerPortable"
sys.path.insert(0, str(code))
AUDITS = pathlib.Path(r"E:\Dev\SupervertalerPortable\docs\refactoring\audits")
# load the P2.0 mock server by file path (its name carries the p2-0_ prefix)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("mock_openai_server", AUDITS / "p2-0_mock_openai_server.py")
_mock_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mock_mod)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)
for var in ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA"):
    os.environ[var] = str(iso / "_profile")
os.makedirs(os.environ["USERPROFILE"], exist_ok=True)
os.environ["TEMP"] = str(iso / "_tmp")
os.environ["TMP"] = os.environ["TEMP"]
os.makedirs(os.environ["TEMP"], exist_ok=True)
os.environ["PYTHONPYCACHEPREFIX"] = str(iso / "_pycache")
os.makedirs(os.path.join(iso, "Supervertaler"), exist_ok=True)

faulthandler.dump_traceback_later(180, repeat=True, file=sys.stderr)
results = {}

# --- Stage 1: headless import-all ----------------------------------------
mods = sorted((code / "modules").rglob("*.py"))
names = ["setup"] + [
    "modules." + str(m.relative_to(code / "modules")).replace("\\", "/")[:-3].replace("/", ".")
    for m in mods
]
ok, fail = 0, []
for name in names:
    try:
        importlib.import_module(name)
        ok += 1
    except Exception as e:
        fail.append((name, f"{type(e).__name__}: {e}"))
results["headless_imports"] = ("INFO" if (ok == 89 and len(fail) == 2) else "FAIL",
                               f"{ok} ok / {len(fail)} fail / {len(names)} total; "
                               f"fails={[n for n, _ in fail]}")
for n, e in fail:
    print(f"  headless FAIL {n}: {e}", flush=True)

# --- Stage 2: offscreen app start -----------------------------------------
app = None
mw = None
try:
    t0 = time.time()
    import Supervertaler as sv  # noqa
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    mw = sv.SupervertalerQt()
    results["offscreen_start"] = ("OK", f"{time.time()-t0:.1f}s, title={mw.windowTitle()!r}")
except Exception as e:
    results["offscreen_start"] = ("FAIL", f"{type(e).__name__}: {e}")
    traceback.print_exc()

# --- Stage 3: translation via mock server ---------------------------------
if mw is not None:
    try:
        import threading
        import urllib.request  # noqa: F401
        from http.server import HTTPServer
        Handler = _mock_mod.Handler
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
        good = isinstance(out, str) and "Hello world" in out
        results["translate_mock"] = ("OK" if good else "FAIL",
                                     f"{time.time()-t0:.1f}s, output={out!r}")
        srv.shutdown()
    except Exception as e:
        results["translate_mock"] = ("FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
else:
    results["translate_mock"] = ("SKIP", "no app instance")

# --- Stage 4: exclusions present/absent ------------------------------------
try:
    junk = ["pygments", "pytest", "_pytest", "iniconfig", "pluggy", "colorama",
            "pyflakes", "chardet"]
    present_junk = [m for m in junk if importlib.util.find_spec(m) is not None]
    sp = unpacked / "python-embed" / "Lib" / "site-packages"
    junk_dirs = [d for d in sp.iterdir()
                 if d.name.split("-")[0].lower() in junk or d.name.lower() in junk]
    pip_spec = importlib.util.find_spec("pip")
    getpip = (unpacked / "python-embed" / "get-pip.py").exists()
    status = "OK" if not present_junk and not junk_dirs and pip_spec and not getpip else "FAIL"
    results["exclusions"] = (status,
                             f"importable junk={present_junk}, dirs={junk_dirs}, "
                             f"pip={'present' if pip_spec else 'MISSING'}, "
                             f"get-pip.py={'present' if getpip else 'absent'}")
except Exception as e:
    results["exclusions"] = ("FAIL", f"{type(e).__name__}: {e}")

# --- cleanup ----------------------------------------------------------------
if mw is not None:
    try:
        mw._really_quit = True
        mw.close()
    except Exception:
        pass
if app is not None:
    try:
        app.quit()
    except Exception:
        pass

print("\n===== P2.1 UNPACKED-BUILD PROBE RESULTS =====")
verdict = "P21-PROBE-OK"
for k, (status, detail) in results.items():
    print(f"[{status}] {k}: {detail}")
    if status == "FAIL":
        verdict = "P21-PROBE-FAIL"
print(verdict, flush=True)
sys.stdout.flush()
os._exit(0 if verdict == "P21-PROBE-OK" else 1)
