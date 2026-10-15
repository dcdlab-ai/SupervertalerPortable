# G5 (урезанный) — АУДИТ FIGURE-КОНТЕКСТА (READ-ONLY) — ОТЧЁТ

Дата: 2026-10-15. Исполнитель: агент-исполнитель. Режим: READ-ONLY (код продукта не тронут).
Коммиты: `87843a42` (9.5f, docs) + docs-коммит аудита (этот отчёт + `audits/g5_*` + `samples/`).
Логи: `docs/refactoring/audits/g5_regex_matrix.log`, `g5_thread_scan.log`, `g5_prompt_capture.log`,
`g5_prompt_capture_results.txt`. Скрипты: `g5_regex_matrix.py`, `g5_thread_scan.py`, `g5_prompt_capture.py`.

---

## §0. База, дрейф, S-clean

- **git status:** `M modules/settings_service.py` — **артефакт CRLF/LF** (AGENTS.md «Git line-ending
  artifacts»): `git diff` пуст, content-hash рабочей копии `08a0d943…` = ожидаемый SHA из ЭТАПа 0 =
  HEAD-содержимое. Продукт-диф (`git diff --stat -- Supervertaler.py modules/ setup.py`) пуст.
- **HEAD:** `cb9d1ea4` (docs-коммиты после кодового `0b9c9ad2`) — соответствует требованию.
- **SHA/строки базы (все совпали, ЭТАП 0):** `Supervertaler.py fe5f706c…/55040`,
  `llm_clients.py 7f2b9ee9…/579`, `settings_service.py 08a0d943…/599`,
  `unified_prompt_manager_qt.py cec2ef68…/6833`, `quicktrans.py 6a6812be…/1635`.
  Фигурный модуль: `figure_context_manager.py d396c761…/347`.
- **S-clean (31 vs 28):** в базе `batch9-5_probe_after_b95-base_clean.log:85` —
  `DATA-TREE (30 entries …)`, т.е. **на базе 30 записей, не 28 и не 31**. «31» в отчёте 9.5 =
  grep по строке `TREE`, захвативший строку-заголовок `DATA-TREE (30 entries…)` (30 записей +
  заголовок = 31). База координатора «28» → 29 → 30 = каталоги `workbench/ai_assistant/attachments/<дата>`
  (20261011/20261013/20261014), создававшиеся прогонами; расхождение возникло **до 9.5** (на 9.4f)
  и уже объяснено в §4 отчёта 9.5 (коммит `cb9d1ea4`). Новых дрейфов в 9.5 нет.
- **Базовые метрики (зафиксированы в `batch9-5_static_after_b95e.log`):** chain 873/0,
  pyflakes 548/126/4, py_compile канон 109/0. Пересчёт в конце (защиты) — идентичен.
- **Коммит 9.5f (`87843a42`, docs-only):** §7 отчёта 9.5 дополнен уточнением Дмитрия о поведении
  («подсказка к переводу, а не перевод надписей на рисунке»); PROJECT_STATUS — «9.5 ПРИНЯТ, G5 в
  работе». Пункты «§7-проверка реальной vision-модели» и «BACKLOG §9.6 (идея режима)» уже внесены
  в `cb9d1ea4` — повтор не потребовался.

---

## §1. Итог (TLDR)

1. Figure-контекст живёт в `modules/figure_context_manager.py` (347 строк) + один гейт в
   `translate_current_segment` + AutoPrompt-гейт в prompt manager + Image Extractor AI-label.
2. Regex-детект покрывает «Figure 1A / fig. 4 / figuur 5», но **пропускает** множественное
   «Figures 1 and 2», «Fig.1A» (без пробела), слитное «Figure1», кириллическое «Рисунок 1», и
   **теряет** вторую ссылку в «Figure 1A and 1B».
3. Имена файлов нормализуются с дефектами: `figure_1a.PNG` → `_1a` (подчёркивание сохраняется и
   никогда не совпадёт с текстовым `1a`); `Figure 1A and 1B.png` → `1aand` (мусор); `1A.png` → None.
4. MD-картинки (`![Image](path)`) в figure-контекст **не попадают**: фикстура содержит 154 строки с
   абсолютными путями `/root/duckling/...` (несуществующими) и хеш-именами без «Figure N».
