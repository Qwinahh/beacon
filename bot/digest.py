"""
Daily digest generator.

Compiles everything the bot did and saw during the day into a readable
summary for Quin. Outputs to:
  1. A markdown file committed to data/digests/YYYY-MM-DD.md
  2. GitHub Actions step summary (GITHUB_STEP_SUMMARY env file)

The digest flags items that scored highly but weren't posted, so Quin
can decide whether to manually intervene the next day.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from bot.sources.alpha import detect_all
from bot.state import State

log = logging.getLogger(__name__)

DIGEST_DIR = Path("data/digests")


def _load_state_raw() -> dict[str, Any]:
    """Read state without wrapping in State class (we just want raw data)."""
    p = Path("data/state.json")
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _format_ts(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%H:%M UTC")


def _build_digest() -> str:
    today   = date.today().isoformat()
    state   = _load_state_raw()
    lines   = [f"# Daily Digest — {today}", ""]

    # --- Posts made today ---
    daily_counts = state.get("daily_counts", {})
    count_today  = daily_counts.get(today, 0)
    lines.append(f"## Posts Made Today: {count_today}")
    lines.append("")

    post_log = state.get("post_log", [])
    today_posts = [p for p in post_log if p.get("date") == today]
    if today_posts:
        for p in today_posts:
            ts_str = _format_ts(p["ts"]) if "ts" in p else "—"
            lines.append(f"- `{ts_str}` [{p.get('kind', '?')} / {p.get('topic', '?')}] — {p.get('title', '')[:80]}")
    else:
        lines.append("*(no post log entries — add post_log tracking to post.py for detail)*")
    lines.append("")

    # --- Alpha signals active right now ---
    lines.append("## 🚨 Live Alpha Signals")
    lines.append("")
    signals = detect_all()
    urgency3 = [s for s in signals if s.urgency == 3]
    urgency2 = [s for s in signals if s.urgency == 2]

    if urgency3:
        lines.append("**Post now:**")
        for s in urgency3[:5]:
            age = f"{s.age_hours:.1f}h ago"
            lines.append(f"- [{s.kind}] {s.title[:90]} *({age})*")
            if s.url:
                lines.append(f"  {s.url}")
        lines.append("")

    if urgency2:
        lines.append("**Worth posting soon:**")
        for s in urgency2[:8]:
            lines.append(f"- [{s.kind}] {s.title[:90]}")
        lines.append("")

    if not urgency3 and not urgency2:
        lines.append("*No high-urgency alpha signals right now.*")
        lines.append("")

    # --- Recent topics (to show coverage) ---
    recent_topics = state.get("recent_topics", [])
    if recent_topics:
        from collections import Counter
        counts = Counter(recent_topics[-30:])
        lines.append("## Topic Coverage (last 30 posts)")
        lines.append("")
        for topic, n in counts.most_common():
            lines.append(f"- {topic}: {n}")
        lines.append("")

    # --- Engagement summary ---
    replied_to = state.get("replied_to", [])
    lines.append(f"## Engagement")
    lines.append("")
    lines.append(f"Total mentions replied to (all time): {len(replied_to)}")
    lines.append("")

    # --- What's in the portfolio ---
    portfolio_posted = state.get("portfolio_posted", [])
    if portfolio_posted:
        lines.append("## Positions Announced")
        lines.append("")
        for key in portfolio_posted[-10:]:
            lines.append(f"- {key}")
        lines.append("")

    # --- Actions for Quin ---
    lines.append("## ⚡ Action Items for You")
    lines.append("")
    if urgency3:
        lines.append(f"- **{len(urgency3)} urgent signal(s)** — consider posting about these manually or updating the bot.")
    if count_today < 3:
        lines.append("- **Low post count today.** Check the Actions log for 'No qualifying candidate' errors.")
    lines.append("- Review `data/portfolio.json` — add any new positions or airdrop farms.")
    lines.append("- If you invested in something new today, update portfolio.json and push.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")

    return "\n".join(lines)


def write_digest() -> str:
    """Generate digest, save it to the repo, and write to GitHub step summary."""
    content = _build_digest()
    today   = date.today().isoformat()

    # Save markdown file.
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"{today}.md"
    path.write_text(content, encoding="utf-8")
    log.info("Digest written to %s", path)

    # Write to GitHub Actions step summary if available.
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(content)
        log.info("Digest written to GitHub step summary.")

    return content
