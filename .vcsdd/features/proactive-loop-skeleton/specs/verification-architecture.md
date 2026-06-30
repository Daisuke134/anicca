---
feature: proactive-loop-skeleton
phase: 1b
mode: lean
sprint: 2
---

# Verification Architecture — proactive-loop-skeleton (sprint-2)

## Purity Boundary

### PURE layer — `skills/_shared/lib/`

Pure functions are testable without disk/network/tmux/clock. All inputs explicit, all
outputs deterministic.

| symbol | module | inputs | output | side-effects |
|--------|--------|--------|--------|--------------|
| `compute_budget(remaining_pct, minutes_until_reset)` | quota_tracker | float, int | float (per-pass budget) | none |
| `quantize_budget(budget_per_pass)` | quota_tracker | float | enum `{FULL, MEDIUM, LIGHT, MINIMAL}` | none |
| `pick_next(menu, log_tail, history, blockers, now_ts, budget)` | menu | dict, list, list, set[str], int, BudgetEnum | menu-item dict OR None | none (FIND-3-002 fix: canonical signature matches REQ-M3 verbatim) |
| `apply_novelty_quota(picks, history, ratio)` | menu | list, list, float | list | none |
| `parse_log_section(text)` | build_log | str | dict (parsed pass record) | none |
| `format_log_section(pass_id, ts, budget, picked, outcome, next)` | build_log | typed | str | none |
| `classify_issue_from_snapshot(snapshot_dict)` | health_check | typed dict (= already-captured HealthSnapshot, see I/O note below) | list[Issue] | none |
| `select_fix_recipe(issue)` | health_check | Issue dict | FixAction dict | none |
| `is_blocker(menu_item, slot_state)` | menu | dict, dict | bool | none |
| `compute_roi_score(item)` | menu | dict | float | none |
| `parse_bot2bot_issue(gh_json)` | bot2bot | dict | TaskRow dict | none |
| `validate_novelty_key(tuple)` | menu | `(category: str, platform: str)` | bool | none |
| `mother_queue_route_due(estimate_ratio, days_degraded)` | quota_tracker | float, int | bool | none |

FIND-017 fix: `classify_health_issue` (renamed to `classify_issue_from_snapshot`) and
`select_fix_recipe` (renamed from `dispatch_fix`) operate on a dict that was already
captured by the I/O layer; the SNAPSHOT capture itself is I/O-bound (see below). The pure
half is the deterministic classification given a complete record.

### I/O-BOUND layer — shell scripts + integration modules

| script / function | I/O surface |
|-------------------|-------------|
| `proactive-loop.sh` | reads tasks/, pending-questions.md, build_log.md, menu.json, strategy.json; writes state/core-status.json, build_log.md, roi.jsonl; calls health-check.py + quota-tracker.py + bot2bot.sh; flock guard |
| `health-check.py capture_snapshot` | tmux capture-pane, send-keys, has-session; stat .last-pass + .last-start; reads spawn-surface pinned.json + signature; returns dict (= input to PURE classify) |
| `health-check.py --fix` | calls capture_snapshot (I/O) → classify (PURE) → dispatch fix actions (I/O); per-action I/O: tmux send-keys, git fetch + checkout, firecrawl npmjs, file appends to logs and .unfixable.jsonl |
| `credential-restore.sh` | drives camofox, reads .env, invokes gog gmail, tmux send-keys |
| `auto-allowlist.sh` | firecrawl, file edit, git commit/push, gh PR open |
| `auto-rollback.sh` | git fetch/checkout, verify_spawn_surface call |
| `quota-tracker.py` | reads claude session usage env vars OR pane footer fallback; writes roi.jsonl + build_log.md append; appends mother-recovery-queue.jsonl on 7d-degradation |
| `bot2bot.sh post/poll/annotate-pr` | gh issue create / list / pr comment; reads/writes bot2bot-sent.jsonl. NO auto-merge in sprint-2 (= sprint-3 commit, see FIND-003 fix in behavioral-spec.md REQ-B3) |
| `lib/build_log.py:append_pass` | append to build_log.md (= the I/O side; format_log_section is the pure half) |
| `lib/menu.py:execute_pick` | reads strategy.json + applied.jsonl history; calls pick_next (pure) |

