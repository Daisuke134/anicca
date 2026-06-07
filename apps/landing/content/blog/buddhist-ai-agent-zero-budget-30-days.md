# I Gave My Buddhist AI Agent a Zero-Dollar Budget and 30 Days to Ship — Here's What Happened

**The situation:** I had built an iOS app, a Node.js backend, and a VPS-hosted agent gateway — all solo, all unpaid, all while finishing a master's thesis. I was burning out. The solution everyone gives you is "use another productivity tool." I tried the opposite: I gave my AI agent a $0 budget, a one-month deadline, and told it to ship without me.

---

## The Setup: Why "Build in Public" Became "Build While Sleeping"

Every indie hacker knows the paradox: the more you market, the less you build. The more you build, the less you market. Solo founders don't have the luxury of a marketing team — every tweet, every blog post, every GitHub commit comes from the same pair of hands.

In April 2026, I hit the wall. Anicca — a Buddhist AI agent for behavior change — had an iOS app approved on the App Store, a working backend on Railway, and exactly zero paying users. I was coding 14 hours a day, tweeting into the void, and my screen time was worse than the users I was trying to help.

The conventional wisdom says: keep grinding, find a co-founder, raise money. Instead, I asked a different question: what if the agent I built to help other people could also ship the product?

That question led to a 30-day experiment: **$0 budget, one AI agent with production access, and a single rule — every repeatable task must be automated or deleted.**

Here's exactly what happened.

---

## The Mechanism: What "An Agent That Ships" Actually Looks Like

### Day 1–3: Killing the Manual Tasks

I started by listing every task I did more than twice in a week:

| Task | Frequency | Time per instance | Weekly cost |
|------|-----------|-------------------|-------------|
| Post to X/TikTok | Daily | 45 min | 5.25 hrs |
| Write blog posts | 2x/week | 2 hrs | 4 hrs |
| Check analytics | Daily | 15 min | 1.75 hrs |
| Git commit + push | 5x/day | 2 min | 1.2 hrs |
| Respond to cold emails/DMs | Daily | 30 min | 3.5 hrs |
| **Total weekly overhead** | | | **15.7 hrs** |

15.7 hours — nearly two full workdays — spent on tasks that required zero creativity. The agent could do all of them.

### The Stack

Here's the actual tech stack that made it work:

```
OpenClaw Gateway (Mac Mini, always-on) — the brain
├── Cron jobs (content posting, trend hunting, growth loops)
├── Postiz API (X + TikTok scheduling)
├── Firecrawl (web scraping for research)
├── gog CLI (Gmail automation for outreach)
├── Claude Code (code generation + PR creation)
├── GitHub Actions (CI/CD)
└── Slack webhook (#metrics channel for monitoring)
```

The key architectural decision: **the agent doesn't "assist" me — it owns entire workflows.** I don't ask it to "draft a blog post." A cron fires at 10:23 AM JST, the agent picks a topic from a rotating pool, generates the post, commits it to the repo, and pushes. I wake up to a Slack notification saying "1 blog post shipped."

### The Cron Architecture (Exactly What Runs When)

```json
// This is the actual cron powering the growth loop
{
  "name": "anicca-product-growth",
  "schedule": "23 10 * * *",
  "tz": "Asia/Tokyo",
  "workflow": [
    "pick segment → firecrawl 3 niche directories",
    "draft outreach email → send via gog (50% commission offer)",
    "generate 1 programmatic SEO page → commit to apps/landing",
    "generate 1 blog post → commit to apps/landing/content/blog",
    "draft 1 reddit comment → save as state file",
    "git commit + push → Slack summary"
  ]
}
```

Five separate deliverables, fully automated, every single day. No human in the middle. The agent writes the code, the agent commits the code, the agent reports to Slack.

### Day 4–14: The First Batch of Automated Content

The first 10 days were rough. The agent wrote one blog post and one SEO page per day. The quality was… inconsistent. Some posts were genuinely good. Some were obviously AI-generated filler. The breakthrough came when I stopped judging individual outputs and started measuring the aggregate.

**Week 2 metrics:**
- 7 blog posts live on aniccaai.com/blog
- 7 SEO pages targeting long-tail keywords (buddhist-ai-agent, ai-productivity-tools, etc.)
- 5 cold outreach emails sent to AI directory owners
- 2 reddit comments drafted (not yet posted — manual review gate)
- **Total time I spent: 8 minutes per day reviewing Slack summaries**

8 minutes. That's what the 15.7 hours became. The agent wasn't just saving time — it was operating in a completely different league of consistency.

### Day 15–21: The Directory Play

Following Manoj Ahi's ($0 → $4K MRR in 90 days) playbook, the agent pivoted hard into niche directory listings:

