# ФИНАЛЬНЫЙ ОТЧЁТ BATCH G3.2 — УСТОЙЧИВОСТЬ LLM-КЛИЕНТА К REASONING-МОДЕЛЯМ (custom_openai)

Дата: 2026-10-21. Исполнитель: ZCode-агент. Координатор: Дмитрий.
Батч завершён: все вердикты координатора (ответы 1–7 на §11 вопросов, ответы Q8/Q9,
ответ Q10) исполнены. **Пуш НЕ выполнялся** (по правилу батча); коммиты локальные.

Это — единый итоговый файл батча. Хронологический отчёт с детализацией по sub-batch
(`BATCH_G3_2_REASONING_RESPONSES_REPORT.md`, §1–§13) остаётся в репозитории как
история; здесь — финальное состояние: код, карта вызывающих, матрица проб, полный
оффскрин-набор, защиты, журнал вопросов.

## §0. Итог

- **Цель батча:** клиент `custom_openai` устойчив к reasoning-моделям: разбор
  reasoning/think-блоков, типизированные исключения (truncation / empty / timeout),
  пользовательские поля профиля (`max_tokens`, `timeout_min`, `extra_body`),
  строгий/снисходительный гейт усечения, понятное отображение ошибок в вызывающих путях.
- **Sub-batch’и:** G3.2a (парсер + иерархия исключений + log-hook),
  G3.2b (поля профиля: модель/UI/валидация/применение), G3.2c (пробный харнесс
  fake-endpoint + полный набор + артефакты), G3.2d (гейт strict/lenient +
  `partial_text` + dangling/unclosed — вердикт, ответы 1–7), G3.2e (мягкий чат при
  усечении — вердикт Q8/Q9), G3.2f/Q10 (Image Extractor AI-подпись — ответ
  «вариант (а)», ноль правок кода).
- **Итоговые цифры:** 5 коммитов кода/артефактов + финальный docs-коммит; пробная
  матрица **16/16 PASS**; юниты **11/11** (парсер профиля) и **11/11**
  (`_parse_completion_response`); полный 16-этапный оффскрин-набор **0 FAIL**
  (regress-хэши байт-идентичны базлайну); статика идентична базлайну; все 10 вопросов
  координатора закрыты.

## §1. Коммиты

| Коммит | Sub-batch | Содержание |
|---|---|---|
| `951b54cd` | G3.2a | `llm_clients.py`: типизированные исключения, парсинг reasoning/think, log-hook (`set_llm_log_callback`, wiring в монолите); починка прокси-импорта (httpx2) |
| `35873b2d` | G3.2b | Поля профиля `max_tokens` / `timeout_min` / `extra_body`: модель (`parse_profile_request_fields`), UI диалога профилей, валидация при сохранении, применение во всех 7+ точках создания клиента |
| `a17fcb63` | G3.2c | Probe-скрипт fake-endpoint, `batch-g32_run_full.sh`, 31 артефакт в audite (код продукта не тронут) |
| `10f621fd` | G3.2d | Гейт строгости существующим флагом `skip_cleaning` → `lenient_on_truncation`; атрибут `partial_text`; `_CLOSE_REASONING_RE` (dangling closer); unclosed opener → raise во всех путях |
| `d59bc61e` | G3.2e | Чат ловит `LLMTruncatedError` в вызывающем коде: `partial_text` как обычный ответ ассистента + пометка «⚠ Answer truncated by Max tokens» + warning в лог; 3 хендлера в 2 модулях; карта вызывающих; матрица 16 |
| (этот) | G3.2f | Q10 (вариант (а), ноль правок кода — лог проверен), таблица вызывающих §13.3 хрон.отчёта, настоящий финальный отчёт, PROJECT_STATUS |

## §2. Финальный пакет файлов сборки (репозиторий; тестовая сборка не обновлялась — решение Дмитрия)

