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
daily 03:00 fresh-context adversary runs per slot. Human is touched exactly once: when
`escalate.sh` posts a `label=escalation` GitHub issue that triggers a Telegram notification.

## Scope (in vs out)

**In scope** — the 9 shared scripts in `~/anicca/skills/_shared/`:
`loop-healthcheck.sh` · `loop-roi.sh` · `loop-improve.py` · `loop-scale.sh` · `loop-propose.sh` ·
`cross-learn-read.sh` · `cross-learn-share.sh` · `adversary-daily.sh` · `escalate.sh`. Plus: the
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
- **`~/loops/escalation-log.jsonl`** — append-only; one row per `escalate.sh` invocation; used by
  REQ-F2 dedup.

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
  (d) IF a URL extracted, call `escalate.sh <slot> needs-login <url>`;
  IF NOT, call `escalate.sh <slot> oauth-extract-failed <truncated pane sha256>`.

- **REQ-A4** WHEN `classify(ctx) == TRUST_DIALOG`, THE SYSTEM SHALL `tmux send-keys "1" Enter`.

- **REQ-A5** WHEN `classify(ctx) == HOOK_ERROR`, THE SYSTEM SHALL:
  (a) grep the failing `require(...)` path,
  (b) extract a candidate module name AND validate against:
      `^@?[a-z0-9][a-z0-9._\-/]*$` (strict npm package regex)
      AND inclusion in `~/anicca/skills/_shared/hook-modules-allowlist.txt`
      (curated allowlist; addresses FIND-004 RCE: NO auto-install of arbitrary modules),
  (c) IF validated AND in allowlist, run `npm install -g <name>`;
  IF validation fails OR name not in allowlist, call
  `escalate.sh <slot> hook-module-unrecognized <module_name_sha256>` (= human review required for
  new modules; this is the conservative anti-RCE default per FIND-004).

- **REQ-A6** WHEN `classify(ctx) == API_RATE_LIMIT`, THE SYSTEM SHALL
  `tmux send-keys "/model haiku-4-5" Enter`.

