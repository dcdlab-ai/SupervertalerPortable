# -*- coding: utf-8 -*-
"""Batch #8.12: снапшоты вырезаемых блоков (до правок) с sha256.

Формат: файл-снапшот = ровно строки [start..end] исходного файла (1-based,
включительно), как в файле (raw bytes). Проверка после правок: удалённый блок
== снапшот (byte-wise).
"""
import hashlib
import pathlib

REPO = pathlib.Path(r"E:\Dev\SupervertalerPortable")
S = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-12\snapshots")
S.mkdir(parents=True, exist_ok=True)

BLOCKS = [
    # (file, start, end, snapshot-name)
    ("modules/statuses.py", 4, 4, "statuses_import_typing.txt"),
    ("modules/statuses.py", 5, 5, "statuses_import_re.txt"),
    ("modules/statuses.py", 184, 244, "statuses_memoq_functions.txt"),
    ("modules/help_system.py", 160, 167, "help_system_voice_clipboard_chat.txt"),
    ("modules/termbase_manager.py", 461, 502, "termbase_voice_get_set.txt"),
    ("modules/termbase_manager.py", 530, 552, "termbase_voice_ids.txt"),
    ("modules/styled_widgets.py", 116, 124, "styled_widgets_voice_doc.txt"),
    ("modules/styled_widgets.py", 169, 171, "styled_widgets_teal_voice.txt"),
    ("Supervertaler.py", 320, 326, "monolith_statuses_import.txt"),
]

for rel, start, end, name in BLOCKS:
    lines = REPO.joinpath(rel).read_text(encoding="utf-8").splitlines(keepends=True)
    block = "".join(lines[start - 1:end])
    (S / name).write_text(block, encoding="utf-8", newline="")
    h = hashlib.sha256(block.encode("utf-8")).hexdigest()
    print(f"{rel}:{start}-{end} -> {name} sha256={h} ({end-start+1} lines)")
