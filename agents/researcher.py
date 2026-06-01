"""
Researcher Agent -- deep-dives new and watched projects.

When the Scout surfaces a project the bot hasn't seen before (or hasn't
researched in a while), the Researcher is called to:

  1. Pull on-chain data from DeFiLlama (TVL, category, chain, age)
  2. Fetch the project's website/docs for a plain-English description
  3. Check X consensus via LunarCrush (what are people actually saying)
  4. Evaluate airdrop worthiness (is it worth farming? what actions?)
  5. Form a thesis and trust score, write everything to data/projects/

The output is stored in per-project JSON files that the writer reads from
in future cycles, giving the bot accumulated genuine views over time.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import Optional

from agents.base import ToolAgent
from bot.brain import vault as _vault

log = logging.getLogger(__name__)

_SESSION_HEADERS = {"User-Agent": "CryptoBot/2.0", "Accept": "application/json"}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _defillama_lookup(project_name: str) -> dict:
    """Look up a project on DeFiLlama by name."""
    try:
        import requests
        r = requests.get(
            "https://api.llama.fi/protocols",
            headers=_SESSION_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        protocols = r.json()
        name_lower = project_name.lower()
        matches = [
            p for p in protocols
            if name_lower in p.get("name", "").lower()
            or name_lower in p.get("slug", "").lower()
        ]
        if not matches:
            return {"found": False, "note": f"No DeFiLlama entry found for '{project_name}'."}
        p = matches[0]
        return {
            "found": True,
            "name": p.get("name"),
            "slug": p.get("slug"),
            "tvl_usd": p.get("tvl"),
            "category": p.get("category"),
            "chains": p.get("chains", []),
            "change_1d": p.get("change_1d"),
            "change_7d": p.get("change_7d"),
            "url": f"https://defillama.com/protocol/{p.get('slug', '')}",
            "description": p.get("description", ""),
            "listed_at": p.get("listedAt"),
            "audits": p.get("audits"),
            "github": p.get("github", []),
        }
    except Exception as exc:
        return {"found": False, "error": str(exc)}


def _fetch_page_text(url: str) -> dict:
    """Fetch text content from a URL (docs, website, etc.)."""
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": "CryptoBot/2.0"}, timeout=15)
        r.raise_for_status()
        # Strip HTML tags crudely for text extraction
        import re
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        return {"url": url, "text": text[:3000], "status": r.status_code}
    except Exception as exc:
        return {"url": url, "error": str(exc)}


def _x_consensus(topic: str) -> dict:
    """Fetch what crypto X is saying about a project."""
    try:
        from bot.sources.xcontext import fetch_topic_posts
        posts = fetch_topic_posts(topic, limit=10)
        if not posts:
            return {"posts": [], "summary": f"No recent X posts found for '{topic}' (or scraper unavailable)."}
        return {"posts": posts, "summary": f"Found {len(posts)} recent posts about '{topic}'."}
    except Exception as exc:
        return {"posts": [], "summary": f"X consensus unavailable: {exc}"}


def _write_thesis(
    project_name: str,
    thesis: str,
    category: str,
    chain: str,
    trust_score: int,
    website: Optional[str] = None,
    docs: Optional[str] = None,
    defillama_url: Optional[str] = None,
) -> dict:
    """Persist the researcher's thesis and metadata to the vault."""
    _vault.update_thesis(project_name, thesis)
    _vault.update_trust_score(project_name, trust_score)
    # Record links as an observation so they appear in the file.
    links = []
    if website:   links.append(f"website: {website}")
    if docs:      links.append(f"docs: {docs}")
    if defillama_url: links.append(f"DeFiLlama: {defillama_url}")
    if links:
        _vault.add_observation(project_name, "Links — " + " | ".join(links), source="researcher")
    _vault.log_research(project_name, trust_score, notes=f"category={category}, chain={chain}")
    return {"saved": True, "project": project_name, "trust_score": trust_score}


def _write_airdrop(
    project_name: str,
    status: str,
    worth_farming: Optional[bool],
    reasoning: str,
    actions: Optional[list] = None,
) -> dict:
    """Persist airdrop evaluation to the vault."""
    _vault.update_airdrop_status(project_name, status, worth=worth_farming)
    note = f"Airdrop eval: status={status}, worth_farming={worth_farming}. {reasoning}"
    if actions:
        note += f" Actions: {', '.join(actions)}."
    _vault.add_observation(project_name, note, source="researcher")
    return {"saved": True, "project": project_name, "worth_farming": worth_farming}


def _write_consensus(project_name: str, sentiment: str, summary: str) -> dict:
    """Persist X crowd consensus as an observation in the vault."""
    note = f"X consensus: sentiment={sentiment}. {summary}"
    _vault.add_observation(project_name, note, source="x_scraper")
    return {"saved": True}


def _write_observation(project_name: str, note: str, source: str = "") -> dict:
    """Add a time-stamped observation to a project's vault file."""
    _vault.add_observation(project_name, note, source or "researcher")
    return {"saved": True}


def _read_project_memory(project_name: str) -> dict:
    """Read existing vault memory for a project before deciding what to research."""
    data = _vault.read_project(project_name)
    if not data:
        return {"exists": False, "project": project_name}
    return {"exists": True, **data}


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

_DEFILLAMA_SCHEMA = {
    "name": "defillama_lookup",
    "description": "Look up a project on DeFiLlama by name. Returns TVL, category, chains, 24h/7d change, age, audits, GitHub links.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Project name to search for."}
        },
        "required": ["project_name"],
    },
}

_FETCH_PAGE_SCHEMA = {
    "name": "fetch_page_text",
    "description": "Fetch text from a URL (project website, docs, whitepaper). Returns first 3000 chars of text content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch."}
        },
        "required": ["url"],
    },
}

