# BATCH P2.4 — ОТЧЁТ

**Упаковщик строит рантайм из requirements.lock (вместо копии dev-рантайма); чистка lock и pyproject.**

Дата: 2026-11-01. База: origin/main после пуша P2.3 (HEAD `819f9797`, дерево идентично
`9b85a3b2`). Рабочая область: `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p24\`.
**Код продукта и dev-рантайм `E:\Dev\python-embed` НЕ менялись** — `git diff` по
`Supervertaler.py modules translations assets user_data setup.py requirements.txt` пуст.
Монолит: 54 643 строк (без изменений с P2.2). **Пуша нет — стоп до вердикта.**

---

## §1. Итог одной строкой

Дистрибутив собирается теперь так: официальный embeddable-zip CPython 3.13.15 +
`requirements.lock` через колёсный кэш `E:\Dev\wheelhouse` (offline); dev-рантайм больше
не копируется в поставку вообще (только исполняет сборочный скрипт). Новый zip
`supervertaler-portable_20261101_1728.zip` — **128 387 481 байт** против 128 851 415 у P2.1
(−464 КБ = ровно PyYAML+Markdown+packaging), site-packages = ровно 29 пинов lock + pip,
0 `__pycache__`/`.pyc`, полный офскрин-пробег и запуск через `start.bat` — OK.

## §2. Часть A — чистка (состояние на входе P2.4: уже выполнено P2.3-аддендумом, P2.4 перепроверило)

1. **requirements.lock — 29 записей, Markdown/PyYAML/packaging отсутствуют** (убраны
   P2.3-аддендумом по вердикту GO). Файл в P2.4 НЕ менялся. Повторная METADATA-проверка
   (`docs/refactoring/audits/p2-4_requires_check.py`, источник METADATA — dist-info
   проверенного дистрибутива P2.1, где лежит каждый пин lock своей версией):

| пакет | версия | Requires-Dist → PyYAML/Markdown/packaging |
|---|---|---|
| annotated-types | 0.8.0 | — |
| anyio | 4.15.1 | — |
| certifi | 2026.7.22 | — |
| charset-normalizer | 3.5.1 | — |
| et-xmlfile | 2.0.0 | — |
| h11 | 0.16.0 | — |
| httpcore2 | 2.13.1 | — |
| httpx2 | 2.13.1 | — |
| idna | 3.19 | — |
| jiter | 0.17.0 | — |
| lxml | 6.1.3 | — |
| openai | 3.24.0 | — |
| openpyxl | 3.1.5 | — |
| pillow | 12.3.0 | `packaging; extra == "tests"` — **EXTRA**, не ставится |
| pydantic | 2.14.0 | — |
| pydantic_core | 2.50.0 | — |
| pyperclip | 1.11.0 | — |
| PyQt6 | 6.11.0 | — |
| PyQt6-Qt6 | 6.11.2 | — |
| PyQt6_sip | 13.12.0 | — |
| pyspellchecker | 0.9.0 | — |
| python-docx | 1.2.0 | — |
| requests | 2.34.2 | — |
| sniffio | 1.3.1 | — |
| spylls | 0.1.7 | — |
| truststore | 0.10.4 | — |
| typing_extensions | 4.16.0 | — |
| typing-inspection | 0.4.4 | — |
| urllib3 | 2.7.0 | — |

   **Вердикт: CLEAN** — ни один из 29 пакетов lock не требует PyYAML/Markdown/packaging
   в mandatory-замыкании (полный вывод: `docs/refactoring/audits/p2-4_requires_check.out`).
2. **pyproject.toml** — extras уже только `import` и `linux-hotkeys` (P2.3); файл в P2.4
   НЕ менялся. Версионная строка подтверждена дважды: проба Help→About на dev-рантайме
   (`p2-4_probe_about.py` — `About PROBE: OK`, заголовок `Supervertaler Workbench v1.10.371`)
   и на собранном дистрибутиве (§4, about_version OK).
3. **requirements-optional.txt** — примечание о markdown/PyYAML/packaging удалено
   (P2.4, единственная содержательная правка Части A). Содержимое опциональных пакетов
   не тронуто (markitdown + pynput с linux-маркером).

## §3. Часть B — упаковщик

### 3.1. `docs/templates/make_portable_zip.bat` (переписан)

* Новые переменные в шапке: `EMBED_ZIP=E:\Dev\python-3.13.15-embed-amd64.zip`
  (локальная копия, использовалась в P2.0), `GETPIP=E:\Dev\python-embed\get-pip.py`
  (локальная копия), `WHEELHOUSE=E:\Dev\wheelhouse` (кэш ВНЕ репозитория),
  `LOCK=%REPO%\requirements.lock`.
* Шаг [3/6] «Copy embedded runtime» (robocopy dev-рантайма + prune) **удалён**; вместо
  него — вызов `packaging_helper.py runtime STAGE EMBED_ZIP GETPIP WHEELHOUSE LOCK`.
* Preflight проверяет существование embed-zip, get-pip.py и lock.
* Роль dev-рантайма: **только оркестратор** — исполняет helper и при неполном wheelhouse
  делает read-only `pip download` (в штатной сборке не потребовалось после первого
  заполнения кэша). Содержимое dev-рантайма в поставку не попадает.
* Старое исключение `*.md`/`scripts\`/`tools\` и комментарий-перечень сохранились;
  в перечень «Kept» добавлен requirements.lock.

### 3.2. `docs/templates/packaging_helper.py` (переписан)

* `runtime <stage> <embedzip> <getpip> <wheelhouse> <lockfile>` — новый шаг:
  1. распаковка embed-zip в `<stage>\python-embed` (проверка безопасности имён записей;
     подъём содержимого, если внутри одна корневая папка — наша локальная копия зипа не
     плоская);
  2. запись `python313._pth` (точно как RUNTIME_REBUILD.md);
  3. проверка полноты wheelhouse (колесо на каждый пин lock + pip по нормализованным
     именам; недостающее → `pip download -r lock -d wheelhouse` + `pip download pip`;
     нет сети и кэш неполный → понятная ошибка с инструкцией, **stage сохраняется**);
  4. bootstrap pip offline: `python.exe get-pip.py --no-index --find-links <wheelhouse>`;
  5. установка ровно lock: `python.exe -m pip install --no-index --find-links
     <wheelhouse> -r requirements.lock` (pip-шаги с `PYTHONDONTWRITEBYTECODE=1`);
  6. `get-pip.py` из stage удаляется; **pip остаётся** (решение координатора);
  7. гейт dist-info: в site-packages ровно 29 пинов lock (сверка name+version по
     METADATA) + ровно один `pip-*.dist-info`; любое отклонение = FAIL;
  8. гейт «forbidden»: старый список исключений P2.0 (pygments, pytest-стек, pyflakes,
     chardet, get-pip.py, их dist-info и exe-шимы) превращён в проверку присутствия —
     **FAIL, если нашлось**; плюс зачистка `__pycache__`/`*.pyc` с проверкой нуля.
* `prune` (чистка копии) удалён за ненадобностью — собирать нечего.
* `importsmoke`: список модулей актуализирован — **`yaml` убран** (PyYAML в поставке
  больше нет — на старом списке смоук упал бы), добавлены `spylls` и `pydantic`;
  всего 11 модулей.
* `zip`: к прежним проверкам (testzip, число записей, безопасные имена) добавлен гейт
  **0 `__pycache__`/`.pyc`/`.pyo`** записей в готовом zip.

### 3.3. Прогоны сборки (все — в `refactoring/batch-p24/build/`)

| прогон | результат | причина/фикс |
|---|---|---|
| 1 (1724) | FAIL: «unpacked zip has no python.exe» | локальный embed-zip содержит корневую папку `python-embed\` → упаковщик научен поднимать содержимое |
| 2 (1725) | FAIL: гейт dist-info «UNEXPECTED: pip» | pip ложно попадал в unexpected-список → исключён из него (pip разрешён ровно один) |
| 3 (1726) | FAIL: zip-гейт — **3371 `__pycache__`/`.pyc` записей** | pip оставил байткод в site-packages (старый путь с robocopy это маскировал) → `PYTHONDONTWRITEBYTECODE=1` на pip-шаги + зачистка байткода с проверкой нуля |
| 4 (1728) | **OK** | финальная сборка |

Первый прогон заполнил wheelhouse: 30 колёс (29 пинов + pip), 109 МБ, `E:\Dev\wheelhouse`.
Прогоны 2–4 идут полностью offline из кэша.

## §4. Часть C — верификация сборки

### 4.1. Zip и распаковка

| метрика | P2.1 (было) | P2.4 (стало) |
|---|---|---|
| zip | `supervertaler-portable_20261101_1401.zip` | `supervertaler-portable_20261101_1728.zip` |
| размер | 128 851 415 байт (122,9 МБ) | **128 387 481 байт (122,4 МБ)** |
| sha256 | `87bad0dc5093e33f…` | `c1465e01ba5f3860…` |
| записей | 7397 файлов + 539 каталогов | **7320 файлов + 528 каталогов** |
| `__pycache__`/`.pyc` в zip | 0 | **0** (гейт в упаковщике + контроль при распаковке) |

Разница размера −463 934 байта = ровно удалённые PyYAML/Markdown/packaging (−77 файлов,
−11 каталогов, включая `markdown_py.exe` из `Scripts\`).

### 4.2. Состав site-packages (name==version, `p2-4_compare_distrib.py`)

* P2.1: 33 dist-info → P2.4: **30 dist-info**.
* Удалены ровно: **markdown, packaging, pyyaml**. Добавлено: ничего.
* Версия-мисматчи: только **pip 26.2.1 → 26.2.2** (pip в lock не входит, решение
  координатора — не фиксируется; get-pip ставит текущий). Остальные 29 пинов — точные.
* `Scripts\` идентичен P2.1 минус `markdown_py.exe`.

Полный вывод: `docs/refactoring/audits/p2-4_compare_distrib.out`.

### 4.3. Пробы распакованного дистрибутива (чистый каталог Work_temp, НЕ D:\Supervertaler_clean)

`p2-4_probe_unpacked.py`, интерпретатор — **из самой сборки** (`unpacked\python-embed\python.exe`):

| проверка | результат |
|---|---|
| headless-импорты (setup + modules.*) | **89 ok / 1 fail** (единственный fail — известный `setup`[setuptools]; ожидание 89/1 выполнено) |
| офскрин-старт | OK, 1,6 с, `Supervertaler Workbench v1.10.371` |
| перевод через mock-сервер | OK (custom_openai → mock_openai_server, 3,8 с) |
| Help → About | OK, `v1.10.371` |
| инвентарь отсутствия | OK: yaml, markdown, packaging, markitdown, onnxruntime, vosk, faster_whisper, sounddevice, ahk, chardet, pytest, pygments, pyflakes, anthropic, google.generativeai, fitz, PyQt6-WebEngine — все ABSENT |
| негативный контроль профиля | OK: изолированный USERPROFILE/HOME/APPDATA/LOCALAPPDATA чист |

Дополнительно (dev-рантайм, Часть A.2): `p2-4_probe_about.py` — Help→About v1.10.371 OK.

### 4.4. Запуск через start.bat реальным процессом

`p2-1_start_bat_smoke.py` (без изменений, как в P2.1): **P21-START-OK** — cmd →
`python.exe Supervertaler.py` из сборки, корень данных создан за 3 с, процесс закрыт по
PID (офскрин-модал закрытия → /F, ожидаемо), сирот этого прогона нет, в профиле ничего.

### 4.5. Время сборки

Offline (wheelhouse заполнен): runtime-шаг 35 с (распаковка + bootstrap + install),
код-копия ~5 с, zip 27 с, importsmoke <1 с — **итого ~1,5 мин**. Первый прогон с
заполнением wheelhouse — +~2 мин на `pip download`.

## §5. Защитная батарея («было = стало»)

| проверка | было (P2.3) | стало (P2.4) |
|---|---|---|
| AST startup-chain | 874/0 | **874/0** (`chain_p24.out`) |
| pyflakes | 519 | **519** |
| headless (repo) | 89/1 | **89/1** |
| grep-gate | CLEAN | **CLEAN** (rc=0, вкл. QSettings- и PDF-Rescue-секции) |
| smoke (канонический 8.13, раннер P1-B) | 40 предметов SMOKE OK | **40 предметов, SMOKE OK (10,0 с), 0 EXC** |
| py_compile CANONICAL | 107/0 | **107/0** |
| py_compile REFERENCE (до коммита) | 282/0 | **282/0**; **после коммита P2.4: 286/0** (+4 новых аудит-скрипта p2-4_*; измерено на коммите `6b92ae7e`, `docs/refactoring/audits/p2-4_pycompile_p24_after_commit.out`) |
| git diff по продукту | пуст | **пуст** |

Артефакты: `refactoring/batch-p24/` (chain_p24.out, pyflakes_p24.out, headless_repo_p24.out,
gate_p24.out, smoke_p24.out), копии ключевых — в `docs/refactoring/audits/p2-4_*`.

## §6. sha256 изменённых файлов (обе колонки: блоб LF / рабочая копия)

| файл | до (блоб LF) | до (раб. копия) | стало (блоб LF) | стало (раб. копия) |
|---|---|---|---|---|
| `docs/templates/packaging_helper.py` | `33afb30860d75c1f23b4c911b8e3043a5bc95557481544a1107671eb6d866330` | `33afb308…` | `cce736cc11a1c310929459e158cb3bec41808e47318850ba63de09a0adf61ac4` | `cce736cc…` |
| `docs/templates/make_portable_zip.bat` | `9a6a96f1f14ca09c8a5740d512f2921f11624520b9c05e66591e6e8a16e3ef63` | `ef3beb262719564d1a4786ff5735d84aeea53d75e7c650cbb9c8420b0949b9b4` | `476b70694506c44d5aa565b360e07af8093aa0f105edd3d0dd162890d58b54a2` | `61eb32278d161bf57ea657ae2139201de60cf8de21273fdbf59fc901290ba835` |
| `requirements-optional.txt` | `798eb5ddaa88d409b30eb375146a0d546ed258bfb282ad2a4a19b585cb241d0f` | `798eb5dd…` | `abd0eedaa5887436f11b4ebaaa40be262a69eb688a06bdac46548c0fa8f79f51` | `abd0eeda…` |
| `docs/templates/RUNTIME_REBUILD.md` | `49eb7fb3c5103d12f26e1a6fd64aa0e5a4ea55a5d13e320811ec3ecf9e4f2abe` | `49eb7fb3…` | `5a470346e8159dfc02ab379e3484b1462550817229b1eb279506381746aabd8c` | `5a470346…` |
| `requirements.lock` | без изменений (`e2c6f371…`) | — | без изменений | — |
| `pyproject.toml` | без изменений (`a7e2308c…`) | — | без изменений | — |

Блоб-LF «до» снят с `git show HEAD:<файл>`; «стало» — CR-нормализация рабочей копии
(совпадает с блобом, который уйдёт в коммит; для CRLF-файла .bat значения колонок
различаются ожидаемо). Новые файлы (аудиты P2.4): «до» = «—».

## §7. RUNTIME_REBUILD.md

Переписан: с P2.4 пересборку рантайма делает упаковщик автоматически (описаны переменные
EMBED_ZIP/GETPIP/WHEELHOUSE, роль wheelhouse, гейты); ручной рецепт сохранён как
справка и приведён в соответствие (offline-варианты команд, зачистка байткода, состав
гейтов, приёмочные проверки со ссылками на пробы P2.4).

## §8. Ручной тест Дмитрия — T-P2.4a (простым языком)

**Цель:** убедиться, что новая сборка (которую теперь делает обновлённый упаковщик)
работает как старая.

1. Двойным щелчком запустить `docs\templates\make_portable_zip.bat` из репозитория.
   Подождать — в консоли появится строка `[DONE] 128387481 bytes: ...zip`
   (примерно полторы-две минуты; окно закрывать не нужно, оно само ждёт Enter).
2. Открыть свежий zip из `E:\Dev\Work_temp\SupervertalerPortable\build\` в Проводнике,
   распаковать в **новую пустую папку**.
3. Запустить `start.bat` внутри распакованной папки. Дождаться открытия программы.
4. Открыть проект, перевести один сегмент, сохранить, закрыть программу.
5. Затем пересобрать тестовую сборку: удалить старое содержимое
   `D:\Supervertaler_clean\` и распаковать туда этот же zip (папки `start.bat`,
   `python-embed`, `SupervertalerPortable` — прямо в корень), запустить `start.bat`.

**Ожидание:** всё работает как раньше; в консоли нет сообщений `ModuleNotFoundError`;
перевод выполняется; настройки и данные появляются в папке сборки.

**Провал:** программа не стартовала, или в консоли `ModuleNotFoundError` / жалоба на
отсутствующий пакет.

*Примечание: если при первом запуске упаковщика сети не будет, а папки
`E:\Dev\wheelhouse` нет — сборка остановится с подсказкой, что положить в wheelhouse;
это штатная диагностика, stage сохраняется.*

## §9. Вопросы координатору

1. **Wheelhouse вне репо.** `E:\Dev\wheelhouse` (30 колёс, 109 МБ) — предложенное место
   из промта. Он не версионруется; для сборки на другой машине нужен один онлайн-прогон
   `pip download`. Устраивает ли такое положение?
2. **pip 26.2.2 в новой сборке** против 26.2.1 в P2.1 (get-pip ставит текущий, pip не
   входит в lock — прежнее решение). Принимаем как допустимое расхождение (как в P2.3)?
3. **`importsmoke` теперь 11 модулей** (yaml убран, spylls/pydantic добавлены) — ок?

## §10. Коммит

Один коммит: конфиги упаковщика (`make_portable_zip.bat`, `packaging_helper.py`,
`RUNTIME_REBUILD.md`, `requirements-optional.txt`) + аудит-артефакты
(`docs/refactoring/audits/p2-4_*`) + отчёт + PROJECT_STATUS.md. Продукт не тронут.
**Пуша нет — жду вердикта.**
