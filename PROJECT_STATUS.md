# PROJECT_STATUS.md

**Точка входа для актуального состояния проекта.** Обновляется в конце каждого шага/батча —
читать этот файл вместо повторного просмотра всех документов. Подробности каждого шага — в
`EXTRACTION_PLAN.md` (секции «Статус Step N после Batch #X») и `docs/refactoring/`.

**Обновлено:** 2026-10-09 (Batch #8.8 — первый запуск без визарда, legacy-миграции удалены) • **Текущий шаг:** серия Batch #8 (удаление функциональности): 8.1–8.5 ✓, 8.7 ✓, 8.10 ✓, **8.8 ✓** (коммит `ede28068`: удалены SetupWizard/first-run гейты/миграции, `modules/setup_wizard.py` удалён); монолит **61 743** строки; дальше — Batch #8.9 (CLI `--batch/--translate-sdlxliff`), затем микро-батч «Trados-чип», финальный инвентарь сирот + docs-проход.

**Batch #7 (историч.):** Step 7 завершён: Stage 1 (read-only) + Stage 2 в пяти под-батчах (S2.1 «ядро API», S2.2 «general + clipboard reading», S2.3 «LLM/proxy/provider/api keys», S2.4 «языковая пара + spellcheck-IO», S2.5 «recent projects») — `modules/settings_service.py` 565 строк / 26 методов + 25 тонких делегатов; монолит на тот момент **68 224** строки

## Кратко: где мы находимся

Инкрементальная декомпозиция монолита `Supervertaler.py` (73 337 строк на старте;
сейчас **61 743**) в пакеты `modules/` по плану `EXTRACTION_PLAN.md` (Step 0–14).
Выполнены **Step 1–5** (батчи #1, #2, #3a, #3b, #3c, #4, #5) и **Step 6 целиком**
(Batch #6: Stage 1 — инвентаризация, Stage 2 — `modules/grid/helpers.py`,
Stage 3 — `modules/grid/pagination.py`, Stage 4 — `modules/grid/filters.py`).
По **Step 7** выполнен **Stage 1 (Batch #7, read-only инвентаризация, 24.09.2026)**,
решения по V1–V4 приняты, и **Stage 2 закрыт целиком** (S2.1–S2.5): под-батч
**S2.1 «ядро API»** (25.09.2026) перенёс 6 методов / 39 строк в новый
`modules/settings_service.py`,
под-батч **S2.2 «general + clipboard reading»** (26.09.2026) добавил туда ещё
3 метода / 56 строк (`load_clipboard_privacy_settings`,
`_load_general_settings_from_file`, `save_general_settings`) и оставил в монолите
3 тонких делегата с исходными сигнатурами; монолит 68 400 → **68 373** строки,
8 метрик без изменений, живой offscreen-прогон приложения — 9/9 PASS; под-батч
**S2.3 «LLM/proxy/provider/api keys»** (27.09.2026) перенёс ещё 10 методов / 150
строк (`load_llm_settings`, `save_llm_settings`, `load_proxy_settings`,
`save_proxy_settings`, `_get_proxy_url`, `_get_proxy_dict`,
`load_provider_enabled_states`, `save_provider_enabled_states`, `load_api_keys`,
`save_api_keys`) и оставил в монолите 10 тонких делегатов с исходными сигнатурами
(включая приватные `_get_proxy_url`/`_get_proxy_dict`); монолит 68 373 → **68 285**
строк (−88), 8 метрик без изменений, живой offscreen-прогон — 14/14 PASS (в т.ч.
прямой тест 5 НЕЗАЩИЩЁННЫХ вызовов `PreTranslationWorker`). Под-батч
**S2.4 «языковая пара + spellcheck-IO»** (27.09.2026) перенёс ещё 4 метода / 47
строк (`_load_language_pair_from_disk`, `save_language_settings`,
`_save_spellcheck_settings`, `_load_spellcheck_settings`) и оставил 4 тонких
делегата; это ПЕРВЫЙ под-батч Stage 2, где сработало стоп-условие «зависимость от
состояния окна»: 2 тела чистые (ВЕРБАТИМ), а 2 перенесены SPLIT-ом (запись
`self.source_language`/`target_language` и чтение `self.spellcheck_enabled`
остались в делегатах, сервис принимает/возвращает значения); монолит 68 285 →
**68 274** строки (−11), 8 метрик без изменений, живой offscreen-прогон — 11/11 PASS
плюс отдельный процесс-перезапуск 4/4 PASS. Под-батч **S2.5 «recent projects»**
(28.09.2026) — ПОСЛЕДНИЙ в Stage 2 — перенёс ещё 2 метода / 74 строки
(`load_recent_projects`, `save_recent_projects`) и оставил 2 тонких делегата; это
первый под-батч, где перенесённые тела работают НЕ через `settings.json`, поэтому
применён вариант **SPLIT-BY-ARGUMENT**: делегат читает `self.recent_projects_file`
(и `self.user_data_path`) при КАЖДОМ вызове и передаёт их аргументами, сервис пути
не хранит, конструктор сервиса не менялся; монолит 68 274 → **68 224** строки
(−50), 8 метрик без изменений, живой offscreen-прогон — 16/16 PASS +
процесс-перезапуск 6/6 PASS + клик по реальным пунктам меню 3/3 PASS, кросс-дерево
(work против worktree предыдущего коммита) — 0 неожиданных расхождений. **Step 7
закрыт целиком: 25 методов / ~366 строк перенесены (S2.1 6, S2.2 3, S2.3 10,
S2.4 4, S2.5 2), голосовые методы, три миграции, `load_general_settings`,
V3-исключения и тир C `recent_projects` (add/remove/display/clear) сознательно
остались в монолите** — основания в итоговом блоке Step 7 `EXTRACTION_PLAN.md` и
§5 отчёта S2.5.
Дальше — **Step 8** (Grid: render + match panel + comments UI); Step 7 закрыт полностью.

**Синхронизация с апстримом (серия U1, 01–02.10.2026): база апстрима обновлена
частично до v1.10.372** — под-батчи U1.1/U1.2 (данные, цены, настройки,
`a7746d65`/`f5c460e9`), U1.3a/U1.3b (фиксы TM/TMX/F&R, `a1f76985`/`2e258269`),
U1.4a/U1.4b (сегментация без потерь + правила + страница настроек,
`5c052c9d`/`426a09e2`); класс D (QA-фичи, Inline Codes, тёмная тема,
settings autosave, вставка исходника) и файлы `CHANGELOG.md`/`FAQ.md` апстрима —
не перенесены; перенесено частично: `segment_split_merge.py` = 763291e8 без
34a4c661. Манифест и детали — `docs/refactoring/reports/UPSTREAM_SYNC_MANIFEST.md`.
Среда, тестирование и валидация — по `AGENTS.md` (обязательно к
прочтению перед любой работой).

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
| 7 | Settings service (IO-слой) | ✅ выполнен (Stage 2 закрыт целиком) | Batch #7 Stage 1 (read-only) + Stage 2 S2.1/S2.2/S2.3/S2.4/S2.5: 25 методов / ~366 строк в `modules/settings_service.py` (565 строк, 26 методов) + 25 делегатов; отчёты `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 1.txt`, `…Stage 2 (S2.1…S2.5).txt`; findings `docs/refactoring/audits/step7_stage1_findings.md`; аудиты `docs/refactoring/audits/batch7_stage1_*.txt`, `batch7s2{1,2,3,4,5}_*.txt` |
| 8 | Grid: render + match panel + comments UI | ⬜ не начат | — |
| 9 | Мелкие изолированные фичи | ⬜ не начат | — |
| 10 | Find&Replace + поиск | ⬜ не начат | — |
| 11 | Импорт/Экспорт контроллеры | ⬜ не начат | — |
## Что дальше: Step 7 Stage 2 — под-батч S2.5 закрыт, STEP 7 ЗАКРЫТ ЦЕЛИКОМ (28.09.2026)

**S2.5 выполнен** (база HEAD `d4db217` — потомок базы разведки `1ef3c708`, дрейфа
нет; монолит 68 274 → **68 224** строки, −50; difflib — ровно 2 неравных региона
−52/+2, сумма −50 == изменению файла). Перенесены 2 метода / 74 строки в
`modules/settings_service.py` (451 → 565 строк; методов 24 → 26) —
`load_recent_projects` (сервис 490–552), `save_recent_projects` (сервис 554–565).
**Это единственный под-батч Stage 2, где тела не ходят через `settings.json`**:
они открывают отдельный `recent_projects.json`, поэтому применён вариант
**SPLIT-BY-ARGUMENT** (решение координатора): делегат читает
`self.recent_projects_file` при каждом вызове (в save — ещё и
`self.user_data_path` для `mkdir`) и передаёт их аргументами; сервис пути НЕ
хранит, конструктор `SettingsService` и перепривязка сервиса в
`_reinitialize_with_new_data_path` не менялись (проверено AST: Store этих двух
имён в сервисе = 0). Тела перенесены ВЕРБАТИМ, документированная правка — 3 и 2
замены ссылок на пути (+ строка `def` в save разбита на две): diff −4/+4 и
−3/+4. В монолите — 2 тонких делегата с исходными сигнатурами (2/2
signature_identical + forwards, форвардинг идёт именованными аргументами путей).

**Живой прогон (offscreen) — 16/16 PASS + перезапуск 6/6 PASS + клик по меню 3/3
PASS + кросс-дерево 0 неожиданных расхождений:**
- все пункты промпта а–ж закрыты фактически: list-формат с фильтрацией
  (`os.path.exists` + `.svproj`, регистр расширения не важен, доставка
  `name`/`last_opened`), старый dict-формат, latin-1-fallback с точной строкой
  предупреждения, отсутствующий файл → [], битый JSON → [] с точной строкой
  ошибки, save в кириллический путь с побайтовой идентичностью каноническому
  `json.dumps(indent=2, ensure_ascii=False)` и созданием `user_data_path`,
  ветка ошибки записи без исключения, переприсваивание `recent_projects_file` →
  чтение/запись в новый файл и «нет кэша» (1 → 2 записи при внешней перезаписи);
- живой прогон: проект сохранён/открыт реальными `save_project_to_file` и
  `load_project` → появился в файле, в меню «Open Recent» («1. S25 Alpha») и в
  списке недавних (панель подставлена — в сборке её нет, см. п. 45 реестра);
  второй проект встал выше; удаление и `clear_recent_projects` (Yes/No) работают;
  лимит `MAX_RECENT_PROJECTS=10` соблюдён; `restore_last_project_if_enabled`
  восстанавливает самый свежий проект, а перезапуск в ОТДЕЛЬНОМ интерпретаторе
  делает это на СТАРТЕ приложения (`__init__` 6486) — то есть проверен именно
  путь запуска;
- «прежняя реализация» — тот же драйвер в worktree `d4db217`: 16/16 PASS, и
  сравнение JSON-листьев двух деревьев даёт 0 неожиданных расхождений (7
  отличий — прямые вызовы сервиса, которых до переноса не существует).
- 7 NOT-MOVE-блоков (4 метода тира C недавних + 3 миграции) — byte-identical;
  `__init__`, `_reinitialize_with_new_data_path`, `update_recent_menu`,
  `restore_last_project_if_enabled` — byte-identical; оба присваивания
  `recent_projects_file` на месте (2/2).
- манифест (по git-блобам): changed = ровно 2 (`Supervertaler.py` 0854f899… →
  c0370685…, `modules/settings_service.py` 6778e9e7… → 5e582639…), added/removed
  = 0; 8 метрик 1211/18/35/24/24/0/85/2 — файлы до/после побайтово равны;
  py_compile COMPILE_OK; смоук save/load EXIT=0 на обоих деревьях.

Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.5).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.5 recent-projects).txt`;
аудиты: `docs/refactoring/audits/batch7s25_*` (снапшот-индекс 9 блоков,
deps-load/store, manifest-before/after/cmp по git-блобам, line-accounting
монолита и сервиса, callsites head/AST-cmp, path-attrs dump+cmp, verify 33/33,
app-check work/head-wt/cmp, restart work/head-wt/cmp, menu work/head-wt/cmp,
smoke-exit). Непокрытые проверки — §4 отчёта; новый пункт реестра **один: п. 45**
(home-экран «Recent projects»: панель `recent_projects_layout` в сборке не
создаётся, отрисовка проверена подставленным реальным `QVBoxLayout`; MOOT для
текущей сборки), остальное — ссылками на п. 12/13/21/25/29/30/33/35/36/43/44,
чтобы не дублировать сквозные пункты.

**РАСКРЫТИЕ ФАКТИЧЕСКОГО СУЖЕНИЯ SCOPE (занесено и в `EXTRACTION_PLAN.md`):**
план ожидал в S2.5 «голосовую часть S2.4 + recent-projects + миграции» — 10
методов / ~419 строк, после чего «будет закрыто 33 из 33 методов Stage 2».
Координатор переопределил под-батч: перенесены ТОЛЬКО `load/save_recent_projects`
(2 метода / 74 строки), а голосовые методы (`load/save_dictation_settings`,
`load/save_voice_vocabulary_settings`, `load_language_settings`) и три миграции
(`_migrate_settings_to_unified`, `_migrate_to_workbench_layout`,
`_migrate_voice_dictation_default_off`) промпт прямо отнёс к СТРОГО NOT-MOVE.
Итог Step 7: **перенесено 25 методов** (S2.1 6, S2.2 3, S2.3 10, S2.4 4, S2.5 2),
остальное осталось в монолите сознательно — основания в итоговом блоке Step 7
`EXTRACTION_PLAN.md`

## Что дальше: Step 7 Stage 2 — под-батч S2.4 закрыт (Batch #7 Stage 2, 27.09.2026)

## Что дальше: Step 7 Stage 2 — под-батч S2.4 закрыт (Batch #7 Stage 2, 27.09.2026)

**S2.4 выполнен** (база HEAD `f600e00` РОВНО — ни потомков, ни расхождения; монолит
68 285 → **68 274** строки, −11; `git diff --numstat` 27/38, difflib — ровно 4
региона, сумма −11 == изменению файла). Перенесены 4 метода / 47 строк в
`modules/settings_service.py` (368 → 451 строка; методы 20 → 24) —
`_load_language_pair_from_disk` (402–419), `save_language_settings` (421–431),
`_save_spellcheck_settings` (433–442), `_load_spellcheck_settings` (444–451).
**Это первый под-батч Stage 2, где сработало стоп-условие «зависимость от состояния
окна»:** два тела перенесены ВЕРБАТИМ (`save_language_settings`,
`_load_spellcheck_settings`), а два — SPLIT-ом (документированная правка −3/+3 и
−2/+2): сервисный `_load_language_pair_from_disk` больше не пишет
`self.source_language`/`target_language`, а ВОЗВРАЩАЕТ пару (на исключении — None),
и атрибуты окна пишет тонкий делегат (только при не-None результате);
сервисный `_save_spellcheck_settings(enabled)` больше не читает
`self.spellcheck_enabled` — значение передаёт делегат. В монолите — 4 тонких
делегата с исходными сигнатурами (4/4 signature_identical + forwards).
Ограничение промпта выполнено: единственный вызов `_load_language_pair_from_disk`
остался в `__init__` на строке 6348 (LOADS `source_language`/`target_language` в
`__init__` = 0, проверено AST и до, и после).

**Живой прогон (offscreen) — 11/11 PASS + отдельный процесс-перезапуск 4/4 PASS:**
- SPLIT подтверждён живьём: прямой вызов сервиса вернул пару и НЕ тронул атрибуты
  окна; делегат записал их; на искусственном исключении атрибуты остались
  нетронутыми, а сохранённая диагностика `[LangSettings] Load failed…` попала в stdout.
- Вкладка Language Pair проверена через РЕАЛЬНЫЙ обработчик
  `_save_language_settings_from_ui` (настоящие QComboBox); тумблер spellcheck — через
  РЕАЛЬНЫЕ `_toggle_spellcheck_from_button` и `_toggle_spellcheck` (в логе виден бэкенд
  `pyspellchecker (pl_PL)`); файл всегда равен состоянию окна.
- Перезапуск в ОТДЕЛЬНОМ интерпретаторе на изолированном каталоге данных (резолвер
  `get_user_data_path` подменён до создания окна): языковая пара и spellcheck
  подхватились из файла, а голосовой диктант в режиме «Auto (use project target
  language)» получил `language='pl'` из пережившего перезапуск `self.target_language`
  (контроль: 'ru'; автодетект → 'auto').
- Ровно 4 метода-соседа не тронуты байт-в-байт (8 NOT-MOVE-блоков, включая
  `load_dictation_settings`, найденный AST repo-wide); 8 метрик 1211/18/35/24/24/0/85/2
  без изменений (файлы до/после побайтово равны); манифест changed=2, added=0, removed=0;
  смоук save/load — `EXIT=0` и на рабочем дереве, и на worktree HEAD.

Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.4).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.4 languages-spellcheck).txt`;
аудиты: `docs/refactoring/audits/batch7s24_*` (снапшот-индекс 12 блоков,
deps-load/store, manifest-compare, line-accounting, callsites AST-compare,
per-file counts, verify 37/37, app-check JSON+лог, restart JSON+лог, smoke-exit).
Непокрытые проверки — раздел 4 отчёта (новый пункт реестра один: **п. 44** —
голосовой диктант с реальным аудио, переведён в **MOOT** (docs-follow-up): Voice-виджет
удаляется целиком в Batch #8, ручной голосовой тест не проводится; остальное дано
ссылками на п. 12/13/14/15/17/18/19/20/21/27, чтобы не дублировать сквозные пункты).

**РАСКРЫТИЕ ДВУХ ФАКТИЧЕСКИХ ПОПРАВОК** (обе занесены в `EXTRACTION_PLAN.md`):
1) состав «S2.4 = 9 методов / ~203 строки» на этом шаге НЕ выполнялся целиком —
   координатор исключил голосовую часть, поэтому под-батч = 4 метода / 47 строк;
2) утверждение промпта «остальные 3 кандидата используют
   `_load_settings_section("ui")`» неверно: разделение API фактическое 2/2
   (`save_language_settings` и `_save_spellcheck_settings` пишут через whole-file
   API, два оставшихся читают секционным). Асимметрия сохранена «как есть».

