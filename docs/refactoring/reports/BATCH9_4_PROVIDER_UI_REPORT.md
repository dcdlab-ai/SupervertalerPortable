# ОТЧЁТ Batch #9.4 — UI удалённых LLM-провайдеров (Settings / QuickTrans / статус-бар / чат)

**Дата:** 2026-10-13. **Исполнитель:** агент (executor). **Координатор:** Дмитрий.
**База:** `59290c98` (код 9.3d). **Вердикт за Дмитрием.** Не пушить (пуш — только по команде Дмитрия).

---

## §0. Баatch и baseline (ДО)

Цель по промпту: удалить из UI всё, что относится к удалённым в 9.3 LLM-провайдерам
(OpenAI, Anthropic/Claude, Gemini, Mistral, DeepSeek, OpenRouter, Ollama), сохранив
рабочими: Custom (OpenAI-Compatible) профили, статус-бар, QuickTrans, чат, страницы Settings.

Решения Дмитрия, реализованные в этом батче:
- QuickTrans LLM = **один чекбокс «Custom (OpenAI-Compatible)»** + read-only модель активного
  профиля (вариант 1a), код чипа **CUS**;
- **выбор профилей в QuickTrans** (дополнение Дмитрия от 2026-10-13) — по паттерну Custom MT
  (мастер-чекбокс + чекбокс на профиль) → под-батч **9.4f** (шлюз: ≤~100 строк нетто, без
  правок LLMClient, без изменения глобального активного профиля — шлюз выполнен, см. §2/§3);
- статус-бар: «🔌 {profile}: {model}» / «🔌 Custom profile not configured» (замечание Дмитрия
  по T9.3.9 учтено: индикатор теперь показывает состояние «не настроено»);
- Local LLM = **read-only заметка** «local server management coming later» в секции Custom
  профилей AI Settings (НЕ второй редактор профилей);
- ключи удалённых провайдеров в settings.json **не удалять** (инертны);
- страницы Settings **не переименовывать**.

