---
name: social-media-commander-soul
description: Soul-layer for social-media-commander. Tracks brand presence, content pipeline, funnel health, platform performance, and growth trajectory across sessions.
---

# Social Media Commander — Soul Context

## [WORKSPACE OWNER]
- Owner:        [soul.owner.name]
- Brand:        [brand/business name]
- Initialized:  YYYY-MM-DD
- Soul version: 1.0.0

---

## [PLATFORM PRESENCE]
<!-- One entry per active platform. Upsert. -->
<!-- Format: PLATFORM | FOLLOWERS | FOLLOWING | POSTS | AVG_ENGAGEMENT% | LAST_POST -->

---

## [CONTENT PIPELINE]
<!-- Current content pipeline summary. Update daily. -->
<!-- Format: ideas:N | drafts:N | review:N | approved:N | scheduled:N | published_this_week:N -->

---

## [ACTIVE CAMPAIGNS]
<!-- All running campaigns. Upsert by campaign-id. -->
<!-- Format: ID | GOAL | PLATFORM | START | END | POSTS_DONE | BUDGET_USED | STATUS -->

---

## [FUNNEL HEALTH]
<!-- Current funnel balance. Update weekly. -->
<!-- Format: AWARENESS:N% | CONSIDERATION:N% | CONVERSION:N% | RETENTION:N% | ADVOCACY:N% -->

---

## [TOP PERFORMING CONTENT]
<!-- Best content by engagement. Rolling 10. -->
<!-- Format: SLUG | PLATFORM | TYPE | ENGAGEMENT_RATE% | LESSON -->

---

## [BRAND VOICE VIOLATIONS]
<!-- Any brand voice issues detected. Rolling 10. -->
<!-- Format: YYYY-MM-DD | SLUG | RULE | SEVERITY | RESOLVED -->

---

## [COMPETITOR SUMMARY]
<!-- Tracked competitors. Upsert by brand. -->
<!-- Format: BRAND | PLATFORMS | EST_FOLLOWERS | POSTING_FREQ | LAST_REVIEWED -->

---

## [HASHTAG PERFORMANCE]
<!-- Top and bottom performing hashtag sets. -->
<!-- Format: SET_NAME | AVG_REACH | TREND | LAST_REVIEWED -->

---

## [ACTIVE A/B TESTS]
<!-- Running tests. Remove when concluded. -->
<!-- Format: TEST_ID | SLUG_A | SLUG_B | PLATFORM | STARTED | METRIC | STATUS -->

---

## [GROWTH METRICS]
<!-- Monthly snapshots. Append-only. -->
<!-- Format: MONTH | PLATFORM | FOLLOWERS_START | FOLLOWERS_END | GROWTH% | TOP_POST -->

---

## [CRISIS LOG]
<!-- Any crisis events. Append-only. -->
<!-- Format: YYYY-MM-DD | PLATFORM | SUMMARY | STATUS | RESOLVED_AT -->

---

## [CONTENT CALENDAR STATUS]
<!-- How far ahead is the calendar. Update weekly. -->
<!-- Format: PLATFORM | APPROVED_AHEAD_DAYS | SCHEDULED_AHEAD_DAYS | LAST_UPDATED -->

---

## [SESSION LOG]
<!-- Append-only. -->
<!-- Format: YYYY-MM-DD | ideas:N | drafts:N | published:N | reviews:N | analytics:N -->

---

## Write Protocol

| Section | Trigger | Operation |
|---|---|---|
| [PLATFORM PRESENCE] | Post published / weekly review | Upsert by platform |
| [CONTENT PIPELINE] | Any content state change | Full refresh |
| [ACTIVE CAMPAIGNS] | Campaign created/updated | Upsert by ID |
| [FUNNEL HEALTH] | Weekly review | Update percentages |
| [TOP PERFORMING CONTENT] | Post hits top 20% | Append; drop oldest >10 |
| [BRAND VOICE VIOLATIONS] | Violation detected | Append; drop oldest >10 |
| [COMPETITOR SUMMARY] | Competitor review | Upsert by brand |
| [HASHTAG PERFORMANCE] | After every 10 posts | Upsert by set |
| [ACTIVE A/B TESTS] | Test created/concluded | Upsert; remove when done |
| [GROWTH METRICS] | Monthly | Append |
| [CRISIS LOG] | Crisis detected/resolved | Append-only |
| [CONTENT CALENDAR STATUS] | Weekly | Update |
| [SESSION LOG] | Session end | Append |
