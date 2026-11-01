import os, sys, json, email
ROOT = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p21\unpacked\python-embed\Lib\site-packages"
out = []
for name in sorted(os.listdir(ROOT)):
    if not name.endswith(".dist-info"):
        continue
    di = os.path.join(ROOT, name)
    meta = os.path.join(di, "METADATA")
    rec = {"dist_info": name}
    if os.path.exists(meta):
        with open(meta, encoding="utf-8", errors="replace") as f:
            msg = email.message_from_file(f)
        rec["Name"] = msg.get("Name")
        rec["Version"] = msg.get("Version")
        rec["Requires-Dist"] = [v for k, v in msg.items() if k.lower() == "requires-dist"]
        rec["Requires-Python"] = msg.get("Requires-Python")
    out.append(rec)
json.dump(out, open(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p23\distinfo.json", "w"), indent=1, ensure_ascii=False)
for r in out:
    print(f"{r.get('Name','?')}=={r.get('Version','?')}  [{r['dist_info']}]")
    for rd in r.get("Requires-Dist", []):
        print(f"    -> {rd}")
