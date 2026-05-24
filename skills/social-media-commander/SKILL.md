---
name: social-media-commander
description: Full-stack social media management skill. Covers content creation, review, scheduling, publishing, funnel management, analytics, audience insights, competitor tracking, engagement, brand voice, A/B testing, campaign management, and growth strategy. A to Z.
version: 1.0.0
metadata: {"openclaw": {"emoji": "📱", "requires": {"bins": []}}}
---

# Social Media Commander

## Purpose

Agent manages the workspace owner's entire social media presence.
From raw idea → polished content → scheduled post → published → analysed → improved.
Every platform. Every funnel {{profile.lateness.stakeholders.senderType}}. Every format.

---

## Supported Platforms

| Platform | Content Types | Primary Use |
|---|---|---|
| `instagram` | Feed post, Reel, Story, Carousel, Guide | Visual brand, engagement |
| `twitter-x` | Tweet, Thread, Space | Thought leadership, real-time |
| `linkedin` | Post, Article, Newsletter, Poll, Document | B2B, professional authority |
| `youtube` | Long-form, Shorts, Community post | Deep content, SEO |
| `threads` | Text post, Image post | Casual, conversation |
| `whatsapp-channel` | Broadcast message, Poll | Direct audience |
| `telegram` | Post, Poll, File | Community, power users |

---

## Content States

| State | Meaning |
|---|---|
| `idea` | Raw concept, not yet developed |
| `draft` | Being written/designed |
| `review` | Submitted for review |
| `approved` | Ready to schedule |
| `scheduled` | Queued with date/time |
| `published` | Live on platform |
| `archived` | No longer active |
| `rejected` | Not approved — reason logged |

---

## Content Types

| Type | Description |
|---|---|
| `educational` | Teaches something — tips, how-tos, explainers |
| `entertaining` | Humor, relatable, storytelling |
| `inspirational` | Motivational, aspirational, transformation |
| `promotional` | Product/service, offer, CTA |
| `engagement` | Questions, polls, challenges, UGC prompts |
| `social-proof` | Testimonials, case studies, results |
| `behind-scenes` | Process, culture, personal |
| `news` | Industry updates, hot takes, trends |
| `repurposed` | Existing content adapted for platform |

---

## Funnel Stages

| Stage | Goal | Content Focus |
|---|---|---|
| `awareness` | New people discover you | Educational, entertaining, viral |
| `consideration` | Followers evaluate your value | Social proof, deep value, FAQs |
| `conversion` | Audience becomes customers | Promotional, offers, urgency |
| `retention` | Customers stay and return | Behind-scenes, loyalty, community |
| `advocacy` | Customers become promoters | UGC, referral, ambassador |

Every piece of content must be tagged with a funnel {{profile.lateness.stakeholders.senderType}}.

---

## Content Pillars

Defined in `brand/guidelines/pillars.md`.
Every post must align with at least one pillar.
Default pillars (customizable):
1. Education / Value
2. Authority / Expertise
3. Personality / Story
4. Community / Engagement
5. Promotion / Conversion

---

## The Content Engine (idea → published)

```
IDEA captured
    ↓
DEVELOP: format, platform, angle, hook
    ↓
DRAFT: write copy, define visual, add CTA
    ↓
REVIEW: brand voice check, rule compliance, funnel fit
    ↓
APPROVED → SCHEDULE (date + time + platform)
    ↓
PUBLISH (manual or via integration)
    ↓
TRACK: engagement metrics at 1h / 24h / 7d
    ↓
ANALYSE: what worked, what didn't
    ↓
IMPROVE: update templates, adjust strategy
```

---

## Slug Format

Content: `YYYY-MM-DD-<platform>-<type>-<3-word-desc>`
Campaign: `<name>-<YYYY-MM>`
Competitor: `<brand-name>-analysis`

---

## Folder Structure

```
social-media-commander/
  platforms/<platform>/
    profile.md         ← account info, bio, links, stats
    strategy.md        ← platform-specific strategy
    best-times.md      ← optimal posting times
    performance.md     ← running metrics log

  content/
    drafts/            ← state: idea / draft
      <slug>/content.md
    scheduled/         ← state: scheduled
    published/         ← state: published (with metrics)
    archived/
    templates/         ← reusable content templates
    assets-index.md    ← index of visual assets (no files stored)

  calendar/
    YYYY-MM.md         ← monthly content calendar

  funnels/
    <{{profile.lateness.stakeholders.senderType}}>/
      strategy.md      ← how we approach this {{profile.lateness.stakeholders.senderType}}
      content-index.md ← all content at this {{profile.lateness.stakeholders.senderType}}

  campaigns/
    active/<campaign-id>/
      manifest.md      ← goal, budget, timeline, content list
      performance.md   ← real-time results
    completed/
    templates/

  analytics/
    daily/YYYY-MM-DD.md
    weekly/YYYY-WNN.md
    monthly/YYYY-MM.md
    reports/           ← deep analysis reports

  audience/
    segments/          ← audience segment definitions
    personas/          ← buyer personas
    competitors/       ← competitor analysis entries

  engagement/
    comments/          ← comments requiring response
    dms/               ← DMs to track
    mentions/          ← brand mentions
    saved/             ← notable engagement to reference

  brand/
    voice/guidelines.md     ← tone, language, personality
    guidelines/
      pillars.md       ← content pillars
      dos-donts.md     ← brand-level rules
      visual.md        ← visual identity guidance
    hashtags/
      master.md        ← all hashtags by category
      performance.md   ← which hashtags work
    hooks/
      master.md        ← proven hook formulas
      performance.md   ← which hooks perform

  hooks/               ← skill execution hooks
  workflows/           ← process definitions
  rules/do/ rules/dont/ rules/platform-specific/
  reviews/pending/ approved/ rejected/
  memory/schema.json index.json
  crons/active/ completed/
  templates/
  CONTENT_LOG.md       ← append-only publish log
  ANALYTICS_SUMMARY.md ← running performance snapshot
  GROWTH_JOURNAL.md    ← weekly growth reflections
  STATS.md
  SOUL.md
  AGENT.md
```

---

## A/B Testing

When testing content variants:
1. Create two entries with same concept, different angle/hook/format
2. Tag both: `ab_test: true`, `ab_group: A` / `ab_group: B`
3. After 7 days: compare metrics, declare winner
4. Log winner in `brand/hooks/performance.md` and templates

---

## Repurposing Engine

Every published piece of long-form content should be repurposed:

| Source | Repurpose into |
|---|---|
| YouTube video | Shorts, LinkedIn post, Twitter thread, Instagram carousel |
| Blog/article | LinkedIn article, Twitter thread, Instagram carousel, Reels script |
| Podcast | Audiogram, quote cards, Twitter thread |
| Twitter thread | LinkedIn post, Instagram carousel |

Tag repurposed content: `repurposed_from: <original-slug>`

---

## Crisis Protocol

If negative viral content / PR issue:
1. Capture in `engagement/mentions/` with tag `crisis: true`
2. Immediate advisory to owner
3. Pause all scheduled promotional content
4. Draft response per `brand/voice/guidelines.md`
5. Owner approves before any response goes live
6. Log in `CONTENT_LOG.md` with `crisis: resolved`

---

## Competitor Tracking

For each tracked competitor in `audience/competitors/`:
- Platform presence and frequency
- Content types they use
- Engagement rates (estimated)
- What's working for them
- Gaps we can exploit
- Monthly update schedule
