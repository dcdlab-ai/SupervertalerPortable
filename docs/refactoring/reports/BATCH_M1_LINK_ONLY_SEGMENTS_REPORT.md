# BATCH M1 — Сегменты из одной md-ссылки не отправляются в LLM

Исполнитель: агент. Координатор: Дмитрий. Дата: 2026-10-19. Пуш не выполнялся (коммиты локальные).

## 0. Шаг 0 (среда)

- `git fetch origin`; `main` впереди origin/main на 1 коммит.
- HEAD до батча: `6dff2082` (docs-only O.0 поверх `9321764b`).
- `git diff 9321764b HEAD --stat`: только `AGENTS.md` (+16/−), `PROJECT_STATUS.md` (+2/−),
  `docs/refactoring/reports/RECON_O0_OCR_TOOL_REPORT.md` (+182) — кода продукта в diff нет.
- Незакоммиченный `modules/settings_service.py` — известный CRLF/LF-артефакт: не тронут, не коммитился.

## 1. Изменения по коммитам

| # | Коммит | Файлы | Изменение |
|---|--------|-------|-----------|
| M1a | `e902aaa1` | `modules/bilingual_markdown_handler.py` (+18), аудит-проба | Детектор `is_image_links_only(text)` + регулярка `_MD_IMAGE_LINK_ONLY_RE = ^\s*(?:!\[[^\]]*\]\([^)]*\)\s*)+$` (точная из промпта батча). Плюс проба-матрица 23 кейса → `docs/refactoring/audits/batch-m1_probe_detector.py` (+verdict json), 23/23 PASS |
| M1b | `9a56eb22` | `Supervertaler.py` (+38/−13) | Пакетный путь в `PreTranslationWorker` (см. §2) |
| M1c | `3062942d` | `Supervertaler.py` (+32) | Одиночный путь в `translate_current_segment` (см. §3) |
| M1d | (этот отчёт) | отчёт + проби-артефакты | — |

**Место детектора (задание п.1):** `modules/bilingual_markdown_handler.py`, сразу после
однородного shape-предиката `looks_like_bracketed_markdown` (~:391). Это модуль — владелец
md-синтаксиса (экспорт/импорт «[SEGMENT NNNN]») и в нём уже живут текстовые предикаты-«нюхалки»
(`looks_like_bracketed_markdown`, `iter_tag_tokens`, `structural_tag_count`); новый детектор —
ровно та же категория. Новый модуль не создавался. Импорт в воркере и в окне — локальный
`from modules.bilingual_markdown_handler import is_image_links_only` (модуль лёгкий, без Qt/PIL —
в фоновом потоке безопасен).

