# ОТЧЁТ Batch P2.2 — удаление PDF Rescue целиком

Дата: 2026-11-01. База: `origin/main` после пуша P2.1 (локально HEAD = `d7504dfb`,
продуктовый код идентичен origin/main — проверено `git diff` по продукту).
Основание: решение Дмитрия 2026-10-31 (BATCH_P20_REPORT §4.3, вердикт P2.0 п.2) —
PDF Rescue убрать совсем, за PDF отвечает внешний инструмент.

Правки продукта: **удалён** `modules/pdf_rescue_Qt.py` (1758 строк); из
`Supervertaler.py` удалены пункт меню Tools и обработчик (−33 строки, только
удаления, 0 вставок). Больше продукт не менялся. Docs: новый сэмпл промпта,
правки гейта/смоука, промт, отчёт, PROJECT_STATUS. Пуша нет — ждём вердикта.

## §0. Docs-правка по поручению (P2.2 → P2.3)

По указанию Дмитрия ссылки на «P2.2» по сплиту requirements и lock исправлены на
«P2.3» (включены в коммит P2.2): PROJECT_STATUS.md — 3 места (строка 7 «затем P2.3
(сплит requirements + lock)», строка 15 «это P2.3, после PDF Rescue» и «поштучная
сверка пакетов — в P2.3»); BATCH_P20_REPORT.md — 2 места (конец §5 и §6/D
«поштучное сравнение наборов пакетов»). Ссылки «пересборка D:\Supervertaler_clean —
после P2.2» (удаление PDF Rescue) оставлены как есть — там P2.2 = этот батч.

## §1. Шаг 0 — рекон (без правок)

Grep по продукту без `docs/` (Supervertaler.py, modules/, translations/,
requirements/setup/pyproject). Полные логи: Work_temp
`refactoring/batch-p22/recon_*.txt`. Сводная таблица:

| Где | Что | Решение |
|---|---|---|
| `Supervertaler.py:8222–8224` | QAction «📄 &PDF Rescue...» + connect + addAction в меню Tools | **Удалить** (шаг 2) |
| `Supervertaler.py:9625–9652` | метод `open_pdf_rescue_window` (ленивый импорт `modules.pdf_rescue_Qt`, переиспользование окна) | **Удалить** (шаг 2) |
| `Supervertaler.py:8101, 8886` | комментарии-памятки «…retired in v1.9.467: PDF Rescue and TMX…» | Оставить (исторические, не код; гейт их не ловит — пробел в «PDF Rescue») |
| `modules/pdf_rescue_Qt.py` | сам модуль (1758 строк; fitz:24,409,439; `import anthropic`:79; `import google.generativeai`:91; свои чтения api_keys/workbench-settings в standalone-режиме) | **Удалить** (шаг 2) |
| `modules/help_system.py:168` | константа `TOOL_PDF_RESCUE = "workbench/tools/pdf-rescue/"` — **нигде не используется** (только определение; динамического обхода TOOL_* нет) | Оставить (мёртвое «иное» — 8.18, по промту не трогать) |
| `modules/unified_prompt_manager_qt.py:1533` | комментарий «matches standard tool style: PDF Rescue, TMX Editor» | Оставить (комментарий, не код) |
| `translations/*.xlf` (5 файлов: nl, pl, template, zh_CN, zh_TW) | 2 TU на файл: source «📄 &PDF Rescue...» и «🔍 PDF Rescue – Supervertaler» | Оставить инертными (как осиротевшие ключи настроек; вопрос координатору §9.3) |
| `requirements.txt:22,23,50` / `pyproject.toml:70,71,99–100,137` | `anthropic`, `google-generativeai`, `PyMuPDF` | **Не трогать в P2.2** — сплит/lock requirements = P2.3 (вопрос §9.2: выкинуть ли эти три пакета там же) |
| Ключи настроек `pdf_rescue*` | **не существуют** вне удалённого модуля (рекон 0 попаданий) | Удалять нечего |

**Зависимости других модулей от pdf_rescue_Qt.py: НЕТ.** Единственный импорт во
всём продукте — `Supervertaler.py:9628` (ленивый, внутри удаляемого метода). Общих
хелперов/рендера/списка моделей модуль наружу не отдаёт (проверено grep
`pdf_rescue_Qt` по всем .py — 1 попадание).

**SDK-импорты:** `import anthropic` и `import google.generativeai` существуют только
внутри удалённого модуля (ленивые, guarded). Основной продукт работает с Claude/Gemini
через `modules/llm_clients.LLMClient` (Supervertaler.py:51470+ — это LLMClient с
provider='anthropic', не SDK); упоминания «Anthropic» в llm_clients/llm_pricing —
комментарии и парсинг цен, не импорты. `fitz`/PyMuPDF — только в удалённом модуле.

