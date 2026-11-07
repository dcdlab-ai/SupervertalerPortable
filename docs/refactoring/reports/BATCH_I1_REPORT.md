# ОТЧЁТ BATCH I1 — писатель InDesign Tagged Text (md → .txt)

**Агент, 2026-11-07.** Первый код-батч I-серии. Промпт координатора (с уточнением
«ШАПКА» от 2026-11-07: по умолчанию шапка БЕЗ ColorTable). Продуктовый код
`Supervertaler.py` и существующие `modules/*`, `translations/`, `assets/`,
`requirements*`, `pyproject.toml` **не тронуты**; добавлен новый пакет
`modules/tagged_text/` (только stdlib), тест-фикстуры, headless-тесты и docs.
Пуша нет — стоп до вердикта. Ручные тесты — §10.

## s0. Итог

* Новый пакет `modules/tagged_text/` — 5 файлов, только stdlib:
  `__init__`, `mdparse` (md → блоки), `writer` (блоки → байты Tagged Text),
  `stylemap` (JSON «роль → имя стиля»), `__main__` (CLI).
* Регенерация T4b2 **побайтово** (sha256 `56fe7e6b…3ea196` совпал) — режим
  `color_table='gboh'` + `char_style_policy='all'` (см. s2.5).
* Headless-тесты: **75 проверок / 0 провалов** (фикстуры ≤ 9 абзацев, в git).
* Прогон на реальных md: T-I1a (docling) и T-I1b (PyMuPDF4LLM) — отчёты в s4,
  числа согласуются с замерами I0-B (`i0_md_tables_audit.py`).
* T4c1 (без ColorTable) / T4c2 (минимальный ColorTable Black+Paper) созданы
  вне git + инструкция Дмитрию (s5).
* Упаковщик: полная офлайн-сборка — zip 128 401 701 байт, **7325 файлов**
  (P2.4: 7320, ровно +5 новых .py), **0 `__pycache__`/`.pyc`**, importsmoke
  **OK all 12 modules** включая `modules.tagged_text`, About v1.10.371.
* Защитная батарея «было = стало» — s7: chain 874/0, pyflakes 519 (новый код
  0), headless 89→94 ok/0 fail (+5 модулей пакета), smoke 40 SMOKE OK,
  regress-хэши 3/3 без изменений, e2e-агрегат `982e72a247f0a6ac` без изменений.
* git diff по продукту пуст (единственное изменение вне нового пакета —
  `docs/templates/packaging_helper.py` +2 строки: importsmoke-список).

## s1. ШАГ 0 — docs-коммит s11.9 (отдельным коммитом)

До кода в `BATCH_I0_REPORT.md` добавлен раздел **s11.9** — результаты
микротестов I0-C от Дмитрия (2026-11-07): T4b1 провал (однострочная шапка
читается как обычный текст), T4b2 полный успех (пустых абзацев нет, стили и
жирный/курсив работают), T5b гипотеза подтверждена по строкам (ошибка ровно
на `\; \: \, \=` в ТЕКСТЕ, контроли чисты; символьная группа — тест
некорректен, НЕ проверено), T6b успех (таблица по эталону, с BOM и без).
Коммит `3c2fbc8d`, только docs.

## s2. Состав и ключевые решения формата

### s2.1. Файлы пакета

| Файл | Назначение |
|---|---|
| `modules/tagged_text/__init__.py` | докстринг-контракт формата; экспорт API |
| `modules/tagged_text/mdparse.py` | строка md → блоки (одна непустая строка = один блок, как `import_simple_txt`); роли h1/h2/h3/p/li/li_n/img/table_row; счётчики (ParseStats) |
| `modules/tagged_text/writer.py` | блоки → байты (UTF-16LE+BOM, CRLF); шапка, Define*Style, экранирование, сущности, `<br>`, выделения, img; ExportReport |
| `modules/tagged_text/stylemap.py` | JSON-карта «роль → имя стиля», версия 1, load/save, умолчания |
| `modules/tagged_text/__main__.py` | CLI: `python -m modules.tagged_text in.md out.txt [--map …] [--images-dir …] [--save-map …] [--color-table …] [--char-styles …] [--report …]` |

