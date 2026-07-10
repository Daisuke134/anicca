# Security Hardening Report

## Feature: franklin-sol-evolvable-edge | Sprint: 1 | Date: 2026-07-10

## Tooling

| Tool | Availability | Used | Notes |
|---|---|---|---|
| Semgrep | available, `1.168.0` | yes | `--config auto` and `--config p/security-audit` both run against all 8 production files |
| Wycheproof | not applicable | n/a | This feature contains no cryptographic primitive implementation (no signing, hashing-for-security, or key handling — `genomeId()` uses `sha256` only as a non-cryptographic content-addressing id, not a security boundary; wallet/signing logic is entirely out of scope, owned by pre-existing `resolveSolanaSecret`/`franklin-trading`, explicitly unchanged by this feature per the Purity Boundary Map) |
| Mutation testing (`cargo-mutants`/`stryker`/`mutmut`) | not applicable | n/a | JS/bash feature; mutation coverage need is instead served by the Tier 2 fast-check property tests already run in Phase 2/5 (see verification-report.md) |

## Scope

Scanned files (8, all production modules named in the task scope):
- `skills/earn/sol-trade/lib/sol-genome.mjs`
- `skills/earn/sol-trade/lib/sol-gate.mjs`
- `skills/earn/sol-trade/lib/sol-trace.mjs`
- `skills/earn/sol-trade/lib/sol-evolve.mjs`
- `skills/earn/sol-trade/lib/sol-gate-cli.mjs`
- `skills/earn/sol-trade/lib/resolve-max-spend.sh`
- `skills/earn/sol-trade/run.sh`
- `skills/earn/sol-trade/baseline-genome.json`

## Raw results

| Run | Config | Rules loaded | Files scanned | Findings | Errors | Raw output |
|---|---|---|---|---|---|---|
| 1 | `--config auto` | (auto-selected registry ruleset) | 8/8 | **0** | 0 | `verification/security-results/semgrep-auto.json` |
| 2 | `--config p/security-audit` | 225 (verified via `--verbose --dryrun`) | 8/8 | **0** | 0 | `verification/security-results/semgrep-security-audit.json` |

Both scans confirmed non-trivial (225 real rules loaded and executed for the security-audit
ruleset, not a silent empty-ruleset pass) and both scans confirmed 0 parse/scan errors across all
8 files (i.e. every file was actually analyzed, not skipped).

## Manual cross-checks (beyond Semgrep, given this is money-path code)

- Grepped the entire feature scope for `eval(`, `new Function(`, and variable-derived `import(` —
  none found. This duplicates PROP-018's automated static source-text contract test
  (`sol-source-contract.test.mjs`), which also passes.
- Grepped for any assignment of `SOL_GATE_LIVE_ENABLE` to `"1"` outside test fixtures — none found;
  the only production reference is the strict-equality read in `sol-gate.mjs:32`.
- Read `resolve-max-spend.sh` in full (10 lines): unconditional `echo "0.25"`, zero env-var reads.
- Confirmed (by reading each declared-pure function body) that `stripForbidden`, `mutate`,
  `genomeId`, `decideEngagement`, `attributeGenomeIdSol`, and `summarizeByGenomeSol` contain no
  `fs.`/`fetch(`/uninjected `Date.now()`/uninjected `Math.random()` calls — no hidden I/O or
  non-determinism in the pure core (see purity-audit.md for the full boundary comparison).

## Findings

**Clean pass.** 0 findings across both Semgrep configurations and the manual cross-checks above.
No investigation was required (the task's "expect 0; investigate any hit" condition was not
triggered).

## Summary

Semgrep (`--config auto` + `--config p/security-audit`, 225 rules) ran cleanly against all 8
production files in scope with 0 findings and 0 errors. Wycheproof is explicitly not applicable
(no cryptographic primitive implementation in this feature's scope). No mutation-testing tool is
applicable to this JS/bash feature; Tier 2 fast-check property tests already discharged the
mutation-equivalent scrutiny for the money-safety-critical surfaces (PROP-002/004/008/009/012b/
013/016/017 — see verification-report.md). Money-path code (genome mutation, cap-stripping,
hard-spend-override, earnings-gate summation) is confirmed clean by both automated tooling and
direct source review.
