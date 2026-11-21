# -*- coding: utf-8 -*-
r"""
BATCH TM5 recon «до» — импорт TMX в TM: два симптома Дмитрия и путь
TMXImportThread из разведки TM4.

Симптомы (D:\Supervertaler_clean, наблюдения Дмитрия):
  1. Импортированные в TM записи «не появляются в Editor вообще никак»
     (перевод сегмента с совпадающим source — совпадения нет).
  2. Кнопка «+ Create New TM» сама ставит галку Read; импорт TMX в режиме
     «создать базу» — нет.
  3. Двойной импорт одного TMX дублей не даёт (поведение сохранить).
  4. Разведка TM4: TMXImportThread (tm_manager_qt.py:86) вызывает
     add_translation_unit(…, save_mode='all') — параметра нет → TypeError
     → «Import failed». Достижимость и последствия не проверены.

Запуск (из репозитория E:\Dev\SupervertalerPortable), изолированный профиль:
  TM5_STAGE_DIR=<stage> E:\Dev\python-embed\python.exe -u ^
    docs/refactoring/audits/tm5_recon_import.py > <stage>\out\recon_before.log 2>&1

«CONFIRMED» = симптом воспроизведён на ДО-коде (на ПОСЛЕ-коде должен
исчезнуть или остаться как эталон — помечено отдельно). «NOT-REPRODUCED» =
не воспроизведён. Код выхода 0 — это измерение, не gate. JSON-факты:
<stage>\out\tm5_recon_before.json.

Все действия — через РЕАЛЬНЫЕ обработчики кнопок:
  R0  реальная кнопка «+ Create New TM» → эталон галки Read (создаёт TM
      create_tm + activate_tm, Supervertaler.py:18196-18197).
  R1  реальная кнопка «📥 Import TMX» → «Create new TM from this TMX»
      (fixture A, теги en-US/ru-RU, 4 пары; SRC4 уникален для A) →
      СИМПТОМ 2 (Read off) и СИМПТОМ 1 (совпадений нет: реальный поиск
      Editor через tm_database.search_all c активными TM и точный
      instant-путь _show_instant_tm_match не видят импортированную TM).
  R2  «📥 Import TMX» → «Add to existing TM» (fixture B в TM из R0) →
      записи пишутся (upsert), галки других TM не меняются.
  R3  TM Editor (реальный TMEditorDialog → вкладка Import/Export →
      «📂 Select and Import TMX...» → TMXImportThread) → СИМПТОМ 4:
      TypeError «Import failed», БД чистая (0 записей, мусорной TM нет).
  R4  «📥 Import TMX» → «Create new TM» (fixture B, теги EN/ru) →
      нормализация языков: EN→en при импорте (0.5), записи корректны.
  R5  повторный импорт fixture B «Add to existing TM» → СИМПТОМ 3:
      число записей не растёт (эталон, не должен измениться после правки).
  R6  после РУЧНОЙ активации Read (тот же механизм, что у галки —
      activate_tm + invalidate_translation_cache) реальный поисковый
      вызов Editor (tm_database.search_all c активными TM) находит пару
      SRC4→TGT4 (текст сверен; SRC4 уникален для fixture A);
      _show_instant_tm_match на несвежем снапшоте проекта — измеряется
      (известный нюанс, общий и для «+ Create New TM»), после синхронизации
      снапшота (как при сохранении проекта) — находит.
"""

import json
import os
import pathlib
import sys

STAGE = pathlib.Path(os.environ.get(
    'TM5_STAGE_DIR', r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-tm5\run-001'))
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

RESULTS = []          # (name, reproduced(bool), detail)
FACTS = {}


def verdict(name, ok, detail=None):
    """ok=True → симптом/факт воспроизведён (или эталон подтверждён)."""
    RESULTS.append((name, bool(ok), detail))
    tag = 'CONFIRMED' if ok else 'NOT-REPRODUCED'
    print(f"[{tag}] {name}" + (f" | {detail!r}" if detail is not None else ""), flush=True)


from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QDialog, QMessageBox, QFileDialog,
                             QInputDialog, QLineEdit, QPushButton, QRadioButton,
                             QComboBox, QTableWidget)  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

# ── Обезвреживание модальных диалогов ─────────────────────────────────────
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
CRITICAL_MSGS = []


def _critical_stub(*a, **k):
    # QMessageBox.critical(parent, title, text) — текст третий позиционный
    # (или keyword text=); записываем для вердикта.
    msg = k.get('text') or (a[2] if len(a) >= 3 else '')
    CRITICAL_MSGS.append(str(msg))
    return QMessageBox.StandardButton.Ok


QMessageBox.critical = staticmethod(_critical_stub)

_open_queue = []
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (_open_queue.pop(0) if _open_queue else '', ''))
_name_queue = []          # имена для QInputDialog (импорт → имя новой TM)
QInputDialog.getText = staticmethod(
    lambda *a, **k: (_name_queue.pop(0) if _name_queue else ('', False)))


