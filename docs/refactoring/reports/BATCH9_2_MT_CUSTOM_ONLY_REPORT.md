# ОТЧЁТ Batch #9.2 — Machine Translation: только custom MT

**Дата:** 2026-10-11 · **База:** `a6b1097c` (код 9.1b) · **Коммиты:** **fc6e313f** (9.2a), **be82d963**
(9.2b), **513a2fae** (9.2c), **7298ce24** (9.2d), **a39ca9a5** (9.2e), **13e1ad29** (cleanup).
Файлы: `Supervertaler.py`, `modules/quicktrans.py`, `modules/translation_results_panel.py`,
`modules/settings_service.py`. Монолит 56 587 → **55 997** (SHA `287781c1…`, −590).
**«Не пушить» — выполнено.** Рантайм: `openai 3.24.0` установлен Дмитрием (проверено Этапом 0).

---

## §0 Baseline и дрейф

- Дрейф `a6b1097c..HEAD` до старта: только docs (PROJECT_STATUS, batch9-1 аудиты, 8.12-note) — СТОП не сработал.
- Эталоны: `Supervertaler.py` `5cdae632…` / 56 587 / CRLF-only; `quicktrans.py` `0e6ac610…` / 1663 / LF;
  `translation_results_panel.py` `1fc6a7b3…` / 2427 / LF; `settings_service.py` `d76a2816…` / 565 / LF — совпали.
- `import openai` в `E:\Dev\python-embed`: **OK, версия 3.24.0**.
- Baseline: py_compile 110/0 + 160/0; headless 91/2 (setup, pdf_rescue_Qt); pyflakes 577/126/4
  (монолит undefined=0); AST chain 922/0; S-clean 28 OK; S-upgrade HASH-DIFF пуст; regress 6 sha == 8.15;
  smoke 42 OK; TB OK.
- Контроль «ДО»: e2e custom MT через фейк OpenAI-совместимый endpoint на 127.0.0.1 —
  `call_custom_mt('Good morning', …)` → **«Goedemorgen»**, SDK постит `/v1/chat/completions`
  (`batch9-2_e2e_before.log`, `batch9-2_probe_mt_e2e.py`).

## §1 Рекон (по пунктам промпта; границы по AST в координатах 9.1b)

1. **Страница MT Settings:** `_create_mt_settings_tab` (20440–20550, 111), `_save_mt_settings_from_ui`
   (24037–24056, 20), пункт сайдбара 19092–19094. **Индексы не сдвигаются:** все переходы по подписям
   (`_go_to_settings_tab` 48306+ — substring-поиск; хелпер 26040+ — тоже; QuickTrans-индекс
   `mt_quick_lookup_tab_index` считается как `count()-1` в момент добавления 19105 → пересчитывается
   на новой раскладке). Проба подтвердила: 14 → 13 страниц, порядок цел. Строки «MT Settings» в
   сообщениях: 51051 (warning — переформулирован в 9.2b на «Settings → QuickTrans»), 51204
   (No-MT-Provider — переформулирован), 34059/34109 (compare panel «Machine Translation» — остался,
   кормится custom MT), 21629/21928 (General-справка о «MT matches» — концепт остался), 6063/26018
   (комментарии — docs-проход).
2. **Шесть `call_*`:** google 51932–51985, deepl 51987–52059 (ленивый `import deepl`), microsoft
   52061–52116, amazon 52118–52173 (ленивый `import boto3`), modernmt 52175–52225, mymemory
   52227–52276 — 346 строк, удалены 9.2a. Вызывающие: только диспетчер (по 1 разу на ветку),
   `PreTranslationWorker._translate_with_mt` (google/deepl), мёртвый `_REMOVED_…` (2), QuickTrans —
   **по имени строки** (`getattr(self.parent_app, method_name)`, quicktrans.py 344–357) — удалён 9.2c.
3. **Диспетчер `_fetch_mt_translation_async`** (51807–51930): потребитель `_perform_delayed_lookup`
   (40763, Match Panel/assist). Целевое поведение реализовано: активный профиль custom MT; нет
   включённого профиля с endpoint — тихий выход, MT-строка не появляется, ошибок на сегмент нет.
