# Batch #8.5 — Удаление F2: Clipboard Manager, Этап 2

Дата: 2026-10-06. Исполнитель: Zcode. Кодовый коммит: `4988a0fb` — «Batch #8.5: remove Clipboard Manager (F2)» (пересобран amend-ом после ПРАВКИ к промпту: каскадные сироты snippet_library.py / text_conversion_library.py удаляются этим же батчем; исходный хэш до amend — `e62ea752`).
Порядок Batch #8: 8.1 ✓ → 8.2 ✓ → 8.3 ✓ → 8.4 ✓ → **8.5 ✓** → 8.7 → 8.10 → 8.8 → 8.9.

## 0. Baseline и git-синхронизация

| Проверка | Значение | Результат |
|---|---|---|
| git fetch origin | HEAD == origin/main == `cb6e7403` | OK |
| git status | чисто; untracked `.zcode/plans/…`, `.zcodeignore` (допустимы) | OK |
| Дрейф-чек | `git merge-base --is-ancestor bf821d0f HEAD` — предок | OK |
| SHA256 рабочей копии Supervertaler.py ДО | `82cc599cd47b357d60d9b5c44ab1b11b1f548f788544ea3f5db0ff0d2eff58b3` (65961 строка; = 8.4-after) | OK |
| Baseline файлов | modules/**/*.py = 125; py_compile монолита+модулей = **126/126** | OK |
| EOL до | Supervertaler.py i/lf **w/crlf**; shortcut_manager / keyboard_shortcuts_widget / settings_service / clipboard_manager_widget i/lf **w/lf** — предсуществующий набор | OK |

