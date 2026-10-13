# ОТЧЁТ Batch #9.3 — Облачные LLM-провайдеры и Ollama удалены; молчаливая миграция provider → custom_openai (БЭКЕНД; UI — в 9.4)

Дата: 2026-10-11. База кода: 13e1ad29 (код Batch #9.2), монолит 55 997 / SHA `287781c1…` (CRLF),
modules `6e3e23f3…`/`317a5677…`/`3d883246…`. Рекон R9 §2.1–2.7 использован как карта; все границы
выведены заново по AST текущего кода. Промпт: Batch #9.3 (4 коммита 9.3a–d, обойма защит после
каждого, спец-пробы на фейк-endpoint, матрица совместимости, ловушка сети).

## §0 Baseline (Этап 0)

- Дрейф 13e1ad29..HEAD: только docs/ + PROJECT_STATUS.md — чисто.
- Эталоны совпали (монолит 55 997 CRLF / `\r\r\n`=0; quicktrans 1627 LF; panel 2422; settings_service 555).
- py_compile: **канонический 110/0**, справочный 163/0 (b9-2 добавил 3 аудит-скрипта).
- headless: **91 ok / 2 fail** (setup: setuptools; pdf_rescue_Qt: fitz — известные).
- pyflakes: **576 / 126 / 4** (монолит undefined = 0). Примечание: в таблице отчёта 9.2 стояло
  577 — фактический финал 9.2 (batch9-2_pyflakes_final_summary.txt) = 576; за базу принята 576.
- AST startup-chain: **907 / 0**. S-clean OK; S-upgrade HASH-DIFF пуст; regress_common 6 sha
  (5a12501f / 44828d90 / c413d563); Tools-smoke **42 OK**; termbase OK; About OK.
- **Контроль «ДО» (фейк OpenAI-совместимый endpoint 127.0.0.1, openai 3.24.0 в дев-рантайме)** —
  `batch9-3_e2e_verdict_before.json` (аудит-артефакт):
  | Сценарий | запросы к фейку | модель | результат |
  |---|---|---|---|
  | single (translate_current_segment, строка 1) | 1 | **fake-llm** (профиль) | «Goedemorgen», draft, TM-запись |
  | batch 3 (translate_batch, диалог LLM по умолчанию) | 1 | **custom-model** (!) | 2/3 сегментов переведены |
  | Match Panel LLM (`_add_mt_and_llm_matches`) | **0** | — | LLM-совпадений нет (ветки только openai/claude/gemini по ключам) |
  | proofread 2 (`_run_proofreading`) | 1 | fake-llm (явно передан) | ✓✓, notes пустые |
  | chat (`send_ai_request`) | 1 | fake-llm (фабрика) | «Goedemorgen» |
  Все запросы: POST `/v1/chat/completions`, `Authorization: Bearer prof-key-123` (ключ профиля
  приоритетнее). **Квирки ДО**: batch/proofread резолвили модель плоским `custom_openai_model`
  (пусто → DEFAULT_MODELS → «custom-model» ушёл на эндпоинт); Match Panel вообще не имел
  custom-ветки. Оба устранены в 9.3b (см. §2).

## §1 Рекон (Этап 1, пункты 1–8)

1. **Выбор провайдера вне llm_settings.provider**: `current_provider`/`current_model` (монолит
   10849/23620/23770/37212 — читатели `f"{provider}_model"`; для custom_openai фабрика всё равно
   берёт модель профиля → значения безвредны, не трогались); QuickTrans `mtql_*`-флаги + `llm_defs`
   (8 LLM-дефов, коды CL/GPT/GEM/MIS/DS/OR/OLL/CUS); `provider_enabled_states` llm_*; usage ledger —
   только запись. Миграция значений не нужна нигде, кроме `llm_settings.provider` (единая точка —
   `SettingsService.load_llm_settings`, подтверждено: все читатели идут через неё).
2. **load_llm_settings**: дефолты (provider 'openai' + 4 облачные модели), авто-миграция плоского
   конфига 255–263, setdefault-механика. Целевое (а)–(в) реализовано в 9.3a. Нормализация endpoint:
   единственная реализация перенесена в `SettingsService.normalize_custom_endpoint`, монолит —
   делегат (нулевое дублирование; 15/15 кейсов 9.1b сходятся — аудит `batch9-3_check_93a_unit.py`).
