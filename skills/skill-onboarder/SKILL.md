---
name: skill-onboarder
description: Meta-skill — runs the standard 3–5 question wizard for any other skill. When invoked with SKILL=<target>, reads ~/.openclaw/skills/<target>/SKILL.md, extracts (or generates) its wizard section, prompts the user, writes config to ~/.openclaw/state/<target>.json, proposes a cron entry, and writes it to jobs.json with enabled=false until acked. Codifies the load-time wizard convention so every skill defers here for first-time setup.
metadata:
  tags: meta, onboarding, wizard, setup, convention
  version: 0.1.0
  requires:
    bins: [bash, jq, python3]
    env_live: []
  invariants:
    - Never edits the target skill's SKILL.md.
    - Never auto-flips POLITICIAN_DRY_RUN, LOBBYIST_HIRED, or any other gate flag without explicit user ack.
    - Always writes new cron entries with enabled=false. Flipping to true is a separate explicit step.
    - Never overwrites an existing ~/.openclaw/state/<skill>.json without writing .bak.<ts> first.
    - Wizard answers are persisted before any cron-proposal step — partial state is preserved across re-invocation.
license: MIT
---

# skill-onboarder

The single mechanism every OpenClaw skill uses for first-time setup. Instead of each skill reinventing its own wizard, they delegate here. This solves the "11 skills, 11 inconsistent setup flows" problem by codifying the convention in one place.

## Mode dispatch

```bash
SKILL=politician         bash scripts/run.sh   # onboards the politician skill
SKILL=naist-thesis       bash scripts/run.sh   # onboards naist-thesis
SKILL=apply-to-funder    bash scripts/run.sh   # onboards apply-to-funder
```

Force a re-run after partial config: `REONBOARD=1 SKILL=<target> bash scripts/run.sh`.

## Invariants

- The target skill's `SKILL.md` is **read-only** to skill-onboarder. Never edit it.
- All wizard answers persist to `~/.openclaw/state/<target>.json` (canonical state). If the file already exists, it is backed up to `~/.openclaw/state/<target>.json.bak.<ts>` before merge.
- The proposed cron entry is appended to `~/.openclaw/state/jobs.json` with `enabled: false`. Flipping to `true` is a separate explicit step — `enabled: true` writes are never made by this skill.
- Lifecycle gate flags (`LOBBYIST_HIRED`, `PAC_FORMED`, `JP_SEIJIDANTAI_REGISTERED`, `POLITICIAN_DRY_RUN`, etc.) are never auto-flipped by this skill. The wizard collects intent only.

## Target-skill discovery

When invoked with `SKILL=<target>`, the onboarder:

1. Resolves the target SKILL.md path: `~/.openclaw/skills/<target>/SKILL.md`. Errors out if missing.
2. Parses the YAML frontmatter for `name`, `description`, `metadata.requires.env_live`, `metadata.invariants`.
3. Searches the body for a `## Setup wizard` section (h2). If present, parses numbered questions in the form `<n>. **<label>** — <prompt>. Default: \`<default>\`. → \`state.path\`.`
4. If no `## Setup wizard` section exists, generates a default 3-question wizard from frontmatter:
   - Q1: confirm scope of automation (free-text)
   - Q2: cadence (daily | weekly | monthly | manual)
   - Q3: Slack channel for output (default = `~/.openclaw/state/anicca.json::slack.metrics_channel`)
5. Prompts the user one question at a time via stdin. Validates each answer against the type hint embedded in the question (`enum:`, `{{profile.lateness.stakeholders.channel}}:`, `int:`, `bool:` — defaults to free-text).

## Config-write conventions

Answers are merged into `~/.openclaw/state/<target>.json` using the dotted path declared after `→` in each question. Example:

```
3. **US {{profile.lateness.stakeholders.senderType}} shells status** — `none | llc_only | llc_527 | llc_527_pac | llc_527_pac_501c4`. → `politician.us_shells_status`.
```

writes `{"politician": {"us_shells_status": "<answer>"}}` into `~/.openclaw/state/anicca.json` (keyed by skill).

