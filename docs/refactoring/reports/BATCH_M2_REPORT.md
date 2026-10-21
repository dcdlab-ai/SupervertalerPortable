# ОТЧЁТ Batch M2 — link-only во всех LLM-путях, видимые ошибки, NBSP

Дата: 2026-10-21. Промт: BATCH M2 (Дмитрий). Основа: `4ed68bc0` (G3.2g).
Пуш **не выполнялся**; коммиты локальные. Стоп до вердикта.

Содержание: M2.1 (link-only в оставшихся LLM/MT-путях), M2.2 (видимые ошибки LLM:
чип + консоль AutoTagger), M2.3 (NBSP в пакетном прогресс-хендлере).

---

## 1. Коммиты

| Коммит | Содержание | Монолит | sha256 (Supervertaler.py) |
|---|---|---|---|
| `5da1858d` | M2.1 — link-only гейты (a,c,d,e) | 55342 → 55392 (+60/−10) | `cb96fad3c38e57325eb2007981db11263df0e147abaafc1916f7b8ad9e6bfe7f` |
| `93815bca` | M2.2 — видимые ошибки (чип + консоль AutoTagger) | 55392 → 55439 (+49/−2) | `ed22121b048f5065e62584e0a36b695438742e604e3179905052ab011db51506` |
| `abb6e086` | M2.3 (NBSP-обёртка) + M2.2(b) follow-through | 55439 → 55456 (+17/−0) | `65d50655727e5568642e86d68edaf823d0c32f0a45a79a7c918d1ceaca87d1c7` |

Итог по батчу: `git diff 4ed68bc0..HEAD` — **1 файл** (`Supervertaler.py`), **+126/−12**.
Ни один модуль не изменён (см. §2). `modules/settings_service.py` (CRLF-артефакт, «M»)
не коммитился — по правилу промта. `.zcodeignore`, файл плана сессии не коммитились.

## 2. Файловый пакет (manifest: sha256 + строки + EOL)

Инструмент: `docs/refactoring/audits/batch-m2_manifest.py` (92 файла: монолит + `modules/**/*.py`).
Снимки: `batch-m2_manifest_base.json` (база 4ed68bc0), `_m21`, `_m22`, `_m2post` (HEAD).

Сравнение base → HEAD: **отличается ровно 1 запись из 92** — `Supervertaler.py`:

| Состояние | sha256 | строк | CRLF | bare-LF |
|---|---|---|---|---|
| База 4ed68bc0 | `42a6d41b49740d4319f34113f4f6aba4ac243e3e9009b94d8992680130f76c4c` | 55342 | 55342 | 0 |
| HEAD abb6e086 | `65d50655727e5568642e86d68edaf823d0c32f0a45a79a7c918d1ceaca87d1c7` | 55456 | 55456 | 0 |

CRLF-режим монолита сохранён (bare-LF 0 на всех трёх замерах); модули (LF) не тронуты.
py_compile: 0 ошибок после каждой правки (финальный замер сессии: `PYCOMPILE_0`).

## 3. M2.1 — карта путей (file:line на HEAD; решение по каждому пути)

Общий инструмент — **существующий** `is_image_links_only`
(`modules/bilingual_markdown_handler.py:412`); новых детекторов нет. Единые правила
(как M1): target = source дословно, status **draft**, TM-запись отсутствует
(во всех пробах `tu_delta = 0`), лог
`⤳ Segment #N: link-only segment skipped — LLM not called, source copied to target (draft)`
(для MT — «MT engine not called»).

