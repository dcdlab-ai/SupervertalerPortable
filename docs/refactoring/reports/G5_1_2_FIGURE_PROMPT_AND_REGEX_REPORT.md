# ОТЧЁТ Batch G5.1 + G5.2 — роль картинки в промпте + расширение детекта ссылок на рисунки

Дата: 2026-10-15. Промпт: «BATCH G5.1 + G5.2 — РОЛЬ КАРТИНКИ В ПРОМПТЕ + РАСШИРЕНИЕ ДЕТЕКТА ССЫЛОК НА РИСУНКИ» (координатор — Дмитрий). Роль: исполнитель. Пуш не выполнялся (по промпту).

База: HEAD `c2ab7f46`. SHA/строки шести файлов совпали с промптом: `Supervertaler.py` fe5f706c…/55040, `llm_clients.py` 7f2b9ee9…/579, `settings_service.py` 08a0d943…/599, `unified_prompt_manager_qt.py` cec2ef68…/6833, `quicktrans.py` 6a6812be…/1635, `figure_context_manager.py` d396c761…/347. Снимки «до» — `D:\Temp\SupervertalerPortable\refactoring\batch-g5-12\snap\*.before`.

## §1. Коммиты

| # | SHA | Содержание | Файлы |
|---|-----|-----------|-------|
| 1 | `8a490f94` | G5.1a: блок FIGURE CONTEXT кодом в гейте (только при реально отправленной картинке) + транзиент-правило S-clean + g5_12_static.py | Supervertaler.py (55040→55069, SHA 3eb4ecbd…), batch8-15_probe_window.py, g5_12_static.py |
| 2 | `1d80c8c1` | G5.1b: удалить статичную строку :4038 из системного шаблона | unified_prompt_manager_qt.py (6833→6831, SHA d2c45b29…) |
| 3 | `45cfa549` | G5.1c: пометка «в пакетном переводе изображения не используются» в tooltip кнопки загрузки папки | Supervertaler.py (55069→55071, SHA 23ff34b2…) |
| 4 | `f82c5a9e` | G5.2: regex + normalize имён + MAX_FIGURE_IMAGES_PER_REQUEST=4 + матрица B after | figure_context_manager.py (347→381, SHA 2a9b1ef4…), Supervertaler.py (55071→55080, SHA d7e18689…), g5_2_regex_matrix_after.py |
| 5 | `38b64910` | Спец-проба probe_g5_12.py (P1–P11, 29/29 PASS) + логи обоймы g5-12_* | audits (97 файлов) |

Итоговые строки/SHA продукта: `Supervertaler.py` **55080** (SHA `367d8e50…`, CRLF 55080/0 LF-only), `unified_prompt_manager_qt.py` **6831** (`d2c45b29…`, CRLF 6831/0), `figure_context_manager.py` **381** (`2a9b1ef4…`, LF 381/0 — файл штатно LF, как на базе).

## §2. Рекон (RECON_G5_12.md, кратко)

- Текст запроса: `build_final_prompt` (mode="single"), финальный разделитель `**YOUR TRANSLATION …` — всегда последняя строка (`unified_prompt_manager_qt.py:4163`). Блок вставлен по той же схеме, что surrounding-context: `replace("**YOUR TRANSLATION", блок + "\n\n**YOUR TRANSLATION")`, fallback `+=` — финальная инструкция остаётся последней строкой (проверено пробой P1).
- **Шаблон :4038 — константа в коде** (`_get_default_system_template`), не диск: `system_prompts_layer1.json` пишется только при явном Save в редакторе; в репо/тестовой сборке/production файла нет. Правка кода = правка дефолта; пользовательские сохранённые копии сохраняют старую строку (штатное поведение редактируемого шаблона, Reset возвращает дефолт). STOP не сработал.
- STOP-условия не сработали: точка вставки не требует перестройки сборки промпта; сигнатуры `detect_figure_references`/`get_images_for_text` сохранены (List[str] / List[Tuple[str, Image]]); `llm_clients.py` не менялся (формат content-parts подтверждён реконом и пробой P1 — всё корректно).
- AutoPrompt (`_collect_autoprompt_images`, chat-путь) и Image Extractor AI-label (`_build_image_extract_ai_callback`, собственный prompt+system_prompt) `build_final_prompt` не используют → блок и удаление :4038 их не касаются (проверено статически + пробой P6).
- Пакетные пути (worker ×3, Match Panel) картинок не шлют → блок не вставится (проба P9).

## §3. Изменения по коммитам

