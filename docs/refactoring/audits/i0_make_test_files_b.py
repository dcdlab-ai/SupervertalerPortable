r"""i0_make_test_files_b.py — BATCH I0-B/I0-C, микротесты.

I0-B (файлы T4, T5, T6 — T6 больше НЕ генерируется: ронял InDesign,
синтаксис таблиц CS2 не работает; см. эталон в s11.8 отчёта):

  T4_i0_definestyle_names_utf16le_bom.txt — Define*Style только по именам.
  T5_i0_backslash_matrix_utf16le_bom.txt — матрица обратного слэша.

I0-C (результаты T4/T5/T6 у Дмитрия; новые файлы):

  T4b1_i0_header_oneline_utf16le_bom.txt — ВСЕ теги шапки и Define*Style
      в ОДНОЙ строке (без CRLF между ними), один CRLF после шапки.
  T4b2_i0_header_gboh_utf16le_bom.txt   — шапка в точной структуре
      заголовка образца GBoH: <UNICODE-WIN> отдельной строкой, вторая
      строка <Version>+<FeatureSet>+<ColorTable> (строка 2 образца
      дословно), затем по одному Define*Style на строку; разделители CRLF.
      Bold/Italic/BoldItalic определены С АТРИБУТАМИ из образца
      (<cTypeface:…>), без BasedOn и без шумовых атрибутов.
  T5b_i0_value_escapes_utf16le_bom.txt  — изолированные конструкции:
      контроли \\ и \\<, затем \; \: \, \= в ТЕКСТЕ (по одному на абзац,
      с подписью), плюс <CharStyle:Группа\\:Стиль>…<CharStyle:>.
  T6b_i0_table_from_reference_utf16le_bom.txt — таблица 3×3 с шапкой
      по ЭТАЛОНУ реального экспорта InDesign 16.4 (не по спецификации CS2):
      <TableStyle:\[Basic Table\]><TableStart:3,3:1:0<tCellDefaultCellType:Text>>
      <ColStart:<tColAttrWidth:…>>×3, <RowStart:<tRowAttrHeight:…>>,
      <CellStyle:\[None\]><StylePriority:0><CellStart:1,1>…<CellEnd:>,
      <RowEnd:>, <TableEnd:> (см. s11.8 отчёта).

Файлы — только в out/ (вне git). Самопроверка: обратное чтение, BOM,
число абзацев, наличие всех тестируемых конструкций.

Использование: python i0_make_test_files_b.py [OUT_DIR]
"""
import sys
import os
import hashlib

OUT_DEFAULT = r'E:\Dev\Work_temp\samples\indesign\out'

# ---------- T4: Define*Style только по именам ----------

DEFINE_HEADER = [
    '<DefineParaStyle:h1=<Nextstyle:h1>>',
    '<DefineParaStyle:h2=<Nextstyle:h2>>',
    '<DefineParaStyle:h3=<Nextstyle:h3>>',
    '<DefineParaStyle:p=<Nextstyle:p>>',
    '<DefineParaStyle:li=<Nextstyle:li>>',
    '<DefineParaStyle:img=<Nextstyle:img>>',
    '<DefineCharStyle:Bold=<Nextstyle:Bold>>',
    '<DefineCharStyle:Italic=<Nextstyle:Italic>>',
]

# I0-C: параграфные определения T4b (без символьных — они ниже с атрибутами)
DEFINE_HEADER_PARA = DEFINE_HEADER[:6]

T4_PARAS = [
    ('h1', 'Проверка Define*Style по именам: глава «Гавгамела»'),
    ('h2', 'Раздел: кириллица, «ё», кавычки «»'),
    ('h3', 'Подзаголовок — тире и многоточие…'),
    ('p', 'Обычный абзац: если этот текст принял стиль «p», определения '
          'по именам сработали.'),
    ('p', 'Абзац с <b>жирным куском</b> внутри — стиль Bold из шапки.'),
    ('p', 'Абзац с <i>курсивным куском</i> внутри — стиль Italic из шапки.'),
    ('li', 'Пункт списка стиля «li»'),
    ('img', '![Метка: карта сражения Гавгамелы](images/test_gaugamela.png)'),
    ('p', 'Замыкающий абзац.'),
]


