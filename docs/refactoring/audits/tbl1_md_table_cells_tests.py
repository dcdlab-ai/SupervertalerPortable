# -*- coding: utf-8 -*-
"""Headless-тесты Batch TBL1.1: modules/md_table_cells.py + нормализация
table_info в Segment.from_dict (modules/models.py).

Без Qt. Покрытие (по промпту): split_table_row (обычная строка, пустые ячейки,
«\|», «\\|», строка без внешних «|», строка на «\|», не-таблица, одна ячейка,
лишние пробелы); is_table_separator; find_table_blocks (таблица с заголовком,
два блока через абзац, блок без разделителя, разделитель не на 2-й позиции,
«разорванная» строка с разным числом ячеек, таблица в начале и в конце файла,
пустой список); build_*; круг parse→build (нормализованный ввод — байт-в-байт,
ненормализованный — нормализация + идемпотентность); фикстуры из образцов
PyMuPDF4LLM/docling; models.from_dict (список → кортеж, None, неверная длина,
без table_info).

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u docs/refactoring/audits/tbl1_md_table_cells_tests.py
"""
import faulthandler
import json
import os
import pathlib
import sys

faulthandler.dump_traceback_later(60, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-tbl11\tests\run-tbl11')
ISO = STAGE / 'iso'
ISO.mkdir(parents=True, exist_ok=True)
(ISO / 'tmp').mkdir(parents=True, exist_ok=True)

os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'AppData' / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

sys.path.insert(0, REPO)

from modules.md_table_cells import (  # noqa: E402
    TableBlock,
    build_table_row,
    build_table_separator,
    escape_cell,
    find_table_blocks,
    is_table_separator,
    split_table_row,
    unescape_cell,
)

FIXTURES = pathlib.Path(REPO) / 'docs' / 'refactoring' / 'audits' / 'fixtures' / 'md_tables'

PASSED = 0
FAILED = 0


def check(name, cond, detail=''):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f'PASS {name}', flush=True)
    else:
        FAILED += 1
        print(f'FAIL {name} {detail}', flush=True)


def expect_raises(exc_type, func, *args):
    try:
        func(*args)
        return False
    except exc_type:
        return True


def read_lines(name):
    return (FIXTURES / name).read_text(encoding='utf-8').splitlines()


# ── 1. split_table_row ───────────────────────────────────────────────────────
check('split.basic', split_table_row('| a | b |') == ['a', 'b'])
check('split.empty_cells', split_table_row('| a | | b |') == ['a', '', 'b'])
check('split.bold_header', split_table_row('|**A**|**B**|') == ['**A**', '**B**'])
check('split.one_cell', split_table_row('| one cell |') == ['one cell'])
check('split.extra_spaces', split_table_row('|  a  |  b  |  ') == ['a', 'b'])
check('split.escaped_pipe', split_table_row('| a \\| b | c |') == ['a | b', 'c'])
# «\\|» = НЕэкранированный «|» → разделитель; слэши остаются в тексте как есть
check('split.backslash_before_pipe',
      split_table_row('| a \\\\| b |') == ['a \\\\', 'b'])
# одиночный слэш не перед «|» — литерал
check('split.lone_backslash', split_table_row('| a \\ b |') == ['a \\ b'])
# строка, оканчивающаяся на «\|» — не таблица
check('split.ends_on_escaped_pipe', split_table_row('| a \\|') is None)
check('split.no_pipes', split_table_row('plain text') is None)
check('split.no_leading', split_table_row('a | b |') is None)
check('split.no_trailing', split_table_row('| a | b') is None)
check('split.too_short', split_table_row('|') is None)
check('split.empty_string', split_table_row('') is None)
check('split.only_pipes', split_table_row('||') == [''])
# чётность: три слэша перед «|» → pipe экранирован, в ячейке два слэша + «|»
check('split.triple_backslash_escaped',
      split_table_row('| a \\\\\\| b |') == ['a \\\\| b'])

# ── 2. is_table_separator ────────────────────────────────────────────────────
check('sep.plain', is_table_separator('|---|---|') is True)
check('sep.aligned', is_table_separator('| :---: | ---: |') is True)
check('sep.one_col', is_table_separator('|---|') is True)
check('sep.long_dashes', is_table_separator('|------------|------|') is True)
check('sep.no_pipes', is_table_separator('---') is False)
check('sep.text_cells', is_table_separator('| a | b |') is False)
check('sep.bad_cell', is_table_separator('|--x|') is False)
check('sep.not_table', is_table_separator('|- a') is False)

