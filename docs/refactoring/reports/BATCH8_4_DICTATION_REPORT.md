# Batch #8.4 — Удаление F1: диктовка PTT, словарь, UI «🎤»

Кодовый коммит: `bf821d0f` «Batch #8.4: remove voice dictation, vocabulary, termbase 🎤 UI (F1)».
База: состояние после Batch #8.3 (HEAD `03308061`, Supervertaler.py `74b05eaf…`, 67157 строк).
Стейдж-каталог: `D:\Temp\SupervertalerPortable\refactoring\b8-4\`.

## 0. Baseline и git-синхронизация

| Проверка | Значение |
|---|---|
| git fetch origin | OK, изменений нет |
| HEAD == origin/main | `03308061` |
| git status | чисто (untracked `.zcode/plans/…`, `.zcodeignore` — допустимо) |
| Дрейф-чек | `git merge-base --is-ancestor 91f7f8ac HEAD` → OK |
| SHA256 Supervertaler.py | `74b05eaf3fc619af18c93720e9970ff4e68f8aa5ff70effb618f435afd3a5c3f` (67157 строк) — совпал с пакетом 8.3 |
| modules/**/*.py | 131 файл |
| py_compile ДО | 132/132 OK (монолит + 131 модуль) |
| EOL ДО | w/crlf — предсуществующие (Supervertaler.py, grid/filters, grid/pagination, tag_manager, undo_manager и документация) |

Базовые значения защит:

| Защита | ДО |
|---|---|
| 1. Резолв стартовой цепочки (скрипт 8.3 + `create_termbases_tab`/`create_assistance_panel`/`create_grid_view_widget_for_home` в цепочке) | 934 вызова, 0 неразрешённых |
| 2. pyflakes undefined names | 149, множество идентично 8.3-after (посимвольный diff `un_before_sorted.txt`) |
| 3. Offscreen-проба ДО | 7 вкладок; 16 страниц Settings; кнопок Dictate **1** (текст `🎤 Dictate (Ctrl+Shift+Space)`, parent QWidget); хоткеи `ctrl+alt+c/l/q/ctrl+shift+space`; таблица термбаз **10 колонок** `[Type, Name, Languages, Terms, Read, Write, Project, AI, 🎤 Voice, 🔍 SuperLookup]` |
| headless-импорты ДО (8.3-after) | 124/131, падения предсуществующие |

Примечание к пробе ДО: созданий кнопки Dictate в коде **два** (грид-тулбар и нижняя
панель вкладки), проба нашла 1 — вторая панель строится в ветке, не выполняющейся
при пустом профиле. Контроль ПОСЛЕ: 0 кнопок (см. §4).

## 1. Рекон

### 1.1 Таблица имён (AST + grep, полная таблица в `recon_names.txt`)

| Имя | Где (номера ДО) | Класс self | Только 8.4? | Действие |
|---|---|---|---|---|
| `_get_voice_release_poller` | 53174–53209 | SupervertalerQt | да | УДАЛИТЬ |
| `_register_voice_pushtotalk_deferred` | 53211–53226 | SupervertalerQt | да (0 вызывающих с 8.2) | УДАЛИТЬ |
| `_get_voice_hotkey_listener` | 53228–53274 | SupervertalerQt | да | УДАЛИТЬ |
| Pause-блок: `_voice_pause_mode`, `_pause/_resume_alwayson_external`, `_ensure_voice_pause_hotkey_armed`, `_on_voice_pause_press/_release`, `_set_voice_pause_setting`, `_begin_voice_pause_capture`, `_on_voice_pause_key_captured`, `_clear_voice_pause_hotkey` | 53276–53416 | SupervertalerQt | да | УДАЛИТЬ |
| `stop_voice_dictation_if_recording` | 53418–53455 | SupervertalerQt | да | УДАЛИТЬ |
| `start_voice_dictation` | 53457–53675 | SupervertalerQt | да | УДАЛИТЬ |
| `on_dictation_complete` / `_insert_dictated_text` | 53677–53755 | SupervertalerQt | да | УДАЛИТЬ |
| `on_dictation_status/_error/_finished` | 53757–53794 | SupervertalerQt | да | УДАЛИТЬ |
| `_resume_alwayson_after_dictation` | 53796–53814 | SupervertalerQt | да | УДАЛИТЬ |
| `on_model_loading_started/_finished` | 53816–53857 | SupervertalerQt | да | УДАЛИТЬ |
| `_dictation_shortcut_label` + `_set_dictation_button_recording` | 53859–53910 | SupervertalerQt | да | УДАЛИТЬ |
| `load_dictation_settings` / `save_dictation_settings` | 44095–44166 | SupervertalerQt | да (читатели только в 8.4-зоне; save — PROBABLY_DEAD ещё в Step 7) | УДАЛИТЬ |
| `load/save_voice_vocabulary_settings`, `build_voice_initial_prompt`, `_collect_voice_dictation_termbase_terms` | 44186–44305, 44339–44389 | SupervertalerQt | да | УДАЛИТЬ |
| `open_termbases_tab` | 44284–44304 | SupervertalerQt | сирота F1 (добавлена v1.10.31 для флажка voice-bias; 0 вызывающих после 8.3) | УДАЛИТЬ |
| `_migrate_voice_dictation_default_off` | 44306–44337 | SupervertalerQt | **НЕТ — миграция 8.8, вызов из `__init__` остаётся** | ОСТАВИТЬ |
| `_get_whisper_cache_path` | 57380–57386 | SupervertalerQt | читатель только closeEvent-гард | УДАЛИТЬ |
| `open_settings_to_keyboard_shortcuts` | 25285–25308 | SupervertalerQt | сирота F1 (ссылка была на вкладке Voice; 0 вызывающих) | УДАЛИТЬ |
| `_on_pynput_pushtotalk` / `_handle_pushtotalk_hotkey` | 66072–66117 | SuperlookupTab | да | УДАЛИТЬ |
| QShortcut `voice_dictate` | 7056–7069 | SupervertalerQt | да | УДАЛИТЬ |
| init-атрибуты `is_loading_model`, `loading_model_name`, `_voice_hotkey_listener`, `_voice_dictate_last_press_ms` | 6243–6254 | SupervertalerQt | да | УДАЛИТЬ |
| `voice_listener = None` (+комментарий) | 6414–6415 | SupervertalerQt | сирота interlock (читатели только 8.4-зона) | УДАЛИТЬ |
| `_alwayson_paused_by_external`, `_alwayson_was_running_before_dictation` | 53295–53348, 53498, 53804–53806 | SupervertalerQt | сироты (читатели только в удаляемых методах) | УДАЛИТЬ |
| closeEvent-гард «Voice Model Downloading» | 57172–57199 | SupervertalerQt | да | УДАЛИТЬ |
| Кнопки «🎤 Dictate»: грид-тулбар (создание + `self.tab_dictate_btn`) и нижняя панель вкладки (`editor_widget.dictate_btn`) | 27070–27101, 28269–28286 | SupervertalerQt | да | УДАЛИТЬ |
| Колонка «🎤 Voice» термбаз: комментарий v1.10.28, заголовок, `setColumnWidth(8)`, ячейка PurpleCheckmarkCheckBox, тултип, `on_voice_toggle` | 16829–16847, 17869–17895 | SupervertalerQt | да | УДАЛИТЬ (+сдвиг SuperLookup 9→8) |
| binding `pt` в `register_global_hotkey` (чтение/skip/дефолт/binding) + PTT-комментарий + докстринг | 65689–65786 | SuperlookupTab | да | УДАЛИТЬ ТОЛЬКО pt |
| `voice_dictate` запись + `_LEGACY_IDS`/`_GLOBAL_TO_MERGED` `global_pushtotalk` | shortcut_manager.py 188–195, 747, 828 | ShortcutManager | да | УДАЛИТЬ |
| Коммент. «НЕ удалять» у импорта QuickDictationThread | 348–349 | — | историческая оговорка; рекон: 0 ссылок вне 8.4-зоны, модуль удаляется по ТЗ | УДАЛИТЬ (обоснование в §7 п.6) |

### 1.2 Импортёры модулей-кандидатов

| Модуль | Импортёры | Решение |
|---|---|---|
| `voice_dictation_lite.py` (321) | монолит :347 (top-level) | **git rm** |
| `voice_release_poller.py` (310) | монолит :53187 (лениво, 8.4-зона) | **git rm** |
| `voice_vocabulary.py` (269) | монолит :44275 (8.4-зона); voice_dictation_lite:307 | **git rm** |
| `dictation_toast.py` (170) | монолит :53657 (лениво, 8.4-зона) | **git rm** |
| `mic_devices.py` (171) | voice_dictation_lite:125; в монолите только комментарий | **git rm** |
| `voice_hotkey_listener.py` (480, класс `GlobalHotkeyListener`) | монолит :53238, :53387 (обе — 8.4-зона) | **git rm** — СТОП-флаг проверен: остающиеся хоткеи Ctrl+Alt+L/Q/C идут через `GlobalHotkeyManager` из `modules/platform_helpers.py` (импорт в `register_global_hotkey`), класс `GlobalHotkeyListener` остающимися фичами не используется; `keyboard_shortcuts_widget.py` ссылок на voice не имеет (grep = 0) |

### 1.3 Карта колонок таблицы термбаз

ДО (10): `Type(0) Name(1) Languages(2) Terms(3) Read(4) Write(5) Project(6) AI(7) 🎤Voice(8) 🔍SuperLookup(9)`.
ПОСЛЕ (9): SuperLookup становится колонкой **8**.

Все обращения по индексам ≥8 (поиск по всей зоне `create_termbases_tab`…`_show_edit_terms_dialog` и по всему файлу):
`setColumnWidth(8/9)`, `setCellWidget(row,8/9)`, `cellWidget(row_idx,9)`, `cellWidget(r,9)` — все перенумерованы/удалены; обращения к колонкам 0–7 не менялись. Внешние пользователи `self.termbase_table` (Superlookup-навигация :64820) используют только колонку 1 (Name/UserRole). Импорт/экспорт/контекстное меню используют колонку 1.

Сохранённое состояние заголовков/ширин: `saveState/restoreState` и ключи ширин в коде **отсутствуют** (grep = 0) — ширины задаются заново при каждой постройке, старые пользовательские значения не сохраняются, ломаться нечему. Запись флага 🎤 шла через `set_termbase_voice_enabled` — метод слоя БД остаётся (ТЗ), UI-ячейка удалена.

### 1.4 Потребители вне кластера и ShortcutManager

* Неохраняемых обращений остающегося кода к удаляемым именам **не найдено** (защита 2, §4).
* `keyboard_shortcuts_widget.py` — правок не требует: grep `voice_dictate|Special|voice` = 0 (комментарий :408 — исторический, про Ctrl+Alt+A Always-On; док-остаток до конца Batch #8).
* Поведение при сохранённом пользовательском значении отсутствующего ID — по правилу 8.2/8.3: `get_shortcut` возвращает значение из `custom_shortcuts` ( orphan сохраняется в JSON, но ни один код его больше не читает); страница строится из `DEFAULT_SHORTCUTS` → строки нет; Ctrl+Shift+Space ничего не регистрирует (подтверждено пробой ПОСЛЕ).
* `modules/feature_manager.py` (запись «Voice (Commands & Dictation)») — не тронут: файл вне согласованного списка; grep показал 0 импортёров `FEATURE_MODULES` по всему репо (модуль сам по себе мёртвый — кандидат в отдельное решение, §8).
* `settings_service.py` — ссылок на диктовку нет (только исторический докстринг — док-остаток).

## 2. Что сделано

| Файл | Действие |
|---|---|
| Supervertaler.py | 67157 → **65961** строк (−1196): 12 contiguous-зон скриптом `remove_zones.py` (каждая с boundary-assertions по снимку ДО; −1133) + 15 хирургических правок (кнопки ×2 панели, импорт QuickDictationThread/PurpleCheckmarkCheckBox, колонка 🎤, сдвиг SuperLookup 9→8 ×3, register_global_hotkey ×5, устаревший комментарий :43732) |
| modules/shortcut_manager.py | −11: запись `voice_dictate` (+комментарий «# Special»), `'global_pushtotalk'` из `_GLOBAL_TO_MERGED` и `_LEGACY_IDS` |
| modules/voice_dictation_lite.py | **git rm** (321 строка) |
| modules/voice_release_poller.py | **git rm** (310) |
| modules/voice_vocabulary.py | **git rm** (269) |
| modules/dictation_toast.py | **git rm** (170) |
| modules/mic_devices.py | **git rm** (171) |
| modules/voice_hotkey_listener.py | **git rm** (480) |

Итого коммит: 8 файлов, +16/−2944. `_migrate_voice_dictation_default_off`, схема БД, методы `termbase_manager` (get/set_termbase_voice_enabled, get_voice_enabled_termbase_ids), ключи настроек, `PurpleCheckmarkCheckBox` (styled_widgets), HelpTopics, platform_helpers-докстринг, feature_manager — **не тронуты** (по ТЗ).

## 3. Диффы изменённых методов монолита до/после

| Метод | ДО | ПОСЛЕ |
|---|---|---|
| `SupervertalerQt.__init__` (зона менеджеров) | is_loading_model/loading_model_name, _voice_hotkey_listener, _voice_dictate_last_press_ms, voice_listener | удалены; `_migrate_voice_dictation_default_off()` вызов остался |
| `closeEvent` | гард «Voice Model Downloading» (29 строк) + гард несохранённых изменений | только гард несохранённых изменений |
| `register_global_hotkey` (SuperlookupTab) | чтение sl/qt/sk/cb/pt + skip ×4 + дефолты ×4 + PTT-комментарий/_log + binding 4 | sl/qt/sk/cb + skip ×3 + дефолты ×3 + binding 3; `pt_shortcut`/`_on_pynput_pushtotalk` = 0 (AST-подсчёт) |
| `create_grid_view_widget_for_home` | …AutoTagger → Dictate → «\|» → Log → stretch → Confirm&Next; `self.tab_dictate_btn` | …AutoTagger → «\|» → Log → stretch → Confirm&Next; без дыр и двойных разделителей |
| `create_assistance_panel` (панель вкладки) | Copy → Clear → Dictate (+`editor_widget.dictate_btn`) → stretch → Save → Confirm&Next | Copy → Clear → stretch → Save → Confirm&Next |
| `create_termbases_tab` | setColumnCount(10), 10 заголовков, 10 ширин, ячейки 7/8/9 | setColumnCount(9), 9 заголовков, 9 ширин, ячейки 7/8; SuperLookup=8 везде |
| ShortcutManager: `get_shortcut`/миграции | `_LEGACY_IDS`/`_GLOBAL_TO_MERGED` с global_pushtotalk | без global_pushtotalk; остальные legacy-мэппинги нетронуты |

Верификация переноса: хвост файла (последние 60 строк) байт-в-байт совпадает со снимком HEAD; `git diff --stat` = только 2 изменённых + 6 удалённых файлов.

## 4. Статическая валидация

| Проверка | ДО | ПОСЛЕ | Итог |
|---|---|---|---|
| py_compile (монолит + модули) | 132/132 | **126/126** (131−6 модулей) | OK |
| Защита 1: резолв стартовой цепочки | 934 / 0 unresolved | **925 / 0 unresolved** (−9 — вызовы из удалённого кода цепочки) | OK |
| Защита 2: grep 63 удалённых идентификаторов (`protection2_grep.py`, скрипт в стейдже; Supervertaler.py + modules/** + tools/**) | — | **1 допустимый остаток**: `PurpleCheckmarkCheckBox` в styled_widgets.py:112 (класс остаётся по ТЗ). Один устаревший комментарий монолита :43732 найден и исправлен в ходе проверки | OK |
| Защита 3: pyflakes undefined names | 149 (warnings 711) | **149, множество идентично** (warnings 699) | OK |
| AST: `register_global_hotkey` | — | pt/voice-упоминаний 0; sl/qt/cb по 4; pushtotalk-обработчика в bindings нет | OK |
| AST: карта колонок термбаз | 10 колонок, SuperLookup=9 | 9 колонок, SuperLookup=8, «🎤 Voice» в заголовках отсутствует; stray-обращений к колонке 9 нет | OK |
| AST: `save_general_settings()` без аргументов | 0 | 0 | OK |
| Offscreen-проба (изолированный профиль, `QT_QPA_PLATFORM=offscreen`, модали нейтрализованы, `PROBE OK` 13.3 c) | 7 вкладок; 16 страниц; Dictate=1; хоткеи c/l/q/**ctrl+shift+space**; таблица термбаз 10 колонок c «🎤 Voice» | 7 вкладок; 16 страниц; **Dictate=0**; хоткеи **c/l/q** (ctrl+shift+space больше не регистрируется); таблицы с «🎤 Voice» нет | OK |
| Доп-проба термбаз (`probe_termbase.py`, изолированный профиль) | — | `termbase_table cols=9 headers=[Type, Name, Languages, Terms, Read, Write, Project, AI, 🔍 SuperLookup]` | OK |
| Headless-импорт всех modules/** | 124/131 (8.3-after) | **118/125** — 118 = 124−6 удалённых; падения идентичны предсуществующим: find_replace, pdf_rescue_Qt, pdf_rescue_tkinter, prompt_library, setup_wizard, tracked_changes (tkinter/fitz), glossary_manager (NameError, предсуществующая находка 8.3 §7.7) | OK |
| EOL | w/crlf набор предсуществующий | без изменений | OK |
| git diff --stat | — | Supervertaler.py, modules/shortcut_manager.py + 6 удалённых — только согласованные файлы | OK |

БД-проба (изолированная БД профиля `iso-tb`, headless): `create_termbase("probe_tb84", en→ru)` → id=1; `add_term(house→дом)` OK; `get_terms` OK; `get_termbase_voice_enabled`/`set_termbase_voice_enabled` (слой БД остаётся по ТЗ) работают.

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: состояние после 8.3 (код `03308061`/файлы 8.3-пакета: Supervertaler.py `74b05eaf…`, shortcut_manager.py `c4f96d0a…`).
Файлы заменяются/удаляются в `<корень сборки>\SupervertalerPortable\`.

| № | Путь | Действие | SHA256 | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | ЗАМЕНИТЬ | `82cc599cd47b357d60d9b5c44ab1b11b1f548f788544ea3f5db0ff0d2eff58b3` | 65961 строк (рабочая копия репо, CRLF; git-blob LF = `6538e04b…`) |
| 2 | `modules\shortcut_manager.py` | ЗАМЕНИТЬ | `429bba4bb02cebbbc26ac94d29e0f6a3735f0faacf4624c954e77b8aeea7dca2` | без voice_dictate/global_pushtotalk |
| 3 | `modules\voice_dictation_lite.py` | **УДАЛИТЬ** | — | |
| 4 | `modules\voice_release_poller.py` | **УДАЛИТЬ** | — | |
| 5 | `modules\voice_vocabulary.py` | **УДАЛИТЬ** | — | |
| 6 | `modules\dictation_toast.py` | **УДАЛИТЬ** | — | |
| 7 | `modules\mic_devices.py` | **УДАЛИТЬ** | — | |
| 8 | `modules\voice_hotkey_listener.py` | **УДАЛИТЬ** | — | |

После замены перезапустить `start.bat`. `__pycache__` в сборке можно не чистить —
удалённые имена больше не импортируются.

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data тестовой сборки; сначала КОНТРОЛЬ на базовой сборке, затем после замены)

* **T8.4.1** Старт без исключений; 7 вкладок, Settings последняя.
* **T8.4.2** Нижняя панель сегмента (Status / Preview Prompts / AutoTagger / Log /
  Confirm & Next), панель грида и tab-редактор: кнопки Dictate нет, остальные
  кнопки на местах без «дыр» (контроль на baseline: Dictate есть).
* **T8.4.3** Вкладка Termbases: таблица без столбца «🎤 Voice»; создать термбазу,
  добавить/изменить/удалить термин; переключить AI-чекбокс; остальные столбцы
  (ширины, сортировка, контекстное меню) работают; открыть термбазу из копии
  user_data с ранее включённым флагом 🎤 — открывается без ошибок.
* **T8.4.4** Импорт и экспорт термбазы (TSV) — без исключений.
* **T8.4.5** AI-перевод с активной термбазой: Preview Prompts показывает термины
  термбазы в промпте (инжекция не затронута).
* **T8.4.6** Settings → Keyboard Shortcuts: строки «Voice dictation / push-to-talk»
  нет; Ctrl+Shift+Space ничего не вызывает; все Settings-страницы открываются.
* **T8.4.7** ГЛОБАЛЬНЫЕ ХОТКЕИ из другой программы: Ctrl+Alt+Q (выделить текст в
  Блокноте → попап QuickTrans) и Ctrl+Alt+L (вызов SuperLookup) работают как до
  батча.
* **T8.4.8** live-test: импорт файла 180/400 сегментов; перевод сегмента; Save;
  сохранение настройки после перезапуска; навигация по вкладкам.
* **T8.4.9** Выход: иконка трея исчезает, процесс завершается (флаки-краш
  0xC0000005 — предсуществующий, не считается).

## 7. Непокрытые проверки (честно)

1. **Живых прогонов приложения не было** (батч — статика + offscreen + headless):
   клики по таблице термбаз, сортировка щелчком по заголовку, контекстное меню,
   импорт/экспорт offscreen не эмулировались — закрываются T8.4.3–T8.4.5.
2. **Термбаза из user_data с включённым флагом 🎤**: статически путь проверен
   (чтение флага шло только в удалённой ячейке; `_refresh_termbase_list` не читает
   колонку voice), живой прогон на реальной копии — T8.4.3.
3. **Поведение Ctrl+Shift+Space в другой программе после батча**: статически
   binding удалён из `register_global_hotkey` и QShortcut-реестра; проба подтверждает
   отсутствие регистрации при старте; проверка из стороннего приложения — T8.4.6/8.4.7
   (клавиши offscreen не эмулируются).
4. **Вторая кнопка Dictate** (нижняя панель вкладки) строится в ветке, не
   выполняющейся при пустом профиле пробы — offscreen-проба ДО видела только 1 из 2
   кнопок; после удаления обе зоны вырезаны (grep `🎤 Dictate` = 0), живой контроль
   обеих панелей — T8.4.2.
5. **Стрелочные клавиши/повтор клавиши** (setAutoRepeat-логика QShortcut) ушли
   вместе с QShortcut; поведение остальных QShortcut не менялось.
6. **Удаление импорта QuickDictationThread вместе с историческим комментарием
   «НЕ удалять»**: комментарий утверждал возможный динамический импорт; рекон
   (AST + grep `QuickDictationThread` и `voice_dictation_lite` по Supervertaler.py,
   modules/**, tools/**) показал 0 ссылок вне 8.4-зоны и 0 строковых
   `getattr/importlib`-упоминаний — динамического пути нет. Осталось зафиксировать
   здесь как решение, отменяющее старую оговорку.
7. **`modules/feature_manager.py`** содержит запись фичи «Voice (Commands &
   Dictation)» (+ «Local Whisper») — файл вне согласованного списка правок и имеет
   0 импортёров `FEATURE_MODULES` во всём репо (сам по себе мёртвый); вопрос вынесен
   в §8.
8. Миграция `_migrate_voice_dictation_default_off` остаётся (8.8); при каждом старте
   пишет «✓ …reset to opt-in» только один раз (сентинела) — живое поведение не менялось.

## 8. Вопросы к Дмитрию

1. `modules/feature_manager.py`: запись `id="voice"` («Voice (Commands &
   Dictation)», pip_extra `voice`) и `id="local_whisper"` — модуль целиком не имеет
   ни одного импортёра (grep `FEATURE_MODULES` = 0). Снести обе записи в конце
   Batch #8, оставить, или отдать модуль под отдельное решение о мёртвом коде?
2. Тултип/комментарии в `styled_widgets.py` (`PurpleCheckmarkCheckBox`: «Termbase
   Manager → 🎤 Voice column») и `termbase_manager.py` (комментарии Voice-dictation
   biasing) теперь описывают удалённый UI. Класс и методы БД остаются по ТЗ; док-
   строки почистить в конце Batch #8 вместе с HelpTopics/platform_helpers?
3. Орфанные ключи (`ui.dictation_settings` с вложенными `voice_pause_hotkey` /
   `pushtotalk_mode` / `mic_device`, `voice_vocabulary`, `voice_commands.json`,
   `voice_scripts/`, миграции) — по плану 8.8/конец Batch #8. Подтверждаете, что
   `load/save_dictation_settings` и `load/save_voice_vocabulary_settings` сносить
   именно сейчас (сделано), а ключи в user_data не трогать?
