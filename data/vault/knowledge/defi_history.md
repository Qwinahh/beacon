---
type: knowledge
topic: defi-history
updated: 2026-06-02
source: seeded
---

# DeFi History — Key Protocols & Milestones

Context for the writer: understand where protocols came from and how they
evolved. Use to write takes that reflect actual knowledge, not surface headlines.

---

## Foundational Layer (2018–2020)

- **MakerDAO** (2017): First major DeFi protocol. DAI = first decentralised stablecoin.
  Introduced collateralised debt positions (CDPs). Still operates; now called Sky.
- **Uniswap v1** (Nov 2018): AMM with constant-product formula (x*y=k).
  Removed order books from DEX design entirely.
- **Compound** (Sep 2018): On-chain money market. Introduced COMP governance token
  + liquidity mining (Jun 2020) — started DeFi Summer.
- **Aave** (Jan 2020, formerly ETHLend): Flash loans, variable/stable rate borrowing.

## DeFi Summer 2020

- Yield farming: lock tokens, earn governance tokens. TVL $1B → $15B in 6 months.
- **Yearn Finance** (Jul 2020): Automated yield optimiser. YFI token distribution
  was fully fair-launch — no VC, no team allocation. Set a cultural benchmark.
- **Curve Finance** (Jan 2020): Stable-swap AMM optimised for pegged assets.
  CRV wars (bribery/gauge voting) became a meta within DeFi.
- **SushiSwap** (Aug 2020): Uniswap fork + vampire attack. Migrated ~$800M liquidity.
  First high-profile protocol fork controversy.

## 2021 — Expansion

- **Uniswap v3** (May 2021): Concentrated liquidity. Capital efficiency 4000x vs v2.
- **Polygon** PoS: EVM sidechain. Onboarded Aave, Curve, QuickSwap. TVL peaked ~$10B.
- **Arbitrum** and **Optimism** launched testnets → mainnet (late 2021/2022).
  Optimistic rollup architecture. Arbitrum overtook Polygon in TVL by 2022.
- **Terra/LUNA**: Algorithmic stablecoin UST backed by LUNA minting/burning.
  Grew to ~$30B TVL. Collapsed May 2022 — death spiral.

## 2022–2023 — Rebuild & Specialisation

- **GMX** (Sep 2021 on Arb, Oct 2022 on Avax): Perps DEX with GLP liquidity pool.
  Traders vs liquidity providers. First successful on-chain perps at scale.
- **Uniswap v4** designed (hooks). Not deployed until 2024.
- **EigenLayer** (Jun 2023): Restaking. ETH stakers secure additional networks
  (AVSs) and earn additional yield. TVL grew to $20B+ before EIGEN TGE.
- **Pendle Finance**: Yield tokenisation. Separate principal and yield tokens.
  Became the dominant yield-trading protocol in 2024.

## 2024–2025 — Perps & Points Era

- **Hyperliquid** (mainnet 2023, HYPE airdrop Nov 2024): On-chain order book perps.
  Custom L1 (HyperEVM). No VC. $1.8B raised for community via HYPE airdrop.
  Became the dominant on-chain perps venue by volume/OI by 2025.
- **dYdX v4** (Oct 2023): Migrated from Ethereum to its own Cosmos chain.
  Decentralised order book + validator set. TVL and volume declined post-launch.
- **Meteora** (Solana): DLMM (dynamic liquidity market maker). Dominant Solana DEX.
  META token anticipated.
- **Lighter** (2024): On-chain limit order book perps on Arbitrum. Targeting
  institutional-grade execution for on-chain traders.

---

## DeFi Structural Patterns

- **AMM → Order book**: The DeFi trajectory moves from passive AMMs toward
  active order-book matching (Hyperliquid, Lighter). Tighter spreads, deeper books.
- **Yield compression**: As more capital chases the same farms, APYs normalise.
  Early farmers capture the most value. Meta shifts every 6-12 months.
- **Points → Airdrop**: Replaced direct token incentives. Opaque and gameable,
  but works for bootstrapping TVL before TGE.
- **Governance token utility**: Most governance tokens have minimal actual
  cash flows attached. Exceptions: Curve/CRV (bribe economy), GMX (real yield).
