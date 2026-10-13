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
import sys
import time
from typing import Dict, Optional, Literal, List, Tuple
from dataclasses import dataclass


def load_api_keys() -> Dict[str, str]:
    """Load API keys from unified settings/settings.json, with legacy api_keys.txt fallback."""
    import json
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    api_keys = {}
    configured_user_data_path = None

    # Resolve user data pointer path (same cross-platform location as main app)
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        pointer_path = os.path.join(appdata, "Supervertaler", "config.json")
    elif sys.platform == 'darwin':
        pointer_path = os.path.join(os.path.expanduser('~'), "Library", "Application Support", "Supervertaler", "config.json")
    else:
        xdg_config = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        pointer_path = os.path.join(xdg_config, "Supervertaler", "config.json")

    # Read configured user data path from pointer file (if available)
    if os.path.exists(pointer_path):
        try:
            with open(pointer_path, 'r', encoding='utf-8') as f:
                pointer_data = json.load(f)
            configured_user_data_path = pointer_data.get("user_data_path") or None
        except Exception:
            configured_user_data_path = None

    # Try unified settings first
    unified_paths = []
    if configured_user_data_path:
        # New layout first, then old layout as fallback
        unified_paths.append(os.path.join(configured_user_data_path, "workbench", "settings", "settings.json"))
        unified_paths.append(os.path.join(configured_user_data_path, "settings", "settings.json"))
    unified_paths.extend([
        os.path.join(os.path.expanduser('~'), "Supervertaler", "workbench", "settings", "settings.json"),
        os.path.join(os.path.expanduser('~'), "Supervertaler", "settings", "settings.json"),  # old layout fallback
        os.path.join(script_dir, "user_data_private", "workbench", "settings", "settings.json"),
        os.path.join(script_dir, "user_data_private", "settings", "settings.json"),  # old layout fallback
        os.path.join(script_dir, "user_data", "workbench", "settings", "settings.json"),
        os.path.join(script_dir, "user_data", "settings", "settings.json"),  # old layout fallback
    ])

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
        legacy_paths = []
        if configured_user_data_path:
            legacy_paths.append(os.path.join(configured_user_data_path, "api_keys.txt"))
        legacy_paths.extend([
            os.path.join(os.path.expanduser('~'), "Supervertaler", "api_keys.txt"),
            os.path.join(script_dir, "user_data_private", "api_keys.txt"),
            os.path.join(script_dir, "user_data", "api_keys.txt"),
            os.path.join(script_dir, "api_keys.txt"),
        ])
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


class LLMClient:
    """Universal LLM client for translation tasks"""

    # Default model per provider (Batch #9.3: единственный — custom_openai;
    # модель активного профиля всегда приоритетнее этого значения)
    DEFAULT_MODELS = {
        "custom_openai": "custom-model",  # Custom OpenAI-compatible endpoint
    }



    
    # Vision-capable models (support image inputs).
    # Batch #9.3: облачные провайдеры удалены; для custom_openai vision пока
    # ОТКЛЮЧЁН (model_supports_vision == False для любой модели) — включается
    # отдельным шагом: галка «модель поддерживает vision» в профиле (план 9.5).
    VISION_MODELS = {}


    # Reasoning models that don't support temperature parameter (must be omitted)
    REASONING_MODELS = ["gpt-5", "o1", "o3"]

    @classmethod
    def model_supports_vision(cls, provider: str, model_name: str) -> bool:
        """
        Check if a model supports vision (image) inputs
        
        Args:
            provider: Provider name ("openai", "claude", "gemini")
            model_name: Model identifier
            
        Returns:
            True if model supports vision, False otherwise
        """
        provider = provider.lower()
        vision_models = cls.VISION_MODELS.get(provider, [])
        return model_name in vision_models

    def __init__(self, api_key: str = None, provider: str = "openai", model: Optional[str] = None, max_tokens: int = 16384, base_url: Optional[str] = None, http_proxy: Optional[str] = None):
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
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODELS.get(self.provider)
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.http_proxy = http_proxy  # e.g. "http://user:pass@127.0.0.1:8080"

        if not self.model:
            raise ValueError(f"Unknown provider: {provider}")

        # Validate API key (Batch #9.3: custom_openai — единственный провайдер,
        # ключ не обязателен; фабрика/воркеры подставляют 'not-needed')
        if self.provider != 'custom_openai' and not self.api_key:
            raise ValueError(f"API key required for provider: {provider}")

        # Auto-detect temperature based on model
        self.temperature = self._get_temperature()
    
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

        if images and not self.model_supports_vision(self.provider, self.model):
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
            system_prompt=system_prompt, enable_prompt_caching=enable_prompt_caching)

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

    def _call_openai_with_usage(self, prompt: str, max_tokens: Optional[int] = None, images: Optional[List] = None, system_prompt: Optional[str] = None, enable_prompt_caching: bool = False) -> Tuple[str, Dict]:
        """Call an OpenAI-compatible API and return (text, usage_dict).

        Единственное ядро исполнения после Batch #9.3 (custom_openai).
        enable_prompt_caching сохранён в сигнатуре для совместимости
        вызывающих; маркеры кэша провайдеров (OpenRouter→Anthropic)
        удалены вместе с провайдерами — совместимые эндпоинты кэшируют
        стабильные префиксы на своей стороне.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")

        model_lower = self.model.lower()
        is_reasoning_model = any(x in model_lower for x in ["gpt-5", "o1", "o3"])
        timeout_seconds = 600.0 if is_reasoning_model else 120.0

        client_kwargs = {"api_key": self.api_key, "timeout": timeout_seconds}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if self.http_proxy:
            import httpx
            client_kwargs["http_client"] = httpx.Client(proxy=self.http_proxy, timeout=timeout_seconds)
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

        api_params = {"model": self.model, "messages": messages, "timeout": timeout_seconds}
        if is_reasoning_model:
            api_params["max_completion_tokens"] = tokens_to_use
        else:
            api_params["max_tokens"] = tokens_to_use
            api_params["temperature"] = self.temperature

        response = client.chat.completions.create(**api_params)

        if not response.choices or not response.choices[0].message.content:
            raise ValueError(f"OpenAI returned empty response for model {self.model}")

        text = response.choices[0].message.content.strip()
        if not text:
            raise ValueError(f"OpenAI returned empty translation for model {self.model}")

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


