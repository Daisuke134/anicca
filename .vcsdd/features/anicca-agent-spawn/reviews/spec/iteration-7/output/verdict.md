# Spec Review Verdict — anicca-agent-spawn — Iteration 7

**Overall verdict: FAIL**

## Prior findings (FIND-501..504) — verification status

| Finding | Severity | Status this iteration |
|---|---|---|
| FIND-501 | critical | Genuinely resolved on its own stated terms (homeDir is now distinct + resolves non-null for both citizens, confirmed by walking resolve-identity.mjs's real source with the corrected seed values and confirming the relevant legacy wallet files exist on disk) — but see NEW FIND-603: the fix does not close the full class of bug it targeted. |
| FIND-502 | major | Genuinely resolved — config.json/SKILL.md citation split confirmed byte-accurate; PROP-304e's Base/8453/CCTP claim confirmed against escrow.mjs's real constants — but see NEW FIND-602: two other spec locations were never updated to match this correction. |
| FIND-503 | major | Genuinely resolved for its own specified case (exactly one chain fails) — but see NEW FIND-604: the adjacent "both chains fail" case this iteration's manifest asked about has no dedicated proof obligation. |
| FIND-504 | minor | Genuinely resolved — the cited evidence file is real, on-disk, dated, and contains the claimed CLI --help output verbatim. |

## New findings this iteration

### FIND-601 — CRITICAL — spec_fidelity
REQ-105's seed data assigns automaton (`anicca-a3cdd4`) the wallet address `0xB9dd3B67921B354c656523d6851537988F31DD56`, and claims this was verified against "this project's own `CLAUDE.md` colony table." Opening that exact file shows `CLAUDE.md:42` lists automaton's wallet as a **different** address, `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21`, independently corroborated by `docs/WALLETS.md:13` (labelled "Operational... pays x402 compute... payTo") and `docs/WALLETS.md:49-55` (which explicitly says, for automaton, "the funding wallet IS the signing key — no distinction needed"). REQ-101's entire colony-surplus aggregation and REQ-304's funding transfers key exclusively on `walletAddress` — if the wrong address was seeded, this feature's core treasury gate could silently aggregate/fund the wrong wallet. Neither address is fabricated (both are real, in-repo addresses used elsewhere — `0xB9dd3B...` in `colony-status.sh`/`colony-wallets.json`, `0xa3CDd4...` in CLAUDE.md/WALLETS.md/several production scripts) but the spec never reconciles this pre-existing, real, two-source conflict, despite explicitly claiming to have checked both.

### FIND-602 — MAJOR — spec_fidelity
Two purity-boundary summary tables (`behavioral-spec.md:207`, `verification-architecture.md:61`) were never updated for iteration 6's PROP-304e correction and still describe the Akash funding transfer as Solana/Jupiter-only — directly answering this iteration's manifest question ("does anything else still assume Franklin/Solana is the ONLY funding source") in the affirmative. REQ-304's own body text and Acceptance Criteria are correct; the summary tables are stale.

### FIND-603 — CRITICAL — verification_readiness
`resolve-identity.mjs`'s legacy-fallback resolution (the mechanism FIND-501's fix relies on) depends on a **second**, ambient input — `env.HOME`/`process.env.HOME` — never modeled by REQ-105's `homeDir` field nor pinned down by any REQ-403 acceptance criterion. The reused test suite never exercises the exact bare `{home: X}` invocation shape the spec's own worked examples use. If the audit ever runs where ambient HOME isn't exactly `/Users/anicca` (a documented real risk class for this project's own launchd/cron loops), both resolvers silently return `null` for both citizens — reproducing FIND-501's "vacuous audit" failure mode via an unaddressed second trigger.

### FIND-604 — MAJOR — verification_readiness
No proof obligation in the table (PROP-101a-g) explicitly instantiates a dual-wallet citizen whose BOTH chains fail simultaneously — a real, easy-to-miss combinatorial gap directly requested by this iteration's manifest.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-601, FIND-602 |
| verification_readiness | FAIL | FIND-603, FIND-604 |

## Convergence

7 consecutive iterations, 38+ cumulative findings. This iteration again surfaced a critical-severity defect in the exact wallet-identity area (`REQ-105`/`REQ-403`) that FIND-501, FIND-202, and FIND-303 all previously touched. Convergence has not occurred.
