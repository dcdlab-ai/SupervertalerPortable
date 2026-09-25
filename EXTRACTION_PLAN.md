# EXTRACTION_PLAN.md
**Проект:** Supervertaler — практический план декомпозиции `Supervertaler.py` (73 337 строк) в `modules/`
**Дата:** 2026-09-12 • Основа: CODE_MAP_REFACTOR.md, DEPENDENCY_MAP.md, DEAD_CODE_REPORT.md
**Главные правила:** (1) один шаг = одна подсистема = одна проверяемая итерация; (2) `modules/` никогда не импортирует `Supervertaler.py`; (3) переиспользовать существующие модули, не создавать дубликаты; (4) поведение не меняется — только перемещение и явные интерфейсы; (5) перед началом: `git init` + эталонный smoke-прогон.

## Общая валидация (применяется к КАЖДОМУ шагу)

- **AST/token-checks:** `python -m py_compile <затронутые файлы>`; повторный прогон AST-аудита — число методов класса и точки входа (connect/shortcut/timer/invokeMethod) не уменьшились; diff «словаря имён» до/после пуст (кроме помеченных dead).
- **Runtime checks:** запуск приложения; создание проекта → импорт DOCX/TXT → перевод сегмента → подтверждение → экспорт; открытие настроек (каждой затронутой вкладки); F&R; TM/termbase-операции; SuperLookup (Ctrl+Alt+L); голосовая диктовка (если затронута).
- **Integrity:** SHA256-снимок всех .py до шага; после — изменились только файлы шага.
- **Rollback:** каждый шаг — отдельный коммит; откат = `git revert`; имена классов/функций сохраняются (алиас-импорты в монолите), поэтому откат тривиален.

---

## Step 0

### Goal
Подтвердить dead-инвентарь и зафиксировать базовую линию. Ничего не удалять.
### Source
DEAD_CODE_REPORT.md (16 DEFINITELY_DEAD + 57 PROBABLY_DEAD + 5 shadowed + 19 orphan-модулей).
### Destination
—
### Objects to move
—
### Existing module to reuse
—
### New module if required
—
### Dependencies
—
### Required import changes
—
### Circular dependency risks
—
### Risk
LOW (не меняет код; только пометки/документация и решение владельца по удалению).
### Validation
Список dead-методов вычитан владельцем; каждое решение зафиксировано (удалить/оставить/перенести).
### Rollback
—
### Expected result
Утверждённый список на удаление (отдельный будущий PR), защищённые имена DYNAMIC_ENTRY_POINT (219 методов) в чек-листе ревью.

## Step 1 — Модели данных

### Goal
Вынести чистые data-классы.
### Source
`Supervertaler.py` 1775–2402.
### Destination
`modules/models.py`.
### Objects to move
`Comment` (6 методов), `Segment` (9), `Project` (3+class attrs).
### Existing module to reuse
— (в modules/ нет дублей: find_replace_qt/theme_manager имеют свои to_dict, не конфликтуют).
### New module if required
`modules/models.py` (новый).
### Dependencies
Только stdlib (dataclasses, datetime). Проверить: Segment/Project не импортируют Qt — да (PURE).
### Required import changes
В монолите: `from modules.models import Comment, Segment, Project` (строка после существующих импортов modules). Внутренние ссылки `Comment(...)`/`Segment(...)`/`Project(...)` не меняются.
### Circular dependency risks
Нет (листья графа).
### Risk
LOW.
### Validation
py_compile; запуск; создание проекта; импорт; сохранение/загрузка .svproj; экспорт.
### Rollback
 revert; алиасы гарантируют совместимость.
### Expected result
−630 строк из монолита; модели доступны modules/ без зависимости от монолита.

## Step 2 — DOCX tag-движок (топ-функции)

### Goal
Вынести ~30 чистых функций форматирования и объединить с существующим `tag_manager`.
### Source
`Supervertaler.py` 494–1767 (+ static/classmethod-хелперы `_strip_inline_tags`, `_raw_to_visible_offset`, `_wysiwyg_runs_to_tagged_text`).
### Destination
`modules/tag_formatting.py` — ЛИБО расширение `modules/tag_manager.py`.
### Objects to move
`runs_to_tagged_text`, `tagged_text_to_runs`, `strip_formatting_tags`, `strip_outer_wrapping_tags`, `compact_tags`, `expand_compact_tags`, `extract_*_tags`, `apply/has_formatting_tags`, `get/set_docx_language`, `get_formatted_html_display`, `validate_tag_transfer`, `place_tags_via_llm`, pipe-хелперы (`count_pipe_symbols`…), `_normalize_ws_for_compare`, `_classify_tag`, `_tags_well_formed`, `_reinsert_tags_into_target` и др.
### Existing module to reuse
`modules/tag_manager.py` (дублирует runs_to_tagged_text/tagged_text_to_runs) — объединить: tag_manager поглощает монолит-версии, docx_handler переключить на нормальный импорт (`from modules.tag_manager import`, убрав bare-fallback на `docx_handler.py:21-24`).
### New module if required
`modules/tag_formatting.py`, если решено не трогать tag_manager API.
### Dependencies
stdlib + опционально docx-объекты как параметры; `place_tags_via_llm` принимает callback (не импортирует llm_clients).
### Required import changes
Монолит: `from modules.tag_formatting import ...` (30+ имён); вызовы методов `_strip_inline_tags(...)` → импортированные функции (осторожно: это classmethod/staticmethod — при выносе вызовы `self._strip_inline_tags` заменить на функции или оставить тонкие делегаты в классе на переходный период).
### Circular dependency risks
Нет. `tag_manager` ↔ `docx_handler` — унифицировать направление (tag_formatting ← docx_handler).
### Risk
LOW (функции чистые), MEDIUM в части classmethod-делегатов.
### Validation
Импорт DOCX с форматированием; экспорт target-DOCX; F&R с тегами; validate_tag_transfer юнит-сравнение (до/после переноса — одинаковый вывод на 3–5 файлах).
### Rollback
revert.
### Expected result
−1 300 строк; единая реализация tag-движка вместо 5 копий.

