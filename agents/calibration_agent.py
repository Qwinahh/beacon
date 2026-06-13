"""
Calibration agent — gives the account a falsifiable track record.

A trader account's credibility comes from being on record and owning the
misses. This agent maintains data/vault/knowledge/calibration-log.md:

  1. Scans the post log for tweets that make a falsifiable prediction
     (future-tense / claim language) and appends them to "## Open Predictions".
  2. Reads the human/bot-resolved entries under "## Resolved" and recomputes
     a "## Scorecard" (hit rate). Resolving an entry is a one-line edit: move
     its bullet to Resolved and tag it `result: right|wrong|partial`.

The bot can then mine "## Resolved" for an honest "here's what I got wrong"
post — one of the highest-trust formats an account can run.

When it runs: weekly via .github/workflows/refresh.yml (or on demand).
Deterministic — no API keys, never crashes the workflow.

Reads:  data/performance/post_log.json
Writes: data/vault/knowledge/calibration-log.md
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("calibration_agent")

try:
    from bot.config import POST_LOG_PATH
except Exception:  # noqa: BLE001 — config may not import in isolation
    POST_LOG_PATH = "data/performance/post_log.json"

LOG_PATH = Path("data/vault/knowledge/calibration-log.md")
MAX_NEW_PER_RUN = 8

# Language that signals a falsifiable claim about the future.
_PREDICTION_RE = re.compile(
    r"\b(will|won't|by (?:q[1-4]|eo[wqy]|year[- ]?end|\d{4})|expect|"
    r"i (?:think|bet)|target|flips?|overtakes?|underperform|outperform|"
    r"going to|ends? the year|hits? \$?\d|reaches? \$?\d|tops? out|bottoms?)\b",
    re.IGNORECASE,
)

_SEED = """\
---
title: Calibration Log
tags: [knowledge, calibration, predictions, track-record]
last_updated: {today}
---

# Calibration Log

Track-record discipline. Every falsifiable call the account makes lands here.
Resolve them honestly. Being wrong on the record and saying so is the most
credible thing a trader account can do, and the account's persona demands it.

How resolution works: when an open prediction's outcome is known, move its
bullet from "Open Predictions" to "Resolved" and add `result: right`,
`result: wrong`, or `result: partial` plus a one-line note. The Scorecard is
recomputed automatically.

## Scorecard
<!-- Auto-generated. Do not edit by hand. -->
- Resolved: 0 | right 0 | wrong 0 | partial 0 | hit rate: n/a

## Open Predictions
<!-- Auto-appended from the post log. -->

## Resolved
<!-- Tag each with result: right | wrong | partial -->
- **2026-06-07** — Hyperliquid's USDC-yield buyback (AQA v2, 90% from Oct 3) makes HYPE one of the few revenue-backed majors; it should outperform non-revenue perps tokens through 2026. result: open — *seed thesis, resolve at year-end*
"""


def _load_log() -> str:
    if LOG_PATH.exists():
        return LOG_PATH.read_text(encoding="utf-8")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = _SEED.format(today=date.today().isoformat())
    LOG_PATH.write_text(text, encoding="utf-8")
    log.info("Seeded calibration-log.md")
    return text


def _section(body: str, heading: str) -> str:
    m = re.search(rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    return m.group(1) if m else ""


def _replace_section(body: str, heading: str, content: str) -> str:
    block = f"## {heading}\n{content.rstrip()}\n"
    pattern = rf"## {re.escape(heading)}\n.*?(?=\n## |\Z)"
    if re.search(pattern, body, re.DOTALL):
        return re.sub(pattern, block, body, flags=re.DOTALL)
    return body.rstrip() + "\n\n" + block


def _load_posts() -> list[dict]:
    p = Path(POST_LOG_PATH)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("posts", [])
    except Exception as exc:  # noqa: BLE001
        log.warning("post log unreadable: %s", exc)
        return []


def run() -> dict:
    body = _load_log()

    open_sec = _section(body, "Open Predictions")
    resolved_sec = _section(body, "Resolved")
    known_ids = set(re.findall(r"tweet\s+(\d+)", open_sec + resolved_sec))

    # 1. Append new predictions from the post log.
    new_lines = []
    for post in _load_posts():
        tid = str(post.get("tweet_id") or post.get("id") or "")
        text = (post.get("text") or post.get("tweet") or "").strip()
        if not tid or tid in known_ids or not text:
            continue
        if _PREDICTION_RE.search(text):
            when = (post.get("date") or str(post.get("posted_at", "")))[:10] or date.today().isoformat()
            snippet = text.replace("\n", " ")[:180]
            new_lines.append(f"- **{when}** — {snippet} — tweet {tid} — resolve by: TBD")
            known_ids.add(tid)
        if len(new_lines) >= MAX_NEW_PER_RUN:
            break

    if new_lines:
        open_sec = (open_sec.rstrip() + "\n" + "\n".join(new_lines)).strip() + "\n"
        body = _replace_section(body, "Open Predictions", open_sec)

    # 2. Recompute scorecard from Resolved results.
    # Strip the instructional HTML comment so its "result: right | wrong | partial"
    # example is not miscounted as a real resolved entry.
    resolved_clean = re.sub(r"<!--.*?-->", "", resolved_sec, flags=re.DOTALL)
    results = re.findall(r"result:\s*(right|wrong|partial)\b", resolved_clean, re.IGNORECASE)
    counts = {k: sum(1 for r in results if r.lower() == k) for k in ("right", "wrong", "partial")}
    total = sum(counts.values())
    hit = f"{counts['right'] / total * 100:.0f}%" if total else "n/a"
    scorecard = (
        "<!-- Auto-generated. Do not edit by hand. -->\n"
        f"- Resolved: {total} | right {counts['right']} | wrong {counts['wrong']} "
        f"| partial {counts['partial']} | hit rate: {hit}"
    )
    body = _replace_section(body, "Scorecard", scorecard)

    body = re.sub(r"(?m)^last_updated:.*$", f"last_updated: {date.today().isoformat()}", body, count=1)
    LOG_PATH.write_text(body, encoding="utf-8")
    log.info("calibration: +%d open, %d resolved (hit rate %s)", len(new_lines), total, hit)
    return {"new_open": len(new_lines), "resolved": total, "hit_rate": hit}


if __name__ == "__main__":
    run()
