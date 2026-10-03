# Batch #8 — Addendum A2: аудит усечения SuperLookup (read-only)

**Дата:** 2026-10-03
**Исполнитель:** ZCode
**Базовый коммит:** `80a8552b` (HEAD = origin/main, `git fetch origin` выполнен)
**Дрейф-чек:** `git merge-base --is-ancestor 20b5675b HEAD` → предок, OK.
**Supervertaler.py:** 68216 строк, SHA256 `025b192456f308f24b84f1332ff44ce40df1a7f85f9e3e11610c98e8783c778e` (= состояние после 8.1, коммит 20b5675b не менял монолит до 80a8552b — все промежуточные коммиты docs-only).
**py_compile baseline:** 137 файлов (монолит + 136 модулей) — OK=137, FAIL=0
(скрипт `D:\Temp\SupervertalerPortable\refactoring\b8-a2\py_compile_all.py`).
**Статус:** READ-ONLY. Код не менялся; отчёт — единственный новый файл.

**Решение Дмитрия (финальное, постановка A2):** вкладка SuperLookup ОСТАЁТСЯ как
оболочка с подвкладками TMs и Termbases (единый поиск по TM и термбазам).
Удаляются: подвкладка Web Resources со всеми веб-сервисами, режимы
Embedded/External, глобальный хоткей Ctrl+Alt+L. Подвкладка SuperLookup Settings
урезается до нужного TMs/Termbases. Целиком SuperLookup НЕ удаляется.

---

## 1. Где живёт SuperLookup (объект аудита)

| Компонент | Расположение | Размер | Вердикт |
|---|---|---|---|
| `class SuperlookupTab(QWidget)` | Supervertaler.py:62498–67738 | 5241 строк, 120 методов | Остается, урезается |
| `_SuperLookupSearchWorker(QRunnable)` + `_SuperLookupSearchSignals` | Supervertaler.py:62405–62496 | ~92 строки | **KEEP целиком** — только TM/termbase-поиск, web-атрибутов не касается (AST-проверка) |
| `modules/superlookup.py` (`SuperlookupEngine`, `LookupResult`) | 256 строк | — | **KEEP** — движок `search_tm` (конкорданс) используется воркером (Supervertaler.py:62459); модуль НЕ удаляется |
| Верхняя вкладка «🔍 SuperLookup» | `_ensure_superlookup_top_tab` Supervertaler.py:11794–11822, плейсхолдер 9998–10000 | — | KEEP |
| Скрытый экземпляр-владелец хоткеев | `_setup_superlookup_hotkeys` 12047–12070 → `self.lookup_tab` | — | KEEP (после 8.10 владеет единственным глобальным хоткеем Ctrl+Alt+Q) |
| Отсоединяемое окно | `detach_superlookup` 11886–12017, `reattach_superlookup` 12019–12037 | — | KEEP (+ удалить мёртвые блоки `home_lookup_widget`, см. §8) |

Три экземпляра SuperlookupTab: `_superlookup_top_widget` (видимая вкладка,
`register_hotkeys=False`), `lookup_detached_widget` (окно detach,
`register_hotkeys=False`), `self.lookup_tab` (скрытый владелец глобальных
хоткеев). Все три создаются с одним классом — урезание класса применяется ко
всем автоматически.

## 2. Карта методов SuperlookupTab по подвкладкам

Полная карта: `D:\Temp\SupervertalerPortable\refactoring\b8-a2\sltab_map.json`
(AST, реальные границы `lineno`–`end_lineno`). Сводка по группам:

### 2.1 Группа WEB (DELETE-SAFE, 19 методов, 1258 строк)

| Метод | Строки | строк | Вызыватели вне своей группы | Вердикт |
|---|---|---|---|---|
| `create_web_resources_tab` | 63247–63741 | 495 | только `init_ui` (62767, правится) | DELETE-SAFE |
| `_show_web_welcome_message` | 63743–63758 | 16 | только web-группа | DELETE-SAFE |
| `_create_web_view_for_resource` | 63760–63792 | 33 | только web-группа | DELETE-SAFE |
| `_create_web_view_container` | 63794–63940 | 147 | только web-группа | DELETE-SAFE |
| `_get_web_view_index` | 63942–63946 | 5 | только web-группа | DELETE-SAFE |
| `_on_web_mode_changed` | 63948–63957 | 10 | только web-группа | DELETE-SAFE |
| `_update_web_view_for_mode` | 63959–63971 | 13 | только web-группа | DELETE-SAFE |
| `_on_web_resource_selected` | 63973–64013 | 41 | только web-группа | DELETE-SAFE |
| `_update_web_lang_info` | 64015–64024 | 10 | только web-группа | DELETE-SAFE |
| `_schedule_lazy_web_views` | 64026–64051 | 26 | только web-группа | DELETE-SAFE |
| `_perform_web_search` | 64053–64167 | 115 | только web-группа | DELETE-SAFE |
| `search_all_web_resources` | 64169–64178 | 10 | web-группа + `search_with_query` (65298, правится) | DELETE-SAFE |
| `_build_web_search_url` | 64180–64264 | 85 | только web-группа | DELETE-SAFE |
| `_on_opus_corpus_changed` | 64266–64275 | 10 | только web-группа | DELETE-SAFE |
| `_get_web_lang_code` | 64277–64393 | 117 | только web-группа | DELETE-SAFE |
| `_open_web_resource_external` | 64395–64405 | 11 | только web-группа | DELETE-SAFE |
| `create_web_settings_subtab` | 64582–64651 | 70 | только `create_settings_tab` (правится) | DELETE-SAFE |
| `_on_web_resource_checkbox_changed` | 64724–64737 | 14 | только web-группа | DELETE-SAFE |
| `create_mt_settings_subtab` | 64551–64580 | 30 | **вызывателей нет вообще** (мёртвый с момента выноса MT-настроек, комментарий 64500) | DELETE-SAFE (мёртвый) |