### s2.2. Формат (все правила — по итогам ручных тестов I0/I0-B/I0-C, s11.8–s11.9)

* Кодировка **только UTF-16LE + BOM**, разделитель CRLF, финальный CRLF.
* Строка 1 `<UNICODE-WIN>` одна (T4b1: однострочная шапка непригодна);
  строка 2 `<Version:16.4><FeatureSet:InDesign-Roman>` **без ColorTable**
  (уточнение координатора «ШАПКА», s11.9); режимы ColorTable:
  `minimal` (Black+Paper, T4c2) и `gboh` (дословно строка 2 образца — для
  побайтовой регенерации T4b2). Версия `16.4` — константа `VERSION_DEFAULT`.
* Define*Style по одному на строку, только реально использованные роли,
  порядок фиксированный (h1,h2,h3,p,li,li_n,img,table_row); формат
  `<DefineParaStyle:ИМЯ=<Nextstyle:ИМЯ>>`; символьные
  `<DefineCharStyle:ИМЯ=<Nextstyle:ИМЯ><cTypeface:…>>` с атрибутами
  `Bold`/`Italic`/`Bold Italic` (образец GBoH/T4b2 — пустые определения
  дают «пустой» стиль, s11.6).
* Экранирование в ТЕКСТЕ: только `\`→`\\`, `<`→`\<`, `>`→`\>` (T5b:
  «лишние» `\; \: \, \=` в тексте дают ошибки в логе InDesign; при этом
  `\;` исходного текста пишется `\\;` и отображается как `\;`).
* Экранирование в ЗНАЧЕНИЯХ тегов: `\ < > : ; , = [ ]` — минимум промпта +
  скобки (`\[Basic Table\]` эталона). **Подчёркивание НЕ экранируется**
  (в образце GBoH экранируется `\_` в имени цвета, но в именах стилей это
  не проверено — вопрос координатору §9.1; дефолтное имя `table_row`
  поэтому пишется без `\_`).
* HTML-сущности только с «;»: именованные `amp lt gt quot apos` + числовые
  (десятичные и hex) раскодируются; неизвестная именованная и сущность без
  «;» остаются буквально и в счётчик не попадают. Декодированные `<`/`>`
  затем экранируются по правилам выхода (`&lt;` → `\<`).
* `<br>`/`<br/>`/`<br />` (без учёта регистра) → одиночный LF (принудительный
  перенос внутри абзаца).
* Выделения: `***…***` и `**_…_**` → BoldItalic, `**…**` → Bold,
  `*…*` → Italic, `_…_` → Italic (только на границе слов: `snake_case`,
  `a_b_c` не выделяются) — через `<CharStyle:ИМЯ>…<CharStyle:>`.
  Несбалансированные маркеры остаются буквально; счётчик = каждый пробег
  `*` и каждое подчёркивание на границе слов в неспаренных местах.
  В заголовках снимаются только ПАРНЫЕ выделения (содержимое остаётся,
  оформление даёт стиль), одиночные маркеры сохраняются («Define*Style»
  не портится); счётчик — снятые спаны.
* Картинки: строка-только-картинка → абзац роли img; относительный
  `images/<имя>` — как есть; абсолютный путь → базовое имя + поиск в
  `images/` рядом с выходом (`--images-dir` переопределяет), предупреждение
  «файл не найден: <путь>» при отсутствии, в метке `images/<базовое имя>`
  (правило s11.5); относительный путь вне `images/` — как есть +
  предупреждение; смешанная строка (текст+картинка) режется на блоки
  text/img/text с предупреждением.
* Таблицы (pipe и ограда ```csv) в I1 НЕ собираются (TBL1/TBL2): строки
  пишутся абзацами роли `table_row`, разделители `|---|` и
  комментарии `<!-- … -->` отбрасываются со счётчиками, ограды отбрасываются
  (ограда не csv — отдельное предупреждение). Выделения `**` внутри строк
  таблиц обрабатываются (в T-I1b 11 bold-спанов в ячейках — см. §9.3).
* Роль `li_n`: номер из md (`1.`/`1)`) **сохраняется текстом** («1. …») —
  нумерацию стилем не задаём (определение li_n пишется без атрибутов
  списка). Маркер `- ` у li снимается.

### s2.3. Отчёт экспорта

