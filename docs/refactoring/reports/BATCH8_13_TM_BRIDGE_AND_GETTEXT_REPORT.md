# ОТЧЁТ Batch #8.13 — UI-остатки: TM «Bridge» (часть A) и GNU gettext (часть B)

Этап 2. База кода: **f804d447** (коммит кода Batch #8.12). Дрейф: `git diff --name-only f804d447..HEAD`
до начала работ — только docs-коммиты 182c31ae, 486095d9 (отчёты 8.12 + PROJECT_STATUS + аудиты),
код не тронут. SHA256 рабочей копии `Supervertaler.py` на старте:
`80d53b439a92335007c82593dbd81585d11fbecfe2a60131f9ede5b9a2f1ac43`, 57009 строк — совпал с эталоном промта.

Коммиты батча (локальные, push — только по команде Дмитрия):
* **350e63a8** «Batch #8.13a: remove TM Bridge UI (Dmitry's 8.11 decision)» — Supervertaler.py, 11+/81−;
* **41b7ece1** «Batch #8.13b: remove GNU gettext import/export» — Supervertaler.py 5+/255−,
  `git rm modules/po_handler.py` (−566).

Итог: монолит **57009 → 56689** строк (−320), po_handler.py удалён (−566). Всего −886 строк.

---

## 0. Baseline (Этап 0)

Все прогоны — в `E:\Dev\Work_temp\SupervertalerPortable\refactoring\b8-13\`, интерпретатор
`E:\Dev\python-embed\python.exe`, CWD = репозиторий.

| Проверка | Baseline | Комментарий |
|---|---|---|
| py_compile (все .py репо, excl. `__pycache__`) | **127 ok / 0 fail** | 127 = 111 код приложения + 16 docs-аудитов 8.12; в промте «115» — счёт без docs-аудитов; используем 127 консистентно before/after |
| headless imports (+setup.py) | **92 ok / 2 fail / 94** | fail: `setup` (нет setuptools), `modules.pdf_rescue_Qt` (нет fitz) — известные |
| pyflakes | **596 warnings / 143 undefined-строк / 10 уникальных имён** | тот же набор, что в 8.12 |
| AST startup chain | **926 calls / 0 unresolved** | |
| S-clean probe (offscreen, изолир. профиль) | **28 записей дерева, main_tabs 6, Settings 14, PROBE OK** | |
| S-upgrade probe | **HASH-DIFF пустой, PROBE OK** | |
| regress_common (txt/md/docx/tmx) | **6 sha совпали** (5, 5a12501f…, 5, 4, 44828d90…, c413d563…) | |
| Tools-smoke | **44 пункта, 2 EXC** (gettext TypeError — дефект `@staticmethod`; PDF Rescue ModuleNotFoundError) | |
| termbase regression | **SNAP полный OK** (export_tsv_sha 1fc4f1d5… — uuid4-колонка, см. §4.9 отчёта 8.12) | |
| Спец-baseline TM-вкладки | 9 колонок с Bridge; флаги Read/Write/SuperLookup/Bridge читаются из БД; Select All синхронизирует; сортировка/переименование/удаление работают | |
| Спец-baseline меню/фильтров | 160 строк меню + фильтры всех файловых диалогов; `Import/GNU-gettext: EXC TypeError` (дефект подтверждён), `Export/GNU-gettext: ok` | |

Дефект части B, зафиксированный baseline-командами: AST показывает `@staticmethod` (строка 32713),
отделённый комментариями от `def import_po_file` (32718) → декоратор не применяется, вызов
`self.import_po_file` через `triggered.connect` даёт `TypeError: import_po_file() missing 1 required
positional argument: 'self'` — ровно то, что Дмитрий наблюдал как «нет реакции» (решение 8.12, POST_BATCH8 §8).

## 1. Рекон (Этап 1)

### Часть A — TM Bridge UI

Зоны D-01…D-11 из BATCH8_12_ORPHAN_INVENTORY_REPORT.md §D, границы **перевыведены AST** (после 8.12
монолит сдвинулся на −1). Все обращения к колонкам ≥5 и все bridge-идентификаторы находятся
**строго внутри `_create_tm_list_tab`** (11209–11678 на HEAD):

* `toggle_all_bridge`, `on_bridge_toggle`, `bridge_header_checkbox`, `tm_select_all_bridge_btn`,
  `tm_clear_all_bridge_btn` — ноль внешних ссылок (grep + AST по всему репо);
* внешние читатели таблицы TM обращаются **только к колонке 0** (TM Name) — строки 11687, 19015,
  19089, 19119 (на HEAD);
* `saveState/restoreState` для TM-таблицы нет; сортировка — только `setSortingEnabled`-тумблеры
  при наполнении таблицы; делегатов/декораторов на колонки нет; состояние заголовков не персистится;
* ширина колонок: `setColumnWidth(5..8)` — в зоне; `header().…` синхронизация «Select All» — в зоне.

### Часть B — GNU gettext

* Методы `import_po_file` / `export_po_file` (блок 32713–32940, 228 строк + trailing blank) —
  самодостаточны; общие хелперы (`_check_reimport_same_file`, `_apply_reimport_settings`,
  `_normalize_language_code`, `_clear_caches_after_import`, `_finalise_import_with_indexes`,
  `_ImportProgressDialog`, `load_segments_to_grid`) вызываются и остальным кодом — **остаются**;
* `self.po_handler`, `self.po_source_file` используются только внутри po-методов;
* `modules/po_handler.py` (566 строк, только stdlib: re/pathlib/typing; polib/babel в requirements
  нет) — единственный импортер: монолит (2 точки внутри po-методов);
* `po_source_path`: читатели — `modules/models.py` (поле/сериализация, защищено) и
  `modules/segment_split_merge.py` (`_BILINGUAL_ORIGIN_ATTRS`, защищено); UI-читателей нет;
* экспорт-в-исходный-формат (`export_document`/`export_okapi_merge`) — формат-агностичен, .po-ветки нет;
* Settings → File Types: .po отсутствует; Open Recent: .svproj/.json; drag-and-drop: не найден;
* точки входа UI: меню Import/Export (≈7961–7965 / ≈8022–8026), фильтры Quick Count (≈9478) и
  Import Document (через `OKAPI_OTHER_FORMATS`, ≈29751), `okapi_exts` Quick Count (≈9455),
  формат-списки в трёх docstring/tooltip.

Согласованный список правок (промт: «список согласовать в отчёте ДО правки») — §2 ниже;
никаких правок вне `Supervertaler.py` + `git rm modules/po_handler.py` не потребовалось.

## 2. Что сделано (зона | строки на HEAD | действие)

Строки — на HEAD (f804d447 + docs), выровнены AST-снапшотами (sha256 в `snapshots/`).

### Часть A (коммит 350e63a8)

| Зона | Строки | Действие | sha256 снапшота (16) |
|---|---|---|---|
| D-01 help-строка | 11244 | удалена строка «• Bridge (orange ✓)…» из help-подсказки вкладки | `556a859e9af6f63b` |
| D-02..04 bridge bulk | 11276–11287 | удалены `bridge_header_checkbox`, `tm_select_all_bridge_btn`, `tm_clear_all_bridge_btn` с layout-строками | `bbea34e4fc0def17` |
| D-11 комментарий | 11289–11292 | удалён комментарий про Bridge в блоке bulk-кнопок | `8db7be1b0328814f` |
| D-05..06 колонки | 11306–11319 | `setColumnCount(9→8)`, header-labels без «Bridge», ширины 5=SuperLookup(100), 6=Last Modified(150) | `91621361ef351160` |
| D-07 toggle_all_bridge | 11370–11381 | удалён метод + комментарий «mirroring the Bridge bulk toggle» | `8dacf414d13e10ce` |
| (коммент) | 11383–11385 | комментарий про Bridge в SuperLookup-блоке переформулирован | `298c3722ad0fd0c6` |
| D-08 connect | 11400 | удалён `bridge_header_checkbox.toggled.connect(...)` | `782a025e4faa484e` |
| D-09 строка таблицы | 11513–11544 | удалён per-row bridge-блок (32 строки, incl. `on_bridge_toggle`, tooltip) | `b308da9d5810f421` |
| ренум SuperLookup revert | 11566 | `cellWidget(row_idx, 6→5)` | `0fddc5d5546c7fd3` |
| ренум SuperLookup set | 11573 | `setCellWidget(row, 6→5, …)` | `bf6ce18f30a1983d` |
| ренум Last Modified | 11585 | `setItem(row, 7→6, modified)` | `8fcee9f1a8508b35` |
| ренум Description | 11589 | `setItem(row, 8→7, desc_text)` | `c2c8751e77744286` |
| D-10 header-sync | 11591–11607 | удалён bridge-блок blockSignals/setChecked/all_bridge_checked; `all_superlookup_checked` → col 5 | `16fdc36652ec13f0` |

### Часть B (коммит 41b7ece1)

| Зона | Строки | Действие | sha256 снапшота (16) |
|---|---|---|---|
| B меню Import | 7958–7967 | удалён блок «GNU gettext (.po / .pot)...» (QAction, tooltip, connect, addAction) + один соседний разделитель (двойных не осталось) | `fb0d92fd3bc7b8d8` |
| B меню Export | 8019–8029 | удалён блок «GNU gettext - Translated (.po)...» + один соседний разделитель | `dc91926659aa37aa` |
| B okapi_exts | 9453–9455 | из списка расширений Quick Count убран `'.po'` | `c723f2c062a440a6` |
| B Quick Count formats | 9473–9481 | из списка фильтров убрана строка `("PO (gettext)", "*.po")` | `ad7fe3869ecddd03` |
| B OKAPI_OTHER_FORMATS | 29744–29754 | убрана строка `("PO (gettext)", "*.po")` (питает фильтр Import Document) | `df615412a01cb797` |
| B docstring/tooltip ×3 | 7931–7939, 11952–11958, 29695–29701 | из формат-списков в текстах подсказок убран PO | (в diff) |
| B po-методы | 32713–32940 | вырезан блок `import_po_file`/`export_po_file` (228 строк + trailing blank; шов: `_normalize_language_code` → `get_translator_name`) | `bf99a6c7fe92499f` |
| B модуль | — | `git rm modules/po_handler.py` (566 строк) | HEAD `990c6bb8d4fd96c8…` |

Защищённое (не тронуто, проверено grep'ом): колонка БД `bridged_to_trados` + `set_bridged_to_trados`
(`database_manager.py`, `tm_metadata_manager.py`; сеттер остался без вызывателей — разрешено промтом),
`Project.po_source_path` (`models.py`), `_BILINGUAL_ORIGIN_ATTRS` (`segment_split_merge.py`),
колонки Read/Write/SuperLookup и их логика, TMX импорт/экспорт, создание/переименование/удаление TM,
схема БД, requirements/pyproject, механизм пути данных, комментарии `i18n.py`/`extract_strings.py`
(док-остатки — батч 8.16).

## 3. Ключевые диффы

Часть A, колонки (до/после):

```python
tm_table.setColumnCount(9)
["TM Name","Languages","Entries","Read","Write","Bridge","🔍 SuperLookup","Last Modified","Description"]
→
tm_table.setColumnCount(8)
["TM Name","Languages","Entries","Read","Write","🔍 SuperLookup","Last Modified","Description"]
```

Часть B, меню Import (после): `Document | Text/Markdown | — | Folder | — | 🔁 Re-importable | — | ❓ Help`
(было: `… Folder | — | GNU gettext | — | 🔁 Re-importable …`); Export (после):
`Document | Simple Text | — | Folder | — | Relocate | …` (GNU gettext убран, разделители без двойных).

Фильтр Import Document (после): `All supported formats (*.docx *.idml *.html *.htm *.xliff *.xlf
*.xlsx *.pptx)` — без `*.po`; Quick Count — аналогично.

## 4. Валидация (Этап 3)

### Часть A (после 350e63a8)

| Проверка | Результат |
|---|---|
| py_compile | 127/0 (без изменений) |
| headless | 92/2/94 (без изменений) |
| AST chain | 926/0 (без изменений) |
| pyflakes | 596/143/10 — идентично baseline |
| protection grep (bridge-идентификаторы) | 0 hits в коде приложения |
| S-clean / S-upgrade | 28 записей / HASH-DIFF пустой — идентично |
| regress_common | 6 sha идентичны |
| Tools-smoke | 44 пункта; PDF-Rescue `new-widgets` флуктуирует (['QFrame'] vs ['QFrame','QMenu']) — доказано pre-existing прогоном на HEAD-worktree (smoke2) |
| termbase | идентично (sha uuid4-колонки — см. §4.9 отчёта 8.12) |
| TM-регрессия (спец-проба) | **8 колонок**, заголовки `TM Name, Languages, Entries, Read, Write, 🔍 SuperLookup, Last Modified, Description`; каждый чекбокс меняет СВОЙ флаг (Read→tm_activation, Write→set_read_only, SuperLookup→set_superlookup_enabled); Select All синхронизирует строки; сортировка по колонкам работает; переименование/удаление OK; **`bridged` в БД не меняется кодом приложения** (всегда False) |

### Часть B (после 41b7ece1)

| Проверка | Результат |
|---|---|
| py_compile | **126/0** (127 − po_handler.py) |
| headless | **91/2/93** (−po_handler; fail-ы те же) |
| AST chain | **922/0** (−4 вызова из вырезанных методов; новых unresolved нет) |
| pyflakes | **596/143/10 — идентично baseline** (po-методы не давали undefined-имён; новых warning'ов нет) |
| protection grep | `import_po_file/export_po_file/po_handler/POHandler/PO (gettext)/*.po/po_source_file/import_po_action/export_po_action` — **0 hits** в коде приложения. Остатки только разрешённые: `docs/refactoring/audits/batch8-12_code_tools_smoke.py` (smoke-таблица 8.12, кликает по имени — ожидаемо), комментарии «GNU gettext» в `i18n.py`/`models.py`/`extract_strings.py` (док-остатки, 8.16) |
| защищённое | `bridged_to_trados` 12 hits, `set_bridged_to_trados` 1, `po_source_path` 8, `_BILINGUAL_ORIGIN_ATTRS` 2 — все на местах |
| S-clean / S-upgrade | 28 записей / HASH-DIFF пустой — идентично |
| regress_common | 6 sha идентичны (MODAL-ATTEMPTS 3 vs 4 — диалог opt-in статистики: в iso-профиле уже записан отказ, диалог не появляется; не регрессия) |
| Tools-smoke | 44 пункта; **оба gettext-пункта → ожидаемый `AttributeError`** (методов нет) — это и есть «ожидаемо исчезнувшее gettext-исключение»; PDF-Rescue — известная флуктуация QMenu; остальные 42 идентичны |
| termbase | идентично (свежий профиль tb-regress2: полный SNAP OK; sha uuid4-колонки отличается — известное) |
| menu probe afterB | QAction-списки всех меню: **разница ровно 2 gettext-пункта** (+ схлопнутые разделители, двойных нет); фильтры всех диалогов — ровно без «PO (gettext)»/`*.po`; .svproj, docx/txt/md, TMX — без изменений |
| EOL | `git ls-files --eol`: `i/lf w/crlf` без изменений; `\r\r\n` = 0; CRLF 56689/56689 |
| diff --stat | только `Supervertaler.py` + `modules/po_handler.py` — посторонних файлов нет |
| SHA256 после коммита | рабочая копия `30799778e4462af1f0e8531806c2d5197290d87ae4ae63eb627e6889c5ace166` (56689 строк); blob в git `1a488627a1ef1698717541b80b739978461bae41c255451a821d5d903c7ec348` (LF-нормализация git, содержимое идентично) |

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ (`D:\SupervertalerPortable_test\`)

База кода: **f804d447** (текущая тестовая сборка Дмитрия после 8.12). SHA256 — рабочей копии (CRLF).

| № | Путь | Действие | SHA256 | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler\Supervertaler.py` | **ЗАМЕНИТЬ** | `30799778e4462af1f0e8531806c2d5197290d87ae4ae63eb627e6889c5ace166` | состояние после 8.13b, 56689 строк (мост убран, gettext убран) |
| 2 | `Supervertaler\modules\po_handler.py` | **УДАЛИТЬ** (обязательно) | `990c6bb8d4fd96c885e2d3be261d49a549a463a7e803bebb819a01f43c183d6b` (HEAD-база) | модуль удалён из репозитория; в сборке быть не должен |

Остальные файлы сборки не меняются. `_pth`/`start.bat`/профиль — без изменений.

## 6. СЦЕНАРИИ РУЧНОГО ТЕСТИРОВАНИЯ (T8.13.x)

Все сценарии — на **копии** user_data (не на боевых данных); контроль — на базовой сборке f804d447
(до применения пакета). Чистый старт = быстрый прогон T8.13.1 + T8.13.2.

| № | Сценарий | Ожидаемый результат |
|---|---|---|
| T8.13.1 | Открыть вкладку TMs | Таблица **8 колонок**: `TM Name, Languages, Entries, Read, Write, 🔍 SuperLookup, Last Modified, Description`; колонки «Bridge» и кнопок «Select All Bridge»/«Clear All Bridge» **нет**; help-подсказка вкладки без строки про Bridge |
| T8.13.2 | Создать 2 TM; переключать Read/Write/SuperLookup (строковые чекбоксы) | Каждый чекбокс меняет свой флаг: Read активирует/деактивирует TM (Match Panel), Write снимает/ставит read-only (строка редактируется), SuperLookup участвует/не участвует в SuperLookup-поиске |
| T8.13.3 | «Select All Read», «Select All Write», «Select All SuperLookup» (шапочные чекбоксы) | Все строки синхронно меняются; повторный клик снимает; поведение как в baseline (кроме отсутствия Bridge) |
| T8.13.4 | Сортировка по клику на заголовки (Languages, Entries, Last Modified), изменение ширины колонок | Сортировка и ширины работают, колонки не разъезжаются (ренум 6→5, 7→6, 8→7 корректен) |
| T8.13.5 | Меню Project → Import и Export | Пунктов «GNU gettext (.po / .pot)...» и «GNU gettext - Translated (.po)...» **нет**; разделители без двойных; остальные пункты на местах (Folder, Re-importable, TMX, Relocate…) |
| T8.13.6 | Import Document и Quick Count — открыть файловые диалоги | В фильтрах нет «PO (gettext)» и `*.po`; docx/idml/html/xliff/xlsx/pptx — есть; импорт docx/txt/md работает как раньше |
| T8.13.7 | Открыть существующий .svproj-проект (в т.ч. импортированный ранее из .po, если есть такой в user_data) | Проект открывается; сегменты, комментарии, поля пути (po_source_path) сохраняются; экспорт в исходный формат (DOCX/OKAPI) работает; .po-экспорт для такого проекта недоступен (пункта меню нет) |
| T8.13.8 | Импорт/экспорт TMX, создание/переименование/удаление TM | Работают без изменений (защищённые пути) |
| T8.13.9 | Выход из приложения (Exit), повторный запуск | Закрытие чистое, без ошибок; при повторном запуске TM-таблица и меню в состоянии T8.13.1/T8.13.5 |

## 7. Непокрытые проверки

* U-A1: реальное (не offscreen) поведение header-checkbox «Select All» при видимой вкладке —
  offscreen-проба эмулирует через `setChecked`; визуальный клик не проверялся.
* U-A2: персистентность ширины колонок TM-таблицы между запусками (нет saveState — проверено
  статически; живая проверка на сборке не выполнялась).
* U-B1: импорт .po-файла через «Folder (Multiple Files)» с .po внутри — не проверялся (путь
  проходит через тот же формат-список, который очищен; ожидается ValueError/пропуск пофайлово).
* U-B2: проект, ранее импортированный из .po: экспорт «в исходный формат» через Okapi-диспетчер
  для .po-origin проекта — live-проверка на сборке (T8.13.7) статически не покрыта.
* U-B3: Termbase/TMX-регрессии запускались в изолированном профиле с пустой БД; проверка на
  реальном user_data — только в сценариях Дмитрия.

## 8. Вопросы к Дмитрию

1. **tools_smoke-аудит 8.12** (`docs/refactoring/audits/batch8-12_code_tools_smoke.py`) содержит
   пункты `Project/Import/GNU-gettext`/`Export/GNU-gettext`, которые теперь дают `AttributeError`.
   Аудит-артефакт зафиксирован как есть (исторический baseline-лог). Предложить обновить smoke-таблицу
   в новом аудите 8.13 (сделано: `smoke/smoke_afterB.log`), а старый файл не трогать — ок?
2. **CODE_MAP_REFACTOR.md / DEPENDENCY_MAP.md** содержат записи о `po_handler` (строки 1150, 24, 111,
   225) — отнесены к док-остаткам батча 8.16 согласно промту. Подтвердить.
3. **`set_bridged_to_trados`** остался без вызывателей (UI убран). Промт: сеттер может остаться.
   Удаление сеттера + колонки БД — кандидаты в 8.18 (мёртвые методы) или в отдельный финальный
   проход по orphan-инвентарю? (Пока не тронуто.)
4. **`Project.po_source_path`** (поле + сериализация) остаётся по промту. После 8.13 у него нет
   писателей UI (кроме старых .svproj-файлов). Оставить до финального инвентаря — ок?
5. **py_compile 127 vs 115**: счёт 127 включает 16 docs-аудит-скриптов, закоммиченных в 8.12.
   Зафиксировано в §0; использовать 127 как канонический baseline-счёт дальше — ок?

---

*Итоговые коммиты: 350e63a8 (часть A), 41b7ece1 (часть B). Push — только по команде Дмитрия.*
*Отчёт доставлен — агент останавливается и ждёт вердикта координатора.*

## 9. Вердикт Дмитрия (2026-10-10): ручные тесты T8.13.1–T8.13.9 + ответы на вопросы §8

**Batch #8.13 ПРИНЯТ.** Все сценарии подтверждены; единственное НЕПОДТВЕРЖДЕНО (T8.13.3,
массовый Write) — **изначальный баг, не связанный с изменениями 8.13** (доказательство §9.2:
присутствует от корневого коммита репозитория и в v1.10.372).

### 9.1 Результаты ручного тестирования

| № | Результат |
|---|---|
| T8.13.1 (8 колонок, нет Bridge) | ПОДТВЕРЖДЕНО |
| T8.13.2 (строчные флаги Read/Write/SuperLookup) | ПОДТВЕРЖДЕНО |
| T8.13.3 «Select All Read» | ПОДТВЕРЖДЕНО: строки синхронно; повторный клик снимает синхронно; кнопка «Clear All Read» снимает синхронно |
| T8.13.3 «Select All Write» | **НЕПОДТВЕРЖДЕНО**: массово не работает, только каждая строка по отдельности (разбор §9.2; то же поведение в v1.10.372) |
| T8.13.3 «Select All SuperLookup» | ПОДТВЕРЖДЕНО |
| T8.13.4 (сортировка/ширины) | ПОДТВЕРЖДЕНО |
| T8.13.5 (меню без gettext) | ПОДТВЕРЖДЕНО |
| T8.13.6 (фильтры без PO) | ПОДТВЕРЖДЕНО |
| T8.13.7 (открытие .svproj) | ПОДТВЕРЖДЕНО (`.po`-проектов в user_data нет) |
| T8.13.8 (TMX, создание/переименование/удаление TM) | ПОДТВЕРЖДЕНО |
| T8.13.9 (выход/повторный запуск) | ПОДТВЕРЖДЕНО |

### 9.2 Разбор НЕПОДТВЕРЖДЕНО T8.13.3: массовый Write — изначальный баг, не защита

**Вывод: это баг ввода неверного имени метода, а не функция защиты.** Доказательства:

* Код (после 8.13): `toggle_all_write` (монолит 11319–11330) в цикле вызывает
  `tm_metadata_mgr.set_tm_read_only(tm_id, not checked)` **за `hasattr`-защитой**.
  Метода `set_tm_read_only` в `modules/tm_metadata_manager.py` не существует — есть
  `set_read_only` (строка 634). `hasattr` → False → тело `if` не выполняется, исключения нет,
  в лог ничего не пишется (блок `except` не срабатывает) — **тихий no-op**.
* Строчный чекбокс Write вызывает правильный `set_read_only` (монолит 11445) — работает,
  что Дмитрий и наблюдал («только каждая строка по отдельности»).
* Git-история: имя `set_tm_read_only` появляется в репозитории **только** как пара
  (hasattr + вызов) внутри `toggle_all_write`, впервые уже в корневом коммите
  **13bd37fb** «baseline before extraction batch 1» (2026-09-12). `def set_tm_read_only`
  не существовало ни в одной ревизии; в той же ревизии `modules/tm_metadata_manager.py`
  уже имел `set_read_only` (строка 625). Значит, самый старый срез истории репо уже сломан;
  поведение в v1.10.372 (до начала рефакторинга) согласуется — унаследованный дефект.
* Это не защита: комментарий в коде «checked = writable, read_only is the opposite» и
  строчный обработчик показывают, что массовое переключение должно было снимать/ставить
  `read_only` всем TM. «Защита от записи одного сегмента во все TM» логикой не
  предусмотрена — до цикла дело просто не доходит.
* Побочное наблюдение для будущей починки: `toggle_all_write` не инвалидирует кэш
  переводов (в отличие от `toggle_all_read`, который делает
  `invalidate_translation_cache(smart_invalidation=False)`).

**Варианты (решение за Дмитрием; в 8.13 не включено):**
(a) починка одной строки `set_tm_read_only` → `set_read_only` (+ инвалидация кэша) —
кандидат в 8.15 «скрытые баги» вместе с E-02/E-03 того же сорта (обращение к
несуществующему/отсоединённому имени);
(b) убрать массовый чекбокс/кнопку Write;
(c) памятка в интерфейсе.
Поскольку это баг, (a) — единственный вариант, сохраняющий задуманную функциональность;
(b)/(c) имеют смысл, только если массовое переключение Write будет сочтено нежелательным.

### 9.3 Ответы на вопросы отчёта (§8) — решения Дмитрия

1. **Smoke-таблица.** Старый `batch8-12_code_tools_smoke.py` не трогать — исторический
   baseline-лог. В 8.13 заведена обновлённая таблица **без** gettext-пунктов:
   `docs/refactoring/audits/batch8-13_code_tools_smoke.py` (42 пункта). Канонический
   baseline-прогон на состоянии после 8.13b: `batch8-13_code_smoke_baseline813.log`
   (42 items, SMOKE OK; единственный EXC — PDF Rescue без fitz, известный). Все следующие
   батчи (8.15, 8.18) берут за baseline именно эту таблицу.
2. **po_handler в CODE_MAP_REFACTOR.md / DEPENDENCY_MAP.md** — док-остатки, но их место
   в **8.17** (документы репозитория), не в 8.16 (комментарии и докстринги в коде).
   По инвентарю раздел J относится к 8.17.
3. **set_bridged_to_trados.** Колонку БД **не удалять никогда**: решение «схему БД не
   трогаем» остаётся в силе. Сеттер сейчас не трогать — 29 строк мёртвого метода в модуле,
   на отдельный батч не тянет. В 8.18 сеттер попадёт, если там будет сканирование мёртвых
   методов и по модулям: список 63 методов считался только по монолиту, модульный проход
   будет добавлен в промпт 8.18 отдельным разделом, и сеттер вместе с другими найденными
   подберёт он.
4. **Project.po_source_path** — оставить. То же правило, что для `sdlppx_source_path` и
   прочих CAT-полей: поля модели и .svproj остаются инертными ради совместимости старых
   проектов. Все такие поля будут собраны одним решением в финальном проходе,
   по умолчанию «оставить».
5. **Счёт py_compile** — два числа: канонический baseline = только код вне `docs/`
   (на f804d447 это **115**), не растёт от аудит-скриптов, которые каждый батч коммитит в
   `docs/refactoring/audits/`; справочно — общий счёт со скриптами (сейчас **127**).
   Сравнение до и после — всегда на одном и том же наборе файлов. Критерий один: 0 ошибок.
   Правило зафиксировано в AGENTS.md («Refactoring batch validation practices»).

**Следующий шаг: батч 8.15 (скрытые баги: E-01, E-02, E-03, MyMemory default OFF) — старт
только по команде Дмитрия и его промпту.** Кандидатом в 8.15 также может стать починка
массового Write (§9.2 вариант a) — на усмотрение Дмитрия при составлении промпта.
