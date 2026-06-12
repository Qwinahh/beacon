# lido — research (2026-06-12)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| Lido TVL | $18.666B (Ethereum $18.662B, Solana $4.23M) | 2026-06-12 (live fetch) | https://defillama.com/protocol/lido |
| Lido ETH staked (protocol-reported) | ~9.17M ETH / ~$19.42B TVL | 2026-03-27 (per search result citing Lido institutional page) | https://lido.fi/ |
| Lido share of all staked ETH | ~24.2% (8,721,598 ETH) per Datawallet; ~28–28.1% per Coin Bureau / BingX 2026 reviews | early–mid 2026 (sources vary) | https://www.datawallet.com/crypto/ethereum-staking-statistics-and-trends ; https://coinbureau.com/review/lido-finance-review |
| LDO price | $0.34 (DeFiLlama) / $0.2676 (CoinGecko, per search snippet) | 2026-06-12 | https://defillama.com/protocol/lido ; https://www.coingecko.com/en/coins/lido-dao |
| LDO market cap | $290.91M (DeFiLlama) / ~$226.1M (CoinGecko) / ~$225.5M (CoinMarketCap) | 2026-06-12 | https://defillama.com/protocol/lido ; https://coinmarketcap.com/currencies/lido-dao/ |
| LDO FDV | $342.63M | 2026-06-12 | https://defillama.com/protocol/lido |
| LDO vs ATH | ATH $7.30; trading ~96% below ATH; DeFiLlama lists all-time low at $0.27 (i.e., price is near ATL territory) | 2026-06-12 | https://www.coingecko.com/en/coins/lido-dao ; https://defillama.com/protocol/lido |
| stETH yield (avg APY, DeFiLlama tracked pool) | 2.36% | 2026-06-12 | https://defillama.com/protocol/lido |
| Lido fees (30d) | $45.2M (annualized $551.4M) | 2026-06-12 | https://defillama.com/protocol/lido |
| Lido protocol revenue (30d) | $4.52M (annualized $55.14M; 10% fee on staking rewards) | 2026-06-12 | https://defillama.com/protocol/lido |
| Lido DAO treasury | $116.02M | 2026-06-12 | https://defillama.com/protocol/lido |
| Rocket Pool TVL | $1.13B | 2026-06-12 (live fetch) | https://defillama.com/protocol/rocket-pool |
| rETH yield (avg APY, DeFiLlama) | 1.99% | 2026-06-12 | https://defillama.com/protocol/rocket-pool |
| RPL price / mcap | $1.95 / $43.91M | 2026-06-12 | https://defillama.com/protocol/rocket-pool |
| Binance staked ETH TVL (no. 2 LST) | $7.737B–$8.386B (two DeFiLlama page snapshots same day) | 2026-06-12 | https://defillama.com/protocol/binance-staked-eth |
| CSM + SimpleDVT combined stake | ~800,000 ETH = 2.2% of ALL Ethereum stake | 2026-01-01 | https://blog.lido.fi/lido-validator-and-node-operator-metrics-q4-2025/ |

## Market share trend + DVT/CSM status

- **Share of staked ETH:** 2026 sources put Lido between ~24.2% (Datawallet, early 2026) and ~28% (Coin Bureau, BingX). Older coverage of the centralization debate referenced Lido "often exceeding 30%" of staked ETH (CCN review), so the directional read is **flat-to-shrinking** from the >30% era — but I could not pin down a clean time series in these searches (see Caveats). Sources: https://www.datawallet.com/crypto/ethereum-staking-statistics-and-trends , https://coinbureau.com/review/lido-finance-review , https://www.ccn.com/crypto-investing/reviews/lido/
- **CSM (Community Staking Module):** Lido's first permissionless-entry module (bonded, open to solo stakers). LDO holders approved raising CSM's stake-share limit from 3% to 5% in late September 2025. Source: https://blog.lido.fi/lido-validator-and-node-operator-metrics-q4-2025/ , https://operatorportal.lido.fi/modules/community-staking-module
- **SimpleDVT:** target stake share raised from 4% to 4.3% in December 2025. Source: https://blog.lido.fi/lido-validator-and-node-operator-metrics-q4-2025/
- **Combined decentralized modules:** CSM + SimpleDVT = ~800k ETH, or 2.2% of total Ethereum stake as of 2026-01-01 (Lido Q4 2025 metrics blog). So community/DVT staking is real but still a single-digit share of Lido's own book — it softens, not eliminates, the centralization critique.
- **Next step — IDVTC:** a proposed "Identified DVT Cluster" operator type would let verified independent stakers pool into distributed validator clusters with lower collateral; targeted to ship with CSM v3 in Q2–Q3 2026. Source: https://crypto.news/lidos-community-staking-module-sharpens-its-edge-with-dvt-clusters/
- **Governance angle:** Dual Governance (stETH-holder veto over LDO votes) is live and frequently cited as a decentralization counterweight. Source: https://www.bitget.com/news/detail/12560604845055

## Rocket Pool comparison

