# ОТЧЁТ BATCH Q-A — MT-профили: поля запроса; link-only в QuickTrans; отмена при закрытии

**Батч:** Q-A (промпт Дмитрия 2026-10-23, `docs/refactoring/prompts/Promt - EXTRACTION BATCH Q-A.txt`).
**Основание:** RECON Q.0 (`docs/refactoring/reports/RECON_Q0_QUICKTRANS_PANEL_REPORT.md`, HEAD `8507dd55`), решения координатора Q1, Q2, Q4, Q7, Q9.
**База:** `090810fe` (RECON Q.0, docs-only). **Стоп до вердикта координатора. Пуш не выполнялся.**

---

## 0. Сводка

| Под-батч | Коммит | Файлы |
|---|---|---|
| Q.1 — поля max_tokens/timeout_min/extra_body в MT-профилях + видимые ошибки MT | `4535b46c` | `Supervertaler.py` (+117/−7), аудиты `batch-qa_q1_*` |
| Q.2 — link-only гейт в QuickTrans (панель + попап, MT + LLM) | `46c174ce` | `modules/quicktrans.py` (+40/−18 от базы), аудиты `batch-qa_q2_*` |
| Q.6 — кооперативная отмена при закрытии QuickTrans | `dd1c5b97` | `modules/quicktrans.py` (+66/−13 к Q.2), аудиты `batch-qa_q6_*` |
| Q-A docs (этот отчёт, PROJECT_STATUS, BACKLOG, промпт, suite-логи, статика) | финальный коммит | docs |

### Пакет файлов (итоговое состояние, wc/sha256 по байтам файла)

| Файл | Строк | EOL | sha256 |
|---|---|---|---|
| `Supervertaler.py` | 55 573 (было 55 456) | CRLF 55 573 / bare-LF **0** | `bf8f64f2faaa308588eb8680c120dc6a9a5a2c1a99995039677135af011accb4` (2 971 113 B) |
| `modules/quicktrans.py` | 1 741 (было 1 635) | LF 1 741 / CR-байт **0** | `81a6a3f8d77b4fc6aec926b4d45e9e44dfeb6b861f8a4f85be31e71b93134143` (76 183 B) |
| `modules/llm_clients.py` | 854 | без изменений | `93e995521395e6fc1a63c7a6956f1f1fe59d599c2ffc30f29722b1c7d6df784b` (== базе Q-A) |
| `modules/settings_service.py` | 599 | без изменений; **не коммитился** (CRLF-артефакт M) | `08a0d943…` (== состоянию до батча) |
| `modules/bilingual_markdown_handler.py` | 873 | без изменений | `463a5237…` (детектор `is_image_links_only` :412 не тронут) |

