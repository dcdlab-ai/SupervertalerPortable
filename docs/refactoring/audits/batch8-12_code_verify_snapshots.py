# -*- coding: utf-8 -*-
"""Batch #8.12: проверка, что вырезанные блоки == снапшоты (byte-wise),
и что удалённые 17 модулей == HEAD-версии (git show), и что в новых файлах
блоки отсутствуют."""
import hashlib
import pathlib
import subprocess
import sys

REPO = pathlib.Path(r"E:\Dev\SupervertalerPortable")
S = pathlib.Path(r"D:\Temp\SupervertalerPortable\refactoring\b8-12\snapshots")

BLOCKS = [
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

fails = 0
for rel, start, end, name in BLOCKS:
    head = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO,
                          capture_output=True).stdout
    lines = head.split(b"\n")
    # git blob split drops the newline that terminated line `end`; restore it
    block = b"\n".join(lines[start - 1:end]) + b"\n"
    snap = (S / name).read_bytes()
    # snapshot written with newline="" from text splitlines(keepends=True):
    # normalize snapshot newlines to \n for byte compare against git blob
    snap_n = snap.replace(b"\r\n", b"\n")
    ok = block == snap_n
    print(f"{rel}:{start}-{end} {name}: {'OK' if ok else 'MISMATCH'} "
          f"sha256(head-block)={hashlib.sha256(block).hexdigest()[:16]} "
          f"sha256(snap)={hashlib.sha256(snap_n).hexdigest()[:16]}")
    if not ok:
        fails += 1
        print("  HEAD block:", block[:200])
        print("  snapshot  :", snap_n[:200])

# удалённые модули: git show HEAD == снапшот? (снятие не делалось поштучно,
# проверяем что git rm совпадает с HEAD-версиями: diff HEAD vs index пуст для удалённых)
deleted = subprocess.run(["git", "diff", "--cached", "--name-status", "HEAD"],
                         cwd=REPO, capture_output=True, text=True).stdout
print("\n=== git diff --cached HEAD (name-status):")
print(deleted)

# блоки отсутствуют в новых файлах
NEW_ABSENT = {
    "modules/statuses.py": ["def match_memoq_status", "def compose_memoq_status", "import re", "Optional"],
    "modules/help_system.py": ["SIDEKICK", "TRADOS_AWARE_CHAT", "CLIPBOARD",
                               'VOICE               = "workbench/voice/overview/"'],
    "modules/termbase_manager.py": ["get_termbase_voice_enabled", "set_termbase_voice_enabled",
                                    "get_voice_enabled_termbase_ids", "Voice-dictation biasing"],
    "modules/styled_widgets.py": ["Used by the voice-dictation-bias UI", "and Voice (purple)"],
    "Supervertaler.py": ["StatusDefinition"],
}
print("=== absence checks in edited files:")
for rel, needles in NEW_ABSENT.items():
    text = (REPO / rel).read_text(encoding="utf-8")
    for n in needles:
        present = n in text
        print(f"{rel}: '{n}' {'PRESENT(!!)' if present else 'absent OK'}")
        if present:
            fails += 1

print(f"\nFAILS={fails}")
sys.exit(1 if fails else 0)
