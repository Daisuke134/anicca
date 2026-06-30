---
feature: earn-shared-skeleton
phase: 1a
mode: lean
sources:
  - anicca-project/docs/superpowers/specs/2026-06-30-earn-slots-daily-loop-master.md (Shared Earn-Core Skeleton section, 2026-07-01)
  - Anthropic Nov 2025 spec-gaming study
  - VOYAGER (arXiv 2305.16291) skill-library-as-code
  - Reflexion (arXiv 2303.11366) verbal-RL post-mortem
  - EvoAgentX 2026 survey (arXiv 2508.07407) Three Laws
---

# Behavioral Specification — earn-shared-skeleton

## Purpose

Every earn slot (gig, clip, video, affiliate, bounty, future slots) inherits ONE shared library in
`~/anicca/skills/_shared/` instead of hand-coding healthcheck/ROI/adversary/escalation per slot.
This stops the bleed where every break (today: "Not logged in", trust dialog, hook errors, restart-loop)
requires manual hand-fix, and lets new slots ship by inheritance.

## Goal (= "Done" condition)

After this feature is converged: ANY earn slot's launchd plist invokes
`~/anicca/skills/_shared/loop-healthcheck.sh <slot>` (= no per-slot healthcheck file), the slot's
cron-prompt calls `loop-roi.sh` at end-of-pass, an INV-11 archive trip is auto-detected, and a daily
03:00 fresh-context adversary runs per slot. Human is touched exactly once: when `escalate.sh` posts
a `label=escalation` GitHub issue that triggers a Telegram notification.

## Scope (in vs out)

**In scope** — the 9 shared scripts in `~/anicca/skills/_shared/`:
`loop-healthcheck.sh` · `loop-roi.sh` · `loop-improve.py` · `loop-scale.sh` · `loop-propose.sh` ·
`cross-learn-read.sh` · `cross-learn-share.sh` · `adversary-daily.sh` · `escalate.sh`.
Plus: the per-slot launchd plist template that invokes them, and the per-slot cron-prompt template
that ends each pass by calling them.

