# Spec Review Verdict — claude-p-ceo-loop (Phase 1c, iteration 2)

Reviewer: fresh-context adversary (no Builder context, no iteration-1 adversary context — this instance
has zero memory of authoring either). All claims below were verified by directly reading the artifacts
on disk: the two updated spec files, the iteration-1 verdict, the design doc §CEO LOOP / §採用する BP,
and the real source of every cited symbol (`~/anicca/skills/self/{cadence.py,cadence-contracts.json,
founder-loop/founder-loop.sh,self-improve/**,loop-scale/guardrails.py}`, and fresh reads of the
already-cloned `Mahoraga`/`agent-os` repos under
`/private/tmp/claude-501/.../scratchpad/{Mahoraga,agent-os}`).

## Overall verdict: **FAIL** (2 blocking findings — new, not carried over)

## Per-dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Completeness | **FAIL** (1 major gap, 1 minor gap) |
| 2 | Testability | **FAIL** |
| 3 | Consistency | **FAIL** |
| 4 | Reality-grounding | PASS (all cited symbols re-verified to exist exactly as described) |
| 5 | 安全境界 (safety boundary) | **FAIL** |

---

## Part A — Disposition of iteration-1's findings (B1/B2/B3/M1/M2/m1/m2)

All were checked against the live filesystem, not just re-read as prose.

| Finding | Status | Evidence |
|---|---|---|
| **B1** (`_comment` crash) | **RESOLVED** | Re-read `~/anicca/skills/self/cadence-contracts.json` directly with `json.load` + type-introspection: confirmed 8 top-level keys, `_comment` is `str`, the other 7 (`clip`/`affiliate`/`video`/`gig`/`bounty`/`founder-loop`/`pm-earner`) are `dict`. REQ-CEO-001's fix (filter by `isinstance(v, dict)`, not a key-name blocklist) correctly excludes `_comment` before any `contract["kind"]` access, and PROP-CEO-001's fixture description now matches the real 8-key file. |
| **B2** (dead code after `exit "$RC"`) | **RESOLVED** | Re-read `founder-loop.sh` in full: still exactly 73 lines, `exit "$RC"` is still the literal last line, and it is the only `exit` statement in the file (`grep -n exit` returns only line 73 plus two unrelated `awk "BEGIN{exit ...}"` substring matches inside `STATUS=` string literals — not control-flow exits). REQ-CEO-070 now explicitly states the CEO pass call goes "before `exit \"$RC\"` (currently line 73)" and clarifies "末尾" means before the script's control-flow exit, not the last byte of the file. PROP-CEO-022 adds a genuine RC≠0 reachability test via an existing test seam, plus a check that CEO pass doesn't mutate the final exit code. This closes the gap the iteration-1 Tier2 check (diff-only) missed. |
| **B3** (rollback restores stale/already-bad state) | **PARTIALLY RESOLVED — see B4/B5 below** | REQ-CEO-052's streak-freeze idea (only snapshot when `consecutive_miss_count==0 and cooldown==0`) correctly fixes the *original* 2-week trace from the iteration-1 verdict: `ceo-rollback.json` is no longer overwritten by `A_bad1` before the 2nd miss fires, so `should_rollback` now restores `A_good`, not `A_bad1`. This core mechanism is sound. **However**, the *newly added* cooldown state machine (REQ-CEO-054/055/056/057), which iteration-1 explicitly asked for ("(c) 明示的に定義する`consecutive_miss_count`のリセットと再武装"), introduces two new self-contained contradictions — see **B4** and **B5** below. The original livelock scenario is fixed; a new one is opened by the fix itself. |
| **M1** (currency-mixed `company_score`) | **RESOLVED for `company_score` itself, but see M3/M4** | `convert_to_usd`/`company_score` (REQ-CEO-050, PROP-CEO-013) correctly convert-then-sum. Math re-verified: `convert_to_usd(150,"jpy",{"jpy_usd_rate":150.0})=1.0`; `company_score([{5.0,"usd"},{1500,"jpy"}], rate=150.0) = 5.0 + 10.0 = 15.0` — correct. **But** see M3 (currency-tag source unspecified) and M4 (the same conflation bug M1 fixed here is left un-fixed at a second call site, REQ-CEO-030(b)). |
| **M2** (`BudgetPacer` cited but unused) | **RESOLVED** | Re-cloned/re-read `Mahoraga/backend/orchestrator/routing/budget_pacer.py`: `BudgetPacer.update(task_cost)` (dual-ascent on `lambda_`), `.filter_agents()`, `.save()`/`.load()` (atomic tmp+`os.replace`) all exist exactly as REQ-CEO-014 describes. REQ-CEO-014 now wires `weekly_spend_by_loop()`'s company-wide total into `BudgetPacer.update()`, and the resulting `lambda_` flows into REQ-CEO-010's `compute_reward`. PROP-CEO-002's math re-verified: `lambda_=0.5, spend=2.0, earn=10.0` → `base=5.0` → `reward=5.0-0.5*2.0=4.0`. Correct, and the wiring is now real, not just cited. |
| **m1** (private `_week_start` import) | **RESOLVED** | Re-read `weekly_report.py:38`: `_week_start(d) -> d - datetime.timedelta(days=d.weekday())`. REQ-CEO-071 now re-derives this exact one-line formula locally inside `ceo/allocator.py` instead of importing the private symbol, and the verification method explicitly greps for the absence of a `weekly_report` import from `ceo/allocator.py`. Resolved. |
| **m2** (schema gate ≠ authorization) | **RESOLVED** | REQ-CEO-060 now has the explicit disclaimer sentence iteration-1 asked for. Resolved. |

