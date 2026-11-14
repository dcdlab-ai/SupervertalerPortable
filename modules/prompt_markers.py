"""Prompt marker constants shared by prompt building and echo detection.

Batch C1 (по рекон C1.0, отчёт docs/refactoring/reports/BATCH_C1.0_REPORT.md):
блок окружающих сегментов в translate_current_segment собирается из этих
констант, чтобы защита от эха физически не могла разойтись с шаблоном промта
(строки байт-в-байт те же, что были литералами).

Модуль без зависимостей (только re) — импортируется и из llm_clients, и из
монолита, и из modules.tagged_text.writer.
"""

import re

# Литералы блока окружающих сегментов (до C1 — литералы в Supervertaler.py
# :48519/:48525–48526; байт-в-байт те же строки).
SURROUNDING_CONTEXT_HEADER = "**SURROUNDING SEGMENTS FOR CONTEXT:**"
SURROUNDING_CONTEXT_EXPLAINER = "(The segment marked with >>> <<< is the one to translate)"
TRANSLATE_THIS_MARK = "[TRANSLATE THIS]"

# Сигналы эха (C1, решения координатора Q1): любой из них в ответе модели,
# КОГДА соответствующего маркера нет в исходном сегменте. nailong-9b переводит
# каркас промта на целевой язык, поэтому надёжны структурные сигналы (а) и (б);
# литерал (в) ловит модели, не переведшие каркас.
_ECHO_PAIR_MARKERS = (">>>", "<<<")
_ECHO_NUMBERED_RE = re.compile(r">>>\s*\d+\s*\.")
_ECHO_HEADER_LITERAL = "SURROUNDING SEGMENTS FOR CONTEXT"


def _contains_pair(text: str) -> bool:
    """Парные '>>>' и '<<<' в одном тексте (условие (а))."""
    return _ECHO_PAIR_MARKERS[0] in text and _ECHO_PAIR_MARKERS[1] in text


def looks_like_prompt_echo(response, source_text) -> bool:
    """True, если ответ модели несёт маркеры каркаса промта, которых нет в source.

    Сигналы (срабатывает любой, при условии отсутствия маркера в source_text):
    (а) парные '>>>' и '<<<';
    (б) нумерованный маркированный сегмент '>>> <число>.';
    (в) литерал 'SURROUNDING SEGMENTS FOR CONTEXT' (переведённое эхо ловится
        пп. (а)/(б), это осознанное ограничение).

    Голые нумерованные строки ('27.', '28.') эхом НЕ считаются — markdown-списки
    легитимны (контракт координатора, тест 5). Вырезать перевод из мусора
    функция не пытается.
    """
    if not response:
        return False
    source_text = source_text or ""
    if _contains_pair(response) and not _contains_pair(source_text):
        return True
    if _ECHO_NUMBERED_RE.search(response) and not _ECHO_NUMBERED_RE.search(source_text):
        return True
    if _ECHO_HEADER_LITERAL in response and _ECHO_HEADER_LITERAL not in source_text:
        return True
    return False


# C2 (перелив контекста, живой случай nailong-9b на сегменте #31): пороги
# детектора. Подобраны по таблице пар в
# docs/refactoring/audits/c2_context_overflow_tests.py; обоснование — §1
# отчёта docs/refactoring/reports/BATCH_C2_REPORT.md.
#
# Порог «лишних абзацев»: одноабзацный source — перелив от +3 абзацев
# (±1 — допуск на легитимное разбиение/склейку абзаца, +2 — запас на
# граничные случаи многострочных заголовков); многоабзацный source
# (содержит '\n\n') — порог от числа абзацев source (координатор, задача 1г).
_OVERFLOW_EXCESS_MIN = 3
_OVERFLOW_SHORT_SOURCE_CHARS = 60
_OVERFLOW_LENGTH_RATIO = 10


def _overflow_paras(text):
    """Непустые строки текста после strip (считаются абзацами)."""
    text = (text or "").strip()
    if not text:
        return []
    return [line for line in text.split("\n") if line.strip()]


def count_paragraphs(text) -> int:
    """Число непустых абзацев (нужен для сообщений лога C2)."""
    return len(_overflow_paras(text))


