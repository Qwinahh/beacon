@echo off
REM Push: Knowledge base, verifier, learner agent, community scrapers
REM Run this from the X Bot folder (where .git lives)
REM When prompted for password, paste your GitHub PAT

cd /d "%~dp0"

git add agents/learner_agent.py
git add bot/brain/verifier.py
git add bot/brain/context.py
git add bot/sources/reddit.py
git add bot/sources/telegram.py
git add bot/sources/discord.py
git add .github/workflows/learn.yml
git add .github/workflows/post.yml
git add requirements.txt
git add data/vault/

git status

git commit -m "feat: knowledge base + learning system + community signal ingestion

- data/vault/knowledge/: seeded 2017-2025 crypto history, exploit history,
  narrative cycles, DeFi primitives (all confirmed Tier 1 facts)
- bot/brain/verifier.py: 4-tier source credibility system
  Tier 1 = on-chain/official -> write as fact
  Tier 2 = research/media -> write as fact (cited)
  Tier 3 = community (CT/Reddit/Discord/Telegram) -> signals only, never facts
  Tier 4 = noise -> discard
- agents/learner_agent.py: continuous learning loop (runs 2x/day via Actions)
  ingests DeFiLlama hacks/raises, RSS news feeds, community signals
  verifies all claims before vault writes
- bot/sources/reddit.py: Reddit community signal ingestion (praw)
- bot/sources/telegram.py: Telegram channel scraping (telethon)
- bot/sources/discord.py: Discord bot ingestion (discord.py)
- bot/brain/context.py: now injects relevant knowledge base facts
  into every writer call (confirmed historical context)
- .github/workflows/learn.yml: learner runs 6am + 5pm UTC
- data/vault/dashboard.md: added knowledge base + signals sections
- requirements.txt: added praw, telethon, discord.py"

git push origin master
echo.
echo Done. Check GitHub Actions for the new learn.yml workflow.
echo.
echo NEXT: Add these GitHub Secrets (Settings -^> Secrets -^> Actions):
echo   REDDIT_CLIENT_ID      (from reddit.com/prefs/apps)
echo   REDDIT_CLIENT_SECRET  (from reddit.com/prefs/apps)
echo   TELEGRAM_API_ID       (from my.telegram.org)
echo   TELEGRAM_API_HASH     (from my.telegram.org)
echo   TELEGRAM_SESSION_STRING (generate with: python -m telethon.sync)
echo   DISCORD_BOT_TOKEN     (from discord.com/developers - optional)
echo   X_SCRAPER_COOKIES     (already have this one)
pause
