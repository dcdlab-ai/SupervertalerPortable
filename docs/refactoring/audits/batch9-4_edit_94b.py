# Batch 9.4b editor: keepwarm cluster + _apply_ollama_timeout_setting +
# _apply_gemini_proxy + all call sites. Bottom-up, py_compile after each.
import pathlib, subprocess, sys

ROOT = pathlib.Path(r"E:\Dev\SupervertalerPortable")
PY = r"E:\Dev\python-embed\python.exe"
F = ROOT / "Supervertaler.py"

raw = F.read_bytes()
lines = raw.decode("utf-8").split("\r\n")
assert len(lines) == 55188, len(lines)

EDITS = [
    (47657, 47669, []),   # _apply_gemini_proxy method + trailing blank
    (23339, 23340, []),   # save: "# Re-apply Gemini env vars" + call
    (7623, 7697, []),     # keepwarm cluster (5 methods) + trailing blank
    (7554, 7557, []),     # init: keepwarm timer + setup + timeout calls
    (6362, 6363, []),     # startup: gemini proxy comment + call
]

for i, (a, b, repl) in enumerate(EDITS, 1):
    assert lines[a-1].strip().startswith(("def _apply_gemini_proxy", "# Re-apply Gemini env vars",
        "def _setup_ollama_keepwarm", "# Initialize Ollama keep-warm timer",
        "# Apply proxy env vars for Gemini")), (i, lines[a-1][:60])
    lines[a-1:b] = repl
    out = "\r\n".join(lines).encode("utf-8")
    F.write_bytes(out)
    r = subprocess.run([PY, "-m", "py_compile", str(F)], capture_output=True, text=True)
    crlf = out.count(b"\r\n"); lf = out.count(b"\n"); dcr = out.count(b"\r\r\n")
    print(f"edit {i} ({a}-{b} -> {len(repl)}): rc={r.returncode} lines={len(lines)} CRLF={crlf} LF={lf} dCR={dcr}")
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    if lf != crlf or dcr != 0:
        print("EOL ANOMALY"); sys.exit(1)

print("ALL 9.4b EDITS OK; final line count:", len(lines))