## Proof Obligations

| ID | REQ | tier | property | mechanism | required (lean) |
|----|-----|------|----------|-----------|------------------|
| **PROP-P0-status** | P0 | 0 | core-status.json written at start with status=running; rewritten with status=idle at end of pass | unit-test (tmp_path) | YES |
| **PROP-P1-budget-quantize** | P1, Q2 | 1 | `quantize_budget(b)` returns FULL iff b>=3.0; MEDIUM iff 1.0<=b<3.0; LIGHT iff 0.1<=b<1.0; MINIMAL iff b<0.1; never throws (FIND-010 fix: boundaries half-open, consistent inclusive lower / exclusive upper) | property-test (1000 random b + 4 boundary fixtures: 2.99/3.0/0.99/0.0999) | **YES** (drives every pass's depth) |
| **PROP-P2-tasks** | P2 | 0 | proactive-loop step 1 reads tasks/, processes priority order (urgent > normal > low; tie = mtime), writes result file with same task-id, archives task | unit-test (tmp_path) | YES (FIND-007) |
| **PROP-P3-pending-q** | P3 | 0 | proactive-loop step 2 reads pending-questions.md; if unanswered AND budget>=LIGHT, log to build_log.md; NEVER post to Telegram/Slack/etc (REQ-J8) | unit-test | YES (FIND-007) |
| **PROP-P4-health-call** | P4 | 0 | step 3 invokes health-check.py --fix <slot> exactly once per pass; unfixable issues surface to .unfixable.jsonl | integration-test (health-check stubbed) | YES (FIND-007) |
| **PROP-P5-buildlog-read** | P5 | 0 | step 4 reads build_log.md tail; if absent, falls back to empty list | unit-test | YES (FIND-007) |
| **PROP-P6-menu-pick** | P6, M3 | 1 | step 5 calls pick_next(menu, log_tail, history, blockers) and uses the returned item; if pick_next returns None, transitions to EDGE-S4 path | integration-test | YES (FIND-007) |
| **PROP-P8-budget-depth** | P8 | 1 | FULL budget allows subagent spawn; MEDIUM blocks subagent; LIGHT blocks code-write; MINIMAL blocks all step 6 (only owner tasks + health + log) | property-test (4 budget × N candidate actions) | YES (FIND-007) |
| **PROP-P9-buildlog-append** | P9 | 0 | step 7 appends ONE section to build_log.md; section format matches REQ-M1 schema | unit-test (regex match on appended content) | YES (FIND-007) |
| **PROP-P10-exit** | P10 | 0 | end-of-pass writes status=idle to core-status.json; process exits with code 0 | unit-test | YES (FIND-007) |
| **PROP-H4-log** | H4 | 0 | every health-check fix attempt writes one line to health.log with {ts, issue, action, outcome, details} | unit-test | YES (FIND-007) |
| **PROP-Q1-snapshot** | Q1 | 0 | quota-tracker reads at end-of-pass; produces RoiRow with all 13 sprint-1 REQ-B1 fields | integration-test | YES (FIND-007) |
| **PROP-Q2-formula** | Q2 | 1 | budget_per_pass = remaining_pct / (minutes_until_reset / 5); when minutes_until_reset == 0 → MAX_FLOAT (=> FULL); when remaining_pct == 0 → 0 | property-test | YES (FIND-007) |
| **PROP-Q4-buildlog-summary** | Q4 | 0 | end-of-pass appends 1-line budget+cost summary to build_log.md AND a roi.jsonl row | integration-test | YES (FIND-007) |
| **PROP-B2-poll** | B2 | 0 | bot2bot.sh poll returns JSON list of {issue_url, comment_body, kind, ts}; empty list if no issues (NOT crash) | integration-test (gh stubbed) | YES (FIND-007) |
| **PROP-B3-annotate** | B3 | 1 (integration) | sprint-2 ships annotate-pr ONLY; an attempt to call `bot2bot.sh auto-merge` SHALL exit 1 with "auto-merge deferred to sprint-3 per FIND-003"; PROP fixture verifies the auto-merge code path does NOT exist | static-analysis + integration | **YES** (= FIND-003 critical closure) |
| **PROP-M2-menu-load** | M2 | 0 | menu.py load_menu(path) returns parsed schema OR falls back to {pending: investigate menu.json} when JSON malformed; logs the parse failure | unit-test | YES (FIND-007) |
| **PROP-M4-jsonl-preserved** | M4 | 0 | sprint-1 jsonl streams (lessons/earnings/applied/roi) are NEVER rewritten; build_log.md is the ONLY narrative writer | static-analysis (grep for write modes on the 4 jsonl paths) | YES (FIND-007) |
| **PROP-S2-seed-files** | S2 | 0 | gig migration creates ~/loops/gig/{menu.json, build_log.md, tasks/, results/} AND preserves applied.jsonl + lessons.jsonl + earnings.jsonl unchanged | integration-test on tmp_path | YES (FIND-007) |
| **PROP-S3-data-preserved** | S3 | 1 | byte-level diff: pre-migration vs post-migration of ~/loops/gig/{applied.jsonl, lessons.jsonl, earnings.jsonl, .last-start} == zero diff | static check (sha256 compare on these specific files) | YES (FIND-007) |
| **PROP-novelty-key-aligned** | M3 | 1 | novelty quota key is exactly the 2-tuple `(category, platform)` matching sprint-1 REQ-H1 (FIND-005 fix); any code using `(category, novelty)` or other variant FAILs static analysis | static-analysis | **YES** |
| **PROP-P7-pivot** | P7 | 1 | given a menu of N items where K are blocked, pick_next(menu, blocked_set) returns the highest-ROI item from the (N-K) unblocked subset; if N-K==0, returns None (= step 5 logs no-unblocked) | property-test | **YES** (= core "never-idle" rule) |
| **PROP-P11-skip** | P11 | 0 | proactive-loop exits without running step 6 iff one of EXACTLY 3 conditions hold (FIND-2-004 fix: aligns count with v2 REQ-P11 which has 3 conditions a/b/c after .presenter-mode removal); fixtures: (a) MINIMAL + empty tasks; (b) .dormant.sentinel present; (c) ≥3 unfixable cascade entries | unit-test (3 condition fixtures + 1 negative fixture asserting NO skip when none match) | YES |
| **PROP-H1-snapshot** | H1, H2 | 0 | HealthSnapshot captures all 8 fields enumerated in REQ-H1; missing fields default to None not "" | unit-test | YES |
| **PROP-H3-dispatch** | H3 | 1 | for each of 7 detectable issue classes, classify+dispatch maps to the correct FixAction recipe; multi-match resolves to the HIGHEST-PRIORITY issue per REQ-H3 priority order (FIND-2-002 fix: aligned with v2 REQ-H3 tie-break) | property-test (7 single-class fixtures + 5 multi-match fixtures asserting highest-priority dispatch) | **YES** (= the auto-recovery correctness gate) |
| **PROP-H5-unfixable** | H5 | 0 | when dispatch_fix fails, the issue is written to .unfixable.jsonl AND surfaces as a menu candidate next pass | integration-test | YES |
| **PROP-H6-no-human-touch** | H6 | 1 | static-analysis: anti_human_touch_violations (sprint-1) returns zero hits for all sprint-2 source files | static-analysis test | **YES** (REQ-J8 enforcement) |
| **PROP-Q3-fallback** | Q3(c) | 0 | when usage source unavailable, fallback (c) uses 2× penalty AND emits token_source="estimated" | unit-test | YES |
| **PROP-Q3d-ratio-escalation** | Q3(d) | 1 | when Σ token_source=="estimated" / Σ all > 0.5 over last 100 rows, the next computed `token_cost_jpy` is multiplied by 4× (not 2×); when ratio drops below 0.5 again, multiplier returns to 2× | property-test (synthetic 100-row windows crossing the 0.5 boundary both directions) | **YES** (FIND-2-003 fix; sprint-1 REQ-J9 line 2 verification-closed) |
| **PROP-Q3e-mother-queue** | Q3(e) | 1 | after 7 days of `roi_7day_jpy < 0` OR 7 days of `token_source=="estimated"` ratio > 0.5, exactly one row appended to ~/anicca/state/mother-recovery-queue.jsonl with {ts, slot, reason: degradation-7d, evidence_path}; NO row appended on day 6 or earlier; NO duplicate row on day 8 if day 7 already wrote one | integration-test (synthetic day-by-day fixture) | **YES** (FIND-2-003 fix; sprint-1 REQ-J9 line 3 verification-closed) |
| **PROP-Q5-dormant** | Q5 | 1 | when 14-day rolling ROI < 0 AND slot age > 14 days, .dormant.sentinel is created; when condition not met, sentinel is NOT created | property-test (boundary cases) | YES |
| **PROP-Q6-sentinel-rm** | Q6 | 1 | static-analysis: grep + AST walk of all sprint-2 source for any unlink/remove/rm/os.remove/Path.unlink/shutil targeting `.dormant.sentinel`; ONLY 2 call sites SHALL be present: (a) inside bot2bot.sh's `apply-sibling-response` handler when the response carries a `clear-dormancy` directive AND an adversary-PASS verdict; (b) inside the REQ-C3 mutation-gate post-merge hook when the merged strategy.json shows recovery markers; ALL other call sites FAIL the daily adversary review (FIND-009 fix: mechanism made concrete; the static-analyzer now has a finite expected call-site set) | static-analysis (AST + grep) + integration | YES |
| **PROP-blocker-gate** | P7, M3 | 0 | `is_blocker(menu_item, slot_state)` returns True iff the item's `blocker_check` field references a state predicate (e.g. "coconala_search_reachable", "tmux_alive") that evaluates False given slot_state; unknown blocker_check names default to False (= item NOT blocked, since we can't verify the block); each known blocker name has a unit-test fixture (FIND-015 fix) | unit-test (per known blocker_check name) | YES |
| **PROP-EDGE-S4-sink** | EDGE-S4 | 1 | when all categories are blocked AND bot2bot.sh post fails 3× retries (= EDGE-S4 sink), the loop writes a row to ~/loops/<slot>/.unfixable.jsonl AND exits 0; on the NEXT pass the .unfixable.jsonl row surfaces as a menu item; if that menu item also fails to resolve, the cycle is durable (= written to disk, not lost; FIND-018 fix) | integration-test (synthetic full-block + gh-failure fixture) | YES |
| **PROP-cadence** | M3(ii) | 1 | pick_next respects `min_cadence_seconds` — items whose last_fired_ts is within the window are excluded; items without the field are always selectable; sidecar cadence.json or build_log.md is the source of truth for last_fired_ts (FIND-2-005 fix) | property-test (100 random menu + history pairs) | YES |
| **PROP-B1-post** | B1 | 0 | bot2bot.sh post creates exactly one gh issue with correct label AND appends one row to bot2bot-sent.jsonl | integration-test (gh stubbed) | YES |
| **PROP-B4-no-human-escalation** | B4 | 1 | static-analysis: no code path creates a gh issue with label=escalation whose body contains owner/dais/human/please/manual handling phrases | static-analysis | **YES** (REQ-J8 reinforcement) |
| **PROP-M1-append-only** | M1 | 0 | build_log.md is opened in append-mode only; no path overwrites existing content | static-analysis + integration | YES |
| **PROP-M3-pick-next** | M3 | 1 | pick_next satisfies: returns argmax(roi×prob) over unblocked items; novelty quota fires at every 1/ratio-th pick | property-test | **YES** (= self-improvement engine) |
| **PROP-S1-startup-prompt** | S1 | 0 | gig-cli.sh STARTUP after migration is ≤200 characters (= 1-line invocation of proactive-loop.sh) | unit-test (file content length check) | YES |
| **PROP-S4-first-pass-touches** | S4 | 1 | after migration, first proactive-loop pass touches .last-pass AND appends to build_log.md AND applied.jsonl growth pattern preserved (verified by comparing pre-migration and post-migration cumulative growth rate) | integration-test on tmp_path slot | YES |
| **PROP-J8-blocklist** | J8 | 1 | sprint-1 PROP-J8 anti-human-touch invariant re-asserted over sprint-2 sources; static analyzer returns 0 hits for telegram.org/slack/twilio/etc | static-analysis test | **YES** (= the inherited gate) |
| **PROP-J8a-new-files** | J8a | 1 | proactive-loop.sh + health-check.py + quota-tracker.py + bot2bot.sh + build_log.py + menu.py each scanned by anti_human_touch_violations; ZERO hits | static-analysis test | **YES** |

