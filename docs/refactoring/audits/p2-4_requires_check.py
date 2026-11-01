"""BATCH P2.4, Part A.1: does ANY package in requirements.lock require
PyYAML / Markdown / packaging (mandatory Requires-Dist, extras excluded)?

METADATA source: the verified P2.1 distributive
(E:\\Dev\\Work_temp\\SupervertalerPortable\\refactoring\\batch-p21\\unpacked),
which contains every lock package's dist-info at the pinned version.
Lock set is parsed from requirements.lock itself (29 entries).
Output: one line per lock package = table for the report.
"""
import email
import os
import re

REPO = r"E:\Dev\SupervertalerPortable"
ROOT = (r"E:\Dev\Work_temp\SupervertalerPortable\refactoring"
        r"\batch-p21\unpacked\python-embed\Lib\site-packages")
TARGETS = {"pyyaml", "markdown", "packaging"}
norm = lambda s: re.sub(r"[-_.]+", "-", s.lower()).strip()

lock = []
with open(os.path.join(REPO, "requirements.lock"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            name, _, ver = line.partition("==")
            lock.append((norm(name), name, ver))

# dist-info directory per normalized package name (Name from METADATA;
# the dir name itself is ambiguous: the last "-" is inside ".dist-info")
distinfos = {}
for entry in os.listdir(ROOT):
    if entry.endswith(".dist-info"):
        mpath = os.path.join(ROOT, entry, "METADATA")
        with open(mpath, encoding="utf-8", errors="replace") as f:
            pkg = email.message_from_file(f).get("Name", "")
        if pkg:
            distinfos[norm(pkg)] = entry

rows, missing = [], []
for nname, oname, ver in lock:
    di = distinfos.get(nname)
    if not di:
        missing.append(oname)
        continue
    with open(os.path.join(ROOT, di, "METADATA"),
              encoding="utf-8", errors="replace") as f:
        msg = email.message_from_file(f)
    meta_ver = msg.get("Version", "?")
    hits = []
    for k, v in msg.items():
        if k.lower() != "requires-dist":
            continue
        m = re.match(r"\s*([A-Za-z0-9_.\-]+)", v)
        if m and norm(m.group(1)) in TARGETS:
            kind = "EXTRA" if "extra ==" in v else "MANDATORY"
            hits.append((v.strip(), kind))
    rows.append((oname, ver, meta_ver, hits))

for oname, ver, meta_ver, hits in rows:
    if hits:
        detail = "; ".join(f"{t} [{k}]" for t, k in hits)
        print(f"{oname}=={ver} (dist-info {meta_ver}): {detail}")
    else:
        print(f"{oname}=={ver} (dist-info {meta_ver}): -")

print(f"\nchecked {len(rows)} lock packages; dist-info missing: "
      f"{missing if missing else 'none'}")
mandatory_hits = [(r[0], h) for r in rows for h in r[3] if h[1] == "MANDATORY"]
print("VERDICT:", "FAIL - mandatory requires exist: " + repr(mandatory_hits)
      if mandatory_hits
      else "CLEAN - no lock package requires PyYAML/Markdown/packaging "
           "(extras excluded)")
