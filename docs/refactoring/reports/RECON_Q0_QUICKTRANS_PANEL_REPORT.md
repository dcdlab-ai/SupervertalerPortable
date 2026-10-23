# RECON Q.0 — отчёт: подсистема Match Panel (блоки MT и AI/LLM), профили, выбор профиля для действий

Режим: ТОЛЬКО ЧТЕНИЕ. Код продукта не изменялся. HEAD: `8507dd55`
(`Supervertaler.py` — 55 456 строк, sha256 `65d50655727e5568…` — совпадает с записью M2.3;
`modules/quicktrans.py` — 1635 строк, sha256 `6a6812be6c7a…`).
Все ссылки ниже проверены по содержимому на этом HEAD. Артефакты:
`docs/refactoring/audits/recon-q0_inventory.py` (сканер) и `recon-q0_inventory.txt` (его вывод:
инвентарь вызовов, AST-проверки, 14 сайтов M2, сайты `is_image_links_only`, сайты `mtql_*`, статики).

---

## 0. Расхождения с описанием в постановке (зафиксировано, ничего не «заодно»)

| # | Утверждение в постановке | Факт на HEAD |
|---|---|---|
| 0.1 | «MT авто-запрос на каждый сегмент ко всем отмеченным профилям» | Реально, но **только для видимой панели** QuickTrans: `request_update` проверяет `isVisible()` (quicktrans.py:1400-1410); авто-MT на сегмент — quicktrans.py:1483-1488. Результаты идут в MT-блок панели, не в панель «Translation Results». |
| 0.2 | «блок Translation Results / чипы» | Старая цепочка панели Translation Results **мертва**: `self.results_panels = []` (Supervertaler.py:24951-24953, комментарий о deprecated), `assistance_widget` никогда не присваивается (AST: 0 присваиваний — inventory §2). Live-чип = только `MTSuggestionItem` QuickTrans. |
| 0.3 | M2.2(a) «чип с ошибкой LLM» | Находится в **недостижимой** цепочке: пишется в `results_panels` (Supervertaler.py:51136-51173, шлюз :51148), а панель мертва (0.2). Работает только «❌ AutoTagger» (M2.2b) — он на живом пути. |
| 0.4 | «в popup авто-MT» | В popup (Ctrl+Alt+Q) авто-запрос на showing **одновременно MT и LLM** по всем провайдерам (`start_fetching` 980-1036, вызов :554), результат — строки «Fetch: …» (1038-1100). На панели LLM **не авто**: только кнопка Fetch (1492-1494). |
| 0.5 | «MT endpoint — отдельный MT-сервер» | MT-запрос строится тем же `LLMClient` в режиме chat-completions (Supervertaler.py:47927-47933); отдельного MT-протокола нет. Строка ошибки «[MT proxy not running…]» (:47984) — легаси-текст. |
| 0.6 | «профили MT наследуются из AI Settings?» | **Не наследуются**: два независимых списка (`custom_openai_profiles` / `custom_mt_profiles`, defaults settings_service.py:276-283 с явным комментарием «independent of the AI custom endpoint»). Совпадает с наблюдением Дмитрия (Local_llama и сервер — разные). |
| 0.7 | «QuickTrans (Ctrl+Alt+Q) должен отменять LLM-запрос при закрытии» | Отмены сейчас **нет вообще** (H-раздел): closeEvent popup quicktrans.py:1293-1306 — только `quit()+wait(1000)`; начатый сетевой запрос продолжает выполняться. |
| 0.8 | «панель: кнопка Fetch + видимый список профилей MT» | Список профилей MT как рядов нет: панель показывает **метку провайдера и результат** (по enabled-фильтру mtql_*); профили с `enabled=False`/пустым endpoint молча выбрасываются (quicktrans.py:325-339). |

Прочие расхождения не обнаружены; картина A–I ниже подтверждает описание постановки.

---

## A. Цепочка «выделение → запрос MT/LLM»

### A.1 Живая цепочка (панель QuickTrans)

1. Сигналы таблицы (Supervertaler.py:25633-25639): `currentCellChanged` → `on_cell_selected` (def :37177);
   `itemClicked` → `on_cell_clicked` (def :40203) — клик по «#» (номер строки) = обычное выделение;
   клик по колонке Status игнорируется (:40217-40219); `itemSelectionChanged` → `on_selection_changed`
   (def :38144) → форвард в `on_cell_selected` (:38162).
