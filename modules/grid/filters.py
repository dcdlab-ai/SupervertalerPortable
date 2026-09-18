"""Фильтры и отображение невидимых символов грида, извлечённые из
Supervertaler.SupervertalerQt (Batch #6 Stage 4, Step 6 of EXTRACTION_PLAN.md).

Архитектура — та же, что в helpers.py (Stage 2) и pagination.py (Stage 3),
решение владельца Stage 1 §6: МОДУЛЬ ЧИСТЫХ ФУНКЦИЙ — без класса и без ссылок
на главное окно. Каждая функция получает нужный контекст явными параметрами и
именованными колбэками для зависимостей, которые пока остаются в монолите
(log, populate-механика, диалоги представлений, границы файлов, ресайз).

SupervertalerQt сохраняет 20 тонких одноимённых делегатов, поэтому все call
sites продолжают работать без изменений, включая:
- modules/undo_manager.py:215 — bound-метод apply_invisible_replacements,
  инжектируемый при конструировании UndoManager (Batch #5);
- modules/pseudo_translate_dialog.py:250 — hasattr-охраняемый прямой вызов
  mw.apply_invisible_replacements(new_target) (имя метода и сигнатура
  «один позиционный аргумент → строка» — строковый контракт);
- modules/shortcut_manager.py:642/648 — записи "filter_selected_text" и
  "clear_filter" с "action": "filter_on_selected_text" (имя метода — часть
  строкового контракта диспетчера горячих клавиш).

Слой helpers: widget_is_alive импортируется напрямую из modules.grid.helpers
(тот же принцип, что resize_visible_rows/widget_is_alive в pagination.py,
Stage 3), а не передаётся колбэком.

Классы монолита (TagHighlighter, EditableGridTextEditor,
ReadOnlyGridTextEditor) сюда НЕ импортируются — это был бы циклический
импорт (монолит импортирует modules.grid):
- флаг подсветки NBSP записывается через set_show_nbsp_callback;
- классы текстовых редакторов передаются параметром editor_classes.

Единственная точка пересечения с циклом SCC#1 — apply_sort: полная
перезагрузка грида идёт через reload_callback (делегат передаёт
self.load_segments_to_grid); сам load_segments_to_grid не тронут.
"""

from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (QApplication, QDialog, QLineEdit, QMessageBox,
                             QProgressDialog, QTableWidget)

from modules.dialogs import AdvancedFiltersDialog
from modules.shortcut_display import format_shortcut_for_display
from modules.tag_manager import (compact_tags, protect_tags_from_linebreak,
                                 strip_outer_wrapping_tags, WORD_JOINER)

from modules.grid.helpers import widget_is_alive

__all__ = [
    "highlight_text_in_widget",
    "clear_filter_highlights_in_widget",
    "apply_filters",
    "clear_filters",
    "on_file_filter_changed",
    "update_file_filter_combo",
    "toggle_invisible_display",
    "toggle_all_invisibles",
    "refresh_grid_invisibles",
    "apply_invisible_replacements",
    "reverse_invisible_replacements",
    "filter_empty_segments",
    "clear_all_filter_highlights",
    "apply_quick_filter",
    "show_advanced_filters_dialog",
    "apply_advanced_filters",
    "apply_sort",
    "filter_on_selected_text",
    "ensure_shared_filter",
    "ensure_primary_filters_ready",
]


def highlight_text_in_widget(table, row: int, col: int, search_term: str):
    """Подсвечивает поисковый терм внутри виджета ячейки QTextEdit.

    Поскольку ячейки источника/перевода используют setCellWidget()
    с редакторами QTextEdit, метод paint() делегата минуется.
    Подсветку нужно делать прямо внутри виджета через QTextCursor
    и QTextCharFormat.

    ПРИМЕЧАНИЕ: эта функция только ДОБАВЛЯЕТ жёлтые подсветки — она не
    снимает существующее форматирование. Для снятия используйте
    clear_filter_highlights_in_widget()."""
    widget = table.cellWidget(row, col)
    if not widget or not hasattr(widget, 'document'):
        return

    # Create yellow highlight format
    highlight_format = QTextCharFormat()
    highlight_format.setBackground(QColor("#FFFF00"))  # Yellow background

    # Find and highlight all occurrences (case-insensitive)
    document = widget.document()
    cursor = QTextCursor(document)

    search_term_lower = search_term.lower()
    text = document.toPlainText()
    text_lower = text.lower()

    # Find all occurrences
    pos = 0
    while True:
        pos = text_lower.find(search_term_lower, pos)
        if pos == -1:
            break

        # Select the match and apply highlight
        cursor.setPosition(pos)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(search_term))
        cursor.mergeCharFormat(highlight_format)

        pos += len(search_term)


def clear_filter_highlights_in_widget(table, row: int, col: int):
    """Убирает жёлтые подсветки фильтра из виджета QTextEdit, сохраняя
    прочее форматирование.

    Это эффективнее, чем перезагружать всю сетку ради снятия
    подсветок."""
    widget = table.cellWidget(row, col)
    if not widget or not hasattr(widget, 'document'):
        return

    # Iterate through the document and clear only yellow backgrounds
    document = widget.document()
    cursor = QTextCursor(document)
    cursor.movePosition(QTextCursor.MoveOperation.Start)

    # Select the entire document
    cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)

    # Get current block and iterate character by character
    # For efficiency, we'll just clear all backgrounds that are yellow
    # This preserves termbase highlights (which are green shades) and tag colors
    block = document.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                fmt = fragment.charFormat()
                bg = fmt.background().color()
                # Check if it's a yellow highlight (filter highlight)
                if bg.name().upper() == "#FFFF00":
                    # Clear this specific range
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.MoveMode.KeepAnchor)
                    clear_fmt = QTextCharFormat()
                    clear_fmt.setBackground(QColor(Qt.GlobalColor.transparent))
                    cursor.mergeCharFormat(clear_fmt)
            it += 1
        block = block.next()