5. Пакетный перевод (PreTranslationWorker) и QuickTrans **не используют figure-контекст вообще** —
   картинки в пакете не отправляются (цена/время = 0).
6. Потоки чистые: worker-код не трогает виджеты (только сигналы); единственный `QTimer.singleShot`
   из worker-потока — в update-check fallback (48090/48103), кандидате на удаление (P1).
7. Текст промпта с картинкой и без — **байтово идентичен** (G3): роль картинки в тексте объясняет
   только статичная строка системного шаблона `unified_prompt_manager_qt.py:4038`
   («…relevant images may be provided for visual context»), присутствующая **независимо** от того,
   отправлена картинка или нет; она не говорит «не переводи надписи на рисунке».
8. UTF-8 корректен: эмодзи/кириллица доходят на endpoint как правильные UTF-8 байты
   (`c3a9`, `e29895`, `f09f96bc`, `d0bf`), 0 «?» в тексте → «???» в логе LM Studio = артефакт
   отображения лога, не потеря на проводе.
9. Багов, портящих данные, не найдено.

---

## §2. A — Карта figure-контекста

**Модуль `modules/figure_context_manager.py` (347 строк):**
- `FigureContextManager` (34): `figure_context_map: Dict[str, PIL.Image]` (ref→Image, 45),
  `figure_context_folder` (46).
- `detect_figure_references` (49–78): `pattern = r"(?:figure|figuur|fig\.?)\s+(\d+[a-zA-Z]?)"` (69),
  `re.findall(..., re.IGNORECASE)` (70), нормализация через `normalize_figure_ref` (74).
- `load_from_folder` (80–128): расширения `.png/.jpg/.jpeg/.gif/.bmp/.tiff` (109), `Image.open` (116),
  ключ = `normalize_figure_ref(filename)` (118).
- `get_images_for_text` (136–153): refs → `(ref, PIL.Image)` только если ref есть в map (150).
- `has_images`/`get_image_count`/`get_folder_name` (155–167).
- `update_ui_display`/`_update_thumbnails` (169–261) — **tkinter-легаси** (кандидат 8.18).
- `save_state`/`restore_state` (263–296): persist только `folder_path` + `image_count`.
- `normalize_figure_ref` (301–331): `re.search(r'(?:figure|figuur|fig\.?)\s*([\w\d]+(?:[\s\.\-]*[\w\d]+)?)', …)` (324),
  затем `re.sub(r'[\s\.\-]','',ref)` (328).
- `pil_image_to_base64_png` (334–347): PNG, **без ресайза/сжатия**, base64.

**Точки вызова в монолите (`Supervertaler.py`):**
- init: `6288–6289` `self.figure_context = FigureContextManager(self)`.
- UI-загрузка: `9616` `load_context_btn.clicked.connect(self._on_load_image_context_folder)`,
  `9632` `image_context_status_label`, `10285` `_on_load_image_context_folder` (QFileDialog),
  `10310` `_load_image_context_from_path` (общая загрузка + preview-лист 10330–10363),
  `10401` `_on_clear_image_context`.
- автозагрузка после извлечения: `10202` `_load_image_context_from_path(auto_load_folder, "just-extracted")`.
- гейт перевода сегмента: `48924–48956` — `48931 detect_figure_references(segment.source)`,
  `48935 get_images_for_text`, гейт `48939 getattr(client,'supports_vision',False)`,
  `48946–48949` base64-PNG payload, `48950` лог «✅ Including N figure images», `48952` отказ без галки.
- предпросмотр промпта: `38065–38099` (figure_info в composition).
- панель «Project info»: `42994–42999`.
- prompt manager AutoPrompt: `unified_prompt_manager_qt.py:4420–4530` `_collect_autoprompt_images`
  (гейты: чекбокс 4431, images 4440, vision 4458, payload 4489–4492, cost-диалог 4520+);
  `4054–4072` `update_image_context_display`.
- Image Extractor AI-label: `9989–10065` `_ai_label_fn` (prompt 10009–10029 «what label/caption does
  this figure carry», `chat_backend.send_ai_request(..., images=…)` 10036).
