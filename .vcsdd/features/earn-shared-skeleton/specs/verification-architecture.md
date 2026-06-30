---
feature: earn-shared-skeleton
phase: 1b
mode: lean
---

# Verification Architecture — earn-shared-skeleton

## Purity Boundary (formal)

### PURE layer (testable without disk/network)

`skills/_shared/lib/` — Python modules + bash helper functions:

| symbol | inputs | output | side-effects |
|--------|--------|--------|--------------|
| `roi.compute(model_breakdown, fx_jpy, earnings_window, token_window)` | typed dicts | `RoiRow` dataclass | none |
| `roi.kill_switch_tripped(cumulative_tokens, cumulative_jpy, multiplier=5)` | int, int, int | bool | none |
| `passprep.compute_novelty_floor(applied_history, max_apply, ratio=0.1)` | jsonl rows, int, float | int (rows required novel) | none |
| `passprep.pick_untried(catalog, history)` | list, list | list (untried tuples) | none |
| `lessons.dedup_hash(requestId, outcome)` | str, str | str (sha256) | none |
| `roi.rolling_window(rows, window_hours, now_ts)` | rows, int, int | sublist | none |
| `manifest.validate(json_obj)` | dict | bool | none |
| `escalate.dedup_key(slot, reason, evidence)` | str×3 | str | none |
| `healthcheck.classify(pane_text)` | str | enum `{TMUX_DEAD, STALE, NOT_LOGGED_IN, TRUST_DIALOG, HOOK_ERROR, API_RATE_LIMIT, CRON_GONE, BACKOFF}` | none |

### I/O-BOUND layer (integration-tested or mocked at the seam)

| script | I/O surface |
|--------|-------------|
| `loop-healthcheck.sh` | `tmux capture-pane`, `tmux send-keys`, `tmux has-session`, `stat`, `gh issue create`, file writes to `~/loops/*` |
| `loop-roi.sh` | reads `~/loops/<slot>/earnings.jsonl`, reads claude session usage (env or fallback), writes `~/loops/<slot>/roi.jsonl` |
| `loop-improve.py` | reads `lessons.jsonl` + `strategy.json`, writes `strategy.json.next` |
| `cross-learn-read.sh` | `gh issue list` |
| `cross-learn-share.sh` | `gh issue create`, file append to `shared-lessons.jsonl` |
| `adversary-daily.sh` | spawn subagent (= main session does this), file reads under `.vcsdd/features/<slot>/` |
| `escalate.sh` | `gh issue create`, HTTPS POST to Telegram bot endpoint, file append |
| `loop-scale.sh` | reads `roi.jsonl`, edits `strategy.json` (gated by adversary like C3) |
| `loop-propose.sh` | `gh issue list`, `git clone` into `.worktrees/sandbox-*/` |

The I/O seam is the **only** layer that touches the outside world; PURE functions never call into
it. Tests in 2a target PURE coverage at ≥ 90% and exercise the I/O seam via stubbed fixtures.

## Proof Obligations (per requirement)