def _default_exec_stub(dialog_self, *a, **k):
    """Дефолт: принять диалог как есть (radio «Create new TM» стоит по
    умолчанию, пары языков предвыбирает _preselect_tmx_pair)."""
    return QDialog.DialogCode.Accepted


def _make_add_existing_stub(tm_name):
    def _stub(dialog_self, *a, **k):
        for rb in dialog_self.findChildren(QRadioButton):
            if 'Add to existing TM' in rb.text():
                rb.setChecked(True)
                break
        for cb in dialog_self.findChildren(QComboBox):
            idx = cb.findText(tm_name)
            if idx >= 0:
                cb.setCurrentIndex(idx)
        return QDialog.DialogCode.Accepted
    return _stub


def _make_create_tm_stub(name, tm_id, src, tgt):
    def _stub(dialog_self, *a, **k):
        for f, val in zip(dialog_self.findChildren(QLineEdit),
                          [name, tm_id, src, tgt]):
            f.setText(val)
        return QDialog.DialogCode.Accepted
    return _stub


QDialog.exec = _default_exec_stub

import Supervertaler as SV  # noqa: E402

print('[tm5-recon] building window (1-2 min)...', flush=True)
win = SV.SupervertalerQt()
for _ in range(60):
    app.processEvents()
print('[tm5-recon] window built', flush=True)

# ── Проект: 3 сегмента, source = источники пар TMX ────────────────────────
SRC1 = 'The quick brown fox jumps over the lazy dog.'
SRC2 = 'Translation memory import test sentence.'
SRC3 = 'Third recon sentence with unique words zqwq.'
SRC4 = 'Fourth recon sentence unique to fixture A zqza.'
TGT1 = 'Быстрая бурая лиса прыгает через ленивого пса.'
TGT2 = 'Предложение для теста импорта памяти переводов.'
TGT3 = 'Третье разведочное предложение со словами зкжк.'
TGT4 = 'Четвёртое разведочное предложение уникальное для A зкза.'

FIX_TXT = OUT / 'tm5_project_fixture.txt'
FIX_TXT.write_text(f'{SRC1}\n{SRC2}\n{SRC3}\n{SRC4}\n', encoding='utf-8')

FIX_A = OUT / 'tm5_fixture_a_enUS.tmx'
FIX_A.write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<tmx version="1.4">\n'
    '  <header creationtool="SupervertalerRecon" srclang="en-US" adminlang="en" '
    'segtype="sentence" datatype="plaintext"/>\n'
    '  <body>\n'
    f'    <tu><tuv xml:lang="en-US"><seg>{SRC1}</seg></tuv>'
    f'<tuv xml:lang="ru-RU"><seg>{TGT1}</seg></tuv></tu>\n'
    f'    <tu><tuv xml:lang="en-US"><seg>{SRC2}</seg></tuv>'
    f'<tuv xml:lang="ru-RU"><seg>{TGT2}</seg></tuv></tu>\n'
    f'    <tu><tuv xml:lang="en-US"><seg>{SRC3}</seg></tuv>'
    f'<tuv xml:lang="ru-RU"><seg>{TGT3}</seg></tuv></tu>\n'
    f'    <tu><tuv xml:lang="en-US"><seg>{SRC4}</seg></tuv>'
    f'<tuv xml:lang="ru-RU"><seg>{TGT4}</seg></tuv></tu>\n'
    '  </body>\n'
    '</tmx>\n', encoding='utf-8')

