"""
Suggestion agent — weekly synthesis that surfaces improvement ideas to Quin.

What it does: reads everything the system knows about its own week —
post performance (data/performance/post_log.json), what CT is covering
(data/vault/inspiration/), vault project freshness, portfolio.json
staleness — and writes a structured suggestions report a human can act
on in five minutes.

When it runs: Mondays at 07:00 UTC via .github/workflows/suggest.yml.

Reads:  data/performance/post_log.json, data/vault/inspiration/,
        data/vault/projects/*.md, data/portfolio.json, data/vault/persona.md
Writes: data/suggestions/YYYY-WW.md

Key design decisions:
- Fully deterministic — no LLM call, no API keys required. The value is
  in honest aggregation, not generated prose; this also means the weekly
  report can never fail for quota/key reasons.
- Every suggestion includes the number that motivated it, in the same
  "claims carry data" discipline the persona demands of posts.
"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bot.config import POST_LOG_PATH, PORTFOLIO_PATH, SUGGESTIONS_DIR

log = logging.getLogger(__name__)

_VAULT = Path("data/vault")
_PROJECTS_DIR = _VAULT / "projects"
_INSPIRATION_DIR = _VAULT / "inspiration"
_PERSONA_PATH = _VAULT / "persona.md"

STALE_PROJECT_DAYS = 14
STALE_PORTFOLIO_DAYS = 14


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_post_log() -> list[dict]:
    path = Path(POST_LOG_PATH)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        log.warning("post_log.json unreadable: %s", exc)
        return []


def _posted_ts(entry: dict) -> float:
    try:
        return datetime.fromisoformat(
            str(entry.get("posted_at", "")).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _week_split(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    now = time.time()
    this_week = [e for e in entries if now - _posted_ts(e) <= 7 * 86400]
    last_week = [e for e in entries if 7 * 86400 < now - _posted_ts(e) <= 14 * 86400]
    return this_week, last_week


def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _rate(entries: list[dict], key: str = "engagement_rate") -> float | None:
    return _avg([e[key] for e in entries if e.get(key)])


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

def _format_performance(week: list[dict]) -> list[tuple[str, float, int]]:
    groups: dict[str, list[float]] = defaultdict(list)
    for e in week:
        if e.get("engagement_rate"):
            groups[e.get("format_used", "unknown")].append(e["engagement_rate"])
    return sorted(
        ((f, sum(v) / len(v), len(v)) for f, v in groups.items()),
        key=lambda x: -x[1],
    )


def _stale_projects() -> list[tuple[str, int]]:
    """Projects with no Observation bullet in STALE_PROJECT_DAYS days."""
    out = []
    now = datetime.now(timezone.utc)
    date_re = re.compile(r"\*\*(\d{4}-\d{2}-\d{2})\*\*")
    for path in sorted(_PROJECTS_DIR.glob("*.md")):
        if path.stem in ("general",):
            continue
        try:
            dates = date_re.findall(path.read_text(encoding="utf-8"))
            if not dates:
                continue
            latest = max(datetime.fromisoformat(d).replace(tzinfo=timezone.utc)
                         for d in dates)
            age = (now - latest).days
            if age >= STALE_PROJECT_DAYS:
                out.append((path.stem, age))
        except Exception as exc:
            log.debug("Skipping %s: %s", path.name, exc)
    return sorted(out, key=lambda x: -x[1])


def _portfolio_age_days() -> int | None:
    path = Path(PORTFOLIO_PATH)
    if not path.exists():
        return None
    return int((time.time() - path.stat().st_mtime) // 86400)


def _portfolio_is_empty() -> bool:
    try:
        data = json.loads(Path(PORTFOLIO_PATH).read_text(encoding="utf-8"))
        return not any(data.get(k) for k in ("positions", "airdrops", "watching"))
    except Exception:
        return True


def _inspiration_topics() -> list[str]:
    """Crude topic extraction from the inspiration agent's daily output."""
    topics: list[str] = []
    for name in ("patterns.md", "trending.md"):
        path = _INSPIRATION_DIR / name
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for kw in ("hyperliquid", "ethena", "pendle", "jupiter", "kamino",
                       "berachain", "monad", "polymarket", "babylon", "ondo",
                       "lido", "morpho", "aave", "layerzero", "rwa", "btc",
                       "restaking", "drift", "gmx", "solana"):
                if kw in text and kw not in topics:
                    topics.append(kw)
        except Exception:
            continue
    return topics