| Dimension | Lido | Rocket Pool | As of / Source |
|---|---|---|---|
| TVL | $18.666B | $1.13B (~16.5x smaller) | 2026-06-12, https://defillama.com/protocol/lido , https://defillama.com/protocol/rocket-pool |
| Yield (DeFiLlama avg APY) | 2.36% (stETH) | 1.99% (rETH) | 2026-06-12, same DeFiLlama pages |
| Protocol revenue | 10% fee on rewards (~$55.1M annualized) | DeFiLlama: "protocol doesn't take any fees or rewards cut" (revenue $0) | 2026-06-12, DeFiLlama pages |
| Decentralization | Modular: curated set + SimpleDVT + permissionless CSM (CSM+SDVT = 2.2% of all ETH stake, 2026-01-01) | Fully permissionless node operators; 8 ETH + RPL bond minipools; widely called the most decentralized major LST | https://blog.lido.fi/lido-validator-and-node-operator-metrics-q4-2025/ , https://coincodex.com/article/27799/lido-vs-rocket-pool-which-eth-staking-solution-is-best/ |
| Liquidity | stETH deepest LST liquidity | rETH thinner; more slippage on large swaps | https://passiveyieldlab.com/blog/lido-vs-rocket-pool-vs-eigenlayer-2026/ |
| Token | LDO $0.27–0.34, mcap ~$226–291M | RPL $1.95, mcap $43.91M | 2026-06-12, DeFiLlama / CoinGecko |

Note: Passive Yield Lab (2026) quoted Rocket Pool APR at ~2.39% with a ~0.6pp gap vs Lido, which conflicts with DeFiLlama's same-day 1.99% vs 2.36%. Treat exact APRs as ~2–2.5% with the spread favoring stETH.

## Recent developments (last 30 days)

- **2026-06-03 — Staking Router v3 (LIP-35) announced.** Moves from count-based to balance-based validator accounting (post-Pectra EIP-7251, validators up to 2048 ETH), adds TopUpGateway with Merkle-proof-secured deposits, a deposit reserve, and a consolidation pipeline for migrating stake between modules (Curated Module v1 → v2). Snapshot vote late June 2026; audits to finish early July; mainnet tentatively July 2026; phased migration through ~Q1 2027. Explicitly the foundation for LIP-33 (CSM v3 + Curated Module v2). Source (published 2026-06-04): https://cryptobriefing.com/lido-staking-router-v3-ethereum/
- **Ongoing (announced earlier in 2026, still active this month) — Lido V3 / stVaults + ValMart roadmap.** stVaults target 1M ETH staked by end-2026; ValMart is a planned validator marketplace; Lido Earn vaults for DeFi strategies. Exact announcement dates not confirmed in this research pass. Source: https://www.ainvest.com/news/lido-2026-transition-staking-infrastructure-defi-platform-2511/
- **Date unconfirmed — WisdomTree Ethereum staking fund using stETH** ("first to market," per The Block headline; article was paywalled/unfetchable so the publish date could not be verified — do not tweet a date for this). Source: https://www.theblock.co/post/381549/wisdomtree-first-market-ethereum-staking-fund-lido-steth
- **Date unconfirmed — Hex Trust integrates stETH** for institutional liquid staking + custody. Source: https://thefintechtimes.com/hex-trust-integrates-lidos-steth-to-offer-institutional-liquid-staking-and-custody/

## CT sentiment

- Aggregated tweet-sentiment trackers (surfaced via Coinbase/BYDFI price pages, June 2026): ~69.0% of tweets bullish on LDO vs ~7.9% bearish, average social sentiment ~4.6/5. Provenance/date of the underlying sample is unclear — use as a soft signal only. Sources: https://www.coinbase.com/price/lido-dao , https://www.bydfi.com/en/cointalk/lido-token-news
- The dominant bear narrative on CT is the old one with a new twist: LDO sits ~96% below its $7.30 ATH and near its listed all-time low (~$0.24–0.27) despite Lido doing ~$551M in annualized fees — the "great protocol, valueless token" critique, since LDO holders receive $0 of revenue (DeFiLlama: Holders Revenue $0, 2026-06-12). https://defillama.com/protocol/lido
- The centralization debate persists (Lido >24% of staked ETH) but defenders point to Dual Governance (stETH-holder veto), CSM permissionless entry, and DVT clusters as evidence the critique is stale. Sources: https://blockworks.co/news/lido-centralization-debate-ethereum , https://www.ccn.com/crypto-investing/reviews/lido/ , https://www.bankless.com/leave-lido-alone
- Newer bull narrative: 2026 pivot from pure staking infra to a DeFi/institutional platform (stVaults, ValMart, ETF-wrapper ambitions, WisdomTree/Hex Trust integrations). Source: https://www.ainvest.com/news/lido-2026-transition-staking-infrastructure-defi-platform-2511/

## Caveats

- **LDO price discrepancy:** DeFiLlama showed $0.34 / $290.9M mcap while a same-day CoinGecko search snippet showed $0.2676 / $226.1M mcap (CMC $225.5M). One of these is likely a stale cache. Verify on CoinGecko live before quoting a price in a tweet.
- **Market-share number is fuzzy:** 24.2% (Datawallet) vs ~28% (Coin Bureau/BingX) — different snapshot dates and methodologies. I could NOT verify a precise June 2026 share or a clean trend series (e.g., Dune dashboards were not fetched). The "shrinking from >30%" trend is inferred from secondary sources, not from a verified time series.
- **stETH APY:** 2.36% is DeFiLlama's "average APY" for its single tracked Lido pool on 2026-06-12, not necessarily the headline APR shown on stake.lido.fi (which I did not fetch directly).
- **WisdomTree and Hex Trust items:** publication dates unverified (The Block was unfetchable); may or may not fall within the last 30 days.
- **CT sentiment figures** (69% bullish, 4.6/5) come from third-party price-page widgets via search snippets; sample size, window, and methodology unknown. No direct X/Twitter data was pulled.
- **Binance staked ETH TVL** appeared as both $7.737B and $8.386B in two DeFiLlama page renders on the same day (cache skew).
- All figures above are exclusively from searches/