# Batch #8.12 — Финальный инвентарь сирот и остатков (READ-ONLY, docs-only)

**Репозиторий:** dcdlab-ai/SupervertalerPortable • **Исполнитель:** ZCode • **Дата:** 2026-10-10
**Основание:** `docs/refactoring/prompts/Promt - Batch #8.12.txt`; решения Дмитрия по 8.4, 8.7, 8.8, 8.9, 8.10, 8.11 (POST_BATCH8_BACKLOG.md §4/§7/§10, разделы «Решения» отчётов BATCH8_*); база кода — `d308a93f` (8.11).
**Код не менялся.** Единственное изменение в репо — этот отчёт + ссылка в POST_BATCH8_BACKLOG.md + строка в PROJECT_STATUS.md.

---

## 0. Baseline и git-синхронизация

| Пункт | Значение |
|---|---|
| HEAD | `28799a82` (docs 8.11 §9) |
| origin/main | `28799a82` (после `git fetch origin` — совпадает) |
| git status | чистый; untracked: `.zcode/plans/…`, `.zcodeignore`, файл промпта 8.12 (допустимо) |
| Дрейф-чек | `git merge-base --is-ancestor d308a93f HEAD` → **0** (предок) |
| SHA256 Supervertaler.py | `aab1f180e5789878c014d6042a0ee1a29c9e7bdf1d85dbb02e0722f3604f7644` (57010 строк) — **совпадает** |
| py_compile всего репо | OK (110 модулей + Supervertaler.py + setup.py + tools/tests) |
| modules/**/*.py | **110** (git ls-tree HEAD; в промпте «111» — это headless-инвентарь 110 модулей + `setup.py`) |
| Headless-импорт | **104 ok / 7 fail / 111** (tkinter×4, GlossaryInfo, fitz, setuptools) — `headless_before.txt` |
| pyflakes | **149** undefined-name строк (12 уникальных имён) — `undefined_names_before.txt` |

**Важное уточнение метода (Этап 2):** первичный AST-скан Section A содержал баг резолвера
(`resolve_rel` дописывал имя пакета к **абсолютным** импортам `from modules.X import Y` внутри
`modules/*.py`, порождая фантомные рёбра `modules.modules.X`). Из-за этого модули, импортируемые
только живыми модулями, ложно попадали в список сирот (32 вместо 17). Баг пойман независимой
grep-проверкой Этапа 2, резолвер исправлен в обоих скриптах (`importer_scan.py`, `reach.py`),
все производные таблицы пересчитаны. Все цифры отчёта — из пересчитанных артефактов
(`reach_v3.txt`, `importers.json`, `dep_scan_v2.txt`).

---

## 1. Сводка по разделам

| Раздел | Пунктов | УДАЛИТЬ-БЕЗОПАСНО | УДАЛИТЬ-ПО-РЕШЕНИЮ | ОСТАВИТЬ-ЖИВОЕ | ДОК-ОСТАТОК | ТРЕБУЕТ РЕШЕНИЯ | Объём строк |
|---|---|---|---|---|---|---|---|
| A. Модули-сироты | 17 | 17 | 0 | 0 | 0 | 0 | 6734 |
| B. Зависимости | 32 пакета | 11 (0 потребителей) | 1 (faster-whisper) | 20 | 0 | 0 | requirements/pyproject |
| C. statuses.py | 4 | 1 (import) | 3 (2 функции + поля) | 1 (STATUSES/get_status) | 0 | 0 | ~60 |
| D. UI TM-бриджа | 1 зона | 1 (пробa зелёная) | 0 | 1 (колонка БД + сеттер) | 0 | 0 | 69 (с комментариями) |
| E. Undefined names | 12 имён | 15 строк (show_about) | 0 | 126 (tkinter tmx_editor) | 0 | 2 (e, LLMClient) | — |
| F. Headless-падения | 7 | 6 (входят в A) | 0 | 1 (fitz/pdf_rescue_Qt) | 0 | 0 | — |
| G. Настройки | 8+6 ключей | 0 (ключи не трогаем) | 8 (мёртвые дефолты/читатели) | 1 (translator_name) | 0 | 6 (читатели — сироты) | ~15 |
| H. main() + мёртвые методы | 2+63 | 2 (комменты main) | 63 метода | 0 | 0 | 0 | 2683 + 5 |
| I. Док-остатки в коде | ~250 Trados + 10 прочих | 4 (константы HelpTopics) | 0 | ~210 (правило) | ~40 правок + 10 прочих | 1 (voice-методы termbase_manager) | ~55 правок |
| J. Документы репо | 10 | 0 | 0 | 0 | 10 | 0 | заметки ~60–120 |
| K. Итоги Batch #8 | справочно | — | — | — | — | — | — |

---

## 2. Разделы A–K

### A. Модули-сироты (17 модулей, 6734 строк, 0 импортёров)

