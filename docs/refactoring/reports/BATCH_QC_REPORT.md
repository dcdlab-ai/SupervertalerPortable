# ОТЧЁТ BATCH Q-C — NBSP у корня, выбор профиля для Proofreading/пакета, connect-timeout

Основание: промпт `docs/refactoring/prompts/Promt - EXTRACTION BATCH Q-C.txt` (Дмитрий, 2026-10-25);
Q-B отчёт §5 (Q.7-анализ), RECON Q.0 §G. Три кодовых коммита + этот docs-коммит. Пуш НЕ выполнялся.

## 0. Коммиты и пакет файлов

| Коммит | Под-батч | Суть |
|---|---|---|
| `b9be50eb` | Q.7r | NBSP у корня: чтение ячейки для модели через `toRawText` (хелперы в монолите и quicktrans) |
| `f3fede01` | Q.5 | QComboBox профиля в диалогах Proofreading и пакетного перевода (+MT-профиль в пакетном) |
| `bc9a600a` | Q.8 | Q.8b connect-timeout 15 с + `LLMConnectionError` + разделение ретраев; Q.8a — без правки кода (не воспроизводится) |
| (этот) | docs | отчёт, PROJECT_STATUS, промпт, артефакты проб/регрессии/статики |

### Изменённые файлы (worktree-sha256, длины, EOL)

| Файл | До (0e1f0f97) | b9be50eb | f3fede01 | bc9a600a (HEAD) | EOL |
|---|---|---|---|---|---|
| `Supervertaler.py` | 55 573 строк, `bf8f64f2faaa3085…` | 55 598, `af5a334a04f2e417…` | 55 703, `adac689efafaabc8…` | 55 712, `c1a3f17c571c26658b4c2d459913147bd686a63d146e1a3199429ea10fd9bbeb` | CRLF (CR = числу строк, 55 712; одиночных LF — 0) |
| `modules/quicktrans.py` | 2 020, `610bc42d0ff09255…` | 2 035, `9c422339137790fb152ef4e81c5ff6ecc45f545d7fe89ab6c0fd665d3828bdac` | — | — | LF (CR 0) |
| `modules/llm_clients.py` | 853, `e1c13c64e591a85d…` (worktree, CRLF) | — | — | 932, `931b43ab888b815ee32311d80671342b16ce4bd881f754e82b1053bed96b6734` | CRLF в worktree (CR = 932), git-blob LF |