**Дальше — S2.5 «голосовая часть + recent-projects + миграции», 10 методов / ~419 строк.**
Границы ПЕРЕСЧИТАНЫ AST на этом дереве (после переноса −11; номера ниже 52 249
сместились, ниже 44 991 — тоже):
    load_recent_projects                    32326–32388 (63)
    save_recent_projects                    32390–32400 (11)
    _migrate_settings_to_unified            44744–44834 (91)
    _migrate_to_workbench_layout            44836–44901 (66)
    load_dictation_settings                 44918–44933 (16)   ← голосовая часть
    save_dictation_settings                 44935–44989 (55)   ← SPLIT (QMessageBox)
    load_voice_vocabulary_settings          45015–45053 (39)   ← голосовая часть
    save_voice_vocabulary_settings          45055–45078 (24)   ← голосовая часть
    _migrate_voice_dictation_default_off    45129–45160 (32)   ← 3-я миграция
    load_language_settings                  45214–45235 (22)   ← SPLIT (TagHighlighter +
                                                                  spellcheck_manager)
NOT-MOVE-остаток (не переносить без решения владельца):
`load_general_settings` 44542–44638 (97), `save_clipboard_privacy_settings`
44721–44742 (22), `get_autocorrect_settings` 44640–44651 (12, тир C),
`load_font_sizes_from_preferences` 45256–45342 (87, тир C — ссылается на классы
монолита). После S2.5 будет закрыто 33 из 33 методов Stage 2 (23 закрыто S2.1–S2.4).
**ПРОГНОЗ НЕ ПОДТВЕРДИЛСЯ:** координатор сузил S2.5 до `load/save_recent_projects`,
поэтому Step 7 закрыт на **25 методах**; голосовая часть и три миграции остались в
монолите сознательно. Правка прогноза — `EXTRACTION_PLAN.md`, блок «ПОПРАВКА К
ПРОГНОЗУ S2.4» и «ИТОГ Step 7 — ЗАКРЫТ ЦЕЛИКОМ».

