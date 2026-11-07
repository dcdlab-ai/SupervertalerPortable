"""i1_tagged_text_tests.py — BATCH I1, headless-тесты писателя Tagged Text.

Проверяет модульный пакет modules/tagged_text (только stdlib, без GUI):
  T1  структура шапки по умолчанию (без ColorTable, решение s11.9);
  T2  регенерация T4b2 ПОБАЙТОВО (sha256 56fe7e6b…3ea196, режим gboh+all);
  T3  экранирование текста/значений, HTML-сущности, <br>;
  T4  выделения (Bold/Italic/BoldItalic, граница «_», несбалансированные,
      снятие в заголовках, одиночный «*» сохраняется);
  T5  списки/таблицы/комментарии/ограды/понижение h4→h3;
  T6  картинки (relative images/, абсолютный → basename + поиск,
      вне images/ — предупреждение, смешанная строка);
  T7  краевые случаи (пустой вход, пробелы, странные строки, CRLF-вход);
  T8  stylemap: save/load roundtrip, умолчания, битый JSON, версия,
      спецсимволы в имени стиля;
  T9  CLI: python -m modules.tagged_text (экспорт + --save-map + --report);
  T10 политика char_style_policy='used';
  T11 варианты строки 2: color_table minimal/gboh;
  T12 ограда не csv → предупреждение.

Использование:
  python i1_tagged_text_tests.py [STAGE_DIR]
(STAGE_DIR по умолчанию — Work_temp batch-i1/tests/run-001; артефакты
и подробный журнал пишутся туда, итог печатается в stdout по-ASCII.)
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO)

from modules.tagged_text.mdparse import parse_markdown  # noqa: E402
from modules.tagged_text.stylemap import (  # noqa: E402
    StyleMap, load as load_stylemap, save as save_stylemap, default_paragraph_styles)
from modules.tagged_text.writer import (  # noqa: E402
    write_tagged_text, write_file, escape_text, escape_value, GBOH_COLOR_LINE2)

FIXTURES = os.path.join(REPO, 'docs', 'refactoring', 'audits', 'fixtures',
                        'tagged_text')
STAGE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    r'E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i1\tests',
    'run-001')
os.makedirs(STAGE, exist_ok=True)

RESULTS = []
PASSED = 0
FAILED = 0


def check(name, cond, detail=''):
    global PASSED, FAILED
    RESULTS.append('%s %s%s' % ('PASS' if cond else 'FAIL', name,
                                (' | ' + detail) if (detail and not cond) else ''))
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        RESULTS.append('     detail: %s' % detail)


def read_fixture(name):
    with open(os.path.join(FIXTURES, name), 'r', encoding='utf-8') as f:
        return f.read()


def decode(data):
    assert data[:2] == b'\xff\xfe', 'нет BOM UTF-16LE'
    return data[2:].decode('utf-16-le')


def lines_of(data):
    return decode(data).split('\r\n')


def body_of(data):
    """Тело файла: строки после шапки и всех Define*Style."""
    ls = lines_of(data)
    # последняя строка пустая (финальный CRLF)
    assert ls[-1] == '', 'файл должен заканчиваться CRLF'
    ls = ls[:-1]
    ls = ls[2:]  # <UNICODE-WIN> + строка 2
    while ls and ls[0].startswith('<Define'):
        ls = ls[1:]
    return ls


def t1_header_default():
    data, rep = write_tagged_text('Один абзац.')
    ls = lines_of(data)
    check('T1 BOM UTF-16LE', data[:2] == b'\xff\xfe')
    check('T1 строка 1 = <UNICODE-WIN> одна', ls[0] == '<UNICODE-WIN>', repr(ls[0]))
    check('T1 строка 2 без ColorTable',
          ls[1] == '<Version:16.4><FeatureSet:InDesign-Roman>', repr(ls[1]))
    check('T1 ColorTable отсутствует', 'ColorTable' not in decode(data))
    check('T1 DefineParaStyle:p на своей строке',
          ls[2] == '<DefineParaStyle:p=<Nextstyle:p>>', repr(ls[2]))
    check('T1 один Define на строку',
          all(l.count('<Define') <= 1 for l in ls))
    check('T1 тело: <ParaStyle:p>Один абзац.',
          ls[3] == '<ParaStyle:p>Один абзац.', repr(ls[3]))
    check('T1 финальный CRLF', decode(data).endswith('\r\n'))
    check('T1 без BasedOn', 'BasedOn' not in decode(data))
    check('T1 BasedOn/шум отсутствуют в определениях',
          all('=' in l for l in ls if l.startswith('<Define')))
    check('T1 отчёт: одна роль p', rep.role_counts == {'p': 1}, repr(rep.role_counts))
    check('T1 отчёт: Define*Style зафиксированы',
          rep.define_styles == ['DefineParaStyle:p'], repr(rep.define_styles))


T4B2_SHA = '56fe7e6bed37375b36e11c615dd053c92c2bfb3aee57c751c343c2d4563ea196'


def t2_t4b2_regeneration():
    md = read_fixture('t4_t4b2_regeneration.md')
    data, rep = write_tagged_text(md, color_table='gboh', char_style_policy='all')
    h = hashlib.sha256(data).hexdigest()
    check('T2 T4b2 побайтово (sha256)', h == T4B2_SHA, h)
    check('T2 размер 2842 байта', len(data) == 2842, str(len(data)))
    ls = body_of(data)
    check('T2 тело h1 c «*» сохранено',
          ls[0] == '<ParaStyle:h1>Проверка Define*Style по именам: глава «Гавгамела»',
          repr(ls[0]))
    check('T2 6 параграфных + 3 символьных определения',
          decode(data).count('<DefineParaStyle:') == 6
          and decode(data).count('<DefineCharStyle:') == 3)
    check('T2 cTypeface:Bold Italic', '<cTypeface:Bold Italic>' in decode(data))


def t3_escape_entities():
    md = read_fixture('i1_escape_entities.md')
    data, rep = write_tagged_text(md)
    body = body_of(data)
    check('T3 слэш и скобки в тексте',
          body[0] == '<ParaStyle:p>Слэш \\\\ и скобки \\<b\\> и \\> конец.',
          repr(body[0]))
    check('T3 ; : , = НЕ экранируются (двойной слэш только от \\)',
          body[1] == '<ParaStyle:p>Знаки ; : , = остаются как есть: '
                     '\\\\; \\\\: \\\\, \\\\= конец.', repr(body[1]))
    check('T3 сущности раскодированы (затем < > экранируются по правилам выхода)',
          body[2] == '<ParaStyle:p>Сущности: & \\< \\> " \' ☺ конец.', repr(body[2]))
    check('T3 неизвестная сущность и «&amp» без «;» остаются',
          body[3] == '<ParaStyle:p>Неизвестная сущность &foo; и без точки '
                     'с запятой &amp конец.', repr(body[3]))
    check('T3 <br> → одиночный LF',
          body[4] == '<ParaStyle:p>Перенос внутри: первая часть\n'
                     'вторая часть\nтретья\nконец.', repr(body[4]))
    check('T3 счётчик сущностей = 6', rep.entities_decoded == 6,
          str(rep.entities_decoded))
    check('T3 счётчик <br> = 3', rep.br_breaks == 3, str(rep.br_breaks))
    check('T3 экранирование значения: имя стиля со спецсимволами',
          escape_value('Мой:Стиль[1],X=Y;Z<W>\\Q') ==
          'Мой\\:Стиль\\[1\\]\\,X\\=Y\\;Z\\<W\\>\\\\Q', escape_value('Мой:Стиль[1],X=Y;Z<W>\\Q'))
    check('T3 escape_text тривиальный текст не трогает',
          escape_text('а; б: в, г= д') == 'а; б: в, г= д')


def t4_emphasis():
    md = read_fixture('i1_emphasis.md')
    data, rep = write_tagged_text(md)
    body = body_of(data)
    check('T4 bold/italic/bold-italic спаны',
          body[0] == '<ParaStyle:p><CharStyle:Bold>жирный<CharStyle:> и '
                     '<CharStyle:Italic>курсив<CharStyle:> и '
                     '<CharStyle:BoldItalic>жирный курсив<CharStyle:> в одном.',
          repr(body[0]))
    check('T4 подчёркивание только на границе слов',
          body[1] == '<ParaStyle:p>Подчёркивания: <CharStyle:Italic>италик'
                     '<CharStyle:> работает, snake_case — нет, a_b_c — нет.',
          repr(body[1]))
    check('T4 несбалансированные маркеры остались буквально',
          body[2] == '<ParaStyle:p>Несбалансированный **маркер без закрытия '
                     'и *одиночная звезда.', repr(body[2]))
    check('T4 счётчик несбалансированных = 2',
          rep.emphasis_leftover == 2, str(rep.emphasis_leftover))
    check('T4 заголовок: выделение снято, одиночная «*» сохранена',
          body[3] == '<ParaStyle:h1>Заголовок с жирным и Define*Style внутри',
          repr(body[3]))
    check('T4 снят 1 спан в заголовке',
          rep.emphasis_stripped_headings == 1,
          str(rep.emphasis_stripped_headings))
    check('T4 спаны: bold=1, italic=2, bold_italic=1',
          rep.char_style_spans == {'bold': 1, 'italic': 2, 'bold_italic': 1},
          repr(rep.char_style_spans))
    check('T4 определения: h1, p, затем 3 символьных',
          [d for d in rep.define_styles] == [
              'DefineParaStyle:h1', 'DefineParaStyle:p',
              'DefineCharStyle:Bold', 'DefineCharStyle:Italic',
              'DefineCharStyle:BoldItalic'], repr(rep.define_styles))


def t5_lists_tables():
    md = read_fixture('i1_lists_tables.md')
    data, rep = write_tagged_text(md)
    body = body_of(data)
    check('T5 роли: li=2, li_n=2, table_row=4, h3=1',
          rep.role_counts == {'li': 2, 'li_n': 2, 'table_row': 4, 'h3': 1},
          repr(rep.role_counts))
    check('T5 номер сохранён текстом',
          '<ParaStyle:li_n>1. Первый нумерованный' in body, repr(body[1:3]))
    check('T5 маркер списка снят',
          body[0] == '<ParaStyle:li>Первый маркированный пункт', repr(body[0]))
    check('T5 комментарий отброшен',
          not any('комментарий отбрасывается' in l for l in body))
    check('T5 разделитель |---| отброшен',
          not any(l.strip('|-: ') == '' and '---' in l for l in body),
          repr([l for l in body if '---' in l]))
    check('T5 pipe-строки записаны table_row',
          '<ParaStyle:table_row>|Колонка A|Колонка B|' in body
          and '<ParaStyle:table_row>|Значение 1|Значение 2|' in body)
    check('T5 строки ограды отброшены, csv-строки записаны',
          '```' not in decode(data)
          and '<ParaStyle:table_row>ключ,значение' in body
          and '<ParaStyle:table_row>имя,Иван' in body)
    check('T5 счётчики: комментарий=1, разделитель=1, ограда=2/1',
          rep.comments_dropped == 1 and rep.table_separators_dropped == 1
          and rep.fence_lines_dropped == 2 and rep.fence_blocks == 1,
          repr((rep.comments_dropped, rep.table_separators_dropped,
                rep.fence_lines_dropped, rep.fence_blocks)))
    check('T5 h4 понижен до h3 (счётчик h4=1)',
          rep.headings_downgraded == {'h4': 1}, repr(rep.headings_downgraded))
    check('T5 тело h3 без ####',
          '<ParaStyle:h3>Заголовок четвёртого уровня' in body)


def _make_images_stage(with_files=True):
    img_dir = os.path.join(STAGE, 'images')
    os.makedirs(img_dir, exist_ok=True)
    if with_files:
        for name in ('map.png', 'icon.png', 'shot_001.png'):
            with open(os.path.join(img_dir, name), 'wb') as f:
                f.write(b'png')
    return img_dir


def t6_images():
    md = read_fixture('i1_images.md')
    img_dir = _make_images_stage(with_files=True)
    out1 = os.path.join(STAGE, 'i1_images_found.txt')
    rep = write_file(os.path.join(FIXTURES, 'i1_images.md'), out1,
                     images_dir=img_dir)
    body = body_of(open(out1, 'rb').read())
    check('T6 относительный images/ как есть',
          body[0] == '<ParaStyle:img>![Метка карты](images/map.png)', repr(body[0]))
    check('T6 абсолютный путь → базовое имя, файл найден',
          body[1] == '<ParaStyle:img>![Скриншот](images/shot_001.png)', repr(body[1]))
    check('T6 относительный вне images/ — как есть + предупреждение',
          body[2] == '<ParaStyle:img>![Диаграмма](figures/diagram.png)', repr(body[2]))
    check('T6 предупреждение о пути вне images/',
          any('вне images/' in w for w in rep.warnings), repr(rep.warnings))
    check('T6 смешанная строка разрезана на 3 блока',
          body[3] == '<ParaStyle:p>Текст с картинкой в середине'
          and body[4] == '<ParaStyle:img>![иконка](images/icon.png)'
          and body[5] == '<ParaStyle:p>и текст после.', repr(body[3:6]))
    check('T6 счётчик смешанных строк = 1', rep.mixed_image_lines == 1)
    check('T6 картинки: всего 4, найдено 3, не найдено 1',
          rep.images_total == 4 and rep.images_found == 3
          and rep.images_missing == ['figures/diagram.png'],
          repr((rep.images_total, rep.images_found, rep.images_missing)))
    # без файлов: абсолютный не найден → предупреждение s11.5
    img_dir_empty = os.path.join(STAGE, 'images_empty')
    os.makedirs(img_dir_empty, exist_ok=True)
    out2 = os.path.join(STAGE, 'i1_images_missing.txt')
    rep2 = write_file(os.path.join(FIXTURES, 'i1_images.md'), out2,
                      images_dir=img_dir_empty)
    check('T6 без файлов: найдено 0, предупреждение «файл не найден»',
          rep2.images_found == 0
          and any('файл не найден' in w for w in rep2.warnings),
          repr(rep2.warnings))


def t7_edge_cases():
    data, rep = write_tagged_text('')
    ls = lines_of(data)
    check('T7 пустой вход: только шапка',
          ls == ['<UNICODE-WIN>', '<Version:16.4><FeatureSet:InDesign-Roman>', ''],
          repr(ls))
    check('T7 пустой вход: без определений', rep.define_styles == [])
    data2, rep2 = write_tagged_text('   \n\t\n\n')
    check('T7 пробельные строки пропущены (счётчик 3)',
          rep2.empty_lines_skipped == 3
          and lines_of(data2)[-1] == '', repr(rep2.empty_lines_skipped))
    data3, rep3 = write_tagged_text('# \n| \n<!--\n')
    check('T7 странные строки не падают: роли посчитаны',
          set(rep3.role_counts) <= {'p', 'table_row'}, repr(rep3.role_counts))
    crlf_md = 'Первый\r\n\r\nВторой\r\n'
    data4, rep4 = write_tagged_text(crlf_md)
    body = body_of(data4)
    check('T7 CRLF-вход: два абзаца, пустая пропущена',
          body == ['<ParaStyle:p>Первый', '<ParaStyle:p>Второй']
          and rep4.empty_lines_skipped == 1, repr(body))


def t8_stylemap():
    path = os.path.join(STAGE, 'stylemap_roundtrip.json')
    save_stylemap(path, StyleMap())
    sm, warns = load_stylemap(path)
    check('T8 roundtrip: умолчания сохраняются и читаются',
          sm.paragraph_styles == default_paragraph_styles()
          and sm.char_styles == {'bold': 'Bold', 'italic': 'Italic',
                                 'bold_italic': 'BoldItalic'}
          and warns == [], repr((sm.to_dict(), warns)))
    partial = os.path.join(STAGE, 'stylemap_partial.json')
    with open(partial, 'w', encoding='utf-8') as f:
        json.dump({'version': 1, 'paragraph_styles': {'p': 'Body Text'}}, f)
    sm2, _ = load_stylemap(partial)
    check('T8 частичная карта: p замещён, остальные умолчания',
          sm2.para_name('p') == 'Body Text' and sm2.para_name('h1') == 'h1')
    v2 = os.path.join(STAGE, 'stylemap_v2.json')
    with open(v2, 'w', encoding='utf-8') as f:
        json.dump({'version': 2}, f)
    _, warns2 = load_stylemap(v2)
    check('T8 версия ≠ 1 → предупреждение, карта принимается',
          len(warns2) == 1 and 'версия' in warns2[0], repr(warns2))
    bad = os.path.join(STAGE, 'stylemap_bad.json')
    with open(bad, 'w', encoding='utf-8') as f:
        f.write('{not json')
    try:
        load_stylemap(bad)
        ok = False
    except ValueError:
        ok = True
    check('T8 битый JSON → ValueError', ok)
    arr = os.path.join(STAGE, 'stylemap_arr.json')
    with open(arr, 'w', encoding='utf-8') as f:
        f.write('[]')
    try:
        load_stylemap(arr)
        ok2 = False
    except ValueError:
        ok2 = True
    check('T8 не-объект JSON → ValueError', ok2)
    sm3 = StyleMap()
    sm3.paragraph_styles['p'] = 'Мой:Стиль[1]'
    data3, _ = write_tagged_text('Текст.', sm3)
    body = body_of(data3)
    check('T8 спецсимволы в имени стиля экранированы в шапке и теле',
          '<DefineParaStyle:Мой\\:Стиль\\[1\\]=<Nextstyle:Мой\\:Стиль\\[1\\]>>'
          in decode(data3)
          and body[0] == '<ParaStyle:Мой\\:Стиль\\[1\\]>Текст.', repr(body[0]))


def t9_cli():
    out = os.path.join(STAGE, 'cli_out.txt')
    repf = os.path.join(STAGE, 'cli_report.txt')
    proc = subprocess.run(
        [sys.executable, '-m', 'modules.tagged_text',
         os.path.join(FIXTURES, 'i1_escape_entities.md'), out,
         '--report', repf],
        cwd=REPO, capture_output=True, text=True)
    check('T9 CLI rc=0', proc.returncode == 0,
          'rc=%s stderr=%s' % (proc.returncode, proc.stderr[-300:]))
    if os.path.exists(out):
        check('T9 CLI выход с BOM', open(out, 'rb').read()[:2] == b'\xff\xfe')
    else:
        check('T9 CLI выход создан', False, 'файла нет')
    check('T9 CLI отчёт записан',
          os.path.exists(repf) and 'Отчёт экспорта' in open(
              repf, encoding='utf-8').read())
    mpath = os.path.join(STAGE, 'cli_saved_map.json')
    proc2 = subprocess.run(
        [sys.executable, '-m', 'modules.tagged_text', '--save-map', mpath],
        cwd=REPO, capture_output=True, text=True)
    check('T9 CLI --save-map без входных файлов rc=0 и JSON создан',
          proc2.returncode == 0 and os.path.exists(mpath),
          'rc=%s stderr=%s' % (proc2.returncode, proc2.stderr[-200:]))


def t10_policy_used():
    data, rep = write_tagged_text('Абзац с **жирным** куском.')
    check('T10 used: только Bold определён',
          decode(data).count('<DefineCharStyle:') == 1
          and '<DefineCharStyle:Bold=' in decode(data)
          and 'Italic' not in decode(data))
    check('T10 used: спаны посчитаны', rep.char_style_spans['bold'] == 1)
    data2, rep2 = write_tagged_text('Просто абзац.')
    check('T10 used: без выделений символьных определений нет',
          decode(data2).count('<DefineCharStyle:') == 0)


def t11_color_table_modes():
    data, _ = write_tagged_text('X.', color_table='minimal')
    ls = lines_of(data)
    check('T11 minimal: строка 2 = Version+FeatureSet+Black+Paper',
          ls[1] == '<Version:16.4><FeatureSet:InDesign-Roman>'
                   '<ColorTable:=<Black:COLOR:CMYK:Process:0,0,0,1>'
                   '<Paper:COLOR:CMYK:Process:0,0,0,0>>', repr(ls[1]))
    data2, _ = write_tagged_text('X.', color_table='gboh')
    ls2 = lines_of(data2)
    check('T11 gboh: строка 2 = Version+FeatureSet+ColorTable образца',
          ls2[1] == '<Version:16.4><FeatureSet:InDesign-Roman>'
                    + GBOH_COLOR_LINE2, repr(ls2[1][:80]))
    try:
        write_tagged_text('X.', color_table='wrong')
        ok = False
    except ValueError:
        ok = True
    check('T11 недопустимый режим → ValueError', ok)


def t12_non_csv_fence():
    md = '```python\nprint(1)\n```\n'
    data, rep = write_tagged_text(md)
    check('T12 ограда не csv: предупреждение и счётчик',
          rep.non_csv_fences == 1
          and any('не csv' in w for w in rep.warnings), repr(rep.warnings))
    check('T12 содержимое не-csv ограды записано table_row',
          '<ParaStyle:table_row>print(1)' in decode(data))


def main():
    for fn in (t1_header_default, t2_t4b2_regeneration, t3_escape_entities,
               t4_emphasis, t5_lists_tables, t6_images, t7_edge_cases,
               t8_stylemap, t9_cli, t10_policy_used, t11_color_table_modes,
               t12_non_csv_fence):
        fn()
    log_path = os.path.join(STAGE, 'i1_tagged_text_tests.out')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(RESULTS) + '\n')
    print('I1-TESTS: %d passed / %d failed' % (PASSED, FAILED))
    print('log: %s' % log_path)
    if FAILED:
        print('FAILED ITEMS:')
        for r in RESULTS:
            if r.startswith('FAIL') or r.startswith('     detail'):
                try:
                    print(r.encode('ascii', 'replace').decode('ascii'))
                except Exception:
                    print(r)
    return 0 if FAILED == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