FIX_B = OUT / 'tm5_fixture_b_en.tmx'
FIX_B.write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<tmx version="1.4">\n'
    '  <header creationtool="SupervertalerRecon" srclang="EN" adminlang="en" '
    'segtype="sentence" datatype="plaintext"/>\n'
    '  <body>\n'
    f'    <tu><tuv xml:lang="EN"><seg>{SRC1}</seg></tuv>'
    f'<tuv xml:lang="ru"><seg>{TGT1}</seg></tuv></tu>\n'
    f'    <tu><tuv xml:lang="EN"><seg>{SRC2}</seg></tuv>'
    f'<tuv xml:lang="ru"><seg>{TGT2}</seg></tuv></tu>\n'
    f'    <tu><tuv xml:lang="EN"><seg>{SRC3}</seg></tuv>'
    f'<tuv xml:lang="ru"><seg>{TGT3}</seg></tuv></tu>\n'
    '  </body>\n'
    '</tmx>\n', encoding='utf-8')

_open_queue.append(str(FIX_TXT))
win.import_simple_txt()
segs = list(win.current_project.segments)
print(f'[tm5-recon] segments: {len(segs)}', flush=True)
for _s in segs:
    _s.target = ''
    _s.status = 'untranslated'

win._handle_target_text_debounced_by_id = lambda *a, **k: None

proj = win.current_project
if proj.id is None:
    proj.id = 1
proj.source_lang = 'en'
proj.target_lang = 'ru'
win.initialize_tm_database()

cur = win.db_manager.cursor


def tm_rows(tm_id):
    cur.execute(
        "SELECT id, source_text, target_text, source_lang, target_lang, "
        "usage_count FROM translation_units WHERE tm_id = ? ORDER BY id",
        (tm_id,))
    return [dict(r) for r in cur.fetchall()]


def tm_meta(tm_id):
    return win.tm_metadata_mgr.get_tm_by_tm_id(tm_id)


def read_flag(tm_id):
    m = tm_meta(tm_id)
    if not m:
        return None
    return bool(win.tm_metadata_mgr.is_tm_active(m['id'], proj.id))


def read_checkbox_state(tm_name):
    """Буквальное состояние галки Read в таблице TM (колонка 3)."""
    for t in win.findChildren(QTableWidget):
        hdr = t.horizontalHeaderItem(3)
        if hdr is not None and hdr.text() == 'Read':
            for r in range(t.rowCount()):
                it = t.item(r, 0)
                if it is not None and it.text() == tm_name:
                    w = t.cellWidget(r, 3)
                    return None if w is None else bool(w.isChecked())
    return None


def find_button(text_part):
    for b in win.findChildren(QPushButton):
        if text_part in b.text():
            return b
    return None


def editor_match(source):
    """Реальный поиск, который выполняет ветка панели Editor
    (search_and_display_tm_matches → tm_database.search_all с активными TM).

    Панельная ветка search_and_display_tm_matches в текущем билде
    недостижима: атрибут assistance_widget не создаётся нигде
    (Supervertaler.py:40610 → AttributeError → лог «Error searching TM»),
    поэтому её содержимое в offscreen-прогоне не проверяем — проверяем
    сам поисковый вызов и текст найденного перевода."""
    tm_ids = win.tm_metadata_mgr.get_active_tm_ids(proj.id)
    matches = win.tm_database.search_all(source, tm_ids=tm_ids, max_matches=5)
    return [{'target': m['target'], 'tm_id': m['tm_id'],
             'pct': m['match_pct']} for m in matches]


def instant_match(seg):
    """Реальный точный путь на клик: _show_instant_tm_match.

    Dedup-guard (win._instant_tm_guard, Supervertaler.py:51316-51321)
    сбрасываем перед КАЖДЫМ замером: guard возвращает True («уже показано»)
    и для ранее не найденного source, что маскировало бы miss."""
    try:
        win._instant_tm_guard = None
        return bool(win._show_instant_tm_match(seg))
    except Exception as e:
        return f'EXC:{e}'


def click_import_tmx_button(fixture_path, mode_stub=None, new_name=None):
    """Реальная кнопка «📥 Import TMX» (путь _import_tmx_as_tm).

    Обработчик кнопки синхронный: выбор файла → диалог режима → (имя) →
    (пара языков) → create_tm → _load_tmx_into_db → refresh_callback.
    Дополнительные processEvents — только чтобы осели UI-события."""
    _open_queue.append(str(fixture_path))
    if new_name:
        _name_queue.append((new_name, True))
    btn = find_button('Import TMX')
    if btn is None:
        return 'BUTTON_NOT_FOUND'
    old_exec = QDialog.exec
    QDialog.exec = mode_stub if mode_stub else _default_exec_stub
    try:
        btn.click()
        for _ in range(20):
            app.processEvents()
    finally:
        QDialog.exec = old_exec
    return 'OK'


