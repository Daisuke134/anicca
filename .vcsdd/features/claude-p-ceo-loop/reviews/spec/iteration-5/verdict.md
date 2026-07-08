# Spec Review Verdict — claude-p-ceo-loop (Phase 1c, iteration 5)

Reviewer: fresh-context adversary (no Builder context, no iteration-1/2/3/4 adversary context — zero
memory of authoring any of them). All claims below verified by directly reading the artifacts on disk: the
two spec files as they currently stand in full (`behavioral-spec.md`, 670 lines; `verification-
architecture.md`, 116 lines), the iteration-3 and iteration-4 verdicts (`reviews/spec/iteration-{3,4}/
verdict.md`), and fresh re-reads of the cited ground-truth files (`~/anicca/skills/self/cadence-
contracts.json`, `~/anicca/skills/self/founder-loop/founder-loop.sh`).

## Overall verdict: **FAIL** (3 blocking-severity findings — all new, not carried over; iteration-4's B7
and B8 are genuinely resolved)

## Per-dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Completeness | **FAIL** |
| 2 | Testability | **FAIL** |
| 3 | Consistency | **FAIL** |
| 4 | Reality-grounding | PASS (re-verified fresh, unchanged from iterations 2-4) |
| 5 | 安全境界 (safety boundary) | **FAIL** |

---

## Part A — Disposition of iteration-4's B7/B8 findings, and the two new structural invariants

### B7 (loop-registry.json ordering + double-write ambiguity): **RESOLVED at the level it targeted**

REQ-CEO-023/024/025 now have an explicit position: step ③-c (behavioral-spec.md line 499-504) names all
three by REQ number and states they run unconditionally, every WEEKLY pass, "rollback発火pass・cooldown中
passを含む". `verification-architecture.md`'s PROP-CEO-023 enumeration was correspondingly extended to
`REQ-CEO-010/011/014/022/023/024/025/030/031/032/034/060/058` — the gap iteration-4 named (023/024/025
missing from both the ordering text and the exhaustiveness test) is closed. REQ-CEO-025's write ambiguity
is resolved by a structural change, not a clarifying sentence: REQ-CEO-025/040/053 were all rewritten to
**queue** into an in-memory `registry_updates` accumulator instead of performing direct I/O, and a new
REQ-CEO-044 (`merge_loop_registry_updates`) was introduced as the sole function that performs the actual
`loop-registry.json` write (step ⑨, exactly once per pass). This is a materially different, stronger fix
than iteration-4 asked for (ordering-only) — it eliminates the entire class of "two independent writers to
the same file" bugs by construction, not just by sequencing. Verified by hand: no REQ in section C/D/E
(020-044) performs `open(...,"w")`/`os.replace` on `loop-registry.json` other than REQ-CEO-044 itself; each
one explicitly disclaims direct I/O in its own text (lines 270, 322, 414).

### B8 (REQ-CEO-010's `realized_earn_usdc` not required to route through `realized_profit_usd()`): **RESOLVED**

REQ-CEO-010 (line 195-197) now states explicitly: "第1引数`realized_earn_usdc`には、当該loopの
`ledger_earn_entries`（REQ-CEO-002(c)）を REQ-CEO-050 の `realized_profit_usd(entries, fx_config) -> float`
に通した後のUSD換算済みの値を必ず渡す". REQ-CEO-002(c)'s and REQ-CEO-050's "must route through" enumeration
lists now both include REQ-CEO-010 by name (lines 166, 359-360). A new PROP-CEO-013b mirrors PROP-CEO-007's
M4/反証 pattern with a JPY fixture (`6000 jpy → 40.0 usd`) and explicitly asserts the raw `6000` never
reaches `compute_reward`'s first argument. Step ③-a (line 493-496) wires this into the fixed ordering.
**Genuinely resolved**, verified against both spec text and the corresponding test.

### The two new cross-cutting invariants (INV-CEO-1, INV-CEO-2): structurally the right idea, but **both
contain at least one real, unenumerated exception** — which is exactly the failure class they were
written to eliminate

This iteration's core strategic move (behavioral-spec.md lines 106-133) — replacing per-REQ patches with
two blanket invariants that claim to bind "all `_usd`/`_usdc` params, present and future" and "all
side-effecting REQs" — is the correct fix *technique* for a bug pattern that has recurred 3 times (M1→M4→B8
for currency, M5→B7 for ordering). It is not, however, actually complete as currently drafted. See Part B.

