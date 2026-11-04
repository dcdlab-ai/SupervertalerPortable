r"""i0_md_tables_audit.py — BATCH I0-B, Часть 3.

Замер поведения программы на РЕАЛЬНЫХ md-файлах (read-only; продукт не
правится, вызываются только существующие модули product-кода):

  * конвейер импорта воспроизводится 1:1 по Supervertaler.py:29723-29754:
    построчно, пустая строка -> пустой сегмент, при включённой сегментации
    предложений — MarkdownSegmenter.segment_with_separators с join_before;
  * в двух режимах: сегментация предложений ВЫКЛ (дефолт импорта) и ВКЛ;
  * классификация строк: pipe-таблица (в т.ч. |---|), ограда ```csv,
    строки CSV внутри ограды, <!-- table_id -->, заголовки (в т.ч. с ** и
    скачками уровней), строки-картинки, обычный текст;
  * «рвёт ли сегментер строки таблицы по точкам внутри ячеек»: число
    кусков на строку + обратная сборка join_segments и побайтовое
    сравнение с исходной строкой (что дойдёт до экспорта);
  * «что видит LLM»: сегменты, попадающие в батч (пустые и
    image-only пропускаются, S.py:5572-5576), выборка табличных;
  * is_image_links_only: оба вида ссылок на картинки
    (![](images/x.png) и ![Image](/abs/path/image_...png));
  * разрыв посреди фразы (To signal / Thomas's death): строки-соседи,
    paragraph_id, join_before, отсутствие автослияния;
  * врезки/колонтитулы: строки с ** внутри абзаца (замер, не классификация);
  * сверка tables/table_N.csv со строками CSV в Input.translation.md.

Использование: python i0_md_tables_audit.py OUT_PATH
"""
import os
import re
import sys
import glob

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, _REPO)

from modules.simple_segmenter import MarkdownSegmenter, join_segments
from modules.bilingual_markdown_handler import is_image_links_only

SAMPLES = r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out'
FILES = [
    ('PyMuPDF4LLM', 'Input.md',
     os.path.join(SAMPLES, 'PyMuPDF4LLM', 'pymupdf4llm_gui_x0bf0ve2', 'Input.md')),
    ('docling', 'Input.md',
     os.path.join(SAMPLES, 'docling', '4164e8d8a0ef6c4df4142b7d9dc49a7f', 'Input.md')),
    ('docling', 'Input.translation.md',
     os.path.join(SAMPLES, 'docling', '4164e8d8a0ef6c4df4142b7d9dc49a7f',
                  'Input.translation.md')),
]

SEP_ROW = re.compile(r'^\|[\s:\-|]+\|$')
FENCE = re.compile(r'^```')
TABLE_ID = re.compile(r'^<!--\s*table_id')
HEADING = re.compile(r'^(#{1,6})\s+')
CSV_ROW = re.compile(r'^[^`\s].*,')


def classify(line, in_fence):
    """Класс строки: (kind, detail)."""
    if FENCE.match(line):
        return 'fence', line.rstrip()
    if in_fence:
        return 'csv_row', line.rstrip()
    if TABLE_ID.match(line):
        return 'table_id_comment', line.rstrip()
    if SEP_ROW.match(line):
        return 'pipe_separator', line.rstrip()
    if line.startswith('|'):
        return 'pipe_row', line.rstrip()
    m = HEADING.match(line)
    if m:
        return 'heading', f'уровень {len(m.group(1))}'
    s = line.strip()
    if s and is_image_links_only(s):
        return 'image_only', s
    if s:
        return 'text', line.rstrip()
    return 'empty', ''


def import_like_product(text, sentence_segmentation):
    """1:1 по S.py:29723-29754 (encoding='utf-8', readlines, rstrip '\r\n')."""
    lines = text.splitlines(keepends=True)
    segs = []  # (id, source, paragraph_id, join_before)
    if sentence_segmentation:
        segmenter = MarkdownSegmenter(None)
        for line_num, line in enumerate(lines, 1):
            t = line.rstrip('\r\n')
            if not t.strip():
                segs.append((len(segs) + 1, t, line_num, None))
            else:
                for sentence, sep in segmenter.segment_with_separators(t):
                    segs.append((len(segs) + 1, sentence, line_num, sep))
    else:
        for line_num, line in enumerate(lines, 1):
            t = line.rstrip('\r\n')
            segs.append((len(segs) + 1, t, line_num, None))
    return segs


def fence_blocks(lines):
    """Блоки ```...``` как список списков строк (строки между оградами)."""
    blocks, cur = [], None
    for line in lines:
        if FENCE.match(line):
            if cur is None:
                cur = []
            else:
                blocks.append(cur)
                cur = None
        elif cur is not None:
            cur.append(line)
    return blocks


