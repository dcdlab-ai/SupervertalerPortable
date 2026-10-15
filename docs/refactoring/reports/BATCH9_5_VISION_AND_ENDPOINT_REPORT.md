# ОТЧЁТ Batch #9.5 — «Модель поддерживает vision» в профиле Custom + запрет сохранения профиля с пустым endpoint

Исполнитель: агент (executor). Координатор: Дмитрий. Промпт: «Модель поддерживает vision» в профиле Custom + запрет сохранения профиля с пустым endpoint.
Дата: 2026-10-14. База: `575bd419` (docs 9.4i; код = состояние `2e9dd938`: Supervertaler.py `fb3dce5c…`/54992, quicktrans.py `6a6812be…`/1635).
Коммиты локальные, НЕ запушены (push — только по команде Дмитрия).

---

## §1. Коммиты

| # | SHA | Содержание | Монолит | llm_clients | prompt mgr | settings_service |
|---|-----|-----------|---------|-------------|------------|------------------|
| 9.5a | `791024bd` | vision как свойство профиля: данные + клиент | 54992→54999 | 597→598 | 6833 | 598→599 |
| 9.5b | `0410bdc4` | UI-чекбокс vision в AI Settings | 54999→55020 | 598 | 6833 | 599 |
| 9.5c | `7aa98248` | гейты берут флаг профиля + тексты; шим удалён | 55020 | 598→579 | 6833 | 599 |
| 9.5d | `61639c60` | запрет сохранения пустого endpoint Custom LLM-профиля | 55020→55042 | 579 | 6833 | 599 |
| 9.5e | `0b9c9ad2` | follow-up по ответам координатора (Q2/Q3/Q4): текст warning через `self.tr()` по формулировке Дмитрия; V6-кейс «пустой список»; legacy-сценарий save-пробы | 55042→55040 | 579 | 6833 | 599 |

Финальное состояние (для пакета тестовой сборки, §5):
- `Supervertaler.py` — SHA256 `fe5f706c1f654b061c64bda60503b427d2035000fac28154cd10e79aa7a70552`, 55040 строк (CRLF)
- `modules/llm_clients.py` — `7f2b9ee9e2ff7f101f7b1ddbcf764deb59c3c7c7675ccbe7f81453d738226c47`, 579
- `modules/settings_service.py` — `08a0d943a8b04add8b0255ec5548042b69489a6c34e92c746886b82b68d79667`, 599
- `modules/unified_prompt_manager_qt.py` — `cec2ef68b48f23148e4a9f7ab9ef2e54f8bcdd94ea89c117ed70e0bc04d00661`, 6833
- `modules/quicktrans.py` — `6a6812be6c7acce66cbb821c83010e66e658abe39ccf286a06945d153fbf8808`, 1635 (в 9.5 НЕ менялся)

---

## §2. Рекон (RECON_95.md — полный текст в `docs/refactoring/reports/RECON_95.md`)

Ключевые выводы:
- **Vision-гейты**: 4 вызова, у всех экземпляр клиента в области видимости — Image Extractor (`Supervertaler.py:9901`, через `chat_backend.llm_client`), figure-context `translate_current_segment` (`:48891`, `client` создан в `:48737`), prompt manager `_collect_autoprompt_images` (`modules/unified_prompt_manager_qt.py:4458`, через `chat_backend.llm_client`), внутриклиентский `translate_with_usage` (`modules/llm_clients.py:471`, `self`). Ни один гейт не требует рефакторинга — флаг экземпляра резолвится на месте.
- **Формат images**: OpenAI-compatible content-parts (`[{"type":"text",...},{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}]`) — проверен на fake-сервере, **правка 0 строк** (условие СТОП «>30 строк» не близко).
- **Структура профилей**: `ui.llm_settings.custom_openai_profiles = [{name, endpoint, model, api_key}]` + `custom_openai_active_profile` + плоские зеркала; добавление ключа `supports_vision` — единственное изменение формата хранения.
- **Валидация endpoint**: возможна в начале `_save_ai_settings_from_ui` до первой записи на диск — валидация без перестройки диалога.
- **Custom MT** (описан, не трогался): `custom_mt_profiles` в той же секции `llm_settings`, сохраняется `_save_mt_quick_lookup_settings` (вкладка QuickTrans), пустой endpoint MT разрешён.
- **СТОП-условия**: не сработали (гейты ≤4 с контекстом профиля; валидация без перестройки; VISION_MODELS — 3 внешних потребителя, все гейты; images 0 строк).

