# Spec Review Verdict — claude-p-ceo-loop (Phase 1c, iteration 1)

Reviewer: fresh-context adversary (no Builder context). All claims below were verified by directly
reading the artifacts on disk and, where cited, by `gh repo clone`-ing Mahoraga / agent-os into
`/private/tmp/claude-501/.../scratchpad/` and reading the actual source.

## Overall verdict: **FAIL** (3 blocking findings)

## Per-dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Completeness | PASS (1 minor gap noted) |
| 2 | Testability | **FAIL** |
| 3 | Consistency | **FAIL** |
| 4 | Reality-grounding | **FAIL** |
| 5 | 安全境界 (safety boundary) | **FAIL** |
| 6 | token guardrail 実効性 | PASS (1 minor note) |

---

## BLOCKING findings

### B1 — `derive_roster` will include the non-loop `_comment` key and crash (REQ-CEO-001, PROP-CEO-001)

Verified directly: `cadence-contracts.json`'s actual top-level keys are
`['_comment', 'clip', 'affiliate', 'video', 'gig', 'bounty', 'founder-loop', 'pm-earner']` — **8 keys**,
where `_comment` is a `str` ("REQ-LV-100 — Cadence Contract declarations…"), not a `dict`. All other
7 keys are `dict`.

REQ-CEO-001 says the roster is derived as "cadence-contracts.json のキー集合から `founder-loop` を除いた
もの…に `clip-promote` を加えた集合" — this filters out only `founder-loop`, nothing else. A literal
implementation therefore produces a roster that still contains `"_comment"` as a fake 8th loop.
PROP-CEO-001's own test description ("cadence-contracts.json の**7キー**…→ roster から founder-loop が
消え clip-promote が加わり**計7件**になること") assumes the file has exactly 7 clean keys — it does not;
it has 8, one of which is a string. This mismatch between the spec author's mental model of the fixture
and the real file is exactly the kind of thing this dimension exists to catch.

Downstream impact: REQ-CEO-002's weekly snapshot step calls `cadence.streak()` /
`cadence_met()` for every roster entry, which does `contract["kind"]` on
`cadence-contracts.json["_comment"]`. Since that value is a string, this raises
`TypeError: string indices must be integers` — the CEO's WEEKLY pass would crash on its very first
snapshot read, every week, forever, until fixed.

**Required fix**: REQ-CEO-001 MUST specify `derive_roster` filters to keys whose value is a `dict`
(or explicitly excludes keys starting with `_`), and PROP-CEO-001's test fixture description must be
corrected to reflect the real 8-key file (roster = 7 real loops − founder-loop + clip-promote = 7,
with `_comment` explicitly excluded and asserted excluded in the test).

### B2 — CEO pass call appended after `founder-loop.sh`'s existing `exit "$RC"` becomes dead code half the time (REQ-CEO-070, REQ-CEO-071, PROP verification of REQ-CEO-070)

Verified directly by reading `~/anicca/skills/self/founder-loop/founder-loop.sh` in full. Its actual
last line (line 73) is:

```bash
exit "$RC"
```

`$RC` is the exit code of `record-earn.mjs` (line 24: `node "$RECORD" ... ; RC=$?`), and the script's
own comment on that same line documents this is NOT a rare path: "a persistent RPC-fail / corrupt-cursor
should alert" (INV-H6). I.e. whenever the RPC call fails or the ledger is corrupt, `$RC != 0` and the
script terminates at line 73.

REQ-CEO-070 says CEO pass is "既存ロジックが完了した**後**に追加で1回呼ばれるステップとして**末尾に追記
するのみ**" — a literal reading of "append at the tail of the file" places the new `ceo-pass.sh` call
line **after** `exit "$RC"`, which is unreachable bash whenever RC≠0. Since RC≠0 is an explicitly
documented non-rare failure mode of this exact script, this would make the entire CEO loop (bandit
update, allocation write, self-verification, weekly mail) **silently never run** on any wake where the
underlying money-recording had a transient RPC hiccup — a systemic reliability gap for a feature whose
entire job is "run reliably every Monday."