Прочие файлы не менялись: `modules/workers/proofread.py` (воркер вычитки не тронут — параметры уже kwargs),
`modules/settings_service.py` (не коммитился и не менялся), тестовая сборка `D:\SupervertalerPortable_test\` не обновлялась.
`py_compile` после каждой правки — 0 ошибок; pyflakes по изменённым модулям: llm_clients 0, quicktrans 3 (= база файла).

## 1. Q.7r — NBSP: шаг 0, реализация, пробы

### 1.1 Шаг 0 (до правок; `batch-qc_q7r_step0_qt.py`, PyQt 6.11.0 / Qt 6.11.0, offscreen) — 23/23 GREEN

- (а) `setPlainText` с NBSP хранит NBSP в документе: текст блока (`QTextBlock.text`) и курсора
  (`QTextCursor.selectedText`) содержат `\xa0`;
- (б) `document().toRawText()` возвращает NBSP (2/2), а `toPlainText()` даёт `'a b c d'`;
- (в) `toRawText` + замены разделителей (U+2029/U+2028/U+FDD0/U+FDD1 → `\n` — ровно как в toPlainText)
  равен `toPlainText()` с единственной разницей NBSP: 6 кейсов (multi-block, края, серии, табы) +
  инъекция U+2028 курсором;
- (г) ручная правка соседнего символа (QTest.keyClicks между `a` и `\xa0b`) и Delete символа после
  NBSP — NBSP сохраняется (`'ax\xa0b'`, `'a\xa0cd'`).
WYSIWYG-ветка (`batch-qc_q7r_step0_wysiwyg.py`, реальный `_wysiwyg_document_to_tagged_text` на
заглушке-self): 5/5 — fragment-чтение и setHtml-путь NBSP сохраняют НАТУВНО → правка не нужна.

### 1.2 Реализация (вместо гибрида 14 сайтов из Q-B §5.4)

1. `Supervertaler.py`: модульный хелпер `_cell_text_keep_nbsp(widget)` (перед `class
   EditableGridTextEditor`, :3199) — `toRawText` + 4 замены разделителей. Применён ровно в 4 точках
   обработчика `on_target_text_changed`: не-WYSIWYG чтение (:33154→33169), WYSIWYG-fallback
   (:33150→33165) и ОБА сравнения display (:33241→33261, :33247→33267 — нормализованное сравнение
   заставляло бы перерисовывать display при каждом нажатии клавиши в NBSP-ячейке).
2. `modules/quicktrans.py`: модульный хелпер `_field_text_keep_nbsp(field)` (тот же смысл) —
   `PanelResultRow.current_text()` (:507→521) и ветка «весь текст» в `_on_paste` (:503→517).
   Это ровно пункт 3 промпта: чтение поля, которое уходит в модель через `translation_selected` →
   `_insert_quicktrans_translation`. Ветка с выделением (`selectedText`) NBSP сохраняет — проверено шагом 0.
3. WYSIWYG — не правлена (§1.1). Остальные `toPlainText` (UI/поиск/отображение) — не тронуты.
   Чтения ячейки в модель после вставки: живых сайтов, кроме обработчика и current_text, НЕТ —
   два чтения `toPlainText()` в popup-closure (:7529) и панели (:35917) сидят в МЁРТВОМ коде
   (guard `hasattr(self,'segments')` всегда False) и по промпту не тронуты; трассировки стека в пробе
   подтверждают, что записей модели кроме сайта/обработчика/`update_status_icon` нет.

**Механизм защиты всех 14 сайтов без blockSignals:** guard обработчика `new_text == old_target`
теперь сравнивает СЫРОЙ текст с моделью. Сайты, пишущие модель до `setPlainText` (№3,5–14 из §5.2),
после вставки получают ранний return — без второй записи модели, undo-дубля и статуса (для текста
БЕЗ NBSP так работало и раньше — поведение унифицировано). Сайты QuickTrans (№1/2/4), где модель
писал только обработчик (явная запись — мёртвый код), теперь получают NBSP-текст в модель от
обработчика. Повторная вставка того же текста — guard, без нового undo (идемпотентность, проба F).
Мёртвая явная запись и фантомный `mark_segment_modified` НЕ тронуты (идут в 8.18).

**Находка регрессии (не продукт, для протокола):** вторая undo-запись в `_auto_insert_tm_match`
в PRE-прогонах — тройка `[(site raw), (handler normalized), (status-only)]` — раскладывается
трассировками на: сайт (:52079), обработчик (старый код перезаписывал модель нормализованным
текстом) и `update_status_icon` (:37287 — статусная undo-запись с old==new target, существующее
поведение, не связано с NBSP). В POST обработчик гасится guard'ом, остаётся сайт + статусная запись.

### 1.3 Пробы (`batch-qc_q7r_probe.py`: полное приложение, изолированный iso-профиль, fake loopback
endpoint с NBSP-ответами, сетевая ловушка, заглушки модалок; pre — worktree на HEAD 0e1f0f97)

**POST 26/26 PASS / PRE 16/26 (10 FAIL = документация старой потери NBSP).** Пути:
(а) панель QuickTrans: реальный Fetch LLM-ряда → ряд с `\xa0` → Ctrl+N (`insert_match_by_number`)
→ модель `'Paneel\xa0vertaling\xa0NBSP'`, ровно 1 undo-запись с сырым текстом, статус не меняется
(обработчик меняет только confirmed→draft); виджет показывает текст; PRE — модель с пробелами.
(б) TM: `search_and_display_tm_matches` 100% autofill → `'TM\xa0vol\xa0zin'` (PRE `'TM vol zin'`,
undo-тройка raw→normalized); `_auto_insert_tm_match` → единственная текстовая перезапись — сайта
(PRE — вторая, нормализованная, от обработчика).
(в) пакетный LLM-перевод → все targets `'Batch\xa0antwoord\xa0N'`, статусы draft (этот путь уже был
защищён M2.3 display-записью; теперь и обработчик безопасен) — PASS и в PRE.
(г) ручная правка соседнего символа (QTest в ячейку с NBSP) → `'BatchX\xa0antwoord\xa01'`
(PRE — пробелы), 1 undo, статус draft.
(д) Ctrl+T → `'CtrlT\xa0antwoord'`, draft (PRE — пробелы).
(F) идемпотентность: повторная вставка того же текста дважды — 0 новых undo, NBSP в модели.
(G) экспорт txt → файл содержит `\xa0` (PRE — пробелы). Сетевая ловушка пуста.
Регрессии по каждому пути: статусы/undo/TM-debounce/превью — как до правки (см. JSON проб);
экспортёры txt/docx/tmx читают модель (grep: toPlainText у экспортёров нет), 16-этапный набор
подтверждает байт-идентичность экспортов (§4).

## 2. Q.5 — выбор профиля в диалогах

### 2.1 Реализация

- **Proofreading** (`show_proofread_dialog` :39167–39175 → комбобокс, :39283+): read-only метка
  `📊 Using: …` заменена на `QComboBox` имён Custom LLM-профилей (по умолчанию активный; пустой
  список — отключённый combo + прежний шлюз в `_run_proofreading`). На accept — модель выбранного
  профиля + `profile_name` в `_run_proofreading(...)`; гейт `_custom_llm_ready(settings, profile_name)`
  и резолв `_get_active_custom_profile(settings, profile_name)` (endpoint/ключ/**kwargs) — от
  выбранного профиля. `ProofreadWorker` не менялся.
- **Пакетный перевод** (`translate_batch` :50507–50520 → два комбобокса): LLM-комбо (Custom LLM
  профили) + MT-комбо (включённые Custom MT профили с endpoint; по умолчанию активный MT) —
  переключатель «LLM / MT / TM» в диалоге ЕСТЬ, поэтому по промпту добавлен MT-список. Каждый
  пикер активен только в своём режиме. LLM-ветка: гейт/модель от выбранного, `_batch_profile_name`
  сохраняется для retry-проходов (воркер-подготовка :50974 резолвит профиль и kwargs по нему, в т.ч.
  на бездиалоговых повторах). MT-ветка: `_batch_mt_profile_name` → `PreTranslationWorker(mt_profile=…)`
  → `_translate_with_mt(segment, profile=…)` → `call_custom_mt(profile=…)` (необязательный параметр;
  None = активный MT, как раньше); `provider_info` показывает эффективное имя MT-профиля.
  `_get_active_custom_mt_profile` получил `profile_name` (зеркально LLM-твину).
- Выбор действует только на запуск: активные профили и settings.json не пишутся (проверено пробой).
- Ctrl+T и QuickTrans не менялись. Воркеры не менялись (кроме сквозного kwarg `mt_profile`).

### 2.2 Пробы (`batch-qc_q5_probe.py`: два fake-endpoint'а A/B с разными моделями и параметрами —
B: max_tokens 777 + extra_body `{"foo":"bar"}`; scripted `QDialog.exec` выбирает профиль; pre —
worktree на b9be50eb)

**POST 20/20 PASS / PRE 10/13 (FAIL = выбор невозможен, все запросы в активный A).**
P1 вычитка без смены выбора → A, модель llm-a, заметки `proofreading_notes` с ключом llm-a;
P2 вычитка с выбором B → только B, llm-b, max_tokens 777 в теле, foo=bar смержен, 0 запросов в A,
активный остаётся A, settings.json байт-идентичен сиду; P3 пакет LLM без смены → A/llm-a
(идентично до правки); P4 с B → B/llm-b/777/foo; P5 пакет MT с B → только B, модель mt-b
(raw_mode: тело = исходный текст), 0 в A; P6 пустой список профилей → прежнее сообщение шлюза
«Custom LLM profile is not configured», 0 запросов. Ловушка пуста.

## 3. Q.8 — подключение и таймаут; двойные скобки

### 3.1 Q.8b шаг 0 (`batch-qc_q8b_step0_cases.py`, текущий код ДО правок) — гипотеза подтверждена

| Случай | Время | Исключение (класс → cause) | Текст |
|---|---|---|---|
| TEST-NET 192.0.2.1, дефолт 600 с | **64.3 с** | LLMTimeoutError ← APITimeoutError (ConnectTimeout) | «…timed out after 10 minutes (600 s) — profile 'Probe profile'.» |
| TEST-NET, профиль 0.05 мин (3 с) | 10.5 с | LLMTimeoutError ← APITimeoutError | «…timed out after 0.05 minutes (3 s)…» |
| Закрытый порт 127.0.0.1:1 | 8.2 с | APIConnectionError (ConnectError) — сырой openai | «Connection error.» |
| Молчащий сервер (принял и молчит), 3 с | 10.3 с | LLMTimeoutError ← APITimeoutError (ReadTimeout) | прежний текст |

Наблюдение Дмитрия (~65 с, сообщение про 10 минут) воспроизведено точно: TCP-connect Windows
~21 с × 3 попытки SDK + паузы; httpx.ConnectTimeout попадает в timeout-ветку SDK → APITimeoutError,
llm_clients пишет текст про READ-таймаут.

### 3.2 Реализация Q.8b (`modules/llm_clients.py` — единственное место создания клиента: чат,
vision-путь и MT едут через него; `Supervertaler.py` — ветка в `call_custom_mt`)

1. `httpx.Timeout(<read бюджет профиля>, connect=CONNECT_TIMEOUT_SECONDS=15.0)` — и на клиенте,
   и в per-request `api_params["timeout"]` (конвенция SDK).
2. Новое исключение `LLMConnectionError(LLMResponseError)` с одной строкой:
   «Cannot connect to \<host:port\> within 15 s — host unreachable or server stopped — profile 'Имя'.»
   Без упоминания read-таймаута. Возникает для: APITimeoutError с cause=httpx.ConnectTimeout и для
   APIConnectionError без ответа сервера. Настоящий read-таймаут — прежний LLMTimeoutError/текст.
3. Ретраи: у SDK (openai 3.24) бюджет ЕДИНЫЙ на клиенте, отдельной ручки для connect-ошибок нет
   (проверено по `_base_client.py`), поэтому `max_retries=0` на клиенте, а семантика SDK
   воспроизведена собственным циклом в `_call_openai_with_usage`: ретраятся только STATUS-коды
   408/409/429/5xx (2 повтора, backoff 0.5·2ⁿ ≤ 8 с, Retry-After учитывается) и READ-таймауты
   (как у SDK); connect-ошибки НЕ ретраятся. Тела запросов байт-идентичны (§3.4).
4. `call_custom_mt`: ветка `except LLMConnectionError` ПЕРЕД `except LLMResponseError` —
   localhost → прежний «[MT proxy not running. Start it.]» (проверенное Дмитрием поведение),
   удалённый хост → «[Error: Cannot connect …]».

### 3.3 Q.8a — двойные скобки «[[Error: Connection error.]]»: НЕ воспроизводится, код не правлен

Проба `batch-qc_q8a_step0_probe.py` (мёртвый endpoint 127.0.0.1:1, реальный `_call_llm_translation`
прямо + реальный Fetch панели): LLM-ряд — «[Error: Connection error.]» (одна пара), MT-ряд —
«[MT proxy not running. Start it.]». Попап рендерит текст ряда дословно (`QLabel(translation)`),
вся история git не содержит композиции скобка-вокруг-скобки (`git log -S "[[Error"` пуст).
Проба из промпта (одна пара скобок в LLM- и MT-ряду, прочие форматы не менялись) — ЗЕЛЁНАЯ на
текущем коде и перепроверена после Q.8b (§3.4: s3_llm_remote_single_brackets). Вопрос QC1 —
нужен контекст наблюдения (сборка/сервер/скриншот); возможный источник — ответ прокси-сервера
самого Дмитрия, возвращающего строку со скобками как контент.

### 3.4 Пробы Q.8b (`batch-qc_q8b_probe.py`; pre — worktree на f3fede01)

**POST 9/9 PASS / PRE 3/9 (FAIL = старое поведение, см. §3.1).**
S1/S4: fake-endpoint 500,500,200 → успех на 3-й попытке (3 запроса) на ОБОИХ деревьях (в PRE —
ретраи SDK, в POST — наш цикл); **тело запроса байт-идентично** (sha256 `44f972f25163…` совпадает).
S2: TEST-NET дефолт → LLMConnectionError за ~15 с с точным шаблоном (PRE: 64.4 с, «10 minutes»);
закрытый порт → LLMConnectionError быстро, БЕЗ ретраев (PRE: сырой APIConnectionError 7.4 с);
молчащий сервер 3 с → LLMTimeoutError 10.4 с с прежним текстом и временем (сохранено на обоих).
S3: MT-ряд на мёртвом localhost — прежний «[MT proxy not running. Start it.]»; LLM-ряд на мёртвом
удалённом хосте — «[Error: Cannot connect to 192.0.2.1:65500 within 15 s — host unreachable or
server stopped — profile 'LLM dead'.]», одинарные скобки (= проба Q.8a). Ловушка (без TEST-NET) пуста.

## 4. Регрессия

- **16-этапный набор** (`batch-qc_run_full.sh`, TAG=qc): fb/profiles/qtchat/statusbar/S-clean/
  S-upgrade/tb/about/save/save-legacy/r9-a/r9-rm/r9-ctrl — ЗЕЛЁНЫЕ. Три стадии первого прогона
  (e2e/smoke/regress) оборвались после постройки окна — конкурентные процессы статики на моей
  стороне (уборщик `kill_leftovers` сюиты между стадиями); перегнаны СОЛО: **e2e — verdict OK,
  5 запросов, тела байт-идентичны базе Q-B** (sha256 по отсортированным записям равны);
  **smoke — SMOKE OK**; **regress — RESULTS хэши `5a12501f934a589c` / `44828d90090f046d` /
  `c413d56372e69dd9` — байт-идентичны базе Q-B**; **S-upgrade HASH-DIFF пуст** (added/removed/
  changed/transient = []). Итог: 16/16.
- **Пробы Q-A/Q-B без изменений** (`batch-qc_run_qab_probes.sh`): Q.1 20/20, Q.3 17/17, Q.4 24/24,
  adapted panel 18/18; Q.2 11/16 и Q.6 18/19 — наборы FAIL РОВНО те же, что в базе Q-B
  (panel_link1_rows, panel_link2_rows, panel_mixed_requests, panel_mixed_rows_normal,
  panel_llm_button_present, panel_close_while_inflight — by-design панельные изменения Q-B,
  покрытые adapted-пробой).
- **Статика** (`batch-qc_static_run.sh`): AST chain 893/0 (= база), pyflakes 548/126/4 (= база),
  py_compile канонический 109/0 (= база), референсный 224/0 (было 217; +7 новых скриптов проб Q-C —
  вопрос QC4), headless 90/2 (известные setuptools/fitz), grep-gate CLEAN.

## 5. Защиты

- Попап Ctrl+Alt+Q не тронут (авто-запрос/клик/цифры/Enter — пробы Q-A re-run).
- Монолит: только описанные точки; мёртвая явная запись модели (:35916–35921/:7537–7542) и
  `mark_segment_modified` НЕ тронуты (8.18); blockSignals-обёрток на 14 сайтах НЕТ.
- Ctrl+T и QuickTrans-движок не менялись (пробы E/Q-B re-run).
- Воркеры: `ProofreadWorker` не менялся; `PreTranslationWorker` — только сквозной kwarg.
- settings_service.py не менялся и не коммитился; dev-рантайм не менялся (pyflakes внешний).
- Реальные данные не тронуты (все пробы — изолированные iso-профили); сетевые ловушки пусты;
  процессы чистились по PID/путям, не по имени образа; сирот после прогонов нет (проверено).
- EOL: Supervertaler.py и llm_clients.py CRLF (CR = числу строк), quicktrans.py LF (CR 0).

## 6. Ручные тесты для Дмитрия

Тестовая сборка НЕ содержит код Q-C (батчи её не обновляют). Для ручных тестов нужна пересборка
по правилам AGENTS.md — достаточно скопировать `Supervertaler.py`, `modules/quicktrans.py`,
`modules/llm_clients.py`. Решение за вами. Серверы: ваши локальные MT/LLM-профили. Тестовый файл:
создайте `E:\Dev\Work_temp\SupervertalerPortable\manual\test_qc.txt` из двух строк с НЕразрывным
пробелом (в Word/Блокноте++ вставьте U+00A0, напр. «Dutch\xa0text one» / «Dutch\xa0text two»).
Восстановление: проект не сохранять; статус/профили не менять.

**Обязательные:**

- **T-QC.1 — NBSP сохраняется при правке и вставке.** Открыть test_qc.txt (2 сегмента). Включить
  подсветку NBSP (View → Show Invisibles → Non-breaking Spaces — NBSP закрашивается фоном).
  Сегмент 1: щёлкнуть в ячейку перевода, дописать букву рядом с NBSP → закрашенный NBSP остаётся
  на месте. Скопировать источник в перевод (Ctrl+Shift+S или контекстное меню Copy Source) →
  NBSP закрашен. Сегмент 2: перевести Ctrl+T → если ответ сервера содержит NBSP, он закрашен.
  Затем File → Export → Simple Text и открыть файл в Блокноте++/Word: NBSP на месте (в Блокноте++
  виден через View → Show Symbol → Show All Characters как °-подобный символ). Провал: NBSP
  превратился в обычный пробел (закраска исчезла/экспорт без NBSP).
- **T-QC.2 — выбор профиля в Proofreading.** Настроить два профиля Custom LLM (A активен, B с
  другим endpoint/моделью; Settings → AI Settings). QA → Proofreading → Proofread Translation…:
  вместо строки «Using: …» — список профилей, по умолчанию A. Выбрать B → Start. Ожидание:
  комментарии вычитки помечены МОДЕЛЬЮ профиля B (вкладка Proofreading comments), в логе сервера B
  есть запросы, у сервера A — нет; Settings → AI Settings показывает по-прежнему активным A.
- **T-QC.3 — выбор профиля в пакетном переводе.** Translate → Batch Translate…: под чекбоксами —
  два списка («LLM profile», «MT profile»), активен LLM-список с профилем A. (i) Запуск с A →
  запросы идут к A (как раньше). (ii) Выбрать в «LLM profile» профиль B → Start → запросы только
  к B (лог сервера), модель B в логе; активный профиль A не изменился. (iii) Включить «MT» —
  LLM-список гаснет, MT-список активен; выбрать MT-профиль B → запросы MT только к его endpoint.
- **T-QC.4 — понятная ошибка недоступного хоста.** Остановить LLM-сервер, чей профиль указывает
  на УДАЛЁННЫЙ хост (не 127.0.0.1). Match Panel → QuickTrans → Fetch в AI-ряду: не более ~15–20 с —
  строка «[Error: Cannot connect to <хост:порт> within 15 s — host unreachable or server stopped —
  profile 'Имя'.]» одной строкой, ОДНА пара скобок. Для профиля на 127.0.0.1 с закрытым портом —
  прежний «[MT proxy not running. Start it.]» (MT-ряд). Провал: ожидание ~ минуты, сообщение
  «timed out after 10 minutes» или двойные скобки.

**Опциональные (покрыты пробами):** повторная вставка того же перевода из панели (Paste/Ctrl+N
дважды) не создаёт вторую запись undo (проба F); read-таймаут молчащего сервера даёт прежний текст
«timed out after …» (проба S2); пустой список профилей — прежний шлюз «Custom LLM profile is not
configured» (проба P6).

## 7. Артефакты

Пробы/шаги: `docs/refactoring/audits/batch-qc_q7r_*` (шаг 0 Qt + WYSIWYG + полная проба post/pre,
9 файлов), `batch-qc_q5_*` (проба post/pre, 5), `batch-qc_q8a_step0_*` (2), `batch-qc_q8b_*`
(шаг 0 + проба post/pre, 8). Регрессия: `batch-qc_run_full.sh` / `batch-qc_run_full_main.log`,
`batch-qc_e2e_*`, `batch-qc_regress_after_qc.log`, `batch-qc_smoke_after_qc.log`,
`batch-qc_probe_after_qc_{clean,upgrade}.log`, `batch-qc_run_qab_probes.sh`,
`batch-qa_q{1,2,6}_after_qc.json`, `batch-qb_q{3,4}_after_qc.json`,
`batch-qb_qa_panel_adapted_after_qc.json`. Статика: `batch-qc_static_run.sh`,
`batch-qc_static_{chain_headless_grep,pyflakes,pycompile}.log`. Стейдж-каталог:
`E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-qc\` (q7r, q5, q8, regress, static).

## 8. Журнал вопросов (с дефолтами; решает координатор)

| # | Вопрос | Мой дефолт |
|---|---|---|
| QC1 | Q.8a: «[[Error: Connection error.]]» не воспроизводится на текущем коде (прямой вызов, реальный Fetch панели и попап — одинарные скобки; в истории git двойной обёртки нет). Где вы её видели — сборка, сервер, скриншот? Код не правлен. | Считать наблюдение относящимся к окружению (например, ответ самого прокси со скобками в контенте); повторно рассмотреть по вашему репро |
| QC2 | Q.7r: для сайтов «модель пишет код ДО вставки» обработчик теперь гасится guard'ом (ранний return) — для NBSP-текстов так же, как и раньше для текстов без NBSP (унификация); побочные эффекты обработчика при программных вставках (undo-дубль, сброс confirmed→draft) не выполняются. Ок? | Да — это и была цель «у корня» |
| QC3 | Q.8b: ретраи SDK перенесены в наш цикл (у SDK одна ручка на всё): 5xx/429/408/409 и READ-таймауты ретраятся как раньше (2 повтора, backoff 0.5·2ⁿ, Retry-After), connect — никогда; заголовок `x-stainless-retry-count` теперь всегда 0 (тела не меняются). Ок? | Да |
| QC4 | РЕФЕРЕНСНЫЙ py_compile вырос 217→224 (+7 скриптов проб Q-C в docs/refactoring/audits); канонический 109/0 не изменился. Фиксировать 224/0 как новую базу? | Да |
| QC5 | LLMConnectionError-сообщение для МГНОВЕННОГО отказа (закрытый порт) тоже говорит «within 15 s» (единый шаблон из промпта), хотя отказ наступает быстрее. Ок? | Да (шаблон един, 15 с — верхняя граница) |
| QC6 | Первая итерация 16-этапного набора оборвала e2e/smoke/regress (моя конкурентная статика; уборщик процессов сюиты). Стадии перегнаны соло — все зелёные/идентичные. Считать набор 16/16? | Да |

Вердикт координатора: **ожидается**.