AST-проверка самодостаточности: web-группа создаёт 29 self-атрибутов
(`web_browser_mode`, `web_engine_available`, `web_profile`, `QWebEngineView`,
`QWebEngineProfile`, `SilentWebPage`, `web_views`, `web_view_stack`,
`web_view_containers`, `web_resource_buttons`, `web_resource_checkboxes`,
`web_resources`, `current_web_resource_index`, `opus_*`, `_web_search_query`,
`last_web_search_*`, `search_web_enabled` и др.). Из НЕ-web методов класса их
касаются только 4 (см. §2.3). Из-за пределов класса — ни один
(AST-скан `self.X` по монолиту с резолвом по классу-владельцу: 0 попаданий;
скрипт `callers.py`). Читает web-методами из общих: `lang_from_combo`,
`lang_to_combo`, `source_text`, `status_label`, `main_window`,
`user_data_path` — только чтение, переживает удаление без правок.

### 2.2 Группа HOTKEY-SL (Ctrl+Alt+L и AHK-фолбэк, DELETE-SAFE, ~542 строки)

| Метод | Строки | строк | Основание | Вердикт |
|---|---|---|---|---|
| `_find_autohotkey_executable` | 66481–66514 | 34 | вызывают только удаляемые (67280, 66556-косвенно) | DELETE-SAFE |
| `_show_autohotkey_setup_dialog` | 66516–66600 | 85 | Help-меню (58062) + отложенный вызов из `_register_hotkey_external_script` (67289) — оба пункта удаляются вместе | DELETE-SAFE |
| `_open_ahk_download` | 66602–66611 | 10 | только диалог AHK | DELETE-SAFE |
| `_browse_for_autohotkey` | 66613–66649 | 37 | только диалог AHK | DELETE-SAFE |
| `_on_pynput_superlookup` | 66808–66821 | 14 | только binding Ctrl+Alt+L (66761) | DELETE-SAFE |
| `_handle_superlookup_hotkey` | 67382–67397 | 16 | Ctrl+Alt+L (QShortcut 7297–7300 + pynput 66817) | DELETE-SAFE |
| `_read_clipboard_for_superlookup` | 67399–67421 | 23 | только `_handle_superlookup_hotkey` | DELETE-SAFE |
| `on_ahk_capture` | 67472–67504 | 33 | только AHK-фолбэк (67348, 67421) и fallback в 67220 | DELETE-SAFE |
| `capture_text` | 65042–65067 | 26 | **вызывателей нет** — мёртвый (grep по всему монолиту: единственный `self.engine.capture_text()` внутри самого метода) | DELETE-SAFE (мёртвый) |
| `_try_ahk_library_method` | 67179–67246 | 68 | **вызывателей нет** (пип-пакет `ahk`, импорт 67184 — единственный в репо) | DELETE-SAFE (мёртвый) |
| `_register_hotkey_external_script` | 67248–67316 | 69 | вызов только из `register_global_hotkey` (66804); скрипт `supervertaler_hotkeys.ahk` **никогда не существовал в git** (`git log -- supervertaler_hotkeys.ahk` пуст) → фолбэк всегда падал в «Script not found» | DELETE-SAFE |
| `start_file_watcher` | 67318–67330 | 13 | только из 67309 | DELETE-SAFE |
| `check_for_signal` | 67332–67379 | 48 | только таймер из `start_file_watcher`; его QuickTrans-половина (67352–67379) тоже мертва (зависит от несуществующего AHK-скрипта) | DELETE-SAFE |
| `show_superlookup` + `_fill_and_search` | 67673–67738 | 66 | единственный вызыватель — `on_ahk_capture` (67501) | DELETE-SAFE (мёртвые после удаления on_ahk_capture) |

`register_global_hotkey` (66651–66806, 156 строк) — **NEEDS-SPLIT** (не удалять):
убрать binding `sl_shortcut`/`_on_pynput_superlookup` и обработку
`tools_universal_lookup` (66689, 66705, 66761), оставить `qt_shortcut`
(mt_quick_lookup → Ctrl+Alt+Q) и общий каркас GlobalHotkeyManager. Сокращается
примерно до 100 строк.

### 2.3 Общие методы с web-вкраплениями (SHARED-KEEP, правки точечные)

| Метод | Строки | Что правится | Вердикт |
|---|---|---|---|
| `__init__` | 62503–62578 | строка 62561 `self.search_web_enabled = False` (и комментарий) — удалить; параметр `user_data_path` сохранить в сигнатуре (снаружи передают 3 сайта), хотя единственное потребление было web-кэшем 63307 | SHARED-KEEP |
| `init_ui` | 62638–62782 | блок «Web Resources tab» 62766–62768 (addTab); текст описания 62651–62664 упоминает Ctrl+Alt+L — переписать; комментарий 62748–62750 про «Web Reso…» — почистить | SHARED-KEEP |
| `on_results_tab_changed` | 64653–64704 | web-ветка 64673–64674 (`web_index`), 64691–64704 — удалить; ветка Settings (64684–64689) остаётся | SHARED-KEEP |
| `perform_lookup` | 65069–65226 | web-блок 65186–65226 (deferred web search, чтение `web_resource_checkboxes`/`web_browser_mode`) — удалить целиком; TM/TB/MT-часть не трогается | SHARED-KEEP |
| `search_with_query` | 65264–65298 | web-префетч 65295–65298 — удалить; остальное — KEEP (внешний вход из `_go_to_superlookup` 56894) | SHARED-KEEP |

