# Implementation Review (Phase 3) — claude-p-ceo-loop — iteration 2

Reviewer: fresh-context adversary (no Builder context, no iteration-1 adversary context; disk-only
evidence + live re-execution of my own adversarial scenarios).
Reviewed: `~/anicca/.worktrees/ceo-loop` (branch `feature/claude-p-ceo-loop`, HEAD `49db66a`) +
`~/profitable-claude/.worktrees/ceo-cost` (branch `feature/ceo-cost-events`, HEAD `f44063b`), against
`/Users/anicca/anicca-project/.vcsdd/features/claude-p-ceo-loop/specs/{behavioral-spec.md,verification-architecture.md}`.
Prior verdict on disk: `.../reviews/impl/iteration-1/verdict.md` (FAIL, blocking B-1 + B-2).

## Overall verdict: **PASS** (0 blocking findings)

---

## A. B-1 resolution — live re-verification (not grep, not trusting the commit message)

I independently constructed four scratch `CEO_STATE_DIR` scenarios (none reused from the commit's own
log) and ran `python3 run_pass.py` directly against each, then inspected the resulting
`loop-registry.json` byte-for-byte.

**A1 — reproduction of the exact iteration-1 exploit.** `clip` loop, existing
`capital_cap_usd:50, fleet_size_target:1`, `$0` realized profit (empty earn ledger), no
`ceo-allocation-ranges.json`, agent decision proposing `capital_cap_usd:5000` (100x) +
`fleet_size_target:100` (100x):
- Result: `capital_cap_usd` stayed **50.0** (not 5000), `fleet_size_target` stayed **1** (not 100).
- This is the precise scenario iteration-1 proved was a live capital/fleet runaway. It is now blocked.

**A2 — legitimate profit-backed capital increase must still be ALLOWED (not just "everything rejected").**
`clip` loop, `$100` realized profit via a real `clip-earn-ledger.jsonl` row, existing
`capital_cap_usd:50`, agent proposes `capital_cap_usd:120` (+70, within the $100 realized profit):
- Result: `capital_cap_usd` became **120** (the proposal passed through unmodified).
- Confirms the gate is a genuine profit-bound clamp, not a blanket freeze — REQ-CEO-030(b) semantics
  hold in both directions.

**A3 — fleet guardrail triad is wired to LIVE inputs, not stubs.** Same profit-positive `clip` loop,
`streak:10` (>=7, satisfies the streak condition) and `weekly_score=100` (well above the default
threshold 0.0), agent proposes `fleet_size_target:3` (small, plausible increase):
- This Mac's real free disk at test time: `shutil.disk_usage(state_dir).free` = **2.08 GB** (confirmed
  via a direct Python call in the same environment `run_pass.py` runs in).
- Result: `fleet_size_target` stayed **1** — rejected purely because of real disk space, despite a
  favorable streak and score. This proves `allocator.fleet_increase_allowed` → `guardrails.py`'s
  `scale_eligible(streak, weekly_score, weekly_score_threshold, disk_free_gb)` call is reading the
  actual filesystem, not a hardcoded/stubbed value — matching the commit message's own claim, which I
  did not trust until reproducing it independently with different input values.

**A4 — budget hard-stop (8-a) takes priority over profit-based capital increase.** `clip` loop with
`$1000` realized profit (very high) but a `ceo-budget-config.json`/`ceo-cost-events.jsonl` combination
that puts it over `hard_stop_usd:10` (`spend_usd:20`), agent proposes `capital_cap_usd:100`:
- Result: `capital_cap_usd` stayed **50** (unmodified) and the registry's `budget.hard_stopped` field is
  `true` — confirms `filter_budget_compliant_loops` (8-a) unconditionally blocks any resource increase
  for an over-budget loop, even one with abundant realized profit. This is the correct ordering per
  REQ-CEO-058 §⑧-a preceding §⑧-c.

**Guardrail source check**: `git diff a688137~1 49db66a -- skills/self/loop-scale/guardrails.py` is
empty — `guardrails.py` (the `scale_eligible`/`cooldown_ok`/`fleet_at_capacity` triad) is untouched by
this feature, confirming `allocator.fleet_increase_allowed` genuinely reuses the existing module (no
re-derivation, no threshold duplication) rather than a look-alike copy.