## Что дальше: Step 7 Stage 2 — под-батч S2.3 закрыт (Batch #7 Stage 2, 27.09.2026)

**S2.3 выполнен** (база HEAD `7a2de37` — потомок `4c7ad680`; монолит 68 373 →
**68 285** строк, −88; `git diff --numstat` 47/135, difflib — ровно 10 регионов,
сумма −88 == изменению файла). Перенесены 10 методов / 150 строк в
`modules/settings_service.py` (197 → 368 строк; методы 10 → 20) — `load_llm_settings`
(в сервисе 210–248), `save_llm_settings` (250–257), `load_proxy_settings` (259–275),
`save_proxy_settings` (277–284), `_get_proxy_url` (286–308), `_get_proxy_dict`
(310–317), `load_provider_enabled_states` (319–345), `save_provider_enabled_states`
(347–354), `load_api_keys` (356–364), `save_api_keys` (366–368). Тела — ВЕРБАТИМ
(10/10, sha256 == снапшотам HEAD); новых параметров конструктора не потребовалось
(единственные внешние зависимости — методы самого сервиса + stdlib `urllib.parse`);
в монолите — 10 тонких делегатов с исходными сигнатурами (10/10
signature_identical + forwards), приватные имена `_get_proxy_url`/`_get_proxy_dict`
сохранены. `_get_api_keys` (11452) НЕ трогался (сторонний
`modules/llm_clients.load_api_keys`).

