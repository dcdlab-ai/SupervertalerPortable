# Batch #9.4i — рекон (Этап 1, база 6c653b9b / код после 9.4h 3f9554dd)

## Baseline (Этап 0)
- Supervertaler.py 55 004 строк, SHA a3ced13deaf5, CRLF
- modules/quicktrans.py 1 642 строк, SHA c443c5e87509, LF
- Статика: chain 875/0; pyflakes 549 (undefined 126/4: tk 100, messagebox 19, filedialog 2, ttk 5);
  py_compile канон 109/0 (справочный 186/0); headless 90/2 (setuptools, fitz — известные); grep-gate чистый.
- Offscreen: fb S1–S5 OK; profiles SAVE/EXEC OK; qtchat OK; statusbar OK; e2e verdict OK;
  S-clean/S-upgrade PROBE OK (HASH-DIFF пуст); regress 6 sha (5a12501f/44828d90/c413d563);
  smoke 42; termbase OK; about OK; save ALL OK; r9 a/ctrl/rm OK.

## п.1 — все места mtql_custom_openai (grep во всех формах, без docs/)
| # | Файл:строка | Роль |
|---|---|---|
| 1 | Supervertaler.py:20092 | таб: `custom_cb.setChecked(mt_quick_settings.get("mtql_custom_openai", False))` — чтение при построении |
| 2 | Supervertaler.py:20094 | реестр `self._mtql_checkboxes["mtql_custom_openai"] = custom_cb` → Save пишет ключ |
| 3 | Supervertaler.py:20090–20114 | мастер-строка `custom_row` (чекбокс + read-only поле модели + stretch, `llm_layout.addLayout`) |
| 4 | Supervertaler.py:20117 | комментарий «Master checkbox … gates the group» |
| 5 | modules/quicktrans.py:353–358 | гейт `_add_llm_providers`: `if not mt_quick_settings.get('mtql_custom_openai', False): return` |
| 6 | Supervertaler.py:20159 | Save: цикл по `_mtql_checkboxes` (пишет все ключи реестра) |
| 7 | Save пересобирает секцию с нуля: `general_settings['mt_quick_lookup'] = mt_quick_settings` → ключи вне реестра исчезают при Save |

Читатели `mtql_custom_openai_model`: таб 20103 (profile_display), 20111 (реестр `_mtql_llm_combos` → Save),
quicktrans.py:407 (legacy-чип «Custom»). Динамической сборки ключей (`mtql_%s`, f-строки) нет.
Других читателей (getattr, тултипы, реестры) нет → **СТОП не срабатывает**.

## п.2 — read-only поле модели
После удаления мастера поле теряет смысл (модели показаны в подписях чекбоксов профилей
«Profile A – model-a»). Readers поля: 20103 (сам таб), 20111 (реестр→Save), quicktrans.py:407
(legacy-чип, умирает вместе с ним). Побочных эффектов нет → **поле удаляется вместе с мастером**.
Реестр `_mtql_llm_combos` остаётся пустым механизмом (Save-цикл по пустому dict — no-op).

## п.3 — сценарии «без мастера»: вход → ожидаемые чипы
(profiles = custom_openai_profiles с непустым endpoint; enabled = mtql_llm_profiles)
| Вход | Ожидаемые чипы |
|---|---|
| P=[A,B], enabled=[A,B] | A, B |
| P=[A,B], enabled=[B] | B |
| P=[A,B], enabled=[] | fallback: глобальный активный (A) → чип A, перевод с ключом A |
| P=[A,B], enabled отсутствует | A, B (все с endpoint) |
| P=[A,B], enabled=[Ghost] (имена устарели) | fallback: активный → A |
| P=[A,B], enabled=[], active='Ghost' (dangling) | `_get_active_custom_profile` → первый с endpoint → A |
| P=[] (все удалены), плоский endpoint есть | SettingsService мигрирует в профиль «Custom Endpoint» → чип «Custom Endpoint» |
| P=[], плоского endpoint нет | чипов нет, ошибок нет (legacy-чип 407 удаляется) |
| P=[A(endpoint пуст), B] | только B |
| старый файл mtql_custom_openai=false/true/отсутствует | одинаковый результат (ключ игнорируется) |

## п.4 — старый ключ mtql_custom_openai в существующих settings.json
Не читается (гейт и таб не читают). Не удаляется и не перезаписывается: Save пересобирает
секцию с нуля → нужен явный перенос инертных ключей из старой секции
(`mtql_custom_openai`, `mtql_custom_openai_model`) в новую. Отсутствующий ключ остаётся отсутствующим.

## Реализация (Этап 2, 2 коммита)
- 9.4i-1 (Supervertaler.py): удалить мастер-строку+поле (20089–20114, сохранив load_llm_settings),
  обновить комментарий 9.4f, в Save переносить инертные ключи.
- 9.4i-2 (modules/quicktrans.py): удалить гейт (353–358) и legacy-чип (402–408); порядок:
  профили по enabled → fallback активного (9.4h) → ничего не настроено = чипов нет.
