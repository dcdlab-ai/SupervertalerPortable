"""mdparse — разбор строки Markdown на блоки (Batch I1).

Одна непустая строка md = один блок (как в import_simple_txt
Supervertaler.py: предложение не применяется). Роли:

* ``h1``/``h2``/``h3``  — заголовки ``#``/``##``/``###``
  (``####``–``######`` понижаются до ``h3`` со счётчиком);
* ``p``                — обычный абзац;
* ``li``               — маркированный пункт (``-``/``*``/``+``);
* ``li_n``             — нумерованный пункт (``1.``/``1)``);
* ``img``              — строка только из ``![alt](путь)``;
* ``table_row``        — временная роль I1 (pipe-строки и содержимое
  оград ``​```csv``); разделители ``|---|`` и комментарии ``<!-- … -->``
  отбрасываются (настоящие таблицы — батчи TBL1/TBL2).

Смешанная строка (текст + картинка) режется на блоки text/img/text
с предупреждением (в образцах не встречается).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Порядок ролей определяет порядок DefineParaStyle в шапке писателя.
ROLES = ('h1', 'h2', 'h3', 'p', 'li', 'li_n', 'img', 'table_row')

# Заголовки: #### … ###### понижаются до h3 (решение промпта I1).
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
# Маркированный список: маркер отбрасывается.
_BULLET_RE = re.compile(r'^[-*+]\s+(.+?)\s*$')
# Нумерованный список: номер СОХРАНЯЕТСЯ текстом (нумерацию стилем не
# задаём — определение li_n пишется без атрибутов списка).
_NUM_RE = re.compile(r'^(\d+[.)])\s+(.+?)\s*$')
# Картинка: ![alt](path)
_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(\s*([^)]+?)\s*\)')
# Строка целиком — картинка (окружающие пробелы допустимы).
_IMAGE_ONLY_RE = re.compile(r'^\s*!\[([^\]]*)\]\(\s*([^)]+?)\s*\)\s*$')
# Комментарий-строка <!-- … --> (отбрасывается).
_COMMENT_RE = re.compile(r'^<!--.*-->\s*$')


@dataclass
class Block:
    """Один блок вывода: роль + исходный текст строки (без роли-разметки)."""

    role: str
    text: str


@dataclass
class ParseStats:
    """Счётчики разбора md (попадают в отчёт экспорта)."""

    headings_downgraded: dict = field(default_factory=dict)  # 'h4' -> count
    comments_dropped: int = 0
    table_separators_dropped: int = 0
    fence_lines_dropped: int = 0
    fence_blocks: int = 0
    non_csv_fences: int = 0
    table_rows: int = 0
    empty_lines_skipped: int = 0
    mixed_image_lines: int = 0
    warnings: list = field(default_factory=list)


def _split_mixed_image(text: str, stats: ParseStats):
    """Строка с картинкой и текстом → блоки text/img/text."""
    stats.mixed_image_lines += 1
    stats.warnings.append(
        'смешанная строка (текст + картинка) разрезана на блоки: '
        + (text[:60] + '…' if len(text) > 60 else text))
    blocks = []
    pos = 0
    for m in _IMAGE_RE.finditer(text):
        before = text[pos:m.start()]
        if before.strip():
            blocks.append(Block('p', before.strip()))
        blocks.append(Block('img', m.group(0)))
        pos = m.end()
    tail = text[pos:]
    if tail.strip():
        blocks.append(Block('p', tail.strip()))
    return blocks


def parse_markdown(md_text: str):
    """Строка md → (список Block, ParseStats). Пустые строки пропускаются."""
    stats = ParseStats()
    blocks = []
    in_fence = False
    for raw_line in md_text.splitlines():
        line = raw_line.rstrip('\r\n')
        stripped = line.strip()
        if not stripped:
            stats.empty_lines_skipped += 1
            continue
        if stripped.startswith('```'):
            # Ограда: сама строка отбрасывается, содержимое — table_row
            # (временный режим I1; настоящие таблицы — TBL1/TBL2).
            stats.fence_lines_dropped += 1
            if not in_fence:
                in_fence = True
                stats.fence_blocks += 1
                info = stripped[3:].strip()
                if info and info.lower() != 'csv':
                    stats.non_csv_fences += 1
                    stats.warnings.append(
                        'ограда не csv (содержимое записано table_row): '
                        + info)
            else:
                in_fence = False
            continue
        if in_fence:
            blocks.append(Block('table_row', stripped))
            stats.table_rows += 1
            continue
        if _COMMENT_RE.match(stripped):
            stats.comments_dropped += 1
            continue
        # Разделитель pipe-таблицы: только |, -, :, +, пробелы, ≥2 «|».
        if ('|' in stripped
                and set(stripped) <= set('|-:+ ')
                and stripped.count('|') >= 2
                and '---' in stripped):
            stats.table_separators_dropped += 1
            continue
        m = _IMAGE_ONLY_RE.match(stripped)
        if m:
            blocks.append(Block('img', m.group(0)))
            continue
        if '|' in stripped and stripped.startswith('|'):
            blocks.append(Block('table_row', stripped))
            stats.table_rows += 1
            continue
        if _IMAGE_RE.search(stripped):
            blocks.extend(_split_mixed_image(stripped, stats))
            continue
        m = _HEADING_RE.match(stripped)
        if m:
            level = len(m.group(1))
            if level <= 3:
                blocks.append(Block('h%d' % level, m.group(2)))
            else:
                key = 'h%d' % level
                stats.headings_downgraded[key] = (
                    stats.headings_downgraded.get(key, 0) + 1)
                blocks.append(Block('h3', m.group(2)))
            continue
        m = _BULLET_RE.match(stripped)
        if m:
            blocks.append(Block('li', m.group(1)))
            continue
        m = _NUM_RE.match(stripped)
        if m:
            # «3. текст» → номер сохраняется текстом, роль li_n.
            blocks.append(Block('li_n', m.group(1) + ' ' + m.group(2)))
            continue
        blocks.append(Block('p', stripped))
    return blocks, stats
