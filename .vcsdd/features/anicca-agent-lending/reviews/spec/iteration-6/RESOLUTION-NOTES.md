# Resolution Notes — Spec Review Iteration 6 (anicca-agent-lending)

Iteration 6 FAILed with 3 findings (2 major, 1 minor): FIND-501, FIND-502, FIND-503. This document records
exactly what changed, per finding, in `specs/behavioral-spec.md` and `specs/verification-architecture.md`,
with the current line ranges of the edited sections as of this resolution pass (both files grew:
`behavioral-spec.md` 1763 → 2013 lines, `verification-architecture.md` 384 → 415 lines — the SAME "moving
target" discipline REQ-113 already establishes for line-range citations applies to this document's own
internal cross-references too). `state.json`, the reviews manifest/verdict files, and git history were NOT
touched, per instructions — no commit/push was performed.

---

## FIND-501 (major) — false "deadlock avoidance" rationale for the lock-acquisition order

**Grounding read performed first, as directed:** `~/anicca/skills/economy/gig/lib/lock.mjs`'s real
`withGigLock` implementation, re-read fully fresh this session (lines 153-158 `acquire()`, lines 174-179
`withGigLock`'s own docstring, lines 187-209 `withGigLock`'s own body). Confirmed: `acquire()` is a SINGLE,
non-blocking attempt — `tryCreateLockFile` (POSIX `wx` exclusive create), then AT MOST ONE
`reclaimStaleLock` attempt if that fails (itself also non-blocking: one `fs.stat` + one `fs.rename`
attempt) — there is NO internal retry-with-wait loop anywhere in this module. `withGigLock`'s own docstring
states verbatim: "If another call already holds the lock, returns a fail-closed rejection WITHOUT ever
calling `fn()` — no queueing, no waiting." A caller whose SECOND (inner) nested lock acquisition fails
returns `{ok:false}` immediately, and its own FIRST (outer) lock is released in `withGigLock`'s own
`finally` block (lines 203-208) — it is never held-and-waited. This confirms classical hold-and-wait
deadlock (party A holds resource 1 and blocks waiting for resource 2, while party B holds resource 2 and
blocks waiting for resource 1) is structurally impossible against this primitive, REGARDLESS of what order
the two nested `withGigLock` calls acquire their keys in — the prior revision's "textbook total-lock-
ordering deadlock-avoidance technique" framing for `resolveLoanLockAcquisitionOrder`'s fixed order was
therefore analytically false, exactly as the finding stated.