def apply_filters(current_project, table, source_filter_text: str,
                  target_filter_text: str, clear_filters_callback,
                  set_filtering_active_callback,
                  set_active_text_filter_rows_callback,
                  apply_pagination_callback, log_callback):
    """Применяет фильтры источника и перевода, показывая/скрывая строки
    и подсвечивая совпадения.

    ОПТИМИЗИРОВАНО: сетка больше не перезагружается целиком. Вместо:
    1. Снимаются только жёлтые подсветки фильтра (форматирование
       терминологий/тегов сохраняется).
    2. Строки показываются/скрываются на месте.
    3. На совпадающий текст наносятся новые подсветки.

    Если оба поля фильтров пусты — сразу передаёт работу
    clear_filters_callback (тот же порядок, что в исходном теле до
    установки filtering_active). Делегат записывает self.filtering_active
    и self._active_text_filter_rows через set-колбэки В ПОРЯДКЕ ИСХОДНОГО
    тела: filtering_active=True до цикла, allowlist после цикла и перед
    повторным применением пагинации."""
    # If both empty, clear everything
    if not source_filter_text and not target_filter_text:
        clear_filters_callback()
        return

    # Set flag to disable auto-center scrolling during filtering
    set_filtering_active_callback(True)

    # Track which rows match the active text filters so pagination can respect filtering
    matching_rows: set[int] = set()

    # Batch UI updates for performance
    table.setUpdatesEnabled(False)

    try:
        visible_count = 0
        segments = current_project.segments
        total_segments = len(segments)

        # Pre-compute lowercase filter texts
        source_filter_lower = source_filter_text.lower() if source_filter_text else None
        target_filter_lower = target_filter_text.lower() if target_filter_text else None

        # IMPORTANT: Always search through ALL segments, not just visible rows
        # Pagination state should not affect which segments we search
        for row in range(total_segments):
            if row >= total_segments:
                break

            segment = segments[row]
            source_lower = segment.source.lower()
            target_lower = segment.target.lower()

            source_match = not source_filter_lower or source_filter_lower in source_lower
            target_match = not target_filter_lower or target_filter_lower in target_lower

            show_row = source_match and target_match

            if show_row:
                matching_rows.add(row)

            if show_row:
                visible_count += 1

                # Clear previous filter highlights first (only yellow, preserves other formatting)
                clear_filter_highlights_in_widget(table, row, 2)
                clear_filter_highlights_in_widget(table, row, 3)

                # Highlight matching terms in the QTextEdit widgets
                if source_filter_lower and source_filter_lower in source_lower:
                    highlight_text_in_widget(table, row, 2, source_filter_text)

                if target_filter_lower and target_filter_lower in target_lower:
                    highlight_text_in_widget(table, row, 3, target_filter_text)
            else:
                # Clear highlights from hidden rows too (for when they become visible again)
                clear_filter_highlights_in_widget(table, row, 2)
                clear_filter_highlights_in_widget(table, row, 3)
    finally:
        # Re-enable UI updates
        table.setUpdatesEnabled(True)

    # Persist allowlist and apply combined pagination+filter visibility
    set_active_text_filter_rows_callback(matching_rows)
    if apply_pagination_callback is not None:
        apply_pagination_callback()

    # Update status
    if source_filter_text or target_filter_text:
        log_callback(f"Filter applied: showing {visible_count} of {len(current_project.segments)} segments")


def clear_filters(current_project, table, source_widget, target_widget,
                  set_active_text_filter_rows_callback,
                  set_filtering_active_callback, apply_pagination_callback,
                  set_grid_page_callback, set_file_filter_callback,
                  log_callback, grid_page_size=50, grid_current_page=0):
    """Очищает все поля фильтров, подсветки и показывает все строки.

    ОПТИМИЗИРОВАНО: сетка больше не перезагружается целиком. Вместо:
    1. Снимаются только жёлтые подсветки фильтра (форматирование
       терминологий/тегов сохраняется).
    2. Все строки показываются на месте.
    3. Намного быстрее перезагрузки всех виджетов.

    Делегат уже разрешил живость source_filter/target_filter (мёртвые
    виджеты приходят как None, а само-атрибут обнуляет сам) и передал
    getattr-дефолты grid_page_size (50) / grid_current_page (0). Запись
    страницы при возврате к выбранному сегменту идёт через
    set_grid_page_callback — ДО повторного применения пагинации, как в
    исходном теле; сброс файлового фильтра на «All Files» — через
    set_file_filter_callback."""
    # Clear delegate highlights and global search terms
    if table is not None:
        delegate = table.itemDelegate()
        if delegate:
            if hasattr(delegate, 'clear_all_highlights'):
                delegate.clear_all_highlights()
            # Clear global search terms
            delegate.global_search_term = None
            delegate.global_source_search_term = None

    # Remember which segment was selected before clearing
    selected_segment_id = None
    current_column = 3  # Default to target column
    if current_project and table is not None:
        current_row = table.currentRow()
        current_column = table.currentColumn()

        if current_row >= 0:
            # Get segment ID directly from the ID cell (column 0)
            id_item = table.item(current_row, 0)
            if id_item:
                try:
                    selected_segment_id = int(id_item.text())
                except (ValueError, AttributeError):
                    pass

    if source_widget is not None:
        source_widget.blockSignals(True)
        source_widget.clear()
        source_widget.blockSignals(False)

    if target_widget is not None:
        target_widget.blockSignals(True)
        target_widget.clear()
        target_widget.blockSignals(False)

    # Clear any active text-filter allowlist so pagination can show rows normally
    set_active_text_filter_rows_callback(None)

    # OPTIMIZED: Clear highlights and show rows WITHOUT reloading grid
    if current_project:
        # Safety check: ensure table exists
        if table is None:
            return

        # Batch UI updates for performance
        table.setUpdatesEnabled(False)

        try:
            row_count = table.rowCount()

            for row in range(row_count):
                # Clear yellow filter highlights (preserves other formatting)
                clear_filter_highlights_in_widget(table, row, 2)  # Source
                clear_filter_highlights_in_widget(table, row, 3)  # Target

                # Show all rows
                table.setRowHidden(row, False)
        finally:
            # Re-enable UI updates
            table.setUpdatesEnabled(True)

        # Clear filtering flag to re-enable auto-center
        set_filtering_active_callback(False)

        # Resolve the previously selected segment's row index BEFORE we
        # re-apply pagination. If pagination is on, we need to switch to
        # the page that contains this row first; otherwise the row stays
        # hidden and the scroll/select call below silently no-ops on a
        # hidden cell, leaving the user looking at page 1 even though
        # they were working at the end of the project.
        target_row = None
        if selected_segment_id is not None:
            for row, segment in enumerate(current_project.segments):
                if segment.id == selected_segment_id:
                    target_row = row
                    break

        page_size = grid_page_size
        if target_row is not None and page_size and page_size < 999999:
            target_page = target_row // page_size
            if grid_current_page != target_page:
                set_grid_page_callback(target_page)

        # Re-apply pagination after clearing filters (also resizes visible rows)
        if apply_pagination_callback is not None:
            apply_pagination_callback()

        # Restore selection to the previously selected segment.
        # PositionAtCenter centres it in the viewport so the user lands
        # back where they were looking, not at the top of the page.
        if target_row is not None:
            table.setCurrentCell(target_row, current_column)
            table.scrollToItem(
                table.item(target_row, 0),
                QTableWidget.ScrollHint.PositionAtCenter
            )

    # Reset file filter to "All Files"
    if set_file_filter_callback is not None:
        set_file_filter_callback()

    log_callback("Filters cleared")


