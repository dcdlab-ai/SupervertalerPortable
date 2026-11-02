r"""i0_make_test_files.py — BATCH I0, Часть D.

Создаёт три минимальных файла InDesign Tagged Text (5–6+ синтетических
абзацев, русский текст, «ё», кавычки «», тире, жирный, курсив, метка
изображения, экранирование) в каталог out рядом с фикстурами:

  T1_*_verbose_utf16le_bom.txt  — Verbose,  UTF-16LE + BOM (FF FE)
  T2_*_verbose_utf8_bom.txt     — Verbose,  UTF-8 + BOM (EF BB BF)
  T3_*_abbrev_utf16le_bom.txt   — Abbreviated, UTF-16LE + BOM

Роли-стили: h1, h2, h3, p, li, img. Без Define*Style — тест проверяет,
создаёт ли InDesign стили по именам (см. отчёт I0, Часть C.2).

Использование: python i0_make_test_files.py [OUT_DIR]
"""
import sys
import os

PARAS_VERBOSE = [
    # (роль, текст) — теги Verbose добавляет генератор
    ('h1', 'Проверка импорта: глава «Великие битвы Александра»'),
    ('h2', 'Раздел: кириллица, буква «ё» и кавычки «ёлки»'),
    ('h3', 'Подзаголовок — с тире и многоточием…'),
    ('p', 'Обычный абзац: русский текст с «ё», кавычками «» и тире — '
          'проверка кодировки. Второе предложение: три, два, один…'),
    ('p', 'Абзац с <b>жирным выделением</b> в середине строки и обычным '
          'текстом после него.'),
    ('p', 'Абзац с <i>курсивным выделением</i> в середине строки.'),
    ('p', 'Абзац с экранированными символами: \\<угловая скобка\\>, '
          'обратный слэш \\\\ и точка с запятой\\;'),
    ('li', 'Первый пункт списка — с тире и «ё»'),
    ('li', 'Второй пункт списка: три, два, один…'),
    ('img', '![Метка: карта сражения Гавгамелы](images/test_gaugamela.png)'),
    ('p', 'Замыкающий абзац после метки изображения.'),
]

# Abbreviated использует те же тексты, но короткие имена тегов
TAG_V = {'para': 'ParaStyle', 'char': 'CharStyle'}
TAG_A = {'para': 'pstyle', 'char': 'cstyle'}


def build_lines(tags, texts):
    lines = []
    for role, text in texts:
        line = f'<{tags["para"]}:{role}>'
        # инлайн-разметка <b>/<i> -> CharStyle-спаны
        line += text.replace('<b>', f'<{tags["char"]}:Bold>') \
                    .replace('</b>', f'<{tags["char"]}:>') \
                    .replace('<i>', f'<{tags["char"]}:Italic>') \
                    .replace('</i>', f'<{tags["char"]}:>')
        lines.append(line)
    return lines


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else \
        r'E:\Dev\Work_temp\samples\indesign\out'
    os.makedirs(out_dir, exist_ok=True)

    header_v = '<UNICODE-WIN>\r\n<Version:16.4><FeatureSet:InDesign-Roman>'
    header_a = '<UNICODE-WIN>\r\n<vsn:16.4><fset:InDesign-Roman>'

    files = [
        ('T1_i0_verbose_utf16le_bom.txt', header_v, TAG_V, 'utf-16-le', True),
        ('T2_i0_verbose_utf8_bom.txt', header_v, TAG_V, 'utf-8', True),
        ('T3_i0_abbrev_utf16le_bom.txt', header_a, TAG_A, 'utf-16-le', True),
    ]
    for name, header, tags, enc, bom in files:
        body = header + '\r\n' + '\r\n'.join(build_lines(tags, PARAS_VERBOSE)) + '\r\n'
        data = body.encode(enc)
        if bom:
            data = (b'\xff\xfe' if enc == 'utf-16-le' else b'\xef\xbb\xbf') + data
        path = os.path.join(out_dir, name)
        with open(path, 'wb') as f:
            f.write(data)
        print(f'{path}: {len(data)} байт, {enc}, BOM={bom}')

    # самопроверка: обратное чтение
    import re
    for name, _, _, enc, bom in files:
        path = os.path.join(out_dir, name)
        raw = open(path, 'rb').read()
        if bom and enc == 'utf-16-le':
            assert raw[:2] == b'\xff\xfe', name
        if bom and enc == 'utf-8':
            assert raw[:3] == b'\xef\xbb\xbf', name
        text = raw.decode(enc)
        if bom:
            text = text.lstrip('\ufeff')
        paras = [l for l in text.split('\r\n') if l.startswith('<') and
                 (':h1>' in l or ':h2>' in l or ':h3>' in l or ':p>' in l or
                  ':li>' in l or ':img>' in l)]
        print(f'{name}: абзацев с ролью = {len(paras)} (ожидалось '
              f'{len(PARAS_VERBOSE)})')
        assert len(paras) == len(PARAS_VERBOSE), name


if __name__ == '__main__':
    main()
