"""
bot/brain/llm.py — Unified LLM client with free-tier provider fallback chain.

Provider priority (all free, no credit card):
  1. Groq          — llama-3.3-70b-versatile. 14,400 req/day free. Fastest.
                     Get key: console.groq.com (email only, instant)
  2. Cerebras      — llama-3.3-70b. Fastest throughput. Free tier.
                     Get key: cloud.cerebras.ai
  3. OpenRouter    — 200 req/day on :free models. Good fallback variety.
                     Get key: openrouter.ai (GitHub login)
  4. Anthropic     — fallback only if all free tiers exhausted or unavailable.
                     Costs money. Set ANTHROPIC_API_KEY if you want this.

All providers use the OpenAI-compatible chat completions format.
The bot will try each provider in order, falling back on rate limit or error.

To run completely free: set GROQ_API_KEY (and optionally CEREBRAS_API_KEY,
OPENROUTER_API_KEY). Leave ANTHROPIC_API_KEY unset.

References:
  github.com/cheahjs/free-llm-api-resources  — full free LLM API directory
  github.com/tashfeenahmed/freellmapi        — multi-provider proxy
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider configs
# ---------------------------------------------------------------------------

_PROVIDERS = [
    {
        "name": "anthropic_compat",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": None,          # uses native anthropic SDK
        "model": "claude-sonnet-4-6",
        "free": False,
        "rpm": 50,
        "rpd": 10000,
    },
    {
        "name": "groq",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "free": True,
        "rpm": 30,
        "rpd": 14400,
    },
    {
        "name": "cerebras",
        "env_key": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "model": "llama-3.3-70b",
        "free": True,
        "rpm": 30,
        "rpd": 1000,
    },
    {
        "name": "openrouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "free": True,
        "rpm": 20,
        "rpd": 200,
    },
]

# Track per-provider failure timestamps to implement backoff
_provider_failures: dict[str, float] = {}
_FAILURE_BACKOFF = 300   # 5 min backoff after a provider error


def _is_backed_off(name: str) -> bool:
    last_fail = _provider_failures.get(name, 0)
    return time.time() - last_fail < _FAILURE_BACKOFF


def _mark_failure(name: str) -> None:
    _provider_failures[name] = time.time()


def _available_providers() -> list[dict]:
    """Return configured providers in priority order, skipping unconfigured or backed-off."""
    available = []
    for p in _PROVIDERS:
        key = os.environ.get(p["env_key"], "").strip()
        if not key:
            continue
        if _is_backed_off(p["name"]):
            log.debug("Provider %s is in backoff, skipping", p["name"])
            continue
        available.append({**p, "api_key": key})
    return available


# ---------------------------------------------------------------------------
# OpenAI-compatible call (covers Groq, Cerebras, OpenRouter)
# ---------------------------------------------------------------------------

def _call_openai_compat(
    provider: dict,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    """Make a chat completion call using the OpenAI-compatible API format."""
    try:
        from openai import OpenAI, RateLimitError, APIError  # type: ignore
    except ImportError:
        log.warning("openai package not installed. Run: pip install openai")
        return None

    client = OpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
    )

    extra_headers = {}
    if provider["name"] == "openrouter":
        extra_headers["HTTP-Referer"] = "https://github.com/Qwinahh/beacon"
        extra_headers["X-Title"] = "Beacon Bot"

    try:
        resp = client.chat.completions.create(
            model=provider["model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            extra_headers=extra_headers if extra_headers else None,
        )
        text = resp.choices[0].message.content
        log.info("LLM: generated via %s (%s)", provider["name"], provider["model"])
        return text
    except Exception as e:
        err = str(e).lower()
        if "rate limit" in err or "429" in err:
            log.warning("Provider %s rate limited: %s", provider["name"], e)
        else:
            log.warning("Provider %s error: %s", provider["name"], e)
        _mark_failure(provider["name"])
        return None


# ---------------------------------------------------------------------------
# Anthropic native call (fallback)
# ---------------------------------------------------------------------------

def _call_anthropic(
    provider: dict,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
) -> Optional[str]:
    try:
        import anthropic  # type: ignore
    except ImportError:
        log.warning("anthropic package not installed")
        return None

    client = anthropic.Anthropic(api_key=provider["api_key"])
    try:
        msg = client.messages.create(
            model=provider["model"],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = msg.content[0].text
        log.info("LLM: generated via anthropic (%s)", provider["model"])
        return text
    except Exception as e:
        log.warning("Anthropic error: %s", e)
        _mark_failure(provider["name"])
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def complete(
    system: str,
    user: str,
    max_tokens: int = 400,
    temperature: float = 0.85,
) -> Optional[str]:
    """
    Generate text using the best available free provider.
    Falls back through the provider chain automatically.

    Returns the generated text, or None if all providers fail.
    """
    providers = _available_providers()

    if not providers:
        log.error(
            "No LLM providers configured. Set at least one of: "
            "GROQ_API_KEY, CEREBRAS_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY"
        )
        return None

    for provider in providers:
        if provider["name"] == "anthropic_compat":
            result = _call_anthropic(provider, system, user, max_tokens, temperature)
        else:
            result = _call_openai_compat(provider, system, user, max_tokens, temperature)

        if result is not None:
            return result

        log.info("Falling back from %s to next provider", provider["name"])

    log.error("All LLM providers failed or exhausted")
    return None


def get_active_provider() -> str:
    """Return name of the first available (non-backed-off) provider."""
    for p in _available_providers():
        return p["name"]
    return "none"


def provider_status() -> list[dict]:
    """Return status of all configured providers for diagnostics."""
    status = []
    for p in _PROVIDERS:
        key = os.environ.get(p["env_key"], "").strip()
        status.append({
            "name": p["name"],
            "configured": bool(key),
            "free": p["free"],
            "backed_off": _is_backed_off(p["name"]),
            "model": p["model"],
        })
    return status
