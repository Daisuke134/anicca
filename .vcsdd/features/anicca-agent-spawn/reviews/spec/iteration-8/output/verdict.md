# VCSDD Adversary Verdict — anicca-agent-spawn — Phase 1c spec review — iteration 8

**Overall verdict: FAIL**

## Prior findings (iteration 7) re-verification

| Finding | Severity | Status |
|---|---|---|
| FIND-601 | critical | **Genuinely resolved.** Directly read `~/.automaton/wallet.json` (confirms real `rotatedAt`/`rotationReason` fields), `docs/WALLETS.md`, the live `CLAUDE.md` on disk (not this session's stale cached context injection — that snapshot is itself outdated), and `colony-wallets.json`. All four now consistently show the rotated `0xB9dd3B67921B354c656523d6851537988F31DD56` address matching REQ-105's seed data. |
| FIND-602 | major | **Genuinely resolved.** Both purity-boundary summary tables and REQ-303's body text now consistently describe the Akash funding route as dual-entry (Solana/Jupiter or Base/CCTP). Grepped for the old stale phrase — only historical changelog mentions remain, describing the fix itself. |
| FIND-603 | critical | **Partially resolved.** The specific mechanical claim (never invoke the resolvers with an implicit/ambient shape) is genuinely true — passing a non-null `env` object makes the function bypass `process.env` entirely. But the fix's own prescription for constructing that `env` object depends on "the coordinator host's own real $HOME, sourced from a registry/coordinator constant" — a value this spec never actually defines anywhere (no constant, module, or schema field). The underlying hazard class (an unmodeled, silently load-bearing input) has been relocated, not eliminated. See new FIND-701. |
| FIND-604 | major | **Genuinely resolved.** PROP-101h is a real, new, non-duplicate both-chains-fail-simultaneously fixture, distinct from PROP-101f/PROP-101g, cross-referenced through the edge cases, acceptance criteria, and Gate section. |

## New findings this iteration

### FIND-701 (critical, verification_readiness) — the coordinator-host-HOME value in PROP-403e's own fix has no canonical source
REQ-403's explicit-env fix requires passing `env: {HOME: <the coordinator host's own real $HOME, sourced from a registry/coordinator constant>, ANICCA_HOME: citizen.homeDir}`. That exact placeholder phrase appears in only two places in the spec and is never resolved to an actual constant, module, or `citizens.json` schema field — unlike REQ-103's disciplined, single-named-constant (`CITIZENS_REGISTRY_PATH`) treatment of the structurally analogous "must not diverge across call sites" hazard. A Phase 2 implementer can satisfy PROP-403e's own literal stripped-`process.env` test while still silently reintroducing an ambient-environment dependency one layer up (e.g. reading `os.homedir()`/`process.env.HOME` once at audit-script startup). This is the same recurring "unmodeled input" failure class as FIND-501/FIND-603, relocated rather than closed.

### FIND-702 (major, verification_readiness) — PROP-105g verifies a citation, not the cited fact
PROP-105g's stated Tool/Method is "the adversary confirms the commit/PR ... cites" one of two acceptable verification methods — a check for the presence of a prose citation, not an independent re-performance of the cryptographic re-derivation it claims to require. This is meaningfully weaker than its own analogy to REQ-104 (which greps actual source code for a pattern's absence, a deterministic artifact check). A future append's commit message could falsely claim the re-derivation was performed and PROP-105g as worded would not catch it — reproducing, one layer removed, the exact "trusted-but-unverified citation" failure FIND-601 just found and fixed. A secondary, related gap: PROP-105g's method (a) requires reading the real private-key file to compute the re-derivation, which is never explicitly reconciled with this spec's repeated "content never read/printed" secrets discipline.

### FIND-703 (critical, spec_fidelity) — REQ-403's "co-located" enumeration has no schema-level basis
REQ-403's live-comparison half is specified to run "once per CO-LOCATED running instance... enumerated from REQ-105's registry" — but REQ-105's registry schema has no field distinguishing co-located from cloud-hosted citizens. REQ-301 mandates every spawned child is cloud-hosted (never co-located), and REQ-305 appends every successful child into this same registry. The moment this feature's own core deliverable (a spawn) succeeds, citizens.json mixes both kinds with no way to tell them apart, directly threatening PROP-403d's own binding "never invoked against a cloud-hosted child's homeDir" guarantee. Compounding this, REQ-403's own EARS clause promises the live-audit gate applies "before any newly-spawned CO-LOCATED child is permitted to participate" — a category REQ-301 makes structurally impossible this increment, so as literally worded the clause is either vacuous or a leftover phrase never reconciled with REQ-301/305's realities (the same "stale phrase" class of defect as FIND-602). This is the fourth variant of the REQ-101/105/403 wallet-identity area's recurring failure class the manifest specifically asked to be checked for.

## Broader fresh pass (areas not recently touched)

Directly re-read ~15 real source files this spec cites outside the immediate wallet-audit hot zone: `child-spec.js`, `is-self-funded.mjs`, `ledger.js`, `gen-wallet.sh`, `ensure-agent-id.mjs`, `lock.mjs`, `spawn-decision.js`, `akt-cost-gate.js`, `spawn-child/config.json`, `spawn-child/sdl/child.yaml`, `install.sh`, `identity/genesis.md`, `escrow.mjs`, `identity.mjs`, `run.sh` (specific cited line ranges), `colony-wallets.json`, `telemetry-post-franklin.mjs`. Every citation checked (REQ-102/103/104/201/202/204/205/206/301/303/304/306's factual claims about these files) was byte-accurate against the real, current source — no drift found in these areas this iteration.

## Dimension verdicts

- **spec_fidelity: FAIL** (FIND-703)
- **verification_readiness: FAIL** (FIND-701, FIND-702)

Convergence has not occurred. 8 consecutive iterations, 41+ cumulative findings, and the REQ-101/105/403 wallet-identity area has now produced a new defect in 5 of the last 4 iterations checked (FIND-501 → FIND-601/603 → FIND-701/703), even as each prior round's specific claim gets genuinely fixed.
