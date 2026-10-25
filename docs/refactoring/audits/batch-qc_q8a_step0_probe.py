# -*- coding: utf-8 -*-
"""BATCH Q-C / Q.8a STEP 0 — reproduce the "[[Error: Connection error.]]"
double-bracket row in the QuickTrans panel LLM row (dead endpoint), and the
MT row for contrast. Uses the real QuickTransProviderMixin._call_llm_translation
and the real panel Fetch path with a stub parent_app (Q-B probe pattern)."""
import json, os, sys, time

TREE = r"E:\Dev\SupervertalerPortable"
OUT = r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-qc\q8\step0_q8a.json"
os.chdir(TREE)
sys.path.insert(0, TREE)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['TEMP'] = os.path.dirname(OUT)
os.environ['TMP'] = os.path.dirname(OUT)

from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

import Supervertaler as SV
SQ = SV.SupervertalerQt

DEAD = "http://127.0.0.1:1/v1"          # closed port on localhost, instant refusal


class ParentStub:
    def __init__(self):
        self._mtql = {'mtql_custom_mt': True, 'mtql_llm_profiles': None}

    load_api_keys = lambda self: {}
    load_provider_enabled_states = lambda self: {}
    call_custom_mt = SQ.call_custom_mt
    create_llm_client = SQ.create_llm_client
    _custom_llm_ready = SQ._custom_llm_ready
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
            'custom_mt_profiles': [
                {'name': 'MT dead', 'endpoint': DEAD, 'model': 'm',
                 'api_key': '', 'raw_mode': True, 'enabled': True}],
            'custom_openai_profiles': [
                {'name': 'LLM dead', 'endpoint': DEAD, 'model': 'm',
                 'api_key': '', 'supports_vision': False}],
            'custom_openai_active_profile': 'LLM dead',
        }


stub = ParentStub()

from modules.quicktrans import QuickTransPanel

panel = QuickTransPanel(stub)
panel.show()

result = {}


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


# Direct call path (what the panel's LLM Fetch row executes)
t0 = time.time()
direct = panel._call_llm_translation('custom_openai', 'hello', 'English', 'Dutch')
result['direct_llm_call'] = {"text": direct, "seconds": round(time.time() - t0, 1)}
print("DIRECT LLM:", repr(direct))

# Real panel fetch path: build rows for a segment, click the AI Fetch button
panel.request_update('hello world', 'English', 'Dutch')
pump(0.5)
panel._force_refresh()
pump(0.5)
result['ai_rows'] = len(panel._ai_fetch_rows)
if panel._ai_fetch_rows:
    panel._ai_fetch_rows[0][1].click()
    pump(12.0)
    texts = [r.current_text() for r in panel._rows]
    result['panel_llm_row'] = texts
    print("PANEL LLM ROW:", repr(texts))

# MT row via the panel (dead localhost endpoint -> '[MT proxy not running. ...]')
mt_rows = list(panel._mt_fetch_rows)
result['mt_rows'] = len(mt_rows)
if mt_rows:
    mt_rows[0][1].click()
    pump(12.0)
    texts = [r.current_text() for r in panel._rows]
    result['panel_all_rows_after_mt'] = texts
    print("PANEL ROWS (after MT):", repr(texts))

# MT direct call
mt_direct = stub.call_custom_mt('hello', 'English', 'Dutch')
result['direct_mt_call'] = mt_direct
print("DIRECT MT:", repr(mt_direct))

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("STEP0-Q8A DONE")
os._exit(0)
