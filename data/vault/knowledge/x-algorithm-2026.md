---
title: X Algorithm 2026 — How For You Ranking Actually Works
type: knowledge
topic: x-algorithm
tags: [knowledge, x-strategy, algorithm]
confirmed: true
source: data/research/x-algorithm.md (compiled 2026-06-12; primary sources incl. github.com/xai-org/x-algorithm)
last_updated: 2026-06-12
updated: 2026-06-12
---

# X Algorithm 2026 — How For You Ranking Actually Works

*Operational guide for the writer and orchestrator. Full citations in
`data/research/x-algorithm.md`. Re-verify monthly — xAI updates the
open-source repo roughly every 4 weeks.*

## The system (since Jan 2026)

xAI open-sourced the current algorithm (github.com/xai-org/x-algorithm,
Jan 20, 2026). For You is now: **Home Mixer** (orchestration) → **Thunder**
(in-network candidates) → **Phoenix**, a Grok-based transformer that
predicts per-user probabilities for every action — favorite, reply,
repost, quote, click, profile_click, photo_expand, dwell, follow_author,
not_interested, block, mute, report. Final score = Σ(weight × P(action)).
Hand-engineered features are gone; negative actions carry negative
weights. The Following feed is also ranked now (since ~Nov 2025), not
chronological.

## Signal weights (legacy values, directionally current)

Explicit numbers are from X Engineering's Sep 2025 restatement; Phoenix
learns weights internally now, but the ordering holds:

| Signal | Weight |
|---|---|
| Reply that the author engages with | **+75** (150x a like) |
| Reply | **+13.5** |
| Profile click → like/reply | +12.0 |
| Conversation click + reply/like | +11 |
| Conversation click + dwell ≥2min | +10 |
| Bookmark | ~10x a like (estimate) |
| Retweet | +1.0 |
| Like | +0.5 |
| Negative feedback (mute/block/show-less) | ~−74 |
| Report | ~**−369** |

Operational ordering: **author-engaged replies >> replies > profile
clicks ≈ dwell >> bookmarks > RTs > likes.** One report erases hundreds
of likes. Write to provoke replies and dwell, never to fish for likes.

## Posting frequency

- 3-5 posts/day optimum; per-post engagement decays steeply past ~7
- Code-confirmed dilution: the **Author Diversity Scorer** attenuates repeated authors within one feed load — your posts compete with each other
- Post half-life ~15-30 min: space posts across peak windows, never burst
- Viral posts grant a temporary boost to subsequent posts — follow up a winner within hours

## Spam / suppression (what the bot must never do)

Penalties accrue to a persistent **account reputation score**, not per-post.
Suppression labels: low-quality, spam, toxicity, untrusted URL, NSFW,
**repeatedly @mentioning the same handle**. Specifics:

- "Offensive" text: ~80% reach reduction; ALL CAPS penalized
- May 2026 **Grox** classifiers target templated/repeated formats and engagement bait — format rotation is now an algorithmic requirement, not a style preference
- Duplicate/near-duplicate posts filtered at serve time
- Hashtags are vestigial; >1-2 correlates with reduced reach — we use zero
- Follow-churn triggers platform-manipulation limits
- Reply farming with templated takes is exactly what Grox profiles — every reply must be post-specific

## Premium

- Premium ≈ **10x median reach** vs free accounts (Buffer, 18M posts); legacy multipliers ~4x in-network / ~2x out-of-network
- Premium replies rank above non-verified replies; Premium+ tops reply stacks
- Free-account link posts: near-zero median engagement since Mar 2025
- Verdict: Premium is mandatory infrastructure for this account

## Format performance

- **Text posts slightly beat images** on median engagement (~0.9% for Premium accounts) — text-only is never a handicap
- Images earn their place via **dwell + photo_expand**: dense data charts and annotated screenshots that invite tap-to-expand have a real scoring path; decorative images don't
- 2-4 image posts can beat single images (dwell)
- **Long-form single posts out-reach classic threads** (Hootsuite experiment); later thread tweets see steep drop-off. Thread only when each tweet can earn its own engagement; otherwise one long post or post + reply chain
- Video >10s watch time gets outsized boost — not our format yet

## Replies (the growth engine)

- Replies rank under posts by predicted engagement; Premium preferred
- An author-engaged reply inherits the +75-class signal AND feeds your distribution to that author's audience — the single highest-leverage action available to a small account
- DedupConversationFilter surfaces only the strongest branch of a reply chain — be the best reply, not the fifth-best
- Early + substantive + non-templated. Vary targets (repeat-@ is a suppression label)

## Links

- Oct 14, 2025: Nikita Bier announced removal of the link penalty + in-app browser test
- Dwell mechanics still favor native content; 2026 consensus: link in first reply, or link + full native summary
- Bot rule: never bare-link. A/B our own data before trusting the penalty removal

## What this means for the writer

1. Optimize for replies and dwell. A post someone argues with beats a post someone likes.
2. Rotate formats — Grox profiles templates. Same format twice in a row is now a suppression risk, not just a style miss.
3. Topic consistency > format tricks: Phoenix is personalization-heavy, so a coherent audience cluster engaging repeatedly matters more than any single banger.
4. Never post anything that risks a report. −369 is unrecoverable at our size.

---

→ [[index]] · [[knowledge/post-structure-science]] · [[knowledge/reply-strategy]] · [[knowledge/x-growth-strategy]]