# BATCH TM5 — импорт TMX в TM: разведка и починка очевидных дефектов

**Статус: выполнено (агент, 2026-11-21). Ждёт вердикта Дмитрия. Пуша нет.**
База: origin/main = `75213147` (TM4 запушен), HEAD = `70526b67` (push-record
TM4). `75213147` — предок HEAD (проверено `git merge-base --is-ancestor` до
первого чтения кода). Локальный push-record TM4 (`70526b67`) ждёт следующего
пуша вместе с коммитами этого батча.

Батч выполнен по исходному промпту и **дополнению Дмитрия** (нашёл баг в
зоне батча — исправляю сразу, отдельным коммитом, с тестом до/после и
строкой в таблице): в итоге исправлено **8 багов** (исходные 1.1/1.2 + 6
найденных разведкой на пути «импорт TMX → запись в БД → совпадение в
Editor»), каждый отдельным коммитом.

---

## 1. Разведка (задача 0) — `docs/refactoring/audits/tm5_recon_import.py`

Recon «до» на изолированном профиле, реальные кнопочные пути
(лог: `run-001/out/recon_before3.log`, факты: `run-002`/`run-001` JSON в
stage). **13/13 симптомов/эталонов воспроизведено** (чистый прогон на
ДО-коде; первые два прогона были замусорены: неочищенный iso-профиль
сталкивал tm_id — повторено на чистом; в первом прогоне R6 был артефакт
харнесса, исправлен в коммитнутом скрипте).

### 1.1. Карта путей импорта TMX (0.1) — все с номерами строк

| # | Путь из UI | Код | Движок импорта | Достижим | Состояние до батча |
|---|---|---|---|---|---|
| 1 | Вкладка 💡 TMs → кнопка **«📥 Import TMX»** | Supervertaler.py:11293–11295 → `_import_tmx_as_tm` (18245) | `_load_tmx_into_db` (translation_memory.py:539) → `add_translation_units_batch` (upsert) | ДА | Работает; режим «создать TM» не активировал TM (галка Read off) |
| 2 | Вкладка TMs → **«✏️ Edit/Maintain TM»** → вкладка «📥 Import/Export» → **«📂 Select and Import TMX...»** | Supervertaler.py:18775 → `TMEditorDialog` (tm_editor_dialog.py:74) → `TMManagerDialog.import_tmx` (tm_manager_qt.py:1600) → `TMXImportThread` (tm_manager_qt.py:32) | `add_translation_unit` построчно | ДА | Падал с TypeError («Import failed») |
| 3 | Superlookup → правый клик → «Open in TM browser» → TM Manager → та же вкладка Import/Export | Supervertaler.py:53947 → `show_tm_manager_tab` (10373) | тот же `TMXImportThread` | ДА (через concordance) | Тот же TypeError |
| 4 | Tools → «✏️ TMX Editor...» (Supervertaler.py:8240) | `tmx_editor_qt.py` | собственная БД TMX-файлов (`tmx_files`), НЕ `translation_units` | ДА | Не путь импорта в TM — вне батча |
| 5 | File → Import | Supervertaler.py:7673+ | — | — | Пункта импорта TMX нет |
| 6 | `import_tmx_file` (Supervertaler.py:11414), `load_tmx_file` (translation_memory.py:506), `load_from_tmx` (translation_memory.py:840) | — | — | **МЁРТВЫЙ КОД**: ни один не подключён к UI | Описан, не тронут |

Примечание (расхождение путей, исправлено фикс-ом F): TM Editor встраивает
вкладку Import/Export из `TMManagerDialog`, но поле «TM ID:» оставалось
«imported» (а не редактируемая TM), а `parent_app` оставался диалогом —
языковая пара импорта всегда была en→de (жёсткий дефолт), и при
`current_project is None` `import_tmx` падал AttributeError.

### 1.2. TMXImportThread: достижимость и последствия (0.2)