| Файл | До батча | Финал | Δ | sha256 (префикс) | EOL |
|---|---|---|---|---|---|
| `Supervertaler.py` | 55 153 | **55 338** | +185 (только G3.2a/b) | `7c499f0387850b34` | CRLF, bare-LF 0 |
| `modules/llm_clients.py` | 579 | **851** | +272 | `e8d5c0bb10bd8c0a` | CRLF, bare-LF 0 |
| `modules/chat_view_widget.py` | 934 | **953** | +19 | `38148b43086396f8` | LF чистый |
| `modules/unified_prompt_manager_qt.py` | 6 831 | **6 879** | +48 | `6bd7beab2eaf4387` | CRLF, lone-LF 0 |
| `modules/workers/proofread.py` | 151 | **154** | +3 | `e3cb001d024bbfc7` | LF (как базово) |
| `modules/chat_backend.py` | 284 | 284 | 0 (не тронут) | — | — |

Файлы сверены sha256 с состоянием, на котором прогонены матрица 16/16 и полный
оффскрин-набор (G3.2e): **совпадают**; G3.2f (Q10) не изменил ни одного файла →
приведенные ниже результаты проб соответствуют финальному состоянию кода.

## §3. Правила разбора ответа (`_parse_completion_response`, финал)

Иерархия: `LLMResponseError(ValueError)` (атрибуты `finish_reason`,
`has_reasoning`, `reasoning_tokens`, `partial_text`); подклассы
`LLMTruncatedError`, `LLMEmptyResponseError`, `LLMTimeoutError`. Наследование от
`ValueError` сохраняет совместимость со всеми существующими `except Exception`.

1. `choices` пустой → `LLMEmptyResponseError`.
2. Закрытые `<think>…</think>` / `<thinking>…</thinking>` срезаются
   (несколько блоков, регистронезависимо, многострочно); «висячий» закрывающий без
   открывающего (артефакт шаблонов) → берётся текст **после последнего** closer.
   `reasoning_content` как перевод **никогда не используется**.
3. **Незакрытый** открывающий think-тег в content → `LLMTruncatedError`
   **во всех путях** (строгость не применяется: ничего не возвращается,
   `partial_text=None`); в тексте — подсказки (поднять Max tokens /
   `extra_body {"chat_template_kwargs": {"enable_thinking": false}}`).
4. content пуст + `finish='length'` → `LLMTruncatedError` (число
   `reasoning_tokens` в атрибуте и тексте).
5. content пуст + `finish != 'length'` → `LLMEmptyResponseError`
   (`finish_reason` + признак `reasoning_content`).
6. content непустой + `finish='length'`: **strict** → `LLMTruncatedError`
   «cut off at max_tokens mid-answer», `partial_text` = восстановленный текст
   (превью ≤200 симв.); **lenient** → текст возвращается + `⚠ … truncated at
   max_tokens` в лог.
7. Таймаут SDK → `LLMTimeoutError` с именем профиля и текущим значением
   («timed out after N minutes — profile 'Имя'»), без трейсбека.

Гейт строгости — **существующий флаг** `skip_cleaning` (прокидка
`lenient_on_truncation`); новый параметр в публичный API **не вводился** (вердикты 1, Q8).
Дефолты профиля: `max_tokens` пусто → 16384; `timeout_min` пусто → 10 мин (600 с —
подтверждено вердиктом 2); `extra_body` пусто → ничего; forbidden-ключи
`model/messages/max_tokens/stream/tools` отклоняются при сохранении (вердикт 7:
live-подсказка не нужна).

## §4. Финальная карта вызывающих (AST-инвентарь 30 колл-сайтов; `batch-g32e_ast_caller_inventory.txt`)

