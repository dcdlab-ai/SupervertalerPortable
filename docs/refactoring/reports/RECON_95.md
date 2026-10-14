# RECON Batch #9.5 — vision как свойство профиля + запрет пустого endpoint

Дата: 2026-10-14. База: HEAD 575bd419. Read-only.

## A. Карта vision

### Определения (modules/llm_clients.py)
- `LLMClient.VISION_MODELS = {}` (стр. 149) — пустой whitelist после 9.3.
- `LLMClient.model_supports_vision(cls, provider, model_name)` (стр. 156–169) — **classmethod**,
  читает `VISION_MODELS.get(provider, [])`, возвращает `model_name in список` → всегда False.

### Потребители гейта (4 вызова, все — classmethod-вызов `LLMClient.model_supports_vision(provider, model)`)

| # | Место | Функция | Что гейтит | Откуда provider/model | Контекст профиля/клиента в точке вызова |
|---|-------|---------|-----------|----------------------|----------------------------------------|
| 1 | llm_clients.py:471 | `translate_with_usage` | `images` → `None` (молчаливый сброс перед запросом) | `self.provider`, `self.model` | **есть**: экземпляр клиента (`self`) |
| 2 | Supervertaler.py:9901 | `_build_image_extract_ai_callback` (Image Extractor, Gate 3) | шаг «🤖 AI label»: диалог «vision не включён», далее text-only / Cancel | `llm_client.provider/model` из `prompt_manager_qt.chat_backend.llm_client` | **есть**: экземпляр `llm_client` в scope |
| 3 | Supervertaler.py:48891 | `translate_current_segment` (figure-context) | прикладывание изображений фигур к переводу сегмента | локальные `provider`/`model` (48707/48710); клиент создан на 48737 через `create_llm_client` | **есть**: `client` в scope (try-блок после 48737) |
| 4 | unified_prompt_manager_qt.py:4458 | `_collect_autoprompt_images` (Gate 3) | vision-aware AutoPrompt: предупреждающий диалог, text-only / sentinel-отмена | `chat_backend.llm_client.provider/model` | **есть**: экземпляр `llm_client` в scope |

**Вывод:** все 4 точки имеют экземпляр клиента → экземплярный флаг `client.supports_vision` применим везде.
Условие СТОП 1 (более 2 мест без контекста профиля) — **НЕ** достигнуто (0 мест).

### Прочие вхождения «vision» (не потребители гейта)
- `modules/pdf_rescue_Qt.py` (7 вхождений) — собственные клиенты OpenAI/Anthropic/Gemini
  (`api_keys.get('openai')` и т.п.), к `LLMClient`/`VISION_MODELS` не обращается. **Вне объёма 9.5.**
- `modules/image_extractor.py` (3) — только docstring-тексты про vision-AI fallback.
- `Supervertaler.py:9537–9560` — tooltip чекбокса «🤖 AI label»: текст «Vision-capable model in
  Settings (Claude Sonnet/Opus 4.x, GPT-4o or newer, Gemini)» — упоминает удалённых провайдеров →
  правка текста в 9.5c.
- `unified_prompt_manager_qt.py:2373–2395` — tooltip «🖼️ Include loaded figure images»: те же
  упоминания → правка текста в 9.5c.
- `unified_prompt_manager_qt.py:4392–4393` — сообщение после отмены AutoPrompt («switching to a
  vision-capable model») → правка текста в 9.5c.
- `Supervertaler.py:9948–9957` — cost-эстимейт по именам моделей (opus/sonnet/gemini) —
  8.18-кандидат, **не трогать**.
- `Supervertaler.py:48893–48895` — мёртвая gemini-ветка в figure-гейте (provider всегда
  custom_openai) — 8.18-кандидат, **не трогать** (в объёме 9.5c меняется только условие гейта).
- `unified_prompt_manager_qt.py:130` — комментарий конструктора запроса.

### Вызовы без экземпляра клиента
Все 4 — статические (`LLMClient.model_supports_vision(...)`), но экземпляр клиента доступен во всех
точках (см. таблицу) → экземплярный флаг применим без рефакторинга вызовов.

### Потребители VISION_MODELS
Только `model_supports_vision` (тот же класс). В продукте — 0 внешних потребителей.
Исторические аудит-скрипты (не входят в обойму, не правятся):
`batch8-15_probe_e03.py` (monkeypatch метода), `batch9-3_check_93d_matrix.py` (assert False для всех).
→ **VISION_MODELS + classmethod удаляются** (после перевода 4 гейтов на экземплярный флаг —
0 потребителей в коде продукта).

## B. Формирование запроса с images

`_call_openai_with_usage` (llm_clients.py:538–542) строит content-parts ровно в ожидаемом формате:

```python
content = prompt
if images:
    content = [{"type": "text", "text": prompt}]
    for img_ref, img_base64 in images:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})
```

`images` — список кортежей `(ref, base64_png)`; поставщики: figure-context
(`pil_image_to_base64_png`) и AutoPrompt (тот же конвертер). messages: system + user(content).
**Формат корректен, правка не требуется (0 строк).** Условие СТОП 4 — не достигнуто.

## C. Структура профиля: создание / чтение / сериализация / копирование

Места словаря профиля `{name, endpoint, model, api_key}`:

1. **Создание:**
   - `_add_custom_profile` (Supervertaler.py:19425): `{'name','endpoint','model','api_key'}` — сюда
     добавить `'supports_vision': False`.
   - settings_service.py:295–300 — миграция legacy-конфига в профиль при загрузке — добавить
     `'supports_vision': False`.
   - `_get_active_custom_profile` legacy-fallback (Supervertaler.py:47530–47532) — synthetic-профиль
     из плоских полей — добавить `'supports_vision': False`.
