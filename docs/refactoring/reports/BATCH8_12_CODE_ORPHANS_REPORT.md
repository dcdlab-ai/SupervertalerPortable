# ОТЧЁТ Batch #8.12 — Удаление модулей-сирот и мёртвых определений (Этап 2)

Исполнитель: Zcode. Репозиторий: dcdlab-ai/SupervertalerPortable.
Основание: `BATCH8_12_ORPHAN_INVENTORY_REPORT.md` (разделы A, C, F, I-09/I-10, E-05,
§4 строка 8.12, §5 U-1…U-3), ответы Дмитрия §7–§8 (коммит 17846698), решение E-03
(коммит 5f3d6b64).
Кодовый коммит: **f804d447** «Batch #8.12: remove orphan modules and dead definitions».
База кода: **d308a93f** (HEAD на старте = 768fe720 = origin/main; после d308a93f —
только docs-коммиты, проверено `git diff --name-only d308a93f..HEAD`).
Все артефакты: `D:\Temp\SupervertalerPortable\refactoring\b8-12\`.

---

## 0. Baseline и git-синхронизация

| Проверка | Команда | Результат |
|---|---|---|
| HEAD = origin/main | `git rev-parse HEAD origin/main` | оба `768fe720` |
| Рабочее дерево | `git status --short` | чисто; untracked только `.zcode/plans/plan-sess_49142aaa….md`, `.zcodeignore` (допустимо) |
| Дрейф-чек | `git merge-base --is-ancestor d308a93f HEAD` | ANCESTOR OK; `git diff --name-only d308a93f..HEAD` — 21 файл, все docs/audits/prompts/reports |
| SHA Supervertaler.py | `sha256sum Supervertaler.py` | `aab1f180e5789878c014d6042a0ee1a29c9e7bdf1d85dbb02e0722f3604f7644` (совпал с постановкой), `wc -l` = 57010 |

### Baseline-метрики (до правок)

| Метрика | Команда | Результат |
|---|---|---|
| py_compile всего репо | `pycompile_all.py` (git ls-files *.py) | **132 ok / 0 fail / 132** |
| Число modules/**/*.py | `find modules -name "*.py" -not -path "*__pycache__*" \| wc -l` | **110** |
| Headless-импорт модулей | `headless_imports.py` | **104 ok / 6 fail / 110** (tkinter: find_replace, pdf_rescue_tkinter, prompt_library, tracked_changes; NameError GlossaryInfo: glossary_manager; fitz: pdf_rescue_Qt). С `setup.py` (setuptools) — 104/7/111, как в baseline инвентаря `batch8-12_headless_before.txt` |
| pyflakes | `run_pyflakes.py before` | **640 warnings; 149 undefined-строк; 12 уникальных имён** (tk 100, messagebox 19, dialog 8, ttk 5, GlossaryInfo 4, tabs 3, layout 2, import_tab 2, filedialog 2, TermEntry 2, e 1, LLMClient 1) |
| AST-резолв стартовой цепочки монолита | `startup_chain_resolve.py … before` | **926 вызовов, 0 неразрешённых** |
| Offscreen S-clean | `probe_window_812.py iso-clean before clean` | окно построено (9.3 с), main_tabs 6, Settings 14 страниц, **DATA-TREE 28 записей**, PROBE OK |
| Offscreen S-upgrade | `probe_window_812.py iso-upgrade before upgrade` | PROBE OK (7.4 с), **HASH-DIFF пуст** (added/removed/changed/transient = []) |
| Регрессия общих путей | `regress_common.py <repo> … before` | import txt=5, md=5, docx=4 сегмента; sha256: simple.txt `5a12501f934a589c`, translated.docx `44828d90090f046d`, grid.tmx `c413d56372e69dd9` |
| Tools-smoke (baseline) | `tools_smoke.py <repo> … before` | 44 пункта меню (Project 24 + Tools 10 + Help 10), все обработчики отработали; 2 ожидаемых исключения (см. §4.8) |

Профили проб: `probes/iso-clean` (пустой user_data), `probes/iso-upgrade` (преднаполненный
prompt_library + resources/supervertaler.db + workbench). Все пробы — offscreen, изолированный
профиль (USERPROFILE/APPDATA/LOCALAPPDATA/HOME/TEMP → `b8-12\probes\…`), модалки
нейтрализованы (`QDialog.exec` → Rejected c логом, `QMessageBox.*` → Ok/No,
`QFileDialog.*` → пусто, `webbrowser.open`/`QDesktopServices.openUrl` → лог),
opt-in статистика отключена (`usage_statistics.show_opt_in_dialog → False`).
На боевых данных ничего не запускалось.

---

## 1. Рекон (без правок)

### 1.1 «0 импортёров» для 17 модулей на текущем HEAD

Скан `importer_scan.py` (тот же, что в инвентаре: AST Import/ImportFrom с резолвом
relative, `importlib.import_module`/`__import__`/`getattr`/`hasattr`/`setattr` с
литералами, строковые константы с dotted/path/base-формой имени, non-py grep по
.bat/.spec/.toml/.cfg/.json/.md/.txt/.iss/.ini; обход всего top-level, включая
tools/** и tests/** как потребителей). Вывод: `recon_importers.json` + таблица.

| Модуль | py-hits | nonpy-hits | importers(files) |
|---|---|---|---|
| modules.extract_tm | 0 | 102 | — |
| modules.feature_manager | 0 | 135 | — |
| modules.find_replace | 0 | 224 | — |
| modules.glossary_manager | 0 | 93 | — |
| modules.identifier_conventions | 0 | 82 | — |
| modules.pdf_rescue_tkinter | 0 | 93 | — |
| modules.project_home_panel | 0 | 83 | — |
| modules.project_tm | 0 | 77 | — |
| modules.prompt_assistant | 0 | 71 | — |
| modules.prompt_library | 0 | 234 | — |
| modules.quick_access_sidebar | 0 | 90 | — |
| modules.ribbon_widget | 0 | 87 | — |
| modules.style_guide_manager | 0 | 65 | — |
| modules.superdocs | 1 | 160 | — |
| modules.superdocs_viewer_qt | 0 | 117 | — |
| modules.tracked_changes | 0 | 70 | — |
| modules.translation_services | 0 | 83 | — |

Единственный py-hit (`modules.superdocs`) — строка в docstring самого
`modules/superdocs_viewer_qt.py` («The 'modules.superdocs_viewer_qt' module has been
removed…»), т.е. сирота ссылается на сироту; оба удаляются. Цепочек
«единственный импортёр — сирота» вне пары сирот нет. nonpy-hits — ссылки в
docs/audits/отчётах (не код).

### 1.2 Публичные имена 17 модулей в остальном коде

`recon_public_names.py`: AST top-level class/function каждого сироты + grep
`\bимя\b` по Supervertaler.py, modules/**, tools/**, tests/** (без самих сирот).
49 имён, **43 с нулём упоминаний**. 6 с хитами — все допустимые остатки:

| Имя | Хиты | Характер |
|---|---|---|
| RibbonButton/Group/Tab/Widget | 1–2 | закомментированный блок монолита 9012–9024 (`# from modules.ribbon_widget import …`) |
| TermbaseManager | 11 | одноимённый класс ЖИВОГО `modules/termbase_manager.py` (импорт 6292/15893/17119, docstring-ссылки) |
| get_user_data_path | 12 | одноимённая функция монолита (241) и метод `config_manager.ConfigManager` |

