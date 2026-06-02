"""
Fear & Greed Index data source.

Fetches the Crypto Fear & Greed Index from alternative.me (free, no auth).
Injected into every post for macro sentiment context.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

log = logging.getLogger(__name__)

_URL = "https://api.alternative.me/fng/"
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "CryptoBot/2.0"})


def fetch_fear_greed() -> Optional[dict]:
    """Return current Fear & Greed reading as {value, label, direction}."""
    try:
        resp = _SESSION.get(_URL, params={"limit": 2}, timeout=8)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return None
        current = data[0]
        value = int(current["value"])
        label = current["value_classification"]
        prev  = int(data[1]["value"]) if len(data) > 1 else value
        return {
            "value":     value,
            "label":     label.lower(),
            "prev":      prev,
            "direction": "rising" if value > prev else ("falling" if value < prev else "flat"),
        }
    except Exception as exc:
        log.warning("Fear & Greed Index fetch failed: %s", exc)
        return None


def fear_greed_summary() -> str:
    """Return a compact one-liner for context injection."""
    data = fetch_fear_greed()
    if not data:
        return ""
    direction = f", {data['direction']}" if data["direction"] != "flat" else ""
    return f"Fear & Greed: {data['value']}/100 ({data['label']}{direction})"