## Verification Tiers

- **Tier 0** (tests + review): PROP-P0, P11, H1, H5, Q3, B1, M1, S1
- **Tier 1** (property-tests / static-analysis): PROP-P1, P7, H3, H6, Q5, Q6, B4, M3, S4, J8, J8a
- **Tier 2 / 3**: not required for lean mode.

## Required Set for Lean Convergence

`required: true` PROPs (= gate Phase 6 convergence):

1. **PROP-P1-budget-quantize** — drives every pass's depth
2. **PROP-P7-pivot** — the core "never-idle" rule
3. **PROP-H3-dispatch** — auto-recovery correctness
4. **PROP-H6-no-human-touch** — REQ-J8 enforcement on auto-fix surface
5. **PROP-M3-pick-next** — self-improvement engine correctness
6. **PROP-J8-blocklist** — anti-human-touch invariant
7. **PROP-J8a-new-files** — invariant enforcement on the NEW sprint-2 source files
8. **PROP-B4-no-human-escalation** — bot2bot must not become a back-door for human touch
9. **PROP-B3-annotate** — auto-merge SCOPE-DEFERRED enforcement (FIND-003 critical fix)
10. **PROP-novelty-key-aligned** — sprint-1 (category, platform) key (FIND-005 fix)

All other PROPs are `required: false` in lean mode.