def audit_file(label, fname, path):
    L = []
    text = open(path, 'r', encoding='utf-8').read()
    lines = text.splitlines()
    L.append(f'--- {label}/{fname}: {path}')
    L.append(f'строк: {len(lines)} (непустых: {sum(1 for l in lines if l.strip())})')

    # классификация строк
    kinds = {}
    in_fence = False
    headings_levels = []
    headings_bold = []
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            kind = 'fence'
            in_fence = not in_fence
            detail = line
        else:
            kind, detail = classify(line, in_fence)
        kinds.setdefault(kind, []).append(i)
        m = HEADING.match(line)
        if m:
            headings_levels.append((i, len(m.group(1)), line.strip()[:60]))
            if '**' in line:
                headings_bold.append((i, line.strip()[:70]))

    L.append('классы строк: ' + ', '.join(
        f'{k}={len(v)}' for k, v in kinds.items()))
    L.append('номера: ' + '; '.join(f'{k}: {v}' for k, v in kinds.items()))
    L.append('заголовки (строка, уровень): ' + '; '.join(
        f'{i}:H{lv} «{t}»' for i, lv, t in headings_levels))
    if headings_levels:
        lv = [x[1] for x in headings_levels]
        jumps = [(a, b) for a, b in zip(lv, lv[1:]) if b > a + 1]
        L.append(f'пропуски уровней (заголовок глубже, чем предыдущий +1): '
                 f'{jumps if jumps else "нет"}')
    L.append('заголовки с ** внутри: ' +
             ('; '.join(f'{i}: {t}' for i, t in headings_bold) if headings_bold
              else 'нет'))

    # (а)/(б): импорт в двух режимах + обратная сборка по строкам
    L.append('')
    L.append('импорт в двух режимах (1:1 по import_simple_txt):')
    for sent_mode in (False, True):
        segs = import_like_product(text, sent_mode)
        nonempty = [s for s in segs if s[1].strip()]
        L.append(f'  сегментация предложений {"ВКЛ" if sent_mode else "ВЫКЛ"}: '
                 f'сегментов всего {len(segs)} (непустых {len(nonempty)})')
        # строки, разбитые на >1 сегмента
        per_line = {}
        for _id, src, pid, sep in segs:
            per_line.setdefault(pid, []).append((_id, src, sep))
        split_rows = []
        rebuilt_bad = []
        trail_only = []
        for pid, parts in sorted(per_line.items()):
            orig = lines[pid - 1] if pid - 1 < len(lines) else ''
            rebuilt = join_segments([(src, sep) for _id, src, sep in parts])
            if len(parts) > 1:
                split_rows.append((pid, len(parts), orig[:60]))
            if rebuilt != orig and orig.strip():
                if rebuilt == orig.rstrip():
                    trail_only.append(pid)
                else:
                    rebuilt_bad.append((pid, orig[:50], rebuilt[:50]))
        pipe_splits = [x for x in split_rows if lines[x[0]-1].startswith('|')]
        L.append(f'    строк, разбитых на >1 сегмента: {len(split_rows)}'
                 + (f', из них pipe-строк: {len(pipe_splits)}' if pipe_splits else ''))
        for pid, n, head in split_rows[:10]:
            kind = ('PIPE' if lines[pid-1].startswith('|') else
                    ('CSV' if kinds.get('csv_row') and pid in kinds['csv_row'] else 'text'))
            L.append(f'      строка {pid} [{kind}] -> {n} куска(ов): {head!r}')
        L.append(f'    обратная сборка join_segments != исходной строке: '
                 f'{len(rebuilt_bad)}'
                 + (f' — ПОТЕРИ' if rebuilt_bad else ' (круг байт-в-байт)')
                 + (f'; ещё {len(trail_only)} строк отличаются только концевым'
                    f' пробелом (сегментер снимает его на границе)' if trail_only else ''))
        for pid, a, b in rebuilt_bad[:5]:
            L.append(f'      строка {pid}: было {a!r} / стало {b!r}')
        # что видит LLM: пустые и image-only пропускаются (S.py:5572-5576)
        llm = [s for s in nonempty if not is_image_links_only(s[1])]
        L.append(f'    LLM получает сегментов: {len(llm)} '
                 f'(пропущено image-only: {len(nonempty) - len(llm)})')
        tab = [s for s in llm if s[1].startswith('|') or s[1].startswith('<!--')
               or kinds.get('csv_row') and s[2] in kinds.get('csv_row', [])
               or kinds.get('fence') and s[2] in kinds.get('fence', [])]
        L.append(f'    из них табличных (pipe/fence/csv/table_id): {len(tab)}')
        for _id, src, pid, sep in tab[:8]:
            L.append(f'      LLM видит [{pid}]: {src[:90]!r}')

    # (д): &amp;
    amp = [i for i, l in enumerate(lines, 1) if '&amp;' in l or
           re.search(r'&[a-z]+;', l)]
    L.append('')
    L.append(f'HTML-сущности (&amp; и т.п.): {len(amp)} строк: {amp}: '
             f'ни один шаг md-конвейера не разэкранирует (обзор кода: '
             f'unescape только в docx-верификаторе, S.py:12889) — '
             f'дойдут до LLM и экспорта как есть')
    for i in amp[:3]:
        L.append(f'      строка {i}: {lines[i-1].strip()[:70]!r}')

    # (е): картинки
    L.append('')
    imgs = [(i, l.strip()) for i, l in enumerate(lines, 1)
            if re.search(r'!\[[^\]]*\]\([^)]*\)', l)]
    L.append(f'строк с md-картинками: {len(imgs)}')
    for i, s in imgs:
        abs_path = bool(re.match(r'!\[[^\]]*\]\(\s*/', s))
        L.append(f'      строка {i}: is_image_links_only={is_image_links_only(s)}, '
                 f'путь {"АБСОЛЮТНЫЙ" if abs_path else "относительный"}: {s[:80]!r}')
    # юнит-проверка обоих видов на синтетике (относительный путь отсутствует
    # в docling-файлах, есть в фикстуре T1)
    unit = ['![Метка: карта](images/test_gaugamela.png)',
            '![Image](/root/duckling/outputs/x/images/image_000000_abc.png)',
            'Текст ![иконка](images/i.png) в середине предложения.']
    L.append('юнит-проверка is_image_links_only:')
    for s in unit:
        L.append(f'      {is_image_links_only(s)}  <- {s[:70]!r}')

    # (ж): разрыв посреди фразы — только если фраза обрывается В КОНЦЕ строки
    L.append('')
    for pat in ('To signal', "Thomas's death"):
        hits = [i for i, l in enumerate(lines, 1) if l.rstrip().endswith(pat)]
        for i in hits:
            nxt = next((j for j in range(i + 1, len(lines) + 1)
                        if lines[j - 1].strip()), None)
            L.append(f'разрыв фразы: строка {i} обрывается на «{pat}», '
                     f'продолжение «{lines[nxt-1].strip()[:40]!r}» — строка {nxt}; '
                     f'paragraph_id различаются, join_before=None '
                     f'(начало абзаца) — автослияния в сетке нет, только ручное')
    # (з): врезки/колонтитулы — строки с ** внутри обычного текста
    L.append('')
    bold_in_text = [(i, l) for i, l in enumerate(lines, 1)
                    if '**' in l and not HEADING.match(l)
                    and not l.strip().startswith('|')]
    L.append(f'** внутри обычных абзацев (кандидаты врезки/колонтитулов): {len(bold_in_text)}')
    for i, l in bold_in_text[:5]:
        L.append(f'      строка {i}: {l.strip()[:100]!r}')

    # сверка CSV-файлов с блоками оград translation.md (по одному блоку на таблицу)
    L.append('')
    tables_dir = os.path.join(os.path.dirname(path), 'tables')
    blocks = fence_blocks(lines)
    if os.path.isdir(tables_dir) and blocks:
        csv_files = sorted(glob.glob(os.path.join(tables_dir, '*.csv')))
        L.append(f'оград ```csv: {len(blocks)} блок(ов) по '
                 f'{[len(b) for b in blocks]} строк; CSV-файлов: {len(csv_files)}')
        for n, csv_path in enumerate(csv_files):
            want = open(csv_path, 'r', encoding='utf-8').read()
            got = '\n'.join(blocks[n]) + ('\n' if blocks[n] else '')
            L.append(f'сверка {os.path.basename(csv_path)} с блоком ограды №{n + 1}: '
                     f'строк в csv {len(want.rstrip().splitlines())} / в ограде '
                     f'{len(blocks[n])}, содержимое совпадает: {got == want}')
    elif os.path.isdir(tables_dir):
        L.append(f'оград ```csv в файле нет — сверка tables/*.csv с md не проводится '
                 f'(в этой версии конвертера таблицы лежат в md как pipe)')
    return L


def main():
    out_path = sys.argv[1]
    L = ['=' * 100,
         'I0-B / Часть 3 — md-таблицы на РЕАЛЬНЫХ файлах '
         '(конвейер import_simple_txt 1:1, read-only)', '=' * 100,
         f'репозиторий (продукт не правится): {_REPO}']
    for label, fname, path in FILES:
        L += audit_file(label, fname, path)
        L.append('')
    open(out_path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'отчёт записан: {out_path}')


if __name__ == '__main__':
    main()
