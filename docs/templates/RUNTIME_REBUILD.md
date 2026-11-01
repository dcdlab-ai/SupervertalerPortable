# Rebuilding the bundled Python runtime from scratch

Факты проверены в BATCH P2.3 (2026-11-01, см. `docs/refactoring/reports/BATCH_P23_REPORT.md`,
Часть C): рантайм, собранный по этой записке из `requirements.lock`, побайтно-по-версиям
совпал с проверенным дистрибутивом P2.1 (32/32 пакета, ZERO-DIFF) и прошёл полный
офскрин-пробег приложения с трансляцией через mock-сервер.

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

## 3. Bootstrap pip

Положить `get-pip.py` в корень рантайма и выполнить:

```
<runtime>\python.exe get-pip.py
```

Версия pip при этом берётся «текущая» (при проверке P2.3 поставился 26.2.2; в
дистрибутиве P2.1 лежал 26.2.1). **pip в lock не входит** — его версия не фиксируется;
это единственное допустимое расхождение пересобранного рантайма с дистрибутивом.

## 4. Установка пакетов строго из lock

```
<runtime>\python.exe -m pip install --no-cache-dir -r requirements.lock
```

* Без `-U` и без других аргументов: пинам верить, «последние» не подтягивать.
* `requirements.lock` = все обязательные пакеты + транзитивные зависимости, версии
  сняты с dist-info проверенного дистрибутива P2.1 (зип
  `supervertaler-portable_20261031_1843.zip`, Python 3.13.15). Первый комментарий
  в самом файле дублирует источник и дату.
* `--target` НЕ нужен: ставим в собственный `Lib\site-packages` рантайма.
  (В проверке P2.3 `--target` использовался только чтобы сравнить свежую установку
  с дистрибутивом, не трогая рабочие деревья.)

## 5. Что исключить при упаковке рантайма в zip

По фактам P2.1/P2.3 (финальный зип P2.1 содержал 0 `__pycache__` и 0 `.pyc`):

* `get-pip.py` из корня рантайма;
* `<runtime>\Scripts\` (консольные обёртки pip) и `Lib\site-packages\pip*` — по
  решению координатора: pip можно оставить (он в дистрибутиве P2.1 есть, 26.2.1)
  либо исключить; в lock он не входит;
* все `__pycache__\` и `*.pyc` / `*.pyo`;
* stray-файлы типа `py.py` и каталоги `tests` внутри site-packages (наблюдались в
  распаковке P2.1 как мусор, на работу не влияют);
* тяжёлые опциональные пакеты (`markitdown`, `onnxruntime`, `numpy`, `vosk`,
  `faster-whisper`, ...) в рантайм НЕ ставятся — опциональные зависимости описаны в
  `requirements-optional.txt` и в дистрибутив не попадают.

## 6. Приёмочная проверка пересобранного рантайма

1. Инвентаризация dist-info: в `Lib\site-packages` должно быть ровно 32 каталога
   `*.dist-info` (список = `requirements.lock`; если оставлен pip — 33-й `pip-*.dist-info`).
2. Смоук-импорт: `python.exe -c "import openai, PyQt6, docx, lxml; print('ok')"`.
3. Офскрин-старт приложения с изолированным `SUPERVERTALER_DATA_ROOT` и трансляция
   через mock OpenAI-сервер — метод и скрипты: Часть C отчёта BATCH P2.3
   (`docs/refactoring/reports/BATCH_P23_REPORT.md`).
