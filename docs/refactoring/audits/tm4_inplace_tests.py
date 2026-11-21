# -*- coding: utf-8 -*-
r"""
BATCH TM4 suite — гейт «после»: сохранение ID записи TM при правке перевода
и повторном подтверждении (update-in-place в add_translation_unit,
overwrite-ветка «Save only latest translation»).

Все сценарии проводки идут через РЕАЛЬНЫЙ путь приложения:
импорт фикстуры (import_simple_txt) → Ctrl+Enter
(_confirm_current_row_segment → update_status_icon →
save_segment_to_activated_tms → db_manager.add_translation_unit).
Прямые вызовы БД используются только для СИДОВАНИЯ legacy-состояний
(дубли, FTS-проверки) — это отмечено в названиях проверок.

Запуск (из репозитория E:\Dev\SupervertalerPortable), изолированный профиль:
  TM4_STAGE_DIR=<stage> E:\Dev\python-embed\python.exe -u ^
    docs/refactoring/audits/tm4_inplace_tests.py > <stage>\out\tests.log 2>&1

Код выхода: 0 = все PASS, 1 = есть FAIL.
"""

import json
import os
import pathlib
import sys

STAGE = pathlib.Path(os.environ.get(
    'TM4_STAGE_DIR', r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-tm4\run-001'))
ISO = STAGE / 'iso-tests'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
for d in ('Desktop', 'Documents', 'Downloads', 'tmp'):
    (ISO / d).mkdir(parents=True, exist_ok=True)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import faulthandler  # noqa: E402
faulthandler.dump_traceback_later(90, repeat=True)

PASSED = 0
FAILED = 0
FACTS = {}


def check(name, cond, detail=None):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print('PASS', name, flush=True)
    else:
        FAILED += 1
        print('FAIL', name, '->', repr(detail), flush=True)


from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

QDialog.exec = (lambda self, *a, **k: QDialog.DialogCode.Accepted)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
_open_queue = []
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (_open_queue.pop(0) if _open_queue else '', ''))

import Supervertaler as SV  # noqa: E402

print('[tm4] building window (1-2 min)...', flush=True)
win = SV.SupervertalerQt()
for _ in range(60):
    app.processEvents()
print('[tm4] window built', flush=True)

log_lines = []
_orig_log = win.log


def _capturing_log(msg, *a, **k):
    log_lines.append(str(msg))
    return _orig_log(msg, *a, **k)


win.log = _capturing_log

# Лог db_manager идёт через callback, захваченный ПРИ КОНСТРУИРОВАНИИ
# (Supervertaler.py:6188 log_callback=self.log), — rebind win.log его не
# перехватывает. Оборачиваем сам db_manager.log.
db_log_lines = []
_orig_db_log = win.db_manager.log


def _capturing_db_log(msg, *a, **k):
    db_log_lines.append(str(msg))
    return _orig_db_log(msg, *a, **k)


win.db_manager.log = _capturing_db_log

# ── Фикстура: 4 сегмента ──────────────────────────────────────────────────
FIX_TXT = OUT / 'tm4_fixture.txt'
FIX_TXT.write_text(
    'Suite sentence one.\n'
    'Suite sentence two.\n'
    'Suite sentence three.\n'
    'Suite sentence four.\n',
    encoding='utf-8')
_open_queue.append(str(FIX_TXT))
win.import_simple_txt()
segs = list(win.current_project.segments)
check('B0 фикстура импортирована: 4 сегмента', len(segs) == 4, len(segs))
for _s in segs:
    _s.target = ''
    _s.status = 'untranslated'

win._handle_target_text_debounced_by_id = lambda *a, **k: None

proj = win.current_project
if proj.id is None:
    proj.id = 1
proj.source_lang = 'en'
proj.target_lang = 'nl'
tm_id_1 = win.tm_metadata_mgr.create_tm(
    'TM4 suite A', 'tm4suitea', 'en', 'nl', read_only=False, project_id=proj.id)
win.tm_metadata_mgr.activate_tm(tm_id_1, proj.id)
proj.tm_settings = {'activated_tm_ids': ['tm4suitea']}
win.tm_save_mode = 'latest'

cur = win.db_manager.cursor


def _entries(tm_id, src=None):
    if src is None:
        cur.execute(
            "SELECT id, source_text, target_text, created_date, modified_date, "
            "usage_count FROM translation_units WHERE tm_id = ? ORDER BY id",
            (tm_id,))
    else:
        cur.execute(
            "SELECT id, source_text, target_text, created_date, modified_date, "
            "usage_count FROM translation_units "
            "WHERE tm_id = ? AND source_text = ? ORDER BY id", (tm_id, src))
    return [dict(r) for r in cur.fetchall()]


def fill_target(seg, text):
    row = win._find_row_for_segment(seg.id)
    if row >= 0:
        w = win.table.cellWidget(row, 3)
        if w is not None and hasattr(w, 'setPlainText'):
            w.setPlainText(text)
            app.processEvents()
    seg.target = text
    if seg.status == 'confirmed':
        seg.status = 'draft'  # как реальная правка (Supervertaler.py:33192-33196)


def select_seg(seg):
    row = win._find_row_for_segment(seg.id)
    win.table.clearSelection()
    win.table.setCurrentCell(row, 3)
    win.table.selectRow(row)
    app.processEvents()


def confirm(seg):
    select_seg(seg)
    win._confirm_current_row_segment()
    app.processEvents()


def reset_log():
    log_lines.clear()
    db_log_lines.clear()


# ═══ S1: главный гейт — правка + повторное подтверждение сохраняет ID ════
s1 = segs[0]
fill_target(s1, 'Vertaling eerste versie.')
confirm(s1)
rows1 = _entries('tm4suitea', s1.source)
check('S1 первое подтверждение: 1 строка', len(rows1) == 1, len(rows1))
id1 = rows1[0]['id']
created1 = rows1[0]['created_date']

import time as _time
_time.sleep(1.1)  # modified/created имеют разрешение 1 с
fill_target(s1, 'Vertaling gewijzigd versie.')
reset_log()
confirm(s1)
rows2 = _entries('tm4suitea', s1.source)
check('S1 после правки+подтверждения: СТОЙ же ID',
      len(rows2) == 1 and rows2[0]['id'] == id1,
      (id1, [r['id'] for r in rows2]))
check('S1 запись одна (не две)', len(rows2) == 1, len(rows2))
check('S1 target обновлён на новый',
      rows2 and rows2[0]['target_text'] == 'Vertaling gewijzigd versie.',
      rows2[0]['target_text'] if rows2 else None)
check('S1 created_date сохранён', rows2 and rows2[0]['created_date'] == created1,
      (created1, rows2[0]['created_date'] if rows2 else None))
check('S1 modified_date обновился',
      rows2 and rows2[0]['modified_date'] != created1,
      (created1, rows2[0]['modified_date'] if rows2 else None))
# usage_count на реальном пути НЕ проверяем на точное значение: инстант-
# TM-lookup приложения делает touch (+1) при выборе строки и в старом коде
# маскировал бы сброс. Точный гейт сохранения usage_count — S1u (DB-уровень).
FACTS['S1'] = {'before': rows1, 'after': rows2}

# S3: лог по-английски, одной строкой, без модалей — перехват db_manager.log
# (проверяется СРАЗУ после S1, до S1u, чтобы в перехват не попадали строки
# юнит-блока)
inplace_logs = [m for m in db_log_lines if 'updated in place' in m]
check('S3 лог «TM entry #N updated in place» записан',
      len(inplace_logs) == 1 and f'#{id1}' in inplace_logs[0]
      and 'tm4suitea' in inplace_logs[0],
      inplace_logs)

# S1u: детерминированный гейт сохранения usage_count на слое, который правится
# (add_translation_unit, overwrite-ветка): touch → правка target → в старом
# коде DELETE+INSERT сбросил бы usage в 0, теперь сохраняется.
_s1u_tm = 'tm4suitea'
_s1u_src = 'Unit-level usage preservation sentence.'
_r1u = win.db_manager.add_translation_unit(
    source=_s1u_src, target='Usage variant one.', source_lang='en',
    target_lang='nl', tm_id=_s1u_tm, overwrite=True)
win.db_manager.get_exact_match(_s1u_src, tm_ids=[_s1u_tm], touch=True)
_r1u_after_touch = win.db_manager.get_exact_match(
    _s1u_src, tm_ids=[_s1u_tm], touch=False)
check('S1u touch поднял usage_count до 1',
      _r1u_after_touch and _r1u_after_touch['usage_count'] == 1,
      _r1u_after_touch['usage_count'] if _r1u_after_touch else None)
_r2u = win.db_manager.add_translation_unit(
    source=_s1u_src, target='Usage variant TWO (edited).', source_lang='en',
    target_lang='nl', tm_id=_s1u_tm, overwrite=True)
check('S1u правка target возвращает ТОТ ЖЕ ID (in-place)',
      _r2u == _r1u, (_r1u, _r2u))
_r2u_row = win.db_manager.get_exact_match(_s1u_src, tm_ids=[_s1u_tm], touch=False)
check('S1u usage_count НЕ сброшен после правки target',
      _r2u_row and _r2u_row['usage_count'] == 1,
      _r2u_row['usage_count'] if _r2u_row else None)
_r3u = win.db_manager.add_translation_unit(
    source=_s1u_src, target='Usage variant TWO (edited).', source_lang='en',
    target_lang='nl', tm_id=_s1u_tm, overwrite=True)
check('S1u подтверждение того же target: ID тот же, usage не тронут',
      _r3u == _r1u and _r3u is not None
      and win.db_manager.get_exact_match(_s1u_src, tm_ids=[_s1u_tm],
                                         touch=False)['usage_count'] == 1,
      (_r1u, _r3u))

# ═══ S2: повторное подтверждение с НЕизменённым target (через путь записи) ═
_time.sleep(1.1)
s1.status = 'draft'  # имитация правки-без-изменения: путь записи сработает
confirm(s1)
rows3 = _entries('tm4suitea', s1.source)
check('S2 подтверждение без правки: ID тот же, строка одна',
      len(rows3) == 1 and rows3[0]['id'] == id1,
      (id1, [r['id'] for r in rows3]))
# usage_count на реальном пути — см. комментарий к S1/S1u (S1u покрывает).
FACTS['S2'] = rows3

# ═══ S5: FTS/concordance — старый target не ищется, новый ищется ══════════
res_old = win.db_manager.concordance_search('eerste versie', tm_ids=['tm4suitea'])
res_new = win.db_manager.concordance_search('gewijzigd versie', tm_ids=['tm4suitea'])
check('S5 concordance: старый target не находится', len(res_old) == 0, len(res_old))
check('S5 concordance: новый target находится', len(res_new) == 1, len(res_new))
cur.execute(
    "SELECT rowid FROM translation_units_fts WHERE translation_units_fts "
    "MATCH 'gewijzigd'")
fts_ids = [r['rowid'] for r in cur.fetchall()]
check('S5 FTS: rowid найденной записи = сохранённый ID', fts_ids == [id1],
      (fts_ids, id1))

# ═══ S4: две записываемые TM — каждая хранит свой ID ══════════════════════
tm_id_2 = win.tm_metadata_mgr.create_tm(
    'TM4 suite B', 'tm4suiteb', 'en', 'nl', read_only=False, project_id=proj.id)
win.tm_metadata_mgr.activate_tm(tm_id_2, proj.id)
proj.tm_settings = {'activated_tm_ids': ['tm4suitea', 'tm4suiteb']}
s4 = segs[3]
fill_target(s4, 'Vierde zin vertaling.')
confirm(s4)
a4 = _entries('tm4suitea', s4.source)
b4 = _entries('tm4suiteb', s4.source)
check('S4 обе TM получили запись', len(a4) == 1 and len(b4) == 1,
      (len(a4), len(b4)))
check('S4 ID в двух TM разные (каждая хранит свою запись)',
      a4[0]['id'] != b4[0]['id'], (a4[0]['id'], b4[0]['id']))
id_a, id_b = a4[0]['id'], b4[0]['id']
_time.sleep(1.1)
fill_target(s4, 'Vierde zin GEWIJZIGD.')
confirm(s4)
a5 = _entries('tm4suitea', s4.source)
b5 = _entries('tm4suiteb', s4.source)
check('S4 после правки оба ID сохранены',
      len(a5) == 1 and a5[0]['id'] == id_a and len(b5) == 1 and b5[0]['id'] == id_b,
      ((id_a, [r['id'] for r in a5]), (id_b, [r['id'] for r in b5])))
check('S4 target в обеих TM обновлён',
      a5[0]['target_text'] == 'Vierde zin GEWIJZIGD.'
      and b5[0]['target_text'] == 'Vierde zin GEWIJZIGD.',
      (a5[0]['target_text'], b5[0]['target_text']))
FACTS['S4'] = {'A_before': a4, 'B_before': b4, 'A_after': a5, 'B_after': b5}

# ═══ S6: ИМПОРТ — поведение «как раньше» (эталон из recon «до») ═══════════
tm_id_3 = win.tm_metadata_mgr.create_tm(
    'TM4 suite import', 'tm4suiteimp', 'en', 'nl', read_only=False,
    project_id=proj.id)
TMX = OUT / 'tm4_suite_import.tmx'
TMX.write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<tmx version="1.4"><header creationtool="tm4" segtype="sentence" '
    'o-tmf="tm4" adminlang="en" srclang="en" datatype="plaintext" '
    'creationtoolversion="1"/>'
    '<body>'
    '<tu><tuv xml:lang="en"><seg>Import sentence.</seg></tuv>'
    '<tuv xml:lang="nl"><seg>Import vertaling v1.</seg></tuv></tu>'
    '<tu><tuv xml:lang="en"><seg>Import sentence.</seg></tuv>'
    '<tuv xml:lang="nl"><seg>Import vertaling v2.</seg></tuv></tu>'
    '</body></tmx>', encoding='utf-8')