def to_charstyle(text):
    """<b>/<i> -> <CharStyle:…>…<CharStyle:>."""
    return (text.replace('<b>', '<CharStyle:Bold>')
                .replace('</b>', '<CharStyle:>')
                .replace('<i>', '<CharStyle:Italic>')
                .replace('</i>', '<CharStyle:>'))


def build_t4():
    lines = ['<UNICODE-WIN>', '<Version:16.4><FeatureSet:InDesign-Roman>']
    lines += DEFINE_HEADER
    for role, text in T4_PARAS:
        lines.append(f'<ParaStyle:{role}>' + to_charstyle(text))
    return '\r\n'.join(lines) + '\r\n'


# ---------- T5: матрица обратного слэша + стиль в группе ----------
# Подписи в скобках показывают, ЧТО записано в файле (как видно в редакторе).

T5_LINES = [
    '<ParaStyle:p>Вариант 1 (в файле записано два слэша: слэш слэш): '
    'текст со слэшем \\\\ после слова и конец.',
    '<ParaStyle:p>Вариант 2 (в файле записано четыре слэша: слэш слэш слэш слэш): '
    'текст со слэшами \\\\\\\\ после слова и конец.',
    '<ParaStyle:p>Вариант 3 (в файле записан спецсимвол 0x005C): '
    'текст со спецсимволом <0x005C> после слова и конец.',
    '<ParaStyle:p>Вариант 4 (в файле записано слэш-меньше): '
    'текст со скобкой \\< меньшек после слова и конец.',
    '<ParaStyle:p>Вариант 5 (в файле записано слэш-больше): '
    'текст со скобкой \\> большек после слова и конец.',
    '<ParaStyle:p>Вариант 6 (в файле записано слэш-слэш в самом конце строки): '
    'слэш в конце строки \\\\',
    '<ParaStyle:Группа\\:Стиль>Вариант 7 — стиль в группе: если этот абзац '
    'принял стиль «Стиль» из группы «Группа», синтаксис Группа\\:Стиль верен.',
    '<ParaStyle:p>Замыкающий абзац.',
]


def build_t5():
    lines = ['<UNICODE-WIN>', '<Version:16.4><FeatureSet:InDesign-Roman>']
    lines += T5_LINES
    return '\r\n'.join(lines) + '\r\n'


# ---------- T6: таблица 3×3 с шапкой по спецификации ----------
# Спецификация (Adobe InDesign CS2 User Guide, гл. Tagged Text, стр. 15):
#   <TableStart:numRows,numCols:numHeaderRows:numFooterRows>, <TableEnd>,
#   <RowStart>/<RowEnd>, <CellStart:row,col>/<CellEnd>; пример <cStart:1,1>
#   (нумерация строк/столбцов с 1). Таблица целиком на ОДНОЙ строке файла,
#   чтобы CRLF не создавал абзацев внутри ячеек.

T6_INTRO = ('<ParaStyle:p>Перед таблицей: шапка должна состоять из трёх ячеек '
            'первой строки (Заголовок A/B/C).')

T6_TABLE = (
    '<ParaStyle:p><TableStart:3,3:1:0>'
    '<rStart>'
    '<cStart:1,1><ParaStyle:p>Заголовок A<cEnd>'
    '<cStart:1,2><ParaStyle:p>Заголовок B<cEnd>'
    '<cStart:1,3><ParaStyle:p>Заголовок C<cEnd>'
    '<rEnd>'
    '<rStart>'
    '<cStart:2,1><ParaStyle:p>Ячейка с <CharStyle:Bold>жирным<CharStyle:> куском<cEnd>'
    '<cStart:2,2><ParaStyle:p>Значение: 3,14 (запятая внутри ячейки)<cEnd>'
    '<cStart:2,3><ParaStyle:p>Кавычки «ё» и тире — в ячейке<cEnd>'
    '<rEnd>'
    '<rStart>'
    '<cStart:3,1><ParaStyle:p>Победитель<cEnd>'
    '<cStart:3,2><ParaStyle:p>Поражение<cEnd>'
    '<cStart:3,3><ParaStyle:p>Ничья<cEnd>'
    '<rEnd>'
    '<TableEnd>'
)

