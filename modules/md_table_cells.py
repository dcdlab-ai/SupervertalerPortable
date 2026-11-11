# ============================================================================
# modules/md_table_cells.py — чистый разбор md-таблиц на ячейки (Batch TBL1.1).
#
# Только pure-функции и dataclass: без Qt, без зависимостей от Supervertaler.py,
# без логирования и побочных эффектов. Нигде не вызывается продуктом —
# интеграция (импорт/экспорт) — отдельный батч TBL1.2 по вердикту координатора.
#
# Контракт (решения координатора TBL1.1):
#   * Ячейка = сегмент; source — очищенный текст без «|».
#   * Строка-разделитель (|---|---|) — не сегмент; при экспорте регенерируется
#     как «|---|» по числу столбцов. Выравнивание разделителя («:---:», «---:»,
#     «:---») НЕ сохраняется — при сборке всегда канонический «|---|».
#   * «\|» внутри ячейки — экранированный pipe (текст ячейки «|»); чётность
#     обратных слэшей перед «|» учитывается (нечётное число = экранировано).
#   * Число ячеек строки сохраняется как есть: строки с разным числом ячеек
#     не выравниваются и не дополняются.
#   * Внутри ячейки предложения не режутся; пустые ячейки сохраняются.
#   * Сборка строки: «|» → «\|», CR/LF → пробел. Формат детерминированный;
#     байт-в-байт круг гарантируется только для нормализованного ввода
#     (нормализованный = собранный build_table_row / build_table_separator).
#   * «<br>» и «**» в ячейках не обрабатываются — остаются в тексте как есть.
# ============================================================================

import re
from dataclasses import dataclass, field
from typing import List, Optional

# Ячейка-разделитель: «---», «:---», «---:», «:---:» (после trim).
_SEPARATOR_CELL_RE = re.compile(r'^:?-+:?$')


def escape_cell(text: str) -> str:
    r"""Готовит текст ячейки к сборке в md-строку: CR/LF → пробел, «|» → «\|».

    Обратные слэши не трогаются: сборка всегда обрамляет содержимое ячейки
    пробелами («| a |»), поэтому «\» в тексте никогда не оказывается
    вплотную к разделителю и при обратном разборе интерпретируется как
    литерал (экранирует только «\|»).
    """
    if not text:
        return text
    text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
    return text.replace('|', '\\|')


def unescape_cell(text: str) -> str:
    r"""Разворачивает «\|» → «|» в фрагменте ячейки с учётом чётности слэшей.

    Нечётное число обратных слэшей непосредственно перед «|» означает
    экранированный pipe: последний слэш «съедается», pipe остаётся в тексте.
    Остальные последовательности («\\», «\a», …) не трогаются.
    """
    if not text or '\\' not in text:
        return text
    out: List[str] = []
    backslashes = 0
    for ch in text:
        if ch == '\\':
            backslashes += 1
            out.append(ch)
        elif ch == '|':
            if backslashes % 2 == 1:
                # Последний слэш экранировал pipe: снять его.
                out.pop()
            out.append('|')
            backslashes = 0
        else:
            backslashes = 0
            out.append(ch)
    return ''.join(out)


def _scan_cells(fragment: str) -> List[str]:
    r"""Разбирает фрагмент между внешними «|» на ячейки по неэкранированным «|».

    «\|» → «|» в тексте ячейки (чётность слэшей учитывается); края ячейки
    обрезаются; остальное содержимое не меняется.
    """
    cells: List[str] = []
    cur: List[str] = []
    backslashes = 0
    for ch in fragment:
        if ch == '\\':
            backslashes += 1
            cur.append(ch)
        elif ch == '|':
            if backslashes % 2 == 1:
                # Экранированный pipe: последний слэш становится «|».
                cur.pop()
                cur.append('|')
            else:
                cells.append(''.join(cur).strip())
                cur = []
            backslashes = 0
        else:
            backslashes = 0
            cur.append(ch)
    cells.append(''.join(cur).strip())
    return cells


def split_table_row(line: str) -> Optional[List[str]]:
    r"""Разбирает строку md-таблицы на список ячеек; не табличная строка → None.

    Строка табличная, только если после strip() начинается с «|», заканчивается
    НЕэкранированным «|» и имеет длину ≥ 2. Разбор по неэкранированным «|»;
    «\|» → «|» в тексте ячейки; пробелы по краям ячейки обрезаются; остальное
    содержимое не меняется. Число ячеек сохраняется как есть (пустые ячейки —
    пустые строки).
    """
    s = line.strip()
    if len(s) < 2 or not s.startswith('|') or not s.endswith('|'):
        return None
    # Последний «|» должен быть неэкранированным: чётное число слэшей перед ним.
    trailing_bs = 0
    for ch in reversed(s[:-1]):
        if ch == '\\':
            trailing_bs += 1
        else:
            break
    if trailing_bs % 2 == 1:
        return None
    return _scan_cells(s[1:-1])


