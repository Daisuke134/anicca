# Spec Review Verdict — anicca-agent-spawn — iteration 4

**Overall verdict: FAIL**

Fresh-context adversary, zero prior conversational context. Read the manifest, both full spec
documents (behavioral-spec.md 1240 lines, verification-architecture.md 365 lines, both read in
full), and independently re-read every real source file the spec cites for the 6 prior findings'
claimed fixes, plus several more for a full fresh pass, as instructed.

## Prior iteration-3 findings (FIND-201..206): all 6 confirmed genuinely resolved AS STATED

- **FIND-201** (critical, registry-vs-ledger location contradiction for `active_since`/`status`):
  the textual contradiction is gone — both REQ-101 and REQ-402 now consistently agree these facts
  live exclusively in `ledger.js`. *However*, the new join mechanism this fix introduces
  (`filterProductiveCitizens`) is itself broken at the implementation-mechanism level — see
  **FIND-301** below.
- **FIND-202 + FIND-205** (major/medium, `$HOME`-template / missing `homeDir`): confirmed no
  unresolved `$HOME` template exists in the seed data, and `homeDir` is present. *However*, this fix
  only works for today's 2 co-located citizens — see **FIND-302**/**FIND-303** below for why it
  breaks for any actual spawned (necessarily cloud-hosted) child.
- **FIND-203** (major, dangling `REQ-402`→`REQ-102` data flow): genuinely removed; `PROP-402d`
  explicitly pins `decideColonySpawn`'s signature. Confirmed resolved, no follow-on issue found.
- **FIND-204** (critical, `buildChildSpec`'s 4 mandatory fields never addressed): confirmed
  genuinely resolved and accurately grounded — `run.sh:136`'s `ANICCA_GENERATION:-1}` default,
  `install.sh:77-94`'s verbatim `genesis.md` shipping, and `identity/genesis.md`'s real existence
  were all independently re-verified against the actual files, not just the spec's own claims.
- **FIND-206** (low, vestigial edge case): confirmed removed from REQ-101.

## New findings this iteration (5, three critical)

| ID | Severity | One-line |
|---|---|---|
| FIND-301 | critical | `ledger.js` is append-only with zero update/dedup capability; `filterProductiveCitizens`'s "matching ledger row" join is unspecified for the duplicate-child_id-rows case that `run.sh`'s own real usage pattern proves is the norm, not the exception. |
| FIND-302 | critical | REQ-101/105's `telemetryPath`-based balance lookup is a coordinator-local `fs.readFile`; REQ-301 mandates every child run exclusively on a remote cloud lease, so no mechanism exists for a spawned child's own telemetry to ever reach that local path. |
| FIND-303 | critical | REQ-403's live wallet audit reuses `resolve-identity.mjs`, a pure local-filesystem resolver, against instances REQ-403 itself requires to include an actual spawned (remote) child — structurally unimplementable as specified. |
| FIND-304 | major | The key name `wallet` is reused with 3 incompatible shapes across this feature's own artifacts (address-string in `child-spec.js`/`ledger.js` rows vs. boolean-flags in `citizens.json` vs. `walletAddress` strings) without the disambiguation the spec explicitly provides elsewhere (FIND-104's own precedent). |
| FIND-305 | major | REQ-306 claims to reuse "already-available" AKT/USD and NOS/SOL/USD price-conversion mechanisms; a full read of `akt-treasury.sh` and a repo-wide grep confirm neither exists — both would need to be newly built, contradicting the requirement's own "never inventing a new pricing oracle" framing. |

## Dimension verdicts

- **spec_fidelity: FAIL** (FIND-301, 302, 303, 304, 305)
- **verification_readiness: FAIL** (FIND-301, 302, 303, 305)

## What must happen before this can PASS

FIND-301/302/303 are the load-bearing blockers — they all stem from the same class of gap: the
spec's location-contradiction-level review (iteration 3) fixed WHERE facts live and WHAT shape
fields have, but never verified that the underlying mechanisms (an append-only ledger being
treated as updatable-by-key; a local-filesystem-only balance/key resolver being asked to observe a
remote, cloud-hosted process) can actually execute the properties the spec claims for them. These
three need either (a) a new, explicit reconciliation/read mechanism specified (e.g., "last
chronological ledger row per `child_id` is authoritative," plus a registry-driven,
`walletAddress`-keyed, public-RPC telemetry generator run on the coordinator, plus an explicit
answer for how REQ-403's audit observes a remote child without moving private key material off its
own host), or (b) an explicit, honest scope-narrowing (analogous to REQ-106's own single-host
caveat) stating these mechanisms are NOT proven for cloud-hosted children this increment — but the
spec currently claims both without either being true.

Findings and full evidence: `findings/FIND-301.json` through `findings/FIND-305.json`.