### 1.3 E-05: tmx_editor без tkinter (живая функция Tools → TMX Editor)

- В `modules/tmx_editor.py` **нет** `import tkinter` (grep `import tkinter|import tk|as tk` = 0).
  tkinter-код класса `TmxEditorUI` (321+) обращается к `tk.*` без импорта — это источник
  100 undefined-имён `tk` в pyflakes; он не достижим из Qt-пути.
- Headless-импорт `modules.tmx_editor` — **OK** (в baseline FAIL-списке его нет).
- `modules/tmx_editor_qt.py:37` берёт из него: `TmxFile, TmxParser, TmxTranslationUnit,
  TmxSegment, TmxHeader` (framework-agnostic core, строки 36–126).
- tkinter-часть под охраной: `main()` (1460) и `TmxEditorUI` вызываются только из
  `if __name__ == '__main__'`; Qt-путь их не трогает.
- **СТОП-флага нет.**

### 1.4 statuses.py

- `match_memoq_status` / `compose_memoq_status`: потребители — только определения в
  `modules/statuses.py` (grep по всем .py: 0 обращений извне).
- `StatusDefinition`: в монолите — только строка импорта 323 (0 использований);
  в statuses.py — живой класс (используется в `STATUSES: Dict[str, StatusDefinition]`
  и `get_status`), остаётся.
- Поля словаря STATUSES, читаемые живым кодом: `label`, `icon`, `color`,
  `match_symbol`, `short_label`, `badge_text`, `badge_bg`, `badge_fg`, `icon_color`
  (монолит читает их через `get_status(...)`). `memoq_label` читается только
  `compose_memoq_status` (удаляемой), `memoQ_equivalents` — только
  `match_memoq_status` (удаляемой); по решению Дмитрия поля в STATUSES остаются.
- Побочный вывод: после вырезки функций `import re` и `Optional` в statuses.py
  становятся мёртвыми импортами (использовались только в удаляемых функциях) —
  удалены как прямое следствие (иначе новая pyflakes-тревога).

### 1.5 help_system.py: 4 константы HelpTopics