2. `on_cell_selected`: мгновенный точный TM (:37198-37209 → `_show_instant_tm_match` def :51511);
   guard «та же строка» (:37211-37217); debounce **10 мс** (250 мс при фильтре) через
   `_deferred_lookup_timer` (:37239-37252) → `_on_cell_selected_full` (def :37526).
3. Внутри полной обработки: вызовы `_update_both_termlens` (def :14232) из :37497 (фильтр-путь),
   :37750 (TM-cache-hit), :37922 (miss). QuickTrans-блок :14271-14283: для обеих панелей
   (`quicktrans_panel`, `quicktrans_panel_match`) вызывается `request_update(source_text, src, tgt)`.
4. Панель (quicktrans.py): `request_update` :1400-1410 (работает только при `isVisible()`),
   собственный debounce **300 мс** (:1340-1343) → `_do_fetch` (:1448-1494):
   - `_fetch_token` — счётчик поколений запроса (:1459);
   - **MT: авто-запрос** по всем enabled-провайдерам (:1483-1488) через `MTFetchWorker`;
   - **LLM: только кнопки** «Fetch: <профиль>» (:1492-1494, `_add_llm_button` :1549-1608) —
     запрос уходит по клику кнопки (:1582-1585), не по выделению.
5. MT-воркер: `MTFetchWorker` (quicktrans.py:111-147, QThread): `run()` :125 → `fetch_single` (:127-134)
   на провайдера внутри `ThreadPoolExecutor(max_workers=6)` (:137); текст, начинающийся с «[»,
   трактуется как ошибка (:131).
6. LLM-воркер: `_call_llm_translation` (quicktrans.py:403-477): `create_llm_client(profile_name)`
   (:429-430 → Supervertaler.py:47988-48025, профильные kwargs :48022 → :47822-47851); строгий промпт
   без PM-шаблона (:443-454).
7. Stale-drop: результат принимает только текущее поколение `_fetch_token`
   (`_start_worker` :1496-1515, шлюз :1502-1508) — поэтому «остаётся только последний».
   Отмены сетевого запроса нет (H-раздел).
8. Popup (Ctrl+Alt+Q / Ctrl+Shift+Q, quicktrans.py:518-1306): `showEvent` :554 → `start_fetching`
   (:980-1036): строки заголовков и «Fetch: …»-строки по всем провайдерам MT+LLM сразу
   (:1006-1014, :1017-1019, worker :1027/:1036); результат строки — `_on_result_ready` (:1163-1197);
   клик по строке → вставка + закрытие (:1234-1237); цифры 1-9 — выбор (:1239-1246); Enter — вставка
   (:1285-1291).

### A.2 Мёртвая цепочка (не трогать, не удалять без решения координатора)

- `_schedule_delayed_lookup` (:39868) — внешних вызовов 0 (inventory §1);
- `_perform_delayed_lookup` (:39901) — вызывается только из lambda внутри мёртвой же цепочки (:39897);
- → `_fetch_llm_translation_async` (:51021) / `_fetch_mt_translation_async` (:51181): запись результата
  зашлюзована на `assistance_widget` (:51099, :51190-51194, :51207), который нигде не создаётся
  (`create_assistance_panel` def :25780 — вызовов 0);
- `_add_mt_and_llm_matches_progressive` (:51993) — stub `pass` (живой вызов из TM-цепочки :51770);
- `_add_mt_and_llm_matches` (:52276) — вызовов 0.

### A.3 TM-цепочка (живая, MT/LLM там нет)

`_schedule_mt_and_llm_matches` (:51621, `start(150)` :51637) → `_execute_mt_llm_lookup` (:51642) →
`_search_mt_and_llm_matches` (:51660): stale-abort по id сегмента (:51672-51675), `TMSearchWorker`
(:51750-51764, cancel предыдущего :51746-51747), stale UI-drop (:51849-51852); MT/LLM-часть — stub
(:51770 → :51993).

---

## B. Модель данных профилей

Файл: `<user_data>/workbench/settings/settings.json` (modules/settings_service.py:110-112).
Секции: `ui.llm_settings` (списки профилей + активные ключи, read :265-312, write :314-321) и
`general.mt_quick_lookup` (фильтры показа QuickTrans, write Supervertaler.py:20354).

### B.1 Ключи

| Ключ | Секция | Смысл | Defaults | Запись |
|---|---|---|---|---|
| `custom_openai_profiles` | ui.llm_settings | список LLM-профилей | [] (settings_service.py:276) | Supervertaler.py:23313-23319 |
| `custom_openai_active_profile` | ui.llm_settings | активный LLM | '' (:277) | :23264/:23319 |
| `custom_mt_profiles` | ui.llm_settings | список MT-профилей | [] (:282) | Supervertaler.py:20374 |
| `custom_mt_active_profile` | ui.llm_settings | активный MT | '' (:283) | :20375 |
| `mtql_custom_mt` | general.mt_quick_lookup | master-выключатель «показывать MT-профили» | — | :20330 |
| `mtql_<имя MT-профиля>` | general.mt_quick_lookup | {'enabled': …} — чекбокс «Show this profile in QuickTrans» | — | :20330-20343; читает quicktrans.py:325-339 |
| `mtql_llm_profiles` | general.mt_quick_lookup | фильтр показа LLM-профилей на панели (UI :20290-20304) | — | :20341-20343; читает quicktrans.py:365-381 |
| легаси mtql_* | general.mt_quick_lookup | инертные ключи (записываются, не читаются) | — | :20345-20352 |

### B.2 Поля профилей (различия MT vs LLM)

| Поле | MT | LLM | Где в UI |
|---|---|---|---|
| name / endpoint / model / api_key | + | + | MT :20149-20155; LLM в редакторе :19460-19579 |
| `raw_mode` («Send raw text only (MT mode)») | + (:20172-20179) | — | — |
| `enabled` («Show this profile in QuickTrans») | + (:20164-20170 → mtql_*) | — (для LLM фильтр панели: чекбоксы :20290-20304) | — |
| `supports_vision` | **—** | + (:19461-19470) | |
| `max_tokens` | **—** | + (:19482-19495) | |
| `timeout_min` | **—** | + (:19497-19509) | |
| `extra_body` (JSON) | **—** | + (:19511-19523) | |

Шаблоны нового профиля: MT — :20220 (`{'name','endpoint','model','api_key','raw_mode':True,'enabled':True}`),
LLM — :19609. Чтение расширенных полей: `parse_profile_request_fields`
(modules/llm_clients.py:211-270); потребление: `_custom_profile_request_kwargs`
(Supervertaler.py:47822-47851). **MT-путь kwargs не передаёт** (`call_custom_mt`, :47927-47933) —
live-запросы MT идут на дефолтах (16384 токенов, 600 с, без extra_body, vision False).

### B.3 Кто и какой активный профиль использует

| Действие | Профиль | Ссылки |
|---|---|---|
| QuickTrans MT (панель/popup) | **не активный**: все enabled-профили MT | quicktrans.py:325-339 |
| QuickTrans LLM (кнопка/строка) | профиль строки (profile_name) | quicktrans.py:429-430; Supervertaler.py:47786 (с name), fallback :386-400 |
| Batch, MT-ветка | активный MT (`custom_mt_active_profile`) | :5602-5617 → `call_custom_mt` :47904-47905 → :47873-47893 |
| Batch, LLM-ветка | активный LLM | :50851-50864 (profile_kwargs :50864) → PreTranslationWorker :50887+ |
| Proofreading | активный LLM (read-only метка в диалоге :39064-39068) | :39247, spawn :39255-39267 (kwargs :39266) |
| Одиночный Ctrl+T | активный LLM | :49079-49110 |
| Single MT в таблице | прямого живого вызова нет (путь :51181 мёртв) | — |

---

## C. Построение MT-запроса (`call_custom_mt`, Supervertaler.py:47895-47986)

- Клиент: `LLMClient(api_key, provider='custom_openai', model, base_url=endpoint, http_proxy)`
  (:47927-47933) — **chat completions**, не MT-протокол; ключ: профиль → `api_keys['custom_openai']`
  → `'not-needed'` (:47921-47924).
- raw_mode (:47941): «raw» → prompt = текст источника, system = «Translate from {src} to {tgt}.
  Output only the translated text — no quotes, notes, or explanations.» (:47943-47946);
  non-raw — расширенный промпт (:47948-47960). PM-шаблоны/глоссарий **не подмешиваются**.
- Вызов: `client.translate(text="", custom_prompt=…, system_prompt=…)` (:47962-47968); срезание
  кавычек ответа (:47969-47973).
- Ответ: `_parse_completion_response` (llm_clients.py:279-360): `choices[0].message.content` (:300-303);
  строгое усечение → `LLMTruncatedError` (:344-359). Ошибки сети: `call_custom_mt` перехватывает и
  возвращает строку «[MT proxy not running. Start it.]» (:47984) / «[Custom MT: endpoint unreachable.]»
  (:47985); QuickTrans показывает её как ошибку (`is_error`: startswith «[», quicktrans.py:131).
- Таймаут/токены: kwargs не передаются → дефолты `_effective_timeout_seconds` 600 с
  (llm_clients.py:423-432), `max_tokens` 16384 (:378); `extra_body` не передаётся (:803-804);
  `temperature` 0.3 (:798-800).
- Зависимость от llm_clients полная: общий класс, общий путь `_call_openai_with_usage` (:739-852),
  общий usage-log (:725-735) — **MT-запросы пишутся в тот же журнал LLM-расхода**, что и LLM.
- Типизированные ошибки (LLMTruncatedError/LLMEmptyResponseError/LLMTimeoutError, :171-204) MT-путь
  тоже может породить; в QuickTrans они схлопываются в строку «[...]».

MT vs LLM в запросе:

| Параметр | MT (QuickTrans/batch) | LLM |
|---|---|---|
| Источник endpoint/model | `custom_mt_profiles` | `custom_openai_profiles` |
| Промпт | фиксированный (:47943-47960) | PM-шаблон+глоссарий (single/batch, :51081-51088/:49xxx, :50xxx) или строгий в QuickTrans (:443-454) |
| max_tokens/timeout/extra_body/vision | нет (дефолты) | есть (per-profile) |
| usage-log | общий | общий |

---

## D. Варианты развития MT-профилей (пожелание 3)

### Вариант 1 — «свои поля у MT-профиля» (рекомендуется)

Добавить в редактор MT (секция :20110-20246) поля Max tokens / Timeout min / extra body
(копия UI LLM-редактора :19482-19523) и писать их в словарь профиля `custom_mt_profiles`;
в `call_custom_mt` (:47927-47933) передать `**self._custom_profile_request_kwargs(profile)`
(:47822-47851).
- Объём: ~+55-75 строк в монолите (UI+populate :20186-20199+sync :20201-20208+save :20360-20376),
  +1 строка в `call_custom_mt`; `modules/` не трогаем.
- Миграция settings.json: **не нужна** — поля опциональны, отсутствующие → дефолты = текущее
  поведение (`parse_profile_request_fields` это выдерживает, llm_clients.py:211-270).
- Batch MT и QuickTrans MT получают новые поля автоматически (общий `call_custom_mt`).
- Риск: низкий (UI + 1 вызов; поведение старых профилей не меняется).
- Vision для MT: по смыслу не нужен (изображения в link-only, F-раздел) — решение Дмитрия (вопрос Q2).

### Вариант 2 — объединить списки MT+LLM

Миграция (defaults и read :265-312, активные ключи, читатели :47873-47893/:5602-5617/quicktrans.py:325-339,
семантика mtql_*, два редактора UI). ~-40 строк нетто, но: ломает разделение MT/LLM-серверов
(факт Дмитрия), требует миграции файла и каскада читателей. **Не рекомендуется.**

### Вариант 3 — «наследовать поля из LLM-профиля при создании MT»

Копирование полей кнопкой в редакторе. Дублирование данных, рассинхрон. **Не рекомендуется.**

Ответ на пожелание 3 (наследование): lists независимы намеренно (settings_service.py:278-283);
вариант 1 даёт MT те же рычаги, не смешивая списки.

---

## E. Блоки результатов (чипы), вставка, Paste, NBSP

### E.1 Структура чипа

`MTSuggestionItem` (quicktrans.py:150-276): метка-шапка провайдера (:189-217) + текст перевода
`QLabel` с `TextInteractionFlags.NoTextInteraction` (:220-222) — **текст не выделяется и не редактируется**;
клик по элементу → `mousePressEvent` (:272-276) → вставка.

### E.2 Обработчики вставки и NBSP (находка M2.3 в QuickTrans)

| Путь вставки | file:line | setPlainText без blockSignals? |
|---|---|---|
| Панель: клик по чипу | quicktrans.py:1610-1611 → `_insert_quicktrans_translation` Supervertaler.py:35768-35793 | да (:35785) |
| Панель: Ctrl+1..9 | :45908 → `insert_match_by_number` quicktrans.py:1613-1626 → тот же :35785 | да |
| Popup: клик по строке | quicktrans.py:1234-1237 → closure `insert_translation` Supervertaler.py:7503-7533 | да (:7519, :7523) |
| Popup: Enter / цифры | quicktrans.py:1285-1291, :1239-1246 | те же :7519/:7523 |
| Popup: замена выделения | :7515 (`cursor.replaceSelection`) | не setPlainText |

Механизм M2.3 (NBSP → пробел при `setPlainText` без блокировки сигналов, proofrun — обёртка только
в `handle_progress_update` :50940-50942): **обе QuickTrans-вставки попадают в 14 неразобранных сайтов**
(7519, 7523, 35785 — из списка inventory §3; полный список 14 сайтов в отчёте M2.3). Итог: вставка
QuickTrans-перевода с NBSP молча нормализует NBSP в source-сегменте обратно в target.

### E.3 Пожелание 4 (кнопка Paste + редактируемое поле) — реализуемость

Редактируемое поле результата feasible: заменить `NoTextInteraction`-QLabel (:220-222) на
редактируемый `QTextEdit`/`QPlainTextEdit` per row и добавить кнопку «Paste», вставляющую
(выделение-aware, образец :35780-35784) с тем же `blockSignals`-обёрнутым `setPlainText`.
Сломается при удалении вставки по клику: `mousePressEvent` (:272-176…), панель
`_on_item_clicked` (:1610-1611), popup `_on_item_clicked` (:1234-1237), `insert_match_by_number`
(:1613-1626) + горячие клавиши Ctrl+1..9 (:45908), popup-цифры/Enter (:1239-1246, :1285-1291) —
минимальный объём замены: горячие клавиши оставить (вставить целый ряд), клик снять.

---

## F. Link-only сегменты (пожелание 2)

- Детектор `is_image_links_only` — modules/bilingual_markdown_handler.py:412-420 (regexes :408-409).
- В quicktrans.py — **0 gates** (inventory §4: ноль входов `is_image_links_only` в модуле).
- В продукте gates есть: 14+ вызовов (инвентарь §4: single Ctrl+T :49051-49076, batch MT/LLM,
  FuzzyFixer, proofreading, batch-failure handler — M1/M1e/M2.1).
- Предложение (для Q-батча): gate в `QuickTransPanel._do_fetch` (quicktrans.py:1448) и в popup
  `start_fetching` (:980): link-only source → в MT/LLM-блок кладётся исходник verbatim («⤳ link-only»),
  сетевой запрос не уходит; вставка — как обычный результат (статус draft только при вставке, как в M1).

---

## G. Выбор профиля: Proofreading / Batch / Ctrl+T

Сейчас — глобальный активный профиль, в диалогах только read-only метки:
- Proofreading: метка :39064-39068; профиль активный :39247; воркер `ProofreadWorker` spawn
  :39255-39267 (kwargs :50864-образец :39266; внутри modules/workers/proofread.py:86 LLMClient,
  :117 translate на батч).
- Batch: метка :50391-50403; профиль активный :50851-50864 → `PreTranslationWorker` :50887+.
- Ctrl+T: активный LLM :49079-49110; MT batch-ветка — активный MT :5602-5617.

Минимальный вариант (для Q-батча): в диалог — `QComboBox` имён профилей с дефолтом «активный»;
в spawn воркера передать `self._custom_profile_request_kwargs(выбранный)` вместо активного
(:39266, :50864) + endpoint/key выбранного профиля. Изменения: ~+15-25 строк в каждый диалог,
1-3 строки в двух spawn-точках; воркеры не трогаем (параметры уже kwargs-ные). Для MT-batch —
аналогично активный MT (:50851-50864 MT-ветка).

---

## H. Отмена запроса при закрытии QuickTrans (side-пожелание)

- Панель `closeEvent` (quicktrans.py:1628-1635) и popup `closeEvent` (:1293-1306): только
  `QThread.quit()+wait(1000)`; начатый запрос продолжается; результат приходит в панель/-popup
  после закрытия (в popup строки уже скрыты; в панели следующая сегмент-смена всё равно дропнет
  по `_fetch_token`).
- Кооперативный вариант: флаг отмены (например `requestInterruption()` / self._closed) — проверка
  после `fetch_single` / перед emit; результат отбрасывается, сетевой вызов доживает до ответа
  (600 с timeout). Дёшево, без изменения llm_clients.
- Настоящий abort: синхронный `chat.completions.create` (llm_clients.py:807-818) прервать нельзя без
  смены транспортного слоя — вне рамок Q-серии.
- Рекомендация: кооперативный дроп при closeEvent (Q.6).

---

## I. Предлагаемый план Q-серии (порядок, зависимости)

| # | Содержание | Зависимости | Оценка |
|---|---|---|---|
| Q.1 | Поля max_tokens/timeout_min/extra_body (+vision по решению) в MT-профили (вариант 1) | нет | ~70 строк, риск низкий |
| Q.2 | Link-only gates в QuickTrans (панель+popup) | нет | ~25 строк |
| Q.3 | MT-блок панели: ряды по профилям + кнопка Fetch вместо авто (пожелание 1); popup — авто оставить? | Q.3→Q.4 UI | ~60 строк, тред-риск |
| Q.4 | Редактируемое поле результата + кнопка Paste (панель+popup); удаление вставки по клику (пожелание 4) | Q.1, Q.3 | ~90 строк, NBSP-риск (обязательна blockSignals-обёртка) |
| Q.5 | QComboBox профиля в Proofreading и Batch | нет | ~40 строк |
| Q.6 | Кооперативная отмена при закрытии QuickTrans | нет | ~15 строк |
| Q.7 | blockSignals-обёртки в 14 insert-сайтах (финиш M2.3) | Q.4 (пересечение сайтов 35785/7519/7523) | ~30 строк |

- Проб-план: fake-endpoint (локальный HTTP на 127.0.0.1: ответы/усечение/таймаут/битый JSON) —
  offscreen-пробы Q.1/Q.3/Q.6; NBSP-проба (образец M2.3 S0) — Q.4/Q.7; link-only-проба — Q.2
  (строки `![Image](y.png)`, `![Image](y.png).`, смешанные).
- Риски: (а) lifecycle QThread при Q.3/Q.6 (убрать висячие QThread — см. M2-закрытие popup
  wait(1000)); (б) NBSP (Q.4/Q.7) — обязателен wrapper на всех insert-путях; (в) обратная
  совместимость settings.json (Q.1 — дефолты при отсутствии полей).

## Журнал вопросов к координатору (с моими дефолтами)

| # | Вопрос | Мой дефолт |
|---|---|---|
| Q1 | Вариант 1 для полей MT (без миграции)? | Да |
| Q2 | Vision-флаг в MT-профиле: нужен? | Нет (MT = текст) |
| Q3 | Панель: полностью заменить авто-MT на Fetch-ряды? | Да (пожелание 1) |
| Q4 | Popup: авто-fetch при показе остаётся? | Да (быстрый Ctrl+Alt+Q) |
| Q5 | Редактируемое поле: per-row или одно общее? | Per-row |
| Q6 | Горячие клавиши Ctrl+1..9 / Enter / цифры — оставить после снятия вставки кликом? | Оставить |
| Q7 | Link-only в QuickTrans: верbatim в строку без сети, draft только при вставке? | Да (как M1) |
| Q8 | QComboBox профиля — для Proofreading+Batch (LLM) и для MT-batch? | Proofreading+Batch LLM — да; MT-batch — отдельным рядом, по желанию |
| Q9 | Отмена при закрытии — кооперативный дроп (без true abort)? | Да |
| Q10 | 14 NBSP-сайтов — входить в Q-серию (Q.7) или отдельный батч? | Входить |

Стоп до вердикта координатора.
