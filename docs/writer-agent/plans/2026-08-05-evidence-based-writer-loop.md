# Evidence-based Writer loop correction

## 1. Overview

The Writer must run every day without equating daily operation with forced
daily publication. The prior shipment prose treated editorial feedback as
non-blocking even when factual or citation integrity remained unresolved. That
contradicts the live terminal-quality repair and primary platform guidance.

The corrected loop creates one daily run, researches one reader job, permits
bounded revision and at most one evidence-backed topic reroute, publishes only
a quality-eligible artifact, and closes an exhausted artifact without
poisoning the next day. It does not create a second short fallback article.

## 2. Acceptance Criteria

1. One JST day creates at most one normal run and at most one bounded topic
   reroute inside that run.
2. An artifact with unresolved factual, citation, identity, policy, or harm
   defects creates no publication intent or delivery row.
3. Editorial exhaustion is keyed by `(language, current_article_sha256)`: a
   newly authorized reroute hash gets one bounded evaluation, while the same
   language/hash remains exhausted and cannot purchase another call; a
   terminal miss never poisons the next JST day.
4. A PASS artifact dispatches every active-six destination independently;
   one destination failure cannot cancel the others.
5. Topic selection binds reader, problem, transformation, deliverable, price
   hypothesis, distribution path, and multiple independent source bodies.
6. The revenue controller keeps one-time revenue separate from MRR and reaches
   the $10,000 MRR gate only from active external recurring contracts.
7. Every strategy change binds one variable, a baseline, a candidate, measured
   funnel/revenue/cost outcomes, and KEEP/REVERT/INCONCLUSIVE.

## 3. As-Is / To-Be

| Area | As-Is | To-Be |
|---|---|---|
| Daily outcome | Prose implies shipment regardless of editorial debt | Daily execution; publication only when eligible |
| Failure | Quality state could poison later runs | Hash-bound terminal rejection; next day starts cleanly |
| Replacement | Ambiguous fallback/replacement language | No fallback article; one bounded evidence-backed reroute |
| Review | Multiple overlapping gates appear to own taste | Four decision dimensions: factual integrity, reader job, original value, offer fit; deterministic safety/policy checks remain hard blockers |
| Topic | Vendor claims can dominate supply | Paid-market, reader-demand, publisher, and owned-funnel evidence select the problem first |
| Revenue | Mixed one-time monthly target precedes MRR | Cash-learning gates remain separate; $10K MRR uses only subscriptions and recurring retainers |

## 4. Test Matrix

| # | To-Be | Test Name | Coverage | Execution |
|---:|---|---|---|---|
| 1 | One daily run, one reroute | `test_daily_run_and_reroute_are_bounded` | PLANNED | NOT RUN |
| 2 | Unsafe debt never publishes | `test_unresolved_integrity_defect_has_no_publication_intent` | PLANNED | NOT RUN |
| 3 | Terminal miss releases next day | `test_terminal_quality_miss_allows_next_jst_day` | PLANNED | NOT RUN |
| 4 | Active-six failure isolation | `test_one_destination_failure_does_not_cancel_others` | PLANNED | NOT RUN |
| 5 | Demand-bound topic card | `test_selected_topic_binds_demand_offer_and_sources` | PLANNED | NOT RUN |
| 6 | MRR excludes one-time money | `test_mrr_requires_active_recurring_external_contract` | PLANNED | NOT RUN |
| 7 | One-variable learning | `test_strategy_promotion_requires_matched_canary` | PLANNED | NOT RUN |
| 8 | Language/hash editorial exhaustion | `test_editorial_exhaustion_is_scoped_to_language_and_current_hash` | PLANNED | NOT RUN |

`Coverage=PLANNED` means every To-Be has an explicit future test identity;
`Execution=NOT RUN` is the current truth for this plan's new contracts. Each
row moves to IMPLEMENTED/PASS only after its code and execution receipt exist.

## 5. Boundaries

- DO NOT create or publish a lower-quality fallback article to satisfy cadence.
- DO NOT count views, paid-state configuration, test payments, affiliate
  commission, or one-time article sales as MRR.
- DO NOT reactivate X Post JA or X Article EN before their measured gates.
- DO NOT add products derived from articles before the direct-writing revenue
  gate permits them.
- Legal/KYC and irreversible owner-payment actions remain explicit exceptions.

| Item | Value |
|---|---|
| UI変更 | なし |
| 結論 | Maestro: 不要（理由: runtime、ledger、scheduler、receipt契約の変更でありmobile UIを変更しない） |

## 6. Execution Steps

1. Verify the live next-day start controller against the terminal run.
2. Implement and pass the active-six isolation and no-forced-publication
   contracts; then record those receipts in the SSOT.
3. Replace vendor-biased topic authority with demand-bound selection and prove
   one live bilingual article from full source bodies.
4. Close public Money Control, first external payments, matched learning
   canary, and revenue gates in SSOT order.
5. For every implementation slice: RED, GREEN, focused regression, full Writer
   regression, live owner E2E, receipt update, commit, and push.

The remaining revenue/UX order is binding: hash-keyed editorial repair and
current-hash reader/editorial gates -> active-six publication/readback and money
sync -> three consecutive active-six runs -> public Money Control plus Telegram
parity (same snapshot, verified/unknown/pending separated) -> accepted publisher
work -> first note purchase -> first Substack contract/renewal -> self-owned
unlock/renewal -> matched learning canary -> first dollar -> `$400` month ->
`$1,000` month with three autonomous positive weeks -> scorable unit economics
-> three `$10,000` revenue months -> three `$10,000` active-MRR months with
positive net margin. No view, paid-state configuration, test payment, estimate,
or one-time article sale satisfies MRR. Telegram sends natural-language deltas;
the SSOT/spec, raw logs, and generated artifacts are never sent as user files.