**Риск-приоритеты закрыты прямыми тестами (offscreen, 14/14 PASS):**
- ★ RISK #1 — ПЯТЬ НЕЗАЩИЩЁННЫХ вызовов `PreTranslationWorker`
  (`self.parent_app.load_api_keys()` без guard): 5637, 5660, 5730, 5943, 5995 —
  все пять вызваны под фейковым LLMClient; счётчик на СЕРВИСНОМ методе доказал
  цепочку делегат→сервис; плюс полный `wk.run()`; негативный контроль показал
  AttributeError без делегата.
- RISK #2 — hasattr-guarded сайты LLM-чата: реальный `ChatBackend(w, …)` поднял LLMClient
  через guard; «тихого» провала в дефолт нет.
- SuperlookupTab-сайт (`_perform_mt_lookup`) — оба делегата реально вызваны.
- Дефолты на пустом файле, цепочка прокси (с percent-encoding), миграция
  google→gemini, отсутствие кэша (3 вызова = 3 открытия), цикл записи на КОПИИ
  user_data (соседние секции сохранены), продовый settings.json sha не изменился.

Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.3).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.3 llm-proxy-keys).txt`;
аудиты: `docs/refactoring/audits/batch7s23_*` (снапшот-индекс, manifest-compare,
line-accounting, callsites AST-compare, per-file counts, verify, app-check JSON+лог).
Непокрытые проверки — раздел 4 отчёта (M1–M13; главные: реальный сетевой вызов LLM/MT,
настоящие клики в модальных окнах Settings, полный человеческий цикл — после S2.4/S2.5).

**Дальше — S2.4 «языки / диктовка / словарь / спеллчек», 9 методов / ~203 строки** —
**ВЫПОЛНЕН, см. раздел S2.4 ВЫШЕ** (код перенесён по 4 методам вместо 9: голосовая
часть вынесена в S2.5 решением координатора). Границы были выведены AST ЗАНОВО
(после сдвига −88). После S2.3 в Stage 2 было перенесено 19 из 32 методов.

## Что дальше: Step 7 Stage 2 — под-батч S2.2 закрыт (Batch #7 Stage 2, 26.09.2026)

**S2.2 выполнен** (база HEAD `25627c9` — потомок `3e5c100c`; монолит 68 400 →
**68 373** строки, −27: делегаты −34, комментарии +7; `git diff --numstat` 23/50).
Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.2).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.2 general).txt`;
аудиты: `docs/refactoring/audits/batch7s22_*` (манифест до/после + сравнение,
counts, analysis, snapshot_index, verify, line_accounting, quotes, app_check_run2,
bug_head_probe, smoke_save/load).

