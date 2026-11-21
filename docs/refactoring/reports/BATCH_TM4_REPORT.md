# BATCH TM4 — сохранение ID записи TM при правке перевода и повторном подтверждении

**Статус: выполнено (агент, 2026-11-21). Ждёт вердикта Дмитрия. Пуша нет.**
База: origin/main = `02ecf67b` (TM3+TM3.1 запушены), HEAD = `7da9f08a`
(push-record TM3+TM3.1). `02ecf67b` — предок HEAD (проверено `git merge-base
--is-ancestor` до первого чтения кода).

Наблюдение Дмитрия: сегмент подтверждён (запись в TM с ID 463) → перевод
правится → повторное подтверждение → запись получает НОВЫЙ ID (499).
Ожидание: правка перевода — это та же запись, ID должен сохраняться.

---

## 1. Разведка (задача 0) — `docs/refactoring/audits/tm4_recon_before.py`

### 1.1. Таблица записи и ключ уникальности

`modules/database_manager.py`, таблица `translation_units` (DDL на строках
236–267):

```sql
CREATE TABLE translation_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_text TEXT NOT NULL, target_text TEXT NOT NULL,
    source_lang TEXT NOT NULL, target_lang TEXT NOT NULL,
    tm_id TEXT NOT NULL, project_id TEXT, ...
    source_hash TEXT NOT NULL, target_hash TEXT,   -- md5 от нормализованных текстов
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0, ...
    UNIQUE(source_hash, target_text, tm_id)
)
```

- Ключ уникальности на уровне БД: `UNIQUE(source_hash, target_text, tm_id)`
  — формально включает target.
- **Оперативный** ключ режима overwrite («Save only latest translation») —
  `(source_hash, tm_id)`: старый код делал
  `DELETE FROM translation_units WHERE source_hash = ? AND tm_id = ?`
  (строки 1052–1056) перед INSERT, т.е. работало правило «одна строка на
  (source, TM)». Именно этот ключ и предлагает промпт (0.5: tm_id +
  нормализованный source); он подтверждён кодом.

### 1.2. Все писатели в `translation_units` (0.1/0.5)

| # | Писатель | Где | SQL / режим | Что с ID при совпадении ключа |
|---|---|---|---|---|
| 1 | `add_translation_unit` — **overwrite-ветка** (`overwrite=True`) | database_manager.py:1049–1070 | `DELETE (source_hash, tm_id)` + `INSERT` | **Новый ID всегда** (и при другом, и при том же target) — ядро симптома |
| 2 | `add_translation_unit` — upsert-ветка (`overwrite=False`, режим «all») | database_manager.py:1058–1067 | `INSERT … ON CONFLICT(source_hash, target_text, tm_id) DO UPDATE SET usage_count+1, modified_date` | Совпадающая пара → ID сохранён; **другой target → новая строка** (штатные «варианты» режима all) |
| 3 | `add_translation_units_batch` (импорт TMX/CSV-подобных массовых вставок) | database_manager.py:1106–1165 | тот же upsert, без overwrite | как #2; семантика импорта не менялась |
| 4 | `get_exact_match` / реверс-ветка | database_manager.py:1258–1262, 1319–1323 | `UPDATE usage_count+1 WHERE id` | запись не меняется |
| 5 | usage-инкремент после батч-поиска | database_manager.py:1586 | `UPDATE usage_count+1 WHERE id IN (…)` | запись не меняется |
| 6 | `update_entry` (TM Editor / Match Panel) | database_manager.py:2212–2263 | `UPDATE … SET source_text, target_text, хэши, modified_date WHERE id` | уже in-place, ID сохраняется — не тронут |
| 7 | `delete_entry` (Browse All Delete) | database_manager.py:2182–2210 | `DELETE WHERE id` | — |
| 8 | `clear_tm` / удаление TM | database_manager.py:2178; tm_metadata_manager.py:287 | `DELETE WHERE tm_id` | — |
| 9 | TM Maintenance (чистка дублей) | tm_manager_qt.py:173/217/1543 | `DELETE … IN (…)` | — |
| 10 | tm_replace (массовая замена) | tm_replace.py:142–151 | свой UPDATE/DELETE по rowid | — |

**Вызывающие** путь #1 (overwrite=True — единственный затронутый правкой):

