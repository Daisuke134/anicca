# economy/gig — the internal gig loop (SPEC.md §3 P2.2)

The minimal working agent-economy transaction: one agent POSTS a paid gig (bounty into x402 escrow) →
another agent TAKES it → delivers → poster verifies → **gasless payout to the taker** via the
already-running self-host x402-rs facilitator (`services/facilitator`, P2.1). This is what lets a
funded agent (e.g. automaton) employ a broke agent (e.g. Franklin) so the broke agent earns its first
income (SPEC.md §3 P2 DECISION A).

## What's here

- `lib/store.mjs` — pure state-machine (post→open→taken→delivered→paid|rejected). No fs, no network.
  Unit-tested in isolation (`__tests__/store.test.mjs`).
- `lib/escrow.mjs` — pays USDC through the facilitator's `/verify`+`/settle` (same EIP-3009
  `transferWithAuthorization` flow proven in `services/facilitator/scripts/settle-test.mjs`), waits for
  on-chain confirmation before reporting success, retries transient `insufficient_funds` (RPC lag).
- `lib/identity.mjs` — ERC-8004 identity: `registerIdentity()` (mint), `verifyIdentity()` (on-chain
  ownership check) against the **live** ChaosChain reference-implementation `IdentityRegistry` on Base
  Sepolia — see "ERC-8004 identity" below.
- `lib/lock.mjs` — per-gig file lock so concurrent calls on the SAME gig can't race past each other
  (see "Security fixes, round 2" below), with a heartbeat so a live holder is never mistaken for a
  crashed one (round 3, see "Security fixes, round 3").
- `lib/persist.mjs` — JSON state file read/write (`state/gigs.json`, gitignored).
- `gig.mjs` — orchestration: the 5 operations, combining the above, with poster-auth + ERC-8004 gating
  + per-gig locking (round-2 security fixes) + a fresh-read-before-write board lock so unrelated gigs'
  saves can never clobber each other (round 3).
- `mcp-server.mjs` — MCP stdio server exposing the 5 operations + 2 identity tools to Franklin.
- `scripts/e2e-testnet.mjs` — real, no-mock full-loop proof on Base Sepolia, INCLUDING re-proof that
  both adversary-found drains now fail (see "Security fixes, round 2").
