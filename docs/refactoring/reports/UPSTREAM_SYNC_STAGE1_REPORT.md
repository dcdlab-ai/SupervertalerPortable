# Upstream Sync — Этап 1 (разведка): аудит апстрима v1.10.372

**Дата:** 2026-10-01
**Исполнитель:** Zcode (режим READ-ONLY; единственная запись — этот файл)
**Апстрим:** https://github.com/Supervertaler/Supervertaler-Workbench (remote `upstream`, только для чтения)
**Цель:** карта переноса исправлений `v1.10.371 → v1.10.372` в Portable. Сам перенос — Этап 2 (не выполнялся).

---

## 0. Baseline и git-синхронизация

### 0.1 Синхронизация
| Параметр | Значение |
|---|---|
| Локальный HEAD (main) | `7b895c932d106712adbabf42d725459ea06db196` |
| origin/main (после `git fetch origin`) | `7b895c9` — **совпадает с HEAD** |
| `git status` | чисто (только служебный untracked `.zcode/plans/…`, не тронут) |
| Опережающие коммиты (main впереди origin) | **нет** — пуш-подтверждение не требуется |
| Дрейф-чек `git merge-base --is-ancestor 22ccea43 HEAD` | **истина** (блокера нет) |
| upstream/main | `8206153d72a844318d9e414625314040712d1d48` |
| `git log --oneline v1.10.372..upstream/main` | 1 коммит: `8206153d Remove v1.10.372 release handoff` (служебная чистка; в объём не входит) |
| `git merge-base HEAD upstream/main` | **ОБЩЕЙ ИСТОРИИ НЕТ** (`fatal: Not a valid commit name` / пустой вывод) → Portable импортирован файлами; все сравнения — тег-к-тегу внутри апстрима |

### 0.2 Baseline Portable
| Метрика | Значение | Команда |
|---|---|---|
| `Supervertaler.py` | **68 224** строки | `wc -l` |
| `modules/settings_service.py` | 565 строк, 27 функций | `wc -l` |
| `modules/` *.py | 134 файла (+ подкаталоги `dialogs/`, `grid/`, `workers/`) | `git ls-files modules/ \| grep '\.py$'` |
| `py_compile` монолит + все modules | **135 / 135 OK**, сбоев нет | `E:\Dev\python-embed\python.exe -c …py_compile…` |
| SHA256 `Supervertaler.py` | `c0370685430514a39b1147a8b19a54fd615e06d225324fc4ba74e1dd8eaffe5c` | `sha256sum` |
| SHA256 `modules/settings_service.py` | `5e5826397f6794f741822dd5ca76846fd8ddff7b9eca33ebc0208e342ee015bf` | `sha256sum` |

---

## 1. Базовая версия апстрима, на которой основан Portable

**Заявленная версия:** `pyproject.toml` → `version = "1.10.371"` (Portable). `__version__` читается `_read_version()` из `Supervertaler.py:36–72`; резервный литерал `1.10.313` не актуален. **CHANGELOG.md в репо Portable НЕТ** (проверено: `git ls-files | grep -i changelog` — пусто) — версии сверялись через `git show <tag>:pyproject.toml`; у апстрима `v1.10.371` → `1.10.371`, `v1.10.372` → `1.10.372`.

**Независимое подтверждение базы blob-хэшами.** Выбраны 9 файлов `modules/`, не менявшихся с момента импорта (`git log --follow` = 1 коммит). Сравнение `git rev-parse HEAD:<path>` против `git rev-parse v1.10.371:<path>` / `v1.10.372:<path>`:

| Файл | vs v1.10.371 | vs v1.10.372 |
|---|---|---|
| translation_memory.py | **MATCH** | diff |
| tmx_generator.py | **MATCH** | MATCH |
| docx_handler.py | **MATCH** | MATCH |
| po_handler.py | **MATCH** | MATCH |
| llm_clients.py | **MATCH** | diff |
| i18n.py | **MATCH** | MATCH |
| platform_helpers.py | **MATCH** | diff |
| language_codes.py | **MATCH** | MATCH |
| models.py | нет в апстриме (Portable-only) | нет |

8/9 совпадений с `v1.10.371`; с `v1.10.372` часть расходится (эти файлы и меняет диапазон). Кандидат единственный — **база = тег `v1.10.371`**, неоднозначности нет.

**Полная карта дрейфа** (поблочное сравнение всех `modules/*.py` + монолит, `git rev-parse HEAD:<f>` vs `v1.10.371:<f>`):

| Файл | Расхождение |
|---|---|
| `Supervertaler.py` | рефакторинг-батчи (68 224 строки против 73 211 в базе апстрима) |
| `modules/tag_manager.py` | расширен переносами: 1 719 строк против 382 у апстрима (`_ALL_TAGS_PATTERN`/`extract_all_tags` переехали сюда) |
| `modules/settings_service.py`, `modules/models.py`, `modules/event_filters.py`, `modules/undo_manager.py` | **Portable-only** (созданы батчами; в апстриме отсутствуют) |
| всё остальное (128 файлов) | **blob-идентично v1.10.371** → правки апстрима к этим файлам применимы дословно |

**Прочее:** `git merge-base --is-ancestor 1f8cad19984aa36ef3006ea589aaeb7eacbe47a7 v1.10.372` — **истина** (Inline Codes входит в релиз). Пост-релизных содержательных коммитов нет (см. 0.1).

