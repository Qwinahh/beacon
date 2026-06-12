# image-apis — research (2026-06-12)

All prices verified on 2026-06-12 unless noted. Sources are listed per row and per section.

## Comparison table

| Provider/model | Price per image | Latency | Text rendering quality | Notes | Source URL |
|---|---|---|---|---|---|
| Replicate — black-forest-labs/flux-schnell | $3.00 / 1,000 output images = **$0.003/image** (2026-06-12) | "Generates images in seconds"; `go_fast` fp8-optimized variant available; no official seconds figure on page (third-party benchmarks at Artificial Analysis) | Good for short strings: FLUX renders legible 5–15 char text reliably per comparisons | Cheapest paid tier of FLUX family; flux-dev $0.025, flux-1.1-pro $0.04 if more quality needed | https://replicate.com/pricing ; https://replicate.com/black-forest-labs/flux-schnell |
| Replicate — stability-ai/sdxl | ~**$0.0020/run** (≈500 runs/$1), billed by L40S GPU time (2026-06-12) | "Predictions typically complete within 3 seconds" | Poor — model card states outright: "The model cannot render legible text" | Cheapest option overall but dated (2023 model); fine-tunable | https://replicate.com/stability-ai/sdxl |
| OpenAI — DALL-E 3 | Was $0.04 (1024² standard) / $0.08 (HD); **removed from API on 2026-05-12** | n/a (retired) | Mediocre — tends to duplicate/warp words beyond short phrases | Do not build on this; OpenAI replaced it with GPT Image 1.5 | https://www.aiworthit.com/blog/dall-e-review/ ; https://tokenmix.ai/blog/dall-e-api-pricing |
| OpenAI — gpt-image-1 | ~$0.011–$0.25/image (≈$0.02/$0.07/$0.19 low/med/high 1024²); **deprecating 2026-10-23** | Known slow; community reports of timeouts on generation/edit calls | Strong (token-based autoregressive image model) | Avoid for new projects due to deprecation | https://costgoat.com/pricing/openai-images ; https://community.openai.com/t/gpt-image-1-is-realy-slow/1310616 |
| OpenAI — gpt-image-1.5 (current flagship) | Token-based: image output $32/1M tokens, text input $5/1M (standard; batch is half). ≈ **$0.009 low / $0.034 medium / $0.133 high** per 1024² image (2026-06-12) | Up to 4x faster than gpt-image-1; still seconds-to-minutes — complex prompts can take up to 2 minutes | Best-in-class family for prompt adherence and text; DALL-E 3's successor | gpt-image-1-mini at $8/1M image-output tokens for cheaper tier | https://developers.openai.com/api/docs/pricing ; https://costgoat.com/pricing/openai-images ; https://evolink.ai/blog/gpt-image-1-5-api-guide |
| Fal.ai — fal-ai/flux/schnell | **$0.003 per megapixel**, rounded up to nearest MP (1024² ≈ 1MP ≈ $0.003) (2026-06-12) | Sub-second warm inference; page example shows `"inference": 0.366` seconds | Same FLUX schnell weights as Replicate — good short-string text | fal is the speed leader for FLUX schnell per benchmarks | https://fal.ai/models/fal-ai/flux/schnell |
| Fal.ai — Flux Kontext Pro | **$0.04/image** (2026-06-12) | Not stated on pricing page | FLUX Pro tier — higher quality/adherence than schnell | Listed on fal pricing page alongside Seedream V4 $0.03, Nano Banana $0.0398, Qwen $0.02/MP | https://fal.ai/pricing |

## Per-provider details

