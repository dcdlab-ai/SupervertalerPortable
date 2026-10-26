# ОТЧЁТ BATCH P1-A — P1.1a usage statistics + P1.1b autostart + P1.2 check for updates (удаление трёх cluster'ов)

Промпт: `docs/refactoring/prompts/Promt - BATCH P1-A.txt`. План: RECON P1.0 (вердикт GO, под-батчи P1.1a/P1.1b/P1.2).
База: `3ba4ecb2` (verdict-record поверх кода `824454d5`). Пуш **не выполнялся**. **Стоп до вердикта координатора.**

## 1. Итог

Три cluster'а внешнего состояния и непрошенного сетевого трафика удалены из продукта тремя коммитами:

| Коммит | Под-батч | Содержание | Суперvertaler.py (строк) |
|---|---|---|---|
| `68f0502f` | P1.1a | `git rm modules/usage_statistics.py` (295) + 3 блока монолита (вызов, Privacy-группа, метод) | 55 687 → **55 634** |
| `b0c7231d` | P1.1b | `git rm modules/autostart.py` (237, целиком, incl. Linux/macOS ветки — QP1.10) + tray-блок + обработчик | 55 634 → **55 591** |
| `7d769099` | P1.2 | Help-пункт, `check_for_updates`, fallback, About-кнопка, QNetwork-импорт, осиротевший `_normalize_version_tuple` | 55 591 → **55 037** |

Суммарно: монолит −650 строк (55 687 → 55 037), два модуля удалены (532 строк).
Приёмка: приложение стартует offscreen (изолированный профиль) без ошибок; `winreg` в продукте — **0**;
`usage_statistics|autostart|check_for_updates|_fetch_latest_release` — **0**; Privacy-группы в Settings нет;
«Start with computer» в tray нет; пункта обновлений в Help нет; в About — только **Copy Version Info** и **Close**.

## 2. Что именно удалено (снапшотный протокол)

Все блоки удалены по снапшотам, снятым с рабочей копии базы (`snapshots/make_snapshots.py`, манифест `baseline_manifest.sha256`);
каждый удалённый «−»-ран git diff посверен с снапшотом побайтово (`snapshots/verify_removals.py` — OK для всех блоков
соответствующего коммита; для кластера P1.2 дополнительно вариант «+1 trailing blank», удалён побайтово скриптом
`remove_cluster.py`, 23 278 байт за одну правку). py_compile 0 ошибок после каждой правки.
Границы методов подтверждены AST (`ast.parse`, def/end_lineno) — снапшоты выровнены по целым методам с
разделительной пустой строкой.

**P1.1a** (монолит, старые номера строк базы):
- вызов с комментарием — `:6436-6438` (`# Usage statistics – opt-in dialog (once) and anonymous ping` + `self._init_usage_statistics()`); sha снапшота `73fb65f8…`;
- группа «Privacy» в `_create_settings_tab` — `:20814-20839` (CheckmarkCheckBox `usage_stats_cb`, `_on_usage_stats_toggled`, `self.log(...)` записи флага); sha `90b3be00…`;
- метод `_init_usage_statistics` — def@37093 end@37115 (AST), снапшот `:37093-37116`; sha `6b5051dd…`;
- модуль `modules/usage_statistics.py` (295 строк, LF) — удалён: sha256 `665396442bd06ae8ed343b8cf406b1c2daa0b1bd0964108f14a1be0fcdcdc828`.
  (В модуле был единственный в продукте read-only читатель реестра — Accessibility\TextScaleFactor.)
- Ключи `usage_statistics_*` в существующих settings.json **не тронуты** (инертны, QP1.5) — проверено пробой §5.

**P1.1b**:
- tray-блок с локальным импортом `modules.autostart` — `:26501-26517`; sha `e5fee073…`;
- обработчик `_on_toggle_autostart` — def@26623 end@26647 (AST, incl. resync-блока записи реестра и balloon-подсказки), снапшот `:26623-26648`; sha `d2d305c1…`;
- модуль `modules/autostart.py` (237 строк, LF, HKCU Run writer + macOS plist + Linux .desktop) — удалён целиком: sha256 `a0e260c8324279d885e0228a1a0ef9af260bc1a9b91a8b8574c5b22759063382`.

