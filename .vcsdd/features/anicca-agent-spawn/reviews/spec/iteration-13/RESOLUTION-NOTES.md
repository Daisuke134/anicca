# Resolution Notes — spec review iteration-13 (FIND-1201, FIND-1202)

**Feature**: anicca-agent-spawn · **Result**: both findings resolved; `behavioral-spec.md` and
`verification-architecture.md` bumped to **revision: iteration 13**.

---

## FIND-1201 (critical) — REQ-103's colony-spawn lock critical section unified to ONE scope

**Problem**: REQ-103 stated three mutually inconsistent lock critical-section scopes in the same
requirement — EARS clause said "and beyond" (open-ended), its statePath prose said "REQ-101 through
REQ-305", and its *binding* Acceptance Criteria said only "REQ-201 through REQ-205, and the decision to
proceed into REQ-3xx" — the narrowest reading textually excluding REQ-206's ledger-row assembly,
REQ-304's funding transfer, and REQ-305's append. That narrow reading would let the lock release before
funding/ledger-append completed, opening a staggered (non-simultaneous) double-spawn/double-funding
race between two evaluators.

**Resolution — canonical scope adopted**: the lock is held from **REQ-201's wallet generation THROUGH
REQ-305's ledger append actually completing** (the new citizen durably recorded in `citizens.json`).
REQ-101's registry read and REQ-102's decision run *outside* the lock (REQ-102's gate function is pure
and needs no mutual exclusion of its own — only acting on a `true` decision needs the lock).

### `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| Revision header (lines 4-32) | Bumped `iteration 12` → `iteration 13`; new lead paragraph describing the FIND-1201/FIND-1202 fixes, prior iteration-11 content preserved as a subordinate `AND spec review iteration-11 findings ... resolved` clause. |
| New `## Changelog (iteration 12 spec review → iteration 13)` section (lines 249-260, immediately before `## Scope of this increment (read first)` at line 262) | Added, following the exact same pattern as every prior iteration's changelog table (FIND-1201/FIND-1202 rows). |
| REQ-103 EARS clause (lines 679-689) | Changed "proceeds to REQ-201's identity generation **and beyond**" (open-ended) to "proceeds past REQ-201's identity generation, and SHALL hold the `\"colony-spawn\"` lock continuously **through REQ-305's ledger append actually completing**" — now states the lock is the requirement's ENTIRE critical section, cross-referencing the (also-corrected) statePath prose and Acceptance Criteria as stating the IDENTICAL scope. |
| REQ-103 statePath prose (lines 700-733, specifically 716-723) | Replaced "the critical section this lock protects IS \"read the durable `citizens.json` + decide + possibly append to it\" (**REQ-101 through REQ-305**)" with "the lock's critical section is **REQ-201's wallet generation THROUGH REQ-305's ledger append actually completing**" — and added an explicit clarifying clause that REQ-101's read and REQ-102's decision run *outside* the lock (REQ-102's gate function is pure, per its own existing edge case). |
| REQ-103 Acceptance Criteria (first bullet, line 758) | Replaced "The colony-spawn critical section (**REQ-201 through REQ-205, and the decision to proceed into REQ-3xx**)" with "The colony-spawn critical section (**REQ-201's wallet generation THROUGH REQ-305's ledger append ACTUALLY COMPLETING** — the new citizen durably recorded in `citizens.json`)" — explicitly stating this is never released earlier, e.g. not merely through REQ-205 or "the decision to proceed into REQ-3xx". |

### `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Revision header (lines 5-32) | Bumped `iteration 12` → `iteration 13`; same restructuring pattern as the behavioral-spec header. |
| Purity Boundary Map | No change needed for this finding (lock.mjs row already correctly describes reuse; the scope correction lives in behavioral-spec.md's REQ-103 text, cross-referenced here). |
| Proof Obligations table — new row **PROP-103e** (line 276) | Added, directly after PROP-103d and before PROP-104a: a staggered-timing fixture — a first evaluator's REQ-304 funding call is deliberately delayed; a second evaluator's repeated lock-acquire attempts throughout that entire delay must ALL fail (`reason:"lock_held"`, zero REQ-201 wallet-generation calls), succeeding only after the first evaluator's REQ-305 append lands. Tier 2, required. |
| Tier 1/Tier 2 narrative lists (lines 196, 217) | Updated to cite PROP-103e alongside PROP-103a for REQ-103's concurrent-attempt coverage. |
| Gate item (2) (line 600 onward) | Extended to additionally require PROP-103e's staggered-race proof "IN ADDITION to PROP-103a's simultaneous-race fixture, since a simultaneous race alone cannot prove the lock is not released early somewhere between REQ-206 and REQ-305." |

---

## FIND-1202 (major) — expose per-citizen surplus via a new function

**Problem**: REQ-304's per-citizen ceiling check (added to resolve FIND-1102) requires "each citizen's
own certified surplus-above-reserve contribution," but `computeColonySurplusUsd({citizens,
perCitizenReserveUsd})` only returns an aggregate SUM — no function anywhere exposed the per-citizen
value REQ-304's own Acceptance Criteria and PROP-304f's companion fixture needed to bind to.

**Resolution**: new pure sibling function, same file as `computeColonySurplusUsd`:

```
computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd})
  → Array<{citizenId: string, surplusUsd: number}>
