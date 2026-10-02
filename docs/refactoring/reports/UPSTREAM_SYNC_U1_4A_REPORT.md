# Upstream-sync U1.4a — сегментация: ядро (без страницы настроек)

Батч: U1.4a. Исполнитель: Zcode. Дата: 2026-10-02.
Апстрим-коммит: **763291e8** «Segmentation Rules: user-definable SRX-style rules, and a segmenter that never drops text (#191)» из диапазона v1.10.371 → v1.10.372 (тег-цель `a5857227`). Общей git-истории нет, сравнения тег-к-тегу.
Объём: **только ядро** — самостоятельные модули сегментации + перевод всех вызывающих мест монолита на новый API с правилами **по умолчанию**. Страница настроек «Segmentation Rules» (`segmentation_rules_widget.py`, `create_segmentation_rules_tab`, `_save_segmentation_rules`) — U1.4b, НЕ перенесена.

## 0. Baseline и git-синхронизация

- HEAD = `ed4587e1` = `origin/main`, рабочее дерево чистое (кроме служебного `.zcode/plans/*`).
- `git fetch origin`, `git fetch upstream --tags` — без ошибок.
- Дрейф-чек: `git merge-base --is-ancestor 2e258269 HEAD` — истина (последний кодовый коммит U1.3b в истории; HEAD опережает только docs-коммитами `34512e70`, `ed4587e1`, не трогающими файлы батча).
- `git rev-parse v1.10.372^{commit}` = `a58572276b4fced9384cf64580237c9edee75007` ✔; `git cat-file -t 763291e8` = commit ✔; 763291e8 — предок v1.10.372 ✔.
- Baseline: `Supervertaler.py` 68 397 строк, SHA256 `e2ee4966…`; py_compile монолита + 135 модулей = 136/136 OK.

## 1. Аудит 763291e8

### 1.1 Что делает коммит

Сегментер перестроен на **позициях разрывов**: сегменты — всегда срезы входного текста, символы не теряются. `segment_with_separators()` возвращает для каждого сегмента предшествующий пробел (`join_before`), что даёт точный обратный экспорт (кастомное правило может резать без пробела). В коммите ОБА заявленных исправления (проверено по диффу):

- **(а) потеря первого слова**: «Dr. Smith works here.» больше не теряет «Dr.» — старый код вырезал аббревиатуру; новый строит сегменты срезами (в headless-прогоне §4 дефект «до» воспроизведён, «после» исправлен);
- **(б) Markdown `\x00MD0\x00`**: восстановление плейсхолдеров переведено на «новые — первыми» (`reversed(list(placeholders.items()))` — строка в `MarkdownSegmenter.segment_with_separators`; в родителе `763291e8^` — прямой порядок, утечка воспроизведена в §4). Оба исправления лежат в 763291e8, посторонних коммитов для (б) не требуется.

### 1.2 Файлы коммита и решения

| Файл | В 371? | Коммиты диапазона, трогающие файл | Blob Portable vs 371 | Решение |
|---|---|---|---|---|
| `modules/simple_segmenter.py` | да | только 763291e8 | идентичен 371 | **ЦЕЛИКОМ из тега** |
| `modules/segmentation_rules.py` | нет (новый) | только 763291e8 | — | **ЦЕЛИКОМ из тега** (движок правил; stdlib-only, зависимостей от монолита нет — AST-проверка) |
| `modules/segment_split_merge.py` | да | 34a4c661 (#173, **класс D, отложен**), 763291e8 | идентичен 371 | **только дельта 763291e8** (diff `34a4c661..763291e8`); патч ложится на 371-состояние с ровным офсетом −22 (отсутствующие строки 34a4c661 в другом месте файла) — `git apply --check` OK, применён (+18/−2 — точно как в апстриме) |
| `modules/segmentation_rules_widget.py` | нет | только 763291e8 | — | **НЕ копировать** (U1.4b) |
| `tests/test_segmentation_rules.py` | нет | только 763291e8 | — | в репо НЕ добавлялся; запущен из repo-sim (§4) |
| `CHANGELOG.md` | нет | — | — | в Portable отсутствует, скип |
| `Supervertaler.py` | да | 24 коммита диапазона | отличается | вручную, по именам методов (§1.4) |

Правило «идентичен 371 И трогает только 763291e8 → целиком» для `segment_split_merge.py` нарушено вторым коммитом 34a4c661, поэтому файл перенесён дельтой; результат сверён с полным состоянием 763291e8: отличаются ТОЛЬКО отсутствием добавлений 34a4c661 (`split_source_text` + `Callable` в typing) — проверено diff'ом против `763291e8:modules/segment_split_merge.py`.

### 1.3 API-дифф `simple_segmenter.py` (AST, Portable@HEAD vs v1.10.372)

| Категория | Имена |
|---|---|
| Удалено (внешнее API) | ничего (модульные внутренности `_is_abbreviation_only`, `_merge_abbreviation_splits` удалены — внешних вызовов не было, инвентарь §1.4) |
| Изменено | `SimpleSegmenter.__init__(self)` → `(self, rules=None)` (старый вызов без аргументов валиден); `MarkdownSegmenter`: `segment_text` → `segment_with_separators` (переопределение; унаследованный `segment_text` сохранён) |
| Добавлено | модульная `join_segments(parts)`; `SimpleSegmenter.segment_with_separators`, `_split_line`, `_settle`, `_builtin_positions` |

Совместимость: `segment_text(text)` и `segment_paragraphs(paragraphs)` сохранены с прежними сигнатурами и семантикой «список строк».

### 1.4 Полный инвентарь использований (AST + строки, монолит и все modules/**)

| Место (Portable, AST) | Что вызывает | Затронуто API | Фича Batch #8? | Действие |
|---|---|---|---|---|
| `new_project` @29290: локальный импорт @29296 + `SimpleSegmenter()` @29508 | `segment_text` | да | нет | хунки #4/#5: импорт убран, `_make_sentence_segmenter()` |
| `import_simple_txt` @33380: 2 ветки (осн. + retry-кодировки), тултип | `MarkdownSegmenter/SimpleSegmenter`, `segment_text` | да | нет | хунки #6–#10: `_make_sentence_segmenter(markdown=…)`, `segment_with_separators` + `join_before`, тултип |
| `export_simple_txt` @33754: сборка строк | `' '.join` | да | нет | хунк #11: `join_segments` + `join_before` |
| `import_folder_multifile` @34293: тултип | — | нет | нет | хунк #12: текст тултипа |
| `_import_multifile_project` @34451: lazy `self.segmenter` @34491, создание, цикл | `SimpleSegmenter`, `segment_text` | да | нет | хунки #13–#15: lazy-init убран, `_make_sentence_segmenter`, `segment_with_separators` + `join_before` |
| `_export_file_as_txt` @35204: сборка строк | `' '.join` | да | нет | хунк #16: `join_segments` + `join_before` |
| `create_segmentation_rules_tab` @15307 + `test_segmentation_rules` @15397 (старая страница-заглушка) | `SimpleSegmenter().segment_paragraphs` | нет (API сохранён) | нет | **оставлены без изменений** (страница U1.4b); совместимы с новым сегментером |
| `Segment` dataclass | поле | — | нет | хунк #1: `join_before` → `modules/models.py` (см. §1.7) |
| `modules/config_manager.py:43` | строка `'resources/segmentation_rules'` | нет | — | ложное совпадение, не тронуто |
| `modules/database_manager.py:790` | legacy-таблица `segmentation_rules` (только DDL, чтения/записи в коде нет) | нет | — | не тронуто (763291e8 schema не меняет) |
| `modules/okapi_sidecar.py:574` | SRX Okapi-движка | нет | — | ложное совпадение |
| `Supervertaler.py:55511/55537/55546` | имя метода `_replace_current_target_segment_text` / локальная переменная `segment_text` | нет | — | ложные совпадения подстроки |
| upstream hunk #2 (`add_source_text_to_project`, 34a4c661) | — | — | — | **метод в Portable отсутствует** (фича #173 отложена) → хунк скипнут, вне объёма |

После правок инвентарь повторён: все ссылки монолита резолвятся в новый API (`_make_sentence_segmenter` ×4, `segment_with_separators` ×3, `join_segments` ×2+2 импорта); вызовов удалённых внутреннихностей нет.

### 1.5 Совместимость остальных потребителей

Единственные потребители старого API — методы из §1.4, все покрыты переносом (хунки #4–#16). Потребителей старого API вне 763291e8, которые сломались бы, не найдено. `self.segmenter` после удаления lazy-init на монолит больше никем не читается (grep: 1 совпадение до правки, 0 после).

### 1.6 Существующая страница сегментации

`create_segmentation_rules_tab` (@15307, Portable) — заглушка: текст «Current Implementation: SimpleSegmenter…», кнопка «🧪 Test Segmentation» → `test_segmentation_rules` → `QInputDialog.getMultiLineText` + `SimpleSegmenter().segment_paragraphs` (AST-сверка с `763291e8^`: идентична, docstrings в стороне). Настройки не читает и не пишет. С новым модулем совместима (API сохранён), исключений не будет — покрывается сценарием T4.7.

### 1.7 Оценка U1.4b (страница настроек)

- `segmentation_rules_widget.py` — 380 строк, ЦЕЛИКОМ из тега (новый файл, трогает только 763291e8).
- Хунки монолита: замена `create_segmentation_rules_tab` на 4-строчную фабрику виджета + `_save_segmentation_rules` (6 строк). `_load_segmentation_rules` (7 строк) **уже перенесена в U1.4a**, т.к. нужна ядру (`_make_sentence_segmenter` → `_load_segmentation_rules`).
- Ключ настроек: `SETTINGS_KEY = "segmentation_rules"` (`modules/segmentation_rules.py:34`), хранится в general settings (`self.load_general_settings()` / `save_general_settings(settings)` — оба есть в Portable: `Supervertaler.py:44608/44977`, перенесены в U1.2).
- Поведение при отсутствии ключа: `_load_segmentation_rules` → `.get(SETTINGS_KEY)` → `None` → `SegmentationRules.from_dict(None)` → **правила по умолчанию** (from_dict: `data if isinstance(data, dict) else {}`; headless §4(г) подтверждает). Вызов `save_general_settings` без проверки результата есть только в `_save_segmentation_rules` (U1.4b), getattr/hasattr-обращений к правилам нет, обращений к `main_window.general_settings` напрямую нет.

### 1.8 Безопасность данных

- **Формат сохраняемых данных**: единственное добавление — поле `Segment.join_before: Optional[str] = None` (`modules/models.py`, asdict при сохранении проекта). Изменение аддитивное: `Segment.from_dict` фильтрует неизвестные ключи, старые проекты (без поля) загружаются (default `None`) — проверено headless (§4, п. «dataclass»). БД/DDL не затронуты (763291e8 не трогает database_manager), миграций не требуется.
- **Проекты без разделителей**: экспорт (`join_segments`) при `join_before=None` ставит одиночный пробел (докстринг + код `simple_segmenter.py:159-170`); split/merge читают через `getattr(b, 'join_before', None)` — фолбэк есть, headless split/merge round-trip точен.
- **Настройки**: чтение правил обёрнуто try/except с фолбэком на значения по умолчанию; `None`/отсутствие ключа безопасны (§4(г)).
- **Изменений формата, требующих СТОП, нет.**

## 2. Что сделано

Коммит **`5c052c9d`** «U1.4a upstream-sync: segmenter never drops text, exact plain-text round-trip, rules engine core (from v1.10.372 763291e8, settings page deferred to U1.4b)».

| Апстрим | Файл | Способ |
|---|---|---|
| 763291e8 (файл) | `modules/simple_segmenter.py` | `git checkout v1.10.372 --`; staged blob `eb564a81` == `git rev-parse v1.10.372:modules/simple_segmenter.py` |
| 763291e8 (файл, новый) | `modules/segmentation_rules.py` | то же; blob `f8606a04` == тег |
| 763291e8 (дельта) | `modules/segment_split_merge.py` | `git diff 34a4c661 763291e8 -- <файл>` → `git apply` (после `--check`); офсет −22, +18/−2 |
| 763291e8 (дельта, метод из монолита апстрима) | `modules/models.py` | вручную: `join_before: Optional[str] = None` после `category` (Portable-расположение dataclass `Segment`) |
| 763291e8 (хунки #4,#5) | `Supervertaler.py::new_project` | вручную |
| 763291e8 (часть хунка #3) | `Supervertaler.py::` +`_load_segmentation_rules`, +`_make_sentence_segmenter` | вручную, после `test_segmentation_rules` |
| 763291e8 (хунки #6–#10) | `Supervertaler.py::import_simple_txt` | вручную |
| 763291e8 (хунк #11) | `Supervertaler.py::export_simple_txt` | вручную |
| 763291e8 (хунк #12) | `Supervertaler.py::import_folder_multifile` | вручную |
| 763291e8 (хунки #13–#15) | `Supervertaler.py::_import_multifile_project` | вручную |
| 763291e8 (хунк #16) | `Supervertaler.py::_export_file_as_txt` | вручную |
| 763291e8 (хунк #3: фабрика виджета, `_save_segmentation_rules`) | — | **не перенесено** (U1.4b) |
| 763291e8 (хунк #2: `add_source_text_to_project`) | — | **не перенесено** (фича #173/34a4c661 отложена, метода-якоря нет) |

Отклонение от списка файлов коммита, задокументированное: `modules/models.py` (в апстриме правка dataclass входит в `Supervertaler.py`) — поле dataclass `Segment` в Portable живёт в models.py после экстракции предыдущими батчами. Перенос однозначный.

## 3. Диффы методов монолита до/после

AST-сверка против `763291e8:Supervertaler.py` (после правок): `new_project`, `import_simple_txt`, `export_simple_txt`, `import_folder_multifile`, `_import_multifile_project`, `_load_segmentation_rules`, `_make_sentence_segmenter` — **MATCH-372** (docstrings в стороне); `_export_file_as_txt` — отличается ТОЛЬКО двумя переведёнными docstring (внешним и вложенного `strip_tags`), известное осознанное отличие Portable. Побайтовая сверка строк методов (difflib по сырому тексту): все различия — только docstring (RU-переводы), различий кода и whitespace-only строк нет.

`create_segmentation_rules_tab`, `test_segmentation_rules` — сверены с `763291e8^` и оставлены без изменений (KEPT-OLD).

Регресс-guard из U1.2: no-arg `save_general_settings()` — 0 вызовов.

## 4. Статическая и headless-валидация

| Проверка | Результат |
|---|---|
| py_compile монолита + 136 модулей (стало 137 файлов) | OK (было 136/136, стало 137/137: +segmentation_rules.py) |
| `git diff --stat` — только ожидаемые файлы | Supervertaler.py 95±, models.py +1, segment_split_merge.py 20±, segmentation_rules.py +285, simple_segmenter.py 216± |
| EOL (`git ls-files --eol`) до/после | все 5 файлов `i/lf w/lf` — не изменились |
| staged blobs «ЦЕЛИКОМ»-файлов == тег | `eb564a81`, `f8606a04` == `v1.10.372:…` |
| AST-сигнатуры ЦЕЛИКОМ-модулей == 372 | blob-идентичность делает сверку избыточной; api_diff-скрипт подтвердил таблицу §1.3 |
| Тесты апстрима `tests/test_segmentation_rules.py` (12 шт., из repo-sim вне репо, junction `modules`) | **12 passed** |
| Инвентарь использований после правок | все вызовы резолвятся, старых внутреннихностей нет |

### Headless «до/после» (без Qt; before = модули из HEAD, after = рабочий репозиторий, один скрипт; результаты `headless/before.json`, `headless/after.json`)

(а) **Свойство без потерь** (посегментная склейка `separator+segment` == `line.strip()` побайтно; «до» — старый экспортный путь `' '.join`):

| Случай | До | После |
|---|---|---|
| `Dr. Smith went home. He slept.` | **VIOLATED** — потерян «Dr.» (`'Smith went home.'`) | LOSSLESS — `'Dr. Smith went home.'` |
| `Mr. Jones walked to St. Mary's church…` | **VIOLATED** — потерян «Mr.» | LOSSLESS |
| `J. R. R. Tolkien wrote the book…` | LOSSLESS | LOSSLESS |
| `e.g./i.e./etc.` | LOSSLESS | LOSSLESS |
| `What about this... Really?! Yes.` | **VIOLATED** — `?!` отдельным сегментом, при экспорте теряется | LOSSLESS — `'Really?!'` |
| Диалог с кавычками и тире | LOSSLESS | LOSSLESS |
| Строка только «etc.» | **VIOLATED** — сегментов нет, строка терялась целиком | LOSSLESS — `'etc.'` |
| Числа `3.5`, `1.` | LOSSLESS | LOSSLESS |
| NBSP | LOSSLESS | LOSSLESS |
| Пробелы/табуляция внутри строки | **VIOLATED** — внутренний пробел заменялся на одиночный при экспорте | LOSSLESS — разделители сохранены точно |
| Русский текст | LOSSLESS (1 сегмент) | LOSSLESS (4 сегмента: `Привет, мир!` / `Это второе предложение.` / `Тест Др.` / `Смитов и т.д. работает.`) |

(в) **Markdown** `Read [`code`](https://example.com) first.`: до — сегмент `Read [\x00MD0\x00](https://example.com) first.` (утечка плейсхолдера), после — `Read [`code`](https://example.com) first.`; флаг утечки `before=True → after=False`.

(г) **Фолбэк**: `SegmentationRules.from_dict(None)` и `from_dict({})` → правила по умолчанию (`split_at_line_breaks=False`, `use_builtin_rules=True`, rules=0); `SimpleSegmenter(правила_по_умолчанию)` и `SimpleSegmenter()` работают без исключений. В before-дереве модуля правил нет — old `SimpleSegmenter()` работает как раньше.

**dataclass**: старый JSON без `join_before` → `Segment.from_dict` даёт `join_before=None`; new to_dict/from_dict round-trip сохраняет `" "`. **split/merge**: `split_segment` при разрезе ставит `new.join_before=""`, `merge_with_next` склеивает точно (`'One. Two.'` → split → merge → `'One. Two.'`).

Замечание (не дефект): «Др.» нет в списке аббревиатур по умолчанию — апстримное поведение; пользователь сможет добавить её в U1.4b через «extra abbreviations» (сейчас — через SRX-правила тоже недоступно, страницы нет). Потерь текста это не создаёт.

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: последний кодовый коммит U1.3b **`2e258269`** (+ допускаются docs-коммиты `34512e70`, `ed4587e1` — код не трогают). Заменить поверх сборки файлы, изменённые в U1.4a (`5c052c9d`):

| № | Путь | SHA256 | Примечание |
|---|---|---|---|
| 1 | `Supervertaler.py` | `28b862e80e654c214ab904dc779d0c669c8da972f1e84e444d1c45ce9631f9c6` | 68 392 строки |
| 2 | `modules/models.py` | `cac9259d5b6ea6b60a5b364f3b278cb89742498d7b268e390d87ccf556c66c3a` | +1 строка (`join_before`) |
| 3 | `modules/simple_segmenter.py` | `40863ab167732e9c1a5cd5b1e224a123db29246efeb10952bcdd8f65212080b0` | 268 строк, blob == тег 372 |
| 4 | `modules/segmentation_rules.py` | `34edc6244b0c106575fddb9b831db07b1ac1d297824f62c7eca67789ed44fc4e` | НОВЫЙ файл, 285 строк, blob == тег 372 |
| 5 | `modules/segment_split_merge.py` | `3e8752ad40758331354431762487fc62b99e52dc8e93d0378782e80b9d0eedde` | 291 строка, дельта 763291e8 |

Тестовые данные (созданы вне репо): `D:\Temp\SupervertalerPortable\refactoring\u1-port4\testdata\` — `sample_en.txt` (LF), `sample_crlf.txt` (то же CRLF), `sample.md` (ссылки с inline-кодом), `expected_segments.md` (таблица ожидаемых сегментов, вычислена новым сегментером; 27 сегментов).

## 6. СЦЕНАРИИ ПРОВЕРКИ

Всё на КОПИИ user_data тестовой сборки. Сначала КОНТРОЛЬ на базовой сборке (2e258269), затем после замены файлов из §5.

- **T4.1 (потеря слов)**: Импорт TXT → `sample_en.txt`, «Split lines into sentences» включено. КОНТРОЛЬ (до): воспроизводится потеря «Dr.»/«Mr.», строка «etc.» теряется, «Really?!» режется на «Really»+«?!». После: сегменты соответствуют `expected_segments.md`; ни одно слово не потеряно (включая `Dr.`, `Mr.`, `J. R. R.`, `e.g.`, `3.5`, кириллицу).
- **T4.2 (обратный экспорт)**: импортировать `sample_en.txt` и `sample_crlf.txt`, скопировать source→target во всех сегментах, экспортировать в txt. Результат должен совпасть с исходным файлом побайтно, КРОМЕ: точные пробелы между сегментами восстанавливаются из `join_before` (совпадает), НО пробелы/табуляции, шедшие до/после текста строки, обрезаются импортом (это поведение и до U1.4a), и пустые строки дают пустые строки. CRLF-файл экспортируется с LF (окончания строк нормализуются экспортом — `newline='\n'`, как и было). Если наблюдаются иные отличия — зафиксировать.
- **T4.3 (Markdown)**: импорт `sample.md` — в тексте сегментов НЕТ `\x00MD0\x00`; ссылки вида `[`code`](https://example.com)` читаемы; экспорт markdown сохраняет ссылки (КОНТРОЛЬ до: `\x00MD0\x00` виден в сегменте).
- **T4.4 (без настроек)**: убедиться, что ключа `segmentation_rules` нет в настройках (на свежей копии user_data его нет) → импорт работает на правилах по умолчанию, в консоли нет исключений. Страница Settings → Segmentation Rules остаётся старой заглушкой — это ожидаемо (U1.4b).
- **T4.5 (регрессия других путей)**: те же сегментаторы используют: New Project с вставленным текстом (вкладка «Paste Text»), Import → Import Folder (мультифайловый, TXT/MD с галочкой сегментации), экспорт Export → Simple Text и автоматический txt-экспорт мультифайловых проектов. Открыть каждый и убедиться, что импорт/экспорт проходят как раньше (сегментация — лучше: без потерь).
- **T4.6 (существующий проект)**: открыть проект, созданный ДО обновления (без `join_before` в JSON) → открывается без ошибок; экспорт TXT работает (разделители по фолбэку — одиночный пробел, как и было до U1.4a).
- **T4.7 (дымовой)**: приложение стартует; ВСЕ страницы Settings открываются без исключений (особенно Settings → Segmentation Rules — старая заглушка с кнопкой «Test Segmentation»); split/merge сегментов в гриде работают.

### 6.1 Результаты ручной проверки (Дмитрий, 2026-10-02)

| Сценарий | Результат |
|---|---|
| T4.1 (потеря слов) | **ок** — сегменты соответствуют `expected_segments.md`, слова не теряются |
| T4.2 (обратный экспорт) | **ок** |
| T4.3 (Markdown) | **ок** |
| T4.4 (без настроек) | косвенно подтверждён T4.1 — импорт прошёл на копии user_data без ключа правил |
| T4.5 (регрессия других путей) | **ок**; наблюдение — см. ниже |
| T4.6 (существующий проект) | **ок** |
| T4.7 (дымовой) | Settings-страницы открываются; страница Segmentation Rules (старая заглушка) открывается; кнопка «Test Segmentation» открывает диалог, но тест на дефолтном тексте падает: `'tuple' object has no attribute 'strip'` — по словам Дмитрия, поведение было и до работ над проектом (диагностика и проверка — в U1.4b); split и merge сегментов работают |

**Наблюдение T4.5** (New Project → «Paste Text» и «Load a plain-text file»): фраза «J. R. R. Tolkien wrote the book. It was long.» разбивается на «J.» / «R.» / «R.» / «Tolkien wrote the book.» (кириллица — «Дж.» / «Р.» / «Р.» / «Толкин написал книгу.»). Это **не регрессия U1.4a**: headless-прогон (§4, случай `initials`) даёт идентичные сегменты до и после батча (`['J.', 'R.', 'R.', 'Tolkien wrote the book.', 'It was long.']` в обоих деревьях) — старый сегментер резал так же. Это апстримные правила по умолчанию: однобуквенные инициалы не входят в список аббревиатур (`simple_segmenter.py:36-41`), потерь текста нет (LOSSLESS в обоих деревьях). Предсказано таблицей `expected_segments.md` (строки 13–17) и подтверждено сценарием T4.1. Смена поведения возможна после U1.4b (кастомное правило-исключение или extra abbreviations), вопрос — в §8 п. 3.

## 7. Непокрытые проверки (честно)

- Приложение агентом не запускалось (жёсткое ограничение батча) — все сценарии §6 на стороне Дмитрия. Grid-отображение `join_before` (невидимо для UI), реальное сохранение/загрузка проекта с полем, диалоговые окна — не проверялись headless-средствами.
- Headless-прогон покрывает сегментер посегментно, но не полный цикл импорта монолита (диалоги, кодировки через GUI, Okapi-пути) — их поведение меняется только в вызовах, сверенных AST-ом с апстримом.
- Тесты апстрима запускались против рабочего модуля (junction); тестовый файл `test_add_source_text.py` фичи #173 не запускался (фича вне объёма).
- Поведение правил SRX (`parse_srx`/`build_srx`) покрыто 12 апстрим-тестами, но без GUI эти пути в приложении недостижимы до U1.4b.
- Эффект «правила по умолчанию» на реальных пользовательских файлах (длина/шум сегментов) — субъективная оценка Дмитрия по T4.1.

## 8. Вопросы к Дмитрию

1. **Push**: коммиты `5c052c9d` (код) и docs-коммит отчёта — пушить в origin после вашего подтверждения (как обычно). → **ПОДТВЕРЖДЕНО (2026-10-02): пушить.**
2. **U1.4b — делать?** Объём: новый файл `segmentation_rules_widget.py` (380 строк, ЦЕЛИКОМ из тега) + 2 монолитных куска (фабрика `create_segmentation_rules_tab` ~4 строки, `_save_segmentation_rules` ~6 строк) + тесты ручные (редактор правил, SRX-импорт/экспорт, live-тест-бокс). Ничего больше не требуется; ядро уже совместимо. Рекомендую делать отдельным батчем U1.4b после проверки T4.1–T4.7. → **ПОДТВЕРЖДЕНО (2026-10-02): делаем отдельным батчем.** В объём U1.4b также включить диагностику падения кнопки «Test Segmentation» (см. §6.1, T4.7).
3. **«Др.» и др. русские аббревиатуры** в правилах по умолчанию отсутствуют (языково-агностичный апстрим). → **ЗАКРЫТО (2026-10-02): оставить строго апстримное поведение.**
4. Отчёт по-прежнему не обновляет `PROJECT_STATUS.md` (батч U1 вне формата «batch/step» экстракции; зафиксировано как постоянное отклонение с U1.1).
