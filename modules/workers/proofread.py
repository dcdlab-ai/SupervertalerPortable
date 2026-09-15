# modules.workers.proofread - ProofreadWorker QThread worker, extracted verbatim from Supervertaler.py
# (Batch #4, Step 4 of EXTRACTION_PLAN.md).

from PyQt6.QtCore import QThread, pyqtSignal


class ProofreadWorker(QThread):
    """Фоновый поток вычитки переводов."""

    # Signals
    progress_update = pyqtSignal(int, str)  # checked_count, status_message
    stats_update = pyqtSignal(int, int, int)  # checked, issues, ok
    batch_error = pyqtSignal(int, int, str)  # batch_start, batch_end, error_message
    segment_issue = pyqtSignal(int, str, str)  # row_idx, issue_text, model_name
    finished_proofreading = pyqtSignal(int, int, int)  # checked, issues, ok

    def __init__(self, segments_to_check, provider, model, custom_prompt, api_keys, source_lang, target_lang, base_url=None, custom_api_key=None, http_proxy=None):
        super().__init__()
        self.segments_to_check = segments_to_check
        self.provider = provider
        self.model = model
        self.custom_prompt = custom_prompt
        self.api_keys = api_keys
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.base_url = base_url
        self.custom_api_key = custom_api_key
        self.http_proxy = http_proxy
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        """Главный цикл вычитки — выполняется в фоновом потоке."""
        import re

        # Build prompt if not custom
        if not self.custom_prompt:
            lang_specific = ""
            if self.target_lang.lower() in ['dutch', 'nl', 'nl-nl', 'nl-be', 'nederlands']:
                lang_specific = """
5. Dutch Compound Words – Verify correct spelling of compound words (e.g., "persoonsgegevens" NOT "persoongegevens", "bedrijfsnaam" NOT "bedrijfnaam"). Pay special attention to connecting letters like 's', 'e', 'en'.
6. Dutch Spelling – Check for common Dutch spelling errors including de/het articles, dt-errors, and capitalization."""
            elif self.target_lang.lower() in ['german', 'de', 'de-de', 'deutsch']:
                lang_specific = """
5. German Compound Words – Verify correct compound noun formation and capitalization of all nouns.
6. German Cases – Check correct use of cases (Nominativ, Akkusativ, Dativ, Genitiv)."""
            elif self.target_lang.lower() in ['french', 'fr', 'fr-fr', 'français']:
                lang_specific = """
5. French Accents – Verify correct use of accents (é, è, ê, à, ù, ô, etc.).
6. French Agreement – Check gender/number agreement between nouns, adjectives, and articles."""

            self.custom_prompt = f"""You are a translation proofreader. Your task is to analyze translations for errors.

DO NOT translate anything. DO NOT provide corrected translations unless specifically requested.
ONLY identify errors using the exact format specified below.

Task: Proofread this translation from {self.source_lang} to {self.target_lang}.

For each segment, verify:
1. Accuracy – Does the translation correctly convey the source meaning?
2. Completeness – Is anything missing or added?
3. Terminology – Are technical terms translated correctly and consistently?
4. Grammar & Style – Is the text natural and error-free?{lang_specific}

CRITICAL OUTPUT FORMAT (FOLLOW EXACTLY):
- If segment is OK: [SEGMENT XXXX] ✓
- If segment has issues: [SEGMENT XXXX] ⚠
  Issue: <brief description>
  Suggestion: <recommended fix>

OUTPUT ONLY THE SEGMENT MARKERS. DO NOT ADD EXPLANATIONS BEFORE OR AFTER."""

        # Initialize LLM client
        try:
            from modules.llm_clients import LLMClient

            if self.provider == 'openai':
                api_key = self.api_keys.get('openai', '')
            elif self.provider == 'claude':
                api_key = self.api_keys.get('claude', '')
            elif self.provider == 'gemini':
                api_key = self.api_keys.get('gemini', '')
            elif self.provider == 'mistral':
                api_key = self.api_keys.get('mistral', '')
            elif self.provider == 'deepseek':
                api_key = self.api_keys.get('deepseek', '')
            elif self.provider == 'ollama':
                api_key = self.api_keys.get('ollama', '') or 'not-needed'
            elif self.provider == 'custom_openai':
                api_key = self.custom_api_key or self.api_keys.get('custom_openai', '') or 'not-needed'
            else:
                api_key = ''

            llm_client = LLMClient(api_key=api_key, provider=self.provider, model=self.model, base_url=self.base_url, http_proxy=self.http_proxy)
        except Exception as e:
            self.batch_error.emit(0, 0, f"Failed to initialize LLM client:\n{str(e)}")
            self.finished_proofreading.emit(0, 0, 0)
            return

        # Process in batches of 20 segments
        batch_size = 20
        checked_count = 0
        issues_count = 0
        ok_count = 0

        for batch_start in range(0, len(self.segments_to_check), batch_size):
            if self._cancelled:
                break

            batch_end = min(batch_start + batch_size, len(self.segments_to_check))
            batch = self.segments_to_check[batch_start:batch_end]

            # Format batch for API
            batch_text = ""
            for row_idx, segment in batch:
                segment_num = f"{row_idx + 1:04d}"
                batch_text += f"[SEGMENT {segment_num}]\n{self.source_lang}: {segment.source}\n{self.target_lang}: {segment.target}\n\n"

            self.progress_update.emit(checked_count, f"Proofreading segments {batch_start + 1}-{batch_end}...")

            # Send to LLM
            try:
                full_prompt = f"{self.custom_prompt}\n\n{batch_text}"

                response = llm_client.translate(
                    text="",
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                    custom_prompt=full_prompt
                )

                if self._cancelled:
                    break

                # Parse response
                for row_idx, segment in batch:
                    if self._cancelled:
                        break

                    segment_num = f"{row_idx + 1:04d}"

                    pattern_ok = f"\\[SEGMENT {segment_num}\\]\\s*✓"
                    pattern_issue = f"\\[SEGMENT {segment_num}\\]\\s*⚠"

                    if re.search(pattern_ok, response, re.IGNORECASE):
                        ok_count += 1
                    elif re.search(pattern_issue, response, re.IGNORECASE):
                        issue_pattern = f"\\[SEGMENT {segment_num}\\]\\s*⚠\\s*\\n(.+?)(?=\\[SEGMENT|$)"
                        issue_match = re.search(issue_pattern, response, re.DOTALL)

                        if issue_match:
                            issue_text = issue_match.group(1).strip()
                            self.segment_issue.emit(row_idx, issue_text, self.model)
                            issues_count += 1

                    checked_count += 1
                    self.stats_update.emit(checked_count, issues_count, ok_count)

            except Exception as e:
                self.batch_error.emit(batch_start, batch_end, str(e))

        self.finished_proofreading.emit(checked_count, issues_count, ok_count)
