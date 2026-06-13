"""
Market updater — keeps the vault's project files current with live data.

What it does: for each protocol in PROJECT_FEEDS, pulls live TVL (DeFiLlama)
and price (CoinGecko), then writes the numbers into the project's markdown
file in two places:
  1. Frontmatter fields (tvl_usd, price_usd, price_change_24h, metrics_updated)
     so the Obsidian Dataview dashboard can sort/filter on live numbers.
  2. A single, replaceable "## Live Metrics" section so a human (or the
     writer's context builder) sees the latest snapshot without scrolling
     through observation history.

Why a replaceable section, not an observation bullet: observations are the
bot's dated qualitative notes and should stay sparse and meaningful. Raw
metric snapshots would bury them in noise. So metrics live in their own
section that gets overwritten each run; genuine state changes still get
logged as observations by the learner agent.

When it runs: daily via .github/workflows/refresh.yml (06:30 UTC, after the
performance tracker, before the first posting window).

Reads:  data/vault/projects/*.md, DeFiLlama + CoinGecko (free, no keys)
Writes: data/vault/projects/<name>.md (frontmatter + Live Metrics section)

Design decisions:
- Degrades gracefully: a wrong slug, a down API, or a missing file is logged
  and skipped. The agent never raises, so it can never break the workflow.
- Wrong DeFiLlama slugs simply return no TVL (the source returns None), so the
  mapping below is best-effort and safe to extend without fear of crashes.
- Adding a protocol is one line in PROJECT_FEEDS. The file stem must match the
  vault filename (data/vault/projects/<stem>.md).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("market_updater")

PROJ_DIR = Path("data/vault/projects")

# stem -> {"slug": DeFiLlama protocol slug, "coin": CoinGecko id (or symbol)}.
# Either field may be omitted. Slugs/ids are best-effort; failures are skipped.
PROJECT_FEEDS: dict[str, dict[str, str]] = {
    "hyperliquid": {"slug": "hyperliquid",      "coin": "hyperliquid"},
    "ethena":      {"slug": "ethena",           "coin": "ethena"},
    "aave":        {"slug": "aave",             "coin": "aave"},
    "pendle":      {"slug": "pendle",           "coin": "pendle"},
    "gmx":         {"slug": "gmx",              "coin": "gmx"},
    "lido":        {"slug": "lido",             "coin": "lido-dao"},
    "morpho":      {"slug": "morpho",           "coin": "morpho"},
    "ondo":        {"slug": "ondo-finance",     "coin": "ondo-finance"},
    "jupiter":     {"slug": "jupiter",          "coin": "jupiter-exchange-solana"},
    "kamino":      {"slug": "kamino",           "coin": "kamino"},
    "drift":       {"slug": "drift",            "coin": "drift-protocol"},
}


# ---------------------------------------------------------------------------
# Minimal, self-contained markdown helpers (no dependency on vault internals)
# ---------------------------------------------------------------------------

def _split_frontmatter(text: str) -> tuple[list[str], str]:
    """Return (frontmatter_lines_without_fences, body). Empty list if none."""
    if not text.startswith("---"):
        return [], text
    end = text.find("\n---", 3)
    if end == -1:
        return [], text
    fm = text[3:end].strip("\n").splitlines()
    body = text[end + 4:].lstrip("\n")
    return fm, body


def _set_fm_field(fm_lines: list[str], key: str, value: str) -> list[str]:
    """Set or replace a `key: value` line in frontmatter lines."""
    out, found = [], False
    for line in fm_lines:
        if re.match(rf"\s*{re.escape(key)}\s*:", line):
            out.append(f"{key}: {value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}: {value}")
    return out


def _replace_section(body: str, heading: str, content: str) -> str:
    """Replace a '## heading' section's content, or append the section."""
    block = f"## {heading}\n{content.rstrip()}\n"
    pattern = rf"## {re.escape(heading)}\n.*?(?=\n## |\Z)"
    if re.search(pattern, body, re.DOTALL):
        return re.sub(pattern, block, body, flags=re.DOTALL)
    return body.rstrip() + "\n\n" + block