## Task 0: Restore the truthful green baseline

The runtime contract is Terra medium, but one historical test still expects
Luna xhigh. Change only that stale expectation and its name so the test asserts
the current model/effort boundary. Run the focused model-runner test and the
complete Writer suite. This task changes no production behavior.

Done receipt: focused test passes; complete Writer suite has zero failures; the
diff changes only the stale test contract; commit and push exist.

Status: DONE. The stale test first failed with `1 failed, 28 passed`, then
passed as `29 passed` after changing only its model/effort expectation and
name. The complete Writer suite passed `685/685` with seven pre-existing
multiprocessing deprecation warnings. Feature commits are `120d6e8d` and
`76d5b303`; live-branch commits are `e1fe2565` and `01d36dda`. A fresh Terra
task review found no critical or important issue and approved the slice.

## Task 1: Prove terminal quality releases the next JST day

Use the live hash-bound terminal run as input. Prove today's terminal miss is
closed, tomorrow's decision is `new`, no publication state or destination
ledger row exists, and no provider invocation is added. Add a real behavior
test only if the existing suite does not already protect this exact transition.

Done receipt: focused automated coverage plus live-state read-only output. This
does not claim the future scheduled launch occurred before its real clock time.

Status: DONE without a code change. Existing behavior test
`test_second_terminal_quality_block_closes_daily_miss` already protects the
exact transition and its focused file passes `31/31`. Live run
`20260804-214206` returns `skip-quality-miss` for `2026-08-05` and `new` for
`2026-08-06`; publication state is absent, matching destination rows are zero,
and the provider attempt count remains one. Fresh Terra review approved the
evidence with no findings. This proves next-day eligibility, not execution of a
future scheduled launch.

## Task 2: Prove active-six isolation and no forced publication

Write RED behavior tests first. A current-hash ineligible artifact creates no
publication intent; a quality-eligible artifact creates all active-six intents;
one destination failure leaves the other five owned and recoverable; dormant X
Post JA and X Article EN produce explicit skip receipts without an SLO breach.

Done receipt: RED observed, minimal GREEN implementation, focused and full
Writer regression, live owner E2E, commit and push.

Status: DONE. The final runtime tip is `2a332475` on the feature branch and
`493b185f` on the live branch. RED rounds exposed missing active/dormant
separation, dormant mutation paths, hidden X Post initialization, false
completion labels, legacy completion/routing errors, untrusted state paths,
lost legacy timing/slot rules, and divergent marker inference. The final
Writer suite passes `706/706`; four shell owner contracts, isolated note/daily
workers, syntax, compile, and diff checks pass. The installed launchd owner
points at the canonical pending worker, has last exit `0`, and three real
unmarked historical states resolve as `legacy-exact8`. No external publication
was triggered for this verification. Fresh Terra review approved with zero
critical, important, or minor findings.

## Task 3: Replace vendor-biased topic authority

Write RED behavior tests first. Collect paid-market, reader-demand, publisher,
and owned-funnel observations; limit source-family concentration; bind buyer,
problem, transformation, deliverable, price hypothesis, distribution path,
and multiple full source bodies to each selected card. Read X Article bodies
from the rendered CDP DOM when selected. Produce one live JA/EN article from a
paid-demand card and dispatch it only after current-hash eligibility.

Current live receipt: claim run `309` created `paid-demand:7c43...` with X
captures `2/2 valid`; the bilingual article run is the current
`daily-2026-08-06` recovery described in the canonical live receipt section
below. Task 3 remains open until current-hash editorial/reader gates pass and
active-six publication/readback plus money sync are observed.

Done receipt: source-family fixtures, one live selected card, source-body
hashes, prompt hash, bilingual article hashes, active-six public readbacks,
commit and push.

## Current live receipt (2026-08-06 JST)

See the detailed canonical receipt in
`docs/writer-agent/WRITER-AGENT-SSOT.md#26-current-live-receipt--2026-08-06-jst`;
this plan does not duplicate it. The installed runtime/remote/marker are all
`06141970` after the reviewed Civo series. Claim launchd run `309` exited `0`
`READY / FILLED`, queue `0 -> 1`, and created `paid-demand:7c43...`; X capture
was `2/2 valid`. Feature `4295cf8f` and the live equivalent contain separate
authoritative Civo full-body and fixed structural-window evidence reviewed
`SHIP`.

The `daily-2026-08-06` run generated JA/EN research, images, and diagram;
self-healed `how-to -> comparison`; current identity+CTA hashes are `PASS`;
editorial refused the new hashes with exit `77`
(`high-escalation-exhausted`) because the prior high FAIL was not keyed by
language and current hash. No publication state, public URL, payment, or
revenue exists. Telegram message ID is `7398`; received revenue and MRR are
`$0`.

### Next exact task

Implement RED/GREEN for language+current-hash exhaustion, deploy the canonical
runtime, kickstart `ai.anicca.article-resume`, pass current-hash editorial and
reader gates, dispatch/read back active-six, then run money sync. Same-hash
exhaustion remains terminal; a newly authorized reroute hash gets one bounded
evaluation. This is the next task, not a passive schedule wait.

## Task 4: Close revenue, reporting, and learning gates

Deploy public Money Control parity, advance publisher opportunities, collect
the first external note/Substack/self-owned/retainer receipts, and run one
matched one-variable learning canary. Keep one-time revenue separate from MRR.
Advance $1, $400, $1K, $10K monthly, and $10K active MRR only from their exact
external receipts.

Done receipt: each SSOT gate passes in order; no projection, internal transfer,
test payment, view, or one-time sale is counted as MRR.
