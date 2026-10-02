# Манифест синхронизации с апстримом — серия U1 (v1.10.371 → v1.10.372)

**Дата:** 2026-10-02 · **Состояние на:** `05da99de` (origin/main)
**База апстрима:** v1.10.371 · **Цель:** v1.10.372 (`a58572276b4fced9384cf64580237c9edee75007`)
**Общей git-истории нет** (Portable импортирован файлами) — все сравнения тег-к-тегу внутри апстрима;
копирование из тега — только `git checkout v1.10.372 -- <путь>`; методы монолита — по именам с AST-проверкой.

**Итог: база апстрима обновлена ЧАСТИЧНО до v1.10.372** — перенесены классы A/B
(данные, настройки, фиксы TM/тегов/хоткеев, сегментация); класс D (новые фичи),
QA-фичи и служебные файлы апстрима — не перенесены (см. §3–§4). Держатели решений:
[Stage 1](UPSTREAM_SYNC_STAGE1_REPORT.md) §5–§8, отчёты под-батчей.

---

## 1. Перенесено (хронология под-батчей)

| Под-батч | Кодовый коммит Portable | Коммиты апстрима | Что перенесено | Отчёт |
|---|---|---|---|---|
| U1.1 Данные и цены | `a7746d65` | `8e8be3d4`, `0d5375e0` | `modules/llm_pricing.py`, `modules/pricing.json`, `modules/chat_backend.py` — ЦЕЛИКОМ из тега (blob == тег) | [U1_1_U1_2](UPSTREAM_SYNC_U1_1_U1_2_REPORT.md) §2 |
| U1.2 Настройки | `f5c460e9` | `75a621a1`, `b3f76ee7`, `f5bfefc9`, `626d4c63`, `da403a48` | `unified_prompt_manager_qt.py`, `platform_helpers.py`, `llm_clients.py`, `pdf_rescue_Qt.py`, `prompt_assistant.py`, `keyboard_shortcuts_widget.py` — ЦЕЛИКОМ; монолит — 5 мест (f5bfefc9), `_save_general_settings_from_ui` + 4 AHK-сайта (626d4c63), Ollama timeout (da403a48: `__init__` + `_apply_ollama_timeout_setting`); `settings_service.py` — дефолт `claude_model` вручную | там же §3 |
| U1.3a TMX-импорт | `a1f76985` | `fe1a7d0a` | `translation_memory.py`, `tm_metadata_manager.py` — ЦЕЛИКОМ; монолит — 8 хунков / 3 метода вручную | [U1_3](UPSTREAM_SYNC_U1_3_REPORT.md) §2 |
| U1.3b Фиксы TM / F&R | `2e258269` | `ee75e3be` | `database_manager.py` — ЦЕЛИКОМ; **новый** `tm_replace.py` — ЦЕЛИКОМ; монолит — 7 хунков / 3 метода + 1 новый вручную | там же §3 |
| U1.4a Ядро сегментации | `5c052c9d` | `763291e8` (часть) | `simple_segmenter.py` — ЦЕЛИКОМ; **новый** `segmentation_rules.py` — ЦЕЛИКОМ; `models.py` +1 (`Segment.join_before`); `segment_split_merge.py` — **ДЕЛЬТА, см. §2.1**; монолит — 14 хунков (все пути импорта/экспорта на новый API с правилами ПО УМОЛЧАНИЮ) + `_load_segmentation_rules` + `_make_sentence_segmenter` | [U1_4A](UPSTREAM_SYNC_U1_4A_REPORT.md) |
| U1.4b Страница настроек | `426a09e2` | `763291e8` (остаток) | **новый** `segmentation_rules_widget.py` — ЦЕЛИКОМ (380 строк, blob `60c55579`); монолит: `create_segmentation_rules_tab` → фабрика, новый `_save_segmentation_rules`, удалены заглушка и `test_segmentation_rules` | [U1_4B](UPSTREAM_SYNC_U1_4B_REPORT.md) |

Docs-коммиты серии (без кода): отчёты Stage 1, U1.1/U1.2, U1.3, U1.4a (вкл. правки),
U1.4b (вкл. результаты T5.x 8/8 ОК и правки §6.1/§8), настоящий манифест.

## 2. Перенесено ЧАСТИЧНО (обязательные отметки)

1. **`modules/segment_split_merge.py` = 763291e8 БЕЗ 34a4c661.** В диапазоне 371..372
   файл трогают два коммита: 34a4c661 (класс D, «Вставленный исходник в существующий
   проект», не переносился) и 763291e8. Перенесена только дельта 763291e8
   (`git diff 34a4c661 763291e8 -- modules/segment_split_merge.py`, применена на
   состояние 371). В файле **нет** апстримных `split_source_text` и импорта `Callable`
   из 34a4c661; ссылок на `split_source_text` в Portable нет
   (`grep -rn "split_source_text" Supervertaler.py modules/` — 0). При будущем
   переносе 34a4c661 сверять файл с `v1.10.372` нельзя — только дельта от текущего
   состояния.