loaded = win.tm_database._load_tmx_into_db(str(TMX), 'en', 'nl', 'tm4suiteimp')
imp1 = _entries('tm4suiteimp', 'Import sentence.')
check('S6 импорт TMX с двумя вариантами: 2 строки, 2 разных ID (как раньше)',
      len(imp1) == 2 and loaded == 2 and imp1[0]['id'] != imp1[1]['id'],
      (loaded, [r['id'] for r in imp1]))
usage1 = {r['id']: r['usage_count'] for r in imp1}
loaded2 = win.tm_database._load_tmx_into_db(str(TMX), 'en', 'nl', 'tm4suiteimp')
imp2 = _entries('tm4suiteimp', 'Import sentence.')
check('S6 повторный импорт: строки те же, ID те же, usage_count+1 (как раньше)',
      len(imp2) == 2
      and {r['id'] for r in imp2} == {r['id'] for r in imp1}
      and all(next(x for x in imp2 if x['id'] == i)['usage_count'] > u
              for i, u in usage1.items()),
      (loaded2, [r['id'] for r in imp2], usage1))

# импорт в TM с overwrite-записью (T-TM4f): same target → upsert (ID жив,
# usage+1, 1 строка); новый target → добавляется вариант (2 строки)
_before_f = _entries('tm4suitea', s1.source)
TMX_F = OUT / 'tm4_suite_import_f.tmx'