`ExportReport` (dataclass + `to_text()`): счётчики по ролям, список
определений, символьные спаны, сущности (всего + по видам), `<br>`,
несбалансированные маркеры, снятые в заголовках, комментарии/разделители/
ограды/строки таблиц/пустые строки, понижение h4–h6, картинки
(всего/найдено/не найдено), смешанные строки, предупреждения. Печатается
CLI в stdout и/или `--report ФАЙЛ`; в I2 ляжет в окно отчёта.

### s2.4. Stylemap

`{version:1, paragraph_styles:{роль→имя}, char_styles:{bold/italic/
bold_italic→имя}}`; load дозаполняет умолчания, битый JSON/не-объект →
`ValueError`, версия ≠1 — предупреждение; save (utf-8, indent 2).
Путь — параметр (в data root попадёт в I2).

### s2.5. Побайтовая регенерация T4b2

T4b2 определяет BoldItalic, хотя в теле он не используется — режим по
умолчанию `char_style_policy='used'` его не пишет. Поэтому регенерация
выполняется с `char_style_policy='all'` (API-флаг; в CLI `--char-styles all`)
и `color_table='gboh'`. Тест T2 фиксирует sha256
`56fe7e6bed37375b36e11c615dd053c92c2bfb3aee57c751c343c2d4563ea196` (2842 байта).

## s3. Автоматические тесты (headless, без GUI)

Скрипт `docs/refactoring/audits/i1_tagged_text_tests.py` (stdlib, запуск
`E:\Dev\python-embed\python.exe -u docs\refactoring\audits\i1_tagged_text_tests.py [STAGE]`),
артефакт прогона: `batch-i1\tests\run-001\i1_tagged_text_tests.out`.
Фикстуры (в git, `docs/refactoring/audits/fixtures/tagged_text/`, ≤ 9 абзацев):
`t4_t4b2_regeneration.md`, `i1_escape_entities.md`, `i1_emphasis.md`,
`i1_lists_tables.md`, `i1_images.md`.

**Результат: 75 passed / 0 failed.** Группы: T1 структура шапки по умолчанию
(11 проверок); T2 регенерация T4b2 побайтово (5); T3 экранирование,
сущности, `<br>`, экранирование значений (7); T4 выделения (8); T5 списки/
таблицы/комментарии/ограды/h4→h3 (10); T6 картинки (10); T7 краевые случаи —
пустой вход, пробельные строки, странные строки, CRLF-вход (7); T8 stylemap
(9); T9 CLI через `python -m modules.tagged_text` (5); T10 политика `used` (3);
T11 режимы ColorTable + ошибка режима (4); T12 ограда не csv (2).

Из тестов выловлены и исправлены: 2× `m.group(1)`→`m.group(m.lastindex)`
(спан-группа в комбинированном матчере), мёртвый блок char_keys, счётчик
несбалансированных маркеров внутри спанов, некорректный подсчёт
неизвестных сущностей, потеря ветки `all`.

## s4. Прогон на реальных md (T-I1a / T-I1b, вне git)

Входы: `samples\md_out\docling\4164e8d8…\Input.md` и
`samples\md_out\PyMuPDF4LLM\pymupdf4llm_gui_x0bf0ve2\Input.md`; выходы и
отчёты — `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i1\out\`
(вне git). Команда: `python -m modules.tagged_text <Input.md> <выход>`
(умолчания: без ColorTable, char-styles used).

| показатель | T-I1a docling | T-I1b PyMuPDF4LLM |
|---|---|---|
| абзацы | h2=6, p=7, img=2, table_row=11 | h1=1, h2=3, h3=2, p=8, table_row=11 |
| символьные спаны | — | bold=11, bold_italic=2 |
| сущности | 1 (`&amp;`) | 0 |
| `<br>` | 0 | 68 |
| снято в заголовках | 0 | 1 (`# **ANTIDOTE…**`) |
| разделители/комментарии отброшены | 2 / 0 | 2 / 0 |
| пустые строки пропущены | 16 | 20 |
| картинки | 2: абсолютные пути → `images/<имя>`, 2 предупреждения «файл не найден» | 0 |