**Переводческие — строго (raise), без изменений:** `Supervertaler.py` :5645/:5790/:5927
(одиночный/пакет/FuzzyFixer в воркере), :49250 (`translate_current_segment`, в т.ч.
vision-сегмент), :47898 (`_fetch_llm_translation_async`), :49823 (QuickLauncher),
:51012/:52085/:52127/:52224 (Match Panel + progressive), `quicktrans.py:456`,
`tag_manager.py:1439` (AutoTagger bulk), `workers/proofread.py:117`, обёртка
`llm_clients.py:656`.

**Не-переводческие со `skip_cleaning=False` (пункт вердикта Q8):**

| Колл-сайт | Что делает | Финальный статус |
|---|---|---|
| `chat_view_widget.py:626` (`_do_send`) | обычный чат (попап/виджет) | **мягко** (G3.2e): partial как ответ ассистента + пометка + warning |
| `unified_prompt_manager_qt.py:6354` (`_context_aware_send`) | чат AI-ассистента (context-aware) | **мягко** (то же + AI-действия из partial) |
| `unified_prompt_manager_qt.py:6453` (`_send_ai_request`, non-analysis) | чат легаси-путь | **мягко** (то же) |
| `Supervertaler.py:10076` (`_build_image_extract_ai_callback`) | AI-подпись изображения в Image Extractor (vision) | **строго, ошибка → подпись пропущена** — вердикт Q10 (вариант (а)): усечение → raise → `except Exception` (:10101) → label=None, извлечение продолжается; лог в хендлере есть (:10102 «[Image Extractor] AI label call failed for …»), код не тронут |

**Lenient-флаг (подтверждён Q9, без изменений):** `unified_prompt_manager_qt.py:136`
(AutoPrompt-воркер, `is_analysis=True`), `workers/glossary.py:28` (Image Extractor
выкачивание терминов, `skip_cleaning=True`). Диспетчер `chat_backend.py:210`
(`skip_cleaning=is_analysis`) — не тронут. `painter.translate`-сайты
(`chat_message_delegate`, `tm_manager_qt`, `pseudo_translate`, `unified:594/670/736`,
`Supervertaler:5145`) — QPainter, к LLM отношения не имеют.

Timeout/Empty в чате — без изменений: пузырь «⚠ Error communicating with AI: …».

## §5. Матрица проб — **16/16 PASS**

Харнесс: fake loopback OpenAI-endpoint (`batch-g32_fake_endpoint_probe.py`,
ThreadingHTTPServer на `127.0.0.1:0`), изолированные iso-профили
(`E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-g32*`), завершение только своих PID
по фильтру командной строки (kill по имени образа не выполняется).

| # | Кейс | Результат |
|---|---|---|
| 1 | finish=stop, обычный ответ | byte-identical текст + usage |
| 2 | think-stripping ×6 (закрытый, вложенный, 2 блока, `</THINK>`, текст до/после, пустой content → Empty) | PASS |
| 2b | dangling closer ×3 (`</think>Привет`→`Привет`; `</THINK> mid Привет `→`mid Привет`; `<think>x</think>tail</think>Answer`→`Answer`) | PASS |
| 3 | незакрытый `<think` + length | `LLMTruncatedError` (unclosed, подсказки) |
| 3b | незакрытый opener + непустой content (stop) | raise, `partial_text=None` |
| 4 | content='' + reasoning_content + length | `LLMTruncatedError` (reasoning_tokens=12345) |
| 5 | content='' + reasoning_content + stop | `LLMEmptyResponseError`; reasoning **не утекла** |
| 6 | **translation strict**: непустой content + length | raise, `partial_text='Partial answer'`, в тексте «Max tokens» |
| 6b | lenient-тот же кейс | текст возвращён + `⚠ … truncated at max_tokens` |
| 7 | **регресс**: тело запроса профиля без новых полей == capture до правок | plain/vision byte-equal |
| 8 | `extra_body {"chat_template_kwargs":{"enable_thinking":false}}` | присутствует в теле запроса |
| 9 | timeout_min=0.0083, endpoint с задержкой (ретраи SDK: отложенные ответы на 3 попытки) | `LLMTimeoutError` с именем профиля и значением |
| 10 | валидация сохранения (не-JSON / массив / forbidden-ключи / max_tokens='abc' / timeout=-3) | заблокированы QMessageBox; валидный набор распарсен |
| 11 | vision-запрос того же профиля | max_tokens=1234 + chat_template_kwargs в теле |
| 12 | **чат (G3.2e)**: offscreen Qt, реальный `ChatViewWidget`+`ChatBackend` против endpoint с canned `finish_reason='length'` | assistant-сообщение = «Chat partial…» + «truncated by Max tokens»; warning в логе бэкенда; **не** пузырь ошибки |
| — | net-traps (Host-assert на всех запросах) | `requests=24`, `foreign_hosts=[]` |