T6_OUTRO = ('<ParaStyle:p>После таблицы: если таблица собралась 3×3 и текст '
            'после неё стал абзацем, синтаксис верен.')


def build_t6():
    lines = ['<UNICODE-WIN>', '<Version:16.4><FeatureSet:InDesign-Roman>',
             T6_INTRO, T6_TABLE, T6_OUTRO]
    return '\r\n'.join(lines) + '\r\n'


# ---------- I0-C: T4b1 / T4b2 / T5b / T6b ----------

# символьные стили С АТРИБУТАМИ из образца (cTypeface), без BasedOn и шума;
# в эталоне таблиц ровно так: <DefineCharStyle:Bold=<Nextstyle:Bold><cTypeface:Bold>>
CHAR_DEFS_ATTR = [
    '<DefineCharStyle:Bold=<Nextstyle:Bold><cTypeface:Bold>>',
    '<DefineCharStyle:Italic=<Nextstyle:Italic><cTypeface:Italic>>',
    '<DefineCharStyle:BoldItalic=<Nextstyle:BoldItalic><cTypeface:Bold Italic>>',
]

# строка 2 шапки образца GBoH дословно (Version+FeatureSet+ColorTable)
GBOH_LINE2 = ('<Version:16.4><FeatureSet:InDesign-Roman><ColorTable:='
              '<Black:COLOR:CMYK:Process:0,0,0,1>'
              '<C\\=15 M\\=100 Y\\=100 K\\=0:COLOR:CMYK:Process:0.15,1,1,0>'
              '<Paper:COLOR:CMYK:Process:0,0,0,0>'
              '<C\\=0 M\\=0 Y\\=0 K\\=90:COLOR:CMYK:Process:0,0,0,0.9>'
              '<C\\=100 M\\=0 Y\\=0 K\\=0:COLOR:CMYK:Process:1,0,0,0>'
              '<C\\=8 M\\=10 Y\\=18 K\\=0:COLOR:CMYK:Process:0.08,0.1,0.18,0>'
              '<Word\\_R0\\_G0\\_B0:COLOR:RGB:Process:0,0,0>>')


def build_t4b1():
    """Все теги шапки и Define*Style подряд без CRLF, один CRLF после шапки."""
    head = ('<UNICODE-WIN><Version:16.4><FeatureSet:InDesign-Roman>'
            + ''.join(DEFINE_HEADER_PARA) + ''.join(CHAR_DEFS_ATTR))
    lines = [head] + [f'<ParaStyle:{r}>' + to_charstyle(t)
                      for r, t in T4_PARAS]
    return '\r\n'.join(lines) + '\r\n'


def build_t4b2():
    """Шапка в точной структуре образца GBoH (по байтам: CRLF между строками,
    <UNICODE-WIN> отдельно, Version+FeatureSet+ColorTable одной строкой,
    далее по одному Define*Style на строку)."""
    lines = ['<UNICODE-WIN>', GBOH_LINE2]
    lines += DEFINE_HEADER_PARA + CHAR_DEFS_ATTR
    lines += [f'<ParaStyle:{r}>' + to_charstyle(t) for r, t in T4_PARAS]
    return '\r\n'.join(lines) + '\r\n'


# T5b: каждая конструкция в своём абзаце с подписью; контроли первыми.
T5B_LINES = [
    '<ParaStyle:p>Контроль 1 (в файле записано два слэша): '
    'текст со слэшем \\\\ после слова и конец.',
    '<ParaStyle:p>Контроль 2 (в файле записано слэш-меньше): '
    'текст со скобкой \\< после слова и конец.',
    '<ParaStyle:p>Вариант 3 (в файле записано слэш и точка с запятой): '
    'текст со знаком \\; после слова и конец.',
    '<ParaStyle:p>Вариант 4 (в файле записано слэш и двоеточие): '
    'текст со знаком \\: после слова и конец.',
    '<ParaStyle:p>Вариант 5 (в файле записано слэш и запятая): '
    'текст со знаком \\, после слова и конец.',
    '<ParaStyle:p>Вариант 6 (в файле записано слэш и знак равенства): '
    'текст со знаком \\= после слова и конец.',
    '<ParaStyle:p>Вариант 7 — символьный стиль из группы (в файле тег со '
    'слэшем-двоеточием в значении): этот кусок в стиле '
    '<CharStyle:Группа\\:Стиль>Группа-Стиль<CharStyle:> — если кусок '
    '«Группа-Стиль» принял символьный стиль «Стиль» из группы «Группа», '
    'синтаксис значения верен.',
    '<ParaStyle:p>Замыкающий абзац.',
]