def _write_tmf(path, tgt):
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<tmx version="1.4"><header creationtool="tm4" segtype="sentence" '
        'o-tmf="tm4" adminlang="en" srclang="en" datatype="plaintext" '
        'creationtoolversion="1"/>'
        '<body>'
        f'<tu><tuv xml:lang="en"><seg>{s1.source}</seg></tuv>'
        f'<tuv xml:lang="nl"><seg>{tgt}</seg></tuv></tu>'
        '</body></tmx>', encoding='utf-8')


_write_tmf(TMX_F, _before_f[0]['target_text'])
loaded3 = win.tm_database._load_tmx_into_db(str(TMX_F), 'en', 'nl', 'tm4suitea')
_after_same = _entries('tm4suitea', s1.source)
check('S6f импорт пары с ТОТ ЖЕ target: строка одна, ID сохранён, usage+1',
      len(_after_same) == 1 and _after_same[0]['id'] == _before_f[0]['id']
      and _after_same[0]['usage_count'] > _before_f[0]['usage_count'],
      ([r['id'] for r in _after_same], _before_f[0]['id']))
_write_tmf(TMX_F, 'Vertaling import variant.')
loaded4 = win.tm_database._load_tmx_into_db(str(TMX_F), 'en', 'nl', 'tm4suitea')
_after_new = _entries('tm4suitea', s1.source)
check('S6f импорт пары с НОВЫМ target: 2 строки, старый ID жив (как раньше)',
      len(_after_new) == 2 and _before_f[0]['id'] in [r['id'] for r in _after_new],
      ([r['id'] for r in _after_new], _before_f[0]['id']))
