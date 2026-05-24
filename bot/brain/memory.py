"""
Bot memory system.

The bot builds its own understanding of the crypto landscape over time by
writing structured observations after each posting cycle. This is separate
from Quin's persona.md (which Quin edits) -- this is what the bot itself
notices and learns.

Memory is stored in data/memory/ as plain JSON files that are committed
back to git alongside state.json. Each file has a clear purpose:

  project_observations.json  -- What the bot has noticed about each project
  signal_patterns.json       -- What kinds of signals lead to good vs bad posts
  thesis_updates.json        -- How views on projects have shifted over time
  quin_notes.json            -- Things Quin has explicitly told the bot

The MemoryReader is called by the writer to inject relevant memory into
each generation. The MemoryWriter is called by the orchestrator after each
successful post to record what happened.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

MEMORY_DIR = Path("data/memory")

OBSERVATION_FILE  = MEMORY_DIR / "project_observations.json"
SIGNAL_FILE       = MEMORY_DIR / "signal_patterns.json"
THESIS_FILE       = MEMORY_DIR / "thesis_updates.json"
QUIN_NOTES_FILE   = MEMORY_DIR / "quin_notes.json"

# Maximum observations per project before oldest are pruned.
MAX_OBSERVATIONS_PER_PROJECT = 20
# Maximum signal pattern entries total.
MAX_SIGNAL_ENTRIES = 50


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Memory load failed for %s: %s", path, exc)
        return {}


def _save(path: Path, data: dict) -> None:
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        log.error("Memory save failed for %s: %s", path, exc)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Project observations
# ---------------------------------------------------------------------------

def record_project_observation(project: str, observation: str, source: str = "bot") -> None:
    """
    Record something the bot noticed about a project.

    Args:
        project:     Project name (e.g. "Hyperliquid", "Kaito").
        observation: What was noticed (one or two sentences max).
        source:      "bot" for autonomous observations, "quin" for user-reported.
    """
    data = _load(OBSERVATION_FILE)
    projects = data.setdefault("projects", {})
    entries = projects.setdefault(project, [])

    entries.append({
        "ts":          _now(),
        "observation": observation,
        "source":      source,
    })

    # Prune oldest if over limit.
    if len(entries) > MAX_OBSERVATIONS_PER_PROJECT:
        entries[:] = entries[-MAX_OBSERVATIONS_PER_PROJECT:]

    data["projects"] = projects
    _save(OBSERVATION_FILE, data)
    log.debug("Recorded observation for %s: %s", project, observation[:80])


def get_project_observations(project: str, n: int = 5) -> list[dict]:
    """Return the n most recent observations for a project."""
    data = _load(OBSERVATION_FILE)
    entries = data.get("projects", {}).get(project, [])
    return entries[-n:]


def get_all_project_memory(projects: list[str], n_each: int = 3) -> str:
    """
    Build a memory context string covering multiple projects.

    Returned string is suitable for injection into a writer or analyst prompt.
    """
    data = _load(OBSERVATION_FILE)
    all_projects = data.get("projects", {})

    lines = []
    for project in projects:
        entries = all_projects.get(project, [])[-n_each:]
        if not entries:
            continue
        lines.append(f"### {project} (bot observations)")
        for e in entries:
            src = " [Quin]" if e.get("source") == "quin" else ""
            lines.append(f"  - {e['ts'][:10]}{src}: {e['observation']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Signal patterns
# ---------------------------------------------------------------------------

def record_signal_outcome(
    signal_type: str,
    topic: str,
    outcome: str,
    note: str = "",
) -> None:
    """
    Record whether a type of signal led to a good or skipped post.

    Args:
        signal_type: "rss", "raise", "tvl", "alpha", etc.
        topic:       The topic it was about.
        outcome:     "posted", "skipped", "low_score".
        note:        Brief reason or observation.
    """
    data = _load(SIGNAL_FILE)
    key = "good_signals" if outcome == "posted" else "noise_signals"
    entries = data.setdefault(key, [])

    entries.append({
        "ts":          _now(),
        "signal_type": signal_type,
        "topic":       topic,
        "outcome":     outcome,
        "note":        note,
    })

    # Prune oldest.
    if len(entries) > MAX_SIGNAL_ENTRIES:
        entries[:] = entries[-MAX_SIGNAL_ENTRIES:]

    if outcome == "skipped":
        skipped = data.setdefault("skipped_reasons", [])
        skipped.append({"ts": _now(), "topic": topic, "note": note})
        if len(skipped) > MAX_SIGNAL_ENTRIES:
            skipped[:] = skipped[-MAX_SIGNAL_ENTRIES:]

    data[key] = entries
    _save(SIGNAL_FILE, data)


def get_signal_patterns_summary(n: int = 10) -> str:
    """Return a short summary of recent signal patterns for prompt injection."""
    data = _load(SIGNAL_FILE)
    good   = data.get("good_signals", [])[-n:]
    noise  = data.get("noise_signals", [])[-n:]

    lines = []
    if good:
        lines.append("Signals that led to good posts recently:")
        for e in good[-5:]:
            lines.append(f"  - {e['signal_type']} / {e['topic']}: {e.get('note', '')[:80]}")
    if noise:
        lines.append("Signals that were skipped or low-quality recently:")
        for e in noise[-5:]:
            lines.append(f"  - {e['signal_type']} / {e['topic']}: {e.get('note', '')[:80]}")

    return "\n".join(lines) if lines else ""


# ---------------------------------------------------------------------------
# Thesis updates
# ---------------------------------------------------------------------------

def record_thesis_update(project: str, update: str, trigger: str = "") -> None:
    """
    Record a shift in the bot's view on a project.

    Args:
        project: Project name.
        update:  What changed and why (one or two sentences).
        trigger: The event or data point that caused the update.
    """
    data = _load(THESIS_FILE)
    updates = data.setdefault("updates", [])
    updates.append({
        "ts":      _now(),
        "project": project,
        "update":  update,
        "trigger": trigger,
    })
    # Keep last 100 thesis updates total.
    if len(updates) > 100:
        updates[:] = updates[-100:]
    data["updates"] = updates
    _save(THESIS_FILE, data)
    log.info("Thesis update for %s: %s", project, update[:80])


def get_recent_thesis_updates(n: int = 5) -> str:
    """Return recent thesis updates for prompt context."""
    data = _load(THESIS_FILE)
    updates = data.get("updates", [])[-n:]
    if not updates:
        return ""
    lines = ["Recent view changes:"]
    for u in updates:
        lines.append(f"  - {u['ts'][:10]} {u['project']}: {u['update'][:120]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quin notes
# ---------------------------------------------------------------------------

def add_quin_note(note: str, project: Optional[str] = None) -> None:
    """
    Store a note from Quin for the bot to remember.

    Called by note.py (the human-facing script for sending the bot info).
    """
    data = _load(QUIN_NOTES_FILE)
    notes = data.setdefault("notes", [])
    notes.append({
        "ts":      _now(),
        "note":    note,
        "project": project,
    })
    # Keep last 50 notes.
    if len(notes) > 50:
        notes[:] = notes[-50:]
    data["notes"] = notes
    _save(QUIN_NOTES_FILE, data)
    log.info("Quin note stored: %s", note[:80])


def get_quin_notes(project: Optional[str] = None, n: int = 5) -> str:
    """
    Return recent notes from Quin, optionally filtered by project.
    """
    data = _load(QUIN_NOTES_FILE)
    notes = data.get("notes", [])
    if project:
        notes = [n_ for n_ in notes if n_.get("project") == project]
    notes = notes[-n:]
    if not notes:
        return ""
    lines = ["Notes from Quin:"]
    for n_ in notes:
        lines.append(f"  - {n_['ts'][:10]}: {n_['note'][:200]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full context for writer injection
# ---------------------------------------------------------------------------

def build_memory_context(topic: str, title: str) -> str:
    """
    Build the memory block injected into every writer call.

    Extracts project names from topic/title, pulls observations, recent
    thesis updates, Quin notes, and signal patterns.
    """
    import re

    # Infer which projects might be relevant.
    text = f"{topic} {title}".lower()
    known_projects = [
        "Hyperliquid", "Kaito", "Meteora", "EigenLayer", "Arbitrum",
        "Jupiter", "Solana", "Base", "Optimism", "LayerZero",
        "Drift", "GMX", "Aave", "Uniswap", "Pendle", "Ethena",
    ]
    relevant = [p for p in known_projects if p.lower() in text]

    parts: list[str] = []

    # Project observations.
    if relevant:
        obs = get_all_project_memory(relevant, n_each=3)
        if obs:
            parts.append("## Bot Observations (from memory)\n" + obs)

    # Quin's notes on relevant projects.
    for project in relevant:
        qn = get_quin_notes(project=project, n=3)
        if qn:
            parts.append(qn)

    # Any general Quin notes (not project-specific).
    general_qn = get_quin_notes(project=None, n=3)
    if general_qn and not relevant:
        parts.append(general_qn)

    # Recent thesis updates.
    thesis = get_recent_thesis_updates(n=3)
    if thesis:
        parts.append("## View Updates\n" + thesis)

    return "\n\n".join(parts)