def _covered_topics(week: list[dict]) -> set[str]:
    covered = set()
    for e in week:
        blob = f"{e.get('topic', '')} {e.get('tweet_text', '')}".lower()
        covered.update(w for w in blob.split() if len(w) > 3)
    return covered


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report() -> str:
    now = datetime.now(timezone.utc)
    year, week_num, _ = now.isocalendar()

    entries = _load_post_log()
    week, last_week = _week_split(entries)
    measured = [e for e in week if e.get("engagement_rate")]
    fmt_perf = _format_performance(week)
    stale = _stale_projects()
    port_age = _portfolio_age_days()
    insp_topics = _inspiration_topics()
    covered = _covered_topics(week)
    gaps = [t for t in insp_topics if t not in covered]

    lines = [f"# Suggestions — Week {week_num:02d}, {year}", ""]

    # -- What's working -----------------------------------------------------
    lines += ["## What's Working This Week", ""]
    working = []
    if fmt_perf:
        f, v, n = fmt_perf[0]
        working.append(f"- Best format: `{f}` at {v*100:.2f}% avg engagement ({n} posts). Keep its share up.")
    top_posts = sorted(measured, key=lambda e: -(e.get("engagement_rate") or 0))[:2]
    for p in top_posts:
        working.append(
            f"- Top post ({(p.get('engagement_rate') or 0)*100:.2f}% eng, "
            f"{p.get('format_used')}): \"{(p.get('tweet_text') or '')[:80]}\"")
    if len(week) and not measured:
        working.append(f"- {len(week)} posts went out this week — cadence is alive; metrics pending the 24h fetch window.")
    lines += working or ["- Not enough data yet. The tracker needs ~a week of measured posts."]
    lines += [""]

    # -- What needs attention -----------------------------------------------
    lines += ["## What Needs Attention", ""]
    attention = []
    cur, prev = _rate(week), _rate(last_week)
    if cur is not None and prev and cur < prev * 0.7:
        attention.append(
            f"- Engagement rate fell {((prev-cur)/prev)*100:.0f}% WoW "
            f"({prev*100:.2f}% → {cur*100:.2f}%). Review which formats/topics dropped; "
            "check data/vault/knowledge/performance-log.md hour table for timing drift.")
    if fmt_perf and len(fmt_perf) > 1 and fmt_perf[-1][1] < fmt_perf[0][1] * 0.3:
        f, v, n = fmt_perf[-1]
        attention.append(
            f"- Format `{f}` underperforming badly ({v*100:.2f}% over {n} posts) — "
            "reduce its weight or tighten its hook formula (post-structure-science.md).")
    no_metrics = [e for e in entries if e.get("metrics_unavailable")]
    if len(no_metrics) >= 3:
        attention.append(
            f"- {len(no_metrics)} posts have unavailable metrics — check the X API tier "
            "or whether tweets are being deleted.")
    if len(week) < 7:
        attention.append(
            f"- Only {len(week)} posts in 7 days against a 6/day ceiling — the quality "
            "gate may be rejecting too much, or sources are running dry. Check skip logs in data/vault/log/.")
    lines += attention or ["- Nothing flagged."]
    lines += [""]

    # -- Narrative gaps -----------------------------------------------------
    lines += ["## Narrative Gaps", ""]
    if gaps:
        lines += [f"- CT inspiration mentions `{t}` but we haven't posted on it this week" for t in gaps[:6]]
    else:
        lines += ["- No obvious gaps between inspiration topics and our posting."]
    lines += [""]

    # -- Content ideas --------------------------------------------------------
    lines += ["## Content Ideas", ""]
    ideas = []
    for name, age in stale[:2]:
        ideas.append(f"- `{name}` vault entry is {age}d quiet — refresh its data and post the delta as a data_observation.")
    for t in gaps[:2]:
        ideas.append(f"- CT is on `{t}` — check our vault stance and post the angle consensus is missing (X Consensus section).")
    if fmt_perf:
        ideas.append(f"- Double down on `{fmt_perf[0][0]}` (best format this week) against a Recurring Theme from persona.md.")
    ideas.append("- wrong_take_correction sweep: scan circulating stale figures (the vault flags several known ones) and correct one with sources.")
    lines += ideas[:5]
    lines += [""]

    # -- Performance summary ---------------------------------------------------
    lines += ["## Performance Summary", ""]
    lines += [f"- Posts: {len(week)} this week vs {len(last_week)} last week."]
    if cur is not None:
        wow = f" ({((cur-(prev or cur))/(prev or cur))*100:+.0f}% WoW)" if prev else ""
        lines += [f"- Avg engagement rate: {cur*100:.2f}%{wow}."]
    imps = [e.get("impressions") for e in week if e.get("impressions")]
    if imps:
        lines += [f"- Impressions: {sum(imps):,} total, {sum(imps)//len(imps):,} avg."]
    if not measured:
        lines += ["- No measured metrics yet — see data/vault/knowledge/performance-log.md once the tracker has run."]
    lines += [""]

    # -- Actions for Quin -------------------------------------------------------
    lines += ["## Recommended Actions for Quin", ""]
    actions = []
    if _portfolio_is_empty():
        actions.append(
            "- portfolio.json positions/airdrops are empty — add current positions so "
            "diary posts and reply disclosures have real material. This is the single "
            "highest-leverage authenticity input the bot has.")
    elif port_age is not None and port_age >= STALE_PORTFOLIO_DAYS:
        actions.append(
            f"- portfolio.json hasn't changed in {port_age} days — update positions "
            "for more authentic diary posts.")
    if stale:
        name, age = stale[0]
        actions.append(
            f"- {len(stale)} vault projects have no observation in 14+ days "
            f"(oldest: `{name}`, {age}d) — refresh the two you care most about.")
    actions.append(
        "- Skim this week's drafted replies before sending — reply quality is the "
        "growth engine and the only human-gated surface.")
    lines += actions[:3]
    lines += ["", "---", f"*Generated {now.strftime('%Y-%m-%d %H:%M UTC')} by agents/suggestion_agent.py*", ""]

    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    now = datetime.now(timezone.utc)
    year, week_num, _ = now.isocalendar()
    out_dir = Path(SUGGESTIONS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{year}-{week_num:02d}.md"
    out_path.write_text(build_report(), encoding="utf-8")
    log.info("Suggestions written to %s", out_path)


if __name__ == "__main__":
    main()
