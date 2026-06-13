# ethena — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| USDe circulating supply | $4.476B | 2026-06-11 | https://stablecoins.llama.fi/stablecoins (DeFiLlama API) |
| USDe price | $0.9994 | 2026-06-11 | https://www.coingecko.com/en/coins/ethena-usde (CoinGecko API) |
| sUSDe current staking yield (APY) | 3.50% | 2026-06-10 (API lastUpdated) | https://ethena.fi/api/yields/protocol-and-staking-yield |
| Protocol yield (gross, pre-split) | 3.87% | 2026-06-10 | https://ethena.fi/api/yields/protocol-and-staking-yield |
| sUSDe 30d avg yield | 3.88% | 2026-06-10 | https://ethena.fi/api/yields/protocol-and-staking-yield |
| sUSDe 90d avg yield | 3.66% | 2026-06-10 | https://ethena.fi/api/yields/protocol-and-staking-yield |
| sUSDe avg yield since inception | 11.20% | 2026-06-10 | https://ethena.fi/api/yields/protocol-and-staking-yield |
| sUSDe market cap | $1.747B (price $1.23) | 2026-06-11 | https://www.coingecko.com/en/coins/ethena-staked-usde (CoinGecko API) |
| ENA price | $0.0800 (+13.1% 24h) | 2026-06-11 | https://www.coingecko.com/en/coins/ethena (CoinGecko API) |
| ENA market cap | $743.7M (~9.03B circulating of 15B total) | 2026-06-11 | https://www.coingecko.com/en/coins/ethena |
| Reserve fund | $62.04M (~1.4% of USDe supply) | 2026-06-11 21:00 UTC | https://ethena.fi/api/solvency/reserve-fund |
| Total backing assets | $4.548B | 2026-06-11 14:58 UTC | https://ethena.fi/api/positions/current/collateral |
| ENA drawdown from ATH ($1.52) | approx -94% | 2026-06-11 | https://www.coingecko.com/en/coins/ethena ; https://thedefiant.io/news/defi/ethena-strikes-lending-deals-with-anchorage-and-maple-amid-usde-reserve-overhaul |
| USDe peak supply (pre Oct-10-2025 crash) | >$14.6B | 2025-10 (reported 2026-04-06) | https://thedefiant.io/news/defi/ethena-strikes-lending-deals-with-anchorage-and-maple-amid-usde-reserve-overhaul |

## Yield source breakdown

The story in mid-2026: **USDe is barely a "basis trade" product anymore.** Live backing composition from Ethena's own transparency API (2026-06-11 14:58 UTC, https://ethena.fi/api/positions/current/collateral):

| Backing asset | USD value | % of backing |
|---|---|---|
| Liquid Cash (stables / T-bill-like / lending positions) | $4,432.1M | 97.4% |
| BTC (delta-hedged) | $82.5M | 1.8% |
| ETH / LSTs (delta-hedged) | $32.7M | 0.7% |
| BNB | $1.0M | ~0.0% |

- The Defiant reported (2026-04-06) that perp futures positions had already fallen to just **11% of reserves**, with the rest in stablecoin reserves and DeFi lending — the live API now shows hedged crypto at only ~2.5%. Source: https://thedefiant.io/news/defi/ethena-strikes-lending-deals-with-anchorage-and-maple-amid-usde-reserve-overhaul
- Implication: the ~3.5–3.9% current yield is now driven overwhelmingly by **stablecoin/T-bill-style and lending returns**, not perp funding. Funding-rate income is a marginal contributor at current positioning.
- Diversification roadmap (announced ~2026-04-06): institutional lending (Anchorage Digital, Maple Institutional, Coinbase Asset Management), RWA beyond T-bills (AAA CLOs first), and extending the delta-neutral framework to **equity and commodity perps** (Ethena cited gold perp funding on Binance averaging 24.6% in March 2026). Source: https://thedefiant.io/news/defi/ethena-strikes-lending-deals-with-anchorage-and-maple-amid-usde-reserve-overhaul and https://ethena.fi/blog/usde-backing-diversification-building-resilience-across-market-cycles
- Note: Ethena does not publish (in the endpoints checked) an exact % attribution of yield by source (funding vs staking vs stables); the split above is inferred from backing composition. See Caveats.

## Recent developments (last 30 days)

- **2026-06-09 — Janus Henderson partnership.** The $480B AUM asset manager made a strategic ENA investment via its ANTIK venture arm; Ethena will integrate Janus Henderson's tokenized AAA-rated CLO fund (JAAA, via Centrifuge/Anemoy) into USDe backing, **capped at ~$310M** — first corporate-credit exposure in USDe reserves. Both firms target regulated USDe/ENA ETPs (incl. ETFs) for H2 2026. Sources: https://www.coindesk.com/business/2026/06/09/ethena-lands-janus-henderson-backing-as-asset-manager-invests-in-ena-eyes-usde-distribution ; https://beincrypto.com/ethena-janus-henderson-usde-clo-backing-2/ ; https://cryptobriefing.com/janus-henderson-ethena-partnership-crypto-etps/
- **2026-06-02 — Coinbase Ventures backs ENA.** Coinbase bought ENA on the open market ahead of launching an onchain savings product (Ethena-powered) for its 100M+ users; ENA rallied ~10% on the news. Sources: https://www.theblock.co/post/403403/coinbase-invests-ethena-open-market-purchase-ena-flags-new-partnership ; https://www.coindesk.com/business/2026/06/02/coinbase-backs-ethena-ahead-of-savings-product-launch-for-exchange-s-100-million-users
- **2026-06-02 — Sui USDe SDK launch**, enabling developers to build with USDe on Sui. Source: https://coinmarketcap.com/cmc-ai/ethena/latest-updates/
- **2026-06-06 — CLO backing diversification detailed** (AAA CLO evaluation to create a yield floor independent of crypto funding). Source: https://cryptobriefing.com/ethena-usde-aaa-clo-diversification/
- Slightly older context (outside 30d window but load-bearing): **2026-04-06** — lending deals with Anchorage Digital, Maple Institutional, Coinbase Asset Management; proposal to replace the static 7-day sUSDe unstaking cooldown with a dynamic model. Source: https://thedefiant.io/news/defi/ethena-strikes-lending-deals-with-anchorage-and-maple-amid-usde-reserve-overhaul

