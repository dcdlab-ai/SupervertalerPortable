# -*- coding: utf-8 -*-
"""Batch P1-B: make suite probe copies wired to the new data-path seam.

Each copy is derived from its P1-A copy (batch-p1a_<name>, which already has
the 2-line usage_statistics stub removed) by exactly two edits (STEP 4 test
seam); batch8-15_regress_common.py has no P1-A copy and is taken from the
original:
  1. os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  -- inserted right after
     the TMP env line, so the app resolves its data root to <iso>/Supervertaler
     (the same location the old pointer seeding used to select);
  2. the config.json pointer-write block is deleted (lines
       cfg_dir = iso / "AppData" / "Roaming" / "Supervertaler"
       cfg_dir.mkdir(...)
       (cfg_dir / "config.json").write_text(
           '{"user_data_path": ...
       [)]
     -- the product no longer reads the pointer, so the harness must not
     pretend it does). batch8-15_probe_window.py has no pointer block (its
     data dir comes from argv over a pre-seeded iso); it only gets edit 1.

USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP/TMP stay pointed at the isolated
profile exactly as before -- they are the negative control: on the new code
nothing may appear there.

Copies are written to docs/refactoring/audits/ as batch-p1b_<orig>.py.
The originals are NOT modified; the batch-p1a copies stay frozen as historical
(P1-A report rule: old probes are not rerun on new code).
"""
import hashlib
import pathlib
import re

AUD = pathlib.Path(r"E:\Dev\SupervertalerPortable\docs\refactoring\audits")
NAMES = [
    "batch9-4_probe_94h_fallback.py",
    "batch9-4_probe_94f_profiles.py",
    "batch9-4_probe_94d_qtchat.py",
    "batch9-4_probe_94c_statusbar.py",
    "batch9-3_probe_llm_e2e.py",
    "batch8-15_probe_window.py",
    "batch8-13_code_tools_smoke.py",
    "batch8-15_regress_termbase.py",
    "batch8-15_probe_about.py",
    "batch9-4_probe_94a_save.py",
    "r9_probe_profiles.py",
    "batch8-15_regress_common.py",
]
ENV_LINE = 'os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)  # P1-B seam: data root -> <iso>/Supervertaler\n'
TMP_LINE = 'os.environ["TMP"] = str(iso / "tmp")'
RE_CFG_DEF = re.compile(r'^cfg(?:_dir)? = iso / "AppData" / "Roaming" / "Supervertaler"\s*$')
RE_CFG_MK = re.compile(r'^cfg(?:_dir)?\.mkdir\(parents=True, exist_ok=True\)\s*$')
RE_CFG_W = re.compile(r'^\(cfg(?:_dir)? / "config\.json"\)\.write_text\(\s*$')

out = []
for name in NAMES:
    p1a = AUD / f"batch-p1a_{name}"
    src = p1a if p1a.exists() else (AUD / name)
    lines = src.read_bytes().decode("utf-8").splitlines(keepends=True)
    new, removed, i = [], [], 0
    while i < len(lines):
        ln = lines[i]
        if RE_CFG_W.match(ln):
            # pointer write: the json line, then an optional standalone ")"
            removed.append(ln)
            i += 1
            nxt = lines[i]
            removed.append(nxt)
            i += 1
            if nxt.rstrip().endswith(")"):
                pass  # 2-line form: closing paren on the json line
            else:
                third = lines[i]
                assert third.strip() == ")", (name, third)
                removed.append(third)
                i += 1
            continue
        if RE_CFG_DEF.match(ln) or RE_CFG_MK.match(ln):
            removed.append(ln)
            i += 1
            continue
        new.append(ln)
        if ln.rstrip("\r\n") == TMP_LINE:
            new.append(ENV_LINE)
        i += 1
    text = "".join(new)
    assert ENV_LINE.strip() in text, name
    joined = "".join(removed)
    if removed:
        assert '"config.json"' in joined and "user_data_path" in joined, name
        # nothing pointer-related may survive in the copy
        assert "user_data_path" not in text and '"config.json"' not in text, name
    assert "usage_statistics" not in text, name
    assert 'SUPERVERTALER_DATA_ROOT' not in (AUD / name).read_text(encoding="utf-8"), name
    copy = AUD / f"batch-p1b_{name}"
    copy.write_bytes(text.encode("utf-8"))
    out.append(f"{hashlib.sha256(copy.read_bytes()).hexdigest()[:16]}  {copy.name}  "
               f"-{len(removed)} lines, +1 seam line (src {name})")

print("\n".join(out))
print("COPIES:", len(out))
