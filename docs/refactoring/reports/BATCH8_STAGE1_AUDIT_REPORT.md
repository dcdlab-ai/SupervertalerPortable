# Batch #8, Этап 1 — Read-only аудит зависимостей для удаления фич F1–F6

Дата: 2026-10-02. Исполнитель: ZCode (GLM). Режим: только статический анализ (git, AST, grep); приложение не запускалось, user_data не затронут.
Рабочие скрипты и сырые данные: `D:\Temp\SupervertalerPortable\refactoring\b8-s1\` (вне репозитория):
- `ast_map.json`, `ast_map.py` — AST-карта монолита (классы/методы/границы);
- `main.txt`, `init.txt`, `create_main_layout.txt`, `top_tabs.txt`, `create_menus.txt`, `tray.txt`, `alwayson_tray.txt`, `global_shortcuts.txt`, `create_settings_tab.txt`, `switch_tabs.txt`, `f1_*.txt` — дампы методов с номерами строк;
- `notes_stage0_1.md`, `notes_stage2_4.md` — сырые инвентари по этапам.

---

## 5. BLOCKER-и и неохраняемые зависимости (читать первым)

Блокирующих остановок нет: дрейфа нет, py_compile 138/138. Ниже — точки, где удаление «в лоб» ломает ОСТАЮЩИЙСЯ код (все — предупреждения для Этапа 2, не останов работы):

| # | Зависимость | Кто потребляет (остающийся код) | Доказательство | Риск |
|---|---|---|---|---|
| B1 | `get_translator_name()` / ключ `general.translator_name` (страница «User Identity», F3-слой III) | TMX Editor (`Supervertaler.py:10204` `tmx_editor.translator_name = ...`), автор DOCX-комментариев `_comment_author_and_initials` `:13788`, автор в 53609, QuickLauncher-путь 7496, F3-слой II 38244/38851 | grep `translator_name`, вывод в §2.F3-III | Если удалить страницу вместе с `get_translator_name` — падение экспорта TMX/комментариев. Решение: метод оставить (фолбэк — системное имя пользователя), удалить только страницу Settings |
| B2 | `modules/trados_bridge_client.py` (F3-слой I) | ОСТАЮЩИЕСЯ `modules/chat_view_widget.py:23-29` (`TradosBridgeClient.shared()`, `TradosBridgePoller.shared()`, чип «🔗 Trados»), `modules/unified_prompt_manager_qt.py` | grep importers | Модуль не удалять без решения по Chat-интеграции |
| B3 | `_reinitialize_with_new_data_path()` (6665–6728) — формально рядом с F5 | Settings → General → смена папки данных `:22869`, диалог `:6643` | sed-дампы | Метод остаётся; удаляется только `_show_setup_wizard` и пункт меню |
| B4 | `PyQt6-WebEngine` (requirements) | После удаления F4 остаётся нужен: `SuperlookupTab.create_web_resources_tab` `:63296+` (QWebEngineView/Profile, `:63303-63354`), вкладка «🌐 Web Resources» `:62816` | grep WebEngine | Пакет из сборки НЕ исключать |
| B5 | `pynput` | `modules/platform_helpers.py` (GlobalHotkeyListener), `modules/superlookup.py`, `modules/keyboard_shortcuts_widget.py` — всё остаётся | grep pynput | Не исключать из requirements |
| B6 | `create_main_layout` → `self._setup_superlookup_hotkeys()` `:9975` — без try/except вся цепочка `__init__` падает насмерть при любом исключении (см. §1.4) | вся стартовая цепочка | дампы main/init | Шаблон осторожности при Этапе 2: не оставлять висячих ссылок внутри `create_main_layout` |
| B7 | Глобальный хоткей `Ctrl+Alt+C` «Clipboard summon» регистрируется `SuperlookupTab` (остаётся), путь `open_workbench_to_clipboard` `:25916` ведёт на F2-вкладку | `modules/superlookup.py` → монолит | дамп 25916–26006 | При удалении F2 путь в SuperLookup нужно перенаправить/убрать в том же под-батче |
| B8 | `_warm_up_top_tabs` `:11770` вызывает `_ensure_voice_top_tab`/`_ensure_clipboard_top_tab` по строковым именам через `getattr(self, helper, None)` | монолит | дамп 11785–11793 | При удалении методов warming молча пропустит (низкий риск), но вызовы надо убрать вместе с фичей |

Защищённые (охрана hasattr/getattr/try) потребители вкладок SuperLookup/Clipboard/Voice: `_on_main_tab_changed:11738-11743`, tray-jumpers `:29508-29536`, `_open_voice_in_workbench:25595-25598`, хоткейные пути `:25880/25945`, `_on_esc_quick_lookup_dismiss:29637-29640`, лямбда хоткея `:7297-7301`, closeEvent `:29881-29905` — при удалении вкладок они деградируют молча, а не падают.

---

## 0. Baseline и git-синхронизация

| Параметр | Значение |
|---|---|
| git fetch origin | выполнен, без новых объектов |
| HEAD | `8963e05e114ddd300dfb05ae032b99711f262913` |
| origin/main | `8963e05e114ddd300dfb05ae032b99711f262913` (совпадает) |
| git status | чисто; untracked только `.zcode/plans/plan-sess_49142aaa-….md` (допустимо) |
| git log -8 | `8963e05e` U1 manifest … `426a09e2` U1.4b … `5c052c9d` U1.4a |
| Дрейф-чек | `git merge-base --is-ancestor 426a09e2 HEAD` → OK (предок). Обратного дрейфа НЕТ |
| `wc -l Supervertaler.py` | **68265** строк |
| modules/**/*.py | **137** файлов (с монолитом 138) |
| py_compile | **138/138 OK** (pyc писались во временную папку; `cfile='NUL'` на Windows не работает — артефакт окружения, не кода) |
| SHA256 Supervertaler.py | `5080fd5b4e6a5bdd58cc5b2a45f4d8c248578ec20c6eb1eae006dbc455d573d2` |
| SHA256 modules/settings_service.py | `4770acaab14d1706ba05a335c7fbcf80f0479fac52b7b05a19099f909f874e32` |

AST-карта: 18 классов, 28 top-level функций; `SupervertalerQt` — 822 метода, строки 6055–62333 (`ast_map.json`).

---

## 1. Запуск и связность вкладок

### 1.1 Последовательность старта

| Шаг | Метод | Условие | Что создаёт/назначает |
|---|---|---|---|
| 1 | `main()` 68006 | `--batch`/`--translate-sdlxliff` в argv | CLI-режим batch-offload (Trados), выход до GUI |
| 2 | `_setup_diagnostic_log`/`_install_log_hooks` 68017-68019 | всегда | журнал; WebEngine-переменные `QTWEBENGINE_CHROMIUM_FLAGS` 68038, `QT_LOGGING_RULES` 68042, `StderrFilter` 68046 (глушение `js:`-шума WebEngine — след F4/WebEngine, но ставится безусловно и безвреден) |
| 3 | `AA_ShareOpenGLContexts` 68083 | всегда | требование QtWebEngine (комментарий в коде) — общий стартовый код |
| 4 | `SupervertalerQt()` 68230 | всегда | см. шаги 5–17 |
| 5 | `__init__` 6067: state, UndoManager, `needs_first_run_data_dialog()` 6289 → `self._needs_data_location_dialog` | — | гейт первого запуска |
| 6 | `get_user_data_path()` 6299, `SettingsService(user_data/'workbench'/'settings')` 6306 | — | единый IO настроек |
| 7 | `user_data_path.mkdir` 6331 | если НЕ первый запуск | каталог данных |
| 8 | `_migrate_settings_to_unified()` 6337 + `_migrate_to_workbench_layout()` 6338 | если НЕ первый запуск | **F6** |
| 9 | `_load_language_pair_from_disk()` 6348, `DatabaseManager.connect()` 6358 | если НЕ первый запуск | — |
| 10 | TMDatabase, TMMetadataManager, внешний TM-таймер QTimer(5000) 6379-6382 | всегда | остаётся |
| 11 | `TermbaseManager` 6386, `_migrate_voice_dictation_default_off()` 6399 | всегда (sentinel внутри) | **F6/F1** |
| 12 | `VoiceCommandManager(self, main_window=self)` 6417; `voice_listener=None` 6420 | всегда | **F1** |
| 13 | `init_ui()` 6433 → create_menus 8538 → **create_main_layout** 9838 → status bar, `_setup_progress_indicators` (в нём `alwayson_indicator_label` 8222-8228 — **F1**), `setup_global_shortcuts` 7038 | всегда | см. 1.2 |
| 14 | `_ensure_alwayson_tray_icon()` 6475 | всегда | **F1** — иконка трея Always-On создаётся на каждом старте |
| 15 | load_general/language_settings, restore_last_project, `_init_usage_statistics`, okapi deferred | всегда | — |
| 16 | `QTimer.singleShot(2500, self._warm_up_top_tabs)` — в `create_main_layout` 10082 | всегда | прогрев SuperLookup/Clipboard/Voice + `_prewarm_ahk` (**вместо упомянутого в задаче autoload-механизма — его в коде больше нет**, см. 1.6) |
| 17 | первый запуск: `QTimer.singleShot(300, _show_setup_wizard)` 6540-6542 | `_needs_data_location_dialog or not first_run_completed` | **F5** |
| 18 | `main()`: `_load_settings_section("ui")` 68236, `window.show()`, `_setup_tray_icon()` 68244, `app.exec()` | всегда | Workbench-трей |

### 1.2 Вкладки главного окна (`main_tabs`, create_main_layout 9838–10086)

| # | Метка | Создание | Атрибуты | Удаляемая фича |
|---|---|---|---|---|
| 0 | 📝 Editor | `create_grid_view_widget_for_home` | — | — |
| 1 | 💾 TMs | `create_translation_memories_tab` | — | — |
| 2 | 🏷️ Termbases | `create_termbases_tab` | колонка 8 «🎤 Voice» 16937-16995 | F1 (часть) |
| 3 | ✨ AI | `UnifiedPromptManagerQt(self, standalone=False)` | `prompt_manager_qt`, `ai_subtabs`; Chat → `right_tabs.insertTab(1,…)` | — |
| 4 | 🔍 SuperLookup | плейсхолдер → lazy `_ensure_superlookup_top_tab` 11843 (SuperlookupTab `register_hotkeys=False`) | `superlookup_tab_index`, `_superlookup_top_widget` | — (остаётся) |
| 5 | 📋 Clipboard Manager | плейсхолдер → lazy `_ensure_clipboard_top_tab` 11873 | `clipboard_tab_index`, `_clipboard_top_widget` | **F2** |
| 6 | 🎤 Voice | плейсхолдер → lazy `_ensure_voice_top_tab` 11913 (`modules.voice_tab.VoiceTab(self)`) | `voice_tab_index`, `_voice_top_widget` | **F1** |
| 7 | ⚙️ Settings | `create_settings_tab` 20460 | `settings_tabs` (SettingsSidebar) | страницы F1/F2/F3-III |

Back-compat псевдонимы: `resources_tabs = main_tabs` (9893), `document_views_widget = main_tabs` (9968). Стартовый таб: `setCurrentIndex(0)` 10023. Esc-to-tray QShortcut 10041-10065 (проверка текущей вкладки в обработчике). `currentChanged → _on_main_tab_changed` 10068. **Индексы вкладок хранятся атрибутами** (`*_tab_index`), не константами; навигация по возможности по тексту метки (`_switch_main_tab` 28530 по подстроке, `open_termbases_tab` 45041, `_go_to_settings_tab` 56893) — хрупких числовых привязок к удаляемым вкладкам нет; жёсткие `index == 0 / index == 1` в `_on_main_tab_changed:11745-11750` касаются только Editor/AI (остаются).

### 1.3 Страницы Settings (create_settings_tab 20460–20593, боковой навигатор SettingsSidebar)

General, Backup, AutoCorrect, **👤 User Identity (F3-III, 25442)**, AI Settings, **🎤 Voice (F1, 25516)**, **📋 Clipboard (F2, 23446)**, Language Pair, MT Settings, QuickTrans, View Settings, System Prompts, Debug, Segmentation Rules, File Types, Keyboard Shortcuts, Log.
Навигация: `_switch_settings_subtab(label)` 28543 — по тексту метки (устойчиво к удалению страниц); индексные потребители — `mt_quick_lookup_tab_index` 22436 (hasattr) и `keyboard_shortcuts_tab_index` 26018 (getattr) — оба к остающимся страницам.

### 1.4 «Знаменитый случай»: закомментирование кода вкладки SuperLookup не даёт открыться главному окну

Механизм (статически установлен):
1. `main()` 68230 `window = SupervertalerQt()` — **без try/except**; `__init__` → `init_ui()` 6433 → `create_main_layout()` 7027/9838 — тоже без try/except. Любое необработанное исключение в построении вкладок убивает процесс **до** `window.show()` — окно просто не появляется.
2. Внутри `create_main_layout` **до** плейсхолдеров вызывается `self._setup_superlookup_hotkeys()` 9975, который конструирует `SuperlookupTab(self, …)` 12108 и присваивает `self.lookup_tab` 12110. Комментирование класса `SuperlookupTab` (62547+) или его импорта даёт `NameError` ровно здесь → старт мёртв.
3. Потребители `self.lookup_tab` сегодня все охранены (hasattr): лямбда хоткея 7297-7301, closeEvent 29881-29905, 30360, 48515, 58110 — поэтому в текущем коде падает именно (2), а не потребители. Исторически падение давали неохраняемые потребители атрибутов вкладки.

Шаблон «потребитель вкладки X» для каждой вкладки: любой код вне метода создания, читающий `self.<tab_attr>`, `self.<index_attr>` или `<widget>.<метод>`. Охрана: `hasattr`/`getattr(…, None)`/`try`. Таблица потребителей:

| Вкладка | Потребители вне вкладки | Охрана | Риск при удалении |
|---|---|---|---|
| SuperLookup | 7297 (хоткей), 25880 (Ctrl+Alt+L summon), 29881-29905 (closeEvent), 30360, 48515, 58110, tray jumper 29521 | hasattr/getattr везде | низкий: охранённые деградируют молча; но сам класс остаётся |
| Clipboard | 7290 `open_clipboard_tab` (hasattr-внутри), 25916-26006 (hasattr/getattr), 29765 `_dismiss_clipboard_summon`, tray 29525, Esc-ветка 29637+ | hasattr/getattr | низкий при удалении всех путей одновременно; иначе «живые» пункты меню/хоткеи, ведущие в пустоту |
| Voice | 25586-25600 (hasattr), tray Always-On 25036-25118 (не охраняется, но сам oтносится к F1), tray jumper 29529, Esc-ветка | hasattr/getattr | низкий/средний: Always-On трей — отдельная поверхность, удалять вместе |
| Settings | `_go_to_settings_tab` 56893 (по label), 22436/26018 (hasattr/getattr) | есть | — |
| TMs/Termbases/AI/Editor | `_switch_main_tab` по подстроке; `open_termbases_tab` 45041 по тексту | есть | — |

### 1.5 Глобальные хоткеи и трей

`setup_global_shortcuts` 7038–7343 (через `ShortcutManager`, `modules/shortcut_manager.py` — общий, остаётся). Фичевые привязки:

| ID | Клавиши | Обработчик | Фича |
|---|---|---|---|
| `voice_dictate` | Ctrl+Shift+Space | `start_voice_dictation` 7076 | F1 |
| `voice_alwayson_toggle` | Ctrl+Alt+O | `_toggle_alwayson_listening` 7303 | F1 |
| `sidekick_open_clipboard` | Ctrl+Shift+C | `open_clipboard_tab` 7290 | F2 |
| `tools_universal_lookup` | Ctrl+Alt+L | `lookup_tab._handle_superlookup_hotkey` 7297 | SuperLookup (остаётся; OS-сторона регистрируется `SuperlookupTab.register_global_hotkey`) |
| `sidekick_open` | Alt+K | `open_quicklauncher` 7302 | остаётся |
| `editor_split/merge_segment`, match/termlens/compare и пр. | — | — | остаются |

Плюс голосовые биндинги вне реестра QShortcut: `voice_pause_hotkey` (настраиваемая клавиша паузы, listener-путь 54246-54269) — F1. F2 «Ctrl+Alt+C summon» регистрируется `SuperlookupTab` (см. B7).

Трей — **две** иконки:
1. Workbench (`_setup_tray_icon` 29459, вызов из main 68244): Show, Open SuperLookup/Clipboard/Voice/Settings (jumpers через `getattr` 29508-29536 — F1/F2 дают по пункту), Close-to-tray, Start minimized, Autostart (`modules/autostart.py` — остаётся), Quit.
2. Always-On Voice (`_ensure_alwayson_tray_icon` 25036, вызов из `__init__` 6475 **безусловно**): серая/красная рисованная иконка-микрофон, одиночный клик = toggle, меню Start/Stop + «Open Voice». Целиком F1.

### 1.6 Расхождение с постановкой: autoload-механизм отсутствует

`grep -rn "autoload" Supervertaler.py modules/` → **0 совпадений**. Ни `_autoload_modules_impl`, ни `autoload_modules`, ни QTimer 500 мс в HEAD не существует (выведен ранее; роль «отложенной инициализации» сейчас выполняют `QTimer.singleShot(2500, _warm_up_top_tabs)` 10082 и `_init_okapi_sidecar_deferred` 58267). Пункт задачи F1 «автозагрузка в _autoload_modules_impl» — удалять нечего.

### 1.7 Классификация типов зависимостей (как в Batch #7)

- **Охраняемые hasattr/getattr по self** (низкий риск): все nav-пути к вкладкам (см. 1.4), tray-jumpers, `open_clipboard_tab`.
- **Динамические цепочки `self.parent()`** (высокий риск, hasattr молча False): `VoiceTab(self)` читает свойства окна duck-typed (`shortcut_manager`, `load_dictation_settings`… — внутренние для F1); `ClipboardManagerWidget` читает `self._parent_app` через `getattr` (`load_clipboard_privacy_settings` — clipboard_manager_widget.py:771; `user_data_path` — :1566).
- **Неохраняемые вызовы «модуль → main_window»**: не обнаружены новые; duck-typed `mw.start_voice_dictation()` 67131 охранён `hasattr`. `main()` → `window._load_settings_section("ui")` 68236 — безусловно, но к фичам не относится (остаётся).
- **Прямые bind без охраны** (удалять синхронно с фичей): `create_shortcut("voice_dictate", …, self.start_voice_dictation)` 7076, `dictate_btn.clicked.connect(self.start_voice_dictation)` 27795/29019, `alwayson_btn`/`_toggle_alwayson_listening` 27803+, tray-обработчики.

---

## 2. Инвентарь F1–F6 (+справка F7/F8)

Полные сырые таблицы — `notes_stage2_4.md`. Сводки:

### 2.1 F1 Voice

**modules/ (целиком фичевые, ~5604 строк):** `voice_tab.py` (1378), `voice_commands.py` (1465; `ContinuousVoiceListener` :730, `VoiceCommandManager`), `voice_command_dialog.py` (355), `voice_dictation_lite.py` (321; `QuickDictationThread`, lazy `faster_whisper` :248), `voice_hotkey_listener.py` (480; `GlobalHotkeyListener`), `voice_release_poller.py` (310), `voice_vocabulary.py` (269), `dictation_toast.py` (170), `vosk_model_manager.py` (188; импортируется только voice_commands.py:1003), `mic_devices.py` (171; lazy `sounddevice`). Все импортируются только монолитом (347-349, lazy: 11923, 45032, 53944, 53989, 54231, 54388, 54658). `modules/voice_dictation.py` (497) — **уже мёртв** (DEAD_CODE_REPORT №8; импортёров 0).

**Монолит (кластеры, класс `SupervertalerQt` — AST-проверено):**
- init: 6417 (`VoiceCommandManager(main_window=self)`), 6420 (`voice_listener=None`), 6255-6256, 6246-6247, 6475 (tray Always-On на каждом старте);
- Always-On: 24730-25163 (`_toggle_alwayson_listening`, создание `ContinuousVoiceListener` 24793, `_update_alwayson_ui` 24845, tray 25036-25118, `_on_alwayson_*` 25120-25163), статус-бар `alwayson_indicator_label` 8222-8228 (создаётся всегда, hidden), меню трея 29529;
- вкладка Voice: плейсхолдер 10013-10015, lazy 11913-11933, Settings-страница `_create_voice_settings_tab` 25516-25584, `_open_voice_in_workbench` 25586;
- voice commands UI: 24683-24728 (`_populate_voice_commands_table`, `_reset_voice_commands`, `_open_voice_scripts_folder`);
- диктовка PTT: 53931-54955 (`_get_voice_release_poller`, `_register_voice_pushtotalk/voice_command_ptt_deferred`, press/release 54050-54219, `_get_voice_hotkey_listener` 54221, pause 54284-54417, `start/stop_voice_dictation` 54458/54419, `on_dictation_*` 54678-54827, `_set_dictation_button_recording` 54896);
- словарь/промпт: `load/save_voice_vocabulary_settings` 44949-45012, `build_voice_initial_prompt` 45014-45039, `_collect_voice_dictation_termbase_terms` 45096-45146, настройки `load/save_dictation_settings` 44852-44923;
- кнопки: грида 27793-27803+ (`🎤 Dictate`, `🎧 Always-On: OFF`), tab-редактора 29017-29021; хоткеи 7076/7303;
- duck-typed потребитель 67131-67132 (охранён).

**Термбазы и 🎤 (особый пункт):** колонка 8 «🎤 Voice» таблицы термбаз — UI-чекбокс `PurpleCheckmarkCheckBox` 17977-17995 (класс из `modules/styled_widgets.py:112`, остаётся — используется и AI-колонкой). Флаг хранится **в БД**: таблица `termbases`, колонка `voice_dictation_enabled` (`modules/database_manager.py:577` `ALTER TABLE termbases ADD COLUMN … DEFAULT 0`), доступ через `modules/termbase_manager.py:479/493/547` (`get_termbase_voice_enabled`/`set_…`/`get_voice_dictation_termbases`). `termbase_import_export.py` и `termbase_entry_editor.py` флаг **не читают и не пишут** (grep 0). Рекомендация по схеме БД: колонку не удалять (см. §7).
Whisper-инъекция: только `build_voice_initial_prompt` → термы voice-термбаз → начальный промпт диктовки (F1-внутреннее).

**Ключи настроек F1:** `ui.dictation_settings{model, max_duration, language, recognition_engine, pushtotalk_engine, alwayson_sensitivity, alwayson_commands_only, voice_pause_hotkey}`, секция `voice_vocabulary{custom_terms, replacements, use_termbase}`, `ui.voice_dictation_opt_in_reset_applied` (sentinel F6). Читающий остающийся код — не найден (grep по ключам вне F1-кластеров — 0).

**Внешние пакеты:** lazy-импорты с `except ImportError`: `faster_whisper` (voice_dictation_lite.py:248-249), `sounddevice` (mic_devices.py, voice_commands.py:967), `vosk` (voice_commands.py:989-990, 1370). В `requirements.txt` их **нет** — исключать из сборки нечего. `pynput` остаётся (B5).

### 2.2 F2 Clipboard Manager

- `modules/clipboard_manager_widget.py` (2531) — единственный файл; импортируют только `Supervertaler.py:11885` (lazy-вкладка) и `:23467` (Settings-страница, читает `ClipboardManagerWidget.DEFAULT_PRIVACY`/`COMMON_SECRET_APPS`).
- Монолит: плейсхолдер 10009-10011, `_ensure_clipboard_top_tab` 11873-11911, `open_clipboard_tab` 7566-7578 (Ctrl+Shift+C), `open_workbench_to_clipboard` 25916-26006 (Ctrl+Alt+C от SuperLookup, B7), `_dismiss_clipboard_summon` 29765-29808, Settings `_create_clipboard_settings_tab` 23446-23676, `load/save_clipboard_privacy_settings` 44645-44676 (load — делегат `SettingsService`, вызывается виджетом через `getattr(self._parent_app, …)` clipboard_manager_widget.py:771), tray jumper 29525, Esc-ветка 29637+, warm-up.
- Данные: таблица `clipboard_history` в общем `supervertaler.db` (`modules/database_manager.py:3213-3260`); `<user_data>/snippet_library/*.md`. Схему БД не трогать.
- Ключи настроек: `features.clipboard_privacy` (settings_service.py:164-170).
- **Каскадные сироты после удаления:** `modules/snippet_library.py` и `modules/text_conversion_library.py` — используются только clipboard_manager_widget (grep -rln: только они и виджет).
- Общая инфраструктура: paste через `CrossPlatformKeySender`/AHK (`platform_helpers`) — остаётся (SuperLookup использует тот же механизм).

### 2.3 F3 CAT-интеграции (слои I/II/III)

**Слой I — механизмы интеграции:**
- `modules/supervertaler_bridge_server.py` (357) — приём промптов от Trados-плагина в Chat; создаётся в `create_main_layout` 9955-9965 (try/except, `aboutToQuit → stop`), обработчик `_on_bridge_prompt_request` 7671-7754 → Chat/Prompt Manager (остаются). Удалимо отдельно от Chat.
- `modules/trados_bridge_client.py` (524) — **B2: импортируется остающимися** chat_view_widget.py:23-29 и unified_prompt_manager_qt.py (чип «Trados», poller доступности). Без решения по Chat не удалять.
- `modules/batch_offload.py` — CLI `--batch`/`--translate-sdlxliff` (main 68011-68013), сценарий Trados-плагина; импортирует `sdlppx_handler` → пересекается со слоем II.
- `modules/sdltm_handler.py` (237) + `_attach_sdltm_as_tm` 20004-20231 — подключение Trados TM (граничит с остающимися TM).

**Слой II — обработчики форматов** (все модули импортируются ТОЛЬКО монолитом; grep importers):

| CAT | Импорт (метод, строки) | Экспорт | Модуль (строк) |
|---|---|---|---|
| memoQ | `import_memoq_bilingual` 35385, `import_memoq_rtf` 35750, `import_memoq_xliff` 36404 | `export_memoq_bilingual` 36021, `export_memoq_rtf` 36677, `export_memoq_xliff` 36794, `_interpret_memoq_status` 35378 | `memoqrtf_handler.py` 688, `mqxliff_handler.py` 717 |
| CafeTran | `import_cafetran_bilingual` 37135 | `export_cafetran_bilingual` 40444 | `cafetran_docx_handler.py` 379 |
| Trados | `import_trados_bilingual` 37285, `import_sdlppx_package` 37698, `import_standalone_sdlxliff` 38361, `import_sdlxliff_folder` 38569 | `export_trados_bilingual` 37554, `export_sdlrpx_package` 38113, `export_standalone_sdlxliff` 38772, `_map_sdlxliff_segment` 38270, sdlxliff-dicts 38006-38067 | `trados_docx_handler.py` 433, `sdlppx_handler.py` 2270 |
| Phrase | `import_phrase_bilingual` 38922 | `export_phrase_bilingual` 39207 | `phrase_docx_handler.py` 669 |
| Déjà Vu | `import_dejavu_bilingual` 39382 | `export_dejavu_bilingual` 39547 | `dejavurtf_handler.py` 784 |

Меню: Import-подменю memoQ/CafeTran/Trados Studio/Phrase (Memsource)/Déjà Vu X3 — 8616-8666; Export — 8728-8780.
Пересечения слоя II с остающимися: (а) `sdlppx_handler` нужен `batch_offload.py` и `sdltm_handler.py`; (б) `sdlxliff` упоминается в остающих модулях `segment_split_merge.py`, `models.py`, `chat_view_widget.py`, `unified_prompt_manager_qt.py`; (в) `handler.username = self.get_translator_name()` 38244/38851 (связь со слоем III); (г) Okapi merge-export `_try_okapi_merge_export` 14316-14463 и Okapi-sidecar используются общим импортом (остаются). Решение о входе слоя II в объём — вопрос Дмитрию (§7).

**Слой III — User Identity:** `_create_user_identity_tab` 25442-25503, `_save_user_identity_from_ui` 25505-25514, ключ `general.translator_name`, чтение `get_translator_name` 37998-38001 (фолбэк — системное имя пользователя). Потребители **остающегося** кода — B1 (TMX Editor 10204, DOCX-комментарии 13788/53609, 7496). Страница удалима, `get_translator_name` — нет.

### 2.4 F4 Superbrowser

- `modules/superbrowser.py` (351): `SuperbrowserWidget` — 3 фиксированные колонны ChatGPT/Claude/Gemini (согласуется с «встроенные сайты не грузятся»), `QWebEngineProfile` на колонку с персистентными профилями `<user_data>/workbench/superbrowser_profiles/` (:108-123). Импортирует только монолит (lazy 10119).
- Монолит: `open_superbrowser_window` 10117-10157 (атрибут `_superbrowser_window`, `WA_DeleteOnClose` 10156), пункт меню Tools 9273-9278.
- **Причина зависания главного окна при закрытии (статически, не чинилось):** методы `BrowserColumn.cleanup()` (superbrowser.py:163-183) и `SuperbrowserWidget.cleanup()` (:321-329, останавливают web_view, `profile.deleteLater()`) **никем не вызываются** — `grep -n "\.cleanup()"` даёт только определение :325 и обработчики docx-хендлеров 37747-37910. Нет ни `closeEvent`, ни `aboutToQuit`-очистки. Закрытие окна с `WA_DeleteOnClose` выполняет синхронное C++ удаление `QWebEngineView`/`QWebEngineProfile` с живыми Chromium-процессами в GUI-потоке → блокировка. Дополнительный фон: ручная WebEngine-очистка на выходе отключена из-за крашей (58245-58249).
- WebEngine в сборке остаётся и после F4 (B4).

### 2.5 F5 SetupWizard

- Фактический визард — **инлайн** `_show_setup_wizard` 6747-6995 (QDialog со страницами «папка данных» + features; `dialog.exec()` 6993 — модальный). `modules/setup_wizard.py` (354) **не импортируется никем** (grep по всем импорт-формам — 0) — pre-existing orphan, отдельная строка мёртвого кода.
- Вызовы: первый запуск `QTimer.singleShot(300, …)` 6540-6542 (гейт `_needs_data_location_dialog or not first_run_completed`); пункт Help-меню 9362-9365.
- Связанная логика: `needs_first_run_data_dialog` 292-313 и `save_user_data_path`/config-pointer (~/.supervertaler_config.json); визард создаёт выбранную папку (`mkdir` 6955) и дергает `_reinitialize_with_new_data_path` 6957.
- **B3:** `_reinitialize_with_new_data_path` 6665-6728 используется остающими настройками (General → смена папки данных 22869, диалог 6643) — остаётся.
- Гейты первого запуска в `__init__` (6330/6336/6347/6357: mkdir, миграции, языковая пара, `db_manager.connect`) при удалении F5 требуют упрощения: Portable всегда стартует с фиксированной папкой → ветки можно свести к безусловному mkdir+connect, а `first_run_completed` оставить только для welcome-логики (решение Дмитрия).

### 2.6 F6 Миграции легаси-данных

| Миграция | Строки | Когда вызывается | Что делает/создаёт | Зависимости остающегося кода |
|---|---|---|---|---|
| `_migrate_settings_to_unified` | 44678-44768 | `__init__` 6337 (только не-первый запуск) и `_reinitialize_with_new_data_path` 6680 | Однократно (skip если settings.json есть): general_settings.json/ui_preferences.json/feature_settings.json/api_keys.txt → `workbench/settings/settings.json`; переезд сателлитов (find_replace_history, superlookup_history, recent_projects, themes, shortcuts, **voice_commands.json**) | Делегаты `_get_settings_dir/_load/_save_unified_settings` в SettingsService (S2.1) используются постоянно; миграция как таковая — legacy-путь |
| `_migrate_to_workbench_layout` | 44770-44835 | `__init__` 6338, `:6683` | Однократно по флагу `workbench/.migrated`; переносит settings/dictionaries/voice_scripts/ai_assistant/superbrowser_profiles/web_cache/projects → `workbench/`. **На чистом старте (старой компоновки нет) ВСЁ РАВНО создаёт `workbench/settings/` и пишет `.migrated`** — т.е. участвует в начальной раскладке папок | Полной замены нет: `SettingsService._save_unified_settings` сам делает `mkdir(parents=True)` (settings_service.py:129) — settings-каталог возникнет при первой записи; остальным каталогам mkdir делает создающий их код. Но флаг `.migrated` и мгновенная раскладка пропадут |
| `_migrate_voice_dictation_default_off` | 45063-45094 | **каждый старт** (6399), внутри sentinel `ui.voice_dictation_opt_in_reset_applied` | Однократный `UPDATE termbases SET voice_dictation_enabled = 0` (v1.10.29) | Чисто F1: при удалении Voice уходит вместе с колонкой-флагом; схему БД всё равно не трогать |

Portable-специфика: «Portable всегда стартует с формата 1.10.x» ⇒ обе legacy-миграции на новой установке срабатывают только как «создатели раскладки» (см. выше), а не как перенос данных. Проверено: ни одна из трёх не создаёт каталогов данных ресурсов (resources/ создаёт `DatabaseManager`, snippet_library — код F2 и т.д.).

### 2.7 Справка F7 (AHK) и F8 (Ollama) — только данные, без вердиктов

**F7 AHK / SuperLookup hotkey setup:** монолит — 148 упоминаний (`grep -rc`). Кластеры: диалог настройки `_show_autohotkey_setup_dialog` внутри `SuperlookupTab` (класс 62547+; `from ahk import AHK` — единственный импорт pip-пакета `ahk`, Supervertaler.py:67233; вызовы 58110-58111; closeEvent-остановка 29881-29905, hasattr-охранён); `_find/_browse_autohotkey_for_settings` 22439-22467; пункт меню Help 9415-9419; `_prewarm_ahk` 11799-11841 (общий прогрев paste-пути). modules: `platform_helpers.py` 66 (`CrossPlatformKeySender._find_ahk` — paste-механизм, используется SuperLookup/Clipboard/Voice), `voice_commands.py` 47, `voice_tab.py` 25, `keyboard_shortcuts_widget.py` 21, `voice_command_dialog.py` 13, `shortcut_manager.py` 2. U1.2-правки AHK-вызовов (апстрим 626d4c63) живут в `SuperlookupTab`/`keyboard_shortcuts_widget` (VALIDATION_BACKLOG #26 — CLOSED этим коммитом). AHK — внешний exe; pip-пакет `ahk` в requirements tie-нится только к F7-диалогу.
**F8 Ollama:** монолит — 179 упоминаний; `local_llm_setup.py` 88, `llm_clients.py` 69, `quicktrans.py` 5, `llm_pricing.py` 4, `chat_view_widget.py` 3, `settings_service.py` 2 (дефолты `ollama_model`, `llm_ollama` :241/:351), `chat_backend.py` 2, `voice_vocabulary.py` 1, `help_system.py` 1. U1.2 перенёс Ollama timeout (`da403a48` → `_apply_ollama_timeout_setting`). Ollama — провайдер для остающихся AI-перевода/Chat/QuickTrans; выделение «только timeout/keepwarm» затрагивает общий AI-стек.

---

## 3. Граф удаления, сироты, пакеты, ресурсы, настройки

### 3.1 Листовой порядок (без последствий для других фич)

1. **F4 Superbrowser** — самодостаточный лист (модуль + окно + пункт меню); WebEngine остаётся.
2. **F1** — внутри фичи листья: сначала UI-поверхности (трей Always-On → вкладка → Settings-страница → кнопки/хоткеи), затем модули; `modules/voice_dictation.py` можно удалить хоть сейчас (уже мёртв).
3. **F2** — лист; каскадные сироты `snippet_library`/`text_conversion_library` удалять следом.
4. **F3-II** — хендлеры-листья (после решения Дмитрия); особое внимание `sdlppx_handler` (его держат batch_offload и sdltm_handler).
5. **F3-I** — bridge_server; bridge_client НЕ трогать (B2).
6. **F5** — визард; только после упрощения first-run-гейтов.
7. **F6** — последними (проверить чистый старт после всего).

Жёсткие межфичевые связи: F2 ← хоткей Ctrl+Alt+C регистрируется SuperLookup (B7); F1 ← общий `_prewarm_ahk`/paste-механизм (остаётся); F6.3 ← F1 (sentinel + колонка); F5 ↔ F6 (гейты 6336-6338).

### 3.2 Каскадные сироты (станут мёртвыми ПОСЛЕ удаления; доказательство — grep importers)

| Сирота | Строк | После какой фичи | Доказательство отсутствия других потребителей |
|---|---|---|---|
| `modules/voice_dictation.py` | 497 | уже сейчас | DEAD_CODE_REPORT №8; grep импорт-форм — 0 |
| `modules/snippet_library.py` | — | F2 | grep -rln: clipboard_manager_widget, text_conversion_library, сам |
| `modules/text_conversion_library.py` | — | F2 | grep -rln: clipboard_manager_widget, сам |
| `mic_devices.py`, `vosk_model_manager.py`, `voice_*` (8 файлов) | ~5600 | F1 | importers — только монолит (F1-кластеры) |
| 6 CAT-хендлеров (слой II) | ~5666 | F3-II | importers — только монолит |
| `supervertaler_bridge_server.py` | 357 | F3-I | importer — монолит |
| `superbrowser.py` | 351 | F4 | importer — монолит |
| `setup_wizard.py` | 354 | уже сейчас | importers — 0 |
| Методы монолита: `start/stop_voice_dictation`, `on_dictation_*`, `_toggle_alwayson_*`, `_ensure/_update_alwayson_tray_icon`, `_open_voice_in_workbench`, `load/save_dictation_settings`, `load/save_voice_vocabulary_settings`, `build_voice_initial_prompt`, `_collect_voice_dictation_termbase_terms`, `open_clipboard_tab`, `open_workbench_to_clipboard`, `_dismiss_clipboard_summon`, `load/save_clipboard_privacy_settings`, import/export CAT-методы, `open_superbrowser_window`, `_show_setup_wizard`, `create_log_tab`-нет и т.п. | — | соответствующие фичи | AST-карта + grep; часть уже помечена в DEAD_CODE_REPORT (`_register_voice_command_ptt_deferred` №10, `_register_voice_pushtotalk_deferred` №57 и др.) |
| `SettingsService.load_clipboard_privacy_settings` (settings_service.py:164-170) | — | F2 | вызывается только делегатом монолита + виджетом F2 |

### 3.3 Внешние пакеты

| Пакет | Кем используется | Вердикт для сборки |
|---|---|---|
| `faster_whisper`, `sounddevice`, `vosk` | только F1, lazy + ImportError-guards; **в requirements.txt отсутствуют** | ничего исключать (в requirements и так нет) |
| `pynput` | platform_helpers/superlookup/keyboard_shortcuts_widget (остаются) + F1 | **остаётся** |
| `ahk` (pip) | единственный импорт Supervertaler.py:67233 — F7-диалог SuperLookup | кандидат только при решении по F7; сейчас остаётся |
| `PyQt6-WebEngine` | SuperLookup Web Resources (остаются) + F4 | **остаётся** (B4) |
| `pyperclip` | SuperlookupEngine + остающиеся | остаётся |

### 3.4 Ресурсы и «вокруг кода»

- `assets/` — только иконки приложения; фичевых иконок/звуков нет (grep .wav/.mp3 по voice/dictation — 0).
- Документация: README.md — о рефакторинг-проекте (упоминаний фич нет); CHANGELOG в репо отсутствует (не портирован, см. U1 manifest); user guides в репо нет. Обновлять нечего, кроме, возможно, `modules/DATABASE_README.md` — проверить при Этапе 2 (таблица clipboard_history, колонка voice_dictation_enabled).
- Скрипты сборки/spec: spec-файлов в репо не обнаружено; requirements.txt — см. 3.3.
- Тесты: `tools/batch_validation/*` не привязаны к фичам F1–F6 (probe/smoke — общие).

### 3.5 Орфанные ключи настроек (останутся в settings.json пользователя)

U1.2: неизвестные ключи сохраняются (`dict(existing)` в SettingsService) — удаления не произойдёт, конфликтов имён нет. Останутся: `ui.dictation_settings` (+вложенные), `ui.voice_vocabulary`, `ui.voice_dictation_opt_in_reset_applied`, `features.clipboard_privacy`, `general.translator_name` (если страницу удалить — ключ останется и будет читаться остающимися B1 — т.е. вообще не станет орфанным), UI-ключи вкладок (если где-то сохраняется «последний таб» — найдено только `bottom_dock_active_tab`/`match_top_active_tab` к остающимся дока-вкладкам). Два варианта обработки (оставить / чистить при следующем сохранении) — решение Дмитрия; по умолчанию «оставить» безопасно.

### 3.6 Влияние на ранее перенесённое

- `settings_service.py`: `load_clipboard_privacy_settings` (S2.2) — станет сиротой при F2 (удалить синхронно); дефолты `voice_commands.json`-переезда в `_migrate_settings_to_unified` — при F6.1; docstring-упоминания voice_tab/clipboard_manager_widget (строки 35-38) — косметика.
- Делегаты монолита (UndoManager-стиль) не затронуты — фичевые методы живут в монолите.
- VALIDATION_BACKLOG: #26 (AHK setup dialog) — CLOSED в U1.2; после удаления F7-диалога пункт можно архивировать. Прочих упоминаний AHK в бэклоге нет (grep — 1 совпадение).
- U1-manifest (UPSTREAM_SYNC_MANIFEST.md:72-74): «Voice, Clipboard-фича, CAT-интеграции, Superbrowser, SetupWizard — в апстриме 371..372 переносу не подлежат» — апстрим-синк с удалением не конфликтует; из перенесённого в код фич попадают только U1.2 AHK-правки (626d4c63) и Ollama timeout (da403a48) — при удалении F7/F8 они исчезнут вместе с кодом (потеря переносимости правок, не функциональная).

---

## 4. Предложение декомпозиции Этапа 2 (черновик для координатора)

Порядок — по возрастанию риска; внутри под-батча — листья первыми.

| Под-батч | Состав (ID из §2) | ~Объём | Зависимости | Риск | Обоснование |
|---|---|---|---|---|---|
| **8.1 F4 Superbrowser** | модуль `superbrowser.py` (351), `open_superbrowser_window` 10117-10157, пункт меню 9273-9278, `_superbrowser_window` | ~380 строк | нет | **низкий** | самодостаточный лист; WebEngine остаётся |
| **8.2 F1 Always-On и трей** | 24730-25163, tray 25036-25118 + вызов 6475, `alwayson_indicator_label` 8222-8228, хоткей 7303, пункт меню трея 29529, Esc-ветка Voice | ~500 строк | 8.3 не нужна, но меню-флаг | **средний** | много поверхностей, но все внутренне связаны; `start_voice_dictation` НЕ трогать |
| **8.3 F1 вкладка + voice commands + Settings** | плейсхолдер 10013-10015, lazy 11913-11933, Settings 25516-25584, 24683-24728, модули voice_tab/voice_commands/voice_command_dialog/dictation_toast/vosk_model_manager/mic_devices, хоткеи ID `voice_alwayson_toggle`, warm-up-строка | ~2600 строк | после 8.2 | **средний** | `VoiceCommandManager` 6417/6710 удалить здесь; duck-typed ссылки охранены |
| **8.4 F1 диктовка PTT + словарь + 🎤 UI** | 53931-54955, 44852-45012, 45014-45146 (кроме миграции 45063), хоткей `voice_dictate`, кнопки 27793/29017/54896, колонка 8 UI 16937-16995, `modules/voice_dictation_lite.py`, `voice_hotkey_listener.py`, `voice_release_poller.py`, `voice_vocabulary.py` | ~1800 строк | после 8.2/8.3 | **высокий** | больше всего точек входа; БД-колонку `voice_dictation_enabled` и методы termbase_manager НЕ удалять (схему не трогать) |
| **8.5 F2 Clipboard** | плейсхолдер 10009-10011, lazy 11873-11911, 7566-7578, 25916-26006, 29765-29808, Settings 23446-23676, 44645-44676 + сервисный метод, tray jumper, Esc-ветка, `clipboard_manager_widget.py` (2531), сироты `snippet_library`/`text_conversion_library`, хоткей `sidekick_open_clipboard` | ~3200 строк | независимо; координация с SuperLookup по Ctrl+Alt+C (B7) | **средний** | единый батч, чтобы хоткей не вёл в пустоту |
| **8.6 F3-II CAT-форматы** | 6 хендлеров (~5666) + import/export-методы + меню 8616-8666/8728-8780 + `sdltm_handler`+`_attach_sdltm_as_tm` (вопрос) | ~7000+ строк | **после решения Дмитрия об объёме** | **средний** (по коду) | хендлеры — листья; не задевать общий импорт/Okapi/sdlxliff без решения |
| **8.7 F3-I bridge server** | 9955-9965, `_on_bridge_prompt_request` 7671-7754, `supervertaler_bridge_server.py` | ~450 строк | после решения по Chat | **средний** | bridge_client и Chat не трогать (B2) |
| **8.8 F5+F6 first-run и миграции** | `_show_setup_wizard` 6747-6995, меню 9362-9365, гейты 6330-6358 упростить, `_migrate_settings_to_unified` + `_migrate_to_workbench_layout` + вызовы, `_migrate_voice_dictation_default_off` (если 8.4 уже удалён), `modules/setup_wizard.py` (уже мёртв) | ~700 строк | **последним**; после 8.4 (миграция голоса) | **высокий** | стартовая последовательность; требуется проверка чистого старта и `user_data`-копии |

К каждому под-батчу можно присоединить соответствующие строки DEAD_CODE_REPORT (например, №8 `modules/voice_dictation.py` и №10/№57 voice-методы — к 8.3/8.4) — без отдельного риска.

Минимальные сценарии валидации (для каждого под-батча, на **копии** user_data): старт без исключений в консоли; импорт файла 180/400 сегментов; перевод сегмента; навигация по всем вкладкам и страницам Settings (каждая открывается); прогресс-окна импорта; Save; сохранение настроек; трей и статус-бар без упоминаний удалённого; выход без зависания (флаки-краш 0xC0000005 при выходе — предсуществующий и нестабильный, не считать регрессией). Специфика: 8.8 — дополнительно чистый старт (без settings.json, без .migrated) и апгрейд-старт на копии существующей папки.

NOT-REMOVE-границы (обязательно остаются): `get_translator_name`+ключ (B1), `trados_bridge_client` (B2), `_reinitialize_with_new_data_path` (B3), `PyQt6-WebEngine` и Web-Resources SuperLookup (B4), `pynput` (B5), `platform_helpers` целиком, `shortcut_manager`/`styled_widgets` (`PurpleCheckmarkCheckBox` используется AI-колонкой), `modules/autostart.py`, таблица `clipboard_history` и колонка `voice_dictation_enabled` в БД (схему не трогать), SuperlookupTab и его глобальные хоткеи.

---

## 6. Непокрытые проверки (не проверено статически / требует запуска)

1. Фактическое поведение Qt при закрытии Superbrowser (диагноз B-«hang» — статическая реконструкция: cleanup не вызывается; подтверждение — только live).
2. Реальный старт приложения после каждого предполагаемого удаления (offscreen-прогон) — не выполнялся по условию READ-ONLY.
3. `modules/setup_wizard.py`: не проверено, не вызывается ли внешними скриптами вне репо (сборка/инсталлятор) — по коду репо импортёров 0.
4. Полный перебор строковых `getattr`/`setProperty`/динамических имён по всем 137 модулям для фичевых методов выполнен точечно (по спискам Batch #7 и grep); остаточный шанс строковой ссылки, не покрытой grep-паттернами, не нулевой — Этап 2 должен повторить проверку по каждому удаляемому имени (как в Batch #7: connect-цели, invokeMethod, QML-строки).
5. `web_browser_mode`/Superbrowser-ключи UI (если сохраняются) — не искались целенаправленно; выявить при удалении 8.1 (grep по `_superbrowser_window`/`superbrowser` в settings-методах).
6. Сигнатуры `open_workbench_to_clipboard`/`_handle_clipboard_hotkey` в SuperLookup (Ctrl+Alt+C) — точное место регистрации в `modules/superlookup.py` не дизассемблировано до строки; путь зафиксирован по монолиту (25916).
7. Поведение `_warm_up_top_tabs` при отсутствии методов — охрана `getattr(self, helper, None)` читается как безопасная, но вживую не проверялась.
8. Апгрейд-сценарий «старый user_data → новая сборка без F6» не моделировался (только статический вывод: чистый старт создаёт раскладку лениво).

---

## 7. Вопросы к Дмитрию

### Решения Дмитрия (внесены 2026-10-02, финал Stage 1)

1. **F3 слой II (форматные обработчики memoQ/Trados/CafeTran/Phrase/Déjà Vu): удалять** (обмена файлами с memoQ, Trados, CafeTran, Phrase и Déjà Vu нет), ПОСЛЕДНИМ отдельным под-батчем. Слои I и III — раньше. Общие форматы (txt, md, docx, Okapi) остаются. *(ответ на в. 1)*
2. **sdlxliff в остающихся модулях и Okapi: остаются.** Поля Segment/.svproj не трогать. *(в. 2)*
3. **Superbrowser: удалить целиком** (под-батч 8.1). *(в. 3)*
4. **F7 AHK: удалить** — диалог настройки, `_prewarm_ahk`, pip-пакет `ahk` (глобальным хоткеем SuperLookup для вставки в другие программы не пользуюсь). `CrossPlatformKeySender` — удалить после F1/F2, если потребителей не останется. Отдельный под-батч после F1/F2. *(в. 4)*
5. **F8 Ollama: в Batch #8 не трогать.** `custom_openai` не затрагивать ни при каких упрощениях. *(в. 5)*
6. **Орфанные настройки: оставить** в settings.json. *(в. 6)*
7. **Схема БД: не трогать** — `termbases.voice_dictation_enabled` и `clipboard_history` остаются. *(в. 7)*
8. **User Identity:** удалить страницу, **оставить `get_translator_name()`** с фолбэком «системное имя». *(в. 8)*
9. **Editor/грид: вопрос закрыт.** Дефект «прыжок строки при клике» воспроизводится на свежей v1.10.372 (апстримный), к F1–F6 не относится, ведётся отдельно (G1). *(в. 9)*
10. **F5: упрощение first-run согласовано.** Валидация — обязательный запуск с пустой папкой данных (папки и дефолтные настройки создаются без визарда). *(в. 10)*

### Вопросы (исходная формулировка, для трассировки)

1. **Объём F3 (главный):** входят ли обработчики ФОРМАТОВ (слой II) в «CAT-интеграции»? Затронуто: импорт/экспорт memoQ (bilingual DOCX/RTF/XLIFF), CafeTran (bilingual DOCX), Trados (bilingual DOCX, .sdlppx/.sdlrpx, standalone .sdlxliff, папки sdlxliff, .sdltm-TM), Phrase (bilingual DOCX), Déjà Vu (bilingual RTF) — суммарно ~11 import/export-методов и ~5,7 тыс. строк хендлеров. Альтернатива: оставить слой II (это «просто форматы», полезные и вне CAT-интеграций), удалив только слой I (мосты) и слой III.
2. **`sdlxliff` и Okapi:** даже при удалении слоя II остающиеся модули (`segment_split_merge`, `models`, `chat_view_widget`, `unified_prompt_manager_qt`) упоминают sdlxliff, а Okapi-sidecar/merge-export обслуживают общий импорт — подтверждаете, что всё это остаётся?
3. **Судьба Superbrowser:** подтверждаете удаление целиком (8.1)? Заодно: чинить ли зависание при закрытии уже не нужно, если удаляем.
4. **F7 (AHK):** удаляем ли диалог AutoHotkey-setup SuperLookup, `_prewarm_ahk` и pip-пакет `ahk`, или AHK остаётся как paste-механизм (CrossPlatformKeySender используется SuperLookup/Clipboard/Voice; после удаления F1/F2 останется только SuperLookup)?
5. **F8 (Ollama):** ограничиться ли timeout/keepwarm или пересматривать провайдера целиком? (Ollama вшит в общий AI-стек: llm_clients, local_llm_setup, Chat, QuickTrans.)
6. **Орфанные настройки:** оставить ключи удалённых фич в settings.json пользователя (рекомендую: безопасно, U1.2 их сохраняет) или вычищать при следующем сохранении?
7. **Схема БД по 🎤:** подтверждаете рекомендацию «не трогать» — колонку `termbases.voice_dictation_enabled` и таблицу `clipboard_history` оставить в схеме (удаляем только UI/логику)?
8. **User Identity (F3-III):** удалить страницу Settings, но оставить `get_translator_name()` с фолбэком на системное имя (иначе ломаются TMX Editor и DOCX-комментарии, см. B1) — согласны? Или оставить и страницу?
9. **Editor/грид-заметка:** в постановке есть хвост «дописанная заметка про Editor/грид» — уточните, что имелось в виду; в коде Editor/грид фиче-специфичных связей с F1–F6, кроме кнопок Dictate/Always-On и колонки 🎤 (уже учтены), не найдено.
10. **F5:** согласны ли на упрощение first-run: без визарда, фиксированная папка данных, `first_run_completed` больше не пишется (welcome-диалог исчезает вместе с визардом)?

---

*Отчёт — единственный новый файл в репозитории; push — после подтверждения Дмитрия (docs-only коммит).*
