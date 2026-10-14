# -*- coding: utf-8 -*-
"""Batch 9.4i-2 edit: modules/quicktrans.py — remove the master gate
mtql_custom_openai in _add_llm_providers and the legacy single-field chip.

Dmitry's decision 2026-10-14: LLM chips in the popup are always present.
Order: profiles by mtql_llm_profiles (absent = all with endpoint; subset =
selected with endpoint) -> no chips -> global active profile from AI Settings
as the only remaining chip (9.4h, extended: also covers the no-profiles case
via _get_active_custom_profile's legacy flat-endpoint resolution) -> nothing
configured -> no chips, no errors.

File is LF — all inserted lines end with \n.
"""
import pathlib

F = pathlib.Path(r"E:\Dev\SupervertalerPortable\modules\quicktrans.py")
text = F.read_bytes().decode("utf-8")
assert "\r\n" not in text
lines = text.splitlines(keepends=True)

def find(sub, start=0, end=None):
    end = len(lines) if end is None else end
    hits = [i for i in range(start, end) if sub in lines[i]]
    assert len(hits) == 1, (sub, hits)
    return hits[0]

# --- 1: remove master gate (comment 353-356 + if 357-358) ---
a = find("# Batch #9.4f: master checkbox mtql_custom_openai gates the group;")
b = find("            return", a, a + 8)
assert lines[b - 1].strip() == "if not mt_quick_settings.get('mtql_custom_openai', False):", lines[b - 1]
assert lines[a - 1].strip().endswith('"""'), lines[a - 1]  # right after docstring
del lines[a:b + 1]

# --- 2: replace 9.4h fallback + legacy chip with unified fallback ---
c = find("        if _added == 0 and profiles:")
d = find('providers.append(("Custom", "CUS", make_llm_caller(model, None)))')
NEW = [
    "        if _added == 0:\n",
    "            # Batch #9.4h/#9.4i (решение Дмитрия 2026-10-13/14): когда в QuickTrans\n",
    "            # сняты/удалены ВСЕ профили (или список устарел, или профилей нет вовсе),\n",
    "            # попап работает с глобальным активным профилем из AI Settings как с\n",
    "            # единственно оставшимся чипом. _get_active_custom_profile разрешает\n",
    "            # активный по имени -> первый профиль -> легаси-плоский endpoint.\n",
    "            active = None\n",
    "            if hasattr(self, 'parent_app') and self.parent_app and hasattr(self.parent_app, '_get_active_custom_profile'):\n",
    "                try:\n",
    "                    active = self.parent_app._get_active_custom_profile(llm_settings)\n",
    "                except Exception:\n",
    "                    active = None\n",
    "            if active and (active.get('endpoint') or '').strip():\n",
    "                label = (active.get('name') if active.get('name') else 'Custom')\n",
    "                providers.append((label, \"CUS\", make_llm_caller(None, None)))\n",
    "            # Batch #9.4i: профиль не настроен вовсе — чипов нет, ошибок нет.\n",
]
lines[c:d + 1] = NEW

# --- 3: docstring note (inserted before the closing line, inside the docstring) ---
e = find('только Custom (активный профиль custom_openai, чип CUS)."""')
lines[e:e] = [
    "\n",
    "        Batch #9.4i (решение Дмитрия 2026-10-14): мастер-чекбокс\n",
    "        mtql_custom_openai убран — чипы есть всегда; mtql_llm_profiles выбирает\n",
    "        профили; при пустом списке работает глобальный активный профиль.\n",
]

out = "".join(lines).encode("utf-8")
F.write_bytes(out)
print("94i-2 applied: gate", a + 1, "..", b + 1, "fallback", c + 1, "..", d + 1)
print("lines:", len(out.splitlines()))
