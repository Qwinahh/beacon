---
title: DeFi Primitives — How the Core Protocols Work
type: knowledge
category: technical
tags: [knowledge, technical, defi]
last_updated: 2026-06-01
source_tier: 1
confirmed: true
updated: 2026-06-07
---

# DeFi Primitives — How the Core Protocols Work

Reference for the bot when discussing DeFi mechanics, yield sources, and protocol risk.
Understanding primitives helps identify whether a yield is sustainable or subsidized.

---

## Automated Market Makers (AMMs)

### How AMMs Work
- Liquidity providers (LPs) deposit two tokens in a pool (e.g., ETH/USDC).
- Traders swap against the pool. Price adjusts based on the ratio of reserves.
- Constant product formula: `x * y = k` (Uniswap V1/V2)
- LP earns trading fees (typically 0.05%–1% per swap).

### Impermanent Loss (IL)
- If the price of one asset changes significantly, LPs end up holding more of the losing asset.
- Not a real loss until you withdraw — hence "impermanent."
- Becomes permanent when you exit.
- At 2x price change: ~5.7% IL vs. just holding
- At 5x price change: ~25.5% IL vs. just holding
- Correlated pairs (e.g., USDC/USDT, wBTC/USDC) have less IL than volatile pairs.

### Key AMM Protocols
| Protocol | Innovation | Chain |
|---|---|---|
| Uniswap V2 | Standard AMM, TWAP oracle | ETH |
| Uniswap V3 | Concentrated liquidity (LPs set price ranges) | ETH + L2s |
| Curve | Optimized for stablecoins / correlated assets | ETH |
| Balancer | Multi-token pools, custom weights | ETH |
| Raydium | AMM + CLOB hybrid on Solana | SOL |
| Meteora | DLMM (dynamic liquidity bin market maker) | SOL |
| Jupiter | Aggregator across all SOL DEXs | SOL |

### CLMM / DLMM (Concentrated Liquidity)
- LPs choose a price range instead of providing liquidity across infinite range.
- More efficient capital, higher fees earned per dollar — if price stays in range.
- Higher risk: if price exits range, LP stops earning and holds 100% of the declining asset.
- Active management required for volatile pairs.

---

## Lending & Borrowing

### How It Works
- Suppliers deposit assets. Receive interest tokens (aTokens in Aave, cTokens in Compound).
- Borrowers provide collateral, borrow up to a collateralization ratio.
- Interest rate adjusts algorithmically based on utilization.
- Liquidations: if collateral value falls below liquidation threshold, bots liquidate.

### Key Metrics
- **LTV (Loan-to-Value)**: Max you can borrow against collateral. ETH LTV ~80% on Aave = deposit $100 ETH, borrow up to $80.
- **Liquidation threshold**: Point where position gets liquidated (usually 5-10% above LTV).
- **Health factor**: Ratio of collateral to debt. Below 1 = liquidatable.
- **Utilization rate**: % of supplied assets being borrowed. Drives interest rates.

### Key Protocols
| Protocol | Notes |
|---|---|
| Aave | Largest. Multi-chain. GHO stablecoin. |
| Compound | Original. COMP governance token. |
| Morpho | Optimizes Aave/Compound rates via P2P matching |
| Spark (MakerDAO) | Powers DAI/USDS with sDAI yield |
| Kamino | Solana lending leader |

---

## Perpetuals DEXs

### How Perps Work (CEX Model)
- Trade with leverage (up to 50x). No expiry (unlike futures).
- Funding rate mechanism: if longs dominate, longs pay shorts (and vice versa). Keeps price anchored to spot.
- Mark price (oracle) vs. index price (external). Liquidation based on mark price.

### On-Chain Perps
- **vAMM model (dYdX V1, Perpetual Protocol)**: Virtual liquidity pool. No real LPs needed. Less efficient.
- **Oracle-based model (GMX)**: Trades against oracle price. LPs take the other side. LPs win when traders lose net.
- **Orderbook model (Hyperliquid)**: Full on-chain orderbook with HFT-level performance. Superior UX.

### Funding Rate Dynamics
- Positive funding: longs pay shorts. Means market is bullish, leveraged long.
- Negative funding: shorts pay longs. Means market is bearish, leveraged short.
- Funding extremes often precede reversals.
- Basis trade: hold spot long + perp short = collect funding rate if positive (delta-neutral).

