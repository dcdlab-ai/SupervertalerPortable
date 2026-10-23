# RECON O.0 — OCR-инструмент для изображений: разведка кода (read-only)

Дата: 2026-10-18. Роль: исполнитель. Координатор: Дмитрий. Пуш не выполнялся.
HEAD: `9321764b` == `origin/main` (Шаг 0 чистый). Код продукта не изменён.
В working tree на момент старта: предсуществующие незакоммиченные правки `modules/settings_service.py` (не трогались, в коммит не включены) и untracked `.zcodeignore`, `.zcode/plans/…`.

---

## Краткие выводы (TL;DR)

1. **PDF Rescue — изолированный соседний модуль**: 1758 строк, подключён 3 строками меню + 28-строчным обработчиком; удаление не задевает общий код вообще (обратная связь — только `load_api_keys()` и `log()`, утиные). OCR-инструмент строится по той же паре «QAction → open_*_window → create_tab».
2. **Виджета рисования прямоугольников на картинке в проекте нет**: ни `QGraphicsView`, ни `QRubberBand`, ни маппинга координат. Canvas придётся писать с нуля; переиспользовать можно базовые куски (QLabel-превью, base64-энкодер, конвейер payload).
3. **Vision-вызов через активный Custom-профиль существует и работает** (Image Extractor AI-подписи — рабочий образец). Профиль без `supports_vision`: клиент молча выкидывает картинки (`llm_clients.py:453-454`), UI-гейты на местах. Стриминга нет; таймауты 120/600 с; пустой `content` у reasoning-моделей → `ValueError` (обработки `reasoning_content` нет, запись в BACKLOG G3.2) — реальный риск для OCR.
4. **Pillow в сборке есть: 12.3.0** (pip show бандла; `requirements.txt:17 Pillow>=10.0.0`). Crop/поворот/LANCZOS/контраст/PNG→base64 доступны уже сейчас.
5. **Round-trip .txt проверен пробой на текущем коде**: импорт строка=сегмент, пустые строки сохраняются, leading/trailing-пробелы, табы, BOM, `<1>`-теги, литеральный `\n` и md-ссылки проходят байт-в-байт (режим без сегментации по предложениям). С включённым чекбоксом сегментации — leading/trailing-пробелы строки теряются (strip). Предложен формат с устойчивыми ID (см. §5).
6. **CSV с нужным образцом ( ; / cp1251 / CRLF / без BOM ) в проекте нет**: вся существующая CSV-механика — TSV-tab и запятая в `utf-8-sig`; cp1251 и `;` в репозитории не встречаются нигде. Реализация — стандартный `csv` с явными параметрами (см. §6); совместимость с InDesign 2021/2026 проверяет Дмитрий руками (O.5).
7. **Единственный механизм относительных путей в приложении — `modules/project_assets.py`** (`os.path.relpath` от `.svproj`); папки изображений хранятся абсолютным путём, переезд папки = только warning в лог. Для layout'ов нужно использовать relpath-паттерн project_assets (см. §7).
8. **Промпты хранятся файлами** (`.md` в `user_data/prompt_library/` + механизм внешнего prompt-файла `[EXTERNAL] <путь>`); хардкод промпта в коде — антипаттерн (пример: Image Extractor, `Supervertaler.py:10011-10036`). Для OCR — файл в библиотеке + переопределение в проекте инструмента (см. §8).
9. **md-ссылка в пакетном переводе**: сегмент `![Image](/path/file.png)` **не блокируется и отправляется в LLM как текст дословно**; в target записывается дословный вывод модели (status `draft`). В vision он не попадает никогда (фигур-детект — по ключевым словам, парсинга `![..](..)` нет).
10. **Архитектура**: отдельный пакет `modules/ocr_tool/` (layout-модель, canvas, vision-воркер, двухэтапный .txt-конвейер, CSV-экспорт, окно по образцу PDF Rescue) + батчи O.1–O.5 (§10).

