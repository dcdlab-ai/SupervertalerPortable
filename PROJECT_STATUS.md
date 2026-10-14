# PROJECT_STATUS.md

**Точка входа для актуального состояния проекта.** Обновляется в конце каждого шага/батча —
читать этот файл вместо повторного просмотра всех документов. Подробности каждого шага — в
`EXTRACTION_PLAN.md` (секции «Статус Step N после Batch #X») и `docs/refactoring/`.

**Обновлено:** 2026-10-14 (Batch #9.5 **EXECUTED** (4 коммита 9.5a–9.5d, отчёт `docs/refactoring/reports/BATCH9_5_VISION_AND_ENDPOINT_REPORT.md`; база 575bd419/код 2e9dd938): vision как свойство профиля `supports_vision` (без whitelist имён) — чекбокс «Model supports vision (image input)» в Custom-профиле AI Settings, все 4 vision-гейта берут флаг реально используемого клиента, VISION_MODELS/model_supports_vision удалены; запрет сохранения Custom LLM-профиля с пустым endpoint (warning с именем профиля, комбо выделяет, файл не меняется; Custom MT не трогается); спец-проба probe_95_vision_and_endpoint 39/39 + 9.4i-проба зелёная (V7); монолит 54 992 → **55 042** (SHA `9e7a3080…`), llm_clients 597→579, settings_service 598→599; ручные T9.5.1–.7 и вердикт — за Дмитрием; **следующий шаг — G5 (урезанный), затем 8.18 → 8.16 → 8.17 — по команде Дмитрия и его промпту**) • 2026-10-14 (Batch #9.4 **EXECUTED + протестирован Дмитрием**: 6 коммитов 9.4a–9.4f + follow-up **9.4g `f6f98538`** (Custom MT endpoint: нормализация схемы при Save таба QuickTrans + на чтении в call_custom_mt — авторизованная ЗАМЕТКА Дмитрия, как в AI Settings 9.1b) + **9.4h `3f9554dd`** (попап с пустым списком профилей QuickTrans → чип глобального активного профиля из AI Settings — уточнение Дмитрия 2026-10-13: «когда отключены/удалены профили в QuickTrans, попап должен работать с глобальным активным профилем, как с единственно оставшимся»; баг 9.4f: mtql_llm_profiles=[] давал ноль чипов; правка в quicktrans._add_llm_providers, probe_94h_fallback 5 сценариев зелёные) + **9.4i `064c2bbf`+`2e9dd938`** (решение Дмитрия 2026-10-14: мастер-чекбокс «Custom (OpenAI-Compatible)» (`mtql_custom_openai`) в табе QuickTrans убран — LLM-чипы в попапе есть всегда, чекбоксы профилей выбирают чипы, при пустом/устаревшем списке работает глобальный активный профиль (9.4h); read-only поле модели активного профиля удалено вместе с мастером; старый ключ `mtql_custom_openai` в settings.json инертен (Save переносит без изменений, не читается); баг «9.4h не работает» (скриншот: мастер снят → попап пуст) устранён; спец-проба probe_94i_master_removed зелёная, в т.ч. скриншот-сценарий «strata» и ловушка сети; новый сценарий T9.4.12 — **ПОЛНОЕ ПОДТВЕРЖДЕНИЕ (Дмитрий, 2026-10-14)**); тесты: **T9.4.1–.5, .7–.11 ПОДТВЕРЖДЕНО (T9.4.11 — 2026-10-13); T9.4.6 ПОДТВЕРЖДЕНО с ЗАМЕЧАНИЕМ → исправлено 9.4h; Q4 ПОДТВЕРЖДЕНО (статус-бар = глобальный активный профиль)**; ЗАМЕЧАНИЕ по попапу: в коде репозитория попап переводит через Custom (пробы popup/scheme-less зелёные), бесcхемный endpoint на frozen-сборке 960be5d8 (до 9.1b) не работал — пересборка пакета решает; ЗАМЕТКИ Дмитрия внесены в BACKLOG §9.3 (импорт/экспорт профилей), §9.4 (переключение активного профиля в чат-меню), §9.5 (запрет сохранения профиля без endpoint); монолит 55 703 → 55 000 → 55 004 → **54 992** (SHA `fb3dce5c…`), quicktrans.py 1628 → 1642 → **1635** (SHA `6a6812be…`); формальный вердикт — за Дмитрием) • 2026-10-11 (Batch #8.15 **ПРИНЯТ** — вердикт Дмитрия: T8.15.1 (About) / T8.15.5 (массовый Write) / T8.15.6 (MyMemory OFF) / T8.15.7 (smoke) — ПОДТВЕРЖДЕНЫ; T8.15.2 не тестировался («функция проверки обновлений не нужна» — удаление в P1); T8.15.3/.4 (vision e2e) не тестировались — функция не работает с локальными провайдерами/моделями. Pillow на тестовой сборке: **12.3.0** (протокол). Находка: vision привязан к точному whitelist `VISION_MODELS` (llm_clients.py:374) — custom_openai/ollama отсутствуют → всегда «doesn't support vision»; у ollama `_call_ollama` не принимает images вовсе. Решения: ремонт vision для **Custom (OpenAI-Compatible API)** — в план работ (BACKLOG §9.1, варианты: паттерн/галка/whitelist); **Ollama — не ремонтировать** (провайдер использоваться не будет); **облачные провайдеры — не в приоритете**; **проектный приоритет — локальные провайдеры OpenAI-Compatible API и модели**. Новая фича: **TMs «Project» → «Set as Project TMs»** по аналогии с «Set as Project Termbase» (сейчас новые записи пишутся во все подключённые TM) — BACKLOG §9.2 с контекстом рекона. Монолит **54 992** после 9.4+9.4g+9.4h+9.4i (SHA `fb3dce5c…`; 55 004 после 9.4g/9.4h, 55 000 после 9.4a–f, 55 703 после 9.3, 55 997 после 9.2, 56 587 после 9.1, 56 524 до 9.1); quicktrans.py 1628 → 1642 → **1635** (SHA `6a6812be…`); пакет тестовой сборки 9.4 — 8 файлов (§5 отчёта BATCH9_4: Supervertaler.py `fb3dce5c…` (после 9.4i; был `a3ced13d…`), quicktrans.py `6a6812be…` (после 9.4i; был `c443c5e8…`), chat_view_widget.py `47e4def0…`, llm_clients.py `1e64c2f1…`, llm_pricing.py `e46f6c76…`, help_system.py `805c3971…`, setup.py `644e1986…`, + УДАЛИТЬ modules/local_llm_setup.py `c08b7704…`); 8.15: E-01/E-02/E-03a+b/8.15f/W/M — все коммиты и пробы в отчёте; AST chain 922/0, pyflakes undefined в монолите 0, S-clean/S-upgrade/regress/smoke/TB идентичны baseline) • **Текущий шаг:** серия Batch #8: 8.1–8.5 ✓, 8.7 ✓, 8.10 ✓, 8.8 ✓, 8.9 ✓, 8.11 ✓, 8.12 ✓, 8.13 ✓, **8.15 ✓ (ПРИНЯТ)**. Ключевые решения (актуальные): 17 модулей-сирот удалены (8.12); UI TM-бриджа удалён (8.13a), колонка БД `bridged_to_trados` остаётся навсегда, сеттер — кандидат модульного прохода 8.18; GNU gettext удалён целиком (8.13b); `Project.po_source_path` и прочие CAT-поля — инертные, «оставить» (финальный проход); 8.15: сломанный дубль show_about удалён, err_text-захват в отложенном on_err, vision-путь оживлён (E-03a+b + 8.15f ImageTk=None), массовый Write → `set_read_only` + инвалидация кэша, MyMemory default OFF для новых установок; удаление check_for_updates (функция+пункт меню+кнопка) → рекогносцировка **P1**; 63 мёртвых метода монолита — батч **8.18** группами по 10–15 + модульный проход по modules/ (`set_bridged_to_trados`, tkinter-остатки `update_ui_display`/`_update_thumbnails`); запись Дмитрия 2026-10-11: мёртвый `_save_llm_settings_from_ui` (в списке 63) всё ещё содержит старый код сохранения с багом профилей — **удалять в 8.18, не оживлять** (иначе баг вернётся; см. предупреждение в BATCH8_12_ORPHAN_INVENTORY_REPORT.md §H); зависимости — в P2; app_target «Trados only» и режим `'trados'` — окончательно; po_handler-записи в CODE_MAP/DEPENDENCY_MAP → 8.17; docs-комментарии в коде → 8.16. **Приоритеты проекта: локальные провайдеры OpenAI-Compatible API и модели — в приоритете; облачные провайдеры — НЕ в приоритете (решение Дмитрия 2026-10-11).** **Решение Дмитрия (R9, 2026-10-11): удалить ВСЕ жёстко зашитые облачные провайдеры (OpenAI/Anthropic/Gemini/Mistral/DeepSeek/OpenRouter) и страницу MT Providers; остаются Custom (OpenAI-Compatible) с профилями, Local LLM на коде Custom, custom MT в QuickTrans; Token Usage остаётся счётчиком.** **План R9 (содержание авторизовано ответами 1–5 от 2026-10-11): 9.1 фикс профилей Custom ✓ ПРИНЯТ (T9.1.1–.6 все ПОДТВЕРЖДЕНЫ, 2026-10-11) → 9.2 MT (custom-only) ✓ ПРИНЯТ (T9.2.1–.6 все ПОДТВЕРЖДЕНЫ, 2026-10-11) → 9.3 облачные LLM + Ollama + молчаливая миграция provider ✓ EXECUTED (4 коммита, отчёт BATCH9_3; тесты Дмитрия 2026-10-13: 9 из 11 ПОДТВЕРЖДЕНЫ, T9.3.4 снят, T9.3.9 уточнить; формальный вердикт за Дмитрием) → 9.4 Settings/QuickTrans/Local LLM ✓ EXECUTED (6 коммитов 9.4a–9.4f, отчёт BATCH9_4, 2026-10-13: UI удалённых провайдеров удалён, профильный выбор Custom в QuickTrans; ручные T9.4.1–.11 и вердикт за Дмитрием) → 9.5 vision-чекбокс в профиле; старт каждого — только по команде Дмитрия и его промпту.** **Дальше (каждый шаг — только по команде Дмитрия и его промпту): порядок 9.x относительно 8.18 → 8.16 → 8.17 — за Дмитрием; новые фичи — BACKLOG §9.2 (Set as Project TMs); G5-аудит figure-context.**

**Batch #8.13 ПРИНЯТ** (2026-10-10, тесты T8.13.1–T8.13.9 на тестовой сборке; отчёт `docs/refactoring/reports/BATCH8_13_TM_BRIDGE_AND_GETTEXT_REPORT.md` §9): коммиты **350e63a8** (часть A: TM Bridge UI — колонка «Bridge», чекбоксы, bulk-кнопки, `toggle_all_bridge`/`on_bridge_toggle`, tooltips, комментарии; ренумбер колонок SuperLookup 6→5, Last Modified 7→6, Description 8→7, ширины и header-sync; 11+/81−) и **41b7ece1** (часть B: GNU gettext — пункты меню Import/Export с разделителями без двойных, методы `import_po_file`/`export_po_file` (228 строк, дефект `@staticmethod` ушёл вместе с ними), `git rm modules/po_handler.py` (566), фильтры «PO (gettext)»/`*.po` из Quick Count и Import Document, `okapi_exts`, формат-списки в docstring/tooltip; 5+/255−, −566). Защищённое не тронуто: колонка БД `bridged_to_trados` (никогда не удалять) + `set_bridged_to_trados` (сеттер 29 строк — кандидат модульного прохода 8.18), `Project.po_source_path` (оставить по правилу CAT-полей, решение — в финальном проходе), `_BILINGUAL_ORIGIN_ATTRS`, TMX, Okapi-механизм, схема БД. Решения §9.3: smoke-таблица каноническая — `audits/batch8-13_code_tools_smoke.py` (42 пункта, без gettext; старая 8.12 — историческая, не трогать; baseline-прогон `batch8-13_code_smoke_baseline813.log`); po_handler-записи в CODE_MAP/DEPENDENCY_MAP → 8.17; py_compile — два счёта: канонический (код вне docs/, на f804d447 = 115) + справочный, сравнение всегда на одном наборе, критерий 0 ошибок (правило в AGENTS.md). T8.13.3 «Select All Write» НЕПОДТВЕРЖДЕНО — **изначальный баг** (§9.2, починен в 8.15d). Монолит **57 009 → 56 689** (SHA `30799778…`).

**Batch #8.15 ПРИНЯТ** (2026-10-11; отчёт `docs/refactoring/reports/BATCH8_15_HIDDEN_BUGS_REPORT.md`, §9 — вердикт): база 41b7ece1; 6 кодовых коммитов: **30cde089** 8.15a (E-01: вырез затенённой сломанной копии `show_about` 48584–48755 — тело от TMX-импорта, 15 pyflakes-undefined + redefinition; живая копия не тронута, About-проба до/после байтно идентична; −172), **c2c9bafb** 8.15b (E-02: `err_text = str(e)` в except → `show_offline_error(err_text)` в отложенном `on_err`; NameError воспроизведён на baseline-worktree; +1), **c183508f** 8.15c (E-03a+b: локальные импорты `LLMClient` и `pil_image_to_base64_png` в vision-try по образцам ~10027/~10122; проба: openai/claude/custom_openai — base64-png, gemini — PIL.Image; на baseline images=null у всех 4; +3), **feeecdd4** 8.15d (W: `toggle_all_write` → реальный `set_read_only(tm_id, not checked)`, hasattr снят, инвалидация кэша как в `toggle_all_read`; проба 3 TM — OK; +3), **adcebd47** 8.15e (M: `'mt_mymemory': False` в defaults `SettingsService`; пробы чистый/true/false — OK; +4), **4ed6eba4** 8.15f (ImageTk отделён от PIL-импорта — `ImageTk=None`; `load_from_folder` работает в среде без tkinter; e2e 4 провайдеров — OK; +7). Защищённое не тронуто: схема БД, `tm_metadata_manager.py`, regex ссылок на рисунки, PreTranslationWorker, MyMemory inline-fallbacks. Валидация: py_compile канонический 110/0 + справочный 136/0 (после аудитов 153/0 — канонический не растёт), pyflakes 596→577 (undefined монолита 17→0), AST chain 922/0, S-clean 28 / S-upgrade HASH-DIFF пуст / regress / smoke 42 / TB / About — идентичны baseline на каждом шаге. Аудиты: `docs/refactoring/audits/batch8-15_*` (17 скриптов + снапшоты + before/after логи, включая e2e). Методология: указатели user-data в iso-профилях перезаписаны на локальные (апгрейд-пробы с 8.11 молча читали b8-11 каталог — исправлено). Пакет тестовой сборки — 3 файла: Supervertaler.py `3109531c…`, modules/settings_service.py `d76a2816…`, modules/figure_context_manager.py `d396c761…`; Pillow на тестовой сборке 12.3.0 (протокол §9).

**R9 — разведка консолидации провайдеров ЗАВЕРШЕНА** (2026-10-11, READ-ONLY; отчёт `docs/refactoring/reports/R9_PROVIDERS_RECON_REPORT.md`, коммит **4e4f1f45**): (1) **баг профилей Custom найден и воспроизведён 1:1** — сохранение AI Settings перечитывает диск (23859–23860) и выбрасывает снапшот диалога, которому живут кнопки «+»/«−» (19776/19799): add теряет профиль, а `custom_openai_active_profile` получает имя из комбо (у Дмитрия: profiles=[Custom Endpoint], active='Local'); remove воскрешает удалённый профиль и перезаписывает поля выжившего полями другого (тихая порча). Чтение сломанного файла безопасно (fallback profiles[0], 48361). Минимальный фикс описан, НЕ применён — под-батч **9.1**. Гипотеза 5 подтверждена отдельно: нормализации схемы endpoint нет нигде. (2) Инвентарь: провайдер живёт только в settings.json (.svproj/TM-БД/prompt library чисты); единственная точка миграции `SettingsService.load_llm_settings:228`; custom_openai работает через SDK `openai` (`_call_openai_with_usage` 893–1008) — **SDK остаётся**, уходят anthropic/google-generativeai/boto3/deepl (P2); в dev-runtime облачных SDK нет вообще. (3) План 9.1–9.5 (§Ч3) с зонами/рисками/T9.x/защитами; ответы Дмитрия 1–5 (2026-10-11) — все рекомендации ПОДТВЕРЖДЕНЫ, записаны в отчёте. Мёртвые методы с провайдерными ветками (`_REMOVED_add_mt_and_llm_matches_progressive`, `_save_llm_settings_from_ui`) — не трогать в 9.x, очередь 8.18.

**Batch #9.1 ПРИНЯТ** (2026-10-11; вердикт: T9.1.1–T9.1.6 на тестовой сборке — **все ПОДТВЕРЖДЕНЫ** (§9 отчёта), включая самолечение dangling-файла, сохранение/удаление профилей, нормализацию схемы и перевод через локальный llama с http-endpoint; отчёт `docs/refactoring/reports/BATCH9_1_CUSTOM_PROFILES_REPORT.md`): база 4ed6eba4 (код 8.15f); 2 коммита: **e471b716** 9.1a (сохранение профилей Custom: `_save_ai_settings_from_ui` берёт список из живого снимка диалога — новый опц. параметр `custom_profiles_snapshot` от единственного вызывающего, кнопки Save; dangling-имя самолечится на profiles[0]; плоские зеркала — из активного профиля; +12 нетто) и **a6b1097c** 9.1b (`@staticmethod _normalize_custom_endpoint`: без схемы → http:// для loopback/частных, https:// для остальных; применён на записи AI-профиля (с показом в поле) и на чтении в `_get_active_custom_profile` (нормализованная КОПИЯ, диск не мутируется) и `_get_active_custom_mt_profile`; LLMClient/create_llm_client не тронуты (G3.x); таблица хелпера 15/15; +51 нетто). Монолит 56 524 → **56 587** (SHA `5cdae632…`) — первый растущий батч (фикс, не удаление). Крайние случаи: дубликаты/пустые имена — гард был и остался; удаление единственного/нуля профилей — теперь чистый файл; юникод+trim — сохраняется. Защиты после каждого коммита идентичны baseline: py_compile 110/0 + 156/0, headless 91/2, pyflakes 577/126/4 (монолит undefined=0), AST chain 922/0, S-clean 28 OK, S-upgrade HASH-DIFF пуст, regress 6 sha == 8.15, smoke 42 OK, TB OK, About OK. Спец-пробы (настоящие виджеты, изо-профили): a/ctrl/rm/d/c1/c2/c3/mt/крайние — зелёные после каждого коммита; контроль «ДО» подтверждает баг. Пакет тестовой сборки: **заменить только Supervertaler.py** SHA `5cdae632…`. Аудиты: `docs/refactoring/audits/batch9-1_*` (4 скрипта + 54 лога). Находки: полный e2e-запрос с фейк-endpoint не прогонялся (в dev-runtime нет пакета `openai`, по промпту не ставился — проверить конструирование); stdout простаивающего offscreen-экземпляра ненадёжен → вердикты в файл. **Перед 9.2: поставить `openai` в dev-runtime той же версии, что в тестовой сборке. Следующий шаг — 9.2 (MT: только custom MT) — по команде Дмитрия и его промпту.**

**Batch #9.2 ПРИНЯТ** (2026-10-11; вердикт: T9.2.1–T9.2.6 на тестовой сборке — **все ПОДТВЕРЖДЕНЫ** (§9 отчёта): страница MT Settings исчезла, QuickTrans-чипы/пакетный диалог/Match Panel на custom MT работают, старые ключи инертны, smoke цел; отчёт `docs/refactoring/reports/BATCH9_2_MT_CUSTOM_ONLY_REPORT.md`): база a6b1097c (9.1b); 6 коммитов: **fc6e313f** 9.2a (диспетчер `_fetch_mt_translation_async` → custom MT only: активный профиль, вежливый no-op без профиля, provider_code='CMT'; вырез шести `call_*` 346 строк с ленивыми `import deepl/boto3`; MT-блок `_add_mt_and_llm_matches` → `call_custom_mt`; −414), **be82d963** 9.2b (диалог пакетного перевода: MT-вариант = «Custom MT» при наличии включённого профиля; воркер `PreTranslationWorker._translate_with_mt` → `call_custom_mt`, вариант (а) — parent_app уже используется воркером; −13), **513a2fae** 9.2c (quicktrans.py: 6 дефов+цикл удалены, custom MT-чипы (CMT) остались; панель: тултипы MT удалены, CMT добавлен; монолит-таб: чекбоксы mtql_gt/dl/ms/at/mmt/mm удалены; −69), **7298ce24** 9.2d (страница MT Settings + `_save_mt_settings_from_ui` + пункт сайдбара удалены; Settings 14→13, порядок цел; MT-ключи в settings.json инертны; −134), **a39ca9a5** 9.2e (дефолты `mt_*` из provider_enabled_states; механизм и llm_* целы; −10), **13e1ad29** cleanup (PROVIDER_COLORS: −6 мёртвых кодов, +CMT). Монолит 56 587 → **55 997** (SHA `287781c1…`); quicktrans.py 1627, панель 2422, settings_service 555. Защиты после каждого коммита: py_compile 110/0+160/0, headless 91/2, pyflakes 577/126/4 (монолит 0), S-clean/S-upgrade/regress 6 sha/smoke/TB/About идентичны; AST chain 922→**907** (−15 резолвов удалённых методов, ожидаемо). Спец-пробы (openai 3.24.0): e2e фейк-endpoint «ДО»=«ПОСЛЕ» («Goedemorgen», POST /v1/chat/completions); диспетчер дошёл до custom MT; empty — вежливо; legacy-trap (ловушка requests) — удалённые провайдеры не вызываются, старые mt_*-ключи инертны; QuickTrans-таб/AI-таб целы. Grep-гейт: 0 вне мёртвого `_REMOVED_…` (8.18). Находка методологии: `git checkout` отдаёт монолит LF → после откатов обратная конверсия CRLF; сплайсы по устаревшим номерам строк ловились py_compile (2 отката в stage, в репо только корректные версии). Пакет тестовой сборки — 4 файла (§5 отчёта). T9.2.1–.6 — ручные.

**Batch #9.3 EXECUTED** (2026-10-11; отчёт `docs/refactoring/reports/BATCH9_3_LLM_BACKEND_REPORT.md`, §0–§9; ручные T9.3.1–.11 не выполнены — ждут тестовой сборки и вердикта): база 13e1ad29 (код 9.2); 4 коммита: **f5fe9477** 9.3a (молчаливая миграция provider → custom_openai в `SettingsService.load_llm_settings` — в ВОЗВРАЩАЕМОМ словаре, диск не переписывается; legacy-плоский конфиг → профиль с нормализацией endpoint; правило 9.1b перенесено в `SettingsService.normalize_custom_endpoint`, монолит — делегат, 15/15 кейсов сходятся; дефолты `provider_enabled_states` → только `llm_custom_openai`; chat_backend дефолт → custom_openai; юнит-проверка 10 сценариев), **6c75769a** 9.3b (монолит: +`_custom_llm_ready` гейт-хелпер «профиль с endpoint»; create_llm_client только custom, чужой provider → ValueError; translate_current_segment без ollama-диалога/промпта/веток ключей; translate_batch — модель через `_resolve_provider_model` (чинит ДО-квирк «custom-model»), гейт до старта; Match Panel LLM-часть переписана на custom (ДО: 0 запросов — ветки custom не было) с кодом CUS; quicklauncher/autotag×2/proofread — гейты и кастомные цепочки ключей; воркер ×4; Image Extractor «Vision for Custom profile is not enabled yet»; −283), **89a20764** 9.3c (proofread-воркер 8 веток → 1; chat_view keyless; quicktrans llm_defs → [Custom/CUS]; unified_prompt_manager gemini-payload → base64; −22), **59290c98** 9.3d (llm_clients 2000→**787**: удалены claude/gemini-with_usage, все 5 legacy-клиентов, ollama-хелперы, check_ollama_status/get_*_model_info, DEEPSEEK_MODELS, CLI-хелперы; translate_with_usage — одна ветка, чужой provider → ValueError; VISION_MODELS = {} (галка — 9.5); СОХРАНЕНО до 9.4: set_ollama_timeout, MISTRAL/CLAUDE/OLLAMA/OPENROUTER_MODELS (меню чата), load_api_keys дословно; закрыты щели «не настроено → api.openai.com»: chat_backend-гейт, quicktrans-чип, _do_extract_terms; фикс затенения QMessageBox в translate_batch; −1213). Итог по коду **−1567**; монолит 55 997 → **55 703**. Валидация: py_compile канон 110/0 (справочный 163→165 от аудит-скриптов), headless 91/2, pyflakes 576→**562**/126/4 (−14 из удалённого кода; 4 имени = baseline-набор, монолит 0), chain 907/0, S-clean/S-upgrade/regress 6 sha/smoke 42/TB/About — идентичны на каждом коммите; grep-гейт 0 FAIL (разрешённые остатки: мёртвые 8.18-методы, UI-9.4 зоны, G5-блок, комментарии). Спец-пробы: e2e «ПОСЛЕ» == «ДО» (путь/Authorization/model/длина промпта; batch теперь шлёт модель профиля — задокументированный фикс; Match Panel 0→1 CUS — целевое); матрица совместимости 40/40 (11 провайдеров × 4 формы профилей, диск не переписывается); ловушка сети 0 попаданий (включая legacy-seed provider=ollama; localhost:11434 от UI-виджета Ollama-статуса разрешён до 9.4); Save AI Settings ×8 радио — provider остаётся custom_openai; ledger: provider=custom_openai, in_regular=11/out=4, source=actual, cost_known=false для модели без прайса. Находки: затенение QMessageBox локальным импортом — латентный паттерн ещё в create_termbases_tab/_show_edit_terms_dialog/_create_ai_settings_tab (не трогались, отметить в 8.18); heredoc в Git Bash съедает бэкслэши — правки только файловыми скриптами. Пакет тестовой сборки — 8 файлов (§5 отчёта). T9.3.1–.11 — ручные. **2026-10-13: результаты тестов Дмитрия (§10 отчёта): T9.3.1/.2/.3/.5/.6/.7/.8/.10/.11 — ПОТВЕРЖДЕНЫ; T9.3.4 снят (нет UI-проявления; находка 2b: путь Match Panel осиротел до baseline, кластер «Enable LLM (AI) matching» — в кандидаты 8.18 по решению Дмитрия); T9.3.9 — ПОТВЕРЖДЕНО (замечание Дмитрия: текст «not configured» только в модельных окнах, в статус-баре нет — отметить для 9.4). Ответы на вопросы §8: 1 — вариант (a) (один чекбокс Custom + read-only модель профиля) с ДОПОЛНЕНИЕМ Дмитрия: рассмотреть выбор профиля по аналогии с Custom (OpenAI-Compatible) Setting в AI Settings — в план 9.4; 2 и 3 — по рекомендации; 4 — pyflakes 562/126/4 новая база. Формальный вердикт «ПРИНЯТ» за Дмитрием. Следующий шаг — 9.4 (UI: AI Settings/Local LLM/QuickTrans-таб (вариант 1a + выбор профиля)/статус-бар; тогда же удаление MISTRAL/CLAUDE/OLLAMA/OPENROUTER_MODELS и set_ollama_timeout из llm_clients) — по команде Дмитрия и его промпту.**

**Batch #9.5 EXECUTED** (2026-10-14; отчёт `docs/refactoring/reports/BATCH9_5_VISION_AND_ENDPOINT_REPORT.md` §1–§10; рекон `docs/refactoring/reports/RECON_95.md`; ручные T9.5.1–T9.5.7 не выполнены — ждут тестовой сборки и вердикта): база 575bd419 (код 2e9dd938: монолит `fb3dce5c…`/54992); 4 коммита: **791024bd** 9.5a (vision как свойство профиля в данных + клиенте: `LLMClient.__init__(supports_vision=False)` + гейт `if images and not self.supports_vision: images = None` в `translate_with_usage`; `create_llm_client` резолвит `profile.get('supports_vision')` (absent/не-bool → False, settings.json при загрузке не переписывается); легаси-синтез `_get_active_custom_profile` и миграция settings_service несут `supports_vision: False`; VISION_MODELS/model_supports_vision — временный always-False шим для 3 внешних гейтов, удалён в 9.5c; +7), **0410bdc4** 9.5b (UI: `custom_vision_cb = CheckmarkCheckBox(self.tr("Model supports vision (image input)"))` + tooltip «Enable only if the model behind this endpoint accepts images…» в `_create_ai_settings_tab`; populate по профилю (не-bool → False), toggled → sync в живой снимок, новый профиль unchecked, Save-параметр `custom_vision_cb` → `profiles[idx]['supports_vision']`; +21), **7aa98248** 9.5c (гейты берут флаг реально используемого клиента: Image Extractor гейт 3 → `getattr(llm_client,'supports_vision',False)`, figure-context гейт → `getattr(client,'supports_vision',False)` (импорт LLMClient из try-блока удалён, мёртвая gemini-ветка не тронута — 8.18), prompt manager `_collect_autoprompt_images` → `getattr(llm_client,"supports_vision",False)`; тексты отказов → «tick Model supports vision (image input) … Settings → AI Settings»; VISION_MODELS + model_supports_vision удалены (0 потребителей в продукте; 2 исторических audit-скрипта не тронуты); из импорта prompt manager убран неиспользуемый `LLMClient` (`load_api_keys` был неиспользуем на базе — оставлен, §9 отчёта); llm_clients 598→579), **61639c60** 9.5d (запрет пустого endpoint: `_save_ai_settings_from_ui` проверяет ВСЕ профили живого снимка (активный — после синка видимых полей) ДО первой записи на диск; пустой (strip(), пробелы = пусто) → `QMessageBox.warning` «Empty Endpoint» с именем профиля + `custom_profile_combo.setCurrentIndex(idx)` + `return` — файл не меняется, вкладка открыта; пустой список профилей разрешён; **Custom MT не проверяется** (пустой MT endpoint разрешён); +22). Итог: монолит 54 992 → **55 042** (SHA `9e7a3080…`), llm_clients 597→**579** (`7f2b9ee9…`), settings_service 598→**599** (`08a0d943…`), prompt manager 6833 без изменений (`cec2ef68…`), quicktrans 1635 не тронут (`6a6812be…`). Формат images (OpenAI content-parts `image_url` + base64 data-URL) проверен на fake-сервере — правка 0 строк. Валидация per-commit: chain 871→**873/0** (9.5b: ровно +2 `self.tr()` чекбокса, оба резолвятся; diff JSON added 2/removed 0), pyflakes 549→**548** (9.5c: −1 удалённый неиспользуемый импорт; undefined 126/4 идентичен базе), py_compile канон **109/0** (справ. 190/0), headless 90/2 (setuptools, fitz), grep-гейт 8 файлов CLEAN, S-clean 31 TREE / S-upgrade HASH-DIFF пуст / regress 5a12501f+44828d90+c413d563 / smoke 42 / TB / About / save / r9 a+ctrl+rm / e2e / qtchat / statusbar / profiles / fallback — зелёные на каждом коммите. Спец-проба `batch9-5_probe_vision_and_endpoint.py` (V1–V8, fake-endpoint на 127.0.0.1 + ловушка сети): на 9.5c 33/39 (6 FAIL = V6, фича не готова), после 9.5d **39/39**; V7-доказательство — `probe_94i_master_removed.py` на финальном состоянии зелёная (T1–T5, ловушка 0). Правки audit-артефактов: сид 9.4a save-probe дополнен `supports_vision: False` у активного профиля (Save легитимно дописывает ключ → строгая dict-проверка сравнивает одинаковые словари; ALL OK); в обе спец-пробы добавлен патч `Supervertaler.SupervertalerQt._start_okapi_sidecar = lambda self: None` **до конструирования** (находка: `QTimer.singleShot(1500, self._start_okapi_sidecar)` захватывает bound-метод при планировании — патч экземпляра после конструктора не спасает; раньше 9.4i T4 была зелёной только пока прокачка событий не пересекала 1,5 с). r9-сиды и сиды 9.4f/9.4i правки не потребовали (endpoint-ы непустые; 9.4f/9.4i кликают только «Save QuickTrans»). Находки в BACKLOG (§9 отчёта): pdf_rescue_Qt легаси-клиенты удалённых провайдеров (8.18), «Sonnet cost ballpark» в текстах (8.16), неиспользуемый `load_api_keys` в импорте prompt manager. Пакет тестовой сборки — 4 файла (§5 отчёта). **Следующий шаг — G5 (урезанный), затем 8.18 → 8.16 → 8.17 — по команде Дмитрия и его промпту.** AST-границы (пересчёт на 61639c60): `_create_ai_settings_tab` 19236–19887, `_create_mt_quick_lookup_settings_tab` 19898–20148, `_save_mt_quick_lookup_settings` 20150–20206, `_save_ai_settings_from_ui` 23038–23204, `_save_api_keys_from_ui` 23206–23217, `_update_llm_indicator` 7570–7592, `_resolve_provider_model` 7553–7568, `_normalize_custom_endpoint` 47519–47526, `_custom_llm_ready` 47528–47542, `_get_active_custom_profile` 47544–47578, `call_custom_mt` 47608–47699, `create_llm_client` 47701–47734, `show_about` 48493–48555.

**Batch #9.4 EXECUTED** (2026-10-13; отчёт `docs/refactoring/reports/BATCH9_4_PROVIDER_UI_REPORT.md` §0–§9; ручные T9.4.1–.11 не выполнены — ждут тестовой сборки и вердикта): база 59290c98 (код 9.3d); 6 коммитов: **57648c47** 9.4a (AI Settings: удалены радио 7 провайдеров, 6 модельных комбо, Ollama-виджет + try-импорты local_llm_setup, API-keys группа (7 удалённых ключей), 6 enable-чекбоксов, Ollama Advanced, неактивный чекбокс «Enable LLM (AI) matching» (находка 2b 9.3); `_save_ai_settings_from_ui` → provider 'custom_openai', записи удалённых моделей/ollama_*/keepwarm удалены, enabled_states = merge (иностранные ключи сохраняются); `_save_api_keys_from_ui` KEEP; 30+/546−), **df1b238f** 9.4b (keepwarm-кластер 4 метода, `_apply_ollama_timeout_setting`, `_apply_gemini_proxy` + вызовы; `git rm modules/local_llm_setup.py` (1071); 96−), **bfeb79d2** 9.4c (`_update_llm_indicator`: 8 ветвей → Custom «🔌 {profile}: {model}» / «🔌 Custom profile not configured» — замечание Дмитрия по T9.3.9 учтено; read-only заметка Local LLM «local server management coming later»; 24+/39−), **7e274af0** 9.4d (QuickTrans-таб: llm_providers-цикл + Ollama-строка + загрузка api_keys/enabled_states удалены; custom-строка = чекбокс mtql_custom_openai + read-only модель активного профиля; quicktrans.py чипы → CUS-only; чат-меню → read-only заголовок профиля + «AI Settings…», `_on_model_selected` удалён; 41+/246−), **f6c26a8d** 9.4e (llm_clients −190: set_ollama_timeout/_ollama_timeout_override, MISTRAL/OPENROUTER/OLLAMA/CLAUDE_MODELS, OLLAMA_ENDPOINT env; llm_pricing `_FREE_PROVIDERS=()`; тексты About/пакетный чекбокс/proxy_note/setup.py/help_system/docstring; 9+/204−), **9675f93f** 9.4f (профильный выбор QuickTrans по паттерну Custom MT — решение Дмитрия 2026-10-13: чекбокс на профиль в табе, `mtql_llm_profiles` в mt_quick_settings (absent = все с endpoint, пусто = ни одного), чип CUS на каждый включённый профиль (label = имя), опц. параметр `profile_name` в `_get_active_custom_profile`/`_custom_llm_ready`/`create_llm_client` (глобальный активный профиль не меняется); шлюз ≤100 выполнен: +41 нетто; 82+/41−). Итог по коду **−2232**; монолит 55 703 → **55 000** (SHA `ade0e48a…`); llm_clients 787→597, chat_view_widget 1024→934, quicktrans 1626→1628, local_llm_setup удалён. **Follow-up 9.4g `f6f98538`** (ЗАМЕТКА Дмитрия 2026-10-13, авторизована): Save QuickTrans-таба применяет `_normalize_custom_endpoint` к endpoint профиля Custom MT (`192.168.1.5:8080/v1` → `http://192.168.1.5:8080/v1`; loopback/приватные → http, публичные → https; поле показывает нормализованное значение — как AI Settings 9.1b) + нормализация на чтении в `call_custom_mt`; +6/−2, монолит → **55 004** (SHA `a3ced13d…`). **Follow-up 9.4h `3f9554dd`** (уточнение Дмитрия 2026-10-13): попап QuickTrans с пустым списком профилей (все чекбоксы сняты/профили удалены) обязан работать с глобальным активным профилем из AI Settings как с единственно оставшимся — баг 9.4f (`mtql_llm_profiles=[]` → ноль чипов); правка в `quicktrans._add_llm_providers`: при нуле чипов и непустом списке профилей добавляется чип `_get_active_custom_profile` (label = имя активного профиля, вызов с `profile_name=None` → endpoint/ключ/модель активного); `probe_94h_fallback.py` 5 сценариев зелёные (all-off → «Profile A» + `Bearer prof-key-A`; subset; absent; deleted → легаси «Custom Endpoint»; активного имени нет → первый профиль); quicktrans.py 1628 → 1642. **Follow-up 9.4i `064c2bbf`+`2e9dd938`** (решение Дмитрия 2026-10-14): мастер-чекбокс «Custom (OpenAI-Compatible)» (`mtql_custom_openai`) в табе QuickTrans **убран** — LLM-чипы в попапе есть всегда; чекбоксы профилей (`mtql_llm_profiles`) выбирают чипы; при пустом/устаревшем списке — чип глобального активного профиля (9.4h, унифицирован: `_get_active_custom_profile` = активный по имени → первый с endpoint → легаси-плоский); при ненастроенном профиле — чипов нет, ошибок нет; read-only поле модели активного профиля удалено вместе с мастером; legacy-чип «Custom» (плоский endpoint) удалён; старый ключ `mtql_custom_openai` инертен (Save переносит из старой секции без изменений, не читается, заново не пишется); баг «9.4h не работает» (скриншот Дмитрия: мастер снят → попап пуст) устранён удалением мастера; спец-проба `probe_94i_master_removed.py` зелёная (T1 таб/Save, T2 чипы, T3 false/true/отсутствует одинаково, T4 ловушка сети 0, T5 скриншот-сценарий «strata» + `Bearer prof-key-strata`); монолит 55 004 → **54 992** (SHA `fb3dce5c…`), quicktrans.py 1642 → **1635** (SHA `6a6812be…`); новый сценарий **T9.4.12** (§6 отчёта) — **ПОЛНОЕ ПОДТВЕРЖДЕНИЕ (Дмитрий, 2026-10-14)**. Находка 9.4h: HASH-DIFF upgrade-пробы `changed=['workbench/ai_assistant/index.json']` — артефакт даты (чат-индекс добавляет сессионный ключ по дате), не регрессия; транзиент-фильтр пробы расширить в инфра-проходе. Тесты Дмитрия 2026-10-13 (§10 отчёта): T9.4.1–.5/.7–.10 ПОДТВЕРЖДЕНО; T9.4.6 ПОДТВЕРЖДЕНО с ЗАМЕЧАНИЕМ (→ 9.4h); T9.4.11 ПОДТВЕРЖДЕНО (2026-10-13); Q4 ПОДТВЕРЖДЕНО (статус-бар = глобальный активный профиль). Исследование ЗАМЕЧАНИЯ (попап не переводит с Custom-профилем): в коде репозитория попап переводит (пробы `probe_94g_popup.py`, `probe_94g2_schemeless.py` — зелёные, в т.ч. с бесcхемным endpoint); на frozen-сборке 960be5d8 `create_llm_client` берёт endpoint без нормализации → бесcхемный endpoint не работает в OpenAI SDK (баг сборки до 9.1b, не «так задумано»); Custom MT профили Дмитрия работают, т.к. введены со схемой. Ответы §8: Q1 label=имя профиля подтверждён; Q2 → запрет сохранения профиля без endpoint (BACKLOG §9.5); Q3 подтверждён (8.18); Q4 без вердикта. ЗАМЕТКИ в BACKLOG: §9.3 импорт/экспорт профилей, §9.4 переключение активного профиля в чат-меню. Валидация per-commit: chain 907→875→**871/0** (9.4i: −4 — ровно 4 вызова удалённой мастер-строки: `self._get_active_custom_profile()` + 3× `self.tr()`; diff JSON before/after: removed 4, added 0), pyflakes 562→**549** (undefined 126/4 идентичен базе), py_compile канон 110→**109/0** (справ. 186/0), headless 90/2, S-clean/S-upgrade/regress 6 sha/smoke 42/TB/About/save/r9 a+ctrl+rm/e2e 5 сценариев (verdict OK)/qtchat/statusbar/profiles-пробы — зелёные на каждом коммите; grep-гейт 0 FAIL (разрешённые остатки: мёртвые 8.18-методы, инертные ключи settings.json, комментарии 8.16, pdf_rescue_Qt PROTECTED). Находки: 9.4f-правка таба потеряла `llm_layout.addLayout(custom_row)` (мастер-чекбокс не появлялся в UI) — восстановлена, найдено offscreen-пробой; `mt_quick_lookup` живёт в верхнеуровневой секции `general` settings.json (не `ui.general_settings`) — пробы сеять/читать туда. Пакет тестовой сборки — 8 файлов (§5 отчёта). **Следующий шаг — 9.5 (vision-чекбокс в профиле Custom) — по команде Дмитрия и его промпту.** AST-границы (пересчёт на 2e9dd938): `_create_ai_settings_tab` 19236–19868, `_create_mt_quick_lookup_settings_tab` 19879–20129, `_save_mt_quick_lookup_settings` 20131–20187, `_save_ai_settings_from_ui` 23019–23161, `_save_api_keys_from_ui` 23163–23174, `_update_llm_indicator` 7570–7592, `_resolve_provider_model` 7553–7568, `_normalize_custom_endpoint` 47476–47483, `_custom_llm_ready` 47485–47499, `_get_active_custom_profile` 47501–47534, `call_custom_mt` 47564–47655, `create_llm_client` 47657–47684, `show_about` 48443–48505.

**Batch #7 (историч.):** Step 7 завершён: Stage 1 (read-only) + Stage 2 в пяти под-батчах (S2.1 «ядро API», S2.2 «general + clipboard reading», S2.3 «LLM/proxy/provider/api keys», S2.4 «языковая пара + spellcheck-IO», S2.5 «recent projects») — `modules/settings_service.py` 565 строк / 26 методов + 25 тонких делегатов; монолит на тот момент **68 224** строки

## Кратко: где мы находимся

Инкрементальная декомпозиция монолита `Supervertaler.py` (73 337 строк на старте;
сейчас **55 042** после 9.5) в пакеты `modules/` по плану `EXTRACTION_PLAN.md` (Step 0–14).
Выполнены **Step 1–5** (батчи #1, #2, #3a, #3b, #3c, #4, #5) и **Step 6 целиком**
(Batch #6: Stage 1 — инвентаризация, Stage 2 — `modules/grid/helpers.py`,
Stage 3 — `modules/grid/pagination.py`, Stage 4 — `modules/grid/filters.py`).
По **Step 7** выполнен **Stage 1 (Batch #7, read-only инвентаризация, 24.09.2026)**,
решения по V1–V4 приняты, и **Stage 2 закрыт целиком** (S2.1–S2.5): под-батч
**S2.1 «ядро API»** (25.09.2026) перенёс 6 методов / 39 строк в новый
`modules/settings_service.py`,
под-батч **S2.2 «general + clipboard reading»** (26.09.2026) добавил туда ещё
3 метода / 56 строк (`load_clipboard_privacy_settings`,
`_load_general_settings_from_file`, `save_general_settings`) и оставил в монолите
3 тонких делегата с исходными сигнатурами; монолит 68 400 → **68 373** строки,
8 метрик без изменений, живой offscreen-прогон приложения — 9/9 PASS; под-батч
**S2.3 «LLM/proxy/provider/api keys»** (27.09.2026) перенёс ещё 10 методов / 150
строк (`load_llm_settings`, `save_llm_settings`, `load_proxy_settings`,
`save_proxy_settings`, `_get_proxy_url`, `_get_proxy_dict`,
`load_provider_enabled_states`, `save_provider_enabled_states`, `load_api_keys`,
`save_api_keys`) и оставил в монолите 10 тонких делегатов с исходными сигнатурами
(включая приватные `_get_proxy_url`/`_get_proxy_dict`); монолит 68 373 → **68 285**
строк (−88), 8 метрик без изменений, живой offscreen-прогон — 14/14 PASS (в т.ч.
прямой тест 5 НЕЗАЩИЩЁННЫХ вызовов `PreTranslationWorker`). Под-батч
**S2.4 «языковая пара + spellcheck-IO»** (27.09.2026) перенёс ещё 4 метода / 47
строк (`_load_language_pair_from_disk`, `save_language_settings`,
`_save_spellcheck_settings`, `_load_spellcheck_settings`) и оставил 4 тонких
делегата; это ПЕРВЫЙ под-батч Stage 2, где сработало стоп-условие «зависимость от
состояния окна»: 2 тела чистые (ВЕРБАТИМ), а 2 перенесены SPLIT-ом (запись
`self.source_language`/`target_language` и чтение `self.spellcheck_enabled`
остались в делегатах, сервис принимает/возвращает значения); монолит 68 285 →
**68 274** строки (−11), 8 метрик без изменений, живой offscreen-прогон — 11/11 PASS
плюс отдельный процесс-перезапуск 4/4 PASS. Под-батч **S2.5 «recent projects»**
(28.09.2026) — ПОСЛЕДНИЙ в Stage 2 — перенёс ещё 2 метода / 74 строки
(`load_recent_projects`, `save_recent_projects`) и оставил 2 тонких делегата; это
первый под-батч, где перенесённые тела работают НЕ через `settings.json`, поэтому
применён вариант **SPLIT-BY-ARGUMENT**: делегат читает `self.recent_projects_file`
(и `self.user_data_path`) при КАЖДОМ вызове и передаёт их аргументами, сервис пути
не хранит, конструктор сервиса не менялся; монолит 68 274 → **68 224** строки
(−50), 8 метрик без изменений, живой offscreen-прогон — 16/16 PASS +
процесс-перезапуск 6/6 PASS + клик по реальным пунктам меню 3/3 PASS, кросс-дерево
(work против worktree предыдущего коммита) — 0 неожиданных расхождений. **Step 7
закрыт целиком: 25 методов / ~366 строк перенесены (S2.1 6, S2.2 3, S2.3 10,
S2.4 4, S2.5 2), голосовые методы, три миграции, `load_general_settings`,
V3-исключения и тир C `recent_projects` (add/remove/display/clear) сознательно
остались в монолите** — основания в итоговом блоке Step 7 `EXTRACTION_PLAN.md` и
§5 отчёта S2.5.
Дальше — **Step 8** (Grid: render + match panel + comments UI); Step 7 закрыт полностью.

**Синхронизация с апстримом (серия U1, 01–02.10.2026): база апстрима обновлена
частично до v1.10.372** — под-батчи U1.1/U1.2 (данные, цены, настройки,
`a7746d65`/`f5c460e9`), U1.3a/U1.3b (фиксы TM/TMX/F&R, `a1f76985`/`2e258269`),
U1.4a/U1.4b (сегментация без потерь + правила + страница настроек,
`5c052c9d`/`426a09e2`); класс D (QA-фичи, Inline Codes, тёмная тема,
settings autosave, вставка исходника) и файлы `CHANGELOG.md`/`FAQ.md` апстрима —
не перенесены; перенесено частично: `segment_split_merge.py` = 763291e8 без
34a4c661. Манифест и детали — `docs/refactoring/reports/UPSTREAM_SYNC_MANIFEST.md`.
Среда, тестирование и валидация — по `AGENTS.md` (обязательно к
прочтению перед любой работой).

## Прогресс по шагам EXTRACTION_PLAN.md

| Step | Что | Статус | Батч / артефакты |
|---|---|---|---|
| 0 | Dead-инвентарь, базовая линия | ✅ выполнен (база до Batch #1) | `DEAD_CODE_REPORT.md`; решения по удалению — в backlog |
| 1 | Модели данных → `modules/models.py` | ✅ выполнен | Batch #1, коммит `969c9fe`; отчёт `docs/refactoring/reports/ОТЧЁТ Batch #1.txt` |
| 2 | DOCX tag-движок → `modules/tag_manager.py` | ✅ выполнен | Batch #2, коммит `1ac400d`; см. TECH-DEBT в конце `EXTRACTION_PLAN.md` |
| 3 | Event-фильтры + диалоги + чекбоксы | ✅ выполнен | Batch #3a `c7497d6` (`modules/event_filters.py`), #3b `4895e72` (`modules/dialogs/`), #3c `e543787` (`modules/styled_widgets.py`) |
| 4 | Чистые QThread-воркеры | ✅ выполнен | Batch #4 (этот коммит; `modules/workers/`); отчёт `docs/refactoring/reports/ОТЧЁТ Batch #4.txt` |
| 5 | Undo-менеджер | ✅ выполнен | Batch #5 Stage 1 `c11e1bc` (инвентаризация) + Stage 2 (`modules/undo_manager.py`); отчёты `docs/refactoring/reports/ОТЧЁТ Batch #5 Stage 1.txt` и `…Stage 2.txt` |
| 6 | Grid: helpers/pagination/filters | ✅ выполнен (Step 6 закрыт целиком) | Batch #6 Stage 1 `c5a5da1`; Stage 2 `4ace504` (`modules/grid/helpers.py`, 16 функций + 17 делегатов); Stage 3 `26b998c` (`modules/grid/pagination.py`, 14 функций + 14 делегатов + 2 константы); Stage 4 (`modules/grid/filters.py`, 20 функций + 1 внутренняя + 20 делегатов); отчёты `docs/refactoring/reports/ОТЧЁТ Batch #6 Stage {1,2,3,4}.txt`; аудиты `docs/refactoring/audits/batch6_stage1_*.txt`, `*batch6stage{2,3,4}*` |
| 7 | Settings service (IO-слой) | ✅ выполнен (Stage 2 закрыт целиком) | Batch #7 Stage 1 (read-only) + Stage 2 S2.1/S2.2/S2.3/S2.4/S2.5: 25 методов / ~366 строк в `modules/settings_service.py` (565 строк, 26 методов) + 25 делегатов; отчёты `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 1.txt`, `…Stage 2 (S2.1…S2.5).txt`; findings `docs/refactoring/audits/step7_stage1_findings.md`; аудиты `docs/refactoring/audits/batch7_stage1_*.txt`, `batch7s2{1,2,3,4,5}_*.txt` |
| 8 | Grid: render + match panel + comments UI | ⬜ не начат | — |
| 9 | Мелкие изолированные фичи | ⬜ не начат | — |
| 10 | Find&Replace + поиск | ⬜ не начат | — |
| 11 | Импорт/Экспорт контроллеры | ⬜ не начат | — |
## Что дальше: Step 7 Stage 2 — под-батч S2.5 закрыт, STEP 7 ЗАКРЫТ ЦЕЛИКОМ (28.09.2026)

**S2.5 выполнен** (база HEAD `d4db217` — потомок базы разведки `1ef3c708`, дрейфа
нет; монолит 68 274 → **68 224** строки, −50; difflib — ровно 2 неравных региона
−52/+2, сумма −50 == изменению файла). Перенесены 2 метода / 74 строки в
`modules/settings_service.py` (451 → 565 строк; методов 24 → 26) —
`load_recent_projects` (сервис 490–552), `save_recent_projects` (сервис 554–565).
**Это единственный под-батч Stage 2, где тела не ходят через `settings.json`**:
они открывают отдельный `recent_projects.json`, поэтому применён вариант
**SPLIT-BY-ARGUMENT** (решение координатора): делегат читает
`self.recent_projects_file` при каждом вызове (в save — ещё и
`self.user_data_path` для `mkdir`) и передаёт их аргументами; сервис пути НЕ
хранит, конструктор `SettingsService` и перепривязка сервиса в
`_reinitialize_with_new_data_path` не менялись (проверено AST: Store этих двух
имён в сервисе = 0). Тела перенесены ВЕРБАТИМ, документированная правка — 3 и 2
замены ссылок на пути (+ строка `def` в save разбита на две): diff −4/+4 и
−3/+4. В монолите — 2 тонких делегата с исходными сигнатурами (2/2
signature_identical + forwards, форвардинг идёт именованными аргументами путей).

**Живой прогон (offscreen) — 16/16 PASS + перезапуск 6/6 PASS + клик по меню 3/3
PASS + кросс-дерево 0 неожиданных расхождений:**
- все пункты промпта а–ж закрыты фактически: list-формат с фильтрацией
  (`os.path.exists` + `.svproj`, регистр расширения не важен, доставка
  `name`/`last_opened`), старый dict-формат, latin-1-fallback с точной строкой
  предупреждения, отсутствующий файл → [], битый JSON → [] с точной строкой
  ошибки, save в кириллический путь с побайтовой идентичностью каноническому
  `json.dumps(indent=2, ensure_ascii=False)` и созданием `user_data_path`,
  ветка ошибки записи без исключения, переприсваивание `recent_projects_file` →
  чтение/запись в новый файл и «нет кэша» (1 → 2 записи при внешней перезаписи);
- живой прогон: проект сохранён/открыт реальными `save_project_to_file` и
  `load_project` → появился в файле, в меню «Open Recent» («1. S25 Alpha») и в
  списке недавних (панель подставлена — в сборке её нет, см. п. 45 реестра);
  второй проект встал выше; удаление и `clear_recent_projects` (Yes/No) работают;
  лимит `MAX_RECENT_PROJECTS=10` соблюдён; `restore_last_project_if_enabled`
  восстанавливает самый свежий проект, а перезапуск в ОТДЕЛЬНОМ интерпретаторе
  делает это на СТАРТЕ приложения (`__init__` 6486) — то есть проверен именно
  путь запуска;
- «прежняя реализация» — тот же драйвер в worktree `d4db217`: 16/16 PASS, и
  сравнение JSON-листьев двух деревьев даёт 0 неожиданных расхождений (7
  отличий — прямые вызовы сервиса, которых до переноса не существует).
- 7 NOT-MOVE-блоков (4 метода тира C недавних + 3 миграции) — byte-identical;
  `__init__`, `_reinitialize_with_new_data_path`, `update_recent_menu`,
  `restore_last_project_if_enabled` — byte-identical; оба присваивания
  `recent_projects_file` на месте (2/2).
- манифест (по git-блобам): changed = ровно 2 (`Supervertaler.py` 0854f899… →
  c0370685…, `modules/settings_service.py` 6778e9e7… → 5e582639…), added/removed
  = 0; 8 метрик 1211/18/35/24/24/0/85/2 — файлы до/после побайтово равны;
  py_compile COMPILE_OK; смоук save/load EXIT=0 на обоих деревьях.

Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.5).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.5 recent-projects).txt`;
аудиты: `docs/refactoring/audits/batch7s25_*` (снапшот-индекс 9 блоков,
deps-load/store, manifest-before/after/cmp по git-блобам, line-accounting
монолита и сервиса, callsites head/AST-cmp, path-attrs dump+cmp, verify 33/33,
app-check work/head-wt/cmp, restart work/head-wt/cmp, menu work/head-wt/cmp,
smoke-exit). Непокрытые проверки — §4 отчёта; новый пункт реестра **один: п. 45**
(home-экран «Recent projects»: панель `recent_projects_layout` в сборке не
создаётся, отрисовка проверена подставленным реальным `QVBoxLayout`; MOOT для
текущей сборки), остальное — ссылками на п. 12/13/21/25/29/30/33/35/36/43/44,
чтобы не дублировать сквозные пункты.

**РАСКРЫТИЕ ФАКТИЧЕСКОГО СУЖЕНИЯ SCOPE (занесено и в `EXTRACTION_PLAN.md`):**
план ожидал в S2.5 «голосовую часть S2.4 + recent-projects + миграции» — 10
методов / ~419 строк, после чего «будет закрыто 33 из 33 методов Stage 2».
Координатор переопределил под-батч: перенесены ТОЛЬКО `load/save_recent_projects`
(2 метода / 74 строки), а голосовые методы (`load/save_dictation_settings`,
`load/save_voice_vocabulary_settings`, `load_language_settings`) и три миграции
(`_migrate_settings_to_unified`, `_migrate_to_workbench_layout`,
`_migrate_voice_dictation_default_off`) промпт прямо отнёс к СТРОГО NOT-MOVE.
Итог Step 7: **перенесено 25 методов** (S2.1 6, S2.2 3, S2.3 10, S2.4 4, S2.5 2),
остальное осталось в монолите сознательно — основания в итоговом блоке Step 7
`EXTRACTION_PLAN.md`

## Что дальше: Step 7 Stage 2 — под-батч S2.4 закрыт (Batch #7 Stage 2, 27.09.2026)

## Что дальше: Step 7 Stage 2 — под-батч S2.4 закрыт (Batch #7 Stage 2, 27.09.2026)

**S2.4 выполнен** (база HEAD `f600e00` РОВНО — ни потомков, ни расхождения; монолит
68 285 → **68 274** строки, −11; `git diff --numstat` 27/38, difflib — ровно 4
региона, сумма −11 == изменению файла). Перенесены 4 метода / 47 строк в
`modules/settings_service.py` (368 → 451 строка; методы 20 → 24) —
`_load_language_pair_from_disk` (402–419), `save_language_settings` (421–431),
`_save_spellcheck_settings` (433–442), `_load_spellcheck_settings` (444–451).
**Это первый под-батч Stage 2, где сработало стоп-условие «зависимость от состояния
окна»:** два тела перенесены ВЕРБАТИМ (`save_language_settings`,
`_load_spellcheck_settings`), а два — SPLIT-ом (документированная правка −3/+3 и
−2/+2): сервисный `_load_language_pair_from_disk` больше не пишет
`self.source_language`/`target_language`, а ВОЗВРАЩАЕТ пару (на исключении — None),
и атрибуты окна пишет тонкий делегат (только при не-None результате);
сервисный `_save_spellcheck_settings(enabled)` больше не читает
`self.spellcheck_enabled` — значение передаёт делегат. В монолите — 4 тонких
делегата с исходными сигнатурами (4/4 signature_identical + forwards).
Ограничение промпта выполнено: единственный вызов `_load_language_pair_from_disk`
остался в `__init__` на строке 6348 (LOADS `source_language`/`target_language` в
`__init__` = 0, проверено AST и до, и после).

**Живой прогон (offscreen) — 11/11 PASS + отдельный процесс-перезапуск 4/4 PASS:**
- SPLIT подтверждён живьём: прямой вызов сервиса вернул пару и НЕ тронул атрибуты
  окна; делегат записал их; на искусственном исключении атрибуты остались
  нетронутыми, а сохранённая диагностика `[LangSettings] Load failed…` попала в stdout.
- Вкладка Language Pair проверена через РЕАЛЬНЫЙ обработчик
  `_save_language_settings_from_ui` (настоящие QComboBox); тумблер spellcheck — через
  РЕАЛЬНЫЕ `_toggle_spellcheck_from_button` и `_toggle_spellcheck` (в логе виден бэкенд
  `pyspellchecker (pl_PL)`); файл всегда равен состоянию окна.
- Перезапуск в ОТДЕЛЬНОМ интерпретаторе на изолированном каталоге данных (резолвер
  `get_user_data_path` подменён до создания окна): языковая пара и spellcheck
  подхватились из файла, а голосовой диктант в режиме «Auto (use project target
  language)» получил `language='pl'` из пережившего перезапуск `self.target_language`
  (контроль: 'ru'; автодетект → 'auto').
- Ровно 4 метода-соседа не тронуты байт-в-байт (8 NOT-MOVE-блоков, включая
  `load_dictation_settings`, найденный AST repo-wide); 8 метрик 1211/18/35/24/24/0/85/2
  без изменений (файлы до/после побайтово равны); манифест changed=2, added=0, removed=0;
  смоук save/load — `EXIT=0` и на рабочем дереве, и на worktree HEAD.

Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.4).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.4 languages-spellcheck).txt`;
аудиты: `docs/refactoring/audits/batch7s24_*` (снапшот-индекс 12 блоков,
deps-load/store, manifest-compare, line-accounting, callsites AST-compare,
per-file counts, verify 37/37, app-check JSON+лог, restart JSON+лог, smoke-exit).
Непокрытые проверки — раздел 4 отчёта (новый пункт реестра один: **п. 44** —
голосовой диктант с реальным аудио, переведён в **MOOT** (docs-follow-up): Voice-виджет
удаляется целиком в Batch #8, ручной голосовой тест не проводится; остальное дано
ссылками на п. 12/13/14/15/17/18/19/20/21/27, чтобы не дублировать сквозные пункты).

**РАСКРЫТИЕ ДВУХ ФАКТИЧЕСКИХ ПОПРАВОК** (обе занесены в `EXTRACTION_PLAN.md`):
1) состав «S2.4 = 9 методов / ~203 строки» на этом шаге НЕ выполнялся целиком —
   координатор исключил голосовую часть, поэтому под-батч = 4 метода / 47 строк;
2) утверждение промпта «остальные 3 кандидата используют
   `_load_settings_section("ui")`» неверно: разделение API фактическое 2/2
   (`save_language_settings` и `_save_spellcheck_settings` пишут через whole-file
   API, два оставшихся читают секционным). Асимметрия сохранена «как есть».

**Дальше — S2.5 «голосовая часть + recent-projects + миграции», 10 методов / ~419 строк.**
Границы ПЕРЕСЧИТАНЫ AST на этом дереве (после переноса −11; номера ниже 52 249
сместились, ниже 44 991 — тоже):
    load_recent_projects                    32326–32388 (63)
    save_recent_projects                    32390–32400 (11)
    _migrate_settings_to_unified            44744–44834 (91)
    _migrate_to_workbench_layout            44836–44901 (66)
    load_dictation_settings                 44918–44933 (16)   ← голосовая часть
    save_dictation_settings                 44935–44989 (55)   ← SPLIT (QMessageBox)
    load_voice_vocabulary_settings          45015–45053 (39)   ← голосовая часть
    save_voice_vocabulary_settings          45055–45078 (24)   ← голосовая часть
    _migrate_voice_dictation_default_off    45129–45160 (32)   ← 3-я миграция
    load_language_settings                  45214–45235 (22)   ← SPLIT (TagHighlighter +
                                                                  spellcheck_manager)
NOT-MOVE-остаток (не переносить без решения владельца):
`load_general_settings` 44542–44638 (97), `save_clipboard_privacy_settings`
44721–44742 (22), `get_autocorrect_settings` 44640–44651 (12, тир C),
`load_font_sizes_from_preferences` 45256–45342 (87, тир C — ссылается на классы
монолита). После S2.5 будет закрыто 33 из 33 методов Stage 2 (23 закрыто S2.1–S2.4).
**ПРОГНОЗ НЕ ПОДТВЕРДИЛСЯ:** координатор сузил S2.5 до `load/save_recent_projects`,
поэтому Step 7 закрыт на **25 методах**; голосовая часть и три миграции остались в
монолите сознательно. Правка прогноза — `EXTRACTION_PLAN.md`, блок «ПОПРАВКА К
ПРОГНОЗУ S2.4» и «ИТОГ Step 7 — ЗАКРЫТ ЦЕЛИКОМ».

## Что дальше: Step 7 Stage 2 — под-батч S2.3 закрыт (Batch #7 Stage 2, 27.09.2026)

**S2.3 выполнен** (база HEAD `7a2de37` — потомок `4c7ad680`; монолит 68 373 →
**68 285** строк, −88; `git diff --numstat` 47/135, difflib — ровно 10 регионов,
сумма −88 == изменению файла). Перенесены 10 методов / 150 строк в
`modules/settings_service.py` (197 → 368 строк; методы 10 → 20) — `load_llm_settings`
(в сервисе 210–248), `save_llm_settings` (250–257), `load_proxy_settings` (259–275),
`save_proxy_settings` (277–284), `_get_proxy_url` (286–308), `_get_proxy_dict`
(310–317), `load_provider_enabled_states` (319–345), `save_provider_enabled_states`
(347–354), `load_api_keys` (356–364), `save_api_keys` (366–368). Тела — ВЕРБАТИМ
(10/10, sha256 == снапшотам HEAD); новых параметров конструктора не потребовалось
(единственные внешние зависимости — методы самого сервиса + stdlib `urllib.parse`);
в монолите — 10 тонких делегатов с исходными сигнатурами (10/10
signature_identical + forwards), приватные имена `_get_proxy_url`/`_get_proxy_dict`
сохранены. `_get_api_keys` (11452) НЕ трогался (сторонний
`modules/llm_clients.load_api_keys`).

**Риск-приоритеты закрыты прямыми тестами (offscreen, 14/14 PASS):**
- ★ RISK #1 — ПЯТЬ НЕЗАЩИЩЁННЫХ вызовов `PreTranslationWorker`
  (`self.parent_app.load_api_keys()` без guard): 5637, 5660, 5730, 5943, 5995 —
  все пять вызваны под фейковым LLMClient; счётчик на СЕРВИСНОМ методе доказал
  цепочку делегат→сервис; плюс полный `wk.run()`; негативный контроль показал
  AttributeError без делегата.
- RISK #2 — hasattr-guarded сайты LLM-чата: реальный `ChatBackend(w, …)` поднял LLMClient
  через guard; «тихого» провала в дефолт нет.
- SuperlookupTab-сайт (`_perform_mt_lookup`) — оба делегата реально вызваны.
- Дефолты на пустом файле, цепочка прокси (с percent-encoding), миграция
  google→gemini, отсутствие кэша (3 вызова = 3 открытия), цикл записи на КОПИИ
  user_data (соседние секции сохранены), продовый settings.json sha не изменился.

Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.3).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.3 llm-proxy-keys).txt`;
аудиты: `docs/refactoring/audits/batch7s23_*` (снапшот-индекс, manifest-compare,
line-accounting, callsites AST-compare, per-file counts, verify, app-check JSON+лог).
Непокрытые проверки — раздел 4 отчёта (M1–M13; главные: реальный сетевой вызов LLM/MT,
настоящие клики в модальных окнах Settings, полный человеческий цикл — после S2.4/S2.5).

**Дальше — S2.4 «языки / диктовка / словарь / спеллчек», 9 методов / ~203 строки** —
**ВЫПОЛНЕН, см. раздел S2.4 ВЫШЕ** (код перенесён по 4 методам вместо 9: голосовая
часть вынесена в S2.5 решением координатора). Границы были выведены AST ЗАНОВО
(после сдвига −88). После S2.3 в Stage 2 было перенесено 19 из 32 методов.

## Что дальше: Step 7 Stage 2 — под-батч S2.2 закрыт (Batch #7 Stage 2, 26.09.2026)

**S2.2 выполнен** (база HEAD `25627c9` — потомок `3e5c100c`; монолит 68 400 →
**68 373** строки, −27: делегаты −34, комментарии +7; `git diff --numstat` 23/50).
Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.2).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.2 general).txt`;
аудиты: `docs/refactoring/audits/batch7s22_*` (манифест до/после + сравнение,
counts, analysis, snapshot_index, verify, line_accounting, quotes, app_check_run2,
bug_head_probe, smoke_save/load).

