# План: архитектурный аудит Supervertaler (STRICT READ-ONLY, 4 отчёта)

## Зафиксированные ограничения
1. **Ни один `.py`-файл не изменяется, не создаётся и не перемещается.** Единственные создаваемые файлы — 4 отчёта в корне проекта: `CODE_MAP_REFACTOR.md`, `DEPENDENCY_MAP.md`, `DEAD_CODE_REPORT.md`, `EXTRACTION_PLAN.md`.
2. Все анализирующие скрипты и промежуточные артефакты (JSON/CSV) — во временном каталоге ВНЕ репозитория (`%TEMP%/sv_audit/`).
3. **Доказательство неизменности**: SHA256-снимок всех `.py`-файлов до начала и после завершения; несовпадение = ошибка.
4. Метод объявляется dead **только** с динамическими проверками (connect / timers / shortcuts / threads / getattr / event overrides / duck-typed вызовы из modules/). Категории строго по ТЗ: DEFINITELY_DEAD / PROBABLY_DEAD / DYNAMIC_ENTRY_POINT / LIVE / LIVE_BUT_LEGACY / UNKNOWN.
5. Язык отчётов: русский текст, заголовки разделов — английские, как в ТЗ.

## Факты разведки (уже собраны)
- 125 .py-файлов, 156 890 строк; `Supervertaler.py` = 73 337 строк; Python 3.13 доступен (AST работает); git/тестов/прежних отчётов нет.
- `SupervertalerQt`: строки 9170–67098, **819 методов**; `SuperlookupTab`: 67312–72548, **115 методов**; ещё 36 классов (модели, event-фильтры, grid-редакторы, workers, диалоги) и 59 топ-уровневых функций (~30 из них — DOCX tag-движок).
- `modules/`: 115 файлов, плоско; 18 orphan-модулей; 14 модулей duck-typed связаны с main window (`parent_app`); обратных импортов монолита нет.
- Динамическая обвязка: 781 `.connect()` (165 lambda), ~18 QTimer.timeout + 67 singleShot, QShortcut-реестр (~35 обработчиков), `threading.Thread(target=self.X)`, worker-signal connects к замыканиям и методам, 747 getattr / 1189 hasattr.
- Аномалии для документирования: `closeEvent` объявлен дважды в `SupervertalerQt` (33453 затенён 62932); устаревшие ссылки в докстринге (CODE_MAP.md, UNDERSTANDING.md, Supervertaler_tkinter.py); расхождение версий (pyproject 1.10.371 vs fallback-литерал 1.10.313, modules/__init__ 2.5.0); `docx_handler` использует legacy bare-import `tag_manager`; 3 копии `strip_tags` внутри самого монолита.

## Шаги выполнения

**Шаг 0 — Подготовка.** Создать `%TEMP%/sv_audit/`; посчитать SHA256 всех .py; зафиксировать полный список методов через AST (контрольное число 819).

**Шаг 1 — AST-инвентаризация (скрипт `inventory.py`).** По всем классам/функциям `Supervertaler.py`: для каждого из 819 методов `SupervertalerQt` (+115 `SuperlookupTab`, + методы прочих классов) извлечь: диапазон строк, LOC, декораторы; чтение/запись `self.*`; вызовы self-методов; внешние вызовы (функции/классы); lazy-импорты внутри метода (в файле 877 import-ов, 243 `from modules` — нужен обход вложенных импортов). Результат: JSON-досье.

**Шаг 2 — Карта динамических точек входа (скрипт `wiring.py`).** AST-разбор: все `.connect()` с разрешением целей (прямой `self.X`, `lambda: self.X`, перенос на следующую строку), QTimer timeout/singleShot, QShortcut + регистрации через `ShortcutManager.create_shortcut`, `threading.Thread(target=...)`, connects сигналов worker-ов (включая обработчики-замыкания — пометить как LIVE-обёртки), event-override список, строковые ссылки в getattr/hasattr/setattr. Плюс grep имён методов SupervertalerQt по `modules/`, `scripts/`, `tools/` — duck-typed контракты (`voice_commands` вызывает ~15 методов main window через hasattr, `quicktrans`, `translation_results_panel`, `pseudo_translate_dialog` и др.). Для каждого метода — класс входа: DIRECT / SIGNAL_SLOT / MENU_ACTION / SHORTCUT / TIMER / CALLBACK / WORKER_RESULT / EVENT_OVERRIDE / STRING_DYNAMIC / NOT_FOUND (+ кто вызывает).

