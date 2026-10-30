# ОТЧЁТ BATCH P1-C — P1.4a last_directory в корень сборки + P1.4b shortcuts.json + P1.5 Okapi внутри сборки

**Батч:** BATCH P1-C (промпт Дмитрия 2026-10-28, «BATCH P1-C — last_directory в корень сборки, фикс shortcuts.json, Okapi внутри сборки (P1.4 + P1.5)»; файл `docs/refactoring/prompts/Promt - BATCH P1-C.txt`).
**База:** `4860a2e6` (P1-B закрыт полностью, вердикт GO, ручные тесты подтверждены). **Отчёт:** `docs/refactoring/reports/BATCH_P1C_REPORT.md`.
**Коммиты:** P1.4a `8e5512cb` (last_directory) → P1.4b `f5ff6286` (shortcuts.json) → P1.5 `0746c717` (Okapi) → docs (этот коммит: отчёт + промпт + пробы P1-C).
**Пуш не выполнялся. Стоп до вердикта координатора.**
**Реальные данные пользователя (~\Supervertaler, %APPDATA%, реестр), dev-рантайм — не тронуты. Монолит НЕ менялся: Supervertaler.py байт-идентичен базе (54 743 строки; sha256 рабочей копии CRLF `f4ec3bf2b774b656…`, sha256 блоба репозитория LF `aa87db91279c1858…` — один и тот же контент, см. §10).**

---

## 1. Итог

**P1.4a — last_directory (`modules/config_manager.py`, 444 → 104 строки).** ConfigManager сокращён до единственной живой функции — хранилища последней папки файловых диалогов. Файл состояния: `<state_root()>\last_directory.json` (state_root() = build_root(), P1-B), формат `{"last_directory": "<путь>"}`. Чтение — на каждом `get_last_directory()`, запись — на каждом успешном `set_last_directory()` (без кэша в памяти — «перезапуск сервиса» всегда видит файл). Ошибка записи (нет прав) — тихий `logger.warning`, без падения диалога. API `get_last_directory` / `set_last_directory` / `update_last_directory_from_file` и все 4 вызова из `file_dialog_helper.py` не изменены (файл не трогал вовсе). Старый `~\.supervertaler_config.json` не читается, не удаляется, миграции нет (решение координатора) — упоминается только в исторических докстрингах.

**Удалено как мёртвый код** (проверка: grep по всем методам/именам по `Supervertaler.py`, `modules/` — ноль вызовов в продукте вне `file_dialog_helper`; единственный потребитель ConfigManager — `file_dialog_helper`, использует только last_directory-тройку). Причина удаления — отступление от QP1.6 по указанию промпта: все эти методы содержат `Path.home()` / `~`-литералы и ломают гейт «нет путей вне корня»:

| удалено (в файле не существует) | что было |
|---|---|
| `CONFIG_FILENAME` (`.supervertaler_config.json`), `_is_dev_mode`, `_get_config_file_path`, `_load_config`, `_save_config`, поля `dev_mode`/`script_dir`/`config_path`/`config` | система файла-указателя в домашнем каталоге |
| `DEFAULT_USER_DATA_FOLDER`, `_get_default_user_data_path` (`~/Supervertaler_Data`) | `Path.home()`-дефолт |
| `is_first_launch`, `get_user_data_path`, `set_user_data_path`, `_validate_path` | указатель user_data + валидация |
| `REQUIRED_FOLDERS`, `ensure_user_data_exists`, `get_subfolder_path` | создание структуры user_data (с P1-B это делает монолит из `data_root()`) |
| `get_existing_user_data_folder`, `migrate_user_data`, `migrate_api_keys_from_installation`, `API_KEYS_FILENAME` | legacy-миграции |
| `validate_current_path`, `get_preferences_path`, `load_preferences`, `save_preferences`, `get_all_config_info` |Preference-IO (живёт в `settings_service`) и debug-хелперы |

