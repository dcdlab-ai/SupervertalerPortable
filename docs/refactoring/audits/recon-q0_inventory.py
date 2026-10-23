"""RECON Q.0 audit inventory (read-only).

Inventories for the Match Panel / QuickTrans reconnaissance report:
 1. Dead-chain reachability: caller counts for the legacy Translation-Results
    lookup chain and the deprecated panel builder.
 2. target-cell setPlainText sites with/without a blockSignals wrapper
    (NBSP exposure, M2.3 finding) around QuickTrans insert paths.
 3. is_image_links_only call sites (product code).
 4. QuickTrans request entry points (modules/quicktrans.py).
 5. mtql_* settings keys: definition/read/write sites.
 6. Monolith baseline (line count + sha256) at the recon HEAD.

Run with the bundled runtime from the project root:
  E:\\Dev\\python-embed\\python.exe -u docs\\refactoring\\audits\\recon-q0_inventory.py
"""
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MONOLITH = os.path.join(ROOT, "Supervertaler.py")
QUICKTRANS = os.path.join(ROOT, "modules", "quicktrans.py")
BMH = os.path.join(ROOT, "modules", "bilingual_markdown_handler.py")


def read_lines(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read().splitlines()


def grep(path, pattern):
    out = []
    rx = re.compile(pattern)
    for i, line in enumerate(read_lines(path), 1):
        if rx.search(line):
            out.append((i, line.strip()))
    return out


print("=" * 72)
print("RECON Q.0 INVENTORY  (read-only, HEAD 8507dd55 product code)")
print("=" * 72)

# 1. Dead-chain reachability -------------------------------------------------
print("\n[1] Legacy chain caller counts (0 = unreachable in live app)")
targets = [
    "_schedule_delayed_lookup",
    "_perform_delayed_lookup",
    "_fetch_llm_translation_async",
    "_fetch_mt_translation_async",
    "_add_mt_and_llm_matches_progressive",
    "_add_mt_and_llm_matches",
    "create_assistance_panel",
    "_show_instant_tm_match",
    "_update_both_termlens",
    "request_update",
]
for name in targets:
    hits = grep(MONOLITH, rf"\b{re.escape(name)}\b")
    defs = [i for i, t in hits if t.startswith("def ") or t.startswith("async def ")]
    calls = [i for i, t in hits if i not in defs]
    print(f"  {name:<38} defs={len(defs)} refs={len(calls)} def@{defs} call@{calls[:8]}")

# assistance_widget assignment (AST-verified absence)
import ast
tree = ast.parse(open(MONOLITH, encoding="utf-8").read())
assigns = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            if isinstance(tgt, ast.Attribute) and tgt.attr == "assistance_widget":
                assigns.append(node.lineno)
print(f"  assistance_widget assignments in monolith: {assigns} "
      f"(empty = gate never opens)")

# 2. target-cell setPlainText sites and blockSignals proximity ----------------
print("\n[2] target-cell setPlainText sites (M2 NBSP list) + blockSignals check")
M2_LIST = [7519, 7523, 26008, 35785, 40524, 41302, 45770, 46251,
           46787, 46974, 49167, 49336, 49595, 51970]
lines = read_lines(MONOLITH)
for ln in M2_LIST:
    ctx = "\n".join(lines[ln - 4:ln + 1])
    wrapped = "blockSignals(True)" in ctx
    print(f"  {MONOLITH.split(os.sep)[-1]}:{ln:<6} blockSignals={wrapped}  {lines[ln-1].strip()[:70]}")

extra = [i for i, t in grep(MONOLITH, r"\btarget_widget\.setPlainText\(")]
print(f"  total target_widget.setPlainText sites: {len(extra)} -> {extra}")

# 3. is_image_links_only call sites -------------------------------------------
print("\n[3] is_image_links_only")
print(f"  def: {BMH.split(os.sep)[-1]}:{grep(BMH, 'def is_image_links_only')[0][0]}")
for i, t in grep(MONOLITH, r"\bis_image_links_only\b"):
    print(f"  Supervertaler.py:{i:<6} {t[:78]}")
qt_hits = grep(QUICKTRANS, r"is_image_links_only")
print(f"  quicktrans.py call sites: {len(qt_hits)} (0 = no gate in QuickTrans)")

# 4. QuickTrans request entry points ------------------------------------------
print("\n[4] QuickTrans request entry points (modules/quicktrans.py)")
for i, t in grep(QUICKTRANS, r"MTFetchWorker\(|\.start\(\)|worker\.quit\(\)|closeEvent|_debounce|_fetch_token|isVisible\(\)"):
    print(f"  quicktrans.py:{i:<6} {t[:76]}")

# 5. mtql_* keys ---------------------------------------------------------------
print("\n[5] mtql_* keys")
for i, t in grep(MONOLITH, r"mtql_[a-z_]+"):
    print(f"  Supervertaler.py:{i:<6} {t[:90]}")
for i, t in grep(QUICKTRANS, r"mtql_[a-z_]+"):
    print(f"  quicktrans.py:{i:<6} {t[:90]}")

# 6. baseline -----------------------------------------------------------------
print("\n[6] baseline")
raw = open(MONOLITH, "rb").read()
print(f"  Supervertaler.py lines={raw.count(b'\n') + 1} sha256={hashlib.sha256(raw).hexdigest()}")
raw2 = open(QUICKTRANS, "rb").read()
print(f"  modules/quicktrans.py lines={raw2.count(b'\n') + 1} sha256={hashlib.sha256(raw2).hexdigest()}")
print("\nDONE")