- **REQ-A7** WHEN `classify(ctx) == CRON_GONE`, THE SYSTEM SHALL re-inject the slot's STARTUP
  prompt via `send-keys` (looking up the STARTUP from `~/anicca/skills/earn/<slot>/STARTUP.txt`,
  a file the slot's `<slot>-cli.sh` writes on its own first run).

- **REQ-A8** WHEN `classify(ctx) == BACKOFF`, THE SYSTEM SHALL NOT restart. THE SYSTEM SHALL call
  `escalate.sh <slot> backoff-cap "<last 5 audit verdicts>"`.

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
rows, THE SYSTEM SHALL call `escalate.sh <slot> token-source-degraded "<ratio>"` (= human review:
the measurement seam itself is broken, not a transient outage).

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

#### REQ-E3 — Round-5 escalation

WHEN 5 rounds elapse without `overallVerdict: PASS`, the top-level claude SHALL call
`escalate.sh <slot> adversary-stalled "<sha256 of round-5 verdict.json>"`.

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

##### Trust anchor — ed25519 signature with keychain-sealed pubkey (ROUND-3-001 fix)

`spawn-surface.pinned.json` enumerates sha256 of files 1-5 above AND its own sha256
(self-reference is now explicit, not implicit). It is accompanied by a detached signature
`spawn-surface.pinned.json.sig` (ed25519, raw 64 bytes).

The ed25519 PUBLIC KEY (32 bytes raw) is stored in the macOS Keychain under generic-password
service `anicca-trust-anchor-pubkey` (created at first install via `security add-generic-password
-s anicca-trust-anchor-pubkey -a anicca -w <base64-pubkey>`; subsequent writes require user
authentication via Touch ID / sudo). Updating the pubkey requires a user gesture
(macOS-enforced); a runaway script CANNOT silently overwrite the pubkey.

At the top of `loop-healthcheck.sh`, `loop-roi.sh`, `loop-improve.py`, `adversary-daily.sh`,
`escalate.sh`, THE SYSTEM SHALL perform THIS ORDERED CHECK:

(a) Read pubkey from keychain via `security find-generic-password -s anicca-trust-anchor-pubkey
    -w 2>/dev/null`. IF read fails (keychain unset, locked, denied) → halt without side effect
    AND call `escalate.sh <slot> trust-anchor-unreadable ""`.
(b) Verify `spawn-surface.pinned.json.sig` against `spawn-surface.pinned.json` using the pubkey
    (via `openssl pkeyutl -verify -pubin -inkey <pubkey-pem-tmpfile> -sigfile <sig> < <pinned>`
    or `signify -V`). IF verification fails → halt AND call
    `escalate.sh <slot> spawn-surface-sig-invalid ""`.
(c) Compute current sha256 of each of files 1-6 and compare against `pinned.json` values
    (including pinned.json's own sha against the self-sha entry in the file). ANY mismatch →
    halt AND call `escalate.sh <slot> spawn-surface-drift
    "<file>:<observed>:<pinned>"`.

Updating `pinned.json` + `.sig` requires Dais signing with his private key (held only by him;
NOT on the Mac filesystem). The CI pipeline rejects any push touching either file unless the
top commit on the branch is signed by Dais's git-signing key AND its body contains literal
token `SPAWN-SURFACE-PIN-UPDATE` (enforced by a `.github/workflows/spawn-surface-guard.yml`
that is itself out of scope for this feature but is a downstream commitment).

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

(1) ed25519-signed pin manifest with keychain-sealed pubkey (ROUND-3-001 closure) +
(2) OS-level 0444+uchg (unchanged) +
(3) structured-analysis adversary gate (ROUND-3-002 closure).

### Group F — Escalate (`escalate.sh`, the only human gate)

#### REQ-F1 — Invocation contract (FIND-006 fix)

`escalate.sh <slot> <reason> <evidence>` SHALL perform the following IN THIS ORDER:

1. Compute `dedup_key = sha256(slot || "\x00" || reason || "\x00" ||
   normalize_evidence(evidence))` where `normalize_evidence` strips substrings matching
   `\b\d{10}\b` (unix timestamps) and `\bround-\d+\b` and `\bts:\d+\b` from `evidence` so that
   rotating identifiers do not defeat dedup (addresses FIND-007 critical bug).
2. Scan `~/loops/escalation-log.jsonl` rows where `ts > (now_ts − 86400)`; IF a row exists with
   `dedup_key == dedup_key_here`, EXIT 0 without further action (= 24h dedup window;
   FIND-007 fix).
3. Append `{ts, slot, reason, evidence_sha256, dedup_key, status: "pending"}` to
   `escalation-log.jsonl`.
4. Construct gh args with the evidence shell-escaped through `printf '%q'` (not raw
   interpolation; addresses FIND-006(d) shell injection). Title is fixed: `[escalation][<slot>][<reason>]`. Body is the evidence file content with backticks fenced.
5. `gh issue create --label escalation --title "<title>" --body-file <tmpfile>`. ON success
   capture the issue URL.
6. POST to Telegram endpoint:
   - URL = `${TG_BOT_API}/sendMessage` where `TG_BOT_API` is read from `~/.openclaw/.env`
     (existing secret store). Token-in-URL form per Telegram API.
   - chat_id = `TG_DAIS_CHAT_ID` (also from .env).
   - body = `{chat_id, text: "[escalation][<slot>][<reason>] <issue_url>",
     disable_web_page_preview: true}`.
   - 3 retries with exp backoff. On terminal failure, log to
     `~/.openclaw/logs/escalation-tg-failed.jsonl` and continue (= the gh issue is the durable
     record; TG is the notification).
7. Update the `escalation-log.jsonl` row's `status` to `"posted"` and add `issue_url`,
   `tg_message_id` (or `tg_failed: true`).

#### REQ-F2 — Dedup (FIND-007 critical fix)

The dedup mechanism IS the 24h-window scan of `escalation-log.jsonl` defined in REQ-F1 step 2.
The dedup key IS the `dedup_key` defined in REQ-F1 step 1. PROP-F2 verifies this concrete
mechanism (no more "evidence_hash undefined" gap).

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

- **EDGE-10** (NEW) Telegram POST succeeds but `escalation-log.jsonl` update fails → next
  invocation of `escalate.sh` re-scans `escalation-log.jsonl` and sees the row at
  `status: "pending"`; treats as in-progress, does not re-fire.

## Purity Boundary (sketch — formalized in 1b)

| layer | side-effect surface |
|-------|---------------------|
| PURE | `classify(HealthcheckContext) → mode`, `roi.compute(...)`, `roi.kill_switch_tripped(cost_jpy, earned_jpy, age_seconds, multiplier=5)`, novelty-quota math, rolling-window math, manifest field validation, lesson dedup hashing, `escalate.dedup_key(...)`, `escalate.normalize_evidence(...)` |
| I/O-BOUND | `tmux send-keys`, `gh issue` API, launchd plist, file writes to `~/loops/*`, browser CDP, Telegram POST, platform-payout API calls |

The PURE layer accepts ALL inputs as typed records and returns typed results; the I/O layer is a
thin shell wrapper that snapshots state into a record, hands it to PURE, and applies the result.
