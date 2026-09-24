# Step 7 — Stage 1 findings (Batch #7, read-only inventory)

**Дата:** 24.09.2026 • **HEAD:** `b5c46e7` • **Монолит `Supervertaler.py`:** 68 386 строк
(sha256 блоба `802c504c8849ac58551bece6b297917426e31226` — совпадает с
`git rev-parse HEAD:Supervertaler.py`, т.е. код НЕ изменялся)
**Режим:** READ-ONLY ANALYSIS (ни одна строка кода не правилась)
**Класс-цель:** `SupervertalerQt` (AST: 6054–62458; прямых методов 819)

Артефакты прогона (`docs/refactoring/audits/`):

| файл | содержимое |
|---|---|
| `batch7_stage1_methods_ast.txt` | все 819 прямых методов класса (имя, start, end, строк, декораторы) — AST, не греп |
| `batch7_stage1_candidates_scan.txt` | полный скан класса: 205 методов с name-паттерном (settings/config/save/load/…) И/ИЛИ IO-паттерном в теле (`json.`, `open(`, `os.path`, `user_data`, `Path.home`) |
| `batch7_stage1_inventory_tables.txt` | таблицы состава (тиры A/B/C) + таблица «вне состава» по группам, с точными границами и строками |
| `batch7_stage1_callsites_categorized.txt` | AST-карта всех 394 ссылок на 40 методов состава (call/attr-ref/string-ref/def + класс/модуль-владелец) |
| `batch7_stage1_callsites_raw.txt` | то же в машинном TSV |
| `batch7_stage1_dependencies.txt` | на каждый метод состава: используемые `self.*` и вызываемые имена |
| `batch7_stage1_dead_dynamic_check.txt` | сверка 40 имён состава с `DEAD_CODE_REPORT.md` (4 совпадения) |
| `batch7_stage1_config_manager_overlap.txt` | дубликаты «владельца settings.json», три механизма разрешения user_data, 11 внешних дукт-тайпед-консументов |
| `step7_stage1_findings.md` | этот файл |

Статус подзадач: **1.1 ✅ 1.2 ✅ 1.3 ✅ 1.4 ✅ 1.5 ✅ 1.6 ✅ 1.7 ✅ 1.8 ✅ 1.9 ✅**
(все девять закрыты в одной сессии; чужой незавершённой работы не было — файл findings
и секция «ПЕРЕДАЧА СМЕНЫ» в промпте отсутствовали).

---

## 1.1 Полная AST-инвентаризация по кластерам

Метод: `ast.parse` → `node.body` класса `SupervertalerQt` (НЕ `ast.walk`), 819 прямых
методов; далее скан по name-/body-паттернам (205 кандидатов) + вспомогательный
AST-поиск потребителей приватного API (`_load_settings_section`,
`_load_unified_settings`, `_save_unified_settings`, `_get_unified_settings_path`,
`_get_settings_dir`, `settings.json`) по всему классу — так найдены методы, которые
грепом по именам не ловятся (группа G3).

Проверка предварительных координат координатора (все, кроме перечисленных ниже,
подтверждены; здесь только расхождения и уточнения):

| Координатор (грep) | Факт (AST) | Комментарий |
|---|---|---|
| `_migrate_to_workbench_layout ~44816–?` | **44816–44881 (66L)** | конец не был проверен координатором — теперь зафиксирован |
| language pair ~45004–45021 и ~45228–45261 | + найден `_save_language_settings_from_ui` 45263–45273 | UI-обработчик с `QMessageBox`, вне состава |
| llm/proxy ~56987–57111 | + `_apply_gemini_proxy` 57100–57111 | прокси-хелпер, не settings IO (потребитель) |
| recent ~32231–32430 | + `update_recent_menu` 32195–32229 | построение QMenu (UI, вне состава) |
| — | **`get_autocorrect_settings` 44620–44631 (12L)** | ❌ пропущен грепом координатора: имя без settings/config-префикса, тело без файлового IO (in-memory getter) — сидит ровно в «необъяснённом разрыве» 44619–44638 |
| — | **`_migrate_voice_dictation_default_off` 45143–45174 (32L)** | ❌ пропущен: третья миграция Step 7, в `EXTRACTION_PLAN.md` не названа |
| — | **13 прямых читателей/писателей `settings.json`** (`get_termbase_code_map` 49124–49130, `save_termbase_code_map` 49132–49139, `_set_fr_demote_to_draft` 50149–50159, `_set_voice_pause_setting` 54397–54404, `_set_confirmed_progress_basis` 8481–8504, `_persist_autocorrect_settings` 23761–23772, `save_current_font_sizes` 44228–44278, `_save_bottom_dock_active_tab` 43603–43613, `_toggle_match_panel_tm_layout` 41495–41544, `_maybe_show_okapi_java_warning` 58442–58508, `_apply_reimport_settings` 48685–48700, `_init_usage_statistics` 45363–45385, `_verify_export_word_count` 14213–14252) | ❌ все пропущены грепом «на глаз» — группа G3, все вне состава |

**Объяснение «необъяснённых разрывов» координатора:**