4. **`translate_batch`:** диалог 51001–51053 (список 6 провайдеров → custom MT), ветка исполнения
   51197–51206 (имя фикс. «Custom MT»), provider_info 51243+ без изменений.
5. **`PreTranslationWorker._translate_with_mt`** (5571–5592): выбрал **вариант (а)** — переключить на
   custom MT. Обоснование: воркер уже использует `parent_app` в TM/LLM-режимах
   (`load_api_keys`, `_resolve_provider_model`), новых потоковых рисков нет; `call_custom_mt` сам
   резолвит активный профиль. Ветка-ловушка: строки-ошибки «[…]» мапятся в `None` (как старый путь
   «нет провайдера»), чтобы фейковый текст не вставлялся как перевод. Риски варианта (б) (убрать
   MT-режим) — потеря функциональности предперевода без необходимости.
6. **`_add_mt_and_llm_matches`:** MT-блок 53312–53348 (Google через `get_google_translation`) →
   `call_custom_mt` + код «CMT» (9.2a). LLM-часть и `_clean_provider_prefix` НЕ тронуты (9.3).
7. **QuickTrans:** quicktrans.py 332–362 (6 дефов + цикл по имени) удалены; custom MT (364+, код
   «CMT», чип на профиль) — остался. Монолит-таб: чекбоксы `mtql_gt/dl/ms/at/mmt/mm` (20596–20621)
   удалены, custom MT-секция и реестр `_mtql_checkboxes` целы; `_save_mt_quick_lookup_settings`
   итерирует реестр динамически — мёртвых переключателей нет. `mt_info` переформулирован.
8. **Панель:** тултипы GT/AT/MMT/DL/MS/MM удалены, добавлен «CMT»: «Custom MT» (код уже использовался
   панелью через `provider_code`); docstring-примеры обновлены; PROVIDER_COLORS — мёртвые коды
   удалены, добавлен «CMT» (cleanup 13e1ad29).
9. **settings_service:** дефолты `mt_*` (6 шт., вкл. комментарий 8.15) удалены (9.2e); `llm_*` и
   механизм не тронуты; `custom_mt_profiles/custom_mt_active_profile` остались. Читатели `mt_*`/
   `mtql_*`/MT-ключей — все перечислены в §1.2–1.7; после 9.2a–d читателей нет; старые ключи в
   settings.json остаются инертно (проба legacy: файл с 6 mt_*-ключами читается, старт чистый).
10. **Прочее:** `llm_clients.get_google_translation` и CLI-хелперы НЕ тронуты (9.3);
    `_REMOVED_add_mt_and_llm_matches_progressive` (теперь 52451–52724) и `_save_llm_settings_from_ui`
    — не тронуты (8.18), их grep-попадания зафиксированы как разрешённые остатки;
    `superlookup.py` TODO — docs-проход; MT-ключи страницы AI Settings: их не было (ключи MT жили
    на удалённой MT-странице; `_api_key_inputs` — общий словарь, `_save_api_keys_from_ui` теперь
    перезаписывает только LLM-поля, MT-ключи в файле не трогаются).
11. **Совместимость:** проба legacy — старт без ошибок, ловушка `requests.post/get/request →
    AssertionError` не сработала (ни один удалённый провайдер не вызван), custom MT-ридер жив.

## §2 Что сделано