**Что сделано:** в `modules/settings_service.py` (113 → 197 строк) добавлены три
метода общего слоя ВЕРБАТИМ-переносом (sha256 тел совпадают со снапшотами HEAD):
`load_clipboard_privacy_settings` 140–149, `_load_general_settings_from_file`
151–190, `save_general_settings` 192–197. В монолите на месте их тел — три тонких
делегата с исходными именами и сигнатурами: `load_clipboard_privacy_settings`
44711–44719, `_load_general_settings_from_file` 44903–44909,
`save_general_settings` 44911–44916. Новых параметров конструктора НЕ потребовалось:
тела зависят только от `_load_settings_section` / `_save_settings_section` / `log`
(измерено AST — §1.3 отчёта), т.е. всё уже есть в сервисе.

**Сохранение бага бит-в-бит:** делегат `save_general_settings` оставлен БЕЗ default
у обязательного `settings` (AST: `defaults = []`), поэтому вызов без аргумента
падает тем же `TypeError`, что и до переноса. Проверено ДО/ПОСЛЕ на worktree HEAD
25627c9 (`audits/batch7s22_bug_head_probe.*`) — текст ошибки совпадает посимвольно.
Дополнительно выяснено (новое): оба баговых сайта (теперь 66753 и 66796,
SuperlookupTab) защищены `hasattr(<окно>, 'general_settings')`, а такого атрибута в
монолите НЕ СУЩЕСТВУЕТ → путь сегодня мёртв, баг спит (кандидат в
VALIDATION_BACKLOG для решения владельца, НЕ из S2.2).