| Путь (поз. промта) | Место (HEAD) | До батча | После батча | Проба |
|---|---|---|---|---|
| (a) FuzzyFixer bulk pass `_run_fuzzy_fixer_llm` | `Supervertaler.py:5879` (def), гейт 5897–5899, импорт 5884, тег 5913 | link-only сегменты уходили в LLM как обычные | гейт per-segment: LLM не вызывается, слот = source, тег `⤳ link-only (LLM skipped)` | S3 (2 обычных запроса, link-only скопирован) |
| (b) AutoTagger bulk `autotag_segments_bulk` | def 50077; фильтр 50094–50095; гейт воркера `_run_autotag_only:6012`, линия 6024 «⊘ no tags / no target» | link-only **уже покрывался** существующим фильтром вызывающего: `autotag_extract_tags(s.source)` даёт нуль тегов из markdown-картинок → сегмент отсеивается до вызова LLM | **код не изменён** — существующие проверки не дублируются (решение по промту «существующие проверки не дублировать, отметить в отчёте») | S4 (1 запрос, link-only строка нетронута), S4b |
| (c) MT pre-translate `PreTranslationWorker.run()` MT-цикл | 5392–5400 (гейт), тег 5413 | MT-движок вызывался на link-only | гейт: вызов MT пропускается, слот = source, тег `⤳ link-only (MT skipped)` | S5 (1 MT-запрос, link-only скопирован) |
| (d) Proofreading `_run_proofreading` | def 39180; фильтр 39186–39197 | link-only попадали во множество сегментов и вычитывались | исключение из `segments_to_check` (индексы строк сохраняются — `proofreading_notes` адресуются по строке), лог `⤳ N link-only segment(s) excluded from proofreading (not sent to LLM)`; всё-из-link-only → инфо «No Segments» + выход | S6 (payload без `fig.png`, лог) |
| (e) Main package — падение всего LLM-батча | `run()` except-обработчик батча 5491–5513 | при ошибке батча **все** сегменты помечались `✗ BATCH ERROR`, link-only не получали draft (известный крайний случай M1 §5) | link-only слоты копируются в target (draft, undo) несмотря на ошибку LLM; остальные — как раньше `✗ BATCH ERROR` | S2 (endpoint 500: link-only draft, остальные пустые с ошибкой) |

Существующий гейт M1 (успешный батч) — `run()` 5686–5699 (импорт 5686, `link_only_ids`
5699) — **не дублировался**, не изменён; используется как есть. Одиночный Ctrl+T гейт
(`translate_current_segment`, def 49022; гейт 49051–49052) — из M1, не тронут.

## 4. M2.2 — видимые ошибки

**(a) Чип LLM-панели** — `_fetch_llm_translation_async` (def 51021), except-блок
51136–51176: `LLMTruncatedError / LLMEmptyResponseError / LLMTimeoutError`
(modules/llm_clients.py) пишутся однострочным текстом в LLM-чип панели результатов:
`TranslationMatch(target=<текст ошибки>, relevance=0, metadata llm_error=<имя класса>,
match_type='LLM', provider_code='CUS')` во все `results_panels`; текст сворачивается в
одну строку и ограничивается 140 знаками; подсказка «Increase 'Max tokens'» для
усечения сохраняется из текста исключения. Модалок нет (в пробе `modal_delta 0`).
Запись чипа выполняется только при выбранной той же строке и при наличии панелей —
иначе тихий лог. Прочие исключения — прежнее тихое поведение
(`LLM translation failed (silent)`). Остальная часть метода не изменена.

**(b) AutoTagger bulk** — `translation_error.connect` в `autotag_segments_bulk`
50176–50178: линия консоли прогресс-диалога `❌ AutoTagger: …` (паттерн main package)
+ app-log `❌ AutoTagger batch failed: …`. Источник эмита — `_autotag_segment_llm`
(def 5972): follow-through commit `abb6e086` (см. журнал вопросов Q2): линия 6002
(`reason` содержит «LLM error» — place_tags_via_llm проглатывает ошибки вызова) и
6009 (ветка except). Проба S4b: консоль `❌ AutoTagger: AutoTagger on #…` + app-log.

Прочие безмолвные места BACKLOG §9.10 **не тронуты** (по промту).