Достижим двумя путями (№2 и №3 в таблице). До батча:
- **TypeError на первой же записи**: `add_translation_unit(…, save_mode='all')`
  (tm_manager_qt.py:86) — параметра `save_mode` нет (есть `overwrite: bool`).
  Исключение ловится (tm_manager_qt.py:88–89) → `finished(False, "Import
  failed: DatabaseManager.add_translation_unit() got an unexpected keyword
  argument 'save_mode'")` → QMessageBox «Import Failed».
- **БД после падения чистая**: 0 записей, TM-метаданных не создаётся
  (recon R3: ref-интактно, `imported`-TM нет) — падение происходит ДО
  любого доступа к БД.

### 1.3. «Успешный» двойной импорт без дублей (0.3)

Дмитрий пользовался путём №1 («📥 Import TMX»): он и в режиме «создать»,
и в режиме «добавить» пишет через `_load_tmx_into_db` →
`add_translation_units_batch` (database_manager.py:1148+), а там upsert
`ON CONFLICT(source_hash, target_text, tm_id) DO UPDATE SET usage_count+1`.
Повторный импорт того же файла → совпадение хэшей → обновление на месте,
дублей нет (recon R5: 3→3 записи, ID те же, usage подрос). Это штатное
поведение, сохранено.

### 1.4. Механизм галки Read (0.4)

- Состояние галки: `tm_metadata_mgr.is_tm_active(tm['id'], project_id)`
  (Supervertaler.py:11107) по таблице `tm_activation (tm_db_id, project_id,
  is_active)`; нет записи → неактивно. Без проекта project_id=0 (глобальная).
- «+ Create New TM» (Supervertaler.py:11285–11291 → `_show_create_tm_dialog`
  18120): после `create_tm` вызывает `activate_tm(result, project_id)`
  (18196–18197) — поэтому галка ставится сама.
- «📥 Import TMX» → «Create new TM from this TMX» вызывал только `create_tm`
  (18536–18543) — без активации. **Это корень симптома 2.**
- Клик по галке: `activate_tm/deactivate_tm` + `invalidate_translation_cache`
  (Supervertaler.py:11124–11138).
- Write: у обоих путей `create_tm` с дефолтом `read_only=False` → Write-галка
  отображается включённой одинаково; правка не требовалась.

### 1.5. Цепочка «запись в БД → совпадение в Editor» (0.5)

Реальные пути показа совпадений:
1. **Точный instant-путь на клик** `_show_instant_tm_match`
   (Supervertaler.py:51286+): `get_exact_match(source, tm_ids=…)` — список
   TM берёт из **снапшота** `current_project.tm_settings['activated_tm_ids']`
   (51303–51306); пустой список → отказ, отсутствующий ключ → поиск везде.
2. **Фоновая предзагрузка** `_prefetch_worker_run` (27720+): свой
   SQL-запрос активных TM по `tm_activation` (27748–27753) → кэш
   `translation_matches_cache` → рендер панели.
3. **`search_and_display_tm_matches`** (40470): `get_active_tm_ids()` из БД +
   `tm_database.search_all(source, tm_ids=…)`. Ветка панели (40610)
   недостижима — см. «найдено, но не исправлено» №1.
4. **F5/ручной ре-поиск** (42806) — тоже снапшот.

Фильтры поиска: точный — `source_hash IN (4 варианта)` + `tm_id IN (список)`
+ языки через `get_lang_match_variants` / `LIKE 'en-%'`
(database_manager.py:1210+); нечёткий — FTS5, тот же фильтр tm_ids и языков.
**Нормализация языков при импорте** (`_load_tmx_into_db`):
`get_simple_lang_code` — `en-US` сохраняется как `en-US`, `EN`→`en`
(recon R1/R4: записаны (en-US, ru-RU) и (en, ru)); поиск по проекту `en → ru`
находит оба варианта (матчится базовый код + `en-%`). Языковая нормализация
**не** блокер.