**NOT-MOVE:** `load_general_settings` 44542–44638 (97 строк) — код не тронут
вообще, байт-в-байт как в HEAD; его внутренний вызов
`self._load_general_settings_from_file()` продолжает работать через делегат (это и
есть выполнение V3-требования SPLIT — отдельного разделения тела не делалось).
`save_clipboard_privacy_settings` (44721–44742) тоже остался в монолите (V3).

**Валидация:** py_compile OK (144 файла); 8 метрик 1211/18/35/24/24/0/85/2 — до и
после идентичны; манифест 144 → 144 (changed=2: `Supervertaler.py`
80993e2f…, `modules/settings_service.py` 02914e1f…; added/removed = 0); difflib —
ровно 5 неравных регионов, все заявленные, сумма −27 == изменению файла; живой
offscreen-прогон приложения — **9/9 PASS** (делегаты == сервис, 4 внутренних
потребителя, getattr-путь `modules/clipboard_manager_widget.py:771` с реальным
виджетом и маркером из файла, полный цикл save→файл→load→окно→виджет на КОПИИ
user_data, продовый settings.json побайтово не изменился, «3 вызова = 3 открытия»);
смоук save/load OK (`SAVE_OK 6584`, `LOAD_OK S22Smoke 7`) и одинаково на обоих
деревьях. Непокрытые проверки — §4 отчёта (главные: настоящие клики в модальных
диалогах; запись clipboard-настроек через UI; полный человеческий цикл
«изменить каждую вкладку → перезапуск» — после S2.3/S2.4; N14 — продовые user-data
затрагивались дважды, оба раза контролируемо и откатано).

**Дальше — S2.3 «LLM / proxy / provider / api keys», 10 методов / 150 строк**
(ровно на границе конвенции ≤10 — отметить в отчёте явно):
`load_llm_settings`, `save_llm_settings`, `load_proxy_settings`,
`save_proxy_settings`, `_get_proxy_url`, `_get_proxy_dict`,
`load_provider_enabled_states`, `save_provider_enabled_states`, `load_api_keys`,
`save_api_keys`; fan-in ~116, ~10 вызовов из `modules/` + ~10 строковых, часть имён
приватные. Границы вывести AST ЗАНОВО на дереве S2.2 (после −27 документированные
номера сдвинуты).

## Что дальше: Step 7 Stage 2 — под-батч S2.1 закрыт (Batch #7 Stage 2, 25.09.2026)

