# -*- coding: utf-8 -*-
"""Характеризационное сравнение (Batch TBL1.2, Task 1): прежний
продублированный код построения сегментов import_simple_txt (монолит,
ветка основной и fallback-кодировок) против нового чистого построителя
modules/simple_import_builder.build_segments_from_lines.

Прежний код включён ВЕРБАТИМ (из снимков рабочей копии e7d91f05:
builder_block_main_before.py.txt / builder_block_fallback_before.py.txt,
отличалась только глубина отступа). Self-зависимостей у тела нет —
Segment строится одинаково; сегментер подаётся готовым объектом, как
его строит монолит: (MarkdownSegmenter if markdown else SimpleSegmenter)(
SegmentationRules()) — в свежем изолированном профиле из_dict(None)
даёт правила по умолчанию.

Сравнение: списки Segment.to_dict() (asdict), ключи created_at/modified_at
исключены (недетерминированные метки времени __post_init__, оба варианта
ставят «сейчас»); всё остальное — байт-в-байт через json.dumps(...,
ensure_ascii=False, sort_keys=True).

Входы: оба образца Input.md (docling, PyMuPDF4LLM из samples/md_out),
синтетический txt (пустые строки, заголовки, списки, картинки),
файл в cp1251 (реальный fallback-путь: байты невалидны в UTF-8).
Режимы: без сегментера и с сегментером (в обоих вариантах).
Запуск: E:\\Dev\\python-embed\\python.exe -u
docs/refactoring/audits/tbl12_import_builder_charact_tests.py
(без Qt; sys.path добавляет корень репозитория).
"""
import hashlib
import json
import os
import pathlib
import sys

REPO = r'E:\Dev\SupervertalerPortable'
sys.path.insert(0, REPO)
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

from modules.models import Segment  # noqa: E402
from modules.segmentation_rules import SegmentationRules  # noqa: E402
from modules.simple_segmenter import MarkdownSegmenter, SimpleSegmenter  # noqa: E402
from modules.simple_import_builder import build_segments_from_lines  # noqa: E402
from modules.statuses import DEFAULT_STATUS  # noqa: E402

STAGE = pathlib.Path(r'E:\Dev\Work_temp\SupervertalerPortable'
                     r'\refactoring\batch-tbl12\charact')
STAGE.mkdir(parents=True, exist_ok=True)

MD_DOCLING = (r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out\docling'
              r'\4164e8d8a0ef6c4df4142b7d9dc49a7f\Input.md')
MD_PYMUPDF = (r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out'
              r'\PyMuPDF4LLM\pymupdf4llm_gui_x0bf0ve2\Input.md')

SYNTH = STAGE / 'synthetic.txt'
SYNTH.write_text(
    "# Heading One\n"
    "\n"
    "Paragraph text with **bold** and *italic*.\n"
    "\n"
    "## Second heading\n"
    "\n"
    "- bullet one\n"
    "- bullet two\n"
    "\n"
    "1. numbered one\n"
    "2. numbered two\n"
    "\n"
    "![Image caption](images/pic_001.png)\n"
    "\n"
    "Line after the image.\n"
    "\n"
    "\n"
    "Line after empty gap.\n"
    "Last line with trailing spaces.   \n",
    encoding='utf-8')

CP1251 = STAGE / 'cp1251.txt'
CP1251.write_text(
    "Первая строка: пример русского текста.\n"
    "\n"
    "Вторая строка, содержащая буквы Ёё и цифры 12345.\n"
    "Третья строка — тире и кавычки «ёлочки».\n",
    encoding='cp1251')

_N = [0]


def check(name, cond, detail=''):
    _N[0] += 1
    print(f'{"PASS" if cond else "FAIL"} {name}'
          + ('' if cond else f'  DETAIL: {detail}'), flush=True)


def norm_dict_list(segments):
    out = []
    for s in segments:
        d = s.to_dict()
        d.pop('created_at', None)
        d.pop('modified_at', None)
        out.append(d)
    return out


def dumps(segments):
    return json.dumps(norm_dict_list(segments), ensure_ascii=False,
                      sort_keys=True)


# ── Прежний код ВЕРБАТИМ (из снимка builder_block_main_before.py.txt;
#    тело ветки fallback отличается только отступом и побочных состояний
#    не создаёт — в нём нет обращений к self) ──────────────────────────
def old_build(lines, use_sentence_segmentation, segmenter):
    """Точная копия прежнего построения (без ветвления по self)."""
    segments = []
    if use_sentence_segmentation:
        for line_num, line in enumerate(lines, 1):
            text = line.rstrip('\r\n')
            if not text.strip():
                # Empty line → empty segment (hidden in grid, preserved for export)
                segments.append(Segment(
                    id=len(segments) + 1, source=text, target="",
                    status="untranslated", notes="", type="para",
                    paragraph_id=line_num, document_position=line_num
                ))
            else:
                for sentence, separator in segmenter.segment_with_separators(text):
                    segments.append(Segment(
                        id=len(segments) + 1, source=sentence, target="",
                        status="untranslated", notes="", type="para",
                        paragraph_id=line_num, document_position=line_num,
                        join_before=separator
                    ))
    else:
        for line_num, line in enumerate(lines, 1):
            text = line.rstrip('\r\n')
            segments.append(Segment(
                id=len(segments) + 1, source=text, target="",
                status="untranslated", notes="", type="para",
                paragraph_id=line_num, document_position=line_num
            ))
    return segments


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


