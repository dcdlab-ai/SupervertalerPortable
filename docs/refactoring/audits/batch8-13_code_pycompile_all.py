import py_compile, subprocess, sys, pathlib
files = subprocess.run(["git", "ls-files", "*.py"], capture_output=True, text=True,
                       cwd=r"E:\Dev\SupervertalerPortable").stdout.split()
ok, fail = 0, []
for f in files:
    try:
        py_compile.compile(f, doraise=True, cfile=r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\b8-13\_pyc.pyc")
        ok += 1
    except Exception as e:
        fail.append((f, str(e)))
print(f"py_compile: {ok} ok / {len(fail)} fail / {len(files)} total")
for f, e in fail:
    print(f"FAIL {f}: {e}")
