# Implementation Review (Phase 3) — claude-p-ceo-loop — iteration 1

Reviewer: fresh-context adversary (no Builder context; disk-only evidence + live re-execution).
Reviewed: worktree `~/anicca/.worktrees/ceo-loop` (branch `feature/claude-p-ceo-loop`, HEAD `8fad21e`),
against `/Users/anicca/anicca-project/.vcsdd/features/claude-p-ceo-loop/specs/{behavioral-spec.md,verification-architecture.md}`.

## Overall verdict: **FAIL** (2 blocking findings, 1 blocking-adjacent, several non-blocking notes)

---

## Dimension 1 — Spec準拠 + 骨抜き検査（hollow-implementation check）

**FAIL.**

The pure-function layer (`allocator.py`, `budget.py`, `bandit.py`, `budget_pacer.py`) is faithful to the
spec and to INV-CEO-1/INV-CEO-2 wherever it is actually *called*. But the orchestration layer
(`run_pass.py`, which implements REQ-CEO-058's ①–⑫ sequence) **never calls seven of the spec's
mandatory deterministic gates**, and the required external integration for REQ-CEO-020 is **0% done**.
This is exactly the "tests pass but the wiring is hollow" pattern the task asked me to check for.

### B-1 (BLOCKING) — Step ⑧'s sub-gates (⑧-a…⑧-e) are not implemented at all

`run_pass.py`'s step (8) block is:

```python
allocation_decisions = {}
gate_open = (cooldown_in == 0) and (not rollback_fired)
decisions_path = os.environ.get("CEO_AGENT_DECISIONS_JSON")
if gate_open and decisions_path and os.path.exists(decisions_path):
    candidate_decisions = _read_json(decisions_path, {})
    ranges_cfg = _read_json(os.path.join(state_dir, "ceo-allocation-ranges.json"), {})
    allocation_decisions = {
        loop: decision
        for loop, decision in candidate_decisions.items()
        if allocator.validate_allocation_ranges(decision.get("allocation", {}), ranges_cfg)
    }
```

The **only** gate applied to an agent-supplied decision is `validate_allocation_ranges` (REQ-CEO-042).
None of the following REQ-CEO-058 §⑧ sub-steps are invoked anywhere in `run_pass.py` (confirmed by
`grep -oE "allocator\.[a-zA-Z_]+|budget\.[a-zA-Z_]+"` against every call site in the file — full list
below):

| REQ | Function (exists in allocator.py/budget.py, unit-tested, 100% unreachable from run_pass.py) | Spec step |
|---|---|---|
| REQ-CEO-022 | `budget.filter_budget_compliant_loops` | ⑧-a |
| REQ-CEO-031 | `allocator.fleet_increase_allowed` (guardrail triad) | ⑧-c |
| REQ-CEO-030(b) | `allocator.capital_increase_within_realized_profit` | ⑧-c |
| REQ-CEO-032 | `allocator.should_scale_down` | ⑧-c |
| REQ-CEO-034 | `allocator.build_lesson_row` (→ `ceo-lessons.jsonl`) | ⑧-d |
| REQ-CEO-060 | `allocator.validate_escalation_schema` (→ `ceo-escalations.jsonl`) | ⑧-e |
| REQ-CEO-024 | `budget.alert_key` / `should_fire_alert` / `record_alert_fired` | ③-c (unconditional, not even in ⑧) |

`ceo-lessons.jsonl` and `ceo-escalations.jsonl` are never opened anywhere in `ceo/` (`grep -rn
"ceo-lessons\|ceo-escalations" --include="*.py" .` returns only the one docstring mention in
`allocator.py`, zero write sites).

**This is not a paperwork gap — I reproduced the resulting safety hole live.** With `CEO_STATE_DIR`
pointed at a scratch dir, an `existing loop-registry.json` for `clip` at `capital_cap_usd:50,
fleet_size_target:1`, **zero realized profit** (empty ledger → `company_score=0.0`), no
`ceo-allocation-ranges.json` (so `validate_allocation_ranges` — whose own docstring says "Fields absent
from `ranges_cfg` are not gated" — passes everything through unchecked), and a
`CEO_AGENT_DECISIONS_JSON` claiming `capital_cap_usd: 5000` (100×) and `fleet_size_target: 100` for that
same $0-profit loop, running `python3 ceo/run_pass.py` **wrote the runaway decision straight into
`loop-registry.json` unmodified**:

```json
"clip": {
  "allocation": {"capital_cap_usd": 5000, "fleet_size_target": 100},
  "budget": {"hard_stopped": false, "loop": "clip", "spend_usd": 0.0},
  "consecutive_bad_weeks": 0
}
```

This is precisely the scenario REQ-CEO-030(b) ("増額量は... 直近実現 realized profit の範囲内") and
REQ-CEO-031 ("1つでも false なら fleet 増加は allocation テーブルに書かれない") exist to prevent — a
100× capital increase and a 100× fleet increase for a loop with **$0** realized profit, written with
zero resistance because the gate functions that would have caught it are never called. Design spec's
own stated guardrail ("資本増額は on-chain 検証済み realized profit の範囲内") is currently enforced by
nothing but the honor system of whatever writes `CEO_AGENT_DECISIONS_JSON`.

`run_pass.py`'s docstring justifies *not* auto-computing step 8 from the bandit's argmax (REQ-CEO-012,
correctly) — but REQ-CEO-012 only forbids the *bandit* from picking the winner; it does not exempt the
*independent deterministic gates* (budget compliance, capital-increase bound, fleet guardrail triad,
escalation schema) from being applied to whatever the agent decides. `validate_allocation_ranges` being
wired in while its six siblings are not is an inconsistent, partial implementation of step ⑧, not a
deliberate scope choice — nothing in the spec, the commit message, or the code comments says these six
gates are deferred.

### B-2 (BLOCKING) — REQ-CEO-020 (per-loop `record_cost_event` hook) is 0/6 done

In-scope section names six files as this feature's own implementation scope:
`~/anicca/skills/earn/{clip,video,clip-promote}/<loop>-cli.sh` and
`~/profitable-claude/skills/human-funded/{affiliate,gig,bounty}/<loop>-cli.sh`. I grepped all six for
`record_cost_event` with `command grep` (bypassing any shell alias) — **0 matches in all 6 files**. I
then checked `git log`/`git status` on both the `~/anicca` main checkout and the `~/profitable-claude`
repo for these paths: the most recent commits touching them (`okdad2fed`, `002a8f1`, etc.) are all from
the unrelated, already-completed `loop-verification` feature (REQ-LV-*, task #7/#8/#11) — nothing
CEO-loop-related has ever touched these 6 files. `ceo-cost-events.jsonl` will therefore never receive a
row from any of the 6 in-scope loops in production, meaning `monthly_spend_by_loop`/`weekly_spend_by_loop`
return `{}` for every loop forever (not just pm-earner as the spec's fallback rule intends) — the
entire budget-observation/hard-stop mechanism is inert for all 7 roster loops today, not just pm-earner.
This also means PROP-CEO-004's B11 反証 requirement and PROP-CEO-020's "少なくとも1loopの既存
pass-endフックからrecord_cost_eventが実際に呼ばれ" requirement are both currently unsatisfiable.

### Non-blocking notes (dimension 1)
- INV-CEO-1 (currency conversion): PASS for every call site that *is* wired — `compute_reward`'s first
  argument and `company_score` both correctly route through `realized_profit_usd()`, matching
  PROP-CEO-013b/PROP-CEO-013's intent. (Moot for `capital_increase_within_realized_profit`'s third
  argument and the escalation's `weekly_realized_profit_usd` field, since those call sites don't exist —
  see B-1.)
- INV-CEO-2 (single `loop-registry.json` write site): PASS. `grep -rn "loop-registry.json"` across
  `ceo/` shows the only `open(...)`/`os.replace` pair is `allocator.write_registry_atomic`, called once
  from `run_pass.py` step (9). No shared-mutable accumulator exists anywhere in `ceo/`.
- `build_next_registry`'s 4-argument priority order (rollback_restore > allocation_decisions >
  existing_registry, budget from budget_snapshot_by_loop) matches REQ-CEO-044 exactly; confirmed both by
  reading the code and by the passing `test_build_next_registry.py` content-assertion (`rollback_restore`
  wins over `allocation_decisions` in the same call that also carries `budget_snapshot_by_loop` — the B9
  core property).
- REQ-CEO-043 (no `apps/landing/**` touched): PASS — `git diff --stat a688137~1 8fad21e -- apps/landing/`
  is empty.
- REQ-CEO-070 ordering (insertion before `exit "$RC"`, `founder-loop.sh`'s own 7 pre-existing lines
  unchanged): PASS — `git diff` shows a pure 7-line insertion, positioned before the final `exit "$RC"`.

---

## Dimension 2 — テスト実効性

**PASS for what exists, but the existing tests structurally cannot see B-1/B-2.**

I ran all 14 test files myself (`python3 test_*.py` per file, no framework):

```
alert_dedup 6, bandit 23, budget_gate 12, budget_pacer 9, build_next_registry 7,
capital_gate_and_scale_down 11, cooldown_rollback_state_machine 16, cost_events_and_spend 11,
currency_conversion 17, derive_roster 8, escalation_and_reporting 18, guardrail_reuse 2,
registry_bootstrap_and_ranges 6, rollback_pass_composition 22
= 168 passed, 0 failed  (matches the commit message's "168/168 assertions")
```

These are honest unit/property tests, not rigged to the implementation — e.g.
`test_capital_gate_and_scale_down.py`'s M4/m3 disproof assertions and `test_build_next_registry.py`'s
B9 content-assertion genuinely exercise the documented failure modes of the *pure functions*. But
`grep -l "run_pass" tests/*.py` returns **zero files** — no test imports or executes `run_pass.py`, so
no test could ever have caught B-1 (the pure `capital_increase_within_realized_profit` function is
correct in isolation; the defect is that `run_pass.py` never calls it). `test_rollback_pass_composition.py`
says this explicitly in its own docstring: "This is NOT the Tier3 E2E ... done in Phase 3, not here."

Per `verification-architecture.md`, PROP-CEO-020/021/022 are Tier 3 and **Required (lean) = true**. I
found no evidence any of the three had been executed before this review reached me: `~/.anicca-founder/
state/` has no `ceo-*` files at all, and `state.json`'s phase history shows a direct `2c→3` transition
with no interim Tier-3 run recorded. I executed PROP-CEO-022 and a real WEEKLY-pass cycle
(PROP-CEO-020's core mechanics) myself during this review (see Dimension 3) as fresh evidence — both
of those specific properties now have live evidence; PROP-CEO-021's full 4-week rollback replay against
real files has still not been executed end-to-end (only its pure-function composition, in
`test_rollback_pass_composition.py`).

---

## Dimension 3 — 安全境界（最重要）

**(a) founder-loop.sh insertion / RC propagation: PASS, live-verified.** I ran (not just read) the
real RC≠0 seam:

```
FOUNDER_TEST=1 FOUNDER_DIR=<tmp> BASE_RPC_URL=http://127.0.0.1:1/invalid-rpc-seam \
CEO_STATE_DIR=<tmp>/state bash founder-loop.sh
→ "founder-loop wake: realised_earn_usdc=0 record_rc=1 ..."; founder-loop.sh exit code: 1
→ <tmp>/state/ceo-pass.log: "ceo-pass ran (today_jst=2026-07-08)" + full WEEKLY-pass output
  (bandit/budget-pacer/miss-streak/rollback/verification/loop-registry.json all written)
```

`record-earn.mjs` failed (`record_rc=1`), CEO pass ran anyway (log proves it, and it completed a full
WEEKLY pass — bandit state, pacer state, miss-streak, rollback snapshot, verification row, and
`loop-registry.json` were all written to disk in this same run), and `founder-loop.sh`'s own final exit
code was still `1` (== the original `$RC`), confirming INV-H6 is intact. This directly satisfies
PROP-CEO-022.

**(b) `record-earn.mjs` / INV-H1..H6 / INV-1..7 non-destructive: PASS.** `git diff a688137~1 8fad21e`
touches only the 21 new `ceo/` files + a pure 7-line addition to `founder-loop.sh`; `record-earn.mjs` is
not in the diff at all. `grep -rl "record-earn"` inside `ceo/` only turns up docstring mentions (no
import/exec).

**(c) Rollback/cooldown livelock or capital runaway: FAIL — capital/fleet runaway is real, not
theoretical (see B-1's live reproduction above).** The rollback/cooldown state machine itself (arm →
freeze → decrement → reopen) is sound by trace and by the passing `test_cooldown_rollback_state_machine.py`
/ `test_rollback_pass_composition.py` — no livelock risk there. But because step ⑧'s deterministic
safety gates are unwired (B-1), the one guardrail this review actually cares about most — "an agent
decision cannot blow past realized-profit-bounded capital or the fleet-scaling triad" — does not hold
in the shipped code today. This is the review's single most severe finding.

---

## Dimension 4 — 判断のハードコード検査

**PASS.** `grep -rE "os\.remove|shutil\.rmtree|unlink"` → 0 hits (REQ-CEO-033). `grep -rniE
"llm|claude --model|anthropic\.|openai"` → 0 hits (REQ-CEO-061 — no content judgment). `bandit.py`'s
`select_scores` is explicitly non-mutating and does not pick a winner (REQ-CEO-012); `run_pass.py`'s
step 8 correctly refuses to auto-write the bandit's argmax and instead requires an external
`CEO_AGENT_DECISIONS_JSON` — the judgment/tool boundary that *is* implemented is implemented correctly.
The irony of this review is that the missing piece is the opposite failure mode from what this
dimension usually catches: instead of a hardcoded judgment overriding the agent, the deterministic
backstops that are supposed to constrain the agent's judgment are simply absent (B-1), which is a
Dimension-1/3 finding, not a Dimension-4 one.

---

## Dimension 5 — copy元との整合

**PASS (structural), with one caveat.** `bandit.py`'s LinUCB (`A`/`b`/`theta=A⁻¹b`/`ucb=exploit+explore`,
cold-start identity-A) and `budget_pacer.py`'s `BudgetPacer` (rolling-window dual ascent on `lambda_`,
never-empty hard-limit filter with cheapest-fallback) match the Ground-Truth section's description of
Mahoraga's `LinUCBRouter`/`BudgetPacer` API. `budget.py`'s `budget_for_loop`/`monthly_spend_by_loop`/
`filter_budget_compliant_loops`/`alert_key`+`should_fire_alert` dedup match the described agent-os
`budgets.py` shapes (`agent`→`loop` rename only). No undefined/hallucinated symbol names were found.
**Caveat**: I did not re-clone `pockanoodles/Mahoraga` or `kai-linux/agent-os` myself in this review (time
budget) — I am trusting the spec's own Ground Truth section, which states the prior iteration's adversary
already did a real `gh clone` and confirmed these signatures. Given B-1/B-2 above, I'd weight this
dimension's PASS lower than I would in a review with no other findings — but nothing here contradicts
the copy-source claim on its own.

---

## Summary

| Dimension | Verdict |
|---|---|
| 1. Spec準拠 + 骨抜き検査 | **FAIL** — B-1 (step ⑧ sub-gates unwired, live capital/fleet-runaway reproduced), B-2 (REQ-CEO-020, 0/6 loop-CLI hooks) |
| 2. テスト実効性 | PASS (168/168 honest and self-verified GREEN) but structurally blind to B-1/B-2; Tier-3 E2E had not been run before this review |
| 3. 安全境界（最重要） | **FAIL** — (a)/(b) PASS and live-verified; (c) capital/fleet runaway is live-reproducible today |
| 4. 判断のハードコード検査 | PASS |
| 5. copy元との整合 | PASS (structural, not independently re-cloned this iteration) |

**Blocking count: 2** (B-1, B-2). Both must be fixed — and re-verified with a real
`CEO_AGENT_DECISIONS_JSON` run that proves the capital/fleet/budget/escalation gates now reject an
out-of-policy decision, plus real `record_cost_event` grep hits in all 6 loop CLI files — before this
feature can advance past Phase 3.