| разрыв | что там на самом деле |
|---|---|
| 44619–44638 | 44619 — пустая; **44620–44631 `get_autocorrect_settings`**; 44632 — пустая; 44633–44637 — баннер-комментарий «Unified Settings Infrastructure … top-level sections: "api_keys", "general", "ui", "features"»; 44638 — пустая. Это 1 метод + комментарий-разметка, а не пропущенный IO |
| 44683–44689 | пустые/разделительные строки между `_save_settings_section` и блоком clipboard privacy |
| 44930 | одна пустая строка между `save_general_settings` и `load_dictation_settings` |
| 45022–45028 | пустые строки между `_load_language_pair_from_disk` и `load_voice_vocabulary_settings` |
| 45093–45227 | 45094–45119 `build_voice_initial_prompt` (Whisper-prompt, не IO), 45121–45141 `open_termbases_tab` (UI-навигация), **45143–45174 `_migrate_voice_dictation_default_off` (в составе)**, 45176–45226 `_collect_voice_dictation_termbase_terms` (читает БД терминологий) — поэтому «дыра» в 136 строк |
| 45262–45274 | `_save_language_settings_from_ui` (45263–45273) — UI-обработчик |
| 45275–45361 | `load_font_sizes_from_preferences` — читает general-секцию, но в основном применяет UI-настройки (тир C) |
| 57112–57162 | `_get_active_custom_profile` / `_get_custom_mt_profiles` / `_get_active_custom_mt_profile` — потребители `load_llm_settings()` |

**Итог 1.1:** гипотеза «минимум 9 кластеров» подтверждена; span не 32 231–61 247, а
**8481 → 61 247** (≈52 800 строк) — ещё более рассеяно. Помимо 5 кластеров внутри
44451–45361 (ядро settings), recent-projects и spellcheck-IO, найдены 4 группы
«одноразовых писателей» секций (`ui`/`general`/`features`) в 8481–54397, которых
в плане и в предварительном грепе не было.

---

## 1.2 Точный итоговый состав (тиры A/B/C)

| tier | метод | строки | строк |
|---|---|---|---|
| A | `_get_settings_dir` | 44639–44641 | 3 |
| A | `_get_unified_settings_path` | 44643–44645 | 3 |
| A | `_load_unified_settings` | 44647–44661 | 15 |
| A | `_save_unified_settings` | 44663–44672 | 10 |
| A | `_load_settings_section` | 44674–44676 | 3 |
| A | `_save_settings_section` | 44678–44682 | 5 |
| B | `load_general_settings` | 44522–44618 | 97 |
| B | `_load_general_settings_from_file` | 44883–44922 | 40 |
| B | `save_general_settings` | 44924–44929 | 6 |
| B | `load_clipboard_privacy_settings` | 44690–44699 | 10 |
| B | `save_clipboard_privacy_settings` | 44701–44722 | 22 |
| B | `_migrate_settings_to_unified` | 44724–44814 | 91 |
| B | `_migrate_to_workbench_layout` | 44816–44881 | 66 |
| B | `_migrate_voice_dictation_default_off` | 45143–45174 | 32 |
| B | `load_dictation_settings` | 44931–44946 | 16 |
| B | `save_dictation_settings` | 44948–45002 | 55 |
| B | `_load_language_pair_from_disk` | 45004–45021 | 18 |
| B | `load_voice_vocabulary_settings` | 45029–45067 | 39 |
| B | `save_voice_vocabulary_settings` | 45069–45092 | 24 |
| B | `load_language_settings` | 45228–45249 | 22 |
| B | `save_language_settings` | 45251–45261 | 11 |
| B | `_save_spellcheck_settings` | 52262–52271 | 10 |
| B | `_load_spellcheck_settings` | 52273–52280 | 8 |
| B | `load_llm_settings` | 56987–57025 | 39 |
| B | `save_llm_settings` | 57027–57034 | 8 |
| B | `load_proxy_settings` | 57040–57056 | 17 |
| B | `save_proxy_settings` | 57058–57065 | 8 |
| B | `_get_proxy_url` | 57067–57089 | 23 |
| B | `_get_proxy_dict` | 57091–57098 | 8 |
| B | `load_provider_enabled_states` | 57283–57309 | 27 |
| B | `save_provider_enabled_states` | 57311–57318 | 8 |
| B | `load_api_keys` | 61235–61243 | 9 |
| B | `save_api_keys` | 61245–61247 | 3 |
| B | `load_recent_projects` | 32306–32368 | 63 |
| B | `save_recent_projects` | 32370–32380 | 11 |
| C | `get_autocorrect_settings` | 44620–44631 | 12 |
| C | `add_to_recent_projects` | 32238–32288 | 51 |
| C | `_remove_from_recent_projects` | 32290–32304 | 15 |
| C | `clear_recent_projects` | 32416–32430 | 15 |
| C | `load_font_sizes_from_preferences` | 45275–45361 | 87 |

Итоги: **A = 6 методов / 39 строк**, **B = 29 / 791**, **C = 5 / 180**;
A+B = **35 / 830**; A+B+C = **40 / 1010**.

Обе названные планом миграции подтверждены точно: `_migrate_settings_to_unified` =
**44724–44814 (91L)**, `_migrate_to_workbench_layout` = **44816–44881 (66L)**.
Третья миграция — `_migrate_voice_dictation_default_off` **45143–45174 (32L)**,
в плане не названа.

**Расхождение с ожиданиями:**
* План «~25 методов» считал только явно названные в `Source` имена; фактическое ядро
  A+B = **35 методов / 830 строк**. План не назвал `load_clipboard_privacy_settings`,
  `save_clipboard_privacy_settings`, `_load_general_settings_from_file`,
  `_load_language_pair_from_disk` и третью миграцию, зато «языки/диктовку/словарь/
  спеллчек/недавние» перечислил одной строкой без методов. «−1 200 строк» из
  `Expected result` недостижимо: verbatim 830 минус ~35 делегатов × 2–4 строки
  ≈ **−700**.
* Координатор «~46 методов / ~1709 строк» — греп «на глаз»: он смешивает состав A+B,
  тир C (UI-соседние `add/remove/clear_recent_projects`,
  `load_font_sizes_from_preferences`, `get_autocorrect_settings`) и часть группы G3
  (`_set_voice_pause_setting`, `save_termbase_code_map`, `_set_fr_demote_to_draft`,
  `_persist_autocorrect_settings` и др.). 35 + 5 + ~6 = 46 — совпадение по числу,
  но не по составу.