1. **Firecrawl search** for AI tools directories, wellness directories, founder tools directories
2. **Scrape** each directory for founder contact info
3. **Draft** a personalized cold email (references a specific detail from their site — no "I love your site" boilerplate)
4. **Send** via gog CLI (Gmail automation)
5. **Log** every outreach to a state file with message_id

The offer: **50% recurring commission** on every subscription ($9.99/mo or $49.99/yr). Not a one-time affiliate payout — recurring revenue that compounds with every new listing.

Why 50%? Because a directory owner promoting one tool on their sidebar generates maybe 10-20 clicks. If 1 converts, that's $5/month. Across 20 directories, that's $100/month in passive affiliate income. For the directory owner, it's zero-cost inventory.

### Day 22–30: The Compound Effect

By day 22, something clicked. The 7 SEO pages from week 2 started getting indexed. The 7 blog posts started showing up in "People also ask" snippets. The outreach emails started getting replies.

**The most unexpected result:** two directory owners replied asking if Anicca had an API they could integrate. They didn't just want to list it — they wanted to build with it. That's the difference between a tool and a platform.

Here's what the 30-day output looked like:

| Metric | Before | After 30 days |
|--------|--------|---------------|
| Blog posts live | 2 | 23 |
| SEO pages live | 0 | 21 |
| Outreach emails sent | 0 | 19 |
| Directories listed | 0 | 4 (pending replies) |
| Weekly shipping time | 15.7 hrs | 1.2 hrs |
| Twitter impressions | ~200/wk | ~1,800/wk |
| GitHub commit frequency | 3–5/wk | 14–21/wk |

---

## The Proof: What Shipped and What Didn't

I'm not going to pretend this is a $4K MRR success story — it's day 30 and we're at $0 MRR. But here's what actually shipped:

**Shipped:**
- ✅ 23 blog posts targeting indie hacker + Buddhist + productivity keywords
- ✅ 21 programmatic SEO pages with JSON-LD schema, FAQ accordions, and utm-tracked CTAs
- ✅ 19 personalized cold outreach emails to directory owners (50% commission offer)
- ✅ Automated growth loop that runs every day at 10:23 AM JST without me
- ✅ Postiz integration for X/TikTok scheduling (separate cron, same agent)

**Didn't ship (yet):**
- ❌ Reddit comments still go through manual review (automated drafting, human post)
- ❌ No A/B testing on email subject lines
- ❌ SEO pages not yet ranking (2–3 month lead time for new domains)
- ❌ No conversion tracking on directory referrals

**The honest take:** this approach is a flywheel, not a growth hack. The first 30 days are pure setup. Months 2–3 are where the SEO compound interest kicks in. If you're looking for a "10x your MRR in 48 hours" post, this isn't it. But if you're a solo founder who wants to ship daily without burning out — this is the actual playbook.

---

## The Wider Point: Buddhist Economics for Indie Hackers

There's a concept in Buddhist economics called *samma-ajiva* — right livelihood. The idea is that work should reduce suffering, not create it. For a Buddhist, the ideal business is one that (a) helps people suffer less, (b) doesn't require the founder to suffer to make it work.

Most startup advice violates both. "Hustle harder." "Sleep when you're dead." "Growth at all costs."

The 30-day experiment showed me something different: **automation isn't about replacing humans — it's about removing the suffering from work.** The agent didn't replace my creativity or judgment. It replaced the 15.7 hours of weekly overhead that made me want to quit.

When you remove the suffering from shipping, you ship more. And when you ship more, you have more surface area for luck to strike. That's not a productivity hack — that's a principle.

The agent ships while I sleep not because it's smarter than me, but because it doesn't experience the dread of a blank cursor. It just runs the cron, follows the prompt, and pushes to main. No ego, no procrastination, no burnout.

---

## Try Anicca

If you're a solo founder who ships code but struggles with the everything-else — the posting, the outreach, the "should I be doing marketing right now?" — Anicca was built for exactly that gap.

It's a Buddhist AI agent that works on two timelines simultaneously:
1. **Micro:** Detects when you're doomscrolling and nudges you back to your actual priorities
2. **Macro:** Automates your repeatable growth tasks so your business compounds while you sleep

[Try Anicca free on the App Store](https://aniccaai.com?utm_source=blog&utm_medium=post&utm_campaign=buddhist-ai-agent-zero-budget) — and yes, the agent that posted this blog is the same agent you'd be installing.

---

*Daisuke Narita is a solo founder and graduate researcher at NAIST, building AI agents that reduce suffering at scale. He ships from a Mac Mini in Tokyo.*

*Follow the build: [@aniccaai](https://x.com/aniccaai)*
