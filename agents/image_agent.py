"""
Image agent — generates terminal-aesthetic images for image-eligible posts.

What it does: decides per-post whether an image helps (format-based rules
from data/vault/knowledge/image-strategy.md), builds a prompt in the
@Qwinahh visual style (#0d1117 dark background, terminal/data-viz look,
no moons/rockets/lambos), calls Replicate's flux-schnell model, and
returns raw image bytes for the orchestrator to upload.

When it runs: inline during the posting cycle, after the tweet passes
the authenticity judge and before post_tweet() — gated by
IMAGE_GENERATION_ENABLED and IMAGE_CHANCE in bot/config.py.

Reads:  bot/config.py flags, REPLICATE_API_TOKEN env
Writes: nothing on disk — returns bytes (or None) to the caller

Key design decisions:
- Never blocks posting: every failure path returns None and the
  orchestrator posts text-only. Missing token disables the agent.
- Generated images are decorative/abstract backgrounds and short labels
  only. AI models hallucinate digits, so REAL numbers are never put in
  the image prompt as chart data — a credibility-ending failure mode for
  an account whose thesis is being verifiably right (see image-strategy.md).
- Uses Replicate's sync HTTP API (Prefer: wait) — no SDK dependency.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from bot.config import IMAGE_GENERATION_ENABLED, REPLICATE_API_TOKEN

log = logging.getLogger(__name__)

_REPLICATE_URL = (
    "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"
)
_TIMEOUT_SECONDS = 60

# ---------------------------------------------------------------------------
# Decision logic — which formats warrant an image
# ---------------------------------------------------------------------------

# YES: image adds dwell/photo-expand value. MAYBE: only if the text leads
# with a number that can be visually echoed. NO: text-only performs better.
_IMAGE_YES     = {"data_observation", "thread_hook"}
_IMAGE_MAYBE   = {"contrarian", "farming_update"}
_IMAGE_NEVER   = {"hot_take", "punchy_take", "callout", "mistake_admission",
                  "prediction", "market_read", "announcement"}

_NUMBER_RE = re.compile(r"\$[\d,.]+[bmk]?|\d+(?:\.\d+)?%|\d{2,}", re.IGNORECASE)


def _wants_image(tweet_text: str, format_name: str) -> bool:
    """Format-level decision from image-strategy.md."""
    fmt = (format_name or "").lower()
    if fmt in _IMAGE_NEVER:
        return False
    if fmt in _IMAGE_YES:
        return bool(_NUMBER_RE.search(tweet_text)) if fmt == "data_observation" else True
    if fmt in _IMAGE_MAYBE:
        return bool(_NUMBER_RE.search(tweet_text))
    return False


# ---------------------------------------------------------------------------
# Prompt construction — @Qwinahh visual style
# ---------------------------------------------------------------------------

_STYLE_SUFFIX = (
    "dark background hex 0d1117, terminal aesthetic, monospace typography, "
    "thin subtle grid lines, white and terminal-green accents, clean minimal "
    "data visualization style, flat design, no gradients, no glow, "
    "professional trading dashboard look, no people, no logos, "
    "no rockets, no moons, no coins"
)

_TOPIC_HINTS = [
    (re.compile(r"\bperp|funding|oi\b|open interest|orderbook", re.I),
     "abstract minimal visualization of order book depth bars"),
    (re.compile(r"\byield|apy|apr|stak|susde|stable", re.I),
     "abstract minimal visualization of a flattening yield curve"),
    (re.compile(r"\btvl|inflow|outflow|deposit", re.I),
     "abstract minimal visualization of liquidity flow blocks"),
    (re.compile(r"\bunlock|vesting|supply", re.I),
     "abstract minimal visualization of token supply schedule bars"),
    (re.compile(r"\bhack|exploit|risk|depeg", re.I),
     "abstract minimal visualization of a fractured grid panel"),
]


def _build_prompt(tweet_text: str) -> str:
    subject = "abstract minimal on-chain data dashboard panel"
    for pattern, hint in _TOPIC_HINTS:
        if pattern.search(tweet_text):
            subject = hint
            break
    return f"{subject}, {_STYLE_SUFFIX}"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _generate(prompt: str) -> Optional[bytes]:
    """Call Replicate flux-schnell synchronously. Returns image bytes or None."""
    try:
        import requests
    except ImportError:
        log.warning("requests not available — image generation disabled.")
        return None

    try:
        resp = requests.post(
            _REPLICATE_URL,
            headers={
                "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json",
                "Prefer": "wait",
            },
            json={
                "input": {
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                    "output_format": "png",
                    "num_outputs": 1,
                }
            },
            timeout=_TIMEOUT_SECONDS,
        )
        if resp.status_code not in (200, 201):
            log.info("Replicate returned %d: %s", resp.status_code, resp.text[:200])
            return None

        output = resp.json().get("output") or []
        url = output[0] if isinstance(output, list) and output else (
            output if isinstance(output, str) else None)
        if not url:
            log.info("Replicate prediction finished without output URL.")
            return None

        image = requests.get(url, timeout=_TIMEOUT_SECONDS)
        if image.status_code != 200 or not image.content:
            log.info("Image download failed (%d).", image.status_code)
            return None
        log.info("Image generated (%d bytes) for prompt: %s", len(image.content), prompt[:80])
        return image.content
    except Exception as exc:
        log.info("Image generation failed (non-fatal): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def maybe_generate_image(tweet_text: str, format_name: str) -> Optional[bytes]:
    """
    Return PNG bytes if this post warrants an image and generation succeeds,
    else None. Never raises — the post must go out regardless.
    """
    if not IMAGE_GENERATION_ENABLED:
        log.debug("Image generation disabled (no REPLICATE_API_TOKEN).")
        return None
    try:
        if not _wants_image(tweet_text, format_name):
            log.debug("Format '%s' not image-eligible.", format_name)
            return None
        return _generate(_build_prompt(tweet_text))
    except Exception as exc:
        log.info("Image agent error (non-fatal): %s", exc)
        return None
