"""
Portfolio and watchlist management.

Reads data/portfolio.json (maintained by Quin) and generates posts for:
  - New positions that haven't been announced yet.
  - New airdrop farming activities.
  - Daily portfolio summary (optional, for high-activity periods).

All position-related posts include explicit disclosure language.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import anthropic

from bot.config import CLAUDE_MAX_TOKENS, CLAUDE_MODEL, PORTFOLIO_PATH, WATCHLIST_PATH
from bot.state import State

log = logging.getLogger(__name__)

_PORTFOLIO_SYSTEM = """\
You write transparent position announcements for a crypto commentary account.

Rules:
- Be honest about what you're doing and why.
- Always include a clear disclosure: "I hold a position in [project]" or "I'm farming [project]'s airdrop."
- No price predictions. No "this will 10x" framing.
- Max 260 characters.
- No hashtags.
- Keep it grounded — uncertainty is fine to acknowledge.
"""


def _load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to read %s: %s", path, exc)
        return {}


def _generate_position_post(entry: dict, kind: str) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_position_post(entry, kind)

    client = anthropic.Anthropic(api_key=api_key)

    if kind == "position":
        prompt = (
            f"Write a tweet announcing I've taken a position in {entry.get('project')} "
            f"({entry.get('ticker', '')}).\n"
            f"My reasoning: {entry.get('entry_note', 'early-stage interest')}\n"
            f"Include explicit position disclosure."
        )
    elif kind == "airdrop":
        actions = ", ".join(entry.get("actions", []))
        prompt = (
            f"Write a tweet announcing I'm farming {entry.get('project')}'s airdrop.\n"
            f"Activities: {actions}\n"
            f"Note: {entry.get('note', '')}\n"
            f"Include explicit disclosure that I'm farming this airdrop."
        )
    elif kind == "watching":
        prompt = (
            f"Write a tweet announcing I'm watching {entry.get('project')}.\n"
            f"Reason: {entry.get('reason', '')}\n"
            f"Frame as early-stage research, not a position. No price predictions."
        )
    else:
        return None

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=_PORTFOLIO_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()[:279]
    except anthropic.APIError as exc:
        log.error("Anthropic API error generating portfolio post: %s", exc)
        return _fallback_position_post(entry, kind)


def _fallback_position_post(entry: dict, kind: str) -> str:
    project = entry.get("project", "this protocol")
    if kind == "position":
        note = entry.get("entry_note", "")
        return f"Took a position in {project}. {note} (position disclosed)"[:279]
    if kind == "airdrop":
        return f"Farming {project}'s airdrop. Tracking this one closely. (position disclosed)"
    return f"Added {project} to my watchlist. Early stage, worth watching."


def get_new_announcements(state: State) -> list[str]:
    """
    Return a list of post texts for portfolio entries that haven't
    been announced yet. Each call only returns entries that are new
    since the last run.
    """
    data    = _load_json(PORTFOLIO_PATH)
    posted  = state.posted_portfolio_keys()
    posts   = []

    for entry in data.get("positions", []):
        if entry.get("status") != "active":
            continue
        key = f"position:{entry.get('project', '').lower()}"
        if key in posted:
            continue
        text = _generate_position_post(entry, "position")
        if text:
            posts.append((key, text))

    for entry in data.get("airdrops", []):
        if entry.get("status") != "farming":
            continue
        key = f"airdrop:{entry.get('project', '').lower()}"
        if key in posted:
            continue
        text = _generate_position_post(entry, "airdrop")
        if text:
            posts.append((key, text))

    for entry in data.get("watching", []):
        key = f"watching:{entry.get('project', '').lower()}"
        if key in posted:
            continue
        text = _generate_position_post(entry, "watching")
        if text:
            posts.append((key, text))

    return posts  # list of (key, text) tuples


def load_portfolio(path: str = PORTFOLIO_PATH) -> dict:
    """Return the full portfolio dict for use by the writer module."""
    return _load_json(path)
