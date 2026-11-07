# ОТЧЁТ BATCH I2 — экспорт в InDesign Tagged Text из программы (пункт меню + окно «роль → имя стиля»)

Дата: 2026-11-07. Исполнитель: агент (ZCode). Координатор: Дмитрий.
Промпт: `docs/refactoring/prompts/Promt - BATCH I2.txt`. Пуша нет — ждём вердикт.

## s0. Итог

Реализовано: **Project → Export → «InDesign Tagged Text (TXT)...»** (рядом с
«Simple Text File - Translated (TXT)...»): выбор файла (`<проект>.tagged.txt`)
→ окно соответствий «роль → имя стиля InDesign» → запись UTF-16LE+BOM (CRLF)
→ окно отчёта (`ExportReport.to_text()` + «Копировать»).

Источник текста — **тот же, что у export_simple_txt**: сбор строк вынесен в
общий хелпер `SupervertalerQt._collect_translated_lines` (groupby
paragraph_id + `join_segments`); поведение и regress-хэш export_simple_txt
**не изменились** (5a12501f934a589c, батарея I2). Правило пустого перевода —
как у соседа: 0 переводов → предупреждение «No Translations» и отмена;
непереведённые сегменты — исходник (радио в окне экспорта, дефолт) или пусто.

Окно соответствий — новый модуль `modules/tagged_text_export_dialog.py`
(`TaggedTextExportDialog`, по образцу `segmentation_rules_widget.py`):
таблица 8 абзацных ролей (h1, h2, h3, p, li, li_n, img, table_row) +
3 символьных (Bold, Italic, BoldItalic) с колонкой пояснений; имя стиля —
непустая строка (проверка при принятии); подсказка «Group:Style» для группы
стилей (писатель экранирует «:» — I1.1); «Сбросить»; серия (набор
соответствий) с выбором из имеющихся и кнопками Load/Save; папка images
(только проверка «найдено/не найдено», копирование картинок — НЕ в этом
батче). Серии хранятся в `<data_root>\mapping\<серия>.tagmap.json`
(формат `modules/tagged_text/stylemap.py`), путь — через seam
(`get_user_data_path()` → `modules.portable_paths`); последние серия и папка
images — в settings.json (ключи `tagged_text_last_series`,
`tagged_text_last_images_dir`, по образцу `segmentation_rules` /
`last_import_*`). Ничего вне data root, реестр не тронут.

В пакете `modules/tagged_text` — малая правка по п.3 промпта: **номера строк
md в предупреждениях** (смешанная строка, ограда не csv, картинки не найдены,
не разобрана метка): `Block.line`, `enumerate` в `parse_markdown`,
суффикс « (строка N)». Выходные байты не меняются — регенерации T4b2/T4c2
байт-точны, I1-сьют 94/0.

Упаковка: `docs/templates/packaging_helper.py` +2 строки (importsmoke +
`modules.tagged_text_export_dialog`), пересборка офлайн-дистрибутива:
`supervertaler-portable_20261107_1256.zip`, 7326 файлов (+1 новый модуль),
**0 `__pycache__`**, importsmoke **13/13 OK**.

## s1. Факты ШАГА 0 (разведка, до правок)

**(а) export_simple_txt (Supervertaler.py:29923 в HEAD).** Сборка текста:
`groupby(segments, key=paragraph_id)` → на сегмент `target`, если
`target.strip()`, иначе `source` (радио «use source», дефолт) или `""`;
части `(text, join_before)` → `modules.simple_segmenter.join_segments`
(пустые тексты пропускаются → пустая строка на пустой абзац). До диалога —
страж: нет проекта/сегментов → «No Project»; `translated_count == 0` →
«No Translations» и отмена. Диалог: радио непереведённых + кодировка;
запись `line + '\n'`.

