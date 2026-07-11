# E2E status — Base Sepolia (spec §5)

**Status: NOT-RUN.**

**Exact blocker**: this build task's own MONEY-SAFETY boundary explicitly states "NEVER touch/read/print
wallet keys, .env, .solana-session, ledger.mjs, spend caps... any violation = abort+report". Running the
real E2E script (`skills/economy/gig/scripts/e2e-reputation-testnet.mjs`) requires a Base
Sepolia-funded EVM private key exported into the environment. Obtaining or reading such a key (from
`.env`, `~/.anicca-signing/`, or any other credential store) is out of scope for this session under that
constraint — this is a structural exclusion, not a "couldn't find a key" failure.

**What IS verified this session (real, not simulated)**:
- The two Reputation Registry addresses (mainnet `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`,
  base-sepolia `0x8004B663056A597Dffe9eCcC1965A193B7388713`) were confirmed LIVE via direct
  `eth_call`/`readContract` this session (not guessed) — see `reputation.mjs`'s own header comment for
  the exact `getVersion()`/`getIdentityRegistry()` return values and how they were cross-checked against
  `identity.mjs`'s own already-live mainnet registry.
- The known base-sepolia identity-registry mismatch (Reputation Registry checks against
  `0x8004A818...`, not `identity.mjs`'s default `0xdc5277...`) was discovered and documented via real
  reads, not assumed — this is WHY the E2E script registers a fresh throwaway agentId directly against
  the Reputation-linked registry rather than reusing `identity.mjs`'s default testnet flow.
- All pure-logic and DI-faked-network unit tests (PROP-001..041, this feature's own 29 new tests + the
  pre-existing 80+162 regression tests) pass — see `evidence/sprint-1-green-phase.log`.

**What is NOT verified**: no real testnet transaction was submitted in this session. PROP-043/044/045
(the three live-chain E2E items from spec §5) remain open. Before this feature is claimed "done" against
the design spec's own definition (§1 G1/G2 "done = ... E2E ログ"), a separate, explicitly money-authorized
session/operator must run `e2e-reputation-testnet.mjs` with a funded Base Sepolia key and attach its
output here.
