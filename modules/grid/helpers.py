"""
Grid-хелперы, извлечённые из Supervertaler.SupervertalerQt (Batch #6 Stage 2,
Step 6 of EXTRACTION_PLAN.md).

Архитектура (решение владельца, Stage 1 §6): МОДУЛЬ ЧИСТЫХ ФУНКЦИЙ — без класса
и без ссылок на главное окно. Каждая функция получает нужный контекст явными
параметрами (current_project, table, виджеты пагинации) и именованными
колбэками для зависимостей, которые пока остаются в монолите (go_to_page,
_apply_pagination_to_grid, _auto_resize_single_row, log).

SupervertalerQt сохраняет 17 тонких одноимённых делегатов (16 вызывают функции
этого модуля; _get_line_edit_text остаётся в монолите целиком — его
getattr/setattr-логика разрешения атрибута ПО ИМЕНИ self-специфична, п.Г
промпта Stage 2), поэтому все call sites продолжают работать без изменений,
включая bound-методы, захваченные modules/undo_manager.py
(_find_row_for_segment, _select_grid_row_by_id — критично для Undo/Redo).

Внутренние вызовы helpers → helpers (select_grid_row_by_id →
find_row_for_segment; get_selected_or_filtered_segments →
get_selected_segments_from_grid) — простые вызовы функций одного модуля.
"""

import re
from typing import Dict, List, Optional, Tuple

from PyQt6 import sip
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (QMessageBox, QTableWidget, QTextEdit,
                             QTableWidgetItem, QWidget)

from modules.models import Segment

__all__ = [
    "widget_is_alive",
    "segment_for_grid_row",
    "recompute_list_numbers",
    "reindex_grid_rows_from",
    "find_row_for_segment",
    "find_row_for_segment_id",
    "select_grid_row_by_id",
    "compute_initial_visible_rows",
    "navigate_to_segment_in_grid",
    "navigate_to_segment_by_id",
    "get_selected_segments_from_grid",
    "get_selected_or_filtered_segments",
    "resize_visible_rows",
    "move_to_next_visible_row",
    "is_text_filter_active",
    "get_filtered_segments_with_rows",
]


def widget_is_alive(widget: Optional[QWidget]) -> bool:
    """Возвращает True, если базовый Qt-объект ещё существует."""
    if widget is None:
        return False
    try:
        return not sip.isdeleted(widget)
    except RuntimeError:
        return False


def segment_for_grid_row(current_project, table, row: int):
    """Вернуть (segment, индекс_в_списке) для строки сетки — по id в колонке 0.

    Возвращает (None, -1), если строка или id не распознаны. Использование колонки
    id (а не индекса строки) сохраняет корректность при пагинации."""
    if not current_project:
        return None, -1
    try:
        id_item = table.item(row, 0)
        sid = int(id_item.text())
    except (AttributeError, ValueError, TypeError):
        return None, -1
    for i, s in enumerate(current_project.segments):
        if s.id == sid:
            return s, i
    return None, -1


def recompute_list_numbers(current_project) -> Dict[int, int]:
    """Пересобрать индекс «строка сетки → номер в упорядоченном списке» после
    структурного изменения, зеркально предварительному проходу в
    load_segments_to_grid.

    Чистая функция: строит НОВЫЙ словарь с нуля из current_project.segments
    (старое значение _list_numbers окна не читается); делегат в монолите
    присваивает результат self._list_numbers."""
    list_counter = 0
    last_was_list = False
    list_numbers = {}
    for idx, segment in enumerate(current_project.segments):
        source_text = (segment.source or "").strip()
        is_list_item = source_text.startswith(('<li-o>', '<li-b>', '<li>'))
        is_ordered = source_text.startswith('<li-o>') or (
            source_text.startswith('<li>') and not source_text.startswith('<li-b>'))
        if is_list_item and is_ordered:
            m = re.match(r'^<li(?:-o)?>\s*(\d+)[.)\s]', source_text)
            if m:
                list_counter = int(m.group(1))
                list_numbers[idx] = list_counter
                last_was_list = True
            elif last_was_list:
                list_counter += 1
                list_numbers[idx] = list_counter
            else:
                list_counter = 1
                list_numbers[idx] = list_counter
                last_was_list = True
        else:
            last_was_list = False
            list_counter = 0
    return list_numbers


