r"""i0_make_test_files_b.py — BATCH I0-B, Часть 2.

Создаёт три минимальных файла InDesign Tagged Text (все Verbose,
UTF-16LE + BOM, по одному файлу, 6–10 абзацев) в каталоге out рядом
с фикстурами:

  T4_i0_definestyle_names_utf16le_bom.txt — шапка с Define*Style ТОЛЬКО
      по именам (формат как в образце GBoH: <DefineParaStyle:Имя=<Nextstyle:Имя>>),
      роли h1/h2/h3/p/li/img, CharStyle Bold/Italic.
      Проверки: (а) документ БЕЗ стилей — помещается ли без окна ошибок;
      (б) документ СО стилями — не перезаписывает ли оформление, окно конфликта имён.

  T5_i0_backslash_matrix_utf16le_bom.txt — матрица обратного слэша:
      каждый вариант в СВОЁМ абзаце с подписью: \\, \\\\<, <0x005C>, \\, \\<,
      плюс абзац со стилем в группе (Группа\\:Стиль).

  T6_i0_table_3x3_utf16le_bom.txt — маленькая таблица 3×3 с шапкой по
      спецификации (TableStart/RowStart/CellStart/CellEnd/RowEnd/TableEnd),
      ячейки с текстом, одна ячейка с жирным куском.

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


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else OUT_DEFAULT
    os.makedirs(out_dir, exist_ok=True)
    write_file(out_dir, 'T4_i0_definestyle_names_utf16le_bom.txt', build_t4())
    write_file(out_dir, 'T5_i0_backslash_matrix_utf16le_bom.txt', build_t5())
    write_file(out_dir, 'T6_i0_table_3x3_utf16le_bom.txt', build_t6())
    verify(out_dir)
    print('Самопроверка пройдена.')


if __name__ == '__main__':
    main()