## CT sentiment

**Bull side (current narrative):**
- TradFi validation wave: Janus Henderson + Coinbase Ventures both taking ENA stakes within a week (June 2 and June 9, 2026) drove ENA +13% on 2026-06-11; the "distribution to 100M Coinbase users" thesis is the dominant bull case. Sources above.
- Backing overhaul is framed by supporters as "Ethena maturing into a regulated synthetic dollar / RWA yield platform" rather than a funding-rate hedge fund.

**Bear / systemic-risk arguments:**
- **"Tokenized hedge fund, not a stablecoin."** OKX founder Star Xu argued treating USDe as a stablecoin is a systemic risk to crypto and that its depeg risk can cause market-wide contagion. Source: https://ambcrypto.com/treating-ethena-usde-as-a-stablecoin-is-systematic-risk-to-crypto-okx-founder/
- **CryptoQuant CEO Ki Young Ju** called USDe "a CeFi stablecoin run by a hedge fund, effective only in bull markets," questioning delta-neutral viability in bear markets. Source: https://yellow.com/learn/usde-ethena-synthetic-dollar-hedging (citing Ju)
- **Thin reserve fund vs supply.** Reserve fund was reported at ~$61M against $5.6B supply (~1.1%) in March 2026; live API shows $62.0M vs $4.48B (~1.4%) on 2026-06-11. Critics argue it could be depleted in a prolonged negative-funding regime. Sources: https://yellow.com/learn/usde-ethena-synthetic-dollar-hedging ; https://ethena.fi/api/solvency/reserve-fund
- **Oct 10, 2025 crash scar tissue.** USDe supply collapsed from >$14.6B peak to ~$4.5B now (-69%); ENA is down ~94% from ATH. CEX outage/liquidity issues during the crash (e.g., Binance) amplified depeg fear, underscoring counterparty risk on centralized venues. Sources: https://thedefiant.io/news/defi/ethena-strikes-lending-deals-with-anchorage-and-maple-amid-usde-reserve-overhaul ; https://www.ainvest.com/news/resilience-ethena-usde-19b-crypto-flash-crash-lesson-stablecoin-design-risk-management-2512/
- **Yield compression kills the pitch.** sUSDe at ~3.5% (vs ~11.2% lifetime average) offers little premium over T-bills while carrying smart-contract, custodial, and exchange risk — a common CT take per the compressed-funding environment in 2026. Sources: https://eco.com/support/en/articles/15254002-ethena-usde-and-susde-2026-delta-neutral-yield ; https://ethena.fi/api/yields/protocol-and-staking-yield
- **Regulatory tail risk.** SEC posture toward yield-bearing tokens flagged as the largest single risk for US holders. Source: https://yellow.com/learn/usde-ethena-synthetic-dollar-hedging
- New bear angle on the pivot itself: adding CLOs/corporate credit and institutional loans introduces credit and duration risk that didn't exist in the pure basis-trade design (raised around the June 6–9 CLO news). Source: https://cryptobriefing.com/ethena-usde-aaa-clo-diversification/

## Caveats

- **Yield attribution split is inferred, not officially published.** Ethena's API gives backing composition (97.4% "Liquid Cash") but no per-source yield attribution (funding vs staking vs stables/T-bills). The claim that yield is now mostly stables/lending-driven follows from composition; exact percentages unverified.
- **"Liquid Cash" is Ethena's own aggregate label** — it likely spans stablecoins, tokenized T-bill products (e.g., USDtb/BUIDL-type), and DeFi/institutional lending positions; the internal split was not retrievable from the endpoints checked.
- **ENA price varies by source** on 2026-06-11: CoinGecko API $0.0800/$743.7M mcap; CoinMarketCap showed $0.0748; CoinStats $0.088/$796M. Table uses the CoinGecko API figure pulled live.
- **sUSDe APY figures differ slightly by source**: ethena.fi API staking yield 3.50% (2026-06-10), Aavescan showed 3.86% for sUSDe suppliers, Messari (early 2026) 3.72%. The ethena.fi API figure is treated as canonical.
- The USDe supply figure ($4.476B, DeFiLlama API) differs from total backing ($4.548B, Ethena API) — consistent with overcollateralization plus timing differences; not independently reconciled.
- Could **not** verify: status/outcome of the dynamic-cooldown governance proposal (proposed ~April 2026); the exact launch date of the Coinbase savings product ("next week" as of June 2 reporting); current chain-by-chain USDe distribution.
- Janus Henderson CLO allocation ($310M cap) is announced, not necessarily yet deployed as of 2026-06-11.
- X/Twitter posts were not directly accessible; CT sentiment is reconstructed from news coverage quoting prominent figures (Star Xu, Ki Young Ju) and 2026 analyst write-ups.
