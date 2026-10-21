# G3.2g unit: parse_profile_request_fields — 11 базовых кейсов G3.2b (восстановлены
# по семантике G3.2b: отчёт §3 + матрица 10) + новые кейсы десятичной запятой
# (вердикт 2026-10-21: 0,1 / 1,5 / 1,5,5 / abc / пусто + 1.5,5 из правила).
# Run: E:\Dev\python-embed\python.exe docs\refactoring\audits\batch-g32g_unit_checks.py
import os
import sys

sys.path.insert(0, os.getcwd())

from modules.llm_clients import parse_profile_request_fields  # noqa: E402

fails = []


def check(name, ok):
    print(("UNIT PASS " if ok else "UNIT FAIL ") + name)
    if not ok:
        fails.append(name)


def parse(**prof):
    return parse_profile_request_fields(prof)

# --- 11 базовых кейсов G3.2b -------------------------------------------------
mt, to, eb, errs = parse()
check("1-empty-profile defaults (None,None,None,no-errors)",
      mt is None and to is None and eb is None and errs == [])

mt, to, eb, errs = parse(max_tokens='5000', timeout_min='5',
                         extra_body='{"chat_template_kwargs": {"enable_thinking": false}}')
check("2-valid set mt=5000 to=300.0s eb parsed",
      mt == 5000 and to == 300.0 and eb == {"chat_template_kwargs": {"enable_thinking": False}}
      and errs == [])

mt, to, eb, errs = parse(max_tokens='abc')
check("3-max_tokens 'abc' blocked", mt is None and len(errs) == 1)

mt, to, eb, errs = parse(max_tokens='0')
check("4-max_tokens '0' blocked", mt is None and len(errs) == 1)

mt, to, eb, errs = parse(max_tokens='-5')
check("5-max_tokens '-5' blocked", mt is None and len(errs) == 1)

mt, to, eb, errs = parse(timeout_min='-3')
check("6-timeout_min '-3' blocked", to is None and len(errs) == 1)

mt, to, eb, errs = parse(timeout_min='0')
check("7-timeout_min '0' blocked", to is None and len(errs) == 1)

mt, to, eb, errs = parse(extra_body='[1,2]')
check("8-extra_body array blocked", eb is None and len(errs) == 1)

mt, to, eb, errs = parse(extra_body='not json')
check("9-extra_body non-JSON blocked", eb is None and len(errs) == 1)

mt, to, eb, errs = parse(extra_body='{"model":"m","messages":[],"max_tokens":1,'
                                    '"stream":true,"tools":[]}')
check("10-extra_body all 5 forbidden keys blocked",
      eb is None and len(errs) == 1 and all(k in errs[0] for k in
                                            ('max_tokens', 'messages', 'model', 'stream', 'tools')))

mt, to, eb, errs = parse(max_tokens='   ', timeout_min=' ', extra_body='  ')
check("11-whitespace fields treated as empty (defaults, no errors)",
      mt is None and to is None and eb is None and errs == [])

# --- новые кейсы G3.2g (десятичная запятая в timeout_min) --------------------
mt, to, eb, errs = parse(timeout_min='0,1')
check("12-timeout_min '0,1' -> 6.0s", to == 6.0 and errs == [])

mt, to, eb, errs = parse(timeout_min='1,5')
check("13-timeout_min '1,5' -> 90.0s", to == 90.0 and errs == [])

mt, to, eb, errs = parse(timeout_min='1,5,5')
check("14-timeout_min '1,5,5' blocked", to is None and len(errs) == 1)

mt, to, eb, errs = parse(timeout_min='1.5,5')
check("15-timeout_min '1.5,5' blocked", to is None and len(errs) == 1)

mt, to, eb, errs = parse(timeout_min='abc')
check("16-timeout_min 'abc' blocked", to is None and len(errs) == 1)

mt, to, eb, errs = parse(timeout_min='')
check("17-timeout_min '' -> default (None, no errors)", to is None and errs == [])

base11 = [f for f in fails if f.split('-')[0].isdigit() and int(f.split('-')[0]) <= 11]
print(f"UNIT BASE 11: {11 - len(base11)}/11; NEW G3.2g: {6 - len([f for f in fails if int(f.split('-')[0]) > 11])}/6")
print(f"UNIT PASS {'17/17' if not fails else '16/17+ ' + str(len(fails))} fails: {fails}")
sys.exit(1 if fails else 0)
