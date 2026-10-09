# ОТЧЁТ Batch #8.11 — микро-батч «Trados-чип»: удаление чипа «🔗 Trados» и trados_bridge_client

Кодовый коммит: **d308a93f** «Batch #8.11: remove Trados chip and trados_bridge_client» —
`modules/chat_view_widget.py` 1155 → 1026 (−129), `modules/unified_prompt_manager_qt.py`
6861 → 6835 (−26), `modules/trados_bridge_client.py` удалён (524). Суммарно 3 файла, −679 строк.
База кода: **5a29d3c9** (Batch #8.9), HEAD перед правкой — 40441230 (docs-коммит 8.9 §9).

Основание: BATCH8_7_IDENTITY_BRIDGE_REPORT.md §1.4 (микро-проверка чипа, решение 12
«удалять отдельным микро-батчем после 8.9»), BATCH8_9_CAT_FORMATS_REPORT.md (протокол).

## 0. Baseline и git-синхронизация

| Проверка | Результат |
|---|---|
| `git fetch origin` | HEAD = origin/main = **40441230** |
| `git status` | чисто (untracked `.zcode/plans/…md`, `.zcodeignore` — допустимы) |
| Дрейф-чек `git merge-base --is-ancestor 5a29d3c9 HEAD` | **ANCESTOR OK** |
| SHA256 рабочей копии `Supervertaler.py` | **aab1f180e5789878c014d6042a0ee1a29c9e7bdf1d85dbb02e0722f3604f7644** (57 010 строк, 0 bare LF) — совпадает с базой 8.9 |
| `py_compile` всего репо (compileall) | exit 0, 0 ошибок |
| `modules/**/*.py` | **111** (git ls-files = filesystem) |
| Blob-хэши (git HEAD) | chat_view_widget `2cfcb4ff…` (1155), unified_prompt_manager_qt `073a1cc5…` (6861), trados_bridge_client `212d1031…` (524) |
| EOL (`git ls-files --eol`) | все три файла `i/lf w/lf attr=text=auto eol=lf` |

Базовые значения (Этап 0 п.5, артефакты в `D:\Temp\SupervertalerPortable\refactoring\b8-11\`):

- **(а) AST-резолв self-вызовов** (`chain_resolve.py before`): ChatViewWidget — **24 метода**
  (BFS от `__init__`/`_init_ui`/`_init_context_chips`/`_on_chip_toggled`/`_do_send`/`_send_message`
  + trados-методы), UnifiedPromptManagerQt — **16 методов** (от `_context_aware_send`);
  неразрешённых self-вызовов — **2** (предсуществующие, охраняемые: `_context_aware_send →
  _update_active_prompt_display` (hasattr-guard в коде), `log_message → log` (атрибут parent_app)).
- **(б) pyflakes**: репо — **149 undefined-name** (множество идентично 8.9-after),
  chat_view_widget — 4 предупреждения (unused imports `io.BytesIO`, `QFont`, `QAction`,
  `QSizePolicy` — предсуществующие), unified_prompt_manager_qt — 21 (f-string/redefinition —
  предсуществующие).
- **(в) offscreen-проба ДО** (`probe_window_811.py`, изолированный профиль, offscreen):
  окно строится; main_tabs **6**; Settings **14**; чипы Chat (2 инстанса, порядок раскладки):
  `Context: | doc | tm | termbase | files | trados | stretch` — чип trados **скрыт**
  (`setVisible(False)`, avail=False); счётчики: chatview QTimer=0/QThread=0 (thinking-таймер
  не создан), POLLER singleton **present, QTimer=1, avail=False**, CLIENT present;
  QThreadPool active=0; S-clean дерево **28 записей**; S-upgrade hash-diff **пустой**
  (added=[] removed=[] changed=[]; транзитный `db-shm` печатается отдельно).
- **(г) сборка промпта ДО** (`prompt_capture.py` в worktree HEAD, подставной LLM-клиент,
  перехват `send_ai_request`): 3 запроса (A — `_do_send` напрямую; B — `_send_message` с
  включёнными tm/termbase/files; C — прямой `_context_aware_send`), payload sha256
  **fe08637c723e26290d977e35df6944c9b2889f4053468e007132dad28901f236**.
  system_prompt всех трёх — без TRADOS-блока (плагин недоступен → prepend не срабатывает).

## 1. Рекон (без правок)

### 1.1 Таблица зон (текущий код = таблица §1.4 отчёта 8.7, **расхождений нет**)

| # | Файл:диапазон | Строк | Метод/блок | Вызыватели | Охрана |
|---|---|---|---|---|---|
| Z1 | chat_view_widget.py:835–859 | 25 | `_fetch_trados_context_for_prompt` | `_do_send` (815) | try/except на каждом шаге |
| Z2 | chat_view_widget.py:811–817 | 7 | prepend trados-блока в `_do_send` | `_send_message` → `_do_send` | `if trados_block:` |
| Z3 | chat_view_widget.py:425–431 | 7 | ветка `key == "trados"` в `_on_chip_toggled` | `btn.toggled` лямбда (323) | — |
| Z4 | chat_view_widget.py:401–411 | 11 | `_get/_set_trados_chip_pref` | Z1, Z3, Z5 | `getattr(app, …, "auto")`, `if app is not None` |
| Z5 | chat_view_widget.py:364–399 | 36 | `_on_trados_availability_changed` | подписки poller (350,355), стартовый вызов (362) | — |
| Z6 | chat_view_widget.py:332–362 | 31 | singleton `_trados_bridge`/`_trados_poller`, подписки, стартовое применение | `_init_context_chips` | — |
| Z7 | chat_view_widget.py:309 | 1 | чип `("trados", "🔗 Trados", False)` | список chips | — |
| Z8 | chat_view_widget.py:23–27 | 5 | import `TradosBridgeClient/Poller/format_context_for_prompt` | — | — |
| Z9 | unified_prompt_manager_qt.py:6380–6381 | 2 | prepend `trados_block` | `_context_aware_send` | `if trados_block:` |
| Z10 | unified_prompt_manager_qt.py:6337–6358 | 22 | trados-блок в `_context_aware_send` | monkey-patch `_do_send` (1219,1520,2163) | import в try/except, `getattr(pref,…)`, `if client.is_available()` |

Итого **147 строк** (совпадает с §1.4 8.7). В вырез включены по одной пустой строке после
блока (Z1–Z6, Z9–Z10) и пустая строка import-шва (Z8) — всего 155 строк выреза.

### 1.2 Чипы Chat

Список строится в `_init_context_chips` (цикл по `chips`, порядок = порядок в списке,
`addStretch()` после цикла). Обращений к чипам **по индексу нет** — только по ключу
(`self._context_toggles[key]` в popover'ах tm/termbase/files и `setChecked` в `_attach_file`).
Удаление элемента из списка не сдвигает индексы остальных (раскладка — последовательная
`addWidget`, растяжка в конце). `_on_chip_toggled` целиком: style + синхронизация pm
(`tm`/`termbase`) + trados-ветка (Z3). Состояние чипов нигде не персистится
(`get_context_state()` — 0 вызовов вне модуля, проверено grep).

### 1.3 Состояние/настройки

Pref чипа — **только in-memory атрибут** `parent_app._trados_chip_pref` (Z4); ключевых
файлов настроек нет. Чтения вне удаляемого кода: `unified_prompt_manager_qt.py:6346`
(`getattr(self.parent_app, "_trados_chip_pref", "auto")` — в Z10, удаляется). Иных
читателей нет (grep по `_trados_chip_pref` — только 3 правимых файла). Ключи настроек
не появляются → инертных ключей не остаётся.

### 1.4 Отправка

`_do_send` (ДО, 803–833): prompt = user_text; system_prompt = базовая строка; Z2 prepend
trados-блока при `if trados_block:`. `_fetch_trados_context_for_prompt` возвращает `""`
при pref=="off", недоступном мосте, пустом ctx, любой исключении → **при недоступном
плагине prepend не добавляет ничего**. `_context_aware_send` (ДО, 6330+): Z10 блок
(try-import → pref → `client.is_available()` → fetch → format) + Z9 prepend. Ожидание
подтверждено регрессией (раздел 4): при недоступном плагине текст запроса не меняется.

### 1.5 Потребители удаляемых имён (grep по Supervertaler.py, modules/**, tools/**, tests/**)

Имена: `trados_bridge_client`, `TradosBridgeClient`, `TradosBridgePoller`,
`format_context_for_prompt`, `_trados_bridge`, `_trados_poller`,
`_on_trados_availability_changed`, `_get/_set_trados_chip_pref`,
`_fetch_trados_context_for_prompt`, `_trados_chip_pref`, `notify_pref_changed`.

| Имя | Место | Охрана | Действие |
|---|---|---|---|
| все выше | только chat_view_widget.py (Z1–Z8), unified_prompt_manager_qt.py (Z9–Z10), сам модуль | — | вырезаются |
| — | Supervertaler.py, tools/**, tests/**, прочие modules/** | — | **0 обращений** |

Неохраняемых обращений остающегося кода нет → СТОП-флага нет. `Supervertaler.py` не тронут.

### 1.6 Остаточный скан `trados`/`sdl`/`bridge` (301 совпадение в .py вне трёх файлов)

| Место | Что | Класс |
|---|---|---|
| Supervertaler.py ~250 строк (комментарии «конвенция memoQ/Trados», «Trados parity», regex `<1>/</1>` Trados-тегов, hotkey-комментарии Ctrl+Alt+T/Ctrl+Shift+P/H) | док-комментарии и общая функциональность подсветки/паритета тегов | **ДОК-ОСТАТОК** (docs-проход) / ЖИВОЕ (tag-regex — общие форматы, решение 8.9 №2) |
| Supervertaler.py:11245–11545 (Bridge-колонка TM, «Select All Bridge», tooltip'ы) | UI флага `bridged_to_trados` | **ДАННЫЕ ПО РЕШЕНИЮ** (см. 1.7) |
| Supervertaler.py:13699, 15114, 16955–16964, 19260, 19565, 21076 (комментарии о плагине) | док | ДОК-ОСТАТОК |
| modules/termlens_widget.py ~30, termbase_manager.py 4, statistics_dialog_qt.py 1, pseudo_translate.py 3, tools/extract_strings.py 1 | комментарии паритета с плагином + tag-regex | ДОК-ОСТАТОК / ЖИВОЕ (pseudo_translate — общие теги) |
| modules/superlookup.py:49,64 — режим `'trados'` (tag-extraction) | живой режим SuperLookup | **ЖИВОЕ ПОСЛЕ БАТЧА** (не трогать) |
| unified_prompt_manager_qt.py:2573,3158,3204 + unified_prompt_library.py:133 — `app_target` «Trados only» промптов | живой enum метаданных промптов | **ЖИВОЕ ПОСЛЕ БАТЧА** (кандидат финального инвентаря) |
| setup.py:91 keywords «Trados» | PyPI-метаданные | ДОК-ОСТАТОК (решение 8.9 №3 — оставить) |
| unified_prompt_manager_qt.py:61,4020,4029,4129,5705 (комментарии/дефолты prompt-текстов) | док | ДОК-ОСТАТОК |

Правок по этой таблице в батче нет (кроме удалённых зон).

### 1.7 TM-бридж `bridged_to_trados` / «Select All Bridge»

- Схема: `modules/database_manager.py:470–486` — колонка `bridged_to_trados` в
  `translation_memories` (миграция v1.10.212).
- Читает: `modules/tm_metadata_manager.py:146–178` (проекция для UI), пишет:
  `set_bridged_to_trados` (:653–681).
- UI: Supervertaler.py — колонка «Bridge» (индекс 5) в таблице TM (11311, 11514–11545),
  «Select All Bridge»/«Clear All Bridge» (11281–11288) + `toggle_all_bridge` (11372–11382).
- **Назначение**: флаг говорит внешнему Trados-плагину, какие TM плагину показывать.
  Единственный потребитель флага внутри Workbench — сам UI-чекбокс. Workbench-код
  (поиск, TM-подсказки, SuperLookup) флаг **не читает**; после удаления чипа/клиента
  в приложении не остаётся ничего, что его использует. Обслуживает ТОЛЬКО Trados-плагин.
- **Рекомендация (без правок, решение за Дмитрием)**: в финальном инвентаре сирот
  удалить UI-слой (колонка «Bridge», чекбоксы, bulk-кнопки, tooltip'ы — ~40 строк в
  `_create_tm_list_tab`), оставить колонку БД и `set_bridged_to_trados` (метод-сеттер
  инертен, миграция на удаление колонки не нужна; внешний плагин, если установлен,
  читает БД напрямую).

### 1.8 Фоновая активность

Poller (`trados_bridge_client.py:414–524`): синглтон-QObject с одним singleShot-QTimer,
интервал 3 с → бэкофф 10/30/60 с; воркер `_ProbeRunnable` через `QThreadPool.globalInstance()`
(не собственный QThread); localhost-HTTP `/_ping` к плагину по handshake-файлу
`<user_data>/trados/runtime/bridge.json` (пишет плагин). Chat-виджеты трогали только
сигналы. После удаления: модуля нет, синглтонов нет, QTimer-источника нет —
подтверждено пробой ПОСЛЕ (раздел 4): POLLER/CLIENT absent, счётчики 0, QThreadPool active=0.

### 1.9 Пакеты

`trados_bridge_client` импортирует: stdlib (json/os/sys/time/pathlib/typing) +
`requests` (try/except) + PyQt6.QtCore (try/except). `requests` остаётся нужным
`Supervertaler.py`, `modules/llm_clients.py`, `modules/local_llm_setup.py`,
`modules/okapi_sidecar.py` → **requirements.txt/pyproject не меняются** (только отчёт).

### 1.10 Контрольный список имён для защиты 2

См. 1.5 (11 идентификаторов + ключ `"trados"`). Допустимые остатки: строковые enum-значения
`'trados'` в superlookup-режиме и prompt `app_target` (не обращения к удалённым объектам).

## 2. Что сделано (один кодовый коммит d308a93f)

| Блок | Строки (ДО) | Действие |
|---|---|---|
| Z1 `_fetch_trados_context_for_prompt` | 835–860 (26) | вырез (снизу вверх) |
| Z2 prepend в `_do_send` | 811–818 (8) | вырез |
| Z3 ветка `key=="trados"` | 425–432 (8) | вырез |
| Z4 `_get/_set_trados_chip_pref` | 401–412 (12) | вырез |
| Z5 `_on_trados_availability_changed` | 364–400 (37) | вырез |
| Z6 poller-блок с подписками | 332–363 (32) | вырез |
| Z7 чип в списке | 309 (1) | вырез |
| Z8 import-блок | 23–28 (6) | string-replace (assert count==1) |
| Z9 prepend в `_context_aware_send` | 6380–6382 (3) | вырез |
| Z10 trados-блок в `_context_aware_send` | 6337–6359 (23) | вырез |
| `modules/trados_bridge_client.py` | 524 | `git rm` |
| PEP8: восстановлена вторая пустая строка перед `class ChatViewWidget` | — | string-replace |

SHA-guard: blob-хэши обоих файлов = HEAD перед правкой. Якоря первой/последней строки
каждой зоны проверены assert'ами. Снапшоты 10 зон с sha256 —
`D:\Temp\...\b8-11\snapshots\`; побайтовая сверка снапшотов с базой 40441230 —
**10/10 OK** (`verify_snapshots.py`).

Итог: chat_view_widget 1155 → **1026** (−129), unified_prompt_manager_qt 6861 → **6835**
(−26), модуль −524. Ориентир «≈−170 в двух модулях»: факт −155 (147 кодовых + 8 пустых
строк зон) — расхождение −8.8%, объяснено пустыми строками разделителей.
`git diff --stat`: только 3 ожидаемых файла. EOL после: `i/lf w/lf` (не изменился).
SHA256 (w/lf): chat_view_widget `6b4a3295b882488b0648d61783207dfb357467f0e52422615cadf8e0576b2115`,
unified_prompt_manager_qt `cd56aa486b3a8d15f9c23a803c584ea25fd93e251049c76e48844c555c870d05`.
`Supervertaler.py` — **без изменений** (SHA `aab1f180…` = база; потребители не найдены).

## 3. Диффы до/после

### 3.1 Построение чипов (`_init_context_chips`)

```diff
             ("files",     "\U0001F4CE Files",        False),
-            ("trados",    "\U0001F517 Trados",        False),
         ]
...
         self._context_chips_row.addStretch()
-
-        # Trados Supervertaler Bridge integration: ...
-        self._trados_bridge = TradosBridgeClient.shared()
-        ... (Z6: singleton, setVisible(False), подписки availability_changed/pref_changed,
-             стартовое применение current_state)
```

### 3.2 `_on_chip_toggled`

```diff
             elif key == "termbase":
                 pm.include_termbase_data = checked
-
-        # Trados chip: persist the explicit user preference ...
-        if key == "trados":
-            self._set_trados_chip_pref("auto" if checked else "off")
-            self._trados_poller.notify_pref_changed()
```

Ветки tm/termbase целы; метод заканчивается на pm-синхронизации.

### 3.3 `_do_send`

```diff
         system_prompt = "You are an AI assistant for Supervertaler, a professional translation tool."
-
-        # Trados-aware mode: prepend ...
-        trados_block = self._fetch_trados_context_for_prompt()
-        if trados_block:
-            system_prompt = trados_block + "\n" + system_prompt
 
         try:
             response, metadata = self._backend.send_ai_request(
```

### 3.4 `_context_aware_send`

```diff
         context = self._build_ai_context(user_text)
-
-        # Trados-aware mode: ...
-        trados_block = ""
-        try:
-            from modules.trados_bridge_client import TradosBridgeClient, format_context_for_prompt
-            ... (pref, client.shared(), is_available, fetch, format)
-        except Exception:
-            trados_block = ""
 
         # Choose system prompt
         system_prompt = """You are an AI assistant ..."""
-
-        if trados_block:
-            system_prompt = trados_block + "\n" + system_prompt
```

## 4. Валидация

| Проверка | ДО | ПОСЛЕ | Результат |
|---|---|---|---|
| py_compile всего репо | exit 0 | exit 0 | OK |
| Защита 1: AST-резолв self-вызовов (цепочки Chat/Prompt Manager) | 24+16 методов, 2 неразрешённых | **20+16 методов, те же 2 неразрешённых** (20 = 24 − 4 удалённых seed-метода) | 0 новых неразрешённых |
| Защита 2: grep по 11 удалённым идентификаторам + `"trados"` (Supervertaler.py, modules/**, tools/**, tests/**, строки/getattr/hasattr/connect/ключи) | — | **0 обращений**; 5 совпадений — строковые enum-значения `'trados'` (superlookup-режим ×2, prompt app_target ×3), не обращения к удалённым объектам (вывод: `protection2_grep.txt`) | OK |
| Защита 3: pyflakes | 149 undefined; 4/21 по модулям | **149 undefined (множество идентично, diff пуст)**, 4/21 (те же) | OK |
| AST: висячие подписки | POLLER avail/pref-подписки ×2 на виджет | подписок нет (модуль удалён, grep 0) | OK |
| Список чипов | doc/tm/termbase/files/**trados**/stretch | **doc/tm/termbase/files/stretch** (проба, порядок и checked остальных идентичны) | OK |
| Регрессия сборки промпта (A `_do_send`, B чипы+`_send_message`, C `_context_aware_send`; worktree HEAD vs репо, подставной LLM, перехват `send_ai_request`) | sha256 payload **fe08637c…** | sha256 payload **fe08637c…**, JSON **побайтово идентичен** (`diff prompt_before.json prompt_after.json` пуст) | 0 расхождений |
| Offscreen S-clean | окно/6 вкладок/14 страниц/чипы 5+trados/дерево 28/POLLER QTimer=1 | окно/6 вкладок/14 страниц/**чипы 4 без trados**/дерево **28**/POLLER-модуль absent, счётчики QTimer/QThread=0, QThreadPool active=0 | OK, фоновый опрос ушёл |
| Offscreen S-upgrade | hash-diff пустой | hash-diff **пустой** (added=[] removed=[] changed=[]; transient db-shm отдельно) | OK |
| Headless-импорт modules/** | 105 ok / 6 fail / 111 (tkinter×4, fitz, glossary_manager) | **104 ok / 6 fail / 110** — те же 6 предсуществующих, −1 = удалённый модуль | OK |
| wc -l | 1155 + 6861 + 524 | 1026 + 6835 + 0 | −679 |
| EOL | i/lf w/lf | i/lf w/lf | не изменился |

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ (база: код 5a29d3c9)

| № | Путь | Действие | SHA256 (w/lf) | Примечание |
|---|---|---|---|---|
| 1 | `SupervertalerPortable/modules/chat_view_widget.py` | **заменить** | `6b4a3295b882488b0648d61783207dfb357467f0e52422615cadf8e0576b2115` | 1026 строк |
| 2 | `SupervertalerPortable/modules/unified_prompt_manager_qt.py` | **заменить** | `cd56aa486b3a8d15f9c23a803c584ea25fd93e251049c76e48844c555c870d05` | 6835 строк |
| 3 | `SupervertalerPortable/modules/trados_bridge_client.py` | **УДАЛИТЬ** (обязательно) | — (был `212d1031…`, 524) | без удаления забытый импорт не проявится |
| 4 | `SupervertalerPortable/Supervertaler.py` | **без изменений** | `aab1f180e5789878c014d6042a0ee1a29c9e7bdf1d85dbb02e0722f3604f7644` | SHA как в базе 8.9 |

Перед заменой — контроль на базовой сборке (сценарии ниже), после — проверка.
`__pycache__` модуля в тестовой сборке удалить/пересобрать (старый кэш не помеха, но
для чистоты).

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data; сначала КОНТРОЛЬ на базовой сборке, затем после пакета)

Процедура чистого старта (из 8.8): бэкап `%APPDATA%\Supervertaler\config.json` и
`%USERPROFILE%\.supervertaler_config.json`, указатель на пустую папку, после проверки — восстановить.

- **T8.11.1** старт без исключений; вкладки открываются; в логе нет упоминаний trados/bridge.
- **T8.11.2** Chat: вкладка открывается; набор чипов = контрольный без «🔗 Trados»
  (он и раньше был скрыт без плагина); переключение каждого чипа (doc/tm/termbase/files)
  работает; раскладка без пустого места (stretch в конце).
- **T8.11.3** Chat: отправить сообщение в настроенный LLM (облачный или локальный) —
  ответ приходит; затем с включёнными чипами (контекст проекта и др.) — ответ приходит.
- **T8.11.4** Prompt Manager: открыть, запустить промпт с контекстом (путь
  `_context_aware_send`) — ответ приходит, без исключений.
- **T8.11.5** AI Assistant (если открывается из других мест) — без исключений.
- **T8.11.6** live-test на копии: импорт файла 180/400 сегментов, перевод сегмента,
  Save, навигация по всем вкладкам и 14 страницам Settings.
- **T8.11.7** выход: иконка трея исчезает, процесс завершается (0xC0000005 —
  предсуществующий флаки), в логе нет traceback.

## 7. Непокрытые проверки (честно)

1. Ручные сценарии T8.11.1–T8.11.7 — только на сборке Дмитрия (offscreen-пробы покрывают
   старт/чипы/счётчики, не интерактив и не живой LLM-обмен).
2. **Живой Trados-плагин не проверялся** — функция удалена; поведение с запущенным
   Studio+плагином (чип больше не появляется, плагин работает автономно) не тестировалось.
3. Регрессия промптов выполнена с подставным LLM-клиентом (перехват `send_ai_request`),
   с реальным облачным/локальным LLM — в T8.11.3/T8.11.4.
4. Состояние чипов не персистится (рекон 1.2) — проверка «сохранённое состояние других
   чипов не пострадало» покрыта статически (0 потребителей `get_context_state`) и пробой
   (CHIPSTATE view#0/1 идентичны ДО/ПОСЛЕ кроме отсутствия ключа trados).

## 8. Вопросы к Дмитрию

1. **TM-бридж** (рекон 1.7): `bridged_to_trados` + «Select All Bridge» + колонка «Bridge»
   в таблице TM — рекомендация: удалить UI-слой в финальном инвентаре сирот (~40 строк),
   оставить колонку БД и сеттер `set_bridged_to_trados` (внешний плагин читает БД сам).
   Подтвердить?
2. **Prompt `app_target` «Trados only»** (editor combo «Trados only», `app_value == 'trados'`
   в unified_prompt_library) — оставить как метаданные промптов (кандидат финального
   инвентаря)?
3. **superlookup-режим `'trados'`** (tag-extraction) — живая функция, оставляем (не трогали).
4. Док-остатки «Trados» в комментариях (~250+ строк, рекон 1.6) — в финальный docs-проход?

---

Артефакты: `D:\Temp\SupervertalerPortable\refactoring\b8-11\` — `implement_811.py`,
`snapshots\` (10 зон, sha256), `verify_snapshots.py` (10/10 OK vs 40441230),
`chain_resolve.py` + `chain_{before,after}.json`, `run_pyflakes.py` +
`undefined_names_{before,after}.txt` + `pyflakes_{before,after}.txt`,
`protection2_grep.txt`, `probe_window_811.py` + `probes\probe_{before,after}_{clean,upgrade}.log`,
`prompt_capture.py` + `prompts\{capture,prompt}_{before,after}.{log,json}`,
`headless_{before,after}.txt`, `py_compile_{before,after}.txt`,
`eol_{before,after}.txt`, `head-wt\` (worktree HEAD).

**Push — только после подтверждения Дмитрия.**