### Replicate
- **Pricing model:** public models billed either per output (flux-schnell $3.00/1k images; flux-dev $0.025/img; flux-1.1-pro $0.04/img — all on https://replicate.com/pricing, 2026-06-12) or by GPU-seconds (SDXL on L40S at $0.000975/sec, ≈$0.0020/run per https://replicate.com/stability-ai/sdxl, 2026-06-12).
- **Latency:** SDXL "typically completes within 3 seconds." flux-schnell offers a `go_fast` flag (compiled fp8 quantization, optimized attention kernel). Replicate is benchmarked alongside fal/Together/Runware at https://artificialanalysis.ai/image/providers/flux-1-schnell.
- **Dark/terminal/data-viz aesthetic:** FLUX models have strong prompt adherence ("matching the performance of closed source alternatives" per model card); SDXL's own card warns it struggles with compositionality and cannot render legible text — bad fit for labeled data-viz. Replicate also hosts text-rendering specialists: recraft-ai/recraft-v3 ($0.04/img, "ability to generate long texts") and ideogram-v3-quality ($0.09/img) if labels are critical.
- **API ergonomics:** `pip install replicate`, auth via `REPLICATE_API_TOKEN` env var, official Python SDK (`import replicate; replicate.run(...)`). Pay-as-you-go, no subscription — well suited to a GitHub Action.

### OpenAI
- **DALL-E 3 is gone:** removed from the API on 2026-05-12 (https://www.aiworthit.com/blog/dall-e-review/). Historical pricing was $0.04 standard 1024² / $0.08 HD / up to $0.12 portrait-landscape HD (https://tokenmix.ai/blog/dall-e-api-pricing).
- **gpt-image-1 is deprecating 2026-10-23** (https://costgoat.com/pricing/openai-images); skip it.
- **gpt-image-1.5** is the current default. Official pricing (https://developers.openai.com/api/docs/pricing, fetched 2026-06-12): image output $32/1M tokens, image input $8/1M, text input $5/1M; Batch API exactly half. Practical per-image cost ≈ $0.009 (low) / $0.034 (medium) / $0.133 (high) for 1024²; portrait/landscape ≈ $0.013/$0.05/$0.20 (https://costgoat.com/pricing/openai-images). gpt-image-1-mini is the budget tier ($8/1M image-output tokens).
- **Latency:** up to 4x faster than gpt-image-1, but OpenAI docs note complex prompts can take up to 2 minutes; JPEG output is faster than PNG (https://evolink.ai/blog/gpt-image-1-5-api-guide). Slowest of the three options here.
- **Text rendering / aesthetics:** GPT Image family is the strongest at complex layouts and reliable spelling (DALL-E 3 already beat diffusion models on short words; comparisons note OpenAI keeps "a slight edge for complex text layouts" — https://getimg.ai/blog/flux-1-vs-dall-e-3-what-is-the-best-ai-text-to-image-model, https://zsky.ai/blog/flux-vs-dall-e-comparison).
- **API ergonomics:** `pip install openai`, `OPENAI_API_KEY` env var, `client.images.generate(model="gpt-image-1.5", ...)`. Mature SDK; org verification may apply for image models. Token-based billing makes per-image cost slightly less predictable than flat per-image pricing.

### Fal.ai
- **Pricing:** flux/schnell at $0.003/megapixel, billed rounding up to the nearest MP (https://fal.ai/models/fal-ai/flux/schnell, 2026-06-12) — a 1024x1024 image costs ~$0.003; a 1216x832 (~1.01MP) rounds to 2MP = $0.006, so stay at/under 1MP. Pricing page (https://fal.ai/pricing, 2026-06-12) lists Flux Kontext Pro $0.04/img, Seedream V4 $0.03/img, Nano Banana $0.0398/img, Qwen $0.02/MP.
- **Latency:** the fastest FLUX schnell host — sub-second warm inference (model page shows a real 0.37s inference timing; fal's own docs target sub-second generation: https://fal.ai/learn/devs/gen-ai-performance-optimization).
- **Quality for this use case:** identical FLUX.1 [schnell] weights as Replicate (Apache-2.0, 1–4 step distilled). Good short-label text (5–15 chars reliable per https://getimg.ai/blog/flux-1-vs-dall-e-3-what-is-the-best-ai-text-to-image-model); model card touts "consistent style maintenance across multiple generations," useful for a recurring bot aesthetic.
- **API ergonomics:** `pip install fal-client`, auth via `FAL_KEY` env var, `fal_client.subscribe("fal-ai/flux/schnell", arguments={...})` with sync/async/webhook modes. Simple queue-based REST under the hood; very GitHub-Action friendly.

## Recommendation

For ~1–3 images/day with a dark terminal/data-viz aesthetic called from a Python GitHub Action, use **Fal.ai's fal-ai/flux/schnell** as the primary: at $0.003/MP it costs well under $0.30/month at this volume, returns images in under a second (no Action-timeout risk), uses a trivial Python client (`fal-client` + `FAL_KEY` secret), and FLUX's strong prompt adherence handles dark neon/terminal styling and short text labels (ticker symbols, "BTC", "+4.2%") reliably enough for tweet graphics — Replicate's flux-schnell at $0.003/image is an interchangeable fallback with the same weights if fal has an outage. If a given image needs longer or pixel-perfect text (multiple axis labels, sentences), step up per-image to OpenAI **gpt-image-1.5** at low/medium quality ($0.009–$0.034) — the GPT Image family is the most reliable at complex text layouts — or Replicate's recraft-v3 ($0.04). Avoid SDXL (its own model card says it cannot render legible text) and anything DALL-E (removed from the API May 2026).

## Caveats

- **No model renders precise numeric charts.** AI image models will invent or garble axis values and exact numbers; for a true data-viz (real prices, real candles), render the chart programmatically (matplotlib/Pillow) and use the image model only for backgrounds/branding, or composite the two. Short decorative labels are fine; dense labels are not.
- **Deprecation churn at OpenAI:** DALL-E 3 removed 2026-05-12; gpt-image-1 deprecates 2026-10-23. Pin to gpt-image-1.5 (or gpt-image-2, also on the pricing page at $30/1M image-output tokens) and expect this row to change.
- **Fal bills per megapixel rounded up** — a 1.05MP image is billed as 2MP. Keep outputs at 1024x1024 or other ≤1MP sizes to stay at $0.003.
- **Replicate flux-schnell latency is not officially published**; the page only says "seconds" and third-party medians (Artificial Analysis) fluctuate. Fal's sub-second claim is for warm inference; cold paths can be slower.
- **Token-based OpenAI pricing** means cost varies with prompt length and quality setting; per-image figures above are estimates from third-party calculators (costgoat.com), not an OpenAI flat rate.
- **No benchmark specifically scores "dark terminal aesthetic"** — quality claims here are extrapolated from general prompt-adherence and text-rendering comparisons; run a small bake-off (same prompt on fal schnell, flux-dev, gpt-image-1.5 low) before committing.
- Aggregate/per-image price breakdowns for gpt-image-1.5 and the DALL-E retirement date come from third-party trackers (costgoat.com, aiworthit.com, tokenmix.ai) dated June 2026; the authoritative token rates are the OpenAI pricing page fetched 2026-06-12.

## Sources

- https://replicate.com/pricing (fetched 2026-06-12)
- https://replicate.com/black-forest-labs/flux-schnell (fetched 2026-06-12)
- https://replicate.com/stability-ai/sdxl (fetched 2026-06-12)
- https://fal.ai/pricing (fetched 2026-06-12)
- https://fal.ai/models/fal-ai/flux/schnell (fetched 2026-06-12)
- https://developers.openai.com/api/docs/pricing (fetched 2026-06-12)
- https://costgoat.com/pricing/openai-images (June 2026)
- https://www.aiworthit.com/blog/dall-e-review/
- https://tokenmix.ai/blog/dall-e-api-pricing
- https://evolink.ai/blog/gpt-image-1-5-api-guide
- https://getimg.ai/blog/flux-1-vs-dall-e-3-what-is-the-best-ai-text-to-image-model
- https://zsky.ai/blog/flux-vs-dall-e-comparison
- https://artificialanalysis.ai/image/providers/flux-1-schnell
- https://fal.ai/learn/devs/gen-ai-performance-optimization