---

## §3. Изменения по коммитам

### 9.5a — данные + клиент (`791024bd`)
- `modules/llm_clients.py`: `LLMClient.__init__` получил `supports_vision: bool = False`; `self.supports_vision = bool(supports_vision)`; гейт в `translate_with_usage`: `if images and not self.supports_vision: images = None`.
- `Supervertaler.py::create_llm_client`: резолвит `profile.get('supports_vision')`; не-bool → False; передаёт в конструктор. Плоский легаси-синтез `_get_active_custom_profile` несёт `supports_vision: False`.
- `modules/settings_service.py`: миграция legacy-конфига в профиль добавляет `'supports_vision': False`.
- `VISION_MODELS` + `model_supports_vision` оставлены **временным always-False шимом** (3 внешних гейта 9.5c ещё читали его; удалён в 9.5c). settings.json при загрузке НЕ переписывается (V4).

### 9.5b — UI (`0410bdc4`)
- `_create_ai_settings_tab`: `custom_vision_cb = CheckmarkCheckBox(self.tr("Model supports vision (image input)"))` + tooltip «Enable only if the model behind this endpoint accepts images…»; populate по профилю (не-bool → False); `toggled → _sync_fields_to_profile`; новый профиль — unchecked; `update_combo_states` включает чекбокс.
- `_save_ai_settings_from_ui`: параметр `custom_vision_cb=None`; запись `profiles[idx]['supports_vision'] = custom_vision_cb.isChecked() …`; Save-лямбда передаёт чекбокс.

### 9.5c — гейты + тексты (`7aa98248`)
- Image Extractor гейт 3 → `if not getattr(llm_client, 'supports_vision', False):`; текст: «To enable it, tick Model supports vision (image input) for this profile in Settings → AI Settings, then re-run.»
- Figure-context гейт → `if getattr(client, 'supports_vision', False):` (импорт `LLMClient` из try-блока удалён; мёртвая gemini-ветка не тронута — правило 8.18).
- Prompt manager гейт 3 → `if not getattr(llm_client, "supports_vision", False):` + текст Settings → AI Settings; обновлены tooltip и сообщение AutoPrompt-cancel.
- `VISION_MODELS` + `model_supports_vision` удалены (0 потребителей в продукте; 2 исторических audit-скрипта не тронуты). Из `from modules.llm_clients import LLMClient, load_api_keys` убран `LLMClient` (неиспользуемый; `load_api_keys` был неиспользуем на базе — см. §9).

### 9.5d — запрет пустого endpoint (`61639c60`)
- `_save_ai_settings_from_ui`: после синка видимых полей активного профиля, **до первой записи на диск** — цикл по всем профилям живого снимка: `if not str(_gp.get('endpoint','')).strip():` → `QMessageBox.warning(self, "Empty Endpoint", …имя профиля…)`, `custom_profile_combo.setCurrentIndex(idx)`, `return`. Файл не меняется, вкладка открыта. Строка из пробелов = пусто. Пустой список профилей разрешён. **Custom MT не проверяется** (пустой MT endpoint разрешён).

