# Batch U1.4b — Upstream-sync, Этап 2: страница настроек Segmentation Rules

Репозиторий: `dcdlab-ai/SupervertalerPortable`. База апстрима v1.10.371, цель v1.10.372
(`a58572276b4fced9384cf64580237c9edee75007`), общей git-истории нет; перенесённый
коммит **763291e8** («Segmentation Rules: user-definable SRX-style rules, and a
segmenter that never drops text», #191). Ядро перенесено в U1.4a (кодовый коммит
`5c052c9d`), настоящий батч завершает перенос 763291e8: страница настроек.

---

## 0. Baseline и git-синхронизация

| Проверка | Результат |
|---|---|
| `git fetch origin` / `git fetch upstream --tags` | OK, без изменений |
| HEAD == origin/main | `239a56e53575b62e9d83a20c0b704cce93320224` |
| `git status` | чисто (только untracked `.zcode/plans/…` — план предыдущей сессии, к батчу не относится) |
| `git log --oneline -6` | `239a56e5`, `c462b21e`, `5c052c9d` (U1.4a), `ed4587e1`, `34512e70`, `2e258269` |
| `5c052c9d` в origin/main | да (запушено после подтверждения Дмитрия) |
| Дрейф-чек `git merge-base --is-ancestor 5c052c9d HEAD` | PASS (предок) |
| `git rev-parse v1.10.372^{commit}` | `a5857227…` — совпадает с ожиданием |
| `git cat-file -t 763291e8` | commit |
| `wc -l Supervertaler.py` (до) | 68 392 |
| SHA256 `Supervertaler.py` (до) | `28b862e80e654c214ab904dc779d0c669c8da972f1e84e444d1c45ce9631f9c6` |
| `py_compile` монолит + `modules/**/*.py` (до) | 137/137 OK |
| EOL (до) | `i/lf w/lf` для `Supervertaler.py` |

