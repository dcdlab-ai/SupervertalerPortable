# Промпт PDF Rescue для внешнего OCR-инструмента (vision-модель)

Сохранено при удалении модуля PDF Rescue (BATCH P2.2, решение Дмитрия 2026-10-31 —
за PDF отвечает внешний инструмент). Текст ниже — **дословная копия** промпта,
который PDF Rescue отправлял vision-модели вместе с изображением страницы
(base64), без правок.

**Источник:** `modules/pdf_rescue_Qt.py`, строки 291–302 (константа
`default_instructions`), коммит `119f89a2` (origin/main после пуша P2.1).
Условная модификация: при включённом «Preserve Formatting» последняя содержательная
строка (markdown-форматирование) остаётся; при выключенном — удаляется из текста
промпта (логика в `pdf_rescue_Qt.py:565–573`, тот же текст).

---

```text
Extract all text from this image. The image is a screenshot from a poorly formatted PDF.
Please:
- Extract all visible text accurately
- Fix any obvious OCR errors or formatting issues
- Remove extraneous line breaks within paragraphs
- Preserve intentional paragraph breaks
- Maintain the logical flow and structure of the content
- For redacted/blacked-out text: insert a descriptive placeholder in square brackets in the document's language (e.g., [naam] for Dutch names, [name] for English names, [bedrag] for amounts, etc.)
- For stamps, signatures, or images: insert a descriptive placeholder in square brackets in the document's language (e.g., [handtekening], [stempel], [signature], [stamp], etc.)
- For any non-text elements that would normally appear: describe them briefly in square brackets
- Use markdown for text formatting: **bold text**, *italic text*, __underlined text__
- Output clean, readable text only (no commentary)
```

Условная строка (добавляется/удаляется целиком в зависимости от настройки
«сохранять форматирование»):

```text
- Use markdown for text formatting: **bold text**, *italic text*, __underlined text__
```

Параметры отправки: изображение страницы как base64 вместе с этими инструкциями;
Max Tokens: 4000 (текст UI `pdf_rescue_Qt.py:600,620`).