---

## Yield Sources — Real vs. Subsidized

Understanding where yield comes from is key to assessing sustainability.

### Real Yield (Sustainable)
1. **Trading fees**: LP earns % of swaps. Revenue proportional to volume.
2. **Borrowing interest**: Lenders earn from borrowers. Rate set by utilization.
3. **Liquidation fees**: Protocols take a cut of liquidation penalties.
4. **Real-world asset yield**: Tokenized T-bills earn from actual government yield.
5. **Protocol revenue sharing**: Protocols distribute real fees to stakers (e.g., GMX, dYdX).

### Subsidized Yield (Not Sustainable)
1. **Liquidity mining**: Protocol inflates token supply to pay LPs. Dilutes existing holders.
2. **Ponzi yield**: Yield paid from new depositor capital (Anchor's 19.5% on UST).
3. **Points/airdrop farming**: Expected future airdrop value not yet real.
4. **Governance token incentives**: Token price supports APY. Token dumps → APY collapses.

### The Yield Sustainability Test
Ask: "If token price went to zero, would this yield still exist?"
- If yes → real yield
- If no → subsidized / token-dependent

---

## Stablecoins

### Types
| Type | Mechanism | Examples | Risk |
|---|---|---|---|
| Fiat-backed | 1:1 USD in bank | USDC, USDT, BUSD | Custodian / regulatory risk |
| Overcollateralized | Crypto collateral, over-collateralized | DAI, USDS, LUSD | Collateral price crash |
| Algorithmic | Algorithm + seigniorage | UST (dead), FRAX | Death spiral risk |
| CDP (Collateralized Debt Position) | Lock collateral, mint stablecoin | MakerDAO/DAI | Collateral + governance risk |
| Yield-bearing | Holds T-bills / RWAs | sDAI, sUSDE, USDY | Smart contract + custodian |

### Key Events in Stablecoin History
- **USDT (Tether)**: Exists since 2014. Most traded. Reserves always questioned. Multiple regulatory settlements. Still dominant.
- **DAI (MakerDAO)**: Oldest decentralized stablecoin. Survived multiple crises. Now backed mainly by USDC (centralization concern).
- **UST/Luna (Terra)**: $60B algorithmic stablecoin collapsed May 2022. Death spiral: UST de-pegs → LUNA minted to restore → hyperinflation → both go to zero.
- **USDC de-peg (Mar 2023)**: Circle had $3.3B stuck in SVB. USDC briefly traded at $0.87. Recovered when Fed guaranteed deposits.
- **USDe (Ethena)**: Delta-neutral stablecoin. Backs USDe with BTC/ETH spot + short perps. Earns funding rate. Yields vary with market. Novel model — risk is negative funding.

---

## Liquid Staking

- **What**: Stake ETH (or SOL, etc.) and receive a liquid token (stETH, rETH) that earns staking rewards.
- **Why useful**: Normal staked ETH was locked until Shapella upgrade. LSTs let you use staked value in DeFi.
- **Key protocols**: Lido (stETH, ~30% ETH stake), Rocket Pool (rETH, decentralized), Frax Ether (sfrxETH).
- **Risk**: Smart contract risk + depeg risk (stETH traded below ETH during 3AC crisis, Jun 2022).
- **Restaking (EigenLayer)**: Re-use staked ETH to secure other networks (Actively Validated Services). Earns additional yield. Higher risk — slashing for multiple networks.

---

## Key Blockchain Concepts for Context

### Gas
- Cost of computation on Ethereum. Denominated in Gwei (1 ETH = 1B Gwei).
- High gas = network congested. Often correlates with market activity.
- L2s solve this: Arbitrum, Base, Optimism transactions cost cents vs. dollars on mainnet.

### MEV (Maximal Extractable Value)
- Profit extracted by block producers by reordering/inserting/censoring transactions.
- Sandwich attacks: front-run + back-run a DEX trade, profiting from slippage.
- MEV is a tax on regular users. Flashbots (MEV-Boost) redistributes some to validators.

### Tokenomics Red Flags
- High % for team/VCs with short vesting
- Inflation rate outpacing protocol growth
- No value accrual to token (governance only)
- Token unlock schedules with large near-term unlocks
- Concentrated ownership (whale can dump)

---
## Related Notes
- [[crypto-history]] — When these primitives emerged and why
- [[exp