**Находка (вне объёма, не исправлялось):** шлюз успеха чипа 51099
`if translation and hasattr(self, 'assistance_widget') and self.assistance_widget:` —
`assistance_widget` нигде не присваивается (тот же узор 51207, 39930, 40560):
успешный LLM-перевод **никогда не попадал в чип** — дефект предшествует M2 и к M2
отношения не имеет (M2.2(a) пишет чип через `results_panels`, который жив). В BACKLOG.

## 5. M2.3 — NBSP в пакетном прогресс-хендлере

**Механизм (доказан пробой S0, чистый Qt, offscreen):**
1. `QTextEdit.toPlainText()` нормализует NBSP (U+00A0) → обычный пробел;
2. `setPlainText()` без блокировки сигналов синхронно порождает `textChanged`;
3. обработчик сетки `on_target_text_changed` (Supervertaler.py:33028) получает
   нормализованный текст; идемпотентный шлюз (`new_text == old_target → return`)
   не срабатывает (текст отличается от хранимого) и **пишет нормализованный текст
   обратно в `segment.target`** — NBSP молча вырезается из каждого сегмента,
   переведённого пакетом.

**Воспроизведение базы:** проба на worktree 4ed68bc0 (`run-regress`): target
`'Trans lated1'` (NBSP потерян), строка 4 `'![Image](y.png) '` (NBSP → пробел);
на 93815bca (`run-pre`) воспроизводится.

**Фикс (commit abb6e086, минимальный вариант по Q7 промта):** `handle_progress_update`
(вложенная функция в `show_batch_progress`, def 50913), блок 50930–50943: запись ячейки
цели обёрнута в `blockSignals(True) / setPlainText(display_text) / blockSignals(False)`
(50941–50943) — тот же узор виджета, что M1 link-only гейт и `copy_source_to_target_bulk`.
`apply_invisible_replacements` (modules/grid/filters.py:701) **не изменялся**: NBSP
остаётся сырым в модели (Camp B, подсветка TagHighlighter). Обоснование минимальности:
проба S0 — без обёртки `textChanged` срабатывает синхронно, с обёрткой — 0 срабатываний
после pump; задержка событий (комментарий виджета 3222) не проявляется.

**Доказательство после фикса** (`run-post`, `run-post2`, `run-post3`, S1): model-targets
`'Trans\xa0lated1'`, `'Trans\xa0lated3'`, `'![Image](y.png)\xa0'` — NBSP **сохранён**
(виджет по-прежнему отображает нормализованный текст — это поведение Qt-отображения,
модель корректна).

**Места с той же проблемой (перечислены, НЕ исправлялись — по промту):** 14 участков
`setPlainText` в ячейку цели без блокировки сигналов —
7519/7523 (`show_mt_quick_popup`), 26008 (`on_match_inserted`),
35785 (`_insert_quicktrans_translation`), 40524 (`search_and_display_tm_matches`),
41302 (`insert_term_translation`), 45770 (`copy_source_to_grid_target`),
46251 (`_replace_current_target_segment_text`), 46787 (`_check_auto_confirm_100_percent`),
46974 (`_auto_propagate_to_identical`), 49167/49336 (`translate_current_segment`,
включая успех Ctrl+T), 49595 (`autotag_current_segment`), 51970 (`_auto_insert_tm_match`).

## 6. Проба-матрица (фейковый loopback-эндпоинт + сетевая ловушка)

Инструмент: `docs/refactoring/audits/batch-m2_probe_matrix.py`
(аргументы: tree, run-dir, sections-csv; изолированный профиль в run-dir/iso,
ThreadingHTTPServer на 127.0.0.1, ловушка `socket.connect` на не-loopback,
стабы QDialog.exec/QMessageBox/QFileDialog, перехват `LiveProgressDialog.add_console_line`,
pump processEvents). JSON результата пишется в `probe_m2.json`.

Прогоны: `run-regress` (база 4ed68bc0 через worktree), `run-pre` (93815bca, до M2.3),
`run-post`, `run-post2` (после M2.3), `run-s7` (только чип, после починки обёртки
перехвата), **`run-post3` — чистый полный прогон: 39/39 PASS, ловушки `[]`**.

