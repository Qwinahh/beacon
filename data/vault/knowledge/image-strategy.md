---
title: Image Strategy — When and How @Qwinahh Uses Images
type: knowledge
topic: images
tags: [knowledge, x-strategy, images, visual-style]
confirmed: true
source: data/research/image-apis.md + data/research/x-algorithm.md + data/research/ct-accounts.md (2026-06-12)
last_updated: 2026-06-12
updated: 2026-06-12
---

# Image Strategy — When and How @Qwinahh Uses Images

## When images help vs hurt

The data ([[knowledge/x-algorithm-2026]]): text posts slightly out-engage
images on median (~0.9% Premium median, Buffer 18M-post dataset). Images
are not a default — they're a tool that pays only through two scoring
paths: **dwell** (people stop to read the chart) and **photo_expand**
(dense detail invites tap-to-expand, an explicit Phoenix prediction head).

Helps:
- data_observation with a chart that SHOWS the number in the post
- thread_hook (a strong cover image lifts thread entry)
- pattern_recognition with a then-vs-now comparison
- 2-4 image sets when each adds information (dwell stacking)

Hurts:
- punchy_take / contrarian one-liners — the aphorism archetype (@0xSisyphus) is text-first for a reason; an image dilutes the hit
- Decorative AI art on analyst content — instantly reads as bot slop and invites mutes
- Generic stock-crypto imagery of any kind

Top-account pattern (research/ct-accounts.md): analysts (@DefiIgnas,
@thedefiedge) attach Dune/DeFiLlama screenshots and branded covers to
nearly everything; aphorists post text. We are the analyst archetype with
aphorist moments — image on data posts, never on takes.

## Image types that perform (crypto niche)

1. Annotated data screenshots (Dune, DeFiLlama dashboards with one highlight)
2. Clean single-metric charts (one line, one number callout)
3. Then-vs-now comparison panels
4. Terminal-style stat cards (our signature format — see style guide)

## @Qwinahh visual style guide

- Background: **#0d1117** (GitHub-dark), always
- Text: white (#e6edf3) primary, terminal green (#3fb950) for the key number/highlight, red (#f85149) only for drawdowns
- Aesthetic: terminal / TradingView-overlay / on-chain data display. Monospace type. Thin grid lines (#21262d)
- One number is the hero — big, green, centered or upper-left. Everything else is context at half the size
- Footer: small "@Qwinahh" watermark, bottom-right, #484f58
- NEVER: moons, rockets, lambos, bulls/bears as animals, candlestick-explosion art, glowing coins, cartoon mascots, gradient hype-poster look

## Technical X specs

- 1024x1024 (1MP) — stays at fal.ai's $0.003 single-MP billing and renders sharp in feed
- 16:9 (1200x675) acceptable for wide charts; mind the MP rounding (>1MP bills as 2MP)
- PNG for charts (sharp text), JPEG if generation speed matters
- Always check the image reads at thumbnail size — feed renders small first

## Generation stack (from research/image-apis.md, prices 2026-06-12)

- **Primary: fal.ai `fal-ai/flux/schnell`** — $0.003/MP, sub-second warm inference, `fal-client` Python SDK, FAL_KEY env var. Handles dark terminal styling + short labels (tickers, "+4.2%") reliably
- **Fallback: Replicate `flux-schnell`** — $0.003/image, same weights, REPLICATE_API_TOKEN
- **Complex text needed: OpenAI gpt-image-1.5** low/medium ($0.009-$0.034) — only when multiple legible labels are essential
- **Never: SDXL** (own model card: "cannot render legible text"), anything DALL-E (removed from API 2026-05-12)

## CRITICAL: numbers must be rendered, not generated

AI image models invent or garble axis values and digits. **Any image
containing real data must be rendered programmatically** (matplotlib/
Pillow with the style guide above) — the generative model is only for
backgrounds/branding/abstract texture, or skipped entirely. A tweet
with a hallucinated number in the image is a credibility-ending event
for an account whose thesis is "verifiably right in public."

## Prompt templates (for generative backgrounds/covers only)

Base style suffix (append to every prompt):
"dark GitHub-dark background #0d1117, terminal aesthetic, monospace
typography, thin grid lines, white and terminal-green text accents,
clean minimal data visualization style, flat design, no gradients,
no glow effects, professional trading dashboard look"

- Thread cover: "minimal abstract visualization of [topic: e.g. 'order book depth', 'yield curve'], " + base suffix
- Stat card backdrop: "empty dark terminal dashboard panel with subtle grid, " + base suffix (numbers composited with Pillow afterwards)

## What NOT to generate, ever

- Charts with specific numbers/axes (render those)
- Faces, real people, project logos (IP + cringe risk)
- Moon/rocket/lambo/bull/bear imagery (style guide violation)
- Meme templates (wrong archetype for this account)
- Anything when the post is a take rather than data

---

→ [