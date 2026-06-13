# pendle — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| TVL (total) | $1.146B ($1,146,126,399) | 2026-06-11 | https://api.llama.fi/tvl/pendle (https://defillama.com/protocol/pendle) |
| TVL 30 days ago | $1.398B (2026-05-12) → TVL is down ~18% in 30d | 2026-06-11 | https://api.llama.fi/protocol/pendle |
| TVL 1 year ago / ATH | $5.06B (2025-06-11); ATH $13.39B (2025-09-19) | 2026-06-11 | https://api.llama.fi/protocol/pendle |
| PENDLE price | $1.26 (Binance spot: $1.258) | 2026-06-11 | https://api.coingecko.com/api/v3/simple/price?ids=pendle / https://api.binance.com |
| 24h change | +7.7% | 2026-06-11 | https://api.coingecko.com/api/v3/simple/price?ids=pendle |
| Market cap | $214.5M (rank #169) | 2026-06-11 | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=pendle |
| FDV | $353.9M | 2026-06-11 | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=pendle |
| Circulating supply | ~170.66M PENDLE | 2026-06-11 | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=pendle |
| ATH price | $7.50 (2024-04-11) | 2026-06-11 | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=pendle |
| Active markets (Ethereum) | 85 markets, ~$179M AMM liquidity | 2026-06-11 | https://api-v2.pendle.finance/core/v1/1/markets/active |

### Chain TVL breakdown (DeFiLlama, 2026-06-11)

| Chain | TVL | Source |
|---|---|---|
| Ethereum | $773.8M | https://api.llama.fi/protocol/pendle |
| Plasma | $193.4M | https://api.llama.fi/protocol/pendle |
| Arbitrum | $139.5M | https://api.llama.fi/protocol/pendle |
| Ethereum staking (vePENDLE/sPENDLE) | $124.0M | https://api.llama.fi/protocol/pendle |
| Hyperliquid L1 (HyperEVM) | $24.0M | https://api.llama.fi/protocol/pendle |
| BNB Chain | $11.0M | https://api.llama.fi/protocol/pendle |
| Base | $3.6M | https://api.llama.fi/protocol/pendle |

Ethereum dominates (~68% of TVL); Plasma is the surprise #2 chain; Arbitrum #3.

## Top pools right now

Top active Pendle V2 markets by AMM liquidity, with PT fixed/implied APY (all pulled 2026-06-11 from https://api-v2.pendle.finance/core/v1/{chainId}/markets/active — "impliedApy" field = fixed rate a PT buyer locks in):

| Pool | Fixed/implied APY | Chain | Maturity | AMM liquidity | Source |
|---|---|---|---|---|---|
| USDai | 7.53% | Arbitrum | 2026-06-18 | $35.3M | api-v2.pendle.finance (chain 42161) |
| SIERRA | 9.21% | Ethereum | 2026-07-02 | $14.0M | api-v2.pendle.finance (chain 1) |
| sUSDai | 10.18% | Arbitrum | 2026-10-15 | $11.0M | api-v2.pendle.finance (chain 42161) |
| USDat | 8.25% | Ethereum | 2026-08-27 | $10.2M | api-v2.pendle.finance (chain 1) |
| sUSDe (Ethena) | 4.31% | Ethereum | 2026-08-13 | $9.4M | api-v2.pendle.finance (chain 1) |
| apyUSD | 33.54% | Ethereum | 2026-06-18 | $9.1M | api-v2.pendle.finance (chain 1) |
| msY | 12.04% | Ethereum | 2026-07-30 | $8.9M | api-v2.pendle.finance (chain 1) |
| srUSDe | 4.86% | Ethereum | 2026-06-25 | $8.5M | api-v2.pendle.finance (chain 1) |
| apxUSD | 16.57% | Ethereum | 2026-06-18 | $7.6M | api-v2.pendle.finance (chain 1) |
| apyUSD | 16.62% | Ethereum | 2026-11-05 | $7.5M | api-v2.pendle.finance (chain 1) |
| AVLT | 18.34% (LP agg. 29.23%) | HyperEVM | 2026-11-12 | $5.2M | api-v2.pendle.finance (chain 999) |
| reUSDe | 17.87% | Ethereum | 2026-06-25 | $4.8M | api-v2.pendle.finance (chain 1) |
| sUSDat (Saturn) | 14.55% | Ethereum | 2026-08-27 | $4.2M | api-v2.pendle.finance (chain 1) |

Notes: high-APY standouts right now are apyUSD (~33.5% implied on the June maturity), AVLT on HyperEVM (~18.3%), reUSDe (~17.9%), apxUSD (~16.6%). Blue-chip Ethena sUSDe fixed yield has compressed to ~4.3%. Boros BTCUSDC (28 May 2026 maturity) funding-rate market was showing 10.77% implied APR in search results on 2026-06-11 (https://boros.pendle.finance/markets).

## Recent developments (last 30 days)

- **2026-05-09** — Pendle was among 14 protocols that paused/froze certain markets or bridging as a precaution after a LayerZero security incident / "crisis of confidence" in cross-chain bridging. Sources: https://cryptorank.io/news/feed/51d47-layerzero-bridge-protocols-exit-suspend ; https://coinmarketcap.com/cmc-ai/pendle/latest-updates/
- **2026-05-11** — STRC-linked TVL on Pendle surpassed $318M (Stream/STRC yield strategies: fixed yield up to ~18% APY cited). Source: https://blockchainreporter.net/strc-linked-tvl-on-pendle-reaches-318-million-as-yield-strategies-expand
- **2026-05-13** — Pendle team deposited 600,000 PENDLE (~$1.27M) to Binance, sparking sell-off speculation; intent unconfirmed. Source: https://cryptorank.io/news/feed/94749-pendle-team-deposits-pendle-binance (BitcoinWorld)
- **2026-05-14 (CMC AI roundup)** — 2026 roadmap themes: "stupidly easy, stupidly powerful" UX (one-click leveraged PTs, auto-rollover, CEX access), Boros expansion (funding-rate/IR derivatives with leverage, cross-exchange funding arb), and live Pendle Skills/MCP AI-agent integration. Source: https://coinmarketcap.com/cmc-ai/pendle/latest-updates/
- **2026-05-19** — Price analysis: PENDLE battling the $1.80 level with derivatives open interest holding steady (price has since fallen to ~$1.26 on 2026-06-11). Source: https://cryptorank.io/news/feed/9166c-pendle-price-outlook-1-80-key-as-open-interest-holds-steady (Invezz)
- **2026-05-12 → 2026-06-11** — TVL declined from ~$1.40B to ~$1.15B (-18% in 30d) per DeFiLlama, continuing a longer drawdown from the $13.4B ATH (2025-09-19). Source: https://api.llama.fi/protocol/pendle
- **Context (slightly older but referenced this period):** PENDLE rallied to test ~$2.09 around 2026-05-08 (4h RSI 88 per trader posts) before the current pullback; a late-April KelpDAO-related incident was followed by "smart money" accumulation per on-chain analysts. Source: https://coinmarketcap.com/cmc-ai/pendle/latest-updates/ . New RWA/regulated-stablecoin pools (USDG by Paxos, apxUSD, apyUSD) were announced earlier in 2026 and the apxUSD/apyUSD pools are now among the top markets by liquidity. Source: https://earnpark.com/en/posts/what-is-pendle-finance-the-complete-2026-guide-to-yield-tokenisation-pt-yt-mechanics-and-boros/

## CT sentiment

- Aggregate tweet sentiment (CoinCodex, undated snapshot retrieved 2026-06-11): ~55.2% bullish, 7.8% bearish, 44.8%* neutral — net bullish skew. Source: https://coincodex.com/crypto/pendle/price-prediction/ (*figures as published; they don't sum to 100, treat as indicative only)
- CMC AI social roundup (2026-05-14, https://coinmarketcap.com/cmc-ai/pendle/latest-updates/): consensus = "bullish on fundamentals, mixed on near-term price":
  - @arndxt_xo (46.8k followers, 2026-04-14): Pendle "already won its category" and is "priced like a damaged product" — mispricing thesis.
  - @Kathydotxyz (2026-04-24): token at historical lows, good R/R; Boros still early; bullish on the sPENDLE buyback/dividend-style token model.
  - @TommyBeFamous (2026-05-08): bearish short setup — "hyper-exhaustion," 4h RSI 88 at $2.09 resistance (this call aged well; price now ~$1.26).
  - @antiiheroine (2026-04-28): net exchange outflows and accumulation after the KelpDAO incident — bullish on-chain signal.
- Recurring CT narratives: Pendle as DeFi's "fixed income layer" with no real competitor (https://www.livebitcoinnews.com/defis-hidden-monopoly-why-pendle-has-zero-competition/), Boros as the under-appreciated growth leg, vePENDLE→sPENDLE buyback tokenomics, and the bear counterpoint that TVL/fees are compressing with stablecoin yields.
- Watch items CT flags: team Binance deposits (May 13), TVL-to-mcap ratio, whether Boros volume offsets V2 yield compression.

## Caveats

- **TVL collapse context**: DeFiLlama shows TVL down from a $13.39B ATH (2025-09-19) to $1.15B today — an ~91% drawdown. I could not fully verify the cause within search budget (likely yield compression, the late-2025 stablecoin/yield unwinds, and asset migrations); treat any "why" framing as unverified.
- **Price discrepancies on cached pages**: CryptoRank's page header showed $1.48 and CMC's cached AI page showed $2.07 — both stale. Live price ($1.26) was verified against two independent live sources (CoinGecko API, Binance spot API) on 2026-06-11.
- **"Liquidity" vs "TVL"**: pool figures in the table are Pendle AMM liquidity from the official API, not total market TVL (TVL incl. PT/YT held outside LPs is larger; DeFiLlama total $1.146B).
- **Implied APY ≠ guaranteed**: impliedApy is the fixed rate locked only if PT is held to maturity; it moves constantly. The 33.5% apyUSD print is a small/new market with a 1-week maturity — quote with care.
- **Boros current stats unverified**: the >$250M Boros open-interest ATH and $7B+ cumulative notional date from ~late Dec 2025 (https://www.bitget.com/news/detail/12560605131298); I could not verify Boros OI/volume as of 2026-06-11. The 10.77% BTCUSDC Boros rate comes from a search-result snippet of boros.pendle.finance, not a direct API read.
- **Sentiment percentages**: CoinCodex bullish/bearish split is undated and methodology-opaque; CMC AI roundup is dated 2026-05-14 (pre-dates the drop from ~$1.80 to $1.26, so sentiment may be cooler now).
- **2025 aggregates** ($40M annualized revenue, $5.8B avg TVL, $47.8B volume) come from secondary sources (FalconX/earnpark summaries), not primary dashboards.
- Sonic and Berachain returned zero active markets via the API on 2026-06-11; small residual TVL on those chains per DeFiLlama may be legacy/expired positions.