# ── 3. escape_cell / unescape_cell ──────────────────────────────────────────
check('esc.pipe_newline', escape_cell('a|b') == 'a\\|b')
check('esc.lf', escape_cell('c\nd') == 'c d')
check('esc.crlf', escape_cell('c\r\nd') == 'c d')
check('esc.cr', escape_cell('c\rd') == 'c d')
check('esc.br_kept', escape_cell('the<br>bridge.') == 'the<br>bridge.')
check('unesc.pipe', unescape_cell('a\\|b') == 'a|b')
check('unesc.double', unescape_cell('a\\\\|b') == 'a\\\\|b')
check('unesc.none', unescape_cell('no pipes') == 'no pipes')

# ── 4. build_table_row / build_table_separator ──────────────────────────────
check('build.basic', build_table_row(['a', 'b']) == '| a | b |')
check('build.empty', build_table_row(['']) == '| |')
check('build.mixed', build_table_row(['a', '', 'b']) == '| a | | b |')
check('build.pipe_escaped', build_table_row(['a|b', 'c']) == '| a\\|b | c |')
check('build.lf_to_space', build_table_row(['c\nd']) == '| c d |')
check('build.br_kept', build_table_row(['the<br>bridge.']) == '| the<br>bridge. |')
check('sepbuild.2', build_table_separator(2) == '|---|---|')
check('sepbuild.3', build_table_separator(3) == '|---|---|---|')
check('sepbuild.0_raises', expect_raises(ValueError, build_table_separator, 0))
check('sepbuild.1', build_table_separator(1) == '|---|')

# ── 5. Круг parse→build ─────────────────────────────────────────────────────
# 5a. Нормализованный ввод (выход build_*): байт-в-байт.
normalized_rows = [
    '| a | b |',
    '| |',
    '| a | | b |',
    '| a\\|b | c |',
    '| the<br>bridge. | Start in a march column. |',
    '| a \\ b |',           # слэш внутри ячейки
    '| trailing\\ |',        # слэш на краю ячейки (не перед «|»)
]
for row in normalized_rows:
    check(f'circle.normalized {row!r}',
          build_table_row(split_table_row(row)) == row)
# parse→build→parse: ячейки без CR/LF восстанавливаются точно
cells_sets = [
    ['a', 'b'],
    [''],
    ['a', '', 'b'],
    ['a|b', 'c'],
    ['a \\ b', 'trailing\\'],
    ['**A**', '**B**'],
    [''],
]
for cells in cells_sets:
    check(f'circle.parse(build({cells!r}))',
          split_table_row(build_table_row(cells)) == cells)
# идемпотентность: build(parse(build(parse(x)))) == build(parse(x))
for row in normalized_rows:
    once = build_table_row(split_table_row(row))
    check(f'circle.idempotent {row!r}',
          build_table_row(split_table_row(once)) == once)

# 5b. Ненормализованный ввод: равенство после нормализации.
non_normalized = [
    '|a|b|',                 # без пробелов
    '|  a  |  b  |  ',       # лишние пробелы, хвостовые пробелы
    '| a  | |  b |',         # пустая ячейка с лишними пробелами
]
for row in non_normalized:
    norm = build_table_row(split_table_row(row))
    check(f'normalize.then_stable {row!r}',
          build_table_row(split_table_row(norm)) == norm)
check('normalize.spaces', build_table_row(split_table_row('|  a  |  b  |  ')) == '| a | b |')
# выравнивание разделителя не сохраняется: регенерация всегда «|---|»
check('normalize.alignment_dropped',
      is_table_separator('| :---: | ---: |') and build_table_separator(2) == '|---|---|')

# ── 6. find_table_blocks ────────────────────────────────────────────────────
# 6a. Обычная таблица с заголовком.
lines = [
    '# Title',
    '',
    '| h1 | h2 |',
    '|---|---|',
    '| a | b |',
    '| c | d |',
    '',
    'tail paragraph',
]
blocks = find_table_blocks(lines)
check('blocks.one', len(blocks) == 1)
b = blocks[0]
check('blocks.indices', (b.start, b.end) == (2, 5))
check('blocks.header', b.header is True and b.separator_index == 3)
check('blocks.rows', b.rows == [['h1', 'h2'], ['a', 'b'], ['c', 'd']])
check('blocks.ncols', b.n_cols_header == 2 and b.warnings == [])