**G5.1a (`8a490f94`, Supervertaler.py, гейт translate_current_segment):** после успешного формирования `images` (vision-гейт пройден, файлы найдены) в `custom_prompt` вставляется блок:
`FIGURE CONTEXT: The following image(s) are attached to this request as visual context for the figure reference(s) in the source segment: Image 1 = Figure 1A; Image 2 = Figure 1B. Use them only to resolve ambiguity and choose terminology. Do NOT translate, transcribe, describe or comment on any text shown in the images. Return only the translation of the source segment, with no numbering or labels.`
Подписи строятся по фактически отправленным картинкам в их порядке (`enumerate(images, 1)`, ref '1a' → «Figure 1A»). Блок вставляется ТОЛЬКО при ≥1 реально отправленной картинке. Плюс: транзиент-правило S-clean в `batch8-15_probe_window.py` (исключает `workbench/ai_assistant/attachments/<дата>` + `index.json`, счётчик DATA-TREE-STATIC) и консолидированный статический раннер `g5_12_static.py`.

**G5.1b (`1d80c8c1`, unified_prompt_manager_qt.py):** из `_get_default_system_template` удалены строка «If the text refers to figures (e.g., 'Figure 1A'), relevant images may be provided for visual context.» и пустая строка после неё (была :4038). Роль картинки в промпте теперь описывает только код (G5.1a).

**G5.1c (`45cfa549`, Supervertaler.py, create_reference_images_tab):** tooltip кнопки «📁 Load Folder» обёрнут в `self.tr(...)` и дополнен: «Note: images are not used in batch translation — figure context applies to interactive (current-segment) translation only.» (вердикт Q4). Метод не входит в AST-chain — chain не изменился (подтверждено обоймой).

**G5.2 (`f82c5a9e`):**
- `figure_context_manager.py`: новый `_FIGURE_PATTERN` — keywords `figures|figure|figuur|figs|fig|рисунки|рисунков|рисунка|рисунок|рис` (кириллица добавлена, выражение осталось читаемым — вердикт Q1 «низкий приоритет» выполнен), lookbehind `(?<!\w)` (границы слов), опциональная точка, обязательная цифра `(\d{1,3}[a-zA-Z]?)(?!\d)`, цепочка только через запятую/`and`/`&`/`or` (допускается двойной разделитель «, and»); дефис/en-dash и «/» НЕ разделители, диапазоны не раскрываются; порядок первого появления, без дублей. Негативы молчат: «Figure», «Figure.», «figures of speech», «configuration», «Config. 3», «Table 1», «prefigure 2», «Fig», «нарисуй 2»; «Figure 1 and 2018» → ['1'] (токены цепочки ≤3 цифр с lookahead — годы не ссылки).
- `normalize_figure_ref` (имена файлов): сепараторы `[_\s.\-]*` между словом и числом (`figure_1a.png` → '1a'), берётся только первый числовой токен (`Figure 1A and 1B.png` → '1a', без «1aand»; множественные имена beyond first — известное ограничение); `1A.png` без слова figure → None (без изменений).
- `MAX_FIGURE_IMAGES_PER_REQUEST = 4` — константа модуля (Q2); импорт в гейте монолита; при переполнении берутся первые 4 по порядку появления и пишется лог «Figure context: N images found, only first 4 sent» (не молча).
- Ссылки без файла по-прежнему молча игнорируются (get_images_for_text без изменений).
- md-вставка: поведение сохранено — `![Image](..\Figure 2.jpg)` находит ref '2' (косвенный путь через regex по тексту, не «чиним»).
- Матрица B «after» — новый файл `audits/g5_2_regex_matrix_after.py` (старый лог `g5_regex_matrix.log` не тронут), лог `g5-12_matrix_after_g52.log`.

## §4. Обойма (метрики до/после на каждом коммите)

Все четыре прогона идентичны базе; логи в `docs/refactoring/audits/g5-12_*` (pre-tag: base/g512a/g512b/g512c/g52a).

| Метрика | База | g512a | g512b | g512c | g52a |
|---|---|---|---|---|---|
| AST-chain | 873/0 | 873/0 | 873/0 | 873/0 | 873/0 |
| pyflakes warnings | 548 | 548 | 548 | 548 | 548 |
| undefined lines/names | 126/4 (tmx_editor) | 126/4 | 126/4 | 126/4 | 126/4 |
| py_compile канон (вне docs/) | 109/0 | 109/0 | 109/0 | 109/0 | 109/0 |
| py_compile справочный | 195/0 | 196/0* | 196/0 | 196/0 | 196/0 |
| headless imports | 90/2 (setuptools, fitz) | 90/2 | 90/2 | 90/2 | 90/2 |
| grep-гейт | CLEAN | CLEAN | CLEAN | CLEAN | CLEAN |
| S-clean (с динамикой / статич.) | 31/23 | 31/23 | 31/23 | 31/23 | 31/23 |
| S-upgrade HASH-DIFF | пустой | пустой | пустой | пустой | пустой |
| regress 3 хеша | 5a12501f/44828d90/c413d563 | = | = | = | = |
| Tools-smoke | 42 | 42 | 42 | 42 | 42 |
| TB / About / save modern+legacy / r9 a+ctrl+rm | OK | OK | OK | OK | OK |
| e2e / qtchat / statusbar / profiles / fallback | DONE | DONE | DONE | DONE | DONE |