---

## Part B — New findings (grep-verified against every `_usd`/`_usdc` occurrence and every side-effecting
REQ in both spec files, not spot-checked against only the previously-named call sites)

### B9 (new, blocking, Consistency + Completeness — the most severe finding this iteration, directly on the
question asked) — REQ-CEO-044 formally specifies only the **outer** merge (`registry_updates` →
`existing_registry` at step ⑨); the **inner** merge (multiple steps' queue operations accumulating into the
single `registry_updates` dict across a pass) is never specified, and a plausible literal implementation
silently drops subkeys already queued earlier in the same pass for the same loop

Trace the queue-writing steps in the order REQ-CEO-058 actually executes them:

1. **③-c** (line 499-504, runs unconditionally, every pass, all roster loops): "`budget_snapshot_for_
   registry()`の出力を`registry_updates[loop]["budget"]` へ **queue する**" — notation is explicit
   subkey-level assignment: `registry_updates[loop]["budget"] = <value>`.
2. **⑥** (line 512-516, fires only on rollback): "`restore_from_rollback(rollback_snapshot)`の出力を
   `registry_updates`へ**queue**" — `restore_from_rollback`'s own signature (REQ-CEO-053,
   `verification-architecture.md` line 47) returns `dict[str, dict]` shaped like the *entire*
   `ceo-rollback.json` snapshot, i.e. `{loop1: {"allocation": {...}}, loop2: {"allocation": {...}}, ...}`
   for **every loop in the roster at once** (REQ-CEO-052's snapshot shape). The notation here is *not*
   `registry_updates[loop]["allocation"] = ...` (subkey-indexed, like ③-c) — it is "queue the whole
   returned dict into `registry_updates`", with no stated merge rule.
3. **⑧-c** (line 542-543, fires only when the ⑧ gate is true, i.e. never in the same pass as ⑥ — see below):
   "決定した`allocation`を`merge_allocation()`...に通し、更新後の`consecutive_bad_weeks`と合わせて
   `registry_updates`へqueue" — again phrased as "queue into `registry_updates`" without a stated per-key
   merge rule, for the loop(s) the agent acted on.

REQ-CEO-044 (line 332-347) is the **only** place a merge algorithm is formally defined, and it explicitly
operates on the relationship between the fully-accumulated `registry_updates` and `existing_registry`
("`registry_updates`に含まれる全loop×全subkey…を一括で非破壊マージする"). Nothing in the spec states how
step ⑥'s whole-dict output combines with subkeys step ③-c already placed into `registry_updates[loop]`
*earlier in the same pass, before ⑥ runs*. A literal, defensible reading of "queue the output into
`registry_updates`" is `registry_updates.update(restore_from_rollback_output)` — a shallow, top-level
Python `dict.update`. If implemented this way, for any loop present in both the rollback snapshot (i.e.
every roster loop, since REQ-CEO-052's snapshot covers the whole roster) and step ③-c's earlier budget
queue (also every roster loop, unconditionally), `registry_updates[loop]` is **replaced wholesale** with
`{"allocation": {...}}`, silently discarding the `"budget"` subkey ③-c queued moments earlier in the exact
same pass. This is not a rare edge case — **it happens on every single rollback-firing pass, for every
loop in the roster**, because ③-c's budget queue is unconditional (line 490: "毎WEEKLY passで無条件に")
and ⑥'s rollback restore, when it fires, covers the whole roster by construction. The mirror case exists
for ⑧-c: on any ordinary (non-cooldown, non-rollback) pass where the agent updates a loop's allocation,
if ⑧-c's "queue" is implemented the same way (`registry_updates[loop] = {"allocation": ..., "consecutive_
bad_weeks": ...}` instead of `registry_updates.setdefault(loop, {}).update(...)`), the budget subkey
③-c queued for that same loop earlier in the pass is silently dropped again — this time on **every normal
week**, not just rollback weeks.

Note the inconsistent notation between steps is itself evidence the granularity was never actually decided:
③-c is written with explicit subkey indexing (`registry_updates[loop]["budget"]`), while ⑥ and ⑧-c are
written as "queue [output] into `registry_updates`" (dict-level, no subkey named). This is the same failure
signature iteration 2/3 exhibited (a trailing narrative or informal phrase implies behavior the formal text
doesn't actually pin down) — recurring in the exact mechanism (`registry_updates`, the accumulator this
iteration invented specifically to fix B7) that this iteration's own fix introduced.

**Whether ⑥ and ⑧-c can collide with each other in the same pass**: no — the ⑧ gate condition
`cooldown_weeks_remaining_in == 0 and not rollback_fired_this_pass` structurally excludes ⑧-c whenever ⑥
fires (this part of B6's fix is sound, re-verified). But **both ⑥ and ⑧-c independently collide with ③-c**,
which is unconditional and always runs first — and that collision is exactly the "which queue wins" question
the review asked to check, and the spec does not answer it.

**Why the existing tests don't catch this**: PROP-CEO-020 (the normal-pass Goal E2E, Tier 3, required=true
in lean mode) *does* explicitly assert that a single loop's `"allocation"` (from ⑧-c) and `"budget"` (from
③-c) both appear in the same step-⑨ write — this incidentally exercises the ⑧-c-vs-③-c collision and would
catch a naive-replace bug there. But PROP-CEO-021 (the rollback scenario, Tier 3, required=true), which is
the test that exercises the ⑥-vs-③-c collision, only checks *write count* — its own text says the B7-
反証 confirms the combination "をI/Oログ/atomic renameの**タイムスタンプ数**で確認" (verifying the number of
write operations is 1), not the **content** of that write. A rollback pass where ③-c's budget subkey is
silently dropped by ⑥'s replace-style queue would still produce exactly one atomic write to
`loop-registry.json` — PROP-CEO-021 as currently worded would pass even though the resulting file is
missing data that should be there.