- `scripts/fund-agents.mjs` — one-off ETH gas drip (from the facilitator's own signer) so a test
  poster/taker wallet can pay for its own ERC-8004 `register()` tx.

## Escrow model (documented limitation)

"Escrow" here = a custody keypair the gig-board process itself holds (`GIG_ESCROW_PRIVATE_KEY`), not a
Solidity escrow contract. Funds move in two real on-chain settles per completed gig:

1. **`gig_post`**: poster → escrow (immediate, funds the bounty; if this settle fails, no gig is
   created).
2. **`gig_verify_and_pay(verified:true)`**: escrow → taker (only if the poster approves).

Fail-closed release is enforced in `lib/store.mjs` (`applyVerifyAndPay` refuses to mark a gig `'paid'`
without a real `payoutTx` already in hand) and in `gig.mjs` (payout is only ever attempted when
`verified === true`, and a failed settle leaves the gig in `'delivered'` — not falsely `'paid'` — so it
can be retried). **No-verify → no-pay.** Upgrading this custody model to an on-chain escrow contract
(so no single process holds the funds) is a documented future step, not required for the P2.2 MVP.

**Round-2 hardening (see "Security fixes, round 2" below)**: `gig_verify_and_pay` additionally requires
proof the caller IS the gig's poster (a private key, not just a boolean), and the whole
load→decide→settle→save sequence for `gig_take`/`gig_deliver`/`gig_verify_and_pay` runs inside a
per-gigId file lock so concurrent calls can't both reach a real settle.

## ERC-8004 identity

Each agent registers its OWN identity by calling `register()` directly via viem (no
`create-8004-agent` scaffold — confirmed broken per SPEC.md §1.2: tsc errors + Pinata dependency). We
reuse the **already-live** reference-implementation deployment
(`ChaosChain/trustless-agents-erc-ri`, CC0-1.0) instead of deploying our own contract:

```
IdentityRegistry (legacy v1.1.0, base-sepolia, chainId 84532):
  0xdc527768082c489e0ee228d24d3cfa290214f387
```

Confirmed live 2026-07-07 via `eth_call name()` → `"ERC-8004 Trustless Agent"` (matches the ERC-721
constructor name in `src/IdentityRegistry.sol`). `register()`/`ownerOf()`/`agentExists()` are unchanged
between this legacy v1.1.0 deployment and the current v1.2.0 main-branch source (the Jan-2026 update
only touched `unsetAgentWallet`/Reputation/Validation), so the current ABI is accurate here. `register()`
is **not** gasless (no relayed/meta-tx path in this contract) — each agent needs a small amount of Base
Sepolia ETH to register itself; `scripts/fund-agents.mjs` provisions that from the facilitator's own
signer (which already holds bridged testnet ETH from P2.1).

**Gotcha**: immediately after a `register()` tx confirms, `ownerOf()` calls against the public
`sepolia.base.org` RPC can transiently revert with `"ERC721: invalid token ID"` even though the mint
definitely succeeded — reproduced twice in the E2E run, and confirmed (by re-querying moments later) to
be RPC-node propagation lag (public RPC providers load-balance across backend nodes without strict
read-your-writes consistency), not a real defect. A caller that needs an immediate post-register
verification should retry `verifyIdentity()` a few times before giving up.

## lucid-agents (reviewed, not forked)

Reviewed `daydreamsai/lucid-agents`'s `packages/{catalog,payments,ident, ...}` for reusable patterns
per SPEC.md's "do not reinvent" instruction. Its actual shape is a **fixed-price catalog of x402-priced
HTTP entrypoints** (`catalog()` turns a YAML/CSV price list into routes) — a different workflow from a
**take/deliver/verify bounty board**, and its own CLI trading-agent scaffold is confirmed broken (SPEC
§1.2, reproduced in a prior session) and has no gig-style escrow release gate. `packages/payments`
confirms the same `x402-fetch`/EIP-3009 pattern our facilitator scripts already use — no new pattern to
adopt there. Given the mismatch + the broken scaffold, P2.2 is a purpose-built gig board directly on
the already-working facilitator rather than a fork.

## Running

```bash
cd services/facilitator && ./start.sh   # P2.1 facilitator must be up (127.0.0.1:8405)

set -a
source ~/.anicca-signing/x402-facilitator/.env   # FACILITATOR_PRIVATE_KEY, TEST_PAYER_*
source ~/.anicca-signing/gig-board/.env          # GIG_ESCROW_*, GIG_TAKER_* (test wallets)
set +a
export GIG_ESCROW_ADDRESS GIG_ESCROW_PRIVATE_KEY

npm test                          # unit tests (pure logic, no network)
node scripts/e2e-testnet.mjs       # real testnet full loop
```

## E2E evidence (Base Sepolia, real tx, 2026-07-07)

Full loop run via `scripts/e2e-testnet.mjs`:

| step | result |
|---|---|
| poster ERC-8004 register | agentId `8`, tx `0x5f6ef20a68b1a2106da8830208b29e85cba9f0e0174e64b008f1f3cabbcc4e6b` |
| taker ERC-8004 register | agentId `9`, tx `0x7a76e308bbe97345b936704579f6c3f19c602e22c2705666dcf3f1704459fe36` |
| `ownerOf(8)` verify | `true` (poster address) |
| `ownerOf(9)` verify | transient RPC lag on first check, `true` on recheck (see Gotcha above) |
| `gig_post` (poster funds escrow) | tx `0xaceb134d749d624188e0eed6a6280260612b8af861f62dbb00099a3cc1e5ea44` |
| `gig_take` | taker assigned, status `taken` |
| `gig_deliver` | deliverable recorded, status `delivered` |
| `gig_verify_and_pay(true)` (escrow releases to taker) | **paid**, tx `0x17e4d4aa330ed5a4aaf3e5f5f926a4841c9a11958dfd1d7981de01ab04e32f6f` |

Balances after the run confirm the accounting exactly: escrow `0.001 USDC` (residual from an earlier
aborted run's unfunded-release attempt, before the confirmation-wait fix below), taker `0.001 USDC`
(the real payout from this run).

**Bug found + fixed during this E2E**: the very first run failed `gig_verify_and_pay` with
`insufficient_funds` moments after a real, successful escrow-funding settle — the facilitator's
`/settle` response only confirms the tx was *broadcast*, and the immediately-following settle's own
on-chain balance preflight raced ahead of confirmation. Fixed in `lib/escrow.mjs`'s `settleBody()`:
it now calls `publicClient.waitForTransactionReceipt()` and only reports `ok:true` once the settle tx
is actually mined. Re-ran clean afterward — see table above.

## Security fixes, round 2 (adversary found 2 real live drains)

A fresh-context adversary reviewed this skill and drained the escrow LIVE, twice, against the round-1
code:

1. **No poster auth** (critical): `gig_verify_and_pay` checked ZERO caller identity — the taker itself
   took a gig, delivered garbage, and called `verify_and_pay(true)` on itself, draining the escrow (real
   tx `0x78111fa62b82d9e94b2f7609cca40592e7cd824991c4a3667cf99b6572e68555`, paid to a separate attacker
   wallet `0xc7d7dec0be728d930d777aaec5afe114e197d8c1`).
2. **Double-pay race** (critical): no lock around `gigVerifyAndPay`'s load→(network wait)→save. Two
   concurrent `verify_and_pay(true)` calls on one gig BOTH paid (real tx
   `0xd0af29c3c0c119d62f32c48c3e63273db0344fb58fbc68962afd9c03ef59fc08` +
   `0x6573886bc22ac7a39ce9e22db0ed1864a5c32b83227563d3dcd8b794018f7e54`), the JSON ledger only recorded
   one (last-write-wins).
3. **ERC-8004 decorative**: identity registration worked, but nothing in the gig lifecycle ever checked
   it — strangers weren't actually protected.

**Fixes** (all in `gig.mjs`, see the file's own header comment for the finding→fix map):

- **Finding 1**: `gig_verify_and_pay` now requires `posterPrivateKey`; its derived address (the same
  `privateKeyToAccount` primitive `gig_post` already uses) must equal `gig.poster` or the call is
  rejected — a taker/attacker/anyone else can never verify their own delivery. (This also closed a
  related spoofing gap: `gig_post` used to accept an independently-claimed `posterAddress` that didn't
  have to match the signing key; the poster's address is now ALWAYS derived from the key, never a
  separate claim.)
- **Finding 2**: `lib/lock.mjs` — a per-gigId POSIX-exclusive file lock (`fs.open(path, "wx")`, atomic
  across processes, not just within one). The entire load→decide→settle→save sequence for
  `gig_take`/`gig_deliver`/`gig_verify_and_pay` runs inside the lock; a concurrent call for the same
  gig is rejected immediately (fail-closed, never queued), so at most one call ever reaches a real
  settle. `gig_post`'s shared `nextId` counter got the same treatment under a fixed `"_post"` lock key.
- **Finding 3**: `gig_post` requires `posterAgentId` (verified on-chain against the poster's own
  derived address before any funds move); `gig_take` requires `takerAgentId` (verified against
  `takerAddress` before the gig can be taken); `gig_verify_and_pay` RE-verifies the taker's identity at
  payout time (not just trusting take-time), so a since-invalidated identity blocks payout too.

**RED→GREEN evidence**: `__tests__/gig.test.mjs` (new, 7 tests, orchestration layer — the layer where
all 3 bugs lived; `store.mjs`'s 10 tests never touched this code). Each finding's fix was temporarily
reverted and the exact corresponding test (and only that test) failed, then restored to green — see
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-security-fixes.md` for the full transcripts.

**Real testnet re-proof** (`scripts/e2e-testnet.mjs`, updated to attempt both attacks for real against
the fixed code):
- GIG A: the taker called `gig_verify_and_pay(true)` on itself → **rejected**
  (`"caller ... is not the poster ..."`); the real poster then paid successfully, tx
  `0x701e638cd0dc322c700dd90bf128334a20c24dddba5bd24f6ab6b3a40f4c2476`.
- GIG B: two concurrent REAL `gig_verify_and_pay(true)` calls fired via `Promise.all` → exactly one
  paid (tx `0x5b34159acdf5e90b5575c77ee9bdfef76006d07c7f63b0d88106074fd2c7eeb4`), the other rejected
  with a lock-contention message.
- **On-chain reconciliation** (`eth_getLogs` over the escrow address's full Transfer history, both
  directions): 7 deposits in / 7 releases out, net-zero, exactly matching every individual tx this
  session PLUS the adversary's own 3 drain transactions from their earlier report — no unaccounted-for
  transfer anywhere. Full ledger in the evidence file.

Also found + fixed live during this re-proof run: the SAME transient RPC-propagation-lag class (see
"Gotcha" above) hit the facilitator's own internal balance preflight this time (not just our
`ownerOf()` reads) — a legitimate, already-funded release failed `/verify` with `insufficient_funds`
seconds after its funding tx had a confirmed receipt. Fixed with a bounded retry+backoff
(`lib/escrow.mjs`'s `verifyWithRetry`, 3 attempts / 3s+5s+8s) scoped specifically to that one
transient reason string — confirmed it resolves the race without masking a genuine insufficient-balance
error (only retries when the reason is `insufficient_funds`; any other rejection fails immediately).

## Security fixes, round 3 (2 residual concurrency gaps — not fund-theft, but real data-loss bugs)

A second adversary pass over the round-2 fix confirmed all 3 fund-drain findings closed, but found 2
concurrency gaps that would bite once automaton + Franklin are separate concurrent launchd loops
sharing this board:

- **GAP 1 (stale-lock steal)**: `lib/lock.mjs`'s `STALE_MS=30000` let a second caller STEAL a lock
  after 30s even from a holder that was still genuinely (legitimately) working — a real settle+retry
  sequence measured at 16.79s plus network/confirmation on top can exceed 30s under congestion,
  reopening the finding-2 double-pay race.
- **GAP 2 (cross-gig shared-state clobber)**: the per-gigId lock never protected the SHARED
  `state/gigs.json` file — `persist.mjs` is a full-file overwrite with no version check, so a slow
  operation on gig X would compute its save from a state snapshot taken BEFORE its slow network step,
  and that late save would silently revert a concurrent `gig_take` on an unrelated gig Y back to
  `'open'` — the legit taker's assignment would vanish from the persisted board.

**Fixes**:

- **GAP 1**: `lib/lock.mjs`'s `withGigLock` now HEARTBEATS the lock file's mtime (every `heartbeatMs`,
  default 5s) for as long as `fn()` is running, so a LIVE holder's lock never looks stale to anyone
  else — staleness (`staleMs`, default 60s, raised from 30s) now only ever indicates a genuinely dead
  (crashed) holder, never a merely slow one. Both are injectable for fast, deterministic testing.
- **GAP 2**: `gig.mjs`'s new `applyAndSave()` is now the ONLY place that ever writes to disk — it
  re-reads the board FRESH from disk immediately before applying a mutation, inside a dedicated global
  `"_board"` lock. The (possibly slow) network settle still only holds the per-gigId/`"_post"` lock;
  the board lock is held only for the brief local read-mutate-write, so unrelated gigs still process
  concurrently, but no write can ever be computed from data older than the instant it's persisted.

**RED→GREEN**: 4 new tests — `__tests__/lock.test.mjs` (3: heartbeat prevents steal-while-alive, a
genuinely dead holder's lock IS reclaimable, unrelated lock keys never contend) +
`__tests__/gig.test.mjs`'s `★GAP 2★` test (a slow verify_and_pay on gig X, racing a concurrent take on
gig Y, confirms Y's take survives in the final persisted board). Each gap's specific mechanism (the
heartbeat; the fresh-read-before-write) was temporarily reverted and the exact corresponding test (and
only that test) failed, then restored — full suite 21/21 green. See
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-security-fixes-round3.md` for transcripts.

**Real testnet re-proof**: re-ran the full `scripts/e2e-testnet.mjs` (both attack re-proofs from round
2) against the round-3 code — both still correctly rejected/serialized (self-verify attack rejected;
concurrent real settles → exactly 1 paid). On-chain reconciliation of the escrow address still nets
out exactly (deposits − releases = current balance; releases to the taker = taker's current balance) —
no hidden double-payout anywhere, across the full combined history (rounds 1–3 plus the adversary's own
testing).

## Wiring to Franklin (MCP) — NOT applied here, witness step for the team lead

Franklin's own MCP loader (`@blockrun/franklin`, `dist/mcp/config.js`) reads
`~/.blockrun/mcp.json`'s `"mcpServers"` map at startup — add this entry (do not edit the live file from
this worktree; this is the exact snippet to apply, AFTER the gig subsystem has been deployed to
`~/.blockrun/skills/economy/gig/` per WITNESS-RUNBOOK.md — the path here must point at that deployed
copy, not this worktree or the un-populated main `the canonical checkout` checkout):

```json
{
  "mcpServers": {
    "anicca-gig": {
      "transport": "stdio",
      "command": "/opt/homebrew/bin/node",
      "args": ["/home/life-manager/.blockrun/skills/economy/gig/mcp-server.mjs"],
      "env": {
        "GIG_ESCROW_ADDRESS": "0x...",
        "GIG_ESCROW_PRIVATE_KEY": "0x...",
        "GIG_FACILITATOR_URL": "http://127.0.0.1:8405",
        "GIG_STATE_PATH": "/home/life-manager/.anicca-signing/gig-board/state/gigs.json",
        "GIG_CHAIN": "base-sepolia"
      }
    }
  }
}
```

Exposes 7 tools: `gig_post`, `gig_list`, `gig_take`, `gig_deliver`, `gig_verify_and_pay`,
`identity_register`, `identity_verify`. Franklin itself is not modified — this only adds a server entry
(SPEC.md §9.1: "Franklin に append, original shit でない").

**`GIG_STATE_PATH` is REQUIRED here** (not optional) — without it, Franklin's copy of `gig.mjs` defaults
its board file to a location next to ITS OWN `mcp-server.mjs` (i.e. inside `~/.blockrun/`), completely
separate from automaton's copy's own default board file (inside `~/.anicca/`) — the two would never see
each other's gigs. Both deployed copies MUST point `GIG_STATE_PATH` at the SAME shared file. **Gotcha**:
Franklin's MCP loader auto-`disabled`s any server whose `env` contains a path ending in `.json`/`.key`/
`.pem` that doesn't exist yet at config-load time (`dist/mcp/config.js`'s credential-file heuristic) — the
shared `GIG_STATE_PATH` file (and its parent dir) must already exist (e.g. `echo '{"nextId":1,"gigs":{}}'
> $GIG_STATE_PATH`) BEFORE Franklin next reads `mcp.json`, or this server silently gets `disabled: true`.

## Tests

```bash
npm test   # node --test __tests__/*.test.mjs
```

21/21 pass:
- `__tests__/store.test.mjs` (10) — pure lifecycle transitions + the ★core★ fail-closed guarantee:
  `applyVerifyAndPay` refuses to mark a gig `'paid'` without a real `payoutTx`.
- `__tests__/gig.test.mjs` (8, 7 from round 2 + 1 from round 3) — orchestration-layer tests with
  injected fake `pay`/`verifyIdentityFn` (fast, deterministic, no real network): non-poster rejection
  (finding 1), concurrent-call double-pay prevention (finding 2), ERC-8004 identity gating at
  post/take/payout-time (finding 3), cross-gig shared-state clobber prevention (round-3 gap 2).
- `__tests__/lock.test.mjs` (3, new in round 3) — `lib/lock.mjs` unit tests: a live holder's heartbeat
  prevents its lock from being stolen (gap 1), a genuinely dead holder's lock IS reclaimable, unrelated
  lock keys never contend.

Every guard in all three files was verified RED→GREEN by temporarily reverting it and confirming the
exact corresponding test (and only that test) fails, then restoring — see
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-security-fixes.md` (rounds 1-2) and
`.vcsdd/features/anicca-agent-economy/evidence/p2.2-security-fixes-round3.md` (round 3) for the
transcripts.
