# Iteration 2

Reviewer: fresh-context vcsdd-adversary (strict-mode sprint contract review, negotiation iteration 2)
Contract: `contracts/sprint-1.md` (content revised since iteration 1; frontmatter `negotiationRound` field itself still reads `1` — see F-5 below)
Compared against: `specs/behavioral-spec.md`, `specs/verification-architecture.md` (now 29 proof obligations, PROP-023 added), `evidence/sprint-1-red-phase.log`, and iteration 1's `findings.md`/`verdict.json` in this same directory (read before being overwritten).

## Verification of iteration 1's findings

**F-1 (BLOCKING, PROP-021/live-E2E entirely absent from all criteria) — RESOLVED.**
A new `CRIT-006` (dimension: `verification_readiness`, weight 0.15) now exists. Its
`passThreshold` requires the PROP-021 live E2E plan from `verification-architecture.md`'s Done
section to actually run against the audited wallet `0xa3cdd4...` and pass all four conditions
verbatim: zero silent drops / zero fabricated extras with a count cross-check against the raw
live response; `sum(net_usdc)` equal to raw `sum(closedPnl - fee)` within `1e-6`; an immediately
repeated run appending zero additional lines (idempotency against live data); and no
dry/fake/mock/simulated language in the recorded output. This is stated as a THIS-sprint pass
condition (sprint 1's own `scope` line still covers the entire feature; there is no later sprint
this is deferred to), not a waiver or a promise to check later. Evidence: `contracts/sprint-1.md`
lines 33-37 (CRIT-006 in full).

**F-2 (major, REQ-D4 has no proof obligation anywhere) — RESOLVED.**
`verification-architecture.md` now has 29 rows (was 28) — `PROP-023` (Tier 0, required: yes,
"Added at contract-review negotiation round 1 (finding F-2)") covers REQ-D4 via a static grep
that the checkpoint/ledger paths are derived exclusively from the reconciler's own file location,
with zero matches for `.blockrun|.anicca|.openclaw|/Users/` anywhere in `reconcile.py`.
`CRIT-003`'s `passThreshold` now cites PROP-023 explicitly: "PROP-023 static check confirms
REQ-D4 path isolation (checkpoint and ledger paths derived exclusively from the reconciler's own
checkout location, with no literal reference to another instance's home directory)." Evidence:
`specs/verification-architecture.md` line 86 (PROP-023 row); `contracts/sprint-1.md` line 22
(CRIT-003 passThreshold).

**F-3 (minor, CRIT-005 dimension bundling under verification_readiness) — RESOLVED.**
`CRIT-005`'s `dimension` field now reads `implementation_correctness` (was
`verification_readiness` in iteration 1). `verification_readiness` is now exclusively represented
by the new `CRIT-006`. This is a cleaner separation than iteration 1 suggested as an optional fix:
`verification_readiness` now means specifically "is the live-E2E verification apparatus itself
trustworthy," while `implementation_correctness` carries ledger.mjs's functional correctness
(PROP-013/014a-e) alongside `reconcile.py`'s composition-root correctness (PROP-012/007/015-017/023).
Evidence: `contracts/sprint-1.md` line 29 (CRIT-005 `dimension:` field).

**F-4 (note, PROP-007 cited under both CRIT-002 and CRIT-003) — UNCHANGED, still non-blocking.**
Both criteria still cite PROP-007 (`contracts/sprint-1.md` lines 17 and 22). Iteration 1 explicitly
marked this "not required to fix before Phase 2b/3." No regression: the contract's own
"Cross-criterion note (contract-review F-4)" section (lines 149-154) now documents this
explicitly as deliberate, which is a strict improvement over iteration 1 (silent double-citation)
— this note itself resolves the residual ambiguity F-4 flagged. Downgrading to fully closed.

## Independent completeness check (fresh, not just re-verifying prior findings)

Cross-referencing every `passThreshold` string in `contracts/sprint-1.md` against
`verification-architecture.md`'s Required column: all 27 Tier-0-required PROP-IDs
(001, 002, 002b, 003, 004, 005, 006, 007, 008, 009, 010, 010b, 011, 012, 013, 014a-e, 015, 016,
017, 018, 019, 022, 023) plus the Tier-2-required PROP-021 — 28 of 28 required obligations — are
each cited in at least one criterion's `passThreshold`. PROP-020 (Tier-1, `required: no`) is
correctly absent from any `passThreshold`, matching its own "no" flag. No required proof
obligation is left uncovered by any criterion.