**Out of scope** — migrating existing slot code (= task #14, downstream feature). This spec
defines the library; migration is a separate sprint per slot.

## EARS-Format Functional Requirements

### Group A — Self-Heal (`loop-healthcheck.sh`)

- **REQ-A1** WHEN launchd fires `loop-healthcheck.sh <slot>` AND the tmux session
  `anicca-<slot>-core` does not exist, THE SYSTEM SHALL invoke `<slot>-cli.sh --restart` and append
  a `tmux-dead → restart` entry to `~/.openclaw/logs/<slot>-core-healthcheck.log`.

- **REQ-A2** WHEN `~/loops/<slot>/.last-pass` exists AND its mtime is older than 90 minutes, THE
  SYSTEM SHALL invoke `<slot>-cli.sh --restart`.

- **REQ-A3** WHEN a pane capture of `anicca-<slot>-core` contains the substring
  `Not logged in · Please run /login`, THE SYSTEM SHALL: (a) `tmux send-keys "/login" Enter`,
  (b) wait 6s, (c) capture pane and extract the OAuth `https://claude.com/cai/oauth/authorize…`
  URL via regex, (d) call `escalate.sh <slot> needs-login <url>` so the URL surfaces to Dais's
  Telegram via the watcher cron — Dais clicks once and the next healthcheck tick resumes the pass.

- **REQ-A4** WHEN a pane capture contains the substring
  `Quick safety check: Is this a project you ... trust`, THE SYSTEM SHALL `tmux send-keys "1" Enter`
  to dismiss the trust dialog.

- **REQ-A5** WHEN a pane capture contains the substring
  `PreToolUse:Bash hook error  node:internal/modules/cjs/loader`, THE SYSTEM SHALL: (a) grep the
  hook script for the failing `require(...)` path, (b) run `npm install -g <module-name>`,
  (c) re-tick (= return without restart so the next tmux pass sees the fix).

- **REQ-A6** WHEN a pane capture contains `API error · Retrying in` AND a numeric `attempt N/10`
  where N ≥ 5, THE SYSTEM SHALL `tmux send-keys "/model haiku-4-5" Enter` to drop to the cheapest
  available model and continue.

- **REQ-A7** WHEN the tmux session is alive but `CronList` (queried via a short send-keys probe)
  returns zero jobs whose prompt mentions `earn/<slot>`, THE SYSTEM SHALL re-inject the slot's
  STARTUP prompt via `send-keys` (= cron registration was dropped post-`/clear` etc).

- **REQ-A8** WHEN `~/loops/<slot>/.restart-log` shows ≥ 5 restart entries within the last 3600
  seconds, THE SYSTEM SHALL stop attempting restarts AND call
  `escalate.sh <slot> backoff-cap "<last 5 audit verdicts>"`.

- **REQ-A9** THE SYSTEM SHALL detect at most ONE failure mode per healthcheck tick (= if A1 matches,
  A2..A8 are not also fired in the same tick; serialization prevents thrash).

### Group B — ROI Tracking (`loop-roi.sh`)

- **REQ-B1** WHEN any slot's pass completes, THE SYSTEM SHALL append exactly one JSON line to
  `~/loops/<slot>/roi.jsonl` containing:
  `{ts, slot, pass_id, tokens_in, tokens_out, tokens_total, token_cost_jpy, jpy_earned_this_pass,
   usdc_earned_this_pass, wall_seconds, roi_7day_jpy, roi_30day_jpy, actions_taken}`.

- **REQ-B2** THE SYSTEM SHALL compute `token_cost_jpy` as
  `tokens_in × $3/M + tokens_out × $15/M (Sonnet+Opus mix per model_breakdown) × FX_USDJPY` —
  the per-model PUBLIC API rate, never zero (TRAP-5 token-rich illusion).

- **REQ-B3** THE SYSTEM SHALL compute `jpy_earned_this_pass` as the sum of `amount` over rows
  appended to `~/loops/<slot>/earnings.jsonl` since the previous pass, where each row's
  `{receipt_id, payer, amount, ts}` came from the platform's settled-payout API call (INV-8).

- **REQ-B4** WHEN cumulative `tokens_total` since the slot's first-ever pass exceeds 5 ×
  cumulative `jpy_earned`, THE SYSTEM SHALL create `~/loops/<slot>/loop.disabled`. The slot's
  launchd plist SHALL check this file before each healthcheck tick and skip when present.
  (= INV-11 token kill-switch.)

- **REQ-B5** `roi_7day_jpy` SHALL be `Σ(jpy_earned − token_cost_jpy)` over the prior 168 hours.
  `roi_30day_jpy` over 720 hours. Window-boundary truncation: rows older than the window are
  excluded; partial-window passes (< 7 days of data) are not used to gate scale-up.

### Group C — Self-Improve (`loop-improve.py`, Reflexion verbal-RL)

- **REQ-C1** WHEN a pass's B3 LEARN step detects an outcome
  `(accepted|rejected|low_rating|needs_human|unsustainable|delivered_no_収)` for an applied
  request, THE SYSTEM SHALL append `{ts, requestId, category, outcome, reason, lesson,
  evidence_id}` to `~/loops/<slot>/lessons.jsonl`. `evidence_id` SHALL quote raw tool output
  (URL of the offer page, payout_id, screenshot path) — not a paraphrase (TRAP-4 faithfulness).

- **REQ-C2** WHEN `passprep.py` computes `do_improve = true`, THE SYSTEM SHALL invoke
  `loop-improve.py <slot>` which: (a) reads `tail -50 lessons.jsonl`, (b) reads previous
  `strategy.json`, (c) produces a candidate `strategy.json.next`.

- **REQ-C3** BEFORE `strategy.json.next` overwrites `strategy.json`, THE SYSTEM SHALL invoke
  `vcsdd-adversary` (fresh-context Opus subagent) on the diff. IF the adversary verdict is FAIL,
  THE SYSTEM SHALL discard `strategy.json.next` and append the failure to `lessons.jsonl` so the
  next pass re-attempts with the failure as input. (= INV-10 fresh-context before mutation merge.)

### Group D — Cross-Learn (`cross-learn-{read,share}.sh`)

- **REQ-D1** AS PRE-STEP of every pass, THE SYSTEM SHALL run
  `gh issue list --label <slot>-lesson --label earning-skill-proposal --limit 20` and emit the
  result as JSON to stdout for the cron-prompt to fold into its judgment.

- **REQ-D2** WHEN a pass detects a novel lesson (= a `{requestId, outcome}` tuple not present in
  `~/loops/<slot>/shared-lessons.jsonl`), THE SYSTEM SHALL `gh issue create --label <slot>-lesson`
  with body `{category, outcome, reason, lesson, evidence_id}` AND append `{ts, requestId,
  outcome, issue_url}` to `shared-lessons.jsonl`.

- **REQ-D3** IF `gh` returns non-zero exit code, THE SYSTEM SHALL log a warning and continue
  the pass; gh failure SHALL never abort.

### Group E — Self-Verify (`adversary-daily.sh`)

- **REQ-E1** AT 03:00 local time daily for each slot, THE SYSTEM SHALL spawn a fresh-context
  `vcsdd-adversary` (Opus) subagent against `~/anicca/.vcsdd/features/<slot>/` reading
  disk-only artifacts (= no shared chat context with the slot's builder).

- **REQ-E2** WHEN the adversary verdict is FAIL, THE SYSTEM SHALL spawn `vcsdd-builder` (Sonnet)
  with the findings, then re-spawn a fresh adversary. THE SYSTEM SHALL loop up to 5 rounds.

- **REQ-E3** WHEN 5 rounds elapse without PASS, THE SYSTEM SHALL call
  `escalate.sh <slot> adversary-stalled "<round-5 verdict json>"`.

### Group F — Escalate (`escalate.sh`, the only human gate)

- **REQ-F1** WHEN `escalate.sh <slot> <reason> <evidence>` is called, THE SYSTEM SHALL:
  (a) `gh issue create --label escalation --title "[<slot>][<reason>] short summary" --body <evidence>`,
  (b) write the issue URL to `~/loops/escalation-log.jsonl`,
  (c) post the issue URL to the configured Telegram bot endpoint.

- **REQ-F2** THE SYSTEM SHALL deduplicate by `(<slot>, <reason>, evidence_hash)` so the same
  underlying failure does not create multiple issues within 24 hours.

### Group G — Skill Provenance & Self-Write Ban

- **REQ-G1** Every skill under `~/anicca/skills/earn/<slot>/` SHALL have a `manifest.json` with
  fields `{origin: "self" | "github-issue:<owner>/<repo>#<n>" | "fork-of:<sha>", first_seen_ts,
  last_audit_round, cumulative_tokens, cumulative_jpy_earned}`. (= INV-12.)

- **REQ-G2** The skill's own code SHALL NOT write to its own `manifest.json`. The slot runner
  (= the claude-p in tmux invoking the skill) SHALL write. The skill SHALL emit events to a
  named pipe / file `events.jsonl` and the runner SHALL parse + append. (= INV-13.)

### Group H — Novelty Quota (TRAP-3 curriculum collapse)

- **REQ-H1** `passprep.py` SHALL enforce: of `max_apply_per_pass`, at least
  `ceil(0.1 × max_apply_per_pass)` rows must target a `(category, platform)` tuple never present
  in `~/loops/<slot>/applied.jsonl` history. IF the novelty floor cannot be met (= no untried
  tuples available), THE SYSTEM SHALL append `{ts, slot, reason: "novelty-floor-unmet"}` to
  `lessons.jsonl` and allow the pass to continue without the quota.

## Non-Functional Requirements

- **NFR-1** All shared scripts SHALL be POSIX-bash or Python 3.11+; no external runtime
  dependencies beyond what's already in the OSS framework (= tmux, jq, gh, python3, node, claude).

- **NFR-2** State SHALL be file-backed; no in-memory-only daemon. Crash-restart SHALL be loss-free
  (= every relevant value either appended to jsonl or recomputed from current state).

- **NFR-3** Scripts SHALL be re-entrant: concurrent healthcheck ticks for the same slot SHALL
  NOT double-restart (= flock or atomic mtime check).

## Edge Cases

- **EDGE-1** Two self-heal modes match in one tick (e.g. trust dialog AND "Not logged in"
  visible) → REQ-A9 mutual-exclusion: priority order A1>A2>A3>A4>A5>A6>A7>A8; only highest
  fires this tick.

- **EDGE-2** `gh` CLI is rate-limited → cross-learn-share retries 3× with exponential backoff,
  then logs warning + continues (REQ-D3).

- **EDGE-3** Two launchd ticks fire concurrently → `flock -n ~/loops/<slot>/.healthcheck.lock`
  guards entry; second tick exits without action.

- **EDGE-4** `~/loops/<slot>/` does not exist on first run → script auto-creates with `mkdir -p`.

- **EDGE-5** Imported skill from `loop-propose.sh` is malicious → all imported skills run in
  `.worktrees/sandbox-<sha>/` for at least 3 days before promotion to live (TRAP-6).

- **EDGE-6** Claude session usage stats not exposed (CLAUDE_CODE_ENTRYPOINT=plugin etc) →
  fall back to byte-count × heuristic ratio for `tokens_total`; clearly mark such rows with
  `token_source: "estimated"` for downstream filtering.

- **EDGE-7** `~/loops/<slot>/earnings.jsonl` row arrives with `amount=0` (e.g. partial settlement,
  refund) → ROI calc includes it as zero, does not skip; this is honest reporting.

## Purity Boundary (sketch — formalized in 1b)

| layer | side-effect surface |
|-------|---------------------|
| PURE | ROI calculation, novelty-quota math, two-clock rolling average, manifest field validation, lesson dedup hashing |
| I/O-BOUND | `tmux send-keys`, `gh issue` API, launchd plist, file writes to `~/loops/*`, browser CDP send, Telegram POST |

The 9 shared scripts SHALL keep pure logic in helper functions / Python modules that take inputs +
return values, with the I/O surface kept thin and at the script's outer edge — so the pure layer
can be tested without touching tmux/gh/disk.