---

## Part B — New findings introduced by this iteration's fixes

### B4 — `cooldown_weeks_remaining` set-then-decrement race can make the cooldown last zero weeks (REQ-CEO-053, REQ-CEO-055)

This is the exact class of bug iteration-1's B3 was: two REQs individually read as reasonable, but their
literal composition inside a single WEEKLY pass produces the opposite of the stated intent.

REQ-CEO-053: when `should_rollback` fires, THE SYSTEM SHALL, as part of that same rollback action,
"(b) `cooldown_weeks_remaining` を config の `ROLLBACK_COOLDOWN_WEEKS`（デフォルト1）に設定する" —
i.e., set it to `1`, mid-pass, at rollback time.

REQ-CEO-055: "各WEEKLY pass の最後に THE SYSTEM SHALL `decrement_cooldown(cooldown_weeks_remaining) ->
int`（新設・純粋: `max(0, n-1)`）を呼び `ceo-miss-streak.json` を更新する" — stated as an
**unconditional** action at the end of *every* WEEKLY pass, with no exception carved out for the pass in
which REQ-CEO-053 just armed cooldown.

Trace the pass in which rollback fires (call it week N+1, the pass that reads back week N's miss and
crosses the 2-miss threshold):
1. `should_rollback` fires; REQ-CEO-053 sets `cooldown_weeks_remaining = 1` mid-pass.
2. REQ-CEO-055's `WHILE cooldown_weeks_remaining > 0` guard (now true) correctly skips this pass's own
   REQ-CEO-040 write — good, this part works.
3. "At the end of the pass," REQ-CEO-055 calls `decrement_cooldown(cooldown_weeks_remaining)`. Read
   literally, this operates on the value **as it stands at end-of-pass**, which is the `1` that
   REQ-CEO-053 *just set two steps earlier in this same pass* — producing `max(0, 1-1) = 0`.

Result: `cooldown_weeks_remaining` is back to `0` before the pass even finishes, i.e. before the *next*
Monday's pass runs. The cooldown period specified as "デフォルト1 週間" lasts **zero** effective weeks —
the very next WEEKLY pass sees `cooldown_weeks_remaining == 0` and immediately resumes normal
`update_miss_count`/`should_snapshot`/allocation-writing, with no observation week in between.

This directly contradicts the spec's own stated purpose for this mechanism ("配分を変える前に最低1回の
PASSで復元後の状態を確認してから再武装する", REQ-CEO-055's own prose) and its own **proof obligation**:
PROP-CEO-021 explicitly asserts that after the rollback-firing pass, `ceo-miss-streak.json` shows
`cooldown_weeks_remaining=1` — a value that survives into the *next* week ("次週（cooldown中）は
`loop-registry.json`のallocationが変化しない"). A literal implementation of REQ-CEO-053 + REQ-CEO-055 as
currently worded (decrement unconditionally at the end of every pass, including the one that just armed
cooldown) produces `cooldown_weeks_remaining=0` at that checkpoint, **failing PROP-CEO-021 itself**. The
REQ text and the REQ's own proof obligation disagree about what the REQ requires.

**Required fix**: REQ-CEO-055 must explicitly state that `decrement_cooldown` is *not* applied on the
same pass in which REQ-CEO-053 just set `cooldown_weeks_remaining` (equivalently: the decrement operates
on the value the pass *entered* with, before any rollback-triggered reassignment this same pass; or:
`decrement_cooldown` is skipped entirely on any pass where `should_rollback` fired). Whichever rule is
chosen, it must be stated as its own sentence, not left to be inferred from step ordering.

### B5 — `update_miss_count`'s own text and its own proof obligation specify different return values for the same input (REQ-CEO-054 vs. PROP-CEO-014)

REQ-CEO-054's body text: "`cooldown_weeks_remaining > 0`なら`prev_count`を変更せず**0のまま据え置く**"
— read literally, this says the function's return value is forced to `0` whenever cooldown is active,
regardless of `prev_count`.

PROP-CEO-014 (verification-architecture.md), the proof obligation that is supposed to verify this exact
requirement, tests: "`update_miss_count`: ... `prev=1,beats=false,cooldown=1`（cooldown中）→**`1`のまま
変化しない**（凍結）" — i.e. for `prev_count=1` under cooldown, the *same* function must return `1`
(the input unchanged), not `0`.

These are two different specified outputs (`0` vs `1`) for the identical input triple
`(prev_count=1, beats_this_week=false, cooldown_weeks_remaining=1)`. An implementer who codes
REQ-CEO-054's prose literally ("常に0を返す during cooldown") will fail PROP-CEO-014's Tier-1 unit test
outright — not a subtle integration gap, a directly contradicting assertion in the same document.

(Note: under the *intended* end-to-end state machine, `prev_count` is always already `0` on entry to any
cooldown week, because REQ-CEO-053 resets it to `0` in the same atomic action that arms cooldown — so
"変更せず0のまま据え置く" and "prev_countのまま変化しない" would coincide in practice. But
`update_miss_count` is specified as a general **pure function** with its own signature and its own
proof obligation covering inputs outside that narrow on-path case, e.g. `prev=1`. As a pure function
spec, it must have one unambiguous rule for all inputs its signature admits, and right now it has two.)

**Required fix**: Pick one rule and correct the other artifact to match — either (a) REQ-CEO-054's prose
should read "`prev_count`を変更せず、そのまま返す（0を強制しない）" and drop "0のまま据え置く" (matching
PROP-CEO-014's test), or (b) PROP-CEO-014's fixture must use `prev=0` (the only value that can legitimately
occur during cooldown per REQ-CEO-053) and REQ-CEO-054's "0のまま据え置く" phrasing is kept as a
documented invariant, not a general-input contract.

---

## Part C — Other findings from the full 5-dimension pass

### M3 (new, Completeness) — REQ-CEO-002(c)'s `{amount, currency}` pair has no specified source for `currency`

REQ-CEO-002(c) and REQ-CEO-050 both consume "実収益（金額と通貨のペア `{amount, currency}`）" as an
input, and `build_loop_snapshot`'s Tier-1 signature takes `ledger_earn_entry` as a pre-formed pair. But
neither spec file ever defines *how* the `currency` half of that pair is derived from the real ledger
data. `score_from_rows` (the existing function the spec says to reuse) returns a single blended float
via an `earn_usdc → earn_jpy → commission_jpy` fallback **chain per row** — it does not return which
field it used, and there is no new function anywhere in either spec (no `loop_currency(loop) -> str`,
no per-row currency tag, nothing) that produces the `currency` label the rest of the pipeline assumes
exists. PROP-CEO-013's test only exercises `convert_to_usd`/`company_score` on fixture data that is
*already* labeled (`{amount:5.0,currency:"usd"}`) — it never tests the actual currency-determination
step, because that step doesn't exist in the spec to test. An implementer must invent this mechanism
unguided, which is exactly the kind of silently-filled gap this review dimension exists to catch.

**Required fix**: add a REQ (or extend REQ-CEO-002) that defines a concrete, deterministic mechanism for
tagging each loop's realized-earn amount with its currency — e.g. a static per-loop config
(`{"clip":"usd","gig":"jpy","affiliate":"jpy",...}`) checked against the design doc's loop table, or a
function that inspects which of `earn_usdc`/`earn_jpy`/`commission_jpy` was non-zero in the summed rows
— with its own Tier-1 test.

### M4 (new, Consistency, M1-derivative) — `capital_increase_within_realized_profit`'s `_usd`-named parameter is fed a non-USD value for JPY loops

REQ-CEO-030(b) defines `capital_increase_within_realized_profit(new_cap, old_cap,
realized_profit_usd) -> bool` as the machine gate on how much `capital_cap_usd` (an explicitly
USD-denominated field, per REQ-CEO-040's schema) can be increased in one pass. But REQ-CEO-002(c)
explicitly says the *raw, unconverted* per-loop currency value is what feeds "loop単体の判断" — and
names REQ-CEO-030(b) as the direct example: "company_score算出時のみREQ-CEO-050が別途USD換算する、
**REQ-CEO-030(b)等loop単体の判断にはこの生の通貨のままの値を使う**". Read together: for a JPY-reporting
loop (`gig`/`affiliate`, per the design doc's loop table cited in iteration-1's own M1 finding),
`capital_increase_within_realized_profit`'s third argument — named and typed `realized_profit_usd` — is
in fact the loop's raw JPY figure (e.g. `¥50,000`), never divided by `fx_config["jpy_usd_rate"]`. Compared
directly against a USD `capital_cap_usd` delta, this makes the guardrail roughly 150x too permissive for
those two loops (a JPY number numerically similar to a much smaller USD number passes as if it were
"$50,000 of realized profit" rather than the ~$333 it actually represents). This is the identical
currency-conflation defect M1 flagged, left un-fixed at a second call site that the M1 fix never touched —
the design doc's own guardrail language ("資本増額は on-chain 検証済み realized profit の範囲内") is
undermined for exactly the two loops for which currency correctness matters most.

**Required fix**: REQ-CEO-030(b) must call `convert_to_usd` on the loop's realized profit before passing
it to `capital_increase_within_realized_profit`, the same way REQ-CEO-050 now does for `company_score`.
REQ-CEO-002(c)'s carve-out sentence must be corrected — it should say the raw currency value is retained
in the snapshot dict for auditability, but any consumer whose parameter is `_usd`-typed (REQ-CEO-030(b)
included) must convert first.

### m3 (new, minor) — REQ-CEO-032's `consecutive_bad_weeks` input has no defined persistence location

`should_scale_down(weekly_score, beats_previous_week, consecutive_bad_weeks) -> str` takes
`consecutive_bad_weeks` as an input, but no REQ or state file (unlike `ceo-miss-streak.json` for the
company-wide counter) specifies where this **per-loop** streak is read from or written to. Likely a
sub-key inside `loop-registry.json`'s per-loop entry, but this should be named explicitly (one sentence)
rather than left implicit, given `merge_allocation`'s non-destructive-merge contract already has to know
about every key it must preserve.

### m4 (new, minor) — `ceo-rollback.json`'s exact shape is defined only by a PROP fixture, not by REQ-CEO-052's prose

REQ-CEO-052 says "現在の allocation テーブル全体を...スナップショットする," which could plausibly mean
either "each loop's bare allocation dict" or "each loop's full registry entry including the `"allocation"`
wrapper key." PROP-CEO-014b's fixture (`restore_from_rollback(..., {"clip":{"allocation":{"x":9}}})`)
resolves this concretely (the wrapper is present), but REQ-CEO-052's own text should say so directly
rather than leaving the shape to be reverse-engineered from one test fixture.

---

## Reality-grounding summary (re-verified against live sources, not iteration-1's report)

Directly re-read (not trusted from iteration-1's write-up) and confirmed to match every claim the spec
makes about them:
- `cadence-contracts.json` — loaded with `json.load` in this session: 8 keys, `_comment` is `str`, other
  7 are `dict`. Matches REQ-CEO-001/PROP-CEO-001 exactly.
- `founder-loop.sh` — 73 lines, `exit "$RC"` is the sole control-flow exit and the literal last line.
  Matches REQ-CEO-070/PROP-CEO-022.
- `weekly_report.py::_week_start`, `_rows_in_week`, `_score_for_rows` — read directly; `_week_start`'s
  formula (`d - timedelta(days=d.weekday())`) matches REQ-CEO-071's re-derivation exactly.
- `self-improve/lib/weekly_compare.py::beats_previous_week` — strict `>`, matches.
- `self-improve/lib/ledger_metrics.py::score_from_rows` — fallback chain `earn_usdc → earn_jpy →
  commission_jpy`, matches (and is the root of the M3/M4 gap above — it doesn't expose which field won).
- `loop-scale/guardrails.py` — all four functions read in full, signatures and logic match REQ-CEO-031/032
  exactly.
- `report-args.mjs::founderReportArgs`, `loop-report.sh::lr_valid_evidence` — read in full, match.
- `clip-promote-status.mjs::clipPromoteStatus(payoutRows, todayJstDate)` — read in full, matches REQ-CEO-004.
- Mahoraga (already-cloned copy re-read fresh this session): `LinUCBRouter` (`_init_agent` cold-start —
  identity matrix `A`, prior-seeded `b`; `select_agent`'s UCB formula; `save_state`/`load_state` via
  tmp-write + `os.replace`), `ThompsonSamplingRouter` (`alpha`/`beta` update rule, `save_state`/
  `load_state`), `BudgetPacer` (`update` dual-ascent on `lambda_`, `filter_agents` hard-limit with
  cheapest-fallback, `save`/`load` atomic) — all match the spec's descriptions exactly, including the
  M2 fix's claim that `lambda_` is now actually wired to `compute_reward`.
- agent-os `budgets.py` — `budget_for_agent` per_agent→default resolution, `filter_budget_compliant_agents`
  fail-open on missing `budgets` section, `check_budget_alerts` dedup via `(month,agent,threshold)` key —
  all match REQ-CEO-020〜025 exactly.

No hallucinated symbols found in this pass either. The Reality-grounding PASS verdict is unchanged from
iteration 1; every new B4/B5/M3/M4 finding above is a spec-internal logical/consistency defect, not a
reference to something that doesn't exist.

---

## 収束傾向 (convergence trend)

Iteration 1 → iteration 2: 3 blocking → 0 of those 3 remain (all genuinely resolved, verified against
live files, not just re-read prose). 2 major → 0 of those 2 remain (also genuinely resolved). 2 minor →
0 remain. That is real progress and the fixes are not superficial — B1/B2 in particular are now airtight
(exact line-number citations, exact fixture values matching the real file).

However, total finding count did not shrink: 2 new blocking (B4, B5) + 2 new major (M3, M4) + 2 new minor
(m3, m4) replaced the resolved set, and — notably — **all of the new blocking/major findings are
concentrated inside the two most complex additions this iteration made** (the cooldown state machine
added to close B3, and the currency-conversion machinery added to close M1). This is a legitimate
"frontier keeps moving" pattern rather than random churn: the parts of the spec that were fully resolved
in iteration 1 (REQ-CEO-001/070, the roster derivation, the exit-code ordering) show no regressions
under this pass's re-verification. The unresolved complexity has narrowed to two specific, well-bounded
areas (cooldown-week bookkeeping; USD-conversion coverage at all `_usd`-typed call sites), which is a
tractable scope for iteration 3 — but the spec is not yet convergent and must not proceed to Phase 2
(RED) as-is: B4 and B5 both directly threaten the correctness of the safety mechanism (rollback +
cooldown) that this entire feature exists to guarantee, and B4/B5's own proof obligations (PROP-CEO-021,
PROP-CEO-014) would not pass against the REQ text as currently written.

## What must happen before re-review

Fix B4 and B5 in the spec text (not deferred to implementation judgment — both are literal
self-contradictions or unstated-ordering bugs that a correct implementation could still satisfy the
individual REQ sentences while failing the feature's own proof obligations). Address M3 and M4 with an
explicit decision (add the missing currency-tag mechanism; wire `convert_to_usd` into REQ-CEO-030(b)).
m3/m4 may be deferred to implementation-time judgment calls but should get at least one sentence each in
the spec, per the same standard iteration 1 applied to m1/m2.
