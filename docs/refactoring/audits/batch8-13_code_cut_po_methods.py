# -*- coding: utf-8 -*-
"""Вырезание блока import_po_file/export_po_file (32643-32870, 1-based)
со снапшот-проверкой sha256 и assert count==1."""
import hashlib, pathlib

p = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py")
data = p.read_bytes()
lines = data.split(b"\n")

# boundaries (1-based): 32643 = '    @staticmethod', 32870 = last line of export_po_file
a, b = 32643, 32870
block = b"\n".join(lines[a - 1:b])
h = hashlib.sha256(block).hexdigest()
assert h == "bf99a6c7fe92499ff6e271e9d64484b9fa60da8af0fc30d147afb11983f8ef39", f"sha mismatch {h}"
assert lines[a - 1] == b"    @staticmethod\r", lines[a - 1][:40]
assert lines[a - 2] == b"\r", "blank line before @staticmethod expected"
assert lines[b - 1] == b"            )\r", lines[b - 1][:60]
assert lines[b] == b"\r", "blank line after block expected"
assert lines[b + 1].startswith(b"    def get_translator_name"), lines[b + 1][:60]

new = b"\n".join(lines[:a - 1] + lines[b + 1:])
before = data.count(b"import_po_file"), data.count(b"export_po_file")
after = new.count(b"import_po_file"), new.count(b"export_po_file")
assert before == (2, 2) and after == (1, 1), (before, after)  # menu connect lines remain
p.write_bytes(new)
print(f"cut OK: removed {b+1-a+1} lines (incl. trailing blank); new line count {len(new.split(b'\\n'))}")
