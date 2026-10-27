# ОТЧЁТ BATCH P1-B — P1.3 корень сборки как единственный источник путей (+ ШАГ 0: фикстуры/runner)

**Батч:** BATCH P1-B (промпт Дмитрия 2026-10-27, «BATCH P1-B — корень сборки как единственный источник путей (P1.3) + инфраструктурный шаг 0»).
**База:** `32d52974` (вердикт P1-A GO). **Отчёт:** `docs/refactoring/reports/BATCH_P1B_REPORT.md`.
**Коммиты:** ШАГ 0 `b5b8bdf4` (инфра) → P1.3a `ff7fba9b` (portable_paths) → P1.3b `5137f94e` (монолит) → P1.3c `24e3801d` (зеркала) → P1.3d `b2e0e523` (шов + AGENTS.md) → fix `0a0312b5` (копии проб из batch-p1a-источников) → docs (этот коммит).
**Пуш не выполнялся. Стоп до вердикта координатора.**
**Реальные данные пользователя (~\Supervertaler, %APPDATA%, реестр), dev-рантайм — не тронуты.**

---

## 1. Итог

Единственный источник путей данных — корень сборки, новый модуль `modules/portable_paths.py` (78 строк, только stdlib, чистые функции без записей на диск):

- `build_root()` — env `SUPERVERTALER_DATA_ROOT` (только абсолютный путь; относительный → понятный `ValueError`), иначе `parents[2]` файла модуля = каталог, в котором лежит каталог кода (`<root>\SupervertalerPortable\modules\portable_paths.py` → `<root>`).
- `data_root()` — приоритет зафиксирован: **env > dev-флаг `.supervertaler.local` (→ `<репо>\user_data_private`) > `<корень сборки>\Supervertaler`** (QP1.3/QP1.4).
- `state_root()` = `build_root()` — задел под P1-C/P1.6 (служебные файлы в корне, QSettings-фолбэк `<root>\Supervertaler\qsettings\`).

Монолит: `get_user_data_path()` теперь тонкий делегат в `portable_paths.data_root()`; вся система «файл-указатель + ~/Supervertaler + автовосстановление + диалог первого запуска» удалена. Создание структуры первого запуска осталось в `__init__` (как было, `mkdir` в :6314-старом — поведение «первый запуск создаёт структуру» сохранено, записи указателя больше нет).

Зеркала без импорта монолита переведены на `data_root()`: `ui_scale.py` (указатель удалён), `llm_clients.py` (указатель + `~/Supervertaler`-фолбэки заменены; dev-фолбэки `user_data_private`/`user_data` сохранены как есть), `llm_pricing.py` (оверрайд `~/Supervertaler/pricing.json` → `<data_root>/pricing.json`).

Тестовый шов (ШАГ 4): все новые прогоны выставляют `SUPERVERTALER_DATA_ROOT=<iso>`; USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP/TMP остаются изолированными пустыми — как негативный контроль. Прежние пробы с посевом указателя помечены историческими (в AGENTS.md добавлен раздел «Data paths and the test seam»).

Монолит: **55 037 → 54 743** (−294; sha256 `f4ec3bf2b774b656a49e8307f36a1d34ae332a722de86ca80814d0fd49330f6f`, CRLF, CR=54 743=строкам, bare-LF 0; блобы: `d6fee55b33ec0ead` (база) → `b17fbc978b599c9b`).

## 2. Удалено из монолита (AST-проверка: в файле не существуют)

Блоки сняты с исполнения; снапшот HEAD-версии монолита: `Work_temp/.../batch-p1b/snapshots/mono_head.py` (sha256 `484c22654588080f…`):

| что | где было (на исполнении, база 55037) |
|---|---|
| `get_config_pointer_path()` | :171-192 (вкл. Windows/macOS/Linux ветки) |
| `get_default_user_data_path()` | :195-205 (`~/Supervertaler`) |
| `save_user_data_path()` | :208-215 |
| `load_user_data_path_from_config()` | :218-238 |
| тело `get_user_data_path()` (указатель + автовосстановление с побочной записью) | :241-289 → заменено делегатом :172-183 |
| комментарий-блок USER DATA PATH в `__init__` (нарратив указателя) | :6264-6281 → переписан |
| `_reinitialize_with_new_data_path()` | :6474-6537 — единственный вызов был из удаляемой Settings-группы (проверено grep+AST; в :6288/:36816 — только комментарии, переписаны) |
| Settings-группа «📁 Data Folder Location» (показ пути, Change…, Open, копирование данных, `save_user_data_path`) | :20805-20915 |
| устаревшие комментарии про диалог первого запуска / пересоздание сервиса | шапка :149-156, :36815-36816 |

macOS-ветки удаляемых функций ушли вместе с ними; остальные macOS-ветки монолита не тронуты (P1.7).

## 3. Греп-гейты приёмки

- `get_config_pointer_path|get_default_user_data_path|save_user_data_path|load_user_data_path_from_config|_reinitialize_with_new_data_path|user_data_path_from_config` по монолиту = **0** (осталось одно упоминание «Data Folder Location» в новой шапке-комментарии — описание того, что удалено).
- `APPDATA` в продукте: **0** вне разрешённых остатков — `modules/okapi_sidecar.py` `LOCALAPPDATA` ×2 (:666, :752; okapi-кеш/логи, **остаётся до P1-C**, перечислен), `modules/config_manager.py` (`.supervertaler_config.json` — это ConfigManager/last_directory, **P1-C**), `modules/settings_service.py:11` (докстринг, описание той же ConfigManager-сравки — P1-C), докстринг нового `portable_paths.py` (описание старой системы без литералов паттернов — переписан, литералов APPDATA нет).
- `expanduser`/`Path.home()` для путей данных: **0**; остались только crash-log `~/Desktop` (не путь данных, вне скоупа), okapi_sidecar (`Application Support`/`.local/share` — до P1-C), config_manager (P1-C).
- `config.json`-указатель в продукте: **0** (ConfigManager `.supervertaler_config.json` — P1-C).

## 4. Приёмочные пробы P1-B (логи/верdicts в `Work_temp/.../batch-p1b/`)

1. **Юнит portable_paths** (`batch-p1b_unit_portable_paths.py`): **UNIT-OK**, 13 проверок — все три ветки (default/dev-флаг/env), env побеждает флаг, относительный env → ValueError для обеих функций, пустой env игнорируется, снапшот дерева до/после идентичен (нет записей), реальный модуль: build_root=`E:\Dev`, data_root по факту флага.
2. **Полный app** (`batch-p1b_probe_app.py`, offscreen, шов на iso): **P1B-APP-OK** — `user_data_path == <iso>\Supervertaler`; создано 25 новых путей — ВСЕ под `<iso>\Supervertaler\` (prompt_library, resources/supervertaler.db, workbench/…); в AppData изолированного профиля не появилось ничего с «Supervertaler» и ни одного config.json; e2e: `save_general_settings`+`save_api_keys` (те же делегаты, что у кнопок Save) пишут в `<data_root>/workbench/settings/settings.json`, чтение назад OK; значение api-ключа байт-стабильно через цикл сохранения.
3. **Негативная** (`batch-p1b_probe_negative.py`, HEAD-код в worktree `<stage>\negroot\SupervertalerPortable` → build root внутри stage, БЕЗ шва и БЕЗ указателя): **P1B-NEG-OK** — `user_data_path = <negroot>\Supervertaler`; в изолированном профиле не создано НИ ОДНОГО файла (снапшот-диф пуст): нет `%APPDATA%\Supervertaler`, нет config.json, нет `~\Supervertaler`.
4. **Группы Settings до/после** (`batch-p1b_probe_groups.py`, один и тот же скрипт на worktree базы `32d52974` и на рабочей копии): 49 → 48 групп, **удалена ровно одна «📁 Data Folder Location»**, добавленных нет.
5. **Save-байты**: покрыто пробой 2 (api-ключ и general-секция после цикла Settings→Save совпадают с сеяными байт-в-байт).

## 5. Статика (база 32d52974 → после; логи `static_base.log`, `static_after.log`)

| показатель | было | стало | причина расхождения |
|---|---|---|---|
| AST-chain | 885/0 | **875/0** (−10, unresolved 0) | удалены 4 функции указателя, `_reinitialize_with_new_data_path`, Settings-группа (её connect-ы и обращения к self) |
| pyflakes | 542 (undefined 126/4) | **542 (126/4)** | без изменений; зеркала после правок pyflakes-чистые (лишние `sys` убраны) |
| py_compile canonical | 107/0 | **108/0** (+1) | новый `modules/portable_paths.py` |
| py_compile REFERENCE | 239/0 | **254/0** (+15) | +portable_paths, +12 копий проб, +генератор, +юнит-проба |
| headless | 88/2 | **89/2** | +portable_paths импортируется; те же 2 известных FAIL (setuptools, fitz) |
| grep-гейт 9.3 | CLEAN | **CLEAN** | вне зоны батча изменений нет |

## 6. 16-этапный оффскрин-набор ОДНИМ процессом (`batch-p1b_run_full.sh p1b`) — 16/16

Оба финальных прогона стартовали с **полностью чистым stage-каталогом** (`rm -rf batch-p1b/regress`) — само-посев runner'а (mkdir всех stage-каталогов, фикстуры из `docs/refactoring/audits/fixtures/regress_inputs/` c sha256 `c9c80973…/c079e760…/39abb383…`, создание `stage-regress/iso/`) отработал без ручного досева (ШАГ 0 подтверждён).

- regress: `export_simple_txt 5a12501f934a589c`, `export_docx 44828d90090f046d`, `export_tmx c413d56372e69dd9` — **байт-идентичны базе**; 5/5/4 сегментов.
- e2e: verdict OK (`b9-3/llm_e2e_verdict_p1b.json`); 5 запросов; агрегатный sha тел запросов **совпадает с базой Q-C-fin при одном рецепте** (`982e72a247f0a6ac` по sha256(json(requests)) у qcfin и у p1b — тела байт-идентичны; зафиксированный в P1-A `17e71049fd76b89c` считался другим рецептом и не воспроизводится как таковой, но равенство тел доказано прямым сравнением verdict-ов: без tag/port различаются только порядок асинхронных строк лога и seg/sec-число — известный transient).
- smoke: **SMOKE OK**, 41 пункт (единственный EXC — известный `fitz` на Tools/PDF-Rescue, среды без PyMuPDF; не регрессия).
- S-clean PROBE OK; S-upgrade PROBE OK, HASH-DIFF `added=[] removed=[] changed=[]` + известный transient `workbench/ai_assistant/index.json`.
- save modern/legacy (api_keys + mt_quick_lookup intact), TB OK, about OK, fb S2-S5 OK, profiles/qtchat/statusbar PROBE DONE, r9 a/ctrl/rm RESULT OK.

**Инцидент 1-го прогона (исправлен, коммит `0a0312b5`):** генератор копий брал оригиналы проб вместо batch-p1a-копий — 11 этапов упали на `ModuleNotFoundError: modules.usage_statistics` (stub в оригиналах). Генератор исправлен (источник `batch-p1a_<name>`, ассерт на отсутствие stub), копии перегенерированы, сюита перегнана с чистого stage — зелёная. Продукт не затронут.

Сид-скрипты (`batch9-4_seed_94a_save.py`, `r9_seed_profiles.py`) указатель не пишут и оставлены без копий. Сид шва в изолированных профилях пишет `settings.json` в `<iso>\Supervertaler` — совпадает с data_root по шву.

## 7. Пробы-копии и исторические пробы

- `batch-p1b_*` — 12 живых копий (11 из batch-p1a-копий + `batch8-15_regress_common.py`): каждая = источник + строка шва `os.environ["SUPERVERTALER_DATA_ROOT"] = str(iso)` − блок посева указателя (у window-пробы только шов: data dir приходит argv'ем). Генератор: `batch-p1b_make_probe_copies.py`; манифест хэшей: `batch-p1b_copies_manifest.sha256`.
- Исторические (не перезапускать на новом коде): все пробы с посевом config.json-указателя — оригиналы b8-15/g32*/qa/qb/qc/qcfin/m1/m2/9-4…, копии batch-p1a_* (правило записано в AGENTS.md).

## 8. Спец-проб и утилит P1-B (закрыты в audits)

`batch-p1b_unit_portable_paths.py`, `batch-p1b_probe_app.py`, `batch-p1b_probe_negative.py`, `batch-p1b_probe_groups.py`, `batch-p1b_make_probe_copies.py`, `batch-p1b_kill_leftovers.ps1`, `batch-p1b_run_full.sh`, `batch-p1b_copies_manifest.sha256`, фикстуры `fixtures/regress_inputs/` + README.

---

## 9. Для Дмитрия: тестовая сборка (простым языком)

### 9.1 Какие файлы меняются в тестовой сборке после этого батча

Пересобирать сборку целиком НЕ нужно; достаточно (решение о пересборке всё равно твоё):

| действие | файл |
|---|---|
| заменить | `SupervertalerPortable\Supervertaler.py` (новый sha256 `f4ec3bf2…`) |
| заменить | `SupervertalerPortable\modules\ui_scale.py` |
| заменить | `SupervertalerPortable\modules\llm_clients.py` |
| заменить | `SupervertalerPortable\modules\llm_pricing.py` |
| добавить | `SupervertalerPortable\modules\portable_paths.py` (новый) |
| удалять ничего не нужно | (в этом батче файлы продукта не удалялись) |

Всё это — файлы из репозитория `E:\Dev\SupervertalerPortable` после моего финального коммита.

### 9.2 Где сейчас лежат данные тестовой сборки и что скопировать

Сейчас (до обновления) настройки/базы тестовой сборки лежат **внутри редиректнутого профиля**, здесь:

```
D:\SupervertalerPortable_test\Supervertaler\profile\Supervertaler\
    prompt_library\   — библиотека промптов
    resources\        — supervertaler.db (термины/TM)
    workbench\        — settings\settings.json (все настройки и API-ключи) и пр.
```

После обновления кода приложение будет хранить данные **на уровень выше**, здесь:

```
D:\SupervertalerPortable_test\Supervertaler\          (рядом с папкой profile)
```

**Что сделать один раз руками:** скопировать три папки `prompt_library`, `resources`, `workbench` из
`D:\SupervertalerPortable_test\Supervertaler\profile\Supervertaler\`
в
`D:\SupervertalerPortable_test\Supervertaler\`
(просто перетащить с копированием; папку `profile` там не трогать). После этого сборка увидит свои настройки, промпты и термины. Старую копию в `profile\Supervertaler` можно оставить как резервную копию.

### 9.3 Нужен ли редирект профиля в start.bat

**Да, оставить как есть.** Он по-прежнему изолирует сборку от твоего настоящего профиля Windows (мусор от Qt, временные файлы и т.п.). Но теперь он **больше не влияет на пути данных**: данные приложение кладёт в `D:\SupervertalerPortable_test\Supervertaler\` независимо от редиректа, и в самом профиле папки Supervertaler появляться не должно (это проверяет T-P1B.4).

### 9.4 Ручные тесты (обязательные)

**T-P1B.1 — запуск с перенесёнными данными.**
Запусти `D:\SupervertalerPortable_test\start.bat`. Приложение должно стартовать; настройки, библиотека промптов и термины — на месте (после копирования из 9.2). Открой любой старый промпт в библиотеке — должен открыться.

**T-P1B.2 — настройки переживают перезапуск.**
В приложении открой вкладку Settings, поменяй любую заметную настройку (например, размер шрифта таблицы), нажми «💾 Save … Settings» в этой же группе, закрой приложение, запусти снова. Настройка должна остаться.

**T-P1B.3 — проект и перевод.**
Открой/создай проект (File → Open Project / New Project), импортируй тестовый файл `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1b\regress\stage-regress\inputs\test.txt` (или любой свой .txt/.docx), переведи один сегмент через настроенный сервер. Перевод должен появиться в таблице; проект должен сохраниться и открыться заново.

**T-P1B.4 — в профиле не появилось папки Supervertaler.**
После T-P1B.1–T-P1B.3 открой Проводником папку `D:\SupervertalerPortable_test\Supervertaler\profile\`. В ней НИЧЕГО нового появиться не должно — в частности, папки `Supervertaler` внутри профиле быть не должно было создаться заново, и файла `config.json` в `profile\AppData\Roaming\` быть не должно. (Папки AppData/Desktop/Documents/Downloads/Temp — это сам скелет профиля, они там и должны быть.)

**T-P1B.5 — в Settings нет группы «Data Folder Location».**
Открой Settings: между «🌐 Language» и «🔊 Sound Effects» группы с путём к папке данных и кнопками «Change…»/«Open» быть не должно — группа удалена.

Что считается провалом любого теста: приложение не стартует; настройки/промпты потерялись после копирования из 9.2; в `profile\` появилась папка `Supervertaler` или файл `config.json`; группа «Data Folder Location» видна.

---

## 10. Вопросы координатору

1. QP1.2: служебные файлы (last_directory.json, quicktrans.ini) и QSettings-фолбэк `<root>\Supervertaler\qsettings\` — план на P1-C/P1.6 через `state_root()`; подтверди, что `state_root() = build_root()` соответствует замыслу.
2. Dev-режим: в репозитории `E:\Dev\SupervertalerPortable` флага `.supervertaler.local` сейчас НЕТ → dev-запуски резолвят данные в `E:\Dev\Supervertaler` (не `user_data_private`). Это ожидаемое поведение ветки 3, или флаг нужно создать/задокументировать?
3. e2e-агрегат: P1-A фиксировала `17e71049fd76b89c`, мой рецепт даёт `982e72a247f0a6ac` (одинаково у qcfin и p1b). Принять `982e72a2…` (sha256 json(requests)) как канонический рецепт для следующих батчей?

## 11. Среда и дисциплина

Все прогоны offscreen в `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1b\`; реальные пользовательские данные, реестр и dev-рантайм не читались и не писались; kill только по PID-фильтру (survivors: пусто); worktree-и (`head-wt`, `negroot/SupervertalerPortable`) сняты после проб. Тестовая сборка не обновлялась (решение Дмитрия). `git push` не выполнялся.