---

## 2. Инвентаризация v1.10.371..v1.10.372

### 2.1 Счётчики
| Метрика | Значение |
|---|---|
| Коммитов | **33** (`git log --oneline v1.10.371..v1.10.372 \| wc -l`) |
| Файлов изменено | 82 (`git diff --stat`, tail): монолит, 54 модуля/дока, **26 новых тестов** `tests/test_*.py` |
| Строк | **+9 142 / −974**; в монолите +1 919 / −734 (73 211 → 74 396 строк) |
| Новых модулей `modules/` | 22 (class A/D ниже) |
| Коммитов без правок монолита | 6 (8e8be3d4, 0d5375e0, 75a621a1, b3f76ee7, f90edc12, a5857227) |

Методы монолита определялись AST-маппером (изменённые строки `+`/`-` резолвились в охватывающий метод состояния файла на момент коммита; артефакты: `D:\Temp\SupervertalerPortable\refactoring\upstream-stage1\{commit_methods.txt, anchor_map.txt, d_*.diff}`).

### 2.2 Таблица коммитов (хронологически)

Классы: **A** — самостоятельный модуль/дословный перенос; **B** — правка в перенесённом коде или поверх него; **C** — удаляемая фича (пропуск); **D** — новая функциональность (отложить); **E** — неприменимо. «Цель в Portable» — по именам методов (AST `anchor_map.json`), не по строкам.

