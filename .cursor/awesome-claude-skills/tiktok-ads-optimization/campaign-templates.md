# TikTok Campaign Templates for Anicca

## Template 1: Japanese Market - Click Discovery

Use when: Starting fresh with limited budget, need to build pixel data.

```
Campaign Settings:
- Name: anicca-jp-click-v[XX]
- Advertising Objective: App Promotion
- App: Anicca
- Optimization Location: App Install (but optimize for Click in Ad Group)
- Campaign Budget: Not set (use Ad Group budget)

Ad Group Settings:
- Name: jp-broad-click-[date]
- Promotion Type: App Install
- Optimization Goal: Click
- Bidding Strategy: Maximum Delivery (Lowest Cost)
- Budget: 6,000 JPY/day
- Schedule: Run continuously starting today
- Targeting:
  - Location: Japan
  - Age: 18-44
  - Gender: All
  - Languages: Japanese
  - Targeting Expansion: ON (Automatic)
  - Interests/Behaviors: None (Broad)
- Placements: TikTok only (uncheck Pangle, News Feed apps)
- Creative Delivery: Optimize per creative (not evenly)
```

## Template 2: Japanese Market - Install Optimization

Use when: After Phase 1 (Click) has generated data, ready to optimize for installs.

```
Campaign Settings:
- Name: anicca-jp-install-v[XX]
- Advertising Objective: App Promotion
- App: Anicca
- Campaign Budget: 8,000-10,000 JPY/day (CBO)

Ad Group Settings:
- Name: jp-broad-install-[date]
- Promotion Type: App Install
- Optimization Goal: App Install
- Bidding Strategy: Cost Cap
- Cost Cap: [1.2× your CPC from Phase 1] or 500-800 JPY
- Budget: Campaign-level (CBO)
- Schedule: Run continuously
- Targeting: Same as Template 1
- Placements: TikTok only
```

## Template 3: English Market - US/UK/CA/AU Combined

Use when: Testing English-speaking markets with unified budget.

```
Campaign Settings:
- Name: anicca-en-click-v[XX]
- Advertising Objective: App Promotion
- Campaign Budget: Not set (use Ad Group budget)

Ad Group Settings:
- Name: en-broad-click-[date]
- Optimization Goal: Click (Phase 1) or Install (Phase 2)
- Bidding Strategy: Maximum Delivery
- Budget: 8,000+ JPY/day (minimum for English markets)
- Targeting:
  - Location: United States, United Kingdom, Canada, Australia
  - Age: 18-44
  - Gender: All
  - Languages: English
  - Targeting Expansion: ON
  - Interests/Behaviors: None (Broad)
- Placements: TikTok only
```

## Creative Naming Convention

```
[app]-[market]-[concept]-[variant]-[date]

Examples:
- anicca-jp-hook1-cta1-0128
- anicca-jp-hook1-cta2-0128
- anicca-en-testimonial-v1-0128
```

## Weekly Rotation Schedule

| Week | Action |
|------|--------|
| Week 1 | Launch with 3-5 creatives |
| Week 2 | Kill losers (Hook < 20%), add 2 new variations |
| Week 3 | Promote winners to Install campaign |
| Week 4 | Major refresh: 2-3 new concepts |

## Budget Scaling Path

| Milestone | Budget | Action |
|-----------|--------|--------|
| CPI < 600 JPY achieved | Current | Continue testing |
| CPI stable for 7 days | +50% | Increase budget |
| CPI < 400 JPY | +100% | Aggressive scaling |
| CPI spikes > 800 JPY | -30% | Reduce, refresh creatives |

## Anicca-Specific Targeting Notes

Target Persona: 25-35 year olds struggling with habits for 6-7 years

Recommended settings:
- Age: 18-44 (let algorithm narrow down)
- Gender: All (data shows women respond more, but don't restrict)
- Interests: None (Broad) - let algorithm find your audience
- Exclude: None initially

If budget allows ($100+/day), can test:
- Interest: Self Improvement, Mindfulness, Mental Health
- But always have a Broad control group for comparison