def is_table_separator(line: str) -> bool:
    """True, если строка — разделитель md-таблицы («|---|---|», «| :---: | ---: |»).

    Табличная строка (см. split_table_row), все ячейки которой после trim
    подходят под ^:?-+:?$. «---» без внешних «|» — НЕ разделитель.
    """
    cells = split_table_row(line)
    if not cells:
        return False
    return all(_SEPARATOR_CELL_RE.match(c) for c in cells)


@dataclass
class TableBlock:
    """Один непрерывный блок табличных строк в списке физических строк.

    start — индекс первой строки блока; end — индекс последней (включительно);
    оба — индексы в исходном списке lines. rows — все строки блока, кроме
    разделителя (строка заголовка при header=True — это rows[0]).
    header — разделитель стоит сразу после первой строки блока.
    separator_index — индекс строки-разделителя в исходных lines (или None).
    n_cols_header — число ячеек первой строки блока. warnings —
    человекочитаемые предупреждения (разделитель не на второй позиции и т.п.).
    """
    start: int
    end: int
    rows: List[List[str]]
    header: bool
    separator_index: Optional[int]
    n_cols_header: int
    warnings: List[str] = field(default_factory=list)


def find_table_blocks(lines: List[str]) -> List[TableBlock]:
    """Находит все блоки подряд идущих табличных строк (включая разделители).

    Блок = максимальная серия подряд идущих строк, для которых split_table_row
    возвращает список (любая нетабличная строка — даже пустая — разрывает блок).
    Разделитель, оказавшийся не на второй позиции блока, отбрасывается (не
    попадает ни в rows, ни в separator_index) и даёт предупреждение; сам блок
    при этом продолжается. Блок из одной строки без разделителя — тоже блок
    (header=False). Порядок и число ячеек строк сохраняются как есть.
    """
    blocks: List[TableBlock] = []
    i, n = 0, len(lines)
    while i < n:
        if split_table_row(lines[i]) is None:
            i += 1
            continue
        start = i
        while i < n and split_table_row(lines[i]) is not None:
            i += 1
        end = i - 1
        block = TableBlock(start=start, end=end, rows=[], header=False,
                           separator_index=None,
                           n_cols_header=len(split_table_row(lines[start])),
                           warnings=[])
        # Первая строка блока.
        first = split_table_row(lines[start])
        if is_table_separator(lines[start]):
            # Разделитель на первой позиции блока — не на второй: отбросить.
            block.warnings.append(
                f'line {start + 1}: table separator at block start (no header row); dropped')
        else:
            block.rows.append(first)
        # Остальные строки блока.
        for j in range(start + 1, end + 1):
            if is_table_separator(lines[j]):
                if j == start + 1 and len(block.rows) == 1:
                    block.header = True
                    block.separator_index = j
                else:
                    block.warnings.append(
                        f'line {j + 1}: table separator not at block position 2; dropped')
            else:
                block.rows.append(split_table_row(lines[j]))
        blocks.append(block)
    return blocks


def build_table_row(cells: List[str]) -> str:
    r"""Собирает md-строку таблицы из списка ячеек.

    Каждая непустая ячейка рендерится как « текст », пустая — как « »;
    результат: «|» + «|».join(...) + «|». Экранирование («|» → «\|») и
    CR/LF → пробел применяются внутри (escape_cell). Примеры:
    ["a","b"] → «| a | b |»; [""] → «| |»; ["a","","b"] → «| a | | b |».
    Формат детерминированный; байт-в-байт круг гарантируется только для
    нормализованного ввода.
    """
    rendered = []
    for c in cells:
        escaped = escape_cell(c)
        rendered.append(f' {escaped} ' if escaped else ' ')
    return '|' + '|'.join(rendered) + '|'


def build_table_separator(n_cols: int) -> str:
    """Собирает строку-разделитель: «|---|---|…» для n_cols столбцов (n_cols ≥ 1).

    Выравнивание («:---:» и т.п.) не поддерживается: разделитель всегда
    канонический, см. докстринг модуля.
    """
    if n_cols < 1:
        raise ValueError(f'n_cols must be >= 1, got {n_cols}')
    return '|---' * n_cols + '|'