**Не входит в состав** (полный скан класса закрыт; доказательство — таблица «вне
состава» в `batch7_stage1_inventory_tables.txt`): G1 bootstrap (5 методов / 906 строк),
G2 UI-вкладки настроек + их `_save_*_from_ui` + навигация (33 / 5 298),
G3 одноразовые писатели секций (19 / 972), G4 проектный/файловый IO (17 / 2 139),
G5 прочий JSON/log-IO (16 / 1 029), G6 голосовой runtime (31 / 1 069),
G7 spellcheck-runtime (8 / 447).


---

## 1.3 Проверка «Circular dependency risks: Нет»

**Вывод: утверждение плана ПОДТВЕРЖДЕНО для состава A+B** (с оговорками по тиру C и
при обязательном сохранении делегатов). Факты:

1. В телах всех 35 методов A+B **нет ни одного `import` из `modules/`** (проверено
   грепом по дампам тел и по `deps`-картам). Единственная внешняя библиотечная
   зависимость — `QMessageBox` (PyQt6) в `save_dictation_settings` (44948–45002).
2. Единственный `from modules.…` в тире C — `get_autocorrect_settings` →
   `from modules.autocorrect import AutoCorrectSettings`. `modules/autocorrect.py`
   монолит не импортирует (0 файлов репозитория импортируют `Supervertaler.py` —
   методика `DEAD_CODE_REPORT.md`, п.12), а вызывают этот метод через
   `main_window.get_autocorrect_settings()` → цикла нет.
3. **Блокер — не цикл, а неразрешимые глобальные имена монолита:**
   * `load_language_settings` (45228–45249) ссылается на `TagHighlighter`
     (класс монолита, строка 2926) и `self.spellcheck_manager` → вне монолита
     `NameError`; «как есть» не переносится (нужно разделение: файловая часть — в
     сервис, побочные эффекты spellcheck — в монолите).
   * `load_font_sizes_from_preferences` (45275–45361, тир C) импортирует
     `modules.translation_results_panel` И ссылается на классы монолита
     `EditableGridTextEditor`, `ReadOnlyGridTextEditor`, `SupervertalerQt`.
   * `add_to_recent_projects` / `_remove_from_recent_projects` / `clear_recent_projects`
     (тир C) используют модульную функцию монолита `_canon_path`,
     `self.current_project`, `self.project_file_path`, `self.MAX_RECENT_PROJECTS`,
     `QMessageBox` и UI-методы `update_recent_menu`/`update_recent_projects_display`.
4. **Обратного направления (сервис → монолит) нет ни в одном варианте:** делегаты
   живут в монолите и импортируют сервис (монолит → `modules.settings_service`).
   Цикл не появится при условии, что `modules/settings_service.py` НЕ импортирует
   `modules/termbase_entry_editor.py`, `modules/voice_tab.py`,
   `modules/clipboard_manager_widget.py`, `modules/quicktrans.py` — они обращаются к
   сервису только через `parent_app`-дукт-тайпинг (в рантайме импорт не нужен).
5. Не-циклическая, но поведенческая мина: `_migrate_settings_to_unified` использует
   `Path(__file__).parent / "user_data_private" / "api_keys.txt"` (44850–44851).
   После переноса `Path(__file__)` укажет на `modules/` → путь станет
   `modules/user_data_private/api_keys.txt` вместо `<repo>/user_data_private/api_keys.txt`.

---

## 1.4 Call sites (фокус — `load_general_settings`)

Полная AST-карта: `batch7_stage1_callsites_categorized.txt` (394 ссылки: 345 call-сайтов,
30 string-ref, 3 attr-ref, 40 def). Ниже сводка.

### 1.4.1 `load_general_settings` — точное число реальных вызовов

* **61 call-сайт**: 60 в монолите + 1 в `modules/quicktrans.py:303`.
  Разбивка 60 монолитных: **56 из методов `SupervertalerQt`**, 1 из
  `PreTranslationWorker.run` (5479), 2 из `SuperlookupTab` (66766 `on_close`,
  66809 `_browse_for_autohotkey`), 1 из модульной функции `main()` (68357 — там же
  `window._load_settings_section("ui")`).
* Плюс **7 string-ref** (обращения по строковому имени):
  1809 `highlight_termbase_matches`, 55545/55554 `_play_sound_effect`,
  64697 `_load_superlookup_landing_pref`, 64712/64713 `_on_landing_pref_changed`,
  7861 `show_term_insert_popup` + `modules/quicktrans.py:302` — все в форме
  `getattr(self, 'load_general_settings', lambda: {})()` («мягкий» duck-typing).
* **Итог: fan-in = 60 вызовов в монолите + 1 внешний (quicktrans) + 7 строковых ссылок.**
  Это больше «до 48» из плана: в плане не учтены `getattr`-формы и вызовы из
  `main()`/`SuperlookupTab`/`PreTranslationWorker`.

Ожидание «свежего чтения» подтверждено для всех не-классовых сайтов:
* `modules/quicktrans.py:300–305 _load_mt_quick_settings()` вызывает
  `parent_app.load_general_settings()` **на каждый** `_get_enabled_providers()` и
  возвращает `settings.get('mt_quick_lookup', {})` — своей копии не хранит;
* `PreTranslationWorker.run` (5479) — читает при старте прогона, между прогонами не
  переиспользует;
* `SuperlookupTab.on_close` / `_browse_for_autohotkey` — читают в момент действия;
* `main()` (68357) — читает один раз после создания окна.

**Кэша результата нет ни в одном сайте:** грепом по репозиторию найдено только
`_row_color_settings_cached` (41116/43976/44093) — производный кэш цветов строк в
`_apply_row_color`, явно сбрасываемый при смене настроек; сам файл он не кэширует.

