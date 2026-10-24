# BATCH Q-B / Q.4 probe — panel QuickTrans: editable result field, Paste
# button, click-no-insert, Ctrl+N inserts the edited text, error rows carry
# no Paste, link-only Paste = source verbatim.
# argv[1] = tree root, argv[2] = results JSON.
# Real call chain: QuickTransPanel -> MTFetchWorker -> parent_app stub whose
# call_custom_mt / create_llm_client are the REAL SupervertalerQt methods
# aimed at a fake loopback OpenAI endpoint. Insertion is asserted at the
# panel's translation_selected boundary — the exact signal the host wires to
# _insert_quicktrans_translation (which this batch does not modify).
import os, sys, json, time, threading, traceback

TREE = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
os.chdir(TREE)
sys.path.insert(0, TREE)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
STAGE_TMP = os.path.dirname(OUT)
os.environ['TEMP'] = STAGE_TMP
os.environ['TMP'] = STAGE_TMP

RESULTS = {}


def check(name, cond, detail=""):
    RESULTS[name] = {"status": "PASS" if cond else "FAIL", "detail": str(detail)[:500]}


from http.server import BaseHTTPRequestHandler, HTTPServer

REQUESTS = []


class FakeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n)
        REQUESTS.append({"path": self.path, "body": body.decode('utf-8', 'replace')[:200]})
        resp = {"id": "chatcmpl-1", "object": "chat.completion", "created": 0,
                "model": "m", "choices": [{"index": 0,
                "message": {"role": "assistant",
                            "content": "First line of the translation.\nSecond line continues here."},
                "finish_reason": "stop"}]}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


