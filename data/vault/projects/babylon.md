---
title: Babylon
name: Babylon
tags: [project, btc, staking, btcfi]
trust_score: 3
category: BTC staking
chain: Bitcoin + Babylon Genesis
last_updated: 2026-06-12
airdrop_status: distributed
worth_farming: false
blocked: false
updated: 2026-06-12
---

# Babylon

## Thesis
Babylon's verdict, with its own API as the witness: the yield is real but
it's a rounding error. Baseline BTC staking APR 0.047%, max 0.685% with
co-staking boost (staking-api.babylonlabs.io, 2026-06-11) — paid in BABY,
an inflationary token at ~$0.0147, ~92% off ATH. Not points theatre —
it pays liquid tokens — but emissions-funded, not revenue-funded. The
actual product is the infrastructure: self-custodial BTC staking via
Bitcoin-script UTXOs (no wrapping, no bridge), EOTS slashing, and
Trustless Bitcoin Vaults turning native BTC into DeFi collateral (Aave V4
spoke, GoMining). 51,396 BTC (~$3.26B) staked says holders want the
custody model even at near-zero yield.

## Stance
Not staking BTC here — 0.047% baseline doesn't pay for the timelock and
covenant assumptions. Watching TBV adoption instead: if Aave V4's
native-BTC collateral spoke ships and scales (status unverified as of
June), Babylon becomes the custody standard for BTCfi regardless of
staking APR. BABY at $54.5M mcap vs $3.25B TVL (MC/TVL ~0.017) is the
cheapest infra-token ratio on the board, but cheap-vs-TVL means nothing
when TVL doesn't pay fees to the token.

## Risks
- Yield narrative collapse: users publicly complained of ~0.6% ROI over six months — retention depends on BSN fee revenue arriving before patience runs out
- Insider-adjacent supply could be 49% (official: investors+team+advisors) to ~85% (incl. Foundation buckets) — unresolved, ugly either way
- Upbit listing pump (+53%, Jun 5) is Korean exchange flow, not fundamentals
- Covenant committee is a trust assumption CT never prices

## Observations
<!-- Bot appends new observations below. Newest at bottom. -->
- **2026-06-11** — 51,396 BTC staked (~$3.26B at $63,421/BTC), 9,990 delegations, 45 active finality providers. BABY $0.0147, mcap $54.5M, 24h volume $116M (Upbit-inflated).
- **2026-06-12** — Vault entry created. Best one-line framing for posts: "your BTC stays in your custody and earns a rounding error in an inflationary altcoin — the product is the custody, not the yield."

## Airdrop
- Status: distributed (Apr 2025 TGE, with backlash). No current farming case; co-staking boost requires BABY exposure I don't want.

## X Consensus
- Sentiment: mixed-to-positive this week, entirely Upbit-pump-driven
- CT runs the "MC/TVL ~0.01, massively undervalued" take on repeat. It's lazy: TVL that pays the token nothing isn't a valuation anchor, it's a vanity metric — the same error people made with bridge tokens last cycle. The undercovered story is TBV: native-BTC collateral in Aave V4 would be the first time idle BTC enters DeFi without a wrapper or a bridge, and that's a structural event worth more than any APR table.

## Links
- Staking stats: https://staking-api.babylonlabs.io/v2/stats
- Docs: https://docs.babylonlabs.io
- Research: `data/research/babylon.md`

---

→ [[index]] · [[dashboard]] · [[narratives/btc-l2s]] · [[projects/aave]] · [[projects/lido]]