**Вопросы координатору** — сводный список в §10.3 (10 вопросов, по формату ID, многострочности, режиму импорта, паре языков, месту промпта, layout-хранилищу, выбору профиля, диалогу стоимости, standalone-режиму, именам колонок CSV).

---

## 1. PDF Rescue

Файл: `modules/pdf_rescue_Qt.py` — 1758 строк; README `modules/PDF_RESCUE_README.md` — 323 строки.

* Структура: один top-level класс `PDFRescueQt` (`modules/pdf_rescue_Qt.py:31`); вложенный `StandaloneApp(QMainWindow)` только в `__main__` (`:1661-1757`). **QThread/воркеров нет** — синхронные циклы с `processEvents()` (`:432, :461, :916, :954`).
* Подключение к приложению: QAction `Supervertaler.py:8352-8354` (Tools-меню, без шортката); обработчик `open_pdf_rescue_window` `Supervertaler.py:9754-9781`: ленивый импорт `:9757`, переиспользование окна через `self._pdf_rescue_window` `:9759-9767`, конструктор `PDFRescueQt(self, standalone=False)` `:9775`, `create_tab(window)` `:9776`, `WA_DeleteOnClose` `:9780`.
* Настроек нет: QSettings-ключей, вкладок настроек, записей в `settings_service.py`/`config_manager.py` для PDF Rescue — ноль (grep). Промпт — хардкод-дефолт в UI (`pdf_rescue_Qt.py:288-302`), не в промпт-библиотеке.
* Зависимости модуля: `fitz  # PyMuPDF` `:24` (объявлена `requirements.txt:50 PyMuPDF>=1.23.0`; **общая с ядром** — `Supervertaler.py` тоже импортирует fitz, т.е. PyMuPDF не «-pdf-rescue-only»), `docx` `:22-23`, лениво `openai`/`anthropic`/`google.generativeai` `:69/:79/:91`; `modules.platform_helpers.open_file` `:13`, `modules.styled_widgets.CheckmarkCheckBox` `:28`.
* Обратная связность (blast radius при удалении): импортирует модуль **только** `Supervertaler.py:9757`. Код, существующий только ради PDF Rescue: `Supervertaler.py:8352-8354`, `Supervertaler.py:9754-9781`, `modules/help_system.py:168` (`TOOL_PDF_RESCUE`, мёртвая константа — ноль использований), README + упоминания в docs (`DEPENDENCY_MAP.md` и др.) и переводах (`translations/supervertaler_template.xlf:1963, :2500`). В общем коде при удалении не ломается ничего.
* Колбэки в приложение — утиные, `hasattr`-гейты: `parent_app.load_api_keys()` (`pdf_rescue_Qt.py:53-58` → `Supervertaler.py:50887-50894`), `parent_app.log()` (`:102` → `Supervertaler.py:47345`). Функций перевода/проекта не использует. Общий код использует только `platform_helpers` и `styled_widgets`. `llm_clients`, `usage_log`, `unified_prompt_library`, `get_user_data_path` — **не использует** (свои SDK-клиенты `:63-98`).
* Шаблон соседнего инструмента (для OCR): тот же канон — TMX Editor `Supervertaler.py:9152-9207` (инъекция общего состояния в конструктор), Superlookup `:8356-8360`, Scratchpad `:8394-8398`.

**Оценка связности: низкая.** OCR-инструмент как соседний модуль того же типа — тривиальное подключение; решение об удалении PDF Rescue не принято, при удалении достаточно удалить две точки в `Supervertaler.py` + константу help + файлы.

## 2. Виджеты работы с изображением

