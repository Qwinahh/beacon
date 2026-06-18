---
title: Pendle
name: Pendle
tags: [project, yield, fixed-income, ethereum, arbitrum]
trust_score: 4
category: Yield / Fixed income
chain: Ethereum (+Plasma, Arbitrum, HyperEVM, BNB, Base)
last_updated: 2026-06-12
airdrop_status: none
worth_farming: true
blocked: false
updated: 2026-06-12
tvl_usd: 964094466
price_usd: 1.46
price_change_24h: -2.8
metrics_updated: 2026-06-18
---

# Pendle

## Thesis
Pendle won its category — there is still no real competitor for on-chain
fixed income — and then the category shrank under it. TVL is $1.15B
(2026-06-11, DeFiLlama), down 18% in 30d and ~91% off the $13.4B ATH of
Sep 2025. That's not a Pendle failure, it's the stablecoin-yield unwind:
when sUSDe pays 4.3% fixed, nobody needs to lock it in. The protocol's
answer is Boros (funding-rate derivatives) and regulated-stable pools
(USDG, apxUSD/apyUSD). The mispricing argument: $214M mcap for a working
monopoly on rate markets, "priced like a damaged product."

## Stance
Farming selectively. PT buying only makes sense where the implied APY
actually compensates: apyUSD printed 33.5% implied on the June maturity
(small, 1-week, quote with care), AVLT on HyperEVM 18.3%, reUSDe 17.9%
(all 2026-06-11, Pendle API). Blue-chip sUSDe PT at 4.3% fixed is dead
money — skip. Watching Boros OI as the real growth signal; V2 yield
compression is structural until funding regimes turn.

## Risks
- TVL down 18%/30d and still falling — fee base compresses with it
- Team moved 600k PENDLE (~$1.27M) to Binance on 2026-05-13, intent unconfirmed
- High-APY pools are high-APY because the underlying (apyUSD, reUSDe) carries real blowup risk — PT fixed yield doesn't remove collateral risk
- LayerZero dependency: Pendle was among 14 protocols pausing markets in the May 9 LZ incident

## Observations
<!-- Bot appends new observations below. Newest at bottom. -->
- **2026-06-11** — PENDLE $1.26, mcap $214.5M. TVL $1.15B: Ethereum $774M (68%), Plasma $193M (surprise #2 chain), Arbitrum $139M. Ethena sUSDe fixed compressed to 4.31%.
- **2026-06-12** — Vault entry created. STRC-linked TVL hit $318M (May 11). The chain mix is the tell: Plasma at #2 means stablecoin-chain flows, not ETH-native degens, are the marginal Pendle user now.

## Airdrop
- Status: none pending. vePENDLE→sPENDLE migration with buybacks is the value-accrual story instead.

## X Consensus
- Sentiment: bullish on fundamentals, mixed near-term
- CT consensus is "fixed-income monopoly, undervalued" (@arndxt_xo: "already won its category"). Where consensus is lazy: everyone quotes the monopoly, nobody models what happens to a rate-market monopoly when rates compress to T-bill levels — Pendle's moat is real but its TAM is cyclical. The under-covered angle is Boros: funding-rate markets are the only leg that GROWS when spot yield dies, and almost nobody tracks its OI.

## Links
- DeFiLlama: https://defillama.com/protocol/pendle
- App: https://app.pendle.finance
- Boros: https://boros.pendle.finance
- Research: `data/research/pendle.md`

---

→ [[index]] · [[dashboard]] · [[narratives/yield-bearing-stables]] · [[projects/ethena]] · [[projects/layerzero]]

## Live Metrics
- TVL: $964.1M
- Price: $1.46 (-2.8% 24h)
- Snapshot: 2026-06-18 (auto, DeFiLlama + CoinGecko)