Worse: the verification-architecture's own Tier2 check for REQ-CEO-070 is `git diff` showing "既存行
（CEO pass呼び出し追加行を除く）に変更が無いこと" — this only diffs line **content**, not line
**order/reachability**. A naive-but-diff-clean implementation (new line inserted after `exit "$RC"`)
would **pass** this Tier2 check while the CEO loop is permanently dead code.

**Required fix**: REQ-CEO-070 MUST explicitly state the CEO pass invocation is inserted **before** the
final `exit "$RC"` line (i.e., "末尾" means before the script's control-flow exit, not textually after
the last byte of the file), and the Tier2 verification method must additionally assert CEO pass actually
runs on a wake where `$RC != 0` (not just on the happy path), not merely that unrelated lines are
byte-identical.

### B3 — Rollback restores a stale (already-bad) snapshot, not a known-good baseline (REQ-CEO-052, REQ-CEO-053, REQ-CEO-054)

REQ-CEO-052: "allocation テーブルを書き込む直前（REQ-CEO-040 の前）、THE SYSTEM SHALL 現在の allocation
テーブル全体を `ceo-rollback.json` に atomic 書込でスナップショットする" — this snapshot happens **every
single week**, unconditionally, right before that week's new allocation is written.

REQ-CEO-053: after **2 consecutive weeks** of `beats_previous_week == false`, THE SYSTEM SHALL roll back
to "`ceo-rollback.json` の直近スナップショット."