**Почему «не видны вообще никак»**: импортированная TM без записи в
`tm_activation` не попадает в списки активных TM ни одного пути. Если в
проекте есть хотя бы одна активированная TM (у Дмитрия так), список непуст →
`search_all`/`get_exact_match` фильтруют по нему → импортированная TM
исключена. Если бы активных TM не было вовсе, `search_all` искал бы везде
(`tm_ids=[] → None`, translation_memory.py:212–214) — поэтому симптом
проявляется «при других активных TM».

Нюанс снапшота: `tm_settings['activated_tm_ids']` синхронизировался с БД
только при сохранении/загрузке проекта (28251–28254); `on_read_toggle` его
не обновлял, а dedup-guard `_instant_tm_guard` не сбрасывался нигде
(комментарий 51327 обещал сброс при TM refresh — кода сброса не было).
Исправлено фиксами D/E.

### 1.6. Таблица «симптом → причина → правится ли»

| Симптом | Причина (файл:строка) | Правится в этом батче |
|---|---|---|
| 1. Записи «не видны в Editor вообще» | Импорт-«создать TM» не активирует TM (Supervertaler.py:18536–18548 — нет `activate_tm`); плюс несвежие кэши (снапшот 28251–28254 / guard 51327 / toggle 11124) | ДА — фиксы C, D, E |
| 2. «+Create New TM» ставит Read, импорт — нет | То же: путь импорта пропускает `activate_tm`; механизм — `tm_activation` | ДА — фикс C (тот же механизм/ключ) |
| 3. Двойной импорт без дублей | upsert `ON CONFLICT(source_hash, target_text, tm_id)` в батч-вставке — штатное поведение | Эталон, сохранён (S5) |
| 4. TMXImportThread → «Import failed» | `save_mode='all'` (tm_manager_qt.py:86) → TypeError | ДА — фикс A |

Найдено дополнительно разведкой/прогонами на пути «импорт → БД → совпадение»
(исправлено по дополнению Дмитрия):

| # | Баг | Где | Фикс |
|---|---|---|---|
| B | Отказы phantom-TM guard считаются «импортированными»: поток не проверяет возврат `add_translation_unit` → «Successfully imported N entries» при 0 реальных записях | tm_manager_qt.py:80–104 | Честный счётчик + отказы в сообщении; полный отказ → success=False |
| F | TM Editor импортирует в «imported», а не в редактируемую TM; языковая пара en→de; AttributeError при `current_project=None` | tm_editor_dialog.py:74+, tm_manager_qt.py:1613 | Поле prefilled своей TM, `parent_app` = главное окно, защита от None-проекта |
| H | Поток пишет через GUI-соединение: «SQLite objects created in a thread…» на каждую запись (замаскировано фиксом A) | tm_manager_qt.py:44+ | Собственный writer-коннект DatabaseManager в потоке (паттерн TMCleanupThread), close в finally |
| G | Ложная подсказка «Activated TMs don't match project language»: `tm['id']` (int) ищется в списке tm_id-строк → всегда False | Supervertaler.py:40521 | Сравнение `tm['tm_id']` |
| D | Кэши после переключения Read: `_instant_tm_guard` не сбрасывается никогда (комментарий обещал), снапшот `tm_settings` не обновляется в `on_read_toggle` | Supervertaler.py:28158+, 11136+ | Сброс guard в полной инвалидации + пересчёт снапшота в toggle |
| E | После активации при импорте снапшот/кэши не обновляются — instant-путь не видит новую TM до сохранения проекта | Supervertaler.py (_import_tmx_as_tm) | Пересчёт снапшота + `invalidate_translation_cache` в момент импорта |

---

## 2. Правки (задача 1 + дополнение) — серия коммитов

Каждый фикс — отдельный коммит (по правилу Дмитрия); правки минимальные,
«чужой» код не тронут, схема БД не менялась, вызываемые функции
(`add_translation_unit`, `create_tm`, `activate_tm`) не менялись.