# ══ R0: эталон — реальная кнопка «+ Create New TM» ═══════════════════════
create_btn = find_button('Create New TM')
QDialog.exec = _make_create_tm_stub('TM5 Recon Ref TM', 'tm5reconref', 'en', 'ru')
try:
    create_btn.click()
    app.processEvents()
finally:
    QDialog.exec = _default_exec_stub

ref_meta = tm_meta('tm5reconref')
ref_read = read_flag('tm5reconref')
ref_cb = read_checkbox_state('TM5 Recon Ref TM')
verdict('R0 +Create New TM: TM создана', ref_meta is not None,
        {'name': ref_meta['name'] if ref_meta else None,
         'tm_id': ref_meta['tm_id'] if ref_meta else None})
verdict('R0 +Create New TM: Read auto-ON (эталон для симптома 2)',
        ref_read is True and (ref_cb is True or ref_cb is None),
        {'is_active': ref_read, 'checkbox': ref_cb})
FACTS['r0'] = {'read': ref_read, 'checkbox': ref_cb,
               'db_id': ref_meta['id'] if ref_meta else None}

# Имитация загруженного проекта с сохранённым списком активных TM
# (снапшот tm_settings['activated_tm_ids'] — его читает instant-путь
# _show_instant_tm_match, Supervertaler.py:51303-51306; у реального
# Дмитрия в проекте была активная TM, список непустой).
proj.tm_settings = {'activated_tm_ids': ['tm5reconref'],
                    'tm_read_only_status': {'tm5reconref': False}}

# ══ R1: «📥 Import TMX» → «Create new TM from this TMX» (fixture A) ══════
CRITICAL_MSGS.clear()
r1 = click_import_tmx_button(FIX_A, new_name='TM5 Recon Import A')
imp_a = tm_meta('tm5_recon_import_a')
if imp_a is None:
    imp_a = tm_meta('tm5reconimporta')  # запасной вариант tm_id
rows_a = tm_rows(imp_a['tm_id']) if imp_a else []
FACTS['r1'] = {
    'button': r1, 'tm_found': imp_a is not None,
    'meta': {k: imp_a[k] for k in ('name', 'tm_id', 'source_lang', 'target_lang')}
            if imp_a else None,
    'rows': len(rows_a),
    'row_langs': sorted({(r['source_lang'], r['target_lang']) for r in rows_a}),
    'read_flag': read_flag(imp_a['tm_id']) if imp_a else None,
    'read_checkbox': read_checkbox_state(imp_a['name']) if imp_a else None,
    'critical_msgs': list(CRITICAL_MSGS),
}
print('[tm5-recon] R1 facts:', json.dumps(FACTS['r1'], ensure_ascii=False), flush=True)

verdict('R1 Import-create: TM создана и записи записаны (4 пары fixture A)',
        imp_a is not None and len(rows_a) == 4,
        {'rows': len(rows_a), 'crit': FACTS['r1']['critical_msgs']})
verdict('R1 СИМПТОМ 2: галка Read у TM импорта OFF',
        imp_a is not None and FACTS['r1']['read_flag'] is False,
        {'read_flag': FACTS['r1']['read_flag'],
         'checkbox': FACTS['r1']['read_checkbox']})

# СИМПТОМ 1: совпадений нет (другая TM активна → список непуст).
# Сегмент SRC4 — уникален для fixture A: его нет в ref TM и fixture B,
# поэтому miss/hit однозначно указывает на импортированную TM.
seg1 = next(s for s in segs if s.source == SRC4)
active_ids = win.tm_metadata_mgr.get_active_tm_ids(proj.id)
m_r1 = editor_match(SRC4)
inst_r1 = instant_match(seg1)
FACTS['r1_match'] = {'active_ids': active_ids, 'panel': m_r1,
                     'instant': inst_r1,
                     'snapshot': proj.tm_settings.get('activated_tm_ids')}
print('[tm5-recon] R1 match facts:',
      json.dumps(FACTS['r1_match'], ensure_ascii=False)[:600], flush=True)
verdict('R1 СИМПТОМ 1: Editor не находит импортированную пару',
        len(m_r1) == 0 and inst_r1 is False,
        {'panel_n': len(m_r1), 'instant': inst_r1, 'active_ids': active_ids})

