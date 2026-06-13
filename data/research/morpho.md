# morpho — research (2026-06-11)

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| TVL (deposits net of borrows) | $6.62B | 2026-06-11 | https://defillama.com/protocol/morpho (api.llama.fi/protocol/morpho) |
| Active loans (borrowed) | $3.43B | 2026-06-11 | https://defillama.com/protocol/morpho (api.llama.fi/protocol/morpho) |
| Total deposits (TVL + borrowed) | ~$10.05B | 2026-06-11 | Computed from api.llama.fi/protocol/morpho currentChainTvls |
| TVL by chain (top 3) | Ethereum $3.38B / Base $2.58B / Hyperliquid $287M | 2026-06-11 | https://defillama.com/protocol/morpho |
| Chains deployed | ~38 chains with non-zero listing (long tail tiny; Monad $96M, Katana $82M, Flare $45M next) | 2026-06-11 | https://defillama.com/protocol/morpho |
| MORPHO price | $1.70 (24h +1.0%, 7d -9.2%) | 2026-06-11 | https://www.coingecko.com/en/coins/morpho |
| Market cap | $935.5M (rank #72) | 2026-06-11 | https://www.coingecko.com/en/coins/morpho |
| FDV | $1.70B (Mcap/FDV 0.55) | 2026-06-11 | https://www.coingecko.com/en/coins/morpho |
| Circulating supply | 550.1M / 1B max | 2026-06-11 | https://www.coingecko.com/en/coins/morpho |
| 24h volume | $17.3M | 2026-06-11 | https://www.coingecko.com/en/coins/morpho |
| Fees | ~$192.4M annualized; ~$15.77M 30d (no revenue attributed to protocol/tokenholders) | ~2026-06-03 (via search summary of DeFiLlama) | https://defillama.com/protocol/morpho |
| Coinbase US loan originations via Morpho | >$2.17B USDC cumulative | 2026-04-14 | https://crypto.news/coinbase-brings-5m-crypto-backed-loans-to-uk-via-morpho-on-base/ |
| Funding round | $175M at ~$2B valuation (Paradigm, a16z crypto, Ribbit co-led) | 2026-06-09 | https://www.theblock.co/post/404111/morpho-raises-175m-paradigm-a16z-crypto-ribbit-capital |

## How it differs from Aave

- **Isolated markets vs pooled risk.** Aave runs one big shared liquidity pool per deployment where all listed assets share risk parameters set by governance. Morpho Blue is a minimal, immutable primitive: each market is an isolated pair (one collateral asset, one loan asset, one oracle, one LLTV) that anyone can create permissionlessly. Bad debt in one market doesn't contaminate others.
- **Curator model.** Risk management is unbundled from the protocol. Third-party "curators" (notably Gauntlet, Steakhouse Financial, plus Morpho's own first-party vaults) build and manage vaults that allocate deposits across markets — they set caps, choose markets, and earn fees. On Aave, equivalent decisions go through token-holder governance and risk service providers. (Sources: https://www.gauntlet.xyz/resources/sustainable-apys-at-scale-how-gauntlets-active-curation-on-morpho-handled-a-775-million-supply-event , https://defiprime.com/defi-vaults-guide)
- **MetaMorpho / Vaults.** Passive lenders deposit into curated vaults (MetaMorpho, now Vaults V2) that spread liquidity across isolated markets — the vault layer recreates the "deposit and forget" UX of Aave on top of isolated markets. Vault V2 code was actively iterated as of June 2026 (commits 2026-06-09 per CoinMarketCap updates page: https://coinmarketcap.com/cmc-ai/morpho/latest-updates/).
- **B2B / embedded distribution.** Morpho positions itself as white-label lending infrastructure ("open credit network") that exchanges and fintechs embed — Coinbase's BTC/ETH/SOL-backed loans are the flagship example (https://morpho.org/stories/coinbase/). Aave is primarily a destination app/brand.
- **Morpho V2 / fixed rate.** Morpho V2 adds intent-based fixed-rate, fixed-term loans with custom terms; a fixed-rate "Morpho Midnight" codebase was made public 2026-05-14 (per https://coinmarketcap.com/cmc-ai/morpho/latest-updates/). Aave's core model remains variable-rate pool lending.
- **Scale context.** Morpho is the clear #2 DeFi lender behind Aave by TVL (per https://cryptodaily.co.uk/2026/06/morpho-lending-thesis-smaller-defi-tokens-revenue-proof, June 2026).

## Recent developments (last 30 days)

- **2026-06-09 — $175M funding round.** Morpho Association closed a $175M round co-led by Paradigm, a16z crypto, and Ribbit Capital at a reported ~$2B valuation; Apollo and Coinbase Ventures also participated via token purchases. Capital earmarked for institutional integrations with banks, fintechs, and crypto platforms — pitched as building an "open credit network" for Wall Street's DeFi push. Sources: https://www.theblock.co/post/404111/morpho-raises-175m-paradigm-a16z-crypto-ribbit-capital , https://fortune.com/2026/06/09/morpho-fundraise-a16z-crypto-paradigm-ribbit-capital-175-million/
- **2026-06-09/10 — Token outperformance on the news.** MORPHO gained ~7.5% in 24h post-announcement, defying a broader market slide; analysts flagged a potential $2.10 breakout level. Sources: https://finance.yahoo.com/markets/crypto/articles/morpho-token-defies-market-slide-061513187.html , https://www.banklesstimes.com/articles/2026/06/10/morpho-price-targets-2-10-breakout-after-record-defi-funding-round/ (Note: by 2026-06-11 CoinGecko shows price back at $1.70, -9.2% on 7d.)
- **2026-05-14 — Morpho Midnight codebase public.** Core code for a new fixed-rate lending protocol released for public review, targeting institutional fixed-rate demand. Source: https://coinmarketcap.com/cmc-ai/morpho/latest-updates/ (secondary source — see Caveats)
- **Recent (2026, exact date unverified) — Coinbase UK expansion.** Coinbase brought USDC borrowing (up to $5M, BTC/ETH collateral) to UK users via Morpho on Base; more countries planned. US originations passed $2.17B USDC as of 2026-04-14. Source: https://crypto.news/coinbase-brings-5m-crypto-backed-loans-to-uk-via-morpho-on-base/
- **Recent (2026, exact date unverified) — SOL-backed loans.** Coinbase and Morpho launched Solana-backed loans. Source: https://www.pymnts.com/cryptocurrency/2026/coinbase-and-morpho-unveil-solana-backed-loans/
- **Unlock overhang flagged.** CoinMarketCap story: "Morpho Drops 4% on 22.6% Unlock Overhang" — a ~22.6% token unlock cited as near-term volatility source (exact unlock date not verified in this research). Source: https://coinmarketcap.com/top-stories/69b9c261a29d0029078e1b79/ ; schedule reference: https://defillama.com/unlocks/morpho

## CT sentiment

- **Net bullish on fundamentals.** Aggregated social data (via CoinMarketCap/Bitcoin Foundation roundups, June 2026) shows ~59% bullish vs ~4% bearish tweets and a 4.7/5 average sentiment score. The $175M Paradigm/a16z raise dominated the conversation in the last week and was framed as institutional validation ("Wall Street backs Morpho"). Sources: https://bitcoinfoundation.org/news/altcoins/morpho-price-prediction-2026-can-morpho-crypto-deliver-another-explosive-rally/ , https://genfinity.io/2026/06/09/morpho-raises-175m-paradigm-a16z-ribbit-open-credit-network/
- **Traders more skeptical than fundamentalists.** Technical CT had been fading MORPHO before the raise — describing it as "losing trend across the board after exhaustion at range high" — and the ~22.6% unlock is the recurring bear talking point. Source: https://coinmarketcap.com/top-stories/69b9c261a29d0029078e1b79/
- **Recurring value-accrual debate.** Commentary (e.g., CryptoDaily, June 2026) notes Morpho generates ~$192M annualized fees but attributes no revenue to the protocol or tokenholders — the "strong product, weak token" critique is a standing CT theme. Source: https://cryptodaily.co.uk/2026/06/morpho-lending-thesis-smaller-defi-tokens-revenue-proof
- **Curator narrative.** "Curators hitting peak activity" / curated-vault yield meta is a positive narrative thread for Morpho on CT. Source: https://www.mexc.co/news/491648

## Caveats

- **TVL definitions vary.** DeFiLlama's simple /tvl endpoint returned $7.21B for "morpho" on 2026-06-11, while summing currentChainTvls (excluding borrows) gives $6.62B; the discrepancy likely reflects parent/child protocol aggregation or staking inclusion. The $6.62B (supplied, net of borrows) + $3.43B (borrowed) breakdown from currentChainTvls is the figure used here. "Total deposits ~$10.05B" is my computation (TVL + borrowed), not a number published verbatim by DeFiLlama.
- **Price snapshot conflict.** A search summary cited "$2.00, mcap $1.1–1.2B" for June 2026, but the directly fetched CoinGecko page on 2026-06-11 showed $1.70 / $935.5M. The fetched CoinGecko figures are used. Prices move fast; re-verify before posting.
- **Fees figures** ($192.4M annualized, $15.77M 30d) come from a search-result summary of DeFiLlama dated ~2026-06-03, not a direct page fetch — verify on https://defillama.com/protocol/morpho before quoting.
- **Morpho Midnight (2026-05-14)** and Vault V2 commit activity are sourced only from CoinMarketCap's AI updates page; not confirmed against an official Morpho blog post.
- **Could not verify:** exact date of the 22.6% unlock and its size in tokens; exact launch dates of the Coinbase UK and SOL-backed loan products; current per-vault deposit figures for Gauntlet/Steakhouse (Gauntlet's "30+ vaults, $2B+ vault TVL across Morpho/Drift/Kamino" claim is from early-2026 secondary sources); precise count of active markets/vaults (Morpho app data not fetched). CT sentiment is from aggregator summaries, not direct X data.
- All numbers above were found in searches/fetches performed 2026-06-11; none are from model training data.