def _fmt_usd(n: Optional[float]) -> str:
    if n is None:
        return "n/a"
    a = abs(n)
    if a >= 1e9:
        return f"${n/1e9:.2f}B"
    if a >= 1e6:
        return f"${n/1e6:.1f}M"
    if a >= 1e3:
        return f"${n/1e3:.1f}K"
    return f"${n:,.2f}"


# ---------------------------------------------------------------------------
# Data fetch (graceful)
# ---------------------------------------------------------------------------

def _fetch_tvl(slug: str) -> Optional[dict]:
    try:
        from bot.sources.defillama_ctx import get_protocol_tvl
        return get_protocol_tvl(slug)
    except Exception as exc:  # noqa: BLE001
        log.warning("TVL fetch failed for %s: %s", slug, exc)
        return None


def _fetch_price(coin: str) -> Optional[dict]:
    try:
        from bot.sources.coingecko import get_price
        return get_price(coin)
    except Exception as exc:  # noqa: BLE001
        log.warning("Price fetch failed for %s: %s", coin, exc)
        return None


def _num(d: Optional[dict], *keys) -> Optional[float]:
    """First numeric value found across candidate keys in a dict."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


# ---------------------------------------------------------------------------
# Per-project update
# ---------------------------------------------------------------------------

def update_project(stem: str, feed: dict[str, str]) -> bool:
    path = PROJ_DIR / f"{stem}.md"
    if not path.exists():
        log.info("Skip %s: no vault file.", stem)
        return False

    tvl_data   = _fetch_tvl(feed["slug"]) if feed.get("slug") else None
    price_data = _fetch_price(feed["coin"]) if feed.get("coin") else None

    tvl        = _num(tvl_data, "tvl", "current_tvl", "totalLiquidityUSD")
    price      = _num(price_data, "price", "usd", "current_price")
    chg24      = _num(price_data, "change_24h", "usd_24h_change", "price_change_percentage_24h")

    if tvl is None and price is None:
        log.info("Skip %s: no live data returned.", stem)
        return False

    text = path.read_text(encoding="utf-8")
    fm_lines, body = _split_frontmatter(text)
    today = date.today().isoformat()

    if tvl is not None:
        fm_lines = _set_fm_field(fm_lines, "tvl_usd", f"{tvl:.0f}")
    if price is not None:
        fm_lines = _set_fm_field(fm_lines, "price_usd", f"{price:.4f}".rstrip("0").rstrip("."))
    if chg24 is not None:
        fm_lines = _set_fm_field(fm_lines, "price_change_24h", f"{chg24:.1f}")
    fm_lines = _set_fm_field(fm_lines, "metrics_updated", today)

    # Build the replaceable Live Metrics section.
    rows = []
    if tvl is not None:
        rows.append(f"- TVL: {_fmt_usd(tvl)}")
    if price is not None:
        chg = f" ({chg24:+.1f}% 24h)" if chg24 is not None else ""
        rows.append(f"- Price: ${price:,.4f}".rstrip("0").rstrip(".") + chg)
    rows.append(f"- Snapshot: {today} (auto, DeFiLlama + CoinGecko)")
    section = "\n".join(rows)

    new_body = _replace_section(body, "Live Metrics", section)
    new_text = "---\n" + "\n".join(fm_lines) + "\n---\n\n" + new_body.lstrip("\n")
    path.write_text(new_text, encoding="utf-8")
    log.info("Updated %s: TVL=%s price=%s", stem, _fmt_usd(tvl), price)
    return True


def run() -> int:
    if not PROJ_DIR.exists():
        log.warning("No projects dir at %s", PROJ_DIR)
        return 0
    updated = 0
    for stem, feed in PROJECT_FEEDS.items():
        try:
            if update_project(stem, feed):
                updated += 1
        except Exception as exc:  # noqa: BLE001 — never break the workflow
            log.warning("update_project(%s) errored: %s", stem, exc)
    log.info("market_updater: %d/%d project files updated.", updated, len(PROJECT_FEEDS))
    return updated


if __name__ == "__main__":
    run()
