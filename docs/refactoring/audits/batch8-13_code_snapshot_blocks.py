# -*- coding: utf-8 -*-
"""Снапшоты вырезаемых блоков Batch #8.13 (sha256) из рабочей копии."""
import hashlib, pathlib, sys

src = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py").read_bytes()
lines = src.split(b"\n")
out = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-13\snapshots")
out.mkdir(exist_ok=True)

BLOCKS = {
    # part A
    "A_D01_help_bridge_line": (11244, 11244),
    "A_D02_D03_D04_bridge_bulk": (11276, 11287),
    "A_D11_comment_bridge": (11289, 11292),
    "A_D05_D06_columns": (11306, 11319),
    "A_comment_superlookup_bridge": (11383, 11385),
    "A_D07_toggle_all_bridge": (11370, 11381),
    "A_D08_connect": (11400, 11400),
    "A_D09_row_bridge": (11513, 11544),
    "A_renum_superlookup_revert": (11566, 11566),
    "A_renum_superlookup_set": (11573, 11573),
    "A_renum_lastmod": (11585, 11585),
    "A_renum_desc": (11589, 11589),
    "A_D10_headersync": (11591, 11607),
    # part B
    "B_import_menu": (7958, 7967),
    "B_export_menu": (8019, 8029),
    "B_okapi_exts": (9453, 9455),
    "B_quickcount_formats": (9473, 9481),
    "B_okapi_other_formats": (29744, 29754),
    "B_po_methods": (32713, 32940),
}

for name, (a, b) in BLOCKS.items():
    block = b"\n".join(lines[a - 1:b])
    h = hashlib.sha256(block).hexdigest()
    (out / f"{name}.txt").write_bytes(block)
    print(f"{name}: {a}-{b} ({b-a+1} lines) sha256={h}")