### 2.4 Группа TMs/Termbases (KEEP без правок, ядро)

`create_tm_results_tab` (62784), `create_termbase_results_tab` (62876),
`create_mt_results_tab` (62946) + MT-хвост (`_perform_mt_lookup`,
`_call_mymemory`, `_update_mt_provider_status`, `_open_mt_settings`,
`display_mt_results`, `_copy_mt_result`, `on_mt_result_double_click`) —
MT-результаты в главном поиске остаются (MT-вкладка результатов была удалена
ранее, но MT-блок в `perform_lookup` выводит в общий UI; удаление MT — не в
объёме 8.10). Поиск: `perform_lookup`, `_on_search_*`, `search_termbases`
(66082, 229 строк), `get_selected_tm_ids`/`get_selected_termbase_ids`
(колонка SuperLookup на вкладках TMs/Termbases, `tm_metadata_mgr`),
`get_search_direction`, `get_language_filters`, `swap_language_filters`,
`populate_language_dropdowns`, история `_init_search_history`/
`_add_to_search_history`/`_save_search_history` (файл
`user_data/settings/superlookup_history.json`, 66017 — **KEEP**, работает и
после усечения), отображение `display_tm_results`/`display_termbase_results`,
контекстные меню, `add_to_termbase`/`show_add_term_dialog`,
`set_project_languages` (вызов из монолита 30315), `set_tm_database` (48467),
`keyPressEvent`, `showEvent`, `_delayed_language_population`,
`_get_base_language_name`, `_lang_base_name`, `_highlight_search_term`,
`_resize_html_cell_rows`, `_normalize_language_code`, `_on_language_changed`,
`_set_language_combo`, `toggle_tm_view_mode`, `_select_first_term_in_table`,
`on_results_tab_changed` (после правки), `refresh_tm_list`/
`refresh_termbase_list` (no-op-заглушки v1.10.168, внешний вызов 47967 —
сохранить), `get_selected_*`, `__del__`.

Примечание к `__del__` (65035–65040): вызывает `self.unregister_global_hotkey()`,
которого **не существует** — молчаливый no-op через bare `except`
(grep `unregister_global_hotkey` — единственное вхождение 65038). Можно поправить
попутно (не блокер).

### 2.5 Группа хоткеев OTHER (не 8.10, покрывается 8.2/8.3/8.5)

| Метод | Строки | Под-батч |
|---|---|---|
| `_on_pynput_clipboard`, `_handle_clipboard_hotkey`, `_open_clipboard_after_copy` | 66837–66846, 66849–66984, 66986–67050 | 8.5 (Clipboard; B7-путь) |
| `_on_pynput_pushtotalk`, `_handle_pushtotalk_hotkey` | 67052–67097 | 8.3 (Voice) |
| `_on_pynput_alwayson_toggle`, `_handle_alwayson_toggle_hotkey` | 67099–67145 | 8.2 (Always-On) |
| `_on_pynput_command_ptt`, `_handle_command_ptt_press_hotkey` | 67111–67126, 67148–67177 | 8.3 (Voice) |

`show_supervertaler_assistant` (67576–67615) — **KEEP**: вызывается из
контекстных меню редакторов сетки (2699, 3852), к хоткеям/web не относится.
`_paste_translation_to_external_app` (67617–67655) — **KEEP** (QuickTrans,
см. §5).
`set_compact_mode` (67666–67671) — KEEP (общий UI).

## 3. Общее состояние, которое должно пережить удаление Web Resources

| Атрибут/элемент | Кто создаёт | Кто читает вне Web Resources | Вердикт |
|---|---|---|---|
| `source_text` (HistoryComboBox) | `init_ui` 62680 | `perform_lookup`, `search_with_query`, web-группа (чтение) | KEEP |
| Кнопки Search/Clear | `init_ui` 62694–62704 | `perform_lookup` (connect), внешне `open_workbench_to_superlookup` ткёт `search_btn.click` (25855) | KEEP |
| `lang_from_combo`/`lang_to_combo` | `init_ui` 62714–62735 | `get_language_filters`, `swap_language_filters`, `set_project_languages`, web-группа (чтение) | KEEP |
| `_web_search_pending` | `perform_lookup` 65204–65226, `on_results_tab_changed` 64692–64693 | только web-логика | Удалить вместе с web-блоками |
| `web_browser_mode`, `web_engine_available` | `create_web_resources_tab` 63322/63253 | после правки §2.3 — потребителей нет | DELETE с группой |
| `status_label`, `results_tabs` | `init_ui` | общие; `results_tabs` наружу не выходит (grep) | KEEP |
| История поиска `search_history` | `_init_search_history` (файл в user_data) | `perform_lookup`, `init_ui` | KEEP |
| `engine`, `tm_database`, `termbase_mgr`, `db_manager`, `enabled_tms/termbases`, `search_tm_enabled`, `search_termbase_enabled` | `__init__`/`perform_lookup` | worker, TMs/Termbases | KEEP |
| `search_web_enabled` | `__init__` 62561, web-группа | никем не читается вне web | DELETE |

