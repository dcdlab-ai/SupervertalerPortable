# ОТЧЁТ BATCH P2.3 — requirements: обязательные + опциональные, lock-файл

* Дата: 2026-11-01. Исполнитель: агент (роль-дисциплина: координатор/исполнитель).
* База: origin/main после пуша P2.2 (`abf741d1`; HEAD на старте батча `610d32c1` — push-record коммит поверх базы, продукт в нём не тронут).
* Промпт: Дмитрия (BATCH P2.3). Рабочая область: `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p23\`.
* Суть: сплит зависимостей на обязательные/опциональные, lock-файл по версиям проверенного дистрибутива P2.1, заметка о пересборке рантайма. **Код продукта и dev-рантайм `E:\Dev\python-embed` не менялись.**
* Статус: отчёт доставлен, **ПУША НЕТ — жду вердикта.**

---

## §1 Часть A — рекон (без правок)

Метод: AST-скан внешних импортов продукта (копия `p2-0_scan_b_imports.py` с выводом в
batch-p23: `docs/refactoring/audits/p2-3_scan_b_imports.py`, вывод `p2-3_imports_scan.out`,
сырой JSON `p2-3_imports_raw.json`) на текущем HEAD. Классификация как в P2.0:
mandatory (top-level вне try) / guarded (top-level в try/except) / lazy (внутри функций).
Спорные корни дополнительно проверены grep-ом и проверкой существования внутренних модулей.

### §1.1 Таблица: пакет → где импортируется → решение

| Пакет (PyPI) | Импорт в продукте | Тип | Решение |
|---|---|---|---|
| PyQt6 | 94 top-level mandatory + 6 guarded + 265 lazy сайтов | mandatory | **обязательный** |
| Pillow (`PIL`) | mandatory `modules/image_extractor.py:58`; guarded figure_context_manager:19/29; lazy Supervertaler.py:9833 | mandatory | **обязательный** |
| pyperclip | mandatory `Supervertaler.py:184`, `modules/superlookup.py:18` | mandatory | **обязательный** |
| openai | lazy `modules/llm_clients.py:748` (единственное ядро исполнения после #9.3 — все провайдеры через custom_openai) | lazy, живой путь | **обязательный** |
| python-docx (`docx`) | guarded top-level `modules/docx_handler.py:11–13` + 34 lazy сайта | guarded, живой путь | **обязательный** |
| openpyxl | lazy `modules/statistics_dialog_qt.py:530–531` (экспорт XLSX статистики), `modules/usage_log.py:308` | lazy, живой путь | **обязательный** |
| requests | guarded `modules/okapi_sidecar.py:40` (живой путь XLIFF/Okapi) | guarded | **обязательный** |
| pyspellchecker (`spellchecker`) | guarded `modules/spellcheck_manager.py:39` | guarded | **обязательный** |
| spylls | guarded `modules/spellcheck_manager.py:30` + lazy `:613` | guarded | **обязательный** |
| lxml | импортов в продукте **0**; транзитивная зависимость python-docx (и стоит в дистрибутиве) | транзитивный | обязательный транзитивно — в lock; в requirements/pyproject отдельной строкой не нужен |
| markitdown | lazy `modules/unified_prompt_manager_qt.py:5910` и `:6099` | lazy, graceful | **опциональный** (extras) |
| pynput | lazy `modules/platform_helpers.py:1013/1187/1261` — только Linux-бэкенды (GlobalHotKeys, Controller); Windows = RegisterHotKey/AHK | lazy, платформенный | **опциональный** с маркером `sys_platform == "linux"` |
| hunspell | guarded `modules/spellcheck_manager.py:22` | guarded, деградирует | вне списков (как и сейчас: нет ни в requirements.txt, ни в dependencies pyproject) |
| tomli | lazy `Supervertaler.py:56` (fallback Python < 3.11) | lazy | не нужен (рантайм 3.13.15 → stdlib tomllib) |
| httpx / httpx2 | lazy `modules/llm_clients.py:763/765` (`try import httpx → кроме ImportError import httpx2 as httpx`) | lazy | отдельно не вносится: `httpx2` приходит транзитивно с openai 3.24.0 (см. §3.1) |
| PyQt6-WebEngine | импортов в продукте **0** (единственное вхождение слова WebEngine — комментарий Supervertaler.py:54435) | — | **исключён** из dependencies; бакет extras `web` оставлен пустым no-op — вопрос координатору (§7.2) |
| PyYAML, Markdown, packaging | импортов в продукте **0**; стоят в проверенном дистрибутиве P2.1 | — | в lock включены (фидельность к дистрибутиву, §3.2); в requirements/pyproject **не** вносятся — вопрос координатору (§7.1) |

УДАЛЕНЫ из зависимостей (координатор, решение 3) — подтверждено AST-сканом + grep-ом: **0 импортов**
каждого из: `anthropic`, `google-generativeai`, `PyMuPDF` (`fitz`), `numpy`, `sacrebleu`,
`boto3`, `deepl`, `psutil`, `chardet`, `setuptools`, `wheel`, `pyobjc` (также проверены
ветки `objc`/`AppKit`/`Cocoa`/`Foundation`/`Quartz` — 0).

Сверх списка решения 3, по результату рекона (решения 1–2) удалены из dependencies
pyproject — импортов в продукте **0** (не mandatory, не guarded, не lazy; dynamic-import
сайтов скан не нашёл вовсе): `vosk`, `faster-whisper`, `sounddevice`, `ahk`,
`PyQt6-WebEngine`, `lxml` (транзитивный), `pyyaml`, `markdown`. Согласование — §7.3.

Внутренние модули, ошибочно похожие на PyPI-пакеты (guarded fallback-импорты из
каталога `modules/`): `language_codes`, `segmentation_rules`, `tag_manager` — внешними
зависимостями НЕ являются (файлы `modules/*.py` существуют).

### §1.2 markitdown — одна строка для оценки (Дмитрий)

`markitdown` в `unified_prompt_manager_qt` конвертирует приложенный к промпту файл
`.pdf/.docx/.pptx/.xlsx` в markdown-текст (ленивый импорт с graceful-заглушкой
«markitdown not installed — run: pip install markitdown» при отсутствии пакета):
сайт `:5910` — чтение содержимого файла при добавлении в промпт, сайт `:6099` —
хелпер-конвертер документа; тянет onnxruntime, поэтому уходит в extras.

### §1.3 Сверка с текущими requirements.txt и pyproject.toml (до правки)

* `requirements.txt` (26 строк-пакетов): 9 из них продуктом реально импортируются
  (PyQt6, python-docx, openpyxl, Pillow, openai, requests, pyperclip, pyspellchecker,
  spylls); 17 — нет (setuptools, wheel, lxml, anthropic, google-generativeai,
  markitdown, sacrebleu, chardet, pyyaml, markdown, numpy, PyMuPDF, boto3, deepl,
  psutil, pynput, pyobjc-framework-Cocoa).
* `pyproject.toml` dependencies (28 записей): 9 обязательных совпадают; лишние — те же
  плюс `PyQt6-WebEngine`, `vosk`, `faster-whisper`, `sounddevice`, `ahk`.
* `optional-dependencies` pyproject — 9 пустых бакетов-ноупов (local-whisper, voice,
  web, pdf, mt, hunspell, windows, core, all) с пояснением про обратную совместимость.
* Секций «dev» в обоих файлах нет.

### §1.4 setup.py (сообщаю, НЕ менял)

`setup.py` про зависимости **ничего не declares**: ни `install_requires`, ни
`extras_require`, ни чтения requirements-файлов — только метаданные (name/version/author/
classifiers), `find_packages(include=["modules*"])`, `py_modules=["Supervertaler"]`,
entry_points и `include_package_data`. Версию берёт из `pyproject.toml` через `tomllib`
(ветка fallback «1.9.227» при сбое). Правка списков зависимостей в pyproject на него
не влияет; трогать нечего.

---

## §2 Часть B — requirements.txt + requirements-optional.txt + pyproject.toml

### §2.1 Выбор формы опционального блока

Выбран **отдельный файл `requirements-optional.txt`** (не закомментированный блок в
requirements.txt). Почему: (а) автоматика/скрипты, потребляющие `requirements.txt`
(`pip install -r`), не смогут случайно утянуть тяжёлые extras — markitdown тянет
onnxruntime; (б) закомментированные строки в requirements.txt легко не заметить и
легко сломать при правке; (в) в шапке requirements.txt и в шапке optional-файла стоят
перекрёстные ссылки, так что обнаружение простое.

### §2.2 Новый requirements.txt — 9 обязательных пакетов

Только реально импортируемые при старте и в живых путях (§1.1), диапазоны `>=` как
были, у каждого пакета краткий комментарий «зачем»: PyQt6, python-docx, openpyxl,
Pillow, openai, requests, pyperclip, pyspellchecker, spylls. Блоки setuptools/wheel
удалены (решение 3); шапка объясняет связь с requirements-optional.txt и
requirements.lock.

### §2.3 pyproject.toml — синхронно

* `dependencies` = те же 9 записей (комментарии сжаты); **версионная строка
  `version = "1.10.371"` не тронута** — проверено чтением tomllib и пробой Help→About (§6.4).
* `optional-dependencies`: два наполненных бакета — `import = ["markitdown>=0.0.1"]`,
  `linux-hotkeys = ["pynput>=1.7.6; sys_platform == 'linux'"]`; прежние пустые бакеты
  (local-whisper, voice, web, pdf, mt, hunspell, windows, core, all) сохранены как
  no-ops для обратной совместимости (существующие скрипты с `[extra]` не падают).

---

## §3 Часть C — requirements.lock и проверка воспроизводимости

### §3.1 Источник версий

Скрипт `docs/refactoring/audits/p2-3_distinfo_inventory.py` снял METADATA всех
`*.dist-info` из **распакованного дистрибутива P2.1**
(`.../refactoring/batch-p21/unpacked/python-embed/Lib/site-packages`, зип
`supervertaler-portable_20261031_1843.zip`, Python **3.13.15** embeddable — версия
подтверждена `python.exe -V` самого дистрибутива). Итого 33 dist-info, из них 32 без
pip. Состав соответствует метаданным: openai 3.24.0 требует `httpx2<3,>=2.12.0`
(форк httpx — потому в рантайме `httpx2`/`httpcore2`, а не `httpx`/`httpcore`),
PyQt6 6.11.0 тянет PyQt6-Qt6 6.11.2 + PyQt6-sip 13.12.0, python-docx 1.2.0 — lxml 6.1.3,
openpyxl 3.1.5 — et-xmlfile 2.0.0 и т.д.

### §3.2 requirements.lock

Новый файл в корне (рядом с requirements.txt): **32 записи name==version** — все
обязательные + транзитивные, ровно как в дистрибутиве; **pip исключён** (26.2.1 в
дистрибутиве — не в lock, по промпту); dev-мусора в дистрибутиве P2.1 уже нет.
Markdown/PyYAML/packaging включены (стоят в дистрибутиве, фидельность рантайма) —
вопрос о их судьбе §7.1. Первые строки — комментарий: источник (дистрибутив P2.1),
дата снятия (2026-11-01), Python 3.13.15, команда установки без `-U`.

### §3.3 Проверка воспроизводимости

1. **Чистый embedded Python 3.13.15** — копия cleanrt из P2.0
   (`refactoring/batch-p23/rt313/`, `._pth` переписан на минимум:
   `python313.zip / . / Lib\site-packages / import site`), pip поднят штатным
   `get-pip.py` (поставился pip 26.2.2 — текущий; в lock не входит).
2. `pip install --target .../lockinstall -r requirements.lock` (без `-U`, без
   «последних») — **rc=0**, все 32 пакета встали ровно в запиненные версии
   (`lock_install.log`).
3. **Сверка наборов name==version** (`p2-3_compare_lock_distrib.py`):
   дистрибутив без pip (32) vs lock-install (32) —
   `only in distributive: NONE; only in lock-install: NONE; version mismatches: NONE`
   → **VERDICT: ZERO-DIFF**.
4. **Headless-импорты + офскрин-старт + перевод** на lock-рантайме
   (`p2-3_probe_lock.py`, вывод `p2-3_probe_lock.out`): import Supervertaler OK (0.3s,
   version=1.10.371); офскрин-старт SupervertalerQt OK; перевод через
   LLMClient custom_openai → in-process mock-сервер OK
   (`output='MOCK:Translate the following text…'`); инвентаризация extras: все 17
   проверенных (`markitdown, anthropic, google.generativeai, fitz, numpy, sacrebleu,
   boto3, deepl, psutil, chardet, pynput, vosk, faster_whisper, sounddevice, ahk,
   PyQt6.QtWebEngineWidgets, setuptools`) — ABSENT, приложение при этом работает
   (грейсфул-деградация подтверждена на чистом lock-рантайме).

Замечание: dist-имена в lock взяты дословно из METADATA дистрибутива
(`pydantic_core`, `PyQt6_sip`, `typing_extensions` — с подчёркиваниями; pip
нормализует имена, установка проходит).

---

## §4 Часть D — docs/templates/RUNTIME_REBUILD.md

Новая заметка `docs/templates/RUNTIME_REBUILD.md`: как пересобрать рантайм с нуля —
embeddable-zip CPython **3.13.15**, точные строки `python313._pth` (как в дистрибутиве
P2.1), bootstrap pip через get-pip.py, команда установки строго из lock без `-U`,
что исключать при упаковке (get-pip, `__pycache__`/`*.pyc`, stray `py.py`/`tests`,
тяжёлые опциональные пакеты не ставить) и приёмочная проверка (32 dist-info, смоук-импорт,
офскрин+mock). Упаковщик НЕ менялся. Факты — из Части C.

---

## §5 Защитная батарея — «было = стало» (было = P2.2 after-состояние)

| Метрика | До (P2.2) | После (P2.3) | Комментарий |
|---|---|---|---|
| AST chain | 874 / 0 | **874 / 0** | `batch8-15_startup_chain_resolve.py`, без изменений |
| pyflakes (repo) | 519 | **519** | вывод **байт-идентичен** `pyflakes_full_after.txt` P2.2 (внешняя библиотека `qa/env/pyflakes-ext`) |
| py_compile canonical | 107 / 0 | **107 / 0** | вне docs/ |
| py_compile reference | 276 / 0 | **276 / 0** | все tracked .py |
| headless | 89 ok / 1 fail | **89 / 1** | единственный fail — известный `setup`[setuptools]; дельт нет |
| grep-gate | CLEAN | **CLEAN** | вывод идентичен чистому прогону P2.2, вкл. секцию «PDF-Rescue removal OK (0 hits … 107 product .py)» |
| smoke | 40 предметов, SMOKE OK | **40 предметов, SMOKE OK, 0 EXC** | раннер `batch-p1b_batch8-13_code_tools_smoke.py` не менялся с коммита P2.2 (`859ece12`) — тот же список 40 |
| git diff по продукту | — | **пусто** | `git diff --stat -- Supervertaler.py modules translations assets` = пусто; `git status` = только requirements.txt, pyproject.toml (M) + requirements-optional.txt, requirements.lock, docs (??) |

### §5.1 Проба Help→About (версия из pyproject)

Офскрин-проба (QDialog.exec monkeypatched, заголовок снапшотится): и на **lock-рантайме**,
и на **dev-рантайме** `E:\Dev\python-embed` — `import → version=1.10.371`,
старт → `title='Supervertaler Workbench v1.10.371'`, About →
`'<h2>Supervertaler Workbench v1.10.371</h2>'`. Правка списков зависимостей pyproject
чтение версии не сломала. Артефакты: `p2-3_probe_lock.out`, `p2-3_probe_dev_about.out`.

### §5.2 Dev-рантайм и процессы

`E:\Dev\python-embed` не изменялся (только read-only; pip-операции Части C — в копии
cleanrt под `Work_temp`). После проб осиротевших `python.exe`/`java.exe` сессии нет
(полный список процессов пуст — убивать нечего).

---

## §6 sha256 изменённых/новых файлов (оба вида: блоб LF / рабочая копия)

| Файл | до — блоб LF | до — рабочая копия | стало — блоб LF | стало — рабочая копия |
|---|---|---|---|---|
| `requirements.txt` | `c12e733bcac6c43992bd2590721fd54814d4415a` | `4517593376fd567e136bc62c37c7544b355c9b1e9d32553f79f4f84853d8e214` | `4b148ce6fc1bc9b1394bb764163ff299c2d241cb` | `cc3d42f6136ecd26b5be73233202ec921f97330c29b7915357714fe20eacefa2` |
| `pyproject.toml` | `28f1a716a9ad4d797aa1ae7daf4485c0612ff731` | `2b18ebf9b976db77c1402240b9e7743a8d7fa3a79cb4098a64b2edef365306b2` | `13b258ccfefad2a64639e8ad1c72e54b1c935b08` | `cdd66af1cb073d064b2617528a8af399f990195b7dba89419d665dabae333524` |
| `requirements-optional.txt` (новый) | — | — | `07ca6249c34f19b89f28c58979c678528743a7df` | `2fa877ba596d3ff347d00f3c1ca74f6f1146527496e259a8ca202a74e24628af` |
| `requirements.lock` (новый) | — | — | `5f66aa0de5bd2b41bf93f9757ee806e98fc6d703` | `b509af5c340d7b2916aa4d42a1846e90cdff3e4de75b0b90f17ca42cf7ba7a9c` |
| `docs/templates/RUNTIME_REBUILD.md` (новый) | — | — | `ead8244b7b470db9ca5bc7ae7bdb04ecc214daae` | `22c88250f43fc25be908293c9e6f4938c1648a1383c95274681f23f655875061` |
| `docs/refactoring/reports/BATCH_P23_REPORT.md` (новый, этот файл) | — | — | см. коммит (самоссылка невозможна) | см. коммит |
| `PROJECT_STATUS.md` (обновлён) | `f18b4565d0a70513d7ced2a807ae64375297a80b` | `1fdcd142b33c84f3c4b6613a1f0b35bfed68d0403b9ddb01ba4e519b9d4b4094` | `abd64309a27f9846860aa20eeb606f23ca7b4863` | `9b4ffdb39fe005cb8cfeaea1fcc375bde6a2c8bece657e9f688939b848047ed4` |

Примечания: «до» взяты из пре-редакционных снапшотов
(`refactoring/batch-p23/before/`, requirements.txt и pyproject.toml сняты с
`git show HEAD:` и побайтово совпадают с рабочей копией до правки). Блоб LF и рабочая
копия у этих файлов совпадают по содержимому (файлы LF, но блоб — sha1 git, рабочая —
sha256, поэтому числа разные по природе алгоритмов). У новых файлов «до» = «—».
Аудит-артефакты (14 файлов `p2-3_*`) коммитятся в `docs/refactoring/audits/`.

---

## §7 Вопросы координатору (не блокируют вердикт GO/NO-GO по сути батча)

1. **PyYAML, Markdown, packaging** — в дистрибутиве P2.1 стоят, продуктом не
   импортируются. В lock включил (фидельность к проверенному рантайму, ZERO-DIFF),
   в requirements/pyproject НЕ вносил, в requirements-optional.txt — примечание без
   строк установки. Оставляем в lock как есть / исключаем из lock и из следующей
   сборки дистрибутива (−1.3 МБ)? (markdown 0.5 МБ + yaml 0.7 МБ, packaging — крошечный.)
2. **PyQt6-WebEngine** — импортов 0 (Web Resources уже в fallback-режиме), из
   dependencies убран; бакет extras `web` оставлен пустым no-op. Держать пустой
   (обратная совместимость `supervertaler[web]`) или наполнить им
   `"PyQt6-WebEngine>=6.5.0"`?
3. **vosk, faster-whisper, sounddevice, ahk** — сверх списка решения 3: импортов в
   продукте нет вообще (голосовые движки, судя по комментариям pyproject, исторические).
   Убрал из dependencies по решениям 1–2. Подтвердить; если где-то ожидаются
   будущими фичами — вернуть отдельными extras.
4. **pip в lock** — исключён по промпту; при пересборке рантайма get-pip ставит
   текущий pip (26.2.2), в дистрибутиве P2.1 лежит 26.2.1. Это единственное
   допустимое расхождение пересобранного рантайма (зафиксировано в
   RUNTIME_REBUILD.md). Если нужна и версия pip — скажите, добавлю отдельной строкой
   комментария в lock.

---

## §8 Ручные тесты

Ручных тестов для Дмитрия **нет** — по промпту: конфигурационные файлы; рантайм-проверки
выполнены пробами (§3.3, §5.1).

---

## §9 Артефакты

* Стейдж: `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p23\` — скан, dist-info
  инвентарь, compare, lock_install.log, getpip.log, probe_lock.*, probe_dev_about.*,
  статика, smoke, iso-профили, rt313/lockinstall (копии cleanrt — оставить до вердикта,
  потом можно чистить).
* Коммитится: `requirements.txt`, `pyproject.toml` (изменены), `requirements-optional.txt`,
  `requirements.lock`, `docs/templates/RUNTIME_REBUILD.md` (новые), отчёт, PROJECT_STATUS.md,
  14 артефактов `docs/refactoring/audits/p2-3_*`.
* **`git push` НЕ выполняется — только по команде Дмитрия.**

---

## §10 Аддендум — вердикт GO и ответы координатора (2026-11-01)

Вердикт по BATCH P2.3: **GO**, пуш разрешён. Ответы на вопросы §7 применены
аддендум-коммитом (до пуша):

1. **PyYAML, Markdown, packaging — убрать из lock и из следующей сборки.** Выполнено с
   условием координатора: (а) проверка по METADATA всех 29 оставшихся пакетов lock
   (`p2-3_requires_check.py`) — ни один не требует PyYAML/Markdown/packaging в
   mandatory-замыкании; единственное вхождение — `packaging` в extras `"tests"` у
   pillow (extras не ставятся); (б) чистая установка из нового lock: pip rc=0, 29
   пакетов ровно в пинах (`lock_install2.log`); (в) сверка с дистрибутивом
   (`p2-3_compare_lock2_distrib.py`): только в дистрибутиве остались ровно
   Markdown 3.10.3, PyYAML 6.0.3, packaging 26.3 (объяснённые удаления), прочее
   ZERO-DIFF, версийных расхождений 0; (г) полная проба на новом lock-рантайме
   (`p2-3_probe_lock2.out`): импорт 0.3s / version=1.10.371, офскрин-старт OK,
   перевод через mock OK, About OK.
2. **Пустые extras убраны все** (local-whisper, voice, web, pdf, mt, hunspell,
   windows, core, all) — в pyproject остались только `import` и `linux-hotkeys`
   (исполнение решения 8.12 про `web = []`). TOML валиден, version=1.10.371, 9 deps.
3. **vosk, faster-whisper, sounddevice, ahk** — удаление подтверждено координатором
   (голос убран в Batch #8). Без изменений к аддендуму.
4. **pip в lock не фиксируется** — допустимое расхождение остаётся в
   RUNTIME_REBUILD.md (обновлён: 29 dist-info в приёмочной).

Оформление (замечание координатора): в следующих отчётах sha256 в ОБЕИХ колонках
(«блоб LF» = sha256 содержимого блоба, «рабочая копия» = sha256 файла; git-sha1 больше
не используется). Таблица аддендума — в обеих колонках sha256; у всех файлов этого
батча рабочая копия LF, поэтому обе колонки совпадают по значению:

| Файл (аддендум) | до — блоб LF (sha256) | до — рабочая копия (sha256) | стало — блоб LF (sha256) | стало — рабочая копия (sha256) |
|---|---|---|---|---|
| `requirements.lock` | `b509af5c340d7b2916aa4d42a1846e90cdff3e4de75b0b90f17ca42cf7ba7a9c` | = блобу | см. коммит-аддендум | см. коммит-аддендум |
| `requirements-optional.txt` | `2fa877ba596d3ff347d00f3c1ca74f6f1146527496e259a8ca202a74e24628af` | = блобу | см. коммит-аддендум | см. коммит-аддендум |
| `pyproject.toml` | `cdd66af1cb073d064b2617528a8af399f990195b7dba89419d665dabae333524` | = блобу | см. коммит-аддендум | см. коммит-аддендум |
| `docs/templates/RUNTIME_REBUILD.md` | `22c88250f43fc25be908293c9e6f4938c1648a1383c95274681f23f655875061` | = блобу | см. коммит-аддендум | см. коммит-аддендум |

(«до» = состояние на коммите 2fb6828c — первая часть P2.3; «стало» фиксируется
коммитом-аддендумом, sha256 значений обоих видов совпадают, т.к. файлы LF.)

**py_compile REFERENCE после коммита** (с учётом новых p2-3_* скриптов): см. строку
ниже — счётчик прогоняется по `git ls-files *.py` на состоянии аддендум-коммита:
**282 ok / 0 fail (282 total; canonical без изменений 107 ok / 0 fail — оба новых скрипта в docs/; проверено прогоном batch8-15_pycompile_all.py по git ls-files на состоянии аддендум-коммита).**

Пуш: выполняется командой Дмитрия после аддендума (610d32c1 + коммиты P2.3;
пре-пуш-проверка пустого diff по продукту — см. PROJECT_STATUS).
