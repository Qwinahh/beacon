---
title: On-Chain and Derivatives Metrics — Reading Guide
type: knowledge
category: technical
tags: [knowledge, metrics, onchain, derivatives, trading]
confirmed: true
source_tier: 1
last_updated: 2026-06-13
updated: 2026-06-13
---

# On-Chain and Derivatives Metrics — Reading Guide

Reference for turning raw chain and derivatives data into post material.
Each metric section covers: what it is, the trap (common misread), and
a concrete post angle.

---

## 1. TVL (Total Value Locked)

**What it is.** The USD value of assets deposited into a protocol's smart contracts.
DeFiLlama is the standard source. Often used as a proxy for protocol health or adoption.

**The trap.** TVL double-counts constantly. A user deposits ETH into Lido (stETH),
deposits that stETH into Aave as collateral, borrows USDC, and deposits that USDC
into a Curve pool. The same ETH appears in Lido TVL, Aave TVL, and Curve TVL. DeFiLlama
attempts to deduplicate but does not catch all cases. Mercenary capital also inflates TVL
during incentive programs and exits within 72 hours of rewards ending — Berachain lost
98.3% of peak TVL this way, and Monad incentive programs showed the same pattern.

TVL growth rate matters more than absolute TVL for early-stage protocols. TVL retention
after an incentive program ends is the real test.

**Post angle.** When a protocol posts headline TVL numbers, look at the 30-day chart.
Flat-to-declining TVL on a rising token price is a structural divergence worth naming.
"$2B TVL" is a press release. "$2B TVL and −40% in 30d after points ended" is a post.

---

## 2. Perp Funding Rates

**What it is.** The periodic payment between longs and shorts on perpetual futures.
Positive funding = longs pay shorts (market tilted long, leverage crowded to the upside).
Negative funding = shorts pay longs (market tilted short). Rates reset every 1-8 hours
depending on the venue. Hyperliquid and Binance both publish real-time funding dashboards.

**The trap.** A single positive funding reading is noise. Sustained elevated positive
funding across multiple venues for 24-72+ hours is signal. Venue divergence matters too:
Hyperliquid funding positive while Binance funding is flat or negative means HL-specific
leverage buildup, not broad market consensus — a squeeze setup, not a trend trade.

Negative funding is misread in the other direction. Sustained negative funding indicates
short crowding, but the unwind can be violent in either direction: a short squeeze or a
genuine capitulation dump, depending on whether the shorts are right.

**Post angle.**
- Funding spike on HL but not Binance → squeeze setup, worth posting with OI context
- Funding sustained >0.1% per 8h for 48h+ → crowded longs, note it as a risk factor
- Funding flips from positive to sustained negative → watch for short-squeeze or confirmation;
  post the flip itself, not the prediction

Funding rate is also the source of [[projects/ethena|Ethena]] sUSDe yield. When funding
is positive across venues, Ethena earns carry on its delta-neutral hedge and sUSDe APY
rises. Sustained negative funding compresses yield and, at extremes, requires the reserve
fund ($62M as of mid-2026, ~1.18% of TVL) to cover the shortfall. The reserve fund size
relative to TVL is the metric nobody tracks but everybody should. See [[narratives/yield-bearing-stables]].

---

## 3. Open Interest (OI)

**What it is.** The total notional value of open perpetual futures contracts — long and
short combined. OI is a leverage gauge: high OI means a lot of borrowed capital is in
the market. OI tracks how much fuel is in the system for a move in either direction.

**The trap.** OI and volume are not the same thing. High volume with flat OI = traders
rotating positions. High OI with low volume = positions held, not turned over. The
dangerous setup is high OI + high price + low volume: leverage is extended and nobody
is actively managing it. That configuration resolves violently.

Watch OI-to-market-cap ratio, not raw OI. OI of $5B on a $500B BTC market is different
from $5B on a $50B altcoin. Elevated OI/market-cap ratios on small-caps indicate a
leverage overhang that liquidation cascades can trigger.

**Post angle.**
- OI up >20% in 48h with no news catalyst → structural flow entering, post with the
  specific numbers and the venue breakdown (HL vs Binance vs OKX)
- OI drops sharply mid-rally → deleveraging while price holds; the longs that survived
  are unlevered, a potentially more durable base
- Large OI divergence between a perps DEX and a CEX on the same asset → arbitrage or
  a story about different user bases positioning differently

---

## 4. Exchange In/Outflows

**What it is.** The net movement of assets into (inflow) or out of (outflow) centralized
exchange wallets. Outflows indicate tokens are moving to self-custody or DeFi — historically
an accumulation signal. Inflows indicate tokens moving toward exchanges — historically a
potential selling pressure signal.

