"""
Tag Manager
Handle inline formatting tags (bold, italic, underline)

This module converts formatting runs into XML-like tags for editing,
validates tag integrity, and reconstructs formatting on export.

Example:
    "This is **bold** text" → "This is <b>bold</b> text"

ВАЖНО (Batch #2): модуль содержит ДВА блока с несовместимыми грамматиками
тегов — класс TagManager (выше, комбинированные теги <bi>/<li>, используется
docx_handler) и перенесённый из монолита tag-движок (ниже, вложенные теги
<b><i>…, используется Supervertaler.py). Блоки сосуществуют намеренно;
не объединять и не переключать callsites без решения владельца —
см. TECH-DEBT раздел EXTRACTION_PLAN.md и баннер перед Блоком 2.
"""

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import re


@dataclass
class FormattingRun:
    """Represents a formatting run in text"""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    subscript: bool = False
    superscript: bool = False
    start_pos: int = 0
    end_pos: int = 0
    
    def has_formatting(self) -> bool:
        """Check if this run has any formatting"""
        return self.bold or self.italic or self.underline or self.subscript or self.superscript
    
    def get_tag_name(self) -> str:
        """Get the tag name for this formatting"""
        if self.bold and self.italic:
            return "bi"
        elif self.bold:
            return "b"
        elif self.italic:
            return "i"
        elif self.underline:
            return "u"
        elif self.subscript:
            return "sub"
        elif self.superscript:
            return "sup"
        return None


class TagManager:
    """Manage inline formatting tags"""
    
    # Tag patterns - includes list item tags and sub/sup
    TAG_PATTERN = re.compile(r'<(/?)([biu]|bi|li|sub|sup)>')
    
    def __init__(self):
        self.tag_colors = {
            'b': '#CC0000',    # Red for bold
            'i': '#0066CC',    # Blue for italic
            'u': '#009900',    # Green for underline
            'bi': '#CC00CC',   # Purple for bold+italic
            'li': '#FF6600',   # Orange for list items
            'sub': '#666600',  # Olive for subscript
            'sup': '#006666'   # Teal for superscript
        }
    
    def extract_runs(self, paragraph) -> List[FormattingRun]:
        """
        Extract formatting runs from a python-docx paragraph

        Args:
            paragraph: python-docx paragraph object

        Returns:
            List of FormattingRun objects with position information
        """
        runs = []
        current_pos = 0

        # Check if paragraph style has bold/italic formatting
        # This handles cases like "Subtitle" or "Title" styles that are bold
        style_bold = False
        style_italic = False
        try:
            if paragraph.style and paragraph.style.font:
                if paragraph.style.font.bold:
                    style_bold = True
                if paragraph.style.font.italic:
                    style_italic = True
        except Exception:
            pass  # If we can't read style, just use run-level formatting

        # Helper function to process a single run element
        def process_run_element(run_elem, style_bold, style_italic):
            """Process a run element (w:r) and return FormattingRun or None"""
            from docx.text.run import Run
            try:
                run = Run(run_elem, paragraph)
                text = run.text
                if not text:
                    return None

                # Combine run-level formatting with style-level formatting
                is_bold = run.bold if run.bold is not None else style_bold
                is_italic = run.italic if run.italic is not None else style_italic

                return FormattingRun(
                    text=text,
                    bold=is_bold or False,
                    italic=is_italic or False,
                    underline=run.underline or False,
                    subscript=run.font.subscript or False if run.font else False,
                    superscript=run.font.superscript or False if run.font else False,
                    start_pos=0,  # Will be set later
                    end_pos=0     # Will be set later
                )
            except Exception:
                return None

        # Iterate through all child elements of the paragraph
        # This includes both direct runs (w:r) AND hyperlinks (w:hyperlink)
        from docx.oxml.ns import qn

        for child in paragraph._element:
            tag = child.tag

            # Direct run (w:r)
            if tag == qn('w:r'):
                run_info = process_run_element(child, style_bold, style_italic)
                if run_info:
                    run_info.start_pos = current_pos
                    run_info.end_pos = current_pos + len(run_info.text)
                    runs.append(run_info)
                    current_pos += len(run_info.text)

            # Hyperlink (w:hyperlink) - contains runs inside it
            elif tag == qn('w:hyperlink'):
                # Process all runs inside the hyperlink
                for run_elem in child.findall(qn('w:r')):
                    run_info = process_run_element(run_elem, style_bold, style_italic)
                    if run_info:
                        run_info.start_pos = current_pos
                        run_info.end_pos = current_pos + len(run_info.text)
                        runs.append(run_info)
                        current_pos += len(run_info.text)

        return runs
    
    def runs_to_tagged_text(self, runs: List[FormattingRun]) -> str:
        """
        Convert formatting runs to tagged text
        
        Example:
            [Run("Hello ", bold=False), Run("world", bold=True), Run("!", bold=False)]
            → "Hello <b>world</b>!"
        
        Args:
            runs: List of FormattingRun objects
            
        Returns:
            Text with inline tags
        """
        if not runs:
            return ""
        
        result = []
        current_formatting = {'bold': False, 'italic': False, 'underline': False, 'subscript': False, 'superscript': False}
        
        for run in runs:
            # Determine what formatting changed
            formatting_changed = (
                run.bold != current_formatting['bold'] or
                run.italic != current_formatting['italic'] or
                run.underline != current_formatting['underline'] or
                run.subscript != current_formatting['subscript'] or
                run.superscript != current_formatting['superscript']
            )
            
            if formatting_changed:
                # Close previous tags (in reverse order of nesting)
                if current_formatting['subscript']:
                    result.append('</sub>')
                if current_formatting['superscript']:
                    result.append('</sup>')
                if current_formatting['bold'] and current_formatting['italic']:
                    result.append('</bi>')
                elif current_formatting['bold']:
                    result.append('</b>')
                elif current_formatting['italic']:
                    result.append('</i>')
                elif current_formatting['underline']:
                    result.append('</u>')
                
                # Open new tags
                if run.bold and run.italic:
                    result.append('<bi>')
                elif run.bold:
                    result.append('<b>')
                elif run.italic:
                    result.append('<i>')
                elif run.underline:
                    result.append('<u>')
                if run.subscript:
                    result.append('<sub>')
                if run.superscript:
                    result.append('<sup>')
                
                # Update current state
                current_formatting['bold'] = run.bold
                current_formatting['italic'] = run.italic
                current_formatting['underline'] = run.underline
                current_formatting['subscript'] = run.subscript
                current_formatting['superscript'] = run.superscript
            
            result.append(run.text)
        
        # Close any remaining tags
        if current_formatting['subscript']:
            result.append('</sub>')
        if current_formatting['superscript']:
            result.append('</sup>')
        if current_formatting['bold'] and current_formatting['italic']:
            result.append('</bi>')
        elif current_formatting['bold']:
            result.append('</b>')
        elif current_formatting['italic']:
            result.append('</i>')
        elif current_formatting['underline']:
            result.append('</u>')
        
        return ''.join(result)
    
    def tagged_text_to_runs(self, text: str) -> List[Dict[str, Any]]:
        """
        Convert tagged text back to run specifications
        
        Example:
            "Hello <b>world</b>!" →
            [{'text': 'Hello ', 'bold': False},
             {'text': 'world', 'bold': True},
             {'text': '!', 'bold': False}]
        
        Args:
            text: Text with inline tags
            
        Returns:
            List of run specifications (dicts with text and formatting)
        """
        runs = []
        current_formatting = {'bold': False, 'italic': False, 'underline': False, 'subscript': False, 'superscript': False}
        current_text = []
        
        pos = 0
        while pos < len(text):
            # Check for tag
            match = self.TAG_PATTERN.match(text, pos)
            if match:
                # Save current text as a run
                if current_text:
                    runs.append({
                        'text': ''.join(current_text),
                        'bold': current_formatting['bold'],
                        'italic': current_formatting['italic'],
                        'underline': current_formatting['underline'],
                        'subscript': current_formatting['subscript'],
                        'superscript': current_formatting['superscript']
                    })
                    current_text = []
                
                # Process tag
                is_closing = match.group(1) == '/'
                tag_name = match.group(2)
                
                if tag_name == 'bi':
                    current_formatting['bold'] = not is_closing
                    current_formatting['italic'] = not is_closing
                elif tag_name == 'b':
                    current_formatting['bold'] = not is_closing
                elif tag_name == 'i':
                    current_formatting['italic'] = not is_closing
                elif tag_name == 'u':
                    current_formatting['underline'] = not is_closing
                elif tag_name == 'sub':
                    current_formatting['subscript'] = not is_closing
                elif tag_name == 'sup':
                    current_formatting['superscript'] = not is_closing
                
                pos = match.end()
            else:
                # Regular character
                current_text.append(text[pos])
                pos += 1
        
        # Save final text
        if current_text:
            runs.append({
                'text': ''.join(current_text),
                'bold': current_formatting['bold'],
                'italic': current_formatting['italic'],
                'underline': current_formatting['underline'],
                'subscript': current_formatting['subscript'],
                'superscript': current_formatting['superscript']
            })
        
        return runs
    
    def validate_tags(self, text: str) -> Tuple[bool, str]:
        """
        Validate that all tags are properly paired and nested
        
        Args:
            text: Text with inline tags
            
        Returns:
            (is_valid, error_message)
        """
        stack = []
        pos = 0
        
        while pos < len(text):
            match = self.TAG_PATTERN.match(text, pos)
            if match:
                is_closing = match.group(1) == '/'
                tag_name = match.group(2)
                
                if is_closing:
                    if not stack:
                        return False, f"Closing tag </{tag_name}> without opening tag"
                    if stack[-1] != tag_name:
                        return False, f"Mismatched tags: expected </{stack[-1]}>, found </{tag_name}>"
                    stack.pop()
                else:
                    stack.append(tag_name)
                
                pos = match.end()
            else:
                pos += 1
        
        if stack:
            return False, f"Unclosed tags: {', '.join(stack)}"
        
        return True, ""
    
    def count_tags(self, text: str) -> Dict[str, int]:
        """
        Count tags in text
        
        Returns:
            Dictionary with tag counts (e.g., {'b': 2, 'i': 1})
        """
        counts = {}
        pos = 0
        
        while pos < len(text):
            match = self.TAG_PATTERN.match(text, pos)
            if match:
                is_closing = match.group(1) == '/'
                if not is_closing:  # Only count opening tags
                    tag_name = match.group(2)
                    counts[tag_name] = counts.get(tag_name, 0) + 1
                pos = match.end()
            else:
                pos += 1
        
        return counts
    
    def strip_tags(self, text: str) -> str:
        """Remove all tags from text"""
        return self.TAG_PATTERN.sub('', text)
    
    def get_tag_color(self, tag_name: str) -> str:
        """Get color for tag name"""
        return self.tag_colors.get(tag_name, '#000000')
    
    def format_for_display(self, text: str) -> str:
        """
        Format tagged text for display (simplified version)
        This could be enhanced with colored markers in a rich text widget
        
        For now, just show tags as-is
        """
        return text


