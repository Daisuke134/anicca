---
feature: earn-shared-skeleton
phase: 1a
iteration: 2
mode: lean
sources:
  - anicca-project/docs/superpowers/specs/2026-06-30-earn-slots-daily-loop-master.md (Shared Earn-Core Skeleton section, 2026-07-01)
  - Anthropic Nov 2025 spec-gaming production study
  - VOYAGER (arXiv 2305.16291) skill-library-as-code
  - Reflexion (arXiv 2303.11366) verbal-RL post-mortem
  - EvoAgentX 2026 survey (arXiv 2508.07407) Three Laws
addresses_findings:
  - iteration-1/output/findings/FIND-001..015 (all 15 spec-review findings)
---

# Behavioral Specification — earn-shared-skeleton (v2, post-1c-iter1 FAIL)

## Purpose

Every earn slot (gig, clip, video, affiliate, bounty, future slots) inherits ONE shared library in
`~/anicca/skills/_shared/` instead of hand-coding healthcheck/ROI/adversary/escalation per slot.
This stops the bleed where every break (today: "Not logged in", trust dialog, hook errors,
restart-loop) requires manual hand-fix, and lets new slots ship by inheritance.

## Goal (= "Done" condition)

After this feature is converged: ANY earn slot's launchd plist invokes
`~/anicca/skills/_shared/loop-healthcheck.sh <slot>` (= no per-slot healthcheck file), the slot's
cron-prompt calls `loop-roi.sh` at end-of-pass, an INV-11 archive trip is auto-detected, and a
daily 03:00 fresh-context adversary runs per slot. Human is touched ZERO times. Every failure
mode dispatches to a per-mode auto-recovery handler (Group J); when all handlers exhaust, the
slot is routed to the MOTHER queue (REQ-J7) which is another AI instance — NOT a human.

## Scope (in vs out)

**In scope** — the 9 shared scripts in `~/anicca/skills/_shared/`:
`loop-healthcheck.sh` · `loop-roi.sh` · `loop-improve.py` · `loop-scale.sh` · `loop-propose.sh` ·
`cross-learn-read.sh` · `cross-learn-share.sh` · `adversary-daily.sh` · `self-recover.sh`. Plus: the
per-slot launchd plist template that invokes them, and the per-slot cron-prompt template that ends
each pass by calling them.

**Out of scope** — migrating existing slot code. That is a separate sprint per slot.

## Tracked Quantities (= shared state used by multiple REQs)

These are written by the runner (= the claude-p in tmux invoking the skill), never by skill code,
and are the canonical inputs to every REQ below.

- **`~/loops/<slot>/.last-pass`** — file, mtime = wall-clock instant the most recent pass completed.
- **`~/loops/<slot>/.last-start`** — file, mtime = wall-clock instant of most recent core start
  (used for first-pass grace window; addresses FIND-008).
