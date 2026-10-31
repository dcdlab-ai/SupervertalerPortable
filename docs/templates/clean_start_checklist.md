# Чек-лист «чистый старт» (батч P1.8, замена E1 §3)

Сборка считается портативной, если «удаление папки сборки» полностью убирает
приложение и все его данные. Ниже — что разрешено появиться в корне сборки
после первого запуска (шаблон `start.bat` из этого каталога) и чего быть нигде
не должно.

## Что ДОЛЖНО (или может) появиться в корне сборки

Создаётся `start.bat` ещё до старта приложения:

| Путь | Когда |
|---|---|
| `temp\` | сразу (каталог `%TEMP%`/`%TMP%` процесса; при обычной работе остаётся пустым) |
| `pycache\` | сразу (единый кэш байткода Python; внутри — зеркало путей исходников) |

Создаётся приложением при первом запуске (data root `<корень>\Supervertaler\`):

| Путь | Когда |
|---|---|
| `Supervertaler\resources\supervertaler.db` (+ `-wal`/`-shm` во время работы) | старт базы |
| `Supervertaler\prompt_library\Translate\Default\Default Translation Prompt.md` | первый старт |
| `Supervertaler\prompt_library\Proofread\Default\Default Proofreading Prompt.md` и `UK to US English Localization.md` | первый старт |
| `Supervertaler\prompt_library\QuickLauncher\Default\` (Assess…, Define.md, `Explain\Explain selection…`) | первый старт |
| `Supervertaler\workbench\ai_assistant\` (`attachments\<ГГГГММДД>\`, `conversations\`, `index.json`) | первый старт |
| `Supervertaler\workbench\dictionaries\` (пустой) | первый старт |
| `Supervertaler\workbench\settings\themes.json` | первый старт |
| `Supervertaler\workbench\settings\settings.json` | после первого сохранения настроек |
| `Supervertaler\workbench\settings\recent_projects.json` | после первого сохранения проекта |
| `Supervertaler\workbench\backups\<проект>\<проект>_<дата>.svproj` | автоматические бэкапы |
| `Supervertaler\workbench\usage\usage-<ГГГГ-ММ>.jsonl` | локальный журнал использования (в файл, не в сеть) |
| `quicktrans.ini` (прямо в корне сборки) | после первого закрытия попапа QuickTrans |
| `last_directory.json` (прямо в корне сборки) | после первого файлового диалога |
| `Supervertaler\okapi-sidecar\` | только если Okapi скачивался по кнопке диалога либо JAR положен вручную |

## Чего быть НЕ должно (проверка после работы)

| Где | Что проверять | Как |
|---|---|---|
| Реестр | ключа `HKCU\Software\Supervertaler` не существует | `reg query "HKCU\Software\Supervertaler" /s` → «не удается найти указанный раздел» |
| Реестр | в автозагрузке нет значения `Supervertaler` | `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v Supervertaler` → «не удается найти» |
| `%APPDATA%`, `%LOCALAPPDATA%` | папки `Supervertaler` не пополняются (остатки прежних версий могут уже существовать — они должны остаться нетронутыми) | сравнить содержимое до/после |
| Профиль `C:\Users\<я>` | нет `~\.supervertaler_config.json`, `~\Supervertaler\`, `~\.config\autostart\supervertaler.desktop` | осмотр (проводник) |
| Системный `%TEMP%` (вне корня) | новых файлов приложения нет (AHK/PowerShell-скрипты вставки остаются в `<корень>\temp\`) | сравнить до/после |
| `Documents` | только файлы, которые пользователь сохранил сам (`.svproj` и экспорты); ничего служебного от приложения | осмотр |
| `SupervertalerPortable\` (код) | не обрастает `__pycache__` — байткод уходит в `<корень>\pycache\` | осмотр |

## Сборочные примечания (не про запуск)

* `python-embed\python313._pth` сборки обязан содержать строки
  `..\SupervertalerPortable` и `Lib\site-packages` — иначе embedded-интерпретатор
  не найдёт ни код, ни PyQt6 (`start.bat` это не компенсирует).
* JRE для Okapi в сборку не кладётся (QP1.11): Windows-ZIP ленивой загрузки несёт
  собственную JRE; ручная установка JAR = положить `okapi-sidecar.jar` в
  `<корень>\Supervertaler\okapi-sidecar\` и перезапустить приложение.

Проверено пробами батча P1.8 (offscreen, изолированный профиль, 2026-10-31):
чистый старт и полный цикл (импорт → перевод через фейк-сервер → сохранение →
закрытие) не создали ничего вне корня сборки; дифф реестра «до/после» пуст.
