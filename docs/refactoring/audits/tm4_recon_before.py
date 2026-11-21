# -*- coding: utf-8 -*-
r"""
BATCH TM4 recon «до» — воспроизводит симптом Дмитрия: подтверждённый
сегмент (запись в TM с ID X) → перевод правится → повторное подтверждение →
запись получает НОВЫЙ ID Y (наблюдение: 463 → 499).

Запуск (из репозитория E:\Dev\SupervertalerPortable), в изолированном профиле:
  TM4_STAGE_DIR=<stage> E:\Dev\python-embed\python.exe -u ^
    docs/refactoring/audits/tm4_recon_before.py > <stage>\out\recon_before.log 2>&1

«CONFIRMED» = симптом воспроизведён на ДО-коде (на ПОСЛЕ-коде должен
исчезнуть). «NOT-REPRODUCED» = не воспроизведён. Код выхода 0 — это
измерение, не gate. JSON-факты пишутся в <stage>\out\tm4_recon_before.json.

Все действия идут через РЕАЛЬНЫЙ путь приложения:
импорт фикстуры (import_simple_txt) → Ctrl+Enter
(_confirm_current_row_segment → update_status_icon →
save_segment_to_activated_tms → db_manager.add_translation_unit).

Сценарии:
  R1  основной симптом: подтвердить → править target → подтвердить:
      ID меняется (ДО-код), запись одна (строка не дублируется),
      created_date/usage_count пересоздаются.
  R2  повторное подтверждение с НЕизменённым target через путь записи
      (статус сброшен в draft имитацией правки-без-изменения текста):
      ID тоже меняется (DELETE+INSERT безусловный).
  R3  счётчик ID: сколько消耗ляется sqlite_sequence за одно подтверждение
      (объяснение скачка 463→499: растёт ли счётчик внутри одного
      подтверждения или между подтверждениями).
  R4  две записываемые TM: после правки обе записи получают новые ID.
  R5  ИМПОРТ (эталон «как раньше», не должен измениться после правки):
      TMX с двумя вариантами одного source → 2 строки; повторный импорт
      той же пары → usage_count+1, ID сохранён (upsert-путь).
  R6  legacy-дубли: две старые записи одного source в одной TM
      (накоплены в режиме 'all') → подтверждение в режиме 'latest'
      оставляет 1 строку (контракт «only latest»).
  R7  удаление записи (delete_entry) + повторное подтверждение → новая
      запись с новым ID (штатно, T-TM4e).
  R8  FTS-согласованность после правки: старый target не находится
      concordance-поиском, новый находится (базлайн: триггеры FTS
      работают и на DELETE+INSERT — то же должно остаться после правки).
"""

import json
import os
import pathlib
import sys