Пакет тестовой сборки (при пересборке `D:\SupervertalerPortable_test\`): **Supervertaler.py + modules/quicktrans.py**.

### Рекон-верификация перед правками

Все места из RECON Q.0 сверены с кодом на базе `090810fe` — **расхождений нет** (MT-редактор 20095–20246; LLM-образец 19460–19592; валидация Save 23290–23301; `parse_profile_request_fields` llm_clients 211–270; `call_custom_mt` 47895–47986 без профильных kwargs; quicktrans: fetch_single 127–134, popup start_fetching 980–1036, closeEvents 1293–1306/1628–1635; 0 link-only гейтов в quicktrans.py). Мёртвая цепочка (`_fetch_llm/_mt_translation_async` 51181/51204, `_add_mt_and_llm_matches` 52286) подтверждена недостижимой и **не правилась** (выгодна автоматически, т.к. правка внутри `call_custom_mt`).

---

## 1. Q.1 — поля запроса в MT-профилях (вариант 1 рекона: без миграции, без vision)

### 1.1 Карта правок `Supervertaler.py` (до → после)

| Место | До (база) | После (Q.1) | Содержание |
|---|---|---|---|
| Блок «Advanced request parameters (optional)» | — | вставка **20181–20234** | Метка + строка: `Max tokens:` (`default 16384`), `Request timeout, min:` (`default 10`), `Extra request body (JSON):` — подписи/плейсхолдеры/тултипы дословно из LLM-редактора (:19476–19524); виджеты `self._custom_mt_{max_tokens,timeout,extra}_input` |
| `_cmt_populate` | 20186–20199 | **20237–20264** | +3 поля: setText с `blockSignals(True/False)` (по образцу LLM populate :19537–19547), в else-ветке `.clear()` |
| `_cmt_sync` | 20201–20208 | **20266–20285** | +цикл по 3 ключам: непустое пишется (`_cmt_clean`), `timeout_min` — запятая→точка (G3.2g), пустое — ключ удаляется (`pop`) |
| connects | 20238–20240 | **20319–20324** | +3 × `editingFinished → _cmt_sync` |
| `_save_mt_quick_lookup_settings` | 20323–20379 | **20404–20484** | Синк видимых полей (вкл. новые 3) перенесён **до первой записи на диск**; затем валидация ВСЕХ профилей `self._validate_custom_profiles` → при ошибке `QMessageBox.warning` «Invalid Profile Parameters» с текстом `Profile "{имя}": {сообщение}` (тот же формат, что AI Settings :23293–23301), выбор виновного профиля в комбо, `return` — **ничего не пишется**; записи general/llm_settings — после успешной валидации, внутренность не менялась |
| `call_custom_mt` | 47895–47986 | **48000–48103** | (а) импорт `+LLMResponseError`; (б) `LLMClient(..., **self._custom_profile_request_kwargs(profile))` — kwargs профиля **вызывающего**; (в) новый `except LLMResponseError` **до** `except Exception` → однострочный `[Error: {str(e)}]` |

### 1.2 Профиль «своей строки»

Аудит вызовов `call_custom_mt` (все 4 места):
- `modules/quicktrans.py:337` (живой) — QuickTrans передаёт профиль **своего чипа** (`make_custom_mt_caller(prof)`) → kwargs именно этого профиля.
- `Supervertaler.py:5610` `_translate_with_mt` (живой, пакетный предперевод) — профиля у строки нет by design («активный профиль», докстринг), kwargs разрешённого активного профиля.
- `Supervertaler.py:51204`, `:52286` — мёртвая цепочка (рекон §B), не правились.

### 1.3 Ошибки MT

- `LLMTruncatedError`/`LLMEmptyResponseError`/`LLMTimeoutError` (общий базовый `LLMResponseError`, llm_clients :171–198; все сообщения однострочные) → `[Error: <текст>]` — тот же формат, что LLM-ряд панели (`_call_llm_translation` :477); красный цвет ряда — существующее правило `fetch_single` (`startswith('[') and 'error' in lower`). В таймаут-тексте имя профиля (llm_clients :814 `profile '{self.profile_name}'`).
- Легаси-тексты остались только для реальных сетевых состояний: `[MT proxy not running. Start it.]` — отказ соединения на 127.0.0.1/localhost (проверено пробой на закрытый порт), `[Custom MT: endpoint unreachable.]` — внешний эндпоинт, `[Custom MT error: …]` — прочее. Трассбеков нет нигде.
- Причина вводившей в заблуждение строки была не в эвристике `is_conn` (она корректна), а в том, что до правки типизированные исключения обрабатывались общей веткой `[Custom MT error: …]` (доказано pre-прогоном пробы: таймаут → `[Custom MT error: Error code: 500 …]`, усечение → `[Custom MT error: Model m was cut off …]`).

### 1.4 Обратная совместимость

- Профиль без новых ключей → `_custom_profile_request_kwargs` возвращает только `profile_name` (на тело запроса не влияет: `api_params` = model/messages/timeout/max_tokens/temperature/extra_body, llm_clients :795–804) → **тела запросов байт-идентичны** (проба §4.1: sha256 `bfdf4403c83f05e7…` до == после).
- Старый settings.json без полей читается и сохраняется без дописывания ключей (пробы parse + save).

---

## 2. Q.2 — link-only в QuickTrans (панель и попап, MT и LLM)

### 2.1 Выбор места гейта

Нижнее общее место существует: **`MTFetchWorker.fetch_single`** — через него проходят ВСЕ живые сетевые вызовы QuickTrans: авто-fetch MT панели (`_do_fetch` → `_start_worker`), авто-fetch MT+LLM попапа (`start_fetching`), Fetch-кнопки LLM в панели (`_add_llm_button`) и попапе (`_make_fetch_row`), re-translate/re-fetch. Отдельный гейт в `_call_llm_translation` не нужен: его единственные живые вызовы исполняются как `call_func` внутри `fetch_single` (рекон Q.0 F: 0 гейтов было; входы перечислены в recon §I). Гейты верхнего уровня не добавлялись.

### 2.2 Карта правок `modules/quicktrans.py` (до → после)

| Место | До | После | Содержание |
|---|---|---|---|
| Константа + хелпер | — | **65–81** | `LINK_ONLY_MARKER = "⤳ link-only — не отправлено"`; `_is_link_only_text` — ленивый импорт `is_image_links_only` (как `_canonical_lang_name`), детектор **как есть** (M1e: ссылка + точка = link-only; ссылка + слова/цифры = нет) |
| `MTSuggestion` | 102–108 | +поле **134** | `link_only: bool = False` |
| `MTFetchWorker.result_ready` | 114 (4 арг.) | **140** | 5-й аргумент `link_only`; оба `emit` в `run()` обновлены (:174, :177) |
| `fetch_single` | 127–134 | **153–166** | **Гейт**: link-only → `call_func` не вызывается, ряд = `(name, code, source_text, False, True)` |
| `MTSuggestionItem` | — | **299–302** | при `link_only` — мелкая серая пометка справа от текста ряда |
| Обработчики 5-арг. сигнала | 4-арг. | **1155** (fetch-row `on_ready`), **1241–1247** (`_on_result_ready`), **1545+1563/1573** (`_on_mt_result`/`_append_result`), **1689** (панельная LLM `on_ready`), **1601** (`_start_worker._ready`) | `+link_only` пробрасывается в `MTSuggestion` |
| Вставка | без изменений | — | клик/цифра/Enter эмитят `translation` = исходник; пометка — только отображение, в target не пишется |

### 2.3 Поведение

- Link-only: **0 сетевых запросов** (проба-ловушка), в каждом блоке (MT и LLM) ряд с исходником дословно и пометкой; ряд кликабелен/нумерован/автовыделяется; вставка = обычный результат (draft, как в M1: target получает исходник неизменным).
- TM-запись не выполняется — вставки QuickTrans никогда не пишут в TM (проверено по всем путям вставки: попап in-app `Supervertaler.py:7503–7535`, панель `:35873–35899` — только `setPlainText`+`mark_segment_modified`; внешний попап — буфер обмена `:54906–54908`).
- Fetch-кнопка LLM на link-only — тот же гейт (клик → ряд, без сети).
- Смешанные сегменты (`![Image](y.png) see figure two`) идут как раньше (детектор = False).

---

## 3. Q.6 — кооперативная отмена при закрытии

### 3.1 Карта правок `modules/quicktrans.py` (до → после)

| Место | До | После | Содержание |
|---|---|---|---|
| Реестр + детач | — | **182–214** | `_DETACHED_WORKERS: List[MTFetchWorker]`; `_detach_worker_for_close(worker)`: `result_ready.disconnect()` + `all_complete.disconnect()` (TypeError-tolerant), `setParent(None)`, append в реестр; `all_complete → _remove_from_detached` |
| Попап `_closed` | — | init **623** | флаг «закрыто» |
| Попап `closeEvent` | 1293–1306 (quit()+wait(1000)) | **1377–1400** | `self._closed = True` → детач работающего авто-воркера и всех fetch-row воркеров → очистка ссылок → **затем** сохранение геометрии (QSettings); ожидание удалено |
| Попап guard-ы | — | **1155, 1244, 1283** | `_make_fetch_row.on_ready`, `_on_result_ready`, `_on_all_complete` — ранний выход |
| Панель `_closed` | — | init **1435** | флаг «закрыто» |
| Панель `closeEvent` | 1628–1635 (wait(1000) каждый) | **1730–1741** | `self._closed = True` → детач работающих → очистка `_workers`; ожидание удалено |
| Панель guard-ы | — | **1546, 1601–1609, 1689** | `_do_fetch` (нет новых fetch после закрытия), `_start_worker._ready`/`_done`, `_add_llm_button.on_ready` |

### 3.2 Семантика (по промпту)

- Результат после закрытия **отбрасывается** (disconnect + флаг; поздняя доставленная эмиссия гасится guard-ом до касания UI).
- Висячих QThread нет: объект воркера переживает диалог в `_DETACHED_WORKERS`, `run()` завершается естественной смертью, `all_complete` убирает из реестра → GC с **завершённым** потоком; уничтожение работающего потока невозможно (родитель снят, ссылка держится).
- **Реальный abort сетевого вызова НЕ делается** (решение промпта): запрос доживает до ответа/таймаута на стороне сервера — оплачивается/логируется на сервере как обычный запрос, его результат просто отбрасывается. Для LLM Fetch-кнопки это означает, что закрытие попапа не отменяет платный вызов.
- Старое поведение (доказано pre-прогоном): `quit()` — no-op (в `run()` нет event loop), `wait(1000)` блокировал закрытие ~1 с и не гарантировал завершение; поздний результат **дописывался в закрытый UI** (2 строки попапа, 1 строка панели, 1 fetch-row).

---

## 4. Матрица проб

### 4.1 Q.1 — `batch-qa_q1_probe.py` (fake loopback OpenAI-endpoint; стаб с реальными методами `SupervertalerQt`; pre = worktree базы `090810fe`)

| # | Проверка | post | pre |
|---|---|---|---|
| 1 | Профиль без новых полей: перевод OK, ровно 1 запрос | PASS | PASS |
| 2 | **Тело запроса без полей байт-идентично до/после** (sha256 `bfdf4403c83f05e749…`, оба дерева) | PASS | PASS (совпадает) |
| 3 | max_tokens «20000» → `max_tokens: 20000` в теле | PASS | FAIL (16384 — поле игнорировалось) |
| 4 | extra_body `{"chat_template_kwargs": …}` → ключ в теле | PASS | FAIL (None) |
| 5 | Таймаут (0.005 мин, сервер спит) → `[Error: … timed out … profile 'Local proxy' …]`, одна строка, без «proxy not running» | PASS | FAIL (`[Custom MT error: Error code: 500 …]`) |
| 6 | Усечение (finish_reason=length) → `[Error: Model m was cut off at max_tokens …]`, одна строка | PASS | FAIL (`[Custom MT error: …]`) |
| 7 | parse: старый формат чист; «1,5»→90 c; «1,5,5»/«abc»/запрещённые ключи — ошибки | PASS | PASS (та же функция) |
| 8 | Save «abc» / «1,5,5» / `{"model": "x"}` — окно «Invalid Profile Parameters» с `Profile "Local proxy"`, **ничего не записано** (general/llm_settings) | PASS | FAIL (полей не было, Save молча проходил) |
| 9 | Save «1,5» → на диске `timeout_min: "1.5"` | PASS | FAIL (нет) |
| 10 | Старый формат профиля: Save чист, новые ключи не дописываются | PASS | PASS |
| 11 | Легаси-текст: закрытый порт 127.0.0.1 → `[MT proxy not running. Start it.]` | PASS (отд. прогон, лог в §7) | — (код не менялся) |

### 4.2 Q.2 — `batch-qa_q2_probe.py` (та же схема; реальные `call_custom_mt`/`create_llm_client` на fake-endpoint = сетевая ловушка)

| # | Проверка | post | pre |
|---|---|---|---|
| 1 | Панель, `![Image](y.png)`: 0 запросов; ряд = исходник, не ошибка, link-only | PASS | FAIL (запрос ушёл, ряд «TRANSLATED-OK») |
| 2 | Панель, `![Image](y.png).` (точка после ссылки): то же | PASS | FAIL |
| 3 | Панель, смешанная строка: запрос уходит (1), ряд обычный | PASS | PASS |
| 4 | Панель, LLM Fetch-кнопка на link-only: кнопка есть, клик → 0 запросов, ряд с исходником | PASS | FAIL (запрос ушёл) |
| 5 | Попап (авто MT+LLM), link-only: 0 запросов, 2 ряда с исходником (оба блока) | PASS | FAIL |
| 6 | Попап: Enter-вставка эмитит исходник (не пометку) | PASS | FAIL (эмитил перевод) |
| 7 | Попап (режим Fetch-кнопок): MT-ряд link-only; клик Fetch → 0 запросов, ряд с исходником | PASS | FAIL |
| 8 | Попап, смешанная строка: запрос уходит, ряды обычные | PASS | PASS (один FAIL в pre = ожидание 2 рядов в fetch-режиме — дефект пробы, исправлен, данные корректны) |

**Итог: post 18/18 PASS; pre 12 FAIL = документация старого поведения; смешанные строки идентичны в обоих деревьях.**

### 4.3 Q.6 — `batch-qa_q6_probe.py` (endpoint с задержкой 1.5 с; закрытие в момент запроса)

| # | Проверка | post | pre |
|---|---|---|---|
| 1 | Попап закрыт при работающем авто-fetch: закрытие **0.001 с** (pre 1.008 с), флаг `_closed` | PASS | FAIL (блокировка ~1 с, флага нет) |
| 2 | После ответа сервера: 0 строк в закрытом попапе, `translation_selected` не эмитится | PASS | FAIL (2 строки дописаны в закрытый UI) |
| 3 | Потоки завершены, `_DETACHED_WORKERS` пуст | PASS | FAIL (реестра нет) |
| 4 | Панель: закрытие 0.000 с (pre 1.010 с), 0 поздних строк (pre 1), потоки завершены | PASS | FAIL |
| 5 | Fetch-row воркер (кнопка LLM): закрытие 0.001 с, ряд не появился (pre появился), потоки завершены | PASS | FAIL |
| 6 | Логи прогонов: без Traceback/RuntimeError/QThread-destroyed (оба дерева) | PASS | PASS |

**Итог: post 19/19 PASS.**

### 4.4 Полный оффскрин-набор (16 этапов) — `batch-qa_run_full.sh` (копия раннера M2, tag `qa`, фикстуры regress засеяны из batch-m2, sha-сверка: `39abb383…`/`c079e760…`/`c9c80973…`)

fb(9.4h), profiles(9.4f), qtchat, statusbar-prof, e2e, S-clean, S-upgrade, regress, smoke, termbase, about, save modern, save legacy, r9 a, r9 ctrl, r9 rm — **16/16 зелёные** (PROBE DONE ×8, RESULT OK ×4, SMOKE OK 42 пункта, regress OK). Regress-хэши **байт-идентичны M2/G3.2e**: `5a12501f934a589c` (txt), `44828d90` (docx), `c413d563` (tmx). S-upgrade HASH-DIFF пуст (transient `workbench/ai_assistant/index.json` — известный артефакт даты, 9.4h). QThreadStorage-шум в 4 логах идентичен логам M2 (паритет). Остаточных процессов python/java после набора нет.

### 4.5 Статика (до и после suite — идентична)

| Метрика | База M2 | Q-A | Вердикт |
|---|---|---|---|
| AST chain | 883/0 | **893/0** | +10 резолвящихся вызовов (виджеты блока Q.1); 0 unresolved — новая база |
| pyflakes | 548 (126/4) | **548 (126/4)** | идентично |
| py_compile канонический (вне docs/) | 109/0 | **109/0** | OK |
| py_compile справочный (все tracked .py) | 208/0 | **214/0** | +6 аудит-скриптов (recon + 3 пробы батча); 0 ошибок |
| headless imports | 90/2 (setuptools, fitz) | **90/2** | известные |
| grep-gate | CLEAN | **CLEAN** (вкл. quicktrans.py) | OK |

**Заметка среды:** пакет `pyflakes` отсутствовал в `E:\Dev\python-embed` (последний раз фиксировался в M2 2026-10-21) — переустановлен `E:\Dev\python-embed\python.exe -m pip install pyflakes` (4.0.3), после чего статика воспроизводится 1:1.

---

## 5. Защиты (что не тронуто)

- `modules/llm_clients.py`, `modules/settings_service.py`, `modules/bilingual_markdown_handler.py` и остальные 89 модулей — байт-идентичны базе (правки только `Supervertaler.py` + `modules/quicktrans.py`).
- Формат хранения: миграции settings.json нет; ключи пишутся только при непустом значении; старые файлы читаются без изменений (пробы).
- LLM-редактор AI Settings (:19476–19592) и его Save (:23290–23301) не менялись — MT-редактор копирует образец.
- Легаси-конвенция ошибок QuickTrans (`[...]`) сохранена; тексты `[MT proxy not running. Start it.]` / `[Custom MT: endpoint unreachable.]` / `[Custom MT error: …]` — только для реальных сетевых состояний.
- Мёртвая цепочка результатов (`_fetch_llm/_mt_translation_async`, `_add_mt_and_llm_matches`) не правлена (рекон §B).
- `_reset_and_refetch` попапа (смена языков/re-translate при открытом окне) — вне объёма Q.6, не тронут.
- Реальные пользовательские данные: все пробы — изолированные профили/стабы + loopback; QSettings-запись геометрии попапа (HKCU) — штатная, как в проде и в пробах прежних батчей.
- `modules/settings_service.py` не коммитился (CRLF-артефакт, без изменения контента).

---

## 6. Ручные тесты (для Дмитрия)

Сервер для тестов: ваш локальный MT-прокси (как настроен, например `http://127.0.0.1:1234/v1`); модель — любая рабочая. Восстановление настроек после каждого теста: вернуть поля «Max tokens», «Request timeout, min», «Extra request body (JSON)» в пустое состояние (пусто = значения по умолчанию) и нажать Save.

### Обязательные

**T-QA.1 — Поля MT-профиля сохраняются, неверные значения блокируют Save.**
Цель: убедиться, что три новых поля в MT-профиле проверяются и сохраняются.
Шаги: 1) Меню Settings → ⚡ QuickTrans, секция «Custom MT endpoint»; 2) выберите существующий профиль; 3) в поле «Max tokens:» введите `abc`, нажмите «💾 Save QuickTrans Settings»; 4) прочитайте окно; 5) очистите «Max tokens:», в поле «Request timeout, min:» введите `1,5`, нажмите Save; 6) закройте Settings и откройте снова на той же вкладке.
Ожидание: шаг 3–4 — окно «Invalid Profile Parameters» с текстом `Profile "имя вашего профиля": 'Max tokens' must be a positive whole number…`, настройки НЕ сохранены (вкладка остаётся открытой); шаг 5 — Save проходит; шаг 6 — в поле «Request timeout, min:» стоит `1.5` (с точкой).
Провал: Save с `abc` проходит без окна; или после `1,5` в поле осталась запятая; или поле пустое после сохранения.

