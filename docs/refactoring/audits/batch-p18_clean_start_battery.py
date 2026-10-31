# -*- coding: utf-8 -*-
r"""BATCH P1.8 Part D: clean-start battery M1+M3+M4 in ONE script.

M1  static gate, in-process, on the product tree:
    - winreg mentions in code (Supervertaler.py + modules/) = 0
    - HKCU / CurrentVersion\Run literals in code = 0
    - os.environ APPDATA/LOCALAPPDATA/USERPROFILE reads in code = 0
    - QSettings constructor audit (AST): the two-string-arg form
      QSettings("org","app") (Qt6 forces NativeFormat) and any explicit
      NativeFormat are banned; IniFormat sites are listed.
M4  `reg query HKCU\Software\Supervertaler /s` + the HKCU Run value,
    read-only, taken BEFORE and AFTER the run below; diff by body = empty.
M3  the run itself is a subprocess (winreg tripwire must precede product
    imports): batch-p18_probe_inventory.py in mode "full" + "tripwire" —
    empty isolated profile, start, QuickTrans popup, import, translate via
    fake server, save project, graceful close. The probe also verifies
    nothing appears in iso\AppData, iso\Desktop/Downloads, or the REAL
    environment (sentinel dirs diffed pre/post).

Verdicts: P18-BATTERY-OK / P18-BATTERY-FAIL <reasons>.
Run: python batch-p18_clean_start_battery.py [tree-root]
"""
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else \
    pathlib.Path(r"E:\Dev\SupervertalerPortable")
STAGE = pathlib.Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p18")
STAGE.mkdir(parents=True, exist_ok=True)
OUT = STAGE / "battery_p18.json"
PY = sys.executable
PROBE = ROOT / "docs" / "refactoring" / "audits" / "batch-p18_probe_inventory.py"

FAIL = []
RESULT = {"tree_root": str(ROOT)}

# ---------------------------------------------------------------- M1 (static)
def product_files():
    yield ROOT / "Supervertaler.py"
    for p in sorted((ROOT / "modules").rglob("*.py")):
        yield p


CODE_LINE = re.compile(r"^\s*(#|$)")  # skip blank/pure-comment lines


def code_lines(src):
    for i, line in enumerate(src.split("\n"), 1):
        s = line.strip()
        if s.startswith("#") or not s:
            continue
        yield i, line


m1 = {}
winreg_hits, hkcu_hits, env_hits, qs_files = [], [], [], []
for f in product_files():
    src = f.read_bytes().decode("utf-8")
    rel = str(f.relative_to(ROOT))
    for i, line in code_lines(src):
        if re.search(r"\bwinreg\b|import\s+_winreg|\b_winreg\b", line):
            winreg_hits.append(f"{rel}:{i}")
        if re.search(r"HKCU|CurrentVersion\\\\Run", line):
            hkcu_hits.append(f"{rel}:{i}")
        if re.search(r"environ\[.[\"'](APPDATA|LOCALAPPDATA|USERPROFILE)|"
                     r"getenv\(.[\"'](APPDATA|LOCALAPPDATA|USERPROFILE)", line):
            env_hits.append(f"{rel}:{i}")
    if "QSettings" in src:
        qs_files.append(rel)
m1["winreg"] = winreg_hits
m1["hkcu"] = hkcu_hits
m1["env_profile_reads"] = env_hits
m1["qsettings_files"] = qs_files
if winreg_hits:
    FAIL.append(f"M1: winreg code mentions: {winreg_hits[:10]}")
if hkcu_hits:
    FAIL.append(f"M1: HKCU literals: {hkcu_hits[:10]}")
if env_hits:
    FAIL.append(f"M1: profile env reads: {env_hits[:10]}")

# QSettings AST audit (same rule as batch9-3_grep_gate.py Part C section)
def qsettings_audit(fname, src):
    import ast
    rows = []
    tree = ast.parse(src)
    n_sites = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else "")
        if name != "QSettings":
            continue
        n_sites += 1
        where = f"{fname}:{node.lineno}"
        strs = [a for a in node.args
                if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if len(node.args) >= 2 and len(strs) == len(node.args):
            rows.append(f"FAIL {where}: two-arg string QSettings -> NativeFormat")
        if "NativeFormat" in ast.dump(node) :
            rows.append(f"FAIL {where}: explicit NativeFormat")
    return n_sites, rows


qs_report = []
for rel in qs_files:
    n, rows = qsettings_audit(rel, (ROOT / rel).read_bytes().decode("utf-8"))
    qs_report.append(f"{rel}: {n} site(s), "
                     + ("VIOLATIONS: " + "; ".join(rows) if rows else "all IniFormat/portable"))
    FAIL.extend(f"M1 {r}" for r in rows)
m1["qsettings_report"] = qs_report
RESULT["M1"] = m1

# ---------------------------------------------------------------- M4 pre
def reg_snapshot():
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


reg_before = reg_snapshot()

# ------------------------------------------------- M3 + full cycle (subprocess)
iso = STAGE / "iso-battery"
subprocess.run(["cmd", "/c", f"rmdir /s /q {iso}"], capture_output=True)
p = subprocess.run(
    [PY, "-u", str(PROBE), str(ROOT), str(iso), "p18battery", "full", "tripwire"],
    capture_output=True, text=True, errors="replace", timeout=900,
    cwd=str(ROOT))
RESULT["probe_exit"] = p.returncode
RESULT["probe_tail"] = "\n".join((p.stdout or "").strip().split("\n")[-6:])
inv = STAGE / "inventory_p18battery.json"
if inv.exists():
    d = json.loads(inv.read_text(encoding="utf-8"))
    RESULT["probe_fail"] = d.get("fail")
    RESULT["probe_winreg_accesses"] = d.get("winreg_accesses")
    FAIL.extend(f"M3/cycle {r}" for r in d.get("fail", []))
else:
    FAIL.append("battery: probe JSON missing")
if p.returncode != 0:
    FAIL.append(f"battery: probe exit {p.returncode}")

# ---------------------------------------------------------------- M4 post
reg_after = reg_snapshot()
RESULT["M4_diff_empty"] = (reg_before == reg_after)
if not RESULT["M4_diff_empty"]:
    FAIL.append("M4: registry diff non-empty")
    RESULT["M4_before"] = reg_before
    RESULT["M4_after"] = reg_after

# post-assert: iso\AppData empty (probe asserted too; belt-and-braces here)
appd = iso / "AppData"
if appd.exists() and any(appd.rglob("*")):
    FAIL.append("battery: iso\\AppData non-empty after cycle")

RESULT["fail"] = FAIL
OUT.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False), encoding="utf-8")
if FAIL:
    print(f"P18-BATTERY-FAIL {FAIL}", flush=True)
    sys.exit(1)
print("P18-BATTERY-OK", flush=True)
