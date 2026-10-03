# E1 — Аудит внешнего состояния Portable (read-only)

Дата: 2026-10-03. Исполнитель: ZCode (GLM). Режим: READ-ONLY — код не менялся, реестр только читался (`reg query`), user_data не затронут, приложение не запускалось.
Рабочие скрипты и дампы: `D:\Temp\SupervertalerPortable\refactoring\e1\` (`qfdump.py`, `qfiledialog_dump.json`, pyc/) — вне репозитория.

Контекст: на тестовых сборках «новые установки подхватывают путь сохранения проектов». Задача — найти всё состояние приложения/ОС вне папки user_data, общее между сборками под одной учётной записью Windows, и дать вход для Batch #8.8 (first-run).

---

## 0. Baseline и git-синхронизация

| Параметр | Значение |
|---|---|
| git fetch origin | без новых объектов |
| HEAD = origin/main | `01f4ae2ec3e371c06e5a7db4715ed36026ec6465` |
| git status | чисто (untracked `.zcode/plans/…` — допустимо) |
| Дрейф-чек | `git merge-base --is-ancestor 8963e05e HEAD` → OK (предок) |
| py_compile | **137/137 OK** (Supervertaler.py + 136 модулей; superbrowser.py удалён в 8.1; pyc в `D:\Temp\...\e1\pyc\`) |

Метод: AST для вызовов/классов (реальный `self` — `open_project`/`save_project_as` принадлежат `SupervertalerQt(QMainWindow)`, AST-проверено через walk ClassDef), grep для строк и имен, дамп всех статических `QFileDialog.*`-вызовов скриптом (`qfdump.py`: **91 статический вызов** по монолиту+modules, экземпляров `QFileDialog()` — 0). reg query через `cmd /c` (Git Bash ломает `/s`, `/v`).

---

## 1. Таблица внешнего состояния

| № | Расположение | Писатель (метод) | Читатель (метод) | Что хранится | Общее между сборками под одной учётной записью? | Сброс |
|---|---|---|---|---|---|---|
| 1 | `%APPDATA%\Supervertaler\config.json` | монолит `save_user_data_path` (Supervertaler.py:208). Вызовы: :283 (автовосстановление в `get_user_data_path`), :6637/:6657 (first-run диалог выбора папки данных), :6950 (`_show_setup_wizard`), :22815 (Settings → смена папки) | монолит `get_user_data_path()` :241 (через `load_user_data_path_from_config` :230); зеркала без импорта монолита: `modules/ui_scale.py` `_user_data_path` :71, `modules/llm_clients.py` `load_api_keys` :48, `modules/supervertaler_bridge_server.py` :115, `modules/trados_bridge_client.py` :58 | `{"user_data_path": "<путь>"}` — **файл-указатель папки данных** | **ДА** (per-user, все сборки читают один и тот же файл) | `del "%APPDATA%\Supervertaler\config.json"` — с оговоркой об автоловлении, см. §3 |
| 2 | `~\.supervertaler_config.json` (т.е. `%USERPROFILE%\.supervertaler_config.json`) | `ConfigManager._save_config` (modules/config_manager.py:96), вызывается из `set_last_directory` :413 и `update_last_directory_from_file` :424 — **после каждого файлового диалога** через `modules/file_dialog_helper.py` (все 4 функции: get_open_file_name/get_open_file_names/get_save_file_name/get_existing_directory). Ветка `set_user_data_path` :175 используется только мёртвым `modules/setup_wizard.py` (:132/:333) | `ConfigManager.get_last_directory` :406 → fdh передаёт как **стартовый каталог** каждого диалога | `{"last_directory": "<путь>"}` — последняя папка любого open/save-диалога, **включая .svproj** | **ДА** (per-user, все сборки) | `del "%USERPROFILE%\.supervertaler_config.json"` |
| 3 | `HKCU\Software\Supervertaler\MTQuickPopup` (QSettings NativeFormat, org=`Supervertaler` app=`MTQuickPopup`) | `modules/quicktrans.py` `closeEvent` :1324 (`setValue width/height/x/y`) | `modules/quicktrans.py` :610 конструктор попапа (restore геометрии) | геометрия окна QuickTrans-попапа | **ДА** (per-user реестр) | `reg delete "HKCU\Software\Supervertaler" /f` (ключ только наш) |
| 4 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, значение `Supervertaler` | `modules/autostart.py` `_windows_enable` :84–90 | `_windows_is_enabled` :71–75; монолит `_on_toggle_autostart` (трей-меню) | команда автозапуска: `"pythonw.exe" "<путь>\Supervertaler.py"` — **захватывается та сборка, из которой включали** | **ДА**, но value одно на пользователя — указывает ровно на одну сборку | `reg delete "HKCU\...\Run" /v Supervertaler /f` |
| 5 | `HKCU\Software\Microsoft\Accessibility` `TextScaleFactor` | — (пишет ОС) | `modules/usage_statistics.py` `_get_text_scale` :271–282 — **только чтение** для телеметрии | масштаб текста ОС | не состояние приложения | не требуется |
| 6 | `%LOCALAPPDATA%\Supervertaler\okapi-sidecar\` | внешний установщик sidecar (не код приложения) | `modules/okapi_sidecar.py` кандидаты :657–668 (`okapi-sidecar.jar`) | jar Okapi-sidecar | **ДА** | `rmdir /s /q "%LOCALAPPDATA%\Supervertaler\okapi-sidecar"` |
| 7 | `~\Supervertaler\` (домашняя папка) | любой код, создающий данные по умолчанию; **автовосстановление** монолита создаёт сюда указатель | `get_default_user_data_path` :199; `modules/llm_pricing.py` :36–39 (`~/Supervertaler/pricing.json` — override поверх bundled); `modules/llm_clients.py` :77–102 (фолбэки настроек/api_keys) | каталог данных по умолчанию + pricing-override | **ДА**; его существование **с содержимым** включает автовосстановление №1 | переименовать/очистить для чистого старта |
| 8 | `HKCU\...\Explorer\ComDlg32\` (`OpenSavePidlMRU\<ext>`, `LastVisitedPidlMRU`, `FirstFolder`, `CIDSizeMRU`) | ОС — при каждом нативном файловом диалоге (в т.ч. Qt native) | ОС — стартовый каталог нативных диалогов без явного dir | per-user MRU путей по расширениям, **общий для всех приложений хоста** | **ДА** (и не только между сборками Supervertaler) | не рекомендуется — заденет чужие приложения; точечно `reg delete "...\OpenSavePidlMRU\<ext>"` |
| 9 | CWD-зависимые файлы: `user_data/workbench/settings/shortcuts.json` | `modules/shortcut_manager.py` :671 — дефолт **относительный**; но монолит всегда передаёт абсолютный (Supervertaler.py:6414, :6709); относительный дефолт реально срабатывает в `modules/keyboard_shortcuts_widget.py:231` | те же | пользовательские хоткеи | зависит от **рабочего каталога** запуска, не от учётной записи | запускать сборку из её собственной папки |

Примечания:
- Мёртвые импорты QSettings: `modules/shortcut_manager.py:10`, `modules/unified_prompt_manager_qt.py:26` (конструкторов нет, ключей не пишут) — утилизация мусора возможна в будущих под-батчах, к симптому не относится.
- `~\.supervertaler_config.json` ветка `user_data_path` у ConfigManager фактически не читается никем: `get_config_manager()` импортирует только `file_dialog_helper.py` (live) и мёртвый `setup_wizard.py`; ключ `user_data_path` в этом файле поэтому и не встречается (на машине Дмитрия файл содержит ровно `{"last_directory": …}` — проверено чтением ключей).
- Dev-маркер `.supervertaler.local` (монолит :481–489, ConfigManager :59–64) переводит ConfigManager в dev-режим; в репо `E:\Dev\SupervertalerPortable` маркера нет, в Portable-сборках его тоже нет → всегда user-mode.

Проверка существования на машине агента (только чтение, 2026-10-03):
- `%APPDATA%\Supervertaler\config.json` — существует, ключи `['user_data_path']` (mtime 10:42);
- `~\.supervertaler_config.json` — существует, ключи `['last_directory']` (mtime 09:59);
- `reg query "HKCU\Software\Supervertaler" /s` → «Не удается найти указанный раздел» (QSettings-ключ ещё не создавался);
- `reg query "...\Run" /v Supervertaler` → не найдено (автозапуск выключен);
- `ComDlg32` существует, `OpenSavePidlMRU` имеет ~сотни подключей-расширений; подключа `svproj` **нет** (поиск `/f svproj /k` — не найдено).

---

## 2. Путь сохранения/открытия проектов

### 2.1 Диалоги, значимые для проектов

| Метод | Строки | Вызов | Стартовый каталог |
|---|---|---|---|
| `open_project` (SupervertalerQt) | :29873 | `fdh.get_open_file_name(... .svproj ...)` | `ConfigManager.get_last_directory()` — **файл №2, общий между сборками** |
| `save_project_as` | :31791 | `fdh.get_save_file_name(... .svproj ...)` | тот же |
| `save_project` | :31776 | при пустом `project_file_path` → `save_project_as()` | тот же |
| `restore_last_project_if_enabled` | :45253 | без диалога: берёт `recent_projects[0]` | `recent_projects.json` **внутри user_data** (не внешнее) |
| `new_project` → `browse_file` | :29227 | `QFileDialog.getOpenFileName` без dir | нативный дефолт |
| Прочие import/export (53 вызова) | см. 2.2 | `QFileDialog.*` **без аргумента dir** | нативный дефолт |
| Экспортные save-диалоги | напр. :13190, :15061, :36143 | dir = имя файла (`supervertaler_selected.tmx`, `default_name`) или `str(source_path.parent / …)` | bare-имя резолвится от **CWD процесса**; путь исходного документа — от его папки |

Ключа настроек «путь проектов» в settings.json **не существует**: grep `default_project_location`, `last_project_dir`, `project_directory` — 0 совпадений; `general.restore_last_project` (:179 settings_service.py) — только флаг восстановления, пути не хранит. Вся «память о папке проектов» — внешняя (файл №2) либо в `recent_projects.json` внутри user_data.

### 2.2 Вызовы без стартового каталога (53 шт., вход для гипотезы B)

Полный список в `D:\Temp\...\e1\qfiledialog_dump.json`. Основные группы: все CAT-импорты/ре-экспорты memoQ/CafeTran/Trados/Phrase/Déjà Vu (:35338–:40437), import_document :32400, import_simple_txt :33227, import_folder_multifile :34059, _import_termbase :18753, _import_tmx_as_tm :19534, _attach_sdltm_as_tm :19969, new_project/browse_file :29227, модули: tm_manager_qt :895/:943, tmx_editor_qt :1007/:1395, pdf_rescue_Qt :398–:1518, chat_view_widget :563, unified_prompt_manager_qt :3401/:5893, find_replace_qt :433, segmentation_rules_widget :269, keyboard_shortcuts_widget :788.

### 2.3 Цепочка приоритета стартового каталога проектных диалогов

1. `fdh.get_save_file_name` → `config.get_last_directory()` (config_manager.py:406–411) → `config['last_directory']` из `~\.supervertaler_config.json`.
2. Файла/ключа нет → `''` → Qt при пустом начальном каталоге использует **рабочий каталог процесса** (корень сборки при запуске из start.bat). Подтверждено наблюдением Дмитрия: после удаления `~\.supervertaler_config.json` диалоги открывают папку сборки. «TMX from selected segment» — голое имя файла (`supervertaler_selected.tmx`, :15061) разрешается от CWD; экспорты после Open recent берут папку проекта (`source_path.parent`, напр. :36143).
3. `last_directory` перезаписывается после **каждого** успешного диалога (`update_last_directory_from_file` fdh), т.е. «последняя папка» глобально одна на пользователя для всех типов файлов и всех сборок.

### 2.4 Гипотезы

- **Гипотеза A (приложение хранит путь вне user_data) — ПОДТВЕРЖДЕНА**, но не через QSettings/реестр: механизм — `last_directory` в `~\.supervertaler_config.json` (таблица №2). Файл per-user → любая новая сборка под той же учётной записью начинает диалоги проектов с папки, оставленной любой другой сборкой (или любым диалогом — TMX, DOCX, экспорт). Это объясняет симптом «новые установки подхватывают путь сохранения проектов».
- **Гипотеза B (диалоги без начальной папки → внешний MRU) — исправлена наблюдением Дмитрия**: при пустом dir Qt использует **рабочий каталог процесса** (корень сборки при запуске из start.bat), а не Documents/MRU. Подтверждение: после удаления `~\.supervertaler_config.json` диалоги открывают папку сборки; «TMX from selected segment» — голое имя файла разрешается от CWD (:15061); экспорты после Open recent берут папку проекта (`source_path.parent`, :36143). Роль ComDlg32-MRU **понижена до вторичной**: она проявляется только для вызовов с реально пустым путём, когда нативный диалог игнорирует CWD, и к проектным диалогам отношения не имеет (они идут через fdh с явным `last_directory`). Вклад B в симптом — экспортные диалоги, наследующие папку документа/CWD.
- QSettings/реестр (`HKCU\Software\Supervertaler`) к пути проектов отношения не имеет (только геометрия QuickTrans-попапа).

---

## 3. Чек-лист сброса внешнего состояния перед чистым запуском тестовой сборки

Выполнять в cmd на тестовой машине ПОД ТЕМ же пользователем, что и сборка. Пункты 1–2 обязательны, 3–5 по обстоятельствам, 6 не делать.

```bat
:: 1. Указатель папки данных (общий для всех сборок!)
del "%APPDATA%\Supervertaler\config.json"
::    ВНИМАНИЕ: при следующем старте автовосстановление (Supervertaler.py:276-290)
::    пересоздаст указатель на ~\Supervertaler, ЕСЛИ та существует и не пуста.
::    Для по-настоящему чистого старта: переименовать/очистить ~\Supervertaler
::    или заранее положить указатель на нужную папку.

