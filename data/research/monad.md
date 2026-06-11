# monad — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| Mainnet launch | Live since Nov 24, 2025 | 2026-06-11 | https://www.monad.xyz/announcements/get-started-on-monad-mainnet |
| MON token | Live (TGE at mainnet launch) | 2026-06-11 | https://www.monad.xyz/announcements/mon-tokenomics-overview |
| Airdrop | Done — claims ran Oct 14–Nov 3 2025, distributed to ~289k wallets | 2025-11-10 | https://www.monad.xyz/announcements/the-mon-airdrop-results |
| MON price | $0.02155 | 2026-06-11 | https://api.coingecko.com/api/v3/simple/price?ids=monad (CoinGecko) |
| Market cap | $254.7M | 2026-06-11 | CoinGecko API (same endpoint) |
| 24h volume | $40.4M | 2026-06-11 | CoinGecko API (same endpoint) |
| Total initial supply | 100B MON | 2025-11-10 | https://www.monad.xyz/announcements/mon-tokenomics-overview |
| Implied FDV | ~$2.15B (100B × $0.02155, my calc) | 2026-06-11 | derived from above two sources |
| Chain TVL | $361.3M | 2026-06-11 | https://api.llama.fi/v2/chains (DeFiLlama) |
| TVL trend | ~$402M (~May 25) → ~$351M (Jun 10), roughly -12% in 2 weeks | 2026-06-11 | https://api.llama.fi/v2/historicalChainTvl/Monad |
| App fees (24h / 30d) | $60.3k / $2.23M | 2026-06-11 | https://api.llama.fi/overview/fees/monad |
| Chain gas fees (24h) | ~$4,153 — very low | 2026-06-11 | https://api.llama.fi/overview/fees/monad |
| Protocols tracked on chain | 112 | 2026-06-11 | https://api.llama.fi/protocols (DeFiLlama) |
| Throughput claim | 10,000 TPS capacity, 0.4s blocks, 0.8s finality (Chainspect-cited) | 2026-02-10 | https://monadblock.com/2026/02/10/monad-mainnet-performance-140m-transactions-10k-tps-and-220m-defi-tvl-breakdown/ |
| Cumulative transactions | 140M+ by Feb 10, 2026 (≈21 TPS sustained average over first ~78 days, my calc) | 2026-02-10 | same monadblock.com article |
| Actual utilization | ~0.07% of 10k TPS capacity (third-party estimate) | 2026-06 | https://coinmarketcap.com/cmc-ai/monad/latest-updates/ |

## What's actually live

