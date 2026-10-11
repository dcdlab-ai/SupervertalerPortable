import importlib, pathlib, sys
sys.path.insert(0, r"E:\Dev\SupervertalerPortable")
mods = sorted(pathlib.Path(r"E:\Dev\SupervertalerPortable\modules").rglob("*.py"))
names = ["setup"] + [
    "modules." + str(m.relative_to(r"E:\Dev\SupervertalerPortable\modules")).replace("\\", "/")[:-3].replace("/", ".")
    for m in mods
]
ok, fail = 0, []
for name in names:
    try:
        importlib.import_module(name)
        ok += 1
    except Exception as e:
        fail.append((name, f"{type(e).__name__}: {e}"))
print(f"headless imports (with setup.py): {ok} ok / {len(fail)} fail / {len(names)} total")
for n, e in fail:
    print(f"FAIL {n}: {e}")