**Что сделано:** в `modules/settings_service.py` (113 → 197 строк) добавлены три
метода общего слоя ВЕРБАТИМ-переносом (sha256 тел совпадают со снапшотами HEAD):
`load_clipboard_privacy_settings` 140–149, `_load_general_settings_from_file`
151–190, `save_general_settings` 192–197. В монолите на месте их тел — три тонких
делегата с исходными именами и сигнатурами: `load_clipboard_privacy_settings`
44711–44719, `_load_general_settings_from_file` 44903–44909,
`save_general_settings` 44911–44916. Новых параметров конструктора НЕ потребовалось:
тела зависят только от `_load_settings_section` / `_save_settings_section` / `log`
(измерено AST — §1.3 отчёта), т.е. всё уже есть в сервисе.

**Сохранение бага бит-в-бит:** делегат `save_general_settings` оставлен БЕЗ default
у обязательного `settings` (AST: `defaults = []`), поэтому вызов без аргумента
падает тем же `TypeError`, что и до переноса. Проверено ДО/ПОСЛЕ на worktree HEAD
25627c9 (`audits/batch7s22_bug_head_probe.*`) — текст ошибки совпадает посимвольно.
Дополнительно выяснено (новое): оба баговых сайта (теперь 66753 и 66796,
SuperlookupTab) защищены `hasattr(<окно>, 'general_settings')`, а такого атрибута в
монолите НЕ СУЩЕСТВУЕТ → путь сегодня мёртв, баг спит (кандидат в
VALIDATION_BACKLOG для решения владельца, НЕ из S2.2).