«Search All»-маршрутизации вне web нет: `search_all_web_resources` вызывается
только из web-группы и `search_with_query` (65298). Кнопки/пункты «Search All»
в TMs/Termbases отсутствуют.

## 4. Ключи настроек и данные

| Ключ/данные | Где читается/пишется | Вердикт |
|---|---|---|
| `superlookup_landing_tab` (general settings.json) | Единственный владелец — SuperlookupTab: константы 64408–64415, чтение `_load_superlookup_landing_pref` 64519, запись `_on_landing_pref_changed` 64532. **Фактическая «приземляющая» логика не подключена: ключ нигде не применяется к `results_tabs.setCurrentIndex`** — радио-кнопка в Settings-подвкладке единственный потребитель. Settings-страница General ключ только сохраняет как есть (комментарий 26540, `_save_general_settings_from_ui`), UI для него нет. | В 8.10 радио-UI + 2 метода + константы удаляются. Фолбэк **не нужен**: ключ перестаёт читаться вовсе, сохранённое значение (в т.ч. `'webresources'`) становится инертным мусором в settings.json и ни на что не влияет. Документируем в отчёте 8.10. |

**Эмпирическое подтверждение (offscreen-проба, 2026-10-03, возражение Дмитрия
проверено).** Дмитрий сообщил, что наблюдает работу настройки: после
перезапуска Ctrl+Alt+L (выделение в Editor → Ctrl+C → Ctrl+Alt+L) открывает
подвкладку по выбору, а при отсутствии результата — «⚙️ SuperLookup Settings».
Статический анализ этого не объясняет, поэтому поставлена изолированная
offscreen-проба полного приложения
(`D:\Temp\SupervertalerPortable\refactoring\b8-a2\landing_probe.py`,
изолированные HOME/USERPROFILE/APPDATA, указатель на временный user_data,
подложенный `settings.json` с `general.superlookup_landing_tab`, модалки
нейтрализованы как в 8.1; маршрут Ctrl+Alt+L воспроизведён вызовом
`open_workbench_to_superlookup("internationalization")` — тот же путь, что
`_handle_superlookup_hotkey → _read_clipboard_for_superlookup`, минус буфер).

Результат (обе пробы `result.json` в `landing-probe/{termbases,tms}/`):

| pref | Радио после старта | Подвкладка после поиска | Статус |
|---|---|---|---|
| `termbases` | termbases (✓ прочитан) | **📖 TMs (индекс 0)** | "No results found" |
| `tms` | tms (✓ прочитан) | **📖 TMs (индекс 0)** | "No results found" |

Ключ читается, но влияет только на состояние радио-кнопок; подвкладка после
маршрута Ctrl+Alt+L всегда TMs (дефолтный индекс 0 свежепостроенного виджета),
перехода на Termbases/Settings нет. Единственное переключение `results_tabs`
в классе — `setCurrentIndex(0)` в `search_with_query` (65290, путь Ctrl+K).
Наблюдаемое Дмитрием поведение в этом коде воспроизвести не удалось
(см. §9 п.7 — предложить контрольный эксперимент).
| `autohotkey_path`, `hide_autohotkey_dialog` | Пишет диалог AHK (66594, 66638); читают `_find_autohotkey_executable` (66491) и `_register_hotkey_external_script` (67288). Поле `ahk_path_edit` в Settings General **никогда не создаётся** (`self.ahk_path_edit =` отсутствует; 23379 — `getattr(..., None)`), т.е. UI-владельца у ключа нет | Удалить вместе с AHK-группой; `_save_general_settings_from_ui` (26578) — убрать сохранение ключа |
| История поиска `user_data/settings/superlookup_history.json` | `_init_search_history` 66008 | KEEP |
| `workbench/web_cache` (user_data) | создаёт web-профиль QWebEngineProfile (63306–63316) | Код удаления уходит; в production user_data каталога **нет** (проверено `ls D:/_old/Supervertaler-Portable/Supervertaler/workbench/web_cache` → отсутствует, т.к. WebEngine в сборке не установлен). Остаточные каталоги у пользователей, ставивших full-install, безвредны |
| Ключи из 14 General (`superlookup_landing_tab`) | см. выше | см. выше |

`modules/settings_service.py` ключа `superlookup_*` не содержит (grep — пусто).

## 5. Потребители вне SuperLookup

