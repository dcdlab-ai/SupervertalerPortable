# Upstream Sync U1.1 + U1.2 — Этап 2: перенос (A-пакет + настройки)

**Дата:** 2026-10-01
**Основание:** [UPSTREAM_SYNC_STAGE1_REPORT.md](UPSTREAM_SYNC_STAGE1_REPORT.md) (база апстрима v1.10.371, цель v1.10.372, общей git-истории нет)
**Коммиты батча:** U1.1 = `a7746d65`, U1.2 = `f5c460e9` (поверх U1.1)
**Вне объёма (не переносилось даже «попутно»):** все остальные коммиты диапазона (классы C/D: ee75e3be, fe1a7d0a, 2386c976, 763291e8, 1f8cad19, f6d9c279, 05720a55 и др.)

---

## 0. Baseline и git-синхронизация

| Параметр | Значение |
|---|---|
| `git fetch origin` / `git fetch upstream --tags` | выполнены; origin/main без изменений |
| HEAD до работ | `07437d61f4180b430b309634f1f7bbfcc7beaec3` (отчёт Этапа 1) |
| origin/main | `07437d61` — совпадает |
| `git status` | чисто (только служебный untracked `.zcode/plans/…`) |
| `git log --oneline -5` | `07437d61` (Stage 1 report), `7b895c93` (Batch #7 final), `94db76d2`, `22ccea43`, `d4db217e` |
| Дрейф-чек `git merge-base --is-ancestor 7b895c93 HEAD` | **истина** |
| HEAD опережает 7b895c93 | 1 коммит `07437d61` — docs-only, файлы батча не трогает → не блокер |
| `git rev-parse v1.10.372^{commit}` | `a58572276b4fced9384cf64580237c9edee75007` — совпадает с Этапом 1 |
| 7 SHA батча (`git cat-file -t`) | все — `commit`: 8e8be3d4, 0d5375e0, 75a621a1, b3f76ee7, f5bfefc9, 626d4c63, da403a48 |
| Baseline `wc -l` | Supervertaler.py = 68 224; settings_service.py = 565 |
| Baseline SHA256 | Supervertaler.py `c0370685…`, settings_service.py `5e582639…` |
| `py_compile` до работ | 135/135 OK |
| EOL baseline (`git ls-files --eol`) | все 12 файлов батча: `i/lf w/lf` |

---

## 1. План файлов (Этап 1)

| Файл | Коммиты батча | Остальные коммиты 371..372 | Blob vs 371 | Решение |
|---|---|---|---|---|
| modules/llm_pricing.py | 8e8be3d4, 0d5375e0 | — | идентичен | **ЦЕЛИКОМ из тега** |
| modules/pricing.json | 8e8be3d4 | — | идентичен | **ЦЕЛИКОМ** |
| modules/chat_backend.py | 0d5375e0 | — | идентичен | **ЦЕЛИКОМ** |
| modules/unified_prompt_manager_qt.py | 75a621a1 | — | идентичен | **ЦЕЛИКОМ** |
| modules/platform_helpers.py | b3f76ee7 | — | идентичен | **ЦЕЛИКОМ** |
| modules/llm_clients.py | f5bfefc9, da403a48 | — | идентичен | **ЦЕЛИКОМ** (оба коммита в батче → финальное состояние тега) |
| modules/pdf_rescue_Qt.py | f5bfefc9 | — | идентичен | **ЦЕЛИКОМ** |
| modules/prompt_assistant.py | f5bfefc9 | — | идентичен | **ЦЕЛИКОМ** |
| modules/keyboard_shortcuts_widget.py | 626d4c63 | — | идентичен | **ЦЕЛИКОМ** |
| Supervertaler.py | f5bfefc9, 626d4c63, da403a48 | — | рефакторинг | **ВРУЧНУЮ (B)**, по именам методов |
| modules/settings_service.py | (f5bfefc9, 626d4c63 — косвенно) | — | Portable-only | **ВРУЧНАЯ**: только дефолт `claude_model` + комментарий |
| FAQ.md | da403a48 | — | в Portable файла НЕТ | **ПРОПУЩЕН** (см. вопрос Q2) |

`tests/test_*.py` и `CHANGELOG.md` апстрима не переносятся (в репо не добавлялись; CHANGELOG в Portable нет).

### AST-проверка зависимостей 75a621a1 (п.3) — PASS
- `UnifiedPromptManagerQt.__init__(self, parent_app, …)`; экземпляры создаются только как `UnifiedPromptManagerQt(self, standalone=False)` внутри `SupervertalerQt` (`Supervertaler.py:9897`, `:10098`) → `parent_app` — экземпляр `SupervertalerQt`.
- `self.tm_database`/`self.tm_metadata_mgr` присваиваются в `SupervertalerQt.__init__` (AST; также в `_reinitialize_with_new_data_path`, `initialize_tm_database` — тот же класс; присваивание `self.tm_database` в `SuperlookupTab.__init__@62515` — другой класс, менеджеру недоступно и не нужно).
- `_search_termbase_in_memory` и `_segment_for_grid_row` определены в `SupervertalerQt` (AST: `@30860`, `@9438`; ссылка `_mw_sm._segment_for_grid_row`@2522 — обращение к главному окну из вложенного helper'а, тот же класс-владелец).
- **Блокера нет.**

### API-проверка platform_helpers (b3f76ee7, п.4) — PASS
Все имена, импортируемые из `modules.platform_helpers` по всему Portable (AST: `Supervertaler.py:119,11801,25784,29788,54712,66763,66901,66914,66921,66956,67399,67456,67489,67643,67651`; `modules/clipboard_manager_widget.py` и др.), присутствуют в версии v1.10.372. Фикс чисто аддитивный (`send_unicode_text`, `altgr_character`, `_WinKeyboard`, `VK_RMENU/VK_LCONTROL/VK_CAPITAL`, `_KEYEVENTF_UNICODE` + расширение `GlobalHotkeyManager`). **Ломающего API нет.**

### Трёхсторонние диффы монолитных методов (п.5) — дрейфа нет
Для каждого затронутого метода сверены тела: апстрим@371 → Portable@HEAD — **в затронутых регионах совпадают дословно** (у `_save_ai_settings_from_ui`/`_create_ai_settings_tab` Portable расширял метод в ДРУГИХ регионах — mistral/deepseek/openrouter уже были и в апстриме 371; `existing_settings = self.load_llm_settings()` на rel-строке 47 в обеих версиях — сверено AST). Тело «апстрим 371 → коммит» = таблица в §3. Диффы: `D:\Temp\SupervertalerPortable\refactoring\u1-port\{f5_mono,626_mono,da4_mono,626_ksw,da4_llm_clients,f5_modules}.diff`.

---

## 2. U1.1 — что сделано (коммит `a7746d65`)

Порядок хронологический: 8e8be3d4 → 0d5375e0 → 75a621a1 → b3f76ee7.

| Апстрим-SHA | Файл | Способ | Проверка |
|---|---|---|---|
| 8e8be3d4 | modules/llm_pricing.py | ЦЕЛИКОМ из тега | blob == `v1.10.372:modules/llm_pricing.py` (`410509e9`) |
| 8e8be3d4 | modules/pricing.json | ЦЕЛИКОМ | blob == `c78168e8` |
| 0d5375e0 | modules/chat_backend.py | ЦЕЛИКОМ | blob == `f5c855d2` |
| 0d5375e0 | modules/llm_pricing.py | (уже покрыт выше) | — |
| 75a621a1 | modules/unified_prompt_manager_qt.py | ЦЕЛИКОМ | blob == `073a1cc5` |
| b3f76ee7 | modules/platform_helpers.py | ЦЕЛИКОМ | blob == `d751aff6` |

После U1.1: `py_compile` 135/135; `git diff --stat 7b895c93` — ровно 5 ожидаемых файлов; EOL всех — `i/lf w/lf` (не изменились).

---

## 3. U1.2 — что сделано (коммит `f5c460e9`)

Порядок строго: f5bfefc9 → 626d4c63 → da403a48.

### 3.1 Апстрим-SHA → файлы

| Апстрим-SHA | Файл | Способ |
|---|---|---|
| f5bfefc9 | modules/llm_clients.py, pdf_rescue_Qt.py, prompt_assistant.py | ЦЕЛИКОМ из тега (blob == v1.10.372: `3df9259b`, `9e0f44e1`, `351d294a`) |
| f5bfefc9 | Supervertaler.py — 5 мест | вручную, по методам (§3.2) |
| f5bfefc9 | modules/settings_service.py — дефолт `claude_model` | вручную |
| 626d4c63 | modules/keyboard_shortcuts_widget.py | ЦЕЛИКОМ (blob == `6d723a29`) |
| 626d4c63 | Supervertaler.py — `_save_general_settings_from_ui` + 4 AHK-сайта | вручную (§3.3) |
| 626d4c63 | modules/settings_service.py — комментарий S2.2 | вручную |
| 626d4c63 | VALIDATION_BACKLOG.md — запись #26 | вручную (docs) |
| da403a48 | modules/llm_clients.py | ЦЕЛИКОМ (финальное состояние тега включает и f5bfefc9) |
| da403a48 | Supervertaler.py — `__init__`, `_apply_ollama_timeout_setting` (новый), `_create_ai_settings_tab`, `_save_ai_settings_from_ui` | вручную (§3.4) |
| da403a48 | FAQ.md | ПРОПУЩЕН (в Portable нет, вопрос Q2) |

### 3.2 f5bfefc9 — монолит (до → после)

| Метод (класс подтверждён AST) | Изменение |
|---|---|
| `SupervertalerQt._create_ai_settings_tab` | claude_combo: список `sonnet-5/haiku-4.5/opus-5/fable-5` → `sonnet-5-5 (Recommended)/opus-5-5/fable-5-1`; новый tooltip ($2/$10, $4/$20); дефолт `claude-sonnet-5` → `claude-sonnet-5-5`; выбор сохранённой модели — **точное сравнение** `itemText(i).split()[0] == current` вместо подстроки; `for…else` добавляет `"{id} (your current model)"`, если модель ушла из списка. + friendly-словарь: добавлены `claude-sonnet-5-5/opus-5-5/fable-5-1`, старые ID сохранены |
| `SupervertalerQt._create_mt_quick_lookup_settings_tab` | `llm_providers` claude-список → 3 новых ID; восстановление `saved_model`: `findData<0` → append `"{saved} (your current model)"` с setData (было: молча не выбирать → перезапись при сохранении) |
| `SupervertalerQt._add_mt_and_llm_matches` | дефолт `settings.get('claude_model', 'claude-sonnet-5')` → `'claude-sonnet-5-5'` |
| `SettingsService.load_llm_settings` (modules/settings_service.py) | дефолт `'claude_model': 'claude-sonnet-5'` → `'claude-sonnet-5-5'` (монолитный делегат @56913 — тонкий, собственных дефолтов не держит — проверено) |

**Конфликтные пары подстрок (для T2.4):** `claude-sonnet-5` ⊂ `claude-sonnet-5-5`; `claude-opus-5` ⊂ `claude-opus-5-5`; `claude-fable-5` ⊂ `claude-fable-5-1`.

### 3.3 626d4c63 — монолит

| Метод | Изменение |
|---|---|
| `SupervertalerQt._save_general_settings_from_ui` | `general_settings = {` → `general_settings = dict(existing_settings)` + `general_settings.update({…})` (закрытие `}` → `})`); комментарий апстрима перенесён; все ~40 ключей литерала Portable сохранены 1:1 |
| `SuperlookupTab._find_autohotkey_executable` | чтение `main_window.general_settings.get('autohotkey_path',…)` (атрибут не существует) → `(main_window.load_general_settings() or {}).get('autohotkey_path', …)`, guard `hasattr(…,'load_general_settings')` |
| `SuperlookupTab._show_autohotkey_setup_dialog.on_close` | `general_settings['hide_autohotkey_dialog']=True; save_general_settings()` (TypeError) → `settings = load_general_settings() or {}; settings['hide_autohotkey_dialog']=True; save_general_settings(settings)` |
| `SuperlookupTab._browse_for_autohotkey` | то же для `autohotkey_path` |
| `SuperlookupTab._register_hotkey_external_script` | чтение `hide_autohotkey_dialog` через `load_general_settings()` |

`modules/keyboard_shortcuts_widget.py` (ЦЕЛИКОМ): чтение пути AHK через `mw.load_general_settings()` вместо несуществующего `mw.general_settings`.

Docs: `VALIDATION_BACKLOG.md` #26 → CLOSED (ссылка на сценарий T2.4); комментарий в `settings_service.py` (оговорка «предсуществующие сайты… не чинятся здесь») обновлён.

### 3.4 da403a48 — монолит

| Метод | Изменение |
|---|---|
| `SupervertalerQt.__init__` (хвост блока Ollama) | + `self._apply_ollama_timeout_setting()` после `self._setup_ollama_keepwarm()` |
| `SupervertalerQt._apply_ollama_timeout_setting` | **новый метод** (между `_setup_ollama_keepwarm` и `_start_ollama_keepwarm_timer`): `set_ollama_timeout(minutes*60)` из `llm_settings['ollama_timeout_minutes']` (0 = автоматический), try/except с `self.log` |
| `SupervertalerQt._create_ai_settings_tab` | после keepwarm-чекбокса: UI-строка «Request timeout» (QSpinBox 0–1440 мин, «Automatic», tooltip #180); kwarg `ollama_timeout_spin=ollama_timeout_spin` в вызове `_save_ai_settings_from_ui` |
| `SupervertalerQt._save_ai_settings_from_ui` | сигнатура + `ollama_timeout_spin=None`; `new_settings = {…}` → `new_settings = dict(existing_settings)` + `new_settings.update({…})`; после update: `new_settings['ollama_timeout_minutes'] = ollama_timeout_spin.value()` (если спин передан); + `self._apply_ollama_timeout_setting(new_settings)` после `save_llm_settings` |

**Проверка наборов ключей (по заданию):** `existing_settings = self.load_llm_settings()` (rel-строка 47 метода, обе версии) возвращает сохранённый `ui.llm_settings` **включая** `custom_mt_profiles`/`custom_mt_active_profile` (дефолты: `settings_service.py:244–266`); `update()` добавляет только перечисленные ключи + `ollama_timeout_minutes` → `custom_mt_*` сохраняются, лишние производные ключи не появляются (подтверждено headless-прогоном, §4.4).

После U1.2: `py_compile` 135/135; `git diff --stat a7746d65` — ровно 7 ожидаемых файлов (193+/105−); EOL не изменились.

---

## 4. Статическая валидация

### 4.1 AST-проверки (скрипт `D:\Temp\SupervertalerPortable\refactoring\u1-port\validate_u1.py`)
- **(а)** Вызовов `save_general_settings()` без аргументов во всём Portable: **0** (AST по монолиту + все modules).
- **(б)** Все изменённые методы в ожидаемых классах: `_create_ai_settings_tab`, `_create_mt_quick_lookup_settings_tab`, `_add_mt_and_llm_matches`, `_save_general_settings_from_ui`, `_save_ai_settings_from_ui`, `_apply_ollama_timeout_setting` → `SupervertalerQt`; `_find_autohotkey_executable`, `_browse_for_autohotkey`, `_register_hotkey_external_script` → `SuperlookupTab`. Совпадение множеств классов — OK (ловушка одноимённого `SuperlookupTab.create_settings_tab`/`_SearchTermHighlighter.highlightBlock` не сработала).
- **(в)** Diff `settings_service.py` vs 7b895c93: ровно 8 строк — дефолт `claude_model` (±2) и комментарий об оговорке S2.2 (±6). Логика/сигнатуры не тронуты.
- **(г)** AST-сигнатуры всех 26 методов `SettingsService` до/после — **идентичны**.
- **(д)** Все `from modules.<X> import <имя>` по всему Portable разрешаются в изменённых модулях — битых импортов 0.

### 4.2 Blob- и EOL-проверки
- 9 файлов «ЦЕЛИКОМ» — blob равен `v1.10.372:<path>` (список хэшей в §5).
- EOL всех 12 затронутых файлов до и после: `i/lf w/lf` — не изменились.

### 4.3 Тесты апстрима — 36/36 PASS
`tests/test_llm_pricing.py`, `test_chat_backend_cost.py`, `test_ollama_timeout.py`, `test_altgr_hotkeys.py` (все — только `modules.*`, монолит не импортируют) запущены из временной копии вне репо (`D:\Temp\SupervertalerPortable\refactoring\u1-port\repo-sim\`, junction на `modules/`; `E:\Dev\python-embed\python.exe -m pytest … -q`):
```
36 passed in 1.34s
```
(pytest установлен в bundled-рантайм; в репо `tests/` НЕ добавлялся.)

### 4.4 Headless-проверка логики фиксов настроек — PASS
Реальный `SettingsService` на временной папке вне репо (без Qt; скрипт `headless_settings_check.py`): секция `general` с 14 ключами + `llm_settings` с `custom_mt_profiles`:
- T2.1-логика: 14 ключей переживают `dict(existing)+update` + `save_general_settings` → **PASS**;
- T2.2-логика: `custom_mt_profiles`/`custom_mt_active_profile` переживают `dict(existing)+update` + `save_llm_settings` → **PASS**;
- `ollama_timeout_minutes` персистится → **PASS**;
- перекрёстно: Save AI не трогает general, Save General не трогает llm_settings → **PASS**.

### 4.5 py_compile — 135/135 (после каждого коммита).

---

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

Baseline сборки: коммит `7b895c93`. Файлы заменяются целиком поверх рабочей сборки.

### Пакет A — U1.1 (коммит `a7746d65`, поверх baseline)
| № | Путь | SHA256 | Примечание |
|---|---|---|---|
| 1 | `modules/llm_pricing.py` | `a5a489a2281ffab1d3de2a1acb63f26b16a1e25c197de3e7fb76c4c7983dc012` | цены + None-cost; blob == апстрим v1.10.372 |
| 2 | `modules/pricing.json` | `e3c62767fab39e729b34ba977c8d7e9b4d8eee6c79b699d43b052ca99f26ff01` | blob == апстрим |
| 3 | `modules/chat_backend.py` | `9b3b19087ffea688cd71ecdcd77bf8ef9f1a31d8865ccd82d0a6e0b62d99bf53` | «cost unknown»; blob == апстрим |
| 4 | `modules/unified_prompt_manager_qt.py` | `34e4a969b2f2de09bc086da4361c725ca07b177876276a3e3a208bd47427f43d` | TM/termbase-контекст; blob == апстрим |
| 5 | `modules/platform_helpers.py` | `fd2eb0abc54c0f70f55357baa44bdd97d2e7ef497ca85e7cb0df5a2c6b8c6d99` | AltGr; blob == апстрим |

### Пакет B — U1.2 (коммит `f5c460e9`, поверх Пакета A)
| № | Путь | SHA256 | Примечание |
|---|---|---|---|
| 6 | `Supervertaler.py` | `82d2e5d56fe2bd7db9daabdf324907b2799716c44b94ade51de05dc5899d1531` | ручные правки f5bfefc9/626d4c63/da403a48 (68 286 строк) |
| 7 | `modules/settings_service.py` | `4770acaab14d1706ba05a335c7fbcf80f0479fac52b7b05a19099f909f874e32` | только дефолт `claude_model` + комментарий |
| 8 | `modules/llm_clients.py` | `3df9259bfaa3dc4248489c4928113a1ff6fb583af704346e7ca4169ec6f9dbec` | модели + `set_ollama_timeout`; blob == апстрим |
| 9 | `modules/pdf_rescue_Qt.py` | `9e0f44e109ea3b6ed38a54d467a091953a32bfc105e60a2dee085120719241d1` | blob == апстрим |
| 10 | `modules/prompt_assistant.py` | `351d294ab6f11efbda47864b3b4e9b7b793b4610f5ad1565fdb007d1a4405433` | blob == апстрим |
| 11 | `modules/keyboard_shortcuts_widget.py` | `6d723a2903a64436bd76fe40bc818f0c8811cad950cccef11d02c492fbec2f4c` | AHK-путь; blob == апстрим |

**Файл настроек** (путь из `SettingsService`, конструируется в `Supervertaler.py:6306`): `<user_data>/workbench/settings/settings.json` — единый JSON с секциями `api_keys`/`general`/`ui`/…; LLM-настройки живут в `ui.llm_settings` (`custom_mt_profiles`, `custom_mt_active_profile`, `ollama_timeout_minutes`, `claude_model`, …), общие — в секции `general` (14 ключей из T2.1 там же). `<user_data>` — каталог из `~/.supervertaler_config.json` (на тестовой сборке — свой изолированный).

---

## 6. СЦЕНАРИИ ПРОВЕРКИ (на тестовой сборке, вручную)

Каждый сценарий — сначала КОНТРОЛЬ на baseline `7b895c93` (дефект виден), затем после замены файлов. Логические части T2.1–T2.3/T2.6 уже подтверждены headless (§4.4); ниже — UI-проверки.

**U1.1:**
- **T1.1** Чат (AI Assistant) с локальной моделью без записи о цене (custom OpenAI → KoboldCPP/LM Studio): сообщение уходит, в логе `cost unknown`. Контроль baseline: `unsupported format string passed to NoneType.__format__`, сообщение падает.
- **T1.2** Включить «include TM data»/«include termbase data» в чате: в промпт попадают активные TM проекта (имена + счётчики + совпадения для выбранного сегмента) и термины, встречающиеся в документе. Где увидеть: системный промпт/лог ChatBackend (`[ChatBackend] … chars`), текст запроса; на baseline — всегда «No translation memories loaded» / «No termbases loaded».
- **T1.3** Польская раскладка, глобальный хоткей Ctrl+Alt+<буква>: AltGr+<буква> печатает польский символ («ł», «ć», «ó») в другом приложении; настоящий левый Ctrl+Alt+<буква> вызывает хоткей. Контроль baseline: символ не печатается нигде, хоткей съедает AltGr.
- **T1.4** Стоимость для `claude-sonnet-5-5` считается ($2/$10, cache-read ×0.1) — в usage-логе/оценках. Контроль baseline: модели нет в таблице → unknown/0.

**U1.2:**
- **T2.1** General: задать нестандартные значения 14 ключей (`batch_size`, `surrounding_segments`, `use_full_context`, `context_window_size`, `quicklauncher_context_percent`, `check_tm_before_api`, `check_tm_exact_only`, `lookup_delay`, `fuzzy_fixer_min_pct`, `fuzzy_fixer_max_pct`, `persist_usage_log`, `monthly_budget_usd`, `mt_quick_lookup` (страница QuickTrans), `superlookup_landing_tab`), нажать Save General → все 14 на месте в `<user_data>/workbench/settings/settings.json` (секция `general`). Контроль baseline: пропадают.
- **T2.2** Создать кастомный MT-профиль (QuickTrans → custom MT endpoint), нажать Save AI Settings → `ui.llm_settings.custom_mt_profiles`/`custom_mt_active_profile` на месте. Контроль baseline: удаляются каждым нажатием.
- **T2.3** Перекрёстно: Save AI не меняет секцию `general`; Save General не меняет `ui.llm_settings`.
- **T2.4** SuperLookup AHK-диалог (без AutoHotkey в системе): путь сохраняется и подхватывается после рестарта; «Do not show this dialog again» сохраняется и работает; TypeError нет (виден в консоли/логе). Контроль baseline: «Saved» при пустом результате, диалог на каждом старте, TypeError при закрытии с галочкой.
- **T2.5** Списки моделей: в AI Settings — Sonnet 5.5 / Opus 5.5 / Fable 5.1; в QuickTrans — те же. Сохранённый ID выбирается точно: записать в settings `claude_model: claude-sonnet-5-5` → выбран Sonnet 5.5 (а не «первый подходящий по подстроке»); записать `claude_model: claude-sonnet-5` → показан «claude-sonnet-5 (your current model)», значение НЕ перезаписывается первым элементом. Пары с конфликтом подстрок: sonnet-5/5-5, opus-5/5-5, fable-5/5-1.
- **T2.6** Ollama timeout: Settings → AI → Local LLM (Ollama) Advanced Settings → «Request timeout» = 90 мин → Save → в `ui.llm_settings.ollama_timeout_minutes` = 90, переживает перезапуск (при старте `__init__` вызывает `_apply_ollama_timeout_setting`), применяется в llm_clients (таймаут реального запроса). «Automatic» = 0.
- **T2.7** Дымовой: приложение стартует, все страницы Settings открываются без исключений.

---

## 6.1 Результаты ручной проверки (тестовая сборка, Дмитрий, 2026-10-02)

Файлы пакетов A+B заменены поверх рабочей сборки согласно §5.

**Подтверждено:**

| Сценарий | Результат | Доказательство (лог тестовой сборки) |
|---|---|---|
| T1.1 | PASS | `[ChatBackend] LLM client: custom_openai/unsloth/qwen3.8-27b` → `Response: 339 chars, 1005 in / 217 out, cost unknown, 6.4s` — сообщение уходит, ответ получен, падения на None-cost нет |
| T1.2 (термины) | PASS | `✅ Enabled AI injection for termbase: 234`; в промпт попали термины termbase, модель их применила: `"Conrad Kinch" is mapped to "Иван Петрович"` → перевод сегмента использует «Иван Петрович» (`8304 in / 923 out, 27.8s`) |
| T2.1 | PASS | 14 ключей секции `general` на месте после Save General |
| T2.2 | PASS | `custom_mt_profiles`/`custom_mt_active_profile` на месте после Save AI Settings |
| T2.3 | PASS | Save AI не меняет `general`; Save General не меняет `ui.llm_settings` |
| T2.5 | PASS | Подтверждено (списки Sonnet 5.5/Opus 5.5/Fable 5.1, точный выбор сохранённой модели) |
| T2.7 | PASS | Приложение стартует, все страницы Settings открываются; при старте исполняется `_apply_ollama_timeout_setting` без ошибок |

**Не проверялось (фича не используется; риск принят):**

| Сценарий | Причина | Почему приемлемо |
|---|---|---|
| T1.3 (AltGr/польская раскладка) | раскладка не используется | Файл побайтно равен апстриму; поведение покрыто 36 юнит-тестами апстрима (фейковый keyboard) |
| T1.4 (стоимость платных моделей) | платные модели не используются | `llm_pricing.py`/`pricing.json` побайтно равны апстриму, тесты `test_llm_pricing.py` проходят |
| T1.2 (TM-часть) | проверена только термин-часть | `unified_prompt_manager_qt.py` побайтно равен апстриму |
| T2.4 (AHK-диалог) | диалог не найден, фича использоваться не будет | Файл побайтно равен апстриму; логика словарей покрыта headless-прогоном §4.4 |
| T2.6 (Ollama timeout, эффект) | Ollama не установлена | Вызов `_apply_ollama_timeout_setting` в `__init__` уже исполнен при старте (T2.7) без ошибок; непроверен только фактический эффект таймаута на реальный запрос |

*Иначе через месяц непроверенное сойдёт за проверенное — поэтому непроверенное перечислено явно, а не опущено.*

---

## 7. Непокрытые проверки

1. **Рантайм UI-сценарии T1.1–T1.4, T2.1–T2.7 изначально не выполнялись ИИ** (приложение по ТЗ не запускалось); headless-прогон покрывает только логику словарей §4.4, не UI-рутину целиком (чекбоксы/спины не существовали при прогоне). Часть сценариев затем выполнена Дмитрием на тестовой сборке — см. §6.1; непроверенное там перечислено явно.
2. **Монолитные правки не покрываются тестами апстрима** (36 тестов — только modules); корректность вставок в монолите подтверждена статически (py_compile + AST + построчное сравнение с апстримным диффом), но не исполнением.
3. **`_apply_ollama_timeout_setting` при старте** вызывается до создания UI — фактический порядок инициализации `llm_clients`/`load_llm_settings` в живом приложении не проверялся (статически: метод обёрнут try/except и не может уронить старт; `set_ollama_timeout` — модульный override без Qt).
4. **AltGr-поведение** проверено только юнит-тестами апстрима с фейковым keyboard; живой RegisterHotKey/SendInput на реальной раскладке не воспроизводился.
5. **FAQ.md** (документация Ollama timeout из da403a48) не перенесён — файла нет в Portable; вопрос Q2.
6. **EOL-поведение на Windows-чекaутах** Дмитрия может отличаться, если у него иные git-атрибуты (у нас `text=auto eol=lf`; blob-хэши это не зависящее от чекaута доказательство).

---

## 8. Вопросы к Дмитрию

1. **Q1 — push:** коммиты `a7746d65` (U1.1), `f5c460e9` (U1.2) и docs-коммит отчёта — пушить в origin сразу после вашего подтверждения?
   **→ ЗАКРЫТ (2026-10-02): подтверждено**, пуш выполнен после внесения поправок §6.1/§8.
2. **Q2 — FAQ.md:** добавить из тега (документация Ollama timeout, файл в Portable отсутствует с момента импорта) или пропустить окончательно?
   **→ ЗАКРЫТ (2026-10-02): пропущен окончательно** — необходимости нет.
3. **Q3 — pytest:** оставляем установленный в bundled-рантайм pytest (нужен для будущих прогонов тестов апстрима) или сносим?
   **→ ЗАКРЫТ (2026-10-02): оставляем.** pytest остаётся в bundled-рантайме (вне репо; в `tests/` репо не добавлялся).
4. **Q4 — очерёдность:** следующие под-батчи U1.3 (фиксы TM/тегов/хоткеев) — после вашего прогона T-сценариев на тестовой сборке или параллельно? **→ ОТКРЫТ** (прогон частично выполнен, §6.1; момент старта U1.3 — на усмотрение Дмитрия).

---
*Артефакты: `D:\Temp\SupervertalerPortable\refactoring\u1-port\` — диффы семи коммитов (`f5_mono.diff`, `626_mono.diff`, `da4_mono.diff`, `626_ksw.diff`, `f5_modules.diff`, `da4_llm_clients.diff`), `validate_u1.py`, `headless_settings_check.py`, `repo-sim/tests/` (копии тестов апстрима).*
