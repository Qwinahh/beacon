# gmx — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| GMX v2 TVL (GM pools + GLV) | $161.08M | 2026-06-11 | https://api.llama.fi/tvl/gmx-v2-perps |
| GMX v1 TVL (legacy GLP) | $2.85M | 2026-06-11 | https://api.llama.fi/tvl/gmx-v1-perps |
| Fees, 24h (all GMX versions) | $208,164 | 2026-06-11 | https://api.llama.fi/summary/fees/gmx |
| Fees, 7d | $775,587 | 2026-06-11 | https://api.llama.fi/summary/fees/gmx |
| Fees, 30d | $2.23M (~$27M annualized run-rate) | 2026-06-11 | https://api.llama.fi/summary/fees/gmx |
| Fees, cumulative all-time | $460.2M | 2026-06-11 | https://api.llama.fi/summary/fees/gmx |
| Revenue, 30d (protocol + holders) | ~$1.15M (per DeFiLlama site) | 2026-06-11 | https://defillama.com/protocol/gmx |
| Holders revenue, 30d | ~$842K (per DeFiLlama site) | 2026-06-11 | https://defillama.com/protocol/gmx |
| Holders revenue, annualized | ~$10.27M (per DeFiLlama site) | 2026-06-11 | https://defillama.com/protocol/gmx |
| GMX token price | $5.48 (CoinGecko); $5.43 (CMC) | 2026-06-11 | https://www.coingecko.com/en/coins/gmx |
| GMX market cap | ~$57.2M (CoinGecko, rank #410); $56.6M (CMC, rank #359) | 2026-06-11 | https://www.coingecko.com/en/coins/gmx , https://coinmarketcap.com/currencies/gmx/ |
| GMX 24h token trading volume | ~$2.96M | 2026-06-11 | https://www.coingecko.com/en/coins/gmx |
| Hyperliquid 30d perp volume (for comparison) | >$180B, ~70–80% perp DEX market share | April 2026 | https://yellow.com/research/hyperliquid-perp-volume-dominance-how-2026 , https://supa.is/article/hyperliquid-vs-dydx-vs-gmx-best-perp-dex-2026 |

## GLP vs GM / real yield status

- **GLP is effectively dead.** GMX V1 trading was phased out in July 2025 and the V1 contracts have been sunset; GLP no longer provides active liquidity (Coin Bureau review, 2026: https://coinbureau.com/review/gmx-review). Residual V1 TVL is only ~$2.85M vs ~$161M in v2 (DeFiLlama API, 2026-06-11) — roughly a 98/2 split in favor of v2.
- **V2 liquidity = GM pools + GLV vaults.** GM pools are isolated, market-specific pools (long token + short token + index feed); GLV vaults auto-allocate across multiple GM markets based on utilization/risk (https://cryptoadventure.com/gmx-review-2026-perpetuals-gm-pools-multichain-trading-and-real-ways-users-try-to-earn/).
- **Real yield thesis: changed, not dead.** The original "stake GMX, earn ETH/AVAX fees" model has morphed: per DeFiLlama's methodology, GMX v2 routes 37% of fees to the protocol side — 10% to treasury and 27% to GMX token holders — with the rest to LPs (https://defillama.com/protocol/gmx-v2-perps). The 27% holder share is now used primarily for **GMX buybacks** rather than direct ETH distribution (https://coinbureau.com/review/gmx-review). So fees still accrue to the token, but via buybacks.
- **Possible staking-reward pause (UNVERIFIED, see Caveats):** A CryptoRank news item claims GMX paused staking rewards entirely, redirecting them to treasury/buybacks until the token hits a $90 target (https://cryptorank.io/news/feed/6ff26-gmx-staking-rewards-paused-price-target). Could not independently confirm via official GMX channels in this session.
- **Scale check:** ~$842K/30d in holders revenue (DeFiLlama, 2026-06-11) against a ~$57M market cap implies a low-double-digit annualized "yield" via buybacks — the real-yield story is intact mechanically but the absolute fee base has shrunk badly (24h fees of ~$22K–$208K depending on day, vs millions/day in the 2021–22 era).

## Recent developments (last 30 days)

- **2026-05-08 — Commodity perps launched:** gold, silver, WTI crude, Brent crude, and natural gas perpetuals added (RWA expansion beyond crypto); weekly GMX buyback program ongoing (https://coinmarketcap.com/cmc-ai/gmx/latest-updates/). *(34 days ago — slightly outside the 30-day window but material.)*
- **2026-05-08 — Formal governance structure:** a community member was appointed CEO, signaling a shift toward structured leadership (https://coinmarketcap.com/cmc-ai/gmx/latest-updates/).
- **2026-05-25 — Doji partnership:** GMX named primary execution venue for Doji, an onchain prop-trading platform (https://coinmarketcap.com/cmc-ai/gmx/latest-updates/).
- **Early June 2026 — MegaETH deployment:** GMX launched perps on MegaETH, its 8th network — BTC/USD, ETH/USD, SOL/USD with up to 50x leverage (https://coinmarketcap.com/cmc-ai/gmx/latest-updates/).
- **Background (2025, still shaping narrative):** the July 2025 GLP pool hack and the subsequent $44M compensation plan for GLP holders (https://www.theblock.co/post/366890/gmx-44-million-compensation-plan) accelerated V1's sunset.

## CT sentiment

- Direct X/Twitter social data was not retrievable this session (LunarCrush API required a paid subscription), so this is inferred from secondary coverage — treat as directional.
- GMX is broadly framed as a **legacy/OG perp DEX that lost the volume war to Hyperliquid** (and newer venues like Aster, Lighter, edgeX); Hyperliquid holds ~70–80% of perp DEX share vs GMX's small fraction (https://yellow.com/research/hyperliquid-perp-volume-dominance-how-2026 , https://supa.is/article/hyperliquid-vs-dydx-vs-gmx-best-perp-dex-2026).
- Discussion that does exist centers on: the **buyback flywheel** (27% of fees buying GMX weekly), the reported **staking-pause / $90 target gambit** (polarizing if true), the **commodity/RWA perps angle**, and the **MegaETH expansion** as a possible relevance reset.
- Reviewers (e.g., Coin Bureau 2026) still credit GMX for oracle-based zero-slippage execution and "real yield" branding, but note it's now a niche rather than a leader (https://coinbureau.com/review/gmx-review).
- Token down to ~$57M mcap (vs multi-hundred-million prior cycles) — sentiment is best characterized as **muted-to-bearish with a contrarian "fee-generating value coin" minority**.

## Caveats

- **DeFiLlama figure discrepancy:** the DeFiLlama API (fetched directly 2026-06-11) shows 30d fees of $2.23M and all-time fees of $460.2M, while search-result snapshots of the DeFiLlama site quoted 30d fees $3.12M, annualized fees $38.05M, all-time $470.4M. The site figures may include adapters/timeframes the API summary doesn't, or be cached from a different date. The directly-fetched API numbers are the more reliably timestamped.
- **Staking rewards paused until $90:** sourced only from a single CryptoRank news feed item; I could NOT verify this against GMX's official docs, governance forum, or X account in this session. Do not tweet this as fact without confirming on gov.gmx.io or @GMX_IO.
- **GMX v2 30d trading volume:** could not retrieve an exact figure (DeFiLlama derivatives API returned empty for the GMX slugs). Volume-vs-competitor claims here are qualitative, based on April 2026 third-party analysis.
- **CT sentiment is inferred** from articles, not from raw X data (LunarCrush paywalled). No verified engagement/sentiment metrics.
- **Exact dates for "early June 2026" MegaETH launch** not pinned to a day; sourced from CoinMarketCap's AI-generated updates page, which should be double-checked against GMX's official announcement.
- Price/mcap figures vary by aggregator ($5.43–$6.28 across CMC, CoinGecko, Blo