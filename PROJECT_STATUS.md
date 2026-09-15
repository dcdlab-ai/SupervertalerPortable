# PROJECT_STATUS.md

**Точка входа для актуального состояния проекта.** Обновляется в конце каждого шага/батча —
читать этот файл вместо повторного просмотра всех документов. Подробности каждого шага — в
`EXTRACTION_PLAN.md` (секции «Статус Step N после Batch #X») и `docs/refactoring/`.

**Обновлено:** 2026-09-15 (Batch #5 Stage 1) • **Текущий шаг:** Step 5 — Stage 1 (инвентаризация) выполнен, Stage 2 (перенос) ждёт подтверждения архитектуры владельцем

## Кратко: где мы находимся

Инкрементальная декомпозиция монолита `Supervertaler.py` (73 337 строк на старте;
сейчас **69 862**) в пакеты `modules/` по плану `EXTRACTION_PLAN.md` (Step 0–14).
Выполнены **Step 1–4** (батчи #1, #2, #3a, #3b, #3c, #4). Следующий — **Step 5:
Undo-менеджер**. Среда, тестирование и валидация — по `AGENTS.md` (обязательно к
прочтению перед любой работой).

## Прогресс по шагам EXTRACTION_PLAN.md

| Step | Что | Статус | Батч / артефакты |
|---|---|---|---|
| 0 | Dead-инвентарь, базовая линия | ✅ выполнен (база до Batch #1) | `DEAD_CODE_REPORT.md`; решения по удалению — в backlog |
| 1 | Модели данных → `modules/models.py` | ✅ выполнен | Batch #1, коммит `969c9fe`; отчёт `docs/refactoring/reports/ОТЧЁТ Batch #1.txt` |
| 2 | DOCX tag-движок → `modules/tag_manager.py` | ✅ выполнен | Batch #2, коммит `1ac400d`; см. TECH-DEBT в конце `EXTRACTION_PLAN.md` |
| 3 | Event-фильтры + диалоги + чекбоксы | ✅ выполнен | Batch #3a `c7497d6` (`modules/event_filters.py`), #3b `4895e72` (`modules/dialogs/`), #3c `e543787` (`modules/styled_widgets.py`) |
| 4 | Чистые QThread-воркеры | ✅ выполнен | Batch #4 (этот коммит; `modules/workers/`); отчёт `docs/refactoring/reports/ОТЧЁТ Batch #4.txt` |
| 5 | Undo-менеджер | 🟨 Stage 1 (инвентаризация) выполнен; Stage 2 — после GO владельца | `docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 1.txt`; снимок в `audits/` |
| 6 | Grid: helpers/pagination/filters | ⬜ не начат | — |
| 7 | Settings service (IO-слой) | ⬜ не начат | — |
| 8 | Grid: render + match panel + comments UI | ⬜ не начат | — |
| 9 | Мелкие изолированные фичи | ⬜ не начат | — |
| 10 | Find&Replace + поиск | ⬜ не начат | — |
| 11 | Импорт/Экспорт контроллеры | ⬜ не начат | — |
| 12 | TM / Termbase сервисы | ⬜ не начат | — |
| 13 | Перевод-ядро (вкл. PreTranslationWorker) | ⬜ не начат | — |
| 14 | SuperLookup + Voice + финальный cleanup | ⬜ не начат | — |

## Что дальше: Step 5 — Undo-менеджер

Batch #5 разделён на два этапа-промпта. **Stage 1 выполнен** (15.09.2026):
инвентаризация + рекомендация по архитектуре — отчёт
`docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 1.txt`,
снимки `docs/refactoring/audits/not_moved_methods_batch5_snapshot.txt`.
Код не менялся. **Stage 2 (сам перенос) запускать только после подтверждения
владельцем архитектуры** (4 открытых вопроса В1–В4 в отчёте Stage 1).

Ключевые факты Stage 1 (все — из AST, не из документов):
- Подтверждён состав **8 методов** (не 7, как в `EXTRACTION_PLAN.md` §Step 5):
  `record_undo_state`, `record_undo_states_batch`, `undo_action_handler`,
  `redo_action_handler`, `_apply_undo_redo_action`, `_push_structural_undo`,
  `_apply_structural_history`, `update_undo_redo_actions`.
- Фактические AST-границы внутри `SupervertalerQt` (в рабочем дереве, HEAD 435b0c4):
  `record_undo_state` 9373–9401, `record_undo_states_batch` 9403–9447,
  `undo_action_handler` 9449–9463, `redo_action_handler` 9465–9478,
  `_apply_undo_redo_action` 9480–9515, `_push_structural_undo` 9731–9746,
  `_apply_structural_history` 9888–9939, `update_undo_redo_actions` 9941–9944.
  Состояние `undo_stack`/`redo_stack`/`max_undo_levels` инициализируется в
  `__init__` на 6212–6214; в `.svproj` НЕ сериализуется.
- Прочие 14 методов окна 9373–9989 — NOT MOVE (снимок со SHA256 в audits/).
  Пограничный `_sync_after_structural` (9748–9764) остаётся в монолите.
- 43 call sites (план ожидал 23+): 28 self.-стиль из методов, остающихся в
  монолите; 11 MOVE→MOVE; 4 внешних duck-typed (`EditableGridTextEditor`,
  `modules/pseudo_translate_dialog.py:264`).
- Рекомендация: 8 тонких делегатов-обёрток с теми же именами + состояние в
  `modules/undo_manager.py`; полная замена call sites отклонена (не решает
  hasattr/connect-входы, расширяет скоуп).

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
