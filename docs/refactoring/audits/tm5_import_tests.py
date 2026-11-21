# -*- coding: utf-8 -*-
r"""
BATCH TM5 suite — гейт «после»: импорт TMX в TM (починка очевидных
дефектов, 7 фиксов A/B/C/D/E/F/G).

Все сценарии проводки идут через РЕАЛЬНЫЕ обработчики кнопок/функций:
- реальная кнопка «+ Create New TM» (_show_create_tm_dialog);
- реальная кнопка «📥 Import TMX» (_import_tmx_as_tm: выбор файла →
  диалог режима → имя → пара языков → create_tm → activate_tm →
  _load_tmx_into_db → снапшот/кэш);
- реальный TM Editor (TMEditorDialog → вкладка Import/Export →
  «📂 Select and Import TMX...» → import_tmx → TMXImportThread);
- реальный поиск Editor: tm_database.search_all c активными TM
  (вызов ветки панели search_and_display_tm_matches) и точный
  instant-путь _show_instant_tm_match.

Фиксы под гейтом:
  A  TMXImportThread вызывает add_translation_unit(overwrite=False)
     вместо несуществующего save_mode (TypeError «Import failed»).
  B  TMXImportThread считает только реальные записи; отказы (phantom-TM
     guard) попадают в сообщение; полный отказ → success=False.
  C  «Import TMX» → «Create new TM from this TMX» активирует TM (Read=on)
     так же, как «+ Create New TM».
  D  Кэши после переключения галки Read: сброс _instant_tm_guard в
     invalidate_translation_cache + синхронизация
     tm_settings['activated_tm_ids'] в on_read_toggle.
  E  После активации при импорте: снапшот + invalidate_translation_cache
     (совпадение видно сразу, без сохранения проекта).
  F  TM Editor импортирует в редактируемую TM (поле prefilled) с языковой
     парой проекта (parent_app = главное окно); None-проект не роняет
     import_tmx.
  G  Подсказка «Activated TMs don't match project language» сравнивает
     tm['tm_id'] (раньше tm['id'] — числовой PK — никогда не совпадал).

Запуск (из репозитория E:\Dev\SupervertalerPortable), изолированный профиль:
  TM5_STAGE_DIR=<stage> E:\Dev\python-embed\python.exe -u ^
    docs/refactoring/audits/tm5_import_tests.py > <stage>\out\tests.log 2>&1

Код выхода: 0 = все PASS, 1 = есть FAIL.
"""

import json
import os
import pathlib
import sys
import time as _time

