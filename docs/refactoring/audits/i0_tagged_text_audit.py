#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""i0_tagged_text_audit.py — BATCH I0, Часть B.

Независимое измерение двух образцов InDesign Tagged Text
(экспорт InDesign 16.4, не пересохранённый): Form «Verbose» и «Abbreviated».

Только stdlib. Фикстуры читаются как данные (read-only), ничего не изменяет.

Использование:
    python i0_tagged_text_audit.py VERBOSE_PATH ABBREV_PATH OUT_PATH

Проверяем (по промпту I0, Часть B):
  * кодировка/BOM/CRLF (первые байты оригинала);
  * заголовок: Version/FeatureSet/ColorTable/Define*Style с разбором вложенных
    тегов и \-экранирования;
  * таблица «сокращённое имя тега → полное» (сопоставление двух форм);
  * совпадение текста обоих файлов (после декодирования и после снятия тегов);
  * инвентарь тегов и значений; перечень стилей с числом использований;
  * символы вёрстки (U+00AD, U+2011, NBSP, тонкие пробелы, <0x...>);
  * абзацы без ParaStyle в начале;
  * сверка с числами координатора (фиксированные ожидания — внизу).
"""
import sys
import re
import collections
import unicodedata

# ---------------------------------------------------------------- tokenizing

def decode_sample(path):
    """Читает файл как есть, возвращает (raw_bytes, bom_kind, text, eol_stats)."""
    raw = open(path, 'rb').read()
    if raw.startswith(b'\xff\xfe'):
        bom, text = 'UTF-16LE BOM (FF FE)', raw.decode('utf-16')
    elif raw.startswith(b'\xfe\xff'):
        bom, text = 'UTF-16BE BOM (FE FF)', raw.decode('utf-16')
    elif raw.startswith(b'\xef\xbb\xbf'):
        bom, text = 'UTF-8 BOM (EF BB BF)', raw.decode('utf-8-sig')
    elif raw[:2] in (b'<\x00', b'\x00<'):
        bom, text = 'НЕТ BOM; байты указывают на UTF-16LE' if raw[:1] == b'<' else \
                    'НЕТ BOM; байты указывают на UTF-16BE', raw.decode('utf-16-le')
        if raw[:1] == b'\x00':
            text = raw.decode('utf-16-be')
    elif raw[:6] == b'<UNICODE':
        bom, text = 'НЕТ BOM; UTF-8 (ASCII-заголовок)', raw.decode('utf-8')
    else:
        bom, text = 'НЕОПОЗНАНО', raw.decode('utf-8', errors='replace')
    eol = collections.Counter()
    eol['CRLF (\\r\\n)'] = text.count('\r\n')
    eol['одиночный LF'] = len(re.findall(r'(?<!\r)\n', text))
    eol['одиночный CR'] = len(re.findall(r'\r(?!\n)', text))
    return raw, bom, text, eol


def tokenize(text):
    r"""Разбирает поток на теги <...> и текст, учитывая \-экранирование.

    Возвращает список кортежей ('tag', inner) / ('text', chunk).
    inner — содержимое тега без внешних угловых скобок, \-экранирование
    сохранено как есть. Вложенные группы (ColorTable:=<...>, DefineX:Name=<...>)
    обрабатываются подсчётом глубины: '<' после '='/'<..' увеличивает глубину,
    '>' при глубине 1 закрывает тег.
    """
    out = []
    i, n = 0, len(text)
    buf = []
    while i < n:
        c = text[i]
        if c == '\\' and i + 1 < n:
            buf.append(text[i:i + 2])
            i += 2
            continue
        if c == '<':
            if buf:
                out.append(('text', ''.join(buf)))
                buf = []
            j, depth, inner = i + 1, 1, []
            while j < n and depth > 0:
                cj = text[j]
                if cj == '\\' and j + 1 < n:
                    inner.append(text[j:j + 2])
                    j += 2
                    continue
                if cj == '<':
                    depth += 1
                elif cj == '>':
                    depth -= 1
                    if depth == 0:
                        break
                inner.append(cj)
                j += 1
            if j >= n and depth > 0:
                # незакрытый '<' — откатываемся в текст
                buf.append(c)
                i += 1
                continue
            out.append(('tag', ''.join(inner)))
            i = j + 1
        else:
            buf.append(c)
            i += 1
    if buf:
        out.append(('text', ''.join(buf)))
    return out


TAG_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):(.*)$', re.S)


def parse_tag(inner):
    """'ParaStyle:H1' -> ('ParaStyle', 'H1'); без ':' -> (name, None)."""
    m = TAG_RE.match(inner)
    if m:
        return m.group(1), m.group(2)
    return inner, None


def unescape(s):
    r"""Снимает \-экранирование (символ после \ остаётся как есть)."""
    return re.sub(r'\\(.)', r'\1', s)

# ---------------------------------------------------------------- analysis

COLOR_HEADERS = {'Version': 'vsn', 'FeatureSet': 'fset', 'ColorTable': 'ctable'}
DEFINE_PREFIXES = ['DefineKinsokuStyle', 'DefineListStyle', 'DefineCharStyle',
                   'DefineParaStyle', 'DefineTextVariable']
DEFINE_ABBREV = {'dks', 'dls', 'dcs', 'dps', 'dtv'}
DEFINE_FULL = {'dks': 'DefineKinsokuStyle', 'dls': 'DefineListStyle',
               'dcs': 'DefineCharStyle', 'dps': 'DefineParaStyle',
               'dtv': 'DefineTextVariable'}


def split_header(tokens):
    """Тело начинается с первого тега ParaStyle/pstyle (каждый абзац объявляет
    стиль; сбросы атрибутов вида <pLeftIndent:> стоят УЖЕ после ParaStyle
    или перед ним только внутри абзаца — в начале файла их нет).
    Всё до первого ParaStyle — заголовок (UNICODE-WIN, Version/FeatureSet/
    ColorTable, Define*Style)."""
    header, body_start = [], None
    for idx, (kind, val) in enumerate(tokens):
        if kind != 'tag':
            continue
        name, _ = parse_tag(val)
        if name in ('ParaStyle', 'pstyle') and body_start is None:
            body_start = idx
            break
        header.append((idx, val))
    return header, body_start if body_start is not None else len(tokens)


def analyze(path, label):
    raw, bom, text, eol = decode_sample(path)
    tokens = tokenize(text)
    header, body_start = split_header(tokens)

    res = {'label': label, 'path': path, 'size': len(raw), 'bom': bom,
           'eol': eol, 'text_len': len(text), 'n_tokens': len(tokens),
           'body_start_token': body_start}

    # --- заголовок
    hdr_lines = []
    color_table_raw = None
    define_styles = []            # (kind, raw_name, body)
    for _, val in header:
        name, value = parse_tag(val)
        if name in ('UNICODE-WIN',):
            hdr_lines.append(('<UNICODE-WIN>', val))
        elif name in COLOR_HEADERS or name in COLOR_HEADERS.values():
            # полное или сокращённое имя одной из служебных строк заголовка
            full = {v: k for k, v in COLOR_HEADERS.items()}.get(name, name)
            hdr_lines.append((full, value))
            if full == 'ColorTable':
                color_table_raw = value
        elif name in DEFINE_PREFIXES or name in DEFINE_ABBREV:
            kind = DEFINE_FULL.get(name, name)
            if value is None:
                define_styles.append((kind, '', ''))
                continue
            if '<' in value:
                left, body = value.split('<', 1)
            else:
                left, body = value, ''
            sname = unescape(left.rstrip('=:'))
            define_styles.append((kind, sname, body))
    res['header'] = hdr_lines
    res['define_styles'] = define_styles

    if color_table_raw:
        colors = re.findall(r'<((?:[^<>]|\\.)+):COLOR:', color_table_raw)
        res['colors'] = [unescape(c) for c in colors]

    # --- тело
    body = tokens[body_start:]
    res['body_tokens'] = len(body)
    tag_counter = collections.Counter()
    tag_value_counter = collections.Counter()      # (name, value) -> count
    text_chunks = []
    para_styles = collections.Counter()            # стиль -> число абзацев
    para_first_tag_ok = 0
    para_first_tag_bad = []                        # абзацы без ParaStyle первой
    para_count = 0
    charstyle_counts = collections.Counter()
    open_close = collections.Counter()             # (name, value, position open/close)

    # разбиение на абзацы: параграф-маркер = CRLF в текстовом куске
    # (одиночные LF/CR внутри текста абзац не рвут — они остаются в тексте).
    paras = []
    cur = []
    for kind, val in body:
        if kind == 'text' and '\r\n' in val:
            parts = val.split('\r\n')
            for k, p in enumerate(parts):
                if p:
                    cur.append(('text', p))
                if k < len(parts) - 1:
                    paras.append(cur)      # cur может быть пустым = пустой абзац
                    cur = []
        else:
            cur.append((kind, val))
    if cur:
        paras.append(cur)
    res['paras_raw'] = len(paras)

    for p_idx, para in enumerate(paras):
        if not para:
            res.setdefault('empty_para_idx', []).append(p_idx)
            para_count += 1
            continue
        para_count += 1
        for kind, val in para:
            if kind == 'text':
                if val:
                    text_chunks.append(val)
                continue
            name, value = parse_tag(val)
            tag_counter[name] += 1
            tag_value_counter[(name, value)] += 1
            if name in ('ParaStyle', 'pstyle'):
                para_styles[unescape(value or '')] += 1
            if name == 'CharStyle':
                cs = unescape(value or '')
                if cs:
                    charstyle_counts[cs] += 1
            open_close[(name, value)] += 1
        if para[0][0] == 'tag' and parse_tag(para[0][1])[0] in ('ParaStyle', 'pstyle'):
            para_first_tag_ok += 1
        else:
            lead_tags = [parse_tag(v)[0] for k, v in para[:6] if k == 'tag']
            para_first_tag_bad.append((p_idx, lead_tags))
            has_ps_later = any(parse_tag(v)[0] in ('ParaStyle', 'pstyle')
                               for k, v in para if k == 'tag')
            para_first_tag_bad[-1] = (p_idx, lead_tags, has_ps_later)

    res['para_count'] = para_count
    res['para_styles'] = para_styles
    res['para_first_tag_ok'] = para_first_tag_ok
    res['para_first_tag_bad'] = para_first_tag_bad
    res['tag_counter'] = tag_counter
    res['tag_value_counter'] = tag_value_counter
    res['charstyle_counts'] = charstyle_counts
    res['text_chars'] = ''.join(text_chunks)

    # --- символы вёрстки
    tc = res['text_chars']
    res['layout_chars'] = {
        'U+00AD мягкий перенос (SOFT HYPHEN)': tc.count('\u00ad'),
        'U+2011 неразрывный дефис': tc.count('\u2011'),
        'U+00A0 NBSP': tc.count('\u00a0'),
        'U+2009 тонкий пробел': tc.count('\u2009'),
        'U+202F узкий NBSP': tc.count('\u202f'),
        'U+2014 тире (EM DASH)': tc.count('\u2014'),
        'U+00AB/BB « »': tc.count('\u00ab'),
        'U+2026 многоточие': tc.count('\u2026'),
    }
    res['hex_tags'] = sum(v for (n, _), v in tag_value_counter.items()
                          if re.fullmatch(r'0x[0-9A-Fa-f]+', n or ''))

    # --- одиночные LF внутри абзацев (в тексте)
    res['embedded_lf_in_text'] = tc.count('\n')
    return res, tokens


def strip_tags_from_text(text):
    """Текст без тегов (для сравнения содержимого двух форм)."""
    tokens = tokenize(text)
    return ''.join(v for k, v in tokens if k == 'text')


def main():
    v_path, a_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    rv, tv = analyze(v_path, 'VERBOSE (GBoH-...-v2.txt)')
    ra, ta = analyze(a_path, 'ABBREVIATED (GBoH-...-v2-.txt)')

    L = []
    P = L.append
    P('=' * 100)
    P('I0 / Часть B — аудит образцов InDesign Tagged Text')
    P('=' * 100)

    for r in (rv, ra):
        P('')
        P(f"--- {r['label']}: {r['path']}")
        P(f"размер файла: {r['size']} байт; BOM: {r['bom']}")
        P(f"EOL: {dict(r['eol'])}")
        P(f"символов после декодирования: {r['text_len']}; токенов: {r['n_tokens']}")
        P('')
        P('ЗАГОЛОВОК:')
        for name, val in r['header']:
            if name in ('Version', 'vsn', 'FeatureSet', 'fset'):
                P(f"  <{name}:{val}>")
        colors = r.get('colors') or []
        P(f"  ColorTable: {len(colors)} цветов: {colors}")
        P(f"  Define*Style определений: {len(r['define_styles'])}")
        by_kind = collections.Counter(k for k, _, _ in r['define_styles'])
        for k, c in sorted(by_kind.items()):
            P(f"    {k}: {c}")
        for k, name, body in r['define_styles']:
            # короткие атрибуты определения
            attrs = re.findall(r'<([A-Za-z_]+):((?:[^<>]|\\.)*)>', body)
            keys = ', '.join(sorted({a for a, _ in attrs}))
            P(f"    {k} «{name}»: {len(body)} симв.; атрибуты: {keys}")
        P('')
        P('АБЗАЦЫ:')
        P(f"  абзацев (по CRLF): {r['para_count']}  (пустых: {len(r.get('empty_para_idx', []))})")
        P(f"  абзацев, начинающихся с ParaStyle-тега: {r['para_first_tag_ok']}")
        bad = r['para_first_tag_bad']
        P(f"  абзацев БЕЗ ParaStyle первым тегом: {len(bad)}")
        for idx, lead, has_later in bad[:10]:
            P(f"    абзац #{idx}: первые теги {lead}; ParaStyle дальше в абзаце: {has_later}")
        P('')
        P('СТИЛИ АБЗАЦЕВ (ParaStyle -> число абзацев):')
        for s, c in r['para_styles'].most_common():
            P(f"    {s}: {c}")
        P('')
        P('СИМВОЛЬНЫЕ СТИЛИ (CharStyle:X -> открытий):')
        for s, c in r['charstyle_counts'].most_common():
            P(f"    {s}: {c}")
        P('')
        P('ИНВЕНТАРЬ ТЕГОВ ТЕЛА (имя -> число вхождений):')
        for n, c in r['tag_counter'].most_common():
            P(f"    {n}: {c}")
        P(f"  ВСЕГО тегов тела: {sum(r['tag_counter'].values())}")
        P('')
        P('СИМВОЛЫ ВЁРСТКИ (в тексте без тегов):')
        for k, v in r['layout_chars'].items():
            P(f"    {k}: {v}")
        P(f"  тегов вида <0x...>: {r['hex_tags']}")
        P(f"  одиночных LF внутри текста абзацев: {r['embedded_lf_in_text']}")

    # --- сравнение форм
    P('')
    P('=' * 100)
    P('СРАВНЕНИЕ ФОРМ')
    P(f"  байты совпадают: {open(v_path,'rb').read() == open(a_path,'rb').read()}")
    v_text = open(v_path, 'rb').read().decode('utf-16-le')
    a_text = open(a_path, 'rb').read().decode('utf-16-le')
    P(f"  декодированный текст (UTF-16LE) совпадает целиком: {v_text == a_text}")
    v_stripped = strip_tags_from_text(v_text)
    a_stripped = strip_tags_from_text(a_text)
    P(f"  текст без тегов совпадает: {v_stripped == a_stripped}"
      f"  (verbose {len(v_stripped)} симв., abbrev {len(a_stripped)} симв.)")
    if v_stripped != a_stripped:
        for i in range(min(len(v_stripped), len(a_stripped))):
            if v_stripped[i] != a_stripped[i]:
                P(f"  первое расхождение в позиции {i}: "
                  f"verbose {v_stripped[i-30:i+30]!r} vs abbrev {a_stripped[i-30:i+30]!r}")
                break

    # --- таблица сокращённое -> полное
    P('')
    P('ТАБЛИЦА «СОКРАЩЁННОЕ ИМЯ -> ПОЛНОЕ» (сопоставление потоков тегов)')
    v_stream = [parse_tag(v)[0] for k, v in tv if k == 'tag']
    a_stream = [parse_tag(v)[0] for k, v in ta if k == 'tag']
    P(f"  длина потока тегов: verbose {len(v_stream)}, abbreviated {len(a_stream)}; "
      f"равна: {len(v_stream) == len(a_stream)}")
    # заголовок тоже входит в поток — он тоже параллелен (vsn/fset/ctable/dps…)
    mapping = {}
    inconsistent = []
    for vm, am in zip(v_stream, a_stream):
        if mapping.setdefault(vm, am) != am:
            if am not in inconsistent:
                inconsistent.append(am)
            mapping[vm] = f"{mapping[vm]}/{am}"
    # согласованность: каждый сокращённый тег должен отображаться ровно в одно полное
    rev = {}
    for vm, am in mapping.items():
        rev.setdefault(am, set()).add(vm)
    P(f"  отображение взаимно однозначно: "
      f"{all(len(s) == 1 for s in rev.values())}")
    if inconsistent:
        P(f"  НЕОДНОЗНАЧНЫЕ соответствия: {inconsistent}")
    P('  соответствие (verbose -> abbreviated, число вхождений в verbose):')
    for vm, am in sorted(mapping.items(), key=lambda x: -rv['tag_counter'].get(x[0].split('/')[0], 0)):
        cnt = rv['tag_counter'].get(vm.split('/')[0], 0)
        P(f"    {vm} -> {am} ({cnt})")

    # --- сверка с числами координатора
    P('')
    P('=' * 100)
    P('СВЕРКА С ЧИСЛАМИ КООРДИНАТОРА')
    checks = [
        ('абзацев', 907, rv['para_count']),
        ('тегов тела (verbose)', 32783, sum(rv['tag_counter'].values())),
        ('cNoBreak (verbose)', 27794, rv['tag_counter'].get('cNoBreak', 0)),
        ('U+00AD мягкий перенос', 259, rv['layout_chars']['U+00AD мягкий перенос (SOFT HYPHEN)']),
        ('U+2011 неразрывный дефис', 23, rv['layout_chars']['U+2011 неразрывный дефис']),
        ('U+00A0 NBSP', 0, rv['layout_chars']['U+00A0 NBSP']),
        ('CharStyle Bold', 213, rv['charstyle_counts'].get('Bold', 0)),
        ('CharStyle Italic', 6, rv['charstyle_counts'].get('Italic', 0)),
        ('CharStyle BoldItalic', 4, rv['charstyle_counts'].get('BoldItalic', 0)),
        ('CharStyle myHorizontalScaleForEmDashSpaceBefore',
         167, rv['charstyle_counts'].get('myHorizontalScaleForEmDashSpaceBefore', 0)),
        ('CharStyle myHorizontalScaleForEmDashSpaceAfter',
         168, rv['charstyle_counts'].get('myHorizontalScaleForEmDashSpaceAfter', 0)),
        ('U+2014 тире', 168, rv['layout_chars']['U+2014 тире (EM DASH)']),
    ]
    for name, expected, got in checks:
        mark = 'OK ' if expected == got else ('~  ' if abs(expected - got) <= max(3, expected // 100) else 'РАСХОЖДЕНИЕ')
        P(f"  [{mark}] {name}: координатор {expected}, измерено {got}")

    out = open(out_path, 'w', encoding='utf-8')
    out.write('\n'.join(L) + '\n')
    out.close()
    print(f"отчёт записан: {out_path}")


if __name__ == '__main__':
    main()