def reindex_grid_rows_from(current_project, table, start_row: int) -> set:
    """После вставки/удаления исправить текст ячейки # и поле .row виджетов
    ячеек для всех строк от start_row и далее (здесь строка сетки == индекс
    списка) и пересчитать множество заполненных строк. Дёшево: без
    пересоздания виджетов.

    Мутирует переданный table на месте (Qt-виджет, мутация по ссылке ожидаема)
    и возвращает НОВОЕ множество заполненных строк; делегат присваивает его
    self._populated_rows."""
    segs = current_project.segments
    n = table.rowCount()
    for r in range(start_row, n):
        if r >= len(segs):
            break
        seg = segs[r]
        id_item = table.item(r, 0)
        if id_item is None:
            id_item = QTableWidgetItem()
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r, 0, id_item)
        id_item.setText(str(seg.id))
        for col in (2, 3, 4, 5):
            w = table.cellWidget(r, col)
            if w is not None and hasattr(w, 'row'):
                w.row = r
    return {
        r for r in range(n) if table.cellWidget(r, 2) is not None
    }


def find_row_for_segment(table, segment_id: int) -> int:
    """Находит индекс строки сетки для сегмента по ID."""
    if not table:
        return -1

    for row in range(table.rowCount()):
        id_item = table.item(row, 0)
        if id_item:
            try:
                if int(id_item.text()) == segment_id:
                    return row
            except (ValueError, AttributeError):
                continue
    return -1


def find_row_for_segment_id(table, segment_id: int) -> int:
    """Возвращает индекс строки для ID сегмента в видимой таблице или -1,
    если сегмента нет на текущей странице. Хелпер для адресного
    обновления якорей после создания/правки одного комментария."""
    if not table:
        return -1
    for row in range(table.rowCount()):
        id_item = table.item(row, 0)
        if id_item:
            try:
                if int(id_item.text()) == segment_id:
                    return row
            except (ValueError, AttributeError):
                continue
    return -1


def select_grid_row_by_id(table, focus_id) -> None:
    """Выбрать и прокрутить к строке сетки с сегментом focus_id и передать
    фокус таблице.

    Передача фокуса таблице важна после структурного изменения: если фокус остался
    в QTextEdit ячейки, тот перехватит следующий Ctrl+Z (собственный текстовый undo)
    вместо того, чтобы сработал app-уровневый структурный undo."""
    if focus_id is None:
        return
    r = find_row_for_segment(table, focus_id)
    if r >= 0:
        table.selectRow(r)
        table.setCurrentCell(r, 2)
        it = table.item(r, 0)
        if it is not None:
            table.scrollToItem(it)
    # Defer the focus move: when invoked from the right-click context menu,
    # the menu restores focus to the source cell as it closes — which would
    # override an immediate setFocus and let that cell swallow the next
    # Ctrl+Z. Running on the next event-loop tick lands focus on the table
    # after the menu has finished closing, so Ctrl+Z reaches structural undo.
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(0, table.setFocus)


def compute_initial_visible_rows(total: int, filter_allowlist=None,
                                 page_size: int = 50,
                                 current_page: int = 0) -> set:
    """Возвращает множество индексов строк, которые должны получить полные
    виджеты-редакторы при начальной загрузке сетки (только текущая страница).

    Часть оптимизации загрузки сетки с учётом страниц в v1.10.147
    (на основе форка Simpelvertaler Ханса Лентинга). Вне-страничные
    строки получают дешёвую заглушку QTableWidgetItem и лениво
    заполняются обработчиком пагинации, когда становятся видимыми.

    Состояние окна (allowlist текстового фильтра, размер/номер страницы)
    передаётся делегатом через getattr с теми же значениями по умолчанию,
    что были в исходном теле (50 / 0)."""
    if filter_allowlist is not None:
        return set(filter_allowlist)
    if not isinstance(page_size, int) or page_size <= 0 or page_size >= 999999:
        # "All" mode (or unset) — populate every row.
        return set(range(total))
    start_row = current_page * page_size
    end_row = min(start_row + page_size, total)
    return set(range(start_row, end_row))


