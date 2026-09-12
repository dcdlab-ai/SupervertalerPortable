# DEPENDENCY_MAP.md
**Проект:** Supervertaler — карта зависимостей для декомпозиции
**Дата:** 2026-09-12 • Метод: AST-парсинг всех 120 файлов (Supervertaler.py + modules/ + scripts/ + tools/), включая ленивые импорты внутри методов и ветки try/except/orelse

---

# 1. Обзор

| Направление | Факт |
|---|---|
| `Supervertaler.py` → `modules.*` | 243 import-выражения (многие ленивые, внутри методов), 163 уникальных имени, 128 классов/функций инстанцируются в 513 местах |
| `modules.*` → `Supervertaler.py` | **0 прямых импортов** (правило «modules/ must not import from Supervertaler.py» зафиксировано в `modules/voice_command_dialog.py:3-5`) |
| `modules.*` ↔ `modules.*` | ~60 внутренних связей; крупнейший потребитель — `unified_prompt_manager_qt` (11 внутренних зависимостей) |
| Циклы импортов | **Не обнаружены** (проверено AST-графом всех файлов) |
| Duck-typed контракты MainWindow | **14 модулей** получают `parent_app`/`main_window`/`self` |
| scripts/, tools/ → modules | **0** (полностью автономны) |

Обратные зависимости `modules → MainWindow` существуют ТОЛЬКО в duck-typed форме (инжектируемые объекты) — это главный источник хрупкости при extraction, т.к. интерфейсы не декларированы.

# 2. MainWindow (SupervertalerQt) → modules.*

Модули, используемые классом `SupervertalerQt` (суммарно 58): `autocorrect`, `bilingual_markdown_handler`, `cafetran_docx_handler`, `clipboard_manager_widget`, `database_manager`, `dejavurtf_handler`, `dictation_toast`, `docx_comments`, `docx_handler`, `figure_context_manager`, `i18n`, `image_extractor`, `keyboard_shortcuts_widget`, `lang_detect`, `language_codes`, `llm_clients`, `local_llm_setup`, `memoqrtf_handler`, `merge_prompt_dialog`, `mqxliff_handler`, `okapi_sidecar`, `pdf_rescue_Qt`, `phrase_docx_handler`, `platform_helpers`, `po_handler`, `quicktrans`, `sdlppx_handler`, `sdltm_handler`, `settings_sidebar`, `simple_segmenter`, `statistics_dialog_qt`, `statuses`, `styled_widgets`, `superbrowser`, `supervertaler_bridge_server`, `term_picker_dialog`, `termbase_entry_editor`, `termbase_import_export`, `termbase_manager`, `termlens_popup`, `termlens_widget`, `theme_manager`, `tm_editor_dialog`, `tm_manager_qt`, `tm_metadata_manager`, `tmx_editor_qt`, `tmx_generator`, `trados_docx_handler`, `translation_memory`, `translation_results_panel`, `ui_scale`, `unified_prompt_manager_qt`, `usage_report_dialog`, `usage_statistics`, `voice_hotkey_listener`, `voice_release_poller`, `voice_tab`, `voice_vocabulary`

Топ использования: `CheckmarkCheckBox` ×128, `format_shortcut_for_display` ×59, `CheckmarkRadioButton` ×42, `TranslationMatch` ×27, `set_help_topic` ×16, `LLMClient` ×14, `get_status` ×14, `open_help` ×9, `StandaloneSDLXLIFFHandler` ×6, `SimpleSegmenter` ×6, `CrossPlatformKeySender` ×6, `TMXGenerator` ×5, `TermbaseEntryEditor` ×4, `MQXLIFFHandler` ×4, `CafeTranDOCXHandler` ×4, `DatabaseManager` ×3, `ThemeManager` ×2, `ShortcutManager` ×2, `VoiceCommandManager` ×2, `TermLensWidget` ×2, `UnifiedPromptManagerQt` ×2 (и ~100 одноразовых).

Ключевые инжекции объектов MainWindow в модули: `UnifiedPromptManagerQt(self)`, `VoiceTab(self)`, `VoiceCommandManager(path, main_window=self)`, `TranslationResultsPanel(tabs, parent_app=self)`, `ClipboardManagerWidget(parent_app)`, `QuickTransPanel/MTQuickPopup(parent_app)`, `ChatBackend(parent_app)`, `PDFRescueQt(parent_app)`, `install(main_window)` (help_system), `run_pseudo_translation(main_window)`.

