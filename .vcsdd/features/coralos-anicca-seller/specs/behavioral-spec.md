# Behavioral Spec v2 — coralos-anicca-seller (VCSDD Phase 1a/1b, lean)

**v2 corrects a critical error caught by the sonnet-5 spec adversary (round 1, FAIL, all 5 dims).**
v1 targeted `examples/agent-economy/quickstart/server.ts` — the repo's own README
(`examples/agent-economy/README.md`, "No Docker? — the quickstart") explicitly calls this the
**pay-first, no-escrow fallback**, contrasted against "Want trustless settlement? — the escrow"
(`examples/txodds/escrow/README.md`). The parent submission spec's R5 requires the REAL
WANT→BID→AWARD→DEPOSIT→DELIVER→RELEASE escrow loop. Submitting the quickstart would have been
**a false claim of what CoralOS demands** — caught before any submission happened, per Dais's
"don't fake it, god is watching" directive (2026-07-04).

## Ground truth (re-verified from disk, this round)

- **Escrow is ALREADY DEPLOYED to public devnet.** `examples/txodds/escrow/README.md:6-8`: Program ID
  `R5NWNg9eRLWWQU81Xbzz5Du1k7jTDeeT92Ty6qCeXet` (Explorer-verified), arbiter wrapper
  `FJtuVXsyXuRKqgJBEPAXmktkd13CqStapgevzGwYktXd`. This means: **a local `solana-test-validator`
  CANNOT be used for the real escrow flow** — the deployed program only exists on the public
  devnet cluster. A2/A3's earlier local-validator workaround (done for the wrong fork point) does
  NOT carry over to this corrected target. This spec's E2E MUST run against public devnet.
- **The correct fork point is `coral-agents/seller-agent/src/service.ts::deliverService(request:
  string): Promise<string>`** (verified by reading the file this round) — NOT quickstart's
  `deliverData`. Its current body calls TxLine's API + `@pay/agent-runtime`'s `complete()`
  (provider-agnostic LLM shim per LLM.md) and falls back to a `deterministicRead` on LLM failure
  (an existing "never crash" pattern we must preserve, same discipline as v1's REQ-2).
- **The proxy that actually settles the escrow is `examples/txodds/server/proxy.ts`** (read in
  full this round): `ensureToken()` subscribes the buyer wallet to TxLine's free tier on-chain (a
  real devnet tx), then `/api/settle` (further down the file, not yet read in full — MUST read
  before GREEN) drives `deposit → deliverService (or the proxy's own analyzeEdge) → release` through
  `../agent/arbiter.ts` (`makeArbiter`, `arbiterOpen`, `arbitrateRelease`) — this is the REAL
  escrow lifecycle the parent spec's R5 demands.
- **Public devnet airdrop is rate-limited/exhausted** (verified live 2026-07-04: direct RPC
  `requestAirdrop` → `429 Too Many Requests`, official `solana airdrop` CLI → same). The faucet
  page itself (`faucet.solana.com`) tells AI agents NOT to use the web UI and instead offers: (a)
  `solana airdrop <n> <addr> --url devnet` (same rate limit, already tried), (b) a **Proof-of-Work
  faucet** (`cargo install devnet-pow` — blocked locally by a disk-space crunch during this
  session, retry after disk hygiene), (c) `solana-test-validator` (NOT applicable here since the
  escrow program only lives on public devnet, not local). **Action: retry the PoW faucet now that
  disk is clear (7.2Gi freed), OR find/use an already-funded devnet wallet, OR wait out the public
  faucet's rate-limit window and retry `solana airdrop`.**

## Requirements (EARS) — supersede v1's REQ-1..5

- **REQ-1 (correct fork point)** The implementation SHALL modify
  `coral-agents/seller-agent/src/service.ts::deliverService` (or, if the E2E path actually runs
  through `examples/txodds/server/proxy.ts`'s inlined delivery rather than the coral-agents
  package — TO BE CONFIRMED by fully reading `proxy.ts`'s `/api/settle` handler before GREEN — that
  file instead) to return an Anicca-produced payload instead of the TxLine odds/edge read.
- **REQ-2 (preserve the deterministic-fallback invariant)** WHERE the Anicca data source is
  unreachable, the function SHALL return a deterministic, non-throwing fallback (mirrors the
  existing `deterministicRead` pattern) — never crash, never strand a buyer mid-escrow.