**Шаг 3 — Self-state карта (скрипт `state_map.py`).** По каждому полю `self.*`: где/сколько читается и пишется, классификация (UI-widget / app state / project / translation / search / TM / termbase / settings / cache / worker / service / temp / legacy), кластеры совместного использования полей (кандидаты на выделение в сервисы).

**Шаг 4 — Call graph (скрипт `callgraph.py`).** Fan-in/fan-out по всем методам; hotspots (UI+logic+I/O в одном методе); изоляты; кластеры связности; циклические пути self-вызовов.

**Шаг 5 — Дубликаты и legacy (скрипт + ручная верификация).** Совпадения имён monolith↔modules/ (69 известных коллизий) и внутри монолита; difflib-сходство для near-duplicates; классификация legacy/compatibility-областей (tkinter-параллельные стеки, orphan-модули, «extracted from main file»-маркеры).

**Шаг 6 — Функциональная классификация (выполняю сам по досье).** Батчами по ~60–80 методов каждому присвоить: subsystem (кластеры из реальных данных, не механическая нарезка), responsibility, потенциальное назначение (destination), сложность/риск extraction, является ли кандидатом. Методы вне списка категорий ТЗ — в уточнённые новые кластеры.

**Шаг 7 — Dead-code аудит.** Классификация всех методов и orphan-модулей строго по evidence из шагов 1–5; для каждого кандидата — местоположение, доказательства, найденные callers, проверенные динамические механизмы, уверенность, безопасное следующее действие. Ничего не удалять.

**Шаг 8 — Отчёты (4 файла в корне проекта).**
- `CODE_MAP_REFACTOR.md` — структура §24 ТЗ; раздел 4 — **полная таблица всех 819 методов** (Method / Lines / LOC / Responsibility / Subsystem / Calls / Called By / self-state / Qt-Dynamic / Destination / Risk), пишется частями; далее кластеры, self-state map, call graph/hotspots, архитектура modules/, cross-dependencies, дубликаты/legacy, SuperLookup-анализ (115 методов отдельной таблицей), workers, UI, естественные границы модулей (без modules/misc.py-свалок), целевая архитектура, candidates, порядок extraction, риски, unknowns, ARCHITECTURE AUDIT VERDICT (16 вопросов §31).
- `DEPENDENCY_MAP.md` — module→deps, class→deps, function→deps, reverse dependencies, циклы (или их доказанное отсутствие), HIGH/LOW coupling, duck-typed контракты main window (14 модулей), dependencies SupervertalerQt→modules (163 имени) и modules→MainWindow.
- `DEAD_CODE_REPORT.md` — 5 разделов ТЗ с evidence по каждому кандидату (включая 18 orphan-модулей modules/).
- `EXTRACTION_PLAN.md` — пошаговый план по формату §27 (Goal/Source/Destination/Objects/Reuse/Dependencies/Imports/Circular risks/Risk/Validation/Rollback/Expected result), порядок выводится из dependency graphs, каждый шаг проверяем (AST-checks, smoke-сценарии запуска, hash-контроль).

**Шаг 9 — Финальная верификация.** Сравнение SHA256 всех .py до/после (неизменность); чек-лист §32 ТЗ; контроль полноты карты (819 методов + 115 SuperlookupTab); итоговое сообщение по формату §33: «Architecture audit completed. No source code was modified.» + счётчики (файлов, методов, кластеров, candidates, категорий dead-code, рисков) + первый рекомендованный extraction batch. Далее — остановка в ожидании следующего задания.

## Оценка объёма
Таблица 819 методов ≈ 150–250 KB в CODE_MAP_REFACTOR.md — это соответствует требованию «ТОЧНОСТЬ > КРАТКОСТЬ»; никаких сокращений перечня методов не допускается.