3. **«Не настроено»**: ДО — клиент создавался с base_url=None → openai-SDK шёл на api.openai.com с
   ключом-заглушкой (сетевая ошибка/трейсбек-диалог). ПОСЛЕ — единое вежливое сообщение
   «Custom LLM profile is not configured — Settings → AI Settings» на всех интерактивных путях
   (single/batch/proofread/quicklauncher/autotag×2/Terms-Extract), тихий выход на фоновых
   (Match Panel, _fetch_llm), строка чипа в QuickTrans, лог в chat. Гейт-хелпер:
   `_custom_llm_ready(settings)` — активный профиль С НЕПУСТЫМ endpoint.
4. **Карта веток монолита** — все зоны сведены (§2, коммит 9.3b). create_llm_client,
   _resolve_provider_model (не менялся — уже custom-корректен), translate_current_segment (вкл.
   Ollama-прогресс-диалог 55 строк и Ollama-промпт-ветку 78 строк), translate_batch,
   _fetch_llm_translation_async, run_grid_quicklauncher_prompt, autotag_current_segment,
   autotag_segments_bulk (+ воркерные _autotag_segment_llm/_run_autotag_only),
   _run_proofreading+show_proofread_dialog, PreTranslationWorker (4 метода),
   _add_mt_and_llm_matches LLM-часть, Image Extractor callback.
5. **Другие модули**: workers/proofread.py 8-веточный выбор ключа → 1; chat_backend дефолт +
   keyless; chat_view keyless (меню моделей НЕ тронуто); quicktrans llm_defs → [Custom];
   unified_prompt_manager vision-payload gemini-ветка → base64; llm_pricing._FREE_PROVIDERS =
   ("ollama",) — **не тронуто** (правка — 9.4): влияние на custom_openai нулевое и сейчас
   (custom ∉ free → стоимость считается по pricing.json, для модели без прайса cost_known=false,
   счётчик токенов работает — решение Д.1 сохранено).
6. **llm_clients.py**: таблица R9 §2.3 подтверждена; OPENAI_MODELS/GEMINI_MODELS в модуле
   отсутствуют (chat_view держит их inline). Потребители каждого имени сняты grep'ом: у
   check_ollama_status/get_claude_model_info/get_ollama_model_info/get_google_translation/
   get_openai/get_claude_translation/DEEPSEEK_MODELS живых потребителей НЕТ (get_google_translation —
   только внутри мёртвого `_REMOVED_add_mt_and_llm_matches_progressive`); MISTRAL/CLAUDE/OLLAMA/
   OPENROUTER_MODELS + set_ollama_timeout — UI-зависимые (меню чата, Save страницы AI Settings) →
   **список «только после 9.4»** (§7).
7. **Image Extractor**: callback остался на chat_backend; гейт 3 теперь сообщает «Vision for
   Custom profile is not enabled yet»; gemini-ветка payload удалена. G5-блок translate_current_segment
   не тронут (включая его `provider == "gemini"` — разрешённый остаток).
8. **Матрица совместимости** — 11×4 = 40/40 PASS (`batch9-3_check_93d_matrix.py`): провайдеры
   {openai, claude, gemini, mistral, deepseek, openrouter, ollama, custom_openai, '', mystery-llm,
   отсутствует} × профили {есть, нет, только legacy-плоские, active не найден}. Во всех случаях:
   возвращаемый provider == custom_openai, диск не переписан, профили/legacy-ключи целы.

## §2 Что сделано (коммит | файл | зона)