**Decision made (per the finding's own explicit framing: ground the ordering in a real reason, or drop
it):** the fixed lexicographic order is RETAINED — but its stated justification is corrected to TWO
honestly-different reasons, neither of which is "prevents deadlock": (1) a single deterministic convention
every call site derives its nested lock order from, instead of each independently choosing an ad-hoc
"lender first"/"borrower first" rule (avoiding a class of easy-to-get-inconsistent bugs across call sites,
and giving Tier-2 concurrency tests one canonical, reproducible acquisition order to reason about for a
given `(lenderId, borrowerId)` pair); and (2) forward-insurance should `lock.mjs` ever be changed to a
blocking/retry-with-backoff primitive in the future (at which point a fixed total order WOULD become
genuinely required to prevent a real hold-and-wait deadlock) — having the ordering already in place today,
at zero marginal cost, means a future maintainer making that change does not also have to invent and
retrofit a lock-ordering discipline under time pressure. The spec now explicitly states that removing
`resolveLoanLockAcquisitionOrder` entirely (in favor of "acquire both locks in any consistent per-call
order") would be EQUALLY CORRECT against today's fail-fast lock — the function is kept anyway, for reasons
(1) and (2), never because it is required for correctness today. This directly answers the finding's own
final question ("is there truly zero risk either way from a correctness standpoint, only from a
UX/retry-experience standpoint?") — yes: zero correctness risk either way against today's lock; the value
retained is convention/insurance, not risk-avoidance.

**Fix implemented, `specs/behavioral-spec.md`:**
- REQ-106's "Lock-acquisition order" paragraph (now lines 990-1040, previously the "deadlock avoidance"
  paragraph at the prior revision's lines 793-815) is REWRITTEN in full: the opening SHALL statement is
  preserved (fixed lexicographic order), but the false "textbook total-lock-ordering deadlock-avoidance
  technique" sentence is REMOVED and replaced with three new sub-paragraphs — "Corrected justification"
  (lines 999-1018, states the fail-fast mechanism precisely, cites `lock.mjs` lines 153-158/174-179/
  187-209 by line number, and additionally notes the lender/borrower lock-key namespaces are disjoint as a
  SECOND, independent reason classical lock-ordering deadlock could never occur here even against a
  blocking lock); "Given ordering is NOT required..." (lines 1020-1032, states the two retained,
  honestly-different reasons and explicitly says removing the function would be equally correct today); and
  the closing paragraph (lines 1038-1057, unchanged in substance from the prior revision's closing
  paragraph — the `resolveLoanLockAcquisitionOrder` helper declaration, the release-order statement, the
  `lock_held` fail-closed refusal shape, and the pre-existing `GOJO_SENDER_ID`-style `borrower_`-prefix
  naming-collision limitation — with a corrected one-line pointer replacing "new PROP-106m" with "new
  PROP-106m, its own description corrected this revision to match the justification above — never
  'deadlock avoidance'").
- REQ-106's own Acceptance Criteria bullet for `resolveLoanLockAcquisitionOrder` (now lines ~1352-1360)
  gains an appended clause: "kept as a deterministic-convention and forward-insurance discipline, resolves
  this revision's own FIND-501; NOT a deadlock-avoidance mechanism, which today's fail-fast `lock.mjs` does
  not require regardless of acquisition order — see the corrected justification above."
- Header/changelog: this fix is entered as its own row in the new "Changelog (iteration 6 → current)" table
  (see FIND-503's own fix, below), since that table did not exist before this pass.

**Fix implemented, `specs/verification-architecture.md`:**
- Purity Boundary Map row for `resolveLoanLockAcquisitionOrder` (line 25): the phrase "preventing deadlock
  between two concurrent attempts that might involve the same lender+borrower pair in different roles" is
  REMOVED and replaced with a corrected description citing FIND-501, the fail-fast mechanism, and the two
  retained reasons (deterministic convention + forward-insurance).
- Effectful Shell row for `lock.mjs` (line 36): the parenthetical "total lock ordering, deadlock-free by
  construction" is REMOVED and replaced with "a deterministic-convention/forward-insurance discipline,
  resolves FIND-501; NOT deadlock-avoidance, which today's non-blocking, fail-fast `withGigLock` does not
  require regardless of acquisition order."
- Proof Obligations table, PROP-106m row (line 146): the description column's "the total-lock-ordering
  deadlock-avoidance primitive REQ-106's dual-lock design depends on" phrase is REMOVED and replaced with
  "kept as a deterministic-convention and forward-insurance discipline REQ-106's dual-lock design relies
  on," followed by an explicit "Corrected this revision (resolves FIND-501): this is NOT a
  deadlock-avoidance primitive" sentence restating the fail-fast mechanism. The test-method column (the
  actual unit-test fixture requirements) is UNCHANGED — the sort function's own correctness proof was never
  the false part of this finding, only its stated JUSTIFICATION was.
- Verification tiers/Verification Strategy Tier-0/Tier-1 narrative and Gate item (3) mentions of
  `resolveLoanLockAcquisitionOrder`/PROP-106m were checked — none of them independently repeated the false
  "deadlock avoidance" framing beyond the three locations fixed above (confirmed via a full-file grep for
  the literal string "deadlock" both before and after this pass — the only remaining occurrences post-fix
  are the corrected, honest ones listed above and their behavioral-spec.md counterparts).

---

## FIND-502 (major) — kill-switch has zero coverage for larger, established-tier loans (bust-out blind spot)

**Design decision made:** rather than folding a general-purpose monitor into REQ-105 (which is scoped,
by its own title, specifically to the cold-start ladder), a NEW requirement, REQ-114, is added — mirroring
this document's own existing precedent of numbering a requirement by discovery order while placing it
topically (REQ-112/REQ-113 are likewise numbered above REQ-108/109 despite being inserted structurally
within REQ群C). REQ-114 is placed immediately after REQ-105 and before REQ群C's own header, since it is
topically a monitoring-plan companion to REQ-105, not an issuance-mechanics concern.

**Fix implemented, `specs/behavioral-spec.md`:**
- New section, **REQ-114: Colony-wide default-rate monitoring — ALL loan tiers, dollar-weighted (bust-out /
  reputation-laundering defense, resolves this revision's own spec-review iteration-6 FIND-502)** (lines
  796-935, inserted between REQ-105's own closing `---` divider and the `### REQ群C: Issuance mechanics`
  header). Contents:
  - EARS SHALL statement introducing `computeOverallDefaultRateUsd({loanRows}) → {totalIssuedUsd,
    totalDefaultedUsd, defaultRateUsd, sampleSize}`, explicitly scoped to operate ALONGSIDE, never
    replacing, REQ-105's cold-start-only monitor.
  - A "Why a count-based metric alone is insufficient here" paragraph restating the finding's own bust-out/
    reputation-laundering scenario precisely (colony-wide, not lender-specific reputation; a large default
    invisible to `computeColdStartRepaymentRate`'s own sample once `successfulOnTimeRepayments` is no
    longer `0`; a pure loan-count metric under-weighting a single large dollar loss).
  - The function's own precise definition (terminal-row-only sampling, last-write-wins reduction, dollar
    sums for issued/defaulted principal, `.toFixed(6)` clamping, null-not-throw on zero sample).
  - A "Kill-switch enforcement" paragraph introducing the SECOND pure function,
    `evaluateOverallDefaultKillSwitch({totalIssuedUsd, totalDefaultedUsd, defaultRateUsd, sampleSize}) →
    {paused, reason}`, mirroring `evaluateColdStartKillSwitch`'s own two-branch rule
    (`sampleSize>=10 AND defaultRateUsd>0.20`, OR `sampleSize<10 AND totalDefaultedUsd>0`), specifying
    REQ-106's issuance step calls it IN ADDITION TO (never instead of) `evaluateColdStartKillSwitch`, for
    EVERY loan request regardless of tier, refusing with `reason:"overall_default_paused"` when paused.
  - A "Threshold, honestly grounded" paragraph explicitly flagging the `0.20` figure as an UNVALIDATED
    starting placeholder — reusing REQ-105's own already-cited Federal Reserve credit-builder study ONLY
    for internal consistency of the two kill-switches' relative strictness, NOT as an independently
    validated dollar-weighted benchmark — following the SAME honest, no-overclaim discipline this document
    already applies to `LOAN_INTEREST_RATE` and REQ-105's own threshold.
  - Five Edge Cases (zero-sample handling; the single-large-default-while-small-sample bust-out case;
    dollar-weighting not diluted by loan count; the two monitors' overlap/non-overlap relationship;
    fail-closed malformed-numeric-input handling).
  - Eight Acceptance Criteria bullets, including the required dollar-dominance fixture (`8 × $0.02` repaid
    + `1 × $5.00` defaulted → `defaultRateUsd ≈ 0.969`, `sampleSize:9`), the zero-sample fixture, three
    `evaluateOverallDefaultKillSwitch` threshold fixtures, a new Tier-0 real-code-wiring check (new
    PROP-114c, mirroring PROP-105h's discipline), and a new both-kill-switches-independent-and-additive
    fixture (new PROP-114d).
- REQ-106's own Edge Cases (new bullet at lines 854-859, immediately after the existing `cold_start_paused`
  bullet) and Acceptance Criteria (new bullet at lines 1313-1318, immediately after the existing PROP-105h
  structural-check bullet) both gain a parallel entry for `evaluateOverallDefaultKillSwitch`/
  `reason:"overall_default_paused"`, stated as additive to, never a replacement of, the existing cold-start
  kill-switch wiring.
- Purity boundary analysis overview table gains two new rows (lines 277-278) — "Colony-wide, dollar-weighted
  default-rate monitoring" and "Colony-wide default kill-switch enforcement" — immediately after the
  existing "Cold-start kill-switch enforcement" row.
- Non-functional requirements (money-safety) bullet list (line 315) gains a new clause: "colony-wide
  loan-default risk is monitored by DOLLAR VALUE across ALL loan tiers, not merely the smallest cold-start
  tier (REQ-114's `evaluateOverallDefaultKillSwitch`, operating ALONGSIDE REQ-105's cold-start-specific
  monitor, resolves this revision's own FIND-502)."

**Fix implemented, `specs/verification-architecture.md`:**
- Purity Boundary Map gains two new rows (lines 27-28), immediately after the existing
  `computeColdStartRepaymentRate` row, for `computeOverallDefaultRateUsd` and
  `evaluateOverallDefaultKillSwitch`, both citing REQ-114 and FIND-502.
- Proof Obligations table gains four new rows (lines 131-134), inserted between the existing PROP-105h row
  and PROP-106a: **PROP-114a** (Tier 1 — `computeOverallDefaultRateUsd`'s own dollar-dominance and
  zero-sample fixtures), **PROP-114b** (Tier 1 — `evaluateOverallDefaultKillSwitch`'s own threshold-rule
  fixtures), **PROP-114c** (Tier 0 — the real-production-code wiring check, mirroring PROP-105h exactly),
  and **PROP-114d** (Tier 1/2 — the both-kill-switches-independent-and-additive fixture).
- Verification tiers narrative (Tier 0 list, line ~45-49; Tier 1 list, lines ~68-70) and Verification
  Strategy narrative (Tier 0 list, lines ~171-175; Tier 1 list, lines ~192-194) both updated to cite the
  four new PROPs alongside their PROP-105 siblings.
- Gate item (2) (lines 252-273) — the REQ-105 gate — extended with a new clause (appended before the
  semicolon that previously closed the item) requiring the adversary to confirm: REQ-114's monitor operates
  genuinely alongside (never replacing) REQ-105's; a single large default is correctly captured
  dollar-weighted (PROP-114a); the kill-switch threshold rule is correct (PROP-114b); the REAL production
  REQ-106 issuance code (never a mock) is confirmed via direct control-flow read to call
  `evaluateOverallDefaultKillSwitch` before the per-lender lock, in addition to
  `evaluateColdStartKillSwitch` (PROP-114c); the two kill-switches are independent, additive gates
  (PROP-114d); and the `0.20` threshold is honestly flagged as an unvalidated placeholder, never presented
  as independently validated.

---

## FIND-503 (minor) — stale changelog header (stopped at iteration 2→3)

**Fix implemented, `specs/behavioral-spec.md`:**
- Header (lines 1-9): the `**revision**` line rewritten from "iteration 3, revised (spec review iteration-1
  findings FIND-001..008 resolved AND spec review iteration-2 findings FIND-101..107 resolved...)" to
  "iteration 6, revised (spec review iterations 1 through 5 — findings FIND-001..008, FIND-101..107,
  FIND-201..206, FIND-301..305, and FIND-401..403 — ALL resolved; this revision additionally resolves
  iteration-6's own FIND-501..503; see `reviews/spec/iteration-1/RESOLUTION-NOTES.md` through
  `reviews/spec/iteration-6/RESOLUTION-NOTES.md`, one file per iteration, for the full per-finding
  changelogs)".
- Three NEW Changelog tables inserted (the pre-existing "iteration 1 → iteration 2" and "iteration 2 →
  iteration 3" tables are left exactly as they were, per this project's own "old rules are overwritten, not
  duplicated, but a historical changelog is not a 'rule' and is preserved as a factual record" convention):
  - **"Changelog (iteration 3 → iteration 4)"** (lines 43-56): 6 rows, one per FIND-201..206, each
    resolution summarized from `reviews/spec/iteration-3/RESOLUTION-NOTES.md`.
  - **"Changelog (iteration 4 → iteration 5)"** (lines 58-69): 5 rows, one per FIND-301..305, each
    resolution summarized from `reviews/spec/iteration-4/RESOLUTION-NOTES.md`.
  - **"Changelog (iteration 5 → iteration 6)"** (lines 71-79): 3 rows, one per FIND-401..403, each
    resolution summarized from `reviews/spec/iteration-5/RESOLUTION-NOTES.md`.
  - **"Changelog (iteration 6 → current, this revision)"** (lines 81-91): 3 rows, one per FIND-501..503
    (this pass's own three findings), summarizing the fixes recorded in full above/below in this same
    document.
- Each new table follows the EXACT same format as the pre-existing two tables (`| Finding | Severity |
  Resolution |` header, one row per FIND-ID, severity taken from each iteration's own `RESOLUTION-NOTES.md`
  opening line) — no new format was invented.

**Fix implemented, `specs/verification-architecture.md`:** none required — FIND-503's own evidence
citation is scoped exclusively to `specs/behavioral-spec.md`'s header/changelog section (lines 1-41 in the
finding's own `evidence.lineRange`); `verification-architecture.md` has no per-iteration changelog table of
its own to correct (it carries only a single-line revision note, not a changelog), so it was left untouched
for this finding, matching the finding's own stated scope exactly.

---

## Post-fix integrity checks performed this session

- `grep -n "^### REQ-" specs/behavioral-spec.md` returns 14 requirement headers (the pre-existing 13 plus
  the new REQ-114) — no structural corruption, no duplicate REQ-IDs.
- Full-file grep for the literal string `deadlock` in both spec files: every remaining occurrence, post-fix,
  is part of the CORRECTED framing (stating deadlock is impossible / explaining why the prior claim was
  false) — zero occurrences of the removed false "textbook ... deadlock-avoidance technique" framing
  remain anywhere in either file.
- Grep confirms all 3 iteration-6 FIND-IDs are now cited in `behavioral-spec.md` (FIND-501: 8 occurrences,
  FIND-502: 7 occurrences, FIND-503: 3 occurrences) and that FIND-501/FIND-502 (the two findings whose
  evidence spanned both spec files) are also cited in `verification-architecture.md` (FIND-501: 5
  occurrences, FIND-502: 11 occurrences) — FIND-503 is correctly absent from `verification-architecture.md`
  per its own scoped evidence citation.
- `grep -o "PROP-114[a-z]" specs/verification-architecture.md | sort | uniq -c` confirms each of the four
  new PROP IDs (PROP-114a/b/c/d) appears across the expected set of locations (Purity Boundary Map is NOT
  where PROPs are cited by ID — only the Proof Obligations table row, the two Verification-tiers/Strategy
  narrative mentions, and the Gate item — 4-5 occurrences each) with no collision against any pre-existing
  PROP ID in this feature (checked against the full existing PROP-101 through PROP-113 range).
- A Python pipe-count check over every `| PROP-` row in the Proof Obligations table confirms all rows
  (including the four new ones) have exactly 7 `|` characters (6-column table) — no malformed table rows
  introduced.
- A Python pipe-count check over every Purity Boundary Map row (`| **...`) confirms all rows (including the
  two new REQ-114 rows) have exactly 5 `|` characters (4-column table) — no malformed table rows
  introduced.
- Did NOT touch `state.json`, any `reviews/` manifest/verdict file, and did not commit or push, per
  instructions.
