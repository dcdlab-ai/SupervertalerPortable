# ОТЧЁТ BATCH P1.6 — реестр: геометрия попапа QuickTrans в ini, страховка QSettings, AA_DontUseNativeDialogs

Дата: 2026-10-30. Промпт: «BATCH P1.6» Дмитрия 2026-10-30
(`docs/refactoring/prompts/Promt - BATCH P1.6.txt`).
Основание: RECON_P1_0 (§1.1 R1, R4; §3; §4 P1.6), вердикты P1-B и P1-C (GO).
База: `fdfc1754` (docs P1-C). Роль: исполнитель. **Пуш не выполнялся. Стоп до вердикта.**

## 1. Итог

Три коммита (база `fdfc1754`, локальные):

| Коммит | Содержание |
|---|---|
| `28257adc` | **P1.6a** — геометрия попапа QuickTrans из реестра в `quicktrans.ini`: два сайта `QSettings("Supervertaler","MTQuickPopup")` в `modules/quicktrans.py` (чтение при открытии, запись в closeEvent) заменены на `QSettings(str(state_root() / "quicktrans.ini"), QSettings.Format.IniFormat)`. Старое значение `HKCU\Software\Supervertaler\MTQuickPopup` не читается и не мигрируется — геометрия один раз вернётся к значениям по умолчанию (решение координатора). Мёртвые импорты `QSettings` убраны как тривиальные: `modules/shortcut_manager.py:10` и `modules/unified_prompt_manager_qt.py:26` (проверено AST+grep: конструкторов в этих файлах нет). |
| `28a03462` | **P1.6b** — страховка QSettings в `main()` ДО `QApplication` и до любого `QSettings`: `setDefaultFormat(IniFormat)` + `setPath(IniFormat, UserScope, <data_root()>/qsettings)`. Случайная будущая запись QSettings уходит в ini-файл внутри папки данных, а не в реестр. |
| `d8997753` | **P1.6c** — `QApplication.setAttribute(AA_DontUseNativeDialogs, True)` в `main()` перед `QApplication` (однострочный коммит; откат = удалить одну строку). Все файловые диалоги становятся едиными Qt-диалогами на любой версии Windows; нативные диалоги больше не пишут MRU путей в реестр (`HKCU\...\ComDlg32`). |

Изменения строк: `Supervertaler.py` 54743 → **54763** (+20: блок P1.6b — 19 строк, строка P1.6c — 1);
`modules/quicktrans.py` 2016 → **2029** (+13: два сайта + комментарий);
`modules/shortcut_manager.py` 1094 → **1093** (−1 мёртвый импорт);
`modules/unified_prompt_manager_qt.py` 6879 → **6879** (строка импорта сокращена на имя QSettings).

Приёмка промпта — зелёная целиком (§2–§6): попап пишет/читает геометрию в `quicktrans.ini`
в корне шва; `HKCU\Software\Supervertaler` за полный цикл не изменился; `QSettings(` в продукте —
только IniFormat-сайты; `winreg` в продукте — 0; диалоги открываются. Набор 16/16 одним процессом,
regress-хэши совпали, e2e-агрегат `982e72a247f0a6ac`, smoke без новых отклонений.
Ни один диалог не сломался (вопрос «выбор папки» из промпта не возник — выбор папки работает, §4).

**Известное ограничение Qt 6.11 — в §8 (вопрос координатору).**

## 2. Гrep-гейт (М1)

`grep -rn "QSettings(" --include="*.py"` по продукту (без `docs/`, без `__pycache__`):

- `modules/quicktrans.py:832` и `modules/quicktrans.py:1571` — оба конструктора
  `QSettings(str(state_root() / "quicktrans.ini"), QSettings.Format.IniFormat)` — IniFormat;
- `Supervertaler.py:54564` — только комментарий блока страховки (конструкторов в монолите нет);
- оба мёртвых импорта удалены (P1.6a).

`grep -rn "winreg"` по продукту: **0** (совпадения только в тексте пробонаезда М3 в `docs/`).

Старых вызовов `QSettings("Supervertaler", "MTQuickPopup")` в коде не осталось —
продукт не читает и не пишет ветку реестра.

## 3. Приёмочная проба: попап → quicktrans.ini (P16-POPUP-OK 12/12)

`docs/refactoring/audits/batch-p16_probe_popup.py`, offscreen, профиль изоляции +
`SUPERVERTALER_DATA_ROOT` = профиль (шов P1-B). Цикл: создать попап → закрыть →
изменить (resize 611×317, move 73,41) → закрыть (запись) → создать заново (чтение).

