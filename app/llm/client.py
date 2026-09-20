"""
Thin LLM client wrapper.

Scope of the LLM in this architecture is intentionally narrow:
  1. Intent classification -- "which agent(s) appear relevant to this
     request?" (a SUGGESTION only; never an authorization decision).
  2. Answer synthesis -- turning retrieved documents into a fluent,
     cited natural-language answer.

The LLM is never given the authorization matrix and never decides
whether an agent is invoked -- see app/auth/policy_engine.py for that.

If no LLM_API_KEY is configured (or DISABLE_LLM=true), MedOrch falls back
to deterministic keyword-based heuristics so the whole POC remains fully
runnable and demoable offline, without requiring any external credentials.
"""
from __future__ import annotations

from app.config import get_settings


class LLMUnavailableError(RuntimeError):
    pass


def llm_configured() -> bool:
    settings = get_settings()
    return bool(settings.llm_api_key) and not settings.disable_llm


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 600) -> str:
    """
    Calls the configured LLM provider. Raises LLMUnavailableError if no
    provider/key is configured -- callers are expected to have a
    deterministic fallback path (see app/graph/workflow.py).
    """
    settings = get_settings()
    if not llm_configured():
        raise LLMUnavailableError("No LLM configured (LLM_API_KEY unset or DISABLE_LLM=true)")

    if settings.llm_provider == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, max_tokens, settings)
    elif settings.llm_provider == "openai":
        return _call_openai(system_prompt, user_prompt, max_tokens, settings)
    else:
        raise LLMUnavailableError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def _call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int, settings) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.llm_api_key)
    response = client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if getattr(block, "type", None) == "text")


def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int, settings) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.llm_api_key)
    response = client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""