def on_file_filter_changed(current_project, table, file_filter_combo,
                           apply_pagination_callback,
                           update_file_boundary_callback,
                           show_manage_views_callback, log_callback):
    """Обрабатывает смену выпадающего списка файлового фильтра для
    мультифайловых проектов.

    Диалог сохранённых представлений остаётся методом главного окна
    (НЕ в составе Stage 4): вызывается через show_manage_views_callback.
    Обновление меток границ файлов — метод монолита (Step 8/теги)."""
    data = file_filter_combo.currentData()

    # "Manage Views..." action
    if data == "manage_views":
        # Reset to previous selection (All Files) before opening dialog
        file_filter_combo.blockSignals(True)
        file_filter_combo.setCurrentIndex(0)
        file_filter_combo.blockSignals(False)
        show_manage_views_callback()
        return

    if data is None:
        # "All Files" selected - re-apply pagination (keeps empty segments hidden)
        if apply_pagination_callback is not None:
            apply_pagination_callback()
        update_file_boundary_callback()
        log_callback("File filter: showing all files")
        return

    if table is None:
        return

    # View selected (dict with view_file_ids)
    if isinstance(data, dict) and 'view_file_ids' in data:
        view_file_ids = set(data['view_file_ids'])
        visible_count = 0
        for row, segment in enumerate(current_project.segments):
            if row >= table.rowCount():
                break
            segment_file_id = getattr(segment, 'file_id', None)
            show_row = segment_file_id in view_file_ids and segment.source.strip()
            table.setRowHidden(row, not show_row)
            if show_row:
                visible_count += 1
        log_callback(f"View filter: showing {visible_count} segments from {len(view_file_ids)} files")
        update_file_boundary_callback()
        return

    # Single file selected (int file_id)
    file_id = data
    visible_count = 0
    for row, segment in enumerate(current_project.segments):
        if row >= table.rowCount():
            break
        segment_file_id = getattr(segment, 'file_id', None)
        show_row = segment_file_id == file_id and segment.source.strip()
        table.setRowHidden(row, not show_row)
        if show_row:
            visible_count += 1

    file_name = "Unknown"
    files = getattr(current_project, 'files', [])
    for f in files:
        if f['id'] == file_id:
            file_name = f['name']
            break

    log_callback(f"File filter: showing {visible_count} segments from '{file_name}'")
    update_file_boundary_callback()


def update_file_filter_combo(current_project, file_filter_combo):
    """Обновляет выпадающий список файлового фильтра файлами и
    представлениями текущего проекта."""
    file_filter_combo.blockSignals(True)
    file_filter_combo.clear()
    file_filter_combo.addItem("All Files", None)

    is_multifile = getattr(current_project, 'is_multifile', False) if current_project else False
    files = getattr(current_project, 'files', []) if current_project else []

    if is_multifile and files:
        # Saved views section
        views = getattr(current_project, 'views', []) or []
        if views:
            file_filter_combo.insertSeparator(file_filter_combo.count())
            for view in views:
                view_name = view.get('name', 'Unnamed View')
                file_count = len(view.get('file_ids', []))
                file_filter_combo.addItem(
                    f"\U0001F441 {view_name} ({file_count} files)",
                    {"view_file_ids": view.get('file_ids', [])}
                )

        # Individual files section
        file_filter_combo.insertSeparator(file_filter_combo.count())
        for file_info in files:
            file_id = file_info['id']
            file_name = file_info['name']
            seg_count = file_info.get('segment_count', 0)
            file_filter_combo.addItem(f"\U0001F4C4 {file_name} ({seg_count} seg)", file_id)

        # Manage Views action
        file_filter_combo.insertSeparator(file_filter_combo.count())
        file_filter_combo.addItem("Manage Views...", "manage_views")

        file_filter_combo.show()
    else:
        file_filter_combo.hide()

    file_filter_combo.blockSignals(False)


def toggle_invisible_display(invisible_display_settings: Dict[str, bool],
                             char_type: str, set_show_nbsp_callback,
                             refresh_callback, log_callback,
                             write_settings_callback=None) -> Dict[str, bool]:
    """Переключает отображение конкретного типа невидимых символов.

    Получает текущий словарь настроек (делегат инициализирует дефолтом,
    если атрибута ещё нет) и возвращает НОВЫЙ словарь — делегат записывает
    его в self.invisible_display_settings. Флаг подсветки NBSP у
    TagHighlighter записывается через set_show_nbsp_callback (класс живёт
    в монолите — прямой импорт дал бы цикл). write_settings_callback
    вызывается ДО refresh-колбэка (порядок исходного тела: запись
    настроек → флаг NBSP → refresh → log)."""
    # Toggle the setting
    invisible_display_settings[char_type] = not invisible_display_settings[char_type]

    # Keep the highlighter NBSP-shading flag in sync (covers the no-project case too,
    # where the grid invisibles refresh early-returns before it can update the flag).
    set_show_nbsp_callback(invisible_display_settings.get('nbsp', False))

    # Refresh the grid to show/hide invisibles (re-runs the highlighter via setPlainText)
    if write_settings_callback is not None:
        write_settings_callback(invisible_display_settings)
    if refresh_callback is not None:
        refresh_callback()

    # Log the change
    status = "enabled" if invisible_display_settings[char_type] else "disabled"
    char_names = {
        'spaces': 'Spaces',
        'tabs': 'Tabs',
        'nbsp': 'Non-breaking Spaces',
        'linebreaks': 'Line Breaks'
    }
    log_callback(f"Show invisibles: {char_names[char_type]} {status}")
    return invisible_display_settings


