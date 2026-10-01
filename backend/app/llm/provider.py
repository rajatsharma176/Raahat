"""
LLM Provider abstraction — clean interface supporting Gemini (primary),
with extension points for OpenAI and Anthropic.

Usage:
    from app.llm.provider import get_llm_provider
    llm = get_llm_provider()
    response = await llm.generate(prompt, ...)
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)



# We use a simple dataclass here to avoid circular imports
class LLMOutput:
    def __init__(self, text: str, raw: Any = None):
        self.text = text
        self.raw = raw


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMOutput:
        """Generate a text response."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a structured JSON response conforming to schema."""
        ...


class GeminiProvider(LLMProvider):
    """Gemini Flash provider via google-generativeai with auto-retry on rate limits."""

    def __init__(self) -> None:
        import google.generativeai as genai
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please add it to your .env file."
            )
        genai.configure(api_key=settings.gemini_api_key)
        self._model_name = settings.llm_model
        self._client = genai
        logger.info("GeminiProvider initialized with model=%s", self._model_name)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMOutput:
        import asyncio
        import re
        import google.generativeai as genai

        temp = temperature if temperature is not None else settings.llm_temperature
        max_tok = max_tokens if max_tokens is not None else settings.llm_max_tokens

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {prompt}"

        def _sync_generate():
            model = genai.GenerativeModel(
                self._model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=temp,
                    max_output_tokens=max_tok,
                ),
            )
            resp = model.generate_content(full_prompt)
            return resp.text

        # Retry up to 3 times on rate limit (429) with backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(None, _sync_generate)
                return LLMOutput(text=text)
            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "quota" in err_str.lower()
                is_last = attempt == max_retries - 1
                if is_rate_limit and not is_last:
                    # Parse retry_delay from API response, default 30s
                    delay_match = re.search(r"retry in (\d+\.?\d*)s", err_str)
                    wait = float(delay_match.group(1)) if delay_match else 30.0
                    wait = min(wait, 60.0)  # cap at 60s
                    logger.warning(
                        "Gemini rate limit hit (attempt %d/%d). Waiting %.0fs...",
                        attempt + 1, max_retries, wait
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
        raise RuntimeError("Gemini generate failed after all retries")

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ask Gemini to return JSON conforming to the given schema.
        We instruct Gemini explicitly to return valid JSON only.
        """
        json_schema_str = json.dumps(schema, indent=2)
        structured_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: You MUST respond with ONLY valid JSON that strictly "
            f"conforms to this schema. Do NOT include any explanation, markdown "
            f"fences, or extra text outside the JSON:\n\n{json_schema_str}"
        )
        output = await self.generate(
            structured_prompt,
            system_prompt=system_prompt,
            temperature=0.05,  # low temperature for structured output
        )
        # Strip potential markdown code fences
        text = output.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # remove first and last fence lines
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse structured LLM response: %s\nRaw: %s", e, text[:500])
            raise ValueError(f"LLM returned invalid JSON: {e}") from e


class MockLLMProvider(LLMProvider):
    """
    Fallback mock provider when no API key is configured.
    Returns deterministic responses so the system can start without an API key.
    """

    async def generate(self, prompt: str, **kwargs) -> LLMOutput:
        logger.warning("MockLLMProvider: No real LLM available. Returning mock response.")
        return LLMOutput(
            text="[MOCK RESPONSE - Configure GEMINI_API_KEY for real AI responses]"
        )

    async def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # Return a minimal valid structure matching common schemas
        logger.warning("MockLLMProvider: Returning mock structured response.")
        return {"mock": True, "message": "Configure GEMINI_API_KEY for real AI responses"}


# ─────────────────────── Provider factory ─────────────────────────────────── #

_provider_instance: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider singleton."""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    if not settings.gemini_api_key:
        logger.warning(
            "GEMINI_API_KEY not configured — using MockLLMProvider. "
            "Set GEMINI_API_KEY in .env for real AI behavior."
        )
        _provider_instance = MockLLMProvider()
        return _provider_instance

    provider = settings.llm_provider.lower()
    if provider == "gemini":
        _provider_instance = GeminiProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Supported: gemini")

    return _provider_instance


def reset_provider() -> None:
    """Reset the singleton (useful for testing)."""
    global _provider_instance
    _provider_instance = None