Артефакты: `batch-g32_verify_matrix.json` (12), `batch-g32d_verify_matrix.json` (15),
`batch-g32e_verify_matrix.json` (16, финальная), `batch-g32e_chat_conversation_sample.json`.

## §6. Юниты

- `parse_profile_request_fields` — **11/11 PASS** (`batch-g32_unit_checks.log`).
- `_parse_completion_response` — **11/11 PASS** (strict-raise / lenient-return /
  dangling ×3 / unclosed-nonempty / unclosed-в-lenient-тоже-raise / empty+length /
  empty+stop / normal / partial-500; `batch-g32d_unit_checks.log`).

## §7. Полный оффскрин-набор (16 этапов) — **0 FAIL** (final-состояние)

Прогон G3.2e (`batch-g32e_run_full.sh`, main log `batch-g32e_run_full_main.log`,
SUITE_EXIT=0) на коде, идентичном финальному (sha256 сверены, §2); Q10 правок кода не
несёт → набор действителен как «после правок Q8 и Q10».

| Этап | Вердикт |
|---|---|
| fallback (9.4h), profiles (9.4f), statusbar prof, e2e, r9-a | IDENTICAL / совпадают (шум: тайминги, порт/тег) |
| qtchat, r9-ctrl, r9-rm, save modern, save-legacy | совпадают по вердиктам; в конструкторских stdout — непорядковые строки `[Superlookup]`/`[CrossPlatformKeySender]` (известный недетерминизм порядка импортов) |
| S-clean | IDENTICAL (шум: тайминги; `index.json` — транзитный файл по правилу M1e) |
| S-upgrade | HASH-DIFF **лучше базлайна**: `transient=[]` (в базлайне был транзитный `ai_assistant/index.json`) |
| regress | **3 хэша байт-идентичны базлайну**: export_txt `5a12501f934a589c`, export_docx `44828d90090f046d`, export_tmx `c413d56372e69dd9`; import-счётчики 5/5/4 |
| smoke | 42 элемента, гейт no-exception выполнен; известный базлайновый `PDF-Rescue: fitz`; QMenu `new-widgets` jitter — известная нестабильность (BACKLOG §9.11, доказана на базе `340ad21a`) |
| termbase | совпадает; diffs — clean/dirty состояние stage (известное) |
| about | IDENTICAL (шум: тайминги, порядок Okapi/AHK) |

Методология (записана для будущих прогонов): `kill_leftovers` набора фильтрует по
`ExecutablePath = E:\Dev\python-embed\*` и убивает все процессы bundled-рантайма,
включая параллельные фоновые пробы исполнителя → статику/инвентарь гонять после
завершения набора; регресс-харнесс на свежем stage требует предсозданных
`iso/`+`inputs/` (фиксация M1d).

## §8. Защиты — идентичны базлайну (тег g32e)

- AST-chain: **883 connect / 0 unresolved** (+10 к базлайну 873 — все из G3.2b UI:
  3×`editingFinished.connect`, 6×`blockSignals`, 1×`QMessageBox.warning`).
