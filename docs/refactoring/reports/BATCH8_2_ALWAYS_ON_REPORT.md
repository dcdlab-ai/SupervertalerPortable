# Batch #8.2 — Удаление F1 «Always-On» и второй иконки трея — ОТЧЁТ

Исполнитель: Zcode. Дата: 2026-10-03. Кодовый коммит: `7d9cf7dc`
«Batch #8.2: remove Always-On voice + second tray icon (F1)».
Отчёт: docs-only отдельный коммит. Основание: BATCH8_STAGE1_AUDIT_REPORT.md (§1.5, §2.1, §4 строка 8.2, §4.1), BATCH8_A2_SUPERLOOKUP_TRIM_AUDIT_REPORT.md §2.5, протокол под-батча BATCH8_1_SUPERBROWSER_REPORT.md.

## 0. Baseline и git-синхронизация

| Проверка | Значение |
|---|---|
| `git fetch origin` | выполнен |
| HEAD до работ | `d3b319e5` = `origin/main` |
| `git status` до работ | чисто (untracked `.zcode/plans/…`, `.zcodeignore` — допустимы) |
| Дрейф-чек | `git merge-base --is-ancestor 20b5675b HEAD` → предок ✓ |
| SHA256 `Supervertaler.py` до | `025b192456f308f24b84f1332ff44ce40df1a7f85f9e3e11610c98e8783c778e` (68216 строк) ✓ совпал с ожиданием |
| modules/*.py | 136; py_compile **137/137, 0 ошибок** |
| EOL до | `i/lf w/lf` (Supervertaler.py, shortcut_manager.py) |

Базовые значения защит (каталог `D:\Temp\SupervertalerPortable\refactoring\b8-2\`):
- (а) резолв стартовой цепочки **ДО** (расширенная цепочка, см. §4): 369 вызовов, 0 неразрешённых (`startup_chain_before.json`);
- (б) pyflakes ДО: **149** undefined names (совпало с ожиданием задания), всего warnings 721 (`undefined_names_before.txt`);
- (в) offscreen-проба ДО: успешно (`probe_before.log`, см. §4).

## 1. Рекон (без правок)

### 1.1 Таблица имён кластера и действий

AST-инвентаризация (`recon_alwayson.py`, вывод `recon_alwayson_out.txt`); строки ДО правок.

| Имя | Файл:место | Вид | Класс self | Только Always-On? | Действие |
|---|---|---|---|---|---|
| `_toggle_alwayson_listening` | Supervertaler.py:24681–24794 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_update_alwayson_ui` | 24796–24933 | def | SupervertalerQt | да (создаёт ссылки на `alwayson_status_label`/`alwayson_toggle_btn`, которые нигде не создаются — мёртвые hasattr-ветки) | УДАЛИТЬ |
| `_draw_mic_icon` | 24936–24985 (staticmethod) | def | SupervertalerQt | да (только рисование иконок Always-On-трея, вызовы 25014/25015) | УДАЛИТЬ |
| `_ensure_alwayson_tray_icon` | 24987–25031 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_on_alwayson_tray_activated` | 25033–25037 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_update_alwayson_tray_icon` | 25039–25069 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_on_alwayson_speech` | 25071–25073 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_on_alwayson_command` | 25075–25078 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_on_alwayson_dictation` | 25080–25114 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_on_alwayson_status` | 25116–25121 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_on_alwayson_error` | 25123–25126 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_on_alwayson_vad_status` | 25128–25148 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_toggle_alwayson_from_statusbar` | 25150–25152 | def | SupervertalerQt | да | УДАЛИТЬ |
| `_toggle_alwayson_from_grid_btn` | 25154–25157 | def | SupervertalerQt | да | УДАЛИТЬ |
| вызов `self._ensure_alwayson_tray_icon()` из `__init__` | 6470–6475 (комментарий+вызов) | call | SupervertalerQt | да (безусловный старт второго трея) | УДАЛИТЬ (комментарий `# Note: … _setup_tray_icon()` 6476–6477 оставлен) |
| `alwayson_indicator_label` (создание в `_setup_progress_indicators`) | 8221–8228 | widget+connect(mousePressEvent) | SupervertalerQt | да | УДАЛИТЬ |
| хоткей `voice_alwayson_toggle` (Ctrl+Alt+O) | 7303–7306 `create_shortcut(...)` | shortcut | SupervertalerQt | да | УДАЛИТЬ |
| `ao_shortcut` + `_skip('voice_alwayson_toggle')` | 66694, 66709 | pynput-путь | SuperlookupTab | да | УДАЛИТЬ |
| fallback `ao_shortcut = 'ctrl+alt+a'` | 66722 | pynput-путь | SuperlookupTab | да | УДАЛИТЬ |
| binding `(ao_shortcut, self._on_pynput_alwayson_toggle)` | 66765 | bindings register_global_hotkey | SuperlookupTab | да (только эта строка; каркас не тронут) | УДАЛИТЬ |
| `_on_pynput_alwayson_toggle` | 67099–67109 | def | SuperlookupTab | да (A2 §2.5) | УДАЛИТЬ |
| `_handle_alwayson_toggle_hotkey` | 67128–67145 (@pyqtSlot) | def | SuperlookupTab | да | УДАЛИТЬ |
| кнопка «🎧 Always-On: OFF» грида | 27750–27772 (комментарий+23 строки, connect 27770) | widget+connect | SupervertalerQt | да | УДАЛИТЬ |
| запись `voice_alwayson_toggle` в ShortcutManager | modules/shortcut_manager.py:619–628 | DEFAULT_SHORTCUTS | — | да | УДАЛИТЬ (решение п. 1.4 ниже) |
| миграция `autofingers_alwayson_toggle → voice_alwayson_toggle` | shortcut_manager.py:726–738 | migration | — | да | УДАЛИТЬ |
| default-upgrade Ctrl+Alt+A→Ctrl+Alt+O для voice_alwayson_toggle | shortcut_manager.py:772–782 | migration | — | да | УДАЛИТЬ |
| legacy-маппинги `global_alwayson_toggle`, `autofingers_alwayson_toggle` | shortcut_manager.py:797, 879–881 | _LEGACY_IDS / _GLOBAL_TO_MERGED | — | да | УДАЛИТЬ |
| `ContinuousVoiceListener` в импорте монолита | Supervertaler.py:348 | import | — | имя используется ТОЛЬКО в удалённом кластере (24744) | УДАЛИТЬ из импорта (класс в voice_commands.py остаётся до 8.3) |
| вызов `self._toggle_alwayson_listening()` в `_on_voice_command_ptt_press` | 54054–54069 | call в try/except | SupervertalerQt | нет (PTT-командная зона 8.4), но ссылка на удаляемый метод | МИНИМАЛЬНАЯ ПРАВКА (см. 1.2) |
| вызов `self._toggle_alwayson_listening()` в `_do_voice_command_ptt_stop` | 54148–54155 | call в try/except | SupervertalerQt | нет (8.4), охранён `voice_listener is not None` | МИНИМАЛЬНАЯ ПРАВКА (см. 1.2) |

### 1.2 Потребители вне кластера и их охрана

- `modules/voice_tab.py` — **правок не требует** (исключение Этапа 1 п. 3 не сработало): все обращения охранены — `_toggle_alwayson` через `getattr(self._parent_app, '_toggle_alwayson_listening', None)` + `callable()` (voice_tab.py:1013–1016), `voice_listener` через `getattr(..., None)` (1018–1024), `set_alwayson_status` вызывается из монолита только через `hasattr` (24924–24926, удалено вместе с кластером). После 8.2 кнопка Voice-вкладки «Start Always-On Listening» становится беззвучным no-op — до 8.3.
- Interlock-зона 8.4 (53920–54955): `_pause_alwayson_external`, `_resume_alwayson_external`, `_resume_alwayson_after_dictation`, `voice_pause_alwayson`-регистрации, `alwayson_was_running` в `start_voice_dictation` — **оставлены**: ссылаются только на сохраняемые атрибуты (`voice_listener`, навсегда None после 8.2; `_alwayson_paused_by_external`; `_alwayson_was_running_before_dictation`) и все охранены getattr/None-проверками → runtime-безопасные no-op до 8.4.
- Единственные неохраняемые (текстуально) ссылки на удаляемые методы — два вызова `_toggle_alwayson_listening()` в PTT-командной паре press/stop. Закрыты минимальной правкой: try-блоки удалены и заменены комментариями Batch #8.2 (метод `__init__`-логику PTT-команд это не меняет: аккорд Ctrl+Alt+V регистрируется, press/release становятся no-op с сохранённой логикой deferral). Дополнительно восстановлен сброс флага `_voice_command_ptt_owned = False` в `_do_voice_command_ptt_stop` (раньше его сбрасывал удалённый `_update_alwayson_ui("stopped")` через listening_stopped).
- Докстринги/комментарии interlock-зоны, упоминавшие удалённые имена (`_toggle_alwayson_listening`, `_update_alwayson_ui`, `_on_alwayson_dictation`, `_on_alwayson_vad_status`), переформулированы (7 мест, только текст).

### 1.3 Трей и меню

- Вторая (Always-On) иконка: `_ensure_alwayson_tray_icon` + `_draw_mic_icon` + меню Start/Stop/Open Voice — удалена целиком с кластером; безусловный вызов из `__init__` (6475) удалён.
- Workbench-трей (`_setup_tray_icon`, вызов из main() 68195): **не тронут**. Пункт ≈29529 из постановки проверен: это jumper **«Open Voice»** (Voice-вкладка, через `voice_tab_index`) → уходит в 8.3, в 8.2 не трогался. Отдельного пункта «Always-On» в меню Workbench-трея нет (он был в меню второй иконки).
- Esc-ветка Voice (`_on_esc_quick_lookup_dismiss`): работает с `voice_tab_index`, ссылок на кластер не имеет → 8.3, не тронута. (§4 аудита упоминал её в строке 8.2, но она не Always-On.)
- closeEvent (29803): ссылок на Always-On/`voice_listener` не содержит — проверено grep; правка не нужна. Явной остановки Always-On в closeEvent и не было (остановка — только через toggle).

### 1.4 Решение по ShortcutManager (Этап 1, п. 5)

Толерантность к отсутствующему ID доказана чтением кода:
- `get_shortcut(unknown)` → `''` (нет KeyError), `is_enabled(unknown)` → True, `is_global(unknown)` → False (shortcut_manager.py:858–905);
- Settings → Keyboard Shortcuts строится из `DEFAULT_SHORTCUTS` (`get_all_shortcuts` → `get_shortcuts_by_category`, keyboard_shortcuts_widget.py:552) — после удаления записи строка просто исчезает; в keyboard_shortcuts_widget.py упоминания alwayson — только комментарии (408–409, 659), правки не требуются.

**Решение:** запись `voice_alwayson_toggle` удалена из `DEFAULT_SHORTCUTS` вместе с миграциями и legacy-маппингами (все упоминания alwayson в shortcut_manager.py — 0). Сохранённое пользовательское значение `custom_shortcuts['voice_alwayson_toggle']` остаётся орфанным ключом в settings.json (решение 6 — допустимо).

### 1.5 Финальный контрольный список имён (Этап 1, п. 7)

Удалены (ZОЛНО): `_toggle_alwayson_listening`, `_update_alwayson_ui`, `_draw_mic_icon`, `_ensure_alwayson_tray_icon`, `_on_alwayson_{tray_activated,tray_icon→,speech,command,dictation,status,error,vad_status}`, `_update_alwayson_tray_icon`, `_toggle_alwayson_from_{statusbar,grid_btn}`, `alwayson_indicator_label`, `grid_alwayson_btn`, `_alwayson_tray_*`, `_alwayson_tray_active`, `ao_shortcut`, `_on_pynput_alwayson_toggle`, `_handle_alwayson_toggle_hotkey`, хоткей `voice_alwayson_toggle` (привязка + bindings-строка + запись в ShortcutManager).

Допустимые остатки (проверены grep, §4 Защита 2): `voice_listener = None` (init 6420, нужно 8.4), `_alwayson_paused_by_external`, `_alwayson_was_running_before_dictation`, `voice_pause_alwayson` (interlock 8.4), ключи настроек `alwayson_sensitivity`/`alwayson_commands_only`, класс `ContinuousVoiceListener` в modules/voice_commands.py, modules/voice_tab.py (охранённые ссылки), комментарии (voice_dictate в shortcut_manager.py:200 и монолит 6420), docs/.

## 2. Что сделано

| Файл | Действие |
|---|---|
| Supervertaler.py | Удалён кластер Always-On 24681–25158 (14 методов + `_draw_mic_icon`); удалён вызов/комментарий трея в `__init__` (6470–6475); удалён `create_shortcut("voice_alwayson_toggle", …)` (7303–7306); удалён `alwayson_indicator_label` из `_setup_progress_indicators` (8221–8229); удалена кнопка «🎧 Always-On: OFF» из тулбара грида (27750–27773); удалены `ao_shortcut`/`_skip`/fallback/binding и оба pynput-метода из `SuperlookupTab` (66694, 66709, 66722, 66765, 67099–67109, 67128–67145); из импорта 348 убран `ContinuousVoiceListener`; interlock press/stop: удалены try-блоки с вызовом `_toggle_alwayson_listening`, добавлен сброс `_voice_command_ptt_owned`, переформулированы 7 докстрингов/комментариев |
| modules/shortcut_manager.py | Удалены: запись `voice_alwayson_toggle` из DEFAULT_SHORTCUTS, миграция autofingers→voice, default-upgrade Ctrl+Alt+A→O, legacy-маппинги `global_alwayson_toggle`/`autofingers_alwayson_toggle` (в `_GLOBAL_TO_MERGED` и `_LEGACY_IDS`) |
| modules/voice_tab.py | НЕ менялся (обращения охранены) |
| modules/keyboard_shortcuts_widget.py | НЕ менялся (только комментарии) |

Итог: `git diff HEAD~1 HEAD --stat`: Supervertaler.py −615 net, shortcut_manager.py −40 net; всего `27 insertions(+), 642 deletions(-)`; монолит 68216 → **67641** строк. SHA256 после: Supervertaler.py `86e88bb3e0d372b4eac7a86434d5429815eb4a97e872ddd47df515518174536f`, shortcut_manager.py `daf32ce573673633b49fcf795140650ce7abf3728cfd8038ce441582b72029cb`. EOL после: `i/lf w/lf` (не изменился).

## 3. Диффы изменённых методов монолита (суть)

- `SupervertalerQt.__init__`: убраны комментарий+вызов `self._ensure_alwayson_tray_icon()`; `self.voice_listener = None` (6420) оставлен.
- `setup_global_shortcuts`: убран `create_shortcut("voice_alwayson_toggle", "Ctrl+Alt+O", …)`; соседние (Ctrl+Alt+L, Alt+K, Ctrl+M, Ctrl+Q, Ctrl+Shift+C, Ctrl+Shift+Q) не тронуты — видно по diff-хунку @@ -7300,10 +7294,6.
- `_setup_progress_indicators`: убран блок `alwayson_indicator_label` (7 строк+комментарий); остальные индикаторы (Words/Confirmed/Remaining/Files) на месте.
- `create_grid_view_widget_for_home`: убрана кнопка alwayson_btn; цепочка layout теперь `…dictate_btn → "|" → Log → stretch → Confirm&Next` — без дыр и двойных разделителей (проверено по тексту и offscreen-пробе).
- `SuperlookupTab.register_global_hotkey`: из `_bindings` удалена ровно одна строка `(ao_shortcut, self._on_pynput_alwayson_toggle),`; sl/qt/cb/pt/cmd_ptt на месте; удалены присваивания `ao_shortcut` (3 места).
- `_on_voice_command_ptt_press` / `_do_voice_command_ptt_stop`: удалены try-блоки с вызовом `_toggle_alwayson_listening`; в stop добавлен сброс `_voice_command_ptt_owned`; остальная логика (deferral enable/drain, pending-stop QTimer, идемпотентный guard) сохранена.
- `Supervertaler.py:348`: `from modules.voice_commands import VoiceCommandManager, VoiceCommand` (без ContinuousVoiceListener).

## 4. Статическая валидация (§4.1)

| Проверка | ДО | ПОСЛЕ | Вывод |
|---|---|---|---|
| py_compile (Supervertaler.py + modules) | 137/137 | **137/137, 0 ошибок** | ✓ |
| Защита 1: резолв стартовой цепочки (AST, расширенная цепочка: main, `__init__`, init_ui, create_menus, create_main_layout, setup_global_shortcuts, _setup_progress_indicators, _warm_up_top_tabs + `create_grid_view_widget_for_home` + `create_assistance_panel`) | 369 вызовов, 0 unresolved | **364 вызова, 0 unresolved**; из diff до/после исчезли ровно 2 записи (`_toggle_alwayson_from_grid_btn`, `_toggle_alwayson_from_statusbar` — удалённые), новых unresolved нет | ✓ |
| Защита 2: grep удалённых имён (24 шаблона, включая строки) | — | 0 живых упоминаний вне допустимых остатков (voice_tab — охранённые; interlock-атрибуты 8.4; ключи настроек; ContinuousVoiceListener в voice_commands; комментарии) | ✓ |
| Защита 3: pyflakes undefined names | 149 | **149** (дифф распределения имён пуст; полный дифф warnings — только сдвиги номеров строк и исчезновение 1 redefinition из удалённого кластера; новых warnings нет) | ✓ |
| AST (а): layout грида/редактора без лишних stretch/separator | — | грид: dictate → «\|» → Log (по одному разделителю); редактор: без Always-On (рекон: в tab-редакторе её и не было — указание «≈29017–29021» из постановки устарело, там только «🎤 Dictate») | ✓ |
| AST (б): bindings register_global_hotkey | 6 строк | 5 строк (удалена только Always-On); Ctrl+Alt+L, Ctrl+Alt+Q, Ctrl+Alt+C, Ctrl+Shift+Space, Ctrl+Alt+V на месте; `ctrl+alt+o` нигде не регистрируется (лог пробы: `Registering: ctrl+alt+l, ctrl+alt+q, ctrl+alt+c, ctrl+shift+space, ctrl+alt+v`) | ✓ |
| AST (в): нет вызовов `save_general_settings()` без аргументов | — | grep: 0 | ✓ |
| EOL | i/lf w/lf | i/lf w/lf | ✓ |
| `git diff --stat` | — | только Supervertaler.py + modules/shortcut_manager.py | ✓ |

Offscreen-проба (изолированная: `QT_QPA_PLATFORM=offscreen`, USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP → `D:\Temp\SupervertalerPortable\refactoring\b8-2\iso\{before,after}`, модалки нейтрализованы, opt-in statistics отключён, faulthandler-таймаут):

| Факт | ДО (HEAD d3b319e5) | ПОСЛЕ (7d9cf7dc) |
|---|---|---|
| Конструирование SupervertalerQt | без исключений, 7.7 c | без исключений, 7.7 c |
| `QSystemTrayIcon.isSystemTrayAvailable()` | False (offscreen) | False (offscreen) |
| Число QSystemTrayIcon (allWidgets / window-owned) | 0 / 0 | 0 / 0 (offscreen трей не создаётся: `_setup_tray_icon` и Always-On-трей оба гейтятся isSystemTrayAvailable; факт реального числа иконок на Windows — T8.2.1 на тестовой сборке) |
| `alwayson_indicator_label` | присутствует (hidden) | **отсутствует** |
| Кнопки Always-On | `['🎧 Always-On: OFF']` | **`[]`** |
| Кнопка Dictate | `['🎤 Dictate (Ctrl+Shift+Space)']` | `['🎤 Dictate (Ctrl+Shift+Space)']` ✓ |
| Вкладки main_tabs | 8: Editor, TMs, Termbases, AI, SuperLookup, Clipboard Manager, Voice, Settings | те же 8 (паритет) ✓ |

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

База сборки: состояние после 8.1 (кодовый коммит 8.1 = `20b5675b`); файлы заменяются в `<корень сборки>\SupervertalerPortable\`.

| № | Путь | Действие | SHA256 (после 8.2) | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler.py` | заменить | `86e88bb3e0d372b4eac7a86434d5429815eb4a97e872ddd47df515518174536f` | 67641 строк; портативность через `._pth` — локальных патчей нет |
| 2 | `modules\shortcut_manager.py` | заменить | `daf32ce573673633b49fcf795140650ce7abf3728cfd8038ce441582b72029cb` | удалена запись Ctrl+Alt+O из реестра хоткеев |

После замены: py_compile двух файлов не обязателен (проверено в репо), но допустим.

## 6. СЦЕНАРИИ ПРОВЕРКИ (тестовая сборка; всё на КОПИИ user_data; сначала КОНТРОЛЬ на базовой сборке, затем после замены)

Все сценарии T8.2.1–T8.2.8 **ПОДТВЕРЖДЕНЫ Дмитрием** на тестовой сборке (2026-10-04):

- **T8.2.1** — ПОДТВЕРЖДЕНО (старт без исключений; ровно ОДНА иконка в области уведомлений).
- **T8.2.2** — ПОДТВЕРЖДЕНО (статус-бар без индикатора Always-On).
- **T8.2.3** — ПОДТВЕРЖДЕНО (кнопки Always-On нет, Dictate на месте, раскладка не поехала).
- **T8.2.4** — ПОДТВЕРЖДЕНО (Voice-вкладка и Settings → Voice открываются; кнопка Always-On — беззвучный no-op).
- **T8.2.5** — ПОДТВЕРЖДЕНО (Ctrl+Alt+O ничего не вызывает; Ctrl+Shift+Space присутствует в Settings → Keyboard Shortcuts).
- **T8.2.6** — ПОДТВЕРЖДЕНО (меню Workbench-трея работает; пункта Always-On нет).
- **T8.2.7** — ПОДТВЕРЖДЕНО (live-test: импорт 180/400, перевод, Save, сохранение настройки, навигация по вкладкам и Settings; строка Voice Always-On исчезла из Keyboard Shortcuts).
- **T8.2.8** — ПОДТВЕРЖДЕНО с оговоркой на portable-версию: после выхода остаётся окно cmd.exe от запускающего bat-файла (поведение `start.bat`, предсуществующее и к 8.2 не относящееся; иконка из трея исчезает, процесс завершается).

Примечание Дмитрия: функционал Voice требует дополнительных пакетов (`Error: no module named 'sounddevice'` в портативной сборке); поскольку он подлежит удалению (8.3/8.4), установка не производилась и voice-функционал далее не тестировался.

## 7. Непокрытые проверки — ЗАКРЫТЫ по решению Дмитрия (2026-10-04)

Исходный список закрывается следующим образом: пункты 1, 2, 5 покрыты ручным тестом (T8.2.1 — число иконок; T8.2.5 — живой Ctrl+Alt+O в окне и из другой программы; T8.2.4 — живой клик по кнопке Voice-вкладки без падения); пункты 3, 4, 6 относятся к функционалу, запланированному к удалению в 8.3/8.4, который в портативной сборке к тому же невоспроизводим без установки `sounddevice`/`faster_whisper` (установка по решению Дмитрия не производится). Возражений со стороны исполнителя нет.

1. ~~Фактическое число иконок в системном трее Windows~~ — покрыто T8.2.1 (ПОДТВЕРЖДЕНО: одна иконка).
2. ~~Живое поведение Ctrl+Alt+O из другой программы~~ — покрыто T8.2.5 (ПОДТВЕРЖДЕНО).
3. ~~Реальная диктовка/PTT~~ — закрывается как удаляемый функционал (8.4); в портативной сборке отсутствует `sounddevice`, установка не производится (решение Дмитрия).
4. ~~Поведение Settings → Keyboard Shortcuts с орфанным ключом~~ — покрыто T8.2.7 (строка исчезла из списка; орфанный ключ «есть и не просит»).
5. ~~Клик по Always-On-кнопке Voice-вкладки~~ — покрыт T8.2.4 (ПОДТВЕРЖДЕНО, no-op без падения).
6. ~~Клавиша паузы `voice_pause_hotkey`~~ — закрывается как удаляемый функционал (8.4); machinery в 8.2 стала фактическим no-op (voice_listener всегда None), риска регрессии нет.

## 8. Решения Дмитрия (2026-10-04, ответы на вопросы отчёта)

1. **Кнопка Voice-вкладки «Start/Stop Always-On Listening»**: оставить как есть (no-op до 8.3), микро-правку voice_tab.py в 8.2 не делать — по плану.
2. **Пункт трея «Open Voice»** (jumper, ≈29529): подтверждено — остаётся до 8.3.
3. **Расхождение по «кнопке Always-On в tab-редакторе (≈29017–29021)»**: закрыто — в UI действительно была только одна кнопка Always-On в тулбаре грида; recon верен.
4. **Орфанный ключ** `custom_shortcuts['voice_alwayson_toggle']` в settings.json: ок («есть и не просит»).
