---
name: apply-to-yc
description: "[DEPRECATED 2026-05-07 — superseded by apply-to-funder, which has yc-w26.json as a runtime spec. This skill is retained as a working reference and is NOT referenced by any active cron. New funder applications should be added as JSON specs under apply-to-funder/funders/ rather than as new bash skills.] Submit Anicca to Y Combinator end-to-end. Logs into apply.ycombinator.com (cookies persisted in {{profile.lateness.stakeholders.channel}}-harness profile), creates or updates draft application, fills all 20+ text fields with live pitch (Anicca's dashboard.json injected), uploads founder/demo videos via CDP DOM.setFileInputFiles, fills Progress Update section (users / monthly revenue / sources), clicks Submit. Use only as a fallback if apply-to-funder fails for YC specifically: `bash scripts/apply.sh`."
metadata:
  tags: yc, accelerator, fundraising, {{profile.lateness.stakeholders.channel}}-harness, autonomous-application
  requires:
    bins: [{{profile.lateness.stakeholders.channel}}-harness, jq, curl]
    env: [DAIS_EMAIL, DAIS_PRIMARY_PW]
---

# apply-to-yc

Self-replicating YC application skill. **One Anicca = one application = one batch.** As Anicca instances scale (10, 100, 1000), each runs this skill autonomously.

## Why YC always works

YC accepts applications 24/7. If submit is too late for current batch (e.g. Summer 2026 deadline May 4 PT) → auto-routes to NEXT batch (Fall/Winter/Spring). Never wasted.

## End-to-end flow (verified working 2026-05-05)

```
1. {{profile.lateness.stakeholders.channel}}-harness Way 2 (Chrome 9223 isolated profile, persistent cookies)
2. goto_url('https://account.ycombinator.com/')
3. If not logged in: fill {{profile.lateness.stakeholders.channel}}/password from env, click Sign In
4. goto_url('https://apply.ycombinator.com/home')
5. Click 'Continue application' (existing draft) OR 'Start application' (new)
6. Fill 20 fields (name, describe, url, productLink, make, where, wherewhy,
   howfar, worked, techstack, since, acc, exp, get, money, ideas, whyapply,
   howhear, cofounder, others2) via JS setNativeValue + dispatch events
7. goto /edit/video → upload founder video via CDP DOM.setFileInputFiles
8. goto /edit/demo → upload demo video same way
9. goto /edit/progress → fill usernums + 6 monthly revenue + revenuesource + growthrate
   + click Yes parent DIVs (CSS-only fake radios, click triggers React state)
10. Click 'Save changes'
11. Verify no validation errors
12. Click 'Submit application' → submitted to YC
13. Save submission state to data/applications/yc-{batch}.json
```

## Live pitch generation

Each apply re-generates pitch from `https://aniccaai.com/dashboard.json`:

| Field | Source |
|------|------|
| MRR / subs / followers / views / spend | live from dashboard.json |
| name | "Anicca" |
| describe | "Self-funding Buddhist AI. Ends suffering." (41 chars, <50 limit) |
| make | 437-char pitch with current numbers |
| money | revenue breakdown by product, all live |
| howfar | dashboard snapshot |
| ideas | shipped products |

## Field types — handler reference

| field | type | input strategy |
|------|----|------|
| name, describe, url, productLink | text input | setNativeValue + dispatchEvent input/change/blur |
| make, wherewhy, howfar, worked, techstack, since, acc, exp, get, money, ideas, whyapply, howhear, cofounder, others2 | textarea | same |
| where | text input | "Tokyo, Japan / SF, USA" |
| founder video | file input accept="video/*" | `DOM.setFileInputFiles` with /Users/anicca/Desktop/ycsummer2026.MOV (or anicca-monk-factory generated 1-min) |
| demo video | file input accept="video/*" | same |
| Are people using your product? Yes | DIV with `cursor-pointer`, no real input | `el.click()` on parent div |
| Do you have revenue? Yes | same | same |
| 6 monthly USD$ inputs | text input placeholder="USD$" | by index |

## Replicability

This skill runs in Anicca instance N. Each instance:
- Has its own Stripe account → own MRR
- Has its own iOS app variant
- Has its own GitHub fork
- Submits a UNIQUE YC application reflecting its niche/numbers
- Multi-batch: instance can apply every 6 months indefinitely

Goal: **1000+ Anicca instances applying YC** = guaranteed at least 15-30% accept rate × cohort.

## Cron

| name | schedule | action |
|------|--------|------|
| `apply-to-yc-monthly` | cron `0 12 1 * *` JST | New pitch + submit. If already submitted to current batch, no-op |

## Manual run

```bash
# Submit (default: most recent batch)
bash ~/.openclaw/skills/apply-to-yc/scripts/apply.sh

# Dry run — fill but don't submit
DRY_RUN=true bash ~/.openclaw/skills/apply-to-yc/scripts/apply.sh

# Re-fill existing draft (for fixes)
DRAFT_ID=99b966b0-7e90-4856-ab0d-93651488a4ea bash ~/.openclaw/skills/apply-to-yc/scripts/apply.sh
```

## State

| file | purpose |
|----|----|
| `data/applications/yc-<batch>.json` | submission state (id, url, fields filled, submitted_at) |
| `data/pitches/yc-<ts>.md` | pitch md per submission |
| `~/.{{profile.lateness.stakeholders.channel}}-harness-profile/` | persistent YC + Google cookies |