**P1.2**:
- Help-пункт `🔄 Check for Updates...` — `:8536-8540`; sha `ee058569…`;
- строка импорта `from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply` — `:429` (осиротела вместе с cluster'ом); sha `421cf9a1…`;
- непрерывный cluster `:48286-48827` (23 276 байт): `check_for_updates` (def@48286, ранний return + мёртвый QtNetwork-код), `_fetch_latest_release_info_from_github` (def@48793), `_normalize_version_tuple` (def@48818 — осиротела: оба колл-сайта лежали внутри удалённого мёртвого кода); sha `e1dd4411…`;
- About-кнопка `🔄 Check for Updates...` — `:48998-49002`; sha `fd538ff1…`.
- **Сохранено:** `_format_version_for_display` (нужна кнопке Copy Version Info — `show_about` → `_build_version_info_text`, монолит `:48184`/`:48199` — проверено grep).
- Атрибуты `_update_check_*`: grep по продукту — **0** (все жили только внутри cluster'а).

sha256 blob'ов Supervertaler.py по коммитам (git-нормализованный LF): `2c8e4d6e`→`5cd306256d32e6e3…`, `68f0502f`→`4d5b0ed038d433a0…`, `b0c7231d`→`bb8a2249b47279cf…`, `7d769099`→`484c22654588080f…`.
**Итоговая рабочая копия (CRLF):** `Supervertaler.py` sha256 `8a38644f94a9a975fbb110f1b88ca007feaf41a17f12656df552212d9fbc0128`,
**55 037 строк**, 2 949 976 байт, CR = 55 037 = строкам, bare-LF 0. py_compile OK.

## 3. Гrep-гейты приёмки (финальная запись, после 7d769099)

- `winreg` вне `docs/` и `__pycache__`: **0**.
- `usage_statistics|autostart|check_for_updates|_fetch_latest_release_info_from_github|_normalize_version_tuple` в `Supervertaler.py` + `modules/`: **0**.
- `_update_check_`: **0**.
- Конструкторы `QSettings("Supervertaler", "MTQuickPopup")`: **2** — `modules/quicktrans.py:826`, `:1563` (вне объёма P1-A; перенос в ini — P1.6, ответ QP1.1).

## 4. UI-пробы до/после (`probes/batch-p1a_probe_ui.py`, offscreen, изолированные профили iso-pre/iso-post)

Сравнение снапшотов (`compare_snapshots.py`):
- **Tray**: удалено `['Start with computer']`, добавлено `[]`. Post: Show Workbench, Open SuperLookup, Open Settings, ─, Close to tray, Start minimized to tray, ─, Quit Supervertaler.
- **Settings-группы**: удалено `['Privacy']`, добавлено `[]` (46 групп post против 47 pre).
- **Help-меню**: удалено `['🔄 Check for Updates...']`, добавлено `[]`.
- **About-диалог**: кнопки post `['📋 Copy Version Info', 'Close']` (удалена `🔄 Check for Updates...`); лейблы (заголовок v1.10.371, license, Built with PyQt6) — идентичны (True).
- Tray доступен в обоих прогонах (isSystemTrayAvailable monkeypatch) — путь построения меню покрыт.

## 5. settings.json байт-стабильность

Сидed-файл (с инертными ключами `usage_statistics_enabled=false`, `usage_statistics_asked=true`, `usage_statistics_id=seed-UUID`) прогонялся через полный старт приложения (построение окна) и закрытие — и до, и после удалений:
sha256 **`4559007a85f2b01706fd5bafa28350f963a170151a90ba6036514db7260b2e37`** — идентичен на всех трёх замерах (seeded / after-build / after-close) в **обоих** прогонах (`bytes_stable=True pre и post`). Save за прогон не вызывался; Save-путь покрыт этапом save probe сюиты (§7).

## 6. Статика (pre `p1a-pre` / post `p1a-post`, логи `static/static_pre.log`, `static/static_post.log`)

| Метрика | Было (база Q-C-fin) | Стало | Причина |
|---|---|---|---|
| AST chain | 893 / 0 unresolved | **885 / 0** | −8 self.*-рёбер: Privacy-группа (2× self.tr, 1× self.log, 2× self._get_unified_settings_path) + 1× self._init_usage_statistics в `__init__` + 2× self.tr на пункте Help-меню |
| pyflakes warnings | 548 | **542** | −6, все из удалённого `usage_statistics.py` (4 неиспользуемых импорта в `show_opt_in_dialog`, `typing.Optional`, F841 `no_btn`); 10 warning-строк сместились номерами (redefinition/shadow) — net 0 |
| pyflakes undefined | 126 строк / 4 имени | **126 / 4** | без изменений |
| py_compile CANONICAL | 109 / 0 | **107 / 0** | −2 (удалённые модули вне docs/) |
| py_compile REFERENCE | 224 / 0 | **222 / 0** | −2 (замер post статиками до docs-коммита); после docs-коммита `977f6da2` (11 копий проб + 6 скриптов stages) measured **239 / 0** (проверено прогоном py_compile по tracked-набору) — новая база фиксируется вердиктом |
| headless imports | 90 ok / 2 fail (92) | **88 ok / 2 fail (90)** | −2 модуля; те же известные fails (`setup`→setuptools, `pdf_rescue_Qt`→fitz) |
| grep-gate | CLEAN | **CLEAN** | без изменений |

## 7. Полный 16-этапный оффскрин-набор (ОДНИМ процессом)

Runner: `suite/batch-p1a_run_full.sh` (копия канонического `batch-qc_run_full.sh`; probes — 11 копий `batch-p1a_`,
seeds/regress_common — канонические; kill_leftovers.ps1 — PID-фильтр).
Примечание по прогонам (добросовестно): **первый запуск сюиты не исполнен** — в runner'е отсутствовало `mkdir -p "$S"`
для свежего stage-каталога, все 21 редирект-лог не создались, этапы не стартовали (лог `suite/run_full_main.log` — только
«No such file»); python-процессов не запускалось, сирот нет. Runner исправлен: `mkdir -p $S/stage-regress/inputs` +
засев фикстур `test.txt/test.md/test.docx` из `batch-g32e/stage-regress/inputs` (байт-в-байт база Q-C-fin: хэши
`c9c80973…`/`c079e760…`/`39abb383…`; оригиналы b8-15/regress/inputs утрачены свипом 2026-10-22).
Перезапуск: `suite/run_full_main2.log`, tag `p1a`.

Результат перезапуска (tag `p1a`, 15/16 зелёных; regress-этап на первом прогоне упал на моём досеве — харнесс требует
предсуществования `stage-regress/iso/`, в Q-C он доставался от прошлых прогонов; засеян каталог, этап перегнан соло
`regress_after_p1a2.log` → зелёный. Итог — **16/16**):
- fb (9.4h) `S5 OK: True`; profiles (9.4f) `EXEC OK: True`; qtchat `PROBE DONE` (чипы Profile A/B CUS, chat-виджет, меню-экшены); statusbar-prof `EXPECTED '🔌 Profile B: model-b' -> OK`;
- e2e: **verdict OK** (`b9-3/llm_e2e_verdict_p1a.json`), тела запросов байт-идентичны базе Q-C-fin (агрегатный sha тел `17e71049fd76b89c…` = у `qcfin`);
- S-clean `PROBE OK (3.8s)`; S-upgrade `PROBE OK (4.0s)`, HASH-DIFF `added=[] removed=[] changed=[]` + известный transient `index.json`;
- **regress: хэши экспорта байт-идентичны базе** — `export_simple_txt=5a12501f934a589c`, `export_docx=44828d90090f046d`, `export_tmx=c413d56372e69dd9`; MODAL-ATTEMPTS 3 (монkeypatch-захват, штатный паттерн);
- smoke (копия, 41 пункт): **SMOKE OK (12.5s)**, известный EXC PDF-Rescue/fitz + jitter new-widgets `['QFrame','QMenu']`;
- termbase `REGRESS-TB OK (11.6s)`; about-проба `RESULT OK`; save modern + save legacy — `OK` (mt_quick_lookup/api_keys intact, seed → save → сравнение); r9 a/ctrl/rm — `RESULT OK`;
- Traceback-записи в логах сюиты: только в несостоявшемся первом прогоне regress (ошибка харнесса на mkdir до старта приложения); в логах прогонов — нет.
- Сироты: после соло-regress сняты сидкар-java (PID по фильтру) и python-процессы прогонов; survivor — пользовательский `33960:python.exe` (не тронут).

## 8. Пробы-копии и исторические пробы

Канонические пробы сюиты (batch8-13/8-15/9-3/9-4/r9) содержат 2-строчный stub `import modules.usage_statistics … show_opt_in_dialog` (нужен был для offscreen-старта) и/или вызывают удаляемые методы.
После удалений их импорт сломается, поэтому:
- **Новый живой набор** — 11 файлов `docs/refactoring/audits/batch-p1a_*.py`: байт-идентичные оригиналам минус stub
  (генератор `make_probe_copies.py`); у smoke-копии дополнительно удалён пункт 10 «Help/Check-for-Updates` → smoke-база **42 → 41** (каноническая таблица `batch8-13_code_tools_smoke.py` не тронута, остаётся исторической базой по правилу AGENTS.md).
- **Исторические (не перезапускать)**: оригиналы `batch8-15_probe_e02.py`, `batch8-13_code_menu_probe.py` и все оригиналы probe'ов сюиты (stub-импорт больше не резолвится) — помечены как исторические; их pre-результаты остаются доказательством поведения до удалений.

## 9. Файлы для тестовой сборки (`D:\SupervertalerPortable_test`)

Заменить:
- `Supervertaler.py` — sha256 `8a38644f94a9a975fbb110f1b88ca007feaf41a17f12656df552212d9fbc0128` (55 037 строк, CRLF).

Удалить в тестовой сборке (файлы прекратили существование в продукте):
- `SupervertalerPortable/modules/usage_statistics.py`;
- `SupervertalerPortable/modules/autostart.py`.

Пересборка — отдельное решение Дмитрия (правило AGENTS.md); в этом батче тестовая сборка не тронута.

## 10. Ручные тесты (для Дмитрия, обязательные; замечания — не требуют)

**T-P1.1 — трей и Settings: удалённые пункты отсутствуют**
1. Цель: убедиться, что приложение запускается как раньше, а «автозапуск» и «приватность» исчезли из интерфейса.
2. Подготовка: ничего менять не нужно; любой обычный запуск (тестовая сборка `D:\SupervertalerPortable_test\start.bat` или `E:\Dev\SupervertalerPortable\Supervertaler.py`).
3. Шаги: (а) запустить приложение; дождаться окна; (б) найти значок приложения в системном трее (правый нижний угол, возможно в «скрытых значках»); щёлкнуть по нему правой кнопкой; (в) открыть Settings (меню View → Settings или кнопка Settings) и пролистать список секций/групп вниз.
4. Ожидание: в меню значка托盘 ровно: Show Workbench, Open SuperLookup, Open Settings, разделитель, Close to tray (instead of quit), Start minimized to tray, разделитель, Quit Supervertaler — пункта «Start with computer» **нет**; в Settings группы «Privacy» **нет**; приложение работает (грид, меню).
5. Провал: «Start with computer» в трей-меню; группа Privacy; приложение не стартует / окно падает при открытии Settings.

**T-P1.2 — Help и About: проверки обновлений больше нет**
1. Цель: убедиться, что меню Help и окно About не содержат проверки обновлений.
2. Подготовка: то же приложение, что в T-P1.1.
3. Шаги: (а) меню Help — просмотреть все пункты; (б) Help → ℹ️ About — посмотреть кнопки окна; (в) нажать «📋 Copy Version Info» и склеить содержимое в любой текстовый редактор.
4. Ожидание: в Help ровно: Supervertaler Workbench Help, Keyboard Shortcuts, Changelog, 📋 Copy Version Info, Open Diagnostic Log, Open Log Folder, Community Discussions, GitHub Repository, ℹ️ About — пункта «🔄 Check for Updates…» **нет**; в About ровно две кнопки: «📋 Copy Version Info» и «Close»; в буфер вставляется текст версии (Supervertaler Workbench v…).
5. Провал: «Check for Updates» в любом из двух мест; кнопка «Check for Updates…» в About; Copy Version Info пустой/не работает.

**T-P1.3 — обычная работа не пострадала**
1. Цель: открыть проект, перевести сегмент, сохранить настройки — без новых ошибок.
2. Подготовка: любой рабочий проект (например из `D:\_old\…` — путь в Settings → «Data Folder Location» не менять); профиль Custom LLM активен (Settings → AI Providers).
3. Шаги: (а) File → Open Project, открыть проект; (б) в первом сегменте Ctrl+T (или правый клик → Translate); дождаться перевода; (в) Settings → Save Settings; (г) File → Save Project.
4. Ожидание: все четыре шага проходят как раньше (перевод появляется в колонке Target, Save пишет «Settings saved», проект сохраняется); в логе (Help → Open Log Folder) нет строк `Traceback`.
5. Провал: Ctrl+T выдаёт ошибку/пусто на обычном тексте; Settings→Save падает; любые новые всплывающие ошибки.

Опциональные (покрыто пробами): старт с пустым профилем (S-clean, сюита §7), legacy settings.json (save probe legacy §7), e2e-запросы к профилю (e2e §7).

## 11. Вопросы координатору

Вопросов нет. Сомнительных мест не найдено: все найденные при удалении зависимости (QNetwork-импорт, `_normalize_version_tuple`) осиротели точно и удалены в том же коммите; `_format_version_for_display` сохранена как живая.

## 12. Среда и дисциплина

- Реальный реестр не трогался (ни reg query с записью, ни запуски продукта на реальном профиле); все прогоны — offscreen, изолированные профили под `E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1a\`; реальный `C:\Users\Dmitry` и `HKCU\Software\Supervertaler\MTQuickPopup` не тронуты (гейт M1 лестницы RECON P1.0 выполняется в P1.8).
- Реальный `settings.json` пользователя не открывался ни на чтение запись: пробы §5/сюита работают только с засеянными копиями в изолированных профилях.
- Dev-рантайм `E:\Dev\python-embed` не изменялся.
- Kill только по PID-фильтру (`kill_leftovers.ps1`: python по ExecutablePath `E:\Dev\python-embed\*`, java по CommandLine `*SupervertalerPortable*`); survivors — пользовательский `33960:python.exe` (чужие процессы не тронуты).
- Пуш не выполнялся. **Стоп до вердикта координатора.**