def toggle_all_invisibles(invisible_display_settings: Dict[str, bool],
                          menu_actions, set_show_nbsp_callback,
                          refresh_callback, log_callback,
                          write_settings_callback=None) -> Dict[str, bool]:
    """Включает или выключает все невидимые символы.

    menu_actions — уже разрешённые делегатом действия меню
    (show_spaces_action / show_tabs_action / show_nbsp_action /
    show_linebreaks_action; отсутствующие передаются как None и
    пропускаются). Сигналы блокируются, чтобы setChecked() не вызвал
    повторный toggle и 4 лишние перезагрузки сетки. Возвращает НОВЫЙ
    словарь настроек — делегат записывает его в
    self.invisible_display_settings. write_settings_callback вызывается
    ДО refresh-колбэка (порядок исходного тела: запись настроек →
    флаг NBSP → refresh → log)."""
    # Check if any are currently on
    any_on = any(invisible_display_settings.values())

    # Toggle all to opposite state
    new_state = not any_on
    invisible_display_settings = {
        'spaces': new_state,
        'tabs': new_state,
        'nbsp': new_state,
        'linebreaks': new_state
    }

    # Keep the highlighter NBSP-shading flag in sync (covers the no-project case too).
    set_show_nbsp_callback(invisible_display_settings.get('nbsp', False))

    # Update menu checkboxes – block signals so setChecked() does NOT re-fire
    # the per-type toggle and cause 4 extra grid reloads
    for action in menu_actions:
        if action is not None:
            action.blockSignals(True)
            action.setChecked(new_state)
            action.blockSignals(False)

    # Refresh the grid (in-place, no full reload; re-runs the highlighter via setPlainText)
    if write_settings_callback is not None:
        write_settings_callback(invisible_display_settings)
    if refresh_callback is not None:
        refresh_callback()

    status = "enabled" if new_state else "disabled"
    log_callback(f"Show invisibles: All {status}")
    return invisible_display_settings


def refresh_grid_invisibles(current_project, table,
                            invisible_display_settings: Dict[str, bool],
                            hide_outer_wrapping_tags: bool, tag_view_mode: str,
                            old_suppress, set_suppress_callback,
                            set_show_nbsp_callback, auto_resize_callback,
                            update_match_panel_callback,
                            update_match_panel_available: bool):
    """Обновляет отображение невидимых символов на месте, без перезагрузки
    сетки.

    Обходит существующие виджеты ячеек и напрямую повторно применяет
    (или снимает) подстановки невидимых символов, избегая дорогого
    полного перестроения сетки, которое запустило бы
    load_segments_to_grid().

    Стратегия обработки сигналов
    -----------------------
    Функция вызывает setPlainText() с заблокированными сигналами Qt на
    каждом виджете. В отличие от полной загрузки сетки мы НЕ
    разблокируем сигналы после — виджеты уже имеют подключённые
    с исходной загрузки сетки обработчики textChanged, и эти
    обработчики остаются активными для будущих правок пользователя.
    Держать сигналы заблокированными только на время setPlainText()
    (и короткого окна отложенных событий) необходимо, чтобы
    устаревшие маркеры невидимых символов не записались обратно
    в segment.target.

    Также поднимается флаг подавления обработчика target-changed
    (_suppress_target_change_handlers) как подстраховка, чтобы любой
    просочившийся сигнал (например, на уже сфокусированной ячейке, чьё
    отложенное событие сработало до вступления blockSignals) молча
    игнорировался обработчиком on_target_text_changed. Запись флага идёт
    через set_suppress_callback (старое значение уже разрешено делегатом
    через getattr(..., False)) — тот же self-специфичный паттерн, что в
    apply_pagination_to_grid (Stage 3). Делегат пишет
    self.showing_invisible_spaces до вызова — тот же порядок тела.

    Подстановки текста — прямым вызовом
    apply_invisible_replacements(text, invisible_display_settings=...)
    из этого же модуля (контекст уже в параметрах)."""
    set_show_nbsp_callback(invisible_display_settings.get('nbsp', False))

    segments = current_project.segments
    row_count = table.rowCount()

    # Suppress the target-changed handler for all cells during the refresh
    set_suppress_callback(True)
    try:
        _refresh_grid_invisibles_cells(table, segments, row_count,
                                       invisible_display_settings,
                                       hide_outer_wrapping_tags, tag_view_mode)
    finally:
        set_suppress_callback(old_suppress)

    # Resize rows since space→middle-dot substitution changes text width
    auto_resize_callback()

    # Refresh Match Panel TM panes so ↵ markers appear/disappear with toggling
    if update_match_panel_available:
        try:
            update_match_panel_callback()
        except Exception:
            pass