| Секция | Что проверяется | Итог (run-post3) |
|---|---|---|
| S0 (3) | Qt-нормализация NBSP; хендлер срабатывает без блокировки; с обёрткой — молчит | PASS |
| S1 (7) | пакет 4 строк (2 link-only): 1 запрос, ids=[1,3]; NBSP в target (model); link-only = source; все draft; 2 линии `⤳` в консоли; TM-запись 0 | PASS |
| S2 (5) | endpoint 500 весь батч: все запросы mode=fail (внутренние ретраи llm_clients учтены); link-only скопирован (draft); обычные — пусто/ошибка; консоли `⤳`×1 + `✗ BATCH ERROR`×2; TM 0 | PASS |
| S3 (5) | FuzzyFixer-включён (атрибут после импорта настроек): только 2 запроса (обычные); link-only скопирован; обычная строка переведена; 1 линия `⤳`; TM 0 | PASS |
| S4 (3) | AutoTagger bulk (tagged+link-only, targets пресеты): только 1 запрос (tagged); link-only строка нетронута; TM 0 | PASS |
| S4b (2) | AutoTagger bulk, endpoint 500: консоль `❌ AutoTagger: AutoTagger on #…`; app-log линия | PASS |
| S5 (5) | MT pre-translate (Custom MT профиль, raw_mode): 1 MT-запрос; link-only скопирован (draft); обычная строка переведена MT; 1 линия `⤳`; TM 0 | PASS |
| S6 (3) | Proofreading: 1 запрос; payload **без** link-only (`fig.png` отсутствует); лог «excluded from proofreading» | PASS |
| S7 (5) | Усечение ответа (finish_reason='length'): 1 запрос; чип панели содержит текст ошибки (`metadata llm_error = LLMTruncatedError`), подсказка «Max tokens» в тексте чипа, **0 модалок**, лог `⚠ LLM translation failed (shown in LLM chip)` | PASS |
| S8 (1) | Сетевая ловушка пуста | PASS |

**Регрессия тел запросов:** `req-00.json` прогона базы (`run-regress`), `run-pre`
и `run-post3` — **байтово идентичны**: sha256
`25b6402b4ac5a10c56a2fbde5654246104711cfc54cccc314cc6991eeb752719`, 3844 байта
(артефакты `batch-m2_payload_regress.json`, `_pre`, `_post3`). Тела запросов M2
не изменились относительно 4ed68bc0.

Замечания методики: (1) llm_clients делает внутренние HTTP-ретраи на 500, поэтому
S2/S4b проверяют режим каждого запроса, а не количество==1; единственность прохода
приложения доказана линиями консоли. (2) `fuzzy_fixer_enabled` сбрасывается импортом
настроек — выставляется после импорта окна. (3) Обёртка перехвата `set_matches` —
атрибут экземпляра: сигнатура **без** `self` (иначе TypeError проглатывается
внутренним try продукта).

## 7. Защиты

**Статика** (`docs/refactoring/audits/g5_12_static.py`, логи `batch-m2_static_base.log`
— база 4ed68bc0, `batch-m2_static_m2post.log` — HEAD):

| Метрика | База | HEAD |
|---|---|---|
| цепочка connect/QShortcut/QTimer (grep) | 883 / 0 потерь | 883 / 0 |
| pyflakes | 548 (126 / 4) | 548 (126 / 4) |
| py_compile канон (вне docs/) | 109 / 0 ошибок | 109 / 0 |
| py_compile справочный (с скриптами) | 208 / 0 | 208 / 0 |
| headless-инструменты | 90 / 2 (известные setuptools/fitz) | 90 / 2 |
| grep-гейт | CLEAN | CLEAN |

Замеры идентичны базовой линии; py_compile 0 после каждой правки.
Статика **после** 16-stage suite (`batch-m2_static_m2final.log`): все числовые строки
идентичны базлайну (отличаются только tag-заголовки секций) — chain 883/0,
pyflakes 548 (126/4), канон py_compile 109/0, справочный 208/0, headless 90/2, grep CLEAN.
(Метод-заметка подтверждена: статика гоняется **после** suite — `kill_leftovers` убивает все
python-embed процессы.)

