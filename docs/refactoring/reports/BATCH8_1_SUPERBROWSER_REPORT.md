# Batch #8.1 — Удаление F4 Superbrowser (Этап 2, реализация)

Дата: 2026-10-03. Исполнитель: ZCode (GLM). Основание: `BATCH8_STAGE1_AUDIT_REPORT.md` ред. 2 (§2.4 F4, §4 строка 8.1, §4.1, B4, §6 «Непокрытое» №5).
Рабочие скрипты, снапшоты и логи: `D:\Temp\SupervertalerPortable\refactoring\b8-1\` (вне репозитория).
Это первый под-батч Batch #8 — его протокол валидации (§4) является шаблоном для 8.2–8.9.

---

## 0. Baseline и git-синхронизация

| Параметр | Значение |
|---|---|
| git fetch origin | без новых объектов |
| HEAD до работ | `c9aabfa61386ebce0bbbbe8b36591f13f4b19d71` = origin/main |
| git status | чисто; untracked только `.zcode/plans/plan-sess_….md` (допустимо) |
| Дрейф-чек | `git merge-base --is-ancestor 8963e05e HEAD` → OK (предок); HEAD опережает 8963e05e только docs-коммитами (ee765eea, 20f1c3ba, c9aabfa6) |
| SHA256 Supervertaler.py (baseline) | `5080fd5b4e6a5bdd58cc5b2a45f4d8c248578ec20c6eb1eae006dbc455d573d2` — совпал с baseline Этапа 1 |
| SHA256 modules/settings_service.py (baseline) | `4770acaab14d1706ba05a335c7fbcf80f0479fac52b7b05a19099f909f874e32` — не менялся |
| wc -l Supervertaler.py | 68265 (ожидалось 68265 ✓); modules/**/*.py = 137 ✓ |
| py_compile (baseline) | **138/138 OK** (pyc в `D:\Temp\...\b8-1\pyc\`; скрипт `py_compile_all.py`) |
| git ls-files --eol (baseline) | Supervertaler.py `i/lf w/lf`; modules/superbrowser.py `i/lf w/lf` |
| SHA256 modules/superbrowser.py (baseline) | `0a669658139d739e9952e329ba16bf6f99ef47bf9a42f9676083b1b219992b73` — совпадает со всеми манифестами аудитов начиная Batch #2 (модуль не менялся) |

Базовые значения защит §4.1 (сохранены в `D:\Temp\...\b8-1\`):

1. **Защита 1** (`startup_chain_resolve.py` → `startup_chain_before.json`): AST-резолв вызовов `self.X(...)` в main, `SupervertalerQt.__init__`, `init_ui`, `create_menus`, `create_main_layout`, `setup_global_shortcuts`, `_setup_progress_indicators`, `_warm_up_top_tabs` — **270 вызовов, 0 неразрешённых** (резолв: метод класса / присвоенный атрибут / унаследованный Qt-API по `dir(QMainWindow|QWidget|QObject)`).
2. **Защита 3** (pyflakes 4.0.1, установлен `pip --target` во временную папку — в bundled runtime не добавлялся; обёртка `run_pyflakes.py` с `sys.path.insert`, т.к. `._pth` встроенного Python игнорирует PYTHONPATH): baseline **726 предупреждений, из них 149 «undefined name»** — все предсуществующие; файл `undefined_names_before.txt` служит дифф-источником.

## 1. Рекон (без правок)

### 1.1 Таблица упоминаний (grep case-insensitive + AST)

| Файл | Место | Вид | Только Superbrowser? | Действие |
|---|---|---|---|---|
| Supervertaler.py | 9273–9278 | пункт меню Tools: `superbrowser_action` (QAction, tooltip, `triggered.connect(self.open_superbrowser_window)`, `addAction`) | да | удалить |
| Supervertaler.py | 10117–10157 | метод `open_superbrowser_window` (класс `SupervertalerQt(QMainWindow)` — AST-проверено, границы AST 10117–10157): lazy-импорт `from modules.superbrowser import SuperbrowserWidget` (:10127), атрибут `_superbrowser_window` (:10129/:10139/:10152/:10155), `WA_DeleteOnClose` (:10156) | да | удалить |
| modules/superbrowser.py | весь файл (351 строка) | `ChatColumn` (:45, cleanup :163–183), `SuperbrowserWidget` (:178, cleanup :321–329), standalone `__main__` (:335+) | да | git rm |
| Supervertaler.py | 44730 (комментарий), 44774 (список каталогов) | `_migrate_to_workbench_layout` — перечень переезда `superbrowser_profiles` | **нет — это F6** | **НЕ трогать** (уходит в 8.8) |
| docs/refactoring/audits/* | манифесты/каунты | исторические артефакты измерений прошлых батчей | — | не трогать (история) |
| docs/refactoring/reports/UPSTREAM_SYNC_STAGE1_REPORT.md:156 | упоминание в отчёте | исторический docs | — | не трогать |
| docs/refactoring/reports/BATCH8_STAGE1_AUDIT_REPORT.md | §2.4, §4 | сам аудит | — | не трогать |

Прочие имена (grep = 0 по коду): `BrowserColumn` — **уточнение рекона: такого класса нет**, класс колонки называется `ChatColumn` (в отчёте Этапа 1 §2.4/§3 он ошибочно назван `BrowserColumn`; строки :163–183 совпадают — неточность только в имени); ID хоткея `tools_superbrowser` — не существует; упоминаний в `modules/help_system.py`, `modules/keyboard_shortcuts_widget.py`, `modules/shortcut_manager.py`, tray, closeEvent — нет.

### 1.2 Закрытие «Непокрытого» №5 аудита

`web_browser_mode` — **не ключ настроек и не имеет отношения к Superbrowser**: это runtime-атрибут `SuperlookupTab` (`Supervertaler.py:63373`: `'embedded' if self.web_engine_available else 'external'`; переключается пользователем в `_on_web_mode_changed` :63996–64004; читается ~10 местами Web-Resources-логики SuperLookup :63652–65345). Не сохраняется в settings.json (в `modules/settings_service.py` — 0 упоминаний). **Ключей настроек, связанных с Superbrowser, не существует** — удалять нечего, решение 6 (орфанные ключи остаются) применяется тривиально.

### 1.3 Потребители superbrowser.py

Единственный импортёр — lazy `from modules.superbrowser import SuperbrowserWidget` внутри `open_superbrowser_window` (Supervertaler.py:10127). WebEngine-код остающихся модулей (`SuperlookupTab.create_web_resources_tab` — `QWebEngineView`/`QWebEnginePage`/`QWebEngineProfile` 63296+63303+) **не зависит от superbrowser.py** — у SuperLookup собственные импорты PyQt6-WebEngine. B4 соблюдён.

### 1.4 Структура Tools-меню вокруг удаляемого пункта

Последовательность (AST-реконструкция): PDF Rescue → SuperLookup → **Superbrowser** → TMX Editor → Statistics → Quick Count → addSeparator → Image Extractor → Scratchpad → Log Window → Usage Report → addSeparator → Settings. Пункт в середине — разделители-сироты не образуются, подменю не пустеет.

### 1.5 Итоговый список файлов к изменению и контрольный список имён

Файлы: `modules/superbrowser.py` (удалить), `Supervertaler.py` (два региона: 9273–9278, 10117–10157).
Контрольный список «ноль упоминаний» после удаления: `SuperbrowserWidget`, `ChatColumn`, `superbrowser_action`, `open_superbrowser_window`, `_superbrowser_window`, `modules.superbrowser`, `modules/superbrowser` (допустимое исключение: `superbrowser_profiles` в `_migrate_to_workbench_layout` 44730/44774 — по плану до 8.8).

## 2. Что сделано

| Файл | Действие |
|---|---|
| modules/superbrowser.py | `git rm` (−351 строка) |
| Supervertaler.py | удалён блок пункта меню Tools (был 9273–9278, 6 строк+пустая строка) |
| Supervertaler.py | удалён метод `open_superbrowser_window` целиком (был 10117–10156 + 1 пустая строка) |

Итого: `Supervertaler.py` 68265 → **68216** (−49), SHA256 после: `025b192456f308f24b84f1332ff44ce40df1a7f85f9e3e11610c98e8783c778e`. `git diff --stat` кодового коммита: ровно 2 файла, +0/−400.

## 3. Диффы изменённых методов монолита до/после

Изменены 2 региона (единственные хунки `git diff`: `@@ -9270,13 +9270,6 @@` и `@@ -10112,49 +10105,7 @@`):

1. **`create_menus`** — удалены 4 строки QAction+tooltip+connect+addAction и 2 пустые строки; теперь `tools_menu.addAction(superlookup_action)` сразу за ним следует `tmx_editor_action = QAction(self.tr("✏️ T&MX Editor..."), self)`. Снапшот до: `snapshots/menu_9273_9278.txt` (SHA256 `73c78d360be6569d3dff3ac8a10517e3e0bae163c9a4d05f85299cc7675db1de`); после — в `git show 20b5675b`.
2. **`open_superbrowser_window`** — метод удалён целиком; соседние методы (`_create_ai_prompt_manager…`/`open_tmx_editor_window`) не тронуты, между ними остались 2 пустые строки (стиль файла). Снапшот до: `snapshots/method_10117_10157.txt` (SHA256 `ee646bd0fe3ce4620e42d006fe2017c27792dce804746fda2c208e32e26f14a6`).

## 4. Статическая валидация (шаблон для 8.2–8.9)

| Проверка | Результат | Доказательство |
|---|---|---|
| py_compile после | **137/137 OK** (Supervertaler.py + 136 модулей; superbrowser.py удалён) | `py_compile_all.py`, pyc в `b8-1\pyc\` |
| Защита 1: резолв стартовой цепочки ПОСЛЕ | **268 вызовов, 0 неразрешённых** (было 270 — минус 2 `self.*()` из удалённого метода) | `startup_chain_after.json` |
| Защита 2: ноль упоминаний удалённых имён | `SuperbrowserWidget`/`ChatColumn`/`superbrowser_action`/`open_superbrowser_window`/`_superbrowser_window`/`modules.superbrowser`/`modules/superbrowser` — **0 по Supervertaler.py, modules/, tools/**; `superbrowser_profiles` — только 44730/44774 (не трогаем, 8.8) | grep-вывод в логе сессии |
| Защита 3: pyflakes-дифф | **новых предупреждений нет** (149 «undefined name» до = 149 после); нормализованный дифф (без номеров строк) содержит только (а) 5 предупреждений удалённого superbrowser.py, (б) сдвинутые номера строк в тексте 8 сообщений («from line 9850→9843» и т.п.) | `undefined_names_{before,after}.txt`, `norm_{before,after}.txt` |
| Меню Tools (AST) | последовательность 12 пунктов: PDF Rescue, SuperLookup, TMX Editor, Statistics, Quick Count, SEP, Image Extractor, Scratchpad, Log Window, Usage Report, SEP, Settings — **без двойных разделителей, без ведущего/замыкающего SEP, без «дыры»** | `menu_check.py`; аналогичный прогон на baseline-копии: те же предупреждения по file/import/export/view/help-меню (предсуществующие, правкой не затронуты), Tools: 13→12 пунктов |
| EOL | Supervertaler.py `i/lf w/lf` — не изменился; в modules/ 4 файла с `w/crlf` (grid/filters.py, grid/pagination.py, tag_manager.py, undo_manager.py) — **предсуществующее**, коммитом не затронуты | `git ls-files --eol` до/после |
| Offscreen-прогон ДО/ПОСЛЕ | **выполнен** (см. ниже) | `probe_window.py`, `probe_{before,after}.log`, изоляция `iso/{before,after}/` |
| Guard: no-arg `save_general_settings()` | 0 по всему коду | grep |
| Guard: `create_web_resources_tab` не изменён | AST-dump тела метода идентичен до/после: SHA256 `118c810949c6908d` (границы 63296–63790 → 63247–63741, сдвиг ровно −49) | AST-сравнение |

### 4.1 Offscreen-прогон (изолированно, §4.1 п.6)

Методика: `git worktree add` baseline-коммита c9aabfa6 во временную папку; в обоих прогонах `QT_QPA_PLATFORM=offscreen`, `USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP/TMP` перенаправлены в `D:\Temp\...\b8-1\iso\{before,after}\` (процесс-локально, user_data и реальный %APPDATA% не затронуты); модальные диалоги обезврежены (`modules.usage_statistics.show_opt_in_dialog → False`, `QDialog.exec → Rejected`, статические `QMessageBox.* → Ok/No`) — **первая попытка без этого зависла на opt-in диалоге usage statistics в обоих деревьях одинаково** (`usage_statistics.py:167` ← `_init_usage_statistics`), что само по себе подтверждает паритет до/после.

Результат (оба прогона ~8 с, логи в `probe_before.log`/`probe_after.log`):

- **ДО** (baseline c9aabfa6): `SupervertalerQt constructed (8.0s)`, PROBE OK; контроль: пункт меню найден — `&Tools > 🌐 Super&browser...`. Примечание: первый контрольный матчинг дал ложный «0 найдено» из-за мнемоники `Super&browser` — исправлено на сравнение с вырезанным `&` (зафиксировано для шаблона 8.2–8.9).
- **ПОСЛЕ** (рабочее дерево): `SupervertalerQt constructed (7.7s)`, PROBE OK; пункт меню **не найден**; `main_tabs` идентичны (8 вкладок, Superbrowser среди них никогда не был).
- Логи до/после побайтово эквивалентны по составу событий (создание БД, миграции схемы, промпт-библиотека, горячие клавиши) — отличий нет. Предупреждения «QWebEngineView not available — external browser only» и ошибки `'NoneType' object has no attribute 'execute'` раннего старта — **в обоих прогонах одинаково** (предсуществующие, offscreen-контекст/первый запуск на пустом профиле).
- Осиротевших python.exe/java.exe после прогонов нет (проверено tasklist).

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: последний кодовый коммит перед 8.1 — U1.4b `426a09e2` (docs-коммиты ee765eea/20f1c3ba/c9aabfa6 кода не меняют). Заменять файлы на сборке, собранной из `426a09e2`, поверх кода коммита `20b5675b`:

| № | Путь | Действие | SHA256 | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | ЗАМЕНИТЬ | `025b192456f308f24b84f1332ff44ce40df1a7f85f9e3e11610c98e8783c778e` | из коммита `20b5675b`, 68216 строк |
| 2 | `modules/superbrowser.py` | **УДАЛИТЬ ФАЙЛ** | — | файл больше не существует в репозитории |

Другие файлы кода не менялись. `requirements.txt` не менялся (PyQt6-WebEngine остаётся — B4).

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data тестовой сборки; сначала КОНТРОЛЬ на базовой сборке 426a09e2, затем после замены)

- **T8.1.1** Tools → Superbrowser: на базовой сборке пункт «🌐 Superbrowser...» есть (контроль подтверждён offscreen-пробником: `&Tools > 🌐 Super&browser...`); после замены — отсутствует; меню Tools: PDF Rescue, SuperLookup, TMX Editor, Statistics, Quick Count, разделитель, Image Extractor, Scratchpad, Log Window, Usage Report, разделитель, Settings — без «дыр» и лишних разделителей.
- **T8.1.2** Старт без исключений в консоли; главное окно открывается. (Offscreen-аналог пройден: `SupervertalerQt constructed`, PROBE OK, логи до/после эквивалентны.)
- **T8.1.3** Навигация: все главные вкладки и все страницы Settings открываются без исключений.
- **T8.1.4** SuperLookup → «🌐 Web Resources» открывается и грузит страницу (WebEngine жив). Примечание: в offscreen-прогоне обеих сборок импорт QWebEngineView недоступен («external browser only») — это артефакт offscreen-встраиваемой среды, одинаковый до/после; живую проверку WebEngine делает только этот сценарий на настольной сборке.
- **T8.1.5** live-test: импорт файла 180/400 сегментов; перевод сегмента; Save; сохранение настройки после перезапуска.
- **T8.1.6** Выход без зависания (флаки-краш 0xC0000005 при выходе — предсуществующий, регрессией не считать). Сценарий, ради которого F4 и удалялся: закрытие Superbrowser-окна больше невозможно — зависание устранено удалением.
- **T8.1.7** Данные: папка `workbench/superbrowser_profiles` в копии user_data (если есть) осталась нетронутой — код её больше не читает и не пишет; миграция `_migrate_to_workbench_layout` (список 44774) сохранена до 8.8.

## 7. Непокрытые проверки

1. Живое поведение Qt при закрытии Superbrowser-окна не воспроизводилось (диагноз зависания — статическая реконструкция из Этапа 1; после удаления сценарий исчезает вместе с фичей).
2. Живой WebEngine (T8.1.4) — только на настольной сборке Дмитрия: в offscreen-среде QWebEngineView-импорт недоступен в обеих сборках (до и после), т.е. смещение не связано с 8.1, но подтвердить «WebEngine жив» статикой нельзя.
3. Запуск приложения целиком (`main()` с `app.exec()`, трей, warm-up QTimer 2500 мс) не моделировался — проверялось конструирование окна без event-loop (трей/`_setup_tray_icon` живут в `main()` и не конструировались; к Superbrowser не относятся).
4. Внешние скрипты/инсталляторы вне репо, могущие ссылаться на `modules/superbrowser.py` (как в «Непокрытом» №3 аудита для setup_wizard.py), — не проверяемы из репо.
5. `first_run_completed`/welcome-логика не затрагивалась (это 8.8); offscreen-прогон шёл по пути первого запуска с `_needs_data_location_dialog` — Wizard-QTimer не срабатывал без event-loop (по проекту — ок).

## 8. Вопросы к Дмитрию

1. Подтверждаете тестовую сборку поверх базы `426a09e2` по пакету §5 (заменить Supervertaler.py, удалить modules/superbrowser.py)?
2. Уточнение рекона: класс колонки в модуле назывался `ChatColumn`, а не `BrowserColumn`, как в отчёте Этапа 1 (§2.4/§3) — исправить ли имя в Stage-1 отчёте отдельной строчкой ред. или оставить как есть (в Этапе 2 использовано фактическое имя)?
3. VALIDATION_BACKLOG.md не пополнялся: сценарии T8.1.x — специфичны для тестовой сборки и живут в §6 отчёта; общие сценарии «старт/вкладки/Settings» уже покрыты существующими пунктами. Верно ли, что отдельный пункт backlog для 8.1 не нужен?

---

*Кодовый коммит: `20b5675b` «Batch #8.1: remove Superbrowser (F4)» (2 файла, +0/−400). Docs-коммит отчёта — отдельный. Push — только после подтверждения Дмитрия. CODE_MAP_REFACTOR.md / EXTRACTION_PLAN.md не обновлялись (единый проход в конце Batch #8).*
