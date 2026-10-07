# Batch #8.10 — Усечение SuperLookup до TMs+Termbases — ОТЧЁТ

**Дата:** 2026-10-07
**Исполнитель:** ZCode
**Кодовый коммит:** `6897539d` «Batch #8.10: trim SuperLookup to TMs+Termbases»
**Отчёт:** отдельный docs-коммит (этот файл).
**Основание:** постановка 8.10 (промпт Дмитрия), `BATCH8_A2_SUPERLOOKUP_TRIM_AUDIT_REPORT.md`
(§2.1/§2.2/§2.4a/§2.3, §3, §4, §7, §9, §10), `BATCH8_STAGE1_AUDIT_REPORT.md` ред. 2 (§4.1).
**Рабочие файлы:** `D:\Temp\SupervertalerPortable\refactoring\b8-10\`
(снапшоты всех вырезанных зон `snapshots\cut_*.txt`, скрипты `implement_810.py`,
`fix_810.py`, `startup_chain_resolve.py`, `ast_checks_810.py`, `probe_window.py`,
`headless_imports.py`, логи проб `probe_before/after/after2.log`).

---

## 0. Baseline и git-синхронизация

| Параметр | Значение |
|---|---|
| git fetch origin | выполнен, без новых объектов |
| HEAD / origin/main | `b5be3fb9` / `b5be3fb9` (совпадают) |
| git status | чисто; untracked `.zcode/plans/…`, `.zcodeignore` (допустимы) |
| Дрейф-чек | `git merge-base --is-ancestor acfe8880 HEAD` → предок, OK |
| Supervertaler.py ДО | **64984** строки, SHA256 `ae9e3163ffc584a2fed228912d82daeb7d2c268e0d631c066bfa5878ae0177a9` (совпал с ожидаемым; CRLF-копия — независимая проверка: LF→CRLF от HEAD-блоба даёт ровно этот SHA) |
| modules/**/*.py | 121 файл |
| py_compile ДО | **139/139 OK / 0 FAIL** (весь репо) |
| Защита 1 ДО | резолв стартовой цепочки: **977 вызовов, 0 неразрешённых** (`startup_chain_before.json`) |
| pyflakes ДО | 695 предупреждений, **149 undefined names** (set записан: `undefined_names_before.txt`) |
| Offscreen-проба ДО | main_tabs **6**; страниц Settings **14**; хоткеи при старте **ctrl+alt+l, ctrl+alt+q**; SuperLookup results_tabs **4**: «📖 TMs», «📚 Termbases», «🌐 Web Resources», «⚙️ SuperLookup Settings»; source_text/search_btn/lang_from_combo/lang_to_combo = True; web_browser_mode/web_views/web_resource_checkboxes = True (`probe_before.log`) |

Среда: `E:\Dev\python-embed\python.exe`, CWD `E:\Dev\SupervertalerPortable` — как в AGENTS.md.

## 1. Рекон (без правок)

### 1.1 Сверка A2 с текущим монолитом

Пересчёт AST-границами: `class SuperlookupTab` = 59642–64506 (106 методов) на базе
64984 строк; сдвиг относительно A2 (база 68216 строк) — все номера A2 устарели,
методы §2.1/§2.2/§2.4a присутствуют все. Текущие границы — в
`D:\Temp\...\b8-10\sltab_map.json`. Расхождения с A2 — отдельной таблицей:

| # | A2 утверждал | Факт (проверка) | Решение в 8.10 |
|---|---|---|---|
| D1 | §2.1: вызыватели `_update_web_lang_info` — «только web-группа» | Также вызывается из KEEP-метода `_on_language_changed` (тот, в свою очередь, — из `set_project_languages` и двух `currentIndexChanged`-connect) — grep 61948 (база до правок) | `_on_language_changed` оставлен как охраняемый no-op (докстринг объясняет); вызов из `set_project_languages` удалён. Защита 2 подтвердила: после правок упоминаний `_update_web_lang_info` нет |
| D2 | §2.2: `capture_text` мёртв | Подтверждено (единственный `self.engine.capture_text()` внутри самого метода) | Удалён (z17). `modules/superlookup.py:83 SuperlookupEngine.capture_text` — другой класс, остаётся (движок KEEP) |
| D3 | §6.2 п.4: `on_ahk_mt_lookup_capture`/`show_mt_quick_lookup_from_ahk` — «мёртв (скрипта нет), уходит с AHK-группой в 8.10» | **НЕ мёртвы**: `on_ahk_mt_lookup_capture` вызывается из живого `_read_clipboard_for_quicktrans` (хвост цепочки Ctrl+Alt+Q из внешнего приложения: `_handle_quicktrans_hotkey` → `CrossPlatformKeySender.send_copy()` → `_read_clipboard_for_quicktrans` → `on_ahk_mt_lookup_capture`). Мёртв только file-watcher-источник (check_for_signal) | Первично вырезаны вместе с AHK-группой; **защита 2 поймала висячий вызов** (`self.on_ahk_mt_lookup_capture(text)` в `_read_clipboard_for_quicktrans`); оба метода восстановлены verbatim из снапшота `cut_z02_ahk_mt_capture.txt` (122 строки; они ссылаются только на остающееся: `MTQuickPopup`, `resolve_quicktrans_direction`, `_paste_translation_to_external_app`) |
| D4 | §4: «Поле `ahk_path_edit` в Settings General никогда не создаётся» | Поле **создаётся** — не в General, а на странице Settings → Keyboard Shortcuts (`modules/keyboard_shortcuts_widget.py`, `mw.ahk_path_edit = ahk_path_edit`), с кнопками через `mw._browse_autohotkey_for_settings`/`mw._find_autohotkey_for_settings` | AHK-блок страницы Keyboard Shortcuts удалён (файл разрешён постановкой «по рекону»); `_find_autohotkey_for_settings`/`_browse_autohotkey_for_settings` (монолит, 30 строк, вне таблиц A2 — согласуется с A2 §4 «удалить вместе с AHK-группой» и Stage1 §2.7 F7-кластером) удалены; `_save_general_settings_from_ui`: параметр `ahk_path_edit`, аргумент вызова и строка `'autohotkey_path'` удалены (вердикт A2 §4). Ключ в старых settings.json становится инертным |
| D5 | §2.2: регистрация `tools_universal_lookup` ≈174–179 | Подтверждено: `modules/shortcut_manager.py` 174–180 + алиасы 727/789 | Удалены (см. §1.6) |
| D6 | — (не в A2) | `_show_ahk_setup_from_menu` и стаб `_cleanup_web_views` не были включены в первичный список зон; защита 2 нашла оба | Удалены доп-прогоном `fix_810.py` (зоны z18/z19) |
| D7 | — (не в A2) | Модульные глобалы `_ahk_process` + блок в `cleanup_hotkey_processes` (atexit) — AHK-процессы больше не создаются | `_ahk_process` удалён (глобал, ветка atexit, `global`-строка в `register_global_hotkey`); pynput-половина atexit осталась |

### 1.2 Атрибуты и точечные правки SHARED-KEEP

| Метод | Правка |
|---|---|
| `__init__` | удалены `self.search_mt_enabled = False` и `self.search_web_enabled = False`; параметр `user_data_path` сохранён в сигнатуре (3 сайта создания) |
| `init_ui` | описание переписано без Ctrl+Alt+L (`"Type or paste text to search your TMs and Termbases."`, ветки nt/mac/linux схлопнуты); блок «# Web Resources tab» (3 строки) удалён; комментарий про ElideMode на Mac — без «Web Resources» |
| `create_settings_tab` | удалён блок радио «Ctrl+Alt+L lands on:» (37 строк) и блок `settings_subtabs` (20 строк: создание QTabWidget, Web-подвкладка, addWidget); header + resource_info (памятка про Read-флаги) сохранены; метод завершается `return tab`; комментарий v1.10.168 обновлён |
| `on_results_tab_changed` | удалены `web_index`/`quicktrans_index` (второй — мёртв с v1.10.10), web-ветка deferred-поиска (15 строк), web-буллет докстринга; Settings-ветка осталась |
| `perform_lookup` | удалён MT-блок (8 строк, вызов `_perform_mt_lookup`+`display_mt_results`) и весь deferred web-блок (41 строка); TM/термбаз-ветка (воркер `_SuperLookupSearchWorker`, `get_selected_tm_ids`/`get_selected_termbase_ids`, `display_*_results`, статусы) не тронута — AST-проверка (б) |
| `search_with_query` | удалён web-префетч (4 строки); `setCurrentIndex(0)` (путь Ctrl+K) сохранён |
| `set_project_languages` / `_on_language_changed` | см. D1 |

### 1.3 `register_global_hotkey` (NEEDS-SPLIT)

После правок (122 → 74 строки метода): единственный binding
`(qt_shortcut, self._on_pynput_quicktrans)` — AST-проверка (а) подтверждает.
Удалены: чтения `sl_shortcut` (`tools_universal_lookup`) и мёртвого `sk_shortcut`
(`sidekick_open`), `_skip('tools_universal_lookup')`, ветка AHK «Attempt 2»
(`self._register_hotkey_external_script()`), `global _ahk_process`; docstring
переписан (одна клавиша QuickTrans, стратегия без AHK-шага). Fallback при
неудаче менеджера: `self.hotkey_registered = False` (как и было для не-Windows).
`reload_global_hotkeys` (монолит) не тронут — вызывает `register_global_hotkey()`,
от удалённых переменных не зависит. `-`прочее: `_on_pynput_quicktrans`,
`_handle_quicktrans_hotkey`, `_read_clipboard_for_quicktrans`,
`_paste_translation_to_external_app`, `show_supervertaler_assistant`,
`set_compact_mode` — KEEP без правок (кроме докстринга `_on_pynput_quicktrans`,
ссылавшегося на удалённый `_on_pynput_superlookup`).

### 1.4 AHK-таблица (Этап 1 п.4)

| Место | Группа | Действие |
|---|---|---|
| `_find_autohotkey_executable`, `_show_autohotkey_setup_dialog`, `_open_ahk_download`, `_browse_for_autohotkey` (SuperlookupTab) | hotkey-SL/AHK §2.2 | удалены (z09) |
| `_register_hotkey_external_script`, `start_file_watcher`, `check_for_signal`, `_try_ahk_library_method`, `capture_text`, `on_ahk_capture`, `_on_pynput_superlookup`, `_handle_superlookup_hotkey`, `_read_clipboard_for_superlookup`, `show_superlookup`, `_fill_and_search` | hotkey-SL §2.2 | удалены (z01–z08, z17) |
| `on_ahk_mt_lookup_capture`, `show_mt_quick_lookup_from_ahk` | QuickTrans-сервис (живая цепочка Ctrl+Alt+Q извне) — см. D3 | **ОСТАЮТСЯ** (восстановлены после защиты 2) |
| `_find/_browse_autohotkey_for_settings` (монолит) + AHK-блок Keyboard Shortcuts | настройки AHK (D4) | удалены |
| `_prewarm_ahk` + вызов из `_warm_up_top_tabs` | прогрев paste-back QuickTrans (A2 §10 п.5) | ОСТАЮТСЯ |
| `CrossPlatformKeySender`, `platform_helpers` (`_find_ahk`, `_send_*_via_ahk`) | QuickTrans paste-back | ОСТАЮТСЯ (grep `_ahk` в modules — только platform_helpers) |
| pip-импорт `ahk` (`from ahk import AHK`) | был только в `_try_ahk_library_method` (63952 база) | удалён вместе с методом; **grep `import ahk`/`from ahk` по Supervertaler.py, modules/, tools/ после правок — 0** → requirements-строка снимается (СТОП-флага нет) |

### 1.5 QtWebEngine (Этап 1 п.5) — вывод: удаляется целиком, кроме орфана

Потребители на базе до правок: Supervertaler.py 60403–60404
(`create_web_resources_tab`), 60947 (`_create_web_view_container`) — обе в
web-группе; `main()` 64755–64791 (QTWEBENGINE_CHROMIUM_FLAGS, QT_LOGGING_RULES,
StderrFilter — все suppress-префиксы начинаются с `js:`, т.е. фильтр — чисто
WebEngine-шум) и 64801–64802 (AA_ShareOpenGLContexts). modules/**:
только `modules/feature_manager.py:95,312` — **модуль-сирота без импортёров**,
вне 8.10 по решению Дмитрия (постановка §НЕ-удалять). tools/** — 0. Ленивых
импортов/try-ImportError вне web-группы нет; warm-up WebEngine отсутствует.
Все перечисленные строки main() удалены (z25a/z25b).

### 1.6 Внешняя проводка и ShortcutManager

| Пункт | Действие |
|---|---|
| Edit-меню «🔍 &SuperLookup...» (Ctrl+Alt+L) | удалён целиком вместе с preceding-разделителем (решение Дмитрия, A2 §10.1) |
| In-app QShortcut `tools_universal_lookup` (create_shortcut 7239–7243) | удалён; комментарий переписан под оставшийся `sidekick_open` |
| Help-меню «⌨️ Setup AutoHotkey (Global Hotkey)» + `_show_ahk_setup_from_menu` | удалены (разделитель Help-меню сохранён — двойных разделителей нет) |
| closeEvent | ahk-блоки (`_using_ahk_library`/`_ahk`, `ahk_process`) удалены; pynput-блок (`_hotkey_manager`) сохранён |
| `_cleanup_web_views` | 3 вызова из closeEvent + no-op-стаб удалены |
| `_setup_superlookup_hotkeys` | докстринг и лог-строка: только Ctrl+Alt+Q; скрытый `self.lookup_tab` остаётся владельцем хоткея |
| detach/reattach | мёртвые `home_lookup_widget`-блоки удалены (доказательство мёртвости: 0 присваиваний `home_lookup_widget` во всём репо — только 3 чтения внутри hasattr-блоков; код ещё и звал `setPlainText` у HistoryComboBox) |
| shortcut_manager | запись `tools_universal_lookup` (174–180), `'global_superlookup'` из `_GLOBAL_TO_MERGED` и из `_LEGACY_IDS` удалены |
| keyboard_shortcuts_widget | группа «Global Hotkeys» — заголовок и инфо-только QuickTrans; AHK-блок удалён; `backend_label 'AutoHotkey'` → `'unknown'`; `IS_WINDOWS` убран из импорта |
| main() | z25a/z25b (см. §1.5) |
| requirements.txt | `-PyQt6-WebEngine>=6.5.0`, `-ahk>=1.0.0; sys_platform == "win32"` |

**Толерантность ShortcutManager к старым settings** (правило 8.2–8.5): загрузка
сохранённых `custom_shortcuts`/`disabled` не валидирует ID; `get_shortcut()` —
`_LEGACY_IDS.get(id, id)` → промах → проверка `custom_shortcuts` → `DEFAULT_SHORTCUTS`
→ дефолт-ветка не найдёт удалённый ID только если его кто-то запросит — а после
удаления из `register_global_hotkey`/`create_shortcut` запросов нет. Сохранённые
`shortcuts["tools_universal_lookup"]`/`"global_superlookup"` в пользовательском
файле — инертные ключи (U1.2: `dict(existing)` их сохраняет, конфликтов нет).
Страница Keyboard Shortcuts строит таблицу из `get_all_shortcuts()` (итерация
`DEFAULT_SHORTCUTS`) — удалённая строка в таблицу не попадает (T8.10.7).

### 1.7 Контрольный список остатков (Этап 1 п.9)

Инертные ключи настроек: `superlookup_landing_tab` (радио удалено, чтение
удалено, фолбэк не нужен), `autohotkey_path`, `hide_autohotkey_dialog`
(читателей в коде не осталось — grep 0). `_prewarm_ahk`/`CrossPlatformKeySender`
остаются (QuickTrans). Док-остатки — §7/раздел 7 (чистка в конце Batch #8).

## 2. Что сделано (зона | строки базы | действие)

Вырезанные зоны (снапшоты `snapshots\cut_*.txt`, всего **2397 строк зон**):

| Зона | Строки базы | Строк | Содержимое |
|---|---|---|---|
| z16_mt_group | 60090–60389 | 301 | `create_mt_results_tab`, `_open_mt_settings`, `_update_mt_provider_status`, `_perform_mt_lookup`, `_call_mymemory` (§2.4a) |
| z15_web_group | 60391–61549 | 1160 | web-группа §2.1: `create_web_resources_tab` … `_open_web_resource_external` (18 методов) |
| z14_landing_constants | 61551–61559 | 9 | `SUPERLOOKUP_LANDING_TAB_*` + комментарий |
| z13_landing_pref_methods | 61663–61687 | 26 | `_load_superlookup_landing_pref`, `_on_landing_pref_changed` |
| z12_mt_web_settings_subtabs | 61695–61795 | 102 | `create_mt_settings_subtab`, `create_web_settings_subtab` |
| z11_web_checkbox_changed | 61868–61881 | 15 | `_on_web_resource_checkbox_changed` |
| z17_capture_text | 62186–62211 | 27 | `capture_text` (мёртв) |
| z10_mt_display_group | 62967–63039 | 74 | `display_mt_results`, `_copy_mt_result`, `on_mt_result_double_click` (§2.4a) |
| z09_ahk_dialog_group | 63625–63793 | 170 | `_find_autohotkey_executable`, `_show_autohotkey_setup_dialog`, `_open_ahk_download`, `_browse_for_autohotkey` (§2.2) |
| z08_on_pynput_superlookup | 63918–63931 | 15 | `_on_pynput_superlookup` |
| z07_try_ahk_library | 63947–64014 | 69 | `_try_ahk_library_method` (единственный pip-импорт `ahk`) |
| z06_register_hotkey_external | 64016–64084 | 70 | `_register_hotkey_external_script` |
| z05_file_watcher_check_signal | 64086–64147 | 63 | `start_file_watcher`, `check_for_signal` |
| z04_handle_sl_hotkey | 64150–64189 | 41 | `_handle_superlookup_hotkey`, `_read_clipboard_for_superlookup` |
| z03_on_ahk_capture | 64240–64272 | 34 | `on_ahk_capture` |
| z02_ahk_mt_capture | 64274–64342 | 70 | `on_ahk_mt_lookup_capture`, `show_mt_quick_lookup_from_ahk` — вырезаны, затем **восстановлены** (D3) |
| z01_show_superlookup_fill_search | 64441–64506 | 67 | `show_superlookup`, `_fill_and_search` (мёртвые после удаления on_ahk_capture) |
| z21_autohotkey_for_settings | 22077–22105 | 30 | `_find/_browse_autohotkey_for_settings` (D4) |
| z26a/z26b home_lookup | 11718–11726 / 11755–11760 | 15 | мёртвые блоки detach/reattach |
| z25a_webengine_env | 64755–64791 | 37 | QTWEBENGINE_CHROMIUM_FLAGS, QT_LOGGING_RULES, StderrFilter |
| z25b_aa_share | 64801–64802 | 2 | AA_ShareOpenGLContexts + комментарий |
| z18/z19 (fix-прогон) | 55132–55141 / 55236–55243 | 19 | `_show_ahk_setup_from_menu`, стаб `_cleanup_web_views` |

Точечные правки (string-replace с assert count==1, ~250 строк суммарно): §1.2–§1.6.
Порядок: зоны снизу вверх по базе, затем string-правки; каждый `repl` — с
проверкой числа вхождений; каждая зона — с якорями первой/последней строки.

## 3. Диффы ключевых методов до/после

Полные тексты — git diff `6897539d`. Сводка:

- **`register_global_hotkey`**: docstring «Регистрирует глобальные горячие клавиши
  Superlookup, QuickTrans и Sidekick… Стратегия: 1. WinAPI/pynput 2. откат к AHK…»
  → «Регистрирует глобальную горячую клавишу QuickTrans (Ctrl+Alt+Q…)» без AHK-шага;
  чтения сокращены до `qt_shortcut`; `_bindings` — одна пара; хвост `Attempt 2`
  заменён на `self.hotkey_registered = False`.
- **`perform_lookup`**: docstring минус «MT и веб-поиск…»; после
  `QThreadPool.globalInstance().start(worker)` метод заканчивается (MT-try-block
  и web-deferred блок удалены); TM/термбаз-путь идентичен.
- **`init_ui`**: описание без Ctrl+Alt+L; `results_tabs` = TMs → Termbases →
  Settings (web addTab удалён); остальное идентично.
- **`main()`**: между блоком Linux-специфики и `app = QApplication(sys.argv)`
  больше нет WebEngine-строк; `_setup_diagnostic_log`/`_install_log_hooks` и
  Qt-message-handler не тронуты.

## 4. Статическая валидация (§4.1) и проверки

| Проверка | ДО | ПОСЛЕ | Вердикт |
|---|---|---|---|
| py_compile (весь репо) | 139/139 | **139/139** | OK |
| Защита 1: резолв стартовой цепочки (main, __init__, init_ui, create_menus, create_main_layout, setup_global_shortcuts, _setup_progress_indicators, _warm_up_top_tabs, create_settings_tab + страницы Settings, closeEvent, SuperlookupTab.__init__/init_ui/perform_lookup/search_with_query/on_results_tab_changed/register_global_hotkey) | 977 вызовов, 0 unresolved | **962 вызова, 0 unresolved** (`startup_chain_after.json`) | OK (−15 вызовов = удалённые connect/вызовы) |
| Защита 2: grep удалённых имён по Supervertaler.py, modules/, tools/ (все методы §2.1/§2.2/§2.4a, `web_browser_mode`, `web_engine_available`, `web_profile`, `web_views`, `web_resource_*`, `settings_subtabs`, `_landing_tab_*`, `SUPERLOOKUP_LANDING_TAB_*`, `_cleanup_web_views`, `tools_universal_lookup`, `global_superlookup`, `QTWEBENGINE_CHROMIUM_FLAGS`, `QT_LOGGING_RULES`, `StderrFilter`, `AA_ShareOpenGLContexts`, `QWebEngine`, `sl_shortcut`, `sk_shortcut`, `ahk_process`, `_using_ahk_library`, `mt_results_table`, `home_lookup_widget`, `search_web_enabled`, `search_mt_enabled`, `_web_search_pending`, `superlookup_landing_tab`, `autohotkey_path`, `hide_autohotkey_dialog`, `show_superlookup`, …) | — | 3 остатка (ниже) | OK |
| Защита 3: pyflakes undefined-names | 149 | **149, множество идентично** (`diff` пуст) | OK |
| AST (а): binding в `register_global_hotkey` | 2 (sl, qt) | **только `('qt_shortcut', '_on_pynput_quicktrans')`**; `mt_quick_lookup` → «Ctrl+Alt+Q», `global: True` в ShortcutManager | OK |
| AST (б): `perform_lookup` | — | TM/термбаз-ветка цела (worker, get_selected_*, display_*), MT/web-упоминаний 0 | OK |
| AST (в): `create_menus` | — | нет `Ctrl+Alt+L`/`Meta+Ctrl+L`/`ahk_setup_action`/`_show_ahk_setup_from_menu`/`_handle_superlookup_hotkey` | OK |
| AST (г): `save_general_settings()` без аргументов | 0 | **0** | OK |
| AST (д): импорты `PyQt6.QtWebEngine*` по репо | 2 файла | **только `modules/feature_manager.py:312`** — известное исключение (орфан без импортёров, вне 8.10 по решению Дмитрия) | OK с оговоркой |
| Headless-импорт modules/** | — | **114 ok / 7 fail / 121**; падения = известные предсуществующие: tkinter×5 (find_replace, pdf_rescue_tkinter, prompt_library, setup_wizard, tracked_changes), fitz (pdf_rescue_Qt), glossary_manager | OK, новых падений нет |
| Offscreen-проба ПОСЛЕ (`probe_after2.log`, финальные байты) | см. §0 | main_tabs **6**; Settings **14**; хоткеи при старте **только ctrl+alt+q** (WinAPI-регистрация прошла); SuperLookup results_tabs **3**: «📖 TMs», «📚 Termbases», «⚙️ SuperLookup Settings»; source_text/search_btn/lang_from_combo/lang_to_combo = True; web_browser_mode/web_views/web_resource_checkboxes = **False**; в стартовом логе **нет** «[Superlookup] QWebEngineView not available…» | OK |
| wc -l | Supervertaler.py 64984; shortcut_manager 1098; keyboard_shortcuts_widget 850; requirements 62 | **62387 / 1089 / 806 / 60** (монолит **−2597**) | соответствует порядку −2250+ (A2-оценка была до 8.2–8.7 и без учёта восстановления z02/правок Settings-страницы) |
| git diff --stat | — | Supervertaler.py 2622−/29+; keyboard_shortcuts_widget 48−/4+; shortcut_manager 9−; requirements 2−; **других файлов в коммите нет** | OK |
| EOL | `git ls-files --eol`: монолит w/crlf, модули w/lf | **без изменений** | OK (предсуществующая CRLF-копия монолита не тронута; инцидент с `\r\r\n` при восстановлении z02 найден и исправлен до коммита — см. §7) |

Допустимые остатки защиты 2 (полный список):
1. `modules/feature_manager.py:95,312` — `PyQt6.QtWebEngineWidgets` — модуль-сирота
   (0 импортёров по репо), НЕ в 8.10 по решению Дмитрия;
2. `Supervertaler.py:20` — докстринг модуля «Superlookup с глобальной горячей
   клавишей (Ctrl+Alt+L)»;
3. `Supervertaler.py:62177` — комментарий в main() «…или инициализации QWebEngine»;
4. `Supervertaler.py:24479` — докстринг «легаси-маршрут Sidekick.show_superlookup(text)»;
5. `modules/superlookup.py:83` — `SuperlookupEngine.capture_text` (другой класс, движок KEEP);
6. `modules/platform_helpers.py` `_ahk*` — CrossPlatformKeySender/QuickTrans (KEEP);
   `Supervertaler.py` `_prewarm_ahk` (решение A2 §10.5);
7. исторические упоминания Ctrl+Alt+L в докстрингах/комментариях остающегося кода
   (9733, 9825, 22001, 24478, 27978 монолита; 662 platform_helpers; 676, 1135
   quicktrans) — док-остатки, чистка в конце Batch #8.

Пункты 2–4, 7 — на чистку финального docs-прохода Batch #8 (постановка: «Док-остатки — чистка в конце Batch #8»).

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: состояние после 8.7 (код `acfe8880`). Копировать из рабочей копии
репо (E:\Dev\SupervertalerPortable) после этого коммита (`6897539d`):

| № | Путь | Действие | SHA256 (рабочая копия) | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | заменить | `b7fb94cd4e4a95c672b25f254ec200671131b51bde48e6fcbfba5c4899e7e981` | 62387 строк; файл идентичен репо (в т.ч. CRLF) |
| 2 | `modules/shortcut_manager.py` | заменить | `265396e5fd2b27c627d85a79ddade027708dec490eaa7253be414767136359b1` | 1089 строк |
| 3 | `modules/keyboard_shortcuts_widget.py` | заменить | `09e799f14f52a40bcd0fddb1548af1a8111d9bdbaa8eab3f5be8c234641feef7` | 806 строк |
| 4 | `requirements.txt` | заменить | `4517593376fd567e136bc62c37c7544b355c9b1e9d32553f79f4f84853d8e214` | 60 строк; на работу сборки не влияет, для порядка |
| 5 | — | после ручной проверки T8.10.1–T8.10.9: `pip uninstall PyQt6-WebEngine PyQt6-WebEngine-Qt6` (≈340 МБ) в тестовой сборке, затем T8.10.10 | — | см. T8.10.10 |

Других файлов пакет не требует (`git diff --stat` коммита = ровно эти 4 файла).

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data; сначала КОНТРОЛЬ на базовой сборке, затем после замены файлов)

- **T8.10.1** Старт без исключений; в логе нет «[Superlookup] QWebEngineView
  available…» (offscreen-проба подтвердила отсутствие строки) и ошибок
  регистрации хоткеев, кроме возможно занятого Ctrl+Alt+Q.
- **T8.10.2** Вкладка SuperLookup: подвкладки ровно «📖 TMs», «📚 Termbases»,
  «⚙️ SuperLookup Settings»; поиск, поля From/To, история на месте
  (offscreen подтвердил состав и наличие виджетов).
- **T8.10.3** Поиск: тестовый проект, включить SuperLookup-флаг у TM и термбазы;
  поиск из SuperLookup и из редактора (Ctrl+K, контекстное меню «Search in
  SuperLookup») — результаты TM/термбаз приходят, нет исключений.
- **T8.10.4** Settings → SuperLookup Settings: нет радио «Ctrl+Alt+L lands on:»,
  нет подвкладки Web Resources, осталась памятка про Read-флаги; старый
  settings.json со значением `superlookup_landing_tab: webresources` стартует
  без ошибок (ключ игнорируется).
- **T8.10.5** Хоткеи: Ctrl+Alt+L ни глобально, ни в приложении ничего не
  вызывает (пункта в Edit-меню нет); Ctrl+Alt+Q из Блокнота открывает
  QuickTrans-попап и вставка перевода работает (в т.ч. путь через
  восстановленные `on_ahk_mt_lookup_capture`/`show_mt_quick_lookup_from_ahk`);
  Ctrl+Shift+Q в приложении; Ctrl+K работает.
- **T8.10.6** Tools-меню: 12 пунктов, «Super&lookup (Ctrl+K)» на месте;
  Edit-меню без пункта SuperLookup; Help-меню без пункта AutoHotkey Setup.
- **T8.10.7** Settings → Keyboard Shortcuts: QuickTrans/Concordance на месте,
  «Superlookup (Ctrl+Alt+L)» нет; группа Global Hotkeys упоминает только
  QuickTrans; смена Ctrl+Alt+Q переживает перезапуск.
- **T8.10.8** Editor: вставка из SuperLookup, «Ask AI assistant»; detach/reattach
  SuperLookup работает (мёртвые home_lookup-блоки удалены).
- **T8.10.9** live-test: импорт файла 180/400 сегментов; перевод сегмента; Save;
  настройка переживает перезапуск; навигация по вкладкам.
- **T8.10.10** БЕЗ WebEngine: после T8.10.1–9 выполнить в тестовой сборке
  `pip uninstall PyQt6-WebEngine PyQt6-WebEngine-Qt6`, запустить заново — старт
  и базовые сценарии (T8.10.1, T8.10.2, T8.10.9) проходят.
- **T8.10.11** Выход: иконка трея исчезает, процесс завершается (флаки-краш
  0xC0000005 — предсуществующий), в логе нет traceback и ahk-хвостов
  (`cleanup_hotkey_processes` теперь чистит только pynput).

## 7. Непокрытые проверки

1. **OS-глобальный хоткей Ctrl+Alt+Q вне offscreen** — offscreen-проба показала
   успешную WinAPI-регистрацию и старт менеджера, но живой перехват клавиши из
   другого приложения — только ручная T8.10.5.
2. **Реальные settings.json** Дмитрия (наличие `superlookup_landing_tab` /
   `autohotkey_path` / сохранённого `tools_universal_lookup`) — user_data не
   читался; все три ключа инертны по коду, но фактическое наличие не проверено.
3. **`modules/feature_manager.py`** — остаётся единственным импортёром
   QtWebEngine; судьба модуля (и pyproject `web = []`) — отдельное решение.
4. **EOL-инцидент**: восстановление z02 из снапшота первично дало `\r\r\n`
   (двойной CR на 70 строках) — поймано по расхождению `git diff --stat`
   (whole-file rewrite) и счётчикам CR/LF, исправлено (`\r\r\n` → `\r\n`, ровно
   70 замен) до коммита; финальные проверки (py_compile, защиты 1–3, AST,
   headless, probe_after2) выполнены уже на исправленных байтах. Работа git с
   предсуществующей CRLF-копией монолита (нормализация на commit) проверена
   тестовым файлом в репо.
5. **Контекстные меню редакторов** (Ctrl+K) — статически не задеты; живое
   поведение — T8.10.3.
6. **pip-пакет `ahk` в тестовой сборке** — из requirements удалён; фактический
   `pip uninstall ahk` в сборке не требуется для работы (пакет импортировался
   только удалённым `_try_ahk_library_method`), но остаётся в site-packages —
   почистить опционально при следующей пересборке.
7. **Performance `perform_lookup`** — после удаления MT/web-хвостов путь стал
   короче; отдельного замера не делалось.

## 8. Вопросы к Дмитрию

1. **`modules/feature_manager.py`** (орфан, 0 импортёров, импортирует QtWebEngine):
   удалить целиком вместе с pyproject `web = []` — или отложить до финального
   инвентаря сирот в конце Batch #8? (Постановка 8.10: «отдельное решение».)
2. **Док-остатки Ctrl+Alt+L / WebEngine** (список в §4, п. 2–4 и 7): чистить
   финальным docs-проходом Batch #8, как запланировано, — подтверждаете?
3. **Опционально**: `pip uninstall ahk` в тестовой сборке вместе с
   T8.10.10 (пакет больше нигде не импортируется) — включить в сценарий или
   почистить при следующей пересборке?
