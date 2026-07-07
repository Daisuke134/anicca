# Resolution Notes — Spec Review Iteration 5 (anicca-agent-lending)

Iteration 5 FAILed with 3 findings (2 critical, 1 major): FIND-401, FIND-402, FIND-403. This document
records exactly what changed, per finding, in `specs/behavioral-spec.md` and
`specs/verification-architecture.md`, with the current line ranges of the edited sections. Line numbers
are as of this resolution pass; both spec files grew (behavioral-spec.md 1590 → 1762 lines,
verification-architecture.md 360 → 383 lines) as a direct result of these fixes, so any future citation of
these ranges should be re-verified fresh (the SAME "moving target" discipline REQ-113 already establishes
for the sibling `anicca-agent-spawn` spec applies to this document's own internal cross-references too).
`state.json`, the reviews manifest/verdict files, and git history were NOT touched, per instructions.

---

## FIND-401 (critical) — no cross-lender enforcement of at-most-one-outstanding-loan

**Grounding read performed first, as directed:** `~/anicca/skills/economy/gig/lib/lock.mjs`'s real,
current API — `withGigLock(statePath, lockKey, fn, {staleMs, heartbeatMs})` acquires exactly ONE lock key
per call (POSIX `wx` exclusive create, atomic `fs.rename`-based stale-reclaim, heartbeat-refreshed mtime),
runs `fn()`, and releases in a `finally` block. There is no built-in multi-key acquisition primitive — a
caller needing two keys held simultaneously for one critical section must NEST two `withGigLock` calls
itself. This grounded the fix: the existing per-lender `` `loan_${lenderId}` `` lock cannot simply be
widened or replaced (it alone protects `nextLoanSequenceForLender`'s sequence-number collision-freedom,
PROP-106e — fragmenting it by borrower would reopen that guarantee), so a SECOND, borrower-scoped lock had
to be added and acquired ALONGSIDE it via nested `withGigLock` calls, in a fixed deterministic order to
avoid deadlock (the finding's own suggested fix, adopted verbatim: lexicographically-smaller key outer).

**Design decision made:** a single COMBINED lock key derived from both IDs (e.g. sorted-and-joined) was
considered and explicitly REJECTED (documented in the new spec text, not just this note): it would
fragment the per-lender sequence-number critical section by borrower — two DIFFERENT borrowers of the
SAME lender would then hold DIFFERENT combined keys and could proceed concurrently against STALE
`loanRows` snapshots, reopening `nextLoanSequenceForLender`'s own `loan_id`-collision-freedom guarantee.
The per-lender lock must remain a single, whole-lender critical section, so TWO separate locks (nested,
in a deterministic total order) was the correct choice, not a merged one.

**Fix implemented, `specs/behavioral-spec.md`:**
- REQ-106 top EARS paragraph, lines 742-753: broadened the trigger to cover races against the SAME
  borrower (not only the SAME lender), and introduced the second lock key,
  `` `loan_borrower_${borrowerId}` ``, alongside the unchanged `` `loan_${lenderId}` `` key.
- REQ-106 body, two NEW subsections inserted after the `LOANS_LEDGER_PATH` paragraph and before the
  `loan_id` generation paragraph:
  - "Cross-lender same-borrower exclusion" (lines 767-791): states the hazard precisely (a
    `"provisioning"`/`"disbursement_uncertain"` row is not one of REQ-102 condition (c)'s excluded
    statuses, so the window is unbounded, not millisecond-scale), specifies the new borrower lock is
    acquired IN ADDITION to the lender lock, explicitly rejects the single-combined-key alternative and
    why, and requires a FRESH re-read + re-check of REQ-102's conditions (a)-(d) while BOTH locks are
    held, before REQ-101's own recheck/REQ-104/105 sizing/`n` computation/disbursement.
  - "Lock-acquisition order (deadlock avoidance)" (lines 793-815): specifies the deterministic total
    lock-ordering rule (lexicographically-smaller key string acquired outer, the other inner), introduces
    the new pure helper `resolveLoanLockAcquisitionOrder(lenderId, borrowerId) → [outerKey, innerKey]`
    (new PROP-106m), and documents an honest, low-probability, assumed limitation of the naming scheme
    (no citizen ID is assumed to begin with the literal substring `borrower_`).
- REQ-106 "Lock-key disambiguation" paragraph, lines 1004-1015: updated to state the two-phase
  provisional/follow-up append is now appended under BOTH the per-lender AND the new per-borrower lock
  together (still never REQ-108/109's own per-loan lock).
- REQ-106 Edge Cases, lines 1017-1041: the existing "two different lenders proceed without contention"
  bullet qualified to the two-DIFFERENT-borrowers case only, with a "Corrected this revision" pointer to
  the new same-borrower behavior; a NEW bullet added directly describing the L1/L2-vs-same-borrower-B race
  and its correct resolution (exactly one succeeds, the other observes `reason:"outstanding_loan"` on a
  fresh re-check); a further new bullet documents the self-loan-rejected-first ordering (shared with
  FIND-402, see below).
- REQ-106 Acceptance Criteria, lines 1098-1132: added a bullet for the lock-acquisition-order unit test
  (PROP-106m); rewrote the "critical section wrapped by lock" bullet to describe the nested,
  deterministically-ordered dual-lock wrapping and the fresh-read-then-recheck sequence; qualified the
  existing "two different lenders" collision-freedom bullet to the two-different-borrowers case; added a
  new bullet for the same-borrower race fixture (PROP-106n).
- Purity boundary analysis overview table (lines 230): the lock-discipline row updated from "TWO distinct
  new lock keys" to "THREE distinct new lock keys," naming the new per-borrower key and its purpose.
- Non-functional requirements (money-safety), line 259: new clause — "a borrower can never hold two
  simultaneously-open loans from two DIFFERENT lenders (REQ-106's new per-borrower
  `loan_borrower_${borrowerId}` lock, resolves FIND-401)."

**Fix implemented, `specs/verification-architecture.md`:**
- Purity Boundary Map, new row (line 25): `resolveLoanLockAcquisitionOrder(lenderId, borrowerId) →
  [outerKey, innerKey]` — pure, zero I/O, the deterministic total-lock-ordering helper.
- Effectful Shell row for `lock.mjs` (line 34): rewritten from "TWO distinct new lock keys" to "THREE
  distinct new lock keys," describing the new per-borrower key, the nested-acquisition-in-deterministic-
  order discipline, and that the two-phase append is now appended under both REQ-106 keys together.
- Proof Obligations table: PROP-106e (line 127) updated to state its collision-freedom claim now
  explicitly requires two DIFFERENT borrowers (not just two different lenders), pointing at the new
  PROP-106n for the same-borrower case; two NEW rows added after PROP-106l — **PROP-106m** (line 134, Tier
  1 — the lock-order helper's own deterministic unit test) and **PROP-106n** (line 135, Tier 2 — the core
  required fixture: two different lenders concurrently target the same borrower, exactly one succeeds).
- Verification tiers (Tier 1/Tier 2 narrative lists), lines 186 and 198: both updated to cite the new
  PROP-106m (Tier 1) and PROP-106n (Tier 2).
- Gate item (3), lines 279-296: new clause requiring the adversary to confirm, via control-flow read of
  the REAL issuance code (never a mocked assertion), that every issuance attempt acquires BOTH locks in
  the deterministic order `resolveLoanLockAcquisitionOrder` returns, and that the cross-lender
  same-borrower race resolves to exactly one success under a deliberately-induced concurrent test
  (PROP-106m/PROP-106n).

---

## FIND-402 (critical) — self-loan exploit: `lender_id === borrower_id` not forbidden

**Fix implemented, `specs/behavioral-spec.md`:**
- REQ-102 EARS text, lines 391-426: added a FOURTH eligibility condition, (d) `lenderId !== borrowerId`,
  stated as evaluated FIRST — before conditions (a)/(b)/(c) and before REQ-101's own lender-availability
  computation ever runs for the candidate pair. The rationale paragraph states the exploit precisely
  (a self-funded citizen could self-loan-and-repay at negligible real cost — REQ-104's smallest loan is
  `$0.02` + `$0.002` interest — to fabricate `successfulOnTimeRepayments`, defeating REQ-105's cold-start
  risk-mitigation rationale and corrupting `computeColdStartRepaymentRate`'s own monitoring signal), and
  notes that because self-loans are rejected structurally at issuance, no self-dealt row can ever exist in
  `loans.jsonl` — `computeColdStartRepaymentRate` needs no separate self-loan-filtering logic of its own.
- REQ-102 Edge Cases, lines 428-432: new bullet stating a `lenderId === borrowerId` candidate is rejected
  under condition (d) regardless of balance/surplus/repayment history.
- REQ-102 Acceptance Criteria, lines 445-462: `isBorrowerEligible`'s own signature updated to add a NEW
  `lenderId` parameter (required because condition (d) is a fact about the specific candidate PAIR, not
  the borrower alone) and a new `reason:"self_loan"` enum value, checked first; existing fixture bullets
  updated to include `lenderId !== borrowerId` where relevant; a NEW bullet added for the required fixture
  — a self-loan request rejected BEFORE any lock is acquired or any surplus check runs, asserted even when
  the same citizen would otherwise pass every other condition (new PROP-102e).
- Purity boundary analysis overview table, line 219: the borrower-eligibility-check row updated to name
  the self-loan exclusion as the FIRST-checked condition.
- REQ-105 body (Monitoring plan, cold-start-loan definition), lines 605-610: added a cross-reference
  stating REQ-102's condition (d) structurally forbids `lenderId === borrowerId` at issuance, so
  `computeColdStartRepaymentRate`'s own sample can never include a self-dealt loan — closing the loop the
  finding's own rationale raised, without adding redundant filtering logic to that function.
- REQ-106 EARS/Edge Cases/Acceptance Criteria (shared with FIND-401's edits, since the self-loan check and
  the dual-lock design are both part of the SAME critical-section ordering): the self-loan check is
  explicitly sequenced as step 0, before either lock (`loan_${lenderId}` or the new
  `loan_borrower_${borrowerId}`) is ever acquired — see lines 1037-1041 (Edge Cases) and line 1099-1100
  (Acceptance Criteria).
- Non-functional requirements (money-safety), line 260: new clause — "a citizen can never be both the
  lender AND the borrower of the SAME loan (REQ-102's condition (d), resolves FIND-402)."

**Fix implemented, `specs/verification-architecture.md`:**
- Purity Boundary Map, `isBorrowerEligible` row (line 17): updated signature to add `lenderId`, and
  described the FOUR-condition gate with the self-loan exclusion checked first.
- Proof Obligations table, new row (line 110): **PROP-102e** — the required fixture (a candidate with
  `lenderId === borrowerId` that would otherwise pass every other condition is rejected with
  `reason:"self_loan"`, checked before (a)/(b)/(c)).
- Verification tiers (Tier 1 narrative list), line 175: updated from "REQ-102's three-condition gate...
  (PROP-102a-d)" to "REQ-102's FOUR-condition gate (including the NEW self-loan exclusion... PROP-102e)...
  (PROP-102a-e)."
- Gate item (1), lines 224-232: new clause requiring the adversary to confirm REQ-102's self-loan
  exclusion is checked first, before conditions (a)-(c) and before REQ-101's own availability computation,
  refusing at zero cost before any lock is acquired (PROP-102e).

---

## FIND-403 (major) — `issued_ms` undefined relative to two-phase row timestamps

**Decision made, per the finding's own explicit two-option framing:** `issued_ms` is drawn EXCLUSIVELY
from the FOLLOW-UP `"active"` row's own append-time timestamp — NEVER the provisional row's own
`provisioned_ms`. Rationale (matching the finding's own suggested reasoning): the repayment window should
count from when the borrower actually RECEIVED usable funds (confirmed disbursement), not from when
issuance was merely attempted, since a slow-to-reconcile provisional row must not silently eat into the
borrower's real repayment window. The residual asymmetry the finding itself flagged (a reconciled loan
gets a FRESHER window than a normal-path loan of the same real on-chain disbursement date, since
reconciliation can be delayed) is explicitly acknowledged as a documented, low-probability, NOT-further-
resolved limitation this increment — backdating `issued_ms` to the on-chain block's own timestamp was
considered and rejected as an unrequested, out-of-scope third mechanism (the finding asked for a choice
between the two ROW timestamps, not a new on-chain-timestamp lookup).

**Fix implemented, `specs/behavioral-spec.md`:**
- REQ-106 body, new paragraph "`issued_ms`, precisely defined" (lines 855-881), inserted immediately after
  the two-phase append's step 3 (the follow-up-row description) and before the `nextLoanSequenceForLender`
  treatment paragraph: states `issued_ms` is a field on the `"active"` row ONLY, set at that row's own
  append time; states `due_ms = issued_ms + LOAN_REPAYMENT_WINDOW_DAYS * 86400000` is always computed from
  that value; states a `"provisioning"`/`"disbursement_failed"`/`"disbursement_uncertain"` row carries NO
  `issued_ms` field; and documents the acknowledged reconciled-path trade-off honestly, explicitly
  declining to add an `eth_getBlockByNumber` lookup to close it this increment.
- REQ-105 body, lines 601-610: the first `issued_ms ascending` mention (in `computeColdStartRepaymentRate`'s
  own description) updated with a parenthetical pointing at REQ-106's precise definition.
- REQ-106 Acceptance Criteria, lines 1141-1149: new bullet for the required fixture — a loan whose
  provisional row is appended at `T1` and whose active/follow-up row is appended at a later `T2` asserts
  `issued_ms === T2` (never `T1`) and `due_ms` computed from that same, correct value (new PROP-106o).
- REQ-109 EARS text, lines 1581-1584: the `due_ms (issued_ms + LOAN_REPAYMENT_WINDOW_DAYS * 86400000)`
  parenthetical extended to state explicitly that `issued_ms` is the `"active"` row's own append-time
  timestamp, never the provisional row's `provisioned_ms`, pointing at REQ-106's definition.
- Non-functional requirements (money-safety), lines 261-262: new clause — "a loan's own default-clock
  (`issued_ms`/`due_ms`) is drawn EXCLUSIVELY from the confirmed-disbursement `"active"` row, never the
  pre-transfer provisional row (REQ-106, resolves FIND-403)."

**Fix implemented, `specs/verification-architecture.md`:**
- Proof Obligations table, new row (line 136): **PROP-106o** — `issued_ms` drawn exclusively from the
  `"active"` row's own append-time timestamp, `due_ms` computed from that same value; test method reuses
  the PROP-106g/h/k reconciliation-delay fixture shape (provisional row at `T1`, active row at later `T2`).
- Verification tiers (Tier 2 narrative list), line 199: updated to cite the new PROP-106o.
- Gate item (3), lines 292-296: new clause requiring the adversary to confirm, by a direct read of the
  two-phase append code, that `issued_ms` is set exclusively on the `"active"` row, never equal to
  `provisioned_ms`, including in a reconciled-path fixture where the active row is appended materially
  later than the provisional row (PROP-106o).

---

## Cross-cutting consistency checks performed after all 3 edits

- Confirmed no leftover "TWO distinct new lock keys" framing remains anywhere in either spec file after
  the FIND-401 fix (grepped both files — every occurrence now reads "THREE distinct new lock keys").
- Confirmed PROP-106e's own claim ("two DIFFERENT lenders... produce DISTINCT `loan_id`s... both succeed")
  no longer contradicts the new borrower-lock behavior: its description and test method were both
  qualified to the two-DIFFERENT-borrowers case, with an explicit pointer to the new PROP-106n for the
  same-borrower case (which correctly asserts only ONE succeeds, not both).
- Confirmed the "**a cold-start loan is NOT equivalent to...**" sentence in REQ-105 (a colon-continuation
  of the preceding "this is the exact and ONLY definition:" sentence) was NOT broken by the inserted
  self-loan cross-reference — re-read after editing to confirm the colon-continuation still reads
  grammatically, with the new sentence inserted immediately after it rather than splitting it.
- Confirmed every new PROP ID introduced (PROP-102e, PROP-106m, PROP-106n, PROP-106o) follows the existing
  PROP-XXX-lettersuffix convention and does not collide with any pre-existing PROP ID in either spec file
  (checked via `grep -o "^| PROP-[0-9a-z]*" verification-architecture.md | sort | uniq -d` — zero
  duplicates).
- Confirmed both spec files still contain all 13 REQ-XXX section headers with no structural corruption
  (`grep -n "^### REQ-"` returns the same 13 requirements as before this pass).
- Confirmed double-backtick code-span delimiters remain balanced in both files after all edits (56 in
  behavioral-spec.md, 28 in verification-architecture.md — both even counts).
- Did NOT touch `state.json`, any `reviews/` manifest/verdict file, and did not commit or push, per
  instructions.