### 1.4.2 Остальные методы состава (сводка call-сайтов)

| метод | вызовов | mono | modules/ | примечание |
|---|---|---|---|---|
| `_get_settings_dir` | 3 | 3 | 0 | все внутри состава |
| `_get_unified_settings_path` | 4 | 4 | 0 | 22756, 22767, 45369 + внутри состава |
| `_load_unified_settings` | 12 | 11 | 1 | modules-сайт мнимый (наблюдение F1) |
| `_save_unified_settings` | 11 | 10 | 1 | то же (наблюдение F1) |
| `_load_settings_section` | 28 | 27 | 1 | 26 в `SupervertalerQt`, 1 в `main()` (68357), 1 мнимый; 2 string-ref в `modules/clipboard_manager_widget.py` (2284/2298) — реальные duck-typed вызовы |
| `_save_settings_section` | 11 | 11 | 0 | + string-ref clipboard_manager_widget.py:2299 |
| `save_general_settings` | 27 | 27 | 0 | все из `SupervertalerQt` |
| `_load_general_settings_from_file` | 4 | 4 | 0 | 41540, 44295, 44487, 44525 |
| `load_clipboard_privacy_settings` | 1 | 1 | 0 | + string-ref clipboard_manager_widget.py:771 |
| `save_clipboard_privacy_settings` | 1 | 1 | 0 | `_create_clipboard_settings_tab._persist` |
| `_migrate_settings_to_unified` | 2 | 2 | 0 | `__init__:6326`, `_reinitialize_with_new_data_path:6658` |
| `_migrate_to_workbench_layout` | 2 | 2 | 0 | `__init__:6327`, `_reinitialize_with_new_data_path:6659` |
| `_migrate_voice_dictation_default_off` | 1 | 1 | 0 | `__init__:6388` |
| `load_dictation_settings` | 8 | 8 | 0 | + 2 string-ref `modules/voice_tab.py` (736/781) |
| `save_dictation_settings` | **0** | 0 | 0 | PROBABLY_DEAD (см. 1.6), имя публичное |
| `_load_language_pair_from_disk` | 1 | 1 | 0 | `__init__:6337` |
| `load_voice_vocabulary_settings` | 3 | 3 | 0 | + string-ref `modules/voice_tab.py:1239` |
| `save_voice_vocabulary_settings` | **0** | 0 | 0 | DYNAMIC_ENTRY_POINT — живёт через string-ref `modules/voice_tab.py:1280` |
| `load_language_settings` | 1 | 1 | 0 | `__init__:6472` |
| `save_language_settings` | 2 | 2 | 0 | 20791, 45267 |
| `_save_spellcheck_settings` | 2 | 2 | 0 | |
| `_load_spellcheck_settings` | 1 | 1 | 0 | 27238 |
| `load_llm_settings` | 28 | 24 | 4 | `chat_backend.py:139`, `chat_view_widget.py:737`, `quicktrans.py:370,454` (+4 string-ref) |
| `save_llm_settings` | 3 | 3 | 0 | |
| `load_proxy_settings` | 2 | 2 | 0 | |
| `save_proxy_settings` | 1 | 1 | 0 | |
| `_get_proxy_url` | 15 | 13 | 2 | `chat_backend.py:150`, `chat_view_widget.py:745` (+2 string-ref) |
| `_get_proxy_dict` | 5 | 5 | 0 | 5 MT-вызовов (google/deepl/microsoft/modernmt/mymemory) |
| `load_provider_enabled_states` | 13 | 12 | 1 | `quicktrans.py:326` (+string-ref) |
| `save_provider_enabled_states` | 3 | 3 | 0 | |
| `load_api_keys` | 45 | 35 | 10 | в modules/ свои реализации: `llm_clients.py:1864/1901` (свой `def load_api_keys`, стр. 43); duck-typed `parent_app.load_api_keys()` в `quicktrans.py:324,440`, `chat_backend.py:101,103`, `chat_view_widget.py:712,714`, `pdf_rescue_Qt.py:55` |
| `save_api_keys` | 1 | 1 | 0 | 26490 |
| `load_recent_projects` | 5 | 5 | 0 | `update_recent_menu`, `add/_remove_from_recent_projects`, `update_recent_projects_display`, `restore_last_project_if_enabled` |
| `save_recent_projects` | 3 | 3 | 0 | `add/remove/clear_recent_projects` |
| `get_autocorrect_settings` (C) | 1 | 1 | 0 | вызов из `modules/autocorrect.py` по атрибуту duck-typed `main_window` |
| `add_to_recent_projects` (C) | 2 | 2 | 0 | |
| `_remove_from_recent_projects` (C) | 1 | 1 | 0 | `load_project:30446` |
| `clear_recent_projects` (C) | 0 | 0 | 0 | только attr-ref (QAction connect, 32421) → DYNAMIC_ENTRY_POINT/MENU_ACTION |
| `load_font_sizes_from_preferences` (C) | 1 | 1 | 0 | `__init__:6501` |

**«Не кэшируется» — проверка по внешним сайтам:** все duck-typed потребители
(`quicktrans`, `chat_backend`, `chat_view_widget`, `voice_tab`,
`clipboard_manager_widget`, `autocorrect`) вызывают метод **в момент потребности**
(открытие поповера, выбор модели, нажатие клавиши, чтение буфера, ввод символа) и не
сохраняют результат дольше одного вызова. Для `get_autocorrect_settings` это прямо
записано в докстринге: «каждое нажатие клавиши… передаёт свежий снимок настроек».

`lru_cache`/`functools.cache` в монолите и в методах состава отсутствуют.

   В Stage 2 корень репозитория надо передавать явно.


---

## 1.5 Зависимости / отношение к существующему ConfigManager