Базовые значения защит (стадийная папка `D:\Temp\SupervertalerPortable\refactoring\b8-5\`):

| Защита | ДО | Источник |
|---|---|---|
| 1. Резолв стартовой цепочки (AST; цепочка + `_setup_tray_icon`, `_on_main_tab_changed`) | 933 вызова, **0 неразрешённых** | `startup_chain_before.json` |
| 2. pyflakes undefined names | **149 вхождений, множество идентично 8.4-after** | `un_before_sorted.txt` |
| 3. Offscreen-проба ДО (изолированный профиль `iso-before`) | main_tabs **7** (вкл. «📋 Clipboard Manager»), страниц Settings **16** (вкл. «📋 Clipboard»), хоткеи **c/l/q** («Registering: ctrl+alt+l, ctrl+alt+q, ctrl+alt+c»), QTimer 3 / QThread 0, Clipboard-кнопок 0 (вкладка ленивая) | `probe_before.log` |

## 1. Рекон

### 1.1 Таблица имён (монолит — SupervertalerQt, если не указано иное; номера ДО = состояние 8.4-after)

| Имя | Место ДО | Вид | Класс self | Только F2? | Действие |
|---|---|---|---|---|---|
| `create_shortcut("sidekick_open_clipboard", "Ctrl+Shift+C", …)` + коммент | 7234–7235 | QShortcut-реестр | SupervertalerQt | да | удалено |
| `open_clipboard_tab` | 7507–7519 | метод | SupervertalerQt | да | удалён |
| `self._clipboard_top_widget = None`; placeholder-вкладка «📋 Clipboard Manager» (`clipboard_placeholder`, `clipboard_tab_index`) | 9925, 9932–9934 | init-атрибуты + вкладка | SupervertalerQt | да | удалены |
| elif-ветка Clipboard в `_on_main_tab_changed` | 11617–11618 | ветка | SupervertalerQt | да | удалена |
| `'_ensure_clipboard_top_tab'` в кортеже `_warm_up_top_tabs` | 11660–11661 | элемент кортежа | SupervertalerQt | да | удалён (остался 1 helper) |
| `_ensure_clipboard_top_tab` (lazy-импорт `modules.clipboard_manager_widget`) | 11747–11785 | метод | SupervertalerQt | да | удалён |
| регистрация страницы «📋 Clipboard» в `create_settings_tab` | 20325–20327 | вызов + addTab | SupervertalerQt | да | удалена |
| `_create_clipboard_settings_tab` (стр. 23262–23492; читает `ClipboardManagerWidget.DEFAULT_PRIVACY` :23291 и `COMMON_SECRET_APPS` :23466) | 23262–23492 | метод | SupervertalerQt | да | удалён |
| `open_workbench_to_clipboard(source_window=None)` | 25121–25211 | метод | SupervertalerQt | да | удалён |
| пункт трея `jump_clipboard` «Open Clipboard» (`_make_jumper('clipboard_tab_index')`) | 28664–28666 | QAction в `_setup_tray_icon` | SupervertalerQt | да | удалён |
| `clipboard_idx` + in-Workbench return path + focus-затвор + финальная ветка в `_on_esc_quick_lookup_dismiss` | 28782, 28791–28817, 28819–28856, 28858–28862 | ветки | SupervertalerQt | да (SuperLookup-ветка осталась) | удалены |
| Clipboard-элемент кортежа `quick` в `keyPressEvent`-fallback | 28879–28880 | ветка | SupervertalerQt | да | удалён |
| `_dismiss_clipboard_summon` | 28894–28937 | метод | SupervertalerQt | да | удалён |
| `load_clipboard_privacy_settings` (делегат SettingsService) | 43774–43782 | метод | SupervertalerQt | да | удалён |
| `save_clipboard_privacy_settings` (+ live-refresh `_clipboard_top_widget`) | 43784–43805 | метод | SupervertalerQt | да | удалён |
| `cb_shortcut` чтение/skip/дефолт/binding в `register_global_hotkey` | 64593, 64603, 64607, 64638 | фрагменты | **SuperlookupTab** | да (sl/qt не затронуты) | удалены |
| `_on_pynput_clipboard` | 64709–64718 | метод | SuperlookupTab | да | удалён |
| `_handle_clipboard_hotkey` (+ отправка синтетического Ctrl+C, polling sequence number) | 64720–64856 | метод | SuperlookupTab | да | удалён |
| `_open_clipboard_after_copy` (in-Workbench детект, `_clipboard_prior_*`) | 64858–64922 | метод | SuperlookupTab | да | удалён |
| служебные: `_clip_summon_t0`, `_clip_summon_copy_ms`, `_clipboard_prior_workbench_tab`, `_clipboard_prior_focused_widget`, `_clipboard_settings_loading`, `_continue_clipboard` (замыкание) | внутри удалённых зон | атрибуты/замыкания | — | да | удалены вместе с зонами |

Привязка всего кластера Ctrl+Alt+C к `SuperlookupTab` подтверждена AST (`recon_owners.py`); записи вида `mw._clipboard_prior_*` пишутся только из `_open_clipboard_after_copy`, читаются только из `_on_esc_quick_lookup_dismiss` — оба удалены.

### 1.2 Ctrl+Alt+C (B7) — точное место регистрации

* Регистрация — НЕ в modules/superlookup.py: `SuperlookupTab.register_global_hotkey` живёт в монолите (64553–64678 ДО). modules/superlookup.py упоминает буфер обмена только в собственном захвате выделения SuperLookup (код `_capture_selected_text` и т.п.) — **не тронуто**.
* Цепочка: `register_global_hotkey` читает `sm.get_shortcut('sidekick_open_clipboard')` → binding `(cb_shortcut, self._on_pynput_clipboard)` → `QTimer.singleShot(0, _handle_clipboard_hotkey)` → `_open_clipboard_after_copy` → `open_workbench_to_clipboard`.
* Кастомный хоткей пользователя: ShortcutManager хранит кастом по id `sidekick_open_clipboard`; сам файл settings пользователя не трогался (ключ остаётся, но никто его не читает — сирота, см. §1.8). `_GLOBAL_TO_MERGED`/`_LEGACY_IDS`-строки `global_clipboard` удалены (правило отсутствия ID доказано в 8.2–8.4: `get_shortcut` по отсутствующему id вернул бы дефолт из DEFAULT_SHORTCUTS — записи там тоже больше нет; обращений по этому id вне удалённого кода 0).
* Удаление затронуло только cb: AST-проверка — binding-переменные после = `qt_shortcut, sk_shortcut, sl_shortcut`, pynput-обработчики = `_on_pynput_quicktrans, _on_pynput_superlookup`.

### 1.3 Мониторинг буфера обмена

* Подписка `QApplication.clipboard().dataChanged` живёт **внутри виджета** (`clipboard_manager_widget.py:706`), стартует при его конструировании; виджет создаётся лениво (`_ensure_clipboard_top_tab` / warm-up). Таймеры автозачистки (`_purge_timer` :199, `_preview_timer` :325) — тоже внутри виджета.
* В монолите мониторинга нет: `dataChanged` упоминается только в комментариях удалённых обработчиков (64772/64809/64842 ДО). closeEvent/трей ссылок на clipboard-мониторинг не имели (grep до правок = 0 вне кластера).
* Offscreen-проба: QTimer 3 → 3, QThread 0 → 0 (виджет в пробе ДО не строился — вкладка ленивая; после удаления строить его нечему). Висящих слушателей нет.

### 1.4 Импортёры

`modules/clipboard_manager_widget.py` импортировался только из монолита: lazy-вкладка (:11759 ДО) и Settings-страница (:23283 ДО). Других импортёров нет (grep по репо). Модуль: 2531 строки, класс `ClipboardManagerWidget(QWidget)` — 3-колоночный менеджер истории буфера (текст/изображения), сниппеты, текстовые конвертации, промпты; БД `clipboard_history` через DatabaseManager; paste-back через CrossPlatformKeySender/AHK.

### 1.5 Каскадные сироты (ПРАВКА к промпту: УДАЛЯЮТСЯ этим же батчем; описания — для восстановления из истории)

* **modules/snippet_library.py** (282 строки; удалён `git rm`). Назначение: файловое хранилище сниппетов — `.md`-файлы под `<user_data>/snippet_library/` (папка = категория, имя файла = подпись, тело = вставляемый текст; опциональный front-matter `name:` перекрывает подпись). Формат данных: `<user_data>/snippet_library/**/*.md` (+ опциональный YAML-frontmatter `--- name: … ---`). Публичный API: `class SnippetLibrary` (`load_all() -> int`, `ensure_defaults(default_defs) -> int`), константа `DEFAULT_SNIPPETS: List[Dict]`, приватный `_split_front_matter`. Импорты: pathlib/typing/re (stdlib only). Единственный потребитель — clipboard_manager_widget (ленивые импорты 1564/1705/1813 ДО). Коммит-родитель: **`13bd37fb`** («baseline before extraction batch 1» — файл добавлен им и больше не менялся).
* **modules/text_conversion_library.py** (442 строки; удалён `git rm`). Назначение: файловые текстовые конвертации — `.md`-файлы под `<user_data>/text_conversion_library/` с YAML-frontmatter, декларирующим тип (`case`/`wrap`/`regex_replace`/`strip_chars`), параметры и метаданные (`label`/`category`/`enabled`); структура зеркалит snippet_library. Формат данных: `<user_data>/text_conversion_library/**/*.md` с YAML-frontmatter. Публичный API: `class TextConversion` (`apply(text) -> str`), `class TextConversionLibrary` (`load_all() -> int`, `ensure_defaults(default_defs) -> int`), константа `DEFAULT_CONVERSIONS: List[Dict]`. Импорты: re/pathlib/typing/**yaml**. Единственный потребитель — clipboard_manager_widget (ленивый импорт 1881 ДО). Коммит-родитель: **`13bd37fb`** (аналогично — добавлен и не менялся).
* Восстановление из истории: `git show 13bd37fb:modules/snippet_library.py` / `git show 13bd37fb:modules/text_conversion_library.py`.
* СТОП-флаг (какой-либо ДРУГОЙ остающийся модуль импортирует сирот): проверен на финальном состоянии — **0 импортёров** (grep по Supervertaler.py, modules/**, tools/**; совпадения только внутри самих удалённых файлов).

### 1.6 Индексы вкладок/страниц

* `clipboard_tab_index` создавался как `main_tabs.count()-1`; навигация: `_switch_main_tab`/`_switch_settings_subtab`/`_open_mt_settings` — **по подписям** (label-based, v1.10.161), `jump_*` в трее — через `_make_jumper(attr_name)` + getattr; `settings_tab_index`/`superlookup_tab_index` — динамические `count()-1`; `mt_quick_lookup_tab_index` — `count()-1` после вставки. Жёстких числовых `setCurrentIndex(n)` на `main_tabs`/`settings_tabs` в монолите нет (AST-обход: только `setCurrentIndex(0)` на main_tabs — старт на Grid, без изменений).
* Восстановление последней вкладки при старте отсутствует (подтверждено в 8.3).

### 1.7 ShortcutManager / keyboard_shortcuts_widget

* DEFAULT_SHORTCUTS: запись `sidekick_open_clipboard` (588–594 ДО) удалена; «Open Clipboard manager» исчезнет из Settings → Keyboard Shortcuts автоматически (список строится из DEFAULT_SHORTCUTS).
* `_GLOBAL_TO_MERGED` (:737) и `_LEGACY_IDS` (:817): `'global_clipboard': 'sidekick_open_clipboard'` удалены.
* One-time миграция дефолта Ctrl+Shift+C → Ctrl+Alt+C (`_CLIP_MIGRATION = 'clipboard_default_ctrlaltc_v1'`, 762–781 ДО) удалена целиком — обслуживала только удалённый id. Маркер в пользовательском shortcuts-файле остаётся (данные не трогаем).
* keyboard_shortcuts_widget: заголовок группы «⌨️ Global Hotkeys (Superlookup && QuickTrans)», инфо-текст без Clipboard (пользовательские строки — не док-остатки; T8.5.4). Докстринг `_reload_global_hotkeys_on_main_window` (:659, упоминает Clipboard/push-to-talk) — док-остаток, чистка в конце Batch #8.

### 1.8 Данные (только описание, ничего не удаляется)

* БД: таблица `clipboard_history` и все методы database_manager (3213–3360 ДО) — **не тронуты**; миграции database_migrations.py (Migration 5, image-колонки) — не тронуты; offscreen-проба после показывает «Creating clipboard_history table…» как раньше.
* Ключ настроек `features.clipboard_privacy` — остаётся в пользовательском settings.json (сирота; инвентаризация в конце Batch #8 / 8.8).
* Папки `<user_data>/snippet_library/`, `<user_data>/text_conversion_library/` — данные, не тронуты.
* Маркер `clipboard_default_ctrlaltc_v1` в shortcuts-файле и кастом `sidekick_open_clipboard` — данные, не тронуты.

### 1.9 Потребители вне кластера и охрана

Все оставшиеся ссылки на «clipboard» в монолите (70 упоминаний) — либо легитимные использования API буфера (QuickLauncher `behavior="clipboard"`, копирование TM-статистики/version-info, захват выделения SuperLookup/QuickTrans), либо док-остатки в комментариях/докстрингах нетронутого кода (9068, 9847, 9886, 9925, 24579, 24641, 25849, 27274, 54214 и др.) — чистка в конце Batch #8 (решение Дмитрия из 8.4). Ни один остающийся код не обращается к удалённым именам (Защита 2); СТОП-флагов нет.

## 2. Что сделано

| Файл | Действие |
|---|---|
| `Supervertaler.py` | 65961 → **65163** строк (−798): 7 contiguous зон среза (remove_zones.py, нисходящий порядок, SHA-guard `82cc599c…`, якоря с проверкой) + 14 точечных Edit-правок (§1.1); docstring-обновления правленых методов (`_warm_up_top_tabs`, `_on_esc_quick_lookup_dismiss`, `register_global_hotkey`, коммент-блок Unified Settings) |
| `modules/clipboard_manager_widget.py` | **git rm** (2531 строки) |
| `modules/snippet_library.py` | **git rm** (282 строки; каскадная сирота — ПРАВКА к промпту) |
| `modules/text_conversion_library.py` | **git rm** (442 строки; каскадная сирота — ПРАВКА к промпту) |
| `modules/shortcut_manager.py` | −20 строк (1118 → 1098): DEFAULT_SHORTCUTS-запись, `_GLOBAL_TO_MERGED`, миграция `_CLIP_MIGRATION`, `_LEGACY_IDS` |
| `modules/keyboard_shortcuts_widget.py` | −7/+6: заголовок и инфо-текст группы Global Hotkeys без Clipboard (qm_key удалён) |
| `modules/settings_service.py` | метод `load_clipboard_privacy_settings` удалён (−10); док-комментарии модуля/блока обновлены; остальные сигнатуры не менялись |

Коммит `4988a0fb`: 7 файлов changed, +44/−4136 (вкл. удаление виджета и двух сирот).

## 3. Диффы изменённых методов монолита (до/после)

* `SupervertalerQt._on_main_tab_changed` (11606–11636 →): остался SuperLookup-ensure + Grid/Project-resources ветки; elif-ветка Clipboard удалена; коммент «SuperLookup / Clipboard» → «SuperLookup».
* `SupervertalerQt._warm_up_top_tabs` (11645–11671 →): кортеж helpers = `('_ensure_superlookup_top_tab',)`; `_prewarm_ahk` остаётся (решение 8.4 — keep; CrossPlatformKeySender используется SuperLookup/QuickTrans-путями захвата); докстринг переписан без Clipboard.
* `SupervertalerQt._on_esc_quick_lookup_dismiss` (28736–28862 → 28344–…): осталась только SuperLookup-ветка (unconditional hide при наличии трея); семантика для не-quick-lookup вкладок не изменилась (ранее фоллбэк «ничего не делать» — теперь явный выход); docstring обновлён с пометкой об удалении ветки в 8.5.
* `SupervertalerQt.keyPressEvent` (28864–28892 →): кортеж `quick` без clipboard_tab_index; поведение: Esc на SuperLookup — dismiss, на остальных — super().
* `SuperlookupTab.register_global_hotkey` (64553–64678 →): чтение/skip/дефолт/binding cb удалены; sl/qt/sk и структура (WinAPI → AHK-fallback) не тронуты; docstring «Superlookup, QuickTrans и Sidekick».
* `SupervertalerQt._setup_tray_icon`: «Open Clipboard» удалён между «Open SuperLookup» и «Open Settings»; разделители не тронуты.
* Esc-QShortcut-биндинг окна (9960–9984 ДО) — **не тронут** (SuperLookup-путь).

## 4. Статическая валидация

| Проверка | ДО | ПОСЛЕ | Результат |
|---|---|---|---|
| py_compile | 126/126 | **123/123** (123 файла: монолит + 122 модуля после git rm виджета и двух сирот) | OK |
| Защита 1: резолв стартовой цепочки | 933 / 0 неразрешённых | **912 / 0** (`startup_chain_after.json`) | OK |
| Защита 2: grep удалённых имён | — | **0 живых ссылок**; в список добавлены имена сирот и их публичные классы (`snippet_library`, `text_conversion_library`, `SnippetLibrary`, `DEFAULT_SNIPPETS`, `_split_front_matter`, `TextConversion`, `TextConversionLibrary`, `DEFAULT_CONVERSIONS`) — 0 совпадений вне удалённых файлов; остатки живых имён виджета = 7 строк-комментариев, документирующих удаление (`settings_service.py:35,53,56,165,166`, `Supervertaler.py:43195`, `shortcut_manager.py:755`) | OK |
| Защита 3: pyflakes | 699 warnings / 149 undefined | 696 warnings / **множество undefined идентично (149)** | OK |
| AST: register_global_hotkey | bindings sl/qt/cb | **sl/qt/sk без cb**; обработчики `_on_pynput_superlookup/_quicktrans` | OK |
| AST: числовые индексы | — | setCurrentIndex с литералом на main_tabs/settings_tabs: только `main_tabs(0)` (старт на Grid); остальные — комбобоксы/подвкладки вне навигации | OK |
| AST: целостность методов | — | `_on_main_tab_changed`, `_warm_up_top_tabs`, `_on_esc_quick_lookup_dismiss`, `keyPressEvent` на месте; `save_general_settings()` без аргументов — 0 вызовов | OK |
| Offscreen-проба (изолированный профиль) | 7 вкладок / 16 страниц / c-l-q | **6 вкладок** [Editor, TMs, Termbases, AI, SuperLookup, Settings], Settings последняя; **15 страниц** (Clipboard нет); хоткеи **l/q** («Registering: ctrl+alt+l, ctrl+alt+q»); QTimer 3→3, QThread 0→0; Clipboard-кнопок 0; миграция clipboard_history в БД проходит как раньше; контрольный повтор после удаления сирот (`probe_after2.log`) — идентичен | OK |
| Headless-импорт modules/** | 118/125 (8.4-after) | **115/122** — падения идентичны предсуществующим (find_replace, pdf_rescue_Qt, pdf_rescue_tkinter, prompt_library, setup_wizard, tracked_changes — tkinter/fitz; glossary_manager — NameError 8.3 §7.7); новых нет | OK |
| 8 метрик (git grep HEAD → grep рабочей копии) | connect 1138 / QShortcut 15 / create_shortcut 33 / QTimer 24 / timeout.connect 24 / QTimer.timeout 0 / singleShot 79 / invokeMethod 2 | 1111 / 15 / 32 / 21 / 21 / 0 / 71 / 2 — дельты attributable: widget-connects, −1 create_shortcut (sidekick_open_clipboard), −3 QTimer/timeout (таймеры виджета), −8 singleShot (кластер _handle_clipboard_hotkey) | OK |
| EOL | набор ДО | без изменений (Supervertaler.py w/crlf, остальные w/lf) | OK |
| git diff --stat | — | Supervertaler.py, shortcut_manager.py, keyboard_shortcuts_widget.py, settings_service.py + удалённый clipboard_manager_widget.py — только согласованные файлы | OK |

Швы всех 7 зон проверены визуально (def-строки соседей на месте, без пустых дыр и двойных blank-блоков); снапшоты блоков сняты из HEAD-состояния с SHA256 (`snapshots/`).

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: состояние после 8.4 (код `bf821d0f`; Supervertaler.py `82cc599c…`, shortcut_manager.py `429bba4b…`).
Файлы заменяются/удаляются в `<корень сборки>\SupervertalerPortable\`.

| № | Путь | Действие | SHA256 | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | ЗАМЕНИТЬ | `f65e0e59bf24d992baab6060994f11cf518ac4b53f4ea2f0dedabc20cda05930` | 65163 строк (рабочая копия репо, CRLF; git-blob LF = `e05139f49aab834e74d48af00a13301bd4d065a1b8aad24da7f0aa396f98742c`) |
| 2 | `modules\shortcut_manager.py` | ЗАМЕНИТЬ | `c0b3ec61dd9a477610ed9752825f6cac8ecac9feaac1b84f25139d1c4cb6604e` | без sidekick_open_clipboard/global_clipboard/_CLIP_MIGRATION |
| 3 | `modules\keyboard_shortcuts_widget.py` | ЗАМЕНИТЬ | `dea11021a61ed62fb500905f5a7ef414c303a402a06f44232e43a920f97c6609` | Global Hotkeys: Superlookup && QuickTrans |
| 4 | `modules\settings_service.py` | ЗАМЕНИТЬ | `c8e7a6e1b25628059d3bfa4d46f2557a8d2e8d9ce70c2205e5fad41c2ba1a5dc` | без load_clipboard_privacy_settings |
| 5 | `modules\clipboard_manager_widget.py` | **УДАЛИТЬ** | — | единственный файл F2 |
| 6 | `modules\snippet_library.py` | **УДАЛИТЬ** | — | каскадная сирота (ПРАВКА к промпту); данные `<user_data>\snippet_library\` НЕ удалять |
| 7 | `modules\text_conversion_library.py` | **УДАЛИТЬ** | — | каскадная сирота (ПРАВКА к промпту); данные `<user_data>\text_conversion_library\` НЕ удалять |

После замены перезапустить `start.bat`. `__pycache__` можно не чистить — удалённое имя больше не импортируется.

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data тестовой сборки; сначала КОНТРОЛЬ на базовой сборке, затем после замены)

* **T8.5.1** Старт без исключений; панель вкладок: 6 вкладок (Editor, TMs, Termbases, AI, SuperLookup, Settings), Settings последняя (контроль на baseline: 7 вкладок с «📋 Clipboard Manager»).
* **T8.5.2** Все вкладки и ВСЕ страницы Settings открываются; страницы «📋 Clipboard» нет.
* **T8.5.3** Меню Workbench-трея: «Open Clipboard» нет; «Open SuperLookup», «Open Settings», «Close to tray…», «Start minimized…» работают.
* **T8.5.4** Хоткеи: Ctrl+Alt+C из другой программы ничего не вызывает (контроль на baseline: вызывает Clipboard summon); Ctrl+Alt+Q (QuickTrans) и Ctrl+Alt+L (SuperLookup) из Блокнота работают как до батча; Ctrl+Shift+C в окне ничего не вызывает; Settings → Keyboard Shortcuts: строк «Open Clipboard manager» нет, группа «Global Hotkeys» без упоминания Clipboard.
* **T8.5.5** Esc в SuperLookup (скрытие в трей) и в редакторе (естественное поведение) — без исключений; быстрое закрытие Lookup работает.
* **T8.5.6** Копия user_data с историей clipboard_history и папкой snippet_library: приложение открывается без ошибок (схема БД не тронута, миграции проходят).
* **T8.5.7** live-test: импорт файла 180/400 сегментов; перевод сегмента; Save; сохранение настройки после перезапуска; навигация по вкладкам.
* **T8.5.8** Выход: иконка трея исчезает, процесс завершается (флаки-краш 0xC0000005 — предсуществующий, не считается).

## 7. Непокрытые проверки (честно)

1. **Живых прогонов приложения не было** (батч — статика + offscreen + headless): клики по меню трея, Esc-сценарии в реальном фокусе, summons из сторонних приложений offscreen не эмулируются — закрываются T8.5.3–T8.5.5.
2. **Трей в offscreen-пробе недоступен** (`isSystemTrayAvailable()=False`) — факт наличия/отсутствия пункта «Open Clipboard» проверен статически (удаление 3 строк QAction) и живым прогоном T8.5.3.
3. **Поведение Ctrl+Alt+C в другой программе**: статически binding удалён из `register_global_hotkey` (AST) и проба подтверждает отсутствие регистрации; клавиши offscreen не эмулируются — T8.5.4.
4. **Кастомный хоткей пользователя на sidekick_open_clipboard**: пользовательский shortcuts-файл не трогался; после батча запись сиротская (не читается никем). Если у кого-то кастом остался — он молча игнорируется; инвентаризация сирот — конец Batch #8.
5. **Esc на вкладке SuperLookup при отсутствии трея**: прежний код возвращал `return` в обеих ветках — поведение не менялось; живой контроль T8.5.5.
6. **`_prewarm_ahk` остаётся** (решение 8.4): прогрев AHK теперь обслуживает только пути захвата/вставки SuperLookup/QuickTrans; докстринг обновлён.
7. **Док-остатки**: ~20 упоминаний «Clipboard» в комментариях/докстрингах нетронутого кода монолита (список в §1.9) + докстринг `_reload_global_hotkeys_on_main_window` + `HelpTopics.CLIPBOARD` (help_system.py:167; справочная страница остаётся) — чистка в конце Batch #8 по решению Дмитрия.

## 8. Вопросы к Дмитрию

1. **Пункт трея «Open Clipboard» / вкладка / Settings-страница** — подтверждаете полное удаление (сделано) без замещающего поведения (например, «Open Clipboard»-аналога не оставляли)?
2. **Данные clipboard_history** (таблица БД, миграции, ключ `features.clipboard_privacy`, маркер миграции в shortcuts-файле) и **папки данных** `<user_data>/snippet_library/`, `<user_data>/text_conversion_library/` — по плану не тронуты (папки данных остаются как пользовательские данные; модули-обработчики удалены); подтверждаете, что чистка данных — за пределами Batch #8 (инвентаризация сирот в конце)?