Baseline ДО (замерено на 59290c98 в stage `D:\Temp\SupervertalerPortable\refactoring\batch9-4\`):
- AST chain: **907 / 0 unresolved**; pyflakes: **562** (undefined 126 строк / 4 имени: tk 100,
  messagebox 19, filedialog 2, ttk 5 — база Дмитрия из ответа 4 на вопросы 9.3);
- py_compile канонический **110/0**, справочный 168/0; headless 91/2 (setuptools, fitz);
- монолит **55 703** строк; QuickTrans-таб, AI Settings, статус-бар, чат-меню содержали UI
  удалённых провайдеров (радио, комбо, чекбоксы, Ollama-виджет, API-keys группа, 8 веток
  индикатора, 7 чипов-дефов, меню моделей чата на CLAUDE_MODELS).

---

## §1. Рекон (ЭТАП 1, без правок) — RECON_94.md

Полный рекон п.1–13 записан в stage-файле `RECON_94.md` (перенесён в аудиты, §5). Ключевые
выводы:
1. **AI Settings** (`_create_ai_settings_tab`): радио 7 провайдеров, 6 модельных комбо,
   Ollama-виджет (LocalLLMStatusWidget), API-keys группа (7 удалённых ключей, без custom),
   6 enable-чекбоксов, Ollama Advanced, неактивный чекбокс «Enable LLM (AI) matching»
   (находка 2b из 9.3) — всё DELETE; Custom-секция, proxy, Preferences, fuzzy/LLM-лимиты — KEEP.
2. **Save-цепочка** `_save_ai_settings_from_ui`: провайдер-цепочка → 'custom_openai'; записи
   удалённых `*_model`/ollama_* → DELETE; enabled_states → сохранять существующее + писать
   только `llm_custom_openai` (иностранные ключи сохраняются merge'ом); `_save_api_keys_from_ui`
   KEEP дословно (гард `if not self._api_key_inputs: return` обрабатывает пустую группу).
3. **Ollama-хвосты**: keepwarm-кластер (4 метода), `_apply_ollama_timeout_setting`,
   `_apply_gemini_proxy` + все вызовы (init, Save, startup) → DELETE (9.4b).
4. **local_llm_setup.py**: импортеры — только 2 места в AI Settings (умирают в 9.4a) →
   `git rm` (9.4b).
5. **Local LLM**: отдельной страницы нет (секция внутри AI Settings) → read-only заметка (9.4c).
6. **Статус-бар** `_update_llm_indicator`: 8 ветвей → одна Custom (9.4c).
7. **QuickTrans-таб**: список+цикл llm_providers, Ollama-строка, загрузка api_keys/enabled_states
   → DELETE; custom-строка KEEP (9.4d). quicktrans.py: PROVIDER_COLORS → CMT/CUS,
   `_AI_PROVIDER_CODES = {"CUS"}`.
8. **9.4f-шлюз**: паттерн Custom MT; оценка ~90 строк нетто; без LLMClient; без изменения
   глобального профиля → РЕШЕНИЕ: реализован как 9.4f.
9. **Чат-меню** `_show_model_menu`: read-only заголовок активного профиля + «AI Settings…»
   (навигация `_go_to_settings_tab("AI Settings")`); `_on_model_selected` DELETE.
10. **llm_clients.py хвосты**: `set_ollama_timeout`/`_ollama_timeout_override`,
    MISTRAL/OPENROUTER/OLLAMA/CLAUDE_MODELS, OLLAMA_ENDPOINT env-блок → DELETE (9.4e;
    единственные читатели умерли в 9.4b/9.4d).
11. **llm_pricing**: `_FREE_PROVIDERS = ("ollama",)` → `()`.
12. **Тексты** (9.4e): About, чекбокс пакетного диалога, proxy_note, setup.py keywords,
    help_system AI_OLLAMA, docstring AI-таба. pdf_rescue_Qt.py — PROTECTED, не тронут.
13. **Совместимость**: старые settings.json с облачными ключами — merge-from-existing сохраняет
    все ключи; загрузка дефолтов custom-only; миграция 9.3 даёт provider='custom_openai'.

Доп. проверки: `_clean_provider_prefix` — 0 вызовов (мёртвый кластер 8.18, не трогать);
legacy-ветка chat_backend 151–160 недостижима (provider всегда custom_openai) — KEEP (вне скоупа).

---

## §2. Зоны по коммитам

| Коммит | Файлы | Содержание |
|---|---|---|
| **9.4a `57648c47`** | Supervertaler.py (30+/546−) | AI Settings: удалены радио 7 провайдеров, 6 модельных комбо, Ollama-виджет+try-импорт local_llm_setup, `_friendly_model_name`/`_update_provider_label`, `on_ollama_selected`, radio-connect'ы (остал custom), API-keys группа (7 ключей), 6 enable-чекбоксов (остал custom), Ollama Advanced, неактивный llm_matching чекбокс; `update_combo_states` сведена к custom; `_save_ai_settings_from_ui`: provider→'custom_openai', записи удалённых моделей/ollama_*/keepwarm/enable_llm_matching удалены, enabled_states = merge (иностранные ключи целы) + llm_custom_openai; `_save_api_keys_from_ui` KEEP |
| **9.4b `df1b238f`** | Supervertaler.py (0+/96−), `git rm modules/local_llm_setup.py` (1071) | keepwarm-кластер (`_setup_ollama_keepwarm`, `_apply_ollama_timeout_setting`, `_start/_stop_ollama_keepwarm_timer`, `_ping_ollama_keepwarm`), `_apply_gemini_proxy` + вызовы (init 7554, startup 6363, Save 23752/23827/23856) |
| **9.4c `bfeb79d2`** | Supervertaler.py (24+/39−) | `_update_llm_indicator`: 8 ветвей → Custom (`🔌 {profile}: {model}` / `🔌 Custom profile not configured` через `_custom_llm_ready`); read-only заметка Local LLM в секции Custom профилей |
| **9.4d `7e274af0`** | Supervertaler.py (0+/103−), quicktrans.py (8+/20−), chat_view_widget.py (33+/123−) | QuickTrans-таб: llm_providers-список+цикл, Ollama-строка, load_api_keys/load_provider_enabled_states удалены; custom-строка (mtql_custom_openai + read-only модель активного профиля). quicktrans.py: PROVIDER_COLORS CMT/CUS, `_AI_PROVIDER_CODES={"CUS"}`, has_key-ветки gemini/ollama убраны. Чат: `_show_model_menu` → заголовок «🔌 {profile} – {model}» (disabled) / «🔌 Custom profile not configured» + «AI Settings…» → `_open_ai_settings`; `_on_model_selected` удалён |
| **9.4e `f6c26a8d`** | Supervertaler.py (4+/4−), llm_clients.py (0+/190−), llm_pricing.py (5+/5−), help_system.py (0+/1−), setup.py (0+/4−) | llm_clients: OLLAMA_ENDPOINT env-блок, `_ollama_timeout_override`/`set_ollama_timeout`, MISTRAL/OPENROUTER/OLLAMA/CLAUDE_MODELS (KEEP: DEFAULT_MODELS, VISION_MODELS={}, google→gemini, REASONING_MODELS); llm_pricing `_FREE_PROVIDERS=()`; тексты: About «Built with PyQt6 • Supports Custom (OpenAI-Compatible) LLMs», чекбокс пакетного диалога «(Custom OpenAI-Compatible)», proxy_note «Applies to: Custom (OpenAI-Compatible), Google Translate, DeepL, Microsoft Translator, ModernMT, and MyMemory.», setup.py keywords, help_system AI_OLLAMA, docstring AI-таба |
| **9.4f `9675f93f`** | Supervertaler.py (41+/14−), quicktrans.py (41+/27−) | Профильный выбор QuickTrans: в табе — мастер-чекбокс (восстановлен `llm_layout.addLayout(custom_row)`, см. §7 находка 1) + чекбокс на профиль («{name} – {model}», `self._mtql_llm_profile_cbs`); сохранение `mtql_llm_profiles` (список имён) в mt_quick_settings; quicktrans `_add_llm_providers`: мастер-гейт mtql_custom_openai → чип CUS на каждый включённый профиль (label = имя профиля; absent-список = все профили с endpoint; пустой = ни одного; legacy-fallback одиночный «Custom»); `_call_llm_translation(profile_name=…)` → `create_llm_client(..., profile_name=…)` → `_get_active_custom_profile(settings, profile_name)` / `_custom_llm_ready(settings, profile_name)` (опц. параметр, дефолт = глобальный активный профиль — не меняется) |

---

## §3. Диффы

Суммарно по коду: **+111 / −2343 = −2232 строк** (numstat по 6 коммитам, без docs).
- Supervertaler.py: 55 703 → **55 000** (−703; +102/−805 по 6 коммитам);
- modules/local_llm_setup.py: 1071 → удалён;
- modules/llm_clients.py: 787 → **597** (−190);
- modules/chat_view_widget.py: 1024 → **934** (−90);
- modules/quicktrans.py: 1626 → **1628** (+2: 9.4d −12, 9.4f +14);
- modules/llm_pricing.py: 192 (−0 net); modules/help_system.py: 255 → 254; setup.py: 98 → 94.

9.4f net: **+41** (шлюз ≤100 выполнен; LLMClient не тронут; глобальный
`custom_openai_active_profile` не меняется — проба ACTIVE UNCHANGED: True).

---

## §4. Валидация (обойма после КАЖДОГО коммита)

Канонические скрипты (AGENTS.md), тег b94x, stage `batch9-4\`:

| Метрика | ДО (907-база) | 9.4a | 9.4b | 9.4c | 9.4d | 9.4e | 9.4f |
|---|---|---|---|---|---|---|---|
| AST chain (unresolved) | 907/0 | 880/0* | 879/0 | 880/0 | 874/0 | 874/0 | **875/0** |
| pyflakes (undefined 126/4) | 562 | 558 | 550 | 550 | 549 | 549 | **549** |
| py_compile канон/справ. | 110/0, 168/0 | 110/0, 168/0 | 109/0, 167/0 | 109/0 | 109/0 | 109/0 | **109/0, 167/0** |
| headless imports | 91/2 | 91/2 | 90/2 | 90/2 | 90/2 | 90/2 | **90/2** |
| S-clean / S-upgrade | OK | OK | OK | OK | OK | OK | **OK** |
| regress 6 sha (5a12501f/44828d90/c413d563) | OK | OK | OK | OK | OK | OK | **OK** |
| Tools-smoke 42 (база 8.13) | OK | OK | OK | OK | OK | OK | **OK** |
| termbase regress | OK | OK | OK | OK | OK | OK | **OK** |
| About probe | OK | OK | OK | OK | OK | OK | **OK** |
| save probe (seed+save, иностр. ключи) | — | OK | OK | OK | OK | OK | **OK** |
| r9 a/ctrl/rm (профили) | — | OK | OK | OK | OK | OK | **OK** |
| e2e 5 сценариев (verdict OK) | — | — | — | OK | OK | OK | **OK** |
| qtchat probe (чипы+меню) | — | — | — | — | OK | OK | **OK** |
| statusbar probe (3 состояния) | — | — | — | OK | OK | OK | **OK** |
| profiles probe (9.4f) | — | — | — | — | — | — | **OK** |

\* 9.4a: chain-прогон 9.4a не был сохранён в лог (обойма 9.4a включала pyflakes/py_compile/
headless/полный offscreen-набор — все зелёные); число 880 — из замера 9.4c (после 9.4b 879).
py_compile канон 110→109 с 9.4b (удалён local_llm_setup.py). pyflakes −14 (562→549) — из
удалённого кода; undefined-набор идентичен базе (126/4). headless 91→90 с 9.4b (файл удалён).

**Grep-гейт** (`docs/refactoring/audits/batch9-3_grep_gate.py`, прогон `gate_after_94f.txt`):
монолит — только 2 разрешённых остатка (`get_google_translation` 2 — comment/разрешённые зоны,
`provider == 'gemini'` 1 — comment); llm_clients/settings_service/chat_backend/chat_view_widget/
quicktrans/unified_prompt_manager/workers/proofread/translation_results_panel — CLEAN (0 hits).
Явный список разрешённых остатков (вне гейта, по решению скоупа):
- мёртвые методы 8.18: `_save_llm_settings_from_ui`, `_add_mt_and_llm_matches`,
  `_REMOVED_add_mt_and_llm_matches_progressive`, `_clean_provider_prefix` (не трогались);
- инертные ключи settings.json (не удалялись по решению Дмитрия): `llm_openai/claude/gemini/
  mistral/openrouter/ollama`, `openai_model/claude_model/gemini_model/mistral_model/
  deepseek_model/openrouter_model/ollama_model`, `ollama_keepwarm`, `ollama_timeout_minutes`,
  `enable_llm_matching`, старые `mtql_*` удалённых провайдеров;
- комментарии кода с именами провайдеров (ai_actions, autocorrect, chat_message_delegate,
  platform_helpers, chat_backend, superlookup TODO) → 8.16;
- pdf_rescue_Qt.py (PROTECTED, google→gemini миграция ключа — живой читатель);
- docs/ и аудиты.

Спец-пробы 9.4f (probe_94f_profiles.py, iso-профиль): TAB OK; чекбоксы таба =
[Auto-fetch, Custom (OpenAI-Compatible), Profile A/B/C]; DEFAULT ALL ON True;
SAVED `mtql_llm_profiles: ['Profile A','Profile B']` (C снят) SAVE OK True;
CHIPS: master-off=[]; A,B→2 чипа; C-only=[] (пустой endpoint отфильтрован);
list-absent=2 (все с endpoint); empty-list=[]; CLIENT A резолвится на endpoint/model/key
профиля A при активном B; EXEC OK; ACTIVE UNCHANGED True.

---

## §5. Пакет тестовой сборки (8 файлов, SHA256)

Замена в `D:\SupervertalerPortable_test\SupervertalerPortable\` (решение о пересборке — за Дмитрием):

```
fb3dce5c13dd30c14403c4384320da6b2e0b625521b556a5d6ae22a91adc4352  Supervertaler.py (54992)
6a6812be6c7acce66cbb821c83010e66e658abe39ccf286a06945d153fbf8808  modules/quicktrans.py (1635)
47e4def072eaca94624b4e66860de9f02209d7a73508a3779eeb3f1438ac4afa  modules/chat_view_widget.py (934)
1e64c2f1a8d56beee6f7aa533970dac332ededcf40095c855f6d2564b3d41152  modules/llm_clients.py (597)
e46f6c762d29abfb597e58034e0fc5998e9a9cb4a432e2218e89b6d20cc4c5d8  modules/llm_pricing.py (192)
805c397101b50ba6068127c039afefff0b7f82a485b6ecfab4f6bc496fe3f72d  modules/help_system.py (254)
644e19867b580cb281f008ea135d411920259029a9d30a039ffa2645d3387d0b  setup.py (94)
c08b7704f42b40536fd9553f34cff3f94c5a9cd79336fe64c736cdcc64568ab6  modules/local_llm_setup.py — УДАЛИТЬ (sha последней версии)
```

(Итоговые SHA после 9.4i, 2026-10-14; Supervertaler.py и quicktrans.py обновлены коммитами
`064c2bbf`/`2e9dd938`, остальные файлы 9.4 — без изменений.)

---

## §6. Ручные сценарии T9.4.x (для тестовой сборки)

- **T9.4.1** AI Settings: нет радио/комбо/Ollama-виджета/API-keys группы/enable-чекбоксов
  удалённых провайдеров/Ollama Advanced; Custom-секция с профилями работает (добавить/
  сохранить/активный профиль); Proxy и Preferences целы; чекбокс «Enable LLM (AI) matching»
  отсутствует.
- **T9.4.2** Save AI Settings: после Save в settings.json provider=custom_openai, профили
  целы, иностранные ключи (llm_openai и т.п.) сохранены (merge), ключей удалённых моделей нет.
- **T9.4.3** Статус-бар: с профилем → «🔌 {profile}: {model}»; без профилей →
  «🔌 Custom profile not configured»; тултип с endpoint.
- **T9.4.4** Local LLM: в секции Custom профилей заметка «ℹ️ Local LLM: local servers are used
  via the Custom (OpenAI-Compatible) profiles above. Local server management is coming later.»
- **T9.4.5** QuickTrans-таб: чекбокс «Custom (OpenAI-Compatible)» + read-only модель активного
  профиля + чекбоксы по профилям (по умолчанию все включены); Save сохраняет mtql_llm_profiles.
- **T9.4.6** QuickTrans-попап (Ctrl+Alt+Q): чип CUS на каждый включённый профиль (label = имя
  профиля); снятие профиля в табе + Save → чип исчезает; мастер-выключен → LLM-чипов нет;
  перевод чипом идёт endpoint/моделью этого профиля (проверить на двух профилях с разными
  моделями).
- **T9.4.7** Меню чата: заголовок «🔌 {profile} – {model}» (не кликается) + «AI Settings…»
  открывает вкладку AI Settings; без профиля — «🔌 Custom profile not configured».
- **T9.4.8** About: «Built with PyQt6 • Supports Custom (OpenAI-Compatible) LLMs».
- **T9.4.9** Старый settings.json (с облачными ключами): приложение стартует, ключи инертны,
  UI чистый; QuickTrans/чат/перевод через Custom работают.
- **T9.4.10** Пакетный перевод: чекбокс «(Custom OpenAI-Compatible)»; диалог без GPT/Claude/Gemini.
- **T9.4.11** Smoke: 42 пункта меню работают (Tools-smoke база 8.13).
- **T9.4.12** (9.4i, 2026-10-14): 1) в табе QuickTrans нет чекбокса «Custom (OpenAI-Compatible)»,
  есть чекбоксы профилей; 2) все профили включены → попап: по чипу на профиль; 3) снять один →
  остаётся чип второго; снять все → попап работает с глобальным активным профилем; 4) профили
  удалены/пустой endpoint → вежливо, без ошибок; 5) старый settings.json с
  `mtql_custom_openai: false` → попап всё равно работает.

---

## §7. Находки

1. **9.4f-правка таба потеряла `llm_layout.addLayout(custom_row)`** (мастер-чекбокс строился,
   но не добавлялся в layout — в UI не появлялся). Найдено offscreen-пробой (мастер-чекбокс
   отсутствовал в списке чекбоксов группы), восстановлено в 9.4f. Урок: правка «замены строки»
   обязана сохранять все add*-вызовы зоны — проверять пробой виджетов, а не только py_compile.
2. **Секция general vs ui.general_settings**: `mt_quick_lookup` живёт в верхнеуровневой секции
   `general` settings.json (не в `ui.general_settings`); проба 9.4f сначала сеяла/читала не ту
   секцию → ложный FAIL save-проверки. Приложение (SettingsService) корректно пишет `general`.
3. **Метод `_update_llm_indicator` теперь показывает «not configured»** — прямое следствие
   замечания Дмитрия по T9.3.9 (текст был только в модельных окнах). Совпадение с его
   наблюдением подтверждено пробой (3 состояния).
4. **Чат-меню не меняет глобальный активный профиль** (read-only заголовок) — согласуется с
   решением Дмитрия; выбор профиля для QuickTrans — локальный (`mtql_llm_profiles`), глобальный
   `custom_openai_active_profile` не трогается (ACTIVE UNCHANGED True).
5. **llm_matching чекбокс удалён из UI** (находка 2b 9.3, решение Дмитрия): сам метод
   `_save_llm_settings_from_ui` и кластер Match Panel — в 8.18 (не трогались).
6. **pdf_rescue_Qt.py не тронут** (PROTECTED); google→gemini миграция ключа сохранена
   (живой читатель).
7. **Path-scoped kill процессов** (предупреждение Дмитрия 2026-10-13): все kill_leftovers в
   runner'ах — PowerShell-фильтр по `ExecutablePath E:\Dev\python-embed\*` + project java по
   CommandLine; `taskkill //IM python.exe` не используется; `I:\AI\StrataPortable\python` не
   затрагивался ни разу.

---

## §8. Вопросы координатору

1. **Чипы профилей в QuickTrans**: label чипа = имя профиля (паттерн Custom MT). Альтернатива —
   «CUS: {profile}». Текущий вариант согласован с Custom MT; менять не требуется.
2. **Профиль без endpoint** (в табе чекбокс есть, чип не создаётся): молча пропускается.
   Нужен ли в табе маркер «нет endpoint» — на усмотрение (в 9.5 с vision-галкой уместнее).
3. **mtql_llm_profiles при удалении профиля в AI Settings**: имя остаётся в списке (фильтр по
   существующим профилям делает его безвредным). Чистка — кандидат 8.18/модульного прохода.
4. **Статус-бар при пустом списке mtql_llm_profiles**: показывает активный профиль (глобальный)
   — индикатор не связан с чипами QuickTrans. Считать ли это корректным — на усмотрение.

---

## §9. Handover

- **9.5** (vision-чекбокс в профиле Custom): VISION_MODELS={} жёткий; план — галка
  «модель поддерживает vision» в профиле + `model_supports_vision` по профилю; чипы 9.4f
  позволяют включать vision-профиль отдельно.
- **8.18** (мёртвые методы): `_save_llm_settings_from_ui` (удалять, не оживлять — запись
  Дмитрия), `_add_mt_and_llm_matches`, `_REMOVED_add_mt_and_llm_matches_progressive`,
  `_clean_provider_prefix`, enable_llm_matching-кластер (решение Дмитрия 2026-10-13),
  `set_bridged_to_trados`, tkinter-остатки.
- **8.16** (docs-комментарии): комментарии с именами удалённых провайдеров (список §7 гейта).
- **8.17**: po_handler-записи в CODE_MAP/DEPENDENCY_MAP.
- **P1**: check_for_updates; **BACKLOG §9.2**: Set as Project TMs; **G5**: figure-context.
- Тестовая сборка: пакет §5 (8 файлов, local_llm_setup.py удалить); пересборка — решение Дмитрия.

**Итог:** Batch #9.4 EXECUTED — 6 коммитов (9.4a `57648c47`, 9.4b `df1b238f`, 9.4c `bfeb79d2`,
9.4d `7e274af0`, 9.4e `f6c26a8d`, 9.4f `9675f93f`), код −2232 строк, монолит 55 703 → 55 000.
Обойма зелёная после каждого коммита; grep-гейт чист (разрешённые остатки перечислены).
Ручные T9.4.1–.11 — за Дмитрием на тестовой сборке. Формальный вердикт — за Дмитрием.
Агент останавливается и ждёт вердикта. Не пушить.

