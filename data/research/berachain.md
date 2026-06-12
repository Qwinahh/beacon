# berachain — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| BERA price | $0.250 (CoinPaprika $0.2501; CoinCodex $0.2502; Crypto.com last $0.2495) | 2026-06-11 ~21:30 UTC | https://api.coinpaprika.com/v1/tickers/bera-berachain ; https://coincodex.com/api/coincodex/get_coin/BERA |
| BERA circulating supply | 276,568,107 | 2026-06-11 | https://coincodex.com/api/coincodex/get_coin/BERA |
| BERA market cap | ~$69M implied (276.57M × $0.2502); press cited $66–67M on 2026-06-06 | 2026-06-11 / 2026-06-06 | https://coincodex.com/api/coincodex/get_coin/BERA ; https://cryptodaily.co.uk/2026/06/berachain-pol-next-mainnet-incentives |
| BERA all-time high | $15.01 (CoinPaprika) / $14.79 (CoinCodex), -98.3% from ATH | 2025-02-06 | https://api.coinpaprika.com/v1/tickers/bera-berachain |
| BERA all-time low | $0.227 — set THIS WEEK | 2026-06-10 | https://coincodex.com/api/coincodex/get_coin/BERA |
| BERA 30d / 1y price change | -37.3% / -89.7% | 2026-06-11 | https://coincodex.com/api/coincodex/get_coin/BERA |
| 24h volume | ~$13.8M (CoinPaprika) / ~$26.2M (CoinCodex) | 2026-06-11 | https://api.coinpaprika.com/v1/tickers/bera-berachain ; https://coincodex.com/api/coincodex/get_coin/BERA |
| Chain TVL (DeFiLlama) — now | $54.7M | 2026-06-10 | https://api.llama.fi/v2/historicalChainTvl/Berachain |
| Chain TVL — all-time peak | $3.31B | 2025-03-27 | https://api.llama.fi/v2/historicalChainTvl/Berachain |
| Chain TVL — mainnet launch day | $777M (day 1), $2.2B within first week (Boyco deposits) | 2025-02-06 to 2025-02-13 | https://api.llama.fi/v2/historicalChainTvl/Berachain |
| TVL drawdown peak → now | ~-98.3% ($3.31B → $54.7M) | 2026-06-10 | https://api.llama.fi/v2/historicalChainTvl/Berachain |
| TVL 1 year ago vs now | ~$773M (2025-06-08) → $54.7M (-93% y/y) | 2026-06-10 | https://api.llama.fi/v2/historicalChainTvl/Berachain |
| Native / bridged TVL (press) | Native ≈ $106M; Bridged ≈ $204M | 2026-06-06 | https://cryptodaily.co.uk/2026/06/berachain-pol-next-mainnet-incentives |

