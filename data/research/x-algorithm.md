# x-algorithm — research (2026-06-12)

Knowledge base on how the X "For You" feed algorithm works as of 2025–2026, for the crypto X bot.
Every numeric claim is tagged **[sourced]** (URL + date) or **[estimate/consensus claim]**.

## Big picture: what changed in 2025–2026

- **Jan 20, 2026:** xAI open-sourced the current For You algorithm at https://github.com/xai-org/x-algorithm (verified directly, repo README fetched 2026-06-12). It replaces the old 2023 `twitter/the-algorithm` repo. Architecture: **Home Mixer** (orchestration) + **Thunder** (in-network posts from follows) + **Phoenix** (Grok-based transformer ranker) + **Candidate Pipeline** (framework). Rust + Python. Repo updated **May 15, 2026** with a runnable inference pipeline, the **Grox** content-understanding service (spam detection, post-category classification, policy enforcement), and ads blending. **[sourced: github.com/xai-org/x-algorithm README, fetched 2026-06-12]**
- The new system has "eliminated every single hand-engineered feature and most heuristics." Phoenix predicts per-user probabilities for: favorite, reply, repost, quote, click, profile_click, video_view, photo_expand, share, dwell, follow_author, not_interested, block_author, mute_author, report. Final score = Σ (weight_i × P(action_i)); positive actions have positive weights, block/mute/report/not-interested have **negative** weights. The exact numeric weights are NOT published in the 2026 repo README. **[sourced: same README]**
- An **Author Diversity Scorer** attenuates scores of repeated authors in one feed load — your own posts compete with each other. **[sourced: same README]**
- **Nov 30, 2025:** the Following feed reportedly stopped being purely chronological; both feeds now ranked by Grok-predicted engagement. **[secondary sources: postory.io/blog/x-algorithm-2026, basenor.com blog — consensus claim, not verified against X official statement]**
- Several 2026 analyses claim Grok now does **sentiment/tone analysis**: positive/constructive posts get wider distribution, negative/combative tone gets reduced reach even with high engagement. **[consensus claim from secondary analyses (basenor.com, opentweet.io, 2026); plausible given the Grox classifiers in the repo, but no explicit weight published]**
- Musk stated (Sep 2025) that hand-coded ranking would be progressively replaced by Grok AI judgments — which is exactly what the Jan 2026 release shows. **[sourced: x.com/elonmusk/status/1965473807164125675 via socialmediatoday.com, 2025-09-09]**

## Signal weights

The explicit numeric weights below come from the **legacy heavyweight ranker**, restated by X Engineering in **Sep 2025** (so they were still operative through late 2025). The 2026 Phoenix model learns weights end-to-end and does not publish equivalents, but the relative ordering is widely treated as still directionally true.

| Signal | Weight | Status |
|---|---|---|
| Reply that the author then engages with | **+75** (150x a like) | [sourced: X Eng post x.com/XEng/status/1965226798460887127 via socialmediatoday.com/news/x-formerly-twitter-open-source-algorithm-ranking-factors/759702/, 2025-09-09] |
| Reply | **+13.5** (27x a like) | [sourced: same, 2025-09-09] |
| Profile click followed by like/reply | **+12.0** | [sourced: same] |
| Click into conversation + reply or like | **+11** | [sourced: same] |
| Click into conversation + dwell ≥ 2 minutes | **+10** | [sourced: same] |
| Retweet/repost | **+1.0** (2x a like) | [sourced: same] |
| Like (favorite) | **+0.5** | [sourced: same] |
| Video watched ≥ 50% | **+0.005** | [sourced: same — but note video gets large boosts elsewhere; multiple 2025-26 analyses say >10s watch time is a strong booster, consensus claim] |
| Bookmarks | ~10x a like | [estimate/consensus claim — cited in posteverywhere.ai and conbersa.ai 2026 analyses; bookmark weight was not in the Sep 2025 X Eng list, treat as approximate] |
| Negative feedback ("show less often", block, mute) | ~**-74** | [estimate: legacy 2023 open-source repo value, repeated in 2026 analyses (posteverywhere.ai); not re-confirmed in 2026 repo] |
| Report | ~**-369** | [estimate: legacy 2023 repo value; 2026 repo only confirms P(report) carries a negative weight, no number] |

Practical ordering for the bot: **author-engaged replies >> replies > profile clicks ≈ conversation clicks ≈ long dwell >> bookmarks > retweets > likes**, and one report can wipe out hundreds of likes' worth of score.

## Posting frequency effects