**NOT-MOVE:** `load_general_settings` 44542–44638 (97 строк) — код не тронут
вообще, байт-в-байт как в HEAD; его внутренний вызов
`self._load_general_settings_from_file()` продолжает работать через делегат (это и
есть выполнение V3-требования SPLIT — отдельного разделения тела не делалось).
`save_clipboard_privacy_settings` (44721–44742) тоже остался в монолите (V3).

**Валидация:** py_compile OK (144 файла); 8 метрик 1211/18/35/24/24/0/85/2 — до и
после идентичны; манифест 144 → 144 (changed=2: `Supervertaler.py`
80993e2f…, `modules/settings_service.py` 02914e1f…; added/removed = 0); difflib —
ровно 5 неравных регионов, все заявленные, сумма −27 == изменению файла; живой
offscreen-прогон приложения — **9/9 PASS** (делегаты == сервис, 4 внутренних
потребителя, getattr-путь `modules/clipboard_manager_widget.py:771` с реальным
виджетом и маркером из файла, полный цикл save→файл→load→окно→виджет на КОПИИ
user_data, продовый settings.json побайтово не изменился, «3 вызова = 3 открытия»);
смоук save/load OK (`SAVE_OK 6584`, `LOAD_OK S22Smoke 7`) и одинаково на обоих
деревьях. Непокрытые проверки — §4 отчёта (главные: настоящие клики в модальных
диалогах; запись clipboard-настроек через UI; полный человеческий цикл
«изменить каждую вкладку → перезапуск» — после S2.3/S2.4; N14 — продовые user-data
затрагивались дважды, оба раза контролируемо и откатано).

