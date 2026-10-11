# -*- coding: utf-8 -*-
"""Спец-проба W: массовый Write в TM-вкладке.

3 TM в изолированной БД; «Select All Write» (заголовочный чекбокс) -> все 3
read_only=False; снятие галочки -> все True; «Clear All Write» -> все True;
построчный чекбокс продолжает работать; кэш инвалидируется
(invalidate_translation_cache(smart_invalidation=False)).

Запуск: python batch8-15_probe_w.py <tree-root> <iso-dir> <tag>
"""
import faulthandler, json, os, pathlib, sys

tree = pathlib.Path(sys.argv[1]).resolve()
iso = pathlib.Path(sys.argv[2]).resolve()
tag = sys.argv[3]

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USERPROFILE"] = str(iso)
os.environ["APPDATA"] = str(iso / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(iso / "AppData" / "Local")
os.environ["HOME"] = str(iso)
os.environ["TEMP"] = str(iso / "tmp")
os.environ["TMP"] = str(iso / "tmp")
for d in ("Desktop", "Documents", "Downloads", "tmp"):
    (iso / d).mkdir(parents=True, exist_ok=True)
cfg_dir = iso / "AppData" / "Roaming" / "Supervertaler"
cfg_dir.mkdir(parents=True, exist_ok=True)
data_dir = iso / "Supervertaler"
(cfg_dir / "config.json").write_text(
    '{"user_data_path": "' + str(data_dir).replace("\\", "\\\\") + '"}', encoding="utf-8"
)

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)
sys.path.insert(0, str(tree))

import Supervertaler  # noqa: E402
import modules.usage_statistics as _us  # noqa: E402
_us.show_opt_in_dialog = lambda parent=None: False

from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

app = QApplication(sys.argv)
QDialog.exec = lambda self, *a, **k: QDialog.DialogCode.Rejected

win = Supervertaler.SupervertalerQt()
print(f"[{tag}] window built", flush=True)

mgr = win.tm_metadata_mgr
ids = []
for i in (1, 2, 3):
    db_id = mgr.create_tm(f"probeW_{i}", f"probeW_{i}", "en", "nl")
    assert db_id, f"create_tm {i} failed"
    ids.append(db_id)
print(f"[{tag}] created TMs: {ids}", flush=True)

# найти заголовочный чекбокс Select All Write и кнопку Clear All Write
# ВАЖНО: искать в контейнере TM-таблицы — у вкладки Termbases свои одноимённые
# «Select All Write» / «Clear All Write» (win.findChildren хватает первые попавшиеся)
from PyQt6.QtWidgets import QCheckBox, QPushButton, QTableWidget, QWidget  # noqa: E402

tm_table = next(t for t in win.findChildren(QTableWidget)
                if t.columnCount() == 8 and t.horizontalHeaderItem(0).text() == "TM Name")

def _in_tm_container(widget_type, text):
    anc = tm_table.parentWidget()
    while anc is not None and anc is not win:
        hits = [w for w in anc.findChildren(widget_type) if w.text() == text]
        if hits:
            return hits[0]
        anc = anc.parentWidget()
    return None

write_cb = _in_tm_container(QCheckBox, "Select All Write")
clear_btn = _in_tm_container(QPushButton, "Clear All Write")
assert write_cb and clear_btn, "bulk controls not found"

# счётчик инвалидаций
inv_calls = []
_orig_inv = win.invalidate_translation_cache
win.invalidate_translation_cache = lambda **kw: (inv_calls.append(kw), _orig_inv(**kw))[1]


def ro_states():
    return {t["id"]: bool(t.get("read_only")) for t in mgr.get_all_tms()}


report = {}

# 1. Select All Write -> все writable (read_only=False)
write_cb.setChecked(True)
report["select_all_write"] = ro_states()
# 2. снятие -> все read_only=True
write_cb.setChecked(False)
report["unselect_all_write"] = ro_states()
# 3. Select All -> Clear All Write кнопка -> все True
write_cb.setChecked(True)
clear_btn.click()
report["clear_all_write_btn"] = ro_states()
# 4. построчный: включить Write только у первой строки
row0_cb = tm_table.cellWidget(0, 4)  # сам BlueCheckmarkCheckBox (subclass QCheckBox)
assert isinstance(row0_cb, QCheckBox), f"cell(0,4) is {type(row0_cb)}"
before = ro_states()
row0_cb.setChecked(True)
after_row = ro_states()
report["per_row_toggle_before"] = before
report["per_row_toggle_after"] = after_row

report["invalidate_calls"] = inv_calls
print(f"[{tag}] REPORT {json.dumps(report)}", flush=True)

states = report
ok = (
    all(v is False for v in states["select_all_write"].values())
    and all(v is True for v in states["unselect_all_write"].values())
    and all(v is True for v in states["clear_all_write_btn"].values())
    and sum(1 for v in states["per_row_toggle_after"].values() if v is False) == 1
    and len(inv_calls) >= 3
    and all(c.get("smart_invalidation") is False for c in inv_calls)
)
print(f"[{tag}] RESULT {'OK' if ok else 'FAIL'}", flush=True)
os._exit(0 if ok else 1)