| Коммит | Фикс | Файл(ы) | Дельта |
|---|---|---|---|
| `181a5973` | recon-before (артефакт разведки) | docs/refactoring/audits/tm5_recon_import.py | +495 |
| `9380cbbb` | **A**: `save_mode='all'` → `overwrite=False` (та же семантика «all»: варианты не затираются, повторная пара — upsert) | modules/tm_manager_qt.py | +6/−1 |
| `87007d7e` | **B**: честный счётчик записей/отказов, `success=imported>0` | modules/tm_manager_qt.py | +17/−3 |
| `a6e890d6` | **F**: TM Editor импорт в свою TM + parent_app = главное окно + защита None-проекта | modules/tm_editor_dialog.py, modules/tm_manager_qt.py | +15/−2 (tm_editor_dialog +15/−2, tm_manager_qt +6/−1) |
| `ca66d0ad` | **C**: импорт-«создать TM» активирует TM (Read=on) как «+Create New TM» + англ. лог одной строкой `TM import: created TM '…' (…), Read=on` | Supervertaler.py | +15 |
| `5f4fbe74` | **D**: сброс `_instant_tm_guard` в `invalidate_translation_cache` (полная ветка) + пересчёт снапшота в `on_read_toggle` | Supervertaler.py | +19 |
| `1dad9c5e` | **E**: после активации при импорте — пересчёт снапшота + `invalidate_translation_cache(smart_invalidation=False)` | Supervertaler.py | +11 |
| `76afb6c3` | **G**: `tm['id']` → `tm['tm_id']` в языковой проверке подсказки | Supervertaler.py | +6/−1 |
| `f170bba5` | **H**: TMXImportThread пишет через собственный writer-коннект (WAL), close в finally | modules/tm_manager_qt.py | +33/−11 (реструктуризация run: тело под try/finally; в первой версии таблицы ошибочно стояло +58/−48 — оценка вместо замера, исправлено по предпуш-проверке Дмитрия) |

Монолит: 55 309 → **55 359** строк (нетто **+50**: фикс C +15, D +19,
E +11, G +6/−1 = +5). Схема БД не менялась; `database_manager.py` не
трогался. Новых UI-строк нет; новый лог — английский, одной строкой.

Исправление в ходе серии: первый вариант фикса F обращался к параметру
`parent` из `init_ui` (NameError, поймал recon-после) — исправление
`self._creator_window` вобрано в коммит F через `fixup`+`autosquash` до
каких-либо пушей (серия не пушится).

---

## 3. Тесты «до/после»

### 3.1. Recon «до» (13/13) и «после» (измерение)

| Сценарий | До | После | Комментарий |
|---|---|---|---|
| R0 +Create New TM: Read auto-ON | CONFIRMED | CONFIRMED | Эталон не изменился |
| R1 импорт-создать: записи записаны | CONFIRMED | CONFIRMED | |
| R1 СИМПТОМ 2: Read OFF | CONFIRMED | NOT-REPRODUCED (Read=on, галка стоит) | фикс C |
| R1 СИМПТОМ 1: Editor не находит | CONFIRMED | NOT-REPRODUCED (находит, instant=True) | фиксы C/D/E |
| R2 add-to-existing: записи добавлены | CONFIRMED | CONFIRMED | |
| R2 галки других TM не изменились | CONFIRMED | NOT-REPRODUCED (в после-коде обе TM Read=on — исходное состояние сценария другое; флаги не менялись) | |
| R3 СИМПТОМ 4: TypeError | CONFIRMED | NOT-REPRODUCED («Successfully imported 4 entries») | фиксы A/H |
| R3 «БД чистая после падения» | CONFIRMED | NOT-REPRODUCED (записи теперь легли: 4) | ожидание специфично для ДО |
| R4 теги EN/ru → нормализация (en, ru) | CONFIRMED | CONFIRMED | |
| R5 дублей нет (эталон) | CONFIRMED | CONFIRMED | |
| R6 ручная Read: поиск находит (текст сверен) | CONFIRMED | CONFIRMED | |
| R6 instant после синхронизации | CONFIRMED | CONFIRMED | |
| R0 TM создана | CONFIRMED | CONFIRMED | |