# ══ R2: «📥 Import TMX» → «Add to existing TM» (fixture B в TM из R0) ════
# (fixture B, а не A: SRC4 остаётся уникальным для import-A TM, чтобы
# измерения instant в R1/R6 не загрязнялись записями в ref TM.)
CRITICAL_MSGS.clear()
ref_rows_before = len(tm_rows('tm5reconref'))
r2 = click_import_tmx_button(FIX_B, mode_stub=_make_add_existing_stub('TM5 Recon Ref TM'))
rows_ref_after = tm_rows('tm5reconref')
ref_read_after = read_flag('tm5reconref')
FACTS['r2'] = {
    'button': r2, 'rows_before': ref_rows_before,
    'rows_after': len(rows_ref_after),
    'crit': list(CRITICAL_MSGS),
    'read_flag_ref': ref_read_after,
    'read_flag_import_a': read_flag(imp_a['tm_id']) if imp_a else None,
}
print('[tm5-recon] R2 facts:', json.dumps(FACTS['r2'], ensure_ascii=False), flush=True)
verdict('R2 Add-to-existing: записи добавлены в существующую TM',
        len(rows_ref_after) == 3 and ref_rows_before == 0,
        {'before': ref_rows_before, 'after': len(rows_ref_after)})
verdict('R2 Add-to-existing: галки других TM не изменились',
        ref_read_after is True and read_flag(imp_a['tm_id']) is False,
        {'ref_read': ref_read_after,
         'import_a_read': FACTS['r2']['read_flag_import_a']})

# ══ R3: TM Editor → вкладка Import/Export → TMXImportThread ══════════════
from modules.tm_editor_dialog import TMEditorDialog  # noqa: E402
CRITICAL_MSGS.clear()
ed = TMEditorDialog(win, win.db_manager, win.log,
                    tm_id='tm5reconref', tm_name='TM5 Recon Ref TM')
mgr = ed._tm_manager
_open_queue.append(str(FIX_A))
mgr.import_tmx()
# TMXImportThread — QThread: ждём завершения до ~30 с
finished, waited = False, 0.0
import time as _time
while waited < 30.0:
    app.processEvents()
    th = getattr(mgr, 'import_thread', None)
    if th is not None and th.isFinished():
        finished = True
        break
    _time.sleep(0.05)
    waited += 0.05
app.processEvents()
imported_tm = tm_meta('imported')
imported_rows = tm_rows('imported') if imported_tm else []
tm5reconref_rows = tm_rows('tm5reconref')
FACTS['r3'] = {
    'thread_finished': finished, 'waited_s': round(waited, 2),
    'status_label': mgr.import_status.text(),
    'crit': list(CRITICAL_MSGS),
    'ref_rows_after_editor_import': len(tm5reconref_rows),
    'imported_tm_exists': imported_tm is not None,
    'imported_rows': len(imported_rows),
}
print('[tm5-recon] R3 facts:', json.dumps(FACTS['r3'], ensure_ascii=False)[:800],
      flush=True)
fail_msg = next((m for m in FACTS['r3']['crit'] if 'Import failed' in m or
                 'save_mode' in m), None)
verdict('R3 СИМПТОМ 4: TMXImportThread падает (Import failed/save_mode)',
        finished and fail_msg is not None,
        {'crit': FACTS['r3']['crit'], 'status': FACTS['r3']['status_label']})
verdict('R3 БД чистая после падения (0 записей, мусорной TM нет)',
        len(tm5reconref_rows) == 3 and imported_rows == [] and
        imported_tm is None,
        {'ref_rows': len(tm5reconref_rows), 'imported_rows': len(imported_rows),
         'imported_tm': FACTS['r3']['imported_tm_exists']})
ed.close()
app.processEvents()

# ══ R4: fixture B (теги EN/ru) → «Create new TM» → нормализация языков ═══
CRITICAL_MSGS.clear()
r4 = click_import_tmx_button(FIX_B, new_name='TM5 Recon Import B')
imp_b = tm_meta('tm5_recon_import_b')
if imp_b is None:
    imp_b = tm_meta('tm5reconimportb')
rows_b = tm_rows(imp_b['tm_id']) if imp_b else []
FACTS['r4'] = {
    'button': r4, 'tm_found': imp_b is not None,
    'meta': {k: imp_b[k] for k in ('name', 'tm_id', 'source_lang', 'target_lang')}
            if imp_b else None,
    'rows': len(rows_b),
    'row_langs': sorted({(r['source_lang'], r['target_lang']) for r in rows_b}),
    'targets': sorted(r['target_text'] for r in rows_b),
}
print('[tm5-recon] R4 facts:', json.dumps(FACTS['r4'], ensure_ascii=False)[:600],
      flush=True)