STAGE = pathlib.Path(os.environ.get(
    'TM4_STAGE_DIR', r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-tm4\run-001'))
ISO = STAGE / 'iso'
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

REPRODUCED = []       # (name, ok, detail)
FACTS = {}


def verdict(name, ok, detail=None):
    REPRODUCED.append((name, bool(ok), detail))
    tag = 'CONFIRMED' if ok else 'NOT-REPRODUCED'
    print(f"[{tag}] {name}" + (f" | {detail!r}" if detail is not None else ""), flush=True)


from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

QDialog.exec = (lambda self, *a, **k: QDialog.DialogCode.Accepted)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
_open_queue = []
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (_open_queue.pop(0) if _open_queue else '', ''))

import Supervertaler as SV  # noqa: E402

print('[tm4-recon] building window (1-2 min)...', flush=True)
win = SV.SupervertalerQt()
for _ in range(60):
    app.processEvents()
print('[tm4-recon] window built', flush=True)

# ── Фикстура: 4 сегмента ──────────────────────────────────────────────────
FIX_TXT = OUT / 'tm4_fixture.txt'
FIX_TXT.write_text(
    'Recon sentence one.\n'
    'Recon sentence two.\n'
    'Recon sentence three.\n'
    'Recon sentence four.\n',
    encoding='utf-8')
_open_queue.append(str(FIX_TXT))
win.import_simple_txt()
segs = list(win.current_project.segments)
print(f'[tm4-recon] segments: {len(segs)}', flush=True)
for _s in segs:
    _s.target = ''
    _s.status = 'untranslated'

# Debounced-обработчик набора не участвует в сьюте (набор не тестируется) —
# выключаем, чтобы после подтверждения не прилетел ложный второй вызов записи.
win._handle_target_text_debounced_by_id = lambda *a, **k: None

proj = win.current_project
if proj.id is None:
    proj.id = 1
proj.source_lang = 'en'
proj.target_lang = 'nl'
tm_id_1 = win.tm_metadata_mgr.create_tm(
    'TM4 recon A', 'tm4recona', 'en', 'nl', read_only=False, project_id=proj.id)
win.tm_metadata_mgr.activate_tm(tm_id_1, proj.id)
proj.tm_settings = {'activated_tm_ids': ['tm4recona']}
win.tm_save_mode = 'latest'

cur = win.db_manager.cursor


def _seq():
    cur.execute("SELECT seq FROM sqlite_sequence WHERE name='translation_units'")
    row = cur.fetchone()
    return row['seq'] if row else 0


def _entries(tm_id):
    cur.execute(
        "SELECT id, target_text, created_date, modified_date, usage_count "
        "FROM translation_units WHERE tm_id = ? ORDER BY id", (tm_id,))
    return [dict(r) for r in cur.fetchall()]


def _by_source(tm_id, src):
    rows = [e for e in _entries(tm_id) if e['target_text'] is not None]
    # выбрать по source
    cur.execute(
        "SELECT id, target_text, created_date, modified_date, usage_count "
        "FROM translation_units WHERE tm_id=? AND source_text=? ORDER BY id",
        (tm_id, src))
    return [dict(r) for r in cur.fetchall()]


def fill_target(seg, text):
    """Правка перевода как у пользователя: виджет сетки + сегмент; статус
    confirmed→draft сбрасывается как в реальном on_target_text_changed
    (Supervertaler.py:33192-33196)."""
    row = win._find_row_for_segment(seg.id)
    if row >= 0:
        w = win.table.cellWidget(row, 3)
        if w is not None and hasattr(w, 'setPlainText'):
            w.setPlainText(text)
            app.processEvents()
    seg.target = text
    if seg.status == 'confirmed':
        seg.status = 'draft'


def select_seg(seg):
    row = win._find_row_for_segment(seg.id)
    win.table.clearSelection()
    win.table.setCurrentCell(row, 3)
    win.table.selectRow(row)
    app.processEvents()


def confirm(seg):
    """Реальный Ctrl+Enter путь."""
    select_seg(seg)
    win._confirm_current_row_segment()
    app.processEvents()


# ═══ R1: основной симптом ══════════════════════════════════════════════════
s1 = segs[0]
fill_target(s1, 'Vertaling eerste versie.')
confirm(s1)
import time as _time
_time.sleep(1.1)  # CURRENT_TIMESTAMP имеет разрешение 1 с — разделяем подтверждения
rows1 = _by_source('tm4recona', s1.source)
fact_r1_first = {
    'n_rows': len(rows1),
    'id_first': rows1[0]['id'] if rows1 else None,
    'created': rows1[0]['created_date'] if rows1 else None,
    'usage': rows1[0]['usage_count'] if rows1 else None,
}
print(f"R1 first confirm: {fact_r1_first}", flush=True)

fill_target(s1, 'Vertaling gewijzigd versie.')
confirm(s1)
rows2 = _by_source('tm4recona', s1.source)
fact_r1_second = {
    'n_rows': len(rows2),
    'id_second': rows2[0]['id'] if rows2 else None,
    'created': rows2[0]['created_date'] if rows2 else None,
    'usage': rows2[0]['usage_count'] if rows2 else None,
}
print(f"R1 second confirm: {fact_r1_second}", flush=True)
FACTS['R1'] = {'first': fact_r1_first, 'second': fact_r1_second}

verdict('R1 ID изменился после правки+подтверждения (симптом Дмитрия)',
        fact_r1_second['id_second'] != fact_r1_first['id_first'],
        (fact_r1_first['id_first'], fact_r1_second['id_second']))
verdict('R1 запись одна (строка не дублируется)',
        fact_r1_second['n_rows'] == 1,
        fact_r1_second['n_rows'])
verdict('R1 created_date пересоздан (новая строка)',
        fact_r1_second['created'] != fact_r1_first['created'],
        (fact_r1_first['created'], fact_r1_second['created']))

# ═══ R2: повторное подтверждение с НЕизменённым target через путь записи ══
# Имитация правки-без-изменения: статус сбрасываем в draft, текст тот же.
s1.status = 'draft'
confirm(s1)
rows3 = _by_source('tm4recona', s1.source)
FACTS['R2'] = rows3
verdict('R2 ID изменился даже при неизменённом target (путь записи ушёл в DELETE+INSERT)',
        rows3[0]['id'] != fact_r1_second['id_second'],
        (fact_r1_second['id_second'], rows3[0]['id'] if rows3 else None))

# ═══ R3: счётчик ID внутри одного подтверждения ════════════════════════════
s3 = segs[2]
fill_target(s3, 'Derde zin vertaling.')
seq_before = _seq()
confirm(s3)
seq_after = _seq()
ids_now = _by_source('tm4recona', s3.source)
FACTS['R3'] = {'seq_before': seq_before, 'seq_after': seq_after,
               'new_id': ids_now[0]['id'] if ids_now else None}
verdict('R3 одно подтверждение тратит ровно 1 ID (скачок 463→499 = другие записи между подтверждениями)',
        (seq_after - seq_before) == 1,
        {'seq_before': seq_before, 'seq_after': seq_after})

# ═══ R4: две записываемые TM ═══════════════════════════════════════════════
tm_id_2 = win.tm_metadata_mgr.create_tm(
    'TM4 recon B', 'tm4reconb', 'en', 'nl', read_only=False, project_id=proj.id)
win.tm_metadata_mgr.activate_tm(tm_id_2, proj.id)
proj.tm_settings = {'activated_tm_ids': ['tm4recona', 'tm4reconb']}
s4 = segs[3]
fill_target(s4, 'Vierde zin vertaling.')
confirm(s4)
a4 = _by_source('tm4recona', s4.source)
b4 = _by_source('tm4reconb', s4.source)
FACTS['R4'] = {'A': a4, 'B': b4}
verdict('R4 обе TM получили запись (по одной на TM)',
        len(a4) == 1 and len(b4) == 1, (len(a4), len(b4)))
id_a, id_b = a4[0]['id'], b4[0]['id']
fill_target(s4, 'Vierde zin GEWIJZIGD.')
confirm(s4)
a5 = _by_source('tm4recona', s4.source)
b5 = _by_source('tm4reconb', s4.source)
FACTS['R4_after'] = {'A': a5, 'B': b5}
verdict('R4 после правки ОБА ID сменились (ДО-код)',
        a5[0]['id'] != id_a and b5[0]['id'] != id_b,
        ((id_a, a5[0]['id']), (id_b, b5[0]['id'])))

# ═══ R5: ИМПОРТ — эталон «как раньше» (не должен измениться) ══════════════
tm_id_3 = win.tm_metadata_mgr.create_tm(
    'TM4 recon import', 'tm4reconimp', 'en', 'nl', read_only=False,
    project_id=proj.id)
TMX = OUT / 'tm4_recon_import.tmx'
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
loaded = win.tm_database._load_tmx_into_db(
    str(TMX), 'en', 'nl', 'tm4reconimp')
imp_rows = _by_source('tm4reconimp', 'Import sentence.')
FACTS['R5_first_import'] = {'loaded': loaded, 'rows': imp_rows}
verdict('R5 импорт TMX с двумя вариантами source: 2 строки (варианты сохраняются)',
        len(imp_rows) == 2 and loaded == 2, (loaded, len(imp_rows)))

# повторный импорт той же пары: upsert → usage_count+1, ID сохранён
usage_before = {r['id']: r['usage_count'] for r in imp_rows}
loaded2 = win.tm_database._load_tmx_into_db(
    str(TMX), 'en', 'nl', 'tm4reconimp')
imp_rows2 = _by_source('tm4reconimp', 'Import sentence.')
FACTS['R5_reimport'] = {'loaded': loaded2, 'rows': imp_rows2}
same_ids = set(r['id'] for r in imp_rows) == set(r['id'] for r in imp_rows2)
usage_bumped = all(
    next(x for x in imp_rows2 if x['id'] == i)['usage_count'] > u
    for i, u in usage_before.items())
verdict('R5 повторный импорт: строк по-прежнему 2, ID те же (upsert, не new-ID)',
        len(imp_rows2) == 2 and same_ids, (len(imp_rows2), same_ids))
verdict('R5 повторный импорт: usage_count вырос',
        usage_bumped, usage_before)

# T-TM4f: импорт TMX в TM, где уже есть подтверждением написанная запись
# того же source. Импорт ведёт себя как раньше:
#  - пара (source, ТАКОЙ ЖЕ target) → upsert: ID сохранён, usage_count+1,
#    строк по-прежнему 1;
#  - пара (source, НОВЫЙ target) → добавляется вариант (2 строки).
# Импорт не должен «съедать»/обновлять overwrite-записи подтверждений.
TMX_F = OUT / 'tm4_recon_import_f.tmx'


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


# первый запуск импорта в tm4reconimp мог добавить варианты — пересчитать
_before_f = _by_source('tm4recona', s1.source)
_write_tmf(TMX_F, _before_f[0]['target_text'])
loaded3 = win.tm_database._load_tmx_into_db(
    str(TMX_F), 'en', 'nl', 'tm4recona')
_after_same = _by_source('tm4recona', s1.source)
FACTS['R5f_same_target'] = {
    'before': _before_f, 'loaded': loaded3, 'after': _after_same}
verdict('R5f импорт пары с ТОТ ЖЕ target в TM с overwrite-записью: строка одна, ID сохранён',
        len(_after_same) == 1
        and _after_same[0]['id'] == _before_f[0]['id'],
        (len(_before_f), len(_after_same),
         _before_f[0]['id'], _after_same[0]['id']))
verdict('R5f импорт пары с ТОТ ЖЕ target: usage_count вырос',
        _after_same[0]['usage_count'] > _before_f[0]['usage_count'],
        (_before_f[0]['usage_count'], _after_same[0]['usage_count']))

_write_tmf(TMX_F, 'Vertaling import variant.')
loaded4 = win.tm_database._load_tmx_into_db(
    str(TMX_F), 'en', 'nl', 'tm4recona')
_after_new = _by_source('tm4recona', s1.source)
FACTS['R5f_new_target'] = {'loaded': loaded4, 'after': _after_new}
verdict('R5f импорт пары с НОВЫМ target: добавляется вариант (2 строки), старый ID жив',
        len(_after_new) == 2
        and _before_f[0]['id'] in [r['id'] for r in _after_new],
        ([r['id'] for r in _after_new], _before_f[0]['id']))

# ═══ R6: legacy-дубли + overwrite-подтверждение ════════════════════════════
tm_id_4 = win.tm_metadata_mgr.create_tm(
    'TM4 recon dup', 'tm4recondup', 'en', 'nl', read_only=False,
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
        "(?, ?, 'en', 'nl', 'tm4recondup', ?, ?)",
        (_src, tgt, _src_hash,
         hashlib.md5(_normalize_for_matching(tgt).encode('utf-8')).hexdigest()))
win.db_manager.connection.commit()
dup_before = _by_source('tm4recondup', _src)
FACTS['R6_before'] = dup_before

s_dup = segs[1]
fill_target(s_dup, '')  # на всякий случай чистый target
fill_target(s_dup, 'Legacy variant two.')  # target = существующий вариант
# сегмент источника должен совпадать с _src — перезаписываем source сегмента
s_dup.source = _src
fill_target(s_dup, 'Legacy variant two.')
s_dup.status = 'draft'
confirm(s_dup)
dup_after = _by_source('tm4recondup', _src)
FACTS['R6_after'] = dup_after
verdict('R6 overwrite-подтверждение по legacy-дублям оставляет 1 строку',
        len(dup_after) == 1, len(dup_after))

# ═══ R7: удаление записи + повторное подтверждение = новая запись ══════════
before_del = _by_source('tm4recona', s3.source)
win.db_manager.delete_entry('tm4recona', s3.source, before_del[0]['target_text'])
after_del = _by_source('tm4recona', s3.source)
s3.status = 'draft'
confirm(s3)
after_reconfirm = _by_source('tm4recona', s3.source)
FACTS['R7'] = {'before_del': before_del, 'after_del': after_del,
               'after_reconfirm': after_reconfirm}
verdict('R7 удаление → подтверждение создаёт новую запись',
        len(before_del) == 1 and len(after_del) == 0 and len(after_reconfirm) == 1,
        (len(before_del), len(after_del), len(after_reconfirm)))
verdict('R7 новый ID у новой записи',
        after_reconfirm and after_reconfirm[0]['id'] != before_del[0]['id'],
        (before_del[0]['id'] if before_del else None,
         after_reconfirm[0]['id'] if after_reconfirm else None))

# ═══ R8: FTS-согласованность после правки (базлайн) ════════════════════════
res_old = win.db_manager.concordance_search('eerste versie', tm_ids=['tm4recona'])
res_new = win.db_manager.concordance_search('gewijzigd versie', tm_ids=['tm4recona'])
FACTS['R8'] = {'old_hits': len(res_old), 'new_hits': len(res_new)}
verdict('R8 FTS: старый target не находится, новый находится',
        len(res_old) == 0 and len(res_new) == 1,
        (len(res_old), len(res_new)))

# ── Итог + JSON ────────────────────────────────────────────────────────────
n_conf = sum(1 for _, ok, _ in REPRODUCED if ok)
print(f"\n=== tm4_recon_before: {n_conf}/{len(REPRODUCED)} reproduced ===", flush=True)
for name, ok, detail in REPRODUCED:
    print(f"  [{'CONFIRMED' if ok else 'NOT-REPRODUCED'}] {name}", flush=True)

(OUT / 'tm4_recon_before.json').write_text(
    json.dumps({'facts': FACTS,
                'verdicts': [{'name': n, 'ok': ok, 'detail': str(d)}
                             for n, ok, d in REPRODUCED]},
               ensure_ascii=False, indent=1),
    encoding='utf-8')

try:
    win.db_manager.connection.close()
except Exception:
    pass
print('[tm4-recon] done', flush=True)
os._exit(0)