Лог: `run-002/out/recon_after3.log` (после всех 8 фиксов).

### 3.2. Сьют — `docs/refactoring/audits/tm5_import_tests.py` — **23/23 PASS, exit 0**

| Проверка | Фикс(ы) |
|---|---|
| S7: «+Create New TM» — эталон (TM создана, Read auto-ON) | — (регресс) |
| S1: TM Editor импорт: поле prefilled, parent_app=win, БЕЗ TypeError, записи в редактируемой TM (3), языки пары проекта (en→ru, не en→de) | A, F, H |
| S2: phantom-TM отказ: success=False, сообщение с «refused … no_such_tm_zzz», БД без мусора | B |
| S3: импорт-«создать»: TM создана, 4 записи, Read СТОИТ САМ (как у +Create New TM), метаданные en-US/ru-RU | C |
| S4: поиск Editor находит импортированную пару СРАЗУ (текст TGT4 сверен), instant-путь находит БЕЗ сохранения проекта, снапшот обновлён в момент импорта | D, E |
| S5: повторный импорт — дублей нет, ID живы, usage вырос, тексты сверены | эталон |
| S6: «add to existing» не меняет галки других TM | регресс |
| S8a: битый TMX через «Import TMX» — без падения, TM не создаётся | регресс |
| S8b: пустой TMX через поток — «Import failed», БД без мусора | A, H |
| S9: Read off → instant не находит; Read on → находит снова (без сохранения) | D |
| S10: при пустом результате НЕТ ложной подсказки «don't match project language» | G |

Проводка: реальные кнопки («+ Create New TM», «📥 Import TMX», «📂 Select
and Import TMX...» в реальном `TMEditorDialog`), реальный поиск Editor
(`search_all` c активными TM + `_show_instant_tm_match`). Только статически:
нормализация языков `get_simple_lang_code` (проверено юнит-вызовом
`language_codes.canonical` в ходе разведки: EN→en, en-US сохраняется);
карта достижимости путей 5/6 (мёртвый код).

### 3.3. Батарея защиты

Статическая (`batch-tm5/battery/out/static_tm5_after.log`):

| Проверка | Было (защита) | Стало |
|---|---|---|
| py_compile CANONICAL | 116/0 | **116/0** |
| py_compile REFERENCE | 325 +2 (аудит-файлы TM4, см. примечание) | **328/328** на момент батареи → **329/329 подтверждено финальным замером** после коммита сьюта (4e56f2e6, дозамерено и довключено в тот же коммит amend-ом → итоговый хэш 00678eaf; +1 файл `tm5_import_tests.py`; лог `static_tm5_final.log`) |
| pyflakes (canonical, 99 файлов) | 517 | **517** |
| AST startup chain | 876/0 | **876/0** |
| AST parse tracked .py | 327 | **328/328** на момент батареи → 329/329 после коммита сьюта |
| headless imports | 98 ok / 1 fail (setup.py) | **98 ok / 1 fail** (тот же) |
| importsmoke | 16/16 | **16/16** (новых tracked-модулей нет) |

Примечание к REFERENCE: в промпте было «325 (+2 audit-файла TM5)». Фактический
базовый замер до правок дал **327** (два файла TM4 `tm4_recon_before.py` +
`tm4_inplace_tests.py` стали tracked после коммита 75213147 — дрейф, не
ошибка; TM4-батарея гонялась до их коммита). Дальше: +1 recon-коммит → 328,
+1 сьют в финальном коммите → 329. КАНОНИЧЕСКИЙ счётчик (вне docs/) не
меняется: 116/0.

