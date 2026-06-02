"""
4-tier fact-checking verifier.

Every piece of information is assigned a confidence tier before it can
appear in a post as a stated fact.

  Tier 1 — On-chain / primary data:  DeFiLlama, CoinGecko, block explorers.
            Highest trust. Numbers here are facts. State directly.
  Tier 2 — Research / credible press: CoinDesk, The Block, Blockworks, etc.
            High trust. State as fact, optionally attribute the source.
  Tier 3 — Community:  Reddit, Telegram, Discord, LunarCrush, X crowd.
            Low trust. Surface as "community thesis" or "people are saying".
            NEVER write as a confirmed fact.
  Tier 4 — Noise:  Price predictions, "analyst says", "could reach $X", etc.
            Reject entirely. Never written.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import IntEnum


class Tier(IntEnum):
    ON_CHAIN  = 1
    RESEARCH  = 2
    COMMUNITY = 3
    NOISE     = 4


_ON_CHAIN_SOURCES = {
    "defillama", "coingecko", "etherscan", "solscan", "arbiscan",
    "hyperliquid", "dune", "nansen", "defillama_ctx",
}

_RESEARCH_SOURCES = {
    "coindesk", "the defiant", "the block", "blockworks", "dl news",
    "messari", "kaito", "decrypt", "rss",
}

_COMMUNITY_SOURCES = {
    "reddit", "telegram", "discord", "lunarcrush", "twitter", "x",
    "xcontext",
}

_NOISE_PATTERNS = [
    r"price prediction",
    r"could reach \$",
    r"might hit \$",
    r"set to (?:moon|pump|explode|surge|skyrocket)",
    r"analyst says",
    r"experts predict",
    r"\d+x (?:gains|returns|profit)",
    r"guaranteed (?:returns|profit|gains)",
    r"top \d+ (?:reasons|coins|cryptos)",
    r"you need to know",
]

_NOISE_RE = re.compile("|".join(_NOISE_PATTERNS), re.IGNORECASE)


@dataclass
class VerifiedItem:
    text: str
    source: str
    tier: Tier
    added_at: float = field(default_factory=time.time)
    raw: bool = False


def _classify_source(source: str) -> Tier:
    s = source.lower().strip()
    if s in _ON_CHAIN_SOURCES:
        return Tier.ON_CHAIN
    if s in _RESEARCH_SOURCES:
        return Tier.RESEARCH
    if s in _COMMUNITY_SOURCES:
        return Tier.COMMUNITY
    return Tier.COMMUNITY


class Verifier:
    """Collects signals and classifies them by confidence tier."""

    def __init__(self) -> None:
        self._items: list[VerifiedItem] = []

    def add(self, text: str, source: str, raw: bool = False) -> VerifiedItem:
        """Add a signal. Noise patterns override source classification."""
        tier = Tier.NOISE if _NOISE_RE.search(text) else _classify_source(source)
        item = VerifiedItem(text=text, source=source, tier=tier, raw=raw)
        self._items.append(item)
        return item

    def add_many(self, texts: list[str], source: str) -> list[VerifiedItem]:
        return [self.add(t, source) for t in texts]

    # ------------------------------------------------------------------
    # Tier accessors
    # ------------------------------------------------------------------

    def tier1(self) -> list[VerifiedItem]:
        return [i for i in self._items if i.tier == Tier.ON_CHAIN]

    def tier2(self) -> list[VerifiedItem]:
        return [i for i in self._items if i.tier == Tier.RESEARCH]

    def tier3(self) -> list[VerifiedItem]:
        return [i for i in self._items if i.tier == Tier.COMMUNITY]

    def tier4(self) -> list[VerifiedItem]:
        return [i for i in self._items if i.tier == Tier.NOISE]

    def confirmed_facts(self) -> list[VerifiedItem]:
        """Tier 1+2 items — safe to state as facts in posts."""
        return [i for i in self._items if i.tier <= Tier.RESEARCH]

    def community_signals(self) -> list[VerifiedItem]:
        """Tier 3 — surface as sentiment, never as confirmed fact."""
        return [i for i in self._items if i.tier == Tier.COMMUNITY]

    def rejected(self) -> list[VerifiedItem]:
        """Tier 4 — noise. Do not use."""
        return [i for i in self._items if i.tier == Tier.NOISE]

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def summary(self) -> str:
        return (
            f"Tier 1 (on-chain): {len(self.tier1())} | "
            f"Tier 2 (research): {len(self.tier2())} | "
            f"Tier 3 (community): {len(self.community_signals())} | "
            f"Tier 4 (noise, rejected): {len(self.rejected())}"
        )

    def to_context_block(self) -> str:
        """Format for injection into the writer context."""
        parts: list[str] = []

        facts = self.confirmed_facts()
        if facts:
            parts.append("## Confirmed Market Facts (on-chain + research)")
            for item in facts:
                parts.append(f"- [{item.source}] {item.text}")

        community = self.community_signals()
        if community:
            parts.append("\n## Community Signals (NOT confirmed facts)")
            parts.append("*Treat as community narrative. Never state as confirmed.*")
            for item in community[:5]:
                parts.append(f"- [{item.source}] {item.text}")

        return "\n".join(parts)
