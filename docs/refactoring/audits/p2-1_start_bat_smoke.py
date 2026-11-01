# -*- coding: utf-8 -*-
r"""BATCH P2.1 smoke: launch the UNPACKED build via its own start.bat
(the real launcher path), wait for the app to come up, close by PID.

Run with the DEV runtime (orchestration only):
  E:\Dev\python-embed\python.exe -u p2-1_start_bat_smoke.py <unpacked-root> <iso-dir>

Start detection: the clean first run creates the data root
<iso>\Supervertaler\workbench\... within ~1-2 min (database, prompt library,
hotkeys, sidecar). Process liveness is checked via the cmd/python process
tree. Close: graceful taskkill (WM_CLOSE) on the python PID, hard /F after a
30 s grace. Orphan sidecar processes of THIS run (sidecar jar path) are
enumerated by command line and killed individually (never by image name).

Prints P21-START-OK / P21-START-FAIL <reasons>.
"""
import os
import pathlib
import subprocess
import sys
import time

unpacked = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
FAIL = []
NOTE = []

env = dict(os.environ)
env["QT_QPA_PLATFORM"] = "offscreen"
env["SUPERVERTALER_DATA_ROOT"] = str(iso)
for var in ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA"):
    env[var] = str(iso / "_profile")
os.makedirs(env["USERPROFILE"], exist_ok=True)
os.makedirs(iso / "Supervertaler", exist_ok=True)
# TEMP/TMP and PYTHONPYCACHEPREFIX are (re)set by start.bat inside the build
# root; leaving ours in place only covers the pre-launch window.

log = open(unpacked / "start_smoke_console.log", "w", encoding="utf-8", errors="replace")
proc = subprocess.Popen(["cmd", "/c", "start.bat"], cwd=str(unpacked), env=env,
                        stdout=log, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
cmd_pid = proc.pid
print(f"[smoke] cmd pid={cmd_pid}", flush=True)


def children(pid):
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-CimInstance Win32_Process -Filter \"ParentProcessId={pid}\" "
         "| Select-Object -ExpandProperty ProcessId"],
        capture_output=True, text=True, timeout=30)
    return [int(x) for x in out.stdout.split() if x.strip().isdigit()]


def procs_of(pids):
    rows = []
    for pid in pids:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" "
             "| Select-Object -ExpandProperty CommandLine"],
            capture_output=True, text=True, timeout=30)
        rows.append((pid, out.stdout.strip()))
    return rows


# --- wait for startup: files in the data root -----------------------------
t0 = time.time()
started = False
data_root = iso / "Supervertaler"
while time.time() - t0 < 300:
    if proc.poll() is not None:
        FAIL.append(f"start.bat exited early, rc={proc.returncode}")
        break
    if any(data_root.rglob("*")):
        started = True
        break
    time.sleep(3)
dt = time.time() - t0
if started:
    n_files = sum(1 for _ in data_root.rglob("*") if _.is_file())
    print(f"[smoke] app data root populated in {dt:.0f}s ({n_files} files)", flush=True)
else:
    FAIL.append(f"no files in data root after {dt:.0f}s (or early exit)")

# let the app settle, then snapshot the process tree
time.sleep(20)
if proc.poll() is not None:
    FAIL.append("start.bat exited during settle window")
    tree_pids = []
else:
    tree_pids = [cmd_pid] + children(cmd_pid)
    while len(tree_pids) < 12:
        more = []
        for p in list(tree_pids):
            more += [c for c in children(p) if c not in tree_pids]
        if not more:
            break
        tree_pids += more
    print(f"[smoke] process tree: {procs_of(tree_pids)}", flush=True)

py_pid = None
for pid, cl in procs_of(tree_pids):
    if "python.exe" in (cl or "") and "Supervertaler.py" in (cl or ""):
        py_pid = pid
if py_pid is None and not FAIL:
    FAIL.append("Supervertaler.py python process not found in tree")

if py_pid:
    subprocess.run(["taskkill", "/PID", str(py_pid)], capture_output=True, timeout=30)
    for _ in range(15):
        # tasklist prints an OEM-codepage header (crashed the utf-8 reader
        # thread once) - use PowerShell for an ascii-safe liveness check
        chk = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"if (Get-Process -Id {py_pid} -ErrorAction SilentlyContinue) "
             "{'ALIVE'} else {'GONE'}"],
            capture_output=True, text=True, timeout=30)
        if "GONE" in chk.stdout or not "ALIVE" in chk.stdout:
            break
        time.sleep(2)
    else:
        print("[smoke] graceful close timed out (offscreen closeEvent shows a "
              "modal confirm - expected for an unattended run), using /F",
              flush=True)
        subprocess.run(["taskkill", "/F", "/PID", str(py_pid)],
                       capture_output=True, timeout=30)
        NOTE.append("graceful close timed out - hard kill /F used (offscreen "
                    "modal close-confirm, expected unattended)")
    print(f"[smoke] python pid {py_pid} closed", flush=True)

proc.wait(timeout=30)

# --- orphan sidecar cleanup (THIS run only, by command line) ---------------
out = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='java.exe'\" "
     "| Select-Object ProcessId, CommandLine | ConvertTo-Json -AsArray"],
    capture_output=True, timeout=30)  # bytes: PS writes the OEM codepage
import json
try:
    rows = json.loads((out.stdout or b"[]").decode("oem", errors="replace") or "[]")
except json.JSONDecodeError:
    rows = []
if isinstance(rows, dict):
    rows = [rows]
survivors = []
for row in rows:
    cl = (row.get("CommandLine") or "")
    pid = row.get("ProcessId")
    key = str(unpacked).lower()
    if key in cl.lower() or str(iso).lower() in cl.lower():
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        print(f"[smoke] killed orphan of this run: pid={pid} :: {cl[:120]}", flush=True)
    else:
        survivors.append(f"{pid} :: {cl[:80]}")
print("[smoke] unrelated survivors (left running):", *survivors[:5], sep="\n  ", flush=True)

log.close()
for n in NOTE:
    print(f"[smoke] NOTE: {n}", flush=True)
print("\nP21-START-OK" if not FAIL else f"\nP21-START-FAIL {FAIL}", flush=True)
sys.stdout.flush()
os._exit(0 if not FAIL else 1)
