"""
agents/growth_agent.py — Weekly growth analysis agent.

Runs after metric collection, analyses what's working, and writes a report
to the Obsidian vault. Updates a growth_context.json that the orchestrator
reads to bias format and topic selection toward what's actually performing.

This is the feedback loop that makes the bot self-improving over time:
  Post → Collect metrics → Analyse → Adjust orchestrator weights → Better posts

Run via: python -m agents.growth_agent
Or from growth.yml GitHub Actions (weekly).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_GROWTH_DIR     = Path("data/growth")
_CONTEXT_FILE   = _GROWTH_DIR / "growth_context.json"
_REPORT_DIR     = Path("data/vault/growth")


def _load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _analyse_metrics() -> dict:
    """Read metrics.json and compute what's working."""
    from bot.sources.x_metrics import get_best_formats, get_best_topics, _load_json as load_m

    metrics_path = _GROWTH_DIR / "metrics.json"
    all_metrics = load_m(metrics_path)
    if not isinstance(all_metrics, dict) or not all_metrics:
        return {"status": "no_data", "message": "No tweet metrics collected yet."}

    records = list(all_metrics.values())
    real_records = [r for r in records if not r.get("metrics", {}).get("is_estimated")]

    if len(real_records) < 5:
        return {
            "status": "insufficient_data",
            "message": f"Only {len(real_records)} posts with real metrics. Need 5+ to analyse.",
            "total_tracked": len(records),
        }

    # Aggregate
    total_posts      = len(real_records)
    total_impressions = sum(r["metrics"].get("impressions", 0) for r in real_records)
    total_replies    = sum(r["metrics"].get("replies",     0) for r in real_records)
    total_likes      = sum(r["metrics"].get("likes",       0) for r in real_records)
    total_bookmarks  = sum(r["metrics"].get("bookmarks",   0) for r in real_records)
    avg_impressions  = total_impressions / total_posts if total_posts else 0

    # Engagement rate = (replies + bookmarks) / impressions — the most meaningful signal
    eng_rates = []
    for r in real_records:
        imp = r["metrics"].get("impressions", 0)
        if imp > 0:
            eng_rate = (r["metrics"].get("replies", 0) + r["metrics"].get("bookmarks", 0)) / imp
            eng_rates.append(eng_rate)
    avg_eng_rate = sum(eng_rates) / len(eng_rates) if eng_rates else 0

    best_formats = get_best_formats(min_posts=2)
    best_topics  = get_best_topics(min_posts=2)

    # Find single best post
    best_post = max(
        real_records,
        key=lambda r: r["metrics"].get("impressions", 0),
    )

    # Find worst post
    worst_post = min(
        (r for r in real_records if r["metrics"].get("impressions", 0) > 0),
        key=lambda r: r["metrics"].get("impressions", 0),
        default=None,
    )

    return {
        "status": "ok",
        "total_posts": total_posts,
        "total_impressions": total_impressions,
        "avg_impressions": round(avg_impressions, 0),
        "avg_engagement_rate": round(avg_eng_rate * 100, 3),
        "total_replies": total_replies,
        "total_likes": total_likes,
        "total_bookmarks": total_bookmarks,
        "best_formats": best_formats[:5],
        "best_topics": best_topics[:5],
        "best_post": {
            "text":        best_post.get("text", ""),
            "format":      best_post.get("format", ""),
            "topic":       best_post.get("topic", ""),
            "impressions": best_post["metrics"].get("impressions", 0),
            "replies":     best_post["metrics"].get("replies", 0),
        },
        "worst_post": {
            "text":        worst_post.get("text", "") if worst_post else "",
            "format":      worst_post.get("format", "") if worst_post else "",
            "impressions": worst_post["metrics"].get("impressions", 0) if worst_post else 0,
        } if worst_post else None,
    }


def _build_growth_context(analysis: dict) -> dict:
    """
    Build the growth_context.json that the orchestrator reads.
    This directly influences what formats and topics the bot favours.
    """
    ctx = {
        "updated_at": time.time(),
        "status":     analysis.get("status", "no_data"),
    }

    if analysis["status"] != "ok":
        return ctx

    best_formats = analysis.get("best_formats", [])
    best_topics  = analysis.get("best_topics",  [])

    # Preferred formats: top 3 by engagement rate
    ctx["preferred_formats"] = [f["format"] for f in best_formats[:3]]

    # Preferred topics: top 3 by reach
    ctx["preferred_topics"] = [t["topic"] for t in best_topics[:3]]

    # Avoid formats: bottom performer (if we have enough data)
    if len(best_formats) >= 4:
        ctx["deprioritise_format"] = best_formats[-1]["format"]

    # Performance headline
    ctx["avg_impressions"] = analysis.get("avg_impressions", 0)
    ctx["avg_engagement_rate_pct"] = analysis.get("avg_engagement_rate", 0)

    # Growth advice for the orchestrator to read
    advice = []
    if ctx.get("preferred_formats"):
        advice.append(
            f"Recent data shows {ctx['preferred_formats'][0]} performs best. "
            "Prefer this format when content fits."
        )
    if ctx.get("preferred_topics"):
        advice.append(
            f"Top performing topics: {', '.join(ctx['preferred_topics'])}. "
            "These consistently reach more people."
        )
    if analysis.get("avg_impressions", 0) < 500:
        advice.append(
            "Average impressions are low. Reduce posting frequency, increase specificity. "
            "Quality over volume."
        )
    if analysis.get("avg_engagement_rate", 0) > 2.0:
        advice.append(
            "Engagement rate is strong (>2%). Current content strategy is working. "
            "Keep format variety and don't reduce quality gate."
        )

    ctx["orchestrator_advice"] = advice
    return ctx