def build_t5b():
    lines = ['<UNICODE-WIN>', '<Version:16.4><FeatureSet:InDesign-Roman>']
    lines += T5B_LINES
    return '\r\n'.join(lines) + '\r\n'


# T6b — строго по эталону реального экспорта (s11.8): имена тегов Verbose,
# атрибуты внутри угловых скобок ОТКРЫВАЮЩЕГО тега (закрывающая скобка одна,
# в конце), ячейка = CellStyle + StylePriority + CellStart:1,1 + ParaStyle +
# текст + CellEnd:; все строки таблицы на ОДНОЙ строке файла.
T6B_INTRO = ('<ParaStyle:p>Перед таблицей: шапка — первая строка '
             '(Заголовок A/B/C), во второй строке одна жирная ячейка.')

T6B_TABLE = (
    '<ParaStyle:p>'
    '<TableStyle:\\[Basic Table\\]>'
    '<TableStart:3,3:1:0<tCellDefaultCellType:Text>>'
    '<ColStart:<tColAttrWidth:84.37795275587534>>'
    '<ColStart:<tColAttrWidth:84.37795275587534>>'
    '<ColStart:<tColAttrWidth:84.37795275587534>>'
    + ''.join(
        '<RowStart:<tRowAttrHeight:15.209930419921875>>'
        + ''.join(
            '<CellStyle:\\[None\\]><StylePriority:0><CellStart:1,1>'
            '<ParaStyle:p>'
            + ('<CharStyle:Bold>' if (row, col) == (2, 1) else '')
            + cell
            + ('<CharStyle:>' if (row, col) == (2, 1) else '')
            + '<CellEnd:>'
            for col, cell in enumerate(row_cells, 1))
        + '<RowEnd:>'
        for row, row_cells in enumerate([
            ['Заголовок A', 'Заголовок B', 'Заголовок C'],
            ['Ячейка с жирным куском', 'Значение: 3,14', 'Кавычки «ё» и тире'],
            ['Победитель', 'Поражение', 'Ничья'],
        ], 1))
    + '<TableEnd:>'
)

T6B_OUTRO = ('<ParaStyle:p>После таблицы: если таблица собралась 3×3 с шапкой '
             'и текст после неё стал абзацем, эталонный синтаксис верен.')


def build_t6b():
    """UTF-16LE + BOM, CRLF — как эталон, но BOM и CRLF (проверено T1/T4/T5).
    Шапка: определения, которые использует таблица (стиль p, Bold,
    пустое определение встроенного [Basic Table] — как в эталоне)."""
    lines = ['<UNICODE-WIN>', '<Version:16.4><FeatureSet:InDesign-Roman>',
             '<DefineParaStyle:p=<Nextstyle:p>>',
             '<DefineCharStyle:Bold=<Nextstyle:Bold><cTypeface:Bold>>',
             '<DefineTableStyle:\\[Basic Table\\]=>',
             T6B_INTRO, T6B_TABLE, T6B_OUTRO]
    return '\r\n'.join(lines) + '\r\n'


# ---------- запись + самопроверка ----------

def write_file(out_dir, name, body):
    data = b'\xff\xfe' + body.encode('utf-16-le')
    path = os.path.join(out_dir, name)
    with open(path, 'wb') as f:
        f.write(data)
    h = hashlib.sha256(data).hexdigest()
    print(f'{path}: {len(data)} байт, UTF-16LE+BOM, sha256(файл)={h}')
    return path