**16-stage offscreen suite** (`docs/refactoring/audits/batch-m2_run_full.sh m2`,
kill_leftovers — только PID по command line / ExecutablePath, никогда по имени образа;
логи — `batch-m2_*` в audits). **Итог: 16/16 зелёная.**

| Стадия | Итог |
|---|---|
| fallback (9.4h) | PROBE DONE, S5 OK True |
| profiles (9.4f) | EXEC OK True, ACTIVE UNCHANGED True |
| qtchat | CHAT WIDGET True, menu actions в норме |
| statusbar (prof) | LOCAL-LLM NOTE OK, PROBE DONE |
| e2e (9.3) | старт приложения 21 LOG-линия, идентичен базлайну g32e (хвот: hotkeys registered) |
| S-clean | PROBE OK (4.9s) |
| S-upgrade | PROBE OK (5.2s), HASH-DIFF: added=[] removed=[] changed=[], transient=['…/ai_assistant/index.json'] (известный транзиент §4) |
| regress | RESULTS: import_txt 5 / export_simple_txt `5a12501f934a589c` / import_md 5 / import_docx 4 / export_docx `44828d90090f046d` / export_tmx `c413d56372e69dd9` — **байтово идентичны g32e**; MODAL-ATTEMPTS 4 (штатные стабы). Первичный запуск упал (FileNotFoundError) — харнесс требует засеянных `iso/+inputs/` (метод-заметка G3.2e); досеяно из g32e-фикстур, повторный запуск зелёный |
| smoke (канон 8.13, 42 элемента) | SMOKE OK (13.6s), 41 no-exception + известный fitz (PDF-Rescue); QMenu-джиттер §9.11 — не регрессия |
| termbase | REGRESS-TB OK (12.5s), MODAL-ATTEMPTS [] |
| about | RESULT OK (диалог собран) |
| save modern / save legacy | PROBE DONE, все позиции OK |
| r9 a / ctrl / rm | RESULT OK ×3 (резуррекция удалённого профиля отсутствует) |

## 8. Ручные тесты T-M2.x (для Дмитрия)

Модель/сервер: Custom (OpenAI-compatible) профиль с эндпоинтом; для MT — Custom MT
профиль; для усечения — в профиле `max_tokens` поставить маленькое значение (например
8). Логи смотреть: консоль прогресс-диалога пакета + журнал приложения.
Замечание: замороженная тестовая сборка `D:\SupervertalerPortable_test` батчами
**не обновляется** (AGENTS.md; пересборка — решение Дмитрия); тесты выполняются на
пересобранной сборке или на рабочей копии репозитория.