# 6b. Два блока, разделённые абзацем.
lines = [
    '| a | b |',
    '|---|---|',
    '| c | d |',
    '',
    'paragraph between',
    '',
    '| x | y | z |',
    '|---|---|---|',
    '| e | f | g |',
]
blocks = find_table_blocks(lines)
check('blocks.two', len(blocks) == 2)
check('blocks.two_first', (blocks[0].start, blocks[0].end) == (0, 2)
      and blocks[0].header and blocks[0].rows == [['a', 'b'], ['c', 'd']])
check('blocks.two_second', (blocks[1].start, blocks[1].end) == (6, 8)
      and blocks[1].header and blocks[1].n_cols_header == 3)

# 6c. Блок из одной строки без разделителя.
blocks = find_table_blocks(['| single |'])
check('blocks.single_no_sep', len(blocks) == 1 and blocks[0].header is False
      and blocks[0].separator_index is None and blocks[0].rows == [['single']]
      and blocks[0].n_cols_header == 1)

# 6d. Разделитель не на 2-й позиции блока — отбросить + предупреждение.
lines = [
    '| a | b |',
    '|---|---|',
    '| c | d |',
    '|---|---|',
    '| e | f |',
]
blocks = find_table_blocks(lines)
check('blocks.mid_sep.one', len(blocks) == 1)
b = blocks[0]
check('blocks.mid_sep.header', b.header is True and b.separator_index == 1)
check('blocks.mid_sep.rows', b.rows == [['a', 'b'], ['c', 'd'], ['e', 'f']])
check('blocks.mid_sep.warn', len(b.warnings) == 1 and '4' in b.warnings[0])

# 6e. Разделитель на ПЕРВОЙ позиции блока — тоже отбросить + предупреждение.
lines = [
    '|---|---|',
    '| a | b |',
]
blocks = find_table_blocks(lines)
b = blocks[0]
check('blocks.start_sep', len(blocks) == 1 and b.header is False
      and b.separator_index is None and b.rows == [['a', 'b']]
      and len(b.warnings) == 1 and '1' in b.warnings[0])

# 6f. «Разорванная» строка: разное число ячеек сохраняется как есть.
lines = [
    '| a | b | c |',
    '|---|---|---|',
    '| one | two |',
    '| three | four | five | six |',
]
blocks = find_table_blocks(lines)
b = blocks[0]
check('blocks.ragged.rows', b.rows == [['a', 'b', 'c'], ['one', 'two'],
                                       ['three', 'four', 'five', 'six']])
check('blocks.ragged.no_warn', b.warnings == [] and b.header is True)

# 6g. Таблица в начале и в конце файла.
lines = [
    '| top | row |',
    '|---|---|',
    '| a | b |',
    'middle text',
    '| bottom | row |',
    '|---|---|',
    '| c | d |',
]
blocks = find_table_blocks(lines)
check('blocks.first_and_last', len(blocks) == 2 and blocks[0].start == 0
      and blocks[0].header and blocks[1].end == 6 and blocks[1].header)

# 6h. Пустой список / нет таблиц.
check('blocks.empty', find_table_blocks([]) == [])
check('blocks.no_tables', find_table_blocks(['text', '', 'more']) == [])

# 6i. Разрыв блока пустой строкой между таблицами без абзаца.
blocks = find_table_blocks(['| a |', '', '| b |'])
check('blocks.blank_splits', len(blocks) == 2)

# ── 7. Фикстуры из образцов md_out ──────────────────────────────────────────
# 7a. PyMuPDF4LLM, таблица 1 (шапка + 3 строки данных, <br> сохраняется).
lines = read_lines('pymupdf4llm_table1_franco_scots.md')
blocks = find_table_blocks(lines)
check('fix.pymupdf1.count', len(blocks) == 1)
b = blocks[0]
check('fix.pymupdf1.geom', b.start == 6 and b.end == 10 and b.header
      and b.separator_index == 7 and b.n_cols_header == 2 and b.warnings == [])
check('fix.pymupdf1.rows', len(b.rows) == 4)  # шапка (rows[0]) + 3 строки данных
check('fix.pymupdf1.br',
      b.rows[1][0] == 'One Archers unit must deploy within 3” of the<br>bridge.')
check('fix.pymupdf1.bold', b.rows[0] == ['**FRANCO-SCOTS**', '**ENGLISH**'])