| Коммит | Файл | Зона (до правки) | Действие | Снапшот (sha256-16) |
|---|---|---|---|---|
| 9.2a | монолит | диспетчер 51807–51930 | переписан: custom MT only, polite no-op, provider_code='CMT' | 96f47b02e6633754 |
| 9.2a | монолит | 51932–52277 | вырез шести `call_*` (346 строк, вкл. ленивые `import deepl/boto3`) | ab1cf64e2f926e16 |
| 9.2a | монолит | MT-блок `_add_mt_and_llm_matches` 53312–53348 | → `call_custom_mt`, код 'CMT' | bc0a811e31bfed37 |
| 9.2b | монолит | avail 51001–51018 | список доступности → custom MT (профиль с endpoint) | (snapshots/b_*) |
| 9.2b | монолит | warning 51051–51053; exec 51197–51206; воркер 5571–5592 | тексты → QuickTrans; имя 'Custom MT'; воркер → `call_custom_mt` | d/w |
| 9.2c | quicktrans.py | 332–362 | вырез 6 дефов + цикла | c_quicktrans_zone_332-362 |
| 9.2c | панель | docstring 36; тултипы 173–182 | коды MT удалены, CMT добавлен | c_panel_tooltips |
| 9.2c | монолит | таб 20592–20620; mt_info 20584 | чекбоксы удалены; текст переформулирован | c_tab_providers_20592-20620 |
| 9.2d | монолит | сайдбар 19087–19089; страница 20435–20545; save 24003–24022 | удалены (−134) | d_sidebar/d_page/d_save |
| 9.2e | settings_service | defaults 347–356 | 6 `mt_*` удалены (−10) | e_defaults |
| cleanup | quicktrans.py; панель | PROVIDER_COLORS; комментарий 169 | −6 мёртвых кодов, +CMT | — |

Все замены — assert count==1 по байтам, EOL сохранены (монолит CRLF 55 997/`\r\r\n`=0; модули LF).

**Методология (находка):** первая попытка 9.2a сделала повторный сплайс по устаревшим номерам
строк и повредила зону Superlookup — поймано py_compile, откат `git checkout` (+ обратная
конверсия LF→CRLF: checkout отдаёт LF при i/lf w/crlf), повтор одним проходом от исходного
снимка. Аналогично в 9.2b первая попытка взяла неверную границу блока доступности (51015 вместо
51018) — откат и повтор. В репо попали только корректные версии; обе ошибки не покидали stage.

## §3 Диффы

`git diff a6b1097c..HEAD -- Supervertaler.py modules/quicktrans.py modules/translation_results_panel.py modules/settings_service.py`:
монолит +79/−669 (итог −590), quicktrans −47/+10, панель −10/+6, settings_service −11/+1.

## §4 Валидация (по коммитам; логи `docs/refactoring/audits/batch9-2_*`)

| Метрика | base | a | b | c | d | e+cleanup | final |
|---|---|---|---|---|---|---|---|
| py_compile канон/справ | 110/0·160/0 | = | = | = | = | = | = |
| headless | 91/2 | = | = | = | = | = | = |
| pyflakes | 577/126/4 | = | = | = | = | = | = |
| AST chain | 922/0 | 922/0 | 922/0 | 922/0 | **907**/0 | 907/0 | 907/0 |
| S-clean / S-upgrade | OK/пуст | = | = | = | = | = | = |
| regress 6 sha | ==8.15 | = | = | = | = | = | = |
| smoke / TB / About | OK | = | = | = | = | = | = |

Снижение chain 922 → **907 (−15)** — резолв-цели удалённых методов (страница+save), ожидаемо
по промпту; unresolved = 0 на каждом шаге. Grep-гейт финальный: `call_*`, `_create_mt_settings_tab`,
`_save_mt_settings_from_ui`, `mtql_*`, коды GT/DL/MS/AT/MMT/MM, `import deepl/boto3` — **0 в
modules/ и 0 в монолите вне мёртвого `_REMOVED_add_mt_and_llm_matches_progressive`** (52451–52724,
проверено AST-принадлежностью) и docs/audits.

**Спец-пробы:**
- **e2e custom MT**: «ДО» = «ПОСЛЕ» на одном входе: «Goedemorgen» (`call_custom_mt`, тот же метод,
  что зовёт лямбда QuickTrans); диспетчер-проба: фейк-сервер получил POST `/v1/chat/completions`
  (панельная ветка требует assistance_widget — как в baseline, гард сохранён).
- **empty**: диспетчер — тихий выход; `_get_active_custom_mt_profile()` = None; пакетный вариант
  MT недоступен; QuickTrans MT-чипов нет. Без падений.