def _refresh_grid_invisibles_cells(table, segments, row_count,
                                   invisible_display_settings,
                                   hide_outer_wrapping_tags, tag_view_mode):
    """Внутренний обход ячеек для refresh_grid_invisibles (тело цикла
    исходного метода, перенесено 1:1; не входит в __all__)."""
    for row in range(row_count):
        if row >= len(segments):
            break
        segment = segments[row]

        # --- Source column (col 2) – read-only, no save risk ---
        source_widget = table.cellWidget(row, 2)
        if source_widget is not None:
            source_for_display = segment.source
            if hide_outer_wrapping_tags:
                stripped, _ = strip_outer_wrapping_tags(source_for_display)
                source_for_display = stripped
            if tag_view_mode == 'compact':
                source_for_display = compact_tags(source_for_display)
            new_source_text = apply_invisible_replacements(
                source_for_display,
                invisible_display_settings=invisible_display_settings)
            source_widget.blockSignals(True)
            source_widget.setPlainText(new_source_text)
            source_widget.blockSignals(False)

        # --- Target column (col 3) ---
        # Always use segment.target (the clean, marker-free canonical text)
        # as the source of truth, then re-apply current marker settings.
        target_widget = table.cellWidget(row, 3)
        if target_widget is not None:
            target_for_display = segment.target
            if hide_outer_wrapping_tags:
                stripped, _ = strip_outer_wrapping_tags(target_for_display)
                target_for_display = stripped
            # Apply compact tag shortening (display only – reversed before saving)
            if tag_view_mode == 'compact':
                # Re-use the tag_map built from source so numbering stays consistent
                tag_map = {}
                src_display = segment.source
                if hide_outer_wrapping_tags:
                    src_display, _ = strip_outer_wrapping_tags(src_display)
                compact_tags(src_display, tag_map)
                target_for_display = compact_tags(target_for_display, tag_map)
                target_widget._compact_tag_map = tag_map
            else:
                target_widget._compact_tag_map = None
            new_target_text = apply_invisible_replacements(
                target_for_display,
                invisible_display_settings=invisible_display_settings)
            target_widget.blockSignals(True)
            target_widget.setPlainText(new_target_text)
            # Keep signals blocked – user edits will unblock naturally when
            # the widget is next focused and the handler fires from keystrokes.
            # We restore signals here so the widget stays interactive, but
            # the suppress flag guards against the queued event.
            target_widget.blockSignals(False)
            # Reset initial-load flag so the single queued textChanged event
            # that Qt delivers after blockSignals(False) is eaten harmlessly.
            target_widget._initial_load_complete = False


def apply_invisible_replacements(text: str,
                                 invisible_display_settings: Optional[Dict[str, bool]] = None) -> str:
    """Применяет подстановки невидимых символов для ОТОБРАЖЕНИЯ.

    Сигнатурный контракт (пункт Б промпта): один позиционный аргумент —
    target-текст, возвращается строка. Делегат главного окна сохраняет
    имя apply_invisible_replacements; на этот метод опираются
    modules/undo_manager.py (bound-колбэк при конструировании) и
    modules/pseudo_translate_dialog.py (hasattr-охраняемый вызов).

    Отсутствие настроек (атрибут invisible_display_settings ещё не создан)
    эквивалентно исходному hasattr-выходу: текст возвращается только с
    tag-защитой. The WORD JOINER it inserts is stripped again by
    reverse_invisible_replacements, so saved text is unaffected. Applies
    to both source and target display cells."""
    text = protect_tags_from_linebreak(text)

    if invisible_display_settings is None:
        return text

    result = text

    # Replace spaces with middle dot (·) followed by zero-width space for word-wrap capability
    # The zero-width space (U+200B) provides a line-break opportunity
    if invisible_display_settings.get('spaces', False):
        result = result.replace(' ', '·\u200B')

    # Replace tabs with right arrow (→) followed by zero-width space
    if invisible_display_settings.get('tabs', False):
        result = result.replace('\t', '→\u200B')

    # Non-breaking spaces are NO LONGER substituted (Camp B approach, as used by
    # VS Code/memoQ/Trados): the real U+00A0 / U+202F characters stay in the text and
    # their positions are shaded with a coloured background box by the TagHighlighter.
    # This avoids the old fragile '°' sentinel that collided with real degree signs.

    # Replace line breaks with return arrow (↵)
    if invisible_display_settings.get('linebreaks', False):
        result = result.replace('\n', '↵\n')
        result = result.replace('\r', '↵')

    return result


def reverse_invisible_replacements(text: str) -> str:
    """Обращает ВСЕ подстановки невидимых символов, получая исходный текст.

    ПРИМЕЧАНИЕ: мы всегда безусловно вырезаем ВСЕ типы маркеров,
    независимо от того, какие настройки включены сейчас. Это
    необходимо, потому что:
    - пользователь может выключить настройку после того, как маркеры
      уже помещены в виджет; маркеры всё равно должны быть убраны
      из сохраняемого текста;
    - обновление невидимых на месте вызывает setPlainText() с чистым
      текстом segment.target, но отложенное событие textChanged,
      сработавшее после, увидит только что установленный текст
      (который может содержать маркеры) и всё равно должен очистить
      его корректно.
    Функция не читает никакого состояния окна — настройки ей не нужны."""
    result = text

    # Strip the tag-protection WORD JOINER (U+2060) unconditionally. It is
    # display-only (inserted by protect_tags_from_linebreak) and must never
    # reach saved segment text, tag counts, TM, or exports.
    result = result.replace(WORD_JOINER, '')

    # Reverse spaces (middle dot + zero-width space → space) – always
    result = result.replace('·\u200B', ' ')
    result = result.replace('·', ' ')  # Fallback for any without zero-width space

    # Reverse tabs (right arrow + zero-width space → tab) – always
    result = result.replace('→\u200B', '\t')
    result = result.replace('→', '\t')  # Fallback

    # Reverse line breaks (return arrow → line break) – always
    result = result.replace('↵\n', '\n')
    result = result.replace('↵', '\r')
    # Legacy: pilcrow was used as line-break marker before v1.9.295
    result = result.replace('¶\n', '\n')
    result = result.replace('¶', '\r')

    # Always strip any stray zero-width spaces left over
    result = result.replace('\u200B', '')

    return result


def clear_all_filter_highlights(table):
    """Снимает жёлтые подсветки фильтра со всех ячеек без перезагрузки сетки."""
    for row in range(table.rowCount()):
        # Clear source column (2)
        clear_filter_highlights_in_widget(table, row, 2)

        # Clear target column (3)
        clear_filter_highlights_in_widget(table, row, 3)