* `modules/image_extractor.py` (665 строк) — **ноль GUI-кода**: Docx-извлечение картинок + детект подписей; класс `ImageExtractor` `:453`; PIL `Image.open(BytesIO(...))` `:432`.
* Показ картинки: `QLabel`-превью в `QScrollArea` — `Supervertaler.py:9701-9713`, обновление `_update_preview` `:10223-10260` (scale-to-fit `:10254-10258`). Зума нет (README `IMAGE_EXTRACTOR_README.md:143` — «unimplemented»), **рисования прямоугольников нигде нет**: grep `QRubberBand|QGraphicsView|QGraphicsScene|QGraphicsRectItem|setScaledContents` по модулям и монометру — ноль.
* Вкладка Reference Images («Image Context»): фабрика `create_reference_images_tab` `Supervertaler.py:9405`, встроена в стек Prompt Manager `:8980-8989`; показ — тот же QLabel-превью; мышиная обвязка только `QListWidget.itemClicked` `:9672`. Прочие показо-картинки: чат-миниатюры 48×48 (`chat_view_widget.py:894-907`), tkinter-полоса миниатюр в figure-менеджере (`figure_context_manager.py:260-313`, Qt-приложением не вызывается). overlay-прецедент: `_PreviewTextEdit.paintEvent` `Supervertaler.py:34403-34429` (QPainter по viewport, не картинка).
* `_build_image_extract_ai_callback` (`Supervertaler.py:9863`): гейты — чекбокс `:9877`, наличие клиента `:9882-9884`, vision-гейт диалогом `:9901-9919` (Cancel→False/OK→None), пред-подсчёт `:9926`, **диалог подтверждения стоимости** с эвристикой цен `:9950-9981`. Сам вызов `:9991-10065`: PIL→RGB→`pil_image_to_base64_png` (`figure_context_manager.py:427-440`), payload `[('figure', b64)]` `:10003-10005`, контекст-сниппет 1500 симв `:10007-10009`, промпт-литералы `:10011-10036`, транспорт `chat_backend.send_ai_request(..., images=payload)` `:10038-10041`; постобработка ответа (квотирование, отбраковка «unlabelled», лимит 80 символов, первая строка) `:10045-10061`.
* **Вывод:** как заготовку OCR-вызова — годится целиком (кроме постобработки под подпись). Для рисования прямоугольников годится только каркас (скролл+QLabel+QPixmap-пайплайн); canvas (сцена, rectangle-итемы, rubber band, маппинг widget↔image, поворот/увеличение, кроп) — строить с нуля.

## 3. Vision-вызов вне translate_current_segment