def looks_like_context_overflow(response, source_text) -> bool:
    """True, если ответ выглядит как перевод соседних сегментов вместе с текущим.

    Чистая функция (без Qt и побочных эффектов, координатор задача 1).
    Сигналы (срабатывает любой; пустой/пробельный ответ — False, пустой
    source — False, его в вызывающем коде не бывает):

    (1) абзацы: у ответа заметно больше непустых строк, чем у source
        (после strip):
          - одноабзацный source: избыток >= 3 абзацев (+1 — легитимный
            допуск, +2 — запас, координатор задача 1б);
          - многоабзацный source ('\n\n' в source): избыток >= max(3, число
            абзацев source) (координатор, задача 1г);
          - ответ с МЕНЬШИМ числом абзацев никогда не перелив (потерю
            структуры ловят другие проверки).
    (2) длина (только В СОЧЕТАНИИ с превышением абзацев, задача 1в):
        source <= 60 знаков и ответ >= 10 x длины source при абзацев у
        ответа строго больше. Само по себе (одна строка любой длины) — не
        перелив: короткие заголовки легитимно дают длинный перевод.
    """
    source_text = source_text or ""
    if not response or not response.strip() or not source_text.strip():
        return False
    src_paras = _overflow_paras(source_text)
    resp_paras = _overflow_paras(response)
    if not resp_paras or not src_paras:
        return False
    src_n = len(src_paras)
    resp_n = len(resp_paras)
    excess = resp_n - src_n
    if excess <= 0:
        return False
    if "\n\n" in source_text.strip():
        if excess >= max(_OVERFLOW_EXCESS_MIN, src_n):
            return True
    elif excess >= _OVERFLOW_EXCESS_MIN:
        return True
    if (len(source_text) <= _OVERFLOW_SHORT_SOURCE_CHARS
            and len(response) >= _OVERFLOW_LENGTH_RATIO * len(source_text)
            and resp_n > src_n):
        return True
    return False


# C3 (остатки каркаса промта в переводе; живые случаи nailong-9b — эталоны
# F1–F4 промпта BATCH C3): модель ПЕРЕВОДИТ метки промта на язык перевода,
# поэтому ни C1 (литеральные маркеры '>>>'/'<<<'/'>>> N.'), ни C2 (избыток
# абзацев) их не видят. strip_prompt_leaks срезает три формы по СОЧЕТАНИЮ
# структурных признаков (координатор, задача 1) и возвращает срезанные
# фрагменты для лога. Пороги подобраны по таблице пар в
# docs/refactoring/audits/c3_prompt_leaks_tests.py; FP-анализ — §1 отчёта
# docs/refactoring/reports/BATCH_C3_REPORT.md.
#
# Пороги правила (б) — хвостовая метка в квадратных скобках:
_LEAK_LABEL_MAX_CHARS = 30
_LEAK_LABEL_MIN_WORD = 3   # FP-заслон: «[ОК]»/«[OK]» — не метка (см. §1)
_LEAK_LABEL_MAX_WORDS = 3
# Пороги правила (в) — хвостовая строка-инструкция:
_LEAK_LINE_HEADER_MAX = 40     # «короткий заголовок до ~40 знаков»
_LEAK_LINE_PAREN_MIN = 10      # «скобки с текстом от 10 знаков»
_LEAK_LINE_PAREN_MAX = 200     # верхний заслон от патологических строк

# (а) префикс номера в ответе: «8. АНГЛИЧАНЕ». (?!\d) — защита от десятичных
# дробей («8.5 см» для сегмента №8 не срезается). \s? — один пробел после
# точки (без него «8.АНГЛИЧАНЕ» оставил бы ведущий пробел... с \s? срезается
# ровно число+точка+один пробел).
_LEAK_NUMBER_PREFIX_RE = re.compile(r'^\s*(\d+)\s*\.(?!\d)\s?')
# Источник, сам начинающийся с числа («8. First item», «3) Chapter», —
# правило (а) выключается целиком: и совпадающий, и другой номер.
_LEAK_SOURCE_NUMBER_RE = re.compile(r'^\s*\d+\s*[.)]')
# (б) метка в квадратных скобках в самом конце (вложенные скобки не матчатся:
# содержимое не может содержать '['/']').
_LEAK_BRACKET_RE = re.compile(r'\s*\[([^\[\]]*)\]\s*$')
# (в) отдельная строка: «**ВАШ ПЕРЕВОД (укажите ТОЛЬКО переведённый текст,
# без нумерации или меток):**», «**YOUR TRANSLATION (provide ONLY the
# translated text, no numbering or labels):**». Заголовок без '*' и без
# переносов; содержимое скобок без скобок/переносов; ** и двоеточие
# необязательны (координатор, задача 1в).
_LEAK_INSTRUCTION_LINE_RE = re.compile(
    r'^\*{0,2}\s*([^*\n]{1,%d}?)\s*\(([^()\n]{%d,%d})\)\s*:?\s*\*{0,2}$'
    % (_LEAK_LINE_HEADER_MAX, _LEAK_LINE_PAREN_MIN, _LEAK_LINE_PAREN_MAX))


