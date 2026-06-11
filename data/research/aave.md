# aave — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| Aave total TVL (all versions, all chains) | $12.22B | 2026-06-11 | https://api.llama.fi/tvl/aave (DeFiLlama API) |
| Aave V3 TVL | $11.77B | 2026-06-11 | https://api.llama.fi/tvl/aave-v3 |
| Aave V4 TVL (Ethereum mainnet only) | $113.9M | 2026-06-11 | https://api.llama.fi/tvl/aave-v4 |
| Aave V2 TVL (runoff) | $107.7M | 2026-06-11 | https://api.llama.fi/tvl/aave-v2 |
| DeFiLlama "Lending" category total TVL | $35.84B | 2026-06-11 | https://api.llama.fi/protocols (category=Lending sum) |
| Aave share of lending TVL | ~34% (12.22/35.84); V3 alone is #1, ~1.8x Morpho Blue ($6.57B) | 2026-06-11 | https://api.llama.fi/protocols |
| TVL trend | $14.49B on 2026-05-18, down ~52% from reported ~$30.25B peak in Nov 2025; now $12.22B | 2026-05-18 / 2026-06-11 | https://coinlaw.io/aave-statistics/ ; https://api.llama.fi/tvl/aave |
| AAVE price | $64.57 (+5.98% 24h) | 2026-06-11 21:32 UTC | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=aave |
| AAVE market cap | $979.5M (rank #70); FDV $1.03B | 2026-06-11 | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=aave |
| AAVE circulating supply | 15.18M / 16M max | 2026-06-11 | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=aave |
| AAVE vs ATH | -90.2% from $661.69 ATH (2021-05-18) | 2026-06-11 | https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=aave |
| GHO circulating supply | $598.2M | 2026-06-11 | https://stablecoins.llama.fi/stablecoins (DeFiLlama stablecoins API) |
| GHO price / peg | $0.9987 | 2026-06-11 | https://stablecoins.llama.fi/stablecoins |
| Buybacks executed | 205,000+ AAVE (~1.28% of supply) repurchased in under a year | as of 2026-02-28 | https://governance.aave.com/t/arfc-aave-buybacks-program-an-update/23290 |
| Buyback budget | Cut from ~$50M/yr to ~$30M/yr (~99.4% vote support) | 2026 (vote date unverified, see Caveats) | https://governance.aave.com/t/arfc-buyback-program-budget-adjustment/24229 ; https://www.kucoin.com/news/flash/aave-proposes-cutting-annual-buyback-budget-from-50m-to-30m |
| Fee revenue trend | Borrow fee revenue down ~25% from peak; Jan 2026 revenue $7.95M vs $13.5M Jan 2025 | Jan 2026 | https://governance.aave.com/t/arfc-buyback-program-budget-adjustment/24229 |

## GHO status

- Supply: $598.2M circulating as of 2026-06-11 (DeFiLlama stablecoins API: https://stablecoins.llama.fi/stablecoins). Reported as ~580M in March 2026 and ~$584M in May 2026 — growth has plateaued around the $600M level.
- Peg: $0.9987 on 2026-06-11 (DeFiLlama) — holding within ~13bps of $1.00; no notable depeg events surfaced in searches.
- Search-result claims (secondary, via https://coinmarketcap.com/cmc-ai/gho/latest-updates/): the team that scaled GHO supply is scheduled to exit in July 2026, shifting management; RWA collateral integrations explored for 2026. Treat as unverified — see Caveats.

## Aave V4 status

- SHIPPED. V4 went live on Ethereum mainnet on 2026-03-30 after ~2 years of development (https://thedefiant.io/news/defi/aave-v4-launches-on-ethereum-mainnet ; https://coinpedia.org/news/aave-v4-goes-live-on-ethereum-mainnet-with-new-lending-architecture/).
- Architecture: hub-and-spoke — central liquidity hub holds assets/accounting; spokes are user-facing markets with customizable collateral, risk params, and liquidation rules (https://news.bitcoin.com/aave-v4-launch-explained-hub-and-spoke-model-new-partners-and-what-changes-for-borrowers/).
- Launch assets: USDT, USDC, EURC, XAUt, cbBTC, frxUSD, USDG + Lido/EtherFi/Kelp/Ethena/Lombard assets. Supply caps filled quickly post-launch and were raised (https://www.cryptotimes.io/2026/04/18/aave-v4-witnesses-accelerating-traction-just-after-mainnet-launch/, 2026-04-18).
- Ethereum-only so far; multi-chain expansion (incl. Avalanche) pending DAO governance. V4 TVL is still small: $113.9M vs V3's $11.77B as of 2026-06-11 (DeFiLlama API) — migration is early.

## Recent developments (last 30 days)

- 2026-05-07: Aave overhauls collateral/asset-listing standards after the KelpDAO bridge exploit, in which an attacker minted $293M in unbacked rsETH (April 2026) and used it as Aave collateral, leaving hundreds of millions in bad debt. New listings face broader interoperability/cybersecurity/architecture review. (https://www.coindesk.com/business/2026/05/07/aave-to-overhaul-collateral-and-listing-standards-after-kelpdao-exploit) [Note: 35 days ago, kept as essential context.]
- 2026-05-09: Judge Margaret Garnett permitted Aave to transfer $71M in frozen exploit-linked funds on Arbitrum (tied to North Korea hack); legal freeze remains amid terrorism-case plaintiff claims. (https://coinmarketcap.com/cmc-ai/aave/latest-updates/)
- May–June 2026: Aave DAO "May/June 2026 Funding Update" posted direct-to-AIP, plus AL Development Update May 2026 — ongoing post-V4 development cadence. (https://governance.aave.com/t/direct-to-aip-may-june-2026-funding-update/25000 ; https://governance.aave.com/t/al-development-update-may-2026/25013)
- 2026 (recent; exact vote date unverified): Buyback budget adjustment ARFC — annual buyback cut from ~$50M to ~$30M on declining revenue, passing with ~99.4% support. (https://governance.aave.com/t/arfc-buyback-program-budget-adjustment/24229 ; https://en.bloomingbit.io/feed/news/107931)
- 2026-06-06: Whale borrowed $142M on Aave to buy ETH — cited as evidence of Aave's role as DeFi's core leverage venue. (https://coinmarketcap.com/cmc-ai/aave/latest-updates/)
- Background (April 2026): Aave DAO passed the binding "Aave Will Win" vote — 100% of revenue from Aave-branded products flows to DAO treasury; Aave Labs granted $25M stablecoins + 75,000 AAVE. Vote: 522,780 for / 175,310 against (~75%), up from 52.58% at temp check. ACI cast the largest dissenting vote (166,200 AAVE). (https://www.theblock.co/post/397138/aave-dao-approves-25-million-aave-labs-funding-grant-in-binding-aave-will-win-vote ; https://www.fxstreet.com/cryptocurrencies/news/aave-price-forecast-aave-will-win-framework-passes-fueling-bullish-sentiment-202604130600)

## CT sentiment

- Split between fundamentals-bulls and governance-drama watchers. Bull case: V4 shipped, permanent buybacks, "real revenue" narrative — framed as DeFi's blue-chip lender becoming investable (https://beincrypto.com/aave-v4-release-fuels-market-momentum/ ; https://cryptodaily.co.uk/2026/05/aave-buybacks-protocol-revenue-defi-tokens).
- Governance drama is a major CT storyline: Marc Zeller (ACI) publicly fought the Aave Labs "Aave Will Win" proposal, calling it a value-extraction attempt, questioning ROI on $86M prior funding and claiming Horizon earned ~$216K against ~$5.25M costs ("$24 spent per $1 earned"). ACI then challenged the vote result, extending the drama (https://www.cryptopolitan.com/aave-aci-challenges-voting-result/ ; https://www.thecoinrepublic.com/2026/02/26/governance-critique-triggers-short-term-aave-price-pressure-despite-long-term-protocol-fundamentals/).
- Bear undertone: TVL roughly halved from the Nov 2025 peak, borrow-fee revenue compressing (~-25% from peak), buyback budget cut — read by skeptics as fading demand; AAVE at ~$64 is ~90% off its 2021 ATH.
- KelpDAO/rsETH bad-debt episode and the frozen-funds court saga keep risk-management discourse active around Aave.
- Whale-watching content (e.g., the 2026-06-06 $142M ETH leverage borrow) remains reliable engagement fodder.

## Caveats

- All numbers above were pulled 2026-06-11 from live APIs (DeFiLlama, CoinGecko) or dated articles; none from training data.
- DeFiLlama parent "aave" TVL ($12.22B) slightly exceeds the v2+v3+v4 sum ($11.99B) — parent likely includes other modules (e.g., GHO/other deployments). Use $12.22B as the headline combined figure.
- The ~$30.25B Nov 2025 TVL peak and the $14.49B 2026-05-18 figure come from a secondary aggregator (coinlaw.io); I could not independently verify the peak value against DeFiLlama historical data in this session.
- Exact date of the buyback budget-cut vote ($50M→$30M, ~99.4% support) was not verifiable from search snippets; the governance thread exists (link above) but I did not confirm whether the AIP has fully executed.
- GHO claims about the scaling team exiting in July 2026 and RWA collateral plans come from CoinMarketCap's AI-generated update page — verify before tweeting.
- CT sentiment is inferred from news coverage of X posts and governance forums, not from direct X/Twitter data pulls.
- AAVE price/mcap figures vary slightly across sources intraday ($63–65 range during 2026-06-08 to 06-11); table uses CoinGecko API at 2026-06-11 21:32 UTC.
- The exact V4 mainnet launch date (2026-03-30) is reported by Coinpedia/TradingView; The Defiant confirms the launch but I did not confirm the precise date on Aave's official channels.
