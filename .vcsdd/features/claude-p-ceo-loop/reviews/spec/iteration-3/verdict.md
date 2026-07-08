# Spec Review Verdict — claude-p-ceo-loop (Phase 1c, iteration 3)

Reviewer: fresh-context adversary (no Builder context, no iteration-1/2 adversary context — zero memory
of authoring either). All claims below verified by directly reading the artifacts on disk: the two spec
files as they currently stand, the iteration-2 verdict (`reviews/spec/iteration-2/verdict.md`), and
fresh re-reads of the cited ground-truth files (`~/anicca/skills/self/cadence-contracts.json`,
`~/anicca/skills/self/founder-loop/founder-loop.sh`).

## Overall verdict: **FAIL** (1 blocking finding — new, not carried over)

## Per-dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Completeness | **FAIL** (1 major gap) |
| 2 | Testability | **FAIL** |
| 3 | Consistency | **FAIL** |
| 4 | Reality-grounding | PASS (re-verified, unchanged from iteration 2) |
| 5 | 安全境界 (safety boundary) | **FAIL** |

---

## Part A — Disposition of iteration-2's B4/B5/M3/M4 findings

Each checked individually against the current spec text, not just trusted from iteration-2's write-up.

| Finding | Status | Evidence |
|---|---|---|
| **B4** (set-then-decrement race on `cooldown_weeks_remaining`) | **RESOLVED (for the value itself)** | New REQ-CEO-058 step ⑥ introduces `next_cooldown_weeks_remaining(cooldown_weeks_remaining_in, rollback_fired_this_pass, rollback_cooldown_weeks=1)` as the **single** function that decides the next value: if `rollback_fired_this_pass` it returns `rollback_cooldown_weeks` (arm, no decrement this pass); else if `cooldown_weeks_remaining_in>0` it decrements; else `0`. Arming and decrementing are now mutually exclusive branches of one pure function, not two independently-worded REQs composed in sequence — this structurally eliminates the literal race iteration-2 found. PROP-CEO-021 explicitly asserts, immediately after the rollback-firing pass, `cooldown_weeks_remaining=1` (not 0) in `ceo-miss-streak.json` — the exact B4 counter-scenario is now a named Tier-3 assertion. Traced by hand for week N (rollback fires) → week N+1 (cooldown, decrement to 0) → week N+2 (normal resumption): the arithmetic is self-consistent and matches REQ-CEO-058's own worked example. **However, this same fix opens a new defect — see B6 below** — the cooldown *number* is fixed, but the *allocation write* that happens in the same pass is not gated correctly. |
| **B5** (`update_miss_count` prose vs. proof-obligation contradiction) | **RESOLVED** | REQ-CEO-054 now reads "`cooldown_weeks_remaining > 0`なら`prev_count`をそのまま変更せず返す（cooldown中は凍結——0への強制リセットではない）" and PROP-CEO-014 now tests **both** `prev=0,cooldown=1→0`(unchanged) **and** `prev=1,cooldown=1→1`(unchanged) — the "0 vs 1" contradiction iteration-2 found is gone; both artifacts now assert the single "return input unchanged" rule for both example inputs. REQ-CEO-056's justification was also correctly re-grounded on `should_rollback`'s own `cooldown_weeks_remaining==0` condition rather than on `update_miss_count`'s cooldown-time output, exactly as iteration-2 required. |
| **M3** (currency-tag source unspecified) | **RESOLVED** | REQ-CEO-002(c) now defines `sum_earn_by_currency(rows) -> list[{amount,currency}]` as a fully deterministic function that **always** returns exactly 2 entries — `earn_usdc` totals under `"usd"`, `earn_jpy+commission_jpy` totals under `"jpy"` — with no field-precedence branch to reverse-engineer. PROP-CEO-013 tests this exact mapping directly. Currency provenance is now a named, testable, single-purpose function; the M3 gap (no mechanism existed to determine `currency`) is closed. |
| **M4** (JPY loops feeding raw value into a `_usd`-typed parameter) | **RESOLVED** | REQ-CEO-050 explicitly designates `realized_profit_usd(entries, fx_config)` as "loopの実収益をUSDへ変換する唯一の共有経路" and REQ-CEO-030(b) now states its third argument "には...`realized_profit_usd(entries, fx_config)`に通した後のUSD換算済みの値を必ず渡す". PROP-CEO-007 directly tests this with a JPY fixture (`9000 jpy → 60.0 usd` at `rate=150`) and explicitly asserts the raw `9000` never reaches the gate function. Both call sites (`company_score` and `capital_increase_within_realized_profit`) now route through the one shared conversion function — the "fixed once, broke again at a second call site" pattern from M1/M4 cannot recur structurally, since there is only one conversion entry point left. |