def filter_empty_segments(current_project, table, source_widget,
                          target_widget, log_callback):
    """Быстрый фильтр, показывающий только сегменты с пустым переводом.

    ЖИВЫЙ КОД: 0 внешних call sites в callsites_before_batch6stage4.txt
    (единственное совпадение — собственный def); перенесён как есть по
    стандартной политике проекта («не удалять и не помечать dead-код при
    рефакторинге»). Мёртвые виджеты фильтров пропускаются через
    widget_is_alive (прямой импорт из helpers)."""
    # Clear filter boxes first
    if widget_is_alive(source_widget):
        source_widget.blockSignals(True)
        source_widget.clear()
        source_widget.blockSignals(False)
    if widget_is_alive(target_widget):
        target_widget.blockSignals(True)
        target_widget.clear()
        target_widget.blockSignals(False)

    # OPTIMIZED: Batch UI updates and don't reload grid
    table.setUpdatesEnabled(False)
    try:
        # Clear any yellow text filter highlights (but preserve termbase/tag formatting)
        clear_all_filter_highlights(table)

        # Hide rows with non-empty target (empty structural segments always hidden)
        visible_count = 0
        for row, segment in enumerate(current_project.segments):
            if row >= table.rowCount():
                break

            has_empty_target = not segment.target or not segment.target.strip()
            show_row = has_empty_target and segment.source.strip()
            table.setRowHidden(row, not show_row)

            if show_row:
                visible_count += 1
    finally:
        table.setUpdatesEnabled(True)

    log_callback(f"🔍 Empty segments filter: showing {visible_count} of {len(current_project.segments)} segments")


def apply_quick_filter(current_project, table, filter_type: str,
                       source_widget, target_widget,
                       set_active_text_filter_rows_callback,
                       set_filtering_active_callback,
                       apply_pagination_callback, log_callback):
    """Применяет быстрый фильтр по типу — интегрируется с системой пагинации.

    Записи self._active_text_filter_rows и self.filtering_active идут через
    set-колбэки в порядке исходного тела, затем повторно применяется
    пагинация через apply_pagination_callback (делегат передаёт
    self._apply_pagination_to_grid — сборку ~15 self-специфичных параметров
    не воссоздаём здесь, пункт Ж промпта)."""
    # Clear filter boxes first
    if widget_is_alive(source_widget):
        source_widget.blockSignals(True)
        source_widget.clear()
        source_widget.blockSignals(False)
    if widget_is_alive(target_widget):
        target_widget.blockSignals(True)
        target_widget.clear()
        target_widget.blockSignals(False)

    # Clear any yellow text filter highlights (but preserve termbase/tag formatting)
    clear_all_filter_highlights(table)

    # Calculate matching rows - collect into a set for pagination integration
    matching_rows = set()
    for row, segment in enumerate(current_project.segments):
        show_row = False

        if filter_type == "empty":
            show_row = not segment.target or not segment.target.strip()
        elif filter_type == "not_started":
            show_row = segment.status in ["not_started", "draft"]
        elif filter_type == "confirmed":
            show_row = segment.status == "confirmed"
        elif filter_type == "locked":
            show_row = getattr(segment, 'locked', False)
        elif filter_type == "not_locked":
            show_row = not getattr(segment, 'locked', False)
        elif filter_type == "commented":
            show_row = bool(segment.notes and segment.notes.strip())

        if show_row:
            matching_rows.add(row)

    # Integrate with pagination system - this ensures the filter persists
    # when other UI events trigger pagination updates
    set_active_text_filter_rows_callback(matching_rows)
    set_filtering_active_callback(True)

    # Apply the filter through the pagination system
    if apply_pagination_callback is not None:
        apply_pagination_callback()

    filter_names = {
        "empty": "Empty segments",
        "not_started": "Not started",
        "confirmed": "Confirmed",
        "locked": "Locked",
        "not_locked": "Not locked",
        "commented": "Commented"
    }
    log_callback(f"🔍 {filter_names.get(filter_type, 'Quick')} filter: showing {len(matching_rows)} of {len(current_project.segments)} segments")


def show_advanced_filters_dialog(current_project, parent,
                                 apply_advanced_filters_callback):
    """Показывает диалог расширенных фильтров с детальными опциями фильтрации.

    Диалог создаётся здесь напрямую (тот же принцип, что _ImportProgressDialog
    в pagination.py, Stage 3): модуль dialogs не импортирует modules.grid,
    цикла нет. Применение фильтров — через apply_advanced_filters_callback
    (делегат передаёт self.apply_advanced_filters)."""
    if not current_project:
        QMessageBox.information(parent, "No Project", "Please open or create a project first.")
        return

    dialog = AdvancedFiltersDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        filters = dialog.get_filters()
        apply_advanced_filters_callback(filters)


def apply_advanced_filters(current_project, table, filters: dict,
                           source_widget, target_widget, log_callback):
    """Применяет расширенные фильтры к сетке — оптимизировано по скорости.

    Мёртвые виджеты фильтров пропускаются через widget_is_alive (прямой
    импорт из helpers); подсветки снимаются прямым вызовом
    clear_all_filter_highlights из этого же модуля."""
    # Clear text filter boxes
    if widget_is_alive(source_widget):
        source_widget.blockSignals(True)
        source_widget.clear()
        source_widget.blockSignals(False)
    if widget_is_alive(target_widget):
        target_widget.blockSignals(True)
        target_widget.clear()
        target_widget.blockSignals(False)

    # OPTIMIZED: Batch UI updates and don't reload grid
    table.setUpdatesEnabled(False)
    try:
        # Clear any yellow text filter highlights (but preserve termbase/tag formatting)
        clear_all_filter_highlights(table)

        visible_count = 0
        for row, segment in enumerate(current_project.segments):
            if row >= table.rowCount():
                break

            show_row = True

            # Match rate filter
            if filters.get('match_rate_enabled'):
                match_percent = getattr(segment, 'match_percent', 0) or 0
                min_rate = filters.get('match_rate_min', 0)
                max_rate = filters.get('match_rate_max', 102)
                if not (min_rate <= match_percent <= max_rate):
                    show_row = False

            # Row status filters
            status_filters = filters.get('row_status', [])
            if status_filters:
                if segment.status not in status_filters:
                    show_row = False

            # Locked/unlocked filter
            if filters.get('locked_filter'):
                locked_value = getattr(segment, 'locked', False)
                if filters['locked_filter'] == 'locked' and not locked_value:
                    show_row = False
                elif filters['locked_filter'] == 'unlocked' and locked_value:
                    show_row = False

            # Other properties
            if filters.get('has_comments'):
                if not (segment.notes and segment.notes.strip()):
                    show_row = False

            if filters.get('has_proofreading'):
                if not getattr(segment, 'proofreading_notes', None):
                    show_row = False

            if filters.get('repetitions_only'):
                # TODO: Implement repetition detection
                pass

            # Empty structural segments are always hidden
            if not segment.source.strip():
                show_row = False

            table.setRowHidden(row, not show_row)

            if show_row:
                visible_count += 1
    finally:
        table.setUpdatesEnabled(True)

    log_callback(f"🔍 Advanced filters: showing {visible_count} of {len(current_project.segments)} segments")