**Регулярка и границы (матрица пробы, 23/23 PASS, `batch-m1_probe_detector_verdict.json`):**
- True: одиночная ссылка; две подряд; через перевод строки; alt с ключевым словом (`![Figure 1]`);
  кириллица и пробелы в alt и пути (включая windows-пути с `\`); пустой alt `![](x.png)`;
  trailing-пробелы; `[url "title"]`.
- False: ссылка + текст (в т.ч. с новой строки); ссылка + точка после; обычная ссылка `[t](u)`;
  текст перед ссылками; пустой сегмент; только пробелы; `<img>`; `[img]`; url с внутренними
  скобками (за пределами спецификации — вне срабатывания).

## 2. Пакетный путь (M1b) — что изменено

`PreTranslationWorker._translate_batch_with_llm` (AST 5653–5847):
1. До формирования промпта сегменты делятся: `link_only_ids` (детектор по `seg.source`) и
   `send_segments` (всё остальное). Все места промпта, считавшие `batch_segments`
   (guard prompt_manager + `first_segment`, счётчики «(N segments)»/«ALL N», inline-tag скан,
   цикл сегментов `{seg.id}. {seg.source}`), переведены на `send_segments` — link-only сегменты
   в запрос не попадают.
2. Полностью link-only пакет → early-return без создания клиента и без вызова LLM.
3. Сборка ответа выравнивается по исходному списку `batch_segments`: слоты link-only заполняются
   `seg.source` дословно; остальные — `translation_map.get(seg.id, None)`.
4. **Нумерация/парсинг ответа.** Ответ парсится `^(\d+)\.\s*(.*)` по **id сегментов**, а не по
   позициям: при пропусках id в запросе нумерация не ломается (подтверждено пробой S1: в payload
   id `[1,6,7,8,10,11]`, ответ `1./6./7./8./10./11.` сопоставился корректно, все цели на месте).
5. Логи/счётчики: печать на каждую пачку `⤳ {n} link-only segments skipped in this batch
   (not sent to LLM)` (stdout воркера tee-ится в диагностический лог приложения); в `run()`
   цикл результатов тегирует пропущенные сегменты в сообщении прогресса
   `[i/N] ⤳ link-only (LLM skipped)` (в диалоговой консоли — по 1 строке на сегмент).
   Счётчики воркера (`success_count`) и диалога: link-only считается успехом (target непустой) —
   счётчики воркера и UI совпадают, отдельная «summary»-строка в канал прогресса НЕ эмитится
   (не завышает счётчик диалога).

**Статус (задание п.2): использован `draft`.** Прецедент «копия source→target без перевода» найден
и это `copy_source_to_target_non_translatable_bulk` (Supervertaler.py:38526–38626,
Edit > Bulk Operations): непереводимые сегменты (только цифры/коды/пунктуация, предикат
`_is_non_translatable`) копируются дословно (`_transform_non_translatable` возвращает source
как есть) и статус ставится **`'draft'`** (docstring:38531–38532, подтверждение
«…and mark as Draft?», undo-запись `old→'draft'`). Тот же статус во всех TM/MT/LLM-записях
воркера. Примечание: tooltip меню (:8150) говорит «mark as Translated» — расходится с кодом
(устаревший текст); кода не тронут, кандидат в BACKLOG.

**Undo:** записи создаются тем же механизмом, что и для переводов
(`(segment.id, old_target, source, old_status, "draft")`), пачкой через `undo_entries`
воркера → стек отмены.

## 3. Одиночный путь (M1c) — что изменено

`translate_current_segment` (AST 48782–49151) — гейт сразу после проверки пустого источника,
ДО загрузки LLM-настроек, TM-проверки, сборки промпта и vision: при `is_image_links_only`
LLM не вызывается; `segment.target = segment.source` дословно; статус `draft`; undo-запись
`record_undo_state(...)`; обновление виджета цели в display-форме
(`apply_invisible_replacements`, как в прецеденте copy_source_to_target); `update_status_icon`,
`_auto_resize_single_row`, `project_modified=True` + заголовок окна; в лог:
`⤳ Segment #N: link-only segment (image links) skipped — LLM not called, source copied to target (draft)`;
строка статуса окна 3 сек. В TM копия НЕ добавляется (прецедент copy-bulk тоже не добавляет).
Гейт общий для Ctrl+T и для FuzzyFixer-варианта входа (`fuzzy_match` аргумент) — ранний выход.

## 4. Инвентаризация путей, где source сегмента уходит в LLM/MT (задание п.4)

| # | Путь | Место | Затронут M1? |
|---|------|-------|--------------|
| 1 | Пакетный LLM-перевод (Batch Translate, «Translate all…» меню → `translate_multiple_segments` → `translate_batch` → воркер) | `PreTranslationWorker._translate_batch_with_llm` (5653–5847) | **ИЗМЕНЁН (M1b)** |
| 2 | Одиночный LLM-перевод (Ctrl+T) | `translate_current_segment` (48782–49151) | **ИЗМЕНЁН (M1c)** |
| 3 | FuzzyFixer-одиночный (тот же Ctrl+T вход с fuzzy-словарём) | тот же метод | **ИЗМЕНЁН** (гейт общий, ранний выход) |
| 4 | FuzzyFixer пакетный режим (per-segment LLM в воркере) | `_run_fuzzy_fixer_llm` (5849–5888) → `_translate_single_with_llm` (5890–5930, LLMClient :5914) | Не затронут. Рекомендация: добавить тот же гейт per-segment |
| 5 | AutoTagger (bulk, без перевода) | `_run_autotag_only` (5961–5994) → `_autotag_segment_llm` (:5932–5960) | Не затронут. Рекомендация: пропускать link-only (в ссылочных сегментах inline-тегов нет — запрос = чистый оверхед) |
| 6 | MT-предперевод (worker provider MT) | `_translate_with_mt` (5574–5589) → `call_custom_mt` (47659–47750, вызов :5582) | Не затронут (MT-движок, не LLM). Рекомендация: единый гейт в батч-петле воркера |
| 7 | Match Panel: LLM-совпадения | `_add_mt_and_llm_matches` (51974+, LLMClient :52031); асинхронный чип `_fetch_llm_translation_async` (50758–50877, LLMClient :50801) | Не затронут. Рекомендация: гейт по `segment.source` |
| 8 | MT-чипы (панель результатов) | `_fetch_llm_translation_async` MT-ветка `call_custom_mt` (:50902) | Не затронут (MT) |
| 9 | QuickTrans (popup выделения, MTQuickPopup) | `modules/quicktrans.py:435` (LLM-провайдер) + MT-провайдеры | Не затронут (работает по выделенному тексту, не по сегменту). Рекомендация: тот же предикат в LLM-ветке провайдера |
| 10 | Proofreading (AI-вычитка) | `_run_proofreading` (39007+) → `ProofreadWorker` (modules/workers/proofread.py) | Не затронут. Рекомендация: исключать link-only сегменты из проверки (у них target==source, вычитка будет маркировать их как «непереведено») |
| 11 | TM (предперевод по БД) | worker `_translate_from_tm`, main-thread TM pre-check | Не затронут (в LLM не отправляет; TM-совпадения по ссылочным сегментам — легальные копии) |
| 12 | Chat (AI-чат) | `modules/chat_backend.py:157` | Вне сегментных путей (пользовательский текст) |
| 13 | Prompt launcher (кнопки промптов в сетке) | `run_grid_quicklauncher_prompt` (49613+, LLMClient :49666) | Вне переводческих путей (произвольный промпт к тексту ячейки) |
| 14 | Мёртвый код (не вызывает) | `_translate_with_llm` воркера (5592–648; вызовов нет), `_REMOVED_add_mt_and_llm_matches_progressive` (51879+) | Отмечено, кода не тронут |

Правки внесены только в п.1–3 (пакетный + одиночный пути), как предписано заданием.

## 5. Проба e2e (фейковый loopback OpenAI-совместимый endpoint + ловушка сети)

Скрипт `docs/refactoring/audits/batch-m1_probe_m1_e2e.py`, прецедент batch9-3_probe_llm_e2e.py:
полное приложение offscreen, изолированный профиль (`run-002/iso`), настройки seeded на фейковый
endpoint `http://127.0.0.1:<PORT>/v1`; фейк логирует полный payload каждого запроса
(`run-002/payloads/req-*.json`) и id сегментов из блока «SEGMENTS TO TRANSLATE»; ловушка сети —
обёртка `socket.socket.connect`, все не-loopback подключения записываются. Модальные диалоги
заглушены. Verdict: `run-002/probe_m1_e2e_verdict.json` → **PASS** (log-файл `run-001` — первый
прогон, FAIL из-за багнутой проверки харнесса S4 «Translated6» против фиксированного ответа
одиночного промпта «Goedemorgen»; продукт не затронут, поправлено в run-002).

Матрица «что ушло на endpoint»:

| # | Кейс (11-сегментный синтетический проект) | Отправлен? | Target | Статус |
|---|-------------------------------------------|-----------|--------|--------|
| 1 | обычный текст | да | «Translated1» (ответ модели) | draft |
| 2 | ![Image](/path/file.png) | **нет** | == source байт-в-байт | draft |
| 3 | ![Image](a.png) ![Image](b.png) (две подряд) | **нет** | == source | draft |
| 4 | ![Figure 1](x.png) (alt-ключ) | **нет** | == source | draft |
| 5 | ![Рисунок 1](рисунки/рисунок 1.png) (кириллица+пробелы) | **нет** | == source | draft |
| 6 | ![Image](x.png) Figure 1 shows | да | «Translated6» | draft |
| 7 | ![Image](x.png). (точка после) | да | «Translated7» | draft |
| 8 | [t](u) (обычная ссылка) | да | «Translated8» | draft |
| 9 | ![](x.png) (пустой alt) | **нет** | == source | draft |
| 10 | ![Image](x.png) some text after | да | «Translated10» | draft |
| 11 | обычный текст после ссылок | да | «Translated11» | draft |

- `ids_in_prompt` = **[1, 6, 7, 8, 10, 11]** — ровно непровалидированные, ровно 1 запрос;
  ответ парсится по id, выравнивание целей корректно (все 11 targets на месте).
- 5 console-строк `[i/N] ⤳ link-only (LLM skipped)`; счётчик воркера = успех 11.
- S2 «весь пакет только ссылки» (2 сегмента): **0 запросов** на endpoint, targets==source,
  draft, 2 ⤳-строки.
- S3 одиночный на ссылочном сегменте: **0 запросов**, target==source, draft, строка лога
  `⤳ Segment #2 … source copied to target (draft)`.
- S4 одиночный на «ссылка + текст»: ровно 1 запрос, target = ответ модели («Goedemorgen»), draft —
  поведение не изменилось.
- S5 фикстура `docs/refactoring/samples/Miniature Wargames #520.translation.md` (импорт
  import_simple_txt: строка=сегмент; 3 сегмента, id3 — ссылка
  `![Image](e:\Dev\...\Figure 2.jpg)`): 1 запрос, `ids_in_prompt=[1,2]`,
  **link id на endpoint не утёк**, target==source, draft, 1 ⤳-строка; экспорт
  `build_markdown`+`write_export` → строка со ссылкой встречается в экспорте ровно 2 раза
  (source- и target-строка), **байт-идентично** (`export_link_byte_identity: 2/2`).
- Ловушка сети: `net_traps: []` — ни одного не-loopback подключения.

Уточнение харнесса: в S4 surrounding-context (5 сегментов до/после) содержит link-only сегменты
как КОНТЕКСТ — это не отправка их на перевод (в перевод берётся один сегмент), оставлено как есть.

Известный краевой случай (не правится, в отчёт): смешанная пачка, у которой LLM-вызов падал
(исключение) — в этом проходе link-only сегменты помечаются BATCH ERROR (не копируются), target
остаётся пустым; на retry-проходе они копируются (а полностью link-only ретрай-пачка
короткозамыкается без LLM). Самовосстановление через retry-механизм.

## 6. Обойма (до/после)

Статика (`g5_12_static.py m1`, лог `batch-m1_static.log`) — всё идентично базе G5.2b:

| Метрика | До | После |
|---------|----|-------|
| AST chain | 873 ok / 0 fail | 873 / 0 ✓ |
| pyflakes warnings | 548 | 548 ✓ |
| undefined-name lines / unique names | 126 / 4 (tk 100, messagebox 19, ttk 5, filedialog 2) | 126 / 4 ✓ (тот же состав) |
| py_compile CANONICAL (вне docs/) | 109 ok / 0 fail | 109 / 0 ✓ |
| py_compile REFERENCE (все tracked .py) | 199 | 200/0 — +1: аудит-проба M1a (канон не вырос, 0 ошибок) ✓ |
| headless imports | 90 ok / 2 fail (setuptools, fitz — известные) | 90 / 2 ✓ |
| grep-гейт (9 файлов) | CLEAN | CLEAN ✓ |

Полный offscreen-прогон (`batch-m1_run_full.sh`, лог `batch-m1_run_full.log`, все 16 этапов):

| Этап | После M1 | База g52b |
|------|----------|-----------|
| fallback 9.4h | PROBE DONE (S5 OK: True) | OK ✓ |
| profiles 9.4f | EXEC OK / ACTIVE UNCHANGED | OK ✓ |
| qtchat | CHAT WIDGET: True | OK ✓ |
| statusbar prof | LOCAL-LLM NOTE: OK | OK ✓ |
| e2e (batch9-3, 5 сценариев) | verdict OK; single/batch3/matchpanel/proofread2/chat: 1 запрос на сценарий, цели/статусы идентичны | OK ✓ (в `single` единственное поле-отличие — строка лога termbase-worker со скоростью `374491 seg/sec` vs `322639` — транзиентный тайминг-шум) |
| S-clean | PROBE OK | OK ✓ |
| S-upgrade | PROBE OK, HASH-DIFF: added=[] removed=[] changed=[] transient=[index.json] — только известная транзиентная запись (правило G5.2) | OK ✓ |
| **regress** | **`5a12501f934a589c` / `44828d90090f046d` / `c413d56372e69dd9`** — совпадение байт-в-байт | те же ✓ |
| Tools-smoke | 42 ITEM, SMOKE OK (12.7s) | 42 / OK ✓ |
| termbase-регресс | REGRESS-TB OK (12.2s) | OK ✓ |
| About | RESULT OK, labels идентичны | OK ✓ |
| save modern | PROBE DONE (api_keys/mt_quick_lookup intact) | OK ✓ |
| save legacy | PROBE DONE | OK ✓ |
| r9 a / ctrl / rm | RESULT OK / VERDICT OK / VERDICT OK | OK ✓ |

Отклонений от baseline нет (единственная нетождественная строка — транзиентный тайминг
termbase-worker в e2e-логе, поведение идентично; reference py_compile +1 — новый аудит-скрипт
M1a, канон не вырос).

Замечание харнесса (не код продукта): при свежем stage-каталоге `stage-regress` харнесс
`batch8-15_regress_common.py` требует предсуществующих `stage-regress/iso/` и `inputs/`
(в g512b доставались из старого разделяемого stage); в m1 созданы заново (`iso` + копия
`inputs/` — те же fixtures test.txt/md/docx).

Точечный kill: после этапов убиты только процессы этого прогона (python-embed с путями батча;
java.exe Okapi-sidecar от перезапуска regress — PID 54016, CommandLine указывал на
`batch-m1/stage-regress`). Выжившие (пользовательские, не тронуты): PID 57772, 55060
(Strata: `i:\AI\StrataPortable\...`). Других python/java процессов прогона не осталось.

## 7. Пакет файлов для тестовой сборки Дмитрия

| Файл | Строк | SHA-256 |
|------|-------|---------|
| `Supervertaler.py` | 55 153 (было 55 096, +57) | `10553447d8486abfa24f972d0e2eee145d1226e64c0b5ae880b95c33893ae5b2` |
| `modules/bilingual_markdown_handler.py` | 866 (было 848, +18) | `d64aed69dadf9b81f1dbb5ba76acfb21c92297cc31d3b63e652ef1fb06f58031` |

CRLF монолита сохранён (55153 CRLF, bare-LF = 0, проверено после каждого редактирования).
Модуль bilingual_markdown_handler.py — LF (как и был).

## 8. Ручные сценарии T-M1.x

- **T-M1.1 — пакет по md-фикстуре.** Импорт `Miniature Wargames #520.translation.md`,
  Batch Translate (LLM). Ожидание: в диалоговой консоли строка
  `⤳ 1 link-only segments skipped in this batch (not sent to LLM)`, ссылочный сегмент помечен
  `⤳ link-only (LLM skipped)`, его target побайтово равен source (путь не искажён), статус Draft;
  остальные сегменты переведены; экспорт md сохраняет ссылку в target байт-в-байт; Ctrl+Z
  откатывает пачку.
- **T-M1.2 — одиночный перевод на сегменте-ссылке.** Ctrl+T на ссылочном сегменте. Ожидание:
  без сетевого запроса (статус-бар не «Translating…»), target==source, статус Draft, строка лога
  `⤳ Segment #N: link-only segment … source copied to target (draft)`, undo работает.
- **T-M1.3 — «ссылка + текст» уходит в LLM как раньше.** Сегмент
  `![Image](x.png) Figure 1 shows`: в пакете — в payload (идёт с номером id), в одиночном —
  ответ модели в target, статус draft. Сегмент «`![Image](x.png).`» (точка после) — тоже уходит.
- T-M1.4 — нумерация при пропусках: пакет с чередованием (текст/ссылка/текст) — все цели
  сопоставлены своим сегментам (в probe S1 подтверждено).

## 9. Вопросы координатору

1. FuzzyFixer-пакетный режим (`_run_fuzzy_fixer_llm`) — добавить тот же гейт per-segment
   следующим мини-батчем? (link-only сегменты и там уходят в LLM дословно.)
2. AutoTagger bulk — пропускать link-only сегменты (тегов в них нет)?
3. Единый гейт для MT-путей (MT-предперевод воркера, MT-чипы, QuickTrans-MT) — в отдельный
   батч? (MT на ссылочном сегменте возвращает переписанный текст, риск тот же.)
4. Proofreading — исключить link-only сегменты из AI-вычитки (у них target==source)?
5. Устаревший tooltip :8150 «mark as Translated» vs код `'draft'` (non-translatable bulk) —
   кандидат в BACKLOG как docs-правка; править?
6. Статус для M1-копий — `draft` (прецедент). Отдельного статуса (напр. «copied») не вводил;
   нужен ли — решение за координатором.

## 10. Останов

Работа batch M1 завершена (M1a–M1c код + пробит, M1d отчёт), коммиты локальные, пуш не выполнялся.
Стоп до вердикта координатора.