**Дальше — S2.3 «LLM / proxy / provider / api keys», 10 методов / 150 строк**
(ровно на границе конвенции ≤10 — отметить в отчёте явно):
`load_llm_settings`, `save_llm_settings`, `load_proxy_settings`,
`save_proxy_settings`, `_get_proxy_url`, `_get_proxy_dict`,
`load_provider_enabled_states`, `save_provider_enabled_states`, `load_api_keys`,
`save_api_keys`; fan-in ~116, ~10 вызовов из `modules/` + ~10 строковых, часть имён
приватные. Границы вывести AST ЗАНОВО на дереве S2.2 (после −27 документированные
номера сдвинуты).

## Что дальше: Step 7 Stage 2 — под-батч S2.1 закрыт (Batch #7 Stage 2, 25.09.2026)

**S2.1 выполнен** (база HEAD `043da2a`, монолит 68 386 → **68 400** строк; прирост
+14 разобран замером: импорт +1, блок делегатов −6, проводка в `__init__` +10 и в
`_reinitialize_with_new_data_path` +9 — `git diff --numstat` 47/33 по одному файлу,
но уточнение регионов см. §8.1 отчёта и `audits/batch7s21_line_accounting.txt`). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 2 (S2.1).txt`; промпт:
`docs/refactoring/prompts/Promt - EXTRACTION BATCH #7 STAGE 2 (S2.1 settings core).txt`;
аудиты: `docs/refactoring/audits/batch7s21_*` (манифест до/после + сравнение, counts,
callsites, verify, class_shape, snapshot_index, remaining_ast, app_check_run{1,2,3},
smoke-*) и `not_moved_methods_batch7stage2s21_snapshot.txt`.