---

## §10. Результаты тестов Дмитрия (2026-10-13), ответы §8 и follow-up 9.4g

### 10.1 Тесты T9.4.x

- **T9.4.1–T9.4.5, T9.4.7–T9.4.10 — ПОДТВЕРЖДЕНО.**
- **T9.4.6 — ПОДТВЕРЖДЕНО с ЗАМЕЧАНИЕМ** (попап и профили Custom — см. п. 10.3).
- **T9.4.11 (smoke) — маркера нет**; offscreen-прогон 42 пунктов зелёный (`smoke_after_94g.log`).
- Формальный вердикт (ACCEPT) — за Дмитрием.

### 10.2 Ответы на вопросы §8

1. Label чипа = имя профиля — **ПОДТВЕРЖДЕНО, менять не требуется**.
2. Профиль без endpoint: Дмитрий не понял формулировку; его решение — **«возможно нужно
   сделать запрет на сохранение профиля без заполненного поля endpoint»** → записано в
   BACKLOG §9.5 (в 9.5 вместе с vision-галкой).
3. mtql_llm_profiles при удалении профиля — **ПОДТВЕРЖДЕНО** (кандидат 8.18).
4. Статус-бар при пустом mtql_llm_profiles показывает глобальный активный профиль —
   пересказано Дмитрием без явного вердикта; остаётся как есть.

