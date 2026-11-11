# ============================================================================
# modules/simple_import_builder.py — чистый построитель сегментов для
# импорта txt/md (Batch TBL1.2, Tasks 1–2).
#
# Общая часть для основной и fallback-веток кодировок import_simple_txt и
# для TXT/MD-ветки многофайлового импорта (раньше логика дублировалась в
# монолите Supervertaler.py). Без Qt: сегментер передаётся ГОТОВЫМ объектом
# (SimpleSegmenter/MarkdownSegmenter из modules.simple_segmenter); загрузка
# правил настроек и всё остальное остаётся на вызывающей стороне монолита.
#
# Таблицы (Task 2, решения координатора TBL1.0/TBL1.1): при
# recognize_tables=True каждая ячейка md-строки таблицы становится
# сегментом: source — текст ячейки без «|» (split_table_row), type =
# "table_cell", is_table_cell=True, table_info = (table_idx, row, col,
# is_header); все ячейки одной md-строки делят paragraph_id (= номер
# физической строки, как у обычных сегментов). table_idx — сквозной номер
# таблицы в файле с 0 (file_id в table_idx НЕ входит: экспорт группирует по
# (file_id, table_idx, row)); row — индекс md-строки данных внутри блока
# (строка заголовка при header=True — row=0); col — индекс ячейки.
# Строка-разделитель сегментом не становится. Ячейки предложениями не
# режутся; пустые ячейки — сегменты с пустым source.
#
# Характеризационное сравнение с прежним продублированным кодом (байт-в-байт
# по спискам Segment.to_dict() при recognize_tables=False) —
# docs/refactoring/audits/tbl12_import_builder_charact_tests.py.
# ============================================================================

from modules.models import Segment
from modules.md_table_cells import find_table_blocks, is_table_separator, split_table_row


def _map_table_rows(lines):
    """Карта табличных строк файла (0-based) -> два множества:

    table_rows: индекс физической строки данных -> (table_idx, row,
    is_header, cells);
    separator_lines: индексы строк-разделителей внутри блоков — сегментами
    не становятся (при экспорте регенерируются). Разделитель-одиночка
    (блок без строк данных, отброшен find_table_blocks) остаётся обычным
    текстом. Разделители, «отброшенные» внутри блока (не на 2-й позиции),
    тоже не сегментируются. Нумерация row идёт по md-строкам данных блока
    подряд, поэтому карта совпадает с порядком block.rows.
    """
    table_rows = {}
    separator_lines = set()
    for table_idx, block in enumerate(find_table_blocks(lines)):
        row_idx = 0
        for line_idx in range(block.start, block.end + 1):
            if is_table_separator(lines[line_idx]):
                separator_lines.add(line_idx)
                continue
            cells = split_table_row(lines[line_idx])
            if cells is None:
                continue  # защита: строки блока всегда табличные
            table_rows[line_idx] = (table_idx, row_idx,
                                    bool(block.header and row_idx == 0), cells)
            row_idx += 1
    return table_rows, separator_lines


def build_segments_from_lines(lines, segmenter=None, recognize_tables=False,
                              id_start=1, status="untranslated",
                              file_id=None, file_name=""):
    """Строит список Segment из строк файла (импорт txt/md).

    Одна физическая строка = один сегмент; paragraph_id и
    document_position = номер строки (с 1); пустые строки сохраняются
    как пустые сегменты (для структуры).

    segmenter=None — каждая непустая строка целиком становится сегментом.
    segmenter=<объект с segment_with_separators(text)> — непустые
    НЕтабличные строки режутся на предложения (join_before = separator);
    пустые строки остаются пустыми сегментами.

    recognize_tables=True — ячейки md-таблиц становятся сегментами, а
    строки-разделители внутри табличных блоков сегментами не становятся
    (см. шапку модуля); табличные строки предложениями не режутся.

    id_start — начальный id (по умолчанию 1; многофайловый импорт передаёт
    продолжающийся счётчик); status — статус новых сегментов; file_id /
    file_name — атрибуты многофайлового проекта (для одиночного импорта
    остаются None/"").

    Возвращает список Segment.
    """
    segments = []
    next_id = id_start
    if recognize_tables:
        table_rows, separator_lines = _map_table_rows(lines)
    else:
        table_rows, separator_lines = {}, set()

    for line_num, line in enumerate(lines, 1):
        idx0 = line_num - 1
        table_entry = table_rows.get(idx0)
        if table_entry is not None:
            table_idx, row_idx, is_header, cells = table_entry
            for col, cell in enumerate(cells):
                segments.append(Segment(
                    id=next_id, source=cell, target="",
                    status=status, notes="", type="table_cell",
                    paragraph_id=line_num, document_position=line_num,
                    is_table_cell=True,
                    table_info=(table_idx, row_idx, col, is_header),
                    file_id=file_id, file_name=file_name,
                ))
                next_id += 1
            continue

        if idx0 in separator_lines:
            # Строка-разделитель таблицы сегментом не становится:
            # при экспорте регенерируется (build_table_separator).
            continue

        text = line.rstrip('\r\n')
        if segmenter is not None:
            if not text.strip():
                # Empty line → empty segment (hidden in grid, preserved for export)
                segments.append(Segment(
                    id=next_id, source=text, target="",
                    status=status, notes="", type="para",
                    paragraph_id=line_num, document_position=line_num,
                    file_id=file_id, file_name=file_name,
                ))
                next_id += 1
            else:
                for sentence, separator in segmenter.segment_with_separators(text):
                    segments.append(Segment(
                        id=next_id, source=sentence, target="",
                        status=status, notes="", type="para",
                        paragraph_id=line_num, document_position=line_num,
                        join_before=separator,
                        file_id=file_id, file_name=file_name,
                    ))
                    next_id += 1
        else:
            segments.append(Segment(
                id=next_id, source=text, target="",
                status=status, notes="", type="para",
                paragraph_id=line_num, document_position=line_num,
                file_id=file_id, file_name=file_name,
            ))
            next_id += 1
    return segments