| Коммит | Файл | Зона | Изменение |
|---|---|---|---|
| 9.3a f5fe9477 | settings_service.py | load_llm_settings | дефолт provider=custom_openai; облачные дефолты моделей удалены; молчаливая миграция provider в ВОЗВРАЩАЕМОМ словаре; legacy-плоский → профиль с нормализацией endpoint |
| 9.3a | settings_service.py | +normalize_custom_endpoint | единственная реализация правила 9.1b |
| 9.3a | settings_service.py | load_provider_enabled_states | дефолты → только llm_custom_openai; механизм и старые ключи (инертно) целы |
| 9.3a | chat_backend.py | init_llm_client | дефолт → custom_openai (вывод по ключам openai/claude/gemini удалён); keyless = custom_openai |
| 9.3a | Supervertaler.py | _normalize_custom_endpoint | делегат в SettingsService (−22 строки) |
| 9.3b 6c75769a | Supervertaler.py | +_custom_llm_ready | гейт-хелпер «настроено = профиль с endpoint» |
| 9.3b | Supervertaler.py | create_llm_client | только custom_openai; чужой provider → ValueError «has been removed»; openrouter-base_url/ключевые ветки/gemini-прокси удалены |
| 9.3b | Supervertaler.py | translate_current_segment | ключевые ветки ollama/облаков удалены; Ollama-прогресс-диалог (55) и Ollama-промпт (78) удалены; гейт «не настроено» |
| 9.3b | Supervertaler.py | translate_batch | retry-дефолты custom_openai/custom-model; llm_model через _resolve_provider_model (чинит ДО-квирк «custom-model»); exec-ветка сведена; гейт до старта воркера |
| 9.3b | Supervertaler.py | _fetch_llm_translation_async | профиль-endpoint гейт → тихий выход; provider_code 'CUS' |
| 9.3b | Supervertaler.py | _add_mt_and_llm_matches | LLM-часть переписана: один CUS-совпадение от активного профиля (ДО: 0 — веток custom не было) |
| 9.3b | Supervertaler.py | quicklauncher/autotag×2 | ключи: профиль → api_keys → not-needed; гейты |
| 9.3b | Supervertaler.py | _run_proofreading + show_proofread_dialog | модель через _resolve_provider_model; гейт; прокси |
| 9.3b | Supervertaler.py | PreTranslationWorker ×4 | api_key = custom_api_key or api_keys[custom_openai] or 'not-needed' |
| 9.3b | Supervertaler.py | Image Extractor | сообщение «Vision for Custom profile is not enabled yet»; gemini-payload удалён |
| 9.3c 89a20764 | workers/proofread.py | выбор ключа | 8 веток → custom-цепочка |
| 9.3c | chat_view_widget.py | keyless | ollama убрана (меню моделей — до 9.4) |
| 9.3c | quicktrans.py | llm_defs | только Custom/CUS (чекбоксы таба до 9.4 чипов не создают) |
| 9.3c | unified_prompt_manager_qt.py | vision payload | gemini-ветка → base64 (G5-логика фигур не менялась) |
| 9.3d 59290c98 | llm_clients.py | весь модуль | 2000 → **787** (−1213); один клиент `_call_openai_with_usage`; см. §2d ниже |
| 9.3d | chat_backend.py | key-chain | gemini-тернарник удалён (provider всегда custom) |
| 9.3d | Supervertaler.py | _do_extract_terms | гейт + _resolve_provider_model |

**9.3d детально — удалено**: `_call_claude_with_usage`, `_call_gemini_with_usage`, legacy
`_call_openai/_call_claude/_call_gemini/_call_gemini_rest/_call_ollama`, хелперы
`_resolve_ollama_timeout/_sanitize_ollama_endpoint`, `LLMClient.check_ollama_status/
get_claude_model_info/get_ollama_model_info` (потребителей нет — монолит импортирует
check_ollama_status из local_llm_setup), `DEEPSEEK_MODELS`, CLI: `main/get_openai_translation/
get_claude_translation/get_google_translation/_load_api_key/_convert_lang_name_to_code`
(живой потребитель get_google_translation был только в мёртвом `_REMOVED_…`, очередь 8.18).
**Изменено**: translate_with_usage — одна ветка (чужой provider → ValueError);
_call_openai_with_usage — без OpenRouter-заголовков и cache_control-массива
(enable_prompt_caching оставлен в сигнатуре); __init__ — без mistral/deepseek/openrouter
base_url, keyless = custom_openai; DEFAULT_MODELS → custom_openai; VISION_MODELS = {}.
**Сохранено до 9.4**: set_ollama_timeout + _ollama_timeout_override,
MISTRAL/CLAUDE/OLLAMA/OPENROUTER_MODELS, load_api_keys дословно (включая ollama_endpoint-env и
google→gemini алиас — пинг-кластер 9.4 ещё читает OLLAMA_ENDPOINT), LLMConfig.

