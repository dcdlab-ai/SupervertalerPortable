"""modules.tagged_text — писатель InDesign Tagged Text (Batch I1).

Markdown → Adobe InDesign Tagged Text (.txt, UTF-16LE + BOM, CRLF).
Только stdlib. Продукт (Supervertaler.py) пакет не импортирует до I2.

Правила формата установлены ручными тестами I0/I0-B/I0-C
(docs/refactoring/reports/BATCH_I0_REPORT.md, s11.8–s11.9):
* кодировка только UTF-16LE + BOM, разделитель строк CRLF;
* строка 1 — ``<UNICODE-WIN>`` одна на строке (T4b1: однострочная шапка
  непригодна — InDesign читает файл как обычный текст);
* строка 2 — ``<Version:16.4><FeatureSet:InDesign-Roman>``; ColorTable
  по умолчанию НЕ пишется (решение координатора, s11.9); режимы
  ``minimal`` (Black+Paper) и ``gboh`` (дословно образец) — опционально;
* далее по одному Define*Style на строку, только использованные роли;
* экранирование в ТЕКСТЕ только ``\\ → \\\\``, ``< → \\<``, ``> → \\>``
  (T5b: «лишние» экранирования ``\\; \\: \\, \\=`` в тексте дают ошибки
  в логе InDesign); в ЗНАЧЕНИЯХ тегов — ``\\ < > : ; , = [ ] _`` (образец
  GBoH);
* HTML-сущности (только с «;») раскодируются, ``<br>`` → одиночный LF.

Состав: mdparse (md → блоки), writer (блоки → байты Tagged Text),
stylemap (JSON «роль → имя стиля»), __main__ (CLI для разработки).
"""