Weight sum: `0.2 + 0.2 + 0.15 + 0.15 + 0.15 + 0.15 = 1.0` — exact, no rounding slack.

Dimension coverage: `spec_fidelity` (CRIT-001), `edge_case_coverage` (CRIT-002),
`implementation_correctness` (CRIT-003, CRIT-005), `structural_integrity` (CRIT-004),
`verification_readiness` (CRIT-006) — all 5 grading-schema dimensions represented by at least one
criterion.

No criterion's `passThreshold` is weaker than its corresponding spec requirement(s): CRIT-001's
tied-timestamp inclusive-boundary language matches REQ-B2/B8's `>=` (not `>`) requirement
verbatim; CRIT-002 explicitly requires the PROP-010b two-call integration test's
`since_time_ms=500` re-query assertion (not a weaker "eventually recovers" claim); CRIT-003's
"byte-exact" REQ-C1 payload-key language and "not the first" checkpoint-advance language both
match spec wording exactly; CRIT-004's `reconcile` line-number-ordering language matches REQ-E3
exactly; CRIT-005 requires the pre-existing `ledger.test.js`'s 9 tests to "remain green
unmodified" (matches REQ-E2/non-regression exactly, not merely "still exist"); CRIT-006's four
sub-conditions are verbatim from verification-architecture.md's Done section.

## F-5 — minor — target: process/structural hygiene (not a criteria-content defect) — contract frontmatter `negotiationRound` still reads `1` despite the content having visibly been revised to address iteration 1's F-1/F-2/F-3

**What**: `contracts/sprint-1.md`'s frontmatter (line 5) still declares `negotiationRound: 1`, and
`status: draft` (line 6) is unchanged, even though the body content demonstrably reflects a
revision made in response to a prior review round (CRIT-006 is new; PROP-023 is dated "Added at
contract-review negotiation round 1 (finding F-2)" inside `verification-architecture.md` itself,
implying this contract edit happened AFTER that negotiation round concluded). This is not a
criteria-quality defect — every substantive finding from iteration 1 is genuinely resolved on
disk — but the artifact's own round-tracking metadata does not reflect that a revision cycle
occurred, which could cause the state library or a future auditor to misread how many negotiation
rounds this contract has actually been through.

**Evidence**: `contracts/sprint-1.md` lines 5-6 (`negotiationRound: 1`, `status: draft`);
`specs/verification-architecture.md` line 86 ("Added at contract-review negotiation round 1
(finding F-2)" — internal evidence that at least one revision cycle post-dates the original
draft).

**Required fix**: None required before Phase 2b — this is metadata hygiene, not a verifiability
gap. Recommend bumping `negotiationRound` to `2` and `status` to `negotiated` (or equivalent) the
next time this file is touched, so the round-tracking metadata matches the actual revision
history.

---

## Summary (iteration 2)

| ID | Severity | Status |
|---|---|---|
| F-1 | was BLOCKING | RESOLVED — CRIT-006 added, live E2E is a this-sprint pass condition |
| F-2 | was major | RESOLVED — PROP-023 added to verification-architecture.md, cited in CRIT-003 |
| F-3 | was minor | RESOLVED — CRIT-005 relabeled implementation_correctness |
| F-4 | was note | RESOLVED — contract now documents the dual-citation as deliberate |
| F-5 | minor (new) | OPEN, non-blocking — negotiationRound/status metadata not bumped |

BLOCKING count: 0 -> overallVerdict: PASS.

---

# Iteration 1 (prior record, preserved verbatim below)

# Sprint-1 Contract Review — hl-realized-pnl

Reviewer: fresh-context vcsdd-adversary (strict-mode sprint contract review)
Contract: `contracts/sprint-1.md`
Compared against: `specs/behavioral-spec.md`, `specs/verification-architecture.md`, `evidence/sprint-1-red-phase.log`

## F-1 — BLOCKING — target: whole criteria set (spec_fidelity / verification_readiness) — PROP-021 (Tier-2 live E2E money-correctness capstone) is entirely absent from all 5 criteria

