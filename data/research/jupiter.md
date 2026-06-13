# jupiter — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| JUP price | ~$0.154–0.161 (sources disagree slightly; CMC $0.1540, CoinGecko widget $0.1585–0.1609) | 2026-06-11 | https://coinmarketcap.com/currencies/jupiter-ag/ ; https://crypto.news/price/jupiter/ |
| JUP market cap | ~$511M–554M (CMC $511.2M; CoinGecko widget $554.4M) | 2026-06-11 | https://coinmarketcap.com/currencies/jupiter-ag/ ; https://crypto.news/price/jupiter/ |
| JUP 24h volume | ~$19–21M | 2026-06-11 | https://crypto.news/price/jupiter/ |
| Circulating supply | 3,320,935,307 JUP | 2026-06-11 | https://coinmarketcap.com/currencies/jupiter-ag/ |
| Drawdown from ATH ($2.00) | approx -92% | 2026-06-11 | https://www.coingecko.com/en/coins/jupiter |
| Aggregator volume 24h (Solana) | $934.6M | 2026-06-11 | https://api.llama.fi/summary/aggregators/jupiter-aggregator |
| Aggregator volume 7d | $7.88B | 2026-06-11 | https://api.llama.fi/summary/aggregators/jupiter-aggregator |
| Aggregator volume 30d | $17.06B | 2026-06-11 | https://api.llama.fi/summary/aggregators/jupiter-aggregator |
| Aggregator volume all-time | $1.23T | 2026-06-11 | https://api.llama.fi/summary/aggregators/jupiter-aggregator |
| Share of Solana aggregator-routed DEX volume | 93.6% (its highest in ~6 months) | late Dec 2025 | https://solanafloor.com/news/jupiter-reclaims-dominance-with-93-6-market-share-in-solana-s-aggregator-landscape |
| Aggregators' share of all Solana DEX volume | 74.3%+ (up from ~40% six months prior) | late Dec 2025 | https://solanafloor.com/news/jupiter-reclaims-dominance-with-93-6-market-share-in-solana-s-aggregator-landscape |
| Jupiter share of total Solana DEX volume | 50%+ | 2026 reviews | https://blockchainreporter.net/exchanges/jupiter/ |
| Jupiter TVL | above $2.5B; annualized fees ~$500M | 2026-01-02 (crypto.news citing DeFiLlama) | https://crypto.news/jupiter-launches-mobile-v3-native-pro-trading-2026/ |
| 2025 buyback spend | $70M+ (about half of protocol fee revenue) | 2026-01-05 | https://crypto.news/jupiter-jup-token-buyback-unlocks-solana-2026/ |
| Monthly unlocks through June 2026 | ~53M JUP/month | 2026-01-05 | https://crypto.news/jupiter-jup-token-buyback-unlocks-solana-2026/ |
| Jupuary 2026 airdrop | cut to 200M JUP from planned 700M | 2026 (announced late 2025/early 2026) | https://cryptorank.io/news/feed/78788-jupiter-revised-its-jupuary-airdrop-to-avoid-dilution |

## Product suite status

