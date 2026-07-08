# Spec Review Findings — hl-realized-pnl (Phase 1c, iteration 2)

Reviewer: fresh-context VCSDD adversary, zero knowledge of iteration-1's reviewer reasoning.
Reviewed the REVISED `specs/behavioral-spec.md` and `specs/verification-architecture.md` against
iteration-1's `findings.md`, the referenced production code (`skills/earn/hl-trade/hl.py`,
`skills/earn/run.sh`, `skills/_shared/lib/ledger.mjs`, `skills/earn/lib/record.mjs`,
`skills/earn/lib/resolve-identity.mjs`, `skills/earn/sol-trade/lib/record-swap.mjs`,
`skills/earn/self-improve/lib/ledger_reader.py`), and independently re-derived the audit evidence
numbers from the raw live API response.

## Iteration-1 findings: resolution check

| ID | iteration-1 severity | Resolved? | Evidence |
|---|---|---|---|
| F-1 | BLOCKING (checkpoint `+1` boundary silently drops tied-timestamp sibling forever) | YES — substantively, not cosmetically | REQ-B8 now states the boundary is INCLUSIVE (`since_time_ms`, explicitly NOT `+1`), with an explicit non-negotiable money-safety invariant paragraph naming the exact silent-drop failure mode and rejecting it "regardless of how it is phrased." REQ-B2's candidate filter is also now `>=` (inclusive), consistent with B8. REQ-B5 now explicitly documents that a subsequent pass WILL re-fetch the checkpoint-setting fill and its ties, and that REQ-B4.1's tid-dedup (not the time boundary) is the sole duplicate-prevention mechanism. New PROP-002b (unit, proves `>=` not `>` via a tied-timestamp fixture), PROP-010 (static grep asserting `since_time_ms + 1`/`since_time_ms+1` never appears in `reconcile.py`, and `Info.user_fills(` unbounded variant never appears), and PROP-010b (full integration regression test reproducing F-1's exact two-pass failure trace: X/Y tied at t=500, Y fails pass 1, pass 2 re-queries from 500 inclusive, dedups X, records Y) were added. EDGE-9 expanded into new EDGE-11 with the exact scenario. I independently re-verified the audited wallet's own history actually contains 1 real tied-timestamp pair (time=1783129123087, tids 987009796558893/247403740235423) by re-parsing the raw JSON myself — this is not a hypothetical edge case for this wallet. |
| F-2 | MAJOR (check-then-act race, no lock, concurrent reconcile could double-record) | YES | New REQ-B10 requires fcntl.flock(fd, LOCK_EX \| LOCK_NB) acquired BEFORE reading the checkpoint or already_recorded_tids, held for the entire read-check-record-write sequence, released after the checkpoint write or on STOP/error; a non-acquirable lock returns {"status":"locked","recorded":0} untouched. New PROP-022 (real fcntl.flock integration test, not a fake). Not a novel pattern for this codebase — skills/_shared/proactive-loop-dispatch.py:43 already uses the identical fcntl.flock(fh.fileno(), fcntl.LOCK_EX \| fcntl.LOCK_NB) idiom for the same class of re-entrancy guard, so REQ-B10 copies an established in-repo convention rather than inventing one. |
| F-3 | MAJOR (GATE-0 redefinition — HL close as "external" — bundled invisibly inside a bugfix spec) | YES, as a documented policy decision | REQ-C1 now carries an explicit "Policy sign-off" paragraph naming the policy owner (Dais), the directive date (2026-07-09), and its literal goal text, plus a dedicated "Wash-trading / self-dealing defense" paragraph explaining why GATE-0's unchanged net_usdc > 0 gate and this feature's zero new trading logic (REQ-D3) bound the risk. This resolves F-3's actual ask ("should be explicitly confirmed... not treated as an implicit side effect") — the redefinition is now visible, dated, attributed, and defended, not hidden. Whether the underlying policy call itself is correct is a business decision outside a spec-review adversary's remit once it is explicit and defended, which it now is. |
| F-4 | minor (cited audit numbers had no evidence artifact) | YES | evidence/audit-userfills-0xa3cdd4-raw.json (146-element raw array) and evidence/audit-userfills-summary.md now exist. I independently re-parsed the raw JSON and recomputed every cited figure myself rather than trusting the summary file: count 146, non-zero-closedPnl count 71, sum(closedPnl)=0.27274, sum(fee)=0.396474, net=-0.123734, fee/tid present on all 146 fills (0 missing), tid always Python int, exactly 1 tied-timestamp pair — all confirmed. Every number in the evidence file is honestly derived from the raw file, not fabricated or rounded to look better. |
| F-5 | minor (SDK docstring omits fee/tid; assumption unconfirmed live) | YES | The live raw response's first fill (and all 146) carry both fee (numeric string) and tid (int) — reproduced independently above. Spec §2 item 2 now explicitly states the installed SDK docstring is stale/incomplete, not the live API. |
| F-6/F-7/F-8 | note (no action required) | N/A | F-6 was a positive confirmation. F-7 (REQ-E3 scoping vs P1 HALT guard) is now explicitly addressed in REQ-E3's own body. F-8 (linear-scan cost) is now explicitly named and deliberately deferred in NFR-4. |

No cosmetic/relabeling-only fixes were found — every BLOCKING/major item from iteration 1 has a
structural spec change plus at least one new falsifiable PROP tied to the exact failure trace that
was raised.

## New findings, iteration 2

### F-9 — MINOR

Dimension: verification_readiness
Target: REQ-A2, REQ-D4, REQ-E4, REQ-E5 (implementation-side)

What is wrong: Four REQs use strong negative "SHALL NEVER" language but have no dedicated,
independently-checkable PROP in the table (unlike REQ-A1, whose negative claim gets a direct
grep -n "closed_pnl_usd" in PROP-018, or REQ-D3, whose negative claim gets a direct grep in
PROP-017):

- REQ-A2 ("SHALL NEVER be derived from a pre-close or post-close unrealizedPnl/accountValue
  snapshot") has no static check (e.g. grep -n "unrealizedPnl\|accountValue" on reconcile.py/fills.py
  = 0 matches) analogous to PROP-017/PROP-018's style. Only indirectly implied by the
  purity-boundary table showing fetch_fills calls user_fills_by_time (never user_state).
- REQ-D4 (no cross-instance leakage) has no PROP verifying the checkpoint/lock/ledger paths are
  actually derived from the caller's own resolved home directory rather than a hardcoded or
  shared-$HOME path — PROP-016 covers identity-key reuse (REQ-D2) but nothing directly covers
  REQ-D4's path-scoping claim.
- REQ-E4 ("hl.py close keeps performing Exchange.market_close unchanged") has no PROP; only
  REQ-A1's negative claim (field removed) is checked. Nothing asserts the market_close call
  itself is still present/unchanged post-diff.
- REQ-E5 (no "dry"/"fake"/"mock"/"simulated" in production code/log lines) is checked only at
  runtime inside PROP-021(d)'s live E2E output, not as a static grep across fills.py/reconcile.py
  themselves.

None of these are money-safety BLOCKING — the underlying architecture already structurally
prevents the bad outcome in each case (e.g. reconcile.py's only data-source call is
fetch_fills/user_fills_by_time per the purity-boundary table, so REQ-A2 is satisfied by
construction, not by discipline) — but "every REQ covered by >=1 falsifiable PROP" is one of this
review's explicit dimensions, and these four are not, strictly. Recommend adding four one-line
static-grep PROPs before Phase 2 (TDD) starts, mirroring PROP-017/PROP-018's existing style.

Evidence (file:line): .vcsdd/features/hl-realized-pnl/specs/verification-architecture.md
(proof-obligation table, PROP-001 through PROP-022 — no entry keyed to REQ-A2, REQ-D4, or REQ-E4;
PROP-021(d) is the only REQ-E5 check and it is E2E-runtime-only, not static).

### F-10 — NOTE

Dimension: verification_readiness
Target: REQ-C4

What is wrong: REQ-C4 is phrased as a SHALL ("SHALL be noted in a code comment there") but has
no corresponding PROP in the table. Not a defect — REQ-C4 is self-consciously an exception to
"every REQ needs a PROP," and the spec's own Done criteria explicitly say ledger_reader.py
recognition is not required — but flagging so the Phase 3 adversary doesn't mistake the
comment's absence-of-a-PROP for an oversight.

Evidence (file:line): .vcsdd/features/hl-realized-pnl/specs/behavioral-spec.md:220-226 (REQ-C4).

---

## Summary of severities (iteration 2)

| ID | Severity | Dimension(s) |
|---|---|---|
| F-9 | minor | verification_readiness |
| F-10 | note | verification_readiness |

Blocking: 0. Major: 0. Minor: 1. Note: 1.

All five of iteration-1's BLOCKING/major/minor findings are genuinely resolved with structural
spec changes and new falsifiable proof obligations, independently re-verified against the raw live
evidence (not merely re-reading the summary file's own claims about itself).
