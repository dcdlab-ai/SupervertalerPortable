# modules.workers.tm_search - TMSearchWorker QThread worker, extracted verbatim from Supervertaler.py
# (Batch #4, Step 4 of EXTRACTION_PLAN.md).

from PyQt6.QtCore import QThread, pyqtSignal


class TMSearchWorker(QThread):
    """Фоновый поток для нечёткого поиска по памяти переводов."""

    # Сигнал: segment_id, список словарей совпадений
    results_ready = pyqtSignal(int, list)
    # Signal: segment_id, error description - so a failed search reaches the log
    # instead of looking like a TM with no matches.
    search_failed = pyqtSignal(int, str)

    def __init__(self, db_path: str, source_text: str, segment_id: int,
                 tm_ids: list = None, source_lang: str = None, target_lang: str = None,
                 fuzzy_threshold: float = 0.75, max_matches: int = 10,
                 tm_metadata: dict = None):
        super().__init__()
        self.db_path = db_path
        self.source_text = source_text
        self.segment_id = segment_id
        self.tm_ids = tm_ids
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.fuzzy_threshold = fuzzy_threshold
        self.max_matches = max_matches
        self.tm_metadata = tm_metadata or {}
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        """Выполняет поиск по TM в фоновом потоке с поток-локальным SQLite-соединением."""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")

            from modules.database_manager import DatabaseManager

            # Создаём облегчённый DatabaseManager поверх нашего поток-локального соединения
            db = DatabaseManager.__new__(DatabaseManager)
            db.connection = conn
            db.cursor = conn.cursor()
            db.log = lambda msg: None  # отключаем логирование в потоке воркера
            db.db_path = self.db_path

            if self._cancelled:
                conn.close()
                return

            # Сначала пробуем точное совпадение (быстро, по хешу)
            exact_match = db.get_exact_match(
                source=self.source_text,
                tm_ids=self.tm_ids,
                source_lang=self.source_lang,
                target_lang=self.target_lang
            )

            if exact_match:
                results = [{
                    'source': exact_match['source_text'],
                    'target': exact_match['target_text'],
                    'similarity': 1.0,
                    'match_pct': 100,
                    'tm_name': self.tm_metadata.get(exact_match['tm_id'], {}).get('name', exact_match['tm_id']),
                    'tm_id': exact_match['tm_id'],
                    # v1.10.51: проносим флаг обратного совпадения через воркер,
                    # чтобы _on_tm_search_results мог поместить его в
                    # метаданные TranslationMatch для чтения рендерером.
                    'reverse_match': exact_match.get('reverse_match', False),
                }]
                if not self._cancelled:
                    self.results_ready.emit(self.segment_id, results)
                conn.close()
                return

            if self._cancelled:
                conn.close()
                return

            # Нечёткие совпадения (дорого: SequenceMatcher по множеству кандидатов)
            fuzzy_matches = db.search_fuzzy_matches(
                source=self.source_text,
                tm_ids=self.tm_ids,
                threshold=self.fuzzy_threshold,
                max_results=self.max_matches,
                source_lang=self.source_lang,
                target_lang=self.target_lang
            )

            results = []
            for match in fuzzy_matches:
                results.append({
                    'source': match['source_text'],
                    'target': match['target_text'],
                    'similarity': match.get('similarity', 0.85),
                    'match_pct': match.get('match_pct', 85),
                    'tm_name': self.tm_metadata.get(match['tm_id'], {}).get('name', match['tm_id']),
                    'tm_id': match['tm_id'],
                    'reverse_match': match.get('reverse_match', False),
                })

            if not self._cancelled:
                self.results_ready.emit(self.segment_id, results)

            conn.close()

        except Exception as e:
            try:
                conn.close()
            except:
                pass
            # Never fail silently here. This except used to swallow `e` and emit
            # an empty result, which renders as "no TM matches" - visually
            # identical to a TM that genuinely has nothing to offer. Any fault in
            # the search (a locked database, a malformed FTS index, a bad
            # language value) therefore looked like an empty TM, with nothing in
            # the log to say otherwise.
            import traceback
            print(f"[TM search] FAILED for segment {self.segment_id}: "
                  f"{type(e).__name__}: {e}")
            traceback.print_exc()
            self.search_failed.emit(self.segment_id, f"{type(e).__name__}: {e}")
            if not self._cancelled:
                self.results_ready.emit(self.segment_id, [])