- document_analyzer: `modules/document_analyzer.py:247–255` (совет «load_figure_context»).
- формат запроса: `modules/llm_clients.py:521–524` content-parts
  `{"type":"image_url","image_url":{"url":"data:image/png;base64,…"}}`.

**Настройки/хранение:** путь папки — `current_project.prompt_settings['image_context_folder']`
(сохранение `28313–28316`, восстановление `26531–26544`); в `.svproj` лежит **только путь**, картинки
при открытии перечитываются с диска (`restore_state`/`load_from_folder`). В памяти — PIL.Image,
base64 пересобирается на каждый запрос (кэша нет).

**Схема потока:** сегмент → `detect_figure_references` (regex) → `figure_context_map[ref]` (PIL) →
`pil_image_to_base64_png` → content-parts `image_url` → POST `/v1/chat/completions`.

---

## §3. B — Матрица regex (полная таблица в `g5_regex_matrix.log`)

Имена файлов → нормализованный ref (`normalize_figure_ref`):

| Файл | ref | Комментарий |
|---|---|---|
| `Figure 1A.png` | `1a` | ✓ |
| `figure_1a.PNG` | `_1a` | **дефект**: подчёркивание сохраняется → никогда не совпадёт с текстом `1a` |
| `Fig 1A.jpg` | `1a` | ✓ |
| `1A.png` | None | **miss**: нет слова figure/fig |
| `Fig. 3-B.png` | `3b` | ✓ |
| `figure1.png` | `1` | ✓ |
| `Figure 1A and 1B.png` | `1aand` | **мусор** |
| `Рисунок 1.png` | None | **miss** (кириллица) |
| `IMG_001.png` | None | ✓ (не figure) |

Сегменты → refs (`detect_figure_references`):

| Вход | refs | Hit/Miss |
|---|---|---|
| `Figure 1A` | `['1a']` | ✓ |
| `figure 2b` | `['2b']` | ✓ |
| `FIGURE 3` | `['3']` | ✓ |
| `Fig. 1` | `['1']` | ✓ |
| `Fig.1-3` | `[]` | **MISS** (нет пробела после `fig.`) |
| `Figures 1 and 2` | `[]` | **MISS** (множественное) |
| `See Figure 1A…` | `['1a']` | ✓ |
| `(Figure 4)` | `['4']` | ✓ |
| `Figure 10` | `['10']` | ✓ |
| `Figure 1A and 1B` | `['1a']` | **MISS 1B** (вторая ссылка теряется) |
| `Table 1` | `[]` | ✓ (не figure) |
| `Рисунок 1` | `[]` | **MISS** (кириллица) |
| `Figure1` (слитно) | `[]` | **MISS** (нет пробела) |
| `See\u00a0Figure\u00a01A` (nbsp) | `['1a']` | ✓ (`\s` покрывает nbsp) |
| `Fig.1A` | `[]` | **MISS** |
| `Figures 1A and 1B` | `[]` | **MISS** |
| `Figure 1A/B` | `['1a']` | ✓ (B теряется) |
| `Fig. 1A-B` | `['1a']` | ✓ (B теряется) |
| `see fig. 4` / `see fig 4` / `figuur 5` | `['4']/['4']/['5']` | ✓ |

**Сопоставление с файлами:** текстовый `1a` матчится файлам `Figure 1A.png`/`Fig 1A.jpg`; файл
`figure_1a.PNG` (`_1a`) **никогда** не матчится; `1A.png` (None) — никогда.

---

## §4. C — MD-картинки

- **Фикстуры на месте:** `docs/refactoring/samples/Miniature Wargames #520.translation.md` (2143
  строки, 154 строки `![Image](/root/duckling/outputs/…/image_NNNNNN_<sha>.png)`) и `Figure 1A.png`
  (330 KB). Пути фикстуры — абсолютные `/root/duckling/...`, **не существуют** на этой машине;
  имена файлов — хеши, без «Figure N».