All four of iteration-2's findings are genuinely resolved as claimed, verified against the live spec text
and disk ground truth, not just re-read prose.

---

## Part B — REQ-CEO-058's fixed ①〜⑩ steps, traced for new ordering defects

### B6 (new, blocking) — Step ⑦'s formal write condition does not exclude the rollback-firing pass, contradicting REQ-CEO-058's own worked example and PROP-CEO-021

Step ⑦, quoted verbatim: "`cooldown_weeks_remaining_in == 0`なら REQ-CEO-040 の allocation テーブル
書込を実行（REQ-CEO-052の`should_snapshot`判定→必要ならスナップショット→書込）、そうでなければ
スキップ（REQ-CEO-055）。" The condition is a single boolean test on `cooldown_weeks_remaining_in`. It
has no clause referencing `rollback_fired_this_pass`.

Trace the rollback-firing pass (week N) against this literal condition:
1. `should_rollback` requires `cooldown_weeks_remaining_in == 0` to be true at all (REQ-CEO-053's own
   definition: `cooldown_weeks_remaining==0 and consecutive_miss_count>=threshold`). So on any pass where
   rollback fires, `cooldown_weeks_remaining_in` is necessarily `0`.
2. Step ⑤ executes the rollback: `restore_from_rollback` produces the registry with the loop's
   `"allocation"` reset to the known-good `ceo-rollback.json` snapshot (`A_good`).
3. Step ⑦'s condition (`cooldown_weeks_remaining_in == 0`) is **true** on this exact pass (per point 1),
   so per the literal text, REQ-CEO-040's write executes: `should_snapshot` check, then `merge_allocation`
   with **this week's agent-decided allocation** (computed from this week's — still-bad — data, entirely
   independent of the rollback), then an atomic write to `loop-registry.json`.
4. That write happens in the same pass, after the rollback restore, and nothing in step ⑦'s formal text
   skips it. The result: whatever `A_new` the agent's normal double-down/scale-down logic computes this
   pass overwrites the just-restored `A_good` before the pass ends.

REQ-CEO-058's own worked example, appended right after the ten steps, asserts the opposite: "⑦は
`cooldown_weeks_remaining_in==0`だったので通常ならallocation書込するはずだが、rollbackが⑤で既に
allocationを復元しているため**このpassの通常書込は行わない**（rollback自体が書込を兼ねる）". This
sentence is narrative prose, not a formal amendment to step ⑦'s stated condition — it asserts a
`rollback_fired_this_pass` exclusion that the actual IF-THEN in step ⑦ does not contain. An implementer
who codes step ⑦ exactly as written (a single condition on `cooldown_weeks_remaining_in`) satisfies the
REQ's literal text while producing behavior the REQ's own example claims is impossible.

This is the identical failure pattern iteration-2 flagged as B4/B5: a narrative walkthrough at the end of
a REQ describes behavior that the REQ's own formal steps do not actually produce. It is more severe here
because it directly threatens the mechanism the whole B3→B4→B5 fix chain exists to protect: **PROP-CEO-021**
asserts the rollback pass ends with `loop-registry.json`'s allocation equal to `A_good`, but as formally
specified, step ⑦ can (and, for any agent decision that differs from `A_good`, will) overwrite that
restored state with a new, unrelated allocation before the pass completes. PROP-CEO-021's verification
method only checks the *final* state matches `A_good` in a curated fixture — it does not test whether a
compliant implementation that also runs step ⑦'s write (as literally required) still satisfies that
final-state assertion in the general case where the agent's this-week decision differs from `A_good`,
which is the realistic case.

