# layerzero — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| ZRO price (Crypto.com Exchange ZRO_USD, last) | $0.9017 (24h range $0.8056–$0.9222) | 2026-06-11 21:39 UTC | Crypto.com Exchange MCP ticker (live API) |
| ZRO price (secondary ref) | ~$0.84 | 2026-06-09 | https://www.dailypolitical.com/2026/06/09/layerzero-hits-self-reported-market-capitalization-of-288-34-million-zro.html |
| ZRO market cap (self-reported) | $288.34M | 2026-06-09 | https://www.dailypolitical.com/2026/06/09/layerzero-hits-self-reported-market-capitalization-of-288-34-million-zro.html |
| ZRO market cap (earlier in month) | $342.10M at ~$1.00 | 2026-06-05 | https://www.dailypolitical.com/2026/06/05/layerzero-zro-reaches-self-reported-market-cap-of-342-10-million.html |
| ZRO vs ATH | ATH $7.47; trading ~-88.9% below peak; 7d -24.5% | 2026-06-09 | https://www.dailypolitical.com/2026/06/09/layerzero-hits-self-reported-market-capitalization-of-288-34-million-zro.html |
| Total value transferred (lifetime) | >$260B; ~70% of cross-chain stablecoin volume | 2026-06-03 (cited in CMC AI story, via AMBCrypto) | https://coinmarketcap.com/top-stories/6a20a51b398a8965f3b1c071/ and https://ambcrypto.com/layerzero-pitches-wall-street-expansion-as-rivals-question-cross-chain-security/ |
| Cross-chain bridge volume share | ~75% of bridge volume; ~1.2M messages/day; ~$293M avg daily transfers | Sep 2025 (dated figure) | https://yellow.com/research/cross-chain-messaging-comparing-ibc-wormhole-layerzero-ccip-and-more |
| Network scale | 130+ chains, 150M+ messages, 250+ OFT assets, 500+ apps | mid-2025 (dated figure) | https://www.coti.news/news/what-is-layerzero-zro-and-everything (via search; see Caveats) |
| LayerZero + Stargate cumulative volume | >$70B to 80+ chains since launch | mid-2025/early-2026 (undated precisely) | https://www.cryptonewsnavigator.com/academy/article/layerzero-built-the-rails-and-stargate-runs-the-train |
| ZRO buybacks | >$112M deployed into ZRO buybacks since late 2025 | 2026-06-03 | https://ambcrypto.com/layerzero-pitches-wall-street-expansion-as-rivals-question-cross-chain-security/ |
| KelpDAO rsETH exploit size | $292M (largest 2026 DeFi exploit; some coverage cites $230M for the rsETH leg) | 2026-04-19 exploit; postmortem 2026-06-01 | https://www.coindesk.com/markets/2026/06/01/aave-overhauls-listing-standards-after-usd230-million-rseth-exploit-exposed-bridge-risks |

## Where real usage is

