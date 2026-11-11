# ============================================================================
# modules/simple_import_builder.py — чистый построитель сегментов для
# импорта txt/md (Batch TBL1.2, Task 1).
#
# Общая часть для основной и fallback-веток кодировок import_simple_txt
# (раньше логика дублировалась в монолите Supervertaler.py). Без Qt:
# сегментер передаётся ГОТОВЫМ объектом (SimpleSegmenter/MarkdownSegmenter
# из modules.simple_segmenter); загрузка правил настроек и всё остальное
# остаётся на вызывающей стороне монолита.
#
# Характеризационное сравнение с прежним продублированным кодом (байт-в-байт
# по спискам Segment.to_dict()) — docs/refactoring/audits/
# tbl12_import_builder_charact_tests.py.
# ============================================================================

from modules.models import Segment


def build_segments_from_lines(lines, segmenter=None):
    """Строит список Segment из строк файла (импорт txt/md).

    Одна физическая строка = один сегмент; paragraph_id и
    document_position = номер строки (с 1); пустые строки сохраняются
    как пустые сегменты (для структуры).

    segmenter=None — каждая непустая строка целиком становится сегментом.
    segmenter=<объект с segment_with_separators(text)> — непустые строки
    режутся на предложения (join_before = separator); пустые строки
    остаются пустыми сегментами.

    Возвращает список Segment; id — сквозная нумерация с 1.
    """
    segments = []
    if segmenter is not None:
        for line_num, line in enumerate(lines, 1):
            text = line.rstrip('\r\n')
            if not text.strip():
                # Empty line → empty segment (hidden in grid, preserved for export)
                segments.append(Segment(
                    id=len(segments) + 1, source=text, target="",
                    status="untranslated", notes="", type="para",
                    paragraph_id=line_num, document_position=line_num
                ))
            else:
                for sentence, separator in segmenter.segment_with_separators(text):
                    segments.append(Segment(
                        id=len(segments) + 1, source=sentence, target="",
                        status="untranslated", notes="", type="para",
                        paragraph_id=line_num, document_position=line_num,
                        join_before=separator
                    ))
    else:
        for line_num, line in enumerate(lines, 1):
            text = line.rstrip('\r\n')
            segments.append(Segment(
                id=len(segments) + 1, source=text, target="",
                status="untranslated", notes="", type="para",
                paragraph_id=line_num, document_position=line_num
            ))
    return segments