- pyflakes: **548** warnings; undefined-name строк 126, уникальных имён 4 — тот же
  набор, что в базлайне (filedialog 2, messagebox 19, tk 100, ttk 5).
- py_compile: канон (вне `docs/`) **109 ok / 0 fail**; справочный (со скриптами)
  **206 ok / 0 fail**.
- headless-импорты: **90 ok / 2 fail** (известные: `setuptools`, `fitz`).
- grep-гейт: CLEAN (8/8 файлов).
- После каждой правки — py_compile 0 ошибок (процедура батча).

Артефакт: `batch-g32e_static.log`, `batch-g32e_pyflakes_trace.log`.

## §9. Журнал вопросов и вердиктов (все закрыты)

| № | Вопрос исполнителя | Вердикт координатора | Исполнение |
|---|---|---|---|
| 1 | Непустой content + finish='length' — raising? | Raise в переводческих; чат/аналитика — ответ+warning; `partial_text`; существующий флаг | G3.2d (`10f621fd`), матрица 6/6b |
| 2 | Дефолт 600 с для всех профилей | Подтверждён, `timeout_min` остаётся | Без правок |
| 3 | Silent-места — поднимать в UI? | В M2 только `_fetch_llm_translation_async`; остальные — BACKLOG | BACKLOG §9.10 |
| 4 | Autotag-bulk не подписывает `translation_error` | Да, в M2 | BACKLOG §9.10 |
| 5 | Незакрытый `<think>` — закрывать case? | Строго: unclosed opener → raise; dangling closer → текст после последнего | G3.2d, матрица 2b/3b |
| 6 | QMenu в smoke-поле `new-widgets` | Проверить на базе → нестабильно и на базе | BACKLOG §9.11, smoke ×2 на worktree |
| 7 | Live-подсказка extra_body при вводе? | Не нужна, валидации при Сохранении достаточно | Без правок |
| Q8 | Чат стал строгим (flag False) — подтвердить? | Чат мягкий: ловить `LLMTruncatedError` в вызывающем коде, partial как ответ ассистента + пометка + warning; Timeout/Empty как были; карта не-переводческих вызывающих | G3.2e (`d59bc61e`), §4 настоящего отчёта |
| Q9 | Glossary Image Extractor lenient? | Lenient подтверждён; требование: «OCR-воркер (O.2) должен вызывать клиент в строгом режиме» (на будущее) | Записано дословно (§12) |
| Q10 | Image Extractor AI-подпись (`Supervertaler.py:10076`): (а) как есть / (б) мягко / (в) lenient | **(а)** — оставить как есть; единственная проверка — лог в `except` | Лог есть (:10102) → **ноль правок**; статус «строго, ошибка → подпись пропущена» в §4 |

## §10. Ручные сценарии для тестовой сборки (T-G3.2.x) — ИЗМЕНЕНЫ (предупреждение координатору)