def _write_vault_report(analysis: dict) -> None:
    """Write a human-readable growth report to the Obsidian vault."""
    if analysis["status"] != "ok":
        return

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    date_str  = time.strftime("%Y-%m-%d")
    report_path = _REPORT_DIR / f"growth-report-{date_str}.md"

    best_fmt_lines = "\n".join(
        f"- **{f['format']}** — {f['avg_engagement_rate']*100:.2f}% eng rate "
        f"({f['sample_size']} posts)"
        for f in analysis.get("best_formats", [])[:5]
    ) or "- No data yet"

    best_topic_lines = "\n".join(
        f"- **{t['topic']}** — {t['avg_impressions']:.0f} avg impressions "
        f"({t['sample_size']} posts)"
        for t in analysis.get("best_topics", [])[:5]
    ) or "- No data yet"

    best_post = analysis.get("best_post", {})
    worst_post = analysis.get("worst_post", {})

    content = f"""---
type: growth-report
date: {date_str}
total_posts: {analysis.get("total_posts", 0)}
avg_impressions: {analysis.get("avg_impressions", 0):.0f}
avg_engagement_rate_pct: {analysis.get("avg_engagement_rate", 0):.3f}
---

# Growth Report — {date_str}

## Account Performance

| Metric | Value |
|--------|-------|
| Posts analysed | {analysis.get("total_posts", 0)} |
| Total impressions | {analysis.get("total_impressions", 0):,} |
| Avg impressions/post | {analysis.get("avg_impressions", 0):,.0f} |
| Avg engagement rate | {analysis.get("avg_engagement_rate", 0):.3f}% |
| Total replies | {analysis.get("total_replies", 0)} |
| Total likes | {analysis.get("total_likes", 0)} |
| Total bookmarks | {analysis.get("total_bookmarks", 0)} |

## Format Performance

{best_fmt_lines}

## Topic Performance

{best_topic_lines}

## Best Performing Post

> "{best_post.get("text", "N/A")}"

- Format: {best_post.get("format", "N/A")}
- Topic: {best_post.get("topic", "N/A")}
- Impressions: {best_post.get("impressions", 0):,}
- Replies: {best_post.get("replies", 0)}

## Lowest Performing Post

> "{worst_post.get("text", "N/A") if worst_post else "N/A"}"

- Impressions: {worst_post.get("impressions", 0) if worst_post else 0:,}

## What to Do Next

{"  ".join("- " + a for a in _build_growth_context(analysis).get("orchestrator_advice", ["Keep posting and collecting data."]))}

---
*Generated by growth_agent.py | [[x-growth-strategy]] | [[dashboard]]*
"""
    report_path.write_text(content, encoding="utf-8")
    log.info("Growth report written to %s", report_path)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_growth_cycle() -> dict:
    """
    Full growth analysis cycle:
    1. Trigger metric collection for any pending posts
    2. Analyse what's working
    3. Update growth_context.json (read by orchestrator)
    4. Write vault report
    """
    log.info("Starting growth analysis cycle.")

    # Step 1: Pull fresh metrics
    try:
        from bot.sources.x_metrics import update_metrics
        metric_result = update_metrics()
        log.info("Metrics updated: %s", metric_result)
    except Exception as exc:
        log.warning("Metric collection failed (non-fatal): %s", exc)
        metric_result = {"error": str(exc)}

    # Step 2: Analyse
    analysis = _analyse_metrics()
    log.info("Analysis status: %s", analysis.get("status"))

    # Step 3: Update orchestrator context
    ctx = _build_growth_context(analysis)
    _save_json(_CONTEXT_FILE, ctx)

    # Step 4: Write vault report
    _write_vault_report(analysis)

    return {
        "metric_update": metric_result,
        "analysis":      analysis,
        "context_updated": True,
    }


def get_growth_context_for_orchestrator() -> str:
    """
    Return a compact string the orchestrator injects into its system prompt.
    Called on every posting cycle to bias format/topic selection.
    """
    ctx = _load_json(_CONTEXT_FILE)
    if not isinstance(ctx, dict) or ctx.get("status") == "no_data":
        return ""

    parts = ["## Growth Performance Context (from recent posts)"]

    preferred = ctx.get("preferred_formats", [])
    if preferred:
        parts.append(f"Best performing formats: {', '.join(preferred)}")

    topics = ctx.get("preferred_topics", [])
    if topics:
        parts.append(f"Best performing topics: {', '.join(topics)}")

    deprioritise = ctx.get("deprioritise_format")
    if deprioritise:
        parts.append(f"Avoid overusing: {deprioritise} (lowest recent engagement)")

    avg_imp = ctx.get("avg_impressions", 0)
    if avg_imp > 0:
        parts.append(f"Recent avg impressions/post: {avg_imp:,.0f}")

    for advice in ctx.get("orchestrator_advice", []):
        parts.append(f"→ {advice}")

    return "\n".join(parts)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_growth_cycle()
    print(json.dumps(result, indent=2, default=str))
