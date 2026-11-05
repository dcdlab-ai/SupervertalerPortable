r"""i0_escape_lines.py — BATCH I0-C, задача 2.

Проверка гипотезы Дмитрия по БАЙТАМ тест-файлов: на каких
конструкциях экранирования стоят строки с ошибкой «escape character
found without the preceding…» и каких нет на безошибочных строках.

Для каждого файла: для каждой строки — какие последовательности
экранирования стоят В ТЕКСТЕ (вне угловых скобок тегов) и В ЗНАЧЕНИЯХ
тегов; сколько <0x005C>; сколько CRLF/LF во всём файле и в шапке.

Использование: python i0_escape_lines.py OUT_PATH
"""
import os
import re
import sys

OUT_DIR = r'E:\Dev\Work_temp\samples\indesign\out'
FILES = [
    'T1_i0_verbose_utf16le_bom.txt',
    'T5_i0_backslash_matrix_utf16le_bom.txt',
]
# ошибка в логе InDesign на этих строках (факты от Дмитрия, 1-based
# с учётом строк шапки)
ERROR_LINES = {
    'T1_i0_verbose_utf16le_bom.txt': [9],
    'T5_i0_backslash_matrix_utf16le_bom.txt': [9],
}
# сообщение «Importing invalid tag as text»
INVALID_TAG_LINES = {
    'T1_i0_verbose_utf16le_bom.txt': [],
    'T5_i0_backslash_matrix_utf16le_bom.txt': [5],
}

SEQ = re.compile(r'\\(.)')


def split_line_scopes(line):
    r"""Разделить строку на 'вне тегов' (текст) и 'внутри <>' (значения),
    уважая backslash-экранирование (экранированная пара идёт целиком)."""
    text, values, cur = [], [], []
    inside = False
    k = 0
    while k < len(line):
        ch = line[k]
        if ch == '\\' and k + 1 < len(line):
            cur.append(line[k:k + 2])
            k += 2
            continue
        if ch == '<' and not inside:
            inside = True
            text.append(''.join(cur))
            cur = []
        elif ch == '>' and inside:
            inside = False
            cur.append(ch)
            values.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
        k += 1
    text.append(''.join(cur))
    return ''.join(text), ''.join(values)


def main():
    out_path = sys.argv[1]
    L = ['=' * 100,
         'I0-C: экранирование в тест-файлах по строкам (текст vs значения тегов) '
         'против ошибок лога InDesign', '=' * 100]
    for name in FILES:
        raw = open(os.path.join(OUT_DIR, name), 'rb').read()
        t = raw.decode('utf-16-le').lstrip('\ufeff')
        lines = t.split('\r\n')
        L.append(f'--- {name}: строк {len(lines) - 1} (+ пустая последняя); '
                 f'CRLF в файле: {t.count(chr(13) + chr(10))}, '
                 f'одиночных LF: {t.replace(chr(13) + chr(10), "").count(chr(10))}')
        errs = ERROR_LINES[name]
        inv = INVALID_TAG_LINES[name]
        L.append(f'ошибки «escape character…» в логе (Дмитрий): строки {errs}; '
                 f'«Importing invalid tag as text»: строки {inv}')
        L.append('  стр | в ТЕКСТЕ            | в ЗНАЧЕНИЯХ тегов | лог')
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            text, values = split_line_scopes(line)
            ts = sorted(set(SEQ.findall(text)))
            vs = sorted(set(SEQ.findall(values)))
            mark = 'ОШИБКА escape' if n in errs else \
                   ('invalid tag' if n in inv else 'чисто')
            L.append(f'  {n:3} | {ts!r:19} | {vs!r} | {mark}')
        L.append('')
    # контроль: шапка GBoH — чем разделены строки (для T4b2)
    gb = open(r'E:\Dev\Work_temp\SupervertalerPortable\samples\indesign'
              r'\GBoH-Great_Battles_of_Alexander_RU-v2.txt', 'rb').read()
    gt = gb.decode('utf-16-le')
    i = gt.find('<ParaStyle:')
    j = gt.rfind('\n', 0, i)
    hdr, body = gt[:j + 1], gt[j + 1:]
    L.append('--- GBoH (эталон структуры шапки):')
    L.append(f'  BOM: {gb[:2].hex()}; шапка до первого ParaStyle: строк '
             f'{hdr.count(chr(10))}; разделители шапки: CRLF '
             f'{hdr.count(chr(13) + chr(10))}, одиночных LF '
             f'{hdr.replace(chr(13) + chr(10), "").count(chr(10))};')
    L.append(f'  тело: CRLF {body.count(chr(13) + chr(10))}, одиночных LF '
             f'{body.replace(chr(13) + chr(10), "").count(chr(10))} '
             f'(это U+2028-принудительные переносы и U+2028).')
    # эталон таблицы: разделители
    tb = open(r'E:\Dev\Work_temp\SupervertalerPortable\samples\md_out'
              r'\tagget_text_table_Verbose.txt', 'rb').read()
    tt = tb.decode('utf-16-le')
    L.append('--- Эталон таблицы (tagget_text_table_Verbose.txt):')
    L.append(f'  BOM: {tb[:2].hex()}; CRLF {tt.count(chr(13) + chr(10))}, '
             f'одиночных LF {tt.replace(chr(13) + chr(10), "").count(chr(10))}; '
             f'строк (по LF): {tt.count(chr(10))}')
    open(out_path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'отчёт записан: {out_path}')


if __name__ == '__main__':
    main()
