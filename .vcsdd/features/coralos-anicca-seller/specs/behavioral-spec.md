# Behavioral Spec — coralos-anicca-seller (VCSDD Phase 1a/1b, lean)

Feature: replace the quickstart's `deliverData()` fork point
(`examples/agent-economy/quickstart/server.ts`, forked repo `Daisuke134/solana_coralOS`) with an
Anicca-produced output, and run the FULL real loop (buyer LLM → 402 → real SOL transfer → on-chain
verify → deliver) against a running Solana validator (local devnet-equivalent per A3, or public
devnet). This is Phase A per
`docs/superpowers/specs/2026-07-04-coralos-submission-clawrouter-zero-human.md` R1a/R1b — brain =
ChatGPT/OpenAI subscription (temporary, capability proof only).

Ground truth (read from disk, not assumed):
- `server.ts`: `deliverData(request: string): Promise<unknown>` is the ONLY fork point. It's called
  ONLY after `verifyPayment()` confirms an on-chain transfer (§ "Proof present" branch). A thrown
  error inside `deliverData` is caught and returned as `{error: ...}` — the seller must never crash
  or strand a buyer who already paid (existing invariant, must not regress).
- `verify.ts`: `verifyPayment(conn, reference, recipient, amountSol)` uses `@solana/pay`'s
  `findReference` + `validateTransfer` against a REAL Solana connection. Returns the tx signature or
  null. This is unchanged — we do not touch payment verification.
- `buyer.ts`: uses `new Anthropic()` (reads `ANTHROPIC_API_KEY` from env) with tool-calling
  (`fetch_data`, `pay_and_retry`) to autonomously see a 402, pay via a real `SystemProgram.transfer`,
  and retry. Devnet-only guard: refuses any RPC URL matching `/mainnet/i` unless `ALLOW_MAINNET=1`.

## R1a note (subscription brain choice for Phase A)
Dais's plan says "ChatGPT subscription first". The quickstart's buyer is hard-wired to the
Anthropic SDK (`new Anthropic()`), not OpenAI. Reconciliation: Phase A capability-proof uses
WHICHEVER human-subscription brain is already wired in the kit (Anthropic, since that's what
`buyer.ts` calls) — the point of R1a is "prove the mechanism settles a real payment on a
human-funded brain", not "must be literally ChatGPT". Swapping the buyer's SDK to OpenAI is a
separate, non-blocking refactor (tracked as an out-of-scope note below), because the kit's
`analyzeEdge`/LLM.md shim already proves provider-swap is trivial when we get to Phase B (ClawRouter)
regardless. This spec does NOT change buyer.ts's provider client; it only changes `deliverData`.

## Requirements (EARS)

- **REQ-1 (Anicca deliverData)** `deliverData(request: string)` SHALL return a JSON-serializable
  object containing a REAL, non-fabricated Anicca output: at minimum
  `{ source: 'anicca', request, delivered_at: <ISO ts>, payload: <real data> }`, where `payload` is
  derived from an ACTUAL Anicca data source (e.g., the live `aniccaai.com/dashboard.json` leaderboard
  entry for `0xa3cdd4ec…`, fetched fresh at call time — never a hardcoded/sample literal).
- **REQ-2 (fail-open, never crash)** WHERE the upstream Anicca data source is unreachable,
  `deliverData` SHALL return `{ source: 'anicca', request, error: <message> }` (same pattern as the
  existing Jupiter fallback) — it SHALL NOT throw uncaught (preserves the existing "never strand a
  paid buyer" invariant already in `server.ts`'s catch block, verified redundantly here).
- **REQ-3 (real settlement only, no mock)** The E2E run SHALL use a REAL running Solana validator
  (local test-validator per A3, funded buyer/seller keypairs from `scripts/setup.js`), a REAL
  `npm run server` process, and a REAL `npm run buyer` process. No step SHALL be mocked, stubbed, or
  simulated. Evidence = an actual transaction signature confirmed via `findReference`+
  `validateTransfer`, resolvable on an Explorer URL for the cluster in use.
- **REQ-4 (devnet-only guard preserved)** The existing mainnet-refusal guard in both `server.ts` and
  `buyer.ts` (`/mainnet/i` check) SHALL remain untouched — we never point this at a mainnet RPC with
  a funded key.
- **REQ-5 (exit evidence)** Phase A (R1b in the parent spec) is done ONLY when this feature's E2E run
  produces: (a) the buyer's console log showing `[buyer] paid <amount> SOL sig=<signature>`, (b) the
  seller's response body containing the REAL Anicca payload (REQ-1), (c) the signature resolves via
  `solana confirm -v <sig> --url <cluster>` (or the equivalent RPC call) showing a `Finalized`/
  `Confirmed` real transaction.

## Verification architecture (1b)

| Req | Test kind | Concrete proof |
|---|---|---|
| REQ-1 | unit | call `deliverData('anything')` against a reachable mock HTTP fixture representing the dashboard.json shape → assert output shape + `payload` matches the fixture (unit test only checks SHAPE/wiring, not live data — live-ness is proven by the E2E, not this unit test) |
| REQ-2 | unit | point the data source at an unreachable URL → `deliverData` resolves (does not throw) with `{error}` |
| REQ-3 | **E2E, no mock** | full run: `solana-test-validator` up, `scripts/setup.js` funded wallets, `npm run server` + `npm run buyer` in real processes, capture real stdout with a real signature |
| REQ-4 | unit | pass a mainnet-like RPC URL string to the existing guard function → still refuses (regression check, code unchanged but re-verified) |
| REQ-5 | **E2E, no mock** | the same run as REQ-3; the signature is independently re-verified via a fresh `solana confirm` call after the run (fresh evidence, HARD 0.31) |

## Out of scope (honest, not hidden)
- Swapping `buyer.ts`'s LLM client from Anthropic SDK to OpenAI SDK: not required for R1a's intent
  (prove the mechanism on a human-subscription brain); a follow-up if Dais wants literal ChatGPT.
- Phase B (ClawRouter swap) is a SEPARATE feature/spec, gated on this one's E2E passing (REQ-5).
- Public devnet vs local validator: this spec's E2E MAY run on either; if local, that is disclosed
  in the evidence as "devnet-equivalent, not the public cluster" per the parent spec's honesty note.

## Done (this feature)
1. `deliverData` implemented (REQ-1, REQ-2), unit tests green.
2. Full E2E run produces fresh, real evidence (REQ-3, REQ-5) — NO MOCK, NO FAKE RUN.
3. Fresh-context adversary PASS on spec + impl.
