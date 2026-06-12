# defillama-top20 — research (2026-06-12)

## Top 20 by TVL

Source: DeFiLlama API (`https://api.llama.fi/protocols` + `https://api.llama.fi/lite/protocols2`), fetched 2026-06-12 ~09:50 UTC. CEX entries (Binance, OKX, Bybit, Robinhood, etc.) excluded. 30d change computed as (tvl − tvlPrevMonth) / tvlPrevMonth from the same API response.

| Rank | Protocol | Category | TVL | 30d change | Chains |
|------|----------|----------|-----|------------|--------|
| 1 | Lido | Liquid Staking | $14.76B | −26.3% | 5 (Ethereum, Solana, ...) |
| 2 | SSV Network | Staking Pool | $12.21B | −27.4% | 1 (Ethereum) |
| 3 | Aave V3 | Lending | $11.65B | −17.9% | 21 (Ethereum, Plasma, Arbitrum, ...) |
| 4 | LayerZero V2 | Bridge | $7.47B | +6.2% | 60 (Ethereum, Base, Arbitrum, ...) |
| 5 | WBTC | Bridge | $7.21B | −22.5% | 1 (Bitcoin) |
| 6 | Morpho Blue | Lending | $6.50B | −13.3% | 38 (Ethereum, Base, Hyperliquid L1, ...) |
| 7 | Binance staked ETH | Liquid Staking | $6.13B | −27.3% | 2 (Ethereum, BSC) |
| 8 | Sky Lending | CDP | $5.71B | −2.6% | 1 (Ethereum) |
| 9 | Hyperliquid Bridge | Bridge | $5.70B | +16.6% | 2 (Hyperliquid L1, Arbitrum) |
| 10 | Coinbase Bridge | Bridge | $5.39B | −18.3% | 5 (Bitcoin, XRPL, Doge, ...) |
| 11 | EigenCloud (EigenLayer) | Restaking | $4.61B | −37.1% | 1 (Ethereum) |
| 12 | Ethena USDe | Basis Trading | $4.48B | +12.8% | 1 (Ethereum) |
| 13 | Binance Bitcoin | Bridge | $4.30B | −21.7% | 1 (Bitcoin) |
| 14 | USDT0 | Bridge | $3.61B | +0.7% | 1 (Ethereum) |
| 15 | SparkLend | Lending | $3.35B | +1.5% | 2 (Ethereum, Gnosis) |
| 16 | Babylon Protocol | Restaking | $3.24B | −20.9% | 1 (Bitcoin) |
| 17 | JustLend | Lending | $3.02B | −16.4% | 1 (Tron) |
| 18 | BlackRock BUIDL | RWA | $3.02B | +2.7% | 8 (Ethereum, Aptos, Solana, ...) |
| 19 | Circle USYC | RWA | $3.01B | +1.0% | 4 (BSC, Ethereum, Noble, ...) |
| 20 | Tether Gold | RWA | $2.96B | −11.9% | 8 (Ethereum, Monad, Plasma, ...) |

Just outside the top 20 (as of 2026-06-12, DeFiLlama): ether.fi Stake (Liquid Restaking, $2.76B, −44.5% 30d), Arbitrum Bridge (Canonical Bridge, $2.70B, −21.3% 30d).

## Observations

- Broad 30d drawdown (as of 2026-06-12, DeFiLlama): 14 of the top 20 are down over 30 days, with ETH-correlated staking/restaking hit hardest — EigenCloud −37.1%, SSV −27.4%, Binance staked ETH −27.3%, Lido −26.3%. Pattern is consistent with falling ETH/BTC prices deflating dollar-denominated TVL rather than mass outflows.
- Bridges dominate by count: 6 of the top 20 (LayerZero V2, WBTC, Hyperliquid Bridge, Coinbase Bridge, Binance Bitcoin, USDT0) — roughly $33.7B combined (2026-06-12, DeFiLlama). Lending is next with 4 entries (Aave V3, Morpho Blue, SparkLend, JustLend, ~$24.5B combined).
- Biggest 30d gainers against the downtrend (2026-06-12, DeFiLlama): Hyperliquid Bridge +16.6%, Ethena USDe +12.8%, LayerZero V2 +6.2% — Hyperliquid and Ethena attracting capital while the rest of DeFi bleeds.
- RWA/tokenized assets are now a fixture of the top 20: BlackRock BUIDL ($3.02B), Circle USYC ($3.01B), Tether Gold ($2.96B) — ~$9B combined and all flat-to-up over 30d (2026-06-12, DeFiLlama), i.e. the most drawdown-resistant category in the list.
- Surprises: SSV Network sits at #2 with $12.21B (DVT staking infrastructure, rarely discussed at that scale); no DEX appears anywhere in the top 20 (Uniswap et al. all below ~$2.9B); ether.fi fell out of the top 20 after a −44.5% 30d drop.

## Caveats

- All figures are point-in-time from the DeFiLlama API fetched 2026-06-12 ~09:50 UTC; TVL moves continuously with prices and flows.
- Rankings use DeFiLlama's split-protocol view (e.g. "Aave V3" not combined Aave V2+V3; "Morpho Blue" not all Morpho products). Combined parent-protocol rankings would differ slightly (Aave combined would rank higher).
- The API's `change_1m` field returned null for all protocols, so 30d change was computed from `tvl` vs `tvlPrevMonth` in the `/lite/protocols2` response — same source, but "prev month" is DeFiLlama's snapshot definition, not exactly 30 calendar days.
- Several "Bridge" entries (WBTC, Coinbase Bridge, Binance Bitcoin, Binance staked ETH) are custodial wrappers counted by DeFiLlama as TVL; some analysts exclude these from "real DeFi" TVL. They are kept here per DeFiLlama's classification.
- Staking/restaking TVL (Lido, SSV, EigenCloud, Babylon) partially double-counts the same underlying ETH/BTC across protocols; summing the column overstates unique capital.
- TVL in this list is USD-denominated, so 30d changes blend price moves and actual deposits/withdrawals.