Пересборка тестовой сборки (`D:\SupervertalerPortable_test\`) — отдельное решение Дмитрия
(батчи её не обновляли).

- **T-G3.2.1 (отключение thinking):** extra_body `{"chat_template_kwargs":
  {"enable_thinking": false}}` → запрос без thinking, ответ чистый.
- **T-G3.2.2 (бюджет на reasoning — переписан вердиктом 1):** маленький Max tokens на
  переводческом пути → диалог `LLMTruncatedError` «cut off at max_tokens mid-answer …
  Partial text: '…» (раньше: усечённый ответ подставлялся); пакет →
  `✗ BATCH ERROR` / `❌ Batch translation failed`.
- **T-G3.2.3 (таймаут):** Request timeout = 1 мин, endpoint с задержкой →
  `LLMTimeoutError` «… timed out after 1 minutes … — profile 'Имя'».
- **T-G3.2.4 (pure-reasoning stop):** content пуст, reasoning есть →
  «empty response (finish_reason='stop', reasoning_content present)»; перевод из
  reasoning не берётся.
- **T-G3.2.5 (регресс-дефолт):** профиль без новых полей → переводы обычные,
  таймаут 10 мин, тела запросов byte-identical старым (матрица 7).
- **T-G3.2.6 (валидация):** extra_body `[1,2]` / `{"model":"x"}` / max_tokens `abc` →
  сохранение блокируется QMessageBox с именем профиля.
- **T-G3.2.7 (lenient + чат):** чат-анализ / AutoPrompt / glossary-экстрактор при
  усечении → текст возвращается + warning, перевод не прерывается. **Явный пункт про
  чат (вердикт Q8):** маленький Max tokens + обычный вопрос в чате → **обычный пузырь
  ассистента** с восстановленным текстом и пометкой «⚠ Answer truncated by Max tokens»
  + warning в лог («[Chat] ⚠ answer truncated by Max tokens (N chars recovered)») —
  НЕ пузырь ошибки; пустой partial → пузырь «… (no recovered text)»; Timeout/Empty в
  чате — как раньше.
- **T-G3.2.8 (висячий `</think>`):** инжектированный opener → в перевод текст **после
  последнего** `</think>`; незакрытый opener → raise «unclosed reasoning block» во
  всех путях.

Image Extractor (Q10): усечение AI-ответа подписи → подписи нет, извлечение
продолжается, в логе «[Image Extractor] AI label call failed for …» — поведение
оставлено намеренно.

## §11. Изоляция и правила (соблюдены)

- Все пробы/наборы — изолированные iso-профили под `E:\Dev\Work_temp\SupervertalerPortable\`,
  реальные данные пользователя не тронуты; сети — только loopback (net-traps).
- Завершение процессов — только свои PID по фильтру командной строки; kill по имени
  образа не выполнялся ни разу.
- `git push` не выполнялся; `modules/settings_service.py` (известный CRLF-артефакт)
  и `.zcode/*` в батч не включались.

## §12. Требование на будущее (подтверждение Q9, записано дословно; код не тронут)

**«OCR-воркер (O.2) должен вызывать клиент в строгом режиме».** O.2 — vision-OCR вызов
(crop/трансформы → base64 → llm) из плана рекона `RECON_O0_OCR_TOOL_REPORT.md`; OCR-батчи
не начинались; требование фиксируется на старт O.2.

## §13. Артефакты (`docs/refactoring/audits/`)

- G3.2c: `batch-g32_fake_endpoint_probe.py` (расширен: items 1–11 + G3.2d + item 12 = 16),
  `batch-g32_run_full.sh`, capture-манифест и тела запросов, `batch-g32_verify_matrix.json`,
  `batch-g32_unit_checks.log`, `batch-g32_static_g32b.log`, 22 логов этапов, smoke-прогоны
  на базе `batch-g32_base_smoke1/2_340ad21a.log`.
- G3.2d: `batch-g32d_verify_matrix.json` (15/15), `batch-g32d_unit_checks.log` (11/11),
  `batch-g32d_static.log`.
- G3.2e (30): `batch-g32e_verify_matrix.json` (16/16), `batch-g32e_verify_run.log`,
  `batch-g32e_chat_conversation_sample.json`, `batch-g32e_static.log`,
  `batch-g32e_run_full.sh` + `batch-g32e_run_full_main.log`, 16 логов этапов + 5 seed-логов,
  `batch-g32e_ast_caller_inventory.txt`/`.py`, `batch-g32e_pyflakes_trace.log`.

Хронологический отчёт по sub-batch’ам: `BATCH_G3_2_REASONING_RESPONSES_REPORT.md`
(§1–§13, с ответом Q10 в §13.9).

**Стоп. Батч G3.2 завершён; дальнейшие шаги — по вердикту координатора
(M2 начинается только по команде Дмитрия и его промпту). Пуш не выполнялся.**