Динамическая (`batch-tm5/battery/out/dynamic_tm5.log`, TAG=tm5; **все 28
шагов exit=0**):

| Шаг | Результат |
|---|---|
| smoke (batch8-13) | SMOKE OK |
| c1 / c2 / c3 / c11 | 33/0, 75/0, 86/0, 15/0 |
| i1 / i2 | 94/0, 39/0 |
| tbl1 / tbl12 / charact | 109/0, 70/0, 24/0 |
| t2 double-write / quickedit / faulthandler | 31/0, 10/0, 12/0 |
| tm1 recon + suite | OK, 8/8 |
| tm1_1 recon + suite | OK, 6/6 |
| tm2 (recon + suite) | 39/39 |
| tm3 suite | 45/45 |
| tm31 suite | 28/28 |
| tm4 recon + suite | 13/17 (измерение на после-коде, штатно), 34/34 |
| **tm5 recon + suite** | **7/13** (после-код: симптомы 1/2/4 сняты — см. §3.1), **23/23** |
| regress common | exit=0; sha: simple_txt **5a12501f934a589c**, docx **44828d90090f046d**, tmx **c413d56372e69dd9** — эталоны |
| regress termbase | REGRESS-TB OK |
| e2e (fake endpoint, 5 сценариев) | verdict **OK**, aggregate **982e72a247f0a6ac** == эталон (user_len 3109/652/68/1254/9 — без изменений) |

Известный урок сессии (повторён из TM4): перед каждым прогоном recon/сьюта
iso-профиль стирается (`rm -rf`) — неочищенный профиль сталкивал tm_id
(`_2`-суффиксы `create_tm`) и мусорил замеры; два первых прогона recon
переделаны на чистых профилях.

---

## 4. Таблица «было / стало / причина» (sha256)

| Файл | до | стало | причина |
|---|---|---|---|
| `Supervertaler.py` | рабочая CRLF `92148004…`, блоб LF `89b036d0…`, 55 309 строк | рабочая CRLF `7f62a6d8…`, блоб LF `cad2f7c4…`, **55 359 строк** (+50) | фиксы C (+15), D (+19), E (+11), G (+6/−1) |
| `modules/tm_manager_qt.py` | `efab8bbe…` (LF), 1963 строк | `3def997a…` (LF), 2009 строк (+46) | фиксы A (+6/−1), B (+17/−3), F (+6/−1), H (+33/−11); сумма нетто +5+14+5+22 = +46 — сходится с 2009−1963 |
| `modules/tm_editor_dialog.py` | `ed0bb688…` (LF), 99 строк | `9df0b257…` (LF), 112 строк (+13) | фикс F (+13) |
| `modules/database_manager.py` | `7fba2c18…`, 3408 строк | **без изменений** | правка не требовалась |
| `docs/refactoring/audits/tm5_recon_import.py` | — (новый) | блоб = рабочая копия | артефакт разведки |
| `docs/refactoring/audits/tm5_import_tests.py` | — (новый) | блоб = рабочая копия | сьют |
| `docs/refactoring/audits/fixtures/tm5_manual_test_en-ru.tmx` | — (новый) | блоб = рабочая копия | фикстура ручных тестов |

Полные sha256 — в журнале статики (`batch-tm5/battery/out/static_tm5_after.log`).

---

## 5. Найдено, но не исправлено (по требованию дополнения)

