"""Пагинация грида, извлечённая из Supervertaler.SupervertalerQt
(Batch #6 Stage 3, Step 6 of EXTRACTION_PLAN.md).

Архитектура — та же, что в helpers.py (Stage 2, решение владельца Stage 1 §6):
МОДУЛЬ ЧИСТЫХ ФУНКЦИЙ — без класса и без ссылок на главное окно. Каждая функция
получает нужный контекст явными параметрами и именованными колбэками для
зависимостей, которые пока остаются в монолите (log, _populate_single_row,
_start_background_populate).

SupervertalerQt сохраняет 14 тонких одноимённых делегатов (DYNAMIC_ENTRY_POINT:
go_to_prev_page / go_to_next_page / on_page_size_changed — SIGNAL_SLOT /
EXTERNAL_ATTR_REF, select_range_page_up / select_range_page_down — ARG_REF),
поэтому все call sites продолжают работать без изменений.

Константы PAGE_AUTO_ALL_THRESHOLD / PAGE_FALLBACK_SIZE перенесены сюда как
module-level (в монолите были class-level константами SupervertalerQt,
использовались только внутри _maybe_auto_set_page_size — выверено grep'ом,
Stage 3 промпт + Этап 0.4).

Слой helpers: там, где зависимость уже есть в modules/grid/helpers.py
(Stage 2), она импортируется напрямую — resize_visible_rows (вместо колбэка на
self._resize_visible_rows) и widget_is_alive (вместо колбэка на делегата
self._widget_is_alive; сам делегат в монолите сохранён и по-прежнему вызывает
helpers.widget_is_alive).
"""

from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetSelectionRange

from modules.dialogs import _ImportProgressDialog

from modules.grid.helpers import resize_visible_rows, widget_is_alive

# Порог автопереключения «All» → постраничный режим при открытии проекта.
PAGE_AUTO_ALL_THRESHOLD = 1000
# Размер страницы, на который откатывается автопереключатель для больших
# документов (> PAGE_AUTO_ALL_THRESHOLD сегментов).
PAGE_FALLBACK_SIZE = 200

# Сентинел «All»-режима (исторически 999999; параметр pure-функций для
# отладки/тестов, в делегатах всегда передаётся 999999).
PAGE_ALL_SENTINEL = 999999

__all__ = [
    "maybe_auto_set_page_size",
    "get_total_pages",
    "update_pagination_ui",
    "apply_pagination_to_grid",
    "go_to_first_page",
    "go_to_prev_page",
    "go_to_next_page",
    "select_range_page_up",
    "select_range_page_down",
    "select_range_between",
    "clear_selection_anchor",
    "go_to_last_page",
    "go_to_page",
    "on_page_size_changed",
    "PAGE_AUTO_ALL_THRESHOLD",
    "PAGE_FALLBACK_SIZE",
]


def maybe_auto_set_page_size(
    current_project,
    page_size_decided_for=None,
    page_size_combo=None,
    log_callback=None,
    threshold=PAGE_AUTO_ALL_THRESHOLD,
    fallback_size=PAGE_FALLBACK_SIZE,
    all_sentinel=PAGE_ALL_SENTINEL,
) -> Optional[int]:
    """Выбирает размер страницы сетки один раз для каждого заново открытого
    проекта.

    По умолчанию — «All» (показывать все сегменты); для очень больших
    документов (> threshold сегментов) откатывается к fallback_size на
    страницу. Выполняется один раз на объект проекта — с ключом по
    идентификатору проекта, — поэтому перерисовки (сортировка, фильтр, смена
    страницы) и любой сделанный пользователем в этой сессии ручной выбор
    «Per page» не перезаписываются.

    Возвращает None, если менять размер страницы не нужно (нет проекта /
    решение уже принято), иначе — новый размер страницы. Делегат записывает
    результат в self.grid_page_size, сбрасывает self.grid_current_page в 0,
    обновляет self._page_size_decided_for и отражает решение в комбобоксе
    (пункты Б/В промпта: self-специфичные getattr/setattr-обёртки — в
    делегате).
    """
    if not current_project or not current_project.segments:
        return None
    key = id(current_project)
    if page_size_decided_for == key:
        return None

    total = len(current_project.segments)
    if total > threshold:
        new_page_size = fallback_size
        if log_callback is not None:
            log_callback(
                f"📄 Large project ({total} segments) — paginating at "
                f"{fallback_size}/page. Switch to 'All' via the "
                f"Per-page selector if you prefer one page.")
    else:
        new_page_size = all_sentinel  # All

    # Reflect the decision in the combo without retriggering the handler.
    if page_size_combo is not None and widget_is_alive(page_size_combo):
        page_size_combo.blockSignals(True)
        page_size_combo.setCurrentText(
            "All" if new_page_size >= all_sentinel
            else str(new_page_size))
        page_size_combo.blockSignals(False)
    return new_page_size