Метод: AST-скан всех форм (`import`, `from` incl. relative, `importlib.import_module`,
`__import__`, getattr/hasattr/setattr-литералы, строковые пути `modules.X`/`modules/X`/
`modules\X`/`X.py`) по всем `.py` + grep по `.bat/.spec/.toml/.cfg/.json/.iss` — 0 нон-питон
ссылок; BFS от корней {Supervertaler, setup, tools/**, tests/**}. Кросс-проверка третьим
методом (plain-text grep всех форм, self исключён): **17/17 подтверждены, 0 импортёров**.
Каскада нет: ни один живой модуль не импортируется исключительно сиротами (проверено BFS).

| ID | Модуль | Строк | Класс | Примечание |
|---|---|---|---|---|
| A-01 | modules/extract_tm.py | 518 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |
| A-02 | modules/feature_manager.py | 342 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров FEATURE_MODULES (решение 8.10 §8.1 — отложено сюда); импортирует QtWebEngine (95, 312) |
| A-03 | modules/find_replace.py | 164 | УДАЛИТЬ-БЕЗОПАСНО | tkinter-версия; живая — `find_replace_qt.py` |
| A-04 | modules/glossary_manager.py | 429 | УДАЛИТЬ-БЕЗОПАСНО | NameError `GlossaryInfo` при импорте (E-03); 0 импортёров → NameError недостижим |
| A-05 | modules/identifier_conventions.py | 83 | УДАЛИТЬ-БЕЗОПАСНО | ссылка только в комментарии termbase_manager.py:1101 |
| A-06 | modules/pdf_rescue_tkinter.py | 910 | УДАЛИТЬ-БЕЗОПАСНО | tkinter; живая — pdf_rescue_Qt |
| A-07 | modules/project_home_panel.py | 209 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |
| A-08 | modules/project_tm.py | 320 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |
| A-09 | modules/prompt_assistant.py | 360 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |
| A-10 | modules/prompt_library.py | 689 | УДАЛИТЬ-БЕЗОПАСНО | tkinter; живая — unified_prompt_library (импортируется live unified_prompt_manager_qt) |
| A-11 | modules/quick_access_sidebar.py | 278 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |
| A-12 | modules/ribbon_widget.py | 608 | УДАЛИТЬ-БЕЗОПАСНО | ссылка только в закомментированной строке Supervertaler.py:9013 |
| A-13 | modules/style_guide_manager.py | 315 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |
| A-14 | modules/superdocs.py | 20 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров (строка в superdocs_viewer_qt.py:11 — текст про удалённый viewer) |
| A-15 | modules/superdocs_viewer_qt.py | 305 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |
| A-16 | modules/tracked_changes.py | 903 | УДАЛИТЬ-БЕЗОПАСНО | tkinter; 0 импортёров |
| A-17 | modules/translation_services.py | 281 | УДАЛИТЬ-БЕЗОПАСНО | 0 импортёров |

Цепочки «единственный импортёр — сирота» после исправления резолвера: **нет** (все 17 — листья;
например `tmx_editor` импортируется живым `tmx_editor_qt`, `chat_backend`/`chat_view_widget`/
`unified_prompt_library`/`llm_pricing` — живыми модулями, `statistics_analyzer` — живым
`statistics_dialog_qt`, `config_manager` — живым `file_dialog_helper`, `database_migrations` —
живым `database_manager`, `document_analyzer`/`ai_*`/`prompt_library_migration` — живым
`unified_prompt_manager_qt`).

Ручная проверка: старт приложения; Tools → TMX Editor, PDF Rescue, Statistics, Pseudo-translate;
AI-ассистент (prompt manager, chat); импорт файла (file_dialog_helper).

### B. Зависимости (requirements.txt + pyproject.toml)

Метод: top-level имена пакетов из метаданных установленного бандла (`importlib.metadata`),
AST-поиск импортёров, разбивка live/orphan по `reach_v3.txt`; транзитивные зависимости —
`Requires-Dist` установленных пакетов.

| Пакет | Импортёры | Транзитивно | Вывод |
|---|---|---|---|
| setuptools, wheel | setup.py (build) | — | ОСТАВИТЬ (build-tools) |
| PyQt6 | 46 live-файлов | — | ОСТАВИТЬ |
| **PyQt6-WebEngine** (только pyproject `web`) | **0** (после 8.10; строка в feature_manager) | — | **УДАЛИТЬ из pyproject** (extras и так пустые no-op) |
| python-docx | 4 live | требует **lxml** | ОСТАВИТЬ |
| **lxml** | **0 прямых** | нужен python-docx | **УДАЛИТЬ из прямого списка** (requirements.txt:18, pyproject:66); пакет останется транзитивно; `pip uninstall lxml` НЕ предлагать |
| openpyxl, Pillow, requests, markitdown, pyspellchecker, spylls, PyMuPDF, boto3, deepl, psutil, pynput, pyobjc-framework-Cocoa | ≥1 live | — | ОСТАВИТЬ |
| openai, anthropic, google-generativeai | 2 live (llm_clients, pdf_rescue_Qt) | — | ОСТАВИТЬ |
| pyperclip | 2 live | — | ОСТАВИТЬ |
| **sacrebleu** | **0** | — | **УДАЛИТЬ** (Superbench удалён ранее) |
| **chardet** | **0** | requests[use-chardet-on-py3] extra (не ставится) | **УДАЛИТЬ** |
| **pyyaml** | **0** | markdown[testing] extra | **УДАЛИТЬ** |
| **markdown** | **0** | — | **УДАЛИТЬ** |
| **numpy** | **0** | — | **УДАЛИТЬ** |
| **sounddevice** (pyproject voice) | **0** | — | **УДАЛИТЬ** |
| **ahk** (pyproject windows; из requirements уже убран) | **0** | — | **УДАЛИТЬ из pyproject**; `pip uninstall ahk` в тестовой сборке — при пересборке (решение 8.10 §8.3) |
| **vosk** (pyproject voice) | **0** | — | **УДАЛИТЬ** |
| **faster-whisper** (pyproject local-whisper) | 1 — **только feature_manager (A-02)** | — | **УДАЛИТЬ** (после удаления A-02) |

pyproject extras `local-whisper/voice/web/pdf/mt/hunspell/windows/core/all` — пустые no-op
(ссылок на удалённые пакеты в коде 0). `setup.py` остаётся как PyPI-метаданные (решение 8.9 §9;
keywords memoQ/Trados/SDLPPX не править). Для запуска из `python-embed` (вход в P2-slimming):
ядро = PyQt6, python-docx, openpyxl, Pillow, requests, markitdown, pyspellchecker, spylls,
PyMuPDF, boto3, deepl, psutil, pynput (+pyobjc на macOS), openai/anthropic/google-generativeai.

Ручная проверка: установка из урезанного requirements в чистый embed-рантайм; старт; сценарии
DOCX/XLSX/PDF/TMX; проверка орфографии; MT-провайдеры.

### C. modules/statuses.py (+ соседи)

| ID | Что | Где | Доказательство | Класс |
|---|---|---|---|---|
| C-01 | `match_memoq_status` | statuses.py:185–226 | AST-def_scan + grep: 0 вызовов вне statuses.py (решение Дмитрия 8.9 §9.1 — удалить) | УДАЛИТЬ-ПО-РЕШЕНИЮ |
| C-02 | `compose_memoq_status` | statuses.py:229–242 | 0 вызовов | УДАЛИТЬ-ПО-РЕШЕНИЮ |
| C-03 | поля `memoq_label`, `memoQ_equivalents` (13 литералов STATUSES) | statuses.py:14–15, 41–163 | читаются ТОЛЬКО C-01/C-02; после их удаления — 0 читателей | УДАЛИТЬ-ПО-РЕШЕНИЮ (словарь данных; можно оставить как документацию статусов memoQ) |
| C-04 | импорт `StatusDefinition` | Supervertaler.py:323 | 0 использований имени в монолите (AST) | УДАЛИТЬ-БЕЗОПАСНО |
| C-05 | `STATUSES`, `get_status`, `_STATUS_ALIASES`, `DEFAULT_STATUS` | statuses.py | живые потребители (монолит, grid) | ОСТАВИТЬ-ЖИВОЕ |
| C-06 | `modules/models.py` и соседи | def_scan.txt | осиротевших определений, кроме C-01..C-04, не найдено | — |

Пробная проверка (Этап 2): удаление C-01/C-02/C-04 в worktree → py_compile OK, headless OK
(см. §2-проба). Ручная проверка: старт, статусная колонка грида, импорт/экспорт статусов проекта.

### D. UI-слой TM-бриджа (решение 8.11 §9 — удалить; колонку БД и сеттер оставить)

Зона: `_create_tm_list_tab` (11210–11679). Точный перечень (база d308a93f):

| ID | Элемент | Строки |
|---|---|---|
| D-01 | help-строка «• Bridge (orange ✓) …» | 11245 |
| D-02 | комментарий bulk toggles | 11277–11280 |
| D-03 | `bridge_header_checkbox` («Select All Bridge») | 11281–11283 |
| D-04 | `tm_clear_all_bridge_btn` + tooltip + connect | 11285–11288 |
| D-05 | комментарий «9 columns … Bridge» | 11307–11309 |
| D-06 | `setColumnCount(9)` → 8; headers (убрать «Bridge»); `setColumnWidth(5,60)` удалить; 6→5, 7→6 | 11310–11320 |
| D-07 | `toggle_all_bridge` (def) | 11371–11383 |
| D-08 | `bridge_header_checkbox.toggled.connect` | 11401 |
| D-09 | per-row Bridge-чекбокс + tooltip + `on_bridge_toggle` + connect + `setCellWidget(row,5,…)` | 11514–11546 |
| D-10 | header-sync: blockSignals/setChecked/all_bridge_checked (col 5) + renumber all_superlookup 6→5 | 11595, 11599, 11600, 11603, 11607 |
| D-11 | комментарий «read/write/bridge» | 11293 |

Итого ~69 строк (с комментариями/пустыми; «~40» из решения 8.11 — без них).

**Таблица индексов колонок TM-таблицы** (главное: удаление колонки 5 сдвигает 6,7,8):

| Операция | Строка | Индекс | Зависит от сдвига? |
|---|---|---|---|
| setItem name/langs/entries | 11436, 11443, 11449 | 0,1,2 | нет |
| cellWidget/setCellWidget Read/Write | 11483, 11490, 11505, 11512 | 3,4 | нет |
| cellWidget Bridge (удал.) | 11538, 11545 | 5 | — |
| cellWidget/setCellWidget SuperLookup | 11567, 11574 | 6 → **5** | **да** |
| setItem Last Modified / Description | 11586, 11590 | 7,8 → **6,7** | **да** |
| header-sync all_read/write/bridge/superlookup | 11597–11600 | 3,4,5,6 → 3,4,5 | **да** |
| внешние чтения таблицы (только col 0 — имя TM) | 11688, 19016, 19090, 19120 | 0 | нет |
| числовых `setCurrentIndex`/сортировка по колонкам вне навигации | AST: нет | — | — |

**Рекомендация:** удалить колонку и пересчитать индексы (не скрывать): скрывание оставило бы
мёртвый слой и расхождение заголовков. Пробная проверка (Этап 2, worktree): применено D-01…D-11
с ренумбером → py_compile OK; offscreen-проба: приложение стартует, TM-таблица **8 колонок**,
заголовки `TM Name, Languages, Entries, Read, Write, 🔍 SuperLookup, Last Modified, Description`,
Bridge-колонка отсутствует (`probe_trial.log`).

Ручные тесты TM-вкладки (на сборке Дмитрия): старт; вкладка TMs — список, чекбоксы Read/Write/
SuperLookup работают и синхронизируются с «Select All…»; сортировка по клику заголовка;
переименование/удаление TM; импорт/экспорт TMX; колонки Last Modified/Description на месте.

### E. Undefined names (149 pyflakes-строк, 12 имён)

Раскладка: **Supervertaler.py 17** + **modules/glossary_manager.py 6** + **modules/tmx_editor.py 126**.

| ID | Имя | Число | Где | Достижимая ошибка времени выполнения? | Класс |
|---|---|---|---|---|---|
| E-01 | `dialog`,`tabs`,`layout`,`import_tab` | 15 | Supervertaler.py 48905–49075 — **битая копия `show_about`** (реальная — 49759, привязана 8640) | нет (метод мёртв, переопределён ниже) | УДАЛИТЬ-БЕЗОПАСНО (удаление дубля снимает 15 предупреждений) |
| E-02 | `e` | 1 | Supervertaler.py:49368 — в замыкании `on_err`, отложенном `QTimer.singleShot(0, on_err)`; имя `e` удаляется после `except` | **да — реальный латентный NameError** при пути ошибки | ТРЕБУЕТ РЕШЕНИЯ (исправление = 8.15: сохранить ссылку `err=e` до singleShot) |
| E-03 | `LLMClient` | 1 | Supervertaler.py:50351 — нет модульного импорта, вызов в `try/except` | NameError глотается → **молчаливый пропуск vision-пути** | ТРЕБУЕТ РЕШЕНИЯ (8.15: импорт/делегат) |
| E-04 | `GlossaryInfo`,`TermEntry` | 6 | glossary_manager.py | модуль-сирота (A-04) → импорт никто не выполняет, NameError недостижим | УДАЛИТЬ-БЕЗОПАСНО (вместе с A-04) |
| E-05 | `tk`,`ttk`,`messagebox`,`filedialog` | 126 | tmx_editor.py | модуль **живой** (импортёр tmx_editor_qt ← Tools→TMX Editor); в бандле python-embed tkinter есть, в тестовой сборке — нет → импорт падает там | ОСТАВИТЬ-ЖИВОЕ (зависимость tkinter; в B не входит — stdlib) |

Реальные скрытые баги (список для 8.15): **E-02** (49368), **E-03** (50351). Остальные 147 —
недостижимые/сиротские/stdlib-окружение.

### F. Падения headless-импорта (7)

| ID | Модуль | Причина | Импортёры | Живой путь? | Класс |
|---|---|---|---|---|---|
| F-01 | find_replace | tkinter | 0 | нет (живая find_replace_qt) | УДАЛИТЬ-БЕЗОПАСНО (A-03) |
| F-02 | glossary_manager | NameError GlossaryInfo | 0 | нет | УДАЛИТЬ-БЕЗОПАСНО (A-04) |
| F-03 | pdf_rescue_Qt | fitz | **живой** (монолит, Tools→PDF Rescue 8499–8501/9900–9925) | **да** | ОСТАВИТЬ-ЖИВОЕ; PyMuPDF в requirements остаётся; в бандле разработчика fitz нет → пункт «Непокрытые проверки» U-4 |
| F-04 | pdf_rescue_tkinter | tkinter | 0 | нет | УДАЛИТЬ-БЕЗОПАСНО (A-06) |
| F-05 | prompt_library | tkinter | 0 | нет | УДАЛИТЬ-БЕЗОПАСНО (A-10) |
| F-06 | tracked_changes | tkinter | 0 | нет | УДАЛИТЬ-БЕЗОПАСНО (A-16) |
| F-07 | setup | setuptools | build-only | да (setup.py) | ОСТАВИТЬ |

После удаления 17 сирот headless = **92 ok / 2 fail / 94** (fitz, setuptools) — подтверждено
пробой (Этап 2). Пользователь без PyMuPDF: Tools→PDF Rescue даёт ошибку lazy-импорта
(негативный сценарий — в ручные тесты 8.14).

### G. Настройки

Ключи с **0 читателей/писателей в коде** (скан всех ключей settings-дефолтов + grep всех форм;
`settings_keys.txt`): `features.clipboard_privacy`, `superlookup_landing_tab`,
`autohotkey_path`, `hide_autohotkey_dialog`, `ui.dictation_settings` (+вложенные
`voice_pause_hotkey`, `pushtotalk_mode`, `mic_device`), `ui.voice_vocabulary`,
`ui.voice_dictation_opt_in_reset_applied`, `general.first_run_completed`.
Решение Дмитрия: ключи в файлах пользователя **остаются**; в коде мёртвого перечня нет —
миграции удалены в 8.8, дефолты settings_service.py:172–191 орфанных ключей не содержат
(проверено), UI-страницы удалены в 8.3–8.5, 8.7.

Ключи, **читатели которых — модули-сироты** (становятся 0-читателями после 8.12):
`claude_enabled`, `deepl_enabled`, `enable_mt_matching`, `google_translate_enabled`,
`openai_enabled` (читатель — translation_services, A-17), `context_before`
(читатель — statistics_analyzer, живой — не сирота; проверено: statistics_analyzer импортируется
живым statistics_dialog_qt → ключ жив). Итог: 5 ключей зависят от судьбы A-17.

Живой контроль: `general.translator_name` — читается `get_translator_name` (фолбэк
«Translator», acfe8880) — **ОСТАВИТЬ-ЖИВОЕ**. `MyMemory` (`mt_mymemory`, дефолт True,
Supervertaler.py:20570–20572) — функция живая, решение о дефолте — продуктовое (вопрос Q-13).

### H. main() и мёртвые методы монолита

**(1) main() (56793–56994):** комментарий batch-offload 56795–56797 (решение 8.9 §9.2 — снести),
упоминание QWebEngine 56801–56802 (8.10). Неиспользуемых переменных/импортов AST не нашёл.

**(2) Мёртвые методы (AST, все формы: self-резолв класса, connect/QTimer/singleShot/getattr/
hasattr/setattr/строки; `dead_methods.py`):** **63 метода / 2683 строки** с 0 обращений.
Крупнейшие: `_show_edit_terms_dialog` 18119–18451 (333), `export_for_ai` 31143–31422 (280),
`_REMOVED_add_mt_and_llm_matches_progressive` 53456–53729 (274), `import_tmx_file` 11769–11944
(176), `create_assistance_panel` 26490–26640 (151), `detach_superlookup` 10994–11116 (123),
`_add_mt_and_llm_matches` 53731–53918 (188), `_translate_with_llm` 5595–5658 (64),
`_show_tm_context_menu` 11681–11739 (59). Полный список — `dead_methods.txt`.
Исключены из кандидатов (Qt virtual overrides, вызываются из C++):
`WordWrapDelegate.setEditorData/setModelData/updateEditorGeometry`.

Сверка с `DEAD_CODE_REPORT.md` (снимок 2026-09-12): голосовая/clipboard-группы из него удалены
батчами 8.2–8.5; **новые** после Batch #8 (появились как побочные эффекты удалений):
`detach_superlookup`, `_open_superdocs_tab`, `create_superdocs_tab`, `on_main_tab_changed`,
`show_options_dialog`, `_show_tm_context_menu`, `_translate_with_llm`, `_add_mt_and_llm_matches*`.
Класс: УДАЛИТЬ-ПО-РЕШЕНИЮ (каждый доказан по всем формам; массовое удаление — отдельным
батчем с ручными тестами, не механической зачисткой).

### I. Док-остатки в коде

Полная выборка с классификацией — `docs/refactoring/audits/batch8-12_section_I_trados_sample.txt`
(50 строк выборки + категории). Ключевые пункты:

| ID | Файл:строки | Что говорит | Устарело? | Предложение |
|---|---|---|---|---|
| I-01 | Supervertaler.py:56795–56797 | batch-offload-режим (CLI удалён 8.9) | да | править (решение 8.9 §9.2) |
| I-02 | Supervertaler.py:56801–56802 | «…инициализации QWebEngine» | да | править |
| I-03 | Supervertaler.py:20, 23 | фичи-лист: «DOCX memoQ», «Ctrl+Alt+L» | да (8.9/8.10) | править 2 строки |
| I-04 | Ctrl+Alt+L в докстрингах: 9165, 9257, 21082, 27059; quicktrans.py:670–677, 1130–1136 («Same plumbing as Ctrl+Alt+L») | хоткей удалён 8.10 | да | править (решение 8.10 §8.2) |
| I-05 | Supervertaler.py:23559–23560 | «легаси-маршрут Sidekick.show_superlookup … продолжает работать» | да (Sidekick удалён v1.10.4) | править |
| I-06 | platform_helpers.py:2163 | «…as VoiceCommandManager._run_ahk_code» (класс удалён 8.3) | да | править |
| I-07 | settings_service.py:38–39 | legacy-миграции (удалены 8.8) | да | править (решение 8.8 §9.3) |
| I-08 | styled_widgets.py:116–122, 170 | тултип/комментарий «🎤 Voice column» (колонка удалена 8.4) | да | править |
| I-09 | termbase_manager.py:461–551 | методы voice-bias + комментарии про Voice tab | UI удалён 8.4; методы 0 потребителей (grep) | **ТРЕБУЕТ РЕШЕНИЯ**: методы+колонка БД оставлены решением 8.4 — править только комментарии или удалить методы (вопрос Q-10) |
| I-10 | help_system.py:160–176 | `HelpTopics.SIDEKICK/VOICE/CLIPBOARD/TRADOS_AWARE_CHAT` — 0 обращений (grep `HelpTopics.<CONST>` по репо) | да | УДАЛИТЬ-БЕЗОПАСНО (4 константы + комментарий-блок) |
| I-11 | clipboard-комментарии монолита: 9153, 9171, 9210, 23389, 23451, 24658 | Clipboard-вкладка (удалена 8.5) | частично | править построчно (выборка I-09…I-14 sample) |
| I-12 | modules/DATABASE_README.md | grep `clipboard_history`/`voice_dictation_enabled`/`bridged_to_trados` = **0** | нет устаревших пунктов | ОСТАВИТЬ |

**≈250 комментариев «Trados/memoQ» — правило** (предложение): править только те, что описывают
удалённую функцию как присутствующую; оставить конвенции тегов (tag_manager, autocorrect,
bilingual_markdown_handler, pseudo_translate, grid/filters — подсветка тегов живая), паритет с
внешним плагином (termlens*, TermPicker, цены, prompt-флаги), исторические заметки v1.10.x и
ссылки на внешние продукты. Числа по категориям (выборка 50 строк, экстраполяция): править
~35–45; оставить-паритет ~60–70; оставить-теги ~90–110; исторические ~25–30; внешний контекст
~40–50. Итого правок ~40 строк из ~250.

### J. Документы репозитория

| Документ | Устарело | Предложение | Объём |
|---|---|---|---|
| CODE_MAP_REFACTOR.md (1639 стр.) | номерные диапазоны методов удалённых групп (voice 28048–28570, clipboard, bridge, autohotkey, settings-страницы) | шапка «снимок 2026-09-12, строки не актуальны; актуальные границы — AST» + указатель на отчёты 8.x; полная пересводка не нужна | ~10 строк |
| DEPENDENCY_MAP.md (246) | §2 перечисляет удалённые модули (voice_*, clipboard_manager_widget, superbrowser, CAT-хендлеры, bridge_server) | шапка-заметка «снимок; удалённые в Batch #8 модули вычеркнуты» + список | ~10 строк |
| DEAD_CODE_REPORT.md (403) | снимок 2026-09-12; голосовая/clipboard-группы удалены 8.2–8.5 | заметка «удалено в 8.x» + ссылка на dead_methods.txt 8.12 | ~8 строк |
| EXTRACTION_PLAN.md (714) | исторические номера Step 7 | не править (история); добавить финальную строку статуса | ~3 строки |
| VALIDATION_BACKLOG.md (221) | п. 26 AHK CLOSED (U1.2) | архивировать п. 26 в раздел CLOSED | ~5 строк |
| BATCH8_STAGE1_AUDIT_REPORT.md | план → итоги | раздел «Итоги: что ушло в 8.1–8.11, что перешло в инвентарь 8.12» | ~20 строк |
| PROJECT_STATUS.md | строка «upstream base partially updated to v1.10.372» — **корректна** (U1.1–U1.4b перенесены, класс D/CHANGELOG — нет) | добавить строку 8.12 + next step | ~5 строк |
| UPSTREAM_SYNC_MANIFEST.md | заметки актуальны (segment_split_merge=763291e8 без 34a4c661; hunk №2 `add_source_text_to_project` вне объёма; CHANGELOG не портирован; U1.5/U1.6/autosave/Inline Codes отложены) | добавить: «Batch #8 удалил CAT/Voice/Clipboard/Web-функции — объём будущего синхрон-а с апстримом сократился» | ~5 строк |
| README.md (38) | актуален | без правок | 0 |
| AGENTS.md (234) | актуален (политика тестовой сборки) | без правок | 0 |
| POST_BATCH8_BACKLOG.md | §7 закрывается этим отчётом; §10 → 8.16/8.17 | ссылка на отчёт (без дублей) | ~3 строки |

### K. Итоги Batch #8 (справочно, по git log + отчётам)

| Под-батч | Код-коммит | Монолит до→после | Удалённые модули |
|---|---|---|---|
| 8.1 Superbrowser | 20b5675b | 68265 → 68216 | superbrowser.py |
| 8.2 Always-On voice | 7d9cf7dc | 68216 → 67641 | — |
| 8.3 Voice tab | 91f7f8ac | 67641 → 67157 | voice_command_dialog, voice_commands, voice_dictation, voice_tab, vosk_model_manager |
| 8.4 Dictation/🎤 | bf821d0f | 67157 → 65961 | dictation_toast, mic_devices, voice_dictation_lite, voice_hotkey_listener, voice_release_poller, voice_vocabulary |
| 8.5 Clipboard | 4988a0fb | 65961 → 65163 | clipboard_manager_widget, snippet_library, text_conversion_library |
| 8.7 Identity+bridge | dc2e2838 | 65163 → 64979 | supervertaler_bridge_server |
| 8.10 SuperLookup trim | 6897539d | 64979 → 62387 | — |
| 8.8 First-run/migrations | ede28068 | 62387 → 61743 | setup_wizard |
| 8.9 CAT formats | 5a29d3c9 | 61743 → 57010 | batch_offload, cafetran_docx_handler, dejavurtf_handler, memoqrtf_handler, mqxliff_handler, phrase_docx_handler, sdlppx_handler, sdltm_handler, trados_docx_handler |
| 8.11 Trados chip | d308a93f | 57010 → 57010 (монолит не тронут) | trados_bridge_client (524) |

Суммарно: монолит **68265 → 57010** (−11255); модули **137 → 110** (−27); вкладки main_tabs
**8 → 6** (Editor, TMs, Termbases, AI, SuperLookup, Settings); страницы Settings **17 → 14**;
глобальные хоткеи при старте **ctrl+alt+l, ctrl+alt+q, ctrl+alt+c, ctrl+shift+space, ctrl+alt+v
→ только ctrl+alt+q**. Расхождений с отчётами не обнаружено (8.10: −2597 по wc против оценки
A2 −2250 — отмечено в отчёте 8.10).

---

## 3. Трассировка решений Дмитрия (Этап 2 п.3)

| Пункт решения (источник) | Раздел отчёта |
|---|---|
| Орфанные ключи voice/clipboard/AHK/first_run (8.3 §7, 8.4 §7, 8.5 §7, BACKLOG §7) | G |
| glossary_manager NameError (8.3 §7.7, BACKLOG §7) | A-04, E-04 |
| Пересчёт 149 undefined names (BACKLOG §7) | E |
| feature_manager + pyproject web=[] (8.10 §8.1) | A-02, B |
| HelpTopics.VOICE/SIDEKICK/CLIPBOARD (8.3 §8, BACKLOG §7) | I-10 |
| platform_helpers докстринг VoiceCommandManager (BACKLOG §7) | I-06 |
| styled_widgets/termbase_manager 🎤 (BACKLOG §7) | I-08, I-09 |
| settings_service.py:38–39 (8.8 §9.3) | I-07 |
| main() 56795–56797 (8.9 §9.2) | I-01 |
| statuses.py memoQ-функции (8.9 §9.1) | C-01, C-02 |
| lxml (8.9 §9.4) | B |
| setup.py оставить (8.9 §9.3) | B (примечание) |
| `_prewarm_ahk` оставить (A2, BACKLOG §7) | H (живой, 10916→10920 — не кандидат) |
| MyMemory дефолт (BACKLOG §7) | G, Q-13 |
| UI TM-бриджа удалить / колонку+сеттер оставить (8.11 §9.1) | D |
| app_target «Trados only», superlookup `'trados'` — оставить до инвентаря (8.11 §9.2–3) | Q-11, Q-12 (решение: оставить — метаданные живые) |
| Trados-док-остатки ~250 (8.11 §9.4) | I (правило + выборка) |
| general.translator_name живой (8.7 §9) | G |
| sidekick-bridge.json/.log, clipboard_history, snippet_library/, кастомный хоткей sidekick_open_clipboard (8.5 §9.2, 8.7 §9) | вне кода → Q-14 (чистка данных) |
| Ctrl+Alt+L/WebEngine док-остатки (8.10 §8.2) | I-02, I-04 |
| pip uninstall ahk при пересборке (8.10 §8.3) | B, Q-15 |
| Док-проход документов репо (BACKLOG §10) | J |

Пропущенных пунктов нет.

---

## 4. Предложение разбивки на батчи реализации

| Батч | Состав | Оценка | Риск | Ручные тесты |
|---|---|---|---|---|
| **8.12** механические код-сироты | A (17 модулей, 6734) + C-01..C-04 (~60) + I-10 HelpTopics (4 константы) + I-01/I-02/I-07/I-06/I-08 (мелкие док-правки, ~20) | ~6800 строк | низкий (проба зелёная: py_compile, headless 92/2, pyflakes 143=149−6, offscreen-старт) | старт; Tools (TMX Editor, PDF Rescue, Statistics, Pseudo); AI-ассистент/chat; импорт файлов; статусы грида |
| **8.13** UI TM-бриджа | D-01…D-11 (69 строк, ренумбер колонок) | 69 | средний (индексы колонок) — проба зелёная | TM-вкладка: чекбоксы Read/Write/SuperLookup + Select All, сортировка, импорт/экспорт TMX |
| **8.14** зависимости | B: удалить из requirements/pyproject lxml, sacrebleu, chardet, pyyaml, markdown, numpy, sounddevice, vosk, ahk, faster-whisper, PyQt6-WebEngine | 2 файла | средний: только после согласования с P2; lxml транзитивен | чистая установка в embed; старт; DOCX/PDF/TMX/орфография/MT |
| **8.15** скрытые баги | E-02 (`e` 49368), E-03 (LLMClient 50351), удаление битого `show_about` (E-01) | ~190 | низкий | vision-запрос; путь ошибки LLM; About-диалог |
| **8.16** docs-проход в коде | правило I + выборка: ~40 строк Trados + Ctrl+Alt+L/clipboard-комментарии | ~60 | низкий (комментарии) | не нужны (docs-only коммит) |
| **8.17** docs-проход репо | J (заметки/архив п.26/итоги Stage1) | ~60–120 | низкий | не нужны |

Порядок: 8.12 → 8.13 → 8.15 → 8.16 → 8.17; 8.14 — после решения по P2.

---

## 5. Непокрытые проверки (честно)

- **U-1.** Полный offscreen S-clean/S-upgrade прогон (полные сценарии user-data) для 17-модульного
  удаления не выполнялся — только py_compile + headless + pyflakes-дифф + offscreen-старт с
  TM-таблицей (worktree, изолированный профиль). Полные сценарии — в ручные тесты 8.12.
- **U-2.** Методы voice-bias `termbase_manager` (I-09): 0 потребителей доказано grep/AST;
  рантайм-достижимость через duck-typed `parent_app` не прощупывалась.
- **U-3.** Поля `trados_source_path`/`memoq_source_path`/… в `modules/models.py` (498–510):
  совместимость со старыми `.svproj` (поля в JSON) не тестировалась — образцов старых проектов
  в изолированном профиле нет.
- **U-4.** Поведение Tools→PDF Rescue без PyMuPDF (F-03) в бандле разработчика не прощупано
  (fitz там нет); в тестовой сборке не проверялось.
- **U-5.** Классификация ~250 Trados-комментариев — экстраполяция с выборки 50 строк; полная
  построчная классификация — работа батча 8.16.
- **U-6.** MyMemory-дефолт (G) — продуктовое решение, кодовой проверкой не покрыто.

---

## 6. Вопросы к Дмитрию (построчно: да / нет / свой вариант)

**ТРЕБУЕТ РЕШЕНИЯ / УДАЛИТЬ-ПО-РЕШЕНИЮ:**

1. **A-01…A-17** — 17 модулей-сирот (6734 строк, 0 импортёров, проба зелёная) — удалить в 8.12? (да/нет)
2. **C-01/C-02** `match_memoq_status`/`compose_memoq_status` + **C-03** поля memoq_label/memoQ_equivalents — удалить функции (решение 8.9 подтверждено); поля удалять тоже или оставить как словарь соответствий? (удалять всё / только функции)
3. **D** UI TM-бриджа (69 строк, колонка+чекбоксы+bulk) с ренумбером колонок 6→5,7→6,8→7 — подтверждаете удаление в 8.13? (колонка БД и `set_bridged_to_trados` остаются)
4. **E-02** `e`@49368 (латентный NameError) — чинить в 8.15? (да/нет)
5. **E-03** `LLMClient`@50351 (молчаливый пропуск vision) — чинить в 8.15? (да/нет)
6. **E-01** удалить битую копию `show_about` 48905–49075 (снимает 15 pyflakes-хитов)? (да/нет)
7. **H** 63 мёртвых метода (2683 строк, `dead_methods.txt`) — удалять списком по решению, выборочно, или оставить? (весь список / выборочно / оставить)
8. **A-02 feature_manager + pyproject web=[]** — подтверждаете удаление (решение 8.10 отложено сюда)? (да/нет)
9. **B** удалить из requirements/pyproject: lxml, sacrebleu, chardet, pyyaml, markdown, numpy, sounddevice, vosk, ahk, faster-whisper, PyQt6-WebEngine (lxml останется транзитивно) — да/нет по списку; 8.14 после P2?
10. **I-09** методы voice-bias `termbase_manager` (get/set_termbase_voice_enabled, get_voice_enabled_termbase_ids, 0 потребителей): удалить методы (колонку БД оставить) или оставить методы, правив только комментарии? (удалить / оставить)
11. **app_target «Trados only»** (unified_prompt_library/combo) — решение 8.11 «оставить до инвентаря»: оставляем окончательно? (да/нет)
12. **superlookup-режим `'trados'`** (tag-extraction) — оставляем окончательно? (да/нет)
13. **MyMemory дефолт True** (внешний сервис, 500 символов) — оставить по умолчанию? (да/нет)
14. **Чистка данных** (вне кода): таблица `clipboard_history`, `<user_data>/snippet_library/`,
    `text_conversion_library/`, `sidekick-bridge.json/.log`, ключи-сироты в settings.json,
    кастомный хоткей `sidekick_open_clipboard` в shortcuts — оставить как есть / скрипт-чистка?
15. **`pip uninstall ahk`** в тестовой сборке — при ближайшей пересборке (решение 8.10)? (да/нет)
16. **Правило Trados-комментариев** (раздел I: править ~40 из ~250, остальные оставить) — принимаете? (да/нет/корректировка)

**Разбивка (после ответов 1–16):**

17. Порядок 8.12 → 8.13 → 8.15 → 8.16 → 8.17, 8.14 после P2 — принимаете? (да/нет/свой порядок)
18. Ручные тесты на сборке Дмитрия: 8.12 (старт+Tools+AI+статусы), 8.13 (TM-вкладка),
    8.14 (чистая установка), 8.15 (vision/About) — подтверждаете объём? (да/нет)

---

## 7. Решения Дмитрия по вопросам §6 (2026-10-10)

| № | Решение |
|---|---|
| 1 | **Да** — удалить 17 модулей-сирот (A-01…A-17) в батче 8.12. |
| 2 | Удалить **только** `match_memoq_status`/`compose_memoq_status` (C-01/C-02) и импорт `StatusDefinition` (C-04). Поля `memoq_label`/`memoQ_equivalents` (C-03) **оставить**: безобидные данные, правка живого словаря статусов — лишний риск. |
| 3 | **Да** — UI TM-бриджа с ренумбером колонок в 8.13 (колонка БД + сеттер остаются). |
| 4 | **Да** — чинить E-02 (`e`@49368) в 8.15. |
| 5 | E-03 (`LLMClient`@50351) — **чинить в 8.15, вариант (а): локальный импорт `from modules.llm_clients import LLMClient` по образцу строки 10048** (описание функции — §7.5; решение Дмитрия 2026-10-10 после уточнения области действия — §7.6). |
| 6 | **Да** — удалить битый дубль `show_about` 48905–49075 (E-01) в 8.15. |
| 7 | **Да, все 63 мёртвых метода** (≈2683 строк) — **отдельным батчем 8.18**, группами по 10–15 с полным протоколом. |
| 8 | **Да** — `feature_manager.py` (A-02) и `web = []` в pyproject. |
| 9 | **Да по списку**, внутри P2 (чистая установка в embed — единственный честный тест). Дополнительно убрать **pyobjc-framework-Cocoa** (macOS не поддерживаем). Батч 8.14 **растворяется в P2**. |
| 10 | **Удалить** voice-bias методы `termbase_manager` (I-09); колонку БД оставить. |
| 11, 12 | **Оставить окончательно** `app_target` «Trados only» и режим SuperLookup `'trados'`; вернуться на проходе по оставшимся функциям. |
| 13 | **MyMemory — выключить по умолчанию для новых установок** (лимит 500 символов + отправка текста стороннему сервису без ключа). Мелкая правка дефолта в 8.15; у существующих пользователей значение не меняется. |
| 14 | Данные **оставить как есть**, без скрипта чистки. В целевой раскладке P1 папки `snippet_library/`, `text_conversion_library/` больше не нужны (модули удалены в 8.5). |
| 15 | **Да** — `pip uninstall ahk` при пересборке тестовой сборки. |
| 16 | **Да** — правило для Trados-комментариев (править ~40 из ~250). |
| 17 | Порядок: **8.12 → 8.13 → 8.15 → 8.18 (мёртвые методы) → 8.16 → 8.17**; docs-проход в коде — после всех удалений. |
| 18 | **Да** — объём ручных тестов принят. |

### 7.5. Описание функции для решения по E-03 (п. 5)

Функция: **`translate_current_segment(self, fuzzy_match=None)`** (Supervertaler.py:49997) —
основной путь перевода текущего сегмента. Блок 50339–50368: проверка рисунков. Если
`figure_context` содержит изображения и в исходном тексте сегмента обнаружены ссылки на рисунки
(`detect_figure_references`), строка 50351 вызывает
`LLMClient.model_supports_vision(provider, model)`, чтобы решить, прикладывать ли изображения
(PIL для gemini, base64 PNG для openai/claude, строки 50353–50361).

`LLMClient` не импортирован на уровне модуля; во всех остальных местах монолита перед вызовом
делается локальный импорт (`from modules.llm_clients import LLMClient` — строки 5598, 10048,
48719, 50872, 52142; в 10048–10049 — ровно та же проверка vision, с импортом). Здесь импорт
пропущен → NameError → перехват `except Exception` на 50367 → в лог пишется
«⚠️ Could not load figures: name 'LLMClient' is not defined» → `images = None` → перевод
продолжается **без изображений**.

Последствия: vision-путь в этой функции молча не работает никогда (рисунки не прикладываются
ни при каком провайдере), сообщение в логе вводит в заблуждение (дело не в загрузке рисунков).
Функция живая (горячая клавиша перевода сегмента).

Варианты починки (оба — 1 строка): (а) локальный импорт по образцу 10048 в начале `try`;
(б) вызов через уже созданный `client` (50127, `create_llm_client` возвращает экземпляр
`LLMClient`; `model_supports_vision` — classmethod, доступен от экземпляра).

### 7.6. Уточнение области действия E-03 (вопросы Дмитрия 2026-10-10)

**Вид ссылки на рисунок** (`figure_context_manager.py:62`,
`pattern = r"(?:figure|figuur|fig\.?)\s+(\d+[a-zA-Z]?)"`, проверено на регулярке):
слово `figure`/`figuur`/`fig` (регистр не важен, точка факультативна) + **пробел** + номер с
факультативной буквой: «Figure 1A»→`1a`, «fig. 4»→`4`, «Figuur 5»→`5`, «Figure 1, Figure 2»→
`1,2`. НЕ матчится: множественное «Figures 2 and 3B» (докстринг обещает `2,3b` — расхождение
документа и кода), «Fig.10C» без пробела, русские «рис./рисунок». Второе условие:
нормализованная ссылка должна совпасть с файлом из папки рисунков («Figure 1.png»→`1`,
«fig3b.png»→`3b`; загрузка — меню 10467 / авто из `image_folder` проекта 27442–27445).

**Область действия — только одиночный сегмент.** `translate_current_segment` вызывается из
меню Translate (действие 8171) и из `fuzzy_fix_current_segment` (50456→50525). Пакетный перевод
(пункты меню 8196–8225) идёт через `PreTranslationWorker` (QThread, 5287), в котором обращений
к `figure_context`/`images` нет вообще (grep по классу = 0; `client.translate` на 5648/5778/5915
параметр `images` не передаёт) — в пакетном режиме vision-пути не существует, рисунки никогда не
прикладывались, ломаться нечему. Vision с рабочим импортом существует только в Image Extractor
(`_build_image_extract_ai_callback`, 10009, проверка на 10048) и в превью промпта в гриде
(`_preview_combined_prompt_from_grid`, 39208).

**Решение Дмитрия: чинить в 8.15, вариант (а)** — локальный импорт по образцу 10048.

---

## 8. Итоговый порядок реализации (после решений §7)

1. **8.12** — код-сироты: A-01…A-17 (17 модулей, 6734) + C-01/C-02/C-04 (без полей) +
   A-02 feature_manager + `web = []` + I-10 HelpTopics (4 константы) + мелкие док-правки
   I-01/I-02/I-06/I-07/I-08.
2. **8.13** — UI TM-бриджа (D-01…D-11, ренумбер колонок).
3. **8.15** — скрытые баги: E-02 (чинить), E-01 (удалить дубль `show_about`), E-03 (чинить —
   локальный импорт `LLMClient` по образцу 10048, §7.6), MyMemory-дефолт False для новых
   установок (правка дефолта, существующие значения не трогаем).
4. **8.18** — 63 мёртвых метода (2683 строк), группами по 10–15, полный протокол.
5. **8.16** — docs-проход в коде (правило I + Ctrl+Alt+L/clipboard-комментарии) — после всех удалений.
6. **8.17** — docs-проход документов репо (J).
7. **P2** — зависимости (список 9 + pyobjc-framework-Cocoa; lxml транзитивен; `pip uninstall ahk`
   при пересборке) — батч 8.14 растворяется в P2.

---

*Артефакты прогона (в репозитории): `docs/refactoring/audits/batch8-12_*` —
headless_before.txt, undefined_names_before/trial.txt, importers.json, reach_v3.txt,
reach.py, importer_scan.py, dep_scan.py/dep_scan_v2.txt, def_scan.txt, settings_keys.txt,
dead_methods.txt, section_I_trados_sample.txt, probe_trial.log, probe_trial_tm.py.
Рабочая копия прогона: `D:\Temp\SupervertalerPortable\refactoring\batch8-12\`.*