`HelpTopics` в монолите = алиас класса `Topics` (`from modules.help_system import
Topics as HelpTopics`, строка 337). Обращения `HelpTopics.SIDEKICK/VOICE/CLIPBOARD/
TRADOS_AWARE_CHAT` и `Topics.<…>` по всем формам (включая строковые и getattr):
**0**. Остатки слова в комментариях (`TOOL_VOICE removed…`) — не обращения.

### 1.6 termbase_manager.py: voice-bias

Состав по рекону (блок 461–552): комментарий 461–466, `get_termbase_voice_enabled`
468–486, `set_termbase_voice_enabled` 488–502, `get_voice_enabled_termbase_ids`
531–552. Между ними — `set_termbase_superlookup_enabled` (488→504, живой, не трогать).
Потребители по всем формам (прямые вызовы, getattr/hasattr, строки, duck-typed
parent_app, non-py grep): **0 вне модуля**. Колонку БД `voice_dictation_enabled`
остальный код не читает и не пишет (единственные SQL-обращения — в удаляемых
методах; `database_manager.py:577` — ALTER TABLE миграция, остаётся).
Комментарии про Voice tab в модуле: 464, 472, 539 (внутри удаляемого блока).

### 1.7 styled_widgets.py: места комментариев про Voice

- 116–124: docstring `PurpleCheckmarkCheckBox` — «Used by the voice-dictation-bias UI:
  Termbase Manager → 🎤 Voice column / Voice tab → "Also bias…"».
- 169–171: docstring `TealCheckmarkCheckBox` — «…distinct from Read (green), Write (blue),
  Bridge/AI (orange), Project (pink) and Voice (purple)».
Колонка «🎤 Voice» в таблице Termbases отсутствует (header 15975–15977: Type, Name,
Languages, Terms, Read, Write, Project, AI, 🔍 SuperLookup) — удалена в Batch #8.4;
`PurpleCheckmarkCheckBox` сейчас не используется нигде (grep 0 потребителей), класс остаётся.

### 1.8 Контрольный список имён для защиты 2

73 идентификатора: 17 имён модулей + 49 публичных имён + `match_memoq_status`,
`compose_memoq_status`, `StatusDefinition`, `SIDEKICK`, `TRADOS_AWARE_CHAT`,
`CLIPBOARD`, 3 voice-метода. Допустимые остатки (см. §4.2): закомментированный
Ribbon-блок монолита, одноимённые символы живого кода, комментарии, ключи словарей.

---

## 2. Что сделано (коммит f804d447)

SHA-guard перед стартом: SHA Supervertaler.py = `aab1f180…` (совпал с постановкой);
SHA statuses/help_system/termbase_manager/styled_widgets зафиксированы
(`58c538ef…`, `753d55f8…`, `4e45b302…`, `0b317da1…`).

1. **`git rm` 17 модулей-сирот** (см. §1.1).
2. **modules/statuses.py**: удалены `match_memoq_status` (185–226),
   `compose_memoq_status` (229–244) и ставшие мёртвыми `import re` (5) и
   `Optional` из `from typing import Dict, Optional` (4). Поля `memoq_label` /
   `memoQ_equivalents` в STATUSES, `STATUSES`, `get_status`, `_STATUS_ALIASES`,
   `DEFAULT_STATUS` — не тронуты. 244 → 183 строк.
3. **Supervertaler.py**: удалена единственная строка 323 `    StatusDefinition,`
   из блока `from modules.statuses import (…)`. Единственная правка монолита.
   57010 → 57009.
4. **modules/help_system.py**: удалены 4 константы `SIDEKICK`, `TRADOS_AWARE_CHAT`,
   `VOICE`, `CLIPBOARD` (164–167) и связанный комментарий-блок Companion Tabs
   (160–163). 263 → 255.
5. **modules/termbase_manager.py**: удалены voice-bias методы
   `get_termbase_voice_enabled`, `set_termbase_voice_enabled` (с комментарием-заголовком
   блока 461–466) и `get_voice_enabled_termbase_ids`. Колонка БД
   `voice_dictation_enabled` и схема не тронуты. 1497 → 1431.
6. **modules/styled_widgets.py**: правка только текстов комментариев (docstring
   PurpleCheckmarkCheckBox — указано, что voice-bias UI удалён в Batch #8.4, класс
   сохранён; docstring TealCheckmarkCheckBox — убрано упоминание Voice (purple) из
   перечня цветов). Поведение не менялось. 498 → 494.

Итог мелких правок: −140 строк (6 insertions, 146 deletions по git). Ориентир
постановки −150…−250; расхождение объясняется тем, что styled_widgets — правка
текста без сокращения объёма (9 строк → 5), а voice-блок termbase_manager содержит
и живой метод superlookup между voice-методами.