### 10.3 ЗАМЕЧАНИЕ: «QuickTrans-попап не переводит с профилем из Custom (OpenAI-compatible API)»

Исследование (пробы на коде репозитория, `probe_94g_popup.py`, `probe_94g2_schemeless.py`):

- **Попап подключён к Custom (OpenAI-Compatible) в коде репозитория и переводит**: чип CUS
  на каждый включённый профиль, запрос уходит endpoint/моделью/ключом этого профиля
  (`/v1/chat/completions`, `Bearer prof-key-123`, `fake-llm`), в попапе появляется строка
  перевода. С **бесcхемным** endpoint (`127.0.0.1:PORT/v1`) — тоже зелёный (read-path
  нормализация 9.3a).
- **Причина наблюдения (уточнено 2026-10-14, после тестов Дмитрия):** первичный диагноз
  «тестовая сборка до 9.1b» **НЕ подтверждён** — Дмитрий подтверждал T9.1.5 (нормализация
  схемы endpoint в AI Settings) на этой же тестовой сборке, значит нормализация в сборке есть.
  Реальная причина — **гейт 9.4f**: попап не переводил, когда мастер-чекбокс
  «Custom (OpenAI-Compatible)» выключен (`mtql_custom_openai = false`) или список профилей пуст
  (`mtql_llm_profiles = []`) → ноль CUS-чипов → переводить нечем. Исправлено **9.4h**
  (пустой список → чип глобального активного профиля) и **9.4i** (мастер-чекбокс убран
  вовсе, чипы есть всегда). 9.4g (нормализация схемы в Custom MT) остаётся как независимое
  улучшение.