verdict('R4 Import-create (теги EN/ru): 3 записи записаны',
        imp_b is not None and len(rows_b) == 3,
        {'rows': len(rows_b)})
FACTS['r4_lang_norm'] = FACTS['r4']['row_langs']
print('[tm5-recon] R4 языковые пары записей (нормализация EN→?):',
      FACTS['r4']['row_langs'], flush=True)

# ══ R5: повторный импорт fixture B → дублей нет (СИМПТОМ 3, эталон) ══════
CRITICAL_MSGS.clear()
rows_ref_before_reimport = tm_rows('tm5reconref')
r5 = click_import_tmx_button(FIX_B, mode_stub=_make_add_existing_stub('TM5 Recon Ref TM'))
rows_ref_reimport = tm_rows('tm5reconref')
usage_before = {r['id']: r['usage_count'] for r in rows_ref_before_reimport}
usage_after = {r['id']: r['usage_count'] for r in rows_ref_reimport}
FACTS['r5'] = {
    'button': r5,
    'rows_before': len(rows_ref_before_reimport),
    'rows_after': len(rows_ref_reimport),
    'same_ids': usage_before.keys() == usage_after.keys(),
    'usage_bumped': any(usage_after[k] > usage_before.get(k, 0)
                        for k in usage_after),
    'texts_ok': sorted(r['target_text'] for r in rows_ref_reimport) ==
                sorted([TGT1, TGT2, TGT3]),
}
print('[tm5-recon] R5 facts:', json.dumps(FACTS['r5'], ensure_ascii=False), flush=True)
verdict('R5 СИМПТОМ 3 (эталон): повторный импорт без дублей',
        len(rows_ref_reimport) == 3 and FACTS['r5']['same_ids'],
        {'before': FACTS['r5']['rows_before'],
         'after': FACTS['r5']['rows_after']})

# ══ R6: РУЧНАЯ активация Read (механизм галки) → совпадение появляется ═══
imp_a_id = imp_a['tm_id']
imp_a_db_id = imp_a['id']
# Тот же механизм, что у клика по галке Read (Supervertaler.py:11127-11138):
win.tm_metadata_mgr.activate_tm(imp_a_db_id, proj.id)
win.invalidate_translation_cache(smart_invalidation=False)
app.processEvents()

m_r6 = editor_match(SRC4)
inst_r6 = instant_match(seg1)
snap_before = proj.tm_settings.get('activated_tm_ids')
FACTS['r6'] = {
    'panel': m_r6, 'instant': inst_r6, 'snapshot_before': snap_before,
    'read_flag': read_flag(imp_a_id),
}
# Текст найденного перевода сверяем с TMX-парой (SRC4 уникален для A)
panel_target_ok = any(t['target'] == TGT4 for t in m_r6)
verdict('R6 ручная Read: поиск Editor находит пару (текст сверен)',
        len(m_r6) >= 1 and panel_target_ok,
        {'panel': m_r6})
print('[tm5-recon] R6 instant-путь на несвежем снапшоте (измерение, '
      'общий нюанс и для +Create New TM):', inst_r6,
      'snapshot=', snap_before, flush=True)

# Синхронизация снапшота — так делает сохранение проекта (28251-28254):
proj.tm_settings['activated_tm_ids'] = \
    win.tm_metadata_mgr.get_active_tm_ids(proj.id)
inst_r6b = instant_match(seg1)
FACTS['r6']['instant_after_sync'] = inst_r6b
verdict('R6 после синхронизации снапшота: точное совпадение найдено',
        inst_r6b is True,
        {'instant_before': inst_r6, 'instant_after': inst_r6b})

# Итоговый JSON
FACTS['verdicts'] = [{'name': n, 'ok': ok, 'detail': d} for n, ok, d in RESULTS]
out_json = OUT / 'tm5_recon_before.json'
out_json.write_text(json.dumps(FACTS, ensure_ascii=False, indent=1),
                    encoding='utf-8')
print(f'[tm5-recon] facts → {out_json}', flush=True)

n_conf = sum(1 for _, ok, _ in RESULTS if ok)
print(f'[tm5-recon] RESULT: {n_conf}/{len(RESULTS)} reproduced/confirmed', flush=True)
app.processEvents()
os._exit(0)   # Qt-teardown может сегфолтить — завершаем после вердикта