- **Swap aggregator (core)** — Live and dominant. Reclaimed 93.6% of Solana aggregator-routed volume (late Dec 2025, SolanaFloor). Ultra V3 high-speed routing engine shipped to cut slippage/MEV. Now the largest aggregator globally by volume despite being Solana-only. (https://solanafloor.com/news/jupiter-reclaims-dominance-with-93-6-market-share-in-solana-s-aggregator-landscape)
- **Perps + JLP** — Live. JLP remains the perps liquidity pool and is now a central collateral asset in Jupiter Lend; users can borrow jupUSD against JLP (looped APY quoted up to 43% by CMC AI). Plan in motion to convert ~$750M of JLP-pool stablecoins into JupUSD. (https://coinmarketcap.com/cmc-ai/jupiter-perps-lp/latest-updates/)
- **Jupiter Lend** — Live. Third-party integrations exist: Marinade Borrow surfaces Jupiter Lend positions (announced 2026-05-07 per CMC AI). (https://coinmarketcap.com/cmc-ai/jupiter-ag/latest-updates/)
- **JupUSD stablecoin** — Live. Built with Ethena Labs; reserves ~90% in BlackRock's BUIDL tokenized treasury fund, custody at Anchorage Digital. Being made default collateral across swaps, lending, perps. (https://finance.yahoo.com/news/jupiter-unveils-jupusd-stablecoin-major-185718200.html ; https://x.com/JupiterExchange/status/2008194285750124816)
- **Mobile** — Live. Mobile V3 launched 2026-01-01: fully native pro trading terminal, no in-app browser dApps, swaps claimed up to 10x cheaper than competing mobile apps. (https://crypto.news/jupiter-launches-mobile-v3-native-pro-trading-2026/)
- **Prediction markets** — Live/expanding. "Forecast" unveiled 2026-06-05 as Solana's first fully native prediction market within Jupiter Predict, settled in JupUSD, using Prop AMMs to trade against multiple market makers. (https://www.cryptotimes.io/2026/06/05/jupiter-unveils-forecast-to-power-solana-prediction-markets/)
- **Jupnet (omnichain)** — Still vision/buildout, not a fully shipped product as far as I could verify. Framing: extend Jupiter routing across Ethereum, Base, Arbitrum, etc.; 300M JUP reserved for it. (https://coinmarketcap.com/cmc-ai/jupiter-ag/latest-updates/)
- **Buybacks** — In flux. ~$70M spent in 2025 from ~50% of fee revenue; founder Siong proposed halting them 2026-01-03 after price failed to respond; Bitget reported Jupiter halted buybacks and pivoted funds to growth incentives; a governance proposal passed to reduce net future emissions toward zero. Exact current buyback status as of June 2026 unverified (see Caveats). (https://crypto.news/jupiter-jup-token-buyback-unlocks-solana-2026/ ; https://www.bitget.com/amp/news/detail/12560605130545)
- **ASR (Active Staking Rewards)** — Active. Q1 2026 ASR (Jan–Mar) is claimable now; claim window ends 2026-07-08. Eligibility: time-weighted average stake of 50+ JUP during the quarter, plus governance voting. (https://jup.ag/rewards/asr-2026-q1)

## Recent developments (last 30 days)

- **2026-06-05** — Jupiter unveiled "Forecast," a natively built Solana prediction market inside Jupiter Predict, settled in JupUSD with Prop AMM liquidity (multiple market makers quoting simultaneously). https://www.cryptotimes.io/2026/06/05/jupiter-unveils-forecast-to-power-solana-prediction-markets/
- **2026-05-05** — Partnership with Securitize and Jump Trading to launch regulated tokenized-equities trading on Solana, combining Securitize's regulatory framework, Jump's liquidity engine and Jupiter's aggregation layer (per CoinMarketCap AI updates feed). https://coinmarketcap.com/cmc-ai/jupiter-ag/latest-updates/
- **2026-05-07** — Marinade Finance launched Marinade Borrow, integrating Jupiter Lend borrowing positions into the Marinade portfolio UI (per CoinMarketCap AI updates feed). https://coinmarketcap.com/cmc-ai/jupiter-ag/latest-updates/
- **May 2026 (ongoing)** — JupUSD rollout deepening: plan to progressively convert ~$750M of JLP-pool stablecoins to JupUSD and make it default collateral across the ecosystem including Perps. https://coinmarketcap.com/cmc-ai/jupiter-perps-lp/latest-updates/
- **Ongoing through 2026-07-08** — Q1 2026 ASR claim window open at jup.ag. https://jup.ag/rewards/asr-2026-q1
- **Undated (recent)** — A Chainlink integration was floated as a possible JUP catalyst by FinanceFeeds; date and scope not verified. https://financefeeds.com/will-jupiter-surge-after-chainlink-integration/

## CT sentiment

- **Mixed-to-frustrated on the token, respectful of the product.** The defining CT narrative of 2026: Jupiter executes well (93%+ aggregation share, superapp expansion) but JUP is down ~89–92% from its $2.00 ATH. The phrase "good product, bad token" captures the split. (https://crypto.news/jupiter-jup-token-buyback-unlocks-solana-2026/)
- **Buyback debate went viral.** Founder Siong's 2026-01-03 post ("we spent more than 70m on buyback last year and the price obviously didn't move much... should we stop?") triggered a major CT debate; Solana co-founder toly weighed in arguing buybacks can't beat heavy emissions and protocols should accumulate and deploy later or use long lockups. (https://twitter.com/sssionggg/status/2007275334551646302 ; https://x.com/toly/status/2007869110399668573)
- **CoinCodex tweet-sentiment snapshot:** 64.44% bullish vs 8.04% bearish tweets on Jupiter (undated rolling metric — treat as soft). (https://coincodex.com/crypto/jupiter-coin/price-prediction/)
- **CMC AI consensus:** "mixed, split between long-term believers in its Solana ecosystem utility and traders weary of its stagnant chart"; everyone is hunting for a catalyst. (https://coinmarketcap.com/cmc-ai/jupiter-ag/latest-updates/)
- Supply overhang (~53M JUP unlocking monthly through June 2026) is the most-cited bear point; the unlock schedule ending mid-2026 is itself cited as a potential bullish inflection by some. (https://crypto.news/jupiter-jup-token-buyback-unlocks-solana-2026/)

## Caveats

- **Price/mcap discrepancy:** On 2026-06-11, CMC-derived figures showed $0.1540 / $511.2M mcap while crypto.news's CoinGecko-powered widget showed $0.1585–$0.1609 / $534–554M across two fetches minutes apart. Both captured same-day; use "~$0.15–0.16, mcap ~$510–555M" in posts.
- **Buyback status unverified for June 2026.** The halt proposal (Jan 2026) and a Bitget headline saying buybacks were halted/pivoted to growth are confirmed, but I could not verify via a primary source whether buybacks are formally stopped, reduced, or restructured as of today. Do not tweet "buybacks are dead" as fact.
- **93.6% aggregator share is from late December 2025** (SolanaFloor), not a June 2026 reading. Current share unverified; the "50%+ of total Solana DEX volume" figure comes from 2026 exchange-review pages without exact dates.
- **TVL ($2.5B+) and annualized fees (~$500M) are as of 2026-01-02** (crypto.news citing DeFiLlama); I did not get a fresh June TVL reading.
- **Jupnet:** could not verify any mainnet launch; treat as roadmap/in-development, not shipped.
- **CT sentiment percentages** (CoinCodex 64.44% bullish) are an undated rolling aggregate from one vendor; directional only.
- **May 2026 items (Securitize/Jump, Marinade) are sourced from CoinMarketCap's AI-generated updates feed**, not primary announcements — verify against @JupiterExchange before quoting specifics.
- **Macro context:** broad market is weak (BTC ~$69.6K, SOL ~$87.7 on 2026-06-11 per crypto.news tickers), so JUP price action is partly beta, not purely idiosyncratic.
- DeFiLlama volume figures are for the **Jupiter Aggregator module only** (swap routing on Solana); they exclude perps, lend, and other Jupiter products.
