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

---

# M1e (2026-10-20) — РАСШИРЕНИЕ КРИТЕРИЯ LINK-ONLY

## 11.0 Премисса (по ручному тесту координатора)

Разбор по repr файла проекта `3.svproj` (сохранён 19:24, состояние со скриншота 19:30):
пробел в начале сегмента 2 не причина — причина точка после ссылки по спецификации M1
(«link + trailing period» не был link-only, уходил в LLM). Спецификация M1 признана слишком
узкой (ошибка координатора). Новый критерий (промпт Дмитрия от 2026-10-20): сегмент
link-only, если после удаления всех md-ссылок на картинки `![alt](path)` в остатке нет ни
одной буквы/цифры (`re.search(r'[^\W_]', rest) is None`); остаток из пробелов / NBSP / ZWSP /
точек / «!» / тире / любой пунктуации — link-only; сегмент без ссылок (в т.ч. пустой) не
подпадает; буквы/цифры («Figure 2 shows», «1») — в LLM, как раньше.

## 11.1 Задача 1 — детектор (коммит `3fc8b876`)

`modules/bilingual_markdown_handler.py` — только детектор, без «заодно»:

* `_MD_IMAGE_LINK_RE = !\[[^\]]*\]\([^)]*\)` (строка 408), `_MD_LEFTOVER_CONTENT_RE = [^\W_]`
  (строка 409), `is_image_links_only` — строки 412–420 (AST): `subn` по всем ссылкам,
  `n_links == 0 → False` (без-ссылочные/пустые вне правила), остаток без букв/цифр → True.
* Замонтировано по снятому снапшоту блока HEAD (`m1e_detector_block_head.txt`); LF файла
  сохранён; py_compile 0 ошибок после правки.
* Файл: 866 → **873 строк**, sha256
  **`463a523711beb1efa3866475914e9d2d647a6f251b04601cf047cc5ea1bcf8e9`**.
  `Supervertaler.py` не тронут: **55 153** строки, `10553447…` (гейты M1b/M1c не менялись —
  весь новый критерий внутри функции детектора).
* Статик-матрица (`batch-m1e_detector_matrix.py/json`): **14/14 PASS** по матрице промпта
  (ведущий пробел+точка, чистая точка, «.)», «!» в конце, NBSP+точка, две ссылки+точка,
  пустой alt → True; link+words, words+link, `[t](u)`, пустой, «.», «Figure 2.» → False)
  + дополнения: ZWSP+точка True, «_» True, цифра False, кириллица False, полноширинная
  «１» False, многострочный текст со ссылками True.

## 11.2 Задача 2 — TM: статика (правка НЕ требуется)

Вопрос промпта: пишет ли путь «копия source→target для link-only» TU в TM?
Статический аудит всех колл-сайтов записи TU в монолите (9 у `save_segment_to_activated_tms`
+ прямые `tm_database.add_to_project_tm`):

| Колл-сайт | Метод | Гейт |
|---|---|---|
| :36961 | `_handle_target_text_debounced_by_id` (дебаунс набора в гриде) | только `status == 'confirmed'` |
| :36993 | `update_status_icon` (её вызывает M1-гейт со статусом draft) | только `status == 'confirmed'` |
| :44354 | `_save_tab_target_to_tm` (дебаунс вкладки) | только `confirmed` |
| :44398 | `on_tab_segment_status_change` (смена статуса в комбо) | только `confirmed` |
| :45508 / :45628 | `save_tab_segment` / `save_grid_segment` (ручной Save) | только `confirmed` |
| :46604 / :46707 / :46853 | auto-confirm 100 % / `_confirm_current_row_segment` / `confirm_selected_segments` | путь подтверждения |
| :49107 | `add_to_project_tm` в `translate_current_segment` | лежит ЗА `return` M1-гейта (:48834) — недостижим для link-only |

Вывод: **link-only-копия TU в TM не пишет** (одиночный гейт возвращается до записи;
пакетный воркер (PreTranslationWorker, 5286–5994) вообще не содержит колл-сайтов записи TU;
статус копий `draft`, а все сеточные/табовые писатели гейтаны `confirmed`).
Динамическое подтверждение: TU delta = 0 во всех 14 кейсах пробы + в пакете (§11.3).
**Правка по ТМ не выполнялась** (промпт: «если не вызывает — ничего не менять»).

Наблюдение Дмитрия («Added to TM» при блокированной записи, базы нет): строка
«✓ Added to TM: …» (:49109) печатается на пути Ctrl+T **LLM**-перевода безусловно, поверх
phantom-TM guard'а (`database_manager.py:1033`): при отсутствии строки `tm_id 'project'`
guard печатает «⚠️ Refusing to add TU … (orphan write blocked)», возвращает `None` без
исключения → ✓-строка ложная. Как предписано — **не правится**, занесено в
**BACKLOG §9.8** (`docs/refactoring/POST_BATCH8_BACKLOG.md`).