Полные карты `self.*`-атрибутов и вызываемых имён — в `batch7_stage1_dependencies.txt`.
Сводка по типам внешних зависимостей состава A+B (35 методов):

| тип зависимости | методы | вывод для Stage 2 |
|---|---|---|
| **только путь к настройкам** (`self.user_data_path` / `self._get_settings_dir()`) + `json`/`open` | `_get_settings_dir`, `_get_unified_settings_path`, `_load_unified_settings`, `_save_unified_settings`, `_load_settings_section`, `_save_settings_section`, `_load_general_settings_from_file`, `save_general_settings`, `load_dictation_settings`, `_load_language_pair_from_disk`, `load_voice_vocabulary_settings`, `save_voice_vocabulary_settings`, `_save_spellcheck_settings`, `_load_spellcheck_settings`, `load_llm_settings`, `save_llm_settings`, `load_proxy_settings`, `save_proxy_settings`, `_get_proxy_url`, `_get_proxy_dict`, `load_provider_enabled_states`, `save_provider_enabled_states`, `load_api_keys`, `save_api_keys`, `load_recent_projects`, `save_recent_projects` (26) | переносятся чисто; путь передавать явно |
| **путь + `self.log`** | `_save_unified_settings`, `save_general_settings`, `load_clipboard_privacy_settings`, `save_clipboard_privacy_settings`, `save_dictation_settings`, `save_language_settings`, `_save_spellcheck_settings`, `save_llm_settings`, `save_proxy_settings`, `save_provider_enabled_states`, `_migrate_voice_dictation_default_off`, `load_recent_projects`, `save_recent_projects` (13; пересекается с предыдущей строкой) | нужен инъектируемый лог-колбэк (или `log=None` в сервисе/функции) |
| **доп. состояние экземпляра** | `save_recent_projects` (`self.recent_projects_file` + `self.user_data_path.mkdir`), `load_recent_projects` (`self.recent_projects_file`) | путь `recent_projects.json` = `settings_dir/"recent_projects.json"` (задаётся в `__init__:6419`, переприсваивается в 6701) — в сервис передавать как отдельный путь |
| **UI-виджет/логика** | `save_clipboard_privacy_settings` (`self._clipboard_top_widget.refresh_privacy_settings()`), `save_dictation_settings` (`QMessageBox.information/warning(self, …)`), `load_language_settings` (`TagHighlighter.set_spellcheck_enabled`, `self.spellcheck_manager`), `_migrate_voice_dictation_default_off` (`self.db_manager`) | «как есть» не переносятся: либо SPLIT (файловая часть → сервис, эффект → монолит), либо остаётся в монолите |
| **специфично для миграции** | `_migrate_settings_to_unified` (`Path(__file__)` → repo-root, `self.user_data_path`, `json`, `shutil`), `_migrate_to_workbench_layout` (`datetime.utcnow`, `shutil`, `write_text`) | переносятся, но repo-root передавать явно (см. 1.3 п.5) |
| **прочее** | `save_dictation_settings` дополнительно `os.environ`/`os.path.expanduser` (инфо о whisper-кэше) | безвредно |

**Дублирует ли состав существующую логику ConfigManager?** Формально — да, ровно в
одной точке: `ConfigManager.get_preferences_path()` (config_manager.py:358–361) даёт
тот же файл `<user_data>/workbench/settings/settings.json`, а
`load_preferences()`/`save_preferences()` (363–395) читают/пишут ту же секцию `"ui"`
с теми же `indent=2, ensure_ascii=False`. Но:

* **реальных call-sites у этих трёх методов ConfigManager — 0** (грепом по всему
  репозиторию: только определения; `feature_manager.py` имеет собственные
  `_load_preferences`/`_save_preferences`, которые к ConfigManager не обращаются);
* **разные форматы данных — нет**: формат тот же (единый settings.json), пересечение
  настоящее, просто вторая реализация мертва;
* **ортогонально — разрешение пути**: `ConfigManager` резолвит user_data через
  `~/.supervertaler_config.json` (или dev-флаг `.supervertaler.local`), а монолит —
  через `get_config_pointer_path()` = `%APPDATA%/Supervertaler/config.json`
  (см. `batch7_stage1_config_manager_overlap.txt`, блок B). Это **разные**
  указатели: сервис, который сам позовёт `ConfigManager.get_user_data_path()`, может
  молча уйти на другой каталог.

**Тот же файл читают/пишут ещё 4 места** (не монолит): `modules/feature_manager.py`
(секция `features`), `modules/ui_scale.py` (`_read_scale_from_disk`),
`modules/llm_clients.py:43 load_api_keys()` (секция `api_keys` + свой резолвер пути),
`modules/termbase_entry_editor.py` (мнимые вызовы, наблюдение F1).

---

## 1.6 DYNAMIC_ENTRY_POINT / строковые ссылки

Сверка 40 имён состава с `DEAD_CODE_REPORT.md` (`batch7_stage1_dead_dynamic_check.txt`):
совпало **4 из 40**; остальные 36 в отчёте не упоминаются вообще.

| метод | статус в отчёте | механизм | следствие для Stage 2 |
|---|---|---|---|
| `save_voice_vocabulary_settings` | DYNAMIC_ENTRY_POINT (строка 48738 в старом счёте; №137) | EXTERNAL_ATTR_REF | имя/сигнатуру сохранять точно; вызов — `getattr(self._parent_app, 'save_voice_vocabulary_settings')` в `modules/voice_tab.py:1280` |
| `get_autocorrect_settings` | DYNAMIC_ENTRY_POINT (№136) | EXTERNAL_ATTR_REF | вызов `main_window.get_autocorrect_settings()` из `modules/autocorrect.py` — только атрибутный доступ |
| `clear_recent_projects` | DYNAMIC_ENTRY_POINT (№90) | MENU_ACTION | подключён к QAction (32421) — обычный делегат-метод (не `@staticmethod`) |
| `save_dictation_settings` | PROBABLY_DEAD → «Публичные zero-ref» (№24, 55L) | 0 ссылок | переносить как есть (прецедент `filter_empty_segments` в Step 6); **не удалять** — план этого не разрешает |