Снапшоты вырезаемых блоков (9 шт.) сняты до правок в `b8-12\snapshots\` с sha256
(`snapshot_blocks.py`); после правок `verify_snapshots.py`: **9/9 OK byte-wise**
против `git show HEAD:<file>` (с восстановлением завершающего newline git-blob) и
все удалённые идентификаторы отсутствуют в новых файлах (FAILS=0).

`git diff --stat HEAD` (коммит): 22 файла, +6/−6881. Файлы вне списка — отсутствуют.
17 удалений: 6735 строк по git = 6734 по `wc -l` (расхождение 1: у
`translation_services.py` нет завершающего newline — git считает последнюю строку
как удаление, маркер `\ No newline at end of file` в диффе).

EOL (`git ls-files --eol` до/после идентично): Supervertaler.py `i/lf w/crlf`,
модули `i/lf w/lf`. `\r\r\n` в Supervertaler.py после правки: **0**.

---

## 3. Диффы правок

Полный дифф 5 файлов: `b8-12\edits_diff.txt` (225 строк). Ключевые фрагменты:

```diff
--- a/Supervertaler.py
+++ b/Supervertaler.py
@@ -320,7 +320,6 @@ from modules.statuses import (
     STATUSES,
     DEFAULT_STATUS,
-    StatusDefinition,
     get_status,
 )
```

```diff
--- a/modules/statuses.py
+++ b/modules/statuses.py
@@ -1,8 +1,7 @@
 """Centralized status vocabulary for Supervertaler segments."""
 
 from dataclasses import dataclass
-from typing import Dict, Optional
-import re
+from typing import Dict
@@ -182,63 +181,3 @@ def get_status(key: str) -> StatusDefinition:
     resolved = _STATUS_ALIASES.get(key, key)
     return STATUSES.get(resolved, DEFAULT_STATUS)
-
-
-def match_memoq_status(status_text: str) -> tuple[StatusDefinition, Optional[int]]:
-    … (61 строк: match_memoq_status + compose_memoq_status)
```

```diff
--- a/modules/help_system.py
+++ b/modules/help_system.py
@@ -158,14 +158,6 @@ class Topics:
     QA_NT               = "workbench/qa/non-translatables/"
 
-    # Voice, Clipboard Manager, and Chat — the old "Companion Tabs"
-    # grouping was dropped (2026-05-21). Voice and Clipboard Manager are
-    # now their own top-level sections; Chat moved under AI Translation.
-    # The old /workbench/sidekick/* URLs 301-redirect to these.
-    SIDEKICK            = "workbench/voice/overview/"   # legacy alias → Voice
-    TRADOS_AWARE_CHAT   = "workbench/ai-translation/chat/"
-    VOICE               = "workbench/voice/overview/"
-    CLIPBOARD           = "workbench/clipboard/overview/"
     # QuickTrans. Moved to its own top-level section at
```

```diff
--- a/modules/termbase_manager.py
+++ b/modules/termbase_manager.py
@@ -461,46 +461,6 @@ class TermbaseManager:
-    # ---------- Voice-dictation biasing (v1.10.28) ----------------
-    # Per-termbase opt-in flag …
-    def get_termbase_voice_enabled(self, termbase_id: int) -> bool: …
-    def set_termbase_voice_enabled(self, termbase_id: int, enabled: bool) -> bool: …
     def set_termbase_superlookup_enabled(self, termbase_id: int, enabled: bool) -> bool:
@@ -530,25 +490,6 @@ class TermbaseManager:
-    def get_voice_enabled_termbase_ids(self) -> list: …
     def get_ai_inject_termbases(self, project_id: Optional[int] = None) -> List[Dict]:
```

```diff
--- a/modules/styled_widgets.py
+++ b/modules/styled_widgets.py
@@ -113,15 +113,13 @@ class PurpleCheckmarkCheckBox(CheckmarkCheckBox):
     fill (Material 500 / hover 700) instead of the green default.
-    Used by the voice-dictation-bias UI:
-
-      - Termbase Manager → 🎤 Voice column (one per termbase)
-      - Voice tab → "Also bias from your termbases" toggle
-
-    Both UI surfaces drive the same feature (per-termbase voice-
-    dictation vocabulary biasing); using the same colour keeps the
-    visual identity consistent so users can connect them at a glance.
+    The voice-dictation-bias UI surfaces (Termbase Manager 🎤 Voice
+    column, Voice tab "Also bias from your termbases" toggle) were
+    removed in Batch #8.4; the class is kept for the purple colour
+    identity referenced by the sibling checkmark variants.
 
     The CheckmarkCheckBox parent class handles the paintEvent that
@@ -167,7 +165,7 @@ class TealCheckmarkCheckBox(CheckmarkCheckBox):
     Read flag, so the colour is deliberately distinct from Read (green),
-    Write (blue), Bridge/AI (orange), Project (pink) and Voice (purple) –
+    Write (blue), Bridge/AI (orange) and Project (pink) –
     one glance tells you which switch you're looking at.