- **Импорт .md:** `import_simple_txt` (`29701`, фильтр `*.txt *.md` 29705): каждая строка = один
  сегмент, markdown-синтаксис сохраняется дословно (info 29722–29728). В гриде строка
  `![Image](path)` — обычный текст; `TagHighlighter._highlight_markdown_syntax` подсвечивает
  `[text](url)` как ссылку (`3147–3151`), картинки не рендерит.
- **Что видит перевод/экспорт:** сегмент = строка с текстом `![Image](/root/duckling/…)`;
  `detect_figure_references` на неё → `[]` (нет слова figure/fig) → картинка **не попадает** в
  figure-контекст. Экспорт возвращает ту же markdown-строку.
- **Что нужно, чтобы md-картинка шла как figure-контекст:** парсить `![alt](path)`, разрешать
  относительный путь от папки `.md`, загружать файл (`Image.open`), base64, привязывать к ближайшему
  сегменту (md-картинка обычно отдельной строкой перед/после текста). Оценка: ~40–80 строк в
  `figure_context_manager` + хук импорта; риски: разрешение путей (относительные/абсолютные/URL),
  отсутствующие файлы, привязка «картинка ↔ сегмент», дубли с folder-режимом.

---

## §5. E — Пакетный перевод

- `PreTranslationWorker` (QThread, `5286`): `_translate_with_llm` (`5589`) и
  `_translate_batch_with_llm` (`5650`) **не ссылаются на `figure_context` и не передают `images`** →
  пакетный/пред-перевод картинки не отправляет. `translate_batch` (`49824`) → тот же воркер.
- QuickTrans (`modules/quicktrans.py`) — figure_context не использует.
- `supports_vision=False` в пакете: неприменимо (картинок нет в обоих режимах).
- Цена/время: 0 (изображения в пакет не входят).
- Политика «картинки в пакете»: сегодня — **нет**. Добавление = стоимость картинки на каждый сегмент
  (см. G: ~110 токенов/картинка) + привязка ref→сегмент в батч-промпте. Решение — за Дмитрием (§10 Q4).

---

## §6. F — Потоки и QTimer (полный лог в `g5_thread_scan.log`)

Worker-множество (QThread.run + транзитивные self-методы, threading.Thread/Timer targets,
executor.submit): `PreTranslationWorker` (run + 7 методов), `MTFetchWorker`, `StatisticsWorker`,
`TMXImportThread`, `TMCleanupThread`, `_AutoPromptWorker`, `GlossaryExtractionWorker`,
`ProofreadWorker`, `TMSearchWorker`, + threading-таргеты.

Опасные вызовы **внутри worker-кода** — только 2:
- `Supervertaler.py:48090` `QTimer.singleShot(0, on_ok)` и `48103` `QTimer.singleShot(0, on_err)` —
  внутри `def worker()` потока `threading.Thread` (update-check Python-fallback, `48075–48103`;
  функция — кандидат на удаление P1). Риск: `QTimer` из потока без event loop → callback не доходит
  до главного потока.
- `48069` `progress.setLabelText(...)` в том же потоке — обёрнут в `try/except pass` (48068–48071).

Чистые маршрутизации:
- `PreTranslationWorker.run` (5327–5334 docstring): «работники никогда не трогают виджеты Qt —
  только сигналы»; пишет `segment.target` напрямую (данные, не виджет); `self.log()` потокобезопасен
  (`47317` проверяет main thread → `_log_signal.emit`).
- pynput-хоткей: `54382` `QMetaObject.invokeMethod(self, "_handle_quicktrans_hotkey",
  QueuedConnection)` — корректная маршрутизация в главный поток.
- `threading.Timer` flush (`46126`) → `_flush_tm_save_log_threadsafe` → `self.log` (потокобезопасно).

Всего 53 `QTimer.singleShot` и 656 модальных вызовов — **все в main-thread UI-коде** (не worker).
Исправлений нет (READ-ONLY).

---

## §7. G — Текст промпта с картинкой (логи `g5_prompt_capture.log`, `g5_prompt_capture_results.txt`)

Fake-endpoint 127.0.0.1 + ловушка сети; профиль `supports_vision`; сегмент
`"See Figure 1A — café ☕ «привет» 🖼️ gear engages"`; картинка = фикстура `Figure 1A.png`.

