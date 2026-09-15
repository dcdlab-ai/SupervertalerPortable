# modules.workers.glossary - GlossaryExtractionWorker QThread worker, extracted verbatim from Supervertaler.py
# (Batch #4, Step 4 of EXTRACTION_PLAN.md).

from PyQt6.QtCore import QThread, pyqtSignal


# ============================================================================
# WORKER ИЗВЛЕЧЕНИЯ AI-ГЛОССАРИЯ
# ============================================================================
class GlossaryExtractionWorker(QThread):
    """Запрос LLM на извлечение глоссария вне потока UI.
    
    Заменяет старый механический TermExtractor (выведен из эксплуатации в v1.10.357):
    отправляет исходный текст проекта в настроенную LLM и возвращает двуязычные
    пары терминов «исходник→перевод». Сигналы: finished_ok(list_of_dicts) или
    failed(message, raw_response)."""

    finished_ok = pyqtSignal(list)
    failed = pyqtSignal(str, str)

    def __init__(self, client, prompt: str):
        super().__init__()
        self.client = client
        self.prompt = prompt

    def run(self):
        try:
            raw = self.client.translate(
                text="",  # не используется: custom_prompt заменяет весь промпт
                custom_prompt=self.prompt,
                skip_cleaning=True,  # ответ — JSON, а не перевод
            )
            pairs = self._parse_pairs(raw)
            if not pairs:
                self.failed.emit("The AI returned no usable term pairs.", raw or "")
                return
            self.finished_ok.emit(pairs)
        except Exception as e:
            self.failed.emit(str(e), "")

    @staticmethod
    def _parse_pairs(raw: str) -> list:
        """Извлекает [{'source':…, 'target':…, 'note':…}] из ответа модели.
        
        Терпит markdown-заборы и прозу вокруг JSON-массива — модели добавляют
        и то и другое, как бы строго промпт это ни запрещал."""
        import json
        import re as _re

        if not raw:
            return []
        text = raw.strip()
        # Strip ```json … ``` fences if present
        fence = _re.search(r'```(?:json)?\s*(.*?)```', text, _re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        # Fall back to the outermost [...] span
        if not text.startswith('['):
            start, end = text.find('['), text.rfind(']')
            if start == -1 or end <= start:
                return []
            text = text[start:end + 1]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        pairs = []
        for item in data:
            if not isinstance(item, dict):
                continue
            source = str(item.get('source', '') or '').strip()
            if not source:
                continue
            pairs.append({
                'source': source,
                'target': str(item.get('target', '') or '').strip(),
                'note': str(item.get('note', '') or '').strip(),
            })
        return pairs