# ============================================================================
# БЛОК 2 — DOCX tag-движок, перенесённый вербатим из монолита Supervertaler.py
# (Batch #2, Step 2 EXTRACTION_PLAN.md).
#
# ВНИМАНИЕ: этот блок и класс TagManager выше — ДВЕ НЕСОВМЕСТИМЫЕ РЕАЛИЗАЦИИ
# с разными грамматиками тегов, сосуществующие НАМЕРЕННО (решение владельца
# от 2026-09-12):
#   * Класс TagManager выше кодирует bold+italic комбинированным тегом
#     "<bi>...</bi>" и распознаёт <bi>/<li>; его использует docx_handler
#     (self.tag_manager.*).
#   * Функции ниже кодируют то же форматирование ВЛОЖЕННО ("<b><i>x</i></b>");
#     "<bi>" и "<li>" для них — литеральный текст. Их вызывает монолит.
# НЕ объединять блоки и НЕ переключать callsites между ними без отдельного
# решения владельца — это изменит поведение приложения (подробности и
# расходящиеся примеры: TECH-DEBT раздел EXTRACTION_PLAN.md).
# ============================================================================

# ============================================================================
# УТИЛИТЫ ВНУТРЕННЕГО ФОРМАТИРОВАНИЯ (теги DOCX <-> размеченный текст)
# ============================================================================

def runs_to_tagged_text(paragraphs) -> str:
    """
    Преобразует абзацы Word (python-docx) с форматированием run'ов
    в текст с внутренними HTML-подобными тегами.

    Аргументы:
        paragraphs: список объектов python-docx Paragraph.

    Возвращает:
        строку с тегами форматирования, например
        "<b>bold</b> обычный <sub>V</sub>".
    """
    result_parts = []

    for paragraph in paragraphs:
        for run in paragraph.runs:
            text = run.text
            if not text:
                continue

            # Определяем, какие теги нужно применить к этому run'у
            is_bold = run.bold == True
            is_italic = run.italic == True
            is_underline = run.underline == True
            is_subscript = getattr(run.font, 'subscript', None) == True
            is_superscript = getattr(run.font, 'superscript', None) == True

            # Вложенные теги собираются заменой уже вставленных открывающих
            # тегов (str.replace) — корректно, потому что текст run'а ещё
            # не содержит тегов.
            if is_bold or is_italic or is_underline or is_subscript or is_superscript:
                # Открывающие теги (порядок: bold, italic, underline, sub/sup)
                if is_bold:
                    text = f"<b>{text}"
                if is_italic:
                    text = f"<i>{text}" if not is_bold else text.replace("<b>", "<b><i>", 1)
                if is_underline:
                    if is_bold and is_italic:
                        text = text.replace("<b><i>", "<b><i><u>", 1)
                    elif is_bold:
                        text = text.replace("<b>", "<b><u>", 1)
                    elif is_italic:
                        text = text.replace("<i>", "<i><u>", 1)
                    else:
                        text = f"<u>{text}"
                if is_subscript:
                    text = f"<sub>{text}"
                if is_superscript:
                    text = f"<sup>{text}"

                # Закрывающие теги (в обратном порядке: sup, sub, underline, italic, bold)
                if is_superscript:
                    text = f"{text}</sup>"
                if is_subscript:
                    text = f"{text}</sub>"
                if is_underline:
                    text = f"{text}</u>"
                if is_italic:
                    text = f"{text}</i>"
                if is_bold:
                    text = f"{text}</b>"

            result_parts.append(text)

    return ''.join(result_parts)


def strip_formatting_tags(text: str) -> str:
    """
    Удаляет HTML-теги форматирования из текста, оставляя чистый текст.

    Аргументы:
        text: текст с тегами вида <b>, </b>, <i>, </i>, <u>, </u>,
              <sub>, </sub>, <sup>, </sup>

    Возвращает:
        текст без тегов
    """
    import re
    return re.sub(r'</?(?:[biu]|sub|sup)>', '', text)


