# -*- coding: utf-8 -*-
"""M2 batch manifest: sha256 + line count + EOL for Supervertaler.py + modules/**.py."""
import hashlib, json, pathlib, sys

root = pathlib.Path(r"E:\Dev\SupervertalerPortable")
tag = sys.argv[1] if len(sys.argv) > 1 else "base"
files = [root / "Supervertaler.py"] + sorted(root.glob("modules/**/*.py"))
out = {}
for f in files:
    if "__pycache__" in str(f):
        continue
    b = f.read_bytes()
    rel = f.relative_to(root).as_posix()
    out[rel] = {
        "sha256": hashlib.sha256(b).hexdigest(),
        "lines": b.count(b"\n"),
        "crlf": b.count(b"\r\n"),
        "bare_lf": b.count(b"\n") - b.count(b"\r\n"),
    }
outp = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\batch-m2") / f"manifest_{tag}.json"
outp.write_text(json.dumps(out, indent=1), encoding="utf-8")
print("monolith:", json.dumps(out["Supervertaler.py"]))
print("modules/tag_manager.py:", json.dumps(out.get("modules/tag_manager.py")))
print("modules/bilingual_markdown_handler.py:", json.dumps(out.get("modules/bilingual_markdown_handler.py")))
print("modules/llm_clients.py:", json.dumps(out.get("modules/llm_clients.py")))
print("modules/workers/proofread.py:", json.dumps(out.get("modules/workers/proofread.py")))
print("files tracked:", len(out))