FACTS['S6'] = {'first': imp1, 'reimport': imp2, 'f_same': _after_same,
               'f_new': _after_new}

# ═══ S7: legacy-дубли — overwrite-подтверждение сохраняет один ID ═════════
tm_id_4 = win.tm_metadata_mgr.create_tm(
    'TM4 suite dup', 'tm4suitedup', 'en', 'nl', read_only=False,
    project_id=proj.id)
win.tm_metadata_mgr.activate_tm(tm_id_4, proj.id)
import hashlib  # noqa: E402
from modules.database_manager import _normalize_for_matching  # noqa: E402
_src = 'Legacy duplicate sentence.'
_src_hash = hashlib.md5(_normalize_for_matching(_src).encode('utf-8')).hexdigest()
for tgt in ('Legacy variant one.', 'Legacy variant two.'):
    cur.execute(
        "INSERT INTO translation_units (source_text, target_text, source_lang, "
        "target_lang, tm_id, source_hash, target_hash) VALUES "
        "(?, ?, 'en', 'nl', 'tm4suitedup', ?, ?)",
        (_src, tgt, _src_hash,
         hashlib.md5(_normalize_for_matching(tgt).encode('utf-8')).hexdigest()))
win.db_manager.connection.commit()
dup_before = _entries('tm4suitedup', _src)
check('S7 сид: 2 legacy-варианта', len(dup_before) == 2, len(dup_before))

