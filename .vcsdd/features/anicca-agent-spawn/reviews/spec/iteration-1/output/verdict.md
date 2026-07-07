# Verdict — anicca-agent-spawn — Phase 1c spec review — iteration 1

**overallVerdict: FAIL**

## Method

This is a fresh-context adversary review with zero access to the Builder's reasoning. Every artifact
this spec cites as "existing, reused unmodified" was actually opened and read, not assumed:
`gen-wallet.sh`, `spawn-decision.js` (+ tests), `child-spec.js` (+ tests), `ledger.js` (+ tests),
`is-self-funded.mjs` (+ tests), `resolve-identity.mjs`, `economy/gig/lib/identity.mjs`,
`economy/gig/lib/ensure-agent-id.mjs`, `economy/gig/lib/lock.mjs`, `deploy-akash.sh`,
`akt-treasury.sh`, the OLD `self/spawn/run.sh` + `SKILL.md`, `economy/ubi/run.sh`,
`economy/ubi/colony-wallets.json`, the live `~/.blockrun/mcp.json`, and the cited sections of
`anicca-agent-economy/specs/SPEC.md` (§0, §1.2, §1.3, §3, §9.5, §9.6, §9.9).

No web-access tool was available in this adversary's toolset, so the Nosana/Akash live-documentation
re-verification table in behavioral-spec.md was **not** independently re-checked against the internet
in this pass — only local file/artifact consistency was verified. This is a real limitation of this
review pass, not a PASS on that sub-claim.

## Findings summary

| ID | Dimension | Category | Severity | One-line |
|---|---|---|---|---|
| FIND-001 | spec_fidelity / implementation_correctness | requirement_mismatch | critical | `buildChildSpec` (claimed "reused unmodified") hard-requires a non-empty `childInbox` (AgentMail email) and `seedUsdc`, but no REQ-201-205 step produces an inbox, and the spec explicitly declares AgentMail provisioning superseded/out of scope |
| FIND-002 | spec_fidelity / verification_readiness | spec_gap | critical | No REQ specifies how the `citizens` list feeding `computeColonySurplusUsd`/`isSelfFunded()` is discovered or kept current as children are spawned; the only existing precedents (`ubi/run.sh`'s hardcoded 3-name dict, `colony-wallets.json`'s flat address array) don't supply the required shape and don't grow |
| FIND-003 | verification_readiness / structural_integrity | verification_tool_mismatch | major | REQ-103's lock (`lock.mjs`) and REQ-305's ledger (`ledger.js`) are both local-filesystem-only primitives, but REQ-301 guarantees children run on physically separate cloud hosts — no REQ specifies the shared/networked storage the cross-host guarantees actually require |
| FIND-004 | structural_integrity | spec_gap (duplication) | medium | REQ-204's "already-registered" edge case re-specifies logic that already exists, tested, in `ensure-agent-id.mjs`, which neither REQ-204 nor the Purity Boundary Map names |
| FIND-005 | spec_fidelity | requirement_mismatch (citation accuracy) | low | REQ-204 cites "SPEC.md §9.9" for gas-seed tx hashes that actually live in §9.6 |
| FIND-006 | edge_case_coverage | spec_gap | medium | REQ-302/303 both presuppose an already-"selected cloud target" but no REQ specifies who selects Nosana vs. Akash or how |

## Dimension verdicts

- **spec_fidelity: FAIL** — FIND-001, FIND-002, FIND-004, FIND-005, FIND-006.
- **edge_case_coverage: FAIL** — FIND-006.
- **implementation_correctness: FAIL** — FIND-001 (the single biggest blocker: as written, an implementer
  cannot literally satisfy REQ-201-205 without violating either "reused unmodified" or the "no AgentMail"
  architecture).
- **structural_integrity: FAIL** — FIND-003, FIND-004.
- **verification_readiness: FAIL** — FIND-002, FIND-003 (both undermine whether PROP-101a-c/PROP-103a can
  actually be proved as stated once more than one host/citizen-registry is real).

Per this project's binary-verdict rule, any single FAIL dimension fails the whole gate. Five of five
evaluated dimensions failed.

## What must change before iteration 2 can pass

1. Either specify a real, non-AgentMail-requiring path through `child-spec.js` (a modified/new function,
   disclosed as such — not "reused unmodified" — or a documented alternate `buildChildSpec` overload),
   or write a wholly new, purpose-built child-record constructor for REQ-201-205 and stop citing
   `buildChildSpec` as reused unmodified.
2. Add a requirement that defines the citizen registry: where the list of current citizens (including
   each newly-active child) lives, what shape each entry has (enough to call both `isSelfFunded()` and
   read a balance), and how REQ-201-305 keep it current.
3. Add a requirement (or an explicit, justified assumption backed by this project's actual current
   topology) for how the "colony-spawn" lock and the spawn ledger are shared across genuinely separate
   physical/cloud hosts, given REQ-301 forces children onto separate hosts.
4. Either cite `ensure-agent-id.mjs` as the reused already-registered-check mechanism, or explicitly
   justify why it is NOT reused and a new defensive check is written instead.
5. Fix the REQ-204 §9.9→§9.6 citation.
6. Add a requirement (or explicitly route to REQ-104's agent-in-envelope carve-out) for how the
   Nosana-vs-Akash cloud target is selected per spawn attempt.
