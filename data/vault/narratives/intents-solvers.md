---
title: Intents & Solvers
narrative: Intents & Solvers
tags: [narrative, dex, intents, solvers, mev]
conviction: medium
last_updated: 2026-06-12
updated: 2026-06-12
---

# Intents & Solvers

## Thesis
Intents quietly became the default execution layer for serious size —
without ever being a tradeable meta. By 2026, most meaningful DEX volume
above small-retail flows through solver auctions: CoW Protocol (batch
auctions + coincidence-of-wants) hit 34.3% DEX-aggregator share by Aug
2025 and $10B+/month on Ethereum by late 2025; UniswapX owns retail
distribution via Uniswap frontends; 1inch Fusion runs the RFQ/resolver
model cross-chain. Cross-chain intents consolidated on ERC-7683 (Across,
Eco Routes, UniswapX) — intents are eating bridges too. Here's the rub
for traders: the value accrues to solvers and integrators, not tokens.
COW/1INCH/UNI capture little of the flow they route. This is the next
DEX meta in architecture terms and a nothing-burger in token terms,
which is exactly why CT ignores it — no bags to talk.

## What to watch
- Solver concentration: if 2-3 solvers win most CoW/UniswapX auctions, "decentralized execution" becomes market-maker oligopoly with extra steps
- ERC-7683 adoption — each new integration retires a bridge
- Whether any intent protocol ships token value capture (fee switch, solver-bond burns)
- AMM LP share of volume continuing to shrink → passive LPing keeps dying; affects every DEX thesis
- [[projects/hyperliquid|Hyperliquid]] counter-case: a CLOB that beat solvers by just being a better exchange

## Key projects
- CoW Protocol — batch auctions, the share-gainer (12% → 26% → 34.3% in 20 months)
- UniswapX — Dutch auctions, deepest retail distribution
- 1inch Fusion — resolver model, cross-chain via Fusion+
- Across — ERC-7683 cross-chain intents leader
- [[projects/jupiter|Jupiter]] — Solana's equivalent consolidation, different architecture

## Signal patterns
- Solver-win concentration data published → centralization angle, post it before it's consensus
- Major frontend (wallet, aggregator) defaulting to intent routing → adoption confirmation
- MEV sandwich volume declining on Ethereum → intents working as designed, quantifiable post
- Bridge sunsetting in favor of intent settlement → "intents ate bridges" thread material

## Updates
<!-- Bot appends narrative updates here -->
- **2026-06-12** — Initial entry. The meta is real in flow terms, invisible in token terms. The post-worthy angle is solver economics and concentration — nobody covers the auction layer because there's no coin attached.