Остальные 36 имён в `DEAD_CODE_REPORT.md` отсутствуют → DYNAMIC_ENTRY_POINT-риска для
них нет, но **дукт-тайпед-обращения из `modules/` найдены отдельно** (их грепом по
отчёту не видно): `modules/clipboard_manager_widget.py` (строки 771, 2284, 2298),
`modules/voice_tab.py` (736, 781, 1061, 1239, 1280),
`modules/quicktrans.py` (302, 323, 325, 370, 439, 454) — то есть правила Step 6
(«делегаты с точными исходными именами, включая ведущий `_`») обязательны и здесь.
Итог: **строгий режим — 35 тонких делегатов с исходными именами и сигнатурами,
включая 29 имён с ведущим `_`.**


---

## 1.7 Рекомендация по архитектуре (решение — за владельцем)

**Рекомендация: вариант (б) в модифицированной форме — новый
`modules/settings_service.py` с классом, который конструируется ЯВНЫМ путём
(`settings_dir: Path`, опционально `log: Callable[[str], None]`), и НЕ резолвит
user_data через `ConfigManager.get_user_data_path()`.** ConfigManager при этом
остаётся владельцем «где лежит user_data» только для внешнего мира (и, если владелец
захочет, его дубликаты `load_preferences`/`save_preferences` выводятся из
эксплуатации отдельным решением).

Обоснование по фактам 1.5 (а не «как в Step 5/6»):

1. **Всему составу нужны ровно два внешних входа: путь к каталогу настроек и
   лог-колбэк.** 26 из 35 методов не нуждаются даже в логе; 13 — только в логе;
   3 — в пути `recent_projects.json`; 4 — в UI/БД и потому не переносятся «как есть».
   Это делает сервис с двумя полями максимально простым и лишает смысла любую
   «обёртку с состоянием».
2. **Путь нельзя брать из ConfigManager без риска:** ConfigManager резолвит
   user_data из `~/.supervertaler_config.json`/dev-флага (config_manager.py:58–82),
   а монолит — из `%APPDATA%/Supervertaler/config.json`
   (`get_config_pointer_path`, Supervertaler.py:~170) → сервис, вызвавший
   `ConfigManager.get_user_data_path()`, может получить ДРУГОЙ каталог и молча
   читать/писать чужой `settings.json`. Явный `settings_dir` (тот самый
   `self.user_data_path / "workbench" / "settings"`) снимает этот риск без унификации.
3. **Вариант (а) «расширить ConfigManager» отклонён:** (i) он тянет за собой
   bootstrap первого запуска и свой указатель (см. п.2); (ii) в нём уже лежат
   `load_preferences`/`save_preferences` для ЭТОГО ЖЕ файла с 0 call-sites —
   при расширении владельцу пришлось бы разруливать их судьбу внутри того же
   механического батча; (iii) класс разросся бы до смешанной ответственности
   (bootstrap + формат settings + дефолты секций).
4. **Вариант (в) «чистые функции с явными параметрами» (стиль Step 6) рабочий, но
   проигрывает по одному пункту:** у сервиса есть общий инвариант —
   гарантия четырёх секций (`api_keys/general/ui/features`) и дефолты доменных
   аксессоров. Как функции это разъедется по модулю без единой точки контракта;
   как класс это одна точка («один владелец формата»), при этом класс остаётся
   stateless между вызовами (никакого кэша — см. 1.9).
5. **Делегаты обязательны независимо от выбора:** 11 внешних дукт-тайпед-консументов
   обращаются к 6 разных именам, включая приватные (`_load_unified_settings`,
   `_save_unified_settings`, `_load_settings_section`, `_save_settings_section`,
   `_get_proxy_url`) — имена и сигнатуры в монолите сохраняются 1:1 (прецедент Step 6).

**SPLIT-методы (перенос только файловой части, эффект остаётся в делегате):**

| метод | что в сервис | что остаётся в монолите |
|---|---|---|
| `load_general_settings` (97L) | чтение файла + merge дефолтов + миграция `termview_*`→`termlens_*` (это `_load_general_settings_from_file`) | 35 присваиваний `self.<attr>` + вызов `self.load_llm_settings()` (делегат: `settings = service.read_general_settings(...)` → тот же код применения) |
| `save_clipboard_privacy_settings` (22L) | чтение/запись секции `features` | `self._clipboard_top_widget.refresh_privacy_settings()` |
| `save_dictation_settings` (55L) | чтение/запись секции `ui.dictation_settings` | `QMessageBox.information/warning(self, …)` (UI) |
| `load_language_settings` (22L) | ничего (только чтение секции `ui`) | `TagHighlighter.set_spellcheck_enabled`, `self.spellcheck_manager.set_language`, `self.log` |
| `_migrate_voice_dictation_default_off` (32L) | запись сентинелы в `ui` | `self.db_manager` UPDATE + commit |

**Остаются в монолите без изменений (рекомендация):** `load_font_sizes_from_preferences`,
`get_autocorrect_settings`, `add_to_recent_projects`, `_remove_from_recent_projects`,
`clear_recent_projects` (тир C) — все опираются на глобальные имена монолита
(`TagHighlighter`, `EditableGridTextEditor`, `ReadOnlyGridTextEditor`,
`SupervertalerQt`, `_canon_path`) или UI-оркестрацию.