:: 2. Память последних папок файловых диалогов (причина симптома с проектами)
del "%USERPROFILE%\.supervertaler_config.json"

:: 3. QSettings QuickTrans (если существует; ключ только наш — безопасно)
reg delete "HKCU\Software\Supervertaler" /f

:: 4. Автозапуск (если включался из конкретной сборки)
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v Supervertaler /f

:: 5. Кэш Okapi-sidecar (общий)
rmdir /s /q "%LOCALAPPDATA%\Supervertaler\okapi-sidecar"

:: 6. ComDlg32 MRU — НЕ ТРОГАТЬ: общий с другими приложениями пользователя.
```

Чего достаточно для воспроизводимости «новой установки» в минимальном виде: пункты 1–2 (+7 из §1 — пустой `~\Supervertaler`).

---

## 4. Связь с SetupWizard/first-run (F5) и миграциями (F6) для Batch #8.8

1. **Указатель папки данных создаётся визардом и остаётся без него.** `_show_setup_wizard` пишет `%APPDATA%\Supervertaler\config.json` через `save_user_data_path` (:6950); first-run диалог — :6637/:6657 (в т.ч. при отмене — сохраняет дефолт). При удалении визарда (8.8) сам указатель и логика `get_user_data_path` остаются; поведение первого запуска определяется **внешним** состоянием:
   - указатель есть → данные открываются там (независимо от «новизны» сборки);
   - указателя нет, но `~\Supervertaler` существует с содержимым → автовосстановление (:276–290) молча пересоздаёт указатель туда — «новая» установка подхватит старые данные;
   - указателя нет и `~\Supervertaler` пуст/отсутствует → дефолт `~\Supervertaler`, `first_run_completed`/диалог (по решению 10 — упрощается в 8.8).
2. **Сценарий валидации 8.8 «чистый старт на ПУСТОЙ папке данных» нужно дополнить чек-листом §3** — иначе «чистота» подменяется остаточным внешним состоянием (в первую очередь пунктом 1 и автоловлением).
3. `~\.supervertaler_config.json` (last_directory) на выбор папки данных не влияет, но определяет, куда `Save As` предложит сохранить первый проект.
4. Миграции F6 внешнего состояния не создают и не читают (кроме переноса каталогов внутри user_data — `_migrate_to_workbench_layout`); `ConfigManager.user_data_path` — мёртвая ветка (пишется только мёртвым setup_wizard.py), в 8.8 уходит вместе с ним.
5. **Предложение исправления симптома «подхватывается путь проектов» (не применять, на решение):** сделать `last_directory` внутренней памятью сборки — например, хранить в `<user_data>/workbench/settings/dialog_state.json` и передавать из монолита (уже знает user_data_path) вместо общего `~\.supervertaler_config.json`. Альтернатива минимальным изменением: ConfigManager инициализировать путём конфига внутри user_data. Затрагивает метод `get_last_directory`/`set_last_directory` (config_manager.py:406–433) и файл file_dialog_helper.py целиком (4 функции) — потребители вызовов не меняются.

---

## 5. Непокрытые проверки

1. Поведение нативного диалога между сессиями на конкретной машине (точная роль ComDlg32-MRU для Qt6 native dialog) — зависит от версии Qt/ОС; статически не доказывается, live-тест запрещён условиями.
2. reg-запросы выполнены на машине агента (эта машина). Содержимое реестра/файлов на машинах, где воспроизводился симптом, не проверялось — для подтверждения достаточно выполнить §3 п.1–2 на тестовой машине и сравнить поведение.
3. `LastVisitedPidlMRU`/`OpenSavePidlMRU` различают приложения по exe/PIDL; тонкости для python.exe-хостов (несколько сборок под одним именем exe) не анализировались — бинарные PIDL не расшифровывались по условию.
4. Время модификации файлов-указателей (10:42/09:59 2026-10-03) указывает на недавнюю запись, но каким процессом (ручной запуск/тесты) — не устанавливалось; live-наблюдение не проводилось.
5. macOS/Linux-ветки (`~/Library/Application Support/Supervertaler/config.json`, XDG) — по симметрии кода, живьём не проверялись (не целевая ОС).
6. `modules/config_manager.py` методы кроме last_directory/get_user_data_path (`ensure_user_data_exists`, `get_subfolder_path` и т.п.) — не вызываются живым кодом (grep importers: только file_dialog_helper и мёртвый setup_wizard), но полный AST-обход всех 137 модулей на `get_config_manager` выполнен grep'ом по импортам, а не полным резолвом имён — остаточный шанс непрямого вызова не нулевой.

## 6. Вопросы к Дмитрию

1. Подтверждаете интерпретацию симптома: путь проектов подхватывается из `last_directory` (`~\.supervertaler_config.json`, §2.4 гипотеза A)? Проверка на тестовой машине: удалить файл (§3 п.2) → новая сборка должна начать диалоги с Documents.
2. Чек-лист §3 включить как обязательную подготовку сценариев валидации 8.8 (и будущих ручных тестов)?
3. Исправление §4 п.5 (перенос `last_directory` внутрь user_data) — делать отдельным под-батчем после 8.x, оставить глобальное поведение сознательно, или отложить?
4. Для 8.8: согласны ли, что «чистый старт» определяется как «нет обоих файлов-указателей И `~\Supervertaler` пуст/отсутствует» — иначе автовосстановление воссоздаёт указатель на старые данные?

### Ответы Дмитрия (2026-10-03)

1. **Подтверждено (гипотеза A)** — путь проектов подхватывается из `last_directory` в `~\.supervertaler_config.json`; с поправкой к §2.3 п.2 и §2.4: при пустом пути Qt берёт рабочий каталог процесса (не Documents/MRU).
2. **Да** — чек-лист §3 использовать как временную гигиену тестов.
3. **Перенос `last_directory` в корень сборки** (рядом с `python-embed` и `SupervertalerPortable`), **НЕ в user_data**; выполнить отдельным под-батчем **P1 после 8.10**.
4. **Да** — определение чистого старта по §4 п.1 действует в переходный период.

## 7. Целевая архитектура (решение Дмитрия, 2026-10-03)

Полностью portable-инсталляция: все каталоги и файлы в одной папке, **без следов в реестре, без setup wizard, без macOS**.

Раскладка:

```
<корень>\
  python-embed\           — встроенный Python-рантайм
  SupervertalerPortable\  — код (репозиторий)
  Supervertaler\          — пользовательская папка (данные):
      workbench\  resources\  text_conversion_library\  snippet_library\  prompt_library\
  start.bat               — запуск; рабочий каталог = <корень>
