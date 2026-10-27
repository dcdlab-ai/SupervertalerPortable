"""
LLM Clients Module for Supervertaler
=====================================

Specialized independent module for interacting with the LLM provider.
Can be used standalone or imported by other applications.

Supported Provider (Batch #9.3):
- custom_openai — any OpenAI-compatible endpoint (active Custom profile);
  requests go through the OpenAI SDK (`_call_openai_with_usage`).
Cloud providers (OpenAI, Anthropic, Google/Gemini, Mistral, DeepSeek,
OpenRouter) and Ollama were removed; a stale provider name raises a clear
ValueError instead of executing a request.

Temperature Handling:
- Reasoning models (GPT-5, o1, o3): temperature parameter OMITTED (not supported)
- Standard models: temperature=0.3

Usage:
    from modules.llm_clients import LLMClient

    client = LLMClient(api_key="key-or-not-needed", provider="custom_openai",
                       model="my-model", base_url="http://127.0.0.1:8080/v1")

    response = client.translate("Hello world", source_lang="en", target_lang="nl")
"""

import os
import re
import time
from typing import Dict, Optional, Literal, List, Tuple
from dataclasses import dataclass


def load_api_keys() -> Dict[str, str]:
    """Load API keys from unified settings/settings.json, with legacy api_keys.txt fallback."""
    import json
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    api_keys = {}

    # P1-B: single data root via modules/portable_paths.py — priority
    # env SUPERVERTALER_DATA_ROOT > dev flag .supervertaler.local >
    # <build root>/Supervertaler. The old pointer file and the home-directory
    # fallback are gone; the repo dev fallbacks (user_data_private, user_data)
    # stay as before.
    from modules.portable_paths import data_root
    data_dir = str(data_root())

    # Try unified settings first (new layout first, then old layout as fallback)
    unified_paths = [
        os.path.join(data_dir, "workbench", "settings", "settings.json"),
        os.path.join(data_dir, "settings", "settings.json"),
        os.path.join(script_dir, "user_data_private", "workbench", "settings", "settings.json"),
        os.path.join(script_dir, "user_data_private", "settings", "settings.json"),  # old layout fallback
        os.path.join(script_dir, "user_data", "workbench", "settings", "settings.json"),
        os.path.join(script_dir, "user_data", "settings", "settings.json"),  # old layout fallback
    ]

    for settings_path in dict.fromkeys(unified_paths):
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                api_keys = data.get("api_keys", {})
                if api_keys:
                    break
            except Exception:
                pass

    # Legacy fallback: api_keys.txt (for backward compatibility)
    if not api_keys:
        legacy_paths = [
            os.path.join(data_dir, "api_keys.txt"),
            os.path.join(script_dir, "user_data_private", "api_keys.txt"),
            os.path.join(script_dir, "user_data", "api_keys.txt"),
            os.path.join(script_dir, "api_keys.txt"),
        ]
        for legacy_path in dict.fromkeys(legacy_paths):
            if os.path.exists(legacy_path):
                try:
                    with open(legacy_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                api_keys[key.strip()] = value.strip()
                    if api_keys:
                        break
                except Exception:
                    pass

    # Migrate legacy 'google' key to canonical 'gemini' key
    if api_keys.get('google') and not api_keys.get('gemini'):
        api_keys['gemini'] = api_keys['google']


    return api_keys




@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    provider: Literal["openai", "claude", "gemini", "mistral", "deepseek", "openrouter"]
    model: str
    api_key: str
    temperature: Optional[float] = None  # Auto-detected if None
    max_tokens: int = 16384  # Increased from 4096 for batch translation (100 segments needs ~16K tokens)


# ---------------------------------------------------------------------------
# G3.2: reasoning-model response handling (finish_reason, reasoning_content,
# inline <think>/<thinking> blocks) and typed response errors.
# ---------------------------------------------------------------------------

# Closed inline reasoning blocks emitted by chat templates
# (<think>…</think>, <thinking>…</thinking>), case-insensitive, multi-line.
_REASONING_BLOCK_RE = re.compile(
    r'<(think|thinking)\b[^>]*>.*?</\1\s*>', re.IGNORECASE | re.DOTALL)
# An unclosed reasoning opening tag, e.g. a response cut off mid-reasoning.
_OPEN_REASONING_RE = re.compile(r'<(think|thinking)\b[^>]*/?>', re.IGNORECASE)
# G3.2d: a dangling closing tag whose opening tag is not in the response —
# chat templates that inject <think> into the prompt leave the reasoning
# header outside the returned content, so the answer follows the last </think>.
_CLOSE_REASONING_RE = re.compile(r'</(?:think|thinking)\s*>', re.IGNORECASE)

# Module-level log hook: the main app wires its own log callback at startup
# (set_llm_log_callback) so core-level warnings reach the app log panel
# without importing the app.
_llm_log_callback = None


def set_llm_log_callback(callback) -> None:
    """Wire (or clear with None) the log callback for module-level messages."""
    global _llm_log_callback
    _llm_log_callback = callback


def _llm_log(message: str) -> None:
    cb = _llm_log_callback
    if cb is not None:
        try:
            cb(message)
        except Exception:
            pass


class LLMResponseError(ValueError):
    """Base for typed OpenAI-response errors (G3.2).

    Subclasses ValueError so every existing `except ValueError` caller
    (segment, batch, QuickTrans, chat, proofread, …) keeps handling them.
    Attributes: finish_reason, has_reasoning, reasoning_tokens, partial_text
    (G3.2d: text recovered before a mid-answer truncation, None otherwise).
    """

    def __init__(self, message: str, finish_reason: Optional[str] = None,
                 has_reasoning: bool = False, reasoning_tokens: int = 0,
                 partial_text: Optional[str] = None):
        super().__init__(message)
        self.finish_reason = finish_reason
        self.has_reasoning = bool(has_reasoning)
        self.reasoning_tokens = int(reasoning_tokens or 0)
        self.partial_text = partial_text


class LLMTruncatedError(LLMResponseError):
    """The model exhausted its max_tokens budget on reasoning."""


class LLMEmptyResponseError(LLMResponseError):
    """No content (with reasoning_content present, with, or without)."""


class LLMTimeoutError(LLMResponseError):
    """The request timed out under the profile's timeout value (G3.2b)."""


class LLMConnectionError(LLMResponseError):
    """TCP/TLS connect failed (Q.8b): host unreachable, server stopped or the
    connection was refused within the connect-timeout window. A genuine read
    timeout (server accepted the connection and stayed silent) stays
    LLMTimeoutError with its own message."""


# Q.8b: dedicated TCP-connect timeout (seconds) for every client this module
# creates. The read timeout stays the profile's 'Request timeout' (default
# 10 min); connect failures used to ride the SAME budget, and with the SDK's
# 3 attempts an unreachable LAN host cost ~65 s (Windows connect ~21 s × 3)
# before surfacing as a misleading "timed out after 10 minutes (600 s)".
CONNECT_TIMEOUT_SECONDS = 15.0


# Copy-pasteable example for the "Extra request body" fix hint: disables
# thinking in llama.cpp/LM Studio chat templates.
_DISABLE_THINKING_EXAMPLE = '{"chat_template_kwargs": {"enable_thinking": false}}'

# Keys the profile 'Extra request body' field must not override — these are
# owned by the request builder / the profile's own fields (G3.2b).
_PROFILE_FORBIDDEN_EXTRA_KEYS = {"model", "messages", "max_tokens", "stream", "tools"}


def parse_profile_request_fields(profile: dict):
    """Parse the optional Custom-profile request fields (G3.2b).

    Reads profile['max_tokens'], profile['timeout_min'], profile['extra_body']
    (strings from the profile dialog; absent/empty mean "use the default").
    Returns (max_tokens: int|None, timeout_seconds: float|None,
    extra_body: dict|None, errors: list[str]) — an empty `errors` list means
    the profile passes save validation.
    """
    import json as _json
    errors = []
    max_tokens = None
    timeout_seconds = None
    extra_body = None

    raw_mt = profile.get('max_tokens')
    if raw_mt is not None and str(raw_mt).strip():
        try:
            mt = int(str(raw_mt).strip())
            if mt <= 0:
                raise ValueError
            max_tokens = mt
        except (TypeError, ValueError):
            errors.append("'Max tokens' must be a positive whole number "
                          "(e.g. 20000); leave empty for the default (16384).")

    raw_to = profile.get('timeout_min')
    if raw_to is not None and str(raw_to).strip():
        try:
            # G3.2g: decimal comma is accepted ("1,5" → 1.5); strings with
            # several separators ("1,5,5", "1.5,5") become "1.5.5" and stay
            # invalid (float raises → save stays blocked).
            to_min = float(str(raw_to).strip().replace(',', '.'))
            if to_min <= 0:
                raise ValueError
            timeout_seconds = to_min * 60.0
        except (TypeError, ValueError):
            errors.append("'Request timeout' must be a positive number of minutes "
                          "(e.g. 10); leave empty for the default (10 minutes).")

    raw_eb = profile.get('extra_body')
    if raw_eb is not None and str(raw_eb).strip():
        try:
            parsed = _json.loads(str(raw_eb).strip())
        except Exception:
            parsed = None
        if not isinstance(parsed, dict):
            errors.append("'Extra request body' must be a JSON object "
                          f"(e.g. {_DISABLE_THINKING_EXAMPLE}); "
                          "leave empty for nothing.")
        else:
            forbidden = sorted(_PROFILE_FORBIDDEN_EXTRA_KEYS & {str(k) for k in parsed})
            if forbidden:
                errors.append("'Extra request body' must not contain the key(s): "
                              + ", ".join(forbidden)
                              + " — these are managed by the request builder.")
            else:
                extra_body = parsed

    return max_tokens, timeout_seconds, extra_body, errors


def _extract_reasoning_tokens(response) -> int:
    usage = getattr(response, 'usage', None)
    details = getattr(usage, 'completion_tokens_details', None) if usage else None
    return int(getattr(details, 'reasoning_tokens', 0) or 0) if details else 0


def _parse_completion_response(response, model: str, lenient: bool = False) -> str:
    """G3.2: parse a chat-completion response into translation text.

    finish_reason is read; reasoning_content is detected but NEVER used as
    translation; inline <think>/<thinking> blocks are stripped from content.
    Raises typed LLMResponseError subclasses for truncated/empty responses.

    G3.2d (coordinator verdict 2026-10-20, answers 1 & 5):
    - strict (translation paths): a non-empty response cut off at max_tokens
      raises LLMTruncatedError carrying `partial_text`;
    - lenient (skip_cleaning=True callers: chat analysis, AutoPrompt, JSON
      extractors): return the partial text with a warning log, as before;
    - a dangling closing tag (template with <think> injected into the prompt)
      resolves to the text after the last closing tag;
    - an unclosed opening tag raises in every path (nothing is returned).
    """
    choices = getattr(response, 'choices', None)
    if not choices:
        raise LLMEmptyResponseError(
            f"OpenAI-compatible endpoint returned no choices for model {model}",
            finish_reason=None, has_reasoning=False, reasoning_tokens=0)
    choice = choices[0]
    finish = getattr(choice, 'finish_reason', None)
    msg = getattr(choice, 'message', None)
    content = getattr(msg, 'content', None) if msg is not None else None
    reasoning = getattr(msg, 'reasoning_content', None) if msg is not None else None
    has_reasoning = bool(reasoning)
    reasoning_tokens = _extract_reasoning_tokens(response)

    stripped = _REASONING_BLOCK_RE.sub('', content or '')
    last_close = None
    for m in _CLOSE_REASONING_RE.finditer(stripped):
        last_close = m
    if last_close is not None:
        # Dangling closing tag: the opening tag is not in this response
        # (template puts it in the prompt) — the answer is what follows it.
        stripped = stripped[last_close.end():]
    stripped = stripped.strip()

    if _OPEN_REASONING_RE.search(stripped):
        # Reasoning block cut off mid-stream: the budget ran out while
        # the model was still reasoning.
        raise LLMTruncatedError(
            f"Model {model} produced an unclosed reasoning block — the reasoning "
            f"process exhausted the max_tokens budget (finish_reason={finish!r}). "
            f"Increase 'Max tokens' in the profile or disable thinking via the "
            f"'Extra request body' field (e.g. {_DISABLE_THINKING_EXAMPLE}).",
            finish_reason=finish, has_reasoning=has_reasoning,
            reasoning_tokens=reasoning_tokens)
    if not stripped:
        if finish == 'length':
            raise LLMTruncatedError(
                f"Model {model} exhausted the max_tokens budget on reasoning "
                f"(finish_reason='length'; reasoning only, no translation content"
                f"{f', reasoning_tokens={reasoning_tokens}' if reasoning_tokens else ''}). "
                f"Increase 'Max tokens' in the profile or disable thinking via the "
                f"'Extra request body' field (e.g. {_DISABLE_THINKING_EXAMPLE}).",
                finish_reason=finish, has_reasoning=has_reasoning,
                reasoning_tokens=reasoning_tokens)
        raise LLMEmptyResponseError(
            f"Model {model} returned an empty response "
            f"(finish_reason={finish!r}, "
            f"reasoning_content {'present' if has_reasoning else 'absent'})",
            finish_reason=finish, has_reasoning=has_reasoning,
            reasoning_tokens=reasoning_tokens)
    if finish == 'length':
        if lenient:
            # Analysis/prompt-generation callers (skip_cleaning=True) keep the
            # pre-G3.2d behaviour: return the partial text, warn in the log.
            _llm_log(f"⚠ LLM response for {model} truncated at max_tokens "
                     f"(finish_reason='length'); translation may be incomplete")
        else:
            # Translation paths raise; the text recovered before the cut is
            # preserved on the exception (coordinator answer 1).
            preview = stripped if len(stripped) <= 200 else stripped[:200] + '…'
            raise LLMTruncatedError(
                f"Model {model} was cut off at max_tokens mid-answer "
                f"(finish_reason='length'); the translation is incomplete. "
                f"Increase 'Max tokens' in the profile. Partial text: {preview!r}",
                finish_reason=finish, has_reasoning=has_reasoning,
                reasoning_tokens=reasoning_tokens, partial_text=stripped)
    return stripped


class LLMClient:
    """Universal LLM client for translation tasks"""

    # Default model per provider (Batch #9.3: единственный — custom_openai;
    # модель активного профиля всегда приоритетнее этого значения)
    DEFAULT_MODELS = {
        "custom_openai": "custom-model",  # Custom OpenAI-compatible endpoint
    }



    
    # Reasoning models that don't support temperature parameter (must be omitted)
    REASONING_MODELS = ["gpt-5", "o1", "o3"]

    def __init__(self, api_key: str = None, provider: str = "openai", model: Optional[str] = None, max_tokens: int = 16384, base_url: Optional[str] = None, http_proxy: Optional[str] = None, supports_vision: bool = False, timeout_seconds: Optional[float] = None, extra_body: Optional[dict] = None, profile_name: Optional[str] = None):
        """
        Initialize LLM client

        Args:
            api_key: API key ('not-needed' — заглушка от фабрики/воркеров;
                для custom_openai ключ не обязателен)
            provider: "custom_openai" (Batch #9.3: другие имена создают клиент,
                но translate_with_usage отклонит их с понятной ValueError)
            model: Model name (uses default if None)
            max_tokens: Maximum tokens for responses (default: 16384)
            base_url: Custom API base URL (from the active Custom profile)
            http_proxy: Optional HTTP/HTTPS proxy URL, e.g. "http://user:pass@host:8080"
            supports_vision: Batch #9.5 — «Model supports vision» из профиля Custom
                (OpenAI-совместимый эндпоинт). Флаг профиля, не whitelist имён моделей.
            timeout_seconds: G3.2b — «Request timeout» профиля (минуты × 60);
                None → профиль не задан → default 10 минут (600 s; для
                gpt-5/o1/o3-by-name исторические 600 s сохранены).
            extra_body: G3.2b — «Extra request body» профиля (валидированный
                JSON-объект), мержится в тело каждого create()-запроса.
            profile_name: G3.2b — имя профиля для понятных сообщений об ошибке
                таймаута (не участвует в запросе).
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODELS.get(self.provider)
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.http_proxy = http_proxy  # e.g. "http://user:pass@127.0.0.1:8080"
        self.supports_vision = bool(supports_vision)
        self.timeout_seconds = timeout_seconds
        self.extra_body = extra_body if isinstance(extra_body, dict) else None
        self.profile_name = profile_name

        if not self.model:
            raise ValueError(f"Unknown provider: {provider}")

        # Validate API key (Batch #9.3: custom_openai — единственный провайдер,
        # ключ не обязателен; фабрика/воркеры подставляют 'not-needed')
        if self.provider != 'custom_openai' and not self.api_key:
            raise ValueError(f"API key required for provider: {provider}")

        # Auto-detect temperature based on model
        self.temperature = self._get_temperature()

    def _effective_timeout_seconds(self) -> float:
        """Request timeout in seconds (G3.2b).

        Profile's «Request timeout» field (timeout_seconds, minutes×60) wins;
        default is 10 minutes (600.0) — replaces the old hard 120 s. The old
        name-based 600 s for gpt-5/o1/o3 stays identical (default = 600 s).
        """
        if self.timeout_seconds is not None:
            return float(self.timeout_seconds)
        return 600.0
    
    def _clean_translation_response(self, translation: str, prompt: str) -> str:
        """
        Clean translation response to remove any prompt remnants.
        
        Sometimes LLMs translate the entire prompt instead of just the source text.
        This method attempts to extract only the actual translation.
        
        Args:
            translation: Raw translation response from LLM
            prompt: Original prompt sent to LLM
        
        Returns:
            Cleaned translation text
        """
        if not translation:
            return translation
        
        # First, try to find the delimiter we added ("**YOUR TRANSLATION**")
        # Everything after this delimiter should be the actual translation
        delimiter_markers = [
            "**YOUR TRANSLATION (provide ONLY the translated text, no numbering or labels):**",
            "**YOUR TRANSLATION**",
            "**YOUR TRANSLATION (provide ONLY",
            "**JOUW VERTALING**",
            "**TRANSLATION**",
            "**VERTALING**",
            "Translation:",
            "Vertaling:",
            "YOUR TRANSLATION",
            "JOUW VERTALING",
        ]
        
        # Try to split on delimiter first (most reliable)
        import re
        for marker in delimiter_markers:
            # Use word boundary or newline before marker for better matching
            pattern = re.escape(marker)
            # Try with newline before it
            pattern_with_newline = r'\n\s*' + pattern
            match = re.search(pattern_with_newline, translation, re.IGNORECASE | re.MULTILINE)
            if not match:
                # Try without newline requirement
                match = re.search(pattern, translation, re.IGNORECASE)
            
            if match:
                result = translation[match.end():].strip()
                # Clean up any leading/trailing newlines, colons, or whitespace
                result = re.sub(r'^[::\s\n\r]+', '', result)
                result = result.strip()
                if result:
                    # Additional cleanup: remove any remaining prompt patterns
                    result = self._remove_prompt_patterns(result)
                    if result and len(result) < len(translation) * 0.9:  # Must be significantly shorter
                        return result
        
        # Common patterns that indicate the prompt was translated
        # These are translations of common prompt phrases
        prompt_patterns = [
            # Dutch translations of prompt instructions
            "Als een professionele",
            "Als professionele",
            "U bent een expert",
            "Uw taak is om",
            "Tijdens het vertaalproces",
            "De output moet uitsluitend bestaan",
            "Waarschuwingsinformatie:",
            "⚠️ PROFESSIONELE VERTAALCONTEXT:",
            "vertaler",
            "handleidingen",
            "regelgeving",
            "naleving",
            "medische apparaten",
            "professionele doeleinden",
            "medisch advies",
            "volledige documentcontext",
            "tekstsegmenten",
            "CAT-tool tags",
            "memoQ-tags",
            "Trados Studio-tags",
            "CafeTran-tags",
            # English patterns (in case language is mixed)
            "As a professional",
            "You are an expert",
            "Your task is to",
            "During the translation process",
            "The output must consist exclusively",
            "⚠️ PROFESSIONAL TRANSLATION CONTEXT:",
            "professional translation",
            "technical manuals",
            "regulatory compliance",
            "medical devices",
            "professional purposes",
            "medical advice",
            "full document context",
            "text segments",
            "CAT tool tags",
            "memoQ tags",
            "Trados Studio tags",
            "CafeTran tags",
        ]
        
        # Check if translation contains prompt patterns - if so, it's likely a translated prompt
        translation_lower = translation.lower()
        prompt_pattern_count = sum(1 for pattern in prompt_patterns if pattern.lower() in translation_lower)
        
        # If translation is suspiciously long and contains many prompt patterns, it's likely a translated prompt
        if len(translation) > 300 and prompt_pattern_count >= 3:
            # Try to find where actual translation starts
            # Look for the end of the last prompt-like sentence
            lines = translation.split('\n')
            cleaned_lines = []
            found_actual_translation = False
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    if found_actual_translation:
                        cleaned_lines.append(line)
                    continue
                
                # Check if this line looks like prompt instruction
                is_prompt = any(pattern.lower() in line_stripped.lower() for pattern in prompt_patterns)
                
                # Also check if it's a very long line (likely prompt instructions)
                if len(line_stripped) > 200:
                    prompt_phrases = sum(1 for pattern in prompt_patterns if pattern.lower() in line_stripped.lower())
                    if prompt_phrases >= 2:
                        is_prompt = True
                
                if is_prompt:
                    # Skip prompt lines
                    continue
                else:
                    # This might be actual translation
                    found_actual_translation = True
                    cleaned_lines.append(line)
            
            result = '\n'.join(cleaned_lines).strip()
            if result and len(result) < len(translation) * 0.7:  # Significantly shorter = likely cleaned correctly
                return self._remove_prompt_patterns(result)
        
        # Final cleanup: remove any remaining prompt patterns
        cleaned = self._remove_prompt_patterns(translation)
        
        # If cleaned version is much shorter, it was likely cleaned correctly
        if cleaned != translation and len(cleaned) < len(translation) * 0.8:
            return cleaned
        
        return translation
    
    def _remove_prompt_patterns(self, text: str) -> str:
        """Remove prompt-like patterns from text"""
        prompt_patterns = [
            "Als een professionele", "Als professionele", "U bent een expert",
            "Uw taak is om", "Tijdens het vertaalproces", "De output moet",
            "Waarschuwingsinformatie:", "⚠️ PROFESSIONELE", "vertaler",
            "handleidingen", "regelgeving", "naleving", "medische apparaten",
            "professionele doeleinden", "medisch advies", "volledige documentcontext",
            "tekstsegmenten", "CAT-tool tags", "memoQ-tags", "Trados Studio-tags",
            "CafeTran-tags", "As a professional", "You are an expert",
            "Your task is to", "During the translation process",
            "The output must consist exclusively", "⚠️ PROFESSIONAL",
            "professional translation", "technical manuals", "regulatory compliance",
            "medical devices", "professional purposes", "medical advice",
            "full document context", "text segments", "CAT tool tags",
            "memoQ tags", "Trados Studio tags", "CafeTran tags",
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_lower = line.lower()
            # Skip lines that contain prompt patterns
            has_prompt = any(pattern.lower() in line_lower for pattern in prompt_patterns)
            # Also skip very long lines that might be prompt instructions
            if not has_prompt and (len(line.strip()) < 300 or len(line.strip().split()) < 50):
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        return result if result else text
    
    def _get_temperature(self) -> Optional[float]:
        """Determine optimal temperature for model (None means omit parameter)"""
        model_lower = self.model.lower()
        
        # Reasoning models don't support temperature parameter - return None to omit it
        if any(reasoning in model_lower for reasoning in self.REASONING_MODELS):
            return None
        
        # Standard models use 0.3 for consistency
        return 0.3
    
    def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "nl",
        context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List] = None,
        system_prompt: Optional[str] = None,
        skip_cleaning: bool = False,
        enable_prompt_caching: bool = False,
    ) -> str:
        """
        Translate text using configured LLM

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context for translation
            custom_prompt: Optional custom prompt (overrides default simple prompt)
            system_prompt: Optional system prompt for AI behavior context
            skip_cleaning: If True, skip _clean_translation_response post-processing
                (used for prompt generation where translation-related keywords are expected)

        Returns:
            Translated text
        """
        # Delegate to translate_with_usage so that EVERY translation call flows
        # through the single token-usage logging path (translate_with_usage
        # records to the usage ledger). Behaviour is otherwise identical.
        result, _usage = self.translate_with_usage(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
            custom_prompt=custom_prompt,
            max_tokens=max_tokens,
            images=images,
            system_prompt=system_prompt,
            skip_cleaning=skip_cleaning,
            enable_prompt_caching=enable_prompt_caching,
        )
        return result

    def translate_with_usage(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "nl",
        context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List] = None,
        system_prompt: Optional[str] = None,
        skip_cleaning: bool = False,
        enable_prompt_caching: bool = False,
    ) -> Tuple[str, Dict]:
        """
        Same as translate() but returns (text, usage_dict).

        usage_dict contains:
            input_tokens: int
            output_tokens: int

        Returns (text, {}) if usage data is unavailable.
        """
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = f"Translate the following text from {source_lang} to {target_lang}:\n\n{text}"
            if context:
                prompt = f"Context: {context}\n\n{prompt}"

        # Batch #9.5: vision — свойство профиля (галка «Model supports vision»),
        # не whitelist имён моделей. Без галки изображения не отправляются.
        if images and not self.supports_vision:
            images = None

        _t0 = time.perf_counter()
        # Batch #9.3: единственная ветка исполнения — openai-совместимое ядро
        # (custom_openai). Чужое имя провайдера (в т.ч. из ещё не удалённого
        # меню моделей чата, до 9.4) — понятная ValueError вместо запроса.
        if self.provider != "custom_openai":
            raise ValueError(
                f"Provider '{self.provider}' has been removed — use a Custom "
                f"(OpenAI-compatible) profile in Settings → AI Settings")
        result, usage = self._call_openai_with_usage(
            prompt, max_tokens=max_tokens, images=images,
            system_prompt=system_prompt, enable_prompt_caching=enable_prompt_caching,
            lenient_on_truncation=skip_cleaning)

        if not skip_cleaning:
            result = self._clean_translation_response(result, prompt)

        # Record this call to the persistent usage ledger (best-effort, metadata
        # only). When the provider returned no usage, estimate via chars/4.
        try:
            from modules import usage_log as _usage_log
            _est_in = 0 if usage else (len(prompt) + 3) // 4
            _est_out = 0 if usage else (len(result) + 3) // 4
            _usage_log.record(
                self.provider, self.model, usage or {},
                estimated_input=_est_in, estimated_output=_est_out,
                duration_s=time.perf_counter() - _t0,
            )
        except Exception:
            pass

        return result, usage

    def _call_openai_with_usage(self, prompt: str, max_tokens: Optional[int] = None, images: Optional[List] = None, system_prompt: Optional[str] = None, enable_prompt_caching: bool = False, lenient_on_truncation: bool = False) -> Tuple[str, Dict]:
        """Call an OpenAI-compatible API and return (text, usage_dict).

        G3.2d: `lenient_on_truncation` is the existing `skip_cleaning` flag
        threaded down from translate_with_usage — its callers (chat analysis,
        AutoPrompt, JSON extractors) keep the return+warning behaviour for
        responses cut off at max_tokens; translation paths raise.

        Единственное ядро исполнения после Batch #9.3 (custom_openai).
        enable_prompt_caching сохранён в сигнатуре для совместимости
        вызывающих; маркеры кэша провайдеров (OpenRouter→Anthropic)
        удалены вместе с провайдерами — совместимые эндпоинты кэшируют
        стабильные префиксы на своей стороне.
        """
        try:
            from openai import (OpenAI, APITimeoutError, APIConnectionError,
                                APIStatusError)
        except ImportError:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")

        model_lower = self.model.lower()
        is_reasoning_model = any(x in model_lower for x in ["gpt-5", "o1", "o3"])
        # G3.2b: timeout from the profile ('Request timeout', minutes×60) or the
        # 10-minute default; the old 120 s is replaced, name-based 600 s kept.
        timeout_seconds = self._effective_timeout_seconds()
        # Q.8b: split the CONNECT phase out of the profile's read budget —
        # httpx.Timeout(<default for read/write/pool>, connect=N) is the SDK's
        # own convention. The bundled runtime ships httpx2 (openai 3.x's fork)
        # and may have no `httpx` package — fall back like the proxy branch.
        try:
            import httpx
        except ImportError:
            import httpx2 as httpx
        request_timeout = httpx.Timeout(timeout_seconds, connect=CONNECT_TIMEOUT_SECONDS)

        # Q.8b: SDK-level retries are OFF (its single budget also retried
        # CONNECT failures — 3×15 s to a dead host); the loop below keeps the
        # SDK's own retryable semantics for everything else: retryable STATUS
        # codes (408/409/429/5xx, Retry-After honoured, 2 retries, 0.5·2ⁿ
        # backoff capped at 8 s) and READ timeouts (server accepted and went
        # silent) — exactly what the SDK used to retry besides connects.
        client_kwargs = {"api_key": self.api_key, "timeout": request_timeout,
                         "max_retries": 0}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if self.http_proxy:
            client_kwargs["http_client"] = httpx.Client(proxy=self.http_proxy,
                                                        timeout=request_timeout)
        client = OpenAI(**client_kwargs)

        if max_tokens is not None:
            tokens_to_use = max_tokens
        elif is_reasoning_model:
            tokens_to_use = 32768
        else:
            tokens_to_use = self.max_tokens

        content = prompt
        if images:
            content = [{"type": "text", "text": prompt}]
            for img_ref, img_base64 in images:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        api_params = {"model": self.model, "messages": messages, "timeout": request_timeout}
        if is_reasoning_model:
            api_params["max_completion_tokens"] = tokens_to_use
        else:
            api_params["max_tokens"] = tokens_to_use
            api_params["temperature"] = self.temperature
        # G3.2b: profile 'Extra request body' (validated JSON object) is merged
        # into the request body by the SDK.
        if self.extra_body:
            api_params["extra_body"] = dict(self.extra_body)

        # Q.8b: one-line connection message («Cannot connect to … within
        # 15 s — host unreachable or server stopped — profile '…'.») with the
        # endpoint's host:port; no read-timeout wording for connect failures.
        try:
            from urllib.parse import urlsplit
            _netloc = urlsplit(self.base_url or "").netloc or (self.base_url or "endpoint")
        except Exception:
            _netloc = self.base_url or "endpoint"

        def _connection_error():
            return LLMConnectionError(
                f"Cannot connect to {_netloc} within "
                f"{CONNECT_TIMEOUT_SECONDS:g} s — host unreachable or server "
                f"stopped — profile '{self.profile_name or 'Custom LLM'}'.",
                finish_reason=None, has_reasoning=False, reasoning_tokens=0)

        _RETRYABLE_STATUS = {408, 409, 429}
        response = None
        _last_status_exc = None
        for _attempt in range(3):  # 1 try + 2 retries (the SDK default)
            try:
                response = client.chat.completions.create(**api_params)
                break
            except APITimeoutError as exc:
                # Connect-phase timeout (host never answered TCP) fails fast
                # with the connection message; a READ timeout (connection
                # established, server silent) keeps the old retry + message.
                if isinstance(getattr(exc, "__cause__", None), httpx.ConnectTimeout):
                    raise _connection_error() from exc
                if _attempt == 2:
                    # G3.2b: clear message with profile name + current timeout
                    # value, not a raw SDK traceback.
                    raise LLMTimeoutError(
                        f"Request to model {self.model} timed out after "
                        f"{timeout_seconds / 60.0:g} minutes ({timeout_seconds:g} s) — "
                        f"profile '{self.profile_name or 'Custom LLM'}'. Increase "
                        f"the profile's 'Request timeout' field and retry.",
                        finish_reason=None, has_reasoning=False,
                        reasoning_tokens=0) from exc
                time.sleep(min(0.5 * (2 ** _attempt), 8.0))
            except APIConnectionError as exc:
                # Refused / unreachable without any server response
                raise _connection_error() from exc
            except APIStatusError as exc:
                _status = getattr(exc, "status_code", None)
                if _status is None:
                    _resp = getattr(exc, "response", None)
                    _status = getattr(_resp, "status_code", None)
                if (_status is None or
                        not (_status >= 500 or _status in _RETRYABLE_STATUS) or
                        _attempt == 2):
                    raise
                _last_status_exc = exc
                delay = min(0.5 * (2 ** _attempt), 8.0)
                try:
                    _ra = exc.response.headers.get("retry-after")
                    if _ra is not None:
                        delay = max(delay, min(float(_ra), 60.0))
                except Exception:
                    pass
                time.sleep(delay)
        if response is None:
            raise _last_status_exc or RuntimeError(
                "request failed without a response")

        text = _parse_completion_response(response, self.model, lenient=lenient_on_truncation)

        usage = {}
        if hasattr(response, 'usage') and response.usage:
            cached_tokens = 0
            # OpenAI native: prompt_tokens_details.cached_tokens reports the
            # auto-cache hit count (50% off cached input). Available on GPT-4o,
            # GPT-4-turbo, GPT-5.x and the o-series.
            details = getattr(response.usage, 'prompt_tokens_details', None)
            if details is not None:
                cached_tokens = getattr(details, 'cached_tokens', 0) or 0
            # OpenRouter → Anthropic flavour: passes Anthropic's cache fields
            # through directly on the usage object.
            if not cached_tokens:
                cached_tokens = getattr(response.usage, 'cache_read_input_tokens', 0) or 0
            cache_creation_tokens = (
                getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
            )

            usage = {
                'input_tokens': getattr(response.usage, 'prompt_tokens', 0) or 0,
                'output_tokens': getattr(response.usage, 'completion_tokens', 0) or 0,
                # Tokens served from cache, billed at the provider's cache-read
                # rate (50% for OpenAI auto-cache, 10% for Anthropic via
                # OpenRouter, 10% for DeepSeek auto-cache).
                'cache_read_input_tokens': cached_tokens,
                # Tokens written to the cache on this call (Anthropic only;
                # billed at 1.25× input). Zero for native OpenAI / DeepSeek
                # which auto-cache without a separate write step.
                'cache_creation_input_tokens': cache_creation_tokens,
            }

        return text, usage