# 3. modules → MainWindow (duck-typed, обратная зависимость)

| Модуль | Механизм связи | Используемый интерфейс MainWindow | Coupling |
|---|---|---|---|
| modules/unified_prompt_manager_qt.py | конструируется как UnifiedPromptManagerQt(self) — самый тесный контракт | высокая |
| modules/quicktrans.py | parent_app во всех 5 классах: load_api_keys, load_llm_settings, create_llm_client, call_custom_mt, set_quicktrans_direction_override, open_workbench_to_superlookup | высокая |
| modules/voice_commands.py | main_window= kwarg; hasattr-вызовы ~15 методов (go_to_next_segment, split_current_segment, save_grid_segment, copy_source_to_grid_target…) | высокая |
| modules/voice_tab.py | VoiceTab(parent_app); контракт задокументирован в docstring; _reset_voice_commands, _populate_voice_commands_table, save_voice_vocabulary_settings, open_termbases_tab | высокая |
| modules/translation_results_panel.py | TranslationResultsPanel(tabs, parent_app=self) (Supervertaler.py:32547); log/настройки/вставка | высокая |
| modules/clipboard_manager_widget.py | ClipboardManagerWidget(parent_app, paste_text_callback); _clipboard_prior_workbench_tab | средняя |
| modules/chat_view_widget.py | self._get_parent_app() — обход Qt-родителей; load_api_keys, load_llm_settings, _get_proxy_url | средняя |
| modules/chat_backend.py | ChatBackend(parent_app): load_api_keys, current_provider, create_llm_client, _get_proxy_url | средняя |
| modules/keyboard_shortcuts_widget.py | self.main_window=parent; refresh_shortcut_enabled_states (hasattr), _find_autohotkey_for_settings | средняя |
| modules/help_system.py | install(main_window) — глобальный event filter приложения | низкая |
| modules/pseudo_translate_dialog.py | run_pseudo_translation(main_window): current_project, table, get_selected_segments_from_grid | средняя |
| modules/pdf_rescue_Qt.py | PDFRescueQt(parent_app): log, api_keys, load_api_keys | средняя |
| modules/ai_actions.py | AIActionSystem(parent_app=…): current_project | низкая |
| modules/pdf_rescue_tkinter.py | PDFRescue(parent_app): root — ORPHAN | — |

Плюс внутренние duck-typed ссылки внутри монолита (не modules, но та же проблема):
- `SuperlookupTab` → MainWindow: ~25 атрибутов через `self.main_window` + hasattr (`db_manager`, `termbase_mgr`, `call_deepl`, `call_google_translate`, `call_custom_mt`, `create_llm_client`, `load_api_keys`, `_switch_main_tab`, `_bring_workbench_forward`, `_handle_clipboard_hotkey`…).
- `ReadOnlyGridTextEditor`/`EditableGridTextEditor`/`GridTextEditor` → MainWindow через `_get_main_window()`: ~30 атрибутов (`confirm_selected_or_next`, `save_grid_segment`, `copy_source_to_grid_target`, `clear_grid_target`, `open_quicklauncher`, `show_term_insert_popup`…).
- Event-фильтры → MainWindow через параметр `mw`.
- `get_translator_name`, `update_warning_banner`, `get_autocorrect_settings` и др. вызываются из вложенных классов.

# 4. Полная таблица: модуль → зависимости (→ кого импортирует)