def strip_outer_wrapping_tags(text: str) -> tuple:
    """
    Снимает внешнюю «обёртку» из тегов, если сегмент ЦЕЛИКОМ обёрнут одной парой.

    Обрабатывает структурные теги вроде <li-o>...</li-o>, <p>...</p>,
    <td>...</td>, а также теги форматирования <b>...</b> — но только когда
    они обёртывают *весь* сегмент. Внутреннее форматирование
    (например, "Some <b>bold</b> text") не затрагивается никогда.

    Аргументы:
        text: текст, возможно обёрнутый во внешние теги

    Возвращает:
        кортеж (текст_без_обёртки, имя_тега); если внешней пары не нашлось —
        (исходный_текст, None)

    Примеры:
        "<li-o>Hello <b>world</b></li-o>" -> ("Hello <b>world</b>", "li-o")
        "<p>Simple text</p>" -> ("Simple text", "p")
        "No tags here" -> ("No tags here", None)
        "<b>Bold text</b>" -> ("Bold text", "b")  # <b> обёртывает весь сегмент -> снимаем
    """
    import re

    if not text or not text.strip():
        return (text, None)

    text = text.strip()

    # Теги, способные обёртывать весь сегмент — структурные И форматированные.
    # Форматированные (b, i, u, …) включены, потому что, обёртывая *весь*
    # сегмент, они играют роль структурной обёртки; функция и так снимает
    # только одну самую внешнюю пару, поэтому внутреннее форматирование
    # вроде "Some <b>bold</b> text" не пострадает.
    strippable_tags = {
        # Структурные / разметочные
        'li-o', 'li-b', 'li', 'p', 'td', 'th', 'tr', 'div', 'span',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'title', 'caption',
        'blockquote', 'pre', 'code', 'dt', 'dd', 'header', 'footer',
        'article', 'section', 'aside', 'nav', 'main', 'figure', 'figcaption',
        # Форматированные (снимаются только как обёртка всего сегмента)
        'b', 'i', 'u', 'em', 'strong', 's', 'strike', 'sub', 'sup', 'mark',
    }

    # Шаблон открывающего тега в начале: <tag> или <tag attr="...">
    opening_pattern = r'^<([a-zA-Z][a-zA-Z0-9-]*)(?:\s+[^>]*)?>(.*)$'
    opening_match = re.match(opening_pattern, text, re.DOTALL)

    if not opening_match:
        return (text, None)

    tag_name = opening_match.group(1).lower()
    rest = opening_match.group(2)

    # Снимаем только распознанные теги
    if tag_name not in strippable_tags:
        return (text, None)

    # Проверяем, что текст заканчивается парным закрывающим тегом
    closing_pattern = rf'^(.*)</{re.escape(tag_name)}>$'
    closing_match = re.match(closing_pattern, rest, re.DOTALL | re.IGNORECASE)

    if not closing_match:
        return (text, None)

    inner_content = closing_match.group(1)

    # Убеждаемся, что это действительно обёртка: внутри не должно быть других
    # вхождений того же тега. Считаем открывающие и закрывающие теги этого
    # типа во внутреннем содержимом.
    inner_opening_count = len(re.findall(rf'<{re.escape(tag_name)}(?:\s+[^>]*)?>',
                                          inner_content, re.IGNORECASE))
    inner_closing_count = len(re.findall(rf'</{re.escape(tag_name)}>', inner_content, re.IGNORECASE))

    # Есть вложенные теги того же типа — ничего не снимаем
    if inner_opening_count > 0 or inner_closing_count > 0:
        return (text, None)

    return (inner_content, tag_name)


def get_docx_language_code(lang_name_or_code: str) -> str:
    """
    Преобразует название или код языка в формат локали DOCX (например, 'nl-NL', 'en-US').

    В файлах DOCX используются языковые теги BCP 47 / RFC 5646 с кодом региона.

    Аргументы:
        lang_name_or_code: название языка (например, 'Dutch', 'English')
                           или код (например, 'nl', 'en')

    Возвращает:
        совместимый с DOCX код языка с регионом (например, 'nl-NL', 'en-US')
    """
    if not lang_name_or_code:
        return "en-US"  # Запасное значение по умолчанию

    lang_input = lang_name_or_code.strip()
    lang_lower = lang_input.lower()

    # Соответствие «название языка» -> полный код локали (с регионом).
    # Приоритет регионов: нидерландский -> Нидерланды, английский -> США и т.д.
    lang_map = {
        # Major languages with regional defaults
        "dutch": "nl-NL",
        "english": "en-US",
        "german": "de-DE",
        "french": "fr-FR",
        "spanish": "es-ES",
        "italian": "it-IT",
        "portuguese": "pt-PT",
        "russian": "ru-RU",
        "chinese": "zh-CN",
        "japanese": "ja-JP",
        "korean": "ko-KR",
        "arabic": "ar-SA",

        # Варианты нидерландского
        "dutch (netherlands)": "nl-NL",
        "dutch (belgium)": "nl-BE",
        "flemish": "nl-BE",

        # Варианты английского
        "english (us)": "en-US",
        "english (uk)": "en-GB",
        "english (australia)": "en-AU",
        "english (canada)": "en-CA",
        "american english": "en-US",
        "british english": "en-GB",

        # Варианты французского
        "french (france)": "fr-FR",
        "french (canada)": "fr-CA",
        "french (belgium)": "fr-BE",
        "french (switzerland)": "fr-CH",

        # Варианты немецкого
        "german (germany)": "de-DE",
        "german (austria)": "de-AT",
        "german (switzerland)": "de-CH",

        # Варианты испанского
        "spanish (spain)": "es-ES",
        "spanish (mexico)": "es-MX",
        "spanish (latin america)": "es-419",

        # Варианты португальского
        "portuguese (portugal)": "pt-PT",
        "portuguese (brazil)": "pt-BR",
        "brazilian portuguese": "pt-BR",

        # Варианты китайского
        "chinese (simplified)": "zh-CN",
        "chinese (traditional)": "zh-TW",
        "simplified chinese": "zh-CN",
        "traditional chinese": "zh-TW",

        # Другие европейские языки
        "afrikaans": "af-ZA",
        "albanian": "sq-AL",
        "armenian": "hy-AM",
        "basque": "eu-ES",
        "bengali": "bn-BD",
        "bulgarian": "bg-BG",
        "catalan": "ca-ES",
        "croatian": "hr-HR",
        "czech": "cs-CZ",
        "danish": "da-DK",
        "estonian": "et-EE",
        "finnish": "fi-FI",
        "galician": "gl-ES",
        "georgian": "ka-GE",
        "greek": "el-GR",
        "hebrew": "he-IL",
        "hindi": "hi-IN",
        "hungarian": "hu-HU",
        "icelandic": "is-IS",
        "indonesian": "id-ID",
        "irish": "ga-IE",
        "latvian": "lv-LV",
        "lithuanian": "lt-LT",
        "macedonian": "mk-MK",
        "malay": "ms-MY",
        "norwegian": "nb-NO",
        "persian": "fa-IR",
        "polish": "pl-PL",
        "romanian": "ro-RO",
        "serbian": "sr-RS",
        "slovak": "sk-SK",
        "slovenian": "sl-SI",
        "swahili": "sw-KE",
        "swedish": "sv-SE",
        "thai": "th-TH",
        "turkish": "tr-TR",
        "ukrainian": "uk-UA",
        "urdu": "ur-PK",
        "vietnamese": "vi-VN",
        "welsh": "cy-GB",
    }

    # Сначала пробуем полное название языка
    if lang_lower in lang_map:
        return lang_map[lang_lower]

    # Уже в формате локали (например, "nl-NL", "en-US")?
    if '-' in lang_input or '_' in lang_input:
        parts = lang_input.replace('_', '-').split('-')
        if len(parts) >= 2 and len(parts[0]) == 2:
            return f"{parts[0].lower()}-{parts[1].upper()}"

    # Двухбуквенный код: пробуем добавить регион по умолчанию
    code_to_region = {
        "nl": "NL", "en": "US", "de": "DE", "fr": "FR", "es": "ES",
        "it": "IT", "pt": "PT", "ru": "RU", "zh": "CN", "ja": "JP",
        "ko": "KR", "ar": "SA", "pl": "PL", "cs": "CZ", "da": "DK",
        "fi": "FI", "el": "GR", "hu": "HU", "no": "NO", "nb": "NO",
        "sv": "SE", "tr": "TR", "uk": "UA", "he": "IL", "th": "TH",
        "vi": "VN", "id": "ID", "ms": "MY", "ro": "RO", "bg": "BG",
        "hr": "HR", "sk": "SK", "sl": "SI", "et": "EE", "lv": "LV",
        "lt": "LT", "sr": "RS", "mk": "MK", "sq": "AL", "is": "IS",
        "ga": "IE", "cy": "GB", "eu": "ES", "ca": "ES", "gl": "ES",
        "af": "ZA", "sw": "KE", "hi": "IN", "bn": "BD", "ur": "PK",
        "fa": "IR", "hy": "AM", "ka": "GE",
    }

    if len(lang_input) == 2 and lang_lower in code_to_region:
        return f"{lang_lower}-{code_to_region[lang_lower]}"

    # Запасной вариант: вернуть как есть или с обобщённым регионом
    if len(lang_input) == 2:
        return f"{lang_lower}-{lang_input.upper()}"

    return "en-US"  # Крайний запасной вариант