Trace through an actual 2-consecutive-miss scenario:
- Week N−1 (Monday): before writing, `ceo-rollback.json` is overwritten to hold the allocation from
  week N−2 (call it `A_good`). Agent writes new allocation `A_bad1`. End of week N−1: `beats_previous_week
  = false` (miss #1).
- Week N (Monday): before writing, `ceo-rollback.json` is overwritten **again** — this time to hold
  `A_bad1` (the allocation that just produced miss #1), clobbering `A_good`. Agent writes `A_bad2`.
  End of week N: `beats_previous_week = false` again (miss #2, consecutive_miss_count reaches 2).
- REQ-CEO-053 fires: rollback restores "the most recent snapshot" — which is now `A_bad1`, i.e. the
  very allocation that already underperformed at miss #1, **not** `A_good`.

This does not implement the design's stated intent ("配分が悪化させたら巻き戻す" / "自分の判断を数字で
検証する" — restore to the state before the degradation began). As specified, the "rollback" mechanism
is a no-op-adjacent action that swaps one already-bad allocation for another already-bad allocation.

This also directly answers one of the explicit review questions for dimension 5 ("rollback が無限ループ
…を生まないか"): nothing in REQ-CEO-053/054 specifies whether `consecutive_miss_count` resets after a
rollback fires. If it does not reset, and the restored (still-bad) allocation continues to underperform,
the system will fire a "rollback" **every subsequent week** — each one snapshotting-then-restoring a
degraded state, a livelock that never recovers `A_good` and never stops paging via `loop-report.sh`
until an agent manually intervenes.

**Required fix**: either (a) `ceo-rollback.json` must not be overwritten while a miss-streak is already
active (only snapshot the allocation from *before* the streak began, and only allow overwriting once
the streak resets to 0), or (b) keep a short history (≥2 snapshots) so rollback can reach back past the
most recent (already-bad) change, and (c) explicitly define what happens to `consecutive_miss_count`
after a rollback executes (reset to 0, and require a subsequent PASS before re-arming the rollback gate).

---

## MAJOR findings (non-blocking but must be addressed before Phase 2)

### M1 — `company_score` sums per-loop `combined_score` across mixed currencies without conversion (REQ-CEO-050, Consistency + Reality-grounding)

REQ-CEO-002(c) computes each loop's actual earn via `score_from_rows`'s existing fallback chain
`earn_usdc → earn_jpy → commission_jpy` (ground truth section, verified against
`ledger_metrics.py:27`) — different loops report in different currencies. REQ-CEO-050 then sums these
per-loop `combined_score` values directly into a single `company_score`, and the spec explicitly opts
out of any conversion twice ("通貨は loop 固有のまま混在させない — 通貨変換はしない" / "通貨/単位変換
はしない"). Since `company_score` is the sole signal driving the automatic rollback safety mechanism
(REQ-CEO-050〜054, and now also B3 above), summing JPY-scale numbers (hundreds–thousands) together with
USD-scale numbers (single/low-double digits) means `company_score` week-over-week movement will be
dominated by whichever loop happens to report in JPY, essentially independent of real dollar-value
company performance. This undermines the entire premise of "CEO が自分の判断を数字で検証する." Either
justify explicitly why this doesn't matter (e.g. all currently-registered loops report the same
currency — not true, `gig`/`affiliate` are JPY per the loop table in the design doc) or require
conversion before summation.

### M2 — Cited Mahoraga `BudgetPacer` (Lagrange dual-ascent) is never actually used by any REQ (Consistency vs. design doc's "採用する BP" section)

The design doc's "採用する BP" section cites "Mahoraga（LinUCB/Thompson bandit + **Lagrange 乗数の
budget pacer** + per-task hard reject）を…実装土台に" as the CEO's resource-allocation engine. Verified
by cloning Mahoraga: `budget_pacer.py::BudgetPacer` (dual-ascent `lambda_`, `filter_agents`,
`cost_weight_adjustment`) exists exactly as the ground-truth section of the behavioral spec describes
it in detail. But REQ-CEO-020〜025 (the only REQs that implement any budget gate) are 100% sourced from
`agent-os`'s simpler hard-stop-only filter (`filter_budget_compliant_agents`) — no REQ ever calls
`BudgetPacer.update()` / `filter_agents()`, and no REQ feeds a soft cost-penalty signal into the
bandit's reward (REQ-CEO-010's `compute_reward` is pure `earn/spend`, with no lambda term). This is a
silent scope-drop of a BP explicitly cited as adopted. Not harmful by itself (agent-os's hard-stop is
simpler and fine for lean mode), but the spec should say so explicitly instead of leaving readers to
infer that a documented dependency (with a whole paragraph of Ground Truth devoted to it) is actually
unused.

---

## MINOR findings

### m1 — `is_ceo_weekly_due` reuses a private symbol (REQ-CEO-071, Reality-grounding)

`weekly_report.py::_week_start` is underscore-prefixed (module-private by Python convention, verified
at `weekly_report.py:38`). REQ-CEO-071 requires `is_ceo_weekly_due` to reuse "`weekly_report.py::_week_start`
と同じ月曜起点ロジック" — importing a private symbol across modules works but is fragile/violates the
source module's own signaled contract. Recommend either promoting `_week_start` to a public helper in
`lib/` or re-deriving the (one-line) Monday-boundary formula locally with a comment citing equivalence,
rather than a cross-module private import.

### m2 — Escalation schema gate (REQ-CEO-060/061) is a pure formality by design — confirm it's intentionally layered with REQ-CEO-031

Confirmed this is *not* a blocking issue: REQ-CEO-062 requires any fleet/tier escalation to still pass
REQ-CEO-031's substantive gates (`scale_eligible`/`cooldown_ok`/`fleet_at_capacity`) before an actual
allocation write happens, so a low-effort `justification` string alone cannot force real resource
escalation — the schema gate only guarantees a paper trail exists (correctly, per BUILD AGENTS RIGHT:
content judgment stays with the agent / ex-post adversary review). Recommend making this layering
explicit as its own line in REQ-CEO-060/062 ("this schema gate does not itself authorize the escalation;
authorization is REQ-CEO-031's gate, called from the same decision path") so a future implementer
doesn't accidentally treat `validate_escalation_schema() == true` as sufficient permission to write the
allocation change.

---

## Reality-grounding summary (symbols verified to exist, exactly as cited)

All of the following were read directly and confirmed to match the spec's claims:
- `cadence.py::cadence_met(today_jst_date, contract, evidence) -> bool`, `streak(...)` — exist, pure.
- `cadence-contracts.json` — exists; **see B1 for the `_comment` key discrepancy**.
- `self-improve/weekly_report.py::run(loop, ...)`, `_week_start`, `_score_for_rows` calling
  `evaluator_mod.evaluate_stage1(path)["combined_score"]` — exist as described.
- `self-improve/lib/weekly_compare.py::beats_previous_week(this_week_score, last_week_score)` — exists.
- `self-improve/lib/ledger_metrics.py::score_from_rows(rows, view_weight=1.0, earn_weight=1.0)`,
  `evaluate_stage1_generic` — exist.
- `loop-scale/guardrails.py::scale_eligible/cooldown_ok/fleet_at_capacity/is_ban_suspected` — exist,
  exact signatures as cited.
- `founder-loop.sh`, `record-earn.mjs` (`writeCursorAtomic`, INV-H1..H6 comments), `report-args.mjs::
  founderReportArgs` — exist; **see B2 for the `exit "$RC"` ordering issue**.
- `loop-report.sh::lr_valid_evidence` evidence gate — exists.
- `clip-promote/clip-promote-status.mjs::clipPromoteStatus(payoutRows, todayJstDate)` — exists and is
  implemented (the stale `// RED` comment at the top of
  `clip-promote/tests/test_clip_promote_status.mjs` is leftover from an earlier TDD phase; the
  `claude-p-loop-verification` VCSDD feature that produced it is at `currentPhase: 6`, i.e. converged/
  PASS — REQ-CEO-004's "既存" claim is accurate).
- `record-payout.mjs::recordPayout` — exists.
- Mahoraga (cloned fresh, `pockanoodles/Mahoraga`): `LinUCBRouter` (`select_agent`, `update`,
  `save_state`/`load_state` via tmp+`os.replace`, `_init_agent` cold-start with identity `A`/prior `b`)
  and `ThompsonSamplingRouter` (`select_agent` via `np.random.beta`, `update` with
  `reward > threshold` → `alpha += 1` else `beta += 1`) — match the spec's description exactly.
  `budget_pacer.py::BudgetPacer` also exists exactly as described in Ground Truth — **but see M2, it's
  never actually called by any REQ.**
- agent-os (cloned fresh, `kai-linux/agent-os`): `budgets.py::monthly_spend_by_agent`,
  `budget_for_agent` (per_agent→default resolution, `None` on unset), `remaining_budget`,
  `is_hard_stopped`, `filter_budget_compliant_agents` (fail-open on missing `budgets` section, returns
  input unchanged), `check_budget_alerts` (dedup via `(month,agent,threshold)` key in
  `budget_alerts.jsonl`), `warn_if_budgets_missing` (one-shot latch) — all exist exactly as cited,
  including the fail-open behavior.
- `loop-registry.json` — confirmed absent on disk (0 hits via `find`), matching the spec's claim that
  this feature will be its first writer.

No hallucinated symbols were found anywhere in the two specs. The Reality-grounding FAIL verdict is
driven entirely by B1 and B2 (real files behaving differently than the spec's control-flow assumptions
require), not by any nonexistent API reference.

---

## What must happen before re-review

Fix B1, B2, B3 in the behavioral-spec.md / verification-architecture.md text (not just "we'll handle it
in implementation" — these are spec-level ambiguities/errors that a correct implementation could still
satisfy literally while being broken, per the Tier2-check gap noted in B2). Address M1 and M2 with an
explicit decision (fix or documented rationale). m1/m2 may be deferred to implementation-time judgment
calls but should get at least one sentence each in the spec.
