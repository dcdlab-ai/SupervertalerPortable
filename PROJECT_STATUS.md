# PROJECT_STATUS.md

**Точка входа для актуального состояния проекта.** Обновляется в конце каждого шага/батча —
читать этот файл вместо повторного просмотра всех документов. Подробности каждого шага — в
`EXTRACTION_PLAN.md` (секции «Статус Step N после Batch #X») и `docs/refactoring/`.

**Обновлено:** 2026-09-18 (Batch #6 Stage 4) • **Текущий шаг:** Step 6 ЗАКРЫТ ЦЕЛИКОМ (helpers+pagination+filters, модуль 68 386 строк); СТОП — ждать решения владельца по Step 7

## Кратко: где мы находимся

Инкрементальная декомпозиция монолита `Supervertaler.py` (73 337 строк на старте;
сейчас **68 386**) в пакеты `modules/` по плану `EXTRACTION_PLAN.md` (Step 0–14).
Выполнены **Step 1–5** (батчи #1, #2, #3a, #3b, #3c, #4, #5) и **Step 6 целиком**
(Batch #6: Stage 1 — инвентаризация, Stage 2 — `modules/grid/helpers.py`,
Stage 3 — `modules/grid/pagination.py`, Stage 4 — `modules/grid/filters.py`).
Дальше — Step 7 (Settings service, IO-слой) только по решению владельца. Среда,
тестирование и валидация — по `AGENTS.md` (обязательно к прочтению перед любой
работой).

## Прогресс по шагам EXTRACTION_PLAN.md

| Step | Что | Статус | Батч / артефакты |
|---|---|---|---|
| 0 | Dead-инвентарь, базовая линия | ✅ выполнен (база до Batch #1) | `DEAD_CODE_REPORT.md`; решения по удалению — в backlog |
| 1 | Модели данных → `modules/models.py` | ✅ выполнен | Batch #1, коммит `969c9fe`; отчёт `docs/refactoring/reports/ОТЧЁТ Batch #1.txt` |
| 2 | DOCX tag-движок → `modules/tag_manager.py` | ✅ выполнен | Batch #2, коммит `1ac400d`; см. TECH-DEBT в конце `EXTRACTION_PLAN.md` |
| 3 | Event-фильтры + диалоги + чекбоксы | ✅ выполнен | Batch #3a `c7497d6` (`modules/event_filters.py`), #3b `4895e72` (`modules/dialogs/`), #3c `e543787` (`modules/styled_widgets.py`) |
| 4 | Чистые QThread-воркеры | ✅ выполнен | Batch #4 (этот коммит; `modules/workers/`); отчёт `docs/refactoring/reports/ОТЧЁТ Batch #4.txt` |
| 5 | Undo-менеджер | ✅ выполнен | Batch #5 Stage 1 `c11e1bc` (инвентаризация) + Stage 2 (`modules/undo_manager.py`); отчёты `docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 1.txt` и `…Stage 2.txt` |
| 6 | Grid: helpers/pagination/filters | ✅ выполнен (Step 6 закрыт целиком) | Batch #6 Stage 1 `c5a5da1`; Stage 2 `4ace504` (`modules/grid/helpers.py`, 16 функций + 17 делегатов); Stage 3 `26b998c` (`modules/grid/pagination.py`, 14 функций + 14 делегатов + 2 константы); Stage 4 (`modules/grid/filters.py`, 20 функций + 1 внутренняя + 20 делегатов); отчёты `docs/refactoring/reports/ОТЧЁТ Batch #6 Stage {1,2,3,4}.txt`; аудиты `docs/refactoring/audits/batch6_stage1_*.txt`, `*batch6stage{2,3,4}*` |
| 7 | Settings service (IO-слой) | ⬜ не начат | — |
| 8 | Grid: render + match panel + comments UI | ⬜ не начат | — |
| 9 | Мелкие изолированные фичи | ⬜ не начат | — |
| 10 | Find&Replace + поиск | ⬜ не начат | — |
| 11 | Импорт/Экспорт контроллеры | ⬜ не начат | — |
| 12 | TM / Termbase сервисы | ⬜ не начат | — |
| 13 | Перевод-ядро (вкл. PreTranslationWorker) | ⬜ не начат | — |
| 14 | SuperLookup + Voice + финальный cleanup | ⬜ не начат | — |

## Что дальше: Step 6 ЗАКРЫТ ЦЕЛИКОМ (Batch #6 Stage 4 — последний под-батч)

**Stage 4 выполнен** (18.09.2026, filters.py). Состав переноса: 20 методов
(20 pure-функций + 1 внутренняя `_refresh_grid_invisibles_cells`) в
`modules/grid/filters.py` (1277 строк) + 20 тонких делегатов в монолите с
точными исходными именами/сигнатурами (7 делегатов сохранили ведущий `_`,
одноимённые функции — без него). Замена выполнялась строго по AST-спанам
снизу вверх ПО ИМЕНАМ (кластер — не непрерывный блок; окно 51794–55821 на HEAD
содержит посторонние блоки: show_manage_views_dialog, `_refresh_source_column_
display`, spellcheck 52645–53126, comments/dictation 53510–55753).
AST: 22/22 совпало с координаторской таблицей байт-в-байт; 20 тел = 1097 строк →
20 делегатов = 291 строка + 1 строка импорта. Монолит **69 191 → 68 386**
(net −805; numstat: `Supervertaler.py` +222/−1027, `modules/grid/__init__.py`
+54/−3, новый `modules/grid/filters.py` 1277). Класс SupervertalerQt:
6053–63263 → 6054–62458; 819 методов / 838 членов до и после.
Стоп-условия не сработали: 8 метрик ровные (1211/18/35/24/24/0/85/2);
манифест — только монолит + `__init__.py` + новый `filters.py` (0 правок
внешних call sites подтверждено SHA256); 3 NOT-MOVE блока BYTE-IDENTICAL
(`show_manage_views_dialog` b3d00f39…, `_refresh_source_column_display`
90d2bf1b…, `_update_bulk_menu_label` 1d971a9a…); контрольные блоки spellcheck
9ac157cd… и comments/dictation 6496a472… — по 1 вхождению; сценарии фильтров
65/65 PASS (включая F11 apply_sort → reload_callback, единственное пересечение
с SCC#1); Undo/Redo Batch #5 — 38/38 PASS (третий прогон); smoke save/load OK.
Две находки вне «механического» скоупа: (1) предсуществующий бесконечный цикл
в `clear_filter_highlights_in_widget` при наложении+снятии подсветки в одном
диапазоне — воспроизводится и на HEAD, регрессии нет; (2) в этом же коммите
исправлен порядок записи настроек невидимых символов (write_settings_callback
теперь вызывается ДО refresh — как в исходном теле HEAD). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 4.txt`; сигнатуры:
`docs/refactoring/audits/batch6_stage4_signatures.txt`.
**Итог Step 6:** `modules/grid/` = helpers.py 507 + pagination.py 584 +
filters.py 1277 + `__init__.py` 134; 50 публичных функций + 51 делегат в
монолите. Документация Step 6 закрыта целиком.

**Дальше: СТОП — ждать решения владельца.** Следующий шаг плана — Step 7
(Settings service, IO-слой). Номера строк в `EXTRACTION_PLAN.md` для Step 7
устарели (Batch #1–#6 сдвинули монолит на −4951); предварительная AST-карта
после Stage 4 (только чтение, кандидаты IO — 46 методов, 1709 строк; UI-билдеры
вкладок исключены): `_get_settings_dir` 44639–44641, `_get_unified_settings_
path` 44643–44645, `_load_unified_settings` 44647–44661, `_save_unified_settings`
44663–44672, `_load_settings_section` 44674–44676, `_save_settings_section`
44678–44682, `load_general_settings` 44522–44618, load/save clipboard privacy
44690–44722, `_migrate_settings_to_unified` 44724–44814, general-from-file
44883–44929, dictation 44931–45002, language pair/language 45004–45021 и
45228–45261, voice vocabulary 45029–45092, spellcheck IO 52262–52280, llm/proxy
56987–57111, api keys 61235–61247, «недавние проекты» 32231–32430. Точный состав
и границы — пересчитать AST заново на старте Step 7 (как требует AGENTS.md).

**Stage 3 выполнен** (17.09.2026, pagination.py). Состав переноса: 14 методов
(14 pure-функций) в `modules/grid/pagination.py` + 2 module-level константы
`PAGE_AUTO_ALL_THRESHOLD`/`PAGE_FALLBACK_SIZE` (сняты с класса SupervertalerQt;
в классе остались только константы populate-кластера `BACKGROUND_POPULATE_*`).
AST-границы Stage 3: блок 28198–28717 (сдвиг −434 от чисел Stage 1; координаторская
таблица Stage 3 подтверждена БАЙТ-в-БАЙТ), внутри блока НЕ переносились
`_start_background_populate`/`_background_populate_step` (Step 8, populate-кластер).
Стоп-условия не сработали: 8 метрик ровные; манифест — только монолит +
`modules/grid/__init__.py` + новый `pagination.py`; SHA256 двух NOT-MOVE методов —
BYTE-IDENTICAL до/после; Undo/Redo-сценарий Batch #5 — 38/38 PASS;
stage3-сценарий 56/56 PASS; smoke save/load — OK. Монолит 69 428 → **69 191**
(net −237; diff stat: +178 / −376 по двум файлам). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 3.txt`; сигнатуры:
`docs/refactoring/audits/batch6_stage3_signatures.txt`.
**Дальше: Stage 4 = filters.py** — отдельный промпт после GO владельца. Границы
для Stage 4 надо пересчитать AST заново (Stage 1 давал 52186–53901 + 56218–56280 +
28850–28878 — сдвиг после Stage 2/3 уже −434 и станет больше).

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
- **Метрика `singleShot` ловит упоминания в докстрингах/комментариях** (Stage 3: один
  «лишний» singleShot дал ложный DIFF, пока упоминание не перефразировали). Формулировки
  в перенесённых докстрингах не должны содержать самих метрик-паттернов.
- **Позиционные аргументы pure-функций**: у Stage 3 при первой сборке делегат передавал
  `_page_size_decided_for` в мёртвый второй параметр (`grid_page_size`) — combo молча не
  обновлялся. Все новые pure-функции вызывать с явными ключевыми аргументами, а
  неиспользуемые параметры не заводить (найдено функциональным сценарием P13/P14).
- **Offscreen-квирк фокуса таблицы**: на непоказанном виджете `table.setCurrentCell()`
  не меняет `currentRow` (было и на HEAD — проба `probe_head_vs_work.py`); в тест-харнессах
  резервный путь — `selectionModel().setCurrentIndex(...)`, а фокус-сдвиги
  `select_range_page_*` проверять по `selectedRanges()`.
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