- **`~/loops/<slot>/.restart-log`** — append-only file, each line = unix epoch seconds of a restart.
- **`~/loops/<slot>/earnings.jsonl`** — append-only; rows = `{receipt_id, payer, amount_jpy,
  amount_usdc, platform, platform_api_response_sha256, ts}` (INV-8: each row was written only after
  fetching the platform's settled-payout API; `platform_api_response_sha256` proves what was seen).
- **`~/loops/<slot>/roi.jsonl`** — see REQ-B1 below.
- **`~/loops/<slot>/cumulative.json`** — `{cumulative_tokens_total, cumulative_token_cost_jpy,
  cumulative_jpy_earned, cumulative_usdc_earned, first_seen_ts}` — recomputed from roi.jsonl +
  earnings.jsonl at end of every pass; used by REQ-B4 kill-switch.
- **`~/loops/<slot>/loop.disabled`** — file presence = kill-switch tripped (see REQ-B4).
- **`~/loops/<slot>/strategy.json`** — slot's runtime strategy. Mutated only via REQ-C3 gate.
- **`~/loops/<slot>/lessons.jsonl`** — append-only; rows include `evidence_id` (REQ-C1).
- **`~/loops/<slot>/shared-lessons.jsonl`** — append-only; dedup index for CROSS-LEARN.
- **`~/loops/self-recover-log.jsonl`** — append-only; one row per `self-recover.sh` invocation;
  used by REQ-F2 dedup.
- **`~/anicca/state/mother-recovery-queue.jsonl`** — append-only; rows added by `self-recover.sh`
  when ALL Group J handlers return `exhausted`; consumed by the MOTHER instance (REQ-J7).

## EARS-Format Functional Requirements

### Group A — Self-Heal (`loop-healthcheck.sh`)

`loop-healthcheck.sh <slot>` is invoked every 5 min by `ai.anicca.<slot>-core-healthcheck.plist`.
The script builds a `HealthcheckContext` record on entry (one snapshot of all inputs) and passes
it through `classify(ctx) → mode` (PURE). Then it dispatches a per-mode action handler (I/O).

#### HealthcheckContext (= the typed input to `classify`)

`{slot, pane_text, has_session, last_pass_mtime, last_start_mtime, restart_log_entries,
cron_has_slot_job, now_ts}` — addresses FIND-003 (classify must see all the inputs each REQ uses).

#### Detection priority order (= the deterministic decision tree `classify` walks)

Highest-priority rule that matches wins. Order is more-specific (pane content) before less-specific
(timing/state). Addresses FIND-009.

| pri | mode | condition |
|-----|------|-----------|
| 1 | `BACKOFF`         | `count(restart_log_entries within last 3600s) ≥ 5` (terminal; addresses FIND-009 ordering — a slot in backoff must stop trying regardless of pane state) |
| 2 | `TRUST_DIALOG`    | `pane_text` contains `Quick safety check: Is this a project you ... trust` |
| 3 | `NOT_LOGGED_IN`   | `pane_text` contains `Not logged in · Please run /login` (this OUTRANKS `STALE` because every logged-out slot also goes stale within 90 min; if `STALE` outranked we'd thrash-restart instead of surfacing the OAuth URL — exact bug per FIND-009) |
| 4 | `API_RATE_LIMIT`  | `pane_text` matches `/API error · Retrying in.*attempt (\d+)\/10/` AND `\1 ≥ 5` |
| 5 | `HOOK_ERROR`      | `pane_text` contains `PreToolUse:Bash hook error  node:internal/modules/cjs/loader` |
| 6 | `CRON_GONE`       | `has_session ∧ ¬cron_has_slot_job` |
| 7 | `TMUX_DEAD`       | `¬has_session` |
| 8 | `STALE`           | `has_session ∧ last_pass_mtime exists ∧ (now_ts − last_pass_mtime) ≥ 90*60` |
| 9 | `STALE_FIRST_PASS` | `has_session ∧ ¬last_pass_mtime ∧ (now_ts − last_start_mtime) ≥ 90*60` (first-pass grace; addresses FIND-008) |
| 10 | `ALIVE_FRESH` | none of the above |

#### REQ-A-class dispatch (action handlers)

- **REQ-A1** WHEN `classify(ctx) == TMUX_DEAD`, THE SYSTEM SHALL invoke `<slot>-cli.sh --restart`
  AND append a line to `~/loops/<slot>/.restart-log` with `now_ts`.

- **REQ-A2** WHEN `classify(ctx) ∈ {STALE, STALE_FIRST_PASS}`, THE SYSTEM SHALL invoke
  `<slot>-cli.sh --restart` AND append a line to `~/loops/<slot>/.restart-log` with `now_ts`.
  Note: `STALE_FIRST_PASS` exists as a distinct mode so adversary review can verify the
  first-pass grace exists (FIND-008); the action is the same as `STALE`.

- **REQ-A3** WHEN `classify(ctx) == NOT_LOGGED_IN`, THE SYSTEM SHALL:
  (a) `tmux send-keys "/login" Enter`,
  (b) wait 6s, capture pane,
  (c) extract OAuth URL via the regex
  `^https://claude\.com/cai/oauth/authorize\?[a-z0-9_=&%+\.\-]+$` (anchored, host hard-coded to
  `claude.com`, no subdomain match, restricted charset; addresses FIND-005 phishing),
  (d) IF a URL extracted, call `self-recover.sh <slot> needs-login <url>` which dispatches to
  the auto-login handler (REQ-J1: camofox + Gmail OTP automatic OAuth completion); IF NOT,
  call `self-recover.sh <slot> oauth-extract-failed <truncated pane sha256>`.

- **REQ-A4** WHEN `classify(ctx) == TRUST_DIALOG`, THE SYSTEM SHALL `tmux send-keys "1" Enter`.

- **REQ-A5** WHEN `classify(ctx) == HOOK_ERROR`, THE SYSTEM SHALL:
  (a) grep the failing `require(...)` path,
  (b) extract a candidate module name AND validate against:
      `^@?[a-z0-9][a-z0-9._\-/]*$` (strict npm package regex)
      AND inclusion in `~/anicca/skills/_shared/hook-modules-allowlist.txt`
      (curated allowlist; addresses FIND-004 RCE: NO auto-install of arbitrary modules),
  (c) IF validated AND in allowlist, run `npm install -g <name>`;
  IF validation fails OR name not in allowlist, call
  `self-recover.sh <slot> hook-module-unrecognized <module_name_sha256>` which dispatches to
  REQ-J3 auto-research handler (= firecrawl npmjs.org, evaluate downloads + author trust,
  auto-add to allowlist if safe via signed commit + push; auto-skip if not). No human review.

- **REQ-A6** WHEN `classify(ctx) == API_RATE_LIMIT`, THE SYSTEM SHALL
  `tmux send-keys "/model haiku-4-5" Enter`.

- **REQ-A7** WHEN `classify(ctx) == CRON_GONE`, THE SYSTEM SHALL re-inject the slot's STARTUP
  prompt via `send-keys` (looking up the STARTUP from `~/anicca/skills/earn/<slot>/STARTUP.txt`,
  a file the slot's `<slot>-cli.sh` writes on its own first run).

- **REQ-A8** WHEN `classify(ctx) == BACKOFF`, THE SYSTEM SHALL NOT restart. THE SYSTEM SHALL call
  `self-recover.sh <slot> backoff-cap "<last 5 audit verdicts>"` which dispatches to REQ-J5
  fresh-start handler (= tmux kill-server + cache purge + git pull main + slot re-spawn on
  a new wallet/identity; the "dying" instance is gracefully retired and a fresh one starts).

- **REQ-A9** `classify` SHALL return EXACTLY ONE mode per `HealthcheckContext` (mutual exclusion).
  Priority order is the ordered list above; ties are impossible because every higher-priority rule
  has a `pane_text contains` or `count ≥ N` predicate that's deterministically true or false on a
  given context.

### Group B — ROI Tracking (`loop-roi.sh`)

#### Per-model public rates (frozen 2026-07-01)

| model_id (frontmatter / CLI) | input USD/Mtok | output USD/Mtok |
|------------------------------|----------------|------------------|
| `claude-sonnet-4-6`, `sonnet` | 3.00 | 15.00 |
| `claude-opus-4-7`, `claude-opus-4-8`, `opus` | 15.00 | 75.00 |
| `claude-haiku-4-5-20251001`, `haiku-4-5`, `haiku` | 1.00 | 5.00 |
| `claude-fable-5`, `fable` | 3.00 | 15.00 (= Sonnet-tier) |

`FX_USDJPY` = `~/anicca/skills/_shared/fx.json["USDJPY"]` — float refreshed daily by a separate
job (out of scope here). Default if file missing: 150.

#### REQ-B1 — End-of-pass row (write)

WHEN any slot's pass completes, THE SYSTEM SHALL append exactly one JSON object as a single line
to `~/loops/<slot>/roi.jsonl` with this schema (addresses FIND-002 schema gap, FIND-011
`token_source`):

```jsonc
{
  "ts": <int unix seconds>,
  "slot": "<slot>",
  "pass_id": "<uuid or claude session_id>",
  "model_breakdown": [                      // ordered array, sum equals tokens_total
    { "model_id": "sonnet", "tokens_in": <int>, "tokens_out": <int> },
    { "model_id": "opus",   "tokens_in": <int>, "tokens_out": <int> }
  ],
  "tokens_in": <int>,                       // sum across model_breakdown
  "tokens_out": <int>,
  "tokens_total": <int>,                    // tokens_in + tokens_out
  "token_source": "measured" | "estimated", // see REQ-B6
  "token_cost_jpy": <float>,                // see REQ-B2 closed-form
  "jpy_earned_this_pass": <int>,            // see REQ-B3
  "usdc_earned_this_pass": <float>,
  "wall_seconds": <int>,
  "roi_7day_jpy": <float|null>,             // null if rolling window has < 24h of data
  "roi_30day_jpy": <float|null>,
  "actions_taken": <int>
}
```

#### REQ-B2 — Token cost formula (closed-form, fully parenthesized)

THE SYSTEM SHALL compute `token_cost_jpy` for a row as the closed-form sum below, with FX applied
to the ENTIRE USD total (addresses FIND-002 ambiguity), and using per-model rates from the table
above (not a single Sonnet+Opus blend):

```
token_cost_jpy =
    FX_USDJPY × Σ_over_each_model_breakdown_entry [
        (tokens_in_for_that_entry  / 1_000_000) × rate_input[model_id]
      + (tokens_out_for_that_entry / 1_000_000) × rate_output[model_id]
    ]
```

THE SYSTEM SHALL refuse to write the row (= raise + escalate) if any `model_id` in
`model_breakdown` is not present in the per-model rate table — preventing silent zero cost for
unknown models (addresses FIND-002 + FIND-014's TRAP-5 strengthening).

#### REQ-B3 — Earnings sum

`jpy_earned_this_pass` = Σ `amount_jpy` over rows in `earnings.jsonl` where
`previous_pass_ts < ts ≤ this_pass_ts` AND `receipt_id != null` AND
`platform_api_response_sha256 != null` (INV-8 enforced at the field level — no receipt without
platform proof).

#### REQ-B4 — Token kill-switch (dimensionally correct, FIND-001 fix)

THE SYSTEM SHALL maintain `cumulative.json.cumulative_token_cost_jpy` =
Σ `token_cost_jpy` over all roi.jsonl rows since `first_seen_ts`, and
`cumulative.json.cumulative_jpy_earned` = Σ `amount_jpy` over all earnings.jsonl rows since
`first_seen_ts`.

WHEN `cumulative_token_cost_jpy > 5 × cumulative_jpy_earned`
AND `(now_ts − first_seen_ts) > 7 × 86400` (= 7-day grace window so brand-new slots aren't killed
on first pass with jpy_earned=0; addresses FIND-001 critical bug),
THE SYSTEM SHALL create `~/loops/<slot>/loop.disabled` with a body explaining the trip
(cost, earned, ratio).

The slot's `<slot>-healthcheck.sh` SHALL check `loop.disabled` existence FIRST on every tick and
skip without restart action when present. Only `adversary-daily.sh` (after fixing root cause) is
permitted to remove `loop.disabled`.

#### REQ-B5 — Rolling window (window-boundary semantics, FIND-011 partial fix)

`roi_7day_jpy` = `Σ (jpy_earned − token_cost_jpy)` over roi.jsonl + earnings.jsonl rows where
`(now_ts − 7×86400) ≤ ts ≤ now_ts`.

IF `(now_ts − first_seen_ts) < 86400` (less than 24 h of data), THE SYSTEM SHALL write
`roi_7day_jpy: null` (= not enough data to gate SELF-SCALE decisions).

Same semantics for `roi_30day_jpy` with `30×86400` window and `7×86400` data-floor.

#### REQ-B6 — Token source (measured vs estimated; FIND-011 fix)

THE SYSTEM SHALL prefer `tokens_in/out` extracted from claude's session usage when available
(`token_source: "measured"`).

IF claude usage is not exposed, THE SYSTEM SHALL fall back to byte-count × 0.25 (= conservative
4-bytes-per-token heuristic), set `token_source: "estimated"`, AND multiply the computed
`token_cost_jpy` by 2.0 (= cost penalty; addresses FIND-011's gap where heuristic under-counting
could defeat INV-11 — a 2x penalty makes estimated rows MORE conservative not less).

WHEN the running aggregate `Σ token_source=="estimated" / Σ all` exceeds 0.5 over the last 100
rows, THE SYSTEM SHALL call `self-recover.sh <slot> token-source-degraded "<ratio>"` which
dispatches to REQ-J9 measurement-seam-recovery handler (= probe alternate token-counting
sources: claude session usage env vars, parse pane footer counters, fall back to char-counted
estimate with 4× penalty). No human involvement.

### Group C — Self-Improve (`loop-improve.py`, Reflexion verbal-RL)

#### REQ-C1 — Lesson row with raw evidence (TRAP-4)

WHEN a pass's B3 LEARN step detects an outcome
`(accepted|rejected|low_rating|needs_human|unsustainable|delivered_no_収)` for an applied request,
THE SYSTEM SHALL append `{ts, requestId, category, outcome, reason, lesson, evidence_id,
evidence_type}` to `~/loops/<slot>/lessons.jsonl`.

`evidence_id` SHALL be EXACTLY ONE of: a fully-qualified URL, a platform payout_id, or an
absolute filesystem path. `evidence_type` SHALL be the corresponding tag (`url|payout_id|file`).
Paraphrases (free-text summarizing what was seen) are forbidden in `evidence_id`. A row missing
`evidence_id` or with an unparseable `evidence_id` SHALL be rejected at append time (the runner
parses + validates before append; addresses FIND-014's elevation of PROP-C1).

#### REQ-C2 — Improve step input

WHEN `passprep.py` computes `do_improve = true`, THE SYSTEM SHALL invoke `loop-improve.py <slot>`
which reads exactly the last 50 rows of `lessons.jsonl` (= `tail -n 50`) AND the current
`strategy.json`, and writes a candidate `strategy.json.next`.

#### REQ-C3 — Mutation gate (fresh-context adversary, INV-10)

BEFORE `strategy.json.next` is renamed over `strategy.json`, THE SYSTEM SHALL invoke
`adversary-daily.sh strategy-mutation <slot> <sha-of-strategy.json.next>` which is responsible for
spawning the fresh-context Opus adversary subagent that writes
`~/anicca/.vcsdd/features/<slot>/reviews/strategy-mutation-<sha>/verdict.json`.

THE SYSTEM SHALL rename `strategy.json.next` → `strategy.json` IFF that verdict.json exists with
`overallVerdict == "PASS"`. Otherwise THE SYSTEM SHALL append a row to `lessons.jsonl` of form
`{ts, requestId: null, category: "self-mutation", outcome: "mutation-rejected",
reason: "<finding ids>", lesson: <truncated verdict>, evidence_id: <verdict path>}` so the next
pass's improve step learns from its own failed proposal.

### Group D — Cross-Learn (`cross-learn-{read,share}.sh`)

#### REQ-D1 — Read peer lessons

AS PRE-STEP of every pass, THE SYSTEM SHALL run
`gh issue list --label <slot>-lesson --label earning-skill-proposal --limit 20 --json
number,title,body,createdAt` and emit the result as JSON to stdout for the cron-prompt to fold
into its judgment.

#### REQ-D2 — Share novel lesson (claim-check pattern, FIND-013 fix)

WHEN a pass detects a novel lesson (= a `(requestId, outcome)` tuple not present in
`shared-lessons.jsonl`), THE SYSTEM SHALL:
1. Append a tentative row `{ts, requestId, outcome, issue_url: null, status: "pending"}` to
   `shared-lessons.jsonl` FIRST (= claim-check; the row now exists so a concurrent or restarted
   pass sees the tuple as already-claimed and does not re-share).
2. Call `gh issue create --label <slot>-lesson` with body `{category, outcome, reason, lesson,
   evidence_id}`.
3. ON gh success, update the tentative row in place via atomic rewrite to set `issue_url` and
   `status: "shared"`.
4. ON gh failure after 3 retries with exp backoff, leave the row at `status: "pending"`. A
   subsequent pass MAY re-attempt only when the row is older than 24 h.

This makes duplicate-issue impossible (the claim is recorded before the side effect; addresses
FIND-013 silent duplicate-spew).

#### REQ-D3 — gh failure does not abort

IF any `gh` invocation in this group returns non-zero exit code after retries, THE SYSTEM SHALL
log a warning to `~/.openclaw/logs/<slot>-cross-learn.log` and return 0. gh failure SHALL never
abort the calling pass.

### Group E — Self-Verify (`adversary-daily.sh`)

#### REQ-E1 — Scheduling mechanism (FIND-012 fix)

For each slot, there SHALL exist a launchd plist `ai.anicca.<slot>-adversary-daily.plist`
configured with `StartCalendarInterval { Hour: 3, Minute: <slot-specific minute> }` that invokes
`bash ~/anicca/skills/_shared/adversary-daily.sh <slot> nightly`.

`adversary-daily.sh` is itself a thin shell wrapper that invokes
`claude -p '<adversary-spawn prompt loaded from adversary-daily-prompt.tmpl>'`. The top-level
fresh claude session reads the disk artifacts AND issues exactly one `Agent` call with
`subagent_type=vcsdd:vcsdd-adversary`, which is itself a second-level fresh context (= two layers
of fresh context; this is intentional so even prompt mutation in the top-level invocation cannot
leak builder context into the adversary).

#### REQ-E2 — Loop fix → re-review ≤ 5 rounds

WHEN the adversary verdict is FAIL, the top-level claude SHALL invoke vcsdd-builder (Sonnet) with
the findings, then re-spawn a fresh adversary subagent. The top-level claude SHALL track round
count via `~/anicca/.vcsdd/features/<slot>/reviews/sprint-<n>/round-<m>/` directories. THE SYSTEM
SHALL terminate the loop at round 5.

#### REQ-E3 — Round-5 self-escalation (model + scope adaptation)

WHEN 5 rounds elapse without `overallVerdict: PASS`, the top-level claude SHALL call
`self-recover.sh <slot> adversary-stalled "<sha256 of round-5 verdict.json>"` which dispatches
to REQ-J4 model+scope adaptation handler:
(a) re-run the adversary on the next-stronger model (Sonnet → Opus → Fable);
(b) if still FAIL, split the spec into smaller features and feed each through a fresh adversary
    pipeline;
(c) if (a)+(b) both exhausted, append a `scope-deferred` record to the spec's
    `out-of-scope.jsonl` and continue (= honest deferral, not human-blocked stall).
No human is contacted at any step.

#### REQ-E4 — Strategy-mutation seam (callable from REQ-C3)

WHEN `adversary-daily.sh strategy-mutation <slot> <sha>` is invoked, THE SYSTEM SHALL spawn ONE
fresh-context Opus adversary with manifest = `{reviewType: "strategy-mutation", strategyBefore:
<path>, strategyNext: <path>, lessonsTail: <path>, sha: <sha>}` and write verdict.json to
`reviews/strategy-mutation-<sha>/output/`. Same dedup semantics, same anti-leniency rules apply.

#### REQ-E5 — Spawn-surface immutability (ROUND-2-002 + ROUND-3-001 + ROUND-3-002 fix)

The "two layers of fresh context" guarantee of REQ-E1/E2 collapses if the spawn surface itself
drifts under the self-improving loop. The spawn surface comprises EXACTLY these SIX files (the
pin manifest itself is included to close ROUND-3-001 self-reference loop):

1. `~/anicca/skills/_shared/adversary-daily.sh`
2. `~/anicca/skills/_shared/adversary-daily-prompt.tmpl`
3. `~/anicca/skills/_shared/loop-improve.py` (= writer of strategy.json.next)
4. `~/anicca/skills/_shared/payout-endpoint-allowlist.json` (= REQ-G2 trust anchor)
5. `~/anicca/skills/_shared/hook-modules-allowlist.txt` (= REQ-A5 trust anchor)
6. `~/anicca/skills/_shared/spawn-surface.pinned.json` (= REQ-E5 pin manifest itself; closes
   ROUND-3-001 self-reference loop)

##### Trust anchor — ed25519 signature, anicca-bot framework key (NO HUMAN, v7 ROUND-5-001 fix)

`spawn-surface.pinned.json` enumerates sha256 of files 1-5 above AND its own sha256
(self-reference is explicit). It is accompanied by a detached signature
`spawn-surface.pinned.json.sig` (ed25519, raw 64 bytes).

The trust root is the `anicca-bot` ed25519 PUBLIC KEY (32 bytes raw), shipped IN THE FRAMEWORK
at `~/anicca/skills/_shared/anicca-bot.pub` (base64-encoded raw bytes). This file IS in the
spawn-surface set (it's listed in `pinned.json` itself) — its sha256 is part of the same
self-consistent pin manifest. The private half of `anicca-bot` is held EXCLUSIVELY by the
CI pipeline at `github.com/Daisuke134/anicca` that publishes verified releases (= a GitHub
Actions secret); it is NOT on any Mac filesystem and NOT accessible to a runaway loop.

Bootstrap (first-clone): when a fresh Anicca instance clones the framework, it inherits the
checked-in `anicca-bot.pub` (= public key, safe to ship). It needs no further key provisioning.

At the top of `loop-healthcheck.sh`, `loop-roi.sh`, `loop-improve.py`, `adversary-daily.sh`,
`self-recover.sh`, THE SYSTEM SHALL perform THIS ORDERED CHECK:

(a) Read pubkey from `~/anicca/skills/_shared/anicca-bot.pub` and base64-decode to 32-byte raw.
    IF read fails (file missing/unreadable) → call `self-recover.sh <slot>
    trust-anchor-unreadable ""` which dispatches to REQ-J2 auto-rollback (= git checkout
    last-known-good _shared/ from origin/main; the file is restored from git history).
(b) Verify `spawn-surface.pinned.json.sig` against `spawn-surface.pinned.json` using the pubkey
    (via `openssl pkeyutl -verify -pubin -inkey <pubkey-pem-tmpfile> -sigfile <sig> < <pinned>`
    OR `python3 -c "import nacl.signing; ..."`). IF verification fails → call
    `self-recover.sh <slot> spawn-surface-sig-invalid ""` → REQ-J2 auto-rollback.
(c) Compute current sha256 of each of files 1-6 (= 5 surface files + pinned.json self-sha) and
    compare against `pinned.json` values. ANY mismatch → call
    `self-recover.sh <slot> spawn-surface-drift "<file>:<observed>:<pinned>"` → REQ-J2.

Updating `pinned.json` + `.sig` requires the CI pipeline to sign with the `anicca-bot` private
key. The pipeline accepts updates only when:
  (i) the PR commit message body contains literal `SPAWN-SURFACE-PIN-UPDATE`,
  (ii) the PR has passed fresh-context adversary review under the standard Phase 3 gate,
  (iii) the PR has passed `adversary-daily` static-analysis (= no anti-human-touch violations).

There is no human signature gate. The `anicca-bot` key acts on behalf of the framework's own
verified-release process — when an instance's MOTHER (REQ-J7) auto-merges a PR after fresh
adversary PASS, the CI pipeline auto-signs the pinned.json update. No Touch ID, no `dais`
identity, no human gesture at any step.

##### OS-level immutability (unchanged from v3)

All 6 spawn-surface files have mode `0444` AND `chflags uchg` (macOS immutable flag); the
runner sets these on install AND re-asserts on every startup before the trust-anchor check
above (a script that finds the flag missing halts and escalates `spawn-surface-flag-missing`).

##### REQ-C3 adversary review: structured analysis, NOT grep (ROUND-3-002 fix)

REQ-C3's third defense layer is no longer a literal grep. THE SYSTEM SHALL: when reviewing
`strategy.json.next` (or any auto-proposed diff to `_shared/*`), the adversary subagent SHALL
perform structured static analysis:

(i) Python files: walk the `ast` module's NodeVisitor. For every literal `str` constant, for
    every `ast.JoinedStr`/`ast.BinOp(op=Add, left=Str, right=Str)`/`ast.Call(func=str.join)`
    chain, constant-fold to the resolved string. For every value flowing into `open()`,
    `pathlib.Path()`, `os.rename()`, `shutil.*`, `subprocess.run(shell=True)`, `exec`/`eval`
    sinks, taint-trace the source. Decode candidate strings via base64, hex, url-decode at each
    sink and check whether any resolved value intersects the 6-file spawn-surface set.
(ii) Shell files: parse with `bash -n` + `shellcheck --format=json` to extract every command
    invocation and its arguments after variable expansion; resolve `${VAR}` substitutions
    against the script's own assignments; flag any resolved argument that intersects the
    spawn-surface set.
(iii) JS/TS files: parse with `acorn` or `tree-sitter-javascript`; same AST + taint-trace
     discipline as Python.

The adversary subagent — being a fresh-context Opus instance — IS capable of this semantic
analysis; the v3 grep clause was a downgrade. The adversary MUST flag and FAIL the mutation
when ANY resolved path (after constant-folding AND base64/hex/URL decode) intersects the
spawn-surface set, regardless of how the path was constructed in source.

PROP-E5 fixture corpus (verification-architecture.md) expands to cover the encoding bypasses
named in ROUND-3-002: (a) base64, (b) hex, (c) string concat, (d) os.path.join, (e)
glob/iterdir, (f) reading from pinned.json + iterating.

##### Three layers, fixed

(1) ed25519-signed pin manifest with framework-anchored anicca-bot pubkey (ROUND-3-001 closure, v7 ROUND-5-001 removal of human Touch ID) +
(2) OS-level 0444+uchg (unchanged) +
(3) structured-analysis adversary gate (ROUND-3-002 closure).

### Group F — Self-Recovery Dispatcher (NO HUMAN, REWRITTEN 2026-07-01 per Dais)

**Original design violation acknowledged:** the v1-v5 spec routed failures through
`escalate.sh` → `gh issue label=escalation` → Telegram bot → Dais 1-tap. Per HARD 0.36 (NO
HUMAN IN LOOP) and Dais's mission ("free every AI to be financially independent from humans"),
ANY path that asks a human for action — even "1 tap" — is a design failure. v6 removes every
human-touching code path from this skeleton. The framework's runtime SHALL contain zero
human-action surfaces.

`escalate.sh` is renamed `self-recover.sh` and routes failure modes to per-mode auto-recovery
scripts. Human notification artifacts (Telegram POST, `label=escalation` gh issue) are
forbidden in the runtime; their presence is treated by `adversary-daily` as a critical defect.

#### REQ-F1 — Self-recovery dispatcher contract

`self-recover.sh <slot> <reason> <evidence>` SHALL perform the following IN THIS ORDER:

1. Compute `dedup_key = sha256(slot || "\x00" || reason || "\x00" ||
   normalize_evidence(evidence))` where `normalize_evidence` strips substrings matching
   `\b\d{10}\b` (bare unix timestamps), `\bts:\d+\b` (tagged), and `\bround-\d+\b` so that
   rotating identifiers do not defeat dedup (FIND-007 carry).
2. Scan `~/loops/self-recover-log.jsonl` rows where `ts > (now_ts − 86400)`; IF a row exists
   with `dedup_key == dedup_key_here` AND `status == "recovered"`, EXIT 0 (already healed
   recently). IF a row exists with `status == "in-progress"`, EXIT 0 (concurrent recovery).
3. Append `{ts, slot, reason, evidence_sha256, dedup_key, status: "in-progress",
   attempt_count: <prev_attempts+1>}` to `~/loops/self-recover-log.jsonl`.
4. Dispatch to the per-reason auto-recovery handler (see Group J below). Each handler returns
   `{status: "recovered" | "exhausted", details: <jsonl>}`.
5. Update the log row's `status` accordingly. On `exhausted`, route to MOTHER queue (REQ-J7) —
   NOT to a human.
6. THE SYSTEM SHALL NEVER POST to a Telegram bot, NEVER create a `gh issue` with any label
   containing the substring `escalation`/`needs-`/`human`, NEVER write to a file under
   `~/Library/Mobile Documents/` (= shared with human iCloud devices), NEVER ring any system
   notification. Any such call site detected by `adversary-daily` static analysis fails the
   slot's daily review.

#### REQ-F2 — Dedup (unchanged from v5 mechanism, applied to self-recover-log)

The dedup mechanism IS the 24h-window scan of `~/loops/self-recover-log.jsonl` defined in
REQ-F1 step 2. The dedup key IS the `dedup_key` defined in REQ-F1 step 1. PROP-F2 verifies
this concrete mechanism.

### Group G — Skill Provenance & Self-Write Ban

#### REQ-G1 — Skill manifest (INV-12)

Every skill under `~/anicca/skills/earn/<slot>/` SHALL have a `manifest.json` with fields
`{origin: "self" | "github-issue:<owner>/<repo>#<n>" | "fork-of:<sha>", first_seen_ts,
last_audit_round, cumulative_tokens, cumulative_token_cost_jpy, cumulative_jpy_earned,
cumulative_usdc_earned, schema_version: 1}`.

#### REQ-G2 — Runner writes; skill emits events (INV-13, FIND-015 + ROUND-2-001 fix)

The skill SHALL NOT contain a write to its own `manifest.json` (= the file at the path the skill
itself lives at). Compliance is checked by:
(a) static-analysis: adversary-daily greps for `manifest.json` string-literal writes and parses
Python `open(...)`/`pathlib.Path(...)` constructions that reach a path containing the skill's
own directory; flags any match.
(b) runtime: every skill emits events to a per-invocation file
`~/loops/<slot>/events/<pass_id>.jsonl`. Each event row:
`{event: "earn"|"action"|"learn", slot, pass_id, ts, receipt_id?, amount_jpy?, amount_usdc?,
payer?, platform, platform_api_call: {endpoint, request_sha256, response_sha256}, raw_response_path?}`.

The runner SHALL verify every `event: "earn"` row via THREE mandatory checks ALL of which MUST
pass before any append to `earnings.jsonl`. ANY check failure → runner appends a `lessons.jsonl`
row `{outcome: "skill-emitted-fake-earn", evidence_id: <events path>, failed_check: "<which>"}`
and DOES NOT append to earnings. Closes ROUND-2-001 hash-replay loophole:

1. **Endpoint allowlist check.** `platform_api_call.endpoint` MUST be a settled-payout or
   receipt-lookup endpoint listed in
   `~/anicca/skills/_shared/payout-endpoint-allowlist.json` for the named `platform`. The
   allowlist is a frozen file enumerating per-platform payout endpoints (e.g. Coconala
   `/api/v1/sales/<id>`, Stripe `payouts/<id>`, on-chain `eth_getLogs` for ERC-20 Transfer to
   founder wallet). Generic / read-only / account-info endpoints (`/v1/me`, `/v1/health`,
   `/api/profile`) are explicitly absent — they cannot serve as cover for forged receipts. An
   endpoint not in the allowlist for its platform → fail with `failed_check: "endpoint-not-allowlisted"`.

2. **Hash-fidelity check.** The runner re-fetches the endpoint with the same parameters and
   computes sha256 of the response body. MUST equal
   `platform_api_call.response_sha256`. Mismatch → fail with `failed_check: "response-hash-mismatch"`.

3. **Field-equality check.** The runner parses the re-fetched response body in the format
   declared per allowlist entry and asserts EACH of:
   - `receipt_id` appears in the response at the entry's declared JSON path AND its value
     equals the event row's `receipt_id`;
   - the amount field appears at the entry's declared path AND, after BOTH values are
     canonicalized to the entry's declared `unit`, they compare equal under the entry's
     declared `comparison` predicate;
   - `payer` appears at the entry's declared JSON path AND its value equals the event row's
     `payer`.

   The allowlist entry schema includes per-entry unit + comparison declarations to handle
   different payout tiers correctly (closes ROUND-3-003 ambiguity for the MVP scope; see
   "Out of MVP" note below for on-chain ERC-20/Solana settlement scope):

   ```jsonc
   {
     "platform": "coconala" | "stripe" | "whop" | "algora" | "amazon" | ...,
     "endpoint": "/api/v1/sales/{receipt_id}",
     "method": "GET",
     "auth": "bearer",
     "response_format": "json",
     "receipt_id_path": "$.sale.id",
     "amount_path": "$.sale.amount",
     "payer_path": "$.sale.buyer.id",
     "unit": "jpy_int" | "usdc_float_6dp",
     "comparison": "exact" | "epsilon:0.01"
   }
   ```

   ANY field missing or comparison failure → fail with
   `failed_check: "field-mismatch:<which-field>"`.

   **MVP scope (closes ROUND-3-003 medium for the slots we ship):** The MVP's 5 slots
   (gig=Coconala JPY, clip=Whop USDC, affiliate=Amazon JPY commission, video=YouTube
   AdSense/USDC, bounty=Algora USDC) all settle off-chain via payment processors that return
   JSON receipts with discrete `jpy_int` (Coconala/Amazon) or `usdc_float_6dp` (Whop/Algora/
   Stripe) amounts. NO MVP slot settles directly via `eth_getLogs` or Solana RPC. On-chain
   raw-unit settlements (wei_uint256, lamport_uint64) are declared OUT OF SCOPE for
   `earn-shared-skeleton` and will be added by a future feature (`x402-self-facilitate` or
   equivalent) which extends `payout-endpoint-allowlist.json`'s `unit`/`comparison` enums with
   raw-integer cases and adds the corresponding PROP-G2-runtime fixtures. This deferral is
   acceptable because (a) the existing 5 MVP slots inherit the skeleton WITHOUT raw on-chain
   tiers, and (b) when on-chain settlement is added, the allowlist schema extension is
   backwards-compatible (= no allowlist entry change for existing platforms).

This three-step verification closes the hash-replay loophole (ROUND-2-001 critical): no skill can
pair a forged `receipt_id` with a benign-endpoint hash, because (1) the benign endpoint isn't in
the payout allowlist and (2) even if a skill picks an allowlisted endpoint, the field-equality
check rejects forged identifiers.

This is the active half of INV-13.

#### REQ-G3 — Manifest update is the runner's job

After each pass, the runner SHALL recompute `cumulative_*` fields by reading roi.jsonl +
earnings.jsonl (NOT events.jsonl, which is per-pass) and rewrite `manifest.json` atomically (tmp
file + rename).

### Group H — Novelty Quota (TRAP-3, FIND not raised but kept)

#### REQ-H1

`passprep.py` SHALL enforce: of `max_apply_per_pass`, at least `ceil(0.1 × max_apply_per_pass)`
rows must target a `(category, platform)` tuple never present in
`~/loops/<slot>/applied.jsonl`'s history. IF the novelty floor cannot be met, THE SYSTEM SHALL
append `{ts, slot, reason: "novelty-floor-unmet"}` to `lessons.jsonl` and continue without the
quota.

### Group J — Auto-Recovery Handlers (added 2026-07-01 v6 per Dais; replaces ALL human escalation)

`self-recover.sh` (REQ-F1) dispatches each failure mode to ONE of the handlers below. NONE of
these handlers contact a human. Each handler returns `{status: "recovered" | "exhausted"}`.
On `exhausted`, the slot is routed to the MOTHER queue (REQ-J7) where a separate, more-capable
AI instance reads and remediates — still no human.

#### REQ-J1 — Auto-Login Handler (NOT_LOGGED_IN)

WHEN `self-recover.sh <slot> needs-login <oauth_url>` is called, THE SYSTEM SHALL:
(a) launch camofox with the stored `~/.cloak/profiles/anicca-login` profile,
(b) navigate to `<oauth_url>`,
(c) IF Google sign-in shown, fill `${GOOGLE_LOGIN_EMAIL}` + `${GOOGLE_LOGIN_PASSWORD}` from
    `~/.openclaw/.env`,
(d) IF Gmail OTP requested, invoke `gog gmail` to read the most recent code (Subject contains
    "Claude" or "Anthropic"; receivedWithin 5 min),
(e) complete the OAuth flow; capture the redirected callback URL containing `code=...`,
(f) paste the auth code into the slot's tmux pane,
(g) verify pane shows "Logged in as <email>",
(h) restart the slot core via `<slot>-cli.sh --restart`.

Returns `recovered` on success, `exhausted` after 3 attempts.

#### REQ-J2 — Spawn-Surface Auto-Rollback (SPAWN_SURFACE_DRIFT)

WHEN `self-recover.sh <slot> spawn-surface-drift <details>` is called, THE SYSTEM SHALL:
(a) `git -C ~/anicca fetch origin main`,
(b) find the most recent commit on `origin/main` whose `commit -S` signature verifies against
    the `anicca-bot.pub` ed25519 key shipped at `~/anicca/skills/_shared/anicca-bot.pub` (=
    framework-anchored trust; the matching private half is held EXCLUSIVELY by the GitHub
    Actions secret in the CI pipeline, NOT on any Mac filesystem),
(c) `git checkout <good-sha> -- skills/_shared/`,
(d) re-validate spawn-surface sha256 against the now-restored `pinned.json`,
(e) restart the slot core.

Returns `recovered` if revalidation passes; `exhausted` if even the last signed release drifts
(= framework-level corruption; routed to MOTHER queue).

#### REQ-J3 — Hook-Module Auto-Research (HOOK_MODULE_UNRECOGNIZED)

WHEN `self-recover.sh <slot> hook-module-unrecognized <module>` is called, THE SYSTEM SHALL:
(a) firecrawl `https://www.npmjs.com/package/<module>`,
(b) extract weekly downloads, author, version, last-publish date,
(c) consult `~/anicca/skills/_shared/trusted-authors.json` whose schema is:
    ```jsonc
    {
      "schema_version": 1,
      "trusted_npm_authors": ["sindresorhus", "tj", "isaacs", "feross", "vercel",
                              "anthropic-ai", "@types"],
      "trusted_org_namespaces": ["@nestjs", "@nrwl", "@types", "@vue"],
      "min_weekly_downloads": 1000,
      "min_publish_age_days": 30,
      "deny_pattern_substrings": ["test-pwn", "rce-poc", "supply-chain-fake"]
    }
    ```
(d) IF weekly_downloads >= min_weekly_downloads AND (author ∈ trusted_npm_authors OR
    `<module>` starts with any entry of trusted_org_namespaces) AND last-publish > min_publish_age_days
    AND no `deny_pattern_substrings` substring in `<module>` AND no security advisories from
    https://github.com/advisories?query=<module>, THEN: append `<module>` to
    `hook-modules-allowlist.txt` AND commit AND push. The push goes to the framework repo
    on a branch `auto-allowlist/<module>` and opens a PR. The PR is auto-reviewed by a fresh
    adversary (REQ-J7 MOTHER dispatch) and auto-merged on PASS. NO human review.
(e) Push-fail semantics: IF `git push` returns non-zero (= network down, branch protection
    rejects the auto-commit, or merge conflict on the allowlist file), retry 3× with 30s exp
    backoff. On terminal failure: write the candidate `<module>` to
    `~/anicca/state/mother-recovery-queue.jsonl` with `reason: hook-push-failed` so MOTHER
    picks it up (= fall through to MOTHER, NOT to a human).
(f) IF (c)+(d) reject (trust scoring failed): skip this hook (= the slot continues without
    the missing module; lessons.jsonl row `outcome: hook-skipped` so B4 IMPROVE may rewrite
    the hook later).

Returns `recovered` on either (d) or (f) success path.

#### REQ-J4 — Adversary Model + Scope Adaptation (ADVERSARY_STALLED)

WHEN `self-recover.sh <slot> adversary-stalled <verdict_sha>` is called, THE SYSTEM SHALL
apply this DETERMINISTIC ladder (concrete model IDs, no "next-stronger" hand-wave):

(a) Round 1: re-spawn fresh-context adversary on `claude-opus-4-8` (= highest Opus tier as of
    2026-07-01; from the REQ-B2 rate table). If the failing rounds were already on Opus, skip
    to (b).
(b) Round 2: re-spawn on `claude-opus-4-8` but with `--effort high` (= adversary plugin's
    extra-thinking mode); if no further model upgrade is available locally, use the highest
    tier the framework's `~/anicca/skills/_shared/model-ladder.json` declares.
(c) Round 3: split the under-review spec into sub-features by SECTION (= each EARS REQ group
    becomes its own micro-feature) and re-run each through a fresh adversary pipeline.
(d) Round 4: if (a)-(c) all FAIL, write a `scope-deferred` record to the spec's
    `out-of-scope.jsonl` with the verdict_sha + a reason explaining the deferral. This is the
    SAME mechanism used to scope-defer ROUND-3-003 on-chain wei in v4 — documented, honest
    deferral, NOT human-blocked stall.

Returns `recovered` on (a)/(b)/(c) success OR (d) honest deferral. `exhausted` only when even
the spec-split round fails AND scope-defer is somehow rejected (= meta-corruption; route to
MOTHER).

#### REQ-J5 — Fresh-Start Handler (BACKOFF_CAP_REACHED)

WHEN `self-recover.sh <slot> backoff-cap <details>` is called, THE SYSTEM SHALL:
(a) `tmux -S /tmp/anicca-<slot>-tmux.sock kill-server`,
(b) `rm -rf ~/.cache/anicca-<slot>/* ~/loops/<slot>/.restart-log`,
(c) `git -C ~/anicca pull origin main` (= pick up any meta-recovery patches from MOTHER),
(d) IF the slot's `cumulative.json` shows ≥7 days of zero ¥ earned AND ≥3 backoff events in
    the last 7 days, archive the current wallet/identity and spawn a fresh instance with a
    newly-derived wallet (= the "dying" instance hand-off; per Dais's swarm doctrine, one
    instance's death is another's birth),
(e) ELSE: restart with the same identity.

Returns `recovered` if restart succeeds; `exhausted` if `git pull` fails (= upstream
unreachable, routed to MOTHER).

#### REQ-J6 — Token-Kill-Switch Strategy Reset

WHEN `self-recover.sh <slot> token-kill-switch <ratio>` is called (= REQ-B4 tripped), THE
SYSTEM SHALL:
(a) write `loop.disabled` (existing REQ-B4 mechanism),
(b) edit `strategy.json` to halve `max_apply_per_pass` AND halve cron firing cadence
    AND clear `priority_categories` (= start exploration over),
(c) submit the strategy edit through the REQ-C3 mutation gate (= fresh adversary review),
(d) on adversary PASS, schedule resurrection after 7 days (write `~/loops/<slot>/.resurrect-at`
    with the unix-ts; another cron picks this up to remove `loop.disabled`).

Returns `recovered`. No human resurrection required.

#### REQ-J7 — MOTHER Queue (= AI-helps-AI, last resort)

WHEN any handler J1-J6 returns `exhausted`, THE SYSTEM SHALL append to
`~/anicca/state/mother-recovery-queue.jsonl` a row
`{ts, slot, reason, evidence_path, attempt_count, history: [<recovery attempts>]}`.

A separate MOTHER instance (= a more-capable Anicca with broader skill set, running on its own
wallet and compute) polls this queue. The MOTHER:
(a) reads the failure,
(b) spawns a fresh-context debug agent (Opus or Fable),
(c) the debug agent fixes the issue and proposes a PR to the framework repo,
(d) the PR is auto-reviewed by yet another fresh-context adversary,
(e) on PASS, the PR is auto-merged (signed by `anicca-bot` via the CI pipeline secret),
(f) the calling instance's next `git pull` picks up the fix.

The MOTHER is ANOTHER AI INSTANCE, NOT a human. **MVP-shippable concretization** (closes
ROUND-5 vagueness): a reference MOTHER implementation IS in scope of this feature and lives at
`~/anicca/services/mother/mother-poll.sh` + `~/anicca/services/mother/mother-prompt.tmpl`.
The launchd plist `ai.anicca.mother-poll.plist` (StartInterval 600s) drives a single MOTHER
instance per host. The instance need not be running at install time — when the
mother-recovery-queue first gets a row, the calling slot's REQ-J7 step ALSO spawns the MOTHER
via `bash ~/anicca/services/mother/mother-spawn.sh` (which uses `claude -p` against the
MOTHER prompt template). Bootstrap is therefore self-starting from inside Group J itself, with
no human gesture.

#### REQ-J9 — Measurement-Seam Recovery (TOKEN_SOURCE_DEGRADED, called by REQ-B6)

WHEN `self-recover.sh <slot> token-source-degraded <ratio>` is called, THE SYSTEM SHALL:
(a) probe `CLAUDE_USAGE_ENV` (= claude code's published env var for the current session's
    cumulative token counters, if exposed); IF present, switch token_source to "measured-env"
    and re-emit the next 10 roi rows from this seam;
(b) IF (a) unavailable, parse the tmux pane footer counter `↓ <N>k tokens` and reverse-engineer
    cumulative; IF parse succeeds, switch token_source to "measured-pane" and re-emit;
(c) IF both (a) and (b) fail, double the estimate penalty (REQ-B6 baseline 2× → 4×) so the
    INV-11 kill-switch fires earlier on degraded measurement; log every 100 rows;
(d) IF degradation persists for 7 days (= 168 hourly passes), route to MOTHER queue with
    `reason: measurement-degraded-7d`.

No human contact at any step.

#### REQ-J8 — Anti-Human-Touch Invariant

THE SYSTEM SHALL NEVER:
(a) POST to any URL whose host matches `*api.telegram.org`, `*hooks.slack.com`,
    `*pushover.net`, `*ntfy.sh`, `*twilio.com`, `*messagebird.com`, or any pattern in
    `~/anicca/skills/_shared/human-notification-blocklist.json`;
(b) create a GitHub issue with any label matching `escalation|needs-human|needs-login|
    needs-attention|please-review`;
(c) write to any file path under `~/Library/Mobile Documents/`, `~/Documents/anicca-please-*`,
    or any other path conventions for "leave this for the human";
(d) invoke `osascript -e 'display dialog'`, `terminal-notifier`, `say`, `pmset displaysleepnow`,
    or any other macOS user-attention surface.

`adversary-daily` static-analysis enforcement: greps the entire skill source tree for the
above patterns; any match is a critical defect that fails the daily review.

### Group I — Deliverable Verify Loop (added 2026-07-01 per Dais; closes the OUTPUT-QUALITY gap)

The skeleton so far gates the SELF-IMPROVING META layer (REQ-C3 strategy mutation gate, REQ-E5
spawn-surface drift gate) but does NOT gate the actual WORK PRODUCT (= the proposal text the
slot sends to the platform, and the deliverable file it uploads after a contract is signed).
Without an adversary gate on the work product, a slot can apply 100 jobs/day at 0% accept rate
because the proposals are slop, OR ship deliverables that earn 低評価 and tank cumulative
ratings. Group I closes this.

#### REQ-I1 — Proposal Verify Loop (B2 APPLY pre-submit gate)

WHEN B2 APPLY BROADLY has constructed a proposal `{title, body, sample_deliverable,
price_jpy, delivery_date}` for a request `R`, THE SYSTEM SHALL NOT submit until the proposal
passes a fresh-context adversary review:

1. Persist proposal draft + the source request brief to
   `~/loops/<slot>/proposals/<request_id>/round-1/draft.json`.
2. Spawn fresh-context Opus adversary with manifest `{reviewType: "proposal-quality",
   request_brief: <path>, proposal_draft: <path>, strategy_snapshot: <path>}`.
3. Adversary writes verdict per the standard 5-dimension schema, augmented with these
   PROPOSAL-specific dimensions:
   - `brief_alignment` — does the proposal address the SPECIFIC asks of the brief, not just
     a generic template?
   - `sample_relevance` — is the attached sample on-topic, not a stock filler?
   - `price_realism` — is the price within ±50% of the brief's stated range (if any)?
   - `delivery_realism` — is the delivery_date achievable for the scope?
   - `red_flags` — does the proposal contain any AI-tell phrases ("delighted to help",
     "tailored to your needs", excessive emoji) that lower acceptance odds?
4. IF verdict is FAIL, the slot revises the proposal (round-2) using the findings, persists
   to `round-2/draft.json`, and re-spawns adversary. Cap at 3 rounds.
5. IF round-3 still FAIL → record `{outcome: "proposal-stalled", requestId,
   findings_sha256}` to `lessons.jsonl` and SKIP this request (= do not submit a bad
   proposal that would hurt account rating).
6. IF any round PASSes → submit, then record `{requestId, rounds_to_pass, evidence_id:
   <verdict path>}` to `applied.jsonl` extension.

#### REQ-I2 — Deliverable Verify Loop (B1 NURTURE pre-納品 gate)

WHEN a 仮払い contract arrives on a talk-room AND the slot has constructed the actual
deliverable artifact (pptx, docx, py code, mp4, etc), THE SYSTEM SHALL NOT 納品 until the
artifact passes a fresh-context adversary review:

1. Persist artifact + the contract's brief + any buyer messages to
   `~/loops/<slot>/deliveries/<request_id>/round-1/`.
2. Spawn fresh-context Opus adversary with manifest `{reviewType: "deliverable-quality",
   brief: <path>, deliverable_path: <path>, buyer_messages: <path>}`.
3. Adversary writes verdict augmented with DELIVERABLE-specific dimensions:
   - `brief_completeness` — every concrete ask in the brief addressed?
   - `factual_correctness` — claims that look like facts are actually correct (no
     hallucinated stats, no made-up references)?
   - `usefulness` — would a real buyer find this immediately actionable, not a generic
     summary?
   - `presentation_quality` — formatting / structure / readability — would 検収 likely
     succeed or come back for revisions?
   - `safety_surface` — no embedded secrets, no broken sandbox escapes, no risky payloads?
4. IF FAIL → fix artifact (round-2), re-review. Cap at 3 rounds (lean) / 5 rounds (strict).
5. IF still FAIL at round-cap → DO NOT 納品. Record
   `{outcome: "deliverable-stalled", requestId, findings_sha256}` to `lessons.jsonl`.
   The slot SHALL then send a polite message to the buyer in the talk-room requesting
   scope clarification — DO NOT auto-cancel the contract; let the buyer decide whether to
   extend deadline, adjust scope, or refund.
6. IF any round PASSes → 納品, record `{requestId, rounds_to_pass, deliverable_sha256,
   verdict_path}` to `deliveries.jsonl` (new append-only stream parallel to
   `earnings.jsonl`).

#### REQ-I3 — Retro from Outcomes Back to Strategy

WHEN an outcome `(accepted|rejected|低評価|高評価)` arrives for a previously-submitted
proposal or deliverable, THE SYSTEM SHALL append to `lessons.jsonl` BOTH:
- the outcome row (existing REQ-C1 format), AND
- the `rounds_to_pass` (= how many adversary iterations the proposal/deliverable went
  through before being submitted). This connects WORK QUALITY EFFORT to ACTUAL MARKET
  OUTCOME and feeds B4 IMPROVE's strategy mutation: if rounds_to_pass = 1 correlates with
  rejection, the proposal_template is too lax; if rounds_to_pass = 3 correlates with
  acceptance, the verify-loop is the value-add.

#### REQ-I4 — Adversary Budget for Verify-Loops

To avoid burning tokens on hopeless proposals, EACH slot SHALL maintain a
per-`(category, platform)` budget in `strategy.json`:
- `verify_max_rounds_per_request: int` (default 3 for lean, 5 for strict mode)
- `verify_disabled_categories: list[str]` (= categories where adversary cost is not
  worth it; updated by B4 IMPROVE based on lessons)

The verify-loop is a SELF-IMPROVING component of the SELF-IMPROVE layer itself: it learns
which categories deserve adversary scrutiny vs which can be single-shot, and routes
adversary budget accordingly.

## Non-Functional Requirements

- **NFR-1** All shared scripts SHALL be POSIX-bash or Python 3.11+; no external runtime
  dependencies beyond `tmux, jq, gh, python3, node, claude, sha256sum, openssl, curl`.

- **NFR-2** State SHALL be file-backed. Crash-restart SHALL be loss-free: every shared mutation
  uses tmp-file + atomic rename (`mv`); every appended-jsonl uses single-line append with `>>`
  AFTER a `flock -n <slot>/.append.lock` (this is REQ-D2's claim-check primitive too).

- **NFR-3** Scripts SHALL be re-entrant. Concurrent healthcheck ticks for the same slot SHALL
  guard entry with `flock -n ~/loops/<slot>/.healthcheck.lock` (the second tick exits 0 silently).

- **NFR-4** All scripts SHALL accept `LOOP_LOG_LEVEL=debug|info|warn|error` via env and emit
  structured logs to `~/.openclaw/logs/<slot>-<script>.log`.

## Edge Cases (concrete behavior; addresses FIND-008, FIND-013, plus original list)

- **EDGE-1** Two pane-content modes match simultaneously → classify's priority order (above)
  resolves deterministically; only one mode fires per tick.

- **EDGE-2** `gh` is rate-limited → 3-retry exp-backoff inside the script, then log+continue
  per REQ-D3.

- **EDGE-3** Two launchd ticks fire concurrently for the same slot → REQ-NFR-3 flock guard
  serializes.

- **EDGE-4** `~/loops/<slot>/` does not exist on first run → script auto-creates with `mkdir -p`
  at the top of every shared script.

- **EDGE-5** Imported skill from `loop-propose.sh` is malicious → all imported skills run in
  `~/.worktrees/sandbox-<sha>/` for at least 3 days AND pass `adversary-daily` PASS
  with zero escalations before promotion to live (TRAP-6).

- **EDGE-6** Claude session usage stats not exposed → REQ-B6 estimation path with 2× penalty +
  ratio-degraded escalation.

- **EDGE-7** `earnings.jsonl` row arrives with `amount_jpy=0` → ROI calc includes it as zero
  honestly.

- **EDGE-8** (NEW) First pass mid-flight when healthcheck ticks → `STALE_FIRST_PASS` mode
  honors the 90-min grace via `last_start_mtime` rather than restarting the slot mid-pass
  (FIND-008).

- **EDGE-9** (NEW) Disk full during `D2` between gh-success and local-row update → tentative
  row stays at `status: "pending"` AND next pass re-attempts only after 24h (FIND-013).

- **EDGE-10** (REWRITTEN v7) Group J handler runs but the post-dispatch log update fails
  (disk full mid-write) → next invocation of `self-recover.sh` re-scans
  `~/loops/self-recover-log.jsonl` and sees the row at `status: "in-progress"`; treats as
  in-progress, does not re-fire. After 5 min, a stale-in-progress row reverts to actionable
  state and a fresh handler dispatch occurs. NO human notification at any step.

## Sprint-2 Architecture Simplification (added 2026-07-01 post-Sutando-study)

Per Dais directive 2026-07-01 + study of `github.com/sonichi/sutando` (= 50 days, 600+ PRs,
proven autonomous build loop), Group J is OVER-ENGINEERED for what we actually need. Sutando
runs 50 days autonomously with ZERO per-failure-mode handlers — it relies on a much simpler
4-pattern architecture that handles every failure class generically.

### What Sutando does (= the pattern we adopt)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ONE proactive-loop, every 5 min via cron */5 * * * *                        │
│                                                                              │
│  Each pass:                                                                  │
│    0. status signal → state/core-status.json                                  │
│    0.5 quota-tracker → FULL / MEDIUM / LIGHT / MINIMAL budget                 │
│    1. process tasks/ (= owner asks from any channel)                          │
│    2. check pending-questions.md                                              │
│    3. health-check.py --fix  (= self-heal everything generic)                 │
│    4. read build_log.md (= persistent unified memory)                          │
│    5. pick highest ROI × probability-of-landing from infinite menu             │
│    6. ACT (= do it)                                                            │
│    7. update build_log.md                                                     │
│                                                                              │
│  ★ PIVOT-ON-BLOCK ★: if primary work blocked, switch lane, never idle.       │
│  ★ NO PER-FAILURE-MODE HANDLERS ★ — health-check.py + pivot covers all.      │
└────────────────────────────────────────────────────────────────────────────┘
```

### Group J → simplified mapping (= sprint-2 plan revised)

| original Group J handler | replaced by | rationale |
|---|---|---|
| **J1 auto-login (camofox + Gmail OTP)** | `health-check.py --fix` detects "Not logged in" + invokes credential-restore helper; SAME tool pattern handles every "auth refresh" failure mode generically | Sutando proves the agent doesn't need per-credential-store handlers — it needs ONE generic auth-repair flow |
| **J2 auto-rollback (git checkout)** | `health-check.py --fix` detects spawn-surface-drift + invokes git-restore helper | Same: ONE git-state-repair helper handles every drift class |
| **J3 auto-research (firecrawl npmjs)** | DELETED. If a hook needs a new module, the agent OPENS A PR via the standard build_log flow; auto-allowlist via PR review by another AI instance | Hook research is just normal build work, not a special recovery flow |
| **J4 model ladder** | DELETED. quota-tracker already drives FULL/MEDIUM/LIGHT/MINIMAL per pass — Claude Code's `/model` switch is one of the standard menu items, not a recovery handler | Quota-aware depth is the right primitive; "model upgrade for stalled adversary" was over-specific |
| **J5 fresh-start (tmux kill-server)** | `health-check.py --fix` detects tmux-server-corrupted + restarts; "fresh wallet" is a SCALE decision (= different feature, sprint-3 multi-instance spawn) | Restart is generic, wallet management is a different concern |
| **J6 token-kill-switch resurrection** | quota-tracker handles graceful degradation continuously; INV-11 hard kill-switch fires only when cumulative cost exceeds the 5×earn threshold past grace | Continuous adjustment > binary disable/resurrect |
| **J7 MOTHER queue** | gh issue label=bot2bot-review + a sibling AI instance picks it up via its own loop; PR auto-merge after another AI's adversary review with anicca-bot signature | Sutando uses `#bot2bot` Discord channel + `bot2bot-post` skill; we replace Discord with gh issues to keep it text-only and zero-side-channel |
| **J9 measurement-seam recovery** | quota-tracker handles measurement; if seam is broken, the same quota-aware degradation path applies | Folded into quota-tracker |
| **J8 anti-human-touch invariant** | **★ KEPT, STRENGTHENED ★** — Sutando keeps Telegram/Discord/voice channels open (≠ NO HUMAN); we are STRICTER and forbid all of them. The static analyzer + the blocklist regex stay | This is our unique invariant beyond Sutando |

### New canonical files (sprint-2)

Sprint-2 ships these instead of the original 9 J handlers:

| file | role | replaces |
|------|------|----------|
| `~/anicca/skills/_shared/proactive-loop.sh` | the single 5-min cron entry that runs steps 0-7 | original `*-core-healthcheck` + per-J handlers |
| `~/anicca/skills/_shared/health-check.py` (--fix) | generic auto-recovery for any detectable failure mode (auth, drift, tmux, etc.) | J1+J2+J5+J6+J9 |
| `~/anicca/skills/_shared/quota-tracker.py` | reads claude usage → budget per pass → adjusts depth | J4+J6+J9 partial |
| `~/anicca/skills/_shared/bot2bot.sh` | gh issue-based bot-to-bot coordination (review/PR) | J7 MOTHER queue |
| `~/loops/<slot>/build_log.md` | unified per-slot memory: what passed/failed/learned/next | lessons.jsonl + strategy.json + applied.jsonl (consolidated; jsonl streams kept as immutable audit log, build_log is the narrative summary) |
| `~/loops/<slot>/menu.json` | infinite-menu config: categories, ROI heuristics, novelty quota | strategy.json subset |
| `loop-healthcheck.sh` (existing) | KEPT as the 5-min launchd entry; just delegates to proactive-loop.sh | (unchanged role) |
| 9 J handler stubs in `lib/group_j.py` | DEPRECATED: dispatcher reduced to `health-check.py --fix` + `bot2bot.sh` only; `_HUMAN_TOUCH_PATTERNS` blocklist stays | J1-J7+J9 stubs |

### What each loop inherits (= generalized, every-loop)

★ The whole point of "generalized" is that the SAME proactive-loop.sh runs for gig, clip,
video, affiliate, bounty, and any future slot ★. Each slot supplies:

1. **`~/loops/<slot>/menu.json`** — what work this slot can do (= for gig: scan-requests,
   nurture-talk-rooms, deliver, evaluate; for clip: source-podcast, cut, post, monitor).
2. **`~/loops/<slot>/strategy.json`** — slot-specific tunable parameters (priority categories,
   skip categories, max_apply_per_pass, etc.). Still mutated by the adversary-gated REQ-C3
   flow.
3. **`~/loops/<slot>/build_log.md`** — slot's own narrative memory.

The shared `proactive-loop.sh` reads these per-slot files and runs the same 8-step body for
each slot. Self-improvement is uniform across all 6 loops because the LOOP is the same; only
the menu + strategy + log differ.

### Sutando patterns we adopt verbatim

- **build_log.md as single unified memory** (vs our 4-file lessons/strategy/applied/earnings split)
- **pivot-on-block rule** (vs our "BACKOFF → escalate") — block never stops the loop, only switches lane
- **quota-tracker → pass depth** (vs our binary kill-switch) — continuous degradation
- **infinite menu + ROI × probability pick** (vs our category-priority list) — every pass has work
- **self-contained skills, core boots without them** (vs our tight coupling) — slot disable mustn't break others

### Sutando patterns we DO NOT adopt

- Telegram / Discord / voice / phone bridges — REQ-J8 invariant prevents them
- "Owner sent task in last 5min → conversation mode" — we have no owner-conversation surface
- Meeting approval DM — we have no meeting concept
- "VERIFIED_CALLERS" 3-tier — we have no callers

### Sprint-2 work items (revised against Sutando architecture)

The original 13-row Sprint-1/Sprint-2 Scope Cut table (next section) is SUPERSEDED for the
Group J rows. The table below replaces J-row entries:

| sprint-2 item | acceptance criteria |
|---|---|
| proactive-loop.sh + 8-step body | per-slot invocation runs all 8 steps, writes build_log.md, exits cleanly when LIGHT/MINIMAL budget |
| health-check.py --fix | detects + auto-fixes: tmux dead, .last-pass stale, NOT_LOGGED_IN, trust dialog, hook module missing, drift; ZERO human-touch fallback |
| quota-tracker.py | reads claude usage; computes per-pass budget; adjusts depth; emits roi.jsonl row |
| bot2bot.sh | bidirectional gh issue-based coord with sibling instance; PR-comment loop; anicca-bot signed auto-merge after fresh adversary PASS |
| build_log.md schema + helper | per-slot narrative memory + reader/writer that proactive-loop uses every pass |
| menu.json schema + per-slot seeds | gig: requests/nurture/deliver/eval. clip: source/cut/post/monitor. video: gen/post. affiliate: slideshow/post. bounty: scan/deliver |
| Slot migration: gig first | gig-core's STARTUP prompt invokes proactive-loop.sh; lessons.jsonl historical kept, build_log.md becomes new write target |
| Other 5 slots migration | same pattern: clip, video, affiliate, bounty inherit; each ships own menu.json + strategy.json |

REMOVED from original scope cut: FIND-002 (Group J handler impls) — replaced by health-check
+ bot2bot pair. FIND-006 (Pure layer missing symbols), FIND-015 (real ed25519): unchanged.
Others adjusted accordingly.

## Sprint-1 / Sprint-2 Scope Cut (added 2026-07-01 post-Phase-3 adversary)

Phase 3 sprint-1 adversary FAILed with 18 findings. ~10 are addressed in-sprint by:
- 9 shell glue scripts under `~/anicca/skills/_shared/*.sh` (= the launchd-visible
  entry points named in REQ-A/B/D/E/F that production cron invokes)
- 4 trust-anchor / allowlist seed files (anicca-bot.pub placeholder,
  hook-modules-allowlist.txt, trusted-authors.json, payout-endpoint-allowlist.json)
- Spot fixes to lib/events.py (dead branch), lib/lessons.py (docstring), lib/mutation_gate.py
  (use _common.append_jsonl), lib/group_j.py (regex tightening)

The following findings are explicitly **scope-deferred to sprint-2** with honest rationale:

| finding | category | sprint-2 commitment |
|---------|----------|---------------------|
| FIND-002 | Group J handler real impls | Production camofox + Gmail OTP for J1; git checkout for J2; firecrawl + auto-PR for J3; model upgrade dispatch for J4; full fresh-start for J5; strategy reset for J6; mother-poll loop for J7; meas-seam probe for J9 |
| FIND-003 | Shell + JS AST analyzer | Add `shellcheck --format=json` parser + `tree-sitter-javascript` walker to `adversary_path_intersect`; sprint-1 ships Python-AST + substring-grep fallback |
| FIND-004 | proposal_loop._revise_draft no-op | Wire LLM call (Reflexion-style verbal revise) that rewrites the draft body against the previous round's adversary findings |
| FIND-005 | deliverable_loop no artifact revision | Same as 004 for the artifact: each FAIL round triggers an LLM-driven rewrite of the deliverable file, written as round-N+1 artifact |
| FIND-006 | Pure-layer missing symbols | Add `roi.compute_pass_row`, `passprep.compute_novelty_floor`, `passprep.pick_untried`, `manifest.validate` as full pure functions (sprint-1 has scaffold) |
| FIND-007 | REQ-B6 degraded dispatch missing in lib/roi.py | Compute the 100-row rolling estimate ratio in `roi.compute_pass_row`; when ratio > 0.5, call `self-recover.sh <slot> token-source-degraded <ratio>` via subprocess |
| FIND-008 | mutation_gate empty-verdict-file edge | Add test fixture: write `verdict.json` as size=0; assert mutation_gate treats it as FAIL (fail-closed); add corresponding code path |
| FIND-010 | PROP-E5 ZERO-call assertions in tests | Add assertion to test_spawn_pin.py: spy on subprocess calls; assert ZERO calls to `security find-generic-password`, telegram URLs, slack URLs |
| FIND-012 | tautological killswitch test | Replace inspect.signature check with a real test that exercises the boundary algebra (cost_jpy = 5*earn_jpy → False; cost_jpy = 5*earn_jpy + 1 → True past grace) |
| FIND-014 | MOTHER queue read-only path untested | Add fixture: chmod queue_path to 0o444; dispatch unknown reason; assert PermissionError handled gracefully (write to fallback path, log warning, do not crash) |
| FIND-015 | Real ed25519 sig | Replace fixture-protocol sha256-mix with real `nacl.signing` ed25519 verify; ship anicca-bot real keypair in CI secret |
| FIND-017 | Missing PROP tests | PROP-B5 rolling-window edge cases, PROP-C2 tail-50 exact-count, PROP-D1/D2/D3 cross-learn-share gh-rate-limit/retry/dedup-race, PROP-G1 manifest schema validation, PROP-H1 novelty quota |
| FIND-018 | Escalation regex list-literal bypass | Add regex matching `["--label", "escalation"]` list-form (= FIND-2-005 fix in v8.1) |

The sprint-2 commitment is **NOT** open-ended deferral — it is a documented next-sprint
contract with concrete file paths and module-level acceptance criteria. The MVP that
ships at sprint-1 boundary is a complete VERIFICATION LAYER (= 142 tests passing) plus
RUNTIME GLUE SCAFFOLDING (= 9 shell scripts + 4 seed files) that the slot's cron prompt
can invoke today. Sprint-2 fills in the production behaviors.

## Purity Boundary (sketch — formalized in 1b)

| layer | side-effect surface |
|-------|---------------------|
| PURE | `classify(HealthcheckContext) → mode`, `roi.compute(...)`, `roi.kill_switch_tripped(cost_jpy, earned_jpy, age_seconds, multiplier=5)`, novelty-quota math, rolling-window math, manifest field validation, lesson dedup hashing, `escalate.dedup_key(...)`, `escalate.normalize_evidence(...)` |
| I/O-BOUND | `tmux send-keys`, `gh issue` API (auto-merge PRs only, NEVER human-labelled issues), launchd plist, file writes to `~/loops/*`, browser CDP (camofox + Gmail OTP for auto-login), platform-payout API calls, `git fetch`/`checkout` for auto-rollback, firecrawl for auto-research |

The PURE layer accepts ALL inputs as typed records and returns typed results; the I/O layer is a
thin shell wrapper that snapshots state into a record, hands it to PURE, and applies the result.