**S2.1 выполнен** (база HEAD `043da2a`, монолит 68 386 → **68 400** строк; прирост
+14 разобран замером: импорт +1, блок делегатов −6, проводка в `__init__` +10 и в
`_reinitialize_with_new_data_path` +9 — `git diff --numstat` 47/33 по одному файлу,
но уточнение регионов см. §8.1 отчёта и `audits/batch7s21_line_accounting.txt`). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.1).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.1 settings core).txt`;
аудиты: `docs/refactoring/audits/batch7s21_*` (манифест до/после + сравнение, counts,
callsites, verify, class_shape, snapshot_index, remaining_ast, app_check_run{1,2,3},
smoke-*) и `not_moved_methods_batch7stage2s21_snapshot.txt`.

**Что сделано:** новый класс `SettingsService` (`modules/settings_service.py`,
113 строк; конструктор с ЯВНЫМ `settings_dir` + опц. `log`, без ConfigManager) с
6 методами ядра (`_get_settings_dir`, `_get_unified_settings_path`,
`_load_unified_settings`, `_save_unified_settings`, `_load_settings_section`,
`_save_settings_section`; 5 тел перенесены БАЙТ-В-БАЙТ, 1 строка — инъекция пути).
В монолите на их месте — 6 тонких делегатов (44639–44696) с исходными именами и
сигнатурами, строка импорта (421), конструктор сервиса в `__init__` (6301–6309) и
ПЕРЕПРИВЯЗКА сервиса первым оператором `_reinitialize_with_new_data_path()`
(6668–6676) — без неё смена каталога данных (`user_data_path` переприсваивается в
6630/6934/22859, все три ведут в этот метод) оставила бы делегаты и ещё не
перенесённые миграции на старом пути.

**Валидация:** py_compile OK (144 файла); 8 метрик 1211/18/35/24/24/0/85/2 — без
изменений; манифест 143→144 (changed=1, added=1, removed=0); живой offscreen-прогон
приложения — **13/13 PASS** (main():68370 `window._load_settings_section("ui")`,
getattr-пути `modules/voice_tab.py` и `modules/clipboard_manager_widget.py`,
save-путь General-вкладки, полный цикл save→файл→load→окно на КОПИИ user_data,
перепривязка при смене каталога; «4 вызова = 4 открытия файла» — кэша нет);
смоук save/load OK (LOAD_OK и на S2.1, и на HEAD-worktree; краш 0xC0000005 на
teardown идентичен на обоих — предсуществующий, вне скоупа). Непокрытые проверки —
раздел 4 отчёта (главные: настоящий клик Save в модальном диалоге не нажимался;
полный человеческий цикл «изменить каждую вкладку → перезапуск» — после S2.2–S2.4).

**Дальше — S2.2 «general + общий reading», 4 метода / 153 строки** — **ВЫПОЛНЕН
26.09.2026, см. раздел S2.2 выше** (границы пересчитаны AST после S2.1 — `docs/refactoring/audits/batch7s21_remaining_ast.txt`):
`load_general_settings` 44542–44638 (97 строк, SPLIT — применение 35 атрибутов
остаётся в монолите), `_load_general_settings_from_file` 44897–44936 (40),
`save_general_settings` 44938–44943 (6), `load_clipboard_privacy_settings`
44704–44713 (10); `save_clipboard_privacy_settings` 44715–44736 — НЕ переносится
(V3). **Открытый вопрос перед стартом S2.2 ЗАКРЫТ (25.09.2026, follow-up S2.1)**:
прямая цитата кода показала, что формы `getattr(self, 'load_general_settings', lambda: {})()`
нет ни в одном из 7 мест — везде `hasattr`-guard + обычное обращение к атрибуту
(`Supervertaler.py:1810–1811` на `parent()`-цепочке, `modules/quicktrans.py:302–303`
на `parent_app`, плюс 7881, 55559, 55568, 64711, 64726 на `self`/`mw`) → аудит Б1
подтверждён, формулировка Stage 1 §1.4 ошибочна; делегат с исходным именем сохраняет
все места работоспособными, «мягкого» duck-typing-контракта не требуется. Цитаты и
инвентарь: `docs/refactoring/audits/batch7s21_open_item_quotes.txt`; разбор — §8.2
отчёта S2.1.
Если за время паузы строки 44542–44943 или файлы `modules/{voice_tab,
clipboard_manager_widget,termbase_entry_editor}.py` трогали — границы и метрики
пересчитать AST заново перед переносом.
Прирост монолита S2.1 (+14 строк: импорт +1, делегаты −6, проводка в `__init__` +10 и
в `_reinitialize…` +9) подтверждён difflib-замером по всем 10 неравным регионам —
`docs/refactoring/audits/batch7s21_line_accounting.txt`, §8.1 отчёта S2.1.

## Что дальше: Step 7 — Stage 1 закрыт (Batch #7 Stage 1, 24.09.2026, read-only)

**Stage 1 выполнен** (HEAD `b5c46e7`, монолит 68 386 строк, sha256 блоба
`802c504c8849ac58551bece6b297917426e31226` — код не менялся). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 1.txt`; разбор 1.1–1.9:
`docs/refactoring/audits/step7_stage1_findings.md`; измерения:
`docs/refactoring/audits/batch7_stage1_{methods_ast,candidates_scan,inventory_tables,callsites_categorized,callsites_raw,dependencies,dead_dynamic_check,config_manager_overlap}.*`.