- **Решение для сборки:** пересборка пакета §5 (решение Дмитрия) — в нём нормализация и
  исправления попапа (9.4h/9.4i) уже есть.

### 10.4 ЗАМЕТКА (авторизованная правка): схема endpoint в Custom MT (QuickTrans-таб)

Выполнено как **9.4g, коммит `f6f98538`** (Supervertaler.py, +6/−2):

- Save таба: `_normalize_custom_endpoint` к endpoint профиля (паттерн AI Settings 9.1b:
  loopback/приватные → `http://`, публичные → `https://`); поле показывает нормализованное
  значение. `192.168.1.5:8080/v1` → `http://192.168.1.5:8080/v1`.
- `call_custom_mt`: нормализация на чтении (явный профиль и активный с диска).
- Пробы: `probe_94g_mtfix.log` (save/field/read/active — OK), `probe_94g_popup.log`,
  `probe_94g2.log` (попап с бесcхемным профилем — зелёный).
- Полный suite после правки — зелёный: chain 875/0; pyflakes 549 (undefined 126/4);
  py_compile канонический 109/0 (справочный 180/0); headless 90/2 (setuptools, fitz);
  e2e verdict OK; S-clean/S-upgrade (hash-diff пустой); regress 6 sha (5a12501f/44828d90/
  c413d563); smoke 42; TB OK; About OK; save OK; r9 a/ctrl/rm OK; grep-гейт чист.