* `modules/llm_clients.py`: единственный исполняемый класс `LLMClient` `:133` (Anthropic/Google/Ollama удалены из модуля; docstring `:8-13`); в рантайме работает только ветка `provider == "custom_openai"` (`:460-463`). Поля профиля Custom (в `settings.json`): `name`, `endpoint`, `model`, `api_key`, `supports_vision` (канон docstring `Supervertaler.py:47569-47576`; дефолты `settings_service.py:273-284`, миграция `'supports_vision': False` `:300`; UI-чекбокс `Supervertaler.py:19379, 19415-19422, 23078`).
* Мультимодальный контент строит `_call_openai_with_usage`: `content = [{"type":"text","text":prompt}]` + по картинке `{"type":"image_url","image_url":{"url":"data:image/png;base64,…"}}` (`llm_clients.py:520-524`); контракт `images: List[Tuple[ref, base64_png]]`, ref в payload теряется.
* Поведение без vision: `llm_clients.py:453-454` — `images` молча обнуляется (ничего не летит наружу). UI-гейты по местам: перевод сегмента — не шлёт, лог с подсказкой про чекбокс (`Supervertaler.py:48976, 49008`); Image Extractor — диалог с abort/text-only (`:9902-9918`); AutoPrompt — диалог+abort (`unified_prompt_manager_qt.py:4456-4468`). Для OCR нужен свой гейт того же типа.
* Таймауты: 600 с reasoning (`gpt-5/o1/o3`) / 120 с остальные — `llm_clients.py:501-503`, применяется к SDK-клиенту, прокси и запросу (`:505, :508-510, :531`); настройки таймаута в settings нет. Стриминга нет — один блокирующий `chat.completions.create` (`:538`).
* Отмена: отсоединение сигналов у QThread-воркера (`unified_prompt_manager_qt.py:112-118, 6545-6553`), флаг `_cancelled` с проверкой между сегментами (`workers/proofread.py:29-32, 96`; пакетный воркер `Supervertaler.py:5317, 5511-5513`). Сам HTTP-запрос прервать нельзя — отмена только между вызовами.
* Пустой `content` у reasoning-моделей: **обработки нет**; `response.choices[0].message.content` пуст → `ValueError("OpenAI returned empty response…")` (`llm_clients.py:540-545`). Реальность кейса: `docs/refactoring/logT-G510.txt:134-143` (`content: ""`, ответ в `reasoning_content`, reasoning_tokens 5103); задача в бэклоге: `POST_BATCH8_BACKLOG.md` G3.2. Для OCR это критично: reasoning-профиль Дмитрия может возвращать пустой content — воркер обязан это обрабатывать (фолбэк на `reasoning_content`), сейчас фолбэка нет нигде.
* Активный профиль для вспомогательных вызовов: фабрика `create_llm_client` `Supervertaler.py:47727-47760` (endpoint/модель/ключ профиля, vision-флаг, прокси); готовность — `_custom_llm_ready` `:47554-47566`. Ключи: `settings.json[api_keys]` (`settings_service.py:412-419`) + legacy `api_keys.txt` fallback (`llm_clients.py:35-118`), ключ профиля важнее.
* Двухуровневый транспорт для переиспользования: `chat_backend.send_ai_request(prompt, system_prompt, is_analysis, images)` (`chat_backend.py:187-258`) → `llm_client.translate_with_usage(images=...)` (`llm_clients.py:422+`); учёт — `usage_log.UsageContext(task="Chat")` (`chat_backend.py:209`). Второй образец threaded-вызова с картинками: `_AutoPromptWorker` (`unified_prompt_manager_qt.py:109-143` + `:4481-4484`).

## 4. Обработка изображений

* Pillow в бандле: **`pip show` → 12.3.0** (E:\Dev\python-embed); декларации: `requirements.txt:17 Pillow>=10.0.0`, `pyproject.toml:65`. Используется: `image_extractor.py:58,432`; `figure_context_manager.py:19-31` (guarded), `:168` (Image.open), `:290` (thumbnail LANCZOS); `pdf_rescue_Qt.py:883`; `Supervertaler.py:9995`.
* Всё требуемое есть в Pillow: `Image.crop` (прямоугольник), `Image.rotate(angle, expand=True)` (и 90/180, и произвольный угол), `Image.resize(..., Image.Resampling.LANCZOS)` (увеличение), `ImageOps.grayscale`, `ImageOps.autocontrast` (серый/контраст), `img.save(buffer, format='PNG')` → base64. Готовый энкодер: `pil_image_to_base64_png` (`figure_context_manager.py:427-440`).
* Готовой crop/rotate-логики в приложении нет (grep `rotate|LANCZOS` — только thumbnail).
* Память: PIL ленивый (`Image.open` читает заголовок; полная декодировка при `crop`/`resize`). Оценка: растер 2500×3500 px (A4 300 dpi) RGBA ≈ 35 МБ на декодированное изображение; PNG-enkod после кроя прямоугольника — единицы МБ. Существующий прецедент памяти: `figure_context_manager` держит в `figure_context_map` **все** открытые PIL-изображения папки (`:172`) — при больших папках растёт; для OCR-инструмента рекомендация: декодировать только кроп-прямоугольник, оригинал выгружать после экспорта (в модели layout хранить путь, не объект).

## 5. Двухэтапный перевод через .txt

