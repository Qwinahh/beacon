@echo off
REM Push: Fear & Greed, CoinGecko, DeFiLlama extended context
REM Run from X Bot folder. Paste GitHub PAT when prompted for password.

cd /d "%~dp0"

git add bot/sources/fear_greed.py
git add bot/sources/coingecko.py
git add bot/sources/defillama_ctx.py
git add bot/brain/context.py
git add requirements.txt

git status

git commit -m "feat: live market data injection into every writer call

- bot/sources/fear_greed.py: Alternative.me Fear & Greed Index
  Free, no key. Injected as sentiment context on every post.
  Detects extreme readings (<=20 or >=80) worth posting about directly.

- bot/sources/coingecko.py: CoinGecko market data
  Free, no key. Trending coins, BTC dominance, ETH dominance,
  total market cap + 24h change, per-token price + 24h/7d change.

- bot/sources/defillama_ctx.py: DeFiLlama extended context
  Supplements existing defillama.py with per-protocol TVL history,
  7d/30d change, weekly movers, total DeFi TVL trend, real yields.

- bot/brain/context.py: _build_live_market_context() injects all
  three sources into every writer call. All fail silently if
  unavailable. No API keys needed for any of them."

git push origin master
echo.
echo Done. Every post the bot generates now has:
echo   - Fear ^& Greed index (current sentiment + trend)
echo   - CoinGecko: BTC dominance, total mcap, trending coins
echo   - DeFiLlama: total TVL, weekly movers, real yields
echo.
pause
