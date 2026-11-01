# ОТЧЁТ Batch P2.0 — Рекон: состав рантайма и requirements (без правок)

**Дата:** 2026-10-31. **База:** origin/main после пуша P1.8 (`6ce6186b`), локально HEAD = `a6b6b455`.
**Дистрибутив:** `supervertaler-portable_20261031_1843.zip` (334 878 720 байт) из
`E:\Dev\Work_temp\SupervertalerPortable\build\`, распакован в
`E:\Dev\Work_temp\SupervertalerPortable\recon-p20\unpacked\` (НЕ в D:\Supervertaler_clean).
**Правок продукта и дев-рантайма нет** (см. §7). Артефакты — `docs/refactoring/audits/p2-0_*`.

---

## §1. Резюме (TL;DR)

1. **Главное открытие: «zip» дистрибутива — не zip.** `make_portable_zip.bat` (шаг [6/6],
   `tar -a -cf *.zip`) фактически пишет **несжатый ustar-tar с расширением .zip**: bsdtar `-a`
   выбирает только фильтр сжатия, а не формат (проверено контрольным файлом). Поэтому «архив»
   (334,9 МБ) **больше** распакованного содержимого (312,1 МБ). Настоящая deflate-упаковка того
   же содержимого — **136,9 МБ (−59 %)**. Бонус: Windows Explorer на Win10 не открывает tar —
   распаковка сейчас требует 7-Zip/tar.
2. **Состав дистрибутива:** 312,1 МБ = python-embed 302,4 (site-packages 278,5) + код 9,7.
   PyQt6 — 206,9 МБ (66 % site-packages, 2/3 всего дистрибутива), из них Qt6\bin 142,6 МБ.
3. **requirements.txt не описывает рантайм ни в одну сторону.** Из 24 пунктов requirements
   **9 никогда не импортируются продуктом** (setuptools, wheel, numpy, sacrebleu, boto3, deepl,
   psutil, chardet, pyobjc); **11 пакетов из requirements в рантайме дистрибутива отсутствуют**
   (anthropic, google-generativeai, sacrebleu, markitdown, PyMuPDF, boto3, deepl, psutil, pynput,
   numpy, setuptools). Зато в рантайме есть dev-инструменты (pytest, pyflakes, pygments, pip).
4. **Найден реальный баг дистрибутива: «PDF Rescue» сломан.** `modules/pdf_rescue_Qt.py:24`
   импортирует `fitz` (PyMuPDF) **без try**, точка входа `Supervertaler.py:9628` тоже без try,
   а PyMuPDF в рантайме нет → клик по меню падает `ModuleNotFoundError: No module named 'fitz'`.
   Воспроизведено офскрин-пробой. Все остальные отсутствующие пакеты (anthropic, google,
   markitdown, pynput) — под try с вежливыми сообщениями, деградируют штатно.
5. **Воспроизводимость: requirements.txt ДОСТАТОЧЕН для старта и перевода** — чистый embedded
   Python 3.13.15 + `pip install --target -r requirements.txt`: импорт 0,3 с, офскрин-старт 3,9 с,
   реальный раундтрип перевода через OpenAI-SDK → мок-сервер OK. Но получается **814 МБ** (в 2,9 раза
   толще дистрибутивного site-packages 278,5 МБ) — из-за markitdown→onnxruntime (48 МБ),
   google-generativeai→google-api-python-client (109 МБ), PyMuPDF 2.0 (105 МБ), numpy (55 МБ).
   **Минимальный набор из 12 пакетов — 315 МБ — тоже проходит старт+перевод.**
6. **Версии нигде не закреплены.** Свежая установка из requirements даёт другие мажоры:
   PyQt6 6.12.0 (в дистрибутиве 6.11.0), openai 3.42.0 (3.24.0), PyMuPDF 2.0 (в дистрибутиве
   отсутствует), Pillow 13.0.0 (12.3.0). Воспроизводимость версии = удача.

## §2. [A] Состав дистрибутива

### 2.1. Верхний уровень (распаковано, сырые размеры)

| Каталог/файл | Размер |
|---|---|
| python-embed | 302,4 МБ |
| — Lib (site-packages 278,5 + stdlib ~4 + Scripts 1,4) | 278,5 МБ |
| — python313.dll / libcrypto-3.dll / python313.zip / sqlite3.dll / libssl-3.dll / get-pip.py | ~23 МБ |
| SupervertalerPortable (код: Supervertaler.py 2,8 + modules 2,6 + translations 2,6 + assets 1,6 + user_data + 3 файла) | 9,7 МБ |
| start.bat | <0,1 МБ |
| **Итого** | **312,1 МБ** |

Архив-«zip»: 334,9 МБ — **больше содержимого** (см. §3).

### 2.2. site-packages (все 278,5 МБ), топ-15

| Пакет | Размер | Пакет | Размер |
|---|---|---|---|
| **PyQt6** | **206,9** | pydantic | 1,7 |
| PIL | 14,0 | docx | 1,5 |
| lxml | 8,5 | _pytest | 1,3 |
| openai | 7,5 | openpyxl | 0,8 |
| spellchecker | 7,0 | anyio | 0,5 |
| pydantic_core | 5,5 | charset_normalizer | 0,5 |
| pip | 5,3 | packaging | 0,5 |
| spylls | 4,9 | | |
| pygments | 4,4 | | |
| chardet | 2,1 | | |

numpy/scipy/pandas в дистрибутивном рантайме **отсутствуют вовсе** (и не импортируются — §4).
`__pycache__` в site-packages: 0 (чисто). tests: 4 каталога, 0,2 МБ (шум). dist-info: 40 записей.

### 2.3. PyQt6 (206,9 МБ) по подпакетам

| Часть | Размер | Часть | Размер |
|---|---|---|---|
| Qt6\bin (109 DLL) | 142,6 | bindings (.toml, build-time) | 3,0 |
| Qt6\plugins | 15,9 | *.pyd-модули (все) | ~30 |
| Qt6\qml | 13,7 | *.pyi-стабы | 2,1 |
| Qt6\translations | 10,1 | qsci | 1,7 |

Топ DLL Qt6\bin: opengl32sw 19,7; avcodec-61 13,4; Qt6Core 9,9; Qt6Gui 9,1; Qt6Quick 6,3;
Qt6Widgets 6,2; Qt6Qml 5,1; **Qt6Designer 5,0**; Qt6Pdf 4,4; Qt6Quick3DRuntimeRender 4,2;
Qt6ShaderTools 4,2; d3dcompiler_47 4,0; Qt6Quick3DPhysics 3,6; Qt6QuickControls2Imagine 3,0.

Топ плагинов: sqldrivers 2,5; sceneparsers 2,3; assetimporters 2,0; imageformats 1,8;
renderers 1,5; qmlls 1,4; platforms 1,1; multimedia 1,0; tls 0,6.

**QtWebEngine в дистрибутиве НЕТ** (ни в Qt6\bin, ни в plugins, ни pyd) — как и в дев-рантайме.

### 2.4. Мусор/dev-инструменты в дистрибутивном рантайме

| Позиция | Размер | Комментарий |
|---|---|---|
| pip | 5,3 МБ | не используется start.bat (P1.8) |
| get-pip.py | 2,1 МБ | для ручного бутстрапа pip |
| pygments | 4,4 МБ | зависимость pytest, продуктом не импортируется |
| _pytest + pytest + iniconfig + pluggy + colorama | ~1,5 МБ | тест-раннер в дистрибутиве |
| pyflakes | 0,3 МБ | одноразовое отклонение 2026-10-23 (AGENTS) |
| chardet | 2,1 МБ | продуктом не импортируется; requests использует charset_normalizer |
| PyQt6 .pyi + bindings | 5,1 МБ | типизация/сборка, рантайму не нужны |

Итого явно лишнего ~**16 МБ** сырых.

## §3. Открытие: «zip» — на самом деле несжатый tar

* Байты 0–7 файла `supervertaler-portable_20261031_1843.zip`: `start.ba…` (имя первого файла
  tar-заголовка), ustar-магия на смещении 257 подтверждена. Python `zipfile` отказывается читать.
* Причина: bat-файл выполняется cmd → используется `C:\Windows\System32\tar.exe` (bsftdar,
  libarchive). У bsdtar `-a/--auto-compress` подбирает только **фильтр сжатия** (.gz/.bz2/.xz…),
  формат `.zip` в этом списке нет → пишется plain tar. Контрольный эксперимент
  `tar -a -cf test.zip f.txt` даёт tar с тем же заголовком.
* Следствия: (а) +198 МБ к размеру поставки; (б) Explorer Win10 не открывает такой файл
  двойным кликом (нужен 7-Zip/tar); (в) расширение .zip вводит в заблуждение.
* Эталонная перепаковка того же содержимого zipfile'ом (deflate, уровень 6):
  **136 924 690 байт = 130,6 МиБ (136,9 МБ)** — 39 секунд. См. `docs/refactoring/audits/p2-0_*`.

## §4. [B] Импорты продукта vs пакеты

Метод: AST-скан `Supervertaler.py` + 90 файлов `modules/**` (91 всего). Классификация каждого
импорта: **обязательный** (top-level без try), **guarded** (top-level в try/except),
**ленивый** (внутри функции/класса). Плюс файловый граф: какие файлы загружаются на старте
(транзитивно от `Supervertaler.py` по обязательным импортам). Скрипты:
`docs/refactoring/audits/scan_b_imports.py`, `scan_b_filegraph.py`; данные: `imports_raw.json`,
`filegraph.json`. Мёртвых файлов нет: все 91 файлов достижимы (после исправления учёта
пакетных реэкспортов `modules/dialogs/__init__`, `modules/workers/__init__`).

### 4.1. Файловый граф

* **Стартовых (обязательных) файлов: 39 из 91** — включая dialogs/*, workers/*, grid/*.
* Ленивых (по требованию): 51. Ключевые: `pdf_rescue_Qt`, `llm_clients`, `docx_handler`,
  `database_manager`, `unified_prompt_manager_qt`, `tmx_*`, `statistics_*`, `okapi_sidecar`.

### 4.2. Внешние импорты по классам (без stdlib)

| Класс | Пакеты |
|---|---|
| **Обязательные на старте** (файл стартовый + top-level без try) | **PyQt6** (91 файл-источник), **pyperclip** (Supervertaler.py:184, superlookup.py:18) |
| **Guarded на старте** (стартовый файл, top-level в try) | spellchecker, spylls, hunspell (spellcheck_manager.py:22/30/39 — hunspell не установлен, фолбэк), tomli (фолбэк, на 3.13 есть tomllib) |
| **Ленивые с защитой** (в try/функциях) | docx, PIL, openai, openpyxl, requests, language_codes*, segmentation_rules* (*локальные), anthropic (pdf_rescue:79), google.generativeai (pdf_rescue:91), markitdown (unified_prompt_manager_qt:5910/6099), pynput (platform_helpers:1013/1187/1261 — только Linux-пути), httpx (llm_clients:763, фолбэк на httpx2) |
| **Ленивые БЕЗ защиты** | **fitz** — top-level `import fitz` в pdf_rescue_Qt.py:24 без try; `docx`/`Pt` там же без try (docx установлен — ок). Точка входа Supervertaler.py:9628 `from modules.pdf_rescue_Qt import PDFRescueQt` тоже без try |
| Динамический импорт (importlib/__import__) | **не найден** |

### 4.3. Сверка трёх списков

**(1) В рантайме, но продуктом не импортируется:**

| Пакет | Размер | Вердикт |
|---|---|---|
| pip | 5,3 МБ | не нужен в рантайме (start.bat его не зовёт) |
| pygments | 4,4 МБ | зависимость pytest; продуктом не импортируется |
| pytest-стек (_pytest, iniconfig, pluggy, colorama) | ~1,5 МБ | dev-инструмент |
| pyflakes | 0,3 МБ | dev-инструмент (остаток отклонения 2026-10-23) |
| chardet | 2,1 МБ | не импортируется; requests работает через charset_normalizer |
| httpx2/httpcore2 | 0,8 МБ | **нужны** — фолбэк openai 3.x (llm_clients:765), комментарий в коде: «openai 3.x's fork» |
| pydantic/pydantic_core/annotated_types/typing_inspection/jiter/anyio/sniffio/truststore/h11 | ~15 МБ | зависимости openai — нужны |
| certifi/idna/charset_normalizer/urllib3 | ~1,5 МБ | зависимости requests — нужны |
| et_xmlfile | <0,1 | зависимость openpyxl — нужна |
| PyQt6 (все не-Widgets/Core/Gui части) | ~125 МБ | см. §6.2 |

**(2) Импортируется, но в рантайме НЕТ:**

| Пакет | Где импорт | Защита | Последствие в дистрибутиве |
|---|---|---|---|
| **fitz (PyMuPDF)** | pdf_rescue_Qt.py:24 top-level без try; вход Supervertaler.py:9628 без try | **нет** | **«PDF Rescue» падает ModuleNotFoundError при клике** (воспроизведено пробой) |
| anthropic | pdf_rescue_Qt.py:79 (в try) | да | AI-клиент Claude в PDF Rescue молча недоступен, вежливое сообщение в лог |
| google.generativeai | pdf_rescue_Qt.py:91 (в try) | да | аналогично для Gemini |
| markitdown | unified_prompt_manager_qt.py:5910, 6099 (в try) | да | импорт файлов .pdf/.docx/.pptx/.xlsx в промпты — заглушка-сообщение |
| pynput | platform_helpers.py:1013/1187/1261 (в try, Linux-only) | да | на Windows не нужен вообще (RegisterHotKey) |
| setuptools, wheel | нигде | — | не нужны: импортов pkg_resources/setuptools в продукте 0 |
| numpy, sacrebleu, boto3, deepl, psutil | нигде | — | **продукт их вообще не импортирует** (ни обязательных, ни ленивых сайтов) |
| hunspell | spellcheck_manager.py:22 (try) | да | фолбэк на spylls/pyspellchecker работает |

**(3) Версии.** requirements — все `>=` без верхних границ. Дистрибутив vs свежая установка
из requirements (2026-10-31, лог `p2-0_pip_install_from_requirements.log`):

| Пакет | Дистрибутив | Свежая установка | Комментарий |
|---|---|---|---|
| PyQt6 / Qt6 | 6.11.0 / 6.11.2 | 6.12.0 / 6.12.0 | мажорный минор сдвинулся |
| openai | 3.24.0 | 3.42.0 | дрейф в пределах мажора |
| Pillow | 12.3.0 | 13.0.0 | **мажор сдвинулся** |
| PyMuPDF | — (нет) | 2.0 (+pymupdf4llm 2.0, pymupdf-layout 2.0) | `>=1.23` уже тянет новую мажорную линейку 2.0 |
| PyYAML | 6.0.3 | 6.0.3 | стабильно |
| lxml / openpyxl / requests / python-docx | 6.1.3 / 3.1.5 / 2.34.2 / 1.2.0 | те же | стабильно |
| pyspellchecker | 0.9.0 | 0.9.1 | минорный дрейф |

Вывод: сборка из requirements сегодня воспроизводит **поведение**, но не **версии**;
завтра — не гарантировано ни то ни другое (пример: PyMuPDF 2.0 — новая линейка).

## §5. [C] Воспроизводимость с нуля

Метод (дев-рантайм не тронут): официальный `python-3.13.15-embed-amd64.zip` (3.13.15 = версия
дев-рантайма; локальная копия в E:\Dev, сеть не понадобилась для интерпретатора) распакован в
`recon-p20\cleanrt\python-embed`; `_pth` патчен (python313.zip, ., Lib\site-packages, pylibs,
E:\Dev\SupervertalerPortable, import site — зеркально дев-рантайму); pip загружен get-pip.py
(26.2.2). Зависимости — строго `pip install --target` из `requirements.txt` (79 пакетов, exit 0).

Проба `probe_clean.py` (QT_QPA_PLATFORM=offscreen, SUPERVERTALER_DATA_ROOT=изолированный iso,
USERPROFILE/APPDATA/HOME → пустые изолированные каталоги — негативный контроль чист):

| Стадия | Полный requirements (814 МБ) | Минимум из 12 пакетов (315 МБ) |
|---|---|---|
| import Supervertaler | OK 0,3 с, v1.10.371 | OK 0,1 с |
| офскрин-старт SupervertalerQt | OK 3,9 с | OK 1,7 с |
| перевод через мок-сервер (LLMClient custom_openai → локальный OpenAI-совместимый эндпоинт) | **OK** (`MOCK:Translate the following…`) | **OK** |
| fitz/markitdown/anthropic/numpy/sacrebleu/boto3/deepl/psutil/pynput/setuptools | все present | все ABSENT |
| import modules.pdf_rescue_Qt | OK | **FAIL: No module named 'fitz'** — ровно поведение дистрибутива |

**Ответы на вопросы C:**
* Хватает ли requirements для старта и перевода через мок-сервер: **ДА, полностью** (даже
  избыточно: хватает минимума из 12 пакетов — PyQt6, pyperclip, openai, requests, python-docx,
  openpyxl, Pillow, lxml, pyyaml, markdown, pyspellchecker, spylls).
* Чего не хватает: **ничего для старта/перевода**. Для полного паритета функций не хватает
  PyMuPDF (PDF Rescue — единственная реально сломанная функция в текущем дистрибутиве),
  опционально markitdown/anthropic/google-generativeai (guarded, деградируют штатно).
* Что лишнее: numpy, sacrebleu, boto3, deepl, psutil, chardet, setuptools, wheel, pyobjc
  (darwin-маркер) — продукт их не импортирует ни при каком пути кода; в рантайме дистрибутива
  их и так нет (кроме chardet).

**Экономика размеров (site-packages):**

| Вариант | Размер | Δ к дистрибутиву (278,5) |
|---|---|---|
| Дистрибутив сейчас | 278,5 МБ | — |
| Полный requirements | 814 МБ | +536 |
| Минимум (12 пакетов) | 315 МБ | +36 (в основном PyMuPDF-эквивалент отсутствует, зато PyQt6 6.12 чуть крупнее) |

Минимум 315 МБ крупнее дистрибутива (278,5 МБ) на +36 МБ **не из-за PyMuPDF (его в минимуме
нет), а из-за дрейфа версий**: свежая установка несёт PyQt6 6.12.0 (222 МБ против 206,9 у 6.11,
+15 МБ), openai 3.42.0 (28 МБ против 7,5 у 3.24, +20 МБ) и прочие пакеты чуть крупнее
(PIL/lxml/spellchecker/spylls — суммарно ещё +5). Поштучная сверка наборов пакетов — P2.2.

## §6. [D] Предложения (без реализации)

### 6.1. Починить упаковку: настоящий ZIP вместо tar-с-расширением-zip
* **Экономия: 334,9 → ~137 МБ (−198 МБ, −59 %)** на том же содержимом; 7z даст ещё меньше.
* **Риск: минимальный.** Варианты: `tar --format zip -cf out.zip …` (bsdtar умеет), либо
  python zipfile, либо сменить расширение на .tar и жить с tar (но без экономии).
  Нюанс: 7-Zip/распаковка у Дмитрия уже работает и с tar; меняется только размер и
  открываемость в Explorer.

### 6.2. Урезать Qt6 до фактически используемого
Продукт импортирует **только QtWidgets/QtCore/QtGui** (178/101/92 включений; QtNetwork,
QtQuick, QtSql и пр. — 0). Кандидаты на удаление из рантайма (сырые МБ; в сжатом zip ≈ ×0.4):

| Категория | МБ (сырые) | Риск |
|---|---|---|
| Quick/QML-стек (Qt6Quick*, Qt6Qml*, ShaderTools, StateMachine, Labs*, qml\, qmlls/qmllint) | ~66 | низкий: QML не используется |
| Multimedia+ffmpeg (Qt6Multimedia*, av*, sw*, плагин multimedia) | ~21 | низкий |
| opengl32sw.dll (программный OpenGL-фолбэк) | 19,7 | **средний**: на машинах без драйверов GL картинка может пропасть; предлагается оставить или решить отдельно |
| Qt6Designer | 5,0 | низкий (не для рантайма) |
| Qt6Pdf* | 5,1 | низкий (QtPdf не импортируется; не путать с fitz) |
| 3D-плагины (sceneparsers, assetimporters, geometryloaders, renderers) | 5,8 | низкий |
| Connectivity (Bluetooth, Nfc, Positioning, SerialPort, RemoteObjects, WebSockets, TextToSpeech, Sensors + плагины) | ~4 | низкий |
| Неиспользуемые PyQt6 *.pyd (QtQuick, QtNetwork, QtSql, …) | 7,7 | низкий |
| .pyi-стабы + bindings | 5,1 | низкий (но .pyi удобны в dev-копии — можно резать только в дистрибутиве) |
| **Итого** | **~135–140 МБ** | |

После сжатия экономия ≈ **55–60 МБ** в поставке. Обязательная проверка: полный офскрин-набор
проб + ручные сценарии на тест-сборке (у нового тест-билда та же процедура пересборки —
отдельное решение Дмитрия).

### 6.3. Убрать dev-инструменты и мёртвые пакеты из дистрибутива
pip (5,3) + get-pip.py (2,1) + pygments (4,4) + pytest-стек (~1,5) + pyflakes (0,3) +
chardet (2,1) ≈ **16 МБ сырых (~6 МБ в сжатом)**. Риск низкий; решение о pip — отдельно
(если хотим дать пользователю возможность доустановить, например, WebEngine — pip оставить).

### 6.4. WebEngine — факты
`grep` по продукту: **0 реальных использований**; единственное упоминание QWebEngine —
исторический комментарий Supervertaler.py:54468 о падениях при инициализации в офскрин-пробах.
WebEngine в дистрибутиве и дев-рантайме отсутствует, Web Resources работает в фолбэке (P1.8).
Добавление = +340 МБ — не рекомендуется без новой функциональной потребности.

### 6.5. requirements.txt: переписать и закрепить (pin/lock)
* Разделить на **обязательные** (12 пакетов из §5, все импортируются) и **опциональные
  экстра-группы**: `[pdf]` PyMuPDF (чинит PDF Rescue в дистрибутиве), `[import]` markitdown
  (тянет onnxruntime 48 МБ — предупредить), `[ai-extra]` anthropic, google-generativeai
  (последний тянет google-api-python-client 109 МБ — для guarded-ленивого импорта это очень дорого).
* **Удалить** из обязательных: numpy, sacrebleu, boto3, deepl, psutil, chardet, setuptools, wheel.
* pynput оставить только под `sys_platform == "linux"` (аналогично pyobjc под darwin).
* **Pin/lock: нужен.** Все диапазоны `>=` уже дали дрейф мажоров (Pillow 13, PyMuPDF 2.0,
  PyQt6 6.12). Предложение: `requirements.lock` = `pip freeze` дев-рантайма (то, что реально
  в дистрибутиве), а requirements.txt — декларация с диапазонами. Правки dev-рантайма не
  требуются (freeze — только чтение).

### 6.6. Починить PDF Rescue в дистрибутиве (баг, не оптимизация)
Варианты: (а) включить PyMuPDF в дистрибутив (+~20–25 МБ сжато для wheel базового пакета);
(б) обернуть `import fitz` и точку входа в try с вежливым сообщением, как у anthropic/markitdown.
Решение за координатором; (б) дешевле, (а) возвращает функцию.

### 6.7. Сводка потенциала поставки
334,9 МБ сейчас → 136,9 (настоящий zip) → ~80 МБ (минус Qt-урезание ~57) → ~74 МБ (минус
dev-мусор ~6) → +20–25 МБ если добавляем PyMuPDF. **Целевые ~95–100 МБ с PDF Rescue** против
334,9 сегодня.

## §7. Защита

* `git status --porcelain` по продукту: **чисто** (изменений Supervertaler.py/modules/
  translations/assets нет; untracked — только служебные .zcode и новые docs-файлы этого батча).
* Дев-рантайм `E:\Dev\python-embed`: **не изменялся** (все pip-операции — в
  `recon-p20\cleanrt` и `--target recon-p20\pylibs*`; readonly-использование интерпретатора).
  sha256-манифест не снимался — правок не было, подтверждение чтением (§5).
* Статические числа, было = стало: **py_compile 267 ok / 0 fail** по всем tracked .py
  **на момент замера** (замер шёл до коммита P2.0). После коммита P2.0 (7 скриптов в audits/)
  референс: **274 tracked .py всего, из них код вне docs/ — 108**; по коду продукта по-прежнему
  0 изменений (было = стало).
  Реестры и реальные пользовательские данные не тронуты: пробы с SUPERVERTALER_DATA_ROOT
  в `recon-p20\iso`, негативный контроль (USERPROFILE и пр.) — чисто.
* Процессы после проб убраны; пользовательский экземпляр из исторического тест-билда
  `D:\SupervertalerPortable_test` (PID 61716) не затронут.

## §8. Артефакты

`docs/refactoring/audits/`: p2-0_sizes_a.out (верхний уровень+site-packages), p2-0_sizes_a2.out
(Qt6-детали, топ-файлы), p2-0_imports_scan.out, p2-0_filegraph.out, p2-0_imports_raw.json,
p2-0_filegraph.json, p2-0_qt_categories.out, p2-0_pip_install_from_requirements.log,
p2-0_probe_clean_full_reqs.out, p2-0_probe_clean_minimal.out; скрипты (переименованы с
префиксом p2-0_ по вердикту): p2-0_sizes_a.py, p2-0_sizes_a2.py, p2-0_scan_b_imports.py,
p2-0_scan_b_filegraph.py, p2-0_qt_categories.py, p2-0_probe_clean.py, p2-0_mock_openai_server.py.

Рабочая область: `E:\Dev\Work_temp\SupervertalerPortable\recon-p20\` (unpacked, cleanrt,
pylibs 814 МБ, pylibs_min 315 МБ, iso-профиль, логи) — удерживается до вердикта, может быть
удалена после (кроме потенциально полезного cleanrt для будущих пин-батчей).

## §9. Вопросы координатору

1. **Упаковка**: подтверждаете перевод `make_portable_zip.bat` на настоящий zip
   (или 7z)? Это отдельный мини-батч (правка bat-шаблона + пересборка тест-сборки).
2. **PDF Rescue**: (а) добавить PyMuPDF в дистрибутив или (б) обернуть импорт в try
   с сообщением? (б) можно включить в ближайший кодовый батч, (а) требует пересборки.
3. **requirements.txt**: делать ли сплит обязательные/экстры + lock-файл (заморозка версий)?
   Если да — генерировать lock из текущего дев-рантайма (pip freeze, без изменений рантайма)?
4. **Урезание Qt6 и dev-мусора**: проводить ли как батч «минимальный дистрибутив» с полной
   офскрин-верификацией и ручными T-тестами на пересобранной тест-сборке? opengl32sw.dll
   (19,7 МБ) — оставить как страховку от машин без GPU-драйверов или резать?

## §10. Стоп

Ручных тестов для Дмитрия нет (рекон). Останов до вердикта; следующий батч — только по
команде и промпту.

## §11. ВЕРДИКТ координатора: GO (Дмитрий, 2026-10-31) — ответы на §9

* **Неточность отчёта (§5)** признана и исправлена: «минимум 315 МБ крупнее дистрибутива
  из-за PyMuPDF» было неверно (PyMuPDF в минимуме нет); реальная причина — дрейф версий
  (PyQt6 6.12 крупнее 6.11 на ~15 МБ, openai 3.42 крупнее 3.24 на ~20 МБ). На выводы батча
  не влияет. **P2.2:** поштучное сравнение двух наборов пакетов (дистрибутив vs минимум).
* **§9.1 (упаковка): ДА** — переводим `make_portable_zip.bat` на настоящий ZIP (deflate,
  через Python zipfile); 7z не берём (отдельная программа). Промпт P2.1 — в новом чате.
* **§9.2 (PDF Rescue): удаляем целиком** — будет отдельный промт (после P2.1).
* **§9.3 (requirements): ДА** — сплит на обязательные (12 пакетов) и опциональные + lock-файл.
  Lock — не сырой `pip freeze` дев-рантайма (там pytest и прочее), а версии, реально лежащие
  в дистрибутиве и проверенные (PyQt6 6.11.0, не 6.12). Это P2.2, после решения по PDF Rescue.
* **§9.4 (урезание):** dev-мусор (pygments, pytest-стек, pyflakes, chardet, get-pip.py)
  убираем из дистрибутива при упаковке (P2.1); **pip оставляем** (нужен для доустановки).
  Урезание Qt (~135 МБ сырых) сейчас НЕ делаем: выигрыш ~55–60 МБ в zip против реального
  риска потери редких путей; вернёмся, если размер начнёт мешать. **opengl32sw.dll оставляем.**
* Рабочая папка `recon-p20\` чистится после пуша: удаляются `unpacked`, `pylibs` (814 МБ),
  `pylibs_min`; остаются `cleanrt` и логи. Второй отчёт (PyMuPDF4LLM) не коммитится, как решено.