`settings_service.py:8-19` — докстринг переписан: сравка «указатель ConfigManager `~/.supervertaler_config.json` против `%APPDATA%/Supervertaler/config.json` монолита» заменена на актуальную (единственный источник путей — `portable_paths.data_root()`; исторический указатель удалён в P1-C; `_reinitialize_with_new_data_path` удалён в P1-B). `portable_paths.py` — из докстринга убрано упоминание ConfigManager (поведение не менялось, только комментарий).

**P1.4b — shortcuts.json (`modules/shortcut_manager.py`, `modules/keyboard_shortcuts_widget.py`).** Минимальный вариант: относительный дефолт `Path("user_data/workbench/settings/shortcuts.json")` в `ShortcutManager.__init__` (был `:624`) заменён на резолв `data_root() / "workbench" / "settings" / "shortcuts.json"` — тот же абсолютный файл, что передаёт монолит (`Supervertaler.py:6249`). Обоснование минимальности: одна точка резолва, сигнатура `Optional[Path] = None` сохранена, все существующие вызыватели (монолит передаёт путь явно; виджет при отсутствии главного окна делает `ShortcutManager()`) автоматически получают один и тот же абсолютный путь; дублировать выражение пути в виджете не нужно — фолбэк виджета `:231` оставлен без изменений и теперь по построению совпадает с монолитом. Дефолт папки экспорта (`keyboard_shortcuts_widget.py`, был `:716`): тривиальный вариант сделан — диалог «Export Shortcuts» стартует из last_directory (тот же state, что читают обёртки `file_dialog_helper`, локальный импорт `get_config_manager` внутри метода — в стиле файла, где уже есть локальный `import webbrowser`), при пустом state — прежнее голое имя файла.

**P1.5 — Okapi внутри сборки (`modules/okapi_sidecar.py`, 947 → 927 строк).** Цель ленивой загрузки `_user_data_sidecar_dir()` → `data_root() / "okapi-sidecar"`, всегда возвращает путь (ветки None больше нет). ВСЕ кандидаты поиска вне корня удалены вместе с платформенными ветками: секция «In user data directory» в `_find_sidecar_dir()` (LOCALAPPDATA / `~/Library/Application Support` / `~/.local/share`) и три платформенные ветки внутри `_user_data_sidecar_dir()`. Вместо них ОДИН кандидат `<data_root()>\okapi-sidecar` — после кандидатов сборки, поэтому JAR сборки по-прежнему выигрывает (проверено пробой 3), а скачанная копия находится при следующем запуске. Кандидаты сборки не тронуты (frozen/`_MEIPASS`/`_internal`, `app_dir/okapi-sidecar{,/dist,/target}` — первые). Штамп `okapi-sidecar.version` пишется рядом с новой целью без изменений кода (`_write_version_stamp(target_dir)`). Поиск Java (bundled JRE → JAVA_HOME → PATH) не тронут. Мёртвая ветка `if target_dir is None` в `download_install()` удалена. Остальные darwin-ветки вне этих двух функций не трогались (P1.7).

## 2. Греп-гейт приёмки (продукт = `Supervertaler.py` + `modules/`)

| паттерн | было (база P1-B) | стало | остатки |
|---|---|---|---|
| `LOCALAPPDATA` | 2 (okapi_sidecar :666, :752) | **0** | — |
| `APPDATA` | 2 (+LOCALAPPDATA-строки) | **0** | — |
| `Path.home` | 2 (config_manager :75, :81) | **0** | — |
| `expanduser` | 2 | 2 | только crash-log `~/Desktop` монолита (:84, :54734) — не путь данных, вне скоупа, разрешено промптом |
| `~/Library/Application Support`, `~/.local/share` (darwin-ветки okapi) | 2 | **0** | удалены в P1.5; прочих darwin-веток с этими литералами в продукте нет |
| `.supervertaler_config.json` | 3 | 2 | только исторические описания удалённой системы в докстрингах (`config_manager.py:5`, `settings_service.py:12`) — ни чтения, ни записи |

grep-gate `batch9-3_grep_gate.py`: **CLEAN** (идентичен базе).

## 3. Приёмочные пробы P1-C (логи в `Work_temp\...\refactoring\batch-p1c\`)

