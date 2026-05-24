"""
Per-project memory store.

Each discovered project gets its own JSON file in data/projects/.
The researcher agent writes to these files; the writer reads from them
to ground its takes in accumulated knowledge rather than just the current item.

Schema per project file:
{
  "name": "ProjectName",
  "first_seen": "2025-01-01T00:00:00Z",
  "last_updated": "...",
  "category": "DEX | Lending | Perps | Airdrop | ...",
  "chain": "Ethereum | Solana | ...",
  "thesis": "One paragraph summary of what this project is and why it matters.",
  "trust_score": 1-5,        # 1=noise, 5=high conviction
  "airdrop": {
    "status": "none | farming | watching | claimed | done",
    "worth_farming": true/false/null,
    "reasoning": "...",
    "actions": ["Bridge to X", "Use DEX daily", ...]
  },
  "observations": [          # Time-stamped observations, newest last
    {"ts": 1234567890, "note": "TVL spiked 40% after launch", "source": "defillama"}
  ],
  "consensus": {             # What the X crowd thinks
    "sentiment": "bullish | bearish | mixed | unknown",
    "summary": "Most accounts are focused on the airdrop, less on the product.",
    "updated": "..."
  },
  "links": {
    "website": "...",
    "docs": "...",
    "twitter": "...",
    "github": "...",
    "defillama": "..."
  }
}
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

PROJECTS_DIR = Path("data/projects")


def _project_path(name: str) -> Path:
    safe = name.lower().replace(" ", "_").replace("/", "_")[:60]
    return PROJECTS_DIR / f"{safe}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_project(name: str) -> Optional[dict]:
    """Load a project's memory. Returns None if not yet tracked."""
    path = _project_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Failed to read project memory for %s: %s", name, exc)
        return None


def list_projects() -> list[str]:
    """Return all tracked project names."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return [p.stem.replace("_", " ") for p in PROJECTS_DIR.glob("*.json")]


def get_project_context(name: str) -> str:
    """
    Return a compact context string for the writer.
    Summarises thesis, trust score, airdrop status, and recent observations.
    Returns empty string if project is unknown.
    """
    data = get_project(name)
    if not data:
        return ""

    lines = [f"## Bot Knowledge: {data['name']}"]

    if data.get("thesis"):
        lines.append(f"Thesis: {data['thesis']}")

    trust = data.get("trust_score")
    if trust:
        lines.append(f"Trust score: {trust}/5")

    airdrop = data.get("airdrop", {})
    if airdrop.get("status") and airdrop["status"] != "none":
        lines.append(
            f"Airdrop: {airdrop['status']}"
            + (f" — {airdrop['reasoning'][:100]}" if airdrop.get("reasoning") else "")
        )

    consensus = data.get("consensus", {})
    if consensus.get("summary"):
        lines.append(f"X consensus: {consensus['summary'][:120]}")

    obs = data.get("observations", [])
    if obs:
        recent = obs[-3:]
        lines.append("Recent observations:")
        for o in recent:
            lines.append(f"  - {o['note']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def _load_or_create(name: str) -> dict:
    existing = get_project(name)
    if existing:
        return existing
    return {
        "name": name,
        "first_seen": _now_iso(),
        "last_updated": _now_iso(),
        "category": "",
        "chain": "",
        "thesis": "",
        "trust_score": None,
        "airdrop": {"status": "none", "worth_farming": None, "reasoning": "", "actions": []},
        "observations": [],
        "consensus": {"sentiment": "unknown", "summary": "", "updated": ""},
        "links": {},
    }


def _save(name: str, data: dict) -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = _now_iso()
    path = _project_path(name)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def update_thesis(name: str, thesis: str, category: str = "", chain: str = "",
                  trust_score: Optional[int] = None, links: Optional[dict] = None) -> None:
    """Write or update the core thesis for a project."""
    data = _load_or_create(name)
    data["thesis"] = thesis
    if category:
        data["category"] = category
    if chain:
        data["chain"] = chain
    if trust_score is not None:
        data["trust_score"] = max(1, min(5, trust_score))
    if links:
        data["links"].update(links)
    _save(name, data)
    log.info("Updated thesis for %s (trust=%s)", name, trust_score)


def add_observation(name: str, note: str, source: str = "") -> None:
    """Append a time-stamped observation. Keeps the 30 most recent."""
    data = _load_or_create(name)
    obs = data.setdefault("observations", [])
    obs.append({"ts": time.time(), "note": note, "source": source})
    data["observations"] = obs[-30:]
    _save(name, data)


def update_airdrop(name: str, status: str, worth_farming: Optional[bool],
                   reasoning: str, actions: Optional[list] = None) -> None:
    """Update airdrop tracking for a project."""
    data = _load_or_create(name)
    data["airdrop"] = {
        "status": status,
        "worth_farming": worth_farming,
        "reasoning": reasoning,
        "actions": actions or [],
    }
    _save(name, data)
    log.info("Updated airdrop status for %s: %s, worth_farming=%s", name, status, worth_farming)


def update_consensus(name: str, sentiment: str, summary: str) -> None:
    """Update the X crowd consensus for a project."""
    data = _load_or_create(name)
    data["consensus"] = {
        "sentiment": sentiment,
        "summary": summary,
        "updated": _now_iso(),
    }
    _save(name, data)