Контрольные сверки: `&amp;` в заголовке «OBJECTIVES & VICTORY» декодирован;
`**_Lion Rampant’s_**` → BoldItalic (правило `**_`), `**Osprey’s**` → Bold;
`<br>` в ячейках → LF; обе строки-разделителя `|---|` отброшены; шапка
без ColorTable; выходы:

* `T-I1a_docling_indefinestyles.txt` — 16 894 байта,
  `8063ef56886e3d00ff5f39785e510c3199df11aa455524e9d2b1d61984eb3e60`;
* `T-I1b_pymupdf4llm_indefinestyles.txt` — 13 466 байт,
  `d5ee36bf12c51bc719703f693bc80a5c2f7cc3dbf8d5d0132e8d1310a5e89261`.

## s5. T4c — варианты шапки (вне git) и инструкция

Тела обоих файлов идентичны T4b2 (изоляция переменной «ColorTable»;
`--char-styles all`):

* `T4c1_i1_header_nocolortable_utf16le_bom.txt` — 2164 байта,
  `6ce18b4676ae6423372fd26b6fc87404b64768f2dea379c3d1dab49f72f90cff` —
  строка 2 БЕЗ ColorTable (будущий дефолт писателя);
* `T4c2_i1_header_minimalcolortable_utf16le_bom.txt` — 2328 байта,
  `f80f814900893465d9cb685ca6ccbe639b2f645179a12aa39e87d89fb3c6a368` —
  ColorTable только Black+Paper (запасной вариант).

Инструкция Дмитрия:
`E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i1\out\ИНСТРУКЦИЯ_ручные_тесты_I1.txt`.
Константа выбора в писателе: `color_table='none'` по умолчанию; при провале
T4c1 (пустые абзацы/окно ошибок) — переключение на `minimal` фиксируется
аддендумом к этому отчёту.

## s6. Упаковщик

`docs/templates/packaging_helper.py`: в список importsmoke добавлен
`modules.tagged_text` (+2 строки — единственное изменение вне нового пакета
и docs). Полная офлайн-сборка
`make_portable_zip.bat E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i1\build`:

* zip `supervertaler-portable_20261107_0759.zip` — **128 401 701 байт**
  (P2.4: 128 387 481; +14 220 ≈ 5 новых .py), **7325 файлов + 529 каталогов**
  (P2.4: 7320+528), **0 `__pycache__`/`.pyc`** (zip-гейт), runtime-шаг 41 с,
  forbidden check CLEAN, dist-info 30 (lock 29 + pip 1);
* importsmoke на сборке: **OK all 12 modules**, в том числе
  `[importsmoke] OK modules.tagged_text` и `OK Supervertaler (1.10.371)`;
* модуль подтверждён в zip: `SupervertalerPortable/modules/tagged_text/` —
  все 5 файлов.

## s7. Защитная батарея («было / стало / причина»)