- **legacy-trap**: старый settings.json (6 mt_*-флагов, 5 MT-ключей, mtql_*) — старт чистый;
  ловушка сети не сработала; старые mt_*-ключи остаются в файле инертно (загружаются как есть,
  читателей нет); QuickTrans MT-чипы = [].
- **tabs**: QuickTrans-таб — чекбоксов удалённых провайдеров нет, custom MT-чекбокс есть;
  AI-таб — комбо профилей и Save целы (9.1 не задет).
- **страницы**: 14 → 13, полный список в логе `batch9-2_probe_final_clean.log`, порядок цел.

## §5 Пакет для тестовой сборки

Заменить 4 файла, ничего не удалять:
- `Supervertaler.py` — **287781c1e77687c8ad45baf7612e3732a7290e01749ef263be388939b26b28c0** (55 997)
- `modules/quicktrans.py` — **6e3e23f3293c01460b312a8072b7e79e2f1bde6ef795d5238906a1b373f5ae70** (1627)
- `modules/translation_results_panel.py` — **317a56779a8b0e3e8491339aa0c60e078d7ebcabf2aaad3edc5a0889016322f2** (2422)
- `modules/settings_service.py` — **3d883246ac74b3e8e1048b50eba9e7d347622da70740115bd831651e2334a064** (555)

## §6 Сценарии ручного тестирования T9.2.x (на КОПИИ user_data)

- **T9.2.1** В Settings нет страницы «🌐 MT Settings» (13 страниц), остальные открываются, порядок как раньше.
- **T9.2.2** QuickTrans (Ctrl+Alt+Q): в MT только custom MT-чипы; перевод через локальный
  custom MT endpoint работает; при пустом профиле — чипа нет и ошибок нет.
- **T9.2.3** Match Panel: LLM-строки как раньше; MT-строка появляется от custom MT (код «CMT»),
  если профиль настроен и включён.
- **T9.2.4** Диалог пакетного перевода: MT-вариант — только «Custom MT»; без настроенного профиля
  вариант неактивен с подсказкой «Settings → QuickTrans».
- **T9.2.5** Апгрейд-копия со старыми MT-флагами/ключами: старт без ошибок; ключи в файле не тронуты.
- **T9.2.6** Общий smoke: .svproj, txt/md/docx, TMX, выход.

## §7 Непокрытые проверки и находки

1. Полный прогон пакетного перевода через MT (LiveProgressDialog + воркер) автоматической пробой
   не покрыт (нужен реальный .svproj/сегменты) — вручную T9.2.4; воркер-путь проверен статически
   (замена метода) + общий regress/smoke.
2. QuickTrans-попап полностью (клик по чипу) не автоматизирован — проверен провайдер-сборщик
   (`_get_enabled_providers`) и e2e `call_custom_mt`; вручную T9.2.2.
3. `_perform_delayed_lookup` «MT»-категория в matches_dict осталась (пустая без профиля) — не
   мёртвый код: наполняется диспетчером при настроенном custom MT.
4. Мёртвые `_REMOVED_…` и `_save_llm_settings_from_ui` дают фоновые grep-попадания — разрешённые
   остатки, очередь 8.18 (запись Дмитрия о `_save_llm_settings_from_ui` в силе).
5. Методология: `git checkout` отдаёт монолит в LF (i/lf w/crlf) — после откатов требуется
   обратная конверсия в CRLF; в отчётах 9.1 этого не требовалось (откатов не было).

## §8 Вопросы к Дмитрию

Нет блокирующих. К сведению для 9.3: Image Extractor AI-функция (`_build_image_extract_ai_callback`
9988–10196 в координатах R9) — список мест для перевода на custom_openai подготовлен в R9 §2.2/§2.6.

## Handover

Дальше — **9.3: облачные LLM + Ollama + молчаливая миграция provider** (зоны в R9 §Ч3/§2.3);
старт только по команде Дмитрия и его промпту. В dev-runtime теперь есть `openai` 3.24.0 —
фейк-endpoint пробы войдут в защитный набор. Не пушить до команды.