**Достижимость до правки:** пункт меню был единственным входом в модуль
(connect → `open_pdf_rescue_window` → импорт). Хоткеев на PDF Rescue нет
(grep по хоткеям — 0 попаданий), HelpTopics-ссылок нет (TOOL_PDF_RESCUE не
используется).

## §2. Шаг 1 — сэмпл промпта (до удаления)

`docs/refactoring/samples/pdf_rescue_prompt_for_ocr_tool.md` — дословная копия
промпта для vision-модели с правилами плейсхолдеров (12 строк `default_instructions`
включая плейсхолдеры `[naam]`/`[handtekening]` и т.п.) + условная markdown-строка +
параметры (base64-изображение, Max Tokens 4000). Источник помечен в файле:
`modules/pdf_rescue_Qt.py:291–302` (+ логика 565–573), коммит `119f89a2`.
**Сверено программно: текст блока в сэмпле == строкам модуля байт-в-байт**
(VERBATIM-MATCH, прогон до удаления модуля).

## §3. Шаг 2 — правки

Снапшоты до правки (Work_temp `batch-p22/snapshots/`): полный файл
`pdf_rescue_Qt.py` (рабочая копия == git HEAD, cmp OK), блоки монолита
`mono_menu_block.txt` (8222–8225) и `mono_handler_block.txt` (9625–9652).
sha256 снапшотов: меню `5b474f3b…006c45d`, хендлер `8452daf3…2ba5ccb2`,
модуль `9e0f44e1…0719241d1`-форма рабочей копии `9e0f44e109ea3b6e…`.

1. `Supervertaler.py`: удалены строки меню (3 строки + пустая) и метод
   `open_pdf_rescue_window` (28 строк + примыкающая пустая). py_compile после
   каждой правки — OK. Итог: **33 удаления, 0 вставок** (git diff --stat),
  reachability-проверка после: grep `pdf_rescue|PDFRescue` по монолиту и modules —
   только сам удалённый файл, монолит чист.
2. `modules/pdf_rescue_Qt.py` — `git rm`; удалённый файл байт-в-байт равен снапшоту
   (cmp с `git show HEAD:…` OK).
3. Больше ничего: ключи настроек, help-константа, переводы, requirements — не
   тронуты (§1). Никаких «заодно» правок.

Сверка переноса: line-diff HEAD→рабочая копия — **все opcodes = pure delete**,
удалённые строки совпадают со снапшотами (посимвольно, кроме того какая из двух
смежных пустых строк поглощена в каждом месте — содержимое блоков идентично).

## §4. Статика: было / стало / причина

| Метрика | Было (база P1.8…P2.1) | Стало (P2.2) | Причина |
|---|---|---|---|
| AST chain | 875 / 0 | **874 / 0** | −1 вызов: `triggered.connect(self.open_pdf_rescue_window)` из удалённого пункта меню (базлайн 875/0 перепроверен на worktree HEAD) |
| pyflakes | 536 | **519** | −17 = ровно предупреждения удалённого `pdf_rescue_Qt.py` (список §4.1); мультсет сообщений остальных файлов идентичен (§4.1) |
| py_compile canonical | 108 / 0 | **107 / 0** | −1 продуктовый .py = удалённый модуль (как и ожидалось в промте) |
| py_compile reference | 277 (после коммита P2.1) | **276 / 0** | 277 − 1 модуль; новых .py батч не добавляет (сэмпл — .md, раннер — .sh) |
| headless | 89 / 2 (91 total) | **89 / 1 (90 total)** | известный fail `modules.pdf_rescue_Qt`[fitz] исчез вместе с модулем; остался `setup`[setuptools]; ok = 89 без изменений |
| grep-gate | CLEAN | **CLEAN** + новая секция P2.2: «PDF-Rescue removal OK (0 hits … in 107 product .py files)» | секция добавлена (§5) |
| undefined-name | filedialog 2, messagebox 19, tk 100, ttk 5 | те же | нет |

### §4.1 pyflakes-дифф поэлементно

Прогон одной и той же обёрткой (`pyflakes_root.py`, внешняя библиотека
`qa/env/pyflakes-ext` 4.0.3) по worktree HEAD (baseline) и по правленому дереву
(after): baseline **536**, after **519**. Пофайльно:

* `modules\pdf_rescue_Qt.py` — файл исчез из списка: **−17 предупреждений** (10
  unused-imports PyQt6, 6 redefinition, 1 f-string — полный перечень в логе
  `pyflakes_diff_p22.out`);