# 7b. PyMuPDF4LLM, таблица 2 (шапка + 6 строк данных, 3 столбца).
lines = read_lines('pymupdf4llm_table2_rule_tweak.md')
blocks = find_table_blocks(lines)
b = blocks[0]
check('fix.pymupdf2.geom', len(blocks) == 1 and b.start == 4 and b.end == 11
      and b.header and b.separator_index == 5 and b.n_cols_header == 3
      and len(b.rows) == 7 and b.warnings == [])  # шапка + 6 строк данных

# 7c. docling, таблица 1 (паддинги пробелами — обрезаются).
lines = read_lines('docling_table1_franco_scots.md')
blocks = find_table_blocks(lines)
b = blocks[0]
check('fix.docling1.geom', len(blocks) == 1 and b.start == 6 and b.end == 10
      and b.header and b.separator_index == 7 and b.n_cols_header == 2
      and len(b.rows) == 4 and b.warnings == [])  # шапка + 3 строки данных
check('fix.docling1.trim', b.rows[0] == ['FRANCO-SCOTS', 'ENGLISH'])

# 7d. docling, таблица 2 (длинный разделитель без двоеточий).
lines = read_lines('docling_table2_rule_tweak.md')
blocks = find_table_blocks(lines)
b = blocks[0]
check('fix.docling2.geom', len(blocks) == 1 and b.start == 3 and b.end == 10
      and b.header and b.separator_index == 4 and b.n_cols_header == 3
      and len(b.rows) == 7 and b.warnings == [])  # шапка + 6 строк данных

# 7e. Полный круг для всех строк фикстур (build(parse(x)) идемпотентен).
for name in ('pymupdf4llm_table1_franco_scots.md',
             'pymupdf4llm_table2_rule_tweak.md',
             'docling_table1_franco_scots.md',
             'docling_table2_rule_tweak.md'):
    lines = read_lines(name)
    stable = True
    for line in lines:
        if split_table_row(line) is None:
            continue
        once = build_table_row(split_table_row(line))
        if build_table_row(split_table_row(once)) != once:
            stable = False
    check(f'fix.circle {name}', stable)

# ── 8. models.Segment.from_dict: нормализация table_info ────────────────────
from modules.models import Segment  # noqa: E402

s = Segment.from_dict({'id': 1, 'source': 'src', 'target': 'tgt',
                       'is_table_cell': True,
                       'table_info': [0, 1, 2, True]})
check('model.list_to_tuple', s.table_info == (0, 1, 2, True)
      and isinstance(s.table_info, tuple))
s = Segment.from_dict({'id': 2, 'source': 's',
                       'table_info': (0, 1, 2, False)})
check('model.tuple_stays', s.table_info == (0, 1, 2, False)
      and isinstance(s.table_info, tuple))
s = Segment.from_dict({'id': 3, 'source': 's', 'table_info': None})
check('model.none_stays', s.table_info is None)
s = Segment.from_dict({'id': 4, 'source': 's', 'table_info': [0, 1]})
check('model.wrong_len_no_crash', s.table_info == [0, 1])
s = Segment.from_dict({'id': 5, 'source': 's'})
check('model.absent_default', s.table_info is None
      and s.is_table_cell is False)
# JSON-круг: tuple → list (json.dumps) → from_dict → tuple
s = Segment.from_dict({'id': 6, 'source': 's', 'is_table_cell': True,
                       'table_info': (1, 2, 3, True)})
round_trip = json.loads(json.dumps(s.to_dict()))
s2 = Segment.from_dict(round_trip)
check('model.json_roundtrip', s2.table_info == (1, 2, 3, True)
      and isinstance(s2.table_info, tuple))
# сегмент без table_info грузится как раньше (поле просто отсутствует)
s = Segment.from_dict({'id': 7, 'source': 'legacy', 'target': '',
                       'status': 'untranslated', 'paragraph_id': 3})
check('model.legacy_segment', s.source == 'legacy' and s.paragraph_id == 3
      and s.table_info is None)
# to_dict не менялся: кортеж уходит как есть (asdict сохраняет tuple)
d = s.to_dict()
check('model.to_dict_no_change', isinstance(d, dict) and 'table_info' in d)

# ── итог ────────────────────────────────────────────────────────────────────
print(f'\nTOTAL: {PASSED} passed / {FAILED} failed', flush=True)
sys.exit(1 if FAILED else 0)
