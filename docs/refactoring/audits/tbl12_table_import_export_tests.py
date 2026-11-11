# -*- coding: utf-8 -*-
r"""Headless-сьют Batch TBL1.2: импорт и экспорт md-таблиц (ячейка = сегмент).

Без запуска GUI/приложения (без QApplication): модуль монолита импортируется
headless только ради _collect_translated_lines/_collect_source_lines —
они вызываются через стаб-self (staticmethod _group_export_items); всё
остальное — чистые модули (simple_import_builder, md_table_cells, models,
tagged_text.mdparse). Запускается с SUPERVERTALER_DATA_ROOT на изолированный
профиль; запись в пользовательские данные не выполняется (проект
сохраняется/загружается в памяти через to_dict/json/from_dict).

Секции:
  A — импорт обоих образцов Input.md (распознавание ВКЛ): число сегментов,
      все (table_idx, row, col), заголовки, разделители НЕ сегменты.
  B — галка ВЫКЛЮЧЕНА: прежнее поведение (строка = сегмент, «|---|» в тексте).
  C — круг «импорт → экспорт source без переводов» (fallback источника):
      таблицы структурно равны исходным; не-табличные строки байт-в-байт.
  D — перевод одной ячейки меняет только её.
  E — ячейка с «\|» (импорт -> «|» в тексте; экспорт -> «\|» обратно).
  F — пустая ячейка (сегмент с пустым source; экспорт «| |»).
  G — таблица без заголовка (экспорт БЕЗ разделителя).
  H — две таблицы подряд, разделённые абзацем (table_idx 0 и 1).
  I — сохранение/загрузка проекта (to_dict -> JSON -> from_dict):
      table_info остаётся кортежем, экспорт после загрузки тот же.
  J — Tagged Text из таблицы: table_row, разделитель отброшен.

Запуск из корня репозитория:
  E:\\Dev\\python-embed\\python.exe -u
  docs/refactoring/audits/tbl12_table_import_export_tests.py
"""
import faulthandler
import json
import os
import pathlib
import sys

faulthandler.dump_traceback_later(120, repeat=True, file=sys.stderr)

REPO = r'E:\Dev\SupervertalerPortable'
STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-tbl12\tests')
ISO = STAGE / 'iso'
OUT = STAGE / 'out'
OUT.mkdir(parents=True, exist_ok=True)
(ISO / 'tmp').mkdir(parents=True, exist_ok=True)

os.environ['USERPROFILE'] = str(ISO)
os.environ['APPDATA'] = str(ISO / 'AppData' / 'Roaming')
os.environ['LOCALAPPDATA'] = str(ISO / 'AppData' / 'Local')
os.environ['HOME'] = str(ISO)
os.environ['TEMP'] = str(ISO / 'tmp')
os.environ['TMP'] = str(ISO / 'tmp')
os.environ['SUPERVERTALER_DATA_ROOT'] = str(ISO)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

sys.path.insert(0, REPO)

from modules.models import Segment, Project  # noqa: E402
from modules.md_table_cells import (find_table_blocks, split_table_row,  # noqa: E402
                                    build_table_separator)
from modules.simple_import_builder import build_segments_from_lines  # noqa: E402

MD_DOCLING = (r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out\docling'
              r'\4164e8d8a0ef6c4df4142b7d9dc49a7f\Input.md')
MD_PYMUPDF = (r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out'
              r'\PyMuPDF4LLM\pymupdf4llm_gui_x0bf0ve2\Input.md')

_N = [0]
_FAILS = [0]


def check(name, cond, detail=''):
    _N[0] += 1
    if not cond:
        _FAILS[0] += 1
    print(f'{"PASS" if cond else "FAIL"} {name}'
          + ('' if cond else f'  DETAIL: {detail}'), flush=True)


# ── Экспортные функции монолита через стаб-self (без GUI) ────────────────
import Supervertaler  # headless: без QApplication, окон не создаёт  # noqa: E402


class _ExportStub:
    _group_export_items = Supervertaler.SupervertalerQt.__dict__['_group_export_items']


_CTL = Supervertaler.SupervertalerQt._collect_translated_lines
_CSL = Supervertaler.SupervertalerQt._collect_source_lines


