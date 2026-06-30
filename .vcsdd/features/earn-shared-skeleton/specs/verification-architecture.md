---
feature: earn-shared-skeleton
phase: 1b
iteration: 2
mode: lean
addresses_findings:
  - FIND-003 (purity boundary widened — classify input is full HealthcheckContext record)
  - FIND-010 (verification-tool tier corrected for orchestration-level PROPs)
  - FIND-014 (required:true set augmented — promoted PROP-A5, PROP-C1, PROP-G2_runtime)
---

# Verification Architecture — earn-shared-skeleton (v2, post-1c-iter1 FAIL)

## Purity Boundary (formal)

### PURE layer (testable without disk/network/tmux/clock)

`skills/_shared/lib/` — Python modules + small bash helpers. All functions are total (= no
exceptions on valid inputs) and deterministic. NONE reach the I/O surface — every input is
explicitly passed in.

| symbol | inputs (typed) | output | side-effects |
|--------|----------------|--------|--------------|
| `healthcheck.classify(ctx: HealthcheckContext)` | `{slot:str, pane_text:str, has_session:bool, last_pass_mtime:int\|None, last_start_mtime:int\|None, restart_log_entries:list[int], cron_has_slot_job:bool, now_ts:int}` | `Mode` enum: one of `{BACKOFF, TRUST_DIALOG, NOT_LOGGED_IN, API_RATE_LIMIT, HOOK_ERROR, CRON_GONE, TMUX_DEAD, STALE, STALE_FIRST_PASS, ALIVE_FRESH}` | none |
| `healthcheck.extract_oauth_url(pane_text: str)` | str | `str\|None` (anchored https://claude.com/cai/oauth/...) | none |
| `healthcheck.extract_hook_module_name(pane_text: str, allowlist: list[str])` | str, list[str] | `dict {name:str\|None, valid:bool, allowlisted:bool}` | none |
| `roi.compute_token_cost_jpy(model_breakdown: list[BreakdownEntry], rates: dict, fx_usdjpy: float, token_source: str)` | typed | `float` | none |
| `roi.compute_pass_row(...)` | typed | `RoiRow` dataclass | none |
| `roi.kill_switch_tripped(cum_cost_jpy: float, cum_earned_jpy: int, age_seconds: int, multiplier: int = 5, grace_seconds: int = 7*86400)` | float, int, int, int, int | `bool` | none |
| `roi.rolling_window(rows: list[dict], window_seconds: int, now_ts: int, data_floor_seconds: int)` | typed | `float\|None` | none |
| `passprep.compute_novelty_floor(applied_history: list, max_apply: int, ratio: float)` | list, int, float | `int` | none |
| `passprep.pick_untried(catalog: list, history: list)` | list, list | `list` | none |
| `lessons.validate_evidence_id(value: str, type_tag: str)` | str, str | `bool` (URL/payout_id/file path well-formed) | none |
| `lessons.dedup_hash(requestId: str, outcome: str)` | str, str | `str` (sha256 hex) | none |
| `manifest.validate(json_obj: dict)` | dict | `bool` | none |
| `escalate.normalize_evidence(evidence: str)` | str | `str` (timestamps/round-numbers stripped) | none |
| `escalate.dedup_key(slot: str, reason: str, evidence: str)` | str×3 | `str` (sha256 hex) | none |
| `escalate.is_duplicate(dedup_key: str, log_rows: list[dict], now_ts: int)` | str, list, int | `bool` (24h-window check) | none |

`HealthcheckContext` carries every input every detection rule needs (FIND-003 fix). `classify` is
now genuinely pure: a closed function over the record.

### I/O-BOUND layer (integration-tested or stubbed at the seam)

| script | I/O surface |
|--------|-------------|
| `loop-healthcheck.sh` | `tmux capture-pane`, `tmux send-keys`, `tmux has-session`, `stat`, file reads/writes to `~/loops/*`, calls `escalate.sh` |
| `loop-roi.sh` | reads `~/loops/<slot>/earnings.jsonl` + `cumulative.json`, reads claude session usage (env or fallback), writes `~/loops/<slot>/roi.jsonl` + `cumulative.json` |
| `loop-improve.py` | reads `lessons.jsonl` + `strategy.json`, writes `strategy.json.next`, calls `adversary-daily.sh strategy-mutation` |
| `cross-learn-read.sh` | `gh issue list` |
| `cross-learn-share.sh` | `gh issue create`, flock + atomic rewrite of `shared-lessons.jsonl` |
| `adversary-daily.sh` | invokes `claude -p '<prompt>'` (top-level fresh session); top-level claude issues `Agent(subagent_type=vcsdd:vcsdd-adversary)`; writes `.vcsdd/.../reviews/.../verdict.json` |
| `escalate.sh` | `gh issue create`, HTTPS POST to Telegram, file append `escalation-log.jsonl` |
| `loop-scale.sh` | reads `roi.jsonl`, calls `adversary-daily.sh strategy-mutation` before edits |
| `loop-propose.sh` | `gh issue list`, `git clone` into `~/.worktrees/sandbox-*/` |

The PURE layer is unit-testable; the I/O layer is exercised via two paths: (a) seam-stubbed unit
tests where the I/O call is replaced with a fixture-driven stub, AND (b) end-to-end smoke tests
that actually fire the script in a sandboxed `$LOOPS_ROOT` (= a tmp dir, not `~/loops/`) so the
real disk effects are observed without polluting prod state.

## Proof Obligations (per requirement, FIND-010 retiered)

| ID | REQ | tier | property statement | mechanism | required (lean) |
|----|-----|------|--------------------|-----------|------------------|
| **PROP-A-classify** | A1-A9 | 1 | for every `HealthcheckContext` drawn from a deterministic generator, `classify(ctx)` returns EXACTLY ONE of 10 modes; priority dominance preserved | property-test (Hypothesis or fast-check; 10k cases) | **YES** (was PROP-A9; now covers entire group) |
| **PROP-A-oauth** | A3 | 0 | `extract_oauth_url(s)` returns Some(url) iff `s` contains a substring matching the anchored regex `^https://claude\.com/cai/oauth/authorize\?[a-z0-9_=&%+\.\-]+$` AND nothing else; rejects subdomain look-alikes, IP literals, javascript: schemes | unit-test (corpus of 30 fixtures incl. phishing variants) | **YES** (FIND-005 security) |
| **PROP-A-hook-allowlist** | A5 | 0 | `extract_hook_module_name(s, allowlist)` returns `{name:None}` OR `{name:m, valid:true, allowlisted:true}` iff m matches strict npm regex AND m in allowlist; rejects path traversal, `--`-flag injection, shell metas | unit-test (corpus of 40 fixtures incl. RCE attempts) | **YES** (FIND-004 security, FIND-014 promotion) |
| **PROP-B1-schema** | B1 | 0 | `roi.compute_pass_row(...)` output round-trips through `RoiRowSchema.validate`; missing/extra fields raise | unit-test | YES |
| **PROP-B2-cost-formula** | B2 | 1 | for any non-empty `model_breakdown` with `tokens > 0` AND every model_id in the rates table, `compute_token_cost_jpy` returns `> 0`; AND for a fixed Sonnet-only fixture `(1M in, 1M out) at FX=150`, returns exactly `(1×3 + 1×15)×150 = 2700.00` ± 0.01; AND raises (does not silently return 0) on unknown model_id | property-test + unit-test with golden fixtures | **YES** (FIND-002 critical) |
| **PROP-B3-earnings** | B3 | 0 | `compute_pass_row` sums only earnings rows with `receipt_id != null` AND `platform_api_response_sha256 != null` AND `previous_pass_ts < ts ≤ this_pass_ts` | unit-test | YES |
| **PROP-B4-killswitch** | B4 | 1 | `kill_switch_tripped(cost, earned, age, m=5, grace=7*86400)` returns False whenever `age < grace` (= first-week grace); returns True iff `age ≥ grace ∧ cost > 5*earned`; both inputs are jpy (= dimensional check via type annotations + a fuzz test asserting type-coherence) | property-test (1k fuzz cases) | **YES** (FIND-001 critical) |
| **PROP-B5-rolling** | B5 | 1 | `rolling_window(rows, w, now, floor)` returns None when `(now − first_ts) < floor`; otherwise returns sum over rows where `(now − w) ≤ ts ≤ now`; never returns a partial-window number when caller-floor not met | property-test | YES |
| **PROP-B6-estimate** | B6 | 1 | when `token_source == "estimated"`, output `token_cost_jpy` is exactly 2× what it would be at the same byte→token ratio without penalty; conservative direction is preserved | property-test | YES |
| **PROP-C1-evidence** | C1 | 0 | `validate_evidence_id(v, type)` accepts iff (a) `type=url` AND v matches URL regex, OR (b) `type=payout_id` AND v matches platform-specific id regex, OR (c) `type=file` AND v is an absolute path; rejects paraphrase strings | unit-test (corpus of 50 fixtures incl. paraphrase rejections) | **YES** (FIND-014 promotion, TRAP-4) |
| **PROP-C2-tail50** | C2 | 0 | `loop-improve.py` reads EXACTLY 50 rows (or all if file shorter), not more | unit-test (file with 51 rows; assert 50 read) | YES |
| **PROP-C3-mutation-gate** | C3 | 1 (integration) | `rename strategy.json.next → strategy.json` happens IFF a verdict.json at the expected path exists with `overallVerdict == "PASS"` AND that path is under `.vcsdd/features/<slot>/reviews/strategy-mutation-<sha>/` | integration-test in sandbox: stub the adversary-daily call to write a fixture verdict, exercise both PASS and FAIL branches | **YES** (FIND-007 carry, INV-10) |
| **PROP-D1-empty** | D1 | 0 | `cross-learn-read.sh` returns valid JSON parseable as a list, even when `gh issue list` returns empty (returns `[]`, not crash, not non-zero exit) | unit-test (gh stubbed to empty stdout) | YES |
| **PROP-D2-claim-check** | D2 | 1 (integration) | claim-check pattern: the tentative row is written BEFORE the `gh issue create` is invoked; if gh succeeds, row is updated to `status: shared`; if gh fails 3× retry, row stays `status: pending` AND a 24h cooldown prevents re-attempts | integration-test in sandbox (gh stubbed) | YES |
| **PROP-D3-graceful** | D3 | 0 | gh non-zero exit code logs warning to expected log file and the script returns 0 | unit-test | YES |
| **PROP-E1-trigger** | E1 | 0 (integration) | `ai.anicca.<slot>-adversary-daily.plist` exists, loads in launchctl, and its ProgramArguments invokes `adversary-daily.sh <slot> nightly`; the script body invokes `claude -p` with the templated prompt | static-analysis on plist + dry-run smoke test (does NOT spawn a real adversary; verifies the spawn surface) | YES (retiered from FIND-010(2)) |
| **PROP-E2-loop-bound** | E2 | 1 (integration) | given a fixture set of FAIL verdicts, the orchestrator stops at round 5 and calls escalate.sh exactly once | integration-test using fixture verdicts (no real subagent spawned) | YES (retiered from FIND-010(3)) |
| **PROP-E3-escalate-path** | E3 | 0 (integration) | round-5 FAIL path includes the round-5 verdict sha256 in the evidence param | integration-test | YES |
| **PROP-E4-mutation-seam** | E4 | 1 (integration) | calling `adversary-daily.sh strategy-mutation <slot> <sha>` writes the verdict under `reviews/strategy-mutation-<sha>/`; manifest input matches the typed schema | integration-test | YES |
| **PROP-F1-order** | F1 | 0 (integration) | invocation order: dedup-check → log-append-pending → gh create → tg post → log-update-posted; ANY step failure leaves the log row in a recoverable state | integration-test (gh + tg stubbed) | YES |
| **PROP-F2-dedup** | F2 | 1 | `is_duplicate(key, log_rows, now)` returns True iff a row exists in log with `ts > (now − 86400)` AND `dedup_key == key`; `normalize_evidence` strips unix ts substrings and `round-N` substrings so cosmetic rotation doesn't defeat dedup | property-test (corpus of 100 evidence pairs that differ only in stripped fields → must collapse to same dedup key) | **YES** (FIND-007 critical) |
| **PROP-G1-manifest-schema** | G1 | 0 | `manifest.validate(json)` accepts iff all fields present with correct types AND `schema_version == 1` | unit-test | YES |
| **PROP-G2-static** | G2 | 1 | static-analysis grep: for each `~/anicca/skills/earn/<slot>/`, no source file contains a write target whose resolved path is `<that slot's dir>/manifest.json`. Heuristic covers literal strings, simple variable concatenation, and Python `Path(__file__).parent / "manifest.json"` constructions; flags any indirect cases for human review | static-analysis test (AST walker for Python; grep + AST for shell+JS) | **YES** (FIND-014 promotion, INV-13 trust model) |
| **PROP-G2-runtime** | G2 | 1 (integration) | `events.jsonl → earnings.jsonl` runner verification: a skill emitting a fake `event: "earn"` with a forged `receipt_id` but no matching `platform_api_response_sha256` is rejected; ONLY real platform-API-verified events propagate to `earnings.jsonl`; rejected events surface a `skill-emitted-fake-earn` lesson row | integration-test (platform API stubbed) | **YES** (FIND-015 fix, INV-13 active half) |
| **PROP-H1-novelty** | H1 | 1 | `compute_novelty_floor(history, max_apply, 0.1)` returns `min(ceil(0.1 * max_apply), len(untried(catalog, history)))` for any inputs; never throws; never returns negative | property-test | YES |

## Verification Tiers (CLAUDE.md plugin doctrine)

- **Tier 0** (tests + review only): PROP-A-oauth, PROP-A-hook-allowlist, PROP-B1-schema,
  PROP-B3-earnings, PROP-C1-evidence, PROP-C2-tail50, PROP-D1-empty, PROP-D3-graceful,
  PROP-G1-manifest-schema, plus the integration-tagged Tier 0 PROPs (PROP-E1, PROP-E3, PROP-F1)
  which are orchestration-surface checks not requiring fuzzing.
- **Tier 1** (property-tests + fuzzing): PROP-A-classify, PROP-B2-cost-formula, PROP-B4-killswitch,
  PROP-B5-rolling, PROP-B6-estimate, PROP-C3-mutation-gate, PROP-D2-claim-check, PROP-E2-loop-bound,
  PROP-E4-mutation-seam, PROP-F2-dedup, PROP-G2-static, PROP-G2-runtime, PROP-H1-novelty.
- **Tier 2 / 3**: not required for lean mode.

The "(integration)" annotation marks PROPs whose Tier-N test exercises a real sandboxed effect
(tmp dir, stubbed external command), as opposed to a pure unit test (FIND-010 retiering).

## Required Set for Lean Convergence (FIND-014 fix)

In lean mode, the following PROPs are `required: true` and MUST finish as `proved` for Phase 6
convergence. The set was rebuilt to cover security, dimensional correctness, anti-slop, and the
INV trust model — not just easy-to-prove invariants:

1. **PROP-A-classify** — mutex + 10-mode coverage (= the single non-pollution gate of all self-heal)
2. **PROP-A-oauth** — anti-phishing (FIND-005)
3. **PROP-A-hook-allowlist** — anti-RCE (FIND-004 critical)
4. **PROP-B2-cost-formula** — TRAP-5 (FIND-002 critical)
5. **PROP-B4-killswitch** — INV-11, dimensional correctness (FIND-001 critical)
6. **PROP-C1-evidence** — TRAP-4 faithfulness (FIND-014 promotion)
7. **PROP-C3-mutation-gate** — INV-10 (FIND-007 was about F2 not C3; C3 stays required)
8. **PROP-F2-dedup** — Telegram-spam prevention (FIND-007 critical)
9. **PROP-G2-static** — INV-13 static half (FIND-014 promotion)
10. **PROP-G2-runtime** — INV-13 active half (FIND-015 fix)

All other PROPs are `required: false` in lean mode — they're still tested but failure does not
block convergence.

## Adversary Seams

Two seams the daily adversary must verify:

1. **Strategy-mutation seam** (REQ-C3 + REQ-E4 / PROP-C3 + PROP-E4): every `strategy.json` diff
   reviewed before merge. Manifest = `{reviewType: "strategy-mutation", strategyBefore: <path>,
   strategyNext: <path>, lessonsTail: <path>, sha: <sha>}`. Verdict written to
   `reviews/strategy-mutation-<sha>/output/verdict.json`.

2. **Skeleton-itself seam** (REQ-E1): every night the daily adversary reviews
   `_shared/*.{sh,py}` plus the slot it's pointed at, catching drift in the skeleton itself.

## Coherence (CoDD) — downstream impact

This feature impacts:
- `~/anicca/skills/earn/{gig,clip,affiliate,video,bounty}/*` — each slot's runner refactor
- `~/Library/LaunchAgents/ai.anicca.<slot>-{core,adversary}-healthcheck.plist` × 5 each
- `~/anicca/skills/_shared/hook-modules-allowlist.txt` (NEW, REQ-A5 seed file)
- `~/anicca/skills/_shared/adversary-daily-prompt.tmpl` (NEW, REQ-E1 spawn prompt)
- `~/.openclaw/.env` — needs `TG_BOT_API`, `TG_DAIS_CHAT_ID` (existing convention; REQ-F1)

Any change to a Group-A rule propagates to all 5 slot plists; any change to Group-B (rate table,
ROI schema) propagates to all 5 cron-prompts.
