# -*- coding: utf-8 -*-
"""Batch 9.4i-1 edit: Supervertaler.py — remove QuickTrans master checkbox
'Custom (OpenAI-Compatible)' (mtql_custom_openai) + read-only active-model field.

Dmitry's decision 2026-10-14: master removed; LLM chips always present; profile
checkboxes (mtql_llm_profiles) select chips; Save must NOT write the master key
and must NOT erase it from existing settings.json (inert legacy keys carried).

Edits (content-anchored, CRLF preserved):
  1. Delete master row block (comment, custom_cb, profile_display, custom_model_edit,
     custom_row) — keep `llm_settings = self.load_llm_settings()` (used by 9.4f loop).
  2. Update 9.4f comment (no master gate).
  3. Save: carry inert legacy keys mtql_custom_openai / mtql_custom_openai_model
     from the old section into the rebuilt one.
"""
import pathlib, sys

F = pathlib.Path(r"E:\Dev\SupervertalerPortable\Supervertaler.py")
raw = F.read_bytes()
text = raw.decode("utf-8")
lines = text.splitlines(keepends=True)  # 0-based

def find(sub, start=0, end=None):
    end = len(lines) if end is None else end
    hits = [i for i in range(start, end) if sub in lines[i]]
    assert len(hits) == 1, (sub, hits)
    return hits[0]

# --- 1: master row block 20089..20114 (1-based) -> keep load_llm_settings line ---
a = find('# Custom OpenAI-compatible provider (shows active profile info)')
assert lines[a].startswith('        # Custom OpenAI-compatible provider'), lines[a]
b = find('llm_layout.addLayout(custom_row)')
assert b > a and b - a == 25, (a, b)  # block is 26 lines (20089..20114)
for i in range(a, b + 1):
    assert lines[i].endswith('\r\n'), (i, repr(lines[i][-2:]))
NEW1 = [
    "        # Batch #9.4i (решение Дмитрия 2026-10-14): мастер-чекбокс\r\n",
    "        # «Custom (OpenAI-Compatible)» и read-only поле модели активного\r\n",
    "        # профиля убраны — LLM-чипы в попапе есть всегда, профили выбирают\r\n",
    "        # чекбоксы профилей ниже.\r\n",
    "        llm_settings = self.load_llm_settings()\r\n",
]
lines[a:b + 1] = NEW1

# --- 2: 9.4f comment: master gates the group -> group always on ---
c = find('# Custom MT above). Master checkbox mtql_custom_openai gates the group;')
assert lines[c - 1].lstrip().startswith('# Batch #9.4f:'), lines[c - 1]
assert lines[c + 1].lstrip().startswith('# mtql_llm_profiles stores'), lines[c + 1]
NEW2 = [
    "        # Custom MT above). Batch #9.4i: master checkbox removed — the group\r\n",
    "        # is always on; mtql_llm_profiles stores the enabled profile names.\r\n",
]
lines[c:c + 2] = NEW2

# --- 3: Save — carry inert legacy keys ---
d = find("name for name, cb in self._mtql_llm_profile_cbs.items() if cb.isChecked()]")
assert lines[d + 2].lstrip().startswith("general_settings['mt_quick_lookup'] = mt_quick_settings"), lines[d + 2]
NEW3 = [
    "\r\n",
    "        # Batch #9.4i: мастер-чекбокс убран; mtql_custom_openai и\r\n",
    "        # mtql_custom_openai_model — инертные легаси-ключи: Save переносит их\r\n",
    "        # из старой секции без изменений (в файле остаются, не читаются,\r\n",
    "        # заново не записываются).\r\n",
    "        _old_mtql = general_settings.get('mt_quick_lookup') or {}\r\n",
    "        for _k in ('mtql_custom_openai', 'mtql_custom_openai_model'):\r\n",
    "            if _k in _old_mtql:\r\n",
    "                mt_quick_settings[_k] = _old_mtql[_k]\r\n",
]
lines[d + 1:d + 1] = NEW3

out = "".join(lines).encode("utf-8")
F.write_bytes(out)
print("94i-1 applied: block", a + 1, "..", b + 1, "-> comment", c + 1, "-> save insert", d + 2)
print("lines:", len(out.splitlines()))