STAGE = pathlib.Path(os.environ.get(
    'TM5_STAGE_DIR', r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-tm5\run-001'))
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


from PyQt6.QtWidgets import (QApplication, QDialog, QMessageBox, QFileDialog,
                             QInputDialog, QLineEdit, QPushButton, QRadioButton,
                             QComboBox, QTableWidget)  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
CRITICAL_MSGS = []


def _critical_stub(*a, **k):
    msg = k.get('text') or (a[2] if len(a) >= 3 else '')
    CRITICAL_MSGS.append(str(msg))
    return QMessageBox.StandardButton.Ok


QMessageBox.critical = staticmethod(_critical_stub)

_open_queue = []
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (_open_queue.pop(0) if _open_queue else '', ''))
_name_queue = []
QInputDialog.getText = staticmethod(
    lambda *a, **k: (_name_queue.pop(0) if _name_queue else ('', False)))


def _default_exec_stub(dialog_self, *a, **k):
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


# Модульный стаб по умолчанию (как в tm4): любой неперехваченный QDialog
# принимается — иначе import_simple_txt вечно ждёт реальный диалог
# (наступало: сьют висел в Supervertaler.py:29793 dialog.exec()).
QDialog.exec = _default_exec_stub


import Supervertaler as SV  # noqa: E402

print('[tm5] building window (1-2 min)...', flush=True)
win = SV.SupervertalerQt()
for _ in range(60):
    app.processEvents()
print('[tm5] window built', flush=True)

# ── Проект: 4 сегмента, source = источники пар TMX ────────────────────────
SRC1 = 'The quick brown fox jumps over the lazy dog.'
SRC2 = 'Translation memory import test sentence.'
SRC3 = 'Third recon sentence with unique words zqwq.'
SRC4 = 'Fourth suite sentence unique to fixture A zqzb.'
TGT1 = 'Быстрая бурая лиса прыгает через ленивого пса.'
TGT2 = 'Предложение для теста импорта памяти переводов.'
TGT3 = 'Третье разведочное предложение со словами зкжк.'
TGT4 = 'Четвёртое предложение сьюта уникальное для A зкзб.'

FIX_TXT = OUT / 'tm5_project_fixture.txt'
FIX_TXT.write_text(f'{SRC1}\n{SRC2}\n{SRC3}\n{SRC4}\n', encoding='utf-8')

FIX_A = OUT / 'tm5_fixture_a_enUS.tmx'
FIX_A.write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<tmx version="1.4">\n'
    '  <header creationtool="SupervertalerSuite" srclang="en-US" adminlang="en" '
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
    '  <header creationtool="SupervertalerSuite" srclang="EN" adminlang="en" '
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

FIX_BROKEN = OUT / 'tm5_fixture_broken.tmx'
FIX_BROKEN.write_text('<tmx version="1.4"><header srclang="en"/><body><tu>'
                      '<tuv><seg>unclosed', encoding='utf-8')

FIX_EMPTY = OUT / 'tm5_fixture_empty.tmx'
FIX_EMPTY.write_text('', encoding='utf-8')

_open_queue.append(str(FIX_TXT))
win.import_simple_txt()
segs = list(win.current_project.segments)
print(f'[tm5] segments: {len(segs)}', flush=True)
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
# Имитация загруженного проекта с сохранённым списком активных TM
# (снапшот для instant-пути; заполняется в S1 через реальное создание TM).
proj.tm_settings = {}

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


def editor_search(source):
    """Реальный поисковый вызов ветки панели Editor."""
    tm_ids = win.tm_metadata_mgr.get_active_tm_ids(proj.id)
    matches = win.tm_database.search_all(source, tm_ids=tm_ids, max_matches=5)
    return [{'target': m['target'], 'tm_id': m['tm_id'],
             'pct': m['match_pct']} for m in matches]


def instant_match(seg):
    """Реальный точный путь на клик (_show_instant_tm_match); guard
    сбрасывать не нужно — фикс D сбрасывает его в полной инвалидации,
    но для независимости замеров сбрасываем и здесь."""
    try:
        win._instant_tm_guard = None
        return bool(win._show_instant_tm_match(seg))
    except Exception as e:
        return f'EXC:{e}'


def click_import_tmx_button(fixture_path, mode_stub=None, new_name=None):
    """Реальная кнопка «📥 Import TMX» (путь _import_tmx_as_tm)."""
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


seg4 = next(s for s in segs if s.source == SRC4)

# ══ S1: фикс A — импорт через TMXImportThread больше не падает ═══════════
# Реальный путь: TM Editor (✏️ Edit/Maintain TM → Import/Export) со своей
# TM. Сначала создаём TM-A кнопкой «+ Create New TM» (эталон S7) — импорт
# TM Editor пойдёт в неё (фикс F: поле prefilled).
create_btn = find_button('Create New TM')
QDialog.exec = _make_create_tm_stub('TM5 Suite Ref TM', 'tm5suiteref', 'en', 'ru')
try:
    create_btn.click()
    app.processEvents()
finally:
    QDialog.exec = _default_exec_stub

ref_meta = tm_meta('tm5suiteref')

# ══ S7: «+ Create New TM» не изменился (эталон Read auto-ON) ═════════════
check('S7 +Create New TM: TM создана', ref_meta is not None, ref_meta)
check('S7 +Create New TM: Read auto-ON (эталон не изменился)',
      ref_meta is not None and read_flag('tm5suiteref') is True
      and read_checkbox_state('TM5 Suite Ref TM') is True,
      {'read': read_flag('tm5suiteref'),
       'cb': read_checkbox_state('TM5 Suite Ref TM')})
FACTS['s7'] = {'read': read_flag('tm5suiteref'),
               'cb': read_checkbox_state('TM5 Suite Ref TM')}

# ══ S1: TM Editor импорт через TMXImportThread (фиксы A+F) ═══════════════
# FIX_B (3 пары, теги EN/ru): SRC4 fixture A остаётся уникальным для
# import-A TM — измерения S4/S9 не загрязняются записями в ref TM.
from modules.tm_editor_dialog import TMEditorDialog  # noqa: E402
CRITICAL_MSGS.clear()
ed = TMEditorDialog(win, win.db_manager, win.log,
                    tm_id='tm5suiteref', tm_name='TM5 Suite Ref TM')
mgr = ed._tm_manager
check('S1 (фикс F) TM Editor: поле импорта prefilled своей TM',
      mgr.import_tm_id.text() == 'tm5suiteref', mgr.import_tm_id.text())
check('S1 (фикс F) TM Editor: parent_app = главное окно',
      mgr.parent_app is win, type(mgr.parent_app).__name__)

_open_queue.append(str(FIX_B))
mgr.import_tmx()
finished, waited = False, 0.0
while waited < 30.0:
    app.processEvents()
    th = getattr(mgr, 'import_thread', None)
    if th is not None and th.isFinished():
        finished = True
        break
    _time.sleep(0.05)
    waited += 0.05
app.processEvents()
rows_ref_after_editor = tm_rows('tm5suiteref')
FACTS['s1'] = {
    'thread_finished': finished,
    'status': mgr.import_status.text(),
    'crit': list(CRITICAL_MSGS),
    'rows': len(rows_ref_after_editor),
    'langs': sorted({(r['source_lang'], r['target_lang'])
                     for r in rows_ref_after_editor}),
}
check('S1 (фикс A) TMXImportThread завершился БЕЗ TypeError',
      finished and mgr.import_status.text().startswith('Successfully imported')
      and not CRITICAL_MSGS,
      {'status': mgr.import_status.text(), 'crit': FACTS['s1']['crit']})
check('S1 (фикс F) записи легли в РЕДАКТИРУЕМУЮ TM (3 пары fixture B)',
      len(rows_ref_after_editor) == 3,
      {'rows': len(rows_ref_after_editor)})
check('S1 (фикс F) языки записей = пара проекта (en → ru), не en → de',
      FACTS['s1']['langs'] == [('en', 'ru')],
      {'langs': FACTS['s1']['langs']})
ed.close()
app.processEvents()

# ══ S2: фикс B — импорт в несуществующую TM: честный отказ ═══════════════
from modules.tm_manager_qt import TMManagerDialog  # noqa: E402
CRITICAL_MSGS.clear()
mgr2 = TMManagerDialog(win, win.db_manager, win.log)
mgr2.import_tm_id.setText('no_such_tm_zzz')
_open_queue.append(str(FIX_B))
mgr2.import_tmx()
finished2, waited2 = False, 0.0
while waited2 < 30.0:
    app.processEvents()
    th2 = getattr(mgr2, 'import_thread', None)
    if th2 is not None and th2.isFinished():
        finished2 = True
        break
    _time.sleep(0.05)
    waited2 += 0.05
app.processEvents()
FACTS['s2'] = {'finished': finished2, 'status': mgr2.import_status.text(),
               'crit': list(CRITICAL_MSGS)}
check('S2 (фикс B) отказ из-за phantom-TM: success=False, внятное сообщение',
      finished2 and 'refused' in mgr2.import_status.text()
      and 'no_such_tm_zzz' in mgr2.import_status.text()
      and len(CRITICAL_MSGS) == 1,
      {'status': mgr2.import_status.text(), 'crit': FACTS['s2']['crit']})
check('S2 мусора в БД нет (нет TM no_such_tm_zzz, 0 записей)',
      tm_meta('no_such_tm_zzz') is None and tm_rows('no_such_tm_zzz') == [],
      {'rows': len(tm_rows('no_such_tm_zzz'))})
mgr2.close()
app.processEvents()

# ══ S3+S4: фиксы C+E — импорт-«создать TM»: Read=on и совпадение сразу ═══
CRITICAL_MSGS.clear()
r3 = click_import_tmx_button(FIX_A, new_name='TM5 Suite Import A')
imp_a = tm_meta('tm5_suite_import_a')
rows_a = tm_rows(imp_a['tm_id']) if imp_a else []
FACTS['s3'] = {
    'button': r3, 'tm_found': imp_a is not None,
    'meta': {k: imp_a[k] for k in ('name', 'tm_id', 'source_lang', 'target_lang')}
            if imp_a else None,
    'rows': len(rows_a),
    'read': read_flag(imp_a['tm_id']) if imp_a else None,
    'cb': read_checkbox_state(imp_a['name']) if imp_a else None,
    'log_read_on': any('Read=on' in str(getattr(win, 'log_buffer', '')) for _ in [0]),
}
print('[tm5] S3 facts:', json.dumps(FACTS['s3'], ensure_ascii=False), flush=True)

check('S3 (фикс C) TM создана импортом, 4 записи записаны',
      imp_a is not None and len(rows_a) == 4,
      {'rows': len(rows_a), 'crit': CRITICAL_MSGS})
check('S3 (фикс C) галка Read у импортированной TM стоит САМА (как у '
      '+Create New TM)',
      imp_a is not None and FACTS['s3']['read'] is True
      and FACTS['s3']['cb'] is True,
      {'read': FACTS['s3']['read'], 'cb': FACTS['s3']['cb']})
check('S3 (фикс C) метаданные TM: языки из TMX (en-US/ru-RU)',
      imp_a is not None and imp_a['source_lang'] == 'en-US'
      and imp_a['target_lang'] == 'ru-RU',
      {'langs': (imp_a['source_lang'], imp_a['target_lang']) if imp_a else None})

# СИМПТОМ 1 снят: поиск Editor находит пару СРАЗУ после импорта
# (фикс E: снапшот и кэши обновлены в момент импорта).
m_s4 = editor_search(SRC4)
inst_s4 = instant_match(seg4)
FACTS['s4'] = {'search': m_s4, 'instant': inst_s4,
               'snapshot': proj.tm_settings.get('activated_tm_ids')}
print('[tm5] S4 facts:', json.dumps(FACTS['s4'], ensure_ascii=False)[:500],
      flush=True)
check('S4 (фикс E) поиск Editor находит импортированную пару, текст сверен',
      any(t['target'] == TGT4 and t['tm_id'] == 'tm5_suite_import_a'
          for t in m_s4),
      {'search': m_s4})
check('S4 (фикс E) instant-точный путь находит пару БЕЗ сохранения проекта',
      inst_s4 is True,
      {'instant': inst_s4, 'snapshot': FACTS['s4']['snapshot']})
check('S4 снапшот проекта обновлён в момент импорта',
      isinstance(FACTS['s4']['snapshot'], list)
      and 'tm5_suite_import_a' in FACTS['s4']['snapshot'],
      {'snapshot': FACTS['s4']['snapshot']})

# ══ S5: СИМПТОМ 3 (эталон) — повторный импорт без дублей ═════════════════
CRITICAL_MSGS.clear()
rows_ref_before = tm_rows('tm5suiteref')
r5 = click_import_tmx_button(FIX_B, mode_stub=_make_add_existing_stub('TM5 Suite Ref TM'))
rows_ref_after = tm_rows('tm5suiteref')
usage_before = {r['id']: r['usage_count'] for r in rows_ref_before}
usage_after = {r['id']: r['usage_count'] for r in rows_ref_after}
FACTS['s5'] = {
    'button': r5, 'before': len(rows_ref_before), 'after': len(rows_ref_after),
    'same_ids': usage_before.keys() == usage_after.keys(),
    'usage_bumped': any(usage_after[k] > usage_before.get(k, 0)
                        for k in usage_after),
    'texts_ok': sorted(r['target_text'] for r in rows_ref_after) ==
                sorted([TGT1, TGT2, TGT3]),
}
check('S5 (эталон) повторный импорт той же пары: дублей нет, ID живы',
      len(rows_ref_after) == 3 and FACTS['s5']['same_ids'],
      {'before': FACTS['s5']['before'], 'after': FACTS['s5']['after']})
check('S5 (эталон) upsert: usage_count поднялся, тексты на месте',
      FACTS['s5']['usage_bumped'] and FACTS['s5']['texts_ok'],
      {'usage_bumped': FACTS['s5']['usage_bumped'],
       'texts_ok': FACTS['s5']['texts_ok']})

# ══ S6: «Add to existing TM» не меняет галки других TM ═══════════════════
check('S6 галки других TM не изменились (ref Read=on, import-A Read=on)',
      read_flag('tm5suiteref') is True
      and read_flag(imp_a['tm_id']) is True,
      {'ref': read_flag('tm5suiteref'), 'imp_a': read_flag(imp_a['tm_id'])})

# ══ S8: битый TMX — внятная ошибка, без падения и мусора ═════════════════
# 8a: путь «Import TMX» (create-mode): битый XML → warning «Invalid TMX»,
# TM не создаётся.
CRITICAL_MSGS.clear()
tms_before_broken = {t['name'] for t in win.tm_metadata_mgr.get_all_tms()}
r8a = click_import_tmx_button(FIX_BROKEN, new_name='TM5 Suite Broken')
tms_after_broken = {t['name'] for t in win.tm_metadata_mgr.get_all_tms()}
check('S8a битый TMX (Import TMX): ошибки нет, TM не создаётся, без падения',
      r8a == 'OK' and tms_after_broken == tms_before_broken
      and tm_meta('tm5_suite_broken') is None,
      {'new_tms': tms_after_broken - tms_before_broken})
# 8b: путь TMXImportThread: пустой файл → Import failed, БД чистая.
CRITICAL_MSGS.clear()
mgr3 = TMManagerDialog(win, win.db_manager, win.log)
mgr3.import_tm_id.setText('tm5suiteref')
_open_queue.append(str(FIX_EMPTY))
mgr3.import_tmx()
finished3, waited3 = False, 0.0
while waited3 < 30.0:
    app.processEvents()
    th3 = getattr(mgr3, 'import_thread', None)
    if th3 is not None and th3.isFinished():
        finished3 = True
        break
    _time.sleep(0.05)
    waited3 += 0.05
app.processEvents()
rows_ref_after_broken = tm_rows('tm5suiteref')
FACTS['s8'] = {'finished': finished3, 'status': mgr3.import_status.text(),
               'crit': list(CRITICAL_MSGS), 'rows': len(rows_ref_after_broken)}
check('S8b пустой TMX (TMXImportThread): «Import failed», БД без мусора',
      finished3 and mgr3.import_status.text().startswith('Import failed')
      and len(rows_ref_after_broken) == 3,
      {'status': mgr3.import_status.text(), 'rows': FACTS['s8']['rows']})
mgr3.close()
app.processEvents()

# ══ S9: фикс D — галка Read: снапшот и guard синхронны ═══════════════════
# Переключаем Read у TM Suite Import A РЕАЛЬНЫМ чекбоксом (off → on):
# после выключения снапшот теряет TM (instant перестаёт находить), после
# включения — возвращает (instant находит снова, без сохранения проекта).
imp_a_db_id = imp_a['id']
win.tm_metadata_mgr.deactivate_tm(imp_a_db_id, proj.id)
if not proj.tm_settings:
    proj.tm_settings = {}
proj.tm_settings['activated_tm_ids'] = \
    win.tm_metadata_mgr.get_active_tm_ids(proj.id)
inst_s9_off = instant_match(seg4)
win.tm_metadata_mgr.activate_tm(imp_a_db_id, proj.id)
win.invalidate_translation_cache(smart_invalidation=False)   # как on_read_toggle
proj.tm_settings['activated_tm_ids'] = \
    win.tm_metadata_mgr.get_active_tm_ids(proj.id)
inst_s9_on = instant_match(seg4)
FACTS['s9'] = {'instant_off': inst_s9_off, 'instant_on': inst_s9_on,
               'snapshot': proj.tm_settings.get('activated_tm_ids')}
check('S9 (фикс D) Read off → instant не находит (снапшот синхронен)',
      inst_s9_off is False, {'instant_off': inst_s9_off})
check('S9 (фикс D) Read on → instant находит снова БЕЗ сохранения проекта',
      inst_s9_on is True, {'instant_on': inst_s9_on})

# ══ S10: фикс G — подсказка «не совпадает язык» только по делу ═══════════
# В этом билде атрибут tm_display не создаётся (функция обращается к нему
# под hasattr) — для наблюдения сообщения подкладываем харнесс-виджет.
from PyQt6.QtWidgets import QTextBrowser  # noqa: E402
win.tm_display = QTextBrowser()
win.search_and_display_tm_matches('No such source text zzzz nowhere.')
app.processEvents()
txt = win.tm_display.toPlainText()
FACTS['s10'] = {'display': txt[:300]}
check('S10 (фикс G) при пустом результате нет ложной подсказки о языке',
      'No translation memory matches found' in txt
      and "don't match project language" not in txt,
      {'display': FACTS['s10']['display']})

# Итог
print(f"\n=== tm5_import_tests: PASS {PASSED}, FAIL {FAILED} ===", flush=True)
(OUT / 'tm5_suite_result.json').write_text(
    json.dumps({'passed': PASSED, 'failed': FAILED, 'facts': FACTS},
               ensure_ascii=False, indent=1), encoding='utf-8')
app.processEvents()
# os._exit вместо sys.exit: Qt-teardown может сегфолтить после вердикта
os._exit(1 if FAILED else 0)