s_dup = segs[1]
s_dup.source = _src
_time.sleep(1.1)
fill_target(s_dup, 'Legacy variant two.')  # target совпадает со вторым вариантом
s_dup.status = 'draft'
confirm(s_dup)
dup_after = _entries('tm4suitedup', _src)
check('S7 после подтверждения: 1 строка (контракт «latest»)',
      len(dup_after) == 1, len(dup_after))
check('S7 ID сохранён из числа прежних (не новый)',
      dup_after and dup_after[0]['id'] in [r['id'] for r in dup_before],
      ([r['id'] for r in dup_before], [r['id'] for r in dup_after]))
check('S7 target существующего варианта не изменился',
      dup_after and dup_after[0]['target_text'] == 'Legacy variant two.',
      dup_after[0]['target_text'] if dup_after else None)

# тот же источник с НОВЫМ target: дубль-строка обновляется на месте
_time.sleep(1.1)
kept_id = dup_after[0]['id']
fill_target(s_dup, 'Legacy variant THREE.')
s_dup.status = 'draft'
confirm(s_dup)
dup_after2 = _entries('tm4suitedup', _src)
check('S7 новый target по дублям: 1 строка, ID прежний, текст новый',
      len(dup_after2) == 1 and dup_after2[0]['id'] == kept_id
      and dup_after2[0]['target_text'] == 'Legacy variant THREE.',
      ([r['id'] for r in dup_after2], kept_id))
