# CODE_MAP_REFACTOR.md
**Проект:** Supervertaler (SupervertalerQt) — архитектурный аудит перед декомпозицией
**Дата:** 2026-09-12 • **Режим:** STRICT READ-ONLY (исходники не изменялись)
**Метод:** AST-анализ (Python 3.13) всех 125 .py-файлов + карта динамической обвязки Qt + ручная классификация каждого метода

---

# 1. Executive Summary

| Метрика | Значение |
|---|---|
| Python-файлов в проекте | 125 (~156 890 строк) |
| `Supervertaler.py` | 73 337 строк (46.7% всего кода) |
| Классов в монолите | 38 (+59 функций верхнего уровня) |
| Методов `SupervertalerQt` | **819** (57 929 строк, 79% файла) |
| Методов `SuperlookupTab` | 115 (5 237 строк) |
| Модулей в `modules/` | 115 (~82 029 строк), плоский пакет |
| Динамических точек входа | 781 `.connect()`, 165 lambda-wrapped, ~86 QTimer, ~35 shortcut-регистраций, 3×`QMetaObject.invokeMethod`, 6+`threading.Thread` |
| Методов с прямым или динамическим входом | 749 из 817 уникальных имён |
| Функциональных кластеров | 39 (см. §5) |
| **Zero-ref методов** (единственная textualная ссылка — собственный def) | **51** |
| Вероятно мёртвых методов всего (zero-ref + цепочки) | **75** (~9% класса) |
| Методов с назначением в `modules/*` | 559 |
| Методов, остающихся в ядре `SupervertalerQt` | 185 |
| Риск извлечения (методы) | HIGH: 35 LOW: 562 MEDIUM: 205 VERY_HIGH: 17 |
| Orphan-модулей в `modules/` | 19 (никем не импортируются) |
| Модулей, duck-typed зависящих от MainWindow | 14 (обратных импортов монолита — 0) |

**Главный вывод:** монолит уже наполовину декомпозирован — `modules/` содержит живые сервисы (БД, TM, termbase, LLM, форматы), но `SupervertalerQt` остаётся god-object'ом, совмещающим UI-контроллер, бизнес-логику, I/O и воркер-оркестрацию. При этом внутри класса найдено **75 вероятно мёртвых методов**, 5 затенённых дублирующихся определений (`closeEvent`, `show_about`, 3 в `ReadOnlyGridTextEditor`), 19 orphan-модулей и ~30 методов-дубликатов уже существующей функциональности `modules/`. Пошаговая декомпозиция по фазам (§17) способна сократить класс с 57.9k до ~12–15k строк без изменения поведения.

# 2. Project Architecture

```
E:\Dev\SupervertalerPortable\
├── Supervertaler.py            73,337 строк — монолит: bootstrap + MainWindow + контроллеры
├── modules/                    115 .py, плоско — вынесенные сервисы и UI
├── scripts/                    диагностика TM + миграции БД (не импортируют modules/)
├── tools/                      i18n-утилиты (423+241+174 строк)
├── assets/                     генератор иконок
├── translations/               XLIFF-переводы UI (nl, pl, zh_CN, zh_TW)
├── user_data/                  supervertaler.db (SQLite), api_keys.example.txt
├── okapi-sidecar/              Java/Maven sidecar (сегментация, Docker)
├── setup.py, pyproject.toml    версия 1.10.371; тестов НЕТ; git-истории НЕТ
└── requirements.txt            PyQt6, python-docx, openai/anthropic/google-generativeai, deepl, boto3, PyMuPDF, pynput, ahk…
```

Точка входа одна: `main()` в `Supervertaler.py` (строки 73078–73318) → `SupervertalerQt(QMainWindow)`.
Второй «почти entry point»: `batch_offload.py` (headless-пакетный перевод, вызывается из `main()`).
Иерархии плагинов нет; расширение — через duck-typed `parent_app`-контракты (14 модулей).

# 3. Supervertaler.py Overview

| Диапазон строк | Содержимое |
|---|---|
| 1–494 | Шапка, version-хелперы (`_read_version`, `get_user_data_path`…), config paths |
| 1775–2402 | **Модели данных**: `Comment` (1775), `Segment` (1938), `Project` (2124) |
| 676–892 (до Batch #3a: 675–1043, в документе ошибочно 2403–2901) | **Event-фильтры**: остались в монолите `_CtrlReturnEventFilter` (676), `_GridArrowKeyEventFilter` (728); `_QuitEventFilter`, `_WheelGuard`, `_LoneCtrlEventFilter`, `GridTableEventFilter` перенесены в `modules/event_filters.py` (Batch #3a) |
| 2902–6760 | **Грид-редакторы**: `GridTextEditor`, `ReadOnlyGridTextEditor` (31 метод), `TagHighlighter`, `EditableGridTextEditor` (33 метода) |
| 6761–7189 | **Делегаты/подсветка**: `SearchHighlightDelegate`, `ClickableHighlightLabel`, `TermbaseHighlightWidget`, `WordWrapDelegate` |
| — (до Batch #3b: 7190–7786, в документе ошибочно; фактически 5307–5901) | **Диалоги**: `ThemeEditorDialog`, `DetachedLogWindow`, `AdvancedFiltersDialog`, `ScratchpadDialog` перенесены в `modules/dialogs/` (Batch #3b) |
| (до Batch #3b фактически 5908–7284, в документе ошибочно 7787–9169) | **QThread-воркеры**: `TMSearchWorker` (5333–5456), `PreTranslationWorker` (5459–6165, 11 методов, держит `parent_app`), `ProofreadWorker` (6168–6325), `GlossaryExtractionWorker` (6336–6407); `LiveProgressDialog` и `_ImportProgressDialog` перенесены в `modules/dialogs/` (Batch #3b, были 6903–7206) |
| **9170–67098** | **`SupervertalerQt`** — 819 методов |
| 494–1767 | ~30 функций верхнего уровня: DOCX tag/formatting engine (`runs_to_tagged_text`, `tagged_text_to_runs`, `compact_tags`, `validate_tag_transfer`…) |
| 67106–67311 | Хелперы SuperLookup: `_SearchTermHighlighter`, `_NumericTableWidgetItem`, `_ReadOnlyHtmlCell`, `_SuperLookupSearchSignals`, `_SuperLookupSearchWorker` |
| 67312–72548 | **`SuperlookupTab`** — 115 методов |
| 72559–72869 | `Pink/Blue/OrangeCheckmarkCheckBox`, `CustomRadioButton` (дубликаты `modules/styled_widgets.py`) |
| 72876–73337 | Диагностический лог, `main()`, `if __name__` |

Аномалии уровня файла (важно для рефакторинга):
1. **`closeEvent` объявлен дважды** (33453 и 62932) — второе определение молча затирает первое (трей-логика в 33453 недостижима как переопределение).
2. **`show_about` объявлен дважды** (62004, 171 строк — затёрт 62868, 63 строк).
3. `ReadOnlyGridTextEditor`: `keyPressEvent`, `_handle_quick_add_to_glossary_priority`, `_get_main_window` — по два определения (затенение внутри класса).
4. Mid-file импорт `from modules.termbase_entry_editor import …` на строке 7487.
5. 877 import-ов всего, из них 243 `from modules.*` — ленивые импорты внутри методов (нужен AST-обход, а не только шапка).
6. Устаревшие ссылки: докстринг ссылается на `CODE_MAP.md`, `UNDERSTANDING.md`, `Supervertaler_tkinter.py` — файлов не существует. `_read_version` fallback «1.10.313» ≠ pyproject 1.10.371; `modules/__init__.py` = «2.5.0».

# 4. SupervertalerQt Complete Method Map

Все **819** методов (в порядке определения в файле). Колонки:
**Calls** — вызываемые self-методы (топ-4 по частоте); **Called By** — прямые callers (топ-3); **self-state** — читаемые/пишемые `self.*` (топ-4); **Qt/Dynamic** — механизм входа (menu = QAction.triggered, shortcut = QShortcut/activated, timer = QTimer.timeout, singleShot, thread = threading.Thread/Timer target, duck-typed = вызов из modules/ или вложенных классов через `main_window`/`parent_app`, hasattr/getattr/string = строковые ссылки, signal:… = остальные сигналы).

| Method | Lines | LOC | Responsibility | Subsystem | Calls | Called By | self-state | Qt/Dynamic | Proposed Destination | Risk |
|---|---|---|---|---|---|---|---|---|---|---|
| `__init__` | 9182–9627 | 446 | Инициализация приложения: state, services, threads, таймеры | A. Bootstrap/инициализация | `load_general_settings`, `log`, `set_termlens_position`, `_migrate_voice_dictation_default_off` | — (входа нет) | `_log_to_ui`, `_apply_proactive_highlighting`, `_needs_data_location_dialog`, `db_manager` | — | SupervertalerQt (ядро) | VERY_HIGH |
| `_show_data_location_dialog` | 9629–9748 | 120 | Zero-ref диалог данных (не вызывается нигде) | Legacy/мёртвое | `tr`, `log`, `_reinitialize_with_new_data_path` | **dead-candidate** | `tr`, `user_data_path`, `log`, `_show_first_run_welcome` | — | PROBABLY_DEAD | LOW |
| `_reinitialize_with_new_data_path` | 9750–9804 | 55 | Переинициализация с новым data path | A. Bootstrap/инициализация | `log`, `_migrate_settings_to_unified`, `_migrate_to_workbench_layout`, `_get_global_ui_font_scale` | `_show_data_location_dialog`, `_show_setup_wizard`, `_create_general_settings_tab` | `_migrate_settings_to_unified`, `_migrate_to_workbench_layout`, `db_manager`, `log` | — | SupervertalerQt (ядро) | HIGH |
| `_show_first_run_welcome` | 9806–9821 | 16 | Первый запуск: приветствие | A. Bootstrap/инициализация | `load_general_settings`, `save_general_settings` | динамич. вход | `load_general_settings`, `save_general_settings` | singleShot×1 | SupervertalerQt (ядро) | MEDIUM |
| `_show_setup_wizard` | 9823–10071 | 249 | Мастер первичной настройки (запуск+обработка) | A. Bootstrap/инициализация | `tr`, `log`, `_reinitialize_with_new_data_path`, `load_general_settings` | `__init__`, `create_menus` | `_needs_data_location_dialog`, `tr`, `user_data_path`, `log` | menu×1, singleShot×1 | SupervertalerQt (ядро) | MEDIUM |
| `init_ui` | 10073–10112 | 40 | Сборка окна: меню, layout, индикаторы | A. Bootstrap/инициализация | `setWindowTitle`, `setGeometry`, `setMinimumSize`, `create_menus` | `__init__` | `setWindowTitle`, `setGeometry`, `setMinimumSize`, `create_menus` | — | SupervertalerQt (ядро) | VERY_HIGH |
| `setup_global_shortcuts` | 10114–10419 | 306 | Регистрация ~35 глобальных хоткеев | AD. Горячие клавиши | `_get_active_match_shortcut_mode`, `_quick_add_term_with_priority`, `_compare_panel_nav_mt`, `_compare_panel_nav_tm` | `init_ui` | `start_voice_dictation`, `split_current_segment`, `merge_current_segment`, `_handle_compare_panel_alt0_shortcut` | — | modules/shortcuts_wiring | MEDIUM |
| `add_comment_from_selection` | 10421–10610 | 190 | Добавить комментарий к выделенным сегментам | D. Операции с сегментами | `tr`, `log`, `get_translator_name`, `update_window_title` | динамич. вход | `current_project`, `table`, `tr`, `get_translator_name` | duck-typed×4, hasattr×2, string×2, shortcut-registry×1 | modules/segments_controller | MEDIUM |
| `focus_segment_notes` | 10612–10640 | 29 | Фокус на поле заметок | F. Редактирование текста | — | **dead-candidate** | `right_tabs`, `comments_sub_tabs`, `bottom_notes_edit` | — | PROBABLY_DEAD | LOW |
| `open_clipboard_tab` | 10642–10654 | 13 | Открыть вкладку буфера обмена | AF. UI-хелперы | `log`, `open_workbench_to_clipboard` | динамич. вход | `open_workbench_to_clipboard`, `log` | shortcut-registry×1 | SupervertalerQt (ядро) | LOW |
| `open_quicklauncher` | 10656–10711 | 56 | Быстрый prompt-launcher по гриду | J. LLM/AI | `run_grid_quicklauncher_prompt`, `log` | динамич. вход | `table`, `prompt_manager_qt`, `log`, `run_grid_quicklauncher_prompt` | shortcut-registry×2 | modules/quick_actions | MEDIUM |
| `show_supervertaler_assistant` | 10713–10745 | 33 | Показать AI-ассистента (таб) | J. LLM/AI | `show`, `raise_`, `activateWindow` | динамич. вход | `prompt_manager_qt`, `show`, `raise_`, `activateWindow` | duck-typed×2 | SupervertalerQt (ядро) | LOW |
| `_on_bridge_prompt_request` | 10747–10830 | 84 | Обработка prompt-запроса от Trados bridge | Trados bridge | `_bring_workbench_forward`, `log` | динамич. вход | `_bring_workbench_forward`, `log`, `main_tabs` | signal:run_prompt_requested×1 | modules/bridge_controller | MEDIUM |
| `show_term_insert_popup` | 10832–10989 | 158 | Popup вставки термина | TermLens | `statusBar`, `find_nt_matches_in_source`, `load_general_settings`, `_search_termbase_in_memory` | динамич. вход | `current_project`, `termbase_cache_lock`, `find_nt_matches_in_source`, `insert_termlens_text` | duck-typed×1 | modules/termlens_controller | MEDIUM |
| `show_term_picker_dialog` | 10991–11064 | 74 | Диалог выбора термина (Ctrl+Shift+P) | TermLens | `statusBar`, `find_nt_matches_in_source`, `insert_termlens_text`, `_search_termbase_in_memory` | динамич. вход | `current_project`, `termbase_cache_lock`, `find_nt_matches_in_source`, `table` | shortcut-registry×1 | modules/termlens_controller | LOW |
| `_quicktrans_base_pair` | 11066–11072 | 7 | Языковая пара QuickTrans | QuickTrans | — | `set_quicktrans_direction_override`, `resolve_quicktrans_direction` | — | — | modules/quicktrans_controller | LOW |
| `set_quicktrans_direction_override` | 11074–11078 | 5 | Переопределение направления MT | QuickTrans | `_quicktrans_base_pair` | динамич. вход | `_quicktrans_base_pair`, `_quicktrans_lang_override` | duck-typed×2 | modules/quicktrans_controller | LOW |
| `resolve_quicktrans_direction` | 11080–11100 | 21 | Разрешение направления QuickTrans | QuickTrans | `_quicktrans_base_pair`, `log` | `show_mt_quick_popup` | `_quicktrans_base_pair`, `log`, `_quicktrans_lang_override` | duck-typed×2, hasattr×1, string×1 | modules/quicktrans_controller | LOW |
| `show_mt_quick_popup` | 11102–11215 | 114 | MT-popup по Ctrl+Alt+Q | QuickTrans | `log`, `reverse_invisible_replacements`, `resolve_quicktrans_direction`, `mark_segment_modified` | динамич. вход | `resolve_quicktrans_direction`, `table`, `log`, `reverse_invisible_replacements` | duck-typed×6, hasattr×3, string×3, shortcut-registry×1 | modules/quicktrans_controller | MEDIUM |
| `refresh_shortcut_enabled_states` | 11217–11234 | 18 | Вкл/выкл глобальных шорткатов | AD. Горячие клавиши | — | динамич. вход | `global_shortcuts`, `shortcut_manager`, `global_shortcut_keys` | duck-typed×4 | modules/shortcuts_wiring | LOW |
| `_setup_progress_indicators` | 11236–11311 | 76 | Статус-бар: прогресс-индикаторы | AF. UI-хелперы | `tr`, `_update_llm_indicator`, `_setup_ollama_keepwarm`, `_show_confirmed_basis_menu` | `init_ui` | `llm_indicator_label`, `_update_llm_indicator`, `progress_words_label`, `progress_confirmed_label` | — | SupervertalerQt (ядро) | MEDIUM |
| `_resolve_provider_model` | 11313–11328 | 16 | Резолв модели провайдера | J. LLM/AI | `_get_active_custom_profile` | `_update_llm_indicator`, `translate_current_segment`, `autotag_current_segment` | `_get_active_custom_profile` | — | modules/llm_controller | LOW |
| `_update_llm_indicator` | 11330–11375 | 46 | Индикатор LLM в статус-баре | J. LLM/AI | `load_llm_settings`, `_resolve_provider_model`, `_get_active_custom_profile` | `_setup_progress_indicators`, `_save_llm_settings_from_ui`, `_save_ai_settings_from_ui` | `load_llm_settings`, `_resolve_provider_model`, `llm_indicator_label`, `_get_active_custom_profile` | — | modules/llm_controller | LOW |
| `_setup_ollama_keepwarm` | 11377–11386 | 10 | Настройка keepwarm Ollama | J. LLM/AI | `load_general_settings`, `_start_ollama_keepwarm_timer` | `_setup_progress_indicators` | `load_general_settings`, `_start_ollama_keepwarm_timer` | — | modules/llm_controller | LOW |
| `_start_ollama_keepwarm_timer` | 11388–11398 | 11 | Таймер keepwarm | J. LLM/AI | `log` | `_setup_ollama_keepwarm`, `_save_ai_settings_from_ui` | `ollama_keepwarm_timer`, `log`, `_ping_ollama_keepwarm` | — | modules/llm_controller | LOW |
| `_stop_ollama_keepwarm_timer` | 11400–11404 | 5 | Остановка таймера keepwarm | J. LLM/AI | `log` | `_save_ai_settings_from_ui` | `ollama_keepwarm_timer`, `log` | — | modules/llm_controller | LOW |
| `_ping_ollama_keepwarm` | 11406–11439 | 34 | Ping Ollama по таймеру | J. LLM/AI | `load_llm_settings` | динамич. вход | `load_llm_settings` | timer×1 | modules/llm_controller | LOW |
| `update_progress_stats` | 11441–11540 | 100 | Статистика прогресса в статус-баре | AF. UI-хелперы | `tr`, `_get_progress_color`, `log` | `_set_confirmed_progress_basis`, `_apply_undo_redo_action`, `_sync_after_structural` | `current_project`, `_get_progress_color`, `tr`, `progress_words_label` | hasattr×3, string×3, duck-typed×3 | SupervertalerQt (ядро) | MEDIUM |
| `_get_progress_color` | 11542–11549 | 8 | Цвет прогресса | AF. UI-хелперы | — | `update_progress_stats` | — | — | SupervertalerQt (ядро) | LOW |
| `_show_confirmed_basis_menu` | 11551–11575 | 25 | Меню базы расчёта прогресса | AF. UI-хелперы | `tr`, `_set_confirmed_progress_basis` | `_setup_progress_indicators` | `tr`, `_set_confirmed_progress_basis` | — | SupervertalerQt (ядро) | LOW |
| `_set_confirmed_progress_basis` | 11577–11600 | 24 | Сохранение базы прогресса | AB. Персистентность (settings IO) | `update_progress_stats`, `_load_settings_section`, `_save_settings_section`, `log` | `_show_confirmed_basis_menu`, `_create_view_settings_tab` | `update_progress_stats`, `_load_settings_section`, `_save_settings_section`, `log` | menu×2, signal:toggled×1 | SupervertalerQt (ядро) | LOW |
| `create_menus` | 11602–12491 | 890 | Фабрика всех меню (890 строк!) | A. Bootstrap/инициализация | `tr`, `translate_multiple_segments`, `_switch_main_tab`, `_open_url` | `init_ui` | `translate_menu`, `bulk_menu`, `menuBar`, `new_project` | — | modules/menus_factory | HIGH |
| `record_undo_state` | 12493–12521 | 29 | Запись undo-состояния сегмента | F. Редактирование текста | `update_undo_redo_actions` | `on_match_inserted`, `_populate_single_row`, `update_status_icon` | `max_undo_levels`, `update_undo_redo_actions`, `undo_stack`, `redo_stack` | duck-typed×2, hasattr×1, string×1 | modules/undo_manager | LOW |
| `record_undo_states_batch` | 12523–12567 | 45 | Пакетная запись undo | F. Редактирование текста | `update_undo_redo_actions` | `clear_selected_translations`, `copy_source_to_target_bulk`, `copy_source_to_target_non_translatable_bulk` | `max_undo_levels`, `update_undo_redo_actions`, `undo_stack`, `redo_stack` | duck-typed×1 | modules/undo_manager | LOW |
| `undo_action_handler` | 12569–12583 | 15 | Undo | F. Редактирование текста | `update_undo_redo_actions`, `_apply_undo_redo_action`, `_apply_structural_history` | динамич. вход | `undo_stack`, `_apply_undo_redo_action`, `update_undo_redo_actions`, `_apply_structural_history` | duck-typed×2, menu×1, hasattr×1, string×1 | modules/undo_manager | LOW |
| `redo_action_handler` | 12585–12598 | 14 | Redo | F. Редактирование текста | `update_undo_redo_actions`, `_apply_undo_redo_action`, `_apply_structural_history` | динамич. вход | `redo_stack`, `_apply_undo_redo_action`, `update_undo_redo_actions`, `_apply_structural_history` | duck-typed×2, menu×1, hasattr×1, string×1 | modules/undo_manager | LOW |
| `_apply_undo_redo_action` | 12600–12635 | 36 | Применение undo/redo | F. Редактирование текста | `_find_row_for_segment`, `update_window_title`, `_update_status_cell`, `update_progress_stats` | `undo_action_handler`, `redo_action_handler` | `current_project`, `_find_row_for_segment`, `update_window_title`, `_update_status_cell` | — | modules/undo_manager | MEDIUM |
| `_segment_for_grid_row` | 12638–12653 | 16 | Сегмент по строке грида | E. Грид/таблица | — | `_split_segment_at_row`, `_merge_segment_at_row`, `_delete_segments_at_rows` | `current_project`, `table` | — | modules/grid/helpers | LOW |
| `_split_segment_at_row` | 12655–12696 | 42 | Разделение сегмента | D. Операции с сегментами | `_select_grid_row_by_id`, `log`, `load_segments_to_grid`, `_segment_for_grid_row` | `split_current_segment` | `_segment_for_grid_row`, `_push_structural_undo`, `_sync_after_structural`, `log` | hasattr×1, string×1, duck-typed×1 | modules/segments_controller | MEDIUM |
| `_merge_segment_at_row` | 12698–12732 | 35 | Слияние сегментов | D. Операции с сегментами | `_select_grid_row_by_id`, `log`, `load_segments_to_grid`, `_segment_for_grid_row` | `merge_current_segment` | `_segment_for_grid_row`, `_push_structural_undo`, `_sync_after_structural`, `log` | — | modules/segments_controller | MEDIUM |
| `_delete_segments_at_rows` | 12734–12782 | 49 | Удаление сегментов | D. Операции с сегментами | `tr`, `_push_structural_undo`, `_sync_after_structural`, `load_segments_to_grid` | `delete_current_segments` | `_push_structural_undo`, `_sync_after_structural`, `load_segments_to_grid`, `log` | — | modules/segments_controller | MEDIUM |
| `delete_current_segments` | 12784–12806 | 23 | Удаление текущих сегментов (меню) | D. Операции с сегментами | `tr`, `_delete_segments_at_rows` | динамич. вход | `_delete_segments_at_rows`, `tr`, `table` | menu×1 | modules/segments_controller | LOW |
| `split_current_segment` | 12809–12838 | 30 | Split текущего (хоткей) | D. Операции с сегментами | `_split_segment_at_row`, `log`, `reverse_invisible_replacements` | динамич. вход | `_split_segment_at_row`, `log`, `reverse_invisible_replacements`, `table` | shortcut-registry×1 | modules/segments_controller | LOW |
| `merge_current_segment` | 12840–12849 | 10 | Merge текущего (хоткей) | D. Операции с сегментами | `_merge_segment_at_row` | динамич. вход | `_merge_segment_at_row`, `table` | shortcut-registry×1 | modules/segments_controller | LOW |
| `_push_structural_undo` | 12851–12866 | 16 | Структурный undo-push | F. Редактирование текста | `update_undo_redo_actions` | `_split_segment_at_row`, `_merge_segment_at_row`, `_delete_segments_at_rows` | `max_undo_levels`, `update_undo_redo_actions`, `undo_stack`, `redo_stack` | — | modules/undo_manager | LOW |
| `_sync_after_structural` | 12868–12884 | 17 | Синк UI после структурных правок | E. Грид/таблица | `update_window_title`, `update_progress_stats`, `refresh_preview` | `_split_segment_at_row`, `_merge_segment_at_row`, `_delete_segments_at_rows` | `update_window_title`, `update_progress_stats`, `refresh_preview`, `current_project` | — | modules/segments_controller | LOW |
| `_recompute_list_numbers` | 12886–12913 | 28 | Пересчёт нумерации списков | E. Грид/таблица | — | `_split_segment_grid_fast`, `_merge_segment_grid_fast` | `current_project`, `_list_numbers` | — | modules/grid/helpers | LOW |
| `_reindex_grid_rows_from` | 12915–12936 | 22 | Реиндексация строк грида | E. Грид/таблица | — | `_split_segment_grid_fast`, `_merge_segment_grid_fast` | `current_project`, `table`, `_populated_rows` | — | modules/grid/helpers | LOW |
| `_select_grid_row_by_id` | 12938–12959 | 22 | Выбор строки по segment id | E. Грид/таблица | `_find_row_for_segment` | `_split_segment_at_row`, `_merge_segment_at_row`, `_delete_segments_at_rows` | `_find_row_for_segment`, `table` | — | modules/grid/helpers | LOW |
| `_split_segment_grid_fast` | 12961–12987 | 27 | Быстрое обновление грида при split | E. Грид/таблица | `_populate_single_row`, `_auto_resize_single_row`, `_recompute_list_numbers`, `_reindex_grid_rows_from` | `_split_segment_at_row`, `_apply_structural_history` | `_recompute_list_numbers`, `_populate_single_row`, `_reindex_grid_rows_from`, `_auto_resize_single_row` | — | modules/grid/helpers | MEDIUM |
| `_merge_segment_grid_fast` | 12989–13006 | 18 | Быстрое обновление при merge | E. Грид/таблица | `_recompute_list_numbers`, `_populate_single_row`, `_reindex_grid_rows_from`, `_auto_resize_single_row` | `_merge_segment_at_row`, `_apply_structural_history` | `_recompute_list_numbers`, `_populate_single_row`, `_reindex_grid_rows_from`, `_auto_resize_single_row` | — | modules/grid/helpers | MEDIUM |
| `_apply_structural_history` | 13008–13059 | 52 | Применение структурного undo/redo | F. Редактирование текста | `_select_grid_row_by_id`, `update_window_title`, `load_segments_to_grid`, `update_progress_stats` | `undo_action_handler`, `redo_action_handler` | `current_project`, `_select_grid_row_by_id`, `update_window_title`, `load_segments_to_grid` | — | modules/undo_manager | MEDIUM |
| `update_undo_redo_actions` | 13061–13064 | 4 | Обновление undo/redo действий | F. Редактирование текста | — | `record_undo_state`, `record_undo_states_batch`, `undo_action_handler` | `undo_action`, `redo_action`, `undo_stack`, `redo_stack` | — | modules/undo_manager | LOW |
| `create_quick_access_toolbar` | 13066–13109 | 44 | Мёртвый билдер тулбара (заменён sidebar/ribbon) | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `create_ribbon` | 13111–13117 | 7 | Мёртвый билдер ribbon (единственный вызов закомментирован) | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `create_ribbon_toolbar` | 13135–13139 | 5 | Мёртвый билдер ribbon-тулбара | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `toggle_ribbon_minimized` | 13141–13145 | 5 | Мёртвый toggle ribbon | Legacy/мёртвое | — | **dead-candidate** | `ribbon_minimized` | — | PROBABLY_DEAD | LOW |
| `show_ribbon_temporarily` | 13147–13150 | 4 | Мёртвый показ ribbon | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `on_main_tab_changed` | 13152–13156 | 5 | Мёртвый обработчик смены таба (нет connectSlotsByName) | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `create_main_layout` | 13158–13404 | 247 | Создание главных вкладок (247 строк) | A. Bootstrap/инициализация | `setCentralWidget`, `create_grid_view_widget_for_home`, `create_translation_memories_tab`, `create_termbases_tab` | `init_ui` | `main_tabs`, `setCentralWidget`, `create_grid_view_widget_for_home`, `create_translation_memories_tab` | — | SupervertalerQt (ядро) | VERY_HIGH |
| `_create_placeholder_tab` | 13407–13422 | 16 | Мёртвый placeholder-таб | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `create_prompt_manager_tab` | 13424–13434 | 11 | Мёртвый билдер AI-таба (дублирует create_main_layout) | Legacy/мёртвое | — | **dead-candidate** | `prompt_manager_qt` | — | PROBABLY_DEAD | LOW |
| `open_superbrowser_window` | 13437–13477 | 41 | Окно Superbrowser | Superdocs/browser | `tr` | динамич. вход | `tr`, `user_data_path`, `_superbrowser_window` | menu×1 | SupervertalerQt (ядро) | LOW |
| `open_tmx_editor_window` | 13479–13534 | 56 | Окно TMX-редактора | Q. TMX | `tr`, `get_translator_name` | динамич. вход | `get_translator_name`, `tr`, `db_manager`, `tmx_editor_embedded` | menu×1 | SupervertalerQt (ядро) | LOW |
| `show_statistics_dialog` | 13536–13594 | 59 | Полная статистика (диалог) | AC. Статистика | `tr`, `log` | динамич. вход | `current_project`, `tr`, `db_manager`, `log` | menu×1 | modules/stats_controller | LOW |
| `_all_tm_choices` | 13597–13613 | 17 | Список TM для статистики | AC. Статистика | — | `show_quick_statistics_dialog` | `tm_metadata_mgr`, `db_manager` | — | modules/stats_controller | LOW |
| `_quick_count_lang_pair` | 13615–13625 | 11 | Быстрый подсчёт по языковой паре | AC. Статистика | `load_general_settings` | `show_quick_statistics_dialog` | `load_general_settings` | — | modules/stats_controller | LOW |
| `_quick_extract_sources` | 13627–13659 | 33 | Извлечение исходников для подсчёта | AC. Статистика | `_ensure_okapi_sidecar`, `get_effective_import_options` | `show_quick_statistics_dialog` | `_ensure_okapi_sidecar`, `okapi_sidecar`, `get_effective_import_options` | — | modules/stats_controller | MEDIUM |
| `show_quick_statistics_dialog` | 13661–13745 | 85 | Быстрая статистика (меню) | AC. Статистика | `tr`, `log`, `_quick_count_lang_pair`, `_quick_extract_sources` | динамич. вход | `_quick_count_lang_pair`, `tr`, `_quick_extract_sources`, `db_manager` | menu×1 | modules/stats_controller | LOW |
| `create_reference_images_tab` | 13747–14092 | 346 | Вкладка извлечения картинок из DOCX (346 строк) | Картинки/figure context | `tr`, `log` | `create_main_layout` | `_on_add_docx_file_for_extraction`, `_on_add_docx_folder_for_extraction`, `image_extractor_file_list`, `_on_auto_folder_toggled` | — | modules/images_tab | HIGH |
| `open_pdf_rescue_window` | 14094–14121 | 28 | Окно PDF Rescue | AA. Файловые операции | `tr` | динамич. вход | `tr`, `pdf_rescue_qt`, `_pdf_rescue_window` | menu×1 | SupervertalerQt (ядро) | LOW |
| `_on_add_docx_file_for_extraction` | 14127–14140 | 14 | Добавить DOCX в извлечение | Картинки/figure context | — | динамич. вход | `image_extractor_file_list` | signal:clicked×1 | modules/images_tab | LOW |
| `_on_add_docx_folder_for_extraction` | 14142–14164 | 23 | Добавить папку DOCX | Картинки/figure context | — | динамич. вход | `image_extractor_status`, `image_extractor_file_list` | signal:clicked×1 | modules/images_tab | LOW |
| `_on_browse_output_dir_for_extraction` | 14166–14174 | 9 | Выбор папки вывода | Картинки/figure context | — | динамич. вход | `image_extractor_output_dir` | signal:clicked×1 | modules/images_tab | LOW |
| `_on_auto_folder_toggled` | 14176–14184 | 9 | Toggle авто-папки | Картинки/figure context | `tr` | динамич. вход | `image_extractor_output_dir`, `tr` | signal:toggled×1 | modules/images_tab | LOW |
| `_on_file_list_item_clicked` | 14186–14197 | 12 | Клик по файлу: превью | Картинки/figure context | `_update_preview` | динамич. вход | `extracted_image_files`, `_update_preview`, `current_preview_index` | signal:itemClicked×1 | modules/images_tab | LOW |
| `_build_image_extract_ai_callback` | 14203–14411 | 209 | AI-callback анализа картинок (LLM) | Картинки/figure context | `log` | `_on_extract_images` | `log`, `image_extractor` | — | modules/images_tab | MEDIUM |
| `_on_extract_images` | 14413–14565 | 153 | Запуск извлечения картинок | Картинки/figure context | `_build_image_extract_ai_callback`, `tr`, `_update_preview`, `_guess_extracted_folder` | динамич. вход | `_build_image_extract_ai_callback`, `image_extractor_auto_folder`, `image_extractor_status`, `image_extractor_files_list` | signal:clicked×1 | modules/images_tab | MEDIUM |
| `_update_preview` | 14567–14615 | 49 | Превью извлечённых картинок | Картинки/figure context | `tr` | `_on_file_list_item_clicked`, `_on_extract_images`, `_on_preview_prev` | `extracted_image_files`, `current_preview_index`, `image_extractor_preview`, `tr` | — | modules/images_tab | LOW |
| `_on_preview_prev` | 14617–14621 | 5 | Листание превью назад | Картинки/figure context | `_update_preview` | динамич. вход | `extracted_image_files`, `current_preview_index`, `_update_preview` | signal:clicked×1 | modules/images_tab | LOW |
| `_on_preview_next` | 14623–14627 | 5 | Листание превью вперёд | Картинки/figure context | `_update_preview` | динамич. вход | `extracted_image_files`, `current_preview_index`, `_update_preview` | signal:clicked×1 | modules/images_tab | LOW |
| `_on_load_image_context_folder` | 14631–14643 | 13 | Загрузка контекста картинок | Картинки/figure context | `_load_image_context_from_path` | динамич. вход | `_load_image_context_from_path` | signal:clicked×1 | modules/images_tab | LOW |
| `_guess_extracted_folder` | 14645–14654 | 10 | Угадывание папки вывода | Картинки/figure context | — | `_on_extract_images` | — | — | modules/images_tab | LOW |
| `_load_image_context_from_path` | 14656–14745 | 90 | Загрузка image-context из папки | Картинки/figure context | `log`, `tr`, `_update_preview` | `_on_extract_images`, `_on_load_image_context_folder` | `figure_context`, `log`, `prompt_manager_qt`, `image_context_status_label` | — | modules/images_tab | LOW |
| `_on_clear_image_context` | 14747–14771 | 25 | Очистка image-context | Картинки/figure context | `log`, `tr` | динамич. вход | `figure_context`, `log`, `prompt_manager_qt`, `image_context_status_label` | signal:clicked×1 | modules/images_tab | LOW |
| `create_superdocs_tab` | 14773–14782 | 10 | Мёртвый Superdocs-таб (фича удалена) | Legacy/мёртвое | `tr` | **dead-candidate** | `tr` | — | PROBABLY_DEAD | LOW |
| `_get_api_keys` | 14784–14787 | 4 | Zero-ref обёртка над api keys | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `show_concordance_search` | 14789–14865 | 77 | Конкордансный поиск через SuperLookup | G. Поиск | `log`, `_go_to_superlookup` | динамич. вход | `_go_to_superlookup`, `table`, `log` | duck-typed×2, shortcut-registry×1, menu×1 | SupervertalerQt (ядро) | LOW |
| `show_tm_manager_tab` | 14867–14883 | 17 | Открыть менеджер TM | K. Память переводов (TM) | `log` | динамич. вход | `db_manager`, `log` | duck-typed×2, hasattr×1, string×1 | modules/tm_controller | LOW |
| `_show_tm_maintenance_dialog` | 14885–14905 | 21 | Диалог обслуживания TM | K. Память переводов (TM) | `tr`, `log` | динамич. вход | `db_manager`, `log`, `tr` | signal:clicked×1 | modules/tm_controller | LOW |
| `_copy_tm_stats_to_clipboard` | 14907–14972 | 66 | Статистика TM в буфер | K. Память переводов (TM) | `log` | `_create_tm_list_tab` | `db_manager`, `log` | signal:clicked×1 | modules/tm_controller | LOW |
| `create_log_tab` | 14974–15017 | 44 | Вкладка лога с detach | Логирование | `tr` | `create_settings_tab` | `detach_log_window`, `clear_log`, `session_log`, `tr` | — | SupervertalerQt (ядро) | LOW |
| `detach_log_window` | 15019–15031 | 13 | Отсоединить окно лога | Логирование | `log` | динамич. вход | `log`, `detached_log_windows` | signal:clicked×2, duck-typed×2, menu×1, singleShot×1 | SupervertalerQt (ядро) | LOW |
| `clear_log` | 15033–15047 | 15 | Очистить лог | Логирование | — | динамич. вход | `detached_log_windows`, `session_log` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `_on_main_tab_changed` | 15049–15081 | 33 | Обработчик смены главной вкладки (ленивые табы) | Управление вкладками | `_ensure_superlookup_top_tab`, `log`, `_ensure_clipboard_top_tab`, `_ensure_voice_top_tab` | динамич. вход | `superlookup_tab_index`, `_ensure_superlookup_top_tab`, `log`, `clipboard_tab_index` | signal:currentChanged×1 | SupervertalerQt (ядро) | MEDIUM |
| `_warm_up_top_tabs` | 15090–15117 | 28 | Прогрев верхних вкладок | Управление вкладками | `log`, `_prewarm_ahk` | динамич. вход | `_prewarm_ahk`, `log` | singleShot×1 | SupervertalerQt (ядро) | LOW |
| `_prewarm_ahk` | 15119–15161 | 43 | Прогрев AutoHotkey | B. Жизненный цикл окна/Workbench | — | `_warm_up_top_tabs` | — | — | SupervertalerQt (ядро) | LOW |
| `_ensure_superlookup_top_tab` | 15163–15191 | 29 | Ленивое создание SuperLookup-таба | Управление вкладками | `log` | `_on_main_tab_changed`, `open_workbench_to_superlookup` | `_superlookup_top_widget`, `superlookup_tab_index`, `main_tabs`, `log` | string×2, hasattr×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `_ensure_clipboard_top_tab` | 15193–15231 | 39 | Ленивое создание clipboard-таба | Управление вкладками | `log` | `_on_main_tab_changed`, `open_workbench_to_clipboard` | `_clipboard_top_widget`, `clipboard_tab_index`, `main_tabs`, `log` | string×2, hasattr×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `_ensure_voice_top_tab` | 15233–15253 | 21 | Ленивое создание voice-таба | Управление вкладками | `log` | `_on_main_tab_changed`, `_open_voice_in_workbench` | `_voice_top_widget`, `voice_tab_index`, `main_tabs`, `log` | string×2, hasattr×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `detach_superlookup` | 15255–15386 | 132 | Zero-ref отстыковка SuperLookup | Legacy/мёртвое | `tr`, `log`, `geometry` | **dead-candidate** | `theme_manager`, `lookup_detached_window`, `geometry`, `reattach_superlookup` | — | PROBABLY_DEAD | LOW |
| `reattach_superlookup` | 15388–15406 | 19 | Возврат SuperLookup в окно | Z. SuperLookup | `log` | динамич. вход | `lookup_detached_window`, `home_lookup_widget`, `lookup_detached_widget`, `log` | signal:clicked×1 | modules/superlookup | MEDIUM |
| `_setup_superlookup_hotkeys` | 15416–15439 | 24 | Хоткеи SuperLookup | Z. SuperLookup | `log` | `create_main_layout` | `user_data_path`, `log`, `lookup_tab` | — | modules/superlookup | LOW |
| `create_translation_memories_tab` | 15441–15487 | 47 | Вкладка TM (список TM) | K. Память переводов (TM) | `_create_tm_list_tab`, `tr` | `create_main_layout` | `db_manager`, `log`, `_create_tm_list_tab`, `tr` | — | modules/tm_controller | MEDIUM |
| `_create_tm_list_tab` | 15489–15966 | 478 | Построение списка TM (478 строк) | K. Память переводов (TM) | `tr`, `log`, `invalidate_translation_cache`, `_show_create_tm_dialog` | `create_translation_memories_tab` | `current_project`, `_show_tm_maintenance_dialog`, `tr`, `invalidate_translation_cache` | — | modules/tm_controller | HIGH |
| `_show_tm_context_menu` | 15968–16026 | 59 | Zero-ref контекстное меню TM | Legacy/мёртвое | `_toggle_tm_readonly`, `_set_tm_as_project`, `_unset_tm_as_project` | **dead-candidate** | `current_project`, `_toggle_tm_readonly`, `_set_tm_as_project`, `_unset_tm_as_project` | — | PROBABLY_DEAD | LOW |
| `_set_tm_as_project` | 16028–16035 | 8 | Вызывается только из мёртвого _show_tm_context_menu | Legacy/мёртвое | `log` | `_show_tm_context_menu`, **dead-candidate** | `log` | menu×1 | PROBABLY_DEAD | LOW |
| `_unset_tm_as_project` | 16037–16044 | 8 | Вызывается только из мёртвого _show_tm_context_menu | Legacy/мёртвое | `log` | `_show_tm_context_menu`, **dead-candidate** | `log` | menu×1 | PROBABLY_DEAD | LOW |
| `_toggle_tm_readonly` | 16046–16054 | 9 | Вызывается только из мёртвого _show_tm_context_menu | Legacy/мёртвое | `log` | `_show_tm_context_menu`, **dead-candidate** | `log` | menu×1 | PROBABLY_DEAD | LOW |
| `import_tmx_file` | 16056–16231 | 176 | Zero-ref импорт TMX (заменён _import_tmx_as_tm) | Legacy/мёртвое | `log`, `tr`, `_show_language_variant_dialog` | **dead-candidate** | `tm_database`, `current_project`, `log`, `_show_language_variant_dialog` | — | PROBABLY_DEAD | LOW |
| `_show_language_variant_dialog` | 16233–16297 | 65 | Вызывается только из мёртвого import_tmx_file | Legacy/мёртвое | `tr` | `import_tmx_file`, **dead-candidate** | `tr` | — | PROBABLY_DEAD | LOW |
| `export_document` | 16299–16343 | 45 | Меню экспорта документа | N. Экспорт | `export_okapi_merge`, `export_target_only_docx` | динамич. вход | `current_project`, `export_okapi_merge`, `export_target_only_docx` | menu×1 | modules/export/docx_export | LOW |
| `_project_export_path` | 16345–16359 | 15 | Путь экспорта проекта | N. Экспорт | `log` | `export_target_only_docx`, `export_okapi_merge`, `export_simple_txt` | `log` | — | modules/export/docx_export | LOW |
| `_prompt_for_original_source` | 16361–16416 | 56 | Запрос оригинального DOCX | N. Экспорт | `tr`, `log` | `export_target_only_docx` | `log`, `tr`, `current_project`, `IMPORT_DOCUMENT_FORMATS` | — | modules/export/docx_export | LOW |
| `_segments_with_lost_formatting_tags` | 16428–16469 | 42 | Сегменты с потерянными тегами | N. Экспорт | — | `_warn_lost_formatting_tags` | `_INLINE_TAG_RE`, `_TAG_FRIENDLY_NAMES` | — | modules/export/docx_export | LOW |
| `_warn_lost_formatting_tags` | 16471–16502 | 32 | Предупреждение о потерянных тегах | N. Экспорт | `tr`, `_segments_with_lost_formatting_tags` | `export_target_only_docx` | `_segments_with_lost_formatting_tags`, `tr` | — | modules/export/docx_export | LOW |
| `export_target_only_docx` | 16504–16944 | 441 | Экспорт target-only DOCX (441 строка) | N. Экспорт | `log`, `_attach_segment_notes_as_docx_comments`, `_verify_export_word_count`, `_show_export_word_count_warning` | `export_document` | `current_project`, `_attach_segment_notes_as_docx_comments`, `log`, `_verify_export_word_count` | — | modules/export/docx_export | HIGH |
| `_split_docx_run_at_offset` | 16946–17005 | 60 | Разрезание docx-run по смещению (static) | O. Обработка документов | — | `_find_or_split_runs_for_range` | — | — | modules/export/docx_export | LOW |
| `_find_or_split_runs_for_range` | 17007–17067 | 61 | Поиск/нарезка runs для диапазона (static) | O. Обработка документов | `_split_docx_run_at_offset` | `_runs_for_segment_span`, `_attach_segment_notes_as_docx_comments` | `_split_docx_run_at_offset` | — | modules/export/docx_export | LOW |
| `_snap_range_to_word_boundaries` | 17070–17097 | 28 | Привязка диапазона к границам слов (static) | O. Обработка документов | — | `_attach_segment_notes_as_docx_comments` | — | — | modules/export/docx_export | LOW |
| `_comment_author_and_initials` | 17099–17116 | 18 | Автор комментариев (static) | O. Обработка документов | `get_translator_name` | `_attach_segment_notes_as_docx_comments` | `get_translator_name` | — | modules/export/docx_export | LOW |
| `_strip_inline_tags` | 17125–17134 | 10 | Удаление inline-тегов (classmethod) | O. Обработка документов | — | `_runs_for_segment_span`, `_attach_segment_notes_as_docx_comments` | — | — | modules/tag_formatting | LOW |
| `_raw_to_visible_offset` | 17137–17154 | 18 | Смещение raw->visible (classmethod) | O. Обработка документов | — | `_attach_segment_notes_as_docx_comments` | — | — | modules/tag_formatting | LOW |
| `_runs_for_segment_span` | 17156–17177 | 22 | Runs для диапазона сегмента (static) | O. Обработка документов | `_strip_inline_tags`, `_find_or_split_runs_for_range` | `_attach_segment_notes_as_docx_comments` | `_strip_inline_tags`, `_find_or_split_runs_for_range` | — | modules/export/docx_export | LOW |
| `_normalize_docx_run_font_sizes` | 17179–17267 | 89 | Нормализация размеров шрифта runs | O. Обработка документов | `log` | `_try_okapi_merge_export` | `log` | — | modules/export/docx_export | LOW |
| `_attach_segment_notes_as_docx_comments` | 17269–17511 | 243 | Заметки сегментов как комментарии DOCX | O. Обработка документов | `log`, `_runs_for_segment_span`, `_strip_inline_tags`, `_raw_to_visible_offset` | `export_target_only_docx`, `_try_okapi_merge_export` | `_comment_author_and_initials`, `log`, `_strip_inline_tags`, `_runs_for_segment_span` | — | modules/export/docx_export | MEDIUM |
| `_count_words` | 17532–17542 | 11 | Подсчёт слов (static, дубль в modules) | O. Обработка документов | — | `_count_expected_target_words`, `_count_exported_docx_words` | — | — | modules/export/docx_export | LOW |
| `_count_expected_target_words` | 17544–17553 | 10 | Ожидаемое число слов | N. Экспорт | `_count_words` | `_verify_export_word_count` | `_count_words` | — | modules/export/docx_export | LOW |
| `_count_exported_docx_words` | 17555–17585 | 31 | Подсчёт слов экспорта | N. Экспорт | `_count_words`, `log` | `_verify_export_word_count` | `_count_words`, `log` | — | modules/export/docx_export | LOW |
| `_verify_export_word_count` | 17587–17626 | 40 | Проверка числа слов при экспорте | N. Экспорт | `log`, `_count_exported_docx_words`, `_count_expected_target_words`, `_load_settings_section` | `export_target_only_docx`, `_try_okapi_merge_export`, `_export_multifile_to_folder` | `_count_exported_docx_words`, `_count_expected_target_words`, `EXPORT_WORD_COUNT_DEFAULT_THRESHOLD`, `log` | — | modules/export/docx_export | LOW |
| `_show_export_word_count_warning` | 17628–17656 | 29 | Предупреждение о расхождении слов | N. Экспорт | `tr` | `export_target_only_docx`, `_try_okapi_merge_export`, `_export_multifile_to_folder` | `tr` | — | modules/export/docx_export | LOW |
| `_try_okapi_merge_export` | 17658–17805 | 148 | Okapi merge-экспорт | N. Экспорт | `log`, `_verify_export_word_count`, `_show_export_word_count_warning`, `_normalize_docx_run_font_sizes` | `export_target_only_docx`, `export_okapi_merge` | `log`, `_verify_export_word_count`, `_show_export_word_count_warning`, `okapi_sidecar` | — | modules/export/docx_export | MEDIUM |
| `export_review_table_with_tags` | 17807–17813 | 7 | Экспорт review-таблицы (меню) | N. Экспорт | `_export_review_table` | динамич. вход | `_export_review_table` | menu×1 | modules/export/docx_export | LOW |
| `_add_hyperlink_to_paragraph` | 17815–17856 | 42 | Гиперссылка в параграф | O. Обработка документов | — | `_export_review_table` | — | — | modules/export/docx_export | LOW |
| `_export_review_table` | 17858–18354 | 497 | Экспорт review-таблицы (497 строк) | N. Экспорт | `log`, `_add_hyperlink_to_paragraph`, `_sync_grid_targets_to_segments` | `export_review_table_with_tags` | `current_project`, `current_project_path`, `_sync_grid_targets_to_segments`, `_add_hyperlink_to_paragraph` | — | modules/export/docx_export | HIGH |
| `export_tmx_from_grid` | 18356–18429 | 74 | TMX из грида | Q. TMX | `log` | `export_tm_as_tmx` | `log`, `current_project`, `hide_outer_wrapping_tags` | menu×1 | modules/export/tmx_export | LOW |
| `export_tmx_from_selected` | 18431–18521 | 91 | TMX из выбранных | Q. TMX | `log` | динамич. вход | `log`, `current_project`, `table`, `hide_outer_wrapping_tags` | menu×1 | modules/export/tmx_export | LOW |
| `export_tmx_from_tm_database` | 18523–18601 | 79 | TMX из TM-базы | Q. TMX | `log` | динамич. вход | `current_project`, `tm_database`, `log`, `hide_outer_wrapping_tags` | menu×1 | modules/export/tmx_export | LOW |
| `export_tm_as_tmx` | 18603–18605 | 3 | Zero-ref thin-wrapper | Legacy/мёртвое | `export_tmx_from_grid` | **dead-candidate** | `export_tmx_from_grid` | — | PROBABLY_DEAD | LOW |
| `clear_tm_entries` | 18610–18647 | 38 | Zero-ref очистка TM (опасный дубликат) | Legacy/мёртвое | `log` | **dead-candidate** | `tm_database`, `log`, `user_data_path` | — | PROBABLY_DEAD | LOW |
| `create_segmentation_rules_tab` | 18649–18737 | 89 | Вкладка правил сегментации | U. Настройки (UI) | `tr` | `create_settings_tab` | `test_segmentation_rules`, `tr` | — | modules/settings_tabs | LOW |
| `test_segmentation_rules` | 18739–18787 | 49 | Тест правил сегментации | U. Настройки (UI) | — | динамич. вход | — | signal:clicked×1 | modules/settings_tabs | LOW |
| `_update_both_termlens` | 18789–18840 | 52 | Обновление TermLens dock+popup | TermLens | `log`, `reverse_invisible_replacements` | `_update_termlens_for_segment`, `_refresh_termbase_display_for_current_segment`, `_quick_add_term_with_priority` | `termlens_widget`, `termlens_widget_match`, `current_project`, `reverse_invisible_replacements` | — | modules/termlens_controller | MEDIUM |
| `_update_termlens_for_segment` | 18842–18879 | 38 | TermLens для сегмента | TermLens | `find_termbase_matches_in_source`, `find_nt_matches_in_source`, `_get_termbase_status_hint`, `_update_both_termlens` | `confirm_and_next_unconfirmed` | `find_termbase_matches_in_source`, `find_nt_matches_in_source`, `_get_termbase_status_hint`, `_update_both_termlens` | — | modules/termlens_controller | LOW |
| `_get_termbase_status_hint` | 18881–18943 | 63 | Подсказка статуса termbase | TermLens | `_convert_language_to_code`, `log` | `_update_termlens_for_segment`, `_refresh_termbase_display_for_current_segment`, `_quick_add_term_with_priority` | `current_project`, `termbase_mgr`, `_convert_language_to_code`, `log` | — | modules/termlens_controller | LOW |
| `_refresh_termbase_display_for_current_segment` | 18945–19084 | 140 | Подсветка термина в source | L. Termbase/глоссарий | `log`, `find_termbase_matches_in_source`, `highlight_source_with_termbase`, `find_nt_matches_in_source` | `add_term_pair_to_termbase`, `_force_termlens_display_redraw`, `_quick_add_term_with_priority` | `termbase_cache_lock`, `find_termbase_matches_in_source`, `results_panels`, `highlight_source_with_termbase` | — | modules/termlens_controller | MEDIUM |
| `_orient_term_for_termbase` | 19086–19164 | 79 | Ориентация термина (язык) | L. Termbase/глоссарий | `_convert_language_to_code`, `log` | `_detect_and_merge_synonyms`, `add_term_pair_to_termbase`, `_quick_add_term_with_priority` | `current_project`, `_convert_language_to_code`, `log` | — | modules/termbase_service | LOW |
| `_detect_and_merge_synonyms` | 19166–19281 | 116 | Детект и merge синонимов | L. Termbase/глоссарий | `log`, `_orient_term_for_termbase` | `add_term_pair_to_termbase`, `_quick_add_term_with_priority` | `_orient_term_for_termbase`, `termbase_mgr`, `log`, `db_manager` | — | modules/termbase_service | MEDIUM |
| `add_term_pair_to_termbase` | 19283–19526 | 244 | Добавление пары в termbase | L. Termbase/глоссарий | `log`, `statusBar`, `_play_sound_effect`, `_detect_and_merge_synonyms` | динамич. вход | `current_project`, `log`, `_detect_and_merge_synonyms`, `termbase_mgr` | duck-typed×6, hasattr×4, string×4 | modules/termbase_service | MEDIUM |
| `_snapshot_termbase_db_state` | 19579–19598 | 20 | Снимок состояния БД termbase | L. Termbase/глоссарий | — | `_setup_termbase_db_watcher`, `_build_termbase_index`, `force_refresh_matches` | `db_manager` | — | modules/termbase_service | LOW |
| `_setup_termbase_db_watcher` | 19600–19687 | 88 | Watcher изменений БД termbase | L. Termbase/глоссарий | `log`, `_snapshot_termbase_db_state` | `load_project` | `_snapshot_termbase_db_state`, `_on_termbase_db_debounce_fire`, `log`, `db_manager` | — | modules/termbase_service | LOW |
| `_on_termbase_db_debounce_fire` | 19689–19703 | 15 | Debounce-refresh по изменению БД | L. Termbase/глоссарий | `force_refresh_matches`, `log` | динамич. вход | `force_refresh_matches`, `log` | timer×1 | modules/termbase_service | LOW |
| `_force_termlens_display_redraw` | 19705–19747 | 43 | Zero-ref перерисовка TermLens | Legacy/мёртвое | `force_refresh_matches`, `_refresh_termbase_display_for_current_segment`, `log` | **dead-candidate** | `force_refresh_matches`, `_refresh_termbase_display_for_current_segment`, `log` | — | PROBABLY_DEAD | LOW |
| `_post_termbase_delete_refresh` | 19749–19803 | 55 | Refresh после удаления термина | L. Termbase/глоссарий | `log`, `force_refresh_matches`, `termbase_tab_refresh_callback` | `create_termbases_tab`, `_show_edit_terms_dialog`, `_on_termlens_edit_entry` | `force_refresh_matches`, `termbase_tab_refresh_callback`, `log` | duck-typed×2 | modules/termbase_service | LOW |
| `_quick_add_term_with_priority` | 19805–20135 | 331 | Быстрое добавление термина (хоткеи, 331 строка) | L. Termbase/глоссарий | `statusBar`, `log`, `_play_sound_effect`, `_refresh_termbase_display_for_current_segment` | `setup_global_shortcuts` | `log`, `_detect_and_merge_synonyms`, `_orient_term_for_termbase`, `table` | duck-typed×8, hasattr×5, string×5, shortcut-registry×2 | modules/termbase_service | HIGH |
| `add_word_to_dictionary_shortcut` | 20137–20169 | 33 | Слово в словарь (хоткей) | L. Termbase/глоссарий | `statusBar` | динамич. вход | `statusBar` | shortcut-registry×1 | modules/termbase_service | LOW |
| `add_text_to_non_translatables` | 20173–20288 | 116 | Текст в non-translatables | L. Termbase/глоссарий | `log`, `_convert_language_to_code`, `statusBar`, `_play_sound_effect` | динамич. вход | `current_project`, `log`, `termbase_mgr`, `_convert_language_to_code` | duck-typed×6, hasattr×4, string×4 | modules/termbase_service | MEDIUM |
| `create_termbases_tab` | 20290–21566 | 1277 | Вкладка termbase (1277 строк!) | L. Termbase/глоссарий | `tr`, `log`, `_build_termbase_index`, `_normalize_language_code` | `create_main_layout` | `db_manager`, `log`, `tr`, `current_project` | — | modules/termbase_tab | VERY_HIGH |
| `_show_create_termbase_dialog` | 21568–21668 | 101 | Диалог создания termbase | L. Termbase/глоссарий | `tr`, `_play_sound_effect` | `create_termbases_tab` | `tr`, `_play_sound_effect` | signal:clicked×1 | modules/termbase_tab | LOW |
| `_show_term_extraction_dialog` | 21670–22099 | 430 | LLM-извлечение терминов (430 строк) | L. Termbase/глоссарий | `tr`, `log`, `load_llm_settings`, `load_api_keys` | `create_termbases_tab` | `tr`, `load_llm_settings`, `load_api_keys`, `create_llm_client` | signal:clicked×1 | modules/termbase_tab | HIGH |
| `_show_termbase_context_menu` | 22101–22134 | 34 | Контекстное меню termbase | L. Termbase/глоссарий | `_rename_termbase_dialog`, `_delete_termbase` | `create_termbases_tab` | `_rename_termbase_dialog`, `_delete_termbase` | signal:customContextMenuRequested×1 | modules/termbase_tab | LOW |
| `_rename_termbase_dialog` | 22136–22158 | 23 | Переименование termbase | L. Termbase/глоссарий | `log` | `_show_termbase_context_menu` | `log`, `termbase_cache_lock`, `termbase_cache` | menu×1 | modules/termbase_tab | LOW |
| `_delete_termbase` | 22160–22209 | 50 | Удаление termbase | L. Termbase/глоссарий | `log` | `create_termbases_tab`, `_show_termbase_context_menu` | `db_manager`, `log`, `termbase_cache_lock`, `termbase_cache` | signal:clicked×1, menu×1 | modules/termbase_tab | LOW |
| `_refresh_termbase_table` | 22211–22233 | 23 | Обновление таблицы termbase | L. Termbase/глоссарий | `log` | `_import_termbase` | `current_project`, `log`, `db_manager` | — | modules/termbase_tab | LOW |
| `_import_termbase` | 22235–22470 | 236 | Импорт termbase (TSV/CSV) | L. Termbase/глоссарий | `tr`, `log`, `_refresh_termbase_table` | `create_termbases_tab` | `db_manager`, `log`, `tr`, `termbase_cache_lock` | signal:clicked×1 | modules/termbase_tab | MEDIUM |
| `_export_termbase` | 22472–22558 | 87 | Экспорт termbase | L. Termbase/глоссарий | `tr`, `log` | `create_termbases_tab` | `db_manager`, `log`, `tr` | signal:clicked×1 | modules/termbase_tab | LOW |
| `_update_term_forbidden` | 22560–22568 | 9 | Toggle forbidden термина | L. Termbase/глоссарий | `log` | `_show_edit_terms_dialog` | `db_manager`, `log` | signal:toggled×1 | modules/termbase_tab | LOW |
| `_show_edit_terms_dialog` | 22570–22902 | 333 | Zero-ref диалог правки терминов (заменён TermbaseEntryEditor) | Legacy/мёртвое | `tr`, `log`, `_build_termbase_index`, `_update_term_forbidden` | **dead-candidate** | `tr`, `db_manager`, `log`, `termbase_cache_lock` | — | PROBABLY_DEAD | LOW |
| `_show_create_tm_dialog` | 22908–23003 | 96 | Диалог создания TM | K. Память переводов (TM) | `tr` | `_create_tm_list_tab` | `tr` | signal:clicked×1 | modules/tm_controller | LOW |
| `_import_tmx_as_tm` | 23005–23399 | 395 | Импорт TMX как TM (395 строк) | K. Память переводов (TM) | `tr`, `log`, `initialize_tm_database` | `_create_tm_list_tab` | `tm_database`, `tr`, `initialize_tm_database`, `log` | signal:clicked×1 | modules/tm_controller | HIGH |
| `_attach_sdltm_as_tm` | 23401–23628 | 228 | Подключение SDLTM как TM | K. Память переводов (TM) | `log`, `initialize_tm_database`, `tr` | `_create_tm_list_tab` | `tm_database`, `initialize_tm_database`, `tr`, `log` | signal:clicked×1 | modules/tm_controller | MEDIUM |
| `_sync_external_tms` | 23630–23670 | 41 | Таймер синка внешних TM | K. Память переводов (TM) | `_delta_sync_external_tm` | динамич. вход | `db_manager`, `_delta_sync_external_tm` | timer×1 | modules/tm_controller | LOW |
| `_delta_sync_external_tm` | 23672–23728 | 57 | Дельта-синк внешних TM | K. Память переводов (TM) | `log` | `_sync_external_tms` | `log`, `db_manager` | — | modules/tm_controller | MEDIUM |
| `_export_tm_to_tmx` | 23730–23802 | 73 | Экспорт TM в TMX | K. Память переводов (TM) | `log` | `_create_tm_list_tab` | `db_manager`, `log` | signal:clicked×1 | modules/tm_controller | LOW |
| `_delete_tm` | 23804–23832 | 29 | Удаление TM | K. Память переводов (TM) | — | `_create_tm_list_tab` | — | signal:clicked×1 | modules/tm_controller | LOW |
| `_show_tm_editor_dialog` | 23834–23851 | 18 | Диалог редактора TM | K. Память переводов (TM) | — | `_create_tm_list_tab` | `db_manager`, `log` | signal:clicked×1 | modules/tm_controller | LOW |
| `create_settings_tab` | 23857–23990 | 134 | Вкладка настроек (роутер сабтабов) | U. Настройки (UI) | `tr`, `_create_general_settings_tab`, `_create_backup_settings_tab`, `_create_autocorrect_settings_tab` | `create_main_layout` | `_create_general_settings_tab`, `_create_backup_settings_tab`, `_create_autocorrect_settings_tab`, `_create_user_identity_tab` | — | SupervertalerQt (ядро) | MEDIUM |
| `_wrap_in_scroll` | 23999–24054 | 56 | Обёртка сабтаба в scroll | U. Настройки (UI) | — | `create_settings_tab` | `SETTINGS_CONTENT_MAX_WIDTH`, `_settings_wheel_guards` | — | modules/settings_tabs | LOW |
| `_update_settings_sidebar_theme` | 24056–24068 | 13 | Тема sidebar настроек | V. Тема/UI-стили | — | `create_settings_tab`, `refresh_theme_colors` | `theme_manager`, `settings_tabs` | — | modules/settings_tabs | LOW |
| `_update_tools_sidebar_theme` | 24070–24082 | 13 | Тема sidebar инструментов | V. Тема/UI-стили | — | `refresh_theme_colors` | `theme_manager`, `modules_tabs` | — | modules/settings_tabs | LOW |
| `_update_resources_sidebar_theme` | 24084–24086 | 3 | Тема resources-sidebar | V. Тема/UI-стили | — | `refresh_theme_colors` | — | — | modules/settings_tabs | LOW |
| `_create_language_pair_tab` | 24088–24183 | 96 | Вкладка языковой пары | U. Настройки (UI) | `tr`, `save_language_settings`, `log`, `_save_language_settings_from_ui` | `create_settings_tab` | `source_language`, `target_language`, `tr`, `save_language_settings` | — | modules/settings_tabs | MEDIUM |
| `_create_ai_settings_tab` | 24185–25230 | 1046 | Вкладка AI/LLM настроек (1046 строк!) | U. Настройки (UI) | `tr`, `load_general_settings`, `load_llm_settings`, `load_provider_enabled_states` | `create_settings_tab` | `load_llm_settings`, `load_provider_enabled_states`, `load_general_settings`, `load_api_keys` | — | modules/settings_tabs | VERY_HIGH |
| `_create_mt_settings_tab` | 25232–25342 | 111 | Вкладка MT-настроек | U. Настройки (UI) | `tr`, `load_provider_enabled_states`, `load_api_keys`, `_save_mt_settings_from_ui` | `create_settings_tab` | `load_provider_enabled_states`, `load_api_keys`, `tr`, `_api_key_inputs` | — | modules/settings_tabs | MEDIUM |
| `_create_mt_quick_lookup_settings_tab` | 25352–25730 | 379 | Вкладка MT Quick Lookup (379 строк) | U. Настройки (UI) | `tr`, `load_llm_settings`, `load_general_settings`, `load_api_keys` | `create_settings_tab` | `_custom_mt_profiles`, `load_general_settings`, `load_api_keys`, `load_provider_enabled_states` | — | modules/settings_tabs | HIGH |
| `_save_mt_quick_lookup_settings` | 25732–25770 | 39 | Сохранение MT Quick Lookup | U. Настройки (UI) | `load_general_settings`, `save_general_settings`, `log`, `load_llm_settings` | динамич. вход | `load_general_settings`, `save_general_settings`, `_custom_mt_profiles`, `log` | signal:clicked×1 | modules/settings_tabs | LOW |
| `open_mt_quick_lookup_settings` | 25772–25802 | 31 | Переход к MT Quick Lookup | U. Настройки (UI) | `_bring_workbench_forward` | динамич. вход | `_bring_workbench_forward`, `mt_quick_lookup_tab_index`, `main_tabs`, `settings_tabs` | duck-typed×5 | SupervertalerQt (ядро) | LOW |
| `_find_autohotkey_for_settings` | 25804–25820 | 17 | Поиск AutoHotkey | U. Настройки (UI) | — | динамич. вход | — | duck-typed×2 | modules/settings_tabs | LOW |
| `_browse_autohotkey_for_settings` | 25822–25832 | 11 | Браузер пути AutoHotkey | U. Настройки (UI) | — | динамич. вход | — | duck-typed×2 | modules/settings_tabs | LOW |
| `_create_backup_settings_tab` | 25834–25967 | 134 | Вкладка backup-настроек | U. Настройки (UI) | `tr`, `_live_save_backup_settings`, `load_general_settings` | `create_settings_tab` | `load_general_settings`, `tr`, `_live_save_backup_settings`, `user_data_path` | — | modules/settings_tabs | MEDIUM |
| `_live_save_backup_settings` | 25969–25984 | 16 | Live-сохранение backup-настроек | AB. Персистентность (settings IO) | `load_general_settings`, `save_general_settings`, `restart_auto_backup_timer`, `log` | `_create_backup_settings_tab` | `load_general_settings`, `save_general_settings`, `restart_auto_backup_timer`, `enable_backup_cb` | signal:valueChanged×3, signal:toggled×2 | modules/settings_tabs | LOW |
| `_create_general_settings_tab` | 25986–26809 | 824 | Общие настройки (824 строки!) | U. Настройки (UI) | `tr`, `log`, `load_general_settings`, `_get_unified_settings_path` | `create_settings_tab` | `load_general_settings`, `_get_unified_settings_path`, `allow_replace_in_source`, `tr` | — | modules/settings_tabs | VERY_HIGH |
| `_create_clipboard_settings_tab` | 26811–27041 | 231 | Настройки буфера обмена | U. Настройки (UI) | `tr`, `log`, `load_clipboard_privacy_settings`, `save_clipboard_privacy_settings` | `create_settings_tab` | `load_clipboard_privacy_settings`, `save_clipboard_privacy_settings`, `tr`, `log` | — | modules/settings_tabs | MEDIUM |
| `_create_autocorrect_settings_tab` | 27043–27133 | 91 | Настройки автокоррекции | U. Настройки (UI) | `tr`, `_persist_autocorrect_settings`, `log` | `create_settings_tab` | `tr`, `_persist_autocorrect_settings`, `log`, `autocorrect_rule_overrides` | — | modules/settings_tabs | MEDIUM |
| `_persist_autocorrect_settings` | 27135–27146 | 12 | Сохранение настроек автокоррекции | AB. Персистентность (settings IO) | `save_general_settings`, `_load_settings_section`, `log` | `_create_autocorrect_settings_tab` | `autocorrect_enabled`, `autocorrect_rule_overrides`, `save_general_settings`, `_load_settings_section` | — | modules/settings_tabs | LOW |
| `_create_view_settings_tab` | 27148–28046 | 899 | Вкладка вида (899 строк!) | U. Настройки (UI) | `tr`, `_apply_global_ui_font_scale`, `load_general_settings`, `_get_ui_chrome_compact` | `create_settings_tab` | `load_general_settings`, `default_font_family`, `_confirmed_words_checkbox`, `_apply_ui_chrome_compactness` | — | modules/settings_tabs | VERY_HIGH |
| `_populate_voice_commands_table` | 28048–28064 | 17 | Таблица голосовых команд | VOICE | — | `_reset_voice_commands` | — | duck-typed×1 | modules/voice_controller | LOW |
| `_reset_voice_commands` | 28066–28078 | 13 | Сброс голосовых команд | VOICE | `_populate_voice_commands_table` | динамич. вход | `voice_command_manager`, `_populate_voice_commands_table` | duck-typed×1 | modules/voice_controller | LOW |
| `_check_ahk_installed` | 28080–28086 | 7 | Проверка AHK | VOICE | — | динамич. вход | `voice_command_manager` | duck-typed×1 | modules/voice_controller | LOW |
| `_open_voice_scripts_folder` | 28088–28093 | 6 | Открыть папку voice-скриптов | VOICE | — | динамич. вход | `user_data_path` | duck-typed×1 | modules/voice_controller | LOW |
| `_toggle_alwayson_listening` | 28095–28208 | 114 | Toggle always-on прослушивания | VOICE | `log`, `_update_alwayson_ui`, `load_dictation_settings`, `load_voice_vocabulary_settings` | `_on_alwayson_tray_activated`, `_toggle_alwayson_from_statusbar`, `_toggle_alwayson_from_grid_btn` | `voice_listener`, `_update_alwayson_ui`, `log`, `status_bar` | duck-typed×3, shortcut-registry×1, menu×1, hasattr×1 | modules/voice_controller | HIGH |
| `_update_alwayson_ui` | 28210–28347 | 138 | UI always-on статуса | VOICE | `tr`, `_update_alwayson_tray_icon` | `_toggle_alwayson_listening`, `_on_alwayson_vad_status` | `_update_alwayson_tray_icon`, `alwayson_indicator_label`, `alwayson_status_label`, `tr` | signal:listening_started×1, signal:listening_stopped×1 | modules/voice_controller | MEDIUM |
| `_draw_mic_icon` | 28350–28399 | 50 | Иконка микрофона (static) | VOICE | — | `_ensure_alwayson_tray_icon` | — | — | modules/voice_controller | LOW |
| `_ensure_alwayson_tray_icon` | 28401–28445 | 45 | Tray-иконка always-on | VOICE | `_draw_mic_icon`, `tr` | `__init__`, `_update_alwayson_tray_icon` | `_draw_mic_icon`, `_alwayson_tray_icon_normal`, `_toggle_alwayson_listening`, `_open_voice_in_workbench` | — | modules/voice_controller | LOW |
| `_on_alwayson_tray_activated` | 28447–28451 | 5 | Клик по tray-иконке | VOICE | `_toggle_alwayson_listening` | динамич. вход | `_toggle_alwayson_listening` | shortcut×1 | modules/voice_controller | LOW |
| `_update_alwayson_tray_icon` | 28453–28483 | 31 | Обновление tray-иконки | VOICE | `_ensure_alwayson_tray_icon` | `_update_alwayson_ui` | `_ensure_alwayson_tray_icon`, `_alwayson_tray_icon_red`, `_alwayson_tray_icon_normal`, `_alwayson_tray_active` | — | modules/voice_controller | LOW |
| `_on_alwayson_speech` | 28485–28487 | 3 | Событие speech | VOICE | `log` | динамич. вход | `log` | signal:speech_detected×1 | modules/voice_controller | LOW |
| `_on_alwayson_command` | 28489–28492 | 4 | Событие command | VOICE | `log` | динамич. вход | `log`, `status_bar` | signal:command_detected×1 | modules/voice_controller | LOW |
| `_on_alwayson_dictation` | 28494–28528 | 35 | Событие dictation -> вставка текста | VOICE | `log`, `_insert_dictated_text`, `load_dictation_settings` | динамич. вход | `_insert_dictated_text`, `log`, `load_dictation_settings` | signal:text_for_dictation×1 | modules/voice_controller | MEDIUM |
| `_on_alwayson_status` | 28530–28535 | 6 | Событие status | VOICE | `log` | динамич. вход | `log` | signal:status_update×1 | modules/voice_controller | LOW |
| `_on_alwayson_error` | 28537–28540 | 4 | Событие error | VOICE | `log` | динамич. вход | `log` | signal:error_occurred×1 | modules/voice_controller | LOW |
| `_on_alwayson_vad_status` | 28542–28562 | 21 | VAD-статус -> PTT stop | VOICE | `_update_alwayson_ui`, `_do_voice_command_ptt_stop` | динамич. вход | `_update_alwayson_ui`, `_do_voice_command_ptt_stop`, `_voice_command_ptt_last_vad_state` | signal:vad_status_changed×1 | modules/voice_controller | MEDIUM |
| `_toggle_alwayson_from_statusbar` | 28564–28566 | 3 | Toggle из статус-бара | VOICE | `_toggle_alwayson_listening` | `_setup_progress_indicators` | `_toggle_alwayson_listening` | — | modules/voice_controller | LOW |
| `_toggle_alwayson_from_grid_btn` | 28568–28570 | 3 | Toggle из кнопки грида | VOICE | `_toggle_alwayson_listening` | `create_grid_view_widget_for_home` | `_toggle_alwayson_listening` | signal:clicked×1 | modules/voice_controller | LOW |
| `_create_system_prompts_tab` | 28573–28692 | 120 | Вкладка системных промптов | U. Настройки (UI) | `tr`, `_load_system_prompt_into_editor`, `_reset_system_prompt`, `_save_system_prompt_from_ui` | `create_settings_tab` | `_load_system_prompt_into_editor`, `tr`, `_reset_system_prompt`, `_save_system_prompt_from_ui` | — | modules/settings_tabs | MEDIUM |
| `_load_system_prompt_into_editor` | 28694–28726 | 33 | Загрузка системного промпта | U. Настройки (UI) | — | `_create_system_prompts_tab` | `user_data_path`, `prompt_manager_qt` | signal:currentIndexChanged×1 | modules/settings_tabs | LOW |
| `_save_system_prompt_from_ui` | 28728–28768 | 41 | Сохранение системного промпта | U. Настройки (UI) | `log` | `_create_system_prompts_tab` | `log`, `user_data_path`, `prompt_manager_qt` | signal:clicked×1 | modules/settings_tabs | LOW |
| `_reset_system_prompt` | 28770–28805 | 36 | Сброс системного промпта | U. Настройки (UI) | `log` | `_create_system_prompts_tab` | `log`, `prompt_manager_qt` | signal:clicked×1 | modules/settings_tabs | LOW |
| `_create_user_identity_tab` | 28807–28868 | 62 | Вкладка личности переводчика | U. Настройки (UI) | `tr`, `load_general_settings`, `_save_user_identity_from_ui` | `create_settings_tab` | `load_general_settings`, `tr`, `_save_user_identity_from_ui` | — | modules/settings_tabs | LOW |
| `_save_user_identity_from_ui` | 28870–28879 | 10 | Сохранение личности | AB. Персистентность (settings IO) | `load_general_settings`, `save_general_settings`, `log` | `_create_user_identity_tab` | `load_general_settings`, `save_general_settings`, `log` | signal:clicked×1 | modules/settings_tabs | LOW |
| `_create_voice_settings_tab` | 28881–28949 | 69 | Вкладка voice-настроек | U. Настройки (UI) | `tr` | `create_settings_tab` | `_open_voice_in_workbench`, `tr` | — | modules/settings_tabs | LOW |
| `_open_voice_in_workbench` | 28951–28965 | 15 | Открыть voice в Workbench | B. Жизненный цикл окна/Workbench | `_bring_workbench_forward`, `_ensure_voice_top_tab` | динамич. вход | `_bring_workbench_forward`, `_ensure_voice_top_tab`, `voice_tab_index`, `main_tabs` | menu×1, signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `_bring_workbench_forward` | 28967–29119 | 153 | Вывод окна на передний план | B. Жизненный цикл окна/Workbench | `isMinimized`, `show`, `raise_`, `activateWindow` | `_on_bridge_prompt_request`, `open_mt_quick_lookup_settings`, `_open_voice_in_workbench` | `isMinimized`, `show`, `raise_`, `activateWindow` | — | SupervertalerQt (ядро) | HIGH |
| `_verify_foreground_grab` | 29121–29154 | 34 | Проверка захвата фокуса | B. Жизненный цикл окна/Workbench | `_repair_null_keyboard_focus`, `log`, `winId` | динамич. вход | `log`, `winId`, `_repair_null_keyboard_focus` | singleShot×1 | SupervertalerQt (ядро) | MEDIUM |
| `_repair_null_keyboard_focus` | 29156–29187 | 32 | Ремонт клавиатурного фокуса | B. Жизненный цикл окна/Workbench | `log` | `_verify_foreground_grab` | `log` | — | SupervertalerQt (ядро) | MEDIUM |
| `_dismiss_menu_activation` | 29189–29203 | 15 | Гашение активации меню | B. Жизненный цикл окна/Workbench | `menuBar` | `_bring_workbench_forward` | `menuBar` | — | SupervertalerQt (ядро) | MEDIUM |
| `open_workbench_to_superlookup` | 29205–29279 | 75 | Открыть Workbench на SuperLookup | B. Жизненный цикл окна/Workbench | `log`, `_bring_workbench_forward`, `_ensure_superlookup_top_tab` | `_go_to_superlookup` | `_bring_workbench_forward`, `log`, `_ensure_superlookup_top_tab`, `superlookup_tab_index` | duck-typed×6, hasattr×2, string×2 | SupervertalerQt (ядро) | MEDIUM |
| `open_workbench_to_clipboard` | 29281–29371 | 91 | Открыть Workbench на Clipboard | B. Жизненный цикл окна/Workbench | `log`, `_bring_workbench_forward`, `_ensure_clipboard_top_tab`, `isActiveWindow` | `open_clipboard_tab` | `_bring_workbench_forward`, `log`, `_ensure_clipboard_top_tab`, `clipboard_tab_index` | duck-typed×3, hasattr×2, string×2 | SupervertalerQt (ядро) | MEDIUM |
| `open_settings_to_keyboard_shortcuts` | 29373–29396 | 24 | Открыть настройки хоткеев | B. Жизненный цикл окна/Workbench | `_bring_workbench_forward` | динамич. вход | `_bring_workbench_forward` | duck-typed×1 | SupervertalerQt (ядро) | LOW |
| `reload_global_hotkeys` | 29398–29415 | 18 | Перезагрузка глобальных хоткеев | AD. Горячие клавиши | `log` | динамич. вход | `log` | duck-typed×2 | modules/shortcuts_wiring | LOW |
| `_create_debug_settings_tab` | 29417–29533 | 117 | Вкладка debug | U. Настройки (UI) | `tr`, `load_general_settings`, `_save_debug_settings_from_ui` | `create_settings_tab` | `load_general_settings`, `export_debug_log_now`, `clear_debug_log_buffer`, `tr` | — | modules/settings_tabs | LOW |
| `_save_debug_settings_from_ui` | 29535–29547 | 13 | Сохранение debug-настроек | AB. Персистентность (settings IO) | `load_general_settings`, `save_general_settings`, `log` | `_create_debug_settings_tab` | `debug_mode_enabled`, `debug_auto_export`, `load_general_settings`, `save_general_settings` | signal:clicked×1 | modules/settings_tabs | LOW |
| `export_debug_log_now` | 29549–29576 | 28 | Экспорт debug-лога | Логирование | `log` | динамич. вход | `debug_log_buffer`, `log` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `clear_debug_log_buffer` | 29578–29583 | 6 | Очистка debug-буфера | Логирование | `log` | динамич. вход | `debug_log_buffer`, `log` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `_save_llm_settings_from_ui` | 29585–29665 | 81 | Zero-ref сохранение LLM-настроек (заменено _save_ai_settings_from_ui) | Legacy/мёртвое | `save_llm_settings`, `load_provider_enabled_states`, `save_provider_enabled_states`, `load_general_settings` | **dead-candidate** | `save_llm_settings`, `load_provider_enabled_states`, `save_provider_enabled_states`, `load_general_settings` | — | PROBABLY_DEAD | LOW |
| `_save_ai_settings_from_ui` | 29667–29851 | 185 | Сохранение AI-настроек из UI | U. Настройки (UI) | `load_llm_settings`, `save_llm_settings`, `load_provider_enabled_states`, `save_provider_enabled_states` | `_create_ai_settings_tab` | `load_llm_settings`, `save_llm_settings`, `load_provider_enabled_states`, `save_provider_enabled_states` | signal:clicked×1 | modules/settings_tabs | MEDIUM |
| `_save_api_keys_from_ui` | 29853–29864 | 12 | Сохранение API-ключей | AB. Персистентность (settings IO) | `_load_settings_section`, `save_api_keys` | `_save_ai_settings_from_ui`, `_save_mt_settings_from_ui` | `_load_settings_section`, `save_api_keys`, `_api_key_inputs` | — | modules/settings_tabs | LOW |
| `_save_mt_settings_from_ui` | 29866–29885 | 20 | Сохранение MT-настроек | U. Настройки (UI) | `_save_api_keys_from_ui`, `load_provider_enabled_states`, `save_provider_enabled_states`, `log` | `_create_mt_settings_tab` | `_save_api_keys_from_ui`, `load_provider_enabled_states`, `save_provider_enabled_states`, `log` | signal:clicked×1 | modules/settings_tabs | LOW |
| `_save_general_settings_from_ui` | 29887–30077 | 191 | Сохранение общих настроек (191 строка) | U. Настройки (UI) | `log`, `update_warning_banner`, `load_general_settings`, `save_general_settings` | `_create_general_settings_tab` | `auto_fill_100_matches`, `current_project`, `update_warning_banner`, `load_general_settings` | signal:clicked×1 | modules/settings_tabs | MEDIUM |
| `_save_view_settings_from_ui` | 30079–30102 | 24 | Сохранение настроек вида (обёртка) | U. Настройки (UI) | `_save_view_settings_from_ui_impl` | `_create_view_settings_tab` | `_save_view_settings_from_ui_impl`, `_suppress_target_change_handlers` | — | modules/settings_tabs | LOW |
| `_save_view_settings_from_ui_impl` | 30104–30400 | 297 | Сохранение настроек вида (297 строк) | U. Настройки (UI) | `log`, `tr`, `load_general_settings`, `save_general_settings` | `_save_view_settings_from_ui` | `load_general_settings`, `save_general_settings`, `default_font_size`, `log` | — | modules/settings_tabs | MEDIUM |
| `_apply_global_ui_font_scale` | 30402–30428 | 27 | Глобальный масштаб шрифта | V. Тема/UI-стили | `load_general_settings`, `save_general_settings`, `_update_status_bar_fonts`, `_update_main_tabs_fonts` | `create_settings_tab`, `_create_view_settings_tab` | `load_general_settings`, `save_general_settings`, `_update_status_bar_fonts`, `_update_main_tabs_fonts` | signal:clicked×1, singleShot×1 | modules/settings_tabs | MEDIUM |
| `_update_status_bar_fonts` | 30430–30442 | 13 | Шрифты статус-бара | V. Тема/UI-стили | — | `_apply_global_ui_font_scale` | — | — | modules/settings_tabs | LOW |
| `_update_main_tabs_fonts` | 30444–30454 | 11 | Шрифты вкладок | V. Тема/UI-стили | — | `_apply_global_ui_font_scale` | `main_tabs`, `settings_tabs`, `modules_tabs` | — | modules/settings_tabs | LOW |
| `_get_global_ui_font_scale` | 30456–30461 | 6 | Чтение масштаба шрифта | V. Тема/UI-стили | `load_general_settings` | `__init__`, `_reinitialize_with_new_data_path`, `create_settings_tab` | `load_general_settings` | — | modules/settings_tabs | LOW |
| `_get_ui_chrome_compact` | 30463–30472 | 10 | Чтение compact-режима | V. Тема/UI-стили | `load_general_settings` | `create_settings_tab`, `_create_view_settings_tab` | `load_general_settings` | — | modules/settings_tabs | LOW |
| `_apply_ui_chrome_compactness` | 30474–30523 | 50 | Применение compact-режима | V. Тема/UI-стили | `load_general_settings`, `save_general_settings`, `menuBar`, `log` | `create_settings_tab` | `load_general_settings`, `save_general_settings`, `main_tabs`, `right_tabs` | signal:toggled×1, singleShot×1 | modules/settings_tabs | MEDIUM |
| `create_grid_view_widget` | 30525–30671 | 147 | Zero-ref билдер грида (заменён _for_home) | Legacy/мёртвое | `tr`, `toggle_invisible_display`, `_ensure_shared_filter`, `_get_warning_banner` | **dead-candidate** | `_get_warning_banner`, `_ensure_shared_filter`, `clear_filters`, `toggle_all_invisibles` | — | PROBABLY_DEAD | LOW |
| `create_grid_view_widget_for_home` | 30673–31556 | 884 | Главный билдер грида (884 строки!) | E. Грид/таблица | `tr`, `apply_sort`, `_widget_is_alive`, `apply_quick_filter` | `create_main_layout` | `tabs_above_grid`, `_get_warning_banner`, `_ensure_shared_filter`, `apply_filters` | — | modules/grid/builder | VERY_HIGH |
| `_maybe_auto_set_page_size` | 31574–31609 | 36 | Автовыбор размера страницы | E. Грид/таблица | `log`, `_widget_is_alive` | `load_segments_to_grid` | `current_project`, `PAGE_AUTO_ALL_THRESHOLD`, `PAGE_FALLBACK_SIZE`, `log` | — | modules/grid/pagination | LOW |
| `_get_total_pages` | 31611–31618 | 8 | Число страниц | E. Грид/таблица | — | `_update_pagination_ui`, `go_to_next_page`, `go_to_last_page` | `current_project`, `grid_page_size` | — | modules/grid/pagination | LOW |
| `_update_pagination_ui` | 31620–31680 | 61 | UI пагинации | E. Грид/таблица | `_widget_is_alive`, `tr`, `_get_total_pages` | `_apply_pagination_to_grid`, `confirm_and_next_unconfirmed` | `_get_total_pages`, `grid_page_size`, `grid_current_page`, `current_project` | — | modules/grid/pagination | LOW |
| `_apply_pagination_to_grid` | 31682–31803 | 122 | Применение пагинации к гриду | E. Грид/таблица | `_resize_visible_rows`, `_update_pagination_ui`, `_start_background_populate`, `_populate_single_row` | `go_to_first_page`, `go_to_prev_page`, `go_to_next_page` | `current_project`, `_resize_visible_rows`, `_update_pagination_ui`, `_start_background_populate` | hasattr×4, string×4, duck-typed×4 | modules/grid/pagination | MEDIUM |
| `_start_background_populate` | 31825–31875 | 51 | Фоновая заливка грида | E. Грид/таблица | `_background_populate_step` | `_apply_pagination_to_grid` | `_background_populate_generation`, `BACKGROUND_POPULATE_INITIAL_DELAY_MS`, `current_project`, `_background_populate_step` | — | modules/grid/pagination | MEDIUM |
| `_background_populate_step` | 31877–31919 | 43 | Шаг фоновой заливки | E. Грид/таблица | `_populate_single_row`, `_background_populate_step` | `_start_background_populate` | `_background_populate_queue`, `current_project`, `BACKGROUND_POPULATE_BATCH_SIZE`, `BACKGROUND_POPULATE_BATCH_DELAY_MS` | singleShot×2 | modules/grid/pagination | MEDIUM |
| `go_to_first_page` | 31921–31927 | 7 | Навигация: первая страница | E. Грид/таблица | `_apply_pagination_to_grid` | `go_to_first_segment` | `grid_current_page`, `_apply_pagination_to_grid` | hasattr×2, string×2, duck-typed×2, signal:clicked×1 | modules/grid/pagination | LOW |
| `go_to_prev_page` | 31929–31935 | 7 | Навигация: назад | E. Грид/таблица | `_apply_pagination_to_grid` | динамич. вход | `grid_current_page`, `_apply_pagination_to_grid` | shortcut-registry×1, hasattr×1, signal:clicked×1, string×1 | modules/grid/pagination | LOW |
| `go_to_next_page` | 31937–31944 | 8 | Навигация: вперёд | E. Грид/таблица | `_get_total_pages`, `_apply_pagination_to_grid` | динамич. вход | `_get_total_pages`, `grid_current_page`, `_apply_pagination_to_grid` | shortcut-registry×1, hasattr×1, signal:clicked×1, string×1 | modules/grid/pagination | LOW |
| `select_range_page_up` | 31946–31978 | 33 | Выделение на страницу вверх | E. Грид/таблица | `_select_range_between` | динамич. вход | `_select_range_between`, `_selection_anchor_row`, `table`, `current_project` | shortcut-registry×1 | modules/grid/pagination | LOW |
| `select_range_page_down` | 31980–32013 | 34 | Выделение на страницу вниз | E. Грид/таблица | `_select_range_between` | динамич. вход | `_select_range_between`, `_selection_anchor_row`, `table`, `current_project` | shortcut-registry×1 | modules/grid/pagination | LOW |
| `_select_range_between` | 32015–32034 | 20 | Выделение диапазона | E. Грид/таблица | — | `select_range_page_up`, `select_range_page_down` | `table` | — | modules/grid/pagination | LOW |
| `_clear_selection_anchor` | 32036–32039 | 4 | Zero-ref сброс якоря выделения | Legacy/мёртвое | — | **dead-candidate** | `_selection_anchor_row` | — | PROBABLY_DEAD | LOW |
| `go_to_last_page` | 32041–32048 | 8 | Навигация: последняя | E. Грид/таблица | `_get_total_pages`, `_apply_pagination_to_grid` | `go_to_last_segment` | `_get_total_pages`, `grid_current_page`, `_apply_pagination_to_grid` | hasattr×2, string×2, duck-typed×2, signal:clicked×1 | modules/grid/pagination | LOW |
| `go_to_page` | 32050–32069 | 20 | Переход на страницу N | E. Грид/таблица | `_get_total_pages`, `_widget_is_alive`, `_apply_pagination_to_grid` | `_navigate_to_segment_in_grid`, `show_goto_dialog`, `_navigate_to_segment_by_id` | `_get_total_pages`, `grid_current_page`, `_widget_is_alive`, `page_number_input` | hasattr×1, signal:returnPressed×1, string×1, duck-typed×1 | modules/grid/pagination | LOW |
| `on_page_size_changed` | 32071–32093 | 23 | Смена размера страницы | E. Грид/таблица | `_apply_pagination_to_grid` | динамич. вход | `grid_page_size`, `_apply_pagination_to_grid`, `grid_current_page` | signal:currentTextChanged×2, hasattr×1, string×1, duck-typed×1 | modules/grid/pagination | LOW |
| `_widget_is_alive` | 32095–32102 | 8 | Проверка живости грида | E. Грид/таблица | — | `create_grid_view_widget`, `create_grid_view_widget_for_home`, `_maybe_auto_set_page_size` | — | — | modules/grid/helpers | LOW |
| `_switch_main_tab` | 32123–32134 | 12 | Переключение главной вкладки | Управление вкладками | — | `create_menus`, `_go_to_settings_tab` | `main_tabs` | duck-typed×6, menu×5, hasattr×3, string×3 | SupervertalerQt (ядро) | LOW |
| `_switch_settings_subtab` | 32136–32148 | 13 | Переключение сабтаба настроек | Управление вкладками | — | динамич. вход | `settings_tabs` | duck-typed×2, hasattr×1, string×1 | SupervertalerQt (ядро) | LOW |
| `_get_line_edit_text` | 32150–32156 | 7 | Чтение текста line-edit фильтра | E. Грид/таблица | `_widget_is_alive` | `apply_filters`, `filter_on_selected_text`, `_is_text_filter_active` | `_widget_is_alive` | — | modules/grid/helpers | LOW |
| `_ensure_shared_filter` | 32158–32171 | 14 | Ленивый общий фильтр | E. Грид/таблица | `_widget_is_alive` | `create_grid_view_widget`, `create_grid_view_widget_for_home`, `_ensure_primary_filters_ready` | `_widget_is_alive` | — | modules/grid/filters | LOW |
| `_ensure_primary_filters_ready` | 32173–32186 | 14 | Готовность основных фильтров | E. Грид/таблица | `_ensure_shared_filter` | `search_segments` | `_ensure_shared_filter`, `apply_filters`, `source_filter`, `target_filter` | — | modules/grid/filters | LOW |
| `_build_warning_banner` | 32188–32218 | 31 | Баннер предупреждений | AF. UI-хелперы | `tr` | `_get_warning_banner` | `_go_to_settings_tab`, `tr` | — | SupervertalerQt (ядро) | LOW |
| `_get_warning_banner` | 32220–32228 | 9 | Баннер предупреждений грида | E. Грид/таблица | `_widget_is_alive`, `_build_warning_banner` | `create_grid_view_widget`, `create_grid_view_widget_for_home` | `warning_banners`, `_widget_is_alive`, `_build_warning_banner` | — | modules/grid/helpers | LOW |
| `create_translation_grid` | 32230–32390 | 161 | Создание таблицы перевода | E. Грид/таблица | `load_general_settings`, `log`, `_update_file_boundary_labels` | `create_grid_view_widget`, `create_grid_view_widget_for_home` | `status_column_before_target`, `table`, `default_font_family`, `default_font_size` | — | modules/grid/builder | MEDIUM |
| `add_precision_scroll_buttons` | 32395–32465 | 71 | Единственный вызов закомментирован (32393) | Legacy/мёртвое | `tr`, `precision_scroll`, `_table_resize_event_wrapper` | **dead-candidate** | `table`, `position_precision_scroll_buttons`, `_table_resize_event_wrapper`, `scroll_up_btn` | — | PROBABLY_DEAD | LOW |
| `_table_resize_event_wrapper` | 32467–32473 | 7 | Обёртка resize грида | E. Грид/таблица | `position_precision_scroll_buttons` | `add_precision_scroll_buttons` | `position_precision_scroll_buttons` | — | SupervertalerQt (ядро) | LOW |
| `precision_scroll` | 32475–32492 | 18 | Точный скролл | E. Грид/таблица | — | `add_precision_scroll_buttons` | `table` | signal:clicked×2 | SupervertalerQt (ядро) | LOW |
| `position_precision_scroll_buttons` | 32494–32522 | 29 | Позиционирование кнопок скролла | E. Грид/таблица | — | `_table_resize_event_wrapper` | `table`, `scroll_up_btn`, `scroll_down_btn` | singleShot×1 | SupervertalerQt (ядро) | LOW |
| `create_assistance_panel` | 32524–32684 | 161 | Zero-ref панель ассистента (заменена results_panels) | Legacy/мёртвое | `tr`, `load_general_settings`, `_dictation_shortcut_label` | **dead-candidate** | `load_general_settings`, `on_tab_status_combo_changed`, `on_tab_target_change`, `copy_source_to_tab_target` | — | PROBABLY_DEAD | LOW |
| `on_match_selected` | 32686–32690 | 5 | Zero-ref обработчик выбора матча | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `on_match_inserted` | 32692–32771 | 80 | Матч вставлен в сегмент (signal) | I. Перевод/подтверждение | `log`, `record_undo_state`, `reverse_invisible_replacements` | `_insert_compare_panel_current_match`, `_insert_compare_panel_mt_current`, `_insert_compare_panel_tm_target_current` | `current_project`, `table`, `log`, `reverse_invisible_replacements` | signal:match_inserted×1 | SupervertalerQt (ядро) | MEDIUM |
| `new_project` | 32777–33045 | 269 | Новый проект (269 строк) | C. Управление проектом | `tr`, `log`, `update_window_title`, `load_segments_to_grid` | динамич. вход | `source_language`, `target_language`, `update_window_title`, `load_segments_to_grid` | menu×1 | SupervertalerQt (ядро) | HIGH |
| `_setup_tray_icon` | 33060–33183 | 124 | Настройка tray-иконки | B. Жизненный цикл окна/Workbench | `_load_settings_section`, `windowIcon`, `tr`, `_tray_show_window` | динамич. вход | `_load_settings_section`, `_tray_show_window`, `_on_toggle_close_to_tray`, `_tray_close_to_tray_action` | duck-typed×1 | modules/tray_controller | MEDIUM |
| `_on_tray_activated` | 33185–33192 | 8 | Активация tray | B. Жизненный цикл окна/Workbench | `isVisible`, `hide`, `_tray_show_window` | динамич. вход | `isVisible`, `hide`, `_tray_show_window` | shortcut×1 | modules/tray_controller | LOW |
| `_tray_show_window` | 33194–33200 | 7 | Показ окна из tray | B. Жизненный цикл окна/Workbench | `show`, `setWindowState`, `raise_`, `activateWindow` | `_setup_tray_icon`, `_on_tray_activated` | `show`, `setWindowState`, `raise_`, `activateWindow` | menu×1 | modules/tray_controller | LOW |
| `_on_esc_quick_lookup_dismiss` | 33202–33333 | 132 | Esc: dismiss quick lookup | B. Жизненный цикл окна/Workbench | `hide`, `log`, `_dismiss_clipboard_summon` | `create_main_layout`, `keyPressEvent` | `main_tabs`, `_dismiss_clipboard_summon`, `hide`, `log` | shortcut×1 | SupervertalerQt (ядро) | MEDIUM |
| `keyPressEvent` | 33335–33364 | 30 | Qt keyPressEvent override | AE. События Qt/event filters | `_on_esc_quick_lookup_dismiss`, `log` | — (входа нет) | `main_tabs`, `_on_esc_quick_lookup_dismiss`, `log` | — | SupervertalerQt (ядро) | HIGH |
| `_dismiss_clipboard_summon` | 33366–33409 | 44 | Закрытие clipboard-summon окна | Буфер обмена | `log`, `hide`, `showMinimized` | `_on_esc_quick_lookup_dismiss` | `hide`, `showMinimized`, `log` | — | SupervertalerQt (ядро) | MEDIUM |
| `_on_toggle_close_to_tray` | 33411–33414 | 4 | Toggle close-to-tray | B. Жизненный цикл окна/Workbench | `_load_settings_section`, `_save_settings_section` | динамич. вход | `_load_settings_section`, `_save_settings_section` | signal:toggled×1 | modules/tray_controller | LOW |
| `_on_toggle_start_minimized` | 33416–33419 | 4 | Toggle start-minimized | B. Жизненный цикл окна/Workbench | `_load_settings_section`, `_save_settings_section` | динамич. вход | `_load_settings_section`, `_save_settings_section` | signal:toggled×1 | modules/tray_controller | LOW |
| `_on_toggle_autostart` | 33421–33445 | 25 | Toggle автозапуска | B. Жизненный цикл окна/Workbench | — | динамич. вход | `_tray_autostart_action`, `_tray_icon` | signal:toggled×1 | modules/tray_controller | LOW |
| `_tray_quit` | 33447–33451 | 5 | Выход через tray | B. Жизненный цикл окна/Workbench | `close` | динамич. вход | `close`, `_really_quit` | menu×2 | modules/tray_controller | LOW |
| `closeEvent @33453` | 33453–33519 | 67 | Qt closeEvent (ЗАТЕНЁН вторым определением 62932!) | AE. События Qt/event filters | `_load_settings_section`, `hide`, `_save_settings_section` | динамич. вход | `_load_settings_section`, `hide`, `_save_settings_section`, `lookup_tab` | duck-typed×1 | SupervertalerQt (ядро) | VERY_HIGH |
| `open_project` | 33521–33530 | 10 | Открыть проект (меню) | C. Управление проектом | `load_project` | динамич. вход | `load_project` | menu×1 | SupervertalerQt (ядро) | LOW |
| `load_project` | 33532–34078 | 547 | Загрузка проекта (547 строк) | C. Управление проектом | `log`, `tr`, `_reset_comment_ui_state`, `load_segments_to_grid` | `open_project`, `_load_recent_project_with_resize`, `update_recent_projects_display` | `tr`, `_reset_comment_ui_state`, `current_project`, `load_segments_to_grid` | signal:clicked×1 | SupervertalerQt (ядро) | VERY_HIGH |
| `_load_synonyms_bulk` | 34080–34139 | 60 | Массовая загрузка синонимов | L. Termbase/глоссарий | `log` | `_build_termbase_index` | `db_manager`, `log` | — | modules/termbase_service | LOW |
| `_finalise_import_with_indexes` | 34141–34176 | 36 | Финализация импорта: индексы/кэши | M. Импорт | `log`, `_start_termbase_batch_worker`, `_refresh_segment_comments_list`, `_refresh_proofreading_comments_list` | `import_simple_txt`, `_import_multifile_project`, `import_memoq_bilingual` | `_start_termbase_batch_worker`, `current_project`, `_refresh_segment_comments_list`, `_refresh_proofreading_comments_list` | — | modules/import_controller | MEDIUM |
| `_build_termbase_index` | 34178–34461 | 284 | Построение индекса termbase (284 строки) | L. Termbase/глоссарий | `_convert_language_to_code`, `log`, `_load_synonyms_bulk`, `_snapshot_termbase_db_state` | `add_term_pair_to_termbase`, `_quick_add_term_with_priority`, `add_text_to_non_translatables` | `_load_synonyms_bulk`, `current_project`, `db_manager`, `_convert_language_to_code` | — | modules/termbase_service | HIGH |
| `_search_termbase_in_memory` | 34463–34612 | 150 | Поиск по termbase в памяти | L. Termbase/глоссарий | — | `show_term_insert_popup`, `show_term_picker_dialog`, `_termbase_batch_worker_run` | `termbase_index_lock`, `termbase_index` | — | modules/termbase_service | MEDIUM |
| `_start_termbase_batch_worker` | 34614–34648 | 35 | Запуск thread-worker индексации | W. Воркеры/фоновые задачи | `log`, `_build_termbase_index` | `_quick_add_term_with_priority`, `load_project`, `_finalise_import_with_indexes` | `_build_termbase_index`, `termbase_batch_worker_thread`, `log`, `current_project` | — | modules/workers/termbase | LOW |
| `_termbase_batch_worker_run` | 34650–34706 | 57 | Тело thread-worker индексации | W. Воркеры/фоновые задачи | `log`, `_search_termbase_in_memory` | динамич. вход | `termbase_cache`, `log`, `termbase_cache_lock`, `termbase_batch_stop_event` | thread×1 | modules/workers/termbase | MEDIUM |
| `_search_termbases_thread_safe` | 34708–34897 | 190 | Zero-ref потокобезопасный поиск termbase | Legacy/мёртвое | `_convert_language_to_code` | **dead-candidate** | `_convert_language_to_code` | — | PROBABLY_DEAD | LOW |
| `_trigger_idle_prefetch` | 34899–34945 | 47 | Триггер idle-префетча матчей | W. Воркеры/фоновые задачи | `_start_prefetch_worker`, `_apply_proactive_highlighting` | `_handle_target_text_debounced_by_id` | `current_project`, `translation_matches_cache_lock`, `_start_prefetch_worker`, `translation_matches_cache` | — | modules/workers/prefetch | LOW |
| `_start_prefetch_worker` | 34947–34972 | 26 | Запуск prefetch thread-worker | W. Воркеры/фоновые задачи | — | `load_project`, `_finalise_import_with_indexes`, `_trigger_idle_prefetch` | `prefetch_worker_thread`, `prefetch_stop_event`, `_prefetch_worker_run` | — | modules/workers/prefetch | LOW |
| `_prefetch_worker_run` | 34974–35082 | 109 | Тело prefetch thread-worker | W. Воркеры/фоновые задачи | `_fetch_all_matches_for_segment`, `log` | динамич. вход | `db_manager`, `current_project`, `translation_matches_cache_lock`, `_fetch_all_matches_for_segment` | thread×1 | modules/workers/prefetch | MEDIUM |
| `_fetch_all_matches_for_segment` | 35084–35253 | 170 | Все матчи сегмента (TM+termbase+MT) | W. Воркеры/фоновые задачи | `_convert_language_to_code`, `_deduplicate_termbase_matches`, `_search_termbase_in_memory` | `_prefetch_worker_run` | `enable_mt_matching`, `enable_llm_matching`, `current_project`, `_convert_language_to_code` | — | modules/workers/prefetch | HIGH |
| `stop_prefetch_worker` | 35255–35261 | 7 | Остановка prefetch worker | W. Воркеры/фоновые задачи | `log` | `close_project` | `prefetch_worker_thread`, `log`, `prefetch_stop_event` | — | modules/workers/prefetch | LOW |
| `stop_termbase_batch_worker` | 35263–35269 | 7 | Остановка termbase worker | W. Воркеры/фоновые задачи | `log` | `close_project` | `termbase_batch_worker_thread`, `log`, `termbase_batch_stop_event` | — | modules/workers/termbase | LOW |
| `save_segment_to_activated_tms` | 35271–35383 | 113 | Сохранение сегмента в активные TM | K. Память переводов (TM) | `log`, `reverse_invisible_replacements`, `_queue_tm_save_log` | `_handle_target_text_debounced_by_id`, `update_status_icon`, `_save_tab_target_to_tm` | `hide_outer_wrapping_tags`, `current_project`, `tm_metadata_mgr`, `reverse_invisible_replacements` | — | modules/tm_controller | MEDIUM |
| `invalidate_translation_cache` | 35385–35424 | 40 | Инвалидация кэша переводов | K. Память переводов (TM) | `log` | `_create_tm_list_tab`, `send_segments_to_tm_dialog` | `translation_matches_cache_lock`, `translation_matches_cache`, `table`, `log` | hasattr×1, string×1, duck-typed×1 | modules/tm_controller | LOW |
| `save_project` | 35426–35434 | 9 | Сохранить проект | C. Управление проектом | `save_project_as`, `save_project_to_file` | `closeEvent`, `close_project` | `current_project`, `project_file_path`, `save_project_as`, `save_project_to_file` | duck-typed×2, menu×1 | SupervertalerQt (ядро) | MEDIUM |
| `save_project_as` | 35436–35464 | 29 | Сохранить как | C. Управление проектом | `save_project_to_file`, `add_to_recent_projects`, `log` | `new_project`, `save_project` | `current_project`, `save_project_to_file`, `add_to_recent_projects`, `log` | menu×1 | SupervertalerQt (ядро) | MEDIUM |
| `save_project_to_file` | 35466–35637 | 172 | Запись .svproj (172 строки) | C. Управление проектом | `log`, `update_window_title`, `_maybe_make_versioned_backup` | `save_project`, `save_project_as`, `perform_auto_backup` | `spellcheck_enabled`, `current_project`, `log`, `prompt_manager_qt` | — | modules/project_service | HIGH |
| `_maybe_make_versioned_backup` | 35639–35675 | 37 | Версионный бэкап | AB. Персистентность (settings IO) | `log`, `load_general_settings` | `save_project_to_file` | `load_general_settings`, `log`, `_save_count`, `user_data_path` | — | modules/project_service | LOW |
| `restart_auto_backup_timer` | 35677–35702 | 26 | Таймер автобэкапа | AB. Персистентность (settings IO) | `log`, `load_general_settings` | `__init__`, `_live_save_backup_settings`, `_save_general_settings_from_ui` | `auto_backup_timer`, `load_general_settings`, `perform_auto_backup`, `log` | — | modules/project_service | LOW |
| `perform_auto_backup` | 35704–35757 | 54 | Автобэкап (таймер) | AB. Персистентность (settings IO) | `log`, `save_project_to_file` | динамич. вход | `current_project`, `project_file_path`, `save_project_to_file`, `log` | timer×1 | modules/project_service | LOW |
| `close_project` | 35759–35816 | 58 | Закрытие проекта | C. Управление проектом | `stop_termbase_batch_worker`, `stop_prefetch_worker`, `clear_grid`, `_reset_comment_ui_state` | динамич. вход | `project_modified`, `current_project`, `stop_termbase_batch_worker`, `stop_prefetch_worker` | menu×1 | SupervertalerQt (ядро) | MEDIUM |
| `update_recent_menu` | 35818–35852 | 35 | Меню недавних проектов | C. Управление проектом | `load_recent_projects`, `_load_recent_project_with_resize` | `create_menus`, `add_to_recent_projects`, `_remove_from_recent_projects` | `load_recent_projects`, `recent_menu`, `clear_recent_projects`, `MAX_RECENT_PROJECTS` | — | SupervertalerQt (ядро) | LOW |
| `_load_recent_project_with_resize` | 35854–35859 | 6 | Загрузка недавнего проекта | C. Управление проектом | `load_project` | `update_recent_menu` | `load_project`, `auto_resize_rows` | menu×1 | SupervertalerQt (ядро) | LOW |
| `add_to_recent_projects` | 35861–35911 | 51 | Добавить в недавние | C. Управление проектом | `load_recent_projects`, `save_recent_projects`, `update_recent_menu`, `update_recent_projects_display` | `load_project`, `save_project_as` | `load_recent_projects`, `current_project`, `save_recent_projects`, `update_recent_menu` | — | modules/project_service | LOW |
| `_remove_from_recent_projects` | 35913–35927 | 15 | Удалить из недавних | C. Управление проектом | `load_recent_projects`, `save_recent_projects`, `update_recent_menu`, `update_recent_projects_display` | `load_project` | `load_recent_projects`, `save_recent_projects`, `update_recent_menu`, `update_recent_projects_display` | — | modules/project_service | LOW |
| `load_recent_projects` | 35929–35991 | 63 | Чтение списка недавних | AB. Персистентность (settings IO) | `log` | `update_recent_menu`, `add_to_recent_projects`, `_remove_from_recent_projects` | `recent_projects_file`, `log` | — | modules/project_service | LOW |
| `save_recent_projects` | 35993–36003 | 11 | Запись списка недавних | AB. Персистентность (settings IO) | `log` | `add_to_recent_projects`, `_remove_from_recent_projects`, `clear_recent_projects` | `user_data_path`, `recent_projects_file`, `log` | — | modules/project_service | LOW |
| `update_recent_projects_display` | 36005–36037 | 33 | Панель недавних на Home | C. Управление проектом | `load_recent_projects`, `tr`, `load_project` | `add_to_recent_projects`, `_remove_from_recent_projects`, `clear_recent_projects` | `load_recent_projects`, `recent_projects_layout`, `tr`, `load_project` | — | SupervertalerQt (ядро) | LOW |
| `clear_recent_projects` | 36039–36053 | 15 | Очистить недавние | C. Управление проектом | `save_recent_projects`, `update_recent_menu`, `log`, `update_recent_projects_display` | динамич. вход | `save_recent_projects`, `update_recent_menu`, `log`, `update_recent_projects_display` | menu×1 | SupervertalerQt (ядро) | LOW |
| `IMPORT_DOCUMENT_FORMATS` | 36075–36076 | 2 | Property: список форматов импорта | M. Импорт | — | — (входа нет) | `OKAPI_OTHER_FORMATS` | — | SupervertalerQt (ядро) | LOW |
| `import_document` | 36078–36204 | 127 | Универсальный импорт документа (меню) | M. Импорт | `tr`, `load_general_settings`, `get_effective_import_options`, `_build_import_options_widget` | динамич. вход | `_import_source_lang`, `_import_target_lang`, `load_general_settings`, `get_effective_import_options` | menu×1 | modules/import_controller | MEDIUM |
| `export_okapi_merge` | 36206–36259 | 54 | Okapi merge-экспорт (меню) | N. Экспорт | `_project_export_path`, `_try_okapi_merge_export`, `log` | `export_document` | `_project_export_path`, `_try_okapi_merge_export`, `current_project`, `log` | — | modules/export/docx_export | LOW |
| `_ensure_okapi_sidecar` | 36261–36487 | 227 | Запуск Okapi sidecar (227 строк) | O. Обработка документов | `log`, `tr` | `_quick_extract_sources`, `import_docx_from_path`, `_import_multifile_project` | `okapi_sidecar`, `log`, `tr` | — | modules/okapi_controller | MEDIUM |
| `import_docx_from_path` | 36489–36911 | 423 | Импорт DOCX (423 строки) | M. Импорт | `log`, `tr`, `load_segments_to_grid`, `initialize_tm_database` | `import_document` | `current_project`, `log`, `load_segments_to_grid`, `initialize_tm_database` | — | modules/import_controller | HIGH |
| `import_simple_txt` | 36917–37289 | 373 | Импорт простого TXT (373 строки) | M. Импорт | `log`, `tr`, `load_general_settings`, `initialize_tm_database` | динамич. вход | `load_general_settings`, `_check_reimport_same_file`, `save_general_settings`, `tr` | menu×1 | modules/import_controller | HIGH |
| `export_simple_txt` | 37291–37466 | 176 | Экспорт TXT | N. Экспорт | `tr`, `log`, `_project_export_path` | динамич. вход | `log`, `current_project`, `tr`, `_project_export_path` | menu×1 | modules/export_controller | MEDIUM |
| `export_for_ai` | 37468–37747 | 280 | Zero-ref экспорт для AI | Legacy/мёртвое | `tr`, `log`, `_convert_language_to_code` | **dead-candidate** | `current_project`, `log`, `tr`, `_convert_language_to_code` | — | PROBABLY_DEAD | LOW |
| `import_folder_multifile` | 37753–37986 | 234 | Импорт папки (мультифайл) | M. Импорт | `tr`, `load_general_settings`, `get_effective_import_options`, `_build_import_options_widget` | динамич. вход | `load_general_settings`, `get_effective_import_options`, `_build_import_options_widget`, `_read_import_option_widgets` | menu×1 | modules/import_controller | MEDIUM |
| `_import_multifile_project` | 37988–38296 | 309 | Мультифайловый импорт (309 строк) | M. Импорт | `log`, `get_effective_import_options`, `initialize_tm_database`, `_clear_caches_after_import` | `import_folder_multifile` | `log`, `get_effective_import_options`, `current_project`, `initialize_tm_database` | — | modules/import_controller | HIGH |
| `relocate_source_folder` | 38298–38427 | 130 | Перенос папки исходников | C. Управление проектом | `log` | динамич. вход | `current_project`, `log`, `current_document_path` | menu×1 | modules/project_service | LOW |
| `export_folder_multifile` | 38429–38614 | 186 | Экспорт папки (мультифайл) | N. Экспорт | `tr`, `_export_multifile_to_folder` | динамич. вход | `current_project`, `_export_multifile_to_folder`, `tr` | menu×1 | modules/export_controller | MEDIUM |
| `_export_multifile_to_folder` | 38616–38743 | 128 | Мультифайловый экспорт | N. Экспорт | `log`, `_show_export_word_count_warning`, `tr`, `_export_file_as_txt` | `export_folder_multifile` | `current_project`, `log`, `_show_export_word_count_warning`, `tr` | — | modules/export_controller | MEDIUM |
| `_export_file_as_txt` | 38745–38771 | 27 | Экспорт файла как TXT | N. Экспорт | — | `_export_multifile_to_folder` | — | — | modules/export_controller | LOW |
| `_export_file_as_docx` | 38773–38952 | 180 | Экспорт файла как DOCX | N. Экспорт | `log` | `_export_multifile_to_folder` | `okapi_sidecar`, `log`, `current_project` | — | modules/export_controller | MEDIUM |
| `_export_file_as_bilingual` | 38954–39045 | 92 | Экспорт bilingual-файла | N. Экспорт | — | `_export_multifile_to_folder` | — | — | modules/export_controller | LOW |
| `_interpret_memoq_status` | 39047–39052 | 6 | Интерпретация статуса memoQ | Форматы CAT (memoQ/Trados/SDL/…) | — | `import_memoq_bilingual`, `import_memoq_rtf` | — | — | modules/statuses (переисп.) | LOW |
| `import_memoq_bilingual` | 39054–39417 | 364 | Импорт memoQ bilingual DOCX (364 строки) | Форматы CAT (memoQ/Trados/SDL/…) | `tr`, `log`, `_lang_from_column_header`, `_check_reimport_same_file` | динамич. вход | `log`, `_check_reimport_same_file`, `memoq_smart_formatting`, `tr` | menu×1 | modules/import_controller | HIGH |
| `import_memoq_rtf` | 39419–39688 | 270 | Импорт memoQ RTF (270 строк) | Форматы CAT (memoQ/Trados/SDL/…) | `tr`, `log`, `_check_reimport_same_file`, `_apply_reimport_settings` | динамич. вход | `log`, `_check_reimport_same_file`, `memoq_smart_formatting`, `tr` | menu×1 | modules/import_controller | MEDIUM |
| `export_memoq_bilingual` | 39690–39903 | 214 | Экспорт memoQ bilingual (214 строки) | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_apply_formatting_to_cell` | динамич. вход | `memoq_source_file`, `current_project`, `log`, `_apply_formatting_to_cell` | menu×1 | modules/export_controller | MEDIUM |
| `_apply_formatting_to_cell` | 39905–40067 | 163 | Форматирование ячейки memoQ RTF | Форматы CAT (memoQ/Trados/SDL/…) | — | `export_memoq_bilingual` | — | — | modules/export_controller | MEDIUM |
| `import_memoq_xliff` | 40073–40239 | 167 | Импорт memoQ XLIFF | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_is_known_language`, `_normalize_language_code`, `_check_reimport_same_file` | динамич. вход | `_check_reimport_same_file`, `_normalize_language_code`, `_apply_reimport_settings`, `current_project` | menu×1 | modules/import_controller | MEDIUM |
| `_normalize_language_code` | 40241–40247 | 7 | Нормализация кода языка | Прочие утилиты | — | `create_termbases_tab`, `import_memoq_xliff`, `import_po_file` | — | duck-typed×2, hasattr×1, string×1 | modules/language_codes (переисп.) | LOW |
| `_is_known_language` | 40250–40257 | 8 | Проверка известного языка (static) | Прочие утилиты | — | `import_memoq_xliff` | — | — | modules/language_codes (переисп.) | LOW |
| `_lang_from_column_header` | 40260–40298 | 39 | Язык из заголовка колонки (static) | Форматы CAT (memoQ/Trados/SDL/…) | — | `import_memoq_bilingual` | — | — | modules/import_controller | LOW |
| `_confirm_language_pair` | 40300–40344 | 45 | Подтверждение языковой пары | M. Импорт | `tr` | `import_memoq_bilingual`, `import_memoq_xliff` | `tr` | — | modules/import_controller | LOW |
| `export_memoq_rtf` | 40346–40461 | 116 | Экспорт memoQ RTF | Форматы CAT (memoQ/Trados/SDL/…) | `log` | динамич. вход | `memoq_rtf_source_file`, `current_project`, `memoq_rtf_handler`, `log` | menu×1 | modules/export_controller | LOW |
| `export_memoq_xliff` | 40463–40570 | 108 | Экспорт memoQ XLIFF | Форматы CAT (memoQ/Trados/SDL/…) | `log` | динамич. вход | `mqxliff_source_file`, `current_project`, `log`, `mqxliff_handler` | menu×1 | modules/export_controller | LOW |
| `import_po_file` | 40576–40697 | 122 | Импорт .po | Форматы CAT (memoQ/Trados/SDL/…) | `tr`, `log`, `_normalize_language_code`, `_check_reimport_same_file` | динамич. вход | `_check_reimport_same_file`, `tr`, `_normalize_language_code`, `_apply_reimport_settings` | menu×1 | modules/import_controller | MEDIUM |
| `export_po_file` | 40699–40798 | 100 | Экспорт .po | Форматы CAT (memoQ/Trados/SDL/…) | `tr`, `log` | динамич. вход | `po_source_file`, `current_project`, `tr`, `log` | menu×1 | modules/export_controller | MEDIUM |
| `import_cafetran_bilingual` | 40804–40952 | 149 | Импорт CafeTran DOCX | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_check_reimport_same_file`, `_apply_reimport_settings`, `update_window_title` | динамич. вход | `_check_reimport_same_file`, `_apply_reimport_settings`, `current_project`, `update_window_title` | menu×1 | modules/import_controller | MEDIUM |
| `import_trados_bilingual` | 40954–41221 | 268 | Импорт Trados review DOCX | Форматы CAT (memoQ/Trados/SDL/…) | `tr`, `log`, `_check_reimport_same_file`, `_apply_reimport_settings` | динамич. вход | `_check_reimport_same_file`, `tr`, `log`, `_apply_reimport_settings` | menu×1 | modules/import_controller | MEDIUM |
| `export_trados_bilingual` | 41223–41365 | 143 | Экспорт Trados review DOCX | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `reverse_invisible_replacements` | динамич. вход | `trados_handler`, `trados_source_file`, `current_project`, `log` | menu×1 | modules/export_controller | MEDIUM |
| `import_sdlppx_package` | 41367–41665 | 299 | Импорт SDLPPX-пакета (299 строк) | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_normalize_language_code`, `tr`, `_finalise_import_with_indexes` | динамич. вход | `_finalise_import_with_indexes`, `log`, `_normalize_language_code`, `current_project` | menu×1 | modules/import_controller | MEDIUM |
| `get_translator_name` | 41667–41673 | 7 | Имя переводчика | U. Настройки (UI) | `load_general_settings` | `add_comment_from_selection`, `open_tmx_editor_window`, `_comment_author_and_initials` | `load_general_settings` | hasattr×2, string×2, duck-typed×2 | SupervertalerQt (ядро) | LOW |
| `_build_sdlxliff_translations_dict` | 41675–41698 | 24 | Словарь переводов SDLXLIFF | Форматы CAT (memoQ/Trados/SDL/…) | — | `export_sdlrpx_package`, `export_standalone_sdlxliff` | `current_project` | — | modules/export_controller | LOW |
| `_build_sdlxliff_statuses_dict` | 41700–41724 | 25 | Словарь статусов SDLXLIFF | Форматы CAT (memoQ/Trados/SDL/…) | — | `export_sdlrpx_package`, `export_standalone_sdlxliff` | `current_project` | — | modules/export_controller | LOW |
| `_build_sdlxliff_comments_dict` | 41726–41736 | 11 | Словарь комментариев SDLXLIFF | Форматы CAT (memoQ/Trados/SDL/…) | — | `export_sdlrpx_package`, `export_standalone_sdlxliff` | `current_project` | — | modules/export_controller | LOW |
| `_confirm_include_comments` | 41738–41780 | 43 | Диалог включения комментариев | Форматы CAT (memoQ/Trados/SDL/…) | `log` | `export_sdlrpx_package`, `export_standalone_sdlxliff` | `log` | — | modules/export_controller | LOW |
| `export_sdlrpx_package` | 41782–41935 | 154 | Экспорт SDLRPX-пакета | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_sync_grid_targets_to_segments`, `_build_sdlxliff_translations_dict`, `_build_sdlxliff_comments_dict` | динамич. вход | `sdlppx_handler`, `current_project`, `_sync_grid_targets_to_segments`, `_build_sdlxliff_translations_dict` | menu×1 | modules/export_controller | MEDIUM |
| `_map_sdlxliff_segment` | 41939–42028 | 90 | Маппинг сегмента SDLXLIFF | Форматы CAT (memoQ/Trados/SDL/…) | — | `import_sdlppx_package`, `import_standalone_sdlxliff`, `import_sdlxliff_folder` | — | — | modules/import_controller | LOW |
| `import_standalone_sdlxliff` | 42030–42236 | 207 | Импорт standalone SDLXLIFF | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_normalize_language_code`, `_finalise_import_with_indexes`, `update_window_title` | динамич. вход | `log`, `_finalise_import_with_indexes`, `_normalize_language_code`, `current_project` | menu×1 | modules/import_controller | MEDIUM |
| `import_sdlxliff_folder` | 42238–42439 | 202 | Импорт папки SDLXLIFF | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_normalize_language_code`, `_finalise_import_with_indexes`, `update_window_title` | динамич. вход | `log`, `_finalise_import_with_indexes`, `_normalize_language_code`, `current_project` | menu×1 | modules/import_controller | MEDIUM |
| `export_standalone_sdlxliff` | 42441–42589 | 149 | Экспорт standalone SDLXLIFF | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_sync_grid_targets_to_segments`, `_build_sdlxliff_translations_dict`, `_build_sdlxliff_comments_dict` | динамич. вход | `current_project`, `_sync_grid_targets_to_segments`, `_build_sdlxliff_translations_dict`, `_build_sdlxliff_comments_dict` | menu×1 | modules/export_controller | MEDIUM |
| `import_phrase_bilingual` | 42591–42874 | 284 | Импорт Phrase bilingual (284 строки) | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `tr`, `update_window_title`, `initialize_tm_database` | динамич. вход | `log`, `current_project`, `update_window_title`, `initialize_tm_database` | menu×1 | modules/import_controller | MEDIUM |
| `export_phrase_bilingual` | 42876–43049 | 174 | Экспорт Phrase bilingual | Форматы CAT (memoQ/Trados/SDL/…) | `log` | динамич. вход | `phrase_handler`, `phrase_source_file`, `current_project`, `log` | menu×1 | modules/export_controller | MEDIUM |
| `import_dejavu_bilingual` | 43051–43214 | 164 | Импорт DéjàVu RTF | Форматы CAT (memoQ/Trados/SDL/…) | `tr`, `log`, `update_window_title`, `initialize_tm_database` | динамич. вход | `tr`, `current_project`, `update_window_title`, `initialize_tm_database` | menu×1 | modules/import_controller | MEDIUM |
| `export_dejavu_bilingual` | 43216–43367 | 152 | Экспорт DéjàVu RTF | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `_sync_grid_targets_to_segments` | динамич. вход | `dejavu_handler`, `dejavu_source_file`, `current_project`, `_sync_grid_targets_to_segments` | menu×1 | modules/export_controller | MEDIUM |
| `import_review_table` | 43369–43690 | 322 | Импорт review-таблицы (322 строки) | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `update_window_title`, `_finalise_import_with_indexes`, `load_segments_to_grid` | динамич. вход | `current_project`, `update_window_title`, `log`, `_finalise_import_with_indexes` | menu×1 | modules/import_controller | HIGH |
| `export_bilingual_markdown` | 43701–43878 | 178 | Экспорт bilingual Markdown | Форматы CAT (memoQ/Trados/SDL/…) | `tr`, `log`, `_sync_grid_targets_to_segments` | динамич. вход | `log`, `current_project`, `_sync_grid_targets_to_segments`, `tr` | menu×1 | modules/export_controller | MEDIUM |
| `import_bilingual_markdown` | 43880–44111 | 232 | Импорт bilingual Markdown | Форматы CAT (memoQ/Trados/SDL/…) | `log`, `tr`, `update_window_title`, `_sync_grid_targets_to_segments` | динамич. вход | `update_window_title`, `current_project`, `log`, `_sync_grid_targets_to_segments` | menu×1 | modules/import_controller | MEDIUM |
| `export_cafetran_bilingual` | 44113–44242 | 130 | Экспорт CafeTran DOCX | Форматы CAT (memoQ/Trados/SDL/…) | `log` | динамич. вход | `cafetran_source_file`, `current_project`, `cafetran_handler`, `log` | menu×1 | modules/export_controller | MEDIUM |
| `_compute_initial_visible_rows` | 44258–44277 | 20 | Начальные видимые строки | E. Грид/таблица | — | `load_segments_to_grid` | — | — | modules/grid/pagination | LOW |
| `_populate_single_row` | 44279–44733 | 455 | Заполнение строки грида (455 строк!) | E. Грид/таблица | `log`, `apply_invisible_replacements`, `_apply_row_color`, `reverse_invisible_replacements` | `_split_segment_grid_fast`, `_merge_segment_grid_fast`, `_apply_pagination_to_grid` | `hide_outer_wrapping_tags`, `theme_manager`, `default_font_family`, `apply_invisible_replacements` | — | modules/grid/render | VERY_HIGH |
| `load_segments_to_grid` | 44736–44906 | 171 | Загрузка сегментов в грид | E. Грид/таблица | `log`, `_maybe_auto_set_page_size`, `clear_grid`, `_compute_initial_visible_rows` | `_split_segment_at_row`, `_merge_segment_at_row`, `_delete_segments_at_rows` | `_suppress_target_change_handlers`, `log`, `current_project`, `_maybe_auto_set_page_size` | duck-typed×1 | modules/grid/render | VERY_HIGH |
| `_create_compare_panel` | 44912–44986 | 75 | Zero-ref панель сравнения (заменена match panel) | Legacy/мёртвое | `_create_compare_panel_box`, `_compare_panel_nav_mt`, `_compare_panel_nav_tm`, `tr` | **dead-candidate** | `theme_manager`, `compare_panel_segment_label`, `_create_compare_panel_box`, `tr` | — | PROBABLY_DEAD | LOW |
| `_create_match_panel` | 44988–45127 | 140 | Панель матчей (TM/MT) | E. Грид/таблица | `_create_compare_panel_box`, `tr`, `_match_panel_nav_tm`, `load_general_settings` | `create_grid_view_widget_for_home` | `theme_manager`, `termlens_widget_match`, `insert_termlens_text`, `_on_termlens_edit_entry` | — | modules/grid/match_panel | HIGH |
| `_toggle_match_panel_tm_layout` | 45129–45178 | 50 | Переключение layout TM-панели | E. Грид/таблица | `_load_general_settings_from_file`, `save_general_settings` | `create_menus`, `_match_panel_tm_context_menu` | `match_panel_tm_vertical`, `_tm_source_container`, `_tm_target_container`, `_tm_layout` | menu×2 | modules/grid/match_panel | LOW |
| `_match_panel_nav_tm` | 45180–45188 | 9 | Навигация по TM-матчам | E. Грид/таблица | `_update_match_panel_tm_display` | `_create_match_panel` | `match_panel_tm_matches`, `match_panel_tm_index`, `_update_match_panel_tm_display` | signal:clicked×2 | modules/grid/match_panel | LOW |
| `_update_match_panel_tm_display` | 45190–45289 | 100 | Отображение TM-матча | E. Грид/таблица | `_update_fuzzy_fixer_btn_state`, `reverse_invisible_replacements`, `apply_invisible_replacements`, `_set_compare_panel_text_with_diff` | `_match_panel_nav_tm`, `_match_panel_edit_tm_entry`, `_match_panel_delete_tm_entry` | `match_panel_tm_matches`, `match_panel_tm_index`, `match_panel_tm_nav_label`, `_update_fuzzy_fixer_btn_state` | — | modules/grid/match_panel | MEDIUM |
| `_match_panel_tm_context_menu` | 45291–45359 | 69 | Контекстное меню TM-панели | E. Грид/таблица | `tr`, `sender`, `_toggle_match_panel_tm_layout` | динамич. вход | `sender`, `match_panel_tm_matches`, `match_panel_tm_index`, `_match_panel_edit_tm_entry` | signal:customContextMenuRequested×2 | modules/grid/match_panel | LOW |
| `_get_match_panel_tm_fields` | 45361–45373 | 13 | Поля TM-панели | E. Грид/таблица | — | `_match_panel_edit_tm_entry`, `_match_panel_delete_tm_entry` | — | — | modules/grid/match_panel | LOW |
| `_match_panel_edit_tm_entry` | 45375–45450 | 76 | Правка TM-записи из панели | K. Память переводов (TM) | `tr`, `_get_match_panel_tm_fields`, `log`, `_update_match_panel_tm_display` | динамич. вход | `match_panel_tm_matches`, `match_panel_tm_index`, `_get_match_panel_tm_fields`, `tm_manager` | menu×1 | modules/grid/match_panel | MEDIUM |
| `_match_panel_delete_tm_entry` | 45452–45504 | 53 | Удаление TM-записи из панели | K. Память переводов (TM) | `_get_match_panel_tm_fields`, `log`, `_update_match_panel_tm_display` | динамич. вход | `match_panel_tm_matches`, `match_panel_tm_index`, `_get_match_panel_tm_fields`, `log` | menu×1 | modules/grid/match_panel | LOW |
| `_create_compare_panel_box` | 45506–45684 | 179 | Бокс панели сравнения | E. Грид/таблица | `tr`, `setCursor`, `setStyleSheet`, `setText` | `_create_compare_panel`, `_create_match_panel` | `fuzzy_fix_current_segment`, `theme_manager`, `compare_panel_text_edits`, `tr` | — | modules/grid/match_panel | MEDIUM |
| `_compare_panel_nav_mt` | 45686–45694 | 9 | Навигация MT-матчей (шорткаты) | E. Грид/таблица | `_update_compare_panel_mt_display` | `setup_global_shortcuts`, `_create_compare_panel`, `_compare_panel_nav_active_box` | `compare_panel_mt_matches`, `compare_panel_mt_index`, `_update_compare_panel_mt_display` | shortcut-registry×2, signal:clicked×2 | modules/grid/match_panel | LOW |
| `_compare_panel_nav_tm` | 45696–45704 | 9 | Навигация TM-матчей (шорткаты) | E. Грид/таблица | `_update_compare_panel_tm_display` | `setup_global_shortcuts`, `_create_compare_panel`, `_compare_panel_nav_active_box` | `compare_panel_tm_matches`, `compare_panel_tm_index`, `_update_compare_panel_tm_display` | shortcut-registry×2, signal:clicked×2 | modules/grid/match_panel | LOW |
| `_update_compare_panel_mt_display` | 45706–45743 | 38 | Отображение MT-матча | E. Грид/таблица | — | `_compare_panel_nav_mt`, `set_compare_panel_matches` | `compare_panel_mt_matches`, `compare_panel_mt_index`, `compare_panel_mt_nav_label`, `compare_panel_mt` | — | modules/grid/match_panel | LOW |
| `_update_compare_panel_tm_display` | 45745–45852 | 108 | Отображение TM-матча (diff) | E. Грид/таблица | `reverse_invisible_replacements`, `apply_invisible_replacements`, `_set_compare_panel_text_with_diff` | `_compare_panel_nav_tm`, `set_compare_panel_matches` | `compare_panel_tm_matches`, `compare_panel_tm_index`, `compare_panel_tm_nav_label`, `compare_panel_tm_target_label` | — | modules/grid/match_panel | MEDIUM |
| `set_compare_panel_matches` | 45854–45888 | 35 | Установка матчей в панель | E. Грид/таблица | `_update_match_panel_tm_display`, `_update_compare_panel_mt_display`, `_update_compare_panel_tm_display` | `update_compare_panel`, `on_cell_selected`, `_on_cell_selected_full` | `_update_match_panel_tm_display`, `compare_panel_current_source`, `_update_compare_panel_mt_display`, `_update_compare_panel_tm_display` | — | modules/grid/match_panel | MEDIUM |
| `update_compare_panel` | 45890–45917 | 28 | Zero-ref обновление панели сравнения | Legacy/мёртвое | `set_compare_panel_matches` | **dead-candidate** | `set_compare_panel_matches` | — | PROBABLY_DEAD | LOW |
| `_set_compare_panel_text_with_diff` | 45919–46008 | 90 | Текст с diff-подсветкой | E. Грид/таблица | — | `_update_match_panel_tm_display`, `_update_compare_panel_tm_display`, `_show_fuzzy_fix_diff` | `invisible_display_settings` | — | modules/grid/match_panel | LOW |
| `_refresh_compare_panel_theme` | 46010–46053 | 44 | Тема панели сравнения | V. Тема/UI-стили | — | `refresh_theme_colors` | `theme_manager`, `compare_panel_text_edits` | — | modules/grid/match_panel | LOW |
| `_create_preview_tab` | 46059–46162 | 104 | Вкладка предпросмотра | E. Грид/таблица | `tr`, `cursorRect`, `viewport`, `_on_preview_click` | `create_grid_view_widget_for_home`, `_open_preview_window` | `_open_preview_window`, `current_box_range`, `_on_preview_click`, `preview_widgets` | — | modules/preview_controller | MEDIUM |
| `_open_preview_window` | 46164–46209 | 46 | Окно предпросмотра | E. Грид/таблица | `_create_preview_tab`, `tr`, `_render_preview` | динамич. вход | `_create_preview_tab`, `tr`, `_render_preview`, `preview_widgets` | signal:clicked×1 | modules/preview_controller | LOW |
| `_toggle_preview_panel` | 46211–46233 | 23 | Toggle панели предпросмотра | E. Грид/таблица | — | динамич. вход | `_preview_tab_index`, `right_tabs`, `_pre_preview_tab_index` | shortcut-registry×1 | modules/preview_controller | LOW |
| `_on_preview_click` | 46235–46262 | 28 | Клик в предпросмотре -> навигация | E. Грид/таблица | `_navigate_to_segment_in_grid` | `_create_preview_tab` | `_navigate_to_segment_in_grid` | — | modules/preview_controller | LOW |
| `_navigate_to_segment_in_grid` | 46264–46307 | 44 | Навигация к сегменту в гриде | E. Грид/таблица | `log`, `go_to_page` | `_on_preview_click` | `current_project`, `table`, `log`, `main_tabs` | — | modules/grid/pagination | LOW |
| `_get_current_segment_id` | 46309–46325 | 17 | Текущий segment id | E. Грид/таблица | — | `_refresh_preview_on_show`, `_render_preview`, `highlight_preview_segment` | `current_project`, `table` | — | modules/grid/helpers | LOW |
| `_is_preview_tab_active` | 46327–46337 | 11 | Активен ли предпросмотр | E. Грид/таблица | — | `_on_cell_selected_full` | `_preview_tab_index`, `right_tabs` | — | modules/preview_controller | LOW |
| `_scroll_preview_to_segment` | 46339–46412 | 74 | Скролл предпросмотра к сегменту | E. Грид/таблица | `_center_cursor_in_preview` | `_refresh_preview_on_show`, `_on_cell_selected_full` | `preview_widgets`, `current_project`, `_center_cursor_in_preview` | — | modules/preview_controller | LOW |
| `_center_cursor_in_preview` | 46414–46436 | 23 | Центрирование курсора | E. Грид/таблица | — | `_scroll_preview_to_segment`, `_render_preview` | — | singleShot×1 | modules/preview_controller | LOW |
| `_schedule_preview_refresh` | 46438–46462 | 25 | Отложенный refresh предпросмотра | E. Грид/таблица | — | `_populate_single_row`, `_confirm_current_row_segment` | `_preview_tab_index`, `refresh_preview`, `right_tabs`, `_preview_refresh_timer` | — | modules/preview_controller | LOW |
| `refresh_preview` | 46464–46492 | 29 | Refresh предпросмотра (таймер) | E. Грид/таблица | `_preview_content_signature`, `_render_preview` | `_sync_after_structural`, `_apply_structural_history`, `load_segments_to_grid` | `preview_widgets`, `_preview_content_signature`, `current_project`, `_render_preview` | timer×1 | modules/preview_controller | LOW |
| `_preview_content_signature` | 46494–46506 | 13 | Сигнатура контента предпросмотра | E. Грид/таблица | — | `refresh_preview` | `current_project` | — | modules/preview_controller | LOW |
| `_refresh_preview_on_show` | 46508–46522 | 15 | Refresh при показе | E. Грид/таблица | `refresh_preview`, `_get_current_segment_id`, `_scroll_preview_to_segment`, `log` | динамич. вход | `refresh_preview`, `_get_current_segment_id`, `_scroll_preview_to_segment`, `log` | singleShot×1 | modules/preview_controller | LOW |
| `_render_preview` | 46524–46769 | 246 | Рендер предпросмотра (246 строк) | E. Грид/таблица | `_get_current_segment_id`, `_render_formatted_text`, `_center_cursor_in_preview` | `_open_preview_window`, `refresh_preview` | `current_project`, `_get_current_segment_id`, `_render_formatted_text`, `_center_cursor_in_preview` | — | modules/preview_controller | HIGH |
| `_render_formatted_text` | 46771–46866 | 96 | Рендер форматированного текста | E. Грид/таблица | — | `_render_preview` | — | — | modules/preview_controller | MEDIUM |
| `highlight_preview_segment` | 46868–46877 | 10 | Zero-ref подсветка сегмента в предпросмотре | Legacy/мёртвое | `_get_current_segment_id` | **dead-candidate** | `_get_current_segment_id`, `_highlighted_segment_id` | — | PROBABLY_DEAD | LOW |
| `_comment_indicator_bg` | 46887–46903 | 17 | Фон индикатора комментария | E. Грид/таблица | — | `_create_status_cell_widget` | `COMMENT_SC_BG`, `COMMENT_PC_BG` | — | modules/grid/render | LOW |
| `_create_status_cell_widget` | 46905–47054 | 150 | Виджет ячейки статуса | E. Грид/таблица | `_comment_indicator_bg`, `_status_cell_comment_menu`, `tr` | `_update_status_cell` | `_comment_indicator_bg`, `_status_cell_comment_menu`, `tr` | — | modules/grid/render | MEDIUM |
| `_status_cell_comment_menu` | 47056–47069 | 14 | Меню комментариев ячейки | E. Грид/таблица | `_open_comment_in_panel` | `_create_status_cell_widget` | `_open_comment_in_panel` | signal:customContextMenuRequested×1 | modules/grid/render | LOW |
| `_get_custom_tooltip` | 47071–47088 | 18 | Кастомный тултип | AE. События Qt/event filters | — | `eventFilter` | `_custom_tooltip` | — | SupervertalerQt (ядро) | LOW |
| `eventFilter` | 47090–47123 | 34 | Qt eventFilter главного окна | AE. События Qt/event filters | `_get_custom_tooltip` | — (входа нет) | `_get_custom_tooltip`, `_custom_tooltip` | — | SupervertalerQt (ядро) | HIGH |
| `_update_status_cell` | 47125–47137 | 13 | Обновление ячейки статуса | E. Грид/таблица | `_create_status_cell_widget` | `_apply_undo_redo_action`, `_populate_single_row`, `_refresh_segment_status` | `_create_status_cell_widget`, `table` | — | modules/grid/render | LOW |
| `_refresh_segment_status` | 47139–47181 | 43 | Обновление статуса сегмента | E. Грид/таблица | `_auto_resize_single_row`, `_update_status_cell` | `add_comment_from_selection`, `_refresh_segment_status_by_id`, `update_status_icon` | `current_project`, `list_tree`, `_auto_resize_single_row`, `_update_status_cell` | — | modules/grid/render | LOW |
| `_refresh_segment_status_by_id` | 47183–47189 | 7 | Обновление статуса по id | E. Грид/таблица | `_refresh_segment_status` | `_populate_single_row` | `current_project`, `_refresh_segment_status` | singleShot×1 | modules/grid/render | LOW |
| `_enforce_status_row_heights` | 47191–47194 | 4 | Высоты строк статуса | E. Грид/таблица | — | `load_segments_to_grid`, `auto_resize_rows` | — | — | modules/grid/render | LOW |
| `clear_grid` | 47198–47200 | 3 | Очистка грида | E. Грид/таблица | — | `close_project`, `load_segments_to_grid` | `table` | — | modules/grid/render | LOW |
| `set_termlens_position` | 47202–47241 | 40 | Позиция TermLens-dock | TermLens | `_sync_bottom_dock_menu`, `load_general_settings`, `save_general_settings` | `__init__`, `create_menus` | `left_vertical_splitter`, `bottom_tabs`, `_sync_bottom_dock_menu`, `tabs_above_grid` | menu×3 | SupervertalerQt (ядро) | MEDIUM |
| `_sync_bottom_dock_menu` | 47243–47259 | 17 | Меню нижнего дока | AF. UI-хелперы | — | `__init__`, `set_termlens_position` | `underdock_above_action`, `underdock_below_action`, `underdock_hide_action`, `bottom_tabs` | — | SupervertalerQt (ядро) | LOW |
| `_on_bottom_tab_changed` | 47261–47266 | 6 | Смена нижнего таба | AF. UI-хелперы | `_save_bottom_dock_active_tab` | динамич. вход | `_save_bottom_dock_active_tab` | signal:currentChanged×1 | SupervertalerQt (ядро) | LOW |
| `_save_bottom_dock_active_tab` | 47268–47278 | 11 | Сохранение активного нижнего таба | AB. Персистентность (settings IO) | `load_general_settings`, `save_general_settings` | `_on_bottom_tab_changed` | `load_general_settings`, `save_general_settings`, `bottom_tabs` | — | SupervertalerQt (ядро) | LOW |
| `_on_match_top_tab_changed` | 47280–47292 | 13 | Сохранение верхнего таба матчей | AB. Персистентность (settings IO) | `load_general_settings`, `save_general_settings` | динамич. вход | `load_general_settings`, `save_general_settings`, `match_top_tabs` | signal:currentChanged×1 | SupervertalerQt (ядро) | LOW |
| `_insert_quicktrans_translation` | 47294–47320 | 27 | Вставка перевода из QuickTrans | QuickTrans | `log`, `mark_segment_modified`, `reverse_invisible_replacements` | динамич. вход | `log`, `table`, `mark_segment_modified`, `segments` | signal:translation_selected×2 | SupervertalerQt (ядро) | MEDIUM |
| `_update_file_boundary_labels` | 47322–47376 | 55 | Метки границ файлов | E. Грид/таблица | — | `create_translation_grid`, `load_segments_to_grid`, `auto_resize_rows` | `current_project`, `table`, `_file_boundary_labels` | signal:valueChanged×1, signal:sectionResized×1 | modules/grid/render | LOW |
| `auto_resize_rows` | 47378–47395 | 18 | Авторазмер всех строк | E. Грид/таблица | `log`, `_enforce_status_row_heights`, `_update_file_boundary_labels`, `_auto_resize_single_row` | `_save_view_settings_from_ui_impl`, `load_project`, `import_docx_from_path` | `log`, `_enforce_status_row_heights`, `_update_file_boundary_labels`, `table` | menu×1, hasattr×1, singleShot×1, string×1 | modules/grid/render | LOW |
| `_auto_resize_single_row` | 47397–47459 | 63 | Авторазмер строки | E. Грид/таблица | — | `_split_segment_grid_fast`, `_merge_segment_grid_fast`, `_refresh_segment_status` | `current_project`, `table` | — | modules/grid/render | LOW |
| `_resize_visible_rows` | 47461–47468 | 8 | Авторазмер видимых строк (таймер) | E. Грид/таблица | `_auto_resize_single_row` | `_apply_pagination_to_grid` | `table`, `_auto_resize_single_row` | singleShot×2, timer×1 | modules/grid/render | LOW |
| `_on_column_resized` | 47470–47488 | 19 | Обработчик resize колонки | E. Грид/таблица | — | динамич. вход | `_resize_visible_rows`, `_column_resize_timer` | signal:sectionResized×1 | modules/grid/render | LOW |
| `apply_font_to_grid` | 47490–47550 | 61 | Применение шрифта к гриду | V. Тема/UI-стили | `_update_segment_column_width` | `_save_view_settings_from_ui_impl`, `load_segments_to_grid`, `set_font_family` | `default_font_family`, `default_font_size`, `table`, `_update_segment_column_width` | — | modules/grid/render | LOW |
| `_update_segment_column_width` | 47552–47578 | 27 | Ширина колонки сегмента | V. Тема/UI-стили | — | `apply_font_to_grid` | `default_font_family`, `default_font_size`, `table` | — | modules/grid/render | LOW |
| `set_font_family` | 47580–47585 | 6 | Смена семейства шрифта (меню) | V. Тема/UI-стили | `apply_font_to_grid`, `auto_resize_rows`, `log` | `create_menus` | `apply_font_to_grid`, `auto_resize_rows`, `log`, `default_font_family` | menu×1 | SupervertalerQt (ядро) | LOW |
| `increase_font_size` | 47587–47594 | 8 | Увеличить шрифт | V. Тема/UI-стили | `apply_font_to_grid`, `auto_resize_rows`, `log`, `save_current_font_sizes` | `zoom_in` | `apply_font_to_grid`, `auto_resize_rows`, `log`, `save_current_font_sizes` | — | SupervertalerQt (ядро) | LOW |
| `decrease_font_size` | 47596–47603 | 8 | Уменьшить шрифт | V. Тема/UI-стили | `apply_font_to_grid`, `auto_resize_rows`, `log`, `save_current_font_sizes` | `zoom_out` | `apply_font_to_grid`, `auto_resize_rows`, `log`, `save_current_font_sizes` | — | SupervertalerQt (ядро) | LOW |
| `refresh_grid_tag_colors` | 47605–47625 | 21 | Цвета тегов грида | V. Тема/UI-стили | — | `_save_view_settings_from_ui_impl` | `table` | — | modules/grid/render | LOW |
| `_apply_row_color` | 47627–47691 | 65 | Цвет строки | E. Грид/таблица | `load_general_settings` | `_populate_single_row`, `_update_row_selection_tint`, `apply_alternating_row_colors` | `_row_color_settings_cached`, `theme_manager`, `current_project`, `load_general_settings` | — | modules/grid/render | LOW |
| `_update_row_selection_tint` | 47701–47754 | 54 | Оттенок выделения строки | E. Грид/таблица | `_apply_row_color` | `apply_alternating_row_colors` | `SELECTION_TINT`, `table`, `_apply_row_color` | signal:currentCellChanged×1 | modules/grid/render | LOW |
| `apply_alternating_row_colors` | 47756–47783 | 28 | Чередование цветов строк | E. Грид/таблица | `log`, `_update_row_selection_tint`, `_apply_row_color` | `_save_view_settings_from_ui_impl`, `refresh_theme_colors` | `log`, `table`, `_update_row_selection_tint`, `_apply_row_color` | hasattr×1, string×1, duck-typed×1 | modules/grid/render | LOW |
| `on_font_changed` | 47785–47788 | 4 | Zero-ref обработчик смены шрифта | Legacy/мёртвое | `apply_font_to_grid`, `auto_resize_rows` | **dead-candidate** | `apply_font_to_grid`, `auto_resize_rows` | — | PROBABLY_DEAD | LOW |
| `zoom_in` | 47791–47793 | 3 | Зум грид-шрифта (меню) | V. Тема/UI-стили | `increase_font_size` | динамич. вход | `increase_font_size` | menu×1, hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | LOW |
| `zoom_out` | 47795–47797 | 3 | Анти-зум (меню) | V. Тема/UI-стили | `decrease_font_size` | динамич. вход | `decrease_font_size` | menu×1, hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | LOW |
| `results_pane_zoom_in` | 47799–47806 | 8 | Zero-ref зум панели результатов | Legacy/мёртвое | `save_current_font_sizes` | **dead-candidate** | `results_panels`, `save_current_font_sizes` | — | PROBABLY_DEAD | LOW |
| `results_pane_zoom_out` | 47808–47815 | 8 | Zero-ref анти-зум панели | Legacy/мёртвое | `save_current_font_sizes` | **dead-candidate** | `results_panels`, `save_current_font_sizes` | — | PROBABLY_DEAD | LOW |
| `results_pane_zoom_reset` | 47817–47824 | 8 | Zero-ref сброс зума панели | Legacy/мёртвое | `save_current_font_sizes` | **dead-candidate** | `results_panels`, `save_current_font_sizes` | — | PROBABLY_DEAD | LOW |
| `match_panel_zoom_in` | 47835–47840 | 6 | Зум панели матчей (меню) | E. Грид/таблица | `_apply_match_panel_font_size`, `save_current_font_sizes`, `log` | динамич. вход | `_apply_match_panel_font_size`, `save_current_font_sizes`, `log` | menu×1 | modules/grid/match_panel | LOW |
| `match_panel_zoom_out` | 47842–47847 | 6 | Анти-зум панели матчей | E. Грид/таблица | `_apply_match_panel_font_size`, `save_current_font_sizes`, `log` | динамич. вход | `_apply_match_panel_font_size`, `save_current_font_sizes`, `log` | menu×1 | modules/grid/match_panel | LOW |
| `match_panel_zoom_reset` | 47849–47854 | 6 | Сброс зума панели матчей | E. Грид/таблица | `_apply_match_panel_font_size`, `save_current_font_sizes`, `log` | динамич. вход | `_apply_match_panel_font_size`, `save_current_font_sizes`, `log` | menu×1 | modules/grid/match_panel | LOW |
| `_apply_match_panel_font_size` | 47856–47895 | 40 | Шрифт панели матчей | E. Грид/таблица | — | `_save_view_settings_from_ui_impl`, `load_project`, `match_panel_zoom_in` | `compare_panel_text_edits` | — | modules/grid/match_panel | LOW |
| `save_current_font_sizes` | 47897–47947 | 51 | Сохранение размеров шрифтов | AB. Персистентность (settings IO) | `load_general_settings`, `save_general_settings`, `log` | `increase_font_size`, `decrease_font_size`, `results_pane_zoom_in` | `default_font_family`, `default_font_size`, `load_general_settings`, `save_general_settings` | — | SupervertalerQt (ядро) | LOW |
| `get_effective_import_options` | 47949–47972 | 24 | Эффективные опции импорта | M. Импорт | `_load_general_settings_from_file` | `_quick_extract_sources`, `import_document`, `import_docx_from_path` | `_load_general_settings_from_file` | — | modules/import_controller | LOW |
| `_build_import_options_widget` | 47974–48041 | 68 | Виджет опций импорта | M. Импорт | — | `import_document`, `import_folder_multifile`, `_create_file_types_settings_tab` | — | — | modules/import_controller | LOW |
| `_read_import_option_widgets` | 48043–48054 | 12 | Чтение опций из виджета | M. Импорт | — | `import_document`, `import_folder_multifile`, `_create_file_types_settings_tab` | — | — | modules/import_controller | LOW |
| `_attach_docx_comments` | 48056–48118 | 63 | Импорт комментариев DOCX | M. Импорт | `log` | `import_docx_from_path`, `_import_multifile_project` | `log` | — | modules/import_controller | LOW |
| `_create_file_types_settings_tab` | 48120–48189 | 70 | Вкладка типов файлов | U. Настройки (UI) | `get_effective_import_options`, `_build_import_options_widget`, `_read_import_option_widgets`, `save_general_settings` | `create_settings_tab` | `get_effective_import_options`, `_build_import_options_widget`, `_read_import_option_widgets`, `save_general_settings` | — | modules/settings_tabs | LOW |
| `load_general_settings` | 48191–48287 | 97 | Загрузка общих настроек (fan-in 48!) | AB. Персистентность (settings IO) | `_load_general_settings_from_file`, `load_llm_settings` | `__init__`, `_show_first_run_welcome`, `_show_setup_wizard` | `auto_fill_100_matches`, `_load_general_settings_from_file`, `load_llm_settings`, `current_provider` | duck-typed×12, hasattr×6, string×6 | modules/settings_service | HIGH |
| `get_autocorrect_settings` | 48289–48300 | 12 | Настройки автокоррекции | U. Настройки (UI) | — | динамич. вход | `autocorrect_enabled`, `autocorrect_rule_overrides` | duck-typed×1 | modules/settings_service | LOW |
| `_get_settings_dir` | 48308–48310 | 3 | Каталог настроек | AB. Персистентность (settings IO) | — | `_get_unified_settings_path`, `_save_unified_settings`, `_migrate_settings_to_unified` | `user_data_path` | — | modules/settings_service | LOW |
| `_get_unified_settings_path` | 48312–48314 | 3 | Путь unified-настроек | AB. Персистентность (settings IO) | `_get_settings_dir` | `_create_general_settings_tab`, `_load_unified_settings`, `_init_usage_statistics` | `_get_settings_dir` | — | modules/settings_service | LOW |
| `_load_unified_settings` | 48316–48330 | 15 | Чтение unified-настроек | AB. Персистентность (settings IO) | `_get_unified_settings_path` | `_load_settings_section`, `_save_settings_section`, `save_clipboard_privacy_settings` | `_get_unified_settings_path` | duck-typed×1 | modules/settings_service | LOW |
| `_save_unified_settings` | 48332–48341 | 10 | Запись unified-настроек | AB. Персистентность (settings IO) | `_get_settings_dir`, `log` | `_save_settings_section`, `save_clipboard_privacy_settings`, `save_dictation_settings` | `_get_settings_dir`, `log` | duck-typed×1 | modules/settings_service | LOW |
| `_load_settings_section` | 48343–48345 | 3 | Чтение секции настроек (fan-in 26) | AB. Персистентность (settings IO) | `_load_unified_settings` | `_setup_progress_indicators`, `_set_confirmed_progress_basis`, `_verify_export_word_count` | `_load_unified_settings` | duck-typed×3 | modules/settings_service | LOW |
| `_save_settings_section` | 48347–48351 | 5 | Запись секции настроек | AB. Персистентность (settings IO) | `_load_unified_settings`, `_save_unified_settings` | `_set_confirmed_progress_basis`, `_create_general_settings_tab`, `_on_toggle_close_to_tray` | `_load_unified_settings`, `_save_unified_settings` | duck-typed×1 | modules/settings_service | LOW |
| `load_clipboard_privacy_settings` | 48359–48368 | 10 | Настройки приватности буфера | AB. Персистентность (settings IO) | `log`, `_load_settings_section` | `_create_clipboard_settings_tab` | `log`, `_load_settings_section` | duck-typed×1 | modules/settings_service | LOW |
| `save_clipboard_privacy_settings` | 48370–48391 | 22 | Запись приватности буфера | AB. Персистентность (settings IO) | `log`, `_load_unified_settings`, `_save_unified_settings` | `_create_clipboard_settings_tab` | `_load_unified_settings`, `_save_unified_settings`, `log` | — | modules/settings_service | LOW |
| `_migrate_settings_to_unified` | 48393–48483 | 91 | Миграция в unified-настройки | AB. Персистентность (settings IO) | `_get_settings_dir` | `__init__`, `_reinitialize_with_new_data_path` | `_get_settings_dir`, `user_data_path` | — | modules/settings_service | MEDIUM |
| `_migrate_to_workbench_layout` | 48485–48550 | 66 | Миграция layout Workbench | AB. Персистентность (settings IO) | — | `__init__`, `_reinitialize_with_new_data_path` | `user_data_path` | — | modules/settings_service | MEDIUM |
| `_load_general_settings_from_file` | 48552–48591 | 40 | Чтение настроек с диска | AB. Персистентность (settings IO) | `_load_settings_section` | `_toggle_match_panel_tm_layout`, `get_effective_import_options`, `_create_file_types_settings_tab` | `_load_settings_section` | — | modules/settings_service | LOW |
| `save_general_settings` | 48593–48598 | 6 | Сохранение общих настроек | AB. Персистентность (settings IO) | `_save_settings_section`, `log` | `_show_first_run_welcome`, `_show_setup_wizard`, `_save_mt_quick_lookup_settings` | `_save_settings_section`, `log` | duck-typed×4, hasattr×1, string×1 | modules/settings_service | LOW |
| `load_dictation_settings` | 48600–48615 | 16 | Настройки диктовки | AB. Персистентность (settings IO) | `_load_settings_section` | `_toggle_alwayson_listening`, `_on_alwayson_dictation`, `_get_voice_hotkey_listener` | `_load_settings_section` | duck-typed×2 | modules/settings_service | LOW |
| `save_dictation_settings` | 48617–48671 | 55 | Zero-ref сохранение диктовки | Legacy/мёртвое | `log`, `_load_unified_settings`, `_save_unified_settings` | **dead-candidate** | `_load_unified_settings`, `_save_unified_settings`, `log` | — | PROBABLY_DEAD | LOW |
| `_load_language_pair_from_disk` | 48673–48690 | 18 | Языковая пара с диска | AB. Персистентность (settings IO) | `_load_settings_section` | `__init__` | `_load_settings_section`, `source_language`, `target_language` | — | modules/settings_service | LOW |
| `load_voice_vocabulary_settings` | 48698–48736 | 39 | Словарь голосовых команд | AB. Персистентность (settings IO) | `_load_settings_section` | `_toggle_alwayson_listening`, `build_voice_initial_prompt`, `start_voice_dictation` | `_load_settings_section` | duck-typed×1 | modules/settings_service | LOW |
| `save_voice_vocabulary_settings` | 48738–48761 | 24 | Запись словаря команд | AB. Персистентность (settings IO) | `_save_settings_section` | динамич. вход | `_save_settings_section` | duck-typed×1 | modules/settings_service | LOW |
| `build_voice_initial_prompt` | 48763–48788 | 26 | Начальный промпт диктовки | VOICE | `load_voice_vocabulary_settings`, `_collect_voice_dictation_termbase_terms` | `_toggle_alwayson_listening`, `start_voice_dictation` | `load_voice_vocabulary_settings`, `_collect_voice_dictation_termbase_terms` | — | modules/voice_controller | LOW |
| `open_termbases_tab` | 48790–48810 | 21 | Открыть вкладку termbase | Управление вкладками | — | динамич. вход | `main_tabs` | duck-typed×1 | SupervertalerQt (ядро) | LOW |
| `_migrate_voice_dictation_default_off` | 48812–48843 | 32 | Миграция диктовки default-off | AB. Персистентность (settings IO) | `_load_settings_section`, `_save_settings_section`, `log` | `__init__` | `_load_settings_section`, `db_manager`, `_save_settings_section`, `log` | — | modules/settings_service | LOW |
| `_collect_voice_dictation_termbase_terms` | 48845–48895 | 51 | Термины для промпта диктовки | VOICE | — | `build_voice_initial_prompt` | `termbase_mgr` | — | modules/voice_controller | LOW |
| `load_language_settings` | 48897–48918 | 22 | Загрузка языковых настроек | AB. Персистентность (settings IO) | `log`, `_load_settings_section` | `__init__` | `_load_settings_section`, `spellcheck_enabled`, `spellcheck_manager`, `target_language` | — | modules/settings_service | LOW |
| `save_language_settings` | 48920–48930 | 11 | Сохранение языковых настроек | AB. Персистентность (settings IO) | `_load_unified_settings`, `_save_unified_settings`, `log` | `_create_language_pair_tab`, `_save_language_settings_from_ui` | `_load_unified_settings`, `_save_unified_settings`, `log` | — | modules/settings_service | LOW |
| `_save_language_settings_from_ui` | 48932–48942 | 11 | Сохранение языков из UI | AB. Персистентность (settings IO) | `save_language_settings`, `log` | `_create_language_pair_tab` | `save_language_settings`, `source_language`, `target_language`, `log` | signal:clicked×1 | modules/settings_tabs | LOW |
| `load_font_sizes_from_preferences` | 48944–49030 | 87 | Шрифты из настроек | V. Тема/UI-стили | `load_general_settings`, `_apply_match_panel_font_size`, `apply_font_to_grid`, `log` | `__init__` | `load_general_settings`, `results_panels`, `_apply_match_panel_font_size`, `table` | — | modules/settings_service | LOW |
| `_init_usage_statistics` | 49032–49054 | 23 | Инициализация usage-статистики | AB. Персистентность (settings IO) | `log`, `_get_unified_settings_path` | `__init__` | `_get_unified_settings_path`, `log` | — | modules/settings_service | LOW |
| `restore_last_project_if_enabled` | 49056–49085 | 30 | Восстановление последнего проекта | C. Управление проектом | `log`, `load_general_settings`, `load_recent_projects`, `load_project` | `__init__` | `load_general_settings`, `load_recent_projects`, `log`, `load_project` | — | SupervertalerQt (ядро) | MEDIUM |
| `get_status_icon` | 49088–49090 | 3 | Zero-ref иконка статуса | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `_make_source_changed_handler` | 49092–49153 | 62 | Фабрика обработчика source-правки | E. Грид/таблица | `reverse_invisible_replacements` | `_populate_single_row` | `reverse_invisible_replacements`, `hide_outer_wrapping_tags`, `current_project`, `project_modified` | — | modules/grid/render | MEDIUM |
| `_handle_target_text_debounced_by_id` | 49155–49195 | 41 | Debounced обработка target-правки | E. Грид/таблица | `log`, `update_window_title`, `_auto_resize_single_row`, `update_progress_stats` | `_populate_single_row` | `update_window_title`, `_auto_resize_single_row`, `update_progress_stats`, `_trigger_idle_prefetch` | timer×1 | modules/grid/render | MEDIUM |
| `update_status_icon` | 49197–49218 | 22 | Обновление статуса + undo + TM | E. Грид/таблица | `record_undo_state`, `_refresh_segment_status`, `save_segment_to_activated_tms`, `log` | `insert_term_translation`, `_check_auto_confirm_100_percent`, `_confirm_current_row_segment` | `record_undo_state`, `_refresh_segment_status`, `current_project`, `save_segment_to_activated_tms` | — | SupervertalerQt (ядро) | MEDIUM |
| `on_cell_changed` | 49220–49225 | 6 | cellChanged обработчик | E. Грид/таблица | — | динамич. вход | — | signal:itemChanged×1 | SupervertalerQt (ядро) | LOW |
| `on_cell_selected` | 49227–49309 | 83 | Роутер выбора ячейки (3 режима) | E. Грид/таблица | `log`, `_on_cell_selected_minimal`, `_cancel_pending_click_center`, `_on_cell_selected_glossary_only` | `add_text_to_non_translatables`, `on_selection_changed`, `test_cell_selection` | `debug_mode_enabled`, `_deferred_lookup_timer`, `_on_cell_selected_minimal`, `log` | duck-typed×10, hasattr×6, string×6, signal:currentCellChanged×1 | SupervertalerQt (ядро) | HIGH |
| `_center_row_in_viewport` | 49311–49323 | 13 | Центрирование строки | E. Грид/таблица | — | `_apply_click_center`, `_on_cell_selected_minimal`, `_on_cell_selected_full` | `table` | — | modules/grid/render | LOW |
| `_schedule_click_center` | 49342–49363 | 22 | Отложенное центрирование | E. Грид/таблица | `_fire_click_center` | динамич. вход | `_fire_click_center`, `_click_activation`, `_click_center_cancelled`, `_pending_center_timer` | duck-typed×4, hasattr×2, string×2 | modules/grid/render | LOW |
| `_fire_click_center` | 49365–49381 | 17 | Срабатывание центрирования | E. Грид/таблица | `_apply_click_center` | `_schedule_click_center` | `_apply_click_center`, `_pending_center_timer` | timer×1 | modules/grid/render | LOW |
| `_click_center_would_help` | 49383–49398 | 16 | Эвристика центрирования | E. Грид/таблица | — | `_apply_click_center` | `table` | — | modules/grid/render | LOW |
| `_apply_click_center` | 49400–49415 | 16 | Применение центрирования | E. Грид/таблица | `_click_center_would_help`, `_center_row_in_viewport` | `_fire_click_center` | `_click_center_would_help`, `_center_row_in_viewport`, `table`, `_click_activation` | singleShot×1 | modules/grid/render | LOW |
| `_cancel_pending_click_center` | 49417–49430 | 14 | Отмена центрирования | E. Грид/таблица | — | `on_cell_selected` | `_pending_center_timer`, `_click_activation`, `_click_center_cancelled` | duck-typed×4, hasattr×2, string×2 | modules/grid/render | LOW |
| `_on_cell_selected_minimal` | 49432–49461 | 30 | Минимальный режим выбора | E. Грид/таблица | `_center_row_in_viewport`, `log` | `on_cell_selected` | `debug_mode_enabled`, `table`, `theme_manager`, `_center_row_in_viewport` | — | modules/grid/render | LOW |
| `_on_cell_selected_glossary_only` | 49463–49550 | 88 | Только glossary-режим выбора | E. Грид/таблица | `highlight_source_with_termbase`, `find_nt_matches_in_source`, `_get_termbase_status_hint`, `_update_both_termlens` | `on_cell_selected` | `enable_termbase_grid_highlighting`, `current_project`, `debug_mode_enabled`, `table` | — | modules/grid/render | MEDIUM |
| `_pcs` | 49552–49574 | 23 | Лог-хелпер выбора (static) | E. Грид/таблица | `log` | `_on_cell_selected_full`, `_execute_mt_llm_lookup` | `log` | — | SupervertalerQt (ядро) | LOW |
| `_on_cell_selected_full` | 49576–50192 | 617 | Полный режим выбора (617 строк!) — архитектурный hotspot | E. Грид/таблица | `log`, `_pcs`, `find_nt_matches_in_source`, `set_compare_panel_matches` | `on_cell_selected` | `debug_mode_enabled`, `log`, `table`, `current_project` | timer×1 | SupervertalerQt (ядро) | VERY_HIGH |
| `on_selection_changed` | 50194–50215 | 22 | itemSelectionChanged обработчик | E. Грид/таблица | `on_cell_selected`, `log` | динамич. вход | `table`, `_last_selection_row`, `on_cell_selected`, `log` | signal:itemSelectionChanged×1 | SupervertalerQt (ядро) | LOW |
| `test_cell_selection` | 50217–50226 | 10 | Zero-ref тест выбора ячейки | Legacy/мёртвое | `log`, `on_cell_selected` | **dead-candidate** | `log`, `on_cell_selected`, `table` | — | PROBABLY_DEAD | LOW |
| `get_selected_segments_from_grid` | 50228–50242 | 15 | Выбранные сегменты | E. Грид/таблица | — | `_get_selected_or_filtered_segments`, `show_grid_context_menu`, `send_segments_to_tm_dialog` | `current_project`, `table` | duck-typed×6, hasattr×3, string×3 | modules/grid/helpers | LOW |
| `_get_selected_or_filtered_segments` | 50244–50277 | 34 | Выбранные или отфильтрованные | E. Грид/таблица | `get_selected_segments_from_grid` | `clear_selected_translations_from_menu`, `copy_source_to_target_bulk`, `copy_source_to_target_non_translatable_bulk` | `get_selected_segments_from_grid`, `table`, `current_project` | — | modules/grid/helpers | LOW |
| `_preview_combined_prompt_from_grid` | 50279–50486 | 208 | Предпросмотр комбинированного промпта | J. LLM/AI | `tr`, `get_ai_inject_glossary_terms` | динамич. вход | `current_project`, `table`, `get_ai_inject_glossary_terms`, `figure_context` | signal:clicked×1 | modules/llm_controller | MEDIUM |
| `add_segment_actions_to_menu` | 50489–50583 | 95 | Действия сегмента в меню | E. Грид/таблица | `_set_locked_on_selected`, `clear_selected_translations`, `change_status_selected`, `_autotag_row_from_context` | `show_grid_context_menu` | `confirm_selected_segments`, `autotag_segments_bulk`, `clear_selected_translations`, `change_status_selected` | hasattr×2, string×2, duck-typed×2 | modules/grid/menus | MEDIUM |
| `show_grid_context_menu` | 50585–50615 | 31 | Контекстное меню грида | E. Грид/таблица | `get_selected_segments_from_grid`, `add_segment_actions_to_menu` | динамич. вход | `get_selected_segments_from_grid`, `add_segment_actions_to_menu`, `table` | signal:customContextMenuRequested×1 | modules/grid/menus | LOW |
| `_autotag_row_from_context` | 50617–50628 | 12 | Автотег из контекста | E. Грид/таблица | `autotag_current_segment` | `add_segment_actions_to_menu` | `autotag_current_segment`, `table` | menu×1 | modules/grid/menus | LOW |
| `_set_locked_on_selected` | 50630–50642 | 13 | Блокировка сегментов | D. Операции с сегментами | `load_segments_to_grid`, `update_window_title`, `log` | `add_segment_actions_to_menu` | `load_segments_to_grid`, `update_window_title`, `log`, `project_modified` | menu×4 | modules/segments_controller | LOW |
| `clear_selected_translations` | 50644–50682 | 39 | Очистка переводов выбранных | D. Операции с сегментами | `log`, `update_window_title`, `record_undo_states_batch`, `load_segments_to_grid` | `add_segment_actions_to_menu`, `clear_selected_translations_from_menu` | `update_window_title`, `log`, `record_undo_states_batch`, `load_segments_to_grid` | menu×1 | modules/segments_controller | LOW |
| `clear_selected_translations_from_menu` | 50684–50692 | 9 | Очистка из меню | D. Операции с сегментами | `_get_selected_or_filtered_segments`, `clear_selected_translations` | динамич. вход | `current_project`, `table`, `_get_selected_or_filtered_segments`, `clear_selected_translations` | menu×1 | modules/segments_controller | LOW |
| `copy_source_to_target_bulk` | 50694–50756 | 63 | Копировать source->target (bulk) | D. Операции с сегментами | `log`, `_get_selected_or_filtered_segments`, `auto_resize_rows`, `update_progress_stats` | динамич. вход | `_get_selected_or_filtered_segments`, `auto_resize_rows`, `update_progress_stats`, `log` | menu×1 | modules/segments_controller | MEDIUM |
| `_is_non_translatable` | 50772–50776 | 5 | Проверка non-translatable (static) | D. Операции с сегментами | — | `copy_source_to_target_non_translatable_bulk` | — | — | modules/segments_controller | LOW |
| `_transform_non_translatable` | 50779–50786 | 8 | Трансформация non-translatable (static) | D. Операции с сегментами | — | `copy_source_to_target_non_translatable_bulk` | — | — | modules/segments_controller | LOW |
| `copy_source_to_target_non_translatable_bulk` | 50788–50888 | 101 | Копирование non-translatable | D. Операции с сегментами | `log`, `_get_selected_or_filtered_segments`, `auto_resize_rows`, `update_progress_stats` | динамич. вход | `_get_selected_or_filtered_segments`, `current_project`, `auto_resize_rows`, `update_progress_stats` | menu×1 | modules/segments_controller | MEDIUM |
| `pseudo_translate_bulk` | 50890–50899 | 10 | Псевдо-перевод (делегат) | M. Импорт | — | динамич. вход | `current_project` | menu×1 | SupervertalerQt (ядро) | LOW |
| `_copy_source_to_target_selected` | 50901–50948 | 48 | Zero-ref копирование выделенного | Legacy/мёртвое | `log`, `_find_row_for_segment`, `auto_resize_rows`, `update_progress_stats` | **dead-candidate** | `log`, `_find_row_for_segment`, `auto_resize_rows`, `update_progress_stats` | duck-typed×4, hasattr×2, string×2 | PROBABLY_DEAD | LOW |
| `show_clean_tags_dialog` | 50950–50968 | 19 | Диалог очистки тегов | F. Редактирование текста | `tr`, `clean_project_tags` | динамич. вход | `current_project`, `tr`, `clean_project_tags` | menu×1 | SupervertalerQt (ядро) | LOW |
| `clean_project_tags` | 50970–51056 | 87 | Очистка тегов проекта | F. Редактирование текста | `log`, `load_segments_to_grid`, `update_window_title` | `show_clean_tags_dialog` | `log`, `current_project`, `load_segments_to_grid`, `update_window_title` | — | SupervertalerQt (ядро) | MEDIUM |
| `show_proofread_dialog` | 51062–51242 | 181 | Диалог proofreading | Y. Proofreading | `tr`, `load_llm_settings`, `_run_proofreading` | динамич. вход | `current_project`, `load_llm_settings`, `prompt_manager_qt`, `_run_proofreading` | menu×1 | modules/proofread_controller | MEDIUM |
| `_run_proofreading` | 51244–51379 | 136 | Запуск ProofreadWorker | Y. Proofreading | `tr`, `log`, `load_api_keys`, `_get_active_custom_profile` | `show_proofread_dialog` | `load_api_keys`, `tr`, `_get_active_custom_profile`, `log` | — | modules/proofread_controller | MEDIUM |
| `show_proofreading_results_dialog` | 51381–51485 | 105 | Zero-ref диалог результатов proofread | Legacy/мёртвое | `tr`, `jump_to_segment` | **dead-candidate** | `current_project`, `tr`, `jump_to_segment` | — | PROBABLY_DEAD | LOW |
| `send_segments_to_tm_dialog` | 51487–51845 | 359 | Отправка сегментов в TM (359 строк) | K. Память переводов (TM) | `tr`, `log`, `reverse_invisible_replacements`, `get_selected_segments_from_grid` | динамич. вход | `hide_outer_wrapping_tags`, `log`, `current_project`, `tm_metadata_mgr` | menu×1 | modules/tm_controller | HIGH |
| `_restore_active_prompt` | 51847–51887 | 41 | Zero-ref восстановление активного промпта | Legacy/мёртвое | `log` | **dead-candidate** | `prompt_manager_qt`, `log` | — | PROBABLY_DEAD | LOW |
| `_restore_active_style_guide` | 51889–51904 | 16 | Zero-ref восстановление style guide | Legacy/мёртвое | `log` | **dead-candidate** | `log`, `prompt_manager_qt` | — | PROBABLY_DEAD | LOW |
| `_schedule_delayed_lookup` | 51906–51937 | 32 | Zero-ref отложенный lookup (legacy-путь) | Legacy/мёртвое | `log`, `load_general_settings`, `_perform_delayed_lookup` | **dead-candidate** | `lookup_timer`, `log`, `load_general_settings`, `enable_tm_matching` | — | PROBABLY_DEAD | MEDIUM |
| `_perform_delayed_lookup` | 51939–52239 | 301 | Достижим только из мёртвого _schedule_delayed_lookup | Legacy/мёртвое | `log`, `_convert_language_to_code`, `search_and_display_tm_matches`, `_fetch_llm_translation_async` | `_schedule_delayed_lookup`, **dead-candidate** | `log`, `current_lookup_segment_id`, `enable_tm_matching`, `table` | timer×1 | PROBABLY_DEAD | MEDIUM |
| `on_cell_clicked` | 52241–52258 | 18 | cellClicked обработчик | E. Грид/таблица | `log` | динамич. вход | `log`, `current_project`, `_selection_anchor_row` | signal:itemClicked×1 | SupervertalerQt (ядро) | LOW |
| `on_cell_double_clicked` | 52260–52288 | 29 | cellDoubleClicked обработчик | E. Грид/таблица | `log` | динамич. вход | `log`, `table` | signal:cellDoubleClicked×1 | SupervertalerQt (ядро) | LOW |
| `initialize_tm_database` | 52294–52315 | 22 | Инициализация TM-базы | K. Память переводов (TM) | `log` | `_import_tmx_as_tm`, `_attach_sdltm_as_tm`, `new_project` | `current_project`, `tm_database`, `lookup_tab`, `log` | — | modules/tm_controller | MEDIUM |
| `_initialize_spellcheck_for_target_language` | 52317–52329 | 13 | Спеллчек по языку | AB. Персистентность (settings IO) | `log` | `import_docx_from_path`, `import_simple_txt`, `import_memoq_bilingual` | `spellcheck_manager`, `log` | — | SupervertalerQt (ядро) | LOW |
| `_check_reimport_same_file` | 52331–52392 | 62 | Проверка реимпорта того же файла | M. Импорт | `tr`, `log` | `import_simple_txt`, `import_memoq_bilingual`, `import_memoq_rtf` | `current_project`, `tr`, `log` | — | modules/import_controller | LOW |
| `_apply_reimport_settings` | 52394–52409 | 16 | Применение настроек реимпорта | M. Импорт | `log` | `import_simple_txt`, `import_memoq_bilingual`, `import_memoq_rtf` | `log` | — | modules/import_controller | LOW |
| `_clear_caches_after_import` | 52411–52415 | 5 | Очистка кэшей после импорта | M. Импорт | — | `import_simple_txt`, `_import_multifile_project`, `import_memoq_bilingual` | `translation_matches_cache_lock`, `termbase_cache`, `translation_matches_cache` | — | modules/import_controller | LOW |
| `_deactivate_all_resources_for_new_project` | 52417–52456 | 40 | Деактивация ресурсов проекта | M. Импорт | `tm_tab_refresh_callback`, `termbase_tab_refresh_callback` | `import_docx_from_path`, `import_simple_txt`, `_import_multifile_project` | `current_project`, `tm_metadata_mgr`, `termbase_mgr`, `tm_tab_refresh_callback` | — | modules/import_controller | MEDIUM |
| `search_and_display_tm_matches` | 52458–52789 | 332 | Достижим только из мёртвого _perform_delayed_lookup (332 строки) | Legacy/мёртвое | `log`, `initialize_tm_database`, `create_diff_html`, `record_undo_state` | `_perform_delayed_lookup`, **dead-candidate** | `hide_outer_wrapping_tags`, `log`, `current_project`, `tm_database` | — | PROBABLY_DEAD | MEDIUM |
| `create_diff_html` | 52791–52827 | 37 | Вызывается только из мёртвого search_and_display_tm_matches | Legacy/мёртвое | — | `search_and_display_tm_matches`, **dead-candidate** | — | — | PROBABLY_DEAD | LOW |
| `get_termbase_code_map` | 52833–52839 | 7 | Карта кодов termbase | L. Termbase/глоссарий | `_load_settings_section` | `_perform_delayed_lookup`, `get_termbase_code` | `_load_settings_section` | — | modules/termbase_service | LOW |
| `save_termbase_code_map` | 52841–52848 | 8 | Zero-ref сохранение карты кодов | Legacy/мёртвое | `_load_unified_settings`, `_save_unified_settings`, `log` | **dead-candidate** | `_load_unified_settings`, `_save_unified_settings`, `log` | — | PROBABLY_DEAD | LOW |
| `get_termbase_code` | 52850–52908 | 59 | Код termbase | L. Termbase/глоссарий | `get_termbase_code_map`, `log` | `_perform_delayed_lookup` | `get_termbase_code_map`, `termbase_mgr`, `db_manager`, `log` | — | modules/termbase_service | LOW |
| `_convert_language_to_code` | 52910–52926 | 17 | Конвертация языка в код | Прочие утилиты | — | `_get_termbase_status_hint`, `_orient_term_for_termbase`, `add_text_to_non_translatables` | — | — | modules/language_codes (переисп.) | LOW |
| `find_termbase_matches_in_source` | 52928–53131 | 204 | Поиск терминов в source | L. Termbase/глоссарий | `log`, `_deduplicate_termbase_matches`, `_convert_language_to_code`, `reverse_invisible_replacements` | `_update_termlens_for_segment`, `_refresh_termbase_display_for_current_segment`, `_quick_add_term_with_priority` | `db_manager`, `reverse_invisible_replacements`, `termbase_index_lock`, `current_project` | string×1, duck-typed×1 | modules/termbase_service | MEDIUM |
| `_deduplicate_termbase_matches` | 53133–53157 | 25 | Дедупликация совпадений | L. Termbase/глоссарий | — | `_fetch_all_matches_for_segment`, `find_termbase_matches_in_source` | — | — | modules/termbase_service | LOW |
| `find_nt_matches_in_source` | 53159–53223 | 65 | Поиск NT-терминов | L. Termbase/глоссарий | — | `show_term_insert_popup`, `show_term_picker_dialog`, `_update_termlens_for_segment` | `termbase_index_lock`, `termbase_index` | — | modules/termbase_service | LOW |
| `highlight_source_with_termbase` | 53225–53262 | 38 | Подсветка терминов в source | L. Termbase/глоссарий | `log`, `find_nt_matches_in_source`, `find_termbase_matches_in_source` | `_refresh_termbase_display_for_current_segment`, `_quick_add_term_with_priority`, `_on_cell_selected_glossary_only` | `table`, `find_nt_matches_in_source`, `find_termbase_matches_in_source`, `log` | — | modules/termlens_controller | MEDIUM |
| `_apply_proactive_highlighting` | 53264–53320 | 57 | Проактивная подсветка | L. Termbase/глоссарий | `highlight_source_with_termbase` | `_trigger_idle_prefetch`, `_on_cell_selected_full` | `current_project`, `table`, `highlight_source_with_termbase` | signal:_proactive_highlight_signal×1 | modules/termlens_controller | LOW |
| `insert_term_translation` | 53322–53366 | 45 | Zero-ref вставка перевода термина | Legacy/мёртвое | `log`, `update_window_title`, `update_status_icon`, `_refresh_segment_status` | **dead-candidate** | `table`, `update_window_title`, `log`, `current_project` | — | PROBABLY_DEAD | LOW |
| `_apply_case_pattern` | 53373–53400 | 28 | Применение паттерна регистра (static) | H. Замена (Find&Replace) | — | `_execute_single_fr_operation`, `replace_current_match`, `replace_all_matches` | — | — | modules/find_replace_controller | LOW |
| `show_find_replace_dialog` | 53402–53754 | 353 | Диалог Find&Replace (353 строки) | H. Замена (Find&Replace) | `tr`, `log`, `_set_fr_demote_to_draft`, `_fr_find_next` | динамич. вход | `log`, `find_input`, `replace_input`, `search_source_cb` | menu×2 | modules/find_replace_controller | MEDIUM |
| `_fr_find_next` | 53756–53762 | 7 | FR: найти следующее | H. Замена (Find&Replace) | `find_next_match` | `show_find_replace_dialog` | `find_next_match`, `find_input`, `fr_history` | signal:clicked×1, signal:returnPressed×1 | modules/find_replace_controller | LOW |
| `_fr_find_all` | 53764–53770 | 7 | FR: найти все | H. Замена (Find&Replace) | `find_all_matches` | `show_find_replace_dialog` | `find_all_matches`, `find_input`, `fr_history` | signal:clicked×1 | modules/find_replace_controller | LOW |
| `_fr_replace_all` | 53772–53780 | 9 | FR: заменить все | H. Замена (Find&Replace) | `replace_all_matches` | `show_find_replace_dialog` | `replace_all_matches`, `find_input`, `replace_input`, `fr_history` | signal:clicked×1, signal:returnPressed×1 | modules/find_replace_controller | LOW |
| `_fr_add_to_set` | 53782–53808 | 27 | FR: добавить в набор | H. Замена (Find&Replace) | `log` | `show_find_replace_dialog` | `log`, `find_input`, `replace_input`, `find_replace_dialog` | signal:clicked×1 | modules/find_replace_controller | LOW |
| `_fr_load_operation` | 53810–53833 | 24 | FR: загрузка операции | H. Замена (Find&Replace) | — | динамич. вход | `find_input`, `replace_input`, `match_group`, `case_sensitive_cb` | signal:operation_selected×1 | modules/find_replace_controller | LOW |
| `_fr_compile_regex` | 53835–53844 | 10 | FR: компиляция regex | H. Замена (Find&Replace) | — | `find_next_match`, `find_all_matches`, `replace_all_matches` | `find_replace_dialog` | — | modules/find_replace_controller | LOW |
| `_fr_status_after_edit` | 53846–53856 | 11 | FR: статус после правки | H. Замена (Find&Replace) | — | `_execute_single_fr_operation`, `replace_current_match`, `replace_all_matches` | — | — | modules/find_replace_controller | LOW |
| `_set_fr_demote_to_draft` | 53858–53868 | 11 | FR: demote-to-draft настройка | H. Замена (Find&Replace) | `_load_settings_section`, `_save_settings_section`, `log` | `show_find_replace_dialog` | `_load_settings_section`, `_save_settings_section`, `log`, `fr_demote_to_draft` | signal:toggled×1 | modules/find_replace_controller | LOW |
| `_fr_run_set_batch` | 53870–53946 | 77 | FR: пакетный прогон набора | H. Замена (Find&Replace) | `update_window_title`, `update_progress_stats`, `_execute_single_fr_operation`, `log` | динамич. вход | `find_replace_dialog`, `table`, `update_window_title`, `update_progress_stats` | signal:set_selected×1 | modules/find_replace_controller | MEDIUM |
| `_execute_single_fr_operation` | 53948–54047 | 100 | FR: одиночная операция | H. Замена (Find&Replace) | `_apply_case_pattern`, `log`, `_fr_status_after_edit`, `record_undo_state` | `_fr_run_set_batch` | `current_project`, `allow_replace_in_source`, `log`, `_fr_status_after_edit` | — | modules/find_replace_controller | MEDIUM |
| `find_next_match` | 54049–54103 | 55 | Поиск следующего совпадения | G. Поиск | `highlight_search_term`, `log`, `find_all_matches_internal`, `_fr_compile_regex` | `_fr_find_next`, `replace_current_match` | `find_matches`, `current_match_index`, `highlight_search_term`, `log` | — | modules/find_replace_controller | MEDIUM |
| `find_all_matches` | 54105–54155 | 51 | Поиск всех совпадений | G. Поиск | `find_all_matches_internal`, `_clear_search_highlights_in_cells`, `log`, `_fr_compile_regex` | `_fr_find_all` | `find_matches`, `find_all_matches_internal`, `find_input`, `search_source_cb` | — | modules/find_replace_controller | LOW |
| `find_all_matches_internal` | 54157–54172 | 16 | Внутренний поиск всех | G. Поиск | `text_matches` | `find_next_match`, `find_all_matches`, `replace_all_matches` | `current_project`, `text_matches`, `find_matches` | — | modules/find_replace_controller | LOW |
| `text_matches` | 54174–54202 | 29 | Сопоставление текста | G. Поиск | — | `find_all_matches_internal` | — | — | modules/find_replace_controller | LOW |
| `_clear_search_highlights_in_cells` | 54204–54221 | 18 | Снятие подсветки поиска | G. Поиск | — | `find_next_match`, `find_all_matches`, `highlight_all_matches` | `table` | — | modules/find_replace_controller | LOW |
| `highlight_search_term` | 54223–54304 | 82 | Подсветка термина | G. Поиск | — | `find_next_match`, `find_all_matches`, `highlight_all_matches` | `table`, `case_sensitive_cb`, `match_group`, `regex_cb` | — | modules/find_replace_controller | MEDIUM |
| `replace_current_match` | 54306–54389 | 84 | Замена текущего совпадения | H. Замена (Find&Replace) | `update_window_title`, `find_next_match`, `_fr_status_after_edit`, `record_undo_state` | `show_find_replace_dialog` | `find_matches`, `current_match_index`, `update_window_title`, `find_next_match` | signal:clicked×1 | modules/find_replace_controller | MEDIUM |
| `replace_all_matches` | 54391–54570 | 180 | Замена всех (180 строк) | H. Замена (Find&Replace) | `find_all_matches_internal`, `log`, `update_window_title`, `update_progress_stats` | `_fr_replace_all` | `find_all_matches_internal`, `find_matches`, `allow_replace_in_source`, `find_replace_dialog` | — | modules/find_replace_controller | MEDIUM |
| `highlight_all_matches` | 54572–54604 | 33 | Подсветка всех совпадений | G. Поиск | `find_all_matches_internal`, `_clear_search_highlights_in_cells`, `log`, `highlight_search_term` | `show_find_replace_dialog` | `find_matches`, `find_all_matches_internal`, `find_input`, `search_source_cb` | signal:clicked×1 | modules/find_replace_controller | LOW |
| `clear_search_highlights` | 54606–54617 | 12 | Очистка подсветки поиска | G. Поиск | `_clear_search_highlights_in_cells`, `_apply_pagination_to_grid`, `log` | `show_find_replace_dialog` | `_clear_search_highlights_in_cells`, `_search_highlighted_cells`, `_apply_pagination_to_grid`, `log` | signal:clicked×1 | modules/find_replace_controller | LOW |
| `force_refresh_matches` | 54619–54904 | 286 | Принудительный refresh матчей (286 строк) | I. Перевод/подтверждение | `log`, `statusBar`, `find_termbase_matches_in_source`, `find_nt_matches_in_source` | `_on_termbase_db_debounce_fire`, `_force_termlens_display_redraw`, `_post_termbase_delete_refresh` | `current_project`, `log`, `termbase_cache_lock`, `translation_matches_cache_lock` | shortcut-registry×1, hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | HIGH |
| `show_goto_dialog` | 54906–54989 | 84 | Диалог Go To | E. Грид/таблица | `tr`, `log`, `go_to_page` | динамич. вход | `current_project`, `tr`, `_goto_max`, `log` | shortcut-registry×1, menu×1 | SupervertalerQt (ядро) | LOW |
| `show_project_info_dialog` | 54991–55401 | 411 | Инфо о проекте (411 строк) | C. Управление проектом | `tr`, `log`, `_add_overall_progress_section`, `go_to_segment` | `_setup_progress_indicators`, `show_file_progress_dialog` | `current_project`, `current_project_path`, `prompt_manager_qt`, `tm_metadata_mgr` | menu×1 | modules/project_service | MEDIUM |
| `show_search_dialog` | 55403–55456 | 54 | Zero-ref диалог поиска | Legacy/мёртвое | `tr`, `search_segments` | **dead-candidate** | `current_project`, `tr`, `search_segments` | — | PROBABLY_DEAD | LOW |
| `search_segments` | 55458–55492 | 35 | Достижим только из мёртвого show_search_dialog | Legacy/мёртвое | `_ensure_primary_filters_ready` | `show_search_dialog`, **dead-candidate** | `current_project`, `_ensure_primary_filters_ready`, `source_filter`, `target_filter` | — | PROBABLY_DEAD | LOW |
| `_highlight_text_in_widget` | 55494–55533 | 40 | Подсветка в виджете фильтра | E. Грид/таблица | — | `apply_filters` | `table` | — | modules/grid/filters | LOW |
| `_clear_filter_highlights_in_widget` | 55535–55573 | 39 | Снятие подсветки фильтра | E. Грид/таблица | — | `apply_filters`, `clear_filters`, `_clear_all_filter_highlights` | `table` | — | modules/grid/filters | LOW |
| `apply_filters` | 55575–55667 | 93 | Применение фильтров | E. Грид/таблица | `_clear_filter_highlights_in_widget`, `_widget_is_alive`, `_get_line_edit_text`, `_highlight_text_in_widget` | `filter_on_selected_text`, `confirm_and_next_unconfirmed` | `current_project`, `_widget_is_alive`, `table`, `clear_filters` | ARG_REF(self._ensure_shared_filter×10, signal:clicked×1 | modules/grid/filters | MEDIUM |
| `clear_filters` | 55669–55792 | 124 | Сброс фильтров | E. Грид/таблица | `_widget_is_alive`, `_clear_filter_highlights_in_widget`, `log`, `_apply_pagination_to_grid` | `apply_filters`, `filter_on_selected_text` | `current_project`, `_widget_is_alive`, `file_filter_combo`, `log` | signal:clicked×2 | modules/grid/filters | MEDIUM |
| `_on_file_filter_changed` | 55794–55857 | 64 | Смена файлового фильтра | E. Грид/таблица | `log`, `_update_file_boundary_labels`, `show_manage_views_dialog`, `_apply_pagination_to_grid` | динамич. вход | `current_project`, `log`, `_update_file_boundary_labels`, `file_filter_combo` | signal:currentIndexChanged×1 | modules/grid/filters | LOW |
| `_update_file_filter_combo` | 55859–55900 | 42 | Обновление комбо фильтра файлов | E. Грид/таблица | — | `load_project`, `_import_multifile_project`, `import_sdlppx_package` | `current_project`, `file_filter_combo` | hasattr×2, string×2, duck-typed×2 | modules/grid/filters | LOW |
| `show_manage_views_dialog` | 55902–56069 | 168 | Диалог управления видами | E. Грид/таблица | `tr`, `_update_file_filter_combo`, `log` | `_on_file_filter_changed` | `current_project`, `tr`, `_update_file_filter_combo`, `log` | — | modules/grid/filters | MEDIUM |
| `toggle_invisible_display` | 56071–56099 | 29 | Toggle невидимых символов | E. Грид/таблица | `refresh_grid_invisibles`, `log` | `create_grid_view_widget`, `create_grid_view_widget_for_home` | `invisible_display_settings`, `refresh_grid_invisibles`, `log` | menu×8 | modules/grid/filters | LOW |
| `toggle_all_invisibles` | 56101–56140 | 40 | Toggle всех невидимых | E. Грид/таблица | `refresh_grid_invisibles`, `log` | динамич. вход | `refresh_grid_invisibles`, `log`, `invisible_display_settings` | menu×3 | modules/grid/filters | LOW |
| `refresh_grid_invisibles` | 56142–56253 | 112 | Refresh невидимых в гриде | E. Грид/таблица | `apply_invisible_replacements`, `auto_resize_rows`, `_update_match_panel_tm_display` | `toggle_invisible_display`, `toggle_all_invisibles` | `current_project`, `auto_resize_rows`, `match_panel_tm_matches`, `table` | — | modules/grid/filters | MEDIUM |
| `_refresh_source_column_display` | 56255–56268 | 14 | Обновление колонки source | E. Грид/таблица | `load_segments_to_grid` | `_save_view_settings_from_ui_impl` | `load_segments_to_grid`, `table`, `current_project` | — | modules/grid/filters | LOW |
| `apply_invisible_replacements` | 56270–56303 | 34 | Применение замен невидимых | E. Грид/таблица | — | `_apply_undo_redo_action`, `_populate_single_row`, `_update_match_panel_tm_display` | `invisible_display_settings` | duck-typed×11, hasattr×9, string×9 | modules/grid/filters | MEDIUM |
| `reverse_invisible_replacements` | 56305–56344 | 40 | Обратные замены невидимых (fan-in высокий) | E. Грид/таблица | — | `show_mt_quick_popup`, `split_current_segment`, `_update_both_termlens` | — | hasattr×12, string×12, duck-typed×12 | modules/grid/filters | MEDIUM |
| `_update_spellcheck_button_style` | 56350–56356 | 7 | Стиль кнопки спеллчека | Spellcheck | — | `create_grid_view_widget`, `create_grid_view_widget_for_home`, `load_project` | `spellcheck_enabled`, `spellcheck_btn` | — | SupervertalerQt (ядро) | LOW |
| `_toggle_spellcheck` | 56358–56404 | 47 | Toggle спеллчека (меню) | Spellcheck | `log`, `_update_spellcheck_button_style`, `_save_spellcheck_settings`, `_refresh_all_highlighters` | динамич. вход | `spellcheck_enabled`, `_update_spellcheck_button_style`, `current_project`, `target_language` | menu×2 | SupervertalerQt (ядро) | LOW |
| `_toggle_spellcheck_from_button` | 56406–56449 | 44 | Toggle спеллчека (кнопка) | Spellcheck | `log`, `_update_spellcheck_button_style`, `_save_spellcheck_settings`, `_refresh_all_highlighters` | динамич. вход | `spellcheck_enabled`, `_update_spellcheck_button_style`, `current_project`, `target_language` | signal:clicked×2 | SupervertalerQt (ядро) | LOW |
| `_save_spellcheck_settings` | 56451–56460 | 10 | Сохранение настроек спеллчека | AB. Персистентность (settings IO) | `_load_unified_settings`, `_save_unified_settings`, `log` | `_toggle_spellcheck`, `_toggle_spellcheck_from_button` | `_load_unified_settings`, `spellcheck_enabled`, `_save_unified_settings`, `log` | — | modules/settings_service | LOW |
| `_load_spellcheck_settings` | 56462–56469 | 8 | Загрузка настроек спеллчека | AB. Персистентность (settings IO) | `_load_settings_section` | `create_grid_view_widget` | `_load_settings_section` | — | modules/settings_service | LOW |
| `_refresh_all_highlighters` | 56471–56506 | 36 | Refresh всех highlighter'ов | Spellcheck | — | `_toggle_spellcheck`, `_toggle_spellcheck_from_button`, `_save_custom_dictionary` | `table` | duck-typed×4, hasattr×2, string×2 | SupervertalerQt (ядро) | LOW |
| `_open_custom_dictionary_dialog` | 56508–56559 | 52 | Диалог кастомного словаря | Spellcheck | `tr`, `_save_custom_dictionary` | динамич. вход | `custom_dict_editor`, `word_count_label`, `tr`, `spellcheck_manager` | menu×2 | SupervertalerQt (ядро) | LOW |
| `_save_custom_dictionary` | 56561–56579 | 19 | Сохранение словаря | Spellcheck | `log`, `_refresh_all_highlighters` | `_open_custom_dictionary_dialog` | `log`, `_refresh_all_highlighters`, `custom_dict_editor`, `spellcheck_manager` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `_show_spellcheck_info` | 56581–56809 | 229 | Инфо-диалог спеллчека (229 строк) | Spellcheck | `tr`, `log`, `_open_folder_in_explorer`, `_refresh_all_highlighters` | динамич. вход | `spellcheck_enabled`, `spellcheck_manager`, `tr`, `log` | menu×2 | SupervertalerQt (ядро) | MEDIUM |
| `_open_folder_in_explorer` | 56811–56826 | 16 | Открыть папку в проводнике | Прочие утилиты | — | `_show_spellcheck_info` | — | signal:clicked×2 | SupervertalerQt (ядро) | LOW |
| `filter_empty_segments` | 56828–56870 | 43 | Zero-ref фильтр пустых сегментов | Legacy/мёртвое | `_widget_is_alive`, `log`, `_clear_all_filter_highlights` | **dead-candidate** | `current_project`, `_widget_is_alive`, `log`, `table` | — | PROBABLY_DEAD | LOW |
| `_clear_all_filter_highlights` | 56872–56882 | 11 | Снятие всех подсветок фильтра | E. Грид/таблица | `_clear_filter_highlights_in_widget` | `filter_empty_segments`, `apply_quick_filter`, `apply_advanced_filters` | `table`, `_clear_filter_highlights_in_widget` | — | modules/grid/filters | LOW |
| `apply_quick_filter` | 56884–56945 | 62 | Быстрый фильтр | E. Грид/таблица | `_widget_is_alive`, `_clear_all_filter_highlights`, `log`, `_apply_pagination_to_grid` | `create_grid_view_widget_for_home` | `current_project`, `_widget_is_alive`, `_clear_all_filter_highlights`, `log` | ARG_REF(quick_filter_menu.addAction×6 | modules/grid/filters | LOW |
| `_update_bulk_menu_label` | 56947–56973 | 27 | Метка bulk-меню | E. Грид/таблица | `tr` | динамич. вход | `tr`, `bulk_menu`, `current_project`, `table` | signal:aboutToShow×1 | SupervertalerQt (ядро) | LOW |
| `show_advanced_filters_dialog` | 56975–56984 | 10 | Диалог продвинутых фильтров | E. Грид/таблица | `apply_advanced_filters` | динамич. вход | `current_project`, `apply_advanced_filters` | signal:clicked×1 | modules/grid/filters | LOW |
| `apply_advanced_filters` | 56986–57062 | 77 | Применение продвинутых фильтров | E. Грид/таблица | `_widget_is_alive`, `log`, `_clear_all_filter_highlights` | `show_advanced_filters_dialog` | `_widget_is_alive`, `log`, `current_project`, `table` | — | modules/grid/filters | MEDIUM |
| `apply_sort` | 57064–57209 | 146 | Сортировка грида (146 строк) | E. Грид/таблица | `log`, `load_segments_to_grid`, `_widget_is_alive`, `tr` | `create_grid_view_widget_for_home` | `current_project`, `table`, `tr`, `load_segments_to_grid` | ARG_REF(sort_menu.addAction×12 | modules/grid/filters | MEDIUM |
| `on_tab_target_change` | 57215–57280 | 66 | Правка target в таб-панели | F. Редактирование текста | `_refresh_segment_status`, `log`, `_save_tab_target_to_tm` | динамич. вход | `tabbed_panels`, `current_project`, `tab_current_segment_id`, `debug_mode_enabled` | signal:textChanged×1 | SupervertalerQt (ядро) | MEDIUM |
| `_save_tab_target_to_tm` | 57282–57289 | 8 | Отложенное сохранение в TM | K. Память переводов (TM) | `save_segment_to_activated_tms`, `log` | `on_tab_target_change` | `save_segment_to_activated_tms`, `log` | timer×1 | SupervertalerQt (ядро) | LOW |
| `on_tab_status_combo_changed` | 57291–57296 | 6 | Смена статуса в таб-панели | F. Редактирование текста | `sender`, `on_tab_segment_status_change` | динамич. вход | `sender`, `on_tab_segment_status_change` | signal:currentIndexChanged×2 | SupervertalerQt (ядро) | LOW |
| `on_tab_segment_status_change` | 57298–57336 | 39 | Статус сегмента таб-панели | F. Редактирование текста | `log`, `_refresh_segment_status`, `save_segment_to_activated_tms` | `on_tab_status_combo_changed` | `current_project`, `tab_current_segment_id`, `log`, `tabbed_panels` | — | SupervertalerQt (ядро) | LOW |
| `on_tab_notes_change` | 57338–57374 | 37 | Заметки таб-панели | F. Редактирование текста | `_refresh_segment_status` | динамич. вход | `tabbed_panels`, `current_project`, `tab_current_segment_id`, `_refresh_segment_status` | signal:textChanged×1 | SupervertalerQt (ядро) | LOW |
| `_on_results_panel_notes_changed` | 57376–57414 | 39 | Zero-ref заметки панели результатов | Legacy/мёртвое | `_refresh_segment_status` | **dead-candidate** | `translation_results_panel`, `current_project`, `table`, `bottom_notes_edit` | — | PROBABLY_DEAD | LOW |
| `_comment_anchor_bg_color` | 57425–57431 | 7 | Цвет анкера комментария | E. Грид/таблица | — | `_apply_comment_anchors_to_cell` | `_COMMENT_ANCHOR_BG_QCOLOR` | — | modules/comments_ui | LOW |
| `_apply_comment_anchors_to_cell` | 57433–57477 | 45 | Анкеры комментариев в ячейке | E. Грид/таблица | `_comment_anchor_bg_color` | `add_comment_from_selection`, `_split_segment_grid_fast`, `_merge_segment_grid_fast` | `_comment_anchor_bg_color`, `table` | — | modules/comments_ui | LOW |
| `_apply_comment_anchors_to_all_cells` | 57479–57506 | 28 | Анкеры во всех ячейках | E. Грид/таблица | `_apply_comment_anchors_to_cell` | `load_segments_to_grid` | `current_project`, `table`, `_apply_comment_anchors_to_cell` | — | modules/comments_ui | LOW |
| `_refresh_cell_text_for_anchors` | 57508–57544 | 37 | Обновление текста ячейки с анкерами | E. Грид/таблица | — | `_comment_context_menu`, `_edit_comment_dialog` | `table` | — | modules/comments_ui | LOW |
| `_find_row_for_segment_id` | 57546–57560 | 15 | Строка по segment id | E. Грид/таблица | — | `_comment_context_menu`, `_edit_comment_dialog` | `table` | — | modules/grid/helpers | LOW |
| `_reset_comment_ui_state` | 57562–57593 | 32 | Сброс UI комментариев | E. Грид/таблица | — | `load_project`, `close_project` | `tabbed_panels`, `bottom_notes_edit`, `tab_current_segment_id`, `_active_comment_seg_id` | — | modules/comments_ui | LOW |
| `_refresh_segment_comments_list` | 57595–57759 | 165 | Список комментариев сегмента | E. Грид/таблица | `_update_bottom_notes_editor_lock_state`, `_sync_segment_comments_to_active`, `_navigate_to_segment_by_id`, `_comment_context_menu` | `add_comment_from_selection`, `new_project`, `load_project` | `_segment_comments_list_layout`, `current_project`, `_update_bottom_notes_editor_lock_state`, `_comment_list_header_btns` | — | modules/comments_ui | MEDIUM |
| `_sync_segment_comments_to_active` | 57761–57803 | 43 | Синк комментариев с активным | E. Грид/таблица | `_widget_is_alive` | `_on_cell_selected_full`, `_refresh_segment_comments_list` | `_widget_is_alive`, `_active_comment_highlight_btns`, `_active_comment_seg_id` | — | modules/comments_ui | LOW |
| `_comment_context_menu` | 57805–57857 | 53 | Меню комментариев | E. Грид/таблица | `_edit_comment_dialog`, `_refresh_segment_comments_list`, `_find_row_for_segment_id`, `update_window_title` | `_refresh_segment_comments_list` | `_edit_comment_dialog`, `_refresh_segment_comments_list`, `_find_row_for_segment_id`, `update_window_title` | signal:customContextMenuRequested×1 | modules/comments_ui | LOW |
| `_edit_comment_dialog` | 57859–57948 | 90 | Диалог правки комментария | E. Грид/таблица | `tr`, `_refresh_segment_comments_list`, `_find_row_for_segment_id`, `update_window_title` | `_comment_context_menu` | `_refresh_segment_comments_list`, `_find_row_for_segment_id`, `tr`, `update_window_title` | — | modules/comments_ui | LOW |
| `_update_bottom_notes_editor_lock_state` | 57950–58006 | 57 | Блокировка поля заметок | E. Грид/таблица | — | `_refresh_segment_comments_list`, `_update_bottom_notes_for_segment` | `current_project`, `table`, `bottom_notes_edit` | — | modules/comments_ui | LOW |
| `_navigate_to_segment_by_id` | 58008–58077 | 70 | Навигация по segment id | E. Грид/таблица | `log`, `go_to_page` | `_refresh_segment_comments_list`, `_refresh_proofreading_comments_list` | `current_project`, `log`, `table`, `main_tabs` | signal:clicked×2 | modules/grid/pagination | LOW |
| `_open_comment_in_panel` | 58079–58124 | 46 | Открыть комментарий в панели | E. Грид/таблица | `_refresh_segment_comments_list`, `_flash_comment_header`, `_widget_is_alive` | `_status_cell_comment_menu` | `_refresh_segment_comments_list`, `comments_sub_tabs`, `_flash_comment_header`, `right_tabs` | duck-typed×2, menu×1, hasattr×1, string×1 | modules/comments_ui | LOW |
| `_flash_comment_header` | 58126–58141 | 16 | Мигание заголовка комментариев | E. Грид/таблица | `_widget_is_alive` | `_open_comment_in_panel` | `_widget_is_alive` | — | modules/comments_ui | LOW |
| `_on_bottom_notes_changed` | 58143–58189 | 47 | Нигде не подключён (упоминания только в комментариях) | Legacy/мёртвое | `_refresh_segment_status`, `_refresh_segment_comments_list`, `get_translator_name` | **dead-candidate** | `current_project`, `table`, `translation_results_panel`, `_refresh_segment_status` | — | PROBABLY_DEAD | LOW |
| `_on_scratchpad_changed` | 58191–58199 | 9 | Правка scratchpad | F. Редактирование текста | — | динамич. вход | `current_project`, `scratchpad_edit`, `project_modified` | signal:textChanged×1 | SupervertalerQt (ядро) | LOW |
| `_update_scratchpad_for_project` | 58201–58211 | 11 | Scratchpad проекта | F. Редактирование текста | — | `new_project`, `load_project` | `current_project`, `scratchpad_edit` | — | SupervertalerQt (ядро) | LOW |
| `_update_bottom_notes_for_segment` | 58213–58251 | 39 | Заметки сегмента внизу | F. Редактирование текста | `_update_bottom_notes_editor_lock_state` | `_on_cell_selected_full`, `_comment_context_menu`, `_edit_comment_dialog` | `_update_bottom_notes_editor_lock_state`, `bottom_notes_edit` | hasattr×2, string×2, duck-typed×2 | SupervertalerQt (ядро) | MEDIUM |
| `_update_proofreading_notes_for_segment` | 58253–58261 | 9 | Заметки proofreading | Y. Proofreading | `_sync_proofreading_comments_to_active` | `_on_cell_selected_full` | `_sync_proofreading_comments_to_active` | — | SupervertalerQt (ядро) | LOW |
| `_refresh_proofreading_comments_list` | 58263–58381 | 119 | Список proofreading-комментариев | Y. Proofreading | `_sync_proofreading_comments_to_active`, `_navigate_to_segment_by_id`, `_delete_proofreading_comment` | `new_project`, `load_project`, `_finalise_import_with_indexes` | `_proofreading_comments_list_layout`, `current_project`, `_sync_proofreading_comments_to_active`, `_navigate_to_segment_by_id` | — | modules/comments_ui | MEDIUM |
| `_sync_proofreading_comments_to_active` | 58383–58417 | 35 | Синк proofreading-комментариев | Y. Proofreading | `_widget_is_alive` | `_update_proofreading_notes_for_segment`, `_refresh_proofreading_comments_list` | `_widget_is_alive`, `_active_pc_highlight_btns`, `_active_pc_seg_id` | — | modules/comments_ui | LOW |
| `_delete_proofreading_comment` | 58419–58437 | 19 | Удаление proofreading-комментария | Y. Proofreading | `_refresh_proofreading_comments_list`, `_refresh_segment_status` | `_refresh_proofreading_comments_list` | `current_project`, `_refresh_proofreading_comments_list`, `_refresh_segment_status`, `project_modified` | signal:clicked×1 | modules/comments_ui | LOW |
| `delete_all_proofreading_comments` | 58439–58472 | 34 | Удаление всех proofreading-комментариев | Y. Proofreading | `_refresh_proofreading_comments_list`, `log`, `_refresh_segment_status` | динамич. вход | `_refresh_proofreading_comments_list`, `log`, `current_project`, `_refresh_segment_status` | menu×1 | SupervertalerQt (ядро) | LOW |
| `copy_source_to_tab_target` | 58475–58484 | 10 | Копировать source в таб-панель | F. Редактирование текста | — | динамич. вход | `tabbed_panels` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `clear_tab_target` | 58486–58494 | 9 | Очистить target таб-панели | F. Редактирование текста | — | динамич. вход | `tabbed_panels` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `_get_voice_release_poller` | 58496–58532 | 37 | Poller отпускания PTT-ключа | VOICE | `log` | динамич. вход | `stop_voice_dictation_if_recording`, `log`, `_voice_release_poller` | duck-typed×2, hasattr×1, string×1 | modules/voice_controller | LOW |
| `_get_command_ptt_release_poller` | 58534–58571 | 38 | Poller отпускания command-PTT | VOICE | `log` | динамич. вход | `_on_voice_command_ptt_release`, `log`, `_command_ptt_release_poller` | duck-typed×2, hasattr×1, string×1 | modules/voice_controller | LOW |
| `_register_voice_pushtotalk_deferred` | 58573–58588 | 16 | Zero-ref отложенная регистрация PTT | Legacy/мёртвое | `log`, `_get_voice_hotkey_listener` | **dead-candidate** | `_get_voice_hotkey_listener`, `log` | — | PROBABLY_DEAD | LOW |
| `_register_voice_command_ptt_deferred` | 58592–58613 | 22 | Zero-ref отложенная регистрация command-PTT | Legacy/мёртвое | `log`, `_get_voice_hotkey_listener` | **dead-candidate** | `_get_voice_hotkey_listener`, `log` | — | PROBABLY_DEAD | LOW |
| `_on_voice_command_ptt_press` | 58615–58683 | 69 | Нажатие command-PTT | VOICE | `log`, `_toggle_alwayson_listening` | `_get_voice_hotkey_listener` | `voice_listener`, `voice_command_manager`, `_toggle_alwayson_listening`, `log` | duck-typed×2, hasattr×1, string×1 | modules/voice_controller | MEDIUM |
| `_on_voice_command_ptt_release` | 58685–58745 | 61 | Отпускание command-PTT | VOICE | `_do_voice_command_ptt_stop`, `log` | `_get_voice_hotkey_listener` | `_do_voice_command_ptt_stop`, `status_bar`, `log`, `_voice_command_ptt_pending_stop` | signal:released×1 | modules/voice_controller | MEDIUM |
| `_do_voice_command_ptt_stop` | 58747–58784 | 38 | Остановка PTT | VOICE | `log`, `_toggle_alwayson_listening` | `_on_alwayson_vad_status`, `_on_voice_command_ptt_release` | `voice_command_manager`, `voice_listener`, `_toggle_alwayson_listening`, `log` | singleShot×1 | modules/voice_controller | MEDIUM |
| `_get_voice_hotkey_listener` | 58786–58840 | 55 | Ленивый глобальный hotkey-listener | VOICE | `log`, `start_voice_dictation`, `stop_voice_dictation_if_recording`, `_on_voice_command_ptt_press` | `_register_voice_pushtotalk_deferred`, `_register_voice_command_ptt_deferred`, `_ensure_voice_pause_hotkey_armed` | `_voice_hotkey_listener`, `_on_voice_pause_key_captured`, `log`, `start_voice_dictation` | — | modules/voice_controller | MEDIUM |
| `_voice_pause_mode` | 58849–58853 | 5 | Режим voice-pause | VOICE | `load_dictation_settings` | `_on_voice_pause_press`, `_on_voice_pause_release` | `load_dictation_settings` | — | modules/voice_controller | LOW |
| `_pause_alwayson_external` | 58855–58864 | 10 | Пауза always-on извне | VOICE | `log` | `_on_voice_pause_press` | `log`, `_alwayson_paused_by_external` | — | modules/voice_controller | LOW |
| `_resume_alwayson_external` | 58866–58877 | 12 | Возобновление always-on | VOICE | `log` | `_on_voice_pause_press`, `_on_voice_pause_release` | `log`, `_alwayson_paused_by_external` | — | modules/voice_controller | LOW |
| `_ensure_voice_pause_hotkey_armed` | 58879–58910 | 32 | Взведение pause-хоткея | VOICE | `log`, `_get_voice_hotkey_listener`, `load_dictation_settings` | `_toggle_alwayson_listening` | `_get_voice_hotkey_listener`, `log`, `load_dictation_settings` | — | modules/voice_controller | LOW |
| `_on_voice_pause_press` | 58912–58919 | 8 | Нажатие pause-ключа | VOICE | `_pause_alwayson_external`, `_voice_pause_mode`, `_resume_alwayson_external` | `_get_voice_hotkey_listener` | `_voice_pause_mode`, `_pause_alwayson_external`, `_resume_alwayson_external` | — | modules/voice_controller | LOW |
| `_on_voice_pause_release` | 58921–58923 | 3 | Отпускание pause-ключа | VOICE | `_voice_pause_mode`, `_resume_alwayson_external` | `_get_voice_hotkey_listener` | `_voice_pause_mode`, `_resume_alwayson_external` | — | modules/voice_controller | LOW |
| `_set_voice_pause_setting` | 58925–58932 | 8 | Сохранение pause-настройки | VOICE | `_load_unified_settings`, `_save_unified_settings`, `log` | `_on_voice_pause_key_captured`, `_clear_voice_pause_hotkey` | `_load_unified_settings`, `_save_unified_settings`, `log` | — | modules/voice_controller | LOW |
| `_begin_voice_pause_capture` | 58934–58945 | 12 | Захват pause-ключа | VOICE | `log`, `_get_voice_hotkey_listener` | динамич. вход | `_get_voice_hotkey_listener`, `log`, `_capturing_voice_pause` | duck-typed×1 | modules/voice_controller | LOW |
| `_on_voice_pause_key_captured` | 58947–58967 | 21 | Ключ захвачен | VOICE | `_set_voice_pause_setting`, `_get_voice_hotkey_listener`, `log` | динамич. вход | `_set_voice_pause_setting`, `_get_voice_hotkey_listener`, `log`, `_capturing_voice_pause` | signal:captured×1 | modules/voice_controller | LOW |
| `_clear_voice_pause_hotkey` | 58969–58982 | 14 | Сброс pause-хоткея | VOICE | `_set_voice_pause_setting`, `log` | динамич. вход | `_set_voice_pause_setting`, `log`, `_capturing_voice_pause` | duck-typed×1 | modules/voice_controller | LOW |
| `stop_voice_dictation_if_recording` | 58984–59021 | 38 | Остановка диктовки | VOICE | `log`, `load_dictation_settings` | `_get_voice_hotkey_listener` | `log`, `load_dictation_settings`, `_dictation_toast` | signal:released×1 | modules/voice_controller | MEDIUM |
| `start_voice_dictation` | 59023–59241 | 219 | Запуск диктовки (219 строк) | VOICE | `log`, `_set_dictation_button_recording`, `load_dictation_settings`, `load_voice_vocabulary_settings` | `_get_voice_hotkey_listener` | `log`, `_voice_dictate_last_press_ms`, `voice_listener`, `dictation_thread` | duck-typed×4, signal:clicked×2, shortcut-registry×1, hasattr×1 | modules/voice_controller | HIGH |
| `on_dictation_complete` | 59243–59258 | 16 | Диктовка завершена | VOICE | `load_dictation_settings`, `_insert_dictated_text`, `log` | динамич. вход | `load_dictation_settings`, `_insert_dictated_text`, `voice_command_manager`, `log` | signal:transcription_ready×1 | modules/voice_controller | LOW |
| `_insert_dictated_text` | 59260–59333 | 74 | Вставка продиктованного текста | VOICE | `log` | `_on_alwayson_dictation`, `on_dictation_complete` | `tabbed_panels`, `log`, `status_bar` | — | modules/voice_controller | MEDIUM |
| `on_dictation_status` | 59335–59338 | 4 | Статус диктовки | VOICE | `log` | динамич. вход | `log`, `status_bar` | signal:status_update×1 | modules/voice_controller | LOW |
| `on_dictation_error` | 59340–59357 | 18 | Ошибка диктовки | VOICE | `log`, `_set_dictation_button_recording`, `_resume_alwayson_after_dictation` | динамич. вход | `_set_dictation_button_recording`, `log`, `_resume_alwayson_after_dictation`, `status_bar` | signal:error_occurred×1 | modules/voice_controller | LOW |
| `on_dictation_finished` | 59359–59372 | 14 | Финиш диктовки (signal) | VOICE | `log`, `_set_dictation_button_recording`, `_resume_alwayson_after_dictation` | динамич. вход | `log`, `_set_dictation_button_recording`, `_resume_alwayson_after_dictation`, `_dictation_toast` | signal:finished×1 | modules/voice_controller | LOW |
| `_resume_alwayson_after_dictation` | 59374–59392 | 19 | Возобновление always-on после диктовки | VOICE | `log` | `on_dictation_error`, `on_dictation_finished` | `voice_listener`, `log`, `_alwayson_was_running_before_dictation` | — | modules/voice_controller | LOW |
| `on_model_loading_started` | 59394–59427 | 34 | Загрузка Whisper-модели начата | VOICE | `log`, `_get_whisper_cache_path` | динамич. вход | `_get_whisper_cache_path`, `log`, `status_bar`, `is_loading_model` | signal:model_loading_started×1 | modules/voice_controller | LOW |
| `on_model_loading_finished` | 59429–59435 | 7 | Загрузка модели завершена | VOICE | `log` | динамич. вход | `loading_model_name`, `log`, `status_bar`, `is_loading_model` | signal:model_loading_finished×1 | modules/voice_controller | LOW |
| `_dictation_shortcut_label` | 59437–59459 | 23 | Метка шортката диктовки | VOICE | — | `create_grid_view_widget_for_home`, `create_assistance_panel`, `_set_dictation_button_recording` | — | — | modules/voice_controller | LOW |
| `_set_dictation_button_recording` | 59461–59488 | 28 | Кнопка записи диктовки | VOICE | `_dictation_shortcut_label` | `start_voice_dictation`, `on_dictation_error`, `on_dictation_finished` | `_dictation_shortcut_label`, `tab_dictate_btn`, `tabbed_panels` | — | modules/voice_controller | LOW |
| `save_tab_segment` | 59490–59510 | 21 | Сохранение сегмента таб-панели | F. Редактирование текста | `log`, `save_segment_to_activated_tms` | `save_tab_segment_and_next` | `current_project`, `tab_current_segment_id`, `log`, `save_segment_to_activated_tms` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `save_tab_segment_and_next` | 59512–59520 | 9 | Zero-ref save+next таб-панели | Legacy/мёртвое | `save_tab_segment` | **dead-candidate** | `save_tab_segment`, `table` | — | PROBABLY_DEAD | LOW |
| `filter_on_selected_text` | 59526–59588 | 63 | Фильтр по выделенному тексту | E. Грид/таблица | `log`, `apply_filters`, `_get_line_edit_text`, `clear_filters` | динамич. вход | `source_filter`, `clear_filters`, `log`, `table` | shortcut-registry×1 | SupervertalerQt (ядро) | MEDIUM |
| `copy_source_to_grid_target` | 59590–59620 | 31 | Копировать source->target (грид, duck-typed) | F. Редактирование текста | `log`, `record_undo_state`, `apply_invisible_replacements` | динамич. вход | `log`, `table`, `current_project`, `record_undo_state` | duck-typed×2 | SupervertalerQt (ядро) | MEDIUM |
| `clear_grid_target` | 59622–59650 | 29 | Очистить target (грид, duck-typed) | F. Редактирование текста | `log`, `record_undo_state` | динамич. вход | `log`, `table`, `current_project`, `record_undo_state` | duck-typed×2 | SupervertalerQt (ядро) | MEDIUM |
| `save_grid_segment` | 59652–59671 | 20 | Сохранить сегмент (грид, duck-typed) | F. Редактирование текста | `log`, `save_segment_to_activated_tms` | `save_grid_segment_and_next` | `table`, `current_project`, `log`, `save_segment_to_activated_tms` | — | SupervertalerQt (ядро) | MEDIUM |
| `save_grid_segment_and_next` | 59673–59691 | 19 | Zero-ref save+next грида | Legacy/мёртвое | `save_grid_segment` | **dead-candidate** | `save_grid_segment`, `table`, `_ctrl_enter_navigation` | — | PROBABLY_DEAD | LOW |
| `select_previous_match` | 59697–59718 | 22 | Предыдущий матч (шорткаты) | I. Перевод/подтверждение | `_get_active_match_shortcut_mode`, `_compare_panel_nav_active_box`, `_iter_visible_results_panels`, `log` | динамич. вход | `_get_active_match_shortcut_mode`, `_compare_panel_nav_active_box`, `_iter_visible_results_panels`, `log` | hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `select_next_match` | 59720–59741 | 22 | Следующий матч | I. Перевод/подтверждение | `_get_active_match_shortcut_mode`, `_compare_panel_nav_active_box`, `_iter_visible_results_panels`, `log` | динамич. вход | `_get_active_match_shortcut_mode`, `_compare_panel_nav_active_box`, `_iter_visible_results_panels`, `log` | hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `insert_match_by_number` | 59743–59778 | 36 | Вставка матча по номеру | I. Перевод/подтверждение | `log`, `_active_quicktrans_panel`, `_get_active_match_shortcut_mode`, `_iter_visible_results_panels` | `setup_global_shortcuts` | `_active_quicktrans_panel`, `_get_active_match_shortcut_mode`, `_iter_visible_results_panels`, `_insert_compare_panel_match_by_number` | duck-typed×3, hasattr×2, string×2, shortcut×1 | SupervertalerQt (ядро) | MEDIUM |
| `_handle_termlens_shortcut` | 59780–59819 | 40 | Шорткат TermLens | TermLens | `insert_termlens_term_by_number`, `_get_current_target_widget` | `setup_global_shortcuts` | `_termlens_last_key`, `_get_current_target_widget`, `insert_termlens_term_by_number`, `_termlens_last_time` | shortcut×1 | modules/termlens_controller | LOW |
| `_get_current_target_widget` | 59821–59827 | 7 | Целевой виджет ввода | E. Грид/таблица | — | `_handle_termlens_shortcut`, `_handle_compare_panel_alt0_shortcut` | `table` | — | SupervertalerQt (ядро) | LOW |
| `insert_termlens_term_by_number` | 59829–59865 | 37 | Вставка термина по номеру | TermLens | `log` | `_handle_termlens_shortcut` | `log` | — | modules/termlens_controller | LOW |
| `insert_selected_match` | 59867–59891 | 25 | Вставка выбранного матча | I. Перевод/подтверждение | `log`, `_get_active_match_shortcut_mode`, `_iter_visible_results_panels`, `_insert_compare_panel_current_match` | динамич. вход | `_get_active_match_shortcut_mode`, `_iter_visible_results_panels`, `_insert_compare_panel_current_match`, `log` | shortcut-registry×1, hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `_get_active_match_shortcut_mode` | 59893–59910 | 18 | Активный режим матч-шорткатов | I. Перевод/подтверждение | `_widget_is_alive` | `setup_global_shortcuts`, `select_previous_match`, `select_next_match` | `_widget_is_alive`, `right_tabs`, `match_panel_widget`, `translation_results_panel` | shortcut-registry×4 | SupervertalerQt (ядро) | MEDIUM |
| `_active_quicktrans_panel` | 59912–59925 | 14 | Активная панель QuickTrans | QuickTrans | — | `insert_match_by_number` | — | — | SupervertalerQt (ядро) | LOW |
| `_iter_visible_results_panels` | 59927–59936 | 10 | Итератор видимых панелей | I. Перевод/подтверждение | — | `select_previous_match`, `select_next_match`, `insert_match_by_number` | `results_panels` | — | SupervertalerQt (ядро) | LOW |
| `_compare_panel_nav_active_box` | 59938–59959 | 22 | Активный бокс панели | E. Грид/таблица | `_compare_panel_nav_tm`, `_compare_panel_nav_mt`, `_widget_is_alive` | `select_previous_match`, `select_next_match` | `compare_panel`, `_compare_panel_nav_tm`, `compare_panel_mt`, `_compare_panel_nav_mt` | — | modules/grid/match_panel | LOW |
| `_insert_compare_panel_current_match` | 59961–59981 | 21 | Вставка текущего матча | I. Перевод/подтверждение | `on_match_inserted`, `_widget_is_alive` | `insert_selected_match` | `compare_panel`, `compare_panel_mt`, `_widget_is_alive`, `right_tabs` | — | modules/grid/match_panel | LOW |
| `_handle_compare_panel_alt0_shortcut` | 59983–60028 | 46 | Alt+0 быстрая вставка | I. Перевод/подтверждение | `_replace_current_target_segment_text`, `_get_active_match_shortcut_mode`, `_get_current_target_widget` | динамич. вход | `_get_active_match_shortcut_mode`, `_compare_panel_last_key`, `_get_current_target_widget`, `_replace_current_target_segment_text` | shortcut-registry×1 | SupervertalerQt (ядро) | MEDIUM |
| `_replace_current_target_segment_text` | 60030–60106 | 77 | Замена текста target | I. Перевод/подтверждение | `log`, `_play_sound_effect`, `record_undo_state` | `_handle_compare_panel_alt0_shortcut` | `hide_outer_wrapping_tags`, `log`, `_play_sound_effect`, `current_project` | — | SupervertalerQt (ядро) | MEDIUM |
| `_play_sound_effect` | 60108–60174 | 67 | Звуковой эффект | AF. UI-хелперы | `load_general_settings` | `add_term_pair_to_termbase`, `_quick_add_term_with_priority`, `add_text_to_non_translatables` | `load_general_settings` | duck-typed×7, hasattr×4, string×4 | SupervertalerQt (ядро) | LOW |
| `_queue_tm_save_log` | 60176–60224 | 49 | Буферизованный TM-лог | K. Память переводов (TM) | `log` | `save_segment_to_activated_tms` | `_tm_save_log_lock`, `_tm_save_log_msg`, `_tm_save_log_count`, `_tm_save_log_timer` | — | modules/tm_controller | LOW |
| `_flush_tm_save_log_threadsafe` | 60226–60243 | 18 | Потокобезопасный сброс TM-лога | K. Память переводов (TM) | `log` | — (входа нет) | `_tm_save_log_lock`, `log`, `_tm_save_log_msg`, `_tm_save_log_count` | — | modules/tm_controller | LOW |
| `insert_compare_panel_mt` | 60245–60249 | 5 | Zero-ref вставка MT из панели | Legacy/мёртвое | `_insert_compare_panel_mt_current`, `_get_active_match_shortcut_mode` | **dead-candidate** | `_insert_compare_panel_mt_current`, `_get_active_match_shortcut_mode` | — | PROBABLY_DEAD | LOW |
| `insert_compare_panel_tm_target` | 60251–60255 | 5 | Zero-ref вставка TM из панели | Legacy/мёртвое | `_insert_compare_panel_tm_target_current`, `_get_active_match_shortcut_mode` | **dead-candidate** | `_insert_compare_panel_tm_target_current`, `_get_active_match_shortcut_mode` | — | PROBABLY_DEAD | LOW |
| `_insert_compare_panel_mt_current` | 60257–60262 | 6 | Вставка MT-матча | I. Перевод/подтверждение | `on_match_inserted` | `insert_compare_panel_mt`, `_insert_compare_panel_match_by_number` | `on_match_inserted`, `compare_panel_mt` | — | modules/grid/match_panel | LOW |
| `_insert_compare_panel_tm_target_current` | 60264–60269 | 6 | Вставка TM-матча | I. Перевод/подтверждение | `on_match_inserted` | `insert_compare_panel_tm_target`, `_insert_compare_panel_match_by_number` | `on_match_inserted`, `compare_panel_tm_target` | — | modules/grid/match_panel | LOW |
| `_insert_compare_panel_match_by_number` | 60271–60292 | 22 | Вставка матча по номеру из панели | I. Перевод/подтверждение | `_insert_compare_panel_mt_current`, `_insert_compare_panel_tm_target_current`, `_widget_is_alive` | `insert_match_by_number` | `compare_panel`, `_insert_compare_panel_mt_current`, `_insert_compare_panel_tm_target_current`, `_widget_is_alive` | — | modules/grid/match_panel | LOW |
| `go_to_previous_segment` | 60294–60344 | 51 | Навигация: пред. сегмент (duck-typed) | E. Грид/таблица | — | динамич. вход | `table` | duck-typed×12, hasattr×6, string×6 | SupervertalerQt (ядро) | MEDIUM |
| `go_to_next_segment` | 60346–60395 | 50 | Навигация: след. сегмент (duck-typed) | E. Грид/таблица | — | динамич. вход | `table` | duck-typed×12, hasattr×6, string×6 | SupervertalerQt (ядро) | MEDIUM |
| `go_to_first_segment` | 60397–60423 | 27 | Навигация: первый сегмент | E. Грид/таблица | `log`, `go_to_first_page` | динамич. вход | `log`, `table`, `go_to_first_page` | duck-typed×9, hasattr×5, string×5, shortcut-registry×1 | SupervertalerQt (ядро) | LOW |
| `go_to_last_segment` | 60425–60451 | 27 | Навигация: последний сегмент | E. Грид/таблица | `log`, `go_to_last_page` | динамич. вход | `log`, `table`, `go_to_last_page` | duck-typed×6, hasattr×2, string×2, shortcut-registry×1 | SupervertalerQt (ядро) | LOW |
| `confirm_and_next_unconfirmed` | 60453–60574 | 122 | Подтвердить и следующий (122 строки) | I. Перевод/подтверждение | `log`, `_confirm_current_row_segment`, `_update_termlens_for_segment`, `_update_pagination_ui` | `_check_auto_confirm_100_percent`, `confirm_selected_or_next` | `_is_text_filter_active`, `_confirm_current_row_segment`, `table`, `current_project` | duck-typed×2 | SupervertalerQt (ядро) | HIGH |
| `_check_auto_confirm_100_percent` | 60576–60650 | 75 | Авто-подтверждение 100% матчей | I. Перевод/подтверждение | `log`, `update_status_icon`, `confirm_and_next_unconfirmed`, `save_segment_to_activated_tms` | `confirm_and_next_unconfirmed` | `auto_confirm_overwrite_existing`, `log`, `table`, `enable_tm_matching` | singleShot×1 | SupervertalerQt (ядро) | HIGH |
| `confirm_selected_or_next` | 60652–60669 | 18 | Подтвердить выбранные или следующий | I. Перевод/подтверждение | `get_selected_segments_from_grid`, `confirm_selected_segments`, `confirm_and_next_unconfirmed` | динамич. вход | `get_selected_segments_from_grid`, `confirm_selected_segments`, `confirm_and_next_unconfirmed` | duck-typed×8, hasattr×4, string×4, signal:clicked×2 | SupervertalerQt (ядро) | MEDIUM |
| `_is_text_filter_active` | 60671–60675 | 5 | Активен ли текстовый фильтр | E. Грид/таблица | `_get_line_edit_text` | `confirm_and_next_unconfirmed` | `_get_line_edit_text` | — | modules/grid/helpers | LOW |
| `_confirm_current_row_segment` | 60677–60753 | 77 | Подтверждение текущей строки | I. Перевод/подтверждение | `log`, `record_undo_state`, `update_status_icon`, `_schedule_preview_refresh` | `confirm_and_next_unconfirmed` | `log`, `record_undo_state`, `update_status_icon`, `_schedule_preview_refresh` | — | SupervertalerQt (ядро) | HIGH |
| `_auto_propagate_to_identical` | 60755–60830 | 76 | Пропагация в идентичные сегменты | I. Перевод/подтверждение | `log`, `update_progress_stats`, `record_undo_state`, `_find_row_for_segment` | `_confirm_current_row_segment` | `current_project`, `update_progress_stats`, `log`, `record_undo_state` | — | SupervertalerQt (ядро) | MEDIUM |
| `_move_to_next_visible_row` | 60832–60868 | 37 | К следующей видимой строке | E. Грид/таблица | `log`, `_apply_pagination_to_grid` | `confirm_and_next_unconfirmed` | `log`, `table`, `current_project`, `_apply_pagination_to_grid` | — | SupervertalerQt (ядро) | MEDIUM |
| `confirm_selected_segments` | 60870–60924 | 55 | Подтверждение выбранных | I. Перевод/подтверждение | `log`, `_sync_grid_targets_to_segments`, `get_selected_segments_from_grid`, `_find_row_for_segment` | `confirm_selected_or_next`, `confirm_selected_segments_from_menu` | `current_project`, `_sync_grid_targets_to_segments`, `log`, `get_selected_segments_from_grid` | shortcut-registry×1, menu×1 | SupervertalerQt (ядро) | MEDIUM |
| `confirm_selected_segments_from_menu` | 60926–60938 | 13 | Подтверждение из меню | I. Перевод/подтверждение | `_get_selected_or_filtered_segments`, `confirm_selected_segments` | динамич. вход | `current_project`, `_get_selected_or_filtered_segments`, `table`, `confirm_selected_segments` | menu×1 | SupervertalerQt (ядро) | LOW |
| `change_status_selected` | 60940–60997 | 58 | Смена статуса выбранных | D. Операции с сегментами | `log`, `_sync_grid_targets_to_segments`, `_get_selected_or_filtered_segments`, `get_selected_segments_from_grid` | `create_menus`, `add_segment_actions_to_menu` | `current_project`, `_sync_grid_targets_to_segments`, `table`, `_get_selected_or_filtered_segments` | menu×2 | SupervertalerQt (ядро) | MEDIUM |
| `_sync_grid_targets_to_segments` | 60999–61020 | 22 | Синк target грида в сегменты | N. Экспорт | `_find_row_for_segment`, `reverse_invisible_replacements` | `_export_review_table`, `export_sdlrpx_package`, `export_standalone_sdlxliff` | `_find_row_for_segment`, `table`, `reverse_invisible_replacements`, `hide_outer_wrapping_tags` | — | SupervertalerQt (ядро) | MEDIUM |
| `_find_row_for_segment` | 61022–61035 | 14 | Строка по сегменту | E. Грид/таблица | — | `_apply_undo_redo_action`, `_select_grid_row_by_id`, `copy_source_to_target_bulk` | `table` | duck-typed×1 | modules/grid/helpers | LOW |
| `insert_termlens_text` | 61037–61066 | 30 | Вставка текста TermLens (signal) | TermLens | `log` | `show_term_picker_dialog` | `tabbed_panels`, `log`, `table` | signal:term_insert_requested×2, signal:term_inserted×1 | modules/termlens_controller | MEDIUM |
| `_on_termlens_font_size_changed` | 61068–61104 | 37 | Шрифт TermLens изменён | TermLens | `load_general_settings`, `sender`, `save_general_settings`, `log` | динамич. вход | `load_general_settings`, `sender`, `save_general_settings`, `log` | signal:font_size_changed×2 | modules/termlens_controller | LOW |
| `_on_termlens_edit_entry` | 61106–61144 | 39 | Правка термина из TermLens | L. Termbase/глоссарий | `log`, `_post_termbase_delete_refresh` | динамич. вход | `log`, `db_manager`, `_post_termbase_delete_refresh` | signal:edit_entry_requested×2, signal:edit_requested×1 | modules/termlens_controller | LOW |
| `_on_termlens_refresh_requested` | 61146–61173 | 28 | Refresh из TermLens | L. Termbase/глоссарий | `force_refresh_matches`, `log` | динамич. вход | `force_refresh_matches`, `log` | signal:refresh_requested×2 | modules/termlens_controller | LOW |
| `_on_termlens_delete_entry` | 61175–61210 | 36 | Удаление термина из TermLens | L. Termbase/глоссарий | `log`, `_post_termbase_delete_refresh` | динамич. вход | `termbase_mgr`, `log`, `_post_termbase_delete_refresh` | signal:delete_entry_requested×2 | modules/termlens_controller | LOW |
| `_refresh_current_segment_matches` | 61212–61218 | 7 | Zero-ref refresh текущих матчей | Legacy/мёртвое | `_refresh_termbase_display_for_current_segment`, `log` | **dead-candidate** | `_refresh_termbase_display_for_current_segment`, `log` | — | PROBABLY_DEAD | LOW |
| `save_tab_notes` | 61220–61224 | 5 | Сохранение заметок таб-панели | F. Редактирование текста | `log` | динамич. вход | `log`, `tab_current_segment_id` | signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `_toggle_tag_view_via_shortcut` | 61226–61230 | 5 | Toggle tag-view (шорткат) | E. Грид/таблица | `_set_tag_view_mode` | динамич. вход | `_set_tag_view_mode` | shortcut-registry×1 | SupervertalerQt (ядро) | LOW |
| `_enable_tag_view_after_import` | 61232–61236 | 5 | Tag-view после импорта | E. Грид/таблица | `_set_tag_view_mode`, `log` | `import_memoq_bilingual`, `import_memoq_rtf` | `_set_tag_view_mode`, `log` | — | SupervertalerQt (ядро) | LOW |
| `_set_tag_view_mode` | 61238–61257 | 20 | Режим отображения тегов | E. Грид/таблица | `log`, `_refresh_grid_display_mode` | `create_grid_view_widget_for_home`, `_toggle_tag_view_via_shortcut`, `_enable_tag_view_after_import` | `log`, `current_project`, `_refresh_grid_display_mode`, `wysiwyg_btn` | signal:clicked×3 | SupervertalerQt (ядро) | MEDIUM |
| `_wysiwyg_runs_to_tagged_text` | 61260–61284 | 25 | WYSIWYG runs -> теги (static) | O. Обработка документов | — | `_wysiwyg_document_to_tagged_text` | — | — | modules/tag_formatting | LOW |
| `_wysiwyg_document_to_tagged_text` | 61286–61339 | 54 | WYSIWYG документ -> теги | O. Обработка документов | `_wysiwyg_runs_to_tagged_text` | `_populate_single_row` | `_wysiwyg_runs_to_tagged_text` | — | modules/tag_formatting | MEDIUM |
| `toggle_tag_view` | 61341–61343 | 3 | Zero-ref toggle tag-view (дубль) | Legacy/мёртвое | `_set_tag_view_mode` | **dead-candidate** | `_set_tag_view_mode` | — | PROBABLY_DEAD | LOW |
| `_refresh_grid_display_mode` | 61345–61410 | 66 | Refresh режима отображения | E. Грид/таблица | `apply_invisible_replacements`, `auto_resize_rows`, `_segment_for_grid_row` | `load_segments_to_grid`, `_set_tag_view_mode` | `hide_outer_wrapping_tags`, `auto_resize_rows`, `current_project`, `_segment_for_grid_row` | — | SupervertalerQt (ядро) | MEDIUM |
| `update_tab_segment_editor` | 61412–61439 | 28 | Обновление редактора таб-панели | F. Редактирование текста | `log` | `_on_cell_selected_full` | `tabbed_panels`, `log`, `tab_current_segment_id` | hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `update_window_title` | 61448–61457 | 10 | Заголовок окна (fan-in 42) | B. Жизненный цикл окна/Workbench | `setWindowTitle` | `add_comment_from_selection`, `_apply_undo_redo_action`, `_sync_after_structural` | `current_project`, `project_modified`, `setWindowTitle` | — | SupervertalerQt (ядро) | LOW |
| `log` | 61459–61479 | 21 | Центральный лог (fan-in 359, callback-цель) | Логирование | `_log_to_ui` | `__init__`, `_show_data_location_dialog`, `_reinitialize_with_new_data_path` | `_log_to_ui`, `_log_signal` | hasattr×12, duck-typed×12, ARG_REF(TMXGenerator×5, ARG_REF(StandaloneSDLXLIFFHandler×5 | SupervertalerQt (ядро) | VERY_HIGH |
| `_log_to_ui` | 61481–61546 | 66 | Вывод лога в UI (signal) | Логирование | — | `log` | `debug_mode_enabled`, `session_log_text`, `session_log`, `detached_log_windows` | signal:_log_signal×1 | SupervertalerQt (ядро) | LOW |
| `show_options_dialog` | 61548–61551 | 4 | Zero-ref обёртка настроек | Legacy/мёртвое | `_go_to_settings_tab` | **dead-candidate** | `_go_to_settings_tab` | — | PROBABLY_DEAD | LOW |
| `_go_to_settings_tab` | 61553–61580 | 28 | Переход к настройкам | Управление вкладками | `_switch_main_tab` | `create_menus`, `show_options_dialog`, `translate_current_segment` | `_switch_main_tab`, `settings_tabs`, `ai_settings_scroll` | menu×1, signal:clicked×1 | SupervertalerQt (ядро) | LOW |
| `_go_to_superlookup` | 61582–61608 | 27 | Переход к SuperLookup | Z. SuperLookup | `open_workbench_to_superlookup`, `log` | `create_menus`, `show_concordance_search` | `open_workbench_to_superlookup`, `log` | duck-typed×5, menu×1, hasattr×1, string×1 | SupervertalerQt (ядро) | LOW |
| `load_llm_settings` | 61610–61648 | 39 | Загрузка LLM-настроек | AB. Персистентность (settings IO) | `_load_settings_section`, `load_api_keys` | `_update_llm_indicator`, `_ping_ollama_keepwarm`, `_on_main_tab_changed` | `_load_settings_section`, `load_api_keys` | duck-typed×8 | modules/settings_service | LOW |
| `save_llm_settings` | 61650–61657 | 8 | Сохранение LLM-настроек | AB. Персистентность (settings IO) | `_load_unified_settings`, `_save_unified_settings`, `log` | `_save_mt_quick_lookup_settings`, `_save_llm_settings_from_ui`, `_save_ai_settings_from_ui` | `_load_unified_settings`, `_save_unified_settings`, `log` | — | modules/settings_service | LOW |
| `load_proxy_settings` | 61663–61679 | 17 | Загрузка proxy | AB. Персистентность (settings IO) | `_load_settings_section` | `_create_ai_settings_tab`, `_get_proxy_url` | `_load_settings_section` | — | modules/settings_service | LOW |
| `save_proxy_settings` | 61681–61688 | 8 | Сохранение proxy | AB. Персистентность (settings IO) | `_load_unified_settings`, `_save_unified_settings`, `log` | `_save_ai_settings_from_ui` | `_load_unified_settings`, `_save_unified_settings`, `log` | — | modules/settings_service | LOW |
| `_get_proxy_url` | 61690–61712 | 23 | URL proxy | J. LLM/AI | `load_proxy_settings` | `_run_proofreading`, `_get_proxy_dict`, `_apply_gemini_proxy` | `load_proxy_settings` | duck-typed×5, hasattr×1, string×1 | modules/llm_controller | LOW |
| `_get_proxy_dict` | 61714–61721 | 8 | Словарь proxy | J. LLM/AI | `_get_proxy_url` | `call_google_translate`, `call_deepl`, `call_microsoft_translate` | `_get_proxy_url` | — | modules/llm_controller | LOW |
| `_apply_gemini_proxy` | 61723–61734 | 12 | Proxy для Gemini | J. LLM/AI | `_get_proxy_url` | `__init__`, `_save_ai_settings_from_ui` | `_get_proxy_url` | — | modules/llm_controller | LOW |
| `_get_active_custom_profile` | 61736–61763 | 28 | Активный custom-профиль | J. LLM/AI | `load_llm_settings` | `_resolve_provider_model`, `_update_llm_indicator`, `_create_mt_quick_lookup_settings_tab` | `load_llm_settings` | — | modules/llm_controller | LOW |
| `_get_custom_mt_profiles` | 61765–61769 | 5 | Список MT-профилей | J. LLM/AI | `load_llm_settings` | `_get_active_custom_mt_profile` | `load_llm_settings` | — | modules/llm_controller | LOW |
| `_get_active_custom_mt_profile` | 61771–61785 | 15 | Активный MT-профиль | J. LLM/AI | `_get_custom_mt_profiles`, `load_llm_settings` | `call_custom_mt` | `_get_custom_mt_profiles`, `load_llm_settings` | — | modules/llm_controller | LOW |
| `call_custom_mt` | 61787–61878 | 92 | Вызов custom MT (duck-typed извне) | J. LLM/AI | `load_api_keys`, `_get_active_custom_mt_profile`, `_get_proxy_url` | динамич. вход | `load_api_keys`, `_get_active_custom_mt_profile`, `_get_proxy_url` | duck-typed×2 | modules/llm_controller | MEDIUM |
| `create_llm_client` | 61880–61904 | 25 | Фабрика LLM-клиента (duck-typed) | J. LLM/AI | `_get_proxy_url`, `_get_active_custom_profile`, `load_llm_settings` | `_show_term_extraction_dialog`, `translate_current_segment`, `autotag_current_segment` | `_get_proxy_url`, `_get_active_custom_profile`, `load_llm_settings` | duck-typed×5 | modules/llm_controller | MEDIUM |
| `load_provider_enabled_states` | 61906–61932 | 27 | Состояния провайдеров | AB. Персистентность (settings IO) | `_load_settings_section` | `_create_ai_settings_tab`, `_create_mt_settings_tab`, `_create_mt_quick_lookup_settings_tab` | `_load_settings_section` | duck-typed×6, hasattr×2, string×2 | modules/settings_service | LOW |
| `save_provider_enabled_states` | 61934–61941 | 8 | Сохранение провайдеров | AB. Персистентность (settings IO) | `_load_unified_settings`, `_save_unified_settings`, `log` | `_save_llm_settings_from_ui`, `_save_ai_settings_from_ui`, `_save_mt_settings_from_ui` | `_load_unified_settings`, `_save_unified_settings`, `log` | — | modules/settings_service | LOW |
| `update_warning_banner` | 61943–61962 | 20 | Баннер предупреждений | E. Грид/таблица | `update_grid_delegate`, `_widget_is_alive` | `_save_general_settings_from_ui`, `create_grid_view_widget`, `create_grid_view_widget_for_home` | `allow_replace_in_source`, `update_grid_delegate`, `warning_banners`, `_widget_is_alive` | — | SupervertalerQt (ядро) | LOW |
| `update_grid_delegate` | 61964–62002 | 39 | Обновление делегата грида | E. Грид/таблица | `_widget_is_alive`, `log` | `update_warning_banner` | `table`, `allow_replace_in_source`, `_widget_is_alive`, `log` | — | SupervertalerQt (ядро) | LOW |
| `show_about @62004` | 62004–62174 | 171 | Затенён вторым show_about (62868) | Legacy/мёртвое | `tr`, `log` | **dead-candidate** | `tr`, `tm_database`, `tm_metadata_mgr`, `current_project` | menu×1 | PROBABLY_DEAD | LOW |
| `_open_url` | 62176–62182 | 7 | Открыть URL | Прочие утилиты | — | `create_menus`, `_open_superdocs_tab`, `check_for_updates` | — | menu×4 | SupervertalerQt (ядро) | LOW |
| `_open_superdocs_tab` | 62184–62194 | 11 | Zero-ref Superdocs-таб | Legacy/мёртвое | `_open_url` | **dead-candidate** | `_open_url` | — | PROBABLY_DEAD | LOW |
| `check_for_updates` | 62196–62700 | 505 | Проверка обновлений (505 строк!) | B. Жизненный цикл окна/Workbench | `_open_url`, `_normalize_version_tuple`, `_format_version_for_display`, `tr` | динамич. вход | `_update_check_request_id`, `_open_url`, `tr`, `_update_check_net_mgr` | menu×1, signal:clicked×1 | modules/update_checker | HIGH |
| `_fetch_latest_release_info_from_github` | 62702–62725 | 24 | GitHub release info | B. Жизненный цикл окна/Workbench | — | `check_for_updates` | — | — | modules/update_checker | LOW |
| `_normalize_version_tuple` | 62727–62736 | 10 | Нормализация версии | B. Жизненный цикл окна/Workbench | — | `check_for_updates` | — | — | modules/update_checker | LOW |
| `_format_version_for_display` | 62738–62745 | 8 | Формат версии | B. Жизненный цикл окна/Workbench | — | `check_for_updates`, `_build_version_info_text` | — | — | modules/update_checker | LOW |
| `_build_version_info_text` | 62747–62785 | 39 | Текст о версии | B. Жизненный цикл окна/Workbench | `_get_diagnostic_log_path`, `_format_version_for_display` | `copy_version_info_to_clipboard` | `_get_diagnostic_log_path`, `_format_version_for_display` | — | modules/update_checker | LOW |
| `copy_version_info_to_clipboard` | 62787–62800 | 14 | Версия в буфер | B. Жизненный цикл окна/Workbench | `_build_version_info_text` | динамич. вход | `_build_version_info_text` | menu×1, signal:clicked×1 | modules/update_checker | LOW |
| `_get_diagnostic_log_path` | 62802–62820 | 19 | Путь диагностического лога | Логирование | — | `_build_version_info_text`, `open_diagnostic_log`, `open_diagnostic_log_folder` | `user_data_path` | — | SupervertalerQt (ядро) | LOW |
| `open_diagnostic_log` | 62822–62839 | 18 | Открыть лог | Логирование | `_get_diagnostic_log_path` | динамич. вход | `_get_diagnostic_log_path` | menu×1 | SupervertalerQt (ядро) | LOW |
| `open_diagnostic_log_folder` | 62841–62855 | 15 | Открыть папку лога | Логирование | `_get_diagnostic_log_path` | динамич. вход | `_get_diagnostic_log_path` | menu×1 | SupervertalerQt (ядро) | LOW |
| `_show_ahk_setup_from_menu` | 62857–62866 | 10 | AHK setup из меню | B. Жизненный цикл окна/Workbench | — | динамич. вход | `lookup_tab` | menu×1 | SupervertalerQt (ядро) | LOW |
| `show_about @62868` | 62868–62930 | 63 | Диалог About (актуальный def) | B. Жизненный цикл окна/Workbench | `tr` | динамич. вход | `copy_version_info_to_clipboard`, `check_for_updates`, `tr` | menu×1 | SupervertalerQt (ядро) | LOW |
| `closeEvent @62932` | 62932–62991 | 60 | Актуальный closeEvent (затирает def 33453) | AE. События Qt/event filters | `_stop_okapi_sidecar`, `_cleanup_web_views`, `_close_detached_log_windows`, `save_project` | динамич. вход | `is_loading_model`, `project_modified`, `loading_model_name`, `_stop_okapi_sidecar` | duck-typed×1 | SupervertalerQt (ядро) | VERY_HIGH |
| `_cleanup_web_views` | 62993–62999 | 7 | Очистка WebEngine-вью | B. Жизненный цикл окна/Workbench | — | `closeEvent` | — | — | SupervertalerQt (ядро) | LOW |
| `_close_detached_log_windows` | 63001–63012 | 12 | Закрытие detach-окон лога | Логирование | — | `closeEvent` | `detached_log_windows` | — | SupervertalerQt (ядро) | LOW |
| `_init_okapi_sidecar_deferred` | 63016–63020 | 5 | Отложенный старт Okapi sidecar | O. Обработка документов | — | `__init__` | `_start_okapi_sidecar` | — | modules/okapi_controller | LOW |
| `_start_okapi_sidecar` | 63022–63063 | 42 | Запуск Okapi sidecar | O. Обработка документов | `log`, `_maybe_show_okapi_java_warning` | динамич. вход | `okapi_sidecar`, `_maybe_show_okapi_java_warning`, `log` | singleShot×1 | modules/okapi_controller | LOW |
| `_maybe_show_okapi_java_warning` | 63065–63131 | 67 | Предупреждение о Java | O. Обработка документов | `log`, `tr`, `_load_settings_section`, `_save_settings_section` | `_start_okapi_sidecar` | `log`, `_load_settings_section`, `tr`, `_save_settings_section` | — | modules/okapi_controller | LOW |
| `_stop_okapi_sidecar` | 63133–63140 | 8 | Остановка sidecar | O. Обработка документов | — | `closeEvent` | `okapi_sidecar` | — | modules/okapi_controller | LOW |
| `_get_whisper_cache_path` | 63142–63148 | 7 | Кэш Whisper | VOICE | — | `closeEvent`, `on_model_loading_started` | — | — | SupervertalerQt (ядро) | LOW |
| `translate_current_segment` | 63154–63607 | 454 | Перевод текущего сегмента (454 строк!) | I. Перевод/подтверждение | `log`, `tr`, `load_api_keys`, `update_window_title` | `fuzzy_fix_current_segment` | `load_llm_settings`, `_resolve_provider_model`, `table`, `current_project` | duck-typed×2, menu×1 | SupervertalerQt (ядро) | VERY_HIGH |
| `fuzzy_fix_current_segment` | 63613–63682 | 70 | Fuzzy fixer (меню/шорткат) | I. Перевод/подтверждение | `translate_current_segment` | динамич. вход | `current_project`, `translate_current_segment` | menu×1, signal:clicked×1 | SupervertalerQt (ядро) | MEDIUM |
| `_show_fuzzy_fix_diff` | 63684–63700 | 17 | Diff fuzzy fixer | I. Перевод/подтверждение | `_set_compare_panel_text_with_diff` | `translate_current_segment` | `match_panel_tm_target`, `_set_compare_panel_text_with_diff` | — | SupervertalerQt (ядро) | LOW |
| `_update_fuzzy_fixer_btn_state` | 63702–63716 | 15 | Кнопка fuzzy fixer | I. Перевод/подтверждение | — | `_update_match_panel_tm_display` | — | — | SupervertalerQt (ядро) | LOW |
| `autotag_current_segment` | 63722–63829 | 108 | Автотегирование сегмента (LLM) | I. Перевод/подтверждение | `log`, `load_llm_settings`, `_resolve_provider_model`, `update_status_icon` | `_autotag_row_from_context` | `load_llm_settings`, `_resolve_provider_model`, `current_project`, `update_status_icon` | menu×1, signal:clicked×1 | SupervertalerQt (ядро) | MEDIUM |
| `_quicklauncher_get_selection_text` | 63835–63848 | 14 | Текст выделения quicklauncher | J. LLM/AI | `reverse_invisible_replacements` | `run_grid_quicklauncher_prompt` | `reverse_invisible_replacements` | — | modules/quick_actions | LOW |
| `_quicklauncher_build_custom_prompt` | 63850–63932 | 83 | Промпт quicklauncher | J. LLM/AI | `log`, `_build_quicklauncher_document_context` | `run_grid_quicklauncher_prompt` | `prompt_manager_qt`, `current_project`, `log`, `_build_quicklauncher_document_context` | — | modules/quick_actions | MEDIUM |
| `_build_quicklauncher_document_context` | 63934–63997 | 64 | Контекст документа | J. LLM/AI | `load_general_settings` | `_quicklauncher_build_custom_prompt` | `current_project`, `load_general_settings` | — | modules/quick_actions | LOW |
| `_quicklauncher_show_result_dialog` | 63999–64024 | 26 | Диалог результата | J. LLM/AI | `tr` | `run_grid_quicklauncher_prompt` | `tr` | — | modules/quick_actions | LOW |
| `run_grid_quicklauncher_prompt` | 64026–64179 | 154 | Прогон quicklauncher (154 строки) | J. LLM/AI | `_quicklauncher_show_result_dialog`, `_quicklauncher_build_custom_prompt`, `_get_active_custom_profile`, `_quicklauncher_get_selection_text` | `open_quicklauncher` | `_quicklauncher_get_selection_text`, `table`, `current_project`, `load_llm_settings` | duck-typed×7, menu×3, hasattr×1, string×1 | modules/quick_actions | MEDIUM |
| `translate_multiple_segments` | 64181–64271 | 91 | Мульти-перевод (меню) | I. Перевод/подтверждение | `translate_batch`, `_get_selected_segments_with_rows`, `_get_filtered_segments_with_rows` | `create_menus` | `current_project`, `translate_batch`, `_get_selected_segments_with_rows`, `_get_filtered_segments_with_rows` | menu×8 | SupervertalerQt (ядро) | MEDIUM |
| `_get_selected_segments_with_rows` | 64273–64302 | 30 | Выбранные сегменты с номерами строк | E. Грид/таблица | `get_selected_segments_from_grid`, `get_selected_segments_from_list` | `translate_multiple_segments`, `autotag_segments_bulk` | `current_project`, `get_selected_segments_from_grid`, `get_selected_segments_from_list` | — | modules/grid/helpers | LOW |
| `_get_filtered_segments_with_rows` | 64304–64324 | 21 | Отфильтрованные сегменты | E. Грид/таблица | — | `translate_multiple_segments` | `current_project`, `table` | — | modules/grid/helpers | LOW |
| `autotag_segments_bulk` | 64326–64440 | 115 | Массовое автотегирование | I. Перевод/подтверждение | `log`, `_get_selected_segments_with_rows`, `load_llm_settings`, `_resolve_provider_model` | динамич. вход | `current_project`, `_get_selected_segments_with_rows`, `load_llm_settings`, `_resolve_provider_model` | menu×2 | SupervertalerQt (ядро) | MEDIUM |
| `translate_batch` | 64442–65274 | 833 | Пакетный перевод (833 строки! — крупнейший метод) | I. Перевод/подтверждение | `log`, `tr`, `load_api_keys`, `load_llm_settings` | `translate_multiple_segments` | `current_project`, `log`, `get_ai_inject_glossary_terms`, `tm_database` | duck-typed×2 | SupervertalerQt (ядро) | VERY_HIGH |
| `_fetch_llm_translation_async` | 65276–65402 | 127 | Достижим только из мёртвого _perform_delayed_lookup | Legacy/мёртвое | `log`, `load_api_keys`, `load_llm_settings`, `load_provider_enabled_states` | `_perform_delayed_lookup`, **dead-candidate** | `load_api_keys`, `load_llm_settings`, `load_provider_enabled_states`, `_resolve_provider_model` | — | PROBABLY_DEAD | MEDIUM |
| `_fetch_mt_translation_async` | 65404–65527 | 124 | Достижим только из мёртвого _perform_delayed_lookup | Legacy/мёртвое | `log`, `load_api_keys`, `load_provider_enabled_states`, `call_google_translate` | `_perform_delayed_lookup`, **dead-candidate** | `load_api_keys`, `load_provider_enabled_states`, `current_project`, `call_google_translate` | — | PROBABLY_DEAD | MEDIUM |
| `call_google_translate` | 65529–65582 | 54 | Google MT (duck-typed извне) | J. LLM/AI | `load_api_keys`, `_get_proxy_dict` | `_fetch_mt_translation_async` | `load_api_keys`, `_get_proxy_dict` | duck-typed×3, hasattr×1, string×1 | modules/mt_providers | MEDIUM |
| `call_deepl` | 65584–65656 | 73 | DeepL MT (SuperLookupTab вызывает) | J. LLM/AI | `load_api_keys`, `_get_proxy_dict` | `_fetch_mt_translation_async`, `_REMOVED_add_mt_and_llm_matches_progressive` | `load_api_keys`, `_get_proxy_dict` | duck-typed×3, hasattr×1, string×1 | modules/mt_providers | MEDIUM |
| `call_microsoft_translate` | 65658–65713 | 56 | Microsoft MT | J. LLM/AI | `load_api_keys`, `_get_proxy_dict` | `_fetch_mt_translation_async` | `load_api_keys`, `_get_proxy_dict` | duck-typed×2, hasattr×1, string×1 | modules/mt_providers | MEDIUM |
| `call_amazon_translate` | 65715–65770 | 56 | Amazon MT | J. LLM/AI | `load_api_keys` | `_fetch_mt_translation_async`, `_REMOVED_add_mt_and_llm_matches_progressive` | `load_api_keys` | duck-typed×2, hasattr×1, string×1 | modules/mt_providers | MEDIUM |
| `call_modernmt` | 65772–65822 | 51 | ModernMT | J. LLM/AI | `load_api_keys`, `_get_proxy_dict` | `_fetch_mt_translation_async` | `load_api_keys`, `_get_proxy_dict` | duck-typed×2, hasattr×1, string×1 | modules/mt_providers | MEDIUM |
| `call_mymemory` | 65824–65873 | 50 | MyMemory MT | J. LLM/AI | `load_api_keys`, `_get_proxy_dict` | `_fetch_mt_translation_async`, `_REMOVED_add_mt_and_llm_matches_progressive` | `load_api_keys`, `_get_proxy_dict` | — | modules/mt_providers | MEDIUM |
| `load_api_keys` | 65875–65883 | 9 | Загрузка API-ключей (fan-in 24, duck-typed) | AB. Персистентность (settings IO) | `_load_settings_section` | `_show_term_extraction_dialog`, `_create_ai_settings_tab`, `_create_mt_settings_tab` | `_load_settings_section` | duck-typed×12, hasattr×3, string×3 | modules/settings_service | MEDIUM |
| `save_api_keys` | 65885–65887 | 3 | Сохранение ключей | AB. Персистентность (settings IO) | `_save_settings_section` | `_save_api_keys_from_ui` | `_save_settings_section` | — | modules/settings_service | LOW |
| `get_ai_inject_glossary_terms` | 65889–65903 | 15 | Термины для AI-контекста | J. LLM/AI | — | `_preview_combined_prompt_from_grid`, `translate_current_segment`, `translate_batch` | `current_project`, `termbase_mgr` | duck-typed×2, hasattr×1, string×1 | modules/llm_controller | LOW |
| `show_image_extractor_from_tools` | 65905–65919 | 15 | Извлекатель картинок из Tools | Картинки/figure context | — | динамич. вход | `main_tabs`, `ai_subtabs` | menu×1 | SupervertalerQt (ядро) | LOW |
| `show_scratchpad` | 65921–65951 | 31 | Scratchpad (меню) | AF. UI-хелперы | `log` | динамич. вход | `current_project`, `log` | menu×1 | SupervertalerQt (ядро) | LOW |
| `show_theme_editor` | 65953–65960 | 8 | Редактор темы (меню) | V. Тема/UI-стили | `refresh_theme_colors` | динамич. вход | `theme_manager`, `refresh_theme_colors` | menu×1 | SupervertalerQt (ядро) | LOW |
| `refresh_theme_colors` | 65962–66026 | 65 | Глобальный refresh темы | V. Тема/UI-стили | `_update_settings_sidebar_theme`, `_update_tools_sidebar_theme`, `_update_resources_sidebar_theme`, `apply_alternating_row_colors` | `show_theme_editor` | `theme_manager`, `theme_aware_arrows`, `table`, `translation_results_panel` | singleShot×1, hasattr×1, string×1, duck-typed×1 | SupervertalerQt (ядро) | MEDIUM |
| `show_file_progress_dialog` | 66028–66030 | 3 | Zero-ref обёртка прогресса файла | Legacy/мёртвое | `show_project_info_dialog` | **dead-candidate** | `show_project_info_dialog` | — | PROBABLY_DEAD | LOW |
| `_add_overall_progress_section` | 66032–66084 | 53 | Секция общего прогресса | AC. Статистика | `tr` | `show_project_info_dialog` | `current_project`, `tr` | — | modules/stats_controller | LOW |
| `get_themed_button_style` | 66086–66110 | 25 | Zero-ref стиль кнопки | Legacy/мёртвое | — | **dead-candidate** | `theme_manager` | — | PROBABLY_DEAD | LOW |
| `get_themed_panel_style` | 66112–66137 | 26 | Zero-ref стиль панели | Legacy/мёртвое | — | **dead-candidate** | `theme_manager` | — | PROBABLY_DEAD | LOW |
| `_show_instant_tm_match` | 66139–66247 | 109 | Мгновенный TM-матч | K. Память переводов (TM) | `set_compare_panel_matches` | `on_cell_selected`, `_on_cell_selected_full`, `_search_mt_and_llm_matches` | `hide_outer_wrapping_tags`, `current_project`, `set_compare_panel_matches`, `tm_database` | — | SupervertalerQt (ядро) | MEDIUM |
| `_schedule_mt_and_llm_matches` | 66249–66268 | 20 | Отложенные MT/LLM-матчи | I. Перевод/подтверждение | `log`, `_execute_mt_llm_lookup` | `_on_cell_selected_full`, `force_refresh_matches`, `confirm_and_next_unconfirmed` | `_mt_llm_timer`, `log`, `_execute_mt_llm_lookup`, `_pending_mt_llm_segment` | — | SupervertalerQt (ядро) | MEDIUM |
| `_execute_mt_llm_lookup` | 66270–66285 | 16 | Выполнение MT/LLM-lookup (таймер) | I. Перевод/подтверждение | `log`, `_pcs`, `_search_mt_and_llm_matches` | `_schedule_mt_and_llm_matches` | `_pending_mt_llm_segment`, `_pcs`, `_search_mt_and_llm_matches`, `log` | timer×1 | SupervertalerQt (ядро) | MEDIUM |
| `_search_mt_and_llm_matches` | 66287–66401 | 115 | Поиск MT/LLM-матчей (115 строк) | I. Перевод/подтверждение | `log`, `_convert_language_to_code`, `_add_mt_and_llm_matches_progressive`, `_show_instant_tm_match` | `_execute_mt_llm_lookup` | `current_project`, `enable_tm_matching`, `tm_database`, `_add_mt_and_llm_matches_progressive` | — | SupervertalerQt (ядро) | HIGH |
| `_on_tm_search_failed` | 66403–66413 | 11 | Ошибка TMSearchWorker | W. Воркеры/фоновые задачи | `log` | динамич. вход | `log`, `_last_tm_search_error` | signal:search_failed×1 | SupervertalerQt (ядро) | LOW |
| `_on_tm_search_results` | 66415–66539 | 125 | Результаты TMSearchWorker (125 строк) | W. Воркеры/фоновые задачи | `log`, `_play_sound_effect`, `set_compare_panel_matches`, `_auto_insert_tm_match` | динамич. вход | `table`, `log`, `translation_matches_cache_lock`, `results_panels` | signal:results_ready×1 | SupervertalerQt (ядро) | MEDIUM |
| `_auto_insert_tm_match` | 66541–66619 | 79 | Авто-вставка TM-матча | I. Перевод/подтверждение | `log`, `record_undo_state`, `update_status_icon`, `_auto_resize_single_row` | `_on_cell_selected_full`, `_on_tm_search_results` | `log`, `table`, `record_undo_state`, `update_status_icon` | — | SupervertalerQt (ядро) | MEDIUM |
| `_add_mt_and_llm_matches_progressive` | 66621–66627 | 7 | Прогрессивные матчи (живая заглушка) | I. Перевод/подтверждение | — | `_search_mt_and_llm_matches` | — | — | SupervertalerQt (ядро) | LOW |
| `_REMOVED_add_mt_and_llm_matches_progressive` | 66629–66902 | 274 | Явно удалённый метод (274 строки, zero-ref) | Legacy/мёртвое | `log`, `set_compare_panel_matches`, `load_api_keys`, `_get_proxy_url` | **dead-candidate** | `enable_mt_matching`, `enable_llm_matching`, `load_api_keys`, `load_provider_enabled_states` | — | PROBABLY_DEAD | LOW |
| `_add_mt_and_llm_matches` | 66904–67091 | 188 | Zero-ref старый MT/LLM-путь (188 строк) | Legacy/мёртвое | `log`, `_get_proxy_url`, `load_api_keys`, `load_llm_settings` | **dead-candidate** | `enable_mt_matching`, `enable_llm_matching`, `log`, `load_api_keys` | — | PROBABLY_DEAD | LOW |
| `_clean_provider_prefix` | 67093–67098 | 6 | Zero-ref чистка префикса провайдера (дубль translation_services) | Legacy/мёртвое | — | **dead-candidate** | — | — | PROBABLY_DEAD | LOW |

Сводка по подсистемам: E. Грид/таблица: 158 • Legacy/мёртвое: 74 • VOICE: 49 • AB. Персистентность (settings IO): 47 • L. Termbase/глоссарий: 34 • I. Перевод/подтверждение: 34 • U. Настройки (UI): 32 • Форматы CAT (memoQ/Trados/SDL/…): 32 • J. LLM/AI: 29 • B. Жизненный цикл окна/Workbench: 27 • F. Редактирование текста: 26 • K. Память переводов (TM): 23 • N. Экспорт: 21 • V. Тема/UI-стили: 21 • O. Обработка документов: 18 • M. Импорт: 17 • Картинки/figure context: 16 • C. Управление проектом: 16 • D. Операции с сегментами: 15 • H. Замена (Find&Replace): 14 • Логирование: 11 • AF. UI-хелперы: 10 • TermLens: 10 • W. Воркеры/фоновые задачи: 10 • G. Поиск: 9 • Управление вкладками: 9 • A. Bootstrap/инициализация: 7 • Y. Proofreading: 7 • Spellcheck: 7 • QuickTrans: 6 • AC. Статистика: 6 • AE. События Qt/event filters: 5 • Прочие утилиты: 5 • Q. TMX: 4 • AD. Горячие клавиши: 3 • Z. SuperLookup: 3 • Trados bridge: 1 • Superdocs/browser: 1 • AA. Файловые операции: 1 • Буфер обмена: 1

# 5. SupervertalerQt Functional Clusters

Кластеры построены по фактической ответственности (не по расположению в файле). Methods = число методов, LOC = суммарный объём.

| Кластер | Методов | Описание |
|---|---|---|
| E. Грид/таблица | 158 | Рендер/пагинация/фильтры/выделение грида: `_populate_single_row` (455L), `_on_cell_selected_full` (617L), `create_grid_view_widget_for_home` (884L) |
| VOICE | 49 | Always-on listening, PTT, диктовка Whisper, tray-иконка |
| AB. Персистентность (settings IO) | 47 | settings_section/unified_settings, API-ключи, недавние проекты, бэкапы |
| L. Termbase/глоссарий | 34 | Индексация/поиск/добавление терминов, Tab на 1277L, LLM-извлечение терминов (430L) |
| I. Перевод/подтверждение | 34 | Подтверждение/пропагация/вставка матчей; `translate_batch` (833L), `translate_current_segment` (454L) |
| U. Настройки (UI) | 32 | 12+ builders вкладок настроек: `_create_ai_settings_tab` (1046L), `_create_general_settings_tab` (824L), `_create_view_settings_tab` (899L) |
| Форматы CAT (memoQ/Trados/SDL/…) | 32 | Обвязка форматов memoQ/Trados/SDLXLIFF/Phrase/DéjàVu/CafeTran/po |
| J. LLM/AI | 29 | LLM-клиенты, профили, proxy, quicklauncher, AI-контекст |
| B. Жизненный цикл окна/Workbench | 27 | Workbench-фокус, tray, Esc-dismiss, обновления (check_for_updates 505L) |
| F. Редактирование текста | 26 |  |
| K. Память переводов (TM) | 23 | TM-база, список TM (478L), импорт TMX (395L), сохранение в активные TM |
| N. Экспорт | 21 | Экспорт: target-DOCX (441L), review-таблица (497L), TXT/TMX/bilingual |
| V. Тема/UI-стили | 21 | Тема, шрифты, масштаб UI |
| O. Обработка документов | 18 | DOCX-хелперы экспорта (runs/комментарии/подсчёт слов) |
| M. Импорт | 17 | Импорт 10+ форматов: DOCX (423L), TXT (373L), memoQ/SDL/Phrase/… |
| Картинки/figure context | 16 | Вкладка извлечения картинок (346L builder + обработчики) |
| C. Управление проектом | 16 | new/open/load/save/close проекта, recent |
| D. Операции с сегментами | 15 |  |
| H. Замена (Find&Replace) | 14 | Find&Replace: диалог (353L), наборы операций, замены |
| Логирование | 11 | log (fan-in 359), лог-вкладка, detach, debug-буфер |
| AF. UI-хелперы | 10 | Статус-бар, прогресс, баннеры, звуки, scratchpad |
| TermLens | 10 | TermLens dock/popup, вставка терминов по номерам |
| W. Воркеры/фоновые задачи | 10 | threading-воркеры индексации termbase и prefetch матчей + обработчики QThread |
| G. Поиск | 9 | Поиск совпадений, подсветка, goto |
| Управление вкладками | 9 | Ленивые верхние вкладки (SuperLookup/Clipboard/Voice), переключение |
| A. Bootstrap/инициализация | 7 | `__init__` (446L), `create_menus` (890L), `create_main_layout` (247L), `init_ui` |
| Y. Proofreading | 7 | Proofread-диалог + запуск ProofreadWorker |
| Spellcheck | 7 | Toggle, словари, инфо-диалог |
| QuickTrans | 6 | QuickTrans popup/направление |
| AC. Статистика | 6 | Быстрая/полная статистика |
| AE. События Qt/event filters | 5 | `keyPressEvent`, `eventFilter`, `closeEvent`×2, кастомные тултипы |
| Прочие утилиты | 5 | Конвертация языков, открытие URL/папок |
| Q. TMX | 4 | Экспорт TMX ×3, окно TMX-редактора |
| AD. Горячие клавиши | 3 |  |
| Z. SuperLookup | 3 | Горячие клавиши SuperLookup (сам таб — отдельный класс, §11) |
| Trados bridge | 1 | Приём prompt-запросов Trados bridge |
| Superdocs/browser | 1 | Superbrowser-окно |
| AA. Файловые операции | 1 | PDF Rescue окно |
| Буфер обмена | 1 | Clipboard summon/dismiss |
| Legacy/мёртвое | 74 | Dead-цепочки, ribbon-остатки, дубли (§10, DEAD_CODE_REPORT.md) |

# 6. Self-State Map

Всего уникальных `self.*`-полей в `SupervertalerQt`: **1281**. Предварительная классификация по RHS-выражениям присваивания: {'state/data': 862, 'ui-widget': 379, 'cache': 10, 'service/manager': 16, 'worker/thread': 14}.

## 6.1 Топ-30 полей по числу затрагивающих методов

| Поле | Тип | Методов | Чтений | Записей | Пример RHS |
|---|---|---|---|---|---|
| `log` | state/data | 362 | 1208 | 0 | `` |
| `current_project` | state/data | 223 | 932 | 19 | `None` |
| `table` | ui-widget | 148 | 556 | 1 | `QTableWidget()` |
| `tr` | state/data | 123 | 1273 | 0 | `` |
| `project_modified` | state/data | 61 | 4 | 61 | `False` |
| `load_general_settings` | state/data | 48 | 56 | 0 | `` |
| `db_manager` | service/manager | 42 | 113 | 2 | `DatabaseManager(db_path=str(self.user_data_path / 'resources` |
| `update_window_title` | state/data | 42 | 45 | 0 | `` |
| `load_segments_to_grid` | state/data | 29 | 33 | 0 | `` |
| `prompt_manager_qt` | state/data | 29 | 84 | 2 | `UnifiedPromptManagerQt(self, standalone=False)` |
| `_load_settings_section` | state/data | 26 | 26 | 0 | `` |
| `auto_resize_rows` | state/data | 25 | 25 | 0 | `` |
| `save_general_settings` | state/data | 24 | 24 | 0 | `` |
| `user_data_path` | state/data | 24 | 57 | 4 | `get_user_data_path()` |
| `_widget_is_alive` | ui-widget | 24 | 54 | 0 | `` |
| `load_api_keys` | state/data | 24 | 27 | 0 | `` |
| `hide_outer_wrapping_tags` | state/data | 24 | 29 | 3 | `False` |
| `termbase_cache` | cache | 22 | 40 | 1 | `{}` |
| `load_llm_settings` | state/data | 22 | 24 | 0 | `` |
| `results_panels` | ui-widget | 22 | 47 | 2 | `[]` |
| `target_language` | state/data | 21 | 15 | 17 | `'Dutch'` |
| `_original_segment_order` | state/data | 21 | 2 | 22 | `self.current_project.segments.copy()` |
| `project_file_path` | state/data | 20 | 10 | 16 | `None` |
| `main_tabs` | ui-widget | 20 | 55 | 1 | `QTabWidget()` |
| `tm_database` | service/manager | 19 | 56 | 3 | `TMDatabase(source_lang=None, target_lang=None, db_path=str(s` |
| `initialize_tm_database` | service/manager | 19 | 21 | 0 | `` |
| `status_bar` | ui-widget | 19 | 37 | 1 | `QStatusBar()` |
| `theme_manager` | service/manager | 19 | 37 | 3 | `None` |
| `termbase_cache_lock` | cache | 19 | 32 | 1 | `threading.Lock()` |
| `update_progress_stats` | state/data | 18 | 19 | 0 | `` |

## 6.2 Примечания к классификации полей

- `log`, `load_general_settings`, `update_window_title`, `load_segments_to_grid`, `save_general_settings`, `load_api_keys` — это **методы**, попадающие в атрибутивные чтения (self.log(...) и передача как callback: `log` используется в 362 методах). Это не state, а связность вызовов.
- **UI-widgets** (~379): `table`, `main_tabs`, `right_tabs`, `bottom_tabs`, `results_panels`, `*_edit`, `*_btn`, `*_label`…
- **Application/project state**: `current_project` (223 метода!), `project_modified`, `project_file_path`, `source_language`, `target_language`.
- **Translation state**: `translation_matches_cache`+`_lock`, `current_lookup_segment_id`, `_pending_mt_llm_segment`.
- **TM state**: `tm_database`, `tm_metadata_mgr`, `_tm_save_log_*`.
- **Termbase state**: `termbase_index`+`_lock`, `termbase_cache`+`_lock`, `termbase_mgr`, `db_manager`.
- **Workers**: `_termbase_batch_worker_thread`, `_prefetch_worker_thread`+`_stop_event`, `dictation_thread`, `voice_listener`.
- **Settings-дубль**: поля из настроек продублированы в `self.*` (auto_fill_100_matches, auto_propagate_* — кластер из 15 полей всегда используется вместе).

## 6.3 Кластеры совместного использования (кандидаты в отдельные объекты)

| Поля | Размер | Комментарий |
|---|---|---|
| `_clear_caches_after_import`, `_deactivate_all_resources_for_new_project`, `_finalise_import_with_indexes`, `_initialize_spellcheck_for_target_language`, `_original_segment_order`, `initialize_tm_database`, `load_segments_to_grid`, `project_file_path`, … | 10 | общий контекст:  |
| `project_modified`, `update_window_title` | 2 | общий контекст:  |
| `_clear_search_highlights_in_cells`, `_search_highlighted_cells`, `auto_case_cb`, `case_sensitive_cb`, `current_match_index`, `find_all_matches_internal`, `find_input`, `find_matches`, … | 15 | общий контекст:  |
| `auto_center_active_segment`, `auto_confirm_100_percent_matches`, `auto_confirm_overwrite_existing`, `auto_fill_100_matches`, `auto_fill_confirm`, `auto_insert_100_percent_matches`, `auto_propagate_confirm`, `auto_propagate_exact_matches`, … | 17 | общий контекст:  |
| `termbase_cache`, `termbase_cache_lock` | 2 | общий контекст:  |
| `_get_termbase_status_hint`, `_update_both_termlens`, `find_nt_matches_in_source`, `find_termbase_matches_in_source`, `highlight_source_with_termbase` | 5 | общий контекст:  |
| `_update_preview`, `current_preview_index`, `extracted_image_files`, `image_extractor_files_list`, `image_extractor_status`, `preview_prev_btn` | 6 | общий контекст:  |
| `translation_matches_cache`, `translation_matches_cache_lock` | 2 | общий контекст:  |
| `default_font_family`, `default_font_size` | 2 | общий контекст:  |
| `max_undo_levels`, `redo_stack`, `undo_stack`, `update_undo_redo_actions` | 4 | общий контекст:  |
| `termlens_widget`, `termlens_widget_match` | 2 | общий контекст:  |
| `_load_unified_settings`, `_save_unified_settings` | 2 | общий контекст:  |
| `_update_match_panel_tm_display`, `match_panel_tm_index`, `match_panel_tm_matches` | 3 | общий контекст:  |
| `_ensure_shared_filter`, `apply_filters`, `source_filter`, `target_filter` | 4 | общий контекст:  |
| `go_to_page`, `page_number_input`, `page_size_combo` | 3 | общий контекст:  |

Сильнейшие связки: (1) **import-cleanup группа** — `_clear_caches_after_import`, `_original_segment_order`, `project_file_path`, `source_language`, `target_language`, `load_segments_to_grid` — ядро жизненного цикла проекта; (2) **search-highlight группа** (15 полей) — весь find/replace state; (3) **auto-propagate группа** (17 полей) — настройки подтверждения; (4) **termbase-cache** (`termbase_cache` + `termbase_cache_lock`); (5) **undo-группа** (`undo_stack`, `redo_stack`, `max_undo_levels`).

# 7. Call Graph / Hotspots

Граф: 817 узлов, 1 879 рёбер self-вызовов. Одна гигантская компонента связности (**754 метода**), остальные малы (4, 3, 2, 2 + 52 изолята). Циклических кластеров (SCC>1): **5**.

## 7.1 Топ fan-in (вызываются наибольшим числом методов)

| Метод | Fan-in (прямые) | Роль |
|---|---|---|
| `log` | 359 | универсальный логгер + callback для модулей |
| `load_general_settings` | 48 | перечитывает весь settings-файл |
| `update_window_title` | 42 | централизованный UI-синк |
| `load_segments_to_grid` | 29 | перезаливка грида |
| `_load_settings_section` / `_widget_is_alive` / `save_general_settings` / `load_api_keys` | 24–26 | settings-IO / защитные проверки |
| `auto_resize_rows`, `load_llm_settings`, `initialize_tm_database`, `update_progress_stats`, `reverse_invisible_replacements`, `record_undo_state`, `_refresh_segment_status` | 16–23 | инфраструктурные |

## 7.2 Топ fan-out (оркестраторы/роутеры)

`create_settings_tab` (22), `_on_cell_selected_full` (22), `__init__` (19), `load_project` (17), `create_grid_view_widget_for_home` (16), `translate_batch` (15), `import_memoq_bilingual` (15), `import_memoq_xliff` (14), `import_simple_txt`, `translate_current_segment`, `autotag_segments_bulk`, `_save_ai_settings_from_ui` (13)…

## 7.3 Архитектурные hotspots (UI + logic + I/O в одном методе)

| Метод | LOC | Почему hotspot |
|---|---|---|
| `translate_batch` | 833 | LLM-вызовы + retry + UI-прогресс + persistence + кэши |
| `_on_cell_selected_full` | 617 | роутер: TM+termbase+MT+TermLens+панели+подсветка |
| `create_grid_view_widget_for_home` | 884 | сборка всего грида + wiring 50+ сигналов |
| `create_termbases_tab` | 1277 | сборка вкладки + вся бизнес-логика termbase UI |
| `create_menus` | 890 | фабрика меню + wiring действий |
| `_create_ai_settings_tab` | 1046 | UI-билдер + сохранение настроек |
| `load_project` | 547 | парсинг + TM + spellcheck + UI + воркеры |
| `export_target_only_docx` | 441 | docx-генерация + комментарии + валидация |
| `show_find_replace_dialog` | 353 | UI + история + наборы + применение |
| `translate_current_segment` | 454 | LLM + кэш + UI + undo + TM save |
| `force_refresh_matches` | 286 | TM+termbase+MT+панели |
| `check_for_updates` | 505 | сеть + UI + версионирование |

## 7.4 Циклы self-вызовов (5 SCC)

1. `go_to_page → _apply_pagination_to_grid → _start_background_populate → _background_populate_step → _populate_single_row → _refresh_segment_status_by_id → _refresh_segment_status → _update_status_cell → _create_status_cell_widget → _status_cell_comment_menu → _open_comment_in_panel → _refresh_segment_comments_list → _comment_context_menu → _edit_comment_dialog → _navigate_to_segment_by_id → go_to_page` (15 узлов — грид/комментарии/навигация).
2. voice-PTT: `_toggle_alwayson_listening ↔ _get_voice_hotkey_listener ↔ _on_voice_command_ptt_press ↔ _on_voice_command_ptt_release ↔ _do_voice_command_ptt_stop` (6).
3. recent-проекты: `load_project ↔ add_to_recent_projects ↔ update_recent_menu ↔ …` (6).
4. `confirm_and_next_unconfirmed ↔ _check_auto_confirm_100_percent` (2).
5. proofreading-комментарии: `_refresh_proofreading_comments_list ↔ _delete_proofreading_comment` (2).

Циклы не являются import-циклами (это runtime-рекурсии вызовов); для декомпозиции важно, что кластеры 1 и 4 живут на стыке «грид ↔ сегменты ↔ комментарии» — их нельзя резать по границе файлов без разрыва цикла (нужен controller-слой или события).

# 8. Existing modules/ Architecture

115 файлов, плоский пакет `modules/` (без под-пакетов), ~82 029 строк. Легенда: PURE_LOGIC — без Qt; QT_UI — PyQt6; MAIN_WINDOW_COUPLED — duck-typed `parent_app`/`main_window`; ORPHAN — не импортируется никем.

| Модуль | LOC | Назначение (из docstring) | Классификация | Импортёров |
|---|---|---|---|---|
| `ai_actions` | 904 | AI Actions Module | MAIN_WINDOW_COUPLED | 1 |
| `ai_attachment_manager` | 344 | AI Assistant Attachment Manager | PURE_LOGIC | 1 |
| `ai_file_viewer_dialog` | 211 | AI Assistant File Viewer Dialog | QT_UI | 1 |
| `autocorrect` | 648 | AutoCorrect engine — typographic auto-conversion while typing. | PURE_LOGIC | 1 |
| `autostart` | 238 | Cross-platform "Start with computer" helper for Supervertaler Workbench. | PURE_LOGIC | 1 |
| `batch_offload` | 373 | Headless batch-translate engine for the Supervertaler for Trados large-file | PURE_LOGIC | 1 |
| `bilingual_markdown_handler` | 849 | Bilingual *Re-importable Text* handler — AI-friendly bracketed export/import. | PURE_LOGIC | 1 |
| `cafetran_docx_handler` | 380 | CafeTran Bilingual DOCX Handler | PURE_LOGIC | 1 |
| `chat_backend` | 275 | Chat Backend for Supervertaler | MAIN_WINDOW_COUPLED | 2 |
| `chat_message_delegate` | 474 | Chat Message Delegate for Supervertaler | QT_UI | 1 |
| `chat_view_widget` | 1156 | Chat View Widget for Supervertaler | MAIN_WINDOW_COUPLED | 1 |
| `clipboard_manager_widget` | 2532 | Clipboard Manager Widget for Supervertaler Workbench. | MAIN_WINDOW_COUPLED | 1 |
| `config_manager` | 445 | Configuration Manager for Supervertaler | PURE_LOGIC | 2 |
| `database_manager` | 3362 | Database Manager Module | PURE_LOGIC | 4 |
| `database_migrations` | 967 | Database Migration Functions | PURE_LOGIC | 1 |
| `dejavurtf_handler` | 785 | Déjà Vu X3 Bilingual RTF Handler | PURE_LOGIC | 1 |
| `dictation_toast` | 171 | dictation_toast.py – minimal frameless toast widget for dictation feedback. | QT_UI | 1 |
| `document_analyzer` | 325 | Document Analyzer Module | PURE_LOGIC | 1 |
| `docx_comments` | 272 | DOCX comment extraction | PURE_LOGIC | 1 |
| `docx_handler` | 953 | DOCX Handler | PURE_LOGIC | 1 |
| `extract_tm` | 519 | ExtractTM - Persistent TM extraction saved to .svtm files | PURE_LOGIC •ORPHAN | 0 |
| `feature_manager` | 343 | Supervertaler Feature Manager | PURE_LOGIC •ORPHAN | 0 |
| `figure_context_manager` | 341 | Figure Context Manager | PURE_LOGIC | 2 |
| `file_dialog_helper` | 149 | File Dialog Helper for Supervertaler | QT_UI | 1 |
| `find_replace` | 165 | Find and Replace Dialog Module | PURE_LOGIC •ORPHAN | 0 |
| `find_replace_qt` | 558 | Find & Replace Module for Supervertaler (PyQt6) | QT_UI | 1 |
| `glossary_manager` | 430 | Termbase Manager Module | PURE_LOGIC •ORPHAN | 0 |
| `help_system` | 264 | Context-sensitive help system for Supervertaler. | MAIN_WINDOW_COUPLED | 10 |
| `i18n` | 391 | Supervertaler Workbench internationalisation (i18n) support. | QT_UI | 1 |
| `identifier_conventions` | 84 | TM & Termbase identifier conventions — the single authoritative rule. | PURE_LOGIC •ORPHAN | 0 |
| `image_extractor` | 666 | ═══════════════════════════════════════════════════════════════════════════════ | PURE_LOGIC | 1 |
| `keyboard_shortcuts_widget` | 858 | Keyboard Shortcuts Settings Widget | MAIN_WINDOW_COUPLED | 1 |
| `lang_detect` | 106 | Lightweight binary language detection for QuickTrans direction. | PURE_LOGIC | 2 |
| `language_codes` | 294 | ISO 639-1 / BCP-47 language code ↔ English-name mapping. | PURE_LOGIC | 4 |
| `llm_clients` | 1977 | LLM Clients Module for Supervertaler | PURE_LOGIC | 7 |
| `llm_pricing` | 183 | LLM Pricing Module for Supervertaler | PURE_LOGIC | 2 |
| `local_llm_setup` | 1072 | Local LLM Setup Module for Supervertaler | QT_UI | 1 |
| `memoqrtf_handler` | 689 | memoQ Bilingual RTF Handler | PURE_LOGIC | 1 |
| `merge_prompt_dialog` | 177 | Merge Prompt Dialog ("Similar Term Found") | QT_UI | 1 |
| `mic_devices` | 172 | Input-device enumeration + name → index resolution for the Voice surface. | PURE_LOGIC | 3 |
| `mqxliff_handler` | 718 | MQXLIFF Handler Module | PURE_LOGIC | 1 |
| `okapi_sidecar` | 948 | Supervertaler Okapi Sidecar Client | PURE_LOGIC | 1 |
| `pdf_rescue_Qt` | 1759 | PDF Rescue Module - Qt Edition | MAIN_WINDOW_COUPLED | 1 |
| `pdf_rescue_tkinter` | 911 | PDF Rescue Module | MAIN_WINDOW_COUPLED •ORPHAN | 0 |
| `phrase_docx_handler` | 670 | Phrase (Memsource) Bilingual DOCX Handler | PURE_LOGIC | 1 |
| `platform_helpers` | 2225 | Platform Helpers for Supervertaler | PURE_LOGIC | 11 |
| `po_handler` | 567 | GNU gettext .po / .pot file handler. | PURE_LOGIC | 1 |
| `project_assets` | 102 | Project-folder asset handling (issue #228). | PURE_LOGIC | 1 |
| `project_home_panel` | 210 | Project Home Panel - Collapsible sidebar like memoQ's Project Home | QT_UI •ORPHAN | 0 |
| `project_tm` | 321 | ProjectTM - In-memory TM for instant grid lookups (Total Recall architecture) | PURE_LOGIC •ORPHAN | 0 |
| `prompt_assistant` | 361 | AI Prompt Assistant Module | PURE_LOGIC •ORPHAN | 0 |
| `prompt_library` | 690 | Prompt Library Manager Module | PURE_LOGIC •ORPHAN | 0 |
| `prompt_library_migration` | 444 | Migration Script: 4-Layer to Unified Prompt Library | PURE_LOGIC | 1 |
| `pseudo_translate` | 150 | Pseudo-translation: fill targets with deliberately stress-tested placeholder | PURE_LOGIC | 1 |
| `pseudo_translate_dialog` | 288 | Pseudo-translation — options dialog and apply/undo orchestration. | MAIN_WINDOW_COUPLED | 1 |
| `quick_access_sidebar` | 279 | Quick Access Sidebar - memoQ-style left navigation panel | QT_UI •ORPHAN | 0 |
| `quicktrans` | 1664 | QuickTrans - Instant translation popup (GT4T-style) | MAIN_WINDOW_COUPLED | 1 |
| `ribbon_widget` | 609 | Ribbon Widget - Modern Office-style ribbon interface for Supervertaler Qt | QT_UI •ORPHAN | 0 |
| `sdlppx_handler` | 2271 | Trados Studio Package Handler (SDLPPX/SDLRPX) | PURE_LOGIC | 2 |
| `sdltm_handler` | 238 | sdltm_handler — read-only consult of Trados Studio .sdltm Translation Memories. | PURE_LOGIC | 1 |
| `segment_split_merge` | 276 | Segment split & merge logic for Supervertaler Workbench. | PURE_LOGIC | 1 |
| `settings_sidebar` | 209 | Settings Sidebar Widget - Vertical tab navigation for Settings panel | QT_UI | 1 |
| `setup_wizard` | 355 | Setup Wizard for Supervertaler First Launch | PURE_LOGIC •ORPHAN | 0 |
| `shortcut_display` | 35 | Helpers for platform-appropriate shortcut labels in UI text. | PURE_LOGIC | 11 |
| `shortcut_manager` | 1189 | Keyboard Shortcut Manager for Supervertaler Qt | QT_UI | 2 |
| `simple_segmenter` | 209 | Simple Segmenter | PURE_LOGIC | 1 |
| `snippet_library` | 283 | ============================================================================= | PURE_LOGIC | 1 |
| `spellcheck_manager` | 728 | Spellcheck Manager for Supervertaler | PURE_LOGIC | 1 |
| `statistics_analyzer` | 484 | Statistics analyzer for Supervertaler Workbench. | QT_UI | 1 |
| `statistics_dialog_qt` | 616 | Statistics dialog for Supervertaler Workbench. | QT_UI | 1 |
| `statuses` | 245 | Centralized status vocabulary for Supervertaler segments. | PURE_LOGIC | 1 |
| `style_guide_manager` | 316 | Style Guide Manager Module | PURE_LOGIC •ORPHAN | 0 |
| `styled_widgets` | 342 | Shared styled widgets used across Supervertaler. | QT_UI | 10 |
| `superbrowser` | 352 | ============================================================================= | QT_UI | 1 |
| `superdocs` | 21 | modules.superdocs (deprecated) | PURE_LOGIC •ORPHAN | 0 |
| `superdocs_viewer_qt` | 306 | Deprecated Superdocs viewer module. | PURE_LOGIC •ORPHAN | 0 |
| `superlookup` | 257 | Superlookup Engine | PURE_LOGIC | 1 |
| `supervertaler_bridge_server` | 358 | Supervertaler Bridge Server (formerly "Sidekick Bridge") | QT_UI | 1 |
| `tag_manager` | 383 | Tag Manager | PURE_LOGIC | 1 |
| `term_picker_dialog` | 499 | term_picker_dialog.py | QT_UI | 1 |
| `termbase_entry_editor` | 1825 | Termbase Entry Editor Dialog | QT_UI | 2 |
| `termbase_import_export` | 470 | Termbase Import/Export Module | PURE_LOGIC | 1 |
| `termbase_manager` | 1498 | Termbase Manager Module | PURE_LOGIC | 2 |
| `termlens_popup` | 747 | termlens_popup.py | QT_UI | 1 |
| `termlens_widget` | 2597 | TermLens Widget - RYS-style Inline Terminology Display | QT_UI | 2 |
| `text_conversion_library` | 443 | ============================================================================= | PURE_LOGIC | 1 |
| `theme_manager` | 568 | Theme Manager | QT_UI | 1 |
| `tm_editor_dialog` | 100 | TM Editor Dialog - Edit a specific Translation Memory | QT_UI | 1 |
| `tm_manager_qt` | 1256 | Translation Memory Manager for Supervertaler Qt | QT_UI | 2 |
| `tm_metadata_manager` | 699 | Translation Memory Metadata Manager Module | PURE_LOGIC | 2 |
| `tmx_editor` | 1468 | TMX Editor Module - Professional Translation Memory Editor | PURE_LOGIC | 1 |
| `tmx_editor_qt` | 2707 | TMX Editor Module - PyQt6 Edition | QT_UI | 1 |
| `tmx_generator` | 269 | TMX Generator Module | PURE_LOGIC | 4 |
| `tracked_changes` | 904 | Tracked Changes Management Module | PURE_LOGIC •ORPHAN | 0 |
| `trados_bridge_client` | 525 | Trados Bridge Client | PURE_LOGIC | 2 |
| `trados_docx_handler` | 434 | Trados Bilingual DOCX Handler (Review Files) | PURE_LOGIC | 1 |
| `translation_memory` | 847 | Translation Memory Module - SQLite Database Backend | PURE_LOGIC | 1 |
| `translation_results_panel` | 2428 | Translation Results Panel | MAIN_WINDOW_COUPLED | 1 |
| `translation_services` | 282 | Translation Services Module | PURE_LOGIC •ORPHAN | 0 |
| `ui_scale` | 114 | ui_scale.py – global UI font-scale helper for modules with hardcoded stylesheet sizes. | PURE_LOGIC | 3 |
| `unified_prompt_library` | 1111 | Unified Prompt Library Module | PURE_LOGIC | 1 |
| `unified_prompt_manager_qt` | 6809 | Unified Prompt Manager Module - Qt Edition (powers the AI tab) | MAIN_WINDOW_COUPLED | 1 |
| `usage_log` | 325 | Persistent token-usage ledger for Supervertaler Workbench. | PURE_LOGIC | 4 |
| `usage_report_dialog` | 149 | Token Usage & Costs report dialog for Supervertaler Workbench. | QT_UI | 1 |
| `usage_statistics` | 296 | Minimal, opt-in anonymous usage statistics for Supervertaler Workbench. | PURE_LOGIC | 1 |
| `voice_command_dialog` | 356 | Dialog for adding and editing voice commands. | QT_UI | 2 |
| `voice_commands` | 1466 | Voice Commands Module for Supervertaler | MAIN_WINDOW_COUPLED | 2 |
| `voice_dictation` | 498 | Voice Dictation Module for Supervertaler | QT_UI •ORPHAN | 0 |
| `voice_dictation_lite` | 322 | Lightweight Voice Dictation for Supervertaler | QT_UI | 1 |
| `voice_hotkey_listener` | 481 | Global hotkey listener with press AND release events. | QT_UI | 2 |
| `voice_release_poller` | 311 | Detect key-release for the push-to-talk hotkey via GetAsyncKeyState polling. | QT_UI | 1 |
| `voice_tab` | 1379 | Voice tab – voice commands and dictation control panel. | MAIN_WINDOW_COUPLED | 1 |
| `voice_vocabulary` | 270 | Voice dictation vocabulary biasing + replacement table. | PURE_LOGIC | 3 |
| `vosk_model_manager` | 189 | Vosk model lifecycle: locate, download (one-time), extract, and load. | PURE_LOGIC | 1 |

Смежные единицы: `scripts/` (sv_tm_diagnose + 3 миграции БД) и `tools/` (i18n) **не импортируют** `modules/`; `assets/generate_icons.py` автономен.

# 9. Cross-module Dependencies

- `Supervertaler.py` → `modules.*`: **243 import- statements** (вкл. ленивые), 163 уникальных имени, 128 классов/функций инстанцируются в 513 местах. Топ: `CheckmarkCheckBox` (128×), `format_shortcut_for_display` (59×), `CheckmarkRadioButton` (42×), `TranslationMatch` (27×), `LLMClient` (14×), `get_status` (14×).
- `modules.*` → `Supervertaler.py`: **0 прямых импортов** (запрет зафиксирован в docstring `voice_command_dialog.py`). Связь только duck-typed через инжектируемые объекты.
- Самый импортируемый модуль: `platform_helpers` (11 файлов), далее `shortcut_display`, `styled_widgets`, `help_system` (10), `llm_clients` (7).
- Внутри `modules/`: `unified_prompt_manager_qt` — крупнейший потребитель (ai_actions, chat_backend, chat_view_widget, document_analyzer, unified_prompt_library, ai_attachment_manager…).
- HIGH COUPLING (на MainWindow): `unified_prompt_manager_qt`, `quicktrans`, `translation_results_panel`, `voice_commands` (~15 duck-typed методов MainWindow), `voice_tab` (документированный контракт), `clipboard_manager_widget`, `chat_view_widget` (self._get_parent_app()).
- LOW COUPLING (легко отделяемы): все PURE_LOGIC-модули — `database_manager`, `sdlppx_handler`, `docx_handler` + 5 CAT-хендлеров, `tmx_generator`, `llm_clients`, `platform_helpers`, `statuses`, `language_codes`, `config_manager` и др.

## 9.1 Duck-typed контракты MainWindow → modules (обратная зависимость)

| Модуль | Механизм | Используемые методы MainWindow |
|---|---|---|
| `unified_prompt_manager_qt` | `UnifiedPromptManagerQt(self)` | конструируется самим монолитом |
| `quicktrans` | `parent_app` во всех классах | `load_api_keys`, `load_llm_settings`, `create_llm_client`, `call_custom_mt`, `set_quicktrans_direction_override`, `open_workbench_to_superlookup` |
| `voice_commands` | `main_window=` + hasattr | ~15 методов: `go_to_next_segment`, `go_to_previous_segment`, `split_current_segment`, `merge_current_segment`, `_toggle_alwayson_listening`, `save_grid_segment`, `copy_source_to_grid_target`, `clear_grid_target`, `confirm_selected_or_next`… |
| `voice_tab` | `parent_app` (контракт в docstring) | `_reset_voice_commands`, `_populate_voice_commands_table`, `save_voice_vocabulary_settings`, `open_termbases_tab` |
| `translation_results_panel` | `parent_app=self` | `log`, настройки, вставка матчей |
| `chat_view_widget` | `self._get_parent_app()` (обход родителей) | `load_api_keys`, `load_llm_settings`, `_get_proxy_url` |
| `chat_backend` | `parent_app` | `load_api_keys`, `current_provider`, `create_llm_client`, `_get_proxy_url` |
| `clipboard_manager_widget` | `parent_app` + callback | `_clipboard_prior_workbench_tab`, `paste_text_callback` |
| `keyboard_shortcuts_widget` | `main_window=parent` | `refresh_shortcut_enabled_states` (hasattr-guarded), `_find_autohotkey_for_settings` |
| `help_system` | `install(main_window)` | глобальный event filter |
| `pdf_rescue_Qt` | `parent_app` | `log`, `api_keys`, `load_api_keys` |
| `pseudo_translate_dialog` | `run_pseudo_translation(main_window)` | `current_project`, `table`, `get_selected_segments_from_grid` |
| `ai_actions` | `parent_app` | `current_project` |
| `pdf_rescue_tkinter` | `parent_app` | `root` (orphan-модуль) |

Плюс внутренние duck-typed вызовы внутри монолита: `SuperlookupTab` → MainWindow (`call_deepl`, `call_google_translate`, `db_manager`, `termbase_mgr`, `_switch_main_tab`, `load_api_keys`…), grid-редакторы → MainWindow (через `_get_main_window()`, ~30 атрибутов), event-фильтры → MainWindow.

# 10. Duplication / Legacy Boundaries

## 10.1 Точные дубли тел внутри монолита (нормализованный source)

| Дубликаты | LOC |
|---|---|
| `Pink/Blue/OrangeCheckmarkCheckBox.paintEvent` | 3×46 (копия `styled_widgets.CheckmarkCheckBox`) |
| `SearchHighlightDelegate/WordWrapDelegate`: `set_highlight`, `clear_highlight`, `clear_all_highlights` | 3 пары |
| `TMSearchWorker.cancel` = `ProofreadWorker.cancel` | 2 |
| `__init__` трёх event-фильтров | идентичны |

## 10.2 Дубликаты monolith ↔ modules/ (ratio>0.5, 164 пары, главное)

| Имя | В монолите | В modules/ | Вывод |
|---|---|---|---|
| `CheckmarkCheckBox`-семейство | Pink/Blue/Orange + CustomRadioButton (72559–72869) | `styled_widgets.py` (базовые + Purple/Teal) | монолит дублирует библиотеку виджетов |
| `strip_tags` | **3 копии внутри монолита** (38750, 38879, 38960 — вложенные) | `docx_handler`, `tag_manager` | 5 реализаций одной операции |
| `runs_to_tagged_text`, `tagged_text_to_runs` | верхний уровень (494, 990) | `tag_manager.py` | legacy-дубль |
| `get_docx_language_code`, `set_docx_language` | верхний уровень | `docx_handler.py` | legacy-дубль |
| `load_api_keys` | метод (65875) | `llm_clients.py:43` | две реализации |
| `add_term/delete_term/create_termbase/search_termbases` | методы | `glossary_manager`, `termbase_manager`, `database_manager` | старый JSON-путь vs SQLite |
| `_count_words` | static (17532) | `docx_handler`, `statistics_analyzer` | 3 копии |
| `get_user_data_path` | верхний уровень (241) | `config_manager`, `prompt_library` | 3 копии |
| `_clean_provider_prefix` | (67093, zero-ref) | `translation_services.py` | монолит-копия мертва |
| `import_tmx` | метод | `tm_manager_qt` | дублирование |
| `main` | entry point | `llm_clients`, `tmx_editor` | ожидаемо (CLI) |

## 10.3 Legacy-границы

1. **Ribbon-кластер**: `create_quick_access_toolbar`, `create_ribbon`, `create_ribbon_toolbar`, `toggle_ribbon_minimized`, `show_ribbon_temporarily`, `on_main_tab_changed`(@13152) — `modules/ribbon_widget.py` импортируется только закомментированной строкой. Заменён `quick_access_sidebar`/меню.
2. **Compare-panel → match-panel/results_panels**: `create_assistance_panel`, `on_match_selected`, `update_compare_panel`, `_create_compare_panel`, `insert_compare_panel_mt/_tm_target`, `_add_mt_and_llm_matches`, `_REMOVED_…` (274L), `_copy_source_to_target_selected`.
3. **Старый TM-lookup**: `_schedule_delayed_lookup → _perform_delayed_lookup → search_and_display_tm_matches → create_diff_html → _fetch_llm/_fetch_mt_translation_async` — заменён `_show_instant_tm_match`/`_schedule_mt_and_llm_matches`/TMSearchWorker.
4. **Старый импорт TMX**: `import_tmx_file` + `_show_language_variant_dialog` (заменён `_import_tmx_as_tm`).
5. **tkinter-параллели**: `pdf_rescue_tkinter`, `find_replace`, `setup_wizard`, `prompt_library` (tkinter messagebox).
6. **Superseded-сервисы**: `glossary_manager` (→ termbase_manager/database_manager), `project_tm` (→ database_manager), `translation_services`, `extract_tm`, `tracked_changes` (комментарий «will be imported from the main file» — никогда), `feature_manager`, `identifier_conventions`, `voice_dictation`, `superdocs`+`superdocs_viewer_qt` (deprecated shims), `style_guide_manager`, `prompt_assistant`, `project_home_panel`, `quick_access_sidebar`, `ribbon_widget`.
7. **Stale-маркеры**: версии (1.10.313 / 1.10.371 / 2.5.0), ссылки на несуществующие CODE_MAP.md / UNDERSTANDING.md.

# 11. SuperLookup Analysis

`SuperlookupTab(QWidget)` — строки 67312–72548, **115 методов**, 5 237 строк. Ядро поиска уже вынесено в `modules/superlookup.py` (`SuperlookupEngine`, 256 строк, pure logic + pyperclip). Таб включает: поиск по TM/termbase/MT/веб-ресурсам (WebEngine), системные горячие клавиши (pynput/AHK/file-watcher), clipboard-capture, историю поиска, настройки.

**Автономность: средняя.** Класс самодостаточен по UI, но имеет **двустороннюю duck-typed связь с MainWindow**:
- Таб → MainWindow (~25 обращений через `self.main_window` + hasattr): `db_manager`, `termbase_mgr`, `tm_database`, `call_deepl`, `call_google_translate`, `call_custom_mt`, `create_llm_client`, `load_api_keys`, `_switch_main_tab`, `_bring_workbench_forward`, `table`, `current_project`, `theme_manager`, `_handle_clipboard_hotkey`, voice-хоткеи…
- MainWindow → Таб: `_ensure_superlookup_top_tab`, `_setup_superlookup_hotkeys`, `open_workbench_to_superlookup`, `_go_to_superlookup`, `show_concordance_search`, `_on_esc_quick_lookup_dismiss`.

Внутренние воркеры: `_SuperLookupSearchWorker(QRunnable)` + `_SuperLookupSearchSignals` (результаты через сигналы в `_on_search_tm_ready`/`_on_search_termbase_ready`/`_on_search_finished`). Глобальные хоткеи: pynput-колбэки → `QMetaObject.invokeMethod(self, "_handle_*_hotkey")` — **строковая диспетчеризация** (DYNAMIC_ENTRY_POINT).

| Method | Lines | LOC | Responsibility | Subsystem | Risk |
|---|---|---|---|---|---|
| `__init__` | 67317–67392 | 76 | Инициализация таба, hotkeys, история | A. Bootstrap/инициализация | LOW |
| `keyPressEvent` | 67394–67409 | 16 | Qt keyPressEvent | AE. События Qt/event filters | LOW |
| `showEvent` | 67411–67417 | 7 | Qt showEvent (ленивые языки) | AE. События Qt/event filters | LOW |
| `_delayed_language_population` | 67419–67450 | 32 | Отложенное заполнение языков | UI | LOW |
| `init_ui` | 67452–67596 | 145 | Сборка UI (145 строк) | UI | MEDIUM |
| `create_tm_results_tab` | 67598–67688 | 91 | Вкладка TM-результатов | UI | LOW |
| `create_termbase_results_tab` | 67690–67758 | 69 | Вкладка termbase-результатов | UI | LOW |
| `create_mt_results_tab` | 67760–67837 | 78 | Вкладка MT-результатов | UI | LOW |
| `_open_mt_settings` | 67839–67851 | 13 | Открыть MT-настройки через main_window | U. Настройки (UI) | MEDIUM |
| `_update_mt_provider_status` | 67853–67904 | 52 | Статус MT-провайдеров (через main_window) | UI | MEDIUM |
| `_perform_mt_lookup` | 67906–68019 | 114 | MT-lookup (main_window) | G. Поиск | MEDIUM |
| `_call_mymemory` | 68021–68059 | 39 | MyMemory запрос | G. Поиск | LOW |
| `create_web_resources_tab` | 68061–68555 | 495 | Вкладка веб-ресурсов (495 строк) | UI | MEDIUM |
| `_show_web_welcome_message` | 68557–68572 | 16 | Приветствие веб-вкладки | UI | LOW |
| `_create_web_view_for_resource` | 68574–68606 | 33 | Создание WebEngine-вью | UI | MEDIUM |
| `_create_web_view_container` | 68608–68754 | 147 | Контейнер веб-вью | UI | LOW |
| `_get_web_view_index` | 68756–68760 | 5 | Индекс веб-вью | UI | LOW |
| `_on_web_mode_changed` | 68762–68771 | 10 | Смена веб-режима | UI | LOW |
| `_update_web_view_for_mode` | 68773–68785 | 13 | Обновление вью по режиму | UI | LOW |
| `_on_web_resource_selected` | 68787–68827 | 41 | Выбор веб-ресурса | UI | LOW |
| `_update_web_lang_info` | 68829–68838 | 10 | Языковая инфо веб-вью | UI | LOW |
| `_schedule_lazy_web_views` | 68840–68865 | 26 | Ленивое создание веб-вью | UI | LOW |
| `_perform_web_search` | 68867–68981 | 115 | Веб-поиск (115 строк) | G. Поиск | MEDIUM |
| `search_all_web_resources` | 68983–68992 | 10 | Поиск по всем ресурсам | G. Поиск | LOW |
| `_build_web_search_url` | 68994–69078 | 85 | URL веб-поиска (85 строк) | G. Поиск | MEDIUM |
| `_on_opus_corpus_changed` | 69080–69089 | 10 | Смена корпуса Opus | UI | LOW |
| `_get_web_lang_code` | 69091–69207 | 117 | Код языка для веб-ресурса (117 строк) | G. Поиск | LOW |
| `_open_web_resource_external` | 69209–69219 | 11 | Открыть ресурс внешне | G. Поиск | LOW |
| `create_settings_tab` | 69231–69331 | 101 | Настройки SuperLookup | U. Настройки (UI) | LOW |
| `_load_superlookup_landing_pref` | 69333–69344 | 12 | Настройка стартовой вкладки | U. Настройки (UI) | LOW |
| `_on_landing_pref_changed` | 69346–69357 | 12 | Смена стартовой вкладки | U. Настройки (UI) | LOW |
| `create_mt_settings_subtab` | 69365–69394 | 30 | Сабтаб MT-настроек | U. Настройки (UI) | LOW |
| `create_web_settings_subtab` | 69396–69465 | 70 | Сабтаб веб-настроек | U. Настройки (UI) | LOW |
| `on_results_tab_changed` | 69467–69518 | 52 | Смена вкладки результатов | UI | LOW |
| `on_tm_search_toggled` | 69528–69531 | 4 | Toggle TM-поиска | U. Настройки (UI) | LOW |
| `on_termbase_search_toggled` | 69533–69536 | 4 | Toggle termbase-поиска | U. Настройки (UI) | LOW |
| `_on_web_resource_checkbox_changed` | 69538–69551 | 14 | Toggle веб-ресурса | U. Настройки (UI) | LOW |
| `refresh_tm_list` | 69553–69558 | 6 | Обновить список TM | K. Память переводов (TM) | LOW |
| `refresh_termbase_list` | 69560–69562 | 3 | Обновить список termbase | TERM | LOW |
| `get_selected_tm_ids` | 69564–69605 | 42 | Выбранные TM (через main_window) | K. Память переводов (TM) | MEDIUM |
| `get_search_direction` | 69607–69613 | 7 | Направление поиска | G. Поиск | LOW |
| `_on_language_changed` | 69615–69618 | 4 | Смена языка | UI | LOW |
| `get_language_filters` | 69620–69633 | 14 | Языковые фильтры | G. Поиск | LOW |
| `swap_language_filters` | 69635–69641 | 7 | Поменять языки местами | G. Поиск | LOW |
| `populate_language_dropdowns` | 69643–69741 | 99 | Заполнение языков (99 строк) | UI | MEDIUM |
| `_get_base_language_name` | 69743–69811 | 69 | Базовое имя языка | G. Поиск | LOW |
| `get_selected_termbase_ids` | 69813–69840 | 28 | Выбранные termbase (main_window) | TERM | MEDIUM |
| `__del__` | 69849–69854 | 6 | Деструктор: снятие hotkey | A. Bootstrap/инициализация | LOW |
| `capture_text` | 69856–69881 | 26 | Захват текста из буфера | G. Поиск | LOW |
| `perform_lookup` | 69883–70040 | 158 | Главный lookup (158 строк) | G. Поиск | MEDIUM |
| `_on_search_tm_ready` | 70042–70048 | 7 | TM-результаты worker | W. Воркеры/фоновые задачи | LOW |
| `_on_search_termbase_ready` | 70050–70056 | 7 | Termbase-результаты worker | W. Воркеры/фоновые задачи | LOW |
| `_on_search_finished` | 70058–70076 | 19 | Финиш worker | W. Воркеры/фоновые задачи | LOW |
| `search_with_query` | 70078–70112 | 35 | Поиск с готовым запросом | G. Поиск | LOW |
| `set_project_languages` | 70114–70139 | 26 | Установка языков проекта | UI | LOW |
| `_set_language_combo` | 70141–70164 | 24 | Установка комбо языков | UI | LOW |
| `toggle_tm_view_mode` | 70166–70175 | 10 | Режим отображения TM | UI | LOW |
| `display_tm_results` | 70177–70310 | 134 | Отображение TM-результатов (134 строки) | UI | MEDIUM |
| `_lang_base_name` | 70312–70333 | 22 | Базовое имя языка | G. Поиск | LOW |
| `_highlight_search_term` | 70335–70365 | 31 | Подсветка термина | UI | LOW |
| `_resize_html_cell_rows` | 70367–70397 | 31 | Высота HTML-ячеек | UI | LOW |
| `display_termbase_results` | 70399–70508 | 110 | Отображение termbase-результатов | UI | MEDIUM |
| `_show_termbase_result_context_menu` | 70510–70553 | 44 | Меню termbase-результатов | UI | LOW |
| `_navigate_to_termbase_entry` | 70555–70622 | 68 | Навигация к терму (main_window) | TERM | MEDIUM |
| `_select_first_term_in_table` | 70624–70635 | 12 | Выбор первого терма | TERM | LOW |
| `display_mt_results` | 70637–70696 | 60 | Отображение MT-результатов | UI | LOW |
| `_copy_mt_result` | 70698–70702 | 5 | Копирование MT-результата | UI | LOW |
| `on_mt_result_double_click` | 70704–70709 | 6 | Двойной клик MT | UI | LOW |
| `_tm_table_context_menu` | 70711–70752 | 42 | Меню TM-таблицы | UI | LOW |
| `_open_tm_entry_in_browser` | 70754–70792 | 39 | Открыть TM-запись (main_window) | K. Память переводов (TM) | MEDIUM |
| `on_tm_result_double_click` | 70794–70796 | 3 | Двойной клик TM | UI | LOW |
| `copy_selected_tm_target` | 70798–70806 | 9 | Копировать TM-перевод | UI | LOW |
| `insert_selected_tm_target` | 70808–70818 | 11 | Вставить TM-перевод | UI | LOW |
| `_init_search_history` | 70822–70841 | 20 | История поиска | AB. Персистентность (settings IO) | LOW |
| `_add_to_search_history` | 70843–70860 | 18 | Добавление в историю | AB. Персистентность (settings IO) | LOW |
| `_save_search_history` | 70862–70873 | 12 | Сохранение истории | AB. Персистентность (settings IO) | LOW |
| `clear_all` | 70875–70880 | 6 | Очистка всех полей | UI | LOW |
| `_normalize_language_code` | 70882–70889 | 8 | Нормализация кода языка | Прочие утилиты | LOW |
| `search_termbases` | 70896–71124 | 229 | Поиск termbase (229 строк, main_window) | TERM | HIGH |
| `copy_selected_termbase_target` | 71126–71134 | 9 | Копировать перевод терма | UI | LOW |
| `add_to_termbase` | 71136–71158 | 23 | Добавить в termbase | TERM | LOW |
| `show_add_term_dialog` | 71160–71287 | 128 | Диалог добавления терма (main_window) | TERM | MEDIUM |
| `set_tm_database` | 71289–71293 | 5 | Установка TM-базы | K. Память переводов (TM) | LOW |
| `_find_autohotkey_executable` | 71295–71326 | 32 | Поиск AutoHotkey | HOTKEY | LOW |
| `_show_autohotkey_setup_dialog` | 71328–71411 | 84 | Диалог установки AHK | HOTKEY | LOW |
| `_open_ahk_download` | 71413–71422 | 10 | Загрузка AHK | HOTKEY | LOW |
| `_browse_for_autohotkey` | 71424–71459 | 36 | Браузер AHK | HOTKEY | LOW |
| `register_global_hotkey` | 71461–71616 | 156 | Регистрация глобальных hotkey (156 строк) | HOTKEY | MEDIUM |
| `_on_pynput_superlookup` | 71618–71631 | 14 | pynput: Ctrl+Alt+L | HOTKEY | LOW |
| `_on_pynput_quicktrans` | 71633–71645 | 13 | pynput: Ctrl+Alt+Q | HOTKEY | LOW |
| `_on_pynput_clipboard` | 71647–71656 | 10 | pynput: Ctrl+Shift+C | HOTKEY | LOW |
| `_handle_clipboard_hotkey` | 71659–71794 | 136 | Обработка clipboard-hotkey (invokeMethod-цель) | HOTKEY | MEDIUM |
| `_open_clipboard_after_copy` | 71796–71860 | 65 | Открытие clipboard после копирования | HOTKEY | LOW |
| `_on_pynput_pushtotalk` | 71862–71872 | 11 | pynput: push-to-talk | HOTKEY | LOW |
| `_handle_pushtotalk_hotkey` | 71875–71907 | 33 | Обработка PTT | HOTKEY | LOW |
| `_on_pynput_alwayson_toggle` | 71909–71919 | 11 | pynput: always-on toggle | HOTKEY | LOW |
| `_on_pynput_command_ptt` | 71921–71936 | 16 | pynput: command PTT | HOTKEY | LOW |
| `_handle_alwayson_toggle_hotkey` | 71939–71955 | 17 | Обработка always-on toggle | HOTKEY | LOW |
| `_handle_command_ptt_press_hotkey` | 71958–71987 | 30 | Обработка command PTT | HOTKEY | LOW |
| `_try_ahk_library_method` | 71989–72056 | 68 | AHK library регистрация | HOTKEY | MEDIUM |
| `_register_hotkey_external_script` | 72058–72126 | 69 | AHK внешний скрипт | HOTKEY | MEDIUM |
| `start_file_watcher` | 72128–72140 | 13 | Watcher сигнальных файлов | HOTKEY | LOW |
| `check_for_signal` | 72142–72189 | 48 | Проверка сигналов AHK (таймер) | HOTKEY | LOW |
| `_handle_superlookup_hotkey` | 72192–72207 | 16 | invokeMethod-цель SuperLookup hotkey | HOTKEY | MEDIUM |
| `_read_clipboard_for_superlookup` | 72209–72231 | 23 | Буфер для SuperLookup | HOTKEY | LOW |
| `_handle_quicktrans_hotkey` | 72234–72266 | 33 | invokeMethod-цель QuickTrans hotkey | HOTKEY | MEDIUM |
| `_read_clipboard_for_quicktrans` | 72268–72280 | 13 | Буфер для QuickTrans | HOTKEY | LOW |
| `on_ahk_capture` | 72282–72314 | 33 | Захват AHK | HOTKEY | LOW |
| `on_ahk_mt_lookup_capture` | 72316–72326 | 11 | Захват AHK MT | HOTKEY | LOW |
| `show_mt_quick_lookup_from_ahk` | 72328–72384 | 57 | MT-lookup из AHK | HOTKEY | MEDIUM |
| `show_supervertaler_assistant` | 72386–72425 | 40 | Показ AI-ассистента (main_window) | UI | MEDIUM |
| `_paste_translation_to_external_app` | 72427–72465 | 39 | Вставка перевода во внешнее окно | HOTKEY | LOW |
| `set_compact_mode` | 72476–72481 | 6 | Компактный режим | UI | LOW |
| `show_superlookup` | 72483–72530 | 48 | Показ SuperLookup + поиск | G. Поиск | LOW |
| `_fill_and_search` | 72532–72548 | 17 | Заполнить и искать | G. Поиск | LOW |

**Вывод:** `modules/superlookup/` уже существует (engine). Следующий шаг — перенос `SuperlookupTab` + 4 helper-класса + hotkey-подсистемы туда, с явным интерфейсом вместо duck-typing (Protocol с ~12 методами). Связь с MainWindow сохранится (поиск по открытым TM/termbase), но станет декларированной.

# 12. Workers Analysis

## 12.1 QThread-воркеры монолита

| Класс | Строки | Зависимость от MainWindow | Сигналы | Извлекаемость |
|---|---|---|---|---|
| `TMSearchWorker` | 5333–5456 (до Batch #3b: 5908–6031, в документе ошибочно 7787–7910) | **нет** (чистые аргументы) | `results_ready(int,list)`, `search_failed(int,str)` → `_on_tm_search_results`/`_on_tm_search_failed` | **LOW** — готов к переносу |
| `ProofreadWorker` | 6168–6325 | нет (аргументы) | 5 сигналов → **локальные замыкания** в `_run_proofreading` | LOW |
| `GlossaryExtractionWorker` | 6336–6407 | нет | `finished_ok`, `failed` → замыкание | LOW |
| `PreTranslationWorker` | 5459–6165 | **ДА**: `self.parent_app` (читает `parent_app.current_project`, настройки) | `progress_update`, `translation_complete`, `translation_error`, `retry_needed` → замыкания | **HIGH** — сначала рефакторить на параметры |
| `LiveProgressDialog`, `_ImportProgressDialog` | перенесены в `modules/dialogs/` (Batch #3b) | нет | — | готово (Batch #3b) |
| `_SuperLookupSearchWorker(QRunnable)` + signals | 67211–67309 | через `tab` (SuperlookupTab) | 4 сигнала | MEDIUM (вместе с табом) |

## 12.2 threading.Thread/Timer-воркеры внутри SupervertalerQt

`_termbase_batch_worker_run` (индексация termbase, stop-event), `_prefetch_worker_run` (prefetch матчей), `_flush_tm_save_log_threadsafe` (threading.Timer), `_ping_ollama_keepwarm`, pynput-колбэки. Все завязаны на `self.*` состояние (`termbase_index_lock`, `translation_matches_cache`, `db_manager`) — извлекаются только вместе с TM/Termbase-сервисами.

## 12.3 Воркеры в modules/

`unified_prompt_manager_qt._AutoPromptWorker`, `local_llm_setup.ModelDownloadWorker/ConnectionTestWorker`, `tm_manager_qt.TMXImportThread/TMCleanupThread`, `statistics_analyzer.StatisticsWorker` (Qt-поток внутри logic-модуля), `voice_*` (VAD-потоки, poller'ы), `quicktrans.MTFetchWorker`, `voice_dictation_lite.QuickDictationThread`. Паттерн един: QThread + pyqtSignal; общего базового класса нет.

**Предложение:** `modules/workers/` реален, но **только для QThread-классов с чистыми аргументами** (TMSearchWorker, ProofreadWorker, GlossaryExtractionWorker — фаза 4). PreTranslationWorker требует сначала декомпозиции зависимостей. threading-воркеры монолита — не «воркеры», а методы сервисов (переносятся в фазах TM/termbase).

# 13. UI Analysis

## 13.1 Грид-редакторы и делегаты (переносимы в modules/grid/)

| Класс | Строки | Связь с MainWindow |
|---|---|---|
| `GridTextEditor` | 2902–3212 | `_get_main_window()` |
| `ReadOnlyGridTextEditor` | 3213–4797 (31 метод, 3 затенённых дубликата) | `_get_main_window()` + ~15 duck-typed методов |
| `TagHighlighter` | 4798–5125 | через редактор |
| `EditableGridTextEditor` | 5126–6760 (33 метода) | `_get_main_window()` + ~25 duck-typed методов |
| `SearchHighlightDelegate`, `WordWrapDelegate` | 6761–7189 | родитель-виджет |
| `TermbaseHighlightWidget`, `ClickableHighlightLabel`, `_SearchTermHighlighter`, `_NumericTableWidgetItem` | — | лёгкая |

## 13.2 Диалоги (modules/dialogs/, Batch #3b)
Все 6 диалогов перенесены в `modules/dialogs/` (Batch #3b): `theme_editor.py`, `detached_log.py`, `advanced_filters.py`, `scratchpad.py`, `live_progress.py`, `import_progress.py` + `__init__.py` (реэкспорт). До переноса находились в монолите на строках 5307–5901 (4 диалога; в документе ошибочно 7190–7786) и 6903–7206 (2 прогресс-диалога; в документе ошибочно 8782–9091). Все — без прямой зависимости от MainWindow (аргументы/parent), что подтверждено AST-инвентаризацией внешних имён перед переносом.

## 13.3 Event-фильтры (modules/event_filters.py)
После Batch #3a в `modules/event_filters.py`: `_QuitEventFilter`, `_LoneCtrlEventFilter`, `_WheelGuard`, `GridTableEventFilter`. В монолите остались `_CtrlReturnEventFilter` (676) и `_GridArrowKeyEventFilter` (728) — зависят от `ReadOnlyGridTextEditor`/`EditableGridTextEditor` и `_cleaned_modifiers`; переносятся после извлечения грид-редакторов. Принимают `mw`/`main_window` параметром (кроме _WheelGuard), логика компактная (2–5 методов).

## 13.4 Чекбоксы
`Pink/Blue/OrangeCheckmarkCheckBox`, `CustomRadioButton` (72559–72869, ~310 строк) — дублируют `modules/styled_widgets.py` (там CheckmarkCheckBox/Purple/Teal/CheckmarkRadioButton). При переносе — объединить с styled_widgets, а не создавать новый модуль.

# 14. Natural Module Boundaries

Границы следуют из данных: кластеры §5 + связки полей §6.3 + существующие modules/. **Никаких modules/utils.py или misc.py** — каждый хелпер уходит в подсистему, которой принадлежит.

| # | Модуль (предлагаемый) | Входит | Основание |
|---|---|---|---|
| 1 | `modules/models.py` | `Comment`, `Segment`, `Project` (26 классов-методов) | чистые данные, нулевые зависимости |
| 2 | `modules/tag_formatting.py` | ~30 топ-функций + `_strip_inline_tags`, `_raw_to_visible_offset`, `_wysiwyg_runs_to_tagged_text` + поглощение `tag_manager.py` | единый tag-движок, дублируется с modules |
| 3 | `modules/event_filters.py` | 3 фильтра + `GridTableEventFilter` (Batch #3a); 2 оставшихся — после извлечения грид-редакторов | компактные QObject-классы |
| 4 | `modules/grid/` (editors.py, delegates.py, render.py, pagination.py, filters.py, match_panel.py, helpers.py) | grid-редакторы, делегаты, ~120 методов `SupervertalerQt` (populate/render/pagination/filters/selection) | крупнейший кластер (GRID) |
| 5 | `modules/dialogs/` | 6 диалогов монолита | нулевая связность с окном |
| 6 | `modules/workers/` | TMSearchWorker, ProofreadWorker, GlossaryExtractionWorker (+ позже PreTranslationWorker после декомпозиции) | чистые QThread |
| 7 | `modules/undo_manager.py` | 7 undo/redo-методов + `undo_stack`/`redo_stack` | замкнутая подсистема |
| 8 | `modules/settings_service.py` | `_load/_save_settings_section`, `unified_settings`, языки, ключи, proxy (~25 методов) | fan-in до 48 — высокое переиспользование |
| 9 | `modules/tm_service.py` + `tm_controller` | initialize/save/invalidate/sync + TM-вкладка | кластер TM |
| 10 | `modules/termbase_service.py` + `termbase_tab` | индексация/поиск/добавление + вкладка 1277L | кластер TERMBASE |
| 11 | `modules/import_controller.py` / `export_controller.py` | ~25 + ~25 методов форматов | кластеры IMPORT/EXPORT/CAT |
| 12 | `modules/translation_service.py` + `mt_providers.py` | `call_*` провайдеры, профили, `translate_batch`/`translate_current_segment` (позже) | кластеры TRANSL/LLM |
| 13 | `modules/find_replace_controller.py` | 17 методов поиска/замены | замкнутый кластер |
| 14 | `modules/comments_ui.py` | ~15 методов комментариев/proofreading-заметок | кластер + цикл SCC#1 |
| 15 | `modules/superlookup/` (расширение существующего) | `SuperlookupTab` + 5 helper-классов + hotkeys | §11 |
| 16 | `modules/images_tab.py` | вкладка извлечения картинок (~15 методов) | самодостаточная фича |
| 17 | `modules/voice_controller.py` | always-on/PTT/диктовка (~30 методов) | кластер VOICE |
| 18 | `modules/menus_factory.py` | `create_menus` (890L) | чистая фабрика |
| 19 | `modules/update_checker.py` | `check_for_updates` + 4 хелпера | изолированная сеть |
| 20 | `modules/okapi_controller.py` | sidecar-управление (5 методов) | изолированный процесс |
| 21 | `modules/stats_controller.py` | 6 методов статистики | существующий statistics_dialog_qt |
| 22 | `modules/tray_controller.py` | tray-иконка/quit (6 методов) | компактная подсистема |
| 23 | `modules/shortcuts_wiring.py` | `setup_global_shortcuts`, reload, refresh | реестр хоткеев |
| 24 | `modules/preview_controller.py` | 12 методов предпросмотра | кластер preview |

# 15. Proposed Target Architecture

```
Supervertaler.py            ~12–15k строк: imports, bootstrap, main(), SupervertalerQt(QMainWindow)
                            — только: окно, вкладки, меню-wiring, маршрутизация сигналов к сервисам
modules/
├── models.py               данные проекта (Segment/Project/Comment)
├── tag_formatting.py       DOCX-теги (объединить с существующим tag_manager)
├── event_filters.py        системные фильтры
├── settings_service.py     персистентность настроек (единая точка)
├── project_service.py      .svproj IO, недавние, бэкапы
├── undo_manager.py         undo/redo (сегментный + структурный)
├── search_service.py       поиск/подсветка/конкорданс
├── tm_service.py           TM-операции (над database_manager)
├── termbase_service.py     termbase-операции (над database_manager)
├── translation_service.py  LLM/MT-диспетчер (+mt_providers.py)
├── import_controller.py    импорт форматов (переиспользует *_handler)
├── export_controller.py    экспорт форматов
├── okapi_controller.py     sidecar
├── update_checker.py, tray_controller.py, shortcuts_wiring.py, menus_factory.py
├── workers/                TMSearchWorker, ProofreadWorker, GlossaryExtractionWorker, (PreTranslationWorker)
├── dialogs/                ThemeEditor, AdvancedFilters, Scratchpad, LiveProgress, ImportProgress, DetachedLog
├── grid/                   editors, delegates, render, pagination, filters, match_panel, helpers
├── comments_ui.py          комментарии/proofreading-заметки
├── images_tab.py, voice_controller.py, superlookup/ (tab + hotkeys)
├── quicktrans_controller.py, termlens_controller.py
└── (существующие 115 модулей — без изменений; orphans помечены, не удаляются)
```

Правила миграции (из реальной архитектуры): (1) `modules/` не импортирует `Supervertaler.py` — сохранить; (2) связь MainWindow↔сервисы — явные параметры + интерфейсы (Protocol) вместо duck-typing; (3) переиспользовать существующие модули, не создавать дубликаты (checkwidgets → styled_widgets, tag engine → tag_manager); (4) один шаг = одна подсистема + прогон smoke-тестов.

# 16. Extraction Candidates

| Кандидат | Методов | ~LOC | Существующий модуль для переиспользования | Риск |
|---|---|---|---|---|
| Модели данных (Comment/Segment/Project) | 26 | ~630 | — | LOW |
| Топ-функции tag-движка | ~30 | ~1 300 | `modules/tag_manager.py` | LOW |
| Event-фильтры | 6 классов | ~500 | — | LOW |
| Диалоги | 6 классов | ~600 | `modules/dialogs` (новый пакет) | LOW |
| Чистые воркеры (TMSearch/Proofread/Glossary) | 3 класса | ~400 | `modules/workers` | LOW |
| Undo-менеджер | 7 | ~200 | — | LOW |
| Grid: helpers/pagination/filters | ~45 | ~2 500 | — | MEDIUM |
| Grid: render (populate/status/colors) | ~25 | ~2 000 | — | MEDIUM |
| Grid: editors/delegates/highlighter | 6 классов | ~2 000 | — | MEDIUM |
| Match/compare panel | ~18 | ~1 400 | — | MEDIUM |
| Preview | 12 | ~900 | — | MEDIUM |
| Comments UI | ~15 | ~1 100 | — | MEDIUM |
| Settings tabs (builders) | ~30 | ~5 500 | `modules/settings_sidebar` | MEDIUM-HIGH |
| Settings service (IO) | ~25 | ~800 | `modules/config_manager` | MEDIUM |
| Checkwidgets → styled_widgets | 4 класса | ~310 | `modules/styled_widgets.py` | LOW |
| Images tab | ~15 | ~1 000 | `modules/image_extractor.py` | MEDIUM |
| Voice controller | ~30 | ~2 300 | `modules/voice_tab`, `voice_commands` | MEDIUM-HIGH |
| Update checker | 6 | ~600 | — | LOW |
| Menus factory | 1 | 890 | — | MEDIUM |
| Import/Export контроллеры | ~50 | ~6 000 | `*_handler.py` (переиспользуются как есть) | HIGH |
| TM controller/service | ~20 | ~2 500 | `tm_manager_qt`, `tm_metadata_manager`, `translation_memory` | HIGH |
| Termbase service/tab | ~25 | ~3 000 | `termbase_manager`, `termbase_entry_editor` | HIGH |
| Translation core (batch/current) | ~15 | ~2 800 | `llm_clients`, `translation_services` | VERY_HIGH |
| SuperLookup tab | 115 + 5 классов | ~5 700 | `modules/superlookup.py` | MEDIUM-HIGH |
| Find&Replace controller | 17 | ~1 300 | `modules/find_replace_qt.py` | MEDIUM |

# 17. Extraction Order

Порядок выведен из графа зависимостей: сначала то, что ничего не импортирует из класса; затем листовые подсистемы; связь с MainWindow — через параметры; каждый шаг — один коммит/проверка.

| Фаза | Содержимое | Риск | Проверка после шага |
|---|---|---|---|
| 0 | Инвентаризация dead-code (этот аудит); пометить `# AUDIT: dead-candidate` — НЕ удалять | — | diff-хэши .py |
| 1 | `models.py` + `tag_formatting.py` (топ-функции; monolith продолжает импортировать) | LOW | запуск, импорт проекта, экспорт DOCX |
| 2 | `event_filters.py` + `dialogs/` | LOW | закрытие окна, tray, Esc, scratchpad, тема |
| 3 | Чистые воркеры → `workers/` (TMSearch, Proofread, Glossary) | LOW | TM-поиск, proofread, извлечение терминов |
| 4 | `undo_manager.py` + checkwidgets → `styled_widgets` | LOW | undo/redo, чекбоксы UI |
| 5 | `grid/helpers`, `pagination`, `filters` (чистые вычисления над table) | MEDIUM | пагинация, фильтры, сортировка, невидимые |
| 6 | `settings_service.py` (IO-слой настроек; UI-билдеры остаются) | MEDIUM | цикл настроек: изменить→перезапуск→проверка |
| 7 | `grid/render.py` + `match_panel.py` + `comments_ui.py` | MEDIUM-HIGH | открытие проекта, выбор ячеек, матчи, комментарии |
| 8 | `dialogs`-зависимые фичи: `images_tab`, `stats_controller`, `update_checker`, `tray_controller`, `okapi_controller` | MEDIUM | соответствующие меню |
| 9 | `find_replace_controller.py` + `preview_controller.py` | MEDIUM | F&R все режимы, preview |
| 10 | `import_controller`/`export_controller` (формат-за-форматом, малыми шагами) | HIGH | импорт/экспорт каждого формата |
| 11 | `tm_service`/`termbase_service` (с воркерами-потоками) | HIGH | TM/termbase полные сценарии |
| 12 | `voice_controller`, `superlookup/` | MEDIUM-HIGH | голосовые сценарии, SuperLookup hotkeys |
| 13 | `translation_service` + `translate_batch/current` | VERY_HIGH | перевод сегмента, batch, retry, fuzzy fix |
| 14 | Финальный cleanup MainWindow (меню → menus_factory, удаление помеченного dead после явного одобрения) | MEDIUM | полный smoke |

# 18. Risks

1. **Нет тестов и git-истории** — единственная защита: hash-контроль, AST-проверки и ручной smoke-список. Перед фазой 1 настоятельно рекомендуется `git init` + эталонный запуск.
2. **Двойные определения** (`closeEvent`, `show_about`, 3 в ReadOnlyGridTextEditor): при переносе легко перенести не то определение. Правило: переносить только последнее (живое), первое фиксировать как dead.
3. **Строковая диспетчеризация**: `QMetaObject.invokeMethod(self, "_handle_*_hotkey")` (3 метода) и duck-typed getattr/hasattr (~77 hasattr-имён, 119 duck-typed атрибутов) — при переименовании/переносе эти имена ломаются молча. Список — в wiring.json `per_method`.
4. **Замыкания вместо методов**: обработчики proofread/pretranslate/glossary — локальные closures (51330–51370, 64435–64438, 65258–65261, 21930) — при переносе воркеров переносить вместе с местом старта.
5. **Цикл SCC#1 (грид↔комментарии↔навигация, 15 методов)** — нельзя резать по файлам без выделения controller-слоя.
6. **PreTranslationWorker держит `parent_app`** — прямой перенос изменит поведение (обращения к живому состоянию окна из потока).
7. **Ленивые импорты (243 `from modules` внутри методов)** — перенос метода тянет его импорты; сборка может зависеть от порядка инициализации (PyQt6 auto-install try/except в шапке).
8. **Глобальные hotkeys/трей/pynput** живут в двух местах (MainWindow `_get_voice_hotkey_listener` + SuperLookupTab `register_global_hotkey`) — риск двойной регистрации.
9. **settings-фанатом**: `load_general_settings` вызывается 48 методами и перечитывает файл с диска — вынос IO должен сохранить семантику перечитывания, иначе поведение изменится.
10. **19 orphan-модулей** могут использоваться внешними инструментами (Trados-плагин идёт через bridge, а не импорт) — не удалять без отдельного подтверждения.

# 19. Questions / Unknowns

1. Используются ли orphan-модули (`extract_tm`, `feature_manager`, `translation_services`, `tracked_changes`…) внешними скриптами/пользователями вне репозитория? Статический анализ: нет. Требуется подтверждение владельца.
2. `Supervertaler_tkinter.py`, упомянутый в докстринге, — существует ли отдельный репозиторий, с которым нужно сохранять паритет (duplicate-политика)?
3. `_show_setup_wizard` импортирует tkinter-`setup_wizard.py`? (orphan-модуль в modules/) — проверяется при исполнении фазы 8; dynamic usage не исключён.
4. Поведение затёртого `closeEvent@33453` (tray-minimize) — является ли его молчаливое отключение намеренным? (второй closeEvent его полностью замещает).
5. `_REMOVED_add_mt_and_llm_matches_progressive` (274L) и `_add_mt_and_llm_matches` (188L) — история говорит «заменено прогрессивным путём»; подтверждение на удаление — за владельцем.
6. Замыкания-обработчики воркеров содержат бизнес-логику (retry-политики translate_batch) — при выносе translation-ядра их придётся именовать; текущий аудит не может оценить покрытие поведенческих нюансов без runtime-тестов.
7. Динамические вызовы через переменные (bound-methods, сохранённые в локальные переменные) не покрыты AST-анализом вызовов; 16 методов с нулём вызовов проверены дополнительно grep'ом, но для методов-«передаваемых как объект» осталось низкое остаточное затруднение: `_widget_is_alive` (передаётся ли как callable?), `update_progress_stats` — используются только как вызовы.

---

# ARCHITECTURE AUDIT VERDICT

**1. Насколько реально уменьшить Supervertaler.py без изменения поведения?**
С 73 337 строк до ~12–15k (−80%): 819 методов распределяются так: {n_dead} уже мёртвые/legacy, ~{n_modules_dest} переносимы в modules/ (классы-компоненты и подсистемы), ядро окна оставляет ~{n_core} методов-контроллеров. Первые ~40% объёма уходят без изменения поведения вообще (классы верхнего уровня, чистые воркеры, settings-IO).

**2. Первые LOW-RISK кандидаты:** модели (Comment/Segment/Project), tag-движок (топ-функции), event-фильтры, 6 диалогов, чистые воркеры (TMSearch/Proofread/Glossary), undo, checkwidgets→styled_widgets.

**3. Что не трогать в начале:** `translate_batch`/`translate_current_segment`/`_on_cell_selected_full`/`force_refresh_matches` (перевод-ядро), `load_project`/`save_project_to_file`, SCC#1 (грид↔комментарии), `__init__`/`create_main_layout`/`create_menus`, `log` (fan-in 359), threading-воркеры termbase/prefetch (тянут кэши), duck-typed контракты с 14 модулями.

**4. Главные hotspots:** `translate_batch` (833L), `_on_cell_selected_full` (617L), `create_grid_view_widget_for_home` (884L), `create_termbases_tab` (1277L), `create_menus` (890L), `_create_ai_settings_tab` (1046L), `load_project` (547L), `export_target_only_docx` (441L), `show_find_replace_dialog` (353L), `force_refresh_matches` (286L).

**5. Бизнес-логика (переносится в сервисы):** confirm/propagate/auto-confirm, замены F&R, termbase-индексация/синонимы, TM-save/синк, импорт-валидация/реимпорт, экспорт-подсчёт слов, статистика.

**6. Чисто UI:** builders вкладок (settings/termbases/TM/images), меню, статус-бар/прогресс, темы/шрифты, зум, tray, диалоги, предпросмотр.

**7. File/document processing:** импорт ×12 форматов, экспорт ×10, DOCX-теги/комментарии, Okapi sidecar, TMX, review-таблицы.

**8. Translation/TM/termbase/LLM:** `translate_*`, `call_*` (6 провайдеров), TMSearchWorker, instant/MT/LLM-матчи, `_save_segment_to_activated_tms`, `_import_tmx_as_tm`, `_build_termbase_index`, `_quick_add_term_with_priority`, term extraction.

**9. Уже фактически модули внутри MainWindow:** undo-менеджер, find/replace-движок, пагинация+фильтры грида, comments-UI, preview, settings-IO, tray, update-checker, quicklauncher, voice-PTT-машинка, SuperLookup-hotkeys, images-вкладка.

**10. Существующие modules/ для повторного использования:** `styled_widgets` (вместо дубля чекбоксов), `tag_manager` (поглотить tag-движок), `config_manager` (settings), `find_replace_qt` (данные F&R), `termbase_manager`/`termbase_entry_editor`/`termbase_import_export` (терминология), `tm_manager_qt`/`tm_metadata_manager`/`translation_memory`/`tmx_generator` (TM/TMX), `llm_clients`/`translation_services` (LLM), `image_extractor`, `statistics_dialog_qt`+`statistics_analyzer`, `superlookup`, `platform_helpers`, `help_system`, `statuses`, `language_codes`, все `*_handler`.

**11. Циклические риски:** import-циклов нет (modules не импортируют монолит). Runtime-циклы: SCC#1 грид↔комментарии (15), voice-PTT (6), recent-проекты (6), auto-confirm (2), proofreading (2). При выносе comments_ui/грида цикл рвётся через события/callback-интерфейс.

**12. Самые убедительные кандидаты на удаление (после отдельного одобрения):** 51 zero-ref метод (все проверки пройдены: connect/lambda/timer/shortcut/thread/getattr/invokeMethod/duck-typed/override/property), затенённые дубли (`show_about@62004`, `closeEvent@33453`, 3 метода ReadOnlyGridTextEditor), ribbon-кластер (единственные вызовы закомментированы), legacy-цепочка delayed-lookup (5 методов), `_REMOVED_*` (274L).

**13. Первый extraction batch (рекомендация):** Phase 1 — `modules/models.py` (Comment/Segment/Project) + `modules/tag_formatting.py` (30 топ-функций) с сохранением совместимости: монолит импортирует их, имена остаются (`from modules.models import Segment` алиасы). Ноль поведенческих рисков, −1 900 строк.

**14. Второй batch:** Phase 2–3 — event-фильтры + диалоги + чистые воркеры в `modules/{event_filters,dialogs,workers}/` (−1 500 строк, 15 классов).

**15. Порядок минимального риска:** §17 — «снаружи внутрь»: данные → чистые компоненты → сервисы-IO → грид/UI → форматы → TM/termbase → перевод-ядро последним; каждый шаг с hash/AST/smoke-проверками (§23 ТЗ выполнен в EXTRACTION_PLAN.md).

**16. Конечная архитектура:** §15 — `Supervertaler.py` = bootstrap + `SupervertalerQt(QMainWindow)` (окно/вкладки/маршрутизация, ~12–15k строк); `modules/` — доменные сервисы + UI-пакеты (grid/, dialogs/, workers/, superlookup/); зависимости однонаправленные MainWindow→modules, контракты — явные Protocol вместо duck-typing.

---

*Отчёт создан автоматизированным аудитом (AST + динамическая карта вызовов + ручная классификация каждого метода). Ни один .py-файл не был изменён; проверка — SHA256-снимок до/после (см. финальное сообщение).*
