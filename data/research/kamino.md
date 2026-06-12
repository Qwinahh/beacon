# kamino — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| KMNO price | $0.02016 (+1.1% 24h, +14.0% 7d) | 2026-06-11 | https://www.coingecko.com/en/coins/kamino |
| Market cap | $87,752,527 (rank #298) | 2026-06-11 | https://www.coingecko.com/en/coins/kamino |
| FDV | $200,717,766 (Mcap/FDV 0.44) | 2026-06-11 | https://www.coingecko.com/en/coins/kamino |
| Circulating supply | 4,371,918,043 KMNO (max 10B) | 2026-06-11 | https://www.coingecko.com/en/coins/kamino |
| 24h volume | $6,199,948 | 2026-06-11 | https://www.coingecko.com/en/coins/kamino |
| TVL — Kamino combined (DeFiLlama API) | $1.4396B | 2026-06-11 | https://api.llama.fi/tvl/kamino |
| TVL — Kamino Lend (DeFiLlama API) | $1.2940B | 2026-06-11 | https://api.llama.fi/tvl/kamino-lend |
| TVL — Kamino Liquidity (DeFiLlama API) | $141.7M | 2026-06-11 | https://api.llama.fi/tvl/kamino-liquidity |
| TVL shown on CoinGecko (DeFiLlama-sourced) | $1.806B (Mcap/TVL 0.05) | 2026-06-11 | https://www.coingecko.com/en/coins/kamino |
| Total deposits (gross supply, incl. borrows) | $2.68B (+10.1% MoM); total debt $1.08B (+11.4%) | May 2026 month-end (report 2026-06-05) | https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880 |
| Protocol utilization | 40.5% | May 2026 | https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880 |
| Interest paid (monthly) | $5.36M (+12% MoM), avg borrow rate ~5.9% | May 2026 | https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880 |
| Lending-vault deposits | $587M | May 2026 month-end | https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880 |
| ATH / ATL | ATH $0.2478 (-91.9%); ATL $0.01643 on 2026-03-28 | 2026-06-11 | https://www.coingecko.com/en/coins/kamino |
| Next unlock | 229.17M KMNO (2.3% of total supply) on June 30, 2026 | 2026-06-11 search | https://dropstab.com/coins/kamino-finance |

## What it does well / Solana lending meta

- **Largest money market on Solana.** Kamino holds the top TVL slot among Solana DeFi protocols on DeFiLlama in Q2 2026. Kamino Lend was cited at $1.48B TVL (2026-04-27, per DeFiLlama via Backpack), ahead of marginfi (~$700M), Save/ex-Solend (~$400M), and Drift spot lending (~$300M). Sources: https://learn.backpack.exchange/articles/best-solana-lending-protocols, https://defillama.com/protocol/kamino
- **Three core products:** Kamino Lend (money market), Multiply (one-click leveraged looping, e.g. LST/SOL and stablecoin yield loops up to 12.5x in the Ethena market), and automated concentrated-liquidity LP vaults (Kamino Liquidity, the original product, now ~$142M TVL per DeFiLlama API, 2026-06-11).
- **V2 modular architecture:** curated Earn Vaults run by external risk curators (Steakhouse, Re7, Allez, MEV Capital, Rockaway, Sentora), permissionless/isolated market creation, Pro Borrow dashboard. Source: https://www.rockawayx.com/insights/kamino-launches-v2-ushering-in-a-new-era-of-modular-credit-infrastructure-on-solana
- **Competitive edge per third-party writeups:** liquidity flywheel (LP vaults seed lending pools → deeper books, tighter rates) and ~2,000 daily active users vs ~400 for marginfi. marginfi's edge is cleaner global-account UX; Save retains long-tail asset coverage but has lost share since 2023. Sources: https://eco.com/support/en/articles/14801186-kamino-lending-solana-s-money-market-explained, https://eco.com/support/en/articles/15083168-marginfi-solana-lending-protocol-guide
- **Institutional/RWA angle:** isolated markets for RWAs (PRIME, syrupUSDC, ONyc), tokenized stocks (xStocks market, 92% utilized per Solana case study), and reinsurance (OnRe, $152M, top-five market). Sources: https://solana.com/news/case-study-xstocks, https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880
- Solana DeFi TVL overall cited at ~$5.5B (May 2026, per Eco), making Kamino roughly a quarter-plus of the chain's DeFi TVL. Source: https://eco.com/support/en/articles/13225733-solana-defi-apps-top-protocols-2026

## Recent developments (last 30 days)

- **2026-05-13 — Ethena USDe/USDG Multiply market launched** (isolated, up to 12.5x looping USDe vs USDG). Passed $400M supply and hit its $200M USDG borrow cap within a day — fastest market ramp in Kamino history; closed May at $483.2M supply / $211.7M debt, now the protocol's 2nd-largest market. Sources: https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880, https://x.com/kamino/status/2054578964816167158
- **2026-05-14 — xStocks borrow-incentive campaign live:** $50K USDC borrow rewards across SPYx, TSLAx etc. over three months; xStocks market grew +24.2% to $31M in May. Source: https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880
- **2026-05-20 — "Credit Mode" on XPlace, powered by Kamino** (borrow against assets while retaining exposure/yield). Source: https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880
- **2026-05-22 — Network-wide Pyth oracle outage** absorbed by Kamino's Scope oracle infra with no bad debt or adverse liquidations; Scope upgraded afterward. Source: https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880
- **2026-05-28 — STRCx market launched** (up to 2x leverage, 50% max LTV). Source: https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880
- **2026-06-01 — Bitwise's $259M tokenized fund accepts Kamino as collateral protocol** alongside Aave and Morpho — institutional trust signal. Source: https://coinmarketcap.com/cmc-ai/kamino-finance/latest-updates/
- **2026-06-04 — Coinbase backs Ethena's Solana expansion** (strategic investment/partnership expected to funnel Coinbase users toward Ethena products hosted on Kamino). Source: https://coinmarketcap.com/cmc-ai/kamino-finance/latest-updates/
- **2026-06-05 — May risk report published (Allez Labs):** supply +10.1% to $2.68B; stablecoin share jumped 33% → 44.8%; liquidations down 95% to 491 events ($0.51M seized); Main market share fell 52% → 42% as Ethena scaled. Source: https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-may-2026/880
- **2026-06-30 (upcoming) — token unlock:** 229.17M KMNO (2.3% of total supply) to Core Contributors and Key Stakeholders/Advisors. Source: https://dropstab.com/coins/kamino-finance

## CT sentiment

- Aggregated tweet sentiment (per Coinbase/CMC-tracked data surfaced 2026-06-11, sample of 94 tweets): 38.2% bullish, 5.6% bearish, 61.8% neutral — mildly positive, low-volume conversation. Sources: https://www.coinbase.com/price/kamino-finance, https://coinmarketcap.com/cmc-ai/kamino-finance/latest-updates/
- Dominant narratives: (1) the Ethena USDe/USDG market's explosive ramp ($400M in 24h, borrow cap hit in a day — Kamino's own X posts, May 13–14, did the rounds); (2) "fundamentals vs price" disconnect — protocol at/near top of Solana TVL while KMNO sits ~92% below ATH and printed an all-time low ($0.01643) as recently as 2026-03-28; (3) institutional/RWA adoption (Bitwise, xStocks, OnRe) as the bull case. Sources: https://x.com/kamino/status/2055023133388599682, https://www.coingecko.com/en/coins/kamino
- Bear-side chatter centers on supply overhang: Mcap/FDV of 0.44 and recurring monthly unlocks (next: June 30, 2.3% of supply). Source: https://dropstab.com/coins/kamino-finance
- Note: no direct X/Twitter firehose access in this research pass — sentiment above is from aggregator-tracked tweet stats and protocol/news coverage, not first-hand timeline reading.