**What**: `verification-architecture.md` defines 28 proof obligations and is explicit that "1 Tier-2 live capstone required for Done (strict mode does not waive the Tier-2 obligation)" (line 87-88), and again: "Tier 2 (PROP-021) = the only way to actually prove the fill-based pipeline computes the CORRECT real-world number, using real settled fills instead of fixtures. Required for Done in strict mode (unlike a typical Tier-2 'nice to have'...)" (lines 99-103). PROP-021 is mapped to REQ-A2, REQ-B*, REQ-C1 — i.e. it is the only proof obligation that verifies the reconciler actually derives realized P&L from a live Hyperliquid `userFills` call end-to-end, rather than from a fixture that merely *mimics* the live shape.

None of CRIT-001 through CRIT-005's `passThreshold` fields mention PROP-021, `user_fills_by_time`, live data, or any E2E/integration run against the real Hyperliquid API. Every passThreshold in the contract is satisfied by `test_fills.py`, `test_reconcile.py` (fixture/injected-fake based), and `ledger.test.mjs` alone. A sprint that runs ONLY these fixture suites — all green — would satisfy every criterion in this contract, `overallVerdict: PASS`, while REQ-A2 (the requirement that realized P&L is "derived EXCLUSIVELY from Hyperliquid's own `userFills` fill records... via a live call to the Hyperliquid Info API") is never once exercised against the real API in this sprint.

This is precisely the class of defect the feature exists to fix: `behavioral-spec.md` section 2 documents that the OLD code was ~2 orders of magnitude wrong (-$0.0006 vs real -0.123734) despite presumably having internally-consistent logic against its own (wrong) data source. A fixture that *asserts* the live API returns numeric-string `closedPnl`/`fee` and integer `tid` (PROP-003's fixture, copied from `evidence/audit-userfills-summary.md`) proves the code handles that shape correctly IF that shape is what the live API actually returns on every call — but nothing in this contract requires that assumption to ever be checked against a live response. `NFR-1` (pagination) is also explicitly "discovered... during Phase 5 hardening's live E2E," meaning even that risk is only closed by PROP-021, which this contract never invokes.

This also reads as a direct violation of this repo's own workflow rule (`.claude/rules/dev-workflow.md`): "`vcsdd-adversary`（実装レビュー）| fresh adversary + agent 自己完結 E2E green（maestro E2E or 実ブラウザ/実行検証、fresh evidence）| blocking 0 件 + E2E green" — the implementation-review gate this contract feeds is required to include fresh E2E evidence, not fixture tests alone.

**Evidence**: `contracts/sprint-1.md` lines 12/17/22/27/32 (all 5 `passThreshold` strings, none mention PROP-021/live/E2E/`user_fills_by_time`); `specs/verification-architecture.md` lines 85-103, 116-153 (Done section = PROP-021 plan, explicitly gating strict-mode Done); `.claude/rules/dev-workflow.md` (adversary gate requires E2E green).

**Required fix**: Add a criterion (or extend an existing one, e.g. CRIT-002 or a new CRIT-006) whose `passThreshold` requires PROP-021's live E2E plan (Done section in verification-architecture.md) to run successfully against the audited wallet `0xa3cdd4...`, asserting (a) zero silent drops / zero fabricated extras, (b) the summed `net_usdc` matches the raw `(closedPnl - fee)` sum within tolerance, (c) a second call appends zero additional lines, (d) no "dry/fake/mock/simulated" language appears in the recorded output. Alternatively, if PROP-021 is deliberately deferred to a later, explicitly-planned sprint or to Phase 5 hardening as a SEPARATE gate that this sprint's Done does NOT depend on, the contract must say so explicitly (with a dated rationale) rather than silently omitting it — as written, `state.json` shows `sprintCount: 1` and the contract's own `scope` line covers the ENTIRE feature (all new/modified files in verification-architecture.md's file table), so there is no visible later sprint that would pick this up.

---

## F-2 — major — target: structural_integrity / (no criterion) — REQ-D4 (per-instance ledger/checkpoint isolation) has no proof obligation anywhere in verification-architecture.md, so no contract criterion can cover it