def get_total_pages(current_project, grid_page_size=50,
                    all_sentinel=PAGE_ALL_SENTINEL) -> int:
    """Вычисляет общее число страниц по количеству сегментов и размеру страницы."""
    if not current_project or not current_project.segments:
        return 1
    total_segments = len(current_project.segments)
    if not isinstance(grid_page_size, int) or grid_page_size >= all_sentinel:
        return 1  # "All" selected
    return max(1, (total_segments + grid_page_size - 1) // grid_page_size)


def update_pagination_ui(
    current_project,
    pagination_label=None,
    total_pages_label=None,
    page_number_input=None,
    first_page_btn=None,
    prev_page_btn=None,
    next_page_btn=None,
    last_page_btn=None,
    grid_current_page=0,
    grid_page_size=50,
    filter_allowlist=None,
    tr_callback=None,
    widget_is_alive_callback=None,
    all_sentinel=PAGE_ALL_SENTINEL,
) -> int:
    """Обновляет подписи пагинации и состояния кнопок.

    Чистое ядро расчётов (total_pages через get_total_pages, clamp текущей
    страницы, диапазон start/end) выполняется без обращения к виджетам; вся
    работа с виджетами — через Optional-параметры. Зависимости-монолит:
    self.tr (колбэком tr_callback, пункт Г промпта — вариант (i); для
    f-строк-меток колбэк не нужен) и живость виджетов (колбэком
    widget_is_alive_callback — делегат передаёт helpers.widget_is_alive).
    Возвращает clamped grid_current_page — делегат записывает его в
    self.grid_current_page (эквивалент исходной hasattr-починки: атрибут
    создаётся в любом случае, значение тоже).
    """
    if not current_project or not current_project.segments:
        if pagination_label is not None and widget_is_alive_callback(pagination_label):
            pagination_label.setText(tr_callback("Segments 0-0 of 0"))
        if total_pages_label is not None and widget_is_alive_callback(total_pages_label):
            total_pages_label.setText(tr_callback("of 1"))
        if page_number_input is not None and widget_is_alive_callback(page_number_input):
            page_number_input.setText("1")
        return 0

    total_segments = len(current_project.segments)
    total_pages = get_total_pages(current_project, grid_page_size,
                                  all_sentinel=all_sentinel)

    # Clamp current page to valid range
    grid_current_page = max(0, min(grid_current_page, total_pages - 1))

    # Check if a filter is active (text filter or quick filter)
    is_filtered = filter_allowlist is not None

    # Calculate segment range for current page
    if grid_page_size >= all_sentinel:
        # "All" mode - show all segments
        start_seg = 1
        end_seg = total_segments
    else:
        start_seg = grid_current_page * grid_page_size + 1
        end_seg = min((grid_current_page + 1) * grid_page_size, total_segments)

    # Update pagination label - show filtered count when filter is active
    if pagination_label is not None and widget_is_alive_callback(pagination_label):
        if is_filtered:
            filtered_count = len(filter_allowlist)
            pagination_label.setText(
                f"Showing {filtered_count} of {total_segments} segments")
        else:
            pagination_label.setText(
                f"Segments {start_seg}-{end_seg} of {total_segments}")

    if total_pages_label is not None and widget_is_alive_callback(total_pages_label):
        total_pages_label.setText(f"of {total_pages}")

    if page_number_input is not None and widget_is_alive_callback(page_number_input):
        page_number_input.setText(str(grid_current_page + 1))

    # Enable/disable navigation buttons
    is_first_page = grid_current_page == 0
    is_last_page = grid_current_page >= total_pages - 1

    if first_page_btn is not None and widget_is_alive_callback(first_page_btn):
        first_page_btn.setEnabled(not is_first_page)
    if prev_page_btn is not None and widget_is_alive_callback(prev_page_btn):
        prev_page_btn.setEnabled(not is_first_page)
    if next_page_btn is not None and widget_is_alive_callback(next_page_btn):
        next_page_btn.setEnabled(not is_last_page)
    if last_page_btn is not None and widget_is_alive_callback(last_page_btn):
        last_page_btn.setEnabled(not is_last_page)
    return grid_current_page


def apply_pagination_to_grid(
    current_project,
    table,
    parent,
    grid_current_page,
    grid_page_size,
    active_text_filter_rows,
    populated_rows,
    suppress_target_change_handlers,
    set_suppress_target_change_handlers,
    populate_single_row_callback,
    auto_resize_callback,
    deferred_resize_callback,
    update_pagination_ui_callback,
    start_background_populate_callback,
    import_progress_dialog=_ImportProgressDialog,
    all_sentinel=PAGE_ALL_SENTINEL,
) -> None:
    """Показывает/скрывает строки по текущей странице, опционально
    ограниченной активными фильтрами.

    ВАЖНО: при активном текстовом фильтре (поля Filter Source/Target)
    показываются ВСЕ совпадающие строки по всему документу, без учёта
    пагинации. Это гарантирует, что пользователь найдёт контент независимо от
    того, на какой странице он находится.

    Когда фильтр не активен, применяется обычная пагинация.

    Self-специфичные hasattr-дефолты (grid_current_page → 0, grid_page_size →
    50) выполняет делегат ДО вызова (пункт Б промпта: setattr-логика — в
    делегате), поэтому функция получает уже разрешённые int-значения.
    suppress_target_change_handlers — текущее значение флага подавления
    обработчиков цели (читается делегатом через getattr(..., False)),
    set_suppress_target_change_handlers — колбэк записи (setattr), используются
    вложенным _do_populate в порядке исходного тела (True перед циклом,
    восстановление старого значения в finally). deferred_resize_callback —
    bound-метод self._resize_visible_rows: отложенный одиночный выстрел
    Qt-таймера должен резолвить таблицу В МОМЕНТ СРАБАТЫВАНИЯ (таблица может
    быть пересоздана), поэтому отложенный вызов идёт через делегата, а
    синхронный — напрямую через импортированный helpers.resize_visible_rows
    (пункт Д).
    """
    if not current_project or not current_project.segments:
        return

    total_segments = len(current_project.segments)

    # If a text filter (Filter Source/Target) is active, it will populate an allowlist
    # of row indices that are allowed to be visible.
    filter_allowlist = active_text_filter_rows

    # Build set of empty structural segments (always hidden regardless of pagination/filter)
    segments = current_project.segments
    empty_rows = {i for i in range(total_segments) if not segments[i].source.strip()}

    # Compute the set of rows that will be visible. We do this first (rather
    # than iterating + flipping setRowHidden) so the lazy-populate pass
    # below knows exactly which rows it needs to install widgets for.
    if filter_allowlist is not None:
        # Filter mode: show all matching rows across the entire document.
        rows_to_show = {r for r in filter_allowlist if r not in empty_rows}
    else:
        # Normal pagination mode.
        if grid_page_size >= all_sentinel:
            # "All" mode - show everything.
            start_row = 0
            end_row = total_segments
        else:
            start_row = grid_current_page * grid_page_size
            end_row = min(start_row + grid_page_size, total_segments)
        rows_to_show = {r for r in range(start_row, end_row) if r not in empty_rows}

    # v1.10.147 (page-aware grid loading – based on Hans Lenting's
    # Simpelvertaler fork): rows that haven't yet had their full editor
    # widgets installed get them now, just-in-time, so the user only ever
    # pays the widget-construction cost for rows that are about to be
    # visible. Untouched rows continue to use their cheap placeholder.
    #
    # v1.10.151: when a single pagination change brings a large number
    # of un-populated rows into view at once (typically switching from
    # 100/200/page to "All" on a multi-thousand-segment project), wrap
    # the populate loop in the shared _ImportProgressDialog so the user
    # sees activity instead of a "Not Responding" freeze. Threshold
    # chosen so small page flips stay invisible.
    populated = populated_rows
    if populated is not None:
        seg_count = len(segments)
        rows_to_populate = [r for r in rows_to_show
                            if r not in populated and r < seg_count]

        def _do_populate(progress_callback=None):
            set_suppress_target_change_handlers(True)
            try:
                for i, row in enumerate(rows_to_populate):
                    populate_single_row_callback(row, segments[row])
                    # The newly-installed target editor inherits the
                    # suppression flag we just set; unblock its signals
                    # so user edits will reach the change handler.
                    w = table.cellWidget(row, 3)
                    if w:
                        w.blockSignals(False)
                    # Every ~25 rows, give the progress dialog a chance
                    # to repaint and the event loop a chance to keep the
                    # OS from marking the window unresponsive.
                    if progress_callback is not None and i % 25 == 0:
                        progress_callback(i, len(rows_to_populate))
            finally:
                set_suppress_target_change_handlers(
                    suppress_target_change_handlers)

        if len(rows_to_populate) >= 200:
            # Substantial batch — show a progress dialog. 200 was chosen
            # because that's where the per-row widget-construction cost
            # starts being perceptible (~5 s on a typical SDLXLIFF).
            with import_progress_dialog(
                parent,
                title="Loading more segments",
                initial_label=(
                    f"Loading {len(rows_to_populate):,} additional "
                    "segments into grid…"
                ),
                initial_total=len(rows_to_populate),
            ) as _prog:
                _do_populate(progress_callback=_prog.grid_callback)
        elif rows_to_populate:
            # Small batch — populate inline, no dialog flash.
            _do_populate()

    # Now hide/show in a single batched pass.
    table.setUpdatesEnabled(False)
    try:
        for row in range(total_segments):
            table.setRowHidden(row, row not in rows_to_show)
    finally:
        table.setUpdatesEnabled(True)

    # Recalculate heights for visible rows to prevent layout corruption.
    # Call synchronously first, then schedule a deferred resize to catch any
    # layout issues that Qt processes asynchronously.
    resize_visible_rows(table, auto_resize_callback)
    QTimer.singleShot(50, deferred_resize_callback)

    # Update pagination UI
    update_pagination_ui_callback()

    # v1.10.152: kick off background prefetch of the NEXT page in idle
    # time so the next "Next page" click (or Ctrl+Enter on the last
    # segment of this page) is instantaneous instead of triggering a
    # 200-row populate-and-progress-dialog cycle.
    start_background_populate_callback()


def go_to_first_page(grid_current_page) -> Optional[int]:
    """Переход на первую страницу.

    Возвращает 0, если нужен переход (делегат записывает grid_current_page и
    применяет пагинацию), иначе None — состояние окна не меняется.
    hasattr-дефолт grid_current_page → 0 остаётся в делегате (пункт Б).
    """
    if grid_current_page != 0:
        return 0
    return None


def go_to_prev_page(current_project, grid_current_page,
                    grid_page_size) -> Optional[int]:
    """Переход на предыдущую страницу.

    Возвращает новый номер страницы или None, если перехода нет. total_pages
    считается через get_total_pages этого же модуля (вместо колбэка на
    self._get_total_pages — слои pagination→pagination).
    """
    total_pages = get_total_pages(current_project, grid_page_size)
    if grid_current_page > 0:
        return grid_current_page - 1
    return None


def go_to_next_page(current_project, grid_current_page,
                    grid_page_size) -> Optional[int]:
    """Переход на следующую страницу. См. go_to_prev_page."""
    total_pages = get_total_pages(current_project, grid_page_size)
    if grid_current_page < total_pages - 1:
        return grid_current_page + 1
    return None


def go_to_last_page(current_project, grid_current_page,
                    grid_page_size) -> Optional[int]:
    """Переход на последнюю страницу. См. go_to_prev_page."""
    total_pages = get_total_pages(current_project, grid_page_size)
    if grid_current_page != total_pages - 1:
        return total_pages - 1
    return None


def select_range_page_up(current_project, table, grid_page_size,
                         selection_anchor) -> Optional[int]:
    """Выделяет диапазон сегментов вверх (Shift+Page Up).

    Расширяет выделение от текущей строки вверх на одну страницу сегментов.
    Если якорь выделения отсутствует (selection_anchor is None), отсчёт идёт
    от текущей строки.

    Возвращает значение якоря, которое делегат записывает в
    self._selection_anchor_row через setattr (пункт Б промпта: self-специфичный
    hasattr/setattr — в делегате), или None при выходе по guard'у (якорь не
    трогается). Внутренний вызов _select_range_between заменён прямым вызовом
    select_range_between этого же модуля.
    """
    if not table or not current_project:
        return None

    current_row = table.currentRow()
    if current_row < 0:
        return None

    # Calculate page size (number of segments to select). When "All" is
    # active (sentinel 999999) fall back to a screenful so Shift+PgUp
    # doesn't select to the top of the document.
    page_size = grid_page_size
    if not isinstance(page_size, int) or page_size >= 999999 or page_size <= 0:
        page_size = 50

    # Get or set the selection anchor (starting point for range selection)
    if selection_anchor is None:
        selection_anchor = current_row

    # Calculate target row (one page up from current, but not below 0)
    target_row = max(0, current_row - page_size)

    # Select range from anchor to target
    select_range_between(table, selection_anchor, target_row)

    # Move focus to the target row
    table.setCurrentCell(target_row, 3)  # Column 3 is target cell
    table.scrollToItem(table.item(target_row, 0))
    return selection_anchor


def select_range_page_down(current_project, table, grid_page_size,
                           selection_anchor) -> Optional[int]:
    """Выделяет диапазон сегментов вниз (Shift+Page Down). См.
    select_range_page_up."""
    if not table or not current_project:
        return None

    current_row = table.currentRow()
    if current_row < 0:
        return None

    # Calculate page size (number of segments to select). When "All" is
    # active (sentinel 999999) fall back to a screenful so Shift+PgDn
    # doesn't select to the bottom of the document.
    page_size = grid_page_size
    if not isinstance(page_size, int) or page_size >= 999999 or page_size <= 0:
        page_size = 50

    # Get or set the selection anchor (starting point for range selection)
    if selection_anchor is None:
        selection_anchor = current_row

    # Calculate target row (one page down from current, but not beyond last segment)
    max_row = len(current_project.segments) - 1
    target_row = min(max_row, current_row + page_size)

    # Select range from anchor to target
    select_range_between(table, selection_anchor, target_row)

    # Move focus to the target row
    table.setCurrentCell(target_row, 3)  # Column 3 is target cell
    table.scrollToItem(table.item(target_row, 0))
    return selection_anchor


def select_range_between(table, start_row: int, end_row: int) -> None:
    """Выделяет все строки между start_row и end_row (включительно).

    Аргументы:
        start_row: строка-якорь выделения
        end_row: целевая строка, до которой расширяется выделение
    """
    if not table:
        return

    # Determine actual start and end (handle both directions)
    min_row = min(start_row, end_row)
    max_row = max(start_row, end_row)

    # Clear existing selection
    table.clearSelection()

    # Select the range using QTableWidgetSelectionRange
    col_count = table.columnCount()
    selection_range = QTableWidgetSelectionRange(min_row, 0, max_row, col_count - 1)
    table.setRangeSelected(selection_range, True)


def clear_selection_anchor(selection_anchor) -> bool:
    """Сбрасывает якорь выделения при щелчке без Shift.

    МЁРТВЫЙ КОД (пункт А промпта Stage 3, DEAD_CODE_REPORT.md): единственная
    текстуальная ссылка в 125 файлах — собственный def, 0 call sites
    (подтверждено callsites_before_batch6stage3.txt); перенесён как есть по
    стандартной политике проекта («не удалять и не помечать dead-код при
    рефакторинге», решение владельца). Удаление атрибута (del) —
    self-специфично и остаётся в делегате: функция возвращает True, если якорь
    существует и атрибут _selection_anchor_row нужно удалить (пункт Б).
    """
    return selection_anchor is not None


def go_to_page(current_project, grid_page_size, grid_current_page,
               page_number_input) -> Optional[int]:
    """Переход на указанную страницу из поля ввода.

    Возвращает новый номер страницы (0-индексированный), если делегат должен
    записать self.grid_current_page и применить пагинацию; None — если
    страница не изменилась (текст поля ввода обновлён здесь), ввод нечисловой
    или виджет недоступен. Живость виджета — через helpers.widget_is_alive
    (импорт напрямую, пункт Д; делегат self._widget_is_alive в монолите
    сохранён и зовёт ту же функцию).
    """
    if page_number_input is None or not widget_is_alive(page_number_input):
        return None
    try:
        page_num = int(page_number_input.text())
        total_pages = get_total_pages(current_project, grid_page_size)
        if grid_current_page is None:
            grid_current_page = 0
        new_page = max(0, min(page_num - 1, total_pages - 1))  # Convert to 0-indexed and clamp
        if new_page != grid_current_page:
            return new_page
        else:
            # Even if same page, update the input to show clamped value
            page_number_input.setText(str(grid_current_page + 1))
    except ValueError:
        # Invalid input, reset to current page
        if grid_current_page is not None:
            page_number_input.setText(str(grid_current_page + 1))
    return None


def on_page_size_changed(text: str,
                         all_sentinel: int = PAGE_ALL_SENTINEL) -> tuple:
    """Обрабатывает изменение размера страницы.

    Возвращает (grid_page_size, grid_current_page): новый размер страницы
    ("All" → sentinel 999999; нечисловой текст → 50) и сброс на первую
    страницу. Делегат записывает оба значения на окно и применяет пагинацию.
    Исходные self-специфичные hasattr-дефолты не переносятся: значение
    grid_page_size перезаписывается безусловно (в т.ч. ветка ValueError → 50),
    а grid_current_page в обеих ветках оригинала получает 0; read-only
    локальная переменная old_page_size была мёртвой (ни разу не читалась) и
    опущена — задокументировано в отчёте.
    """
    if text == "All":
        page_size = all_sentinel
    else:
        try:
            page_size = int(text)
        except ValueError:
            page_size = 50

    # Reset to first page when page size changes
    current_page = 0

    return page_size, current_page
