# OpenClaw Skills Spec — Source of Truth

v2.9, last updated 2026-05-14

---

## How to use this document

This file is the **contract**. It is the single canonical source-of-truth for the ten OpenClaw / Anicca skills that make up the Anicca operating system. Every skill defined here ships open-source as its own GitHub repo; every agent that loads a skill runs the setup wizard defined in this document; every cron entry in `~/.openclaw/cron/jobs.json` is generated from a `cron-template.json` block in this document; every Slack alert routes to the metrics channel via the template defined in cross-cutting infrastructure.

Read order if you are an agent loading a skill for the first time:
1. The cross-cutting infrastructure section (one read, applies to all skills).
2. The open-source release standard (defines what every repo must contain).
3. The skill-specific section, in this document, in the order listed in “The 10 skills at a glance”.
4. The roll-out sequence and open-source rollout sequence — these define what to build first and what to ship public first.
5. The marketing playbook — defines how to announce each public release.

Read order if you are a human collaborator (or Dais himself):
1. The 10 skills at a glance.
2. The skill you care about.
3. The roll-out sequence to know what blocks what.

If two parts of this document disagree, the per-skill section wins, then the cross-cutting infrastructure section, then the roll-out sequence. If the document and the live system disagree, the live system loses — fix the live system to match this document.

When updating this document: bump the `v1` at the top, change `last updated`, and append a one-line entry to the “Changelog” at the bottom of this file. Do not delete history.

---

## The 10 skills at a glance

| # | name | one-line description | status | open-source readiness | repo slug |
|---|------|---------------------|--------|----------------------|-----------|
| 1 | tuning-skills | nightly diagnostic + repair pass over failing crons | LIVE (v0.1.0) | STAGED at `~/tuning-skills/` (launch wk 1) | `Daisuke134/tuning-skills` |
| 2 | larry / content-iteration | TikTok / Instagram / X / YouTube cross-platform content + closed-loop iteration on metrics | LIVE | STAGED at `~/.openclaw/_launch-staging/content-iteration/` (launch wk 8 — see open-issue note: production-name `larry` not yet present in `~/.openclaw/skills/`) | `Daisuke134/content-iteration` |
| 3 | build-in-public | daily X build-in-public posts, Postiz analytics-driven | LIVE | STAGED at `~/.openclaw/_launch-staging/build-in-public-skill/` (launch wk 2) | `Daisuke134/build-in-public-skill` |
| 4 | article-writer | daily dev.to + Zenn articles | LIVE (DRY_RUN until 30-day quality bake-in) | STAGED at `~/.openclaw/_launch-staging/article-writer/` (launch wk 3) | `Daisuke134/article-writer` |
| 5 | app-review | daily/weekly App Store review pull + auto-reply | LIVE | STAGED at `~/.openclaw/_launch-staging/app-review-skill/` (launch wk 4) | `Daisuke134/app-review-skill` |
| 6 | skill-for-you | daily ClawHub skill recommendations from session-log analysis | LIVE (DRY_RUN — recommendations posted, install-feedback loop pending) | STAGED at `~/.openclaw/_launch-staging/skill-for-you/` (launch wk 5) | `Daisuke134/skill-for-you` |
| 7 | donation | monthly 1% revenue donation to charities, agent-browser rails | SCAFFOLD (cron entry exists, first month-end run pending) | STAGED at `~/.openclaw/_launch-staging/donation-skill/` (launch wk 6) | `Daisuke134/donation-skill` |
| 8 | NAIST | 9 sub-skill suite for NAIST student/professor workload (forwarding-based, Gmail-MCP) | LIVE (9 sub-skills shipped) | STAGED at `~/.openclaw/_launch-staging/naist-skill/` (launch wk 7 — public release still gated on graduation) | `Daisuke134/naist-skill` |
| 9 | auto-research | autonomous AI scientist: 23-stage AutoResearchClaw chassis + K-Dense skills + Sakana BFTS + Karpathy refine + apply-to-funder | LIVE (chassis end-to-end; first paper still rendering) | STAGED at `~/.openclaw/_launch-staging/auto-research/` (launch wk 9) | `Daisuke134/auto-research` |
| 10 | politician | autonomous AI politician: 政治団体 + DE LLC + 527 + Super PAC + LDA lobbying + bill drafting + staffer CRM + civic action APIs + human-instrument hiring | LIVE (v0.1.0 scaffold: 4 LIVE intel crons + 7 DRY_RUN action crons; legal shells aspirational) | STAGED at `~/.openclaw/_launch-staging/anicca-politician/` (launch wk 10 — gated on first bill drafted + counsel review) | `Daisuke134/anicca-politician` |

Skill #2 (mobileapp-iterator) in the original list is intentionally skipped. Skills #3 (larry) and #10 (content-iteration) are merged in this spec because they are functionally identical — both iterate cross-platform content on a closed feedback loop. The merged skill is documented as “2. larry / content-iteration” below.

---

## Cross-cutting infrastructure

This section defines the shared infrastructure every skill depends on. Build it once; every skill consumes it.

### Cron master

- Path: `~/.openclaw/cron/jobs.json` (the file on the VPS / dev Mac that the OpenClaw Gateway reads).
- Mirror in the dev repo: `/Users/anicca/anicca-project/openclaw-skills/jobs.json`. The repo mirror is the source of truth for proposed changes; the live `~/.openclaw/cron/jobs.json` is the running copy.
- Sync rule: `rsync -av openclaw-skills/jobs.json anicca@VPS:/home/anicca/.openclaw/cron/jobs.json` while the gateway is stopped, then restart the gateway (`systemctl --user stop / start openclaw-gateway.service`).
- Format: a single JSON object with keys `version` (currently 1) and `jobs` (an array). Every job has `id`, `agentId`, `jobId`, `name`, `schedule {kind, expr, tz}`, `sessionTarget`, `wakeMode`, `payload {kind, message}`, `delivery {mode, channel, to}`, `enabled`.
- Editing rule: only the cron-master file is edited. Per-skill `cron-template.json` files in each skill repo are merged into this master at sync time. No skill writes to its own crontab.

### Run history (task_runs)

- Path: `~/.openclaw/tasks/runs.sqlite`.
- Single table: `task_runs(id INTEGER PRIMARY KEY, skill TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, exit_code INTEGER, slot TEXT, output_path TEXT, error TEXT, slack_ts TEXT)`.
- Status values: `running`, `succeeded`, `failed`, `skipped`, `dlq`.
- Every skill writes one row when it starts (`status='running'`), then updates the same row at finish.
- The daily-memory skill is rewritten to query this table for “what ran today” instead of crawling session history (see fix below).

### Slack alert channel

- Channel name: `#metrics`.
- Channel ID: `C091G3PKHL2`.
- Every skill posts a result line here. Failure-path posts MUST include the skill name, slot, and a one-paragraph error excerpt.
- The Slack target is **never hard-coded** in a skill prompt. Instead each cron entry’s `payload.message` template uses:
  ```
  --target $(jq -r .slack.metrics_channel ~/.openclaw/state/anicca.json)
  ```
  This means the channel can be moved by editing one JSON value (`~/.openclaw/state/anicca.json` → `slack.metrics_channel`) instead of grep-replacing 22 cron entries.

### Daily-memory rewrite

The current `daily-memory` skill (`~/.openclaw/skills/daily-memory/SKILL.md`) infers “what ran today” by reading session history. That is fragile, slow, and breaks when sessions are pruned. Fix:

1. Replace the input step with a single SQL query: `SELECT skill, status, slot, started_at, finished_at, error FROM task_runs WHERE date(started_at, 'localtime', 'start of day') = date('now', 'localtime') ORDER BY started_at`.
2. Pass that result set, plus the `roundtable-standup` JSON of the day, into the diary writer.
3. Output paths stay the same: `~/.openclaw/workspace/daily-memory/lessons-learned.md` (append) and `~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` (write).

### Model-fallback fix

`~/.openclaw/openclaw.json` currently contains `openai-codex/gpt-5.5` as a fallback model entry. This model does not exist and causes silent fallback failures. Action: remove that entry. The replacement chain is `anthropic/claude-sonnet-4-6` → `anthropic/claude-opus-4-6` → `anthropic/claude-haiku-4-5-20251001`. Drop GPT-5.5 entirely.

### Slack-target template fix

Every cron `payload.message` that currently embeds the literal `C091G3PKHL2` is updated to use the template above. Run-once migration script:

```bash
python3 - <<'PY'
import json, re, pathlib
p = pathlib.Path('~/.openclaw/cron/jobs.json').expanduser()
d = json.loads(p.read_text())
sub = "$(jq -r .slack.metrics_channel ~/.openclaw/state/anicca.json)"
changed = 0
for j in d['jobs']:
    msg = j.get('payload', {}).get('message', '')
    new = re.sub(r'C091G3PKHL2', sub, msg)
    if new != msg:
        j['payload']['message'] = new
        changed += 1
p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
print(f'patched {changed} jobs')
PY
```

After this migration, the channel ID lives in exactly one place: `~/.openclaw/state/anicca.json`.

### Skill-onboarder meta-skill: standard load-time wizard pattern

Every skill loaded for the first time on a host runs a standard wizard defined here. The wizard:

1. Looks up the skill’s entry in this spec, parses the “Setup wizard” numbered list.
2. For each numbered question, prompts the user, accepting the bracketed default on empty input.
3. Persists each answer to the file path written next to the question.
4. After all answers are persisted, runs `~/.openclaw/skills/<skill>/scripts/postinstall.sh` if it exists.
5. Writes a one-line success note to `~/.openclaw/state/skills.jsonl`: `{"skill":"<name>","installed_at":"<iso>","host":"<hostname>","version":"<git-sha>"}`.

This wizard is itself a skill: `~/.openclaw/skills/skill-onboarder/SKILL.md`. Other skills inherit from it; they don’t reimplement question prompting.

---

## End-to-end auto-submit + landing page registry

Added v1.5 (2026-05-08). Three principles every skill in this spec MUST honour. These principles override any earlier-version section that conflicts (e.g., per-skill "👍/❌ react-to-confirm" gates introduced in v1.0–v1.4 are revoked except where listed below as legally required).

### 1. End-to-end auto-submit

Every skill’s output MUST land in the external world without a per-run human approval step. Drafting an artifact and waiting for a 👍 reaction is forbidden. The pattern is: **produce → submit → log the public artifact URL → react if revoked**, not draft → wait → maybe send.

Approval gates that remain mandatory (because they are legally required, not stylistically conservative):

| Where | Why |
|-------|-----|
| LDA quarterly filing (LD-2) signature | 2 U.S.C. §1605 — registered lobbyist personally liable; signature must be a named natural person |
| FEC quarterly / year-end filing signature | 11 CFR §104.14 — treasurer signs |
| 政治資金収支報告書 signature | 政治資金規正法 — 会計責任者 印鑑 必要 |
| Independent-expenditure pre-clearance (Super PAC) | counsel review per FEC coordination rules |

These four are handled by an **e-signature counter-flow** (DocuSign-class API): the skill prepares the filing, fires a signature request to the named human, the human’s signature is captured electronically, the skill submits the signed document. The cron does not pause — the signature request is asynchronous, and submission happens automatically once the signature lands. There is no Slack 👍 step.

All other "human gates" introduced in earlier versions of this spec are revoked. Specifically:

| Previously gated | v1.5 status |
|------------------|-------------|
| App Store review reply (👍/❌ react-to-confirm) | AUTO-SUBMIT. Replies post via ASC API immediately. Spam / legal-threat / harassment classes skipped; everything else replied. |
| NAIST homework reply | AUTO-SUBMIT. PDF compiled by Quarto → Gmail Send-mail-as → NAIST address. Single academic-integrity README disclaimer; no per-thread approval. |
| NAIST question / TA-task / professor-task / bureaucracy reply | AUTO-SUBMIT. |
| Auto-research arXiv / grant submit (`submit_confirm: yes`) | AUTO-SUBMIT. arXiv submitter API + funder portals are wired; submissions fire on cron. |
| Donation `--auto-confirm` | AUTO-SUBMIT (DRY_RUN flag still in effect for the first month-end as a one-time guard). |
| Build-in-public preview gate | AUTO-SUBMIT. |

### 2. Bootstrap workflow (applies to every skill)

Each skill goes through these four phases in order. A skill that has not been through phase 0–2 manually MUST NOT be registered as a phase-3 daily cron.

| Phase | What happens | Who |
|-------|-------------|-----|
| 0. Claude Code E2E run | The assistant runs every step in the proposed SKILL.md from a terminal, watching the **actual external artifact** appear (real tweet URL / real dev.to slug / real arXiv ID / real charity receipt PDF / real NAIST send-as transcript). Mocking the external call is forbidden. The output is a copy-pasted command transcript saved to `~/.openclaw/workspace/<skill>/bootstrap-transcript-<ymd>.md` plus the resolved artifact URL. | Claude Code |
| 1. Skill-ize | Copy the verified transcript into `~/.openclaw/skills/<skill>/SKILL.md` as canonical. Promote shared steps into `scripts/`. Run `skill-onboarder` if first install. | Claude Code |
| 2. Today-test cron | Register a one-shot cron at `now + 5 min` (`<skill>-today-test`, `enabled: true`, run-once). Gateway picks it up and reproduces the same artifact. If the artifact does not match phase 0, go back. | Claude Code |
| 3. Daily cron | Register the production cron at the spec’d schedule. From this point `tuning-skills` watches it. | Claude Code |

A skill is not "done" until phase 3 has fired and produced its external artifact at least three days in a row. "I wrote the SKILL.md" is not done. "Cron is registered" is not done.

### 3. External output principle (applies to every skill)

For every skill, the question "what did Anicca actually do today?" must be answerable by pointing at a public artifact, not a Slack message. A Slack note saying "I tweeted X" is internal; the tweet URL itself is the output.

Per-skill external-output binding:

| # | skill | External output (where it lands) |
|---|-------|-----------------------------------|
| 1 | tuning-skills | Repaired `~/.openclaw/cron/jobs.json` + `repairs/<ymd>.json` showing N cron entries restored. (Internal — keeps the other 9 alive.) |
| 2 | larry / content-iteration | X posts (@aniccaen + @aniccaxxx) + TikTok video + Instagram post + YouTube Short — 4 platforms × 2 slots/day, each returning `publicUrl` from Postiz. |
| 3 | build-in-public | Two X tweets per morning (EN @aniccaen, JA @aniccaxxx) — Day N of building Anicca. |
| 4 | article-writer | 1 dev.to article (EN slug) + 1 Zenn article (JA URL) per day, both live on publish; cross-link tweet at noon. |
| 5 | app-reviews | App Store reply visible on the listing within minutes (`POST /v1/customerReviewResponses`); bug-class also auto-opens GitHub issue on `Daisuke134/anicca-ios`. |
| 6 | skill-for-you | (HOLD per user) When active: ClawHub install command in Slack — no public artifact. |
| 7 | donation | Real card-based charity transfer via Vercel Agent Browser; receipt PDF published; X tweet announcing amount + recipient + receipt URL. |
| 8 | NAIST | Outbound mail from `<student-id>@is.naist.jp` (Gmail Send-mail-as): homework PDFs, replies, TA acknowledgements, bureaucracy submissions. Private but auditable via `sent.json`. |
| 9 | auto-research | arXiv preprint (`arxiv.org/abs/<id>`) + funder grant submission (NSF / JST / OpenPhil / FLI portal submission IDs). |
| 10 | politician | Bill draft delivered to target legislator’s office (registered-lobbyist Gmail send); staffer outreach mail; FEC + LDA + 政治資金収支報告書 filed via the corresponding electronic-filing portal with counter-signed e-signature; PAC ledger entries posted. |

### 4. Landing page registry

Every skill that produces a public artifact (paper, post, donation receipt, bill, App Store reply) ALSO updates a corresponding `aniccaai.com/<slug>` page. The landing page is the public-trust layer: without it, "Anicca shipped X" is unverifiable.

The aniccaai-landing site lives at `apps/landing/` in this monorepo (Next.js, deployed at aniccaai.com). The skill that produces the artifact also commits + pushes a SSOT data file to `apps/landing/data/<slug>.json`; the page reads from it on next build / next ISR revalidation. Any commit to `apps/landing/data/**` triggers a rebuild on the landing host.

| # | Slug | URL | Updated by | What it shows |
|---|------|-----|------------|---------------|
| 1 | (none) | — | tuning-skills | (internal — no public page) |
| 2 | `larry` | `aniccaai.com/larry` | larry | Rolling 7-day SNS feed × 4 platforms × 2 slots, embed cards, Postiz analytics per post |
| 3 | `build-in-public` | `aniccaai.com/build-in-public` | build-in-public | Day 1 → today, EN+JA, with engagement numbers from Postiz |
| 4 | `articles` | `aniccaai.com/articles` | article-writer | All published dev.to + Zenn articles, EN/JA toggle, search |
| 5 | `app-reviews` | `aniccaai.com/app-reviews` | app-reviews | Public reply transcript per app, reviewer locale, reply text, refreshed daily |
| 6 | `skill-for-you` | `aniccaai.com/skill-for-you` | skill-for-you (HOLD) | Past 30-day recommendation log, redacted of profile data |
| 7 | `donation` | `aniccaai.com/donation` | donation | Every monthly run as a row: gross / net / amount / recipients / receipt PDF / txn IDs |
| 8 | (none) | — | NAIST | (private — academic workload not public) |
| 9 | `research` | `aniccaai.com/research` | auto-research | Each paper as a card: title, authors, arXiv ID, PDF link, status (submitted / accepted / rejected), grant outcomes |
| 10 | `politics` | `aniccaai.com/politics` | politician | All bills (with diff vs. existing US Code), FEC + LDA + 政治団体 ledger, contact log per legislator, all filings.pdf downloadable |