- `save_segment_to_activated_tms` (Supervertaler.py:28017–28129) —
  подтверждение сегмента: `overwrite=overwrite_mode`, где
  `overwrite_mode = (self.tm_save_mode == 'latest')` (Supervertaler.py:28081),
  `'latest'` — значение по умолчанию (Supervertaler.py:5976).
- `TMDatabase.add_entry(…, overwrite=True)` (translation_memory.py:161–179) —
  вызывается «Update Active TM(s)» (Supervertaler.py:39795) с галкой
  overwrite (v1.10.145).

Писатели #2/#3 (upsert, режим «all» и импорт): `TMXImportThread`
(tm_manager_qt.py:86), `load_tmx_file`/`_load_tmx_into_db`
(translation_memory.py:506/539 → batch 623/643), legacy-`from_dict` и
`TMAgent` (translation_memory.py:785–824). **Правкой не затронуты.**

Замечание разведки (вне батча, НЕ правилось): `TMXImportThread`
(tm_manager_qt.py:86) вызывает `add_translation_unit(…, save_mode='all')` —
параметра `save_mode` у функции нет (есть `overwrite: bool`), т.е. этот
фоновый импорт TMX из списка TM падает с `TypeError` и импорт не выполняется
(исключение ловится, `finished(False, "Import failed: …")`). Рабочий путь
импорта TMX — `load_tmx_file` (он и тестируется). Сообщено Дмитрию в отчёте,
не чинено («заодно» запрещено).

### 1.3. Путь реального подтверждения (0.2)

```
Ctrl+Enter → _confirm_current_row_segment (Supervertaler.py:46883)
  → правка перевода перед этим: on_target_text_changed
      ставит статус confirmed → draft (Supervertaler.py:33192–33196)
  → update_status_icon(row, 'confirmed', save_to_tm=(old_status != 'confirmed'))
      (Supervertaler.py:46942)
  → guard: save_to_tm ∧ status=='confirmed' ∧ target непуст (37182–37183)
  → save_segment_to_activated_tms(source, target) (37185 → 28017)
  → по каждой записываемой TM (get_writable_tm_ids, флажок Write):
      db_manager.add_translation_unit(…, overwrite=overwrite_mode) (28087–28094)
  → overwrite-ветка: DELETE(source_hash, tm_id) + INSERT (1052–1067)
```

- **Первое подтверждение**: строки (source, TM) нет → plain INSERT → ID N.
- **Повторное после правки target**: строка есть → DELETE + INSERT → ID M≠N
  (AUTOINCREMENT не переиспользует ID). created_date/usage_count новой строки
  — свежие (сброс).
- `save_to_tm=(old_status != 'confirmed')`: Ctrl+Enter по УЖЕ
  подтверждённому сегменту запись не делает вовсе (задумка T2-батча);
  повторное подтверждение после правки идёт именно через draft→confirmed.

### 1.4. Почему меняется ID и скачок 463→499 (0.3)

Старый overwrite-код = безусловный `DELETE` + `INSERT`:
- ID меняется **всегда** при проходе через путь записи — даже если target
  идентичен (воспроизведено: recon R2).
- Скачок 463→499: `AUTOINCREMENT` ведёт `sqlite_sequence`, ID = max+1.
  Одно подтверждение тратит ровно **1** ID на одну TM (recon R3: дельта
  `sqlite_sequence` = 1 на подтверждение). «Лишних» ID внутри одного
  подтверждения нет; разрыв 36 — счётчик, ушедший вперёд между двумя
  подтверждениями Дмитрия (другие подтверждённые сегменты — по 1 ID на
  каждую активную записываемую TM, импорты TMX, записи «Update Active TM(s)»).

### 1.5. FTS и производные индексы (0.4)

- `translation_units_fts` — **external-content FTS5** (`content=
  translation_units, content_rowid=id`), синхронизация триггерами
  `tu_fts_insert/tu_fts_delete/tu_fts_update` (database_manager.py:296–332);
  delete-триггер использует специальную команду `('delete', old…)` —
  обязательную для external-content (комментарий 313–317).
- `translation_units_trigram` — самостоятельная FTS5 (CJK-подмножество,
  tokenize='trigram'), триггеры `tu_trig_insert/delete/update` (355–378).
