import os, email
A = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p21\unpacked\python-embed\Lib\site-packages"
B = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p23\lockinstall2"
def inventory(root):
    inv = {}
    for name in os.listdir(root):
        if name.endswith(".dist-info"):
            with open(os.path.join(root, name, "METADATA"), encoding="utf-8", errors="replace") as f:
                msg = email.message_from_file(f)
            inv[msg.get("Name", name)] = msg.get("Version")
    return inv
d, l = inventory(A), inventory(B)
d.pop("pip", None)
print(f"distributive (no pip): {len(d)}   lock2-install: {len(l)}")
norm = lambda s: s.lower().replace("_", "-").replace(".", "-")
dn = {norm(k): (k, v) for k, v in d.items()}
ln = {norm(k): (k, v) for k, v in l.items()}
only_d = sorted(dn[k] for k in set(dn) - set(ln))
only_l = sorted(ln[k] for k in set(ln) - set(dn))
diff_v = sorted((dn[k], ln[k][1]) for k in set(dn) & set(ln) if dn[k][1] != ln[k][1])
print("only in distributive:", only_d)
print("only in lock2-install:", only_l or "NONE")
print("version mismatches :", diff_v or "NONE")
expected = [("Markdown", "3.10.3"), ("PyYAML", "6.0.3"), ("packaging", "26.3")]
print("VERDICT:", "AS-EXPECTED (3 explained removals, rest ZERO-DIFF)"
      if sorted(only_d) == expected and not only_l and not diff_v else "UNEXPECTED DIFFS")