## §3 Диффы (только код)

- 9.3a: 3 файла, +70/−49 (монолит −22, settings_service +43, chat_backend ±).
- 9.3b: Supervertaler.py +192/−475 (итог −283).
- 9.3c: 4 модуля +26/−48.
- 9.3d: llm_clients +42/−1255; chat_backend ±10/4; quicktrans +4; монолит +15/4.
- Итог батча по коду: **−1567 строк** (монолит 55 997 → **55 703**; llm_clients 2000 → 787).
- Ориентир промпта: llm_clients −700…−1000 (факт −1213: legacy-клиенты оказались крупнее),
  монолит −500…−700 (факт −294: keepwarm/UI-зоны честно оставлены до 9.4), прочие −100…−200 (факт −70).

## §4 Валидация по коммитам (логи `docs/refactoring/audits/batch9-3_*`)

| Метрика | base | 9.3a | 9.3b | 9.3c | 9.3d |
|---|---|---|---|---|---|
| py_compile канон/справ | 110/0 · 163/0 | = · 163/0 | = · 164/0 | = · 165/0 | = · 165/0 |
| headless | 91/2 | = | = | = | = |
| pyflakes | 576/126/4 | 576/126/4 | 573/126/4 | 573/126/4 | **562/126/4** |
| AST chain | 907/0 | 907/0 | 907/0 | 907/0 | 907/0 |
| S-clean / S-upgrade | OK / пуст | = | = | = | = |
| regress 6 sha | 5a12501f/44828d90/c413d563 | = | = | = | = |
| smoke / TB / About | 42 OK / OK / OK | = | = | = | = |

- Справочный py_compile растёт только от аудит-скриптов (163→165: check_93a_unit, probe_spec).
- pyflakes −14 — предупреждения удалённого кода (f-strings/импорты в ollama-диалоге, legacy-клиентах,
  CLI); монолит undefined = 0 на каждом шаге; 4 уникальных имени = baseline-набор
  (filedialog/messagebox/tk/ttk в tmx_editor). Разрешённое снижение, промпт допускает.
- chain 907/0: вызовы стартовой цепочки не задеты (удалялись только провайдерные ветки внутри
  уже-резолвленных методов).
- **Grep-гейт** (`batch9-3_grep_gate.py`, финал `batch9-3_grep_gate_final.txt`): 0 FAIL по
  монолиту и всем модулям. Разрешённые остатки (явный список): мёртвые
  `_REMOVED_add_mt_and_llm_matches_progressive` (52429–52702) и `_save_llm_settings_from_ui`
  (8.18); UI-9.4 зоны `_update_llm_indicator` (ветки провайдеров статус-бара), keepwarm-кластер
  `_setup_ollama_keepwarm/_apply_ollama_timeout_setting/_start|_stop_ollama_keepwarm_timer/
  _ping_ollama_keepwarm`, `_apply_gemini_proxy` (зовётся из Save AI Settings — 23849),
  show_about («Supports OpenAI, Claude, Gemini & Ollama» — текст), страница AI Settings +
  `_save_ai_settings_from_ui`/`_save_api_keys_from_ui`, QuickTrans-таб + `_save_mt_quick_lookup_settings`;
  G5 figure-блок translate_current_segment (его `provider == "gemini"`); chat_view меню моделей;
  `set_ollama_timeout`/`*_MODELS` в llm_clients; инертные ключи в settings_service-комментариях;
  pdf_rescue_Qt.py (вне 9.x); docs/audits.

## §5 ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ (замена файлов, ничего не удалять)

| Файл | SHA256 | Строк | EOL |
|---|---|---|---|
| Supervertaler.py | `4bc104cb76922ebd9bf81510372279679abc0c30bb6a75e1d8cb94ee8b00ce09` | 55 703 | CRLF |
| modules/llm_clients.py | `5d70dbb25a3687fabf7ea520e05c2cfea53551092e57fd2b8c36fae576a70426` | 787 | LF |
| modules/settings_service.py | `f8d0215032c5ce5f97e1a1307cb60cda63ac90691e11db34c208c87b77d16d86` | 598 | LF |
| modules/chat_backend.py | `cc3b6a2d397f60d419a9eda83f29828d595fc3a40eb8cda64f8eadadbe5afd1a` | 284 | LF |
| modules/chat_view_widget.py | `47e5ee7143d4482fe16b328aa82556e936422a4c7c7c085328df51a027106728` | 1024 | LF |
| modules/quicktrans.py | `ee71293b894088b0fb32252997133d4228f5371f133946031085ee2dc37cb75e` | 1626 | LF |
| modules/unified_prompt_manager_qt.py | `10ae1a0b0f20cca2a6b0ca413e846789abe563347042725b5e0faa71f3d8d5fd` | 6833 | LF |
| modules/workers/proofread.py | `1b9b5c44c58cd7cb4de27be735651cb33a0a8195132f218acc3c5dabe09cfb50` | 151 | LF |