\* +1 к справочному — новый аудит-скрипт батча (`g5_2_regex_matrix_after.py`); канон (вне docs/) не изменился. S-clean: база 31 = 23 статич. + 8 транзиентных (attachments/<дата> + index.json, новое правило); TREE-строк 33 (31 записей + 2 строки счётчиков).

Спец-проба `probe_g5_12.py` (fake-endpoint 127.0.0.1 + ловушка сети + socket-guard): **29 PASS / 0 FAIL** — P1 (блок+картинка+labels+delimiter-последняя-строка), P2 (vision=False → 0 картинок, блока нет), P3 (сегмент без ссылки), P4 (2 ссылки → 2 картинки, labels по порядку), P5 (сохранённый layer1.json со СТАРОЙ строкой: строка сохранена дословно, блок ровно 1 раз, файл переводом не трогается), P6 (Image Extractor AI-label prompt без блока), P7 (preview: info-строка есть, кодового блока нет — ожидаемое расхождение, §9), P8 (5 ссылок → 4 картинки + лог переполнения + labels Image 1..4), P9 (пакетный воркер → 0 картинок, блока нет), P10 (md-вставка → ref '2'), P11 (trap молчит, emoji/не-ASCII UTF-8 байтами, '?'=0) + статич. проверка «текста блока нет в prompt manager / figure module».

Замечание по харнессу (не регрессия): в прогоне g512a процесс regress завершился полным выводом (хеши совпали с базой), но завис на `os._exit(0)`; оставшиеся стадии догнаны `run_tail.sh`. Для g512b/g512c/g52a в runner добавлен per-stage `timeout 480` — все стадии отработали штатно.

## §5. Пакет для тестовой сборки