def verify(out_dir):
    ok = True
    # T4
    raw = open(os.path.join(out_dir, 'T4_i0_definestyle_names_utf16le_bom.txt'),
               'rb').read()
    text = raw[2:].decode('utf-16-le')
    assert raw[:2] == b'\xff\xfe'
    n_para = text.count('<ParaStyle:')
    assert n_para == len(T4_PARAS), f'T4: абзацев {n_para}, ожидалось {len(T4_PARAS)}'
    for d in DEFINE_HEADER:
        assert d in text, f'T4: нет {d}'
    assert '<CharStyle:Bold>' in text and '<CharStyle:Italic>' in text
    n_bold = text.count('<CharStyle:Bold>')
    n_italic = text.count('<CharStyle:Italic>')
    n_close = text.count('<CharStyle:>')
    assert n_bold + n_italic == n_close, \
        f'T4: спанов {n_bold + n_italic} != закрытий {n_close}'
    print(f'T4 OK: {n_para} абзацев, Define*Style: {len(DEFINE_HEADER)}, '
          f'CharStyle-спанов: {n_bold + text.count("<CharStyle:Italic>")}')
    # T5
    raw = open(os.path.join(out_dir, 'T5_i0_backslash_matrix_utf16le_bom.txt'),
               'rb').read()
    text = raw[2:].decode('utf-16-le')
    assert raw[:2] == b'\xff\xfe'
    for seq in ['\\\\', '\\\\\\\\', '<0x005C>', '\\<', '\\>']:
        assert seq in text, f'T5: нет последовательности {seq!r}'
    assert '<ParaStyle:Группа\\:Стиль>' in text, 'T5: нет тега группы'
    n_para = text.count('<ParaStyle:')
    assert n_para == len(T5_LINES), f'T5: абзацев {n_para}, ожидалось {len(T5_LINES)}'
    print(f'T5 OK: {n_para} абзацев, все 5 слэш-вариантов + группа на месте')
    # T6
    raw = open(os.path.join(out_dir, 'T6_i0_table_3x3_utf16le_bom.txt'),
               'rb').read()
    text = raw[2:].decode('utf-16-le')
    assert raw[:2] == b'\xff\xfe'
    assert '<TableStart:3,3:1:0>' in text
    assert text.count('<TableStart') == 1 and text.count('<TableEnd') == 1
    assert text.count('<rStart>') == 3 and text.count('<rEnd>') == 3
    assert text.count('<cStart:') == 9 and text.count('<cEnd>') == 9
    assert text.count('<CharStyle:Bold>') == 1
    # таблица на одной строке: внутри строки с таблицей нет CRLF
    for line in text.split('\r\n'):
        if '<TableStart' in line:
            assert '<TableEnd>' in line, 'T6: таблица разорвана по строкам'
            assert line.count('\n') == 0
    print('T6 OK: TableStart:3,3:1:0, 3 строки, 9 ячеек, 1 жирный кусок, '
          'таблица на одной строке')
    return ok