Не менялись (проверено SHA): modules/translation_results_panel.py (`317a5677…`). В тестовой сборке
должен присутствовать пакет `openai` (SDK; проверен в дев-рантайме 3.24.0, ленивый импорт).

## §6 Сценарии T9.3.x (тестовая сборка; копия user_data; локальный llama-server запущен)

- **T9.3.1** Скопировать настройки, в JSON выставить provider="openai", затем "claude", затем
  "ollama"; старт приложения: без ошибок, статус-бар — профиль Custom, страница AI Settings
  открывается, Save не падает (после Save provider остаётся custom_openai).
- **T9.3.2** Перевод текущего сегмента (Ctrl+T) через локальный llama — как раньше; модель в
  статусе = модель профиля.
- **T9.3.3** Пакетный перевод 5–10 сегментов — прогресс, запись в TM; в запросе модель = модель
  профиля (был дефект «custom-model»).
- **T9.3.4** (исправлено после замечания Дмитрия 2026-10-13, см. §7 находка 2b) — НЕ имеет
  видимого UI-проверочного действия: панель-потребитель LLM-строк совпадений удалена из UI до
  Batch #1, метод `_add_mt_and_llm_matches` без вызовов. Проверка: при включённом чекбоксе
  «Enable LLM (AI) matching on segment selection» поведение панели совпадений НЕ меняется
  (так и должно быть), ошибок/трейсбеков в логе нет. Видимый CUS-чип — в QuickTrans (T9.3.7).
- **T9.3.5** Proofread 3–5 сегментов — как раньше.
- **T9.3.6** Chat/AI Assistant: сообщение и ответ.
- **T9.3.7** QuickTrans (Ctrl+Alt+Q): LLM-ответ от Custom (чип CUS).
- **T9.3.8** Token Usage & Cost: новые записи provider=custom_openai; исторические записи
  openai/claude/… остаются и показываются.
- **T9.3.9** Настройки без профилей Custom: везде вежливое «Custom LLM profile is not
  configured — Settings → AI Settings», без падений и без сетевых попыток.
- **T9.3.10** Image Extractor c «🤖 AI label»: сообщение «Vision for Custom profile is not
  enabled yet», извлечение продолжается text-pattern-детектором.
- **T9.3.11** Общий smoke: .svproj, импорт txt/md/docx, TMX, выход.

## §7 Непокрытые проверки и находки; имена «только после 9.4»