- Монолит **55 000 → 55 004**; SHA пакета Supervertaler.py `a3ced13d…`.

### 10.5 ЗАМЕТКИ Дмитрия «внести в документацию» — внесены в BACKLOG

- **§9.3** — импорт/экспорт профилей Custom (формат, UI, судьба api_key, слияние).
- **§9.4** — чат-меню: переключение глобального активного профиля (сейчас read-only).
- **§9.5** — запрет сохранения профиля Custom с пустым endpoint (ответ на §8 Q2).

**Итог §10:** 9.4 протестирован (10/11 подтверждено, T9.4.11 без маркера); follow-up 9.4g
(нормализация схемы Custom MT) выполнен и закоммичен `f6f98538`; попап с Custom LLM в коде
репозитория работает (доказано пробами), причина наблюдения — бесcхемный endpoint на frozen
сборке до 9.1b. Формальный вердикт по 9.4 — за Дмитрием. Агент останавливается. Не пушить.

### 10.6 Уточнение Дмитрия (2026-10-13, вечер): попап с пустым списком профилей → 9.4h

Уточнение ЗАМЕЧАНИЯ: «когда отключены/удалены профили в QuickTrans, попап должен работать с
глобальным активным профилем из AI Settings, как с единственно оставшимся. А он не работает».
Это и есть реальный сценарий T9.4.6 — **подтверждённый баг 9.4f**: при `mtql_llm_profiles = []`
(все чекбоксы сняты) `_add_llm_providers` не создавал ни одного чипа и молча выходил.