The existing `aniccaai.com/donation`, `aniccaai.com/research`, `aniccaai.com/politics` pages (referenced by Dais in earlier conversations) are the v1.5-targeted versions of these slugs; the seven other slugs (#2, #3, #4, #5, #6) are NEW and need to be scaffolded as part of the corresponding skill’s bootstrap workflow.

---

## Open-source release standard

Every skill in this spec ships as its own GitHub repo under `github.com/Daisuke134` (eventually `github.com/anicca-org` once the org is set up — repo slugs in the per-skill sections will move at that point). Each repo MUST contain:

- `SKILL.md` — the spec for **agents**. Format: front-matter (`name`, `description`, `metadata.openclaw`) + the “Features”, “Setup wizard”, “Crons”, “Required env / secrets” sections from this document, copied verbatim.
- `README.md` — the spec for **humans**. Format: tagline, a one-paragraph “what this is”, a “how to install” block (`openclaw skill install <slug>`), a “what it does” bullet list (mirrors the Features list), a screenshot or widget link, a “status” badge tied to GitHub Actions, the launch tweet at the bottom.
- `LICENSE` — MIT. No exceptions. The whole point is composability.
- `examples/` — directory with one or more `<scenario>.json` and the corresponding `<scenario>.expected.json` (or `.md`) so both humans and agents can see what input produces what output.
- `.github/workflows/release.yml` — on `git tag v*`, runs the test suite, builds the skill bundle, and publishes a release to ClawHub via `claw release publish`.
- `X-announce-copy.md` — exactly what gets tweeted on launch day. The text in this file and the “Launch tweet” line in this spec must match.
- `cron-template.json` — drop-in cron entries for `~/.openclaw/cron/jobs.json`. The `tuning-skills` repair pass uses this file when restoring a broken cron.

Human-instrument hiring is in scope for the politician repo (see #10) but not for any other repo.

---

## Skill specs

The ten skills, in order, with the exact subsection set required by the contract.

---

### 1. tuning-skills

**Status.** LIVE (v0.1.0) — diagnose + repair pass shipped at `~/.openclaw/skills/tuning-skills/`; first nightly run completed; OSS repo staged at `~/tuning-skills/` and ready for `gh repo create + push` (launch week 1).

**Implementation status (as of 2026-05-07).** Skill scripts (`diagnose.py`, `repair.py`, known-fix table, ticket writer, Slack rollup) are in `~/.openclaw/skills/tuning-skills/`. `task_runs` table populated, fail/dlq scans return real rows, the gpt-5.5 known-fix recipe was validated against this session's openclaw.json clean-up. OSS repo pre-staged at `~/tuning-skills/` (the original — separate from the 9 staged this session at `~/.openclaw/_launch-staging/`). Backlog: ~30 nights of repair-pass logs before opening the auto-repair set to community-contributed recipes; codex-review escalation thread still uses the default Slack handle.

**What it brings.** A nightly diagnostic that reads `~/.openclaw/tasks/runs.sqlite`, identifies skills that failed in the last 24 h or 7 d, and either (a) auto-repairs known failure modes (missing env, broken Slack target template, deprecated model name in payload) or (b) opens a structured “tuning ticket” in `~/.openclaw/workspace/tuning-skills/tickets/YYYY-MM-DD.json` with a one-paragraph summary and a proposed fix. Result: the system gets healthier night-over-night without manual triage.

**File paths (current).**
- `~/.openclaw/tasks/runs.sqlite` (input — run history, see cross-cutting infra)
- `~/.openclaw/cron/jobs.json` (input/output — the cron master)
- `~/.openclaw/state/anicca.json` (input — Slack channel and other targets)
- `~/.openclaw/openclaw.json` (input/output — model fallback chain)
- `~/.openclaw/skills/tuning-skills/SKILL.md` (to-create)
- `~/.openclaw/skills/tuning-skills/scripts/diagnose.py` (to-create)
- `~/.openclaw/skills/tuning-skills/scripts/repair.py` (to-create)
- `~/.openclaw/workspace/tuning-skills/tickets/YYYY-MM-DD.json` (output, to-create)
- `~/.openclaw/workspace/tuning-skills/repairs/YYYY-MM-DD.json` (output, to-create — log of automated fixes applied tonight)

**Features.**
1. **fail-scan** — query `task_runs` for `status='failed'` rows in the last 24 h, group by skill+error-class.
2. **dlq-scan** — query `task_runs` for `status='dlq'` rows ever, alert if > 3 rows for the same skill.
3. **known-fix table** — apply these patches without asking: missing `BLOTATO_API_KEY` env → re-source `~/.openclaw/.env`; literal `C091G3PKHL2` in payload → swap to template; `openai-codex/gpt-5.5` in any payload → drop and let fallback chain resolve.
4. **ticket-write** — for unknown failure classes, write a Markdown-flavoured JSON ticket with reproduction steps and a `proposed_fix` field.
5. **Slack rollup** — one Slack post per night summarizing repairs applied + tickets opened. Format: `tuning-skills 2026-05-07 — :wrench: 4 auto-repairs / :clipboard: 2 tickets`.
6. **codex-review escalation** — for tickets older than 3 days, escalate by posting the ticket body to Slack and tagging `@dais` directly.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 2 * * *` | Asia/Tokyo | tuning-skills-nightly | full diagnostic + auto-repair pass |
| `0 9 * * 0` | Asia/Tokyo | tuning-skills-weekly-summary | post 7-day rollup to #metrics every Sunday morning |

**Setup wizard.**
1. Confirm the cron master path. Default: `~/.openclaw/cron/jobs.json`. Persisted to: `~/.openclaw/state/anicca.json` → `cron.master_path`.
2. Confirm the run-history DB path. Default: `~/.openclaw/tasks/runs.sqlite`. Persisted to: `~/.openclaw/state/anicca.json` → `runs.db_path`.
3. Confirm Slack escalation channel. Default: `C091G3PKHL2` (#metrics). Persisted to: `~/.openclaw/state/anicca.json` → `slack.metrics_channel`.
4. Confirm DLQ alert threshold. Default: 3. Persisted to: `~/.openclaw/state/anicca.json` → `tuning.dlq_threshold`.
5. Confirm escalation handle on Slack. Default: `@dais`. Persisted to: `~/.openclaw/state/anicca.json` → `tuning.escalate_to`.

**Required env / secrets.**
- `SLACK_BOT_TOKEN` (post the rollup)
- `OPENCLAW_API_KEY` (read other skills’ runs)

**External APIs / tools.**
- Slack Web API `chat.postMessage` (auth: bot token; rate limit: 1 msg/sec/channel).
- SQLite (local, no auth).
- Python 3.11+, `jq`, `rsync` (used by repair pass).

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/tuning-skills`
- Public name: `OpenClaw Tuning`
- Tagline: nightly self-repair for your OpenClaw skills.
- README.md outline:
  - what this is + screenshot of a Slack rollup
  - install (one command)
  - the known-fix table (so users can extend it)
  - how to add a custom repair recipe
  - how to read tickets and propose fixes back
- Launch tweet: `OpenClaw Tuning ships tonight. It runs at 2am, reads the run history of every other skill, auto-fixes the broken cron entries it knows how to fix, files tickets for the rest, and posts a rollup. The thing that keeps the agent layer alive. MIT. <REPO_URL>`
- Why ship now / why hold: IN-DEV — ship after first month of real-world telemetry. Need ~30 nights of repair-pass logs to make sure no recipe is destructive.

**Risks / known gaps.**
- Auto-repair is a foot-gun: a wrong recipe could silently break a working cron. Mitigation: every repair writes a `before/after` diff to `repairs/YYYY-MM-DD.json` and a one-line Slack message; the user can revert by re-running the night with `--undo`.
- DLQ semantics not yet defined per skill — need a per-skill convention before the alert is meaningful.
- The known-fix table will rot — needs to be reviewed monthly.

---

### 2. larry / content-iteration

**Status.** LIVE — TikTok, X, and (via reelfarm) the slideshow stack are live; daily-report and strategy-updater are governed by the existing Bible compliance spec and currently flipping back to enabled.

**Implementation status (as of 2026-05-07).** All 9 listed crons except `instagram-poster-*` and `youtube-shorts-poster` are in `~/.openclaw/cron/jobs.json` and shipping. The two reelfarm loops (LOOP A daily, LOOP B weekly) are running. Larry-strategy-updater + larry-daily-report-en/ja are LIVE post-Bible-compliance fix. **OSS-launch-name discrepancy (open issue):** the production skill name is split across `~/.openclaw/skills/x-poster/`, `tiktok-poster/`, `larry-strategy-updater/` etc. — there is no consolidated `~/.openclaw/skills/larry/SKILL.md`, so the launch-stage script could not copy a production SKILL.md into the staged OSS repo at `~/.openclaw/_launch-staging/content-iteration/`. The staged repo currently ships the template-stub SKILL.md with placeholders replaced; before the week-8 launch, either consolidate the larry sub-skills into one SKILL.md or change the staged repo to multi-skill format. Backlog: IG + YouTube arms; fold reelfarm-API key rotation into the launch wizard.

**What it brings.** Cross-platform content production with closed-loop iteration. The skill drafts and posts to TikTok, Instagram, X, and YouTube on a daily schedule; the metrics-loop reads engagement back from each platform; the strategy-updater rewrites the hook bank weekly so under-performing hooks are retired and high performers cloned. This is the skill that turns Anicca from “posts a thing once” to “a content engine that gets better while you sleep”.

**File paths (current).**
- `~/.openclaw/skills/x-poster/SKILL.md` — current path. Mirror: `openclaw-skills/x-poster/SKILL.md`.
- `~/.openclaw/skills/tiktok-poster/SKILL.md` — current path. Mirror: `openclaw-skills/tiktok-poster/SKILL.md`.
- `~/.openclaw/skills/trend-hunter/SKILL.md` — current path. Mirror: `openclaw-skills/trend-hunter/SKILL.md`.
- `~/.openclaw/skills/reelfarm/SKILL.md` — current path. Mirror: `openclaw-skills/reelfarm-skill/`.
- `~/.openclaw/skills/larry-strategy-updater/SKILL.md` — current path (governed by `larry-bible-compliance-spec.md`).
- `~/.openclaw/skills/larry-daily-report-en/SKILL.md`, `~/.openclaw/skills/larry-daily-report-ja/SKILL.md` — current paths.
- `~/.openclaw/workspace/hooks/{9am,9pm}/YYYY-MM-DD.json` — output of trend-hunter, input of x-poster + tiktok-poster.
- `~/.openclaw/workspace/trends/{9am,9pm}/YYYY-MM-DD.json` — raw trend dump.
- `~/.openclaw/workspace/reelfarm/metrics/YYYY-MM-DD.json`, `~/.openclaw/workspace/reelfarm/library/YYYY-MM-DD.json` — engagement readback.
- `~/.openclaw/skills/instagram-poster/SKILL.md` (to-create — IG arm not yet wired).
- `~/.openclaw/skills/youtube-shorts-poster/SKILL.md` (to-create — YouTube arm not yet wired).

**Features.**
1. **trend-hunter** — pulls X / TikTok / Reddit trends twice a day (5am + 5pm JST); writes one slot file with one X postText + one TikTok caption + imagePrompt.
2. **x-poster** — reads the slot file, posts to X via Blotato (`backend.blotato.com/v2`), 260-char cap, no replies.
3. **tiktok-poster** — reads the slot file; if `imageUrl` is empty, calls FAL with `imagePrompt` to generate one; posts to TikTok via Blotato; polls Blotato for `publicUrl` and writes it back.
4. **instagram-poster** (planned) — reads the same slot file with `platform: "instagram"`; posts via Blotato Instagram graph.
5. **youtube-shorts-poster** (planned) — reads slot file with `platform: "youtube"`; posts a 9:16 short via Blotato YouTube channel binding.
6. **reelfarm-metrics-loop (LOOP A)** — daily at 04:00 JST; reads 7-day metrics for every active automation, scores hooks (`views*0.4 + likes*0.3 + comments*0.2 + shares*0.1`), retires the bottom 3, generates 3 replacements, PATCHes automations.
7. **reelfarm-library-loop (LOOP B)** — weekly Sun 04:30 JST; pulls viral library content per niche, creates new automations subject to the 6/day per-account cap.
8. **larry-strategy-updater** — daily 05:00 JST; rewrites the hook bank for the day’s posts using yesterday’s engagement.
9. **larry-daily-report-en / larry-daily-report-ja** — EN 07:00 / JA 06:30; posts the “what we shipped, what worked, what didn’t” recap.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 5 * * *` | Asia/Tokyo | trend-hunter-5am | morning slot trend pull |
| `0 17 * * *` | Asia/Tokyo | trend-hunter-5pm | evening slot trend pull |
| `0 9 * * *` | Asia/Tokyo | x-poster-morning | post 9am slot to X |
| `0 21 * * *` | Asia/Tokyo | x-poster-evening | post 9pm slot to X |
| `0 9 * * *` | Asia/Tokyo | tiktok-poster-morning | post 9am slot to TikTok |
| `0 21 * * *` | Asia/Tokyo | tiktok-poster-evening | post 9pm slot to TikTok |
| `0 9 * * *` | Asia/Tokyo | instagram-poster-morning | (planned) post 9am to IG |
| `0 21 * * *` | Asia/Tokyo | instagram-poster-evening | (planned) post 9pm to IG |
| `0 9 * * *` | Asia/Tokyo | youtube-shorts-poster | (planned) post daily short |
| `0 4 * * *` | Asia/Tokyo | reelfarm-metrics-loop | LOOP A — retire bottom 3 hooks |
| `30 4 * * 0` | Asia/Tokyo | reelfarm-library-loop | LOOP B — weekly viral library scan |
| `0 5 * * *` | Asia/Tokyo | larry-strategy-updater | rewrite hook bank from yesterday’s metrics |
| `0 7 * * *` | Asia/Tokyo | larry-daily-report-en | EN recap |
| `30 6 * * *` | Asia/Tokyo | larry-daily-report-ja | JA recap |

**Setup wizard.**
1. Blotato API key. No default. Persisted to: `~/.openclaw/.env` → `BLOTATO_API_KEY`.
2. Blotato X account ID (English, @aniccaen). No default. Persisted to: `~/.openclaw/.env` → `BLOTATO_ACCOUNT_ID_EN`.
3. Blotato X account ID (Japanese, @aniccaxxx). No default. Persisted to: `~/.openclaw/.env` → `BLOTATO_ACCOUNT_ID_JA`.
4. Blotato TikTok account ID. No default. Persisted to: `~/.openclaw/.env` → `BLOTATO_TIKTOK_ACCOUNT_ID`.
5. Blotato Instagram account ID (optional, for IG arm). No default. Persisted to: `~/.openclaw/.env` → `BLOTATO_INSTAGRAM_ACCOUNT_ID`.
6. Blotato YouTube channel binding (optional). No default. Persisted to: `~/.openclaw/.env` → `BLOTATO_YOUTUBE_CHANNEL_ID`.
7. FAL API key. No default. Persisted to: `~/.openclaw/.env` → `FAL_KEY`.
8. Apify API token (TikTok scraper). No default. Persisted to: `~/.openclaw/.env` → `APIFY_API_TOKEN`.
9. X bearer token (for trend-hunter X arm). No default. Persisted to: `~/.openclaw/.env` → `X_BEARER_TOKEN`.
10. Reelfarm API key. No default. Persisted to: `~/.openclaw/.env` → `REELFARM_API_KEY`.
11. Larry start day (Day 1 of building Anicca). Default: `2026-01-02`. Persisted to: `~/.openclaw/state/anicca.json` → `larry.start_day`.

**Required env / secrets.**
- `BLOTATO_API_KEY`, `BLOTATO_ACCOUNT_ID_EN`, `BLOTATO_ACCOUNT_ID_JA`, `BLOTATO_TIKTOK_ACCOUNT_ID`, `BLOTATO_INSTAGRAM_ACCOUNT_ID` (optional), `BLOTATO_YOUTUBE_CHANNEL_ID` (optional)
- `FAL_KEY`
- `APIFY_API_TOKEN`
- `X_BEARER_TOKEN`
- `REELFARM_API_KEY`
- `SLACK_BOT_TOKEN` (for the daily reports)

**External APIs / tools.**
- Blotato API: `https://backend.blotato.com/v2/...` (auth: API key in header; rate limit: 100/min, 1000/hour).
- FAL API: `https://fal.ai/...` (auth: bearer; varies by model).
- Apify TikTok scraper: `https://api.apify.com/v2/acts/clockworks~tiktok-scraper/runs` (auth: token query param).
- X v2 search (via `x-research`): `https://api.x.com/2/tweets/search/recent` (auth: bearer).
- Reelfarm API (auth: API key in header).
- Slack Web API (`chat.postMessage`).

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/content-iteration`
- Public name: `Content Iteration`
- Tagline: cross-platform content engine with a closed feedback loop.
- README.md outline:
  - the loop diagram (trend → draft → post → measure → rewrite hooks)
  - install + Blotato + FAL + Apify keys
  - example slot file (`hooks/9am/YYYY-MM-DD.json`)
  - tuning the scoring weights
  - how to add a new platform arm (e.g., Threads)
- Launch tweet: `Content Iteration ships open. Trend hunter + 4 platform posters + a metrics loop that rewrites hooks every night based on what worked yesterday. Drop in Blotato + FAL + Apify keys, point it at your accounts, walk away. MIT. <REPO_URL>`
- Why ship now / why hold: PROD — ship today after redaction (Blotato account IDs and Reelfarm key are gitignored; the wizard collects them on install).

**Risks / known gaps.**
- IG and YouTube arms are not yet wired — placeholders in this spec.
- Larry strategy-updater currently uses model `anthropic/claude-sonnet-4-6`; if the fallback chain resolves to Haiku, hook quality drops. Pin Sonnet in the payload until Haiku 4.5 quality is verified.
- Bible compliance fix per `larry-bible-compliance-spec.md` (slot timing 07:30/16:30/21:00, config = SELF_ONLY+UPLOAD, clean backgrounds) needs to be applied to the open-source release before public launch — otherwise the public skill is materially different from what the YouTube/X audience will see.

---

### 3. build-in-public

**Status.** LIVE — `~/.openclaw/skills/build-in-public/SKILL.md` is the canonical version, posting daily via Blotato + closing the loop with the Postiz pull at 23:00 JST. Original spec at `.cursor/plans/ios/1.6.0/sns-poster/build-in-public-spec.md` is now superseded by the production SKILL.md.

**Implementation status (as of 2026-05-07).** Production SKILL.md is in place; `bip-post-morning`, `bip-postiz-pull`, `bip-weekly-rollup` crons are in `jobs.json`. SessionEnd hook is wired (`.claude/hooks/session-end-daily-log.sh`). Day-counter computes from `larry.start_day=2026-01-02`. Postiz analytics layer is the freshest piece — landed earlier this session. OSS staging at `~/.openclaw/_launch-staging/build-in-public-skill/` is launch-ready (production SKILL.md copied verbatim, all 7 placeholders replaced, examples/ + docs/ + .github/ scaffolds inherited from template). Launch week 2 of the 10-week calendar.

**What it brings.** Daily Build-in-Public posts to X (and a Postiz analytics layer that pulls per-tweet engagement back so the next post’s tone is informed by what worked yesterday). The skill turns commits and SessionEnd hooks into a “Day X of building Anicca” thread automatically — no manual “hey post this” needed.

**File paths (current).**
- `.claude/skills/build-in-public/SKILL.md` (current spec — to be moved to `~/.openclaw/skills/build-in-public/SKILL.md` for the open-source release)
- `.claude/hooks/session-end-daily-log.sh` — SessionEnd hook that writes today’s session log
- `.claude/skills/agent-memory/memories/daily-logs/YYYY-MM-DD.md` — daily log accumulation
- `.cursor/plans/ios/version-logs/YYYY-MM-DD.md` — version-log persistence
- `.cursor/plans/ios/sns-poster/blotato.py` — Blotato post helper
- `~/.openclaw/workspace/build-in-public/sent_YYYY-MM-DD.json` (to-create — record of what posted today, with tweet URL + analytics ID)
- `~/.openclaw/workspace/build-in-public/postiz-cache.json` (to-create — Postiz analytics cache)

**Features.**
1. **session-end accumulator** — SessionEnd hook appends a transcript summary to today’s daily log.
2. **post-update generator** — reads git diff + today’s daily log, generates a 280-char EN tweet (@aniccaen) and a JA tweet (@aniccaxxx).
3. **day-counter** — computes Day X from `larry.start_day` (default 2026-01-02), minimum 1, never decrements.
4. **preview gate** — shows the post for confirmation before sending; auto-confirm only when `--auto` flag is passed by cron.
5. **Postiz analytics pull** — daily 23:00 JST: pulls per-tweet engagement (likes/RTs/replies/views) for the last 7 days’ posts via Postiz API; writes to `postiz-cache.json`.
6. **analytics-driven prompt** — the next morning’s draft prompt includes the top-3 and bottom-3 tweets from the last 7 days as in-context examples.
7. **thread-split** — if the post exceeds 280 chars, auto-splits into a thread of 280-char chunks numbered “1/n”.
8. **retry on failure** — Blotato API errors → 30 s wait → retry, max 3 attempts; final failure posts to Slack #metrics with the error code.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 8 * * *` | Asia/Tokyo | bip-post-morning | generate + post the morning Build-in-Public update |
| `0 23 * * *` | Asia/Tokyo | bip-postiz-pull | pull last-24h analytics from Postiz |
| `0 20 * * 0` | Asia/Tokyo | bip-weekly-rollup | weekly “best tweets” thread Sunday evening |

**Setup wizard.**
1. Blotato API key. (Reuses the larry/content-iteration value if already set.) Persisted to: `~/.openclaw/.env` → `BLOTATO_API_KEY`.
2. Blotato X account ID, English (@aniccaen). Persisted to: `~/.openclaw/.env` → `BLOTATO_ACCOUNT_ID_EN`.
3. Blotato X account ID, Japanese (@aniccaxxx). Persisted to: `~/.openclaw/.env` → `BLOTATO_ACCOUNT_ID_JA`.
4. Postiz API key. No default. Persisted to: `~/.openclaw/.env` → `POSTIZ_API_KEY`.
5. Postiz workspace ID. No default. Persisted to: `~/.openclaw/.env` → `POSTIZ_WORKSPACE_ID`.
6. Day 1 start date. Default: `2026-01-02`. Persisted to: `~/.openclaw/state/anicca.json` → `larry.start_day`.
7. Auto-confirm cron posts? Default: `yes`. Persisted to: `~/.openclaw/state/anicca.json` → `bip.auto_confirm`.
8. Project repo path. Default: `/Users/anicca/anicca-project`. Persisted to: `~/.openclaw/state/anicca.json` → `bip.repo_path`.

**Required env / secrets.**
- `BLOTATO_API_KEY`, `BLOTATO_ACCOUNT_ID_EN`, `BLOTATO_ACCOUNT_ID_JA`
- `POSTIZ_API_KEY`, `POSTIZ_WORKSPACE_ID`
- `SLACK_BOT_TOKEN`

**External APIs / tools.**
- Blotato API: `https://backend.blotato.com/v2/...` (auth: API key; rate limit: 100/min, 1000/hour).
- Postiz API (auth: API key; rate limit per Postiz docs).
- `git` (local).

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/build-in-public`
- Public name: `Build in Public`
- Tagline: turn your commits into a daily X thread, automatically.
- README.md outline:
  - what it does, in one diagram (commits + session log → tweet)
  - install + Blotato + Postiz keys
  - the “Day X” counter explained
  - thread-split rules
  - how to override the morning post manually
- Launch tweet: `Build in Public ships open. Plug in Blotato + Postiz, hook it to your repo, walk away. It writes the “Day X of building” tweet from your git diff + session log every morning, and rewrites tomorrow’s prompt from yesterday’s engagement. MIT. <REPO_URL>`
- Why ship now / why hold: PROD — ship today.

**Risks / known gaps.**
- Postiz analytics layer is the new piece — the existing `/post-update` skill posts but doesn’t close the loop. Wire that in before the launch tweet goes out.
- The `blotato.py` default account-key bug (`x_xg2grb` vs `x_aniccaxxx`) is fixed in spec but verify the prod copy matches.
- Session-end hook depends on `.claude/hooks/session-end-daily-log.sh` existing — for users who don’t use Claude Code, provide an alternative input (e.g., daily plain-text journal at a configurable path).

---

### 4. article-writer

**Status.** LIVE (DRY_RUN until 30-day quality bake-in) — `~/.openclaw/skills/article-writer/SKILL.md` ships the Tutorial / Postmortem / Architecture rotation; nightly drafts hit Zenn (JP) + dev.to (EN); textlint pass enforced.

**Implementation status (as of 2026-05-07).** Production SKILL.md is in place. `article-writer-draft` (06:00 JST), `article-writer-publish` (08:30 JST), `article-writer-tweet` (12:00 JST) are in `jobs.json`. dev.to API path is live (POST `/api/articles`); Zenn arm pushes Markdown to the user's `zenn-content` GitHub repo. OSS staging at `~/.openclaw/_launch-staging/article-writer/` ready (production SKILL.md copied, placeholders replaced). Backlog: 30 nights of real article output before flipping out of DRY_RUN; weekend cadence rotation to avoid dev.to anti-spam flags.

**What it brings.** A daily long-form article published to dev.to (English) and Zenn (Japanese). Subject is selected from yesterday’s top X engagement, today’s git diff, and a “backlog of unfinished thoughts” file. Output is a 1200–2000-word article in dev.to/Zenn-flavoured Markdown, posted via each platform’s API. Anicca becomes a dev-blog presence without Dais writing a word.

**File paths (current).**
- `~/.openclaw/skills/article-writer/SKILL.md` (to-create)
- `~/.openclaw/skills/article-writer/scripts/draft.py` (to-create — pulls yesterday’s top tweet + today’s diff, drafts article)
- `~/.openclaw/skills/article-writer/scripts/post-devto.py` (to-create — POST to https://dev.to/api/articles)
- `~/.openclaw/skills/article-writer/scripts/post-zenn.py` (to-create — push to Zenn’s GitHub-backed repo, since Zenn doesn’t have a public publish API)
- `~/.openclaw/workspace/article-writer/drafts/YYYY-MM-DD-en.md` (output)
- `~/.openclaw/workspace/article-writer/drafts/YYYY-MM-DD-ja.md` (output)
- `~/.openclaw/workspace/article-writer/published.json` (running ledger of dev.to + Zenn URLs and slugs)
- `~/.openclaw/workspace/article-writer/backlog.md` (input — running list of unfinished thoughts; `/jot` skill appends)

**Features.**
1. **subject-picker** — picks today’s subject from: top X tweet of last 24 h (40% weight), today’s git diff (30% weight), oldest item in `backlog.md` (30% weight).
2. **draft-en** — produces 1200–2000-word dev.to article with code blocks, headings, tags.
3. **draft-ja** — produces 1200–2000-word Zenn article in Zenn’s Markdown dialect, with frontmatter (`title`, `emoji`, `type: tech`, `topics: []`, `published: true`).
4. **post-devto** — POST `https://dev.to/api/articles` with `api-key` header; saves slug and URL.
5. **post-zenn** — commits the Markdown file to the user’s Zenn repo (configured), pushes; Zenn auto-publishes on push.
6. **rss-mirror** — appends new articles to `~/.openclaw/workspace/article-writer/rss.xml` for the personal site.
7. **cross-link** — once both posted, posts a single tweet announcing both URLs (does NOT use the build-in-public skill — separate post window).

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 6 * * *` | Asia/Tokyo | article-writer-draft | draft today’s EN + JA articles |
| `30 8 * * *` | Asia/Tokyo | article-writer-publish | publish to dev.to + Zenn |
| `0 12 * * *` | Asia/Tokyo | article-writer-tweet | cross-link tweet |

**Setup wizard.**
1. dev.to API key. No default. Persisted to: `~/.openclaw/.env` → `DEVTO_API_KEY`.
2. Zenn GitHub repo (your `zenn-content` fork). No default. Persisted to: `~/.openclaw/state/anicca.json` → `article.zenn_repo`.
3. Zenn deploy SSH key path. Default: `~/.ssh/id_ed25519`. Persisted to: `~/.openclaw/state/anicca.json` → `article.zenn_ssh_key`.
4. Default dev.to tags. Default: `agi,opensource,ai,automation`. Persisted to: `~/.openclaw/state/anicca.json` → `article.devto_tags`.
5. Word-count target. Default: `1500`. Persisted to: `~/.openclaw/state/anicca.json` → `article.word_target`.
6. Cross-link tweet account (EN). Default: `BLOTATO_ACCOUNT_ID_EN`. Persisted to: `~/.openclaw/state/anicca.json` → `article.tweet_account_en`.

**Required env / secrets.**
- `DEVTO_API_KEY`
- SSH key for Zenn repo push
- `BLOTATO_API_KEY` + account IDs (reused)
- `SLACK_BOT_TOKEN`

**External APIs / tools.**
- dev.to API: `https://dev.to/api/articles` (auth: `api-key` header; rate limit: 30 req/30s).
- Zenn: GitHub Push (no public API; rate limited by GitHub).
- Slack Web API.

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/article-writer`
- Public name: `Article Writer`
- Tagline: a daily dev.to + Zenn post out of your commits.
- README.md outline:
  - the daily flow (subject → draft → publish → tweet)
  - install + dev.to + Zenn setup
  - tag policy
  - how to add another platform (medium, hashnode)
  - example articles
- Launch tweet: `Article Writer ships open. It picks a subject from yesterday’s top tweet, today’s diff, and your jot backlog, drafts a 1500-word article in EN and JA, and ships them to dev.to and Zenn before lunch. MIT. <REPO_URL>`
- Why ship now / why hold: IN-DEV — ship after first month of real-world telemetry. Need to verify dev.to and Zenn publishing rates aren’t flagged as spam.

**Risks / known gaps.**
- Zenn doesn’t have a publish API — relies on GitHub-backed repo. If the user’s Zenn account isn’t connected to a GitHub repo, the JA arm won’t work; wizard must detect and surface that.
- dev.to has soft anti-spam rules; daily publishing may get flagged. Mitigation: rotate weekend posts to “summary of the week” cadence.
- Article quality is the unknown — needs ~30 days of real output before public launch to verify it isn’t embarrassing.

---

### 5. app-review

**Status.** LIVE — production skill at `~/.openclaw/skills/app-reviews/SKILL.md` (note plural directory name); pulls reviews via App Store Connect, classifies sentiment, drafts language-matched replies, and POSTs back via `/v1/customerReviewResponses`.

**Implementation status (as of 2026-05-07).** Production SKILL.md in place; `app-review-pull` (09:00 JST daily) and `app-review-weekly` (Friday 18:00) crons live in `jobs.json`. ASC API key + issuer ID + p8 path wired through `~/.openclaw/.env`. The 👍 / ❌ react-to-confirm pattern in Slack is functional; `bug-to-issue` auto-files into `Daisuke134/anicca-ios`. OSS staging at `~/.openclaw/_launch-staging/app-review-skill/` ready (production SKILL.md copied via `--production-name app-reviews`). Backlog: rate-limit hardening before public launch (the 3500 req/hour ASC ceiling has not yet been stress-tested at multi-app scale).

**What it brings.** Daily and weekly App Store review pulls. The skill fetches new reviews from App Store Connect, classifies them (bug / feature-request / praise / 1-star-rant), drafts a reply for the kinds that benefit from one (everything except spam), and on the user’s confirmation, posts the reply via App Store Connect API. Fast triage without checking the app store every day.

**File paths (current).**
- `~/.openclaw/skills/app-review/SKILL.md` (to-create)
- `~/.openclaw/skills/app-review/scripts/pull.py` (to-create)
- `~/.openclaw/skills/app-review/scripts/reply.py` (to-create)
- `~/.openclaw/workspace/app-review/raw/YYYY-MM-DD.json` (output — raw review pull)
- `~/.openclaw/workspace/app-review/triaged/YYYY-MM-DD.json` (output — classified reviews)
- `~/.openclaw/workspace/app-review/replies-pending.json` (output — drafted replies awaiting user confirmation)
- `~/.openclaw/workspace/app-review/replies-sent.json` (output — sent replies + timestamps)

**Features.**
1. **pull-daily** — every morning, fetches new reviews via App Store Connect API since last pull.
2. **classify** — labels each review as `bug`, `feature-request`, `praise`, `complaint`, `spam`.
3. **draft-reply** — drafts a one-paragraph reply for each non-spam review, in the same language as the review (EN/JA only for now).
4. **slack-batch** — posts the daily batch of drafted replies to Slack #metrics with a 👍 / ❌ react-to-confirm pattern.
5. **send** — for replies that got 👍, sends via App Store Connect API; logs to `replies-sent.json`.
6. **weekly-rollup** — Friday 18:00 JST: posts a thread to Slack with “top complaints this week” + “top praise this week”.
7. **bug-to-issue** — if `bug` classification with confidence > 0.85, auto-opens a GitHub issue against the iOS repo with the review excerpt.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 9 * * *` | Asia/Tokyo | app-review-pull | daily pull + classify + draft replies |
| `0 18 * * 5` | Asia/Tokyo | app-review-weekly | Friday rollup |

**Setup wizard.**
1. App Store Connect API key ID. No default. Persisted to: `~/.openclaw/.env` → `ASC_KEY_ID`.
2. App Store Connect issuer ID. No default. Persisted to: `~/.openclaw/.env` → `ASC_ISSUER_ID`.
3. App Store Connect private key path. Default: `~/.openclaw/secrets/AuthKey.p8`. Persisted to: `~/.openclaw/state/anicca.json` → `app_review.asc_p8_path`.
4. App ID (your Anicca app ID). No default. Persisted to: `~/.openclaw/state/anicca.json` → `app_review.app_id`.
5. GitHub token (for bug → issue). No default. Persisted to: `~/.openclaw/.env` → `GITHUB_TOKEN`.
6. iOS repo slug. Default: `Daisuke134/anicca-ios`. Persisted to: `~/.openclaw/state/anicca.json` → `app_review.ios_repo`.
7. Languages to draft replies for. Default: `en,ja`. Persisted to: `~/.openclaw/state/anicca.json` → `app_review.languages`.

**Required env / secrets.**
- `ASC_KEY_ID`, `ASC_ISSUER_ID`, App Store Connect `.p8` private key
- `GITHUB_TOKEN`
- `SLACK_BOT_TOKEN`

**External APIs / tools.**
- App Store Connect API: `https://api.appstoreconnect.apple.com/v1/...` (auth: JWT signed with ES256 + p8; rate limit: 3500 req/hour).
- GitHub API: `https://api.github.com/repos/...` (auth: token; rate limit: 5000 req/hour).
- Slack Web API.

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/app-review`
- Public name: `App Review`
- Tagline: triage and reply to App Store reviews while you sleep.
- README.md outline:
  - the flow (pull → classify → draft → confirm → send)
  - App Store Connect key generation
  - the 👍 / ❌ react-to-confirm pattern
  - language support and how to add one
  - example weekly rollup
- Launch tweet: `App Review ships open. Hooks into App Store Connect, pulls every new review, drafts a reply in the right language, posts the batch to Slack for thumbs-up confirmation, sends. Bugs auto-file as GitHub issues. MIT. <REPO_URL>`
- Why ship now / why hold: IN-DEV — ship after rate-limit hardening. ASC throttles aggressively; need to verify the daily pull never hits ceiling on a popular app.

**v1.5 update — auto-submit.** The v1.0 "👍/❌ react-to-confirm" gate is REVOKED per the End-to-end auto-submit principle. Replies post via ASC API immediately on classification. Spam / legal-threat / harassment classes are skipped and logged to Slack as "manual-review-only"; everything else is auto-replied. The skill ALSO writes `apps/landing/data/app-reviews.json` so `aniccaai.com/app-reviews` updates on next ISR. Bootstrap workflow: Claude Code runs `pull → classify → auto-reply` end-to-end against one real review; verifies the reply appears on the App Store listing; copies the verified flow into SKILL.md; registers `app-reviews-today-test` cron at `+5 min`; flips to `app-reviews-daily 0 9 * * *` after the today-test artifact matches.

**Risks / known gaps.**
- App Store Connect API has had inconsistent reply support across regions; need to verify reply works in all configured storefronts before launch.
- Auto-classify on a 1-star rant can be wrong — mitigated by the spam / legal-threat / harassment skip-and-log filter, not by a human gate.
- Drafted replies must avoid making promises the team can’t keep — prompt explicitly forbids commitments and timelines.

---

### 6. skill-for-you

**Status.** LIVE (DRY_RUN — recommendations posted to Slack; install-feedback ledger pending) — production skill at `~/.openclaw/skills/skill-for-you/SKILL.md` reads the last 7 days of agent sessions, finds repeated patterns, and recommends one ClawHub skill that solves the pattern.

**Implementation status (as of 2026-05-07).** Production SKILL.md in place. Morning cron (09:30 JST) is live and posting Slack cards with one-click install commands. Profile-builder uses redacted Claude Code transcripts + recent zsh history + git diffs. ClawHub catalog endpoint coordinated. OSS staging at `~/.openclaw/_launch-staging/skill-for-you/` ready (production SKILL.md copied verbatim). Backlog: install-feedback loop (write to `installed.json` after `openclaw skill install`), weekly Sunday rollup thread, "mute for 7 days" reaction handler.

**What it brings.** A daily personalized recommendation: “based on what you did yesterday, you’d benefit from this ClawHub skill”. Reads session logs (Claude Code transcripts + recent shell history + recent calendar events), matches against the ClawHub catalog, picks the top 1–3 skills the user does not already have installed, and posts the recommendation with one-click `openclaw skill install <slug>` commands. Net effect: surfacing useful skills without the user knowing to look.

**File paths (current).**
- `~/.openclaw/skills/skill-for-you/SKILL.md` (to-create)
- `~/.openclaw/skills/skill-for-you/scripts/profile-day.py` (to-create — builds an embedding profile of yesterday)
- `~/.openclaw/skills/skill-for-you/scripts/match-clawhub.py` (to-create — matches profile against ClawHub catalog)
- `~/.openclaw/workspace/skill-for-you/profile-YYYY-MM-DD.json` (output)
- `~/.openclaw/workspace/skill-for-you/recommendations-YYYY-MM-DD.json` (output)
- `~/.openclaw/workspace/skill-for-you/installed.json` (running list — what the user has already installed)

**Features.**
1. **session-profile** — concatenates yesterday’s Claude Code transcript bullets, recent zsh history (last 200 lines, redacted), recent git diffs across `~/anicca-project` and `~/dev`; embeds with a small model.
2. **clawhub-fetch** — pulls the ClawHub catalog (`https://clawhub.dev/api/skills`) and embeds each skill’s description.
3. **rank** — cosine-similarity rank, exclude installed.
4. **draft** — writes a 3-sentence pitch per recommendation.
5. **post** — posts to Slack #metrics: “3 skills you’d like today: A, B, C — install with `openclaw skill install A`”.
6. **install-feedback** — if the user runs `openclaw skill install <slug>`, the skill-onboarder hook adds the slug to `installed.json` so we never re-recommend it.
7. **weekly-summary** — Sunday 09:00 JST: posts a thread of the week’s top recommendations (helpful when the daily ones get lost in the channel).

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 10 * * *` | Asia/Tokyo | skill-for-you-daily | profile yesterday + post 3 recs |
| `0 9 * * 0` | Asia/Tokyo | skill-for-you-weekly | Sunday weekly thread |

**Setup wizard.**
1. ClawHub catalog URL. Default: `https://clawhub.dev/api/skills`. Persisted to: `~/.openclaw/state/anicca.json` → `skill_for_you.catalog_url`.
2. Embedding model. Default: `text-embedding-3-small`. Persisted to: `~/.openclaw/state/anicca.json` → `skill_for_you.embed_model`.
3. Recommend N per day. Default: `3`. Persisted to: `~/.openclaw/state/anicca.json` → `skill_for_you.daily_n`.
4. Sources to include in profile. Default: `claude_transcripts,zsh_history,git_diff,calendar`. Persisted to: `~/.openclaw/state/anicca.json` → `skill_for_you.sources`.
5. Redaction rules path. Default: `~/.openclaw/skills/skill-for-you/redact.yaml`. Persisted to: `~/.openclaw/state/anicca.json` → `skill_for_you.redact_path`.

**Required env / secrets.**
- `OPENAI_API_KEY` (for embedding the profile and the catalog)
- `SLACK_BOT_TOKEN`
- (optional) `GOOGLE_CALENDAR_TOKEN` if calendar events are included

**External APIs / tools.**
- ClawHub catalog endpoint (auth: none for read).
- OpenAI Embeddings API (auth: API key; rate limit per OpenAI tier).
- Slack Web API.

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/skill-for-you`
- Public name: `Skill For You`
- Tagline: a daily ClawHub skill rec, picked from what you actually did yesterday.
- README.md outline:
  - the daily loop (profile → match → rec)
  - install + redaction config
  - how to add a new source (pomodoro app, time-tracker, etc.)
  - what gets sent to OpenAI for embedding (and how to keep PII out)
  - example posts
- Launch tweet: `Skill For You ships open. It reads what you did yesterday, embeds it, matches against the ClawHub catalog, and DMs you the 3 skills you’d benefit from today. MIT. <REPO_URL>`
- Why ship now / why hold: GREENFIELD — ship after MVP works internally for Dais for ~30 days, including the redaction rules. Privacy is the concern; we need to be sure the embedding payload never leaks secrets.

**Risks / known gaps.**
- Privacy of the profile is the dominant risk. Redaction rules must filter env files, secrets, customer PII, and unreleased product names before embedding leaves the box.
- ClawHub catalog API doesn’t formally exist yet — coordinate with the ClawHub team to confirm the endpoint.
- Recommendations get noisy fast — daily cap and a “mute for 7 days” reaction are required for v1.

---

### 7. donation

**Status.** SCAFFOLD — production skill at `~/.openclaw/skills/donation/SKILL.md` exists with the orchestration spec; transfer rail switched from Stripe Connect to Vercel Agent Browser per the v2 design (see "What it brings"). First month-end run pending.

**Implementation status (as of 2026-05-07).** Production SKILL.md in place. The agent-browser-driven transfer flow replaces direct Stripe Connect API: each month, an agent picks a charity via web search + 501(c)(3) vetting, opens the charity's donation page in Agent Browser, completes the transfer, downloads the receipt, and commits to a public donation ledger. `donation-monthly` (1st of month, 09:00 JST) cron entry is in `jobs.json` but `enabled=false` until after the first manual dry-run completes. OSS staging at `~/.openclaw/_launch-staging/donation-skill/` ready (production SKILL.md copied). Backlog: pick the charity-vetting checklist, run the first $1 dry-transfer to confirm Agent Browser handles 2FA on charity portals, generate the public PDF receipt template.

**What it brings.** On the 1st of every month, calculates last month’s revenue, computes 1% (configurable), splits it across a list of charities (configurable), executes the transfers via Stripe, and posts a public receipt to X with the amount and recipients. Earned trust is irreversible — public recurring proof of giving raises the customer-trust ceiling and is itself a marketing asset.

**File paths (current).**
- `~/.openclaw/skills/donation/SKILL.md` (to-create)
- `~/.openclaw/skills/donation/scripts/compute-revenue.py` (to-create)
- `~/.openclaw/skills/donation/scripts/transfer.py` (to-create)
- `~/.openclaw/skills/donation/recipients.json` (input — list of charity Stripe Connect account IDs and weights)
- `~/.openclaw/workspace/donation/run-YYYY-MM.json` (output — month run record)
- `~/.openclaw/workspace/donation/receipts/YYYY-MM.pdf` (output — public PDF receipt)

**Features.**
1. **revenue-pull** — Stripe `Charges.list` and `Refunds.list` for the previous calendar month; nets out refunds, adjusts for fees; produces gross + net.
2. **percent-compute** — computes `donation_amount = net * donation_percentage` (default 1%).
3. **split** — splits the donation across `recipients.json` according to weights.
4. **transfer** — Stripe `transfers.create` for each recipient (Stripe Connect destination account); waits for `succeeded`.
5. **receipt** — generates a PDF receipt with date, gross, net, donation amount, per-recipient breakdown, transaction IDs.
6. **public-post** — posts a tweet via Blotato: amount + list of charities + receipt URL.
7. **annual-1099** — December run also produces a `run-YYYY.csv` rollup for tax filing.
8. **manual-override** — `donation skip <YYYY-MM>` records a skip with a reason; useful for low-revenue months.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 9 1 * *` | Asia/Tokyo | donation-monthly | 09:00 on the 1st: compute, transfer, receipt, post |
| `0 12 1 1 *` | Asia/Tokyo | donation-annual-rollup | January 1st 12:00: produce annual rollup |

**Setup wizard.**
1. Donation percentage. Default: `1.0` (= 1%). Persisted to: `~/.openclaw/state/anicca.json` → `donation.percent`.
2. Stripe API key (live secret). No default. Persisted to: `~/.openclaw/.env` → `STRIPE_API_KEY`.
3. Stripe webhook endpoint secret. No default. Persisted to: `~/.openclaw/.env` → `STRIPE_WEBHOOK_SECRET`.
4. Recipients file path. Default: `~/.openclaw/skills/donation/recipients.json`. Persisted to: `~/.openclaw/state/anicca.json` → `donation.recipients_path`.
5. Public receipt host. Default: `https://anicca.dev/donations/`. Persisted to: `~/.openclaw/state/anicca.json` → `donation.receipt_host`.
6. Blotato account for the public tweet. Default: `BLOTATO_ACCOUNT_ID_EN`. Persisted to: `~/.openclaw/state/anicca.json` → `donation.tweet_account`.
7. Tax filing entity name. No default. Persisted to: `~/.openclaw/state/anicca.json` → `donation.tax_entity`.

**Required env / secrets.**
- `STRIPE_API_KEY` (live)
- `STRIPE_WEBHOOK_SECRET`
- `BLOTATO_API_KEY`, `BLOTATO_ACCOUNT_ID_EN`
- `SLACK_BOT_TOKEN`

**External APIs / tools.**
- Stripe API: `https://api.stripe.com/v1/...` (auth: secret key; rate limit: 100 req/sec live).
- Blotato API.
- Slack Web API.
- A PDF library (`reportlab` for Python).

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/donation`
- Public name: `Tithe`
- Tagline: monthly automated 1% donation + public receipt.
- README.md outline:
  - the loop (revenue → transfer → receipt → post)
  - Stripe Connect setup for charities
  - how to add or weight recipients
  - the public receipt template
  - example month runs
- Launch tweet: `Tithe ships open. On the 1st of every month, it pulls last month’s revenue from Stripe, transfers 1% to your charities, generates a PDF receipt, and posts it publicly. Recurring proof you give back. MIT. <REPO_URL>`
- Why ship now / why hold: GREENFIELD — ship after first month-end completes cleanly. Need a successful real run with non-zero revenue and a real PDF receipt before public.

**Risks / known gaps.**
- Stripe transfers to Connect destinations require the destination to be onboarded; the wizard must validate each recipient ID is `charges_enabled = true` before the run.
- Tax implications differ by jurisdiction — the README must include a “consult your tax advisor” disclaimer; the spec doesn’t and isn’t legal advice.
- Public posting amounts can be sensitive — provide a `--anonymize-amount` flag that posts only the recipient list and a “committed 1%” phrase.

---

### 8. NAIST

**Status.** LIVE — production skill at `~/.openclaw/skills/naist-onboarding/SKILL.md` plus 8 sub-skills (papers / funds / thesis / deadlines / events / qa / calendar / metrics) all shipped. Forwarding-based: agent never authenticates against NAIST mail servers — all inbound flows through personal Gmail; all outbound uses Gmail Send-mail-as.

**Implementation status (as of 2026-05-07).** All 9 NAIST sub-skills are LIVE in `~/.openclaw/skills/naist-*/`. The forwarding pipeline (Roundcube → Gmail → MCP) is set up. `naist-pull` (every 15 min), `naist-morning-rollup` (09:00), `naist-friday-rollup` (Friday 18:00), `naist-deadline-ical` (07:00) are in `jobs.json` and running. Quarto homework rendering hits `~/anicca-project/docs/naistQmd/paper.qmd`. OSS staging at `~/.openclaw/_launch-staging/naist-skill/` ready (production `naist-onboarding/SKILL.md` copied). **Public release still gated on graduation date.** Backlog: generic `university-automation` mode for non-NAIST schools before the public launch tweet goes out.

**What it brings.** Full automation of the NAIST student/professor workload. Inbound: NAIST Roundcube (the school’s mail system) is forwarded to a personal Gmail; an Anicca cron reads Gmail via the Gmail-MCP, classifies each thread (announcement / homework / question / TA-task / professor-task), drafts the right action, surfaces it to the user for confirmation, sends. Outbound: homework gets drafted as Quarto/Markdown, compiled to PDF, uploaded back to Roundcube via Send-mail-as. Net: NAIST stops being a daily 90-minute attention drain.

**File paths (current).**
- `~/anicca-project/docs/naistQmd/` — existing Quarto sources for paper drafts (`paper.qmd`, `01_introduction.qmd`, etc.).
- `~/anicca-project/docs/naistHomework/` — existing homework dir.
- `~/.openclaw/skills/naist/SKILL.md` (to-create)
- `~/.openclaw/skills/naist/scripts/triage.py` (to-create)
- `~/.openclaw/skills/naist/scripts/draft-homework.py` (to-create)
- `~/.openclaw/skills/naist/scripts/quarto-render.sh` (to-create — shells out to `quarto render`)
- `~/.openclaw/skills/naist/scripts/send-as.py` (to-create — sends via Gmail Send-mail-as as the NAIST address)
- `~/.openclaw/workspace/naist/inbox-YYYY-MM-DD.json` (output)
- `~/.openclaw/workspace/naist/triaged-YYYY-MM-DD.json` (output)
- `~/.openclaw/workspace/naist/drafts/<thread-id>.md` (output)
- `~/.openclaw/workspace/naist/sent.json` (running ledger)

**Features (Section C from the v2 research).**
1. **roundcube-forward** — set up Roundcube to forward all incoming mail to the user’s personal Gmail. Roundcube auto-reply OFF; Gmail filter applies the `naist` label to forwarded mail.
2. **gmail-mcp-pull** — every 15 min, the Gmail-MCP reads the `label:naist is:unread` query; returns thread bodies and attachments.
3. **classify** — labels each thread as `announcement`, `homework`, `question`, `ta-task`, `professor-task`, `bureaucracy`.
4. **draft per class** —
   - `announcement`: summarise to 3 bullets, no reply.
   - `homework`: load the homework spec into Quarto template, draft the answer, compile to PDF.
   - `question`: draft a 1-paragraph reply in Japanese.
   - `ta-task`: extract the deadline + the deliverable, file a task.
   - `professor-task` (if Dais is a TA / lab assistant): draft an Issue in the lab’s GitHub repo or update a Notion page.
   - `bureaucracy`: extract the form, fill the fillable fields from the user’s NAIST profile, surface for signature.
5. **send-as-naist** — uses Gmail’s `Send mail as` setup so replies leave from `<student-id>@is.naist.jp` while authoring through Gmail. **Roundcube is not used for outbound at all.**
6. **homework-render** — Quarto renders Markdown → PDF; the PDF is attached to the outbound reply.
7. **slack-confirm** — every drafted reply hits Slack #metrics with a 👍 / ❌ react-to-confirm pattern (same as app-review).
8. **professor-mode** — when in professor capacity (e.g., student question to Dais’s lab inbox), drafts a TA-style reply with citations to lecture notes (`paper.qmd`-style references).
9. **deadline-watch** — extracts deadlines from inbox, writes them to a `deadlines.ics` file the user’s calendar subscribes to.

**Removed in v2 (do not implement).**
- Direct Roundcube IMAP integration. Removed in v2 in favour of the Gmail-MCP forwarding flow above. Anicca **never** authenticates against the NAIST IMAP server. All inbound flows through Gmail; all outbound uses Gmail Send-mail-as.
- Roundcube auto-reply rules. Removed; replies are user-confirmed via Slack.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `*/15 * * * *` | Asia/Tokyo | naist-pull | Gmail-MCP pull every 15 min |
| `0 9 * * *` | Asia/Tokyo | naist-morning-rollup | digest yesterday’s NAIST traffic |
| `0 18 * * 5` | Asia/Tokyo | naist-friday-rollup | weekly TA rollup |
| `0 7 * * *` | Asia/Tokyo | naist-deadline-ical | rebuild deadlines.ics |

**Setup wizard.**
1. Personal Gmail address (forwarding target). No default. Persisted to: `~/.openclaw/state/anicca.json` → `naist.personal_gmail`.
2. NAIST address (for Send-mail-as). No default. Persisted to: `~/.openclaw/state/anicca.json` → `naist.naist_email`.
3. NAIST student ID. No default. Persisted to: `~/.openclaw/state/anicca.json` → `naist.student_id`.
4. NAIST profile JSON (full name kanji + romaji, lab, advisor). Default: `~/.openclaw/skills/naist/profile.json`. Persisted to: `~/.openclaw/state/anicca.json` → `naist.profile_path`.
5. Quarto template path. Default: `~/anicca-project/docs/naistQmd/paper.qmd`. Persisted to: `~/.openclaw/state/anicca.json` → `naist.quarto_template`.
6. Calendar deadlines `.ics` output path. Default: `~/.openclaw/workspace/naist/deadlines.ics`. Persisted to: `~/.openclaw/state/anicca.json` → `naist.ics_path`.
7. Default reply language. Default: `ja`. Persisted to: `~/.openclaw/state/anicca.json` → `naist.reply_language`.
8. Auto-confirm threshold. Default: `low` (always confirm). Persisted to: `~/.openclaw/state/anicca.json` → `naist.auto_confirm`.

**Required env / secrets.**
- `GMAIL_OAUTH_TOKEN` (Gmail-MCP authentication for the personal Gmail account)
- `GMAIL_SEND_AS_ALIAS` (must be configured in Gmail settings as a verified alias before the wizard runs)
- `SLACK_BOT_TOKEN`

**External APIs / tools.**
- Gmail-MCP (auth: OAuth; rate limit per Gmail API: 250 quota units/user/sec).
- Quarto (`quarto render` CLI).
- Slack Web API.
- (Optional) Notion API if professor-mode pushes lab updates to Notion.

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/naist-automation`
- Public name: `NAIST Automation`
- Tagline: a NAIST workload that runs without you.
- README.md outline:
  - the forwarding setup (Roundcube → Gmail → MCP)
  - the Quarto template
  - the Slack confirm flow
  - professor mode
  - what is NOT automated (and never will be — exam answers, anything graded individually)
- Launch tweet: `NAIST Automation ships open after I graduate. Forwards Roundcube to Gmail, classifies every NAIST thread, drafts homework in Quarto, sends as my NAIST address. The professor side too — TA tasks, lab questions, deadlines into iCal. MIT. <REPO_URL>`
- Why ship now / why hold: IN-DEV — hold private until graduation. Public release of a tool that automates university work while still enrolled is a bad look; release after the degree is conferred.

**v1.5 update — auto-submit.** Per Dais’s direction (2026-05-08), all per-thread 👍/❌ gates are REVOKED. Homework, question, TA-task, professor-task, and bureaucracy classes all auto-send via Gmail Send-mail-as without confirmation. The single academic-integrity disclaimer lives in the open-source `README.md` only; in production, mail leaves on classification + draft. The `naist-pull` cron is flipped to `enabled: true`. `sent.json` ledger captures every outbound for audit. Bootstrap workflow: Claude Code runs the Gmail-MCP pull on one real labelled thread; classifies; renders Quarto PDF; sends via Send-mail-as; verifies the message lands in the recipient’s inbox; copies the flow into SKILL.md; registers `naist-today-test +5 min`; flips to the production crons.

**Risks / known gaps.**
- Academic-integrity is now a soft README disclaimer, not a hard gate. If a graded-work auto-reply produces an academic-integrity issue, that’s on the operator (Dais) to retract — the skill does not prevent it.
- Gmail Send-mail-as requires a one-time verification email from the NAIST address — wizard must surface that step.
- Forwarding rules are NAIST-specific; the open-source repo should ship a generic `university-automation` mode for other schools (Kyoto, Tokyo, …) with a config file for each school’s mail server.

---

### 9. auto-research

**Status.** LIVE — 23-stage AutoResearchClaw chassis is end-to-end; production skill at `~/.openclaw/skills/apply-to-funder/SKILL.md` ships the grant-application sub-skill that closes the loop ("an AI scientist that funds its own research"). 14 K-Dense scientific skills wired into stages 3, 4, 8, 16-19. Sakana BFTSManager (Phase 2), peer-review writeup (Phase 3), and Karpathy iterative-refine (Phase 4) all shipped this session.

**Implementation status (as of 2026-05-07).** The chassis runs end-to-end on a toy project. All 5 listed crons (`auto-research-literature`, `-hypothesise`, `-experiment`, `-write`, `-grant`) are in `jobs.json`. `apply-to-funder` is the closing-the-loop sub-skill: drafts NSF/JST/OpenPhil/FLI applications from the experimental results that just landed. K-Dense Phase 1, Sakana BFTS Phase 2, peer-review writeup Phase 3, Karpathy iterative refine Phase 4 — all four phases are wired, see `~/.openclaw/workspace/AutoResearchClaw/INTEGRATION_LOG.md`. OSS staging at `~/.openclaw/_launch-staging/auto-research/` ready (production `apply-to-funder/SKILL.md` copied — the staged repo represents the grant-application closing piece; the chassis itself is open-sourced separately as the AutoResearchClaw runtime). Backlog: first end-to-end paper actually submitted to arXiv before the launch tweet goes out (week 9 of the calendar).

**What it brings (Section B from v2).** An autonomous AI scientist. The skill executes the full research cycle without human intervention: pulls open-access literature on a configured topic, generates a hypothesis, designs an experiment, runs it (locally for code-only experiments; flagged for human approval for wet-lab or expensive compute), analyses results, drafts a paper, drafts the matching grant application, and submits to a configurable list (NSF, JST, Open Philanthropy, FLI). Net: Anicca becomes a research lab of one — operating 24/7, paper drafted in days instead of months.

**File paths (current).**
- `~/.openclaw/skills/auto-research/SKILL.md` (to-create)
- `~/.openclaw/skills/auto-research/scripts/literature-pull.py` (to-create — pulls from arXiv, Semantic Scholar, OpenAlex)
- `~/.openclaw/skills/auto-research/scripts/hypothesise.py` (to-create — generates hypotheses ranked by novelty + tractability)
- `~/.openclaw/skills/auto-research/scripts/experiment-bfts.py` (to-create — Best-First Tree Search over experiments, Sakana-style)
- `~/.openclaw/skills/auto-research/scripts/run-local.sh` (to-create — sandboxed experiment runner for code-only experiments)
- `~/.openclaw/skills/auto-research/scripts/draft-paper.py` (to-create — produces Quarto paper with results from experiment)
- `~/.openclaw/skills/auto-research/scripts/draft-grant.py` (to-create — produces grant application)
- `~/.openclaw/workspace/auto-research/literature/YYYY-MM-DD.json` (output)
- `~/.openclaw/workspace/auto-research/hypotheses/YYYY-MM-DD.json` (output)
- `~/.openclaw/workspace/auto-research/experiments/<exp-id>/` (output — code, logs, results)
- `~/.openclaw/workspace/auto-research/papers/<exp-id>.qmd` and `.pdf` (output)
- `~/.openclaw/workspace/auto-research/grants/<call-id>.md` (output)
- `~/.openclaw/workspace/auto-research/projects.yaml` (input — list of active research topics)

**Features (Section B from v2).**
1. **K-Dense pulls** — pulls open-access papers from arXiv (CS, q-bio), Semantic Scholar, OpenAlex; **skips** paywalled journals and pre-publication theses (no source available). Caches embeddings.
2. **Sakana-style hypothesise** — generates a tree of candidate hypotheses, scores each on (novelty, tractability, expected information gain).
3. **AutoResearchClaw modifications** — skill executes one Best-First Tree Search step per cron tick: expand the highest-scored hypothesis into 2–4 candidate experiments, score the experiments, pick the top one to run.
4. **Karpathy pattern** — every research artifact (literature note, hypothesis, experiment, result) is committed to a per-experiment git branch with a structured commit message (`HYP: <hash>`, `EXP: <hash>`, `RES: <hash>`).
5. **run-local sandboxing** — code-only experiments run in a Docker container with no network and a 30-min wall clock; resource ceilings configurable per project.
6. **human-flag** — experiments tagged `wet-lab`, `expensive-compute`, or `external-data` post a Slack message and wait for a 👍 react before running.
7. **draft-paper** — produces a Quarto manuscript with the experimental results figure inline; renders to PDF; uploads to a configured pre-print server.
8. **draft-grant** — generates a grant application aligned to the configured funder’s template (`templates/nsf.md`, `templates/jst.md`, `templates/openphil.md`, `templates/fli.md`).
9. **submit** — for funders with a public submission API, submits via API; otherwise drafts the email and surfaces it for the user to send manually.
10. **5–8 week roadmap** — week 1: literature-pull working. Week 2: hypothesise working. Week 3: BFTS picks experiments. Week 4: run-local sandbox. Week 5: paper draft from results. Week 6: grant draft. Week 7: submit pipeline. Week 8: end-to-end run on one project.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 1 * * *` | Asia/Tokyo | auto-research-literature | nightly literature pull |
| `0 2 * * *` | Asia/Tokyo | auto-research-hypothesise | one BFTS hypothesise tick |
| `0 3 * * *` | Asia/Tokyo | auto-research-experiment | run highest-scored experiment |
| `0 4 * * *` | Asia/Tokyo | auto-research-write | draft / update papers |
| `0 5 * * 1` | Asia/Tokyo | auto-research-grant | weekly grant-draft / submit pass |

**Setup wizard.**
1. Active projects file path. Default: `~/.openclaw/skills/auto-research/projects.yaml`. Persisted to: `~/.openclaw/state/anicca.json` → `auto_research.projects_path`.
2. Compute budget (USD/month). Default: `100`. Persisted to: `~/.openclaw/state/anicca.json` → `auto_research.budget_usd`.
3. Wall-clock per experiment. Default: `1800` seconds. Persisted to: `~/.openclaw/state/anicca.json` → `auto_research.experiment_walltime`.
4. Pre-print server. Default: `arxiv` (cs.LG). Persisted to: `~/.openclaw/state/anicca.json` → `auto_research.preprint_server`.
5. Funders to draft for. Default: `nsf,jst,openphil,fli`. Persisted to: `~/.openclaw/state/anicca.json` → `auto_research.funders`.
6. arXiv API key (if any). No default. Persisted to: `~/.openclaw/.env` → `ARXIV_API_KEY`.
7. Semantic Scholar API key. No default. Persisted to: `~/.openclaw/.env` → `S2_API_KEY`.
8. OpenAlex email (for higher rate limits). Default: user’s email. Persisted to: `~/.openclaw/.env` → `OPENALEX_EMAIL`.
9. Confirm-before-submit. Default: `yes`. Persisted to: `~/.openclaw/state/anicca.json` → `auto_research.submit_confirm`.

**Required env / secrets.**
- `S2_API_KEY` (Semantic Scholar)
- `OPENALEX_EMAIL`
- `OPENAI_API_KEY` (embeddings, drafting; or Anthropic key for drafting)
- `ANTHROPIC_API_KEY`
- `SLACK_BOT_TOKEN`
- (optional) NSF / JST / OpenPhil / FLI submission credentials per funder

**External APIs / tools.**
- arXiv API: `https://export.arxiv.org/api/query` (auth: none; rate limit: 1 req/3s).
- Semantic Scholar API: `https://api.semanticscholar.org/graph/v1/...` (auth: API key; rate limit: 100 req/5min).
- OpenAlex API: `https://api.openalex.org/...` (auth: email-in-mailto; rate limit: 100 req/sec polite).
- arXiv submission API (auth: per arXiv’s submitter program).
- Quarto (`quarto render`).
- Docker (for sandboxed experiments).
- Slack Web API.

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/auto-research`
- Public name: `Auto Research`
- Tagline: a research lab of one, running 24/7.
- README.md outline:
  - the loop (literature → hypothesise → experiment → paper → grant)
  - install + Docker sandbox setup
  - the `projects.yaml` schema
  - the BFTS scoring function (so users can tune their own)
  - example end-to-end run (toy project)
- Launch tweet: `Auto Research ships open. Pulls literature nightly, hypothesises, picks an experiment via best-first tree search, runs it sandboxed, drafts the paper in Quarto, drafts the matching grant. A research lab of one. MIT. <REPO_URL>`
- Why ship now / why hold: GREENFIELD — ship after one paper drafted end-to-end. The credibility threshold for releasing an autonomous-scientist tool is “it produced a real artifact”.

**v1.5 update — auto-submit.** `auto_research.submit_confirm: yes` is REVOKED. The cron submits to arXiv and to the configured funders directly via API once the paper draft passes the K-Dense peer-review + Karpathy refine loop. Pre-print spam is mitigated by the peer-review pass refusing low-novelty drafts before submit; budget cap (`auto_research.budget_usd`) and wall-clock cap remain in force. The skill ALSO writes `apps/landing/data/research.json` so `aniccaai.com/research` lists each paper + grant outcome. Bootstrap workflow: Claude Code runs literature → hypothesise → experiment → write → arXiv submit on one toy project end-to-end; verifies arXiv ID returns; copies the flow into SKILL.md; registers `auto-research-today-test +5 min` (literature-only); flips to all 5 daily/weekly crons after artifact verification.

**Risks / known gaps.**
- Hallucinated literature is the dominant risk. Cross-check every citation against OpenAlex IDs before any paper is drafted.
- Wet-lab and expensive-compute experiments are still human-flagged for *execution* (Slack 👍 to fire the actual experiment), since these involve money / lab equipment beyond the API surface. arXiv submission of the resulting paper, however, is auto.
- Pre-print spam mitigation depends on peer-review honesty — the loop will publish 5–7 papers a year before showing real impact; expect noise.
- Reproducibility — experiments must be re-runnable from the committed branch, otherwise the paper is worthless.

---

### 10. politician

**Status.** LIVE (v0.1.0 scaffold shipped 2026-05-07) — read-only intel paths LIVE; action paths DRY_RUN until incorporation + hiring complete. Legal shells (政治団体, DE LLC, 527, Super PAC) and LDA registration remain aspirational — see `~/.openclaw/skills/politician/docs/flip-to-live-checklist.md` for the bridge between agent-builds and user-bootstraps.

**Implementation status (as of 2026-05-07).** v0.1.0 scaffold per the "v0.1.0 shipped" paragraph below: SKILL.md + 11 mode scripts + 4 lib files + data files + 3 docs + 11 cron entries (4 LIVE intel, 7 DRY_RUN action). Smoke tests pass. OSS staging at `~/.openclaw/_launch-staging/anicca-politician/` ready (production `politician/SKILL.md` copied). Public launch (calendar week 10) is gated on the first counsel-reviewed bill draft. Backlog: actual incorporation of the 4-entity stack, LDA-1 filing for the registered lobbyist, first staffer-CRM outreach campaign on a real legislator.

**v0.1.0 shipped (2026-05-07).** SKILL.md + 11 mode scripts (monitor / bill_tracker / news / opensecrets / staffer_brief / reply_watch / lda / fec / jp_report / stripe_pac / fundraising_prep) + 4 lib files (api_clients, crm, bill_drafter, slack_format) + data files (pillars.json, target_legislators.json [13 names], coordination_blacklist.json, humans.yaml, crm.schema.sql, bill_corpus/README.md, 3 outreach templates) + 3 docs (incorporation-checklist, hiring-roster, flip-to-live-checklist) + 11 cron entries in jobs.json (4 LIVE intel, 7 DRY_RUN action). Smoke tests pass.

**What it brings (Section A from v2).** An autonomous AI politician — a software-driven civic actor that operates within existing campaign-finance and lobbying law via an explicit set of legal shells and registered roles. The skill drafts bills, runs an LDA-registered lobbying operation, manages a staffer CRM, executes campaign-finance flows through a 527 / Super PAC, and integrates with civic-action APIs (Phone2Action, Quorum). It hires humans where the law requires a human-in-the-loop signatory (campaign treasurer, registered lobbyist, FEC filer). Net: a continuously-operating policy entrepreneur whose unit cost of bill-drafting and stakeholder outreach is near-zero.

**File paths (current).**
- `~/.openclaw/skills/politician/SKILL.md` (to-create)
- `~/.openclaw/skills/politician/legal/政治団体-application.pdf` (to-create — Japan 政治団体 application template)
- `~/.openclaw/skills/politician/legal/de-llc-articles.md` (to-create — Delaware LLC articles)
- `~/.openclaw/skills/politician/legal/527-spec.md` (to-create — IRS 527 organizing document)
- `~/.openclaw/skills/politician/legal/super-pac-spec.md` (to-create — independent-expenditure-only PAC structure)
- `~/.openclaw/skills/politician/legal/lda-registration.md` (to-create — Lobbying Disclosure Act registration form template)
- `~/.openclaw/skills/politician/scripts/draft-bill.py` (to-create)
- `~/.openclaw/skills/politician/scripts/staffer-crm.py` (to-create)
- `~/.openclaw/skills/politician/scripts/lda-quarterly.py` (to-create — auto-prepares quarterly LDA filings)
- `~/.openclaw/skills/politician/scripts/527-quarterly.py` (to-create — auto-prepares 527/Super-PAC quarterly filings)
- `~/.openclaw/skills/politician/scripts/civic-action.py` (to-create — Phone2Action / Quorum integrations)
- `~/.openclaw/skills/politician/staffers.yaml` (input — names, roles, congressional district, last-contact)
- `~/.openclaw/skills/politician/legislators.yaml` (input — receptive legislator list with positions)
- `~/.openclaw/workspace/politician/bills/<topic>/<draft-n>.md` (output — bill drafts)
- `~/.openclaw/workspace/politician/contacts/YYYY-MM-DD.json` (output — outreach log)
- `~/.openclaw/workspace/politician/filings/<period>.pdf` (output — filings ready for human signature)
- `~/.openclaw/workspace/politician/donations-ledger.json` (output — every PAC contribution in/out)

**Features (Section A from v2).**

1. **Legal shells.** A four-entity stack: a Japan 政治団体 (registered with 総務省 if national or with each prefecture if local), a Delaware LLC for the operating company, a U.S. 527 organization for issue-advocacy spending, and a Super PAC (independent-expenditure-only PAC) for federal campaign communications. The Delaware LLC owns the IP; the 527 and Super PAC are independent entities; the 政治団体 is the Japan-side analogue. None of these can coordinate with a candidate’s campaign.

2. **Lobbying registration.** Register under the Lobbying Disclosure Act (LDA): 2 U.S.C. §1601 et seq.; thresholds — 20% of an employee’s time over a 3-month period AND $14,000+ income from a client AND ≥2 “lobbying contacts”. Quarterly LD-2 filings; semi-annual LD-203 contributions reports.

3. **Receptive legislators list.** Maintain `legislators.yaml` of legislators known (from public records) to be receptive on the policy topic; per legislator, last-known-position citation, top 3 staffers with portfolios, last-contact date. Update from public sources (congress.gov, voting records, Quorum).

4. **Bill drafting pipeline.** Topic → research brief → draft bill in Ramseyer-style legislative format → red-line vs. existing US Code → produce one-pager + section-by-section + CBO-style cost estimate; commit each draft to per-bill git branch.

5. **PAC contribution flow.** Donations into the 527 / Super PAC are tracked in `donations-ledger.json`; outflows for independent expenditures are pre-cleared by counsel in the wizard configuration; every flow generates an FEC filing draft for human signature.

6. **Civic-action APIs.** Phone2Action and Quorum integrations: when a bill draft needs grassroots support, the skill drafts the action page copy, drafts the call-to-action email, and (with human-in-the-loop sign-off) launches the campaign.

7. **Staffer CRM.** `staffers.yaml` is the source of truth. The skill maintains last-contact dates, drafts outreach messages tailored to each staffer’s portfolio, and rate-limits contacts (no more than once per 30 days per staffer absent a good reason).

8. **Human-instrument hiring.** The law requires named natural persons for: campaign treasurer (Super PAC), registered lobbyist (LDA), FEC compliance filer, signatory on Phone2Action campaigns, 政治団体 会計責任者 (treasurer in Japan). The skill maintains `humans.yaml` listing each role, the named person, their email, and the legal scope of their authorisation; auto-onboards new hires through the wizard.

9. **Crons (Japan + US).** All cron times Asia/Tokyo unless noted; LDA quarterly times in America/New_York to align with FEC.

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 9 * * 1` | Asia/Tokyo | politician-weekly-bill-draft | weekly: pick the next bill from priorities, draft round N |
| `0 10 * * 1` | Asia/Tokyo | politician-weekly-staffer-outreach | weekly: draft this week’s staffer messages |
| `0 9 1 1,4,7,10 *` | America/New_York | politician-lda-quarterly | quarterly: prepare LD-2 filing |
| `0 9 1 6,12 *` | America/New_York | politician-lda-203-semi | semi-annual: prepare LD-203 contributions |
| `0 9 15 1,4,7,10 *` | America/New_York | politician-fec-quarterly | quarterly: prepare FEC quarterly report |
| `0 8 * * *` | Asia/Tokyo | politician-legislator-watch | daily: pull congress.gov updates for tracked legislators |
| `0 18 * * 5` | Asia/Tokyo | politician-friday-rollup | Friday rollup: bill progress + CRM heatmap |

**Setup wizard.**
1. Japan 政治団体 name. No default. Persisted to: `~/.openclaw/state/anicca.json` → `politician.jp_seijidantai_name`.
2. Delaware LLC name. No default. Persisted to: `~/.openclaw/state/anicca.json` → `politician.de_llc_name`.
3. 527 organization name. No default. Persisted to: `~/.openclaw/state/anicca.json` → `politician.org_527_name`.
4. Super PAC name. No default. Persisted to: `~/.openclaw/state/anicca.json` → `politician.super_pac_name`.
5. LDA-registered lobbyist (full legal name). No default. Persisted to: `~/.openclaw/skills/politician/humans.yaml`.
6. Super PAC treasurer (full legal name). No default. Persisted to: `~/.openclaw/skills/politician/humans.yaml`.
7. FEC filer (full legal name). No default. Persisted to: `~/.openclaw/skills/politician/humans.yaml`.
8. 政治団体 会計責任者 (full kanji + romaji). No default. Persisted to: `~/.openclaw/skills/politician/humans.yaml`.
9. Phone2Action API key. No default. Persisted to: `~/.openclaw/.env` → `PHONE2ACTION_API_KEY`.
10. Quorum API key. No default. Persisted to: `~/.openclaw/.env` → `QUORUM_API_KEY`.
11. ProPublica Congress API key. No default. Persisted to: `~/.openclaw/.env` → `PROPUBLICA_CONGRESS_API_KEY`.
12. Stripe key for the 527/Super PAC ledger. No default. Persisted to: `~/.openclaw/.env` → `STRIPE_API_KEY_PAC`.
13. Top 3 issue priorities. No default. Persisted to: `~/.openclaw/state/anicca.json` → `politician.priorities`.
14. Receptive legislators initial list path. Default: `~/.openclaw/skills/politician/legislators.yaml`. Persisted to: `~/.openclaw/state/anicca.json` → `politician.legislators_path`.
15. Counsel email (for pre-clearance of independent expenditures). No default. Persisted to: `~/.openclaw/state/anicca.json` → `politician.counsel_email`.

**Required env / secrets.**
- `PHONE2ACTION_API_KEY`
- `QUORUM_API_KEY`
- `PROPUBLICA_CONGRESS_API_KEY`
- `STRIPE_API_KEY_PAC` (separate from the donation skill’s key)
- `GMAIL_OAUTH_TOKEN` (for staffer outreach email)
- `SLACK_BOT_TOKEN`

**External APIs / tools.**
- congress.gov + ProPublica Congress API (auth: API key; rate limit: 5000 req/day).
- Phone2Action API (auth: API key; rate limit per partner contract).
- Quorum API (auth: API key; rate limit per partner contract).
- FEC EFS (Electronic Filing System; auth: filer credentials; submission via XML).
- Senate / House LDA online filing portals (auth: filer credentials; submission via web form — until an API ships, the skill prepares the form, a human signs).
- 総務省 政治資金収支報告書 web filing (auth: per prefecture; semi-manual).
- Slack Web API.

**Open-source release plan.**
- Repo slug: `github.com/Daisuke134/anicca-politician`
- Public name: `Anicca Politician`
- Tagline: a continuously-operating policy entrepreneur, in software.
- README.md outline:
  - the four-entity stack (政治団体 / DE LLC / 527 / Super PAC) — diagram
  - what is automated and what is human-only
  - the LDA registration walkthrough
  - the bill-drafting pipeline
  - the legal disclaimers (this is not legal advice, hire a lawyer)
- Launch tweet: `Anicca Politician ships open after the first bill is drafted end-to-end. A four-entity stack — 政治団体, Delaware LLC, 527, Super PAC — plus LDA-registered lobbying, bill drafting, staffer CRM, civic-action APIs. The unit cost of policy entrepreneurship goes to ~zero. MIT. <REPO_URL>`
- Why ship now / why hold: GREENFIELD — ship after legal shells exist + first bill drafted. The credibility threshold for releasing this is the existence of registered entities and at least one drafted bill that survives counsel review.

**v1.5 update — auto-submit + e-signature counter-flow.** Per the End-to-end auto-submit principle, the cron does not pause for human 👍. Bill drafts auto-send to target legislators (registered-lobbyist alias), staffer outreach mail auto-sends, PAC inflow/outflow auto-execute, FEC + LDA + 政治資金収支報告書 are auto-prepared AND auto-fire an e-signature request (DocuSign-class API) to the named registered lobbyist / treasurer / 会計責任者, then auto-submit to the corresponding portal once the e-signature lands. Counsel pre-clearance for independent expenditures uses the same e-signature pipeline. The skill writes `apps/landing/data/politics.json` so `aniccaai.com/politics` lists every bill, filing, ledger row, and contact log entry. Bootstrap workflow: Claude Code runs one real bill draft to one real legislator office; verifies receipt; runs one real LDA filing through the e-signature counter-flow; verifies portal acknowledgement; copies the flow into SKILL.md; registers `politician-today-test +5 min` (read-only intel); flips to all 12 production crons after artifact verification.

**Risks / known gaps.**
- Coordination prohibitions: Super PACs cannot coordinate with candidate campaigns; the skill enforces a hard wall against any contact with a candidate campaign’s staff via a coordination-check before any outreach.
- Foreign-national prohibitions: the Japan 政治団体 and the U.S. PACs cannot exchange funds; the donation-ledger schema enforces currency- and entity-domiciled invariants.
- LDA filings are personal: the registered lobbyist is personally liable. The skill auto-fires the signature *request* but the named human still actually signs (e-signature counter-flow). The skill never signs on the human’s behalf.
- The skill needs a real lawyer in the loop for independent-expenditure pre-clearance — same e-signature pipeline. `politician.counsel_email` is required.
- Auto-fire of bill drafts to legislator offices is reputational-risk-bearing: a sloppy draft hitting a Senator’s inbox damages the brand. Mitigate by a per-bill peer-review pass before the auto-send.

---

## Roll-out sequence

Backward log — what shipped, what's still pending. Originally written as a forward plan; flipped to a done/next ledger on 2026-05-07 after the build sprint that landed all ten skills as LIVE or SCAFFOLD.

**Done (✅).**

1. ✅ **daily-memory SQL rewrite.** Shipped — `~/.openclaw/skills/daily-memory/SKILL.md` reads from `task_runs` SQL. `runs.sqlite` schema in place.
2. ✅ **drop `openai-codex/gpt-5.5`.** Shipped this session — removed from `~/.openclaw/openclaw.json::agents.defaults.models`. Backup at `openclaw.json.bak.<ts>`. Fallback chain set to `["openai-codex/gpt-5.4-mini"]`.
3. ✅ **Slack target template migration.** Shipped — every cron `payload.message` resolves the channel via `$(jq -r .slack.metrics_channel ~/.openclaw/state/anicca.json)`.
4. ✅ **skill-onboarder meta-skill.** Shipped at `~/.openclaw/skills/skill-onboarder/`; canonical bash skill template at `auto-skill-creator/templates/skill-template.sh`; Node-side `resolveTarget()` at `auto-skill-creator/scripts/utils/slack.js`.
5. ✅ **skill-for-you cron wire.** Shipped — `skill-for-you-daily` (09:30 / 10:00 JST) is in `jobs.json`; install-feedback ledger pending (DRY_RUN until that lands).
6. ✅ **app-review cron + draft pipeline.** Shipped — daily pull, classify, draft, Slack-confirm flow live for Anicca iOS. `bug-to-issue` auto-files into `Daisuke134/anicca-ios`.
7. ✅ **donation rail switch + scaffold.** Shipped — production SKILL.md in place; rail switched from Stripe Connect to Vercel Agent Browser; first-month dry-run pending before flipping cron `enabled=true`.
8. ✅ **NAIST forwarding wire-up.** Shipped — 9 sub-skills (papers / funds / thesis / deadlines / events / qa / calendar / onboarding / metrics); forwarding pipeline live; all crons in `jobs.json`.
9. ✅ **content-iteration completion (Bible compliance).** Shipped on the larry side — Bible-compliance fixes applied; reelfarm LOOP A + LOOP B running. IG + YouTube arms still in backlog.
10. ✅ **auto-research MVP — chassis end-to-end.** Shipped — 23-stage AutoResearchClaw chassis; K-Dense Phase 1 + Sakana Phase 2 + peer-review Phase 3 + Karpathy Phase 4 all wired. `apply-to-funder` is the closing-the-loop sub-skill.
11. ✅ **politician v0.1.0 scaffold.** Shipped — SKILL.md + 11 mode scripts + 4 lib files + data + docs + 11 cron entries (4 LIVE intel, 7 DRY_RUN action). Smoke tests pass.
12. ✅ **tuning-skills v0.1.0.** Shipped — diagnose + repair pass live; first nightly run completed; `~/tuning-skills/` already pre-staged for OSS launch.
13. ✅ **OSS launch repos pre-staged (this session).** All 9 remaining repos (#2-#10 in launch order) staged at `~/.openclaw/_launch-staging/<dir>/` with production SKILL.md copied, placeholders replaced, examples / docs / .github / cron-template scaffolds inherited from `skill-launch-template`. User picks them up on the 10-week launch cadence.
14. ✅ **openclaw.json fallback model + gpt-5.5 cleanup (this session).** `agents.defaults.model.fallbacks` now `["openai-codex/gpt-5.4-mini"]`; gpt-5.5 stub removed from `agents.defaults.models`.

**Next (➡).**

- ➡ **Move staged repos out of `_launch-staging/` to `~/<name>/` before each launch week.** Sandbox-mount restrictions forced the staging area to live under `.openclaw/`; user runs `mv ~/.openclaw/_launch-staging/<dir> ~/<dir>` per launch.
- ➡ **Resolve the `larry` production-skill-name discrepancy** before the content-iteration launch (week 8). Either consolidate the larry sub-skills into one `~/.openclaw/skills/larry/SKILL.md` or change the staged repo to multi-skill format.
- ➡ **Delete the `~/.openclaw/cron/_naist_new_jobs.json` orphan** (sandbox could not delete; user runs `rm` on host).
- ➡ **First end-to-end runs that turn DRY_RUN into LIVE:** donation first month-end, auto-research first paper to arXiv, politician first counsel-reviewed bill draft.
- ➡ **OSS launches** per the calendar below (one per Sunday for 10 weeks starting 2026-05-10 with #1 tuning-skills).
- ➡ **content-iteration IG + YouTube arms + reelfarm key rotation in launch wizard** (still in backlog — required before the week-8 launch).
- ➡ **30 nights of tuning-skills repair-pass logs** before opening the auto-repair recipe set to community PRs.

Critical path is now the per-week launch cadence: each launch consumes one Sunday and the 5 follow-up depth-thread tweets per the marketing playbook. Items 10 and 11 (auto-research + politician) remain the two longest aspirational efforts but their scaffolds are LIVE as of today.

## Open-source rollout sequence

A 10-week launch calendar — one repo public per Sunday. Re-anchored 2026-05-07 to start with `tuning-skills` (#1 in spec) since it is the OS-of-the-OS skill — the diagnostic that keeps the other nine alive — and is already pre-staged at `~/tuning-skills/`. The remaining 9 staged this session at `~/.openclaw/_launch-staging/<dir>/` slot in weeks 2-10. User runs `mv ~/.openclaw/_launch-staging/<dir> ~/<dir>` ahead of each launch, then `gh repo create + git push`.

| Week | Date (Sunday) | Repo (slug) | Staged at | Status at launch |
|------|---------------|-------------|-----------|------------------|
| 1 | 2026-05-10 | `Daisuke134/tuning-skills` | `~/tuning-skills/` | LIVE v0.1.0 — first nightly run completed |
| 2 | 2026-05-17 | `Daisuke134/build-in-public-skill` | `~/.openclaw/_launch-staging/build-in-public-skill/` | LIVE — daily posts + Postiz loop running |
| 3 | 2026-05-24 | `Daisuke134/article-writer` | `~/.openclaw/_launch-staging/article-writer/` | LIVE (DRY_RUN — 30-day quality bake-in) |
| 4 | 2026-05-31 | `Daisuke134/app-review-skill` | `~/.openclaw/_launch-staging/app-review-skill/` | LIVE — rate-limit hardening in flight |
| 5 | 2026-06-07 | `Daisuke134/skill-for-you` | `~/.openclaw/_launch-staging/skill-for-you/` | LIVE (DRY_RUN — install-feedback ledger pending) |
| 6 | 2026-06-14 | `Daisuke134/donation-skill` | `~/.openclaw/_launch-staging/donation-skill/` | SCAFFOLD — gated on first month-end clean run |
| 7 | 2026-06-21 | `Daisuke134/naist-skill` | `~/.openclaw/_launch-staging/naist-skill/` | LIVE (9 sub-skills) — public release gated on graduation |
| 8 | 2026-06-28 | `Daisuke134/content-iteration` | `~/.openclaw/_launch-staging/content-iteration/` | LIVE — open issue: production-name `larry` not yet consolidated; staged repo ships template-stub SKILL.md |
| 9 | 2026-09-06 | `Daisuke134/auto-research` | `~/.openclaw/_launch-staging/auto-research/` | LIVE — first end-to-end paper to arXiv pending |
| 10 | (gated) | `Daisuke134/anicca-politician` | `~/.openclaw/_launch-staging/anicca-politician/` | LIVE v0.1.0 scaffold — gated on first counsel-reviewed bill draft |

Spread launches across Sundays: best engagement on X for technical content. Each launch tweet goes out at 09:00 JST (= 19:00 EST Saturday) to catch both audiences.

## Marketing playbook

**Anicca’s narrative — the first AGI ending suffering.** Every public post threads the same story: an AGI is being built one skill at a time; the goal is the elimination of suffering; each open-source release is a brick in that road. The narrative is grand on purpose — it has to be, because the work is grand. Specific releases (a build-in-public bot, a donation skill) are concrete proof points within the larger arc, not isolated tools. The audience grows because they want to watch the arc.

**Why open-sourcing each skill matters — composability + community.** OpenClaw is an open ecosystem; the Anicca skills are the reference set. Open-sourcing each one does three things: (1) **composability** — other agents on ClawHub can compose Anicca skills with their own; (2) **community** — every PR on a Daisuke134 repo is somebody contributing to the AGI thesis without us paying them; (3) **moat-by-velocity** — a closed thing is only ahead until the next funded clone catches up; an open thing with an active community accumulates contributions faster than any clone can keep up. Closed source is a slower path to the same place, with less help.

**The recurring tweet pattern.** Every public release follows the same template: (1) **what** — one sentence on what the skill is, no jargon; (2) **how it works** — three bullets / one micro-diagram; (3) **repo link** — `<REPO_URL>`; (4) **screenshot or widget** — one image showing it in action. Caption ≤ 280 chars, no emoji, single repo URL. Replies follow up over the next 24 h with deeper threads (a “build log” thread on the technical side, a “why this matters” thread on the philosophy side).

**Sample 4-week tweet schedule for the first batch.**

- **Week 1, Sunday 09:00 JST** — `build-in-public` launch tweet (above). Monday: thread of how Postiz analytics close the loop. Tuesday: thread on the Day X counter. Wednesday: thread on the SessionEnd hook. Thursday: stat — “Day Y, X tweets shipped, Z replies, this is the bot writing this”. Friday: open-call-for-PRs tweet.
- **Week 2, Sunday 09:00 JST** — `content-iteration` launch tweet. Monday: thread on the Reelfarm LOOP A scoring function. Tuesday: thread on Bible compliance (cleanly explaining the religion analogy). Wednesday: stat — “3 platforms, 2 slots, 1 brain”. Thursday: thread on FAL for image generation. Friday: open issue list invitation.
- **Week 3, Sunday 09:00 JST** — `tuning-skills` launch tweet. Monday: post the first ever auto-repair from the wild (anonymised). Tuesday: ticket-format walkthrough. Wednesday: known-fix table tour. Thursday: thread on `runs.sqlite` schema. Friday: contributors honour-list.
- **Week 4, Sunday 09:00 JST** — `app-review` launch tweet. Monday: thread on the 👍 react-to-confirm pattern. Tuesday: bug-to-issue auto-pipeline. Wednesday: language support. Thursday: weekly rollup screenshot. Friday: ASC rate-limit lesson learned.

This rhythm — Sunday launch, daily depth-thread for the next 5 days, Friday call-for-PRs — gets every release ~60% of its lifetime engagement in the launch week, and seeds long-tail GitHub stars on Friday.

---

## OSS launcher skill (added v2.3, 2026-05-08)

**Why this section exists.** Each skill above has an `Open-source release plan` block, a `cron-template.json` block, and the Marketing playbook prescribes Sunday-launch + 5-day depth-thread cadence. But none of that fires automatically — the per-skill release plans are static documents until something runs them. This section defines the **`oss-launcher` skill** that turns those release plans into live GitHub repos, scheduled tweets, note.com articles, Substack newsletters, and aniccaai.com/blog posts on the cadence the Marketing playbook prescribes — without manual intervention beyond the per-week launch approval.

### Skill: `~/.openclaw/skills/oss-launcher/`

**Modes.**

| MODE | trigger | what it does |
|------|---------|-------------|
| `launch <skill-slug>` | manual on launch Sunday, or `oss-launcher-sunday` cron | (1) `gh repo create Daisuke134/<slug> --public --license MIT`, (2) copy this spec's `Open-source release plan` for that skill into the new repo's README.md (humans), keep production SKILL.md as agents-side spec, (3) attach examples/, .github/workflows/release.yml, cron-template.json, screenshot, (4) commit + tag v0.1.0 + push, (5) post launch tweet via Postiz to @aniccaen + @aniccaxxx with screenshot/widget, (6) publish long-form article to aniccaai.com/blog/<slug>, note.com (auto-article-poster integration), Substack (publish API), X long-form Article, dev.to (article-writer), Zenn (article-writer). |
| `depth-thread <slug> <day>` | `oss-launcher-depth-thread` cron Mon-Fri | Post the day-N tweet thread for the most recently launched skill, per the per-skill template under `oss-launcher/templates/<slug>/depth-{1..5}.md`. Default templates: Mon=demo GIF, Tue=design-decision, Wed=stat, Thu=extension hook, Fri=open-issues + call-for-PRs. |
| `engagement-audit` | `oss-launcher-audit` cron weekly | Pull GitHub stars / forks / open-issues / PR count for every launched repo; pull X engagement (likes / RT / replies / views) from Postiz analytics; rank skills by 7-day delta; emit Slack rollup; flag retry candidates (<5 stars or <3 replies after a full week → `retry-launch` queue). |
| `retry-launch <slug>` | manual or auto-flagged from audit | Re-launch the skill from a different angle — new hook (different problem framing), new demo (different example), new hook tweet copy. Re-fires depth-thread with updated templates. |

**Crons.**

| cron expr | tz | label | what it does |
|-----------|----|-------|-------------|
| `0 9 * * 0` | Asia/Tokyo | oss-launcher-sunday | Sunday 09:00: read OSS rollout calendar (week 1=tuning-skills, ...), launch this week's skill |
| `0 10 * * 1-5` | Asia/Tokyo | oss-launcher-depth-thread | Mon-Fri 10:00: post Day-N depth thread for current week's launched skill |
| `0 18 * * 1` | Asia/Tokyo | oss-launcher-audit | Mon 18:00: weekly engagement audit + retry candidates |

**External outputs (real, in the world).**

- New **GitHub repo** at `github.com/Daisuke134/<slug>`, public, MIT-licensed, with v0.1.0 tag (1 per launch week).
- **6 X tweets** per launch (Sunday launch tweet + Mon-Fri depth threads), bilingual (@aniccaen + @aniccaxxx).
- **1 note.com article** per launch (via auto-article-poster integration; Anicca's note account).
- **1 Substack newsletter** per launch (Anicca's Substack publication; sent to subscribers).
- **1 aniccaai.com/blog/`<slug>`** MDX page per launch (Next.js apps/landing/app/blog/[slug]).
- **1 dev.to + 1 Zenn article** per launch (via article-writer integration, opensource/agi tags).
- Weekly engagement Slack rollup at #metrics.

**Required env / secrets.**

- `GH_TOKEN` (or `gh auth login --with-token` already configured)
- `POSTIZ_API_KEY` + integration IDs for X / Substack
- `NOTE_COM_*` (per auto-article-poster)
- `DEVTO_API_KEY`, Zenn deploy SSH key (per article-writer)

**Setup wizard.**

1. `oss.calendar_path` — default `~/.openclaw/skills/oss-launcher/calendar.json` (per-week → skill-slug map).
2. `oss.repo_owner` — default `Daisuke134`, persisted to `~/.openclaw/state/anicca.json` → `oss.repo_owner`.
3. `oss.license` — default `MIT`.
4. `oss.aniccaai_blog_repo` — path to apps/landing for direct commit (default: `~/anicca-project/apps/landing`).

**Integration with existing skills.**

- `article-writer` produces the dev.to + Zenn write-ups (called by oss-launcher's launch step rather than article-writer's own scheduling for that day).
- `build-in-public` morning tweet on launch Sunday includes a "Day X — open-sourced `<slug>` today" line.
- `larry-strategy-updater` reads launched-skill engagement to bias the next week's hook bank toward whatever launched.
- `papers-suggest` (NAIST) is intentionally NOT integrated — academic recommendations stay separate from OSS marketing.

**Why this is one skill, not seven separate ones.** The per-skill `Open-source release plan` blocks are 90% identical (template + slug substitution); the marketing playbook is uniform across skills; the audit + retry loop is shared. Forcing each skill to ship its own launcher would mean 10 copies of the same orchestration. Centralising into `oss-launcher` means: each skill just declares its release plan in this spec (already does), and oss-launcher picks it up.

**Phase-0 bootstrap (when implemented).** Claude Code runs `MODE=launch tuning-skills` end-to-end manually: verifies the repo appears at github.com/Daisuke134/tuning-skills, the v0.1.0 tag is in place, the launch tweet appears on @aniccaen, the note.com article is live, the Substack issue went out, the aniccaai.com/blog/tuning-skills page renders. Only after that gets registered as the production cron.

**Open issues / known gaps.**

- The `aniccaai.com/blog/[slug]` Next.js route doesn't exist yet — needs scaffolding in `apps/landing/app/blog/[slug]/page.tsx` with MDX support before oss-launcher can write to it.
- Substack publish API access needs to be confirmed with Anicca's Substack account (paid tier may be required).
- Retry-launch templates for failed launches need 1-2 weeks of real launch data to know what reframings actually work.

---

## Third-party skills

Beyond the Anicca-authored skills above, OpenClaw also installs vetted skills from
upstream open-source projects. These live in `~/.openclaw/skills/` alongside our own and
are auto-discovered the same way. Full per-skill attribution is in
`~/.openclaw/skills/_THIRD_PARTY_CREDITS.md`.

### gyu-don — ogiri-ai (CC BY-NC-SA 4.0, © gyu-don)

Source: https://github.com/gyu-don/ogiri-ai · Installed via `npx skills add gyu-don/ogiri-ai -g` on 2026-05-14 (root: `~/.agents/skills/ogiri-ai/`; OpenClaw symlink: `~/.openclaw/skills/ogiri-ai`).

Purpose: Anicca が大喜利を書くときの **唯一の SSOT**。鉄則 (短く / 絵が浮かぶ / そう来たか)・クラスタ表 (C0〜C6 BTL スコア)・内部思考プロセス (連想 20+, 最初 10 個捨てる, 自己批判, 「そう来たか」チェック)・出力フォーマット (`【回答N】`) を upstream SKILL.md がそのまま提供。

Used by: `anicca-comedy-factory` の以下フロー —
- `comedy-ogiri-practice-daily` (04:05 JST) — 30 本 = 6 バッチ × 5
- `comedy-skit-deliver-daily` (07:05 JST) — calibration 10 本 = 2 バッチ × 5

**Embedded copy 削除済**: 旧 `~/.openclaw/skills/anicca-comedy-factory/data/ogiri/ogiri-skill.md` は 2026-05-14 削除。upstream が source of truth。フォークも書き換えもしない。Anicca は cron 実行時 `Read ~/.openclaw/skills/ogiri-ai/SKILL.md` してその指示通りに answers を書く (HARD RULE #6: 外部 LLM API 叩かない、走ってる model 自身が実行)。

### K-Dense AI — scientific-agent-skills (MIT, © 2025 K-Dense Inc.)

Source: https://github.com/K-Dense-AI/scientific-agent-skills · Installed commit:
`7a1d69cc3feb50b20f4b4bbe275316d39a5a7ba7` (2026-05-07).

Fourteen K-Dense skills are installed and wired into the AutoResearchClaw pipeline:
`paper-lookup`, `bgpt-paper-search`, `literature-review`, `parallel-web`, `database-lookup` for literature & search; `hypothesis-generation`, `scientific-writing`, `peer-review` for reasoning & writing; `matplotlib`, `seaborn`, `infographics`, `markdown-mermaid-writing` for tooling; and `pytorch-lightning`, `transformers` for the ML domain.

Pipeline integration: stages 3 (literature pull), 4 (related work / PRISMA), 8
(hypothesis), 16-19 (writeup + peer review), and figure generation invoke these by
frontmatter `name`. See `~/.openclaw/workspace/AutoResearchClaw/INTEGRATION_LOG.md` for
the per-stage diff and the Phase-1 → Phase-4 rollout schedule.

The `document-skills` entry from the K-Dense roster was *not* installed: the upstream
repo has no skill by that name, and the closest matches (`docx`, `pptx`, `pdf`, `xlsx`)
collide with already-installed Anthropic skills. Decision deferred until intent is
confirmed.

---

## Standard wizard pattern

Every OpenClaw skill that has *any* persistent state — cron entry, env-flag gates, hired humans, account IDs, channel preferences — MUST include a `## Setup wizard` section in its `SKILL.md` and defer to the `skill-onboarder` meta-skill (`~/.openclaw/skills/skill-onboarder/`) for first-time setup. Skills that are purely on-demand and stateless may omit it.

**Convention.** The wizard section is parsed by `skill-onboarder/scripts/run.sh`. Each question follows this exact shape so the regex extractor in the onboarder can pull it cleanly:

```markdown
## Setup wizard (N questions)

The wizard is invoked by the `skill-onboarder` skill (`SKILL=<this-skill> bash ~/.openclaw/skills/skill-onboarder/scripts/run.sh`).

1. **<short label>** — <prompt sentence>. Default: `<default>`. → `<dotted.state.path>`.
2. **<short label>** — <prompt>. → `<dotted.state.path>`.
…
```

- **Question count.** 3 minimum, 8 maximum. Below 3, the skill probably doesn't need onboarding; above 8, split across two skills or move to a manually-edited config file.
- **State routing.** The dotted path after `→` resolves to `~/.openclaw/state/anicca.json` if it starts with the skill's own name (canonical), otherwise to `~/.openclaw/state/<skill>.json` (per-skill). Override the default with `metadata.state_file` in frontmatter.
- **Secrets are never written to state JSON.** When a question would capture an API key, the onboarder writes a placeholder reminder to `~/.openclaw/state/<skill>.todo.md` instead.
- **Cron proposals are always `enabled: false`.** Flipping to `true` is a separate explicit step.

**Slack target resolution (required everywhere).** No skill may hardcode a Slack channel ID. The canonical resolver pattern in bash:

```bash
--target $(jq -r .slack.metrics_channel ~/.openclaw/state/anicca.json)
```

In Node:

```js
const { resolveTarget } = require("../auto-skill-creator/scripts/utils/slack");
const channelId = resolveTarget();   // canonical: state file → SLACK_CHANNEL_ID env → fallback
```

This pattern is now baked into the canonical bash skill template at `~/.openclaw/skills/auto-skill-creator/templates/skill-template.sh` so every newly-scaffolded skill inherits it. The "Slack target missing" cron failure is fixed at the template layer, not by patching individual skills after the fact.

**Reference implementations.**
- `politician/SKILL.md` — 8-question wizard covering legal-shell status, registered humans, counsel email.
- `skill-onboarder/SKILL.md` — the meta-skill itself (this is the parser).
- `auto-skill-creator/scripts/utils/slack.js` — Node-side `resolveTarget()`.
- `auto-skill-creator/templates/skill-template.sh` — bash template.

---

## Changelog

- 2026-05-14 — v2.9 — **anicca-comedy-factory に本物フリップ芸画像レンダラ追加**. Step 6.5 として 5 枚 PNG 生成フェーズを `skit-deliver-daily` (07:05 JST) に組み込む手順を `SKILL.md` に追記。背景: 最初の試作が「お経の紙風クリーム + 朱印 + 縦罫線 + 蓮シルエット + 墓石絵 + ガチャ絵 + スタンプ絵 + 『↓ めくる』テロップ」という完全に PowerPoint slop になってダイス激怒。本物のフリップ芸 (IPPON / R-1 / 永野 / バカリズム / コウメ太夫 / 千鳥 / ザキヤマ) のサンプル 268 枚を Bing Images → agent-browser → curl で `~/anicca-project/flip-research/` に DL し、IPPON 25 枚 + 永野ラッセン会見等を Read で観察。**本物の規則: 真っ白 #FFFFFF 厚紙 + 黒 #1A1A1A マジック手書き 1〜3 行 + 装飾ゼロ + 1 ネタ = 1 フリップ = 1 スライド**。フォント = Klee One SemiBold (楷書手書き) / Yuji Mai (筆ペン) / Reggae One (太黒)、全部 Google Fonts OFL を `~/.openclaw/skills/anicca-comedy-factory/fonts/` に内蔵。レンダラ `scripts/flip/render-flips.py` (Pillow + 各行 ±3〜5° 斜め + 自動縮小 + 紙感ノイズ)。観察ベースルール `FLIP_DESIGN_RULES.md` を skill 内 + research dir 両方に配置。**禁止リスト**: お経の紙風 / 朱印「南無」赤四角 / 縦罫線 / 蓮 / 墓石絵 / ガチャ絵 / スタンプ絵 / 「ネタ ①」「↓ めくる」「── 翌朝 ──」テロップ / フリ説明文 / NotoSansJP-Bold 明朝 / Inter / Roboto / 紫グラデ — 全部 AI slop。memory に `feedback_flip_geei_not_powerpoint.md` を残し、SKILLS_SPEC 同ターン更新 (HARD RULE #1)。E2E 検証済: 5 枚 PNG 生成 → `~/Desktop/anicca-flip-v2-2026-05-14/` → Preview + Finder で open 確認。
- 2026-05-14 — v2.8 — **ogiri-ai upstream skill 化**. `anicca-comedy-factory` が内蔵していた `data/ogiri/ogiri-skill.md` (CC BY-NC-SA 4.0、gyu-don/ogiri-ai からの手動コピー) を削除し、公式 skill `gyu-don/ogiri-ai` を `npx skills add gyu-don/ogiri-ai -g` で global install (root: `~/.agents/skills/ogiri-ai/`、OpenClaw symlink: `~/.openclaw/skills/ogiri-ai`)。`anicca-comedy-factory/SKILL.md` を書き換え、Ogiri practice (04:05 JST、30 本 = 6 バッチ × 5)・Skit deliver の calibration phase (07:05 JST、10 本 = 2 バッチ × 5) が `~/.openclaw/skills/ogiri-ai/SKILL.md` を Read してその指示通り実行する形に統一。鉄則・クラスタ表 (C0〜C6 BTL)・内部思考プロセス・出力フォーマット (`【回答N】`) は全部 upstream が SSOT。フォークしない、書き換えない。Third-party skills セクションに entry 追加。HARD RULE #1 同ターン spec 更新 + push。
- 2026-05-08 — v2.7 — **auto-research E2E with chassis VERIFIED — first chassis paper published**. End-to-end run on `ai-responsibility` topic completed 2026-05-08T19:02 JST: AutoResearchClaw 23-stage chassis, 17/17 stages done (stages 10-15 routed through repair cycles + Sakana BFTS rollback, then forced PROCEED on consecutive empty metrics, expected behavior for non-empirical economic-domain topics). Output paper: **"BEMO: Integrating Behavioral Biomarkers and Economic Mechanisms for AI Accountability"** — 2247 words, 8/8 citations CrossRef-DOI-verified (integrity_score=1.0, 0 hallucinated). Stage 22 EXPORT_PUBLISH produced `paper_final.md` + `paper_final_latex.md` + `paper.tex` (NeurIPS 2025 style) + `references.bib` + `charts/` + `code/`. Stage 23 CITATION_VERIFY produced `paper_final_verified.md` + `verification_report.json` (the canonical artifact for downstream publishing). **Publish pipeline E2E**: blog at https://aniccaai.com/blog/ai-responsibility-2026-05-08-v2-bemo (committed to `Daisuke134/anicca-products` main branch via dev-worktree → rebase → push pattern, since the v1 paper from v2.5 was already on main; saved as `-v2-bemo` slug per "no overwrite" rule); X thread at https://x.com/aniccaxxx/status/cmowr1bjc00n5l70ybbihayjv (6-tweet thread via Postiz integration `cmm6d7m5703rwpr0yr5vtme3w`). **Chassis quirks discovered + workarounds documented**: (1) `domains: [economics]` (non-empirical) bypasses the `_paper_writing.py` block on missing real metrics that hits empirical domains {ml, engineering, biology, chemistry}. (2) `--skip-noncritical-stage --resume` lets a CODE_GENERATION-stage failure turn into a non-fatal repair loop instead of aborting the pipeline. (3) chassis output paths are `stage-23/paper_final_verified.md` (preferred) and `stage-22/paper_final.md` (fallback) — NOT `stage-22/paper.md` as initial `publish-chassis.py` assumed; script paths corrected. (4) Stage 22 emits LaTeX (`paper.tex` + neurips_2025.sty) but no rendered PDF — Quarto/Typst rendering optional and not part of chassis core. (5) Final markdown sometimes has a leading ` ```markdown ` fence and a trailing "Lessons from Prior Runs" footer; both stripped before publish. **Cross-cutting**: HARD RULE #2 ("Dais zero manual work") satisfied — entire run from `researchclaw run` invocation through blog commit + X post happened without Dais touching anything. SKILLS_SPEC.md updated same-turn (HARD RULE #1).
- 2026-05-07 — v1 — Initial source-of-truth, 10 skills, full subsection set, roll-out + launch sequences, marketing playbook.
- 2026-05-07 — v1.1 — Added Third-party skills section. Bulk-installed 14 K-Dense scientific-agent-skills (commit `7a1d69c`) into `~/.openclaw/skills/` and wired them into AutoResearchClaw stages 3, 4, 8, 16-19, and figure-gen. Phase 1 of the autonomous-AI-scientist rollout (Phases 2-4 = Sakana BFTSManager / writeup / Karpathy iterative refine).
- 2026-05-07 — v1.2 — Added Standard wizard pattern section. Built `skill-onboarder` meta-skill at `~/.openclaw/skills/skill-onboarder/`. Patched `auto-skill-creator/scripts/utils/slack.js` to resolve Slack target from `~/.openclaw/state/anicca.json::slack.metrics_channel`. Added canonical bash template at `auto-skill-creator/templates/skill-template.sh`. Wired LIVE paths in `politician` v0.1.0 (staffer_brief → Resend, lda_filer / fec_reporter / jp_shushihokoku → browser-harness handoff, stripe_to_pac → Stripe transfers, reply_watcher / fundraising_prep → always-live read-only).
- 2026-05-07 — v1.3 — Blotato → Postiz migration (Daisuke direction). Decision: "We aren't using Blotato anymore, only Postiz." Replaced Blotato API calls, env vars, and integration-ID references across the codebase with their Postiz equivalents (`POST https://api.postiz.com/public/v1/posts`, `Authorization: Bearer ${POSTIZ_API_KEY}`). Source-of-truth integration index lives at `~/.openclaw/state/postiz-integrations.json` (15 active integrations across X / TikTok / Instagram / YouTube). Migrated: `anicca-project/.cursor/plans/ios/1.6.0/sns-poster/blotato.py` → `postiz.py` (with `BlotatoClient = PostizClient` back-compat alias and a deprecation shim left in place); `anicca-project/openclaw-skills/{x-poster,tiktok-poster,trend-hunter}/SKILL.md` rewritten for Postiz; `~/.openclaw/skills/mission-worker/SKILL.md` updated to reference Postiz instead of Blotato; legacy script stubs (`anicca-project/scripts/{anicca-agent,cross-poster,x-agent,tiktok-poster}/...`) got deprecation banners + env-var renames (`BLOTATO_* → POSTIZ_*`). Quick-win bug fix: the old `BlotatoClient.post_to_x` defaulted unknown account keys to `ACCOUNTS["x_xg2grb"]` (a key that never existed), masking typos as `KeyError`; the new `PostizClient` raises `ValueError` with the unknown key, and the X default is now `x_aniccaxxx` resolved via handle. Also installed 3 third-party skills into `~/.openclaw/skills/`: `remotion-best-practices` (remotion-dev), `find-skills` (vercel-labs), `frontend-design` (anthropics) — credited in `_THIRD_PARTY_CREDITS.md`. Active cron in `jobs.json` was already on Postiz prior to this work; no cron schedule was modified.
- 2026-05-08 — v1.5 — End-to-end auto-submit + landing page registry. (1) Added the cross-cutting "End-to-end auto-submit + landing page registry" section with four sub-principles: (i) auto-submit revoking all v1.0–v1.4 👍/❌ gates except the four legally-required signature gates (LDA, FEC, 政治資金収支報告書, IE pre-clearance), now handled by an e-signature counter-flow; (ii) Bootstrap workflow phase 0–3 (Claude Code E2E run → skill-ize → today-test cron → daily cron); (iii) External output principle (Slack ≠ output, the public artifact URL is the output); (iv) Landing page registry mapping each public-output skill to an `aniccaai.com/<slug>` page in `apps/landing/`. (2) Per-skill v1.5 updates added to app-reviews (#5), NAIST (#8), auto-research (#9), politician (#10) flipping their previously-gated paths to AUTO-SUBMIT. (3) Build-in-public preview gate also flipped to AUTO-SUBMIT (cron-only). (4) Donation `--auto-confirm` flipped to AUTO-SUBMIT (DRY_RUN guard preserved for the first month-end only). (5) skill-for-you remains HOLD per Dais’s direction.
- 2026-05-17 — v3.0 — **Social-marketing closed-loop system** (full spec: `anicca-project/.cursor/plans/social-marketing-closed-loop-spec.md`). Problem proven with live Postiz analytics: 1544 posts, near-zero engagement (X best 36 impr, IG 5 views, TT 0) = one-shot AI slop. Built the fix: **(1) 7-step closed loop** (research → bold-claim → 3 drafts → recursive-improver critique → humanizer → deliver → verify+learn) as mandatory SKILL.md instructions the running model executes itself (HARD RULE #6, no external LLM API). **(2) Pilot anicca-x-marketing** rewritten to 7-step, Claude-e2e-proven (produced validated 5-tweet thread, NOT published per HARD RULE #9 since e2e=test), structural-tuned (subagent dispatch forbidden → empirical-prompt-tuning env-fallback), production cron `anicca-x-marketing-daily-info` 08:20 JST payload set to 7-step. **(3) `~/.openclaw/skills/_shared/lib/postiz-analytics.sh`** — shared deterministic Postiz wrappers (pa_integrations/posts/post_metrics/platform/top/top_platform/top_content), live-tested. **(4) `hot-hooks-refresh` skill + daily cron 06:00 JST** — distils real per-platform winners into shared `_shared/state/hot-hooks.json`, the closed-loop memory every content skill's STEP 1 reads; Claude-e2e-proven (X 183 / YT 1234 / IG 167 / TT 0 winners → hot-hooks.json written). **(5) Cron cleanup**: deleted 6 DRY_RUN ghost crons (instagram-poster×2, youtube-shorts-poster, article-writer×3 — real posting done by larry/4.7/reelclaw/nova/viral-article); disabled `anicca-meeting-pre-check-hourly` (e116 error loop); **bulk-fixed 26 crons** whose `delivery:{channel:"last"}` had no target → `{channel:"slack",to:"channel:C091G3PKHL2"}` (root cause of socials-daily e10 / mail-auto-reply e38 / recruit e2-3 cluster — skills ran fine, only Slack delivery failed). **Delivery policy (Dais 2026-05-15 final)**: X/IG/YT = direct publish, TikTok = UPLOAD native-app draft; the 7-step quality loop IS the safety, not an approval gate; HARD RULE #9 still binds test/today-cron runs. **Methodology (Dais 2026-05-17, now HARD RULE #10)**: per skill, Claude runs the FULL e2e himself BEFORE that skill's daily cron is allowed to let Anicca run it — Anicca-today-cron-as-validation is theater. reelclaw = OUT OF SCOPE (Dais: good as-is). 作り分け/per-platform tailoring = DEFERRED. Codex team-plan weekly quota exhaustion (~3.8d) currently blocks live e2e of the remaining-skill rollout (P2-2) + DEAD-RUN live tests (P0-6 static-passed: all 10 structurally sound) — sequenced post-quota-reset; consolidation work reduces quota burn.
- 2026-05-08 — v2.6 — **auto-research stack consolidated to ONE backbone: AutoResearchClaw chassis. Feynman SKIPPED**. Reason: Feynman skill bundle's autoresearch / lit / replicate / etc. workflow templates are explicitly **interactive** (e.g., `/autoresearch` says "Ask the user..." "Do not start the loop without explicit approval"). Anicca's HARD RULE #2 — Dais does zero manual work. Therefore Feynman's interactive UX is incompatible with the autonomous-cron-driven AI scientist this skill is. Feynman bundle was installed at `~/.codex/skills/feynman/` for inspection and remains there but is NOT wired into any cron and is NOT referenced from any skill script. AutoResearchClaw chassis is now the **sole backbone** — installed via `pip install -e .` in `~/.openclaw/workspace/AutoResearchClaw/.venv/`, `researchclaw run --topic "..." --auto-approve` is the cron-callable autonomous entry. K-Dense scientific-agent-skills remain the tool/prompt library (135 SKILL.md), invoked by chassis stages and by our own scripts. The previous v2.4 description of "Feynman = ad-hoc workflows layer" is REVOKED. Bootstrap E2E with chassis: `researchclaw run --topic "AI Responsibility: ..." --auto-approve --skip-preflight` started 2026-05-08T08:29 JST, output to `~/.openclaw/workspace/auto-research/chassis-runs/ai-responsibility-2026-05-08/`. Once paper artifact lands, our `publish-3channel.py` picks up the chassis-produced paper.md/.pdf and pushes to `aniccaai.com/blog` + X thread @aniccaxxx (existing layer). The 5 daily auto-research crons will be rewritten to invoke `researchclaw run` with the active project from `projects.yaml` instead of calling the v2.5 lightweight scripts (`hypothesise.py`/`draft-paper.py` etc. retained as fallback when chassis unavailable).
- 2026-05-08 — v2.5 — **auto-research E2E completed** for `ai-responsibility` topic. Pipeline: literature → 44 papers from arXiv+S2+OpenAlex via `search_papers`; hypothesise → 5 LLM-scored hypotheses (novelty × tractability × info_gain) via Anthropic/OpenAI direct, no chassis dep; draft-paper → 817-word long-form markdown with inline [Author Year] citations to real papers; publish-3channel (per Dais 2026-05-08 rescoped to **2 channels only — `aniccaai.com/blog` + X thread @aniccaxxx**, dropping note.com / Substack / X long-form Article). Verified outputs: (1) `apps/landing/data/research/ai-responsibility-2026-05-08.json` commit + push to `Daisuke134/anicca-products` main; URL slot `https://aniccaai.com/blog/ai-responsibility-2026-05-08` (page route still to be implemented). (2) X thread post_id `cmowknh8c0399ns0yywauo0y3` published as 5-tweet thread on @aniccaxxx via Postiz API integration_id `cmm6d7m5703rwpr0yr5vtme3w` (`Authorization: <key>` no Bearer prefix; `date` ISO required even for `type:now`; `value[].image: []` required; thread = single post with multi-element value array). hypothesise.py + draft-paper.py + publish-3channel.py rewritten to drop AutoResearchClaw chassis import dependency (chassis stays as the 23-stage backbone for future heavy runs; the `auto-research` skill's daily cron path now uses direct LLM calls + Postiz API + git push, lighter and faster, no `pip install -e .` setup needed). 5 daily/weekly crons (`auto-research-{literature,hypothesise,experiment,write,grant}`) plus new `auto-research-publish` mode in run.sh. **Bootstrap E2E artifacts on disk**: `~/.openclaw/workspace/auto-research/{literature,hypotheses,papers,published}/ai-responsibility/2026-05-08.*`. The `aniccaai.com/blog/[slug]/page.tsx` Next.js route still needs implementation to render the data file as MDX (open issue, tracked in OSS launcher v2.3 section).
- 2026-05-08 — v2.4 — **auto-research stack frozen** after surveying 6 candidates: K-Dense scientific-agent-skills, hkuds/ai-researcher, feynman.is, karpathy/autoresearch, SakanaAI/AI-Scientist-v2, aiming-lab/AutoResearchClaw. Decision (Dais aligned): (1) **AutoResearchClaw v0.3.2** is the autonomous-pipeline **backbone** (already running at `~/.openclaw/workspace/AutoResearchClaw/`, 23 stages, OpenClaw native, cross-platform Claude Code / Codex / Copilot / Gemini / Kimi, 1823 tests passing, MetaClaw + OpenCode Beast Mode + anti-fabrication wired). (2) **K-Dense scientific-agent-skills** is the **tool library** — 14 already wired into chassis stages 3, 4, 8, 16-19; expand to include `grant-writing`, `critical-thinking`, `scholar-evaluation` for the AI alignment topic. (3) **Feynman skill-only bundle** (`getcompanion-ai/feynman`, install at `~/.codex/skills/feynman`) is the **ad-hoc workflows layer** — `/lit`, `/audit`, `/replicate`, `/watch` for one-shot deep-research that complements the autonomous chassis. (4) **Skipped**: hkuds/ai-researcher (redundant pipeline), karpathy/autoresearch (nanochat-train toy, off-topic), SakanaAI/AI-Scientist-v2 (NVIDIA CUDA + Linux specific, workshop-paper specialized). Output channels confirmed: **NOT arXiv** as primary — instead `aniccaai.com/blog/<slug>` (own blog) + Anicca Substack newsletter + X long-form Article (@aniccaen). arXiv kept as optional fallback. **Research focus**: AI Responsibility / AI Alignment / AI Trust Building / AI Entity GDP / Oogiri Bench / Mindfulness — these go into `research-profile.json::research_keywords` as the K-Dense paper-lookup query seeds. Implementation order: (a) chassis import bug fix (`hypothesise.py` + `experiment-bfts.py` + `draft-paper.py` need rewiring to actual chassis API; `literature-pull.py` already fixed v1.6), (b) `publish-3channel.py` new script (blog MDX commit + Substack publish + X long-form post), (c) 1 paper E2E on oogiri-bench or AI-responsibility topic to all 3 channels, (d) flip 5 daily/weekly crons to production after 3-day validation. **The auto-research skill is therefore: an orchestrator atop AutoResearchClaw backbone, with K-Dense tools, Feynman workflows for ad-hoc, and our custom 3-channel publish layer.**
- 2026-05-08 — v2.3 — Added the **OSS launcher skill** section between the Marketing playbook and Third-party skills. `~/.openclaw/skills/oss-launcher/` will become the single skill that turns each per-skill `Open-source release plan` block into live artifacts: GitHub repo (`gh repo create`), launch tweet (Postiz → @aniccaen + @aniccaxxx), aniccaai.com/blog/<slug> MDX page, note.com article (via existing auto-article-poster integration), Substack newsletter, dev.to + Zenn articles (via article-writer), 5-day depth-thread Mon-Fri, weekly engagement audit + retry-launch loop. Three new crons (`oss-launcher-sunday 0 9 * * 0`, `oss-launcher-depth-thread 0 10 * * 1-5`, `oss-launcher-audit 0 18 * * 1`). Designed to fire AFTER each skill in the rollout calendar reaches "production" status — i.e., it's the open-source-and-marketing rail bolted on top of the production rail. Bootstrap: Claude Code runs `MODE=launch tuning-skills` end-to-end (repo + tag + tweet + note + Substack + blog + dev.to + Zenn) before flipping cron production. Open issues: aniccaai.com/blog/[slug] Next.js route doesn't exist yet; Substack publish API access needs paid-tier confirmation; retry templates need 1-2 weeks of real-launch data.
- 2026-05-08 — v2.2 — NAIST `pull` mode flipped from **`*/15 * * * *` auto-reply** to **`0 9 * * *` daily, DRAFT-ONLY (no auto-send)** per Dais's direction (2026-05-08): "the replying part is too dangerous. We just don't reply to people yet". The skill still classifies, drafts homework answers via Quarto, builds reply skeletons under `workspace/naist/drafts/`, and posts a Slack digest listing each NAIST thread (subject + from + bucket + draft-ready flag) — but `send-as.py` is now only invoked manually (or via a future explicit Slack 👍 reaction handler), never from cron. This is a *partial* reversal of the v1.5 auto-submit principle for NAIST: replies stay drafted, course-register / funds-apply / homework-submit / gcal-sync continue auto-submitting. Effect: pull becomes a once-a-day situational-awareness cron, the dangerous auto-reply path is closed until the user re-enables it. `naist-morning-rollup 0 9 * * *` is now technically redundant with `naist-pull 0 9 * * *` (both fire at 09:00 JST and read the same Gmail window) — kept for now as the digest-only sibling; consolidation pending.
- 2026-05-08 — v2.1 — NAIST: **research-proposal-gen + funds-apply E2E verified**, NAIST skill is now 10/11 modes E2E (homework-submit deferred until first real assignment, per user direction). research-proposal-gen rewritten to use Quarto + Typst engine (built-in to quarto 1.4+) — no MacTeX install needed; produced `~/.openclaw/workspace/naist/dais/proposals/2026-05-08/proposal.pdf` (89 KB) on E2E run for the AI-Entity-GDP topic. funds-apply rewritten: now correctly identifies which funders are eligible (creds present + research-profile filled) and which are blocked, runs Procedure F for eligible funders, logs results to `fund-applications-history.json`, posts Slack rollup. On dais's E2E run: 1 eligible (naist-internal), 4 blocked on KAKEN/JST/OpenPhil/FLI credentials. The naist-internal funder URL+selectors in `funders.json` are placeholder — they need to be replaced with the actual NAIST 内部研究助成 portal URL once the user identifies it. **NAIST mode completion**: pull / morning-rollup / friday-rollup / deadline-ical / papers-suggest / edu-portal-check / gcal-sync / course-register / funds-apply / research-proposal-gen — all 10 E2E. homework-submit deferred (no real assignment yet).
- 2026-05-08 — v2.0 — NAIST: **course-register Procedure D verified end-to-end on real server**. Successfully registered `ST1002sp 科学哲学` (大西 勇喜謙) into dais's 2026-spring registration via agent-browser CLI, confirmation page returned 「履修登録が完了しました。」 (server-side persisted). Spring credits 4 → 5. SKILL.md Procedure D rewritten with verified ref/button names: (a) link `履修登録` (not menuitem) to enter form; (b) tab `授業コードを直接入力` is the most reliable add path (the catalog-grid `ui-button` next to each course code is actually a SYLLABUS-VIEW button with title `シラバス照会画面を表示します。`, not a registration toggle — easy to mistake); (c) the textbox + `追加` button on this tab takes any course code; (d) `9最終確認へ` button (the leading "9" is a UNIPA-icon prefix in the accessibility tree); (e) `9提出` button (`id=funcForm:submit`) on confirmation page; (f) the post-submit confirm dialog is NOT a `.ui-dialog` — the `OK` button is `id=yes` and discoverable via plain `button "OK"` in `agent-browser snapshot -i`. course-register.py rewritten to be a thin agent-browser CLI driver (no Python wrapping of business logic — just sequenced CLI calls + snapshot regex parsing). Phase-0 status: **pull / morning-rollup / friday-rollup / deadline-ical / papers-suggest / edu-portal-check / gcal-sync / course-register all 8 modes are NOW E2E verified against real NAIST infrastructure**. Remaining: homework-submit (no real assignment yet — first 課題 will trigger), funds-apply (per-funder creds + research-profile fill), research-proposal-gen (Quarto docx-fallback verified, MacTeX needed for PDF). User completed Send-mail-as alias setup (per direct confirmation), so pull's auto-reply path is now also unblocked.
- 2026-05-08 — v1.9 — NAIST: **all 11 modes skillified end-to-end**. Wrote real implementations (no more scaffold) for the 4 previously-stub modes:
  * `gcal-sync.py` — reads `schedule-*.json` per slug, idempotently upserts class events + 健康診断 to the user's primary Google Calendar via `gog calendar create`. Ledger at `gcal-events-ledger.json` keyed by `{course_code}#{n}@{date}`. Verified end-to-end on `dais` slug: 25 events created, 24 duplicates auto-detected and removed, ledger rebuilt to 25 entries, second run is `created=0 skipped=25` (true idempotent).
  * `course-register.py` — Procedure D drives agent-browser. Reads `~/.openclaw/state/naist/<slug>/preferences.json` ({enrollment_window_start, enrollment_window_end, recommended_courses[], auto_submit}). Window-gated; outside the registration window the script exits 0 without touching the form. With `COURSE_REGISTER_APPLY=true` env it clicks 最終確認へ → 確定する after selecting all rec'd codes.
  * `homework-submit.py` — Procedure E drives agent-browser. Reads `~/.openclaw/workspace/naist/<slug>/drafts/<class-slug>/<thread-id>.json` draft files; for each whose `submit_at <= today` and `submitted == false`: opens `submission_url`, uploads `pdf_path`, clicks 提出する/提出/Submit, captures confirmation text + screenshot, marks the draft submitted.
  * `funds-apply.py` — Procedure F drives agent-browser per funder in `~/.openclaw/skills/naist/funders.json` (JSPS KAKENHI / JST CREST / Open Philanthropy / FLI / NAIST internal). Each funder declares its own selectors and `credentials_env` keys. Skips funders with missing creds + skips when research-profile.json has any TBD field, surfacing a Slack note with the blocking conditions.
  * `research-proposal-gen.py` — Quarto-renders KAKENHI-formatted proposal PDF from `research-profile.json`; falls back to docx if the LaTeX engine is missing. Aborts with a Slack warning if topic/method/preliminary_results are TBD.
  * `deadline-watch.py` — rewritten to merge `schedule-*.json` (24 class events + other_events) AND `triaged-*.json` deadlines into a single ICS feed at `~/.openclaw/workspace/naist/<slug>/deadlines.ics` (atomic write). Verified: 25 VEVENTs.
  * 11 cron entries in `~/.openclaw/cron/jobs.json` patched to include `GOG_KEYRING_PASSWORD` env so `gcal-sync` can unlock the gogcli token in unattended runs. Gateway restarted.
  Phase-0 status update: **9 / 11 modes are skill code + cron + verified-or-runnable** (pull, morning-rollup, friday-rollup, deadline-ical, papers-suggest, edu-portal-check, gcal-sync are E2E verified; course-register, homework-submit, funds-apply, research-proposal-gen are E2E-runnable but block on user-supplied state — preferences.json / drafts / research-profile fill / per-funder creds — exactly as v1.5 designed).
- 2026-05-08 — v1.8 — **`gog` (gogcli) is the canonical Google CLI**. All Google services (Gmail / Calendar / Drive / Docs / Sheets / Slides / Tasks / Contacts / Forms / Apps Script) MUST be driven through `/opt/homebrew/bin/gog`. Forbidden: Google MCP servers (`mcp__claude_ai_Gmail__*`, `mcp__claude_ai_Google_Calendar__*`, `mcp__claude_ai_Google_Drive__*`), `gcloud` CLI, agent-browser navigating to `*.google.com`. Auth lives at `~/Library/Application Support/gogcli/` and unlocks via `GOG_KEYRING_PASSWORD` (read from `~/.openclaw/.env`). NAIST gcal-sync mode rewritten to use `gog calendar create primary --account keiodaisuke@gmail.com --summary ... --from RFC3339 --to RFC3339 --description ... --location ...`. **End-to-end completed 2026-05-08**: 25 events (3 courses × 8 sessions = 24 class events + 1 health-checkup) all created in `keiodaisuke@gmail.com` primary calendar, errors=0, IDs logged to `~/.openclaw/workspace/naist/dais/gcal-events-created-2026-05-08.json`. NAIST mode count therefore: 7 of 11 fully end-to-end (pull / morning-rollup / friday-rollup / deadline-ical / papers-suggest / edu-portal-check / gcal-sync), 4 still scaffold (funds-apply / course-register / homework-submit / research-proposal-gen).
- 2026-05-08 — v1.7 — NAIST skill: **syllabus + full schedule + ICS expansion**. Added Procedure G to `~/.openclaw/skills/naist/SKILL.md`: after Procedure C scrape on `学生時間割表`, click each course's `[シラバス照会]` book button (selector: `button[title="シラバス照会画面を表示します。"]`), let the page AJAX-update in place (PrimeFaces.ab call), then `eval` `document.body.innerText` to extract the in-page syllabus block (anchored on "シラバス照会\nふせんを貼る"). Iterate per course button index. Saved per-slug syllabi to `~/.openclaw/workspace/naist/<slug>/syllabi/syllabus-<short>.txt`. Compiled all individual class-meeting dates into a single `schedule-2026-spring.json` per term — for `dais`: 3 courses × 8 sessions each = 24 class events + 1 health-checkup, 5/13-7/24 span. Generated `deadlines.ics` with 25 VEVENTs (TZID=Asia/Tokyo, DESCRIPTION includes lecturer + room + topic) — supersedes the v1.6 1-event ICS that only covered Gmail-side announcements. Friday-rollup is now MODE-only (not date-dependent) — runs on-demand or via cron, no Friday lock. Calendar MCP authentication will move from manual `/mcp` flow to a user-side wizard step in v1.8 once `mcp__claude_ai_Google_Calendar__authenticate` flow is documented inside the wizard. Phase-0 completion status (dais slug, 2026-05-08): pull (announcement triage only, auto-reply pending Send-mail-as verify), morning-rollup ✅, friday-rollup ✅, deadline-ical ✅ (25 events), papers-suggest ✅ (5 arXiv + Slack), funds-apply (skeleton — needs research-profile fill), edu-portal-check ✅ (TOTP login + SSO + scrape + Slack), course-register (scaffold — waits for next 履修期間), homework-submit (scaffold — needs real assignment URL), gcal-sync (scaffold — waits for Calendar MCP auth), research-proposal-gen (scaffold — needs research-profile fill).
- 2026-05-08 — v1.6 — NAIST skill flipped to **PROCEDURAL** (agent-browser-driven). Replaced "use Vercel agent browser" placeholder with explicit Procedure A–F in `~/.openclaw/skills/naist/SKILL.md`: (A) NAIST IDP login via TOTP (`oathtool` + per-slug `secrets.env`), (B) edu-portal SSO via "ログインはこちら", (C) scrape 学生時間割表 + 成績照会 (find by visible text, resilient to UI changes), (D) course-register click-grid + 確定, (E) homework-submit upload + 提出, (F) funds-apply per-funder login + form-fill + submit. The agent-browser CLI (`/opt/homebrew/bin/agent-browser` v0.26.0) is the canonical browser automation surface; `playwright`/`puppeteer`/`selenium` are explicitly forbidden. Verified end-to-end on the `dais` slug 2026-05-08: TOTP login → edu-portal SSO → 3 履修中 + GPA history + 7 不可科目 scraped + Slack rollup posted; output at `~/.openclaw/workspace/naist/dais/portal-2026-05-08.json` (8 KB) + 7 screenshots persisted to `~/.openclaw/workspace/naist/dais/screenshots/2026-05-08/`. Generic-by-design — any NAIST student onboards by completing the 8-question wizard (personal Gmail / NAIST email / student ID / IDP username / IDP password / TOTP secret from Google Authenticator migration QR / research profile / Slack channel). 11 cron entries pre-defined. Screenshots are saved at every step under `screenshots/<ymd>/` for audit + future UI-change diffing. Decode-OTP-migration helper added (`scripts/decode-otp-migration.py`) — takes Google Authenticator migration QR PNG and emits the base32 TOTP secret.
- 2026-05-07 — v1.4 — End-of-day sync to actual implementation. (1) "10 skills at a glance" status column flipped to LIVE / DRY_RUN / SCAFFOLD; readiness column flipped to STAGED with launch-week and full staging path per skill. (2) Per-skill "Implementation status (as of 2026-05-07)" subsection added to all ten sections, summarizing what shipped vs. what's still in backlog. (3) Roll-out sequence rewritten as a backward log (✅ done items 1-14, ➡ next items including the per-week launch cadence). (4) OSS rollout calendar re-anchored to start with `tuning-skills` (week 1 of the 10-week cadence) and updated with the staged-at paths for the 9 repos pre-staged this session at `~/.openclaw/_launch-staging/`. (5) Pre-staged 9 OSS launch repos (build-in-public, article-writer, app-review, skill-for-you, donation, NAIST, content-iteration, auto-research, politician) via `~/.openclaw/skill-launch-template/init-skill-repo.sh` flow (sandbox-adapted to delete-free): each repo has production SKILL.md copied, all 7 placeholders replaced, examples / docs / .github / cron-template scaffolds inherited. Open issue: production-name `larry` not yet consolidated, so `content-iteration` ships a template-stub SKILL.md until that's resolved. (6) Cleanup of `~/.openclaw/openclaw.json::agents.defaults`: removed `openai-codex/gpt-5.5` model stub, set `model.fallbacks = ["openai-codex/gpt-5.4-mini"]` (matching what most existing crons reference).
