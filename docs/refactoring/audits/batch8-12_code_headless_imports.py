import importlib, pathlib, sys, traceback
sys.path.insert(0, r"E:\Dev\SupervertalerPortable")
mods = sorted(pathlib.Path(r"E:\Dev\SupervertalerPortable\modules").rglob("*.py"))
ok, fail = 0, []
for m in mods:
    name = "modules." + m.relative_to(r"E:\Dev\SupervertalerPortable\modules").with_suffix("").asposix.replace("/", ".") if False else "modules." + str(m.relative_to(r"E:\Dev\SupervertalerPortable\modules")).replace("\\", "/")[:-3].replace("/", ".")
    try:
        importlib.import_module(name)
        ok += 1
    except Exception as e:
        fail.append((name, f"{type(e).__name__}: {e}"))
print(f"headless imports: {ok} ok / {len(fail)} fail / {len(mods)} total")
for n, e in fail:
    print(f"FAIL {n}: {e}")
