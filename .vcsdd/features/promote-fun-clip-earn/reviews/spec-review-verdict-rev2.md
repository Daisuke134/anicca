# VCSDD Phase 1c — Adversary Spec Review Verdict (RE-REVIEW of REV 2)

- Feature: `promote-fun-clip-earn`
- Spec reviewed: `.vcsdd/features/promote-fun-clip-earn/specs/spec.md` (REV 2)
- Mode: lean | Reviewer: fresh-context adversary (disk-only, zero builder context)
- **OVERALL VERDICT: FAIL** (5 / 5 dimensions FAIL — 1 critical, 6 major, 2 minor)

> Scope of this re-review: (A) did REV 2 close the 9 prior MUST-FIX? (B) what NEW flaws did the
> REV 2 rewrite introduce? The prior 9 are LARGELY closed at the prose level (see "Prior-finding
> ledger" below), but the chain-generalization REWRITE introduces a critical second-order break and
> several major gaps that make the money-only DONE gate **unable to fire as specified**.

---

## Prior-finding ledger (factual closure check — NOT a positive summary)

| Prior | Closed? | Evidence in REV 2 / canonical |
|---|---|---|
| F1.1 (external field cited but absent) | YES (semantics) | Canonical `_shared/lib/ledger.mjs:43-48` DOES gate on `external===true`; REV 2 line 54-60 matches it. BUT path is miscited — see **FIND-203**. |
| F1.2 / F3.2 / F5.2 (money-free DONE / views=0 pass) | PARTIAL | DONE is now money-only (lines 10-12), views=0 explicitly non-pass + liveness (REQ-6 lines 87-92). Shadowban hole survives — **FIND-204**. |
| F1.3 (payout step unspecified) | YES | §Payout mechanics (lines 27-37) + REQ-7 (lines 93-95): off-chain balance → campaign-end credit → manual claim → Solana sig. |
| F2.2 (day-1 posting vs warmed-only `--live`) | YES (conditionally) | REQ-4 (lines 76-81) posts only to `ready` account else defers. Warm-state provenance undefined — **FIND-208**. |
| F2.1/F2.3/F2.5 (no-campaign / reject / dedup / 429) | YES | REQ-1a, REQ-5a, REQ-11. |
| F2.4 / F4.2 (state machine + re-auth + per-wake print) | YES | State table (lines 122-138), REQ-10, REQ-12. `decide` purity is genuinely testable — mirrors the pure `video/decide.py:23-43`. |
| F3.1 / F4.1 / F5.1 (EVM-only gate vs Solana) | PARTIAL | Solana adapter + `isProfitable` generalization specified (lines 45-60). The generalization is test-safe but the WRITE PATH is broken — **FIND-201**, **FIND-202**, **FIND-206**. |
| F3.3 / F5.4 (8–90s vs 15–45s) | YES | REQ-3 (lines 72-75) mandates a stricter dedicated `15≤dur≤45` gate over `verify_clip.sh:38`. |
| F5.3 (no-human only grep-asserted) | PARTIAL | REQ-9 adds a runtime watchdog (lines 102-108), but the mechanism/owner is undefined — **FIND-205**. |

---

## Dimension 1 — Spec Fidelity: **FAIL**

**FIND-201 (CRITICAL, requirement_mismatch). The DONE write-path contradicts the named lib: `deriveLine` silently DROPS `sig`/`confirmed`/`chain`, so a generalized `isProfitable` can never see them and DONE can never fire.**
REQ-8 (spec.md:96-101) says append `{chain:"solana", sig, confirmed:true, earn_usdc, cost_usdc, external:true, source}` "to the canonical ledger via `record.mjs`/`isProfitable`", and the verification architecture (spec.md:148-151) asserts "the ledger line satisfies `isProfitable` … no phantom `external`/`0x1` field." But `record.mjs` (`skills/earn/lib/record.mjs:16`) calls `deriveLine(input)`, and `deriveLine` (`skills/_shared/lib/ledger.mjs:11-28`) constructs a NEW object copying ONLY `{ts, wallet, source, task, earn_usdc, cost_usdc, net_usdc, wake}` plus conditionally `tx`/`status`/`external` (lines 25-27). `sig`, `confirmed`, and `chain` are NOT carried. Therefore even after `isProfitable` is generalized to check `line.sig && line.confirmed === true`, the PERSISTED line has no `sig` → `isProfitable` returns false → the only DONE path (`earned_usdc>0`) is unreachable. The spec mandates generalizing `isProfitable` (line 54) but is SILENT on the required parallel change to `deriveLine`. A builder coding REQ-8 literally as written cannot make DONE fire — or will bypass `record.mjs` entirely, which also bypasses the append-only contract and the `assertOwnIdentityOnly` malice-guard (`record.mjs:19`) that the spec never mentions.
Evidence: `skills/_shared/lib/ledger.mjs:14-28`; `skills/earn/lib/record.mjs:16,19`; spec.md:96-101,148-151.

**FIND-202 (MAJOR, requirement_mismatch). Two divergent "canonical" recorders are named; the proposed Solana line satisfies NEITHER, and the spec never says which is authoritative.**
The spec/manifest names BOTH `record.mjs`+`isProfitable` (JS; schema `tx`/`status`/`external`; `_shared/lib/ledger.mjs`) AND `video/record_earn.py` as "the honest record-earn the spec mirrors". These are incompatible schemas: `record_earn.py:11-19` requires `token=="USDC"`, `direction=="in"`, a non-empty `tx_hash`, and `verified is True`. REQ-8's proposed line has `sig` (not `tx_hash`), no `direction`/`token`/`verified` → `record_earn.is_real_usdc_inflow` → "rejected"; and per FIND-201 it also fails the JS path. The spec must pick ONE recorder and define exactly how its schema is extended for Solana. As written a builder cannot tell whether to extend the JS ledger or the Python ledger.
Evidence: `skills/earn/video/record_earn.py:11-19,34-42`; `skills/_shared/lib/ledger.mjs:43-48`; spec.md:96-101.

**FIND-203 (MAJOR, requirement_mismatch). The canonical lib paths cited in REV 2 do not exist; the Solana-adapter location is therefore ambiguous.**
Spec.md:40-41 cites `~/anicca/skills/earn/lib/ledger.mjs`, `lib/verify-tx.mjs`, `lib/usdc.mjs`. The real files live at `~/anicca/skills/_shared/lib/{ledger,verify-tx,usdc}.mjs`; `skills/earn/lib/` contains only `record.mjs` (which imports `../../_shared/lib/ledger.mjs`, `record.mjs:8`). REV 2 then says build `lib/solana-verify.mjs` (spec.md:45) without resolving whether that is `earn/lib/` or `_shared/lib/`. Since `verify-tx.mjs`/`usdc.mjs` (the EVM siblings) live in `_shared/lib/`, the Solana adapter almost certainly belongs there too — but a builder following the literal citation will look in the wrong directory. HONESTY Rule 1 (cite the file that exists).
Evidence: actual files at `skills/_shared/lib/`; `skills/earn/lib/record.mjs:8`; spec.md:40-41,45.

---

## Dimension 2 — Edge Cases: **FAIL**

**FIND-204 (MAJOR, spec_gap / unfalsifiable). REQ-6 CLAIMS its liveness check distinguishes "0 because early" from "0 because dead/shadowbanned", but the stated check cannot detect a shadowban.**
REQ-6 (spec.md:90) says a failed liveness check catches a post that is "removed/shadowbanned/rejected". But the actual liveness checks (spec.md:88-89, verification arch spec.md:146) are: the post URL "still resolves on profile" AND submission status "still accepted/active". A shadowbanned reel STILL resolves on the profile and STILL stays `accepted` — only its reach is throttled, so views stay `0`. That is byte-identical to the legitimate early-zero state. The exact prior-F3.2 collision the rewrite was meant to close therefore survives for the shadowban case: the spec overclaims a detection it cannot perform.
Evidence: spec.md:88-90,146.

**FIND-208 (MINOR, spec_gap). The warm-state `ready` precondition (REQ-4) has no defined source or owner.**
REQ-4 (spec.md:77) gates `--live` on "whose warm-state is `ready` (warmer Day-7 complete)" and verification (spec.md:145) says "assert the state file" — but no requirement defines that file's path/schema or who writes `ready`. The existing clip slot reads `~/.cloak/clip-accounts.json` `status=="ready"` (`skills/earn/clip/run.sh:22,47`), but the spec never names this, so the account-guard precondition is unverifiable as written.
Evidence: spec.md:77,145; `skills/earn/clip/run.sh:22,47`.

**FIND-209 (MINOR, edge_case). `usdcDeltaForSig` assumes a single inbound delta; batch/multi-transfer payouts unaddressed.**
Spec.md:50-51 has the adapter "return a number (USDC, 6dp)" for the inbound amount in a tx. A Promote.fun claim could settle multiple ATAs or batch transfers in one signature; the spec gives no rule for selecting/summing only the inbound delta to OUR ATA vs. unrelated transfers in the same tx. Underspecified for a money gate.
Evidence: spec.md:50-51.

---

## Dimension 3 — Implementation Correctness risks: **FAIL**

**FIND-201 (CRITICAL)** — re-applies here: the write path cannot persist the on-chain proof, so the correct end-state is unreachable. See Dimension 1.

**FIND-204 (MAJOR)** — re-applies: shadowban/early-zero are indistinguishable, so MEASURE cannot correctly classify a dead earner. See Dimension 2.

**FIND-206 (MAJOR, requirement_mismatch). `sig`-keyed idempotency is asserted but absent from both named recorders.**
REQ-8 (spec.md:99-100) and REQ-11 (spec.md:113) require "the same `sig` is NEVER double-counted". But `_shared/lib/ledger.mjs` has NO dedup at all (append-only, `isProfitable` is stateless), and `record_earn.py:21-32,37` dedups on `tx_hash`, not `sig`. So sig-keyed idempotency requires NEW logic that neither named mechanism provides; the spec asserts the guarantee without specifying where the seen-`sig` set lives or how it is checked before append.
Evidence: `skills/_shared/lib/ledger.mjs:43-56`; `skills/earn/video/record_earn.py:21-37`; spec.md:99-100,113.

Note (factual, not a finding): the `isProfitable` generalization itself is backward-compatible — the existing test `_shared/lib/__tests__/ledger.test.js:28-33` only requires non-`tx`/non-`0x1` lines to be false, which an `(EVM 0x1) OR (Solana sig+confirmed)` branch preserves. The break is in the WRITE path (`deriveLine`), not the classifier predicate.

---

## Dimension 4 — Structural Integrity: **FAIL**

**FIND-202 (MAJOR)** — re-applies: two parallel ledger systems (JS `_shared` ledger + Python `record_earn`) with incompatible schemas are both invoked as "canonical"; the feature bolts Solana onto an unreconciled fork. See Dimension 1.

**FIND-207 (MAJOR, structural). Modifying the SHARED `_shared/lib/ledger.mjs` has blast radius beyond this feature, and the spec mandates no regression coverage for it.**
`isProfitable`/`deriveLine` in `_shared/lib/ledger.mjs` are consumed by the main earn slot via `earn/lib/record.mjs` and are covered by `_shared/lib/__tests__/ledger.test.js`. REV 2 (spec.md:54-60) requires editing this shared file to add a Solana branch and (per FIND-201) `deriveLine` field-passthrough, but the verification architecture (spec.md:140-156) never mandates extending or re-running that existing test suite. Editing shared canonical code with no regression gate is a structural hazard, and the new Solana fields must be added without loosening the `external:true`/swap guards the suite locks (`ledger.test.js:23-34`).
Evidence: `skills/_shared/lib/__tests__/ledger.test.js:23-34`; `skills/earn/lib/record.mjs:8`; spec.md:54-60,140-156.

**FIND-203 (MAJOR)** — re-applies: ambiguous module location for `solana-verify.mjs` (earn/lib vs _shared/lib) is a structural placement defect. See Dimension 1.

---

## Dimension 5 — Verification Readiness: **FAIL**

**FIND-201 (CRITICAL)** — re-applies as the dominant verification defect: the DONE check (verification arch spec.md:148-151) is NOT runnable against the named lib, because the line `record.mjs` actually persists lacks `sig`/`confirmed`. A maker≠checker who runs `record.mjs` then `isProfitable` on the result gets `false`, not DONE. The acceptance criterion is uncheckable exactly as written. See Dimension 1.

**FIND-205 (MAJOR, verification_tool_mismatch). REQ-9's runtime watchdog is asserted but its mechanism/owner is undefined, so the "inject a blocking step and observe the timeout" test is not constructible.**
REQ-9(b) (spec.md:104-108) requires "each wake runs under a hard `SKILL_TIMEOUT_S` watchdog AND each browser/IO step under a per-step deadline" tripping to `did:"blocked:human:<step>"`. But (a) the spec never says WHO enforces `SKILL_TIMEOUT_S` — the harness (`run-skill.mjs`) or `run.sh`; the existing `clip/run.sh:10` only mentions it in a comment and implements NO `timeout`/trap; and (b) "per-step deadline on each browser/IO step" has no contract (how a CDP call is wrapped, what the per-step budget is). The verification (spec.md:152-153) "inject a step that blocks → watchdog trips within `SKILL_TIMEOUT_S`" can only test a wake-level timeout IF one is actually implemented, and cannot test the per-step deadline because the per-step mechanism is unspecified. The no-human INVARIANT remains partly asserted rather than constructibly verifiable.
Evidence: spec.md:104-108,152-153; `skills/earn/clip/run.sh:10` (SKILL_TIMEOUT_S referenced but not enforced).

**FIND-207 (MAJOR)** — re-applies: no mandated re-run of the shared ledger test suite after the shared-code edit means the regression surface is unverified. See Dimension 4.

---

## MUST-FIX before building (prioritized)

1. **[FIND-201, CRITICAL] Make the DONE write-path actually persist the Solana proof.** Generalizing `isProfitable` is necessary but NOT sufficient: `deriveLine` (`_shared/lib/ledger.mjs:14-28`) must also carry `sig`, `confirmed`, and `chain` (and `assertOwnIdentityOnly` in `record.mjs:19` must be shown to pass a Solana line), OR REQ-8 must name a different, fully-specified recorder. Add an explicit test: `record.mjs` of the Solana line → `isProfitable(persistedLine) === true`.
2. **[FIND-202] Pick ONE canonical recorder** (JS `_shared` ledger+`isProfitable`, or Python `record_earn.py`) and define its exact Solana-extended schema; do not cite both as authoritative with mutually incompatible field sets (`tx_hash`+`verified`+`direction` vs `tx`+`status`+`external`).
3. **[FIND-206] Specify sig-keyed idempotency concretely** — where the seen-`sig` set is stored and the pre-append check — since neither named recorder provides it.
4. **[FIND-204] Add a real shadowban/early-zero discriminator to REQ-6**, or drop the claim that liveness detects shadowbans. URL-resolves + status-accepted cannot do it; require an independent reach/impression signal or an explicit time-bounded "0 views past T = dead" rule.
5. **[FIND-205] Define the watchdog mechanism and owner.** State whether `run-skill.mjs` or `run.sh` enforces `SKILL_TIMEOUT_S`, give the per-step deadline contract (what wraps each CDP/browser/IO call, the per-step budget), and make the "inject a blocking step → exit 0 with `blocked:human:*`" test runnable.
6. **[FIND-207] Mandate extending + re-running `_shared/lib/__tests__/ledger.test.js`** as part of the shared-code change, preserving the `external:true`/swap/`0x1` guards while adding Solana cases.
7. **[FIND-203] Correct the canonical lib paths** to `skills/_shared/lib/…` and fix the `solana-verify.mjs` target directory.
8. **[FIND-208] Define the warm-state `ready` file** (path/schema/owner) that REQ-4 asserts.
9. **[FIND-209] Specify multi/batch-transfer handling** for `usdcDeltaForSig` (select/sum only the inbound delta to our ATA).
