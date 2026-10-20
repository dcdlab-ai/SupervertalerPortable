# ОТЧЁТ BATCH G3.2 — УСТОЙЧИВОСТЬ LLM-КЛИЕНТА К REASONING-МОДЕЛЯМ (custom_openai)

Дата: 2026-10-20. Исполнитель: ZCode-агент. Координатор: Дмитрий.
Пуш НЕ выполнялся (по правилу батча). Коммиты локальные.

## §0. Шаг 0 — состояние репозитория

- `git fetch`; `origin/main` == HEAD == `340ad21a` (снимок на старте).
- Неконтролируемое изменение `modules/settings_service.py` — известный CRLF-артефакт
  (строки идентичны, различие только в переводах строк). **Не тронуто** (по указанию).
- Рабочий интерпретатор: `E:\Dev\python-embed\python.exe` (3.13.15), CWD =
  `E:\Dev\SupervertalerPortable`. Временные каталоги:
  `D:\Temp\SupervertalerPortable\refactoring\batch-g32\` (пробы/захваты),
  общие сид-каталоги этапов — `...\batch-m1\` (совместно с M1/M1e-набором).

Итог батча: **3 коммита** (`951b54cd` G3.2a, `35873b2d` G3.2b, `a17fcb63` G3.2c),
пробная матрица **12/12 PASS**, юнит-парсер **11/11 PASS**, статика идентична базлайну,
полный оффскрин-набор **16/16** этапов соответствует базлайну M1e.

## §1. Коммиты

| Коммит | Содержание |
|---|---|
| `951b54cd` | G3.2a: `modules/llm_clients.py` — типизированные исключения, парсинг reasoning/think-блоков, log-hook; wiring в монолите (`set_llm_log_callback(self.log)`); починка прокси-импорта (httpx2) |
| `35873b2d` | G3.2b: поля профиля `max_tokens` / `timeout_min` / `extra_body` — UI диалога профилей, сохранение/валидация, применение во всех путях создания клиента |
| `a17fcb63` | G3.2c: probe-скрипт fake-endpoint + `batch-g32_run_full.sh` + 31 артефакт в `docs/refactoring/audits/` (код продукта не тронут) |

Суммарная дельта кода продукта (`git diff --numstat 340ad21a..HEAD`):
`Supervertaler.py` +192/−7, `modules/llm_clients.py` +242/−12, `modules/workers/proofread.py` +5/−2.

## §2. G3.2a — разбор OpenAI-ответа (один метод `_call_openai_with_usage`)

Новые сущности в `modules/llm_clients.py` (после `load_api_keys`, строки 141–335):

- `_REASONING_BLOCK_RE` (:141) — срезание закрытых `<think>…</think>` /
  `<thinking>…</thinking>`: несколько блоков, регистронезависимо, многострочно.
- `set_llm_log_callback(callback)` (:152) + `_llm_log` (:158) — модульный хук лога
  (по умолчанию `print`); в монолите подключён `self.log` (`Supervertaler.py:9016`,
  внутри `create_main_layout`) — сообщения модуля идут в панель лога приложения.
- Иерархия (:167–191): `LLMResponseError(ValueError)` c атрибутами
  `finish_reason / has_reasoning / reasoning_tokens`; подклассы
  `LLMTruncatedError`, `LLMEmptyResponseError`, `LLMTimeoutError`.
  Наследование от `ValueError` сохраняет работоспособность существующих
  `except`-обработчиков caller-путей.
- `_parse_completion_response(response, model)` (:269) — единая точка разбора:
  1. `choices` пустой → `LLMEmptyResponseError`;
  2. срезаются закрытые think-блоки; **reasoning_content как перевод НЕ используется**;
  3. после среза остался незакрытый `<think` → `LLMTruncatedError`
     («reasoning exhausted the max_tokens budget», подсказки: поднять Max tokens /
     отключить thinking через Extra request body с примером
     `{"chat_template_kwargs": {"enable_thinking": false}}`);
  4. content пуст + `finish_reason='length'` → `LLMTruncatedError` (с числом
     `reasoning_tokens` из `completion_tokens_details`);
  5. content пуст + `finish_reason != 'length'` → `LLMEmptyResponseError`
     (в тексте `finish_reason` и признак наличия reasoning_content);
  6. content непустой + `finish_reason='length'` → **ответ возвращается**,
     в лог пишется `⚠ LLM response for … truncated at max_tokens …` (открытый
     вопрос координатору, §11.1).
- `reasoning_content` читается через `getattr` (pydantic extra="allow"),
  `reasoning_tokens` — через `_extract_reasoning_tokens` (:263).
- Таймаут: `APITimeoutError` SDK перехватывается и превращается в
  `LLMTimeoutError` с текстом: «timed out after N minutes — profile 'Имя'.
  Increase 'Request timeout' …» (имя профиля + текущее значение, без трейсбека).
- Попутный дефект, найденный probe-ом (вне plan, починен в G3.2a, т.к. ломал
  сам прокси-пути на нашем рантайме): существующий `import httpx` в прокси-ветке —
  бандл-рантайм поставляет **httpx2**, не httpx. Исправлено аккуратно:
  `try: import httpx / except ImportError: import httpx2 as httpx`.
  Это единственная правка, выходящая за формулировки промпта (минимальная, в той же
  функции; на тело запроса не влияет — см. регресс матрицы 7).

## §3. G3.2b — поля профиля Custom (max_tokens / timeout / extra_body)

Формулировки промпта выполнены; DB-схема не тронута, ключи в профиль не дописываются
при загрузке (пустые поля удаляются `pop`):

- Модель: `parse_profile_request_fields(profile)` (:204, чистая функция, юнит-тестируемая):
  `max_tokens` — положительное целое, пусто → 16384; `timeout_min` — положительное
  число минут, пусто → 10 мин (600 с; заменяет жёсткие 120 с; gpt-5/o1/o3 по имени
  имели 600 с — сохранено, теперь 600 с дефолт для всех); `extra_body` — JSON-объект,
  пусто → ничего;Forbidden-ключи `model/messages/max_tokens/stream/tools` отклоняются.
- UI диалога профилей (`Supervertaler.py:19441–19490`): три новых поля с плейсхолдерами
  и tooltip-ами; синхронизация `_populate_profile_fields` / `_sync_fields_to_profile`
  с `blockSignals` (правило N1 учтено в новой wiring), 3×`editingFinished.connect`;
  включение/выключение в `update_combo_states` вместе с custom-радио.
- Валидация при сохранении: `_validate_custom_profiles` (монолит :47789) →
  `QMessageBox.warning` с именем профиля и текстом; сохранение блокируется, комбо
  выбирается на проблемный профиль.
- Применение везде — хелпер `_custom_profile_request_kwargs(profile)` (:47758)
  (ошибки парсинга в рантайме → `⚠ … using the default for this field` в лог,
  дефолт вместо падения). Точки применения (7):
  - `47958` фабрика `create_llm_client` (покрывает QuickTrans `_call_llm_translation`,
    chat `chat_backend.init_llm_client`, Image Extractor/AutoPrompt/сегментный vision,
    `_preview_combined_prompt`);
  - `39202` спавн ProofreadWorker; `49818` QuickLauncher; `50069` autotag_bulk;
    `50795` translate_batch (только в ветке `custom_openai`); `50990`
    `_fetch_llm_translation_async`; `52221` `_add_mt_and_llm_matches`.
  - `PreTranslationWorker.__init__` принимает `profile_kwargs` (спавны 50069/50795),
    все 4 конструкции `LLMClient` внутри воркера получают `**(self.profile_kwargs or {})`;
    `ProofreadWorker` принимает `profile_kwargs` из спавна.
- Вне scope (не тронуто): Custom MT (`call_custom_mt`), легаси-путь chat_backend для
  стандартных провайдеров, стриминг/отмена/чистка `_clean_translation_response`/
  перенумерация batch-ответа/целевой язык.

## §4. Проба matrix (fake loopback OpenAI-endpoint) — 12/12 PASS

Скрипт: `docs/refactoring/audits/batch-g32_fake_endpoint_probe.py`
(ThreadingHTTPServer на `127.0.0.1:0`; пишет сырые тела запросов + Host;
режимы capture/verify). Все пробы — изолированные iso-профили
(`D:\Temp\SupervertalerPortable\refactoring\batch-g32\` и общие batch-m1-каталоги),
реальные данные не тронуты. `kill_leftovers` — только свои PID по фильтру
командной строки (без kill по имени образа, по правилу).

**Capture (до правок, на HEAD 340ad21a)** — тела запросов профиля без новых полей:
plain 160 B `sha256 5a528a49…bc5f50`, vision 296 B `sha256 155cdd87…65bb7`
(манифест `batch-g32_capture_manifest.json`).

| # | Матрица | Результат |
|---|---|---|
| 1 | finish=stop, обычный ответ | byte-identical текст + usage, host локальный |
| 2 | 6 вариантов think- stripping (1 закрытый, 2 вложенный, 3 два блока, 4 регистр `</THINK>`, 5 текст до/после, 6 пустой content без блоков → LLMEmptyResponseError) | PASS |
| 3 | незакрытый `<think` + length | `LLMTruncatedError` (unclosed, подсказки) |
| 4 | content='' + reasoning_content + length | `LLMTruncatedError` (reasoning_tokens=12345 в атрибуте и тексте) |
| 5 | content='' + reasoning_content + stop | `LLMEmptyResponseError`; секретная строка reasoning в ответ **не утекла** |
| 6 | непустой content + length | ответ вернулся + предупреждение в лог |
| 7 | **регресс**: тело запроса профиля без новых полей == capture до правок | plain: byte-equal, vision: byte-equal |
| 8 | extra_body `{"chat_template_kwargs":{"enable_thinking":false}}` | присутствует в теле запроса |
| 9 | timeout_min=0.0083 (endpoint с задержкой) | `LLMTimeoutError` с именем профиля и значением. Нюанс: SDK ретраит таймауты (max_retries=2) — предоставлены отложенные ответы на все 3 попытки; иначе SDK получал ответ со 2-й попытки |
| 10 | валидация сохранения: не-JSON / массив / 5 forbidden-ключей / max_tokens='abc' / timeout=-3 | заблокированы с текстами; валидный набор распарсен (mt=5000, to=300.0s, eb=…) |
| 11 | vision-запрос (image_parts) того же профиля | max_tokens=1234 + chat_template_kwargs в теле — профиль применяется к vision |
| 12 | net-traps | requests=18, foreign_hosts=[] (ни одного запроса за пределы loopback) |

Артефакты: `batch-g32_verify_matrix.json`, `batch-g32_verify_run.log`,
`batch-g32_unit_checks.log` (`parse_profile_request_fields` 11/11).

## §5. Инвентарь п.5 — как caller-пути показывают исключения LLM

Все обработчики — `except Exception`; типизированные ошибки наследуют `ValueError`
и проходят через них. Изменений отображения по промпту **не вносилось** (только
тексты сообщений стали содержательными).

| Путь | Точка | Как пользователь видит ошибку |
|---|---|---|
| Одиночный сегмент (`translate_current_segment` :48958) | `client.translate` :49250 | `self.log("✗ Translation error: …")` + `QMessageBox.critical "Translation Error"` + статусбар «Translation failed»; пустой ответ (без исключения) → warning «No translation received from LLM.»; vision-загрузка картинок: `⚠️ Could not load figures` только в лог |
| Пакетный воркер (`PreTranslationWorker`) | :5645, :5790, :5927 | одиночные — `print` + return None → в окне прогресса строка `⊘ No translation`; пакет — traceback + `raise` → `run()` :5474 → `translation_error.emit` + в консоль прогресса `✗ BATCH ERROR: …`; подписчик :50926 → лог `❌ Batch translation failed: …`. **Autotag-bulk-спавн (:39269) `translation_error` НЕ подписывает** — видно только `✗ BATCH ERROR` в консоли прогресса |
| QuickTrans (`modules/quicktrans.py:464`) | `except` :476 | текст `[Error: …]` в чипе результата (без диалогов) |
| Чат (`chat_backend.send_ai_request` :207) | `except` :251 (log + `raise`) | обёртка `chat_view_widget._do_send` :625 → системный пузырь «⚠ Error communicating with AI: … Check the log for details.»; реальный путь чата — `unified_prompt_manager_qt._send_ai_request` :6429 (пузырь + трейсбек в лог); AutoPrompt → `_AutoPromptWorker.failed` → пузырь «⚠ Error generating prompt: <первая строка>» + полный трейсбек в лог |
| Image Extractor (`_do_extract_terms` :17184; воркер `workers/glossary.py:27`) | `failed.emit` | `QMessageBox.critical "Extraction Failed"` + лог |
| AutoPrompt preview vision (:38141) | `except` :38253 | только лог `⚠ Preview figure block skipped` |
| AutoTagger сегмента (`autotag_current_segment` :49442) | :49481, :4991 | `QMessageBox.critical "AutoTagger"` + лог + статусбар |
| Match-panel фон (`_fetch_llm_translation_async` :50941) | `except` :51052 | **silent**: только лог `LLM translation failed (silent): …` (по промпту — в список silent, не менять) |
| Match-панель синхронно (`_add_mt_and_llm_matches` :52158 и progressive-близнец :51875) | :52242 и др. | только лог `⚠ Error …` |
| Proofread (`workers/proofread.py`) | :87 init, :151 batch | `batch_error.emit` → метка диалога прогресса `Error: …` (init) / лог `⚠️ Proofreading error for batch N-M: …` (batch) |

Silent-места (перечислены, **не изменены**): `_fetch_llm_translation_async`,
preview vision, `_add_mt_and_llm_matches` (+progressive), загрузка картинок vision;
stdout-only: одиночные translate/FuzzyFixer внутри воркера, авто-tag bulk (без
подписки `translation_error`).

## §6. Статика (g5_12_static.py, тег g32b) — идентична базлайну

- AST-chain: **883 connect / 0 unresolved** (было 873; +10 = 3×`editingFinished.connect`
  + 6×`blockSignals` + 1×`QMessageBox.warning` — все из G3.2b UI).
- pyflakes: 548 warnings, множество undefined-name идентично базлайну
  (filedialog 2, messagebox 19, tk 100, ttk 5).
- py_compile: канон (вне docs/) **109 ok / 0 fail**; справочный (со скриптами)
  **205 ok / 0 fail** (было 201; +4 — добавленные audite-скрипты).
- headless-импорты: 90 ok / 2 fail (известные: `setuptools`, `fitz`).
- grep-гейт 9 файлов: чисто (монолит — только разрешённые зоны).

Лог: `batch-g32_static_g32b.log`.

## §7. Полный оффскрин-набор (16 этапов) — 16/16 соответствуют базлайну M1e

Скрипт `batch-g32_run_full.sh` (копия batch-m1e с TAG=g32, общие сид-каталоги
batch-m1). Main log: `batch-g32_run_full_main.log` (`SUITE_EXIT=0`);
логи этапов скопированы в `docs/refactoring/audits/batch-g32_*.log` (22 файла).

Сверка каждого лога с парой `*_m1e.log` (нормализация: имя тега, timestamps,
адреса потоков/объектов):

| Этап | Вердикт |
|---|---|
| fallback (9.4h), profiles (9.4f), statusbar prof, e2e, r9-a | IDENTICAL |
| qtchat, r9-ctrl, r9-rm, save, save-legacy | совпадают по вердиктам; в конструкторских stdout-логах непорядковые строки `[Superlookup] …` / `[CrossPlatformKeySender] AHK…` (недетерминированный порядок импортов; в M1e-базлайне строки те же) |
| S-clean | IDENTICAL (шум: тайминги; PRE-FILE `index.json` — транзитный файл, см. M1e-правило) |
| S-upgrade | HASH-DIFF: `transient=[]` (в M1e был `transient=['workbench/ai_assistant/index.json']`) — в этом прогоне транзитный файл не менялся; добавлений/удалений/изменений нет — **лучше базлайна** |
| regress | **3 хэша идентичны базлайну**: export_txt `5a12501f934a589c`, export_docx `44828d90090f046d`, export_tmx `c413d56372e69dd9`; import-счётчики 5/5/4; шум — obj-адреса, project_id, seg/sec |
| smoke | 42 элемента; гейт no-exception выполнен (41 no-exception + известный базлайновый `PDF-Rescue: ModuleNotFoundError fitz`); единственный содержательный diff: элемент Tools/Token-Usage-Costs `new-widgets=['QFrame','QMenu']` (было `['QFrame']`) — информационное поле (гейт — отсутствие исключения); QMenu создаётся при активации диалога, в код-пакет G3.2 не влияет (в UsageReportDialog новых правок нет) |
| termbase, about | IDENTICAL (шум: тайминги, порядок Okapi/AHK строк) |

Замечание харнесса regress (известное из M1e, к харнессу, не к коду): артефакты в
`iso/` + `inputs/`.

## §8. Пакет файлов сборки (репозиторий; тестовая сборка не обновлялась — решение Дмитрия)

`wc -l` / `sha256` (рабочие копии; базовые — `git show 340ad21a:<file>`):

| Файл | До | После | Δ | sha256 (рабочий, префикс) |
|---|---|---|---|---|
| `Supervertaler.py` | 55 153 | **55 338** | +185 | `7c499f0387850b34` |
| `modules/llm_clients.py` | 579 | **809** | +230 | `ffae2cac5c24f80d` |
| `modules/workers/proofread.py` | 151 | **154** | +3 | `e3cb001d024bbfc7` |

CRLF сохранён: `Supervertaler.py` CRLF=55 338, bare-LF=0; `llm_clients.py`
CRLF=809, bare-LF=0; `proofread.py` LF (как базово).

## §9. Ручные сценарии для тестовой сборки (T-G3.2.x, после пересборки по решению Дмитрия)

Оригинал — reasoning-модель в LM Studio (reasoning_content в ответе):

- **T-G3.2.1 (отключение thinking)**: Settings → AI Settings → профиль Custom:
  Extra request body = `{"chat_template_kwargs": {"enable_thinking": false}}` →
  сохранить → перевести сегмент; в логе LM Studio — запрос без thinking; ответ чистый.
- **T-G3.2.2 (бюджет на reasoning)**: Max tokens = 400, модель с длинным reasoning →
  сегмент: диалог «Translation Error» с текстом LLMTruncatedError (подсказки: поднять
  Max tokens / extra_body); пакет: `❌ Batch translation failed: …` в логе +
  `✗ BATCH ERROR` в прогрессе.
- **T-G3.2.3 (таймаут)**: Request timeout = 1 мин, endpoint с задержкой ответа →
  `LLMTimeoutError` «… timed out after 1 minutes … — profile 'Имя'» в диалоге сегмента
  (пакет — тот же текст в логе).
- **T-G3.2.4 (pure-reasoning stop)**: модель, вернувшая только reasoning
  (stop, content пуст) → «… returned an empty response (finish_reason='stop',
  reasoning_content present)»; перевод не подставляется из reasoning.
- **T-G3.2.5 (регресс-дефолт)**: профиль без новых полей (пустые) → переводы
  обычные, таймаут 10 мин; тела запросов совпадают со старыми (probe-матрица 7).
- **T-G3.2.6 (валидация)**: Extra request body = `[1,2]` / `{"model":"x"}` /
  Max tokens = `abc` → сохранение блокируется QMessageBox с именем профиля.

## §10. Артефакты в репозитории (`docs/refactoring/audits/`)

`batch-g32_fake_endpoint_probe.py`, `batch-g32_run_full.sh`,
`batch-g32_capture_manifest.json`, `batch-g32_req_plain.body`, `batch-g32_req_vision.body`,
`batch-g32_verify_matrix.json`, `batch-g32_verify_run.log`, `batch-g32_unit_checks.log`,
`batch-g32_static_g32b.log`, 22 лога этапов (`batch-g32_probe_*`, `batch-g32_seed_*`,
`batch-g32_e2e_after`, `batch-g32_regress_after`, `batch-g32_smoke_after`,
`batch-g32_tb_after`, `batch-g32_about_after`, `batch-g32_run_full_main.log`).

## §11. Вопросы координатору

1. **Непустой content + finish='length'**: сейчас ответ **возвращается** + warning в
   лог (§2 п.6). Поднимать ли в исключение? По промпту это открытая точка.
2. **Дефолт 120 с → 600 с для всех профилей**: принято как «пусто = 10 мин»;
   для не-reasoning имён это тоже 600 с (было 120). Подтвердить смену дефолта.
3. **Silent-места** (§5) перечислены без изменений. Поднимать ли их в UI —
   отдельным батчем (кандидат: `_fetch_llm_translation_async`)?
4. **Autotag-bulk не подписывает `translation_error`** (только консоль прогресса) —
   включить в M2-гейт?
5. **Срезание `<think>`**: сейчас срезается и возврат; закрывать ли case «часть
   ответа была внутри незакрытого блока» (строгий режим — raise при любом `<think`
   в content)?
6. **QMenu в smoke-элементе Token-Usage-Costs** (§7) — зафиксировать как известную
   нестабильность базлайнового поля `new-widgets`?
7. **Валидация extra_body** срабатывает только при Сохранении. Нужен ли live-подсказка
   на editingFinished?

## §12. Дополнение — вердикт координатора (ответы 1–7, 2026-10-20) и sub-batch G3.2d

### 12.1 Ответы вердикта → исполнение

| № | Ответ координатора | Исполнение |
|---|---|---|
| 1 | Непустой content + finish='length': raise в переводческих путях; чат/аналитика (`skip_cleaning=True`) — ответ+warning; атрибут `partial_text`; существующий флаг, без новых параметров; перечислить вызывающих | **G3.2d** (код `10f621fd`), §12.2–12.3; матрица 6 (strict) / 6b (lenient) |
| 2 | Дефолт 600 с подтверждён, `timeout_min` остаётся | Без правок (поведение G3.2b) |
| 3 | Silent-места: в M2 только `_fetch_llm_translation_async` (текст в чипе, без модалки); остальные — BACKLOG | BACKLOG §9.10 (код не тронут) |
| 4 | Autotag-bulk: да, в M2 — подписать `translation_error`, поднимать в консоль прогресса | BACKLOG §9.10 (запись в план M2, код не тронут) |
| 5 | Строго: незакрытый открывающий think-тег → raise (ничего не возвращать); «висячий» закрывающий `</think>` → текст после **последнего** `</think>`; добавить в матрицу | **G3.2d**: `_CLOSE_REASONING_RE`, unclosed-raise во всех путях; матрица 2b / 3b |
| 6 | QMenu: зафиксировать как нестабильность, сначала smoke на базе `340ad21a` | Smoke ×2 на базе (worktree, изолированный профиль): run1 `['QFrame']`, run2 `['QFrame','QMenu']` → **поле нестабильно и на базе** → известная нестабильность, BACKLOG §9.11; разбирательство не требуется (условие «стабильно на базе» не выполнено). Логи `batch-g32_base_smoke1_340ad21a.log`, `batch-g32_base_smoke2_340ad21a.log` |
| 7 | Live-подсказка не нужна, валидации при сохранении достаточно | Без правок (валидация Save действует, G3.2b) |

### 12.2 G3.2d — код (1 коммит `10f621fd`, только `modules/llm_clients.py`: 809 → **851**, sha `e8d5c0bb…`, CRLF сохранён, bare-LF 0)

- `_CLOSE_REASONING_RE` (:148) — закрывающий `</think>`/`</thinking>` без открывающего (шаблоны вставляют opener в промпт, в ответе остаётся только closer).
- Базовый `LLMResponseError.__init__` получил атрибут **`partial_text`** (:176–187).
- `_parse_completion_response(response, model, lenient=False)` (:276): после среза закрытых блоков берётся текст **после последнего** закрывающего тега; **незакрытый** открывающий тег → `LLMTruncatedError` во **всех** путях (ничего не возвращается, `partial_text=None`); пустые случаи без изменений; непустой content + `finish='length'`: lenient → возврат + `⚠ … truncated at max_tokens` (как было), strict → `LLMTruncatedError` «cut off at max_tokens mid-answer» с **`partial_text`** = восстановленный текст (превью ≤200 симв. в сообщении) + подсказка «Increase 'Max tokens'».
- Строгость — **существующим флагом**: `skip_cleaning` прокидывается на :715 (`lenient_on_truncation=skip_cleaning`) → `_call_openai_with_usage` (:736, default False) → :817. Публичный API и монолит не тронуты (монолит **55 338**, `7c499f03…`).

### 12.3 Вызывающие — strict/lenient (ответ 1, существующий флаг)

**Strict (`skip_cleaning=False` → raise):** одиночный сегмент `translate_current_segment` :49250 (в т.ч. vision-сегмент — тот же вызов с images); `PreTranslationWorker` :5645/:5790/:5927 (одиночные, пакет, FuzzyFixer, одиночные внутри воркера); QuickTrans `quicktrans.py:464`; AutoTagger `autotag_current_segment` :49481; `_fetch_llm_translation_async` :51012; `_add_mt_and_llm_matches` :52224 (+progressive-близнец :51875); Proofread `workers/proofread.py` :117/:151; **обычный чат** — `chat_backend.send_ai_request` :216 с `skip_cleaning=is_analysis` (для чата False).

**Lenient (`skip_cleaning=True` → возврат+warning):** чат-анализ (`is_analysis=True`), AutoPrompt-воркер (`is_analysis=True`), JSON-экстрактор глоссария `workers/glossary.py:31`.

Факты гейта флага (расходятся с формулировками вердикта — зафиксировано как есть, вопросы Q8/Q9 в §12.9):
- Обычный чат — flag False → **strict** (вердикт приравнял чат к `skip_cleaning=True`). Усечённый обычный чат поднимает исключение → пузырь «⚠ Error communicating with AI: …» (обёртка перехватывает, не падает).
- Image Extractor (glossary-воркер) — flag True → **lenient** (вердикт отнёс «vision/Image Extractor» к переводческим путям). Vision **внутри сегмента перевода** (:49250) — строгий; выкачивание терминов из картинки — снисходительное.

### 12.4 Матрица проб — **15/15 PASS** (перепрогон по ответам 1 и 5)

Новые кейсы: **2b-dangling-close** (3 кейса: `</think>Привет`→`Привет`; `</THINK> mid Привет `→`mid Привет`; `<think>x</think>tail</think>Answer`→`Answer`); **3b-unclosed-nonempty** (видимый текст + незакрытый opener, finish=stop → raise, `partial_text=None`); **6-strict-length-raise-partial** (`partial_text='Partial answer'`, в тексте 'Max tokens'); **6b-lenient-length-warning** (lenient → текст возвращён + `truncat` в логе). Прежние 1–11 зелёные, регресс 7 — byte-equal с capture. net-traps: `requests=23 foreign_hosts=[]`. Артефакты: `batch-g32d_verify_matrix.json`, `batch-g32d_verify_run.log`.

### 12.5 Unit на `_parse_completion_response` — **11/11 PASS**

strict-raise / lenient-return / dangling (3, в т.ч. верхний регистр) / unclosed-nonempty / unclosed-в-lenient-тоже-raise / empty+length / empty+stop / normal / partial-500. Артефакт `batch-g32d_unit_checks.log`.

### 12.6 Статика (тег g32d) — идентична базлайну

chain 883/0-unresolved; pyflakes 548 (undefined 126/4 — тот же set); канон py_compile **109/0**; справочный **206/0** (+1 — unit-скрипт учтён в списке аудитов); headless 90/2 (setuptools, fitz — известные); grep-гейт CLEAN. Артефакт `batch-g32d_static.log`. Полный 16-этапный оффскрин-набор **не перепрогонялся**: G3.2d трогает только парсер ответа в `llm_clients.py` (монолит/воркеры/UI не затронуты; покрыто пробой+юнитом), набор a17fcb63 для пакета из тех же файлов действителен.

### 12.7 QMenu (ответ 6)

Worktree `340ad21a` (без правок G3.2), изолированный профиль, smoke ×2: run1 `new-widgets=['QFrame']`, run2 `['QFrame','QMenu']` → поле `new-widgets` элемента `Tools/Token-Usage-Costs` плавает **уже на базлайне** — известная нестабильность, записана в BACKLOG §9.11; починка не требуется, появление QMenu в наших прогонах регрессией не считать.

### 12.8 Ручные тесты — ИЗМЕНЕНЫ (предупреждение координатору)

- **T-G3.2.2 — переписан:** маленький Max tokens на переводческом пути → диалог `LLMTruncatedError` «cut off at max_tokens mid-answer … Partial text: '…» (было: усечённый ответ подставляется + warning в лог); пакет → `✗ BATCH ERROR` / `❌ Batch translation failed`.
- **T-G3.2.7 (новый) — lenient:** чат-анализ / AutoPrompt / glossary-экстрактор при усечении → текст **возвращается**, в логе `⚠ … truncated at max_tokens`; перевод не прерывается.
- **T-G3.2.8 (новый) — висячий `</think>`:** ответ шаблона с инжектированным opener → в перевод идёт текст **после последнего** `</think>`; незакрытый opener в content → raise «unclosed reasoning block» во всех путях (ничего не подставляется).

### 12.9 Вопросы координатору

- **Q8:** обычный чат (flag False) стал строгим — по инструкции «использовать существующий флаг». Подтвердить строгость чата или сделать lenient (явная передача флага для обычного чата)?
- **Q9:** glossary Image Extractor (flag True) остался lenient — подтвердить lenient для экстрактора (vision внутри сегмента перевода — строгий)?

**Стоп. Дальнейшие шаги — по вердикту координатора. Пуш не выполнялся.**