# ── Прежний код многофайлового TXT/MD-импорта ВЕРБАТИМ (снимок
#    builder_block_multifile_before.py.txt из e7d91f05; _extractor_label,
#    чтение файла и try/except — окружение монолита, тело построения —
#    ниже дословно) ─────────────────────────────────────────────────────
def old_build_multifile(lines, sentence_segment, txt_segmenter,
                        current_segment_id, file_id, file_name):
    """Точная копия прежней TXT/MD-ветки _import_multifile_project."""
    file_segments = []
    if sentence_segment:
        for line_num, line in enumerate(lines, 1):
            text = line.rstrip('\n\r')
            if not text.strip():
                file_segments.append(Segment(
                    id=current_segment_id, source=text, target="",
                    status=DEFAULT_STATUS.key, file_id=file_id,
                    file_name=file_name, paragraph_id=line_num,
                    document_position=line_num
                ))
                current_segment_id += 1
            else:
                for sentence, separator in txt_segmenter.segment_with_separators(text):
                    file_segments.append(Segment(
                        id=current_segment_id, source=sentence, target="",
                        status=DEFAULT_STATUS.key, file_id=file_id,
                        file_name=file_name, paragraph_id=line_num,
                        document_position=line_num, join_before=separator
                    ))
                    current_segment_id += 1
    else:
        for line_num, line in enumerate(lines, 1):
            text = line.rstrip('\n\r')
            file_segments.append(Segment(
                id=current_segment_id, source=text, target="",
                status=DEFAULT_STATUS.key, file_id=file_id,
                file_name=file_name, paragraph_id=line_num,
                document_position=line_num
            ))
            current_segment_id += 1
    return file_segments


inputs = [
    ('md docling', MD_DOCLING, 'utf-8', True),
    ('md pymupdf', MD_PYMUPDF, 'utf-8', True),
    ('synthetic txt', str(SYNTH), 'utf-8', False),
    ('cp1251 fallback', str(CP1251), 'cp1251', False),
]

for label, path, enc, is_md in inputs:
    with open(path, 'r', encoding=enc) as f:
        lines = f.readlines()
    for seg_mode, seg_name in ((False, 'без сегментера'),
                               (True, 'с сегментером')):
        seg_obj = None
        if seg_mode:
            rules = SegmentationRules()
            seg_obj = (MarkdownSegmenter if is_md else SimpleSegmenter)(rules)
        old = old_build(lines, seg_mode, seg_obj)
        new = build_segments_from_lines(lines, seg_obj if seg_mode else None)
        o, n = dumps(old), dumps(new)
        check(f'{label} [{seg_name}]: to_dict байт-в-байт',
              o == n, (sha(o), sha(n), len(old), len(new)))
        check(f'{label} [{seg_name}]: длина и параграф-идентификаторы',
              len(old) == len(new)
              and [s.paragraph_id for s in old] == [s.paragraph_id for s in new]
              and [s.id for s in old] == [s.id for s in new]
              and [s.type for s in old] == [s.type for s in new]
              and [s.status for s in old] == [s.status for s in new]
              and [s.join_before for s in old] == [s.join_before for s in new],
              (len(old), len(new)))

# ── Многофайловый TXT/MD-импорт (ветка _import_multifile_project):
#    recognize_tables=False (галка выключена) — байт-в-байт против прежнего
#    кода; file_id/file_name/DEFAULT_STATUS.key/продолжающийся id ────────
for label, path, is_md in (('multifile md docling', MD_DOCLING, True),
                           ('multifile md pymupdf', MD_PYMUPDF, True),
                           ('multifile synthetic', str(SYNTH), False),
                           ('multifile cp1251', str(CP1251), False)):
    with open(path, 'r', encoding='cp1251' if 'cp1251' in label else 'utf-8') as f:
        lines = f.readlines()
    for seg_mode, seg_name in ((False, 'без сегментера'),
                               (True, 'с сегментером')):
        seg_obj = None
        if seg_mode:
            rules = SegmentationRules()
            seg_obj = (MarkdownSegmenter if is_md else SimpleSegmenter)(rules)
        old = old_build_multifile(lines, seg_mode, seg_obj,
                                  current_segment_id=17, file_id=3,
                                  file_name='Input.md')
        new = build_segments_from_lines(
            lines, seg_obj if seg_mode else None, recognize_tables=False,
            id_start=17, status=DEFAULT_STATUS.key, file_id=3,
            file_name='Input.md')
        o, n = dumps(old), dumps(new)
        check(f'{label} [{seg_name}]: to_dict байт-в-байт',
              o == n, (sha(o), sha(n), len(old), len(new)))

print(f'CHARACT-TESTS: {_N[0]} passed / '
      f'{sum(1 for _ in [])} — всего проверок {_N[0]}', flush=True)
