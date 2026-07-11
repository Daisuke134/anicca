# Adversary notes — lending-lender-key-wiring, impl-review iteration-2

Fresh-context review. No Bash tool available this session -- all verification below is static
(Read/Grep/Glob only) plus one direct read of the live production ledger file
(`~/.blockrun/skills/economy/lending/state/loans.jsonl`) and one live launchd plist / one live
`.env` file, all readable as plain files. Test execution claims ("10/10", "34/34", "139/139",
"250/250") are the task's own reported thinker/builder results, NOT independently re-run by me.

## Files read (this review's own evidence base)

- `.vcsdd/features/lending-lender-key-wiring/{state.json,specs/behavioral-spec.md}`
- `.vcsdd/features/lending-lender-key-wiring/reviews/impl/iteration-1/output/verdict.json` + findings
- `skills/economy/lending/lib/lending-signer.mjs` (new this fix)
- `skills/economy/lending/scripts/wake-gate.mjs` (full)
- `skills/economy/lending/lib/lending-orchestrator.mjs` (full)
- `skills/economy/lending/lib/lending-verify.mjs` (full, unmodified by this fix but newly reachable)
- `skills/economy/lending/lib/__tests__/wake-gate.test.mjs` (full, 10 tests)
- `skills/economy/lending/lib/__tests__/lending-orchestrator.test.mjs` (FIND-001/002/003 sections)
- `skills/economy/lending/lib/__tests__/lending-verify.test.mjs` (reconcile sections)
- `skills/economy/gig/lib/escrow.mjs` (full -- to trace whether a chain mismatch fails safely)
- `skills/economy/gig/WITNESS-RUNBOOK.md` (facilitator port history)
- `skills/registry.json` (economy/lending entry, "status":"live")
- `runtime/loop/always-act-router.mjs` (confirms model-driven, non-cron wake selection)
- `~/.anicca-signing/gig-board/.env` (live GIG_CHAIN/GIG_FACILITATOR_URL config)
- `~/.blockrun/skills/economy/lending/state/loans.jsonl` (the real, live stuck loan_Franklin_1 row)
- `~/Library/LaunchAgents/ai.anicca.franklin-loop.plist`, `...franklin2-loop.plist`

## Item-by-item findings (per the review brief)