**Fail-open/fail-closed direction, checked against spec intent (behavioral-spec.md:814-816, not my own
opinion)**: "budget config 未設定・fx-config 未設定は fail-open... allocation の異常値は fail-closed
（REQ-CEO-042）... rollback の再武装は fail-closed 方向". Confirmed in code: `budget_for_loop`/
`filter_budget_compliant_loops` return "pass everything through" when `budgets` config is absent
(matches spec's explicit fail-open design, not a bug); `fleet_increase_allowed`'s `streak` input
defaults to `existing_loop_entry.get("streak", 0)` when absent, which fails `scale_eligible`'s
`streak>=7` check — fail-closed on an unknown streak, never fail-open. Both directions match spec intent
exactly, not just "some direction that happens to be safe."

**Capital gate's currency-conversion invariant (INV-CEO-1)**: `capital_increase_within_realized_profit`'s
third argument at the call site (`run_pass.py:286-288`) is `loop_realized_profit`, itself
`allocator.realized_profit_usd(per_loop_entries.get(loop, []), fx_config)` (`run_pass.py:265`) — the
same converted value used for the bandit reward and `company_score`. The escalation's
`weekly_realized_profit_usd` field (`run_pass.py:324`) uses the identical variable. No raw
native-currency (JPY) amount reaches either gate.

**Conclusion: B-1 is genuinely fixed.** All five previously-orphaned gates (`filter_budget_compliant_loops`,
`capital_increase_within_realized_profit`, `fleet_increase_allowed`, `should_scale_down`,
`validate_escalation_schema`) plus the previously-orphaned alert dedup trio
(`alert_key`/`should_fire_alert`/`record_alert_fired`) are called from `run_pass.py`'s step (8)/(3-c)
and I have live-reproduced their effect under four independent scenarios I constructed myself, including
one designed to test the "does a legitimate increase still go through" direction that a naive "reject
everything" patch could have faked.

---

## B. B-2 resolution

`command grep -c "record-cost-event.sh <loop>\|record_cost_event"` against all 6 in-scope CLI files:
`clip-cli.sh`=1, `video-cli.sh`=1, `clip-promote-cli.sh`=1 (anicca repo, worktree `ceo-loop`),
`affiliate-cli.sh`=1, `gig-cli.sh`=1, `bounty-cli.sh`=1 (profitable-claude repo, worktree `ceo-cost`) —
**6/6**. Each is a single natural-language instruction sentence inside the loop's own STARTUP prompt
("record this pass's own approximate token/compute cost... your own best-effort USD cost estimate...
your judgment call"), alongside the pre-existing `loop-report.sh` instruction — not a hardcoded number,
consistent with `building-effective-ai-agents.md`'s judgment/tool boundary (the agent supplies the
estimate; `record-cost-event.sh`/`record_cost_event_cli.py` are pure deterministic plumbing that only
validates the number is parseable and appends it).

I ran the CLI myself (not just read it): `CEO_STATE_DIR=/tmp/ceo-cost-test bash record-cost-event.sh clip
0.037` → exit 0, `ceo-cost-events.jsonl` contains
`{"loop": "clip", "month_key": "2026-07", "ts": "...", "usd_estimate": 0.037}`. This is a real
`budget.build_cost_event`/`record_cost_event` round-trip, not a stub.

`pm-earner` stays at 0 hits (`no such dir under anicca/skills/earn` for `polymarket-trade`, matching
B12's documented out-of-scope fallback rule — not an oversight).

**Conclusion: B-2 is genuinely fixed**, 6/6, with the agent-judgment boundary correctly preserved.

---

## C. Regression — self-executed, not inherited from the commit log

- **168/168 target-feature Tier-1 assertions**: I ran all 14 `test_*.py` files myself in
  `ceo/tests/` — `alert_dedup 6, bandit 23, budget_gate 12, budget_pacer 9, build_next_registry 7,
  capital_gate_and_scale_down 11, cooldown_rollback_state_machine 16, cost_events_and_spend 11,
  currency_conversion 17, derive_roster 8, escalation_and_reporting 18, guardrail_reuse 2,
  registry_bootstrap_and_ranges 6, rollback_pass_composition 22` = **168 passed, 0 failed**, 0 non-zero
  exit codes across all 14 files.
- **3 baselines, self-executed**: `bash test-founder-loop.sh` → `PASS` (all 6 named invariants H1-H6 +
  ledger/atomic/no-human/fail-safe checks). `bash test-record-earn.sh` → `PASS` (external-inflow,
  finalized-head, seam-gating, wallet-pin, atomic cursor). `node test-report-args.mjs` → `4/4 pass, 0
  fail`.
- **PROP-CEO-022 (RC≠0 wake) re-confirmed against the REWRITTEN run_pass.py**, not the iteration-1
  version: `FOUNDER_TEST=1 FOUNDER_DIR=/tmp/founder-test-i2 BASE_RPC_URL=http://127.0.0.1:1/invalid-rpc-seam
  bash founder-loop.sh` → `record_rc=1`, `founder-loop.sh exit code: 1` (== original RC, INV-H6 intact),
  and `ceo-pass.log`/`loop-registry.json`/bandit state/etc. were all written in the same run — the CEO
  WEEKLY pass completed a full cycle even though `record-earn.mjs` failed. `ceo-pass.sh`'s own
  `python3 run_pass.py >>... 2>&1; exit 0` plus `founder-loop.sh`'s `bash "$HERE/ceo/ceo-pass.sh" || true`
  wrapper (unchanged 1-line insertion, confirmed by `git diff` scope below) guarantees this never
  influences the caller's exit code — matches INV-H6/REQ-CEO-070.
- **INV-H1..H6 / INV-1..7 non-destructive**: `git diff a688137~1 49db66a --stat` (full iteration-1-base
  to current-HEAD diff) touches only `ceo/` files (5 new modules + `ceo-pass.sh` + `record-cost-event.sh`
  + `record_cost_event_cli.py` + 14 test files), a 1-line-changed CLI instruction sentence in 3
  `*-cli.sh` STARTUP prompts, and a 7-line insertion in `founder-loop.sh`. `record-earn.mjs` and
  `apps/landing/**` are both empty in this diff (`git diff --stat -- apps/landing/` /
  `-- skills/self/founder-loop/record-earn.mjs` both return nothing).

---

## D. Judgment-hardcoding check (Dimension 4)

`grep -rE "os\.remove|shutil\.rmtree|unlink" ceo/*.py` → 0 hits. `grep -rniE "llm|claude --model|
anthropic\.|openai" ceo/*.py` → 0 hits. `bandit.select_scores` is display-only (`8-b_ucb_scores_for_agent`,
printed for the agent, never auto-written into `allocation_decisions`) — the judgment/tool boundary from
iteration-1 (already PASS) is unchanged by this fix. The new code added in this iteration (five gate
call sites) is exclusively composition of pre-existing, already-unit-tested pure functions
(`allocator.py`/`budget.py`) — no new bandit-score-derived thresholds, no new regex/keyword judgment was
introduced to implement the fix. The `record_cost_event` USD number is explicitly agent-supplied
(natural-language instruction, "your judgment call"), not a literal constant in any `.py`/`.sh` file.

## E. Five-dimension summary

| Dimension | Verdict |
|---|---|
| 1. Spec準拠 + 骨抜き検査 | **PASS** — B-1's five gates + alert trio all live-called from `run_pass.py`, reproduced under 4 independent scenarios (malicious reject, legitimate allow, live-disk reject, budget-priority reject) |
| 2. テスト実効性 | PASS — 168/168 self-run GREEN, plus this review adds 4 fresh Tier-3 E2E scenarios `run_pass.py` itself was exercised under (none of which existed as a test file before this review) |
| 3. 安全境界（最重要） | **PASS** — capital/fleet runaway (iteration-1's core finding) is now blocked; RC≠0/INV-H6 self-verified against the rewritten file; no destructive ops |
| 4. 判断のハードコード検査 | PASS — no new judgment hardcoding introduced by the fix; bandit stays display-only; cost estimate stays agent-judgment |
| 5. copy元との整合 | PASS (structural) — `guardrails.py` reuse confirmed byte-identical (0-line diff) to pre-existing module; no new undefined symbols in the diff |

**Blocking count: 0.** Both iteration-1 findings (B-1, B-2) are genuinely resolved, independently
re-verified through live execution against scenarios this review constructed itself (not copied from the
commit's own claimed evidence log). This feature may advance past Phase 3 (`vcsdd-harden` /
`vcsdd-converge`).