2. **Хунк #2 763291e8 (`add_source_text_to_project`) — вне объёма НАВСЕГДА.** Метод
   в Portable отсутствует (добавлен 34a4c661, класс D); `ssm.split_source_text` в
   монолите — 0 вхождений. Хунк применяется к несуществующему контексту; переносим
   только вместе с 34a4c661/ad910e96 (отдельное решение).
3. **`CHANGELOG.md` апстрима не переносился** (+30 в 763291e8; в U1.3 — аналогично):
   в Portable файла нет и не было, файл не входит в разрешённые файлы ни одного
   под-батча. Как и **`FAQ.md`** (da403a48) — пропущен с вопроса Q2 отчёта U1.1/U1.2.
4. **763291e8 перенесён в два приёма** (U1.4a ядро / U1.4b страница настроек) —
   после U1.4b перенесено всё, кроме п. 2–3 этой секции.
5. Тесты апстрима (`tests/test_segmentation_rules.py`, `tests/test_tm_replace.py`,
   `tests/test_tmx_import_languages.py`) в репо **не добавляются** — запускаются из
   временных копий вне репо (12/12, 12/12, соответствующие прогоны в отчётах).

## 3. Пропущено ОСОЗНАННО — отложено (класс D / QA, решения Stage 1 §5–§8)

| Коммит | Issue | Что это | Статус |
|---|---|---|---|
| `09d374e1` | #209 | QA: сохраняемые find-only проверки (новые `qa_checks.py`, `qa_checks_dialog.py`, touch `find_replace_qt.py`) | отложен (QA-фича в Portable отсутствует целиком) |
| `2e9192f5` | #233 | QA: LanguageTool | отложен |
| `2386c976` | #226 | Ремонт съехавших numbered-тегов (`tag_repair.py` + вставки в `PreTranslationWorker`) | отложен |
| `f6d9c279` | #78 | Тёмная тема: деревья/списки (`dark_style_adapter.py` + theme_manager) | отложен |
| `1f8cad19` | #194 | Inline Codes (2 новых файла + ~12 хунков монолита; требует перенесённых QA/`qa_checks`) | отложен |
| `05720a55` | #214 | Settings autosave | вне объёма (Stage 1 §3.11) |
| `34a4c661` | #173 | Вставленный исходник в существующий проект (`add_source_text_to_project`) | отложен (см. §2 п. 2) |
| `ad910e96` | #248 | Обновление проекта из вставленного bilingual-текста | отложен |
| `8206153d` | — | «Remove v1.10.372 release handoff» (служебная чистка) | не входит в объём |

Порядок и условия переноса класс D — в Stage 1 §5 (U1.5+ после Batch #8); при
переносе перепроверять план файлов заново (состав touching-коммитов может меняться).

## 4. Пропущено навсегда (класс C — удаляемые в апстриме фичи)

Voice, Clipboard-фича, CAT-интеграции, Superbrowser, SetupWizard — в апстриме 371..372
это удаления кода, которого в Portable нет (класс C классификации Stage 1 §3);
переносу не подлежат. Отдельные примечания: Clipboard-часть f6d9c279 — №33 плана Stage 1.

## 5. Текущее состояние (после серии U1)

| Метрика | Значение |
|---|---|
| origin/main = HEAD | `05da99de` (push подтверждён Дмитрием после приёмки T5.x) |
| `Supervertaler.py` | **68 265** строк (старт серии: 68 224; SHA256 `5080fd5b…`) |
| `modules/*.py` | 137 файлов (старт: 134; +`tm_replace`, +`segmentation_rules`, +`segmentation_rules_widget`) |
| `py_compile` | 138/138 (монолит + 137 модулей) |
| Версия в `pyproject.toml` | осталась `1.10.371` — код версии Portable в серии U1 сознательно не менялся |
| Ручная приёмка | T4.1–T4.7 (U1.4a) и T5.1–T5.8 (U1.4b) — ОК без замечаний |
| PROJECT_STATUS.md | строка о частичном обновлении базы апстрима добавлена настоящим docs-коммитом |

Отчёты серии: [Stage 1](UPSTREAM_SYNC_STAGE1_REPORT.md) ·
[U1.1+U1.2](UPSTREAM_SYNC_U1_1_U1_2_REPORT.md) · [U1.3](UPSTREAM_SYNC_U1_3_REPORT.md) ·
[U1.4a](UPSTREAM_SYNC_U1_4A_REPORT.md) · [U1.4b](UPSTREAM_SYNC_U1_4B_REPORT.md).