**1. FIND-001 fix (signer==lender_wallet guard):** SOLID. Traced both guard sites. The wake-gate.mjs
guard runs unconditionally before `executeLoanIssuanceAttempt` on every branch -- including the
stuck-row recovery path, which is nested INSIDE `executeLoanIssuanceAttempt`'s own locked section and
therefore categorically cannot run before the guard. `addressesEqual` is case-insensitive and
fail-closed. `defaultDisburse`'s independent re-derivation is a genuine second layer, not a rubber
stamp -- it re-derives from `deps.lenderPrivateKey` and compares against `loanRow.lender_wallet`
(the ledger's own recorded value, not the same variable the wake-gate guard used), so a hypothetical
future direct caller bypassing wake-gate.mjs is still covered. No path reaches `payViaFacilitator`
with a mismatched key. **No new finding.**

**2. FIND-002 fix (bounded reconciliation) -- the double-disburse question:** This is where the deeper
problem lives (FIND-101, FIND-102 in this iteration's output). Two independent gaps compound:

  - `reconcileProvisionalDisbursement` never checks the matched Transfer log's own VALUE against
    `loanRow.principal_usd` -- it only checks address+from+to topics. This means the "found" signal is
    not "this loan's own disbursement happened", it is "SOME transfer between these two wallets
    happened within this window". For today's colony, Franklin and Franklin2 already have a prior,
    separately-documented on-chain transaction with each other (P2 gig-marketplace witness trade,
    per this session's own memory context) -- I could not rule out, without live RPC access, whether
    that transaction's own wallets/timing could coincidentally satisfy `reconcileProvisionalDisbursement`
    for the ledger's stuck row, though the gig marketplace's escrow-address model (a separate
    `GIG_ESCROW_ADDRESS`, not necessarily either party's own lending wallet) makes a direct
    lender_wallet-to-borrower_wallet match for that specific historical trade less likely than a
    generic "any future coincidental transfer" concern. Either way, the missing value check is a real
    implementation gap independent of this specific instance.
  - The 9000-block (~5h) window is only as safe as "reconciliation for this exact lenderId reliably
    re-runs within 5h of a crash" -- and I traced that this system has NO such guarantee. `economy/lending`
    is reached only via the model-driven "always-act" menu (`runtime/loop/always-act-router.mjs`'s
    `DOCTRINE_EARN_ACTIONS`), where the agent freely picks ONE earn action per wake from a menu that also
    includes gig/PM/HL/SOL trading etc. There is no fixed cron interval specifically for lending, and no
    code anywhere compares `nowMs - staleRow.provisioned_ms` against the lookback's own real-time span
    before trusting a `{found:false}` result. The spec's own REQ-120 Edge Cases text names only the
    "risks missing a match" consequence, not the double-disburse consequence that actually follows from a
    miss in `resolveStaleProvisioning`'s own code.

  For TODAY's specific `loan_Franklin_1` row, I independently confirmed (by reading `escrow.mjs` fully)
  that the crash genuinely happens at `privateKeyToAccount(undefined)` inside `signAuthorization`, which
  is the FIRST statement in `payViaFacilitator`'s call chain, strictly before any `fetch()` call in
  `postJson`/`verifyWithRetry`/`settleBody`. So there is provably no real transfer for THIS row to
  double against, independent of window size -- reconciling it to `disbursement_failed` is correct.
  This narrow case is safe; the general mechanism is not yet proven safe for the NEXT crash.

**3. FIND-003 (mainnet gate + port):** The GIG_CHAIN=='base' code gate is solid and tested
  (`lending-orchestrator.test.mjs:471-491`). The port claim is the part I could not fully verify: this
  repo's own `WITNESS-RUNBOOK.md` (2026-07-07) explicitly recorded that PID 94412 on port 8405 was, at
  that time, the TESTNET facilitator, deliberately left untouched, with mainnet config tested on a
  SEPARATE scratch port (8406) specifically to avoid disturbing 8405. `~/.anicca-signing/gig-board/.env`
  today says `GIG_CHAIN=base` + port 8405, which is consistent with someone having since restarted the
  8405 process with `config.mainnet.json` (same port, per the runbook's own `start.sh` change) -- but
  `lsof -iTCP:8405` (the check this fix's own spec cites) cannot distinguish "listening, mainnet-
  configured" from "listening, still testnet-configured" the way `/supported` can (the runbook itself
  used `/supported` for its own genuine confirmation, on the scratch port only). I could not run a live
  HTTP check myself (no Bash). Flagged as FIND-103, high not critical, because escrow.mjs's own payload
  includes an explicit `network: eip155:${chainId}` field that a spec-compliant x402 facilitator would
  be expected to validate and reject on mismatch (fail-safe), but that expectation is itself unverified
  against the actual x402-rs binary (not part of this worktree/review scope).

**4. FIND-004 fix (mock RPC range-restriction):** Confirmed genuinely restrictive --
  `wake-gate.test.mjs:446-463`'s handler rejects `fromBlock:"earliest"`, rejects a non-hex/non-bounded
  `toBlock`, and rejects a span over 10,000 blocks. This is a real constraint the fix's own bounded call
  must satisfy to pass, not a rubber-stamped no-op mock.

**5. Full re-trace of the first loan:** Franklin(0x3EcC...) wake -> resolves Franklin's own key via
  `resolveEvmPrivateKey` -> `findSelectedPair` selects {lenderId:"Franklin", borrowerId:"Franklin2"} ->
  FIND-001 guard compares derived signer address to Franklin's own registered `walletAddress.evm` ->
  passes (assuming Franklin's wake resolves Franklin's own key, which `resolveEvmPrivateKey`'s
  ANICCA_HOME-scoping already guarantees structurally) -> `resolveStaleProvisioning` finds
  `loan_Franklin_1` at `disbursement_uncertain` -> reconciles. Confirmed via direct read of the live
  `loans.jsonl` (2 rows: `provisioning` then `disbursement_uncertain`, `error:"Cannot read properties of
  undefined (reading 'slice')"`, `provisioned_ms:1783744749665`) that this crash is the pre-signing
  crash described above -- reconciling this SPECIFIC row to `disbursement_failed` is correct
  independent of FIND-101/102, PROVIDED FIND-101's value-blind matching doesn't coincidentally hit an
  unrelated transfer between these two wallets (unverified, no RPC access this session).

## Go/No-Go

**NO-GO** for treating this as a fully-hardened, repeatable "safe to lend real money, forever" mechanism.
**Narrowly**, reconciling and superseding TODAY's specific stuck `loan_Franklin_1` row is independently
confirmed safe by this review (pre-signing crash, no real transfer exists to double against) --  but the
review brief asked me to gate more than just today's specific row; it asked whether the fix is safe for
"the first live loan" as a mechanism going forward, and FIND-101/FIND-102 show it is not yet, without
either (a) a value-match check in reconciliation or (b) a bound tying the reconciliation window to the
row's own real elapsed age (refuse rather than silently proceed when the row is older than the window
can cover). FIND-103 is a residual, unconfirmed operational precondition that should be checked live
(one `curl`) before the actual wake, independent of any further code change.