| # | Что найдено | Где | Почему не исправлено | Следующий шаг |
|---|---|---|---|---|
| 1 | Ветка панели в `search_and_display_tm_matches` мертва: `if hasattr(self.assistance_widget, 'set_matches')` (Supervertaler.py:40610) падает AttributeError — атрибут `assistance_widget` не создаётся нигде в коде (присваиваний нет). Функция каждый раз завершается логом «Error searching TM», fallback `tm_display` не отрисовывается; фактический показ совпадений обеспечивают другие пути (instant + prefetch-кэш) | Supervertaler.py:40610 | «Починить» guard = включить легаси-ветку отрисовки/панели — это решение о том, кто владеет показом TM-совпадений (риск дублирования рендера с instant/кэш-путями), выходит за рамки «очевидного локального бага» | Решение Дмитрия: удалить мёртвую ветку (оставить показ instant+кэшу) или вернуть легаси-отрисовку tm_display |
| 2 | Запрос активных TM в prefetch-воркере не повторяет global-fallback `get_active_tm_ids` (берёт только `ta.project_id = ? AND is_active=1`, без глобальных project_id=0 записей без проектной записи) — расхождение с заявленным «Mirrors TMMetadataManager.get_active_tm_ids()» | Supervertaler.py:27748–27753 vs tm_metadata_manager.py:401+ | На текущем потоке выполнения недостижимо: загрузка проекта пишет проектную is_active=0 запись для КАЖДОЙ TM (Supervertaler.py:26554–26556), затеняя глобальные; глобальные активации не имеют эффекта при открытом проекте | Если когда-нибудь изменится поведение «deactivate all at project load» — зеркалить fallback в запросе воркера |
| 3 | В `import_tmx` (TM Manager) движок — построчный `add_translation_unit` (отдельный commit на строку), в `_import_tmx_as_tm` — батч по 5000. На больших TMX путь потока существенно медленнее | tm_manager_qt.py (run) vs translation_memory.py:615+ | Смена движка = изменение производственной семантики/производительности импорта, не «очевидный локальный баг»; корректность обоих путей подтверждена тестами | Опционально: перевести поток на `add_translation_units_batch` (решение о унификации движков) |

---

## 6. Ручные тесты для Дмитрия (сборка D:\Supervertaler_clean)

Файл фикстуры (3 пары en→ru; теги en-US/ru-RU):
`E:\Dev\SupervertalerPortable\docs\refactoring\audits\fixtures\tm5_manual_test_en-ru.tmx` —
скопируй его куда удобно (например, на рабочий стол) перед тестами.

### T-TM5a: импорт TMX «создать базу» — TM с галкой Read
1. Открой Supervertaler (проект можно не открывать).
2. Перейди на вкладку **💡 TMs** (в левой панели ресурсов).
3. Нажми кнопку **«📥 Import TMX»** (внизу списка TM).
4. Выбери файл `tm5_manual_test_en-ru.tmx`.
5. В окне «Import TMX» оставь выбранной опцию **«Create new TM from this TMX»** → **Import**.
6. Введи имя, например `TMX Тест 1` → OK. Подтверди пару языков (Source: en-US, Target: ru-RU — уже выбраны) → OK.
- **Ожидается**: сообщение «TMX imported successfully … Entries imported: 3»; новая TM `TMX Тест 1` появилась в списке; в её строке колонка **Read** отмечена галкой **сама** (как у TM, созданной «+ Create New TM»); в журнале строка `TM import: created TM 'TMX Тест 1' (…), Read=on`.
- **Провал**: галка Read не стоит; сообщение об ошибке импорта.

### T-TM5b: импортированная пара видится в Editor
1. Открой проект (или создай новый: File → Import → Import Document... с любым файлом, или Text/Markdown файл), язык пары проекта — английский → русский.
2. Создай/вставь в проект сегмент с source-предложением из фикстуры, например: `The monthly report was approved by the board.`
   (готовый файл: тот же `tm5_manual_test_en-ru.tmx` содержит 3 таких предложения — можно взять текст из него).
3. Щёлкни в этот сегмент (в колонку Translation), посмотри панель совпадений справа.
- **Ожидается**: совпадение 100% из `TMX Тест 1` с переводом `Ежемесячный отчёт был утверждён советом директоров.` — **текст** совпадает с фикстурой. Если сегмент пустой и включён автоподбор — предложение подставится само.
- **Провал**: совпадения нет при стоящей галке Read (проверь в 💡 TMs, что Read у `TMX Тест 1` отмечен).

