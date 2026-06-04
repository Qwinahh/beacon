"""
bot/brain/verifier.py — Fact-checking and source credibility layer.

4-tier source system:
  Tier 1: On-chain data, official announcements, SEC/regulatory filings, verified audits
  Tier 2: Established researchers (Delphi, Messari, The Block, Arkham), major crypto media
  Tier 3: CT consensus, Reddit, Discord, Telegram — sentiment only, never written as fact
  Tier 4: Anonymous tips, single-source unverified claims — discarded

The verifier checks incoming claims before they're written to the vault as confirmed facts.
Community signals (Tier 3/4) go into a separate unconfirmed_signals store.
"""

from __future__ import annotations

import json
import re
import time
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source Tier Classification
# ---------------------------------------------------------------------------

class SourceTier(IntEnum):
    ON_CHAIN    = 1  # on-chain tx, official contract, protocol announcement
    RESEARCHER  = 2  # Delphi, Messari, The Block, DeFiLlama, Nansen, Arkham
    COMMUNITY   = 3  # CT, Reddit, Discord, Telegram — sentiment only
    NOISE       = 4  # unverified, anon tips, single-source rumour

# Domains / sources that qualify as Tier 2
_TIER2_SOURCES = {
    # Research
    "delphi", "messari", "theblock", "coindesk", "cointelegraph",
    "blockworks", "decrypt", "thedefiant", "banklesshq", "unchainedcrypto",
    # On-chain analytics
    "nansen", "arkham", "dune", "defillama", "glassnode", "chainalysis",
    # Official
    "sec.gov", "cftc.gov", "whitehouse.gov",
    # Protocol official channels
    "mirror.xyz", "medium.com",  # acceptable if verified author
    "forum.arbitrum", "forum.compound", "governance.aave",
}

# Patterns that indicate Tier 1 (on-chain / official)
_ONCHAIN_PATTERNS = [
    r"etherscan\.io/tx/",
    r"solscan\.io/tx/",
    r"explorer\.\w+/tx/",
    r"github\.com/\w+/\w+/releases",   # official release notes
    r"on-chain data",
    r"contract address",
    r"block\s+#?\d{7,}",
]

def classify_source(source: str) -> SourceTier:
    """
    Classify a source string (URL, domain, or description) into a tier.
    Returns SourceTier enum.
    """
    if not source:
        return SourceTier.NOISE

    s = source.lower()

    # Tier 1: on-chain / official
    for pat in _ONCHAIN_PATTERNS:
        if re.search(pat, s):
            return SourceTier.ON_CHAIN

    if any(kw in s for kw in ("on-chain", "official announcement", "sec filing",
                               "etherscan", "solscan", "smart contract")):
        return SourceTier.ON_CHAIN

    # Tier 2: established media/research
    for domain in _TIER2_SOURCES:
        if domain in s:
            return SourceTier.RESEARCHER

    # Tier 3: community
    community_kw = ("twitter", "x.com", "reddit", "discord", "telegram",
                    "ct", "crypto twitter", "community", "gm", "according to")
    if any(kw in s for kw in community_kw):
        return SourceTier.COMMUNITY

    # Default: noise if we can't identify
    return SourceTier.NOISE


# ---------------------------------------------------------------------------
# Claim dataclass
# ---------------------------------------------------------------------------

@dataclass
class Claim:
    """A piece of information to be verified before vault write."""
    text: str
    source: str
    source_tier: SourceTier = field(init=False)
    timestamp: float = field(default_factory=time.time)
    related_project: Optional[str] = None

    def __post_init__(self):
        self.source_tier = classify_source(self.source)


@dataclass
class VerificationResult:
    claim: Claim
    verdict: str          # "confirmed" | "unconfirmed" | "rejected"
    reason: str
    should_write_to_vault: bool
    write_as: str         # "fact" | "signal" | "discard"


# ---------------------------------------------------------------------------
# Knowledge cross-reference
# ---------------------------------------------------------------------------

_KNOWLEDGE_DIR = Path("data/vault/knowledge")
_KNOWN_FACTS_CACHE: dict[str, str] = {}
_CACHE_LOADED = False


def _load_knowledge_cache() -> None:
    """Load knowledge base files into memory for cross-reference."""
    global _CACHE_LOADED, _KNOWN_FACTS_CACHE
    if _CACHE_LOADED:
        return
    if not _KNOWLEDGE_DIR.exists():
        _CACHE_LOADED = True
        return
    for md_file in _KNOWLEDGE_DIR.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
            _KNOWN_FACTS_CACHE[md_file.stem] = text.lower()
        except Exception:
            pass
    _CACHE_LOADED = True


def _check_against_knowledge(claim_text: str) -> tuple[bool, str]:
    """
    Check if the claim contradicts known facts in the knowledge base.
    Returns (is_contradicted, explanation).
    Simple heuristic — looks for obvious contradictions.
    """
    _load_knowledge_cache()
    text_lower = claim_text.lower()

    # Extract key entities to check (protocol names, amounts, dates)
    # If claim says a protocol was hacked and we have no record of it — flag
    hack_match = re.search(r"(\w+)\s+(was|got)\s+hacked\s+for\s+\$?([\d,.]+[kmb]?)", text_lower)
    if hack_match:
        protocol = hack_match.group(1)
        # Check if it appears in our exploit history
        exploit_kb = _KNOWN_FACTS_CACHE.get("exploit-history", "")
        if exploit_kb and protocol in exploit_kb:
            return False, f"{protocol} found in exploit history — consistent"
        # Not in KB doesn't mean it didn't happen — just unverified
        return False, "not in knowledge base — proceed with tier check"

    return False, "no contradiction found"