srv = HTTPServer(('127.0.0.1', 0), FakeHandler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{PORT}/v1"
# a deliberately closed local port -> connection refused -> "[MT proxy …]"
DEAD_BASE = "http://127.0.0.1:1/v1"

import Supervertaler as SV
SQ = SV.SupervertalerQt


class ParentStub:
    def __init__(self, mt_profiles):
        self.source_language = 'English'
        self.target_language = 'Dutch'
        self._mtql = {'mtql_custom_mt': True, 'mtql_popup_ai_autofetch': True,
                      'mtql_llm_profiles': None}
        self._mt_profiles = mt_profiles

    load_api_keys = lambda self: {}
    load_provider_enabled_states = lambda self: {}
    call_custom_mt = SQ.call_custom_mt
    create_llm_client = SQ.create_llm_client
    _get_active_custom_profile = SQ._get_active_custom_profile
    _custom_profile_request_kwargs = SQ._custom_profile_request_kwargs
    _normalize_custom_endpoint = staticmethod(SQ._normalize_custom_endpoint)
    _get_proxy_url = lambda self: None

    def log(self, msg):
        pass

    def load_general_settings(self):
        return {'mt_quick_lookup': dict(self._mtql)}

    def load_llm_settings(self):
        return {
            'custom_mt_profiles': self._mt_profiles,
            'custom_openai_profiles': [
                {'name': 'LLM prof', 'endpoint': BASE, 'model': 'm',
                 'api_key': '', 'supports_vision': False}],
        }


from PyQt6.QtWidgets import (QApplication, QPushButton, QLabel, QTextEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut, QTextCursor
from PyQt6.QtTest import QTest

app = QApplication.instance() or QApplication([])

import modules.quicktrans as QT


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def wait_until(pred, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)
        if pred():
            pump(0.2)
            return True
    return False


def fetch_buttons(panel):
    out = []
    for i in range(panel.results_layout.count()):
        w = panel.results_layout.itemAt(i).widget()
        if w is None:
            continue
        for b in w.findChildren(QPushButton):
            if b.text() in ('Fetch', '…'):
                out.append(b)
    return out


def paste_button(row):
    for b in row.findChildren(QPushButton):
        if b.text() == 'Paste':
            return b
    return None


emitted = []          # everything the panel asked to insert
LINK = "![Image](y.png)"

try:
    stub = ParentStub([
        {'name': 'MT good', 'endpoint': BASE, 'model': 'm',
         'api_key': '', 'raw_mode': True, 'enabled': True},
    ])
    panel = QT.QuickTransPanel(stub)
    panel.show()
    panel.translation_selected.connect(emitted.append)

    # ── fetch the one MT row -> editable result row ────────────────────
    panel.request_update("Hello panel", 'English', 'Dutch')
    pump(0.6)
    fetch_buttons(panel)[0].click()
    ok = wait_until(lambda: len(panel._rows) == 1 and not panel._workers)
    check("q4_row_created", ok and len(panel.suggestions) == 1,
          [(s.provider_name, s.translation) for s in panel.suggestions])
    row = panel._rows[0]
    field = row.field
    check("q4_field_is_editable_widget",
          isinstance(field, QTextEdit) and not field.isReadOnly(), type(field).__name__)
    check("q4_field_content", field.toPlainText() ==
          "First line of the translation.\nSecond line continues here.",
          field.toPlainText())

    # ── the field grows with the text and shrinks back ─────────────────
    field.setPlainText("One single line")
    pump(0.2)
    h_one_line = field.height()
    field.setPlainText("L1\nL2")
    pump(0.2)
    h_two_lines = field.height()
    field.setPlainText("L1\nL2\nL3\nL4")
    pump(0.2)
    h_four_lines = field.height()
    check("q4_field_auto_height",
          h_one_line < h_two_lines < h_four_lines,
          {"one": h_one_line, "two": h_two_lines, "four": h_four_lines})

    # ── editing the field is visible in current_text ───────────────────
    field.setPlainText("Edited by hand: first\nEdited by hand: second")
    cursor = field.textCursor()
    cursor.clearSelection()
    field.setTextCursor(cursor)
    pump(0.1)
    check("q4_field_editable", row.current_text() ==
          "Edited by hand: first\nEdited by hand: second", row.current_text())

    # ── selection is copyable ───────────────────────────────────────────
    cursor = field.textCursor()
    cursor.setPosition(0, QTextCursor.MoveMode.MoveAnchor)
    cursor.setPosition(5, QTextCursor.MoveMode.KeepAnchor)   # "Edit"
    field.setTextCursor(cursor)
    field.copy()
    clip = QApplication.clipboard().text()
    check("q4_selection_copyable", clip == "Edite", repr(clip))  # "Edited"[0:5]

    # ── Paste with a selection inserts the SELECTED fragment ───────────
    emitted.clear()
    paste_button(row).click()
    check("q4_paste_selection", emitted == ["Edite"], emitted)

    # ── Paste with no selection inserts the WHOLE (edited) text ────────
    cursor.clearSelection()
    field.setTextCursor(cursor)
    emitted.clear()
    paste_button(row).click()
    check("q4_paste_whole_edited", emitted ==
          ["Edited by hand: first\nEdited by hand: second"], emitted)

    # ── Ctrl+N (panel) inserts the CURRENT field text ──────────────────
    emitted.clear()
    inserted = panel.insert_match_by_number(1)
    check("q4_ctrl_n_edited_text",
          inserted and emitted == ["Edited by hand: first\nEdited by hand: second"],
          {"inserted": inserted, "emitted": emitted})

    # ── the field's focus does not swallow Ctrl+1 ──────────────────────
    # Real shortcut wiring: the host window owns Ctrl+1..9 and dispatches to
    # the visible panel (Supervertaler.py insert_match_by_number). Mirror it
    # here and send a genuine Ctrl+1 key event to the focused field.
    sc = QShortcut(QKeySequence("Ctrl+1"), panel)
    sc.activated.connect(lambda: panel.insert_match_by_number(1))
    field.setFocus()
    pump(0.1)
    check("q4_field_focused", field.hasFocus(), field.hasFocus())
    emitted.clear()
    QTest.keyClick(field, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    pump(0.1)
    check("q4_ctrl_shortcut_through_focus",
          emitted == ["Edited by hand: first\nEdited by hand: second"]
          and field.toPlainText() == "Edited by hand: first\nEdited by hand: second",
          {"emitted": emitted, "field": field.toPlainText()})

    # ── clicking the row (any part) inserts NOTHING ────────────────────
    emitted.clear()
    QTest.mouseClick(row.num_label, Qt.MouseButton.LeftButton)
    QTest.mouseClick(field, Qt.MouseButton.LeftButton)
    pump(0.1)
    check("q4_click_no_insert", emitted == [], emitted)
    check("q4_click_focuses_field", field.hasFocus(), field.hasFocus())

    # ── number badges follow the visual row order ──────────────────────
    check("q4_number_badges", [r.num_label.text() for r in panel._rows] == ["1"],
          [r.num_label.text() for r in panel._rows])

    panel.close()
    panel.deleteLater()
    pump(0.2)
except Exception:
    check("q4_main_crashed", False, traceback.format_exc())

# ── error row: no Paste button, Ctrl+N refuses ──────────────────────────
try:
    stub2 = ParentStub([
        {'name': 'MT dead', 'endpoint': DEAD_BASE, 'model': 'm',
         'api_key': '', 'raw_mode': True, 'enabled': True},
        {'name': 'MT good', 'endpoint': BASE, 'model': 'm',
         'api_key': '', 'raw_mode': True, 'enabled': True},
    ])
    panel2 = QT.QuickTransPanel(stub2)
    panel2.show()
    emitted2 = []
    panel2.translation_selected.connect(emitted2.append)

    panel2.request_update("Error case segment", 'English', 'Dutch')
    pump(0.6)
    for b in fetch_buttons(panel2):
        b.click()
    ok = wait_until(lambda: len(panel2._rows) == 3 and not panel2._workers)  # 2 MT + 1 LLM
    rows2 = [(r.suggestion.provider_name, r.suggestion.translation, r.suggestion.is_error)
             for r in panel2._rows]
    dead = next((r for r in panel2._rows if r.suggestion.provider_name == 'MT dead'), None)
    good = next((r for r in panel2._rows if r.suggestion.provider_name == 'MT good'), None)
    check("q4_error_row_flagged",
          ok and dead is not None and dead.suggestion.is_error
          and dead.suggestion.translation.startswith('['), rows2)
    check("q4_error_text_style_red", dead is not None and
          'ff6b6b' in dead.field.styleSheet(), dead.field.styleSheet()[:120])
    check("q4_error_row_no_paste", dead is not None and paste_button(dead) is None,
          paste_button(dead) is not None and paste_button(dead).text())
    emitted2.clear()
    res2 = panel2.insert_match_by_number(panel2._rows.index(dead) + 1)
    check("q4_error_ctrl_n_refused", not res2 and emitted2 == [],
          {"res": res2, "emitted": emitted2})
    # the healthy row still inserts
    emitted2.clear()
    res1 = panel2.insert_match_by_number(panel2._rows.index(good) + 1)
    check("q4_healthy_row_still_inserts",
          res1 and emitted2 == ["First line of the translation.\nSecond line continues here."],
          {"res": res1, "emitted": emitted2})
    panel2.close()
    panel2.deleteLater()
    pump(0.2)
except Exception:
    check("q4_error_case_crashed", False, traceback.format_exc())

# ── link-only row: Paste inserts the source verbatim ────────────────────
try:
    stub3 = ParentStub([
        {'name': 'MT good', 'endpoint': BASE, 'model': 'm',
         'api_key': '', 'raw_mode': True, 'enabled': True},
    ])
    panel3 = QT.QuickTransPanel(stub3)
    panel3.show()
    emitted3 = []
    panel3.translation_selected.connect(emitted3.append)

    panel3.request_update(LINK, 'English', 'Dutch')
    pump(0.6)
    REQUESTS.clear()
    rows3 = [(r.suggestion.translation, r.suggestion.is_error, r.suggestion.link_only)
             for r in panel3._rows]
    check("q4_linkonly_row", len(rows3) == 2 and all(
        t == LINK and not e and lo for (t, e, lo) in rows3), rows3)
    check("q4_linkonly_no_requests", len(REQUESTS) == 0, len(REQUESTS))
    row3 = panel3._rows[0]
    pb = paste_button(row3)
    check("q4_linkonly_paste_button", pb is not None, pb is not None)
    if pb is not None:
        emitted3.clear()
        pb.click()
        check("q4_linkonly_paste_source", emitted3 == [LINK], emitted3)
    emitted3.clear()
    res3 = panel3.insert_match_by_number(1)
    check("q4_linkonly_ctrl_n_source", res3 and emitted3 == [LINK],
          {"res": res3, "emitted": emitted3})
    panel3.close()
    panel3.deleteLater()
    pump(0.2)
except Exception:
    check("q4_linkonly_crashed", False, traceback.format_exc())

RESULTS["_meta"] = {"tree": TREE, "port": PORT, "total_requests": len(REQUESTS)}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, ensure_ascii=False, indent=1)
print("WROTE", OUT)
srv.shutdown()
os._exit(0)