## 11.3 Задача 3 — матричная проба (fake endpoint + ловушка сети)

`batch-m1e_probe_matrix.py` (полный app, изолированный профиль, offscreen, фейковый loopback
OpenAI-endpoint, socket-ловушка, 14 кейсов промпта): одиночный Ctrl+T на каждом ряду +
пакетный прогон на свежем импорте. Первый прогон (run001) — FAIL единственной проверкой
`s2_all_link_targets_eq_source` (ряд 6, NBSP — см. §11.4); ожидание пробы скорректировано
(NBSP-нормализация как известное поведение); **прогон run002: PASS 21/21**
(`batch-m1e_probe_verdict_run002.json`; логи `batch-m1e_probe_run001.log` /
`batch-m1e_probe_run002.log`; payloads `batch-m1e_payloads_run001/`).

Одиночный путь (Ctrl+T):

| # source (repr) | link-only | запросов | target | статус | TU в TM |
|---|---|---|---|---|---|
| 1 `' ![Image](x).'` | да | 0 | == source (байт) | draft | 0, логов TM нет |
| 2 `'![Image](x).'` | да | 0 | == source | draft | 0 |
| 3 `'![Image](x)'` | да | 0 | == source | draft | 0 |
| 4 `'![Image](x) .'` | да | 0 | == source | draft | 0 |
| 5 `'![Image](x)!'` | да | 0 | == source | draft | 0 |
| 6 `'![Image](x)\xa0.'` | да | 0 | == source (NBSP сохранён) | draft | 0 |
| 7 `'![A](x)![B](y).'` | да | 0 | == source | draft | 0 |
| 8 `'![Image](x) Figure 1 shows'` | нет | 1 | 'Goedemorgen' (модель) | draft | 0† |
| 9 `'Text ![Image](x)'` | нет | 1 | 'Goedemorgen' | draft | 0† |
| 10 `'![](x)'` | да | 0 | == source | draft | 0 |
| 11 `'[t](u)'` | нет | 1 | 'Goedemorgen' | draft | 0† |
| 12 `''` (пустой) | вне правила | 0 | `''` (QMessageBox «Cannot translate empty source text.») | untranslated | 0 |
| 13 `'.'` | нет | 1 | 'Goedemorgen' | draft | 0† |
| 14 `'Figure 2.'` | нет | 1 | 'Goedemorgen' | draft | 0† |

† LLM-путь вызывает `add_to_project_tm('project', …)`; в изолированном профиле строки
'project' нет → guard блокирует, TU delta = 0; ложная ✓-строка поверх guard'а (BACKLOG §9.8).
Все 7 copy-кейсов дают строку консоли `⤳ Segment #N: link-only segment (image links) skipped —
LLM not called, source copied to target (draft)`.

Пакетный прогон (13 непустых рядов одной пачкой): `n_requests=1`,
`ids_in_prompt=[8,9,11,13,14]` (точно LLM-ряды; все 8 link-only рядов промпта исключены),
8 строк «⤳ link-only … skipped» в прогресс-консоли, TU delta = 0, цели 7/8 byte-identical
(ряд 6 — NBSP-нормализация, §11.4), статусы draft, net_traps = 0.
Мини-проба (`batch-m1e_probe_s2mini.py`, 3 ряда, строгое байтовое сравнение) —
`batch-m1e_probe_s2mini_verdict_run002.json`: одиночный путь NBSP сохранён, пакетный путь
`'![Image](x)\xa0.' → '![Image](x) .'` (строго-байтовая проверка mini-пробы ожидаемо даёт
False на этом ряду — это сама находка, не регрессия).

## 11.4 Находка: Qt-нормализация NBSP в пакетном пути (pre-existing, НЕ править без решения)

Ряд 6 (`'![Image](x)\xa0.'`) в **пакете**: target `'![Image](x) .'` (NBSP → обычный пробел).
Причина не M1e: `handle_progress_update` (:50666) пишет target в ячейку
`target_widget.setPlainText(display_text)` **без blockSignals**; отложенное событие
textChanged (Qt доставляет его после unblock — комментарий :3221) проходит через
`on_target_text_changed` (:32861) и присваивает `segment.target` из `toPlainText()`,
а `QTextDocument` конвертирует U+00A0 → U+0020 при plain-text round-trip (минимальная
проверка на голом `QTextEdit`/`QTextDocument` воспроизводит). В **одиночном** Ctrl+T гейт
пишет `segment.target` raw (NBSP сохранён, ряд 6 == source байт-в-байт) и обновляет виджет
с blockSignals. Прединтscируемость доказана на worktree HEAD (`batch-m1e_probe_head_nbsp.py`
→ `batch-m1e_probe_head_verdict_run004.json`, tree `m1e-run-004/head-wt` @ `2264e2a6`):
link-only ряд `'![Image](x)\xa0'` в пакете HEAD даёт target `'![Image](x) '` (тот же
эффект; код прогресс-хендлера в M1 не менялся). Касается **всех** целей с NBSP в пакете
(не только M1-копий). Правка не выполнена (вне рамок M1e); вопрос Q7 координатору (§11.7).

