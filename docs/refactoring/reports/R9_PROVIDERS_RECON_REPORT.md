# ОТЧЁТ R9 — Разведка: консолидация провайдеров (ТОЛЬКО ЧТЕНИЕ)

**Дата:** 2026-10-11 · **База:** HEAD `bdff36df` (код `4ed6eba4`, Batch #8.15) · **Режим:** рекон,
код не тронут. Написаны только этот отчёт и скрипты/артефакты `docs/refactoring/audits/r9_*`.
**Изоляция:** все пробы — в изо-профилях `D:\Temp\SupervertalerPortable\analysis\r9\iso-*`
(offscreen; USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP перенаправлены; указатель
`config.json` → локальный user_data; реальных данных Дмитрия не касались; сети не было).
Таймауты: отдельные операции пробы ограничены; сам старт приложения ~2 мин (допущение по
AGENTS.md «не убивать раньше ~3 мин»); каждая проба завершается `os._exit(0)`, остатков нет.

**Решение Дмитрия (контекст):** удалить ВСЕ жёстко зашитые облачные провайдеры (OpenAI,
Anthropic, Google/Gemini, Mistral, DeepSeek, OpenRouter) и страницу Machine Translation
Providers. Остаются: (1) «Custom (OpenAI-Compatible API)» с профилями — универсальный
провайдер; (2) страница «Local LLM» на коде Custom (без Ollama); (3) QuickTrans: MT — только
custom MT endpoint; AI/LLM — Local LLM + Custom.

---

## ЧАСТЬ 1 — Баг профилей Custom (приоритет)

### 1.1 Все места чтения/записи четырёх ключей

Читатели/писатели ключей `custom_openai_profiles`, `custom_openai_active_profile`,
`custom_openai_endpoint`, `custom_openai_model` (монолит 56 524 строки):

| Где | Строки | Роль |
|---|---|---|
| `SupervertalerQt._create_ai_settings_tab` | 19363 (таб), **19365** `settings = self.load_llm_settings()` — ЛОКАЛЬНЫЙ СНАПШОТ | комбо профилей 19656–19667; поля 19688–19723; заполнение из профиля 19726–19743; синх полей→снапшот 19745–19757 |
| там же, `_add_custom_profile` | **19760–19779** | append в **снапшот** `settings['custom_openai_profiles']` + combo.addItem |
| там же, `_remove_custom_profile` | **19784–19801** | pop из **снапшота** + combo.removeItem |
| `SupervertalerQt._save_ai_settings_from_ui` | **23812–24004**; ключевые: 23859 `existing_settings = self.load_llm_settings()` (ПЕРЕЧИТЫВАЕТ ДИСК), 23860 `profiles = existing_settings.get(...)`, 23866–23869 sync полей только тек. idx (гард `0 <= idx < len(profiles)`), 23870 `active_profile_name = combo.currentText()`, 23889–23892 запись (в т.ч. legacy-плоские поля) | ЕДИНСТВЕННЫЙ писатель на диск |
| `SupervertalerQt._get_active_custom_profile` | 48343–48370 | читатель движка: профиль по имени → profiles[0] → legacy-плоские поля |
| `SupervertalerQt._save_llm_settings_from_ui` | 23730–23810 | **МЁРТВЫЙ** (0 вызывающих; кандидат 8.18) |
| `SupervertalerQt.create_llm_client` | 48487–48511 (custom: 48494–48507) | фабрика: base_url+model+key из активного профиля |
| `_resolve_provider_model` | 7582–7597 | модель = активный профиль (плоское поле устарело, задокументировано) |
| `_update_llm_indicator` | 7599–7644 | статус-бар: имя профиля + модель |
| `_fetch_llm_translation_async` | 51616–51742 (custom: 51637–51646) | Match Panel LLM |
| `translate_current_segment` | 49534–49542 | одиночный перевод |
| `translate_batch` | 50875–51465 (custom: 51003, 51151, 51462–51465 — дублирует фабрику) | пакетный |
| `run_grid_quicklauncher_prompt`, `autotag_*`, `_run_proofreading` | 50432–50467, 50106–50114, 50703–50723, 39813–39817 | прочие потребители |
| QuickTrans MT-квик-сеттингс | 20886–20905 | читает legacy `custom_openai_model` как fallback отображения |
| `modules/settings_service.py` | 228–266 (load), в т.ч. авто-миграция 255–263; 268–275 (save) | единый файл `<user_data>/workbench/settings/settings.json`, секция `ui.llm_settings` |
| `modules/quicktrans.py` | 414–470 | ключ опционален; клиент через `create_llm_client` |
| `modules/chat_backend.py` | 127–147 | ключ опционален; клиент через фабрику |

Структура, которую **пишет** UI (сохранение): `ui.llm_settings.custom_openai_profiles = [{name,
endpoint, model, api_key}, …]` + `custom_openai_active_profile = <имя из комбо>` + legacy-зеркала
`custom_openai_endpoint`/`custom_openai_model` = значения видимых полей.
Структура, которую **читает** движок: то же самое через `_get_active_custom_profile` — совпадает;
расхождение не в формате, а в том, КАКОЙ список попадает на диск (см. 1.4).

### 1.2 Воспроизведение (проба, изо-профили)

Скрипт: `docs/refactoring/audits/r9_probe_profiles.py` (+ `r9_seed_profiles.py`), логи
`r9_log_{a,ctrl,rm}.txt`. Виджеты настоящей вкладки «🤖 AI Settings»
(`win._create_ai_settings_tab()`), нажатия настоящих кнопок «+»/«−»/«💾 Save AI Settings»,
`QInputDialog.getText` → «Local», `QMessageBox` нейтрализованы.

**Сценарий `a` (сид: 1 профиль «Custom Endpoint», как у Дмитрия):** «+» → «Local», поля
endpoint/model заполнены, Save. Файл после:
`profiles=[{"name":"Custom Endpoint",…}]`, `active_profile='Local'`, плоские поля =
введённые значения. **Вердикт: `bug reproduced=True`** — форма файла 1:1 как у Дмитрия.

**Фаза `d` (тот же сломанный файл, свежая вкладка):** комбо показывает только «Custom Endpoint»
(активное имя «Local» не найдено → выбор остаётся на 0), движок молча использует profiles[0]
(`_get_active_custom_profile` fallback 48361–48362), статус-бар «🔌 Custom Endpoint:
Qwen3.8-27B…». Падений нет; расхождение «файл говорит Local, всё остальное показывает Custom
Endpoint» — до следующего пересохранения.

**Контроль `ctrl` (сид: 2 профиля A/B):** переключение комбо + правка поля + Save — оба профиля
целы, активный корректен. **Переключение между СУЩЕСТВУЮЩИМИ профилями работает.**

**Сценарий `rm` (сид: 2 профиля, удалён «Profile A», Save):** файл после — `["Profile A",
"Profile B"]`, причём **«Profile A» воскрешён с полями «Profile B»**
(`endpoint=…2222/v1`, `model=model-b` у обеих записей): тихая ПОРЧА данных, а не просто no-op.

**Фаза `c` (гипотеза 5):** `LLMClient(base_url='127.0.0.1:3445/v1')` конструируется без ошибок —
валидации схемы нет нигде (`create_llm_client` 48506 передаёт `profile.get('endpoint')` как есть;
`LLMClient.__init__` 565 → `client_kwargs["base_url"]` 913; `call_custom_mt._clean` 48411–48412
чистит только управляющие символы). Ошибка всплывёт только на самом запросе. Отдельно
зафиксировано: **в dev-runtime `E:\Dev\python-embed` пакет `openai` не установлен**
(`ModuleNotFoundError`) — SDK-зависимость ленивая (import внутри `_call_openai_with_usage` 904);
для сравнимости тестов на тестовой сборке это надо учитывать.

**Проверка гипотез из промпта:**
1. «Сохранение пересобирает список из видимых полей/комбобокса» — НЕТ, наоборот: сохранение
   пересобирает список **с диска**, отбрасывая изменения сессии; комбо отдаёт только имя
   активного профиля. Механизм зеркальный гипотезе, но в той же зоне.
2. «Профиль пишется в другой ключ/секцию» — НЕТ (одна секция `ui.llm_settings`, проверено).
3. «Rename/delete/активный не синхронизированы» — **ДА, корень бага** (см. 1.4).
4. «Читатель использует legacy-плоские поля» — НЕТ для основного пути (профили приоритетны);
   плоские поля живут как fallback (48364–48368) и как зеркало при записи (23889–23890).
5. «Endpoint без схемы не нормализуется» — **ДА, но отдельная дыра**, к потере профиля не
   относится (фаза `c`).

### 1.3 Точная причина (file:line)

**Два источника истины для списка профилей.** В течение сессии диалога список живёт в
ЛОКАЛЬНОМ снапшоте `_create_ai_settings_tab` (`settings = self.load_llm_settings()`, 19365),
который мутируют `_add_custom_profile` (19776) и `_remove_custom_profile` (19799). При
сохранении `_save_ai_settings_from_ui` **выбрасывает снапшот** и перечитывает диск:
23859–23860. Дальше:
- **Add:** новый профиль есть только в комбо/снапшоте. На диске его нет → sync полей
  пропускается (гард 23866: `idx=1 < len(disk)=1` false), в файл уходит список с диска
  (23891), а `custom_openai_active_profile` = `combo.currentText()` = «Local» (23870).
  Профиль потерян, активное имя висит. — Полностью совпадает с файлом Дмитрия.
- **Remove:** удаление было только в снапшоте; на диске профиль остаётся (воскрешение);
  sync полей (23867–23869) пишет значения ТЕКУЩИХ видимых полей (уже другого профиля) в
  disk-элемент по индексу комбо → перезаписывает поля выжившего профиля. — Воспроизведено.

### 1.4 Минимальный фикс (ОПИСАНО, НЕ ДЕЛАТЬ — коммит 9.1)

Однострочная суть: **при сохранении брать список профилей из того же снапшота, которым
диалог живёт всю сессию**, а не перечитывать диск.

1. `_save_ai_settings_from_ui` — новый опциональный параметр
   `custom_profiles_snapshot=None` (по образцу существующих опциональных параметров 23821+);
   кнопка Save (20413–20436) передаёт локальный `settings` из `_create_ai_settings_tab`.
2. В теле: `profiles = (custom_profiles_snapshot or existing_settings).get('custom_openai_profiles', [])`
   вместо 23860; sync текущего idx оставить (теперь он согласован со снапшотом).
3. Самолечение dangling-имени: `active_profile_name = combo.currentText()`; если этого имени
   нет в `profiles`, взять имя `profiles[0]` (или оставить пусто при пустом списке) — тогда
   файл никогда не остаётся с несуществующим активным именем.
4. Плоские зеркала 23889–23890 писать из АКТИВНОГО профиля списка (а не из видимых полей),
   чтобы `custom_openai_endpoint/model` перестали расходиться с профилями.
5. (Опционально, тот же коммит) нормализация схемы endpoint при сохранении: если значение
   не начинается с `http://`/`https://` — дополнить `http://` и показать это в поле (закрывает
   гипотезу 5 для будущих вводов; существующий schemeless-пример Дмитрия в плоском поле —
   инертен, но при миграции 9.3 учесть).

Объём: ~+12/−6 строк в монолите, один коммит. Риск минимален: путь «переключение между
существующими» не меняется (контроль `ctrl` остаётся зелёным), меняются только ветки
add/remove/dangling.

**Риск для существующих файлов настроек:** чтение сломанного файла (active ∉ profiles)
безопасно и сегодня — `_get_active_custom_profile` откатывается к profiles[0] (фаза `d`),
падений нет. После фикса первое же сохранение из UI перепишет активное имя на существующий
профиль (самолечение). Файлы, где пользователь правил JSON руками (как Дмитрия), сохраняются
как есть; профиль с полями `endpoint` без схемы запросом не является — рекомендация в 9.3:
при миграции провайдера нормализовать схему и логировать.

---

## ЧАСТЬ 2 — Инвентарь провайдеров

Полные данные: `docs/refactoring/audits/r9_provider_inventory.py` → JSON
`D:\Temp\SupervertalerPortable\analysis\r9\r9_provider_inventory.json` (семья → файл →
владелец-метод → строки). Ниже — сводка с классификацией.

### 2.1 Монолит Supervertaler.py — по семьям (попаданий строк / владельцев)

| Семья | Строк/владельцев | Ключевые зоны (владельцы) | Вердикт |
|---|---|---|---|
| openai | 187 / 30 | AI-таб 19397+ (54); `_save_ai_settings_from_ui`; `PreTranslationWorker._translate_*` (4 метода, ветки api_key); `translate_batch`/`translate_current_segment`/`_fetch_llm_translation_async`; `create_llm_client`; `_add_mt_and_llm_matches` (17); автотег; proofread; мёртвые: `_REMOVED_add_mt_and_llm_matches_progressive` (12), `_save_llm_settings_from_ui` (8) | удалить ветки/UI; `openai` SDK-имя остаётся (custom_openai ходит через `_call_openai_with_usage`) |
| claude | 110 / 20 | AI-таб (46); `_add_mt_and_llm_matches` (11); PreTranslationWorker (4); Image Extractor `_build_image_extract_ai_callback` (2); индикатор; save-методы | удалить |
| gemini | 123 / 25 | AI-таб (42); `_add_mt_and_llm_matches` (16); PreTranslationWorker; `_apply_gemini_proxy` 48330–48341 (env-прокси); `_save_api_keys_from_ui` 24006–24017; vision-ветки Image Extractor 10035+ | удалить; `_apply_gemini_proxy` — целиком |
| mistral | 47 / 5 | AI-таб (35); QuickTrans-таб (4); save (6) | удалить |
| deepseek | 41 / 5 | AI-таб (32); QuickTrans-таб (3); save (4) | удалить |
| openrouter | 44 / 6 | AI-таб (32); save (6); `create_llm_client` base_url (48492–48493); PreTranslationWorker (2) | удалить |
| ollama | 179 / 20 | AI-таб (71); keepwarm-система `_setup_ollama_keepwarm`/`_ping_ollama_keepwarm`/`_start|_stop_…_timer` 7646–7719; `_apply_ollama_timeout_setting` 7657–7666; `translate_current_segment` прогресс-диалог Local LLM 49576–49700; `translate_batch` 51148+; QuickTrans-таб (17); save (22); `show_about` 49306 | удалить Ollama-путь целиком; страница Local LLM переезжает на Custom-код (см. 9.4) |
| custom_openai | 63 / 19 | профили (19645–19840), фабрика 48487, ридер 48343, все потребители | **ОСТАВИТЬ** — целевая архитектура |
| custom_mt | 85 / 5 | QuickTrans-таб 20628–20651 (66), `_get_custom_mt_profiles`/`_get_active_custom_mt_profile` 48372–48392, `call_custom_mt` 48394–48485, `_save_mt_quick_lookup_settings` 20964+ | **ОСТАВИТЬ** |
| google_mt | 38 / 11 | `_fetch_mt_translation_async` (8), `call_google_translate` 51869–51922, `PreTranslationWorker._translate_with_mt`, `_add_mt_and_llm_matches`, MT-таб, `translate_batch` 50944+ | удалить |
| mt_deepl / mt_msft / mt_amazon / mt_modernmt / mt_mymemory | 33/22/34/28/39 | те же зоны + `call_deepl` 51924–51996 (`import deepl` 51927), `call_microsoft_translate` 51998–52053, `call_amazon_translate` 52055–52110 (`import boto3` 52058), `call_modernmt` 52112–52162, `call_mymemory` 52164–52213 | удалить |

Отдельно: `_REMOVED_add_mt_and_llm_matches_progressive` (52970–53243, 274 строки) и
`_save_llm_settings_from_ui` (23730–23810, 81 строка) — уже мёртвые методы с провайдерными
ветками; НЕ удалять в 9.x (чужая очередь 8.18), только учесть, что grep-защиты по
идентификаторам провайдеров будут давать по ним попадания.

### 2.2 modules/* — по файлам

| Файл | Что там по провайдерам | Вердикт |
|---|---|---|
| `llm_clients.py` (2000) | см. 2.3 | перестроить |
| `quicktrans.py` | MT-дефы 334–339 (`call_*` по имени), LLM-дефы 395–470 (claude/openai/gemini/mistral/deepseek/openrouter/ollama/custom + `_call_llm_translation`), custom MT 369–380 | MT → только custom MT; LLM → только Local LLM + Custom |
| `settings_service.py` | дефолты llm_settings 230–246; авто-миграция плоского конфига 255–263; `provider_enabled_states` 340–353 (`llm_*` + `mt_*`); api_keys (378–391, миграция google→gemini) | адаптировать: дефолты/миграция провайдера; `llm_custom_openai` остаётся |
| `chat_backend.py` | дефолт-вывод провайдера по ключам openai/claude/gemini 112–117; keyless для custom/ollama 127–130; фабрика | адаптировать: дефолт → custom_openai |
| `chat_view_widget.py` | keyless-проверки 628–639 | адаптировать (ollama убрать) |
| `workers/proofread.py` | ветки api_key по 8 провайдерам 88–96 | редуцировать до custom_openai (+локальный) |
| `local_llm_setup.py` | Ollama: `LocalLLMStatusWidget`, `check_ollama_status`, `RECOMMENDED_MODELS`, `LocalLLMSetupDialog` (13 владельцев, 88 строк упоминаний) | удалить Ollama-код; страница Local LLM переезжает на Custom (виджет llama-server — НЕ в объёме) |
| `llm_pricing.py` | цены по провайдерам/моделям (pricing.json), `_FREE_PROVIDERS = ("ollama",)` | оставить как счётчик (вопрос Д.2); ollama-строку убрать |
| `usage_log.py` | запись provider/model в ledger | оставить (историч. записи инертны) |
| `usage_report_dialog.py` | отображение стоимости | оставить (вопрос Д.2) |
| `translation_results_panel.py` | коды MT/LLM-провайдеров GT/DL/MS/AT/MMT/MM, CL/GPT/GEM/… | редуцировать: CUS (+локальный) в LLM; custom MT в MT |
| `unified_prompt_manager_qt.py` | vision-анализ фигур: выбор провайдера по `llm_client.provider` 4456+, форматы изображений 4478–4485, оценка стоимости 4500–4514 | адаптировать на custom_openai; относится к G5-зоне — аккуратно |
| `pdf_rescue_Qt.py` | СВОИ клиенты OpenAI/Claude/Gemini (init_clients 64+, 71 попаданий) | удалить облачные ветки; модуль в целом — вне 9.x (отдельный кандидат, решить в 8.18/отдельно) |
| `superlookup.py` | TODO-комментарий про MT-провайдеров (237), список 54 | оставить/почистить коммент в docs-батче |
| `platform_helpers.py`, `help_system.py`, `chat_message_delegate.py`, `autocorrect.py`, `ai_actions.py` | по 1 попаданию (иконка/справка/делегат) | почистить в проходе 9.4 |
| `quicktrans.py` custom MT | `call_custom_mt` через parent_app | **оставить** |

### 2.3 llm_clients.py — структура (2000 строк)

| Блок | Строки | custom_openai нужен? |
|---|---|---|
| `load_api_keys` (unified settings.json + legacy api_keys.txt + указатель) | 43–138 | ДА (fallback ключа) |
| ollama-хелперы (`set_ollama_timeout`, `_resolve_ollama_timeout`, `_sanitize_ollama_endpoint`) | 139–183 | НЕТ |
| `LLMConfig` | 184–190 | ДА |
| `LLMClient.DEFAULT_MODELS` (8 провайдеров) | 198–208 | сократить до `custom_openai` |
| `MISTRAL_MODELS`, `DEEPSEEK_MODELS`, `CLAUDE_MODELS`, `OPENAI_MODELS`, `GEMINI_MODELS`, `OLLAMA_MODELS` | 210–425+ | НЕТ (кроме возможного списка-примера для custom) |
| `get_claude_model_info`, `get_ollama_model_info`, `check_ollama_status` | 432–533 | НЕТ |
| `VISION_MODELS` + `model_supports_vision` | 374–431, 534–547 | АДАПТИРОВАТЬ: после удаления облаков whitelist пуст → vision для custom отключён (уже так); решение по 9.1-BACKLOG (pattern/checkbox) — отдельный шаг |
| `__init__` (default base_url для mistral/deepseek/openrouter 576–585) | 549–589 | удалить ветки |
| `_clean_translation_response`, `_remove_prompt_patterns`, `_get_temperature` | 590–782 | ДА (общие) |
| `translate` → `translate_with_usage` (диспетчер 862–871) | 783–892 | оставить ОДНУ ветку: openai-совместимую (`custom_openai`) |
| `_call_openai_with_usage` (SDK `openai`, base_url, vision, кэш-цены) | 893–1008 | **ДА — ядро** (это и есть путь custom_openai) |
| `_call_claude_with_usage` / `_call_gemini_with_usage` | 1009–1180 | НЕТ |
| legacy `_call_openai`/`_call_claude`/`_call_gemini`/`_call_gemini_rest` (без usage) | 1181–1576 | НЕТ (проверить вызывающих перед удалением — вероятно, только legacy-хелперы) |
| `_call_ollama` (requests; images НЕТ — 8.15-констатация) | 1577–1759 | НЕТ |
| `main` + модульные `get_openai_translation`/`get_claude_translation`/`get_google_translation` | 1760–2000 | НЕТ (CLI-хелперы; `get_google_translation` — Google MT REST) |

Общие хелперы, которые НЕ трогать: `load_api_keys`, `_clean_translation_response`/
`_remove_prompt_patterns`, `usage_log.record`-интеграция в `translate_with_usage`, формат
(usage_dict) — потребители (proofread, chat, quicktrans, prompt manager) зависят от сигнатур.

### 2.4 Страницы настроек и виджеты

- **AI Settings** (`_create_ai_settings_tab` 19363–20437, 1075 строк): радио 8 провайдеров,
  комбо моделей (openai/claude/gemini/mistral/deepseek/openrouter), Ollama-секция
  (19427–19643 + Advanced 20075+ + keepwarm), **Custom-секция с профилями (19645–19840)**,
  API-ключи LLM (19920+), enable-чекбоксы. Удаляется всё, кроме Custom-секции (+General-часть).
- **MT Settings** (`_create_mt_settings_tab` 20439–20549, ~111 строк): чекбоксы 6 MT-провайдеров
  + MT API-ключи (20499–20507) + save `_save_mt_settings_from_ui` 24019–24038. **Удаляется
  страница целиком** (решение Д.), пункт меню/сайдбара 19094.
- **QuickTrans** (`_create_mt_quick_lookup_settings_tab` 20559–20940): MT-часть (20597–20602 +
  custom MT-профили 20628–20651) и LLM-часть (20800–20905). Редукция: MT — только custom MT;
  LLM — только Local LLM + Custom.
- **API-ключи:** хранятся в settings.json секция `api_keys` (settings_service 378–391;
  `api_keys.txt` — legacy-миграция only). UI: блок в AI-табе 19920+ + MT-поля 20499–20507.
- **Local LLM:** сейчас = Ollama-радио в AI-табе + `modules/local_llm_setup.py` (виджет статуса,
  диалог установки, RECOMMENDED_MODELS). По решению Д.: страница остаётся, код — Custom,
  виджет llama-server — НЕ в объёме.

### 2.5 MT-провайдеры: вызовы и custom MT

Единственный диспетчер MT: `_fetch_mt_translation_async` (51744–51867) — приоритет
Google>DeepL>Microsoft>Amazon>ModernMT>MyMemory по ключам из `api_keys` + enable-флагам;
используется Match Panel (`_add_mt_and_llm_matches`/assist). Вторые точки:
`translate_batch` (выбор MT-провайдера в диалоге пакетного перевода 50940–50990),
`PreTranslationWorker._translate_with_mt` (5571–5592 — предперевод, сейчас только Google),
QuickTrans (quicktrans.py 334–380). Все 6 `call_*` (51869–52213, ~340 строк) — чистый
requests/deepl/boto3, других потребителей нет.
**Custom MT:** профили `custom_mt_profiles`+`custom_mt_active_profile` (отдельная секция,
не зависит от AI-профилей), `call_custom_mt` (48394–48485) через LLMClient(custom_openai) с
raw_mode; UI в QuickTrans-табе. Остаточное состояние после 9.2: MT = только custom MT.

### 2.6 Потребители выбора провайдера

| Потребитель | Как выбирает | Что после 9.x |
|---|---|---|
| `translate_current_segment` 49508–49964 | `settings['provider']` → ветки, ollama-диалог, custom-профиль 49536–49542 | один путь custom_openai |
| `PreTranslationWorker` (`_translate_with_llm` 5594+, batch 5659+, single 5878+, autotag 5925+) | provider+ключи через аргументы | custom_openai + base_url из профиля |
| `translate_batch` 50782–51614 | диалог выбора; ветки MT и LLM | LLM: custom; MT: custom MT |
| Chat (`chat_backend.py`) | дефолт по ключам → фабрика | дефолт custom_openai |
| Proofread (`show_proofread_dialog` 39594 + `workers/proofread.py`) | provider-параметр | custom_openai |
| Prompt manager / фигуры (`unified_prompt_manager_qt.py` 4456+) | `llm_client.provider` + whitelist vision | custom_openai; vision — отдельный шаг (G5-смежное) |
| Image Extractor (`_build_image_extract_ai_callback` 9988–10196) | ветки openai/claude/gemini | custom_openai (смежно G5) |
| QuickTrans (quicktrans.py 334–470) | enable-флаги `mtql_*` + ключи | MT: custom MT; LLM: Local LLM + Custom |
| Token Usage & Cost (`usage_log`, `usage_report_dialog`, `llm_pricing`; меню 8532–8544) | ledger-записи provider/model + pricing.json | оставить (вопрос Д.1) |
| Статус-бар (`_update_llm_indicator` 7599–7644) | provider+модель/профиль | упростить до custom |

### 2.7 Персистентность и совместимость со старыми данными

- **settings.json** (`ui.llm_settings.provider`): единственное место хранения выбора.
  **Точка безопасной подмены — `SettingsService.load_llm_settings` (settings_service.py:228)**:
  после загрузки `if provider not in ('custom_openai',): provider='custom_openai'` (молча),
  плюс перенос плоского legacy-конфига в профиль (шаблон уже есть на 255–263; дополнить
  нормализацией схемы endpoint). Все читатели идут через `self.load_llm_settings()`
  (проверено: монолит, quicktrans, chat_backend через parent_app) — второго обхода нет.
- **Ключи** (`api_keys`-секция): ключи удалённых провайдеров остаются в файле инертными
  (подтверждено: читатели — только ветки удаляемых `call_*`/клиентов). Ничего не удалять.
- **.svproj**: провайдер/модель НЕ сохраняются (проверено `save_project_to_file` 29114+,
  `modules/models.py` — полей provider нет). Старые проекты не содержат провайдерных данных.
- **TM-метаданные/БД**: полей provider нет (tm_metadata_manager 659 и database_manager 473 —
  только докстринги про Trados).
- **Prompt library**: провайдер-специфичных полей нет (тексты промптов нейтральны).
- **usage ledger** (`workbench/usage/…`): исторические записи с provider=openai/claude/…
  остаются; `usage_report_dialog`/`llm_pricing` продолжат показывать их стоимости
  (pricing.json сохраняется) — аргумент к вопросу Д.1.

### 2.8 Зависимости (pip) — только список для P2, ничего не менять

- `requirements.txt`: `openai>=1.0.0` — **ОСТАЁТСЯ** (custom_openai работает через SDK
  `openai` с base_url, `_call_openai_with_usage` 904); `anthropic>=0.7.0`,
  `google-generativeai>=0.3.0`, `boto3>=1.28.0`, `deepl>=1.15.0` — станут не нужны.
  `requests` — остаётся (custom MT/QuickTrans/ollama? — ollama уходит, requests всё равно
  нужен для Google MT… тоже уходит; но requests нужен `unified_prompt_manager`/`pdf_rescue`?
  — минимум для тех компонентов, что остаются; решать в P2 по факту).
- В **dev-runtime** `E:\Dev\python-embed` из этого списка нет НИ ОДНОГО SDK (есть только
  `requests 2.34.2`; `openai` отсутствует — фаза `c` пробы). Тестовая сборка: сверить при
  сборке (для custom_openai нужен `openai`!).
- Удаление пакетов — P2 (чистая установка embed = тест, как договорено в 8.12).

### 2.9 Тесты/пробы с провайдерными ссылками

- `docs/refactoring/audits/batch8-13_code_tools_smoke.py` — каноническая smoke-таблица
  (42 пункта) содержит `Tools/Token-Usage-Costs` (140) — остаётся валидной; пункты,
  открывающие AI Settings/MT Settings, после 9.x проверяют редуцированные страницы.
- `batch8-15_probe_e03.py` — LLMClient vision (custom_openai/openai/claude/gemini) — после
  9.3 списки VISION_MODELS изменятся; проба историческая, не трогать, для новых прогонов
  делать r9-версию.
- `batch8-12_dep_scan.py` / `batch8-12_code_protection2_grep.py` — сканируют deps/защиты;
  провайдерных хардов не содержат (grep пуст).
- `batch8-15_probe_m/seed_m.py` — `mt_mymemory` (MyMemory default OFF) — ключ уйдёт вместе
  с MT-страницей; пробы исторические.

---

## ЧАСТЬ 3 — План под-батчей 9.x (предложение)

Порядок по промпту: **9.1 профили Custom → 9.2 MT → 9.3 облачные LLM + Ollama →
9.4 Settings/QuickTrans/селекторы/Token Usage → совместимость со старыми настройками**.
Предлагаю совместимость встроить в 9.3 (миграция provider — там, где удаляются ветки;
одно место — `load_llm_settings`), vision-ремонт custom (BACKLOG 9.1) — отдельным 9.5.

Каждый под-батч: старт только по команде Дмитрия + промпт; защиты §4.1 обязательны:
AST startup-chain (инстанцирование приложения offscreen в изо-профиле), grep удалённых
идентификаторов по всем формам (учесть мёртвые `_REMOVED_…`/`_save_llm_settings_from_ui` —
давают фоновые попадания, зафиксировать дельту), pyflakes undefined-набор (монолит вне
tmx_editor), offscreen-пробы (в т.ч. перевод через локальный фейк-endpoint на 127.0.0.1 —
loopback, без сети), EOL-дисциплина, sha256-снапшоты зон, `«Не пушить»`.

### 9.1 — Починка профилей Custom (первый, отдельный коммит)
- Зона: `_save_ai_settings_from_ui` 23858–23896 + вызов Save 20413–20436 (+опц.
  нормализация схемы 19751–19753). Ожидаемо ~+12/−6.
- Риски: почти нулевые (ветки add/remove раньше молча портили данные).
- T9.1: (а) add+save — профиль сохраняется, активное имя валидно; (б) remove+save —
  удалённый не воскресает, поля выживших не портятся; (в) переключение существующих —
  как в контроле `ctrl`; (г) файл с dangling-именем — загружается, сохранение самолечит;
  (д) endpoint без схемы — нормализуется при сохранении.

### 9.2 — MT: оставить только custom MT
- Зоны: страница MT Settings 20439–20549 + пункт 19094 + `_save_mt_settings_from_ui`
  24019–24038; шесть `call_*` 51869–52213 (~340); `_fetch_mt_translation_async` → вариант
  «только custom MT» (51744–51867); MT-блок диалога `translate_batch` 50940–50990;
  `PreTranslationWorker._translate_with_mt` 5571–5592; MT-часть `_add_mt_and_llm_matches`
  53245–53432 (+`_clean_provider_prefix` оставить для LLM-кодов); QuickTrans MT-дефы
  (quicktrans.py 334–380); коды панели `translation_results_panel.py`; MT-ключи из
  AI-таба-блока API-ключей (если общий блок — только MT-поля).
- Ожидаемо: монолит ~ −700…−850, quicktrans ~ −50, панель ~ −30.
- UI-элементы: вкладка «🌐 MT Settings» исчезает; в диалоге пакетного перевода исчезает
  выбор MT-провайдеров (остаётся custom MT); в Match Panel MT-строки только от custom MT.
- T9.2: (а) старт без MT-страницы, настроек MT-ключей; (б) custom MT endpoint (локальный
  фейк) даёт перевод в QuickTrans и Match Panel; (в) при пустых `custom_mt_profiles` —
  вежливое отсутствие MT (не падение); (г) старые enable-флаги `mt_*`/ключи в settings.json
  не читаются и не мешают.

### 9.3 — Облачные LLM + Ollama; молчаливая миграция provider
- Зоны: llm_clients.py (см. 2.3: словари моделей, claude/gemini/ollama/mistral/deepseek/
  openrouter ветки и клиенты, legacy-методы, ollama-хелперы; оставить openai-совместимое
  ядро + общие хелперы; диспетчер 862–871 → одна ветка); монолит: AI-таб радио/комбо/
  enable/Ollama-секция/keepwarm 7646–7719/`_apply_ollama_timeout_setting`/
  `_apply_gemini_proxy`; `translate_current_segment` ollama-диалог; `translate_batch`
  провайдерные ветки; `_update_llm_indicator`; autotag; proofread-воркер; chat_backend
  дефолт; quicktrans LLM-дефы; `local_llm_setup.py` (Ollama-код); `__init__`-флаги.
  **Здесь же**: `load_llm_settings` — молча `provider→custom_openai` + миграция плоского
  конфига в профиль с нормализацией схемы; `provider_enabled_states` — из дефолтов убрать
  удалённые `llm_*`/`mt_*` (сам механизм оставить; старые ключи инертны).
- Ожидаемо: llm_clients ~ −900…−1100 (2000 → ~900–1100), монолит ~ −600…−800,
  local_llm_setup −(Ollama-часть).
- UI-элементы: AI-таб = Custom + (временно) упрощённый Local LLM; статус-бар всегда custom;
  чекбоксы enable других провайдеров исчезают.
- T9.3: (а) старт с settings.json, где provider=openai/claude/ollama — приложение молча
  работает на custom_openai (или «не настроен», если профилей нет — без падения); (б)
  перевод через локальный фейк-сервер custom_openai (одиночный + пакетный + proofread);
  (в) Token Usage пишет записи с provider=custom_openai; (г) grep: ни одного
  `provider == 'openai'`/`'claude'`/… кроме custom_openai; (д) чат/QuickTrans стартуют.

### 9.4 — Settings/QuickTrans/селекторы; страница Local LLM на коде Custom
- Зоны: `_create_mt_quick_lookup_settings_tab` (редукция 20559–20940), остатки UI-текста
  AI-таба, `show_about` упоминания, `help_system.py` (AI_OLLAMA), `platform_helpers.py`,
  `chat_view_widget.py`, `translation_results_panel.py` коды LLM, `llm_pricing._FREE_PROVIDERS`.
  Страница Local LLM: убрать Ollama-виджет, работать с профилями Custom (пока без виджета
  llama-server — НЕ в объёме).
- Ожидаемо: ~ −200…−350.
- T9.4: QuickTrans показывает только Local LLM + Custom; Smoke-таблица 8.13 обновлена
  (пункты MT/AI-страниц); offscreen-прогон канонической smoke-таблицы.

### 9.5 (предложение) — Vision для custom_openai (BACKLOG §9.1)
- После стабилизации 9.3: паттерн/чекбокс «модель поддерживает vision»/именной whitelist.
  **Решено Дмитрием 2026-10-11 (ответ 4): вариант (б) — чекбокс в профиле Custom.**
  Зона: `llm_clients.VISION_MODELS`/`model_supports_vision`,
  `translate_with_usage` 858–871, `unified_prompt_manager_qt` 4456+. Отдельно от G5.

**Что после 9.x станет мёртвым (кандидаты в 8.18, не трогать в 9.x):**
`_REMOVED_add_mt_and_llm_matches_progressive` (52970–53243), `_save_llm_settings_from_ui`
(23730–23810), legacy-хелперы llm_clients (`main`, `get_*_translation`), остатки
`pdf_rescue_Qt` облачных клиентов (если модуль остаётся), ключи `api_keys`/`mtql_*`/`mt_*`
в settings_service-дефолтах.

**Что пока НЕ трогать:** фабрика `create_llm_client`/`_get_active_custom_profile` (G3.x
клиент LLM) — только минимальные правки в 9.1; виджет запуска llama-server (не существует —
не проектировать в 9.x); G5 figure-context (`translate_current_segment` figure-блок
50339–50368 по старым координатам, Image Extractor 10048-паттерн, `figure_context_manager.py`,
fixtures `docs/refactoring/samples/`); колонка БД `bridged_to_trados`; CAT-поля Project.

---

## Вопросы к Дмитрию (с рекомендациями)

**В.1. Token Usage & Cost — оставить как счётчик токенов или убрать?** Рекомендация:
**оставить** (меню 8532–8544, `usage_log`, `usage_report_dialog`, `llm_pricing`). Локальные
модели тоже отдают usage; стоимость для неизвестных моделей считается оценкой/0, исторические
записи облачных остаются читаемыми. Цена кода — ноль (уже отвязано от провайдеров).
Если убрать — минус ~2 модуля + пункт меню, но теряется учёт токенов (он полезен и для
локальных серверов).

**В.2. Файлы ключей облачных провайдеров (секция `api_keys` в settings.json +
`api_keys.example.txt`).** Рекомендация: в settings.json ничего не удалять и не переписывать
(ключи инертны; пользователь почистит руками, если захочет). UI-поля облачных ключей удалить
вместе со страницами (9.2/9.3). `api_keys.example.txt` обновить в docs-проходе (оставить
`custom_openai`, `custom_mt`; убрать облачные образцы).

**В.3. Судьба `provider_enabled_states` (settings_service 340–353).** Рекомендация: механизм
сохранить (enable/disable нужен как минимум для custom), из дефолтов удалить `llm_openai/
llm_claude/llm_gemini/llm_mistral/llm_openrouter/llm_ollama` и все `mt_*` по мере удаления
страниц (9.2/9.3); `llm_custom_openai` остаётся. Старые ключи в существующих файлах не читаем
и не удаляем (инертные, как договорились в 8.12 по G-группе).

**В.4. Vision для custom (BACKLOG §9.1) включать в план 9.x отдельным под-батчем 9.5?**
Рекомендация: да, отдельным 9.5 после 9.4 (меньше конфликтов по `llm_clients`), вариант на
выбор: (а) паттерн имени модели, (б) чекбокс «модель поддерживает vision» в профиле Custom
(рекомендую (б) — явный, локально-независимый), (в) именной whitelist. Ollama не ремонтируем.

**В.5. Страница «Local LLM» в переходный период (между 9.3 и будущим виджетом llama-server).**
Сейчас её контент — Ollama-виджет (`local_llm_setup.py`). Рекомендация: в 9.3 Ollama-код
удаляется, страница временно показывает те же профили Custom (переиспользование 9.1-логики)
с пометкой «управление локальным сервером появится позже»; виджет llama-server — отдельная
задача вне 9.x. Альтернатива — временно спрятать страницу до появления виджета.

## Ответы Дмитрия (2026-10-11) — вердикт по вопросам 1–5

Все пять рекомендаций ПОДТВЕРЖДЕНЫ:

1. **Token Usage & Cost — оставить** как счётчик токенов (уже отвязан от провайдеров,
   исторические записи читаемы).
2. **Ключи облаков** — в settings.json ничего не удалять; UI-поля уходят со страницами;
   `api_keys.example.txt` обновить в docs-проходе. ПОДТВЕРЖДЕНО.
3. **`provider_enabled_states`** — механизм сохранить; дефолты `llm_*`/`mt_*` удалённых
   провайдеров убирать по мере удаления страниц; старые ключи инертны. ПОДТВЕРЖДЕНО.
4. **Vision для custom** — отдельным под-батчем 9.5; вариант (b) — чекбокс «модель
   поддерживает vision» в профиле Custom. ПОДТВЕРЖДЕНО.
5. **Страница Local LLM в переходный период** — временно показать на ней профили Custom
   с пометкой; виджет llama-server — вне 9.x. ПОДТВЕРЖДЕНО.

Ответы авторизуют СОДЕРЖАНИЕ будущих под-батчей 9.x, но не их старт: каждый под-батч
начинается только по явной команде Дмитрия и его промпту (AGENTS.md, дисциплина
координатор/исполнитель).

---

## Стоп-условия

Не сработало ни одно: реальные данные не затронуты (все пробы в изо-профилях
`D:\Temp\SupervertalerPortable\analysis\r9\iso-*`), сеть не требовалась (fake-endpoint не
понадобился — баг воспроизводится чисто на UI/файле; loopback-конструирование клиента без
запросов), код не правился. Возвращаю управление Дмитрию.

## Артефакты

- `docs/refactoring/audits/r9_provider_inventory.py` + JSON-инвентарь
  (`D:\Temp\SupervertalerPortable\analysis\r9\r9_provider_inventory.json`)
- `docs/refactoring/audits/r9_probe_profiles.py`, `r9_seed_profiles.py`,
  `r9_log_a.txt`, `r9_log_ctrl.txt`, `r9_log_rm.txt`
- Изо-профили и промежуточные материалы: `D:\Temp\SupervertalerPortable\analysis\r9\`
