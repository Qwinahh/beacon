---
title: AI Writing Tells — How to Not Sound Like a Bot
type: knowledge
topic: voice
tags: [knowledge, voice, anti-ai, writing]
confirmed: true
source: r/ClaudeAI — "I pulled 90,000 Reddit posts about what makes writing sound AI"
source_url: https://www.reddit.com/r/ClaudeAI/comments/1ucpw87/
last_updated: 2026-06-24
---

# AI Writing Tells — How to Not Sound Like a Bot

Reference for the writer and the authenticity judge. Based on an Arctic Shift Reddit
analysis: 89,239 posts across 47 subreddits (2021–2026), filtered to 7,984 on-topic
posts about spotting AI writing, with a hand-audited 600-post sample recording what
people *actually cite* as a tell versus what a keyword merely matches.

Why all AI writing converges on the same voice: every model is tuned for a safe,
agreeable register that reads as "good writing" to a grader, so every default lands in
the same place. One reader: *"ChatGPT has a very recognizable cadence. As soon as you
catch it, it's impossible to focus on what's being written."*

## The tells, ranked by how often readers actually cite them

1. **The em dash** — top tell by a wide margin (cited 7.1% of audited posts). "The single most reliable tell of AI-generated text." Use a comma, a period, or two sentences.
2. **Flat, uniform sentence rhythm** (4.0%) — no scanner can see it; the reader's ear catches it. Every sentence the same length and shape.
3. **The "not just X, it's Y" antithesis cadence** (2.8%) — the top sentence-level tell. Say the thing plainly instead of negating first.
4. **Five-paragraph shape + "in conclusion" wrap-up** (2.5%) — the school-essay mold.
5. **Diction memes** (1.3% as a cluster): delve, leverage, seamless, tapestry. (Community also flags: robust, comprehensive, utilize, navigating, underscore, realm, bustling, "treasure trove", "deep dive", unlock, elevate, "game-changer", "testament to", embark.)
6. **Leftover assistant boilerplate** (1.2%): "As an AI language model…", "As an AI developed by…". Never emit it.
7. **Hollow scene-setting opener** (0.7%, iconic): *"I wanted to take a moment to delve into something… In today's fast-paced digital landscape…"*

Two tells rank in the top five but **no keyword can catch them** (judged by the LLM gate, not a word list):
- **Sycophancy** — the "great question!" opener, reflexive refusal to take a side.
- **Saying nothing at length** — prose that is grammatical and confident but makes no actual, falsifiable claim.

## The trap: cheap signal vs real signal point in opposite directions

A naive keyword scanner gets this backwards:
- It **over-counts ordinary words**. "however", "thus", "hence", "moreover", "nuanced" (as a plain word), "comprehensive", "when it comes to", "utilize" are the *highest keyword matches* in the corpus and are cited as a tell ~0% of the time — they're just people writing normally. **Do not hard-ban these as words.** A detector built on a word list flags mostly false positives.
- It **misses the real tells** (flat rhythm, fluent-but-empty prose) because no word list can see them.

Lesson: the *cited* column drives the ranking, not the keyword column. Judgment > word-matching.

## Important caveat

None of these are strictly AI problems. The em dash is good typography; formal diction and tidy structure are how many careful writers, students, and non-native English speakers have always written. AI just made everyone produce them at once, so the people who always wrote this way get falsely flagged. The point isn't that these patterns are *wrong* — it's that they're the model's **default**, and a real voice deviates from the default.

## The fix (what the writer should do)

- Cut the em dash.
- Say the thing plainly instead of negating it first ("not just X, it's Y").
- Vary sentence length so the rhythm isn't a metronome.
- Drop the flattery and take a position.
- Use contractions.
- Let structure follow the argument, not the intro-body-conclusion mold.
- Don't lean on TVL (Beacon's specific habit): lead with volume, open interest, funding, fees, real users, or price action. TVL only when it's genuinely the sharpest number.
- The fix that showed up most: stop letting the model pick the voice — feed it a real sample and read the result out loud, because the rhythm is the tell your ear catches before your eye does.

## How Beacon enforces this (where each defense lives)

- **`config.scrub_voice()`** — deterministic: strips every em/en dash before validation and judging. Applied to all posts and thread tweets. (Tell #1, guaranteed.)
- **`data/persona.md` → Voice & Style** — instructs the writer up front: no em dashes, no antithesis cadence, no TVL-by-habit, banned diction, vary rhythm, contractions, take a position. (Shapes generation.)
- **`bot/brain/authenticity_judge.py`** — the LLM gate scores and blocks the tells a word list can't catch: flat rhythm, sycophancy, saying-nothing, plus the diction and structure tells. (Catches what slips through.)
- Deliberately **not** hard-banned: however / thus / hence / moreover / nuanced-as-a-word — they're false positives per the data.

## Additional findings (from the full 13-graph set)

**Tells by family** (share of on-topic posts naming at least one): diction 17.1% > phrasing 15.4% > formatting 9.9% > pasted artifacts 2.2%. Diction and phrasing are the bulk, but formatting matters too.

**Formatting tells** (relevant for threads, not just single posts): bullet lists / listicles (cited 1.7%), emoji bullets / headers (0.8%), bolded lead-in bullets, markdown headers, horizontal-rule dividers. A real person dashes off a thought; they don't format a tweet like a structured doc. Keep posts as prose; in threads, no bullets/emoji/headers.

**Rule of three / triads** (cited 1.2%): the balanced "X, Y, and Z" three-item cadence. Overusing it reads as AI. Vary the count.

**Chatbot closers / boilerplate** (the "artifact" family): "as an AI" (appears in an AI context in 8,723 posts across 46 subs), "as a large language model", "would you like me to…", "let me know if…", "I hope this helps", "look no further". Never emit any of these — you're a trader, not an assistant.

**More flagged diction** (keyword pass): showcase, crucial, harness, profound, streamline, "ever-evolving", "the world of", "not only… but also", "first / secondly / lastly".

**What is NOT worth doing** (cited ~0.0% — these don't fool anyone):
- Fake typos as an anti-detector trick. Deliberately adding errors just looks sloppy. Don't.
- Horizontal-rule dividers, forced transitions, verbosity/repetition, "Honestly," openers, hallucinated citations. ("Honestly" is fine to use.)
- Normal connectors (however / thus / hence / moreover): high keyword match, ~0% cited. Not tells — don't avoid them.

**Methodology refinement:** funnel was 115,787 raw query hits → 89,239 unique posts → 7,984 on-topic → 600 hand-audited. Complaints concentrate in r/WritingWithAI (32% of its posts), r/aiwars (19%), r/ChatGPT (15%), r/Professors (15%). The em dash was ~0 before 2024, then spiked in 2025 — the signature ChatGPT-era arrival.

## Related
- [[persona]] · [[x-growth-strategy]] · [[voice-integrity]] · [[post-structure-science]]
