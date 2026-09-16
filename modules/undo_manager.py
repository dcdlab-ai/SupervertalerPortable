"""
Undo/redo manager for grid edits (Batch #5 Stage 2, Step 5 of EXTRACTION_PLAN.md).

Extracted verbatim from Supervertaler.SupervertalerQt (ex-window blocks 9373-9515,
9731-9746 and 9888-9944 @ HEAD c11e1bc). Owns the undo_stack / redo_stack /
max_undo_levels state that previously lived on SupervertalerQt.__init__ (former
lines 6212-6214) and receives every other dependency through explicit named
callbacks passed to __init__ — no reference to the main window is kept.

SupervertalerQt keeps 8 thin same-named delegates, so all 43 call sites
(28 self-style from monolith methods, 11 MOVE→MOVE, 4 external duck-typed)
continue to work unchanged.
"""

from typing import Any, Callable, Optional


class UndoManager:
    """Хранит undo/redo-состояние сетки и применяет отмену/повтор.

    Зависимости от главного окна передаются только именованными колбэками
    (решение владельца, Batch #5 Stage 1 §1.9 / В1 — не через ссылку на окно):

    Геттеры (атрибут окна меняется или создаётся лениво/позже менеджера):
      get_current_project     -> Optional[Project]   (18 мест присваивания в окне)
      get_table               -> QTableWidget        (пересоздаётся create_translation_grid)
      get_current_sort        -> Any                 (ленивый; getattr(self, 'current_sort', None))
      get_undo_action         -> QAction             (создаются в create_menus ПОСЛЕ __init__)
      get_redo_action         -> QAction
    Сеттер / действия:
      set_original_segment_order(order)               (в 8 методах только запись)
      mark_project_modified()                         (все 3 использования — `= True`)
    Статические callable-ссылки (имена совпадают с методами окна, тела не менялись):
      _find_row_for_segment, _update_status_cell, _select_grid_row_by_id,
      _split_segment_grid_fast, _merge_segment_grid_fast, update_window_title,
      update_progress_stats, apply_invisible_replacements, load_segments_to_grid,
      refresh_preview, log.
    """

    def __init__(self, *,
                 get_current_project: Callable[[], Optional[Any]],
                 get_table: Callable[[], Any],
                 get_current_sort: Callable[[], Any],
                 get_undo_action: Callable[[], Any],
                 get_redo_action: Callable[[], Any],
                 set_original_segment_order: Callable[[list], None],
                 mark_project_modified: Callable[[], None],
                 _find_row_for_segment: Callable[[int], int],
                 _update_status_cell: Callable[[int, Any], None],
                 _select_grid_row_by_id: Callable[[int], None],
                 _split_segment_grid_fast: Callable[..., None],
                 _merge_segment_grid_fast: Callable[..., None],
                 update_window_title: Callable[[], None],
                 update_progress_stats: Optional[Callable[[], None]],
                 apply_invisible_replacements: Optional[Callable[[str], str]],
                 load_segments_to_grid: Callable[..., None],
                 refresh_preview: Callable[[], None],
                 log: Callable[[str], None],
                 max_undo_levels: int = 100):
        # Undo/Redo state for grid edits (moved from SupervertalerQt.__init__)
        self.undo_stack = []  # List of (segment_id, old_target, new_target, old_status, new_status)
        self.redo_stack = []  # List of undone actions that can be redone
        self.max_undo_levels = max_undo_levels  # Maximum number of undo levels to keep

        # Callbacks (see class docstring)
        self.get_current_project = get_current_project
        self.get_table = get_table
        self.get_current_sort = get_current_sort
        self.get_undo_action = get_undo_action
        self.get_redo_action = get_redo_action
        self.set_original_segment_order = set_original_segment_order
        self.mark_project_modified = mark_project_modified
        self._find_row_for_segment = _find_row_for_segment
        self._update_status_cell = _update_status_cell
        self._select_grid_row_by_id = _select_grid_row_by_id
        self._split_segment_grid_fast = _split_segment_grid_fast
        self._merge_segment_grid_fast = _merge_segment_grid_fast
        self.update_window_title = update_window_title
        self.update_progress_stats = update_progress_stats
        self.apply_invisible_replacements = apply_invisible_replacements
        self.load_segments_to_grid = load_segments_to_grid
        self.refresh_preview = refresh_preview
        self.log = log

    def record_undo_state(self, segment_id, old_target, new_target, old_status, new_status):
        """Записать состояние отмены при редактировании ячеек сетки.
        
        Для массовых операций (Copy Source to Target, AI batch, TM auto-fill,
        пред-перевод и т.п.) предпочтительна ``record_undo_states_batch`` — она делает
        один проход UI/обрезки в конце вместо одного на сегмент."""
        # Don't record if nothing actually changed
        if old_target == new_target and old_status == new_status:
            return

        # Add to undo stack
        undo_entry = {
            "segment_id": segment_id,
            "old_target": old_target,
            "new_target": new_target,
            "old_status": old_status,
            "new_status": new_status
        }
        self.undo_stack.append(undo_entry)

        # Trim undo stack to max levels
        if len(self.undo_stack) > self.max_undo_levels:
            self.undo_stack.pop(0)

        # Clear redo stack (can't redo after new edit)
        self.redo_stack.clear()

        # Update menu actions
        self.update_undo_redo_actions()

    def record_undo_states_batch(self, entries):
        """Записать много записей отмены за один раз с одним проходом UI/обрезки в конце.
        
        ``entries`` — итерируемое объектов в виде словарей
        ``{"segment_id", "old_target", "new_target", "old_status", "new_status"}``
        ИЛИ кортежей ``(segment_id, old_target, new_target, old_status, new_status)``.
        
        Записи, где не изменились ни цель, ни статус, молча пропускаются. Используется
        массовыми операциями, чтобы избежать накладных расходов N×обновление Qt-действий
        и N×list.pop(0), когда батч больше max_undo_levels."""
        appended = 0
        for entry in entries:
            if isinstance(entry, dict):
                old_target = entry.get("old_target", "")
                new_target = entry.get("new_target", "")
                old_status = entry.get("old_status", "")
                new_status = entry.get("new_status", "")
                segment_id = entry.get("segment_id")
            else:
                # Tuple form
                segment_id, old_target, new_target, old_status, new_status = entry

            if old_target == new_target and old_status == new_status:
                continue

            self.undo_stack.append({
                "segment_id": segment_id,
                "old_target": old_target,
                "new_target": new_target,
                "old_status": old_status,
                "new_status": new_status,
            })
            appended += 1

        if appended == 0:
            return

        # Trim once at the end – avoids N pop(0) operations for huge batches
        overflow = len(self.undo_stack) - self.max_undo_levels
        if overflow > 0:
            del self.undo_stack[:overflow]

        # Clear redo stack (can't redo after new edits) and refresh menu once
        self.redo_stack.clear()
        self.update_undo_redo_actions()

    def undo_action_handler(self):
        """Обработка Undo (Ctrl+Z) — откат последней записанной замены цели/статуса."""
        if not self.undo_stack:
            return

        action = self.undo_stack.pop()
        # Structural edits (split / merge) carry full before/after snapshots.
        if action.get("type") == "structural":
            self._apply_structural_history(action, redo=False)
            self.redo_stack.append(action)
            self.update_undo_redo_actions()
            return
        if self._apply_undo_redo_action(action, action["old_target"], action["old_status"]):
            self.redo_stack.append(action)
        self.update_undo_redo_actions()

    def redo_action_handler(self):
        """Обработка Redo (Ctrl+Shift+Z / Ctrl+Y) — повтор последней отменённой замены."""
        if not self.redo_stack:
            return

        action = self.redo_stack.pop()
        if action.get("type") == "structural":
            self._apply_structural_history(action, redo=True)
            self.undo_stack.append(action)
            self.update_undo_redo_actions()
            return
        if self._apply_undo_redo_action(action, action["new_target"], action["new_status"]):
            self.undo_stack.append(action)
        self.update_undo_redo_actions()

    def _apply_undo_redo_action(self, action, target, status) -> bool:
        """Установить заданную цель/статус на сегменте действия и обновить его строку. Общая для undo и redo. Возвращает True, если сегмент найден и обновлён, иначе False (тогда вызывающий код отбрасывает действие).
        
        NB: модель сегмента использует поля ``id`` / ``target`` (не ``segment_id`` /
        ``target_text``), сетка — ``self.table`` (не ``self.grid``), а ячейка Target —
        редактируемый виджет в колонке 3 (Status — колонка 4). Прежняя реализация
        использовала все старые имена и молча выбрасывала исключения."""
        if not self.get_current_project():
            return False

        segment_id = action["segment_id"]
        segment = next((s for s in self.get_current_project().segments if s.id == segment_id), None)
        if segment is None:
            return False

        segment.target = target
        segment.status = status

        row = self._find_row_for_segment(segment_id)
        if row >= 0:
            # Target column (3) is an editable QTextEdit cell widget.
            target_widget = self.get_table().cellWidget(row, 3)
            if target_widget is not None and hasattr(target_widget, 'setPlainText'):
                display = (self.apply_invisible_replacements(target)
                           if self.apply_invisible_replacements is not None else target)
                target_widget.blockSignals(True)
                target_widget.setPlainText(display)
                target_widget.blockSignals(False)
            # Status column (4) is refreshed via its dedicated helper.
            self._update_status_cell(row, segment)

        self.mark_project_modified()
        self.update_window_title()
        if self.update_progress_stats is not None:
            self.update_progress_stats()
        return True

    def _push_structural_undo(self, before, after, focus_id, op, row):
        """Записать обратимое структурное изменение (split / merge) как снимки «до/после» всего списка сегментов. ``op`` ('split'/'merge') и ``row`` позволяют undo/redo применять тот же быстрый инкрементальный апдейт сетки."""
        import copy
        self.undo_stack.append({
            "type": "structural",
            "op": op,
            "row": row,
            "before": before,                 # already a snapshot from the caller
            "after": copy.deepcopy(after),     # snapshot the post-edit list
            "focus_id": focus_id,
        })
        if len(self.undo_stack) > self.max_undo_levels:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.update_undo_redo_actions()
        self.mark_project_modified()

    def _apply_structural_history(self, action, redo: bool):
        """Undo или redo структурного (split/merge) изменения.
        
        Восстанавливает соответствующий полный снимок списка (корректность данных
        в этом случае не под вопросом), затем применяет тот же быстрый инкрементальный
        дельта-апдейт сетки, что и исходное изменение, — undo/redo так же быстры, как
        само изменение, а не полная перестройка. При любом несоответствии — откат
        к полной перезагрузке."""
        import copy
        if not self.get_current_project():
            return
        snap = action["after"] if redo else action["before"]
        self.get_current_project().segments = copy.deepcopy(snap)
        # Keep the save-order list in sync (the data-loss fix) on every history step.
        self.set_original_segment_order(self.get_current_project().segments.copy())
        self.mark_project_modified()

        op = action.get("op")
        row = action.get("row")
        focus_id = action.get("focus_id")
        segs = self.get_current_project().segments

        did_fast = False
        if (op in ("split", "merge") and isinstance(row, int)
                and self.get_current_sort() is None):
            # After restoring the snapshot, is the segment at `row` currently in
            # its split (two rows) or merged (one row) form?
            split_state = (op == "split" and redo) or (op == "merge" and not redo)
            try:
                if split_state and row + 1 < len(segs):
                    # Grid currently shows ONE row here; expand to two.
                    self._split_segment_grid_fast(row, segs[row], segs[row + 1])
                    did_fast = True
                elif not split_state:
                    # Grid currently shows TWO rows here; collapse to one.
                    self._merge_segment_grid_fast(row, segs[row])
                    did_fast = True
            except Exception as e:
                self.log(f"Fast undo/redo refresh failed ({e}); full reload.")
                did_fast = False

        if not did_fast:
            self.load_segments_to_grid()

        self._select_grid_row_by_id(focus_id)
        if self.update_progress_stats is not None:
            self.update_progress_stats()
        self.update_window_title()
        try:
            self.refresh_preview()
        except Exception:
            pass

    def update_undo_redo_actions(self):
        """Обновить состояние включённости пунктов меню undo/redo."""
        self.get_undo_action().setEnabled(len(self.undo_stack) > 0)
        self.get_redo_action().setEnabled(len(self.redo_stack) > 0)
