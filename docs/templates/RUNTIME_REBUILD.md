# Rebuilding the bundled Python runtime from scratch

**С BATCH P2.4 это делает упаковщик автоматически.** `docs/templates/make_portable_zip.bat`
собирает `python-embed\` дистрибутива из официального embeddable-zip + `requirements.lock`
(шаг «runtime» в `packaging_helper.py runtime ...`): распаковка, патч `python313._pth`,
bootstrap pip offline из wheelhouse, установка ровно пинов lock, проверка dist-info =
lock + pip, проверка «запрещённых» пакетов, зачистка байткода. Dev-рантайм
`E:\Dev\python-embed` в дистрибутив больше НЕ копируется — он только исполняет
сборочный скрипт (и при неполном wheelhouse выполняет read-only `pip download`).

Переменные сборки (в шапке `make_portable_zip.bat`):

* `EMBED_ZIP=E:\Dev\python-3.13.15-embed-amd64.zip` — официальный embeddable CPython
  3.13.15 (та же версия, что в проверенном дистрибутиве P2.1). Локальная копия; файл
  может быть как плоским, так и с одной корневой папкой внутри — упаковщик поднимает
  содержимое.
* `GETPIP=E:\Dev\python-embed\get-pip.py` — локальная копия bootstrap-скрипта.
* `WHEELHOUSE=E:\Dev\wheelhouse` — колёсный кэш ВНЕ репозитория. Заполняется один раз
  (`pip download -r requirements.lock -d <wheelhouse>` + `pip download pip`), дальше все
  сборки идут offline (`--no-index --find-links`). Если кэш неполный и сети нет —
  упаковщик печатает инструкцию и ОСТАВЛЯЕТ stage для осмотра.

Факты проверены в BATCH P2.3 (ZERO-DIFF пересборки с дистрибутивом P2.1) и BATCH P2.4
(первая сборка упаковщиком: zip 122,4 МБ, 0 `__pycache__`/`.pyc`, полный офскрин-пробег
с mock-трансляцией). Ниже — ручной рецепт (соответствует тому, что делает упаковщик).

## 1. Базовый интерпретатор

* Windows embeddable distribution **CPython 3.13.15** (та же версия, что в проверенном
  дистрибутиве P2.1). Распаковать zip в `<runtime>\` (каталог с `python.exe`,
  `python313._pth`, `python313.zip`).
* Встроенный рантайм игнорирует `PYTHONPATH` — все пути задаются правкой
  `python313._pth`.

## 2. `python313._pth` (как в дистрибутиве P2.1)

```
python313.zip
.
..\SupervertalerPortable
Lib\site-packages
import site
```

Строка `..\SupervertalerPortable` подключает код продукта (репозиторий кладётся рядом
с `python-embed\`); строка `import site` включает `Lib\site-packages`.

## 3. Bootstrap pip (offline через wheelhouse)

```
<runtime>\python.exe get-pip.py --no-index --find-links <wheelhouse>
```

(упаковщик всегда bootstrapит pip offline — колесо pip заранее скачивается в wheelhouse;
ручной онлайн-вариант `<runtime>\python.exe get-pip.py` тоже работает.)

Версия pip при этом берётся «текущая» (в сборке P2.4 поставился 26.2.2; в дистрибутиве
P2.1 лежал 26.2.1). **pip в lock не входит** — его версия не фиксируется; это
единственное допустимое расхождение пересобранного рантайма с дистрибутивом.

## 4. Установка пакетов строго из lock

```
<runtime>\python.exe -m pip install --no-index --find-links <wheelhouse> -r requirements.lock
```

(ручной онлайн-вариант: `python.exe -m pip install --no-cache-dir -r requirements.lock`.)

* Без `-U` и без других аргументов: пинам верить, «последние» не подтягивать.
* `requirements.lock` = 29 записей: все обязательные пакеты + транзитивные зависимости,
  версии сняты с dist-info проверенного дистрибутива P2.1 (Python 3.13.15);
  PyYAML/Markdown/packaging из lock исключены (решение координатора от 2026-11-01;
  METADATA-проверка повторена в P2.4 — ни один пакет lock их не требует).
* Сетевой pip-кэш не участвует в сборке дистрибутива: `--no-index --find-links` читает
  только wheelhouse.
* `--target` НЕ нужен: ставим в собственный `Lib\site-packages` рантайма.
* `PYTHONDONTWRITEBYTECODE=1` для pip-шагов + зачистка `__pycache__`/`*.pyc` после
  установки: в дистрибутиве байткода быть не должно (в первой сборке P2.4 pip оставил
  3371 entry — гейт упаковщика это поймал; теперь зачищается автоматически).

## 5. Что НЕ должно попасть в рантайм (гейты упаковщика, FAIL при находке)

* `get-pip.py` (удаляется после bootstrap); pip и `Scripts\` — ОСТАЮТСЯ (решение
  координатора: pip в дистрибутиве есть);
* старый список исключений P2.0/P2.1 как проверка присутствия: `pygments`, pytest-стек
  (`_pytest`, `pytest`, `iniconfig`, `pluggy`, `colorama`), `pyflakes`, `chardet` +
  их `*.dist-info` + консольные exe (`pytest.exe`, `pygmentize.exe`, ...);
* все `__pycache__\` и `*.pyc` / `*.pyo` (проверяется и по дереву, и по готовому zip);
* dist-info в `Lib\site-packages` должно быть РОВНО lock-набор + pip (30 каталогов) —
  версии сверяются с METADATA;
* тяжёлые опциональные пакеты (`markitdown`, `onnxruntime`, `numpy`, `vosk`,
  `faster-whisper`, ...) в рантайм НЕ ставятся — опциональные зависимости описаны в
  `requirements-optional.txt` и в дистрибутив не попадают.

## 6. Приёмочная проверка (автоматизирована в упаковщике и в пробах P2.4)

1. dist-info: 30 каталогов `*.dist-info` (29 пинов lock + `pip-*.dist-info`), версии
   совпадают с lock.
2. Смоук-импорт (`packaging_helper.py importsmoke`, 11 модулей: PyQt6, openai, docx,
   openpyxl, PIL, lxml, requests, spellchecker, spylls, pydantic, Supervertaler).
3. Zip-самопроверка: `testzip()` чист, число записей = дереву, безопасные имена,
   0 `__pycache__`/`.pyc`.
4. Проба распакованного дистрибутива (`docs/refactoring/audits/p2-4_probe_unpacked.py`
   интерпретатором ИЗ сборки): headless 89/1, офскрин-старт, перевод через mock-сервер,
   Help→About v1.10.371, инвентарь отсутствия опциональных/дев-пакетов, негативный
   контроль профиля; плюс реальный запуск через `start.bat`
   (`docs/refactoring/audits/p2-1_start_bat_smoke.py`).
