# Spec Review Verdict — claude-p-ceo-loop (Phase 1c, iteration 4)

Reviewer: fresh-context adversary (no Builder context, no iteration-1/2/3 adversary context — zero memory
of authoring any of them). All claims below verified by directly reading the artifacts on disk: the two
spec files as they currently stand, the iteration-3 verdict
(`reviews/spec/iteration-3/verdict.md`), and fresh re-reads of the cited ground-truth files
(`~/anicca/skills/self/cadence-contracts.json`, `~/anicca/skills/self/founder-loop/founder-loop.sh`).

## Overall verdict: **FAIL** (2 blocking-severity findings — both new, not carried over; iteration-3's B6
is genuinely resolved)

## Per-dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Completeness | **FAIL** |
| 2 | Testability | **FAIL** |
| 3 | Consistency | **FAIL** |
| 4 | Reality-grounding | PASS (re-verified fresh, unchanged from iteration 3) |
| 5 | 安全境界 (safety boundary) | **FAIL** |

---

## Part A — Disposition of iteration-3's B6/M5/m5 findings

Each checked individually against the current spec text, not trusted from the Builder's changelog tags.

| Finding | Status | Evidence |
|---|---|---|
| **B6** (step ⑦'s allocation-write condition didn't exclude the rollback-firing pass) | **RESOLVED** | Step ⑧ (renumbered from ⑦) now states the formal condition as `cooldown_weeks_remaining_in == 0 and not rollback_fired_this_pass` as **the conjunction itself**, with explicit text: "この論理積そのものが正式条件——`cooldown_weeks_remaining_in == 0`だけでは不十分" (behavioral-spec.md line ~414-423). PROP-CEO-021 was correspondingly strengthened: it now constructs a fixture where "この週、もし⑧が実行されていたらagentは`A_good`とは意図的に異なる`A_bad3`...を書くはずだった" and requires the verification method to confirm, via **execution log absence**, that "⑧-a〜⑧-fのロジック...が呼び出しごと実行された形跡が一切ない" — not merely that the final state coincidentally equals `A_good`. This is exactly what iteration-3's required fix demanded (a formal conjunctive condition, plus a test that distinguishes "correctly skipped" from "executed then coincidentally matched"). Traced by hand for the rollback-firing pass: ⑥ sets `rollback_fired_this_pass=true` → ⑧'s condition evaluates `True and not True = False` → ⑧ (including ⑧-f's `merge_allocation` write) is skipped entirely → `loop-registry.json` retains the ⑥-restored `A_good`. **Genuinely resolved.** |
| **M5** (bandit/budget/guardrail/agent-decision/log execution position undefined within the ordering REQ) | **PARTIALLY RESOLVED — not closed** | Step ③ (new) explicitly places REQ-CEO-010/011/014 as unconditional, every-pass execution. ⑧-a places REQ-CEO-022. ⑧-b places REQ-CEO-011 (display). ⑧-c places REQ-CEO-030/031/032. ⑧-d places REQ-CEO-034. ⑧-e places REQ-CEO-060. This is real progress. **However**, iteration-3's own required-fix text explicitly demanded placement for "REQ-CEO-010/011/014/**020-025**/030-034/060" (iteration-3 verdict, line 111-113) — the full 020–025 range. The current fix places only **022** from that range. **REQ-CEO-023** (fail-open logging when budget config/loop entry is missing), **REQ-CEO-024** (soft-warn/hard-stop mail alert, dedup-gated), and **REQ-CEO-025** (`budget_snapshot_for_registry()` write of the `"budget"` subkey into `loop-registry.json`) are **not mentioned anywhere in the ①–⑪ / ⑧-a–⑧-f sequence**. Nothing in step ③, ⑧-a, or any other step states when these three fire, or whether they fire on a rollback/cooldown-skip pass at all. This is confirmed independently by `verification-architecture.md`'s own PROP-CEO-023 (the exhaustiveness meta-test built specifically to verify this M5 fix): its enumeration list is "010/011/014/022/030/031/032/034/060/058" — it **also** omits 023/024/025, meaning the gap exists in both the ordering text and the test meant to catch ordering gaps. See Part B below for why this is not a benign omission (it is entangled with a real double-write risk on `loop-registry.json`). REQ-CEO-058's own top-line claim — "順序自体をこのREQ1箇所に集約し、他REQの記述から実行順序を逆算させない" — is therefore currently **false** for REQ-CEO-023/024/025 (their position must still be inferred/guessed). |
| **m5** (`ceo-verification.jsonl` two-schema-rows ambiguity) | **RESOLVED** | REQ-CEO-051 now carries `rolled_back_to_week` as a native field of its 10-field schema and states explicitly: "このREQ-CEO-051の1行が`ceo-verification.jsonl`への唯一のcanonical書込である — REQ-CEO-053(b)が独立に別行を追記することはない". REQ-CEO-053 correspondingly now says its own rollback execution "`ceo-verification.jsonl`への追記は、このREQでは行わない". PROP-CEO-013/051's verification method explicitly asserts "正確に1行だけ追記され...別schemaの行が追加で書かれていないこと". **Genuinely resolved.** |

Verdict on Part A: B6 and m5 are genuinely, structurally resolved — the fix technique (formal conjunctive
condition instead of trailing narrative; single canonical schema instead of two write sites) is sound and
matches what iteration-3 demanded. **M5 is not fully resolved** — the fix covers roughly half of the REQ
range iteration-3 named (010/011/014/022/030-034/060) but silently drops 023/024/025, and this omission
propagated into the newly-added exhaustiveness test (PROP-CEO-023) as well, so there is currently no
verification method that would catch an implementer leaving 023/024/025 unplaced.

---

## Part B — New ①〜⑪ + ⑧-a〜⑧-f steps, traced for new ordering/completeness/consistency defects

### B7 (new, blocking, Completeness+Consistency) — REQ-CEO-023/024/025 have no stated position in the "固定順序", and REQ-CEO-025's write target creates an unresolved double-write risk against REQ-CEO-040's `merge_allocation`

Traced concretely: REQ-CEO-025 requires `budget_snapshot_for_registry()`'s output to be written as the
`"budget"` subkey of the relevant loop's entry in `loop-registry.json` — explicitly declared as "REQ-CEO-040
の non-destructive merge の対象の一部" (behavioral-spec.md line ~219-220). But REQ-CEO-040's own
implementing function, `merge_allocation(existing_registry, loop, allocation) -> dict`, is defined (and
independently confirmed by `verification-architecture.md`'s PROP-CEO-010) to replace **only** the
`"allocation"` subkey while preserving other keys untouched — it has no parameter or mechanism for also
setting `"budget"`. Step ⑧-f's own text names only one write action: "`merge_allocation`で
`loop-registry.json`へ実書込（REQ-CEO-040）" — no mention of a second write for the `"budget"` subkey, no
mention of a `merge_budget()` counterpart function, and no statement that the two writes are combined into
one atomic tmp+rename operation. A compliant implementer who follows the spec's literal text has two
options, neither of which is sanctioned by name: (a) perform a **second**, separate
tmp-write+atomic-rename to `loop-registry.json` within the same pass for the `"budget"` subkey — a literal
double-write to the same file in the same pass, exactly the failure category flagged for scrutiny — or (b)
silently invent an ad-hoc merged-write mechanism the spec never names. Either way, this is unspecified
behavior in a state-file-writing path, the same severity class as B3/B4/B6's prior findings in this exact
subsystem (loop-registry.json / rollback bookkeeping).

REQ-CEO-023 (fail-open logging) and REQ-CEO-024 (mail alert dedup) have the same defect: `filter_budget_
compliant_loops` (REQ-CEO-022, the only budget-related call step ⑧-a names) is independently classified in
`verification-architecture.md` as **新設・純粋** (a pure function, no I/O) — it structurally cannot also
perform 023's log-dedup I/O or 024's `loop-report.sh` mail call. These two REQs describe real, distinct
side-effecting actions (a log write, a mail send) that must happen *somewhere* in the weekly pass, but the
"固定順序" REQ that claims to be the sole ordering authority for "EARSの他REQ群" does not place them.

**Required fix**: Add explicit sub-steps for REQ-CEO-023/024/025 to the ①–⑪/⑧-a–⑧-f sequence (most
naturally alongside ⑧-a, since all three are budget-related and gated by the same `cooldown_weeks_
remaining_in == 0 and not rollback_fired_this_pass` condition per the surrounding text's intent). For
REQ-CEO-025 specifically, state explicitly whether its `"budget"` subkey write is (a) folded into a single
combined write alongside REQ-CEO-040's `"allocation"` subkey write via one unified merge function/one
atomic tmp+rename, or (b) a second, independently-atomic write to the same file — and if (b), state the
ordering relative to REQ-CEO-040's write and confirm no torn-read window exists for readers of `loop-
registry.json` between the two writes. Extend PROP-CEO-023's enumeration to include 023/024/025 so the
exhaustiveness test actually covers what it claims to.

### B8 (new, blocking, Consistency) — step ③'s `compute_reward(realized_earn_usdc, ...)` input is not required to route through `realized_profit_usd()`, reopening the M1/M4 currency-mixing bug at a third call site newly introduced by this iteration's own fix

REQ-CEO-002(c) states its currency-routing mandate in absolute terms: "**この`ledger_earn_entries`（list）は
REQ-CEO-050 の`realized_profit_usd()`に渡すまで一切USD換算しない。company_score算出（REQ-CEO-050）だけで
なく、REQ-CEO-030(b)を含む loop 単体の判断も必ず`realized_profit_usd()`経由でUSD換算してから使う——生の
通貨のまま`_usd`型パラメータへ渡すことは一切ない**". Note precisely what this sentence enumerates as
required consumers: company_score (050) and "REQ-CEO-030(b)を含む loop単体の判断". REQ-CEO-050 echoes this
with "この`realized_profit_usd()`が、loopの実収益をUSDへ変換する唯一の共有経路である — REQ-CEO-030(b)も
この同じ関数を呼ぶ" — again naming only REQ-CEO-030(b) as the second consumer.

REQ-CEO-010 (`compute_reward(realized_earn_usdc, weekly_spend_usd, lambda_) -> float`) is **also** a
"loop単体の判断" that consumes a `_usdc`-typed parameter representing realized earnings — the exact
category REQ-CEO-002(c) says must never receive raw, unconverted currency. But REQ-CEO-010's own text never
states that `realized_earn_usdc` must be obtained via `realized_profit_usd(ledger_earn_entries, fx_config)`,
and neither REQ-CEO-002(c)'s nor REQ-CEO-050's "must route through" enumeration names REQ-CEO-010. This is
not a hypothetical gap: this feature's roster explicitly includes JPY-denominated loops (gig, affiliate —
REQ-CEO-030(b)'s own worked example uses gig/affiliate as the JPY case, with `jpy_usd_rate≈150`). An
implementer filling in step ③'s unspecified wiring could plausibly pass either (a) the loop's raw
`ledger_earn_entries` sum in native currency, or (b) `weekly_row`'s `combined_score` (REQ-CEO-002(b)) —
itself explicitly documented elsewhere in this same spec as a currency-blind blended value produced by
`score_from_rows`'s fallback chain, i.e., exactly the mechanism whose currency-blindness caused the
original M1 finding — into a `_usdc`-named parameter that directly drives the bandit's live learning
signal (`update(context, loop, reward)`), which in turn drives which loops get UCB-ranked for double-down
consideration in ⑧-b/⑧-c. Either substitution would make gig/affiliate loops' reward roughly 150x too
large or too small relative to USD-native loops (clip/video/pm-earner), silently biasing the entire
resource-allocation engine.

This is additionally an ordering problem, not just a missing sentence: step ③ (new this iteration) runs
**before** step ④, and step ④ is where `company_score`'s per-loop `realized_profit_usd()` breakdown is
computed. So even a well-intentioned implementer who correctly infers "of course this should go through
realized_profit_usd()" has no guidance on whether step ③ must independently call `realized_profit_usd()`
per loop a second time (redundant with step ④'s later per-loop computation, but harmless since it's pure),
or whether the step order should change. Nothing in REQ-CEO-058 addresses this.

This directly falsifies REQ-CEO-050's own claim that `realized_profit_usd()` is "唯一の共有経路" (the sole
shared path) — a third real call site (bandit reward) exists that is not required to use it. This is the
identical failure pattern that produced M4 (a fix applied at one call site, not propagated to a second),
now recurring at a third call site that this very iteration's own new step ③ introduces.

**Required fix**: Add one sentence to REQ-CEO-010 (or step ③) stating: "`realized_earn_usdc`には、当該loop
の`ledger_earn_entries`（REQ-CEO-002(c)）を`realized_profit_usd(entries, fx_config)`（REQ-CEO-050）に通し
た後のUSD換算済みの値を必ず渡す" — mirroring REQ-CEO-030(b)'s existing language verbatim. Add REQ-CEO-010
to REQ-CEO-002(c)'s and REQ-CEO-050's "must route through" enumeration lists (which currently name only
REQ-CEO-030(b)). Add a PROP-CEO-002 or PROP-CEO-013 test case mirroring PROP-CEO-007's M4 反証 pattern: a
JPY-denominated loop fixture where the raw JPY sum is verified to **not** reach `compute_reward`'s first
argument directly.

### Steps traced, no defect found

①（START値の固定読み取り）, ②（snapshot組立て）, ④〜⑦（company_score→miss-count→rollback判定→
cooldown次値決定）, ⑨〜⑪（miss-streak確定書込→verification単一行→mail）は個別に手でトレースしたが、
B7/B8以外に新たな順序依存・状態不整合・deadlockは見つからなかった。具体的に確認した項目:
- ⑧-fの`should_snapshot`が①のSTART時点値（`consecutive_miss_count_in`/`cooldown_weeks_remaining_in`）
  を渡す点はREQ-CEO-052の文言と一致し、⑧の外側ゲートとの二重チェックは冗長だが矛盾はない。
- rollback発火pass（⑥でtrue）とcooldown-skip pass（①で`cooldown_weeks_remaining_in>0`）の両方で③
  （bandit/BudgetPacer更新）は実行され、⑧（budget-gate/guardrail/agent決定/registry書込）は実行され
  ない、という設計は本文で明示的に正当化されており（"実現ROI/spendという「今週実際に起きた実測データ」
  からの学習は、今週allocationを変更するかどうかとは独立した別の関心事である"）、team lead提示の懸念
  「cooldown-skip週にbanditはupdateするがallocationは書かない、の整合」については矛盾なし。
- ⑨の`ceo-miss-streak.json`書込が`consecutive_miss_count`/`cooldown_weeks_remaining`の両方について
  唯一の確定書込点であることも維持されている（REQ-CEO-057の一元化と整合、grep可能な単一書込箇所）。

---

## Reality-grounding summary (re-verified fresh against live sources)

- `~/anicca/skills/self/cadence-contracts.json` — re-loaded with `json.load` this session: 8 keys
  (`_comment`, `clip`, `affiliate`, `video`, `gig`, `bounty`, `founder-loop`, `pm-earner`), `_comment` is
  `str`, the other 7 are `dict`. Unchanged from iterations 2/3, matches REQ-CEO-001/PROP-CEO-001.
- `~/anicca/skills/self/founder-loop/founder-loop.sh` — 73 lines, `exit "$RC"` remains the literal last
  line (line 73). Unchanged from iterations 2/3, matches REQ-CEO-070/PROP-CEO-022.
- No new external symbols (Mahoraga/agent-os/cadence.py/weekly_report.py/guardrails.py) were introduced or
  modified by this iteration's spec changes; the new step ③ only wires existing REQ-CEO-010/011/014 (all
  previously reality-grounded in iterations 1-3) into the ordering sequence. Reality-grounding remains
  PASS.

---

## 収束傾向 (convergence trend)

Genuine progress this iteration: B6 is resolved with the correct fix technique (formal conjunctive
condition + a test that distinguishes "correctly skipped" from "executed then coincidentally matched" —
exactly what iteration-3 demanded, not a repeat of the "narrative walkthrough asserts what the formal
condition doesn't encode" anti-pattern that caused B3→B4→B6). m5 is resolved cleanly. This is real,
structural progress on the rollback/cooldown state machine specifically — **that subsystem itself does not
produce a 4th consecutive blocking finding this iteration**, which is what this review was asked to judge
most strictly. The cooldown/rollback core (REQ-CEO-052-058's ⑤-⑦-⑨-⑩ chain) is now internally consistent
across all four iterations' worth of scrutiny.

However, the overall verdict is still FAIL, for two reasons that are new in origin but recognizably the
*same underlying root cause* as this feature's very first blocking findings (M1/M3/M4): **incomplete
propagation of a stated invariant across all its call sites.** M1 was "USD conversion missing at the
company_score call site." M4 was "USD conversion fixed at company_score but not propagated to the capital
gate call site." B8 (this iteration) is "USD conversion fixed at company_score and the capital gate, but
not propagated to the bandit reward call site that this very iteration's own M5 fix newly introduced." This
is the third occurrence of the identical failure mode, and it recurred specifically *because* this
iteration's fix for M5 (placing bandit/BudgetPacer into the ordering) created a new call site that inherited
the currency-safety gap by omission, rather than being checked against the existing "must route through
realized_profit_usd()" invariant when it was written. Likewise, B7 (M5's own incomplete range coverage —
023/024/025 unplaced) recurs the *specific* completeness failure iteration-3 named almost verbatim
("020-025" explicitly requested, "022" alone delivered) — an internally inconsistent partial fix of the
same finding being re-reviewed.

The fix technique that must change going forward: when a Builder response claims "M5 resolved" or "the
currency-conversion invariant now covers all call sites," this claim must be checked against a literal
enumeration match (does the fix's ordering-list/routing-list textually contain every REQ number the
adversary previously enumerated?), not just spot-checked against the specific worked example the previous
finding used. Both B7 and B8 would have been caught by mechanically diffing iteration-3's required-fix REQ
list ("020-025", "all bandit/budget/guardrail/agent-decision/log machinery") against the current spec's
actual coverage, rather than trusting the Builder's own "M5修正" changelog tag at face value.

## What must happen before re-review

1. Fix B7: place REQ-CEO-023/024/025 explicitly in the ①-⑪/⑧-a-⑧-f sequence, and resolve the
   `loop-registry.json` double-write ambiguity between REQ-CEO-025's `"budget"` subkey write and
   REQ-CEO-040's `merge_allocation` `"allocation"` subkey write (single unified atomic write, or two
   explicitly-ordered atomic writes with no torn-read window — state which). Extend PROP-CEO-023's
   enumeration to cover 023/024/025.
2. Fix B8: state explicitly that REQ-CEO-010's `realized_earn_usdc` argument must be
   `realized_profit_usd(ledger_earn_entries, fx_config)`-converted, add REQ-CEO-010 to REQ-CEO-002(c)'s
   and REQ-CEO-050's "must route through" enumeration, and add a PROP-CEO-002/013 test case with a
   JPY-denominated fixture proving the raw value never reaches `compute_reward` directly (mirroring
   PROP-CEO-007's existing M4 反証 pattern).
3. Before claiming either fix resolves the finding, mechanically re-check the fix's REQ-number coverage
   against the full enumeration this verdict names (023/024/025 for B7; the M1/M4/B8 "must route through
   realized_profit_usd()" call-site list for B8) rather than checking only the specific worked example.