**Что сделано:** новый класс `SettingsService` (`modules/settings_service.py`,
113 строк; конструктор с ЯВНЫМ `settings_dir` + опц. `log`, без ConfigManager) с
6 методами ядра (`_get_settings_dir`, `_get_unified_settings_path`,
`_load_unified_settings`, `_save_unified_settings`, `_load_settings_section`,
`_save_settings_section`; 5 тел перенесены БАЙТ-В-БАЙТ, 1 строка — инъекция пути).
В монолите на их месте — 6 тонких делегатов (44639–44696) с исходными именами и
сигнатурами, строка импорта (421), конструктор сервиса в `__init__` (6301–6309) и
ПЕРЕПРИВЯЗКА сервиса первым оператором `_reinitialize_with_new_data_path()`
(6668–6676) — без неё смена каталога данных (`user_data_path` переприсваивается в
6630/6934/22859, все три ведут в этот метод) оставила бы делегаты и ещё не
перенесённые миграции на старом пути.

**Валидация:** py_compile OK (144 файла); 8 метрик 1211/18/35/24/24/0/85/2 — без
изменений; манифест 143→144 (changed=1, added=1, removed=0); живой offscreen-прогон
приложения — **13/13 PASS** (main():68370 `window._load_settings_section("ui")`,
getattr-пути `modules/voice_tab.py` и `modules/clipboard_manager_widget.py`,
save-путь General-вкладки, полный цикл save→файл→load→окно на КОПИИ user_data,
перепривязка при смене каталога; «4 вызова = 4 открытия файла» — кэша нет);
смоук save/load OK (LOAD_OK и на S2.1, и на HEAD-worktree; краш 0xC0000005 на
teardown идентичен на обоих — предсуществующий, вне скоупа). Непокрытые проверки —
раздел 4 отчёта (главные: настоящий клик Save в модальном диалоге не нажимался;
полный человеческий цикл «изменить каждую вкладку → перезапуск» — после S2.2–S2.4).