* 40 файлов (все modules) — мультсет предупреждений **идентичен** байт-в-байт;
* `Supervertaler.py` — мультсет сообщений **идентичен** (166 строк сдвинуты на −33
  после точки правки; сравнение текстов сообщений с нормализацией внутренних
  ссылок «from line N»: removed=0, added=0).

## §5. grep-gate: новая секция P2.2

`docs/refactoring/audits/batch9-3_grep_gate.py` (правка в рамках батча, как в P1.8):

* новая секция «PDF Rescue removal gate (P2.2)»: обход **всех** продуктовых .py
  (rglob по ROOT, исключены `docs/`, `.git`, `__pycache__`, `.zcode`), паттерны
  `pdf_rescue`, `PDFRescue`, `\bfitz\b` — без word-boundary слева/справа у
  snake-имени (иначе `pdf_rescue_Qt` не ловится: подчёркивание — word-символ;
  найдено на негативном контроле и исправлено до финального прогона);
* любой hit → `GATE-PDF-FAIL`, rc=1; чисто → строка OK с числом проверенных файлов;
* самопроверка на подмене (staged-копия монолита + 8 gate-модулей с инъекцией
  `import fitz` и `import modules.pdf_rescue_Qt`): **обе инъекции пойманы,
  rc=1** (`gate_negctl.out`); на чистом дереве rc=0.

## §6. Набор 16 этапов одним процессом

`bash docs/refactoring/audits/batch-p1b_run_full.sh p22`, лог
`...\batch-p22\suite_p22.log`, все этапы OK:

| Этап | Результат |
|---|---|
| fallback 9.4h, profiles 9.4f, qtchat, statusbar | OK (как в P1-B…P2.1) |
| e2e LLM | verdict **OK**, 5 запросов; канонический агрегат `sha256(json.dumps(requests, sort_keys=True))` = **982e72a247f0a6ac9e2f0a5b9294a082bf6b0fb7e7b38cc190d04f64c2730098** — эталон совпал полностью |
| S-clean / S-upgrade | PROBE OK (2.3s / 2.2s) |
| regress | хэши **byte-identical**: export_simple_txt `5a12501f934a589c`, export_docx `44828d90090f046d`, export_tmx `c413d56372e69dd9`; сегменты 5/5/4 |
| smoke | **40 предметов вместо 41** — пункт `Tools/PDF-Rescue` удалён из списка раннера (§6.1); остальные 40 пунктов прежние, порядок прежний; «SMOKE OK», новых EXC нет |
| termbase | REGRESS-TB OK |
| about | OK (About v1.10.371 как в эталоне) |
| save modern / save legacy | OK (api_keys целы) |
| r9 a / ctrl / rm | OK (профили целы) |

### §6.1 Smoke 41 → 40

Раннер-копия `docs/refactoring/audits/batch-p1b_batch8-13_code_tools_smoke.py`
(используется сюитой; исторический базлайн `batch8-13_code_tools_smoke.py` не
трогался) вела статический список из 41 пункта меню, включая
`("Tools/PDF-Rescue", lambda: win.open_pdf_rescue_window())`. После удаления
хендлера этот пункт падал бы AttributeError — строка удалена из списка с
комментарием P2.2; фактический прогон напечатал `menu items: 40`, все прочие
пункты совпадают с прежним списком (сверено повсеместно по логу), SMOKE OK.

## §7. Проба меню Tools (offscreen)