- **Находки**: (1) ДО-квирк batch/proofread — плоский `custom_openai_model` вместо модели профиля —
  исправлен (_resolve_provider_model); в Т9.3.3/T9.3.1 проверять модель в запросе/статусе.
  (2) Match Panel не имел custom-ветки — добавлена (relevance 88, код CUS).
  **2b (уточнение после замечания Дмитрия 2026-10-13):** формулировка была неполной. Метод
  `_add_mt_and_llm_matches` (52524), куда добавлена custom-ветка, **не имеет живых вызовов**:
  единственный путь по выделению сегмента — `_add_mt_and_llm_matches_progressive` (52018), а он
  заглушка `pass` (панель Translation Results удалена из UI до Batch #1, baseline 13bd37fb).
  E2E-проба меряла метод прямым вызовом, не через UI. Выводы: (а) в UI новой CUS-строки совпадений
  появиться не может — панели-потребителя нет; (б) чекбокс «Enable LLM (AI) matching on segment
  selection» (`enable_llm_matching`) фактически инертен — читается только в prefetch-заглушке
  (28655, `pass`) и в бесхозном методе — **кандидат в 8.18** (включая сам
  `_add_mt_and_llm_matches` и, вероятно, чекбокс с его настройкой); (в) видимый LLM-путь Custom —
  QuickTrans (чип CUS, был и раньше из 8 чипов; после 9.3c — единственный).
  **Решение Дмитрия (2026-10-13):** панель Translation Results в интерфейсе нигде не видна →
  кластер включается в кандидаты **8.18**: `_add_mt_and_llm_matches`,
  `_REMOVED_add_mt_and_llm_matches_progressive`, чекбокс «Enable LLM (AI) matching on segment
  selection» + ключ `enable_llm_matching` в settings, `pass`-блок в prefetch. (История: кластер
  осиротел до начала нашей работы — в baseline 13bd37fb progressive уже был заглушкой, живых
  вызовов `_add_mt_and_llm_matches` не было; чекбокс был инертен уже в baseline.)
  (3) Затенение QMessageBox локальным импортом в translate_batch (бюджет-блок) — давний
  латентный паттерн; в этом методе закрыт квалифицированным импортом; те же паттерны в
  create_termbases_tab/_show_edit_terms_dialog/_create_ai_settings_tab — **не трогались**
  (UI-зоны/чужие очереди; отметить для 8.18).
  (4) py_compile/справочный счётчик: при сравнении батов учитывать рост от аудит-скриптов
  (правило 8.13 соблюдено, канонический счётчик 110 неизменен).
  (5) heredoc-правки в Git Bash на этой машине съедают уровень бэкслэшей — правки только через
  файловые скрипты (перенесено в практику).
- **Не покрыто**: реальный llama-server (сценарии §6 — ручные); страницы Settings вне AI
  (не задеты); чтение/запись .svproj (провайдер там не хранится — подтверждено R9 §2.7).
- **Имена, удаляемые только после 9.4** (grep-гейт считает их разрешёнными остатками):
  - llm_clients: `set_ollama_timeout`, `_ollama_timeout_override`, `MISTRAL_MODELS`,
    `CLAUDE_MODELS`, `OLLAMA_MODELS`, `OPENROUTER_MODELS`, блоки `ollama_endpoint`/google→gemini
    в `load_api_keys` (пинг-кластер читает OLLAMA_ENDPOINT);
  - монолит: `_update_llm_indicator` (ветки провайдеров), keepwarm-кластер (5 методов),
    `_apply_gemini_proxy` (зовётся из Save), show_about (текст), страница AI Settings
    (радио/комбо/Ollama-секция/API-ключи) + `_save_ai_settings_from_ui` (пишет облачные
    *_model-ключи и llm_*-флаги), QuickTrans-таб LLM-часть (mtql_* чекбоксы/поля);
  - chat_view: `_show_model_menu`/`_on_model_selected` (список 6 провайдеров, mistral/openrouter
    base_url, legacy-путь ручного клиента);
  - llm_pricing: `_FREE_PROVIDERS = ("ollama",)` (влияния на custom нет; правка — 9.4);
  - superlookup.py TODO-коммент о MT-провайдерах (docs-проход).

## §8 Вопросы к Дмитрию

1. **QuickTrans-таб (LLM-часть) — как представить единственный провайдер (обязательно).**
   Сейчас в табе QuickTrans LLM-блок остался от 8 провайдеров: чекбоксы mtql_claude/mtql_openai/
   mtql_gemini/mtql_mistral/mtql_deepseek/mtql_openrouter/mtql_ollama/mtql_custom_openai + поля
   моделей; после 9.3 создают чип только mtql_custom_openai («Custom», код CUS). Предложение для
   9.4 (вариант (a), рекомендую): оставить ОДИН чекбокс «Custom (OpenAI-Compatible API)» с полем
   модели активного профиля (read-only отображение из профиля) — таб показывает фактически
   существующую сущность; «Local LLM» отдельно не показывать, т.к. после удаления Ollama
   локальный сервер — это просто Custom-профиль с localhost-endpoint (согласуется с R9:
   страница Local LLM временно на коде Custom). Вариант (b): чекбокс + серая пометка «(локальный
   сервер настраивается как Custom-профиль)» — чуть больше текста, меньше правок в подсказках.
   Вариант (c): вообще убрать LLM-блок из таба, оставить только custom MT — не рекомендую:
   теряется возможность быстро включать/выключать LLM-чип.
2. **Чип «Local LLM» в QuickTrans**: показывать ли отдельный чип для custom-профиля с
   localhost-endpoint (например, «Local (имя профиля)», код LOC) или единый CUS для всех?
   Рекомендация: единый CUS в 9.4; разделение — не раньше 9.5 (нужен признак «локальный» в
   профиле — можно вместе с vision-галкой 9.5).
3. **Статус-бар**: после 9.4 оставить вид «🔌 {профиль}: {модель}» (текущий custom-формат) —
   рекомендую да; ветки иконок остальных провайдеров удалить.
4. **pyflakes −14**: подтверди, что снижение за счёт удалённого кода принимается как новая база
   (следующие батчи сравниваются с 562/126/4).

## §9 Handover

- **9.4 (UI)**: страница AI Settings (радио/комбо/Ollama-секция/API-ключи/keepwarm и их настройки),
  страница Local LLM (временно код Custom + пометка), QuickTrans-таб LLM-часть (§8.1),
  статус-бар `_update_llm_indicator`, chat_view меню моделей (тогда же удалить
  MISTRAL/CLAUDE/OLLAMA/OPENROUTER_MODELS и set_ollama_timeout из llm_clients), текст show_about,
  llm_pricing `_FREE_PROVIDERS`, api_keys.example.txt (docs-проход), тексты help.
- **9.5**: vision-галка «модель поддерживает vision» в Custom-профиле (механизм вместо пустого
  VISION_MODELS; Image Extractor/AutoPrompt оживут автоматически — ветки уже на base64-PNG).
- **8.18**: мёртвые методы (в т.ч. `_REMOVED_add_mt_and_llm_matches_progressive` — теперь единственный
  носитель старых провайдерных строк в монолите; `_save_llm_settings_from_ui` — не оживлять!).
- Очерёдность 9.4/9.5/8.18/8.16/8.17 — решение координатора; 9.4 стартует только по команде
  с промптом.

## §10 Результаты ручных тестов и ответы Дмитрия (2026-10-13)

**Тесты (тестовая сборка, локальный llama):**

| Сценарий | Вердикт |
|---|---|
| T9.3.1 миграция provider openai/claude/ollama → старт, статус-бар Custom, Save | ПОТВЕРЖДЕНО |
| T9.3.2 Ctrl+T через локальный llama, модель = модель профиля | ПОТВЕРЖДЕНО |
| T9.3.3 пакетный перевод, модель профиля (дефект «custom-model» устранён) | ПОТВЕРЖДЕНО |
| T9.3.4 | снят (2026-10-13, см. §7 находка 2b — нет UI-проявления) |
| T9.3.5 Proofread 3–5 сегментов | ПОТВЕРЖДЕНО |
| T9.3.6 Chat/AI Assistant | ПОТВЕРЖДЕНО |
| T9.3.7 QuickTrans, чип CUS | ПОТВЕРЖДЕНО |
| T9.3.8 Token Usage & Cost (новые custom_openai, история цела) | ПОТВЕРЖДЕНО |
| T9.3.9 «не настроено» без профилей | **маркера вердикта в сообщении нет — уточнить** |
| T9.3.10 Image Extractor «Vision … not enabled yet» | ПОТВЕРЖДЕНО |
| T9.3.11 Общий smoke | ПОТВЕРЖДЕНО |

**Ответы на вопросы §8:**

1. **QuickTrans-таб (LLM-часть):** вариант (a) — ОДИН чекбокс «Custom (OpenAI-Compatible API)»
   с read-only полем модели активного профиля; «Local LLM» отдельно не показывать.
   **ДОПОЛНЕНИЕ Дмитрия: рассмотреть возможность добавить выбор профиля по аналогии с
   Custom (OpenAI-Compatible) Setting в AI Settings** — включить в рекогносцировку/план 9.4.
2. **Чип «Local LLM»:** по рекомендации — единый CUS в 9.4; разделение не раньше 9.5.
3. **Статус-бар:** по рекомендации — вид «🔌 {профиль}: {модель}», ветки остальных провайдеров удалить.
4. **pyflakes −14:** ПОТВЕРЖДЕНО — новая база 562/126/4 для последующих батчей.
