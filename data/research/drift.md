# drift — research (2026-06-11)

> **TL;DR for the bot:** Drift is NOT business-as-usual. It was hacked for ~$295M on 2026-04-01 (DPRK-attributed), perp trading has been suspended since, and the protocol is mid-recovery with a Tether-led ~$148M rescue package and a planned relaunch as a USDT-settled, security-first perps exchange. Any tweet framing Drift as a live Hyperliquid competitor right now would be wrong.

## Key metrics

| Metric | Value | As of | Source URL |
|---|---|---|---|
| DRIFT price | $0.06411 | 2026-06-11 | https://www.coingecko.com/en/coins/drift-protocol |
| Market cap | $36,934,682 (rank #558) | 2026-06-11 | https://www.coingecko.com/en/coins/drift-protocol |
| FDV | $63,553,042 | 2026-06-11 | https://www.coingecko.com/en/coins/drift-protocol |
| Circulating / max supply | 581.16M / 1B (Mkt Cap/FDV 0.58) | 2026-06-11 | https://www.coingecko.com/en/coins/drift-protocol |
| Token 24h trading volume | $18,450,216 | 2026-06-11 | https://www.coingecko.com/en/coins/drift-protocol |
| ATH / drawdown | $2.60 (2024-11-09), −97.5% from ATH | 2026-06-11 | https://www.coingecko.com/en/coins/drift-protocol |
| ATL | $0.05333 (today's 24h low matched it) | 2026-06-11 | https://www.coingecko.com/en/coins/drift-protocol |
| TVL | $291.24M (DeFiLlama); CoinGecko shows $311.9M | 2026-06-11 | https://defillama.com/protocol/drift |
| Derivatives volume 24h (DeFiLlama) | $190.52M — **treat with caution, see Caveats** | 2026-06-11 | https://defillama.com/protocol/drift |
| Spot/app volume 24h | $18.15M | 2026-06-11 | https://defillama.com/protocol/drift |
| Open interest | Not verifiable today — perps suspended; Drift's contracts API returns empty. Pre-hack marketing figure ">$700M OI" (undated) | 2026-06-11 | https://eco.com/support/en/articles/15083167-drift-protocol-solana-perpetuals-dex-deep-dive |
| Exploit size | $295.4M (April 1, 2026) | 2026-05-05 | https://www.coindesk.com/business/2026/05/05/drift-outlines-a-recovery-plan-for-users-after-usd295-million-dprk-linked-exploit |
| Rescue package | Up to $147.5M ($127.5M Tether + $20M partners, incl. $100M revenue-linked credit facility) | 2026-04-16 | https://www.coindesk.com/business/2026/04/16/drift-gets-usd148-million-funding-from-tether-and-partners-as-it-replaces-circle-stablecoin-with-usdt-after-massive-exploit |

## Hyperliquid comparison

Honest version: **this is not currently a competition.** Drift's perp trading has been suspended since the April 1, 2026 exploit, while Hyperliquid is the runaway category leader.

| Dimension | Drift | Hyperliquid | As of / Source |
|---|---|---|---|
| 24h perp volume | Suspended (DeFiLlama still prints $190.5M/24h — likely stale/misleading, see Caveats) | ~$10.54B | 2026-06-11; https://defillama.com/protocol/drift ; https://www.coinglass.com/exchanges/Hyperliquid |
| Open interest | Unverifiable today; ">$700M" pre-hack (undated) | ~$10.24B (CoinGlass), ">$9B" (Datawallet) | 2026-06-11; https://www.coinglass.com/exchanges/Hyperliquid ; https://www.datawallet.com/crypto/hyperliquid-statistics |
| 30-day perp volume | n/a (suspended) | ~$172.63B | 2026 per https://www.datawallet.com/crypto/hyperliquid-statistics |
| Token valuation | DRIFT FDV $63.6M, mcap $36.9M | HYPE mcap >$14B, ATH $69.97 | 2026-06-11 CoinGecko; https://finance.biggo.com/news/4BNAf54B2jrwCtglAsYt |
| Architecture | Solana program: hybrid JIT auction + AMM fallback + orderbook, cross-margin, spot + perps + vaults + lend | Own L1 with fully on-chain CLOB, HyperEVM ecosystem | https://eco.com/support/en/articles/15083167-drift-protocol-solana-perpetuals-dex-deep-dive |
| Markets / leverage | ~35 perp markets, up to 20x on majors (pre-hack; relaunch will be perps-focused, reduced scope) | Leading perp DEX by activity in 2026 | https://eco.com/support/en/articles/15083167-drift-protocol-solana-perpetuals-dex-deep-dive |
| Settlement asset | Relaunching on USDT (was USDC) | USDC-based | https://www.coindesk.com/business/2026/04/16/drift-gets-usd148-million-funding-from-tether-and-partners-as-it-replaces-circle-stablecoin-with-usdt-after-massive-exploit |

Rough share math: even using Drift's pre-hack ~$700M OI vs Hyperliquid's ~$10.2B today, Drift was ~7% of HL's OI. HYPE's market cap (>$14B) is ~220x DRIFT's FDV ($63.6M). The relevant comparison set for Drift post-relaunch is Solana perps (Jupiter Perps et al.), not Hyperliquid head-on — its stated relaunch goal is "largest USDT-based perpetual exchange on Solana" (https://www.drift.trade/updates/drift-recovery-update-june-3-2026).

## Recent developments (last 30 days)

- **2026-05-05 — Recovery plan announced.** Recovery tokens pegged to verified user losses; recovery pool starts at ~$3.8M and is designed to grow to ~$151M (revenue + Tether + partners) until the full $295.4M in losses is covered. Relaunch planned as a "security-first" exchange: new multisig controls, time-locked operations, key rotation, reduced product scope focused on perps. https://www.coindesk.com/business/2026/05/05/drift-outlines-a-recovery-plan-for-users-after-usd295-million-dprk-linked-exploit ; https://www.dlnews.com/articles/defi/drift-to-issue-recovery-tokens-in-wake-of-295m-hack/
- **2026-05/06 — Relaunch window targeted for May–June 2026** (tentative), with USDT replacing USDC as settlement asset, backed by a Tether market-making facility; audits by OtterSec and Asymmetric Research required before going live. As of 2026-06-11 trading has not resumed. https://intellectia.ai/news/crypto/drift-plans-to-relaunch-exchange-in-may-or-june-2026
- **2026-06-01 — Upbit delisted DRIFT** (market support terminated 15:00 KST). https://www.tradingview.com/news/coinmarketcal:b566ba893094b:0-drift-protocol-upbit-delisting-01-june-2026/
- **2026-06-03/04 — Official recovery update:** Noah Prince (ex-Head of Protocol Engineering at Helium) joins as Head of Protocol for a full protocol reboot; former Gauntlet team members engaged for risk/liquidation-engine/vault work; Mandiant forensics conclusively attributed the exploit to UNC6862, a North Korean state-linked threat group. Recovery mechanics and relaunch timing still "to be shared." https://www.drift.trade/updates/drift-recovery-update-june-3-2026

## CT sentiment

- **Dominant narrative: hack + bailout, not trading metrics.** The April 1 DPRK exploit (~$295M, via Solana durable nonces per Decrypt: https://decrypt.co/366897/how-solana-exchange-drift-repay-users-295-million-crypto-hack) and the Tether rescue define all conversation.
- **The USDC→USDT switch was the spiciest CT topic:** users publicly asked why Circle offered no rapid support to a nine-figure-TVL protocol during the crisis, while Tether swooped in — fueling a broader debate about DeFi's reliance on centralized stablecoin issuers. https://stocktwits.com/news-articles/markets/cryptocurrency/drift-protocol-ditches-circle-s-usdc-for-usdt-after-280-m-hack/cZJvZokRIDk ; https://coincentral.com/tether-swoops-in-with-148m-to-save-drift-protocol-and-takes-usdcs-spot-in-the-process/
- **Mid-April optimism faded.** On the rescue news (~Apr 16), DRIFT rallied 18–20%+ to ~$0.50 and Stocktwits retail sentiment flipped to "bullish." Since then the token has bled back to $0.064 (today's 24h low touched the $0.0533 ATL) as the relaunch slipped through its May–June window and Upbit delisted — i.e., price action says confidence is NOT recovering. https://stocktwits.com/news-articles/markets/cryptocurrency/drift-protocol-ditches-circle-s-usdc-for-usdt-after-280-m-hack/cZJvZokRIDk ; https://www.coingecko.com/en/coins/drift-protocol
- Watch items for the bot: relaunch announcement (trading resumption), recovery-token distribution details, whether the recovery pool actually scales toward $151M.

## Caveats

- **DeFiLlama's "$190.52M derivatives volume 24h" (2026-06-11) directly conflicts with multiple reports that perp trading remains suspended.** It is likely stale, mislabeled, or residual settlement activity. Do NOT tweet it as live trading volume without re-verifying on relaunch.
- **Current open interest could not be verified.** Drift's own contracts API (data.api.drift.trade/contracts) returned empty, consistent with suspended perps. The ">$700M OI" figure (eco.com) is undated and almost certainly pre-hack.
- **TVL discrepancy:** DeFiLlama $291.24M vs CoinGecko (citing DeFiLlama) $311.9M, same day. Also unclear how much of TVL is frozen/locked pending relaunch vs withdrawable.
- **Exploit size is reported variously as $280M–$295.4M** across outlets; Drift's own recovery plan uses $295.4M.
- **Token confusion risk:** an initial search surfaced $0.0159 / $9.7M mcap — that is a DIFFERENT "Drift" token. The verified Drift Protocol (Solana) figures are from coingecko.com/en/coins/drift-protocol.
- **CoinGecko's ATL display was ambiguous** ("$0.05333 — Apr 01, 2026 (43 minutes)") and equals today's 24h low; ATL may have been set on hack day or re-touched today. Either way price is at/near all-time lows.
- CT sentiment is sourced from news coverage of social reaction (Stocktwits/CoinCentral/Cryptopolitan), not direct X firehose data.
- Hyperliquid 24h figures are from a CoinGlass snapshot surfaced via search on 2026-06-11 and fluctuate intraday; the 156.69% 24h volume change suggests an unusually active day, so the $10.5B may be above trend (30d avg ≈ $5.75B/day implied by the $172.63B figure).
