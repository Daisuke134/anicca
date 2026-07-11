# Adversary notes — lending-lender-key-wiring, impl review iteration 1

Fresh-context review, no builder history. Read: state.json, specs/behavioral-spec.md,
specs/verification-architecture.md, skills/economy/lending/scripts/wake-gate.mjs,
skills/economy/lending/lib/lending-orchestrator.mjs, lending-verify.mjs, lending-gate.mjs,
skills/earn/lib/resolve-identity.mjs, skills/economy/gig/lib/escrow.mjs,
skills/economy/lending/run.sh, skills/_shared/lib/load-instance-env.sh, all four
skills/economy/lending/lib/__tests__/*.test.mjs files, skills/economy/gig/WITNESS-RUNBOOK.md,
skills/self/founder-loop/record-earn.mjs (grep only, for the FIND-702 precedent), evidence/*.log,
and the REAL production files /Users/operator/.blockrun/skills/economy/lending/state/loans.jsonl and
/Users/operator/.hermes/state/citizens.json (Read tool reaches outside the worktree; these are cited
as evidence, not edited).

No reviews/impl/iteration-1/input/manifest.json existed in this worktree (lean-mode feature, no
formal manifest was ever written) -- this review's scope was taken directly from the launching
agent's task description (specs/ + the named source/test files), consistent with `mode: lean` in
state.json.

## What is genuinely solid
- REQ-118a fail-closed refusal is real and tested (evidence/sprint-1-red-phase.log shows the
  3 new REQ-118 tests genuinely FAILING pre-fix with real AssertionErrors; green-phase log shows
  8/8 post-fix -- no fabricated RED/GREEN evidence).
- resolveEvmPrivateKey itself (skills/earn/lib/resolve-identity.mjs:69-100) is correctly
  fail-closed and ANICCA_HOME-scoped in isolation -- it never resolves a DIFFERENT instance's key.
- No private-key-shaped value is ever logged, printed, or persisted anywhere on this diff's own
  path -- verified by direct grep of wake-gate.mjs/resolve-identity.mjs/escrow.mjs/
  lending-orchestrator.mjs and by reading the CLI's own `console.log(JSON.stringify(result))`
  return shape (wake-gate.mjs:188-202): candidatesConsidered/selectedPair/issuance/sweep, none of
  which ever contains the key.
- reconcileProvisionalDisbursement (lending-verify.mjs) is genuinely read-only (tested explicitly:
  lending-verify.test.mjs's own "never invokes any transfer/settle call itself" test) and uses
  exact zero-padded-topic equality, not a substring match -- the underlying reconciliation LOGIC is
  sound; this fix's own diff is small, scoped, and well-commented.
- The $0.02 cap / 10% interest / DEFAULT_RESERVE_USD / withGigLock single-in-flight locking are all
  confirmed untouched by this diff.

## Why this is NO-GO as-is (see FIND-001..004 for full evidence)
1. **FIND-001 (critical)**: the resolved lenderPrivateKey's derived on-chain address is never
   checked against `loanRow.lender_wallet`/the selected lenderId's own registered wallet anywhere
   in the disbursement path. wake-gate.mjs's own comment ASSERTS "this wake ALWAYS runs under the
   LENDER's own per-instance env" but nothing enforces it, and findSelectedPair scans the entire
   shared registry, not "self only". The real production registry has two independently-homed
   citizens (Franklin, Franklin2) whose own run.sh is designed (per its header) to be invoked on
   EACH citizen's own wake -- if Franklin2's own wake ever independently computes the same
   deterministic selectedPair (which today it would, since it's the same shared ledger/registry
   state), Franklin2's OWN key gets used to sign a transaction the ledger attributes to Franklin.
2. **FIND-002 (critical)**: this exact fix is what makes `defaultReconcile`'s
   `fromBlock: deps.reconcileFromBlock || "earliest"` reachable against a REAL RPC
   (`https://mainnet.base.org`) for the very first time -- and this codebase's OWN prior FIND-702
   fix (record-earn.mjs) explicitly documents why an unbounded eth_getLogs scan is dangerous
   against a real provider. If mainnet.base.org rejects/times out the "earliest" scan, the real
   stuck loan_Franklin_1 row would get `reason:"reconciliation_failed"` and permanently block
   Franklin's every subsequent wake -- the EXACT failure mode REQ-118b says this fix must resolve.
3. **FIND-003 (medium)**: GIG_CHAIN/GIG_FACILITATOR_URL (which actually gate mainnet vs. testnet
   settlement, per skills/economy/gig/WITNESS-RUNBOOK.md's own 8405-vs-8407 convention) are outside
   this diff's scope and untested by it, but directly determine whether "the first real loan" is
   real at all.
4. **FIND-004 (high)**: the only test exercising defaultReconcile's real rpcUrl path uses a fully
   permissive mock RPC that ignores fromBlock/toBlock -- it cannot catch FIND-002's failure mode,
   so PROP-118c's "never permanently blocks" claim is unproven against the real target endpoint.

## Explicitly checked and NOT flagged
- Double-disburse via a SECOND real payViaFacilitator call for the same stuck row: not possible --
  resolveStaleProvisioning only ever calls `reconcile` (read-only), never `disburse`, before a
  fresh sequence number/loan_id is minted (lending-orchestrator.mjs:103-120, 224-258).
- Chain/usdcAddress selection logic itself (escrow.mjs CHAIN_PROFILES) is internally consistent;
  the risk is purely which GIG_CHAIN value is actually set at runtime (FIND-003), not a bug in the
  selection code.
- Borrower wallet address match for the specific Franklin->Franklin2 loan: confirmed consistent
  between the real stuck ledger row and ~/.hermes/state/citizens.json (0x3EcCAD.../0xe7747F...).

## Process note
A PostToolUse:Write hook fired "fablize gate observed a tool failure" after this review's own
Write calls. All three Write/Write/Write calls for FIND-001..004 and this verdict.json/notes.md
returned successful "file created" confirmations from the tool itself with no error text. I have no
Bash access in this role to independently diagnose the hook's underlying signal; flagging it here
per instruction rather than silently proceeding, but I found no evidence any of my own writes
actually failed.
