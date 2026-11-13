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