## Caveats

- **TVL figures vary by definition.** DeFiLlama API combined TVL = $1.44B (2026-06-11); CoinGecko displays $1.806B (also attributed to DeFiLlama); the Kamino forum reports $2.68B gross deposits (which includes looped/borrowed capital); search snippets cited "$2.2B", "$2.43B", and "nearly $3B". Treat $1.4–1.8B (net) and ~$2.7B (gross deposits) as the defensible range; do not tweet a single TVL number without specifying net vs gross.
- **Price snapshots conflicted:** one search summary returned $0.01511 / ~$72–91M mcap, but the live CoinGecko page fetched 2026-06-11 showed $0.02016 / $87.75M mcap. The CoinGecko live fetch is treated as authoritative here; KMNO is volatile (+14% on the week), so refresh before posting.
- **"V2 went live at the end of May" (per one search summary) could not be year-verified.** The Rockaway article on Kamino V2 is undated in our results; V2 features (curated vaults, modular markets) are clearly live as of the May 2026 risk report. Avoid tweeting a specific V2 launch date.
- **Unlock USD value unverified:** the "$3.46M" figure attached to the June 30 unlock was computed at the stale $0.0151 price; at $0.02016 it would be ~$4.6M. Verify against a live unlocks tracker before citing.
- **No KMNO buyback program was verifiable** in these searches — only speculative language ("revenue could support buybacks"). Do not claim a buyback exists.
- **CT sentiment is thin:** based on a 94-tweet aggregator sample, not direct timeline analysis. marginfi/Save competitor TVL figures (~$700M/~$400M) come from a Backpack Learn article (April 2026 data) and were not independently re-verified on DeFiLlama.
- Daily-active-user comparison (2,000 vs 400) comes from Eco support-article marketing-adjacent content; treat as directional, not exact.