**Состав (подтверждён AST):** 35 методов / 830 строк = A (ядро API, 6 методов /
39 строк: `_get_settings_dir` 44639–44641, `_get_unified_settings_path` 44643–44645,
`_load_unified_settings` 44647–44661, `_save_unified_settings` 44663–44672,
`_load_settings_section` 44674–44676, `_save_settings_section` 44678–44682) + B
(29 доменных аксессоров, 791 строка). Миграции: `_migrate_settings_to_unified`
**44724–44814**, `_migrate_to_workbench_layout` **44816–44881**,
`_migrate_voice_dictation_default_off` **45143–45174** (третья, в плане отсутствует).
Тир C (не включать): `get_autocorrect_settings` 44620–44631,
`add/_remove/clear_recent_projects` 32238–32288 / 32290–32304 / 32416–32430,
`load_font_sizes_from_preferences` 45275–45361.
Не два окна из плана, а ≥9 кластеров в span **8481–61247**; «~25» плана ≈ ядро A+B,
«~46» координатора смешало A+B + тир C + одноразовые писатели секций (группа G3:
`_set_voice_pause_setting`, `save_termbase_code_map`, `_set_fr_demote_to_draft`,
`_persist_autocorrect_settings` и др. — все вне состава).

**Главные риски/факты:** `load_general_settings` = **61 call-сайт** (56 методов
`SupervertalerQt`, `PreTranslationWorker.run` 5479, `SuperlookupTab` 66766/66809,
`main()` 68357, `modules/quicktrans.py:303`) + 7 `getattr`-строковых обращений; это НЕ
чистый IO (2 строки чтения из 97 + 35 присваиваний `self.<attr>`) → SPLIT.
Семантика «файл читается заново на каждый вызов» подтверждена (кэшей нет). Дукт-тайпед
обращения из `modules/` есть и к ПРИВАТНЫМ именам (`_load_unified_settings`,
`_save_unified_settings`, `_load_settings_section`, `_save_settings_section`,
`_get_proxy_url`) → 35 тонких делегатов с исходными именами. ConfigManager:
`get_preferences_path/load_preferences/save_preferences` — дубликаты того же файла/секции
с 0 call-sites, а его резолвер user_data (`~/.supervertaler_config.json`) отличается от
монолитного (`%APPDATA%/Supervertaler/config.json`) → сервис не должен резолвить путь сам.
Наблюдения вне скопа: латентный баг `modules/termbase_entry_editor.py:121/131`,
дубликаты чтения `settings.json` (llm_clients/feature_manager/ui_scale), три механизма
указателя user_data.

**Решение владельца (V1–V4) перед Stage 2:** (V1) архитектура — рекомендация: новый
класс `SettingsService` в `modules/settings_service.py` с явным `settings_dir`
(+ опц. `log`), ConfigManager не расширять; (V2) не включать тир C; (V3) SPLIT для
`load_general_settings` и `_migrate_voice_dictation_default_off` обязателен, для
`save_clipboard_privacy_settings`/`save_dictation_settings`/`load_language_settings` —
на выбор; (V4) под-батч S2.5 (recent + миграции) с валидацией на копии user_data.

**Разбивка Stage 2+ (по риску):** S2.1 ядро API (6/39) → S2.2 general + общий reading
(5/175, fan-in 90) → S2.3 LLM/proxy/provider/api keys (10/150, ★ ровно на границе
конвенции 10 методов) → S2.4 языки/диктовка/словарь/спеллчек (9/203) → S2.5 recent +
миграции (5/263). Ни один под-батч не превышает 10 методов.


| 12 | TM / Termbase сервисы | ⬜ не начат | — |
| 13 | Перевод-ядро (вкл. PreTranslationWorker) | ⬜ не начат | — |
| 14 | SuperLookup + Voice + финальный cleanup | ⬜ не начат | — |

## История: Step 6 ЗАКРЫТ ЦЕЛИКОМ (Batch #6 Stage 4 — последний под-батч)

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
- **Delegates сохраняют сигнатуру БАЙТ-В-БАЙТ, включая обязательные аргументы**:
  если до переноса метод требовал позиционный аргумент, делегат НЕ получает
  `default` — иначе «заодно починенный» баг меняет наблюдаемое поведение вне
  скоупа переноса. Проверять это AST-ом (`args.defaults == []`), а не глазами
  (Batch #7 S2.2: `save_general_settings`, два пред-существующих сайта без
  аргумента). Комплект проверки — сравнение поведения на `git worktree` HEAD.
- **Guard-атрибут может быть мёртвым**: `hasattr(<окно>, 'general_settings')`
  выглядит как защита, но такого атрибута в монолите нет вообще (0 присваиваний) →
  путь не исполняется, и «баг» не воспроизводится из UI. Прежде чем писать
  «пред-существующий баг срабатывает», проверять существование атрибута
  измерением (`hasattr` на живом окне), а не по тексту guard.
- **git в этом окружении**: репозиторий принадлежит другому пользователю
  (`dubious ownership`), поэтому все команды запускать как
  `git -c safe.directory=E:/Dev/SupervertalerPortable …` (в т.ч. из Python-скриптов
  через `subprocess`), НЕ меняя глобальный git-config.
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