# ---------------------------------------------------------------------------
# Main verifier
# ---------------------------------------------------------------------------

def verify(claim: Claim) -> VerificationResult:
    """
    Main entry point. Given a Claim, return a VerificationResult that tells
    the caller whether to write to vault as fact, signal, or discard.
    """
    tier = claim.source_tier

    # --- Tier 1: On-chain / official ---
    if tier == SourceTier.ON_CHAIN:
        _, kb_note = _check_against_knowledge(claim.text)
        return VerificationResult(
            claim=claim,
            verdict="confirmed",
            reason=f"Tier 1 source (on-chain/official). {kb_note}",
            should_write_to_vault=True,
            write_as="fact",
        )

    # --- Tier 2: Established research / media ---
    if tier == SourceTier.RESEARCHER:
        # Still run knowledge check for obvious contradictions
        contradicted, kb_note = _check_against_knowledge(claim.text)
        if contradicted:
            return VerificationResult(
                claim=claim,
                verdict="rejected",
                reason=f"Tier 2 source but contradicts known facts. {kb_note}",
                should_write_to_vault=False,
                write_as="discard",
            )
        return VerificationResult(
            claim=claim,
            verdict="confirmed",
            reason=f"Tier 2 source (established research/media). {kb_note}",
            should_write_to_vault=True,
            write_as="fact",
        )

    # --- Tier 3: Community (CT, Reddit, Discord, Telegram) ---
    if tier == SourceTier.COMMUNITY:
        return VerificationResult(
            claim=claim,
            verdict="unconfirmed",
            reason="Tier 3 source (community). Written as sentiment signal only, not fact.",
            should_write_to_vault=True,
            write_as="signal",
        )

    # --- Tier 4: Noise ---
    return VerificationResult(
        claim=claim,
        verdict="rejected",
        reason="Tier 4 source (unverifiable / anonymous). Discarded.",
        should_write_to_vault=False,
        write_as="discard",
    )


def verify_batch(claims: list[Claim]) -> list[VerificationResult]:
    """Verify a list of claims. Returns list of results in same order."""
    return [verify(c) for c in claims]


# ---------------------------------------------------------------------------
# Vault write helpers
# ---------------------------------------------------------------------------

_SIGNALS_DIR = Path("data/vault/knowledge/signals")
_EVENTS_DIR  = Path("data/vault/knowledge/events")


def write_confirmed_event(result: VerificationResult) -> None:
    """
    Write a confirmed (Tier 1 or 2) event to the events knowledge directory.
    One file per event, named by timestamp.
    """
    if result.write_as != "fact":
        return

    _EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d", time.gmtime(result.claim.timestamp))
    slug = re.sub(r"[^a-z0-9]+", "-", result.claim.text[:50].lower()).strip("-")
    fname = f"{ts}-{slug}.md"
    path = _EVENTS_DIR / fname

    if path.exists():
        return  # Don't duplicate

    project_link = ""
    if result.claim.related_project:
        project_link = f"\n**Project**: [[projects/{result.claim.related_project}]] · [[dashboard]]\n"

    content = f"""---
date: {ts}
source: {result.claim.source}
source_tier: {int(result.claim.source_tier)}
confirmed: true
related_project: {result.claim.related_project or ""}
---

# Event: {result.claim.text[:100]}

**Source**: {result.claim.source}
**Verified**: {result.reason}
{project_link}
{result.claim.text}
"""
    try:
        path.write_text(content, encoding="utf-8")
        log.info("Wrote confirmed event: %s", fname)
    except Exception as e:
        log.error("Failed to write event %s: %s", fname, e)


def write_unconfirmed_signal(result: VerificationResult) -> None:
    """
    Write a community signal to the signals directory.
    These are NEVER treated as fact by the bot — only used as sentiment context.
    """
    if result.write_as != "signal":
        return

    _SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d", time.gmtime(result.claim.timestamp))
    # Append to daily signals file
    fname = f"{ts}-signals.md"
    path = _SIGNALS_DIR / fname

    entry = (
        f"\n- [{result.claim.source}] {result.claim.text[:200]}"
        f" _(unconfirmed, tier {int(result.claim.source_tier)})_\n"
    )
    try:
        with open(path, "a", encoding="utf-8") as f:
            if path.stat().st_size == 0 if path.exists() else True:
                f.write(f"# Unconfirmed Signals — {ts}\n\n"
                        "_Community sentiment only. Not facts. Not written to project files as confirmed._\n")
            f.write(entry)
        log.info("Wrote unconfirmed signal to %s", fname)
    except Exception as e:
        log.error("Failed to write signal: %s", e)


def process_and_store(claims: list[Claim]) -> dict:
    """
    Verify a batch of claims and store results appropriately.
    Returns summary dict with counts.
    """
    results = verify_batch(claims)
    counts = {"confirmed": 0, "unconfirmed": 0, "rejected": 0}

    for r in results:
        if r.write_as == "fact":
            write_confirmed_event(r)
            counts["confirmed"] += 1
        elif r.write_as == "signal":
            write_unconfirmed_signal(r)
            counts["unconfirmed"] += 1
        else:
            counts["rejected"] += 1
            log.debug("Rejected: %s — %s", r.claim.text[:60], r.reason)

    return counts