- **REQ-3 (real public-devnet settlement, no mock, no local-validator substitution)** The E2E run
  SHALL execute against Solana **public devnet** (`https://api.devnet.solana.com` or an equivalent
  devnet RPC) because the escrow + arbiter programs are deployed there and nowhere else. No step
  mocked/stubbed. Evidence = a real transaction signature for EACH stage of
  WANT→BID→AWARD→DEPOSITED→DELIVERED→RELEASED, each resolvable at
  `https://explorer.solana.com/tx/<sig>?cluster=devnet`.
- **REQ-4 (devnet-only guards preserved)** Existing mainnet-refusal guards (seen in v1's read of
  `server.ts`/`buyer.ts`; re-verify the equivalent guard exists in `proxy.ts` /
  `coral-agents/seller-agent`) remain untouched.
- **REQ-5 (funding is a precondition, tracked honestly)** Before REQ-3 can run, the buyer wallet
  MUST hold devnet SOL. This spec does NOT claim REQ-3 is done until real funding is confirmed via
  `solana balance <addr> --url devnet` showing > 0, by one of: PoW faucet, a pre-funded wallet, or
  a successful rate-limit-window retry. This is a BLOCKING precondition, explicitly tracked, not
  glossed over.
- **REQ-6 (exit evidence, replaces v1 REQ-5)** Phase A / parent-spec R1b is done ONLY when: (a) a
  real Explorer link for the DEPOSIT tx, (b) a real Explorer link for the RELEASE tx, (c) the
  seller's delivered payload contains the real Anicca output (REQ-1), all captured as fresh
  evidence in this feature's evidence log — not asserted, not pasted from memory.

## Verification architecture (1b)

| Req | Test kind | Concrete proof |
|---|---|---|
| REQ-1 | unit | `deliverService('anicca')` (or whatever request string routes to it) returns Anicca payload shape; existing TxLine routing for other request strings unaffected (regression) |
| REQ-2 | unit | inject an unreachable Anicca source → function returns the deterministic fallback shape, never throws |
| REQ-3 | **E2E, public devnet, no mock** | run the real proxy/escrow flow against `https://api.devnet.solana.com`; capture EVERY stage's tx signature |
| REQ-4 | unit | mainnet-URL guard still refuses (regression) |
| REQ-5 | **manual/E2E precondition check** | `solana balance <buyer> --url devnet` > 0, captured BEFORE attempting REQ-3, with the funding method noted (PoW / pre-funded / faucet-retry) |
| REQ-6 | **E2E, no mock** | evidence log contains the 2 Explorer links + the delivered Anicca payload, dated, from an actual run in this session |

## Reconciliation with A1-A4 (work already done, still valid)

- A1 (fork exists) — valid, unaffected by fork-point correction.
- A2 (monorepo build fix for `packages/agent-runtime`) — valid and REUSED: `coral-agents/seller-agent`
  also depends on `@pay/agent-runtime`; the same build fix applies.
- A3 (local-validator funding) — **superseded**: that funded wallet is only useful on the local
  validator, which cannot run the real escrow (program not deployed there). A3's technique (install
  `solana-test-validator`, generate/fund via `solana airdrop`) remains available as a fallback ONLY
  for a future quickstart-style demo, NOT for this corrected target.
- A4 (OpenAI key wired for Phase A) — valid; `@pay/agent-runtime`'s `complete()` shim is
  provider-agnostic per LLM.md, so this still applies to `coral-agents/seller-agent`'s
  `complete()` call once we confirm the provider env var naming there.

## Out of scope (honest)
- Phase B (ClawRouter) is gated on this spec's REQ-6 passing — unchanged from v1's ordering.
- If public-devnet funding cannot be obtained in this session (PoW faucet blocked, rate limits not
  clearing), this is disclosed as a BLOCKED status, not worked around with a local-validator
  substitute that would misrepresent the settlement as satisfying R5.

## Done (this feature, v2)
1. Fully read `examples/txodds/server/proxy.ts`'s `/api/settle` handler + `agent/arbiter.ts` to
   confirm the EXACT escrow call sequence before writing GREEN code.
2. `deliverService` (or the confirmed equivalent) returns Anicca's real output (REQ-1, REQ-2), unit
   tests green.
3. Public-devnet funding confirmed (REQ-5) — BLOCKING, must be true before E2E.
4. Full E2E run on public devnet produces fresh, real Explorer-linked evidence (REQ-3, REQ-6).
5. Fresh-context adversary PASS on this v2 spec AND the impl.