Проверки (все OK):
- при первом открытии (пустой ini) геометрия по умолчанию 650×400;
- после закрытия в корне шва появился `quicktrans.ini` (это `<iso-profile>\quicktrans.ini`,
  т.е. корень сборки по шву; в реальной сборке — корень `D:\SupervertalerPortable_test\`);
- содержимое ini — ровно четыре ключа: `General/width=611`, `General/height=317`,
  `General/x=73`, `General/y=41` (именно те, что задал тест);
- заново созданный попап восстановил 611×317 @ (73,41) — цикл запись→чтение работает;
- `reg query HKCU\Software\Supervertaler` до и после пробы — идентично;
- в изолированном профиле нет `AppData\Supervertaler`, нет `.supervertaler_config.json`,
  нет каталога `qsettings/` (попап QSettings не пишет).

## 4. Спец-пробы

### 4.1 Unit страховки QSettings (P16-QS-OK 16/16)

`docs/refactoring/audits/batch-p16_unit_qsettings.py` — воспроизводит порядок `main()`
(setDefaultFormat+setPath до `QApplication`) на PyQt6 6.11 в изолированном профиле:

- вызовы `setDefaultFormat`/`setPath` **до** `QApplication` принимаются без ошибок;
- `QSettings()` без аргументов уважает defaultFormat → формат IniFormat, запись легла в
  `<data_root>/qsettings/Supervertaler/Supervertaler.ini` (Qt вкладывает имя
  organization подкаталогом в каталог setPath), значение прочитано обратно;
- явный конструктор `QSettings(IniFormat, UserScope, "ZZOrg", "ZZApp")` пишет
  `<data_root>/qsettings/ZZOrg/ZZApp.ini` — setPath работает как задано;
- **на голом старте (read-only QSettings) каталог `qsettings/` не создаётся** —
  Qt не создаёт файлов при чтении; папка появляется только при первой записи;
- AST-проверка `main()`: `setDefaultFormat@54570`, `setPath@54571`, `setAttribute@54581` —
  все три до `QApplication(sys.argv)@54583`;
- `HKCU\Software\Supervertaler` до/после unit-пробы — идентично (записи в реестр нет).

### 4.2 Смоук диалогов (AA_DontUseNativeDialogs) — P16-FD-OK 15/15

`docs/refactoring/audits/batch-p16_probe_dialogs.py`: атрибут выставлен до `QApplication`,
`app.testAttribute(...) == True`; `file_dialog_helper` во всех 4 обёртках передаёт явную
стартовую папку (`last_directory`); реальные `QFileDialog` в трёх режимах (открытие,
сохранение, **выбор папки**) открылись как Qt-виджеты (в каждом 6 списков-представлений,
рендер 704×408, стартовая папка = запрошенная). Выбор папки работает — вопроса из промпта
«что-то перестало работать» нет. Негативный контроль: в изолированном AppData ничего не появилось.

### 4.3 М3 — tripwire winreg (P16-WINREG-OK)

`docs/refactoring/audits/batch-p16_probe_winreg.py`: `sys.modules['winreg']` (и `_winreg`)
заменены объектом, который на ЛЮБОЕ обращение пишет имя в журнал и бросает исключение;
замена выполняется до импорта продукта. Полный offscreen-старт `SupervertalerQt`
(база, промпт-библиотека, хоткеи, сайдкар) + открытие/закрытие попапа QuickTrans:
- **обращений к winreg: 0** (журнал пустой);
- попап при старте прочитал геометрию из `quicktrans.ini` в корне шва (True).
Примечание метода: tripwire ловит Python-уровень; C++-запись QSettings NativeFormat
обходит модуль winreg (для этого — М4, §4.4).

### 4.4 М4 — реестр «до = после» (полный цикл на изолированном профиле)

`reg query "HKCU\Software\Supervertaler" /s` и
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v Supervertaler` сняты ДО и ПОСЛЕ
полного 16-этапного прогона. Снимки: `m4_before.txt` / `m4_after.txt`, тело снимков
(без служебных заголовков) **байтово идентично** (sha256 `4caf8b3224218b4b…` на обеих сторонах);
единственная строка диффа — мой же заголовок BEFORE/AFTER. Значения ключей в отчёт
не выписываются (факт: «до = после»). Ветка `HKCU\Software\Supervertaler` существует
на машине по историческим запускам — агент её не создавал и не менял; её удаление
(для ручного теста) — действие Дмитрия (§7).

### 4.5 qsettings-негатив

После полного цикла `find` по изолированным профилям: каталог `qsettings/` не создал
ни один этап (единственный `iso-qs` — unit-проба, которая пишет намеренно, исключена
из поиска). Голый запуск продукта не создаёт QSettings-файлов.

## 5. Набор защиты (ОДНИМ процессом, `batch-p16_run_full.sh p16`)

Все 16 этапов зелёные; логи в `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p16\`:

| Этап | Результат |
|---|---|
| fallback 9.4h, profiles 9.4f, qtchat, statusbar | OK (сегменты/профили/чат/строка статуса — как в P1-B/P1-C) |
| e2e LLM | 5 запросов; тела байтово равны эталонам p1c/p1b/qcfin; канонический агрегат `sha256(json.dumps(requests, sort_keys=True))` = **982e72a247f0a6ac** (совпадает с промптом) |
| S-clean | PROBE OK (4.5s), дерево шва на месте |
| S-upgrade | HASH-DIFF: added=[] removed=[] changed=[] (transient — индекс ассистента, известная норма) |
| regress | хэши **byte-identical**: export_simple_txt `5a12501f934a589c`, export_docx `44828d90090f046d`, export_tmx `c413d56372e69dd9` |
| smoke | **41 предмет** (Tools/PDF-Rescue — известная EXC `fitz`, не новая) |
| termbase, about | OK (окошко About v1.10.371 как в эталоне) |
| save modern / save legacy | OK (ключи api_keys/mt_quick_lookup целы) |
| r9 a / ctrl / rm | OK (профили целы, воскрешения удалённого нет) |
| 4 пробы P1.6 (§3–§4) | exit 0, вердикты зелёные |
| М4 дифф | пустой (по телу) |
| qsettings-негатив | пусто (норма) |

Пробы-копии `batch-p1b_*` переиспользованы без изменений (контракт шва не менялся).

## 6. Статика: было / стало / причина

База измерена на чистом worktree `fdfc1754`, «стало» — на чистом worktree `d8997753`
(одинаковый набор файлов, один скрипт).

| Показатель | Было (fdfc1754) | Стало (d8997753) | Причина |
|---|---|---|---|
| AST-цепочка | 875 / unresolved 0 | 875 / unresolved 0 | цепочка считает фиксированный виджетный инвентарь; новые вызовы (state_root/setPath/setAttribute/QSettings) в него не входят — счётчик не растёт, unresolved остался 0 |
| pyflakes (repo) | 541 | **539** | −2: удалены ровно предупреждения «`PyQt6.QtCore.QSettings` imported but unused» в `shortcut_manager.py:10` и `unified_prompt_manager_qt.py:26` (дифф списков предупреждений: остальное — сдвиги номеров строк; файлы `pyflakes_base_fdfc1754.txt` / `pyflakes_final_d8997753.txt`) |
| py_compile CANONICAL (вне docs/) | 108 / 0 | 108 / 0 | — |
| py_compile REFERENCE (tracked .py) | 261 / 0 | 261 / 0 → **265 / 0** после docs-коммита | +4 новых проб в audits (прошли py_compile) |
| headless imports | 89 ok / 2 fail | 89 ok / 2 fail | известные fail: `setuptools`, `fitz` |
| grep-gate (batch9-3) | CLEAN | CLEAN | — |
| grep QSettings( продукт | 2 NativeFormat-сайта попапа | 2 IniFormat-сайта попапа | P1.6a |
| grep winreg продукт | 0 | 0 | — |

Методическая заметка (для следующих прогонов): `batch8-15_run_pyflakes.py` содержит
жёсткий `os.chdir` в `E:\Dev\SupervertalerPortable` — при запуске из worktree pyflakes
шаг сканирует основную рабочую копию, а не worktree (в логах `base_wt.log`/`final_wt.log`
строка pyflakes = скан основной копии; в основной копии файлы продукта совпадают с
`d8997753`, поэтому 539 там честное финальное число). Канонические базейн/финал этого
отчёта взяты параметризованным прогоном по worktree (скрипт в §6 артефакты).

## 7. Для Дмитрия

### 7.1 Пакет тестовой сборки (D:\SupervertalerPortable_test)

Заменить 4 файла копией из репозитория (свежий коммит `d8997753`):
`Supervertaler.py`, `modules\quicktrans.py`, `modules\shortcut_manager.py`,
`modules\unified_prompt_manager_qt.py`. Ничего больше не менять; `start.bat`/`_pth` не трогать.
После первого запуска в корне `D:\SupervertalerPortable_test\` появится файл `quicktrans.ini`.

### 7.2 Ручные тесты

**T-P1.6a (обязательный, только Дмитрий, вручную). Цель: геометрия попапа QuickTrans
сохраняется в файл сборки, а не в реестр Windows.**
Подготовка (один раз, вручную): удалить ветку реестра — нажмите Win+R, введите `regedit`,
Enter; в дереве слева откройте `HKEY_CURRENT_USER\Software`; правой кнопкой мыши
на папке `Supervertaler` → Удалить (подтвердить). Восстанавливать не нужно —
программа туда больше не пишет. Агент реестр не трогает.
Шаги: 1) запустите `D:\SupervertalerPortable_test\start.bat`; 2) нажмите Ctrl+Alt+Q —
появится маленькое окно быстрого перевода (по умолчанию ~650×400); 3) перетащите его
за заголовок в новое место и потяните за край, изменив размер; 4) закройте окно быстрого
перевода (крестик на самом попапе); 5) закройте программу; 6) запустите снова и снова
нажмите Ctrl+Alt+Q.
Ожидание: окно открылось в том же месте и того же размера, что при закрытии; в папке
`D:\SupervertalerPortable_test\` появился текстовый файл `quicktrans.ini` (в нём числа
width/height/x/y); в regedit папки `Supervertaler` в `HKEY_CURRENT_USER\Software` НЕТ
(ветка не воссоздалась).
Провал: размер/позиция потерялись после перезапуска; `quicktrans.ini` не появился;
ветка реестра появилась заново.
Замечание: при первом запуске после обновления размер станет по умолчанию — это ожидаемо
(старые реестровые значения сознательно не переносятся).

**T-P1.6b (обязательный). Цель: единые Qt-диалоги, старт в последней папке.**
Шаги: 1) запустите тестовую сборку; 2) Файл (File) → «Open Project…» — посмотрите,
в какой папке открылся диалог; отмените; 3) откройте любой файл в диалоге «Save As…»
(Файл → Save Project As…), отмените; 4) снова File → Open Project…
Ожидание: стартовая папка диалога = папка, где вы выбирали файл в прошлый раз;
диалог выглядит одинаково на всех шагах (единый Qt-вид: свой список файлов, без
нативной боковой панели Windows); выбор папки (например, в диалогах терминологической
базы) работает.
Провал / «не устроит вид»: откат — удалить одну строку в `Supervertaler.py`
(строка с `AA_DontUseNativeDialogs`, помечена комментарием P1.6c), это ровно коммит `d8997753`.

**T-P1.6c (обязательный). Цель: обычная работа не сломалась.**
Шаги: откройте свой рабочий проект (File → Open Project…, выберите файл проекта),
переведите один сегмент, сохраните проект (Ctrl+S / File → Save Project).
Ожидание: всё работает как в P1-B/P1-C (проект открылся, перевод появился, сохранение прошло).

Необязательные проверки покрыты пробами: геометрия-цикл — P16-POPUP, старт QSettings —
P16-QS-OK, диалоги — P16-FD-OK, реестр неприкосновенен — М3/М4.

## 8. Вопросы координатору

1. **Ограничение Qt 6.11 (принято как факт, зафиксировано unit-пробой):** конструктор
   `QSettings("org", "app")` с двумя аргументами в Qt 6 **жёстко NativeFormat** —
   `setDefaultFormat`/`setPath` его не перекрывают. Страховка P1.6b покрывает
   `QSettings()` без аргументов и конструкторы с явным IniFormat; 2-аргументный
   конструктор в Windows по-прежнему пойдёт в реестр. Дословная формулировка приёмки
   «любое будущее случайный QSettings(org, app) пишет ini» на уровне Qt недостижима.
   Правила батча («вопрос в отчёт, не обходить») соблюдены: не обходили, сообщаем.
   Варианты на решение координатора: (а) принять как есть (в продукте 2-аргументных
   конструкторов не осталось — гейт §2 это подтверждает); (б) добавить в статический
   гейт запрет 2-аргументного `QSettings(` в продукте (кандидат в 8.18);
   (в) ничего.
2. Ветка `HKCU\Software\Supervertaler` (и значение в `...\CurrentVersion\Run`
   «Supervertaler», если оно есть на машине) осталась от исторических запусков —
   продукт её больше не создаёт. Удаление остатков — на усмотрение Дмитрия
   (T-P1.6a удаляет ветку реестра вручную перед тестом).

## 9. Среда и дисциплина

- CWD `E:\Dev\SupervertalerPortable`; интерпретатор `E:\Dev\python-embed\python.exe`;
  pyflakes — внешний `qa/env/pyflakes-ext` (рантайм не тронут).
- Все прогоны продукта — offscreen (`QT_QPA_PLATFORM=offscreen`) с
  `SUPERVERTALER_DATA_ROOT` = изолированный профиль (шов P1-B); USERPROFILE/APPDATA/
  LOCALAPPDATA/HOME указывали на изолированный профиль как негативный контроль.
- **Реестр пользователя не тронут на запись**: только `reg query` (чтение) как метод М4;
  значения в отчёт не выписаны.
- Артефакты этапа: `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p16\`
  (логи проб, снимки М4, логи набора, worktree `basewt`/`wtfinal` — сняты после замеров).
- Сирот python/java после прогонов нет. Выжившие сторонние процессы (командные строки
  проверены, не тронуты): PID 18952 и 31980 (Strata, пользовательские серверы).
  Убийство по имени образа не применялось.
- Коммиты локальные (`28257adc`, `28a03462`, `d8997753` + docs-коммит этого отчёта).
  **Пуш не выполнялся. Стоп до вердикта координатора.**