Исправление **9.4h** (`modules/quicktrans.py`, `_add_llm_providers`): если чипы не созданы
при непустом списке профилей — добавляется чип **глобального активного профиля**
(`_get_active_custom_profile`, label = его имя, вызов с `profile_name=None` → endpoint/ключ/
модель активного профиля). Ничего не удалено, поведение остальных сценарий не изменилось.

Проба `probe_94h_fallback.py` — 5 сценариев зелёные: S1 все сняты → чип «Profile A» + перевод
с его ключом (`Bearer prof-key-A`); S2 подмножество → только Profile B; S3 список отсутствует →
оба профиля; S4 профили удалены → легаси-чип «Custom Endpoint» (авто-миграция плоского
endpoint SettingsService) + перевод; S5 все сняты + активного имени нет → резолв на первый
профиль. Suite после правки — зелёный (см. §4-паттерн, логи `*_after_94h.*`).

**Находка (9.4h, S-upgrade):** HASH-DIFF пробы upgrade показал `changed=['workbench/ai_assistant/index.json']`
(в 9.4g-прогоне пусто). Это артефакт времени, не регрессия: чат-индекс `index.json` при старте
добавляет запись сессии по дате (`"20261014": []`) и поле `updated`; прогон 2026-10-13 не создал
нового ключа (ключ 20261013 уже был от предыдущих прогонов того дня). Транзиент-фильтр пробы
накрывает только `.db-shm/.db-wal` — дату-зависимые артефакты чат-индекса в него не входят;
учтено при чтении HASH-DIFF (кандидат: расширить транзиент-список пробы в 8.16/инфра).

**T9.4.11 — ПОДТВЕРЖДЕНО (Дмитрий, 2026-10-13).** **Q4 — ПОДТВЕРЖДЕНО**: статус-бар показывает
глобальный активный профиль.

### 10.7 Batch #9.4i (2026-10-14): QuickTrans — мастер-чекбокс «Custom (OpenAI-Compatible)» убран

**Решение Дмитрия (2026-10-14):** мастер-чекбокс `mtql_custom_openai` в табе QuickTrans
УБИРАЕТСЯ. LLM-чипы в попапе есть всегда. Чекбоксы профилей (`mtql_llm_profiles`) выбирают,
какие профили показывать; если ни один не выбран (или список пуст/имена устарели) — работает
глобальный активный профиль из AI Settings как единственный оставшийся (чип 9.4h). Отключить
LLM в QuickTrans нельзя — так задумано. Баг «9.4h не работает» (скриншот: мастер снят → попап
пуст) устраняется удалением самого мастера.