def apply_sort(current_project, parent, sort_type: Optional[str],
               original_segment_order, set_original_segment_order_callback,
               set_current_sort_callback, page_size_combo,
               set_grid_page_size_callback, tr_callback, log_callback,
               reload_callback):
    """Сортирует сегменты по разным критериям (похоже на memoQ).

    Пункт А промпта: единственное пересечение состава Stage 4 с циклом
    SCC#1 — полная перезагрузка грида идёт через reload_callback (делегат
    передаёт self.load_segments_to_grid); сам load_segments_to_grid не
    тронут. self.tr — через tr_callback; переключение пагинации на «All» —
    через page_size_combo + set_grid_page_size_callback (запись
    grid_page_size=999999 внутри исходной combo-ветки: если combo
    отсутствует/мёртв, размер страницы НЕ перезаписывается — порядок
    сохранён); _original_segment_order — через
    set_original_segment_order_callback (hasattr-инициализация и
    обновление в ветке восстановления порядка)."""
    if not current_project.segments:
        return

    # Show progress dialog during sorting
    progress = QProgressDialog("Sorting segments, please wait...", None, 0, 0, parent)
    progress.setWindowTitle(tr_callback("Sorting"))
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)  # Show immediately
    progress.show()
    QApplication.processEvents()  # Force UI update

    try:
        # Store original document order if not already stored
        if original_segment_order is None:
            set_original_segment_order_callback(current_project.segments.copy())

        # Update current sort state
        set_current_sort_callback(sort_type)

        # If sort_type is None, restore document order
        if sort_type is None:
            # Restore document order by sorting by segment ID (original position)
            # This works even if the stored original order is wrong
            current_project.segments.sort(key=lambda seg: int(seg.id))

            # Update stored original order to this correct order
            set_original_segment_order_callback(current_project.segments.copy())

            # Set pagination to "All" to show all segments
            if page_size_combo is not None and widget_is_alive(page_size_combo):
                page_size_combo.blockSignals(True)
                page_size_combo.setCurrentText("All")
                page_size_combo.blockSignals(False)
                # Update the internal page size variable
                if set_grid_page_size_callback is not None:
                    set_grid_page_size_callback(999999)

            reload_callback()
            log_callback("↩️ Restored document order (showing all segments)")
            return

        # Helper function to get text without tags for more accurate sorting
        def strip_tags(text: str) -> str:
            """Удаляет HTML/XML-теги из текста для сортировки."""
            import re
            return re.sub(r'<[^>]+>', '', text).strip()

        # Calculate frequency maps if needed
        frequency_cache = {}
        if 'freq' in sort_type:
            from collections import Counter
            if 'source' in sort_type:
                counter = Counter(strip_tags(seg.source).lower() for seg in current_project.segments)
                frequency_cache = {strip_tags(seg.source).lower(): counter[strip_tags(seg.source).lower()]
                                 for seg in current_project.segments}
            else:  # target frequency
                counter = Counter(strip_tags(seg.target).lower() for seg in current_project.segments if seg.target)
                frequency_cache = {strip_tags(seg.target).lower(): counter[strip_tags(seg.target).lower()]
                                 for seg in current_project.segments if seg.target}

        # Sort based on selected criterion
        if sort_type == 'source_asc':
            current_project.segments.sort(key=lambda s: strip_tags(s.source).lower())
            sort_name = "Source A → Z"
        elif sort_type == 'source_desc':
            current_project.segments.sort(key=lambda s: strip_tags(s.source).lower(), reverse=True)
            sort_name = "Source Z → A"
        elif sort_type == 'target_asc':
            current_project.segments.sort(key=lambda s: strip_tags(s.target).lower() if s.target else "")
            sort_name = "Target A → Z"
        elif sort_type == 'target_desc':
            current_project.segments.sort(key=lambda s: strip_tags(s.target).lower() if s.target else "", reverse=True)
            sort_name = "Target Z → A"
        elif sort_type == 'source_length_asc':
            current_project.segments.sort(key=lambda s: len(strip_tags(s.source)))
            sort_name = "Source (shorter first)"
        elif sort_type == 'source_length_desc':
            current_project.segments.sort(key=lambda s: len(strip_tags(s.source)), reverse=True)
            sort_name = "Source (longer first)"
        elif sort_type == 'target_length_asc':
            current_project.segments.sort(key=lambda s: len(strip_tags(s.target)) if s.target else 0)
            sort_name = "Target (shorter first)"
        elif sort_type == 'target_length_desc':
            current_project.segments.sort(key=lambda s: len(strip_tags(s.target)) if s.target else 0, reverse=True)
            sort_name = "Target (longer first)"
        elif sort_type == 'match_asc':
            current_project.segments.sort(key=lambda s: getattr(s, 'match_percent', 0) or 0)
            sort_name = "Match Rate (lower first)"
        elif sort_type == 'match_desc':
            current_project.segments.sort(key=lambda s: getattr(s, 'match_percent', 0) or 0, reverse=True)
            sort_name = "Match Rate (higher first)"
        elif sort_type == 'source_freq_asc':
            current_project.segments.sort(key=lambda s: frequency_cache.get(strip_tags(s.source).lower(), 0))
            sort_name = "Source Frequency (lower first)"
        elif sort_type == 'source_freq_desc':
            current_project.segments.sort(key=lambda s: frequency_cache.get(strip_tags(s.source).lower(), 0), reverse=True)
            sort_name = "Source Frequency (higher first)"
        elif sort_type == 'target_freq_asc':
            current_project.segments.sort(key=lambda s: frequency_cache.get(strip_tags(s.target).lower(), 0) if s.target else 0)
            sort_name = "Target Frequency (lower first)"
        elif sort_type == 'target_freq_desc':
            current_project.segments.sort(key=lambda s: frequency_cache.get(strip_tags(s.target).lower(), 0) if s.target else 0, reverse=True)
            sort_name = "Target Frequency (higher first)"
        elif sort_type == 'modified_asc':
            current_project.segments.sort(key=lambda s: s.modified_at if s.modified_at else "")
            sort_name = "Last Changed (oldest first)"
        elif sort_type == 'modified_desc':
            current_project.segments.sort(key=lambda s: s.modified_at if s.modified_at else "", reverse=True)
            sort_name = "Last Changed (newest first)"
        elif sort_type == 'status':
            # Sort by status in a logical order: not_started, draft, confirmed
            status_order = {'not_started': 0, 'draft': 1, 'confirmed': 2, 'approved': 3}
            current_project.segments.sort(key=lambda s: status_order.get(s.status, 99))
            sort_name = "Row Status"
        else:
            log_callback(f"⚠️ Unknown sort type: {sort_type}")
            return

        # Set pagination to "All" to show all sorted segments
        if page_size_combo is not None and widget_is_alive(page_size_combo):
            page_size_combo.blockSignals(True)
            page_size_combo.setCurrentText("All")
            page_size_combo.blockSignals(False)
            # Update the internal page size variable
            if set_grid_page_size_callback is not None:
                set_grid_page_size_callback(999999)

        # Reload grid to reflect new order
        reload_callback()
        log_callback(f"⇅ Sorted by: {sort_name} (showing all segments)")

    except Exception as e:
        log_callback(f"❌ Error sorting segments: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close progress dialog
        progress.close()


def filter_on_selected_text(table, source_filter_text: str,
                            target_filter_text: str, source_widget,
                            target_widget, clear_filters_callback,
                            apply_filters_callback,
                            reverse_replacements_callback, editor_classes,
                            log_callback):
    """Фильтрует по выделенному сейчас тексту в колонке источника или
    перевода.

    Переключающее поведение: если фильтры уже активны, Ctrl+Shift+F
    их очистит. Иначе — фильтрация по выбранному тексту.

    Классы текстовых редакторов монолита (EditableGridTextEditor,
    ReadOnlyGridTextEditor) передаются параметром editor_classes —
    прямой импорт дал бы циклический импорт. Обращение подстановок
    невидимых символов — через reverse_replacements_callback (делегат
    передаёт self.reverse_invisible_replacements; исходная
    hasattr-проверка эквивалентна None-проверке). Применение/снятие
    фильтров — через apply_filters_callback / clear_filters_callback
    (тяжёлый self-контекст не воссоздаётся)."""
    # Сначала проверяем, активны ли фильтры сейчас (для поведения переключателя)
    filters_active = bool(source_filter_text or target_filter_text)

    # Переключение: если фильтры активны, очищаем их и выходим
    if filters_active:
        clear_filters_callback()
        log_callback(f"🔍 Filters cleared ({format_shortcut_for_display('Ctrl+Shift+F')} toggle)")
        return

    # Фильтры не активны — пытаемся фильтровать по выделенному тексту
    focused_widget = QApplication.focusWidget()

    selected_text = ""
    is_source = False
    is_target = False

    # Проверяем, что это текстовый редактор (источник или перевод)
    if focused_widget and isinstance(focused_widget, editor_classes):
        cursor = focused_widget.textCursor()
        selected_text = cursor.selectedText().strip()

        # Определяем, источник это или перевод, по столбцу
        if table:
            for row in range(table.rowCount()):
                # Проверяем столбец источника (индекс 2)
                source_cell_widget = table.cellWidget(row, 2)
                if source_cell_widget == focused_widget:
                    is_source = True
                    break
                # Проверяем столбец перевода (индекс 3)
                target_cell_widget = table.cellWidget(row, 3)
                if target_cell_widget == focused_widget:
                    is_target = True
                    break

    # Снимаем маркеры невидимых символов, чтобы фильтр сравнивал чистый текст сегмента
    if selected_text and reverse_replacements_callback is not None:
        selected_text = reverse_replacements_callback(selected_text)
        selected_text = selected_text.strip()

    if not selected_text:
        log_callback("⚠️ No text selected. Select text in source or target column first.")
        return

    # Вставляем выделенный текст в нужное поле фильтра и применяем фильтр
    if is_source and source_widget:
        source_widget.setText(selected_text)
        apply_filters_callback()
        log_callback(f"🔍 Filtering source on: '{selected_text}'")
    elif is_target and target_widget:
        target_widget.setText(selected_text)
        apply_filters_callback()
        log_callback(f"🔍 Filtering target on: '{selected_text}'")


def ensure_shared_filter(existing_widget, placeholder: str,
                         on_change=None, on_return=None) -> Tuple[object, bool]:
    """Создаёт (или возвращает существующий) общий виджет фильтра, который
    может быть уничтожен при смене компоновки.

    Разрешение атрибута ПО ИМЕНИ (getattr/setattr) — self-специфичная логика
    и остаётся в делегате (тот же принцип, что _get_line_edit_text в
    Stage 2, пункт Г промпта Stage 2): функция получает уже разрешённый
    виджет и возвращает (widget, created) — делегат записывает атрибут
    только если виджет был СОЗДАН заново (как в исходном теле).
    Живость — через helpers.widget_is_alive (прямой импорт)."""
    created = False
    widget = existing_widget
    if not widget_is_alive(widget):
        widget = QLineEdit()
        if on_change is not None:
            widget.textChanged.connect(on_change)
        if on_return is not None:
            widget.returnPressed.connect(on_return)
        created = True
    widget.setPlaceholderText(placeholder)
    return widget, created


def ensure_primary_filters_ready(ensure_shared_filter_callback,
                                 apply_filters_callback) -> Tuple[object, object]:
    """Гарантирует существование фильтров сетки перед программным
    использованием. Возвращает (source_filter, target_filter) — делегат
    записывает оба self-атрибута."""
    source = ensure_shared_filter_callback(
        'source_filter',
        "Type to filter source segments...",
        on_change=apply_filters_callback,
        on_return=apply_filters_callback,
    )
    target = ensure_shared_filter_callback(
        'target_filter',
        "Type to filter target segments...",
        on_change=apply_filters_callback,
        on_return=apply_filters_callback,
    )
    return source, target