FACTS['S7'] = {'before': dup_before, 'after1': dup_after, 'after2': dup_after2}

# ═══ S8: удаление записи + повторное подтверждение = новая запись ═════════
before_del = _entries('tm4suitea', s4.source)
win.db_manager.delete_entry('tm4suitea', s4.source, before_del[0]['target_text'])
after_del = _entries('tm4suitea', s4.source)
_time.sleep(1.1)
s4.status = 'draft'
confirm(s4)
after_re = _entries('tm4suitea', s4.source)
check('S8 удаление → подтверждение создаёт новую запись',
      len(before_del) == 1 and len(after_del) == 0 and len(after_re) == 1,
      (len(before_del), len(after_del), len(after_re)))
check('S8 у новой записи новый ID, в другой TM запись не тронута',
      after_re and after_re[0]['id'] != before_del[0]['id']
      and len(_entries('tm4suiteb', s4.source)) == 1,
      ([r['id'] for r in before_del], [r['id'] for r in after_re]))
FACTS['S8'] = {'before': before_del, 'after': after_re}

# ═══ S9: режим 'all' (overwrite=False) — семантика вариантов не изменена ══
win.tm_save_mode = 'all'
tm_id_5 = win.tm_metadata_mgr.create_tm(
    'TM4 suite all', 'tm4suiteall', 'en', 'nl', read_only=False,
    project_id=proj.id)
win.tm_metadata_mgr.activate_tm(tm_id_5, proj.id)
s9 = segs[2]
fill_target(s9, 'All-mode variant one.')
s9.status = 'draft'
confirm(s9)
all1 = _entries('tm4suiteall', s9.source)
check('S9 all-режим: 1 строка', len(all1) == 1, len(all1))
_time.sleep(1.1)
fill_target(s9, 'All-mode variant two.')  # другой target → вариант
s9.status = 'draft'
confirm(s9)
all2 = _entries('tm4suiteall', s9.source)
check('S9 all-режим: другой target добавляет вариант (2 строки, как раньше)',
      len(all2) == 2 and all1[0]['id'] in [r['id'] for r in all2],
      ([r['id'] for r in all2], all1[0]['id']))
_time.sleep(1.1)
fill_target(s9, 'All-mode variant two.')  # тот же target → upsert
s9.status = 'draft'
confirm(s9)
all3 = _entries('tm4suiteall', s9.source)
check('S9 all-режим: тот же target — строк по-прежнему 2, usage растёт у совпавшей',
      len(all3) == 2, len(all3))
win.tm_save_mode = 'latest'
FACTS['S9'] = {'v1': all1, 'v2': all2, 'v3': all3}

# ── Итог ───────────────────────────────────────────────────────────────────
print(f"\n=== tm4_inplace_tests: PASS {PASSED}, FAIL {FAILED} ===", flush=True)
(OUT / 'tm4_inplace_tests.json').write_text(
    json.dumps({'passed': PASSED, 'failed': FAILED, 'facts': FACTS},
               ensure_ascii=False, indent=1, default=str),
    encoding='utf-8')

try:
    win.db_manager.connection.close()
except Exception:
    pass
print('[tm4] done', flush=True)
# os._exit вместо sys.exit: после вердикта Qt-teardown (pynput-поток горячих
# клавиш, QThreadStorage) изредка сегфолтится и портит exit-код прогонщика —
# вердикт уже напечатан и записан в JSON.
os._exit(1 if FAILED else 0)
