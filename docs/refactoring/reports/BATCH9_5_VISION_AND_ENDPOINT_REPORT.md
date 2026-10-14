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

Финальное состояние (для пакета тестовой сборки, §5):
- `Supervertaler.py` — SHA256 `9e7a308075727422a81504c69b6f67e3507ed73dd9ba68ab69280c85c0726e58`, 55042 строки (CRLF)
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

---

## §4. Метрики защит (на каждый коммит; полная таблица логов — §10)

| Метрика | база (9.4i) | 9.5a | 9.5b | 9.5c | 9.5d |
|---------|------------|------|------|------|------|
| AST chain (calls/unresolved) | 871/0 | 871/0 | 873/0 (+2 self.tr чекбокса, оба резолвятся) | 873/0 | 873/0 |
| pyflakes warnings | 549 | 549 | 549 | 548 (−1 удалён неиспользуемый импорт LLMClient) | 548 |
| pyflakes undefined (lines/names) | 126/4 | 126/4 | 126/4 | 126/4 | 126/4 |
| py_compile канон (вне docs/) | 109/0 | 109/0 | 109/0 | 109/0 | 109/0 |
| headless imports | 90/2 (setuptools, fitz) | 90/2 | 90/2 | 90/2 | 90/2 |
| grep-гейт 8 файлов | CLEAN | CLEAN | CLEAN | CLEAN | CLEAN |
| offscreen-обойма (S-clean/S-upgrade/regress/smoke/TB/About/save/r9×3/e2e/qtchat/statusbar/profiles/fallback) | зелёная | зелёная | зелёная | зелёная | зелёная |
| спец-проба probe_95 (V1–V8) | — | — | — | 33/39 (6 FAIL = V6, фича не готова) | **39/39** |

Regres-хэши стабильны на всех коммитах: `5a12501f…` / `44828d90…` / `c413d563…`; S-clean 31 TREE; S-upgrade HASH-DIFF пустой; Tools-smoke 42.

**Пояснения к отклонениям:**
- chain 871→873 (9.5b): ровно +2 вызова `self.tr()` (label + tooltip чекбокса в `_create_ai_settings_tab`), оба резолвятся — diff JSON before/after: added 2, removed 0.
- pyflakes 549→548 (9.5c): −1 = удалённый неиспользуемый импорт `LLMClient`; множество undefined имён идентично (126 строк / 4 имени, все в `tmx_editor.py`).
- 9.4a save-probe: с 9.5b Save легитимно дописывает `supports_vision` активному профилю → строгая dict-проверка «profiles preserved» требовала seed с ключом. Сид-скрипт (audit-артефакт, редактируемый) дополнен `supports_vision: False` у активного профиля → ALL OK. r9-сиды и сиды 9.4f/9.4i правки не потребовали (все endpoint-ы непустые; 9.4f/9.4i кликают только «Save QuickTrans», 9.5d их не касается).

---

## §5. Пакет для тестовой сборки

Файлы для обновления в `D:\SupervertalerPortable_test\SupervertalerPortable\` (по правилам замороженной сборки — копия из репо, без локальных патчей):

1. `Supervertaler.py` — `9e7a3080…` / 55042
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

---

## §7. Что осталось за покрытием

- **Ответ реальной vision-модели** не проверялся: fake-сервер возвращает текст; доказано лишь то, что тело запроса содержит `image_url` с base64-PNG (V1) и что гейты его не срезают при флаге.
- **Попап QuickTrans с изображениями** на уровне UI не гонялся (чип → `create_llm_client(profile_name=…)` → флаг резолвится — покрыто на уровне клиента, V3).
- Границы ЭТАПа 3 не трогались: логика figure-контекста (regex/batch/md-image), Custom MT валидация, авто-детект vision по имени модели, переключение активного профиля в чат-меню, импорт/экспорт профилей, DB-схема, ключи удалённых провайдеров, Local LLM note, кандидаты 8.18.

---

## §8. Вопросы к координатору

- **Q1**: легаси-плоский endpoint (миграция без профилей) получает `supports_vision: False` и в UI-чекбоксе не участвует (плоский путь = синтетический профиль «Custom Endpoint»). Оставить всегда False?
- **Q2**: текст предупреждения «Empty Endpoint» — английский (как остальные диалоги настроек). Ок?
- **Q3**: пустой список профилей разрешён (провайдер может быть выключен) — подтверждение?
- **Q4**: сид 9.4a save-probe дополнен `supports_vision` у активного профиля (audit-артефакт) — принимается как правка артефакта?

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
- Спец-проба: `batch9-5_probe_vision_and_endpoint.py` (V1–V8), `batch9-5_probe_special.log` (39/39), `batch9-5_probe_special_b95c.log` (33/39, 6 V6-red), `batch9-5_probe_94i_v7.log` (T1–T5 зелёные, ловушка 0).
- Статика per-commit: `batch9-5_static_base.log`, `batch9-5_static_after_b95a/b/c/d.log`.
- Offscreen-обойма per-commit: `batch9-5_suite_base.log`, `batch9-5_suite_b95a/b/c/d.log` + отдельные логи проб `batch9-5_probe_b95*_{fb,profiles,qtchat,statusbar_prof,save,r9_a,r9_ctrl,r9_rm}.log`, `batch9-5_probe_after_b95*_{clean,upgrade}.log`, `batch9-5_regress_after_b95*.log`, `batch9-5_smoke_after_b95*.log`, `batch9-5_tb_after_b95*.log`, `batch9-5_about_after_b95*.log`, `batch9-5_e2e_after_b95*.log`, `batch9-5_seed_b95*.log`.
- Рекон: `docs/refactoring/reports/RECON_95.md`.

**Передача:** Batch #9.5 исполнен (4 коммита, защитная обойма зелёная на каждом, спец-проба 39/39, V7-проба 9.4 зелёная). Ручные T9.5.1–T9.5.7 — за Дмитрием на тестовой сборке (§5 пакет). Агент останавливается и ждёт вердикта координатора. Следующий шаг по плану — G5 (урезанный), затем 8.18, 8.16, 8.17 — по команде Дмитрия и его промпту.