Правила импорта (`import_simple_txt`, `Supervertaler.py:29693`; docstring `:29694-29701`):
* **Строка = сегмент**; пустая строка = пустой сегмент (сохраняется для структуры); `rstrip('\r\n')` — ведущие/концевые пробелы строки сохраняются (`:29885-29892`); `paragraph_id = line_num`.
* Чтение `utf-8` с fallback `latin-1/cp1252/iso-8859-1` (`:29858-29860, 29970-29973`); **cp1251 в импорте нет**.
* Чекбокс «Split lines into sentences» (`:29786-29793`): строка режется SimpleSegmenter по правилам `segmentation_rules` (SRX-модель; применяются **на импорте**, не на лету); предложения получают общий `paragraph_id` и `join_before` (сохранённый межсегментный пробел).
* Тег-защиты на импорте нет: md-строки проходят как есть; `![Image](x.png)` не детектируется никаким tag-паттерном `tag_manager.py:61, 1198, 1227, 1660` (все требуют угловых скобок или числовых `[\d+]`).

Экспорт (`export_simple_txt`, `Supervertaler.py:30058`):
* только **target** (source как fallback при радиокнопке «Use source text», `:30111-30115`); склейка предложений по `paragraph_id` + `join_segments` (`:30193-30207`); запись `newline='\n'` (**LF**), кодировки UTF-8 / UTF-8-BOM / Latin-1 / Windows-1252 (`:30127-30131`, **cp1251 нет**).
* Экспорт требует хотя бы один переведённый сегмент (гейт `translated_count==0` `:30074-30081`).

