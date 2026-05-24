---
name: apply-to-funder
description: Generalized funder-application engine. Submits Anicca to any rolling-deadline accelerator, grant, foundation, or prize competition by reading a JSON form-spec at funders/<id>.json and driving {{profile.lateness.stakeholders.channel}}-harness through it. Replaces apply-to-yc (now deprecated). Use when triggered by `accelerator-application-monthly` cron, `jsps-application-monthly` cron, or manually with `MODE=submit bash scripts/run.sh --funder <id>`. Works for YC, Anthropic, a16z, JSPS 科研費, JST CREST/さきがけ, and any new funder with a JSON spec added under funders/.
metadata:
  tags: funding, accelerator, grant, jsps, kakenhi, {{profile.lateness.stakeholders.channel}}-harness, autonomous-application, runtime-driven
  requires:
    bins: [{{profile.lateness.stakeholders.channel}}-harness, jq, curl]
    env: [DAIS_EMAIL, DAIS_PRIMARY_PW]
  invariants:
    - Never submits in DRY_RUN=true mode.
    - CAPTCHA → abort with explanation.
    - File inputs missing on disk → abort.
    - Institutional 2FA (e-Rad) → abort with human-required message.
    - K-Dense draft fields still pending → abort, list pending fields.
    - Funder spec absent → abort with "please add funders/<id>.json first".
---

# apply-to-funder

Runtime-driven funder-application engine. Each funder is a JSON file under `funders/`; the skill executes against the spec.

## Why generic

`apply-to-yc` worked but locked us to YC. The funder universe is wider — Anthropic Builder Grants, a16z START, JSPS 科研費 (kakenhi), JST さきがけ, Soma, AI Grant, EF, SPC. Most have similar form structures: text fields + textareas + sometimes a video upload + Submit. A JSON spec captures the differences in 50–200 lines instead of duplicating 300 lines of bash per funder.

## Mode dispatch

```bash
# Draft only — fetch live numbers, build payload, queue K-Dense draft requests.
MODE=prepare bash scripts/run.sh --funder yc-w26

# Prepare + drive {{profile.lateness.stakeholders.channel}}. DRY_RUN prints plan, doesn't click submit.
MODE=submit DRY_RUN=true bash scripts/run.sh --funder yc-w26

# Live submit (only when verified=true and all guardrails pass).
MODE=submit bash scripts/run.sh --funder yc-w26
```

## Funder-spec schema (`funders/<id>.json`)

| key | required | example | notes |
|---|---|---|---|
| `id` | ✓ | `yc-w26` | stable funder id |
| `name` | ✓ | "Y Combinator W26 Batch" | human-readable |
| `url` | ✓ | `https://apply.ycombinator.com/home` | entry URL |
| `verified` | ✓ | `true` | must be `true` for non-DRY live submit |
| `funder_type` | ✓ | `accelerator` \| `grant` \| `foundation` \| `prize` | |
| `currency` | ✓ | `USD` \| `JPY` \| `EUR` | |
| `amount_range` | ✓ | `{min, max}` | for guardrails |
| `deadline_kind` | ✓ | `rolling` \| `quarterly` \| `annual` \| `biannual` | |
| `next_deadline` | | `"2026-09-15"` | null for rolling |
| `captcha` | ✓ | `null` \| `"recaptcha-v2"` \| `"turnstile"` | non-null → autonomous abort |
| `auth.kind` | ✓ | `none` \| `session_cookie` \| `oauth` \| `institutional_2fa` | `institutional_2fa` w/ `blocking:true` → abort |
| `pages[]` | ✓ | array | each page = a separate URL |
| `pages[].fields[]` | ✓ | array | every form field |
| `submit` | ✓ | `{page, button_text, success_url_pattern}` | |

### Field types

| `type` | how it's filled |
|---|---|
| `text` | `setNativeValue` + dispatch input/change/blur |
| `textarea` | same |
| `select` | `el.value = X; dispatch change` |
| `file` | CDP `DOM.setFileInputFiles` (via `{{profile.lateness.stakeholders.channel}}-harness.set_file_input`) |
| `indexed_inputs` | array of values into `querySelectorAll(selector)[i]` in document order |
| `fake_radio_div` | YC-style: clickable `<div class=cursor-pointer>` containing the option text |

