# Batch #8.3 — Удаление F1: вкладка Voice, voice commands, Settings-страница Voice

Дата: 2026-10-04. Исполнитель: ZCode. Репозиторий: dcdlab-ai/SupervertalerPortable.
Кодовый коммит: `91f7f8ac` «Batch #8.3: remove Voice tab, voice commands, Voice settings page (F1)».
База постановки: BATCH8_STAGE1_AUDIT_REPORT.md §2.1 F1/§4.1, BATCH8_A2 §2.5, BATCH8_2 (протокол).

## 0. Baseline и git-синхронизация (Этап 0)

| Проверка | Значение |
|---|---|
| HEAD до работ | `f513802c` (= origin/main, push разрешён и выполнен до старта) |
| git status | чисто; untracked только `.zcode/plans/…`, `.zcodeignore` (допустимо) |
| Дрейф-чек | `git merge-base --is-ancestor 7d9cf7dc HEAD` → OK (7d9cf7dc — Batch #8.2) |
| SHA256 Supervertaler.py | `86e88bb3e0d372b4eac7a86434d5429815eb4a97e872ddd47df515518174536f` (67641 строк) — совпал с заданным |
| modules/**/*.py | 136; py_compile 137/137 (136 модулей + монолит) |
| EOL | 139 файлов `i/lf w/lf`; 4 предсуществующих `i/lf w/crlf` (grid/filters.py, grid/pagination.py, tag_manager.py, undo_manager.py) — не тронуты |
| Защита 1 (резолв стартовой цепочки, ДО) | 768 вызовов self.X(), неразрешённых 0; цепочка расширена: static-список 8.2 + `create_settings_tab` + все `*_create_*_settings_tab`, найденные AST (динамически) |
| Защита 3 (pyflakes, ДО) | 720 предупреждений, из них **149 undefined names** (совпадает с 8.2; состав: tk×100, messagebox×19, …) |
| Offscreen-проба ДО | main_tabs 8: Editor, TMs, Termbases, AI, SuperLookup, Clipboard Manager, **Voice**, Settings; voice_tab_index/_voice_top_widget присутствуют; страницы Settings **17** (🎤 Voice между AI Settings и Clipboard); кнопка «🎤 Dictate (Ctrl+Shift+Space)» на месте; хоткеи при старте: `ctrl+alt+l, ctrl+alt+q, ctrl+alt+c, ctrl+shift+space, ctrl+alt+v` |

Артефакты: `D:\Temp\SupervertalerPortable\refactoring\b8-3\` (startup_chain_before/after.json,
undefined_names_before/after.txt, probe_before/after.log, recon_table.md, snapshots/).

## 1. Рекон (Этап 1)

Полная таблица имён (33 позиции), граница 8.3/8.4, таблица импортёров, индексы,
потребители и ShortcutManager — в `D:\Temp\...\b8-3\recon_table.md`. Ключевое:

### 1.1 Таблица имён (сводка)

Всё из постановки найдено; номера строк постановки устарели — AST дал фактические
границы (пример: `_create_voice_settings_tab` = 24970-25038, а не ≈25516-25584).
Дополнительно к постановке выявлены и удалены члены того же кластера:

* `_on_voice_command_ptt_release` (53535-53592) — в постановке не названа, но это
  слот command-PTT (подключён в `_get_command_ptt_release_poller` :53431);
* `_get_command_ptt_release_poller` (53399-53435) — потребитель только
  `_handle_command_ptt_press_hotkey` (удаляется);
* `_register_voice_command_ptt_deferred` (53456-53477) — вызовителей нет (осиротела
  после 8.2), мёртвый метод;
* `_check_ahk_installed` (24647-24653) — потребитель только voice_tab.py:745;
* `_open_voice_in_workbench` (25040-25054) — единственный вызов из кнопки
  удалённой Settings-страницы (:25013).

### 1.2 Граница 8.3/8.4 (п.2, call graph)

* **`on_dictation_complete`** (бывш. :54088) — путь диктовки (8.4), но первые строки
  обрабатывали голосовые КОМАНДЫ (`voice_command_manager.process_spoken_text` под
  флагом `voice_commands_enabled`). Решение: блок обработки команд — часть
  удаляемой фичи F1-команд → удалён целиком (включая чтение флага);
  диктовка маршрутизируется в `_insert_dictated_text` безусловно. Охрана
  `hasattr(..., 'voice_command_manager')` делала бы блок мёртвым — оставлять его
  значило бы оставить висячую ссылку. Ключ `voice_commands_enabled` в
  dictation_settings остаётся сиротой в user_data (по ТЗ). Это минимальная правка
  8.4-зоны, доказательство: блок не вызывается больше ниоткуда, `grep voice_command_manager`
  в монолите = 0.
* `start_voice_dictation` / PTT диктовки / `_handle_pushtotalk_hotkey` /
  `_get_voice_release_poller` — не тронуты (отдельный аккорд `voice_dictate`,
  отдельный poller).
* `_get_voice_hotkey_listener`: удалены только ветки `voice_command_ptt`
  (press/release); ветки `voice_dictate` и `voice_pause_alwayson` (зона 8.2/8.4)
  не тронуты.
* `voice_listener = None` (interlock, бывш. :6420) — оставлен.
* Единственная правка в дикт-методе: удалено последнее предложение комментария
  «Companion fix lives in _get_command_ptt_release_poller below» в
  `_get_voice_release_poller` (ссылка на удаляемый метод).

### 1.3 Импортёры модулей (п.3)

| Модуль | Импортёры | Решение |
|---|---|---|
| voice_tab.py | только `_ensure_voice_top_tab` (удален) | УДАЛЁН |
| voice_commands.py | Supervertaler.py:348 (удалён) + voice_command_dialog.py (удалён) | УДАЛЁН |
| voice_command_dialog.py | Supervertaler.py:349 (удалён) + voice_tab.py (удалён) | УДАЛЁН |
| vosk_model_manager.py | только voice_commands.py:1003 (удалён) | УДАЛЁН |
| voice_dictation.py | 0 (DEAD_CODE №8 подтверждён regex-грепом `modules\.voice_dictation\b` = 0) | УДАЛЁН |
| dictation_toast.py | start_voice_dictation :54068 (8.4) | ОСТАВЛЕН |
| mic_devices.py | voice_dictation_lite.py:125 (8.4) | ОСТАВЛЕН |
| voice_dictation_lite.py / voice_hotkey_listener.py / voice_release_poller.py / voice_vocabulary.py | живые импортёры 8.4-зоны | ОСТАВЛЕНЫ |

### 1.4 Индексы и сохранённое состояние (п.4)

* Все `*_tab_index` вычисляются как `count() - 1` в момент addTab — сдвиг безопасен.
* Навигация лейбловая с v1.10.161 (`_switch_main_tab`, циклы по tabText). Числовые
  last-resort fallback остаются корректными: AI=3, SuperLookup=4 (Voice стоял
  ПОСЛЕ Clipboard — индексы 0-5 не изменились; Settings 7→6).
* Сохранённой «последней вкладки»/страницы Settings в настройках нет (grep
  last_tab/restore_tab/settings.value(tab) = 0) — фолбэк не требуется.
* Страницы Settings: `mt_quick_lookup_tab_index`/`keyboard_shortcuts_tab_index`
  вычисляются при построении; переходы лейбловые.

### 1.5 Потребители вне кластера и охрана (п.5)

Неохраняемых обращений из остающегося кода к удаляемым именам НЕТ (Защита 2).
Допустимые остатки-упоминания: докстринг `modules/platform_helpers.py:2163,2172`
(ссылка на «проверенный паттерн» VoiceCommandManager._run_ahk_code — только текст,
platform_helpers не в списке правок), `HelpTopics.VOICE`/`SIDEKICK` в
help_system.py (константы-URL, потребитель был только voice_tab.py), комментарий
`tools/shortcut_overlap.py:21`, миграции `voice_commands.json`/`voice_scripts/`
(8.8), тултип колонки 🎤 термбаз «…in 🎤 Voice tab → …» (:17883 — зона 8.4,
колонку не трогаем по ТЗ).

### 1.6 ShortcutManager (п.6)

Удалена запись `voice_command_ptt` (бывш. :196-210) вместе с комментарием.
Legacy-мэппингов на неё нет (`_LEGACY_IDS` содержит только
`global_pushtotalk→voice_dictate`). `voice_dictate` остался (диктовка, 8.4).
keyboard_shortcuts_widget.py — voice-упоминаний нет (не правился).
settings_service.py — voice-дефолтов/методов нет (не правился).

## 2. Что сделано (файл | действие)

| Файл | Действие |
|---|---|
| Supervertaler.py | изменён: −484 строки (67641 → 67157) |
| modules/shortcut_manager.py | изменён: −13 строк (запись voice_command_ptt) |
| modules/voice_tab.py (1378 строк) | git rm |
| modules/voice_commands.py (1465 строк, вкл. ContinuousVoiceListener) | git rm |
| modules/voice_command_dialog.py (355 строк) | git rm |
| modules/vosk_model_manager.py (188 строк) | git rm |
| modules/voice_dictation.py (497 строк, dead) | git rm |

Итого кодовый коммит: 7 files changed, 17 insertions(+), 4397 deletions(-).

Монолит — удалены блоки (AST-границы из HEAD): `_ensure_voice_top_tab`,
`_populate_voice_commands_table`, `_reset_voice_commands`, `_check_ahk_installed`,
`_open_voice_scripts_folder`, `_create_voice_settings_tab`,
`_open_voice_in_workbench`, `_get_command_ptt_release_poller`,
`_register_voice_command_ptt_deferred`, `_on_voice_command_ptt_press`,
`_on_voice_command_ptt_release`, `_do_voice_command_ptt_stop`,
`_on_pynput_command_ptt`, `_handle_command_ptt_press_hotkey`; точечные правки —
импорты :348-349, две инициализации `voice_command_manager` (:6417, :6704),
вкладка-плейсхолдер (:9987-9989), `_voice_top_widget` (:9976), elif-ветка lazy
(:11674-11675), warm-up-строка и докстринги, регистрация Settings-страницы
(:20437-20439), tray jumper (:28959-28961), Esc-ветка и её докстринг,
keyPressEvent-fallback (:29181), ветки command-PTT в `_get_voice_hotkey_listener`,
блок команд в `on_dictation_complete`, cmd_ptt-фрагменты
`register_global_hotkey` (только строки cmd_ptt: чтение, _skip, дефолт, binding —
соседние sl/qt/cb/pt не тронуты), 7 устаревших комментариев.

## 3. Диффы изменённых методов монолита (до/после)

| Метод | До | После |
|---|---|---|
| `SupervertalerQt.__init__` (зона менеджеров) | импорт+создание VoiceCommandManager | два оператора удалены; voice_listener остался |
| `_reinitialize_with_new_data_path` | строка пересоздания voice_command_manager | удалена |
| `create_main_layout` | 3 плейсхолдера + voice_tab_index | 2 плейсхолдера; Settings стал 6-м индексом |
| `_on_main_tab_changed` | 3 elif-ветки lazy | 2 (superlookup/clipboard) |
| `_warm_up_top_tabs` | кортеж из 3 helper'ов | из 2 |
| `_on_esc_quick_lookup_dismiss` | фокус-набор {clipboard, voice} + хвост «Голосовой режим» | {clipboard}; хвост недостижим — удалён |
| `keyPressEvent` (fallback) | quick = (superlookup, clipboard, voice) | (superlookup, clipboard) |
| `create_settings_tab` | 17 addTab | 16 |
| `on_dictation_complete` | команды → диктовка | сразу `_insert_dictated_text` |
| `_get_voice_hotkey_listener` | ветки dictate/command/pause ×2 | dictate/pause ×2 |
| `SuperlookupTab.register_global_hotkey` | 5 bindings, cmd_ptt чтение/skip/дефолт | 4 bindings, cmd_ptt-фрагменты удалены |

Контроль «не улучшать чужое»: правки комментариев ограничены удалением упоминаний
Voice/voice_tab из затронутых докстрингов; остальной текст сохранён дословно.

## 4. Статическая валидация (Этап 3)

| Защита | ДО | ПОСЛЕ | Вердикт |
|---|---|---|---|
| 1. Резолв стартовой цепочки | 768 вызовов / 0 unresolved | **763 / 0** (уменьшилось ровно на удалённые вызовы: 5 = команды UI/warm-up/страница) | OK |
| 2. Grep удалённых имён | — | `voice_tab_index`, `_voice_top_widget`, `_ensure_voice_top_tab`, `VoiceTab`, `voice_command_manager`, `VoiceCommandManager`, `VoiceCommand`, `VoiceCommandEditDialog`, `ContinuousVoiceListener`*, `_populate/_reset_voice_commands*`, `_open_voice_scripts_folder`, `_check_ahk_installed`, `_open_voice_in_workbench`, `cmd_ptt*`, `_on_pynput_command_ptt`, `_handle_command_ptt_press_hotkey`, `_on_voice_command_ptt_*`, `_do_voice_command_ptt_stop`, `_voice_command_ptt_*`, `_get/_register_*command_ptt*`, `voice_command_ptt`, `modules.voice_tab/voice_commands/voice_command_dialog/vosk_model_manager/voice_dictation.py` → **0 в коде**; остатки: 1 докстринг platform_helpers.py:2163, 1 комментарий-контекст voice_listener (:6415, interlock 8.4), миграции/дока (§1.5) | OK |
| 3. pyflakes undefined names | 149 | **149, множество идентично** (diff пуст); warnings 720→711 (−9: удалённый код) | OK |
| AST-парс монолита и shortcut_manager | OK | OK | OK |

\* ContinuousVoiceListener остался единственной строкой в комментарии при
`self.voice_listener = None` (interlock-атрибут по ТЗ остаётся до 8.4).

AST-проверки Этапа 3 п.5:
(а) bindings `register_global_hotkey` = sl/qt/cb/pt (Ctrl+Alt+L/Q/C + диктовка
Ctrl+Shift+Space) — cmd_ptt удалён, соседние не тронуты (вывод BIND-скрипта в
логе батча);
(б) числовые `setCurrentIndex(<n>)` вне комментариев: только last-resort
fallback :66543 (`3` = AI) и :66641 (`4` = SuperLookup) — оба остаются
корректными, т.к. Voice стоял после Clipboard;
(в) вызовов `save_general_settings()` без аргументов нет (regex = 0).

### Offscreen-проба ДО/ПОСЛЕ (QT_QPA_PLATFORM=offscreen, изолированный профиль, без сети)

| Метрика | ДО | ПОСЛЕ |
|---|---|---|
| main_tabs | 8 (…, Clipboard Manager, **🎤 Voice**, Settings) | **7** (…, Clipboard Manager, Settings) |
| voice_tab_index / _voice_top_widget | есть | нет |
| Страницы Settings | 17 (🎤 Voice между AI и Clipboard) | **16** (Voice нет) |
| Кнопка «🎤 Dictate (Ctrl+Shift+Space)» | есть | есть |
| Горячие клавиши при старте | l, q, c, ctrl+shift+space, **ctrl+alt+v** | l, q, c, ctrl+shift+space |
| Ошибки построения окна | нет | нет (обе пробы PROBE OK, ~8-12 с) |

### Headless-импорт всех modules/**

ДО: 128/136 OK; ПОСЛЕ: **124/131 OK**. Падения в обеих сериях идентичны и
предсуществующие (окружение без tkinter/fitz/sounddevice, `glossary_manager`
NameError): find_replace, pdf_rescue_Qt, pdf_rescue_tkinter, prompt_library,
setup_wizard, tracked_changes, glossary_manager. `voice_dictation` в ДО падал
(sounddevice) — теперь удалён. Ни один модуль не падает из-за удаления
voice-файлов (voice_dictation_lite/hotkey_listener/release_poller/vocabulary,
dictation_toast, mic_devices импортируются успешно).

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: состояние после 8.2 (код `7d9cf7dc`, Supervertaler.py
`86e88bb3…`, 67641 строк). Файлы заменяются/удаляются в
`<корень сборки>\SupervertalerPortable\`.

| № | Путь | Действие | SHA256 | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | ЗАМЕНИТЬ | `74b05eaf3fc619af18c93720e9970ff4e68f8aa5ff70effb618f435afd3a5c3f` | 67157 строк |
| 2 | `modules\shortcut_manager.py` | ЗАМЕНИТЬ | `c4f96d0a825ae76b8c7948499322e487dd7c1aa7450936fd1621067d916c2793` | без voice_command_ptt |
| 3 | `modules\voice_tab.py` | **УДАЛИТЬ** | — | |
| 4 | `modules\voice_commands.py` | **УДАЛИТЬ** | — | |
| 5 | `modules\voice_command_dialog.py` | **УДАЛИТЬ** | — | |
| 6 | `modules\vosk_model_manager.py` | **УДАЛИТЬ** | — | |
| 7 | `modules\voice_dictation.py` | **УДАЛИТЬ** | — | |

После замены: перезапустить `start.bat`. `__pycache__` в сборке можно не чистить —
удалённые имена больше не импортируются.

## 6. СЦЕНАРИИ ПРОВЕРКИ (на КОПИИ user_data тестовой сборки; сначала КОНТРОЛЬ на базовой сборке, затем после замены)

* **T8.3.1** Старт без исключений; панель вкладок: 7 вкладок без Voice, Settings
  последняя. Контроль на baseline: 8 вкладок с Voice.
* **T8.3.2** Все вкладки и ВСЕ страницы Settings открываются; страницы Voice нет.
* **T8.3.3** Меню Workbench-трея: пункта «Open Voice» нет, остальные пункты
  (SuperLookup/Clipboard/Settings/Close to tray/…) работают.
* **T8.3.4** Settings → Keyboard Shortcuts: строки «Voice commands push-to-talk»
  нет; Ctrl+Alt+V ничего не вызывает; «Voice dictation / push-to-talk»
  (Ctrl+Shift+Space) ещё в списке (Special).
* **T8.3.5** Диктовка (остаётся до 8.4): «🎤 Dictate» или Ctrl+Shift+Space —
  приложение не падает (ошибка «sounddevice not installed» допустима).
* **T8.3.6** Esc в редакторе и в SuperLookup — без исключений (в Clipboard —
  прежнее поведение возврата фокуса).
* **T8.3.7** Сохранённая вкладка: выйти из приложения с активной вкладкой
  Settings, запустить снова — окно открывается без ошибки (рекон: приложение не
  сохраняет последнюю вкладку — сценарий подтверждает отсутствие регрессии
  индексов).
* **T8.3.8** Live-test: импорт файла 180/400 сегментов; перевод сегмента; Save;
  сохранение настройки после перезапуска; навигация по вкладкам.
* **T8.3.9** Выход: иконка трея исчезает, процесс завершается (флаки-краш
  0xC0000005 — предсуществующий, не считается).

## 7. Непокрытые проверки (честно)

1. **Живых прогонов приложения не было** (батч — статика + offscreen): поведение
   трея (пункт «Open Voice») offscreen непроверяемо — `isSystemTrayAvailable()=False`
   в обеих пробах, меню трея не строится; проверяется только вручную (T8.3.3).
2. Нажатия клавиш (T8.3.4-8.3.6: Ctrl+Alt+V, Ctrl+Shift+Space, Esc) offscreen не
   эмулировались; корректность подтверждается статически (удаление binding и
   handler'ов) и ручными сценариями.
3. `_register_voice_command_ptt_deferred` удалена как метод без вызовов (осиротела
   после 8.2); живого подтверждения, что её вызов не восстановится из стороннего
   кода, нет — греп по репо = 0.
4. Поведение диктовки после удаления command-блока в `on_dictation_complete`
   проверено только статически + construction-пробой; реальная транскрипция
   (Whisper/sounddevice) не гонялась — T8.3.5.
5. `HelpTopics.VOICE` и докстринг platform_helpers.py оставлены как дока-остатки;
   их чистка не входила в согласованный список файлов.
6. Отложено на 8.4/8.8 по ТЗ: сирота-ключ `voice_commands_enabled`,
   `voice_commands.json`, `voice_scripts/`, миграции, колонка 🎤 термбаз.

## 8. Вопросы к Дмитрию

1. Тултип колонки 🎤 термбаз всё ещё ссылается на «🎤 Voice tab → Dictation
   vocabulary» (:17883). Колонку по ТЗ не трогал — переписать тултип в 8.4 вместе
   с vocab-UI или сейчас?
2. `HelpTopics.VOICE`/`HelpTopics.SIDEKICK` (help_system.py) теперь без
   потребителей. Оставил (файл вне списка правок). Чистить в конце Batch #8?
3. Диктовка больше не распознаёт голосовые КОМАНДЫ из надиктованного текста
   («next segment» теперь вставится текстом). Подтверждаете как ожидаемое
   поведение F1 (команды ушли, диктовка осталась)?
4. Для T8.3.7: подтвердить, что отсутствие восстановления последней вкладки —
   ожидаемое поведение (сохранения нет и до батча).