## 11.5 Задача 4 — обойма (статика + 16 этапов offscreen)

Статика (`g5_12_static.py m1e` → `batch-m1e_static.log`) — идентична базе G5.2b/M1:
chain 873/0; pyflakes 548; undefined 126/4 (tk 100, messagebox 19, ttk 5, filedialog 2);
py_compile CANONICAL **109/0**; REFERENCE **201/0** (= 200, +1 — аудит-скрипт M1e, канон
не вырос, правило «docs/ не считать»); headless 90/2 (setuptools, fitz — известные);
grep-гейт CLEAN.

Полный прогон (`batch-m1e_run_full.sh` → `batch-m1e_run_full.log`), сравнение логов с
базалайнами M1 (`*_after_m1.log`) после нормализации тега m1e→m1:

* **regress: хеши байт-идентичны базе** `5a12501f934a589c` / `44828d90090f046d` /
  `c413d56372e69dd9`; остаточные diff-строки — obj-адреса, project_id, порядок строк
  стартовых логов (состояние stage-директорий);
* **smoke: 42 ITEM** (остаточные diff — миграционные строки свежей БД, время);
  termbase REGRESS-TB OK; about RESULT OK; save modern/legacy — все OK-строки идентичны;
* e2e (probe M1): verdict **OK**, сверка JSON — отличия только `port`/`tag`;
* S-clean / S-upgrade: PROBE OK; транзиенты `index.json` + каталог
  `workbench/ai_assistant/attachments/<дата>` (+1 entry) — известная находка BACKLOG
  (кандидат §4, attachments/<дата>);
* r9 a/ctrl/rm: VERDICT зелёные; profiles / qtchat / statusbar / fallback — PROBE DONE
  (fb residual — порядок строк / QThreadStorage-адрес).
* Точечный kill не требовался: сирот после прогонов нет; survivor list — PID 18684, 27108
  (Strata-процессы пользователя, не тронуты; python-embed/java от проб отсутствовали).

## 11.6 Пакет для тестовой сборки

Оба файла — из репо `main` (состояние коммита `3fc8b876`):

* `Supervertaler.py` — **55 153** строки, sha256
  `10553447d8486abfa24f972d0e2eee145d1226e64c0b5ae880b95c33893ae5b2` — **НЕ ИЗМЕНИЛСЯ**
  (в тестовой сборке уже лежит этот);
* `modules/bilingual_markdown_handler.py` — **873** строки, sha256
  `463a523711beb1efa3866475914e9d2d647a6f251b04601cf047cc5ea1bcf8e9` (LF) —
  **единственный заменяемый файл пакета**.

## 11.7 Ручные сценарии M1e (ждут теста Дмитрия на `D:\SupervertalerPortable_test\`)

* **T-M1e.1** — Ctrl+T на сегменте `'![Image](…Figure 2.jpg).'` (сегмент с точкой после
  ссылки): ожидание 0 POST, target == source, Draft, `⤳ Segment #N: link-only …`.
* **T-M1e.2** — Ctrl+T на `' ![Image](…).'` (ведущий пробел + точка): 0 POST, target == source.
* **T-M1e.3** — пакет со строками «ссылка+точка»: в консоли `⤳ link-only (LLM skipped)`,
  target побайтово == source.
* **T-M1e.4** — `'Figure 2 shows …'` и `'Text ![Image](x)'` — как раньше: 1 POST, перевод модели.
* **T-M1e.5** — `'[t](u)'` (обычная md-ссылка) — 1 POST (в LLM, не копия).
* **T-M1e.6** — ряд с NBSP в пакете: target отобразится с обычным пробелом
  (Qt-нормализация, §11.4) — зафиксировать как известное поведение.

Вопросы координатору по M1e:

7. Qt-нормализация NBSP в пакетном пути (§11.4, pre-existing, касается всех целей с NBSP):
   оставить как есть / править прогресс-хендлер (blockSignals — затронет все пачки) /
   BACKLOG-кандидат?
8. Матричный e2e-пробник M1 (`batch-m1_probe_m1_e2e.py`, закоммичен в M1d) содержит зашитые
   ожидания M1 для ряда `'![Image](x.png).'` (ряд уходил в payload `[1,6,7,8,10,11]`); по
   новому критерию этот ряд копируется. Старый лог не тронут; поведение покрыто новой
   матрицей. Обновить expectations пробы следующим мини-батчем?

## 11.8 Останов M1e

M1e: детектор заменён (коммит `3fc8b876`), TM-статика (правка не требуется, наблюдение —
BACKLOG §9.8), матричная проба PASS 21/21 (run002), Qt-NBSP находка с доказанной
прединтscируемостью на HEAD, обойма идентична базе, пакет собран. Пуш не выполнялся.
**Стоп до вердикта координатора.**
