# G2 — Аудит LLM-клиента для локальных и reasoning-моделей (READ-ONLY)

Дата: 2026-10-04. Исполнитель: ZCode.
Репозиторий: `E:\Dev\SupervertalerPortable`, HEAD `dc8d80c7` (= origin/main).
Код приложения НЕ менялся. Создан только этот отчёт и временные скрипты в
`D:\Temp\SupervertalerPortable\refactoring\g2\` (вне репо).

---

## 0. Базовое состояние (Этап 0)

| Проверка | Результат |
|---|---|
| `git fetch origin` + `git status` | рабочее дерево чистое; только незатреканные `.zcode/` |
| Дрейф: `git merge-base --is-ancestor 7d9cf7dc HEAD` | предок — дрейфа нет |
| HEAD / origin/main | `dc8d80c7` / `dc8d80c7` |
| `Supervertaler.py` | 67641 строк |
| py_compile (формула 8.2: `modules/**` + `Supervertaler.py`) | **137/137 OK** (полный прогон со `tools/batch_validation` — 145/145) |

Приложение не запускалось; user_data не читался и не менялся; внешних сетевых запросов не было.
Headless-проверки парсеров: `D:\Temp\SupervertalerPortable\refactoring\g2\test_parsers.py`
(импортирует реальный `modules.llm_clients.LLMClient`, работает только с методами очистки/парсинга,
без сети; вывод — `test_parsers_out.txt`).

---

## 1. Карта путей к LLM (Этап 1)

Все пути сходятся в один класс `LLMClient` (`modules/llm_clients.py`), метод
`translate()` → `translate_with_usage()` → провайдер-метод. Ключевой факт:
**специализированной ветки для `custom_openai` нет** — локальный сервер
(LM Studio / llama-server) идёт через `_call_openai_with_usage()`, написанный
под облачный OpenAI: короткий таймаут, отбор reasoning-модели по ИМЕНИ,
без стриминга, без `reasoning_content`, без `finish_reason`, без ретраев.

### Общая таблица

| Путь | Точка входа | Клиент | Запрос | Таймаут | Разбор ответа | Вывод ошибки |
|---|---|---|---|---|---|---|
| **A. Перевод сегмента (Editor, кнопка/горячая клавиша)** | `SupervertalerQt.translate_current_segment` (Supervertaler.py:57814), вызов `client.translate` :58190 | `LLMClient` через `create_llm_client` (:56588) для ollama-ветки — свой `LLMClient` | single-промпт из библиотеки (или вшитый для ollama), `custom_prompt`, system нет; синхронно в GUI-потоке (progress dialog + processEvents) | **120 с** (custom_openai/openai; 600 с только если имя модели содержит `gpt-5`/`o1`/`o3` — `llm_clients.py:908-910`) | `choices[0].message.content`; затем `_clean_translation_response` (see §2) | `QMessageBox.critical("Translation Error")` — ВИДИМАЯ (:58255) |
| **B. Batch / PreTranslation** | `PreTranslationWorker._translate_batch_with_llm` (:5715), `run()` :5494-5538; QThread | свой `LLMClient` (:5819) | system = инструкция из библиотеки (base_prompt), user = нумерованный список `«{seg.id}. {source}»`; `enable_prompt_caching=True`; **`skip_cleaning` не передаётся → ответ чистится `_clean_translation_response`** | **120 с** на batch (custom_openai); размер batch из настроек `batch_size` (20) | парс `^(\d+)\.\s*(.*)` построчно, маппинг по **`seg.id`**; необознанные строки — продолжение предыдущей | `translation_error.emit(str(e))` + `✗ BATCH ERROR` построчно; **если ответ пришёл, но не распарсился — никаких ошибок: «⊘ No translation» на каждый сегмент** |
| **C. Match Panel — колонка «AI / LLM»** | `QuickTransPanel` (Match Panel, :40808) и под-грида (:27374), оба — `QuickTransProviderMixin._call_llm_translation` (modules/quicktrans.py:434); LLM — кнопки по требованию (`_do_fetch` :1476: «LLMs: on-demand buttons only») | `create_llm_client` (:458) | жёсткий вшитый промпт «Translate … from {X} to {Y}. Output ONLY the translation…» + system «You are a translation engine…»; языки — канонические имена (`_canonical_lang_name`, 'nl'→'Dutch') | **120 с** | strip кавычек + префиксы `Translation:`/`Result:`/`Output:`; `<think>` НЕ срезается | строка `[Error: {e}]` показывается как «перевод» в панели |
| **D. Chat (ChatBackend) и AI Assistant** | `modules/chat_backend.py:181 send_ai_request` → `translate_with_usage(custom_prompt=prompt, system_prompt=…, skip_cleaning=is_analysis)`; клиент :151 через `create_llm_client` | общий | system + user, `max_tokens=16384`; **`skip_cleaning=is_analysis` — обычные сообщения чата проходят через `_clean_translation_response`!** | **120 с** | без доп. обработки; fence-stripping есть только в AI-действиях (`modules/ai_actions.py:83-91`) | `raise` → UI чата показывает ошибку; лог `[ChatBackend] Error` |
| **E. QuickTrans (MT-попап, внешние хоткеи)** | `MTQuickPopup` (quicktrans.py:546) — тот же `QuickTransProviderMixin` | общий | как C; языки: `parent_app.source_language/target_language` или проект, канонизируются | **120 с** | как C | как C |
| **F. Прочие** | • Custom MT профиль: `_call_custom_mt*` (Supervertaler.py:~56480, raw_mode — исходник в user, направление в system) • Прогрессивные совпадения `_add_llm_matches_progressive` (:61468) / `_add_mt_and_llm_matches` (:61548) • `_fetch_llm_translation_async` (:59919, QTimer.singleShot — НЕ поток, блокирует GUI, исключение «Silently fail») • QuickLauncher (:58774) • Proofread-воркер (`modules/workers/proofread.py:96`, формат `[SEGMENT NNNN]`) • Batch-offload CLI (`modules/batch_offload.py`, зеркалит промпт/парс пути B) | общий | разные; в прогрессивных совпадениях дефолты **перепутаны**: `source_lang_code or 'nl'`, `target_lang_code or 'en'` (:61477-61478, :61519-61520, :61634-61635, :61674-61675) | 120 с (custom_openai); proofread — тот же клиент | разные; batch_offload повторяет парс B | в основном `self.log(...)` — тихо |

### Значения по умолчанию для custom_openai (всё — `llm_clients.py`)

* **Таймаут**: `timeout_seconds = 600.0 if is_reasoning_model else 120.0`, где
  `is_reasoning_model = any(x in model_lower for x in ["gpt-5", "o1", "o3"])` (:908-910).
  «muse-glimmer-30b», «qwen3…», «deepseek-r1…» и т.п. → **120 секунд на весь запрос**.
  Это полный таймаут httpx (connect+read+total), не idle. Настройка
  `ollama_timeout_minutes` (Settings → AI Settings, :21448-21462) действует **только
  на провайдера ollama** (`set_ollama_timeout` читается лишь в `_call_ollama`);
  для custom_openai настройки таймаута нет вообще.
* **Стриминг**: только у ollama (`stream=True` при prompt>3000 или tokens>4096, :1627).
  OpenAI-совместимый путь всегда ждёт весь ответ (`stream` не передаётся).
* **max_tokens**: `client.max_tokens` = 16384 по умолчанию (`LLMConfig.max_tokens`,
  :190); reasoning-ветка по имени ставит `max_completion_tokens=32768`, обычная —
  `max_tokens=16384` (:925-930, :961-966). Отмены запроса на уровне клиента нет
  (только межбатчевый флаг `_cancelled` воркера).
* **Retries**: отсутствуют (grep `retry` в llm_clients.py = 0).
* **Inference-параметры**: `temperature=0.3` жёстко (для не-reasoning-по-имени; :966);
  `top_p`/`top_k`/`min_p`/`repeat_penalty`/`stop` НЕ передаются (у ollama `top_p=0.9`,
  `repeat_penalty=1.1` вшиты, :1635-1640). **Поля extra body нет** — передать
  `chat_template_kwargs`, `reasoning_effort`, грамматику/логиты llama-server некуда.
  Load-параметры сервера (n_ctx, GPU layers и т.п.) через клиент передать нельзя в
  принципе — только при старте сервера.
* **system/user**: передаются как есть; при `enable_prompt_caching` для
  OpenRouter→Anthropic system уходит content-массивом с `cache_control`.

---

## 2. Разбор ответа (Этап 2)

### 2.1 Что читается

* `choices[0].message.content` — единственное поле, которое читается
  (`llm_clients.py:970-973`). **`reasoning_content` не читается нигде в репо**
  (grep `reasoning_content` = 0). Если reasoning-модель (LM Studio/llama-server
  с reasoning-парсером) кладёт рассуждения в `reasoning_content`, а content пуст
  или обрезан — клиент получает пустоту.
* **`finish_reason` не проверяется** в openai-совместимом пути (grep: только Gemini
  пути читают `finish_reason`). Обрыв по `finish_reason=length` (весь бюджет
  съели размышления) ничем не отличается от успеха: если в content есть хоть что-то —
  это уходит в перевод.
* Пустой content → `ValueError("OpenAI returned empty response…")` (:970-975) —
  исключение. Что видит пользователь, зависит от пути: A — QMessageBox; B —
  `translation_error`/`✗ BATCH ERROR`; C — `[Error: …]`; `_fetch_llm_translation_async` —
  **ничего (тихий log)**; D — сообщение в чате.

### 2.2 `<think>…</think>`

**Не обрабатывается нигде** (grep `<think` по *.py = 0 совпадений в коде; только
совпадения в этом отчёте). Единый санитайзер отсутствует; каждый путь вычищает
своё:

* путь A/B: `_clean_translation_response` (`llm_clients.py:590-770`) — убирает
  «остатки промпта», но не теги размышлений;
* путь C: только strip кавычек и префиксов (`quicktrans.py:493-500`);
* AI Actions: fence-stripping тройкой regex (`ai_actions.py:83-91`) — только ` ``` `,
  не `<think>`;
* незакрытый `<think>` (обрыв по max_tokens): ни один путь не распознаёт;
* несколько блоков, регистр (`<Think>`, `<thinking>`): не учитываются нигде.

### 2.3 Batch-путь: почему ответ «теряется молча»

Ожидаемый формат — «`{seg.id}. перевод`», парс `^(\d+)\.\s*(.*)` c маппингом
по `seg.id` (`Supervertaler.py:5844-5874`; зеркало в `batch_offload.parse_batch_response`).
Слепые зоны, каждая из которых даёт «⊘ No translation» на все/часть сегментов
**без единой ошибки в UI** (воркер честно рисует «No translation» как штатный статус,
`Supervertaler.py:5518-5522`):

1. **Модель перенумеровала ответ с 1** (а сегменты пакета имеют id не 1..N —
   выбранный диапазон, retry-проход, фильтр): `translation_map.get(seg.id)` → None
   для всех. Headless-подтверждение: сценарий «id 40..42, ответ 1..3» →
   `[None, None, None]`.
2. **Незакрытый `<think>`** (обрыв по max_tokens): нумерованных строк нет → все None.
   Если нумерация была ВНУТРИ размышлений (в2) — рассуждения молча становятся
   «переводами».
3. **Деструктивная очистка**: перед парсом результат проходит
   `_clean_translation_response` (`translate_with_usage` :874-875, `skip_cleaning`
   путём B не передаётся). Маркеры-разделители включают `"Translation:"`,
   `"**TRANSLATION**"` (:609-620), а список паттернов — **обычные нидерландские
   слова** `"vertaler"`, `"handleidingen"`, `"tekstsegmenten"`, `"naleving"`,
   `"regelgeving"`, `"medische apparaten"`, `"CAT tool tags"` (:647-689).
   Headless-подтверждение: batch-ответ, где строка «2. De **vertaler** controleert…»
   (>300 знаков, ветка :696-729) **молча выбрасывается** — сегмент 2 остаётся пустым,
   хотя модель его перевела. Для EN→NL это не экзотика, а штатная лексика.
4. Нумерация в другом формате (`1)`, `**1.**`, `1 -`): regex не матчит → None.
5. Проблема не в исключении: само по себе исключение пути B теперь пробрасывается
   и показывается (:5524-5538); теряется именно **успешный HTTP-ответ с непарсимым
   содержимым**.

### 2.4 Таблица headless-проверки (сценарии а-е из постановки)

Проверено реальным `LLMClient` без сети (`test_parsers.py`; pipeline пути B =
`_clean_translation_response` → парс; id сегментов 1..3):

| Сценарий (синтетический ответ) | Путь B (batch): результат парса | Путь A (single): что попадёт в target | Путь C (Match Panel) |
|---|---|---|---|
| (а) чистый ответ `1./2./3.` | ✅ все 3 перевода | ✅ чисто | ✅ чисто |
| (б) `<think>…</think>` + ответ | ✅ переводы (think игнорируется парсером, т.к. без номера) | ❌ **think остаётся в тексте**: `'<think>Hmm…</think>\nDe systeem…'` целиком в ячейку | ❌ think остаётся |
| (б2) `<think>` с нумерованным списком внутри | ✅ переводы верные (номера think перезаписываются ответом), но рискованно | ❌ think в ячейке | ❌ think остаётся |
| (в) незакрытый `<think>` без ответа (обрыв) | ❌ **все None, тихо** | ❌ мусор-рассуждение в ячейке | ❌ рассуждение как «перевод» |
| (в2) незакрытый `<think>` с нумерацией внутри | ❌ **рассуждения приняты за переводы** | ❌ мусор в ячейке | ❌ мусор |
| (г) пустой content + reasoning_content + finish_reason=length | клиент падает до парса: `ValueError('OpenAI returned empty response')` — reasoning_content не читается (`grep reasoning_content` = 0) | QMessageBox «Translation Error» | `[Error: …]` в панели; `_fetch_llm_translation_async` — тихо |
| (д) markdown-fence ` ``` ` | ⚠️ переводы получены, но к последнему **приклеился `\n``` `** (fence не срезается в этом пути) | ❌ fence остаётся в ячейке | ❌ fence остаётся (префиксы `Translation:`/кавычки — срезаются ✅) |
| (е) рассуждения без тега + ответ («Sure, here are…») | ✅ переводы | ❌ преамбула в ячейке | ❌ преамбула |
| (ж) доп.: модель перенумеровала 1..3 при id 40..42 | ❌ **все None, тихо** | — | — |
| (з) доп.: строка пакета содержит «vertaler» (>300 зн. общий текст) | ❌ **строка молча выброшена очистителем** → сегмент пуст | ⚠️ то же для многострочного сегмента | ⚠️ то же |

«Fence stripping» из лога ChatBackend/T1.2 — это fence-regex в `modules/ai_actions.py:83-91`
(только для AI-действий чата); переводческие пути A/B/C его не применяют.

---

## 3. Язык перевода и сборка промпта (Этап 3)

### 3.1 Источники исходного/целевого языка

| Путь | SOURCE | TARGET | Где в промпте указан язык вывода |
|---|---|---|---|
| A `translate_current_segment` | `current_project.source_lang` | `current_project.target_lang` | плейсхолдеры `{{SOURCE_LANGUAGE}}/{{TARGET_LANGUAGE}}` в системном шаблоне + текст библиотечного промпта |
| B batch | проект | проект | base_prompt (из библиотеки, = system) + нумерованный список; при отсутствии менеджера — вшитая строка «Translate the following text segments from {X} to {Y}» (:5778) |
| C Match Panel / E QuickTrans | проект → `_canonical_lang_name` → **полное имя** («Dutch») | проект → имя | вшитый английский промпт «from {X} to {Y}» + system «You are a translation engine» |
| Custom MT (raw_mode) | профиль/вызов | вызов | **только system**: «Translate from {X} to {Y}» (:56510-56513) |
| Прогрессивные совпадения (F) | `source_lang_code or 'nl'` ← **дефолт перепутан** | `target_lang_code or 'en'` ← **дефолт перепутан** | `translate()` дефолт-промпт «Translate … from {X} to {Y}» (`llm_clients.py:854`) |
| D Chat | «en» (dummy) | «en» (dummy) | язык определяется текстом промпта/разговора |

Промпт-менеджер: `build_final_prompt` (`modules/unified_prompt_manager_qt.py:4076-4150`)
подставляет в системный шаблон **те строки, что передал вызывающий** — в путях A/B это
**коды** ('en'/'nl') из проекта, т.е. модель видит «expert en to nl translator».
Дефолтный системный шаблон (:3999+) на английском, с нидерландскими примерами тегов;
инструкции языка вывода как таковой нет — есть только «expert X to Y translator» и
правила пунктуации. Поверх — **primary prompt из библиотеки пользователя
вставляется дословно** («# CUSTOM PROMPT»), его язык и содержание приложение не
контролирует.

### 3.2 Инструкции, способные дать вывод «не на том» языке / на двух языках

* Библиотечный промпт пользователя (primary + attached) вставляется без изменений:
  если он написан по-русски или требует двуязычный вывод — модель послушает его, а
  не системный шаблон. Приложение не проверяет конфликт «язык проекта ≠ язык/текст промпта».
* TM/глоссарий: термины вставляются как «source → target» парами; если в терминологии
  целевые термины на другом языке — это дополнительный языковой сигнал (без запрета).
* Вшитые промпты путей C/E/Custom-MT — английские, с **именами** языков; путь A/B —
  с **кодами**. Для локальной модели «nl» — слабый сигнал; comply зависит от модели.
* Surrounding segments (A): контекст содержит уже существующие переводы целиком —
  если они на другом языке, модель склонна продолжать в этом языке.
* system vs user: в путях A инструкции библиотеки уходят **в user-сообщение**, в пути B —
  **в system** (base_prompt). Одна и та же модель может слушаться их по-разному —
  правдоподобное объяснение расхождения «два режима — два языка».

### 3.3 Preview Prompts

Кнопка «🧪 Preview Prompts» (:27233 → `_preview_combined_prompt_from_grid` :45915)
показывает **только** `build_final_prompt(single, проект-языки)` для текущего сегмента.
НЕ покрыты и потому не соответствуют реально отправляемому: batch-запрос пути B
(system=base_prompt + нумерованный user), промпты C/E (QuickTrans), Custom MT raw_mode,
Ollama-промпт пути A, QuickLauncher, Proofread, Chat. Т.е. по превью нельзя
воспроизвести промпт большинства путей.

### 3.4 Вывод по симптому 4 (Target=NL, Match Panel=RU)

Наиболее вероятные механизмы (по силе доказательности):

1. **Утечка reasoning**: локальная reasoning-модель кладёт рассуждения (часто на
   русском) в content до/вместо перевода; единственный санитайзер `think`-тегов не
   существует, поэтому в панели «AI / LLM» показывается русский текст размышлений
   (подтверждено сценарием (в): рассуждение целиком попадает в результат). Это же
   объясняет T1.2 («Wait, let me check the termbase…» в чате) и часть симптома 2.
2. **Разные промпты и роли**: Match Panel шлёт короткий вшитый промпт в user
   (system «translation engine»), Editor — библиотечный промпт (русский текст
   пользователя + системный шаблон с «en to nl»). Слабая локальная модель
   отвечает на языке доминирующего текста: где в промпте много русского
   (библиотека пользователя) — может уехать в RU, где короткий английский —
   следовать инструкции.
3. **Код vs имя**: пути A/B дают «en → nl», путь C — «English → Dutch»; для 30B
   локальной модели разница ощутима.
4. Перепутанные дефолты `or 'nl'/'en'` в прогрессивных совпадениях — отдельный
   баг того же класса (сейчас срабатывает только при пустых кодах).

**Итог по симптому 4 (эксперимент Дмитрия):** эксперимент подтвердил гипотезу №2
(якорный язык примеров в системном шаблоне), а не TM/ручной ввод. Дмитрий
добавил, а затем удалил нидерландский пример из системного промпта —
indexteam/index-nailong-9b вернулся к русскому в гриде (qwen3.8-27b на presence
примера не отреагировал). Значит, нидерландский текст в Target был ответом
модели, копирующей язык примера из контекста. Механизм: путь A (Editor) несёт
системный шаблон с нидерландскими примерами (см. 3.5.2), путь C (Match Panel
AI/LLM) — короткий вшитый промпт без них; отсюда «два режима одного провайдера —
два языка». Предложение 3.5.5 п.1 (язык-нейтральные примеры) подтверждено
экспериментом.

### 3.5 Состав системного промпта и пример на нидерландском

#### 3.5.1 Где живёт системный промпт и как собирается

* **Встроенный дефолт**: `UnifiedPromptManagerQt._get_default_system_template`
  (`modules/unified_prompt_manager_qt.py:3991-4041`) — один статичный шаблон
  для всех режимов (single/batch_docx/batch_bilingual). Измерено: 2 969 символов
  в сыром виде, ≈3 026 с разделителем «**YOUR TRANSLATION (provide ONLY the
  translated text, no numbering or labels):**».
* **Переопределение пользователем**: `self.system_templates` (:1063) заполняется
  в `_load_system_templates` (:3894-3938) по приоритету: (1) файл
  `system_prompts_layer1.json` в каталоге библиотеки промптов (user_data —
  НЕ читался в рамках G2), (2) старые `1_System_Prompts/*.md`, (3) дефолт.
  Т.е. фактический текст у Дмитрия может быть его правкой, а не дефолтом.
* **Сборка** (`build_final_prompt`, :4076-4150): system_template (с подстановкой
  `{{SOURCE_LANGUAGE}}`/`{{TARGET_LANGUAGE}}`/`{{SOURCE_TEXT}}`/`{{TARGET_TEXT}}`)
  + `# CUSTOM PROMPT` (active_primary_prompt дословно) + `# ADDITIONAL
  INSTRUCTIONS` (attached) + `# TERMBASE` + `# FUZZY TM MATCH` + разделитель.
  Preview Prompts вызывает тот же `build_final_prompt` (заголовок диалога
  «System Prompt + Custom Prompts + segment text» — Supervertaler.py:46036).
* **Сверка с 3 844 символами Дмитрия**: дефолт даёт ≈3 026; остаток ≈820 —
  custom prompt из библиотеки и/или текст сегмента/глоссарий (у превью горит
  «✓ Custom prompt attached» при непустом primary prompt).

#### 3.5.2 Все места с зашитым нидерландским (или иным не-целевым) примером

Все примеры **статичны** — плейсхолдеров внутри примеров нет, от целевого языка
не зависят:

| Место | Содержимое |
|---|---|
| `unified_prompt_manager_qt.py:4013` (блок INLINE FORMATTING TAG PRESERVATION) | `"Click the <b>Save</b> button" → "Klik op de knop <b>Opslaan</b>"` — **нужный Дмитрию пример** |
| `unified_prompt_manager_qt.py:4028-4031` (блок CAT TOOL TAG PRESERVATION) | 4 примера с нидерландским: `'[1}De uitvoer{2]' → '[1}The exports{2]'`, `'<410>De uitvoer van machines</410>' → '…Exports of machinery…'`, `'He debuted against |Juventus FC|…' → 'Hij debuteerde tegen |Juventus FC| in 2001'`, multiple |
| `unified_prompt_manager_qt.py:4033-4035` (LANGUAGE-SPECIFIC NUMBER FORMATTING) | «If the target language is **Dutch**, **French**, **German**…» — легитимное правило, но с нидерландским уклоном |
| `unified_prompt_manager_qt.py:745-800` (`DOMAIN_TEMPLATES`, 'patent'/'legal') | статичные NL→EN допущения генератора промптов AI Assistant: маппинги `omvattende>comprising`, `uitvoeringsvorm>embodiment` и др., «If the Dutch text is long, repetitive…», «Meester + surname» — используются через `_get_domain_template` (:5299-5301), в переводный системный промпт не попадают |

Совпадения «uitvoer» в Supervertaler.py (:30194-30345) — комментарии кода о
нормализации синонимов термбазы, не промпты. Dutch-паттерны в
`llm_clients.py:647-689` — это `_clean_translation_response` (см. §2.3).

#### 3.5.3 Условия включения тег-блоков

* **В системном шаблоне** блоки «INLINE FORMATTING TAG PRESERVATION» (:4009-4015)
  и «CAT TOOL TAG PRESERVATION» (:4017-4032) — статичный текст: включаются
  **всегда**, когда путь использует `build_final_prompt` (A-cloud, B, Preview),
  независимо от наличия тегов в сегменте.
* **Условные тег-правила вне шаблона** (единственные «умные»): batch user-промпт —
  правило нумерованных `<N>`-тегов только при `_has_inline_tags`
  (Supervertaler.py:5793-5804); A-ollama-промпт — только при
  `re.search(r'</?\d+/?>', segment.source)` (:~58048); отдельные шаблоны
  FuzzyFixer/AutoTagger.
* **Список форматов** в шаблоне: `<b>/<i>/<u>`; memoQ `[1}…{2]`; Trados Studio
  `<410>…</410>` (XML); CafeTran `|…|`; вне шаблона — нумерованные `<1>…</1>`,
  `<2/>`.

#### 3.5.4 Различия промптов между путями

| Путь | Системный промпт | Состав и порядок | Тег-блоки | Порядок размера |
|---|---|---|---|---|
| A (Editor, cloud) | **нет** (system=None) | весь `build_final_prompt` ≈3.0k+custom уходит в **user**-сообщение | оба блока всегда | тяжёлый |
| A (Editor, ollama-ветка) | нет | свой вшитый промпт (роль + контекст окружения + сегмент) | правило `<N>` условно, CAT-блока нет | средний |
| B (batch) | base_prompt = `build_final_prompt(...)` → в system; **сплит по `**SOURCE TEXT:**` не матчится с дефолтным шаблоном** (там «{{SOURCE_LANGUAGE}} text:»), поэтому base_prompt = весь промпт, включая текст первого сегмента и разделитель «**YOUR TRANSLATION…**» | system (шаблон+custom+хвост) + user (нумерованный список) | оба блока всегда + условное правило `<N>` в user | самый тяжёлый, с чужеродным хвостом |
| C (Match Panel AI/LLM) | «You are a translation engine…» (quicktrans.py:477-482) | короткий вшитый user-промпт ≈250 симв. | нет | лёгкий |
| D (Chat) | «You are an AI assistant for Supervertaler…» (chat_view_widget.py:809) + опц. Trados-контекст (:817) | question as user | нет | лёгкий |

Вывод: системный промпт **не одинаковый** — A/B несут ≈3k шаблон с нидерландскими
примерами (B — ещё и с первым сегментом в system), C/D — лёгкие. Одна и та же
модель получает в разных режимах разные инструкции и разные «якорные» языки —
это второй (после `target_lang='ru'`) вклад в симптом 4 и в разное поведение по
режимам.

#### 3.5.5 Предложения (описать, не применять)

1. **Язык-нейтральные примеры**: в дефолтном шаблоне заменить нидерландские
   примеры на бессмысленно-языковые («target keeps `<b>` around the word
   corresponding to "Save"») или подставлять пример целевого языка из словаря по
   `target_lang` (3–4 строки кода в `build_final_prompt`). Риск: низкий; эффект:
   убрать чужой языковой сигнал из каждого запроса.
2. **Условный тег-блок**: `build_final_prompt` уже получает `source_text` —
   включать INLINE/CAT-блоки только при `re.search(r'</?[a-zA-Z0-9]+/?>', …)` /
   memoQ-CafeTran-маркерах (по образцу batch-правила :5793). Экономия ≈1 500
   символов на чистых сегментах, меньше расфокуса локальных моделей.
3. **Короткий шаблон для локальных моделей**: добавить в
   `system_prompts_layer1.json` ключ `single_compact` (≈300–500 симв.: роль,
   направление «Translate to {{TARGET_LANGUAGE}}», только релевантное тег-правило)
   и выбирать по провайдеру (`ollama`/`custom_openai` → compact) в месте вызова
   `build_final_prompt` или внутри `get_system_template` (параметр от
   вызывающего). Механизм загрузки/приоритетов в `_load_system_templates` уже
   позволяет добавить ключ без ломки пользовательских правок.
4. **Чистка CAT-упоминаний после 8.9**: после удаления memoQ/Trados/CafeTran
   импортёров (батч 8.9) блок CAT TOOL TAG PRESERVATION с их примерами —
   кандидат на сокращение/переписывание; до тех пор не трогать (примеры нужны
   действующим форматам). Dutch-примеры (п.1) можно чистить уже сейчас.

---

## 4. Предложение исправлений (описано, НЕ применено)

Приоритет по влиянию на симптомы Дмитрия. Изменения в `modules/llm_clients.py`
и `Supervertaler.py` затрагивают модули, побайтно равные апстриму; чтобы свести
расхождение к минимуму, санитайзер/парсер/таймауты предлагается делать **тонким
слоем в отдельном модуле** (например `modules/llm_compat.py`), который обёртывает
`LLMClient`, а не правит его.

| # | Правка | Где | Размер | Риск | Закрывает симптом |
|---|---|---|---|---|---|
| 1 | **Таймаут/стрим для custom_openai**: (а) поднять дефолт до ≥600 с; (б) настройка «LLM request timeout (min)» для custom_openai (по аналогии с `ollama_timeout_minutes`, модульный override `set_custom_openai_timeout`); (в) idle-timeout «нет токенов N секунд» через `stream=True` + чтение чанков (openai SDK `client.chat.completions.create(stream=True)`), отмена по флагу | `llm_clients.py` (или обёртка), `Supervertaler.py` Settings | ~60–120 строк | низкий/средний (стрим меняет форму ответа — аккуратно с usage) | 1 (недожидание ответа), частично 3 |
| 2 | **Единый санитайзер ответа** в одном месте (`translate_with_usage` перед возвратом, опция `skip_cleaning` уже есть): срезать `<think>…</think>` (несколько блоков, case-insensitive), **незакрытый** `<think>` → вернуть пусто/ошибку «обрыв по лимиту», читать `reasoning_content` если content пуст, срезать markdown-fence; `_clean_translation_response` применять ТОЛЬКО когда не было `custom_prompt`-перевода, и убрать из паттернов голые слова «vertaler»/«tekstsegmenten» и маркер `"Translation:"`, матчащий любой текст | `llm_clients.py` | ~80–150 строк | средний (меняет поведение всех провайдеров — нужна выборочная регрессия) | 2, 3 (молчаливая потеря от чистки), T1.2 |
| 3 | **Устойчивый batch-парс + видимая ошибка**: (а) маппинг «по порядку + по id» (если модель пронумеровала 1..N, а id другие — брать позиционно, сверяя количество); (б) допуск форматов `1)`/`**1.**`; (в) если распознано <50% сегментов при непустом ответе — `translation_error.emit('Response received but unparsed: first 200 chars …')` вместо тихих «No translation»; (г) то же зеркало в `batch_offload.parse_batch_response`; (д) исправить сборку base_prompt batch: split по '**SOURCE TEXT:**' не срабатывает на дефолтном шаблоне, поэтому в system попадают текст первого сегмента и хвост «YOUR TRANSLATION» — резать по реальному маркеру шаблона | `Supervertaler.py:5844-5879`, `modules/batch_offload.py` | ~60–80 строк | низкий | 3 |
| 4 | **Явный целевой язык**: (а) в `build_final_prompt` добавлять в конец строку `Output language: {target_lang_name}.` (имя, не код) — один слой, все пути A/B; (б) в Preview Prompts — предупреждение, если текст primary/attached промпта не содержит {{TARGET_LANGUAGE}}, но содержит язык-строку, отличную от проекта; (в) починить перепутанные дефолты `or 'nl'/'en'` в прогрессивных совпадениях; (г) расширить Preview Prompts режимом «показать промпт выбранного пути» (A/B/C/CustomMT) | `unified_prompt_manager_qt.py`, `Supervertaler.py` | ~40–80 строк (без (г)); (г) ещё ~60 | низкий | 4 |
| 5 | **Inference-параметры и extra body per provider**: поле профиля custom_openai «extra body (JSON)» → в `api_params` (позволит `chat_template_kwargs: {enable_thinking:false}`, `reasoning_effort` и т.п. для llama-server/LM Studio); опционально temperature/top_p из профиля. Load-параметры сервера — только при старте сервера (в клиент не передать) | `Supervertaler.py` (профиль+`create_llm_client`), `llm_clients.py` (1 параметр) | ~40–60 строк | низкий | 2 (альтернатива санитайзеру: отключить think на сервере), база виджета настроек LLM |
| 6 | **План тестов**: заглушка OpenAI-совместимого сервера на `http.server` (временный скрипт вне репо, `D:\Temp\...\g2\stub_server.py`): сценарии — задержка >таймаута (проверка таймаута/стрима), `<think>`/незакрытый think/`reasoning_content`/`finish_reason=length`, перенумерованный batch-ответ, ответ с «vertaler», fence; гонять через headless-вызовы `translate_with_usage` и `_translate_batch_with_llm`-парсер; плюс регресс `_clean_translation_response` на корпусе NL-переводов | инструменты вне репо | ~150–200 строк скрипта | — | проверка 1–4 |

Апстрим-равные файлы: `modules/llm_clients.py` (и `Supervertaler.py`) совпадают с
апстримом, поэтому правки 1/2/5 лучше всего вносить минимальными точечными диффами
или через отдельный модуль-обёртку (правки 2/3 — чисто локальные функции, их можно
держать полностью в локальном модуле).

---

## 5. Непокрытые проверки (обязательно)

1. **Живых запросов не было** (read-only): все выводы о таймаутах/параметрах — из
   кода, о парсинге — из headless-прогона на синтетике. Реальное поведение LM
   Studio с muse-glimmer-30b (заголовки, форма reasoning-блока, `reasoning_content`
   vs `<think>` в content) не наблюдалось.
2. Неизвестно, что именно лежит в активном primary prompt библиотеки пользователя
   (user_data не читался) — гипотезы симптома 4 №2 не проверены на его тексте.
3. Не проверено, выдаёт ли LM Studio для muse-glimmer-30b `finish_reason=length`
   и пустой content при обрыве (сценарий (г) — только по коду).
4. Путь Proofread и Batch-offload проверены только чтением кода (без headless-прогона
   их парсеров).
5. `_fetch_llm_translation_async` — QTimer-«асинхронность» блокирует GUI на время
   запроса; масштаб проблемы (насколько заметно) не измерялся.
6. Не установлено, каким путём Dmitry получал RU-перевод в Match Panel (какая модель
   и какой из провайдеров AI/LLM был нажат) — нужен живой эксперимент с логом.
7. Ollama-путь (`_call_ollama`) в headless-прогоне не участвовал (синтетика гонялась
   через общие методы очистки/парса).

## 6. Вопросы к Дмитрию

**Ответы Дмитрия (приняты к правкам, описанным в §4):**

1. Очистка (`_clean_translation_response`): нидерландские паттерны убрать
   полностью; маркер «Translation:» считать только как префикс строки; чат
   не чистить.
2. Стриминг — только ветка custom_openai.
3. Preview Prompts — два режима: Single и Batch; Batch показывает реальное
   разделение system/user.
4. Extra body JSON и базовые параметры — в профиле custom_openai.
5. Лог сырого ответа — опция «Log raw LLM responses (debug)», по умолчанию
   выключена.

1. Правка 2 предлагает убрать из `_clean_translation_response` голые Dutch-слова
   («vertaler» и др.) и маркер `"Translation:"`, применяемый к любому тексту. Это
   когда-то было защитой от «модель перевела сам промпт». Убирать полностью или
   только для случая `custom_prompt` (когда промпт наш, а не вшитый)?
2. Правка 1(в): переход на стриминг для custom_openai меняет и отменяемость, и
   idle-timeout, но трогает общий провайдер-метод. Делаю отдельную ветку в
   `_call_openai_with_usage` только для custom_openai, или для всех OpenAI-совместимых?
3. Правка 4(г) «Preview Prompts для выбранного пути»: нужен ли отдельный селектор
   пути в диалоге превью, или достаточно превью batch-промпта (пути B) как второго
   режима кнопки?
4. Правка 5: планируемый виджет настроек LLM — хранить extra body JSON в профиле
   custom_openai (settings.json), или завести отдельный раздел «Inference params»
   для всех провайдеров?
5. Для симптома 4 нужен один живой эксперимент после правок: включить в client
   лог сырого ответа (первые 500 символов) при запросе из Match Panel — добавить
   такой лог в правку 2 (постоянно, в app-лог) или сделать временной отладочной
   опцией?