def verify_i0c(out_dir):
    # T4b1
    raw = open(os.path.join(out_dir, 'T4b1_i0_header_oneline_utf16le_bom.txt'),
               'rb').read()
    text = raw[2:].decode('utf-16-le')
    assert raw[:2] == b'\xff\xfe'
    first, rest = text.split('\r\n', 1)
    assert first.startswith('<UNICODE-WIN><Version:16.4>')
    assert first.count('<DefineParaStyle:') == 6
    assert first.count('<DefineCharStyle:') == 3
    assert '<cTypeface:Bold Italic>' in first
    assert '<BasedOn:' not in first, 'T4b1: BasedOn запрещён условием задачи'
    assert rest.count('<ParaStyle:') == len(T4_PARAS)
    print(f'T4b1 OK: шапка одной строкой ({len(first)} симв., 9 определений), '
          f'{len(T4_PARAS)} абзацев')
    # T4b2
    raw = open(os.path.join(out_dir, 'T4b2_i0_header_gboh_utf16le_bom.txt'),
               'rb').read()
    text = raw[2:].decode('utf-16-le')
    assert raw[:2] == b'\xff\xfe'
    lines = text.split('\r\n')
    assert lines[0] == '<UNICODE-WIN>'
    assert lines[1] == GBOH_LINE2, 'T4b2: строка 2 не совпала с образцом GBoH'
    assert all(l.count('<Define') == 1 for l in lines[2:11]), \
        'T4b2: не по одному определению на строку'
    assert '<cTypeface:Bold>' in text and '<BasedOn:' not in text
    assert text.count('<ParaStyle:') == len(T4_PARAS)
    print(f'T4b2 OK: структура GBoH ({len(lines)} строк шапки+тела), '
          'ColorTable образца дословно, char-стили с cTypeface')
    # T5b
    raw = open(os.path.join(out_dir, 'T5b_i0_value_escapes_utf16le_bom.txt'),
               'rb').read()
    text = raw[2:].decode('utf-16-le')
    assert raw[:2] == b'\xff\xfe'
    for seq in ['\\\\', '\\<', '\\;', '\\:', '\\,', '\\=']:
        assert seq in text, f'T5b: нет {seq!r}'
    assert '<CharStyle:Группа\\:Стиль>' in text and text.count('<CharStyle:>') == 1
    assert text.count('<ParaStyle:') == len(T5B_LINES)
    assert '<0x005C>' not in text
    print(f'T5b OK: {len(T5B_LINES)} абзацев, контроли + 4 варианта в тексте + '
          'символьная группа')
    # T6b
    raw = open(os.path.join(out_dir, 'T6b_i0_table_from_reference_utf16le_bom.txt'),
               'rb').read()
    text = raw[2:].decode('utf-16-le')
    assert raw[:2] == b'\xff\xfe'
    assert '<TableStart:3,3:1:0<tCellDefaultCellType:Text>>' in text
    assert text.count('<ColStart:<tColAttrWidth:') == 3
    assert text.count('<RowStart:<tRowAttrHeight:') == 3
    assert text.count('<CellStart:1,1>') == 9
    assert text.count('<CellEnd:>') == 9
    assert text.count('<RowEnd:>') == 3
    assert text.count('<TableEnd:>') == 1
    assert text.count('<CellStyle:\\[None\\]><StylePriority:0>') == 9
    assert text.count('<CharStyle:Bold>') == 1
    # нет тегов из отвергнутого CS2-синтаксиса (без атрибутных скобок/без двоеточия)
    for bad in ['<rStart>', '<rEnd>', '<cStart:', '<cEnd>', '<TableEnd>']:
        assert bad not in text, f'T6b: найден CS2-тег {bad}'
    for line in text.split('\r\n'):
        if '<TableStart' in line:
            assert '<TableEnd:>' in line, 'T6b: таблица разорвана по строкам'
    print('T6b OK: эталонный синтаксис (TableStyle/TableStart:3,3:1:0<attr>/'
          'ColStart/RowStart/CellStyle/CellStart:1,1/CellEnd:), 3×3, шапка, '
          '1 жирная ячейка')


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else OUT_DEFAULT
    os.makedirs(out_dir, exist_ok=True)
    # I0-B файлы (история); T6 больше не генерируется — ронял InDesign
    write_file(out_dir, 'T4_i0_definestyle_names_utf16le_bom.txt', build_t4())
    write_file(out_dir, 'T5_i0_backslash_matrix_utf16le_bom.txt', build_t5())
    # I0-C файлы
    write_file(out_dir, 'T4b1_i0_header_oneline_utf16le_bom.txt', build_t4b1())
    write_file(out_dir, 'T4b2_i0_header_gboh_utf16le_bom.txt', build_t4b2())
    write_file(out_dir, 'T5b_i0_value_escapes_utf16le_bom.txt', build_t5b())
    write_file(out_dir, 'T6b_i0_table_from_reference_utf16le_bom.txt', build_t6b())
    verify(out_dir)
    verify_i0c(out_dir)
    print('Самопроверка пройдена (T6 не генерируется: ронял InDesign, '
          'синтаксис CS2 отвергнут; заменён на T6b по эталону).')


if __name__ == '__main__':
    main()
