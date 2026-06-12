# Beacon — @Qwinahh

An autonomous crypto X account. Posts opinionated DeFi/perps commentary
with real data, drafts replies for human approval, tracks its own post
performance, and maintains an Obsidian knowledge vault of documented
positions on 20+ protocols.

Full documentation: **[SYSTEM.md](SYSTEM.md)** — architecture, agents,
workflows, configuration, and how to extend it.

Knowledge base: **[data/vault/](data/vault/)** — open in Obsidian.
Start at `index.md`; the bot's voice and 17 standing positions live in
`persona.md`.

## Quick start

Secrets required (GitHub → Settings → Secrets → Actions):

- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` — X API (posting)
- `GROQ_API_KEY` (or `CEREBRAS_API_KEY` / `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY`) — writer LLM
- `GH_PAT` — lets workflows commit state back to the repo
- Optional: `X_SCRAPER_COOKIES` (reply discovery), `X_BEARER_TOKEN` (metrics),
  `REPLICATE_API_TOKEN` (image generation), `WHALE_ALERT_API_KEY`, `DROPSTAB_API_KEY`

Manual triggers: Actions tab → pick a workflow → "Run workflow"
(post, engage, alpha, learn, track, suggest).

Local run: `pip install -r requirements.txt`, set the env vars from
`.env.example`, then `python post.py` (or `python -m agents.performance_tracker`,
`python -m agents.suggestion_agent`).

Quin's positions live in `data/portfolio.json` — keep it current; it drives
diary posts and reply disclosures.
