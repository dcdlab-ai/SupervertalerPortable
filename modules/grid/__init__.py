# modules.grid — grid-слой, извлекаемый из Supervertaler.py (Step 6 EXTRACTION_PLAN.md).
# Stage 2 (Batch #6): helpers.py — модуль ЧИСТЫХ ФУНКЦИЙ (решение владельца,
# Stage 1 §6): явные параметры, без класса и без ссылок на главное окно.
# Stage 3/4 добавят сюда pagination.py и filters.py.

from . import helpers
from .helpers import (
    widget_is_alive,
    segment_for_grid_row,
    recompute_list_numbers,
    reindex_grid_rows_from,
    find_row_for_segment,
    find_row_for_segment_id,
    select_grid_row_by_id,
    compute_initial_visible_rows,
    navigate_to_segment_in_grid,
    navigate_to_segment_by_id,
    get_selected_segments_from_grid,
    get_selected_or_filtered_segments,
    resize_visible_rows,
    move_to_next_visible_row,
    is_text_filter_active,
    get_filtered_segments_with_rows,
)

# Stage 3 (Batch #6): pagination.py — модуль чистых функций пагинации
# (тот же принцип, что и helpers.py; делегаты сохранены в SupervertalerQt).
from . import pagination
from .pagination import (
    maybe_auto_set_page_size,
    get_total_pages,
    update_pagination_ui,
    apply_pagination_to_grid,
    go_to_first_page,
    go_to_prev_page,
    go_to_next_page,
    select_range_page_up,
    select_range_page_down,
    select_range_between,
    clear_selection_anchor,
    go_to_last_page,
    go_to_page,
    on_page_size_changed,
    PAGE_AUTO_ALL_THRESHOLD,
    PAGE_FALLBACK_SIZE,
)

__all__ = [
    "helpers",
    "pagination",
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
