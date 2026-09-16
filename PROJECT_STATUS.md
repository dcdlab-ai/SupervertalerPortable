# PROJECT_STATUS.md

**Точка входа для актуального состояния проекта.** Обновляется в конце каждого шага/батча —
читать этот файл вместо повторного просмотра всех документов. Подробности каждого шага — в
`EXTRACTION_PLAN.md` (секции «Статус Step N после Batch #X») и `docs/refactoring/`.

**Обновлено:** 2026-09-16 (Batch #5 Stage 2) • **Текущий шаг:** Step 5 выполнен полностью (Stage 1 + Stage 2); следующий — Step 6 (Grid: helpers/pagination/filters), ждать GO владельца

## Кратко: где мы находимся

Инкрементальная декомпозиция монолита `Supervertaler.py` (73 337 строк на старте;
сейчас **69 696**) в пакеты `modules/` по плану `EXTRACTION_PLAN.md` (Step 0–14).
Выполнены **Step 1–5** (батчи #1, #2, #3a, #3b, #3c, #4, #5). Следующий — **Step 6:
Grid helpers/pagination/filters**. Среда, тестирование и валидация — по `AGENTS.md`
(обязательно к прочтению перед любой работой).

## Прогресс по шагам EXTRACTION_PLAN.md

| Step | Что | Статус | Батч / артефакты |
|---|---|---|---|
| 0 | Dead-инвентарь, базовая линия | ✅ выполнен (база до Batch #1) | `DEAD_CODE_REPORT.md`; решения по удалению — в backlog |
| 1 | Модели данных → `modules/models.py` | ✅ выполнен | Batch #1, коммит `969c9fe`; отчёт `docs/refactoring/reports/ОТЧЁТ Batch #1.txt` |
| 2 | DOCX tag-движок → `modules/tag_manager.py` | ✅ выполнен | Batch #2, коммит `1ac400d`; см. TECH-DEBT в конце `EXTRACTION_PLAN.md` |
| 3 | Event-фильтры + диалоги + чекбоксы | ✅ выполнен | Batch #3a `c7497d6` (`modules/event_filters.py`), #3b `4895e72` (`modules/dialogs/`), #3c `e543787` (`modules/styled_widgets.py`) |
| 4 | Чистые QThread-воркеры | ✅ выполнен | Batch #4 (этот коммит; `modules/workers/`); отчёт `docs/refactoring/reports/ОТЧЁТ Batch #4.txt` |
| 5 | Undo-менеджер | ✅ выполнен | Batch #5 Stage 1 `c11e1bc` (инвентаризация) + Stage 2 (этот коммит; `modules/undo_manager.py`); отчёты `docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 1.txt` и `…Stage 2.txt` |
| 6 | Grid: helpers/pagination/filters | ⬜ не начат | — |
| 7 | Settings service (IO-слой) | ⬜ не начат | — |
| 8 | Grid: render + match panel + comments UI | ⬜ не начат | — |
| 9 | Мелкие изолированные фичи | ⬜ не начат | — |
| 10 | Find&Replace + поиск | ⬜ не начат | — |
| 11 | Импорт/Экспорт контроллеры | ⬜ не начат | — |
| 12 | TM / Termbase сервисы | ⬜ не начат | — |
| 13 | Перевод-ядро (вкл. PreTranslationWorker) | ⬜ не начат | — |
| 14 | SuperLookup + Voice + финальный cleanup | ⬜ не начат | — |

## Что дальше: Step 6 — Grid: helpers/pagination/filters (Batch #6)

**Step 5 выполнен полностью** (Stage 2, 16.09.2026): 8 методов перенесены в
`modules/undo_manager.py` (класс `UndoManager`, 302 строки), состояние
`undo_stack`/`redo_stack`/`max_undo_levels` — в менеджере, в монолите — 8 тонких
делегатов с теми же именами (все 43 call sites не тронуты), инициализация в
`__init__` заменена созданием `self._undo_manager = UndoManager(<колбэки>)`.
Зависимости — только именованные колбэки (геттеры `get_current_project`,
`get_table`, `get_current_sort`, `get_undo_action`, `get_redo_action`; сеттер
`set_original_segment_order`; действие `mark_project_modified`; статические
bound-method ссылки с именами оригинальных методов). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 2.txt` (GO; валидация 38/38
функциональных сценариев, 14/14 NOT MOVE byte-identity, метрики/манифест чистые).
Открытый вопрос для владельца — семантика batch-undo (см. «Непокрытые» в отчёте
Stage 2): фактическое поведение оригинала — N записей стека с одним trim/UI-проходом,
undo по одной записи (LIFO); сохранено дословно.

Фактические AST-границы окна бывшего Step 5 в монолите (HEAD после Stage 2,
пересчитаны AST — документированные номера в CODE_MAP_REFACTOR.md устарели):
- Делегаты UndoManager: `record_undo_state` 9394–9396, `record_undo_states_batch`
  9398–9400, `undo_action_handler` 9402–9404, `redo_action_handler` 9406–9408,
  `_apply_undo_redo_action` 9410–9412, `_push_structural_undo` 9628–9630,
  `_apply_structural_history` 9772–9774, `update_undo_redo_actions` 9776–9778.
- NOT MOVE (кандидаты Step 6 / grid-хелперы): `_segment_for_grid_row` 9415–9430,
  `_split_segment_at_row` 9432–9473, `_merge_segment_at_row` 9475–9509,
  `_delete_segments_at_rows` 9511–9559, `delete_current_segments` 9561–9583,
  `split_current_segment` 9586–9615, `merge_current_segment` 9617–9626,
  `_sync_after_structural` 9632–9648, `_recompute_list_numbers` 9650–9677,
  `_reindex_grid_rows_from` 9679–9700, `_select_grid_row_by_id` 9702–9723,
  `_split_segment_grid_fast` 9725–9751, `_merge_segment_grid_fast` 9753–9770,
  `create_quick_access_toolbar` 9780–9823.

Состояние `PreTranslationWorker` после Batch #4: перенесён в монолите на
5337–6043, содержимое байт-в-байт без изменений (относится к Step 13).
Справка по перенесённым в Batch #4 воркерам: `modules/workers/`
(`TMSearchWorker`, `ProofreadWorker`, `GlossaryExtractionWorker`); их callsites
в монолите: 18787 (glossary), 48152 (proofread), 63214 (TM search). Базовые
метрики, снимки и проверки — по чек-листу «Общая валидация» в `EXTRACTION_PLAN.md`
и практикам `AGENTS.md` (разделы про батчи #2/#3a–#4 и `tools/batch_validation/`).

## Важные решения и подводные камни (не перечитывать всё)

- **Tag-грамматики**: в `modules/tag_manager.py` намеренно живут ДВЕ несовместимые
  реализации (монолит-блок и TagManager-методы) — НЕ объединять и не переключать
  callsites. Детали: «TECH-DEBT» в конце `EXTRACTION_PLAN.md`.
- **Документированные диапазоны строк в плане устаревают после каждого батча** —
  границы классов пересчитывать через AST (`ast.parse`, `lineno`/`end_lineno`).
- **Пользовательские данные** не следуют за cwd: `get_user_data_path()` резолвится от
  глобального `~/.supervertaler_config.json` — read-only пробы безопасны везде, smoke-тесты
  пишут в продакшн-данные.
- **Git**: ветка `main`, история переписана на noreply-адрес
  (`328762441+dcdlab-ai@users.noreply.github.com`); репозиторий —
  github.com/dcdlab-ai/SupervertalerPortable (private). Материалы батчей — в
  `docs/refactoring/{prompts,reports,audits}/`, в корень не складывать.

## Конвенция обновления этого файла

В конце каждого шага/батча: обновить строку таблицы прогресса, дату, счётчик строк
монолита, раздел «Что дальше» (с фактическими AST-границами) и блок «Важные решения»
при появлении новых. Коммитить вместе с финальным коммитом батча.
