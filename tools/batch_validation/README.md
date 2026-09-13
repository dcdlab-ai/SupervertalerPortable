# tools/batch_validation — переиспользуемый набор валидации extraction-батчей

Скрипты, накопленные в Batch #2 / #3a / #3b / #3c (практики описаны в
`AGENTS.md`, разделы «Refactoring batch validation practices», «Behavioral
comparison of duplicate/merged implementations», «Full-app before/after probes
and user-data isolation»). Цель — не переписывать их с нуля в каждом новом
чате. Версия батча = маленький драйвер поверх этих скриптов в стейдж-каталоге.

Запускать интерпретатором bundled-рантайма: `E:\Dev\python-embed\python.exe`.

## Стейдж-каталог

Артефакты прогона складывать в
`D:\Temp\SupervertalerPortable\refactoring\batch-<N>\run-001\`
(см. AGENTS.md «Temporary files and test artifacts»). В репозиторий попадает
только отчёт «ОТЧЁТ Batch #N.txt» (gitignored) и, при необходимости, правки
планировочных документов.

## Скрипты

| Скрипт | Назначение | Использование |
|---|---|---|
| `manifest.py` | SHA256 всех `.py` репозитория (без `__pycache__`/`.git` и без самого каталога `batch_validation` — чтобы базовые линии оставались сравнимыми с батчами #1–#3c) для манифеста до/после | `python manifest.py <repo_root> <out.txt>` |
| `counts.py` | 8 обязательных метрик (`\.connect\(`, `QShortcut\(`, `create_shortcut\(`, `QTimer\(`, `timeout\.connect`, `QTimer\.timeout`, `singleShot`, `QMetaObject\.invokeMethod`) | `python counts.py <repo_root> <out.txt>` |
| `py_compile_all.py` | Компиляция всех `.py` репозитория | `python py_compile_all.py <repo_root>` → `COMPILE_OK` |
| `ast_classes.py` | Границы top-level классов по AST (не доверять номерам из документов) | `python ast_classes.py <файл.py> [Имя1,Имя2\|all]` |
| `callsites.py` | Все вхождения конструкторов/имён по regex в `.py` репозитория | `python callsites.py <repo_root> <regex> <out.txt>` |
| `pixel_compare.py` | Библиотека offscreen-сравнения рендеров: `render()`, `images_identical()` (попиксельно, с PNG-доказательствами) | импортировать из драйвера батча; см. docstring |
| `probe_app.py` | Полный снапшот живого приложения: `findChildren` по заданным классам + захват виджетов из модальных диалогов (патч `QDialog.exec` → снимок + Rejected); read-only | `python probe_app.py <repo_root> <out.json> [--classes A,B] [--dialog MethodName]` |
| `smoke_project.py` | Двухпроцессный smoke: сохранить `.svproj` программно созданным проектом → загрузить и проверить | `python smoke_project.py save\|load <path.svproj> [имя] [кол-во сегментов]` |

## Проверенный порядок Этапа 0/3 (кратко)

1. `git status` чист; манифест `manifest.py` → `manifest_before_*.txt`.
2. `py_compile_all.py`, `counts.py` → `baseline_counts_*.txt`.
3. Этап 1: `ast_classes.py` (границы/чистота), `callsites.py` (до).
4. Этап 2: снапшот переносимых блоков из `git HEAD` + sha256; правки.
5. Этап 3: `py_compile_all.py`, `counts.py` (после), `callsites.py` (после),
   `manifest.py` (после); пиксельный гейт и/или `probe_app.py` до/после
   (до — из `git worktree add <stage>/head-wt HEAD`); `smoke_project.py`.
6. Сравнение манифестов — Python-скриптом по двум файлам (не shell-awk,
   см. AGENTS.md «Path and tooling quirks»).

## Предупреждения

* `probe_app.py` read-only, но user-data путь берётся из глобального
  `~/.supervertaler_config.json` и НЕ зависит от cwd — smoke-тесты пишут
  (бэкапы проектов) в общий продовый каталог из любого дерева
  (см. AGENTS.md «Full-app before/after probes and user-data isolation»).
* Инстанциация `SupervertalerQt` занимает 1–2 минуты; всегда
  `python -u` + faulthandler (встроен в `probe_app.py` и `smoke_project.py`).