**T-QA.2 — Сегмент только с картинкой не отправляется в перевод.**
Цель: убедиться, что QuickTrans не делает запрос для сегмента из одной Markdown-ссылки на картинку.
Подготовка: создайте в Блокноте файл `D:\Temp\qa_link_test.md` из двух строк: строка 1 — `![Image](Figure1.png)` (только ссылка на картинку), строка 2 — `![Image](Figure2.png) see this figure` (ссылка плюс обычные слова).
Шаги: 1) импортируйте файл (Import Document); 2) поставьте курсор в сегмент со строкой-ссылкой (`![Image](Figure1.png)`); 3) нажмите Ctrl+Shift+Q (попап QuickTrans); 4) посмотрите строки результатов; 5) кликните по строке №1; 6) в логе вашего MT-прокси проверьте, приходил ли запрос.
Ожидание: в попапе строки содержат исходный текст `![Image](Figure1.png)` с серой пометкой «⤳ link-only — не отправлено»; клик вставляет в перевод ровно `![Image](Figure1.png)` (без пометки); в логе прокси НОВОГО запроса нет.
Провал: пришёл «перевод» от прокси (запрос в логе), или вставился текст с пометкой, или строки пустые.

**T-QA.3 — Смешанный сегмент (картинка + слова) переводится как раньше.**
Цель: убедиться, что обычные сегменты со ссылками не затронуты.
Шаги: в том же проекте поставьте курсор во второй сегмент (`![Image](Figure2.png) see this figure`), Ctrl+Shift+Q.
Ожидание: строки — обычные переводы (пометки «link-only» нет); в логе прокси запрос есть.
Провал: пометка «link-only» на смешанном сегменте или отсутствие запроса.