Stage-каталог: `D:\Temp\SupervertalerPortable\refactoring\u1-port5\`.

## 1. Аудит (Этап 1 ТЗ)

### 1.1. Остаток коммита 763291e8

`git diff --stat 763291e8^ 763291e8`: 7 файлов, +1056/−271.
В `Supervertaler.py` — 16 хунков (снапшот `u1-port4/mono_763.diff`). Статус каждого:

| Хунк(и) | Метод/место | Статус |
|---|---|---|
| `modules/models.py` (+1: `join_before`) | `Segment` | перенесено в U1.4a |
| `modules/simple_segmenter.py`, `segmentation_rules.py`, `segment_split_merge.py`, `tests/…` | ядро | перенесено в U1.4a (`segment_split_merge` — дельта только 763, без 34a4c661) |
| #1 | `Segment.join_before` | перенесено в U1.4a (комментарий переведён — допустимо) |
| #2 | `add_source_text_to_project` (контекст `ssm.split_source_text`) | **вне объёма, постоянно**: `grep -n "ssm.split_source_text" Supervertaler.py` в HEAD — 0 вхождений; код из 34a4c661 (класс D) не переносился, хунк применяется к несуществующему в Portable контексту |
| #3 | `create_segmentation_rules_tab` + `test_segmentation_rules` → фабрика + `_load/_save/_make` | `_load_segmentation_rules` и `_make_sentence_segmenter` — U1.4a; **этот батч**: фабрика + `_save_segmentation_rules` + удаление `test_segmentation_rules` |
| #4–#16 | `new_project`, `import_simple_txt`, `import_folder_multifile`, `_import_multifile_project`, `export_simple_txt`, `_export_file_as_txt`, тултипы | перенесено в U1.4a (сверка сигнальных строк против HEAD) |

После U1.4b неперенесёнными остаются **только** хунк #2 (вне объёма по ТЗ) и
`CHANGELOG.md` (+30 — вне объёма: в разрешённых файлах батча только виджет,
монолит и docs; Portable CHANGELOG не ведёт — расхождение фиксировалось ещё в Stage 1).

### 1.2. Зависимости виджета

`modules/segmentation_rules_widget.py` в 371..372 трогает только 763291e8
(`git log --oneline v1.10.371..v1.10.372 -- <path>`), blob в теге
`60c55579016685d71c051b469de200b6d9501796` == blob в 763291e8. В Portable файла нет.
Перенос — ЦЕЛИКОМ из тега (пункт 1.2 ТЗ « whole-file»).

AST-аудит (`widget_audit.py`, 380 строк): класс `SegmentationRulesWidget(QWidget)`;
импорты — stdlib (`re`, `typing`), PyQt6, `modules.segmentation_rules`
(`Rule`, `SegmentationRules`, `build_srx`, `parse_abbreviations`, `parse_srx`, `rule_error`),
`modules.simple_segmenter.SimpleSegmenter`, `modules.styled_widgets.CheckmarkCheckBox`.
**Обращений к главному окну нет**: `load`/`save` — колбэки-параметры конструктора,
ни одного `self.parent()`/`main_window.<attr>`/`self.log`/`self.tr`.
Все импорты разрешаются в Portable: `styled_widgets.CheckmarkCheckBox` (класс есть),
все символы `segmentation_rules` (перенесены в U1.4a), `SimpleSegmenter(rules=None)`
(U1.4a). СТОП-условий нет.

### 1.3. Старая заглушка и её замена

В HEAD до батча: `create_segmentation_rules_tab` — заглушка (монолит:15307, RU-docstring
«Создаёт вкладку управления правилами сегментации.»), `test_segmentation_rules` — :15397.
Единственная регистрация вкладки — монолит:20681
(`seg_tab = self.create_segmentation_rules_tab()` → `addTab(scroll_area_wrapper(seg_tab), …)`,
регистрация коммитом не менялась). `test_segmentation_rules` ссылался только из
заглушки (`test_btn.clicked.connect`, :15376); других ссылок в монолите и `modules/` нет.
Апстрим: заглушка заменена фабрикой на 6 строк, `test_segmentation_rules` **удален**.
Решение — ровно по апстриму (см. §2); висящих ссылок после замены нет
(`grep -c test_segmentation_rules` по HEAD-монолиту = 0).

### 1.4. Диагностика ошибки «'tuple' object has no attribute 'strip'» (T4.7)

**Вывод: предсуществующая, не регрессия U1.4a.** Устранима самим U1.4b — кнопка
принадлежала заглушке и удалена вместе с ней.

- (а) Код заглушки (HEAD до батча, монолит:15397–15445):
  `paragraphs = [(0, text)]` → `segmenter.segment_paragraphs(paragraphs)` →
  `for i, (para_id, segment_text) in enumerate(segments, 1)`.
- Корень: `SimpleSegmenter.segment_paragraphs(self, paragraphs: List[str])`
  (`modules/simple_segmenter.py:140-156`) вызывает `paragraph.strip()` (:149 в HEAD,
  :104 в 2e258269) — а заглушка передаёт список **кортежей** `(0, text)`.
  `AttributeError: 'tuple' object has no attribute 'strip'` ловится собственным
  `except Exception` заглушки и показывается в `QMessageBox.critical` — то самое окно.
- (б) Побайтовое совпадение до/после U1.4a: `test_segmentation_rules` SHA256
  `c883c6aeeb1d6261…` в 2e258269 и HEAD — идентичны; `segment_paragraphs` —
  `ce1fd995792f2ace…` в обоих. (AST `get_source_segment` + sha256.)
- (в) Headless: `SimpleSegmenter().segment_paragraphs([(0, sample)])` на копиях
  `modules` из 2e258269 и из HEAD (`u1-port5/diag/`) — **одинаковый**
  `AttributeError('tuple' object has no attribute 'strip')` в обоих деревьях.
  Апстрим-сравка: в 763291e8 `segment_paragraphs` не менялся (signature-дифф
  API U1.4a: «preserved»), т.е. у апстрима до его же правки заглушка падала так же.

### 1.5. Сохранение настроек

`_save_segmentation_rules` (763291e8, 5 строк):
`settings = self.load_general_settings(); settings[SETTINGS_KEY] = rules.to_dict();
self.save_general_settings(settings)` — читает **весь** словарь секции general,
заменяет один ключ, пишет всё обратно.

В Portable: `load_general_settings` (монолит:44603, чтение `_load_general_settings_from_file`
+ синхронизация атрибутов) и `save_general_settings` (монолит:44972 — тонкий делегат
`SettingsService.save_general_settings`, `modules/settings_service.py:216` →
`_save_settings_section("general")`, try/except с `self.log`).

Ключ `segmentation_rules` (= `SETTINGS_KEY`) переживает:
- «Save General Settings»: `_save_general_settings_from_ui` (монолит:26657) —
  `existing_settings = self.load_general_settings()` (:26712) →
  `general_settings = dict(existing_settings)` (:26719) → `.update({…})` только
  своих ключей → `save_general_settings(general_settings)`. Ключ сохраняется.
- «Save AI Settings»: `_save_ai_settings_from_ui` (монолит:26429) пишет секцию LLM
  (`load_llm_settings`/`save_llm_settings`, :26476–26496) и provider states —
  general-ключи не затрагивает.
- Вызовов `save_general_settings()` без аргументов: 0 (grep по монолиту и
  `modules/`), guard сохраняется и после батча.

### 1.6. Некорректные правила

- Движок (`modules/segmentation_rules.py`): `compile_rule` бросает `ValueError`
  при пустых «Before» и «After» одновременно («Enter a pattern before or after
  the break.») и при `re.error` (например «missing ), unterminated subpattern»);
  `compile_rules` молча пропускает невалидные включённые правила — сегментация
  никогда не падает из-за правила.
- Виджет: `_validate()` (по каждому изменению) — `rule_error()` для включённых
  правил; невалидные строки красятся `_ERROR_BACKGROUND` + tooltip «⚠ …»,
  `status_label` показывает «⚠ N rules with an unusable pattern …».
- Тест-бокс `_refresh_test` — try/except: ошибка выводится строкой «⚠ …» в список.
- SRX-импорт: считает невалидные правила и пишет «N of them use a pattern
  Supervertaler cannot read and are ignored (marked in red)».
- Кнопки Save на странице нет — каждое изменение немедленно сохраняется через
  `_changed()` → `_save(self.rules())` (в апстримном info-тексте так и заявлено:
  «Changes apply immediately – there's no Save button on this tab.»).

### 1.7. Критерий приёмки: инициалы «J. R. R.»

Подтверждены headless-прогоном (`u1-port5/recipe_p7.py`) **два** апстримных механизма:

| Механизм | Ввод в UI | Результат |
|---|---|---|
| **Доп. сокращения (рекомендуемый)** | «Extra abbreviations»: `j, r` | `['J. R. R. Tolkien wrote the book.', 'It was long.']` — 2 сегмента |
| **Правило-исключение (no-break)** | «➕ Exception»: Before `[A-Z]\.`, After `\s` | тот же результат (2 сегмента) |

Механика: `extra_abbreviations` попадают в `never_break_after`
(`SimpleSegmenter.__init__`), builtin-правило для слова из списка даёт
`(m.end(), False, False)` — не режет. `parse_abbreviations("j, r")` → `['j', 'r']`
(точка после сокращения подразумевается, регистр не важен — word сравнивается
в `.lower()`). Одиночные буквы принимаются: `word = "J"` → `"j"`.
Правило-исключение работает через `decided.setdefault`: кастомные правила
проверяются **до** builtin и первый совпавший решает (`_split_line`).
**Формат JSON ключа `rules`: логическое поле называется `break`** (не `is_break`) —
`Rule.to_dict/from_dict`; при первом прогоне из-за этого рецепт B «не сработал»
(правило молча игнорировалось как невалидное по смыслу) — поправлено в аудите.

Guard на тех же правилах: `Mr. Jones went home. He slept.` → 2 сегм.;
`Dr. Smith arrived. Later, e.g. yesterday, it rained. Really?!` → 3 сегм.;
`The U.S.A. is great. What about this... and that? End of test.` → 3 сегм. — не сломались.
Lossless: `segment_with_separators` rebuild == исходная строка для обоих наборов правил.

Граница: рецепт через Extra abbreviations добавляет буквы **глобально** (любая «J.»
в тексте перестанет резать) — это апстримная семантика, кастомного кода нет.

## 2. Что сделано

Кодовый коммит **`426a09e2`** «U1.4b upstream-sync: Settings page Segmentation Rules
(editor, SRX import/export, test box) from v1.10.372 763291e8».

| SHA апстрима | Файл | Способ | Изменение |
|---|---|---|---|
| 763291e8 (=v1.10.372, blob `60c55579`) | `modules/segmentation_rules_widget.py` | `git checkout v1.10.372 -- <path>`, ЦЕЛИКОМ | новый, 380 строк; staged blob == тегу (проверено `git ls-files -s`) |
| 763291e8 хунк #3 | `Supervertaler.py` | по именам методов, вербатим из диффа | `create_segmentation_rules_tab`: заглушка (89 строк) → фабрика (6 строк); `test_segmentation_rules` (49 строк) удалён; `_save_segmentation_rules` (5 строк) вставлен после `_load_segmentation_rules` |

Итог в классе `SupervertalerQt`: `create_segmentation_rules_tab`, `_load_segmentation_rules`,
`_save_segmentation_rules`, `_make_sentence_segmenter` — в порядке апстрима.
Монолит: 68 392 → 68 265 строк. Снапшоты удаляемых блоков с sha256:
`u1-port5/snapshots/stub_create_tab.py` (89 строк, `a43f36dc828d6f90…`),
`stub_test_rules.py` (49 строк, `c883c6aeeb1d6261…` — совпадает с хэшем п. 1.4).

## 3. Диффы методов монолита до/после

AST-сверка (`ast.get_source_segment`) HEAD-монолита против `763291e8:Supervertaler.py`:

| Метод | HEAD == 763291e8 |
|---|---|
| `create_segmentation_rules_tab` | **True** (побайтно) |
| `_load_segmentation_rules` (U1.4a) | **True** |
| `_save_segmentation_rules` | **True** |
| `_make_sentence_segmenter` (U1.4a) | **True** |
| `test_segmentation_rules` | отсутствует в обоих |

Переведённых docstring в перенесённых методах нет — тела совпали целиком.
Вставка выполнялась скриптом по якорям `def create_segmentation_rules_tab` /
`def _load_segmentation_rules` / `def _make_sentence_segmenter` с
assert-проверками региона (что заменяется именно заглушка), затем py_compile.

`git diff --stat 239a56e5 426a09e2`: только `Supervertaler.py` (+12/−139) и
`modules/segmentation_rules_widget.py` (+380). Посторонних файлов нет.
EOL после: `i/lf w/lf` у обоих файлов.

## 4. Статическая и headless-валидация

| Проверка | До | После |
|---|---|---|
| `py_compile` монолит + modules | 137/137 | **138/138** (+виджет) |
| `wc -l Supervertaler.py` | 68 392 | 68 265 |
| SHA256 `Supervertaler.py` | `28b862e8…` | `5080fd5b4e6a5bdd58cc5b2a45f4d8c248578ec20c6eb1eae006dbc455d573d2` |
| SHA256 `segmentation_rules_widget.py` | — | `eeefbccb78b3d4fcd02f4ef4602a33ae24c7b350d38cbb623de0ed72ffcdf3f4` |
| Ссылок на `test_segmentation_rules` | 2 (def + connect) | **0** |
| Вызовов `save_general_settings()` без аргументов | 0 | 0 |
| Тесты апстрима `tests/test_segmentation_rules.py` (pytest, repo-sim junction) | — | **12/12 passed** |
| Изолированный smoke виджета (offscreen, заглушка окна, dict-store, без user_data) `smoke_widget.py` | — | **27/27 PASS** |
| Защита настроек `settings_safety.py` | — | **5/5 PASS** |
| Рецепт инициалов + lossless `recipe_p7.py`, `make_testdata.py` | — | PASS |

Smoke-сценарий (все PASS): пустые настройки → дефолт; тест-бокс на дефолте 5 сегментов
(J./R./R. — воспроизводит наблюдение T4.5); «j, r» → 2 сегмента и живое сохранение в
store; добавление правила-исключения программно (без модалок) → сохранено; перезагрузка
в новый инстанс → всё на месте, round-trip равен; экспорт SRX во временный файл →
сброс (очистка поля, удаление строк) → store пуст → импорт → правило восстановлено;
два невалидных правила («(` и пустое) → оба помечены движком, `status_label` «⚠»,
тест-бокс и движок продолжают работать (невалидные пропускаются); lossless rebuild.
Monkeypatch: `QMessageBox.*` (записаны 2 вызова: Export/Import information),
`QFileDialog.getSaveFileName/getOpenFileName` → временные пути. Примечание: первые 3
«FAIL» первого прогона были багами самого харнеса (нумерованные строки тест-бокса
«1. J. …» и неочищенный store перед третьим инстансом) — исправлен харнес, не код.

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База: последний кодовый коммит U1.4a `5c052c9d` (docs-коммиты `c462b21e`, `239a56e5`
допустимы и присутствуют). Заменить поверх сборки только:

