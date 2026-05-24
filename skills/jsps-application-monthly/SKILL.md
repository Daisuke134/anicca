---
name: jsps-application-monthly
description: Monthly autonomous JSPS / 学振 / 科研費 / JST application loop for Anicca's {{profile.education.institution}} research track. Reads naist-funds (which knows about JSPS DC1/DC2, JST PRESTO/CREST, and live-scrapes JSPS/JST/JFUND every Monday), filters for grants whose deadline is within the next 60 days, picks the best match against the research-topic config (AI economic agency, basic-income distribution, AI mindfulness, Oogiri-bench, AI responsibility), and invokes `apply-to-funder` against the matching `funders/<id>.json` spec. If no spec exists for the matched grant, the skill aborts with a missing-spec warning that lists the exact funder.json filename to create. Companion to `accelerator-application-monthly` (US fundraise side); this is the academic side. Use when triggered by the `jsps-application-monthly` cron at `0 13 1 * *` Asia/Tokyo, or manually as `MODE=run bash scripts/run.sh`.
metadata:
  tags: jsps, kakenhi, 学振, 科研費, jst, naist, academic-funding, apply-to-funder
  requires:
    bins: [jq, curl]
    env: [DAIS_EMAIL]
  invariants:
    - Never submits in DRY_RUN=true.
    - Aborts with 🚨 if no funder spec exists for the matched grant — does not guess form structure.
    - Aborts on institutional 2FA (e-Rad) — JSPS submissions cannot self-auth.
    - Picks at most ONE grant per run — no parallel applications in V1.
---

# jsps-application-monthly

Monthly cron that picks one JSPS / JST / 学振 / 科研費 grant from the {{profile.education.institution}} funds pipeline and submits via `apply-to-funder`.

## Why a separate skill (not just another funder spec)

`apply-to-funder` is the runtime — given a funder id, it submits. This skill is the *picker*: it reads the `naist-funds` candidate pool, filters by deadline + topic match, then hands the chosen funder id to `apply-to-funder`. Separating picker from runtime keeps both reusable.

## Candidate pool

V1 reads three sources in priority order:

1. `~/.openclaw/skills/naist-funds/data/guides.json` — hardcoded JSPS DC1, DC2, JST PRESTO, JST CREST. Stable.
2. `~/.openclaw/state/funder-portfolio.json` — funders tagged `jsps`, `kakenhi`, `学振`, `科研費`, `jst`, `presto`, `さきがけ`, `create`.
3. (Future V2) live `naist-funds` scrape output — currently `naist-funds` only persists notification-dedup IDs, not grant content. V2 would teach `naist-funds` to also write a `data/calls.json` with the full grant list.

## Matching logic

```
candidate := guides ∪ portfolio_jsps_funders
filter by:    deadline_within_next_60_days  (text-match if deadline is "毎年5月頃")
              OR  always-eligible (no specific deadline known)
score by:     topic_match_score(grant.summary, RESEARCH_TOPICS)
              + verified_bonus_if_funder_spec_exists(grant.id → funders/<id>.json)
pick:         argmax(score)
```

`RESEARCH_TOPICS` lives in this skill's `data/research-topics.json` (created on first run if missing, default list below).

## Default research topics

```json
[
  "AI economic agency / AI as economic entity",
  "GDP attribution from AI activity",
  "Oogiri-bench (Japanese humor benchmark)",
  "AI responsibility and accountability",
  "AI mindfulness / contemplative computing",
  "Autonomous algorithmic basic-income distribution",
  "Public-ledger AI philanthropy"
]
```

## Modes

```bash
# Live: pick + submit (DRY_RUN-respecting, hands off to apply-to-funder).
MODE=run bash scripts/run.sh

# Dry: print the picked candidate + plan, never click submit.
MODE=run DRY_RUN=true bash scripts/run.sh

# Force a specific funder (bypass picker — useful for cron debugging).
MODE=run FORCE_FUNDER=jsps-grant-in-aid bash scripts/run.sh
```

## When no funder spec exists

If the picker chose `jst-presto` but there is no `~/.openclaw/skills/apply-to-funder/funders/jst-presto.json`, the skill prints:

```
🚨 funder spec missing for 'jst-presto' (matched grant: JST さきがけ).
   Create ~/.openclaw/skills/apply-to-funder/funders/jst-presto.json
   See yc-w26.json for the schema.
   Queue source: ~/.openclaw/skills/jsps-application-monthly/data/missing-specs.log
```

…appends to `data/missing-specs.log`, and exits non-zero. The cron's Slack message therefore surfaces this as a TODO for the operator. (V2 would auto-generate a spec from the grant announcement page.)

## Cron

| name | schedule | tz | mode | dry_run |
|---|---|---|---|---|
| `jsps-application-monthly` | `0 13 1 * *` | Asia/Tokyo | submit | true (initially) |

The cron payload:
1. Reads this SKILL.md.
2. Runs `bash ~/.openclaw/skills/jsps-application-monthly/scripts/run.sh` (with `MODE=run` and `DRY_RUN=true` initially via `JSPS_DRY_RUN=true`).
3. For any K-Dense draft request the picker queues, the cron's agentTurn invokes `scientific-writing`, `literature-review`, and `peer-review` per their SKILL.md.
4. Hands off to `apply-to-funder` for the actual fill.
5. Slack-announces via `delivery: { mode: announce, channel: slack, to: "channel:{{profile.channels.reportChannel}}" }`.

## State

| file | purpose |
|---|---|
| `data/research-topics.json` | topics for matching |
| `data/last-pick.json` | last picked funder id + ts (avoids re-picking same one twice in a row) |
| `data/missing-specs.log` | append-only list of grants matched but lacking specs |

## Companion

This skill is a sibling of `accelerator-application-monthly` (US side). Both invoke the same `apply-to-funder` runtime. Both write to the same `data/applications/` log.