**Required fix**: State explicitly, in REQ-CEO-058 (or as a third invariant alongside INV-CEO-1/2), that all
queue operations into `registry_updates` across steps ③-c/⑥/⑧-c are **per-loop, per-subkey merges** —
i.e. `registry_updates.setdefault(loop, {})[subkey] = value` — never a top-level dict replace, and that a
later step's queue for a loop must not clobber an earlier step's already-queued subkeys for that same loop
within the same pass. Since `restore_from_rollback`'s output already comes pre-shaped as
`{loop: {"allocation": {...}}}` per loop (matching `merge_loop_registry_updates`'s own input shape), the
cleanest fix is to have ⑥ apply exactly the same per-subkey queue discipline described for `merge_
allocation` (REQ-CEO-040) rather than being worded as a bulk dict merge — or, equivalently, define
`registry_updates` construction itself as repeated calls to a `queue_registry_update(registry_updates, loop,
subkey, value) -> registry_updates` pure helper used uniformly by ③-c/⑥/⑧-c, with `merge_loop_registry_
updates` (REQ-CEO-044) remaining the sole *terminal* merge into `existing_registry`. Strengthen PROP-CEO-021
to assert the rollback pass's single write's **content** includes both the ③-c-queued `"budget"` subkey and
the ⑥-restored `"allocation"` subkey for the same loop (mirroring what PROP-CEO-020 already does for the
⑧-c case), not just that the write count is 1.

### B10 (new, blocking, Completeness + Consistency) — INV-CEO-1's enumeration is not actually exhaustive:
REQ-CEO-060's `weekly_realized_profit_usd` field is a `_usd`-suffixed field, is not in INV-CEO-1's named
list, and REQ-CEO-060's own text never states it must be `realized_profit_usd()`'s output

INV-CEO-1 (line 113-123) claims: "現時点でこの不変条件の対象となる関数（列挙…）: `company_score`
（REQ-CEO-050）、`capital_increase_within_realized_profit`の第3引数`realized_profit_usd`（REQ-CEO-030(b)）、
`compute_reward`の第1引数`realized_earn_usdc`（REQ-CEO-010）" — three items, explicitly presented as
covering everything currently in scope. Grepping every `_usd`/`_usdc`-suffixed identifier across both spec
files (not just the three named above) surfaces a fourth: REQ-CEO-060's `ceo-escalations.jsonl` schema field
`weekly_realized_profit_usd` (line 597) and its reuse in REQ-CEO-062 (line 608-609, "`weekly_realized_
profit_usd` が 0 以下の loop"). INV-CEO-1's own text defines its scope as "`_usd`/`_usdc` と名の付く**全て
の**パラメータ・引数・**フィールド**" — fields are explicitly included, so a JSONL schema field is squarely
in scope, not merely a coincidental naming collision. Yet: it is absent from the enumeration list, and
REQ-CEO-060's own text (lines 594-603) and step ⑧-e's placement text (lines 546-547, which places REQ-
CEO-060 in the ordering but does not touch its value-sourcing) never state that this field must be built
from `realized_profit_usd(ledger_earn_entries, fx_config)` — the same per-loop value already computed at
③-a and reused at ⑧-c's capital gate. This is the identical failure shape as M1→M4→B8: a `_usd`-named
value with no stated conversion requirement, at a call site this iteration's own new invariant claims (but
fails) to cover. Unlike M1/M4/B8, the practical consequence for REQ-CEO-062's specific ">0 or <=0" gate is
muted (dividing by a positive `jpy_usd_rate` preserves sign), but the field itself — a machine-checkable
escalation-audit record this feature's own design principle treats as evidence — would carry a value ~150x
off magnitude for JPY-denominated loops (gig/affiliate) if left unconverted, corrupting exactly the kind of
audit trail REQ-CEO-062/PROP-CEO-062-style cross-checks (design spec §CEO LOOP, REQ-CEO-062) depend on.

**Required fix**: Add REQ-CEO-060's `weekly_realized_profit_usd` to INV-CEO-1's enumeration list, and add
one sentence to REQ-CEO-060 stating this field must be `realized_profit_usd(ledger_earn_entries, fx_config)`
for the loop in question (the same value already computed at ③-a/⑧-c, no new computation needed — just a
routing statement, mirroring REQ-CEO-010's own fix this iteration). Since INV-CEO-1 exists specifically so
future additions don't need per-REQ patches, this finding also demonstrates INV-CEO-1's "対象と**なる**関数
（列挙）" framing needs re-checking against a mechanical grep of every `_usd`/`_usdc` token in the spec
before the enumeration can be trusted as complete — the same lesson iteration-4 drew about REQ-CEO-023/024/
025, now recurring for REQ-CEO-060.

### B11 (new, blocking, Completeness) — REQ-CEO-020 (`record_cost_event` write to `ceo-cost-events.jsonl`)
has no REQ-CEO-058 ①-⑫ step placement, and the spec does not state whether it is even part of the CEO
WEEKLY pass at all — a direct, unaddressed exception to INV-CEO-2's unqualified "全てのREQ" claim

INV-CEO-2 (line 124-127) states, without qualification: "副作用…を持つ**全ての**REQは、REQ-CEO-058が定める
①〜⑫のいずれか1箇所に必ず明示的な位置を持たなければならない。位置未定義の副作用REQはそれ自体がspec
違反である。" REQ-CEO-020 (line 235-238) is unambiguously a side-effecting REQ (an atomic append to
`ceo-cost-events.jsonl`, one of this feature's own declared new state files per the "In scope" section).
Scanning REQ-CEO-058's ①-⑫ (and ③-a/③-b/③-c, ⑧-a…⑧-e) for any mention of `record_cost_event` or
REQ-CEO-020: **none found**. Unlike REQ-CEO-034 (`ceo-lessons.jsonl`, placed at ⑧-d) or REQ-CEO-060
(`ceo-escalations.jsonl`, placed at ⑧-e) — which are both explicitly assigned a step and separately noted as
outside INV-CEO-2's *loop-registry.json single-write* sub-constraint (not outside step-placement itself) —
REQ-CEO-020 has no step assignment of any kind.

This is not merely an oversight to patch by adding a step number, because it's unclear the REQ *belongs* in
the WEEKLY ①-⑫ sequence at all: unlike every other REQ in this spec, REQ-CEO-020's text carries no
"WEEKLY"/"DAILY" cadence qualifier (contrast REQ-CEO-002's "WEEKLY…", REQ-CEO-003's "DAILY…"), and its own
wording — "各 loop の pass 実行コスト（token/USD 見積り、**呼び出し元が渡す引数**）" — describes a
general-purpose recording utility invoked by "the caller" per **any loop's own pass**, which each loop (clip,
gig, video, affiliate, bounty, pm-earner) would presumably call every time *it* runs, independent of and far
more frequently than the CEO's own once-a-week pass. If that reading is correct, REQ-CEO-020 is not one of
"REQ-CEO-058の①〜⑫" at all, and integrating it would require each of those other loop scripts to call
`record_cost_event` — none of which are listed in this feature's "In scope" section (which names only
`founder-loop.sh` among existing loop scripts as touched, via REQ-CEO-070's single insertion point). If that
reading is wrong and REQ-CEO-020 is instead meant to fire once per CEO WEEKLY pass as a company-wide
estimate, it needs an explicit ①-⑫ position like every other side-effecting REQ. The spec currently commits
to neither reading, which means REQ-CEO-021's `weekly_spend_by_loop()`/`monthly_spend_by_loop()` (step
③-a/③-b/③-c's budget/reward inputs) have an unstated dependency: if REQ-CEO-020 is never actually invoked by
anything in this feature's scope, `ceo-cost-events.jsonl` stays permanently empty, `weekly_spend_by_loop()`
always returns `{}`/zeros, `BudgetPacer.update()` (REQ-CEO-014) is always fed `0`, and REQ-CEO-010's reward
denominator (`weekly_spend_usd`) is always `0` — silently defeating the entire budget-pacing mechanism this
iteration's own text (REQ-CEO-014) describes as load-bearing ("会社全体の週次spendがceilingに近づくほど…
ソフトなコストペナルティをかける").

**Required fix**: State explicitly who calls `record_cost_event` (REQ-CEO-020) and when — either (a) each of
the 6 other loop scripts, in which case add those integration points to "In scope" and specify the call site
per script (mirroring REQ-CEO-070's precision for founder-loop.sh), or (b) the CEO WEEKLY pass itself, in
which case give it an explicit ①-⑫ position (most plausibly folded into step ③, alongside REQ-CEO-021's
reads, if it's a self-estimate of the CEO pass's own cost — though this reading sits awkwardly with the
per-"呼び出し元" phrasing). Either way, this must be resolved before REQ-CEO-014/010's spend-input
dependency chain can be considered actually wired, not just described.

### Steps traced, no defect found beyond B9/B10/B11

Independently hand-traced ①②④⑤⑦⑨⑩⑪⑫ against the current text (not the prior iterations' traces): the
START-value freezing convention (①), the `should_snapshot`/`should_rollback` START-time-value discipline
(REQ-CEO-052/053 both explicitly say they consume `..._in` values, verified consistent with ⑦'s
`next_cooldown_weeks_remaining` also consuming `cooldown_weeks_remaining_in`), the ⑧ gate's exact conjunction
(`cooldown_weeks_remaining_in == 0 and not rollback_fired_this_pass`, re-verified byte-for-byte identical to
iteration-4's fix, still correctly excludes both cooldown-continuation and the rollback-firing pass itself),
and the ⑩/⑪ single-write-per-file discipline for `ceo-miss-streak.json`/`ceo-verification.jsonl` are all
internally consistent. No new B6-class (formal-condition-vs-narrative mismatch) defect was found in the
cooldown/rollback arithmetic itself this iteration — that specific subsystem (the `cooldown_weeks_remaining`
state machine, independent of the `registry_updates` accumulator) has now survived two consecutive iterations
(4 and 5) without a new defect, which is genuine, durable progress worth noting separately from B9-B11 below.

---

## Reality-grounding summary (re-verified fresh against live sources)

- `~/anicca/skills/self/cadence-contracts.json` — re-loaded with `json.load` this session: 8 keys
  (`_comment`, `clip`, `affiliate`, `video`, `gig`, `bounty`, `founder-loop`, `pm-earner`), `_comment` is
  `str`, the other 7 are `dict`. Unchanged from iterations 2-4, matches REQ-CEO-001/PROP-CEO-001.
- `~/anicca/skills/self/founder-loop/founder-loop.sh` — 73 lines, `exit "$RC"` remains the literal last
  line (line 73). Unchanged from iterations 2-4, matches REQ-CEO-070/PROP-CEO-022.
- No new external symbols (Mahoraga/agent-os/cadence.py/weekly_report.py/guardrails.py) were introduced or
  modified by this iteration's spec changes; the new INV-CEO-1/INV-CEO-2 invariants and REQ-CEO-044 are
  entirely new pure/queue-discipline text internal to this feature, not references to pre-existing code, so
  there is nothing further to re-verify against disk beyond what iterations 2-4 already confirmed.
  Reality-grounding remains PASS.

---

## 収束傾向 (convergence trend)

Genuine, durable progress this iteration: B7 and B8 are both resolved, and resolved with the *stronger* fix
technique iteration-4's own closing note demanded (mechanical enumeration re-checking rather than trusting
the Builder's changelog tag) — the queue/accumulate-then-single-write architecture (`registry_updates` +
REQ-CEO-044) is a structurally sound answer to the repeated "two writers to one file" bug class, and the
cooldown/rollback arithmetic core (REQ-CEO-052-058's ①②④⑤⑥⑦⑨⑩⑪ chain, independent of the accumulator's
internal merge semantics) has now held for two iterations running without a new defect — real, non-trivial
progress on what was, through iterations 1-3, this spec's most consistently defect-producing subsystem.

However, the overall verdict is still FAIL, and — as directly asked — **this is not yet convergence**: five
iterations in, this review found 3 new blocking findings, all newly introduced by *this iteration's own
fix*. This is the same underlying failure mode that has now appeared in five different guises across five
iterations — **a fix closes the specific gap it targets while leaving the new mechanism it introduces to
close that gap incompletely specified at its edges** — B3 (rollback timing) → B4 (cooldown race, introduced
by B3's fix) → B6 (allocation overwrite, introduced by B4's fix) → B7/B8 (ordering + currency gaps,
introduced by M5's fix) → **B9/B10/B11 (registry_updates inner-merge semantics + enumeration completeness,
introduced by B7's own fix)**. The specific new mechanism this iteration invented to solve B7 — the
`registry_updates` in-memory accumulator — is itself now the subject of the most severe finding (B9),
precisely because its *own* internal consistency (how multiple queue operations across ③-c/⑥/⑧-c combine)
was assumed rather than formally stated, mirroring the exact "narrative claims completeness, formal text
doesn't establish it" pattern that has recurred at every prior step of this chain. B10 and B11 show the two
new blanket invariants (INV-CEO-1/2), while the right *strategy* for preventing exactly this recurrence, are
not yet actually exhaustive as currently drafted — each has at least one real, mechanically-discoverable
exception (a `_usd`-suffixed field for B10, a REQ with no stated cadence or caller for B11) that a literal
grep-and-cross-check (which this review performed, and which the invariants' own text implies should have
been performed before claiming completeness) surfaces.

The fix technique that must change going forward, again: an invariant that *claims* "all X" must be checked
by mechanically enumerating every occurrence of the pattern it claims to cover (every `_usd`/`_usdc` token,
every side-effecting REQ) against its own stated list — not validated only against the specific named call
sites the previous adversary's findings happened to use as examples. B7/B8's enumeration extensions (023/
024/025, REQ-CEO-010) were each themselves incomplete relative to the newly-introduced invariants' own
unqualified claims, and this needs one more explicit pass: grep every `_usd|_usdc` identifier and every
side-effecting REQ number in the spec, cross-check each against INV-CEO-1's/INV-CEO-2's enumeration, and
close any gap found — the same mechanical process this review just performed to find B10/B11.

## What must happen before re-review

1. Fix B9 (highest priority — the accumulator this iteration invented to fix B7 has an unresolved internal
   merge-order gap): state explicitly that `registry_updates` queue operations across ③-c/⑥/⑧-c are
   per-loop, per-subkey merges (never a top-level dict replace), ideally via one shared pure helper
   (`queue_registry_update(registry_updates, loop, subkey, value) -> registry_updates`) used uniformly by
   all three steps, with REQ-CEO-044's `merge_loop_registry_updates` remaining strictly the terminal
   `registry_updates → existing_registry` merge. Strengthen PROP-CEO-021 to assert the rollback pass's
   single write's *content* (not just its count) includes both ③-c's queued `"budget"` subkey and ⑥'s
   restored `"allocation"` subkey for the same loop, mirroring what PROP-CEO-020 already asserts for the
   ⑧-c case.
2. Fix B10: add REQ-CEO-060's `weekly_realized_profit_usd` to INV-CEO-1's enumeration, and state in
   REQ-CEO-060 that this field must be the same `realized_profit_usd(ledger_earn_entries, fx_config)` value
   already computed at ③-a/⑧-c for the loop in question.
3. Fix B11: state explicitly who calls REQ-CEO-020's `record_cost_event` and when — either give it an
   explicit ①-⑫ step position (if it's part of the CEO's own WEEKLY pass) or declare it out of this
   feature's WEEKLY-pass ordering scope and add the corresponding per-loop-script integration points to "In
   scope" (if it's called by each of the other 6 loop scripts) — and confirm which reading is consistent
   with REQ-CEO-014/010's dependency on non-empty `ceo-cost-events.jsonl` data actually existing.
4. Before claiming any of the three resolves its finding, mechanically grep every `_usd`/`_usdc` token and
   every side-effecting-REQ number across both spec files and cross-check each against INV-CEO-1/INV-CEO-2's
   enumerations, rather than checking only the specific fields/REQs this verdict names.
