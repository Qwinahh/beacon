"""
Context assembler for tweet generation.

Builds the rich context string that gets injected into every writer call.
Rather than asking Claude to write "about a news item", we give it:

  1. The account persona and voice rules (from data/persona.md)
  2. The relevant project thesis, if the item matches a known project
  3. Recent posting history — topics, formats, and what we just said
  4. Any trending X conversation context passed in from the Scout

This is what turns generic crypto commentary into posts that feel like
they come from someone with an actual point of view.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from bot.config import PERSONA_PATH, STATE_PATH

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

def load_persona() -> str:
    """
    Load the full persona file as a string.

    Returns an empty string if the file doesn't exist yet, so the writer
    still functions without it (just with less personality).
    """
    p = Path(PERSONA_PATH)
    if not p.exists():
        log.warning("data/persona.md not found — writer will use minimal context.")
        return ""
    return p.read_text(encoding="utf-8").strip()


def extract_thesis(persona_text: str, topic: str, title: str) -> str:
    """
    Pull the relevant project/topic thesis section from the persona.

    Looks for a '### <ProjectName>' heading whose name appears in the
    topic string or the item title, and returns that section's text.
    Returns empty string if no match is found.
    """
    if not persona_text:
        return ""

    # Build a set of keywords to match against section headings.
    search_terms = set()
    if topic:
        search_terms.update(re.split(r"[\s/,]+", topic.lower()))
    if title:
        search_terms.update(re.split(r"[\s/,]+", title.lower()))

    # Split persona into sections by '## ' or '### ' headings.
    sections = re.split(r"\n(?=#{2,3} )", persona_text)

    for section in sections:
        # Grab the heading text.
        heading_match = re.match(r"#{2,3} (.+)", section)
        if not heading_match:
            continue
        heading = heading_match.group(1).lower()

        # Check if any search term appears in this heading.
        if any(term in heading for term in search_terms if len(term) > 3):
            # Return just the thesis block, trimmed.
            return section.strip()

    return ""


# ---------------------------------------------------------------------------
# Recent history
# ---------------------------------------------------------------------------

def _load_state_data() -> dict:
    p = Path(STATE_PATH)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_history_context(n_topics: int = 10, n_formats: int = 5) -> str:
    """
    Return a compact summary of recent posting history.

    Used by the writer to avoid immediate repetition in topic or format.
    """
    data = _load_state_data()
    if not data:
        return ""

    topics  = data.get("recent_topics", [])[-n_topics:]
    formats = data.get("recent_formats", [])[-n_formats:]

    lines = []
    if topics:
        lines.append(f"Recent topics covered: {', '.join(topics)}")
    if formats:
        lines.append(f"Recent post formats: {', '.join(formats)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_writer_context(
    topic: str,
    title: str,
    x_conversation: Optional[str] = None,
) -> str:
    """
    Assemble the full context block for the writer.

    Args:
        topic:           Topic string from the candidate item.
        title:           Item title (used for thesis matching and context).
        x_conversation:  Optional: what influential X accounts are saying
                         about this topic right now (from the Scout).

    Returns:
        A formatted string to be embedded in the writer's user prompt.
    """
    from bot.brain.memory import build_memory_context
    from bot.brain.vault import get_project_context as vault_project_ctx

    persona     = load_persona()
    thesis      = extract_thesis(persona, topic, title)
    history     = build_history_context()
    memory      = build_memory_context(topic, title)

    # Per-project deep memory — check vault (markdown) first, then fallback
    # to legacy JSON project memory if vault has nothing yet.
    project_ctx = ""
    for candidate in _infer_project_names(topic, title):
        project_ctx = vault_project_ctx(candidate)
        if project_ctx:
            break
    if not project_ctx:
        try:
            from bot.brain.project_memory import get_project_context as legacy_ctx
            for candidate in _infer_project_names(topic, title):
                project_ctx = legacy_ctx(candidate)
                if project_ctx:
                    break
        except Exception:
            pass

    parts: list[str] = []

    # --- Persona block (voice + style rules) ---
    if persona:
        voice_section = _extract_section(persona, "Voice & Style")
        narrative_section = _extract_section(persona, "What Counts as a Good Post")
        if voice_section:
            parts.append("## Account Voice & Style\n" + voice_section)
        if narrative_section:
            parts.append("## What Makes a Good Post\n" + narrative_section)

    # --- Relevant persona thesis (hand-written by Quin) ---
    if thesis:
        parts.append("## Relevant Project/Topic Thesis\n" + thesis)

    # --- Researcher-generated project memory (automated deep-dive) ---
    if project_ctx:
        parts.append(project_ctx)

    # --- Posting history ---
    if history:
        parts.append("## Recent Posting History\n" + history)

    # --- General bot memory ---
    if memory:
        parts.append(memory)

    # --- X conversation context ---
    if x_conversation and x_conversation.strip():
        parts.append(
            "## What People on X Are Saying Right Now\n"
            + x_conversation.strip()
            + "\n\n"
            "Use this to understand the current conversation — don't parrot it, "
            "add to it or offer a different angle."
        )

    return "\n\n".join(parts)


def _infer_project_names(topic: str, title: str) -> list[str]:
    """
    Heuristically extract project name candidates from topic and title.
    Used to look up per-project researcher memory.
    Returns a short list of candidates to try, best-guess first.
    """
    candidates = []
    # The topic field is often already the project name (e.g. "hyperliquid")
    if topic and len(topic) > 2:
        candidates.append(topic.strip())
    # First capitalised word in the title is often the project
    if title:
        words = title.split()
        for w in words[:4]:
            clean = w.strip(".,;:()[]").rstrip("'s")
            if len(clean) > 2 and clean[0].isupper():
                candidates.append(clean)
    return candidates


def _extract_section(text: str, heading: str) -> str:
    """Extract the content of a markdown section by heading name."""
    pattern = rf"(?:#{2,3}) {re.escape(heading)}\n(.*?)(?=\n#{2,3} |\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# System prompt builder (replaces the static string in writer.py)
# ---------------------------------------------------------------------------

BASE_SYSTEM = """\
You write tweets for @Qwinahh — a crypto X account run by someone who trades
perps, farms airdrops, and moves into DeFi protocols before narratives form.

You are NOT writing news summaries. You are writing what a real person who
follows this space closely would actually say. The difference:

NEWS SUMMARY (bad): "Protocol X has raised $50M in Series B funding round."
REAL TAKE (good): "Protocol X raised $50M. Lead is Paradigm. That's the
signal — Paradigm doesn't do headline-grab rounds."

ABSOLUTE RULES:
- One specific fact (number, protocol mechanic, data point) minimum.
- State what it means or why it matters. Not just what happened.
- Never start: "Just saw", "Breaking:", "Huge news", "This is significant".
- Start with the observation, the number, or the implication.
- Under 270 chars. No hashtags. No URLs. No quotes around the output.
- Output ONLY the tweet text. Nothing else.
- Add "(position disclosed)" at the end if the post is about something held.
"""


def build_system_prompt(topic: str = "", title: str = "") -> str:
    """
    Build a full system prompt for the writer, augmented with persona context.

    Falls back cleanly to BASE_SYSTEM if persona.md doesn't exist.
    """
    persona = lo