def _is_leak_label(inner: str) -> bool:
    """Содержимое «[...]» похоже на метку перевода ([ПЕРЕВЕСТИ ЭТО],
    [TRANSLATE THIS]): 1–3 слова, <=30 знаков, только буквы верхнего
    регистра, пробелы и дефисы (координатор, задача 1б). Цифры, строчные
    буквы, точки — не метка («[sic]», «[2024]», «[см. приложение]»)."""
    if not inner or len(inner) > _LEAK_LABEL_MAX_CHARS:
        return False
    words = inner.split()
    if not 1 <= len(words) <= _LEAK_LABEL_MAX_WORDS:
        return False
    for word in words:
        for part in word.split('-'):
            if len(part) < _LEAK_LABEL_MIN_WORD:
                return False
            if not all(ch.isalpha() and ch.isupper() for ch in part):
                return False
    return True


def strip_prompt_leaks(response, source_text, segment_number):
    """Срезает остатки каркаса промта из ответа модели (Batch C3).

    Чистая функция (без Qt и побочных эффектов, координатор задача 1):
    возвращает (text, removed) — срезанный текст и список срезанных
    фрагментов для лога. Пустой после срезания текст вызывающий код
    трактует как эхо (сценарий C1).

    Правила применяются итеративно в порядке (в) -> (б) -> (а), результат
    strip(). Каждое правило срабатывает ТОЛЬКО по сочетанию признаков,
    чтобы не задевать обычные переводы (координатор, задача 1):

    (в) последняя непустая строка ответа — ЦЕЛИКОМ инструкция-каркас
        «заголовок до ~40 знаков + (скобки с текстом от 10 знаков) +
        необязательное двоеточие + необязательные **» (F1: «**ВАШ ПЕРЕВОД
        (укажите ТОЛЬКО переведённый текст, без нумерации или меток):**»),
        и такой строки нет в source (дословно), и в строке есть признак-
        разделитель (двоеточие или **) — срезается строка;
    (б) ответ оканчивается «[...]», внутри скобок только буквы верхнего
        регистра, пробелы и дефисы (1–3 слова, <=30 знаков: [ПЕРЕВЕСТИ ЭТО],
        [ПЕРЕВЕСТИ], [TRANSLATE THIS]; FP-заслоны: слово >=3 букв, цифры/
        строчные/точки внутри — не метка), и source не оканчивается на ']'
        — метка срезается вместе с пробелами перед ней;
    (а) ответ начинается с «N.» (N == segment_number — номер сегмента в
        блоке контекста, это seg.id, НЕ индекс строки грида — блок
        собирается из seg.id в translate_current_segment), и source сам
        не начинается с числа («8.» / «8)» / другой номер — не трогать,
        F4); десятичная дробь «8.5» не срезается (?!\\d).
    """
    text = response or ''
    removed = []
    source_text = source_text or ''
    if not text.strip():
        return (text.strip(), removed)

    # (в) хвостовая строка-инструкция: последняя непустая строка, ЦЕЛИКОМ
    # совпадающая с каркасом; «не конец абзаца с текстом» = подстрочный
    # хвост «текст (пояснение):» не срезается (анкор ^...$ проверяет всю
    # строку). Строка есть в source дословно — не трогать.
    lines = text.split('\n')
    last = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            last = i
            break
    if last is not None:
        line = lines[last].strip()
        # FP-заслон (координатор: «только по сочетанию признаков»): голая
        # строка «Заголовок (пояснение)» без двоеточия и без ** — легитимный
        # перевод, не каркас. Требуем хотя бы один признак-разделитель:
        # двоеточие (оба эталона F1) или ** (болд).
        if (line not in source_text
                and _LEAK_INSTRUCTION_LINE_RE.match(line)
                and (':' in line or '*' in line)):
            removed.append(line)
            text = '\n'.join(lines[:last])

    # (б) хвостовая метка в квадратных скобках.
    m = _LEAK_BRACKET_RE.search(text)
    if m:
        inner = m.group(1).strip()
        if (not source_text.strip().endswith(']')
                and _is_leak_label(inner)):
            removed.append(m.group(0).strip())
            text = text[:m.start()]

    # (а) префикс номера сегмента.
    if not _LEAK_SOURCE_NUMBER_RE.match(source_text):
        m = _LEAK_NUMBER_PREFIX_RE.match(text)
        if m:
            seg_no = None
            try:
                seg_no = int(segment_number)
            except (TypeError, ValueError):
                seg_no = None
            if seg_no is not None and int(m.group(1)) == seg_no:
                removed.append(text[:m.end()].strip())
                text = text[m.end():]

    return (text.strip(), removed)