### 9.5e — follow-up по ответам координатора (`0b9c9ad2`)
- **Q2 (текст)**: warning переведён на формулировку Дмитрия и обёрнут в `self.tr()` (как остальные диалоги настроек): заголовок `self.tr("Empty Endpoint")`, тело `self.tr('Profile "{0}" has no endpoint. Fill it in or remove the profile.').format(_gp_name)`. Поведение прежнее: диалог остаётся открытым, на диск ничего не пишется, проблемный профиль выбирается в комбо. 55042→55040 строк (−2: тело диалога стало короче). Вызов находится в `_save_ai_settings_from_ui`, который НЕ входит в AST-chain (chain считает `_create_*_settings_tab`), поэтому chain 873/0 не изменился.
- **Q3 (V6-кейс)**: в спец-пробу добавлен явный кейс: два профиля → удалить оба («−»×2) → комбо пустое → Save → **успех без warning**, на диске `custom_openai_profiles == []`, зеркала очищены, статус-бар «Custom profile not configured» → **перезапуск** (второй `SupervertalerQt`) строится без ошибок и читает ноль профилей. Спец-проба: **45/45 PASS** (39 прежних + 6 новых проверок).
- **Q4 (легаси-сценарий)**: сид 9.4a save-пробы принимает аргумент `modern|legacy`. `modern` — активный профиль с `supports_vision: False` (артефакт, правка принята координатором); `legacy` — файл **до-9.5** (ни у одного профиля ключа `supports_vision` нет). Save-проба в legacy-режиме проверяет: профили сохранены (сравнение с игнорированием нового ключа), активный профиль приобрёл `supports_vision=False`, НЕактивные профили ключ НЕ приобрели. Runner `batch9-4_run_94i.sh` гоняет оба сценария: modern ALL OK + legacy ALL OK. Регрессия 9.1 продолжает покрывать файлы, написанные до 9.5.

---

## §4. Метрики защит (на каждый коммит; полная таблица логов — §10)

| Метрика | база (9.4i) | 9.5a | 9.5b | 9.5c | 9.5d | 9.5e |
|---------|------------|------|------|------|------|------|
| AST chain (calls/unresolved) | 871/0 | 871/0 | 873/0 (+2 self.tr чекбокса, оба резолвятся) | 873/0 | 873/0 | 873/0 |
| pyflakes warnings | 549 | 549 | 549 | 548 (−1 удалён неиспользуемый импорт LLMClient) | 548 | 548 |
| pyflakes undefined (lines/names) | 126/4 | 126/4 | 126/4 | 126/4 | 126/4 | 126/4 |
| py_compile канон (вне docs/) | 109/0 | 109/0 | 109/0 | 109/0 | 109/0 | 109/0 |
| headless imports | 90/2 (setuptools, fitz) | 90/2 | 90/2 | 90/2 | 90/2 | 90/2 |
| grep-гейт 8 файлов | CLEAN | CLEAN | CLEAN | CLEAN | CLEAN | CLEAN |
| offscreen-обойма (S-clean/S-upgrade/regress/smoke/TB/About/save modern+legacy/r9×3/e2e/qtchat/statusbar/profiles/fallback) | зелёная | зелёная | зелёная | зелёная | зелёная | зелёная |
| спец-проба probe_95 (V1–V8) | — | — | — | 33/39 (6 FAIL = V6, фича не готова) | **39/39** | **45/45** (+6 V6-Q3) |

Regres-хэши стабильны на всех коммитах: `5a12501f…` / `44828d90…` / `c413d563…`; S-clean 30 TREE; S-upgrade HASH-DIFF пустой; Tools-smoke 42.

**Пояснение к S-clean (замечание координатора 2026-10-15):** в §4/§10 стояло «31 TREE» — это grep-подсчёт, включающий строку заголовка `DATA-TREE (30 entries …)`; реальных записей **30** (проверено по `batch9-5_probe_after_b95-base_clean.log`: заголовок + 30 TREE-строк). Эволюция базы: **28** (8.15, `batch8-15_probe_afterF_clean.log`) → **29** (9.4f, `batch9-4_probe_after_94f_clean.log`) → **30** (9.5, база батча). Прирост — каталоги `workbench/ai_assistant/attachments/<дата>` (20261011, 20261013, 20261014) в iso-профиле чата, создаваемые при запуске приложения; состав дерева `prompt_library/resources/workbench` идентичен базе на всех коммитах 9.5 (30 == 30, расхождения между коммитами 9.5 — 0). То есть база S-clean сменилась **до** начала 9.5 (на 9.4f), агент сравнивал каждый коммит с базой батча (b95-base) и расхождений между коммитами не имел; в отчёте это отдельным пунктом не было вынесено — исправлено настоящей правкой.