```

`computeColonySurplusUsd` is now specified to be implemented by CALLING this function and summing its
`surplusUsd` values (never an independently-written second reduce) — guaranteeing the aggregate and the
per-citizen breakdown can never silently diverge, mirroring REQ-206's own "two independently-derived
numbers must be identical by construction" discipline already established elsewhere in this spec.

### `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| Revision header + new iteration-13 changelog | See FIND-1201 table above — same edit covers both findings' summary text. |
| REQ-101 body, new paragraph (lines 447-461, inserted between the `perCitizenReserveUsd` default sentence and the "Dual-chain balance handling" paragraph) | New **"Per-citizen surplus, exposed individually (new, resolves FIND-1202...)"** paragraph specifying `computePerCitizenSurplusUsd`'s exact signature, its by-construction relationship to `computeColonySurplusUsd`, and that REQ-304's ceiling check reads this function's output directly rather than re-deriving the arithmetic. |
| REQ-101 Acceptance Criteria, new bullet (line 549, inserted immediately after the first `computeColonySurplusUsd` bullet) | New bullet: `computePerCitizenSurplusUsd` returns one `{citizenId, surplusUsd}` record per citizen; `computeColonySurplusUsd`'s own aggregate is confirmed, by construction, to equal the sum of every returned `surplusUsd`. |
| REQ-304 Acceptance Criteria, FIND-1102 resolution bullet (line 1909 onward) | Updated to cite `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd})` BY NAME as the value each citizen's transfer is checked against — "never an independently re-derived or re-summed aggregate value." |

### `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Purity Boundary Map row for `computeColonySurplusUsd` (line 119) | Extended to also describe the new sibling `computePerCitizenSurplusUsd` and the by-construction (calls-and-sums) consistency relationship, citing PROP-101i. |
| Proof Obligations table — new row **PROP-101i** (line 266) | Added, directly after PROP-101h and before PROP-102a: Tier 0/1 — structural read confirming `computeColonySurplusUsd` calls `computePerCitizenSurplusUsd` and sums it, plus a unit-test fixture proving per-citizen correctness AND aggregate-sum consistency on the identical fixture. |
| Tier 1 narrative list (line 196) | Updated to cite PROP-101i alongside PROP-101f/PROP-101h. |
| Gate section — new item **(1e)** (line 592, inserted between (1d) and (2)) | Requires the adversary to confirm `computePerCitizenSurplusUsd`'s per-citizen correctness and its by-construction consistency with `computeColonySurplusUsd`, noting this is "the exact function REQ-304's per-citizen ceiling check (item (7)) binds to by name." |
| Proof Obligations table — PROP-304f row (line 331, companion-fixture clause) | Updated the companion-fixture clause to read "from REQ-101's `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd})` output for that citizen's `citizenId`" instead of an unnamed "own certified contribution." |
| Gate item (7) (line 694 onward) | Extended with an additional clause requiring confirmation that each individual transfer's ceiling check reads its citizen's value from `computePerCitizenSurplusUsd` output by name, citing PROP-101i. |
| Tier 1/Tier 2 narrative lists mentioning PROP-304f (line 426, line 480) | Both updated with a parenthetical noting the per-citizen ceiling half now reads REQ-101's PROP-101i-proved `computePerCitizenSurplusUsd`. |

---

## Verification of internal consistency (post-edit)

- Grep-confirmed REQ-103's live requirement text (EARS/prose/Acceptance Criteria) no longer contains
  "and beyond" (open-ended) or the narrower "REQ-201 through REQ-205, and the decision to proceed"
  phrasing outside of the changelog's own historical description of the bug.
- `PROP-103e` and `PROP-101i` each appear exactly once as a table-row definition in
  `verification-architecture.md`'s Proof Obligations table (no ID collisions), plus narrative
  cross-references in the Tier lists, Gate section, and revision header.
- `computePerCitizenSurplusUsd` is referenced consistently (same signature) across both spec files:
  `behavioral-spec.md` (REQ-101 body + Acceptance Criteria + REQ-304 Acceptance Criteria + revision
  header/changelog) and `verification-architecture.md` (Purity Boundary Map + PROP-101i + PROP-304f +
  Gate items (1e)/(7) + revision header).
- No edits were made to `state.json`, review manifest/verdict files, or any file outside
  `specs/behavioral-spec.md` / `specs/verification-architecture.md` / this notes file. No commit/push
  was performed.