| Модуль | Third-party | modules (top-level) | modules (lazy) | Импортируют его |
|---|---|---|---|---|
| `ai_actions` | — | — | — | unified_prompt_manager_qt |
| `ai_attachment_manager` | — | — | — | unified_prompt_manager_qt |
| `ai_file_viewer_dialog` | PyQt6 | — | — | unified_prompt_manager_qt |
| `autocorrect` | — | — | — | Supervertaler |
| `autostart` | — | — | — | Supervertaler |
| `batch_offload` | — | — | llm_clients, sdlppx_handler, tmx_generator | Supervertaler |
| `bilingual_markdown_handler` | — | — | language_codes | Supervertaler |
| `cafetran_docx_handler` | docx | — | — | Supervertaler |
| `chat_backend` | PyQt6 | modules.llm_clients, modules.llm_pricing, usage_log | — | chat_view_widget, unified_prompt_manager_qt |
| `chat_message_delegate` | PyQt6 | — | — | chat_view_widget |
| `chat_view_widget` | PyQt6 | modules.chat_backend, modules.chat_message_delegate, modules.trados_bridge_client | llm_clients | unified_prompt_manager_qt |
| `clipboard_manager_widget` | PyQt6 | modules.help_system, modules.styled_widgets, modules.ui_scale | platform_helpers, snippet_library, text_conversion_library | Supervertaler |
| `config_manager` | — | — | — | file_dialog_helper, setup_wizard |
| `database_manager` | — | — | language_codes, database_migrations, tmx_generator | Supervertaler, database_migrations, tmx_editor_qt, translation_memory |
| `database_migrations` | — | — | database_manager | database_manager |
| `dejavurtf_handler` | — | — | — | Supervertaler |
| `dictation_toast` | PyQt6 | — | — | Supervertaler |
| `document_analyzer` | — | — | — | unified_prompt_manager_qt |
| `docx_comments` | — | — | — | Supervertaler |
| `docx_handler` | — | — | .tag_manager, tag_manager | Supervertaler |
| `extract_tm` | — | — | — | ORPHAN |
| `feature_manager` | — | — | — | ORPHAN |
| `figure_context_manager` | — | — | — | Supervertaler, unified_prompt_manager_qt |
| `file_dialog_helper` | PyQt6 | modules.config_manager | — | Supervertaler |
| `find_replace` | — | — | — | ORPHAN |
| `find_replace_qt` | PyQt6 | — | — | Supervertaler |
| `glossary_manager` | — | — | — | ORPHAN |
| `help_system` | PyQt6 | — | — | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget, statistics_dialog_qt, styled_widgets, term_picker_dialog |
| `i18n` | PyQt6 | — | — | Supervertaler |
| `identifier_conventions` | — | — | — | ORPHAN |
| `image_extractor` | PIL | — | — | Supervertaler |
| `keyboard_shortcuts_widget` | PyQt6 | modules.help_system, modules.platform_helpers, modules.shortcut_display, modules.shortcut_manager, modules.styled_widgets, modules.ui_scale | — | Supervertaler |
| `lang_detect` | — | — | — | Supervertaler, quicktrans |
| `language_codes` | — | — | — | Supervertaler, bilingual_markdown_handler, database_manager, tmx_generator |
| `llm_clients` | — | — | usage_log | Supervertaler, batch_offload, chat_backend, chat_view_widget, quicktrans, translation_services |
| `llm_pricing` | — | — | — | chat_backend, usage_log |
| `local_llm_setup` | PyQt6 | modules.platform_helpers | — | Supervertaler |
| `memoqrtf_handler` | — | — | — | Supervertaler |
| `merge_prompt_dialog` | PyQt6 | — | — | Supervertaler |
| `mic_devices` | — | — | — | voice_commands, voice_dictation_lite, voice_tab |
| `mqxliff_handler` | — | — | — | Supervertaler |
| `okapi_sidecar` | — | — | — | Supervertaler |
| `pdf_rescue_Qt` | PyQt6, docx, fitz | modules.platform_helpers, modules.styled_widgets | — | Supervertaler |
| `pdf_rescue_tkinter` | docx, fitz, openai | modules.platform_helpers | — | ORPHAN |
| `phrase_docx_handler` | docx, lxml | — | — | Supervertaler |
| `platform_helpers` | — | — | — | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget, local_llm_setup, pdf_rescue_Qt, pdf_rescue_tkinter |
| `po_handler` | — | — | — | Supervertaler |
| `project_assets` | — | — | — | Supervertaler |
| `project_home_panel` | PyQt6 | — | — | ORPHAN |
| `project_tm` | — | — | — | ORPHAN |
| `prompt_assistant` | — | — | — | ORPHAN |
| `prompt_library` | — | — | — | ORPHAN |
| `prompt_library_migration` | — | — | — | unified_prompt_manager_qt |
| `pseudo_translate` | — | — | — | pseudo_translate_dialog |
| `pseudo_translate_dialog` | PyQt6 | modules.pseudo_translate, modules.styled_widgets | — | Supervertaler |
| `quick_access_sidebar` | PyQt6 | — | — | ORPHAN |
| `quicktrans` | PyQt6 | — | lang_detect, llm_clients | Supervertaler |
| `ribbon_widget` | PyQt6 | modules.shortcut_display | — | ORPHAN |
| `sdlppx_handler` | — | — | — | Supervertaler, batch_offload |
| `sdltm_handler` | — | — | — | Supervertaler |
| `segment_split_merge` | — | — | — | Supervertaler |
| `settings_sidebar` | PyQt6 | — | — | Supervertaler |
| `setup_wizard` | — | modules.config_manager | — | ORPHAN |
| `shortcut_display` | — | — | — | Supervertaler, keyboard_shortcuts_widget, ribbon_widget, shortcut_manager, termlens_widget, tmx_editor |
| `shortcut_manager` | PyQt6 | modules.shortcut_display | — | Supervertaler, keyboard_shortcuts_widget |
| `simple_segmenter` | — | — | — | Supervertaler |
| `snippet_library` | — | — | — | clipboard_manager_widget |
| `spellcheck_manager` | — | — | — | Supervertaler |
| `statistics_analyzer` | PyQt6 | — | — | statistics_dialog_qt |
| `statistics_dialog_qt` | PyQt6 | modules.help_system, modules.statistics_analyzer, modules.styled_widgets | — | Supervertaler |
| `statuses` | — | — | — | Supervertaler |
| `style_guide_manager` | — | — | — | ORPHAN |
| `styled_widgets` | PyQt6 | — | help_system | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget, pdf_rescue_Qt, pseudo_translate_dialog, statistics_dialog_qt |
| `superbrowser` | PyQt6 | — | — | Supervertaler |
| `superdocs` | — | — | — | ORPHAN |
| `superdocs_viewer_qt` | — | — | — | ORPHAN |
| `superlookup` | pyperclip | — | platform_helpers | Supervertaler |
| `supervertaler_bridge_server` | PyQt6 | — | — | Supervertaler |
| `tag_manager` | — | — | — | docx_handler |
| `term_picker_dialog` | PyQt6 | — | help_system | Supervertaler |
| `termbase_entry_editor` | PyQt6 | modules.styled_widgets | termbase_manager | Supervertaler, translation_results_panel |
| `termbase_import_export` | — | — | — | Supervertaler |
| `termbase_manager` | — | — | — | Supervertaler, termbase_entry_editor |
| `termlens_popup` | PyQt6 | — | help_system, termlens_widget | Supervertaler |
| `termlens_widget` | PyQt6 | modules.shortcut_display | help_system | Supervertaler, termlens_popup |
| `text_conversion_library` | yaml | — | — | clipboard_manager_widget |
| `theme_manager` | PyQt6 | — | — | Supervertaler |
| `tm_editor_dialog` | PyQt6 | modules.tm_manager_qt | tm_metadata_manager | Supervertaler |
| `tm_manager_qt` | PyQt6 | — | — | Supervertaler, tm_editor_dialog |
| `tm_metadata_manager` | — | — | — | Supervertaler, tm_editor_dialog |
| `tmx_editor` | — | modules.shortcut_display | — | tmx_editor_qt |
| `tmx_editor_qt` | PyQt6 | modules.styled_widgets, modules.tmx_editor | database_manager | Supervertaler |
| `tmx_generator` | — | — | language_codes | Supervertaler, batch_offload, database_manager, translation_memory |
| `tracked_changes` | — | — | — | ORPHAN |
| `trados_bridge_client` | — | — | — | chat_view_widget, unified_prompt_manager_qt |
| `trados_docx_handler` | docx, lxml | — | — | Supervertaler |
| `translation_memory` | — | modules.database_manager | tmx_generator | Supervertaler |
| `translation_results_panel` | PyQt6 | — | termbase_entry_editor | Supervertaler |
| `translation_services` | — | — | llm_clients | ORPHAN |
| `ui_scale` | — | — | — | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget |
| `unified_prompt_library` | — | — | — | unified_prompt_manager_qt |
| `unified_prompt_manager_qt` | PyQt6 | modules.ai_actions, modules.ai_attachment_manager, modules.ai_file_viewer_dialog, modules.chat_backend, modules.chat_view_widget, modules.document_analyzer, modules.help_system, modules.llm_clients | figure_context_manager, llm_clients, platform_helpers, trados_bridge_client | Supervertaler |
| `usage_log` | — | modules.llm_pricing | — | Supervertaler, chat_backend, llm_clients, usage_report_dialog |
| `usage_report_dialog` | PyQt6 | usage_log | — | Supervertaler |
| `usage_statistics` | — | — | — | Supervertaler |
| `voice_command_dialog` | PyQt6 | modules.shortcut_display, modules.voice_commands | — | Supervertaler, voice_tab |
| `voice_commands` | PyQt6 | modules.platform_helpers, modules.shortcut_display | mic_devices, platform_helpers, voice_vocabulary, vosk_model_manager | Supervertaler, voice_command_dialog |
| `voice_dictation` | PyQt6, numpy, sounddevice | modules.platform_helpers, modules.shortcut_display | — | ORPHAN |
| `voice_dictation_lite` | PyQt6 | modules.platform_helpers | mic_devices, voice_vocabulary | Supervertaler |
| `voice_hotkey_listener` | PyQt6 | — | — | Supervertaler, voice_tab |
| `voice_release_poller` | PyQt6 | — | — | Supervertaler |
| `voice_tab` | PyQt6 | modules.help_system, modules.styled_widgets, modules.voice_command_dialog | mic_devices, shortcut_display, voice_hotkey_listener | Supervertaler |
| `voice_vocabulary` | — | — | — | Supervertaler, voice_commands, voice_dictation_lite |
| `vosk_model_manager` | — | — | — | voice_commands |