**T-QA.4 — Закрытие QuickTrans во время запроса: без ошибок и без поздних результатов.**
Цель: убедиться, что попап можно закрыть, не дожидаясь ответа.
Шаги: 1) выберите обычный текстовый сегмент (без ссылок); 2) Ctrl+Shift+Q; 3) сразу, пока строки ещё грузятся, нажмите Esc; 4) подождите 15–20 секунд, наблюдая за приложением и консолью (View → Log).
Ожидание: попап закрывается мгновенно; после ответа прокси ничего не появляется, новых ошибок в логе нет.
Провал: попап «завис» перед закрытием (~1 секунда и больше), после закрытия появились строки/ошибки.

### Опциональные (покрыты пробами)

- **T-QA.5 (опционально / covered by probe Q.1 #5–6):** в MT-профиле «Request timeout, min:» = `0,02`, источник ошибки — медленный эндпоинт: красная строка `[Error: … timed out … profile 'имя'…]` вместо `[MT proxy not running. Start it.]`. После теста вернуть поле в пустое.
- **T-QA.6 (опционально / covered by probe Q.2 #4–7):** вкладка ⚡ QuickTrans под сеткой и Fetch-кнопка AI-блока в попапе на сегменте-картинке — ряд с исходником и пометкой, запросов нет.
- **T-QA.7 (опционально / covered by probe Q.6 #5):** закрытие попапа при работающей кнопке Fetch (AI) — аналогично T-QA.4; платный LLM-вызов НЕ отменяется — докатывается на сервере (см. §3.2).

---

## 7. Артефакты (docs/refactoring/audits/)

- `batch-qa_q1_probe.py` / `batch-qa_q1_result_{post,pre}.json` / `batch-qa_q1_run_{post,pre}.log` — пробы Q.1 (+ inline-прогон легаси-текста: закрытый порт → `[MT proxy not running. Start it.]`, вывод `LEGACY_REFUSED_TEXT_OK` в §1.3; в JSON пробы не входит).
- `batch-qa_q2_probe.py` / `batch-qa_q2_result_{post,pre}.json` / `batch-qa_q2_run_{post,pre}.log`.
- `batch-qa_q6_probe.py` / `batch-qa_q6_result_{post,pre}.json` / `batch-qa_q6_run_{post,pre}.log`.
- `batch-qa_run_full.sh` (раннер) + 16 логов этапов `batch-qa_{probe_qa_fb,probe_qa_profiles,probe_qa_qtchat,probe_qa_statusbar_prof,e2e_after_qa,probe_after_qa_clean,probe_after_qa_upgrade,regress_after_qa,smoke_after_qa,tb_after_qa,about_after_qa,probe_qa_save,probe_qa_save_legacy,probe_qa_r9_a,probe_qa_r9_ctrl,probe_qa_rm}.log` + `batch-qa_run_full_main.log`.
- `batch-qa_static_qa.log` / `batch-qa_static_qafinal.log` (статика до/после suite — идентична).
- Снимки базы: `qa/recon/snaps/` в stage-каталоге (Supervertaler.py.HEAD `0189f591…`, quicktrans.py.HEAD `6a6812be…`, llm_clients.py.HEAD `93e99552…`), worktree `qa/head-wt` (база `090810fe`).

## 8. Журнал вопросов

- **Q1 (Q.1, формат таймаут-подсказки):** текст таймаут-ошибки завершается «Increase 'Request timeout' in Settings → AI Settings (profile fields)» — формулировка из llm_clients (общая для LLM и MT). Для MT поля живут в Settings → ⚡ QuickTrans. Текст не менял (правка llm_clients вне объёма). Подтвердить/поправить текст в отдельном docs-проходе?
- **Q2 (Q.1, порядок сохранения):** при невалидном MT-профиля Save блокируется ДО записи чего-либо (включая чекбоксы QuickTrans-таба). До правки чекбоксы сохранялись раньше профилей — теперь при ошибке придётся нажать Save дважды (после исправления). Приемлемо?
- **Q3 (Q.2, вид ряда):** на link-only сегменте ряд показывается для каждого включённого провайдера (как обычные результаты) — все с одинаковым исходником и пометкой. Альтернатива — один общий ряд без чипа провайдера. Сделано по первому варианту (не менял структуру рядов); подтвердить.
- **Q4 (Q.2, NBSP-контекст):** вставка link-only исходника идёт через `setPlainText` в 3 известных местах NBSP-экспозиции (список M2.3, QuickTrans-вставки 35785/7519/7523) — NBSP в исходнике при вставке нормализуется Qt (та же известная проблема M2.3, вне объёма Q-A; вставка link-only редко содержит NBSP).
- **Q5 (Q.6, app-exit):** при выходе из приложения с работающим QuickTrans-запросом детачнутый поток живёт до ответа сервера; принудительное завершение интерпретатора в этот момент может напечатать Qt-предупреждение (не воспроизводится в пробах; поведение не хуже базы, где wait(1000) отваливался по таймауту).
- **Q6 (новая база chain):** AST chain 883 → **893** (+10 вызовов блока виджетов Q.1, все резолвятся); дальнейшие батчи сверять с 893/0.
- **Q7 (среда):** `pyflakes` пропал из бандл-рантайма между M2 и Q-A (последний задокументированный прогон — M2, 2026-10-21); переустановлен (4.0.3). Если кто-то чистил site-packages — проверить, не пропало ли ещё что-то (`pip check` чистый).
- **Q8 (Q.1, тултип таймаута):** тултип MT-поля «How long a single request may take (minutes) for this profile — applied to the SDK client and the request itself…» — сокращён против LLM-версии (убрано «the proxy client», у MT-вызова его нет). Подписи/плейсхолдеры/дефолты идентичны LLM.

## 9. Не тронуто / вне объёма

- Пакетный MT-диалог/воркер (`_translate_with_mt`) — без изменений; поля применяются автоматически через активный профиль.
- `_reset_and_refetch` попапа (quit/wait при re-translate), вставка TM/черновиков, Match Panel — не тронуты.
- Тестовая сборка не пересобиралась (решение Дмитрия); пакет для пересборки — §0.
- Пуш не выполнялся; коммиты локальные: `4535b46c` (Q.1), `46c174ce` (Q.2), `dd1c5b97` (Q.6) + финальный docs-коммит. **Стоп до вердикта координатора.**