def navigate_to_segment_in_grid(current_project, table, main_tabs,
                                page_size_combo, page_number_input,
                                segment_id, go_to_page_callback,
                                log_callback) -> None:
    """Переходит к сегменту с заданным ID в сетке.

    Виджеты пагинации (main_tabs, page_size_combo, page_number_input)
    передаются явно; hasattr-защиты исходного тела превращены в проверки
    «is not None» — делегат резолвит атрибуты через getattr(..., None), что
    эквивалентно для всех реальных случаев (атрибут либо не создан, либо
    живой виджет)."""
    if not current_project or not table:
        return

    # Find the row for this segment ID
    for row in range(table.rowCount()):
        id_item = table.item(row, 0)
        if id_item:
            try:
                row_segment_id = int(id_item.text())
                if row_segment_id == segment_id:
                    # Switch to Grid tab first
                    if main_tabs is not None:
                        main_tabs.setCurrentIndex(0)  # Grid tab

                    # Handle pagination - switch to correct page if needed
                    if page_size_combo is not None and page_size_combo.currentText() != "All":
                        try:
                            page_size = int(page_size_combo.currentText())
                            target_page = (row // page_size) + 1
                            if page_number_input is not None:
                                page_number_input.setText(str(target_page))
                                go_to_page_callback()
                        except ValueError:
                            pass

                    # Select this row and focus the target cell
                    table.setCurrentCell(row, 3)  # Column 3 = Target
                    table.scrollToItem(table.item(row, 0), QTableWidget.ScrollHint.PositionAtCenter)

                    target_widget = table.cellWidget(row, 3)
                    if target_widget:
                        target_widget.setFocus()
                        # Place cursor at end of text
                        if isinstance(target_widget, QTextEdit):
                            cursor = target_widget.textCursor()
                            cursor.movePosition(cursor.MoveOperation.End)
                            target_widget.setTextCursor(cursor)

                    log_callback(f"📄 Preview: Navigated to segment {segment_id}")
                    return
            except (ValueError, AttributeError):
                continue


def navigate_to_segment_by_id(current_project, table, main_tabs,
                              page_size_combo, page_number_input,
                              grid_current_page, segment_id,
                              go_to_page_callback, log_callback) -> None:
    """Переходит к сегменту по ID, при необходимости сначала переключая страницу.

    В отличие от navigate_to_segment_in_grid (который ищет сегмент по индексу
    строки в *видимой сейчас* таблице), эта версия находит индекс сегмента в
    полном списке сегментов проекта, вычисляет нужную страницу, переключается
    на неё, если мы ещё не там, и только затем выбирает строку. Корректно
    работает через границы пагинации."""
    if not current_project or not current_project.segments:
        return
    if not table:
        return

    # Locate the target segment in the full project list.
    segments = current_project.segments
    target_idx = None
    for i, seg in enumerate(segments):
        if seg.id == segment_id:
            target_idx = i
            break
    if target_idx is None:
        log_callback(f"⚠ Segment #{segment_id} not found in project")
        return

    # If pagination is active and the segment is on a different page,
    # switch to that page first. The grid rebuilds synchronously
    # inside go_to_page, so by the time it returns the target row
    # is visible.
    if page_size_combo is not None and page_size_combo.currentText() != "All":
        try:
            page_size = int(page_size_combo.currentText())
            target_page = (target_idx // page_size) + 1
            current_page = grid_current_page + 1
            if current_page != target_page and page_number_input is not None:
                page_number_input.setText(str(target_page))
                go_to_page_callback()
        except (ValueError, AttributeError):
            pass

    # Switch to the Grid (Editor) tab if we're elsewhere.
    if main_tabs is not None:
        main_tabs.setCurrentIndex(0)

    # Find the row in the (possibly newly-rebuilt) table and select it.
    for row in range(table.rowCount()):
        id_item = table.item(row, 0)
        if id_item:
            try:
                if int(id_item.text()) == segment_id:
                    table.setCurrentCell(row, 3)  # Column 3 = Target
                    table.scrollToItem(
                        table.item(row, 0),
                        QTableWidget.ScrollHint.PositionAtCenter,
                    )
                    target_widget = table.cellWidget(row, 3)
                    if target_widget:
                        target_widget.setFocus()
                    return
            except (ValueError, AttributeError):
                continue

    # Reaching here means the page-switch logic didn't put the
    # segment on the current page — shouldn't happen but log it.
    log_callback(
        f"⚠ Segment #{segment_id} not on current grid page after "
        f"page-switch attempt (unexpected)"
    )


def get_selected_segments_from_grid(current_project, table) -> list:
    """Возвращает список выбранных сегментов из сетки."""
    if not current_project or not table:
        return []

    selected_rows = set()
    for item in table.selectedItems():
        selected_rows.add(item.row())

    segments = []
    for row in sorted(selected_rows):
        if 0 <= row < len(current_project.segments):
            segments.append(current_project.segments[row])

    return segments


def get_selected_or_filtered_segments(current_project, table, parent_widget,
                                      operation_name: str) -> list:
    """Возвращает сегменты для массовой операции: сначала выбранные строки,
    затем, как откат, отфильтрованные строки.

    Аргументы:
        operation_name: человекочитаемое имя для диалога подтверждения
                        (например, «Confirm Segments»)
        parent_widget:  родительский QWidget для QMessageBox (в монолите —
                        само главное окно)

    Возвращает:
        Список объектов Segment или пустой список, если пользователь
        отменил или ничего недоступно."""
    selected = get_selected_segments_from_grid(current_project, table)
    if selected:
        return selected

    # No selection – check for filtered (visible) rows
    visible_rows = [row for row in range(table.rowCount())
                    if not table.isRowHidden(row)]
    total_rows = table.rowCount()

    if len(visible_rows) < total_rows and len(visible_rows) > 0:
        reply = QMessageBox.question(
            parent_widget, operation_name,
            f"No segments selected.\n\n"
            f"Apply '{operation_name}' to all {len(visible_rows)} filtered (visible) segments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            return [current_project.segments[row] for row in visible_rows
                    if row < len(current_project.segments)]
        return []

    QMessageBox.information(parent_widget, "No Selection",
        "Please select one or more segments, or apply a filter first.")
    return []


def resize_visible_rows(table, auto_resize_callback) -> None:
    """Меняет размер только видимых (не скрытых) строк для эффективности
    после изменений пагинации/фильтра.

    _auto_resize_single_row остаётся в монолите (populate/render-кластер,
    Step 8) и передаётся делегатом колбэком."""
    if not table:
        return
    row_count = table.rowCount()
    for row in range(row_count):
        if not table.isRowHidden(row):
            auto_resize_callback(row)


def move_to_next_visible_row(current_project, table, current_row,
                             grid_page_size=50, grid_current_page=0,
                             set_grid_page_callback=None,
                             apply_pagination_callback=None,
                             log_callback=None) -> None:
    """Переводит фокус на следующую видимую строку после current_row
    (учитывает фильтры + пагинацию).

    Состояние пагинации пока живёт на главном окне (Stage 3 перенесёт его в
    pagination.py), поэтому запись номера страницы и переприменение пагинации
    передаются делегатом двумя колбэками в порядке исходного тела:
        set_grid_page_callback(target_page) -> self.grid_current_page = target_page
        apply_pagination_callback()         -> self._apply_pagination_to_grid()"""
    if not table or not current_project:
        return

    row_count = table.rowCount()
    if row_count <= 0:
        return

    page_size = grid_page_size
    has_pagination = isinstance(page_size, int) and page_size < 999999 and page_size > 0

    last_page_applied = grid_current_page

    for row in range(current_row + 1, row_count):
        if has_pagination:
            target_page = row // page_size
            if target_page != last_page_applied:
                set_grid_page_callback(target_page)
                last_page_applied = target_page
                apply_pagination_callback()

        if not table.isRowHidden(row):
            table.clearSelection()
            table.setCurrentCell(row, 3)
            id_item = table.item(row, 0)
            if id_item is not None:
                table.scrollToItem(id_item)

            target_widget = table.cellWidget(row, 3)
            if target_widget:
                target_widget.setFocus()
                target_widget.moveCursor(QTextCursor.MoveOperation.End)
            return

    # No more visible rows
    log_callback("✅ No more filtered segments")


def is_text_filter_active(source_text: str, target_text: str) -> bool:
    """Возвращает True, если в полях Filter Source/Target сейчас есть текст.

    Разрешение виджетов фильтра по имени атрибута (и починка мёртвых ссылок)
    — self-специфичная логика и остаётся в делегате _get_line_edit_text
    монолита (п.Г промпта Stage 2), поэтому сюда приходят уже извлечённые
    тексты."""
    return bool(source_text.strip() or target_text.strip())


def get_filtered_segments_with_rows(current_project, table) -> List[Tuple[int, Segment]]:
    """Возвращает видимые/отфильтрованные сейчас сегменты как (row_index, segment)."""
    if not current_project:
        return []

    # Check if table is currently filtered
    if not table or table.rowCount() == 0:
        return []

    visible_segments: List[Tuple[int, Segment]] = []

    # Iterate through visible rows in the table
    for visual_row in range(table.rowCount()):
        if not table.isRowHidden(visual_row):
            # Get the segment from this row
            # The visual row index corresponds to the segment index in the project
            if visual_row < len(current_project.segments):
                seg = current_project.segments[visual_row]
                visible_segments.append((visual_row, seg))

    return visible_segments