**(б) Путь исходного md.** `project.original_txt_path` (ставится при импорте,
Supervertaler.py:29775; дублируется `self.current_document_path`). Имя по
умолчанию — из его базового имени, иначе `project.name`; папка по умолчанию —
`_project_export_path()` → `target/` проекта (#228), при несохранённом
проекте голое имя → Qt открывает последнюю папку. Папка images по умолчанию —
каталог исходного md.

**(в) Data root и прецедент.** `get_user_data_path()` (Supervertaler.py:148)
→ `modules.portable_paths.data_root()`: env `SUPERVERTALER_DATA_ROOT` (_abs)
→ `<env>\Supervertaler` → dev-флаг `.supervertaler.local` → `<build
root>\Supervertaler`. Прецедент `segmentation_rules`: SETTINGS_KEY в модуле,
монолитные колбэки `_load_segmentation_rules`/`_save_segmentation_rules` через
`load_general_settings()`/`save_general_settings()` (единый
`<data_root>\settings.json`, секция general). Взято как образец: ключи
`tagged_text_last_series` / `tagged_text_last_images_dir`; файлы серий —
через `stylemap.load/save` (save сам создаёт каталог).

**(г) Соседние пункты меню.** `file_menu = menubar.addMenu(self.tr("&Project"))`
(7634), `export_menu = file_menu.addMenu(self.tr("&Export"))`; сосед —
`QAction(self.tr("Simple &Text File - Translated (TXT)..."), self)` +
`setToolTip(self.tr(...))`. Новая строка — по тому же правилу:
`self.tr("InDesign &Tagged Text (TXT)...")` + tooltip. XLIFF-файлы
(translations/) не перегенерировались (см. s4, вопрос Q2).

**(д) Готовой функции «текст проекта → md-строки» нет** — логика инлайн в
export_simple_txt. Вынесен ТОЛЬКО общий хелпер (см. s2), больше ничего.

## s2. Изменения кода

**Supervertaler.py (54643 → 54814 строк, +171)** — 4 зоны диффа (проверено
diff-ом со снапшотом до правок):
1. Меню (сразу после export_txt_action): QAction + tooltip + connect,
   +10 строк.
2. `def _collect_translated_lines(self, segments, use_source_fallback)` —
   тело бывшего инлайн-блока export_simple_txt, +25 строк.
3. export_simple_txt: инлайн-блок (18 строк) → вызов хелпера (3 строки).
   Поведение байт-в-байт то же (regress-хэш 5a12501f934a589c).
4. `def export_tagged_txt(self)` + `def _show_tagged_text_report(...)`,
   +152 строки: стражи (No Project / No Translations — как у соседа) →
   QFileDialog (имя `<проект>.tagged.txt`, через `_project_export_path`,
   фильтр InDesign Tagged Text) → окно соответствий (начальная карта —
   последняя серия из settings.json, если файл есть; предупреждения
   stylemap.load — в лог) → `_collect_translated_lines` →
   `modules.tagged_text.writer.write_tagged_text(md_text, style_map=...,
   images_dir=...)` → запись байтов → persist настроек → лог → окно отчёта
   (QPlainTextEdit + «Копировать» в буфер + «Close»).

**modules/tagged_text_export_dialog.py (новый, 260 строк)** —
`TaggedTextExportDialog(QDialog)`: таблица 11×3 (роль — только чтение; имя
стиля — правка; пояснение — только чтение), «Сбросить», серия (QLineEdit +
QComboBox имеющихся + Load/Save), папка images (QLineEdit + Browse), радио
непереведённых (как у соседа), валидация непустых имён стилей при «Export»;
`style_map()`, `images_dir()`, `series_name()`, `use_source_fallback()`.
Имя серии: запрещены `\ / : * ? " < > |`, ведущая точка; `list_series()`
читает `*.tagmap.json` в переданном `maps_dir` (отсутствие каталога — не
ошибка). Строки — `self.tr(...)`, интерполированные тела QMessageBox —
английские (Tier 2 по TRANSLATING.md).

**modules/tagged_text/mdparse.py** — `Block.line: int = 0`; `enumerate` по
строкам; предупреждения «ограда не csv» и «смешанная строка» получают
«(строка N)»; `_split_mixed_image(text, stats, lineno)`.

**modules/tagged_text/writer.py** — `_line_suffix()`; предупреждения о
картинках («не удалось разобрать метку», «файл не найден», «относительный
путь вне images/») получают « (строка N)» из `b.line`. Байты выхода не
меняются.

**docs/templates/packaging_helper.py** — +2 строки: importsmoke-список +
`modules.tagged_text_export_dialog`.

## s3. Решения исполнителя (в границах промпта)

- Порядок потока — как в цели промпта: файл → окно соответствий → запись →
  отчёт. Радио непереведённых помещено в окно соответствий (группа
  «Untranslated Segments», как у соседа), чтобы сохранить правило шага 0а
  без лишнего диалога.
- «Последняя серия и папка» в settings.json интерпретированы как серия +
  папка images; при следующем открытии окна images-поле по умолчанию = последнее
  сохранённое значение, иначе каталог исходного md (шаг 0б), иначе пусто (Q1).
- Пустое поле images → `images_dir=None` в writer (поиск не выполняется,
  абсолютные пути дадут «файл не найден») — «иначе пусто» без сюрпризов.
- Серия из settings.json загружается в окно как начальная карта (если файл
  существует; сбой чтения → лог + карта по умолчанию).

## s4. Тесты

**I1-сьют пакета: 94/0** (i1_tagged_text_tests.py, без правок файла) —
включая байт-точные регенерации T4b2/T4c2: правка номеров строк не меняет
выходные байты.

**I2-сьют: 32/0** (`batch-i2/tests/run-003/i2_export_tests.py`, offscreen,
модалки подменены; копия пойдёт в git как
`docs/refactoring/audits/i2_tagged_text_export_tests.py`):
- A1–A17 диалог: 11 строк таблицы, дефолты, правки ↔ `style_map()`, Сброс,
  валидация пустого имени (не принято + предупреждение), валидация имён серий
  (`\ / : * ? " < > |`, ведущая точка — ошибка; «Моя серия 2» — ок), Save →
  `<data_root>\mapping\Test2.tagmap.json`, кругосветка карты, выбор серии из
  комбобокса загружает карту в таблицу, чистая установка (несуществующий
  maps_dir) — диалог открывается, доступы images/series/use_source_fallback.
- B0–B13 хендлер на полном приложении: пункт меню существует; нет проекта →
  «No Project»; импорт md (docling) → путь исходника сохранён → цели =
  источникам (правило шага 0а) → экспорт: окно соответствий и окно отчёта
  открыты, файл UTF-16LE+BOM, **байт-в-байт равен CLI-выходу**
  `python -m modules.tagged_text` того же md (B5); ключи
  `tagged_text_last_*` в settings.json; папка mapping только внутри data root
  (B6/B6b); серия MyMap из settings.json применяется в GUI: экспорт
  pymupdf4llm **байт-в-байт равен CLI с `--map MyMap.tagmap.json`** (B9) и
  содержит `<ParaStyle:Глава>` / `<DefineParaStyle:Глава=` (B10); 0 переводов
  → «No Translations», файл не создаётся (B11); список серий пополняется (B12);
  last_series сохраняется (B13).
- Реальные md: `samples\md_out\docling\4164e8d8…\Input.md` и
  `samples\md_out\PyMuPDF4LLM\pymupdf4llm_gui_x0bf0ve2\Input.md` (вне git).
  Замечание: первый прогон (run-002) дал «FAIL B9» — CLI шёл с картой по
  умолчанию, а GUI с серией MyMap; это корректное поведение фичи, тест
  переведён на CLI с той же картой (run-003: 32/0).

**Защитная батарея I2** (`batch-i2/run_battery.sh`, артефакты
`batch-i2/p1b/`, файлы headless/chain/smoke в stage названы `*_i1.*` — sed
копии I1 не правил суффиксы имён, содержимое — прогон I2):

| Метрика | Было (I1.1) | Стало (I2) | Причина изменения |
|---|---|---|---|
| AST startup-chain | 874/0 | **876/0** | +2 разрешённых вызова: новый блок меню (addAction + triggered.connect); неразрешённых нет |
| pyflakes (канон. scope) | 519 (файлов 95) | **519 (файлов 96)** | новый модуль — 0 предупреждений; 2 вхождения «tagged_text» — прежние |
| py_compile CANONICAL | 112/0 | **113/0** | +1 новый tracked .py (dialog-модуль) |
| py_compile REFERENCE | 299/0 | **300/0** | тот же +1 |
| headless imports | 94/0 | **95/0** | скрипт rglob-ит modules/**/*.py — автонаходка нового модуля |
| smoke (канон. 8.13) | 40 OK | **40 OK** (10,2 с) | — |
| regress export_simple_txt | 5a12501f934a589c | **5a12501f934a589c** | хелпер не меняет байты |
| regress export_docx | 44828d90090f046d | **44828d90090f046d** | — |
| regress export_tmx | c413d56372e69dd9 | **c413d56372e69dd9** | — |
| e2e aggregate | 982e72a247f0a6ac | **982e72a247f0a6ac**, verdict OK | — |
| Монолит | 54 643 | **54 814** | +171: см. s2 п. Supervertaler.py |
| About | v1.10.371 | **v1.10.371** (pyproject.toml не тронут) | — |

Реестр: новый код не содержит QSettings/winreg (grep 0 вхождений в новом
модуле); QSettings приложения по-прежнему redirected в
`<data_root>/qsettings` (Supervertaler.py:54467, не тронуто); headless-прогоны
идут с изолированным профилем и seam.

Упаковка: см. s0. Артефакт сборки:
`E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i2\build_i2.log`.

Остаточные процессы после GUI-прогонов: перечислены по командным строкам —
python.exe/java.exe от батча отсутствуют (sidecar не поднимался: «not
installed yet» в изолированных профилях).

## s5. sha256 (обе формы: рабочая копия CRLF / блоб LF)

| Файл | до (CRLF / LF) | стало (CRLF / LF) |
|---|---|---|
| Supervertaler.py | `d493b499…b95d40` / `72db449a…27984d3` | `ae0f9453…0c74d5` / `39501571…f512be` |
| modules/tagged_text/mdparse.py | `becd8d17…6d86ce` / `becd8d17…6d86ce` | `a0b552c4…fc874497` (CRLF=LF) |
| modules/tagged_text/writer.py | `f8ddda0e…16328bb` / `f8ddda0e…16328bb` | `4215b2ce…6f1821` (CRLF=LF) |
| docs/templates/packaging_helper.py | `f7d2d9ca…eec4035` (LF) | `2eb41429…61bbfd4` (CRLF=LF) |
| modules/tagged_text_export_dialog.py | — | `08817022…35c75b` (CRLF=LF) |
| modules/tagged_text/{__init__,__main__,stylemap}.py | не менялись (см. снапшоты `batch-i2/snapshots/`) | идентичны «до» |

Полные значения — в журнале батча; CRLF рабочей копии Supervertaler.py
восстанавливается git-ом при checkout (LF-блоб — основная форма сравнения).

## s6. Ручные тесты (Дмитрий) — T-I2, на D:\Supervertaler_clean

Пересобрать дистрибутив: свежий zip уже собран
(`supervertaler-portable_20261107_1256.zip`, байт-идентичное содержимое кода);
распаковать в D:\Supervertaler_clean по обычной процедуре (решение о
пересборке — за координатором).

**Обязательные (3):**

**T-I2a. Экспорт по умолчанию → Place в InDesign без стилей.**
1. Цель: экспорт перевода в Tagged Text из программы.
2. Запустить D:\Supervertaler_clean\start.bat. Project → Import → импортировать
   `Input.md` (тестовый файл: `E:\Dev\Work_temp\SupervertalerPortable\samples\md_out\docling\4164e8d8…\Input.md`;
   галку «Split lines into sentences» не ставить). Перевести несколько строк
   (или целиком через любой профиль), Project → Export → InDesign Tagged Text
   (TXT)… → сохранить как `<имя>.tagged.txt`.
3. В окне «Export InDesign Tagged Text» не менять имена, нажать Export.
   В окне отчёта нажать «Копировать» и посмотреть текст.
4. Ожидаемо: в InDesign File → Place этого TXT — 0 пустых абзацев перед
   текстом; абзацы получили стили с именами h1/h2/h3/p/li/li_n/img/table_row
   (несуществующие стили InDesign создаёт сам, вид — по умолчанию); **bold**
   фрагменты — символьным стилем Bold.
5. Неуспех: пустые абзацы перед текстом, отсутствующий файл, ошибка при Place.

**T-I2b. Свои имена стилей и группа.**
1. Цель: карта «роль → имя стиля» применяется и с именами групп.
2. В документе InDesign заранее создать стили «Глава 1» (абзацный) и
   «Красный:Жирный» (символьный, в группе «Красный»).
3. Повторить экспорт; в окне заменить «h1» → «Глава 1», «Bold» →
   «Красный:Жирный»; Export.
4. Ожидаемо: заголовки h1 получили стиль «Глава 1», жирные фрагменты —
   «Красный:Жирный» (InDesign разрешает имя группы через «:»).
5. Неуспех: стили не применились, InDesign ругается на имена в логе.

**T-I2c. Серия переживает перезапуск.**
1. Цель: набор соответствий сохраняется и подхватывается.
2. В окне экспорта ввести имя серии «MyBook», нажать Save, затем Export.
   Закрыть программу, запустить снова, повторить экспорт.
3. Ожидаемо: окно открылось с серией «MyBook» и именами из неё; файл
   `Supervertaler\mapping\MyBook.tagmap.json` существует в папке сборки.
4. Неуспех: серия потерялась, файл не создан, окно пустое.

**Необязательные:**
- T-I2d. Проект без картинок: в отчёте «Картинки: всего 0 …»; с картинками
  (md из docling-сэмпла) — «найдено/не найдено» по папке images; при пустом
  поле images абсолютные пути дают «не найден» с номером строки.
- T-I2e. Экспорт без переводов: предупреждение «No Translations», файл не
  создаётся (то же правило, что у Simple Text File).

## s7. Вопросы координатору

- **Q1. «Последняя серия и папка»** в settings.json — реализовано как
  серия + папка images (сохраняются после успешного экспорта; images-поле при
  следующем открытии = последнее значение, иначе каталог md, иначе пусто).
  Если «папка» означала папку сохранения TXT — Qt помнит её сам для голого
  имени файла; перенесу ключ по вердикту.
- **Q2. XLF-шаблон** (translations/*.xlf) не перегенерирован: новые
  `self.tr`-строки войдут при следующем запуске
  `tools/extract_strings.py` + `tools/merge_template.py`. Делать ли это в
  рамках I2-вердикта или отдельным шагом?
- **Q3. 0-переводов → отмена** сохранено как у соседа (иначе правило
  «как там» нарушается). Альтернатива — разрешать экспорт только исходника;
  по умолчанию оставил поведение соседа.
- **Q4. Байт-сравнение B9** переведено на «CLI с той же картой» (run-002
  показал, что GUI честно применяет серию — см. s4). Считать ли нужным
  отдельный кейс «GUI без серии == CLI без карты» — он уже покрыт B5
  (docling, дефолтная карта).

## s8. Артефакты и метод

- Вне git (stage): `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-i2\`
  (snapshots/ — снапшоты до правок; tests/run-001..003 — логи I2-сьютов;
  p1b/ — батарея; out/ — выходы GUI-экспорта и CLI; build_i2.log).
- В git: отчёт (этот файл), промпт, `docs/refactoring/audits/i2_tagged_text_export_tests.py`
  (копия сьюта), PROJECT_STATUS.md, код (s2).
- Метод: правки Edit-инструментами; py_compile после каждой зоны; снапшоты до
  правок с sha256; дифф-контроль зон; headless с `-u` в stage-каталог;
  подмена модалок по образцу `batch-p1b_batch8-15_regress_common.py`;
  пересборка zip — `make_portable_zip.bat` (self-verifying).
