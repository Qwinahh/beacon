# btc-l2s — research (2026-06-12)

## Per-chain table

| Chain | TVL (DeFi) | As of | Trend | Verdict | Source URL |
|---|---|---|---|---|---|
| Stacks | $95.4M | 2026-06-12 | -24% 30d ($125.8M on 2026-05-13), roughly flat y/y ($105.0M on 2025-06-12) | REAL (the most real of the four) — plus ~$437M sBTC bridged BTC on top of DeFi TVL | https://defillama.com/chain/Stacks (data: api.llama.fi/v2/historicalChainTvl/Stacks) |
| Rootstock | $92.5M | 2026-06-12 | -26% 30d ($124.3M on 2026-05-13), -67% y/y ($278.1M on 2025-06-12) | REAL but stagnant/declining — OG sidechain, real protocols, no growth | https://defillama.com/chain/Rootstock (data: api.llama.fi/v2/historicalChainTvl/Rootstock) |
| Core (Core DAO) | $6.3M | 2026-06-12 | COLLAPSED: -34% 30d ($9.5M on 2026-05-13), -98% y/y ($399.8M on 2025-06-12) | NARRATIVE — effectively dead on-chain; token down catastrophically | https://defillama.com/chain/CORE (data: api.llama.fi/v2/historicalChainTvl/Core) |
| BOB (Build on Bitcoin) | $9.5M | 2026-06-12 | -13% 30d ($10.9M on 2026-05-13), -94% y/y ($164.6M on 2025-06-12) | NARRATIVE with credible tech — BitVM work is real, usage is not | https://defillama.com/chain/BOB (data: api.llama.fi/v2/historicalChainTvl/BOB) |

Token snapshot (CoinGecko simple-price API, 2026-06-12):
- STX: $0.184, mcap $341.6M — https://www.coingecko.com/en/coins/stacks
- CORE: $0.0272, mcap $33.6M — https://www.coingecko.com/en/coins/core
- BOB: $0.00562, mcap $17.0M — https://coinmarketcap.com/currencies/bob-build-on-bitcoin/
- RBTC: $63,481 (1:1 BTC peg holding; BTC = $63,772 same source/date); RIF: $0.0638, mcap $63.3M — https://www.coingecko.com/en/coins/rootstock-smart-bitcoin
- Reference: BTC $63,772, mcap $1.279T (CoinGecko, 2026-06-12)

## Detail per chain