| ID | REQ | tier | property | mode |
|----|-----|------|----------|------|
| **PROP-A1** | A1 | 0 | `healthcheck.classify(pane_text=<empty>) ∧ ¬has_session ⇒ "TMUX_DEAD"` | property-test |
| **PROP-A2** | A2 | 0 | `mtime_age(last_pass) ≥ 90min ⇒ classify returns "STALE"` | property-test |
| **PROP-A3** | A3 | 0 | `pane contains "Not logged in" ⇒ classify returns "NOT_LOGGED_IN"` AND OAuth URL regex extracts a non-empty https URL when present | property-test + regex unit test |
| **PROP-A4** | A4 | 0 | `pane contains "Quick safety check" ⇒ classify returns "TRUST_DIALOG"` | property-test |
| **PROP-A5** | A5 | 0 | `pane contains "node:internal/modules/cjs/loader" ⇒ classify returns "HOOK_ERROR"` AND module-name extractor returns a valid npm package name | property-test |
| **PROP-A6** | A6 | 0 | `attempt N/10 where N ≥ 5 ⇒ classify returns "API_RATE_LIMIT"` | property-test |
| **PROP-A7** | A7 | 0 | `tmux has-session ∧ ¬cron_has_slot_job ⇒ classify returns "CRON_GONE"` | unit-test (stubbed CronList) |
| **PROP-A8** | A8 | 0 | `len(restart_log_within(3600s)) ≥ 5 ⇒ classify returns "BACKOFF"` | property-test |
| **PROP-A9** | A9 | 1 | mutual exclusion: for any pane_text, classify returns exactly one of the 8 enums, with deterministic priority order A1>A2>A3>…>A8 | property-test (1000 generated pane fixtures) |
| **PROP-B1** | B1 | 0 | `loop-roi.sh` end-of-pass writes EXACTLY one `roi.jsonl` row with all 13 required keys | unit-test |
| **PROP-B2** | B2 | 1 | `roi.compute` with `tokens_total > 0` returns `token_cost_jpy > 0` for every supported `model_breakdown`; never returns 0 cost for non-zero tokens (TRAP-5) | property-test (random model mixes, public rates inlined) |
| **PROP-B3** | B3 | 0 | `roi.compute` sums `amount` only over earnings rows with `receipt_id != null` AND `ts > previous_pass_ts` | unit-test |
| **PROP-B4** | B4 | 1 | `roi.kill_switch_tripped(t, j, m=5)` returns true ⇔ `t > 5*j`; the launchd guard short-circuits when `loop.disabled` exists | property-test + integration smoke |
| **PROP-B5** | B5 | 1 | `roi.rolling_window(rows, 168, now)` excludes rows with `ts < now - 168*3600` and never returns a partial-window misleading positive ROI | property-test |
| **PROP-C1** | C1 | 0 | every appended `lessons.jsonl` row has `evidence_id` matching a URL / payout_id / file-path regex; rows missing `evidence_id` are rejected | unit-test |
| **PROP-C2** | C2 | 0 | `loop-improve.py` reads exactly the last 50 lessons rows, not more, not fewer (FIND-008 carry-over) | unit-test |
| **PROP-C3** | C3 | 1 | `strategy.json.next` is committed to `strategy.json` ONLY if a fresh-context adversary verdict file `reviews/strategy-mutation-<sha>/verdict.json` exists with `overallVerdict == "PASS"` | integration-test (adversary seam stubbed by static-file fixture) |
| **PROP-D1** | D1 | 0 | `cross-learn-read.sh` returns valid JSON parseable as a list-of-issue-objects, even when `gh issue list` returns empty (returns `[]`, not crash) | unit-test |
| **PROP-D2** | D2 | 0 | `cross-learn-share.sh` invoked twice for the same `(requestId, outcome)` tuple creates exactly one issue and exactly one `shared-lessons.jsonl` row | property-test |
| **PROP-D3** | D3 | 0 | gh non-zero exit code logs warning and returns 0 (= does not abort caller) | unit-test |
| **PROP-E1** | E1 | 0 | `adversary-daily.sh` invocation spawns one Agent call with `subagent_type=vcsdd:vcsdd-adversary` (default model=opus) and the input message names the slot feature dir | unit-test (Agent call stubbed) |
| **PROP-E2** | E2 | 1 | adversary-builder loop is bounded ≤ 5 rounds; after 5 rounds without PASS, escalate fires exactly once | property-test |
| **PROP-E3** | E3 | 0 | round-5 FAIL path always reaches escalate.sh with the final verdict json in the evidence param | unit-test |
| **PROP-F1** | F1 | 0 | every `escalate.sh` invocation produces exactly one `gh issue create` AND one Telegram POST AND one `escalation-log.jsonl` row | integration-test |
| **PROP-F2** | F2 | 1 | dedup: two calls with the same `(slot, reason, evidence_hash)` within 24h produce exactly one issue, not two | property-test (mtime-based dedup) |
| **PROP-G1** | G1 | 0 | every `~/anicca/skills/earn/<slot>/manifest.json` validates against the JSON schema in `manifest.validate` | unit-test + integration scan |
| **PROP-G2** | G2 | 1 | skill code MUST NOT contain a write to its own `manifest.json` — verified by static grep gate in adversary-daily | static-analysis test |
| **PROP-H1** | H1 | 1 | `passprep.compute_novelty_floor(history, max_apply, 0.1)` returns ≥ `ceil(0.1 * max_apply)` when ≥ that many untried tuples exist; returns `len(untried)` otherwise; never throws | property-test |

## Verification Tiers (per CLAUDE.md plugin doctrine)

- **Tier 0** (tests + review only): A1-A8, B1, B3, C1-C2, D1, D3, E1, E3, F1, G1 — covered by unit/property tests + adversary review.
- **Tier 1** (property-tests + fuzzing): A9, B2, B4, B5, C3, D2, E2, F2, G2, H1 — these are invariants where lazy testing misses edges; property-test with random fixtures required.
- **Tier 2** (lightweight formal): not required for lean mode.
- **Tier 3** (full formal proof): not required for lean mode.

## Required vs Optional (lean mode)

In lean mode, the following PROP-XXX are `required: true` (= must finish as `proved` for Phase 6
convergence):

- PROP-A9 (mutual exclusion of self-heal modes — race / thrash prevention)
- PROP-B2 (token cost never zero — TRAP-5 mitigation, the whole reason this skeleton exists)
- PROP-B4 (token kill-switch correctness — INV-11 enforcement)
- PROP-C3 (no strategy mutation without fresh-context adversary — INV-10 enforcement)
- PROP-F2 (escalation dedup — prevent Telegram spam)

All other PROP-XXX are `required: false` in lean mode; they're still tested but a failure does not
block convergence (lean trade-off).

## Adversary Seam (= where the fresh-context subagent attaches)

Two seams the adversary must verify in this feature:

1. **Strategy-mutation seam** (REQ-C3 / PROP-C3): every `strategy.json` diff is reviewed before
   merge. Adversary reads `strategy.json.before`, `strategy.json.next`, the diff, and the relevant
   tail of `lessons.jsonl`. Verdict written to `reviews/strategy-mutation-<sha>/verdict.json`.

2. **Skeleton-itself seam** (REQ-E1): every night the daily adversary reviews the shared library
   itself (= `_shared/*.sh|*.py`) plus the slot it's pointed at, to catch drift in the skeleton.

## Coherence (CoDD) — downstream impact declaration

This feature directly impacts the following downstream artifacts:

- `~/anicca/skills/earn/gig/*` — gig-cli.sh + gig-healthcheck.sh refactor (task #14)
- `~/anicca/skills/earn/clip/*` — same
- `~/anicca/skills/earn/affiliate/*` — same
- `~/anicca/skills/earn/video/*` — same
- `~/anicca/skills/earn/bounty/*` — same
- `~/Library/LaunchAgents/ai.anicca.<slot>-core-healthcheck.plist` × 5 — point to shared script

Any change to a Group-A requirement (self-heal mode) propagates to all 5 plist files; any change
to Group-B (ROI format) propagates to all 5 cron-prompts. Coherence graph rebuild required when
either group's contract shifts.