| проверка | было | стало | причина |
|---|---|---|---|
| AST startup-chain | 874/0 | **874/0** | продукт не тронут |
| pyflakes (canonical scope: Supervertaler.py + modules/**) | 519 | **519** | новый пакет — 0 предупреждений (2 вхождения «tagged_text» в выводе — прежние импорты `modules.tag_manager` в монолите, Supervertaler.py:209) |
| headless-импорты (scope `modules/**` rglob) | 89 ok / 0 fail | **94 ok / 0 fail** | +5 файлов нового пакета (в вариантe со setup.py, как в P2.4: 95/1 — известный fail `setup`[setuptools] без изменений) |
| smoke (канонический 8.13) | 40 SMOKE OK | **40 SMOKE OK (10,3 с), 0 EXC** | — |
| regress `export_simple_txt` | 5a12501f934a589c | **5a12501f934a589c** | — |
| regress `export_docx` | 44828d90090f046d | **44828d90090f046d** | — |
| regress `export_tmx` | c413d56372e69dd9 | **c413d56372e69dd9** | — |
| e2e aggregate (sha256(json.dumps(requests, sort_keys=True))[:16]) | 982e72a247f0a6ac | **982e72a247f0a6ac**, verdict OK | — |
| py_compile CANONICAL (tracked) | 107/0 | **107/0** до коммита; **112/0 после коммита** (+5 .py пакета) | — |
| py_compile REFERENCE (tracked) | 293/0 | **293/0** до коммита; **299/0 после коммита** (+5 пакета, +1 тест-скрипт) | — |
| git diff по продукту | пуст | **пуст** (`docs/templates/packaging_helper.py` +2 — вне продукта) | — |
| About | v1.10.371 | **v1.10.371** (importsmoke) | — |
| монолит Supervertaler.py | 54 643 строки | **54 643** | — |

Артефакты батареи: `refactoring\batch-i1\` (battery.log, headless_i1.out,
chain_i1.out, smoke_i1.log, regress_after_i1.log, e2e_after_i1.log,
llm_e2e_verdict_i1.json, pyflakes_i1_full.txt) — вне git.

## s8. sha256 изменённых/новых файлов (обе формы: блоб LF / рабочая копия)

| файл | до (блоб LF) | до (раб. копия) | стало (блоб LF) | стало (раб. копия) |
|---|---|---|---|---|
| `docs/templates/packaging_helper.py` | `e5db998eeec28d9fe59dfea134d4b60af7ce8f92` | `cce736cc11a1c310929459e158cb3bec41808e47318850ba63de09a0adf61ac4` (P2.4) | `c9e3f6c433782d6b1b35f89a5f776629cc79f50a` | `f7d2d9ca4353f196ec1de547595f629ee2bb50f49f842464dfcc615cfeec4035` |
| `modules/tagged_text/__init__.py` (новый) | — | — | `e423be246a1937b0d3e08af0a019a43c9c81f8c9` | `9cbb1efa54e6770d8a3c717ad46a2034047facdf4256adca6b810f1f23282d81` |
| `modules/tagged_text/mdparse.py` (новый) | — | — | `534caafd3dd7c28759fc0abff7e17714b317c8a4` | `becd8d177da783f3d2519e1ff1c16b95ce929e2d08b405e3f9ef5e5f7a6d86ce` |
| `modules/tagged_text/stylemap.py` (новый) | — | — | `0d0ca9d5b5304c751f5c0a31e54744760e813bb8` | `6b21ed0bde2a257da7752d7adc1d4569c1f9754a7f3d24ced4f7d2850bb1bc12` |
| `modules/tagged_text/writer.py` (новый) | — | — | `8af667a12b32676e8797634e3c748a1a534cf2d6` | `ccec99d7f61bbfeb577233047ec1db52fe40a7246646dec6be1ac86dbcba1af8` |
| `modules/tagged_text/__main__.py` (новый) | — | — | `7a1990e56f546555b785ed56291faca951954030` | `4bfb79f9639616068dd1a578b8dd36250e81f570918aa450a48dfcff1ec3ef49` |
| `docs/refactoring/audits/i1_tagged_text_tests.py` (новый) | — | — | `d8d294bd706672bdc0b1a4c682fcea6e81a9ede5` | `d1dffe2dd6e960814cc533b6c6edc41128f0ae056eed1b4d71e086900659ed9b` |
| `docs/refactoring/audits/fixtures/tagged_text/t4_t4b2_regeneration.md` (новый) | — | — | `69ab48a2783a9dac2df6b4b7e2c41929148687ee` | `7f440321f9894dfe32a2955c31a21ccf4624821d7698d747d76fc27fd352f9bc` |
| `docs/refactoring/audits/fixtures/tagged_text/i1_escape_entities.md` (новый) | — | — | `58bcda2290833e148dba23763afa09a7099e59fb` | `0b70c01f63dc09bd813aa874fc4873c64d98bb41034cf7a17a6b07fdf4046104` |
| `docs/refactoring/audits/fixtures/tagged_text/i1_emphasis.md` (новый) | — | — | `2fa6e8f654d3fe453c645e32ddf15591319728b2` | `9d71719a9f7e070526a3ab80e710d2339b37affe32812539c848c5b81b0cbced` |
| `docs/refactoring/audits/fixtures/tagged_text/i1_lists_tables.md` (новый) | — | — | `682835f22c5a902673df548efcde2ab3eb6205c9` | `938e691794f87d70a08998622615a2ba00a2fcf5c094980f9e95584c5d237962` |
| `docs/refactoring/audits/fixtures/tagged_text/i1_images.md` (новый) | — | — | `accab9fd6313794fad5e9e0e944f55e221200827` | `f98ce8839e706b9f7715aaacecf099d4a586bd9ed1bbc1f88c9fe5aa0ef54e70` |

Примечание: колонки «до/стало (блоб LF)» для `packaging_helper.py` — по
`git ls-tree HEAD` / `git hash-object`; «до (раб. копия)» — фактический файл
HEAD, восстановленный в `batch-i1\packaging_helper_BEFORE.py` (совпадает с
«стало» отчёта P2.4).

## s9. Вопросы координатору

1. **Подчёркивание в значениях тегов.** Промпт: минимум `\ < > : ; , =` и
   скобки; образец GBoH экранирует `\_` в имени ЦВЕТА (`Word\_R0\_G0\_B0`),
   но в именах стилей `\_` ни разу не проверялся. Реализован минимум
   (без `_`) — дефолтное имя `table_row` пишется `table_row`. Если нужен
   образец-консервативный вариант (`table\_row`) — однострочная правка
   `_VALUE_ESCAPE`; тогда желательно подтвердить ручным тестом имя с `_`.
2. **md-обратные слэши в тексте.** `\;` в md-источнике пишется как `\\;`
   (InDesign покажет `\;`), хотя по семантике CommonMark `\;` = `;`.
   md-unescape в I1 не делался (в промпте не указан; в реальных образцах
   слэшей нет). Нужно ли снимать md-экранирование на входе?
3. **`li_n`: номер сохраняется текстом** («1. …») — определение li_n
   пишется без атрибутов нумерации. Верно?
4. **Выделения в table_row обрабатываются** (`**` в ячейках →
   `<CharStyle:Bold>…`; в T-I1b 11 bold-спанов в строках таблиц).
   Альтернатива — писать строки таблиц буквально без CharStyle до TBL1.

## s10. Ручные тесты (Дмитрий)

Все файлы — в `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i1\out\`,
полная инструкция — `ИНСТРУКЦИЯ_ручные_тесты_I1.txt` там же. Каждый тест:
новый документ → «Файл» → «Поместить» (галочка «Показать параметры импорта»,
ничего не менять) → растянуть фрейм.

**Обязательные (4):**

* **T4c1** — шапка БЕЗ ColorTable (будущий дефолт). Ожидание: 0 пустых
  абзацев, стили h1/h2/h3/p/li/img + Bold/Italic/BoldItalic появились,
  жирный/курсив видны, **лишних образцов цвета нет**. Провал: пустые абзацы,
  окно ошибок, лишние цвета.
* **T4c2** — ColorTable только Black+Paper (запасной вариант). Ожидание:
  как T4c1 + в «Образцах» ровно Black и Paper. Провал: как T4c1.
* **T-I1a** (docling) — заголовки приняли стиль h2, «&» в «OBJECTIVES &
  VICTORY» виден как «&», 11 строк таблиц абзацами с «|», две метки
  картинок с путями `images/<имя>`, окна ошибок нет. Провал: «&amp;» в
  заголовке, окно ошибок, кракозябры.
* **T-I1b** (PyMuPDF4LLM) — «ANTIDOTE TO THE ENGLISH» стиль h1 без
  звёздочек; «FRANCO-SCOTS»/«RULE TWEAK» и т. п. в таблицах жирным;
  «Lion Rampant’s» жирным курсивом, «Osprey’s» жирным; переносы внутри
  ячеек видны (вместо `<br>`). Провал: звёздочки видны как текст, окно
  ошибок.

**Необязательные / покрыто пробами:** сравнение с T4b2 (i0-файл),
кодировка/BOM/CRLF, экранирование и краевые случаи — покрыто 75 headless-
проверками; повторять вручную не нужно.

Если T4c1 провалится (пустые абзацы/ошибки) — T4c2 станет дефолтом писателя
(правка одной константы), фиксируется аддендумом.

## s11. Метод

py_compile после каждой правки; правки только содержимо-привязанные;
реестр и переводы не тронуты; тестовые прогоны — офскрин не требовался
(пакет без GUI); временные артефакты —
`E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i1\`
(tests\run-001, out, build, p1b — до завершения ручной фазы не чистить);
сборка упаковщика — в `batch-i1\build` (не D:\Supervertaler_clean);
пуша нет — стоп до вердикта.