**What**: `behavioral-spec.md` REQ-D4 requires that a line recorded by this feature "SHALL NEVER cause a write to, or be influenced by the contents of, any OTHER instance's `earn-ledger.jsonl` or checkpoint file." Scanning the full PROP-001..022 "Covers" column in `verification-architecture.md`, no PROP-ID cites REQ-D4 (PROP-016 covers REQ-D2's identity/key-path reuse, which is adjacent but not the same claim — REQ-D2 is about not reimplementing key resolution, REQ-D4 is about path isolation). Since the contract's criteria are built by referencing PROP-IDs, and no PROP-ID exists for REQ-D4, this sprint has no verifiable pass condition proving cross-instance isolation. Given this feature explicitly touches file paths (`skills/earn/hl-trade/.last-fill-ts`, `skills/earn/state/earn-ledger.jsonl`) and the project's own memory record (`feedback_earn_identity_resolve_per_instance_gate_on_anicca_home.md`) flags exactly this class of bug (shared identity/path leakage across instances) as a recurring, real defect class in this codebase, this gap is more than cosmetic.

**Evidence**: `specs/behavioral-spec.md` lines 247-252 (REQ-D4); `specs/verification-architecture.md` lines 56-85 (PROP table, no REQ-D4 entry).

**Required fix**: Either verification-architecture.md needs a proof obligation for REQ-D4 (e.g. a static grep confirming both paths are constructed relative to a caller-supplied/`ANICCA_HOME`-scoped instance root, never a hardcoded absolute path or another instance's directory) and the contract needs a criterion citing it, or the contract must explicitly note this is covered by the existing PROP-016/identity-reuse check plus code inspection at Phase 3 and accept the residual risk explicitly.

---

## F-3 — minor — target: verification_readiness (CRIT-005) — ledger.mjs functional correctness (REQ-C2/REQ-C3) is graded under the "verification_readiness" dimension rather than spec_fidelity/implementation_correctness

**What**: CRIT-005's passThreshold is really two different claims bundled under one dimension label: (1) the *functional correctness* of `deriveLine`'s passthrough and `isProfitable`'s new disjunct (PROP-013, PROP-014a-e — this is spec_fidelity/implementation_correctness territory, since it's "does the code do what REQ-C2/C3 say"), and (2) the *process* claim that this is proven via a NEW test file rather than edits to the existing one (this IS legitimately verification_readiness — proving the verification apparatus itself wasn't weakened). Bundling both under one dimension means a reviewer scoring "verification_readiness" is implicitly also scoring ledger.mjs's core correctness, and there is no separate criterion anywhere that grades ledger.mjs's correctness under spec_fidelity or implementation_correctness. This doesn't break falsifiability (the passThreshold is still concrete and checkable) but it does mean the grading-schema's 5-dimension score for spec_fidelity/implementation_correctness is silently incomplete for the ledger.mjs slice of this feature's scope.

**Evidence**: `contracts/sprint-1.md` lines 28-32 (CRIT-005, dimension: verification_readiness, bundles both claims).

**Required fix**: Non-blocking; consider re-labeling CRIT-005 to implementation_correctness (or splitting into two criteria) in a future negotiation round if dimension-purity matters for downstream scoring aggregation. Not required to fix before Phase 2b/3.

---

## F-4 — note — target: implementation_correctness (CRIT-003) / edge_case_coverage (CRIT-002) — PROP-007 is claimed as a pass condition under two different criteria

**What**: PROP-007 (checkpoint advances to the LAST recorded fill's time, atomic write) is listed in CRIT-002's passThreshold ("...PROP-004/005/006/007/008/009/010/010b/011/022...") AND explicitly called out again in CRIT-003's passThreshold ("PROP-012... and PROP-007 (checkpoint == last recorded fill's time, not first) both pass"). This isn't contradictory (the same test can legitimately support two dimensions — checkpoint-advance-correctness is both an edge-case concern (E2/E4) and an implementation-correctness concern (composition-root ordering)), but it means the same single test result is double-counted toward two separately-weighted dimension scores. This is a minor scoring-hygiene note, not a fidelity gap.

**Evidence**: `contracts/sprint-1.md` line 17 (CRIT-002) and line 22 (CRIT-003), both citing PROP-007.

**Required fix**: None required; optional clarification in a future negotiation round on whether shared PROP-ID references across criteria are intentional design or an oversight.

---

## Summary

| ID | Severity | Target |
|---|---|---|
| F-1 | BLOCKING | spec_fidelity / verification_readiness — PROP-021 (Tier-2 live E2E) missing from all criteria |
| F-2 | major | structural_integrity — REQ-D4 has no proof obligation anywhere, so no contract coverage |
| F-3 | minor | verification_readiness (CRIT-005) — dimension bundling |
| F-4 | note | edge_case_coverage / implementation_correctness — PROP-007 cited under two criteria |

BLOCKING count: 1 -> overallVerdict: FAIL.