- Потребители: concordance-поиск (JOIN translation_units_fts, 2316–2332),
  fuzzy-поиск (MATCH по fts-таблицам, 1917–2049), Browse All filter —
  НЕТ, он читает саму таблицу через `sv_casefold` LIKE
  (tm_manager_qt.py:1327–1356).
- **In-place UPDATE строки корректно синхронизирует оба индекса**:
  `tu_fts_update` выполняет `('delete', old)` + insert-new, `tu_trig_update`
  — delete по rowid + условный insert. Проверено на recon (R8) и в сьюте
  (S5: старый target не ищется, новый ищется, rowid найденной записи =
  сохранённый ID). Legacy-упоминания `tm_fts` (2199/2248, tm_replace.py) —
  мёртвый след старой схемы (таблицы нет, statements в try/except).
- **Стоп-условие (б) не сработало**: FTS обновляется на месте без смены
  схемы.

### 1.6. Ключ «та же запись» и затронутые писатели (0.5)

- Действующий ключ overwrite-пути — `(source_hash, tm_id)` (см. 1.1/1.2);
  нормализация source уже делается кодом (`_normalize_for_matching` → md5,
  database_manager.py:1043–1044). Регистр/пробелы нормализуются так же, как
  раньше — ничего добавлять не нужно.
- DB-уровня `UNIQUE(source_hash, target_text, tm_id)` не мешает in-place
  UPDATE (одна строка на (source, TM) удовлетворяет уникальности), но
  формально включает target → по стоп-условию (а) ответ: ключ уникальности
  БД шире операционного; неоднозначности нет, т.к. overwrite-режим уже
  работает на (source_hash, tm_id). **(а) не сработало.**
- Затронутые писатели: только overwrite-ветка `add_translation_unit`
  (пути подтверждения и «Update Active TM(s)» с галкой overwrite).
  Импорт (batch upsert) — другой код, семантика не меняется
  (зафиксировано recon-тестом R5/R5f «до» и сьютом S6/S6f «после»).
  Propagation (`_auto_propagate_to_identical`, Supervertaler.py:46967) в TM
  не пишет — меняет только сегменты проекта. **(в) не сработало**: ни один
  вызывающий не использует возвращённый ID как «ID новой строки» и не
  полагается на пересоздание строки.
- **(г) не сработало**: семантика разделяется существующим флагом
  `overwrite` (latest → in-place; all → варианты), общий путь записи
  разделяем без большой правки.

### 1.7. Recon «до» (0.6) — `docs/refactoring/audits/tm4_recon_before.py`

Изолированный профиль (`TM4_STAGE_DIR`), полное окно `SupervertalerQt`
offscreen, проводка через реальный Ctrl+Enter
(`_confirm_current_row_segment`). Итог чистого прогона: **17/17 CONFIRMED**
(лог: `run-001/out/recon_before.log`, факты: `tm4_recon_before.json`):

| Проверка | Результат (до-код) |
|---|---|
| R1 подтвердить → править → подтвердить | ID **1 → 2**, строка одна, created пересоздан |
| R2 повтор с тем же target через путь записи | ID снова сменился (2 → 3) |
| R3 счётчик | 1 ID на подтверждение (дельта sqlite_sequence = 1) |
| R4 две TM | обе записи получили новые ID |
| R5/R5f импорт (эталон «как раньше») | варианты source → 2 строки; повторный импорт той же пары → usage+1, ID сохранён |
| R6 legacy-дубли + overwrite | 1 строка остаётся (контракт latest) |
| R7 удаление → подтверждение | новая запись с новым ID (штатно) |
| R8 FTS | старый target не ищется, новый ищется |

Recon обязан был падать до правки — основная проверка R1 CONFIRMED (симптом
воспроизведён), код выхода 0 (измерение, не gate).

---

## 2. Что сделано — «было / стало / причина»

Правка ровно одна: overwrite-ветка `add_translation_unit`
(modules/database_manager.py:1049–1101, +46/−3). Схема БД, upsert-ветка
(режим «all»), импорт, Browse All, TM Editor — не тронуты.

