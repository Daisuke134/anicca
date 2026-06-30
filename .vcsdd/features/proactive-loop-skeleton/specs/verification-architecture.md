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
| `compute_budget(remaining_pct, minutes_until_reset)` | quota_tracker | float, int | enum `{FULL, MEDIUM, LIGHT, MINIMAL}` | none |
| `quantize_budget(budget_per_pass)` | quota_tracker | float | enum | none |
| `pick_next(menu, log_tail, history)` | menu | dict, list, list | menu-item dict | none |
| `apply_novelty_quota(picks, history, ratio)` | menu | list, list, float | list | none |
| `parse_log_section(text)` | build_log | str | dict (parsed pass record) | none |
| `format_log_section(pass_id, ts, budget, picked, outcome, next)` | build_log | typed | str | none |
| `classify_health_issue(snapshot)` | health_check | HealthSnapshot dict | list[Issue] | none |
| `dispatch_fix(issue)` | health_check | Issue dict | FixAction dict (= the recipe, not yet executed) | none |
| `is_blocker(menu_item, slot_state)` | menu | dict, dict | bool | none |
| `compute_roi_score(item)` | menu | dict | float | none |
| `parse_bot2bot_issue(gh_json)` | bot2bot | dict | TaskRow dict | none |

### I/O-BOUND layer — shell scripts + integration modules

| script / function | I/O surface |
|-------------------|-------------|
| `proactive-loop.sh` | reads tasks/, pending-questions.md, build_log.md, menu.json, strategy.json; writes state/core-status.json, build_log.md, roi.jsonl; calls health-check.py + quota-tracker.py + bot2bot.sh; flock guard |
| `health-check.py --fix` | tmux capture-pane, send-keys, has-session; stat .last-pass + .last-start; reads spawn-surface pinned.json + signature; git fetch + checkout; firecrawl npmjs; file appends to logs and .unfixable.jsonl |
| `quota-tracker.py` | reads claude session usage env vars OR pane footer fallback; writes roi.jsonl + build_log.md append |
| `bot2bot.sh` | gh issue create / list / merge; reads/writes bot2bot-sent.jsonl |
| `lib/build_log.py:append_pass` | append to build_log.md (= the I/O side; format_log_section is the pure half) |
| `lib/menu.py:execute_pick` | reads strategy.json + applied.jsonl history; calls pick_next (pure) |

## Proof Obligations

| ID | REQ | tier | property | mechanism | required (lean) |
|----|-----|------|----------|-----------|------------------|
| **PROP-P0-status** | P0 | 0 | core-status.json written at start with status=running; rewritten with status=idle at end of pass | unit-test (tmp_path) | YES |
| **PROP-P1-budget-quantize** | P1, Q2 | 1 | `quantize_budget(b)` returns FULL iff b>3; MEDIUM iff 1≤b≤3; LIGHT iff 0.1≤b<1; MINIMAL iff b<0.1; never throws | property-test (1000 random b) | **YES** (drives every pass's depth) |
| **PROP-P7-pivot** | P7 | 1 | given a menu of N items where K are blocked, pick_next(menu, blocked_set) returns the highest-ROI item from the (N-K) unblocked subset; if N-K==0, returns None (= step 5 logs no-unblocked) | property-test | **YES** (= core "never-idle" rule) |
| **PROP-P11-skip** | P11 | 0 | proactive-loop exits without running step 6 iff one of 4 conditions hold; the 4 are enumerable | unit-test (each condition fixture) | YES |
| **PROP-H1-snapshot** | H1, H2 | 0 | HealthSnapshot captures all 8 fields enumerated in REQ-H1; missing fields default to None not "" | unit-test | YES |
| **PROP-H3-dispatch** | H3 | 1 | for each of 7 detectable issue classes, classify+dispatch maps to the correct FixAction recipe; ambiguous issues raise (don't silently dispatch the wrong fix) | property-test (7 attack fixtures + happy paths) | **YES** (= the auto-recovery correctness gate) |
| **PROP-H5-unfixable** | H5 | 0 | when dispatch_fix fails, the issue is written to .unfixable.jsonl AND surfaces as a menu candidate next pass | integration-test | YES |
| **PROP-H6-no-human-touch** | H6 | 1 | static-analysis: anti_human_touch_violations (sprint-1) returns zero hits for all sprint-2 source files | static-analysis test | **YES** (REQ-J8 enforcement) |
| **PROP-Q3-fallback** | Q3 | 0 | when usage source unavailable, fallback estimate uses 2× penalty AND emits token_source="estimated" | unit-test | YES |
| **PROP-Q5-dormant** | Q5 | 1 | when 14-day rolling ROI < 0 AND slot age > 14 days, .dormant.sentinel is created; when condition not met, sentinel is NOT created | property-test (boundary cases) | YES |
| **PROP-Q6-sentinel-rm** | Q6 | 1 | static-analysis: no code path removes .dormant.sentinel except (a) bot2bot.sh response handler, (b) successful adversary-PASS on strategy.json mutation | static-analysis + integration | YES |
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