# 5. Reverse dependencies (кто импортирует модуль)

| Модуль | Число импортёров | Импортёры |
|---|---|---|
| `platform_helpers` | 11 | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget, local_llm_setup, pdf_rescue_Qt, pdf_rescue_tkinter, superlookup, unified_prompt_manager_qt … |
| `shortcut_display` | 11 | Supervertaler, keyboard_shortcuts_widget, ribbon_widget, shortcut_manager, termlens_widget, tmx_editor, unified_prompt_manager_qt, voice_command_dialog … |
| `help_system` | 10 | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget, statistics_dialog_qt, styled_widgets, term_picker_dialog, termlens_popup, termlens_widget … |
| `styled_widgets` | 10 | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget, pdf_rescue_Qt, pseudo_translate_dialog, statistics_dialog_qt, termbase_entry_editor, tmx_editor_qt … |
| `llm_clients` | 7 | Supervertaler, batch_offload, chat_backend, chat_view_widget, quicktrans, translation_services, unified_prompt_manager_qt |
| `tmx_generator` | 4 | Supervertaler, batch_offload, database_manager, translation_memory |
| `language_codes` | 4 | Supervertaler, bilingual_markdown_handler, database_manager, tmx_generator |
| `usage_log` | 4 | Supervertaler, chat_backend, llm_clients, usage_report_dialog |
| `database_manager` | 4 | Supervertaler, database_migrations, tmx_editor_qt, translation_memory |
| `ui_scale` | 3 | Supervertaler, clipboard_manager_widget, keyboard_shortcuts_widget |
| `voice_vocabulary` | 3 | Supervertaler, voice_commands, voice_dictation_lite |
| `mic_devices` | 3 | voice_commands, voice_dictation_lite, voice_tab |