**Round-trip проба на текущем коде** (offscreen, полный app, изолированный профиль `user_data` в стаге, мок диалогов; скрипт и JSON в стаге `E:\Dev\Work_temp\SupervertalerPortable\recon-o0\roundtrip\`):
* A (без сегментации по предложениям, вход CRLF, target=source): 10 строк → 10 сегментов, экспорт **байт-в-байт совпал** с ожидаемым LF-файлом (CRLF входа нормализуется в LF, финальный перевод строки добавляется). Сохранены: кириллица, `<1>`/`<10>`-теги, литеральный `\n` (два символа), `![Image](/path/file.png)`, `<br>`, табы, ведущие/концевые пробелы, пустая строка.
* S (сегментация по предложениям ON): 13 сегментов; многосрочная строка «First sentence. Second sentence! Third? End.» разрезана на 4 с `join_before=' '` и **склеена на экспорте байт-в-байт**; md-ссылка осталась атомарной (мягкий гейт сегментер-стража не дал резать по «.png)»). **Потеря**: ведущие/концевые пробелы строки (`.strip()`, `simple_segmenter.py:100-109`) — единственная байт-несовпадение.
* B: fallback «Use source text» работает (переведённый сегмент → target, прочие → source).
* C: BOM входа (EF BB BF) попадает в source 1-го сегмента как `\ufeff` и на экспорте utf-8 восстанавливается в начале файла (символ кодируется теми же байтами) — BOM переживает round-trip.

**Предлагаемый формат .txt (для двухэтапного конвейера):**
* 1 прямоугольник = 1 физическая строка; пустые строки — структурные разделители (сохраняются).
* Устойчивый ID — числовой тег `<NNNN>` в начале строки: распознаётся `_AUTOTAG_TAG_PATTERN` (`tag_manager.py:1227`) и включает в пакетном переводе защиту тегов в промпте (`Supervertaler.py:5724-5726`); при переносе строк ID стабилен (номер прямоугольника не зависит от позиции).
* Многострочный текст внутри прямоугольника — литеральный `\n` (два символа) (encode/decode делает инструмент, при round-trip проходит как есть — проверено в A/S).
* Импорт — с выключенным чекбоксом сегментации (режим A: гарантия байт-идентичности, без strip-потерь).
* Соответствие прямоугольник↔сегмент после перевода: парсинг экспортированного txt по `<NNNN>` (инструмент сам знает, что на строке K живёт ID; если переводчик слил строки — ID-теги идентифицируют прямоугольник независимо от позиции).

## 6. CSV-экспорт

Существующее (все hits по репозиторию):
* Термбазы: **TSV** — `csv.DictReader/Writer(delimiter='\t')`, `utf-8-sig` (BOM) `termbase_import_export.py:111-119, 420-422`; импорт/экспорт окна `Supervertaler.py:17574-17608, 17811-17838`.
* Логи/статистика: **запятая** (диалект csv по умолчанию), `utf-8-sig` — `usage_log.py:299-304` (кнопка `usage_report_dialog.py:47-49, 143`), `statistics_dialog_qt.py:496-529`.
* `;` как разделитель, `cp1251`/`windows-1251`, запись без BOM — **весь репозиторий: ноль hits**. Явных `\r\n`-писалок нет: все csv-открытия `newline=''`, линетерминатор csv-диалекта (`\r\n`) применяется сам.

Предложение (реализация в O.4, стандартный `csv`):
```python
with open(path, 'w', encoding='cp1251', newline='') as f:
    w = csv.writer(f, delimiter=';', lineterminator='\r\n')  # QUOTE_MINIMAL по умолчанию
```
* Параметры (разделитель / кодировка / EOL / токен переноса внутри ячейки) — настройки инструмента (JSON); перенос внутри ячейки: внутренний `\n` из литерального `\n` прямоугольника; csv экранирует ячейку кавычками автоматически (QUOTE_MINIMAL) — формат совпадает с Excel-образцом.
* Wide: строка = изображение, заголовки = ID прямоугольников; long: строка = прямоугольник (колонки: id, текст). Символы вне cp1251 (эмодзи, CJK) упадут в UnicodeEncodeError — нужен `errors='replace'` и предупреждение.
* **Совместимость с InDesign Data Merge 2021 и 2026 проверяет Дмитрий вручную (O.5) — код этого не проверяет.**

## 7. Хранение layout'ов и проектов

* user_data: абсолютный путь из pointer-файла `%APPDATA%\Supervertaler\config.json` (`Supervertaler.py:170-235`; значение пишется абсолютным `:212-215`); portable-механики «относительно корня программы» для user_data нет.
* Проекты приложения: JSON `.svproj` (`:28450-28451`); единственный механизм относительных путей — `modules/project_assets.py`: `bundle_source` возвращает POSIX-relpath от папки проекта (`:101`), `to_project_relative` (`:43-52`, cross-drive→None), `resolve_source_path` (`:29-40`); потребление `Supervertaler.py:28412-28431, 26578`.
* Прецедент с папкой картинок (уроки): `image_context_folder` сохраняется **абсолютным** путём (`:26542`), при загрузке проекта `os.path.exists` — если папки нет, только лог «⚠️ Saved image folder not found» (`:28312-28320`), перепривязки нет.
* Предложение: проект инструмента = папка (`.svproj`-стиль, `nest_in_own_folder`, `project_assets.py:55-71`); layout'ы = JSON внутри папки проекта; путь изображения в layout — **relpath от папки проекта** (паттерн project_assets, cross-drive-guard); резолв при загрузке + гейт «изображения не найдены → диалог выбора новой папки» (механизма перепривязки в приложении нет — писать).

## 8. Промпты (место и формат, реализация не делается)

* Промпты приложения — файлы: `.md` с YAML-frontmatter в `user_data/prompt_library/` (рекурсивно, `.md/.svprompt/.txt`) — `unified_prompt_library.py:99-143, save_prompt :382-478`; есть внешний prompt-файл `[EXTERNAL] <абс. путь>` (`:527`, сохранение в проекте `Supervertaler.py:26471-26485`).
* Хардкод-пример (антипаттерн): Image Extractor-промпт — литералы `Supervertaler.py:10011-10036`; PDF Rescue — дефолт в UI `pdf_rescue_Qt.py:288-302`.
* Предложение для OCR:
  * дефолт — `user_data/prompt_library/ocr/ocr_prompt.md` (frontmatter `type: prompt`, стандартный формат библиотеки → совместимо с будущим выносом промптов);
  * переопределение — файл `ocr_prompt.md` в папке проекта инструмента (рядом с layout'ами): если есть — использовать его, fallback на библиотеку;
  * формат тела: system-часть + плейсхолдеры `{CONTEXT}` (языки/домен), без зашивки в код.

## 9. md-ссылка в пакетном переводе (побочный вопрос)

Статика по воркеру `PreTranslationWorker` (`Supervertaler.py:5286`):
* Гейды включения: только статус-скоуп (`:49660-49720`) и непустой source (`:49901, 49907`). Гейдов «нет букв», «md-ссылка», «уже автотега» в воркере нет.
* В batch-промпт сегмент попадает дословно: `f"{seg.id}. {seg.source}"` (`:5741-5742`); картинок в batch нет (клиент строится без vision-флага `:5750-5756`, `images=` отсутствует); instruction-о-тегах добавляется только если есть числовые теги `</?\d+/?>` (`:5724-5726`) — для md-ссылки нет.
* Ответ: парсинг `^(\d+)\.\s*(.*)` (`:5784`), в `segment.target` — дословный вывод модели, `status="draft"` (`:5447-5456`).
* AutoTagger (отдельный режим): гейт `if not autotag_extract_tags(source): return None` (`:5914-5915`) — `![Image](/path/file.png)` **не** матчится ни одному tag-паттерну (проверено прогоном функций `tag_manager.py` на реальной строке: `[]`) → сегмент пропускается без LLM-вызова.
* Фигур-vision в md-ссылку не подключается: парсинга `![..](..)` в коде нет; `detect_figure_references` — ключевые слова+номер (`figure_context_manager.py:54-73`: `figure|fig|рисунок…`); в `![Image](/path/file.png)` ключевого слова нет → даже в одиночном переводе картинка не подключается. (Нюанс: `![Figure 1](x.png)` с ключевым словом в alt — в одиночном переводе картинку приаттачит, если файл в loaded-папке.)
**Итог: не блокируется; отправляется в LLM текстом как есть; в target — дословный вывод модели.** Runtime-проверка через fake-endpoint не понадобилась — путь статически однозначен (решение «отправить/не отправить» принимается до всякого ввода; вход = строка).

## 10. Архитектура и план

### 10.1 Структура модулей
```
modules/ocr_tool/
  __init__.py
  layout.py      # модель: Rect{id, xywh, rotation, scale, ocr_text, translated}, Layout{image_relpath, rects[]}
                 # JSON-serialize/restore; relpath-дисциплина (паттерн project_assets)
  canvas.py      # QGraphicsView + QGraphicsPixmapItem; rect-итемы, rubber band, перетаскивание;
                 # маппинг widget↔image (zoom/rotation transform); поворот 90/180/произвольный, LANCZOS-увеличение
  vision.py      # QThread-воркер: crop→rotate→upscale→pil_image_to_base64_png→send_ai_request(images=[(ref,b64)]);
                 # гейты: _custom_llm_ready + supports_vision + диалог стоимости (паттерн Supervertaler.py:9901-9981);
                 # фолбэк пустого content (reasoning_content) — обязателен (G3.2-пробел)
  pipeline.py    # .txt двухэтапный: export layout→txt (<NNNN> ID, \n-encoding); import переведённого txt→rect;
                 # round-trip-инварианты из пробы O.0
  csv_export.py  # csv-модуль: delimiter/encoding/EOL/перенос в ячейке; режимы wide/long (см. §6)
  dialog.py      # OcrToolQt(parent_app, standalone=False) + create_tab(widget) — канон PDF Rescue
  settings.py    # конфиг инструмента (csv-параметры, путь промпта) — в user_data/workbench/settings/
```
Точка входа: Tools-меню QAction (~3 строки по образцу `Supervertaler.py:8352-8354`) + `open_ocr_tool_window` (~28 строк по образцу `:9754-9781`). Промпт — файл (§8), не литерал.

### 10.2 Батчи O.1–O.5 (оценка объёма/рисков)
| Батч | Содержание | Объём | Риски |
|---|---|---|---|
| O.1 | layout-модель + canvas (рисование, поворот, зум, save/load JSON) | ~400–600 строк | маппинг координат/масштаба; QGraphicsView-квирки (нулевой прецедент в приложении); offscreen-тесты без QGraphicsView-опыта |
| O.2 | vision-OCR вызов (crop/трансформы→base64→llm; гейты, отмена, пустой content) | ~200–300 строк | пустой content reasoning (G3.2) — без фолбэка будет ValueError; стоимость (диалог как :9950-9981); отмена между вызовами |
| O.3 | двухэтапный .txt конвейер (ID-формат, round-trip, маппинг rect↔segment) | ~150–250 строк | strip-потери при сегментации (проба S); слип строк переводчиком; парсинг по ID |
| O.4 | CSV-экспорт + настройки | ~150–250 строк | символы вне cp1251; экранирование переносов в ячейке |
| O.5 | интеграция: меню, persistence (relpath-перепривязка), ручные GUI-тесты на frozen build, проверка InDesign 2021/2026 Дмитнием | — | перепривязка перемещённых папок (нового механизма нет) |

### 10.3 Вопросы координатору
1. Формат ID: `<NNNN>` (тег-защита в пакете, проверено) — ок? Альтернатива без защиты — обычный `NNNN:` (LLM может «перевести»).
2. Многострочность прямоугольника = литеральный `\n` в txt — ок?
3. Импорт txt для конвейера — фиксированный режим «без сегментации по предложениям»? (гарантирует байт-identical round-trip)
4. Языковая пара OCR-проекта: фиксированная (RU→основной) или выбор пары?
5. Промпт: `prompt_library/ocr/ocr_prompt.md` (дефолт) + `ocr_prompt.md` в папке проекта (override) — ок?
6. Layout-хранилище: по файлу на изображение (`images/<name>.layout.json`) или единый `layouts.json` на проект инструмента?
7. Vision-профиль: активный Custom (как у перевода) или отдельный выбор из списка профилей в инструменте?
8. Пакетная OCR (N прямоугольников): подтверждение стоимости по образцу `:9950-9981` переиспользовать?
9. Инструмент: только встроенный (Tools-меню) или с standalone-режимом (как PDF Rescue `__main__`)?
10. CSV wide: заголовки = ID прямоугольников; long: имена колонок для Data Merge (что принимает InDesign)?

---

## Handover (конец O.0)

* Код продукта не изменён. Изменения репозитория: этот отчёт + AGENTS.md (правило проверки процессов Python перед kill) + PROJECT_STATUS (строка O.0). Один docs-only коммит, пуш не выполнялся.
* Артефакты пробы: `E:\Dev\Work_temp\SupervertalerPortable\recon-o0\roundtrip\` (скрипт `probe_o0_roundtrip.py`, `roundtrip_results.json`, `probe_out.txt`, in_*/out_*) — сохранены до вердикта координатора.
* Инцидент: после пробы выполнен `taskkill /F /IM python.exe` (и `java.exe`) по имени образа — убиты чужие процессы пользователя. Ошибка исполнителя; правило предотвращения записано в AGENTS.md (секция GUI-testing). Записи в реестр (QSettings HKCU MTQuickPopup/autostart), как и всегда в offscreen-пробах, машинно-глобальные.
* Стоп. Ожидаю вердикта координатора и промпта следующей стадии; следующих батчей не начинаю.
