# Spec Review Verdict — anicca-agent-spawn — iteration 5 (Phase 1c)

**Overall verdict: FAIL**

Fresh-context review, zero prior conversation history. Every citation below was independently
re-read from the real, current file at the path given (not inferred from the spec's own prose).

## Part 1 — Verification of the 5 prior findings (FIND-301..305)

All 5 are **genuinely resolved** on their own terms, confirmed by directly re-reading the real
source files the spec cites (not by trusting the spec's own claims):

| Finding | Verdict | Key confirming evidence |
|---|---|---|
| FIND-301 (duplicate `child_id` rows) | Resolved | `ledger.js` re-confirmed `{readChildren, appendChild}` only; `run.sh:124-220` independently confirms the real multi-row-per-`child_id` pattern; `filterProductiveCitizens`'s last-write-wins rule + PROP-101d's extended fixture are genuinely testable (pure function, plain array fixtures) |
| FIND-302 (coordinator-local `fs.readFile` can't reach a cloud child) | Resolved | `readCitizenBalances` redesigned as registry-driven public-RPC-by-`walletAddress`, generalizing `telemetry-collect.sh`'s real `erc20()`/`sol()`/`solusdc()` pattern (re-read in full); `telemetryPath` grep across both spec files shows zero live schema references (all hits are changelog/historical prose or explicit removal statements) |
| FIND-303 (REQ-403 live check can't reach a cloud child) | Resolved **as scoped** — but see FIND-401 below for a deeper, related gap in the same boundary | Scoping to co-located instances is explicit, textual, and appears in the EARS clause, Edge Cases, Acceptance Criteria, and PROP-403d — not silently dropped. The claim that the static grep-sweep half still covers a cloud-hosted child (because it boots from the same git-cloned repo) is independently verified TRUE by reading `deploy-akash.sh`'s SDL |
| FIND-304 (`wallet` field name collision) | Resolved | `child-spec.js:37`/`child-spec.test.js:36` confirm the cited string-shaped field is real; cross-file disambiguation notes are present in REQ-206/REQ-305/Purity Boundary Map; PROP-206h requires a structural anti-cross-assignment check |
| FIND-305 (false price-oracle reuse claim) | Resolved | `akt-treasury.sh` re-read in full: no live USD query anywhere. `ethPrice()` confirmed real in `telemetry-poster.mjs:68-70` and `execute-invest.mjs:37-39`; `solPrice()` confirmed real in `telemetry-post-franklin.mjs:59-61` — all three are the claimed single-fetch, fail-closed-to-0 pattern, genuinely reused as a PATTERN (not a false "already-available oracle") |

## Part 2 — Fresh full-spec pass: 5 new findings (FIND-401..405)

Despite all 5 prior findings being genuinely resolved, this fresh pass — which this iteration's own
manifest explicitly demanded not be limited to a delta-only check — surfaced **5 new, evidenced
defects**, two of them (FIND-401, FIND-402) via real, pre-existing source artifacts
(`~/anicca/skills/self/spawn-child/`, `install.sh`) that no prior iteration's adversary appears to
have located and read.

### FIND-401 (critical, spec_fidelity + verification_readiness) — no wallet-material transport mechanism into the cloud lease
REQ-201/202 generate the child's wallet BEFORE cloud provisioning and require it "immediately
relocated into the child's own isolated $HOME." REQ-302/303 then deploy via artifacts explicitly
claimed reused "UNMODIFIED." Reading those real artifacts (`~/anicca/skills/self/spawn-child/sdl/child.yaml`
— the only external SDL template that exists in this codebase — and `deploy-akash.sh`'s own inline
default) shows both boot the child via a bare `git clone` + `install.sh` + `node runtime/loop/index.mjs`
with **zero secrets-injection channel** — no volume, no secret env var, nothing. `install.sh` itself
explicitly documents "does NOT ... ask for API keys / private keys (handled out of band)." The
deployed process therefore cannot possibly come into possession of the specific wallet REQ-204
registers and REQ-305 ledgers — this applies to every spawn this feature can ever produce, not a
corner case.

### FIND-402 (critical, spec_fidelity + structural_integrity) — real, live, unmentioned prior-art skill contradicts REQ-304
`~/anicca/skills/self/spawn-child/` is a real, already-implemented, already-tested, already-documented
(dated 2026-07-05, citing "colony spec §17-2/§20.1/§20.2/§21/§21.1") skill directly overlapping this
feature's REQ-102/303/304 scope, never mentioned anywhere in either spec document. Its `config.json`
already implements a concrete, tested Akash funding threshold (`spawn_cost_akt: 25`, `buffer_akt: 1`)
never reconciled with REQ-102's invented `$5.00`/`$10.00` anchor. Worse: its `funding_route` field
documents the ACTUAL, real, already-vetted mechanism for funding an AKT-denominated escrow from
either of the colony's real citizens' actual holdings (Base USDC or Solana SOL/USDC — neither is
natively AKT) — a **4-hop cross-chain bridge** (Jupiter SOL→USDC, then Skip API `smart_relay`
USDC(solana)→AKT via `noble-1`/`osmosis-1`) — directly contradicting REQ-304's claim that funding is
"a single-signer, single-transaction transfer." Given the colony's real wallet composition, every
Akash deploy this feature could ever fund needs exactly this bridge, not a same-chain transfer.

### FIND-403 (major, verification_readiness + spec_fidelity) — PROP-203c falsified by the real SDL artifacts
PROP-203c requires every REQ-302/303 process-launch boundary to "explicitly set HOME/ANICCA_HOME ...
never rely on a base-image default," checkable at Tier 0 by reading the real artifact. Both the real
`spawn-child/sdl/child.yaml` and `deploy-akash.sh`'s inline default SDL set only `AUTOMATON_GOAL`/
`ANICCA_CHILD_ID` — neither sets `HOME` or `ANICCA_HOME`. Since REQ-303 simultaneously requires these
exact artifacts reused "with zero source modification," REQ-203 and REQ-303 cannot both hold as
specified — the same "falsely-claimed unmodified reuse" pattern FIND-001/FIND-305 already caught
elsewhere, now recurring for the Akash SDL.

### FIND-404 (critical, spec_fidelity + verification_readiness) — dual-chain wallet balance aggregation unspecified
REQ-101 never specifies how to compute a USD balance for a citizen whose record carries BOTH
`walletAddress.evm` AND `walletAddress.solana` — and this is not rare: it is the **expected** shape
for every Nosana-deployed child, since REQ-201 unconditionally generates an EVM wallet while REQ-202
additionally generates a Solana wallet specifically when the child is Nosana-deployed. No Edge Case,
Acceptance Criteria, or PROP addresses summation vs. priority vs. error-treatment — despite this
iteration's own manifest explicitly naming this exact question as a re-verification item.

### FIND-405 (major, spec_fidelity) — REQ-402's "same ledger row" wording not reconciled with the append-only mechanism
REQ-402 still says "flips ... to bootstrap_failed in that SAME ledger row" — the identical wording
class FIND-301 flagged as symptomatic of an assumed update/upsert primitive `ledger.js` (re-confirmed
`{readChildren, appendChild}` only) doesn't have. REQ-101/REQ-305's analogous writes were explicitly
revised to state their write is an `appendChild` reduced via last-write-wins; REQ-402's own relabeling
operation was never given the equivalent clarification, leaving it internally inconsistent with its
sibling requirements' now-correct wording.

## Convergence assessment

This is the 5th consecutive FAIL iteration. All findings surfaced in iterations 1-4 (16+ total) are
now reconfirmed genuinely resolved — the resolution discipline itself is sound. But this iteration's
fresh, full-file, real-artifact-reading pass (rather than a delta-only check against the prior 5
findings) surfaced 5 more real, evidenced defects, two of which required discovering and reading
source files no prior review appears to have located. Convergence has not occurred.