| | Было | Стало | Причина |
|---|---|---|---|
| Подтверждение с правкой target (режим latest) | `DELETE (source_hash, tm_id)` + `INSERT` → новый ID, created/usage сброшены | `SELECT id, target_text … WHERE source_hash AND tm_id ORDER BY modified_date DESC, id DESC LIMIT 1`; строка есть и target другой → `UPDATE … SET target_text, target_hash, modified_date + поля вызова` **на месте**; ID/created/usage сохранены; лог `💾 TM entry #N updated in place (TM: …)` | Правка перевода — та же запись (наблюдение Дмитрия) |
| Подтверждение без изменения target через путь записи | тот же DELETE+INSERT → новый ID | строка есть и target идентичен → **без записи** (ID, created, usage, modified не тронуты); legacy-дубли (source_hash, tm_id) сворачиваются до одной строки тем же DELETE с `id != ?` | «Запись не дублируется, ID тот же» (задача 1.1, T-TM4c) |
| Источника нет в TM | INSERT | INSERT (как было) — новый ID корректен | Новая запись — это новая запись |
| Legacy-дубли (старые БД, режим all) | DELETE всех + INSERT одного | UPDATE последней по modified_date + DELETE остальных (`id != ?`) — итог тот же: 1 строка, но ID одной из прежних сохранён | Контракт «latest» = одна строка на (source, TM); поведение не должно падать на дублях (задача 1.6/тесты) |
| FTS/trigram при правке | DELETE+INSERT триггеры | UPDATE-триггеры `tu_fts_update`/`tu_trig_update` | Индексы остаются согласованными: старый текст не ищется, новый ищется (S5/R8) |
| target_hash | INSERT считал, старая строка могла жить с устаревшим | UPDATE пишет актуальный target_hash | реверс-точные совпадения остаются корректными |

Детали семантики (осознанные решения, вошедшие в правку):
- поля вызова обновляются все, кроме identity-полей: сохраняются
  `id`, `created_date`, `usage_count`, `created_by`; обновляются
  `source_text/target_text/source_lang/target_lang/project_id/
  context_before/context_after/target_hash/notes/modified_date` — это в точности
  «строка как после DELETE+INSERT», но с прежним ID (задача 1.1 «прочие
  поля по текущей семантике»);
- лог по-английски, одной строкой, без модалей (задача 1.7): «💾 TM entry #N
  updated in place (TM: tm_id)» — печатается только при фактическом
  изменении target (тихий no-op при идентичном target);
- правка в НЕСКОЛЬКИХ активных TM: путь `save_segment_to_activated_tms`
  и так пишет в каждую TM отдельно — каждая TM обновляет свою запись, свои
  ID (задача 1.4, S4);
- запись удалена между подтверждениями → строка не найдена → INSERT → новый
  ID (задача 1.5, S8).

---

## 3. Тесты

### 3.1. Новый сьют — `docs/refactoring/audits/tm4_inplace_tests.py` — **34/34 PASS**

Проводка через реальный путь: `import_simple_txt` →
`_confirm_current_row_segment` (Ctrl+Enter). Прямые вызовы БД — только
сидование legacy-состояний (отмечено в названиях проверок).