**Дальше — S2.2 «general + общий reading», 4 метода / 153 строки** — **ВЫПОЛНЕН
26.09.2026, см. раздел S2.2 выше** (границы пересчитаны AST после S2.1 — `docs/refactoring/audits/batch7s21_remaining_ast.txt`):
`load_general_settings` 44542–44638 (97 строк, SPLIT — применение 35 атрибутов
остаётся в монолите), `_load_general_settings_from_file` 44897–44936 (40),
`save_general_settings` 44938–44943 (6), `load_clipboard_privacy_settings`
44704–44713 (10); `save_clipboard_privacy_settings` 44715–44736 — НЕ переносится
(V3). **Открытый вопрос перед стартом S2.2 ЗАКРЫТ (25.09.2026, follow-up S2.1)**:
прямая цитата кода показала, что формы `getattr(self, 'load_general_settings', lambda: {})()`
нет ни в одном из 7 мест — везде `hasattr`-guard + обычное обращение к атрибуту
(`Supervertaler.py:1810–1811` на `parent()`-цепочке, `modules/quicktrans.py:302–303`
на `parent_app`, плюс 7881, 55559, 55568, 64711, 64726 на `self`/`mw`) → аудит Б1
подтверждён, формулировка Stage 1 §1.4 ошибочна; делегат с исходным именем сохраняет
все места работоспособными, «мягкого» duck-typing-контракта не требуется. Цитаты и
инвентарь: `docs/refactoring/audits/batch7s21_open_item_quotes.txt`; разбор — §8.2
отчёта S2.1.
Если за время паузы строки 44542–44943 или файлы `modules/{voice_tab,
clipboard_manager_widget,termbase_entry_editor}.py` трогали — границы и метрики
пересчитать AST заново перед переносом.
Прирост монолита S2.1 (+14 строк: импорт +1, делегаты −6, проводка в `__init__` +10 и
в `_reinitialize…` +9) подтверждён difflib-замером по всем 10 неравным регионам —
`docs/refactoring/audits/batch7s21_line_accounting.txt`, §8.1 отчёта S2.1.