```

---

## 4. Валидация (§4.1)

### 4.1 py_compile всего репо
`pycompile_all.py`: **115 ok / 0 fail / 115** (132 − 17 удалённых).

### 4.2 Защита 1: AST-резолв стартовой цепочки монолита
`startup_chain_resolve.py … after`: **926 вызовов, 0 неразрешённых** — идентично
before (`chain_before.json` / `chain_after.json`).

### 4.3 Защита 2: grep по удалённым идентификаторам
`protection2_grep.py` (Supervertaler.py + modules/** + tools/** + tests/**,
`\bимя\b` по всем формам, включая строки/getattr/connect/ключи). 73 идентификатора:
**62 с нулём хитов**, 81 хит — все допустимые остатки:

| Идентификатор | Хиты | Обоснование остатка |
|---|---|---|
| StatusDefinition | 16 | живой класс в `modules/statuses.py` (сам модуль, остаётся) |
| prompt_library | 41 | имя каталога user_data (`user_data_path / "prompt_library" / …`) и атрибут живого PromptManager (`prompt_manager_qt.prompt_library`), параметр `ai_actions.py` — не модуль `modules/prompt_library.py` |
| TermbaseManager | 11 | живой класс `modules/termbase_manager.py` |
| RibbonButton/Group/Tab/Widget | 7 | закомментированный блок монолита 9012–9024 |
| ribbon_widget | 1 | та же закомментированная строка 9012 |
| project_tm | 3 | ключ словаря в `modules/translation_memory.py:770/783/784` (`data['project_tm']`) — не модуль |
| identifier_conventions | 1 | комментарий `modules/termbase_manager.py:1035` («…modules/identifier_conventions.py.») |
| CLIPBOARD | 1 | комментарий `modules/database_manager.py:3210` («# CLIPBOARD HISTORY») |

Полный вывод: `b8-12\protection2_grep.txt`. Реальных ссылок на удалённые модули — 0.

### 4.4 Защита 3: pyflakes
`run_pyflakes.py after`: **596 warnings; 143 undefined-строки** (149 − 6).
Diff по уникальным именам (`undef_before_counts.txt` / `undef_after_counts.txt`):
**gone = GlossaryInfo (4) + TermEntry (2) = 6; new = ∅**. Остальные счётчики
идентичны (tk 100, messagebox 19, dialog 8, ttk 5, tabs 3, layout 2, import_tab 2,
filedialog 2, e 1, LLMClient 1). 143 = 149 − 6 — совпало с предсказанием trial-пробы
инвентаря (`batch8-12_undefined_names_trial.txt`).

### 4.5 Headless-импорт
`headless_imports.py` + `setup.py`: **92 ok / 2 fail / 94** (fail: `pdf_rescue_Qt`
— fitz, `setup` — setuptools). Ожидалось ровно 2; новых падений нет.
(Из 93 модулей: 92 ok / 1 fail.)

### 4.6 Offscreen S-clean / S-upgrade (ПОЛНЫЕ сценарии — закрывает U-1)
- S-clean after (`probe_after_clean.log`): окно построено (9.0 с), main_tabs 6
  (Editor/TMs/Termbases/AI/SuperLookup/Settings), Settings 14 страниц,
  **DATA-TREE 28 записей — идентичен before** (diff только в tag-префиксе и пути iso).
- S-upgrade after (`probe_after_upgrade.log`): PROBE OK (8.1 с), **HASH-DIFF пуст**
  (added/removed/changed/transient = []) — идентично before.

### 4.7 Регрессия общих путей
`regress_common.py … after`: import txt=5, md=5, docx=4; sha256 simple.txt
`5a12501f934a589c`, translated.docx `44828d90090f046d`, grid.tmx
`c413d56372e69dd9` — **идентично before** (число сегментов и хэши). MODAL-ATTEMPTS
4 — те же.

### 4.8 Tools-smoke ПОСЛЕ против ДО
`tools_smoke.py` — прямой программный вызов обработчика каждого из 44 пунктов меню
Project/Tools/Help (Exit пропущен). Прямые вызовы вместо `action.trigger()`: PyQt6
при исключении в слоте, достигнутом через сигнал, вызывает qFatal и прерывает
процесс (это проявилось на PDF Rescue без fitz в первом прогоне).

Результат after: **44/44 пункта отработали**, 2 исключения — те же, что в baseline:
- `Project/Import/GNU-gettext`: `TypeError: import_po_file() missing 1 required
  positional argument: 'self'` — предсуществующий дефект (метод 32719 помечен
  `@staticmethod`-комментарием выше и вызывается как бинд-метод; воспроизводится
  идентично в before-коде worktree, к батчу не относится);
- `Tools/PDF-Rescue`: `ModuleNotFoundError: No module named 'fitz'` — PyMuPDF не
  установлен (как до батча; в тестовой сборке fitz есть).

Diff ITEM-строк before2 (worktree 768fe720, свежий iso) vs after: расхождений по
исключениям/обработчикам/побочным вызовам **нет**. Единственное различие —
в 5 пунктах (New Project, Superlookup, Log-Window, Token-Usage, About) в after-логе
появляется доп. top-level `QMenu`. Диагноз: артефакт состояния профиля, не кода —
QMenu-виджеты меню-бара создаются лениво после миграций БД. Проверено пробой
`qmenu_probe2.py`: before-код + свежий iso = 27 QMenu на старте; after-код +
популированный iso (копия before-профиля с готовой БД) = **27 QMenu** — идентично.
Свежий iso в after-прогоне = 26 (миграции не выполнены). Расхождения поведения нет.

### 4.9 Termbase-регрессия (закрывает U-2)
`regress_termbase.py` в worktree (before) и репозитории (after), изолированные
профили: создать термбазу → id=1; add_term ok; update_term ok (target_after_update
«домик»); export_tsv ok (1 термин); import_tsv ok (terms_after_import=1);
delete_term ok (terms_after_delete=0); вкладка Termbases — QWidget, 2 таблицы,
колонки `[Source Term, Target Term, Domain, Notes, Project, Client, Forbidden,
Created, ""]` и `[Type, Name, Languages, Terms, Read, Write, Project, AI,
🔍 SuperLookup]` (без 🎤 Voice — как до батча); список термбаз `probe_tb812 en→ru`.
**Снапшоты before/after идентичны.** Единственное различие — sha256 TSV-экспорта
(`ec7c7139…` vs `747fdeaa…`): в TSV колонка «Term UUID» — случайный uuid4,
сгенерированный при add_term; содержимое файла построчно совпадает
(проверено: `house/домик/general/probe2/FALSE`).

### 4.10 Совместимость старых .svproj (U-3)
Образцов `.svproj` в репозитории и в артефактах проб нет (`find … -name "*.svproj"`
= пусто). Проверка перенесена в §7 «Непокрытые проверки».

### 4.11 wc -l до/после

| Файл | до | после | Δ |
|---|---|---|---|
| Supervertaler.py | 57010 | 57009 | −1 |
| modules/statuses.py | 244 | 183 | −61 |
| modules/help_system.py | 263 | 255 | −8 |
| modules/termbase_manager.py | 1497 | 1431 | −66 |
| modules/styled_widgets.py | 498 | 494 | −4 |
| 17 модулей | 6734 | 0 | −6734 |
| modules/**/*.py | 110 файлов | 93 файла | −17 |
| **Итого удалено** | | | **6874 строк** (6734 + 140) |

---

## 5. ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ (`D:\SupervertalerPortable_test\`)

База кода: **d308a93f**. SHA256 — полные (кроме помеченных 16-символьных для удалённых).

| № | Путь | Действие | SHA256 | Примечание |
|---|---|---|---|---|
| 1 | `Supervertaler\Supervertaler.py` | ЗАМЕНИТЬ | `80d53b439a92335007c82593dbd81585d11fbecfe2a60131f9ede5b9a2f1ac43` | удалена строка импорта StatusDefinition (57009 строк) |
| 2 | `Supervertaler\modules\statuses.py` | ЗАМЕНИТЬ | `163156909e533d424532514cc3f02e8c5ddd2577d12c500e761cd2baab9c76a1` | 183 строк |
| 3 | `Supervertaler\modules\help_system.py` | ЗАМЕНИТЬ | `7c6c82597e39addc1386bf14e42b25ebaab16c83099c340e69665257a2f086cf` | 255 строк |
| 4 | `Supervertaler\modules\termbase_manager.py` | ЗАМЕНИТЬ | `b2788a52b4f32b4015faaac137405655f22c0baa88bf7a7f0b526953c592ab27` | 1431 строк |
| 5 | `Supervertaler\modules\styled_widgets.py` | ЗАМЕНИТЬ | `76bbfa48a6ebad1407019e5677c5137b40cf4c34bbb3a57e2512d6f2391011e5` | 494 строки |
| 6 | `Supervertaler\modules\extract_tm.py` | **УДАЛИТЬ** | `480df7bb82645fb5…` (HEAD) | 518 строк |
| 7 | `Supervertaler\modules\feature_manager.py` | **УДАЛИТЬ** | `72e229c6174e07f1…` | 342 |
| 8 | `Supervertaler\modules\find_replace.py` | **УДАЛИТЬ** | `001e585f4a69fa99…` | 164 |
| 9 | `Supervertaler\modules\glossary_manager.py` | **УДАЛИТЬ** | `8abee58ad1fa0a48…` | 429 |
| 10 | `Supervertaler\modules\identifier_conventions.py` | **УДАЛИТЬ** | `06a5e3b7e1a74667…` | 83 |
| 11 | `Supervertaler\modules\pdf_rescue_tkinter.py` | **УДАЛИТЬ** | `22efef527d0772fb…` | 910 |
| 12 | `Supervertaler\modules\project_home_panel.py` | **УДАЛИТЬ** | `f1ab37f0c2c61a43…` | 209 |
| 13 | `Supervertaler\modules\project_tm.py` | **УДАЛИТЬ** | `460e417d4ddefce5…` | 320 |
| 14 | `Supervertaler\modules\prompt_assistant.py` | **УДАЛИТЬ** | `351d294ab6f11efb…` | 360 |
| 15 | `Supervertaler\modules\prompt_library.py` | **УДАЛИТЬ** | `9cbe0718fdecb729…` | 689 |
| 16 | `Supervertaler\modules\quick_access_sidebar.py` | **УДАЛИТЬ** | `1dafcf2f73cf0255…` | 278 |
| 17 | `Supervertaler\modules\ribbon_widget.py` | **УДАЛИТЬ** | `240180d32e0ebb12…` | 608 |
| 18 | `Supervertaler\modules\style_guide_manager.py` | **УДАЛИТЬ** | `5fde1e5320bbcff9…` | 315 |
| 19 | `Supervertaler\modules\superdocs.py` | **УДАЛИТЬ** | `75d4f9a1ab857469…` | 20 |
| 20 | `Supervertaler\modules\superdocs_viewer_qt.py` | **УДАЛИТЬ** | `d6b09f60ae51811e…` | 305 |
| 21 | `Supervertaler\modules\tracked_changes.py` | **УДАЛИТЬ** | `ccbee5c95dddd7f7…` | 903 |
| 22 | `Supervertaler\modules\translation_services.py` | **УДАЛИТЬ** | `dfd48cbcb7f2fe6f…` | 281 |

Удаление 17 файлов в тестовой сборке **обязательно** (иначе забытый импорт не
проявится). `__pycache__` удалённых модулей в сборке — удалить.

### Сценарии (на КОПИИ user_data; сначала КОНТРОЛЬ на базовой сборке d308a93f)

- **T8.12.1** старт без исключений; 6 вкладок; 14 страниц Settings; в логе нет traceback.
- **T8.12.2** Tools: каждый пункт открывается (TMX Editor, PDF Rescue, Statistics,
  Quick Count, Image Extractor, Scratchpad, Log Window, Token Usage & Cost) —
  поведение как на контроле (PDF Rescue без PyMuPDF — как до батча).
- **T8.12.3** AI: Chat, Prompt Manager (запуск промпта), AI Assistant — без
  исключений, ответ приходит.
- **T8.12.4** импорт docx/txt/md, экспорт Translated document / Simple text / TMX —
  файлы создаются и открываются.
- **T8.12.5** статусы в гриде: смена статуса сегмента, фильтр по статусу,
  сохранение/открытие проекта — статусы на месте.
- **T8.12.6** Termbases: открыть, создать термбазу, добавить/изменить/удалить термин,
  импорт/экспорт — без исключений.
- **T8.12.7** TMs: список, чекбоксы, импорт TMX.
- **T8.12.8** Help-меню/F1 открываются без исключений.
- **T8.12.9** live-test: импорт 180/400 сегментов, перевод сегмента, Save,
  перезапуск; навигация по вкладкам.
- **T8.12.10** выход: иконка трея исчезает, процесс завершается (0xC0000005 —
  предсуществующий флаки), traceback нет.

Для чистого старта — процедура из 8.8 (бэкап указателей, указатель на пустую папку,
восстановление) — один быстрый прогон T8.12.1 + T8.12.4.

---

## 6. Итоговые счётчики

| Метрика | До | После |
|---|---|---|
| py_compile | 132/0 | 115/0 |
| modules/**/*.py | 110 | 93 |
| headless (с setup.py) | 104/7/111 | 92/2/94 |
| pyflakes warnings | 640 | 596 |
| undefined-строки | 149 | 143 (−6 = GlossaryInfo+TermEntry) |
| AST-цепочка монолита | 926/0 | 926/0 |
| S-clean DATA-TREE | 28 | 28 (идентично) |
| S-upgrade HASH-DIFF | пуст | пуст |
| Регрессия общих путей | 5/5/4, 3 хэша | идентично |
| Tools-smoke 44 пункта | 2 ожидаемых EXC | идентично |
| Termbase-регрессия | — | идентично |
| Строк в репо (5 файлов + 17 модулей) | 60246 | 53372 (−6874) |

---

## 7. Непокрытые проверки

- **U-3 (совместимость старых .svproj):** образцов `.svproj` в репозитории и в
  артефактах нет — загрузка до/после не выполнена. Покрытие: T8.12.9 (live-test
  Save/перезапуск) на тестовой сборке.
- **U-4 (пакеты requirements):** не затрагивалось (P2).
- **U-5 (реальный GUI-интерактив, трея, F1):** offscreen-пробы не покрывают
  трею/F1-фильтр — покрывается T8.12.8/T8.12.10.
- **U-6 (импорт/экспорт TSV термбазы через UI-диалоги):** проверен программно через
  классы `TermbaseImporter/TermbaseExporter` (headless); UI-путь (модалки) не
  покрывался offscreen — покрывается T8.12.6.
- Предсуществующий дефект `import_po_file` (`@staticmethod`-комментарий + бинд-вызов,
  TypeError при вызове из меню) воспроизведён идентично до/после — вне объёма 8.12,
  фиксируется как наблюдение.

## 8. Вопросы к Дмитрию

1. Предсуществующий дефект `Project → Import → GNU gettext` (`.po/.pot`): метод
   `import_po_file` (монолит 32719) вызывается из меню как бинд-метод, но рядом
   стоит комментарий `@staticmethod` (32715) — при программном вызове TypeError
   «missing self». В GUI-прогоне (T8.12.4) стоит проверить, открывается ли пункт
   через меню. Нужен ли отдельный пункт в бэклоге?
2. `modules/styled_widgets.py`: `PurpleCheckmarkCheckBox` сейчас не используется
   нигде (0 потребителей, grep). Комментарий обновлён, класс оставлен (по ТЗ).
   Удалить класс в 8.18 (мёртвые определения) или оставить?
3. `modules/termbase_manager.py`: после удаления voice-методов остались
   pyflakes-предупреждения (sqlite3/json/Tuple unused, f-string без плейсхолдеров,
   7 шт.) — предсуществующие, не трогал. Включить в 8.18?
4. `modules/translation_services.py` не имел завершающего newline (git-дифф
   6735 vs wc 6734) — зафиксировано, на результат не влияет.

---

## 9. Результаты тестов и ответы Дмитрия (2026-10-10)

### 9.1 Тесты на тестовой сборке

T8.12.1–T8.12.10 — **все ПОДТВЕРЖДЕНЫ** (T8.12.10 — с предсуществующим флаки
0xC0000005 при завершении, traceback нет). Процедура чистого старта из 8.8
(бэкап указателей → пустая папка → восстановление), быстрый прогон T8.12.1 +
T8.12.4 — **ПОДТВЕРЖДЕНО**. Batch #8.12 принят.

### 9.2 Ответы на вопросы §8

1. **GNU gettext.** Наблюдение Дмитрия: Project → Import → GNU gettext — нет
   реакции; Project → Export → диалог с кнопкой «открыть», дальше не проверялось.
   **Решение: ненужная функция — на удаление.**
   Уточнение на вопрос «это локализация интерфейса?»: **нет.** GNU gettext
   (.po/.pot) — формат каталогов локализации ПО (l10n: Linux/Django/WordPress);
   функция импортирует такой каталог как двуязычный переводческий проект и
   экспортирует перевод обратно в .po. «Нет реакции» на Import — это и есть
   зафиксированный дефект: декоратор `@staticmethod` (32713) отделён блоком
   комментариев (32714–32716) и «приклеивается» к `def import_po_file(self)`
   (32718) — вызов из меню даёт TypeError «missing self», слот гаснет.
   Предварительный состав удаления (границы пересчитать AST в батче реализации):
   пункты меню 7961–7964 (import) и 8022–8025 (export), обработчики
   `import_po_file` (32718–32838) и `export_po_file` (32841–…),
   `modules/po_handler.py` (POHandler), `current_project.po_source_path`,
   фильтры «PO (gettext)» (9478, 29751), «.po» в списке открываемых расширений
   (9455). Пункт добавлен в POST_BATCH8_BACKLOG §8.
2. **PurpleCheckmarkCheckBox** — УДАЛИТЬ в 8.18.
3. **pyflakes-предупреждения termbase_manager.py** (sqlite3/json/Tuple unused,
   f-string без плейсхолдеров, 7 шт.) — ВКЛЮЧИТЬ в 8.18.
4. **translation_services.py без завершающего newline** — отметить на исправление.
   Файл удалён в 8.12, дефект снят удалением; запись фиксируется как практика
   учёта (git-дифф vs wc −1 строка) для будущих батчей удалений.

---

Артефакты: `D:\Temp\SupervertalerPortable\refactoring\b8-12\` —
baseline/, snapshots/ (9 шт., sha256), probes/ (4 лога + iso-профили),
regress/ (before/after), smoke/ (before/before2/after), tb-regress/ (before/after),
recon_importers.json, recon_public_names.txt, protection2_grep.txt,
edits_diff.txt, chain_before/after.json, undefined_names_before/after.txt,
headless_before/after.txt, py_compile_after.txt, eol_before.txt, wc_before.txt.
