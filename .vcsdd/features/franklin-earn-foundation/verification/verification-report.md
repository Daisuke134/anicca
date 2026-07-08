# Verification Report — franklin-earn-foundation (lean)

Feature: sol-trade P&L recording + per-instance identity safety (REQ-001 EVM wallet-leak fix,
REQ-002 sol-trade realized P&L recording). Fix commit: `3fe382b` (closes 6 adversary blocking
findings). All paths under `/Users/operator/anicca/`.

## Tests (Phase 2a/2b)
Real GREEN output in `evidence/sprint-1-green-phase.log`; RED baseline in `evidence/sprint-1-red-phase.log`.
- `parse-pass.test.mjs` 5/5 pass (extractLastSignature: LAST sig, ANSI-strip, multi-sig, never-throw)
- `record-swap.test.mjs` 8/8 pass (records win OR loss; NEVER external:true; verify-error path appends nothing; earn_usdc/cost_usdc present)
- `tests/test_run.sh` 9/9 pass — hermetic bash integration (PROP-011..016): Franklin PROCEED+record, non-owner HALT (no CLI call, no ledger write), ambient key does NOT bypass, multi-sig records LAST, verify-error degrades to trace-only
- regression: `identity-guard.test.js` 12/12 pass (unchanged)

## Adversary (Phase 3, fresh Opus, two iterations)
- iteration-1 (`reviews/impl/iteration-1/`): FAIL, 6 blocking findings (FIND-001 ambient-key guard bypass [money-safety]; FIND-002 parse-pass.mjs missing; FIND-003 first-not-last sig; FIND-004 external:true vs own test; FIND-005 no integration tests; FIND-007 no verify-error trace). All independently reproduced by the parent before fixing.
- iteration-2 (`reviews/impl/iteration-2/`): **PASS, 0 blocking**. All 6 CLOSED (static trace + independent test-count re-derivation + call-graph trace confirming the integration suite is genuine, not tautological). 3 new findings, all non-blocking/low (cosmetic / stricter-than-spec, no money-safety impact).

## Real-chain E2E (record-swap against a REAL 8Fpqd on-chain signature)
`verification/security-results/realchain-e2e.log`: fetched a real signature from Franklin's wallet
8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9 via getSignaturesForAddress, ran record-swap.mjs under
`env -i` against a scratch ledger → `status:"recorded", net_usdc:-0.008664, earn_usdc:0,
cost_usdc:0.008664, profitable:false`. Proves sigStatus→usdcDeltaForSig→record over LIVE chain data,
records a real LOSS (the exact case record-payout.mjs's delta>0 gate would miss), and correctly does
NOT claim GATE-0 (profitable:false, no external:true). Real production ledger untouched.

## Proof Obligations (discharge status)
- PROP-011 (per-instance identity resolution, no cross-instance key): DISCHARGED — earn/run.sh unsets ANICCA_EVM_PRIVATE_KEY + resolve-identity evm; sol-trade/run.sh unsets ambient ANICCA_SOLANA_PRIVATE_KEY (run.sh:13) before OWN/CLI derivation. integration (b)(c).
- PROP-012 (fail-closed on unresolvable secret): DISCHARGED — wallet-address-solana.mjs prints nothing + exit 0; guard HALTs on empty OWN_WALLET.
- PROP-013 (non-owner HALT before touching franklin-trading CLI): DISCHARGED — integration scenario (b), no CLI invocation, no ledger write.
- PROP-014 (record win AND loss, sig-keyed idempotency): DISCHARGED — record-swap.test.mjs + real-chain E2E (loss recorded).
- PROP-015 (LAST signature on multi-swap pass): DISCHARGED — parse-pass extractLastSignature + integration (f).
- PROP-016 (verify-error degrades to trace-only, no fake earn): DISCHARGED — record-swap returns verify-error (no append) + run.sh appends sol-verify-failed trace line; integration (g).

## Summary
All target tests GREEN, regression GREEN, fresh Opus adversary PASS (0 blocking) at iteration-2, and a
LIVE on-chain E2E confirms real P&L recording (including a real loss) with no false GATE-0. The feature
is implementation-verified. Remaining non-blocking findings (FIND-101/102/103) are cosmetic/stricter-than-
spec with no money-safety impact and are recorded for a future cleanup pass, not blocking convergence.