_X_CONSENSUS_SCHEMA = {
    "name": "x_consensus",
    "description": "Fetch recent X posts about a project or topic to understand current community sentiment and narrative.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Project or topic name to search on X."}
        },
        "required": ["topic"],
    },
}

_WRITE_THESIS_SCHEMA = {
    "name": "write_thesis",
    "description": "Save the researcher's thesis and metadata for a project to persistent memory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "thesis": {"type": "string", "description": "1-3 sentence thesis on what this project is and why it matters (or doesn't)."},
            "category": {"type": "string", "description": "DEX | Lending | Perps | Airdrop | Bridge | Staking | Other"},
            "chain": {"type": "string", "description": "Primary chain(s)"},
            "trust_score": {"type": "integer", "description": "1=noise/scam, 2=low conviction, 3=watch, 4=interesting, 5=high conviction"},
            "website": {"type": "string"},
            "docs": {"type": "string"},
            "defillama_url": {"type": "string"},
        },
        "required": ["project_name", "thesis", "category", "chain", "trust_score"],
    },
}

_WRITE_AIRDROP_SCHEMA = {
    "name": "write_airdrop",
    "description": "Save airdrop evaluation for a project.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "status": {"type": "string", "description": "none | watching | farming | claimed | done"},
            "worth_farming": {"type": "boolean", "description": "True if worth farming based on research."},
            "reasoning": {"type": "string", "description": "Why is or isn't it worth farming?"},
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Steps to farm the airdrop if worth_farming is true.",
            },
        },
        "required": ["project_name", "status", "worth_farming", "reasoning"],
    },
}

_WRITE_CONSENSUS_SCHEMA = {
    "name": "write_consensus",
    "description": "Save X community consensus for a project.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "sentiment": {"type": "string", "description": "bullish | bearish | mixed | unknown"},
            "summary": {"type": "string", "description": "1-2 sentence summary of what X accounts are saying."},
        },
        "required": ["project_name", "sentiment", "summary"],
    },
}

_WRITE_OBS_SCHEMA = {
    "name": "write_observation",
    "description": "Add a specific observation to a project's memory log.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "note": {"type": "string", "description": "Specific, factual observation with numbers if possible."},
            "source": {"type": "string"},
        },
        "required": ["project_name", "note"],
    },
}

_READ_MEMORY_SCHEMA = {
    "name": "read_project_memory",
    "description": "Read existing memory for a project before starting research, to avoid duplicating work.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"}
        },
        "required": ["project_name"],
    },
}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ResearcherAgent(ToolAgent):

    SYSTEM = (
        "You are the Research Agent for @Qwinahh's crypto X account.\n\n"
        "Your job: deep-dive a given project and write everything you learn to\n"
        "persistent memory. Future posting cycles will use this memory to ground\n"
        "takes in real knowledge rather than just surface-level news.\n\n"
        "Research process:\n"
        "1. Call read_project_memory() first. If recent thesis exists (< 7 days old), skip.\n"
        "2. Call defillama_lookup() to get TVL, category, chains, growth metrics.\n"
        "3. If DeFiLlama has a website or docs URL, call fetch_page_text() on it.\n"
        "4. Call x_consensus() to understand what the X community thinks right now.\n"
        "5. Based on all of the above, form a thesis:\n"
        "   - What does this protocol actually do?\n"
        "   - What is the on-chain traction (TVL size/growth, audit status, age)?\n"
        "   - Is this early and worth attention, or late and crowded?\n"
        "   - Trust score 1-5: 1=noise, 3=watch, 5=high conviction\n"
        "6. Call write_thesis() with your findings.\n"
        "7. Evaluate airdrop: Is there a token? Is it launched already? If no token:\n"
        "   - Is TVL > $5M? Is there VC backing? Is usage growing? Is competition low?\n"
        "   - If 3+ of these: worth_farming=true, list the specific actions\n"
        "   - Call write_airdrop() with your evaluation.\n"
        "8. Summarise X sentiment and call write_consensus().\n"
        "9. Write 1-3 specific observations (with numbers) via write_observation().\n\n"
        "Be honest. Low trust_score is correct when evidence is thin.\n"
        "Do not hype. Airdrop worth_farming=false is a valid and common outcome.\n\n"
        "Return raw JSON:\n"
        '{"project": "name", "researched": true, "trust_score": 3, '
        '"thesis_summary": "one sentence", "airdrop_verdict": "worth farming | not worth farming | no airdrop"}'
    )

    TOOLS = {
        "defillama_lookup":  (_defillama_lookup,  _DEFILLAMA_SCHEMA),
        "fetch_page_text":   (_fetch_page_text,   _FETCH_PAGE_SCHEMA),
        "x_consensus":       (_x_consensus,       _X_CONSENSUS_SCHEMA),
        "write_thesis":      (_write_thesis,       _WRITE_THESIS_SCHEMA),
        "write_airdrop":     (_write_airdrop,      _WRITE_AIRDROP_SCHEMA),
        "write_consensus":   (_write_consensus,    _WRITE_CONSENSUS_SCHEMA),
        "write_observation": (_write_observation,  _WRITE_OBS_SCHEMA),
        "read_project_memory": (_read_project_memory, _READ_MEMORY_SCHEMA),
    }


def research_project(project_name: str) -> dict:
    """
    Run a full research cycle on a single project.
    Returns the agent's summary dict.
    """
    log.info("Researcher: starting deep-dive on '%s'", project_name)
    result = ResearcherAgent().run(
        f"Research this project and build a memory for it: {project_name}"
    )
    log.info("Researcher: done with '%s' — %s", project_name, result.get("thesis_summary", "")[:80])
    return result