| # | SHA | Issue | Суть | Файлы | Класс | Цель в Portable | Риск | Замечания |
|---|---|---|---|---|---|---|---|---|
| 1 | 8e8be3d4 | — | pricing.json синхронизация (Sonnet 5.5/Opus 5.5/Fable 5.1, cache-read) | llm_pricing.py, pricing.json, тест | **A** | modules/* blob-идентичны → дословно | низк | данные |
| 2 | f5bfefc9 | — | Переименование Claude-моделей | монолит + llm_clients, pdf_rescue_Qt, prompt_assistant | **B** | `_create_ai_settings_tab`@20831, `_create_mt_quick_lookup_settings_tab`@21998, `_add_mt_and_llm_matches`@62102 (монолит); `load_llm_settings` → **B: modules/settings_service.py** `SettingsService.load_llm_settings@232` (дефолт `claude_model`) | средн | правки комбо-списков; точное сравнение ID моделей вместо substring |
| 3 | 0d5375e0 | #250 | Чат с моделью без цены падает | chat_backend.py, llm_pricing.py | **A** | blob-идентичны → дословно | низк | пункт 10b |
| 4 | da403a48 | #180 | Ollama timeout + **фикс затирания MT-профилей при Save AI Settings** | монолит + llm_clients | **B** | `_save_ai_settings_from_ui`@26313 (дефект подтверждён), новая `_apply_ollama_timeout_setting`; сохранение через делегат → `SettingsService.save_llm_settings@272` (полная замена ключа `llm_settings` секции `ui`) | **выс** | приоритет п. 8 |
| 5 | 974c1045 | #170 | Экспорт конкорданса в Excel/CSV | новый concordance_export.py + монолит | **D** | `SuperlookupTab.export_tm_results` — новый метод | — | фича |
| 6 | ad910e96 | #248 | Обновление проекта из вставленного bilingual-текста | монолит + bilingual_markdown_handler.py | **D** | `import_bilingual_markdown`@40227 переработка; новые `_apply_bilingual_text_update`, `import_bilingual_text_from_paste` | — | фича (фикс п.2 — в №29) |
| 7 | 108439b9 | #93 | AI-модель в Project Information | монолит | **D** | `show_project_info_dialog`@51213 | — | фича, якорь есть |
| 8 | 34a4c661 | #173 | Вставленный исходник в существующий проект | монолит + segment_split_merge.py | **D** | `add_source_text_to_project` — **ОТСУТСТВУЕТ** в Portable | — | фича; якоря нет |
| 9 | 626d4c63 | — | **Фикс затирания General Settings (14 ключей) + AHK prefs** | монолит + keyboard_shortcuts_widget.py | **B** | `_save_general_settings_from_ui`@26533 (дефект подтверждён); битые вызовы `save_general_settings()` без аргумента: `Supervertaler.py:66604`, `:66647` | **выс** | приоритет п. 8; см. 3.8 |
| 10 | 1c77e807 | #69 | Размер шрифта TM-результатов SuperLookup | монолит | **D** | новые методы `SuperlookupTab._on_tm_font_size_changed` и др. | — | фича |
| 11 | 48060d19 | #208 | Regex в фильтрах сетки | новый grid_filter.py + монолит | **D** | `apply_filters`@51724 (внимание: одноимённые методы в grid/filters.py, tmx_editor* — не цели) | — | фича |
| 12 | 75a621a1 | #111 | **TM/termbase-контекст реально доходит до AI** | unified_prompt_manager_qt.py | **A** | blob-идентичен → дословно; зависимости есть: `tm_database`@6362, `tm_metadata_mgr`@6371, `_search_termbase_in_memory`, `_segment_for_grid_row` | низк | пункт 10a; дефект подтверждён (несуществующие атрибуты `tm_databases`/`termbases`) |
| 13 | 46191414 | #219 | Word-count проверка для всех Okapi-форматов | новый export_word_count.py + монолит | **B/D** | `_count_exported_docx_words`@14201 → `_count_exported_words`, `_verify_export_word_count`@14233 | средн | наполовину фича |
| 14 | a1b94f41 | #70 | Zoom превью | монолит | **D** | `_create_preview_tab`@42395, `_render_preview`@42829; `_PreviewTextEdit` в Portable **вложен** в `_create_preview_tab` (в апстриме — топ-уровень) | — | фича; якорь структурно другой |
| 15 | 49eecc5c | #109 | Custom dictionary: import/export/sort | монолит + spellcheck_manager.py | **D** | `_open_custom_dictionary_dialog`@52245, `_save_custom_dictionary`@52298 | — | фича поверх существующего |
| 16 | 6b80a441 | #52 | Backup всех TM/termbase одним махом | новый resource_backup.py + монолит + termbase_* | **D** | `backup_all_resources` — новый метод | — | фича |
| 17 | 2386c976 | #226 | **Ремонт съехавших numbered-тегов из AI** | новый tag_repair.py + монолит | **B** | `PreTranslationWorker._translate_batch_with_llm`@5715, `._translate_single_with_llm`@5934, `translate_current_segment`@58368 | средн | фикс; worker в монолите, вызовы без hasattr — править аккуратно |
| 18 | a8dc2a36 | #8 | Per-job AI cost | новый cost_estimate.py + монолит + usage_* | **D** | `translate_batch`, `show_project_info_dialog`, `create_menus`… | — | крупная фича |
| 19 | bac34892 | #200 | Автодетект языковой пары (Trados/CafeTran/DejaVu/memoQ) | новый bilingual_lang_detect.py + 4 хендлера + монолит | **C** | хендлеры cafetran_docx/dejavurtf/memoqrtf/trados_docx + `import_*_bilingual`, `_confirm_language_pair`@36647 | — | подтверждено: весь домен запланирован к удалению |
| 20 | b3f76ee7 | #243 | **AltGr проходит через Ctrl+Alt глобальные хоткеи** | platform_helpers.py | **A** | blob-идентичен → дословно; `GlobalHotkeyManager` живёт в modules/platform_helpers.py (не удаляется Batch #8; используется `setup_global_shortcuts` и SuperLookup) | низк | пункт 3; см. 3.3 |
| 21 | fe1a7d0a | #105 | **TMX-импорт: srclang, клэши имён, в правильный TM** | translation_memory.py, tm_metadata_manager.py + монолит | **B** | `_import_tmx_as_tm`@19651, `_show_create_tm_dialog`@19554 (есть); `_preselect_tmx_pair` — новый | средн | пункт 7; дефект подтверждён |
| 22 | c0219f5b | #208 | SuperLookup: свои web-ресурсы | новый custom_web_resources.py + монолит | **D** | новые методы SuperlookupTab | — | фича; SuperLookup остаётся |
| 23 | ee75e3be | #68 | **F&R: замена в writable TM; whole-words; TM edit hash** | новый tm_replace.py + database_manager.py, find_replace_qt.py + монолит | **B** | `replace_all_matches`@50613, `replace_current_match`@50528, `show_find_replace_dialog`@49624; новая `_fr_plan_tm_replace`; `update_translation_unit` в database_manager | **выс** | пункты 4, 5; дефекты подтверждены |
| 24 | 09d374e1 | #209 | QA: сохраняемые find-only проверки | **новые** qa_checks.py, qa_checks_dialog.py + find_replace_qt.py + монолит | **D** | `show_qa_checks_dialog` — **ОТСУТСТВУЕТ** в Portable | — | QA-фича в Portable отсутствует целиком (см. 3.4-примечание) |
| 25 | 2e9192f5 | #233 | QA: LanguageTool | новые languagetool_client/dialog.py + монолит | **D** | `show_languagetool_dialog`, `_set_target_from_tool` — новые | — | фича |
| 26 | f6d9c279 | #78 | **Тёмная тема: светлые stylesheet-ы виджетов, деревья/списки** | новый dark_style_adapter.py + theme_manager.py + монолит | **A/B** | `ThemeManager` blob-идентичен → дословно; монолит `__init__`, `refresh_theme_colors`@61160 | средн | пункт 9 (остающиеся вкладки); Clipboard-часть — №33 |
| 27 | f9c212ab | #147 | Help → Open Sample Project | новый sample_project.py + монолит | **D** | `open_sample_project` — новый | — | фича |
| 28 | c32ff52e | #117 | Match Panel: inline-теги как токены в TM diff | **новый** tm_diff.py + монолит | **D** | `_set_compare_panel_text_with_diff`@42255 | — | фича; tm_diff.py в Portable нет |
| 29 | 763291e8 | #191 | **Segmentation Rules + сегментатор, не теряющий текст** | новый segmentation_rules.py/_widget.py + simple_segmenter.py (переработка) + монолит | **B** | `SimpleSegmenter`/`MarkdownSegmenter` blob-идентичны → фикс дословно; вызовы монолита: `import_simple_txt`@33264, `export_simple_txt`@33638, `_make_sentence_segmenter` (новый), `create_segmentation_rules_tab`@15295 | **выс** | пункты 1, 2; переработка API (`segment_with_separators`) |
| 30 | 05720a55 | #214 | Settings autosave («no more Save buttons») | новый settings_autosave.py (196 строк) + монолит | **D** | `create_settings_tab`@20503 (SupervertalerQt; НЕ SuperlookupTab@64429) + 9 `_create_*_settings_tab` | — | вне объёма; оценка в 3.11 |
| 31 | 1f8cad19 | #194 | Inline Codes | новые inline_codes.py (179 стр.), inline_codes_widget.py (218) + qa_checks*, tm_diff, translation_results_panel + монолит | **D/см. §4** | разбор в §4 | средн | см. §4 |
| 32 | f90edc12 | — | Release v1.10.372 (version bump, changelog, handoff) | docs + pyproject.toml | **E** | версионирование Portable своё (pyproject.toml blob совпадал с базой, поднимать отдельно) | — | пропуск |
| 33 | a5857227 | #78 | Тёмная тема: Clipboard Manager читаемость | clipboard_manager_widget.py | **C** | clipboard_manager_widget.py — вкладка к удалению | — | пропуск |

**Итог классов:** A/дословно — 6 (№1, 3, 12, 20, 26-частично, 32-E); B — 8 (№2, 4, 9, 13, 17, 21, 23, 29); C — 2 (№19, 33); D — 17.

### 2.3 Пересечения с доменом Batch #7 (настройки)

| Коммит | Метод | Где в Portable | Незащищённые вызовы |
|---|---|---|---|
| 626d4c63 | `_save_general_settings_from_ui` | **монолит** @26533 (НЕ переносился; делегат `save_general_settings` → `SettingsService.save_general_settings@214`, который делает `_save_settings_section("general", settings)` — **полную замену секции**) | — |
| 626d4c63 | AHK-вызовы `save_general_settings()` / `main_window.general_settings[…]` | монолит `SuperlookupTab` `Supervertaler.py:66604`, `:66647`; комментарий `settings_service.py:161–165` прямо фиксирует: «предсуществующие сайты SuperlookupTab 66780/66823 — не чинятся здесь» (вызов без аргумента обязан падать TypeError). Апстрим-фикс чинит ровно их | — |
| da403a48 | `_save_ai_settings_from_ui` | монолит @26313; сохранение через `save_llm_settings` → `SettingsService.save_llm_settings@272` — `all_settings.setdefault("ui", {})['llm_settings'] = settings` (полная замена ключа) → **затирание `custom_mt_profiles` материализуется через перенесённый модуль**, а сам фикс (строить dict от существующего) вносится в монолит | — |
| f5bfefc9 | `load_llm_settings` (дефолт `claude_model`) | **перенесён**: `SettingsService.load_llm_settings@232` (defaults-словарь) + делегат в монолите @56913 → правка в **settings_service.py** | — |
| 05720a55, 1f8cad19 | страницы Settings (`create_settings_tab`, `_create_*_tab`, `_save_inline_codes`) | монолит | — |
| 2386c976, 1f8cad19 | `PreTranslationWorker._translate_batch_with_llm` / `._translate_single_with_llm` | монолит @5715/@5934 (worker НЕ перенесён); апстрим вставляет вызовы `_inline_codes.*` / `tag_repair` без hasattr — при переносе проверять каждый вызов (batch_offload.py апстрим сознательно не трогал) | есть (вставки идут в тело метода напрямую) |

`load_api_keys`: делегат монолита @61072 + `SettingsService.load_api_keys@378` + автономная `modules/llm_clients.load_api_keys@43`; ни один коммит диапазона их не трогает — пересечений нет.

---

## 3. Обязательные пункты релиза

Формат: коммит-фикс → механика дефекта → **есть ли дефект в текущем Portable** (по чтению кода; blob-идентичность файла базе = дефект присутствует, если фикс не приходил извне).

### 3.1 Потеря первого слова при «Split lines into sentences»
- **Фикс:** 763291e8 (#191) — переработка `modules/simple_segmenter.py`.
- **Механика старого кода** (blob-идентичен Portable): `re.split(r'([.!?]+)\s+(?=[A-Z"\'])', text)` + восстановление с жёстким списком `['.', '!', '?', '...', '.)', '."']`. Для «Really?! Great.» разделитель `?!` в списке НЕ значится → «Really» и «?!" становятся отдельными сегментами (слово отрывается от пунктуации, «?!" — сегмент-мусор); плюс `_is_abbreviation_only` молча **удалял** целые сегменты-аббревиатуры (потеря текста).
- **Portable:** дефект **присутствует** (`modules/simple_segmenter.py` идентичен базе; вызовы монолита: `Supervertaler.py:15408`, `:29393`, `:33439–33450` и др.).
- **Перенос:** фикс неотделим от нового движка правил (см. вопрос Q2): новые `_TERMINATOR`-регексп, `never_break_after`, `segment_with_separators` + `join_segments` (экспорт требует правок вызовов монолита `import/export_simple_txt`).

### 3.2 Markdown: ссылка с inline-кодом → плейсхолдер `\x00MD0\x00`
- **Фикс:** тот же 763291e8, `MarkdownSegmenter.segment_with_separators`: Phase 3 восстанавливает плейсхолдеры **newest-first** (`reversed(list(placeholders.items()))`), т.к. поздний конструкт может содержать ранний: `[`code`](url)`.
- **Portable:** дефект **присутствует** (старый порядок восстановления в `modules/simple_segmenter.py`).

### 3.3 AltGr (Ctrl+Alt) и глобальные хоткеи
- **Фикс:** b3f76ee7 (#243) — **целиком `modules/platform_helpers.py`** (`altgr_character()`, `send_unicode_text()`, `_WinKeyboard`, хук в `GlobalHotkeyManager._win_thread`).
- **Portable:** дефект **присутствует** (файл идентичен базе).
- **Живёт ли модуль через Batch #8:** глобальные хоткеи живут в `modules/platform_helpers.py` (класс `GlobalHotkeyManager`), это не Voice/Clipboard/Superbrowser-модуль; потребители в монолите: `setup_global_shortcuts` (`Supervertaler.py:66764`, создание `GlobalHotkeyManager()`), SuperLookup hotkey-колбэки (`_handle_superlookup_hotkey` через `QMetaObject.invokeMethod`, `Supervertaler.py:66818–66830`). Голосовые модули только ссылаются на механизм в комментариях/докстрингах (`voice_hotkey_listener.py:344`, `voice_release_poller.py:203`). **Вывод: фикс переживёт Batch #8** (SuperLookup остаётся; уточнение по коду, не по предположению).

### 3.4 Отредактированная запись TM перестаёт находиться как exact match
- **Фикс:** ee75e3be (#68), `modules/database_manager.py::update_translation_unit` (~строка 2232): хэш считался как `md5(new_source.strip().lower())`, а ищется через `_normalize_for_matching` → запись с заглавной буквой в source после редактирования выпадала из exact match. Фикс: `md5(_normalize_for_matching(new_source_stripped))` (+ синхронный `target_hash`).
- **Portable:** дефект **присутствует** (файл идентичен базе). Правка ~3 строки, дословная.
- Примечание: `show_qa_checks_dialog`/QA-часть #68→#209 в Portable неприменима — QA-подсистемы нет (см. §4.3, Q5).

### 3.5 Find & Replace «Whole words» заменяет внутри слов
- **Фикс:** ee75e3be, монолит `replace_all_matches`/`replace_current_match` (+ общий replacer, `-  if use_regex:` ветки заменены единым `replacer(..., match_mode=...)`; новый `_fr_plan_tm_replace`; новый `modules/tm_replace.py`).
- **Portable:** дефект **присутствует**: `replace_all_matches`@50613 в не-regex ветке делает `old_text.replace(find_text, replace_text)` / `re.sub(re.escape(...))` **без границ слов**, `match_mode` учитывается только для «Entire segment» (`Supervertaler.py:50713–50731`).

### 3.6 Языковая пара: CafeTran → EN→NL; Déjà Vu/memoQ RTF — фиксированная пара
- **Фикс:** bac34892 (#200): новые `detect_language_pair()` в 4 хендлерах + `modules/bilingual_lang_detect.py` + монолит `_confirm_language_pair`/`_language_detection_message`.
- **Класс C — подтверждено:** все четыре хендлера (cafetran_docx/dejavurtf/memoqrtf/trados_docx) и монолитные `import_*_bilingual` входят в домен удаления (CAT-интеграции). `bilingual_lang_detect.py` используется только ими → тоже C. **Рекомендация: пропуск целиком.**

### 3.7 TMX-импорт: направление, «Failed to create TM metadata», не тот TM
- **Фикс:** fe1a7d0a (#105): `translation_memory.py::detect_tmx_source_language` (header `srclang`; старый `detect_tmx_languages()` сортировал языки по алфавиту — направление терялось, en-GB→de-DE предлагался как de→en), `tm_metadata_manager.py::tm_name_exists` (клэши имён), монолит `_import_tmx_as_tm`/`_show_create_tm_dialog` (+новый `_preselect_tmx_pair`).
- **Portable:** дефект **присутствует** (оба модуля идентичны базе; методы монолита `_import_tmx_as_tm`@19651, `_show_create_tm_dialog`@19554 на месте).

### 3.8 Настройки затирают друг друга — ПРИОРИТЕТ
- **Коммиты:** 626d4c63 (General) + da403a48 (AI).
- **Точные ключи, удалявшиеся «Save General Settings»** (из тела 626d4c63; воспроизведено апстримом headless): `batch_size`, `surrounding_segments`, `use_full_context`, `context_window_size`, `quicklauncher_context_percent`, `check_tm_before_api`, `check_tm_exact_only`, `lookup_delay`, `fuzzy_fixer_min_pct`, `fuzzy_fixer_max_pct`, `persist_usage_log`, `monthly_budget_usd`, `mt_quick_lookup` (все настройки QuickTrans), `superlookup_landing_tab` — **14 ключей**.
- **Механика в Portable:** `_save_general_settings_from_ui`@26533 строит `general_settings = { … }` с нуля (тот же литерал, что у апстрима до фикса — сверено построчно по диффу) → `save_general_settings` (делегат) → `SettingsService.save_general_settings@214` → `_save_settings_section("general", …)@141` = `all_settings[section] = section_data` — **полная перезапись секции**. Дефект присутствует. Фикс апстрима: `general_settings = dict(existing_settings); general_settings.update({…})` — дословно применим (сигнатура метода в Portable расширена, но тело совпадает).
- **AI Settings:** `_save_ai_settings_from_ui`@26313 строит `new_settings = {…}` с нуля (`Supervertaler.py:26376`) → `save_llm_settings` → `SettingsService.save_llm_settings@272` **заменяет весь ключ `llm_settings`** секции `ui`, в котором живут `custom_mt_profiles`/`custom_mt_active_profile` (дефолты: `settings_service.py:244–266`; источник правды MT-профилей — `Supervertaler.py:22411`). Каждый Save AI Settings удалял кастомные MT-эндпоинты. **Дефект присутствует.** Фикс: `new_settings = dict(existing_settings); new_settings.update({…})`.
- **AHK-хвост 626d4c63:** в Portable чтение через несуществующий атрибут `main_window.general_settings` и два вызова `save_general_settings()` **без обязательного аргумента** (`Supervertaler.py:66604`, `:66647` → TypeError); Batch #7 их сознательно не чинил (`settings_service.py:161–165`). Апстрим-фикс переводит их на `load_general_settings()`/`save_general_settings({...})` — переносится, и снимает предохранительную оговорку из S2.2.
- **Затронутые методы из 25 перенесённых:** только адрес сохранения (делегаты) — тела переносимых не меняются; единственная правка внутри settings_service.py — дефолт `claude_model` (f5bfefc9). `load_general_settings` (97 строк) остаётся в монолите — фиксы её не трогают.

### 3.9 Тёмная тема: белые панели
- **Фикс:** f6d9c279 — (а) `modules/theme_manager.py`: QTreeView/QListView-правила + тёмная QPalette для тем с lightness < 0.3; (б) новый `modules/dark_style_adapter.py` (236 строк, самостоятельный): перекрашивает «собственные» светлые stylesheet-ы виджетов; (в) монолит: подключение в `__init__` и `refresh_theme_colors`.
- **Разделение C / остающиеся:** a5857227 (Clipboard Manager) — **C**, пропустить. Всё остальное (theme_manager, dark_style_adapter, деревья/списки промпт-библиотеки, info-боксы, SuperLookup-панели через общий адаптер) — **остающиеся**. Свидетельство: clipboard_manager_widget.py — единственный C-файл в теме; `dark_style_adapter.py` не импортирует удаляемые модули (AST: `modules.*` импортов нет).

### 3.10 AI Assistant: пустой TM/termbase-контекст; чат без цены
- **75a621a1 (#111), A:** `modules/unified_prompt_manager_qt.py` — `_get_tm_context_data`/`_get_termbase_context_data` искали несуществующие атрибуты (`tm_databases`, `termbases`, `termbase_manager`) → всегда «No translation memories loaded»; сборка промпта чата вообще не вставляла секции. Фикс читает реальные `tm_metadata_mgr`/`tm_database`/`_search_termbase_in_memory` + добавляет секции при `include_tm_data`/`include_termbase_data`. **Portable: дефект присутствует** (файл идентичен базе); **зависимости фикса в Portable есть**: `self.tm_database`@6362, `self.tm_metadata_mgr`@6371, `_search_termbase_in_memory`@7826, `_segment_for_grid_row`@2522.
- **0d5375e0 (#250), A:** `modules/chat_backend.py` — `f"~${cost:.4f}"` при `cost is None` (локальная модель без записи о цене) → TypeError; фикс «cost unknown». Плюс записи цен в `llm_pricing.py`. **Portable: дефект присутствует.**

### 3.11 Автосохранение настроек (#214) — оценка масштаба, В ОБЪЁМ НЕ ВХОДИТ
- Состав: новый `modules/settings_autosave.py` (196 строк, `SettingsAutoSaver`: только пользовательские события `clicked`/`activated`/фокусные изменения, дебаунс, snapshot-дифф, подавление попапов) + `create_settings_tab` (+10 строк) + по 1 строке в 9 `_create_*_settings_tab` (маркировка Save-кнопок свойством).
- Пересечения: все страницы остаются в монолите; сохранение идёт через те же делегаты → settings_service. **Критичная зависимость: автосейв запускает существующие Save-рутины — до фиксов 3.8 он бы автоматизировал затирание** (в апстриме 626d4c63/da403a48 предшествуют 05720a55).
- **Рекомендация: отдельным батчем ПОСЛЕ U1-фиксов настроек** (после Batch #8, когда состав страниц стабилизируется); риск средний, объём мал.

---

## 4. Разбор коммита 1f8cad1 (Inline Codes, issue #194)

### 4.1 Новые файлы
| Файл | Строк | Зависимости (AST, `v1.10.372`) | Конфликты имён в Portable |
|---|---|---|---|
| `modules/inline_codes.py` | 179 | нет `modules.*`; stdlib re/typing/collections — **самостоятельный** | нет (файла нет) |
| `modules/inline_codes_widget.py` | 218 | только `modules.inline_codes` + PyQt6 | нет |
| `tests/test_inline_codes.py` | — | — | нет (`tests/` в Portable нет) |

Зависимостей от монолита/self нет (проверено AST-обходом импортов; см. лог скрипта в stage-папке). Класс A.

### 4.2 Затронутые существующие файлы
| Файл | Версия Portable vs база 371 | Следствие |
|---|---|---|
| `Supervertaler.py` |refactor | хунки по якорям, см. 4.3 |
| `modules/qa_checks.py`, `modules/qa_checks_dialog.py` | **в Portable НЕТ, и в базе 371 их НЕТ** (созданы в диапазоне 09d374e1/2e9192f5) | хунки 1f8cad1 к ним неприменимы без переноса всей QA-фичи |
| `modules/tm_diff.py` | **в Portable НЕТ, и в базе 371 НЕТ** (создан c32ff52e #117) | аналогично |
| `modules/translation_results_panel.py` | blob-идентичен базе | дословно (новый метод `_with_adapted_codes` + 2 места вызова) |
| CHANGELOG.md | в Portable нет | n/a |

### 4.3 Хунки монолита (14) и якоря в Portable
Все якоря проверены AST (`anchor_map.json`), класс уточнён там, где имя совпадает у разных классов:

| Хунк (место) | Якорь в Portable | Статус |
|---|---|---|
| import `from modules import inline_codes as _inline_codes` (после voice_commands) | блок импортов монолита | есть |
| `extract_all_tags` (+`_ALL_TAGS_PATTERN`, module-level) | **перенесён**: `modules/tag_manager.py:1198/1201` (монолит импортирует `_ALL_TAGS_PATTERN`@410) → **B-правка в модуль** | есть, перенесён |
| `TagHighlighter.highlightBlock` | `Supervertaler.py:3035` (не путать с `_SearchTermHighlighter.highlightBlock`@62319 — AST) | есть, не перенесён |
| `GridTextEditor._insert_next_tag_or_wrap_selection` (строка `has_any_tags`) | `Supervertaler.py:1109` (строка `has_any_tags = …`@1144) | есть |
| `EditableGridTextEditor._insert_next_tag_or_wrap_selection` (то же, ВТОРОЙ раз) | `Supervertaler.py:4579` (@4616) | есть |
| `PreTranslationWorker._translate_batch_with_llm` (правило промпта) | `Supervertaler.py:5715` | есть, не перенесён |
| `_create_inline_codes_tab` + `_load_inline_codes` + `_save_inline_codes` (новые, после `_save_segmentation_rules`-зоны) | новых методов нет; точка вставки рядом с `_save_segmentation_rules`/`_make_sentence_segmenter` (в Portable их нет — см. Q2/Q3) | вставка |
| `create_settings_tab` (+вкладка) | `Supervertaler.py:20503` — **именно SupervertalerQt**; SuperlookupTab.create_settings_tab@64429 — одноимённый чужой метод (AST) | есть |
| `_update_match_panel_tm_display` (adapt_codes) | `Supervertaler.py:41526` | есть |
| `_current_segment_source` (новый метод перед `_get_current_segment_id`) | `_get_current_segment_id`@42614 — якорь; самого `_current_segment_source` нет ни в Portable, ни в базе 371 (метод новый) | есть |
| `show_qa_checks_dialog` (`extract_tags=…`) | **ОТСУТСТВУЕТ** — QA-подсистемы в Portable нет | неприменим |
| `translate_current_segment` (2 места сборки промпта: LLM-правило + custom_prompt) | `Supervertaler.py:58368` | есть |

### 4.4 Зависимости от settings
`_save_inline_codes` (новый метод) делает `settings = self.load_general_settings(); settings[_inline_codes.SETTINGS_KEY] = entries; self.save_general_settings(settings)` → ключ уходит в секцию **general** через монолитные вызовы (делегат → `SettingsService`). **Взаимодействие с п. 3.8:** до фикса 626d4c63 «Save General Settings» стирал бы и этот ключ (он строит dict с нуля) — в апстриме 626d4c63 стоит раньше 1f8cad19. Чтение через `load_general_settings()` безопасно (read-only + merge с defaults). Вывод: **перенос 1f8cad1 требует предварительного фикса 3.8**.

### 4.5 Оценка
Рекомендация: **отложить (D) в отдельный под-батч после фиксов настроек и, желательно, после Batch #8**. Обоснование: (а) это фича, а не исправление — против правила «фиксы раньше фич»; (б) 3 из 14 хунков упираются в отсутствующие подсистемы (QA, tm_diff, segmentation-rules-зона); (в) единственная ценность «фиксного» характера (подсветка/перенос кодов) не компенсирует касание 9 мест монолита до стабилизации сетки Batch #8. Если Дмитрию фича нужна раньше — минимальный перенос возможен (файлы A + 10 хунков монолита), но строго после 3.8.

---

## 5. Предложение разбивки Этапа 2 (черновик для координатора)

Правила: фиксы данных/настроек раньше фич; валидация каждого под-батча — на **копии user_data**; коммиты внутри под-батча в хронологическом порядке апстрима.

| Под-батч | Состав (SHA) | Содержание | Риск | Минимальный регрессионный сценарий |
|---|---|---|---|---|
| **U1.1 Данные и цены** | 0d5375e0, 8e8be3d4, f5bfefc9 | llm_pricing/pricing.json, chat_backend None-cost, переименование Claude-моделей (+B: дефолт `claude_model` в settings_service.py, комбо-списки монолита) | низкий | чат локальной моделью без цены → «cost unknown», не падает; AI Settings показывает Sonnet 5.5; сохранённая `claude-sonnet-5-5` выбирается точно (не по подстроке) |
| **U1.2 Настройки (приоритет)** | 626d4c63, da403a48 | фиксы затирания General/AI + AHK-вызовы 66604/66647 (+опционально Ollama timeout из da403a48) | высокий | на копии user_data: сохранить General → все 14 ключей + `mt_quick_lookup` остались в settings.json; сохранить AI → `custom_mt_profiles` не пуст; AHK-диалог: путь сохраняется, «не показывать» работает |
| **U1.3 Фиксы данных TM/тегов/хоткеев** | b3f76ee7, ee75e3be (hash+whole-words+tm_replace), fe1a7d0a, 2386c976 | AltGr; F&R; TMX-импорт; tag_repair | высокий | AltGr+L на польской раскладке печатает «ł» при глобальном Ctrl+Alt+L; отредактировать запись TM с заглавной → exact match находится; «Whole words» не заменяет внутри слов; TMX en-GB→de-DE предлагается в правильном направлении; AI-вывод со съехавшими `[1}` чинится |
| **U1.4 Сегментация** | 763291e8 (или минимальный бэкпорт — Q2) | сегментатор без потерь + (опц.) правила | высокий | «Really?! Great.» → корректные сегменты, ни один символ не потерян; `[`code`](url)` не оставляет `\x00MD0\x00`; экспорт txt восстанавливает строку |
| **U1.5 Тёмная тема** | f6d9c279 | theme_manager + dark_style_adapter + подключение | средний | офскрин-рендер тёмных тем: деревья/списки без белых выделений; светлые темы — пиксель-в-пиксель как раньше |
| **U1.6 AI-контекст** | 75a621a1 | TM/termbase реально уходят в промпт | низкий | чат с включённым TM/termbase: промпт содержит активные TM и термины из документа |
| Отложено (D) | №5–8, 10–11, 13–16, 18, 22, 24–25, 27–28, 30–31 | фичи | — | отдельные батчи после Batch #8 |
| Пропущено (C) | bac34892, a5857227 | CAT-импорты, Clipboard | — | — |
| Неприменимо (E) | f90edc12 | релизный bump | — | — |

Порядок U1.1→U1.6 повторяет порядок апстрима там, где есть зависимости (3.8 раньше 1f8cad1; настройки раньше autosave).

---

## 6. Непокрытые проверки

Всё, что не проверено статически или требует запуска (Этап 2 обязан закрыть на копии user_data):

1. **Рантайм-поведение**: ни одно исправление не проверено исполнением (приложение не запускалось по ТЗ). Сценарии из §5 — план, не результаты.
2. **Применимость дословных диффов модулей** доказана blob-идентичностью **базы**, но не примеркой диффа (`git apply --check` в worktree не выполнялся — это уже модификация рабочего дерева).
3. **Сигнатурные расхождения монолита**: Portable расширял некоторые методы (например, `_save_ai_settings_from_ui` имеет доп. параметры mistral/deepseek/openrouter) — хунк да `new_settings = dict(existing)` сверён по контексту, но позиция вставки подбирается вручную; построчного совпадения с апстримом нет.
4. **CRLF-оговорка AGENTS.md**: blob-хэши брались из git-объектов обеих сторон согласованно, но файловые сравнения рабочего дерева могут давать ложные расхождения по переводам строк.
5. **QA/tm_diff/segmentation-rules-зоны**: точное поведение хунков 1f8cad1/763291e8 в Portable не моделировалось там, где подсистем-якорей нет (QA, tm_diff) — там вердикт «неприменимо/вставка» основан на отсутствии файлов, а не на примерке.
6. **`_PreviewTextEdit`**: в апстриме класс поднят на топ-уровень (a1b94f41), в Portable вложен в `_create_preview_tab`@42432 — для отложенной фичи (D) перенос хунка нетривиален; глубоко не разбирался.
7. **Полнота карточек коммитов**: классы присвоены по файлам/методам/сообщениям коммитов; тела фич-коммитов (D) читались выборочно — у отложенных не проверено каждое место вставки.
8. **`tests/` апстрима** (26 файлов) не анализировались на запускаемость вне апстримного окружения (pytest в Portable не настроен).

---

## 7. Вопросы к Дмитрию

1. **Q1 — объём Этапа 2:** подтверждаете, что в U1 идут только классы A/B (§5, U1.1–U1.6), а 17 D-фич и 1f8cad19 откладываются после Batch #8?
2. **Q2 — сегментация:** полный бэкпорт 763291e8 (новый движок правил + Settings-страница «Segmentation Rules») или минимальный фикс двух багов (first-word loss в `SimpleSegmenter`, порядок восстановления плейсхолдеров в `MarkdownSegmenter`) без движка правил? Минимальный вариант расходится с апстримом и усложнит будущий sync.
3. **Q3 — Inline Codes (1f8cad1):** переносить в U1 (после U1.2, минимальным набором хунков) или отложить? Моя рекомендация — отложить (§4.5).
4. **Q4 — Ollama timeout (часть da403a48):** тащить вместе с фикс-частью U1.2 или отрезать (это новая настройка/фича внутри фикс-коммита)?
5. **Q5 — QA-подсистема (#209/#233)** целиком отсутствует в Portable: считать её кандидатной на отдельный батч после Batch #8 или не переносить вовсе (влияет на судьбу QA-хунка 1f8cad1)?
6. **Q6 — push:** отчёт docs-only; локальный main не опережает origin — коммитить и пушить сразу, или сначала ревью?

---

### Приложения (артефакты этапа, вне репо)
`D:\Temp\SupervertalerPortable\refactoring\upstream-stage1\`:
`commits_files.txt` (файлы по коммитам), `commit_methods.txt/json` (AST-маппинг хунков), `anchor_map.txt/json` (существование якорей в Portable), `hunk_to_method.py`, `anchor_check.py`, `d_*.diff` (диффы ключевых модулей), `d_1f8cad1_mono.diff`.
