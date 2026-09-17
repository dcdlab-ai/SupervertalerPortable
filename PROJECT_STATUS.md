# PROJECT_STATUS.md

**Точка входа для актуального состояния проекта.** Обновляется в конце каждого шага/батча —
читать этот файл вместо повторного просмотра всех документов. Подробности каждого шага — в
`EXTRACTION_PLAN.md` (секции «Статус Step N после Batch #X») и `docs/refactoring/`.

**Обновлено:** 2026-09-17 (Batch #6 Stage 2) • **Текущий шаг:** Step 6 Stage 2 выполнен (helpers.py); СТОП — ждать GO владельца → Stage 3 (pagination.py)

## Кратко: где мы находимся

Инкрементальная декомпозиция монолита `Supervertaler.py` (73 337 строк на старте;
сейчас **69 428**) в пакеты `modules/` по плану `EXTRACTION_PLAN.md` (Step 0–14).
Выполнены **Step 1–5** (батчи #1, #2, #3a, #3b, #3c, #4, #5). **Step 6 (Batch #6):
Stage 1 (инвентаризация) и Stage 2 (helpers.py → modules/grid/) выполнены**;
Stage 3 (pagination.py) ждёт GO владельца. Среда, тестирование и валидация — по
`AGENTS.md` (обязательно к прочтению перед любой работой).

## Прогресс по шагам EXTRACTION_PLAN.md

| Step | Что | Статус | Батч / артефакты |
|---|---|---|---|
| 0 | Dead-инвентарь, базовая линия | ✅ выполнен (база до Batch #1) | `DEAD_CODE_REPORT.md`; решения по удалению — в backlog |
| 1 | Модели данных → `modules/models.py` | ✅ выполнен | Batch #1, коммит `969c9fe`; отчёт `docs/refactoring/reports/ОТЧЁТ Batch #1.txt` |
| 2 | DOCX tag-движок → `modules/tag_manager.py` | ✅ выполнен | Batch #2, коммит `1ac400d`; см. TECH-DEBT в конце `EXTRACTION_PLAN.md` |
| 3 | Event-фильтры + диалоги + чекбоксы | ✅ выполнен | Batch #3a `c7497d6` (`modules/event_filters.py`), #3b `4895e72` (`modules/dialogs/`), #3c `e543787` (`modules/styled_widgets.py`) |
| 4 | Чистые QThread-воркеры | ✅ выполнен | Batch #4 (этот коммит; `modules/workers/`); отчёт `docs/refactoring/reports/ОТЧЁТ Batch #4.txt` |
| 5 | Undo-менеджер | ✅ выполнен | Batch #5 Stage 1 `c11e1bc` (инвентаризация) + Stage 2 (`modules/undo_manager.py`); отчёты `docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 1.txt` и `…Stage 2.txt` |
| 6 | Grid: helpers/pagination/filters | 🟡 Stage 1–2 выполнены; Stage 3 (pagination) ждёт GO | Stage 1 (этот коммит c5a5da1); Stage 2 — `modules/grid/helpers.py` (чистые функции, 16 функций + 17 делегатов; `modules/grid/__init__.py`); отчёты `docs/refactoring/reports/ОТЧЁТ Batch #6 Stage {1,2}.txt`; аудиты `docs/refactoring/audits/batch6_stage1_*.txt`, `*batch6stage2*.txt` |
| 7 | Settings service (IO-слой) | ⬜ не начат | — |
| 8 | Grid: render + match panel + comments UI | ⬜ не начат | — |
| 9 | Мелкие изолированные фичи | ⬜ не начат | — |
| 10 | Find&Replace + поиск | ⬜ не начат | — |
| 11 | Импорт/Экспорт контроллеры | ⬜ не начат | — |
| 12 | TM / Termbase сервисы | ⬜ не начат | — |
| 13 | Перевод-ядро (вкл. PreTranslationWorker) | ⬜ не начат | — |
| 14 | SuperLookup + Voice + финальный cleanup | ⬜ не начат | — |

## Что дальше: Step 6 — Grid: helpers/pagination/filters (Batch #6)

**Stage 2 выполнен** (17.09.2026, helpers.py). Состав переноса: 16 pure-функций
в `modules/grid/helpers.py` (модуль чистых функций — решение владельца §6 Stage 1;
без класса и ссылок на окно) + `_get_line_edit_text` оставлен в монолите целиком
(п.Г: getattr/setattr-логика self-специфична) + 17 тонких делегатов с исходными
именами/сигнатурами. Граница `_navigate_to_segment_by_id` уточнена AST:
54700–**54769** (не 54770). Валидация: 8 метрик ровные; SHA256-манифест — только
монолит + 2 новых файла; Undo/Redo-сценарий Batch #5 — 38/38 PASS (делегаты
_find_row_for_segment/_select_grid_row_by_id остались bound-методами);
stage2-сценарий 34/35 (единственный FAIL — предсуществующее поведение навигации
в offscreen, подтверждено идентичным before/after-пробой из worktree HEAD);
smoke save/load — OK. Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 2.txt`;
сигнатуры: `docs/refactoring/audits/batch6_stage2_signatures.txt`.
**Дальше: Stage 3 = pagination.py (12 методов + 2 selection-micro, ~367–391
строк) — отдельный промпт после GO владельца; затем Stage 4 = filters.py.**

**Stage 1 выполнен** (16.09.2026, read-only, код не тронут). Главная находка:
документированные окна Step 6 в EXTRACTION_PLAN.md устарели сильнее, чем
ожидалось (сдвиг ~−3300, а не −531) и почти целиком указывают на посторонний
код (termbase/TM-поиск, proofreading, voice). Реальные кластеры найдены по
содержимому (AST): пагинация 28266–28878, фильтры/невидимые 52186–53901 +
56218–56280 + 28850–28878. Итоговый состав на перенос — **48 методов, ~1780
строк**: pagination.py 12 (367), filters.py 20 (1097), helpers.py 16 (316);
на решение ещё 3 метода (selection-micro, _navigate_to_segment_by_id,
show_manage_views_dialog). Цикл SCC#1: центр подтверждён
`load_segments_to_grid` 41428–41598; на уровне self-вызовов строгого цикла
нет (SCC=1; fwd=82/bwd=60) — цикл замыкается через populate-механику и
UI-сигналы; из кандидатов его касается ТОЛЬКО `apply_sort` (2 прямых вызова,
разрыв — reload_callback параметром). DYNAMIC_ENTRY_POINT: 9 методов
(go_to_prev/next_page, select_range_page_up/down, on_page_size_changed,
_on_file_filter_changed, toggle_all_invisibles, show_advanced_filters_dialog,
filter_on_selected_text) — обязательны делегаты. Реальные внешние связи — 3
bound-метода в modules/undo_manager.py (переживают перенос при сохранении
делегатов). Рекомендация: helpers.py — функции; pagination.py/filters.py —
классы-контейнеры; под-батчи Stage 2=helpers → 3=pagination → 4=filters.
Полный отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 1.txt`;
аудиты: `docs/refactoring/audits/batch6_stage1_{windows_ast,cluster_layout,
named_helpers_ast,scc1,cycle_intersections,callsites_categorized,
dependencies}.txt`. Ожидание решения владельца (6 открытых вопросов в §8
отчёта) → Stage 2.

Фактические AST-границы окна бывшего Step 5 в монолите (HEAD после Stage 2,
пересчитаны AST — документированные номера в CODE_MAP_REFACTOR.md устарели):
- Делегаты UndoManager: `record_undo_state` 9395–9397, `record_undo_states_batch`
  9399–9401, `undo_action_handler` 9403–9405, `redo_action_handler` 9407–9409,
  `_apply_undo_redo_action` 9411–9413, `_push_structural_undo` 9618–9620,
  `_apply_structural_history` 9704–9706, `update_undo_redo_actions` 9708–9710.
- Перенесены в Stage 2 (теперь делегаты modules/grid/helpers.py):
  `_segment_for_grid_row` 9416–9420, `_recompute_list_numbers` 9640–9643,
  `_reindex_grid_rows_from` 9645–9648, `_select_grid_row_by_id` 9650–9655.
- Остаток окна (кандидаты пагинации Stage 3 / монолит): `_split_segment_at_row`
  9422–9463, `_merge_segment_at_row` 9465–9499, `_delete_segments_at_rows`
  9501–9549, `delete_current_segments` 9551–9573, `split_current_segment`
  9576–9605, `merge_current_segment` 9607–9616, `_sync_after_structural`
  9622–9638, `_split_segment_grid_fast` 9657–9683, `_merge_segment_grid_fast`
  9685–9702, `create_quick_access_toolbar` 9712–9755.

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