- **G1** vision=True → 1 запрос, 1 `image_url`-part (PASS).
- **G2** vision=False → 1 запрос, 0 image-parts (PASS).
- **G3** текстовая часть с картинкой и без — **байтово идентична** (3228 = 3228, PASS) → роль
  картинки в per-request тексте **не добавляется**.
- **Блок figure-контекста в тексте (дословно, из системного шаблона):**
  `unified_prompt_manager_qt.py:4038` — «If the text refers to figures (e.g., 'Figure 1A'), relevant
  images may be provided for visual context.» Строка **статична и unconditional**: присутствует и
  когда картинка реально отправлена (G1), и когда не отправлена (G2). Она **не** объясняет
  «используй изображение как контекст, не переводи его надписи».
- **G4 UTF-8:** сырые байты запроса (15265) содержат `café`=`c3a9`, `☕`=`e29895`, `«`=`c2ab`,
  `»`=`c2bb`, `привет`=`d0bf`, `🖼`=`f09f96bc` — все OK; `?` в текстовой части = 0 (PASS).
  → «???» в логе LM Studio = артефакт отображения лога, не потеря на проводе.
- **G5** ловушка сети молчала (PASS).

---

## §8. H — Режим «перевести текст на рисунке» (feasibility)

- **Image Extractor** (`modules/image_extractor.py`, 665 строк) умеет: определять **подпись**
  изображения из DOCX-разметки (Caption-стиль/паттерны, `196–224`) и AI-label fallback
  (`Supervertaler.py:9989–10065`: prompt «what label/caption does this figure carry… Reply with ONLY
  the label text», ответ → имя PNG). Сохраняет PNG с именем метки; показывает превью-лист/панель.
- **OCR текста НА рисунке не умеет** — читает только подписи из XML-разметки/паттернов, не пиксели.
- Вывод: PNG-файлы на диске + превью; к сегменту/термбазе не привязан.
- **Варианты:** (а) отдельная кнопка/режим «Извлечь и перевести текст с рисунка» со своим промптом
  («извлеки весь видимый текст и переведи его»), вывод в scratchpad/комментарий сегмента;
  (б) второй режим в существующем AI-label callback; (в) привязка результата к комментарию сегмента.
- Оценка: ~60–120 строк (промпт + UI-кнопка + цель вывода). Риски: качество vision-моделей на OCR,
  длинный текст на картинке, отсутствие OCR-фолбэка без vision-профиля.

---

## §9. Находки

| id | раздел | суть | severity | где |
|---|---|---|---|---|
| G5-F1 | B | regex пропускает «Figures 1 and 2», «Fig.1A», «Figure1», «Рисунок 1» | функция | `figure_context_manager.py:69` |
| G5-F2 | B | `figure_1a.PNG` → `_1a` (подчёркивание) → никогда не совпадёт с текстом `1a` | функция | `figure_context_manager.py:324–328` |
| G5-F3 | B | `Figure 1A and 1B.png` → `1aand` (мусорный ref) | функция | `figure_context_manager.py:324` |
| G5-F4 | B | «Figure 1A and 1B» → только `1a`, вторая ссылка теряется | функция | `figure_context_manager.py:69` |
| G5-F5 | G | строка о роли картинки статична и unconditional (есть и без картинки); не говорит «не переводи надписи» | косметика/функция | `unified_prompt_manager_qt.py:4038` |
| G5-F6 | E | пакет/QuickTrans не отправляют картинки (figure_context отсутствует в воркере) | функция | `Supervertaler.py:5589,5650` |
| G5-F7 | F | `QTimer.singleShot` из worker-потока (update-check fallback) | косметика (P1) | `Supervertaler.py:48090,48103` |
| G5-F8 | C | md-картинки не попадают в figure-контекст | функция | импорт `.md` `29719` + regex `:69` |
| G5-F9 | A | base64 без ресайза/сжатия и без кэша (330 KB фикстуры → ~440 KB base64 на каждый запрос) | косметика | `figure_context_manager.py:334–347` |
| G5-F10 | — | багов, портящих данные, не найдено | — | — |

---

## §10. Решения для Дмитрия (вопросы + рекомендация)