Самый используемый модуль — `platform_helpers` (11 файлов), далее `shortcut_display` (11), `styled_widgets`/`help_system` (10), `llm_clients` (7).

# 6. Orphan-модули (не импортируются никем — 19 шт.)

`extract_tm.py`, `feature_manager.py`, `find_replace.py`, `glossary_manager.py`, `identifier_conventions.py`, `pdf_rescue_tkinter.py`, `project_home_panel.py`, `project_tm.py`, `prompt_assistant.py`, `prompt_library.py`, `quick_access_sidebar.py`, `ribbon_widget.py`, `setup_wizard.py`, `style_guide_manager.py`, `superdocs.py`, `superdocs_viewer_qt.py`, `tracked_changes.py`, `translation_services.py`, `voice_dictation.py`

Классификация или смертности см. DEAD_CODE_REPORT.md §LIVE_BUT_LEGACY / PROBABLY_DEAD. Особые случаи: `superdocs.py`, `superdocs_viewer_qt.py` — намеренные deprecated-shim'ы (выбрасывают понятную ошибку); `ribbon_widget.py` — единственная ссылка в монолите закомментирована (Supervertaler.py:13119); `tracked_changes.py` — комментарий «will be imported from the main file» не реализован.

# 7. Циклические зависимости

- **Import-циклы: отсутствуют.** Граф импортов 120 файлов ацикличен (проверено: ни один файл не импортирует `Supervertaler`, внутренний граф modules/ — DAG).
- Потенциальные циклы ПОСЛЕ миграции (чего избегать): `grid/*` → `comments_ui` → `grid/*` (runtime-цикл вызовов SCC#1: 15 методов), `translation_service` ↔ `tm_service` (через кэши матчей), `workers/PreTranslationWorker` → MainWindow-состояние.
- Легаси-«полуцикл»: `docx_handler.py:21-24` импортирует `tag_manager` через bare/relative fallback (`from .tag_manager import` / `from tag_manager import`) — при переупаковке modules/ в под-пакеты это сломается первым.

# 8. HIGH COUPLING / LOW COUPLING

**HIGH (требуют проектирования контрактов при выносе):**
1. `unified_prompt_manager_qt` (6 808 LOC; сконструирован самим окном; 11 внутренних зависимостей)
2. `quicktrans` (1 663; parent_app во всём)
3. `voice_commands` (~15 duck-typed методов MainWindow)
4. `translation_results_panel` (2 427; parent_app=self)
5. `voice_tab` (1 378; документированный контракт)
6. `SuperlookupTab` внутри монолита (5 237; ~25 атрибутов MainWindow)
7. Grid-редакторы (2 500+; ~30 атрибутов MainWindow)

**LOW (отделяются сразу):**
`database_manager`, `database_migrations`, `sdlppx_handler`, `sdltm_handler`, `docx_handler`, `tag_manager`, `mqxliff_handler`, `memoqrtf_handler`, `cafetran_docx_handler`, `trados_docx_handler`, `phrase_docx_handler`, `dejavurtf_handler`, `po_handler`, `bilingual_markdown_handler`, `tmx_generator`, `tmx_editor`, `language_codes`, `statuses`, `config_manager`, `platform_helpers`, `llm_clients`, `llm_pricing`, `usage_log`, `spellcheck_manager`, `segment_split_merge`, `pseudo_translate`, `simple_segmenter`, `project_assets`, `okapi_sidecar`, `autocorrect`, `voice_vocabulary`, `vosk_model_manager`, `mic_devices`, `text_conversion_library`, `snippet_library`, `style_guide_manager`, `autostart`, `i18n`, `ui_scale`, `file_dialog_helper`, `superlookup`, `termbase_import_export`, `tm_metadata_manager`, `prompt_library_migration`, `unified_prompt_library`, `document_analyzer`, `docx_comments`.

# 9. Class → dependencies (ключевые классы)

| Класс (файл) | Ключевые зависимости |
|---|---|
| `SupervertalerQt` | PyQt6 QMainWindow; 42 модуля modules/; threading; sqlite (через DatabaseManager); pyperclip; atexit |
| `PreTranslationWorker` | QThread; `parent_app.current_project`; llm_clients; замыкания стартера |
| `TMSearchWorker` / `ProofreadWorker` / `GlossaryExtractionWorker` | только QThread + аргументы (чистые) |
| `SuperlookupTab` | SuperlookupEngine (modules/superlookup); platform_helpers; MainWindow (duck-typed); QThreadPool |
| `Segment/Project/Comment` | dataclasses; stdlib only |
| `UnifiedPromptManagerQt` | PyQt6; unified_prompt_library; llm_clients; chat_backend; chat_view_widget; ai_actions; ai_attachment_manager; document_analyzer |
| `DatabaseManager` | sqlite3; difflib; database_migrations; language_codes; tmx_generator |
| `SuperlookupEngine` | pyperclip; platform_helpers (lazy) |

# 10. Function → dependencies (топ-функции монолита)

~30 DOCX/tag-функций верхнего уровня (494–1767) — **чистые** (stdlib: re, docx-объекты передаются параметрами) → идеальные кандидаты `modules/tag_formatting.py`. `_setup_diagnostic_log`/`_install_log_hooks` — sys/stderr + platform_helpers. `get_user_data_path`-семейство — config files. `main()` — композиционный корень (инстанцирует QApplication, SupervertalerQt, batch_offload CLI, usage_statistics).

---

*Ни один .py-файл не был изменён.*
