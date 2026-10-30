# ОТЧЁТ BATCH P1.7 — Удаление macOS-веток (Linux остаётся)

**Дата:** 2026-10-30. **База:** `origin/main` = `fdfc1754` + локально P1.6 (`28257adc`, `28a03462`, `d8997753`, docs `7bd55fba`/`08c6339a`/`c4c1f3a0`); HEAD до батча `c4c1f3a0`.
**Коммит кода:** `05ebd2b9` (один коммит кода + этот docs-коммит). **Пуш не выполнялся — стоп до вердикта координатора.**
**Промпт:** Дмитрия, 2026-10-30 («BATCH P1.7 — удаление macOS-веток»).
**Рабочая область:** `E:\Dev\Work_temp\SupervertalerPortable\refactoring\p17\` (снапшоты «до», verify-скрипты) и `...\refactoring\batch-p17\` (логи статиков/сюиты).
**Основание:** RECON_P1_0 + решение координатора «без macOS, Linux-ветки допустимы». Функциональных правок нет — только удаление macOS-специфичного кода.

---

## 1. Итог одной строкой

macOS-ветки удалены в 5 файлах, **−548 строк** (64841 → 64293 по пяти файлам; монолит 54763 → **54676**, −87).
Windows- и Linux-поведение не меняется: подтверждено сюитой 16/16 одним процессом (регресс-хэши, e2e-тела и агрегат — байт-в-байт эталонные). Приёмка зелёная целиком (§5–§7).

## 2. Шаг 0 (рекон): таблица мест и решений

Grep по продукту (`Supervertaler.py` + `modules/`, без `docs/`, без `__pycache__`) по ключам:
`darwin`, `Darwin`, `macos`, `IS_MACOS`, `mac_`, `osascript`, `open -a`, `Key_Meta`, `AA_DontUseNativeMenuBar`, `sys.platform`, `platform.system`, `pyobjc|AppKit`, `Command`.

Достижимость проверялась перед каждой правкой: ветка удалялась только если её тело недостижимо
на Windows и Linux (гард чисто по darwin/mac), либо она стала мёртвой именно из-за этого батча.

| Место | Что делает | Достижимо только на macOS? | Решение |
|---|---|---|---|
| `Supervertaler.py:77-99` (до правки) | Crash-лог на Рабочем столе при запуске PyInstaller-бандла из Finder (гард `frozen and platform=='darwin'`) | Да | **Удалить** (блок целиком, с `del _sys, _os`) |
| `Supervertaler.py:119` | Импорт `IS_MACOS` из platform_helpers | Стал мёртвым после удаления 4 сайтов использования | **Убрать имя из импорта** (IS_WINDOWS/IS_LINUX не тронуты) |
| `Supervertaler.py:2531`, `:3678` | `_qt_hotkey = 'Meta+Ctrl+Q' if IS_MACOS else 'Ctrl+Alt+Q'` (меню QuickLauncher, 2 копии) | mac-ветка да | **Заменить на `_qt_hotkey = 'Ctrl+Alt+Q'`**; комментарий выше поправлен |
| `Supervertaler.py:19901` | Заголовок настроек QuickTrans: тернарник `Meta+Ctrl+Q if IS_MACOS` | mac-ветка да | **Заменить на `format_shortcut_for_display('Ctrl+Alt+Q')`** |
| `Supervertaler.py:54013-54021` | Комментарий про NSEvent-backend и Qt Mac convention | Комментарий только про удалённый mac-бэкенд | **Удалить** |
| `Supervertaler.py:54069-54075` | `if IS_MACOS:` подсказка про Accessibility при неудаче регистрации хоткеев | Да | **Удалить** |
| `Supervertaler.py:29063-29113` | Okapi «не установлен»: 4 флейвора скачивания; `is_apple_silicon` (Darwin+arm64); `has_bundled_jre = Windows or is_apple_silicon`; Darwin-подсказка `brew install`; `size_text = "about 50 MB" if is_apple_silicon else "about 70 MB"` | mac-подветки да; общий поток (Windows/Linux) сохранён | **Удалить mac-части**: `has_bundled_jre = (sysname=="Windows")`, `size_text = "about 70 MB"`, Linux-подсказка без `if/else`; комментарий «Four flavours» → «Two flavours». На Windows значение `has_bundled_jre` и `size_text` — те же, что и до правки (is_apple_silicon на Windows всегда False) |
| `Supervertaler.py:48143-48157` | Стартовый диалог «нужен Java»: ветка Darwin (`brew`) vs Linux (apt) | mac-ветка да | **Удалить ветку Darwin**, тело `else` де-индентировано; `sysname` стал мёртвым из-за батча — присваивание удалено |
| `Supervertaler.py:54663-54669` | `if sys.platform == 'darwin': app.setStyle("Fusion")` + 4 строки комментария про QMacStyle | Да | **Удалить** |
| `Supervertaler.py:54746-54762` | `__main__`: обёртка crash-лога вокруг `main()` для Finder-запусков (`frozen and darwin`) | Да | **Удалить**; осталось `if __name__ == '__main__': main()` |
| `modules/shortcut_display.py` (весь, 34 строки) | `format_shortcut_for_display` / `format_shortcuts_in_text`: на darwin конвертируют `Ctrl→⌘, Alt→⌥, Shift→⇧, Meta→⌃`; на Windows/Linux — тождественные | Тела конвертации — да (гард `!= "darwin"` → return вход) | **Тела конвертации удалить**, функции оставить тождественными (стабильный API: ~35 вызовов в монолите); `sys`, `re`, `_MAC_SYMBOLS`, `_SHORTCUT_PATTERN` стали мёртвыми из-за батча — удалены. 34 → 18 строк |
| `modules/platform_helpers.py:24` | Константа `IS_MACOS` | Стала мёртвой после удаления всех внутренних и внешних сайтов | **Удалить** |
| `platform_helpers.py:41-42, 71-73, 209-216, 249-257, 347-355` | `elif IS_MACOS:` в `open_file`, `open_folder_and_select`, `activate_window_by_title`, `get_foreground_window`, `activate_foreground_window` (osascript/`open`) | Да | **Удалить** (5 elif-веток) |
| `platform_helpers.py:1042-1043, 1051-1052, 1081-1082, 1091-1097, 1100-1125` | mac-поля `GlobalHotkeyManager` (`_mac_backend`), mac-ветки `is_available`/`start`/`stop`, метод `_start_macos` | Да | **Удалить** |
| `platform_helpers.py:1290-1293, 1297-1299` | `if IS_MACOS:` принты про Accessibility внутри `_start_pynput` (путь достижим только на Linux) | Да (мёртвые и на Linux) | **Удалить** |
| `platform_helpers.py:1331-1530` | Класс `_MacNSEventHotkey` целиком (NSEvent-мониторинг через PyObjC) | Да | **Удалить класс целиком** (−8 КБ) |
| `platform_helpers.py:1565-1567` | `is_available` сендера: `if IS_WINDOWS or IS_MACOS` | mac-слагаемое да | **→ `if IS_WINDOWS:`**; комментарий поправлен |
| `platform_helpers.py:1625-1626, 1782-1783, 2012-2014, 2268-2269` | `elif IS_MACOS:` диспетчеры `send_copy` / `send_paste` / `send_keystroke` / `type_text` | Да | **Удалить** |
| `platform_helpers.py:1634-1650, 1981-1994, 2104-2158, 2238-2248, 2341-2353` | Методы `_send_copy_macos`, `_send_paste_macos`, `_keystroke_to_applescript`, `_send_keystroke_macos`, `_type_text_macos` (все — osascript) | Да (`_keystroke_to_applescript` звался только из `_send_keystroke_macos`) | **Удалить все 5**; докстринги/комментарии диспетчеров приведены к Windows/Linux |
| `modules/keyboard_shortcuts_widget.py:18` | Импорт `IS_MACOS, IS_LINUX` | `IS_MACOS` стал мёртвым | **→ `import IS_LINUX`** |
| `keyboard_shortcuts_widget.py:399-403` | `if IS_MACOS: qt_key = 'Meta+Ctrl+M' else 'Ctrl+Alt+Q'` в настройках глобальных хоткеев | mac-ветка да | **Оставить только else-ветку** (`Ctrl+Alt+Q`) |
| `keyboard_shortcuts_widget.py:427` | Слагаемое `'nsevent': 'NSEvent'` в словаре backend-подписей | Стало мёртвым из-за батча (backend `'nsevent'` больше не существует) | **Удалить** |
| `keyboard_shortcuts_widget.py:446-461` | Блок `mac_note` (подсказка про Accessibility + pyobjc) | Да | **Удалить**; `elif IS_LINUX:` → `if IS_LINUX:` |
| `modules/unified_prompt_manager_qt.py:3492-3493` | `elif platform.system() == 'Darwin': open -R` («открыть папку с выделением») | Да | **Удалить elif** |
| `modules/termlens_popup.py:656, 712`; `keyboard_shortcuts_widget.py:53` | `Qt.Key.Key_Meta` в списках «чистые модификаторы» (не закрывать попап / игнорировать в захвате) | Нет: Meta — это Super/Win и на Linux; фильтр кроссплатформенный | **Оставить** (общий код с Linux) |
| `modules/okapi_sidecar.py:200/341/364/776/878/890/915` | Все проверки `platform.system() == "Windows"` (else = Linux+mac общий) | Нет (else-ветка общая с Linux) | **Оставить**; упоминания macOS в комментариях к флейворам скачивания — остаток, см. §4 |
| `Supervertaler.py:54556` (`sys.platform == 'linux'`), `:194/10675/22428/22572/53315/53441/54703/54716` (`win32`) | Linux-/Windows-ветки | Нет | **Оставить** (Linux-ветки допустимы по условию) |
| `modules/ui_scale.py` | grep `mac/darwin` — пусто | — | Чисто, правок нет |

Неоднозначных мест (общий код mac+Linux, требующий решения «не трогать») по итогам проверки достижимости не осталось: везде, где тело ветки было достижимо на Linux, ветка сохранена.

## 3. Что изменилось: было / стало / причина

| Файл | Было (строк) | Стало | Δ | Причина |
|---|---|---|---|---|
| `Supervertaler.py` | 54763 | **54676** | −87 | Таблица §2: crash-блок шапки, `__main__`-обёртка, Fusion-on-darwin, 3 тернарника хоткея, Accessibility-лог, okapi Darwin-подсказки + `is_apple_silicon`, NSEvent-комментарий, `IS_MACOS` из импорта |
| `modules/platform_helpers.py` | 2353 | **1930** | −423 | Класс `_MacNSEventHotkey`, `_start_macos`, 5 osascript-методов сендера, 5 elif-диспетчеров, константа `IS_MACOS`, mac-принты в pynput-пути |
| `modules/shortcut_display.py` | 34 | **18** | −16 | Тела darwin-конвертации → тождественные функции; мёртвые `sys`/`re`/таблицы символов |
| `modules/keyboard_shortcuts_widget.py` | 812 | **792** | −20 | `mac_note`, тернарник Meta+Ctrl+M, слагаемое `nsevent`, имя импорта |
| `modules/unified_prompt_manager_qt.py` | 6879 | **6877** | −2 | elif Darwin `open -R` |
| **Итого** | 64841 | **64293** | **−548** | |

Правило «мёртвое из-за батча — убрать, иное мёртвое — не трогать» соблюдено: удалены только `IS_MACOS`-константа и её импорты, `sys`/`re` в shortcut_display, `sysname`/`nsevent`-слагаемое и mac-методы. Прочий пред-существующий мёртвый код не тронут; кандидаты — §10.

## 4. Остаточные упоминания macOS после правки

Grep-гейт по кодовым ключам `darwin|IS_MACOS|osascript|AppKit|pyobjc|_MacNSEvent|is_apple_silicon` по продукту: **0**.

Grep case-insensitive `macos|darwin` по продукту: **30 совпадений — все комментарии/докстринги**, кроме двух пользовательских строк, которые сознательно не тронуты по правилу «Windows- и Linux-поведение байтово не меняется»:

1. `modules/keyboard_shortcuts_widget.py:270` — тултип «…help page (incl. macOS vs Windows symbol cheatsheet)»;
2. `Supervertaler.py:22033` — текст в настройках масштаба «Useful for Linux/macOS users where…».

Оба — кандидаты на текстовую чистку отдельным решением координатора (вопрос §11.2). Остальные 28 — комментарии/докстринги (okapi_sidecar 7, event_filters 2, keyboard_shortcuts_widget 2, Supervertaler 16, styled_widgets 1), описывающие историческое поведение; на исполнение не влияют.

## 5. Статика: было / стало / причина

| Проверка | Было (P1.6 final) | Стало (P1.7) | Причина расхождения |
|---|---|---|---|
| py_compile | 0 ошибок | **0 ошибок** (canon 108/0, ref 265/0) | — |
| AST-цепочка (batch8-15_startup_chain_resolve) | 875/0 | **875/0** | — |
| pyflakes (репо, тот же запуск в основном worktree, что и база 539) | 539 | **536** | **−3, дифф списков проверен поэлементно**: удалены предупреждения `'AppKit' imported but unused`, `'Cocoa' imported but unused`, `local variable 'action' is assigned to but never used` — все три жили в удалённом mac-коде `_MacNSEventHotkey` / `_keystroke_to_applescript`. Остальные расхождения — чистые сдвиги номеров строк монолита (пары 1:1). Новых предупреждений нет (висячего импорта `IS_MACOS` нет) |
| headless imports | 89 ok / 2 fail | **89/2** | Те же 2 известных отказа (`setuptools`, `fitz`) |
| grep-gate М1 (batch9-3_grep_gate.py) | CLEAN | **CLEAN** | — |
| Mac grep-гейт (см. §4) | — | **0 кодовых ключей** | Критерий промпта «darwin/IS_MACOS/macos = 0 или перечислить остаток» — выполнен (остаток перечислен) |

Запуск: `bash docs/refactoring/audits/batch-p17_static_run.sh p17` (копия p16-скрипта; лог `...\batch-p17\static\static_run_p17.log`, pyflakes-список `undefined_names_p17.txt`).

Уточнение по pyflakes «параметризованно по worktree»: правки выполнялись прямо в главном worktree (`E:\Dev\SupervertalerPortable`), отдельный git-worktree не заводился, поэтому предостережение P1.6 про chdir-скрипт (лжёт только при запуске из чужого worktree) не применяется — скрипт `os.chdir`-ится ровно в тот каталог, который правился; число честное, а дифф проверен поэлементно (§5).

## 6. Набор 16 этапов одним процессом

`bash docs/refactoring/audits/batch-p1b_run_full.sh p17`, лог `...\batch-p17\suite_p17.log`, пробы-копии `batch-p1b_*` переиспользованы без изменений:

| Этап | Результат |
|---|---|
| fallback 9.4h, profiles 9.4f, qtchat, statusbar | OK (как в P1-B/P1-C/P1.6) |
| e2e LLM | 5 запросов; тела байтово равны эталонам **qcfin / p1b / p1c / p16**; канонический агрегат `sha256(json.dumps(requests, sort_keys=True))` = **982e72a247f0a6ac…** (полностью совпадает с эталоном промпта) |
| S-clean | PROBE OK (2.3s) |
| S-upgrade | HASH-DIFF пуст: added=[] removed=[] changed=[] |
| regress | хэши **byte-identical**: export_simple_txt `5a12501f934a589c`, export_docx `44828d90090f046d`, export_tmx `c413d56372e69dd9`; сегменты 5/5/4 |
| smoke | **41 предмет** — только известная fitz-EXC, новых нет; SMOKE OK |
| termbase | REGRESS-TB OK |
| about | OK (About v1.10.371 как в эталоне) |
| save modern / save legacy | OK (api_keys целы) |
| r9 a / ctrl / rm | OK (профили целы, воскрешения нет) |

## 7. sha256 до/после (форма по правке координатора: два вида с подписью)

Для каждого изменённого файла — **блоб** (содержимое в git, LF; вычислен `sha256` от `git show HEAD:<файл>`) и **рабочая копия** (файл на диске; `Supervertaler.py` и `unified_prompt_manager_qt.py` — CRLF, модули — LF; `core.autocrlf=true`). CRLF-копии проверены программно как точный LF→CRLF-трансформ соответствующего блоба (True для обоих CRLF-файлов).

| Файл | до: блоб (LF) | до: рабочая копия | после: блоб (LF) | после: рабочая копия |
|---|---|---|---|---|
| `Supervertaler.py` | `ebdcbd101ad51784b25fb52d9a07f1f8f291376e42b3fb66c710c79a43570e55` | `25f3ccb5cdd038e7f8c2729a804a4a4f79310d221df9efe21e6a10b47f289d51` (CRLF) | `13aeaef58e283c0cc7f9ea46f3c0bf1fb4dca036850726f70ac083580d6d86a2` | `d89b1cc119607d8de62dd3a06b5dde648f13c53541263ffc074b852cb6d6a088` (CRLF) |
| `modules/platform_helpers.py` | `fd2eb0abc54c0f70f55357baa44bdd97d2e7ef497ca85e7cb0df5a2c6b8c6d99` | = блоб (LF) | `4341dfb2d3ba163862d948f3d7d6abe51b16fd00d3796a3035e68cf4ac1ff850` | = блоб (LF) |
| `modules/shortcut_display.py` | `1e653c579b1bf0fa24f54cbda80c561933d13b2ca2e55a3068a87e8b5ba68f29` | = блоб (LF) | `bf23f27891ab7bac001e8c74cf09616854873176ad8e6ef9da1d173389e9cb0c` | = блоб (LF) |
| `modules/keyboard_shortcuts_widget.py` | `5997eef1fdcad0543336c543942080eb1d9d52fd1186a1c1488b33e9d3f5ea4c` | = блоб (LF) | `7c75ff7e4290e9c4af89df6d2d6268ba01ba3fef1d37d14c94c2dc8c23db12ea` | = блоб (LF) |
| `modules/unified_prompt_manager_qt.py` | `ffad58cad26d04c6331482ece2f896bc5c1d7359b283b9099e37887724f587e9` | `260e35e2d0c2d3520d701dd98c83fbace138671fa75788c8f77bbd2fe37de475` (CRLF) | `e2674bdc36e47e79c0a1fbd1e92bdbfcd9dd796dba2ecf9a483ce86399149a50` | `1b05f94dcccc1253153e6f3255644d9fad82d41615a0f0e0c170c7d38a5699e6` (CRLF) |

git-объектные id (ls-tree) до → после: Supervertaler `27bee5ea`→`1b578371`, platform_helpers `d751aff6`→`83956209`, shortcut_display `a27fcb91`→`3d3f69e3`, keyboard_shortcuts_widget `61a7b5e4`→`dbd24ffb`, unified_prompt_manager_qt `6e00db42`→`dcf9c1ec`.

Снапшоты «до» (`...\refactoring\p17\pre\`) проверены байт-в-байт против блобов HEAD `c4c1f3a0` (по содержимому, с нормализацией CRLF) — все 5 MATCH; verify-скрипт `p17\verify_pre.py`.

## 8. Ручные тесты для Дмитрия

**Пакет для тестовой сборки `D:\SupervertalerPortable_test\` — заменить 5 файлов** из репозитория `E:\Dev\SupervertalerPortable`:

1. `Supervertaler.py` → `D:\SupervertalerPortable_test\SupervertalerPortable\Supervertaler.py`
2. `modules\platform_helpers.py` → `D:\SupervertalerPortable_test\SupervertalerPortable\modules\platform_helpers.py`
3. `modules\shortcut_display.py` → `D:\SupervertalerPortable_test\SupervertalerPortable\modules\shortcut_display.py`
4. `modules\keyboard_shortcuts_widget.py` → `D:\SupervertalerPortable_test\SupervertalerPortable\modules\keyboard_shortcuts_widget.py`
5. `modules\unified_prompt_manager_qt.py` → `D:\SupervertalerPortable_test\SupervertalerPortable\modules\unified_prompt_manager_qt.py`

Примечание: если тестовая сборка ещё не обновлялась после P1.6, дополнительно заменить `modules\quicktrans.py` и `modules\shortcut_manager.py` из P1.6-пакета (§9 отчёта P1.6); если сборка уже на P1.6 — пятёрки выше достаточно.

### T-P1.7a — обычная работа приложения

1. **Цель:** убедиться, что после удаления mac-веток приложение запускается и работает как раньше.
2. **Шаги:** запустить `D:\SupervertalerPortable_test\start.bat`; открыть последний проект (или создать новый); перевести один сегмент любым подключённым сервером; сохранить проект (Ctrl+S).
3. **Ожидаемый результат:** приложение запускается без ошибок в консоли; сегмент переводится как обычно; проект сохраняется; никаких новых сообщений про «hotkeys», «Java» или «platform».
4. **Провал:** ошибка при старте, падение при переводе/сохранении, либо в консоли трейсбек со словами `platform_helpers`, `shortcut_display`, `IS_MACOS`.

### T-P1.7b — горячие клавиши и вид интерфейса

1. **Цель:** убедиться, что глобальные хоткеи, отображение сочетаний и масштаб интерфейса не изменились.
2. **Шаги:** (а) находясь в любой другой программе (например, браузере), нажать **Ctrl+Alt+Q** — должен открыться всплывающий переводчик QuickTrans; закрыть Esc. (б) В редакторе перевода нажать **Ctrl** и цифру **1–9** (если настроены подстановки) — поведение прежнее. (в) Открыть меню — подписи сочетаний (например «Add to Termbase Ctrl+Alt+T») выглядят как раньше, **без символов ⌘/⌥/⇧**. (г) Настройки → шрифт/масштаб интерфейса — ползунок работает, подпись про масштаб на месте.
3. **Ожидаемый результат:** всё как до обновления; в строке статуса/логе при старте видно `[GlobalHotkeyManager] Registered ctrl+alt+q (WinAPI)`.
4. **Провал:** Ctrl+Alt+Q не срабатывает системно; в меню появились/исчезли символы; масштаб не применяется; в логе сообщения про «NSEvent», «macOS», «Accessibility».

## 9. Вопросы координатору

1. **`format_shortcuts_in_text` — ноль вызовов в продукте** (и до батча): функция сохранена в `modules/shortcut_display.py` как тождественная. Пред-существующий мёртвый код — кандидат в 8.18, не трогал. Подтвердить.
2. **Две пользовательские строки с упоминанием macOS** (§4: тултип справки `keyboard_shortcuts_widget.py:270`, подпись настроек масштаба `Supervertaler.py:22033`) — оставить как есть (текст не менялся ради байт-правила) или почистить отдельным микробатчем?
3. **`modules/shortcut_display.py` дальше**: сейчас это тождественные функции-обёртки (~35 вызовов в монолите). Оставить как стабильный API до инлайн-батча — ок?

## 10. Отложенное (не трогалось, по правилу «иное мёртвое — в 8.18»)

- `IS_WINDOWS`, `IS_LINUX`, `get_hidden_subprocess_flags` в строке импорта монолита — пред-существующие неиспользуемые имена (флаговались pyflakes и до батча).
- `format_shortcuts_in_text` — см. §9.1.
- Коммент-упоминания macOS в okapi_sidecar/event_filters/styled_widgets/Supervertaler (§4) — текстовые, поведение не задевают.

## 11. Ограничения

- Изменены только ветки, недостижимые на Windows/Linux; формат ассертов — см. §6 (регресс-хэши и e2e-тела байт-в-байт).
- БД, реестр, пользовательские данные не тронуты; шов `SUPERVERTALER_DATA_ROOT` не менялся (пробы-копии переиспользованы без изменений).
- Qt-6.11-ограничение P1.6 (§8 отчёта P1.6) не затронуто.

**Стоп до вердикта координатора. Пуш не выполнялся.**
