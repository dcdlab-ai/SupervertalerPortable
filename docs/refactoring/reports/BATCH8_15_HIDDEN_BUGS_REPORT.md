# ОТЧЁТ Batch #8.15 — скрытые баги (E-01, E-02, E-03, массовый Write в TM, MyMemory OFF)

Дата: 2026-10-11. База: 41b7ece1 (код Batch #8.13b); старт по команде Дмитрия + промпт.
Эталон монолита: SHA256 `30799778e4462af1f0e8531806c2d5197290d87ae4ae63eb627e6889c5ace166`, 56 689 строк.

**Итог: 5 кодовых коммитов (8.15a…8.15e), монолит 56 689 → 56 524 строк
(SHA256 `3109531c64a14bd5bd193b43ff5784cead798ed5d1041438699e73c30f88f257`),
+ `modules/settings_service.py` (SHA256 `d76a28161d870253929124fdb1d92c4f74c88a600b25b9edcba289b982f23464`).**

## §0 Baseline и дрейф

* Дрейф `git diff --name-only 41b7ece1..HEAD` до старта: только docs (AGENTS.md, PROJECT_STATUS.md, docs/refactoring/*) — разрешено. Untracked `.zcode/*` не тронуты.
* EOL: `Supervertaler.py` i/lf w/crlf, `\r\r\n` = 0, CRLF-счёт = числу строк — на каждом шаге правок.
* py_compile (два счётчика, правило Дмитрия): канонический (вне docs/) **110 ok / 0 fail**; справочный **136 ok / 0 fail** — идентично до и после каждого коммита.
* headless imports: **91 ok / 2 fail** (setup, modules.pdf_rescue_Qt — известные), всего 93.
* pyflakes: **596 warnings / 143 undefined-строк / 10 имён**; в Supervertaler.py 17 undefined-хитов: 15 внутри сломанной копии show_about, `e` (E-02), `LLMClient` (E-03a).
* AST startup-chain: **922 вызова / 0 unresolved**.
* S-clean: **28 записей**; S-upgrade: **HASH-DIFF пуст**; regress_common: **6 результатов RESULTS** (хеши `5a12501f…`, `44828d90…`, `c413d563…`); Tools-smoke: **42 пункта, SMOKE OK**; termbase: **SNAP OK** (кроме uuid4-хеша экспорта — известная рандомность).

**Отклонение методологии (улучшение, зафиксировано):** скопированный из b8-13 апгрейд-профиль содержал файл-указатель `%APPDATA%/Supervertaler/config.json` со СТАРЫМ путём `…\b8-11\probes\iso-upgrade\Supervertaler` — апгрейд-пробы с 8.11 молча открывали чужой каталог (HASH-DIFF считался по каталогу, куда приложение не писало). В b8-15 указатели iso-clean/iso-upgrade перезаписаны на локальные iso-каталоги; сделан миграционный warm-up прогон; HASH-DIFF теперь измеряет реальную запись. Один прогон ДО фикса указателя добавил один файл (`workbench/ai_assistant/attachments/20261011`) в b8-11 stage-профиль (временная область, не боевые данные).

## §1 Рекон (ничего не правилось)

### E-01 — дублирующий show_about
* AST: два `def show_about` в SupervertalerQt: **#1 @48584–48754 (171 строка) — СЛОМАННАЯ копия**: тело от TMX-Import-диалога (`import_layout = QVBoxLayout(import_tab)`, `QLabel("<h3>Import TMX File</h3>")` …) с 15 pyflakes-undefined (`import_tab`×2, `dialog`×8, `tabs`×3, `layout`×2) + 1 redefinition-warning; **#2 @49438–49500 (63 строки) — ЖИВАЯ** (последнее определение побеждает; настоящий About-диалог).
* Единственный вызов: `8620: about_action.triggered.connect(self.show_about)` → резолвится в живую копию. СТОП-условие («сломанная окажется живой») НЕ сработало.
* Вырез: строки 48584–48755 (метод + хвостовой разделитель `    `); снапшот sha256 `432a28a01dffa10767346a9a327d65ce92f1f5ed88223171202806b1397f8e3c` (172 строки).

### E-02 — отложенный on_err со `str(e)`
* AST-скан всего монолита на паттерн «имя из `except … as X` внутри вложенной функции»: **ровно один экземпляр** — `check_for_updates` (48776) > `start_python_fallback` (48985) > `worker` (49023): `except Exception as e:` @49039 → `def on_err()` @49041 использует `show_offline_error(str(e))` @49047 → `QTimer.singleShot(0, on_err)` @49052 — вызов ПОСЛЕ выхода из except → `NameError: cannot access free variable 'e'`.
* Идиома соседей: `str(e)` синхронно (69 вхождений); для отложенного применён захват в момент ошибки (вариант (а) промпта): `err_text = str(e)`.
* **Находка для отчёта:** `check_for_updates` в текущей сборке закрыт ранним `return` (временное упрощение — открывает страницу релизов; комментарий «Until this is revisited»), т.е. весь fallback-механизм с багом — латентный код. Фикс обязателен: путь оживёт при возврате механизма.
* Снапшот зоны (после 8.15a) `adfa3bb442ffa64a84f2e52c2220f5aaad650f45ed6562945e2d8745a3ecf84c`.

### E-03 — vision-путь translate_current_segment (СТОП + решение Дмитрия)
* `translate_current_segment` @49676; vision-блок @50018–50047; `LLMClient.model_supports_vision(provider, model)` @50030 — имя не импортировано (E-03a); NameError глотается `except` @50046 → `images = None`.
* **СТОП-условие сработало:** фикс E-03a открывает **второй скрытый баг на том же пути (E-03b, найден 2026-10-11)**: `self.figure_context.pil_image_to_base64_png(img)` @50038 — у `FigureContextManager` НЕТ такого метода; `pil_image_to_base64_png` — функция уровня модуля (`modules/figure_context_manager.py:327`). После E-03a для openai/claude/custom_openai — AttributeError, глотается тем же except.
* Вопрос Дмитрию → решение: **чинить оба в 8.15c**; E-03b — локальный импорт модульной функции «ровно как в ≈10122» (монолит, Image Extractor: `from modules.figure_context_manager import pil_image_to_base64_png` + обычный вызов; тот же паттерн в `unified_prompt_manager_qt.py:4490`); `figure_context_manager.py` НЕ править, новых методов НЕ добавлять.
* **Проверка «третьего дефекта»** (AST-проход блока, `batch8-15_recon_vision_third_defect.py`): все атрибуты `self.figure_context.*` существуют (has_images @148, detect_figure_references @42, get_images_for_text @129), `LLMClient.model_supports_vision` — classmethod @534, форматы изображений сходятся с ветками клиента (openai/custom_openai+claude: `(ref, raw_base64)` → клиент строит data-URI @llm_clients.py:935; gemini: `(ref, PIL.Image)` @1120; у клиента двойной гейт vision @858). **Третьего дефекта НЕТ.**

### W — массовый Write в TM
* `toggle_all_write` @11319–11330: `hasattr(tm_metadata_mgr, 'set_tm_read_only')` → False → тихий no-op (баг с корня 13bd37fb; вердикт 8.13 §9.2). Правильный метод `set_read_only` (tm_metadata_manager.py:634).
* Семантика построчного обработчика `on_write_toggle` @11443–11453: `set_read_only(tm_id, not checked)` («checked = writable»), лог успеха, откат чекбокса при неудаче, **БЕЗ инвалидации кэша и refresh**.
* `toggle_all_read` @11299–11317: цикл + `invalidate_translation_cache(smart_invalidation=False)` + `refresh_tm_list()`.
* Заголовочная синхронизация @11506–11518 (пересчёт по строкам после refresh) и кнопка «Clear All Write» @11250–11253 (`toggle_all_write(False)`) заработают сами после фикса обработчика — доп. правок не требуют.
* Снапшот `d6ee73803d0b02c35561c429c98413be42806a8d1272bd510d2f42fded8bde79`.

### M — MyMemory по умолчанию OFF
* Авторитетный источник — `SettingsService.load_provider_enabled_states` (`modules/settings_service.py:336–364`): defaults-словарь (ключ @352) + ensure-defaults `setdefault`, который **только наполняет возвращаемый словарь и сам не пишет settings.json**.
* Все читатели получают словарь из сервиса (7 сайтов `load_provider_enabled_states()` в монолите + quicktrans через `parent_app`): инлайн-fallbacks `.get('mt_mymemory', True)` @20480/51119/51942/53274 и generic `.get(enabled_key, True)` @20602/quicktrans.py:345 **недостижимы через сервис** — потому не правились (минимальность). `Supervertaler.py:20599` (строка таблицы) и `:24027` (сохранение из UI) дефолтов не содержат.
* Таблица «место → текущий дефолт → новый дефолт»:

| Место | Роль | Было | Стало |
|---|---|---|---|
| modules/settings_service.py:352 | defaults-словарь сервиса (авторитетный) | True | **False** |
| Supervertaler.py:20480 | Settings UI чекбокс (fallback) | True | недостижим (сервис всегда отдаёт ключ) |
| Supervertaler.py:51119 | список MT-провайдеров (лейбл) | True | недостижим |
| Supervertaler.py:51942 | выбор MT-провайдера сегмента | True | недостижим |
| Supervertaler.py:53274 | compare panel MyMemory | True | недостижим |
| modules/quicktrans.py:345 | QuickTrans generic-fallback (все провайдеры) | True | не менялся (правка затронула бы все провайдеры) |
| Supervertaler.py:20599 | строка таблицы провайдеров | — | — |
| Supervertaler.py:24027 | сохранение из UI | — | — |

* Существующий пользователь: ключ в `ui.provider_enabled_states` есть → сохраняется любое значение (setdefault — no-op); ключа нет → False (правило «ключа нет → False»). Риск для существующего пользователя отсутствует (пробы §4.6).

## §2 Что сделано (зона | строки | действие | sha256)

| Коммит | Пункт | Зона (нумерация base 41b7ece1) | Действие | Строки | Snapshot sha256 |
|---|---|---|---|---|---|
| 30cde089 8.15a | E-01 | 48584–48755 | вырез затенённой сломанной копии show_about | −172 | `432a28a0…` |
| c2c9bafb 8.15b | E-02 | 49039–49052 | `err_text = str(e)` в except + `show_offline_error(err_text)` | +1 | `adfa3bb4…` (после 8.15a) |
| c183508f 8.15c | E-03a+b | 50018–50047 | 2 локальных импорта в начале try + вызов модульной функции | +3 | `c9831630…` |
| feeecdd4 8.15d | W | 11319–11330 | `set_read_only(tm_id, not checked)`, снят hasattr, + инвалидация кэша | +3 | `d6ee7380…` |
| adcebd47 8.15e | M | settings_service.py:352 | `'mt_mymemory': True → False` (+3 строки комментария) | +4 | `2bfbc7d5…` |

Монолит: 56 689 → 56 524 (−165). Все правки — строковые замены с проверкой границ assert'ами; EOL сохранены (`\r\r\n` = 0 на каждом шаге); `tm_metadata_manager.py`, `figure_context_manager.py`, regex ссылок на рисунки, PreTranslationWorker — не тронуты.

## §3 Ключевые диффы

* **8.15a:** чистое удаление 172 строк (git diff — только минусы). Живой `show_about` теперь один (@49266 после выреза), вызов @8620 не изменился.
* **8.15b:**
  ```python
  except Exception as e:
      err_text = str(e)          # + захват в момент ошибки
      def on_err():
          ...
          show_offline_error(err_text)   # было: str(e) -> NameError
  ```
* **8.15c:**
  ```python
  try:
      from modules.llm_clients import LLMClient                  # E-03a (образец ~10027)
      from modules.figure_context_manager import pil_image_to_base64_png  # E-03b (образец ~10122)
      ...
      images = [(ref, pil_image_to_base64_png(img)) for ref, img in images_for_text]
      # было: self.figure_context.pil_image_to_base64_png(img) -> AttributeError
  ```
* **8.15d:**
  ```python
  tm_metadata_mgr.set_read_only(tm_id, not checked)   # было: hasattr-guard + set_tm_read_only (no-op)
  ...
  try:
      self.invalidate_translation_cache(smart_invalidation=False)   # как в toggle_all_read
  except Exception:
      pass
  refresh_tm_list()
  ```
* **8.15e:** один ключ дефолта + комментарий о политике.

## §4 Валидация

### §4.1 После КАЖДОГО коммита (обойма)
py_compile 110/0 + 136/0 · headless 91/2 · AST chain 922/0 · pyflakes was/now (§4.7) · S-clean 28 записей · S-upgrade HASH-DIFF пуст · regress_common RESULTS идентичны baseline на каждом шаге (6 хешей) · Tools-smoke 42 пункта SMOKE OK · About-проба OK · termbase SNAP идентичен baseline (кроме известного uuid4-хеша экспорта). MODAL-ATTEMPTS 4→3 после первого прогона — известный артефакт (iso-профиль записал отказ статистики), хеши RESULTS идентичны.

### §4.2 E-01 спец-проба
About через меню (`QAction.trigger()`, полный сигнальный путь), QDialog.exec нейтрализован с захватом: заголовок «About Supervertaler Workbench», версия v1.10.371, 4 лейбла. **До (worktree 1d953b0b) и после — байтно идентичный JSON** (batch8-15_about_before/after.log).

### §4.3 E-02 спец-проба
Реальный исходник метода с диска (AST-границы), ранний return нейтрализован, `start_request("api")` → принудительный `start_python_fallback("probe: forced")`, `_fetch_latest_release_info_from_github` → raiser `RuntimeError("probe-net-down-42")`, worker синхронно (thread-hop убран: QTimer.singleShot, созданный в потоке без event loop, не доходит до главного — пре-существующее свойство механизма, вне объёма E-02). **Baseline: `NameError: cannot access free variable 'e'` в on_err (batch8-15_e02_before_NameError.log); после фикса: сообщение дошло до show_offline_error с текстом ошибки** (batch8-15_e02_after_OK.log).

### §4.4 E-03 спец-проба (4 провайдера; vision-флаг → True, клиент — заглушка, сеть не нужна)
| Провайдер | baseline (worktree 1d953b0b) | после 8.15c |
|---|---|---|
| openai | images = **null** | `[{ref:'1a', base64-png}]` |
| claude | images = **null** | `[{ref:'1a', base64-png}]` |
| custom_openai | images = **null** | `[{ref:'1a', base64-png}]` |
| gemini | images = **null** | `[{ref:'1a', PIL.Image 4×4}]` |

**Контроль оказался сильнее прогноза из решения: images=null у ВСЕХ четырёх, включая gemini** — NameError стоит ДО ветки провайдера. Формат аргументов заглушки соответствует ветке клиента. Дополнительно: сегмент без «Figure» — images=null, текстовые аргументы запроса байтно идентичны до/после (prompt sha `c5368fcd…`/`baad5249…`); custom_openai с НЕ-vision моделью (флаг False) — images=null, в логе «⚠️ Figures detected (1a) but model … doesn't support vision».
Ограничение среды: в embed-питоне нет tkinter → `ImageTk` → `PIL_AVAILABLE=False` → `load_from_folder` в ЭТОЙ среде недоступен; проба наполняла `figure_context_map` напрямую тем же объектом PIL.Image (см. §7, вопрос 3).

### §4.5 W спец-проба (3 TM в изолированной БД, `batch8-15_w_after_OK.log`)
Select All Write → все 3 `read_only=False`; снятие → все `True`; кнопка «Clear All Write» → все `True`; построчный чекбокс — только строка 1 переключилась; `invalidate_translation_cache(smart_invalidation=False)` — 4 вызова (по одному на массовое переключение).
(Урок пробы: у вкладки Termbases свои одноимённые «Select All Write»/«Clear All Write» — поиск контролов должен быть ограничен контейнером TM-таблицы.)

### §4.6 M спец-пробы (3 сценария)
* **clean** (settings.json отсутствует): логика False, UI-чекбокс unchecked; созданный приложением settings.json содержит только usage-statistics ключи (provider_enabled_states НЕ записывается на старте).
* **upgrade true**: засеян `{mt_mymemory: true}` → логика True, чекбокс checked, подключ `ui.provider_enabled_states` байтно не изменился за старт (pes_unchanged=true). Полный хеш файла меняется, т.к. приложение на первом старте iso дописывает `usage_statistics_enabled/asked` — init-запись, к провайдерам отношения не имеет.
* **upgrade false**: → логика False, чекбокс unchecked, pes не изменился.
* HASH-DIFF апгрейд-профильного S-пробника — пуст (§4.1).

### §4.7 pyflakes построчно (было/стало)
| Этап | warnings | undefined-строк | имена |
|---|---|---|---|
| baseline | 596 | 143 | 10 (tk 100, ttk 5, messagebox 19, dialog 8, LLMClient 1, e 1, filedialog 2, import_tab 2, layout 2, tabs 3) |
| 8.15a | 580 (−16: 15 undefined + 1 redefinition) | 128 | 6 |
| 8.15b | 578 (−1 undefined `e`; −1 «local var e never used») | 127 | 5 |
| 8.15c | 577 (−1 undefined LLMClient) | 126 | 4 |
| 8.15d/e | 577 | 126 | 4 |
Все 126 остаточных undefined — `modules/tmx_editor.py` (tkinter-редактор, вне объёма). **В Supervertaler.py undefined-имён теперь 0** (было 17 хитов). Изменения набора — ровно ожидаемые, иных нет.

## §5 ПАКЕТ ДЛЯ ТЕСТОВОЙ СБОРКИ

**Внимание: в отличие от ожидания промпта («заменить только Supervertaler.py») пакет — ДВА файла** (правка M физически живёт в settings_service.py; см. §8, вопрос 1):

| Файл | Действие | SHA256 |
|---|---|---|
| `Supervertaler.py` | ЗАМЕНИТЬ | `3109531c64a14bd5bd193b43ff5784cead798ed5d1041438699e73c30f88f257` |
| `modules/settings_service.py` | ЗАМЕНИТЬ | `d76a28161d870253929124fdb1d92c4f74c88a600b25b9edcba289b982f23464` |

Ничего не удалять. `git ls-files --eol`: оба файла i/lf (w/crlf у монолита, w/lf у settings_service — как в репо).

## §6 Сценарии ручного тестирования

* **T8.15.1 (E-01):** Help → ℹ️ About — диалог открывается, заголовок «About Supervertaler Workbench», версия v1.10.371, кликабельные ссылки supervertaler.com / beijer.uk.
* **T8.15.2 (E-02):** только offscreen — путь за ранним return (см. §1/E-02); вручную невоспроизводим до возврата механизма проверки обновлений.
* **T8.15.3 (E-03, vision):** возможен только с облачным vision-ключом (или локальной vision-моделью через custom_openai, если Дмитрий её поднимет): папка фигур с «Figure 1A.png», сегмент «As shown in Figure 1A…», перевод — в логе «✅ Including 1 figure images», у openai/claude/custom_openai и gemini изображение прикрепляется. Если ручной ключ недоступен — достаточно offscreen-проб §4.4.
* **T8.15.4 (E-03, контроль):** тот же сегмент, НЕ-vision модель → «⚠️ … doesn't support vision», перевод текстовый, без изображений.
* **T8.15.5 (W):** 3 TM → «Select All Write» — у всех Write включается (статус «writable»); «Clear All Write» — снимается у всех; построчный чекбокс работает; повторный перевод в TM с включённым Write пишет, с выключенным — нет; заголовочный чекбокс пересинхронизируется после refresh.
* **T8.15.6 (M):** чистый старт → Settings → MT: MyMemory выключена; апгрейд-копия с `mt_mymemory: true` → осталась включённой; с `false` → выключена.
* **T8.15.7 (общий smoke):** открытие .svproj, импорт txt/md/docx, TMX, выход.

## §7 Непокрытые проверки и находки

1. **Ранний return в check_for_updates** (временное упрощение) — fallback-механизм целиком мёртв в текущей сборке; фикс E-02 латентно-корректный. Отдельно: `QTimer.singleShot(0, …)` из worker-потока не доходит до главного loop'а (наблюдение пробы; то же касается on_ok) — механика доставки колбэков fallback'а вне объёма 8.15, материал для G5/отдельного прохода.
2. **PIL_AVAILABLE=False в dev-runtime** (нет tkinter → ImageTk): в ЭТОМ рантайме `FigureContextManager.load_from_folder` недоступен — vision-путь нельзя пройти end-to-end с реальной папкой фигур. Проба инъекцией в `figure_context_map` обошла это; поведенческие фиксы не задеты.
3. **Бродячий файл в репо:** `docs/refactoring/samples/Miniature Wargames #520.translation.md` (untracked, 176 КБ, mtime 27.07.2026, создан 10:20 сегодня в окно baseline-проб; источник установить не удалось — писателя в коде приложения нет, ни в temp, ни в боевых данных файла больше нет). Оставлен на месте незатреканным; вопрос к Дмитрию (§8.4).
4. **Одна проба до фикса указателя** дописала файл в b8-11 stage-профиль (§0) — временная область.
5. У «Select All Write»/«Clear All Write» есть одноимённые дубли на вкладке Termbases (не тронуты; их массовые переключатели работают со своей таблицей — вне объёма).
6. Smoke baseline не менялся (меню не менялись — 42 пункта на каждом шаге).

## §8 Вопросы к Дмитрию

1. **Пакет тестовой сборки: два файла** (Supervertaler.py + modules/settings_service.py) вместо ожидаемого одного — подтверждаешь? (Правка M невозможна из монолита: читатели получают словарь из сервиса.)
2. `docs/refactoring/samples/Miniature Wargames #520.translation.md` — твой артефакт? Удалить / оставить (сейчас untracked, ни во что не входит)?
3. Блиндаж для vision end-to-end: в dev- и, вероятно, тестовом runtime нет tkinter → `ImageTk` → фигуры не грузятся из папки (`load_from_folder` падает). Стоит ли (a) заменить `ImageTk`-импорт на ленивый/опциональный в figure_context_manager.py (1–2 строки, отдельный микробатч), (b) смириться (vision работает только там, где Pillow полный)?
4. E-02: оставляем временный ранний return в check_for_updates как есть (фикс латентный) — или планируешь возврат механизма проверки обновлений в отдельном батче?

## Handover (что дальше)

* **G5-аудит figure-context** (после 8.15): regex ссылок (figure_context_manager.py:62), пакетный PreTranslationWorker (0 использования figure_context/images), md-ссылки — материал отдельного решения.
* **8.18** (по команде + промпт): 63 мёртвых метода монолита группами 10–15 + новый модульный проход по modules/ — включая `set_bridged_to_trados` (29 строк, отдельный раздел в промпте 8.18 — решение 8.13 §9.3.3).
* **8.16** — docs-комментарии в коде (Trados/gettext-остатки в i18n.py:26, models.py, tools/extract_strings.py:10 и т.п.); **8.17** — документы репозитория (CODE_MAP_REFACTOR.md:1150, DEPENDENCY_MAP.md po_handler, раздел J инвентаря).
* Порядок по решению 8.12: 8.12 ✓ → 8.13 ✓ → **8.15 ✓ (этот отчёт)** → 8.18 → 8.16 → 8.17.
* Аудит-скрипты и логи: `docs/refactoring/audits/batch8-15_*` (17 скриптов + снапшоты `batch8-15_snapshots/` + before/after логи). Канонический smoke-baseline не менялся (batch8-13_code_tools_smoke.py, 42 пункта).
