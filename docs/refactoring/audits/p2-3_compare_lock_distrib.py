import os, email
A = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p21\unpacked\python-embed\Lib\site-packages"  # distributive
B = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p23\lockinstall"                              # lock install

def inventory(root):
    inv = {}
    for name in os.listdir(root):
        if name.endswith(".dist-info"):
            with open(os.path.join(root, name, "METADATA"), encoding="utf-8", errors="replace") as f:
                msg = email.message_from_file(f)
            inv[msg.get("Name", name)] = msg.get("Version")
    return inv

d, l = inventory(A), inventory(B)
d.pop("pip", None)  # pip excluded from lock by design
print(f"distributive (no pip): {len(d)}   lock-install: {len(l)}")
norm = lambda s: s.lower().replace("_", "-").replace(".", "-")
dn = {norm(k): (k, v) for k, v in d.items()}
ln = {norm(k): (k, v) for k, v in l.items()}
only_d = sorted(set(dn) - set(ln))
only_l = sorted(set(ln) - set(dn))
diff_v = sorted(k for k in set(dn) & set(ln) if dn[k][1] != ln[k][1])
print("only in distributive:", [dn[k] for k in only_d] or "NONE")
print("only in lock-install:", [ln[k] for k in only_l] or "NONE")
print("version mismatches :", [(dn[k], ln[k][1]) for k in diff_v] or "NONE")
print("VERDICT:", "ZERO-DIFF" if not (only_d or only_l or diff_v) else "DIFFS FOUND")
