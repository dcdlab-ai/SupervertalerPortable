# ОТЧЁТ Batch #8.9 — CAT-форматы (слой II) и Trados-специфика

Исполнитель: Zcode. Дата: 2026-10-09.
Основание: `E:\Dev\п89.txt`; BATCH8_STAGE1_AUDIT_REPORT.md §2.3 (F3 слой II), §4 (строка 8.9), §4.1 (защиты), §7 (решения 1, 2, 8, 11); база кода — `ede28068` (постановка), фактическая база — `0c8b0d87` (HEAD на старте).
Порядок Batch #8: 8.1–8.5 ✓, 8.7 ✓, 8.10 ✓, 8.8 ✓ → **8.9 (этот отчёт)** → микро-батч «Trados-чип» → финальный инвентарь сирот + docs-проход.

---

## 0. Baseline и git-синхронизация

- HEAD = origin/main = `0c8b0d87` (docs Batch #8.8 §9). Рабочая копия чистая (кроме `.zcode/plans/…`, `.zcodeignore`).
- `Supervertaler.py`: **61 743** строки, SHA256 рабочей копии (CRLF) `db37188c79c7434597abce9f0ddb11c36858838c85f047c94126ecb702cacd0d`; git-блоб (LF) `3419012b3763a2e1b0031e512b822efa18bc206ccb58ebc70d4f538987bcb27d`.
- py_compile baseline: 138/138 файлов (120 модулей + монолит + прочее).
- Строки 9 удаляемых модулей (git HEAD, `wc -l`): memoqrtf_handler 688, mqxliff_handler 717, cafetran_docx_handler 379, trados_docx_handler 433, sdlppx_handler 2270, phrase_docx_handler 669, dejavurtf_handler 784, batch_offload 372, sdltm_handler 237 → **6 549**.
- Baseline-артефакты защит (`D:\Temp\SupervertalerPortable\refactoring\b8-9\`): `startup_chain_before.json` (1179 вызовов, 2 неразрешённых), `undefined_names_before.txt` (149 строк / 12 уникальных имён), `headless_before.txt` (114 ok / 6 fail / 120), `cli_before.txt`, `probe_before_clean.log` (90 MENU-строк), `probe_before_upgrade.log` (hash-diff пустой).

## 1. Рекон

### 1.1 Состав и сверка «6 хендлеров ≈5666» vs таблица аудита

Аудит §2.3 перечисляет **7 модулей слоя II** (без batch_offload/sdltm): 688+717+379+433+2270+669+784 = **5 940** — совпадает с фактическими построчными count'ами (см. §0). Формулировка «6 хендлеров ≈5666» арифметически не воспроизводится ни из какого 6-модульного подмножества (ближайшее — 5 561 без cafetran_docx_handler). Вывод: «≈5666» — округлённая/устаревшая оценка объёма слоя II в целом; фактический объём удалённых модулей — **9 модулей, 6 549 строк** (слой II 5 940 + batch_offload 372 + sdltm_handler 237, включённые решением 11).

### 1.2 Методы монолита и их вызыватели (AST, `callers.py`)

Все целевые методы имеют единственный внешний вызыватель — `create_menus` (QAction.triggered.connect), удаляемый вместе с ними. Исключения:
- `_attach_sdltm_as_tm` ← `_create_tm_list_tab` (кнопка `attach_sdltm_btn`, удалена зоной);
- `_sync_external_tms`/`_delta_sync_external_tm` ← таймер `__init__` (удалён зоной);
- `_interpret_memoq_status`, `_apply_formatting_to_cell`, `_is_known_language`, `_lang_from_column_header`, `_confirm_language_pair` — вызываются только из удаляемых методов.

Остающиеся помощники (не вырезаны): `_normalize_language_code` (15 внешних вызывателей: import_po_file, search_termbases, load_terms_for_termbase, _lang_base_name), `get_translator_name` (TMX Editor, DOCX-комментарии — решение 8).

### 1.3 Диспетчеры

- `_quick_extract_sources`: ветки `.sdlxliff`/`.mqxliff` вырезаны; общий путь (docx через Okapi) + `raise ValueError` фолбэк остались.
- `load_project`: CAT-restore блоки (memoq/sdlppx/sdlxliff/cafetran/trados поля) вырезаны; guarded-чтения, NameError не возникает.
- `import_folder_multifile`: memoQ-чекбокс + мёртвый параметр `detect_memoq` убраны (параметр нигде не читался); вызов и сигнатура `_import_multifile_project` согласованы (REPL).
- `export_document`/`export_folder_multifile`/File Types/Open Recent/TM-фильтры — CAT-веток не содержат, не тронуты.
- Drag-and-drop: у главного окна **нет** `dropEvent`/`dragEnterEvent`/`setAcceptDrops` (grep по репо: единственный dropEvent — `modules/unified_prompt_manager_qt.py:355`, остающийся) — CAT-DnD в коде не было, T8.9.5 — только ручная проверка.

### 1.4 Меню и main()

Import-подменю memoQ/CafeTran/Trados Studio/Phrase (Memsource)/Déjà Vu X3 (51 строк), Export-подменю (41) + export-подменю Déjà Vu (5) вырезаны; `import_menu.addSeparator()` перед ними и `tools_menu`-разделители сохранены (двойных разделителей нет — AST-чек, §4.3). CLI-ветка `--batch`/`--translate-sdlxliff` в `main()` вырезана (3 строки).

### 1.5 sdltm / Okapi / пакеты / тесты / ключи

- sdltm: `_attach_sdltm_as_tm` + `_sync_external_tms` + `_delta_sync_external_tm` + таймер + кнопка вкладки TMs — удалены (решение 11).
- Okapi: sidecar, `_try_okapi_merge_export`, общий импорт/экспорт — не тронуты (решение 2). В probe/headless/CLI-прогонах сайдкар стартует и работает.
- Пакеты: **lxml** после удаления — 0 потребителей во всём репо (grep по *.py, исключая `__pycache__`) — кандидат на удаление из `requirements.txt:18` / `pyproject.toml:66` в финальном инвентаре сирот (в 8.9 не менять, по постановке). **python-docx** остаётся (4 потребителя: Supervertaler.py, docx_handler.py, pdf_rescue_Qt.py, pdf_rescue_tkinter.py).
- Тесты: каталога `tests/` нет; `tools/` на удаляемые модули не ссылается (единственная внешняя ссылка — `tools/shortcut_overlap.py` на внешний плагин-репо, не связана).
- Ключи настроек: CAT-ключей в settings-методах не найдено (recon); орфанные ключи по решению 6 не вычищаются.

## 2. Что сделано

`implement_89.py`: SHA-guard (db37188c…) → 35 зон (снапшоты + sha256 в `b8-9\snapshots\`) → удаление зон по убыванию строк → 4 string-замены (assert count==1) → запись (assert `\r\r\n`==0).

| № | Зона (строки HEAD) | Строк | Действие |
|---|---|---|---|
| 1 | main_cli_batch 61528–61530 | 3 | CLI-ветка `--batch`/`--translate-sdlxliff` |
| 2 | export_cafetran_bilingual 38299–38429 | 131 | метод |
| 3 | sdlxliff_map_import_export 36123–37554 | 1432 | `_map_sdlxliff_segment`, import/export standalone sdlxliff, sdlxliff folder, phrase import/export, dejavu import/export (непрерывный блок с секционным заголовком) |
| 4 | export_sdlrpx_package 35968–36122 | 155 | метод |
| 5 | sdlxliff_dicts_confirm_comments 35861–35967 | 107 | sdlxliff-словари статусов + confirm-комментарии |
| 6 | import_sdlppx_package 35548–35847 | 300 | метод |
| 7 | export_trados_bilingual 35404–35547 | 144 | метод |
| 8 | import_trados_bilingual 35135–35403 | 269 | метод |
| 9 | import_cafetran_bilingual 34981–35134 | 154 | метод + секционный заголовок CAFETRAN |
| 10 | export_memoq_rtf_xliff 34527–34752 | 226 | export_memoq_rtf + export_memoq_xliff |
| 11 | lang_helpers 34431–34526 | 96 | `_is_known_language`, `_lang_from_column_header`, `_confirm_language_pair` |
| 12 | import_memoq_xliff 34250–34421 | 172 | метод + заголовок MEMOQ XLIFF |
| 13 | apply_formatting_to_cell 34086–34249 | 164 | `_apply_formatting_to_cell` |
| 14 | export_memoq_bilingual 33871–34085 | 215 | метод |
| 15 | import_memoq_rtf 33600–33870 | 271 | метод |
| 16 | import_memoq_bilingual 33235–33599 | 365 | метод |
| 17 | interpret_memoq_status 33228–33234 | 7 | `_interpret_memoq_status` |
| 18 | multifile_docstring 32187 | 1 | docstring `_import_multifile_project` (REPL-зона) |
| 19 | multifile_detect_memoq 32163 | 1 | строка `detect_memoq = memoq_checkbox.isChecked()` |
| 20 | multifile_memoq_checkbox 32104–32108 | 5 | чекбокс memoQ в импорте папки |
| 21 | taghl_reset_2 31336 | 1 | сброс `_is_cafetran_project` |
| 22 | taghl_reset_1 31007 | 1 | сброс `_is_cafetran_project` |
| 23 | load_project_cat_restore 27962–28006 | 45 | CAT-restore блоки в load_project |
| 24 | sdltm_attach_sync_delta 19147–19475 | 329 | `_attach_sdltm_as_tm` + `_sync_external_tms` + `_delta_sync_external_tm` |
| 25 | tm_tab_attach_sdltm_btn 11773–11780 | 8 | кнопка «Attach Trados TM (.sdltm)» |
| 26 | quickcount_cat_formats 9605–9606 | 2 | CAT-форматы в quick count |
| 27 | quickextract_cat_branches 9584–9595 | 12 | ветки .sdlxliff/.mqxliff |
| 28 | menu_export_dejavu 8141–8145 | 5 | export-подменю Déjà Vu |
| 29 | menu_export_cat_submenus 8093–8133 | 41 | export-подменю memoQ/CafeTran/Trados/Phrase |
| 30 | menu_import_cat_submenus 7981–8031 | 51 | import-подменю memoQ/CafeTran/Trados/Phrase/Déjà Vu |
| 31 | init_external_tm_timer 6301–6310 | 10 | QTimer синхронизации внешних TM |
| 32 | init_memoq_source_file 6034–6035 | 2 | `self.memoq_source_file = None` |
| 33 | taghl_pipe_block 3044–3048 | 5 | CafeTran pipe-подсветка (условный блок) |
| 34 | taghl_cafetran_attr 2886 | 1 | `_is_cafetran_project = False` |
| 35 | statuses_memoq_imports 325–326 | 2 | `match_memoq_status,` / `compose_memoq_status,` из imports |

REPL (4, каждая assert count==1): tooltip Quick Count (форматы), docstring `_quick_extract_sources`, вызов `_import_multifile_project` (убран аргумент `detect_memoq`), сигнатура `_import_multifile_project` (убран параметр).

`git rm` 9 модулей (пути в §0).

**Итог:** монолит 61 743 → **57 010** (−4 733; зоны 4 733, REPL 4 строки замена-на-замену). Модули −6 549. SHA256 нового `Supervertaler.py` (CRLF): `aab1f180e5789878c014d6042a0ee1a29c9e7bdf1d85dbb02e0722f3604f7644`. EOL: 57 010 CRLF, 0 bare-LF, **`\r\r\n` = 0**. `git diff --stat`: 10 файлов (Supervertaler.py + 9 удалённых модулей), 159 insertions — артефакт выравнивания диффа (перемежающиеся keeper'ы); multiset-сравнение строк с HEAD: реально добавлено **ровно 4 строки** (REPL).

## 3. Диффы ключевых мест до/после

- **create_menus (import):** вырезан блок из 5 подменю (memoQ 3 пункта, CafeTran 1, Trados Studio 4, Phrase 1, Déjà Vu X3 1) между `import_menu.addSeparator()` и GNU gettext .po; export — аналогично (memoQ 3, CafeTran 1, Trados 4, Phrase 1 + отдельное Déjà Vu-подменю 1). Разделители: 34 `addSeparator`, 89 `addAction` — двойных нет.
- **main():** удалены `if "--batch" in sys.argv or "--translate-sdlxliff" in sys.argv: from modules.batch_offload import cli_main; raise SystemExit(cli_main(sys.argv[1:]))`. Остался 3-строчный комментарий над удалённой веткой («Автономный batch-offload-режим…») — doc-остаток, строки 56795–56797 (в финальный docs-проход).
- **_quick_extract_sources:** удалены ветки `.sdlxliff` (StandaloneSDLXLIFFHandler) и `.mqxliff` (MQXLIFFHandler); `raise ValueError(f"Unsupported file type: …")` остался.
- **_import_multifile_project:** сигнатура `(…, target_lang: str, detect_memoq: bool, sentence_segment=False)` → `(…, target_lang: str, sentence_segment=False)`; вызов согласован.
- **Перечень удалённых методов (строки HEAD):** `_interpret_memoq_status` 33228–33234; `import_memoq_bilingual` 33235–33599; `import_memoq_rtf` 33600–33870; `export_memoq_bilingual` 33871–34085; `_apply_formatting_to_cell` 34086–34249; `import_memoq_xliff` 34250–34421; `_is_known_language`/`_lang_from_column_header`/`_confirm_language_pair` 34431–34526; `export_memoq_rtf`+`export_memoq_xliff` 34527–34752; `import_cafetran_bilingual` 34981–35134; `import_trados_bilingual` 35135–35403; `export_trados_bilingual` 35404–35547; `import_sdlppx_package` 35548–35847; sdlxliff-словари 35861–35967; `export_sdlrpx_package` 35968–36122; `_map_sdlxliff_segment`+`import_standalone_sdlxliff`+`import_sdlxliff_folder`+`export_standalone_sdlxliff`+`import/export_phrase_bilingual`+`import/export_dejavu_bilingual` 36123–37554; `export_cafetran_bilingual` 38299–38429; `_attach_sdltm_as_tm`+`_sync_external_tms`+`_delta_sync_external_tm` 19147–19475.
- **Keeper'ы, перемежёванные в удалённых диапазонах (остались):** `import_po_file` 34757–34878, `export_po_file` 34880–34979, `_normalize_language_code` 34422–34428, `get_translator_name` 35848–35859, `import_review_table` 37555–37876, `export/import_bilingual_markdown` 37887–38297.

## 4. Статическая валидация

### 4.1 Защита 1 — резолв стартовой цепочки (AST)

`startup_chain_resolve.py after`: **1131 вызов, 2 неразрешённых** — те же два, что в baseline (1179/2): `self.tm_tab_refresh_callback()`, `self.termbase_tab_refresh_callback()` (присваиваются в рантайме / hasattr-guarded; артефакт расширенной цепочки 8.10, не регрессия). «MISSING METHOD: _sync_external_tms/_delta_sync_external_tm» — записи расширенной цепочки для удалённых методов (ожидаемо).

### 4.2 Защита 2 — grep удалённых идентификаторов

`protection2.py`: 35 идентификаторов (все методы, имена модулей, `match_memoq_status`, `compose_memoq_status`, `memoq_source_file`, `_is_cafetran_project`, `attach_sdltm_btn`, `detect_memoq`, `--translate-sdlxliff`) по `Supervertaler.py` + `modules/**` (regex с word-boundary, учитывающим дефис `--batch`). Результат: **2 попадания** — определения `match_memoq_status`/`compose_memoq_status` в остающемся `modules/statuses.py` (185, 229), вызовов 0 (единственные импортёры — удалённая строка 325–326). Вне удалённого кода упоминаний удалённых идентификаторов **0**.

Дополнительный residual-скан (`memoq|cafetran|dejavu|sdlppx|sdlrpx|sdltm|batch_offload|phrase_bilingual`, регистронезависимо): только допустимые остатки — подсветка тегов memoQ/CafeTran в TagHighlighter (общий редакторский функционал), комментарии-конвенции, определения в statuses.py, PyPI-keywords в `setup.py:90–92` (метаданные, не код), поля `.svproj` (`sdlppx_source_path`, `sdlxliff_source_paths` — отображение в Properties проекта, решение 2), sdlxliff в остающихся модулях (решение 2).

### 4.3 Защита 3 — pyflakes undefined names

До/после: **149 строк / 12 уникальных имён, new = ∅, gone = ∅** (`undefined_names_before.txt` / `undefined_names_after.txt`).

### 4.4 AST-проверки

`create_menus`: 0 ссылок на удалённые слоты; 34 `addSeparator` / 89 `addAction`, двойных разделителей нет. `main()`: baseline-флаги `['--batch','--translate-sdlxliff']` → после `[]`; тело main() цело. Вызовов удалённых методов не осталось (защита 1 + grep).

### 4.5 8 базовых метрик (counts.py, идентичная команда)

| Метрика | До (130 py) | После (121 py) | Δ |
|---|---|---|---|
| `\.connect\(` | 1069 | 1029 | −40 (39 в снапшотах зон + 1 в sdltm_handler.py) |
| `QShortcut\(` | 11 | 11 | 0 |
| `create_shortcut\(` | 31 | 31 | 0 |
| `QTimer\(` | 20 | 19 | −1 (зона init_external_tm_timer) |
| `timeout\.connect` | 20 | 19 | −1 (та же зона) |
| `QTimer\.timeout` | 0 | 0 | 0 |
| `singleShot` | 60 | 60 | 0 |
| `QMetaObject\.invokeMethod` | 1 | 1 | 0 |

### 4.6 Регрессия общих путей (offscreen, диалоги нейтрализованы, один вход ДО/ПОСЛЕ)

`regress_common.py` в worktree HEAD (`head-wt`) и в рабочей копии, изолированный профиль, вход: test.txt (5 строк), test.md (5 строк), test.docx (python-docx, 4 абзаца). Сегменты заполнены целевым текстом; экспорт Simple text / Translated docx / TMX из грида.

| Метрика | ДО | ПОСЛЕ |
|---|---|---|
| import txt сегментов | 5 | 5 |
| export Simple text sha256 | `5a12501f934a589c` | `5a12501f934a589c` |
| import md сегментов | 5 | 5 |
| import docx сегментов (Okapi) | 4 | 4 |
| export translated docx sha256 (zip-содержимое) | `44828d90090f046d` | `44828d90090f046d` |
| export TMX sha256 (creationdate нормализован) | `c413d56372e69dd9` | `c413d56372e69dd9` |

Расхождений нет. MODAL-ATTEMPTS: до 4 (включая диалог скачивания Okapi-сайдкара в чистом iso), после 3 (сайдкар уже установлен — диалог не потребовался). Примечание харнесса: отложенный `QTimer(1500)` создания сайдкара требует прокачки event loop (добавлено в скрипт; в before-прогоне loop крутил вложенный диалог скачивания).

### 4.7 Offscreen-пробы до/после

- **S-clean** (изолированный профиль, пустой старт): окно строится, main_tabs 6, хоткей при старте только ctrl+alt+q, модалок 0, дерево данных **28 записей** (как в baseline 8.8). Меню: **90 → 61** строк; diff = ровно 29 CAT-строк (import: 5 подменю + 10 пунктов; export: 5 подменю + 9 пунктов), остальные пункты идентичны.
- **S-upgrade** (копия существующей папки данных): старт без исключений, hash-diff файлов данных **пустой** (added=[] removed=[] changed=[]), дерево стабильно.

### 4.8 Headless-импорты и CLI

- Headless: **105 ok / 6 fail / 111** (baseline 114/6/120; 9 модулей вычеркнуты из инвентаря, те же 6 предсуществующих отказа: tkinter×4, fitz, GlossaryInfo).
- CLI `--batch` после: ветка удалена, `main()` штатно стартует приложение (ожидаемое поведение по §1 п.5), traceback = 0. Первый прогон (без изоляции) поднял приложение на production user_data — процессы убиты, созданный указатель и папка `C:\Users\Dmitry\Supervertaler` удалены (профиль восстановлен); повторный прогон — изолированный профиль, offscreen, чистый старт без traceback.

### 4.9 Верификация снапшотов

`verify_snapshots.py`: 35/35 зон байт-в-байт против `git show HEAD:Supervertaler.py` (HEAD нормализован LF→CRLF по AGENTS.md «Git line-ending artifacts»; сравнение file-to-file). fails = 0.

### 4.10 Пакеты-кандидаты (requirements.txt/pyproject НЕ менять)

| Пакет | Потребители после 8.9 | Кандидат |
|---|---|---|
| lxml (requirements.txt:18, pyproject.toml:66) | **0** (был только в 9 удалённых модулях + 2 строки внутри удалённых методов) | удалить в финальном инвентаре сирот |
| python-docx | 4 (Supervertaler.py, docx_handler.py, pdf_rescue_Qt.py, pdf_rescue_Tkinter.py) | остаётся |

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: код `ede28068` (сборка от 2026-10-03, состояние `960be5d8` вложенного git). Основание — `D:\SupervertalerPortable_test\SupervertalerPortable\`.

| № | Путь (в сборке) | Действие | SHA256 (новый) | Примечание |
|---|---|---|---|---|
| 1 | `SupervertalerPortable\Supervertaler.py` | **заменить** | `aab1f180e5789878c014d6042a0ee1a29c9e7bdf1d85dbb02e0722f3604f7644` | копия из `E:\Dev\SupervertalerPortable\Supervertaler.py` (CRLF) |
| 2 | `SupervertalerPortable\modules\memoqrtf_handler.py` | **УДАЛИТЬ** | — | |
| 3 | `SupervertalerPortable\modules\mqxliff_handler.py` | **УДАЛИТЬ** | — | |
| 4 | `SupervertalerPortable\modules\cafetran_docx_handler.py` | **УДАЛИТЬ** | — | |
| 5 | `SupervertalerPortable\modules\trados_docx_handler.py` | **УДАЛИТЬ** | — | |
| 6 | `SupervertalerPortable\modules\sdlppx_handler.py` | **УДАЛИТЬ** | — | |
| 7 | `SupervertalerPortable\modules\phrase_docx_handler.py` | **УДАЛИТЬ** | — | |
| 8 | `SupervertalerPortable\modules\dejavurtf_handler.py` | **УДАЛИТЬ** | — | |
| 9 | `SupervertalerPortable\modules\batch_offload.py` | **УДАЛИТЬ** | — | |
| 10 | `SupervertalerPortable\modules\sdltm_handler.py` | **УДАЛИТЬ** | — | |

Все 9 модулей удалять обязательно: забытый импорт проявится только при их отсутствии. `modules\statuses.py` остаётся (в нём остались неиспользуемые определения memoQ-статусов — см. §7/§8).

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data; сначала КОНТРОЛЬ на базовой сборке, затем после пакета)

Процедура чистого старта (из 8.8): бэкап `%APPDATA%\Supervertaler\config.json` и `%USERPROFILE%\.supervertaler_config.json`, указатель на пустую папку, после проверки — восстановить.

- **T8.9.1** апгрейд-старт на копии: старт без исключений; меню Project/Import/Export/Tools/Help открываются; CAT-пунктов (memoQ, CafeTran, Trados Studio, Phrase (Memsource), Déjà Vu X3) нет; разделители в порядке (одинарные).
- **T8.9.2** импорт: Import Document (docx), Import Text/Markdown, Import Folder — работают, сегменты появляются (в Import Folder чекбокса memoQ нет).
- **T8.9.3** экспорт: Translated document, Simple text file, TMX (из грида и из выбранного сегмента) — файлы создаются и открываются.
- **T8.9.4** вкладка TMs: импорт TMX, создание/подключение TM работают; кнопки/пунктов «Attach Trados TM (.sdltm)» нет.
- **T8.9.5** drag-and-drop .docx/.txt на окно — поведение как раньше (у окна drop-обработчика нет — проверка фиксирует это); перетаскивание .sdlxliff/.mqxliff (если есть под рукой) — понятное поведение без traceback.
- **T8.9.6** Settings: все 14 страниц открываются (в т.ч. File Types, Keyboard Shortcuts); Save сохраняет.
- **T8.9.7** чистый старт (пустая папка через указатель): окно открывается без визарда; ключ API → импорт md → правка сегмента → Save → перезапуск; восстановить указатели.
- **T8.9.8** CLI: `python Supervertaler.py --batch` — флаг больше не обрабатывается: приложение стартует штатно (ожидаемое поведение по §1 п.5), без traceback.
- **T8.9.9** live-test на копии: импорт файла 180/400 сегментов, перевод сегмента, TM-подсказки, Save, навигация по всем вкладкам; открытие .svproj, ранее импортированного из CAT-формата (если есть; иначе N/A — поля sdlppx/sdlxliff в Properties проекта отображаются, импортёра нет).
- **T8.9.10** выход: иконка трея исчезает, процесс завершается (0xC0000005 — предсуществующий флаки), в логе нет traceback.

## 7. Непокрытые проверки (честно)

1. Ручные сценарии T8.9.1–T8.9.10 — только на сборке Дмитрия (offscreen-пробы покрывают старт/меню/дерево, не интерактив).
2. Drag-and-drop: у главного окна нет drop-обработчика (статически); live-поведение DnD на CAT-файлы не проверялось.
3. Открытие .svproj, импортированного ранее из CAT-формата — зависит от наличия такого проекта в user_data (T8.9.9).
4. Строковая динамика (getattr/setProperty/QML) по удалённым именам покрыта grep-паттернами защиты 2; остаточный шанс динамической ссылки, не покрытой паттернами, не нулевой (как в аудите §6 п.4).
5. Регрессия общих путей выполнена на малом входе (5/5/4 сегмента); большой файл (180/400) — в T8.9.9.

**Остатки, оставленные осознанно:** определения `match_memoq_status`/`compose_memoq_status` в остающемся `modules/statuses.py` (0 вызовов — кандидат финального инвентаря сирот); комментарий над удалённой CLI-веткой в `main()` (56795–56797) — в docs-проход; PyPI-keywords memoQ/Trados/SDLPPX в `setup.py` (метаданные); подсветка memoQ/CafeTran-тегов в редакторе (общий функционал, решение 2 — общие форматы остаются).

## 8. Вопросы к Дмитрию

1. `modules/statuses.py`: функции `match_memoq_status`/`compose_memoq_status` осиротели (0 вызовов после 8.9). Удалить их в финальном инвентаре сирот (сам statuses.py остаётся)?
2. Комментарий в `main()` 56795–56797 («Автономный batch-offload-режим…») над удалённой веткой — снести в финальный docs-проход?
3. `setup.py` (PyPI keywords memoQ/Trados/SDLPPX) — оставить как метаданные?
4. lxml (0 потребителей) — подтверждаю удаление из requirements.txt/pyproject в финальном инвентаре сирот?

---

Артефакты: `D:\Temp\SupervertalerPortable\refactoring\b8-9\` — `implement_89.py`, `snapshots\` (35 зон, sha256), `verify_snapshots.py`, `startup_chain_{before,after}.json`, `undefined_names_{before,after}.txt`, `protection2.py`, `counts_{before,after}.txt`, `regress_common.py` + `regress\regress_{before,after}.log` + `regress\out-{before,after}\`, `probes\probe_{before,after}_{clean,upgrade}.log` + `menu_{before,after}.txt`, `headless_{before,after}.txt`, `cli_{before,after}.txt`, `head-wt\` (worktree HEAD).

**Push — только после подтверждения Дмитрия.**

## 9. Ручные тесты Дмитрия (тестовая сборка, 2026-10-09) и решения по вопросам §8

Пакет §5 (замена `Supervertaler.py` SHA `aab1f180…` + удаление всех 9 модулей) применён к
`D:\SupervertalerPortable_test\`; сценарии §6 выполнены на копии user_data.

| Сценарий | Результат |
|---|---|
| T8.9.1 апгрейд-старт | ПОДТВЕРЖДЕНО — старт без исключений; меню Project/Import/Export/Tools/Help открываются; CAT-пунктов (memoQ, CafeTran, Trados Studio, Phrase (Memsource), Déjà Vu X3) нет; разделители в порядке (одинарные) |
| T8.9.2 импорт | ПОДТВЕРЖДЕНО — Import Document (docx), Import Text/Markdown, Import Folder работают, сегменты появляются (в Import Folder чекбокса memoQ нет) |
| T8.9.3 экспорт | ПОДТВЕРЖДЕНО — Translated document, Simple text file, TMX (из грида и из выбранного сегмента) — файлы создаются и открываются |
| T8.9.4 вкладка TMs | ПОДТВЕРЖДЕНО — импорт TMX, создание/подключение TM работают; кнопки/пунктов «Attach Trados TM (.sdltm)» нет |
| T8.9.5 drag-and-drop | ПОДТВЕРЖДЕНО — .docx/.txt поведение как раньше (у окна drop-обработчика нет — проверка фиксирует это); перетаскивание .sdlxliff/.mqxliff не тестировалось — нет файлов |
| T8.9.6 Settings | ПОДТВЕРЖДЕНО — все 14 страниц открываются (в т.ч. File Types, Keyboard Shortcuts); Save сохраняет |
| T8.9.7 чистый старт | ПОДТВЕРЖДЕНО — окно открывается без визарда; ключ API → импорт md → правка сегмента → Save → перезапуск; указатели восстановлены |
| T8.9.8 CLI `--batch` | ПОДТВЕРЖДЕНО — флаг больше не обрабатывается: приложение стартует штатно (ожидаемое поведение по §1 п.5), без traceback |
| T8.9.9 live-test | ПОДТВЕРЖДЕНО — импорт 180/400 сегментов, перевод сегмента, TM-подсказки, Save, навигация по всем вкладкам; открытие .svproj из CAT-формата — НЕ ТЕСТИРОВАЛОСЬ (нет файлов; поля sdlppx/sdlxliff в Properties проекта отображаются, импортёра нет) |
| T8.9.10 выход | ПОДТВЕРЖДЕНО — иконка трея исчезает, процесс завершается (0xC0000005 — предсуществующий флаки), в логе нет traceback |

**Ответы Дмитрия на вопросы §8 (решения):**

1. `modules/statuses.py` (`match_memoq_status`/`compose_memoq_status`) — **удалить в финальном
   инвентаре сирот** (сам statuses.py остаётся). → POST_BATCH8_BACKLOG §7.
2. Комментарий в `main()` 56795–56797 («Автономный batch-offload-режим…») — **снести в
   финальный docs-проход**. → POST_BATCH8_BACKLOG §7/§10.
3. `setup.py` (PyPI keywords memoQ/Trados/SDLPPX) — **оставить как метаданные**;
   необходимость файла для portable-сборки определена (ниже).
4. lxml (0 потребителей) — **удаление из requirements.txt/pyproject подтверждено**,
   выполняется в финальном инвентаре сирот. → POST_BATCH8_BACKLOG §7.

**Необходимость `setup.py` для portable-сборки (вопрос 3, измерение):** portable-сборка
`D:\SupervertalerPortable_test\` не содержит `setup.py` (в `SupervertalerPortable\` лежат
только `pyproject.toml` и `requirements.txt`); `start.bat` запускает
`python-embed\python.exe … Supervertaler.py` напрямую, без установки пакета; в репозитории
`setup.py` не вызывается ни одним скриптом/конфигом (grep по `.py/.bat/.md/.toml/.txt/.cfg/.spec`
— только сам файл и упоминания в CODE_MAP/аудитах). Вывод: **для portable-сборки `setup.py`
не нужен** — он обслуживает только PyPI-дистрибуцию (`pip install Supervertaler`,
`py_modules=["Supervertaler"]`, `entry_points console_scripts`); по решению Дмитрия файл
остаётся как метаданные PyPI, keywords memoQ/Trados/SDLPPX не правятся.

**Итог Batch #8.9: закрыт** — код `5a29d3c9`, отчёт `c82cb784`, ручные тесты T8.9.1–T8.9.10
подтверждены (2 подпункта N/A из-за отсутствия CAT-файлов), решения по всем 4 вопросам
получены и занесены в POST_BATCH8_BACKLOG §7.