## Step 3 — Event-фильтры + диалоги + чекбоксы

### Goal
Вынести автономные Qt-компоненты.
### Source
`Supervertaler.py` 2403–2901 (фильтры), 7190–7786 + 8782–9091 (диалоги), 69759–70069 (чекбоксы по факту на момент Batch #3c; в документе ранее ошибочно 72559–72869).
### Destination
`modules/event_filters.py`; `modules/dialogs/` (theme_editor.py, detached_log.py, advanced_filters.py, scratchpad.py, live_progress.py, import_progress.py); чекбоксы → `modules/styled_widgets.py` (переиспользование!).
### Objects to move
`_QuitEventFilter`, `_CtrlReturnEventFilter`, `_GridArrowKeyEventFilter`, `_WheelGuard`, `_LoneCtrlEventFilter`, `GridTableEventFilter`; `ThemeEditorDialog`, `DetachedLogWindow`, `AdvancedFiltersDialog`, `ScratchpadDialog`, `LiveProgressDialog`, `_ImportProgressDialog`; `Pink/Blue/OrangeCheckmarkCheckBox`, `CustomRadioButton` (слить со styled_widgets: добавить параметры цвета).
### Existing module to reuse
`modules/styled_widgets.py` — обязательно (монолит дублирует 3×46L paintEvent).
### New module if required
`modules/event_filters.py`, `modules/dialogs/__init__.py`.
### Dependencies
Фильтры принимают `mw` параметром (уже так); диалоги — parent/аргументы. Чекбоксы: соответствие сигнатурам styled_widgets.
### Required import changes
Монолит: импорт классов; замена `getattr(parent, 'theme_manager')`-кода НЕ требуется (переносится как есть).
### Circular dependency risks
Нет.
### Risk
LOW.
### Validation
Запуск; закрытие окна (closeEvent-путь), tray; Esc-dismiss; scratchpad; advanced filters; live progress при импорте; тема-редактор; чекбоксы на вкладках TM/termbase/AI.
### Rollback
revert.
### Expected result
−1 900 строк; 15 классов в modules/.

#### Статус Step 3 после Batch #3a (2026-09-13)
Скоуп фильтров сокращён решением владельца. Перенесено в `modules/event_filters.py`: `_QuitEventFilter`, `_WheelGuard`, `_LoneCtrlEventFilter`, `GridTableEventFilter`. **НЕ перенесены** (остались в монолите, Supervertaler.py:676–892): `_CtrlReturnEventFilter`, `_GridArrowKeyEventFilter` — оба делают `isinstance`-проверки против `ReadOnlyGridTextEditor`/`EditableGridTextEditor`, `_GridArrowKeyEventFilter` также вызывает хелпер `_cleaned_modifiers`; вербатим-перенос невозможен без циклического импорта.

**PRE-CONDITION для будущего батча «грид-редакторы»:** сначала извлечь `ReadOnlyGridTextEditor`, `EditableGridTextEditor` и `_cleaned_modifiers` из монолита в modules/; только после этого `_CtrlReturnEventFilter` и `_GridArrowKeyEventFilter` переносятся в `modules/event_filters.py` вербатим. Не переносить эти два фильтра раньше редакторов и не разрешать `modules/` импортировать из монолита (запуск как `__main__` создал бы второй экземпляр модуля и сломал isinstance-сравнения).

#### Статус Step 3 после Batch #3b (2026-09-13)
Все 6 диалогов перенесены в новый пакет `modules/dialogs/` (по одному классу на файл + `__init__.py` с реэкспортом): `theme_editor.py` (`ThemeEditorDialog`), `detached_log.py` (`DetachedLogWindow`), `advanced_filters.py` (`AdvancedFiltersDialog`), `scratchpad.py` (`ScratchpadDialog`), `live_progress.py` (`LiveProgressDialog`), `import_progress.py` (`_ImportProgressDialog`). Диапазоны из этого плана (7190–7786 + 8782–9091) были устаревшими: фактические границы по AST — 5307–5901 (4 диалога) и 6903–7206 (2 прогресс-диалога, перемежались с воркерами Step 4); тела 4 воркеров не задеты (проверено байт-в-байт). Монолит импортирует все 6 имён одной строкой из `modules.dialogs`; callsite-ы конструкторов не менялись. Остаётся в Step 3: чекбоксы (Batch #3c) → слияние с `modules/styled_widgets.py`.

#### Статус Step 3 после Batch #3c (2026-09-13) — Step 3 ЗАВЕРШЁН
`Pink/Blue/OrangeCheckmarkCheckBox` и `CustomRadioButton` перенесены в существующий `modules/styled_widgets.py`. Диапазон из этого плана (72559–72869) был устаревшим: фактические границы по AST — 69759–70069. Гейт поведенческого сравнения (1.4): три чекбокса подтверждены идентичными `CheckmarkCheckBox` с точностью до цвета (12 offscreen-сценариев пиксельно идентичны, stylesheet отличается ровно 4 hex-подстановками) — реализованы как тонкие подклассы приватной базы `_ColoredCheckmarkCheckBox` без дублирования paintEvent. `CustomRadioButton` оказался НЕ дублем `CheckmarkRadioButton` (18px кольцо + зелёная точка против 16px зелёной заливки + белой точки) — перенесён ВЕРБАТИМ отдельным классом согласно предусмотренному протоколом исходу Этапа 2.2. Монолит импортирует все 4 имени из `modules.styled_widgets`; 16 callsite-ов конструкторов текстуально не менялись. On this Step 3 полностью завершён; следующий — Step 4 (чистые QThread-воркеры), запуск только по команде владельца.

## Step 4 — Чистые QThread-воркеры

### Goal
Вынести воркеров без зависимости от MainWindow.
### Source
`Supervertaler.py` (после Batch #3c, фактические границы по AST; сдвиг +1 относительно post-3b из-за второй строки импорта styled_widgets): TMSearchWorker 5334–5457, ProofreadWorker 6169–6326, GlossaryExtractionWorker 6337–6408 (в документе ранее были ошибочные 7787–7912 / 8622–8779 / 9092–9169; PreTranslationWorker 5460–6166 — НЕ переносится, см. Step 13).
### Destination
`modules/workers/` (`tm_search.py`, `proofread.py`, `glossary.py`).
### Objects to move
3 класса целиком.
### Existing module to reuse
Паттерн QThread+сигналы уже используется в modules (tm_manager_qt и др.) — но переиспользование здесь = перенос классов, не копирование.
### New module if required
`modules/workers/__init__.py`.
### Dependencies
Только аргументы + pyqtSignal. ВНИМАНИЕ: `ProofreadWorker.cancel` и `TMSearchWorker.cancel` идентичны — не дублировать, оставить по классу.
### Required import changes
Монолит: импорт воркеров; места создания/запуска (фактические после Batch #3c: GlossaryExtractionWorker 19152/19159, ProofreadWorker 48517/48601, TMSearchWorker 63579/63594) и замыкания-обработчики остаются в монолите на этом шаге.
### Circular dependency risks
Нет. (PreTranslationWorker НЕ переносится — см. Step 13.)
### Risk
LOW.
### Validation
TM-поиск из SuperLookup/грида; proofread-прогон; извлечение терминов из termbase-вкладки.
### Rollback
revert.
### Expected result
−400 строк; воркеры тестопригодны изолированно.

## Step 5 — Undo-менеджер

### Goal
Вынести undo/redo-подсистему.
### Source
`Supervertaler.py` 12493–13066 + 12851–12886 (`record_undo_state`, `record_undo_states_batch`, `undo/redo_action_handler`, `_apply_undo_redo_action`, `_push_structural_undo`, `_apply_structural_history`, `update_undo_redo_actions`).
### Destination
`modules/undo_manager.py` (класс `UndoManager` с обратными вызовами или прямой доступ к полям через инжекцию).
### Objects to move
7 методов + состояние `undo_stack`, `redo_stack`, `max_undo_levels`.
### Existing module to reuse
—
### New module if required
`modules/undo_manager.py`.
### Dependencies
Читает `current_project`, `table` (через callbacks: `update_window_title`, `update_progress_stats`, `_update_status_cell`, `load_segments_to_grid`). Интерфейс: передать колбэки явно.
### Required import changes
Методы-обёртки в SupervertalerQt оставить как делегаты (переходный период) или заменить все call-sites (23+ места).
### Circular dependency risks
Нет (callbacks вниз).
### Risk
LOW-MEDIUM.
### Validation
Ctrl+Z/Ctrl+Y на текстовых правках; undo после split/merge/delete; структурный undo.
### Rollback
revert.
### Expected result
−250 строк; тестопригодный undo.

#### Статус Step 5 после Batch #5 Stage 1 (2026-09-15) — инвентаризация завершена, перенос не начат
Режим Stage 1 — read-only: код не менялся. Отчёт — `docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 1.txt`; снимок 14 NOT MOVE методов со SHA256 — `docs/refactoring/audits/not_moved_methods_batch5_snapshot.txt`.
Диапазоны из блока Step 5 выше (12493–13066 + 12851–12886) устарели: фактические AST-границы окна — **9373–9989** (смещение −3120 из-за Batch #4). Заявленные «7 методов» — дефект текста плана: `update_undo_redo_actions` пропущен в строке Source. **Подтверждено 8 методов:** `record_undo_state` 9373–9401, `record_undo_states_batch` 9403–9447, `undo_action_handler` 9449–9463, `redo_action_handler` 9465–9478, `_apply_undo_redo_action` 9480–9515, `_push_structural_undo` 9731–9746, `_apply_structural_history` 9888–9939, `update_undo_redo_actions` 9941–9944. Состояние `undo_stack`/`redo_stack`/`max_undo_levels` — `__init__` 6212–6214, в `.svproj` не сериализуется. `_sync_after_structural` (9748–9764) остаётся в монолите (нулевая связность с undo-состоянием). Call sites: 43 (план ожидал 23+), из них 28 self.-стиль из методов, остающихся в монолите, 11 MOVE→MOVE, 4 внешних duck-typed (`EditableGridTextEditor.keyPressEvent` 4214–4226, `EditableGridTextEditor._copy_source_to_target` 4722–4724, `modules/pseudo_translate_dialog.py:264`). Рекомендация: 8 тонких делегатов-обёрток с сохранением имён + состояние в `modules/undo_manager.py`; полная замена call sites отклонена. Stage 2 (перенос) не начинать до решения владельца по вопросам В1–В4 отчёта.


## Step 6 — Grid: helpers/pagination/filters

### Goal
Вынести чистую логику пагинации и фильтров.
### Source
`Supervertaler.py` 31574–32100 (пагинация), 32150–32188+55494–57100 (фильтры/невидимые), хелперы (`_widget_is_alive`, `_segment_for_grid_row`, `_find_row_for_segment`, `_find_row_for_segment_id`, `_select_grid_row_by_id`, `_recompute_list_numbers`, `_reindex_grid_rows_from`, `_get_line_edit_text`).
### Destination
`modules/grid/helpers.py`, `modules/grid/pagination.py`, `modules/grid/filters.py`.
### Objects to move
~45 методов (список — CODE_MAP §16).
### Existing module to reuse
—
### New module if required
Пакет `modules/grid/`.
### Dependencies
Работают над `self.table`, `self.current_project`, `load_segments_to_grid`. Передавать table/project параметрами; вызывающие делегаты оставить в классе.
### Required import changes
Импорт модулей в монолите; сигнатуры не менять (методы-обёртки).
### Circular dependency risks
Пагинация ↔ populate (SCC#1) — на этом шаге НЕ трогать populate/render; helpers получают всё параметрами, цикл не переносится.
### Risk
MEDIUM.
### Validation
Пагинация (все кнопки/Go To), фильтры (быстрый/продвинутый/файловый/сортировка), невидимые символы, авто-размер страниц.
### Rollback
revert.
### Expected result
−2 500 строк.
#### Статус Step 6 после Batch #6 Stage 4 (2026-09-18) — Step 6 ЗАВЕРШЁН ЦЕЛИКОМ
Step 6 выполнялся тремя под-батчами (решение владельца по Stage 1 Batch #6;
архитектура — модули ЧИСТЫХ ФУНКЦИЙ с явными параметрами и именованными
колбэками, НЕ классы-контейнеры):
- Стадия 2 (коммит `4ace504`) — `modules/grid/helpers.py`, 507 строк: 16 функций
  + 17 тонких делегатов в монолите; `_get_line_edit_text` оставлен в монолите
  целиком (self-специфичная getattr-логика).
- Стадия 3 (коммит `26b998c`) — `modules/grid/pagination.py`, 584 строки:
  14 функций + 14 делегатов + 2 module-level константы `PAGE_AUTO_ALL_THRESHOLD`
  / `PAGE_FALLBACK_SIZE` (перенесены с класса); populate-кластер
  (`_start_background_populate`/`_background_populate_step` и его константы)
  намеренно НЕ тронут — Step 8.
- Стадия 4 (этот коммит) — `modules/grid/filters.py`, 1277 строк: 20 функций
  + 1 внутренняя `_refresh_grid_invisibles_cells` + 20 делегатов.
- `modules/grid/__init__.py`: 134 строки, `__all__` = 55 имён (3 модуля +
  16 helpers + 16 pagination + 20 filters).

Фактические номера: документированные в блоке выше диапазоны (31574–32100,
32150–32188 + 55494–57100) устарели сильнее, чем на один батч — сдвиг от
стартового состояния монолита уже −4951. На HEAD Stage 4 (68 386 строк)
окно кластера — 51794–55821, состав 20 методов = 1097 строк; окно содержит
посторонние блоки, которые НЕ переносились: `show_manage_views_dialog`
(52202–52369, открытый вопрос Stage 1 §8 п.3), `_refresh_source_column_display`
(52555–52568, Step 8/теги), `_update_bulk_menu_label` (53247–53273, подпись меню
Bulk Operations), spellcheck/словари (52645–53126), комментарии сегментов +
voice dictation (53510–55753). Метод `_ensure_shared_filter`/
`_ensure_primary_filters_ready` физически лежит отдельно (28544/28559 на HEAD).

Валидация Stage 4: AST 22/22 байт-в-байт; 8 метрик ровные
(1211/18/35/24/24/0/85/2); манифест — только монолит + `__init__.py` + новый
`filters.py`; 3 NOT-MOVE блока BYTE-IDENTICAL (sha256 + containment 1/1);
контрольные блоки spellcheck 9ac157cd… / comments/dictation 6496a472… — по
1 вхождению; функциональные сценарии 65/65 PASS (в т.ч. F11 — apply_sort через
reload_callback, единственное пересечение с SCC#1); Undo/Redo Batch #5 — 38/38
PASS (третий прогон); smoke save/load OK. Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 4.txt`; сигнатуры:
`docs/refactoring/audits/batch6_stage4_signatures.txt`.

Незакрытые вопросы Step 6, перенесённые дальше:
- `show_manage_views_dialog` — остался в монолите (открытый вопрос Stage 1 §8
  п.3 не решён; логичное место — Step 8 «Grid: render + match panel + comments
  UI» или отдельный мини-батч «диалоги представлений»).
- Предсуществующий бесконечный цикл в `clear_filter_highlights_in_widget` при
  наложении и снятии подсветки в ОДНОМ диапазоне (воспроизведён и на HEAD —
  НЕ регрессия Stage 4). Требует отдельного решения владельца.
- `filter_empty_segments` — мёртвый код (0 call sites), перенесён как есть.

## Step 7 — Settings service (IO-слой)

### Goal
Единая точка персистентности настроек.
### Source
`Supervertaler.py` 48308–48750 + 29585–30500 (IO-часть: `_get_settings_dir`, `_get_unified_settings_path`, `_load/_save_unified_settings`, `_load/_save_settings_section`, `load/save_general_settings`, `load/save_llm_settings`, `load/save_proxy_settings`, `load/save_api_keys`, provider states, языки, диктовка, словарь команд, спеллчек, недавние проекты).
ВНИМАНИЕ: эти номера устарели (Batch #1–#6 сдвинули монолит на −4951; сейчас 68 386 строк). Предварительная AST-карта кандидатов IO после Batch #6 Stage 4 (46 методов IO, ~1709 строк; UI-билдеры вкладок исключены) — в `PROJECT_STATUS.md`, раздел «Что дальше». Точный состав и границы пересчитать AST на старте Step 7.
### Destination
`modules/settings_service.py` (расширение логики `modules/config_manager.py`).
### Objects to move
~25 методов IO (БЕЗ UI-билдеров вкладок!).
### Existing module to reuse
`modules/config_manager.py` (user_data paths, singleton).
### New module if required
— (расширить config_manager или новый settings_service, использующий его).
### Dependencies
Миграции `_migrate_settings_to_unified`, `_migrate_to_workbench_layout` (одноразовые, оставить в service). СЕМАНТИКА: `load_general_settings` перечитывает файл с диска (48 call-sites) — сохранить.
### Required import changes
Делегирующие методы в классе остаются (call-sites не менять) — переходный период.
### Circular dependency risks
Нет.
### Risk
MEDIUM (fan-in до 48).
### Validation
Полный цикл настроек: изменить каждую вкладку → перезапуск → проверить; миграция на копии старых настроек; backup-интервал.
### Rollback
revert.
### Expected result
−1 200 строк; один владелец формата settings.
#### Статус Step 7 после Batch #7 Stage 1 (2026-09-24) — инвентаризация завершена, перенос не начат
Режим Stage 1 — read-only: код не менялся. Отчёт — `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 1.txt`; разбор по подзадачам 1.1–1.9 — `docs/refactoring/audits/step7_stage1_findings.md`; измерения — `docs/refactoring/audits/batch7_stage1_*.txt` (AST 819 методов класса, 205 кандидатов, карта 394 ссылок, deps, сверка с `DEAD_CODE_REPORT.md`, дубликаты `settings.json`).
Номера из блока выше (`48308–48750` + `29585–30500`, «~25 методов») устарели и неверны по форме: состав разбросан не по двум окнам, а минимум по 9 кластерам в span **8481–61247** (≈52 800 строк). Подтверждённый состав — **35 методов / 830 строк**: ядро API 6 (`_get_settings_dir` 44639–44641, `_get_unified_settings_path` 44643–44645, `_load_unified_settings` 44647–44661, `_save_unified_settings` 44663–44672, `_load_settings_section` 44674–44676, `_save_settings_section` 44678–44682) + 29 доменных аксессоров: `load_general_settings` 44522–44618, `_load_general_settings_from_file` 44883–44922, `save_general_settings` 44924–44929, `load/save_clipboard_privacy_settings` 44690–44699/44701–44722, `_migrate_settings_to_unified` **44724–44814**, `_migrate_to_workbench_layout` **44816–44881**, `_migrate_voice_dictation_default_off` 45143–45174 (в плане НЕ названа — третья миграция), `load/save_dictation_settings` 44931–44946/44948–45002, `_load_language_pair_from_disk` 45004–45021, `load/save_voice_vocabulary_settings` 45029–45067/45069–45092, `load/save_language_settings` 45228–45249/45251–45261, `_save/_load_spellcheck_settings` 52262–52271/52273–52280, `load/save_llm_settings` 56987–57025/57027–57034, `load/save_proxy_settings` 57040–57056/57058–57065, `_get_proxy_url`/`_get_proxy_dict` 57067–57089/57091–57098, `load/save_provider_enabled_states` 57283–57309/57311–57318, `load/save_api_keys` 61235–61243/61245–61247, `load/save_recent_projects` 32306–32368/32370–32380. Отдельно тир C (рекомендация — НЕ включать): `get_autocorrect_settings` 44620–44631 (пропущен грепом координатора), `add_to_recent_projects` 32238–32288, `_remove_from_recent_projects` 32290–32304, `clear_recent_projects` 32416–32430, `load_font_sizes_from_preferences` 45275–45361 (перенос даст `NameError` — ссылается на классы монолита).
Ключевые риски, зафиксированные фактами: fan-in `load_general_settings` — **61 call-сайт** (60 монолит: 56 `SupervertalerQt`, `PreTranslationWorker.run` 5479, `SuperlookupTab` 66766/66809, `main()` 68357; +1 `modules/quicktrans.py:303`) плюс 7 `getattr`-строковых обращений (в плане «до 48»); `load_general_settings` — НЕ чистый IO (2 строки чтения из 97, остальное 35 присваиваний `self.<attr>` + вызов `load_llm_settings`), поэтому его надо переносить SPLIT-ом; «чтение с диска при каждом вызове» подтверждено (кэшей нет, `lru_cache` отсутствует, единственный производный кэш `_row_color_settings_cached` вне состава). Дукт-тайпед-обращения из `modules/` есть к 6 именам, включая ПРИВАТНЫЕ (`_load_unified_settings`, `_save_unified_settings`, `_load_settings_section`, `_save_settings_section`, `_get_proxy_url`) → 35 тонких делегатов с исходными именами обязательны. `_migrate_settings_to_unified` использует `Path(__file__).parent/user_data_private` → при переносе repo-root передавать явно. ConfigManager: `get_preferences_path/load_preferences/save_preferences` дублируют тот же файл/секцию и имеют 0 call-sites, а его резолвер user_data — ДРУГОЙ указатель (`~/.supervertaler_config.json`), чем у монолита (`%APPDATA%/Supervertaler/config.json`) → сервис не должен сам резолвить путь. Рекомендация по архитектуре: класс `SettingsService` в `modules/settings_service.py` с явным `settings_dir` (+ опц. `log`), ConfigManager не расширять; решать владельцу (V1–V4 отчёта). Разбивка: S2.1 ядро API (6 методов/39 строк), S2.2 general + общий reading (5/175, fan-in 90), S2.3 LLM/proxy/provider/api keys (10/150 — ровно на границе конвенции), S2.4 языки/диктовка/словарь/спеллчек (9/203), S2.5 recent + миграции (5/263, валидация на копии user_data). Stage 2 не начинать до решения владельца по V1–V4.

#### Решения по V1–V4 (25.09.2026, координатор — по делегации владельца)
- **V1 Архитектура** — принято: новый класс `SettingsService` в `modules/settings_service.py`, конструируется явным `settings_dir` (+ опц. `log`); `ConfigManager` НЕ расширяется. Причина: его резолвер user_data (`~/.supervertaler_config.json`) — другой указатель, чем у монолита (`%APPDATA%/Supervertaler/config.json`); расширение тянет bootstrap-логику первого запуска и мёртвые дубликаты `load_preferences`/`save_preferences` для того же файла.
- **V2 Тир C** — принято: НЕ включать в Step 7. `add_to_recent_projects`, `_remove_from_recent_projects`, `clear_recent_projects`, `load_font_sizes_from_preferences`, `get_autocorrect_settings` ссылаются на классы/атрибуты монолита (`TagHighlighter`, `EditableGridTextEditor`, `ReadOnlyGridTextEditor`, `SupervertalerQt`, `_canon_path`, `self.current_project`) или на UI-оркестрацию — механический перенос даст `NameError`.
- **V3 SPLIT** — принято: обязательный SPLIT для `load_general_settings` (не чистый IO — 35 присваиваний `self.<attr>` + вызов `load_llm_settings` из 97 строк тела; самый высокий fan-in состава) и для `_migrate_voice_dictation_default_off` (DB-побочный эффект, третья миграция). Остальные три кандидата — `save_clipboard_privacy_settings` (живой refresh виджета), `save_dictation_settings` (QMessageBox с self-окном как parent), `load_language_settings` (TagHighlighter/spellcheck_manager) — НЕ переносятся в Step 7 вовсе и остаются целиком в монолите: усложнение SPLIT для этих трёх не оправдано их размером/значимостью.
  **Итоговый состав Stage 2 сокращён с 35 до 32 методов (6 A + 26 B) / ~731 строка** (830 − 22 − 55 − 22). Пересчёт под-батчей: **S2.2** «general + общий reading» — 4 метода (`_load_general_settings_from_file`, `save_general_settings`, `load_general_settings` [SPLIT], `load_clipboard_privacy_settings`; без `save_clipboard_privacy_settings`); **S2.4** «языки/диктовка/словарь/спеллчек-IO» — 7 методов (`load_dictation_settings`, `_load_language_pair_from_disk`, `load_voice_vocabulary_settings`, `save_voice_vocabulary_settings`, `save_language_settings`, `_save_spellcheck_settings`, `_load_spellcheck_settings`; без `save_dictation_settings`, `load_language_settings`). S2.1, S2.3, S2.5 — без изменений.
- **V4 Миграции** — принято: отдельный под-батч S2.5 с валидацией на КОПИИ старого `user_data` (миграции необратимо перемещают файлы пользователя).

**Stage 2 разблокирован к старту с S2.1.**

ОТКРЫТО (не блокирует S2.1, блокирует S2.2): раздел 1.4 отчёта Stage 1 характеризует все 7 duck-typed вызовов `load_general_settings` как `getattr(self, 'load_general_settings', lambda: {})()`. Независимый аудит (Б1) оспаривает это для `Supervertaler.py:1809` (`highlight_termbase_matches`) и `modules/quicktrans.py:302-303` — по его прочтению это `hasattr`-guard на `self.parent()`-цепочке / `self.parent_app`, а не `getattr(self, …)`. Не подтверждено ни одной третьей проверкой — нужна прямая цитата кода этих двух мест перед стартом S2.2.

ПРАВКА ИНВЕНТАРЯ (учесть в S2.1): в разделе 1.6 отчёта для `_save_unified_settings` пропущен call site `modules/voice_tab.py:1062` (`getattr` внутри `_set_dictation_keys`, соседняя строка с уже учтённой 1061 для `_load_unified_settings`). Fan-in `_save_unified_settings` = 12, не 11.

## Step 8 — Grid: render + match panel + comments UI

### Goal
Вынести рендер грида, панель матчей и комментарии.
### Source
`Supervertaler.py` 44258–44912 (populate/render), 44912–46060 (match panel), 57425–58500 (comments), 46887–47210 (status cells).
### Destination
`modules/grid/render.py`, `modules/grid/match_panel.py`, `modules/comments_ui.py`.
### Objects to move
~58 методов (см. CODE_MAP §16).
### Existing module to reuse
—
### New module if required
—
### Dependencies
САМЫЙ СЛОЖНЫЙ шаг: цикл SCC#1 (15 методов). Стратегия: выносить целиком ВСЕ участники цикла одновременно (populate/status/comments/navigate) в один пакет; внутрипакетные вызовы остаются прямыми; связи с MainWindow — через явный интерфейс (таблица+проект+колбэки).
### Required import changes
Множественные; сигнатуры сохранить.
### Circular dependency risks
SCC#1 — переносить атомарно; иначе разрыв поведения.
### Risk
MEDIUM-HIGH.
### Validation
Открытие проекта 500+ сегментов; скролл/центрирование; комментарии (добавить/править/меню/анкеры); панель матчей (навигация/edit/delete TM); статусы ячеек; undo после populate.
### Rollback
revert (атомарный шаг).
### Expected result
−5 500 строк.

## Step 9 — Мелкие изолированные фичи

### Goal
Быстрые победы: изолированные подсистемы.
### Source → Destination:
- `check_for_updates` + 5 хелперов (62196–62855) → `modules/update_checker.py`
- tray-методы (33060–33451) → `modules/tray_controller.py`
- okapi sidecar-методы (36261–36488, 63016–63153) → `modules/okapi_controller.py` (переиспользует `modules/okapi_sidecar.py`)
- images-вкладка (13747–14772) → `modules/images_tab.py` (переиспользует `modules/image_extractor.py`)
- статистика (13536–13746, 66032) → переиспользует `modules/statistics_dialog_qt.py`
- preview (46059–46885) → `modules/preview_controller.py`
- menus factory (`create_menus` 11602–12492) → `modules/menus_factory.py` (принимает callbacks-объект)
### Objects to move
~45 методов + builders.
### Existing module to reuse
okapi_sidecar, image_extractor, statistics_dialog_qt, pdf_rescue_Qt (окно).
### New module if required
update_checker, tray_controller, okapi_controller, images_tab, preview_controller, menus_factory.
### Dependencies
Все — низкая связность; menus_factory требует инжекции self (принять как параметр `mw`).
### Required import changes
Локальные.
### Circular dependency risks
Нет.
### Risk
MEDIUM.
### Validation
Каждое меню пункта; tray; проверка обновлений; sidecar; извлечение картинок; предпросмотр.
### Rollback
revert пофично.
### Expected result
−4 500 строк.

## Step 10 — Find&Replace + поиск

### Goal
Вынести движок поиска/замены.
### Source
`Supervertaler.py` 53373–54618 (17 методов).
### Destination
`modules/find_replace_controller.py` (переиспользует данные `modules/find_replace_qt.py`).
### Objects to move
`show_find_replace_dialog`, `_fr_*` ×9, `find_next_match`, `find_all_matches(+internal)`, `text_matches`, `replace_current_match`, `replace_all_matches`, `highlight_*`, `_apply_case_pattern`, `_fr_compile_regex`.
### Existing module to reuse
`modules/find_replace_qt.py` (модели FindReplaceSet/History).
### New module if required
—
### Dependencies
Подсветка работает с `self.table` и делегатами; сохранить сигнатуры.
### Required import changes
Делегаты-методы на переходный период.
### Circular dependency risks
Нет.
### Risk
MEDIUM.
### Validation
F&R: plain/regex/case/наборы/batch/demote-to-draft; подсветка/снятие; замена в source/target.
### Rollback
revert.
### Expected result
−1 300 строк.

## Step 11 — Импорт/Экспорт контроллеры

### Goal
Вынести I/O форматов (пошагово, формат-за-форматом).
### Source
IMPORT: 16056(chain-dead отдельно), 36078–41660 (~25 методов); EXPORT: 16299–18523, 36206–39046, 39690–44113 (~25 методов).
### Destination
`modules/import_controller.py`, `modules/export_controller.py` (или по формату: `modules/io/docx_io.py`, `io/memoq_io.py`…).
### Objects to move
Методы импорта/экспорта; хендлеры форматов (`modules/*_handler.py`) НЕ трогаются — контроллеры их вызывают.
### Existing module to reuse
Все 10 `*_handler.py`, `okapi_sidecar`, `simple_segmenter`, `bilingual_markdown_handler`, `docx_comments`, `statuses`.
### New module if required
—
### Dependencies
`_sync_grid_targets_to_segments`, `_finalise_import_with_indexes`, воркеры индексации — перенести ВМЕСТЕ с termbase/TM-сервисами (Step 12) или временно оставить в MainWindow с вызовом через интерфейс.
### Required import changes
Меню (create_menus) вызывает через self — делегаты.
### Circular dependency risks
Экспорт ↔ грид (`_sync_grid_targets_to_segments`) — интерфейс.
### Risk
HIGH (объём), но каждый формат независим — переносить по одному.
### Validation
Импорт и экспорт КАЖДОГО формата на эталонных файлах; побайтовое сравнение экспорта до/после (кроме timestamp-полей).
### Rollback
revert по одному формату.
### Expected result
−6 000 строк.

## Step 12 — TM / Termbase сервисы

### Goal
Доменные сервисы терминологии и памяти.
### Source
TM: 14867–16232 (живые), 22908–23854, 35271–35420, 52294–52790; Termbase: 18881–20290, 34141–35270, 52833–53264, 20290–22570 (вкладка отдельно).
### Destination
`modules/tm_service.py`, `modules/termbase_service.py`, `modules/termbase_tab.py`.
### Objects to move
~45 методов + threading-воркеры (`_termbase_batch_worker_run`, `_prefetch_worker_run`, `_fetch_all_matches_for_segment`).
### Existing module to reuse
`database_manager`, `termbase_manager`, `termbase_entry_editor`, `termbase_import_export`, `tm_manager_qt`, `tm_metadata_manager`, `translation_memory`, `tmx_generator`, `sdltm_handler`.
### New module if required
—
### Dependencies
Кэши (`termbase_index`, `translation_matches_cache` + локи), `db_manager`; связь с гридом (подсветка) — через колбэки.
### Required import changes
`db_manager` инициализация остаётся в MainWindow; сервис получает его в конструктор.
### Circular dependency risks
Termbase service ↔ TermLens ↔ grid (подсветка) — колбэк-интерфейс; threading-воркеры переносятся вместе с кэшами.
### Risk
HIGH.
### Validation
Полный цикл TM (создать/импортировать TMX/подключить SDLTM/сохранение сегмента/синк); termbase (создать/добавить терм/поиск/quick-add хоткеями/импорт-экспорт/извлечение LLM).
### Rollback
revert.
### Expected result
−5 500 строк.

## Step 13 — Перевод-ядро (ПОСЛЕДНИЙ из крупных)

### Goal
Вынести LLM/MT-диспетчер и перевод.
### Source
`call_*` провайдеры (65529–65870), профили/proxy (61610–61940), `translate_current_segment` (63154), `translate_batch` (64442, 833L!), autotag, quicklauncher, fuzzy-fix, instant/MT/LLM-matches (66139–67098).
### Destination
`modules/mt_providers.py` (провайдеры — первыми, они почти чистые), затем `modules/translation_service.py` (диспетчер), `translate_*` остаются в MainWindow до полной стабилизации интерфейса.
### Objects to move
Этап A: `call_google/deepl/microsoft/amazon/modernmt/mymemory`, `call_custom_mt`, proxy-хелперы. Этап B: `_resolve_provider_model`, `create_llm_client`, профили. Этап C: матч-конвейер (`_show_instant_tm_match`, `_schedule/_execute/_search_mt_and_llm_matches`, `_on_tm_search_results`).
### Existing module to reuse
`llm_clients`, `translation_services` (orphan — оживить вместо дублирования!), `llm_pricing`.
### New module if required
`modules/mt_providers.py`.
### Dependencies
`translate_batch` держит замыкания с retry-логикой и UI-прогрессом — этап D (отдельное проектирование, возможно никогда не переносить полностью).
### Required import changes
Duck-typed вызовы ИЗ SuperLookupTab (`call_deepl`, `call_google_translate`) и voice_commands должны сохраниться: делегаты в MainWindow обязательны.
### Circular dependency risks
translation_service ↔ tm_service (кэши матчей) — направленный интерфейс.
### Risk
VERY_HIGH (этапы C/D), MEDIUM (этапы A/B).
### Validation
Перевод сегмента каждым провайдером; batch (маленький документ); retry-сценарий (невалидный ключ); fuzzy fix; autotag; quicklauncher; SuperLookup MT-lookup (Duck-typed!); cost/usage-лог.
### Rollback
revert по этапам.
### Expected result
−3 500 строк; провайдеры тестопригодны.

## Step 14 — SuperLookup + Voice + финальный cleanup

### Goal
Перенос оставшихся крупных подсистем и чистка MainWindow.
### Source → Destination:
- `SuperlookupTab` + `_ReadOnlyHtmlCell`, `_SuperLookupSearchWorker(+Signals)`, `_SearchTermHighlighter`, `_NumericTableWidgetItem`, hotkey-подсистема (67312–72548) → `modules/superlookup/` (расширение существующего пакета; hotkeys → `modules/superlookup/hotkeys.py`)
- Voice-методы MainWindow (~30, 28048–29700, 58496–59480) → `modules/voice_controller.py`
- Settings UI-билдеры (~30 методов, 824–1046L каждый) → `modules/settings_tabs/` — ОПЦИОНАЛЬНО (можно оставить: они «UI-код» по определению)
- Финал: удалить подтверждённый dead (Step 0), убрать затенённые дубли, обновить докстринги-ссылки, `create_main_layout`/`__init__` остались.
### Existing module to reuse
`modules/superlookup.py` (engine), `modules/voice_tab.py`, `voice_commands`, `voice_dictation_lite`.
### New module if required
`modules/superlookup/tab.py`, `hotkeys.py`.
### Dependencies
SuperLookup-контракт MainWindow (~25 атрибутов) → оформить `SuperLookupHost` Protocol; voice — аналогично.
### Required import changes
Точечные.
### Circular dependency risks
SuperLookup ↔ MainWindow — только через Protocol.
### Risk
MEDIUM-HIGH.
### Validation
SuperLookup: hotkeys Ctrl+Alt+L/Q, clipboard-capture, поиск по всем источникам, настройки, detach-пути; голосовые сценарии; ПОЛНЫЙ smoke из §Общая валидация.
### Rollback
revert.
### Expected result
`Supervertaler.py` ~12–15k строк: bootstrap + SupervertalerQt (окно/вкладки/маршрутизация/делегаты-переходники) + main().

---

## Сводка ожиданий

| Шаг | − строк (≈) | Риск |
|---|---|---|
| 1 Модели | 630 | LOW |
| 2 Tag-движок | 1 300 | LOW |
| 3 Фильтры+диалоги+чекбоксы | 1 900 | LOW |
| 4 Воркеры | 400 | LOW |
| 5 Undo | 250 | LOW-MED |
| 6 Грид: helpers/pagination/filters | 2 500 | MED |
| 7 Settings service | 1 200 | MED |
| 8 Грид: render/panel/comments | 5 500 | MED-HIGH |
| 9 Мелкие фичи | 4 500 | MED |
| 10 Find&Replace | 1 300 | MED |
| 11 Импорт/Экспорт | 6 000 | HIGH |
| 12 TM/Termbase | 5 500 | HIGH |
| 13 Перевод-ядро | 3 500 | VERY_HIGH (A/B — MED) |
| 14 SuperLookup/Voice/cleanup | 8 000 | MED-HIGH |
| Итого | ~43 000 | класс → ~12–15k строк |

## Критические «не делай»
1. Не переносить `PreTranslationWorker` до декомпозиции `parent_app`-зависимостей.
2. Не разрывать SCC#1 (грид↔комментарии) переносом части участников.
3. Не переименовывать 219 методов из списка DYNAMIC_ENTRY_POINT (DEAD_CODE_REPORT.md).
4. Не создавать `modules/utils.py`/`misc.py`; хелперы — в подсистемы.
5. Не удалять orphan-модули до подтверждения владельцем (внешние сценарии не исключены).
6. Не менять семантику `load_general_settings` (перечитывание файла) при выносе settings.

## TECH-DEBT: несовместимые грамматики тегов (находка Batch #2, 2026-09-12)

После переноса tag-движка в `modules/tag_manager.py` (Batch #2) в модуле
намеренно сосуществуют ДВЕ несовместимые реализации с разными грамматиками
тегов. Унификация — ОТДЕЛЬНОЕ решение владельца, не механический рефакторинг
(любое слияние меняет поведение приложения).

| Пара (монолит → modules/tag_manager.py) | Расхождение (проверено на тестовых входах) |
|---|---|
| `runs_to_tagged_text` ↔ `TagManager.runs_to_tagged_text` | Разные входы (python-docx Paragraph'ы vs `List[FormattingRun]`). bold+italic: монолит → `x <b><i>bi</i></b>`, TagManager → `x <bi>bi</bi>`. Пустой форматированный run: монолит пропускает, TagManager даёт `<b></b>after`. |
| `tagged_text_to_runs` ↔ `TagManager.tagged_text_to_runs` | Одинаковая сигнатура. `<bi>combined</bi>`: монолит возвращает литерал `'<bi>combined</bi>'` (bold=False), TagManager — `combined` (bold=True, italic=True). `<li>…</li>`: монолит оставляет теги литералом, TagManager снимает. На текстах только с `<b>/<i>/<u>/<sub>/<sup>` (9 тестов, вкл. несбалансированные/пересекающиеся) — идентичны. |
| `strip_formatting_tags` ↔ `TagManager.strip_tags` | Идентичны на `<b>/<i>/<u>/<sub>/<sup>`; расходятся на `<bi>`/`<li>` (TagManager снимает, монолит оставляет). |

Оба набора вызовов живые: TagManager-методы использует `docx_handler`
(`self.tag_manager.*`), функции из монолит-блока — сам монолит. НЕ объединять
и не переключать callsites между блоками.

Дополнительно: `get_docx_language_code` монолита и `modules/docx_handler.py`
поведенчески РАЗНЫЕ (монолит распознаёт больше языков: `english (uk)` →
`en-GB` vs `en-US`; `flemish` → `nl-BE` vs `en-US`; `brazilian portuguese` →
`pt-BR` vs `en-US`; `sr` → `sr-RS` vs `en-US`; `qq` → `qq-QQ` vs `en-US` —
5 из 17 тестовых входов). `set_docx_language` — идентичны на реальном
Document. Унификация направления `docx_handler ← tag_manager` (см. Step 2,
dependencies) должна учесть это расхождение — слепое переключение docx_handler
на монолит-версию изменит поведение экспорта.
