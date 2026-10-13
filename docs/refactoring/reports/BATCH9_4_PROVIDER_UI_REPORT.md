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
ade0e48a6ac94252a4194408a1cfcee10fe5dfdc523232f471cbd026df7edd15  Supervertaler.py (55000)
a55a0033092fdb7b0ea456e6a585151fc0683b1de38ee11eb872e24067ec09b5  modules/quicktrans.py (1628)
47e4def072eaca94624b4e66860de9f02209d7a73508a3779eeb3f1438ac4afa  modules/chat_view_widget.py (934)
1e64c2f1a8d56beee6f7aa533970dac332ededcf40095c855f6d2564b3d41152  modules/llm_clients.py (597)
e46f6c762d29abfb597e58034e0fc5998e9a9cb4a432e2218e89b6d20cc4c5d8  modules/llm_pricing.py (192)
805c397101b50ba6068127c039afefff0b7f82a485b6ecfab4f6bc496fe3f72d  modules/help_system.py (254)
644e19867b580cb281f008ea135d411920259029a9d30a039ffa2645d3387d0b  setup.py (94)
c08b7704f42b40536fd9553f34cff3f94c5a9cd79336fe64c736cdcc64568ab6  modules/local_llm_setup.py — УДАЛИТЬ (sha последней версии)
```

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
