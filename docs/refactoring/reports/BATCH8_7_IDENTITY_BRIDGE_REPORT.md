# Batch #8.7 — Удаление F3-III (User Identity) и F3-I (Trados bridge server), Этап 2

Дата: 2026-10-06. Исполнитель: Zcode (GLM). База: код 4988a0fb (Batch #8.5), docs 7a4197c2.
Кодовый коммит: **dc2e2838** «Batch #8.7: remove User Identity page and Trados bridge server (F3-III, F3-I)» — Supervertaler.py 65163 → 64979 (−184), `modules/supervertaler_bridge_server.py` удалён (357 строк), суммарно 2 файла +0/−541.

---

## 0. Baseline и git-синхронизация

| Проверка | Значение |
|---|---|
| git fetch origin | origin/main = `7a4197c2` |
| HEAD | `7a4197c2` (= origin/main) |
| git status | чисто; untracked `.zcode/plans/…`, `.zcodeignore` (допустимы) |
| Дрейф-чек | `git merge-base --is-ancestor 4988a0fb HEAD` → предок, ОК |
| SHA256 Supervertaler.py (рабочая копия, CRLF) | `f65e0e59bf24d992baab6060994f11cf518ac4b53f4ea2f0dedabc20cda05930` — совпал с ожидаемым |
| Строк Supervertaler.py | 65163 |
| EOL | `i/lf w/crlf` (предсуществующий, не тронут) |
| py_compile | сопоставимый объём 123/123 (122 модуля + монолит); весь репозиторий 140/140 |
| Защита (а) baseline | startup-chain resolve: 912 вызовов, 0 неразрешённых |
| Защита (б) baseline | pyflakes: 149 уникальных undefined names — множество **идентично** 8.5-after |
| Защита (в) baseline (offscreen-проба) | main_tabs 6; страниц Settings 15 (включая «👤 User Identity»); `window bridge attrs: ['_bridge_server', '_on_bridge_prompt_request']`, `_bridge_server = SupervertalerBridgeServer`; QTimer 3, QThread 0; Trados-кнопок 3 |

Артефакты: `D:\Temp\SupervertalerPortable\refactoring\b8-7\` — `probe_before.log`, `startup_chain_before.json`, `undefined_names_before.txt`, `un_before_sorted.txt`, `iso-before/`.

Примечание о детекте bridge: сервер пишет свой лог только в файл `<user_data>/workbench/runtime/sidekick-bridge.log` (не в stdout), а порт выбирает ядро (`port 0` → случайный высокий) — поэтому факт создания сервера в offscreen-пробе фиксировался по атрибуту окна `_bridge_server` (до: создан; после: отсутствует).

## 1. Рекон (Этап 1)

### 1.1 Таблица имён (AST + grep по всему репо)

| Имя | Файл:место | Вид | Класс self | Только F3? | Действие |
|---|---|---|---|---|---|
| `_create_user_identity_tab` | Supervertaler.py:24433–24494; вызов :20252 | метод + вызов | SupervertalerQt | да | удалено (зона A, B) |
| `_save_user_identity_from_ui` | Supervertaler.py:24496–24505; вызов :24490 (lambda) | метод + connect | SupervertalerQt | да | удалено (зона A) |
| регистрация «👤 User Identity» | Supervertaler.py:20251–20253 | addTab | — | да | удалено (зона B) |
| `_on_bridge_prompt_request` | Supervertaler.py:7595–7678; connect :9866–9868 | метод + connect | SupervertalerQt | да | удалено (зоны C, D) |
| `_bridge_server` | Supervertaler.py:9862–9870 | атрибут + жизненный цикл | SupervertalerQt | да | удалено (зона C) |
| `SupervertalerBridgeServer` | modules/supervertaler_bridge_server.py (весь, 357 строк); импорт монолита :9864 | модуль/класс | — | да (единственный импортер — монолит) | git rm |
| `translator_name` (ключ `general.translator_name`) | чтение :24471 (страница), :36594 (`get_translator_name`); запись :24499 (только страница) | ключ настроек | — | писатель удаляется, читатель остаётся (B1) | ключ ОСТАВЛЕН (орфанный) |
| `get_translator_name` | Supervertaler.py:36591–36597 | метод | SupervertalerQt | нет — B1 | ОСТАВЛЕН |
| `sidekick-bridge.json` / `sidekick-bridge.log` | модуль сервера | handshake/лог-файлы | — | да | удаляются вместе с модулем; **данные user_data не тронуты** |

Внешних потребителей удалённых имён вне монолита нет: grep по `modules/**`, `tools/**` — 0 (keyboard_shortcuts_widget, help_system, shortcut_manager, tools/ чистые). В `docs/**` остаются только документационные упоминания (см. §7).

### 1.2 Bridge server: как работал

- Класс `SupervertalerBridgeServer(QObject)` (modules/supervertaler_bridge_server.py), создавался в `create_main_layout` (9853–9872): try/except, `run_prompt_requested` → `_on_bridge_prompt_request`, `start()`, `QApplication.instance().aboutToQuit.connect(stop)`.
- Слушал `http://127.0.0.1:<случайный высокий порт>` (bind `port 0`, до 10 попыток), поток `threading.Thread(daemon=True)` name=`SupervertalerBridge` (не QThread — поэтому QThread=0 в пробах). Токен: `secrets.token_hex(16)`, Bearer-авторизация.
- Endpoint `POST /v1/run-prompt` (+ `GET /v1/ping` без авторизации); писал handshake `<user_data_root>/workbench/runtime/sidekick-bridge.json` (port+token+pid), удалял его на `stop()`. `user_data_root` — из глобального указателя `%APPDATA%\Supervertaler\config.json` (зеркало монолитного резолва; **не** профиль приложения).
- Порт/хост из настроек не читались (только случайный bind) — ключей настроек bridge в конфиге нет; сирот-ключей не образуется.
- Получатель данных: `_on_bridge_prompt_request` → `_bring_workbench_forward()`, переключение на вкладку AI → под-вкладка Chat (лейбловый поиск), `prompt_manager_qt.chat_backend`: `add_message("user", …)` + `send_ai_request(expanded, system_prompt)`.
- Обратных ссылок Chat/Prompt Manager на bridge server **нет** (проверено grep: chat_view_widget.py, unified_prompt_manager_qt.py не упоминают supervertaler_bridge_server/SupervertalerBridgeServer) — при удалении висячих ссылок не образуется.

### 1.3 User Identity: читатели translator_name и фолбэк

Писатель ключа был **единственный** — `_save_user_identity_from_ui` (:24499). Все читатели:

| Место | Код | Назначение |
|---|---|---|
| Supervertaler.py:10059 (`open_tmx_editor_window`) | `tmx_editor.translator_name = self.get_translator_name()` | TMX Editor |
| Supervertaler.py:13573 (`_comment_author_and_initials`) | `author = self.get_translator_name()` | автор DOCX-комментариев + инициалы |
| Supervertaler.py:7434–7435 (диалог добавления комментария) | `self.get_translator_name() if hasattr(...)` | автор комментария сегмента |
| Supervertaler.py:36837 (SDLPPX return package) | `self.sdlppx_handler.username = self.get_translator_name()` | Trados return package |
| Supervertaler.py:37444 (SDLXLIFF export) | `handler.username = self.get_translator_name()` | SDLXLIFF handler |
| Supervertaler.py:51914 (attach DOCX comments) | `author=self.get_translator_name() if hasattr(...)` | автор DOCX-комментариев |
| modules/tmx_editor.py:706, modules/tmx_editor_qt.py:956 | `getattr(self, 'translator_name', '') or os.getlogin()` | default creator TMX (вторичный фолбэк) |

Фолбэк `get_translator_name` (не менялся, Supervertaler.py:36591–36597):

```python
def get_translator_name(self) -> str:
    """Возвращает настроенное пользователем имя переводчика, с откатом к имени пользователя системы."""
    settings = self.load_general_settings()
    name = settings.get('translator_name', '').strip()
    if name:
        return name
    return os.environ.get('USERNAME', os.environ.get('USER', 'user'))
```

После удаления страницы ключ существующими пользователями сохраняется и продолжает работать; новые пользователи получают системное имя пользователя. `settings_service.py` сирот по User Identity **не содержит** (страница работала через `load_general_settings`/`save_general_settings`) — файл не менялся.

### 1.4 МИКРО-ПРОВЕРКА чипа «🔗 Trados» (решение 12)

**РЕШЕНИЕ: ЧИП И modules/trados_bridge_client.py ОСТАВЛЕНЫ (не удалять).** Правило из промпта: удалять только если суммарно до ~40 строк в обоих файлах. Факт — **~147 строк**:

| Файл:место | Строк | Что | Охрана |
|---|---|---|---|
| chat_view_widget.py:23–27 | 5 | import TradosBridgeClient/Poller/format_context_for_prompt | — |
| chat_view_widget.py:309 | 1 | чип `("trados", "🔗 Trados", False)` в списке | — |
| chat_view_widget.py:332–362 | 31 | `_trados_bridge`/`_trados_poller` singleton, подписки `availability_changed`/`pref_changed`, стартовое применение состояния | все вызовы в try/except или getattr-дефолты |
| chat_view_widget.py:364–399 | 36 | `_on_trados_availability_changed` (видимость/чек/тултип чипа) | — |
| chat_view_widget.py:401–411 | 11 | `_get/_set_trados_chip_pref` (pref на parent_app) | `getattr(app, …, "auto")`, `if app is not None` |
| chat_view_widget.py:425–431 | 7 | ветка `key == "trados"` в `_on_chip_toggled` | — |
| chat_view_widget.py:811–817 | 7 | prepend trados-блока в `_do_send` | — |
| chat_view_widget.py:835–859 | 25 | `_fetch_trados_context_for_prompt` | try/except на каждом шаге |
| unified_prompt_manager_qt.py:6337–6358 | 22 | trados-блок в `_context_aware_send` | import в try/except, `getattr(pref, …)`, `if client.is_available()` |
| unified_prompt_manager_qt.py:6380–6381 | 2 | prepend | — |

Видимость чипа без плагина: чип создаётся скрытым (`setVisible(False)`, chat_view_widget.py:345) и показывается только после первого `availability_changed(True)` — **без запущенного плагина чип не виден**.

Poller: `TradosBridgePoller` — синглтон, QTimer(singleShot) + `QThreadPool` воркер (`_ProbeRunnable`), **не** собственный QThread; интервал 3 с → бэкофф 10/30/60 с при недоступности (chat_view_widget трогает только сигналы). Запросы — на localhost к **плагину**, охрана полная (`probe_blocking` в try/except).

Дополнительный факт (снимает опасение зависимости): клиент читает **чужой** handshake — `<user_data_root>/trados/runtime/bridge.json`, который пишет сам Trados-плагин (trados_bridge_client.py:77–79). Handshake `workbench/runtime/sidekick-bridge.json` пишется только удаляемым сервером. Клиент и сервер — независимые «встречные» мосты: удаление сервера не влияет на чип/клиент/плагин. Оставшийся клиент после 8.7 продолжает опрашивать плагин как раньше.

### 1.5 Страницы Settings: регистрация и индексы

- Навигация лейбловая: `_switch_settings_subtab` (:27300) и её потребители (:60360 `_open_mt_settings`, :54219) ищут подстроку в `tabText(i)` — числовых индексов мимо удалённой страницы нет.
- Хранимые индексы вычисляются в момент построения от `settings_tabs.count() - 1` (`mt_quick_lookup_tab_index` :20278, `keyboard_shortcuts_tab_index` :20315) — пересчитываются сами при каждой сборке окна; сохранённое состояние страницы Settings не персистится (выбранная страница не пишется в конфиг).
- Страница «👤 User Identity» была 4-й (index 3) из 15; после удаления — 14 страниц (подтверждено пробой).

### 1.6 Контрольный список остатков (допустимые)

`get_translator_name` и его 6 вызовов (B1); ключ `general.translator_name` (орфанный, читается фолбэком); TM-колонки `bridged_to_trados` / «Select All Bridge» (функция бриджинга ТМ — не F3-I); чип «🔗 Trados» + `modules/trados_bridge_client.py` (решение 12 — оставить); `sidekick-bridge.json/.log` в данных user_data (не трогать); док-остатки (конец Batch #8).

## 2. Что сделано

| Файл | Действие | Детали |
|---|---|---|
| Supervertaler.py | удалены 4 зоны (−184 строки) | A 24433–24506 (74): `_create_user_identity_tab` + `_save_user_identity_from_ui`; B 20251–20254 (4): регистрация страницы «👤 User Identity»; C 9853–9873 (21): комментарий + создание `_bridge_server` + connect + `aboutToQuit` + except-лог; D 7595–7679 (85): `_on_bridge_prompt_request`. Нисходящий порядок, SHA-guard `f65e0e59…`, якоря до/после, снапшоты зон из git HEAD сверены байтово (sha256 в `D:\Temp\…\b8-7\snapshots\zone_*.txt`) |
| modules/supervertaler_bridge_server.py | git rm | 357 строк; единственный импортер — монолит |

Не менялись (по правилам): modules/trados_bridge_client.py, chat_view_widget.py, unified_prompt_manager_qt.py, settings_service.py, shortcut_manager.py, keyboard_shortcuts_widget.py, help_system.py.

## 3. Диффы изменённых методов монолита

Изменённые тела: только точечные удаления целиком (методы/блоки), без редактирования выживших тел:
- `create_main_layout`: вырезан блок «Supervertaler Bridge server» (комментарий 9 строк + `self._bridge_server = None` + try/except создания/старта/aboutToQuit/лога). Соседний комментарий о ретирменте Sidekick (:9844–9851) сохранён.
- `create_settings_tab`: вырезаны 3 строки регистрации «👤 User Identity» (комментарий-заголовок TAB 2, `identity_tab = …`, `addTab(…)`).
- Методы `_on_bridge_prompt_request`, `_create_user_identity_tab`, `_save_user_identity_from_ui` удалены целиком; полные тела — в снапшотах `snapshots/zone_{A,D}_*.txt` (sha256 `c7da187c…`, `73c21b76…`).
- Chat/Prompt Manager не правились (чип оставлен) — диффов нет.

## 4. Статическая валидация

| Проверка | До | После | Вывод |
|---|---|---|---|
| py_compile (сопоставимый объём) | 123/123 | 122/122 (−1 модуль) | ОК |
| py_compile (весь репо) | 140/140 | 139/139 | ОК |
| Защита 1: startup-chain resolve | 912 вызовов / 0 unresolved | 909 / 0 (−3: `run_prompt_requested.connect`, `aboutToQuit.connect`, `save_btn.clicked.connect`) | ОК |
| Защита 2: grep удалённых идентификаторов (`_on_bridge_prompt_request`, `_bridge_server`, `SupervertalerBridgeServer`, `supervertaler_bridge_server`, `_create_user_identity_tab`, `_save_user_identity_from_ui`, «User Identity», `sidekick-bridge`) по *.py | — | **0 упоминаний** | ОК |
| Защита 3: pyflakes undefined names | 696 предупреждений / 149 имён | 695 / 149 — **множество идентично** | ОК |
| AST: `get_translator_name` + читатели | на месте | на месте (6 self-вызовов; `open_tmx_editor_window`, `_comment_author_and_initials`, `add_comment_from_selection` присутствуют) | ОК |
| AST: удалённые методы/атрибуты отсутствуют, нет `save_general_settings()` без аргументов | — | 0 / 0 / 0 | ОК |
| Offscreen-проба | 6 вкладок; 15 страниц (с «👤 User Identity»); `_bridge_server = SupervertalerBridgeServer`; QTimer 3 / QThread 0 | 6 вкладок; **14 страниц** (без «👤 User Identity»); `window bridge attrs: []`; QTimer 3 / QThread 0; Trados-кнопки 3 (чип сохранён); hotkeys `ctrl+alt+l, ctrl+alt+q` | ОК |
| Headless-импорт modules/** | 115/122 (8.5-after), падения: tkinter×5, fitz, glossary_manager | 114/121 — те же 7 предсуществующих падений, −1 = удалённый модуль | ОК |
| 8 baseline-метрик | connect 1115, QShortcut 15, create_shortcut 32, QTimer 21, timeout.connect 21, QTimer.timeout 0, singleShot 73, invokeMethod 2 | connect **1112**, остальные без изменений | дельта −3 connect = удалённые connect'ы |
| git diff --stat | — | только Supervertaler.py (−184) + удалённый модуль | ОК |
| EOL Supervertaler.py | i/lf w/crlf | i/lf w/crlf | ОК |

Offscreen-пробы изолированы (`QT_QPA_PLATFORM=offscreen`, USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP → `iso-before/`, `iso-after/`, модалки нейтрализованы, opt-in statistics отключён). Headless-конструирование Chat/Prompt Manager не требовалось — файлы не менялись.

Про порт (T8.7.3): сервер биндил случайный высокий порт (bind `port 0`) — фиксированного порта у приложения нет и не было; после батча приложение вообще не слушает порты (проверено фактом отсутствия создания сервера: `window bridge attrs: []`; netstat-контроль Дмитрия — сценарий T8.7.3).

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: состояние после 8.5 (код 4988a0fb). Файлы меняются в `<корень сборки>\SupervertalerPortable\`.

| № | Путь | Действие | SHA256 (после замены) | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | ЗАМЕНИТЬ | `c542a3de63a229e01060225cd5162e13b7c6213cac22973afff3dd37c2879c41` (рабочая копия, CRLF) | 64979 строк; тестовая сборка использует собственный `._pth`, патчить не нужно |
| 2 | `modules\supervertaler_bridge_server.py` | **УДАЛИТЬ** | — | 357 строк; в базовой сборке (8.5) SHA256 файла `89f5d3d17421cc0f78cac2b2749f7cf18fcd91009455d6ba3a5add6a445df1e3` (для контроля, что удаляется именно он) |

Контроль после замены: sha256 `Supervertaler.py` должен совпасть с п.1; `modules\supervertaler_bridge_server.py` должен отсутствовать. Остальные 120 модулей не менялись (в т.ч. `modules\trados_bridge_client.py`, `chat_view_widget.py` — чип Trados сохранён).

## 6. СЦЕНАРИИ ПРОВЕРКИ (тестовая сборка; на КОПИИ user_data; сначала КОНТРОЛЬ на базовой сборке 8.5, затем после замены)

- **T8.7.1** Старт без исключений; 6 вкладок, Settings последняя; в консоли нет строк «Trados bridge server failed to start» (на baseline строка появляется только при сбое; штатный старт сервера в консоль не пишет — пишет в файл sidekick-bridge.log).
- **T8.7.2** Settings: 14 страниц, ВСЕ открываются; страницы «👤 User Identity» нет (была 4-й между «✍️ AutoCorrect» и «🤖 AI Settings»).
- **T8.7.3** Порт: PowerShell `netstat -ano | findstr LISTENING` — у процесса python нет чужих LISTENING-портов. Контроль на baseline: порт есть (случайный высокий, каждый запуск новый; handshake с портом — `<user_data>\workbench\runtime\sidekick-bridge.json`). После замены: handshake-файл не создаётся при новых запусках.
- **T8.7.4** Имя переводчика: Tools → TMX Editor открывается; экспорт TMX содержит автора (системное имя пользователя, т.к. ключ translator_name пуст или сохранён прежний) — приложение не падает; по возможности экспорт DOCX с комментарием — автор проставляется.
- **T8.7.5** Chat (вкладка AI → Chat) и Prompt Manager открываются без исключений; чип «🔗 Trados» **отсутствует** (скрыт) без запущенного Trados-плагина — это штатное поведение сохранённого чипа.
- **T8.7.6** Хоткеи из другой программы: Ctrl+Alt+Q (QuickTrans) и Ctrl+Alt+L (SuperLookup) работают как до батча.
- **T8.7.7** Live-test: импорт файла 180/400 сегментов; перевод сегмента; Save; сохранение настройки после перезапуска; навигация по вкладкам.
- **T8.7.8** Выход: иконка трея исчезает, процесс завершается (флаки-краш 0xC0000005 — предсуществующий).

## 7. Непокрытые проверки (честно)

1. Сценарии T8.7.1–T8.7.8 не выполнялись в этой среде (ручные, на тестовой сборке Дмитрия).
2. netstat-контроль отсутствия LISTENING-портов не проводился программно (offscreen-процесс завершается до замера; замещено проверкой `window bridge attrs: []` и AST-отсутствием создания сервера).
3. Живой POST `/v1/run-prompt` от Trados-плагина не воспроизводился — путь удаления подтверждён статически (0 упоминаний, защита 2) и пробой (сервер не создаётся).
4. Фактическая запись DOCX-комментария/TMX-экспорта с фолбэк-именем не прогонялась в offscreen (модальные диалоги).
5. Док-остатки не чистились (политика конца Batch #8): упоминания bridge server в `DEAD_CODE_REPORT.md`, `CODE_MAP_REFACTOR.md`, `DEPENDENCY_MAP.md`, `docs/refactoring/reports/BATCH8_STAGE1_AUDIT_REPORT.md`, `docs/refactoring/reports/EXTERNAL_STATE_AUDIT_REPORT.md`, аудит-манифестах; «User Identity» в тех же док-файлах.
6. PROJECT_STATUS.md в этом батче не обновлялся (промпт 8.7 не включает его в разрешённые файлы; прецедент 8.5).

## 8. Вопросы к Дмитрию

1. **Фолбэк `get_translator_name`**: оставить как есть — системное имя пользователя (текущее поведение, ключ `general.translator_name` у существующих пользователей продолжает работать), или заменить на нейтральную константу (например, «Translator»)? Сейчас не тронуто.
2. **Чип «🔗 Trados» + `modules/trados_bridge_client.py`**: оставлены по решению 12 (лимит ~40 строк превышен: ~147 затронутых строк, хоть все обращения и охраняются). Клиент независим от удалённого сервера (читает handshake плагина `trados/runtime/bridge.json`). Что делаем с ними после 8.9: удалять отдельным микро-батчем (тогда ~147 строк правок в chat_view_widget.py + ~24 в unified_prompt_manager_qt.py) или оставить жить?

## 9. Результаты ручного тестирования и решения Дмитрия (2026-10-06)

Все сценарии T8.7.1–T8.7.8 на тестовой сборке (замена по §5) — **ПОДТВЕРЖДЕНО**:

| Сценарий | Результат |
|---|---|
| T8.7.1 Старт без исключений; 6 вкладок, Settings последняя; в консоли нет «Trados bridge server failed to start» | ПОДТВЕРЖДЕНО |
| T8.7.2 Settings: 14 страниц, все открываются; «👤 User Identity» нет (была 4-й между «✍️ AutoCorrect» и «🤖 AI Settings») | ПОДТВЕРЖДЕНО |
| T8.7.3 Порт: у процесса python нет чужих LISTENING-портов; `sidekick-bridge.json` не создаётся при новых запусках (Дмитрий: «sidekick-bridge.json не создается») | ПОДТВЕРЖДЕНО |
| T8.7.4 Имя переводчика: TMX Editor открывается, экспорт TMX содержит автора, приложение не падает; DOCX-комментарий — автор проставляется | ПОДТВЕРЖДЕНО |
| T8.7.5 Chat и Prompt Manager без исключений; чип «🔗 Trados» отсутствует (скрыт) без плагина — штатное поведение сохранённого чипа | ПОДТВЕРЖДЕНО |
| T8.7.6 Ctrl+Alt+Q (QuickTrans) и Ctrl+Alt+L (SuperLookup) из другой программы работают как до батча | ПОДТВЕРЖДЕНО |
| T8.7.7 Live-test: импорт 180/400 сегментов; перевод сегмента; Save; настройка выживает перезапуск; навигация по вкладкам | ПОДТВЕРЖДЕНО |
| T8.7.8 Выход: иконка трея исчезает, процесс завершается (флаки-краш 0xC0000005 — предсуществующий) | ПОДТВЕРЖДЕНО |

### Решения Дмитрия (ответы на §8)

1. **Фолбэк `get_translator_name` → нейтральная константа «Translator»** — применено
   отдельным кодовым коммитом **acfe8880** («Batch #8.7 follow-up»): фолбэк
   `os.environ.get('USERNAME', os.environ.get('USER', 'user'))` заменён на
   `"Translator"`, докстринг обновлён; ключ `general.translator_name` остаётся
   приоритетным для существующих пользователей. Вторичные фолбэки
   `os.getlogin()` в modules/tmx_editor.py:706 и tmx_editor_qt.py:956 не тронуты
   (недостижимы при непустом возврате метода, вне скоупа батча).
2. **Чип «🔗 Trados» + trados_bridge_client — удалять отдельным микро-батчем после 8.9.**
   Записано в POST_BATCH8_BACKLOG.md §7 (с раскладкой строк по местам).

### Следствие для тестовой сборки

Из-за follow-up коммита acfe8880 SHA256 `Supervertaler.py` изменился: теперь
`ae9e3163ffc584a2fed228912d82daeb7d2c268e0d631c066bfa5878ae0177a9` (64984 строки,
CRLF-копия). Для приведения тестовой сборки к финальному состоянию 8.7 достаточно
заменить один файл `Supervertaler.py` (п.1 пакета §5; модуль bridge-сервера уже удалён).
Пункты §5 иначе без изменений.

Итог по Batch #8.7: код dc2e2838 + acfe8880, отчёт afd7d68f + настоящий §9; все защиты
и ручные сценарии закрыты. Последовательность Batch #8: 8.1–8.5 ✓, **8.7 ✓** → 8.10 → 8.8 → 8.9.
