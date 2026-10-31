# ОТЧЁТ BATCH P1.8 — Финал портативности: start.bat, батарея проверок, чек-лист «чистый старт»

База: `origin/main` после пуша P1.7 (HEAD `7fa2de8c`, код P1.7 `05ebd2b9` + docs `050fc755`).
Промпт Дмитрия 2026-10-31. Рабочая область: `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p18\`.

## 1. Итог одной строкой

**Код продукта не менялся (0 продуктовых файлов).** Поставка: шаблон `docs/templates/start.bat`
(+ его изолированный прогон), чек-лист `docs/templates/clean_start_checklist.md`, гейт
двухаргументного `QSettings(` в `batch9-3_grep_gate.py`, инвентаризационная проба
`batch-p18_probe_inventory.py` и батарея М1+М3+М4 `batch-p18_clean_start_battery.py` одним
скриптом — всё зелёное: вне корня сборки приложение не пишет ничего; реестр неприкосновенен;
статика и сюита 16 этапов — байт-в-байт эталонные.

## 2. Часть A — что продукт и рантайм пишут вне дерева сборки

Метод: offscreen-проба `batch-p18_probe_inventory.py <tree> <iso> <tag> <clean|full> [tripwire]`
(репозиторий как код, изолированный каталог `iso` имитирует реальную среду:
`USERPROFILE`/`HOME` → iso, `APPDATA` → `iso\AppData\Roaming`, `LOCALAPPDATA` → `iso\AppData\Local`,
`TEMP`/`TMP` → `iso\tmp`; всё, что появилось в этих зонах iso, = то, что БЕЗ изоляции попало бы
в реальные `%USERPROFILE%`/`%APPDATA%`/`%LOCALAPPDATA%`/`%TEMP%`). Шов `SUPERVERTALER_DATA_ROOT`
→ data root = `iso\Supervertaler` (в реальной сборке — `<корень>\Supervertaler`, внутри дерева).

Два прогона (верdict обоих **P18-INV-OK**):
* **clean** — полностью пустой iso, без сидов: старт → попап QuickTrans → закрытие;
* **full** — сид только settings.json (профиль custom_openai → фейк-сервер): старт → попап →
  импорт sample txt (5 сегментов) → перевод через фейк-сервер («Goedemorgen») →
  сохранение проекта (`Documents\test_proj\test_proj.svproj` — модель «собственная папка проекта»,
  `nest_in_own_folder`; versioned backup в data root) → закрытие.

### 2.1 Таблица «что реально появилось» (полный цикл)

| Зона iso (= реальная зона без изоляции) | Что появилось | Вывод |
|---|---|---|
| `iso\AppData\Roaming`, `iso\AppData\Local` (= %APPDATA%/%LOCALAPPDATA%) | **ничего (0 записей)** | чисто |
| `iso\Desktop`, `iso\Downloads` | ничего | чисто |
| `iso\Documents` | только сам сохранённый проект `test_proj\test_proj.svproj` (+ `source\test.txt`) — сознательное действие «Сохранить как» | не утечка |
| `iso\tmp` (= %TEMP%) | **ничего (0 записей)** — цикл без Superlookup-операций; класс T1–T3 (AHK/PowerShell-скрипты вставки) остаётся теоретическим, закрывается TEMP→`<корень>\temp` в start.bat | чисто |
| корень iso (= ~ / build root) | `quicktrans.ini` (сервисный файл state_root, в реальной сборке — в корне сборки); `last_directory.json` — не появился (файловых диалогов с выбором не было, fdh-заглушки его не пишут) | внутри дерева |
| `iso\Supervertaler\` (data root) | см. чек-лист §7: prompt_library (6 промптов), `resources\supervertaler.db`(+wal/shm), `workbench\{ai_assistant, dictionaries, settings, backups, usage}` | ожидаемо |
| реестр (М4, `reg query HKCU\Software\Supervertaler /s` + Run-значение, до/после) | **дифф пуст** в обоих прогонах | чисто |
| реальная среда (сентинелы: `%APPDATA%\Supervertaler`, `%LOCALAPPDATA%\Supervertaler`, `~\.supervertaler_config.json`, `~\Supervertaler\`, `~\.config\autostart\…`, quicktrans.ini/last_directory.json во всех трёх зонах) | новые записи не появились; существующие исторические (`%APPDATA%\Supervertaler` — пустой, `%LOCALAPPDATA%\Supervertaler\okapi-sidecar` ~27 МБ от прежних версий) — не изменились (снимок «до/после» по rel+size) | чисто |
| `__pycache__` | рассыпается по кодовому дереву (внутри корня сборки) → решение Части B: `PYTHONPYCACHEPREFIX=<корень>\pycache` | внутри дерева, централизовано |
| кэши Qt/pip/matplotlib/QtWebEngine | не появились (PyQt6 без WebEngine в дев-рантайме; pip/matplotlib не используются продуктом) | чисто |

Локальный журнал `Supervertaler\workbench\usage\usage-<ГГГГ-ММ>.jsonl` — это
`modules/usage_log.py` (метаданные AI-вызовов: модель, токены, стоимость; без текстов), пишется
в data root, не сеть. Не трогался.

### 2.2 Диалог «Okapi не установлен» (без правок, по запросу промпта)

Код: `Supervertaler.py:29036–29136` (диалог) + `modules/okapi_sidecar.py` (скачивание).

| Вопрос промпта | Ответ (проверено по коду) |
|---|---|
| Создаёт ли что-то вне `<data_root>\okapi-sidecar`? | **Нет.** Windows-ветка качает ZIP во временный файл `<data_root>\okapi-sidecar-download.zip`, распаковывает в data root (JAR+JRE), штамп `.version` рядом; не-Windows — JAR прямо в `okapi-sidecar\` (tmp-файл там же, атомарная замена). Временные файлы — внутри data root, удаляются. |
| Ходит ли в сеть без действия пользователя? | **Нет.** Диалог показывается только когда JAR не найден (путь 3, `is_installed()`=False) и сеть трогается только после ответа **Yes** на `QMessageBox.question` «Download Okapi sidecar?» |
| Нужен ли диалог при ручной установке JAR? | **Нет.** Достаточно положить `okapi-sidecar.jar` в `<корень>\Supervertaler\okapi-sidecar\` и перезапустить приложение: `_resolve_sidecar_dir()` находит data-root-кандидат при старте, диалог не показывается. |
| «4→2 варианта скачивания» | После P1.7 два: Windows ~70 МБ ZIP (JAR+собственная JRE, системная Java не нужна); Linux ~28 МБ JAR (требует системной Java, перед скачиванием проверяется `_find_java()`). macOS-варианты удалены в P1.7. |

Решение — за Дмитрием; по умолчанию предлагаю оставить как есть (добавлено в чек-лист сборки).

## 3. Часть B — шаблон `docs/templates/start.bat`

Решения (по промпту + данным Части A):

| Пункт | Решение | Обоснование |
|---|---|---|
| Каталог запуска | `cd /d %~dp0` (корень сборки), запуск `python-embed\python.exe SupervertalerPortable\Supervertaler.py` | по промпту (консольный python.exe — как в тестовой сборке) |
| `TEMP`/`TMP` | `<корень>\temp` (каталог создаёт скрипт) | класс T1–T3 остаётся внутри корня (RECON §1.5) |
| Редирект профиля | **нет** (QP1.12) | Часть A подтвердила: без редиректа вне корня не пишется ничего; редирект маскировал бы регрессии |
| Байткод | `PYTHONPYCACHEPREFIX=<корень>\pycache` (не PYTHONDONTWRITEBYTECODE) | по Части A `__pycache__` внутри дерева, но рассыпан по коду; централизация держит `SupervertalerPortable\` байт-чистой против репозитория; полное отключение кэша замедляло бы каждый старт (рекомпиляция монолита) |
| JAVA_HOME/PATH | не прописываются | Windows-ZIP Okapi несёт собственную JRE (QP1.11) |
| Комментарии | коротко, по-английски | по промпту |

### 3.1 Изолированный прогон шаблона и НАХОДКА

Прогон в фиктивном корне сборки `...\batch-p18\buildtest\` (не `D:\SupervertalerPortable_test`):
`SupervertalerPortable\` — робокопия кода (без `.git`, `docs`, `__pycache__`), `python-embed\` —
локальная копия рантайма (хардлинки файлов + junction на `Lib`), start.bat — из шаблона;
профиль-зоны → пустой iso (негативный контроль), `QT_QPA_PLATFORM=offscreen`.

**Находка 1 (сборочное требование):** первый прогон упал
(`ModuleNotFoundError: No module named 'modules'`). Причина: embedded-интерпретатор игнорирует
CWD (`python313._pth`); дев-рантайм `_pth` не содержит код. `start.bat` это НЕ компенсирует —
**`python313._pth` сборки обязан содержать строки `..\SupervertalerPortable` и
`Lib\site-packages`** (как в тестовой сборке `D:\SupervertalerPortable_test`). В шаблон не
зашивается (файл рантайма, не батча); зафиксировано в чек-листе §7 и в комментарии шаблона.
После добавления строк в локальный `_pth` — запуск успешен.

Результат прогона (приложение стартовало, проработало, закрыто по PID):
* `temp\` и `pycache\` созданы скриптом/питоном; `temp\` пуст;
* data root `<корень>\Supervertaler\{prompt_library, resources, workbench}` создан приложением
  (как в clean-пробе Части A);
* `SupervertalerPortable\` не оброс `__pycache__` (байткод в `pycache\`);
* iso (профиль-зоны) — **0 файлов**;
* `reg query` до/после — **дифф пуст**.

## 4. Часть C — гейт двухаргументного `QSettings(`

Расширен `docs/refactoring/audits/batch9-3_grep_gate.py` (AST-секция «QSettings constructor gate,
P1.8 Part C», место исполнения M1 — вердикт P1.6):

* **FAIL**: `QSettings` с ≥2 позиционными аргументами, все — строковые константы
  (`QSettings("org","app")` — Qt 6 принудительно NativeFormat независимо от
  `setDefaultFormat(IniFormat)`); и любой аргумент, упоминающий `NativeFormat`.
* **OK**: 1-арг, `QSettings(путь, IniFormat[, parent])` (два существующих сайта quicktrans.py:832/1571
  — именно эта форма), счёт сайтов печатается.
* Добавлен необязательный `argv[1]` = корень дерева (для самотеста; дефолт — репозиторий).

Проверка: на продукте **CLEAN, exit 0**; на тестовой подмене (стейдж-копия с инъекцией
`QSettings("Acme","Injector")` и `NativeFormat` в `quicktrans.py`) — **GATE-QS-FAIL, exit 1**,
обе инъекции пойманы с точными строками.

## 5. Часть D — батарея М1+М3+М4 одним скриптом + чек-лист

`docs/refactoring/audits/batch-p18_clean_start_battery.py` (один вход, результат
**P18-BATTERY-OK**, JSON `...\batch-p18\battery_p18.json`):

| Метод | Реализация | Результат |
|---|---|---|
| М1 (статика) | в процессе: `winreg`/`_winreg` в коде продукта = **0**; литералы `HKCU`/`CurrentVersion\Run` = **0**; чтения env `APPDATA`/`LOCALAPPDATA`/`USERPROFILE` = **0**; QSettings-аудит AST: монолит 0 сайтов, quicktrans.py 2 сайта (обе IniFormat), нарушений 0 | OK |
| М3 (tripwire) | субпроцесс `batch-p18_probe_inventory.py` в режиме **full + tripwire** (подмена `sys.modules['winreg']` ДО импортов продукта; полный цикл: старт, попап, импорт, перевод через фейк-сервер, сохранение, закрытие) | OK — заблокированных обращений 0 |
| М4 (reg query) | `reg query HKCU\Software\Supervertaler /s` + `HKCU\...\Run /v Supervertaler` до/после, дифф по телу (декод OEM — reg.exe говорит в OEM-кодировке) | **дифф пуст** |
| Файловые зоны | iso\AppData пуст; сентинелы реальной среды «до/после» без новых записей | OK |

### 5.1 Находка 2: чтение прокси стандартной библиотекой (вопрос координатору — Q1)

Первая версия М3 с полным запретом ЛЮБЫХ обращений к winreg поймала **одно обращение
`OpenKey`** и уронила перевод. Стек: `urllib.request.getproxies_registry()` →
`HKCU\...\Internet Settings` — **стандартная библиотека Windows** читает настройки прокси при
ПОСТРОЕНИИ ПРОКСИ-КАРТЫ перед каждым исходящим HTTP(S)-запросом (здесь — запрос к LLM;
любая реальная сетевая операция продукта проходит через это). Это:

* только **ЧТЕНИЕ** (записи нет — это доказывается М4 глобально, включая C++-уровень);
* машинно-глобальное, но не «след Supervertaler»: ключ общий для всех Windows-приложений,
  ничего не создаёт и не меняет;
* неизбежное без патчинга stdlib или принудительных env-прокси.

М3 доработан: обращения из пути stdlib-прокси-детекции (`getproxies*`/`proxy_bypass` в стеке)
пропускаются к настоящему winreg с записью в лог `PASSTHROUGH`; всё остальное по-прежнему
блокируется. Итог прогона: ровно 3 PASSTHROUGH-записи (OpenKey/HKEY_CURRENT_USER/QueryValueEx —
одна прокси-детекция), 0 заблокированных, перевод/сохранение успешны.

**Вопрос Q1:** принять это чтение как «строго неизбежное» (рекомендую; альтернативы —
патчить stdlib в сборке или задавать фиктивные env-прокси в start.bat — не рекомендую)?

## 6. Статика: было / стало / причина

Все числа — на базе P1.7; расхождений нет (код не менялся). Дельты объясняются только
новыми/изменёнными audit-скриптами.

| Метрика | Было (P1.7) | Стало (P1.8) | Причина расхождения |
|---|---|---|---|
| AST chain | 875 / 0 | **875 / 0** | нет |
| pyflakes | 536 | **536** (те же 4 undefined-name: filedialog 2, messagebox 19, tk 100, ttk 5) | нет |
| py_compile canonical | 108 / 0 | **108 / 0** | нет (новые скрипты — в `docs/`) |
| py_compile reference | 265 / 0 | **265 / 0** | нет на момент замера; **после коммита станет 267** (три новых .py в audits: probe, battery, +existing gate) |
| headless | 89 / 2 (setuptools, fitz — известные) | **89 / 2** (те же) | нет |
| grep-gate | CLEAN | **CLEAN** + секция QSettings CLEAN | расширение Части C |
| гейт QSettings | — (нет) | CLEAN на продукте, FAIL (exit 1) на подмене | Часть C |

## 7. Чек-лист «чистый старт»

Готовый документ: **`docs/templates/clean_start_checklist.md`** (замена E1 §3). Суть:
«удалить папку сборки — и всё». После первого запуска в корне сборки разрешены:
`temp\`, `pycache\`, `quicktrans.ini`, `last_directory.json`, data root `Supervertaler\`
(prompt_library с 6 промптами, `resources\supervertaler.db`±wal/shm, `workbench\{ai_assistant,
dictionaries, settings, backups, usage}`); после закрытия состав не меняется. Чего быть не
должно: ключа `HKCU\Software\Supervertaler`, значения `Supervertaler` в HKCU Run, пополнения
`%APPDATA%\Supervertaler`/`%LOCALAPPDATA%\Supervertaler` (исторические остатки прежних версий
должны остаться нетронутыми), `~\.supervertaler_config.json`, `~\Supervertaler\`,
`~\.config\autostart\supervertaler.desktop`, новых файлов в системном %TEMP%, чего-либо в
Documents кроме самосохранённого пользователем, `__pycache__` внутри кода. Плюс сборочное
примечание про `_pth` (Находка 1) и ручную установку Okapi JAR.

## 8. Набор 16 этапов одним процессом

`bash docs/refactoring/audits/batch-p1b_run_full.sh p18`, лог `...\batch-p18\suite_p18.log`:

| Этап | Результат |
|---|---|
| fallback 9.4h, profiles 9.4f, qtchat, statusbar | OK (как в P1-B…P1.7) |
| e2e LLM | 5 запросов; тела байтово равны эталонам **qcfin / p1b / p1c / p16**; канонический агрегат `sha256(json.dumps(requests, sort_keys=True))` = **982e72a247f0a6ac…** (эталон совпал полностью) |
| S-clean | PROBE OK (2.2s) |
| S-upgrade | HASH-DIFF пуст: added=[] removed=[] changed=[] |
| regress | хэши **byte-identical**: export_simple_txt `5a12501f934a589c`, export_docx `44828d90090f046d`, export_tmx `c413d56372e69dd9`; сегменты 5/5/4 |
| smoke | **41 предмет** — только известная fitz-EXC, новых нет; SMOKE OK |
| termbase | REGRESS-TB OK |
| about | OK (About v1.10.371 как в эталоне) |
| save modern / save legacy | OK (api_keys целы) |
| r9 a / ctrl / rm | OK (профили целы) |

Плюс вне сюиты: пробы Части A (clean/full — P18-INV-OK), батарея Части D (P18-BATTERY-OK),
прогон шаблона start.bat в изолированной копии (§3.1).

## 9. sha256 поставки (форма: два вида с подписью)

Код продукта не менялся — таблица «до/после» неприменима; ниже поставка батча (все файлы в
`docs/`). «Блоб (LF)» = содержимое, как ляжет в git (`core.autocrlf=true`); «рабочая копия» =
файл на диске. `start.bat` намеренно CRLF в рабочей копии (формат .bat), остальные — LF,
рабочая копия = блобу. Замер до записи отчёта/PROJECT_STATUS.

| Файл | блоб (LF) | рабочая копия |
|---|---|---|
| `docs/templates/start.bat` (новый) | `f86007c3d459636075ecf458510d3aac323ffadb242a43ae4b2c8f957a929d14` | `173d2148c5b25f5e995544e35cb5b500d1ad7106bbdd3b387f5e3ea67eb5bedb` (CRLF) |
| `docs/templates/clean_start_checklist.md` (новый) | `36d004640000438e794f219d5d039a96bd870bc691ec2fad29ddfd98e46cd2d5` (блоб коммита `786f02fb`; ранее в замер попала версия с опечаткой — исправлена до коммита) | = блобу (LF) |
| `docs/refactoring/audits/batch-p18_probe_inventory.py` (новый) | `3b8ff8b147efe48ab8901330af80e86445c0d69045b3c5494a08f705540a13c3` | = блобу (LF) |
| `docs/refactoring/audits/batch-p18_clean_start_battery.py` (новый) | `6f39f722e9455d666c46cf994cc5ccac5e609b2bdd49c8360f1b2df2b7c00d0e` | = блобу (LF) |
| `docs/refactoring/audits/batch-p18_static_run.sh` (новый) | `d2f9480a95f24c2adaaec231b34f6e15b7e8314b81d8afbf448925c03ded95fc` | = блобу (LF) |
| `docs/refactoring/audits/batch9-3_grep_gate.py` (был `4e36e831f40a4d433b1548f248aba1120279cae6553a62a04078c757083f4970`, git-объект `8dce5088`) | `caadaaec1c8a639d95fd2c3c57d9e7686caa36054f6ff9eac4038a9bec3fc26a` | = блобу (LF) |

`git status` по продукту: **0 изменённых продуктовых файлов**; изменён только
`batch9-3_grep_gate.py` + 5 новых файлов.

## 10. Ручные тесты для Дмитрия

Оба теста выполняются после пересборки финальной сборки (отдельное решение — QP1.8): свежая
копия репозитория в корень сборки, `python-embed\` рядом, `python313._pth` с двумя строками
(`..\SupervertalerPortable` и `Lib\site-packages`), `start.bat` из `docs/templates/`.

### T-P1.8a — «чистый старт» по чек-листу (обязательный)

1. **Цель:** убедиться, что с нуля сборка полностью работает и всё своё пишет только в корень сборки.
2. **Подготовка:** собрать папку сборки по чек-листу `docs/templates/clean_start_checklist.md` (см. выше); других приготовлений не нужно.
3. **Шаги:**
   1. Дважды щёлкнуть `start.bat` в корне сборки. Дождаться главного окна (первый старт — до минуты).
   2. Открыть попап быстрого перевода (`Ctrl+Alt+Q` или меню Tools → QuickTrans), закрыть его крестиком.
   3. Создать новый проект: File → New Project → выбрать текстовый файл с пару строками (например `E:\Dev\Work_temp\SupervertalerPortable\refactoring\b9-3\inputs\test.txt`).
   4. Сохранить проект: File → Save Project As → выбрать папку `Documents` → Save.
   5. Закрыть приложение.
4. **Ожидаемый результат:** в корне сборки появились: папки `temp\` и `pycache\`, файл `quicktrans.ini`, папка `Supervertaler\` (внутри — `prompt_library\`, `resources\supervertaler.db`, `workbench\…`); в `Documents` — папка проекта с файлом `.svproj`; **внутри папки `SupervertalerPortable\` нет папок `__pycache__`**. Полный список — «Что ДОЛЖНО появиться» в чек-листе.
5. **Провал:** какого-то пункта «Что ДОЛЖНО» нет; или в `SupervertalerPortable\` появились `__pycache__`; или `temp\` не создан.

### T-P1.8b — «снаружи ничего» (обязательный)

1. **Цель:** убедиться, что после работы приложение ничего не оставило вне папки сборки.
2. **Подготовка:** сразу после T-P1.8a.
3. **Шаги:**
   1. Нажать `Win+R`, ввести `%APPDATA%`, Enter — убедиться, что папка `Supervertaler` отсутствует или (если осталась от старых версий) не изменилась по содержимому. То же для `%LOCALAPPDATA%`.
   2. Открыть `Documents` — там только ваш сохранённый проект из T-P1.8a, никаких других новых папок/файлов.
   3. Нажать `Win+R`, ввести `cmd`, Enter, в чёрном окне выполнить:
      `reg query "HKCU\Software\Supervertaler" /s`
      затем
      `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v Supervertaler`
4. **Ожидаемый результат:** обе команды отвечают «Не удается найти указанный раздел реестра» / «не удается найти указанный параметр».
5. **Провал:** ключ/параметр найден; в `%APPDATA%`/`%LOCALAPPDATA%` появилась новая папка `Supervertaler`; в `Documents` появились служебные файлы приложения.

## 11. Вопросы координатору

### 11.1 Ответы координатора (Дмитрий, 2026-10-31; вердикт: GO)

1. **Q1 (stdlib-прокси-чтение): ПРИНЯТО как неизбежное.** Только чтение настроек Windows,
   записи нет; tripwire пропускает именно этот стек (`getproxies*`) и блокирует всё
   остальное — гарантия «продукт в реестр не пишет» сохраняется.
2. **Q2 (шаблон start.bat): ОСТАВЛЯЕТСЯ.** `PYTHONPYCACHEPREFIX=<корень>\pycache` — да;
   запуск через `python.exe` с консольным окном — да: в консоли видны ошибки локальных
   моделей и логи.
3. **Q3 (диалог Okapi): ОСТАВИТЬ как есть.** Ничего не пишет вне `Supervertaler\okapi-sidecar\`,
   качает только после явного «Yes» пользователя.

Вердикт по BATCH P1.8: **GO**. Пуш разрешён (без force), состав: `7fa2de8c` + коммиты P1.8
(включая `786f02fb`) + коммиты упаковщика и правки AGENTS.md. Перед пушем — проверка, что
продукт не затронут: `git diff --stat origin/main..HEAD -- Supervertaler.py modules
translations assets` должен быть пустым.

1. **Q1 (§5.1):** чтение прокси stdlib (`urllib.getproxies_registry` → `HKCU\...\Internet Settings`,
   read-only, перед каждым исходящим HTTP) — принять как «строго неизбежное» с PASSTHROUGH в М3?
   Рекомендую: да. Записей в реестр по-прежнему ноль (М4), файловых следов ноль.
2. **Q2:** подтверждение решений шаблона: `PYTHONPYCACHEPREFIX=<корень>\pycache` (а не
   PYTHONDONTWRITEBYTECODE — медленный старт) и запуск через `python.exe` (консольное окно,
   как в тестовой сборке; при желании `pythonw.exe` — правка одной строки шаблона).
3. **Q3:** диалог Okapi (§2.2) — оставить как есть (скачивание по явному Yes, всё внутри
   `<data_root>\okapi-sidecar`; ручная установка JAR обходится без диалога).

## 12. Ограничения

* Пробы выполнялись offscreen; нативные диалоги в продукте устранены ранее
  (AA_DontUseNativeDialogs, состав P1 п.8), файловые диалоги в пробах — заглушки;
  М6 (Process Monitor) остаётся опциональным ручным протоколом Дмитрия после пересборки.
* Класс T1–T3 (%TEMP%-следы Superlookup/AHK) в цикле проб не исполнялся — операций вставки не
  было; зона закрыта конструктивно (TEMP→`<корень>\temp` в шаблоне) и проверена только тем,
  что `temp\` создан и пуст.
* Сценарий скачивания Okapi по сети в пробах не запускался (не дёргали сеть GitHub); вывод §2.2 —
  по коду.

## 13. Дополнение (после доставки отчёта, 2026-10-31)

По прямой просьбе Дмитрия добавлен упаковщик `docs/templates/make_portable_zip.bat`:
собирает корень сборки (чистая копия кода, рантайм с пропатченным `python313._pth`,
start.bat из шаблона), смоук-импорт монолита через `_pth` до упаковки, ZIP в
`E:\Dev\Work_temp\SupervertalerPortable\build\supervertaler-portable_<дата_время>.zip`.
Проверен end-to-end (сборка + распаковка в чистый каталог + запуск start.bat offscreen
с изолированным профилем).

Сухой прогон T-P1.8a Дмитрием на распакованном архиве (`D:\Supervertaler_clean`, только чтение)
дал два уточнения:

1. **Баг упаковщика №1 (исправлен):** смоук-импорт (шаг 5) выполнялся после чистого копирования
   и оставлял `__pycache__` (1 файл) в кодовой папке, который уезжал в zip. Фикс:
   `PYTHONDONTWRITEBYTECODE=1` на время смоука. Старый zip `…1602.zip` содержал 102 таких
   записи (+ `okapi-sidecar`, см. п.2); новый `…1814.zip` — 0.
2. **Не баг, но уточнено:** `SupervertalerPortable\okapi-sidecar\` в архиве — исходники
   Java-сборщика из репозитория (109 КБ, без JAR/JRE), в портативную сборку не входят —
   исключён в упаковщике. В data root (`Supervertaler\okapi-sidecar\`) каталог появляется
   ТОЛЬКО после скачивания Okapi по кнопке диалога или ручной установки JAR (у Дмитрия в
   распаковке его не было — чисто).
3. **Чек-лист дополнен** (по реальному GUI-прогону Дмитрия): `Supervertaler\workbench\logs\supervertaler.log`
   (+ `supervertaler-previous.log` после ротации, ~2 МБ, макс. 2 файла) — диагностический журнал,
   создаётся в `main()` при запуске через start.bat (offscreen-пробы его не имели, т.к. создают
   окно напрямую, минуя `main()`); `workbench\usage\usage-<ГГГГ-ММ>.jsonl` — только после первого
   AI-вызова (у Дмитрия не было — корректно).
4. Вопрос T-P1.8a №1: «Documents» в чек-листе — это Documents **профиля пользователя**
   (`C:\Users\<я>\Documents`); приложение пишет туда только то, что пользователь сохраняет
   сам через Save As — служебных файлов приложения там быть не должно.
5. **T-P1.8a/T-P1.8b — оба ПОДТВЕРЖДЕНЫ Дмитрием 2026-10-31** (распаковка → запуск →
   настройка → перевод сегмента → пакетный перевод → QuickTrans → выход; полная сверка
   `D:\Supervertaler_clean` по чек-листу агентом — совпадение по всем пунктам: корень
   сборки, data root, сервисные файлы, temp/pycache, отсутствие запрещённого). Уточнение
   упаковщика №2: из дистрибутива исключены dev-документы и dev-инструменты кодовой папки
   (топ-уровневые `*.md`, `.gitattributes`, `.gitignore`, `scripts\`, `tools\`); оставлен
   `pyproject.toml` — он читается рантаймом (`Supervertaler.py:57`, фолбэк версии).
   Дистрибутив пересобран: `supervertaler-portable_20261031_1843.zip` (334 878 720 байт),
   кодовая папка = `Supervertaler.py, assets, modules, pyproject.toml, requirements.txt,
   setup.py, translations, user_data` — проверено распаковкой.
6. **Решение Дмитрия (2026-10-31): `D:\Supervertaler_clean\` — тестовая сборка** для ручных
   сценариев T-*.x: распакованный дистрибутив `…1843.zip` (продукт = HEAD после P1.8), без
   `.git` и без редиректа профиля (QP1.12 — все данные в корне сборки); пересборка —
   повторный запуск `make_portable_zip.bat` + распаковка свежего zip. Раздел «Frozen test
   build» в AGENTS.md переписан (старая сборка `D:\SupervertalerPortable_test\` с
   замороженным `.git 960be5d8`, редиректом профиля и WebEngine — историческая). Нюанс
   зафиксирован: в новом дистрибутиве НЕТ PyQt6-WebEngine (как и в дев-рантайме) — Web
   Resources в fallback-режиме; добавление WebEngine в дистрибутив — отдельное сборочное
   решение.