**The trap.** Not all inflows are sells. Market makers, OTC desks, and institutions move
large amounts to exchanges without intention to sell into the order book. Spike inflows
from a single address are often institutional, not retail panic. The signal is cleaner
in aggregate sustained trends (7-30 day net flows) than single-day readings.

Also: exchange coverage is incomplete. On-chain data vendors (Glassnode, Nansen, CryptoQuant)
track different exchange wallet sets and produce different numbers. Cross-reference at least
two sources before citing a specific outflow figure.

The June 2026 regime context: roughly 500,000 ETH moved off exchanges as ETH retested
the $1,600-$2,000 zone. That is an accumulation-consistent reading, not a panic signal.
See [[knowledge/market-regime-2026]].

**Post angle.**
- Sustained 7-day net outflow >2% of circulating supply on a major asset →
  accumulation signal, worth a post with the chart
- Inflow spike before a major unlock date → pre-positioning to sell, flag as a risk
- Outflow while price is flat or declining → divergence; patient accumulation or
  exhausted sellers; more nuanced than either bullish or bearish

---

## 5. The Basis (Spot vs. Perp)

**What it is.** The spread between the spot price of an asset and the price of its
perpetual futures contract. Also called the "cash-and-carry" spread. When perps trade
above spot, funding is positive and longs pay; the basis is positive. When perps trade
below spot, funding is negative and shorts pay; the basis is negative.

Traders capture the basis via a delta-neutral position: long spot + short perp = earn
the funding rate without directional exposure. This is the trade Ethena runs at scale
for sUSDe yield.

**The trap.** The basis narrows during deleveraging and widens during euphoria. Citing
a wide basis as a "bullish signal" misreads the mechanism — wide positive basis means
leverage is on the long side and eventually normalizes. It is not a sign that the market
expects higher prices so much as it is a measure of how much leverage is in place.

**Post angle.**
- Basis widens to >0.1%/8h sustained → carry trade is live; Ethena yield will reprice
  upward; post the connection between funding and sUSDe APY for mechanism education
- Basis compresses toward zero despite rising price → the move is unleveraged; more
  durable than it looks; post as a "clean move" signal
- Basis goes persistently negative on a major asset → Ethena reserve drawdown risk
  rises; post the mechanic, not a prediction

---

## 6. Stablecoin Supply Growth

**What it is.** The total circulating supply of major stablecoins (USDT, USDC, USDe,
USDS, and others), tracked via on-chain data. Aggregate stablecoin supply growth is
a dry-powder indicator: more stablecoins in the system means more potential buying
capital available. Stablecoin supply contraction (redemptions outpacing minting)
historically coincides with — and slightly leads — price drawdowns.

**The trap.** Stablecoin supply growth does not guarantee deployment. Stablecoins can
sit idle in wallet addresses or in yield positions and never touch risk assets. In the
current flight-to-quality regime (as of June 2026), a meaningful portion of stablecoin
growth is parked in yield-bearing structures (sUSDe, sDAI, USDY) rather than cycling
into speculative tokens — that is a different market than one where new USDC is being
minted to buy altcoins.

Watch the composition of growth, not just the headline number. USDT growth on exchanges
is more directly investable in risk assets than sUSDe growth, which is already deployed
in a yield strategy.

**Post angle.**
- Stablecoin supply +$5B in a week without a corresponding move in asset prices →
  dry powder loading; post as a setup, not a confirmation
- Stablecoin supply contraction while prices are flat → early warning; sellers haven't
  acted yet but redemptions say they're preparing
- Yield-bearing stablecoin supply exceeding fiat-backed equivalent on a given chain →
  structural shift in how capital positions between cycles; thread-worthy

---

## How to use this in posts

1. **The mechanism post.** Pick one metric, explain what it actually measures vs. what
   CT thinks it measures (the trap), and cite a current reading. No prediction required.
   "OI up 22% in 48h on HL, volume flat. That's leverage entering, not trading. Watch
   for the flush." is a complete post.

2. **The funding-to-Ethena link.** Any time funding rates move materially, connect it
   to sUSDe APY. Most CT tracks Ethena's yield without tracking where it comes from.
   Citing the mechanic with live numbers is differentiated content.

3. **The unfashionable metric.** When the narrative is price and everyone is posting
   charts, post the OI/market-cap ratio or the net exchange flow instead. The data
   nobody quotes is the data with remaining signal.

4. **Regime check.** Anchor any metric post to the current regime context from
   [[knowledge/market-regime-2026]]. A bullish outflow reading in a flight-to-quality
   environment carries different weight than the same reading in a speculative expansion.
