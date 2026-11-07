# -*- coding: utf-8 -*-
"""Пробник BATCH I2.0: влияние 'Start a new segment at every line break' на
импорт md и экспорт Tagged Text. Только чтение продукта; прогон на копии.

Кейс задаётся env I20_CASE: A (чекбокс выкл), B (вкл + правило False,
дефолт), C (вкл + правило True). Профиль и выход — env I20_ISO / I20_OUT.
Файл-импорт всегда построчный; правило действует только когда в ОДИН вызов
сегментера приходит многострочный текст (new_project -> segment_text,
Supervertaler.py:25973) — этот путь проверяется отдельно (i20_paste_probe.py).
"""
import faulthandler
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

faulthandler.dump_traceback_later(90, repeat=True, file=sys.stderr)

CASE = os.environ['I20_CASE']
REPO = r'E:\Dev\SupervertalerPortable'
ISO = pathlib.Path(os.environ['I20_ISO'])
OUT = pathlib.Path(os.environ['I20_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
MD = os.environ.get(
    'I20_MD',
    r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out\docling'
    r'\4164e8d8a0ef6c4df4142b7d9dc49a7f\Input.md')

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'AppData' / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
for d in ('Desktop', 'Documents', 'Downloads'):
    (ISO / d).mkdir(parents=True, exist_ok=True)
(ISO / 'tmp').mkdir(parents=True, exist_ok=True)

# Предзасев settings.json: состояние чекбокса импорта и правила line-break
# (явные флаги — имена кейсов произвольные).
sentences_on = os.environ.get('I20_SENT', '0') == '1'
line_breaks = os.environ.get('I20_LB', '0') == '1'
rules_seed = {"split_at_line_breaks": line_breaks,
              "use_builtin_rules": True,
              "extra_abbreviations": "",
              "rules": []}
# Настоящий settings.json: <data_root>\workbench\settings\settings.json
# (SettingsService._get_settings_dir; первый прогон засевал корень data root
# мимо — приложение его не читало, кейсы B/C шли с дефолтом).
settings_path = ISO / 'Supervertaler' / 'workbench' / 'settings' / 'settings.json'
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps({
    "api_keys": {}, "ui": {}, "features": {},
    "general": {
        "segmentation_rules": rules_seed,
        "last_import_sentence_segment": sentences_on,
    },
}, indent=2), encoding='utf-8')

sys.path.insert(0, REPO)

import PyQt6.QtWidgets as QW  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox  # noqa: E402

modal_log = []
QDialog.exec = lambda self, *a, **k: (
    modal_log.append(f"exec '{self.windowTitle()}'"),
    QDialog.DialogCode.Accepted)[1]
for name in ('information', 'warning', 'critical'):
    setattr(QMessageBox, name, staticmethod(
        lambda *a, **k: (modal_log.append(f"msg '{a[1] if len(a) > 1 else ''}'"),
                         QMessageBox.StandardButton.Ok)[1]))
save_queue = []
open_queue = [MD]
QFileDialog.getSaveFileName = staticmethod(
    lambda *a, **k: (save_queue.pop(0) if save_queue else '', ''))
QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **k: (open_queue.pop(0) if open_queue else '', ''))

import Supervertaler as SV  # noqa: E402
from modules.simple_segmenter import SimpleSegmenter  # noqa: E402
from modules.segmentation_rules import SegmentationRules  # noqa: E402

app = QApplication(sys.argv)
win = SV.SupervertalerQt()
import time as _t  # noqa: E402
for _ in range(30):
    app.processEvents()
    _t.sleep(0.05)

result = {'case': CASE, 'md': MD,
          'seed': {'last_import_sentence_segment': sentences_on,
                   'split_at_line_breaks': line_breaks}}

# Правило, как его видит приложение
loaded_rules = win._load_segmentation_rules()
result['loaded_rules'] = loaded_rules.to_dict()

# --- импорт md ---
win.import_simple_txt()
segs = list(win.current_project.segments)
result['n_segments'] = len(segs)
result['n_paragraph_groups'] = len({s.paragraph_id for s in segs})

md_lines = pathlib.Path(MD).read_text(encoding='utf-8').splitlines()
img_idx = [i + 1 for i, l in enumerate(md_lines) if l.lstrip().startswith('![')]
tbl_idx = [i + 1 for i, l in enumerate(md_lines) if l.lstrip().startswith('|')]
result['image_lines'] = img_idx
result['table_lines'] = tbl_idx