1. **fdh / last_directory** (`batch-p1c_probe_fdh.py`, шов → iso, изолированный профиль): **P1C-FDH-OK**, 11/11 — файл состояния создан ровно в `<iso>\last_directory.json` (state_root по шву), формат верный; диалоги open/save/dir/multi обновляют state; **свежий ConfigManager («перезапуск сервиса») читает сохранённое значение**; в изолированном профиле не появилось ничего (нет `.supervertaler_config.json`).
2. **Виджет хоткеев при CWD ≠ корня** (`batch-p1c_probe_shortcuts.py`, CWD = stage-каталог): **P1C-SH-OK**, 7/7 — фолбэк-менеджер резолвит тот же абсолютный файл `<data_root>\workbench\settings\shortcuts.json`; снапшот-диф CWD **пуст** (никакого `user_data\` под CWD); хоткей изменён, сохранён под `<data_root>`, свежая конструкция виджета его загружает (`is_custom=True`).
3. **Okapi юнит + мок-загрузка** (`batch-p1c_unit_okapi.py`, мок requests, без сети): **P1C-OKAPI-OK**, 15/15 — `_user_data_sidecar_dir()` = `<data_root>\okapi-sidecar`; **JAR сборки выигрывает**, пока существует; после его удаления находится копия из data_root («перезапуск»); `download_install` кладёт мок-bundle (JAR+JRE) под `<data_root>\okapi-sidecar`, штамп `okapi-sidecar.version` = EXPECTED_VERSION рядом, `is_installed/is_user_downloaded/needs_update/installed_version_hint` верны; `<LOCALAPPDATA>\Supervertaler` не создан.
4. **Негативная** (`batch-p1c_probe_negative.py`, код в worktree `<stage>\negroot\SupervertalerPortable` (HEAD `0746c717`), БЕЗ шва, изолированный профиль): **P1C-NEG-OK**, 11/11 — build root = negroot (внутри stage); весь цикл P1-C (fdh-запись + виджет хоткеев с CWD=stage + конструирование OkapiSidecar) кладёт state в `<negroot>\last_directory.json` и `<negroot>\Supervertaler\...`; **снапшот-диф изолированного профиля ПУСТ** (нет `~\Supervertaler`, нет ничего в AppData профиля).
5. **16-этапный набор** — см. §5.

## 4. Спец-пробы и утилиты P1-C (закрыты в audits)

`batch-p1c_probe_fdh.py`, `batch-p1c_probe_shortcuts.py`, `batch-p1c_unit_okapi.py`, `batch-p1c_probe_negative.py`, `batch-p1c_static_run.sh`, `batch-p1c_run_full.sh`. Промпт-файл `docs/refactoring/prompts/Promt - BATCH P1-C.txt`.

**Пробы-копии НЕ создавались заново — набор использует живые копии `batch-p1b_*` без изменений.** Обоснование: копии отличаются от оригиналов только швом `SUPERVERTALER_DATA_ROOT` и удалением посева указателя — в P1-C контракт шва не менялся, и ни одна правка батча не меняет протокол проб. Генератор не нужен; AGENTS.md называет `batch-p1b_*` текущими копиями сюиты — статус сохранился. (`batch-p1c_make_probe_copies.py` в репо не попал — черновик удалён до коммита.)

## 5. 16-этапный оффскрин-набор ОДНИМ процессом (`batch-p1c_run_full.sh p1c`) — 16/16 + 4 пробы P1-C

Прогон с **полностью чистым stage-каталогом** (`rm -rf batch-p1c/regress batch-p1c/iso-* batch-p1c/negroot`); само-посев отработал без ручного досева; изолированные профили создавались runner'ом заново.

- regress: `export_simple_txt 5a12501f934a589c`, `export_docx 44828d90090f046d`, `export_tmx c413d56372e69dd9` — **байт-идентичны базе**; 5/5/4 сегментов.
- e2e: verdict **OK** (`b9-3/llm_e2e_verdict_p1c.json`); 5 запросов; **тела запросов байт-идентичны** qcfin-базе И прогону P1-B (`requests == requests` проверено прямым сравнением verdict-JSON); агрегат по каноническому рецепту координатора — уточнение рецепта: **`sha256(json.dumps(requests, sort_keys=True))[:16] = 982e72a247f0a6ac`** — сходится у qcfin, p1b и p1c (документированная в P1-B формула «sha256(json(requests))» без sort_keys даёт `9a08ef0a135e8407` одинаково у всех трёх — т.е. равенство тел выполняется при любом рецепте; канонический = sort_keys).
- smoke: **SMOKE OK**, 41 пункт (единственный EXC — известный `fitz` на Tools/PDF-Rescue, среды без PyMuPDF; не регрессия).
- S-clean PROBE OK; S-upgrade PROBE OK, HASH-DIFF `added=[] removed=[] changed=[]` + известный transient `workbench/ai_assistant/index.json`.
- save modern/legacy: OK (api_keys + mt_quick_lookup intact), TB REGRESS-TB OK, about RESULT OK, fb S4/S5 OK, profiles/qtchat/statusbar PROBE DONE, r9 a/ctrl/rm RESULT OK.
- Сирот после прогона нет (перечисление Win32_Process python/java пусто); worktree `negroot` снят после пробы.

## 6. Статика (база 4860a2e6 → после; логи `static/…p1c-base`, `…p1c`)

| показатель | было | стало | причина расхождения |
|---|---|---|---|
| AST-chain | 875/0 | **875/0** | монолит не менялся |
| pyflakes | 542 (undefined 126/4) | **541 (126/4)** | −1: старое предупреждение `config_manager.py:329` («f-string is missing placeholders») исчезло вместе с переписанным файлом; по изменённым файлам новых предупреждений нет (пофайловая сверка с HEAD-снапшотами: config_manager 1→0, shortcut_manager 4=4, keyboard_shortcuts_widget 10=10, okapi_sidecar 1=1, settings_service 1=1) |
| py_compile canonical | 108/0 | **108/0** | монолит не менялся |
| py_compile REFERENCE | 254 (запись P1-B) / **257 факт на базе 4860a2e6 и на 442eb6ab** | **257/0** (продукт-коммиты) → **261/0** после док-коммита | 254 у P1-B было измерено до его док-коммита; финальное дерево P1-B уже содержало 257 (проверено прогоном той же команды на worktree `442eb6ab`). P1-C продукт-коммиты не добавили ни одного .py; док-коммит добавит 4 новые .py-пробы (fdh/shortcuts/okapi/negative) |
| headless | 89/2 | **89/2** | те же 2 известных FAIL (setuptools, fitz) |
| grep-гейт 9.3 | CLEAN | **CLEAN** | — |

## 7. Для Дмитрия: тестовая сборка (простым языком)

### 7.1 Какие файлы меняются в тестовой сборке после этого батча

Пересобирать сборку целиком НЕ нужно. Монолит `Supervertaler.py` в этом батче **не менялся** — заменять его не надо (если вы уже обновляли его под P1-B, ничего не делать). Достаточно заменить 5 файлов в папке `SupervertalerPortable\modules\` тестовой сборки:

| действие | файл |
|---|---|
| заменить | `modules\config_manager.py` |
| заменить | `modules\shortcut_manager.py` |
| заменить | `modules\keyboard_shortcuts_widget.py` |
| заменить | `modules\okapi_sidecar.py` |
| заменить | `modules\settings_service.py` |
| удалять ничего не нужно | файлы продукта не удалялись; `portable_paths.py` из P1-B уже на месте |

Всё это — файлы из репозитория `E:\Dev\SupervertalerPortable` после моего финального коммита.

### 7.2 Где появится last_directory.json

В **корне тестовой сборки**: `D:\SupervertalerPortable_test\last_directory.json` — рядом с `start.bat` и папкой `SupervertalerPortable\`, на один уровень ВЫШЕ каталога кода. Это обычный маленький текстовый файл (JSON) с одной строкой — путь к последней открытой папке. В профиле (`D:\SupervertalerPortable_test\Supervertaler\profile\`) его быть **не должно**, как и файла `.supervertaler_config.json`.

Настройки хоткеев по-прежнему лежат в `D:\SupervertalerPortable_test\Supervertaler\workbench\settings\shortcuts.json` — теперь этот путь прописан жёстко (абсолютно), раньше при неудачном стечении обстоятельств мог создаться лишний `user_data\` рядом с местом запуска.

### 7.3 Ручные тесты (обязательные)

**T-P1C.1 — «Последняя папка» переживает перезапуск.**
1. Запусти `D:\SupervertalerPortable_test\start.bat`.
2. File → Open Project, открой проект из любой папки X (или просто зайди в папку X и открой любой файл проекта).
3. Закрой приложение. Запусти снова.
4. File → Open Project — диалог должен открыться **сразу в папке X**.
5. В Проводнике проверь: в `D:\SupervertalerPortable_test\` появился файл `last_directory.json`; в `D:\SupervertalerPortable_test\Supervertaler\profile\` файла `.supervertaler_config.json` **нет**.

**T-P1C.2 — Хоткей переживает перезапуск.**
1. Запусти приложение, открой Settings → Keyboard Shortcuts.
2. Двойным щелчком по любой строке измени клавишу (например, на Ctrl+Shift+O), подтверди.
3. Закрой приложение, запусти снова — клавиша должна работать (и в списке у действия статус «Custom»).
4. Проверь Проводником: рядом с `start.bat` НЕ появилась папка `user_data`.

**T-P1C.3 (необязательный) — Okapi: запрос на загрузку не падает.**
1. Убедись, что в сборке нет папки `okapi-sidecar` (если есть и не хочешь удалять — просто пропусти тест).
2. Импортируй DOCX с форматированием (File → Import → DOCX), когда приложение предложит скачать Okapi-движок — **НЕ соглашайся** (загрузка большая).
3. Достаточно, что предложение показывается корректно и приложение не падает; после отказа импорт должен откатиться к обычному (без Okapi) режиму.

Что считается провалом: приложение не стартует; диалог Open Project после перезапуска открывается не в последней папке; `last_directory.json` появился в профиле или появился `.supervertaler_config.json`; хоткей слетел после перезапуска; рядом с `start.bat` появилась папка `user_data`.

## 8. Вопросы координатору

Блокирующих нет. Для протокола: канонический e2e-рецепт из промпта (`982e72a247f0a6ac`) воспроизводится как `sha256(json.dumps(requests, sort_keys=True))` — формулу предлагаю зафиксировать в таком виде (проверена на qcfin, p1b, p1c — сходится у всех трёх).

## 9. Среда и дисциплина

Все прогоны offscreen в `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1c\`; реальные пользовательские данные, реестр и dev-рантайм не читались и не писались (юнит Okapi создавал и удалял временный `E:\Dev\SupervertalerPortable\okapi-sidecar\okapi-sidecar.jar` внутри репозитория — убран пробой в finally, в git не попадал); kill только по PID-фильтру (survivors: пусто); worktree `negroot` снят после проб, `basewt` (замер REFERENCE на 442eb6ab) снят после замера. Тестовая сборка не обновлялась. `git push` не выполнялся.

## 10. sha256 файлов до/после и подтверждение CRLF (добавлено по замечанию координатора 2026-10-30)

**Метод.** «До» = блоб git на базе P1-C `4860a2e6`; stage-снапшоты, снятые с git HEAD до правок (`Work_temp\…\batch-p1c\snapshots\`), сверены с этими блобами побайтово — MATCH по всем 7. «После» = блоб git на `fdfc1754` (конец P1-C). Все sha256 ниже — по байтам репозитория (блоб, LF): в репо `core.autocrlf=true`, поэтому рабочая копия может отличаться от блоба только концовками строк (см. CRLF-примечание внизу). Изменённых файлов модулей шесть, по одному блоку работ: P1.4a — `config_manager.py` (+ докстринги `settings_service.py`, `portable_paths.py`); P1.4b — `shortcut_manager.py` + `keyboard_shortcuts_widget.py`; P1.5 — `okapi_sidecar.py`.

| файл | до (блоб `4860a2e6`) | после (блоб `fdfc1754`) | размер до → после, байт |
|---|---|---|---|
| `Supervertaler.py` | `aa87db91279c1858eff4bf650fd50dd8d794185010a89bd9823b41563eab00da` | тот же (байт-идентичен) | 2 880 797 → 2 880 797 |
| `modules/config_manager.py` | `ac7402c48346a6e4ac3e89115cbddf23c61d583a5d9fd4a0aef11193e3ca6239` | `e2c0eaec2bba12f688b86abee21a02a981d0ac27fee03a370fed6ca5028e5fe0` | 16 658 → 3 720 |
| `modules/settings_service.py` | `095dce366b615a8c00fb0c6e4428a4b06db1122090f25a018dbdc10d12a3a4bc` | `bdebe669fcf012fc352193151fff9f6702d12226f3cb8662b603944f3b30127b` | 35 525 → 35 621 |
| `modules/portable_paths.py` | `fb0ea2f745a0b3929116336c7df9e9aee9f1e03a91560cd98bd5589534578371` | `3facea3613a46744cb64fdec08f5085d5215dbea867432afea517236eb12d793` | 3 205 → 3 189 |
| `modules/shortcut_manager.py` | `265396e5fd2b27c627d85a79ddade027708dec490eaa7253be414767136359b1` | `dd55542ed919700e54be13a73f5db5d7ad38331323587f762b88c180d9fd3eab` | 40 656 → 40 912 |
| `modules/keyboard_shortcuts_widget.py` | `09e799f14f52a40bcd0fddb1548af1a8111d9bdbaa8eab3f5be8c234641feef7` | `5997eef1fdcad0543336c543942080eb1d9d52fd1186a1c1488b33e9d3f5ea4c` | 35 098 → 35 507 |
| `modules/okapi_sidecar.py` | `b72ec4091b3e66f5cad373bbdb7958854e2f235192509372ccdbfd77f5649ab0` | `aaed69c5a80efdba6ebe854b7691f3f9326a249f1bf714f81d915228185dab64` | 39 609 → 38 743 |

Контроль снапшотов (все == блобам базы): `Supervertaler.py`, `config_manager`, `settings_service`, `shortcut_manager`, `keyboard_shortcuts_widget`, `okapi_sidecar` — MATCH; снапшот `file_dialog_helper.py` (в P1-C не менялся) — MATCH `c3591cb81de9b3f8…`.

**CRLF-подтверждение Supervertaler.py.** Блоб git хранится в LF (0 CRLF / 54 743 LF, и до, и после — идентичен). Рабочая копия — CRLF; её sha256 на конец P1-C `f4ec3bf2b774b656a49e8307f36a1d34ae332a722de86ca80814d0fd49330f6f` (2 935 540 байт) — это точное LF→CRLF-преобразование блоба `aa87db91…` (проверено программно, побайтово). То есть `f4ec3bf2…` в отчётах P1-B/P1-C — хэш рабочей копии (CRLF), `aa87db91…` — хэш блоба (LF): один контент, два представления из-за `core.autocrlf=true`. Число «blob `b17fbc97…`» в отчёте P1-B — это git-овский SHA-1 объекта (`b17fbc978b599c9b331bb6c9bac797f3f9dc5b58`, `git ls-tree`), в P1-C тоже не изменился. Замечание AGENTS.md о ложных диффах «git show против рабочей копии» подтверждается: сверять нужно либо блоб-с-блобом, либо рабочую-копию-с-рабочей-копией.

**CRLF изменённых модулей** (блоб LF у всех): `config_manager.py`, `portable_paths.py`, `keyboard_shortcuts_widget.py`, `okapi_sidecar.py`, `shortcut_manager.py` — рабочая копия тоже LF (байт-в-байт равна блобу); `settings_service.py` — рабочая копия CRLF (601/601, файл старый, правка точечная, CRLF сохранены; sha256 рабочей копии на конец P1-C `93f6c044cbea5100f6e55de3487b3bf3ec16a857aad3274684d039c2dd47e184`). Сверка переноса кода выполнялась блоб-против-блоба, поэтому CRLF-разница рабочей копии на выводы не влияет.

Замер: `Work_temp\…\batch-p1c\hashes\p1c_sha_report.py` (вывод в логе того же прогона); скрипт не входит в продукт и в репо не коммитится.
