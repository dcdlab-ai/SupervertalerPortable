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
