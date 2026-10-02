# Upstream Sync U1.3 — Этап 2: TMX-импорт + хэш TM / Find & Replace

**Дата:** 2026-10-02
**Основание:** [UPSTREAM_SYNC_STAGE1_REPORT.md](UPSTREAM_SYNC_STAGE1_REPORT.md), [UPSTREAM_SYNC_U1_1_U1_2_REPORT.md](UPSTREAM_SYNC_U1_1_U1_2_REPORT.md) (база апстрима v1.10.371, цель v1.10.372, общей git-истории нет; U1.1 = `a7746d65`, U1.2 = `f5c460e9` уже в main).
**Коммиты батча:** U1.3a = `a1f76985` (fe1a7d0a, #105), U1.3b = `2e258269` (ee75e3be, #68) — два отдельных коммита, строго в этом порядке.
**Вне объёма:** QA-коммиты 09d374e1/2e9192f5, 763291e8, 2386c976, f6d9c279, 1f8cad19, 05720a55 и весь остальной диапазон 371..372 — не переносились даже «попутно».
**Push:** не выполнялся — только после подтверждения Дмитрия.

---

## 0. Baseline и git-синхронизация

| Параметр | Значение |
|---|---|
| HEAD до работ | `caa5f0f6` (docs-коммит U1.1+U1.2) |
| origin/main | `caa5f0f6` — совпадает |
| `git status` | чисто (только служебный untracked `.zcode/plans/…`) |
| Дрейф-чек `git merge-base --is-ancestor f5c460e9 HEAD` | **истина** |
| `git rev-parse v1.10.372^{commit}` | `a58572276b4fced9384cf64580237c9edee75007` |
| `git cat-file -t fe1a7d0a` / `ee75e3be` | оба `commit` |
| Baseline `wc -l` | Supervertaler.py = 68 286; database_manager.py = 3 361; translation_memory.py = 846; tm_metadata_manager.py = 698; find_replace_qt.py = 557 |
| Baseline SHA256 Supervertaler.py | `82d2e5d5…` (совпадает с пакетом B отчёта U1.1/U1.2) |
| `py_compile` до работ | 135/135 (монолит + `modules/**/*.py` рекурсивно) |
| EOL baseline (`git ls-files --eol`, 5 файлов) | все `i/lf w/lf` |

После работ: Supervertaler.py = **68 397** строк.

---

## 1. План файлов (Этап 1)

### 1.1 Таблица решений

| Файл | Коммиты батча | Остальные коммиты 371..372, трогающие файл | Blob Portable vs 371 | Решение |
|---|---|---|---|---|
| modules/translation_memory.py | fe1a7d0a | — (`git log v1.10.371..v1.10.372 -- <файл>`: только fe1a7d0a) | идентичен (`cd67543e`) | **ЦЕЛИКОМ из тега** |
| modules/tm_metadata_manager.py | fe1a7d0a | — | идентичен (`55bf6a40`) | **ЦЕЛИКОМ из тега** |
| modules/database_manager.py | ee75e3be | — | идентичен (`e92c2678`) | **ЦЕЛИКОМ из тега** |
| modules/tm_replace.py | ee75e3be (новый) | — | в Portable файла НЕТ | **из тега** (конфликтов имён нет: `modules/` не содержал `tm_replace`) |
| Supervertaler.py | fe1a7d0a, ee75e3be (+ отложенные) | да (дрейф монолита) | — | **ВРУЧНУЮ**, по методам |
| tests/test_tm_replace.py, tests/test_tmx_import_languages.py | ee75e3be / fe1a7d0a | — | — | **в репо НЕ добавляются** (запуск из временной копии, §4.3) |
| CHANGELOG.md | оба | — | — | ПРОПУЩЕН (в Portable нет, как FAQ.md в U1.2) |

**Ловушка find_replace_qt.py не подтвердилась в другую сторону:** файл в диапазоне трогает **только** отложенный QA-коммит 09d374e1; сам ee75e3be его **не трогает** (весь «Whole words»-фикс — в новом `modules/tm_replace.py` и монолите). В батч файл не входит и не менялся.

### 1.2 Контекст хунков монолита — дрейфа нет

AST-сравнение тел (upstream@371 vs Portable@HEAD) для всех затронутых методов показало **единственное отличие — переведённые docstring**:

| Метод | diff-строк Portable vs up@371 | Природа |
|---|---|---|
| `_show_create_tm_dialog` | 2 | docstring (RU) |
| `_import_tmx_as_tm` | 2 | docstring (RU) |
| `show_find_replace_dialog` | 14 | docstring (RU) |
| `replace_current_match` | 2 | docstring (RU) |
| `replace_all_matches` | 2 | docstring (RU) |

Кодового дрейфа нет → апстримные хунки легли дословно (проверено после переноса, §4.1).

### 1.3 Зависимости (AST) — все в Portable или приходят из самих коммитов

| Имя | Где живёт | Статус |
|---|---|---|
| `TMMetadataManager.tm_name_exists` | добавляет fe1a7d0a (ЦЕЛИКОМ-файл) | OK |
| `TMDatabase.detect_tmx_source_language` | добавляет fe1a7d0a (ЦЕЛИКОМ-файл) | OK |
| `language_codes.same_language` | modules/language_codes.py, top-level func (AST) | OK, предсуществовал |
| `TMMetadataManager.get_tm` / `get_tm_by_tm_id` / `get_writable_tm_ids` | предсуществуют (AST @182/@586/@441) | OK |
| `DatabaseManager.update_entry` | предсуществовал @2212; **Portable == up@371 побайтово** | OK |
| `DatabaseManager._normalize_for_matching` | module-level @76 (не метод — первый AST-проход не нашёл его как метод класса) | OK |
| `DatabaseManager.connection` | @120/@173 — используется `tm_replace.replace_in_tms` | OK |
| `SupervertalerQt._apply_case_pattern`, `._clear_caches_after_import` | @49653 / @48691 | OK |
| `CheckmarkCheckBox` | `from modules.styled_widgets import …` в монолите | OK |
| `self.tm_database` | присваивается `TMDatabase(...)` в `SupervertalerQt` (@6362, @6695) | OK |
| `tm_metadata_mgr.create_tm`, `find_all_matches_internal`, `allow_replace_in_source`, `_fr_compile_regex` | предсуществуют | OK |

Зависимостей от кода отложенных коммитов **не обнаружено** — СТОП не сработал ни разу.

### 1.4 Безопасность данных (п. 5 Этапа 1)

- **(а) Схема БД:** изменений нет. Ни один из двух диффов не содержит DDL (ALTER TABLE / CREATE / миграций). fe1a7d0a-модули добавляют только read-only методы (`SELECT`, `ET.iterparse`); `database_manager.py` меняет только вычисление хэша в `update_entry`.
- **(б) Куда пишет tm_replace:** `replace_in_tms` пишет через `db_manager.connection` напрямую: `UPDATE translation_units SET source_text, target_text, source_hash, target_hash, modified_date`, синхронно `UPDATE tm_fts` (OperationalError при отсутствии FTS — игнорируется), на дубликат (IntegrityError) — `ROLLBACK TO SAVEPOINT` + `DELETE` записи-источника (merge). Всё в одной транзакции (`BEGIN`, если не открыт) с `conn.commit()/rollback()`. Хэши пересчитываются `_hashes()` = md5(`_normalize_for_matching(…)`), **идентично** `add_translation_unit` (`database_manager.py:1043-1047`).
- **(в) Защита от записи в read-only/невыбранные TM:** `tm_ids` берутся **только** из `get_writable_tm_ids(project_id)` — в SQL явно `tm.read_only = 0 AND ta.is_active = 1` (только активные для проекта с галочкой Write; предсуществующий метод, тело не менялось). План (dry-run) показывается пользователю в диалоге подтверждения ДО записи; запись — только после «Yes». Read-only и неактивные TM не попадают в выборку by construction.
- **(г) Пересчёт старых хэшей:** апстрим **не** пересчитывает хэши уже сохранённых записей. Фикс действует на: (1) будущие правки записей (`update_entry`), (2) записи, изменённые Replace-all в TM (`replace_in_tms` пересчитывает хэши при записи). Старые записи, испорченные дефектом до фикса, **останутся неверными**, пока их не отредактируют снова. → риск-пункт R1 (§1.5), сценарий T3.1 проверяет именно будущие правки.
- **(д) Дубликаты при merge:** запись, ставшая идентичной существующей в том же TM, удаляется (текст переносится существующей записью); счётчик `merged` показывается в диалоге. Потери текста нет — пара source/target идентична.

### 1.5 Риски (отдельным пунктом)

- **R1 (низкий, принят апстримом):** ранее испорченные хэши не ремонтируются автоматически. Пользовательская процедура: отредактировать запись ещё раз после обновления (или прогнать Replace-all по записи). Массового пересчёта апстрим не делает — переносить своё решение запрещено правилами.
- **R2 (низкий):** Replace-all в TM необратим (Ctrl+Z не действует) — апстрим предупреждает в tooltip и в диалоге подтверждения, но отката нет. Сценарий T3.4 выполнять только на копии user_data.

### 1.6 Режимы match_mode (для сценариев, `modules/tm_replace.py`)

Константы: `MATCH_ANYTHING=0`, `MATCH_WHOLE_WORDS=1`, `MATCH_ENTIRE_SEGMENT=2` (совпадает сPortable: `match_mode == 1` = «Whole words», `== 2` = «Entire segment» в монолите). Поведение `make_replacer`:
- обычный (0): `re.escape(find)`-подстановка; `auto_case` (без case_sensitive) подгоняет регистр замены под найденное; замена — литеральная (backslash не интерпретируется);
- **Whole words (1):** то же + `\b`-границы слова — главное исправление: раньше Replace All заменял и внутри длинных слов;
- Entire segment (2): сегмент целиком сравнивается (без учёта регистра), заменяется на replacement (с `auto_case`);
- regex: `re.compile(find)` + `re.sub`; `count` (1 — «Replace current», 0 — все); `re.error` ловится и показывается как «Invalid regular expression».

---

## 2. U1.3a — что сделано (коммит `a1f76985`)

| Апстрим-SHA | Файл | Способ | Проверка |
|---|---|---|---|
| fe1a7d0a | modules/translation_memory.py | ЦЕЛИКОМ из тега | staged blob `848d572d` == `v1.10.372:modules/translation_memory.py` |
| fe1a7d0a | modules/tm_metadata_manager.py | ЦЕЛИКОМ из тега | staged blob `d079095d` == тег |
| fe1a7d0a | Supervertaler.py — 8 хунков, 3 метода | вручную | §2.1 |

**Суть fe1a7d0a (#105):** TMX-заголовок `srclang` задаёт направление (detect_tmx_languages возвращает алфавитный список, из-за чего en-GB→de-DE предлагался как de→en); имена TM уникальны — при создании предлагается свободное имя («Client TM (2)»), при занятом — явное сообщение вместо голого «Failed to create TM metadata»; импорт идёт в TM, id которой реально создан (`create_tm` делает id уникальным при повторном импорте того же TMX).

### 2.1 Монолит (до → после, verbatim к апстриму)

| Метод | Изменение |
|---|---|
| `SupervertalerQt._show_create_tm_dialog` | перед `create_tm`: guard `tm_metadata_mgr.tm_name_exists(name)` → «Name already in use» |
| `SupervertalerQt._preselect_tmx_pair` | **новый staticmethod** между `_show_create_tm_dialog` и `_import_tmx_as_tm`: точное совпадение `lang.lower() == header_src.lower()`, иначе `same_language`; target — единственный другой язык |
| `SupervertalerQt._import_tmx_as_tm` | цикл подбора свободного имени + `while True`-диалог с повтором при занятом имени; `tmx_header_src = self.tm_database.detect_tmx_source_language(filepath)` + строка «The file says its source language is …» в обоих ветках диалога языков (новая и существующая TM); `self._preselect_tmx_pair(...)` после дефолтного `setCurrentIndex(1)` в обеих ветках; в ветке новой TM: `created = tm_metadata_mgr.get_tm(db_id) or {}; target_tm_id = created.get('tm_id') or tm_id` |

Пост-проверка: `verify_fe1a.py` — `_preselect_tmx_pair` diff = 0 строк; `_show_create_tm_dialog`/`_import_tmx_as_tm` diff = только docstring.

После U1.3a: `py_compile` 135/135; diff --stat ровно 3 файла (99+/15−); EOL всех `i/lf w/lf`.

---

## 3. U1.3b — что сделано (коммит `2e258269`)

| Апстрим-SHA | Файл | Способ | Проверка |
|---|---|---|---|
| ee75e3be | modules/database_manager.py | ЦЕЛИКОМ из тега (Portable == 371, файл трогает только ee75e3be) | staged blob `64ea3445` == тег |
| ee75e3be | modules/tm_replace.py | ЦЕЛИКОМ из тега (новый) | staged blob `943a35d1` == тег |
| ee75e3be | Supervertaler.py — 7 хунков, 3 метода + 1 новый | вручную | §3.1 |

**Суть ee75e3be (#68):** (1) `update_entry` хэшировал отредактированный source как `md5(source.lower())`, а exact-поиск ищет md5(`_normalize_for_matching(source)`) — запись с заглавной буквой после первой же правки переставала находиться; теперь хэш тот же, что пишет `add_translation_unit`. (2) «Whole words» в F&R заменял и внутри длинных слов. (3) Replace All теперь может менять и writable TM проекта (с dry-run-планом в диалоге подтверждения) — вся логика замены сведена в `tm_replace.make_replacer` (проект и TM используют один и тот же replacer).

### 3.1 Монолит (до → после, verbatim к апстриму)

| Метод | Изменение |
|---|---|
| `SupervertalerQt.show_find_replace_dialog` | после `fr_demote_cb`: новый чекбокс `self.fr_also_tm_cb` «Also in writable TMs» (не запоминается: правит TM, Ctrl+Z не отменяет) |
| `SupervertalerQt.replace_current_match` | инлайн-логика (regex/entire/replace-ветки) → `make_replacer(..., count=1)(field_text)`; `re.error` → «Invalid regular expression» |
| `SupervertalerQt.replace_all_matches` | хунк A: `replacer = make_replacer(...)`, `tm_plan = self._fr_plan_tm_replace(replacer, search_source, search_target)`, `tm_changes`; «No matches found» только если нет и в проекте, и в TM («(None in the writable TMs either.)»); хунк B: фильтр source-совпадений учитывает `tm_changes`; хунк C: формулировка подтверждения при отсутствии проектных совпадений + блок TM-плана (имена TM, число записей, до 3 примеров «старое → новое», предупреждение про Ctrl+Z); хунк D: regex-валидация шаблона только при наличии `self.find_matches`; хунки E/F: `import re` из try убран, инлайн-замена → `new_text = replacer(old_text)`; хунк G: итог-сообщение + `replace_in_tms(..., apply=True)`, merge-инфо, `self.log(✓ …)`, `self._clear_caches_after_import()`; ошибки записи — `⚠️ The TMs could not be changed: {e}` |
| `SupervertalerQt._fr_plan_tm_replace` | **новый метод** сразу после `replace_all_matches` (перед `highlight_all_matches`): None при выключенном чекбоксе; `tm_ids = mgr.get_writable_tm_ids(project_id)`; имена через `get_tm_by_tm_id`; `in_source = search_source and allow_replace_in_source`; dry-run `replace_in_tms(apply=False)`; лог «ℹ️ … no TM with Write ticked» при пустом списке |

Пост-проверка: `verify_ee7.py` — `_fr_plan_tm_replace` diff = 0 строк; остальные три метода — только docstring (одна whitespace-строка в `replace_all_matches` приведена к апстримному виду; по ходу правки была ошибочно удалена пара строк WARNING-блока — обнаружено повторным diff-сравнением и восстановлено до отправки в коммит).

После U1.3b: `py_compile` 136/136 (включая новый tm_replace.py); diff --stat ровно 3 файла (266+/49−); EOL всех `i/lf w/lf`.

`database_manager.py` (ЦЕЛИКОМ): `update_entry` @2232 — `new_hash = hashlib.md5(_normalize_for_matching(new_source_stripped)…)` вместо `md5(new_source_stripped.lower()…)`; комментарий апстрима перенесён; target_hash уже считался через `_normalize_for_matching` — не менялся.

---

## 4. Статическая и headless-валидация

### 4.1 AST-проверки (`validate_u13.py`, `verify_fe1a.py`, `verify_ee7.py`)
- **(а)** Все 7 затронутых/новых методов в ожидаемых классах (`SupervertalerQt`); `_preselect_tmx_pair` не появился в других классах (ловушка одноимённых методов).
- **(б)** Сигнатуры всех функций 4 изменённых модулей == `v1.10.372` (database_manager 54, tm_replace 4, tm_metadata_manager 22, translation_memory 46 — расхождений 0).
- **(в)** `tm_replace.py` парсится; все 4 модуля — staged blob == тег.
- **(г)** Регресс-guard: no-arg `save_general_settings()` — по-прежнему 0.
- **(д)** Verbatim-проверка монолитных методов: diff против `v1.10.372` — только docstring; 2 новых метода — 0 diff.

### 4.2 Blob- и EOL-проверки
- 4 файла «ЦЕЛИКОМ» — blob равен `v1.10.372:<path>`: `848d572d` (translation_memory), `d079095d` (tm_metadata_manager), `64ea3445` (database_manager), `943a35d1` (tm_replace).
- EOL всех затронутых файлов до и после: `i/lf w/lf` — не изменились.
- Кумулятивный `git diff --stat caa5f0f6..2e258269`: ровно 5 ожидаемых файлов (365+/64−).

### 4.3 Тесты апстрима — 13/13 PASS
`tests/test_tm_replace.py` + `tests/test_tmx_import_languages.py` (оба импортируют только `modules.*`, монолит не импортируют) запущены из временной копии вне репо (`D:\Temp\SupervertalerPortable\refactoring\u1-port\repo-sim\`, junction на `modules/`; `E:\Dev\python-embed\python.exe -m pytest … -q`):
```
13 passed in 10.35s
```
(покрывают: make_replacer во всех режимах включая whole-words/entire/regex/count/literal-backslashes/auto_case; replace_in_tms dry-run/apply/merge/rollback; detect_tmx_source_language; tm_name_exists.) В репо `tests/` НЕ добавлялся.

### 4.4 Headless-проверка «до/после» (`headless/hl_check.py`, без Qt, временная SQLite)
Один и тот же скрипт на старом коде (`before/` = модули из `caa5f0f6`) и на новом (`after/` = рабочий репозиторий):

| Проверка | before (`caa5f0f6`) | after (`2e258269`) |
|---|---|---|
| (a) запись «Conrad Kinch»→правка `update_entry`→`get_exact_match` | **false — запись НЕ находится** (дефект воспроизведён) | **true**, target = «Iwan Petrowitsch» |
| (b) `detect_tmx_source_language` (синтетический TMX, tuv в алфавитном порядке de-DE/en-GB, srclang="en-GB") | метода нет (AttributeError) | **"en-GB"** |
| (c) `tm_name_exists` на занятом/свободном имени | метода нет (AttributeError) | **True / False** |

### 4.5 py_compile — 135/135 до работ, 135/135 после U1.3a, 136/136 после U1.3b (новый tm_replace.py).

---

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: коммит `f5c460e9` (U1.1 + U1.2 уже установлены). Файлы заменяются целиком поверх.

### Пакет A — U1.3a (коммит `a1f76985`, поверх f5c460e9)
| № | Путь | SHA256 | Примечание |
|---|---|---|---|
| 1 | `modules/translation_memory.py` | `e8ff3fdc65e15f967f24b8221f5edf1dbaf0e21839798b4a28eccaeacee783e3` | `detect_tmx_source_language`; blob == апстрим v1.10.372 |
| 2 | `modules/tm_metadata_manager.py` | `e5d0045cddd4e3583a6f1216453c813195f2204ee652084b5ed6cc95d5db558d` | `tm_name_exists`; blob == апстрим |

### Пакет B — U1.3b (коммит `2e258269`, поверх Пакета A)
| № | Путь | SHA256 | Примечание |
|---|---|---|---|
| 3 | `Supervertaler.py` | `e2ee49662cc3fffae95172a4644078e9b288acabb6fcfa4848ff727b9d5db4b8` | оба коммита, 68 397 строк |
| 4 | `modules/database_manager.py` | `e4072e6762adde0fe02e96efa3024afdf0b5befd52a90e82f0e4ec313c52b834` | фикс хэша `update_entry`; blob == апстрим |
| 5 | `modules/tm_replace.py` | `00ba2c7e400ecc33cd88def8a0de34ecaffbfbf2ed50f0fe2bd3f141e0227993` | **новый файл**; blob == апстрим |

(Заменённый в Пакете B `Supervertaler.py` включает и правки Пакета A; модули Пакета A при установке B повторно заменять не нужно.)

**ВНИМАНИЕ: все операции с TM в T3.1/T3.4/T3.5 — только на КОПИИ user_data тестовой сборки.** T3.4 необратим (Ctrl+Z не действует на TM).

---

## 6. СЦЕНАРИИ ПРОВЕРКИ (на тестовой сборке, вручную)

Каждый сценарий — сначала КОНТРОЛЬ на baseline `f5c460e9` (дефект виден), затем после замены файлов. Приоритет: **T3.1, T3.2, T3.5 — основные**; T3.4 — новая функция, проверять только при использовании.

**U1.3b:**
- **T3.1** (хэш TM): в редакторе TM поправить запись (например сменить target), у которой source начинается с заглавной буквы («Conrad Kinch»); затем в проекте сегмент с тем же source должен находиться как exact (100%) match. Контроль baseline: запись не находится (headless-аналог подтверждён, §4.4a).
- **T3.2** (Whole words): Find & Replace, режим «Whole words», слово встречается и как отдельное слово, и внутри других слов → заменяется только отдельное. Проверить «Replace current» (count=1) и «Replace all».
- **T3.3** (регрессия F&R): обычный режим, regex (включая `re.sub`-шаблоны с `\1`), «Entire segment», без Whole words — результат как раньше; диалог открывается, поиск/подсветка не сломаны; автоподгон регистра (auto_case) работает как раньше.
- **T3.4** (замена в TM — новая функция, только на копии): галочка «Also in writable TMs», Replace all фразы, встречающейся в TM-записях → в диалоге подтверждения показан план (имена writable TM, число записей, примеры); после подтверждения меняются ТОЛЬКО выбранные writable TM; read-only/неактивные TM не изменены; записи, ставшие дубликатами, слиты (в сообщении «N … merged»); матч-панель не показывает старый текст (cache cleared). Контроль baseline: галочки нет, TM не меняются.
- **U1.3a:**
- **T3.5** (TMX): TMX с `srclang="en-GB"` и tuv в алфавитном порядке (de-DE первым): диалог языка предлагает en-GB→de-DE (а не de→en); в подписи диалога строка «The file says its source language is en-GB.»; импорт идёт в выбранный/создаваемый TM; при существующем имени предлагается «name (2)», при вводе занятого — сообщение «Name already in use» вместо «Failed to create TM metadata»; число импортированных записей совпадает с ожидаемым. Контроль baseline: направление предлагается по алфавиту (de→en), занятое имя даёт голую ошибку.
- **T3.6** (регрессия TM): импорт обычного TMX без srclang-особенностей (srclang отсутствует или «*all*» → поведение прежнее: алфавитный порядок), открытие TM-вкладки/редактора, поиск по TM — как раньше.
- **T3.7** (дымовой): приложение стартует, все страницы Settings, F&R-диалог (Ctrl+F/Ctrl+H) и TM-вкладки открываются без исключений.

---

## 6.1 Результаты ручной проверки (тестовая сборка, Дмитрий, 2026-10-02)

Файлы Пакетов A+B заменены поверх сборки `f5c460e9` согласно §5.

**Подтверждено:**

| Сценарий | Результат |
|---|---|
| T3.1 (хэш TM) | PASS — после правки записи с заглавной буквой в source сегмент находится как exact match |
| T3.2 (Whole words) | PASS — заменяется только отдельное слово |
| T3.3 (регрессия F&R) | PASS — обычный режим/regex/Entire segment работают как раньше |
| T3.4 (замена в TM) | PASS — выполнена на копии; затронуты только writable TM, план показан перед применением |
| T3.7 (дымовой) | PASS — приложение стартует, страницы/диалоги открываются |

**Не проверялось (нет подходящих данных; риск принят):**

| Сценарий | Причина | Почему приемлемо |
|---|---|---|
| T3.5 (TMX srclang/направление/имена) | нет TMX-файлов (и тем более с немецким языком) | Оба модуля Пакета A побайтно равны апстриму; логика покрыта 4 headless-проверками (§4.4b/§4.4c: srclang="en-GB" из алфавитного списка → "en-GB"; tm_name_exists True/False) и тестами апстрима test_tmx_import_languages.py |
| T3.6 (регрессия TM-импорта) | нет TMX-файлов | Тот же файл побайтно равен апстриму; detect_tmx_languages не менялся (новый метод добавлен рядом, старый путь не тронут — дифф fe1a7d0a содержит только добавления) |

---

## 7. Непокрытые проверки

1. **UI-сценарии T3.1–T3.7 изначально не выполнялись ИИ** (приложение по ТЗ не запускалось); рантайм-поведение диалогов (`QFileDialog`, `QInputDialog`, `QMessageBox.question`) не воспроизводилось headless. Часть сценариев затем выполнена Дмитрием на тестовой сборке — см. §6.1; непроверенное там перечислено явно.
2. **`_fr_plan_tm_replace` не исполнялась** — вызывается только из UI-пути Replace All; корректность подтверждена статически (verbatim == апстрим, зависимости `get_writable_tm_ids`/`get_tm_by_tm_id`/`db_manager.connection` проверены AST) и юнит-тестами `replace_in_tms`, но не исполнением.
3. **`_clear_caches_after_import`** вызывается в новом пути Replace-all-in-TM; метод предсуществовал (@48691), его эффект на кэши матчей после прямой записи в БД не проверялся в рантайме (в апстриме тот же вызов в том же месте).
4. **Транзакционное поведение `replace_in_tms`** на реальной FTS5-базе с большим объёмом не прогонялось (юнит-тесты апстрима используют маленькие БД; ветка «no full-text index» покрыта тестом).
5. **Взаимодействие с отложенными QA-коммитами:** 09d374e1 трогает `find_replace_qt.py`, который в этом батче не менялся — конфликта нет, но при переносе U1.4 нужно повторить план файлов для этого файла.
6. **`tm_manager.update_entry`** (обёртка TMDatabase, `translation_memory.py:456`) идёт в тот же фикс — её вызов из `translation_results_panel.py` не проверялся рантаймом.

---

## 8. Вопросы к Дмитрию

1. **Q1 — push:** коммиты `a1f76985` (U1.3a), `2e258269` (U1.3b) и docs-коммит отчёта — пушить в origin после вашего подтверждения (как в U1.1/U1.2)?
   **→ ЗАКРЫТ (2026-10-02): подтверждено**, пуш выполнен после внесения результатов ручной проверки §6.1.
2. **Q2 — R1 (старые хэши):** апстрим не чинит уже испорченные хэши TM-записей. Оставляем как в апстриме (самовосстановление по мере правок) или нужно отдельное задание на одноразовый массовый пересчёт (вне регламента verbatim-переноса)?
   **→ ЗАКРЫТ (2026-10-02): оставляем как в апстриме** — записи в базе переводов восстанавливаются по мере их правок; массовый пересчёт не делается.
3. **Q3 — T3.4:** будет ли использоваться замена в TM (нужно ли включать её в обязательный чек-лист приёмки, или «проверять только при использовании»)?
   **→ ЗАКРЫТ (2026-10-02): «проверять только при использовании»** — пока нет наработанной TM.

---
*Артефакты: `D:\Temp\SupervertalerPortable\refactoring\u1-port3\` — диффы двух коммитов (`fe1a_mono.diff`, `ee7_mono.diff`, `ee7_db.diff`, `tm_replace_from_tag.py`), скрипты (`hunk_map.py`, `body_diff.py`, `verify_fe1a.py`, `verify_ee7.py`, `validate_u13.py`, `dep_check.py`), headless-прогон (`headless/hl_check.py`, `headless/before/`, `after`-результаты `before.json`/`after.json`); снимок монолита `mono_head_snapshot.py` (sha256 `82d2e5d5…`).*
