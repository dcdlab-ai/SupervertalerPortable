# RECON P1.0 — План портативности (READ-ONLY)

Дата: 2026-10-25. Исполнитель: ZCode (GLM). Режим: READ-ONLY — код продукта не менялся,
приложение не запускалось, реестр и реальные данные пользователя НЕ трогались (ни одного
`reg`-вызова, ни одной записи на диск вне рабочего каталога репозитория и stage-папки).

База: HEAD `824454d5` (Q-C-fin verdict), рабочее дерево чистое (untracked `.zcode/*` — допустимо).
Основание: аудит E1 (`docs/refactoring/reports/EXTERNAL_STATE_AUDIT_REPORT.md`, 2026-10-03,
HEAD `01f4ae2e`) + решения Дмитрия (E1 §6–§7 и промпт P1.0). Инвентаризация выполнена ЗАНОВО и
НЕЗАВИСИМО от E1 (grep/AST по текущему HEAD, см. §0.2); E1 использован только для кросс-проверки
результата (§1.8).

Рабочая область: `E:\Dev\Work_temp\SupervertalerPortable\recon-p1\` (сырые grep-дампы
`greps/*.txt`: qsettings, winreg, autostart, usage_stats, updates, datafolder, home, appdata,
temp, hardpaths, darwin, environ, last_directory).

---

## 0. Методика

### 0.1 Что считаем «внешним состоянием»

Любая запись/чтение вне корня целевой сборки
`<root>\{python-embed\, SupervertalerPortable\, Supervertaler\, start.bat}`: реестр (QSettings
NativeFormat + прямой winreg), %APPDATA%, %LOCALAPPDATA%, домашний каталог, %TEMP%, жёсткие
пути к дискам. Плюс сетевые касания удаляемых фич (статистика, обновления) — они не состояние
на диске, но входят в согласованный состав P1.

### 0.2 Команды инвентаризации (все — на HEAD `824454d5`)

`grep -rnE --include='*.py'` по репозиторию (исключая `__pycache__`) с пост-фильтрацией
продуктового кода (`Supervertaler.py`, `modules/**`; `docs/`, `tools/`, `scripts/` — не
продукт) по паттернам: `QSettings`, `winreg|HKEY_|Reg*`, `autostart|CurrentVersion..Run`,
`NativeFormat|IniFormat|setOrganizationName`, `usage_statis|telemetry|Help improve`,
`check_for_updates|releases`, `SetupWizard|wizard`, `supervertaler_config|get_user_data_path|
data_folder`, `last_directory`, `okapi|\.jar`, `shortcuts\.json`, `expanduser|Path.home|
USERPROFILE`, `APPDATA|LOCALAPPDATA|PROGRAMDATA|QStandardPaths`, `tempfile|gettempdir`,
`[D-D]:[\\/]` (жёсткие диски), `darwin|sys.platform`, `DontUseNativeDialogs|AA_Dont`,
`environ.get|getenv`. Затем — чтение всех найденных участков кода (Read, контексты ±40 строк).
Нюанс: встроенный grep печатает пути с обратными слэшами (`docs\refactoring\...`), фильтры вида
`^\./docs/` не срабатывают — продуктовые hit'ы отбирались по префиксам `Supervertaler.py:` и
`modules\`.

### 0.3 Состав продукта на HEAD

`Supervertaler.py` (55 687 строк), `modules/**` (~130 модулей, включая `quicktrans.py` 2 020,
`llm_clients.py` 932, `platform_helpers.py`, `autostart.py` 237, `usage_statistics.py` 295,
`config_manager.py` 444, `settings_service.py` 599, `ui_scale.py` 113, `shortcut_manager.py`
1 089, `okapi_sidecar.py`), `okapi-sidecar/` (исходники сайдкара: pom.xml, src/, build.ps1 —
JAR в репо не лежит, собирается), `translations/`, `assets/`, `user_data/`.

---

## 1. Инвентарь внешнего состояния (независимая перепись на HEAD `824454d5`)

### 1.1 Реестр Windows

| # | Ключ/ветка | Сайт кода | Что и когда | Читатель | Переносимо в корень? | Влияние на тесты |
|---|---|---|---|---|---|---|
| R1 | `HKCU\Software\Supervertaler\MTQuickPopup` (QSettings NativeFormat, org=`Supervertaler`, app=`MTQuickPopup`) | `modules/quicktrans.py:826` (чтение при открытии попапа: width/height/x/y), `:1563` (запись в `closeEvent`, quicktrans.py:1562-1567) | геометрия окна QuickTrans-попапа; читается при каждом открытии, пишется при каждом закрытии | те же 2 сайта | ДА, тривиально: `QSettings(<ini-путь>, QSettings.Format.IniFormat)` — 2 строки (по решению E1 §7 п.3; в промпте P1.0 — «может остаться, если проще», см. QP1.1) | попапные пробы (Q.2/Q.6 и т.п.) геометрией не гейтятся; при переносе — offscreen-проба «открыл-закрыл → ini в корне, ключ HKCU не создан» |
| R2 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, значение `Supervertaler` | `modules/autostart.py:66` (_WIN_RUN_KEY), `:69-79` чтение, `:82-94` запись (`_windows_enable`), `:97-110` удаление; вызовы из монолита: трей-меню `Supervertaler.py:26502-26516` (создание пункта «Start with computer»), `:26623-26635` (`_on_toggle_autostart`) | команда автозапуска `"pythonw.exe" "<абс. путь>\Supervertaler.py"` — пишется при включении галочки в трее | `autostart.is_enabled` при построении трей-меню | УДАЛЯЕТСЯ ЦЕЛИКОМ по составу P1 (модуль + пункт меню + обработчик) | трей-пробы: пункт меню исчезает из снапшота меню; после удаления в продуктовом коде не остаётся НИ ОДНОГО `winreg`-импорта (см. R3) |
| R3 | `HKCU\Software\Microsoft\Accessibility`, значение `TextScaleFactor` | `modules/usage_statistics.py:267-282` (`_get_text_scale`) — **только чтение**, системный ключ ОС (пишет Windows, не приложение) | читается 1 раз при отправке пинга статистики (opt-in) | — | уходит вместе с модулем статистики (P1.1); это НЕ состояние приложения | исчезает само; grep-гейт `winreg` в продукте = 0 после P1.1 |
| R4 | `HKCU\...\Explorer\ComDlg32\` (`OpenSavePidlMRU` и др.) | кода НЕТ — пишет ОС при каждом **нативном** файловом диалоге (Qt QFileDialog по умолчанию нативный на Windows; `AA_DontUseNativeDialogs` в коде сейчас НЕ установлен — grep `AA_Dont\|DontUseNativeDialogs` по продукту: 0) | MRU путей, общий для всех приложений пользователя | ОС | непрямым образом: `AA_DontUseNativeDialogs` + явный стартовый каталог у наших диалогов (fdh передаёт `last_directory`) → нативные диалоги не открываются → MRU не пишется | пункт P1 «AA_DontUseNativeDialogs остаётся в плане»; ручная проверка вида диалогов (Win10 сейчас, Win11 — у Дмитрия) |

Итого на HEAD пишут в реестр ТОЛЬКО R1 (2 сайта в quicktrans.py) и R2 (автостарт). Прямых
записей winreg, кроме autostart.py, нет; QSettings-конструкторов в продукте ровно 2 (обе — R1);
импорты QSettings в `shortcut_manager.py:10` и `unified_prompt_manager_qt.py:26` — мёртвые
(конструкторов нет, ключей не пишут; то же отмечал E1 §1 прим. — кандидат на уборку в любом
под-батче P1 или 8.18).

### 1.2 %APPDATA%

| # | Путь | Сайты кода | Что и когда | Читатели | Переносимо? |
|---|---|---|---|---|---|
| A1 | `%APPDATA%\Supervertaler\config.json` — файл-указатель папки данных `{"user_data_path": "<путь>"}` | **Монолит**: `get_config_pointer_path()` `Supervertaler.py:171-192`; `save_user_data_path()` `:208-215`; `load_user_data_path_from_config()` `:218-238`; `get_user_data_path()` `:241-289`. Пишут: `:283` (авто-восстановление — ПОБОЧНАЯ ЗАПИСЬ ПРИ ЧТЕНИИ: если указателя нет, а `~/Supervertaler` существует и не пуст, указатель молча пересоздаётся) и `:20919` (Settings → «Change...», группа «Data Folder Location» `:20840-20950`, вложенная функция `change_data_path` `:20862-20933`). Читают: `:263` (каждый запуск, каждой сборкой) | выбор папки данных; порядок разрешения: указатель → авто-восстановление из `~/Supervertaler` → дефолт `~/Supervertaler` | зеркала без импорта монолита: `modules/ui_scale.py:61-86` (`_config_pointer_path`/`_user_data_path`), `modules/llm_clients.py:44-61` (`load_api_keys`); в i18n/main стартуют через монолитный `get_user_data_path()` (`:55520`) | ДА — ядро P1.3: папка данных фиксируется как `<root>\Supervertaler\`, указатель/авто-восстановление/диалог смены удаляются; зеркала переводятся на общий резолвер |
| A2 | ( macOS-аналог A1: `~/Library/Application Support/Supervertaler/config.json` — `Supervertaler.py:186-188`, `ui_scale.py:68-69`, `llm_clients.py:48-49` ) | уходит с darwin-ветками (P1.7) и с P1.3 | | | |

Существенно против E1: **мастер первого запуска и first-run диалог выбора папки уже удалены**
(`modules/setup_wizard.py` отсутствует, `_show_setup_wizard`/диалог :6637/:6657 из E1 не
существуют; grep `wizard` по продукту — только комментарий `config_manager.py:120`). Писателей
указателя осталось ровно два: авто-восстановление и Settings-диалог.

### 1.3 %LOCALAPPDATA%

| # | Путь | Сайты кода | Что и когда | Читатели | Переносимо? |
|---|---|---|---|---|---|
| L1 | `%LOCALAPPDATA%\Supervertaler\okapi-sidecar\` (JAR + JRE, штамп `okapi-sidecar.version`) | `modules/okapi_sidecar.py:748-761` (`_user_data_sidecar_dir` — цель ленивой загрузки), `:664-669` (кандидат поиска), `:706-714` (штамп версии рядом с JAR), `:763+` (`download_install` — Windows: ZIP с JAR+JRE); вызовы из монолита: `Supervertaler.py:29404` (авто-обновление устаревшей загрузки) и `:29540` (первая загрузка, сценарий 3 в `_ensure_okapi_sidecar` `:29347-29360`: JAR отсутствует → предложение скачать в один клик) | ленивая загрузка сайдкара — ТОЛЬКО когда JAR не найден ни в одном кандидате; порядок кандидатов уже ставит сборку выше: `_MEIPASS/okapi-sidecar` → `app_dir/_internal/okapi-sidecar` → **`app_dir/okapi-sidecar` (+ /dist, /target)** (`:652-662`, app_dir = корень кода, т.е. `<root>\SupervertalerPortable\`) и только потом `%LOCALAPPDATA%` (`:664-677`) | поиск при каждом старте сайдкара | ДА: (а) JAR кладётся в сборку `<root>\SupervertalerPortable\okapi-sidecar\` (в репо каталог уже есть, JAR не входит — сборочная задача Дмитрия); (б) цель ленивой загрузки переносится внутрь корня (`<root>\Supervertaler\okapi-sidecar`), `%LOCALAPPDATA%`-ветка удаляется (P1.5, QP1.7) |

### 1.4 Домашний каталог (`~`)

| # | Путь | Сайты кода | Что и когда | Читатели | Переносимо? |
|---|---|---|---|---|---|
| H1 | `~\.supervertaler_config.json` — `{"last_directory": "<путь>"}` (память последних папок файловых диалогов) | `modules/config_manager.py:28` (CONFIG_FILENAME), `:55-56` + `:66-76` (путь = `Path.home()`), `:99-114` (`_save_config` — запись ПОСЛЕ КАЖДОГО файлового диалога), `:406-433` (`get/set/update_last_directory`). Живой потребитель: `modules/file_dialog_helper.py:11` (`get_config_manager`), вызовы `:32/:67/:102/:135` во всех 4 функциях (стартовый каталог диалога + запись после выбора). `ConfigManager` жив ТОЛЬКО этой функцией: классовых вызовов из монолита нет (в отличие от E1: setup_wizard — его второй импортёр — удалён) | путь, откуда открывается каждый диалог Открыть/Сохранить (вкл. .svproj) | fdh | ДА — решение Дмитрия (E1 §6 п.3): last_directory хранить В КОРНЕ сборки, не в user_data, не в ~ (P1.4) |
| H2 | `~\Supervertaler\` — папка данных по умолчанию | `Supervertaler.py:195-205` (`get_default_user_data_path`); фолбэки: `modules/llm_clients.py:70-71/:95` (settings.json, api_keys.txt), `modules/llm_pricing.py:38` (`~/Supervertaler/pricing.json` — override поверх бандлового), `modules/ui_scale.py:86` | дефолт данных + цепочки фолбэков чтения ключей | — | ДА — заменяется на `<root>\Supervertaler\` в P1.3 (фолбэки ~/… удаляются вместе с указателем) |
| H3 | `~/Library/LaunchAgents/com.supervertaler.workbench.plist`, `~/.config/autostart/supervertaler.desktop` | `modules/autostart.py:117/:159` (macOS/Linux автозапуск) | — | — | Windows-ветка удаляется в P1.1; **Linux-ветка остаётся по составу P1** (`.desktop` — не реестр, для Linux-портируемости допустимо; если P1.1 удаляет модуль целиком — Linux-ветка уходит тоже, см. QP1.10) |

### 1.5 %TEMP%

| # | Что | Сайты кода | Когда | След |
|---|---|---|---|---|
| T1 | AHK-скрипты копирования `supervertaler_send_copy_<key>.ahk` | `modules/platform_helpers.py:1692-1704` | кэшируются в `%TEMP%\` ПЕРСИСТЕНТНО (не удаляются) | постоянные файлы-следы |
| T2 | PowerShell-скрипты copy/paste (NamedTemporaryFile) | `platform_helpers.py:1892-1932, 2170-2179, 2294-2318` | при каждой операции Superlookup/QuickTrans-вставки | транзитные, удаляются |
| T3 | прогрев AHK (пустой скрипт) | `Supervertaler.py:10877-10889` | при старте (Windows, AHK установлен) | транзитный |
| T4 | прочие `tempfile`/`gettempdir` | только перечисленные (grep: других продуктовых сайтов нет) | — | — |

Решение без правки кода: `start.bat` выставляет `TEMP`/`TMP` = `<root>\Supervertaler\tmp\`
(тестовая сборка уже делает это — AGENTS.md, «Frozen test build»), Python `tempfile` читает их
на старте процесса → все T1–T3 остаются внутри корня. Qt/сторонние библиотеки до чтения env не
пишут (процесс стартует с уже выставленным env). Оформляется шаблоном start.bat в P1.8.

### 1.6 Жёсткие пути к дискам/каталогам

Grep `[Dd]:[\\/]|[Cc]:[\\/](Users|Dev|Program|Windows)` по продукту: **0 продуктовых сайтов**
(только docstring-комментарии `Supervertaler.py:199` (описание дефолта) и `:48928` (URL-пример
`file://`) + исторические audit-скрипты в docs/). Единственные «внешние» корни — перечисленные
в §1.2–1.5 (`~`, `%APPDATA%`, `%LOCALAPPDATA%`, `%TEMP%`) и `JAVA_HOME`/PATH-поиск Java
(`okapi_sidecar.py:907`) — последний не запись, а поиск, портативности не мешает (JRE можно
положить в сборку; вопрос необязательный, QP1.11).

### 1.7 Сетевые касания удаляемых фич (не дисковое состояние, для полноты)

- статистика: POST `https://supervertaler-stats.michaelbeijer-co-uk.workers.dev/ping`
  (`usage_statistics.py:31`), opt-in, 1 раз за сессию (`_init_usage_statistics`
  `Supervertaler.py:37093-37115`, вызов `:6437`; ключи `usage_statistics_enabled/asked/id` в
  settings.json `:62-133`; диалог «Help improve Supervertaler» `:138-168`; чекбокс в Settings —
  группа «Privacy» `Supervertaler.py:20814-20838`) — удаляется ЦЕЛИКОМ (P1.1a), ключи в
  существующих settings.json остаются инертными (QP1.5).
- обновления: GitHub API (`api.github.com/repos/Supervertaler/Supervertaler-Workbench/releases`)
  — метод `check_for_updates` `Supervertaler.py:48286-48792`, Python-фолбэк
  `_fetch_latest_release_info_from_github` `:48793-~48900`, пункт меню Help `:8536-8539`,
  кнопка в диалоге About `:48998-49001` — удаляется ЦЕЛИКОМ (P1.2).

### 1.8 Кросс-проверка с E1 (2026-10-03) — расхождения

1. **Удалено с E1**: `modules/setup_wizard.py` (мёртвый импортёр ConfigManager) и
   bridge-модули `supervertaler_bridge_server.py`/`trados_bridge_client.py` (зеркала указателя
   A1) — в дереве отсутствуют; first-run диалог папки данных отсутствует. Писателей A1 теперь
   2 (было 4): авто-восстановление + Settings.
2. **Сдвиг строк**: quicktrans QSettings :610/:1324 (E1) → :826/:1563 (батчи Q.*);
   `save_user_data_path` :22815 (E1) → :20919; `_ensure_okapi_sidecar` и пр. — все номера в
   этом отчёте пересчитаны на HEAD.
3. **Подтверждено без изменений**: R1–R4, A1, L1, H1, H2, T1–T3, относительный дефолт
   shortcuts.json (`shortcut_manager.py:624` + срабатывание в
   `modules/keyboard_shortcuts_widget.py:231` — `ShortcutManager()` без аргумента; монолит
   всегда передаёт абсолютный путь `Supervertaler.py:6367/:6523`; `save_shortcuts` делает
   `mkdir(parents=True)` `:751` → при CWD≠корня создаются посторонние `user_data\` деревья;
   экспорт-диалог дефолт — голое имя файла `keyboard_shortcuts_widget.py:716`).
4. Новое против E1: ничего нового outside-root не появилось (Q-батчи касались QuickTrans/LLM).

---

## 2. Таблица «пункт согласованного состава P1 → точки кода → объём → риск»

| Пункт P1 | Точки кода (HEAD) | Объём | Риск |
|---|---|---|---|
| 1. Статистика использования удаляется полностью (вкл. opt-in диалог, ключ `usage_statistics_asked`) | монолит `:6437`, `:37093-37115`, `:20814-20838`; весь `modules/usage_statistics.py` (295 строк, с ним уходит единственное чтение R3) | −295 модуль, −~40 монолит; 1 коммит | НИЗКИЙ: изолированный модуль, вызов обёрнут в try/except; пробы `_us`-импорты в СТАРЫХ audit-скриптах при перезапуске сломаются (исторические, не перезапускать — QP1.5) |
| 2. Автозапуск Windows удаляется полностью | весь `modules/autostart.py` (237), монолит `:26502-26516` (пункт трей-меню), `:26623-26635` (обработчик) | −237, −~45; 1 коммит | НИЗКИЙ: пункт меню обёрнут `is_supported()`; после удаления продуктовый `winreg` = 0 |
| 3. Ключ QuickTrans (R1) — остаётся ИЛИ переносится (решение QP1.1) | `quicktrans.py:826/:1563` (2 строки) | перенос: 2 строки + путь ini; остаётся: 0 | МИНИМАЛЬНЫЙ в обоих вариантах; перенос даёт «реестр = 0 следов» |
| 4. Корень сборки — единственный источник путей; указатель папки данных и «change data folder» удаляются | монолит `:171-289` (указатель+авто-восстановление), `:6283` (присвоение), `:20840-20950` (Settings-группа), `:6478+` (`_reinitialize_with_new_data_path` — единственный вызов `:20924`, удаляется вместе с группой), `:55515-55520` (main, i18n-чтение — остаётся, меняется резолвер); зеркала `ui_scale.py:61-86`, `llm_clients.py:44-99`, `llm_pricing.py:36-39` | −~220 монолит, −~90 зеркала, +~40 новый общий резолвер `modules/portable_paths.py`; 1–2 коммита | СРЕДНИЙ: центральная функция, ~десятки потребителей `user_data_path`; главный подводный камень — изоляция тестов (теперь через env, см. §4 P1.3 «тестовый шов») |
| 5. last_directory → корень сборки (рядом с python-embed и SupervertalerPortable) | `config_manager.py` (путь конфига `:66-76`, сохранить API `get/set/update_last_directory` `:406-433`); fdh не меняется | ~30 строк; попутно срезаются мёртвые ветки ConfigManager (user_data_path/ensure_user_data_exists, QP1.6) | НИЗКИЙ: API fdh не меняется; поведение «диалог помнит папку» сохраняется, но в пределах сборки |
| 6. Okapi jar живёт внутри папки сборки | `okapi_sidecar.py:660-662` (кандидаты сборки — уже первые), `:664-677` (LOCALAPPDATA-кандидат), `:748-761` + `:763+` (цель ленивой загрузки), `:706-714` (штамп); триггеры `Supervertaler.py:29404/:29540` | ~40 строк правок; JAR в сборку кладёт Дмитрий (сборочная задача) | НИЗКИЙ: порядок кандидатов уже на стороне сборки; меняется только цель download/штампа (QP1.7) |
| 7. Фикс бага относительных путей shortcuts.json | `keyboard_shortcuts_widget.py:231` (безаргументный ctor), `shortcut_manager.py:624` (относительный дефолт), (`:716` — дефолт имени экспорта, опционально) | ~10-15 строк | НИЗКИЙ; регресс: конструирование виджета при CWD≠корня не создаёт посторонних `user_data\` |
| 8. AA_DontUseNativeDialogs остаётся в плане | сейчас НЕ установлен (0 сайтов); установка — 1 строка в `main()` до QApplication (`Supervertaler.py:~55507`) | +1 строка | СРЕДНИЙ по ВПЕЧАТЛЕНИЮ (вид диалогов меняется на Qt-шные на всех Windows; беспокойство Дмитрия о Win11 — там, наоборот, единообразнее native); функционально низкий: fdh всегда передаёт явный стартовый каталог; убивает R4 (ComDlg32 MRU) |
| 9. check_for_updates удаляется целиком (меню + кнопка) | монолит `:8536-8539` (Help), `:48286-48792` (метод), `:48793-~48900` (фолбэк), `:48998-49001` (About) | −~630 строк, 1 коммит | НИЗКИЙ: точечный кластер, 2 внешних вызова |
| 10. Итог: без SetupWizard / без macOS | SetupWizard уже отсутствует (8.8); macOS-ветки: монолит `:83-98`, `:186-188`, `:55591-55592`, `:55673-55687`; `llm_clients.py:48-49`, `ui_scale.py:68-69`, `shortcut_display.py:21-32` (⌘-отображение), `platform_helpers.py` (IS_MACOS, 15 ссылок), `okapi_sidecar.py:670-673/:755-757`; автостарт-macOS уходит в п.2 | ~20 участков, −~120 строк | НИЗКИЙ (мёртвые на Windows ветки), но широкий по файлам — отдельный под-батч, не смешивать с функциональными правками тех же файлов |
| 11. TEMP-следы | код не менять: `start.bat` задаёт TEMP/TMP внутри корня (шаблон в P1.8) | docs + шаблон | МИНИМАЛЬНЫЙ |

Целевая раскладка (решение Дмитрия, E1 §7): `<root>\{python-embed\, SupervertalerPortable\ (код), Supervertaler\ (workbench\, resources\, prompt_library\, …), start.bat}` — соответствует
существующей тестовой сборке `D:\SupervertalerPortable_test\`.

---

## 3. Как проверять «нет следов в реестре» безопасно

Требование: не записывать в реальный реестр пользователя в процессе проверки. Методы, по
возрастанию силы:

| Метод | Что даёт | Автономно для агента? |
|---|---|---|
| М1. Статический гейт | `grep -rn 'winreg' Supervertaler.py modules/` → 0; `grep -rn 'QSettings(' ` → только разрешённые IniFormat-сайты; `grep -rn 'APPDATA\|LOCALAPPDATA'` → 0 продуктовых (кроме Linux XDG); AST-гейт chain из обоймы | ДА (включить в обойму P1-батчей) |
| М2. QSettings.setDefaultFormat(IniFormat) + setPath на уровне кода | в `main()` ДО первого QSettings: `QSettings.setDefaultFormat(QSettings.Format.IniFormat); QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(<root>/config))` — ЛЮБОЙ будущий случайный `QSettings(...NativeFormat)` в процессе пишет ini в корень, а не в HKCU. Страховка уровня приложения, независимая от grep | ДА (1-2 строки в P1.6) |
| М3. Offscreen-проба с блокировкой winreg | в пробе подменить `sys.modules['winreg']` объектом, бросающим на любое обращение; прогнать стартовое окно offscreen → любое python-обращение к реестру падает с трассировкой. Ловит ТОЛЬКО python-уровень (C++-QSettings NativeFormat не идёт через модуль winreg — поэтому М3 дополняется М2, а не заменяет его) | ДА |
| М4. `reg query` до/после (наблюдение, не запись) | в реализационном батче: `reg query "HKCU\Software\Supervertaler" /s` и `reg query "HKCU\...\Run" /v Supervertaler` ДО offscreen-прогона полного приложения на изолированном профиле и ПОСЛЕ; диф должен быть пуст. Чтение реестра записью не является; «не трогать реестр» здесь соблюдено | ДА (в P1.6/P1.8; НЕ выполнялось в P1.0 по условию) |
| М5. `reg export` ветки `HKCU\Software\<org>` до/после на ОТДЕЛЬНОМ тестовом пользователе Windows | самый честный «чёрный ящик» на реальном GUI-запуске | НЕТ (нужен отдельный аккаунт/машина — ручной протокол Дмитрия) |
| М6. Process Monitor (Sysinternals) с фильтром по процессу | исчерпывающий след (реестр+файлы), включая нативные диалоги (R4) | НЕТ (GUI-инструмент, админ; опционально Дмитрию один раз после P1.8) |
| М7. Перенаправление профиля start.bat'ом (как тестовая сборка) | исключает %APPDATA%/%TEMP%/~ — но НЕ реестр (AGENTS: «Registry writes remain machine-global HKCU») — поэтому реестр закрывается М1–М4, а не стартовым скриптом | ДА (шаблон уже существует) |

Рекомендация: обязательный набор агента = М1+М2+М3 в батчах P1.6/P1.8 + М4 как финальный
прогон P1.8; М5/М6 — опциональный ручной протокол Дмитрия после финальной пересборки.

---

## 4. Порядок под-батчей P1.1…P1.8

Принципы: удаления первыми (уменьшают поверхность и строки для последующих диффов); ядро
путей (P1.3) отдельно от его потребителей (P1.4/P1.5); платформенная уборка (darwin) — в конце,
не смешивая файлы с функциональными батчами; каждый под-батч — свой коммит(ы), полная обойма
защит (py_compile, статика chain/pyflakes/canonical+reference, headless, grep-gate, сюита 16
этапов solo-прогоном — правило Q-C о конкурентности), стоп до вердикта после каждого.

### P1.1 — Удаление статистики и автозапуска (2 коммита)

- **P1.1a (статистика)**: `git rm modules/usage_statistics.py`; монолит: вызов `:6437`,
  метод `:37093-37115`, группа «Privacy» `:20814-20838`. Ключи `usage_statistics_*` в
  существующих settings.json не трогаем (инертны, QP1.5).
- **P1.1b (автозапуск)**: `git rm modules/autostart.py`; монолит: `:26502-26516`, `:26623-26635`.
- Критерий приёмки: старт приложения (offscreen, изолированный профиль) без ошибок; grep
  `winreg` по продукту = 0; в Settings нет группы «Privacy»; в трей-меню нет «Start with
  computer»; сюита 16/16, статика не хуже базы.
- Пробы: (1) снапшот пунктов трей-меню до/после; (2) снапшот групп Settings-диалога; (3)
  grep-гейт winreg/QSettings-конструкторов; (4) чтение settings.json до/после старта — байты
  ключей не изменены (инертность).
- Ручной (владелец, после пересборки): T-P1.1 — «в меню значка в трее нет пункта
  "Start with computer"; в Settings нет раздела Privacy; приложение стартует как обычно».

### P1.2 — Удаление check_for_updates (1 коммит)

- Монолит: `:8536-8539` (Help-пункт), `:48286-48792` + `:48793-~48900` (методы;
  точные границы снять AST на исполнении), `:48998-49001` (кнопка About). Проверить, что
  вспомогательные атрибуты `_update_check_*` не используются вне кластера.
- Критерий приёмки: в меню Help нет «Check for Updates...»; в About нет кнопки обновления;
  сюита 16/16; e2e-проба не тронута (фича не участвует).
- Пробы: снапшот пунктов Help-меню и кнопок About-диалога (monkeypatch `exec`) до/после.
- Ручной: T-P1.2 — «Help → нет пункта проверки обновлений; Help → About — только Copy
  Version Info и Close».

### P1.3 — Корень сборки как единственный источник путей; удаление указателя (1–2 коммита)

- Новый `modules/portable_paths.py` (~40 строк): `build_root()` = env `SUPERVERTALER_DATA_ROOT`
  (тестовый шов, см. ниже) → иначе `Path(__file__).resolve().parents[2]` (уровень выше каталога
  кода); `data_root()` = `<root>/Supervertaler`; `state_root()` = `<root>` (для P1.4/P1.6).
- Монолит: `get_user_data_path()` `:241-289` → `return portable_paths.data_root()`;
  УДАЛИТЬ `get_config_pointer_path/save_user_data_path/load_user_data_path_from_config/
  get_default_user_data_path` `:171-205` и авто-восстановление; Settings-группа
  «Data Folder Location» `:20840-20950` — удалить; `_reinitialize_with_new_data_path` `:6478`
  — удалить (единственный вызов `:20924`; QP1.6); комментарий «диалог первого запуска покажут»
  `:249/:287` устарел — поправить.
- Зеркала: `ui_scale.py:61-86` → `portable_paths`; `llm_clients.py:44-99` — указатель и
  `~/Supervertaler`-фолбэки заменить на `data_root()` (+ существующие dev `user_data_private`
  и repo `user_data` фолбэки — решение QP1.4); `llm_pricing.py:36-39` — override
  `~/Supervertaler/pricing.json` → `<root>/Supervertaler/pricing.json`.
- **Тестовый шов (критично)**: сегодня пробы изолируются через `USERPROFILE/APPDATA/HOME` env.
  После P1.3 резолв код-относительный и env-изоляция перестаёт работать для данных: любой прогон
  из репо писал бы в `E:\Dev\Supervertaler\`. Решение: env-переопределение корня
  (`SUPERVERTALER_DATA_ROOT`) в `portable_paths.build_root()` + dev-флаг `.supervertaler.local`
  → repo `user_data_private` (распространить на монолит, QP1.4). Новые пробы P1.3+ обязаны
  выставлять шов; СТАРЫЕ закоммиченные пробы при перезапуске на новом коде поведут себя иначе —
  пометить в отчёте батча (исторические не перезапускать).
- Критерий приёмки: чистый изолированный прогон (offscreen, шов на stage-каталог) — все новые
  файлы под `<stage>/Supervertaler/`; каталог `%APPDATA%` изолированного профиля ПУСТ после
  полного цикла старт→Settings→сохранение→выход; grep `APPDATA|XDG_CONFIG_HOME` по продукту = 0
  вне darwin/Linux-ветвей; сюита 16/16 (с адаптацией env-шва в новых прогонах).
- Пробы: (1) полный app: перечисление созданных путей; (2) юнит `portable_paths` (env → флаг →
  дефолт); (3) e2e сохранение/чтение settings.json из нового корня; (4) негатив: отсутствие
  указателя не создаёт `%APPDATA%\Supervertaler` (снапшот-диф пуст).
- Ручной (после пересборки): T-P1.3 — «запустить сборку с чистой папкой: все новые папки
  (workbench, resources, prompt_library) появляются в <корень>\Supervertaler; в
  %APPDATA%\Supervertaler ничего не создаётся (проверка проводником по точному пути из
  инструкции)».

### P1.4 — last_directory в корень + фикс shortcuts.json (1 коммит)

- `config_manager.py`: путь конфига → `portable_paths.state_root()/<last_directory.json>`
  (имя файла — QP1.2); API `get_last_directory/set_last_directory/update_last_directory_from_file`
  `:406-433` не меняется; fdh не меняется. Мёртвые ветки ConfigManager (`user_data_path`,
  `set_user_data_path`, `ensure_user_data_exists`, `is_first_launch`, REQUIRED_FOLDERS-хелперы,
  legacy api_keys-миграция — проверить AST-вызовы на исполнении) срезаются (QP1.6) или
  переносятся в 8.18.
- `keyboard_shortcuts_widget.py:231`: брать менеджер главного окна (виджет уже ходит к нему
  через `_reload_global_hotkeys_on_main_window`) либо явный абсолютный путь; дефолт
  `shortcut_manager.py:624` сделать обязательным аргументом (fail-fast) или резолвить через
  `portable_paths`; (опционально) дефолт каталога экспорта `:716` — из last_directory.
- Критерий приёмки: диалог Открыть проект после перезапуска стартует из последней папки, файл
  состояния — в корне сборки; конструирование редактора хоткеев при CWD≠корня НЕ создаёт
  `user_data\` под CWD (снапшот-диф пуст); хоткеи сохраняются и живут после перезапуска.
- Пробы: (1) fdh-функции с monkeypatch QFileDialog — state-файл пишется в корень; (2) виджет
  хоткеев при CWD=stage — нет посторонних деревьев, загрузка/сохранение через абсолютный путь;
  (3) регресс-набор сюиты.
- Ручной: T-P1.4 — «открыть проект из папки X, перезапустить приложение, File → Open Project
  снова предлагает папку X; после смены горячей клавиши и перезапуска клавиша действует».

### P1.5 — Okapi jar внутри сборки (1 коммит)

- `okapi_sidecar.py`: `_user_data_sidecar_dir()` `:748-761` → `<root>/Supervertaler/okapi-sidecar`
  (или отключение ленивой загрузки в портативе — QP1.7); LOCALAPPDATA-кандидат `:664-669`
  удалить; штамп версии `:706-714` пишет рядом с новой целью; кандидаты сборки `:660-662` уже
  первые — не менять; `_find_java`/JAVA_HOME не трогать (QP1.11 — JRE в сборку опционален).
- Критерий приёмки: юнит порядка кандидатов (JAR в `<root>/SupervertalerPortable/okapi-sidecar`
  выигрывает); `download_install` (мок requests) кладёт файлы в корень сборки; grep
  `LOCALAPPDATA` по продукту = 0.
- Пробы: юнит-проба резолва (подмена каталогов через `portable_paths`-шов); мок-проба загрузки
  без сети; регресс-сюита (Okapi-пути в e2e не участвуют).
- Ручной (опционально): «импорт DOCX с форматированием проходит без предложения скачать
  сайдкар» (JAR присутствует в сборке).

### P1.6 — Реестр: QSettings → Ini + AA_DontUseNativeDialogs (1 коммит)

- `quicktrans.py:826/:1563` → `QSettings(str(state_ini), QSettings.Format.IniFormat)` (QP1.1;
  при решении «оставить HKCU» — только М2-страховка ниже и пункт исключается).
- `main()` до QApplication: `QSettings.setDefaultFormat(QSettings.Format.IniFormat)` +
  `QSettings.setPath(IniFormat, UserScope, str(portable_paths.state_root()/config))`;
  `QApplication.setAttribute(AA_DontUseNativeDialogs, True)` (п.8 состава P1; беспокойство
  Win11 — вид проверяется ручным тестом, откат = удалить 1 строку).
- Критерий приёмки: offscreen «открыл-закрыл попап» → ini-файл геометрии в корне, ключ
  `HKCU\Software\Supervertaler` не создаётся (М4: reg query до/после — диф пуст); проба М3
  (winreg-блокировка) зелёная; file-диалоги открываются (offscreen-смоук fdh).
- Пробы: М3-проба; М4-диф; смоук диалогов (нативные запрещены → Qt-диалоги рисуются offscreen).
- Ручной: T-P1.6 — «переместить/растянуть попап QuickTrans (Ctrl+Alt+Q), перезапустить —
  положение сохранилось; в корне сборки появился файл quicktrans.ini; вид диалогов Открыть/
  Сохранить изменился на единый Qt (проверить, что приемлемо на Windows 10)».

### P1.7 — Удаление macOS-веток (Linux остаётся) (1 коммит)

- Все сайты из §2 п.10: монолит `:83-98` (ранний crash-лог darwin), `:186-188` (если не ушло в
  P1.3), `:55591-55592` (Fusion), `:55673-55687` (crash-обёртка); `llm_clients.py:48-49`,
  `ui_scale.py:68-69`, `shortcut_display.py:21-32`, `okapi_sidecar.py:670-673/:755-757`,
  `platform_helpers.py` IS_MACOS (15 ссылок) и darwin-ветки send_copy/paste/hotkey;
  `usage_statistics/autostart` уже удалены в P1.1.
- Критерий приёмки: grep `darwin|IS_MACOS|platform == .macos.` по продукту = 0; статика и
  сюита без изменений (ветки мёртвые на Windows); py_compile 0.
- Ручной: не нужен (мёртвые ветки).

### P1.8 — Финал: TEMP в корне, верификационная батарея, чек-лист сборки (docs + 1 прогон)

- Шаблон `start.bat` (в docs): CWD=`<root>`; `TEMP/TMP=<root>\Supervertaler\tmp`; запуск
  `python-embed\pythonw.exe SupervertalerPortable\Supervertaler.py`. (Профиль-редирект
  USERPROFILE/APPDATA как в тестовой сборке БОЛЬШЕ не нужен — после P1.3/P1.4 код сам пишет
  только в корень; оставить ли редирект как дополнительную страховку — QP1.12.)
- Верификация: М1 (грейпы) + М3 (winreg-блокировка) + М4 (reg query до/после полного offscreen
  цикла на изолированном профиле) + файловый диф «за пределами корня ничего не создано»
  (снапшот `%APPDATA%`, `%LOCALAPPDATA%`, `~`, `%TEMP%` до/после).
- Чек-лист «чистый старт» (замена E1 §3): «удалить папку сборки» — и всё; запись в docs.
- Критерий приёмки: батарея зелёная на машине агента; чек-лист и шаблон start.bat закоммичены.
- Ручной (Dmitry, после пересборки финальной сборки): полный T-P1.8 — запуск с чистой папки,
  работа с проектом, попап, перезапуск; опционально М5/М6 (reg export на тест-пользователе /
  Procmon).

### Зависимости и «нельзя вместе»

- Строгий порядок: P1.3 → P1.4, P1.3 → P1.5 (потребители `portable_paths`), P1.3 → P1.6
  (расположение ini). P1.1, P1.2 независимы (можно первыми в любом порядке).
- НЕ объединять в один батч: P1.3+P1.4 (оба меняют конфиг-резолв — ревью-читаемость);
  P1.5+P1.3 (okapi-строки поиска путей пересекаются с зеркалами); P1.7 нельзя мешать ни с
  каким функциональным (совпадающие файлы ui_scale/llm_clients/okapi_sidecar/platform_helpers).
- После P1.3 обязательная перепривязка прогонов обоймы на env-шов (новые прогоны сюиты
  выставляют `SUPERVERTALER_DATA_ROOT`) — иначе пробы начнут писать в `E:\Dev\Supervertaler\`.

---

## 5. Вопросы к координатору (с дефолтами)

| # | Вопрос | Дефолт |
|---|---|---|
| QP1.1 | Ключ QuickTrans R1: переносить в ini в корне (реестр = 0 следов; 2 строки + М2-страховка) или оставить в HKCU как «строго неизбежный» (0 правок)? | **Переносить** (просто и безопасно; формулировка промпта допускает оба) |
| QP1.2 | Точные имена/места служебных файлов в корне: отдельные `last_directory.json` + `quicktrans.ini` (+ каталог `config\` дляsetDefaultFormat-ini) прямо в `<root>`? | **Отдельные простые файлы прямо в корне** (решение «рядом с python-embed и SupervertalerPortable»); общий каталог конфигов не заводить |
| QP1.3 | Тестовый шов `SUPERVERTALER_DATA_ROOT` (env-переопределение корня для проб/CI) — принять имя и семантику (unset → build root)? | **Да** (без него пробы P1.3+ неизолируемы) |
| QP1.4 | Dev-режим репозитория: распространить флаг `.supervertaler.local` на монолитный резолв (dev-запуски → `repo\user_data_private`, не `E:\Dev\Supervertaler\`)? | **Да** |
| QP1.5 | Инертные ключи `usage_statistics_*` (и старые mt_*/прочие) в существующих settings.json — не трогать? | **Не трогать** (инертны; чистка — отдельное решение, никогда не блокер) |
| QP1.6 | `_reinitialize_with_new_data_path` и мёртвые ветки ConfigManager (user_data_path/ensure_user_data_exists/…) — удалять в P1.3/P1.4 или сдать в 8.18 (мёртвые методы)? | P1.3/P1.4 удаляют то, что лежит в правляемых строках; остальное — **8.18** |
| QP1.7 | Okapi ленивая загрузка: перенаправить цель в `<root>\Supervertaler\okapi-sidecar` (JAR в сборке обязателен) или отключить в портативе вовсе (нет JAR → внятная ошибка)? | **Перенаправить** (сборка самодостаточна, поведение восстановления сохранено) |
| QP1.8 | Пересборка замороженной тестовой сборки после P1.3 (+пакет последующих) для ручных T-P1.x — когда? (По AGENTS — отдельное решение Дмитрия.) | После P1.3 (минимальный пакет для T-P1.3), затем после P1.6/P1.8 |
| QP1.9 | Подтвердить установку `AA_DontUseNativeDialogs` (вид Qt-диалогов на Win10/Win11 меняется; native-стиль Win11 отличается от Win10 — Qt-диалоги, наоборот, единообразны). | **Устанавливать** (пункт состава P1; откат = 1 строка) |
| QP1.10 | P1.1 удаляет `modules/autostart.py` целиком — вместе с Linux-веткой (`.desktop` в `~/.config/autostart`). Linux-функциональность автозапуска не нужна и там? (Состав P1: «Linux-ветки остаются» относится к платформенным веткам кода в целом.) | **Удалить целиком** (автозапуск — фича Windows-инсталляции; если Linux-порт когда-либо понадобится — вернём из git) |
| QP1.11 | Класть ли JRE в сборку рядом с JAR (`okapi-sidecar/` уже допускает; сейчас ищется JAVA_HOME/PATH `okapi_sidecar.py:907`)? | **Не сейчас** (jar обязателен, JRE — за рамками P1; зафиксировать в чек-листе сборки) |
| QP1.12 | Сохранить ли в финальном `start.bat` редирект профиля (USERPROFILE/APPDATA) как страховку сверх кодовых P1.3/P1.4? | **Не сохранять** (код уже пишет только в корень; редирект маскирует регрессии верификации) |

---

## 6. Границы P1.0 (что не делалось)

- Код продукта не менялся (ни один продукт-файл не записан; итоговый `git status` — только
  новый отчёт).
- Реестр не запрашивался даже на чтение (в отличие от E1, который делал `reg query`) — по
  условию «реальный реестр не трогать»; все утверждения о реестре выведены из кода.
- Приложение не запускалось; реальные `%APPDATA%`, `~`, `%LOCALAPPDATA%` не читались и не
  писались.
- Пробы/батарея не прогонялись (READ-ONLY рекон; обойма — по месту в реализационных батчах).
- Сырые grep-дампы — `E:\Dev\Work_temp\SupervertalerPortable\recon-p1\greps\` (13 файлов);
  в репозиторий не коммитятся (исторические артефакты доступны по пути на время координации).

*Docs-only. Пуш не выполнялся — стоп до вердикта координатора.*
