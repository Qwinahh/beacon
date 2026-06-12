---
title: Post Structure Science — Format Playbook
type: knowledge
topic: post-formats
tags: [knowledge, x-strategy, formats, writing]
confirmed: true
source: data/research/ct-accounts.md + data/research/x-algorithm.md (2026-06-12)
last_updated: 2026-06-12
updated: 2026-06-12
---

# Post Structure Science — Format Playbook

*Format-by-format guide for the writer. Real examples from
`data/research/ct-accounts.md`; algorithm mechanics from
[[knowledge/x-algorithm-2026]].*

## Universal rules first

- **Numbers in the first line beat adjectives.** "671k $ETH = $3.2B in the unstaking queue" (@DefiIgnas) outperforms any adjective-led opener. Every format below front-loads a number or a named mechanic.
- **One line per sentence, white space everywhere.** All six benchmark accounts write in short lines with hard breaks. No paragraphs.
- **$CASHTAGS yes, hashtags never.** None of the top six use hashtags. Zero.
- **Never the same format twice in a row.** Two reasons: audiences skim predictable accounts (engagement decay), and the May 2026 Grox spam classifiers profile repeated templates — format repetition is now an algorithmic suppression risk, not just a style miss. The orchestrator enforces rotation.

## Format reference

### data_observation
- **When:** fresh on-chain/market data with a non-obvious implication. Our bread and butter.
- **Hook formula:** [specific number + asset] → [one-sentence implication] → [optional: what I'm watching next].
- **Length:** under 200 chars when possible. Drives: **bookmarks + replies**.
- **Real example:** "1/ Record number of $ETH is in the unstaking queue: 671k $ETH = $3.2B USD... Why is it happening? A few reasons:" — @DefiIgnas (Aug 2025).

### contrarian
- **When:** the data contradicts what CT is saying. Requires receipts — a number, not a mood.
- **Hook formula:** [what everyone believes, stated fairly] → [the number that breaks it] → [what's actually happening].
- **Length:** 200-270 chars. Drives: **replies** (people argue) + profile clicks.
- **Real example:** "Why is USDC's supply decreasing? USDC dropped from $55B to $35B. Yet USDT increased from $84B to $120B... it's weird this isn't discussed more on X." — @DefiIgnas (Sep 2024).

### position_update
- **When:** we entered/exited/changed something documented in portfolio.json. First person, honest, includes the uncomfortable part.
- **Hook formula:** [what I did] → [why, with a number] → [what invalidates it].
- **Drives: trust + follows** (skin in the game is the #1 trust signal across all six accounts).
- **Real example:** "I was sizing up until March when I round tripped an 8m profit into a loss in April... Then I essentially reduced by 90%." — @Pentosh1 (Dec 2022). Losses disclosed > wins bragged.

### callout
- **When:** something doesn't add up — tokenomics math, "fair launch" claims, stale TVL figures circulating. Dry and flat, never outraged.
- **Hook formula:** [the claim] → [the number that contradicts it] → [deadpan one-liner, optional].
- **Drives: replies + RTs.** Highest virality, highest risk — must be verifiably correct.
- **Real example:** "1/ Is Binance front-running TGE announcements?" — @DefiIgnas (Oct 2024). Question form works ONLY when the data follows immediately.

### thread_hook
- **When:** a mechanism explainer or documented experience that genuinely needs 3-5 tweets. Rare — see thread rules below.
- **Hook formula:** [big claim or stat] + [stakes] + [explicit promise]: "27% APY on a stablecoin — how sustainable is Ethena?" — @Route2FI (Feb 2024).
- **Drives: follows + bookmarks.** Every body tweet needs its own number or mechanic.

### punchy_take
- **When:** one idea, maximum compression, strong opinion. The aphorism archetype (@0xSisyphus).
- **Hook formula:** none — the whole post is the hook. One or two sentences.
- **Drives: RTs + profile clicks.**
- **Real example:** "Crypto was previously great for amassing large amounts of personal wealth very quickly since you can sell tokens much earlier than you can sell equity in a company. It is a remarkably poor substrate to build a real business for the exact same reason." — @0xSisyphus (Dec 2025).

### pattern_recognition
- **When:** current event rhymes with a documented precedent ([[knowledge/crypto-history]], [[knowledge/exploit-history]]).
- **Hook formula:** [today's event + number] → [the precedent + year] → [what happened next then].
- **Drives: bookmarks** (people save frameworks).
- **Real example register:** Pentoshi's rate-lag thesis: "It is somewhat like a sonic boom... There is a lag" (Nov 2022).

### farming_update
- **When:** documented airdrop/yield position from portfolio.json has news (criteria change, points repricing, pool APY shift).
- **Hook formula:** [position + duration] → [what changed, with number] → [what I'm doing about it].
- **Drives: bookmarks + replies** from fellow farmers. First person mandatory: "Been farming X for 6 weeks" not "farmers are seeing".

### wrong_take_correction
- **When:** a stale or wrong number is circulating (e.g. Core DAO "$353M TVL" when live is $6.3M).
- **Hook formula:** [the circulating claim] → [the live number + source] → [why the gap matters].
- **Drives: replies + bookmarks + credibility.** Our highest-conversion format for profile follows — being verifiably right in public is the whole account thesis.

## Thread rules (2026)

- **Long-form single posts out-reach classic threads** (Hootsuite experiment; Metricool shows accounts posting ~3x more long posts than threads). Default to one long post.
- Thread only when: documenting a multi-week experience, explaining a mechanism that needs diagrams, or a callout with multiple receipts.
- 3-5 tweets max. Each tweet must earn its own engagement — later tweets see steep reach drop-off.
- No "🧵👇" hook clichés (see [[knowledge/voice-integrity]]). The hook is a claim, not an announcement of a thread.
- Max one thread per week.

## Image vs text-only

- Text posts slightly out-engage image posts on median (~0.9% Premium median, Buffer 18M-post dataset) — **text-only is never a penalty.**
- Images pay only when they're dense data (chart, annotated screenshot) that invites tap-to-expand (P(photo_expand) is a real scoring head) and adds dwell.
- Decorative/AI-art images hurt the analyst archetype. See [[knowledge/image-strategy]] for decision logic.

## Format → metric map (for the performance tracker)

| Format | Primary metric | Secondary |
|---|---|---|
| data_observation | bookmark_rate | reply_rate |
| contrarian | reply_rate | profile clicks |
| position_update | follows | reply_rate |
| callout | reply_rate | RTs |
| thread_hook | follows | bookmark_rate |
| punchy_take | RTs | profile clicks |
| pattern_recognition | bookmark_rate | RTs |
| farming_update | bookmark_rate | reply_rate |
| wrong_take_correction | reply_rate | follows |

---

→ [[index]] · [[k