- **OFT standard is the core moat**: 120+ projects use OFTs, headline issuers being Ethena (ENA, USDe, sUSDe), EtherFi (weETH), PancakeSwap (CAKE), plus USDT0 and WBTC as OFT assets. (mid-2025 data: https://www.cryptonewsnavigator.com/academy/article/layerzero-built-the-rails-and-stargate-runs-the-train, https://docs.layerzero.network/v2/deployments/oft-ecosystem-stargate-assets)
- **Stargate is the flagship app**: LayerZero + Stargate have processed >$70B cumulative cross-chain volume across 80+ chains. By transferred value, STG leads ($4.26B) followed by USDC.e via Stargate Hydra ($3.78B). (https://www.cryptonewsnavigator.com/academy/article/layerzero-built-the-rails-and-stargate-runs-the-train)
- **Stablecoin rails**: AMBCrypto/CMC coverage (2026-06-03) claims LayerZero carries ~70% of cross-chain stablecoin volume and >$260B total value handled. (https://coinmarketcap.com/top-stories/6a20a51b398a8965f3b1c071/)
- **High-message-count apps**: Stargate, Merkly, Angle, CoreDAO, Aptos Bridge, DeFi Kingdoms; integrations include PayPal USD and Google Cloud. (mid-2025: https://messari.io/report/understanding-layerzero)
- **New direction — "Zero" L1**: LayerZero is repositioning as institutional infrastructure via a dedicated L1 called "Zero" targeting tokenized assets, stablecoin settlement, 24/7 capital markets, with ZRO as sole value-capture token (ecosystem revenue funds ZRO buybacks/burns). (2026-06-03: https://coinmarketcap.com/top-stories/6a20a51b398a8965f3b1c071/)

### Competitive position
- Pre-incident, LayerZero dominated (~75% of cross-chain bridge volume, Sep 2025: https://yellow.com/research/cross-chain-messaging-comparing-ibc-wormhole-layerzero-ccip-and-more). CCIP is smaller but concentrated in high-value institutional flows (11,000-bank narrative via SWIFT/banking integrations: https://blockeden.xyz/blog/2026/01/12/chainlink-ccip-cross-chain-interoperability-tradfi-bridge/).
- Post-incident, a real migration to Chainlink CCIP is underway: KelpDAO, Solv Protocol, ReProtocol migrated outright; one report cited ~$4B in value migrating to CCIP (see Caveats on that figure). Wormhole and Axelar were not prominent beneficiaries in the coverage found — the trust shift is mainly LayerZero → CCIP.
- Counterpoint: L2BEAT research argues CCIP carries its own significant operational risks and the security uplift vs LayerZero is not absolute. (2026-06-03 via https://ambcrypto.com/layerzero-pitches-wall-street-expansion-as-rivals-question-cross-chain-security/)

## Recent developments (last 30 days)

- **2026-05-09** — LayerZero publicly admits it "made a mistake" in the $292M KelpDAO rsETH exploit (April 19): a single LayerZero verifier (1-of-1 DVN config) approved a forged cross-chain message, minting 116,500 unbacked rsETH on Ethereum. https://www.coindesk.com/tech/2026/05/09/layerzero-says-it-made-a-mistake-in-usd292-million-kelp-exploit
- **2026-05-09 (~48h window)** — "Crisis of confidence": 14 protocols exit or suspend LayerZero bridging. Migrated to CCIP: KelpDAO, Solv, ReProtocol. Suspended bridging: Kamino, Ethena, Euler, Curve. **Froze markets: Aave, Compound, Pendle, SparkLend, Fluid** — this is the Pendle-market incident. https://cryptorank.io/news/feed/51d47-layerzero-bridge-protocols-exit-suspend
- **2026-05-24** — Weekly wrap coverage: "LayerZero Admits $292M Flaw"; claims circulating that ~47% of LayerZero OApps run risky single-DVN configs. https://www.cryptotimes.io/2026/05/24/weekly-wrap-layerzero-admits-292m-flaw-bitcoin-etf-sell-off-cross-chain-hacks-grow/ and https://www.mexc.com/news/1051837
- **~2026-05 (late)** — KelpDAO completes rsETH restoration after the $292M exploit. https://www.crowdfundinsider.com/2026/05/281797-defi-security-breach-kelp-dao-wraps-up-rseth-restoration-following-292m-exploit/
- **2026-06-01** — Aave postmortem: traces exploit to LayerZero bridge verification failure (not Aave code); overhauls listing standards to screen bridges/oracles/custodians/opsec; ~295 parameter changes already executed (168 supply-cap cuts, 66 borrow-cap cuts); building auto LTV-to-zero defenses; mobilized a $300M recovery fund/backstop. https://www.coindesk.com/markets/2026/06/01/aave-overhauls-listing-standards-after-usd230-million-rseth-exploit-exposed-bridge-risks
- **2026-06-03** — ZRO +11.3% in 24h to ~$1.24 on "Zero" L1 institutional-narrative reveal (ZRO sole value-capture token; >$112M buybacks since late 2025), even as Pleasing Market announced migrating ~$90M TVL to CCIP. Heavy CEX flow (Binance volume spikes +300–430%). https://coinmarketcap.com/top-stories/6a20a51b398a8965f3b1c071/
- **~2026-06 (early)** — StakeDAO exploit: compromised deployer key allegedly enabled a forged LayerZero mint on Arbitrum; ZRO dropped ~3.36% amid the news and market selloff. https://ambcrypto.com/compromised-stakedao-deployer-key-allegedly-enabled-forged-layerzero-mint-on-arbitrum/ and https://coinmarketcap.com/top-stories/6a1859c9319cff38dcb7d1c9/
- **2026-06-05 → 06-09** — ZRO slides from ~$1.00 ($342M mcap) to ~$0.84 ($288M mcap), -24.5% on the week, in a broad market selloff. https://www.dailypolitical.com/2026/06/09/layerzero-hits-self-reported-market-capitalization-of-288-34-million-zro.html
- **Security remediation** — LayerZero reportedly now refuses to process messages for apps using a single DVN, mandating multi-verifier configurations (surfaced via CMC AI updates feed; primary-source confirmation not located). https://coinmarketcap.com/cmc-ai/layerzero/latest-updates/

## CT sentiment

- **Deeply split.** Bears: on-chain analyst Emperor Osmo's "14 protocols exited in 48 hours" thread defined the May narrative; traders openly mocked that ZRO "pumped on a day where yet another protocol migrated from LayerZero to Chainlink" (https://x.com/obliiviiscariis/status/2062259271652294892, via https://coinmarketcap.com/top-stories/6a20a51b398a8965f3b1c071/).
- **Bulls:** threads (e.g., https://x.com/0xBumzy/status/2062206181838397846) hyping the "Zero" L1 and name-dropping DTCC, ICE, Citadel Securities, Tether, Google Cloud as partners/investors — these institutional claims are NOT independently verified.
- Aggregator sentiment data surfaced in search (likely CoinCodex/CMC-derived) claims ~73.7% of ZRO tweets bullish vs 7.8% bearish and a 4.6/5 social score — treat skeptically given the price action and incident backdrop; methodology and date unverified.
- Net read: CT treats LayerZero as a "broken-trust infra play with a buyback floor" — the security debate (LayerZero vs CCIP) is itself the main attention driver, cutting both ways.

## Caveats

- **Price/mcap precision**: CoinGecko API returned empty via fetch, so live price is from Crypto.com Exchange ($0.9017, 2026-06-11 21:39 UTC, thin volume on that venue: ~47k ZRO/24h). Market cap figures are "self-reported" per Daily Political (June 5/9); could not verify circulating supply or an authoritative mcap as of June 11.
- **$230M vs $292M**: CoinDesk's June 1 headline says "$230 Million rsETH exploit" while its own body text and most coverage say $292M total (KelpDAO hit, wrapped ether stranded across 20 chains). The $230M may be the Aave-specific rsETH leg; unresolved discrepancy.
- **"~$4B migrated to CCIP"**: appeared only in a search-result summary (attributed to post-exploit reports); no primary source located. Use with attribution hedging or omit.
- **"47% of OApps at risk" (single-DVN)**: from MEXC News aggregation; not confirmed against LayerZero or L2BEAT primary data.
- **Mandatory multi-DVN enforcement**: surfaced in CMC AI summaries; no official LayerZero announcement located in these searches.
- **Usage stats vintage**: the 75% bridge-volume share, 1.2M msgs/day, $293M/day figures are Sep 2025; the $100B/150M-messages/130-chain figures are mid-2025. No post-incident (May–June 2026) message-volume data found — actual current share is likely lower given the exodus, but this is inference, not data.
- **StakeDAO incident date**: article undated in results; inferred early June 2026 from context.
- **"Zero" L1 institutional partners** (DTCC, ICE, Citadel, Tether, Google Cloud): sourced from X threads only; unverified.
- DeFiLlama API endpoints returned empty via fetch; no DeFiLlama-verified Stargate TVL or current bridge volumes in this file.