- **Q1 (regex):** расширить детект на множественное «Figures», «Fig.1A» без пробела, слитное
  «Figure1», кириллицу «Рисунок/рис.»? → **Рекомендация: да** (G5.2).
- **Q2 (мульти-ссылки):** извлекать все ссылки в «Figure 1A and 1B» (1a+1b)? → **Рекомендация: да**
  (входит в G5.2).
- **Q3 (роль картинки в промпте):** добавить per-request блок «используй изображение как контекст
  перевода, НЕ переводи текст/надписи на рисунке» — только когда картинка реально отправлена?
  → **Рекомендация: да** (G5.1); текущая статичная строка 4038 вводит в заблуждение (F5).
- **Q4 (пакет):** картинки в пакетном переводе — оставить «нет» / сделать опцией?
  → **Рекомендация: оставить «нет»** (cost на сегмент), опция — позже (G5.4).
- **Q5 (md-картинки):** делать поддержку md-изображений как figure-контекста?
  → **Рекомендация: отложить** до решения по Q1–Q3 (G5.3, риск привязки).
- **Q6 (режим «текст на рисунке»):** отдельный режим со своим промптом?
  → **Рекомендация: да, отдельным батчем** (G5.5, BACKLOG §9.6).

---

## §11. Предложение батчей G5-impl (размер/зависимости; НЕ реализовано)

- **G5.1** — per-request промпт-блок роли картинки (только при отправке image): ~10–20 строк
  (`unified_prompt_manager_qt.py` + гейт `48939`); зависимости: нет.
- **G5.2** — regex-правки (множественное, без-пробела, кириллица, мульти-ссылки, нормализация
  имён с подчёркиванием): ~30–50 строк + матричные тесты; зависимости: нет.
- **G5.3** — md-картинки как figure-контекст (парсинг `![..](path)`, разрешение относительных
  путей, привязка к сегменту): ~40–80 строк; зависимости: Q5.
- **G5.4** — пакетная политика картинок: 0 строк при «нет»; при «опция» — ~30–60 строк в воркере;
  зависимости: Q4.
- **G5.5** — режим «перевести текст на рисунке» (кнопка + свой промпт + вывод): ~60–120 строк;
  зависимости: Q6, vision-профиль.
- **G5.6** — потоковые правки: **0 строк** (F чист; 48090/48103 уходят вместе с P1-удалением).
- **G5.7 (опц.)** — ресайз/сжатие base64 + кэш: ~20 строк; зависимости: нет.

---

## §12. Что не покрыто

- Реальный ответ vision-модели на md-картинки и на режим «текст на рисунке» (только fake-endpoint).
- AutoPrompt e2e с картинкой (покрыты только гейты, не полный запрос).
- Image Extractor AI-label e2e с реальным vision-ответом.
- `.svproj` round-trip figure-папки (restore_state на чужой машине).
- Производительность на больших папках (сотни изображений, отсутствие кэша — F9).

---

## §13. Логи и артефакты

- `docs/refactoring/audits/g5_regex_matrix.py` + `.log` — матрица regex (раздел B).
- `docs/refactoring/audits/g5_thread_scan.py` + `.log` — AST-скан потоков (раздел F).
- `docs/refactoring/audits/g5_prompt_capture.py` + `.log` + `_results.txt` — fake-endpoint, сырые
  байты, UTF-8 (раздел G).
- `docs/refactoring/samples/` — фикстуры (`Miniature Wargames #520.translation.md`, `Figure 1A.png`).
- Stage-директория прогонов: `D:\Temp\SupervertalerPortable\refactoring\g5\`.

---

## Handover

Код продукта не изменён (SHA базы идентичны, продукт-диф пуст). Метрики после аудита: chain 873/0,
pyflakes 548/126/4, py_compile канон 109/0 — совпадают с базой. Коммиты: `87843a42` (9.5f docs) +
docs-коммит аудита. Push не выполнялся (по правилам — только по команде Дмитрия).

Следующие шаги — за Дмитрием: вердикт по G5, ответы Q1–Q6, затем G5-impl (по решениям), 8.18, 8.16,
8.17. Исполнитель останавливается и ждёт вердикта.