### Stacks — REAL, but cooling
- What's real: sBTC is the substance. Stacks' own Q1 2026 snapshot reports sBTC closed Q1 2026 at $437M TVL (peaked at $545M during the quarter), 320+ BTC added to its staking pilot, plus Fireblocks support, Circle USDC launch on Stacks, and a publicly trading Grayscale Stacks Trust (https://www.stacks.co/blog/q1-2026-snapshot). DeFi TVL on DeFiLlama is $95.4M (2026-06-12) — note this is separate from/lower than bridged sBTC. Nakamoto upgrade (fast blocks) completed end-2025.
- What's narrative: STX price ($0.184, mcap $341.6M, 2026-06-12) has not followed sBTC adoption; DeFi TVL fell ~24% in the last 30 days. "Institutional BTCfi" framing is still mostly forward-looking (Q2 2026 roadmap items: sBTC trustless withdrawals, CEX listings, tier-1 stablecoin depth).

### Rootstock — REAL but a museum piece
- What's real: longest-running BTC sidechain, $92.5M DeFi TVL (DeFiLlama, 2026-06-12), 1:1 PowPeg holding (RBTC $63,481 vs BTC $63,772, CoinGecko 2026-06-12). Real protocols: Sovryn, Money on Chain, plus Sushi, Beefy, Oku deployments; claims 150+ ecosystem partners (https://rootstock.io/). PowPeg Composition Change shipped Feb 2026, expanding the federated signer set (reported via 2026 BTC-L2 roundups, e.g. https://bitcoinfoundation.org/news/analysis/best-bitcoin-layer-2-projects-2026/).
- What's narrative: growth. TVL is down 67% y/y and 26% in 30d; no major new catalysts surfaced in May–June 2026 searches.

### Core (Core DAO) — NARRATIVE, near-dead on-chain
- What's real: chain still runs; Satoshi Plus consensus and Colend (lending) were the flagship story.
- What's narrative: almost everything now. DeFi TVL collapsed from $399.8M (2025-06-12) to $6.3M (2026-06-12) — a -98% y/y wipeout per DeFiLlama. CORE token crashed ~50% in 24h on 2026-03-30 in a leveraged unwind (per CoinMarketCap CMC-AI updates, https://coinmarketcap.com/cmc-ai/core-dao/latest-updates/) and sits at $0.0272 / $33.6M mcap (CoinGecko, 2026-06-12). Older articles still citing "$353M TVL" are stale. Avoid bullish framing on Core.

### BOB (Build on Bitcoin) — tech-credible NARRATIVE
- What's real: engineering output. BitVM3 dispute cost reportedly cut 87% to ~$11/dispute; BitVM trust-minimized bridge mainnet targeted early 2026; March 2026 dev sprint merged 234 PRs; pivoting to a consumer "Bank of Bitcoin" app (swap/save/earn/borrow) (https://www.gobob.xyz/, https://docs.gobob.xyz/docs/bitvm/, https://gobob.xyz/blog/best-of-bob-2025).
- What's narrative: usage. DeFi TVL $9.5M (2026-06-12), down 94% from $164.6M a year ago (DeFiLlama). BOB token at $0.00562 / $17.0M mcap (CoinGecko, 2026-06-12) — micro-cap territory. The BitVM story is the bet; current traction does not support it yet.

## BTCfi meta state

Dormant-to-contracting, not dead. Every one of the four chains lost DeFi TVL over the last 30 days (2026-05-13 → 2026-06-12, DeFiLlama), and two (Core, BOB) are down 94–98% y/y. 2026 roundups describe Bitcoin L2 TVL shrinking dramatically this year (one widely-cited figure: BTC-L2 TVL down >74% YTD, BTCfi cumulative TVL ~91k BTC ≈ 0.46% of supply — see https://www.dextools.io/news/top-5-bitcoin-layer-2-solutions-btcfi-2026 and https://www.vaasblock.com/news/bitcoin-layer2-lightning-bitvm-defi-ecosystem-2026/; exact attribution caveat below). The broader DeFi backdrop is also weak: the Kelp DAO exploit triggered a ~$13B two-day DeFi TVL drop in April 2026 (https://www.coindesk.com/markets/2026/04/20/defi-tvl-drops-more-than-usd13-billion-in-two-days-following-kelp-dao-hack), dragging everything down with it. The two live threads keeping BTCfi interesting: (1) Stacks sBTC + institutional rails (Fireblocks, Circle, Grayscale), and (2) BitVM-based trust-minimized bridges (BOB, Citrea). L2 builders are explicitly pitching BTCfi as an institutional product now (https://www.coindesk.com/business/2026/02/12/bitcoin-layer-2-builders-pitch-btcfi-as-the-next-institutional-unlock). Bitcoin mainnet itself holds $4.17B in DeFiLlama-tracked TVL (2026-06-12), dwarfing all its L2s combined.

## Recent developments (last 30 days)

- 2026-06-12 — 30-day TVL bleed across all four: Stacks $125.8M→$95.4M, Rootstock $124.3M→$92.5M, Core $9.5M→$6.3M, BOB $10.9M→$9.5M (2026-05-13 vs 2026-06-12, api.llama.fi/v2/historicalChainTvl, https://defillama.com).
- 2026-05-13 — Coin Bureau published a fully refreshed Stacks review covering post-Nakamoto direction, sBTC growth, and BTC finality changes (https://coinbureau.com/review/stacks-stx).
- Q2 2026 (in progress) — Stacks roadmap items due this quarter: trustless sBTC withdrawals, sBTC CEX listings, tier-1 stablecoin (USDC) liquidity deepening (https://www.stacks.co/blog/q1-2026-snapshot).
- 2026-05-05 — Rootstock status page reporting all services (explorer, bridges, stats) operating normally; no incidents, but also no major announcements found in the window (https://status.rsk.co/).
- No notable Core DAO or BOB headlines surfaced in the 2026-05-13→2026-06-12 window in searches; the most recent dated events are older (Core token crash 2026-03-30; BOB 234-PR sprint March 2026).

## Caveats

- All "DeFi TVL" figures are DeFiLlama chain TVL (api.llama.fi, pulled 2026-06-12). This EXCLUDES bridged/native BTC not deposited in DeFi protocols — which is why Stacks shows $95M DeFi TVL while sBTC bridged TVL was ~$437M at Q1 2026 close (Stacks' own blog; could not independently re-verify the current June sBTC figure — DeFiLlama's sBTC protocol slug returned "not found").
- The ">74% YTD Bitcoin L2 TVL decline" and "91,332 BTC BTCfi TVL / 0.46% of supply" figures came from search-result summaries of 2026 roundup articles; I could not pin each number to a specific page. Treat as directionally right (consistent with DeFiLlama data) but verify before quoting precisely.
- Conflicting stale data is common: CMC-AI pages still cite Core TVL at "$353M" and some price pages showed RBTC at "$75k"; both contradict live API data ($6.3M and $63,481 respectively, 2026-06-12). Trust the API figures.
- BOB token price/mcap is from CoinGecko id "bob-build-on-bitcoin" (rank ~900); low liquidity, figures may be noisy.
- Could not verify whether BOB's BitVM bridge actually hit mainnet ("early 2026" was the announced target; no confirmation found).
- Merlin Chain claim of "$1.7B TVL" in one search result is stale/wrong — DeFiLlama shows Merlin at $7.7M (2026-06-12).
- All token prices are point-in-time snapshots from CoinGecko's simple-price API on 2026-06-12.