```

Следствия для таблицы §1 (целевое решение по каждой строке):

| № §1 | Целевое решение |
|---|---|
| 1 | Указатель `%APPDATA%\Supervertaler\config.json` не нужен: пользовательская папка фиксирована — `<корень>\Supervertaler\`, резолвится кодом относительно корня (CWD задаёт start.bat). Автовосстановление и first-run-диалог папки упрощаются/удаляются (8.8) |
| 2 | `last_directory` хранить в корне инсталляции (рядом с `python-embed` и `SupervertalerPortable`), НЕ в user_data — под-батч P1 после 8.10 (§6 п.3) |
| 3 | QSettings/реестр MTQuickPopup убрать: геометрия — в тот же переносимый конфиг корня; реестр не используется |
| 4 | Автозапуск (HKCU Run) в portable-режиме не применять — след в реестре недопустим; пункт меню Autostart скрыть/удалить |
| 5 | `TextScaleFactor` — только чтение ОС, не состояние приложения: остаётся как есть |
| 6 | Кэш `%LOCALAPPDATA%\Supervertaler\okapi-sidecar` переносится в `<корень>\Supervertaler\` (кандидаты поиска в `okapi_sidecar.py` дополнить) |
| 7 | `~\Supervertaler` заменяется на `<корень>\Supervertaler\` (та же роль пользовательской папки); pricing.json override — туда же |
| 8 | ComDlg32-MRU — внешнее состояние ОС, кодом не устраняется; после P1 (пустых dir-вызовов для проектов нет) роль для проектов нулевая |
| 9 | CWD-зависимость устраняется фиксированным рабочим каталогом из start.bat; монолит и так передаёт абсолютные пути shortcuts.json |

---

*Docs-only. Код, реестр, user_data не изменялись. Push — после подтверждения Дмитрия.*