**Вне Step 7 (отдельные решения владельца, НЕ в Stage 2):** унификация
трёх механизмов указателя user_data (F5), вывод из эксплуатации дубликатов
`ConfigManager.load_preferences/save_preferences` (F4), `modules/llm_clients.load_api_keys`
(F2), прямых читателей в `feature_manager`/`ui_scale` (F3), баг `termbase_entry_editor`
(F1).


---

## 1.8 Рекомендация по разбивке Stage 2+ на под-батчи

35 методов одним коммитом — неприемлемо (в Step 6 `filters.py` = 20 методов потребовал
трёх моделей на Этапе 3). Предлагаю **5 под-батчей**, порядок — от самого простого и
«фундаментного» к самому рискованному; каждый под-батч атомарен и оставляет
работающие делегаты:

| # | под-батч | методы | строк | call-sites (вне состава) | почему в таком порядке |
|---|---|---|---|---|---|
| S2.1 | **Ядро API** | `_get_settings_dir`, `_get_unified_settings_path`, `_load_unified_settings`, `_save_unified_settings`, `_load_settings_section`, `_save_settings_section` (6) | 39 | 3+4+12+11+28+11 = 69 (из них ~40 из методов, которые сами поедут дальше; 2 `string` в clipboard-виджете; `main()`:68357) | фундамент для остальных; 2 строки `string`-refs в `modules/clipboard_manager_widget.py` и `main()` дают раннюю проверку режима делегатов; при ошибке откат одного коммита |
| S2.2 | **general + общий reading** | `_load_general_settings_from_file`, `save_general_settings`, `load_general_settings` (SPLIT), `load_clipboard_privacy_settings`, `save_clipboard_privacy_settings` (SPLIT) (5) | 40+6+97+10+22 = 175 | `load_general_settings` 61 + `save_general_settings` 27 + 1 + 1 = 90 → **самый высокий fan-in** | требует, чтобы S2.1 был уже в сервисе; из-за fan-in 90 и SPLIT именно этот под-батч надо проверять функционально (полный цикл настроек + перезапуск) |
| S2.3 | **LLM / proxy / provider / api keys** | `load_llm_settings`, `save_llm_settings`, `load_proxy_settings`, `save_proxy_settings`, `_get_proxy_url`, `_get_proxy_dict`, `load_provider_enabled_states`, `save_provider_enabled_states`, `load_api_keys`, `save_api_keys` (10) | 47+25+23+8+35+12 = 150 | 28+3+2+1+15+5+13+3+45+1 = 116, из них 10 в `modules/` (chat_backend/chat_view_widget/quicktrans/pdf_rescue) + 10 string-ref | **ровно 10 методов — отметить в живом чек-листе Этапа 2**; под-батч держит весь сетевой слой настроек вместе (провайдеры + прокси + ключи) — удобно тестировать в одном прогоне «AI/MT вкладка → перезапуск» |
| S2.4 | **Языки / диктовка / словарь / спеллчек-IO** | `load_dictation_settings`, `save_dictation_settings` (SPLIT), `_load_language_pair_from_disk`, `load_voice_vocabulary_settings`, `save_voice_vocabulary_settings`, `load_language_settings` (SPLIT), `save_language_settings`, `_save_spellcheck_settings`, `_load_spellcheck_settings` (9) | 16+55+18+39+24+22+11+10+8 = 203 | 8+0+1+3+0+1+2+2+1 = 18, из них 4 string-ref в `modules/voice_tab.py` | периферия, но с двумя SPLIT и живыми duck-typed потребителями (`voice_tab`) — проверять голосовую вкладку отдельно |
| S2.5 | **Recent projects + миграции** | `load_recent_projects`, `save_recent_projects`, `_migrate_settings_to_unified`, `_migrate_to_workbench_layout`, `_migrate_voice_dictation_default_off` (SPLIT) (5) | 63+11+91+66+32 = 263 (или 231 без SPLIT-метода) | 5+3+2+2+1 = 13 | миграции одноразовые, но необратимо двигают файлы пользователя → отдельный коммит с валидацией «на копии старого user_data»; здесь же `Path(__file__)`-мина и `recent_projects_file` |

Итого 6 + 5 + 10 + 9 + 5 = **35 методов / 830 строк**, ни один под-батч не превышает
10 методов (S2.3 — ровно 10, граница по конвенции Этапа 2).

**Порядок обоснован не размером, а типом риска:** S2.1 — «нет потребителей кроме
своих», S2.2 — максимальный fan-in, но маленький состав, S2.3 — много call-sites, но
все потребители изолированы (сеть/AI), S2.4 — SPLIT + duck-typed, S2.5 — единственный
под-батч с необратимыми файловыми операциями.

**Альтернативная опция для владельца:** не делать SPLIT-методы вообще, оставив
`load_general_settings`, `save_clipboard_privacy_settings`, `save_dictation_settings`,
`load_language_settings`, `_migrate_voice_dictation_default_off` целиком в монолите
(тогда состав сжимается до 30 методов / ~590 строк, но `load_general_settings` перестаёт
быть «единым владельцем» чтения general-секции: читать её будет только сервис через
`_load_general_settings_from_file`, а монолит — только применять к `self`).

---

## 1.9 Семантика «чтение с диска при каждом вызове» — ЗАФИКСИРОВАНО

**Подтверждено фактами:** ни один метод состава (и ни одна внешняя обёртка) не кэширует
результат между вызовами.
* `_load_unified_settings` (44647–44661) на каждом вызове делает
  `open(settings_file)` + `json.load`; `_load_settings_section`/`load_general_settings`/
  `load_llm_settings`/… — цепочки, ведущие к нему (никаких полей-кэшей у класса нет:
  грепом `_settings_cache|_cached_settings|lru_cache|functools` — 0 совпадений в
  методах состава).
