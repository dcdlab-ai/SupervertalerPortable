import os, re, sys

ROOT = r"E:\Dev\SupervertalerPortable"
EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", "build", "dist"}

# Identifiers removed in 8.13a/8.13b: must have ZERO hits in app code
REMOVED = [
    "toggle_all_bridge", "on_bridge_toggle", "bridge_header_checkbox",
    "tm_select_all_bridge_btn", "tm_clear_all_bridge_btn",
    "import_po_file", "export_po_file", "po_handler", "POHandler",
    "PO (gettext)", "*.po", "GNU gettext", "import_po_action", "export_po_action",
    "po_source_file",
]
# Protected identifiers: must STILL be present (protection list)
PROTECTED = [
    "bridged_to_trados", "set_bridged_to_trados", "po_source_path",
    "_BILINGUAL_ORIGIN_ATTRS",
]

def walk():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)

hits_removed = {}
hits_protected = {}
for path in walk():
    rel = os.path.relpath(path, ROOT)
    try:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:
        print("READFAIL", rel, e); continue
    for name in REMOVED:
        for m in re.finditer(re.escape(name), text):
            line = text[:m.start()].count("\n") + 1
            hits_removed.setdefault(name, []).append(f"{rel}:{line}")
    for name in PROTECTED:
        for m in re.finditer(re.escape(name), text):
            line = text[:m.start()].count("\n") + 1
            hits_protected.setdefault(name, []).append(f"{rel}:{line}")

print("=== REMOVED identifiers (expect 0 hits) ===")
bad = 0
for name in REMOVED:
    lst = hits_removed.get(name, [])
    print(f"{name}: {len(lst)}")
    for h in lst:
        print(f"   {h}")
    bad += len(lst)

print("=== PROTECTED identifiers (expect >0 hits) ===")
for name in PROTECTED:
    lst = hits_protected.get(name, [])
    print(f"{name}: {len(lst)}")
    for h in lst:
        print(f"   {h}")

print("RESULT:", "FAIL" if bad else "REMOVED-CLEAN")