## Что дальше: Step 7 — Stage 1 закрыт (Batch #7 Stage 1, 24.09.2026, read-only)

**Stage 1 выполнен** (HEAD `b5c46e7`, монолит 68 386 строк, sha256 блоба
`802c504c8849ac58551bece6b297917426e31226` — код не менялся). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #7 Stage 1.txt`; разбор 1.1–1.9:
`docs/refactoring/audits/step7_stage1_findings.md`; измерения:
`docs/refactoring/audits/batch7_stage1_{methods_ast,candidates_scan,inventory_tables,callsites_categorized,callsites_raw,dependencies,dead_dynamic_check,config_manager_overlap}.*`.

**Состав (подтверждён AST):** 35 методов / 830 строк = A (ядро API, 6 методов /
39 строк: `_get_settings_dir` 44639–44641, `_get_unified_settings_path` 44643–44645,
`_load_unified_settings` 44647–44661, `_save_unified_settings` 44663–44672,
`_load_settings_section` 44674–44676, `_save_settings_section` 44678–44682) + B
(29 доменных аксессоров, 791 строка). Миграции: `_migrate_settings_to_unified`
**44724–44814**, `_migrate_to_workbench_layout` **44816–44881**,
`_migrate_voice_dictation_default_off` **45143–45174** (третья, в плане отсутствует).
Тир C (не включать): `get_autocorrect_settings` 44620–44631,
`add/_remove/clear_recent_projects` 32238–32288 / 32290–32304 / 32416–32430,
`load_font_sizes_from_preferences` 45275–45361.
Не два окна из плана, а ≥9 кластеров в span **8481–61247**; «~25» плана ≈ ядро A+B,
«~46» координатора смешало A+B + тир C + одноразовые писатели секций (группа G3:
`_set_voice_pause_setting`, `save_termbase_code_map`, `_set_fr_demote_to_draft`,
`_persist_autocorrect_settings` и др. — все вне состава).

**Главные риски/факты:** `load_general_settings` = **61 call-сайт** (56 методов
`SupervertalerQt`, `PreTranslationWorker.run` 5479, `SuperlookupTab` 66766/66809,
`main()` 68357, `modules/quicktrans.py:303`) + 7 `getattr`-строковых обращений; это НЕ
чистый IO (2 строки чтения из 97 + 35 присваиваний `self.<attr>`) → SPLIT.
Семантика «файл читается заново на каждый вызов» подтверждена (кэшей нет). Дукт-тайпед
обращения из `modules/` есть и к ПРИВАТНЫМ именам (`_load_unified_settings`,
`_save_unified_settings`, `_load_settings_section`, `_save_settings_section`,
`_get_proxy_url`) → 35 тонких делегатов с исходными именами. ConfigManager:
`get_preferences_path/load_preferences/save_preferences` — дубликаты того же файла/секции
с 0 call-sites, а его резолвер user_data (`~/.supervertaler_config.json`) отличается от
монолитного (`%APPDATA%/Supervertaler/config.json`) → сервис не должен резолвить путь сам.
Наблюдения вне скопа: латентный баг `modules/termbase_entry_editor.py:121/131`,
дубликаты чтения `settings.json` (llm_clients/feature_manager/ui_scale), три механизма
указателя user_data.

**Решение владельца (V1–V4) перед Stage 2:** (V1) архитектура — рекомендация: новый
класс `SettingsService` в `modules/settings_service.py` с явным `settings_dir`
(+ опц. `log`), ConfigManager не расширять; (V2) не включать тир C; (V3) SPLIT для
`load_general_settings` и `_migrate_voice_dictation_default_off` обязателен, для
`save_clipboard_privacy_settings`/`save_dictation_settings`/`load_language_settings` —
на выбор; (V4) под-батч S2.5 (recent + миграции) с валидацией на копии user_data.

**Разбивка Stage 2+ (по риску):** S2.1 ядро API (6/39) → S2.2 general + общий reading
(5/175, fan-in 90) → S2.3 LLM/proxy/provider/api keys (10/150, ★ ровно на границе
конвенции 10 методов) → S2.4 языки/диктовка/словарь/спеллчек (9/203) → S2.5 recent +
миграции (5/263). Ни один под-батч не превышает 10 методов.


| 12 | TM / Termbase сервисы | ⬜ не начат | — |
| 13 | Перевод-ядро (вкл. PreTranslationWorker) | ⬜ не начат | — |
| 14 | SuperLookup + Voice + финальный cleanup | ⬜ не начат | — |

## История: Step 6 ЗАКРЫТ ЦЕЛИКОМ (Batch #6 Stage 4 — последний под-батч)