**Пояснения к отклонениям:**
- chain 871→873 (9.5b): ровно +2 вызова `self.tr()` (label + tooltip чекбокса в `_create_ai_settings_tab`), оба резолвятся — diff JSON before/after: added 2, removed 0.
- pyflakes 549→548 (9.5c): −1 = удалённый неиспользуемый импорт `LLMClient`; множество undefined имён идентично (126 строк / 4 имени, все в `tmx_editor.py`).
- 9.4a save-probe: с 9.5b Save легитимно дописывает `supports_vision` активному профилю → строгая dict-проверка «profiles preserved» требовала seed с ключом. Сид-скрипт (audit-артефакт, редактируемый) дополнен `supports_vision: False` у активного профиля → ALL OK. **Это изменение артефакта, а не продукта (ответ Q4).** Самый важный случай — файлы, написанные до 9.5, — сохранён отдельным legacy-кейсом (9.5e): сид без ключа `supports_vision`, проверка «активный приобрёл False, неактивные без ключа». r9-сиды и сиды 9.4f/9.4i правки не потребовали (все endpoint-ы непустые; 9.4f/9.4i кликают только «Save QuickTrans», 9.5d их не касается).

---

## §5. Пакет для тестовой сборки

Файлы для обновления в `D:\SupervertalerPortable_test\SupervertalerPortable\` (по правилам замороженной сборки — копия из репо, без локальных патчей):

1. `Supervertaler.py` — `fe5f706c…` / 55040 (после 9.5e)
2. `modules/llm_clients.py` — `7f2b9ee9…` / 579
3. `modules/settings_service.py` — `08a0d943…` / 599
4. `modules/unified_prompt_manager_qt.py` — `cec2ef68…` / 6833

`modules/quicktrans.py` (`6a6812be…`/1635) в 9.5 не менялся — менять не нужно. После копирования — перепроверка `_pth`/`start.bat` + `py_compile` (решение Дмитрия, вне батча).

---

## §6. Ручные сценарии (для Дмитрия на тестовой сборке)

- **T9.5.1** — AI Settings → Custom-профиль: чекбокс «Model supports vision (image input)» виден, tooltip про «model behind this endpoint accepts images»; новый профиль («+») — unchecked.
- **T9.5.2** — чекбокс → Save → перечитать (перезапуск/открыть вкладку): флаг сохранён; снять → Save → снят. В settings.json у сохранённого профиля есть/нет `supports_vision`.
- **T9.5.3** — профиль с vision=True + сегмент с «See Figure 1A…» (картинка в figure-контексте) → запрос к endpoint уходит с image_url (content-parts); перевод с учётом картинки.
- **T9.5.4** — профиль с vision=False → Image Extractor / figure-перевод / AutoPrompt отказываются слать изображения; текст указывает «tick Model supports vision (image input) … Settings → AI Settings».
- **T9.5.5** — два профиля с разными флагами: поведение следует профилю, реально использованному для запроса (активный профиль; чип QuickTrans с конкретным профилем).
- **T9.5.6** — профиль с пустым endpoint → Save блокируется: предупреждение с именем профиля, комбо выделяет проблемный профиль, settings.json не меняется, вкладка открыта; строка из пробелов — то же.
- **T9.5.7** — старый settings.json без `supports_vision` грузится (флаг = False, файл не переписан); ранее сохранённый профиль с пустым endpoint грузится и НЕ удаляется; Save QuickTrans с пустым MT endpoint работает как раньше (MT не блокируется).

**Вердикт координатора (Дмитрий, 2026-10-14):** T9.5.1 **ПОДТВЕРЖДЕНО**, T9.5.2 **ПОДТВЕРЖДЕНО**, T9.5.3 **ПОДТВЕРЖДЕНО**, T9.5.4 **ПОДТВЕРЖДЕНО**, T9.5.5 **ПОДТВЕРЖДЕНО**, T9.5.6 **ПОДТВЕРЖДЕНО**, T9.5.7 **ПОДТВЕРЖДЕНО** (проверено на тестовой сборке с §5-пакетом). Формальный ACCEPT-вердикт по 9.5 — за Дмитрием.

---

## §7. Что осталось за покрытием

- **Ответ реальной vision-модели — проверен** (замечание координатора 2026-10-15; правка §7): прогон на тестовой сборке с llama.cpp (profile Documents, сегмент #12 «Figure 1A», модель `Qwen3.8-27B-GGUF:UD-IQ2_XXS` / `unsloth/qwen3.8-27b`): лог `D:\SupervertalerPortable_test\Supervertaler\profile\Supervertaler\workbench\logs\supervertaler.log` — «Detected figure references in segment #12: 1a» → «✅ Including 1 figure images: 1a» (с галкой) против «⚠️ … doesn't support vision — tick 'Model supports vision (image input)'…» (без галки); ledger `workbench/usage/usage-2026-10.jsonl` — `source: actual`, `ok: true`, вклад картинки в промпт ≈110 токенов (in_regular 1290 с картинкой против 1179 без). Fake-сервер в спец-пробе (V1) доказывал форму тела запроса (`image_url` + base64-PNG); теперь доказан и реальный ответ модели с учётом картинки.
- **Поведение с картинкой (уточнение Дмитрия, 2026-10-14):** модель использует изображение как **подсказку к переводу** сегмента (контекст к ссылке «Figure N»), а **не** как объект «перевести надписи на рисунке». Режим «извлечь и перевести текст НА рисунке» — отдельная идея (BACKLOG §9.6), не реализована.
- **Попап QuickTrans с изображениями** на уровне UI не гонялся (чип → `create_llm_client(profile_name=…)` → флаг резолвится — покрыто на уровне клиента, V3).
- Границы ЭТАПа 3 не трогались: логика figure-контекста (regex/batch/md-image), Custom MT валидация, авто-детект vision по имени модели, переключение активного профиля в чат-меню, импорт/экспорт профилей, DB-схема, ключи удалённых провайдеров, Local LLM note, кандидаты 8.18.

---

## §8. Вопросы к координатору

- **Q1**: легаси-плоский endpoint (миграция без профилей) получает `supports_vision: False` и в UI-чекбоксе не участвует (плоский путь = синтетический профиль «Custom Endpoint»). Оставить всегда False?
- **Q2**: текст предупреждения «Empty Endpoint» — английский (как остальные диалоги настроек). Ок?
- **Q3**: пустой список профилей разрешён (провайдер может быть выключен) — подтверждение?
- **Q4**: сид 9.4a save-probe дополнен `supports_vision` у активного профиля (audit-артефакт) — принимается как правка артефакта?

**Ответы координатора (Дмитрий, 2026-10-14):**
- **Q1 — Да.** Плоский путь остаётся синтетическим профилем «Custom Endpoint» без чекбокса, `supports_vision` всегда False; ключ при загрузке на диск не записывается. Уже реализовано; проверяется V4 (хеш settings.json до и после загрузки не меняется — в логе спец-пробы).
- **Q2 — Да, через `self.tr()`,** как остальные диалоги настроек, с именем профиля и подсказкой: «Profile "X" has no endpoint. Fill it in or remove the profile». Диалог остаётся открытым, на диск ничего не пишется, проблемный профиль выбирается в списке. Было реализовано иначе (длинный текст без `self.tr()`) → **поправлено в 9.5e** (`0b9c9ad2`).
- **Q3 — Подтверждаю.** Запрет касается только профилей, которые есть в списке и у которых endpoint пуст или из пробелов. Сохранение с нулём профилей легально (статус-бар «Custom profile not configured», QuickTrans без чипов). Явный V6-кейс (удалить все → Save → успех → перезапуск без ошибок) добавлен в спец-пробу в 9.5e.
- **Q4 — Принимается как правка аудит-артефакта,** не продукта. Условие: в отчёте отметить это как изменение артефакта, а старый сценарий «профиль без ключа» сохранить отдельным кейсом. Выполнено в 9.5e: сид с аргументом `modern|legacy`, legacy-сценарий (файл до-9.5) — отдельный кейс в save-пробе и в runner'е; в §4 (пояснение к 9.4a) и §3 (9.5e) зафиксировано.

---

## §9. Находки вне рамок батча (в BACKLOG)

- `modules/pdf_rescue_Qt.py` содержит легаси-клиенты удалённых провайдеров (кандидат 8.18).
- Текст «Sonnet cost ballpark» остался в About/help (кандидат 8.16).
- `load_api_keys` в импорте prompt manager неиспользуем с базы (в 9.5c убран только `LLMClient`; `load_api_keys` оставлен — правка вне объёма).
- **Harness-урок**: `QTimer.singleShot(1500, self._start_okapi_sidecar)` захватывает **bound-метод** в момент планирования → патч экземпляра после конструктора не спасает (таймер уже держит старый метод). Надёжный патч — по **классу** до конструирования: `Supervertaler.SupervertalerQt._start_okapi_sidecar = lambda self: None`. Применено в обеих спец-пробах (9.5 и 9.4i); в 9.4i это спасло T4-ловушку (раньше зелёная только пока прокачка событий не пересекала 1.5 с).
- Строка лога `✗ Error creating termbase: UNIQUE constraint failed` в TB-пробе — предсуществующий артефакт повторного сида (проба завершается REGRESS-TB OK).
- r9-сиды: все endpoint-ы непустые → 9.5d их не блокирует (проверено).

---

## §10. Логи защит (артефакты)

`docs/refactoring/audits/`:
- Спец-проба: `batch9-5_probe_vision_and_endpoint.py` (V1–V8), `batch9-5_probe_special.log` (39/39), `batch9-5_probe_special_b95c.log` (33/39, 6 V6-red), `batch9-5_probe_94i_v7.log` (T1–T5 зелёные, ловушка 0), `batch9-5_probe_special_b95e.log` (**45/45**, +6 V6-Q3).
- Статика per-commit: `batch9-5_static_base.log`, `batch9-5_static_after_b95a/b/c/d.log`, `batch9-5_static_after_b95e.log`.
- Offscreen-обойма per-commit: `batch9-5_suite_base.log`, `batch9-5_suite_b95a/b/c/d.log`, `batch9-5_suite_b95e.log` + отдельные логи проб `batch9-5_probe_b95*_{fb,profiles,qtchat,statusbar_prof,save,r9_a,r9_ctrl,r9_rm}.log`, `batch9-5_probe_b95e_save_legacy.log` (9.5e), `batch9-5_probe_after_b95*_{clean,upgrade}.log`, `batch9-5_regress_after_b95*.log`, `batch9-5_smoke_after_b95*.log`, `batch9-5_tb_after_b95*.log`, `batch9-5_about_after_b95*.log`, `batch9-5_e2e_after_b95*.log`, `batch9-5_seed_b95*.log` (+ `batch9-5_seed_b95e_save_legacy.log`).
- 9.5e suite: regress-хэши `5a12501f…/44828d90…/c413d563…` стабильны; S-clean 30 TREE (31 = grep с заголовком, см. §4); S-upgrade HASH-DIFF пустой; Tools-smoke 42 (PDF-Rescue fitz — предсуществующий); save modern ALL OK + save legacy ALL OK; r9 a/ctrl/rm OK; TB REGRESS-TB OK; About RESULT OK; e2e/qtchat/statusbar/profiles/fallback — без ошибок.
- Рекон: `docs/refactoring/reports/RECON_95.md`.
- **`PROJECT_STATUS.md` обновлён** (требование промпта; коммиты `c6f90fee` и `710febcb`): строка «Обновлено» (9.5 EXECUTED + протестирован Дмитрием, T9.5.1–.7 ПОДТВЕРЖДЕНО, ответы Q1–Q4), секция «Batch #9.5 EXECUTED + протестирован Дмитрием» (5 коммитов, метрики, правки артефактов, AST-границы пересчитаны по `ast.parse` на `0b9c9ad2`), «Кратко» — монолит **55 040**, следующий шаг G5 → 8.18 → 8.16 → 8.17.

**Передача:** Batch #9.5 исполнен (5 коммитов 9.5a–9.5e, защитная обойма зелёная на каждом, спец-проба 45/45, V7-проба 9.4 зелёная). Ручные T9.5.1–T9.5.7 — **все ПОДТВЕРЖДЕНЫ** Дмитрием на тестовой сборке; ответы Q1–Q4 учтены в 9.5e. Формальный ACCEPT-вердикт по 9.5 — за Дмитрием. Агент останавливается и ждёт вердикта координатора. Следующий шаг по плану — G5 (урезанный), затем 8.18, 8.16, 8.17 — по команде Дмитрия и его промпту.
