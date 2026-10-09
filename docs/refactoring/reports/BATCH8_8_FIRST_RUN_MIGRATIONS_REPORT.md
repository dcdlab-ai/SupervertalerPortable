# Batch #8.8 — Первый запуск без визарда и удаление legacy-миграций

Исполнитель: Zcode. Репозиторий: dcdlab-ai/SupervertalerPortable.
Основание: BATCH8_STAGE1_AUDIT_REPORT.md (§1.1, §2.5 F5, §2.6 F6, §4.1, §5 п. 8.8, вопрос 10),
EXTERNAL_STATE_AUDIT_REPORT.md (§1 п. 1, 7; §3; §4), BATCH8_10_SUPERLOOKUP_TRIM_REPORT.md (протокол).
Кодовый коммит: **ede28068** «Batch #8.8: remove SetupWizard, first-run gates and legacy migrations».
База: код 6897539d (Batch #8.10).

## 0. Baseline и git-синхронизация

| Пункт | Значение |
|---|---|
| HEAD до | 88ad1f31 (= origin/main, пуш Дмитрия) |
| Дрейф-чек | `git merge-base --is-ancestor 6897539d HEAD` → OK (предок) |
| Supervertaler.py (рабочая копия) | SHA256 `b7fb94cd4e4a95c672b25f254ec200671131b51bde48e6fcbfba5c4899e7e981`, 62387 строк, w/crlf |
| py_compile baseline | 139/139 OK (включая modules/setup_wizard.py) |
| modules/**/*.py | 121 |
| Защита 1 baseline | стартовая цепочка: 967 self-вызовов, 0 неразрешённых (`startup_chain_before.json`) |
| Защита 3 baseline | pyflakes: 680 warnings, **149 undefined name** (`undefined_names_before.txt`) |
| EOL baseline | `git ls-files --eol`: Supervertaler.py i/lf w/crlf; setup_wizard.py i/lf w/lf |

Stage-каталог: `D:\Temp\SupervertalerPortable\refactoring\b8-8\` (snapshots/, probes/, baseline-файлы).

### Offscreen-пробы «ДО» (изолированный профиль, QT_QPA_PLATFORM=offscreen, USERPROFILE/APPDATA/HOME → временные папки)

Пробник `probe_window.py` логирует каждую попытку `QDialog.exec` (класс + windowTitle + стек), печатает дерево каталога данных и sha256-снимки ДО/ПОСЛЕ.

- **S-clean** (нет указателей, нет `~\Supervertaler`): окно строится за 11.6 с; `_needs_data_location_dialog = True`; визард НЕ открылся — `QTimer.singleShot(300, _show_setup_wizard)` не успевает: проба закрывает окно и ставит `singleShot(0, app.quit)` раньше (зафиксировано в логе: MODAL-ATTEMPT отсутствует). Дерево: **27 записей** (`prompt_library/…`, `resources/supervertaler.db{,-shm,-wal}`, `workbench/ai_assistant/…`, `workbench/dictionaries`, `workbench/settings/settings.json`). `workbench/.migrated` НЕ создан (миграции в first-run ветке не выполнялись). Help-меню содержит «🚀 Setup Wizard…».
- **S-upgrade** (каталог в текущей раскладке + `workbench/.migrated` + `first_run_completed: true`, указатель на него): `_needs_data_location_dialog = False`; старт OK; хэш-дифф: added = дефолты prompt_library (6 .md) + `workbench/settings/themes.json`; changed = `resources/supervertaler.db-shm`, `workbench/settings/settings.json` (сессия приложения); removed = [].
- **S-legacy** (старая раскладка: `general_settings.json` + `api_keys.txt` в корне, без `workbench/settings`): baseline ВЫПОЛНЯЕТ миграцию: `[Settings] Migrating to unified settings/settings.json … Migration complete`; removed = `api_keys.txt`, `general_settings.json`; added = `api_keys.txt.migrated`, `general_settings.json.migrated`, `workbench/.migrated`, `workbench/settings/settings.json`, `resources/supervertaler.db*`, дефолты prompt_library, `workbench/ai_assistant/index.json`, `themes.json`.

## 1. Рекон (Этап 1)

### 1.1 F5 — визард и первый запуск (AST, класс SupervertalerQt, строки пересчитаны от 62387-строчной базы)

| Идентификатор | Диапазон | Вызыватели | Что пишет |
|---|---|---|---|
| `needs_first_run_data_dialog()` (top-level) | 292–319 | `__init__` 6258 | — (только читает указатель/дефолт) |
| `self._needs_data_location_dialog` | 6258 (запись) | чтения: 6299, 6305, 6316, 6326, 6497, 6730 | атрибут окна |
| `_show_data_location_dialog` | 6501–6620 | **0 вызовов** (мёртв) | mkdir выбранной папки, `save_user_data_path`, `_reinitialize_with_new_data_path`, `db_manager.connect`, `QTimer.singleShot(300, _show_first_run_welcome)` |
| `_reinitialize_with_new_data_path` | 6622–6684 | 6600 (визард-диалог), 6911 (визард), 22421 (Settings→General «смена папки») | миграции, db reconnect, менеджеры |
| `_show_first_run_welcome` | 6686–6701 | 6610 (из `_show_data_location_dialog`, мёртвый путь) | `settings['first_run_completed'] = True` |
| `_show_setup_wizard` | 6703–6951 | 6499 (`QTimer.singleShot(300, …)`), 9156 (Help-меню) | mkdir, `save_user_data_path`, `_reinitialize_with_new_data_path`, `db_manager.connect`, `first_run_completed = True` (6926) |
| Help-пункт «🚀 Setup Wizard…» | 9154–9157 | — | QAction + connect + addAction |

Визард/диалог ПИШУТ: `first_run_completed` (general-секция settings.json), указатель `save_user_data_path`, mkdir каталога данных. Читатели `first_run_completed`: только гейт 6497 (сам визард). После удаления — 0 упоминаний во всём репо (замер: `grep -rn first_run_completed Supervertaler.py modules/ tools/` → 0).

### 1.2 `__init__` — ветвление по `_needs_data_location_dialog` (до)

| Строки | Ветка «первый запуск = True» | Ветка «False» |
|---|---|---|
| 6299 mkdir user_data_path | пропуск (создаст диалог) | mkdir |
| 6305–6307 миграции | пропуск | `_migrate_settings_to_unified` + `_migrate_to_workbench_layout` |
| 6316 `_load_language_pair_from_disk` | пропуск | загрузка пары |
| 6326 `db_manager.connect` | пропуск (подключит диалог) | connect |
| 6497–6499 гейт визарда | singleShot(300, визард) | только если `first_run_completed` отсутствует |

Diff-план: порядок вызовов не меняется; все гейты снимаются (ветка «False» становится безусловной); mkdir дополняется `workbench/settings` (см. п. 1.4). `get_user_data_path` вызывается до всех зависимых (6268) — сохранено. `db_manager.connect` безусловно — каталог уже существует, т.к. mkdir идёт ДО connect (6297→6327).

### 1.3 `_reinitialize_with_new_data_path`

Остаётся (Settings→General, вызов 22421). Из тела удалены вызовы двух миграций (6635–6636); добавлена безусловная идемпотентная mkdir-раскладка. Остальное тело (settings_service, db reconnect, менеджеры, theme) — без изменений.

### 1.4 F6 — миграции

| Метод | Диапазон | Побочные эффекты |
|---|---|---|
| `_migrate_settings_to_unified` | 42941–43031 | создаёт `workbench/settings/settings.json`; переносит `general_settings.json`/`ui_preferences.json`/`feature_settings.json`/`api_keys.txt` → `*.migrated`; переносит 6 спутниковых JSON в `settings/`; читает `user_data_private/api_keys.txt` |
| `_migrate_to_workbench_layout` | 43033–43098 | флаг `workbench/.migrated`; перенос `settings/`, `dictionaries/`, `voice_scripts/`, `ai_assistant/`, `superbrowser_profiles/`, `web_cache/`, `projects/` → `workbench/`; на чистом старте создаёт `workbench/settings/` + `.migrated` |
| `_migrate_voice_dictation_default_off` | 43133–43164 | UPDATE termbases SET voice_dictation_enabled=0; сентинела `ui.voice_dictation_opt_in_reset_applied` |

Читатели продуктов миграций вне миграций: `workbench/.migrated` — 0 (только запись в самой миграции); legacy-файлы (`general_settings.json`, `ui_preferences.json`, `feature_settings.json`, `api_keys.txt`, `voice_commands.json`) — в коде только строки комментариев (30264, 39763) и сам блок миграций; `superlookup_history.json` в старом пути читается с охраной `if self._search_history_file.exists()` (61144–61146, SuperlookupTab) — СТОП-флага нет. Сентинела `voice_dictation_opt_in_reset_applied` читается только самой миграцией.

Чистый старт без `workbench/settings/`: `SettingsService._load_unified_settings` при отсутствии файла возвращает `{"api_keys": {}, "general": {}, "ui": {}, "features": {}}` (modules/settings_service.py:114–128) — чтение настроек не падает.

Сверка дерева: unconditional mkdir (`user_data_path` + `workbench/settings`) даёт дерево S-clean «ДО» (27 записей) без `workbench/.migrated`; единственное отличие «ПОСЛЕ» — `workbench/settings/themes.json` (см. п. 4.5, объяснено).

### 1.5 Читатели ключей/флагов (весь репо)

| Ключ/флаг | Читатель | Эффект при отсутствии |
|---|---|---|
| `first_run_completed` | гейт 6497 (удалён) | — (после батча: 0 упоминаний) |
| `_needs_data_location_dialog` | 6 гейтов (удалены) | — |
| `usage_statistics_asked` | `_init_usage_statistics` (43296–43318) → `modules/usage_statistics.has_been_asked` | opt-in-диалог статистики показывается по СВОЕМУ ключу, НЕ по состоянию первого запуска — СТОП-флага нет |
| `voice_dictation_opt_in_reset_applied` | только миграция (удалена) | — |

### 1.6 Окна первого запуска

Визард (6499) — удалён. `_show_first_run_welcome` — no-op с 1.9.474, вызывался только из мёртвого `_show_data_location_dialog` — удалён. Opt-in статистики — по своему ключу (см. 1.5). Приветствий/подсказок/Okapi-гейтов по первому запуску не найдено.

### 1.7 modules/setup_wizard.py

0 импортёров во всех формах (`import`, `from`, importlib, `__import__`, строки, spec/toml/bat, tools/): единственные упоминания — сам файл и docs (CODE_MAP_REFACTOR.md). Удалён `git rm`. `ConfigManager.set_user_data_path` — 0 вызовов (мёртв; оставлен для P1, ничего не удалялось).

### 1.8 Расхождения с аудитом

Аудит §1.1 шаг 17 (`QTimer.singleShot(300, _show_setup_wizard)` 6540–6542) — в базе 8.10 это 6497–6499 (сдвиг после 8.10). Состав методов — соответствует аудиту. `_show_data_location_dialog` в аудите не выделен отдельно — в коде существует и мёртв (0 вызовов).

## 2. Что сделано (зона | строки | действие)

| № | Строки (база 62387) | Зона | Действие |
|---|---|---|---|
| 13 | 292–320 | `needs_first_run_data_dialog` | удалить |
| 12 | 6256–6259 | запись `_needs_data_location_dialog` + комментарий | удалить |
| 11 | 6297–6300 | mkdir user_data_path под гейтом | заменить на безусловный mkdir + `workbench/settings` mkdir |
| 10 | 6304–6308 | вызовы миграций в `__init__` | удалить |
| 9 | 6316–6317 | гейт `_load_language_pair_from_disk` | снять гейт |
| 8 | 6324–6327 | гейт `db_manager.connect` | снять гейт |
| 7 | 6357–6369 | комментарий v1.10.29 + `_migrate_voice_dictation_default_off()` | удалить |
| 6 | 6495–6620 | гейт визарда + `_show_data_location_dialog` | удалить |
| 5 | 6634–6636 | вызовы миграций в `_reinitialize` | заменить на mkdir раскладки |
| 4 | 6686–6952 | `_show_first_run_welcome` + `_show_setup_wizard` | удалить |
| 3 | 9154–9157 | Help-пункт «Setup Wizard…» | удалить (+ схлопнуть двойной blank 9153/9158 → 1) |
| 2 | 42902–42903 | комментарий блока делегатов (упоминание миграций) | переписать |
| 1 | 42941–43099 | `_migrate_settings_to_unified` + `_migrate_to_workbench_layout` | удалить |
| 0 | 43133–43165 | `_migrate_voice_dictation_default_off` | удалить |
| — | — | `modules/setup_wizard.py` (354 строки) | `git rm` |

Снапшоты зон с sha256: `D:\Temp\SupervertalerPortable\refactoring\b8-8\snapshots\zone_*.txt` (+ `.sha256`). SHA-guard до правок: `b7fb94cd…` OK. Каждая правка — с assert якорей первой/последней непустой строки.

**Итог:** монолит 62387 → **61743** строки (−644); `git diff --stat HEAD~1 HEAD`: Supervertaler.py +12/−656, setup_wizard.py −354 (всего +12/−1010). EOL: w/crlf восстановлен (12 вставленных строк нормализованы в CRLF; `\r\r\n` = 0). SHA256 после: `db37188c79c7434597abce9f0ddb11c36858838c85f047c94126ecb702cacd0d`.

## 3. Диффы ключевых мест (до/после)

`__init__` (фрагменты):
```python
# ДО
self._needs_data_location_dialog = needs_first_run_data_dialog()
...
if not self._needs_data_location_dialog:
    self.user_data_path.mkdir(parents=True, exist_ok=True)
...
if not self._needs_data_location_dialog:
    self._migrate_settings_to_unified()
    self._migrate_to_workbench_layout()
...
if not self._needs_data_location_dialog:
    self._load_language_pair_from_disk()
...
if not self._needs_data_location_dialog:
    self.db_manager.connect()
...
self._migrate_voice_dictation_default_off()
...
if self._needs_data_location_dialog or not general_settings.get('first_run_completed', False):
    QTimer.singleShot(300, lambda: self._show_setup_wizard(is_first_run=True))

# ПОСЛЕ
self.user_data_path.mkdir(parents=True, exist_ok=True)
(self.user_data_path / "workbench" / "settings").mkdir(parents=True, exist_ok=True)
...
self._load_language_pair_from_disk()
...
self.db_manager.connect()
```

`_reinitialize_with_new_data_path`:
```python
# ДО
self._migrate_settings_to_unified()
self._migrate_to_workbench_layout()

# ПОСЛЕ
self.user_data_path.mkdir(parents=True, exist_ok=True)
(self.user_data_path / "workbench" / "settings").mkdir(parents=True, exist_ok=True)
```

`create_menus` (Help): удалены 4 строки `setup_wizard_action = …` … `help_menu.addAction(setup_wizard_action)`; разделитель после superdocs остаётся одиночным (двойной blank схлопнут).

## 4. Статическая валидация (§4.1)

1. **py_compile ПОСЛЕ**: 138/138 OK (setup_wizard удалён).
2. **Защита 1**: стартовая цепочка (включая `_reinitialize_with_new_data_path`) — 958 self-вызовов, **0 неразрешённых** (`startup_chain_after.json`; было 967 — разница = удалённые вызовы).
3. **Защита 2**: grep по Supervertaler.py, modules/**, tools/** для каждого удалённого идентификатора (`_show_setup_wizard`, `needs_first_run_data_dialog`, `_needs_data_location_dialog`, `_migrate_settings_to_unified`, `_migrate_to_workbench_layout`, `_migrate_voice_dictation_default_off`, `_show_data_location_dialog`, `_show_first_run_welcome`, `setup_wizard`, `SetupWizard`, `.migrated`, `first_run_completed`) — **0** в коде. Допустимые остатки: докстринг `modules/settings_service.py:38–39` (историческое упоминание, не вызов; чистка — финальный docs-проход Batch #8); CODE_MAP_REFACTOR.md (docs, не обновляем по постановке).
4. **Защита 3**: pyflakes ПОСЛЕ — 149 undefined, множество идентично baseline (diff пуст).
5. **AST** (`ast_checks_88.py`): (а) `__init__` self-вызовы: 22 → 18, отличия — только 4 удалённых миграции/визард, порядок сохранён, новых нет; (б) Help-меню: нет Setup Wizard, нет двойных/висячих разделителей (14 help_menu-операций); (в) `_reinitialize` содержит mkdir раскладки, не содержит миграций; (г) нет `save_general_settings()` без аргументов.
6. **Offscreen «ПОСЛЕ»** (те же профили, `probe_after_*.log`):
   - S-clean: окно строится; **ни визард, ни диалог папки не пытались открыться** (MODAL-ATTEMPT = 0); `_needs_data_location_dialog` отсутствует; дерево 28 записей = дерево «ДО» (27) **+ `workbench/settings/themes.json`**. Объяснение: в baseline на first-run пути `workbench/settings` не создавался, и сохранение тем падало (`Error saving themes: … themes.json` в probe_before_clean.log:73); теперь mkdir безусловен и сохранение проходит. Отличие ожидаемое, не регрессия.
   - S-upgrade: хэши данных не изменились, кроме `resources/supervertaler.db-shm` (сессия SQLite); данные открываются.
   - S-legacy: старт без исключения; миграция НЕ выполняется: `api_keys.txt` и `general_settings.json` остались нетронутыми (removed=[]), `workbench/.migrated` не создан; приложение работает с пустым settings.json. Сознательное решение Дмитрия (Portable не импортирует старые данные).
   - main_tabs 6, Settings 14, хоткей при старте только ctrl+alt+q — во всех трёх.
7. **Headless-импорты**: 114 ok / 6 fail / 120 total (было 114/121 с setup_wizard в падении tkinter). Новые падения: нет (tkinter×4, fitz, glossary_manager — предсуществующие).
8. **`first_run_completed: false`** в settings.json копии: визард не появляется (probe_frfalse.log: MODAL-ATTEMPT = 0, PROBE OK).

## 5. Пакет для тестовой сборки (база: код 6897539d)

| № | Путь | Действие | SHA256 | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | заменить | `db37188c79c7434597abce9f0ddb11c36858838c85f047c94126ecb702cacd0d` | 61743 строки, CRLF |
| 2 | `modules/setup_wizard.py` | удалить из тестовой сборки, если есть | — | на работу не влияет (0 импортёров) |

## 6. Сценарии проверки (КОНТРОЛЬ на базовой сборке, затем после замены файлов)

ВАЖНО: указатели `%APPDATA%\Supervertaler\config.json` и `%USERPROFILE%\.supervertaler_config.json` общие для всех сборок — перед чистым стартом СКОПИРОВАТЬ их и ВОССТАНОВИТЬ после тестов. Чистый старт: положить в config.json указатель на ПУСТУЮ папку (например `D:\Temp\svt_clean_ud`), `~\Supervertaler` не использовать.

- **T8.8.1** апгрейд-старт на КОПИИ user_data: старт без исключений; Help-меню без «Setup Wizard»; настройки, TMs, термбазы, недавние проекты, ключи API на месте.
- **T8.8.2** чистый старт (пустая папка данных через указатель): нет визарда и диалога выбора папки; окно открывается; после выхода — `tree /f` каталога данных: сверить с деревом §4 (28 записей, включая `workbench/settings/themes.json`), любое различие — в отчёт.
- **T8.8.3** в чистом старте: ввести ключ API в Settings → Save; создать проект/импортировать md-файл; отредактировать сегмент; Save; закрыть и открыть заново — настройки и проект на месте; второй старт без визарда.
- **T8.8.4** `first_run_completed: false` в settings.json копии: визард не появляется (на базовой сборке — появляется).
- **T8.8.5** Settings → General «смена папки данных» на другую пустую папку: приложение переинициализируется без исключений (метод остаётся до P1); затем вернуть прежнюю папку.
- **T8.8.6** live-test на копии: импорт файла 180/400 сегментов, перевод сегмента, TM-подсказки, Save, навигация по всем вкладкам и страницам Settings.
- **T8.8.7** выход: иконка трея исчезает, процесс завершается (0xC0000005 при выходе — предсуществующий флаки), в логе нет traceback.
- **T8.8.8** восстановить указатели из бэкапа и убедиться, что обычная тестовая сборка снова видит свои данные.

## 7. Непокрытые проверки (честно)

1. Реальный первый запуск на тестовой сборке Дмитрия (offscreen-пробы не заменяют GUI-прогон T8.8.2/T8.8.3).
2. Живой QFileDialog в диалоге смены папки (T8.8.5) — offscreen не покрывает.
3. Реестр HKCU (MTQuickPopup, autostart) — не проверялся.
4. Миграция БД-схемы (database_migrations) при старте на старой БД — вне scope (схема не тронута).
5. Флаки 0xC0000005 при выходе — предсуществующий, не исследован.
6. Поведение на реальном профиле Дмитрия с legacy-файлами в каталоге данных (S-legacy покрыт только синтетическим профилем).

## 8. Вопросы к Дмитрию

1. **S-legacy**: после батча старая раскладка игнорируется (миграция не выполняется, `general_settings.json`/`api_keys.txt` остаются нетронутыми, приложение стартует с чистыми настройками). Подтвердите, что это сознательное решение (Portable не импортирует старые данные) — в постановке оно заявлено, фиксируем как решение.
2. **themes.json** в чистом старте (28-я запись дерева) — ожидаемое следствие безусловного mkdir (в baseline сохранение тем падало). Принять как норму?
3. Докстринг `modules/settings_service.py:38–39` (упоминание удалённых миграций) — чистить в финальном docs-проходе Batch #8?
