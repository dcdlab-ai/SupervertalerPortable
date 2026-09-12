# DEAD_CODE_REPORT.md
**Проект:** Supervertaler — аудит неиспользуемого кода
**Дата:** 2026-09-12 • **НИЧЕГО НЕ УДАЛЕНО** (режим STRICT READ-ONLY)

Методика: метод объявлялся кандидатом ТОЛЬКО после исчерпания всех известных динамических механизмов:
(1) все 781 `.connect()` с разрешением целей через AST (включая lambda-тела и переносы строк);
(2) QTimer.timeout и QTimer.singleShot; (3) QShortcut + реестр `ShortcutManager.create_shortcut` (~35 обработчиков);
(4) threading.Thread/Timer targets; (5) `QMetaObject.invokeMethod` по строке (2 сайта → `_handle_superlookup_hotkey`, `_handle_quicktrans_hotkey` — LIVE);
(6) строковые константы = именам методов (77 совпадений); (7) getattr/hasattr/setattr со строковыми именами (747/1189/8);
(8) duck-typed атрибутные вызовы из modules/ и вложенных классов по базам `main_window/parent_app/mw/_main_window/_parent_app/…`;
(9) Qt-override имена (closeEvent/keyPressEvent/eventFilter/…); (10) property/staticmethod/classmethod;
(11) connectSlotsByName — в проекте НЕ используется (проверено);
(12) внешние импортеры монолита — отсутствуют (0 файлов импортируют Supervertaler.py).

# DEFINITELY_DEAD (16 методов)

## Zero-ref методы SupervertalerQt

Критерий: ровно одна textualная ссылка во всех 125 .py-файлах — собственное определение. Все 12 динамических механизмов выше исключены.