`probe_tools_menu.py` (Work_temp, не коммитится), изолированный профиль
`batch-p22\iso-menu` + SUPERVERTALER_DATA_ROOT: старт 3,4 с, окно
v1.10.371; меню Tools — **9 пунктов, PDF Rescue отсутствует**: Superlookup (Ctrl+K),
TMX Editor, Statistics (Analyse Against TM), Quick Count, Image Extractor
(Superimage), Scratchpad, Log Window, Token Usage && Costs, Settings (плюс 2
разделителя). Негативный контроль: `_profile` пуст, данные только в
`<iso>\Supervertaler\`. Вердикт **TOOLS-MENU-OK**.

## §8. Гигиена и защита среды

* `SUPERVERTALER_DATA_ROOT` во всех GUI-прогонах (сюита само-сидируется, проба —
  iso-menu); реестр и реальные данные не тронуты; негативный контроль профиля чист.
* Схема БД не менялась (миграционные строки в логах — штатные проверки продукта).
* Дев-рантайм `E:\Dev\python-embed` не изменялся (pyflakes — внешняя библиотека
  `qa/env/pyflakes-ext`, только read-only).
* Worktree HEAD (`head-wt`) создан для базлайнов pyflakes/chain и удалён после
  замеров (`git worktree prune` чист).
* Свип процессов после прогонов: 0 выживших python.exe/java.exe прогона
  (командные строки проверены, посторонние не трогались).

## §9. Вопросы координатору

1. **Требуют ли удаления** инертные остатки: константа `TOOL_PDF_RESCUE`
   (help_system.py:168, ноль использований), 2×5 переводных TU «PDF Rescue» в
   5 .xlf, комментарии Supervertaler.py:8101/8886 и unified_prompt_manager_qt:1533?
   Рекомендация: по правилу промта оставлено; кандидат — 8.18 (константа,
   комментарии) либо правка .xlf отдельным решением (они регенерируются
   pylupdate6).
2. **Пакеты в requirements/pyproject**: `anthropic`, `google-generativeai`,
   `PyMuPDF` теперь не импортируются продуктом нигде. Убрать ли их в P2.3
   (сплит/lock) или отдельным микробатчем? В дистрибутивном рантайме PyMuPDF
   и так отсутствовал (P2.0 §4.3), anthropic/google не ставились (guarded).
3. **Обновление D:\Supervertaler_clean**: по решению §13 P2.1 — одна пересборка
   после P2.2. Два пути: (а) пересборка упаковщиком
   `make_portable_zip.bat` + распаковка (чисто, но медленнее) или (б) точечная
   правка существующей сборки — скопировать изменённый `Supervertaler.py` в
   `D:\Supervertaler_clean\SupervertalerPortable\` и **удалить там**
   `SupervertalerPortable\modules\pdf_rescue_Qt.py` (других продуктовых изменений
   нет). Рекомендую (б) до следующей пересборки.

## §10. Ручные тесты Дмитрия

Выполнять после обновления `D:\Supervertaler_clean` (§9.3) — оба теста на тестовой
сборке. Настраивать ничего не нужно.

### T-P2.2a — меню Tools без PDF Rescue (обязательный)

1. **Цель:** убедиться, что пункт «PDF Rescue» исчез из меню Tools, а остальные
   пункты на месте.
2. **Шаги:**
   1. Запустить `start.bat` в корне `D:\Supervertaler_clean`, дождаться окна.
   2. Открыть меню **Tools** в строке меню.
3. **Ожидаемый результат:** в меню **9 пунктов** (и две разделительные линии):
   Superlookup (Ctrl+K), TMX Editor, Statistics (Analyse Against TM), Quick Count
   (pick files, no project), Image Extractor (Superimage), Scratchpad, Log Window,
   Token Usage & Costs, Settings. Пункта «📄 PDF Rescue...» **нет** — он был
   первым сверху.
4. **Провал:** пункт PDF Rescue на месте; или не хватает кого-то из девяти
   перечисленных; или меню Tools не открывается.

### T-P2.2b — обычная работа (обязательный)

1. **Цель:** убедиться, что удаление PDF Rescue не задело обычную работу.
2. **Шаги:** открыть проект (или создать новый из текстового файла), перевести
   один сегмент, сохранить проект, закрыть программу.
3. **Ожидаемый результат:** всё как обычно — сегмент переводится, проект
   сохраняется, программа закрывается без ошибок в консоли.
4. **Провал:** ошибка при старте/переводе/сохранении, в консоли
   `ModuleNotFoundError` (например, упоминание `pdf_rescue` или `fitz`).

## §11. sha256 (форма: две колонки — «до» и «стало», два вида внутри каждой)

«Блоб (LF)» = содержимое, как ляжет в git (`core.autocrlf=true`); «рабочая копия» =
файл на диске. `Supervertaler.py` — CRLF в рабочей копии, остальные LF (копия = блобу).
Замер до коммита. Правило (вердикт P2.2, Дмитрий 2026-11-01): **во всех будущих
отчётах для каждого изменённого файла пишутся ОБЕ колонки — «до» и «стало»**;
правило внесено в AGENTS.md («Refactoring batch validation practices»).

| Файл | блоб (LF) до | раб. копия до | блоб (LF) стало | раб. копия стало |
|---|---|---|---|---|
| `Supervertaler.py` (изменён) | `13aeaef58e283c0cc7f9ea46f3c0bf1fb4dca036850726f70ac083580d6d86a2` (проверено: `git show :Supervertaler.py`, HEAD перед коммитом) | `d89b1cc1…` (CRLF; из отчёта P1.7 — продукт после P1.7 не менялся; LF-снимок HEAD подтверждает блоб-форму) | `72db449a1d36939de4ebaa96563baf8003157af27a9b51d8a287c7dbb27984d3` | `d493b499e0ecad29fba1c55c4be06f25672cc20a8248ff2bd88b688a86b95d40` (CRLF) |
| `docs/refactoring/samples/pdf_rescue_prompt_for_ocr_tool.md` (новый) | — | — | `8a2b3b275934d89acab60874fb1c0d20f6fa6956644c955fba59573cc764e139` | = блобу (LF) |
| `docs/refactoring/audits/batch9-3_grep_gate.py` (изменён) | `caadaaec1c8a639d95fd2c3c57d9e7686caa36054f6ff9eac4038a9bec3fc26a` | = блобу (LF) | `2ec8b8aa37f6ec97cd15b4f6fbf259c546541b53d88dab4d8968f58bdeccb7d4` | = блобу (LF) |
| `docs/refactoring/audits/batch-p1b_batch8-13_code_tools_smoke.py` (изменён) | `1a2bc270ba1ac6888c2e615619dc42fa91e5a7b398097ffc49295317ab1b5d7a` | = блобу (LF) | `40ef3fceb49d235e3dbcd1ddd99cf2a8340ddc2c7c0c31a50ca90cccdcf805f0` | = блобу (LF) |
| `docs/refactoring/audits/batch-p22_static_run.sh` (новый) | — | — | `a64bebfac3ed57c9a1a2c49337bd1461e7f06e9b7da140dc2b2075cfc65e5641` | = блобу (LF) |
| `modules/pdf_rescue_Qt.py` | (в HEAD) `9e0f44e109ea3b6ed38a54d467a091953a32bfc105e60a2dee085120719241d1` | = блобу (LF) | **удалён** | — |

## §12. Артефакты

Репозиторий (коммит батча): `Supervertaler.py`, удалённый
`modules/pdf_rescue_Qt.py`, `docs/refactoring/samples/pdf_rescue_prompt_for_ocr_tool.md`,
`docs/refactoring/audits/batch9-3_grep_gate.py`,
`docs/refactoring/audits/batch-p1b_batch8-13_code_tools_smoke.py`,
`docs/refactoring/audits/batch-p22_static_run.sh`,
`docs/refactoring/prompts/Promt - BATCH P2.2.txt`, этот отчёт, PROJECT_STATUS.md.

Work_temp `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p22\` (удерживается
до вердикта): `snapshots/` (снимки до правки + sha256), `recon_*.txt` (рекон),
`pyflakes_full_{baseline,after}.txt`, `pyflakes_root.py`, `static_run_p22.log`,
`gate_negctl.out`, `gate_clean.out`, `suite_p22.log`, `probe_menu.{out,err}`,
`probe_tools_menu.py`, `iso-menu\`.

## §13. Стоп

Следующий шаг — только вердикт координатора. Пуш не выполнялся.

## §14. ВЕРДИКТ координатора: GO; ручные тесты подтверждены; ответы на §9 (Дмитрий, 2026-11-01)

**T-P2.2a и T-P2.2b подтверждены Дмитрием** на `D:\Supervertaler_clean`
(точечное обновление: новый `Supervertaler.py` + удалённый там
`modules\pdf_rescue_Qt.py`). Вердикт: **GO, пуш разрешён** (ожидается `d7504dfb` +
коммиты P2.2; дифф по продукту впервые не пустой — ожидается ровно
`Supervertaler.py` −33/0 и `modules/pdf_rescue_Qt.py` удалён).

**Ответы на вопросы §9:**
1. Инертные остатки: константа `TOOL_PDF_RESCUE` и комментарии (3 места) — **в 8.18**;
   строки «PDF Rescue» в 5 .xlf — **оставить** (регенерируются, не мешают).
2. Пакеты `anthropic`, `google-generativeai`, `PyMuPDF` — **убрать в P2.3**,
   отдельный микробатч не нужен; requirements.txt и pyproject.toml править
   **синхронно** (pyproject.toml строки 70, 71, 99–100, 137); версионную строку
   pyproject.toml не трогать (её читает Supervertaler.py:57).
3. Обновление `D:\Supervertaler_clean` точечной заменой **устраивает** (тесты
   пройдены); полная пересборка упаковщиком — один раз после P2.3.

**Дополнение метода (§11):** в отчётах для каждого изменённого файла всегда
пишутся обе колонки sha256 — «до» и «стало»; правило внесено в AGENTS.md
(для Supervertaler.py в §11: блоб до `13aeaef5…`, рабочая копия до `d89b1cc1…` —
из отчёта P1.7).