def export_lines(segments, use_source_fallback=True):
    stub = _ExportStub()
    return _CTL(stub, list(segments), use_source_fallback)


def source_lines(segments):
    stub = _ExportStub()
    return _CSL(stub, list(segments))


def read_lines(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.readlines()


def import_md(path, recognize=True):
    return build_segments_from_lines(read_lines(path), None,
                                     recognize_tables=recognize)


# ══════════════════ A. Импорт образцов (распознавание ВКЛ) ══════════════
EXPECT = {'docling': 60, 'pymupdf': 63}  # сегментов всего (измерено и сверено с блоками)
for label, path in (('docling', MD_DOCLING), ('pymupdf', MD_PYMUPDF)):
    raw = read_lines(path)
    blocks = find_table_blocks(raw)
    segs = import_md(path)
    cells = [s for s in segs if s.is_table_cell]
    check(f'A1 {label}: число сегментов', len(segs) == EXPECT[label],
          (len(segs), EXPECT[label]))
    check(f'A2 {label}: число ячеек = сумме ячеек блоков',
          len(cells) == sum(len(r) for b in blocks for r in b.rows),
          (len(cells), sum(len(r) for b in blocks for r in b.rows)))
    check(f'A3 {label}: ни одного сегмента с «|---|»',
          not any('|---' in s.source for s in segs),
          [s.source for s in segs if '|---' in s.source][:3])
    check(f'A4 {label}: ни одного не-табличного сегмента с «|»',
          not any('|' in s.source for s in segs if not s.is_table_cell))
    # все (table_idx, row, col) как в блоках исходника
    expected_tis = []
    for t_idx, b in enumerate(blocks):
        for r_idx, row in enumerate(b.rows):
            for c_idx in range(len(row)):
                expected_tis.append((t_idx, r_idx, c_idx, b.header and r_idx == 0))
    got_tis = [s.table_info for s in cells]
    check(f'A5 {label}: все table_info совпадают с блоками',
          got_tis == expected_tis, (len(got_tis), len(expected_tis)))
    check(f'A6 {label}: type/is_table_cell у ячеек',
          all(s.type == 'table_cell' for s in cells)
          and all(s.is_table_cell for s in cells))
    check(f'A7 {label}: тексты ячеек = ячейкам исходника (split_table_row)',
          [s.source for s in cells]
          == [c for b in blocks for row in b.rows for c in row])
    check(f'A8 {label}: ячейки одной md-строки делят paragraph_id',
          all(len({s.paragraph_id for s in cells
                   if s.table_info[0] == t and s.table_info[1] == r}) == 1
              for t, r in set((s.table_info[0], s.table_info[1])
                              for s in cells)))
    # разделители исходника не стали сегментами
    sep_lines = {i for i, ln in enumerate(raw)
                 if ln.strip().startswith('|') and set(ln.strip()) <= set('|-: ')}
    para_ids = {s.paragraph_id for s in segs}
    check(f'A9 {label}: строки-разделители не сегменты',
          all((i + 1) not in para_ids for i in sep_lines),
          sorted(sep_lines))

# ══════════════════ B. Галка выключена — прежнее поведение ══════════════
for label, path in (('docling', MD_DOCLING), ('pymupdf', MD_PYMUPDF)):
    raw = read_lines(path)
    segs = import_md(path, recognize=False)
    check(f'B1 {label}: выключено — строка = сегмент',
          len(segs) == len(raw), (len(segs), len(raw)))
    check(f'B2 {label}: выключено — все type="para", без table_info',
          all(s.type == 'para' and not s.is_table_cell
              and s.table_info is None for s in segs))
    check(f'B3 {label}: выключено — «|---|» в тексте сегментов',
          any('|---' in s.source for s in segs))

# ══════════════ C. Круг «импорт → экспорт source без переводов» ═════════
for label, path in (('docling', MD_DOCLING), ('pymupdf', MD_PYMUPDF)):
    raw = read_lines(path)
    segs = import_md(path)
    out = export_lines(segs, use_source_fallback=True)
    src = source_lines(segs)
    check(f'C1 {label}: экспорт = исходнику по числу строк',
          len(out) == len(raw), (len(out), len(raw)))
    check(f'C2 {label}: source_lines выровнены 1:1', len(src) == len(out))
    blocks = find_table_blocks(raw)
    # позиции строк таблиц в выходе = позиции блоков в исходнике
    # (числа строк совпадают: исходник имеет разделители, экспорт их
    # регенерирует после заголовка)
    out_tables = []
    i = 0
    while i < len(out):
        if out[i].startswith('|'):
            j = i
            while j < len(out) and out[j].startswith('|'):
                j += 1
            out_tables.append((i, out[i:j]))
            i = j
        else:
            i += 1
    check(f'C3 {label}: число табличных блоков в экспорте',
          len(out_tables) == len(blocks), (len(out_tables), len(blocks)))
    skip = set()
    for bi, ((start_pos, blk), b) in enumerate(zip(out_tables, blocks)):
        check(f'C4 {label} таб.{bi}: блок в позиции исходника',
              start_pos == b.start, (start_pos, b.start))
        exp_rows = len(b.rows) + (1 if b.header else 0)
        check(f'C5 {label} таб.{bi}: строк в блоке (вкл. разделитель)',
              len(blk) == exp_rows, (len(blk), exp_rows))
        got_rows = []
        sep_seen = False
        for k, ln in enumerate(blk):
            cells_ln = split_table_row(ln)
            is_sep = (cells_ln is not None
                      and all(all(ch in '-:' for ch in c) and c
                              for c in cells_ln))
            if is_sep:
                sep_seen = True
                check(f'C6 {label} таб.{bi}: разделитель после заголовка, '
                      f'канонический',
                      b.header and k == 1
                      and ln == build_table_separator(b.n_cols_header), ln)
                continue
            got_rows.append(cells_ln)
        check(f'C7 {label} таб.{bi}: только заголовочный разделитель',
              sep_seen == b.header, sep_seen)
        check(f'C8 {label} таб.{bi}: ячейки структурно равны исходным',
              got_rows == b.rows, (len(got_rows), len(b.rows)))
        skip.update(range(start_pos, start_pos + len(blk)))
    check(f'C9 {label}: не-табличные строки байт-в-байт',
          all(out[i] == raw[i].rstrip('\r\n') for i in range(len(out))
              if i not in skip),
          [(i, out[i], raw[i]) for i in range(len(out))
           if i not in skip and out[i] != raw[i].rstrip('\r\n')][:2])

# ══════════════════ D. Перевод одной ячейки ═════════════════════════════
segs = import_md(MD_PYMUPDF)
target_seg = next(s for s in segs if s.is_table_cell
                  and s.table_info == (0, 1, 0, False))
before = export_lines(segs, use_source_fallback=True)
target_seg.target = 'ПЕРЕВЕДЕНО'
after = export_lines(segs, use_source_fallback=True)
diff_rows = [(a, b) for a, b in zip(before, after) if a != b]
check('D1 перевод одной ячейки меняет только её строку',
      len(diff_rows) == 1
      and sum('ПЕРЕВЕДЕНО' in b for b in after) == 1,
      diff_rows)
row = diff_rows[0][1]
check('D2 переведённая ячейка в своей колонке',
      split_table_row(row)[0] == 'ПЕРЕВЕДЕНО', row)

# ══════════════════ E. Ячейка с «\|» ════════════════════════════════════
syn_e = ['| a \\| b | c |', '|---|---|', '| d | e |']
segs_e = build_segments_from_lines(syn_e, None, recognize_tables=True)
cells_e = [s for s in segs_e if s.is_table_cell]
check('E1 «\\|» при импорте = «|» в тексте ячейки',
      cells_e[0].source == 'a | b', cells_e[0].source)
out_e = export_lines(segs_e, use_source_fallback=True)
check('E2 «\\|» при экспорте восстанавливается',
      out_e[0] == '| a \\| b | c |' and out_e[1] == '|---|---|'
      and out_e[2] == '| d | e |', out_e)

# ══════════════════ F. Пустая ячейка ════════════════════════════════════
syn_f = ['| x | |', '|---|---|', '| a | b |']
segs_f = build_segments_from_lines(syn_f, None, recognize_tables=True)
empty_cell = next(s for s in segs_f if s.is_table_cell and not s.source)
check('F1 пустая ячейка = сегмент с пустым source',
      empty_cell.source == '' and empty_cell.type == 'table_cell'
      and empty_cell.table_info == (0, 0, 1, True),
      (empty_cell.source, empty_cell.table_info))
out_f = export_lines(segs_f, use_source_fallback=True)
check('F2 пустая ячейка в экспорте = «| |»',
      out_f[0] == '| x | |', out_f[0])
out_f_nofb = export_lines(segs_f, use_source_fallback=False)
check('F3 без фолбэка пустая ячейка остаётся пустой',
      out_f_nofb[0] == '| | |', out_f_nofb[0])

# ══════════════════ G. Таблица без заголовка ════════════════════════════
syn_g = ['| a | b |', '| c | d |']
segs_g = build_segments_from_lines(syn_g, None, recognize_tables=True)
check('G1 обе строки — данные (is_header=False), table_idx=0',
      all(s.is_table_cell and s.table_info[3] is False
          and s.table_info[0] == 0 for s in segs_g if s.is_table_cell))
out_g = export_lines(segs_g, use_source_fallback=True)
check('G2 экспорт без разделителя', out_g == ['| a | b |', '| c | d |'], out_g)

# ══════════════════ H. Две таблицы через абзац ══════════════════════════
syn_h = ['| h1 | h2 |', '|---|---|', '| a | b |', 'Параграф между.',
         '| H1 | H2 | H3 |', '|---|---|---|', '| c | d | e |']
segs_h = build_segments_from_lines(syn_h, None, recognize_tables=True)
tis_h = sorted(set(s.table_info[0] for s in segs_h if s.is_table_cell))
check('H1 table_idx 0 и 1', tis_h == [0, 1], tis_h)
out_h = export_lines(segs_h, use_source_fallback=True)
check('H2 экспорт: две таблицы с абзацем между',
      out_h == ['| h1 | h2 |', '|---|---|', '| a | b |', 'Параграф между.',
                '| H1 | H2 | H3 |', '|---|---|---|', '| c | d | e |'], out_h)

# ══════════════ I. Проект: to_dict → JSON → from_dict ═══════════════════
segs_i = import_md(MD_PYMUPDF)
proj = Project(name='T', source_lang='en', target_lang='nl', segments=segs_i)
proj.original_txt_path = MD_PYMUPDF
blob = json.dumps(proj.to_dict(), ensure_ascii=False)
proj2 = Project.from_dict(json.loads(blob))
check('I1 table_info после JSON-круга — кортеж',
      all(isinstance(s.table_info, tuple) for s in proj2.segments
          if s.is_table_cell))
out_before = export_lines(proj.segments, use_source_fallback=True)
out_after = export_lines(proj2.segments, use_source_fallback=True)
check('I2 экспорт после загрузки тот же', out_before == out_after)
check('I3 число сегментов сохранено',
      len(proj.segments) == len(proj2.segments) == EXPECT['pymupdf'])

# ══════════════════ J. Tagged Text из таблицы ═══════════════════════════
from modules.tagged_text.mdparse import parse_markdown  # noqa: E402
from modules.tagged_text.writer import write_tagged_text  # noqa: E402
from modules.tagged_text.stylemap import StyleMap  # noqa: E402

md_j = '\n'.join(export_lines(segs_h, use_source_fallback=True))
parsed, stats_j = parse_markdown(md_j)
roles = [(b.role, b.text) for b in parsed]
check('J1 строки таблицы = роль table_row',
      all(r == 'table_row' for r, _ in roles if r != 'p'),
      roles)
check('J2 разделитель отброшен, table_row 4 шт.',
      sum(1 for r, _ in roles if r == 'table_row') == 4
      and not any('|---' in t for _, t in roles), roles)
data, report = write_tagged_text(md_j, StyleMap())
data_text = data.decode('utf-16') if isinstance(data, bytes) else data
check('J3 Tagged Text содержит <ParaStyle:table_row>',
      data_text.count('<ParaStyle:table_row>') == 4,
      data_text.count('<ParaStyle:table_row>'))
check('J4 предупреждений нет', len(report.warnings) == 0, report.warnings)

print(f'TBL12-TESTS: {_N[0]} checks, {_FAILS[0]} failed', flush=True)
