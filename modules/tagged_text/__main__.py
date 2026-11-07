"""CLI для разработки: md → InDesign Tagged Text.

Использование (из корня проекта)::

    E:\\Dev\\python-embed\\python.exe -m modules.tagged_text in.md out.txt ^
        [--map файл.json] [--images-dir папка] [--save-map файл.json] ^
        [--color-table {none,minimal,gboh}] [--char-styles {used,all}] ^
        [--report файл.txt]

Отчёт экспорта печатается в stdout. GUI-интеграция — батч I2.
"""
from __future__ import annotations

import argparse
import sys

from .stylemap import StyleMap, load as load_stylemap, save as save_stylemap
from .writer import write_file


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='python -m modules.tagged_text',
        description='Markdown → InDesign Tagged Text (UTF-16LE+BOM, CRLF)')
    parser.add_argument('in_md', nargs='?', help='входной .md файл')
    parser.add_argument('out_txt', nargs='?', help='выходной .txt (Tagged Text)')
    parser.add_argument('--map', metavar='FILE',
                        help='JSON-карта «роль → имя стиля» (load)')
    parser.add_argument('--save-map', metavar='FILE',
                        help='сохранить карту по умолчанию в FILE и выйти')
    parser.add_argument('--images-dir', metavar='DIR',
                        help='папка images/ для поиска картинок '
                             '(по умолчанию images/ рядом с выходом)')
    parser.add_argument('--color-table', choices=('none', 'minimal', 'gboh'),
                        default='minimal',
                        help='ColorTable в строке 2 шапки (по умолчанию '
                             'minimal — Black+Paper; режим none даёт пустые '
                             'абзацы = Define*Style + 1, ручной факт I1)')
    parser.add_argument('--char-styles', choices=('used', 'all'),
                        default='used',
                        help='определять только использованные символьные '
                             'стили (used) или все три (all)')
    parser.add_argument('--report', metavar='FILE',
                        help='дополнительно записать отчёт в FILE')
    args = parser.parse_args(argv)

    if args.save_map:
        save_stylemap(args.save_map, StyleMap())
        print('Карта по умолчанию сохранена: %s' % args.save_map)
        return 0

    if not args.in_md or not args.out_txt:
        parser.error('требуются in_md и out_txt (или --save-map)')

    warnings = []
    if args.map:
        style_map, warnings = load_stylemap(args.map)
    else:
        style_map = StyleMap()
    for w in warnings:
        print('ПРЕДУПРЕЖДЕНИЕ: %s' % w)

    report = write_file(
        args.in_md, args.out_txt, style_map=style_map,
        images_dir=args.images_dir, color_table=args.color_table,
        char_style_policy=args.char_styles)
    print('Записано: %s' % args.out_txt)
    print(report.to_text())
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report.to_text() + '\n')
        print('Отчёт записан: %s' % args.report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