**Stage 4 выполнен** (18.09.2026, filters.py). Состав переноса: 20 методов
(20 pure-функций + 1 внутренняя `_refresh_grid_invisibles_cells`) в
`modules/grid/filters.py` (1277 строк) + 20 тонких делегатов в монолите с
точными исходными именами/сигнатурами (7 делегатов сохранили ведущий `_`,
одноимённые функции — без него). Замена выполнялась строго по AST-спанам
снизу вверх ПО ИМЕНАМ (кластер — не непрерывный блок; окно 51794–55821 на HEAD
содержит посторонние блоки: show_manage_views_dialog, `_refresh_source_column_
display`, spellcheck 52645–53126, comments/dictation 53510–55753).
AST: 22/22 совпало с координаторской таблицей байт-в-байт; 20 тел = 1097 строк →
20 делегатов = 291 строка + 1 строка импорта. Монолит **69 191 → 68 386**
(net −805; numstat: `Supervertaler.py` +222/−1027, `modules/grid/__init__.py`
+54/−3, новый `modules/grid/filters.py` 1277). Класс SupervertalerQt:
6053–63263 → 6054–62458; 819 методов / 838 членов до и после.
Стоп-условия не сработали: 8 метрик ровные (1211/18/35/24/24/0/85/2);
манифест — только монолит + `__init__.py` + новый `filters.py` (0 правок
внешних call sites подтверждено SHA256); 3 NOT-MOVE блока BYTE-IDENTICAL
(`show_manage_views_dialog` b3d00f39…, `_refresh_source_column_display`
90d2bf1b…, `_update_bulk_menu_label` 1d971a9a…); контрольные блоки spellcheck
9ac157cd… и comments/dictation 6496a472… — по 1 вхождению; сценарии фильтров
65/65 PASS (включая F11 apply_sort → reload_callback, единственное пересечение
с SCC#1); Undo/Redo Batch #5 — 38/38 PASS (третий прогон); smoke save/load OK.
Две находки вне «механического» скоупа: (1) предсуществующий бесконечный цикл
в `clear_filter_highlights_in_widget` при наложении+снятии подсветки в одном
диапазоне — воспроизводится и на HEAD, регрессии нет; (2) в этом же коммите
исправлен порядок записи настроек невидимых символов (write_settings_callback
теперь вызывается ДО refresh — как в исходном теле HEAD). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 4.txt`; сигнатуры:
`docs/refactoring/audits/batch6_stage4_signatures.txt`.
**Итог Step 6:** `modules/grid/` = helpers.py 507 + pagination.py 584 +
filters.py 1277 + `__init__.py` 134; 50 публичных функций + 51 делегат в
монолите. Документация Step 6 закрыта целиком.

**Дальше: СТОП — ждать решения владельца.** Следующий шаг плана — Step 7
(Settings service, IO-слой). Номера строк в `EXTRACTION_PLAN.md` для Step 7
устарели (Batch #1–#6 сдвинули монолит на −4951); предварительная AST-карта
после Stage 4 (только чтение, кандидаты IO — 46 методов, 1709 строк; UI-билдеры
вкладок исключены): `_get_settings_dir` 44639–44641, `_get_unified_settings_
path` 44643–44645, `_load_unified_settings` 44647–44661, `_save_unified_settings`
44663–44672, `_load_settings_section` 44674–44676, `_save_settings_section`
44678–44682, `load_general_settings` 44522–44618, load/save clipboard privacy
44690–44722, `_migrate_settings_to_unified` 44724–44814, general-from-file
44883–44929, dictation 44931–45002, language pair/language 45004–45021 и
45228–45261, voice vocabulary 45029–45092, spellcheck IO 52262–52280, llm/proxy
56987–57111, api keys 61235–61247, «недавние проекты» 32231–32430. Точный состав
и границы — пересчитать AST заново на старте Step 7 (как требует AGENTS.md).

**Stage 3 выполнен** (17.09.2026, pagination.py). Состав переноса: 14 методов
(14 pure-функций) в `modules/grid/pagination.py` + 2 module-level константы
`PAGE_AUTO_ALL_THRESHOLD`/`PAGE_FALLBACK_SIZE` (сняты с класса SupervertalerQt;
в классе остались только константы populate-кластера `BACKGROUND_POPULATE_*`).
AST-границы Stage 3: блок 28198–28717 (сдвиг −434 от чисел Stage 1; координаторская
таблица Stage 3 подтверждена БАЙТ-в-БАЙТ), внутри блока НЕ переносились
`_start_background_populate`/`_background_populate_step` (Step 8, populate-кластер).
Стоп-условия не сработали: 8 метрик ровные; манифест — только монолит +
`modules/grid/__init__.py` + новый `pagination.py`; SHA256 двух NOT-MOVE методов —
BYTE-IDENTICAL до/после; Undo/Redo-сценарий Batch #5 — 38/38 PASS;
stage3-сценарий 56/56 PASS; smoke save/load — OK. Монолит 69 428 → **69 191**
(net −237; diff stat: +178 / −376 по двум файлам). Отчёт:
`docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 3.txt`; сигнатуры:
`docs/refactoring/audits/batch6_stage3_signatures.txt`.
**Дальше: Stage 4 = filters.py** — отдельный промпт после GO владельца. Границы
для Stage 4 надо пересчитать AST заново (Stage 1 давал 52186–53901 + 56218–56280 +
28850–28878 — сдвиг после Stage 2/3 уже −434 и станет больше).

**Stage 2 выполнен** (17.09.2026, helpers.py). Состав переноса: 16 pure-функций
в `modules/grid/helpers.py` (модуль чистых функций — решение владельца §6 Stage 1;
без класса и ссылок на окно) + `_get_line_edit_text` оставлен в монолите целиком
(п.Г: getattr/setattr-логика self-специфична) + 17 тонких делегатов с исходными
именами/сигнатурами. Граница `_navigate_to_segment_by_id` уточнена AST:
54700–**54769** (не 54770). Валидация: 8 метрик ровные; SHA256-манифест — только
монолит + 2 новых файла; Undo/Redo-сценарий Batch #5 — 38/38 PASS (делегаты
_find_row_for_segment/_select_grid_row_by_id остались bound-методами);
stage2-сценарий 34/35 (единственный FAIL — предсуществующее поведение навигации
в offscreen, подтверждено идентичным before/after-пробой из worktree HEAD);
smoke save/load — OK. Отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 2.txt`;
сигнатуры: `docs/refactoring/audits/batch6_stage2_signatures.txt`.
**Дальше: Stage 3 = pagination.py (12 методов + 2 selection-micro, ~367–391
строк) — отдельный промпт после GO владельца; затем Stage 4 = filters.py.**

**Stage 1 выполнен** (16.09.2026, read-only, код не тронут). Главная находка:
документированные окна Step 6 в EXTRACTION_PLAN.md устарели сильнее, чем
ожидалось (сдвиг ~−3300, а не −531) и почти целиком указывают на посторонний
код (termbase/TM-поиск, proofreading, voice). Реальные кластеры найдены по
содержимому (AST): пагинация 28266–28878, фильтры/невидимые 52186–53901 +
56218–56280 + 28850–28878. Итоговый состав на перенос — **48 методов, ~1780
строк**: pagination.py 12 (367), filters.py 20 (1097), helpers.py 16 (316);
на решение ещё 3 метода (selection-micro, _navigate_to_segment_by_id,
show_manage_views_dialog). Цикл SCC#1: центр подтверждён
`load_segments_to_grid` 41428–41598; на уровне self-вызовов строгого цикла
нет (SCC=1; fwd=82/bwd=60) — цикл замыкается через populate-механику и
UI-сигналы; из кандидатов его касается ТОЛЬКО `apply_sort` (2 прямых вызова,
разрыв — reload_callback параметром). DYNAMIC_ENTRY_POINT: 9 методов
(go_to_prev/next_page, select_range_page_up/down, on_page_size_changed,
_on_file_filter_changed, toggle_all_invisibles, show_advanced_filters_dialog,
filter_on_selected_text) — обязательны делегаты. Реальные внешние связи — 3
bound-метода в modules/undo_manager.py (переживают перенос при сохранении
делегатов). Рекомендация: helpers.py — функции; pagination.py/filters.py —
классы-контейнеры; под-батчи Stage 2=helpers → 3=pagination → 4=filters.
Полный отчёт: `docs/refactoring/reports/ОТЧЁТ Batch #6 Stage 1.txt`;
аудиты: `docs/refactoring/audits/batch6_stage1_{windows_ast,cluster_layout,
named_helpers_ast,scc1,cycle_intersections,callsites_categorized,
dependencies}.txt`. Ожидание решения владельца (6 открытых вопросов в §8
отчёта) → Stage 2.

Фактические AST-границы окна бывшего Step 5 в монолите (HEAD после Stage 2,
пересчитаны AST — документированные номера в CODE_MAP_REFACTOR.md устарели):
- Делегаты UndoManager: `record_undo_state` 9395–9397, `record_undo_states_batch`
  9399–9401, `undo_action_handler` 9403–9405, `redo_action_handler` 9407–9409,
  `_apply_undo_redo_action` 9411–9413, `_push_structural_undo` 9618–9620,
  `_apply_structural_history` 9704–9706, `update_undo_redo_actions` 9708–9710.
- Перенесены в Stage 2 (теперь делегаты modules/grid/helpers.py):
  `_segment_for_grid_row` 9416–9420, `_recompute_list_numbers` 9640–9643,
  `_reindex_grid_rows_from` 9645–9648, `_select_grid_row_by_id` 9650–9655.
- Остаток окна (кандидаты пагинации Stage 3 / монолит): `_split_segment_at_row`
  9422–9463, `_merge_segment_at_row` 9465–9499, `_delete_segments_at_rows`
  9501–9549, `delete_current_segments` 9551–9573, `split_current_segment`
  9576–9605, `merge_current_segment` 9607–9616, `_sync_after_structural`
  9622–9638, `_split_segment_grid_fast` 9657–9683, `_merge_segment_grid_fast`
  9685–9702, `create_quick_access_toolbar` 9712–9755.

Состояние `PreTranslationWorker` после Batch #4: перенесён в монолите на
5337–6043, содержимое байт-в-байт без изменений (относится к Step 13).
Справка по перенесённым в Batch #4 воркерам: `modules/workers/`
(`TMSearchWorker`, `ProofreadWorker`, `GlossaryExtractionWorker`); их callsites
в монолите: 18787 (glossary), 48152 (proofread), 63214 (TM search). Базовые
метрики, снимки и проверки — по чек-листу «Общая валидация» в `EXTRACTION_PLAN.md`
и практикам `AGENTS.md` (разделы про батчи #2/#3a–#4 и `tools/batch_validation/`).

## Важные решения и подводные камни (не перечитывать всё)

- **Tag-грамматики**: в `modules/tag_manager.py` намеренно живут ДВЕ несовместимые
  реализации (монолит-блок и TagManager-методы) — НЕ объединять и не переключать
  callsites. Детали: «TECH-DEBT» в конце `EXTRACTION_PLAN.md`.
- **Документированные диапазоны строк в плане устаревают после каждого батча** —
  границы классов пересчитывать через AST (`ast.parse`, `lineno`/`end_lineno`).
- **Метрика `singleShot` ловит упоминания в докстрингах/комментариях** (Stage 3: один
  «лишний» singleShot дал ложный DIFF, пока упоминание не перефразировали). Формулировки
  в перенесённых докстрингах не должны содержать самих метрик-паттернов.
- **Позиционные аргументы pure-функций**: у Stage 3 при первой сборке делегат передавал
  `_page_size_decided_for` в мёртвый второй параметр (`grid_page_size`) — combo молча не
  обновлялся. Все новые pure-функции вызывать с явными ключевыми аргументами, а
  неиспользуемые параметры не заводить (найдено функциональным сценарием P13/P14).
- **Offscreen-квирк фокуса таблицы**: на непоказанном виджете `table.setCurrentCell()`
  не меняет `currentRow` (было и на HEAD — проба `probe_head_vs_work.py`); в тест-харнессах
  резервный путь — `selectionModel().setCurrentIndex(...)`, а фокус-сдвиги
  `select_range_page_*` проверять по `selectedRanges()`.
- **Delegates сохраняют сигнатуру БАЙТ-В-БАЙТ, включая обязательные аргументы**:
  если до переноса метод требовал позиционный аргумент, делегат НЕ получает
  `default` — иначе «заодно починенный» баг меняет наблюдаемое поведение вне
  скоупа переноса. Проверять это AST-ом (`args.defaults == []`), а не глазами
  (Batch #7 S2.2: `save_general_settings`, два пред-существующих сайта без
  аргумента). Комплект проверки — сравнение поведения на `git worktree` HEAD.
- **Guard-атрибут может быть мёртвым**: `hasattr(<окно>, 'general_settings')`
  выглядит как защита, но такого атрибута в монолите нет вообще (0 присваиваний) →
  путь не исполняется, и «баг» не воспроизводится из UI. Прежде чем писать
  «пред-существующий баг срабатывает», проверять существование атрибута
  измерением (`hasattr` на живом окне), а не по тексту guard.
- **git в этом окружении**: репозиторий принадлежит другому пользователю
  (`dubious ownership`), поэтому все команды запускать как
  `git -c safe.directory=E:/Dev/SupervertalerPortable …` (в т.ч. из Python-скриптов
  через `subprocess`), НЕ меняя глобальный git-config.
- **Пользовательские данные** не следуют за cwd: `get_user_data_path()` резолвится от
  глобального `~/.supervertaler_config.json` — read-only пробы безопасны везде, smoke-тесты
  пишут в продакшн-данные.
- **Git**: ветка `main`, история переписана на noreply-адрес
  (`328762441+dcdlab-ai@users.noreply.github.com`); репозиторий —
  github.com/dcdlab-ai/SupervertalerPortable (private). Материалы батчей — в
  `docs/refactoring/{prompts,reports,audits}/`, в корень не складывать.

## Конвенция обновления этого файла

В конце каждого шага/батча: обновить строку таблицы прогресса, дату, счётчик строк
монолита, раздел «Что дальше» (с фактическими AST-границами) и блок «Важные решения»
при появлении новых. Коммитить вместе с финальным коммитом батча.