# картинки: изолированы ли как отдельные сегменты
img_isolated, img_merged = [], []
for lineno in img_idx:
    group = [s.source for s in segs if s.paragraph_id == lineno]
    if len(group) == 1 and group[0].strip() == md_lines[lineno - 1].strip():
        img_isolated.append(lineno)
    else:
        img_merged.append((lineno, [g[:60] for g in group]))
result['images_isolated'] = img_isolated
result['images_merged'] = img_merged

# таблицы: сколько сегментов на строку таблицы
tbl_detail = {}
for lineno in tbl_idx:
    group = [s.source for s in segs if s.paragraph_id == lineno]
    tbl_detail[lineno] = len(group)
result['table_segments_per_line'] = tbl_detail
result['table_lines_split'] = [k for k, v in tbl_detail.items() if v > 1]

# строки, склеенные/разрезанные: группы > 1 сегмента (разрез) и группы,
# чей склеенный текст != исходной строке (потеря при склейке)
split_groups = {pid: len([s for s in segs if s.paragraph_id == pid])
                for pid in {s.paragraph_id for s in segs}}
result['lines_split_into_multiple'] = sorted(k for k, v in split_groups.items() if v > 1)
result['split_examples'] = {
    pid: [s.source[:70] for s in segs if s.paragraph_id == pid]
    for pid in sorted(k for k, v in split_groups.items() if v > 1)[:4]}

# --- экспорт через хендлер (перевод = исходник) ---
for s in segs:
    s.target = s.source
out_gui = str(OUT / f'i20_{CASE}_gui.tagged.txt')
save_queue.append(out_gui)
win.export_tagged_txt()
result['gui_written'] = os.path.isfile(out_gui)

# --- CLI на том же md ---
out_cli = str(OUT / f'i20_{CASE}_cli.tagged.txt')
r = subprocess.run([sys.executable, '-m', 'modules.tagged_text', MD, out_cli],
                   cwd=REPO, capture_output=True)
result['cli_rc'] = r.returncode


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16] \
        if os.path.isfile(p) else None


result['sha_gui'] = sha(out_gui)
result['sha_cli'] = sha(out_cli)
result['gui_equals_cli'] = (result['sha_gui'] == result['sha_cli']
                            and result['sha_gui'] is not None)

# --- построчное сравнение текстов экспорта (если различаются) ---
if result['gui_written'] and not result['gui_equals_cli']:
    g = pathlib.Path(out_gui).read_bytes().decode('utf-16').split('\r\n')
    c = pathlib.Path(out_cli).read_bytes().decode('utf-16').split('\r\n')
    diffs = []
    for i, (a, b) in enumerate(zip(g, c)):
        if a != b:
            diffs.append({'line': i, 'gui': a[:90], 'cli': b[:90]})
        if len(diffs) >= 6:
            break
    result['gui_vs_cli_diff'] = diffs

# --- table_row ParaStyle ---
if result['gui_written']:
    text = pathlib.Path(out_gui).read_bytes().decode('utf-16')
    result['parastyle_table_row'] = text.count('<ParaStyle:table_row>')
    result['parastyle_p'] = text.count('<ParaStyle:p>')
    result['parastyle_img'] = text.count('<ParaStyle:img>')
    # строки таблиц в выходе: те же ли они, что в исходнике (после схлопывания пробелов)
    tr_lines = [l for l in text.split('\r\n') if l.startswith('<ParaStyle:table_row>')]
    result['table_row_output_sample'] = [l[:90] for l in tr_lines[:3]]
    # склейка: строки экспорта == исходным строкам?
    md_body = '\n'.join(win._collect_translated_lines(segs, True))
    result['rejoined_lines_equal_source'] = \
        [l.rstrip() for l in md_body.split('\n') if l.strip()] == \
        [l.rstrip() for l in md_lines if l.strip()]

# --- юнит: путь вставки (new_project -> segment_text, markdown=False) ---
whole = pathlib.Path(MD).read_text(encoding='utf-8')
for flag in (False, True):
    segm = SimpleSegmenter(SegmentationRules(split_at_line_breaks=flag))
    units = segm.segment_text(whole)
    img_units = [u for u in units if u.lstrip().startswith('![')]
    result[f'paste_linebreak_{flag}'] = {
        'n_segments': len(units),
        'image_only_units': len(img_units),
        'image_sample': img_units[0][:60] if img_units else None,
        'first_table_unit': next((u[:70] for u in units if '|' in u), None)}
    result['paste_linebreak_flags_measured'] = True

pathlib.Path(OUT / f'i20_{CASE}_result.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'I20-{CASE}: segments={result["n_segments"]} '
      f'gui==cli={result["gui_equals_cli"]} '
      f'table_row={result.get("parastyle_table_row")}', flush=True)
os._exit(0)
