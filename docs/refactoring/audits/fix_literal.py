# -*- coding: utf-8 -*-
"""Чинит литерал в _do_extract_terms: AI Settings.<LF><LF>"<CRLF> -> AI Settings.\\n\\n"<CRLF>."""
import hashlib, pathlib

p = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py")
d = p.read_bytes()

BS_N = b"\x5c\x6e"  # literal backslash + n

old = b"AI Settings.\n\n\"\r\n"
new = b"AI Settings." + BS_N + BS_N + b"\"\r\n"
assert d.count(old) == 1, d.count(old)
d = d.replace(old, new, 1)
assert d.count(b"\r\r\n") == 0
assert d.count(b"\r\n") == d.count(b"\n"), (d.count(b"\r\n"), d.count(b"\n"))
p.write_bytes(d)
print("repaired, sha", hashlib.sha256(d).hexdigest()[:16])
