"""writer — блоки Markdown → байты InDesign Tagged Text (Batch I1/I1.1).

Формат установлен ручными тестами I0/I0-B/I0-C (s11.8–s11.9 отчёта I0)
и ручными тестами I1 (T4c1/T4c2/T-I1a/T-I1b, отчёт I1.1):

* UTF-16LE + BOM (единственная кодировка), разделитель строк CRLF;
* строка 1 — ``<UNICODE-WIN>`` отдельно (T4b1: иначе файл читается как
  обычный текст); строка 2 — ``<Version:16.4><FeatureSet:InDesign-Roman>``
  + ColorTable. **Дефолт — ``minimal``** (Black+Paper): ручной факт I1 —
  режим ``none`` (без ColorTable) даёт ПУСТЫЕ абзацы перед текстом, их
  число = число строк Define*Style + 1 (T4c1: 10; T-I1a: 5; T-I1b: 8);
  с минимальным ColorTable пустых абзацев нет (T4c2). Режим ``gboh``
  (дословно строка 2 образца, 7 цветов) — для побайтовой регенерации
  T4b2; далее по одному Define*Style на строку (T4b2);
* в ТЕКСТЕ экранируются только ``\\``, ``<``, ``>`` (T5b: ``\\; \\: \\, \\=``
  в тексте дают ошибки в логе InDesign); в ЗНАЧЕНИЯХ тегов —
  ``\\ < > : ; , = [ ]`` (минимум промпта I1; подчёркивание НЕ экранируется
  — решение координатора I1.1, подтверждено T-I1a: стиль table_row
  применился без ``\\_``);
* HTML-сущности (только с «;») раскодируются; ``<br>`` → одиночный LF
  (принудительный перенос внутри абзаца);
* md-экранирование на входе (CommonMark, I1.1): ``\\`` + ASCII-пунктуация
  → сам знак; снимается ПОСЛЕ разбора выделений (экранированный маркер
  ``\\*`` не считается выделением), пути в ``![…](…)`` не трогаются;
  ``\\`` + не-пунктуация остаётся буквально;
* выделения: ``**``→Bold, ``*``/``_``→Italic, ``***``/``**_``→BoldItalic
  через ``<CharStyle:…>…<CharStyle:>``; ``_`` — только на границе слов;
  несбалансированные маркеры остаются буквально и считаются; в заголовках
  выделения снимаются (оформление даёт абзацный стиль);
* в блоках table_row серии из 2+ пробелов схлопываются в один
  (отступы столбцов docling; I1.1), остальной текст не трогается;
* картинки: строка-только-картинка → абзац роли img; ``images/<имя>`` —
  как есть; абсолютный путь → базовое имя + поиск в ``images/`` рядом с
  выходом, предупреждение при отсутствии (правило s11.5);
* таблицы md (pipe и ограда csv) в I1 НЕ собираются: строки пишутся
  абзацами роли table_row, разделители ``|---|`` и комментарии
  отбрасываются (настоящие таблицы — батчи TBL1/TBL2).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .mdparse import ROLES, parse_markdown
from .stylemap import StyleMap, CHAR_KEYS

VERSION_DEFAULT = '16.4'

CRLF = '\r\n'
BOM = b'\xff\xfe'

# Строка 2 образца GBoH дословно (режим color_table='gboh', для побайтовой
# регенерации T4b2; содержит 7 образцов цвета).
GBOH_COLOR_LINE2 = (
    '<ColorTable:='
    '<Black:COLOR:CMYK:Process:0,0,0,1>'
    '<C\\=15 M\\=100 Y\\=100 K\\=0:COLOR:CMYK:Process:0.15,1,1,0>'
    '<Paper:COLOR:CMYK:Process:0,0,0,0>'
    '<C\\=0 M\\=0 Y\\=0 K\\=90:COLOR:CMYK:Process:0,0,0,0.9>'
    '<C\\=100 M\\=0 Y\\=0 K\\=0:COLOR:CMYK:Process:1,0,0,0>'
    '<C\\=8 M\\=10 Y\\=18 K\\=0:COLOR:CMYK:Process:0.08,0.1,0.18,0>'
    '<Word\\_R0\\_G0\\_B0:COLOR:RGB:Process:0,0,0>>')

# Минимальный ColorTable (режим color_table='minimal' — ДЕФОЛТ с I1.1:
# ручной факт — 'none' даёт пустые абзацы = Define*Style + 1; только
# Black и Paper).
MINIMAL_COLOR_LINE2 = (
    '<ColorTable:='
    '<Black:COLOR:CMYK:Process:0,0,0,1>'
    '<Paper:COLOR:CMYK:Process:0,0,0,0>>')

COLOR_TABLE_MODES = ('none', 'minimal', 'gboh')

# cTypeface — значение шрифтового начертания (не имя стиля): из образца
# GBoH / T4b2 (s11.8.4).
TYPEFACE_BY_KEY = {
    'bold': 'Bold',
    'italic': 'Italic',
    'bold_italic': 'Bold Italic',
}

# Экранирование в ТЕКСТЕ: только эти три замены (T5b).
_TEXT_ESCAPE = (('\\', '\\\\'), ('<', '\\<'), ('>', '\\>'))
# Экранирование в ЗНАЧЕНИЯХ тегов: минимум промпта I1 + скобки.
_VALUE_ESCAPE = (('\\', '\\\\'), ('<', '\\<'), ('>', '\\>'),
                 (':', '\\:'), (';', '\\;'), (',', '\\,'),
                 ('=', '\\='), ('[', '\\['), (']', '\\]'))

# HTML-сущности: только с «;»; именованные — маленький набор промпта,
# числовые (десятичные и hex) — любые корректные.
_ENTITY_RE = re.compile(r'&(#x[0-9A-Fa-f]+|#\d+|[A-Za-z][A-Za-z0-9]*);')
_NAMED_ENTITIES = {
    'amp': '&',
    'lt': '<',
    'gt': '>',
    'quot': '"',
    'apos': "'",
}

# <br> → одиночный LF (принудительный перенос внутри абзаца).
_BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)

# Порядок важен: сначала комбинированные (bold-italic), затем bold,
# затем italic; при сканировании слева направо alternation пробует
# шаблоны в этом порядке на каждой позиции.
_EMPHASIS_PATTERNS = (
    ('bold_italic', re.compile(r'\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*')),
    ('bold_italic', re.compile(r'\*\*_(?=\S)(.+?)(?<=\S)_\*\*')),
    ('bold', re.compile(r'\*\*(?=\S)(.+?)(?<=\S)\*\*')),
    ('italic', re.compile(r'(?<!\*)\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?!\*)')),
    ('italic',
     re.compile(r'(?<![A-Za-z0-9_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![A-Za-z0-9_])')),
)
_EMPHASIS_KEYS = tuple(key for key, _ in _EMPHASIS_PATTERNS)
_EMPHASIS_COMBINED = re.compile(
    '|'.join('(?:%s)' % rx.pattern for _, rx in _EMPHASIS_PATTERNS))

# Маркеры, оставшиеся буквально: пробеги звёздочек и подчёркивания на
# границе слов (определение счётчика несбалансированных маркеров).
_STAR_RUN_RE = re.compile(r'\*+')
_BOUNDARY_US_RE = re.compile(r'(?<![A-Za-z0-9_])_|_(?![A-Za-z0-9_])')


# Абсолютный путь: диск (C:\, C:/) или ведущий слэш.
_ABS_PATH_RE = re.compile(r'^([A-Za-z]:[\\/]|[/\\])')

# md-экранирование на входе (CommonMark, I1.1): `\` + ASCII-пунктуация →
# сам знак; `\` + не-пунктуация остаётся буквально. Защита (sentinel)
# выполняется ДО разбора выделений — экранированный маркер `\*` не виден
# матчеру; восстановление — в process_plain ПОСЛЕ сущностей и <br>
# (чтобы `\&amp;` не превратился в `&`) и ПЕРЕД экранированием выхода.
_ASCII_PUNCTUATION = set('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
_ANY_ESC_RE = re.compile(r'\\(.)')
_SENTINEL_RE = re.compile('\x00(\\d+)\x01')

# Схлопывание серий пробелов (2+) — только table_row (I1.1).
_SPACES_RUN_RE = re.compile(' {2,}')


@dataclass
class ExportReport:
    """Отчёт экспорта md → Tagged Text (счётчики + предупреждения)."""

    role_counts: dict = field(default_factory=dict)
    define_styles: list = field(default_factory=list)
    char_style_spans: dict = field(default_factory=lambda: {k: 0 for k in CHAR_KEYS})
    entities_decoded: int = 0
    entity_kinds: dict = field(default_factory=dict)
    br_breaks: int = 0
    md_escapes_unescaped: int = 0
    spaces_collapsed: int = 0
    emphasis_leftover: int = 0
    emphasis_stripped_headings: int = 0
    comments_dropped: int = 0
    table_separators_dropped: int = 0
    fence_lines_dropped: int = 0
    fence_blocks: int = 0
    non_csv_fences: int = 0
    table_rows: int = 0
    empty_lines_skipped: int = 0
    mixed_image_lines: int = 0
    headings_downgraded: dict = field(default_factory=dict)
    images_total: int = 0
    images_found: int = 0
    images_missing: list = field(default_factory=list)
    color_table_mode: str = 'none'
    warnings: list = field(default_factory=list)

    def to_text(self):
        """Человекочитаемое представление отчёта."""
        lines = ['Отчёт экспорта InDesign Tagged Text']
        lines.append('ColorTable: %s' % self.color_table_mode)
        lines.append('Определения стилей (Define*Style): %s'
                     % (', '.join(self.define_styles) or '—'))
        roles = ', '.join('%s=%d' % (r, n)
                          for r, n in sorted(self.role_counts.items()))
        lines.append('Абзацы по ролям: %s' % (roles or '—'))
        spans = ', '.join('%s=%d' % (k, n) for k, n in self.char_style_spans.items())
        lines.append('Символьные спаны: %s' % spans)
        lines.append('Сущности раскодированы: %d' % self.entities_decoded)
        if self.entity_kinds:
            kinds = ', '.join('&%s;=%d' % (k, n)
                              for k, n in sorted(self.entity_kinds.items()))
            lines.append('  по видам: %s' % kinds)
        lines.append('Принудительные переносы (<br>): %d' % self.br_breaks)
        lines.append('md-экранирование снято (\\+пунктуация): %d'
                     % self.md_escapes_unescaped)
        lines.append('Серии пробелов схлопнуты (table_row): %d'
                     % self.spaces_collapsed)
        lines.append('Несбалансированные маркеры выделения (остались буквально): %d'
                     % self.emphasis_leftover)
        lines.append('Выделения сняты в заголовках: %d'
                     % self.emphasis_stripped_headings)
        lines.append('Комментарии отброшены: %d' % self.comments_dropped)
        lines.append('Разделители таблиц отброшены: %d' % self.table_separators_dropped)
        lines.append('Строки оград отброшены: %d (оград: %d)'
                     % (self.fence_lines_dropped, self.fence_blocks))
        lines.append('Строки таблиц (table_row): %d' % self.table_rows)
        lines.append('Пустые строки пропущены: %d' % self.empty_lines_skipped)
        if self.headings_downgraded:
            dg = ', '.join('%s→h3=%d' % (k, v)
                           for k, v in sorted(self.headings_downgraded.items()))
            lines.append('Заголовки понижены до h3: %s' % dg)
        lines.append('Картинки: всего %d, найдено %d, не найдено %d'
                     % (self.images_total, self.images_found,
                        len(self.images_missing)))
        for p in self.images_missing:
            lines.append('  не найден: %s' % p)
        if self.mixed_image_lines:
            lines.append('Смешанных строк (текст+картинка): %d'
                         % self.mixed_image_lines)
        if self.warnings:
            lines.append('Предупреждения:')
            for w in self.warnings:
                lines.append('  - %s' % w)
        else:
            lines.append('Предупреждения: нет')
        return '\n'.join(lines)


def escape_text(s):
    """Экранирование обычного текста: только \\ → \\\\, < → \\<, > → \\>."""
    for old, new in _TEXT_ESCAPE:
        s = s.replace(old, new)
    return s


def escape_value(s):
    """Экранирование значения тега (имя стиля и т. п.): минимум промпта I1."""
    for old, new in _VALUE_ESCAPE:
        s = s.replace(old, new)
    return s


def count_leftover_markers(s):
    """Несбалансированные маркеры в готовом тексте: пробеги «*» и подчёркивания
    на границе слов; каждый пробег/токен считается за 1."""
    n = len(_STAR_RUN_RE.findall(s))
    n += len(_BOUNDARY_US_RE.findall(s))
    return n


def protect_escapes(text):
    """I1.1: защитить md-экранирование (``\\`` + ASCII-пунктуация) sentinel'ом
    ДО разбора выделений. ``\\`` + не-пунктуация остаётся буквально.
    Возвращает (текст с sentinel'ами, список экранированных знаков)."""
    escapes = []

    def repl(m):
        ch = m.group(1)
        if ch in _ASCII_PUNCTUATION:
            escapes.append(ch)
            return '\x00%d\x01' % (len(escapes) - 1)
        return m.group(0)

    return _ANY_ESC_RE.sub(repl, text), escapes


def unescape_md(text, report):
    """I1.1: снять md-экранирование напрямую (для alt-текста картинок,
    где sentinel-конвейер не применяется). Пути не проходят через эту
    функцию — вызов только на alt."""
    def repl(m):
        ch = m.group(1)
        if ch in _ASCII_PUNCTUATION:
            report.md_escapes_unescaped += 1
            return ch
        return m.group(0)

    return _ANY_ESC_RE.sub(repl, text)


def make_plain_processor(report, escapes):
    """Замыкание обработки защищённого текстового куска: сущности → <br> →
    восстановление sentinel'ов (md-unescape) → экранирование выхода;
    счётчики пишутся в отчёт."""

    def process_plain(s):
        text, kinds = _decode_entities(s)

        def bump(kind):
            report.entities_decoded += 1
            report.entity_kinds[kind] = report.entity_kinds.get(kind, 0) + 1

        for kind in kinds:
            bump(kind)
        text, n_br = _BR_RE.subn('\n', text)
        report.br_breaks += n_br

        def restore(m):
            report.md_escapes_unescaped += 1
            return escapes[int(m.group(1))]

        text = _SENTINEL_RE.sub(restore, text)
        return escape_text(text)

    return process_plain


def _decode_entities(s):
    """HTML-сущности (только с «;») → символы. Возвращает (текст, виды)."""
    kinds = []

    def repl(m):
        body = m.group(1)
        if body.startswith('#'):
            try:
                code = int(body[2:], 16) if body[1] in 'xX' else int(body[1:])
            except ValueError:
                return m.group(0)
            if not (0 <= code <= 0x10FFFF):
                return m.group(0)
            kinds.append('#' + ('x' + body[2:].lower() if body[1] in 'xX'
                                else body[1:]))
            return chr(code)
        named = _NAMED_ENTITIES.get(body)
        if named is None:
            return m.group(0)  # неизвестная именованная — оставить буквально,
            # в счётчик раскодированных не попадает
        kinds.append(body)
        return named

    return _ENTITY_RE.sub(repl, s), kinds


def apply_emphasis(text, style_map, process_plain, report):
    """Выделения md → CharStyle-теги; plain-куски обрабатываются process_plain.

    Несбалансированные маркеры остаются буквально (в plain-кусках и внутри
    спанов) и считаются в отчёте: каждый пробег «*» и подчёркивание на
    границе слов — за 1.
    """
    out = []
    counts = report.char_style_spans
    leftover = 0
    pos = 0
    for m in _EMPHASIS_COMBINED.finditer(text):
        gap = text[pos:m.start()]
        if gap:
            out.append(process_plain(gap))
            leftover += count_leftover_markers(gap)
        key = _EMPHASIS_KEYS[m.lastindex - 1]
        counts[key] += 1
        inner_raw = m.group(m.lastindex)
        leftover += count_leftover_markers(inner_raw)
        inner = process_plain(inner_raw)
        out.append('<CharStyle:%s>%s<CharStyle:>'
                   % (escape_value(style_map.char_name(key)), inner))
        pos = m.end()
    tail = text[pos:]
    if tail:
        out.append(process_plain(tail))
        leftover += count_leftover_markers(tail)
    report.emphasis_leftover += leftover
    return ''.join(out)


def strip_emphasis_in_heading(text, process_plain, report):
    """В заголовках выделения снимаются: оформление даёт абзацный стиль.

    Снимаются только ПАРНЫЕ выделения (найденные тем же матчером):
    разделители удаляются, содержимое остаётся; счётчик — снятые спаны.
    Одиночные маркеры (например «Define*Style») остаются как есть.
    """
    out = []
    pos = 0
    for m in _EMPHASIS_COMBINED.finditer(text):
        out.append(text[pos:m.start()])
        out.append(m.group(m.lastindex))
        report.emphasis_stripped_headings += 1
        pos = m.end()
    out.append(text[pos:])
    return process_plain(''.join(out))


def _line_suffix(lineno):
    """« (строка N)» для предупреждений отчёта (Batch I2); 0 → пусто."""
    return ' (строка %d)' % lineno if lineno else ''


def _normalize_image(label_text, images_dir, report, lineno=0):
    """Картинка → текст метки с путём по правилу s11.5.

    Относительный ``images/<имя>`` пишется как есть; абсолютный путь →
    базовое имя + поиск в ``images_dir`` (по умолчанию ``images/`` рядом
    с выходным файлом), предупреждение при отсутствии; прочие
    относительные пути пишутся как есть (отдельное предупреждение).
    Найдено/не найдено считается для всех картинок с путём images/.
    ``lineno`` — номер строки md для предупреждений (Batch I2).
    """
    m = re.match(r'^!\[([^\]]*)\]\(\s*([^)]+?)\s*\)$', label_text)
    if not m:
        report.warnings.append('не удалось разобрать метку картинки%s: %s'
                               % (_line_suffix(lineno), label_text[:80]))
        return escape_text(label_text)
    alt, raw_path = m.group(1), m.group(2)
    # I1.1: alt — текст (md-unescape), путь НЕ трогается (решение
    # координатора); сущности в пути раскодируются как раньше.
    alt = unescape_md(alt, report)
    alt, alt_kinds = _decode_entities(alt)
    report.entities_decoded += len(alt_kinds)
    for kind in alt_kinds:
        report.entity_kinds[kind] = report.entity_kinds.get(kind, 0) + 1
    path, kinds = _decode_entities(raw_path)
    report.entities_decoded += len(kinds)
    for kind in kinds:
        report.entity_kinds[kind] = report.entity_kinds.get(kind, 0) + 1
    p = path.replace('\\', '/')
    report.images_total += 1
    found = None
    if _ABS_PATH_RE.match(p):
        basename = p.rsplit('/', 1)[-1]
        p = 'images/' + basename
        if images_dir:
            cand = os.path.join(images_dir, basename)
            found = cand if os.path.isfile(cand) else None
        if found is None:
            report.warnings.append('файл не найден%s: %s'
                                   % (_line_suffix(lineno), raw_path))
    elif p.startswith('images/'):
        if images_dir:
            cand = os.path.join(images_dir, p[len('images/'):])
            found = cand if os.path.isfile(cand) else None
    else:
        report.warnings.append(
            'относительный путь вне images/ — записан как есть%s: %s'
            % (_line_suffix(lineno), p))
    if found is not None:
        report.images_found += 1
    else:
        report.images_missing.append(p)
    label = '![%s](%s)' % (alt, p)
    return escape_text(label)


def write_tagged_text(md_text, style_map=None, *, color_table='minimal',
                      char_style_policy='used', version=VERSION_DEFAULT,
                      images_dir=None, source_lines=None):
    """Собрать Tagged Text: возвращает (bytes, ExportReport).

    color_table: 'minimal' (Black+Paper — ДЕФОЛТ с I1.1: ручной факт —
    'none' даёт пустые абзацы = Define*Style + 1) | 'none' | 'gboh'
    (дословно образец, T4b2).
    char_style_policy: 'used' (только использованные) | 'all' (все три).
    source_lines: необязательный список исходных текстов, выровненный 1:1 со
    строками md_text (Batch C1). Когда передан, каждая строка-перевод
    проверяется на эхо промта (маркеры каркаса, которых нет в исходнике) —
    в report.warnings добавляется предупреждение с номером строки; экспорт
    НЕ блокируется. Без source_lines проверка не выполняется (CLI/регресс
    без изменений).
    """
    if style_map is None:
        style_map = StyleMap()
    if color_table not in COLOR_TABLE_MODES:
        raise ValueError('color_table: ожидается одно из %s, получено %r'
                         % (COLOR_TABLE_MODES, color_table))
    if char_style_policy not in ('used', 'all'):
        raise ValueError('char_style_policy: used|all, получено %r'
                         % char_style_policy)
    report = ExportReport(color_table_mode=color_table)
    if source_lines is not None:
        # Batch C1: проверка эха промта по строкам перевода (до записи;
        # предупреждение, не блокировка). source_lines выровнен со строками
        # md_text — номера строк совпадают с нумерацией предупреждений о
        # картинках (_line_suffix).
        from modules.prompt_markers import looks_like_prompt_echo
        md_lines = md_text.split('\n')
        for lineno, (line, src) in enumerate(zip(md_lines, source_lines), 1):
            if line and looks_like_prompt_echo(line, src):
                report.warnings.append('похоже на эхо промта%s: %s'
                                       % (_line_suffix(lineno), line[:80]))
        # Batch C2: перелив контекста (модель перевела соседние сегменты
        # вместе с текущим; уже сохранённый target). В отличие от эха
        # перелив не ловится построчно — перелившийся target занимает
        # НЕСКОЛЬКО физических строк md, а построчный вызов на каждой
        # строке-абзаце видит 1 абзац против 1 у source. Сигнатура в этом
        # выравнивании: серия последовательных строк с ОДНИМ и тем же
        # source (так разворачиваются логические строки в
        # export_tagged_txt: [src] * (out.count('\n') + 1)). Серия
        # объединяется и сравнивается с source целиком; номер строки —
        # первая строка серии. Предупреждение, не блокировка; легитимное
        # совпадение source двух соседних сегментов теоретически может
        # дать ложное срабатывание (редко; экспорт не блокируется).
        from modules.prompt_markers import looks_like_context_overflow
        _n_md = len(md_lines)
        i = 0
        while i < _n_md:
            _src = source_lines[i] if i < len(source_lines) else None
            if not _src or not _src.strip():
                i += 1
                continue
            j = i
            while (j < _n_md and j < len(source_lines)
                   and source_lines[j] == _src):
                j += 1
            _run = '\n'.join(md_lines[i:j])
            if looks_like_context_overflow(_run, _src):
                report.warnings.append(
                    'возможный перелив контекста%s: %s'
                    % (_line_suffix(i + 1), md_lines[i][:80]))
            i = j
    blocks, stats = parse_markdown(md_text)
    report.comments_dropped = stats.comments_dropped
    report.table_separators_dropped = stats.table_separators_dropped
    report.fence_lines_dropped = stats.fence_lines_dropped
    report.fence_blocks = stats.fence_blocks
    report.non_csv_fences = stats.non_csv_fences
    report.table_rows = stats.table_rows
    report.empty_lines_skipped = stats.empty_lines_skipped
    report.mixed_image_lines = stats.mixed_image_lines
    report.headings_downgraded = dict(stats.headings_downgraded)
    report.warnings.extend(stats.warnings)
    if stats.non_csv_fences:
        report.warnings.append(
            'оград не csv: %d (содержимое записано как table_row)'
            % stats.non_csv_fences)
    for b in blocks:
        report.role_counts[b.role] = report.role_counts.get(b.role, 0) + 1

    # --- шапка ---
    line2 = '<Version:%s><FeatureSet:InDesign-Roman>' % version
    if color_table == 'gboh':
        line2 += GBOH_COLOR_LINE2
    elif color_table == 'minimal':
        line2 += MINIMAL_COLOR_LINE2
    lines = ['<UNICODE-WIN>', line2]

    # --- Define*Style: только использованные роли, в порядке ROLES ---
    used_roles = [r for r in ROLES if r in report.role_counts]
    for role in used_roles:
        name = escape_value(style_map.para_name(role))
        lines.append('<DefineParaStyle:%s=<Nextstyle:%s>>' % (name, name))
        report.define_styles.append('DefineParaStyle:%s' % name)

    # --- тело ---
    body_lines = []
    for b in blocks:
        if b.role == 'img':
            # путь не проходит через protect_escapes (I1.1: пути не трогать)
            text = _normalize_image(b.text, images_dir, report, lineno=b.line)
        else:
            # I1.1: md-экранирование защищается ДО разбора выделений
            protected, escapes = protect_escapes(b.text)
            process_plain = make_plain_processor(report, escapes)
            if b.role in ('h1', 'h2', 'h3'):
                text = strip_emphasis_in_heading(
                    protected, process_plain, report)
            else:  # p, li, li_n, table_row
                text = apply_emphasis(
                    protected, style_map, process_plain, report)
            if b.role == 'table_row':
                # I1.1: серии пробелов (отступы столбцов docling) → один
                text, n_sp = _SPACES_RUN_RE.subn(' ', text)
                report.spaces_collapsed += n_sp
        name = escape_value(style_map.para_name(b.role))
        body_lines.append('<ParaStyle:%s>%s' % (name, text))

    # определения символьных стилей — после прохода по телу:
    # 'used' — только использованные, 'all' — все три (регенерация T4b2)
    if char_style_policy == 'all':
        char_keys = list(CHAR_KEYS)
    else:
        char_keys = [k for k in CHAR_KEYS if report.char_style_spans.get(k)]
    for key in char_keys:
        name = escape_value(style_map.char_name(key))
        lines.append('<DefineCharStyle:%s=<Nextstyle:%s><cTypeface:%s>>'
                     % (name, name, TYPEFACE_BY_KEY[key]))
        report.define_styles.append('DefineCharStyle:%s' % name)

    lines.extend(body_lines)
    text = CRLF.join(lines) + CRLF
    return BOM + text.encode('utf-16-le'), report


def write_file(in_md_path, out_txt_path, style_map=None, **kwargs):
    """Прочитать md, записать Tagged Text, вернуть отчёт.

    images_dir по умолчанию — ``images/`` рядом с выходным файлом.
    """
    images_dir = kwargs.pop('images_dir', None)
    with open(in_md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    if images_dir is None:
        images_dir = os.path.join(
            os.path.dirname(os.path.abspath(out_txt_path)), 'images')
    data, report = write_tagged_text(
        md_text, style_map=style_map, images_dir=images_dir, **kwargs)
    with open(out_txt_path, 'wb') as f:
        f.write(data)
    return report