Три файла (копировать в `D:\SupervertalerPortable_test\SupervertalerPortable\`):
* `Supervertaler.py` — 55080 строк, SHA `367d8e50…` (был `fe5f706c…`);
* `modules/unified_prompt_manager_qt.py` — 6831 строка, SHA `d2c45b29…` (был `cec2ef68…`);
* `modules/figure_context_manager.py` — 381 строка, SHA `2a9b1ef4…` (был `d396c761…`).

Удалять из пакета нечего (ничего не удалялось). Пересборка тестовой сборки — отдельное решение Дмитрия (по AGENTS.md батчи её не обновляют).

## §6. Ручные сценарии (для тестовой сборки)

* **T-G5.1** — сегмент «See Figure 1A …», профиль с галкой vision, папка с `Figure 1A.png` загружена → перевод сегмента; в логе «✅ Including 1 figure images: 1a»; модель использует картинку как подсказку (не переводит надписи).
* **T-G5.2** — тот же сегмент, галка vision снята → картинок нет, в промпте НЕТ блока FIGURE CONTEXT (проверить через лог/перехват), в логе warning «doesn't support vision».
* **T-G5.3** — сегмент без ссылки на рисунок, vision включён → картинок нет, блока нет.
* **T-G5.4** — «See Figure 1A and Figure 2 …», обе картинки в папке → 2 картинки, в промпте «Image 1 = Figure 1A; Image 2 = Figure 2».
* **T-G5.5** — «See Figures 1, 2, 3, 4 and 5» при 5 загруженных картинках → отправляются первые 4, в логе «Figure context: 5 images found, only first 4 sent».
* **T-G5.6** — «Fig.1-3» / «Figure 1A-B» / «Figure 1A/B» → отправляется только картинка 1 (диапазоны не раскрываются).
* **T-G5.7** — «Table 1», «configuration», «Config. 3», «figures of speech» → картинок нет, блок не появляется.
* **T-G5.8** — кириллица: «Рисунок 1 показывает узел» + файл `Рисунок 1.png` → картинка подхватывается.
* **T-G5.9** — tooltip кнопки «📁 Load Folder» содержит строку «images are not used in batch translation».
* **T-G5.10** — md-сегмент с `![Image](..\Figure 2.jpg)` + загруженный `Figure 2.jpg` → картинка отправляется (косвенный путь сохранён).

## §7. Чем не покрыто

* Реальное поведение vision-модели (что модель делает с картинкой при новом блоке) — проверяется только на материале (T-G5.1… на тестовой сборке + llama.cpp по методике §7 отчёта 9.5); fake-endpoint проверяет формат запроса, не ответ модели.
* Поведение на тестовой сборке (frozen 960be5d8) — после пересборки пакета Дмитрием (§5).
* Пользовательские сохранённые копии системного шаблона (layer1.json) со старой строкой — сохранены намеренно (P5); массовая миграция не делалась (политика не требовалась).

## §8. Вопросы (решения за координатором)

1. **Preview-расхождение:** «Combined Prompt Preview» показывает figure_info-строку («🖼️ N image(s) will be sent…»), но НЕ показывает кодовый блок FIGURE CONTEXT (он вставляется после build_final_prompt). Оставить как есть (источник информации в preview — info-строка) или добавить в preview имитацию блока? (Проба P7 зафиксировала текущее поведение.)
2. **Цепочка «Figure 1A, 1B» (запятая без «and»):** текущая реализация требует разделителя запятой/and/&/or после первого токена — «Figure 1A, 1B» даёт ['1a','1b'] (запятая работает). Проверить на материале, не порождает ли ложных ссылок конструкция вида «…, 2018» (сейчас годы отсекаются 3-значным лимитом токена).
3. **Лимит 4 — считать картинок или ссылки?** Сейчас лимит применяется к найденным КАРТИНКАМ (файлам), ссылки без файла не тратят квоту. Альтернатива — лимит на список ссылок. Текущий вариант соответствует вердикту Q2 («лимит картинок»).
4. **P5-кейс:** нужна ли когда-нибудь миграция пользовательских layer1.json (удаление старой строки из сохранённых копий)? Сейчас — нет (Reset в редакторе возвращает новый дефолт).

## §9. Находки вне рамок батча

* **attachments/<дата> создаётся при каждом запуске** (в т.ч. offscreen-прогонах): в S-clean база с динамикой 31 (23 статич. + транзиент). Кандидат P1 (чистота portable-сборки) — в BACKLOG §4.
* **CRLF/LF-гигиена:** `modules/settings_service.py` стабильно помечен «M» (CRLF/LF-артефакт, content-hash 08a0d943 = HEAD); `figure_context_manager.py` штатно LF. Кандидат 8.17 (нормализация line endings) — в BACKLOG §10.
* В гейте монолита осталась мёртвая gemini-ветка (`if provider == "gemini"` при единственном провайдере) — не тронута (8.18, как отмечено в 9.5c).
* Preview-расхождение (см. §8 Q1) — зафиксировано как ожидаемое.

## §10. Матрица B «after» (полный лог)

Файл: `docs/refactoring/audits/g5_2_regex_matrix_after.py`; лог: `docs/refactoring/audits/g5-12_matrix_after_g52.log`.

```
=== FILENAME -> normalized ref (normalize_figure_ref) ===
  'Figure 1A.png'                -> '1a'
  'figure_1a.PNG'                -> '1a'
  'Fig 1A.jpg'                   -> '1a'
  '1A.png'                       -> None
  'Figure 1.png'                 -> '1'
  'fig3b.png'                    -> '3b'
  'Fig. 3-B.png'                 -> '3b'
  'figure1.png'                  -> '1'
  'Figure 10.png'                -> '10'
  'Fig.1.png'                    -> '1'
  'figure_10c.tiff'              -> '10c'
  'IMG_001.png'                  -> None
  'Figure 1A and 1B.png'         -> '1a'
  'Рисунок 1.png'                -> '1'
  'figure_1a_and_1b.png'         -> '1a'
  'Figure 1A-B.png'              -> '1a'
  'fig_2.jpg'                    -> '2'
  'Рис. 3.png'                   -> '3'
  'рисунки 2.png'                -> '2'
  'Figure1.png'                  -> '1'

=== SEGMENT -> detected refs (detect_figure_references) ===
  'As shown in Figure 1A, the gear engages.'              -> ['1a']
  'see figure 2b for details'                             -> ['2b']
  'FIGURE 3 shows the assembly'                           -> ['3']
  'See Fig. 1 for the diagram'                            -> ['1']
  'See Fig.1-3 for the diagrams'                          -> ['1']
  'See Figures 1 and 2 for details'                       -> ['1', '2']
  'See Figure 1A and 1B together'                         -> ['1a', '1b']
  '(Figure 4) is referenced here'                         -> ['4']
  'Refer to Figure 10 below'                              -> ['10']
  'Table 1 lists the values'                              -> []
  'Рисунок 1 показывает узел'                             -> ['1']
  'Figure1 is glued'                                      -> ['1']
  'See Figure 1A here'                                    -> ['1a']
  'See Figure 1A'                                         -> ['1a']
  'See Figure 1A and 1B'                                  -> ['1a', '1b']
  'Figures 1 and 2 are shown'                             -> ['1', '2']
  'see fig. 4'                                            -> ['4']
  'see fig 4'                                             -> ['4']
  'figuur 5 in the manual'                                -> ['5']
  'Figure 1A, Figure 2B and Figure 3C'                    -> ['1a', '2b', '3c']
  'See Fig 1A'                                            -> ['1a']
  'See Fig.1A'                                            -> ['1a']
  'figure 1a'                                             -> ['1a']
  'Figure 1A (see Fig. 2B)'                               -> ['1a', '2b']
  'no figure reference here'                              -> []
  'Fig. 1A and Fig. 2B'                                   -> ['1a', '2b']
  'Figures 1, 2 and 3'                                    -> ['1', '2', '3']
  'Figures 1, 2, and 3'                                   -> ['1', '2', '3']
  'See figure 1A, figure 2B'                              -> ['1a', '2b']
  'Figure 1A/B'                                           -> ['1a']
  'Fig. 1A-B'                                             -> ['1a']
  'Figure 1A-B'                                           -> ['1a']
  'Figures 1A-1B'                                         -> ['1a']
  'Fig.1A'                                                -> ['1a']
  'Fig.1A-B'                                              -> ['1a']
  'See Figure 1A and Figure 1B'                           -> ['1a', '1b']
  'Figures 1A and 1B'                                     -> ['1a', '1b']
  'Figure 1A and 1B'                                      -> ['1a', '1b']
  'see figure 1a and 1b'                                  -> ['1a', '1b']
  'Figure 1A and 1B (Figures 2A and 2B)'                  -> ['1a', '1b', '2a', '2b']
  'See Fig. 1A'                                           -> ['1a']
  'See Fig.1A and 1B'                                     -> ['1a', '1b']
  'Fig. 1A and 1B'                                        -> ['1a', '1b']
  'Figure 1A and 1B and 2C'                               -> ['1a', '1b', '2c']
  'Figures 1A and 1B and 2C'                              -> ['1a', '1b', '2c']
  'See Figure 1A and 1B and 2C and 3D'                    -> ['1a', '1b', '2c', '3d']
  'Figure 1A and 1B and 2C and 3D and 4E'                 -> ['1a', '1b', '2c', '3d', '4e']
  'Fig. 1A and 1B and 2C and 3D'                          -> ['1a', '1b', '2c', '3d']
  'Figure'                                                -> []
  'Figure.'                                               -> []
  'figures of speech'                                     -> []
  'configuration'                                         -> []
  'Config. 3'                                             -> []
  'Table 1'                                               -> []
  'prefigure 2'                                           -> []
  'Fig'                                                   -> []
  'Figure 1 and 2018'                                     -> ['1']
  'Fig.1A and 1B'                                         -> ['1a', '1b']
  'See\xa0Figure\xa01A'                                   -> ['1a']
  'Figure\xa01A\xa0and\xa01B'                             -> ['1a', '1b']
  'рис. 3 показан'                                        -> ['3']
  'нарисуй 2'                                             -> []
  '![Image](..\\Figure 2.jpg)'                            -> ['2']
```

(CROSS-секция лога — в `g5-12_matrix_after_g52.log`; ключевые совпадения: «Figures 1, 2 and 3» → файлы Figure1.png/рисунки 2.png/Рис. 3.png; «Figure 1 and 2018» → только Figure1.png; md-вставка → рисунки 2.png.)

## §11. Handover

* G5.1 + G5.2 выполнены, 5 коммитов (см. §1), пуш не выполнялся.
* Следующий шаг по порядку вердикта Дмитрия (§11 отчёта G5): **тест на реальном материале** (T-G5.1…T-G5.10 на тестовой сборке после пересборки пакета §5), затем G5.3 (md-парсинг `![..](..)`) или G5.5 (режим «текст на рисунке») по приоритету, G5.4 в конец. Старт каждого — только по команде Дмитрия и его промпту.
* BACKLOG (предложено внести): §4 P1 — создание `attachments/<дата>` при каждом запуске; §10 8.17 — CRLF/LF-гигиена (`settings_service.py` «M», `figure_context_manager.py` LF).