def set_docx_language(doc, lang_code: str):
    """
    Задаёт язык для всего содержимого документа DOCX.

    Изменяет стиль абзаца по умолчанию и существующие абзацы так, чтобы
    орфография и проверка правописания в Word использовали указанный язык.

    Аргументы:
        doc: объект Document из python-docx
        lang_code: код языка в формате BCP 47 (например, 'nl-NL', 'en-US')

    Побочные эффекты: изменяет styles.xml (Normal) и rPr каждого run'а,
    включая таблицы. Все сбои молча игнорируются — расстановка языка
    не должна прерывать экспорт.
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    # Задаём язык в свойствах абзаца по умолчанию документа (styles.xml)
    try:
        # Доступ к части со стилями
        styles = doc.styles

        # Получаем (или создаём) rPr стиля Normal (свойства run'а)
        normal_style = styles['Normal']

        # Set language on the style's font/run properties
        if normal_style._element.rPr is None:
            rPr = OxmlElement('w:rPr')
            normal_style._element.append(rPr)
        else:
            rPr = normal_style._element.rPr

        # Remove existing lang element if present
        existing_lang = rPr.find(qn('w:lang'))
        if existing_lang is not None:
            rPr.remove(existing_lang)

        # Create and add new lang element
        lang_elem = OxmlElement('w:lang')
        lang_elem.set(qn('w:val'), lang_code)
        lang_elem.set(qn('w:eastAsia'), lang_code)
        lang_elem.set(qn('w:bidi'), lang_code)
        rPr.append(lang_elem)

    except Exception:
        pass  # Правка стиля не удалась — продолжаем с установкой на уровне абзацев

    # Также задаём язык для run'ов всех существующих абзацев, чтобы он
    # подействовал сразу
    for para in doc.paragraphs:
        for run in para.runs:
            try:
                # XML-элемент run'а
                run_elem = run._element

                # Get or create rPr
                rPr = run_elem.rPr
                if rPr is None:
                    rPr = OxmlElement('w:rPr')
                    run_elem.insert(0, rPr)

                # Remove existing lang element if present
                existing_lang = rPr.find(qn('w:lang'))
                if existing_lang is not None:
                    rPr.remove(existing_lang)

                # Create and add new lang element
                lang_elem = OxmlElement('w:lang')
                lang_elem.set(qn('w:val'), lang_code)
                rPr.append(lang_elem)
            except Exception:
                continue  # Run'ы, которые нельзя изменить, пропускаем

    # Тоже обрабатываем ячейки таблиц
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        try:
                            run_elem = run._element
                            rPr = run_elem.rPr
                            if rPr is None:
                                rPr = OxmlElement('w:rPr')
                                run_elem.insert(0, rPr)

                            existing_lang = rPr.find(qn('w:lang'))
                            if existing_lang is not None:
                                rPr.remove(existing_lang)

                            lang_elem = OxmlElement('w:lang')
                            lang_elem.set(qn('w:val'), lang_code)
                            rPr.append(lang_elem)
                        except Exception:
                            continue


def has_formatting_tags(text: str) -> bool:
    """
    Проверяет, содержит ли текст теги форматирования.

    Аргументы:
        text: текст для проверки

    Возвращает:
        True, если текст содержит <b>, <i>, <u>, <sub> или <sup>
    """
    import re
    return bool(re.search(r'</?(?:[biu]|sub|sup)>', text))


def apply_formatting_tags(text: str, tag: str) -> str:
    """
    Оборачивает текст указанным тегом форматирования.

    Аргументы:
        text: текст для обёртки
        tag: имя тега ('b', 'i' или 'u')

    Возвращает:
        текст с тегами вида "<b>text</b>"
    """
    if tag in ('b', 'i', 'u'):
        return f"<{tag}>{text}</{tag}>"
    return text


def get_formatted_html_display(text: str) -> str:
    """
    Преобразует наши простые теги в HTML для «богатого» отображения.

    Аргументы:
        text: текст с тегами <b>, <i>, <u>, <sub>, <sup>

    Возвращает:
        HTML-строку, пригодную для QTextEdit.setHtml()

    Суть: сначала заменяем СВОИ теги на невидимые маркеры, затем
    HTML-экранируем весь остальной текст (защита от инъекции разметки),
    и только потом восстанавливаем свои теги как настоящий HTML.
    """
    # Сначала экранируем HTML-сущности (кроме наших тегов)
    import html

    # Временно заменяем наши теги на маркеры-заполнители
    text = text.replace('<b>', '\x00B_OPEN\x00')
    text = text.replace('</b>', '\x00B_CLOSE\x00')
    text = text.replace('<i>', '\x00I_OPEN\x00')
    text = text.replace('</i>', '\x00I_CLOSE\x00')
    text = text.replace('<u>', '\x00U_OPEN\x00')
    text = text.replace('</u>', '\x00U_CLOSE\x00')
    text = text.replace('<sub>', '\x00SUB_OPEN\x00')
    text = text.replace('</sub>', '\x00SUB_CLOSE\x00')
    text = text.replace('<sup>', '\x00SUP_OPEN\x00')
    text = text.replace('</sup>', '\x00SUP_CLOSE\x00')

    # Экранируем остальной HTML
    text = html.escape(text)

    # Восстанавливаем наши теги уже как настоящий HTML
    text = text.replace('\x00B_OPEN\x00', '<b>')
    text = text.replace('\x00B_CLOSE\x00', '</b>')
    text = text.replace('\x00I_OPEN\x00', '<i>')
    text = text.replace('\x00I_CLOSE\x00', '</i>')
    text = text.replace('\x00U_OPEN\x00', '<u>')
    text = text.replace('\x00U_CLOSE\x00', '</u>')
    text = text.replace('\x00SUB_OPEN\x00', '<sub>')
    text = text.replace('\x00SUB_CLOSE\x00', '</sub>')
    text = text.replace('\x00SUP_OPEN\x00', '<sup>')
    text = text.replace('\x00SUP_CLOSE\x00', '</sup>')

    # Сохраняем пробелы при HTML-рендеринге (чтобы не схлопывались пробелы
    # и отступы)
    text = f'<span style="white-space: pre-wrap;">{text}</span>'

    return text


def tagged_text_to_runs(text: str) -> list:
    """
    Разбирает текст с HTML-тегами форматирования и возвращает список run'ов
    с информацией о форматировании.

    Аргументы:
        text: текст с тегами <b>, <i>, <u>, <sub>, <sup> (могут быть вложенными)

    Возвращает:
        список словарей с ключами: text, bold, italic, underline,
        subscript, superscript
    """
    import re

    runs = []

    # Текущее состояние форматирования
    is_bold = False
    is_italic = False
    is_underline = False
    is_subscript = False
    is_superscript = False

    # Шаблон открывающих/закрывающих тегов
    tag_pattern = re.compile(r'(</?(?:[biu]|sub|sup)>)')

    # Разбиваем текст по тегам, оставляя теги как разделители
    parts = tag_pattern.split(text)

    current_text = ""

    def _flush():
        nonlocal current_text
        if current_text:
            runs.append({
                'text': current_text,
                'bold': is_bold,
                'italic': is_italic,
                'underline': is_underline,
                'subscript': is_subscript,
                'superscript': is_superscript,
            })
            current_text = ""

    for part in parts:
        if part == '<b>':
            _flush()
            is_bold = True
        elif part == '</b>':
            _flush()
            is_bold = False
        elif part == '<i>':
            _flush()
            is_italic = True
        elif part == '</i>':
            _flush()
            is_italic = False
        elif part == '<u>':
            _flush()
            is_underline = True
        elif part == '</u>':
            _flush()
            is_underline = False
        elif part == '<sub>':
            _flush()
            is_subscript = True
        elif part == '</sub>':
            _flush()
            is_subscript = False
        elif part == '<sup>':
            _flush()
            is_superscript = True
        elif part == '</sup>':
            _flush()
            is_superscript = False
        else:
            # Обычный текст — накапливаем его
            current_text += part

    # Не забываем оставшийся текст
    _flush()

    return runs


# ============================================================================
# УТИЛИТЫ ТЕГОВ MEMOQ (для горячих клавиш вставки тегов)
# ============================================================================

def extract_memoq_tags(text: str) -> list:
    """
    Извлекает все теги в стиле memoQ из текста в порядке появления.

    memoQ использует несколько типов тегов:
    - Открывающие парные: [1}, [2}, [3} и т.д.
    - Закрывающие парные: {1], {2], {3] и т.д.
    - Автономные: [1], [2], [3] и т.д. (например, для табуляций,
      специальных символов)

    Аргументы:
        text: исходный текст с тегами

    Возвращает:
        список строк тегов в порядке появления: ['[1}', '{1]', '[2]', ...]
    """
    import re
    # Сопоставляем:
    # - Открывающие парные теги: [N}
    # - Закрывающие парные теги: {N]
    # - Автономные теги: [N]
    pattern = r'(\[\d+\}|\{\d+\]|\[\d+\])'
    return re.findall(pattern, text)


def extract_html_tags(text: str) -> list:
    """
    Извлекает все HTML/XML-теги из текста в порядке появления.

    Поддерживает распространённые теги форматирования, используемые в переводе:
    - Открывающие: <b>, <i>, <u>, <li>, <p>, <span> и т.д.
    - Закрывающие: </b>, </i>, </u>, </li>, </p>, </span> и т.д.
    - Самозакрывающиеся: <br/>, <hr/> и т.д.
    - Числовые теги Trados/SDLXLIFF: <92>, </92> и т.д.

    Аргументы:
        text: исходный текст с HTML-тегами

    Возвращает:
        список строк тегов в порядке появления: ['<li>', '</li>', '<b>', '</b>', ...]
    """
    import re
    # Сопоставляем HTML/XML-теги: <tagname>, </tagname>, <tagname/>, <tagname attr="value">
    # А также числовые теги Trados/SDLXLIFF: <N>, </N>
    pattern = r'(</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^>]*)?>|</?\d+>)'
    return re.findall(pattern, text)


def compact_tags(text: str, tag_map: dict = None) -> str:
    """
    Заменяет громоздкие XML/HTML-теги короткими нумерованными плейсхолдерами
    для отображения.

    Простые теги форматирования (<b>, <i>, <u>, <sub>, <sup> и их закрывающие)
    остаются как есть. Сокращаются только громоздкие теги (с атрибутами или
    длинными именами вроде <bmk id="0" name="_Toc219208699" transform="open">).

    Открывающие теги получают {1}, закрывающие {/1}, самозакрывающиеся {1/}.
    Каждое уникальное имя тега получает стабильный номер (первое вхождение = 1
    и т.д.).

    Аргументы:
        text: текст с громоздкими тегами.
        tag_map: необязательный словарь для заполнения соответствиями
                 плейсхолдер -> полный тег (для обратного преобразования).
                 Если None, карта не строится.

    Возвращает:
        текст с громоздкими тегами, заменёнными компактными плейсхолдерами.

    Примечание: tag_map — сеансовый контракт между отображением и обратным
    чтением (expand_compact_tags); он должен жить столько же, сколько
    отображаемый текст, иначе прочитанный текст останется с {N}.
    """
    import re

    # Теги, которые не трогаем (простое форматирование — уже короткие)
    _PASSTHROUGH = {'b', 'i', 'u', 'sub', 'sup', 'em', 'strong', 's'}

    tag_pattern = re.compile(
        r'<(/?)([a-zA-Z][a-zA-Z0-9-]*)(\s[^>]*)?(/?)\s*>'  # именованные теги с необязательными атрибутами
        r'|'
        r'</(\d+)>'          # числовой закрывающий Trados: </92>
        r'|'
        r'<(\d+)>'           # числовой открывающий Trados: <92>
    )

    tag_name_to_num = {}
    counter = [0]

    def _get_num(name: str) -> int:
        if name not in tag_name_to_num:
            counter[0] += 1
            tag_name_to_num[name] = counter[0]
        return tag_name_to_num[name]

    def _replace(m):
        full_tag = m.group(0)

        # Числовой закрывающий Trados </N>
        if m.group(5) is not None:
            n = _get_num(f"trados_{m.group(5)}")
            placeholder = f"{{/{n}}}"
            if tag_map is not None:
                tag_map[placeholder] = full_tag
            return placeholder
        # Числовой открывающий Trados <N>
        if m.group(6) is not None:
            n = _get_num(f"trados_{m.group(6)}")
            placeholder = f"{{{n}}}"
            if tag_map is not None:
                tag_map[placeholder] = full_tag
            return placeholder

        # Именованный тег
        slash = m.group(1)      # '/' для закрывающего, '' для открывающего
        name = m.group(2)       # имя тега
        attrs = m.group(3)      # атрибуты (может быть None)
        self_close = m.group(4) # '/' для самозакрывающегося

        # Простые теги форматирования без атрибутов пропускаем как есть
        if name.lower() in _PASSTHROUGH and not attrs:
            return full_tag

        # Сокращаем только громоздкие теги (с атрибутами или именем > 3 символов)
        if not attrs and len(name) <= 3:
            return full_tag

        n = _get_num(name.lower())
        if slash:
            placeholder = f"{{/{n}}}"
        elif self_close:
            placeholder = f"{{{n}/}}"
        else:
            placeholder = f"{{{n}}}"

        if tag_map is not None:
            tag_map[placeholder] = full_tag
        return placeholder

    return tag_pattern.sub(_replace, text)


# Word Joiner (U+2060): невидимый символ нулевой ширины, запрещающий перенос
# строки по обе стороны от себя. Используется, чтобы сетка с переносом по
# словам не могла разорвать тег посередине (см. protect_tags_from_linebreak).
# Снимается при обратном чтении reverse_invisible_replacements, поэтому в
# сохранённый текст сегмента не попадает.
WORD_JOINER = chr(0x2060)  # U+2060 WORD JOINER (нулевая ширина, без переноса)

# Распознанные формы тегов, содержащие "/" и потому уязвимые для переноса
# после слэша. Алгоритм разбиения строк Unicode (UAX #14) считает SOLIDUS
# классом SY — «возможность разрыва после», поэтому "</i>" может перенестись
# как "</" + "i>" даже в режиме переноса по границам слов. Защищать нужно
# только теги, реально содержащие слэш: закрывающие и самозакрывающиеся
# HTML/XML-теги, числовые закрывающие Trados и компактные {/n}/{n/}.
_TAG_LINEBREAK_PROTECT_RE = re.compile(
    r'</?[a-zA-Z][a-zA-Z0-9-]*/?(?:\s[^>]*)?>'  # <i>, </i>, <t2/>, <tag attr="x">
    r'|</?\d+>'                                  # числовые Trados: <1>, </1>
    r'|\{/?\d+/?\}'                              # компактные плейсхолдеры: {/1}, {1/}
)


def protect_tags_from_linebreak(text: str) -> str:
    """Вставляет WORD JOINER после каждого "/" внутри распознанного тега,
    чтобы перенос по словам в сетке не разрывал тег на две строки
    (например, "</i>" -> "</" + "i>"). Только для отображения:
    reverse_invisible_replacements снимает присоединённые символы перед
    любой записью текста, поэтому текст модели не затрагивается.
    Не делает ничего, если в тексте нет слэша."""
    if not text or '/' not in text:
        return text
    return _TAG_LINEBREAK_PROTECT_RE.sub(
        lambda m: m.group(0).replace('/', '/' + WORD_JOINER), text)


def expand_compact_tags(text: str, tag_map: dict) -> str:
    """
    Обратная операция к compact_tags() — заменяет нумерованные плейсхолдеры
    обратно на полные теги.

    Аргументы:
        text: текст с компактными плейсхолдерами вроде {1}, {/1}.
        tag_map: словарь соответствий плейсхолдер -> полный тег.

    Возвращает:
        текст с восстановленными полными тегами.
    """
    if not tag_map:
        return text
    # Сортируем по убыванию длины плейсхолдера, чтобы избежать частичных замен
    for placeholder, full_tag in sorted(tag_map.items(), key=lambda x: -len(x[0])):
        text = text.replace(placeholder, full_tag)
    return text


# Комбинированный шаблон тегов memoQ, HTML и числовых Trados/SDLXLIFF
# memoQ: [N}, {N], [N]
# HTML: <tag>, </tag>, <tag/>, <tag attr="value"> — включая теги с дефисами: li-o, li-b
# Trados/SDLXLIFF: <N>, </N> (числовые теги парных элементов SDLXLIFF)
_ALL_TAGS_PATTERN = r'(\[\d+\}|\{\d+\]|\[\d+\]|</?[a-zA-Z][a-zA-Z0-9-]*(?:\s+[^>]*)?>|</?\d+>)'


def extract_all_tags(text: str) -> list:
    """
    Извлекает все теги (memoQ, HTML и числовые Trados) из текста
    в порядке появления.

    Аргументы:
        text: исходный текст с тегами

    Возвращает:
        список всех строк тегов в порядке появления
    """
    import re
    return re.findall(_ALL_TAGS_PATTERN, text or '')


# AutoTagger использует собственный, более полный шаблон, чем extract_all_tags:
# он распознаёт также самозакрывающиеся формы (нумерованные <2/> и HTML <x1/>),
# которые применяют SDLXLIFF/Trados для автономных тегов. Держится отдельно,
# чтобы поведение extract_all_tags (используется другими возможностями)
# не изменилось.
# Часть имени допускает символы XML QName — буквы, цифры, '.', '_', '-' и ':'.
# Двоеточие критично: двуязычные файлы memoQ несут теги С ПРОСТРАНСТВОМ ИМЁН,
# например <mq:ch val="→" />, и класс имени [a-zA-Z0-9-] останавливался на
# двоеточии, поэтому такие теги вообще не распознавались как теги. AutoTagger
# сообщал «в исходном сегменте нет внутренних тегов» на большинстве сегментов
# реального файла memoQ и ничего не делал.
_AUTOTAG_TAG_PATTERN = r'(\[\d+\}|\{\d+\]|\[\d+\]|</?\d+/?>|</?[a-zA-Z][a-zA-Z0-9._:-]*(?:\s+[^>]*)?/?>)'


def autotag_extract_tags(text: str) -> list:
    """Извлекает все внутренние теги (включая самозакрывающиеся) для AutoTagger,
    в порядке появления."""
    import re
    return re.findall(_AUTOTAG_TAG_PATTERN, text or '')


def strip_all_tags(text: str) -> str:
    """Удаляет из текста все внутренние теги (включая самозакрывающиеся),
    оставляя только слова.

    Используется AutoTagger для получения текста без тегов и для проверки,
    что ИИ только переставил теги и не менял формулировки."""
    import re
    return re.sub(_AUTOTAG_TAG_PATTERN, '', text or '')


def _normalize_ws_for_compare(text: str) -> str:
    """Схлопывает последовательности пробелов, чтобы diff «только тегов»
    игнорировал изменения пробелов."""
    import re
    return re.sub(r'\s+', ' ', (text or '')).strip()


# Косметические варианты символов, которые LLM регулярно подменяет
# (типографские <-> прямые кавычки, NBSP <-> пробел, короткое/длинное тире,
# многоточие). Проверка «слова не изменены» в AutoTagger сворачивает их,
# чтобы размещение только тегов не отклонялось лишь из-за того, что модель
# «нормализовала» кавычку — реальный текст всё равно сохраняется на запись
# через _reinsert_tags_into_target().
_WORD_COMPARE_FOLD = {
    '“': '"', '”': '"', '„': '"', '‟': '"', '«': '"', '»': '"', '″': '"',
    '‘': "'", '’': "'", '‚': "'", '‛': "'", '′': "'", '`': "'",
    ' ': ' ', ' ': ' ', ' ': ' ', '​': '',
    '–': '-', '—': '-', '‑': '-', '…': '...',
}


def _normalize_for_word_compare(text: str) -> str:
    """Свёрнутая по пробелам/пунктуации форма для проверки «слова не изменены»."""
    import re
    import unicodedata
    t = unicodedata.normalize('NFKC', text or '')
    for a, b in _WORD_COMPARE_FOLD.items():
        t = t.replace(a, b)
    return re.sub(r'\s+', ' ', t).strip()


def _reinsert_tags_into_target(candidate: str, clean_target: str):
    """Вставляет теги из ``candidate`` обратно в ТОЧНЫЙ ``clean_target``.

    ИИ может вернуть правильные позиции тегов, но в косметически отличающейся
    копии перевода (например, с прямыми кавычками). Функция проецирует позицию
    каждого тега на исходный текст пользователя, так что записанный результат
    сохраняет точные формулировки/пунктуацию пользователя. Возвращает
    восстановленную строку или None, если текст кандидата без тегов не
    выравнивается с clean_target."""
    import re
    import difflib
    tag_re = re.compile(_AUTOTAG_TAG_PATTERN)
    pieces = []          # (смещение_в_кандидате_без_тегов, тег)
    cand_stripped_parts = []
    idx = 0
    pos = 0
    for m in tag_re.finditer(candidate):
        chunk = candidate[idx:m.start()]
        cand_stripped_parts.append(chunk)
        pos += len(chunk)
        pieces.append((pos, m.group(0)))
        idx = m.end()
    cand_stripped_parts.append(candidate[idx:])
    cand_stripped = ''.join(cand_stripped_parts)

    sm = difflib.SequenceMatcher(None, cand_stripped, clean_target, autojunk=False)
    opcodes = sm.get_opcodes()

    def map_offset(o):
        # Опкоды непрерывно покрывают [0, len(cand_stripped)], поэтому любое
        # смещение покрыто. Равные участки отображаются 1:1; для изменённых
        # участков (например, заменённой кавычки) граничное смещение
        # отображается на соответствующую чистую границу.
        for op, a1, a2, b1, b2 in opcodes:
            if a1 <= o <= a2:
                if op == 'equal':
                    return b1 + (o - a1)
                if o >= a2:
                    return b2
                return b1
        return len(clean_target)

    from collections import defaultdict
    by_off = defaultdict(list)
    for off, tag in pieces:
        by_off[map_offset(off)].append(tag)

    out = []
    for i in range(len(clean_target) + 1):
        if i in by_off:
            out.extend(by_off[i])
        if i < len(clean_target):
            out.append(clean_target[i])
    return ''.join(out)


def _classify_tag(tag: str):
    """Классифицирует тег как ('open'|'close'|'self', ключ) для проверки вложенности."""
    import re
    # Парные теги memoQ ключуются КОНСТАНТОЙ, а не своим номером: memoQ
    # нумерует теги последовательно по всему сегменту, поэтому открывающий и
    # закрывающий теги пары обычно имеют РАЗНЫЕ номера ("[1}De uitvoer{2]").
    # Ключ по номеру делал каждую пару memoQ «несовпадающей», и AutoTagger
    # отклонял размещение с «unpaired or out of order». Константный ключ
    # корректно парует и соглашение с одинаковыми номерами ("[1}…{1]"),
    # так что подходит в обоих случаях.
    for pat, kind, key in (
        (r'\[\d+\}', 'open', 'mq'), (r'\{\d+\]', 'close', 'mq'),
    ):
        if re.fullmatch(pat, tag):
            return (kind, key)
    for pat, kind, pre in (
        (r'\[(\d+)\]', 'self', 'mq'),
        (r'<(\d+)/>', 'self', 'n'), (r'<(\d+)>', 'open', 'n'), (r'</(\d+)>', 'close', 'n'),
    ):
        m = re.fullmatch(pat, tag)
        if m:
            return (kind, pre + m.group(1))
    m = re.fullmatch(r'<([a-zA-Z][a-zA-Z0-9._:-]*)(?:\s+[^>]*)?/>', tag)
    if m:
        return ('self', 'h' + m.group(1).lower())
    # Закрывающие теги могут нести АТРИБУТЫ. Содержимое DOCX, извлечённое
    # через Okapi, использует формы вида <rpr id="4">…</rpr id="4" transform="close">
    # и <bmk id="3" …>…</bmk id="3" transform="close">. Старый шаблон допускал
    # только </name>, поэтому такие закрывающие теги проваливались в запасную
    # ветку ('self', tag), их открывающий тег не извлекался из стека, и
    # валидация отклоняла совершенно корректное размещение с сообщением
    # «unclosed tag(s): rpr» — проявлялось как «AutoTagger ничего не делает»
    # (Workbench issue #244).
    m = re.fullmatch(r'</([a-zA-Z][a-zA-Z0-9._:-]*)(?:\s+[^>]*)?>', tag)
    if m:
        return ('close', 'h' + m.group(1).lower())
    m = re.fullmatch(r'<([a-zA-Z][a-zA-Z0-9._:-]*)(?:\s+[^>]*)?>', tag)
    if m:
        return ('open', 'h' + m.group(1).lower())
    return ('self', tag)


def _tags_well_formed(text: str) -> tuple:
    """True, если парные теги открываются до закрытия и вкладываются корректно."""
    stack = []
    for tag in autotag_extract_tags(text):
        kind, key = _classify_tag(tag)
        if kind == 'open':
            stack.append(key)
        elif kind == 'close':
            if not stack or stack[-1] != key:
                return False, f"tag {tag} is unpaired or out of order"
            stack.pop()
    if stack:
        return False, "unclosed tag(s): " + ", ".join(stack)
    return True, ""


def validate_tag_transfer(source_text: str, candidate_target: str, clean_target: str) -> tuple:
    """Валидация результата AutoTagger. Возвращает (ok: bool, причина: str).

    Проверки: (1) мультимножество тегов совпадает с исходным, (2) слова не
    изменены относительно перевода без тегов, (3) теги правильно вложены."""
    from collections import Counter
    src_tags = Counter(autotag_extract_tags(source_text))
    cand_tags = Counter(autotag_extract_tags(candidate_target))
    if src_tags != cand_tags:
        missing = src_tags - cand_tags
        extra = cand_tags - src_tags
        parts = []
        if missing:
            parts.append("missing " + ", ".join(f"{t}×{n}" for t, n in missing.items()))
        if extra:
            parts.append("unexpected " + ", ".join(f"{t}×{n}" for t, n in extra.items()))
        return False, "tag set does not match source (" + "; ".join(parts) + ")"
    if _normalize_for_word_compare(strip_all_tags(candidate_target)) != _normalize_for_word_compare(clean_target):
        return False, "the target wording changed (AutoTagger must only move tags)"
    ok, why = _tags_well_formed(candidate_target)
    if not ok:
        return False, why
    return True, ""


def place_tags_via_llm(client, prompt_manager, source_text: str, clean_target: str,
                       source_lang: str, target_lang: str, max_attempts: int = 2) -> tuple:
    """Просит LLM расставить внутренние теги из исходника по переводу без тегов.

    Возвращает (новый_перевод | None, причина). До max_attempts повторов;
    возвращает только результат, прошедший validate_tag_transfer, поэтому
    «битые» теги никогда не попадут в сегмент."""
    tags = autotag_extract_tags(source_text)
    if not tags:
        return clean_target, ""  # расставлять нечего
    template = prompt_manager.get_autotagger_template()
    prompt = (template
              .replace("{{SOURCE_TEXT}}", source_text)
              .replace("{{TARGET_TEXT}}", clean_target)
              .replace("{{TAG_LIST}}", " ".join(tags)))
    from modules import usage_log as _usage_log
    last_reason = "no result"
    for _ in range(max(1, max_attempts)):
        try:
            # Относим эти вызовы к задаче "AutoTagger" в журнале использования
            # (покрывает и одиночную команду, и пакетный воркер).
            with _usage_log.UsageContext(task="AutoTagger"):
                result = client.translate(
                    text=clean_target,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    custom_prompt=prompt,
                )
        except Exception as e:
            last_reason = f"LLM error: {e}"
            continue
        candidate = (result or "").strip()
        ok, reason = validate_tag_transfer(source_text, candidate, clean_target)
        if ok:
            # Предпочитаем вставить теги в ТОЧНЫЙ перевод пользователя, чтобы
            # косметические отличия, внесённые моделью (например, прямые
            # кавычки), не попали в сохраняемый сегмент. Запасной вариант —
            # сам candidate, если восстановление не выравнивается/не валидно.
            recon = _reinsert_tags_into_target(candidate, clean_target)
            if recon is not None:
                rok, _ = validate_tag_transfer(source_text, recon, clean_target)
                if rok:
                    return recon, ""
            return candidate, ""
        last_reason = reason
    return None, last_reason


def count_pipe_symbols(text: str) -> int:
    """Считает количество символов-разделителей (pipe) CafeTran в тексте."""
    return text.count('|')


def get_next_pipe_count_needed(source_text: str, target_text: str) -> int:
    """
    Сколько ещё символов-разделителей (pipe) нужно в переводе,
    чтобы сравняться с исходником.

    Аргументы:
        source_text: исходный сегмент с символами pipe
        target_text: текущий текст перевода

    Возвращает:
        число недостающих символов pipe (0, если в переводе их достаточно
        или больше)
    """
    source_pipes = count_pipe_symbols(source_text)
    target_pipes = count_pipe_symbols(target_text)
    return max(0, source_pipes - target_pipes)


def get_tag_pair(tag_number: int) -> tuple:
    """
    Возвращает открывающий и закрывающий теги для заданного номера.

    Аргументы:
        tag_number: номер тега (1, 2, 3, ...)

    Возвращает:
        кортеж (открывающий_тег, закрывающий_тег), например ('[1}', '{1]')
    """
    return (f'[{tag_number}}}', f'{{{tag_number}]')


def find_next_unused_tag(source_text: str, target_text: str) -> str:
    """
    Находит следующий тег из исходника, ещё не использованный в переводе.

    Поддерживает теги memoQ ([1}, {1], [1]) и HTML (<li>, </li>, <b> и т.д.)

    Аргументы:
        source_text: исходный сегмент с тегами
        target_text: текущий текст перевода (часть тегов может уже стоять)

    Возвращает:
        следующий тег для вставки или пустую строку, если все теги уже
        использованы
    """
    # Комбинированное извлечение для memoQ и HTML
    source_tags = extract_all_tags(source_text)
    target_tags = extract_all_tags(target_text)

    # Считаем вхождения тегов в перевод
    from collections import Counter
    target_tag_counts = Counter(target_tags)
    source_tag_counts = Counter(source_tags)

    # Ищем первый тег, которого в переводе меньше, чем в исходнике
    for tag in source_tags:
        source_count = source_tag_counts[tag]
        target_count = target_tag_counts.get(tag, 0)
        if target_count < source_count:
            return tag

    return ""  # Все теги уже в переводе


def get_wrapping_tag_pair(source_text: str, target_text: str) -> tuple:
    """
    Возвращает следующую доступную пару тегов memoQ для обёртывания выделения.

    Ищет первый номер тега из исходника, для которого в переводе отсутствует
    открывающий или закрывающий тег.

    Аргументы:
        source_text: исходный сегмент с тегами
        target_text: текущий текст перевода

    Возвращает:
        кортеж (открывающий_тег, закрывающий_тег) или (None, None), если
        доступных пар нет
    """
    import re

    # Извлекаем все номера тегов из исходника
    source_tags = extract_memoq_tags(source_text)
    if not source_tags:
        return (None, None)

    # Уникальные номера тегов в порядке появления
    tag_numbers = []
    for tag in source_tags:
        match = re.search(r'\d+', tag)
        if match:
            num = int(match.group())
            if num not in tag_numbers:
                tag_numbers.append(num)

    target_tags = extract_memoq_tags(target_text)

    # Ищем первый номер, пара которого не полна в переводе
    for num in tag_numbers:
        opening, closing = get_tag_pair(num)
        if opening not in target_tags or closing not in target_tags:
            return (opening, closing)

    return (None, None)


def get_html_wrapping_tag_pair(source_text: str, target_text: str) -> tuple:
    """
    Возвращает следующую доступную пару HTML-тегов для обёртывания выделения.

    Ищет парные HTML-теги (открывающий + закрывающий) из исходника, пара
    которых ещё не полна в переводе. Поддерживает распространённые теги
    форматирования: b, i, u, em, strong, span, li, p, a, sub, sup и т.д.
    А также числовые теги Trados/SDLXLIFF вида <92>...</92>.

    Аргументы:
        source_text: исходный сегмент с тегами
        target_text: текущий текст перевода

    Возвращает:
        кортеж (открывающий_тег, закрывающий_тег) или (None, None), если
        доступных пар нет
    """
    import re

    # Ищем все HTML-теги в исходнике
    # Сопоставляем: <tag>, <tag attr="...">, </tag> и числовые теги Trados <N>, </N>
    tag_pattern = r'<(/?)([a-zA-Z][a-zA-Z0-9-]*|\d+)(?:\s+[^>]*)?>'
    source_matches = re.findall(tag_pattern, source_text)
    target_matches = re.findall(tag_pattern, target_text)

    if not source_matches:
        return (None, None)

    # Списки открывающих и закрывающих тегов в исходнике
    source_opening = []  # [(полный_тег, имя_тега), ...]
    source_closing = []

    for match in re.finditer(tag_pattern, source_text):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()
        full_tag = match.group(0)

        if is_closing:
            source_closing.append((full_tag, tag_name))
        else:
            source_opening.append((full_tag, tag_name))

    # Множества имён тегов, уже присутствующих в переводе
    target_opening_names = set()
    target_closing_names = set()

    for is_closing, tag_name in target_matches:
        if is_closing == '/':
            target_closing_names.add(tag_name.lower())
        else:
            target_opening_names.add(tag_name.lower())

    # Ищем первую пару, оба тега которой есть в исходнике, но хотя бы один
    # отсутствует в переводе
    seen_tags = set()
    for full_tag, tag_name in source_opening:
        if tag_name in seen_tags:
            continue
        seen_tags.add(tag_name)

        # Есть ли в исходнике парный закрывающий тег
        has_closing = any(name == tag_name for _, name in source_closing)
        if not has_closing:
            continue

        # Пара неполна в переводе?
        opening_in_target = tag_name in target_opening_names
        closing_in_target = tag_name in target_closing_names

        if not opening_in_target or not closing_in_target:
            # Берём фактические открывающий и закрывающий теги из исходника
            opening_tag = full_tag
            closing_tag = f"</{tag_name}>"
            return (opening_tag, closing_tag)

    return (None, None)


# ============================================================================
# Хелперы класса SupervertalerQt, перенесённые как module-level функции
# (Batch #2). В классе оставлены тонкие делегаты; синтаксис тегов здесь
# совпадает с монолитным блоком выше (_INLINE_TAG_RE — та же регулярка).
# ============================================================================

_INLINE_TAG_RE = re.compile(r'</?[A-Za-z][^<>]*?/?>')


def _strip_inline_tags(text):
    """Возвращает ``text`` без инлайн-тегов форматирования CAT.
    
            Экспортируемый DOCX рендерит эти теги как реальное форматирование
            runs (жирный, курсив, …), поэтому *видимый* текст абзаца не несёт
            ни одного из них. Чтобы найти текст сегмента в абзаце, сравнивать
            нужно с той же формой без тегов."""
    if not text:
        return ''
    return _INLINE_TAG_RE.sub('', text)


def _raw_to_visible_offset(raw_text, raw_off):
    """Преобразует символьное смещение в тексте с тегами в соответствующее
            смещение в его форме без тегов (видимой), чтобы смещения якорей
            комментариев, сохранённые для «сырого» перевода, корректно
            попадали и после удаления тегов."""
    if raw_off <= 0 or not raw_text:
        return 0
    visible = 0
    i = 0
    limit = min(raw_off, len(raw_text))
    while i < limit:
        m = _INLINE_TAG_RE.match(raw_text, i)
        if m and m.end() <= len(raw_text):
            i = m.end()              # skip the whole tag; no visible advance
        else:
            i += 1
            visible += 1
    return visible


def _wysiwyg_runs_to_tagged_text(runs):
    """Сериализует runs ``[(текст, активные_имена_тегов)`` обратно в наш
            синтаксис инлайн-тегов, открывая/закрывая теги в стабильном
            порядке, чтобы вывод совершал обратный круг (например,
            ``<b><i>x</i></b>``)."""
    parts = []
    open_tags = []  # currently-open tag names, in the order opened
    for text, active in runs:
        # Longest common prefix of what's open vs. what this run wants.
        common = 0
        while (common < len(open_tags) and common < len(active)
               and open_tags[common] == active[common]):
            common += 1
        # Close everything opened past the common prefix (reverse order).
        for t in reversed(open_tags[common:]):
            parts.append(f'</{t}>')
        del open_tags[common:]
        # Open the tags this run needs that aren't open yet.
        for t in active[common:]:
            parts.append(f'<{t}>')
            open_tags.append(t)
        parts.append(text)
    for t in reversed(open_tags):
        parts.append(f'</{t}>')
    return ''.join(parts)