| # | Объект | Расположение | Evidence | Safe next action |
|---|---|---|---|---|
| 1 | `_REMOVED_add_mt_and_llm_matches_progressive` | Supervertaler.py:66629–66902 (274L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 2 | `_add_mt_and_llm_matches` | Supervertaler.py:66904–67091 (188L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 3 | `_clear_selection_anchor` | Supervertaler.py:32036–32039 (4L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 4 | `_create_compare_panel` | Supervertaler.py:44912–44986 (75L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 5 | `_create_placeholder_tab` | Supervertaler.py:13407–13422 (16L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 6 | `_force_termlens_display_redraw` | Supervertaler.py:19705–19747 (43L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 7 | `_get_api_keys` | Supervertaler.py:14784–14787 (4L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 8 | `_on_results_panel_notes_changed` | Supervertaler.py:57376–57414 (39L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 9 | `_open_superdocs_tab` | Supervertaler.py:62184–62194 (11L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 10 | `_register_voice_command_ptt_deferred` | Supervertaler.py:58592–58613 (22L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 11 | `_restore_active_prompt` | Supervertaler.py:51847–51887 (41L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 12 | `_restore_active_style_guide` | Supervertaler.py:51889–51904 (16L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 13 | `_save_llm_settings_from_ui` | Supervertaler.py:29585–29665 (81L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 14 | `_show_data_location_dialog` | Supervertaler.py:9629–9748 (120L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 15 | `_show_edit_terms_dialog` | Supervertaler.py:22570–22902 (333L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |
| 16 | `_show_tm_context_menu` | Supervertaler.py:15968–16026 (59L) | Единственная textualная ссылка в 125 файлах — собственный def. Проверено: .connect (все 781, вкл. lambda-цели), QTimer timeout/singleShot, QShortcut+ShortcutManager, threading.Thread/Timer targets, QMetaObject.invokeMethod (все строки), getattr/hasattr/setattr строки, duck-typed атрибуты из modules/ и вложенных классов, Qt-override имена, property/staticmethod. Не является override/property. | Подтвердить владельцем → удалить (или пометить @deprecated) |

# PROBABLY_DEAD (57 методов)

## Публичные zero-ref

| # | Объект | Расположение | Evidence | Safe next action |
|---|---|---|---|---|
| 1 | `clear_tm_entries` | Supervertaler.py:18610 (38L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 2 | `create_assistance_panel` | Supervertaler.py:32524 (161L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 3 | `create_grid_view_widget` | Supervertaler.py:30525 (147L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 4 | `create_prompt_manager_tab` | Supervertaler.py:13424 (11L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 5 | `create_quick_access_toolbar` | Supervertaler.py:13066 (44L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 6 | `create_ribbon_toolbar` | Supervertaler.py:13135 (5L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 7 | `create_superdocs_tab` | Supervertaler.py:14773 (10L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 8 | `detach_superlookup` | Supervertaler.py:15255 (132L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 9 | `export_for_ai` | Supervertaler.py:37468 (280L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 10 | `export_tm_as_tmx` | Supervertaler.py:18603 (3L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 11 | `filter_empty_segments` | Supervertaler.py:56828 (43L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 12 | `focus_segment_notes` | Supervertaler.py:10612 (29L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 13 | `get_status_icon` | Supervertaler.py:49088 (3L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 14 | `get_themed_button_style` | Supervertaler.py:66086 (25L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 15 | `get_themed_panel_style` | Supervertaler.py:66112 (26L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 16 | `highlight_preview_segment` | Supervertaler.py:46868 (10L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 17 | `import_tmx_file` | Supervertaler.py:16056 (176L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 18 | `insert_compare_panel_mt` | Supervertaler.py:60245 (5L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 19 | `insert_compare_panel_tm_target` | Supervertaler.py:60251 (5L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 20 | `on_font_changed` | Supervertaler.py:47785 (4L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 21 | `on_main_tab_changed` | Supervertaler.py:13152 (5L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 22 | `on_match_selected` | Supervertaler.py:32686 (5L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 23 | `results_pane_zoom_reset` | Supervertaler.py:47817 (8L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 24 | `save_dictation_settings` | Supervertaler.py:48617 (55L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 25 | `save_grid_segment_and_next` | Supervertaler.py:59673 (19L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 26 | `save_tab_segment_and_next` | Supervertaler.py:59512 (9L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 27 | `save_termbase_code_map` | Supervertaler.py:52841 (8L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 28 | `show_file_progress_dialog` | Supervertaler.py:66028 (3L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 29 | `show_options_dialog` | Supervertaler.py:61548 (4L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 30 | `show_proofreading_results_dialog` | Supervertaler.py:51381 (105L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 31 | `show_ribbon_temporarily` | Supervertaler.py:13147 (4L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 32 | `show_search_dialog` | Supervertaler.py:55403 (54L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 33 | `test_cell_selection` | Supervertaler.py:50217 (10L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 34 | `toggle_ribbon_minimized` | Supervertaler.py:13141 (5L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 35 | `update_compare_panel` | Supervertaler.py:45890 (28L) | Zero textual-ссылок (анализ идентичен DEFINITELY), но публичное имя — сохранена консервативность (возможен внешний вызов по имени вне репозитория) | Подтвердить владельцем → удалить |
| 36 | `_perform_delayed_lookup` | Supervertaler.py:51939 (301L) | вызывается только из _schedule_delayed_lookup (zero-ref) | Удалить цепочку целиком после подтверждения |
| 37 | `search_and_display_tm_matches` | Supervertaler.py:52458 (332L) | только из мёртвого _perform_delayed_lookup (51963) | Удалить цепочку целиком после подтверждения |
| 38 | `create_diff_html` | Supervertaler.py:52791 (37L) | только из мёртвого search_and_display_tm_matches (52770) | Удалить цепочку целиком после подтверждения |
| 39 | `_fetch_llm_translation_async` | Supervertaler.py:65276 (127L) | только из мёртвого _perform_delayed_lookup | Удалить цепочку целиком после подтверждения |
| 40 | `_fetch_mt_translation_async` | Supervertaler.py:65404 (124L) | только из мёртвого _perform_delayed_lookup | Удалить цепочку целиком после подтверждения |
| 41 | `search_segments` | Supervertaler.py:55458 (35L) | только из мёртвого show_search_dialog | Удалить цепочку целиком после подтверждения |
| 42 | `_show_language_variant_dialog` | Supervertaler.py:16233 (65L) | только из мёртвого import_tmx_file | Удалить цепочку целиком после подтверждения |
| 43 | `_set_tm_as_project` | Supervertaler.py:16028 (8L) | только из мёртвого _show_tm_context_menu | Удалить цепочку целиком после подтверждения |
| 44 | `_unset_tm_as_project` | Supervertaler.py:16037 (8L) | только из мёртвого _show_tm_context_menu | Удалить цепочку целиком после подтверждения |
| 45 | `_toggle_tm_readonly` | Supervertaler.py:16046 (9L) | только из мёртвого _show_tm_context_menu | Удалить цепочку целиком после подтверждения |
| 46 | `add_precision_scroll_buttons` | Supervertaler.py:32395 (71L) | единственный вызов закомментирован: Supervertaler.py:32393 | Проверить git-планы → удалить |
| 47 | `create_ribbon` | Supervertaler.py:13111 (7L) | единственный вызов закомментирован: Supervertaler.py:10095 | Проверить git-планы → удалить |
| 48 | `_on_bottom_notes_changed` | Supervertaler.py:58143 (47L) | упоминания только в комментариях (2054, 31251); не подключён к textChanged | Проверить git-планы → удалить |
| 49 | `_refresh_current_segment_matches` | Supervertaler.py:61212 (7L) | упоминания только в комментариях (61196) | Проверить git-планы → удалить |
| 50 | `insert_term_translation` | Supervertaler.py:53322 (45L) | остальные 2 совпадения — лог-строки внутри самого метода (53359) | Проверить git-планы → удалить |
| 51 | `toggle_tag_view` | Supervertaler.py:61341 (3L) | дубль _toggle_tag_view_via_shortcut; zero прямых вызовов вне def+call от мёртвых путей | Проверить git-планы → удалить |
| 52 | `results_pane_zoom_in` | Supervertaler.py:47799 (8L) | нет вызовов и динамических ссылок | Проверить git-планы → удалить |
| 53 | `results_pane_zoom_out` | Supervertaler.py:47808 (8L) | нет вызовов и динамических ссылок | Проверить git-планы → удалить |
| 54 | `_clean_provider_prefix` | Supervertaler.py:67093 (6L) | zero-ref; дубль translation_services.py | Проверить git-планы → удалить |
| 55 | `_schedule_delayed_lookup` | Supervertaler.py:51906 (32L) | zero-ref; корень мёртвой legacy-цепочки lookup | Проверить git-планы → удалить |
| 56 | `_search_termbases_thread_safe` | Supervertaler.py:34708 (190L) | zero-ref (190 строк); поток-потребитель не существует | Проверить git-планы → удалить |
| 57 | `_register_voice_pushtotalk_deferred` | Supervertaler.py:58573 (16L) | zero-ref; заменено _get_voice_hotkey_listener | Проверить git-планы → удалить |

# Затенённые (shadowed) определения — мертвы по семантике Python (5)

## Shadowed

Поздний def в том же scope молча заменяет ранний: тело раннего недостижимо. При переносе переносить только ПОСЛЕДНЕЕ определение.

| # | Объект | Расположение | Evidence | Safe next action |
|---|---|---|---|---|
| 1 | `show_about @62004` | Supervertaler.py:62004 | Затенён более поздним определением @62868 (Python: поздний def побеждает) — тело недостижимо | Удалить затёртое первое определение; поведение не изменится |
| 2 | `closeEvent @33453` | Supervertaler.py:33453 | Затенён более поздним определением @62932 (Python: поздний def побеждает) — тело недостижимо | Удалить затёртое первое определение; поведение не изменится |
| 3 | `ReadOnlyGridTextEditor.keyPressEvent @3342` | Supervertaler.py:3342 | Затенён более поздним определением @3950 (Python: поздний def побеждает) — тело недостижимо | Удалить затёртое первое определение; поведение не изменится |
| 4 | `ReadOnlyGridTextEditor._handle_quick_add_to_glossary_priority @3566` | Supervertaler.py:3566 | Затенён более поздним определением @4003 (Python: поздний def побеждает) — тело недостижимо | Удалить затёртое первое определение; поведение не изменится |
| 5 | `ReadOnlyGridTextEditor._get_main_window @3572` | Supervertaler.py:3572 | Затенён более поздним определением @4294 (Python: поздний def побеждает) — тело недостижимо | Удалить затёртое первое определение; поведение не изменится |

# DYNAMIC_ENTRY_POINT

Методы без единого прямого вызова, но с подтверждённым динамическим входом — НЕ dead, при рефакторинге их имена/сигнатуры менять нельзя:

| # | Метод | Строка | Механизм входа |
|---|---|---|---|
| 1 | `_show_first_run_welcome` | 9806 | TIMER_SINGLESHOT |
| 2 | `add_comment_from_selection` | 10421 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 3 | `open_clipboard_tab` | 10642 | ARG_REF |
| 4 | `open_quicklauncher` | 10656 | ARG_REF |
| 5 | `show_supervertaler_assistant` | 10713 | EXTERNAL_ATTR_REF |
| 6 | `_on_bridge_prompt_request` | 10747 | SIGNAL_SLOT |
| 7 | `show_term_insert_popup` | 10832 | EXTERNAL_ATTR_REF |
| 8 | `show_term_picker_dialog` | 10991 | ARG_REF |
| 9 | `set_quicktrans_direction_override` | 11074 | EXTERNAL_ATTR_REF |
| 10 | `show_mt_quick_popup` | 11102 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 11 | `refresh_shortcut_enabled_states` | 11217 | EXTERNAL_ATTR_REF |
| 12 | `_ping_ollama_keepwarm` | 11406 | TIMER |
| 13 | `undo_action_handler` | 12569 | EXTERNAL_ATTR_REF, HASATTR_REF, MENU_ACTION, STRING_REF |
| 14 | `redo_action_handler` | 12585 | EXTERNAL_ATTR_REF, HASATTR_REF, MENU_ACTION, STRING_REF |
| 15 | `delete_current_segments` | 12784 | MENU_ACTION |
| 16 | `split_current_segment` | 12809 | ARG_REF |
| 17 | `merge_current_segment` | 12840 | ARG_REF |
| 18 | `open_superbrowser_window` | 13437 | MENU_ACTION |
| 19 | `open_tmx_editor_window` | 13479 | MENU_ACTION |
| 20 | `show_statistics_dialog` | 13536 | MENU_ACTION |
| 21 | `show_quick_statistics_dialog` | 13661 | MENU_ACTION |
| 22 | `open_pdf_rescue_window` | 14094 | MENU_ACTION |
| 23 | `_on_add_docx_file_for_extraction` | 14127 | SIGNAL_SLOT |
| 24 | `_on_add_docx_folder_for_extraction` | 14142 | SIGNAL_SLOT |
| 25 | `_on_browse_output_dir_for_extraction` | 14166 | SIGNAL_SLOT |
| 26 | `_on_auto_folder_toggled` | 14176 | SIGNAL_SLOT |
| 27 | `_on_file_list_item_clicked` | 14186 | SIGNAL_SLOT |
| 28 | `_on_extract_images` | 14413 | SIGNAL_SLOT |
| 29 | `_on_preview_prev` | 14617 | SIGNAL_SLOT |
| 30 | `_on_preview_next` | 14623 | SIGNAL_SLOT |
| 31 | `_on_load_image_context_folder` | 14631 | SIGNAL_SLOT |
| 32 | `_on_clear_image_context` | 14747 | SIGNAL_SLOT |
| 33 | `show_concordance_search` | 14789 | ARG_REF, EXTERNAL_ATTR_REF, MENU_ACTION |
| 34 | `show_tm_manager_tab` | 14867 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 35 | `_show_tm_maintenance_dialog` | 14885 | SIGNAL_SLOT |
| 36 | `detach_log_window` | 15019 | EXTERNAL_ATTR_REF, MENU_ACTION, SIGNAL_SLOT, TIMER_SINGLESHO |
| 37 | `clear_log` | 15033 | SIGNAL_SLOT |
| 38 | `_on_main_tab_changed` | 15049 | SIGNAL_SLOT |
| 39 | `_warm_up_top_tabs` | 15090 | TIMER_SINGLESHOT |
| 40 | `reattach_superlookup` | 15388 | SIGNAL_SLOT |
| 41 | `export_document` | 16299 | MENU_ACTION |
| 42 | `export_review_table_with_tags` | 17807 | MENU_ACTION |
| 43 | `export_tmx_from_selected` | 18431 | MENU_ACTION |
| 44 | `export_tmx_from_tm_database` | 18523 | MENU_ACTION |
| 45 | `test_segmentation_rules` | 18739 | SIGNAL_SLOT |
| 46 | `add_term_pair_to_termbase` | 19283 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 47 | `_on_termbase_db_debounce_fire` | 19689 | TIMER |
| 48 | `add_word_to_dictionary_shortcut` | 20137 | ARG_REF |
| 49 | `add_text_to_non_translatables` | 20173 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 50 | `_sync_external_tms` | 23630 | TIMER |
| 51 | `_save_mt_quick_lookup_settings` | 25732 | SIGNAL_SLOT |
| 52 | `open_mt_quick_lookup_settings` | 25772 | EXTERNAL_ATTR_REF |
| 53 | `_find_autohotkey_for_settings` | 25804 | EXTERNAL_ATTR_REF |
| 54 | `_browse_autohotkey_for_settings` | 25822 | EXTERNAL_ATTR_REF |
| 55 | `_reset_voice_commands` | 28066 | EXTERNAL_ATTR_REF |
| 56 | `_check_ahk_installed` | 28080 | EXTERNAL_ATTR_REF |
| 57 | `_open_voice_scripts_folder` | 28088 | EXTERNAL_ATTR_REF |
| 58 | `_on_alwayson_tray_activated` | 28447 | SHORTCUT |
| 59 | `_on_alwayson_speech` | 28485 | SIGNAL_SLOT |
| 60 | `_on_alwayson_command` | 28489 | SIGNAL_SLOT |
| 61 | `_on_alwayson_dictation` | 28494 | SIGNAL_SLOT |
| 62 | `_on_alwayson_status` | 28530 | SIGNAL_SLOT |
| 63 | `_on_alwayson_error` | 28537 | SIGNAL_SLOT |
| 64 | `_on_alwayson_vad_status` | 28542 | SIGNAL_SLOT |
| 65 | `_open_voice_in_workbench` | 28951 | MENU_ACTION, SIGNAL_SLOT |
| 66 | `_verify_foreground_grab` | 29121 | TIMER_SINGLESHOT |
| 67 | `open_settings_to_keyboard_shortcuts` | 29373 | EXTERNAL_ATTR_REF |
| 68 | `reload_global_hotkeys` | 29398 | EXTERNAL_ATTR_REF |
| 69 | `export_debug_log_now` | 29549 | SIGNAL_SLOT |
| 70 | `clear_debug_log_buffer` | 29578 | SIGNAL_SLOT |
| 71 | `go_to_prev_page` | 31929 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, SIGNAL_SLOT, STRING |
| 72 | `go_to_next_page` | 31937 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, SIGNAL_SLOT, STRING |
| 73 | `select_range_page_up` | 31946 | ARG_REF |
| 74 | `select_range_page_down` | 31980 | ARG_REF |
| 75 | `on_page_size_changed` | 32071 | EXTERNAL_ATTR_REF, HASATTR_REF, SIGNAL_SLOT, STRING_REF |
| 76 | `_switch_settings_subtab` | 32136 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 77 | `new_project` | 32777 | MENU_ACTION |
| 78 | `_setup_tray_icon` | 33060 | EXTERNAL_ATTR_REF |
| 79 | `_on_tray_activated` | 33185 | SHORTCUT |
| 80 | `_on_toggle_close_to_tray` | 33411 | SIGNAL_SLOT |
| 81 | `_on_toggle_start_minimized` | 33416 | SIGNAL_SLOT |
| 82 | `_on_toggle_autostart` | 33421 | SIGNAL_SLOT |
| 83 | `_tray_quit` | 33447 | MENU_ACTION |
| 84 | `closeEvent` | 33453 | EXTERNAL_ATTR_REF |
| 85 | `open_project` | 33521 | MENU_ACTION |
| 86 | `_termbase_batch_worker_run` | 34650 | THREAD_TARGET |
| 87 | `_prefetch_worker_run` | 34974 | THREAD_TARGET |
| 88 | `perform_auto_backup` | 35704 | TIMER |
| 89 | `close_project` | 35759 | MENU_ACTION |
| 90 | `clear_recent_projects` | 36039 | MENU_ACTION |
| 91 | `import_document` | 36078 | MENU_ACTION |
| 92 | `import_simple_txt` | 36917 | MENU_ACTION |
| 93 | `export_simple_txt` | 37291 | MENU_ACTION |
| 94 | `import_folder_multifile` | 37753 | MENU_ACTION |
| 95 | `relocate_source_folder` | 38298 | MENU_ACTION |
| 96 | `export_folder_multifile` | 38429 | MENU_ACTION |
| 97 | `import_memoq_bilingual` | 39054 | MENU_ACTION |
| 98 | `import_memoq_rtf` | 39419 | MENU_ACTION |
| 99 | `export_memoq_bilingual` | 39690 | MENU_ACTION |
| 100 | `import_memoq_xliff` | 40073 | MENU_ACTION |
| 101 | `export_memoq_rtf` | 40346 | MENU_ACTION |
| 102 | `export_memoq_xliff` | 40463 | MENU_ACTION |
| 103 | `import_po_file` | 40576 | MENU_ACTION |
| 104 | `export_po_file` | 40699 | MENU_ACTION |
| 105 | `import_cafetran_bilingual` | 40804 | MENU_ACTION |
| 106 | `import_trados_bilingual` | 40954 | MENU_ACTION |
| 107 | `export_trados_bilingual` | 41223 | MENU_ACTION |
| 108 | `import_sdlppx_package` | 41367 | MENU_ACTION |
| 109 | `export_sdlrpx_package` | 41782 | MENU_ACTION |
| 110 | `import_standalone_sdlxliff` | 42030 | MENU_ACTION |
| 111 | `import_sdlxliff_folder` | 42238 | MENU_ACTION |
| 112 | `export_standalone_sdlxliff` | 42441 | MENU_ACTION |
| 113 | `import_phrase_bilingual` | 42591 | MENU_ACTION |
| 114 | `export_phrase_bilingual` | 42876 | MENU_ACTION |
| 115 | `import_dejavu_bilingual` | 43051 | MENU_ACTION |
| 116 | `export_dejavu_bilingual` | 43216 | MENU_ACTION |
| 117 | `import_review_table` | 43369 | MENU_ACTION |
| 118 | `export_bilingual_markdown` | 43701 | MENU_ACTION |
| 119 | `import_bilingual_markdown` | 43880 | MENU_ACTION |
| 120 | `export_cafetran_bilingual` | 44113 | MENU_ACTION |
| 121 | `_match_panel_tm_context_menu` | 45291 | SIGNAL_SLOT |
| 122 | `_match_panel_edit_tm_entry` | 45375 | MENU_ACTION |
| 123 | `_match_panel_delete_tm_entry` | 45452 | MENU_ACTION |
| 124 | `_open_preview_window` | 46164 | SIGNAL_SLOT |
| 125 | `_toggle_preview_panel` | 46211 | ARG_REF |
| 126 | `_refresh_preview_on_show` | 46508 | TIMER_SINGLESHOT |
| 127 | `_on_bottom_tab_changed` | 47261 | SIGNAL_SLOT |
| 128 | `_on_match_top_tab_changed` | 47280 | SIGNAL_SLOT |
| 129 | `_insert_quicktrans_translation` | 47294 | SIGNAL_SLOT |
| 130 | `_on_column_resized` | 47470 | SIGNAL_SLOT |
| 131 | `zoom_in` | 47791 | EXTERNAL_ATTR_REF, HASATTR_REF, MENU_ACTION, STRING_REF |
| 132 | `zoom_out` | 47795 | EXTERNAL_ATTR_REF, HASATTR_REF, MENU_ACTION, STRING_REF |
| 133 | `match_panel_zoom_in` | 47835 | MENU_ACTION |
| 134 | `match_panel_zoom_out` | 47842 | MENU_ACTION |
| 135 | `match_panel_zoom_reset` | 47849 | MENU_ACTION |
| 136 | `get_autocorrect_settings` | 48289 | EXTERNAL_ATTR_REF |
| 137 | `save_voice_vocabulary_settings` | 48738 | EXTERNAL_ATTR_REF |
| 138 | `open_termbases_tab` | 48790 | EXTERNAL_ATTR_REF |
| 139 | `on_cell_changed` | 49220 | SIGNAL_SLOT |
| 140 | `_schedule_click_center` | 49342 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 141 | `on_selection_changed` | 50194 | SIGNAL_SLOT |
| 142 | `_preview_combined_prompt_from_grid` | 50279 | SIGNAL_SLOT |
| 143 | `show_grid_context_menu` | 50585 | SIGNAL_SLOT |
| 144 | `clear_selected_translations_from_menu` | 50684 | MENU_ACTION |
| 145 | `copy_source_to_target_bulk` | 50694 | MENU_ACTION |
| 146 | `copy_source_to_target_non_translatable_bulk` | 50788 | MENU_ACTION |
| 147 | `pseudo_translate_bulk` | 50890 | MENU_ACTION |
| 148 | `_copy_source_to_target_selected` | 50901 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 149 | `show_clean_tags_dialog` | 50950 | MENU_ACTION |
| 150 | `show_proofread_dialog` | 51062 | MENU_ACTION |
| 151 | `send_segments_to_tm_dialog` | 51487 | MENU_ACTION |
| 152 | `on_cell_clicked` | 52241 | SIGNAL_SLOT |
| 153 | `on_cell_double_clicked` | 52260 | SIGNAL_SLOT |
| 154 | `show_find_replace_dialog` | 53402 | MENU_ACTION |
| 155 | `_fr_load_operation` | 53810 | SIGNAL_SLOT |
| 156 | `_fr_run_set_batch` | 53870 | SIGNAL_SLOT |
| 157 | `show_goto_dialog` | 54906 | ARG_REF, MENU_ACTION |
| 158 | `_on_file_filter_changed` | 55794 | SIGNAL_SLOT |
| 159 | `toggle_all_invisibles` | 56101 | MENU_ACTION |
| 160 | `_toggle_spellcheck` | 56358 | MENU_ACTION |
| 161 | `_toggle_spellcheck_from_button` | 56406 | SIGNAL_SLOT |
| 162 | `_open_custom_dictionary_dialog` | 56508 | MENU_ACTION |
| 163 | `_show_spellcheck_info` | 56581 | MENU_ACTION |
| 164 | `_update_bulk_menu_label` | 56947 | SIGNAL_SLOT |
| 165 | `show_advanced_filters_dialog` | 56975 | SIGNAL_SLOT |
| 166 | `on_tab_target_change` | 57215 | SIGNAL_SLOT |
| 167 | `on_tab_status_combo_changed` | 57291 | SIGNAL_SLOT |
| 168 | `on_tab_notes_change` | 57338 | SIGNAL_SLOT |
| 169 | `_on_scratchpad_changed` | 58191 | SIGNAL_SLOT |
| 170 | `delete_all_proofreading_comments` | 58439 | MENU_ACTION |
| 171 | `copy_source_to_tab_target` | 58475 | SIGNAL_SLOT |
| 172 | `clear_tab_target` | 58486 | SIGNAL_SLOT |
| 173 | `_get_voice_release_poller` | 58496 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 174 | `_get_command_ptt_release_poller` | 58534 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 175 | `_begin_voice_pause_capture` | 58934 | EXTERNAL_ATTR_REF |
| 176 | `_on_voice_pause_key_captured` | 58947 | SIGNAL_SLOT |
| 177 | `_clear_voice_pause_hotkey` | 58969 | EXTERNAL_ATTR_REF |
| 178 | `on_dictation_complete` | 59243 | SIGNAL_SLOT |
| 179 | `on_dictation_status` | 59335 | SIGNAL_SLOT |
| 180 | `on_dictation_error` | 59340 | SIGNAL_SLOT |
| 181 | `on_dictation_finished` | 59359 | SIGNAL_SLOT |
| 182 | `on_model_loading_started` | 59394 | SIGNAL_SLOT |
| 183 | `on_model_loading_finished` | 59429 | SIGNAL_SLOT |
| 184 | `filter_on_selected_text` | 59526 | ARG_REF |
| 185 | `copy_source_to_grid_target` | 59590 | EXTERNAL_ATTR_REF |
| 186 | `clear_grid_target` | 59622 | EXTERNAL_ATTR_REF |
| 187 | `select_previous_match` | 59697 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 188 | `select_next_match` | 59720 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 189 | `insert_selected_match` | 59867 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 190 | `_handle_compare_panel_alt0_shortcut` | 59983 | ARG_REF |
| 191 | `go_to_previous_segment` | 60294 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 192 | `go_to_next_segment` | 60346 | EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 193 | `go_to_first_segment` | 60397 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 194 | `go_to_last_segment` | 60425 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, STRING_REF |
| 195 | `confirm_selected_or_next` | 60652 | ARG_REF, EXTERNAL_ATTR_REF, HASATTR_REF, SIGNAL_SLOT, STRING |
| 196 | `confirm_selected_segments_from_menu` | 60926 | MENU_ACTION |
| 197 | `_on_termlens_font_size_changed` | 61068 | SIGNAL_SLOT |
| 198 | `_on_termlens_edit_entry` | 61106 | SIGNAL_SLOT |
| 199 | `_on_termlens_refresh_requested` | 61146 | SIGNAL_SLOT |
| 200 | `_on_termlens_delete_entry` | 61175 | SIGNAL_SLOT |
| 201 | `save_tab_notes` | 61220 | SIGNAL_SLOT |
| 202 | `_toggle_tag_view_via_shortcut` | 61226 | ARG_REF |
| 203 | `call_custom_mt` | 61787 | EXTERNAL_ATTR_REF |
| 204 | `show_about` | 62004 | MENU_ACTION |
| 205 | `check_for_updates` | 62196 | MENU_ACTION, SIGNAL_SLOT |
| 206 | `copy_version_info_to_clipboard` | 62787 | MENU_ACTION, SIGNAL_SLOT |
| 207 | `open_diagnostic_log` | 62822 | MENU_ACTION |
| 208 | `open_diagnostic_log_folder` | 62841 | MENU_ACTION |
| 209 | `_show_ahk_setup_from_menu` | 62857 | MENU_ACTION |
| 210 | `show_about` | 62868 | MENU_ACTION |
| 211 | `closeEvent` | 62932 | EXTERNAL_ATTR_REF |
| 212 | `_start_okapi_sidecar` | 63022 | TIMER_SINGLESHOT |
| 213 | `fuzzy_fix_current_segment` | 63613 | MENU_ACTION, SIGNAL_SLOT |
| 214 | `autotag_segments_bulk` | 64326 | MENU_ACTION |
| 215 | `show_image_extractor_from_tools` | 65905 | MENU_ACTION |
| 216 | `show_scratchpad` | 65921 | MENU_ACTION |
| 217 | `show_theme_editor` | 65953 | MENU_ACTION |
| 218 | `_on_tm_search_failed` | 66403 | SIGNAL_SLOT |
| 219 | `_on_tm_search_results` | 66415 | SIGNAL_SLOT |

# LIVE_BUT_LEGACY

Объекты, которые используются или намеренно оставлены, но являются устаревшими:

| # | Объект | Расположение | Evidence | Safe next action |
|---|---|---|---|---|
| 1 | `modules/superdocs.py`, `modules/superdocs_viewer_qt.py` | modules/ | deprecated-shim: `__getattr__` выбрасывает понятную ошибку; фича удалена | Оставить (защитный слой) до следующего мажора |
| 2 | `modules/pdf_rescue_tkinter.py` (910L) | modules/ | параллельная tkinter-реализация живого pdf_rescue_Qt; orphan | Слить/удалить после подтверждения |
| 3 | `modules/find_replace.py` (tkinter, 164L) | modules/ | заменён find_replace_qt; orphan | Удалить после подтверждения |
| 4 | `modules/setup_wizard.py` (tkinter, 354L) | modules/ | orphan; вероятный вызов из _show_setup_wizard по runtime-пути — проверить | Проверить runtime → решить |
| 5 | `modules/prompt_library.py` (689L) | modules/ | «Extracted from main file»; заменён unified_prompt_library; orphan | Удалить после подтверждения |
| 6 | `modules/glossary_manager.py` (429L) | modules/ | старый JSON-termbase; заменён database_manager/termbase_manager; orphan | Удалить после подтверждения |
| 7 | `modules/project_tm.py`, `extract_tm.py`, `translation_services.py`, `feature_manager.py`, `identifier_conventions.py`, `tracked_changes.py` (966L суммарно) | modules/ | orphans; tracked_changes содержит комментарий «will be imported from the main file» — никогда не импортировался | Подтвердить → удалить |
| 8 | `modules/voice_dictation.py` (497L) | modules/ | заменён voice_dictation_lite; orphan | Подтвердить → удалить |
| 9 | `modules/ribbon_widget.py` (608L) + ribbon-методы монолита | modules/ + Supervertaler.py:13066–13158 | единственный импорт закомментирован (13119); билдеры zero-ref | Подтвердить → удалить кластер |
| 10 | `modules/style_guide_manager.py`, `prompt_assistant.py`, `project_home_panel.py`, `quick_access_sidebar.py` | modules/ | orphans (вероятно, будущие фичи) | Уточнить планы владельца |
| 11 | `strip_tags` ×3 внутри монолита (38750, 38879, 38960) | Supervertaler.py | 3 вложенные реализации + 2 в modules (docx_handler, tag_manager) | После переноса tag-движка оставить 1 |
| 12 | `Pink/Blue/OrangeCheckmarkCheckBox`, `CustomRadioButton` | Supervertaler.py:72559–72869 | дубликаты styled_widgets (3×46L paintEvent) | Объединить со styled_widgets |
| 13 | Legacy chain delayed-lookup | Supervertaler.py:51906–53225 | `_schedule_delayed_lookup → … → _fetch_mt_translation_async` — заменён instant/worker-путём | См. PROBABLY_DEAD |
| 14 | `modules/tag_manager.py` — bare-import | modules/docx_handler.py:21–24 | `from .tag_manager import` / `from tag_manager import` fallback | Нормализовать импорт при реорганизации |
| 15 | Ссылки на несуществующие файлы | Supervertaler.py:9,29–35; pyproject | `CODE_MAP.md`, `UNDERSTANDING.md`, `Supervertaler_tkinter.py`, README/LICENSE | Почистить докстринги |

# UNKNOWN

| # | Объект | Что неизвестно |
|---|---|---|
| 1 | 14 duck-typed контрактов (§DEPENDENCY_MAP.3) | Полная площадь интерфейса MainWindow, вызываемого модулями, не может быть выведена статически на 100%: hasattr-вызовы покрывают ~77 имён, но новые вызовы могут добавляться динамически. Остаточный риск для методов с zero-ref оценивается как очень низкий, но не нулевой. |
| 2 | `modules/setup_wizard.py`, `modules/autostart.py` | Возможные внешние вызовы (ярлыки/инсталлятор). usage статическим анализом не найден; dynamic usage вне репозитория не исключён. |
| 3 | **Латентный баг**: `self.jump_to_segment(segment_idx)` (Supervertaler.py:51468) | Метода `jump_to_segment` НЕ существует ни в `SupervertalerQt`, ни где-либо в проекте (grep `def jump_to_segment` — пусто). Вызов находится внутри `show_proofreading_results_dialog` (сам zero-ref/dead), поэтому AttributeError не возникает никогда. Строгое доказательство того, что ветка мертва. | При подтверждении удаления `show_proofreading_results_dialog` баг уходит вместе с веткой; НЕ восстанавливать диалог без реализации jump_to_segment. |
| 4 | supervertaler_bridge_server → `"show_supervertaler_assistant"` | Строка имени метода в docstring/сигналах модуля — живой handoff через Qt-signal; проверен как dynamic entry. Внешний Trados-плагин может ссылаться на другие имена методов по строке через HTTP-bridge — вне репозитория. |
| 5 | Поведенческие замыкания воркеров (retry-политики) | Не являются dead (LIVE через замыкания стартеров), но их логика не именована и не покрыта тестами. |

---

**Итого методов SupervertalerQt:** DEFINITELY_DEAD 16 • PROBABLY_DEAD 57 • затенённых 5 • DYNAMIC_ENTRY_POINT 219 • остальные LIVE (прямые вызовы/динамический вход).
**Итого модулей modules/:** 19 orphans (из них ~11 вероятны к удалению, 2 — намеренные shim'ы).
**Ни один объект не удалён и не изменён.**