* Единственный settings-derived кэш в монолите — `_row_color_settings_cached`
  (`_apply_row_color`, вне состава) — производный от цветов строк, сбрасывается явно
  (41116/44093) и файл не кэширует.
* Внешние потребители читают «по требованию» (см. 1.4.1); `modules/autocorrect.py`
  вообще рассчитывает на снимок на КАЖДОЕ нажатие клавиши.

**ОБЯЗАТЕЛЬНОЕ требование для Stage 2+ (не оптимизировать!):**
1. Перенесённый код должен **открывать файл заново на каждый вызов** — никакого
   `lru_cache`, никакого «прочитал один раз в `__init__` сервиса», никакого
   `self._settings`-кэша в делегате.
2. SPLIT-делегаты обязаны вызывать сервис **на каждом** вызове (не сохранять
   прочитанный dict в атрибут окна), иначе 7 `getattr`-сайтов и `modules/*`
   потребители увидят устаревшие данные.
3. При ревью Stage 2 проверять это явно (в отчёте под-батча: «файл открывается N раз
   за прогон сценария; кэша нет — подтверждено»). Любая идея «заодно закэшировать»
   отклоняется как противоречащая плану.


---

## Наблюдения вне скопа (НЕ чинилось, фиксируется для владельца)

* **F1 — латентный баг в `modules/termbase_entry_editor.py`.** `_load_termbase_selections`
  (строка 121) и `_save_termbase_selections` (строка 131) вызывают
  `self._load_settings_section("ui")` / `self._load_unified_settings()` /
  `self._save_unified_settings(...)`, но класс `TermbaseEntryEditor(QDialog)` этих
  методов НЕ определяет (AST: 35 методов, ни одного из трёх; `_parent_app`/`__getattr__`
  отсутствуют). Исключение глотается `except Exception` → выбор терминологий в диалоге
  не сохраняется и не читается (тихий no-op). Это НЕ потребители монолитного API
  (мой AST-скан отнёс их к `_load_settings_section`/`_load_unified_settings` лишь
  по имени) → на состав Step 7 не влияет, но требует решения владельца.
* **F2 — дубликат чтения ключей:** `modules/llm_clients.py:43 load_api_keys()` со своим
  разрешением user_data-пути (APPDATA/…/config.json) — вторая реализация того же
  контракта, что `load_api_keys` в монолите (61235–61243).
* **F3 — прямые читатели того же файла:** `modules/feature_manager.py` (секция
  `features`), `modules/ui_scale.py` (`_read_scale_from_disk`), плюс
  `modules/voice_tab.py`/`modules/clipboard_manager_widget.py` (через `parent_app`).
  Цель «единый владелец формата settings» без их унификации не достигается.
* **F4 — мёртвые дубликаты в ConfigManager:** `get_preferences_path` (358),
  `load_preferences` (363), `save_preferences` (375) — 0 call-sites в репозитории,
  а работают с тем же файлом/секцией, что и монолитное ядро.
* **F5 — три механизма указателя user_data:** монолит `get_config_pointer_path()`
  (`%APPDATA%/Supervertaler/config.json`), ConfigManager
  (`~/.supervertaler_config.json` + dev-флаг `.supervertaler.local`),
  `modules/llm_clients.py` (копия APPDATA-варианта). AGENTS.md упоминает
  `~/.supervertaler_config.json` как «глобальный», т.е. фактически описывает
  ConfigManager, а не реальный указатель приложения.
* **F6 — `load_general_settings` не является «IO-методом»:** 2 строки чтения из 97;
  остальное — 35 присваиваний `self.<attr>` + чтение LLM-настроек. План называет его
  IO-методом Step 7, что может привести к неверной оценке объёма переноса.
* **F7 — `save_dictation_settings` (PROBABLY_DEAD, 55L)** при переносе затащит в
  сервис `QMessageBox` и требует `self`-окна как parent → либо SPLIT, либо остаётся
  в монолите; удалять его нельзя (в плане не разрешено, и `DEAD_CODE_REPORT.md`
  рекомендует сначала подтверждение владельца).
* **F8 — `load_font_sizes_from_preferences`** (тир C) — единственный кандидат, где
  «IO» и UI-применение переплетены так, что механический перенос невозможен без
  `NameError` (ссылки на `EditableGridTextEditor`/`ReadOnlyGridTextEditor`/
  `SupervertalerQt` — классы монолита).
* **F9 — заметка о кэше:** `_row_color_settings_cached` (41116/43976/44093) —
  единственный производный кэш настроек; при будущем Step 7+/рефакторинге цветов
  строк надо помнить, что он явно инвалидируется.

---

## Подтверждение READ-ONLY и артефакты

* `git status` до и после работы: изменённых файлов кода нет.
* `git hash-object Supervertaler.py` (`802c504c8849ac58551bece6b297917426e31226`) ==
  `git rev-parse HEAD:Supervertaler.py` — монолит байт-в-байт как в HEAD.
* Ни `modules/settings_service.py`, ни иные файлы-заглушки не создавались;
  `modules/config_manager.py` не трогался.
* Все измерения регенерируемы скриптами из
  `D:\Temp\SupervertalerPortable\refactoring\batch7_stage1\run-001\`
  (`inv.py methods|audit|gaps|body|deps|calls`, `usage.py`, `dump_methods.py`,
  `callsites_scan.py`, `summarize.py`, `dead_check.py`, `gen_tables.py`,
  `publish_artifacts.py`).
* Номера строк класса пересчитаны AST на HEAD `b5c46e7`; измерение длины монолита —
  Python-скриптом (68 386 строк). Примечание по инструментам: PowerShell
  `(Get-Content … | Measure-Object -Line)` на этом файле даёт 63 195 — некорректно
  из-за особенностей обработки переводов строк; для счётчиков строк использовать
  Python/`wc -l` (зафиксировано наблюдением, в код ничего не менялось).