Mainnet status: live since 2025-02-06 (Blockworks: https://blockworks.co/news/berachain-mainnet-debuts). TVL trend is a near-uninterrupted bleed: $3.31B peak (Mar 2025) → ~$810M (Jun 2025) → ~$173M (Jan 2026) → $54.7M (Jun 2026). Chain still operating; major "PoL Next" tokenomics overhaul activates on mainnet 2026-06-23.

## Tritoken / PoL mechanics today

The original tritoken design — BERA (gas/staking), BGT (non-transferable, emissions-directing governance token earned by LPing in reward vaults), HONEY (native stablecoin) — is being dismantled. The "PoL Next" upgrade (announced 2026-05-21, testnet Bepolia 2026-05-26/27, mainnet 2026-06-23, deploying ~24h before Berachain's Fusaka hardfork) effectively ends the tritoken era. Source: https://docs.berachain.com/general/proof-of-liquidity/changelog and https://forum.berachain.com/t/pol-next-turning-emissions-into-a-growth-engine/1618

Per the official docs changelog (fetched 2026-06-11):
- **BGT is deprecated.** No more user-facing role: no governance, no validator boost, no influence on emissions. Hub UI lets holders redeem/migrate BGT; residual BGT on vaults auto-converts to WBERA on next claim.
- **Emissions paid in WBERA.** Boost curve removed; per-block emission is now fixed: 0.4 WBERA `baseRate` to the validator operator + 1.305 WBERA `rewardRate` to reward vaults.
- **sWBERA is the new value sink.** Incentives (net of validator commission, capped 20%) are auctioned for BERA and accrue to sWBERA stakers. Stakers claim rewards as sWBERA or native BERA. "One token, one yield path, one value sink."
- **Emissions Return Agreements (ERAs):** multi-month guaranteed emission streams to teams that generate on-chain revenue — replacing per-epoch incentive bidding; framed as "growth-equity financing with protocol capital."
- **Staking pools (live Feb 2026):** validator-operated liquid staking with stBERA shares.
- HONEY remains the ecosystem stablecoin in docs, but no recent updates surfaced (see Caveats).

Earlier evolution: enshrined PoL / BRIP-0004 (Aug 2025), BERA staking + 20% validator commission cap (Jul 2025), incentive caps and 10% inflation target (Apr 2025). Source: https://docs.berachain.com/general/proof-of-liquidity/changelog

## Key ecosystem protocols

TVLs from DeFiLlama protocol endpoints, fetched 2026-06-11:

| Protocol | Role | TVL | Source URL |
|---|---|---|---|
| Kodiak | Leading native DEX / liquidity hub | $46.5M | https://api.llama.fi/tvl/kodiak |
| Infrared Finance | Liquid staking / PoL infrastructure (iBGT/iBERA) | $30.2M | https://api.llama.fi/tvl/infrared-finance |
| BEX | Berachain's native DEX | $1.02M | https://api.llama.fi/tvl/bex |
| Beraborrow | Native CDP stablecoin (NECT) | $0.32M | https://api.llama.fi/tvl/beraborrow |
| Dolomite | Lending/DEX, deployed to Berachain Mar 2026 | $117.6M cross-chain total (NOT Berachain-only) | https://api.llama.fi/tvl/dolomite |
| BEND | Official lending protocol ("credit layer"), launched by Berachain | TVL not verified | https://coinmarketcap.com/cmc-ai/berachain/latest-updates/ |

Note: Kodiak + Infrared alone roughly account for the chain's ~$55M TVL; the long tail is tiny. Boyco-era partners (EtherFi, Lombard, Ethena, Concrete, StakeStone, Origami) largely correspond to bridged TVL that has mostly exited.

## Recent developments (last 30 days)

- **2026-05-21** — "PoL Next: Turning Emissions Into a Growth Engine" published on the official forum: sunset BGT and boost, consolidate value accrual into sWBERA, introduce ERAs; code + Zenith and Cantina/Spearbit audits linked. https://forum.berachain.com/t/pol-next-turning-emissions-into-a-growth-engine/1618
- **2026-05-26/27** — PoL Next + Fusaka (BRIP-0010) activated on Bepolia testnet. https://docs.berachain.com/general/proof-of-liquidity/changelog ; https://forum.berachain.com/t/brip-0010-fusaka-hardfork-specification/1609
- **2026-06-23 (upcoming)** — PoL Next mainnet activation, ~24h before the Fusaka hardfork. BGT holders must redeem/migrate via hub.berachain.com after the fork. https://docs.berachain.com/general/proof-of-liquidity/changelog
- **2026-06-06** — Press review of PoL Next: DeFi TVL ~$55M, native ~$106M, bridged ~$204M, mcap ~$66–67M at ~$0.24; questions whether incentive redesign can survive post-hype liquidity. https://cryptodaily.co.uk/2026/06/berachain-pol-next-mainnet-incentives
- **2026-06-10** — BERA printed a fresh all-time low of $0.227 (CoinCodex ATL data), bouncing ~+8-10% on 2026-06-11. https://coincodex.com/api/coincodex/get_coin/BERA
- **May 2026 (ongoing)** — Foundation's "Bera Builds Businesses" (BBB) revenue pivot: build/acquire/partner with 3–5 cash-flow-generating apps; BEND lending launch is part of this push. Week of 2026-05-06 saw $8.91M gross inflows. https://coinmarketcap.com/cmc-ai/berachain/latest-updates/ ; https://thedefiant.io/news/blockchains/berachain-rallies-40-after-unveiling-bera-builds-businesses-plan

## CT sentiment

- Bleeding, with a contrarian-hopium pocket. A June 2026 commentary noted there is "almost zero positive Berachain sentiment on X other than from the few hardcore beras" (https://cryptodaily.co.uk/2026/06/berachain-pol-next-mainnet-incentives).
- CMC AI's aggregated take (2026-06): consensus is mixed — bullish on the strategic pivot to real revenue (BBB, ERAs, sWBERA) vs bearish on "evaporating retail sentiment and community trust" after a ~97-98% drawdown in both token and TVL (https://coinmarketcap.com/cmc-ai/berachain/latest-updates/).
- The Defiant reported BERA rallied ~40% when the BBB plan was unveiled, showing the pivot narrative can still move price (https://thedefiant.io/news/blockchains/berachain-rallies-40-after-unveiling-bera-builds-businesses-plan).
- Net read for bot content: ecosystem is alive (active hardfork pipeline, audited tokenomics overhaul, official lending launch) but capital and attention have overwhelmingly left; the June 23 PoL Next activation is the key near-term catalyst/risk event.

## Caveats

- **Market cap discrepancy:** CoinPaprika reports mcap $26.9M (2026-06-11) using an apparently stale ~107M circulating supply (the launch-era figure). CoinCodex's 276.57M circulating supply implies ~$69M, consistent with the $66–67M cited by CryptoDaily on 2026-06-06. I treat ~$66–69M as correct; could not confirm against CoinGecko (API returned empty responses on multiple attempts, 2026-06-11).
- **BEX TVL ($1.02M)** comes from DeFiLlama slug "bex"; I could not independently confirm this slug maps to Berachain's native BEX. Treat with caution.
- **Dolomite's $117.6M is multi-chain** (Arbitrum etc.); its Berachain-only TVL was not verified.
- **Per-protocol vs chain TVL:** Kodiak ($46.5M) + Infrared ($30.2M) > chain TVL ($54.7M) because DeFiLlama chain TVL excludes double-counted/liquid-staking categories. Do not sum protocol TVLs.
- **HONEY:** No recent (2026) data found on HONEY supply, peg health, or redesign in my searches — unverified. Docs still list it; do not tweet specific HONEY numbers.
- **BBB announcement exact date** not verified (The Defiant article undated in results; its "$0.4165" price quote implies it predates June 2026). CMC AI summaries place the pivot in May 2026.
- One search summary referenced "$3.2B TVL" in 2026 context — that is the stale 2025 Boyco-era peak, not current; current chain TVL is ~$55M.
- CT sentiment is sourced from secondary articles/aggregators, not direct X scraping; the 37.8% bullish / 5.4% bearish tweet stat circulating on aggregator sites is low-quality and was excluded.
- BERA staking APR, validator count, and