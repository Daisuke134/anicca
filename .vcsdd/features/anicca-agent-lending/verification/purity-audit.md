# Purity Boundary Audit — anicca-agent-lending (Phase 5, Formal Hardening)

## Declared Boundaries

Per `specs/verification-architecture.md`'s own "Purity Boundary Map" (lines 9-40):

| File | Declared purity |
|---|---|
| `lending-gate.mjs` | Pure Core — every exported function, zero I/O |
| `lending-path.mjs` | Pure Core (constant only) — `LOANS_LEDGER_PATH`, computed once at module load, no runtime logic |
| `gojo-read.mjs` | Effectful Shell (new, read-only) — `fs.readFileSync` only, never writes |
| `lending-verify.mjs` | Effectful Shell (new) — JSON-RPC `fetch` calls only, no filesystem access |

`contracts/sprint-1.md`'s own CRIT-001/CRIT-009 criteria (already adversary-PASSed) restate this exact
same boundary as a binding sprint-1 acceptance criterion.

## Observed Boundaries (this session's own independent re-verification)

Ran directly against the delivered source (not re-trusting Phase 3's own prior confirmation):

```
cd ~/anicca/skills/economy/lending/lib
grep -n -F "fs."                                    *.mjs   -> 1 hit:  gojo-read.mjs:10 (fs.readFileSync)
grep -n -F "fetch("                                 *.mjs   -> 1 hit:  lending-verify.mjs:17 (inside rpcCall())
grep -n -F "Date.now()"                             *.mjs   -> 0 hits
grep -n "^import"                                   *.mjs   -> 4 hits: gojo-read (fs), lending-gate (isSelfFunded only),
                                                                        lending-path (path, url); lending-verify has NO import
                                                                        statements at all (uses global fetch/Buffer/BigInt)
grep -n -F -e "writeFile" -e "appendFile" -e "unlink" *.mjs  -> 0 hits
```

- **`lending-gate.mjs`**: confirmed its ONLY import is `isSelfFunded` from `../../../_shared/lib/is-self-funded.mjs`
  (itself pure, unmodified — see below). Every `nowMs` a function needs
  (`computeRecentDefaultLossUsd`, `sumRecentGojoGiftsUsd`, `detectDefaultedLoans`) is an explicit
  parameter; zero internal `Date.now()` reads anywhere in the file. Zero `fs`/`fetch`/network calls.
  **Matches the declared boundary exactly — genuinely 100% pure.**
- **`lending-path.mjs`**: exports exactly one runtime value, `LOANS_LEDGER_PATH`, computed via
  `path.join(__dirname, "..", "state", "loans.jsonl")` at module load — zero function exports, zero
  runtime logic beyond that one `path.join` call. **Matches the declared boundary — a pure constant.**
- **`gojo-read.mjs`**: its only side-effecting call is `fs.readFileSync` (confirmed: zero
  `fs.writeFileSync`/`fs.appendFileSync`/`fs.unlinkSync` anywhere in the file); `ENOENT` is the only
  caught error path (returns `[]`), everything else rethrows. **Matches the declared boundary — genuinely
  read-only.**
- **`lending-verify.mjs`**: every network call (`eth_getTransactionReceipt`, `eth_getBlockByNumber`,
  `eth_getLogs`) is routed through the single local `rpcCall()` helper — confirmed no other inline
  `fetch` call exists in the file. Zero `fs` access anywhere in this file. **Matches the declared
  boundary — network-only, single narrow chokepoint.**

### Reused-unmodified dependency (out of this diff, verified anyway for completeness)

- `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded` — PROP-111b's own Tier-0 obligation
  (structural diff against the pre-modification version) already covers byte-identity; this session's
  purity audit independently confirms `lending-gate.mjs` imports this function and calls it without
  wrapping/modifying its behavior.
- `~/anicca/skills/economy/gig/lib/lock.mjs` (`withGigLock`/`isLockStale`) and
  `~/anicca/skills/economy/gig/lib/escrow.mjs` (`payViaFacilitator`) are named in the Purity Boundary Map
  as reused-unmodified effectful shells this feature's (not-yet-built) orchestrator will call — this
  session confirms neither file appears anywhere in this feature's own diff (`git log --oneline --
  skills/economy/lending/` touches only the 4 delivered modules + their tests + this session's new
  property-test file).

## Summary

The four-module purity boundary this sprint declared holds **exactly** as stated, independently
re-verified by direct source grep this session (not merely re-trusting Phase 3's prior confirmation):
`lending-gate.mjs` is fully pure; `lending-path.mjs` is a pure constant; `gojo-read.mjs` and
`lending-verify.mjs` are the only two effectful modules, each narrowly scoped to exactly one purpose
(read-only fs vs. RPC-only network), matching `contracts/sprint-1.md`'s own CRIT-001/CRIT-009 criteria.
No residual risk found in the purity boundary itself; the only residual risks are the two LOW-severity,
non-purity-related observations already recorded in `security-report.md`.
