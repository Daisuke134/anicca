---
feature: proactive-loop-skeleton
phase: 5
mode: lean
sprint: 2
generated_at: 2026-07-01T08:00:00+09:00
---

# Purity Boundary Audit — proactive-loop-skeleton sprint-2

## Declared Boundaries

Per `specs/verification-architecture.md` Phase 1b, the implementation is partitioned into PURE and I/O-BOUND layers.

### PURE layer — `skills/_shared/lib/` (sprint-2 additions)

| Symbol | Module | Side-effects |
|--------|--------|--------------|
| `compute_budget(remaining_pct, minutes_until_reset)` | quota_tracker | none |
| `quantize_budget(b)` | quota_tracker | none |
| `apply_estimate_penalty(base_cost, ratio)` | quota_tracker | none |
| `should_route_mother_queue(neg_roi_days)` | quota_tracker | none |
| `is_dormant(consecutive_neg_7day_windows, age_days)` | quota_tracker | none |
| `count_consecutive_negative_windows(daily_roi_7day_jpy)` | quota_tracker | none |
| `is_allowed_sentinel_removal_call(call_source)` | quota_tracker | none |
| `compute_roi_score(item)` | menu | none |
| `is_blocker(item, slot_state)` | menu | none |
| `pick_next(menu, log_tail, history, blockers, now_ts, budget)` | menu | none |
| `classify_issue_from_snapshot(snap)` | health_check_v2 | none (post-FIND-017 fix: snap is frozen=True) |
| `select_fix_recipe(issue)` | health_check_v2 | none |
| `dispatch_highest_priority(snap)` | health_check_v2 | none (composes the 2 above) |
| `parse_bot2bot_issue(gh_json)` | bot2bot | none |
| `should_skip_step6(budget, tasks_pending, dormant, unfixable_count)` | proactive_loop | none |
| `format_log_section(...)`, `parse_log_section(text)` | build_log | none |
| `load_menu(path)` | menu | reads disk (= I/O at the boundary) |
| `write_dormant_sentinel(slot_dir, evidence)` | quota_tracker | writes disk (= I/O sink) |

### I/O-BOUND layer

| Script / function | I/O surface |
|-------------------|-------------|
| `proactive-loop.sh` | tmux capture, flock guard, exec python3 |
| `proactive-loop-dispatch.py` | os.environ read, file writes (state/, build_log.md, roi.jsonl), invokes lib.health_check_v2.dispatch_highest_priority (PURE) over a freshly-built snapshot |
| `health-check.py --fix` (sprint-3) | will wrap dispatch_highest_priority (PURE) with the real action execution |
| `bot2bot.post / poll / annotate_pr` | gh CLI subprocess, jsonl append |
| `credential-restore.sh / auto-allowlist.sh / auto-rollback.sh` | currently exit-1 scaffolds; sprint-3 wires camofox / firecrawl / git |
| `lib/build_log.append_pass` | disk append |
| `lib/_common.append_jsonl` (sprint-1 carry) | disk append |

## Observed Boundaries

Sample verification — `quantize_budget(b)`: pure function over a single float, returns enum, no side-effects.

Sample verification — `pick_next`: takes 6 explicit parameters, all immutable types (dict/list/set/int/enum). No environment / disk / clock access in the picker logic. The cadence gate reads `now_ts` from the parameter (not `time.time()`).

Sample verification — `classify_issue_from_snapshot`: HealthSnapshot is `frozen=True`; the function cannot mutate the input. Returns a list of Issue dataclasses. No I/O.

Sample verification — `count_consecutive_negative_windows`: takes a list, returns an int via tail-scan + break. No state.

I/O seam coverage — `proactive-loop-dispatch.py` STEP 3 builds `HealthSnapshot(**os.environ_extracted)` and passes to PURE `dispatch_highest_priority`. The I/O capture is at the dispatcher; the classification is pure.

## Sprint-2 Boundary Deviations

1. `write_dormant_sentinel(slot_dir, evidence)` writes disk — declared I/O-BOUND. The decision (is_dormant) and the action (write) are split.

2. `bot2bot.post` raises ValueError on REQ-B4 violation — semantically pure, but the test mocks `_gh_call`. Production wires real subprocess.

3. `proactive-loop-dispatch.py` mixes I/O orchestration with control flow. The PURE sub-decisions (`should_skip_step6`, `pick_next`, `dispatch_highest_priority`) compose into the orchestrator.

4. `load_menu` reads disk; the fallback path on parse error is documented + tested.

## Summary

Sprint-2 declares 14 PURE symbols + 6 I/O surfaces in the shared library. The verification-architecture.md PURE column maps each to a Tier 0/1 test.

Sampled PURE functions verified side-effect-free. I/O surfaces concentrated at:
- proactive-loop-dispatch.py (orchestrator)
- bot2bot.py (gh API)
- shell scripts (env-var pattern bridges to PURE Python)
- write_dormant_sentinel (declared I/O sink for REQ-Q5)
- load_menu (read with malformed fallback)
- build_log.append_pass (append-only)

Residual purity risks (acknowledged, documented):
- proactive-loop-dispatch.py mixes orchestration with `os.environ` access. Sprint-3: extract the parse-environment-into-snapshot step as a typed helper.
- `bot2bot.post` exception path tested via mock; sprint-3: integration test against a sandboxed gh instance.

These risks do not block Phase 6 convergence: the PURE helpers they compose remain side-effect-free.
</parameter>