**Required fix**: Step ⑦'s formal condition must be changed to `cooldown_weeks_remaining_in == 0 and not
rollback_fired_this_pass` (or equivalent), with an explicit accompanying sentence that on the pass where
rollback fires, REQ-CEO-040's normal write is structurally skipped because the rollback restore already
constitutes this pass's allocation-table write. This must be stated as part of step ⑦'s own conditional,
not left as an unenforced claim in the trailing narrative example. PROP-CEO-021's verification method
should also explicitly test the case where the agent's hypothetical this-week decision differs materially
from `A_good`, to make sure a compliant implementation cannot silently reintroduce this overwrite.

### M5 (new, major, Completeness) — REQ-CEO-058 claims to be the sole ordering authority but omits where bandit/budget-pacer/budget-gate/guardrail/agent-decision machinery fits into the ①〜⑩ sequence

REQ-CEO-058's own framing: "THE SYSTEM SHALL 各 WEEKLY pass を以下の**固定順序**で実行する（EARSの他
REQ群はこの順序内の1ステップとして解釈する。順序自体をこのREQ1箇所に集約し、他REQの記述から実行順序
を逆算させない...)" — an explicit claim that every other REQ's execution position is pinned by this one
REQ, so a reader never has to infer ordering elsewhere.

The ten listed steps are: ① read miss-streak state, ② roster snapshot, ③ company_score/beats, ④
update_miss_count, ⑤ should_rollback + rollback exec, ⑥ next_cooldown_weeks_remaining, ⑦ allocation
write/skip, ⑧ ceo-miss-streak.json write, ⑨ ceo-verification.jsonl append, ⑩ mail report. Nowhere in
this list does bandit `update()`/`compute_reward()` (REQ-CEO-010/011), `BudgetPacer.update()`
(REQ-CEO-014), `filter_budget_compliant_loops` (REQ-CEO-022), the guardrail triad
(`scale_eligible`/`cooldown_ok`/`fleet_at_capacity`, REQ-CEO-031), the agent's actual double-down /
scale-down decision (REQ-CEO-030/032/034), or escalation-schema logging (REQ-CEO-060) appear. All of
these are presumably meant to be folded inside the single phrase "REQ-CEO-040 の allocation テーブル
書込を実行" in step ⑦, but that phrase names only the final `merge_allocation`+write call, not the
bandit-scoring → budget-gating → guardrail-checking → agent-decision pipeline that must run first to
produce the allocation dict `merge_allocation` consumes. Whether `BudgetPacer.update()` runs before or
after step ③'s `company_score`, whether budget-gate filtering (REQ-CEO-022) happens before or after
bandit scoring, and whether any of this runs on the pass where rollback fires (interacting with the B6
gap above) are all left to be inferred — which is precisely what this REQ says it exists to prevent.

**Required fix**: Extend the ①〜⑩ list (or explicitly append sub-steps inside ⑦) naming where
REQ-CEO-010/011/014/020-025/030-034/060 execute relative to the ten listed steps, at minimum stating
whether they run before or after the rollback check (⑤) and whether they run at all on a rollback-firing
or cooldown-skip pass.

### m5 (new, minor) — `ceo-verification.jsonl` receives two differently-shaped rows per rollback pass

REQ-CEO-053(b) requires appending `{action:"rollback", rolled_back_to_week}` to `ceo-verification.jsonl`
"同時に" with the rollback execution (step ⑤). REQ-CEO-058 step ⑨ separately requires appending the full
REQ-CEO-051 verification row (`{ts, week_start, ..., rollback_fired}`) at the end of the same pass. These
are two distinct schemas targeting the same file within a single WEEKLY pass; `rolled_back_to_week` is
not a field of REQ-CEO-051's schema, so it is unclear whether the rollback pass produces one row or two,
and (if two) which shape downstream readers (e.g. REQ-CEO-081's evidence pointer, which cites "該当行の
`week_start`値" — a REQ-CEO-051-shaped field) should treat as canonical.

**Required fix**: One sentence stating whether REQ-CEO-053(b)'s append is (a) folded into REQ-CEO-051's
`rollback_fired`/`allocation_change_ref` fields and not a separate write, or (b) a genuinely distinct
second row, in which case `rolled_back_to_week` should be added to REQ-CEO-051's schema or dropped.

---

## Reality-grounding summary (re-verified fresh against live sources)

- `~/anicca/skills/self/cadence-contracts.json` — re-loaded with `json.load` this session: 8 keys
  (`_comment`, `clip`, `affiliate`, `video`, `gig`, `bounty`, `founder-loop`, `pm-earner`), `_comment` is
  `str`, the other 7 are `dict`. Unchanged from iteration 2, matches REQ-CEO-001/PROP-CEO-001.
- `~/anicca/skills/self/founder-loop/founder-loop.sh` — 73 lines, `exit "$RC"` is the sole control-flow
  exit and the literal last line (the one other `exit` match is an unrelated `awk "BEGIN{exit ...}"`
  substring inside a `STATUS=` string literal). Unchanged from iteration 2, matches REQ-CEO-070/PROP-CEO-022.

No new external symbols (Mahoraga/agent-os/cadence.py/weekly_report.py/guardrails.py) were introduced or
modified by this iteration's spec changes — the cooldown state machine and currency-conversion machinery
are entirely new pure functions internal to this feature (`next_cooldown_weeks_remaining`,
`sum_earn_by_currency`, `realized_profit_usd`), not references to pre-existing code, so there is nothing
further to re-verify against disk beyond what iteration 2 already confirmed. Reality-grounding remains
PASS.

---

## 収束傾向 (convergence trend)

Iteration 2 → iteration 3: all 4 of iteration-2's findings (B4, B5, M3, M4) are genuinely resolved —
verified against the current spec text line-by-line, not superficially re-read. That is real, substantive
progress; the currency-conversion machinery (M3/M4) is now fully closed with no known remaining gap.

However, the cooldown-and-rollback state machine — the single most complex and most safety-critical part
of this spec — has again produced a new blocking defect (B6) as a side effect of closing the previous one
(B4). This is the third consecutive iteration in which this exact subsystem (rollback timing / cooldown
bookkeeping) is the source of the blocking finding: iteration 1 found B3 (stale-state rollback), iteration
2's fix for B3 produced B4 (cooldown race), and iteration 2's fix for B4 has now produced B6 (allocation
write not excluded on the rollback pass). Each fix has correctly closed the specific bug it targeted while
introducing a new bug in the same narrow area, via the same root cause: a trailing narrative "worked
example" asserts behavior that the REQ's own formal, literal conditional does not actually encode. This is
a repeating pattern, not random churn, and the fix technique needs to change: rather than adding another
narrative walkthrough after the ten steps, step ⑦'s **formal** conditional itself must be extended, and
PROP-CEO-021's test must exercise the case where the agent's this-week decision differs from `A_good`
(not just assert the final state coincidentally matches the fixture's `A_good`).

The newly-found M5 (bandit/budget/guardrail/agent-decision execution position undefined within the "固定
順序") is a completeness gap in the same REQ, not a new area of complexity — closing it alongside B6 is
tractable in one more pass, since it requires stating, not designing, the missing ordering.

## What must happen before re-review

1. Fix B6: amend REQ-CEO-058 step ⑦'s formal condition to `cooldown_weeks_remaining_in == 0 and not
   rollback_fired_this_pass`, and correspondingly strengthen PROP-CEO-021's verification method to test a
   this-week agent decision that differs from `A_good`, not just check the final state matches the
   fixture.
2. Address M5: state explicitly where REQ-CEO-010/011/014/020-025/030-034/060 execute relative to
   REQ-CEO-058's ten steps (at minimum: before/after step ⑤, and whether they run on rollback-firing or
   cooldown-skip passes).
3. m5 may be deferred to implementation-time judgment but should get one sentence, per the standard
   applied to m1-m4 in prior iterations.