## Adversary Seams

The daily adversary (= step 5 menu category, NOT a separate plist per Sutando
simplification) reviews:

1. **Menu mutations** — `menu.json` edits go through REQ-C3-equivalent fresh-context
   adversary review (= the strategy.json mutation gate from sprint-1 generalizes to
   menu.json mutations too).

2. **Auto-recovery surface drift** — health-check.py changes are reviewed weekly by a
   fresh-context adversary that checks for human-touch creep.

3. **Whole-skeleton drift** — once a week the adversary reviews `_shared/*` as a
   sibling-pull-target (= "would another instance's `git pull` from this state be safe?").

## Coherence (CoDD) — downstream impact

This feature impacts:
- `~/anicca/skills/earn/gig/*` — gig-cli.sh STARTUP rewrite (REQ-S1)
- `~/Library/LaunchAgents/ai.anicca.gig-core-healthcheck.plist` — calls
  proactive-loop.sh instead of the existing healthcheck dispatcher
- Sprint-3 commitment: same migration for clip / video / affiliate / bounty
- `~/anicca/skills/_shared/lib/group_j.py` — dispatcher reduced to `health-check.py` +
  `bot2bot.sh` calls; J1-J7+J9 stub functions DELETED; PROP-J8 blocklist kept and
  strengthened

Coherence graph: changes to Group P (proactive-loop) propagate to ALL future slot
migrations. Changes to Group H propagate to all health-check call sites.