For skills whose canonical state file is **not** `anicca.json` (e.g. `naist-thesis` writes to `~/.openclaw/state/naist-thesis.json`), the question line uses `→ \`state.<skill>.<key>\`` and the onboarder routes to `~/.openclaw/state/<skill>.json` instead. The frontmatter key `metadata.state_file` overrides the default.

Sensitive values (LDA registrant ID, FEC committee ID, Stripe account ID) are still written to JSON state — secrets like API keys go in `~/.openclaw/.env`, never in state JSON. The wizard prompts `please add <KEY>=… to ~/.openclaw/.env when ready` and writes a placeholder reminder into `~/.openclaw/state/<target>.todo.md` instead of capturing the secret.

## Cron-proposal logic

After answers persist, the onboarder builds a proposed cron entry:

```json
{
  "skill": "<target>",
  "mode": "<inferred from SKILL.md mode dispatch table>",
  "schedule": "<from cadence answer>",
  "delivery": { "mode": "announce", "target": "<slack metrics channel>" },
  "enabled": false,
  "proposed_at": "<utc-iso>",
  "proposed_by": "skill-onboarder/0.1.0"
}
```

The cadence-to-cron mapping:

| cadence | cron expression       |
|---------|-----------------------|
| daily   | `0 9 * * *` (09:00 UTC)  |
| weekly  | `0 9 * * 1` (Mon 09:00)  |
| monthly | `0 9 1 * *` (1st 09:00)  |
| manual  | omitted — skill kept on-demand |

The user is shown the proposed entry as JSON and asked to ack with `yes` / `no`. On `yes`, the entry is appended to `~/.openclaw/state/jobs.json` with `enabled: false`. On `no`, the entry is written to `~/.openclaw/state/<target>.todo.md` with a `# TODO: cron declined — re-run skill-onboarder when ready.` header.

## Slack target resolution

Every cron `delivery.target` defaults to the canonical Slack metrics channel from `~/.openclaw/state/anicca.json::slack.metrics_channel` (currently `{{profile.channels.reportChannel}}`). Skills that need a different channel override via the wizard question. **Never hard-code channel IDs** in the proposed cron entry — always resolve via the canonical state path so a single edit there propagates everywhere.

The same resolver pattern applies to the bash one-liner skills emit at runtime:

```bash
--target $(jq -r .slack.metrics_channel ~/.openclaw/state/anicca.json)
```

This resolver pattern is required of every new skill — the `skill-creator` template bakes it in.

## Post-onboarding handoff

After cron entry is written, the onboarder prints:

1. The path to the state JSON: `~/.openclaw/state/<target>.json`.
2. The path to the `.todo.md` file (if any).
3. A one-liner showing how to flip the new cron entry from `enabled: false` to `true`:
   ```
   jq '(.jobs[] | select(.skill=="<target>")) .enabled = true' \
     ~/.openclaw/state/jobs.json > /tmp/j && mv /tmp/j ~/.openclaw/state/jobs.json
   ```
4. A summary of any gate flags the skill still expects in `~/.openclaw/.env` (read from `metadata.requires.env_dryrun_until_flipped`).
5. The exact `MODE=<m> bash scripts/run.sh` command to do a manual smoke run.

## File layout

```
~/.openclaw/skills/skill-onboarder/
├── SKILL.md
└── scripts/
    └── run.sh             MODE dispatcher; reads SKILL=<target>, drives wizard
```

## Standard wizard pattern (the convention every skill should follow)

Skills should include a `## Setup wizard` section in their SKILL.md with this shape:

```markdown
## Setup wizard (N questions)

The wizard is invoked by the `skill-onboarder` skill (`SKILL=<this-skill> bash ~/.openclaw/skills/skill-onboarder/scripts/run.sh`).

1. **<short label>** — <prompt sentence>. Default: `<default>`. → `<dotted.state.path>`.
2. **<short label>** — <prompt>. → `<dotted.state.path>`.
…
```

Question count: 3 minimum, 8 maximum. Less than 3 means the skill probably has no real config and onboarding is unnecessary; more than 8 means the questionnaire should be split across two skills or moved to a config file the user edits manually.

Every skill that has *any* persistent state (cron, env-flag gates, hired humans, account IDs) MUST have a wizard section. Skills that are purely on-demand and stateless (e.g. one-shot generators) may omit it.