### `value_source`

| prefix | meaning |
|---|---|
| `config.<key>` | value from the spec's own `config` object (static answer) |
| `env:<NAME>` | value from `~/.openclaw/.env` |
| `literal:<value>` | embedded literal |
| `live:pitch.<key>` | computed pitch fragment from `prepare.sh` (uses dashboard.json) |
| `live:progress.<key>` | progress-section fragments (MRR, monthly revenue array, etc.) |
| `skill:<skill-name>` (with `kdense_invoke: true`) | a K-Dense skill must produce this section. `prepare.sh` writes a draft-request to `data/drafts/<funder>/<ts>.kdense.md`; the parent agentTurn reads it, invokes the named skill (`scientific-writing`, `literature-review`, `peer-review`), and writes the result back into the payload. |

## Three guardrails (autonomous-abort)

The skill aborts and emits 🚨 when any of these are true:

1. **CAPTCHA present** (`spec.captcha != null`). Switch to `MODE=prepare` and submit manually.
2. **File input missing on disk.** E.g. `~/Desktop/ycsummer2026.MOV` not present → don't try to upload.
3. **Dollar amount drifted ≥50 % since selection.** Funder spec includes `amount_range`; if the funder's announced amount has changed materially, re-verify.
4. **Institutional 2FA** (e.g. e-Rad). Hand off to human.
5. **K-Dense placeholders still pending** at submit time → fail loud.

## Invocation of K-Dense skills

`prepare.sh` emits a markdown draft-request file at `data/drafts/<funder>/<ts>.kdense.md` listing every field marked `kdense_invoke: true`. In an `agentTurn` context the parent agent reads this file, then for each entry:

> Read `~/.openclaw/skills/<skill>/SKILL.md` and follow it. Produce the section described. Write to `data/drafts/<funder>/<field>.md`. Then merge into the payload JSON (jq instructions are in the `.kdense.md` file).

This means: there is no shell-only invocation of K-Dense skills. They are agent-invoked. `prepare.sh` is the queue; the agent is the worker.

## DRY_RUN

`DRY_RUN=true` makes both `prepare` and `submit`:

- Use a stub `dashboard.json` (avoids hitting prod when smoke-testing)
- Print the field plan instead of driving the {{profile.lateness.stakeholders.channel}}
- Never click any Submit button
- Persist a `..._latest.json` with `status: "dry_run_planned"`

## Slack delivery (cron)

Cron payload uses `delivery: { mode: announce, channel: slack, to: "channel:{{profile.channels.reportChannel}}" }`. The Slack message format the cron emits:

```
🎯 funder=<id>  status=<submitted|dry_run_planned|aborted:<reason>>  draft=<id?>  amount=<currency $>
```

## State

| file | purpose |
|---|---|
| `funders/<id>.json` | the spec |
| `data/drafts/<id>/<ts>.payload.json` | resolved field map |
| `data/drafts/<id>/<ts>.kdense.md` | K-Dense draft requests |
| `data/applications/<id>-latest.json` | latest submission state |
| `~/.openclaw/state/funder-portfolio.json` | global index of funders, priorities, guardrails |
| `~/.{{profile.lateness.stakeholders.channel}}-harness-profile/` | persistent cookies |

## Adding a new funder

1. Copy `funders/yc-w26.json` → `funders/<new-id>.json`.
2. Edit `id`, `name`, `url`, `funder_type`, fields, submit.
3. Set `verified: false` until a human runs `MODE=submit DRY_RUN=true` and confirms the plan looks right.
4. Add to `~/.openclaw/state/funder-portfolio.json` with priority.
5. Flip `verified: true` only after a successful manual end-to-end.

## Deprecation note

`apply-to-yc` is the predecessor. It still works (do not delete) but new development happens here. The cron previously named `accelerator-application-monthly` was migrated 2026-05-07 to invoke `apply-to-funder` instead of the legacy skill.