| № | Путь | SHA256 | Примечание |
|---|---|---|---|
| 1 | `modules/segmentation_rules_widget.py` | `eeefbccb78b3d4fcd02f4ef4602a33ae24c7b350d38cbb623de0ed72ffcdf3f4` | новый файл |
| 2 | `Supervertaler.py` | `5080fd5b4e6a5bdd58cc5b2a45f4d8c248578ec20c6eb1eae006dbc455d573d2` | −139/+12 строк против базы |

Больше ни один файл не менялся. Тестовые данные: `D:\Temp\SupervertalerPortable\refactoring\u1-port5\testdata\`
— `sample_initials.txt` (LF, SHA256 см. ниже), `expected_default.md`, `expected_with_rule.md`,
`srx_roundtrip.md`.

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data тестовой сборки)

Сначала КОНТРОЛЬ на базовой сборке (без файлов U1.4b), затем после замены файлов.

### 6.1. Результаты ручной проверки (Дмитрий, тестовая сборка поверх U1.1–U1.4a)

T5.1 страница — **ОК**; T5.2 рецепт инициалов — **ОК**; T5.3 сохранение — **ОК**;
T5.4 тест-бокс — **ОК**; T5.5 SRX — **ОК**; T5.6 некорректное правило и сброс —
**ОК**; T5.7 регрессия — **ОК**; T5.8 дымовой — **ОК**. Замечаний нет.
По контролю T5.1 (воспроизведение ошибки «'tuple' …» на базовой сборке живьём):
ошибка наблюдалась в T4.7 на сборке с U1.4a и на более ранних сборках, а
предсуществование доказано статически и headless (§1.4) — живой контроль на
базовой сборке не гонялся и не нужен. Push — по команде Дмитрия.

- **T5.1 Страница.** Контроль: Settings → Segmentation Rules — заглушка; кнопка
  «🧪 Test Segmentation» → окно с ошибкой «'tuple' object has no attribute 'strip'»
  (воспроизведение T4.7). После замены: открывается редактор правил (Options /
  Custom rules / Test); исключений в консоли нет; старой кнопки больше нет.
- **T5.2 Рецепт инициалов.** Extra abbreviations: `j, r, c, s` → закрыть страницу
  (сохраняется мгновенно) → Import a plain-text file → `testdata/sample_initials.txt`
  с галочкой «Split lines into sentences» → разбиение == `expected_with_rule.md`;
  «J. R. R. Tolkien wrote the book.» — один сегмент. Контроль на базовой сборке:
  разбиение == `expected_default.md` (инициалы режут).
- **T5.3 Сохранение.** Закрыть и открыть приложение → правила на месте; в
  `settings.json` секции general есть ключ `segmentation_rules`; изменить два
  значения на General Settings → Save → ключ `segmentation_rules` и остальные
  настройки на месте. «Сброс»: очистить сокращения, удалить правила из таблицы
  (кнопки Reset в апстриме нет — см. §7), вернуть галочки → ключ соответствует
  дефолту.
- **T5.4 Тест-бокс.** Ввод текста → сегменты обновляются «живьём» при вводе и
  при смене правил (нумерованный список).
- **T5.5 SRX.** По `testdata/srx_roundtrip.md`: экспорт → сброс → импорт → правила
  совпадают. Опционально.
- **T5.6 Некорректное правило и сброс.** Ввести Before = `(` → строка краснеет,
  tooltip с описанием, надпись «⚠ 1 rule with an unusable pattern…»; приложение
  не падает; тест-бокс продолжает работать. После очистки/сброса импорт SRX и
  импорт TXT работают как в U1.4a (`expected_default.md`).
- **T5.7 Регрессия.** Импорт TXT/MD с дефолтными правилами — поведение U1.4a
  (в т.ч. разбиение «J. R. R. Tolkien wrote the book.» на J. / R. / R. / предложение —
  это апстримный дефолт, меняется только рецептом из T5.2); split/merge сегментов
  в гриде работает (`join_before`/`segment_split_merge` не менялись в этом батче).
- **T5.8 Дымовой.** Приложение стартует; все страницы Settings открываются без
  исключений.

## 7. Непокрытые проверки (честно)

1. **Приложение целиком не запускалось** (ограничение ТЗ): T5.1–T5.8 не выполнялись
   автоматикой; страница проверена изолированным smoke с заглушкой главного окна
   (реальный `self._load_segmentation_rules`/`_save_segmentation_rules` монолита
   не вызывались — их логика проверена отдельно симуляцией dict-логики).
2. **Scroll-обёртка**: в smoke виджет инстанцировался напрямую, без
   `scroll_area_wrapper()` и реального QTabWidget — визуальная вписываемость в
   Settings-диалог не проверялась.
3. **SRX от OmegaT** (реальные файлы пользователей) не прогонялись — только
   round-trip собственного экспорта (12/12 тестов апстрима покрывают parse/build,
   включая Java-regex-переводы, но не конкретные файлы OmegaT).
4. **Кнопки Reset в виджете нет** (апстримное поведение): сценарий «сброс правил»
   в T5.3 — ручная очистка; если Дмитрий ожидает кнопку Reset — это запрос на
   изменение апстримного кода (вне правил батча).
5. **Скриншоты/шрифты**: offscreen-рендер без font directory — пиксельную
   вёрстку страницы не оценивали.
6. **`CHANGELOG.md`** апстрима (+30 в 763291e8) не переносился — вне разрешённых
   файлов батча.
7. **QFontDatabase warning** при offscreen-прогоне — окружение embedded Python,
   к коду отношения не имеет.

## 8. Вопросы к Дмитрию

1. **Push**: жду подтверждения на `426a09e2` (код) + docs-коммит отчёта.
   Статус: ручная проверка пройдена (§6.1, 8/8 ОК); push подтверждён Дмитрием
   после правок отчёта (см. ниже).
2. **Рецепт для вашей сборки**: рекомендуемый способ — «Extra abbreviations»
   (например `j, r, c, s`). Правило-исключение Before `[A-Z]\.` / After `\s`
   **не рекомендовано**: в нём нет границы слова, поэтому оно срабатывает и на
   конце любого слова в заглавных («NATO.», «NASA.») и на «I.» («so did I. He
   left»), и предложения слипнутся. Список Extra abbreviations надёжнее — он
   сравнивает слово целиком, а регистр не учитывает. Но он глобальный: не
   добавлять одиночные «a» и «i» (концы предложений вроде «Plan A.»).
3. **T5.1 контроль**: закрыт — см. §6.1: ошибка наблюдалась в T4.7 на сборке с
   U1.4a и раньше, предсуществование доказано статически и headless (§1.4);
   живой контроль на базовой сборке не нужен.
4. **Кнопка Reset**: не нужна — пустые поля и так дают дефолт. Reset как кнопка —
   отдельное решение вне правил переноса.