2. **Чтение UI (AI Settings, `_create_ai_settings_tab`):**
   - `_populate_profile_fields` (19377–19388) — заполняет endpoint/model/key из выбранного профиля →
     добавить установку чекбокса vision (`p.get('supports_vision', False)`).
   - `_sync_fields_to_profile` (19397–19404) — пишет поля обратно в live-список при editingFinished →
     добавить запись флага чекбокса.
   - `_save_ai_settings_from_ui` (23045–23056) — финальный синк активных полей в `profiles[idx]` →
     добавить флаг.
3. **Чтение фабрики:**
   - `_get_active_custom_profile` (47501–47534) — возвращает `dict(p)` (копию) → ключ проходит
     автоматически; нормализация флага — в фабрике.
   - `create_llm_client` (47657–47684) — читает endpoint/model/api_key профиля → добавить
     `supports_vision = v if isinstance(v, bool) else False` и передать в `LLMClient(...)`.
   - `_custom_llm_ready` — не читает флаг (гейт «не настроено»), не меняется.
4. **QuickTrans:** читает профили только для CUS-чипов (quicktrans.py:364+); `_call_llm_translation`
   идёт через `create_llm_client` (profile_name прокидывается, 9.4f) → флаг резолвится фабрикой.
   Прямой конструктор LLMClient в quicktrans.py:435 — fallback без parent_app (в приложении не
   используется, parent_app есть всегда) — флаг там False по умолчанию (дефолт конструктора).
5. **chat_backend.py:147** — клиент через фабрику → флаг резолвится фабрикой.
6. **workers/proofread.py:83** — прямой `LLMClient(...)` из параметров воркера (api_key/provider/model/
   base_url), изображений не шлёт → флаг False по умолчанию, не меняется.

**Нормализация при чтении:** отсутствующий/не-bool → False (`isinstance(v, bool)`). Файл при загрузке
НЕ переписывается (load_llm_settings мутирует только in-memory defaults; список профилей не трогает).

## D. Сохранение и валидация endpoint

- Кнопка «💾 Save AI Settings» (19854) → лямбда → `_save_ai_settings_from_ui` (23019).
- Первый запись на диск — `self.save_llm_settings(new_settings)` (23080); далее
  `save_provider_enabled_states` (23091), `save_general_settings` (23135), `_save_api_keys_from_ui`
  (23147).
- **Валидация возможна в начале `_save_ai_settings_from_ui`, до любой записи на диск, без переработки
  структуры диалога.** Условие СТОП 2 — не достигнуто.
- Источник endpoint'ов на момент валидации: live-снимок `custom_profiles_snapshot` (мутируется
  кнопками +/− и `_sync_fields_to_profile`); активный профиль — текущий текст
  `custom_endpoint_input.text()` (синк полей в функции происходит на 23049–23051, т.е. валидация
  должна читать поле сама).
- **Пустой endpoint:** `text.strip()` пуст (только пробелы = пусто). Проверять ВСЕ профили live-списка
  (не только активный): у неактивных — значение из snapshot (strip), у активного — текст поля.
- **Поведение при пустом (предложение):** `QMessageBox.warning(self, "Empty Endpoint", ...)` с именем
  проблемного профиля; `custom_profile_combo.setCurrentIndex(idx)` (выбрать проблемный профиль);
  `return` — на диск ничего не пишется, вкладка настроек остаётся открытой.
- Уже существующие в settings.json профили с пустым endpoint: загрузка толерантна
  (`_get_active_custom_profile` возвращает их как есть; `_custom_llm_ready` не пропускает запросы),
  профиль НЕ удаляется. Save с пустым endpoint блокируется только для профилей, видимых в UI сессии
  (live-список) — т.е. и для уже сохранённых тоже (они в списке). Это соответствует решению.

## E. Custom MT endpoint (раздел MT) — описание, не менять

`_save_mt_quick_lookup_settings` (20131) пишет `custom_mt_profiles` без валидации endpoint; пустой
endpoint разрешён. `call_custom_mt` (47564+) при пустом endpoint возвращает
`"[Custom MT: no endpoint configured]"` без сетевого запроса. Проблема та же по структуре, но по
решению промпта **не трогается**.

## Условия СТОП — сводка

1. Vision-гейт без контекста профиля > 2 мест — **НЕТ** (0).
2. Валидация Save невозможна без перестройки — **НЕТ**.
3. Неожиданные потребители VISION_MODELS — **НЕТ** (в продукте; 2 исторических аудит-скрипта).
4. Правка формата images > ~30 строк — **НЕТ** (0 строк, формат корректен).

→ Продолжаем, СТОП не объявлен.

## План правок по коммитам

- **9.5a** (llm_clients.py + Supervertaler.py фабрика + settings_service миграция):
  `LLMClient.__init__(..., supports_vision: bool = False)` → `self.supports_vision`;
  гейт 471 → `self.supports_vision`; удалить `VISION_MODELS` + classmethod `model_supports_vision`;
  `create_llm_client` прокидывает флаг профиля (isinstance-нормализация); legacy-fallback и
  миграция — `'supports_vision': False`.
- **9.5b** (Supervertaler.py, зона AI Settings): чекбокс «Model supports vision (image input)» +
  tooltip; populate/sync/add/save-участие; новый профиль — без галки.
- **9.5c** (Supervertaler.py гейты 2/3 + upm гейт 4 + тексты): гейты берут `client.supports_vision`
  (экземпляр); тексты отказов/tooltip'ы — без удалённых провайдеров, с указанием
  Settings → AI Settings → профиль.
- **9.5d** (Supervertaler.py `_save_ai_settings_from_ui`): валидация пустого endpoint всех профилей
  live-списка до записи на диск; warning с именем; выбор профиля; return.
