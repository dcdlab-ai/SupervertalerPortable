# BATCH Q-C / Q.7r STEP 0b — does the WYSIWYG branch lose NBSP?
# Calls the REAL SupervertalerQt._wysiwyg_document_to_tagged_text (bound to a
# stub self; it only needs self._wysiwyg_runs_to_tagged_text, a @staticmethod)
# on a QTextEdit populated exactly like a WYSIWYG grid cell:
#   has_formatting_tags(text) -> setHtml(get_formatted_html_display(text))
#   else                       -> setPlainText(text)
import os, sys, json
from types import SimpleNamespace

TREE = r"E:\Dev\SupervertalerPortable"
OUT = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-qc\q7r\step0_wysiwyg_nbsp.json"
os.chdir(TREE)
sys.path.insert(0, TREE)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['TEMP'] = os.path.dirname(OUT)
os.environ['TMP'] = os.path.dirname(OUT)

RESULTS = {}


def check(name, cond, detail=""):
    RESULTS[name] = {"status": "PASS" if cond else "FAIL", "detail": str(detail)[:400]}
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")


from PyQt6.QtWidgets import QApplication, QTextEdit
app = QApplication.instance() or QApplication([])

import Supervertaler as SV
from modules.tag_manager import get_formatted_html_display, has_formatting_tags

SQ = SV.SupervertalerQt
stub = SimpleNamespace(_wysiwyg_runs_to_tagged_text=SQ._wysiwyg_runs_to_tagged_text)
rebuild = SQ._wysiwyg_document_to_tagged_text.__get__(stub)

NB = '\xa0'

# Case 1: WYSIWYG cell WITH formatting tags (setHtml path)
text_tagged = f"<b>bold{NB}word</b> plain{NB}tail"
ed = QTextEdit()
assert has_formatting_tags(text_tagged)
ed.setHtml(get_formatted_html_display(text_tagged))
rebuilt = rebuild(ed)
check("wysiwyg_sethtml_raw_keeps_nbsp", NB in ed.document().toRawText(),
      repr(ed.document().toRawText()))
check("wysiwyg_sethtml_rebuild_keeps_nbsp", rebuilt.count(NB) == 2, repr(rebuilt))
check("wysiwyg_sethtml_rebuild_tags", "<b>" in rebuilt and "</b>" in rebuilt, repr(rebuilt))

# Case 2: WYSIWYG cell WITHOUT tags (setPlainText path, show_tags=False)
text_plain = f"plain{NB}cell"
ed2 = QTextEdit()
assert not has_formatting_tags(text_plain)
ed2.setPlainText(text_plain)
rebuilt2 = rebuild(ed2)
check("wysiwyg_setplain_rebuild_keeps_nbsp", rebuilt2 == f"plain{NB}cell", repr(rebuilt2))

# Case 3: fragment text itself keeps NBSP after a keystroke next to it
from PyQt6.QtTest import QTest
cur = ed2.textCursor(); cur.setPosition(5); ed2.setTextCursor(cur)
QTest.keyClicks(ed2, "X")
rebuilt3 = rebuild(ed2)
check("wysiwyg_keystroke_rebuild_keeps_nbsp", rebuilt3 == f"plainX{NB}cell", repr(rebuilt3))

ok = all(v["status"] == "PASS" for v in RESULTS.values())
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({"ok": ok, "results": RESULTS}, f, ensure_ascii=False, indent=1)
print("WYSIWYG-NBSP", "KEEPS (no fix needed)" if ok else "LOSES (fix required)")
sys.exit(0 if ok else 1)
