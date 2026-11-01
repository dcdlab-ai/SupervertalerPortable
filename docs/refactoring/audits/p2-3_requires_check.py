"""P2.3 addendum: does ANY remaining lock package (mandatory Requires-Dist, no extras)
require PyYAML / Markdown / packaging?"""
import os, email, re
ROOT = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p21\unpacked\python-embed\Lib\site-packages"
TARGETS = {"pyyaml", "markdown", "packaging"}
norm = lambda s: re.sub(r"[-_.]+", "-", s.lower()).strip()
remaining = [  # lock set minus the three being removed
    "annotated-types","anyio","certifi","charset-normalizer","et-xmlfile","h11","httpcore2",
    "httpx2","idna","jiter","lxml","openai","openpyxl","pillow","pydantic","pydantic_core",
    "pyperclip","PyQt6","PyQt6-Qt6","PyQt6_sip","pyspellchecker","python-docx","requests",
    "sniffio","spylls","truststore","typing_extensions","typing-inspection","urllib3",
]
rem_n = {norm(x) for x in remaining}
hits = []
for name in os.listdir(ROOT):
    if not name.endswith(".dist-info"):
        continue
    with open(os.path.join(ROOT, name, "METADATA"), encoding="utf-8", errors="replace") as f:
        msg = email.message_from_file(f)
    pkg = norm(msg.get("Name", name))
    for rd in [v for k, v in msg.items() if k.lower() == "requires-dist"]:
        m = re.match(r"\s*([A-Za-z0-9_.\-]+)", rd)
        if not m:
            continue
        dep = norm(m.group(1))
        if dep in TARGETS and pkg in rem_n:
            is_extra = "extra ==" in rd or "extra ==" in rd
            hits.append((pkg, rd.strip(), "EXTRA-ONLY" if "extra" in rd else "MANDATORY"))
print(f"checked {len(rem_n)} remaining lock packages")
if not hits:
    print("NO remaining lock package requires PyYAML/Markdown/packaging")
else:
    for h in hits:
        print("HIT:", h)