### T-TM5c: повторный импорт — без дублей
1. Повтори шаги T-TM5a, но в окне выбора режима выбери **«Add to existing TM»** и укажи `TMX Тест 1` в списке.
2. Открой `TMX Тест 1` → **«✏️ Edit/Maintain TM»** → вкладка «📖 Browse Entries».
- **Ожидается**: по-прежнему ровно 3 записи, тексты те же; дубликатов нет.
- **Провал**: записей стало 6.

### T-TM5d: импорт в другую TM не трогает галки
1. Создай вторую TM кнопкой **«+ Create New TM»** (имя `TMX Тест 2`, языки en → ru) — убедись, что её Read-галка стоит сама.
2. Сними галку Read у `TMX Тест 1` (клик по галке), затем импортируй тот же файл в `TMX Тест 2` (Import TMX → Add to existing TM → `TMX Тест 2`).
- **Ожидается**: записи добавились в `TMX Тест 2` (всего 6); галка `TMX Тест 1` осталась снятой, галка `TMX Тест 2` — стоящей.
- **Провал**: галки изменились сами.

### T-TM5e: «+ Create New TM» ведёт себя как прежде
1. Нажми **«+ Create New TM»**, создай TM `TMX Контрольная` (en → ru).
- **Ожидается**: TM создана, Read-галка стоит сама (поведение не изменилось).
- **Провал**: галка не стоит.

### T-TM5f: битый файл — внятная ошибка, без мусора
1. Создай текстовый файл `broken.tmx` с содержимым `<tmx version="1.4"><header srclang="en"/><body><tu><tuv><seg>unclosed` (сохрани как файл с расширением .tmx).
2. 💡 TMs → «📥 Import TMX» → выбери `broken.tmx` → Create new TM → введи имя → OK.
- **Ожидается**: окно «Invalid TMX» с текстом «TMX file must contain at least 2 languages…»; программа не падает; новой TM в списке НЕТ.
3. Дополнительно: 💡 TMs → выбери любую TM → «✏️ Edit/Maintain TM» → вкладка «📥 Import/Export» → «📂 Select and Import TMX...» → выбери ПУСТОЙ файл (создай пустой empty.tmx).
- **Ожидается**: окно «Import Failed» с текстом «Import failed: …»; программа работает; список записей TM не изменился.
- **Провал**: падение программы, мусорная TM в списке, «Successfully imported» для пустого файла.

Дополнительно (необязательно, покрыто сьютом S1): импорт из окна TM Editor
«✏️ Edit/Maintain TM» → «📂 Select and Import TMX...» теперь по умолчанию
пишет в ту TM, которая редактируется (поле «TM ID:» уже заполнено), и
использует языковую пару проекта.

---

## 7. Что НЕ делалось (по промпту)

- Привязка TM к проекту / выбор TM при создании проекта / «Set as Project TMs».
- Browse All (включая выделение текста и Delete), ядро записи TM4.
- Схема БД, чистка существующих записей.
- TMX Editor (отдельная БД TMX-файлов — не путь в translation_units).
- C4, дрейф языка, TBL, «4в».
- Пуш (ждёт вердикта).

---

## 8. Известные особенности, не являющиеся дефектами батча

- Активация при импорте живёт до следующей загрузки проекта, если проект не
  сохранить — **ровно как у «+ Create New TM»** (загрузка проекта
  восстанавливает активации из сохранённого снапшота, Supervertaler.py:26552+).
  Это штатная модель «активации на проект».
- Поле «TM ID:» в автономном окне TM Manager (открытом не из TM Editor)
  по-прежнему редактируемое с дефолтом «imported» — теперь отказ в
  несуществующий TM честно рапортуется (фикс B).