| № | Сценарий (шаг за шагом) | Что видеть |
|---|---|---|
| T-M2.1 | Импорт txt со строками: 2 обычные + 1 только `![Image](...)`. Пакетный перевод (LLM). | Link-only строка: target = source дословно, статус draft; консоль `⤳ Segment #N: link-only segment skipped — LLM not called…`; TM-запись по ней отсутствует |
| T-M2.2 | Настройки → wF enabled. Импорт смешанного txt, пакет. | Link-only скопирован, тег `⤳ link-only (LLM skipped)`; обычные переведены fuzzy-проходом |
| T-M2.3 | Активен Custom MT профиль. Импорт смешанного txt, пакет (провайдер MT). | Link-only: тег `⤳ link-only (MT skipped)`, draft, запрос к MT не шёл (журнал MT-движка) |
| T-M2.4 | Импорт txt с тегами `<n>` + link-only-строка, цели заполнены. Действие AutoTagger bulk. | Link-only строка не изменена; tagged-строки обработаны; ошибок LLM нет |
| T-M2.5 | Смешанный проект (link-only + обычные с целевым текстом), действие Proofreading. | Журнал: `⤳ N link-only segment(s) excluded from proofreading (not sent to LLM)`; только link-only-выборка → инфо «No Segments» |
| T-M2.6 | `max_tokens` мал (8). Выбрать строку, LLM-подсказка в панели (ассистент). | В чипе LLM панели текст усечения с подсказкой «Max tokens»; диалогов нет; журнал `⚠ LLM translation failed (shown in LLM chip)` |
| T-M2.7 | Эндпоинт выключен/500. Пакет смешанного проекта. | Link-only строки скопированы с тегом `⤳`; обычные `✗ BATCH ERROR: …` |
| T-M2.8 | Эндпоинт выключен/500. AutoTagger bulk по tagged-строкам. | Консоль `❌ AutoTagger: AutoTagger on #N: …` (красная линия) |
| T-M2.9 | Сервер отвечает с NBSP (или перевод строки, содержащей NBSP — вставить в source). Пакет. | После пакета в model-target NBSP сохранён: подсветка NBSP-маркера в ячейке (TagHighlighter) сохраняется, TM-поиск/автозамена находят NBSP-вариант, экспорт сохраняет NBSP (до фикса NBSP вырезался) |

## 9. Журнал вопросов

- **Q1 (M2.1(b), AutoTagger bulk):** новых гейтов не потребовалось — существующий
  фильтр вызывающего 50094–50095 (`autotag_extract_tags` даёт нуль тегов на markdown-картинках)
  + гейт воркера 6024 покрывают link-only (проба S4). Отмечено в карте путей, код не дублирован.
- **Q2 (M2.2(b)):** `place_tags_via_llm` (modules/tag_manager.py:1417) проглатывает
  ошибки LLM-вызова в `(None, reason)`, поэтому ветка except `_autotag_segment_llm`
  (коммит 93815bca) на отказе эндпоинта не срабатывает. Применён follow-through
  (commit abb6e086, линия 6002) в духе «заполнять translation_error по существующему
  паттерну». Проба S4b подтвердила видимость.
- **Q3:** мёртвый шлюз успеха чипа `assistance_widget` (51099) — дефект predates M2,
  не тронут; материал в BACKLOG (см. §4).
- **Q4:** 14 мест сетки с той же NBSP-экспозицией перечислены (§5), не исправлялись —
  по промту.
- **Q5 (методика пробы):** внутренние ретраи llm_clients на 500 (S2/S4b), сброс
  `fuzzy_fixer_enabled` импортом (S3), сигнатура перехвата без `self` (S7) — учтены
  в харнеcе, зафиксированы в §6.
- **Q6 (runner suite):** шапка `batch-m2_run_full.sh` — косметическая правка
  (строка 3 без «#» после sed-ремонта) исправлена в этом батче.
- **Q7 (regress-стадия suite):** первичный прогон упал на `stage-regress/iso/Desktop`
  (FileNotFoundError) — харнесс `batch8-15_regress_common.py` на свежем stage требует
  предсозданных `iso/` и `inputs/` (метод-заметка G3.2e подтверждена). Досеяно: `iso/`
  создан, `inputs/` скопированы из g32e-фикстур (sha-сверка). Повторный прогон зелёный,
  хеши байтово идентичны. Правка харнесса/фикстур — не код продукта.

## 10. Не тронуто / вне объёма

- Все модули (`modules/**`) — байтово идентичны базе (manifest-диф 1/92).
- Безмолвные места BACKLOG §9.10 кроме двух указанных (чип, AutoTagger) — не тронуты.
- Одиночный Ctrl+T / autotag_single / TM- и quicktrans-записи (14 мест NBSP) — не тронуты.
- `modules/settings_service.py` — не коммитился (CRLF-артефакт).
- Тестовая сборка не пересобиралась.
- **Пуш не выполнялся.** Коммиты локальные: 5da1858d, 93815bca, abb6e086 (+ финальный
  коммит отчёта/артефактов/PROJECT_STATUS). Стоп до вердикта координатора.
