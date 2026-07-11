# spawn-funding-swap sprint-2 real-clients — iteration 2 adversary notes

Fresh-context review. No manifest existed yet at `reviews/impl/iteration-2/input/manifest.json` (nor
`state.json` for this feature in this worktree's `.vcsdd/`) — the launching agent's task message itself
specified worktree, iteration path, HEAD commit, and the exact adversarial questions to answer, so this
review proceeds against that brief directly, sourcing all artifacts by direct Read/Grep of the worktree.

## Files actually read (all under `/Users/anicca/anicca/.worktrees/spawn-realclients/`)

- `skills/self/spawn-funding-swap/specs/behavioral-spec.md`
- `skills/self/spawn-funding-swap/specs/verification-architecture.md`
- `skills/self/spawn-funding-swap/lib/real-clients/base-signer.mjs` (full file, 431 lines)
- `skills/self/spawn-funding-swap/lib/real-clients/__tests__/base-signer.test.mjs` (full file, 458 lines)
- `skills/self/spawn-funding-swap/lib/real-clients/__tests__/test-money-safety-scan.test.mjs` (full file)
- `skills/self/spawn-funding-swap/lib/real-clients/chain-reader.mjs` (full file)
- `skills/self/spawn-funding-swap/lib/driver.mjs` (full file, 299 lines)
- `skills/self/spawn-funding-swap/lib/pure/constants.mjs` (full file)
- `skills/self/spawn-funding-swap/lib/pure/swap-need.mjs` (full file)
- `skills/self/spawn-funding-swap/lib/pure/route-validation.mjs` (full file)
- `skills/self/spawn-funding-swap/lib/__tests__/driver-crash-recovery.test.mjs` (full file)
- `skills/self/spawn-funding-swap/bin/spawn-funding-swap.mjs` (grep for constants imports)
- `.vcsdd/features/spawn-funding-swap/reviews/impl/iteration-1/output/verdict.json` + `findings/FIND-001.json`

No Bash tool is available to this adversary in this environment — the "173/173 pass at HEAD 74d0af34"
claim was NOT independently re-executed; it is reported as the thinker's claim in `regressionCheck` and
this review instead relies on direct code/test-file inspection to establish correctness, per the task's
instruction that the thinker already ran the full suite.

## Answering the four verify items directly

**1(a) Can a malicious Skip response still move funds via a path that passes all 4 gates, through a
router entrypoint that pulls MORE than `amount`?** YES — see FIND-001. Gate 3 checks a self-reported
metadata field (`required_erc20_approvals[0].amount`), never the entrypoint's actual encoded pull. The
entrypoint's real transferFrom pull is bounded only by the ACTUAL on-chain allowance, which is a standing
grant of $100 set independently of any specific swap's amount.

**1(b) Does a pre-existing higher approval from a past swap let a crafted route over-pull?** YES — this
is precisely the mechanism. `ensureApprovalsSettled` never lowers the allowance once it reaches
`APPROVAL_CAP_BASE_UNITS` ($100); the module's own header comment documents this as intentional
("gives headroom for many swaps ... before a re-approval is ever needed"). So after the very first swap,
the wallet carries a standing $100 allowance to whatever spender the (trusted) Skip route named — and if
that trust is violated on any LATER call, gate 3's exact-amount check on the metadata field provides no
protection against the entrypoint pulling up to that full standing amount.

**1(c) Any other drain selector (permit/increaseAllowance) left open?** No additional vector found at the
TOP-LEVEL call target: gate 2 already forbids `evm_tx.to === USDC contract`, so a top-level
`permit()`/`increaseAllowance()` call on USDC itself is already blocked. The real vector is the
entrypoint-forwarding one above (1a/1b), which is more subtle and not selector-based.

**1(d) Is value==0n correct?** Yes — this feature's route is USDC-in only (source asset is an ERC-20, not
native ETH); no leg of the live-confirmed route shape legitimately needs a non-zero native value on the
Base leg. No issue found here.

**2. Is loss bounded to exactly `amount` under a fully-malicious route?** NO. Confirmed by direct trace:
driver.mjs:174-175 + swap-need.mjs:41-46 (`capUsd`) independently, purely cap `amount` at `SWAP_MAX_USD`
($20, constants.mjs:16) — this half of the question is verified TRUE, `amount` genuinely is
route-independent and capped. But base-signer.mjs's actual worst-case bound is `MAX_SWAP_BASE_UNITS` ==
`APPROVAL_CAP_BASE_UNITS` ($100, base-signer.mjs:89-99), a flat, amount-independent ceiling that is 5x
larger. This is the central finding of this iteration (FIND-001), with supporting documentation-accuracy
findings (FIND-002 in verification-architecture.md, FIND-003 in behavioral-spec.md) showing the codebase's
own comments assert a tighter guarantee than what's actually implemented, and a coverage finding
(FIND-004) showing no test distinguishes "honest reported metadata" from "metadata that lies about what
the entrypoint will actually do."

**3. Regression / PROP-050 tamper tests.** All four named tamper tests (inflated amount, tampered `to`,
over-ceiling, bare-transfer) are present in base-signer.test.mjs and each asserts
`walletClientFactory.sent.length === 0` (never broadcast) on the rejection path — genuinely enforced, not
merely "does not throw" theater. These close exactly what iter1's FIND-001 literally described (a bare
transfer() call, or a `to`/amount mismatch reported in the metadata) — they do not, and structurally
cannot, close FIND-001 of THIS iteration, because that vector requires decoding calldata neither the
tests nor the implementation ever look at.

**4. Are 003-007 genuinely closed with no new issue?** FIND-003 (probe-spender divergence, iter1):
genuinely closed/tested via PROP-051, fails closed as documented. FIND-004 (quoteSnapshot reconciliation,
iter1): genuinely wired driver.mjs -> base-signer.mjs and tested both divergence and match cases.
FIND-005 (constants dedupe): genuinely closed, grep confirms zero remaining hand-copied literals outside
comments across `lib/**` and `bin/spawn-funding-swap.mjs`; no value was changed in the process (same $100/
$20/chain-id/denom/address literals, single-sourced). FIND-006 (NFR-8 nonce-ownership doc): present,
honest about being an unenforced assumption. FIND-007 (money-safety-scan bare-createRealXxx check):
genuinely implemented with its own self-check test (`test-money-safety-scan.test.mjs`'s
"PROP-049 (self-check)" test actually exercises the detector against a deliberately-bare fixture string).
No regression or new issue introduced by any of these five fixes was found.

## Verdict

FAIL overall (spec_fidelity, edge_case_coverage, implementation_correctness, verification_readiness all
FAIL; structural_integrity PASS). NO-GO on real money movement until FIND-001 is addressed at its root
(decode+verify the entrypoint's actual encoded pull amount, and/or stop maintaining a standing
above-per-swap on-chain allowance across swaps).