| Блок | Проверки |
|---|---|
| S1 | правка+подтверждение: **тот же ID**, строка одна, новый target в строке, created сохранён, modified обновился |
| S3 | лог «💾 TM entry #N updated in place (TM: …)» — одна строка, английский (перехват db_manager.log; NOTE: лог идёт через callback, захваченный при конструировании Supervertaler.py:6188, rebind `win.log` его не ловит) |
| S1u | DB-уровень: touch → правка target → возвращает ТОТ ЖЕ ID, **usage_count не сброшен** (на реальном пути точное значение usage маскируется touch инстант-TM-lookup'а приложения — потому юнит-гейт) |
| S2 | подтверждение без правки через путь записи: ID тот же, строка одна |
| S5 | concordance: старый target не находится, новый находится; FTS rowid = сохранённый ID |
| S4 | две записываемые TM: каждая хранит СВОЙ ID после правки, target в обеих обновлён |
| S6/S6f | импорт TMX «как раньше»: 2 варианта → 2 строки; повторный импорт пары → usage+1, ID те же; импорт same-target пары в TM с overwrite-записью → 1 строка, ID жив; новый target → добавляется вариант |
| S7 | legacy-дубли: после подтверждения 1 строка, ID из числа прежних; новый target по дублям → 1 строка, ID прежний, текст новый |
| S8 | удаление → подтверждение: новая запись с новым ID; запись в другой TM не тронута |
| S9 | режим «all»: другой target добавляет вариант (2 строки), совпадающий — upsert; семантика не изменена |

### 3.2. Что проверено только статически (честно)

- Код-ревью факта, что upsert-ветка (режим «all», `overwrite=False`) и
  batch-писатель не изменены (diff затрагивает только overwrite-ветку) —
  статически + покрыто S9/S6 динамикой.
- Триггеры `tu_fts_update`/`tu_trig_update` читаются напрямую в DDL;
  динамическое подтверждение — S5/R8 (concordance + прямой FTS MATCH).
- `update_entry` (TM Editor) не вызывался динамически в этом сьюте — он не
  менялся (строки 2212–2263) и уже был in-place.

### 3.3. Батарея защиты

Статическая (run-001/battery/static_tm4.log):

| Метрика | Было (защита) | Стало |
|---|---|---|
| py_compile CANONICAL | 116/0 | **116/0** |
| py_compile REFERENCE | 323/0 | **325/0** (+2 = audit-файлы TM3.1, закоммиченные после базового замера; дрейф, не ошибка) |
| pyflakes (canonical, 99 файлов) | 517 | **517** |
| AST startup-chain | 876/0 | **876/0** |
| AST tracked .py | 323/323 | **325/325** |
| headless imports | 98 ok / 1 fail (setup.py, известный) | **98 ok / 1 fail** (тот же) |
| importsmoke | 16/16 | **16/16** (новых tracked-модулей нет) |
| smoke (batch8-13) | 40 OK, exit=0 | **exit=0** |

Динамическая (run-001/battery/dynamic_tm4.log, TAG=tm4) — см. §3.4 ниже.

### 3.4. Полная динамическая батарея

Финальный прогон (`run-001/battery/dynamic_tm4_final.log`, TAG=tm4; все 25
этапов exit=0). Первый прогон дал 2 harness-сбоя (см. ниже) — исправлены,
перепрогон полный.

| Этап | Результат |
|---|---|
| static: py_compile canonical/reference | **116/116 fail=0 / 325/325 fail=0** |
| static: pyflakes (canonical, 99 файлов) | **517** (защита: 517; без изменений) |
| static: AST startup-chain | **876/0** |
| static: AST parse всех tracked .py | **325/325 fail=0** |
| static: headless imports (batch8-13) | **98 ok / 1 fail** (setup.py — известный артефакт) |
| static: importsmoke | **16/16 OK** (новых tracked-модулей нет — packaging_helper не трогался) |
| smoke (batch8-13, 40 items) | exit=0 |
| c1 / c2 / c3 / c11 | **33 / 75 / 86 / 15** — exit=0 |
| i1 / i2 | **94 / 39** — exit=0 |
| tbl1 / tbl12 / charact | **109 / 70 / 24** — exit=0 |
| t2 (double-write / quickedit / faulthandler) | **31 / 10 / 12** — exit=0 |
| tm1 recon + suite | exit=0, **8/8** |
| tm1_1 recon + integrity suite | exit=0, **6/6** |
| tm3 suite | exit=0, **45/45** |
| tm31 suite | exit=0, **28/28** |
| tm2 recon + suite | exit=0, **39/39**, TIMING wrap_500=0.233s < 1 c |
| tm4 recon («до»-измерение на после-коде) | exit=0, **13/17 reproduced** — NOT-REPRODUCED ровно 4 симптома (R1 ID, R1 created, R2, R4-оба-ID) = правка работает; остальные 13 — штатные контракты |
| tm4 suite | exit=0, **34/34 PASS** |
| regress common | exit=0; sha: simple_txt **5a12501f934a589c**, docx **44828d90090f046d**, tmx **c413d56372e69dd9** — эталоны |
| regress termbase | **REGRESS-TB OK** |
| e2e (fake endpoint, 5 сценариев) | verdict **OK**, aggregate **982e72a247f0a6ac** == эталон (user_len 3109/652/68/1254/9 — без изменений) |

Harness-сбои первого прогона (оба — дефекты прогонщика, не кода):
1. regress exit=1 — свежий stage не содержал предсидованных
   `stage-regress/inputs/` (известная ловушка TM2: «regress_common требует
   fixtures»; в tm31-батарее файлы оставались от прежних прогонов). В
   battery_dynamic.sh добавлен сид `cp $FIX/test.* → stage-regress/inputs/`.
2. tm4 suite exit=139 (segfault) ПОСЛЕ вердикта «PASS 34, FAIL 0» — гонка
   Qt-teardown (pynput-поток горячих клавиш) на выходе; сьют переведён на
   `os._exit` после вердикта (как recon). На логику не влияет.

---

## 4. sha256 изменённых файлов

| Файл | до (HEAD 7da9f08a) blob LF / рабочая копия | стало blob LF (коммит) / рабочая копия |
|---|---|---|
| `modules/database_manager.py` | **e4072e67**… / e4072e67… (3365 строк) | **7fba2c18**… / 7fba2c18… (3408 строк; файл LF — блоб = рабочая копия) |
| `docs/refactoring/audits/tm4_recon_before.py` | — (новый) | **7e245142**… / 7e245142… (435 строк) |
| `docs/refactoring/audits/tm4_inplace_tests.py` | — (новый) | **05f83c39**… / 05f83c39… (488 строк) |
| `PROJECT_STATUS.md` | c1f9db85… (блоб, 776 строк) | см. коммит 3 (+параграф TM4, 779 строк) |

`Supervertaler.py` — НЕ менялся: рабочая копия CRLF **92148004**…
(55309 строк), блоб LF **89b036d0**… (55309) — совпадает с защитой промпта.
`modules/tm_manager_qt.py` — НЕ менялся: **efab8bbe**… (1963 строка) —
совпадает с защитой промпта.

---

## 5. Коммиты

1. `3167cc83` — BATCH TM4 recon-before: `docs/refactoring/audits/tm4_recon_before.py`
   (17/17 CONFIRMED на до-коде, код выхода 0 — измерение);
2. `386f7400` — BATCH TM4: правка overwrite-ветки `add_translation_unit` —
   `modules/database_manager.py` (+46/−3);
3. (этот коммит) — BATCH TM4: `docs/refactoring/audits/tm4_inplace_tests.py`,
   отчёт, PROJECT_STATUS.

Локально на базе 7da9f08a (push-record TM3+TM3.1). **Пуша нет** — по
промпту: «Пуша нет. Стоп до вердикта».

---

## 6. Что НЕ делалось (по промпту)

- Схема БД, столбцы, индексы — не менялись (in-place UPDATE ложится в
  текущую схему).
- Browse All, TM Editor, TMX Editor — не тронуты.
- Семантика импорта — не менялась (покрыта S6/S6f «как раньше»).
- Существующие записи не конвертировались/не чистились: дубли в старых БД
  сворачиваются только при следующей overwrite-записи этого source в эту TM
  (то же, что делал старый DELETE, но с сохранением одного ID).
- Пуш не выполнен.
- Вне батча: «4в», C4, дрейф языка, TBL.

Замечание разведки для отдельного решения: `TMXImportThread`
(modules/tm_manager_qt.py:86) передаёт `add_translation_unit` несуществующий
параметр `save_mode='all'` → этот фоновый импорт TMX всегда падает с
TypeError (ловится, импорт не выполняется). Рабочий путь импорта —
`load_tmx_file`. Не чинено («заодно» запрещено), требует решения Дмитрия.

---

## 7. Ручная проверка для Дмитрия (T-TM4a–f)

Сборка: `D:\Supervertaler_clean` (код попадает туда при следующем обновлении
билда по решению Дмитрия; файлы копирует Дмитрий). Путь к просмотру записей:
вкладка **TMs → подвкладка Browse All**. Сверять ТЕКСТ записей, а не только
числа. Настройка по умолчанию «Save only latest translation (overwrite)» —
не менять (все тесты на ней; T-TM4f дополнительно проверяет импорт).

**T-TM4a — правка перевода сохраняет ID записи (обязательный).**
1. Цель: подтверждение исправленного перевода не создаёт новую запись TM,
   а обновляет существующую.
2. Шаги: открыть любой проект с TM с включённым флажком Write; подтвердить
   сегмент (Ctrl и Enter); перейти в TMs → Browse All, найти запись по слову
   из source, записать её ID и текст; вернуться в сетку, исправить перевод
   (хотя бы одно слово), снова Ctrl и Enter; открыть Browse All и найти
   запись по тому же source.
3. Ожидаемый результат: запись **одна** (не две), ID **тот же**, текст в
   Target — новый. В журнале строка «💾 TM entry #N updated in place (TM: …)».
4. Провал: другой ID, либо две записи с одним source, либо старый текст.

**T-TM4b — поиск видит новый перевод и не видит старый (обязательный).**
1. Цель: после правки поиск не находит старый текст и находит новый.
2. Шаги: сразу после T-TM4a в строке поиска Browse All ввести слово из
   СТАРОГО перевода → очистить → ввести слово из НОВОГО перевода.
3. Ожидаемый результат: старое слово — «ничего не найдено»; новое слово —
   запись находится (одна).
4. Провал: находится запись со старым текстом, либо новая запись не
   находится.

**T-TM4c — повторное подтверждение без правок ничего не дублирует
(обязательный).**
1. Цель: Ctrl+Enter на уже подтверждённом сегменте (без правки) ничего не
   меняет в TM.
2. Шаги: подтвердить сегмент, открыть Browse All (записать ID), вернуться,
   нажать Ctrl+Enter ещё раз БЕЗ правки перевода, снова открыть Browse All.
3. Ожидаемый результат: запись одна, ID тот же, текст тот же.
4. Провал: вторая запись, другой ID.

**T-TM4d — две активные TM хранят свои записи (обязательный).**
1. Цель: при двух записываемых TM каждая обновляет свою запись, у каждой
   свой ID.
2. Шаги: в списке TM включить флажок Write у двух TM; подтвердить сегмент;
   в Browse All (фильтр по конкретной TM) найти записи в обеих TM, записать
   их ID; исправить перевод, снова Ctrl и Enter; посмотреть Browse All в
   обеих TM.
3. Ожидаемый результат: в каждой TM по одной записи с тем же ID, что был;
   текст в обеих обновился.
4. Провал: в какой-то TM две записи или другой ID.

**T-TM4e — удалённая запись и повторное подтверждение (обязательный).**
1. Цель: удаление записи и повторное подтверждение создают новую запись с
   новым ID — это правильно.
2. Шаги: подтвердить сегмент; в Browse All выделить его запись и удалить
   (Delete); убедиться, что записи нет; вернуться и снова Ctrl+Enter.
3. Ожидаемый результат: запись появляется снова с ДРУГИМ ID (нормально).
4. Провал: запись не появилась.

**T-TM4f — импорт TMX ведёт себя как раньше (обязательный).**
1. Цель: импорт TMX не изменился: варианты сохраняются, совпадающие записи
   не дублируются.
2. Шаги: импортировать небольшой TMX (2+ пары) в TM; импортировать его ещё
   раз; затем перевести сегмент, source которого совпадает с парой из TMX,
   и подтвердить его.
3. Ожидаемый результат: после двойного импорта — по одной записи на пару
   (не по две); после подтверждения сегмента запись из TMX для того же
   source обновилась на месте (ID пары из TMX сохраняется, текст стал
   переводом сегмента).
4. Провал: дубли после повторного импорта; либо импорт «съел» запись TMX.

---

## 8. Справка (по запросу промпта, работ не выполнялось)

- **«4в micro-batch»** — не реализованный кандидат из BATCH C3 (§4в отчёта):
  уменьшение частоты эха промта на коротких source — при
  `len(source) <= N` (N≈60 знаков) ограничить окно surrounding-контекста до
  1 соседа (или 0). Меняет байты промта → e2e-агрегат 982e72a247f0a6ac и
  байт-точные эталоны c1/c2 потребуют согласованного обновления; делается
  отдельным микробатчем, не «заодно». Рекомендация C3: вариант «короткий
  source → окно 1».
- **T-C6/T-C7/T-C8** — три ОБЯЗАТЕЛЬНЫХ ручных теста из BATCH C3 (срезание
  остатков промта), ждут Дмитрия на D:\Supervertaler_clean (подмена
  Supervertaler.py из репозитория, модель index-nailong-9b): T-C6 — обрывки
  каркаса («ВАШ ПЕРЕВОД…», «8.», «[ПЕРЕВЕСТИ ЭТО]») срезаются из перевода с
  журнальной строкой «removed prompt artefact(s)»; T-C7 — экспорт Tagged
  Text предупреждает о возможном переливе контекста и остатках разметки
  промта, не блокируя файл; T-C8 — обычные переводы (нумерованные пункты,
  «[sic]») не задеваются (нет ложных срабатываний).
