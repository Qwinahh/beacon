"""
Memory Agent -- the bot's self-reflection layer.

Runs after each post cycle. Given what just happened (what was posted,
what was skipped, what signals fired), the Memory Agent reasons about:

  - What this tells us about the project or sector
  - Whether any thesis should be updated
  - What signal patterns are proving useful vs noisy
  - Any observation worth recording for future cycles

This is how the bot develops a point of view over time rather than
treating every cycle as a blank slate.

It does NOT post anything. It only reads and writes memory files.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from agents.base import ToolAgent
from bot.brain.memory import (
    record_project_observation,
    record_signal_outcome,
    record_thesis_update,
    get_all_project_memory,
    get_recent_thesis_updates,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def _write_observation(project: str, observation: str) -> dict:
    """Record a bot observation about a specific project."""
    record_project_observation(project, observation, source="bot")
    return {"saved": True, "project": project}


def _write_signal_outcome(signal_type: str, topic: str, outcome: str, note: str = "") -> dict:
    """Record whether a signal type led to a good post or was noise."""
    record_signal_outcome(signal_type, topic, outcome, note)
    return {"saved": True}


def _write_thesis_update(project: str, update: str, trigger: str = "") -> dict:
    """Record a shift in the bot's view on a project."""
    record_thesis_update(project, update, trigger)
    return {"saved": True, "project": project}


def _read_project_memory(project: str) -> dict:
    """Read existing observations about a project to inform current reflection."""
    from bot.brain.memory import get_project_observations
    obs = get_project_observations(project, n=5)
    thesis = get_recent_thesis_updates(n=3)
    return {"observations": obs, "recent_thesis_updates": thesis}


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

_WRITE_OBS_SCHEMA = {
    "name": "write_observation",
    "description": "Record a specific, factual observation about a project based on what just happened in this cycle. One or two sentences. Concrete, not generic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project": {"type": "string", "description": "Project name, e.g. 'Hyperliquid', 'Kaito', 'Meteora'."},
            "observation": {"type": "string", "description": "What you noticed. Be specific: include numbers, trends, or contrasts vs prior observations."},
        },
        "required": ["project", "observation"],
    },
}

_WRITE_SIGNAL_SCHEMA = {
    "name": "write_signal_outcome",
    "description": "Record whether a signal type proved useful (led to a post) or was noise (skipped). Helps the bot calibrate future signal evaluation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "signal_type": {"type": "string", "description": "rss | raise | tvl | alpha | funding_rate | unlock"},
            "topic": {"type": "string", "description": "The topic this signal was about."},
            "outcome": {"type": "string", "description": "posted | skipped | low_score"},
            "note": {"type": "string", "description": "Brief reason. E.g. 'TVL move was too small to say anything interesting' or 'raise had a credible lead investor'."},
        },
        "required": ["signal_type", "topic", "outcome"],
    },
}

_WRITE_THESIS_SCHEMA = {
    "name": "write_thesis_update",
    "description": "Record a meaningful shift in the bot's view on a project. Only use this when something genuinely changes the picture -- not for routine observations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project": {"type": "string", "description": "Project name."},
            "update": {"type": "string", "description": "What changed and why. Two sentences max."},
            "trigger": {"type": "string", "description": "The specific event or data point that prompted this update."},
        },
        "required": ["project", "update"],
    },
}

_READ_MEMORY_SCHEMA = {
    "name": "read_project_memory",
    "description": "Read existing bot observations and thesis updates about a project before recording new ones. Use this to avoid repeating the same observation and to track how views are evolving.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project": {"type": "string", "description": "Project to look up."},
        },
        "required": ["project"],
    },
}


# ---------------------------------------------------------------------------
# Memory Agent
# ---------------------------------------------------------------------------

class MemoryAgent(ToolAgent):

    SYSTEM = """\
You are the Memory Agent for a crypto X account (@Qwinahh).

You run after each post cycle. Your job: reflect on what just happened and
update the bot's memory so future cycles are smarter.

You are given a cycle summary: what was posted (or skipped), which signal
fired, what the topic was, and any relevant context.

Your reflection process:
1. Identify which project(s) are relevant to this cycle.
2. Call read_project_memory() for each to see what was previously observed.
3. Decide if there is a NEW observation worth recording -- something specific
   and concrete, not just "Hyperliquid is active". Good: "Hyperliquid OI at
   $4.2B, up 40% in two weeks -- pace is accelerating". Bad: "Hyperliquid
   had news today".
4. Call write_observation() only if the observation is genuinely new or
   meaningfully updates a prior one.
5. Call write_signal_outcome() to log whether the signal type was useful.
6. If the cycle reveals something that shifts the thesis on a project
   (not just a data point, but something that changes the narrative),
   call write_thesis_update().

Rules:
- Do not write vague observations. Every entry must contain a specific fact,
  number, or contrast.
- Do not repeat what is already in memory unless updating it with new data.
- Do not write a thesis update unless something genuinely changed.
- It is fine to call no tools if nothing interesting happened this cycle.

Return raw JSON only:
{
  "reflected": true,
  "observations_written": ["project1", "project2"],
  "signal_logged": "posted | skipped | none",
  "thesis_updated": ["project"] or [],
  "reflection_note": "One sentence: what was most interesting about this cycle."
}
"""

    TOOLS = {
        "write_observation":   (_write_observation,   _WRITE_OBS_SCHEMA),
        "write_signal_outcome":(_write_signal_outcome,_WRITE_SIGNAL_SCHEMA),
        "write_thesis_update": (_write_thesis_update, _WRITE_THESIS_SCHEMA),
        "read_project_memory": (_read_project_memory, _READ_MEMORY_SCHEMA),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_reflection(cycle_result: dict) -> dict:
    """
    Run the Memory Agent's reflection pass after a post cycle.

    Args:
        cycle_result: The dict returned by run_post_cycle(). Should contain:
            action, tweet_text, tweet_id, reason, and any signal metadata.

    Returns the agent's reflection summary dict.
    """
    action     = cycle_result.get("action", "skipped")
    tweet_text = cycle_result.get("tweet_text", "")
    reason     = cycle_result.get("reason", "")

    summary = (
        f"Cycle result: {action}\n"
        f"Reason: {reason}\n"
    )
    if tweet_text:
        summary += f"Tweet posted: {tweet_text}\n"

    log.info("[MemoryAgent] Running reflection for cycle: %s", action)
    result = MemoryAgent().run("Reflect on this post cycle and update memory.", extra_context=summary)
    log.info("[MemoryAgent] Reflection complete: %s", result.get("reflection_note", "")[:80])
    return result