- **Mainnet is live** since Nov 24, 2025; chainId 143, token MON live and trading. Airdrop already happened (Oct–Nov 2025, ~289k wallets; 50% of some allocations locked/vesting). Sources: https://www.monad.xyz/announcements, https://www.monad.xyz/announcements/the-mon-airdrop-results
- **DeFi is real but lending/curator-dominated** (DeFiLlama protocol TVLs, 2026-06-11, https://api.llama.fi/protocols): Morpho Blue $96.3M, Euler V2 $91.9M, K3 Capital (risk curator) $61.2M, Curvance $55.7M, AFI Protocol $50.0M, Neverland $41.8M, Steakhouse Financial $33.2M, Upshift $21.7M, Mu Digital (RWA) $21.6M, Balancer V3 $17.3M, Centrifuge $15.0M, Uniswap V4 $14.9M, Tether Gold $14.3M, ShMonad (LST) $8.2M, Curve $8.0M.
- **Blue-chip EVM deployments**: Uniswap (V3+V4), Curve, Balancer, Morpho, Euler all deployed via zero-code-change EVM compatibility (2026-05, https://learn.backpack.exchange/articles/monad-ecosystem).
- **Monad-native apps**: Kuru (CLOB DEX, post-launch TVL ~$1.4M — small) and Perpl (CLOB perp DEX) are the flagship natives; ShMonad liquid staking live (https://www.panewslab.com/en/articles/d23e3106-ff4d-4c82-95b6-bc5469765527, https://learn.backpack.exchange/articles/monad-ecosystem).
- **Reality check**: DEX TVL is a small fraction of chain TVL (most TVL sits in lending vaults/curators chasing incentives via the "Monad Momentum" matching program). Chain gas fees of ~$4.2k/day (DeFiLlama, 2026-06-11) indicate organic transaction demand is thin relative to capacity.

## Recent developments (last 30 days)

- **2026-06-09** — Network update reportedly increased speed ~25%; team also deployed "Bugfinder," an internal AI-assisted vulnerability scanner for the C++ execution client and Rust consensus client. https://coinmarketcap.com/cmc-ai/monad/latest-updates/ and https://blog.monad.xyz/blog/monad-bugfinder
- **2026-06 (early)** — Draft **MIP-12** published: cut consensus voting cycle 400ms → 300ms (25% faster finality), while lowering per-block tx limit 5,000 → 3,750 and block gas limit 200M → 150M for stability. https://en.bloomingbit.io/feed/news/113691
- **2026-05 (late)** — Monad Foundation joined 24+ firms launching the "Open Transaction Layer" for institutional on-chain operations; Pendle integration touted as bringing credit-market yield trading on-chain. https://coinmarketcap.com/cmc-ai/monad/latest-updates/
- **2026-05 (late)** — TVL crossed $400M (peak ~$402M around May 25 per DeFiLlama historical data) before sliding back to ~$351–361M by Jun 10–11. https://coingape.com/block-of-fame/pulse/monad-deploys-ai-powered-bug-hunting-system-as-tvl-crosses-400m/ and https://api.llama.fi/v2/historicalChainTvl/Monad
- **2026-06-11** — Price action: +4.6% on the day at $0.0215 (CoinGecko API); earlier in the period CMC AI noted a 10.75% surge on falling volume (spot/derivatives divergence). https://coinmarketcap.com/cmc-ai/monad/latest-updates/

## CT sentiment

- **Hype has cooled hard since launch.** MON popped >30% in its first 24h post-TGE (Nov 2025, https://www.ccn.com/education/crypto/monad-105m-airdrop-mon-token-network-growth/) but has since suffered drawdowns including a widely-discussed ~32% drop that spawned "baseless FUD or going to zero?" takes (https://99bitcoins.com/news/presales/monad-crypto-drops-32-baseless-fud-or-is-it-going-to-zero-mon-price-prediction/).
- **Low chatter volume**: CMC's social tracker showed essentially neutral sentiment with tiny tweet sample sizes — Monad is no longer a dominant CT topic vs its pre-launch era (https://coinmarketcap.com/cmc-ai/monad/latest-updates/).
- **The "speed war" narrative**: CT frames Monad vs MegaETH as the parallel-EVM/speed showdown (https://phemex.com/academy/megaeth-vs-monad-evm-speed-war).
- **Bull case on CT**: TVL growth despite market pullback (e.g., BSCN: "Monad TVL Explodes In Spite of Market Pullback", https://x.com/BSCNews/status/2037560732611486182), institutional angle (Open Transaction Layer, RWA deployments like Centrifuge/Tether Gold).
- **Bear case on CT**: ghost-chain accusations — 10k TPS capacity running at ~0.07% utilization, ~$4k/day gas fees, TVL viewed as incentive-driven mercenary capital, and a large team/investor unlock cliff starting Nov 2026 (~47% of supply vesting monthly into 2029, https://tokenomist.ai/monad and https://learn.backpack.exchange/articles/is-monad-crypto-a-good-investment-pros-cons-and-future-outlook).

## Caveats

- **Circulating supply not directly verified**: CoinGecko mcap $254.7M at $0.02155 implies ~11.8B MON circulating (~12% of 100B), but I did not find an official circulating figure; FDV is my calculation.
- **"10,000 TPS" is capacity, not demand**: the 10k TPS / 0.8s finality numbers come from Chainspect-cited max-throughput stats relayed by monadblock.com (a fan/news site, not official). Sustained real throughput averaged ~21 TPS over the first ~78 days (my calc from 140M tx by Feb 10, 2026). The "0.07% utilization" figure comes from CMC's AI summary and was not independently verified.
- **June 9 "25% speed increase"** and the **Open Transaction Layer (24+ firms)** items come from CMC's AI-generated news digest; I could not locate the primary announcements. Treat specifics as unconfirmed until cross-checked against blog.monad.xyz or @monad on X.
- **MIP-12 is a draft proposal**, not a shipped upgrade, as of 2026-06-11. A separate "MONAD_NINE" upgrade proposal was referenced on Binance Square (https://www.binance.com/en/square/post/35431946486497) but I could not verify its content or status.
- **"$20T credit market on-chain via Pendle"** is marketing framing from news aggregators — the integration may be real but the number is narrative, not a metric.
- **CT sentiment section relies on secondary aggregators** (CMC AI, Phemex, 99Bitcoins), not direct X firehose data — sample sizes were explicitly tiny.
- **TVL discrepancy**: DeFiLlama's live chains endpoint showed $361.3M while its latest historical daily point showed ~$351M (both 2026-06-10/11); normal API lag, quote "~$350–360M".
- Price/TVL figures are point-in-time snapshots from 2026-06-11 and move constantly.