| Потребитель | Что вызывает | Вердикт |
|---|---|---|
| Редакторы сетки `ReadOnlyGridTextEditor` (2162–2185), `EditableGridTextEditor` (3637–3663) | контекстное меню «Search in SuperLookup (Ctrl+K)» → `main_window._go_to_superlookup(...)` | KEEP — поиск по TM/TB |
| `show_concordance_search` (SupervertalerQt, 11420–11487; вызовы 7236, 9270) | `_go_to_superlookup` → `open_workbench_to_superlookup` + `widget.search_with_query` | KEEP |
| Edit menu «🔍 SuperLookup...» (9081–9088) | `setShortcut("Ctrl+Alt+L")`, `triggered → _go_to_superlookup()` | **Удалить пункт целиком** (рекомендация): хоткей уходит, дубль Tools-меню «Super&lookup (Ctrl+K)» 9267–9271 остаётся |
| In-app QShortcut `tools_universal_lookup` Ctrl+Alt+L (7295–7300) | `lambda: self.lookup_tab._handle_superlookup_hotkey()` | Удалить (6 строк) |
| Help menu AHK-пункт (9413–9414) → `_show_ahk_setup_from_menu` (58058–58070) | `lookup_tab._show_autohotkey_setup_dialog()` | Удалить оба (диалог про «глобальный хоткей Ctrl+Alt+L» — смысл исчезает) |
| `reload_global_hotkeys` (25984–25997, вызов из Settings → Keyboard) | `lookup_tab.register_global_hotkey()` | KEEP (перерегистрирует оставшийся Ctrl+Alt+Q) |
| Загрузка проекта (30315) | `lookup_tab.set_project_languages(...)` | KEEP |
| TM-менеджер (48467) | `lookup_tab.set_tm_database(...)` | KEEP |
| `closeEvent` (29803; блок 29828–29858) | стоп `_hotkey_manager`, `_using_ahk_library`/`_ahk`, `ahk_process` | KEEP pynput-блок (Ctrl+Alt+Q); удалить ahk-блоки (фолбэк уходит); убрать вызовы `_cleanup_web_views` (58182/58187/58191) и сам no-op-стаб `_cleanup_web_views` (58195–58201) |
| `_warm_up_top_tabs` (11721–11748) | `_ensure_superlookup_top_tab`, `_prewarm_ahk` | KEEP (прогрев AHK ещё нужен CrossPlatformKeySender'у QuickTrans; на усмотрение 8.5 — прогрев упоминает Clipboard) |
| Esc-обработка/трей (11689–11690, 29602) | `superlookup_tab_index` → ensure, hide-to-tray | KEEP |
| Detach/reattach (11886–12037) | конструктор SuperlookupTab; мёртвые hasattr-блоки `home_lookup_widget` (11988–11995, 12025–12029 — атрибут никогда не создаётся) | KEEP окна; мёртвые блоки удалить (гигиена, −10 строк) |
| QuickTrans | см. §6.2 | KEEP |
| AI/Sidekick-навигация (2694–2699, 3847–3852) | `show_supervertaler_assistant` | KEEP — к web/хоткеям отношения не имеет |
| `_go_to_superlookup` (56873–56899) | открытая вкладка + `search_with_query` | KEEP — ни одного web-вызова |

## 6. Хоткей Ctrl+Alt+L, AHK/pynput, QuickTrans

### 6.1. Полная цепочка Ctrl+Alt+L

1. **Глобально (вне приложения):** `_setup_superlookup_hotkeys` (9968, 12047) →
   скрытый `SuperlookupTab(self)` → `register_global_hotkey` (66651) →
   `GlobalHotkeyManager` (modules/platform_helpers.py:1004, pynput
   `GlobalHotKeys`) binding `(sl_shortcut, self._on_pynput_superlookup)`
   (66761) → `QMetaObject.invokeMethod("_handle_superlookup_hotkey")` →
   `CrossPlatformKeySender.send_copy()` → `pyperclip.paste()` →
   `mw.open_workbench_to_superlookup(text)` (67415). Откат AHK-скрипта
   (66802–66806 → 67248) — мёртвый: скрипта нет в репо.
2. **Внутри приложения:** `create_shortcut("tools_universal_lookup",
   "Ctrl+Alt+L", ... self.lookup_tab._handle_superlookup_hotkey())` (7295–7300)
   + QAction в Edit menu с тем же аккордом (9081–9088).
3. **ShortcutManager:** `tools_universal_lookup` (modules/shortcut_manager.py:174–179,
   `default: Ctrl+Alt+L`, `global: True`, описание «Superlookup»); legacy-алиасы
   `global_superlookup` (792, 874). При удалении записи из словаря DEFAULTS
   нужен tolerance-чек старых settings-файлов (см. Непокрытые проверки №1).

**После 8.2 + 8.3 + 8.5 + 8.6 + 8.10 остаётся ровно один глобальный хоткей:
Ctrl+Alt+Q (mt_quick_lookup → QuickTrans).** `sidekick_open` (Alt+K) глобально
не регистрируется (переменная `sk_shortcut` читается в 66691, но в
`_bindings` отсутствует — мёртвая строка, убрать в 8.10); Alt+K остаётся
in-app QShortcut (7303). Voice/clipboard-хоткеи уходят в 8.2/8.3/8.5.

**Что можно убрать целиком после всех под-батчей:** НЕЛЬЗЯ убрать
GlobalHotkeyManager/pynput — остаётся Ctrl+Alt+Q. CrossPlatformKeySender —
НЕЛЬЗЯ (см. 6.2). Можно убрать: AHK-фолбэк целиком (`_register_hotkey_external_script`,
`_try_ahk_library_method`, `start_file_watcher`, `check_for_signal`,
диалог AHK + Help-меню + `_show_ahk_setup_from_menu`,
`_find_autohotkey_executable`), пип-пакет `ahk` (единственный импорт — мёртвый
67184; requirements.txt:62), ключи `autohotkey_path`/`hide_autohotkey_dialog`.

### 6.2. QuickTrans (modules/quicktrans.py, 1663 строки)

Пути вызова:
1. **Глобальный хоткей Ctrl+Alt+Q** (`mt_quick_lookup`, ShortcutManager:708+,
   `global: True`) → `_on_pynput_quicktrans` (66823) → `_handle_quicktrans_hotkey`
   (67424): если Workbench активен — `main_window.show_mt_quick_popup()` (67442),
   иначе — копирование из внешнего окна + внешний `MTQuickPopup` → выбор
   перевода → `_paste_translation_to_external_app` (67617: буфер +
   `activate_foreground_window` + `CrossPlatformKeySender.send_paste()`).
2. **In-app QShortcut** `mt_quick_lookup` Ctrl+Shift+Q → `show_mt_quick_popup`
   (7327).
3. **Контекстное меню редакторов** → `show_mt_quick_popup(text_override=...)`
   (2793–2794, 4576–4577).
4. **AHK-фолбэк** (file-watcher → `on_ahk_mt_lookup_capture` →
   `show_mt_quick_lookup_from_ahk`, 67518) — мёртв (скрипта нет), уходит с
   AHK-группой в 8.10.
5. Настройки — Workbench Settings → ⚡ QuickTrans (комментарий 64506–64513).

**Вердикт: QuickTrans полностью остаётся и остаётся доступным**, включая
глобальный Ctrl+Alt+Q (регистрация живёт в `register_global_hotkey`, который
в 8.10 урезается, но не удаляется). Модуль `modules/quicktrans.py` не
трогается; его запись геометрии попапа в реестр
HKCU\Software\Supervertaler\MTQuickPopup (QSettings, quicktrans.py:610/1324 —
E1 §1 №3) остаётся как есть.

### 6.3. QtWebEngine — можно ли убрать целиком: ДА

Все потребители в коде приложения:
- `create_web_resources_tab` (63259–63260: `PyQt6.QtWebEngineWidgets` /
  `QtWebEngineCore`) и `_create_web_view_container` (63803) — только web-группа;
- `modules/feature_manager.py:95, 312` — **модуль-сирота: ни одного импорта
  `feature_manager` во всём репо** (grep по *.py — пусто);
- `main()` (67967–68034): env `QTWEBENGINE_CHROMIUM_FLAGS` (67989),
  `QT_LOGGING_RULES` с `qt.webenginecontext` (67993), `StderrFilter` «js:»
  (67997–68023), `AA_ShareOpenGLContexts` (68034), комментарий 67967.

Ленивых импортов/try-ImportError вне web-группы нет; флагов `*_AVAILABLE`
кроме `web_engine_available` нет; warm-up QtWebEngine отсутствует.

Пакеты: requirements.txt:13 `PyQt6-WebEngine>=6.5.0` — убрать;
pyproject.toml:136 `web = []` — уже no-op (заглушка совместимости, можно
оставить или убрать вместе с прочими пустыми extras — не обязательно).
Пип-пакет `ahk` (requirements.txt:62) — убрать (см. 6.1).

**Размер:** в bundled-сборке `E:\Dev\python-embed` PyQt6-WebEngine **не
установлен** (в `Lib/site-packages/PyQt6/` нет `QtWebEngine*.pyd`, каталогов
`*WebEngine*` нет; есть только несвязанные QtWebChannel/QtWebSockets) →
в этой сборке вкладка Web Resources всегда работала в режиме `external`
(`web_browser_mode = 'embedded' if web_engine_available else 'external'`,
63322), а embedded-ветка была недостижима. Это согласуется с наблюдением
Дмитрия в T8.1.4 (вкладка Web Resources открывается, но страницу не грузит).
Размер пакета в сборке оценить не по чему — **«не измерено»**; декларация
в мёртвом feature_manager.py заявляет size_mb=100 (без пруфа). Снятие
PyQt6-WebEngine из requirements/сборки уменьшит full-install на размер
пакета (типично 100–200 МБ, точно не измерено).

Стартовые настройки в `main()` — удаляемые строки перечислены выше; после
удаления `AA_ShareOpenGLContexts` (68034) рисков нет: атрибут требовался
только WebEngine.

### 6.4. Связь с 8.5 и 8.6

| Элемент | Покрывающий под-батч | Осталось на 8.10 |
|---|---|---|
| `_on_pynput_clipboard`, `_handle_clipboard_hotkey`, `_open_clipboard_after_copy` | 8.5 | — |
| pynput voice-хендлеры (4 шт.) | 8.2/8.3 | — |
| CrossPlatformKeySender (класс в platform_helpers) | 8.6 планировал удалить «при отсутствии потребителей» — **A2-вердикт: НЕ удалять**: после 8.3/8.5 остаются живые потребители в QuickTrans (`_handle_quicktrans_hotkey` 67448–67452, `_paste_translation_to_external_app` 67643–67644) + `_prewarm_ahk` (11753–11765) | — (поправка к Stage-1 rev.2) |
| `pyperclip` | — | KEEP (QuickTrans, `check_for_signal` удаляется, но pyperclip нужен QuickTrans-потоку 67409→67373) — точнее: после удаления SL-хендлеров pyperclip остаётся в `_paste_translation_to_external_app` (67628) |
| AHK-фолбэк + диалог + Help-пункт + pip `ahk` | — | **8.10** (8.6(F7) — только микро-аудит CrossPlatformKeySender/платформенных частей) |
| Web Resources + QtWebEngine + Ctrl+Alt+L + landing pref | — | **8.10** |

## 7. Предложение под-батча 8.10 «усечение SuperLookup»

**Порядок:** после 8.6 (нужны уже удалёнными voice/clipboard-хендлеры из
`register_global_hotkey`, чтобы урезание каркаса было одним движением;
8.6 также снимает вопрос CrossPlatformKeySender). До 8.8/8.9 — чтобы финальные
под-батчи с clean-start-сценариями шли по финальному состоянию монолита.

**Состав (один код-коммит «Batch #8.10: trim SuperLookup to TMs+Termbases»):**
1. Удалить web-группу: 19 методов §2.1 (1258 строк).
2. Удалить hotkey-SL/AHK-группу §2.2 (14 методов, ~542 строки).
3. `register_global_hotkey`: оставить только `qt_shortcut`; убрать
   `sl_shortcut`, `sk_shortcut` (мёртв), voice/clipboard-переменные, если
   ещё живы после 8.2/8.3/8.5 (NEEDS-SPLIT).
4. Точечные правки SHARED-KEEP §2.3 (`__init__`, `init_ui` + новый текст
   описания без Ctrl+Alt+L, `on_results_tab_changed`, `perform_lookup`,
   `search_with_query`).
5. SuperLookup Settings: убрать радио «Ctrl+Alt+L lands on:» +
   `_load_superlookup_landing_pref`/`_on_landing_pref_changed` + константы
   `SUPERLOOKUP_LANDING_TAB_*`; убрать `settings_subtabs` (останется пустым);
   оставить header + resource_info (объяснение Read-флагов). Создание
   Settings-вкладки (62770–62772) остаётся.
6. Внешняя проводка: Edit menu 9081–9088, QShortcut 7295–7300, Help AHK-пункт
   9413–9414 + `_show_ahk_setup_from_menu`, closeEvent (ahk-блоки + вызовы и
   стаб `_cleanup_web_views`), `_setup_superlookup_hotkeys` докстринг/лог.
7. `main()`: убрать QtWebEngine-строки (67989, 67993, StderrFilter 67997–68023,
   68034, комментарий 67967).
8. shortcut_manager: удалить запись `tools_universal_lookup` (174–179) +
   legacy-алиасы `global_superlookup` (792, 874) — с tolerance-проверкой
   старых настроек.
9. requirements.txt: убрать `PyQt6-WebEngine>=6.5.0` (13) и `ahk...` (62).
10. Опционально (отдельным решением): удалить модуль-сироту
    `modules/feature_manager.py` (0 потребителей) и мёртвые
    `home_lookup_widget`-блоки в detach/reattach.

**Размер:** примерно −1990 строк внутри SuperlookupTab (5241 → ~3250) и
~−80 строк вне класса (main, меню, closeEvent, shortcut_manager) ≈
**−2070 строк чистыми** (wc -l до/после обязателен).

**Риск:** низкий-средний. Главные зоны: (а) `register_global_hotkey` —
недорезать нельзя, Ctrl+Alt+Q должен выжить; (б) `perform_lookup` — правки
в горячем пути поиска; (в) shortcut_manager — обратная совместимость старых
settings-файлов; (г) main() — не задеть другие startup-флаги.

**Статические защиты §4.1 (обязательный набор 8.10):**
1. AST-резолв стартовой цепочки (`main`, `SupervertalerQt.__init__`,
   `init_ui`, `create_menus`, `create_main_layout`, `setup_global_shortcuts`,
   `_setup_progress_indicators`, `_warm_up_top_tabs` + Qt-whitelist)
   до/после: 0 unresolved в обоих.
2. grep zero-mentions по списку удалённых имён (все методы §2.1–2.2,
   `web_browser_mode`, `web_engine_available`, `web_profile`, `web_views`,
   `web_resource_*`, `settings_subtabs`, `_landing_tab_*`,
   `SUPERLOOKUP_LANDING_TAB_*`, `_cleanup_web_views`, `tools_universal_lookup`,
   `QTWEBENGINE_CHROMIUM_FLAGS` и др.), включая строковые литералы — 0 в
   рабочем коде (допустимые остатки: docs/, отчёты).
3. pyflakes undefined-names diff до/после — пуст.
4. Дополнительно к §4.1: AST-проверка, что `register_global_hotkey` после
   урезания содержит binding только `mt_quick_lookup`, и что `Ctrl+Alt+Q`
   присутствует в ShortcutManager.

**Offscreen-проба (изолированная, как в 8.1):** before/after паритет
`SuperlookupTab` (top-tab): число вкладок `results_tabs` (3 вместо 5),
отсутствие «🌐 Web Resources», наличие «📖 TMs»/«📚 Termbases»/«⚙️ SuperLookup
Settings», наличие `source_text`/`search_btn`/`lang_from_combo`/`lang_to_combo`,
паритет методов стартовой цепочки; `findChildren(QTabWidget)` на главной
вкладке.

**Сценарии тестовой сборки (для ручной проверки):**
- **T8.10.1** Старт: лог без «[Superlookup] QWebEngineView available…» и без
  ошибок регистрации хоткеев (кроме, возможно, занятого Ctrl+Alt+Q); главное
  окно открывается.
- **T8.10.2** Вкладка SuperLookup: подвкладки результатов — ровно «📖 TMs»,
  «📚 Termbases», «⚙️ SuperLookup Settings» (без «🌐 Web Resources» и без
  MT-подвкладки, как и сейчас); поиск, поля From/To, история на месте.
- **T8.10.3** Поиск: открыть тестовый проект, включить SuperLookup-флаг у TM и
  термбазы, выполнить поиск из SuperLookup и из редактора (Ctrl+K /
  контекстное меню «Search in SuperLookup») — результаты TM/TB приходят,
  MT-блок не падает.
- **T8.10.4** Settings → SuperLookup Settings: нет радио «Ctrl+Alt+L lands on:»,
  нет подвкладки Web Resources; осталась памятка про Read-флаги. Старый
  settings.json со значением `superlookup_landing_tab: webresources` стартует
  без ошибок (ключ игнорируется).
- **T8.10.5** Хоткеи: Ctrl+Alt+L ни глобально, ни в приложении ничего не
  вызывает (пункт из Edit-меню исчез); Ctrl+Alt+Q из другой программы
  открывает QuickTrans-попап; Ctrl+Shift+Q в приложении работает; Ctrl+K
  работает.
- **T8.10.6** Tools-меню: 12 пунктов (как после 8.1), «Super&lookup (Ctrl+K)»
  на месте; Help-меню без пункта AutoHotkey Setup.
- **T8.10.7** Settings → Keyboard Shortcuts: действия QuickTrans/Concordance на
  месте, «Superlookup (Ctrl+Alt+L)» отсутствует; смена Ctrl+Alt+Q в настройках
  переживает restart (reload_global_hotkeys жив).
- **T8.10.8** Editor: вставка из SuperLookup, «Ask AI assistant» (внешние
  вызовы `show_supervertaler_assistant`) работают; detach/reattach SuperLookup
  работает.
- **T8.10.9** Выход: закрытие приложения чистое (без ahk_process-хвостов),
  в логе нет traceback'ов.

## 8. BLOCKER-ы

Не обнаружены. Все методы web-группы и hotkey-SL-группы закрыты внутри класса;
единственный межклассовый контракт — внешние входы `search_with_query`,
`set_project_languages`, `set_tm_database`, `register_global_hotkey`,
конструктор SuperlookupTab — все сохраняются.

## 9. Непокрытые проверки (обязательный раздел)

1. **ShortcutManager tolerance**: как поведёт себя `get_shortcut('tools_universal_lookup')`/
   settings-файл, содержащий сохранённое значение удалённого id — статически не
   доказано. В 8.10 перед удалением записи проверить ветку _LEGACY_IDS/unknown-id
   (или оставить запись с `enabled_by_default=False`, если код не терпит отсутствия).
2. **Runtime-поведение GlobalHotkeyManager с единственным binding** (Ctrl+Alt+Q):
   статический анализ; offscreen-проба не регистрирует OS-хоткеи. Проверка
   T8.10.5 вручную.
3. **Реальные settings.json пользователей** на предмет
   `superlookup_landing_tab`/`autohotkey_path` — user_data не читался
   (read-only ограничение аудита). После 8.10 оба ключа инертны, но факт их
   наличия у Дмитрия не проверен.
4. **Размер PyQt6-WebEngine в full-install** — в этой сборке пакет отсутствует,
   измерить не по чему («не измерено», декларация 100 МБ в мёртвом
   feature_manager без пруфа).
5. **Контекстные меню редакторов**: блоки 2607–2609/3753–3755 проанализированы
   статически; живое поведение Ctrl+K после усечения — ручной T8.10.3.
6. **`_prewarm_ahk`** остаётся (полезен QuickTrans-вставке); если 8.5 удалит
   Clipboard раньше — прогрев всё ещё оправдан для CrossPlatformKeySender;
   окончательное решение в 8.10 при правке `_warm_up_top_tabs`.
7. **Наблюдение Дмитрия о работе `superlookup_landing_tab`** (открытие
   Termbases/TMs/Settings по выбору и результату): offscreen-пробой
   воспроизвести не удалось (см. §4). Контрольный эксперимент на машине
   Дмитрия: установить pref=`termbases` → полный перезапуск → выделить слово →
   Ctrl+C → Ctrl+Alt+L → какая подвкладка активна? Если Termbases — на машине
   Дмитрия другой билд монолита (все три копии на диске агента — репо HEAD,
   тестовая сборка D:\SupervertalerPortable_test, старый /e/Dev/Supervertaler.py —
   содержат одинаковый «непроводной» код, проверено grep+sed); если TMs —
   наблюдение объясняется дефолтным индексом 0, а не настройкой.

## 10. Вопросы к Дмитрию

1. **Edit menu «🔍 SuperLookup...» (Ctrl+Alt+L)**: удалить пункт целиком
   (рекомендация — остаётся Tools → «Super&lookup (Ctrl+K)») или оставить
   пункт без горячей клавиши?
2. **`superlookup_landing_tab`**: подтверждаете полное удаление радио-UI и
   забвение ключа (фолбэк не нужен, т.к. «приземление» никогда не было
   подключено к фактическому переключению вкладок)?
3. **`modules/feature_manager.py`** — модуль-сирота (0 импортов): удалить в
   8.10 попутно или отдельным решением (вместе с `web = []` в pyproject)?
4. **MT-блок SuperLookup** (`_perform_mt_lookup`/MyMemory и MT-столбец
   результатов): остаётся? В постановке он не упомянут — по умолчанию KEEP.
5. **`_prewarm_ahk`**: оставить (рекомендация — ускоряет первую вставку
   QuickTrans из внешнего приложения) или убрать вместе с AHK-повесткой?

---
Аудит read-only; рабочие файлы `D:\Temp\SupervertalerPortable\refactoring\b8-a2\`
(sltab_map.json, callers.py, py_compile_all.py). Все численные утверждения —
AST `lineno`–`end_lineno` либо grep с указанием строк.