- **3–5 posts/day** is the consensus optimum for most accounts; engagement per post drops steeply beyond **~7 posts/day** (unless you're a media outlet). **[consensus claim: postnext.io/blog/x-posting-frequency, tweetarchivist.com posting-frequency guide 2025/2026, hootsuite 2025 data — aggregator studies, not X official]**
- Small accounts (<5k followers): 3–5/day helps build impression volume; mid-size (5k–50k): 1–3/day quality-first performs better. **[consensus claim: tweetarchivist.com, 2025/2026]**
- Mechanism for dilution is now confirmed in code: the **Author Diversity Scorer** attenuates repeated-author scores within a single feed serve, so multiple recent posts from the same account suppress each other in any one user's feed. **[sourced: github.com/xai-org/x-algorithm README, fetched 2026-06-12]**
- Post half-life is short (~15–30 min effective lifespan), so spacing posts across peak windows beats burst-posting. **[consensus claim: posteverywhere.ai, hashmeta.com, 2025]**
- Accounts whose posts go viral get a temporary boost on subsequent posts. **[sourced: Alex Finn breakdown of X Eng release via socialmediatoday.com, 2025-09-09 — secondary interpretation]**

## Spam / suppression triggers

Cumulative: penalties feed an **account reputation score**, so suppression persists across posts, not per-post. **[sourced: socialmediatoday.com/news/x-formerly-twitter-open-source-algorithm-ranking-factors/759702/, 2025-09-09]**

Account labels that throttle reach ("shadowban"): **low-quality posts, spam, toxicity, untrusted URL, NSFW, gore, repeatedly mentioning another @handle**. **[sourced: same, 2025-09-09]**

Specific triggers:
- "Offensive" text: **~80% reach reduction** (X does not define "offensive"). Offensive username also penalized. **[sourced: same, 2025-09-09]**
- Posting in ALL CAPS: penalized. **[sourced: same]**
- High predicted P(not_interested) / P(block) / P(mute) / P(report): direct negative score in Phoenix. **[sourced: xai-org/x-algorithm README, 2026]**
- The May 2026 **Grox** service runs dedicated **spam detection** and policy (PTOS) classifiers on content — repeated templates/formats and engagement-bait patterns are the canonical inputs to such classifiers. **[sourced that Grox spam detection exists: repo README; that repeated formats/engagement bait specifically trigger it: estimate/consensus claim]**
- Hashtag stuffing: >1–2 hashtags per post correlates with reduced reach; hashtags are largely vestigial in 2025-26. **[estimate/consensus claim — sproutsocial.com, socialbee.com 2026 guides; no official number]**
- Follow-churn (mass follow/unfollow) violates X platform manipulation policy and triggers account-level limits. **[consensus claim — X Rules; long-standing, not specific to 2025 algorithm release]**
- Duplicate/near-duplicate posts: filtered at serve time (DropDuplicatesFilter, RepostDeduplicationFilter) and old posts dropped by AgeFilter. **[sourced: repo README, 2026]**
- For a crypto bot specifically: reply-guy behavior that repeatedly @mentions the same handles is an explicitly listed suppression label — vary reply targets. **[sourced: socialmediatoday.com list above, 2025-09-09]**

## Premium effects

- Legacy repo multipliers: verified/Premium authors get **~4x** ranking boost in-network (to followers) and **~2x** out-of-network. **[estimate: from the 2023 twitter/the-algorithm release, repeated by postel.app and nerdtechy.com 2025-26 analyses; not re-confirmed as explicit constants in the 2026 Grok-based repo]**
- Buffer analysis of **18M+ posts**: Premium accounts get roughly **10x more median reach per post** than free accounts; Premium+ more than doubles Premium again (~1,550+ impressions/post median). **[sourced: buffer.com/resources/x-premium-review/ and influencermarketinghub.com report, 2025]**
- **Reply prioritization:** verified/Premium replies are ranked above non-verified replies in conversations; Premium+ gets the largest reply boost (X states "largest boost" tiering officially). **[sourced: help.x.com/en/using-x/x-premium, accessed 2026-06-12 via search]**
- Since ~March 2025, **link posts from free accounts show near-zero median engagement** — Premium partially shields the link penalty. **[sourced: buffer.com 18M-post dataset analysis, 2025; "near-zero" is their median finding, not an X statement]**
- Verification status is hydrated as a candidate feature in the 2026 pipeline (author info incl. verification status). **[sourced: repo README, 2026]**
- Bot implication: running Premium is close to mandatory for reach; Premium+ mainly matters if reply visibility is the growth strategy.

## Images vs text / threads / replies

**Images vs text:**
- Mid-2025 medians (Buffer dataset): **text posts ~0.9% median engagement for Premium accounts (highest), video ~0.7%+**. Plain text is NOT penalized — it slightly leads on engagement rate. **[sourced: buffer.com/resources/x-premium-review/, 2025]**
- Multi-image posts (2–4 images) often outperform single images because they increase dwell time. **[consensus claim: 2025-26 growth analyses (hipclip.ai, xbeast.io); no official weight]**
- For finance/crypto specifically: screenshots of data, simple charts, and annotated price screenshots are repeatedly cited as the best-performing image type because they stop scroll and add dwell — **no niche-specific quantitative study found; treat as consensus claim**. P(photo_expand) is an explicit positive prediction head in Phoenix, so images that invite a tap-to-expand (dense charts) have a real scoring path. **[head existence sourced: repo README, 2026]**
- Video gets an outsized boost, especially **>10s watch time**; P(video_view) is an explicit head. **[boost: Alex Finn/X Eng via socialmediatoday.com 2025-09-09; head: repo README]**

**Threads (2025–2026):**
- Hootsuite experiment: **single long-form posts out-reached threads**; later tweets in a thread see steep reach drop-off. **[sourced: blog.hootsuite.com/experiment-x-threads-vs-longform-posts/, 2025]**
- Metricool 2024-25 study: accounts now publish ~3x more long posts than threads (44.9 vs 15.3 avg). **[sourced: metricool.com/twitter-study/, data through 2025]**
- Threads still work when each tweet earns its own engagement (dwell + conversation clicks score), but the 2025-26 meta is: **long-form single post (or post + reply-chain) > classic numbered thread**. **[consensus claim]**

**Reply visibility mechanics (how replies rank under a post):**
- Replies under a post are ranked by predicted engagement relevance, with **verified/Premium replies preferred** and Premium+ at the top tier. **[sourced: help.x.com/en/using-x/x-premium; socialmediatoday 2025-09-09]**
- A reply that the **original author engages with** inherits the +75-class signal — replies that bait an author response rank dramatically higher and feed back into your account's distribution to that author's audience. **[sourced: X Eng weights, 2025-09-09]**
- Replies likely to draw "show less often"/reports get buried (negative heads). **[sourced: repo README, 2026]**
- DedupConversationFilter collapses multiple branches of the same conversation in For You — only the strongest branch of a reply chain surfaces. **[sourced: repo README, 2026]**
- Bot implication: replying early to large crypto accounts with substantive (non-templated) takes remains the highest-leverage reach tactic, but templated reply farming is exactly what Grox spam classifiers target.

## External links

- Legacy era (through mid-2025): external links suppressed; analyses put the penalty at **30–50% reach reduction** [estimate: claimed as "confirmed in open-source code" by posteverywhere.ai 2026 — the exact constant is disputed], with economic analyst Jesse Colombo estimating up to **~94%** reach loss in practice [estimate: Colombo's own A/B observations, via dkodetech.com / medium analyses, 2025].
- Buffer data: from **March 2025**, link posts from free accounts had **zero median engagement**. **[sourced: buffer.com 18M-post analysis, 2025]**
- **Oct 14, 2025:** X head of product **Nikita Bier announced removal of algorithmic penalties on posts with external links**, paired with testing an **in-app browser** that opens links inside X (keeping engagement UI visible). **[sourced: socialmediatoday.com/news/x-formerly-twitter-testing-links-in-app-link-post-penalties/803176/ and tomorrowspublisher.today, Oct 2025]**
- Post-change reality check: dwell-based ranking still structurally favors native content (a user who leaves to read a link generates less on-platform dwell unless the in-app browser counts it), so most 2026 growth analyses still recommend **link in the first reply, or link + substantial native summary in the post**. **[estimate/consensus claim, 2026 analyses]**
- Bot rule of thumb: never bare-link; if linking (e.g., to a dex/chart/article), lead with native content and put the URL in a reply unless data shows otherwise post-Oct-2025.

## Caveats

1. **The explicit weight table is legacy.** The +75/+13.5/+1/+0.5 numbers were restated by X Eng in Sep 2025 but the **Jan 2026 Phoenix system learns weights inside a Grok transformer** — only the action list and sign (positive/negative) are confirmed for 2026; magnitudes are inherited estimates.
2. **xAI updates the repo ~every 4 weeks** (pledged; last verified update May 15, 2026) — re-check github.com/xai-org/x-algorithm monthly. **[pledge: secondary sources, Jan 2026]**
3. Buffer/Metricool/Hootsuite numbers are **observational medians from scheduling-tool user bases**, biased toward marketer accounts — directionally useful, not ground truth for crypto-native accounts.
4. The Grok **sentiment/tone ranking** claim is widely repeated but comes from secondary analyses of the repo, not an explicit X statement — moderate confidence.
5. The **Oct 2025 link-penalty removal** was announced as a test; whether it fully shipped and persists in the Phoenix era is unverified — A/B test with the bot's own posts before trusting it.
6. No quantitative study specific to the **crypto/finance niche** was found; niche claims here are practitioner consensus.
7. The 2026 system is heavily **personalization-driven** (per-user engagement-history transformer): aggregate "weights" matter less than consistently triggering replies/dwell from a coherent audience cluster. Topic consistency likely matters more than any single format trick. [estimate/consensus]

### Primary sources
- https://github.com/xai-org/x-algorithm (fetched 2026-06-12; README dated May 15, 2026)
- https://www.socialmediatoday.com/news/x-formerly-twitter-open-source-algorithm-ranking-factors/759702/ (2025-09-09, citing x.com/XEng/status/1965226798460887127)
- https://buffer.com/resources/x-premium-review/ (2025, 18M+ post dataset)
- https://www.socialmediatoday.com/news/x-formerly-twitter-testing-links-in-app-link-post-penalties/803176/ (Oct 2025)
- https://help.x.com/en/using-x/x-premium (official, Premium reply prioritization)
- https://blog.hootsuite.com/experiment-x-threads-vs-longform-posts/ (2025)
- https://metricool.com/twitter-study/ (2024-25 data)
- Secondary 2026 analyses: posteverywhere.ai, postory.io, opentweet.io, basenor.com, tweetarchivist.com (treat as consensus, not authoritative)
