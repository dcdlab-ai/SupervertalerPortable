# BATCH Q-C / Q.7r STEP 0 — offscreen Qt probe: QTextDocument toPlainText()
# replaces NBSP (U+00A0) with a plain space; toRawText() must not.
# Checks (a) setPlainText keeps NBSP in the document, (b) toRawText returns it,
# (c) toRawText + Qt's own separator replacements == toPlainText except NBSP,
# (d) NBSP survives a manual edit of a NEIGHBOUR character (QTest.keyClick).
import os, sys, json

OUT = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-qc\q7r\step0_nbsp_qt.json"
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['TEMP'] = os.path.dirname(OUT)
os.environ['TMP'] = os.path.dirname(OUT)

RESULTS = {}


def check(name, cond, detail=""):
    RESULTS[name] = {"status": "PASS" if cond else "FAIL", "detail": str(detail)[:400]}
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")


from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, Qt
from PyQt6.QtWidgets import QApplication, QTextEdit
from PyQt6.QtTest import QTest

app = QApplication.instance() or QApplication([])

check("qt_version", True, f"PyQt {PYQT_VERSION_STR} / Qt {QT_VERSION_STR}")

# The helper under test: toRawText + the SAME separator replacements Qt's
# toPlainText() performs (0xfdd0/0xfdd1 are Qt-internal Line/ParagraphSeparator
# markers, 0x2028/0x2029 the Unicode ones) — everything else verbatim.
def cell_text_keep_nbsp(widget):
    raw = widget.document().toRawText()
    out = []
    for ch in raw:
        o = ord(ch)
        if o in (0x2028, 0x2029, 0xfdd0, 0xfdd1):
            out.append('\n')
        else:
            out.append(ch)
    return ''.join(out)

ed = QTextEdit()

NBSP = '\xa0'
SRC = "a\xa0b c\xa0d"

# --- (a)+(b): setPlainText keeps NBSP; toRawText returns it -----------------
ed.setPlainText(SRC)
raw = ed.document().toRawText()
blk = ed.document().firstBlock().text()          # block-level (layout) text
cur = ed.textCursor(); cur.select(cur.SelectionType.Document)
sel = cur.selectedText()                          # cursor-level text (U+2029 for \n)
check("a_block_text_keeps_nbsp", '\xa0' in blk, repr(blk))
check("a_cursor_text_keeps_nbsp", '\xa0' in sel, repr(sel))
check("b_torawtext_returns_nbsp", raw.count('\xa0') == 2, repr(raw))
check("b_toplaintext_replaces_nbsp", ed.toPlainText() == "a b c d", repr(ed.toPlainText()))

# --- (c): helper == toPlainText except NBSP ----------------------------------
cases = {
    "nbsp_only": "a\xa0b",
    "nbsp_multiblock": "one\xa0two\nthree\xa0four",
    "nbsp_edges": "\xa0lead and trail\xa0",
    "nbsp_runs": "x\xa0\xa0\xa0y",
    "plain_ascii": "no special chars here",
    "tabs": "tab\there",
}
ed2 = QTextEdit()
for name, text in cases.items():
    ed2.setPlainText(text)
    tp = ed2.toPlainText()
    helper = cell_text_keep_nbsp(ed2)
    check(f"c_{name}_helper_equals_tp_modulo_nbsp",
          helper == tp.replace(' ', '\xa0') or tp == helper.replace('\xa0', ' '),
          f"tp={tp!r} helper={helper!r}")
    check(f"c_{name}_raw_separator_is_u2029",
          '\n' not in ed2.document().toRawText() or '\u2029' in ed2.document().toRawText(),
          f"raw={ed2.document().toRawText()!r}")

# U+2028 line separator inserted via cursor (what a soft break can produce)
ed2.setPlainText("start")
cur = ed2.textCursor(); cur.movePosition(cur.MoveOperation.End)
cur.insertText("soft\u2028break")
tp = ed2.toPlainText()
helper = cell_text_keep_nbsp(ed2)
check("c_u2028_helper_newline", '\n' in helper and helper.count('\n') == tp.count('\n'),
      f"tp={tp!r} helper={helper!r}")
check("c_u2028_helper_equals_tp", helper == tp, f"tp={tp!r} helper={helper!r}")

# --- (d): manual edit of a NEIGHBOUR char keeps NBSP --------------------------
ed3 = QTextEdit()
ed3.setPlainText("a\xa0b")
# put the cursor between 'a' and NBSP and type 'x' from the keyboard
cur = ed3.textCursor(); cur.setPosition(1); ed3.setTextCursor(cur)
QTest.keyClicks(ed3, "x")
raw3 = ed3.document().toRawText()
check("d_keystroke_keeps_nbsp", raw3 == "ax\xa0b", repr(raw3))
check("d_keystroke_toplaintext_normalizes", ed3.toPlainText() == "ax b", repr(ed3.toPlainText()))
check("d_helper_keeps_nbsp", cell_text_keep_nbsp(ed3) == "ax\xa0b", repr(cell_text_keep_nbsp(ed3)))

# delete the char right after NBSP ('b') — NBSP must survive backspace too
QTest.keyClick(ed3, Qt.Key.Key_Backspace)  # cursor was after 'x' -> removes 'x'? ensure placement
ed3.setPlainText("a\xa0bcd")
cur = ed3.textCursor(); cur.setPosition(3)  # between 'b' and 'c'? -> 'a NBSP b c d' positions: a=0 NBSP=1 b=2 c=3
cur.setPosition(2); ed3.setTextCursor(cur)
QTest.keyClick(ed3, Qt.Key.Key_Delete)  # delete 'b' (char right after NBSP)
raw4 = ed3.document().toRawText()
check("d_delete_after_nbsp", raw4 == "a\xa0cd", repr(raw4))

# --- misc: PyQt6 binding exposes toRawText ------------------------------------
check("api_torawtext_binding", hasattr(ed.document(), 'toRawText'), "QTextDocument.toRawText present")

ok = all(v["status"] == "PASS" for v in RESULTS.values())
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({"ok": ok, "results": RESULTS}, f, ensure_ascii=False, indent=1)
print("STEP0", "GREEN" if ok else "RED")
sys.exit(0 if ok else 1)