**Рекон (Этап 1, `RECON_94i.md`):** читатели `mtql_custom_openai` — только таб (виджет+реестр
`_mtql_checkboxes`), гейт `_add_llm_providers`, Save (через реестр); читатели
`mtql_custom_openai_model` — read-only поле таба и legacy-чип quicktrans.py:407. Динамической
сборки ключей нет, других читателей нет (СТОП не сработал). Read-only поле модели активного
профиля после удаления мастера теряет смысл (модели в подписях чекбоксов профилей) — удалено
вместе с мастером без побочных эффектов. Ключевой нюанс: Save пересобирает секцию
`mt_quick_lookup` с нуля → для требования «старый ключ не удалять» добавлен явный перенос
инертных ключей из старой секции.

**Сделано (2 коммита):**

| Коммит | Файл | Зона | Строки | Изменение |
|---|---|---|---|---|
| `064c2bbf` (9.4i-1) | Supervertaler.py | `_create_mt_quick_lookup_settings_tab` (19879–20129) | 20089–20114 → 5 | Мастер-строка (custom_cb, custom_row, read-only custom_model_edit, ключ `_mtql_llm_combos`) удалена; `load_llm_settings()` сохранён для цикла 9.4f; комментарий 9.4f обновлён |
| `064c2bbf` | Supervertaler.py | `_save_mt_quick_lookup_settings` (20131–20187) | +9 (после 20150) | Перенос инертных ключей `mtql_custom_openai`/`mtql_custom_openai_model` из старой секции (в файле остаются, не читаются, заново не пишутся) |
| `2e9dd938` (9.4i-2) | modules/quicktrans.py | `_add_llm_providers` (347–400) | гейт 353–358 удалён; 382–402 → 16 | Мастер-гейт удалён; legacy-чип «Custom» (плоский endpoint) удалён; fallback 9.4h унифицирован: при нуле чипов чип глобального активного профиля (`_get_active_custom_profile`: активный по имени → первый с endpoint → легаси-плоский), при ненастроенном профиле — чипов нет, ошибок нет |

Монолит **55 004 → 54 992**; quicktrans.py **1 642 → 1 635**. SHA пакета: Supervertaler.py
`fb3dce5c…`, quicktrans.py `6a6812be…` (§5).

**Спец-проба `probe_94i_master_removed.py` (фейк-endpoint 127.0.0.1, openai в рантайме,
ловушка сети requests/anthropic/google.generativeai/ollama + socket-страж) — зелёная:**
- T1 таб: мастера нет; Auto-fetch + чекбоксы профилей есть; read-only поля нет; в реестре
  `mtql_checkboxes` ключа мастера нет; Save НЕ пишет `mtql_custom_openai` и НЕ удаляет его из
  файла (false → false, «legacy-model» → «legacy-model»); чужие ключи секции целы.
- T2 чипы: A,B → два; только B → один; все сняты → чип активного «Profile A» + перевод
  `Bearer prof-key-A`; список устарел (Ghost) → активный; активное имя dangling → первый с
  endpoint; пустой endpoint профиля пропущен; профили удалены + плоский endpoint →
  «Custom Endpoint» + перевод; ничего не настроено → чипов нет, ошибок нет.
- T3: `mtql_custom_openai` false / true / отсутствует → одинаковый результат (ключ игнорируется).
- T4: ловушка сети не сработала (TRAP HITS = []).
- T5 (скриншот Дмитрия): старый файл с мастером=false, профиль «strata» unchecked → чип
  «strata» + перевод `Bearer prof-key-strata`.

**Обойма после каждого коммита — зелёная** (логи `static_after_94i_1/2.log`,
`suite_94i_after.log`): chain 871/0 (−4: удалены ровно 4 вызова мастер-строки —
`self._get_active_custom_profile()` (резолв профиля для read-only поля) + 3× `self.tr()`
(label/tooltip/placeholder); diff JSON chain before/after: removed 4, added 0); pyflakes 549 (undefined
126/4 — идентичен); py_compile канон 109/0 (справочный 186/0); headless 90/2 (setuptools,
fitz); grep-гейт чист; offscreen-набор: fb S1–S5, profiles, qtchat, statusbar, e2e verdict OK,
S-clean/S-upgrade (HASH-DIFF пуст, index.json — артефакт даты, §10.6), regress 6 sha
(5a12501f/44828d90/c413d563), smoke 42, TB OK, About OK, save ALL OK, r9 a/ctrl/rm OK.

**T9.4.12 — сценарий для Дмитрия** (добавлен в §6). **ПОЛНОЕ ПОДТВЕРЖДЕНИЕ (Дмитрий, 2026-10-14):**
все 5 пунктов сценария подтверждены на тестовой сборке с пакетом §5.

**Handover:** 9.5 (vision-галка в Custom-профиле + запрет сохранения профиля с пустым
endpoint, BACKLOG §9.1/§9.5), затем G5 (урезанный), 8.18, 8.16, 8.17.
